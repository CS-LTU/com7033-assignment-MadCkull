// =======================================================
// root_view_manager.js (Shell Architecture & Animations)
// =======================================================

(function () {
  let shellCreated = false;

  /**
   * Ensures the basic "Mac Window" shell structure exists in the DOM.
   * If not, it creates it.
   * Returns the container where specific view content should be injected.
   */
  window.ensureShellStructure = function () {
    const root = document.getElementById("appViewRoot");
    if (!root) return null;

    if (!shellCreated || !root.querySelector(".shell-header")) {
      // Create the persistent shell layout
      root.innerHTML = `
        <!-- 1. Global Header -->
        <div class="shell-header">
          <button id="shellBackButton" class="shell-back-btn" onclick="window.handleShellBack()">
            <!-- Icons injected by JS based on state -->
          </button>
          
          <div id="shellTitle" class="shell-title">StrokeVision</div>
          
          <div style="width: 36px;"></div> <!-- Spacer for balance -->
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

  /**
   * Updates the Global Header state (Title and Back Button mode).
   */
  window.updateShellHeader = function (viewId) {
    const backBtn = document.getElementById("shellBackButton");
    const titleEl = document.getElementById("shellTitle");

    if (!backBtn || !titleEl) return;

    // 1. Set Title
    const titles = {
      list: "Patient Database",
      search: "Search",
      details: "Patient Details",
      add: "Add New Record",
    };
    titleEl.innerText = titles[viewId] || "StrokeVision";

    // 2. Set Back Button Icon & Functionality
    // If we are at the "Root" of the modal (list or add), button is Close (X)
    // If we are deep (details), button is Back (<)
    const isRootView = ["list", "add"].includes(viewId);

    if (isRootView) {
      // Close Icon (X)
      backBtn.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>`;
      backBtn.onclick = () => window.handleViewNavigation(null, "search");
    } else {
      // Back Arrow Icon (<)
      backBtn.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>`;
      // Simple logic: Go back to list if in details
      backBtn.onclick = () => window.handleViewNavigation(null, "list");
    }
  };

  /**
   * Open the Main Window (Pop Animation)
   */
  window.animateShellOpen = function () {
    const root = document.getElementById("appViewRoot");
    if (root) {
      root.classList.remove("is-exiting");
      root.classList.add("is-active");
    }
  };

  /**
   * Close the Main Window (Scale Out)
   */
  window.animateShellClose = function () {
    const root = document.getElementById("appViewRoot");
    if (!root) return Promise.resolve();

    root.classList.add("is-exiting");
    root.classList.remove("is-active");

    return new Promise((resolve) => {
      setTimeout(() => {
        resolve();
      }, 250); // Match CSS transition
    });
  };
})();
