// =======================================================
// utils.js (Global Helpers and Utilities)
// Note: All functions and constants are wrapped in IIFE
// to prevent global scope conflicts. Only necessary functions
// are exposed via the 'window' object.
// =======================================================

(function () {
  // --- General Utility Helpers ---
  function debounce(fn, wait) {
    let t = null;
    return function (...args) {
      clearTimeout(t);
      t = setTimeout(() => fn.apply(this, args), wait);
    };
  }

  async function fetchJson(url, options = {}) {
    const csrfToken = document.querySelector(
      'meta[name="csrf-token"]'
    )?.content;

    const defaultHeaders = {
      Accept: "application/json",
      "X-CSRFToken": csrfToken,
      "X-Requested-With": "XMLHttpRequest",
    };

    options.headers = { ...defaultHeaders, ...options.headers };

    const resp = await fetch(url, {
      credentials: "same-origin",
      ...options,
    });

    if (!resp.ok) {
      if (resp.status === 404) {
        throw new Error("Resource not found.");
      }
      throw new Error(`Fetch ${url} failed: ${resp.status}`);
    }
    return resp.json();
  }

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
        gravity: "bottom",         // bottom (not top)
        position: "right",         // right side
        stopOnFocus: true, // Prevents dismissal on focus
        style: {
          background: classes[type] || classes.info,
        },
      }).showToast();
    } else {
      console.warn(`Toastify not loaded: ${message}`);
    }
  }

// This function handles the placeholder text animation (used by search_manager and router)
  function changePlaceholder(text) {
    const placeholder = document.getElementById("placeholder");

    if (!placeholder) return;
    if (placeholder.innerText === text && text !== "") return;

    if (text === "") {
      placeholder.classList.add("hidden");
      placeholder.classList.remove("entering", "exiting");
      return;
    }

    if (placeholder.classList.contains("hidden")) {
      placeholder.classList.remove("hidden");
      placeholder.innerText = text;
      placeholder.classList.add("entering");
      placeholder.classList.remove("exiting");
      return;
    }

    placeholder.classList.add("exiting");
    placeholder.classList.remove("entering");

    setTimeout(() => {
      placeholder.innerText = text;
      placeholder.classList.remove("exiting");
      placeholder.classList.add("entering");
    }, 200);
  }

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
      year: "numeric",
    });
  }

  window.debounce = debounce;
  window.fetchJson = fetchJson;
  window.changePlaceholder = changePlaceholder;
  window.getRiskLevel = getRiskLevel;
  window.formatDate = formatDate;
  window.showToast = showToast;

  window.addEventListener("DOMContentLoaded", () => {
    if (window.FLASH_NOTIFICATIONS && window.FLASH_NOTIFICATIONS.length > 0) {
      window.FLASH_NOTIFICATIONS.forEach(([category, message]) => {
        showToast(message, category);
      });
      window.FLASH_NOTIFICATIONS = [];
    }
  });
})(); // End of IIFE
