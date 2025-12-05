// =======================================================
// root_view_manager.js (Shell Architecture & Animations)
// =======================================================

(function () {
  let shellCreated = false;

  window.ensureShellStructure = function () {
    const root = document.getElementById("appViewRoot");
    if (!root) return null;

    if (!shellCreated || !root.querySelector(".shell-header")) {
      root.innerHTML = `
        <!-- 1. Global Header -->
        <div class="shell-header">
          <button id="shellBackButton" class="shell-back-btn" onclick="window.handleShellBack()">
            <!-- Icons injected by JS based on state -->
          </button>
          
          <div id="shellTitle" class="shell-title">StrokeVision</div>
          
          <div style="width: 36px;"></div> 
        </div>

        <!-- 2. Scrollable Content Area -->
        <div id="shellContentArea" class="shell-content-area">
          <!-- Views are injected here -->
        </div>
      `;
      shellCreated = true;
    }

    return document.getElementById("shellContentArea");
  };

  window.updateShellHeader = function (viewId, previousView = null) {
    const backBtn = document.getElementById("shellBackButton");
    const titleEl = document.getElementById("shellTitle");

    if (!backBtn || !titleEl) return;

    const titles = {
      list: "Patient Database",
      search: "Search",
      details: "Patient Details",
      add: "Add New Record",
      dashboard: "Dashboard",
      settings: "Settings",
      users: "User Manager",
      activity: "Activity Log",
      changelog: "Change Log",
    };
    titleEl.innerText = titles[viewId] || "StrokeVision";

    const rootViews = [
      "list",
      "add",
      "dashboard",
      "settings",
      "users",
      "activity",
      "changelog",
    ];
    const isRootView = rootViews.includes(viewId);

    if (isRootView) {
      backBtn.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>`;
      backBtn.onclick = () => window.handleViewNavigation(null, "search");
    } else {
      backBtn.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>`;

      backBtn.onclick = () => {
        if (previousView && previousView !== viewId) {
          window.handleViewNavigation(null, previousView);
        } else {
          // Default fallback if no history
          window.handleViewNavigation(null, "list");
        }
      };
    }
  };

  window.animateShellOpen = function () {
    const root = document.getElementById("appViewRoot");
    if (root) {
      root.classList.remove("is-exiting");
      root.classList.add("is-active");
    }
  };

  window.animateShellClose = function () {
    const root = document.getElementById("appViewRoot");
    if (!root) return Promise.resolve();

    root.classList.add("is-exiting");
    root.classList.remove("is-active");

    return new Promise((resolve) => {
      setTimeout(() => {
        resolve();
      }, 250);
    });
  };
})();

