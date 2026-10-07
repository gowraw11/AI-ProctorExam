import logging
from collections import deque
import cv2
import numpy as np

logger = logging.getLogger(__name__)


class HeadPoseEstimator:
    """
    Estimates approximate head direction using facial geometric ratios
    and eye/nose location cascades. Tracks sustained movement.
    """

    def __init__(self, history_size=4):
        self.history_size = history_size
        self.pose_history = deque(maxlen=history_size)

        try:
            self.eye_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_eye.xml'
            )
        except Exception as e:
            logger.warning(f"Failed to load eye cascade: {e}")
            self.eye_cascade = None

    def estimate_direction(self, frame, bounding_box):
        """
        Determines if head is CENTER, LEFT, RIGHT, UP, or DOWN.
        """
        if frame is None or not bounding_box:
            return "UNKNOWN", 0.0

        x, y, w, h = bounding_box
        H, W = frame.shape[:2]

        # Clamp bounding box
        x = max(0, x)
        y = max(0, y)
        w = min(w, W - x)
        h = min(h, H - y)

        if w < 20 or h < 20:
            return "UNKNOWN", 0.0

        face_roi = frame[y:y+h, x:x+w]
        gray_roi = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)

        direction = "CENTER"
        confidence = 0.80

        # Method 1: Face Box Positioning in frame
        # If the face is shifted strongly to the extreme edges of the frame
        face_cx = x + w / 2.0
        face_cy = y + h / 2.0
        rel_x = face_cx / float(W)
        rel_y = face_cy / float(H)

        if rel_x < 0.28:
            direction = "LEFT"
            confidence = 0.85
        elif rel_x > 0.72:
            direction = "RIGHT"
            confidence = 0.85
        elif rel_y < 0.22:
            direction = "UP"
            confidence = 0.85
        elif rel_y > 0.78:
            direction = "DOWN"
            confidence = 0.85

        # Method 2: Eye asymmetry inside face region if cascades are available
        if direction == "CENTER" and self.eye_cascade is not None and not self.eye_cascade.empty():
            # Upper 60% of face for eyes
            eyes_roi = gray_roi[:int(h * 0.6), :]
            eyes = self.eye_cascade.detectMultiScale(eyes_roi, scaleFactor=1.1, minNeighbors=3, minSize=(15, 15))

            if len(eyes) == 2:
                eye1_x = eyes[0][0] + eyes[0][2] / 2.0
                eye2_x = eyes[1][0] + eyes[1][2] / 2.0
                mid_eyes_x = (eye1_x + eye2_x) / 2.0
                face_mid_x = w / 2.0

                # Ratio of eye midpoint to face center
                dx = (mid_eyes_x - face_mid_x) / face_mid_x
                if dx < -0.22:
                    direction = "LEFT"
                    confidence = 0.88
                elif dx > 0.22:
                    direction = "RIGHT"
                    confidence = 0.88
            elif len(eyes) == 1:
                # One eye visible often implies head turned
                eye_cx = eyes[0][0] + eyes[0][2] / 2.0
                if eye_cx < w * 0.35:
                    direction = "LEFT"
                    confidence = 0.75
                elif eye_cx > w * 0.65:
                    direction = "RIGHT"
                    confidence = 0.75

        # Record in history
        self.pose_history.append(direction)

        # Check for sustained movement (at least 2 consecutive non-center frames)
        sustained = False
        if len(self.pose_history) >= 2:
            recent_non_center = [p for p in list(self.pose_history)[-2:] if p not in ("CENTER", "UNKNOWN")]
            if len(recent_non_center) >= 2 and len(set(recent_non_center)) == 1:
                sustained = True
                direction = recent_non_center[0]

        return direction, confidence, sustained

    def reset(self):
        self.pose_history.clear()
