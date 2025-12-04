// =======================================================
// utils.js (Global Helpers and Utilities)
// Note: All functions and constants are wrapped in IIFE
// to prevent global scope conflicts. Only necessary functions
// are exposed via the 'window' object.
// =======================================================

(function () {
  // --- General Utility Helpers ---

  /**
   * Helper for debounce (to prevent API spamming while typing)
   */
  function debounce(fn, wait) {
    let t = null;
    return function (...args) {
      clearTimeout(t);
      t = setTimeout(() => fn.apply(this, args), wait);
    };
  }

  /**
   * Helper for fetching JSON from Flask API (Used by search_manager and patient_list)
   */
  async function fetchJson(url, options = {}) {
    // <--- Add options parameter
    // Retrieve the CSRF token from the meta tag
    const csrfToken = document.querySelector(
      'meta[name="csrf-token"]'
    )?.content;

    // Define default and essential headers
    const defaultHeaders = {
      Accept: "application/json",
      // Include CSRF token for security
      "X-CSRFToken": csrfToken,
      // Send a custom header to Flask to request partial templates for form/details
      "X-Requested-With": "XMLHttpRequest",
    };

    // Merge provided headers with defaults, prioritizing provided ones
    options.headers = { ...defaultHeaders, ...options.headers };

    // Set credentials and spread the provided options
    const resp = await fetch(url, {
      credentials: "same-origin",
      ...options, // <--- This now includes the method and body passed from settings.js
    });

    if (!resp.ok) {
      if (resp.status === 404) {
        throw new Error("Resource not found.");
      }
      // Include the status code in the error message for better debugging
      throw new Error(`Fetch ${url} failed: ${resp.status}`);
    }
    return resp.json();
  }

  /**
   * Helper for displaying Toastify notifications (Assuming Toastify library is loaded)
   */
  function showToast(message, type = "info") {
    if (typeof Toastify !== "undefined") {
      const classes = {
        success: "bg-success",
        danger: "bg-danger",
        warning: "bg-warning",
        info: "bg-info",
      };
      Toastify({
        text: message,
        duration: 3000,
        close: true,
        gravity: "top", // `top` or `bottom`
        position: "right", // `left`, `center` or `right`
        stopOnFocus: true, // Prevents dismissal on focus
        style: {
          background: classes[type] || classes.info,
        },
      }).showToast();
    } else {
      console.warn(`Toastify not loaded: ${message}`);
    }
  }

  // --- UI Utility Helpers ---

  // NOTE: This function handles the placeholder text animation (used by search_manager and router)
  function changePlaceholder(text) {
    // FIX: We query the element INSIDE the function.
    // This ensures we find it even if utils.js loaded before the HTML body.
    const placeholder = document.getElementById("placeholder");

    if (!placeholder) return;
    if (placeholder.innerText === text && text !== "") return;

    // Case 1: Hiding the placeholder (user is typing)
    if (text === "") {
      placeholder.classList.add("hidden");
      placeholder.classList.remove("entering", "exiting");
      return;
    }

    // Case 2: Showing placeholder from hidden state
    if (placeholder.classList.contains("hidden")) {
      placeholder.classList.remove("hidden");
      placeholder.innerText = text;
      placeholder.classList.add("entering");
      placeholder.classList.remove("exiting");
      return;
    }

    // Case 3: Swapping text (Hover effects)
    placeholder.classList.add("exiting");
    placeholder.classList.remove("entering");

    setTimeout(() => {
      placeholder.innerText = text;
      placeholder.classList.remove("exiting");
      placeholder.classList.add("entering");
    }, 200);
  }

  // --- Data Formatting Helpers (Used by future detail/list components) ---

  function getRiskLevel(score) {
    if (score >= 13) return { label: "High Risk", class: "risk-high" };
    if (score >= 6) return { label: "Medium Risk", class: "risk-medium" };
    return { label: "Low Risk", class: "risk-low" };
  }

  function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  }

  // 🌟 Expose all necessary functions globally for access by other modules
  window.debounce = debounce;
  window.fetchJson = fetchJson;
  window.changePlaceholder = changePlaceholder;
  window.getRiskLevel = getRiskLevel;
  window.formatDate = formatDate;
  window.showToast = showToast;

  // Process flashed messages from the server on initial page load
  window.addEventListener("DOMContentLoaded", () => {
    if (window.FLASH_NOTIFICATIONS && window.FLASH_NOTIFICATIONS.length > 0) {
      window.FLASH_NOTIFICATIONS.forEach(([category, message]) => {
        showToast(message, category);
      });
      // Clear the array after showing them
      window.FLASH_NOTIFICATIONS = [];
    }
  });
})(); // End of IIFE
