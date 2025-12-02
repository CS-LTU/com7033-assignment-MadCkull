// =======================================================
// PATIENT LIST MODULE
// =======================================================

// List State
let listPage = 1;
let listHasMore = false;
let listLoading = false;
const listContainerId = "patient-list-data-container";

// Constants (should match search_manager.js)
const LIST_URL = "/api/patients/list";
const LIST_LIMIT = 28;

/**
 * Generate HTML for a single patient row
 */
function patientListRowHtml(p) {
  // p: { patient_id, name, age, gender, stroke_risk, record_entry_date }
  const added = p.record_entry_date
    ? new Date(p.record_entry_date).toLocaleDateString()
    : "";
  // ensure risk is a number for the helper
  const risk = Math.round(Number(p.stroke_risk) || 0);
  const riskStatus = getRiskLevel(risk);

  return `
    <a href="#/details/${
      p.patient_id
    }" class="patient-row" onclick="handleViewNavigation(event, 'details', '${
    p.patient_id
  }')">
      <span class="patient-id">${p.patient_id}</span>
      <span class="patient-name">${p.name}</span>
      <span class="patient-age">${p.age || ""}</span>
      <span class="patient-gender">${p.gender || ""}</span>
      <span class="risk-cell"><span class="risk-badge ${
        riskStatus.class
      }">${risk}%</span></span>
      <span class="patient-date">${added}</span>
      <span class="details-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg></span>
    </a>
  `;
}

/**
 * Get the HTML shell for patient list view
 */
function getPatientListShell() {
  const template = document.getElementById("patient-list-template");
  if (template) {
    return template.innerHTML;
  }

  // Fallback if template not found
  return `
    <div class="list-header">
      <h2>Patient Records Overview</h2>
      <button class="back-button" onclick="handleViewNavigation(event, 'search')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>
      </button>
    </div>
    <div class="list-column-headers">
      <span>ID</span><span>Name</span><span>Age</span><span>Gender</span><span>Risk Level</span><span>Added On</span><span></span>
    </div>
    <div id="${listContainerId}">
      <p style="text-align:center;padding:12px;color:#999;">Loading patients...</p>
    </div>
    <div id="list-loading-indicator" style="text-align:center;padding:12px; color:#666; display: none;">Loading more...</div>
  `;
}

/**
 * Attach infinite scroll handler to list container
 */
function attachListScrollHandler() {
  const container = document.getElementById(listContainerId);
  if (!container) return;

  function onScroll() {
    if (!listHasMore || listLoading) return;
    // when scrolled to near the bottom of the container, load next page
    if (
      container.scrollTop + container.clientHeight >=
      container.scrollHeight - 300
    ) {
      // show tiny loader
      const li = document.getElementById("list-loading-indicator");
      if (li) li.style.display = "block";
      loadPatientList(listPage + 1, true).then(() => {
        const li2 = document.getElementById("list-loading-indicator");
        if (li2) li2.style.display = "none";
      });
    }
  }

  // make sure we don't attach duplicate listeners
  container.removeEventListener("scroll", onScroll);
  container.addEventListener("scroll", onScroll);
}

/**
 * Load patient list from API
 * @param {number} page - Page number to load
 * @param {boolean} append - Whether to append to existing list or replace
 */
async function loadPatientList(page = 1, append = false) {
  if (listLoading) return;
  listLoading = true;

  // Clear previous content if it's a fresh load
  if (!append) {
    const container = document.getElementById(listContainerId);
    if (container)
      container.innerHTML = `<p style="text-align:center;padding:12px;color:#999;">Loading patients...</p>`;
  }

  try {
    const url = `${LIST_URL}?page=${page}&limit=${LIST_LIMIT}`;
    const data = await fetchJson(url);
    const items = data.items || [];
    listHasMore = Boolean(data.has_more);
    listPage = page;

    const container = document.getElementById(listContainerId);

    if (!append) {
      // Render fresh list
      const listHtml = items.map((p) => patientListRowHtml(p)).join("");

      if (container) container.innerHTML = listHtml;

      if (items.length === 0 && container) {
        container.innerHTML = `<p style="text-align:center;padding:20px;color:#999;">No patients found.</p>`;
      }
      attachListScrollHandler();
    } else {
      // append rows to existing container
      if (container) {
        items.forEach((p) => {
          const div = document.createElement("div");
          div.innerHTML = patientListRowHtml(p);
          // append child nodes
          while (div.firstChild) container.appendChild(div.firstChild);
        });
      }
    }
  } catch (err) {
    console.error("Patient list load error", err);
    if (!append) {
      const appViewRoot = document.getElementById("appViewRoot");
      if (appViewRoot) {
        appViewRoot.innerHTML = `<p style="padding:20px;color:#900">Error loading list.</p>`;
      }
    }
  } finally {
    listLoading = false;
  }
}

/**
 * Reset list state (useful when navigating away and back)
 */
function resetListState() {
  listPage = 1;
  listHasMore = false;
  listLoading = false;
}

// Export functions for use in search_manager.js
window.PatientList = {
  getShell: getPatientListShell,
  load: loadPatientList,
  reset: resetListState,
};
