from datetime import datetime
from extensions import db


class ExamAttempt(db.Model):
    __tablename__ = 'exam_attempts'

    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id', ondelete='CASCADE'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    submitted_at = db.Column(db.DateTime, nullable=True)
    score = db.Column(db.Float, default=0.0)
    percentage = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='in_progress')  # 'in_progress', 'submitted', 'auto_submitted', 'terminated'
    suspicious_activity_count = db.Column(db.Integer, default=0)

    # Relationships
    exam = db.relationship('Exam', back_populates='attempts')
    student = db.relationship('User', back_populates='attempts')
    answers = db.relationship('Answer', back_populates='attempt', cascade='all, delete-orphan')
    proctoring_session = db.relationship('ProctoringSession', back_populates='attempt', uselist=False, cascade='all, delete-orphan')
    proctoring_events = db.relationship('ProctoringEvent', back_populates='attempt', cascade='all, delete-orphan', order_by='ProctoringEvent.timestamp.desc()')

    @property
    def is_completed(self) -> bool:
        return self.status in ('submitted', 'auto_submitted', 'terminated')

    @property
    def is_passed(self) -> bool:
        if not self.exam:
            return False
        return self.score >= self.exam.passing_marks

    @property
    def duration_seconds_taken(self) -> int:
        if not self.submitted_at:
            delta = datetime.utcnow() - self.started_at
            return int(delta.total_seconds())
        delta = self.submitted_at - self.started_at
        return int(delta.total_seconds())

    @property
    def formatted_time_taken(self) -> str:
        secs = self.duration_seconds_taken
        mins = secs // 60
        rem_secs = secs % 60
        return f"{mins}m {rem_secs}s"

    def to_dict(self):
        return {
            'id': self.id,
            'exam_id': self.exam_id,
            'exam_title': self.exam.title if self.exam else 'Unknown Exam',
            'student_id': self.student_id,
            'student_name': self.student.full_name if self.student else 'Unknown Student',
            'student_email': self.student.email if self.student else '',
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'score': round(self.score, 2),
            'percentage': round(self.percentage, 2),
            'status': self.status,
            'is_passed': self.is_passed,
            'suspicious_activity_count': self.suspicious_activity_count,
            'risk_score': self.proctoring_session.risk_score if self.proctoring_session else 0,
            'risk_level': self.proctoring_session.risk_level if self.proctoring_session else 'LOW'
        }

    def __repr__(self):
        return f"<ExamAttempt {self.id} (Student {self.student_id}, Exam {self.exam_id})>"


class Answer(db.Model):
    __tablename__ = 'answers'

    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('exam_attempts.id', ondelete='CASCADE'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False)
    selected_answer = db.Column(db.String(5), nullable=True)  # 'A', 'B', 'C', 'D'
    is_correct = db.Column(db.Boolean, nullable=True)
    marks_awarded = db.Column(db.Float, default=0.0)

    # Relationships
    attempt = db.relationship('ExamAttempt', back_populates='answers')
    question = db.relationship('Question', back_populates='answers')

    def to_dict(self):
        return {
            'id': self.id,
            'attempt_id': self.attempt_id,
            'question_id': self.question_id,
            'selected_answer': self.selected_answer,
            'is_correct': self.is_correct,
            'marks_awarded': self.marks_awarded
        }

    def __repr__(self):
        return f"<Answer {self.id} for Attempt {self.attempt_id}, Q{self.question_id}>"
