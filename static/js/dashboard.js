function createLineChart(canvasId, labels, data, label) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: label,
        data: data,
        borderColor: '#00ff88',
        backgroundColor: 'rgba(0, 255, 136, 0.12)',
        tension: 0.3,
        fill: true,
        pointRadius: 5,
        pointBackgroundColor: '#00ff88',
      }],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
      },
      scales: {
        y: {
          beginAtZero: true,
          max: 100,
          grid: {
            color: 'rgba(255, 255, 255, 0.08)',
          },
          ticks: {
            color: '#a5b4fc',
            font: { weight: 'bold' },
          }
        },
        x: {
          grid: {
            color: 'rgba(255, 255, 255, 0.08)',
          },
          ticks: {
            color: '#a5b4fc',
            font: { weight: 'bold' },
          }
        }
      },
    },
  });
}

function createBarChart(canvasId, labels, data, label) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: label,
        data: data,
        backgroundColor: ['#00bcd4', '#00ff88'],
      }],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
      },
      scales: {
        y: {
          beginAtZero: true,
          max: 100,
          grid: {
            color: 'rgba(255, 255, 255, 0.08)',
          },
          ticks: {
            color: '#a5b4fc',
            font: { weight: 'bold' },
          }
        },
        x: {
          grid: {
            color: 'rgba(255, 255, 255, 0.08)',
          },
          ticks: {
            color: '#a5b4fc',
            font: { weight: 'bold' },
          }
        }
      },
    },
  });
}
