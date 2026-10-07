import os
from flask import Flask, render_template, send_from_directory, redirect, url_for
from flask_login import current_user
from config import config_by_name, Config
from extensions import db, login_manager, cors
from routes import auth_bp, student_bp, admin_bp, exam_bp, api_bp


def create_app(config_name='default'):
    """Application factory for Online Examination and Proctoring System."""
    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, Config))

    # Ensure directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['SCREENSHOT_FOLDER'], exist_ok=True)
    os.makedirs(app.config['PROFILE_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.root_path, 'instance'), exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    cors.init_app(app)

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(exam_bp)
    app.register_blueprint(api_bp)

    # Static file route for uploaded screenshots & evidence
    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    # Landing page
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            if current_user.is_admin:
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('student.dashboard'))
        return render_template('landing.html')

    # About Project & Architecture Page for Final Year CS/MCA Presentation
    @app.route('/about')
    def about():
        return render_template('about.html')

    # Error Handlers
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500

    # Global Template Context
    @app.context_processor
    def inject_global_vars():
        return {
            'app_title': 'AI-Powered Online Examination Portal',
            'app_subtitle': 'Machine Learning Based Secure Examination Platform',
            'current_year': 2026,
            'demo_mode': app.config.get('DEMO_MODE', False)
        }

    return app


app = create_app(os.getenv('FLASK_ENV', 'development'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    print("=" * 60)
    print("AI-POWERED ONLINE EXAMINATION AND PROCTORING SYSTEM")
    print("Server starting at http://127.0.0.1:5000")
    print("=" * 60)
    app.run(host='127.0.0.1', port=5000, debug=True)
