// =======================================================
// patient_form.js (Handles Add/Edit Logic)
// =======================================================

(function () {
  window.handlePatientSubmit = async function (event) {
    event.preventDefault();

    const form = event.target;
    const submitBtn = document.getElementById("btnSave");
    const originalBtnContent = submitBtn.innerHTML;

    submitBtn.disabled = true;
    submitBtn.innerHTML = `<div class="spinner-mac" style="width:14px; height:14px; border-width:2px; border-color: rgba(255,255,255,0.3); border-top-color: white; margin:0;"></div> Saving...`;

    const formData = new FormData(form);

    try {
      const response = await fetch("/patient/predict", {
        method: "POST",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
        },
        body: formData,
      });

      const data = await response.json();

      if (response.ok && data.success) {
        window.notify.success(data.message || "Record saved successfully!");

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
      window.notify.error(error.message);
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = originalBtnContent;
    }
  };
})();
