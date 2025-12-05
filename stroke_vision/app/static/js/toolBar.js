document.addEventListener("DOMContentLoaded", () => {
  const CONFIG = {
    baseWidth: 40,
    baseHeight: 40,
    magnification: 80,
    distance: 150,
  };

  const items = [
    { title: "Home", icon: "home", action: "search" },
    { title: "Users", icon: "users", action: "users" },
    { title: "Dashboard", icon: "line-chart", action: "dashboard" },
    { title: "Activity", icon: "activity", action: "activity" },
    { title: "Change Log", icon: "scroll-text", action: "changelog" },
  ];

  const dock = document.getElementById("toolbar");

  if (!dock) return;

  items.forEach((item) => {
    const el = document.createElement("div");
    el.className = "dock-item";

    el.setAttribute("data-view-id", item.action);

    el.innerHTML = `
      <div class="dock-label">${item.title}</div>
      <i data-lucide="${item.icon}" class="dock-icon"></i>
    `;

    el.addEventListener("click", (e) => {
      window.handleViewNavigation(e, item.action);
    });

    dock.appendChild(el);
  });

  if (window.lucide) {
    window.lucide.createIcons();
  }

  const dockItems = dock.querySelectorAll(".dock-item");

  dock.addEventListener("mousemove", (e) => {
    const mouseX = e.pageX;

    dockItems.forEach((item) => {
      const rect = item.getBoundingClientRect();
      const itemCenterX = rect.left + rect.width / 2;
      const distance = mouseX - itemCenterX;

      let width = CONFIG.baseWidth;

      if (distance > -CONFIG.distance && distance < CONFIG.distance) {
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
