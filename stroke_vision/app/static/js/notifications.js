// static/js/notifications.js

// Toast style presets — note: textColor & accentColor used, not heavy backgrounds.
export const TOAST_TYPES = {
  success: { textColor: "#1b7a3a", accentColor: "#28a745" },
  error:   { textColor: "#7a1b1b", accentColor: "#dc3545" },
  warning: { textColor: "#6a5200", accentColor: "#ffb000" },
  info:    { textColor: "#0f6678", accentColor: "#17a2b8" },
};

// Generic toast
export function showToast(message, type = "info") {
  const style = TOAST_TYPES[type] || TOAST_TYPES.info;

  // Build small HTML payload so we can style text and accent dot separately.
  // We keep escapeMarkup: false so markup works — if messages come from users, sanitize upstream.
  const html = `
    <div class="toast-content">
      <span class="toast-dot" style="background:${style.accentColor};"></span>
      <div class="toast-body" style="color:${style.textColor};">
        ${message}
      </div>
      <button class="toast-close" aria-label="close">&times;</button>
    </div>
  `;

  Toastify({
    node: null,                // let Toastify create the node
    text: html,
    duration: 40000,
    gravity: "bottom",         // bottom (not top)
    position: "right",         // right side
    close: true,
    escapeMarkup: false,
    className: "toastify-custom", // use our CSS for look + animation
    offset: { x: 20, y: 22 },  // padding from viewport edge
    stopOnFocus: true,         // pause timeout on hover/focus
    // No inline style for bg — CSS controls that for consistent look
  }).showToast();
}

// Flash loader (server → frontend)
export function showFlashNotifications() {
  const flashed = window.FLASH_NOTIFICATIONS || [];
  console.log("Flash notifications:", flashed);

  flashed.forEach((item) => {
    let category = "info";
    let message = "";

    if (Array.isArray(item) && item.length >= 2) {
      category = item[0];
      message = item[1];
    } else if (typeof item === "object" && item !== null) {
      category = item.category || "info";
      message = item.message || "";
    } else {
      message = String(item);
    }

    showToast(message, category);
  });

  window.FLASH_NOTIFICATIONS = [];
}

// Extra helpers
export const notify = {
  success: (msg) => showToast(msg, "success"),
  error:   (msg) => showToast(msg, "error"),
  info:    (msg) => showToast(msg, "info"),
  warn:    (msg) => showToast(msg, "warning"),
};

window.notify = notify;
window.showFlashNotifications = showFlashNotifications;
