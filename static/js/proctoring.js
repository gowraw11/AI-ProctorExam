/**
 * AI PROCTORING CLIENT CONTROLLER
 * Handles Webcam Stream, Periodic CV Sampling, Security Restrictions,
 * Anomaly Event Logging, Thermal Heat Map Overlays, Web Audio Loud Alarms,
 * and Real-Time HUD Status Updates.
 */

class ProctoringClient {
  constructor(config = {}) {
    this.attemptId = config.attemptId;
    this.frameInterval = (config.frameInterval || 2.0) * 1000;
    this.demoMode = config.demoMode || false;
    this.videoElement = document.getElementById(config.videoId || 'proctoringVideo');
    this.canvas = document.createElement('canvas');
    this.stream = null;
    this.intervalId = null;
    this.isProcessing = false;
    this.tabSwitchCount = 0;
    this.fullscreenExitCount = 0;
    this.isMonitoringActive = false;
    this.missingFaceStreak = 0;
    this.lastFaceWarningTime = 0;
    this.lastMultipleFacesToast = 0;
    this.lastPhoneAlarmTime = 0;

    // Sound Alarm & Web Audio API
    this.soundAlarmEnabled = true;
    this.audioCtx = null;

    // HUD Elements
    this.faceStatusEl = document.getElementById('hudFaceStatus');
    this.headStatusEl = document.getElementById('hudHeadStatus');
    this.hudPhoneStatus = document.getElementById('hudPhoneStatus');
    this.hudPhoneBanner = document.getElementById('hudPhoneBanner');
    this.unwantedRegionBox = document.getElementById('unwantedRegionBox');
    this.hudHeatmapCanvas = document.getElementById('hudHeatmapCanvas');
    this.hudHeatmapBadge = document.getElementById('hudHeatmapBadge');
    this.webcamHudBox = document.getElementById('webcamHudBox');
    this.riskScoreEl = document.getElementById('hudRiskScore');
    this.riskLevelEl = document.getElementById('hudRiskLevel');
    this.riskFillEl = document.getElementById('hudRiskFill');
    this.violationFeedEl = document.getElementById('hudViolationFeed');
    this.fullscreenOverlay = document.getElementById('fullscreenOverlay');

    this.initSecurityListeners();

    // Prepare Web Audio on earliest candidate interaction
    const unlockAudio = () => this.initAudio();
    document.addEventListener('click', unlockAudio, { once: true });
    document.addEventListener('keydown', unlockAudio, { once: true });
  }

  /* ---------------- SOUND ALARM SYSTEM (Web Audio API) ---------------- */

  initAudio() {
    if (!this.audioCtx) {
      const AudioCtxClass = window.AudioContext || window.webkitAudioContext;
      if (AudioCtxClass) {
        this.audioCtx = new AudioCtxClass();
      }
    }
    if (this.audioCtx && this.audioCtx.state === 'suspended') {
      this.audioCtx.resume();
    }
  }

  playAlarmSound(type = 'phone_alert') {
    if (!this.soundAlarmEnabled) return;
    this.initAudio();
    if (!this.audioCtx) return;

    try {
      const now = this.audioCtx.currentTime;

      // Visual pulse indicators on HUD alarm toolbar
      const alarmBar = document.querySelector('.sound-alarm-bar');
      const alarmBell = document.getElementById('alarmBellIcon');
      if (alarmBar) alarmBar.classList.add('alarm-sounding');
      if (alarmBell) alarmBell.classList.add('alarm-bell-ringing');
      setTimeout(() => {
        if (alarmBar) alarmBar.classList.remove('alarm-sounding');
        if (alarmBell) alarmBell.classList.remove('alarm-bell-ringing');
      }, 2500);

      if (type === 'phone_alert') {
        // Dual Audio Trigger: Play HTML5 audio element for guaranteed sound
        const audioEl = document.getElementById('proctorAlarmAudio');
        if (audioEl) {
          audioEl.currentTime = 0;
          audioEl.volume = 1.0;
          audioEl.play().catch(e => console.log("AudioElement play notice:", e));
        }

        // High-Priority Loud Emergency Siren: Sweeps rapidly between 960Hz and 640Hz
        const osc = this.audioCtx.createOscillator();
        const gain = this.audioCtx.createGain();
        osc.type = 'sawtooth';

        // Frequency sweep siren curve
        osc.frequency.setValueAtTime(960, now);
        osc.frequency.linearRampToValueAtTime(640, now + 0.22);
        osc.frequency.linearRampToValueAtTime(960, now + 0.44);
        osc.frequency.linearRampToValueAtTime(640, now + 0.66);
        osc.frequency.linearRampToValueAtTime(960, now + 0.88);
        osc.frequency.linearRampToValueAtTime(640, now + 1.10);
        osc.frequency.linearRampToValueAtTime(960, now + 1.35);
        osc.frequency.linearRampToValueAtTime(640, now + 1.65);

        // Loud gain envelope (high volume output)
        gain.gain.setValueAtTime(0.01, now);
        gain.gain.linearRampToValueAtTime(0.85, now + 0.05);
        gain.gain.setValueAtTime(0.85, now + 1.50);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 1.95);

        osc.connect(gain);
        gain.connect(this.audioCtx.destination);

        osc.start(now);
        osc.stop(now + 2.0);
      } else if (type === 'face_warning') {
        // Dual-tone Warning Buzzer: 580Hz & 880Hz chime
        const osc1 = this.audioCtx.createOscillator();
        const osc2 = this.audioCtx.createOscillator();
        const gain = this.audioCtx.createGain();

        osc1.type = 'sine';
        osc2.type = 'triangle';

        osc1.frequency.setValueAtTime(587.33, now);
        osc1.frequency.setValueAtTime(880.00, now + 0.16);

        osc2.frequency.setValueAtTime(440.00, now);
        osc2.frequency.setValueAtTime(659.25, now + 0.16);

        gain.gain.setValueAtTime(0.01, now);
        gain.gain.linearRampToValueAtTime(0.60, now + 0.03);
        gain.gain.setValueAtTime(0.60, now + 0.35);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.70);

        osc1.connect(gain);
        osc2.connect(gain);
        gain.connect(this.audioCtx.destination);

        osc1.start(now);
        osc2.start(now);
        osc1.stop(now + 0.75);
        osc2.stop(now + 0.75);
      }
    } catch (err) {
      console.warn("Audio alarm playback error:", err);
    }
  }

  testAlarmSound() {
    this.initAudio();
    this.playAlarmSound('phone_alert');
    if (window.AppToast) {
      window.AppToast.show("Loud proctoring siren test playing.", "warning");
    }
  }

  toggleSoundAlarm() {
    this.soundAlarmEnabled = !this.soundAlarmEnabled;
    const badge = document.getElementById('alarmStatusBadge');
    const icon = document.getElementById('toggleSoundIcon');
    const bell = document.getElementById('alarmBellIcon');

    if (this.soundAlarmEnabled) {
      this.initAudio();
      if (badge) { badge.className = 'badge bg-danger text-white'; badge.innerText = 'LOUD ON'; }
      if (icon) { icon.className = 'fas fa-volume-xmark'; }
      if (bell) { bell.className = 'fas fa-bell text-warning alarm-bell-active'; }
      if (window.AppToast) window.AppToast.show("Proctor Sound Alarm is ENABLED (LOUD).", "success");
    } else {
      if (badge) { badge.className = 'badge bg-secondary text-white'; badge.innerText = 'MUTED'; }
      if (icon) { icon.className = 'fas fa-volume-high'; }
      if (bell) { bell.className = 'fas fa-bell-slash text-secondary'; }
      if (window.AppToast) window.AppToast.show("Proctor Sound Alarm is MUTED.", "secondary");
    }
  }

  /* ---------------- THERMAL HEAT MAP RENDERER ---------------- */

  renderThermalHeatmap(boxes = null) {
    if (!this.hudHeatmapCanvas || !this.videoElement) return;

    const canvas = this.hudHeatmapCanvas;
    const vW = this.videoElement.clientWidth || 300;
    const vH = this.videoElement.clientHeight || 225;

    canvas.width = vW;
    canvas.height = vH;
    canvas.style.display = 'block';

    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, vW, vH);

    // Dark ambient thermal background tint
    ctx.fillStyle = 'rgba(15, 23, 42, 0.40)';
    ctx.fillRect(0, 0, vW, vH);

    // Default target hotspot: bottom-center desk workspace
    const targetBoxes = (boxes && boxes.length > 0) ? boxes : [
      [vW * 0.35, vH * 0.42, vW * 0.32, vH * 0.45]
    ];

    targetBoxes.forEach(b => {
      let x = b[0], y = b[1], w = b[2], h = b[3];
      // Scale if coordinates come from 360x270 frame
      if (w < vW * 0.6 && h < vH * 0.6 && b[0] < 360) {
        const scaleX = vW / 360.0;
        const scaleY = vH / 270.0;
        x = x * scaleX;
        y = y * scaleY;
        w = w * scaleX;
        h = h * scaleY;
      }

      const cx = x + w / 2;
      const cy = y + h / 2;
      const radius = Math.max(w, h) * 0.90;

      // Vivid Radial Thermal Gradient: White-Hot -> Red -> Yellow -> Cyan -> Violet
      const grad = ctx.createRadialGradient(cx, cy, 2, cx, cy, radius);
      grad.addColorStop(0.00, 'rgba(255, 255, 255, 0.95)'); // White Core
      grad.addColorStop(0.20, 'rgba(239, 68, 68, 0.90)');   // Intense Red
      grad.addColorStop(0.45, 'rgba(245, 158, 11, 0.75)');  // Orange / Yellow
      grad.addColorStop(0.70, 'rgba(6, 182, 212, 0.50)');   // Cyan / Thermal Blue
      grad.addColorStop(1.00, 'rgba(15, 23, 42, 0.00)');    // Dissipation

      ctx.save();
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, Math.PI * 2);
      ctx.fill();

      // Pulsating Thermal Target Crosshair & Reticle
      ctx.strokeStyle = '#fef08a';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.arc(cx, cy, Math.min(w, h) * 0.5, 0, Math.PI * 2);
      ctx.stroke();
      ctx.setLineDash([]);

      // Crosshair lines
      ctx.strokeStyle = '#ef4444';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(cx - 16, cy); ctx.lineTo(cx + 16, cy);
      ctx.moveTo(cx, cy - 16); ctx.lineTo(cx, cy + 16);
      ctx.stroke();

      // Hotspot readout text
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 10px monospace';
      ctx.fillText('HOTSPOT 98.4%', cx + 18, cy - 6);
      ctx.fillStyle = '#f59e0b';
      ctx.font = '9px monospace';
      ctx.fillText('RF/CONTRABAND', cx + 18, cy + 8);

      ctx.restore();
    });

    if (this.hudHeatmapBadge) {
      this.hudHeatmapBadge.style.display = 'block';
    }
  }

  clearThermalHeatmap() {
    if (this.hudHeatmapCanvas) {
      const ctx = this.hudHeatmapCanvas.getContext('2d');
      ctx.clearRect(0, 0, this.hudHeatmapCanvas.width, this.hudHeatmapCanvas.height);
      this.hudHeatmapCanvas.style.display = 'none';
    }
    if (this.hudHeatmapBadge) {
      this.hudHeatmapBadge.style.display = 'none';
    }
  }

  /* ---------------- WEBCAM & CV MONITORING ---------------- */

  async startCamera() {
    try {
      this.initAudio();
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          facingMode: 'user'
        },
        audio: false
      });

      if (this.videoElement) {
        this.videoElement.srcObject = this.stream;
        await this.videoElement.play();
      }

      this.isMonitoringActive = true;
      this.startFrameSampling();
      if (window.AppToast) window.AppToast.show("Proctoring camera active and secure.", "success");
      return true;
    } catch (err) {
      console.warn("Webcam access error:", err);
      if (this.demoMode) {
        if (window.AppToast) window.AppToast.show("[DEMO MODE] Running simulated camera feed.", "warning");
        this.isMonitoringActive = true;
        this.startFrameSampling(true);
        return true;
      } else {
        if (window.AppToast) window.AppToast.show("Camera permission required for proctoring. Please allow camera access.", "danger");
        this.logEvent('CAMERA_DISABLED', 'Camera stream was refused or is unavailable.');
        return false;
      }
    }
  }

  stopCamera() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    this.isMonitoringActive = false;
  }

  captureFrame() {
    if (!this.videoElement || !this.videoElement.videoWidth) return null;
    this.canvas.width = 360;
    this.canvas.height = 270;
    const ctx = this.canvas.getContext('2d');
    ctx.drawImage(this.videoElement, 0, 0, this.canvas.width, this.canvas.height);
    return this.canvas.toDataURL('image/jpeg', 0.7);
  }

  startFrameSampling(isSimulated = false) {
    if (this.intervalId) clearInterval(this.intervalId);

    this.intervalId = setInterval(async () => {
      if (this.isProcessing || !this.isMonitoringActive) return;

      let frameB64 = isSimulated ? 'SIMULATE' : this.captureFrame();
      if (!frameB64) return;

      this.isProcessing = true;
      try {
        const response = await fetch('/api/proctoring/frame', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            attempt_id: this.attemptId,
            image: frameB64,
            is_demo: this.demoMode || isSimulated
          })
        });

        if (response.ok) {
          const data = await response.json();
          this.updateHUD(data);
        }
      } catch (err) {
        console.error("Frame processing failed:", err);
      } finally {
        this.isProcessing = false;
      }
    }, this.frameInterval);
  }

  updateHUD(data) {
    if (!data.success) return;

    // 1. Face count & status
    if (this.faceStatusEl) {
      if (data.face_count === 1) {
        this.missingFaceStreak = 0;
        this.faceStatusEl.innerHTML = '<span class="text-success"><i class="fas fa-check-circle"></i> Single Face (1)</span>';
      } else if (data.face_count > 1) {
        this.missingFaceStreak = 0;
        this.faceStatusEl.innerHTML = `<span class="text-danger"><i class="fas fa-users"></i> Multiple Faces (${data.face_count})</span>`;
        const now = Date.now();
        if (!this.lastMultipleFacesToast || (now - this.lastMultipleFacesToast > 15000)) {
          this.lastMultipleFacesToast = now;
          this.playAlarmSound('face_warning');
          if (window.AppToast) window.AppToast.show(`Multiple faces detected (${data.face_count}). This has been recorded.`, 'danger');
        }
      } else {
        this.missingFaceStreak = (this.missingFaceStreak || 0) + 1;
        if (this.missingFaceStreak < 3) {
          // Grace period (0 to 4s) - do not raise an alarm
          this.faceStatusEl.innerHTML = '<span class="text-warning"><i class="fas fa-arrows-to-eye"></i> Detecting Face...</span>';
        } else {
          // Sustained absence (>= 6s)
          this.faceStatusEl.innerHTML = '<span class="text-danger"><i class="fas fa-user-slash"></i> Face Missing</span>';
          const now = Date.now();
          if (!this.lastFaceWarningTime || (now - this.lastFaceWarningTime > 20000)) {
            this.lastFaceWarningTime = now;
            this.playAlarmSound('face_warning');
            if (window.AppToast) window.AppToast.show("Your face is not visible in camera. Please face the webcam.", 'warning');
          }
        }
      }
    }

    // 2. Head direction & gaze
    if (this.headStatusEl) {
      const head = data.head_direction || 'CENTER';
      const gaze = data.gaze_direction || 'CENTER';
      if (head === 'CENTER' && gaze === 'CENTER') {
        this.headStatusEl.innerHTML = '<span class="text-success"><i class="fas fa-eye"></i> Looking at Screen</span>';
      } else {
        this.headStatusEl.innerHTML = `<span class="text-warning"><i class="fas fa-arrows-alt"></i> Facing ${head}</span>`;
      }
    }

    // 3. Mobile Phone, Thermal Heat Map & Loud Alarm
    if (data.phone_detected || data.heatmap_active) {
      if (this.hudPhoneBanner) this.hudPhoneBanner.style.display = 'block';
      if (this.webcamHudBox) this.webcamHudBox.classList.add('phone-alert');
      if (this.hudPhoneStatus) {
        this.hudPhoneStatus.innerHTML = '<span class="text-danger fw-bold"><i class="fas fa-exclamation-triangle"></i> PHONE FLAGGED</span>';
      }

      // Render glowing gradient unwanted region box if coordinates exist
      if (this.unwantedRegionBox && data.phone_boxes && data.phone_boxes.length > 0 && this.videoElement) {
        const box = data.phone_boxes[0]; // [x, y, w, h] from 360x270 frame
        const vW = this.videoElement.clientWidth || 300;
        const vH = this.videoElement.clientHeight || 225;
        const scaleX = vW / 360.0;
        const scaleY = vH / 270.0;

        this.unwantedRegionBox.style.left = `${Math.max(4, box[0] * scaleX)}px`;
        this.unwantedRegionBox.style.top = `${Math.max(4, box[1] * scaleY)}px`;
        this.unwantedRegionBox.style.width = `${Math.min(vW - 10, box[2] * scaleX)}px`;
        this.unwantedRegionBox.style.height = `${Math.min(vH - 10, box[3] * scaleY)}px`;
        this.unwantedRegionBox.style.display = 'block';

        // Render Thermal Heat Map overlay over phone coordinates
        this.renderThermalHeatmap(data.phone_boxes);
      } else {
        this.renderThermalHeatmap();
      }

      // Play loud emergency siren (throttled to at most once per 6 seconds)
      const now = Date.now();
      if (!this.lastPhoneAlarmTime || (now - this.lastPhoneAlarmTime > 6000)) {
        this.lastPhoneAlarmTime = now;
        this.playAlarmSound('phone_alert');
      }

      if (window.AppToast) {
        window.AppToast.show("CRITICAL: Mobile phone detected! Loud alarm sounded & thermal heat map active.", "danger");
      }
    } else {
      if (this.hudPhoneBanner) this.hudPhoneBanner.style.display = 'none';
      if (this.unwantedRegionBox) this.unwantedRegionBox.style.display = 'none';
      if (this.webcamHudBox) this.webcamHudBox.classList.remove('phone-alert');
      this.clearThermalHeatmap();
      if (this.hudPhoneStatus) {
        this.hudPhoneStatus.innerHTML = '<span class="text-success"><i class="fas fa-mobile-screen-button me-1"></i> No Phone</span>';
      }
    }

    // 4. Risk Score & Bar
    if (this.riskScoreEl) this.riskScoreEl.innerText = data.risk_score;
    if (this.riskLevelEl) {
      this.riskLevelEl.innerText = data.risk_level;
      this.riskLevelEl.className = `badge badge-risk-${data.risk_level.toLowerCase()}`;
    }
    if (this.riskFillEl) {
      const cappedScore = Math.min(100, Math.max(0, data.risk_score));
      this.riskFillEl.style.width = `${cappedScore}%`;
      if (data.risk_level === 'LOW') this.riskFillEl.style.backgroundColor = '#10b981';
      else if (data.risk_level === 'MEDIUM') this.riskFillEl.style.backgroundColor = '#f59e0b';
      else this.riskFillEl.style.backgroundColor = '#ef4444';
    }

    // 5. Feed items
    if (data.latest_events && data.latest_events.length > 0 && this.violationFeedEl) {
      data.latest_events.forEach(ev => {
        this.addFeedItem(ev);
      });
    }
  }

  testTriggerPhone() {
    this.initAudio();
    if (this.hudPhoneBanner) this.hudPhoneBanner.style.display = 'block';
    if (this.webcamHudBox) this.webcamHudBox.classList.add('phone-alert');
    if (this.hudPhoneStatus) {
      this.hudPhoneStatus.innerHTML = '<span class="text-danger fw-bold"><i class="fas fa-exclamation-triangle"></i> PHONE FLAGGED</span>';
    }

    // Show unwanted gradient highlight region box over bottom-center area
    if (this.unwantedRegionBox && this.videoElement) {
      const vW = this.videoElement.clientWidth || 300;
      const vH = this.videoElement.clientHeight || 225;
      this.unwantedRegionBox.style.left = `${vW * 0.35}px`;
      this.unwantedRegionBox.style.top = `${vH * 0.45}px`;
      this.unwantedRegionBox.style.width = `${vW * 0.32}px`;
      this.unwantedRegionBox.style.height = `${vH * 0.45}px`;
      this.unwantedRegionBox.style.display = 'block';

      // Render thermal heat map overlay
      this.renderThermalHeatmap([[vW * 0.35, vH * 0.45, vW * 0.32, vH * 0.45]]);
    }

    // Play loud alarm siren!
    this.playAlarmSound('phone_alert');

    this.logEvent('PHONE_DETECTED', '[DEMO TEST] Mobile phone detected with thermal heat map anomaly.');
    if (window.AppToast) {
      window.AppToast.show("CRITICAL: Mobile phone detected! Loud alarm sounded & thermal heat map active.", "danger");
    }

    // Auto-reset highlight after 5 seconds
    setTimeout(() => {
      if (this.hudPhoneBanner) this.hudPhoneBanner.style.display = 'none';
      if (this.unwantedRegionBox) this.unwantedRegionBox.style.display = 'none';
      if (this.webcamHudBox) this.webcamHudBox.classList.remove('phone-alert');
      this.clearThermalHeatmap();
      if (this.hudPhoneStatus) {
        this.hudPhoneStatus.innerHTML = '<span class="text-success"><i class="fas fa-mobile-screen-button me-1"></i> No Phone</span>';
      }
    }, 5000);
  }

  addFeedItem(ev) {
    if (!this.violationFeedEl) return;
    const timeStr = new Date().toLocaleTimeString();
    const item = document.createElement('div');
    item.className = 'feed-item';
    const badgeColor = ev.severity === 'HIGH' ? 'danger' : (ev.severity === 'MEDIUM' ? 'warning' : 'info');

    item.innerHTML = `
      <span class="text-light">${ev.event_type.replace('_', ' ')}</span>
      <span class="badge bg-${badgeColor} text-white" style="font-size: 0.65rem;">${timeStr}</span>
    `;
    this.violationFeedEl.prepend(item);
  }

  async logEvent(eventType, description) {
    try {
      const snapshot = this.captureFrame();
      const response = await fetch('/api/proctoring/event', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          attempt_id: this.attemptId,
          event_type: eventType,
          description: description,
          image: snapshot,
          is_demo: this.demoMode
        })
      });

      if (response.ok) {
        const data = await response.json();
        this.addFeedItem({
          event_type: eventType,
          severity: data.event ? data.event.severity : 'MEDIUM'
        });
        if (this.riskScoreEl && data.current_risk_score !== undefined) {
          this.riskScoreEl.innerText = data.current_risk_score;
        }
        if (this.riskLevelEl && data.current_risk_level) {
          this.riskLevelEl.innerText = data.current_risk_level;
          this.riskLevelEl.className = `badge badge-risk-${data.current_risk_level.toLowerCase()}`;
        }
      }
    } catch (err) {
      console.error("Failed to log proctoring event:", err);
    }
  }

  initSecurityListeners() {
    // 1. Tab switch / visibility change
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        this.tabSwitchCount++;
        this.logEvent('TAB_SWITCH', `Candidate switched tab or minimized browser (Count: ${this.tabSwitchCount})`);
        this.playAlarmSound('face_warning');
        if (window.AppToast) {
          window.AppToast.show(`Tab switching detected (${this.tabSwitchCount}). This activity has been recorded.`, 'danger');
        }
      }
    });

    // 2. Window Blur
    window.addEventListener('blur', () => {
      this.logEvent('WINDOW_BLUR', 'Candidate navigated away from examination window.');
    });

    // 3. Fullscreen Exit
    document.addEventListener('fullscreenchange', () => {
      if (!document.fullscreenElement) {
        this.fullscreenExitCount++;
        this.logEvent('FULLSCREEN_EXIT', `Candidate exited fullscreen mode (Count: ${this.fullscreenExitCount})`);
        this.playAlarmSound('face_warning');
        if (this.fullscreenOverlay) {
          this.fullscreenOverlay.style.display = 'flex';
        }
      } else {
        if (this.fullscreenOverlay) {
          this.fullscreenOverlay.style.display = 'none';
        }
      }
    });

    // 4. Copy / Paste / Cut / Right Click Restrictions
    document.addEventListener('copy', (e) => {
      e.preventDefault();
      this.logEvent('COPY_ATTEMPT', 'Candidate attempted clipboard copy operation.');
      if (window.AppToast) window.AppToast.show("Copying is disabled during examination.", "warning");
    });

    document.addEventListener('paste', (e) => {
      e.preventDefault();
      this.logEvent('PASTE_ATTEMPT', 'Candidate attempted clipboard paste operation.');
      if (window.AppToast) window.AppToast.show("Pasting is disabled during examination.", "warning");
    });

    document.addEventListener('contextmenu', (e) => {
      e.preventDefault();
      this.logEvent('RIGHT_CLICK', 'Candidate attempted right-click context menu.');
      if (window.AppToast) window.AppToast.show("Right-click is disabled during examination.", "warning");
    });

    // 5. Prevent DevTools shortcuts
    document.addEventListener('keydown', (e) => {
      if (
        e.key === 'F12' ||
        (e.ctrlKey && e.shiftKey && (e.key === 'I' || e.key === 'J' || e.key === 'C')) ||
        (e.ctrlKey && e.key === 'U')
      ) {
        e.preventDefault();
        this.logEvent('SUSPICIOUS_ACTIVITY', 'Candidate attempted developer tools key combination.');
        if (window.AppToast) window.AppToast.show("Developer shortcuts are strictly prohibited.", "danger");
      }
    });
  }

  requestFullscreen() {
    const elem = document.documentElement;
    if (elem.requestFullscreen) {
      elem.requestFullscreen().catch(err => console.warn(err));
    } else if (elem.webkitRequestFullscreen) {
      elem.webkitRequestFullscreen();
    }
  }
}

window.ProctoringClient = ProctoringClient;
