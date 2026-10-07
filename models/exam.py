from datetime import datetime
from extensions import db


class Exam(db.Model):
    __tablename__ = 'exams'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    subject = db.Column(db.String(100), nullable=False, default='Computer Science')
    duration_minutes = db.Column(db.Integer, nullable=False, default=60)
    total_marks = db.Column(db.Integer, nullable=False, default=100)
    passing_marks = db.Column(db.Integer, nullable=False, default=40)
    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='published')  # 'draft', 'published', 'archived'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    questions = db.relationship('Question', back_populates='exam', cascade='all, delete-orphan', order_by='Question.order')
    attempts = db.relationship('ExamAttempt', back_populates='exam', cascade='all, delete-orphan', lazy='dynamic')

    @property
    def question_count(self) -> int:
        return len(self.questions)

    @property
    def calculated_total_marks(self) -> float:
        return sum(q.marks for q in self.questions) if self.questions else float(self.total_marks)

    def is_available(self) -> bool:
        if self.status != 'published':
            return False
        now = datetime.utcnow()
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return True

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'subject': self.subject,
            'duration_minutes': self.duration_minutes,
            'total_marks': self.total_marks,
            'passing_marks': self.passing_marks,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'question_count': self.question_count,
            'is_available': self.is_available()
        }

    def __repr__(self):
        return f"<Exam {self.id}: {self.title}>"
