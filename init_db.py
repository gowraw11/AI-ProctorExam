import os
import sys
from datetime import datetime, timedelta
import cv2
import numpy as np

# Set environment
os.environ.setdefault('FLASK_ENV', 'development')

from app import create_app
from extensions import db
from models.user import User
from models.exam import Exam
from models.question import Question
from models.attempt import ExamAttempt, Answer
from models.proctoring import ProctoringSession, ProctoringEvent


def seed_database():
    app = create_app()

    with app.app_context():
        print("[*] Initializing database tables...")
        db.create_all()

        # 1. Seed Admin User
        admin_email = 'admin@example.com'
        admin = User.query.filter_by(email=admin_email).first()
        if not admin:
            admin = User(
                full_name='Dr. Alan Turing (Admin)',
                email=admin_email,
                role='admin',
                registration_number='ADMIN-001',
                is_active=True
            )
            admin.set_password('Admin@123')
            db.session.add(admin)
            print(f"[+] Created Administrator: {admin_email} (Password: Admin@123)")
        else:
            print(f"[*] Admin {admin_email} already exists.")

        # 2. Seed Demo Students
        student_email = 'student@example.com'
        student = User.query.filter_by(email=student_email).first()
        if not student:
            student = User(
                full_name='Ada Lovelace',
                email=student_email,
                role='student',
                registration_number='CS2026-001',
                is_active=True
            )
            student.set_password('Student@123')
            db.session.add(student)
            print(f"[+] Created Student: {student_email} (Password: Student@123)")
        else:
            print(f"[*] Student {student_email} already exists.")

        student2_email = 'alex@example.com'
        student2 = User.query.filter_by(email=student2_email).first()
        if not student2:
            student2 = User(
                full_name='Alex Rivera',
                email=student2_email,
                role='student',
                registration_number='CS2026-002',
                is_active=True
            )
            student2.set_password('Student@123')
            db.session.add(student2)
            print(f"[+] Created Student 2: {student2_email} (Password: Student@123)")

        db.session.commit()

        # 3. Seed Exams & Questions
        exams_data = [
            {
                'title': 'Python Programming & Architecture',
                'subject': 'Python Programming',
                'description': 'Advanced assessment covering core syntax, data structures, OOP principles, generator mechanics, and Flask web framework architecture.',
                'duration_minutes': 30,
                'total_marks': 100,
                'passing_marks': 40,
                'status': 'published',
                'questions': [
                    {
                        'text': 'What is the output of print(2 ** 3)?',
                        'a': '6', 'b': '8', 'c': '9', 'd': '5',
                        'correct': 'B', 'marks': 10.0, 'neg': 2.0
                    },
                    {
                        'text': 'What is a Python dictionary?',
                        'a': 'An immutable sequence of characters',
                        'b': 'An ordered list of integers',
                        'c': 'A mutable hash map mapping unique keys to values',
                        'd': 'A compiled binary file format',
                        'correct': 'C', 'marks': 10.0, 'neg': 2.0
                    },
                    {
                        'text': 'What is Flask in the Python ecosystem?',
                        'a': 'A full-stack asynchronous database server',
                        'b': 'A lightweight WSGI micro web framework',
                        'c': 'A graphical game engine',
                        'd': 'A low-level memory allocation compiler',
                        'correct': 'B', 'marks': 10.0, 'neg': 2.0
                    },
                    {
                        'text': 'Which keyword is used to create a generator function in Python?',
                        'a': 'generate', 'b': 'return', 'c': 'yield', 'd': 'async',
                        'correct': 'C', 'marks': 10.0, 'neg': 2.0
                    },
                    {
                        'text': 'What does PEP 8 represent in Python standards?',
                        'a': 'The Python Enhancement Proposal for Code Style Guide',
                        'b': 'The Python Package Index repository',
                        'c': 'The Python Cryptographic Specification',
                        'd': 'The Python Virtual Environment manager',
                        'correct': 'A', 'marks': 10.0, 'neg': 2.0
                    },
                    {
                        'text': 'Which method is called automatically when an object instance is created?',
                        'a': '__init__', 'b': '__new__', 'c': '__call__', 'd': '__create__',
                        'correct': 'A', 'marks': 10.0, 'neg': 2.0
                    },
                    {
                        'text': 'What is the time complexity of looking up a key in a Python dict on average?',
                        'a': 'O(n)', 'b': 'O(n log n)', 'c': 'O(1)', 'd': 'O(log n)',
                        'correct': 'C', 'marks': 10.0, 'neg': 2.0
                    },
                    {
                        'text': 'How do you handle exceptions in Python?',
                        'a': 'try / catch', 'b': 'try / except / finally', 'c': 'do / catch', 'd': 'catch / throw',
                        'correct': 'B', 'marks': 10.0, 'neg': 2.0
                    },
                    {
                        'text': 'Which module in standard library is used for regular expressions?',
                        'a': 'regex_lib', 'b': 're', 'c': 'string', 'd': 'pattern',
                        'correct': 'B', 'marks': 10.0, 'neg': 2.0
                    },
                    {
                        'text': 'What is the purpose of the "with" statement in Python?',
                        'a': 'To create a parallel thread pool',
                        'b': 'To define a lambda expression',
                        'c': 'To manage resources via context managers ensuring proper cleanup',
                        'd': 'To override global variable scopes',
                        'correct': 'C', 'marks': 10.0, 'neg': 2.0
                    }
                ]
            },
            {
                'title': 'Computer Networks & Distributed Systems',
                'subject': 'Computer Networks',
                'description': 'Comprehensive exam evaluating OSI & TCP/IP models, routing protocols, transport security, and packet transmission mechanics.',
                'duration_minutes': 45,
                'total_marks': 100,
                'passing_marks': 40,
                'status': 'published',
                'questions': [
                    {
                        'text': 'What does TCP provide in the transport layer?',
                        'a': 'Unreliable connectionless datagram delivery',
                        'b': 'Reliable, ordered, and error-checked delivery of a stream of octets',
                        'c': 'Physical bit-level synchronization',
                        'd': 'Cryptographic public-key distribution only',
                        'correct': 'B', 'marks': 10.0, 'neg': 2.5
                    },
                    {
                        'text': 'What does HTTP stand for?',
                        'a': 'HyperText Transmission Protocol',
                        'b': 'HyperText Transfer Protocol',
                        'c': 'High Transfer Text Protocol',
                        'd': 'Host Terminal Transfer Protocol',
                        'correct': 'B', 'marks': 10.0, 'neg': 2.5
                    },
                    {
                        'text': 'What is an IP address?',
                        'a': 'A unique numerical identifier assigned to a network interface device',
                        'b': 'A hardware MAC address burned into network cards',
                        'c': 'A software password for local WiFi routers',
                        'd': 'A domain registrar server tag',
                        'correct': 'A', 'marks': 10.0, 'neg': 2.5
                    },
                    {
                        'text': 'Which port is standard for HTTPS encrypted traffic?',
                        'a': '80', 'b': '22', 'c': '443', 'd': '8080',
                        'correct': 'C', 'marks': 10.0, 'neg': 2.5
                    },
                    {
                        'text': 'At which OSI layer does an IP Router operate?',
                        'a': 'Data Link Layer (Layer 2)',
                        'b': 'Network Layer (Layer 3)',
                        'c': 'Transport Layer (Layer 4)',
                        'd': 'Session Layer (Layer 5)',
                        'correct': 'B', 'marks': 10.0, 'neg': 2.5
                    },
                    {
                        'text': 'What protocol is used to translate domain names into IP addresses?',
                        'a': 'DHCP', 'b': 'ARP', 'c': 'DNS', 'd': 'ICMP',
                        'correct': 'C', 'marks': 10.0, 'neg': 2.5
                    },
                    {
                        'text': 'What is the purpose of the 3-Way Handshake in TCP?',
                        'a': 'To establish a synchronized connection before transferring data',
                        'b': 'To encrypt data packets using SSL',
                        'c': 'To resolve MAC addresses to IP addresses',
                        'd': 'To terminate a persistent HTTP connection',
                        'correct': 'A', 'marks': 10.0, 'neg': 2.5
                    },
                    {
                        'text': 'Which protocol is used by the ping utility to verify host reachability?',
                        'a': 'UDP', 'b': 'ICMP', 'c': 'IGMP', 'd': 'SNMP',
                        'correct': 'B', 'marks': 10.0, 'neg': 2.5
                    },
                    {
                        'text': 'What does CIDR notation "/24" mean for an IPv4 subnet?',
                        'a': '24 available host addresses',
                        'b': 'A 24-bit network prefix (Subnet Mask: 255.255.255.0)',
                        'c': '24 subnets in the routing table',
                        'd': 'Class A network allocation',
                        'correct': 'B', 'marks': 10.0, 'neg': 2.5
                    },
                    {
                        'text': 'What mechanism prevents broadcast storms in Ethernet switches?',
                        'a': 'Spanning Tree Protocol (STP)',
                        'b': 'Border Gateway Protocol (BGP)',
                        'c': 'Routing Information Protocol (RIP)',
                        'd': 'Dynamic Host Configuration Protocol',
                        'correct': 'A', 'marks': 10.0, 'neg': 2.5
                    }
                ]
            },
            {
                'title': 'Machine Learning & Artificial Intelligence',
                'subject': 'Machine Learning',
                'description': 'Evaluating fundamental concepts of ML algorithms, model evaluation metrics, deep neural architectures, and computer vision preprocessing.',
                'duration_minutes': 40,
                'total_marks': 100,
                'passing_marks': 40,
                'status': 'published',
                'questions': [
                    {
                        'text': 'What is supervised learning?',
                        'a': 'Training a model without any labeled target outputs',
                        'b': 'Training a model on labeled input-output pairs',
                        'c': 'Reinforcement learning based strictly on environmental rewards',
                        'd': 'Clustering unlabeled data points via k-means',
                        'correct': 'B', 'marks': 10.0, 'neg': 2.0
                    },
                    {
                        'text': 'What is the purpose of an artificial neural network?',
                        'a': 'To simulate relational SQL databases in memory',
                        'b': 'To approximate complex non-linear functions inspired by biological neural structures',
                        'c': 'To serialize JSON objects across network sockets',
                        'd': 'To compile binary assembly code directly',
                        'correct': 'B', 'marks': 10.0, 'neg': 2.0
                    },
                    {
                        'text': 'What is overfitting in machine learning?',
                        'a': 'When a model performs poorly on training data',
                        'b': 'When a model learns training data noise too closely and fails to generalize to unseen test data',
                        'c': 'When a model converges too quickly to zero loss',
                        'd': 'When dataset features have zero variance',
                        'correct': 'B', 'marks': 10.0, 'neg': 2.0
                    },
                    {
                        'text': 'What is cross-validation used for?',
                        'a': 'Assessing model generalization performance and mitigating overfitting across multiple data folds',
                        'b': 'Validating user authentication tokens',
                        'c': 'Converting categorical features to one-hot vectors',
                        'd': 'Compressing neural network weights into FP16',
                        'correct': 'A', 'marks': 10.0, 'neg': 2.0
                    },
                    {
                        'text': 'Which activation function is most widely used in hidden layers of modern deep networks?',
                        'a': 'Step function', 'b': 'Sigmoid', 'c': 'ReLU (Rectified Linear Unit)', 'd': 'Linear',
                        'correct': 'C', 'marks': 10.0, 'neg': 2.0
                    },
                    {
                        'text': 'What does AUC-ROC measure in binary classification?',
                        'a': 'Computational execution speed in milliseconds',
                        'b': 'Model discriminative ability across various classification thresholds',
                        'c': 'Mean Squared Error of continuous values',
                        'd': 'Total parameter count in the neural network',
                        'correct': 'B', 'marks': 10.0, 'neg': 2.0
                    },
                    {
                        'text': 'What is the primary role of Gradient Descent in neural network optimization?',
                        'a': 'To minimize the loss function by iteratively updating model weights in direction of steepest descent',
                        'b': 'To eliminate outliers from input datasets',
                        'c': 'To compute inverse covariance matrices',
                        'd': 'To generate synthetic adversarial images',
                        'correct': 'A', 'marks': 10.0, 'neg': 2.0
                    },
                    {
                        'text': 'Which technique is specifically used in Convolutional Neural Networks (CNNs) to reduce spatial dimensions?',
                        'a': 'Pooling (e.g. MaxPooling)', 'b': 'Dropout', 'c': 'Batch Normalization', 'd': 'Softmax',
                        'correct': 'A', 'marks': 10.0, 'neg': 2.0
                    },
                    {
                        'text': 'In computer vision, what does Haar Cascade classification rely on?',
                        'a': 'Recurrent memory cells with gate vectors',
                        'b': 'Adaboost classifier with rectangular feature differences (Haar-like wavelets)',
                        'c': 'Transformer self-attention maps',
                        'd': 'Random forest bootstrap aggregations',
                        'correct': 'B', 'marks': 10.0, 'neg': 2.0
                    },
                    {
                        'text': 'What does Precision measure in classification metrics?',
                        'a': 'The proportion of actual positives that were correctly identified (TP / (TP + FN))',
                        'b': 'The proportion of predicted positives that were truly correct (TP / (TP + FP))',
                        'c': 'The harmonic mean of precision and recall',
                        'd': 'The overall accuracy of all four quadrants',
                        'correct': 'B', 'marks': 10.0, 'neg': 2.0
                    }
                ]
            }
        ]

        created_exams = []
        for ex_data in exams_data:
            existing_exam = Exam.query.filter_by(title=ex_data['title']).first()
            if not existing_exam:
                exam = Exam(
                    title=ex_data['title'],
                    subject=ex_data['subject'],
                    description=ex_data['description'],
                    duration_minutes=ex_data['duration_minutes'],
                    total_marks=ex_data['total_marks'],
                    passing_marks=ex_data['passing_marks'],
                    status=ex_data['status']
                )
                db.session.add(exam)
                db.session.flush()

                for idx, q_info in enumerate(ex_data['questions']):
                    question = Question(
                        exam_id=exam.id,
                        question_text=q_info['text'],
                        option_a=q_info['a'],
                        option_b=q_info['b'],
                        option_c=q_info['c'],
                        option_d=q_info['d'],
                        correct_answer=q_info['correct'],
                        marks=q_info['marks'],
                        negative_marks=q_info.get('neg', 0.0),
                        order=idx + 1
                    )
                    db.session.add(question)

                db.session.commit()
                created_exams.append(exam)
                print(f"[+] Created Exam: {exam.title} ({len(ex_data['questions'])} questions)")
            else:
                created_exams.append(existing_exam)
                print(f"[*] Exam '{existing_exam.title}' already exists.")

        # 4. Generate a sample photographic screenshot evidence image for demonstration
        screenshot_dir = os.path.join(app.root_path, 'uploads', 'screenshots')
        os.makedirs(screenshot_dir, exist_ok=True)
        demo_screenshot_name = "attempt_demo_evidence.jpg"
        demo_screenshot_path = os.path.join(screenshot_dir, demo_screenshot_name)

        if not os.path.exists(demo_screenshot_path):
            # Create synthetic annotated proof frame
            img = np.zeros((360, 480, 3), dtype=np.uint8)
            img[:] = (30, 30, 30)
            cv2.rectangle(img, (140, 80), (340, 280), (0, 0, 255), 2)
            cv2.putText(img, "FLAGGED: MULTIPLE FACES", (130, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            cv2.putText(img, "PROCTOR EVIDENCE - TIME 14:22:10", (30, 330), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            cv2.imwrite(demo_screenshot_path, img)
            print(f"[+] Generated synthetic proctoring evidence snapshot: {demo_screenshot_path}")

        phone_screenshot_name = "attempt_phone_evidence.jpg"
        phone_screenshot_path = os.path.join(screenshot_dir, phone_screenshot_name)
        if not os.path.exists(phone_screenshot_path):
            img_phone = np.zeros((360, 480, 3), dtype=np.uint8)
            img_phone[:] = (25, 25, 25)
            # Simulated face
            cv2.rectangle(img_phone, (160, 40), (320, 200), (0, 255, 0), 2)
            cv2.putText(img_phone, "CANDIDATE FACE", (170, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
            # Phone in unwanted region with gradient border
            p_x, p_y, p_w, p_h = 290, 210, 80, 140
            cv2.rectangle(img_phone, (p_x - 4, p_y - 4), (p_x + p_w + 4, p_y + p_h + 4), (0, 165, 255), 2)
            cv2.rectangle(img_phone, (p_x, p_y), (p_x + p_w, p_y + p_h), (0, 0, 255), 3)
            sub = img_phone[p_y:p_y+p_h, p_x:p_x+p_w]
            red_fill = np.zeros(sub.shape, dtype=np.uint8)
            red_fill[:] = (0, 0, 180)
            cv2.addWeighted(sub, 0.7, red_fill, 0.3, 1.0, sub)
            img_phone[p_y:p_y+p_h, p_x:p_x+p_w] = sub
            cv2.rectangle(img_phone, (p_x - 4, p_y - 24), (p_x + p_w + 40, p_y - 4), (0, 0, 220), -1)
            cv2.putText(img_phone, "UNWANTED: PHONE", (p_x, p_y - 9), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            cv2.putText(img_phone, "EVIDENCE: PHONE DETECTED IN WORKSPACE", (20, 340), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
            cv2.imwrite(phone_screenshot_path, img_phone)
            print(f"[+] Generated synthetic phone evidence snapshot: {phone_screenshot_path}")

        # 5. Seed a Completed Attempt for Alex Rivera with realistic proctoring events
        # So Admin Dashboard is immediately populated with rich charts upon initial run!
        first_exam = created_exams[0]
        sample_attempt = ExamAttempt.query.filter_by(student_id=student2.id, exam_id=first_exam.id).first()
        if not sample_attempt:
            started = datetime.utcnow() - timedelta(minutes=25)
            submitted = datetime.utcnow() - timedelta(minutes=5)
            sample_attempt = ExamAttempt(
                exam_id=first_exam.id,
                student_id=student2.id,
                started_at=started,
                submitted_at=submitted,
                score=80.0,
                percentage=80.0,
                status='submitted',
                suspicious_activity_count=5
            )
            db.session.add(sample_attempt)
            db.session.flush()

            # Proctoring session
            p_session = ProctoringSession(
                attempt_id=sample_attempt.id,
                started_at=started,
                ended_at=submitted,
                total_events=5,
                risk_score=65,
                final_status='HIGH_RISK'
            )
            db.session.add(p_session)

            # Answers
            for q in first_exam.questions:
                is_correct = (q.order <= 8)
                ans = Answer(
                    attempt_id=sample_attempt.id,
                    question_id=q.id,
                    selected_answer=q.correct_answer if is_correct else ('A' if q.correct_answer != 'A' else 'B'),
                    is_correct=is_correct,
                    marks_awarded=float(q.marks) if is_correct else 0.0
                )
                db.session.add(ans)

            # Sample Events
            events_to_seed = [
                ('LOOKING_AWAY', 'MEDIUM', 'Candidate sustained looking away towards right.', started + timedelta(minutes=4), 0.88, None),
                ('TAB_SWITCH', 'MEDIUM', 'Candidate navigated away from examination window (Count: 1).', started + timedelta(minutes=8), 1.0, None),
                ('MULTIPLE_FACES', 'HIGH', 'Multiple faces detected (2 faces visible).', started + timedelta(minutes=12), 0.92, f"uploads/screenshots/{demo_screenshot_name}"),
                ('PHONE_DETECTED', 'HIGH', 'Mobile phone detected in unwanted workspace region.', started + timedelta(minutes=16), 0.94, f"uploads/screenshots/{phone_screenshot_name}"),
                ('HEAD_MOVEMENT', 'LOW', 'Head and gaze diverted to left.', started + timedelta(minutes=19), 0.80, None)
            ]

            for e_type, sev, desc, ts, conf, shot in events_to_seed:
                evt = ProctoringEvent(
                    attempt_id=sample_attempt.id,
                    event_type=e_type,
                    severity=sev,
                    description=desc,
                    timestamp=ts,
                    confidence=conf,
                    screenshot_path=shot,
                    is_demo=False
                )
                db.session.add(evt)

            db.session.commit()
            print(f"[+] Seeded realistic evaluation attempt for {student2.email} on Exam {first_exam.id}")

        print("=" * 60)
        print("[SUCCESS] Database initialization and demo seeding completed!")
        print("Demo Credentials:")
        print("  Admin:   admin@example.com   | Password:  Admin@123")
        print("  Student: student@example.com | Password:  Student@123")
        print("=" * 60)


if __name__ == '__main__':
    seed_database()
