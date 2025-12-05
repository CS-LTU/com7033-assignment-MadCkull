// admin_dashboard.js
// Logic for fetching stats and rendering charts for Admin Dashboard

(function () {
  let charts = {}; // Store chart instances to destroy them before re-rendering

  // --- Helper to get current theme colors ---
  function getThemeColor(varName) {
      return getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
  }

  async function fetchStats() {
    try {
      const response = await fetch("/admin/dashboard/api/stats", {
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "Content-Type": "application/json",
        },
      });
      if (!response.ok) throw new Error("Failed to fetch stats");
      return await response.json();
    } catch (error) {
      console.error("Admin Stats Error:", error);
      window.notify.error("Could not load dashboard statistics.");
      return null;
    }
  }

  function renderCharts(data) {
    // Get dynamic colors
    const colorTextMain = getThemeColor('--text-main');
    const colorBorder = getThemeColor('--border-light');
    const colorPrimary = getThemeColor('--color-primary');
    const colorPrimaryHover = getThemeColor('--color-primary-hover');
    // For transparent fills, we can use a fixed opacity helper or hardcode simple alphas if needed.
    // Here we'll just use the primary color with a fixed alpha for the line chart fill if possible,
    // or just use the hex if it's simple. 
    // Since --color-primary is hex, we can't easily add alpha without conversion. 
    // Let's use the --color-primary-rgb var if available, or just use the opaque color for lines.
    const colorPrimaryRgb = getThemeColor('--color-primary-rgb'); // "r, g, b"

    // 1. Role Distribution (Doughnut)
    const ctxRole = document.getElementById("adminRoleChart");
    if (ctxRole) {
      if (charts.role) charts.role.destroy();
      
      charts.role = new Chart(ctxRole, {
        type: "doughnut",
        data: {
          labels: ["Admin", "Doctor", "Nurse"],
          datasets: [{
            data: data.roles,
            backgroundColor: [
              colorTextMain,       // Admin (Use Main Text Color -> Black/White)
              "#3068d1ff",        // Doctor (Use Theme Primary -> Blue/Whiteish)
              "#30d158"            // Nurse (Green - fixed is fine, or use success color)
            ],
            borderColor: getThemeColor('--bg-card'), // Border matches card bg for separation
            borderWidth: 2,
            hoverOffset: 4
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'bottom',
              labels: { 
                 color: colorTextMain,
                 usePointStyle: true,
                 padding: 20,
                 font: { family: '-apple-system', size: 12 }
              }
            }
          },
          cutout: '75%'
        }
      });
    }

    // 2. User Growth (Line)
    const ctxGrowth = document.getElementById("adminGrowthChart");
    if (ctxGrowth) {
      if (charts.growth) charts.growth.destroy();

      charts.growth = new Chart(ctxGrowth, {
        type: "line",
        data: {
          labels: data.growth.labels,
          datasets: [{
            label: "New Users",
            data: data.growth.data,
            borderColor: colorPrimary,
            backgroundColor: `rgba(${colorPrimaryRgb}, 0.1)`, // Theme aware fill
            tension: 0.4,
            fill: true,
            pointRadius: 4,
            pointHoverRadius: 6,
            pointBackgroundColor: colorPrimary,
            pointBorderColor: getThemeColor('--bg-card')
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
              grid: { borderDash: [5, 5], color: colorBorder },
              ticks: { precision: 0, color: colorTextMain }
            },
            x: {
              grid: { display: false },
              ticks: { color: colorTextMain }
            }
          }
        }
      });
    }
  }

  async function initAdminDashboard() {
    const data = await fetchStats();
    if (data && data.success) {
      // Update KPIs
      const setText = (id, val) => {
          const el = document.getElementById(id);
          if(el) el.innerText = val;
      };
      
      setText("kpiTotalUsers", data.kpis.total);
      setText("kpiLocked", data.kpis.locked);
      setText("kpiDoctors", data.kpis.doctors);
      setText("kpiNurses", data.kpis.nurses);

      // Render Charts
      renderCharts(data.charts);
    }
  }

  // --- Observer to refresh stats when dashboard reappears ---
  const dashRoot = document.getElementById("adminDashboardRoot");
  if (dashRoot) {
      const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
          if (
            mutation.type === "attributes" &&
            mutation.attributeName === "class"
          ) {
            // If 'view-active' is REMOVED, it means dashboard is reappearing (not fading out)
            // Wait, logic is: view-active means "Moved Away / Hidden". 
            // So removing 'view-active' means "Coming Back / Visible".
            if (!dashRoot.classList.contains("view-active")) {
               initAdminDashboard();
            }
          }
        });
      });
      
      observer.observe(dashRoot, { attributes: true, attributeFilter: ["class"] });
  }

  // Expose init globally so it can be called when partial is loaded
  window.initAdminDashboard = initAdminDashboard;
  
  // Auto-init if element exists immediately
  if (document.getElementById("adminDashboardRoot")) {
      initAdminDashboard();
  }
})();
