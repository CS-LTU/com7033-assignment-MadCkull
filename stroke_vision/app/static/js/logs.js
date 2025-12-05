// logs.js

(function () {
  const LogManager = {
        // --- Activity Log (Security) ---
    async loadActivityLogs() {
      this._loadLogs(
        "activityLogTable",
        "activityLoader",
        "activityEmptyState",
        "/logs/api/activity"
      );
    },

        // --- Change Log (Data Changes) ---
    async loadChangeLogs() {
      this._loadLogs(
        "changeLogTable",
        "changeLogLoader",
        "changeLogEmptyState",
        "/logs/api/changelog"
      );
    },

        // --- Generic Load Logic ---
    async _loadLogs(tableId, loaderId, emptyId, apiUrl) {
      console.log(`Loading logs from ${apiUrl}...`);
      const tableBody = document.querySelector(`#${tableId} tbody`);
      const loader = document.getElementById(loaderId);
      const emptyState = document.getElementById(emptyId);

      if (!tableBody) return;

      tableBody.innerHTML = "";
      if (loader) loader.style.display = "flex";
      if (emptyState) emptyState.style.display = "none";

      try {
        const response = await fetch(apiUrl);
        if (!response.ok) throw new Error("Failed to fetch logs");
        const logs = await response.json();

        this.renderTable(tableBody, logs, loader, emptyState);
      } catch (error) {
        console.error("Error fetching logs:", error);
        if (loader) loader.style.display = "none";
        tableBody.innerHTML = `<tr><td colspan="4" style="text-align:center; color:var(--danger); padding: 20px;">Error loading logs: ${error.message}</td></tr>`;
      }
    },

        // --- Render Logic ---
    renderTable(tbody, data, loader, emptyState) {
      if (loader) loader.style.display = "none";

      if (!data || data.length === 0) {
        if (emptyState) emptyState.style.display = "flex";
        return;
      }

      const fragment = document.createDocumentFragment();

        data.forEach(log => {
        const tr = document.createElement("tr");
        tr.className = `log-row log-level-${log.log_level}`;

                // --- 1. Timestamp Parsing ---
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
                        <div class="log-message-text">${message}</div>
                    </td>
                    <td class="col-client">
                        <div class="log-client-os">${clientOS}</div>
                        <div class="log-client-ip">${clientIP}</div>
                    </td>
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
