document.addEventListener("DOMContentLoaded", () => {
  const navBarComponent = document.getElementById("navBarComponent");

  // Safety check in case the component isn't on the current page
  if (!navBarComponent) return;

  const buttons = navBarComponent.querySelectorAll(".tab-btn");

  buttons.forEach((btn) => {
    btn.addEventListener("mouseenter", () => {
      buttons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
    });
  });

  navBarComponent.addEventListener("mouseleave", () => {
    buttons.forEach((b) => b.classList.remove("active"));
  });
});

window.ToggleTheme = function () {
  const themeLink = document.getElementById("theme-stylesheet");
  if (!themeLink) return;

  const currentHref = themeLink.href;
  const isDark = currentHref.includes("color_scheme-Dark.css");

  if (isDark) {
    localStorage.setItem("theme", "Light");
  } else {
    localStorage.setItem("theme", "Dark");
  }

  // Refresh to apply changes cleanly as requested
  window.location.reload();
};
