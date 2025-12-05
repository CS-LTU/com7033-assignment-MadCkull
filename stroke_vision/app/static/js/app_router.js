// app_router.js

(function () {
  let appViewRoot;
  let searchContainer;

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

  async function loadServerViewIntoShell(url, viewId) {
    const contentArea = window.ensureShellStructure();
    if (!contentArea) return false;

    contentArea.innerHTML = `
      <div class="view-error-state" style="color:#888;">
        <div class="spinner-mac" style="border-top-color:#0071e3;"></div>
      </div>`;

    if (window.updateShellHeader) window.updateShellHeader(viewId, previousView);

    try {
      const resp = await fetch(url, {
        credentials: "same-origin",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
        },
      });

      if (!resp.ok) {
        throw new Error(`Failed to load view: ${resp.status}`);
      }

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

  async function renderView(viewId, patientId = null) {
    let url = "";

    if (viewId === "list") {
      url = "/patient/views/list";
    } else if (viewId === "add" && patientId) {
      url = `/patient/form/${patientId}`;
    } else if (viewId === "add") {
      url = "/patient/form";
    } else if (viewId === "details" && patientId) {
      url = `/patient/views/details/${patientId}`;
    } else if (viewId === "settings") {
      url = "/settings/view";
    } else if (viewId === "users") {
      url = "/admin/users/view";
    } else if (viewId === "dashboard") {
      url = "/dashboard/view";
    } else if (viewId === "activity") {
      url = "/logs/view/activity";
    } else if (viewId === "changelog") {
      url = "/logs/view/changelog";
    } else if (viewId === "search") {
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

    if (
      !document.getElementById("appViewRoot").classList.contains("is-active")
    ) {
      toggleViewActive(true);
      if (window.animateShellOpen) window.animateShellOpen();
    }

    const loaded = await loadServerViewIntoShell(url, viewId);

    if (loaded) {
      if (viewId === "list" && window.loadPatientListAndAttachScroll) {
        setTimeout(() => window.loadPatientListAndAttachScroll(1, true), 50);
      }

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
    const viewId = parts[1];
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

    window.addEventListener("hashchange", hashChangeHandler);

    if (window.location.hash) {
      hashChangeHandler();
    } else {
      window.handleViewNavigation(null, "search");
    }
  });
})();
