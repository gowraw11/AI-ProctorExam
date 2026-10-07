import logging
import random
import cv2
from ml.face_detector import FaceDetector
from ml.head_pose import HeadPoseEstimator
from ml.gaze_detector import GazeDetector
from ml.phone_detector import PhoneDetector

logger = logging.getLogger(__name__)


class ProctoringEngine:
    """
    Unified AI/Computer-Vision Proctoring Engine.
    Combines Face Detection, Head Pose Estimation, Gaze Tracking,
    and Mobile Phone / Device Detection with Gradient Warning Regions.
    Features:
    - Per-attempt session state tracking
    - Calibrated grace periods (0-4s grace, 6-8s warning, >=10s sustained violation)
    - Anti-spam cooldowns on repeated NO_FACE infractions
    - Instant recovery when face returns
    """

    def __init__(self, demo_mode=False):
        self.demo_mode = demo_mode
        self.face_detector = FaceDetector()
        self.head_pose = HeadPoseEstimator()
        self.gaze_detector = GazeDetector()
        self.phone_detector = PhoneDetector()
        self.session_states = {}

    def _get_session_state(self, attempt_id):
        key = str(attempt_id) if attempt_id is not None else 'default'
        if key not in self.session_states:
            self.session_states[key] = {
                'missing_face_streak': 0,
                'last_no_face_tick': -999,
                'looking_away_streak': 0,
                'ticks': 0
            }
        return self.session_states[key]

    def process_frame(self, image_data, attempt_id=None, is_demo=False):
        """
        Processes a single video frame and produces proctoring metrics and events.
        """
        if (self.demo_mode or is_demo) and (image_data is None or image_data == 'SIMULATE'):
            return self._generate_simulated_result()

        result = {
            'face_count': 0,
            'face_detected': False,
            'head_direction': 'CENTER',
            'gaze_direction': 'CENTER',
            'is_centered': True,
            'lighting_ok': True,
            'phone_detected': False,
            'phone_boxes': [],
            'heatmap_active': False,
            'heatmap_intensity': 0.0,
            'risk_score_delta': 0,
            'events': [],
            'status': 'NORMAL',
            'processed_frame': None
        }

        state = self._get_session_state(attempt_id)
        state['ticks'] += 1

        # 1. Advanced Face Detection
        face_info, frame = self.face_detector.detect_faces(image_data, allow_tracking=True)
        if frame is None or not face_info.get('success', False):
            result['status'] = 'WARNING'
            return result

        face_count = face_info['face_count']
        result['face_count'] = face_count
        result['face_detected'] = face_info['face_detected']
        result['is_centered'] = face_info['is_centered']
        result['lighting_ok'] = face_info['lighting_ok']

        # Annotate frame for evidence storage
        annotated_frame = frame.copy()

        # 2. Face Presence & Sustained Absence Policy
        if face_count == 0:
            state['missing_face_streak'] += 1
            streak = state['missing_face_streak']

            # Grace period: 1-2 ticks (0 to 4s) -> Normal brief glance/movement
            if streak < 3:
                result['status'] = 'NORMAL'
            elif 3 <= streak < 5:
                # 6 to 8 seconds: Mild caution indicator for HUD, no disciplinary penalty yet
                result['status'] = 'WARNING'
            else:
                # >= 5 ticks (10+ seconds): Official sustained absence
                result['status'] = 'VIOLATION'
                cooldown_elapsed = (state['ticks'] - state['last_no_face_tick']) >= 8
                if cooldown_elapsed:
                    state['last_no_face_tick'] = state['ticks']
                    result['events'].append({
                        'event_type': 'NO_FACE',
                        'severity': 'HIGH',
                        'description': f'Candidate sustained absence from camera ({streak * 2}s elapsed).',
                        'confidence': 0.95
                    })
                    result['risk_score_delta'] += 10
        else:
            state['missing_face_streak'] = 0

        # Multiple Faces Anomaly
        if face_count > 1:
            result['events'].append({
                'event_type': 'MULTIPLE_FACES',
                'severity': 'HIGH',
                'description': f'Multiple faces detected ({face_count} faces visible in camera).',
                'confidence': 0.90
            })
            result['risk_score_delta'] += 30
            result['status'] = 'VIOLATION'

            for (x, y, w, h) in face_info['bounding_boxes']:
                cv2.rectangle(annotated_frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
                cv2.putText(annotated_frame, 'UNAUTHORIZED PERSON', (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        # 3. Single Face Analysis: Pose and Gaze
        if face_count == 1 and face_info.get('bounding_boxes'):
            primary_box = face_info['bounding_boxes'][0]
            x, y, w, h = primary_box
            is_tracked = face_info.get('tracked', False)

            box_color = (0, 200, 255) if is_tracked else (0, 255, 0)
            cv2.rectangle(annotated_frame, (x, y), (x+w, y+h), box_color, 2)

            # Head Pose Estimation
            head_dir, pose_conf, sustained_pose = self.head_pose.estimate_direction(frame, primary_box)
            result['head_direction'] = head_dir

            # Gaze Estimation
            gaze_dir, gaze_conf = self.gaze_detector.estimate_gaze(frame, primary_box)
            result['gaze_direction'] = gaze_dir

            # Check for extreme non-centering
            if not face_info['is_centered']:
                result['events'].append({
                    'event_type': 'FACE_NOT_CENTERED',
                    'severity': 'LOW',
                    'description': 'Face is significantly offset from the center of the frame.',
                    'confidence': 0.70
                })
                result['risk_score_delta'] += 3

            # Check for sustained looking away
            if sustained_pose and head_dir != "CENTER":
                state['looking_away_streak'] += 1
                result['events'].append({
                    'event_type': 'LOOKING_AWAY',
                    'severity': 'MEDIUM',
                    'description': f'Candidate sustained looking away towards {head_dir.lower()}.',
                    'confidence': round(pose_conf, 2)
                })
                result['risk_score_delta'] += 5
                result['status'] = 'WARNING'
                cv2.putText(annotated_frame, f'LOOKING {head_dir}', (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 2)
            elif gaze_dir != "CENTER" and head_dir != "CENTER":
                result['events'].append({
                    'event_type': 'HEAD_MOVEMENT',
                    'severity': 'LOW',
                    'description': f'Head and gaze diverted towards {head_dir.lower()}.',
                    'confidence': round((pose_conf + gaze_conf) / 2.0, 2)
                })
                result['risk_score_delta'] += 5
            else:
                state['looking_away_streak'] = 0
                label = 'FACE TRACKED' if is_tracked else 'FACE VERIFIED'
                cv2.putText(annotated_frame, label, (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 2)

        # 4. Mobile Phone & Prohibited Device Detection in Unwanted Region
        phone_info, annotated_frame = self.phone_detector.detect(
            annotated_frame,
            face_boxes=face_info.get('bounding_boxes', [])
        )
        if phone_info.get('phone_detected'):
            result['phone_detected'] = True
            result['phone_boxes'] = phone_info.get('boxes', [])
            result['heatmap_active'] = phone_info.get('heatmap_active', True)
            result['heatmap_intensity'] = phone_info.get('heatmap_intensity', 98.4)
            result['events'].append({
                'event_type': 'PHONE_DETECTED',
                'severity': 'HIGH',
                'description': phone_info.get('description', 'Unauthorized mobile phone detected in proctored area.'),
                'confidence': phone_info.get('confidence', 0.92)
            })
            result['risk_score_delta'] += 30
            result['status'] = 'VIOLATION'

        result['processed_frame'] = annotated_frame
        return result

    def _generate_simulated_result(self):
        """Generates realistic simulated result for demo presentations."""
        scenarios = ['NORMAL', 'NORMAL', 'NORMAL', 'LOOKING_AWAY', 'NORMAL']
        choice = random.choice(scenarios)

        if choice == 'NORMAL':
            return {
                'face_count': 1,
                'face_detected': True,
                'head_direction': 'CENTER',
                'gaze_direction': 'CENTER',
                'is_centered': True,
                'lighting_ok': True,
                'phone_detected': False,
                'phone_boxes': [],
                'risk_score_delta': 0,
                'events': [],
                'status': 'NORMAL',
                'processed_frame': None
            }
        else:
            return {
                'face_count': 1,
                'face_detected': True,
                'head_direction': 'LEFT',
                'gaze_direction': 'LEFT',
                'is_centered': True,
                'lighting_ok': True,
                'phone_detected': False,
                'phone_boxes': [],
                'risk_score_delta': 5,
                'events': [{
                    'event_type': 'LOOKING_AWAY',
                    'severity': 'MEDIUM',
                    'description': '[DEMO] Candidate looking away towards left.',
                    'confidence': 0.88
                }],
                'status': 'WARNING',
                'processed_frame': None
            }
