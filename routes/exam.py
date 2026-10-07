from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import login_required, current_user
from utils.decorators import student_required
from models.exam import Exam
from models.question import Question
from models.attempt import ExamAttempt, Answer
from services.exam_service import ExamService
from services.result_service import ResultService

exam_bp = Blueprint('exam', __name__, url_prefix='/exam')


@exam_bp.route('/<int:exam_id>/instructions')
@login_required
@student_required
def instructions(exam_id):
    exam = Exam.query.get_or_404(exam_id)

    # Check if student already finished this exam
    completed = ExamAttempt.query.filter_by(
        exam_id=exam.id,
        student_id=current_user.id
    ).filter(ExamAttempt.status.in_(['submitted', 'auto_submitted'])).first()

    if completed:
        flash("You have already completed this exam.", "info")
        return redirect(url_for('student.result', attempt_id=completed.id))

    # Check if there is an in-progress attempt already running
    in_progress = ExamAttempt.query.filter_by(
        exam_id=exam.id,
        student_id=current_user.id,
        status='in_progress'
    ).first()

    if in_progress:
        # If still within time, jump directly to exam
        remaining = ExamService.get_remaining_seconds(in_progress)
        if remaining > 0:
            return redirect(url_for('exam.take_exam', exam_id=exam.id))

    return render_template('student/instructions.html', exam=exam)


@exam_bp.route('/<int:exam_id>/verify')
@login_required
@student_required
def verify(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    demo_mode = current_app.config.get('DEMO_MODE', False)
    return render_template('student/verification.html', exam=exam, demo_mode=demo_mode)


@exam_bp.route('/<int:exam_id>/start', methods=['POST'])
@login_required
@student_required
def start_exam(exam_id):
    attempt, err = ExamService.start_or_resume_attempt(exam_id, current_user.id)
    if err:
        flash(err, "warning")
        return redirect(url_for('student.dashboard'))

    return redirect(url_for('exam.take_exam', exam_id=exam_id))


@exam_bp.route('/<int:exam_id>/take')
@login_required
@student_required
def take_exam(exam_id):
    exam = Exam.query.get_or_404(exam_id)

    # Fetch active attempt
    attempt = ExamAttempt.query.filter_by(
        exam_id=exam.id,
        student_id=current_user.id,
        status='in_progress'
    ).first()

    if not attempt:
        # Check if completed
        completed = ExamAttempt.query.filter_by(
            exam_id=exam.id,
            student_id=current_user.id
        ).filter(ExamAttempt.status.in_(['submitted', 'auto_submitted'])).first()
        if completed:
            return redirect(url_for('student.result', attempt_id=completed.id))
        return redirect(url_for('exam.instructions', exam_id=exam.id))

    # Calculate remaining time
    remaining_seconds = ExamService.get_remaining_seconds(attempt)
    if remaining_seconds <= 0:
        ResultService.calculate_and_submit_attempt(attempt.id, auto_submit=True)
        flash("Your examination time has expired. Exam was submitted automatically.", "warning")
        return redirect(url_for('student.result', attempt_id=attempt.id))

    # Fetch questions and saved answers
    questions = Question.query.filter_by(exam_id=exam.id).order_by(Question.order).all()
    saved_answers = ExamService.get_attempt_answers_map(attempt.id)

    demo_mode = current_app.config.get('DEMO_MODE', False)
    frame_interval = current_app.config.get('FRAME_INTERVAL', 2.0)

    return render_template(
        'student/exam.html',
        exam=exam,
        attempt=attempt,
        questions=questions,
        saved_answers=saved_answers,
        remaining_seconds=remaining_seconds,
        demo_mode=demo_mode,
        frame_interval=frame_interval
    )


@exam_bp.route('/<int:exam_id>/submit', methods=['POST'])
@login_required
@student_required
def submit_exam(exam_id):
    attempt = ExamAttempt.query.filter_by(
        exam_id=exam_id,
        student_id=current_user.id,
        status='in_progress'
    ).first()

    if not attempt:
        flash("No active examination attempt found.", "warning")
        return redirect(url_for('student.dashboard'))

    submitted_attempt, msg = ResultService.calculate_and_submit_attempt(attempt.id, auto_submit=False)
    flash("Exam submitted successfully!", "success")
    return redirect(url_for('student.result', attempt_id=submitted_attempt.id))
