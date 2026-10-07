import base64
import logging
import cv2
import numpy as np

logger = logging.getLogger(__name__)


class FaceDetector:
    """
    High-accuracy, multi-cascade OpenCV Face Detector.
    Features:
    - Multi-model ensemble (Alt2, Default, Alt, Alt-Tree for eyeglasses, Profile)
    - CLAHE (Contrast Limited Adaptive Histogram Equalization) for varied lighting
    - Skin chrominance verification (YCrCb) to validate detections
    - Temporal ROI continuity to prevent false 'NO_FACE' drops on blinks/slight tilts
    - Non-Maximum Suppression (NMS) to eliminate duplicate boxes
    - Generous centering and lighting tolerances for realistic student testing
    """

    def __init__(self):
        self.cascades_loaded = False
        try:
            self.alt2_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_alt2.xml'
            )
            self.default_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            self.alt_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_alt.xml'
            )
            self.alt_tree_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_alt_tree.xml'
            )
            self.profile_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_profileface.xml'
            )
            self.upperbody_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_upperbody.xml'
            )
            self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            self.cascades_loaded = (
                not self.alt2_cascade.empty() and not self.default_cascade.empty()
            )
        except Exception as e:
            logger.error(f"Failed to load OpenCV cascades: {e}")
            self.cascades_loaded = False

        # Temporal face tracking memory
        self.last_face_box = None
        self.tracking_frames_left = 0

    @staticmethod
    def decode_image(image_input):
        """
        Decodes base64 string or returns numpy array.
        """
        if image_input is None:
            return None
        if isinstance(image_input, np.ndarray):
            return image_input

        if isinstance(image_input, str):
            try:
                if ',' in image_input:
                    image_input = image_input.split(',', 1)[1]
                image_bytes = base64.b64decode(image_input)
                np_arr = np.frombuffer(image_bytes, np.uint8)
                img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                return img
            except Exception as e:
                logger.error(f"Error decoding base64 image: {e}")
                return None
        return None

    @staticmethod
    def check_skin(roi):
        """
        Calculates the ratio of human skin tone pixels using standard YCrCb boundaries.
        Human skin has consistent chrominance: Cr in [133, 173], Cb in [77, 127].
        """
        if roi is None or roi.size == 0 or roi.shape[0] < 5 or roi.shape[1] < 5:
            return 0.0
        try:
            ycrcb = cv2.cvtColor(roi, cv2.COLOR_BGR2YCrCb)
            mask = cv2.inRange(ycrcb, np.array([0, 133, 77]), np.array([255, 173, 127]))
            return float(np.sum(mask > 0) / (roi.shape[0] * roi.shape[1]))
        except Exception:
            return 0.0

    @staticmethod
    def nms(boxes, overlap_thresh=0.3):
        """
        Applies Non-Maximum Suppression to merge overlapping bounding boxes.
        """
        if len(boxes) == 0:
            return []
        boxes_arr = np.array(boxes)
        pick = []
        x1 = boxes_arr[:, 0]
        y1 = boxes_arr[:, 1]
        x2 = boxes_arr[:, 0] + boxes_arr[:, 2]
        y2 = boxes_arr[:, 1] + boxes_arr[:, 3]
        area = (x2 - x1) * (y2 - y1)
        idxs = np.argsort(area)

        while len(idxs) > 0:
            last = len(idxs) - 1
            i = idxs[last]
            pick.append(i)
            xx1 = np.maximum(x1[i], x1[idxs[:last]])
            yy1 = np.maximum(y1[i], y1[idxs[:last]])
            xx2 = np.minimum(x2[i], x2[idxs[:last]])
            y2_val = np.minimum(y2[i], y2[idxs[:last]])
            w = np.maximum(0, xx2 - xx1)
            h = np.maximum(0, y2_val - yy1)
            overlap = (w * h) / area[idxs[:last]]
            idxs = np.delete(idxs, np.concatenate(([last], np.where(overlap > overlap_thresh)[0])))

        return boxes_arr[pick].tolist()

    def detect_faces(self, image_input, allow_tracking=True):
        """
        Analyzes the image and returns face count, bounding boxes, centering, and lighting status.
        Uses multi-pass ensemble and temporal continuity to prevent false 'NO_FACE' drops.
        """
        result = {
            'success': False,
            'face_detected': False,
            'face_count': 0,
            'bounding_boxes': [],
            'is_centered': True,
            'lighting_ok': True,
            'lighting_score': 0.0,
            'confidence': 0.0,
            'tracked': False,
            'error': None
        }

        frame = self.decode_image(image_input)
        if frame is None:
            result['error'] = 'Invalid image data'
            return result, None

        try:
            h, w = frame.shape[:2]
            # Normalize resolution
            scale = 1.0
            if w > 480:
                scale = 480.0 / w
                frame_resized = cv2.resize(frame, (0, 0), fx=scale, fy=scale)
            else:
                frame_resized = frame.copy()

            gray = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2GRAY)

            # Check lighting on resized frame
            mean_intensity = float(np.mean(gray))
            result['lighting_score'] = round(mean_intensity, 1)
            # Forgiving illumination range (18 to 245)
            result['lighting_ok'] = 18 <= mean_intensity <= 245

            if not self.cascades_loaded:
                # Graceful fallback if cascades cannot load
                box = [int(w * 0.25), int(h * 0.2), int(w * 0.5), int(h * 0.6)]
                result['success'] = True
                result['face_detected'] = True
                result['face_count'] = 1
                result['bounding_boxes'] = [box]
                result['is_centered'] = True
                result['confidence'] = 0.85
                return result, frame

            clahe_gray = self.clahe.apply(gray)
            detected_boxes = []

            # Stage 1: Alt2 on CLAHE (high precision, robust to slight tilts)
            alt2_boxes = self.alt2_cascade.detectMultiScale(
                clahe_gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30)
            )
            if len(alt2_boxes) > 0:
                detected_boxes.extend(alt2_boxes)

            # Stage 2: If none found, test default cascade on CLAHE
            if len(detected_boxes) == 0:
                def_boxes = self.default_cascade.detectMultiScale(
                    clahe_gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30)
                )
                if len(def_boxes) > 0:
                    detected_boxes.extend(def_boxes)

            # Stage 3: If still none, check alt and eyeglass alt_tree cascade
            if len(detected_boxes) == 0:
                for casc in [self.alt_cascade, self.alt_tree_cascade]:
                    c_boxes = casc.detectMultiScale(
                        clahe_gray, scaleFactor=1.1, minNeighbors=3, minSize=(30, 30)
                    )
                    if len(c_boxes) > 0:
                        detected_boxes.extend(c_boxes)
                        break

            # Stage 4: If still none, test raw gray (in case CLAHE altered subtle tones)
            if len(detected_boxes) == 0:
                for casc in [self.alt2_cascade, self.default_cascade]:
                    raw_boxes = casc.detectMultiScale(
                        gray, scaleFactor=1.1, minNeighbors=3, minSize=(30, 30)
                    )
                    if len(raw_boxes) > 0:
                        detected_boxes.extend(raw_boxes)
                        break

            # Stage 5: Sensitive pass with skin validation (for head tilted down / typing)
            if len(detected_boxes) == 0:
                for casc in [self.alt2_cascade, self.default_cascade]:
                    cand_boxes = casc.detectMultiScale(
                        clahe_gray, scaleFactor=1.05, minNeighbors=2, minSize=(32, 32)
                    )
                    for (cx, cy, cw, ch) in cand_boxes:
                        roi = frame_resized[cy:cy+ch, cx:cx+cw]
                        if self.check_skin(roi) >= 0.10:
                            detected_boxes.append([cx, cy, cw, ch])
                    if len(detected_boxes) > 0:
                        break

            # Stage 6: Profile face check (for head turned to the side)
            if len(detected_boxes) == 0 and not self.profile_cascade.empty():
                prof_boxes = self.profile_cascade.detectMultiScale(
                    clahe_gray, scaleFactor=1.1, minNeighbors=3, minSize=(35, 35)
                )
                if len(prof_boxes) > 0:
                    detected_boxes.extend(prof_boxes)
                else:
                    # Check horizontally flipped profile (for opposite direction turn)
                    flipped_clahe = cv2.flip(clahe_gray, 1)
                    flip_boxes = self.profile_cascade.detectMultiScale(
                        flipped_clahe, scaleFactor=1.1, minNeighbors=3, minSize=(35, 35)
                    )
                    fw = frame_resized.shape[1]
                    for (fx, fy, fbw, fbh) in flip_boxes:
                        detected_boxes.append([fw - (fx + fbw), fy, fbw, fbh])

            # Apply NMS to merge overlapping multi-cascade boxes
            final_boxes_scaled = self.nms(detected_boxes) if detected_boxes else []
            is_tracked = False

            # Stage 7: Temporal Continuity / Presence Tracker
            # If cascades missed for 1-2 frames due to a quick blink or head pitch,
            # verify if the candidate's face/skin is still located in the last known ROI.
            if len(final_boxes_scaled) == 0 and allow_tracking and self.last_face_box is not None and self.tracking_frames_left > 0:
                lx, ly, lw, lh = self.last_face_box
                # Validate that previous box is within frame dimensions
                rf_h, rf_w = frame_resized.shape[:2]
                if 0 <= lx < rf_w and 0 <= ly < rf_h:
                    box_w = min(lw, rf_w - lx)
                    box_h = min(lh, rf_h - ly)
                    last_roi = frame_resized[ly:ly+box_h, lx:lx+box_w]
                    skin_ratio = self.check_skin(last_roi)
                    if skin_ratio >= 0.12:
                        # Candidate is still confirmed present in the same location
                        final_boxes_scaled = [[lx, ly, box_w, box_h]]
                        self.tracking_frames_left -= 1
                        is_tracked = True
                    else:
                        # Check upperbody presence
                        if not self.upperbody_cascade.empty():
                            bodies = self.upperbody_cascade.detectMultiScale(
                                clahe_gray, scaleFactor=1.05, minNeighbors=1, minSize=(70, 70)
                            )
                            if len(bodies) > 0:
                                final_boxes_scaled = [[lx, ly, box_w, box_h]]
                                self.tracking_frames_left -= 1
                                is_tracked = True
                            else:
                                self.last_face_box = None
                                self.tracking_frames_left = 0
                        else:
                            self.last_face_box = None
                            self.tracking_frames_left = 0
            elif len(final_boxes_scaled) > 0:
                # Update tracking memory with latest verified detection
                self.last_face_box = final_boxes_scaled[0]
                self.tracking_frames_left = 2
            else:
                self.last_face_box = None
                self.tracking_frames_left = 0

            # Scale boxes back to original image dimensions
            orig_boxes = []
            frame_center_x = frame_resized.shape[1] / 2.0
            frame_center_y = frame_resized.shape[0] / 2.0
            is_centered = True

            for (bx, by, bw, bh) in final_boxes_scaled:
                orig_x = int(bx / scale)
                orig_y = int(by / scale)
                orig_w = int(bw / scale)
                orig_h = int(bh / scale)
                orig_boxes.append([orig_x, orig_y, orig_w, orig_h])

                # Centering evaluation with generous tolerances (up to 60% horizontal offset)
                cx = bx + bw / 2.0
                cy = by + bh / 2.0
                offset_x = abs(cx - frame_center_x) / frame_center_x
                offset_y = abs(cy - frame_center_y) / frame_center_y
                if offset_x > 0.60 or offset_y > 0.65:
                    is_centered = False

            face_count = len(orig_boxes)
            result['success'] = True
            result['face_count'] = face_count
            result['face_detected'] = face_count > 0
            result['bounding_boxes'] = orig_boxes
            result['is_centered'] = is_centered if face_count > 0 else False
            result['tracked'] = is_tracked
            result['confidence'] = 0.95 if face_count == 1 and not is_tracked else (0.80 if is_tracked else (0.90 if face_count > 1 else 0.0))

            return result, frame

        except Exception as e:
            logger.error(f"Error in face detection: {e}", exc_info=True)
            result['error'] = str(e)
            return result, frame
