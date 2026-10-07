import unittest
from app import create_app
from extensions import db
from models.user import User
from models.exam import Exam
from models.question import Question
from models.attempt import ExamAttempt, Answer
from services.exam_service import ExamService
from services.result_service import ResultService


class ExamTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        # Create Admin
        self.admin = User(full_name='Admin User', email='admin@test.com', role='admin')
        self.admin.set_password('Admin@123')
        db.session.add(self.admin)

        # Create Student
        self.student = User(full_name='Student User', email='student@test.com', role='student', registration_number='STU-001')
        self.student.set_password('Student@123')
        db.session.add(self.student)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_exam_and_question_creation(self):
        exam = Exam(
            title='Unit Test Exam',
            subject='Testing',
            duration_minutes=30,
            total_marks=20,
            passing_marks=10,
            status='published'
        )
        db.session.add(exam)
        db.session.commit()

        q1 = Question(
            exam_id=exam.id,
            question_text='What is 2+2?',
            option_a='3', option_b='4', option_c='5', option_d='6',
            correct_answer='B', marks=10.0, negative_marks=2.0
        )
        q2 = Question(
            exam_id=exam.id,
            question_text='What is 3*3?',
            option_a='9', option_b='6', option_c='12', option_d='15',
            correct_answer='A', marks=10.0, negative_marks=2.0
        )
        db.session.add_all([q1, q2])
        db.session.commit()

        self.assertEqual(len(exam.questions), 2)
        self.assertEqual(exam.calculated_total_marks, 20.0)

    def test_exam_attempt_and_evaluation(self):
        exam = Exam(
            title='Eval Test Exam',
            subject='Algorithms',
            duration_minutes=30,
            total_marks=20,
            passing_marks=10,
            status='published'
        )
        db.session.add(exam)
        db.session.commit()

        q1 = Question(exam_id=exam.id, question_text='Q1', option_a='A', option_b='B', option_c='C', option_d='D', correct_answer='A', marks=10.0, negative_marks=2.0)
        q2 = Question(exam_id=exam.id, question_text='Q2', option_a='A', option_b='B', option_c='C', option_d='D', correct_answer='B', marks=10.0, negative_marks=2.0)
        db.session.add_all([q1, q2])
        db.session.commit()

        # Start attempt
        attempt, err = ExamService.start_or_resume_attempt(exam.id, self.student.id)
        self.assertIsNone(err)
        self.assertIsNotNone(attempt)
        self.assertEqual(attempt.status, 'in_progress')

        # Save answers: Q1 correct, Q2 wrong
        ok1, msg1 = ExamService.save_answer(attempt.id, q1.id, 'A')
        ok2, msg2 = ExamService.save_answer(attempt.id, q2.id, 'C')
        self.assertTrue(ok1)
        self.assertTrue(ok2)

        # Submit attempt
        submitted, msg = ResultService.calculate_and_submit_attempt(attempt.id)
        self.assertEqual(submitted.status, 'submitted')
        # Score = 10 (Q1 correct) - 2 (Q2 wrong negative) = 8
        self.assertEqual(submitted.score, 8.0)
        self.assertEqual(submitted.percentage, 40.0)
        self.assertFalse(submitted.is_passed)  # Passing marks was 10

        # Attempt is locked
        ok3, _ = ExamService.save_answer(attempt.id, q1.id, 'B')
        self.assertFalse(ok3)


if __name__ == '__main__':
    unittest.main()
