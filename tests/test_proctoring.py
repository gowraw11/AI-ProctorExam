import unittest
import numpy as np
import cv2
from app import create_app
from extensions import db
from models.user import User
from models.exam import Exam
from models.attempt import ExamAttempt
from models.proctoring import ProctoringSession, ProctoringEvent
from services.risk_engine import RiskEngine
from services.proctoring_service import ProctoringService
from ml.proctoring_engine import ProctoringEngine


class ProctoringTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        self.student = User(full_name='Test Candidate', email='cand@test.com', role='student')
        self.student.set_password('Pass@123')
        db.session.add(self.student)

        self.exam = Exam(title='Proctor Test', subject='AI', duration_minutes=30, total_marks=50, passing_marks=20)
        db.session.add(self.exam)
        db.session.commit()

        self.attempt = ExamAttempt(exam_id=self.exam.id, student_id=self.student.id, status='in_progress')
        db.session.add(self.attempt)
        db.session.flush()

        self.session = ProctoringSession(attempt_id=self.attempt.id, risk_score=0)
        db.session.add(self.session)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_risk_weight_calculations(self):
        self.assertEqual(RiskEngine.get_event_weight('NO_FACE'), 10)
        self.assertEqual(RiskEngine.get_event_weight('MULTIPLE_FACES'), 30)
        self.assertEqual(RiskEngine.get_event_weight('TAB_SWITCH'), 15)
        self.assertEqual(RiskEngine.get_event_weight('FULLSCREEN_EXIT'), 15)
        self.assertEqual(RiskEngine.get_event_weight('COPY_ATTEMPT'), 20)

        # Risk levels
        self.assertEqual(RiskEngine.calculate_level(15), 'LOW')
        self.assertEqual(RiskEngine.calculate_level(35), 'MEDIUM')
        self.assertEqual(RiskEngine.calculate_level(65), 'HIGH')
        self.assertEqual(RiskEngine.calculate_level(85), 'CRITICAL')

    def test_log_client_events_and_risk_increment(self):
        # 1. Log Tab Switch
        res1 = ProctoringService.log_client_event(self.attempt.id, 'TAB_SWITCH', 'Candidate switched browser tab')
        self.assertTrue(res1['success'])
        self.assertEqual(res1['current_risk_score'], 15)
        self.assertEqual(res1['current_risk_level'], 'LOW')

        # 2. Log Fullscreen Exit
        res2 = ProctoringService.log_client_event(self.attempt.id, 'FULLSCREEN_EXIT', 'Candidate left fullscreen')
        self.assertTrue(res2['success'])
        # 15 + 15 = 30 -> MEDIUM
        self.assertEqual(res2['current_risk_score'], 30)
        self.assertEqual(res2['current_risk_level'], 'MEDIUM')

        # 3. Log Multiple Faces via client
        res3 = ProctoringService.log_client_event(self.attempt.id, 'MULTIPLE_FACES', 'Multiple individuals detected')
        # 30 + 30 = 60 -> HIGH
        self.assertEqual(res3['current_risk_score'], 60)
        self.assertEqual(res3['current_risk_level'], 'HIGH')

        # Verify DB counts
        events = ProctoringEvent.query.filter_by(attempt_id=self.attempt.id).all()
        self.assertEqual(len(events), 3)
        self.assertEqual(self.attempt.suspicious_activity_count, 3)

    def test_phone_detector_and_unwanted_region(self):
        from ml.phone_detector import PhoneDetector

        detector = PhoneDetector()
        self.assertEqual(RiskEngine.get_event_weight('PHONE_DETECTED'), 30)

        # Synthesize a camera frame with a smartphone rectangle in lower unwanted zone
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # Phone: width=70, height=140 (aspect ratio 2.0:1) placed in desk region (y=260)
        cv2.rectangle(frame, (280, 260), (350, 400), (220, 220, 220), -1)

        result, annotated = detector.detect(frame, face_boxes=[])
        self.assertTrue(result['phone_detected'])
        self.assertGreater(len(result['boxes']), 0)
        self.assertIsNotNone(annotated)

        # Log event through service
        res_svc = ProctoringService.log_client_event(self.attempt.id, 'PHONE_DETECTED', 'Mobile phone detected in unwanted region')
        self.assertTrue(res_svc['success'])
        self.assertEqual(res_svc['event']['severity'], 'HIGH')

    def test_face_detector_ensemble_and_skin_check(self):
        from ml.face_detector import FaceDetector
        detector = FaceDetector()

        # Non-skin ROI (pure blue)
        blue_roi = np.full((100, 100, 3), [255, 0, 0], dtype=np.uint8)
        self.assertEqual(detector.check_skin(blue_roi), 0.0)

        # NMS merging overlapping duplicate boxes
        overlapping_boxes = [[100, 100, 80, 80], [105, 103, 78, 78]]
        merged = detector.nms(overlapping_boxes)
        self.assertEqual(len(merged), 1)

    def test_calibrated_no_face_grace_period(self):
        engine = ProctoringEngine()
        blank_frame = np.zeros((270, 360, 3), dtype=np.uint8)

        # Tick 1: Frame with no face (2s elapsed) -> Grace period, status NORMAL, no events
        r1 = engine.process_frame(blank_frame, attempt_id=999)
        self.assertEqual(len(r1['events']), 0)
        self.assertEqual(r1['risk_score_delta'], 0)
        self.assertEqual(r1['status'], 'NORMAL')

        # Tick 2: Frame with no face (4s elapsed) -> Grace period, status NORMAL
        r2 = engine.process_frame(blank_frame, attempt_id=999)
        self.assertEqual(len(r2['events']), 0)
        self.assertEqual(r2['status'], 'NORMAL')

        # Tick 3: Frame with no face (6s elapsed) -> Soft caution warning, no disciplinary penalty
        r3 = engine.process_frame(blank_frame, attempt_id=999)
        self.assertEqual(len(r3['events']), 0)
        self.assertEqual(r3['status'], 'WARNING')

        # Tick 4: 8s elapsed
        r4 = engine.process_frame(blank_frame, attempt_id=999)
        self.assertEqual(len(r4['events']), 0)

        # Tick 5: 10s elapsed -> Sustained absence violation!
        r5 = engine.process_frame(blank_frame, attempt_id=999)
        self.assertEqual(len(r5['events']), 1)
        self.assertEqual(r5['events'][0]['event_type'], 'NO_FACE')
        self.assertEqual(r5['events'][0]['severity'], 'HIGH')
        self.assertEqual(r5['risk_score_delta'], 10)
        self.assertEqual(r5['status'], 'VIOLATION')

        # Tick 6: Cooldown active -> No duplicate violation event immediately on next frame
        r6 = engine.process_frame(blank_frame, attempt_id=999)
        self.assertEqual(len(r6['events']), 0)


if __name__ == '__main__':
    unittest.main()
