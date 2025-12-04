// =======================================================
// app_router.js (Updated for Shell Architecture)
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

    // 2. Show Loader inside the content area (not destroying the whole window)
    contentArea.innerHTML = `
      <div class="view-error-state" style="color:#888;">
        <div class="spinner-mac" style="border-top-color:#0071e3;"></div>
      </div>`;

    // 3. Update Header (Title & Back Button)
    if (window.updateShellHeader) window.updateShellHeader(viewId);

    try {
      const response = await fetch(url, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });

      if (!response.ok) throw new Error(`Server status: ${response.status}`);

      const html = await response.text();

      // 4. Inject Content
      contentArea.innerHTML = `<div class="view-scroll-container animate-slide-in-right">${html}</div>`;
      return true;
    } catch (err) {
      console.error("View Load Error:", err);
      contentArea.innerHTML = `
        <div class="view-error-state">
           <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-bottom:10px;"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
           <p>Unable to load content.<br><span style="font-size:12px; opacity:0.7">${err.message}</span></p>
           <button class="details-button" style="margin-top:15px;" onclick="location.reload()">Retry</button>
        </div>
      `;
      return false;
    }
  }

  async function renderView(viewId, patientId = null) {
    let url;
    switch (viewId) {
      case "list":
        url = "/patient/views/list";
        break;
      case "add":
        url = "/patient/views/add";
        break;
      case "details":
        if (!patientId) return;
        url = `/patient/views/details/${patientId}`;
        break;
      case "search":
        toggleViewActive(false);
        if (window.animateShellClose) await window.animateShellClose();
        previousView = null;
        return;
      default:
        return;
    }

    // 1. If we are coming from Search (hidden), activate the UI
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
    searchContainer = window.searchContainer;
    window.addEventListener("hashchange", hashChangeHandler);
    hashChangeHandler();
  });
})();
