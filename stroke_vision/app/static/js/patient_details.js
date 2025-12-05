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

      if (response.ok) {
        if (window.showToast)
          window.showToast("Record deleted successfully", "success");

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
