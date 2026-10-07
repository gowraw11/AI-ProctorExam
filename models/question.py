from extensions import db


class Question(db.Model):
    __tablename__ = 'questions'

    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id', ondelete='CASCADE'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.Text, nullable=False)
    option_b = db.Column(db.Text, nullable=False)
    option_c = db.Column(db.Text, nullable=False)
    option_d = db.Column(db.Text, nullable=False)
    correct_answer = db.Column(db.String(5), nullable=False)  # 'A', 'B', 'C', 'D'
    marks = db.Column(db.Float, nullable=False, default=1.0)
    negative_marks = db.Column(db.Float, nullable=False, default=0.0)
    order = db.Column(db.Integer, nullable=False, default=1)

    # Relationships
    exam = db.relationship('Exam', back_populates='questions')
    answers = db.relationship('Answer', back_populates='question', cascade='all, delete-orphan')

    def to_dict(self, include_correct=False):
        data = {
            'id': self.id,
            'exam_id': self.exam_id,
            'question_text': self.question_text,
            'option_a': self.option_a,
            'option_b': self.option_b,
            'option_c': self.option_c,
            'option_d': self.option_d,
            'marks': self.marks,
            'negative_marks': self.negative_marks,
            'order': self.order
        }
        if include_correct:
            data['correct_answer'] = self.correct_answer
        return data

    def __repr__(self):
        return f"<Question {self.id} for Exam {self.exam_id}>"
