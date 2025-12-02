// =======================================================
// API CONFIG & UTILITIES
// =======================================================
const SUGGEST_URL = "/api/patients/suggestions";
const DETAILS_URL_PREFIX = "/api/patients/"; // /api/patients/{id}
const SUGGEST_LIMIT = 30;
const DEBOUNCE_MS = 300;

const isLettersOnly = (s) => /^[A-Za-z ]+$/.test(s.trim());
const isDigitsOnly = (s) => /^\d+$/.test(s.trim());
const isMixed = (s) => /\d/.test(s) && /[A-Za-z]/.test(s);

// Helper for fetching JSON from Flask API
async function fetchJson(url) {
  const resp = await fetch(url, {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
  });
  if (!resp.ok) {
    if (resp.status === 404) {
      throw new Error("Resource not found.");
    }
    throw new Error(`Fetch ${url} failed: ${resp.status}`);
  }
  return resp.json();
}

// Helper for debounce (to prevent API spamming while typing)
function debounce(fn, wait) {
  let t = null;
  return function (...args) {
    clearTimeout(t);
    t = setTimeout(() => fn.apply(this, args), wait);
  };
}

// =======================================================
// FIREBASE SETUP (Original Code Kept)
// =======================================================
const appId = typeof __app_id !== "undefined" ? __app_id : "default-app-id";
const firebaseConfig =
  typeof __firebase_config !== "undefined"
    ? JSON.parse(__firebase_config)
    : null;
const initialAuthToken =
  typeof __initial_auth_token !== "undefined" ? __initial_auth_token : null;

let db = null;
let auth = null;
let userId = null;

// =======================================================
// STATE MANAGEMENT & UI LOGIC
// =======================================================

const mainUiContainer = document.getElementById("mainUiContainer");
const spotlightContainer = document.getElementById("spotlightContainer");
const searchInput = document.getElementById("searchInput");
const placeholder = document.getElementById("placeholder");
const resultsContainer = document.getElementById("resultsContainer");
const appViewRoot = document.getElementById("appViewRoot");
const shortcuts = document.querySelectorAll(".shortcut-btn");

// Suggestions/Search State
let sugLoading = false;

// --- Core Router Logic ---

function toggleViewActive(isActive) {
  if (isActive) {
    mainUiContainer.classList.add("view-active");
    spotlightContainer.classList.remove("typing-active", "hover-active");
    searchInput.value = "";
    resultsContainer.innerHTML = "";
  } else {
    mainUiContainer.classList.remove("view-active");
    changePlaceholder("Search");
  }
}

// Central View Renderer / Router (Updated for async fetching)
async function renderView(viewId, patientId = null) {
  console.log(`Rendering View: ${viewId}, ID: ${patientId}`);
  toggleViewActive(true); // Activate the component view

  let htmlContent = "";

  switch (viewId) {
    case "list":
      // Use PatientList module
      htmlContent = window.PatientList.getShell();
      appViewRoot.innerHTML = htmlContent;
      // Call the data loader via the hook
      if (window._searchManagerHandleView) {
        window._searchManagerHandleView("list");
      }
      break;
    case "add":
      htmlContent = AddPatientComponent();
      appViewRoot.innerHTML = htmlContent;
      break;
    case "details":
      // PatientDetailsComponent is async and handles its own rendering
      const detailHtml = await PatientDetailsComponent(patientId);
      appViewRoot.innerHTML = detailHtml;
      return;
    case "edit":
      // EditPatientComponent is async and handles its own rendering
      const editHtml = await EditPatientComponent(patientId);
      appViewRoot.innerHTML = editHtml;
      return;
    case "search":
      toggleViewActive(false); // Default state: Search
      return;
    default:
      htmlContent = `
        <div class="list-header">
          <h2>Error</h2>
          <button class="back-button" onclick="history.back()">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>
          </button>
        </div>
        <p style="padding: 20px;">View not found: ${viewId}</p>
      `;
      appViewRoot.innerHTML = htmlContent;
  }
}

// --- Utility Component Helpers ---

function getRiskLevel(score) {
  if (score >= 13) return { label: "High Risk", class: "risk-high" };
  if (score >= 6) return { label: "Medium Risk", class: "risk-medium" };
  return { label: "Low Risk", class: "risk-low" };
}

function formatDate(dateString) {
  const date = new Date(dateString);
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

// =======================================================
// ADD PATIENT COMPONENT
// =======================================================

function AddPatientComponent() {
  // Placeholder save function
  window.saveNewPatient = () => {
    const name = document.getElementById("name").value;
    if (!name) {
      console.error("Name required!");
      return;
    }
    console.log(`Saving new patient: ${name}`);
    // In a real app: POST to Flask API here.
    handleViewNavigation(null, "list"); // Go back to list after saving
  };

  return `
    <div class="form-header">
      <h2>Add New Patient Record</h2>
      <button class="back-button" onclick="handleViewNavigation(event, 'list')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="15 18 9 12 15 6"></polyline>
        </svg>
      </button>
    </div>
    <div class="form-grid">
      <div class="form-group">
        <label for="name">Full Name</label>
        <input type="text" id="name" placeholder="John Doe" required>
      </div>
      <div class="form-group">
        <label for="id">Patient ID</label>
        <input type="text" id="id" value="${
          Math.floor(Math.random() * 900000000) + 100000000
        }" disabled>
      </div>
      <div class="form-group">
        <label for="age">Age</label>
        <input type="number" id="age" min="1" max="120" required>
      </div>
      <div class="form-group">
        <label for="gender">Gender</label>
        <select id="gender" required>
          <option value="">Select Gender</option>
          <option value="Male">Male</option>
          <option value="Female">Female</option>
          <option value="Other">Other</option>
        </select>
      </div>
      <div class="form-group">
        <label for="risk">Stroke Risk (%)</label>
        <input type="number" id="risk" min="0" max="100" value="5">
      </div>
      <div class="form-group">
        <label for="date">Entry Date</label>
        <input type="date" id="date" value="${new Date()
          .toISOString()
          .substring(0, 10)}" disabled>
      </div>
      <div class="form-actions">
        <button class="form-btn secondary" onclick="handleViewNavigation(event, 'list')">Cancel</button>
        <button class="form-btn primary" onclick="saveNewPatient()">Save Patient</button>
      </div>
    </div>
  `;
}

// =======================================================
// PATIENT DETAILS COMPONENT
// =======================================================

async function PatientDetailsComponent(id) {
  // Render loading state immediately
  const loadingHtml = `
    <div class="form-header">
      <h2>Patient Details: Loading...</h2>
      <button class="back-button" onclick="handleViewNavigation(event, 'list')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>
      </button>
    </div>
    <p style="padding: 20px;">Fetching details for patient ID: ${id}...</p>
  `;
  appViewRoot.innerHTML = loadingHtml;

  let patient;
  try {
    patient = await fetchJson(`${DETAILS_URL_PREFIX}${id}`);
  } catch (error) {
    console.error("Error fetching patient details:", error);
    return `
      <div class="list-header">
        <h2>Error</h2>
        <button class="back-button" onclick="handleViewNavigation(event, 'list')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>
        </button>
      </div>
      <p style="padding: 20px;">Patient with ID ${id} not found or API error.</p>
    `;
  }

  const risk = getRiskLevel(patient.stroke_risk);
  const addedDate = formatDate(patient.record_entry_date);

  return `
    <div class="form-header">
      <h2>Patient Details: ${patient.name}</h2>
      <div>
        <button class="form-btn secondary" onclick="handleViewNavigation(event, 'edit', '${id}')">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; margin-right: 5px;"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/></svg>
          Edit
        </button>
        <button class="back-button" onclick="handleViewNavigation(event, 'list')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="15 18 9 12 15 6"></polyline>
          </svg>
        </button>
      </div>
    </div>
    <div class="form-grid" style="grid-template-columns: 1fr;">
      <div class="detail-group" style="padding: 0 16px;">
        <p><strong>ID:</strong> ${patient.patient_id}</p>
        <p><strong>Age:</strong> ${patient.age}</p>
        <p><strong>Gender:</strong> ${patient.gender}</p>
        <p><strong>Risk Status:</strong> <span class="risk-badge ${
          risk.class
        }">${risk.label} (${Math.round(patient.stroke_risk)}%)</span></p>
        <p><strong>Record Added:</strong> ${addedDate}</p>
        <p><strong>Ever Married:</strong> ${patient.ever_married}</p>
        <p><strong>Work Type:</strong> ${patient.work_type}</p>
        <p><strong>Residence:</strong> ${patient.residence_type}</p>
        <p><strong>Heart Disease:</strong> ${patient.heart_disease}</p>
        <p><strong>Hypertension:</strong> ${patient.hypertension}</p>
        <p><strong>Glucose Level:</strong> ${patient.avg_glucose_level}</p>
        <p><strong>BMI:</strong> ${patient.bmi}</p>
        <p><strong>Smoking Status:</strong> ${patient.smoking_status}</p>
        <br>
        <h3>Metadata</h3>
        <p><strong>Created By:</strong> ${patient.created_by}</p>
        <p><strong>Updated At:</strong> ${
          patient.updated_at ? formatDate(patient.updated_at) : "N/A"
        }</p>
      </div>
    </div>
  `;
}

// =======================================================
// EDIT PATIENT COMPONENT
// =======================================================

async function EditPatientComponent(id) {
  // Initial render of a loading shell
  const loadingHtml = `
    <div class="form-header">
      <h2>Edit Patient: Loading...</h2>
      <button class="back-button" onclick="handleViewNavigation(event, 'details', '${id}')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>
      </button>
    </div>
    <p style="padding: 20px;">Fetching patient data for editing...</p>
  `;
  appViewRoot.innerHTML = loadingHtml;

  let patient;
  try {
    patient = await fetchJson(`${DETAILS_URL_PREFIX}${id}`);
  } catch (error) {
    console.error("Error fetching patient for editing:", error);
    return PatientDetailsComponent(id); // Fallback to details error
  }

  // Placeholder save function
  window.saveEditedPatient = () => {
    // In a real app: PUT/PATCH to Flask API here.
    console.log(`Saving edits for patient ${id}: Placeholder save executed.`);
    handleViewNavigation(null, "details", id); // Go back to details after saving
  };

  return `
    <div class="form-header">
      <h2>Edit Patient: ${patient.name}</h2>
      <button class="back-button" onclick="handleViewNavigation(event, 'details', '${id}')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="15 18 9 12 15 6"></polyline>
        </svg>
      </button>
    </div>
    <div class="form-grid">
      <div class="form-group">
        <label for="edit-name">Full Name</label>
        <input type="text" id="edit-name" value="${patient.name}" required>
      </div>
      <div class="form-group">
        <label for="edit-id">Patient ID</label>
        <input type="text" id="edit-id" value="${patient.patient_id}" disabled>
      </div>
      <div class="form-group">
        <label for="edit-age">Age</label>
        <input type="number" id="edit-age" min="1" max="120" value="${
          patient.age
        }" required>
      </div>
      <div class="form-group">
        <label for="edit-gender">Gender</label>
        <select id="edit-gender" required>
          <option value="Male" ${
            patient.gender === "Male" ? "selected" : ""
          }>Male</option>
          <option value="Female" ${
            patient.gender === "Female" ? "selected" : ""
          }>Female</option>
          <option value="Other" ${
            patient.gender === "Other" ? "selected" : ""
          }>Other</option>
        </select>
      </div>
      <div class="form-group">
        <label for="edit-risk">Stroke Risk (%)</label>
        <input type="number" id="edit-risk" min="0" max="100" value="${Math.round(
          patient.stroke_risk
        )}">
      </div>
      <div class="form-group">
        <label for="edit-date">Entry Date</label>
        <input type="date" id="edit-date" value="${new Date(
          patient.record_entry_date
        )
          .toISOString()
          .substring(0, 10)}" disabled>
      </div>
      <div class="form-actions">
        <button class="form-btn secondary" onclick="handleViewNavigation(event, 'details', '${id}')">Cancel</button>
        <button class="form-btn primary" onclick="saveEditedPatient()">Save Changes</button>
      </div>
    </div>
  `;
}

// =======================================================
// SUGGESTIONS/SEARCH IMPLEMENTATION (Uses API)
// =======================================================

function createSuggestionElement(item, index) {
  // item: { patient_id, name }
  const el = document.createElement("a");
  el.href = "#";
  el.className = "result-item";
  el.setAttribute("role", "option");
  el.style.animation = `fadeIn 0.3s ease forwards ${index * 0.05}s`;
  el.style.opacity = "0";

  el.innerHTML = `
    <div class="result-text">
      <div class="result-label">${item.name}</div>
      <div class="result-desc">ID: ${item.patient_id}</div>
    </div>
    <svg class="result-arrow" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <polyline points="9 18 15 12 9 6"></polyline>
    </svg>
  `;

  el.addEventListener("click", (ev) => {
    ev.preventDefault();
    // reuse your hash-based navigation
    handleViewNavigation(ev, "details", item.patient_id);
    // clear dropdown
    resultsContainer.innerHTML = "";
  });

  return el;
}

function showNoResults(msg = "No results found") {
  resultsContainer.innerHTML = "";
  const el = document.createElement("div");
  el.className = "result-item";
  el.style.cursor = "default";
  el.innerHTML = `<div class="result-text" style="text-align:center; color:#999; width:100%;">${msg}</div>`;
  resultsContainer.appendChild(el);
}

async function loadSuggestions(q, page = 1) {
  if (sugLoading) return;
  resultsContainer.innerHTML = ""; // Clear previous results while loading

  if (!q || q.trim().length === 0) {
    return;
  }

  // Mixed input => show no results (per backend rule)
  if (isMixed(q)) {
    showNoResults("No results for mixed input");
    return;
  }

  // Digits only: require exactly 9 digits to trigger (per backend rule)
  if (isDigitsOnly(q)) {
    if (q.trim().length !== 9) {
      showNoResults("Type 9 digits for patient ID");
      return;
    }
  } else {
    // letters-only: require at least 1 char and be letters-only
    if (!isLettersOnly(q)) {
      showNoResults("Invalid characters");
      return;
    }
  }

  sugLoading = true;
  try {
    const url = `${SUGGEST_URL}?q=${encodeURIComponent(
      q.trim()
    )}&page=${page}&limit=${SUGGEST_LIMIT}`;
    const data = await fetchJson(url);
    const items = data.items || [];
    resultsContainer.innerHTML = "";

    if (items.length === 0) {
      showNoResults();
    } else {
      items.forEach((it, index) =>
        resultsContainer.appendChild(createSuggestionElement(it, index))
      );
    }
  } catch (err) {
    console.error("Suggestions load error", err);
    showNoResults("Error loading suggestions");
  } finally {
    sugLoading = false;
  }
}

const onInputDebounced = debounce((q) => {
  // always start from page 1 on new query
  loadSuggestions(q, 1);
}, DEBOUNCE_MS);

// --- Search Bar Logic (UI Animations) ---

function changePlaceholder(text) {
  if (placeholder.innerText === text && text !== "") return;

  if (text === "") {
    placeholder.classList.add("hidden");
    placeholder.classList.remove("entering", "exiting");
    return;
  }

  if (placeholder.classList.contains("hidden")) {
    placeholder.classList.remove("hidden");
    placeholder.innerText = text;
    placeholder.classList.add("entering");
    placeholder.classList.remove("exiting");
    return;
  }

  placeholder.classList.add("exiting");
  placeholder.classList.remove("entering");

  setTimeout(() => {
    placeholder.innerText = text;
    placeholder.classList.remove("exiting");
    placeholder.classList.add("entering");
  }, 200);
}

spotlightContainer.addEventListener("mouseenter", () => {
  if (
    searchInput.value.length === 0 &&
    !mainUiContainer.classList.contains("view-active")
  ) {
    spotlightContainer.classList.add("hover-active");
  }
});

spotlightContainer.addEventListener("mouseleave", () => {
  if (
    searchInput.value.length === 0 &&
    !mainUiContainer.classList.contains("view-active")
  ) {
    spotlightContainer.classList.remove("hover-active");
    changePlaceholder("Search");
  }
});

shortcuts.forEach((btn) => {
  btn.addEventListener("mouseenter", () => {
    if (
      searchInput.value.length === 0 &&
      !mainUiContainer.classList.contains("view-active")
    )
      changePlaceholder(btn.getAttribute("data-label"));
  });
  btn.addEventListener("mouseleave", () => {
    if (
      searchInput.value.length === 0 &&
      !mainUiContainer.classList.contains("view-active")
    )
      changePlaceholder("Search");
  });
});

// Primary Input Handler (Calls the debounced API fetch)
searchInput.addEventListener("input", (e) => {
  const val = e.target.value;

  if (val.length > 0) {
    spotlightContainer.classList.add("typing-active");
    spotlightContainer.classList.remove("hover-active");
    changePlaceholder("");
    // NEW: Call the debounced API fetcher
    onInputDebounced(val);
  } else {
    spotlightContainer.classList.remove("typing-active");
    if (
      spotlightContainer.matches(":hover") &&
      !mainUiContainer.classList.contains("view-active")
    ) {
      spotlightContainer.classList.add("hover-active");
    }
    changePlaceholder("Search");
    resultsContainer.innerHTML = "";
  }
});

// =======================================================
// NAVIGATION AND INITIALIZATION
// =======================================================

function handleViewNavigation(event, viewId, patientId = null) {
  if (event) event.preventDefault();

  let newHash = viewId;
  if (patientId) {
    newHash += `/${patientId}`;
  }

  // Update URL hash and trigger the hashchange listener
  window.location.hash = `#/${newHash}`;
}

function handleShortcutClick(event, viewId) {
  handleViewNavigation(event, viewId);
}

// Hook for patient list module to load data
window._searchManagerHandleView = function (viewId) {
  if (viewId === "list") {
    // Use PatientList module to load data
    window.PatientList.load(1, false);
  }
};

// Main Router Listener: fires on hash change (browser back/forward button)
async function hashChangeHandler() {
  const hash = window.location.hash.substring(1); // Remove '#'
  const parts = hash.split("/");
  const viewId = parts[1];
  const patientId = parts[2] || null;

  if (viewId && viewId !== "search") {
    await renderView(viewId, patientId);
  } else {
    await renderView("search");
  }
}

// Initialize router on page load and hash changes
window.addEventListener("hashchange", hashChangeHandler);
window.addEventListener("DOMContentLoaded", () => {
  hashChangeHandler(); // Initialize with current hash
});
