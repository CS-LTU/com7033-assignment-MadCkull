// =======================================================
// patient_details.js (Interactions for Details View)
// =======================================================

(function () {
  /**
   * Handles the delete confirmation and API call
   */
  window.confirmDelete = async function (patientId) {
    // Simple confirmation for now - can be replaced with a custom modal later
    if (
      !confirm(
        "Are you sure you want to delete this patient record? This action cannot be undone."
      )
    ) {
      return;
    }

    try {
      // Retrieve CSRF token
      const csrfToken = document.querySelector(
        'meta[name="csrf-token"]'
      )?.content;

      const response = await fetch(`/patient/api/delete/${patientId}`, {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
          "X-Requested-With": "XMLHttpRequest",
        },
      });

      const result = await response.json();

      if (response.ok) {
        // Show success message (using utility function if available, else alert)
        if (window.showToast)
          window.showToast("Record deleted successfully", "success");

        // Navigate back to the list
        window.handleViewNavigation(null, "list");
      } else {
        throw new Error(result.error || "Failed to delete");
      }
    } catch (error) {
      console.error("Delete error:", error);
      if (window.showToast) window.showToast(error.message, "danger");
      else alert("Error: " + error.message);
    }
  };
})();
