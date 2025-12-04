// =======================================================
// patient_details.js (Interactions for Details View)
// =======================================================

(function () {
  window.confirmDelete = async function (patientId) {
    if (
      !confirm(
        "Are you sure you want to delete this patient record? This action cannot be undone."
      )
    ) {
      return;
    }

    try {
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

      if (response.ok && result.success) {
        window.notify.success(result.message || "Record deleted.");
        window.handleViewNavigation(null, "list");
      } else {
        throw new Error(result.message || "Failed to delete record.");
      }
    } catch (error) {
      console.error("Delete error:", error);
      window.notify.error(error.message);
    }
  };
})();
