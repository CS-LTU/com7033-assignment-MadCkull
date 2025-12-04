// =======================================================
// app_router.js (The Central Application Router/Controller)
// Dependencies:
// - window.changePlaceholder (from utils.js)
// - window.loadPatientListAndAttachScroll (from patient_list.js)
// - Global UI elements (from search_manager.js)
// =======================================================

(function () {
  // 1. Declare ALL core UI element references as local 'let' variables.
  // They will be set inside DOMContentLoaded.
  let appViewRoot;
  let mainUiContainer;
  let spotlightContainer;
  let searchInput;
  let resultsContainer;

  // =======================================================
  // 2. VIEW MANAGEMENT & ANIMATION LOGIC
  // =======================================================

  /**
   * Toggles the visual state of the main UI shell (Searchbar vs. Active View).
   */
  function toggleViewActive(isActive) {
    // Now using the 'let' variables defined in DOMContentLoaded
    if (!mainUiContainer) return;

    if (isActive) {
      mainUiContainer.classList.add("view-active");
      // Ensure search bar UI is reset when entering a view
      if (spotlightContainer)
        spotlightContainer.classList.remove("typing-active", "hover-active");
      if (searchInput) searchInput.value = "";
      if (resultsContainer) resultsContainer.innerHTML = "";

      // Check for global helper before calling
      if (window.changePlaceholder) window.changePlaceholder("Back to Search");
    } else {
      mainUiContainer.classList.remove("view-active");
      // Use the global utility function
      if (window.changePlaceholder) window.changePlaceholder("Search");
    }
  }

  /**
   * Generic function to fetch an HTML fragment from a Flask route and inject it
   * into the main content container (#appViewRoot).
   */
  async function loadServerView(url) {
    // Safety check: ensure the root element has been set by DOMContentLoaded
    if (!appViewRoot) {
      console.error("loadServerView failed: appViewRoot not available.");
      return false;
    }

    // Show a generic loading state immediately
    appViewRoot.innerHTML = `
            <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 300px; color: #666;">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="animation: spin 1s linear infinite;">
                    <path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
                </svg>
                <p style="margin-top: 15px;">Loading content...</p>
            </div>
            <style>@keyframes spin { 100% { transform: rotate(360deg); } }</style>
        `;

    try {
      const response = await fetch(url, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });

      if (!response.ok) {
        if (response.headers.get("content-type")?.includes("text/html")) {
          const errorHtml = await response.text();
          appViewRoot.innerHTML = errorHtml;
          return false;
        }
        if (response.status === 403) {
          throw new Error(
            `Access Forbidden. Check if the Flask route is correct.`
          );
        }
        throw new Error(`Server returned status: ${response.status}`);
      }

      // Inject the successfully fetched HTML fragment
      const html = await response.text();
      appViewRoot.innerHTML = html;

      return true;
    } catch (err) {
      console.error("View Load Error:", err);
      appViewRoot.innerHTML = `
                <div class="list-header">
                    <h2>Content Error</h2>
                    <button class="back-button" onclick="window.history.back()">Back</button>
                </div>
                <p style="padding: 20px; color: #ef4444;">Failed to load view.<br><small>${err.message}</small></p>
            `;
      return false; // Failed
    }
  }

  /**
   * The main router function that maps hash segments to API endpoints.
   */
  async function renderView(viewId, patientId = null) {
    console.log(`Router: Attempting to render ${viewId} (ID: ${patientId})`);

    let url;

    switch (viewId) {
      // FIX: Prepending the Flask Blueprint prefix '/patient' to all API view requests
      case "list":
        url = "/patient/views/list"; // Corrected Flask route
        break;
      case "add":
        url = "/patient/views/add"; // Corrected Flask route
        break;
      case "details":
        if (!patientId) {
          console.error("Router: Details requires patient ID.");
          return;
        }
        url = `/patient/views/details/${patientId}`; // Corrected Flask route
        break;
      case "edit":
        if (!patientId) {
          console.error("Router: Edit requires patient ID.");
          return;
        }
        url = `/patient/views/edit/${patientId}`; // Corrected Flask route
        break;
      case "search":
        toggleViewActive(false); // Reset to search mode
        return;
      default:
        console.warn("Router: Unknown view:", viewId);
        toggleViewActive(false);
        return;
    }

    // 1. Activate View mode and clear search bar UI
    toggleViewActive(true);

    // 2. Fetch and inject the content
    const loaded = await loadServerView(url);

    // 3. Post-load initialization (if successful)
    if (loaded) {
      if (viewId === "list" && window.loadPatientListAndAttachScroll) {
        // This calls a function defined in patient_list.js
        window.loadPatientListAndAttachScroll(1, true);
      }
      // TODO: Add initialization calls here for forms later (e.g., initFormLogic())
    }
  }

  // =======================================================
  // GLOBAL NAVIGATION & INITIALIZATION
  // =======================================================

  /**
   * Exposed globally (via window) for use in HTML onclick attributes
   */
  window.handleViewNavigation = function (event, viewId, patientId = null) {
    if (event) event.preventDefault();

    let newHash = viewId;
    if (patientId) newHash += `/${patientId}`;

    // Changing the hash triggers the hashChangeHandler automatically
    window.location.hash = `#/${newHash}`;
  };

  /**
   * Shortcut for the shortcut buttons.
   */
  window.handleShortcutClick = function (event, viewId) {
    window.handleViewNavigation(event, viewId);
  };

  /**
   * Listens to hash changes and triggers the router.
   */
  async function hashChangeHandler() {
    // CRITICAL CHECK: Wait for the primary element to be found.
    if (!appViewRoot) {
      console.warn("appViewRoot not found yet. Retrying hash check in 50ms.");
      setTimeout(hashChangeHandler, 50);
      return;
    }

    const hash = window.location.hash.substring(1); // Remove '#'
    const parts = hash.split("/");
    const viewId = parts[1];
    const patientId = parts[2] || null;

    if (viewId) {
      await renderView(viewId, patientId);
    } else {
      // If hash is empty, default to search view
      await renderView("search");
    }
  }

  // Attach the core listener and run once on load
  window.addEventListener("hashchange", hashChangeHandler);

  // CRITICAL FIX: All DOM element acquisition and initial setup must be here.
  window.addEventListener("DOMContentLoaded", () => {
    // 1. Define references now that the DOM is fully loaded
    appViewRoot = document.getElementById("appViewRoot"); // The content container

    // 2. References exposed by search_manager.js/utils.js
    mainUiContainer = window.mainUiContainer;
    spotlightContainer = window.spotlightContainer;
    searchInput = window.searchInput;
    resultsContainer = window.resultsContainer;

    // 3. Final check and initialization
    if (!appViewRoot) {
      console.error(
        "Router Initialization Error: Could not find #appViewRoot. Aborting routing setup."
      );
      return;
    }

    // Only run the initial hash check AFTER all critical elements are found
    hashChangeHandler();
  });
})(); // End of IIFE
