// static/js/notifications.js

// Toast style presets
export const TOAST_TYPES = {
  success: { background: "linear-gradient(to right, #28a745, #218838)" },
  error: { background: "linear-gradient(to right, #dc3545, #c82333)" },
  warning: {
    background: "linear-gradient(to right, #ffc107, #e0a800)",
    color: "#000",
  },
  info: { background: "linear-gradient(to right, #17a2b8, #138496)" },
};

// Generic toast
export function showToast(message, type = "info") {
  const style = TOAST_TYPES[type] || TOAST_TYPES.info;

  Toastify({
    text: message,
    duration: 4000,
    gravity: "top",
    position: "right",
    close: true,
    escapeMarkup: false,
    style,
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
  error: (msg) => showToast(msg, "error"),
  info: (msg) => showToast(msg, "info"),
  warn: (msg) => showToast(msg, "warning"),
};

window.notify = notify;
window.showFlashNotifications = showFlashNotifications;
