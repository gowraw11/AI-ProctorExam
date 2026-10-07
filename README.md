# AI-Powered Online Examination and Proctoring System
### *A Machine Learning Based Secure Online Examination Platform*
**Final Year Computer Science / Master of Computer Applications (MCA) Project**

---

## 📌 Executive Summary & Abstract
The **AI-Powered Online Examination and Proctoring System** is an enterprise-grade, full-stack educational assessment portal designed to ensure academic integrity in remote examination settings. 

Powered by a lightweight, CPU-optimized **OpenCV & Computer Vision ML Engine**, the platform performs continuous automated invigilation—monitoring for unauthorized face absences, multiple persons, head diversion, and eye gaze anomalies without requiring specialized GPU hardware. Concurrently, the frontend client enforces anti-cheating mechanisms including full-screen locks, browser tab-switching intercepts, DevTools blocking, and clipboard disabling.

The architecture emphasizes **AI-assisted human review**: rather than immediately disqualifying students based on single predictions, the system computes cumulative, calibrated risk scores and compiles photographic evidence dossiers with timestamps and confidence ratings for fair administrative review.

---

## 🌟 Key Features

### 👨‍🎓 Candidate / Student Experience
- **Sleek EdTech Portal**: Distraction-free, responsive UI built with Bootstrap 5, Font Awesome, and custom glassmorphism components.
- **Hardware & Environment Verification**: Pre-exam multi-step check validating camera signal, single face presence, lighting illumination, and centering.
- **Distraction-Free Test Interface**: 3-column layout featuring an interactive question palette, active question pane, and live proctoring HUD with camera preview.
- **Real-Time Auto-Save**: Candidate responses asynchronously sync to the backend on selection via REST APIs.
- **Server-Side Countdown Timer**: Unforgeable examination duration tracking with automated submission upon time expiration.
- **Instant Result Analytics**: Detailed breakdown of score, percentage, correct/incorrect/unanswered questions, pass/fail status, and proctoring integrity certificate.
- **Attempt History**: Complete archive of past examinations with scores and proctoring risk ratings.

### 🛡️ AI & Computer Vision Invigilation Engine
- **Robust Multi-Model Face Detection & Continuity**: Powered by an ensemble of OpenCV cascades (`frontalface_alt2`, `frontalface_default`, `alt_tree` for eyeglasses, and `profileface`) enhanced with CLAHE adaptive contrast normalization, skin chrominance validation, and temporal ROI tracking to eliminate false `NO_FACE` drops caused by blinks, head tilts, glasses, or ambient lighting shifts.
- **Calibrated Absence Policy**: Enforces progressive absence stages (0–4s grace period, 6–8s caution indicator, and $\ge 10$s sustained absence violation with anti-spam cooldown) preventing penalty inflation when students briefly look down at keyboards or scratch paper.
- **Multiple Face Detection**: Instantly flags unauthorized individuals entering the frame (`MULTIPLE_FACES` violation with photographic screenshot evidence).
- **Mobile Phone / Handheld Device Detection**: Identifies prohibited smartphones in the candidate workspace (`PHONE_DETECTED`) using contour aspect ratios, solidity, and screen luminance checks.
- **Thermal Heat Map Overlay & Contraband Hotspot**: Renders a vivid thermal heat map (OpenCV `COLORMAP_JET` in server evidence and dynamic HTML5 radial gradient on client HUD) with targeting reticles, temperature readings (`HOTSPOT 98.4%`), and glowing gradient boundaries over contraband mobile phones.
- **Web Audio Loud Alarm System & Face Action Alerts**: Built-in browser Web Audio API audio synthesizer delivering a loud emergency siren (960Hz $\leftrightarrow$ 640Hz sweep) when contraband phones appear, and dual-tone warning chimes for face turning (`LOOKING_AWAY`), multiple people (`MULTIPLE_FACES`), or tab switches, with interactive HUD Mute/Unmute and siren test controls.
- **Prohibited Workspace Gradient Region**: Highlights unwanted/restricted desk regions with a glowing multi-layer gradient box (`UNWANTED: PHONE DETECTED`) on both the live proctor HUD and server evidence captures.
- **Head Pose Estimation**: Analyzes facial orientation ratios to detect sustained turning to the left, right, up, or down (`LOOKING_AWAY` / `HEAD_MOVEMENT`).
- **Gaze Tracking**: Calculates eye pupil centroids to estimate whether the candidate is focused on the screen or looking away.
- **Client Anomaly Interceptors**: Logs `TAB_SWITCH`, `WINDOW_BLUR`, `FULLSCREEN_EXIT`, `COPY_ATTEMPT`, `PASTE_ATTEMPT`, and `RIGHT_CLICK`.
- **Dynamic Risk Engine**: Calibrated scoring tiers:
  - **0 – 20**: `LOW RISK` (Green)
  - **21 – 50**: `MEDIUM RISK` (Yellow)
  - **51 – 80**: `HIGH RISK` (Orange)
  - **81+**: `CRITICAL RISK` (Red)

### 👨‍💼 Administrator & Controller Portal
- **Enterprise Analytics Dashboard**: Chart.js visualizations for pass/fail distribution, risk profiles, and incident counts by type.
- **Full Exam & Question Bank CRUD**: Create, configure, publish, and delete exams; add multiple-choice questions with marks and negative marking.
- **Candidate Account Management**: Search students, inspect test attempts, and toggle account activation status.
- **Proctoring Timeline & Photographic Evidence**: Detailed chronological audit trail for every attempt, with modal viewing of flagged webcam snapshots.
- **Export & Reporting**:
  - Raw tabular dataset export via **CSV**.
  - Publication-ready official examination audit dossier via **ReportLab PDF**.
- **Demonstration / Simulation Mode**: Configurable toggle (`DEMO_MODE=true`) for demonstration walkthroughs without active hardware.

---

## 🏗️ System Architecture

```
                                 [ Candidate Browser ]
                                          |
                +-------------------------+-------------------------+
                |                         |                         |
        [ HTML5 / UI ]          [ Webcam Sampling ]      [ Security Listeners ]
        (Exam, Palette)        (Canvas Base64 @ 2s)      (Tab Switch, Fullscreen)
                |                         |                         |
                +-------------------------+-------------------------+
                                          |
                                HTTP / JSON REST APIs
                                          |
                                          v
                              [ Flask Application Core ]
                                (Python 3.11+ / 3.14)
                                          |
                        +-----------------+-----------------+
                        |                                   |
                        v                                   v
             [ Exam & Result Services ]           [ Proctoring Coordinator ]
            - Server Duration Sync               - Event Severity Mapper
            - Real-Time Answer Persistence       - Cumulative Risk Calculator
            - Negative Marking Evaluator         - Evidence Screenshot Store
                        |                                   |
                        |                                   v
                        |                         [ OpenCV ML Pipeline ]
                        |                        - Haar Face Detector
                        |                        - Head Pose Estimator
                        |                        - Eye Gaze Tracker
                        |                                   |
                        +-----------------+-----------------+
                                          |
                                          v
                              [ Relational Database ]
                           (SQLite / PostgreSQL Models)
                                          |
                                          v
                              [ Admin Analytics Console ]
                             - Chart.js Dashboard
                             - Incident Chronological Timeline
                             - CSV & ReportLab PDF Generator
```

---

## 📁 Project Directory Structure

```
online_exam_proctoring/
│
├── app.py                      # Flask Application Factory & URL routing
├── config.py                   # Central environment configuration
├── extensions.py               # SQLAlchemy, LoginManager, CORS instances
├── init_db.py                  # Database creation and realistic demo seeder
├── requirements.txt            # Pinned Python dependencies
├── README.md                   # Complete documentation
├── .env.example                # Environment variable template
├── .gitignore                  # Git tracking exclusion rules
│
├── instance/
│   └── exam.db                 # Local SQLite database instance
│
├── models/
│   ├── __init__.py             # Model exports
│   ├── user.py                 # User model (Student/Admin roles, scrypt hashing)
│   ├── exam.py                 # Exam model (Duration, marks, status)
│   ├── question.py             # Question bank model (Options, correct key, negative marks)
│   ├── attempt.py              # ExamAttempt and Answer models
│   └── proctoring.py           # ProctoringSession and ProctoringEvent models
│
├── ml/
│   ├── __init__.py             # ML package exports
│   ├── face_detector.py        # OpenCV face presence & count detector
│   ├── head_pose.py            # Geometric head pose & sustained movement estimator
│   ├── gaze_detector.py        # Eye region pupil centroid gaze estimator
│   ├── phone_detector.py       # Smartphone geometry & gradient prohibited zone detector
│   └── proctoring_engine.py    # Unified CV coordinator with frame annotation
│
├── services/
│   ├── __init__.py             # Service package exports
│   ├── exam_service.py         # Exam lifecycle, attempt resumption, answer auto-save
│   ├── result_service.py       # Score evaluation, negative marking, outcome analysis
│   ├── proctoring_service.py   # Frame ingest, snapshot persistence, anomaly logger
│   └── risk_engine.py          # Penalty weight mapping and risk categorization
│
├── utils/
│   └── decorators.py           # Role-based access decorators (@admin_required, @student_required)
│
├── routes/
│   ├── __init__.py             # Blueprint package exports
│   ├── auth.py                 # Authentication routes (login, register, logout)
│   ├── student.py              # Student portal (dashboard, available exams, history)
│   ├── exam.py                 # Exam flow (instructions, verification, take exam, submit)
│   ├── admin.py                # Admin portal (analytics, CRUD, audit timelines, reports)
│   └── api.py                  # REST APIs (proctoring frames, events, answers, stats)
│
├── templates/
│   ├── base.html               # Master layout with responsive navbar, toasts, and footer
│   ├── landing.html            # Public landing page with animated HUD showcase
│   ├── about.html              # Capstone project documentation & architecture diagram
│   ├── errors/                 # 403 Forbidden, 404 Not Found, 500 Server Error
│   ├── auth/                   # login.html, register.html
│   ├── student/                # dashboard.html, exams.html, instructions.html, verification.html, exam.html, result.html, history.html
│   └── admin/                  # dashboard.html, exams.html, create_exam.html, edit_exam.html, questions.html, students.html, attempts.html, proctoring.html, proctoring_detail.html, reports.html, settings.html
│
├── static/
│   ├── css/
│   │   ├── style.css           # Global design system & animations
│   │   ├── dashboard.css       # Analytics and timeline styling
│   │   └── exam.css            # Distraction-free exam UI & live proctoring HUD
│   ├── js/
│   │   ├── main.js             # Toast notification system
│   │   ├── proctoring.js       # Client webcam streamer, event interceptors
│   │   ├── exam.js             # Question palette, auto-saver, timer manager
│   │   └── dashboard.js        # Chart.js analytics controllers
│   └── images/
│
├── uploads/
│   ├── screenshots/            # Flagged photographic violation evidence
│   └── profiles/               # Candidate profile images
│
└── tests/
    ├── test_auth.py            # Authentication & role isolation tests
    ├── test_exam.py            # Exam lifecycle & scoring evaluation tests
    ├── test_proctoring.py      # Risk engine & anomaly detection tests
    └── test_api_and_admin.py   # End-to-end REST API & administrative export tests
```

---

## 💻 Windows Setup & Execution Guide

Follow these exact steps to set up and run the application locally on Windows:

### Step 1: Open Terminal in Project Directory
Open **PowerShell** or **Command Prompt** in `d:\Online Examination and Proctoring System`.

### Step 2: Create and Activate Virtual Environment
```powershell
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Required Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Initialize and Seed the Database
```powershell
python init_db.py
```
*This initializes SQLite tables and seeds the administrator account, demo students, 3 realistic Computer Science examinations (30 questions), and sample proctoring events.*

### Step 5: Start the Flask Application
```powershell
python app.py
```

### Step 6: Access the Web Portal
Open your web browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 🔑 Demo Login Credentials

The database initialization script (`init_db.py`) pre-configures verified demonstration accounts:

| Role | Email Address | Password | Privileges |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin@example.com` | `Admin@123` | Full access to Analytics, Exam CRUD, Question Bank, Proctoring Surveillance, and PDF/CSV Reports |
| **Student (Candidate 1)** | `student@example.com` | `Student@123` | Clean candidate profile ready to take new proctored examinations |
| **Student (Candidate 2)** | `alex@example.com` | `Student@123` | Pre-evaluated candidate profile with completed exam and rich proctoring audit timeline |

*Tip: The login page includes one-click "Admin Demo" and "Student Demo" autofill buttons for quick presentation testing.*

---

## 🧪 Running Automated Tests

Execute the comprehensive test suite verifying authentication, exam lifecycle, risk scoring, and report exports:

```powershell
venv\Scripts\python -m unittest discover -s tests -p "test_*.py"
```

All 12 automated test cases will run and confirm:
- Registration, validation, and role authorization isolation.
- Question creation, marks, and negative marking calculation.
- Live answer persistence and submission locking.
- Dynamic penalty weights and risk classification.
- CSV and PDF document generation.

---

## ⚙️ Proctoring Penalty Calibration Matrix

| Security Anomaly Event | Severity Tier | Risk Weight | Primary Detection Mechanism |
| :--- | :---: | :---: | :--- |
| `PHONE_DETECTED` | **HIGH** | **+30** | Smartphone geometry, screen contrast & prohibited zone violation |
| `MULTIPLE_FACES` | **HIGH** | **+30** | OpenCV Haar Frontal Face Cascade (Count > 1) |
| `CAMERA_DISABLED` | **HIGH** | **+25** | MediaStream track interruption or permission denial |
| `COPY_ATTEMPT` | **HIGH** | **+20** | DOM clipboard copy interceptor |
| `PASTE_ATTEMPT` | **HIGH** | **+20** | DOM clipboard paste interceptor |
| `TAB_SWITCH` | **MEDIUM** | **+15** | HTML5 Page Visibility API (`visibilitychange`) |
| `FULLSCREEN_EXIT` | **MEDIUM** | **+15** | HTML5 Fullscreen API (`fullscreenchange`) |
| `SUSPICIOUS_ACTIVITY` | **MEDIUM** | **+15** | DevTools keyboard shortcut attempts (F12, Ctrl+Shift+I) |
| `NO_FACE` | **HIGH** | **+10** | Sustained facial absence in video frame |
| `WINDOW_BLUR` | **LOW** | **+10** | Window focus event (`blur`) |
| `LOOKING_AWAY` | **MEDIUM** | **+05** | Sustained head pose yaw/pitch deviation |
| `HEAD_MOVEMENT` | **LOW** | **+05** | Head coordinate asymmetry |
| `RIGHT_CLICK` | **LOW** | **+05** | DOM context menu interceptor |
| `FACE_NOT_CENTERED` | **LOW** | **+03** | Face bounding box offset from camera center |

---

## 🛡️ Privacy & Ethical AI Declaration

1. **Lightweight Sampling vs. Constant Streaming**: The system does not stream continuous high-bandwidth video files to the server. Periodic snapshots (1 frame every 2 seconds) are sampled, minimizing bandwidth consumption and preserving privacy.
2. **Selective Evidence Archiving**: Photographic snapshots are stored only when high-severity anomalies trigger (such as multiple people detected or unauthorized exits), allowing verification without bulk surveillance storage.
3. **Assisted Review Policy**: The system flags potential suspicious events to aid human educators. It is designed never to disqualify a student arbitrarily without human administrative verification.

---

## 🚀 Future Roadmap & Enhancements
- Integration of MediaPipe 3D Face Mesh for fine iris gaze estimation.
- Dual-camera proctoring via secondary mobile QR code pairing.
- Automated question paper generation using Large Language Models (LLMs).
- WebRTC real-time 2-way audio/video intercom between human proctors and students.

---

## 📜 Academic Attribution
**Academic Level**: Final Year Computer Science / MCA Project  
**Author / Developer**: Full-Stack AI & Cybersecurity Engineering  
**Release Year**: 2026  
**License**: Open Academic Research License
#   A I - P r o c t o r E x a m  
 