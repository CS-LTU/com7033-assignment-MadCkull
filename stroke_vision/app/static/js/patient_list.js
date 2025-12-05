// =======================================================
// patient_list.js (Updated for Shell Architecture)
// =======================================================

let currentPage = 0;
let hasMore = true;
let isFetching = false;
let observer = null;

function createPatientRow(patient) {
  const riskMap = {
    Critical: "risk-critical",
    "Very High": "risk-critical",
    High: "risk-high",
    Moderate: "risk-moderate",
    Low: "risk-low",
  };
  const riskClass = riskMap[patient.risk_level] || "risk-low";

  const row = document.createElement("div");
  row.className = "patient-row grid-layout-7-col";

  row.onclick = (e) =>
    window.handleViewNavigation(e, "details", patient.patient_id);

  const chevronIcon = `<svg class="row-chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>`;

  row.innerHTML = `
        <span class="patient-id">${patient.patient_id}</span>
        <span class="patient-name">${patient.name}</span>
        <span>${patient.age}</span>
        <span>${patient.gender}</span>
        <span><span class="${riskClass} risk-level">${patient.risk_level}</span></span>
        <span style="color: #86868b; font-size: 12px;">${patient.added_on}</span>
        <span>${chevronIcon}</span>
    `;
  return row;
}

async function fetchAndRenderPatients(
  listContainer,
  initialLoader,
  loadMoreSpinner,
  scrollSentinel,
  emptyMessage
) {
  if (!hasMore || isFetching) return;

  isFetching = true;
  currentPage += 1;

  if (currentPage > 1 && loadMoreSpinner)
    loadMoreSpinner.classList.remove("hidden");

  try {
    const response = await fetch(`/patient/api/data?page=${currentPage}`, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });

    if (!response.ok) throw new Error("API Error");

    const data = await response.json();
    const patients = data.patients || [];
    hasMore = data.has_next;

    if (currentPage === 1) {
      if (initialLoader) initialLoader.remove();
      if (emptyMessage) emptyMessage.classList.add("hidden");
    }

    if (patients.length > 0 && listContainer) {
      patients.forEach((patient) => {
        listContainer.appendChild(createPatientRow(patient));
      });
    } else if (currentPage === 1 && emptyMessage) {
      emptyMessage.classList.remove("hidden");
    }
  } catch (error) {
    console.error(error);
  } finally {
    isFetching = false;
    if (loadMoreSpinner) loadMoreSpinner.classList.add("hidden");
    if (!hasMore && observer && scrollSentinel)
      observer.unobserve(scrollSentinel);
  }
}

window.loadPatientListAndAttachScroll = function (
  startPage = 1,
  attachScroll = true
) {
  const listContainer = document.getElementById("patientListRows");
  const initialLoader = document.getElementById("listInitialLoader");
  const loadMoreSpinner = document.getElementById("listLoadMoreSpinner");
  const scrollSentinel = document.getElementById("scrollSentinel");
  const emptyMessage = document.getElementById("listEmptyMessage");

  const scrollArea = listContainer
    ? listContainer.closest(".view-scroll-container")
    : null;

  currentPage = startPage - 1;
  hasMore = true;
  isFetching = false;

  if (observer) {
    observer.disconnect();
    observer = null;
  }

  if (attachScroll && scrollSentinel && scrollArea) {
    const intersectionCallback = (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting && hasMore && !isFetching) {
          fetchAndRenderPatients(
            listContainer,
            initialLoader,
            loadMoreSpinner,
            scrollSentinel,
            emptyMessage
          );
        }
      });
    };

    observer = new IntersectionObserver(intersectionCallback, {
      root: scrollArea,
      rootMargin: "200px",
      threshold: 0.1,
    });

    observer.observe(scrollSentinel);
  }

  fetchAndRenderPatients(
    listContainer,
    initialLoader,
    loadMoreSpinner,
    scrollSentinel,
    emptyMessage
  );
};
