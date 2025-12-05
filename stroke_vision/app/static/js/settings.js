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

    // NOTE: The Python route now supports updating both 'name' and 'email'.
    // Ensure you update your settings.html form to include the 'email' field with the name="email" attribute
    // if you want to support changing email via this form.

    try {
      // UI Loading State
      submitBtn.disabled = true;
      submitBtn.innerHTML =
        '<span class="material-icons spin">refresh</span> Saving...';

      // 2. Send Request using the CSRF-enabled fetchJson helper
      // *** ROUTE AND METHOD CHANGE: PATCH method used for update, new API path ***
      const result = await window.fetchJson("/settings/api/profile", {
        method: "PATCH", // Changed from POST to PATCH
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      });

      if (result.success) {
        window.showToast("Profile updated successfully!", "success");
        // Optional: Update the displayed name in the hero section if needed
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
      // Restore UI State
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
      // *** ROUTE AND METHOD CHANGE: PATCH method used for update, new API path ***
      const result = await window.fetchJson("/settings/api/change_password", {
        method: "PATCH", // Changed from POST to PATCH
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
      // Restore UI State
      submitBtn.disabled = false;
      submitBtn.innerHTML = originalText;
    }
  };
})();
