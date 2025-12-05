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
