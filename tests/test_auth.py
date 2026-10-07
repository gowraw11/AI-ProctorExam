import unittest
from app import create_app
from extensions import db
from models.user import User


class AuthTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_student_registration(self):
        response = self.client.post('/register', data={
            'full_name': 'Test Candidate',
            'registration_number': 'REG-TEST-01',
            'email': 'candidate@test.com',
            'password': 'Password@123',
            'confirm_password': 'Password@123'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        user = User.query.filter_by(email='candidate@test.com').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.full_name, 'Test Candidate')
        self.assertTrue(user.check_password('Password@123'))
        self.assertTrue(user.is_student)
        self.assertFalse(user.is_admin)

    def test_duplicate_registration_prevented(self):
        user = User(full_name='Existing', email='dup@test.com', role='student')
        user.set_password('Pass@123')
        db.session.add(user)
        db.session.commit()

        response = self.client.post('/register', data={
            'full_name': 'Duplicate User',
            'registration_number': 'REG-DUP',
            'email': 'dup@test.com',
            'password': 'Pass@123',
            'confirm_password': 'Pass@123'
        }, follow_redirects=True)

        self.assertIn(b'already exists', response.data)

    def test_login_and_logout(self):
        user = User(full_name='Login Test', email='login@test.com', role='student')
        user.set_password('Secret@123')
        db.session.add(user)
        db.session.commit()

        # Login with correct password
        resp = self.client.post('/login', data={
            'email': 'login@test.com',
            'password': 'Secret@123'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        # Logout
        resp_logout = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(resp_logout.status_code, 200)
        self.assertIn(b'logged out', resp_logout.data.lower())

    def test_role_authorization_isolation(self):
        # Student cannot access admin dashboard
        student = User(full_name='Student User', email='student@test.com', role='student')
        student.set_password('Pass@123')
        db.session.add(student)
        db.session.commit()

        self.client.post('/login', data={'email': 'student@test.com', 'password': 'Pass@123'}, follow_redirects=True)
        admin_resp = self.client.get('/admin/dashboard')
        self.assertEqual(admin_resp.status_code, 403)


if __name__ == '__main__':
    unittest.main()
