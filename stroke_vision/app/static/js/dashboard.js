/* app/static/js/dashboard.js */
(function () {
  // -- Helper to render charts --
  function renderCharts(data) {
    // 1. Metabolic Scatter Chart
    const ctx1 = document.getElementById("metabolicChart").getContext("2d");

    new Chart(ctx1, {
      type: "bubble",
      data: {
        datasets: [
          {
            label: "Patient Risk",
            data: data.scatter, // Expects {x, y, r}
            backgroundColor: (context) => {
              const raw = context.raw;
              // Red if risk > 20, else Blue
              return raw && raw.risk > 20
                ? "rgba(238, 93, 80, 0.7)"
                : "rgba(67, 24, 255, 0.5)";
            },
            borderColor: "transparent",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: {
            title: { display: true, text: "BMI" },
            grid: { borderDash: [5, 5] },
            min: 15,
            max: 40,
          },
          y: {
            title: { display: true, text: "Glucose Level" },
            grid: { display: false },
            min: 70,
            max: 200,
          },
        },
      },
    });

    // 2. Work Type Doughnut Chart
    const ctx2 = document.getElementById("workChart").getContext("2d");
    const workLabels = Object.keys(data.work_distribution);
    const workValues = Object.values(data.work_distribution);

    new Chart(ctx2, {
      type: "doughnut",
      data: {
        labels: workLabels,
        datasets: [
          {
            data: workValues,
            backgroundColor: [
              "#4318FF",
              "#6AD2FF",
              "#EFF4FB",
              "#FFB547",
              "#05CD99",
            ],
            borderWidth: 0,
            hoverOffset: 4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "70%",
        plugins: {
          legend: {
            position: "bottom",
            labels: { usePointStyle: true, font: { size: 10 }, padding: 15 },
          },
        },
      },
    });
  }

  // -- Helper to render Table --
  function renderRiskTable(patients) {
    const tbody = document.getElementById("riskTableBody");
    tbody.innerHTML = "";

    if (patients.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="6" style="text-align:center;">No high risk patients found.</td></tr>';
      return;
    }

    patients.forEach((p) => {
      const riskVal = parseFloat(p.stroke_risk);
      let badgeClass =
        riskVal > 25 ? "risk-critical" : riskVal > 15 ? "risk-mod" : "risk-low";
      let badgeText =
        riskVal > 25 ? "CRITICAL" : riskVal > 15 ? "MODERATE" : "STABLE";
      let barColor =
        riskVal > 25 ? "#EE5D50" : riskVal > 15 ? "#FFB547" : "#05CD99";
      let initial = p.name.charAt(0);

      const row = `
        <tr>
          <td style="display:flex; align-items:center; gap:10px;">
            <div style="width:28px; height:28px; background:#EFF4FB; border-radius:50%; display:flex; align-items:center; justify-content:center; color:#4318FF; font-weight:bold; font-size:12px;">${initial}</div>
            ${p.name}
          </td>
          <td>${p.age} / ${p.gender}</td>
          <td>${p.conditions}</td>
          <td>${p.avg_glucose_level}</td>
          <td>
            <div class="risk-progress-bg"><div class="risk-progress-fill" style="width:${Math.min(
              riskVal * 2,
              100
            )}%; background:${barColor}"></div></div>
            ${riskVal}%
          </td>
          <td><span class="risk-badge ${badgeClass}">${badgeText}</span></td>
        </tr>
      `;
      tbody.insertAdjacentHTML("beforeend", row);
    });
  }

  // -- Main Init Function --
  async function initDashboard() {
    // Set Date
    const dateEl = document.getElementById("currentDateDisplay");
    if (dateEl)
      dateEl.innerText = new Date().toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      });

    try {
      // Fetch Data
      const data = await window.fetchJson("/dashboard/api/stats");

      if (data.success) {
        // 1. Update KPIs
        document.getElementById("kpiTotal").innerText = data.kpis.total;
        document.getElementById("kpiHighRisk").innerText = data.kpis.high_risk;
        document.getElementById("kpiGlucose").innerText = data.kpis.avg_glucose;
        document.getElementById("kpiSmokers").innerText = data.kpis.smokers;

        // 2. Render Charts
        renderCharts(data.charts);

        // 3. Render Table
        renderRiskTable(data.table);
      }
    } catch (error) {
      console.error("Dashboard Init Error:", error);
      window.showToast("Failed to load dashboard analytics.", "danger");
    }
  }

  // Expose init method
  window.dashboard = {
    init: initDashboard,
  };
})();
