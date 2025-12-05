// =======================================================
// user_manager.js (Unified Client-side logic for Admin User Management)
// - Role change uses a select (Doctor, Nurse)
// - Admin password reset shows temp password like other users
// =======================================================

(function () {
  const API = {
    LIST: "/admin/api/users",
    UPDATE_EMAIL: "/admin/api/users/update-email",
    UPDATE_ROLE: "/admin/api/users/update-role",
    // This endpoint is used with an ID suffix for target user: API.RESET_PASSWORD + userId
    RESET_PASSWORD: "/admin/api/users/reset-password/",
    SELF_UPDATE_EMAIL: "/admin/api/self/update-email",
    SELF_RESET_PASSWORD: "/admin/api/self/reset-password",
  };

  let currentUserId = null;
  let userListCache = []; // To hold the user list data
  let activeAction = {}; // Stores state for the generic action modal

  // --- Modal Management ---

  /**
   * Sets up and shows the generic action modal (for Email/Role updates).
   *
   * If inputLabel suggests a Role change (i.e. contains 'role'), we render a select
   * with the options ["Doctor", "Nurse"] and keep the element id as 'actionValue'
   * so submit code reads value uniformly.
   *
   * @param {string} title
   * @param {string} prompt
   * @param {string} inputLabel
   * @param {string} inputValue
   * @param {string} inputHelp
   * @param {function(string):Promise<void>} onSubmit
   */
  function setupAndShowActionModal(
    title,
    prompt,
    inputLabel,
    inputValue,
    inputHelp,
    onSubmit
  ) {
    const modal = document.getElementById("actionModal");
    const form = document.getElementById("actionForm");

    document.getElementById("modalTitle").innerText = title || "";
    document.getElementById("modalPrompt").innerText = prompt || "";
    document.getElementById("inputLabel").innerText = inputLabel || "";

    // Replace existing field with either <input id="actionValue"> or <select id="actionValue">
    // We keep the id 'actionValue' so submit handler reads uniformly.
    const oldField = document.getElementById("actionValue");
    if (oldField) oldField.remove();

    // Determine if it's a role change by inputLabel content
    const isRole =
      typeof inputLabel === "string" &&
      inputLabel.toLowerCase().indexOf("role") !== -1;

    let newField;
    if (isRole) {
      // Create select
      const select = document.createElement("select");
      select.id = "actionValue";
      select.name = "actionValue";
      select.className = "modern-input";
      select.required = true;

      // Options: Doctor, Nurse (values match display)
      const roles = ["Doctor", "Nurse"];
      roles.forEach((r) => {
        const opt = document.createElement("option");
        opt.value = r;
        opt.textContent = r;
        select.appendChild(opt);
      });

      if (inputValue) select.value = inputValue;
      newField = select;
    } else {
      // Email or other free-text
      const input = document.createElement("input");
      input.type = "email";
      input.id = "actionValue";
      input.name = "actionValue";
      input.className = "modern-input";
      input.required = true;
      if (inputValue) input.value = inputValue;
      newField = input;
    }

    // Insert the new field into the DOM where label was expected to reference it.
    // We'll try to insert after the label if present; otherwise append to form.
    const labelEl = document.getElementById("inputLabel");
    if (labelEl && labelEl.parentNode) {
      // Insert right after label
      if (labelEl.nextSibling)
        labelEl.parentNode.insertBefore(newField, labelEl.nextSibling);
      else labelEl.parentNode.appendChild(newField);
    } else {
      // fallback: append to form
      form.insertBefore(newField, form.querySelector(".modal-actions"));
    }

    document.getElementById("inputHelp").innerText = inputHelp || "";

    // Remove any existing handler and attach new one for this modal usage
    form.onsubmit = function (event) {
      event.preventDefault();
      const field = document.getElementById("actionValue");
      const value = field ? field.value : null;
      if (value === null || value === "") {
        // show a short inline hint
        const help = document.getElementById("inputHelp");
        if (help) help.innerText = "Please provide a value.";
        return;
      }
      // call async onSubmit and close modal on success
      Promise.resolve(onSubmit(value))
        .then(() => {
          closeModal("actionModal");
        })
        .catch((err) => {
          // show error inline if possible, else toast
          const help = document.getElementById("inputHelp");
          if (help)
            help.innerText = err && err.message ? err.message : "Action failed";
          else
            window.showToast(
              err && err.message ? err.message : "Action failed",
              "danger"
            );
        });
    };

    modal.classList.remove("hidden");
    // Focus the field after a short delay so CSS transitions are done
    setTimeout(() => {
      const f = document.getElementById("actionValue");
      if (f && typeof f.focus === "function") f.focus();
    }, 200);
  }

  /**
   * Closes a specific modal by adding the 'hidden' class.
   * @param {string} id The ID of the modal element.
   */
  function closeModal(id) {
    const m = document.getElementById(id);
    if (m) m.classList.add("hidden");
    activeAction = {};
  }

  // --- Core Action Handlers ---

  // --- Handle Admin Self-Update (Reset Password Only) ---
  /**
   * Handler for the Admin's self-reset password button.
   * NOTE: This is now ONLY for the self-reset password function,
   * as self-profile update is handled by the main /settings/view.
   */
  // --- Handle Admin Self-Update (Reset Password or Update Email via modal) ---
  async function handleAdminSelfUpdate(event, type) {
    // Find clicked button (for spinner on reset)
    const button = event?.target?.closest?.("button");

    // --- UPDATE EMAIL: open the same modal used for other users ---
    if (type === "update-email") {
      const adminUser = userListCache.find((u) => u.id === currentUserId) || {};
      setupAndShowActionModal(
        "Update Your Email",
        "Enter the new email address for your admin account.",
        "New Email Address",
        adminUser.email || "",
        "We will update your contact email immediately (you may want to verify it).",
        // onSubmit
        async (newEmail) => {
          // Use the same performApiAction helper so errors/toasts are consistent
          const result = await performApiAction(
            API.SELF_UPDATE_EMAIL,
            { email: newEmail },
            "POST",
            "Email updated.",
            "Failed to update email."
          );

          // if success, refresh admin profile so displayed email updates
          if (result && result.success) {
            await loadUserList();
          } else {
            // bubble up as rejection so setupAndShowActionModal shows inline error
            throw new Error(
              (result && result.message) || "Email update failed."
            );
          }
        }
      );

      return;
    }

    // --- RESET PASSWORD: show spinner on the button and call endpoint ---
    if (!button) {
      console.error("No button element found for admin self update.");
      return;
    }

    const originalContent = button.innerHTML;
    try {
      button.disabled = true;
      button.innerHTML = '<span class="material-icons spin">refresh</span>';

      if (
        !confirm(
          "Are you sure you want to reset your own password? A temporary password will be set."
        )
      ) {
        return;
      }

      // Use performApiAction so we get consistent error-handling/toasts
      const result = await performApiAction(
        API.SELF_RESET_PASSWORD,
        {},
        "POST",
        null,
        "Password reset failed."
      );

      if (result && result.success) {
        // prefer commonly named fields used elsewhere
        const pwd =
          result.temp_password || result.new_password || result.password;
        if (pwd) {
          const displayEl = document.getElementById("newPasswordDisplay");
          if (displayEl) displayEl.innerText = pwd;
          const pm = document.getElementById("passwordModal");
          if (pm) pm.classList.remove("hidden");
          else window.showToast("Password: " + pwd, "success");
        } else {
          window.showToast(
            result.message || "Password reset successfully.",
            "success"
          );
        }
      }
    } catch (err) {
      console.error("Admin self-update failed:", err);
      window.showToast(
        "An unexpected error occurred: " + (err.message || err),
        "danger"
      );
    } finally {
      button.disabled = false;
      button.innerHTML = originalContent;
    }
  }

  /**
   * Handles administrative actions for other users (Email, Role, Password Reset).
   * @param {string} action 'email', 'role', or 'reset_password'
   * @param {number} userId The target user's ID
   */
  function handleUserAction(action, userId) {
    const targetUser = userListCache.find((u) => u.id === userId);
    if (!targetUser) return;

    if (action === "email") {
      setupAndShowActionModal(
        `Update Email for ${targetUser.name}`,
        `Enter the new email address for ${targetUser.name}.`,
        "New Email Address",
        targetUser.email,
        "This will immediately update the user's login email.",
        async (newEmail) => {
          await performApiAction(
            API.UPDATE_EMAIL,
            { user_id: userId, email: newEmail },
            "PATCH",
            `Successfully updated ${targetUser.name}'s email.`,
            "Failed to update user email."
          );
          await loadUserList(); // Refresh
        }
      );
    } else if (action === "role") {
      // Render a select for role change (Doctor / Nurse)
      setupAndShowActionModal(
        `Change Role for ${targetUser.name}`,
        `Select the new role for ${targetUser.name}.`,
        "New Role",
        targetUser.role,
        "Changing roles affects permissions.",
        async (newRole) => {
          await performApiAction(
            API.UPDATE_ROLE,
            { user_id: userId, role: newRole },
            "PATCH",
            `Successfully changed ${targetUser.name}'s role to ${newRole}.`,
            "Failed to update user role."
          );
          await loadUserList(); // Refresh
        }
      );
    } else if (action === "reset_password") {
      if (
        !confirm(
          `Are you sure you want to reset the password for ${targetUser.name}? This action cannot be undone.`
        )
      )
        return;

      window.showToast("Generating new password...", "info");

      performApiAction(
        API.RESET_PASSWORD + userId,
        {},
        "POST",
        null,
        "Password reset failed."
      )
        .then((result) => {
          if (result && result.success) {
            const pwd =
              result.new_password || result.temp_password || result.password;
            if (pwd) {
              const displayEl = document.getElementById("newPasswordDisplay");
              if (displayEl) displayEl.innerText = pwd;
              document
                .getElementById("passwordModal")
                .classList.remove("hidden");
            } else {
              window.showToast(
                result.message || "Password reset successfully.",
                "success"
              );
            }
          }
        })
        .catch((err) => {
          console.error("Reset password error:", err);
        });
    }
  }

  /**
   * Generic API call handler
   */
  async function performApiAction(
    url,
    data,
    method,
    successMessage,
    errorMessage
  ) {
    try {
      const result = await window.fetchJson(url, {
        method: method,
        body: JSON.stringify(data),
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (result && result.success) {
        if (successMessage) window.showToast(successMessage, "success");
        return result;
      } else {
        // if result object present but not success show its message
        const msg =
          (result && result.message) || errorMessage || "Action failed";
        window.showToast(msg, "danger");
        return result || null;
      }
    } catch (error) {
      console.error("API Action Error:", error);
      window.showToast(errorMessage || "Action failed", "danger");
      throw error;
    }
  }

  // --- Rendering Functions ---

  /**
   * Fetches the user list data, processes it, and renders the view.
   */
  async function loadUserList() {
    const listContainer = document.getElementById("user-list-container");
    const adminContainer = document.getElementById("admin-profile-container");
    if (!listContainer || !adminContainer) return;

    listContainer.innerHTML = `<p style="text-align:center; color:#86868b; margin-top: 30px;">Fetching user data...</p>`;
    adminContainer.innerHTML = `<p style="text-align:center; color:#86868b;">Loading admin profile...</p>`;

    try {
      // API.LIST returns { current_user_id: 1, users: [...] }
      const data = await window.fetchJson(API.LIST);

      currentUserId = data.current_user_id;
      userListCache = data.users || [];

      const adminUser = userListCache.find((u) => u.id === currentUserId);
      const otherUsers = userListCache.filter((u) => u.id !== currentUserId);

      // 1. Render Admin Profile
      if (adminUser) {
        adminContainer.innerHTML = renderAdminProfile(adminUser);
      } else {
        adminContainer.innerHTML = `<p style="color:red;">Error: Admin profile not found.</p>`;
      }

      // 2. Render Other Users List
      if (otherUsers.length > 0) {
        listContainer.innerHTML = `
          <div class="user-list-header">
              <span>Name / Email</span>
              <span>Role</span>
              <span>Actions</span>
          </div>
          ${otherUsers.map(renderUserRow).join("")}
        `;
      } else {
        listContainer.innerHTML = `<p style="text-align:center; color:#86868b; margin-top: 30px;">No other users found.</p>`;
      }
    } catch (error) {
      console.error("Error loading user list:", error);
      listContainer.innerHTML = `<p style="color:red; text-align:center; margin-top: 30px;">Failed to load user data: ${error.message}</p>`;
      adminContainer.innerHTML = "";
    }
  }

  /**
   * Generates the HTML for the current admin's profile area.
   * @param {Object} user
   */
  function renderAdminProfile(user) {
    return `
    <div class="admin-profile-card">
      <div class="profile-header">
        <div class="profile-title-left">
          <span class="material-icons">manage_accounts</span>
          <h3>Your Profile (Admin)</h3>
        </div>

        <div class="header-actions" role="toolbar" aria-label="Profile actions">
          <!-- Icon-only buttons: title + aria-label for accessibility -->
          <button
            class="icon-btn"
            title="Update email"
            aria-label="Update email"
            onclick="window.handleAdminSelfUpdate(event, 'update-email')"
          >
            <span class="material-icons">email</span>
          </button>

          <button
            class="icon-btn danger"
            title="Reset password"
            aria-label="Reset password"
            onclick="window.handleAdminSelfUpdate(event, 'reset-password')"
          >
            <span class="material-icons">key_off</span>
          </button>
        </div>
      </div>

      <div class="profile-info-grid">
        <div><label>Name:</label><span>${user.name}</span></div>
        <div><label>Role:</label><span class="role-badge">${user.role} (Cannot be changed here)</span></div>
        <div><label>Email:</label><span>${user.email}</span></div>
        <div><label>Member Since:</label><span>${user.created_at}</span></div>
      </div>

      <!-- Removed bottom action row — actions now live in header -->
    </div>
  `;
  }

  /**
   * Generates the HTML for a single user row in the list.
   * @param {Object} user
   */
  function renderUserRow(user) {
    const userId = user.id;
    const currentRole = user.role;
    return `
      <div class="user-list-row" data-user-id="${userId}">
        <div class="user-info">
          <span class="user-name">${user.name}</span>
          <span class="user-email">${user.email}</span>
        </div>
        <div class="user-role">
          <span class="role-badge">${currentRole}</span>
        </div>
        <div class="user-actions">
          <button class="btn-action" title="Update Email" onclick="window.handleUserAction('email', ${userId})">
            <span class="material-icons">edit</span>
          </button>
          <button class="btn-action" title="Change Role" onclick="window.handleUserAction('role', ${userId})">
            <span class="material-icons">security</span>
          </button>
          <button class="btn-action btn-danger" title="Reset Password" onclick="window.handleUserAction('reset_password', ${userId})">
            <span class="material-icons">lock_reset</span>
          </button>
        </div>
      </div>
    `;
  }

  /**
   * Copies the temporary password from the modal to the clipboard.
   */
  function copyPassword() {
    const textEl = document.getElementById("newPasswordDisplay");
    if (!textEl) {
      window.showToast("No password to copy.", "danger");
      return;
    }
    const text = textEl.innerText || textEl.textContent;
    const tempInput = document.createElement("textarea");
    tempInput.value = text;
    document.body.appendChild(tempInput);
    tempInput.select();
    try {
      document.execCommand("copy");
      window.showToast("Password copied to clipboard!", "success");
    } catch (err) {
      window.showToast("Could not copy password.", "danger");
    }
    document.body.removeChild(tempInput);
  }

  // --- Initialization ---

  // Expose public methods to the window object for HTML and router access
  window.userManager = {
    init: loadUserList,
    closeModal: closeModal,
    copyPassword: copyPassword,
  };

  // Attach global handlers needed by HTML
  window.handleAdminSelfUpdate = handleAdminSelfUpdate;
  window.handleUserAction = handleUserAction;

  // Run on initial page load if the element exists
  window.addEventListener("DOMContentLoaded", () => {
    if (document.querySelector(".user-manager-container")) {
      // router usually calls init; this is a safeguard
      // window.userManager.init();
    }
  });
})();
