document.addEventListener("DOMContentLoaded", () => {
  // Configuration
  const CONFIG = {
    baseWidth: 40,
    baseHeight: 40,
    magnification: 80,
    distance: 150,
  };

  // Data for the menu items
  // You can customize icons here. Lucide icon names required.
  const items = [
    { title: "Home", icon: "home", action: "/" },
    { title: "Users", icon: "users", action: "/users" },
    { title: "Dashboard", icon: "line-chart", action: "/dashboard" }, // 'chart-line' is 'line-chart' in newer lucide
    { title: "Activity", icon: "activity", action: "/activity" },
    { title: "Change Log", icon: "scroll-text", action: "/changelog" },
  ];

  const dock = document.getElementById("toolbar");

  if (!dock) return; // Guard clause if element doesn't exist

  // 1. Render the HTML structure
  items.forEach((item) => {
    const el = document.createElement("div");
    el.className = "dock-item";
    // You might want to wrap this in an <a> tag or add onclick handlers based on 'action'
    el.innerHTML = `
            <div class="dock-label">${item.title}</div>
            <i data-lucide="${item.icon}" class="dock-icon"></i>
        `;

    // Optional: Click handling
    el.addEventListener("click", () => {
      console.log(`Navigating to: ${item.action}`);
      // window.location.href = item.action;
    });

    dock.appendChild(el);
  });

  // Initialize icons now that DOM is populated
  if (window.lucide) {
    window.lucide.createIcons();
  }

  const dockItems = dock.querySelectorAll(".dock-item");

  // 2. Physics / Animation Logic
  dock.addEventListener("mousemove", (e) => {
    const mouseX = e.pageX;

    dockItems.forEach((item) => {
      const rect = item.getBoundingClientRect();
      const itemCenterX = rect.left + rect.width / 2;
      const distance = mouseX - itemCenterX;

      let width = CONFIG.baseWidth;

      if (distance > -CONFIG.distance && distance < CONFIG.distance) {
        // Linear interpolation for magnification
        const scaleFactor = 1 - Math.abs(distance) / CONFIG.distance;
        width =
          CONFIG.baseWidth +
          (CONFIG.magnification - CONFIG.baseWidth) * scaleFactor;
      }

      item.style.width = `${width}px`;
      item.style.height = `${width}px`;
    });
  });

  dock.addEventListener("mouseleave", () => {
    dockItems.forEach((item) => {
      item.style.width = `${CONFIG.baseWidth}px`;
      item.style.height = `${CONFIG.baseHeight}px`;
    });
  });
});
