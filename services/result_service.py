from datetime import datetime
from extensions import db
from models.attempt import ExamAttempt, Answer
from models.question import Question
from models.proctoring import ProctoringSession, ProctoringEvent
from services.risk_engine import RiskEngine


class ResultService:
    """
    Evaluates submitted exams, computes scores, negative marking,
    pass/fail outcomes, and aggregated analytical reports.
    """

    @staticmethod
    def calculate_and_submit_attempt(attempt_id: int, auto_submit: bool = False):
        attempt = db.session.get(ExamAttempt, attempt_id)
        if not attempt:
            return None, "Attempt not found"

        if attempt.is_completed:
            return attempt, "Exam already submitted."

        exam = attempt.exam
        questions = Question.query.filter_by(exam_id=exam.id).all()
        answers = Answer.query.filter_by(attempt_id=attempt.id).all()
        answers_map = {ans.question_id: ans for ans in answers}

        total_score = 0.0
        correct_count = 0
        incorrect_count = 0
        unanswered_count = 0

        for q in questions:
            user_ans = answers_map.get(q.id)
            if not user_ans or not user_ans.selected_answer:
                unanswered_count += 1
                if user_ans:
                    user_ans.is_correct = False
                    user_ans.marks_awarded = 0.0
            else:
                is_correct = (user_ans.selected_answer.strip().upper() == q.correct_answer.strip().upper())
                user_ans.is_correct = is_correct

                if is_correct:
                    correct_count += 1
                    user_ans.marks_awarded = float(q.marks)
                    total_score += float(q.marks)
                else:
                    incorrect_count += 1
                    # Apply negative marking if configured
                    neg_deduction = float(q.negative_marks or 0.0)
                    user_ans.marks_awarded = -neg_deduction
                    total_score -= neg_deduction

        # Prevent negative total score
        total_score = max(0.0, total_score)
        total_possible = float(exam.calculated_total_marks) or 100.0
        percentage = (total_score / total_possible) * 100.0 if total_possible > 0 else 0.0

        # Update attempt
        attempt.score = round(total_score, 2)
        attempt.percentage = round(percentage, 2)
        attempt.submitted_at = datetime.utcnow()
        attempt.status = 'auto_submitted' if auto_submit else 'submitted'

        # Close proctoring session
        session = attempt.proctoring_session
        if session:
            session.ended_at = attempt.submitted_at
            # Update session status based on risk level
            risk_level = session.risk_level
            if risk_level == 'LOW':
                session.final_status = 'CLEARED'
            elif risk_level == 'MEDIUM':
                session.final_status = 'LOW_RISK'
            elif risk_level == 'HIGH':
                session.final_status = 'HIGH_RISK'
            else:
                session.final_status = 'CRITICAL_RISK'

        db.session.commit()
        return attempt, "Exam submitted successfully."

    @staticmethod
    def get_detailed_result(attempt_id: int):
        attempt = db.session.get(ExamAttempt, attempt_id)
        if not attempt:
            return None
        exam = attempt.exam
        questions = Question.query.filter_by(exam_id=exam.id).order_by(Question.order).all()
        answers = Answer.query.filter_by(attempt_id=attempt.id).all()
        answers_map = {ans.question_id: ans for ans in answers}

        correct_count = 0
        incorrect_count = 0
        unanswered_count = 0

        question_breakdown = []
        for q in questions:
            ans = answers_map.get(q.id)
            selected = ans.selected_answer if ans else None
            is_correct = ans.is_correct if ans else False

            if not selected:
                unanswered_count += 1
                status = 'unanswered'
            elif is_correct:
                correct_count += 1
                status = 'correct'
            else:
                incorrect_count += 1
                status = 'incorrect'

            question_breakdown.append({
                'question': q,
                'selected_answer': selected,
                'is_correct': is_correct,
                'status': status,
                'marks_awarded': ans.marks_awarded if ans else 0.0
            })

        session = attempt.proctoring_session
        events = ProctoringEvent.query.filter_by(attempt_id=attempt.id).order_by(ProctoringEvent.timestamp.asc()).all()

        return {
            'attempt': attempt,
            'exam': exam,
            'student': attempt.student,
            'correct_count': correct_count,
            'incorrect_count': incorrect_count,
            'unanswered_count': unanswered_count,
            'total_questions': len(questions),
            'question_breakdown': question_breakdown,
            'proctoring_session': session,
            'events': events,
            'is_passed': attempt.is_passed
        }
