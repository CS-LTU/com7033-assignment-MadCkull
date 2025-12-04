// =======================================================
// search_manager.js (Search Bar UI and Suggestions Logic)
// Dependencies: window.debounce, window.fetchJson, window.changePlaceholder (from utils.js)
//               window.handleViewNavigation (from app_router.js)
// =======================================================

// WRAP ENTIRE CODE IN IIFE TO PREVENT GLOBAL SCOPE CONFLICTS
(function () {
  // --- CONFIG ---
  const SUGGEST_URL = "/api/patients/suggestions";
  const SUGGEST_LIMIT = 30;
  const DEBOUNCE_MS = 300; // Time used by the global debounce helper

  // --- VALIDATION HELPERS ---
  const isLettersOnly = (s) => /^[A-Za-z ]+$/.test(s.trim());
  const isDigitsOnly = (s) => /^\d+$/.test(s.trim());
  const isMixed = (s) => /\d/.test(s) && /[A-Za-z]/.test(s);

  // --- UI References (Declare globally inside IIFE, define in DOMContentLoaded) ---
  let searchContainer;
  let spotlightContainer;
  let searchInput;
  let resultsContainer;
  let shortcuts;

  let sugLoading = false;

  // =======================================================
  // SUGGESTIONS/SEARCH IMPLEMENTATION (Functions are safe to define here)
  // =======================================================

  function createSuggestionElement(item, index) {
    const el = document.createElement("a");
    el.href = "#";
    el.className = "result-item";
    el.setAttribute("role", "option");
    el.style.animation = `fadeIn 0.3s ease forwards ${index * 0.05}s`;
    el.style.opacity = "0";

    el.innerHTML = `
            <div class="result-text">
                <div class="result-label">${item.name}</div>
                <div class="result-desc">ID: ${item.patient_id}</div>
            </div>
            <svg class="result-arrow" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="9 18 15 12 9 6"></polyline>
            </svg>
        `;

    el.addEventListener("click", (ev) => {
      ev.preventDefault();
      // Use the global router function defined in app_router.js
      if (window.handleViewNavigation) {
        window.handleViewNavigation(ev, "details", item.patient_id);
      }
      resultsContainer.innerHTML = "";
    });
    return el;
  }

  function showNoResults(msg = "No results found") {
    resultsContainer.innerHTML = "";
    const el = document.createElement("div");
    el.className = "result-item";
    el.style.cursor = "default";
    el.innerHTML = `<div class="result-text" style="text-align:center; color:#999; width:100%;">${msg}</div>`;
    resultsContainer.appendChild(el);
  }

  async function loadSuggestions(q, page = 1) {
    // Rely on globally defined fetchJson
    if (sugLoading || !window.fetchJson) return;
    resultsContainer.innerHTML = "";

    if (!q || q.trim().length === 0) return;

    // --- VALIDATION (Prevent unnecessary API calls) ---
    if (isMixed(q)) {
      showNoResults("No results for mixed input");
      return;
    }

    if (isDigitsOnly(q) && q.trim().length !== 9) {
      showNoResults("Type 9 digits for patient ID");
      return;
    } else if (!isLettersOnly(q) && !isDigitsOnly(q)) {
      showNoResults("Invalid characters");
      return;
    }
    // --------------------------------------------------

    sugLoading = true;
    try {
      const url = `${SUGGEST_URL}?q=${encodeURIComponent(
        q.trim()
      )}&page=${page}&limit=${SUGGEST_LIMIT}`;

      // Check for window.fetchJson before calling
      const data = await window.fetchJson(url);

      const items = data.items || [];
      resultsContainer.innerHTML = "";

      if (items.length === 0) {
        showNoResults();
      } else {
        items.forEach((it, index) =>
          resultsContainer.appendChild(createSuggestionElement(it, index))
        );
      }
    } catch (err) {
      console.error("Suggestions load error", err);
      showNoResults("Error loading suggestions");
    } finally {
      sugLoading = false;
    }
  }

  // Uses globally defined debounce helper
  const onInputDebounced = window.debounce((q) => {
    loadSuggestions(q, 1);
  }, DEBOUNCE_MS);

  // =======================================================
  // DOM READY INITIALIZATION (THE FIX)
  // =======================================================

  document.addEventListener("DOMContentLoaded", () => {
    // --- UI REFERENCES ---
    // Note: Now we can safely assume these elements exist.
    searchContainer = document.getElementById("searchContainer");
    spotlightContainer = document.getElementById("spotlightContainer");
    searchInput = document.getElementById("searchInput");
    resultsContainer = document.getElementById("resultsContainer");
    shortcuts = document.querySelectorAll(".shortcut-btn");

    // CRITICAL: Check if main elements were found before proceeding
    if (!spotlightContainer || !searchInput || !searchContainer) {
      console.error(
        "Search Manager failed to initialize: One or more critical UI elements (spotlightContainer, searchInput, etc.) were not found in the DOM."
      );
      return; // Stop execution if elements are missing
    }

    // 🌟 EXPOSE core elements globally for the router (app_router.js) to manipulate
    window.searchInput = searchInput;
    window.resultsContainer = resultsContainer;
    window.searchContainer = searchContainer;
    window.spotlightContainer = spotlightContainer;

    // =======================================================
    // SEARCH BAR UI INTERACTION LISTENERS (The Gooey Effect)
    // =======================================================

    spotlightContainer.addEventListener("mouseenter", () => {
      if (
        searchInput.value.length === 0 &&
        !searchContainer.classList.contains("view-active")
      ) {
        spotlightContainer.classList.add("hover-active");
      }
    });

    spotlightContainer.addEventListener("mouseleave", () => {
      if (
        searchInput.value.length === 0 &&
        !searchContainer.classList.contains("view-active")
      ) {
        spotlightContainer.classList.remove("hover-active");
        // Check for global helper before calling
        if (window.changePlaceholder) window.changePlaceholder("Search");
      }
    });

    shortcuts.forEach((btn) => {
      btn.addEventListener("mouseenter", () => {
        if (
          searchInput.value.length === 0 &&
          !searchContainer.classList.contains("view-active")
        )
          if (window.changePlaceholder)
            // Check for global helper before calling
            window.changePlaceholder(btn.getAttribute("data-label"));
      });
      btn.addEventListener("mouseleave", () => {
        if (
          searchInput.value.length === 0 &&
          !searchContainer.classList.contains("view-active")
        )
          if (window.changePlaceholder)
            // Check for global helper before calling
            window.changePlaceholder("Search");
      });
    });

    searchInput.addEventListener("input", (e) => {
      const val = e.target.value;

      if (val.length > 0) {
        spotlightContainer.classList.add("typing-active");
        spotlightContainer.classList.remove("hover-active");
        // Check for global helper before calling
        if (window.changePlaceholder) window.changePlaceholder("");
        onInputDebounced(val);
      } else {
        spotlightContainer.classList.remove("typing-active");
        if (
          spotlightContainer.matches(":hover") &&
          !searchContainer.classList.contains("view-active")
        ) {
          spotlightContainer.classList.add("hover-active");
        }
        // Check for global helper before calling
        if (window.changePlaceholder) window.changePlaceholder("Search");
        resultsContainer.innerHTML = "";
      }
    });
  });
})(); // End of IIFE
