// settings.js

(function () {
  // --- Profile Update Handler ---
  window.handleProfileUpdate = async function (event) {
    event.preventDefault();
    const form = event.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;

    // 1. Gather Data
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    try {
      // UI Loading State
      submitBtn.disabled = true;
      submitBtn.innerHTML =
        '<span class="material-icons spin">refresh</span> Saving...';

      const result = await window.fetchJson("/settings/api/profile", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      });

      if (result.success) {
        window.notify.success("Profile updated successfully!");
        document.querySelector(".hero-name").textContent = data.name;
      } else {
        window.notify.error(result.message);
      }
    } catch (error) {

      console.error("Profile update failed:", error);
      window.notify.error(error.message);
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = originalText;
    }
  };

  window.handlePasswordChange = async function (event) {
    event.preventDefault();
    const form = event.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;

    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    if (data.new_password !== data.confirm_password) {
      window.notify.warn("New passwords do not match.");
      return;
    }

    try {
      submitBtn.disabled = true;
      submitBtn.innerHTML =
        '<span class="material-icons spin">refresh</span> Updating...';

      // 2. Send Request using the CSRF-enabled fetchJson helper
      const result = await window.fetchJson("/settings/api/change_password", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      });

      if (result.success) {
        window.notify.success("Password changed successfully.");
        form.reset();
      } else {
        window.notify.error("Failed, Please Check your details.");
      }
    } catch (error) {

      console.error("Password change failed:", error);
      window.notify.error("Failed, Please Check your details.");
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = originalText;
    }
  };
})();
