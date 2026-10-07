from routes.auth import auth_bp
from routes.student import student_bp
from routes.admin import admin_bp
from routes.exam import exam_bp
from routes.api import api_bp

__all__ = [
    'auth_bp',
    'student_bp',
    'admin_bp',
    'exam_bp',
    'api_bp'
]
