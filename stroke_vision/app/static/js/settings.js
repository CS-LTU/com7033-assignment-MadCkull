/* settings.js
 * Logic for handling settings updates asynchronously.
 */

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

      // 2. Send Request using the CSRF-enabled fetchJson helper
      // We must pass the URL and POST data (JSON body) to fetchJson.
      // Since fetchJson returns the JSON response, we don't need .json().
      const result = await window.fetchJson("/settings/update_profile", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      });

      // Note: If fetchJson throws on a non-200 status, the catch block handles it.
      // Otherwise, we assume success based on the result structure.

      if (result.success) {
        window.showToast("Profile updated successfully!", "success"); // Use Toast for better UX
        document.querySelector(".hero-name").textContent = data.name;
      } else {
        window.showToast("Error: " + result.message, "danger");
      }
    } catch (error) {
      console.error("Profile update failed:", error);
      window.showToast(
        "An unexpected error occurred: " + error.message,
        "danger"
      );
    } finally {
      // Reset UI
      submitBtn.disabled = false;
      submitBtn.innerHTML = originalText;
    }
  };

  // --- Password Change Handler ---
  window.handlePasswordChange = async function (event) {
    event.preventDefault();
    const form = event.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;

    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    // Basic Client-side Validation
    if (data.new_password !== data.confirm_password) {
      window.showToast("New passwords do not match.", "warning");
      return;
    }

    try {
      submitBtn.disabled = true;
      submitBtn.innerHTML =
        '<span class="material-icons spin">refresh</span> Updating...';

      // 2. Send Request using the CSRF-enabled fetchJson helper
      const result = await window.fetchJson("/settings/change_password", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      });

      if (result.success) {
        window.showToast("Password changed successfully.", "success");
        form.reset(); // Clear the sensitive fields
      } else {
        window.showToast("Error: " + result.message, "danger");
      }
    } catch (error) {
      console.error("Password change failed:", error);
      window.showToast(
        "An unexpected error occurred: " + error.message,
        "danger"
      );
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = originalText;
    }
  };
})();
