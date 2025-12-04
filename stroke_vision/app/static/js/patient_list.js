// =======================================================
// patient_list.js (List Data Fetching and Rendering)
// Dependencies: app_router.js (calls loadPatientListAndAttachScroll)
// =======================================================

let currentPage = 0;
let hasMore = true;
let isFetching = false;
let observer = null;

// Removed global DOM references as they will be null when the script first runs.
// The references are now created inside loadPatientListAndAttachScroll.

/**
 * Creates the HTML markup for a single patient row.
 */
function createPatientRow(patient) {
  // Determine the color class for the risk level
  let riskClass = "";
  if (patient.risk_level === "Critical" || patient.risk_level === "Very High") {
    riskClass = "risk-critical";
  } else if (patient.risk_level === "High") {
    riskClass = "risk-high";
  } else if (patient.risk_level === "Moderate") {
    riskClass = "risk-moderate";
  } else {
    riskClass = "risk-low";
  }

  // Use the global handleViewNavigation to go to the details view
  const row = document.createElement("div");
  row.className = "patient-row";
  row.setAttribute("data-patient-id", patient.patient_id);
  row.innerHTML = `
        <span>${patient.patient_id}</span>
        <span class="patient-name">${patient.name}</span>
        <span>${patient.age}</span>
        <span>${patient.gender}</span>
        <span class="${riskClass} risk-level">${patient.risk_level}</span>
        <span>${patient.added_on}</span>
        <span class="action-cell">
            <button class="details-button" onclick="window.handleViewNavigation(event, 'details', '${patient.patient_id}')">
                Details
            </button>
        </span>
    `;
  return row;
}

/**
 * Core function to fetch the next page of patient data.
 * Now accepts DOM elements as arguments.
 */
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

  // Ensure all elements exist before trying to manipulate them
  const hasLoaders = initialLoader && loadMoreSpinner;
  const hasContainers = listContainer && emptyMessage;

  // Show spinner for subsequent loads, hide the initial loader
  if (currentPage > 1) {
    if (hasLoaders) loadMoreSpinner.classList.remove("hidden");
  } else {
    if (hasLoaders) initialLoader.classList.remove("hidden");
  }

  try {
    // FIX: Added the 'X-Requested-With: XMLHttpRequest' header to satisfy the Flask server's is_ajax_request() check.
    const response = await fetch(`/patient/api/data?page=${currentPage}`, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });

    if (!response.ok) {
      throw new Error("Failed to fetch patient list data.");
    }

    const data = await response.json();
    const patients = data.patients || [];
    hasMore = data.has_next;

    // 1. Handle Initial Load UI
    if (currentPage === 1 && hasContainers) {
      // Remove initial loader/empty states before injecting content
      if (initialLoader) initialLoader.remove();
      if (emptyMessage) emptyMessage.classList.add("hidden");
    }

    // 2. Render Rows
    if (listContainer) {
      if (patients.length > 0) {
        patients.forEach((patient) => {
          listContainer.appendChild(createPatientRow(patient));
        });
      } else if (currentPage === 1) {
        // Handle truly empty list on first load
        if (emptyMessage) emptyMessage.classList.remove("hidden");
      }
    }
  } catch (error) {
    console.error("List load error:", error);
    // Show error message on the screen
    if (listContainer) {
      listContainer.innerHTML += `<div class="list-placeholder error-message" style="color: #ef4444; padding: 20px;">
                                         Error: ${error.message}
                                     </div>`;
    }
    hasMore = false; // Stop trying to load if there's an error
  } finally {
    isFetching = false;
    // Hide the "Load More" spinner
    if (loadMoreSpinner) loadMoreSpinner.classList.add("hidden");

    // Disconnect observer if there are no more pages
    if (!hasMore && observer && scrollSentinel) {
      observer.unobserve(scrollSentinel);
      console.log("Observer disconnected: No more patients to load.");
    }
  }
}

/**
 * Initializes the list view, resets state, and sets up the Intersection Observer.
 * This is called by app_router.js after the fragment is injected.
 */
window.loadPatientListAndAttachScroll = function (
  startPage = 1,
  attachScroll = true
) {
  // Define DOM references here, AFTER the fragment is loaded into the DOM
  const listContainer = document.getElementById("patientList");
  const initialLoader = document.getElementById("listInitialLoader");
  const loadMoreSpinner = document.getElementById("listLoadMoreSpinner");
  const scrollSentinel = document.getElementById("scrollSentinel");
  const emptyMessage = document.getElementById("listEmptyMessage");

  // Reset state variables
  currentPage = startPage - 1; // It will be incremented to startPage (1) immediately
  hasMore = true;
  isFetching = false;

  // Clear list content before fresh load
  if (listContainer) listContainer.innerHTML = "";

  // Re-attach initial placeholder elements (if they were removed on a previous view)
  if (listContainer) {
    if (initialLoader) listContainer.appendChild(initialLoader);
    if (emptyMessage) listContainer.appendChild(emptyMessage);
  }

  // Disconnect old observer if it exists
  if (observer && scrollSentinel) {
    observer.unobserve(scrollSentinel);
    observer = null;
  }

  // Set up the Intersection Observer for infinite scrolling
  if (attachScroll && scrollSentinel) {
    const intersectionCallback = (entries, observer) => {
      entries.forEach((entry) => {
        // If the sentinel element is visible and we have more pages to load
        if (entry.isIntersecting && hasMore && !isFetching) {
          // Pass the necessary DOM references when calling the fetcher
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
      root: document.getElementById("patientListContainer"), // Observe intersection within the scrollable container
      rootMargin: "0px 0px 50px 0px", // Load content when sentinel is 50px away from the bottom
      threshold: 0.1,
    });

    observer.observe(scrollSentinel);
  }

  // Initial load of the first page
  // Pass the necessary DOM references for the initial fetch
  fetchAndRenderPatients(
    listContainer,
    initialLoader,
    loadMoreSpinner,
    scrollSentinel,
    emptyMessage
  );
};
