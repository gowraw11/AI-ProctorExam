import io
import csv
from datetime import datetime
from flask import (
    Blueprint, render_template, redirect, url_for, flash,
    request, abort, jsonify, send_file, current_app
)
from flask_login import login_required, current_user
from utils.decorators import admin_required
from extensions import db
from models.user import User
from models.exam import Exam
from models.question import Question
from models.attempt import ExamAttempt, Answer
from models.proctoring import ProctoringSession, ProctoringEvent
from services.risk_engine import RiskEngine

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    total_students = User.query.filter_by(role='student').count()
    total_exams = Exam.query.count()
    total_attempts = ExamAttempt.query.count()

    completed_attempts = ExamAttempt.query.filter(
        ExamAttempt.status.in_(['submitted', 'auto_submitted'])
    ).all()

    avg_score = round(sum(a.percentage for a in completed_attempts) / len(completed_attempts), 1) if completed_attempts else 0.0

    # Suspicious attempts (HIGH or CRITICAL risk)
    suspicious_count = ProctoringSession.query.filter(ProctoringSession.risk_score >= 51).count()
    active_exams = Exam.query.filter_by(status='published').count()

    # Pass / Fail distribution
    passed_count = sum(1 for a in completed_attempts if a.is_passed)
    failed_count = len(completed_attempts) - passed_count

    # Risk level distribution
    sessions = ProctoringSession.query.all()
    risk_distribution = {
        'LOW': sum(1 for s in sessions if s.risk_level == 'LOW'),
        'MEDIUM': sum(1 for s in sessions if s.risk_level == 'MEDIUM'),
        'HIGH': sum(1 for s in sessions if s.risk_level == 'HIGH'),
        'CRITICAL': sum(1 for s in sessions if s.risk_level == 'CRITICAL')
    }

    # Violation counts by type
    violation_events = ProctoringEvent.query.all()
    violation_types = {}
    for ev in violation_events:
        clean_name = ev.event_type.replace('_', ' ').title()
        violation_types[clean_name] = violation_types.get(clean_name, 0) + 1

    # Recent attempts
    recent_attempts = ExamAttempt.query.order_by(ExamAttempt.started_at.desc()).limit(8).all()

    return render_template(
        'admin/dashboard.html',
        total_students=total_students,
        total_exams=total_exams,
        total_attempts=total_attempts,
        avg_score=avg_score,
        suspicious_count=suspicious_count,
        active_exams=active_exams,
        passed_count=passed_count,
        failed_count=failed_count,
        risk_distribution=risk_distribution,
        violation_types=violation_types,
        recent_attempts=recent_attempts
    )


# ---------------- EXAM MANAGEMENT ---------------- #

@admin_bp.route('/exams')
@login_required
@admin_required
def exams():
    exams_list = Exam.query.order_by(Exam.created_at.desc()).all()
    return render_template('admin/exams.html', exams=exams_list)


@admin_bp.route('/exams/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_exam():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        subject = request.form.get('subject', '').strip()
        description = request.form.get('description', '').strip()
        duration = int(request.form.get('duration_minutes', 60))
        total_marks = int(request.form.get('total_marks', 100))
        passing_marks = int(request.form.get('passing_marks', 40))
        status = request.form.get('status', 'published')

        if not title or not subject:
            flash("Title and Subject are required.", "danger")
            return render_template('admin/create_exam.html')

        new_exam = Exam(
            title=title,
            subject=subject,
            description=description,
            duration_minutes=duration,
            total_marks=total_marks,
            passing_marks=passing_marks,
            status=status
        )
        db.session.add(new_exam)
        db.session.commit()

        flash(f"Exam '{title}' created successfully! You can now add questions.", "success")
        return redirect(url_for('admin.exam_questions', exam_id=new_exam.id))

    return render_template('admin/create_exam.html')


@admin_bp.route('/exams/<int:exam_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_exam(exam_id):
    exam = Exam.query.get_or_404(exam_id)

    if request.method == 'POST':
        exam.title = request.form.get('title', '').strip()
        exam.subject = request.form.get('subject', '').strip()
        exam.description = request.form.get('description', '').strip()
        exam.duration_minutes = int(request.form.get('duration_minutes', exam.duration_minutes))
        exam.total_marks = int(request.form.get('total_marks', exam.total_marks))
        exam.passing_marks = int(request.form.get('passing_marks', exam.passing_marks))
        exam.status = request.form.get('status', exam.status)

        db.session.commit()
        flash("Exam details updated successfully.", "success")
        return redirect(url_for('admin.exams'))

    return render_template('admin/edit_exam.html', exam=exam)


@admin_bp.route('/exams/<int:exam_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_exam(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    title = exam.title
    db.session.delete(exam)
    db.session.commit()
    flash(f"Exam '{title}' and all associated questions/attempts were deleted.", "info")
    return redirect(url_for('admin.exams'))


@admin_bp.route('/exams/<int:exam_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_exam_status(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    exam.status = 'published' if exam.status == 'draft' else 'draft'
    db.session.commit()
    flash(f"Exam status changed to {exam.status.upper()}.", "success")
    return redirect(url_for('admin.exams'))


# ---------------- QUESTION MANAGEMENT ---------------- #

@admin_bp.route('/exams/<int:exam_id>/questions', methods=['GET', 'POST'])
@login_required
@admin_required
def exam_questions(exam_id):
    exam = Exam.query.get_or_404(exam_id)

    if request.method == 'POST':
        question_text = request.form.get('question_text', '').strip()
        opt_a = request.form.get('option_a', '').strip()
        opt_b = request.form.get('option_b', '').strip()
        opt_c = request.form.get('option_c', '').strip()
        opt_d = request.form.get('option_d', '').strip()
        correct = request.form.get('correct_answer', '').strip().upper()
        marks = float(request.form.get('marks', 1.0))
        negative_marks = float(request.form.get('negative_marks', 0.0))

        if not question_text or not opt_a or not opt_b or not opt_c or not opt_d or not correct:
            flash("All question fields and options are required.", "danger")
        else:
            current_count = len(exam.questions)
            question = Question(
                exam_id=exam.id,
                question_text=question_text,
                option_a=opt_a,
                option_b=opt_b,
                option_c=opt_c,
                option_d=opt_d,
                correct_answer=correct,
                marks=marks,
                negative_marks=negative_marks,
                order=current_count + 1
            )
            db.session.add(question)
            db.session.commit()
            flash("Question added successfully!", "success")
            return redirect(url_for('admin.exam_questions', exam_id=exam.id))

    questions = Question.query.filter_by(exam_id=exam.id).order_by(Question.order).all()
    return render_template('admin/questions.html', exam=exam, questions=questions)


@admin_bp.route('/questions/<int:question_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_question(question_id):
    question = Question.query.get_or_404(question_id)
    exam_id = question.exam_id
    db.session.delete(question)
    db.session.commit()
    flash("Question deleted successfully.", "info")
    return redirect(url_for('admin.exam_questions', exam_id=exam_id))


# ---------------- STUDENTS MANAGEMENT ---------------- #

@admin_bp.route('/students')
@login_required
@admin_required
def students():
    query = request.args.get('q', '').strip()
    if query:
        students_list = User.query.filter_by(role='student').filter(
            (User.full_name.ilike(f"%{query}%")) |
            (User.email.ilike(f"%{query}%")) |
            (User.registration_number.ilike(f"%{query}%"))
        ).all()
    else:
        students_list = User.query.filter_by(role='student').order_by(User.created_at.desc()).all()

    return render_template('admin/students.html', students=students_list, query=query)


@admin_bp.route('/students/<int:student_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_student_status(student_id):
    student = User.query.get_or_404(student_id)
    student.is_active = not student.is_active
    db.session.commit()
    status_str = "activated" if student.is_active else "deactivated"
    flash(f"Student account {student.email} has been {status_str}.", "info")
    return redirect(url_for('admin.students'))


# ---------------- ATTEMPTS MONITOR ---------------- #

@admin_bp.route('/attempts')
@login_required
@admin_required
def attempts():
    exam_id = request.args.get('exam_id', type=int)
    risk_filter = request.args.get('risk', '').strip().upper()

    query = ExamAttempt.query.order_by(ExamAttempt.started_at.desc())

    if exam_id:
        query = query.filter(ExamAttempt.exam_id == exam_id)

    attempts_list = query.all()

    if risk_filter:
        attempts_list = [a for a in attempts_list if a.proctoring_session and a.proctoring_session.risk_level == risk_filter]

    all_exams = Exam.query.all()
    return render_template('admin/attempts.html', attempts=attempts_list, exams=all_exams, selected_exam=exam_id, risk_filter=risk_filter)


# ---------------- PROCTORING MONITOR & TIMELINE ---------------- #

@admin_bp.route('/proctoring')
@login_required
@admin_required
def proctoring():
    # Show attempts with their proctoring sessions
    attempts_list = ExamAttempt.query.order_by(ExamAttempt.started_at.desc()).all()
    return render_template('admin/proctoring.html', attempts=attempts_list)


@admin_bp.route('/proctoring/<int:attempt_id>')
@login_required
@admin_required
def proctoring_detail(attempt_id):
    attempt = ExamAttempt.query.get_or_404(attempt_id)
    session = attempt.proctoring_session
    events = ProctoringEvent.query.filter_by(attempt_id=attempt.id).order_by(ProctoringEvent.timestamp.asc()).all()

    # Event count summary
    event_counts = {}
    for ev in events:
        event_counts[ev.event_type] = event_counts.get(ev.event_type, 0) + 1

    return render_template(
        'admin/proctoring_detail.html',
        attempt=attempt,
        session=session,
        events=events,
        event_counts=event_counts
    )


# ---------------- REPORTS & EXPORT ---------------- #

@admin_bp.route('/reports')
@login_required
@admin_required
def reports():
    exams_data = []
    exams = Exam.query.all()

    for ex in exams:
        attempts = ExamAttempt.query.filter_by(exam_id=ex.id).filter(ExamAttempt.status.in_(['submitted', 'auto_submitted'])).all()
        if attempts:
            scores = [a.percentage for a in attempts]
            avg_s = round(sum(scores) / len(scores), 1)
            highest_s = max(scores)
            lowest_s = min(scores)
            pass_c = sum(1 for a in attempts if a.is_passed)
            pass_rate = round((pass_c / len(attempts)) * 100, 1)
            high_risk_c = sum(1 for a in attempts if a.proctoring_session and a.proctoring_session.risk_score >= 51)
        else:
            avg_s = highest_s = lowest_s = pass_rate = high_risk_c = 0.0

        exams_data.append({
            'exam': ex,
            'total_attempts': len(attempts),
            'avg_score': avg_s,
            'highest_score': highest_s,
            'lowest_score': lowest_s,
            'pass_rate': pass_rate,
            'high_risk_count': high_risk_c
        })

    return render_template('admin/reports.html', exams_data=exams_data)


@admin_bp.route('/reports/export-csv')
@login_required
@admin_required
def export_csv():
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        'Attempt ID', 'Student Name', 'Registration Number', 'Student Email',
        'Exam Title', 'Subject', 'Score', 'Percentage', 'Result',
        'Started At', 'Submitted At', 'Violations Count', 'Risk Score', 'Risk Level'
    ])

    attempts = ExamAttempt.query.order_by(ExamAttempt.started_at.desc()).all()
    for att in attempts:
        session = att.proctoring_session
        writer.writerow([
            att.id,
            att.student.full_name if att.student else '',
            att.student.registration_number if att.student else '',
            att.student.email if att.student else '',
            att.exam.title if att.exam else '',
            att.exam.subject if att.exam else '',
            att.score,
            f"{att.percentage}%",
            'PASSED' if att.is_passed else 'FAILED',
            att.started_at.strftime('%Y-%m-%d %H:%M:%S') if att.started_at else '',
            att.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if att.submitted_at else 'In Progress',
            att.suspicious_activity_count,
            session.risk_score if session else 0,
            session.risk_level if session else 'LOW'
        ])

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f"exam_proctoring_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    )


@admin_bp.route('/reports/export-pdf')
@login_required
@admin_required
def export_pdf():
    """Generates PDF audit report using reportlab."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    elements = []
    styles = getSampleStyleSheet()

    # Title & Subtitle
    elements.append(Paragraph("<b>Online Examination & AI Proctoring System</b>", styles['Title']))
    elements.append(Paragraph("Official Examination Audit & Performance Report", styles['Heading2']))
    elements.append(Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}", styles['Normal']))
    elements.append(Spacer(1, 16))

    # Summary table
    total_students = User.query.filter_by(role='student').count()
    total_attempts = ExamAttempt.query.count()
    completed = ExamAttempt.query.filter(ExamAttempt.status.in_(['submitted', 'auto_submitted'])).all()
    avg_score = round(sum(a.percentage for a in completed) / len(completed), 1) if completed else 0.0

    summary_data = [
        ["Total Registered Students", str(total_students), "Total Exam Attempts", str(total_attempts)],
        ["Completed Exams", str(len(completed)), "Average Percentage", f"{avg_score}%"]
    ]
    summary_table = Table(summary_data, colWidths=[140, 120, 140, 120])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f1f5f9')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 20))

    # Attempts details table
    elements.append(Paragraph("<b>Recent Examination Attempts & Risk Assessments</b>", styles['Heading3']))
    attempts = ExamAttempt.query.order_by(ExamAttempt.started_at.desc()).limit(25).all()

    table_data = [["ID", "Student", "Exam", "Score", "Result", "Violations", "Risk"]]
    for att in attempts:
        session = att.proctoring_session
        table_data.append([
            str(att.id),
            att.student.full_name[:18] if att.student else 'Unknown',
            att.exam.title[:20] if att.exam else 'Exam',
            f"{att.percentage}%",
            'PASS' if att.is_passed else 'FAIL',
            str(att.suspicious_activity_count),
            session.risk_level if session else 'LOW'
        ])

    detail_table = Table(table_data, colWidths=[30, 120, 140, 55, 55, 60, 60])
    detail_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (2, -1), 'LEFT'),
        ('PADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(detail_table)

    doc.build(elements)
    buffer.seek(0)
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"proctoring_audit_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
    )


# ---------------- SETTINGS ---------------- #

@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    if request.method == 'POST':
        demo_mode_val = request.form.get('demo_mode') == 'on'
        current_app.config['DEMO_MODE'] = demo_mode_val
        frame_interval_val = float(request.form.get('frame_interval', 2.0))
        current_app.config['FRAME_INTERVAL'] = frame_interval_val

        flash("System settings updated successfully.", "success")
        return redirect(url_for('admin.settings'))

    demo_mode = current_app.config.get('DEMO_MODE', False)
    frame_interval = current_app.config.get('FRAME_INTERVAL', 2.0)
    return render_template('admin/settings.html', demo_mode=demo_mode, frame_interval=frame_interval)
