from datetime import datetime
from extensions import db


class ProctoringEvent(db.Model):
    __tablename__ = 'proctoring_events'

    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('exam_attempts.id', ondelete='CASCADE'), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)
    # Types: NO_FACE, MULTIPLE_FACES, FACE_NOT_CENTERED, HEAD_MOVEMENT, LOOKING_AWAY,
    # CAMERA_DISABLED, FULLSCREEN_EXIT, TAB_SWITCH, COPY_ATTEMPT, PASTE_ATTEMPT,
    # RIGHT_CLICK, WINDOW_BLUR, SUSPICIOUS_ACTIVITY
    severity = db.Column(db.String(20), nullable=False, default='LOW')  # LOW, MEDIUM, HIGH, CRITICAL
    description = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    confidence = db.Column(db.Float, default=1.0)
    screenshot_path = db.Column(db.String(256), nullable=True)
    is_demo = db.Column(db.Boolean, default=False)

    # Relationships
    attempt = db.relationship('ExamAttempt', back_populates='proctoring_events')

    def to_dict(self):
        return {
            'id': self.id,
            'attempt_id': self.attempt_id,
            'event_type': self.event_type,
            'severity': self.severity,
            'description': self.description,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'formatted_time': self.timestamp.strftime('%H:%M:%S') if self.timestamp else '',
            'confidence': round(self.confidence, 2),
            'screenshot_path': self.screenshot_path,
            'is_demo': self.is_demo
        }

    def __repr__(self):
        return f"<ProctoringEvent {self.id}: {self.event_type} ({self.severity})>"


class ProctoringSession(db.Model):
    __tablename__ = 'proctoring_sessions'

    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('exam_attempts.id', ondelete='CASCADE'), unique=True, nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ended_at = db.Column(db.DateTime, nullable=True)
    total_events = db.Column(db.Integer, default=0)
    risk_score = db.Column(db.Integer, default=0)
    final_status = db.Column(db.String(30), default='CLEARED')
    # CLEARED, LOW_RISK, MEDIUM_RISK, HIGH_RISK, CRITICAL_RISK, UNDER_REVIEW

    # Relationships
    attempt = db.relationship('ExamAttempt', back_populates='proctoring_session')

    @property
    def risk_level(self) -> str:
        if self.risk_score <= 20:
            return 'LOW'
        elif self.risk_score <= 50:
            return 'MEDIUM'
        elif self.risk_score <= 80:
            return 'HIGH'
        else:
            return 'CRITICAL'

    @property
    def risk_badge_class(self) -> str:
        level = self.risk_level
        if level == 'LOW':
            return 'success'
        elif level == 'MEDIUM':
            return 'warning'
        elif level == 'HIGH':
            return 'danger'
        else:
            return 'dark'

    def to_dict(self):
        return {
            'id': self.id,
            'attempt_id': self.attempt_id,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'total_events': self.total_events,
            'risk_score': self.risk_score,
            'risk_level': self.risk_level,
            'risk_badge_class': self.risk_badge_class,
            'final_status': self.final_status
        }

    def __repr__(self):
        return f"<ProctoringSession {self.id} for Attempt {self.attempt_id} (Score: {self.risk_score})>"
