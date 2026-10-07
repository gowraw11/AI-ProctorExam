import logging
import cv2
import numpy as np

logger = logging.getLogger(__name__)


class GazeDetector:
    """
    Approximate gaze direction estimator.
    Analyzes horizontal pupil/dark-pixel centroid in detected eye regions.
    Designed with conservative thresholds to prevent false accusations.
    """

    def __init__(self):
        try:
            self.eye_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_eye.xml'
            )
        except Exception as e:
            logger.warning(f"Failed to load eye cascade: {e}")
            self.eye_cascade = None

    def estimate_gaze(self, frame, bounding_box):
        """
        Estimates gaze direction: 'CENTER', 'LEFT', or 'RIGHT'.
        Returns direction and confidence.
        """
        if frame is None or not bounding_box:
            return "CENTER", 0.60

        x, y, w, h = bounding_box
        H, W = frame.shape[:2]

        x = max(0, x)
        y = max(0, y)
        w = min(w, W - x)
        h = min(h, H - y)

        if w < 20 or h < 20 or self.eye_cascade is None or self.eye_cascade.empty():
            return "CENTER", 0.60

        face_roi = frame[y:y+h, x:x+w]
        gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
        # Upper portion for eyes
        eye_zone = gray[:int(h * 0.55), :]

        eyes = self.eye_cascade.detectMultiScale(eye_zone, scaleFactor=1.1, minNeighbors=3, minSize=(15, 15))
        if len(eyes) == 0:
            return "CENTER", 0.60

        # Sort eyes left to right
        eyes = sorted(eyes, key=lambda b: b[0])
        gaze_votes = []

        for (ex, ey, ew, eh) in eyes[:2]:
            eye_roi = eye_zone[ey:ey+eh, ex:ex+ew]
            if eye_roi.shape[0] < 8 or eye_roi.shape[1] < 8:
                continue

            # Threshold to find darkest region (pupil)
            eye_blur = cv2.GaussianBlur(eye_roi, (5, 5), 0)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(eye_blur)

            # Pupil relative horizontal position in eye
            pupil_rel_x = min_loc[0] / float(ew)

            if pupil_rel_x < 0.32:
                gaze_votes.append("LEFT")
            elif pupil_rel_x > 0.68:
                gaze_votes.append("RIGHT")
            else:
                gaze_votes.append("CENTER")

        if not gaze_votes:
            return "CENTER", 0.60

        # Tally votes
        if gaze_votes.count("LEFT") > gaze_votes.count("CENTER") and gaze_votes.count("LEFT") >= 1:
            return "LEFT", 0.70
        elif gaze_votes.count("RIGHT") > gaze_votes.count("CENTER") and gaze_votes.count("RIGHT") >= 1:
            return "RIGHT", 0.70

        return "CENTER", 0.85
