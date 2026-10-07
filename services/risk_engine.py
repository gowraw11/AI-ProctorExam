class RiskEngine:
    """
    Evaluates and calculates risk scores, severity, and categorical risk levels
    for proctoring sessions based on logged behavioral events.
    """

    EVENT_WEIGHTS = {
        'NO_FACE': 10,
        'MULTIPLE_FACES': 30,
        'PHONE_DETECTED': 30,
        'UNAUTHORIZED_DEVICE': 25,
        'LOOKING_AWAY': 5,
        'HEAD_MOVEMENT': 5,
        'FACE_NOT_CENTERED': 3,
        'TAB_SWITCH': 15,
        'FULLSCREEN_EXIT': 15,
        'COPY_ATTEMPT': 20,
        'PASTE_ATTEMPT': 20,
        'RIGHT_CLICK': 5,
        'WINDOW_BLUR': 10,
        'CAMERA_DISABLED': 25,
        'SUSPICIOUS_ACTIVITY': 15
    }

    SEVERITY_MAPPING = {
        'MULTIPLE_FACES': 'HIGH',
        'PHONE_DETECTED': 'HIGH',
        'UNAUTHORIZED_DEVICE': 'HIGH',
        'CAMERA_DISABLED': 'HIGH',
        'COPY_ATTEMPT': 'HIGH',
        'PASTE_ATTEMPT': 'HIGH',
        'TAB_SWITCH': 'MEDIUM',
        'FULLSCREEN_EXIT': 'MEDIUM',
        'NO_FACE': 'HIGH',
        'LOOKING_AWAY': 'MEDIUM',
        'WINDOW_BLUR': 'LOW',
        'HEAD_MOVEMENT': 'LOW',
        'FACE_NOT_CENTERED': 'LOW',
        'RIGHT_CLICK': 'LOW',
        'SUSPICIOUS_ACTIVITY': 'MEDIUM'
    }

    @classmethod
    def get_event_weight(cls, event_type: str) -> int:
        return cls.EVENT_WEIGHTS.get(event_type, 5)

    @classmethod
    def get_event_severity(cls, event_type: str) -> str:
        return cls.SEVERITY_MAPPING.get(event_type, 'LOW')

    @classmethod
    def calculate_level(cls, score: int) -> str:
        """
        Risk classification:
        0–20: LOW
        21–50: MEDIUM
        51–80: HIGH
        81+: CRITICAL
        """
        if score <= 20:
            return 'LOW'
        elif score <= 50:
            return 'MEDIUM'
        elif score <= 80:
            return 'HIGH'
        else:
            return 'CRITICAL'

    @classmethod
    def get_badge_class(cls, risk_level: str) -> str:
        mapping = {
            'LOW': 'success',
            'MEDIUM': 'warning',
            'HIGH': 'danger',
            'CRITICAL': 'dark'
        }
        return mapping.get(risk_level, 'secondary')
