// =======================================================
// patient_form.js (Handles Add/Edit Logic)
// =======================================================

(function () {
  window.handlePatientSubmit = async function (event) {
    event.preventDefault();

    const form = event.target;
    const submitBtn = document.getElementById("btnSave");
    const originalBtnContent = submitBtn.innerHTML;

    // 1. UI Loading State
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<div class="spinner-mac" style="width:14px; height:14px; border-width:2px; border-color: rgba(255,255,255,0.3); border-top-color: white; margin:0;"></div> Saving...`;

    // 2. Gather Data
    const formData = new FormData(form);

    try {
      // Note: We use the existing 'predict' route because your backend logic
      // handles both prediction AND saving in that one route.
      const response = await fetch("/patient/predict", {
        method: "POST",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
        },
        body: formData,
      });

      const data = await response.json();

      if (response.ok && data.success) {
        // Success!
        if (window.showToast)
          window.showToast("Record saved successfully!", "success");

        // Navigate to the Details view of the new/updated patient
        // We assume the backend returns 'patient_id'
        if (data.patient_id) {
          window.handleViewNavigation(null, "details", data.patient_id);
        } else {
          window.handleViewNavigation(null, "list");
        }
      } else {
        throw new Error(data.message || "Failed to save record.");
      }
    } catch (error) {
      console.error("Form Error:", error);
      if (window.showToast) window.showToast(error.message, "danger");
      else alert("Error: " + error.message);
    } finally {
      // Reset Button
      submitBtn.disabled = false;
      submitBtn.innerHTML = originalBtnContent;
    }
  };
})();
