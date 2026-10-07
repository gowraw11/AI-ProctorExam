from datetime import datetime, timedelta
from extensions import db
from models.exam import Exam
from models.question import Question
from models.attempt import ExamAttempt, Answer
from models.proctoring import ProctoringSession


class ExamService:
    """
    Manages exam lifecycles, question banks, candidate attempts,
    and server-side timer validation.
    """

    @staticmethod
    def get_available_exams_for_student(student_id: int):
        exams = Exam.query.filter_by(status='published').all()
        result = []
        for exam in exams:
            # Check latest attempt for this student
            latest_attempt = ExamAttempt.query.filter_by(
                exam_id=exam.id,
                student_id=student_id
            ).order_by(ExamAttempt.started_at.desc()).first()

            exam_data = exam.to_dict()
            exam_data['user_attempt'] = latest_attempt.to_dict() if latest_attempt else None
            result.append(exam_data)
        return result

    @staticmethod
    def start_or_resume_attempt(exam_id: int, student_id: int):
        exam = db.session.get(Exam, exam_id)
        if not exam:
            return None, "Exam not found."

        # Check for existing in-progress attempt
        attempt = ExamAttempt.query.filter_by(
            exam_id=exam.id,
            student_id=student_id,
            status='in_progress'
        ).first()

        now = datetime.utcnow()

        if attempt:
            # Check if time expired
            max_end_time = attempt.started_at + timedelta(minutes=exam.duration_minutes)
            if now > max_end_time:
                # Expired attempt
                from services.result_service import ResultService
                ResultService.calculate_and_submit_attempt(attempt.id, auto_submit=True)
                return None, "Exam time has expired."
            return attempt, None

        # Check if already submitted and single attempt policy
        completed = ExamAttempt.query.filter_by(
            exam_id=exam.id,
            student_id=student_id
        ).filter(ExamAttempt.status.in_(['submitted', 'auto_submitted'])).first()

        if completed:
            return None, "You have already completed this exam."

        # Create new attempt
        attempt = ExamAttempt(
            exam_id=exam.id,
            student_id=student_id,
            started_at=now,
            status='in_progress'
        )
        db.session.add(attempt)
        db.session.flush()

        # Create linked proctoring session
        session = ProctoringSession(
            attempt_id=attempt.id,
            started_at=now,
            risk_score=0,
            final_status='CLEARED'
        )
        db.session.add(session)
        db.session.commit()

        return attempt, None

    @staticmethod
    def get_remaining_seconds(attempt: ExamAttempt) -> int:
        if not attempt or attempt.is_completed:
            return 0
        exam = attempt.exam
        deadline = attempt.started_at + timedelta(minutes=exam.duration_minutes)
        now = datetime.utcnow()
        remaining = int((deadline - now).total_seconds())
        return max(0, remaining)

    @staticmethod
    def save_answer(attempt_id: int, question_id: int, selected_option: str):
        attempt = db.session.get(ExamAttempt, attempt_id)
        if not attempt or attempt.is_completed:
            return False, "Attempt is closed or does not exist."

        # Validate question belongs to this exam
        question = Question.query.filter_by(id=question_id, exam_id=attempt.exam_id).first()
        if not question:
            return False, "Invalid question for this exam."

        answer = Answer.query.filter_by(attempt_id=attempt.id, question_id=question_id).first()
        if not answer:
            answer = Answer(
                attempt_id=attempt.id,
                question_id=question_id,
                selected_answer=selected_option
            )
            db.session.add(answer)
        else:
            answer.selected_answer = selected_option

        db.session.commit()
        return True, "Answer saved successfully."

    @staticmethod
    def get_attempt_answers_map(attempt_id: int):
        answers = Answer.query.filter_by(attempt_id=attempt_id).all()
        return {ans.question_id: ans.selected_answer for ans in answers}
