// logs.js

(function () {
  // State for each log type
  const logState = {
    activity: { page: 0, hasMore: true, isFetching: false, observer: null },
    changelog: { page: 0, hasMore: true, isFetching: false, observer: null },
  };

  const LogManager = {
    // --- Activity Log (Security) ---
    loadActivityLogs() {
      this._initScrollableLog("activity", {
        tableId: "activityLogTable",
        loaderId: "activityLoader",
        emptyId: "activityEmptyState",
        scrollContainerId: "activityScrollContainer",
        sentinelId: "activityScrollSentinel",
        loadMoreId: "activityLoadMoreSpinner",
        apiUrl: "/logs/api/activity",
      });
    },

    // --- Change Log (Data Changes) ---
    loadChangeLogs() {
      this._initScrollableLog("changelog", {
        tableId: "changeLogTable",
        loaderId: "changeLogLoader",
        emptyId: "changeLogEmptyState",
        scrollContainerId: "changeLogScrollContainer",
        sentinelId: "changeLogScrollSentinel",
        loadMoreId: "changeLogLoadMoreSpinner",
        apiUrl: "/logs/api/changelog",
      });
    },

    // --- Initialize scrollable log with IntersectionObserver ---
    _initScrollableLog(logType, config) {
      const state = logState[logType];
      const tableBody = document.querySelector(`#${config.tableId} tbody`);
      const loader = document.getElementById(config.loaderId);
      const emptyState = document.getElementById(config.emptyId);
      const scrollContainer = document.getElementById(config.scrollContainerId);
      const sentinel = document.getElementById(config.sentinelId);
      const loadMoreSpinner = document.getElementById(config.loadMoreId);

      if (!tableBody) return;

      // Reset state
      state.page = 0;
      state.hasMore = true;
      state.isFetching = false;

      // Disconnect existing observer
      if (state.observer) {
        state.observer.disconnect();
        state.observer = null;
      }

      // Clear table
      tableBody.innerHTML = "";
      if (loader) loader.style.display = "flex";
      if (emptyState) emptyState.style.display = "none";

      // Fetch function
      const fetchLogs = async () => {
        if (!state.hasMore || state.isFetching) return;

        state.isFetching = true;
        state.page += 1;

        if (state.page > 1 && loadMoreSpinner) {
          loadMoreSpinner.classList.remove("hidden");
        }

        try {
          const response = await fetch(`${config.apiUrl}?page=${state.page}`);
          if (!response.ok) throw new Error("Failed to fetch logs");

          const data = await response.json();
          const logs = data.logs || [];
          state.hasMore = data.has_more;

          if (state.page === 1) {
            if (loader) loader.style.display = "none";
          }

          if (logs.length > 0) {
            this._renderLogs(config.tableId, tableBody, logs);
          } else if (state.page === 1 && emptyState) {
            emptyState.style.display = "flex";
          }
        } catch (error) {
          console.error("Error fetching logs:", error);
          if (loader) loader.style.display = "none";
          if (state.page === 1) {
            const colspan = config.tableId === "activityLogTable" ? 4 : 3;
            tableBody.innerHTML = `<tr><td colspan="${colspan}" style="text-align:center; color:var(--danger); padding: 20px;">Error loading logs.</td></tr>`;
          }
        } finally {
          state.isFetching = false;
          if (loadMoreSpinner) loadMoreSpinner.classList.add("hidden");
          if (!state.hasMore && state.observer && sentinel) {
            state.observer.unobserve(sentinel);
          }
        }
      };

      // Setup IntersectionObserver
      if (sentinel && scrollContainer) {
        state.observer = new IntersectionObserver(
          (entries) => {
            entries.forEach((entry) => {
              if (entry.isIntersecting && state.hasMore && !state.isFetching) {
                fetchLogs();
              }
            });
          },
          {
            root: scrollContainer,
            rootMargin: "200px",
            threshold: 0.1,
          }
        );
        state.observer.observe(sentinel);
      }

      // Initial fetch
      fetchLogs();
    },

    // --- Render logs to table ---
    _renderLogs(tableId, tbody, logs) {
      const fragment = document.createDocumentFragment();
      const isActivityLog = tableId === "activityLogTable";

      logs.forEach((log) => {
        const tr = document.createElement("tr");
        tr.className = "log-row";

        // Timestamp parsing
        const dateObj = new Date(log.timestamp);
        const dateStr = dateObj.toLocaleDateString(undefined, {
          month: "short",
          day: "numeric",
          year: "numeric",
        });
        const timeStr = dateObj.toLocaleTimeString(undefined, {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        });

        let userName = log.user_name;
        let userRole = log.user_role;
        let message = log.info;

        if (!userName) {
          const match = message.match(/^(.+?) \((.+?)\): (.*)/);
          if (match) {
            userName = match[1];
            userRole = match[2];
            message = match[3];
          } else {
            const split = message.split(": ");
            if (split.length > 1) {
              userName = split[0];
              message = split.slice(1).join(": ");
              userRole = "Unknown";
            } else {
              userName = "System";
              userRole = "-";
            }
          }
        }

        if (!userRole) userRole = "User";

        const clientOS = log.client_os || "Unknown OS";
        const clientIP = log.client_ip || "Unknown IP";

        tr.innerHTML = `
          <td class="col-timestamp">
            <div class="log-date">${dateStr}</div>
            <div class="log-time">${timeStr}</div>
          </td>
          <td class="col-user">
            <div class="log-user-name">${userName}</div>
            <div class="log-user-role">${userRole}</div>
          </td>
          <td class="col-message">
            <div class="log-message-text log-level-${log.log_level}">${message}</div>
          </td>
          ${
            isActivityLog
              ? `
          <td class="col-client">
            <div class="log-client-os">${clientOS}</div>
            <div class="log-client-ip">${clientIP}</div>
          </td>`
              : ""
          }
        `;
        fragment.appendChild(tr);
      });

      tbody.appendChild(fragment);
    },

    init(viewId) {
      if (viewId === "activity") {
        this.loadActivityLogs();
      } else if (viewId === "changelog") {
        this.loadChangeLogs();
      }
    },
  };

  window.logManager = LogManager;
})();
