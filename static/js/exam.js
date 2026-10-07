/**
 * EXAM CONTROLLER SCRIPT
 * Handles question state transitions, palette navigation, auto-saving,
 * countdown timer, and exam submission.
 */

class ExamManager {
  constructor(config) {
    this.examId = config.examId;
    this.attemptId = config.attemptId;
    this.totalQuestions = config.totalQuestions;
    this.remainingSeconds = config.remainingSeconds;
    this.savedAnswers = config.savedAnswers || {};
    this.markedForReview = new Set();
    this.currentIndex = 0;

    this.timerDisplayEl = document.getElementById('examTimerDisplay');
    this.questions = document.querySelectorAll('.question-block');
    this.paletteButtons = document.querySelectorAll('.palette-btn');

    this.initTimer();
    this.initPalette();
    this.initOptions();
    this.updatePaletteColors();
    this.showQuestion(0);
  }

  showQuestion(index) {
    if (index < 0 || index >= this.totalQuestions) return;
    this.currentIndex = index;

    // Toggle blocks
    this.questions.forEach((q, idx) => {
      q.style.display = idx === index ? 'block' : 'none';
    });

    // Update active highlight on palette
    this.paletteButtons.forEach((btn, idx) => {
      btn.classList.toggle('current', idx === index);
    });

    // Update Prev / Next button states
    const prevBtn = document.getElementById('btnPrev');
    const nextBtn = document.getElementById('btnNext');
    if (prevBtn) prevBtn.disabled = index === 0;
    if (nextBtn) nextBtn.disabled = index === this.totalQuestions - 1;
  }

  nextQuestion() {
    if (this.currentIndex < this.totalQuestions - 1) {
      this.showQuestion(this.currentIndex + 1);
    }
  }

  prevQuestion() {
    if (this.currentIndex > 0) {
      this.showQuestion(this.currentIndex - 1);
    }
  }

  toggleMarkForReview() {
    const activeBlock = this.questions[this.currentIndex];
    const qId = parseInt(activeBlock.dataset.questionId);

    if (this.markedForReview.has(qId)) {
      this.markedForReview.delete(qId);
      if (window.AppToast) window.AppToast.show("Question unmarked from review.", "info", 2000);
    } else {
      this.markedForReview.add(qId);
      if (window.AppToast) window.AppToast.show("Question marked for review.", "warning", 2000);
    }
    this.updatePaletteColors();
  }

  clearAnswer() {
    const activeBlock = this.questions[this.currentIndex];
    const qId = parseInt(activeBlock.dataset.questionId);

    activeBlock.querySelectorAll('.option-item').forEach(opt => {
      opt.classList.remove('selected');
    });

    delete this.savedAnswers[qId];
    this.saveAnswerToServer(qId, null);
    this.updatePaletteColors();
    if (window.AppToast) window.AppToast.show("Answer cleared.", "info", 1500);
  }

  async selectOption(qId, selectedOption, optionElement) {
    const activeBlock = this.questions[this.currentIndex];
    activeBlock.querySelectorAll('.option-item').forEach(opt => {
      opt.classList.remove('selected');
    });
    optionElement.classList.add('selected');

    this.savedAnswers[qId] = selectedOption;
    this.updatePaletteColors();
    await this.saveAnswerToServer(qId, selectedOption);
  }

  async saveAnswerToServer(qId, selectedOption) {
    try {
      const response = await fetch(`/api/exams/${this.examId}/answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          attempt_id: this.attemptId,
          question_id: qId,
          selected_answer: selectedOption
        })
      });

      const data = await response.json();
      if (data.time_expired) {
        alert("Time expired! Your examination is being submitted.");
        this.submitExam(true);
        return;
      }
      if (data.success && selectedOption) {
        if (window.AppToast) window.AppToast.show("Answer auto-saved", "success", 1200);
      }
    } catch (err) {
      console.error("Auto-save error:", err);
    }
  }

  updatePaletteColors() {
    this.paletteButtons.forEach((btn) => {
      const qId = parseInt(btn.dataset.questionId);
      btn.classList.remove('answered', 'marked', 'unanswered');

      if (this.markedForReview.has(qId)) {
        btn.classList.add('marked');
      } else if (this.savedAnswers[qId]) {
        btn.classList.add('answered');
      } else {
        btn.classList.add('unanswered');
      }
    });

    this.updateCounters();
  }

  updateCounters() {
    const answeredCount = Object.keys(this.savedAnswers).length;
    const unansweredCount = this.totalQuestions - answeredCount;
    const markedCount = this.markedForReview.size;

    const answeredEl = document.getElementById('countAnswered');
    const unansweredEl = document.getElementById('countUnanswered');
    const markedEl = document.getElementById('countMarked');

    if (answeredEl) answeredEl.innerText = answeredCount;
    if (unansweredEl) unansweredEl.innerText = unansweredCount;
    if (markedEl) markedEl.innerText = markedCount;
  }

  initPalette() {
    this.paletteButtons.forEach((btn, idx) => {
      btn.addEventListener('click', () => {
        this.showQuestion(idx);
      });
    });
  }

  initOptions() {
    this.questions.forEach((block) => {
      const qId = parseInt(block.dataset.questionId);
      const options = block.querySelectorAll('.option-item');
      options.forEach((opt) => {
        opt.addEventListener('click', () => {
          const val = opt.dataset.option;
          this.selectOption(qId, val, opt);
        });
      });
    });
  }

  initTimer() {
    const updateDisplay = () => {
      if (this.remainingSeconds <= 0) {
        if (this.timerDisplayEl) this.timerDisplayEl.innerText = "00:00";
        clearInterval(this.timerInterval);
        this.submitExam(true);
        return;
      }

      const mins = Math.floor(this.remainingSeconds / 60);
      const secs = this.remainingSeconds % 60;
      const formatted = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;

      if (this.timerDisplayEl) {
        this.timerDisplayEl.innerText = formatted;
        if (this.remainingSeconds <= 300) {
          this.timerDisplayEl.className = 'timer-display danger';
        } else if (this.remainingSeconds <= 600) {
          this.timerDisplayEl.className = 'timer-display warning';
        }
      }

      this.remainingSeconds--;
    };

    updateDisplay();
    this.timerInterval = setInterval(updateDisplay, 1000);
  }

  prepareSubmitModal() {
    const answeredCount = Object.keys(this.savedAnswers).length;
    const unansweredCount = this.totalQuestions - answeredCount;

    const modalAnswered = document.getElementById('modalAnsweredCount');
    const modalUnanswered = document.getElementById('modalUnansweredCount');
    if (modalAnswered) modalAnswered.innerText = answeredCount;
    if (modalUnanswered) modalUnanswered.innerText = unansweredCount;

    const modal = new bootstrap.Modal(document.getElementById('confirmSubmitModal'));
    modal.show();
  }

  async submitExam(isAuto = false) {
    if (this.isSubmitting) return;
    this.isSubmitting = true;

    try {
      if (isAuto && window.AppToast) {
        window.AppToast.show("Exam duration completed. Submitting automatically...", "warning");
      }

      const response = await fetch(`/api/exams/${this.examId}/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          attempt_id: this.attemptId,
          auto_submit: isAuto
        })
      });

      if (response.ok) {
        window.location.href = `/student/result/${this.attemptId}`;
      } else {
        // Fallback form post
        document.getElementById('finalSubmitForm').submit();
      }
    } catch (err) {
      console.error("Submission failed:", err);
      document.getElementById('finalSubmitForm').submit();
    }
  }
}

window.ExamManager = ExamManager;
