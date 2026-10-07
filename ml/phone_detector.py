import os
import logging
import cv2
import numpy as np

logger = logging.getLogger(__name__)


class PhoneDetector:
    """
    High-Accuracy Multi-Engine Mobile Phone & Contraband Device Detector.
    Combines:
    1. YOLOv4-tiny Deep Neural Network (COCO trained for cell phone / handheld devices)
    2. Emissive / Illuminated Screen Detector (detects active glowing phone displays with screen light on)
    3. High-Sensitivity Edge & Bezel Contour Geometry (detects dark phone bodies and handheld slabs)
    4. Thermal Heat Map Synthesis (OpenCV COLORMAP_JET) with multi-tier glowing gradient overlays
    """

    def __init__(self):
        self.min_phone_area = 350
        self.max_phone_area = 60000
        self.streak_counter = 0

        # Load YOLOv4-tiny Deep Learning Model
        self.yolo_net = None
        self.yolo_out_layers = []
        self._init_yolo_model()

    def _init_yolo_model(self):
        weights_path = os.path.join(os.path.dirname(__file__), 'weights', 'yolov4-tiny.weights')
        cfg_path = os.path.join(os.path.dirname(__file__), 'weights', 'yolov4-tiny.cfg')

        if os.path.exists(weights_path) and os.path.exists(cfg_path):
            try:
                self.yolo_net = cv2.dnn.readNetFromDarknet(cfg_path, weights_path)
                self.yolo_net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                self.yolo_net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
                layer_names = self.yolo_net.getLayerNames()
                self.yolo_out_layers = [layer_names[i - 1] for i in self.yolo_net.getUnconnectedOutLayers()]
                logger.info("YOLOv4-tiny phone detection model loaded successfully.")
            except Exception as e:
                logger.warning(f"Could not initialize YOLOv4-tiny: {e}")
                self.yolo_net = None

    def detect(self, frame, face_boxes=None):
        """
        Scans frame for mobile phones using deep learning + emissive screen + contour geometry.
        Returns detection metrics, bounding boxes, thermal heatmap metadata, and annotated frame.
        """
        result = {
            'phone_detected': False,
            'boxes': [],
            'confidence': 0.0,
            'unwanted_regions': [],
            'heatmap_active': False,
            'heatmap_intensity': 0.0,
            'detection_method': 'NONE',
            'description': ''
        }

        if frame is None:
            return result, None

        H, W = frame.shape[:2]
        face_boxes = face_boxes or []
        unwanted_zone_y_start = int(H * 0.25) # Workspace / desk / hand area

        all_candidates = []

        # ---------------- PASS 1: YOLOv4-tiny Deep Learning ----------------
        if self.yolo_net is not None:
            try:
                blob = cv2.dnn.blobFromImage(frame, 1/255.0, (416, 416), swapRB=True, crop=False)
                self.yolo_net.setInput(blob)
                outs = self.yolo_net.forward(self.yolo_out_layers)

                # Class 67: cell phone, Class 65: remote, Class 63: laptop
                target_classes = {67: 0.95, 65: 0.85, 63: 0.88}

                for out in outs:
                    for detection in out:
                        scores = detection[5:]
                        class_id = int(np.argmax(scores))
                        conf = float(scores[class_id])

                        if class_id in target_classes and conf >= 0.20:
                            center_x = int(detection[0] * W)
                            center_y = int(detection[1] * H)
                            bw = int(detection[2] * W)
                            bh = int(detection[3] * H)
                            bx = max(0, int(center_x - bw / 2))
                            by = max(0, int(center_y - bh / 2))
                            bw = min(W - bx, bw)
                            bh = min(H - by, bh)

                            # Ignore if overlapping with candidate's face
                            if not self._overlaps_face([bx, by, bw, bh], face_boxes):
                                all_candidates.append({
                                    'box': [bx, by, bw, bh],
                                    'confidence': conf * target_classes[class_id],
                                    'method': 'YOLO_DNN'
                                })
            except Exception as e:
                logger.error(f"YOLO detection error: {e}")

        # ---------------- PASS 2: Emissive / Illuminated Screen Detection ----------------
        # Specifically catches phones when the screen is turned ON and emitting light
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            ambient_mean = float(np.mean(gray))
            # Screen threshold: significantly brighter than room light
            screen_thresh_val = max(135, int(ambient_mean + 28))
            _, screen_bin = cv2.threshold(gray, screen_thresh_val, 255, cv2.THRESH_BINARY)

            # Filter out top noise
            screen_bin[0:unwanted_zone_y_start, :] = 0

            kernel_screen = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            screen_clean = cv2.morphologyEx(screen_bin, cv2.MORPH_CLOSE, kernel_screen, iterations=2)
            screen_contours, _ = cv2.findContours(screen_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for cnt in screen_contours:
                c_area = cv2.contourArea(cnt)
                if c_area < self.min_phone_area or c_area > self.max_phone_area:
                    continue

                sx, sy, sw, sh = cv2.boundingRect(cnt)
                if sw >= W * 0.85 or sh >= H * 0.85:
                    continue

                aspect = max(float(sh) / max(1, sw), float(sw) / max(1, sh))
                if 1.15 <= aspect <= 2.9:
                    # Confirm interior brightness
                    roi = gray[sy:sy+sh, sx:sx+sw]
                    if roi.size > 0 and float(np.mean(roi)) > (ambient_mean + 20):
                        if not self._overlaps_face([sx, sy, sw, sh], face_boxes):
                            all_candidates.append({
                                'box': [sx, sy, sw, sh],
                                'confidence': 0.94,
                                'method': 'ILLUMINATED_SCREEN'
                            })
        except Exception as e:
            logger.error(f"Emissive screen detection error: {e}")

        # ---------------- PASS 3: Geometric Edge & Bezel Contour Detection ----------------
        # Catches dark phone bodies, glass bezels, and handheld slabs
        try:
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            edges = cv2.Canny(blurred, 35, 110)
            thresh_adapt = cv2.adaptiveThreshold(
                blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
            )
            # Mask out upper head region to avoid hair/face edges
            thresh_adapt[0:unwanted_zone_y_start, :] = 0
            edges[0:unwanted_zone_y_start, :] = 0

            combined = cv2.bitwise_or(edges, thresh_adapt)
            kernel_geom = cv2.getStructuringElement(cv2.MORPH_RECT, (4, 4))
            closed = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel_geom, iterations=2)
            contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < self.min_phone_area or area > self.max_phone_area:
                    continue

                gx, gy, gw, gh = cv2.boundingRect(cnt)
                if gw >= W * 0.85 or gh >= H * 0.85:
                    continue

                aspect = max(float(gh) / max(1, gw), float(gw) / max(1, gh))
                if 1.15 <= aspect <= 2.85:
                    bb_area = gw * gh
                    solidity = area / float(bb_area) if bb_area > 0 else 0
                    if solidity >= 0.35: # Forgiving of fingers and hands holding phone
                        if not self._overlaps_face([gx, gy, gw, gh], face_boxes):
                            all_candidates.append({
                                'box': [gx, gy, gw, gh],
                                'confidence': 0.86,
                                'method': 'CONTOUR_GEOMETRY'
                            })
        except Exception as e:
            logger.error(f"Geometric phone detection error: {e}")

        # ---------------- NMS ENSEMBLE MERGING ----------------
        merged_boxes, merged_confs, merged_methods = self._nms_merge(all_candidates)

        annotated_frame = frame.copy()

        if merged_boxes:
            self.streak_counter += 1
            result['phone_detected'] = True
            result['boxes'] = merged_boxes
            result['confidence'] = round(float(max(merged_confs)), 2)
            result['heatmap_active'] = True
            result['heatmap_intensity'] = 98.6
            result['detection_method'] = merged_methods[0]
            result['description'] = f'Unauthorized mobile device detected ({len(merged_boxes)} found via {merged_methods[0]}).'

            # Render vivid OpenCV Thermal Heat Map (COLORMAP_JET) and gradient borders
            for b in merged_boxes:
                bx, by, bw, bh = b
                self._draw_thermal_heatmap_region(annotated_frame, bx, by, bw, bh)
        else:
            self.streak_counter = 0

        return result, annotated_frame

    def _overlaps_face(self, box, face_boxes):
        """Checks if detected box significantly intersects candidate's primary face."""
        x, y, w, h = box
        for fx, fy, fw, fh in face_boxes:
            ix = max(x, fx)
            iy = max(y, fy)
            iw = max(0, min(x + w, fx + fw) - ix)
            ih = max(0, min(y + h, fy + fh) - iy)
            intersection = iw * ih
            if intersection > 0.40 * (fw * fh) or intersection > 0.50 * (w * h):
                return True
        return False

    def _nms_merge(self, candidates, overlap_thresh=0.35):
        """Merges candidate boxes across all detection engines."""
        if not candidates:
            return [], [], []

        boxes = np.array([c['box'] for c in candidates])
        confs = np.array([c['confidence'] for c in candidates])
        methods = [c['method'] for c in candidates]

        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 0] + boxes[:, 2]
        y2 = boxes[:, 1] + boxes[:, 3]
        area = (x2 - x1) * (y2 - y1)
        idxs = np.argsort(confs)

        pick = []
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

        final_boxes = boxes[pick].tolist()
        final_confs = confs[pick].tolist()
        final_methods = [methods[p] for p in pick]
        return final_boxes, final_confs, final_methods

    def _draw_thermal_heatmap_region(self, frame, x, y, w, h):
        """
        Renders a vivid OpenCV Thermal Heat Map (COLORMAP_JET) and glowing multi-tier
        gradient boundary around the detected contraband mobile device.
        """
        H, W = frame.shape[:2]
        pad_x = int(w * 0.25)
        pad_y = int(h * 0.25)

        x1 = max(0, x - pad_x)
        y1 = max(0, y - pad_y)
        x2 = min(W, x + w + pad_x)
        y2 = min(H, y + h + pad_y)

        sub_w = x2 - x1
        sub_h = y2 - y1
        if sub_w < 8 or sub_h < 8:
            return

        sub_img = frame[y1:y2, x1:x2]

        # 1. 2D Thermal Heat Intensity Kernel
        heat_gray = np.zeros((sub_h, sub_w), dtype=np.uint8)
        cx_sub = sub_w // 2
        cy_sub = sub_h // 2
        rx = max(4, int(w * 0.45))
        ry = max(4, int(h * 0.45))

        # Core hotspot (255 max heat)
        cv2.ellipse(heat_gray, (cx_sub, cy_sub), (rx, ry), 0, 0, 360, 255, -1)

        # Smooth thermal diffusion gradient via Gaussian blur
        kw = max(3, (sub_w // 2) * 2 + 1)
        kh = max(3, (sub_h // 2) * 2 + 1)
        heat_smooth = cv2.GaussianBlur(heat_gray, (kw, kh), 0)

        # 2. Apply OpenCV JET Colormap (Blue -> Cyan -> Yellow -> Crimson Hotspot)
        heat_jet = cv2.applyColorMap(heat_smooth, cv2.COLORMAP_JET)

        # 3. Alpha blend thermal heatmap over the video frame
        alpha = 0.50
        blended = cv2.addWeighted(sub_img, 1.0 - alpha, heat_jet, alpha, 0)
        frame[y1:y2, x1:x2] = blended

        # 4. Multi-layer glowing gradient border around the device
        colors = [
            ((0, 0, 255), 3),      # Inner Crimson Red
            ((0, 140, 255), 2),    # Amber / Neon Orange
            ((0, 255, 255), 1)     # Outer High-Alert Yellow
        ]
        for color, thickness in colors:
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, thickness)

        # 5. Thermal Target Reticle / Crosshair at Center
        cx = x + w // 2
        cy = y + h // 2
        cv2.drawMarker(frame, (cx, cy), (0, 0, 255), cv2.MARKER_CROSS, 16, 2)
        cv2.circle(frame, (cx, cy), 12, (0, 255, 255), 1)

        # 6. Thermal Warning Banner with Heatspot & Confidence Indicator
        banner_y = max(24, y - 10)
        banner_w = min(W - x, 255)
        cv2.rectangle(frame, (x, banner_y - 20), (x + banner_w, banner_y), (0, 0, 200), -1)
        cv2.putText(
            frame,
            "THERMAL MAP: PHONE DETECTED",
            (x + 6, banner_y - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (255, 255, 255),
            1,
            cv2.LINE_AA
        )
