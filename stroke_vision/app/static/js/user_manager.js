// =======================================================
// user_manager.js (Unified Client-side logic for Admin User Management)
// =======================================================

(function () {
  const API = {
    LIST: "/admin/api/users",
    UPDATE_EMAIL: "/admin/api/users/update-email",
    UPDATE_ROLE: "/admin/api/users/update-role",
    RESET_PASSWORD: "/admin/api/users/reset-password/", // Requires ID suffix
    SELF_UPDATE_EMAIL: "/admin/api/self/update-email",
    SELF_RESET_PASSWORD: "/admin/api/self/reset-password",
  };

  let currentUserId = null;
  let userListCache = []; // To hold the user list data
  let activeAction = {}; // Stores state for the generic action modal

  // --- Modal Management ---

  /**
   * Sets up and shows the generic action modal (for Email/Role updates).
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

    document.getElementById("modalTitle").innerText = title;
    document.getElementById("modalPrompt").innerText = prompt;
    document.getElementById("inputLabel").innerText = inputLabel;

    const inputField = document.getElementById("actionValue");
    inputField.value = inputValue || "";
    document.getElementById("inputHelp").innerText = inputHelp;

    // Remove existing listener and attach new one
    form.onsubmit = function (event) {
      event.preventDefault();
      const value = inputField.value;
      if (value) {
        onSubmit(value);
        window.userManager.closeModal("actionModal");
      }
    };

    modal.classList.remove("hidden");
    setTimeout(() => inputField.focus(), 300);
  }

  /**
   * Closes a specific modal by adding the 'hidden' class.
   * @param {string} id The ID of the modal element.
   */
  function closeModal(id) {
    document.getElementById(id).classList.add("hidden");
    activeAction = {};
  }

  // --- Core Action Handlers ---

  /**
   * Handles update actions for the currently logged-in admin user (self-management).
   * @param {string} field 'email' or 'password'
   */
  window.handleAdminSelfUpdate = function (field) {
    if (field === "email") {
      const adminUser = userListCache.find((u) => u.id === currentUserId);
      if (!adminUser) return;

      setupAndShowActionModal(
        "Update My Email",
        "Enter your new email address.",
        "New Email Address",
        adminUser.email,
        "Note: Your role cannot be changed via self-management.",
        async (newEmail) => {
          await performApiAction(
            API.SELF_UPDATE_EMAIL,
            { email: newEmail },
            "PATCH",
            "Email update successful. Reloading profile...",
            "Failed to update email."
          );
          // Reload the list to show the new email
          await loadUserList();
        }
      );
    } else if (field === "password") {
      if (
        !confirm(
          "Are you sure you want to reset your own password? You will receive a new temporary password."
        )
      )
        return;

      performApiAction(
        API.SELF_RESET_PASSWORD,
        {},
        "POST",
        "Password reset link/temporary password sent to your email.",
        "Failed to reset password."
      );
    }
  };

  /**
   * Handles administrative actions for other users (Email, Role, Password Reset).
   * @param {string} action 'email', 'role', or 'reset_password'
   * @param {number} userId The target user's ID
   */
  window.handleUserAction = function (action, userId) {
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
      setupAndShowActionModal(
        `Change Role for ${targetUser.name}`,
        `Enter the new role for ${targetUser.name} (e.g., 'Admin', 'Editor', 'Viewer').`,
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
        // Success message is handled within the fetchJson logic to show the modal
        null,
        "Password reset failed."
      ).then((result) => {
        if (result && result.success) {
          // Display the temporary password modal
          document.getElementById("newPasswordDisplay").innerText =
            result.new_password;
          document.getElementById("passwordModal").classList.remove("hidden");
        }
      });
    }
  };

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

      if (result.success) {
        if (successMessage) window.showToast(successMessage, "success");
        return result;
      } else {
        window.showToast(result.message || errorMessage, "danger");
      }
    } catch (error) {
      console.error("API Action Error:", error);
      window.showToast(errorMessage, "danger");
    }
    return null;
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
      userListCache = data.users;

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
          <span class="material-icons">manage_accounts</span>
          <h3>Your Profile (Admin)</h3>
        </div>

        <div class="profile-info-grid">
          <div><label>Name:</label><span>${user.name}</span></div>
          <div><label>Role:</label><span class="role-badge">${user.role} (Cannot be changed here)</span></div>
          <div><label>Email:</label><span>${user.email}</span></div>
          <div><label>Member Since:</label><span>${user.created_at}</span></div>
        </div>

        <div class="profile-actions">
          <button class="btn-action" onclick="window.handleAdminSelfUpdate('email')">
            <span class="material-icons">email</span> Update Email
          </button>
          <button class="btn-action btn-danger" onclick="window.handleAdminSelfUpdate('password')">
            <span class="material-icons">key_off</span> Reset Password
          </button>
        </div>
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
    const text = document.getElementById("newPasswordDisplay").innerText;
    // Use the older execCommand for better iFrame compatibility
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
  window.handleAdminSelfUpdate = window.handleAdminSelfUpdate;
  window.handleUserAction = window.handleUserAction;

  // Run on initial page load if the element exists
  window.addEventListener("DOMContentLoaded", () => {
    if (document.querySelector(".user-manager-container")) {
      // In a dynamic app, the router calls init, but this is a safeguard
      // window.userManager.init();
    }
  });
})();
