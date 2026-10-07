/**
 * ADMIN & ANALYTICS DASHBOARD SCRIPT
 * Configures Chart.js visual analytics and table filters.
 */

window.DashboardAnalytics = {
  initCharts(data = {}) {
    // 1. Pass / Fail Pie Chart
    const passFailCtx = document.getElementById('passFailChart');
    if (passFailCtx && data.passFail) {
      new Chart(passFailCtx, {
        type: 'doughnut',
        data: {
          labels: ['Passed', 'Failed'],
          datasets: [{
            data: [data.passFail.passed || 0, data.passFail.failed || 0],
            backgroundColor: ['#10b981', '#ef4444'],
            borderWidth: 2,
            borderColor: '#ffffff'
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: 'bottom' }
          },
          cutout: '65%'
        }
      });
    }

    // 2. Risk Level Distribution
    const riskCtx = document.getElementById('riskChart');
    if (riskCtx && data.riskDist) {
      new Chart(riskCtx, {
        type: 'doughnut',
        data: {
          labels: ['Low (0-20)', 'Medium (21-50)', 'High (51-80)', 'Critical (81+)'],
          datasets: [{
            data: [
              data.riskDist.LOW || 0,
              data.riskDist.MEDIUM || 0,
              data.riskDist.HIGH || 0,
              data.riskDist.CRITICAL || 0
            ],
            backgroundColor: ['#10b981', '#f59e0b', '#f97316', '#ef4444'],
            borderWidth: 2,
            borderColor: '#ffffff'
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: 'bottom' }
          },
          cutout: '60%'
        }
      });
    }

    // 3. Proctoring Violations By Type (Bar Chart)
    const violationsCtx = document.getElementById('violationsChart');
    if (violationsCtx && data.violationTypes) {
      const labels = Object.keys(data.violationTypes);
      const counts = Object.values(data.violationTypes);

      new Chart(violationsCtx, {
        type: 'bar',
        data: {
          labels: labels.length ? labels : ['No Violations'],
          datasets: [{
            label: 'Incidents Logged',
            data: counts.length ? counts : [0],
            backgroundColor: '#6366f1',
            borderRadius: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false }
          },
          scales: {
            y: {
              beginAtZero: true,
              ticks: { precision: 0 }
            }
          }
        }
      });
    }
  },

  initTableFilter(inputId, tableId) {
    const input = document.getElementById(inputId);
    const table = document.getElementById(tableId);
    if (!input || !table) return;

    input.addEventListener('keyup', () => {
      const filter = input.value.toLowerCase();
      const rows = table.getElementsByTagName('tr');

      for (let i = 1; i < rows.length; i++) {
        const text = rows[i].textContent || rows[i].innerText;
        if (text.toLowerCase().indexOf(filter) > -1) {
          rows[i].style.display = '';
        } else {
          rows[i].style.display = 'none';
        }
      }
    });
  }
};
