from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user, login_required
from extensions import db
from models.user import User
from models.exam import Exam
from models.question import Question
from models.attempt import ExamAttempt, Answer
from models.proctoring import ProctoringSession, ProctoringEvent
from services.exam_service import ExamService
from services.result_service import ResultService
from services.proctoring_service import ProctoringService
from ml.face_detector import FaceDetector

api_bp = Blueprint('api', __name__, url_prefix='/api')


# ---------------- PROCTORING APIS ---------------- #

@api_bp.route('/proctoring/verify', methods=['POST'])
@login_required
def proctoring_verify():
    """
    Validates webcam feed during pre-exam verification screen.
    Checks: camera signal, face count == 1, centering, lighting.
    """
    data = request.get_json(silent=True) or {}
    image_b64 = data.get('image')
    demo_mode = data.get('demo_mode', False) or current_app.config.get('DEMO_MODE', False)

    if not image_b64 and demo_mode:
        return jsonify({
            'success': True,
            'camera_detected': True,
            'face_detected': True,
            'single_face': True,
            'lighting_ok': True,
            'is_centered': True,
            'status': 'READY',
            'message': '[DEMO MODE] System readiness verified.'
        })

    if not image_b64:
        return jsonify({
            'success': False,
            'camera_detected': False,
            'message': 'No video frame received from camera.'
        }), 400

    detector = FaceDetector()
    face_info, frame = detector.detect_faces(image_b64)

    if not face_info.get('success', False):
        return jsonify({
            'success': False,
            'camera_detected': True,
            'face_detected': False,
            'message': 'Unable to decode camera frame.'
        })

    face_count = face_info['face_count']
    face_detected = face_count > 0
    single_face = (face_count == 1)
    lighting_ok = face_info['lighting_ok']
    is_centered = face_info['is_centered']

    ready = face_detected and single_face and lighting_ok

    if ready:
        msg = 'Verification successful! Face, lighting, and camera verified. You may start.'
    elif not face_detected:
        msg = 'No face detected yet. Please position yourself directly in front of the camera.'
    elif not single_face:
        msg = f'Multiple faces detected ({face_count}). Only the candidate must be visible.'
    elif not lighting_ok:
        msg = 'Lighting level is low or uneven. Please face a light source.'
    else:
        msg = 'Please adjust your position so your face is clearly visible.'

    return jsonify({
        'success': True,
        'camera_detected': True,
        'face_detected': face_detected,
        'face_count': face_count,
        'single_face': single_face,
        'lighting_ok': lighting_ok,
        'lighting_score': face_info['lighting_score'],
        'is_centered': is_centered,
        'status': 'READY' if ready else 'ADJUST_POSITION',
        'message': msg
    })


@api_bp.route('/proctoring/frame', methods=['POST'])
@login_required
def proctoring_frame():
    """
    Receives live periodic frame snapshot from student exam browser.
    Runs face detection, head pose estimation, and gaze tracking.
    """
    data = request.get_json(silent=True) or {}
    attempt_id = data.get('attempt_id')
    image_b64 = data.get('image')
    is_demo = data.get('is_demo', False) or current_app.config.get('DEMO_MODE', False)

    if not attempt_id:
        return jsonify({'success': False, 'message': 'attempt_id is required'}), 400

    attempt = db.session.get(ExamAttempt, attempt_id)
    if not attempt or attempt.student_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized attempt'}), 403

    if attempt.is_completed:
        return jsonify({'success': False, 'message': 'Exam is already closed'}), 400

    result = ProctoringService.process_frame(attempt.id, image_b64, is_demo=is_demo)
    return jsonify(result)


@api_bp.route('/proctoring/event', methods=['POST'])
@login_required
def proctoring_event():
    """
    Logs client-side security event (TAB_SWITCH, FULLSCREEN_EXIT, COPY_ATTEMPT, etc.).
    """
    data = request.get_json(silent=True) or {}
    attempt_id = data.get('attempt_id')
    event_type = data.get('event_type')
    description = data.get('description', '')
    image_b64 = data.get('image')
    is_demo = data.get('is_demo', False) or current_app.config.get('DEMO_MODE', False)

    if not attempt_id or not event_type:
        return jsonify({'success': False, 'message': 'attempt_id and event_type are required'}), 400

    attempt = db.session.get(ExamAttempt, attempt_id)
    if not attempt or attempt.student_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized attempt'}), 403

    result = ProctoringService.log_client_event(
        attempt.id,
        event_type=event_type,
        description=description,
        image_b64=image_b64,
        is_demo=is_demo
    )
    return jsonify(result)


# ---------------- EXAM APIS ---------------- #

@api_bp.route('/exams', methods=['GET'])
def get_exams():
    exams = Exam.query.filter_by(status='published').all()
    return jsonify({'success': True, 'exams': [e.to_dict() for e in exams]})


@api_bp.route('/exams/<int:exam_id>', methods=['GET'])
def get_exam(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    include_correct = current_user.is_authenticated and current_user.is_admin
    questions_data = [q.to_dict(include_correct=include_correct) for q in exam.questions]
    data = exam.to_dict()
    data['questions'] = questions_data
    return jsonify({'success': True, 'exam': data})


@api_bp.route('/exams/<int:exam_id>/start', methods=['POST'])
@login_required
def api_start_exam(exam_id):
    attempt, err = ExamService.start_or_resume_attempt(exam_id, current_user.id)
    if err:
        return jsonify({'success': False, 'message': err}), 400

    remaining = ExamService.get_remaining_seconds(attempt)
    return jsonify({
        'success': True,
        'attempt_id': attempt.id,
        'remaining_seconds': remaining
    })


@api_bp.route('/exams/<int:exam_id>/answer', methods=['POST'])
@login_required
def api_save_answer(exam_id):
    data = request.get_json(silent=True) or {}
    attempt_id = data.get('attempt_id')
    question_id = data.get('question_id')
    selected_answer = data.get('selected_answer')

    if not attempt_id or not question_id:
        return jsonify({'success': False, 'message': 'Missing parameters'}), 400

    attempt = db.session.get(ExamAttempt, attempt_id)
    if not attempt or attempt.student_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    # Check time validity
    remaining = ExamService.get_remaining_seconds(attempt)
    if remaining <= 0:
        ResultService.calculate_and_submit_attempt(attempt.id, auto_submit=True)
        return jsonify({'success': False, 'message': 'Time expired', 'time_expired': True}), 400

    ok, msg = ExamService.save_answer(attempt.id, question_id, selected_answer)
    return jsonify({'success': ok, 'message': msg, 'remaining_seconds': remaining})


@api_bp.route('/exams/<int:exam_id>/submit', methods=['POST'])
@login_required
def api_submit_exam(exam_id):
    data = request.get_json(silent=True) or {}
    attempt_id = data.get('attempt_id')
    auto_submit = data.get('auto_submit', False)

    if not attempt_id:
        return jsonify({'success': False, 'message': 'Missing attempt_id'}), 400

    attempt = db.session.get(ExamAttempt, attempt_id)
    if not attempt or attempt.student_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    submitted_attempt, msg = ResultService.calculate_and_submit_attempt(attempt.id, auto_submit=auto_submit)
    return jsonify({
        'success': True,
        'message': msg,
        'attempt': submitted_attempt.to_dict()
    })


@api_bp.route('/exams/<int:exam_id>/status', methods=['GET'])
@login_required
def api_exam_status(exam_id):
    attempt = ExamAttempt.query.filter_by(
        exam_id=exam_id,
        student_id=current_user.id,
        status='in_progress'
    ).first()

    if not attempt:
        return jsonify({'success': False, 'is_active': False})

    remaining = ExamService.get_remaining_seconds(attempt)
    return jsonify({
        'success': True,
        'is_active': remaining > 0,
        'attempt_id': attempt.id,
        'remaining_seconds': remaining
    })


# ---------------- ATTEMPTS & RESULTS APIS ---------------- #

@api_bp.route('/attempts/<int:attempt_id>', methods=['GET'])
@login_required
def api_get_attempt(attempt_id):
    attempt = db.session.get(ExamAttempt, attempt_id)
    if not attempt:
        return jsonify({'success': False, 'message': 'Not found'}), 404
    if attempt.student_id != current_user.id and not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    return jsonify({'success': True, 'attempt': attempt.to_dict()})


@api_bp.route('/results/<int:attempt_id>', methods=['GET'])
@login_required
def api_get_result(attempt_id):
    attempt = db.session.get(ExamAttempt, attempt_id)
    if not attempt:
        return jsonify({'success': False, 'message': 'Not found'}), 404
    if attempt.student_id != current_user.id and not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    result = ResultService.get_detailed_result(attempt.id)
    return jsonify({
        'success': True,
        'score': attempt.score,
        'percentage': attempt.percentage,
        'is_passed': result['is_passed'],
        'correct_count': result['correct_count'],
        'incorrect_count': result['incorrect_count'],
        'unanswered_count': result['unanswered_count'],
        'risk_score': result['proctoring_session'].risk_score if result['proctoring_session'] else 0
    })


# ---------------- ADMIN STATISTICS API ---------------- #

@api_bp.route('/admin/statistics', methods=['GET'])
@login_required
def api_admin_statistics():
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Forbidden'}), 403

    total_students = User.query.filter_by(role='student').count()
    total_exams = Exam.query.count()
    total_attempts = ExamAttempt.query.count()
    completed = ExamAttempt.query.filter(ExamAttempt.status.in_(['submitted', 'auto_submitted'])).all()
    avg_score = round(sum(a.percentage for a in completed) / len(completed), 1) if completed else 0.0

    return jsonify({
        'success': True,
        'total_students': total_students,
        'total_exams': total_exams,
        'total_attempts': total_attempts,
        'average_score': avg_score
    })
