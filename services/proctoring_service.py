import os
import time
import logging
from datetime import datetime
import cv2
from flask import current_app
from extensions import db
from models.attempt import ExamAttempt
from models.proctoring import ProctoringSession, ProctoringEvent
from services.risk_engine import RiskEngine
from ml.proctoring_engine import ProctoringEngine

logger = logging.getLogger(__name__)


class ProctoringService:
    """
    Central proctoring coordinator.
    Processes live frame streams, handles client anomaly events,
    records photographic evidence, and updates session risk profiles.
    """

    _engine = None

    @classmethod
    def get_engine(cls):
        if cls._engine is None:
            demo_mode = current_app.config.get('DEMO_MODE', False) if current_app else False
            cls._engine = ProctoringEngine(demo_mode=demo_mode)
        return cls._engine

    @classmethod
    def process_frame(cls, attempt_id: int, image_b64: str, is_demo: bool = False):
        attempt = db.session.get(ExamAttempt, attempt_id)
        if not attempt or attempt.is_completed:
            return {
                'success': False,
                'message': 'Attempt is not active'
            }

        session = attempt.proctoring_session
        if not session:
            session = ProctoringSession(attempt_id=attempt.id, risk_score=0)
            db.session.add(session)
            db.session.commit()

        engine = cls.get_engine()
        ml_result = engine.process_frame(image_b64, attempt_id=attempt.id, is_demo=is_demo)

        events_logged = []
        new_risk = 0

        # Process ML generated events
        for evt in ml_result.get('events', []):
            event_type = evt['event_type']
            severity = evt['severity']
            description = evt['description']
            confidence = evt.get('confidence', 0.9)

            # Check if screenshot should be saved for severe events
            screenshot_path = None
            if ml_result.get('processed_frame') is not None and severity in ('HIGH', 'CRITICAL', 'MEDIUM'):
                screenshot_path = cls._save_screenshot(
                    attempt.id,
                    event_type,
                    ml_result['processed_frame']
                )

            p_event = ProctoringEvent(
                attempt_id=attempt.id,
                event_type=event_type,
                severity=severity,
                description=description,
                confidence=confidence,
                screenshot_path=screenshot_path,
                is_demo=is_demo
            )
            db.session.add(p_event)
            events_logged.append(p_event)

            # Add risk
            weight = RiskEngine.get_event_weight(event_type)
            new_risk += weight

        if events_logged:
            session.risk_score += new_risk
            session.total_events += len(events_logged)
            attempt.suspicious_activity_count += len(events_logged)
            db.session.commit()

        return {
            'success': True,
            'face_count': ml_result.get('face_count', 0),
            'face_detected': ml_result.get('face_detected', False),
            'head_direction': ml_result.get('head_direction', 'CENTER'),
            'gaze_direction': ml_result.get('gaze_direction', 'CENTER'),
            'is_centered': ml_result.get('is_centered', True),
            'lighting_ok': ml_result.get('lighting_ok', True),
            'phone_detected': ml_result.get('phone_detected', False),
            'phone_boxes': ml_result.get('phone_boxes', []),
            'heatmap_active': ml_result.get('heatmap_active', False),
            'heatmap_intensity': ml_result.get('heatmap_intensity', 0.0),
            'risk_score': session.risk_score,
            'risk_level': session.risk_level,
            'status': ml_result.get('status', 'NORMAL'),
            'events_count': len(events_logged),
            'latest_events': [e.to_dict() for e in events_logged]
        }

    @classmethod
    def log_client_event(cls, attempt_id: int, event_type: str, description: str = '', image_b64: str = None, is_demo: bool = False):
        attempt = db.session.get(ExamAttempt, attempt_id)
        if not attempt or attempt.is_completed:
            return {'success': False, 'message': 'Attempt is not active'}

        session = attempt.proctoring_session
        if not session:
            session = ProctoringSession(attempt_id=attempt.id, risk_score=0)
            db.session.add(session)

        severity = RiskEngine.get_event_severity(event_type)
        weight = RiskEngine.get_event_weight(event_type)

        screenshot_path = None
        if image_b64:
            engine = cls.get_engine()
            decoded = engine.face_detector.decode_image(image_b64)
            if decoded is not None:
                screenshot_path = cls._save_screenshot(attempt.id, event_type, decoded)

        if not description:
            description = f"Detected client-side security event: {event_type.replace('_', ' ').title()}"

        event = ProctoringEvent(
            attempt_id=attempt.id,
            event_type=event_type,
            severity=severity,
            description=description,
            confidence=1.0,
            screenshot_path=screenshot_path,
            is_demo=is_demo
        )
        db.session.add(event)

        session.risk_score += weight
        session.total_events += 1
        attempt.suspicious_activity_count += 1

        db.session.commit()

        return {
            'success': True,
            'event': event.to_dict(),
            'current_risk_score': session.risk_score,
            'current_risk_level': session.risk_level
        }

    @staticmethod
    def _save_screenshot(attempt_id: int, event_type: str, frame_cv) -> str:
        """
        Saves snapshot evidence to uploads/screenshots directory.
        Format: attemptID_timestamp_event.jpg
        """
        try:
            base_dir = current_app.config.get('UPLOAD_FOLDER', 'uploads')
            screenshot_dir = os.path.join(base_dir, 'screenshots')
            os.makedirs(screenshot_dir, exist_ok=True)

            timestamp_str = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')[:19]
            filename = f"attempt{attempt_id}_{timestamp_str}_{event_type.lower()}.jpg"
            file_path = os.path.join(screenshot_dir, filename)

            # Save JPEG with 80% quality for optimal storage
            cv2.imwrite(file_path, frame_cv, [cv2.IMWRITE_JPEG_QUALITY, 80])

            # Return relative path for web serving
            return f"uploads/screenshots/{filename}"
        except Exception as e:
            logger.error(f"Failed to save screenshot: {e}")
            return None
