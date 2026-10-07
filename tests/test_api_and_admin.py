import unittest
import json
from app import create_app
from extensions import db
from models.user import User
from models.exam import Exam
from models.question import Question
from models.attempt import ExamAttempt, Answer
from models.proctoring import ProctoringSession


class ApiAndAdminTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        # Admin
        self.admin = User(full_name='Admin Lead', email='admin@test.com', role='admin')
        self.admin.set_password('Admin@123')
        db.session.add(self.admin)

        # Student
        self.student = User(full_name='Student Candidate', email='student@test.com', role='student', registration_number='STU-100')
        self.student.set_password('Student@123')
        db.session.add(self.student)

        # Exam
        self.exam = Exam(title='Integration Exam', subject='CS', duration_minutes=60, total_marks=10, passing_marks=5, status='published')
        db.session.add(self.exam)
        db.session.flush()

        self.q1 = Question(exam_id=self.exam.id, question_text='What is 1+1?', option_a='1', option_b='2', option_c='3', option_d='4', correct_answer='B', marks=10.0, order=1)
        db.session.add(self.q1)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def login_student(self):
        return self.client.post('/login', data={'email': 'student@test.com', 'password': 'Student@123'}, follow_redirects=True)

    def login_admin(self):
        return self.client.post('/login', data={'email': 'admin@test.com', 'password': 'Admin@123'}, follow_redirects=True)

    def test_get_exams_api(self):
        res = self.client.get('/api/exams')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(len(data['exams']), 1)

    def test_exam_flow_via_api(self):
        self.login_student()

        # 1. Start exam
        res_start = self.client.post(f'/api/exams/{self.exam.id}/start')
        self.assertEqual(res_start.status_code, 200)
        start_data = res_start.get_json()
        self.assertTrue(start_data['success'])
        attempt_id = start_data['attempt_id']

        # 2. Check status
        res_status = self.client.get(f'/api/exams/{self.exam.id}/status')
        self.assertEqual(res_status.status_code, 200)
        self.assertTrue(res_status.get_json()['is_active'])

        # 3. Answer question
        res_ans = self.client.post(f'/api/exams/{self.exam.id}/answer', json={
            'attempt_id': attempt_id,
            'question_id': self.q1.id,
            'selected_answer': 'B'
        })
        self.assertEqual(res_ans.status_code, 200)
        self.assertTrue(res_ans.get_json()['success'])

        # 4. Proctoring Event
        res_evt = self.client.post('/api/proctoring/event', json={
            'attempt_id': attempt_id,
            'event_type': 'TAB_SWITCH',
            'description': 'Student switched window'
        })
        self.assertEqual(res_evt.status_code, 200)
        self.assertTrue(res_evt.get_json()['success'])

        # 5. Submit exam
        res_sub = self.client.post(f'/api/exams/{self.exam.id}/submit', json={
            'attempt_id': attempt_id
        })
        self.assertEqual(res_sub.status_code, 200)
        sub_data = res_sub.get_json()
        self.assertTrue(sub_data['success'])
        self.assertEqual(sub_data['attempt']['score'], 10.0)
        self.assertTrue(sub_data['attempt']['is_passed'])

        # 6. Get results API
        res_res = self.client.get(f'/api/results/{attempt_id}')
        self.assertEqual(res_res.status_code, 200)
        self.assertEqual(res_res.get_json()['score'], 10.0)

    def test_admin_dashboard_and_reports(self):
        self.login_admin()

        # Admin dashboard
        res_dash = self.client.get('/admin/dashboard')
        self.assertEqual(res_dash.status_code, 200)

        # Admin statistics API
        res_stat = self.client.get('/api/admin/statistics')
        self.assertEqual(res_stat.status_code, 200)
        self.assertTrue(res_stat.get_json()['success'])

        # Admin CSV export
        res_csv = self.client.get('/admin/reports/export-csv')
        self.assertEqual(res_csv.status_code, 200)
        self.assertEqual(res_csv.mimetype, 'text/csv')

        # Admin PDF export
        res_pdf = self.client.get('/admin/reports/export-pdf')
        self.assertEqual(res_pdf.status_code, 200)
        self.assertEqual(res_pdf.mimetype, 'application/pdf')


if __name__ == '__main__':
    unittest.main()
