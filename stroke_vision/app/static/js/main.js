// Global Utilities

/* -------------------------------------------------------
   CSRF Token Manager
------------------------------------------------------- */
class FormManager {
  static getCSRFToken() {
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    return metaTag ? metaTag.getAttribute("content") : null;
  }

  static initialize() {
    document.querySelectorAll("form:not([data-no-csrf])").forEach((form) => {
      if (!form.querySelector('input[name="csrf_token"]')) {
        const csrfToken = this.getCSRFToken();
        if (csrfToken) {
          const csrfInput = document.createElement("input");
          csrfInput.type = "hidden";
          csrfInput.name = "csrf_token";
          csrfInput.value = csrfToken;
          form.appendChild(csrfInput);
        }
      }
    });
  }
}

/* -------------------------------------------------------
   Fetch Helper (with CSRF)
------------------------------------------------------- */
function fetchWithCSRF(url, options = {}) {
  const defaultOptions = {
    credentials: "same-origin",
    headers: {
      "X-CSRFToken": FormManager.getCSRFToken(),
      ...options.headers,
    },
  };

  return fetch(url, { ...defaultOptions, ...options });
}

window.fetchWithCSRF = fetchWithCSRF;

/* -------------------------------------------------------
   Initialization
------------------------------------------------------- */
document.addEventListener("DOMContentLoaded", () => {
  console.log("Main.js initialized: CSRF setup complete");

  if (typeof FormManager !== "undefined") {
    FormManager.initialize();
  }
});
