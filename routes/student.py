from datetime import datetime
from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
from utils.decorators import student_required
from models.exam import Exam
from models.attempt import ExamAttempt
from services.exam_service import ExamService

student_bp = Blueprint('student', __name__, url_prefix='/student')


@student_bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    # Fetch all published exams
    available_exams = ExamService.get_available_exams_for_student(current_user.id)
    
    # Fetch all student attempts
    attempts = ExamAttempt.query.filter_by(
        student_id=current_user.id
    ).order_by(ExamAttempt.started_at.desc()).all()

    completed_attempts = [a for a in attempts if a.is_completed]
    active_attempts = [a for a in attempts if not a.is_completed]

    # Metrics
    total_completed = len(completed_attempts)
    avg_score = round(sum(a.percentage for a in completed_attempts) / total_completed, 1) if total_completed > 0 else 0.0
    passed_count = sum(1 for a in completed_attempts if a.is_passed)
    pass_rate = round((passed_count / total_completed) * 100, 1) if total_completed > 0 else 0.0

    # Risk metric
    risk_scores = [a.proctoring_session.risk_score for a in completed_attempts if a.proctoring_session]
    avg_risk = round(sum(risk_scores) / len(risk_scores), 1) if risk_scores else 0.0
    if avg_risk <= 20:
        overall_risk_label = 'LOW'
        overall_risk_badge = 'success'
    elif avg_risk <= 50:
        overall_risk_label = 'MEDIUM'
        overall_risk_badge = 'warning'
    else:
        overall_risk_label = 'HIGH'
        overall_risk_badge = 'danger'

    return render_template(
        'student/dashboard.html',
        available_exams=available_exams,
        completed_attempts=completed_attempts[:5],
        active_attempts=active_attempts,
        total_completed=total_completed,
        avg_score=avg_score,
        pass_rate=pass_rate,
        overall_risk_label=overall_risk_label,
        overall_risk_badge=overall_risk_badge
    )


@student_bp.route('/exams')
@login_required
@student_required
def exams():
    exams_data = ExamService.get_available_exams_for_student(current_user.id)
    return render_template('student/exams.html', exams=exams_data)


@student_bp.route('/history')
@login_required
@student_required
def history():
    attempts = ExamAttempt.query.filter_by(
        student_id=current_user.id
    ).order_by(ExamAttempt.started_at.desc()).all()
    return render_template('student/history.html', attempts=attempts)


@student_bp.route('/result/<int:attempt_id>')
@login_required
@student_required
def result(attempt_id):
    attempt = ExamAttempt.query.get_or_404(attempt_id)
    if attempt.student_id != current_user.id and not current_user.is_admin:
        abort(403)

    from services.result_service import ResultService
    detailed_result = ResultService.get_detailed_result(attempt.id)
    return render_template('student/result.html', **detailed_result)
