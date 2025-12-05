// =======================================================
// app_router.js (Updated with Settings and Users Routes)
// Minimal patch: only patient endpoints adjusted to legacy URLs
// =======================================================

(function () {
  let appViewRoot;
  let searchContainer;

  // Track previous view to determine animation direction
  let previousView = null;

  function toggleViewActive(isActive) {
    if (!searchContainer) return;
    if (isActive) {
      searchContainer.classList.add("view-active");
      if (window.changePlaceholder) window.changePlaceholder("Back to Search");
    } else {
      searchContainer.classList.remove("view-active");
      if (window.changePlaceholder) window.changePlaceholder("Search");
    }
  }

  /**
   * Fetches content and injects it into the SHELL content area.
   */
  async function loadServerViewIntoShell(url, viewId) {
    // 1. Ensure the Shell Exists
    const contentArea = window.ensureShellStructure();
    if (!contentArea) return false;

    // 2. Show Loader inside the content area
    contentArea.innerHTML = `
      <div class="view-error-state" style="color:#888;">
        <div class="spinner-mac" style="border-top-color:#0071e3;"></div>
      </div>`;

    // 3. Update Header (Title & Back Button)
    if (window.updateShellHeader) window.updateShellHeader(viewId, previousView);

    // 4. Fetch the content
    try {
      // NOTE: We fetch the HTML content directly here, NOT JSON.
      const resp = await fetch(url, {
        credentials: "same-origin",
        headers: {
          // Send a custom header to Flask to request partial templates
          "X-Requested-With": "XMLHttpRequest",
        },
      });

      if (!resp.ok) {
        throw new Error(`Failed to load view: ${resp.status}`);
      }

      // 5. Inject the content
      const htmlContent = await resp.text();

      contentArea.innerHTML = `
  <div class="view-scroll-container animate-slide-in-right">
    ${htmlContent}
  </div>`;
      return true;
    } catch (error) {
      console.error(`Error loading view fragment for ${viewId}:`, error);
      const errorMessage =
        error.message === "Failed to load view: 403"
          ? "Access Denied. You do not have permission to view this page."
          : `Could not load view: ${error.message}`;
      contentArea.innerHTML = `
        <div class="view-error-state">
          <span class="material-icons" style="font-size: 48px; color: #d11a1a; margin-bottom: 10px;">error_outline</span>
          <h2>Error Loading Page</h2>
          <p>${errorMessage}</p>
        </div>`;
      return false;
    }
  }

  /**
   * Main function to route and render the application view.
   */
  async function renderView(viewId, patientId = null) {
    let url = "";

    // Determine the server endpoint based on the viewId
    if (viewId === "list") {
      // legacy endpoint for patient list
      url = "/patient/views/list";
    } else if (viewId === "add" && patientId) {
      // reuse legacy form endpoint for editing
      url = `/patient/form/${patientId}`;
    } else if (viewId === "add") {
      // new patient form (legacy endpoint)
      url = "/patient/form";
    } else if (viewId === "details" && patientId) {
      // legacy patient details endpoint
      url = `/patient/views/details/${patientId}`;
    } else if (viewId === "settings") {
      url = "/settings/view"; // Assumed setting view
    } else if (viewId === "users") {
      url = "/admin/users/view"; // New consolidated User Manager View
    } else if (viewId === "dashboard") {
      url = "/dashboard/view";
    } else if (viewId === "activity") {
      url = "/logs/view/activity";
    } else if (viewId === "changelog") {
      url = "/logs/view/changelog";
    } else if (viewId === "search") {
      // For search, we hide the shell, so no load is needed.
      if (previousView && previousView !== "search") {
        toggleViewActive(false);
        if (window.animateShellClose) window.animateShellClose();
      }
      previousView = "search";
      return;
    } else {
      console.warn("Unknown view ID:", viewId);
      viewId = "search";
      url = null;
    }

    // If navigating from Search (hidden), activate the UI
    if (
      !document.getElementById("appViewRoot").classList.contains("is-active")
    ) {
      toggleViewActive(true);
      if (window.animateShellOpen) window.animateShellOpen();
    }

    // 2. Load the content
    const loaded = await loadServerViewIntoShell(url, viewId);

    // 3. Post-load Init
    if (loaded) {
      if (viewId === "list" && window.loadPatientListAndAttachScroll) {
        // We pass 'false' for attachScroll initially, wait for DOM render
        setTimeout(() => window.loadPatientListAndAttachScroll(1, true), 50);
      }

      // If we are on the users panel, ensure its init script runs
      if (viewId === "users" && window.userManager) {
        window.userManager.init();
      }

      if (viewId === "dashboard" && window.dashboard) {
        window.dashboard.init();
      }

      if ((viewId === "activity" || viewId === "changelog") && window.logManager) {
        window.logManager.init(viewId);
      }
    }

    previousView = viewId;
  }

  window.handleViewNavigation = function (event, viewId, patientId = null) {
    if (event) event.preventDefault();
    let newHash = viewId;
    if (patientId) newHash += `/${patientId}`;
    window.location.hash = `#/${newHash}`;
  };

  async function hashChangeHandler() {
    const hash = window.location.hash.substring(1);
    const parts = hash.split("/");
    const viewId = parts[1]; // e.g. 'settings', 'list', 'add', 'users'
    const patientId = parts[2] || null;

    if (viewId) {
      await renderView(viewId, patientId);
    } else {
      await renderView("search");
    }
  }

  window.addEventListener("DOMContentLoaded", () => {
    appViewRoot = document.getElementById("appViewRoot");
    searchContainer = document.getElementById("searchContainer");

    // Initialize the router
    window.addEventListener("hashchange", hashChangeHandler);

    // Initial load handling
    if (window.location.hash) {
      hashChangeHandler();
    } else {
      // Default view on first load
      window.handleViewNavigation(null, "search");
    }
  });
})();
