// user_manager.js

(function () {
  const API = {
    LIST: "/admin/api/users",
    UPDATE_EMAIL: "/admin/api/users/update-email",
    UPDATE_ROLE: "/admin/api/users/update-role",
    RESET_PASSWORD: "/admin/api/users/reset-password/",
    DELETE_USER: "/admin/api/users/delete/",
    UNLOCK_USER: "/admin/api/users/unlock",
    SELF_UPDATE_EMAIL: "/admin/api/self/update-email",
    SELF_RESET_PASSWORD: "/admin/api/self/reset-password",
  };

  let currentUserId = null;
  let userListCache = [];
  let activeAction = {};

  // Modal Management

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

    const oldField = document.getElementById("actionValue");
    if (oldField) oldField.remove();

    const isRole =
      typeof inputLabel === "string" &&
      inputLabel.toLowerCase().indexOf("role") !== -1;

    let newField;
    if (isRole) {
      const select = document.createElement("select");
      select.id = "actionValue";
      select.name = "actionValue";
      select.className = "modern-input";
      select.required = true;

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
      const input = document.createElement("input");
      input.type = "email";
      input.id = "actionValue";
      input.name = "actionValue";
      input.className = "modern-input";
      input.required = true;
      if (inputValue) input.value = inputValue;
      newField = input;
    }

    const labelEl = document.getElementById("inputLabel");
    if (labelEl && labelEl.parentNode) {
      if (labelEl.nextSibling)
        labelEl.parentNode.insertBefore(newField, labelEl.nextSibling);
      else labelEl.parentNode.appendChild(newField);
    } else {
      form.insertBefore(newField, form.querySelector(".modal-actions"));
    }

    document.getElementById("inputHelp").innerText = inputHelp || "";

    form.onsubmit = function (event) {
      event.preventDefault();
      const field = document.getElementById("actionValue");
      const value = field ? field.value : null;
      if (value === null || value === "") {
        const help = document.getElementById("inputHelp");
        if (help) help.innerText = "Please provide a value.";
        return;
      }
      Promise.resolve(onSubmit(value))
        .then(() => {
          closeModal("actionModal");
        })
        .catch((err) => {
          const help = document.getElementById("inputHelp");
          if (help)
            help.innerText = err && err.message ? err.message : "Action failed";
          else
            window.notify.error(
              err && err.message ? err.message : "Action failed"
            );
        });
    };

    modal.classList.remove("hidden");
    setTimeout(() => {
      const f = document.getElementById("actionValue");
      if (f && typeof f.focus === "function") f.focus();
    }, 200);
  }

  function closeModal(id) {
    const m = document.getElementById(id);
    if (m) m.classList.add("hidden");
    activeAction = {};
  }

  // Admin Self-Update

  async function handleAdminSelfUpdate(event, type) {
    const button = event?.target?.closest?.("button");

    if (type === "update-email") {
      const adminUser = userListCache.find((u) => u.id === currentUserId) || {};
      setupAndShowActionModal(
        "Update Your Email",
        "Enter the new email address for your admin account.",
        "New Email Address",
        adminUser.email || "",
        "We will update your contact email immediately (you may want to verify it).",
        async (newEmail) => {
          const result = await performApiAction(
            API.SELF_UPDATE_EMAIL,
            { email: newEmail },
            "POST",
            "Email updated.",
            "Failed to update email."
          );

          if (result && result.success) {
            await loadUserList();
          } else {
            throw new Error(
              (result && result.message) || "Email update failed."
            );
          }
        }
      );

      return;
    }

    if (!button) {
      console.error("No button element found for admin self update.");
      return;
    }

    const originalContent = button.innerHTML;
    try {
      button.disabled = true;
      button.innerHTML = '<span class="material-icons spin">refresh</span>';

      const result = await performApiAction(
        API.SELF_RESET_PASSWORD,
        {},
        "POST",
        null,
        "Password reset failed."
      );

      if (result && result.success) {
        const pwd =
          result.temp_password || result.new_password || result.password;
        if (pwd) {
          const displayEl = document.getElementById("newPasswordDisplay");
          if (displayEl) displayEl.innerText = pwd;
          const pm = document.getElementById("passwordModal");
          if (pm) pm.classList.remove("hidden");
          else window.notify.success("Password: " + pwd);
        } else {
          window.notify.success(
            result.message || "Password reset successfully."
          );
        }
      }
    } catch (err) {
      console.error("Admin self-update failed:", err);
      window.notify.error(
        err.message || err
      );
    } finally {
      button.disabled = false;
      button.innerHTML = originalContent;
    }
  }

  async function handleUserAction(action, userId) {
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
          await loadUserList();
        }
      );
    } else if (action === "role") {
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
          await loadUserList();
        }
      );
    } else if (action === "reset_password") {
      window.notify.info("Generating new password...");

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
              window.notify.success(
                result.message || "Password reset successfully."
              );
            }
          }
        })
        .catch((err) => {
          console.error("Reset password error:", err);
        });
    } else if (action === "delete") {

      await performApiAction(
        API.DELETE_USER + userId,
        {},
        "DELETE",
        `User ${targetUser.name} deleted successfully.`,
        "Failed to delete user."
      );
      await loadUserList();
    } else if (action === "unlock") {

      await performApiAction(
        API.UNLOCK_USER,
        { user_id: userId },
        "PATCH",
        `User ${targetUser.name} unlocked.`,
        "Failed to unlock user."
      );
      await loadUserList();
    }
  }

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
        if (successMessage) window.notify.success(successMessage);
        return result;
      } else {
        const msg =
          (result && result.message) || errorMessage || "Action failed";
        window.notify.error(msg);
        return result || null;
      }
    } catch (error) {
      console.error("API Action Error:", error);
      window.notify.error(errorMessage || "Action failed");
      throw error;
    }
  }

  // Rendering Functions

  async function loadUserList() {
    const listContainer = document.getElementById("user-list-container");
    const adminContainer = document.getElementById("admin-profile-container");
    if (!listContainer || !adminContainer) return;

    listContainer.innerHTML = `<p style="text-align:center; color:#86868b; margin-top: 30px;">Fetching user data...</p>`;
    adminContainer.innerHTML = `<p style="text-align:center; color:#86868b;">Loading admin profile...</p>`;

    try {
      const data = await window.fetchJson(API.LIST);

      currentUserId = data.current_user_id;
      userListCache = data.users || [];

      const adminUser = userListCache.find((u) => u.id === currentUserId);
      const otherUsers = userListCache.filter((u) => u.id !== currentUserId);

      if (adminUser) {
        adminContainer.innerHTML = renderAdminProfile(adminUser);
      } else {
        adminContainer.innerHTML = `<p style="color:red;">Error: Admin profile not found.</p>`;
      }

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
    </div>
  `;
  }

  function renderUserRow(user) {
    const userId = user.id;
    const currentRole = user.role;
    const isLocked = user.is_locked;
    
    // Lock badge
    const lockBadge = isLocked 
      ? `<span class="role-badge" style="background-color: #dc3545; color: white; margin-left: 8px;">Locked</span>` 
      : "";
      
    // Unlock button
    const unlockBtn = isLocked
      ? `<button class="btn-action" title="Unlock User" onclick="window.handleUserAction('unlock', ${userId})">
           <span class="material-icons" style="color: #28a745;">lock_open</span>
         </button>`
      : "";

    return `
      <div class="user-list-row" data-user-id="${userId}">
        <div class="user-info">
          <span class="user-name">${user.name}</span>
          <span class="user-email">${user.email}</span>
        </div>
        <div class="user-role">
          <span class="role-badge">${currentRole}</span>
          ${lockBadge}
        </div>
        <div class="user-actions">
          ${unlockBtn}
          <button class="btn-action" title="Update Email" onclick="window.handleUserAction('email', ${userId})">
            <span class="material-icons">edit</span>
          </button>
          <button class="btn-action" title="Change Role" onclick="window.handleUserAction('role', ${userId})">
            <span class="material-icons">security</span>
          </button>
          <button class="btn-action btn-danger" title="Reset Password" onclick="window.handleUserAction('reset_password', ${userId})">
            <span class="material-icons">lock_reset</span>
          </button>
          <button class="btn-action btn-danger" title="Delete User" onclick="window.handleUserAction('delete', ${userId})">
            <span class="material-icons">delete_forever</span>
          </button>
        </div>
      </div>
    `;
  }

  function copyPassword() {
    const textEl = document.getElementById("newPasswordDisplay");
    if (!textEl) {
      window.notify.error("No password to copy.");
      return;
    }
    const text = textEl.innerText || textEl.textContent;
    const tempInput = document.createElement("textarea");
    tempInput.value = text;
    document.body.appendChild(tempInput);
    tempInput.select();
    try {
      document.execCommand("copy");
      window.notify.success("Password copied to clipboard!");
    } catch (err) {
      window.notify.error("Could not copy password.");
    }
    document.body.removeChild(tempInput);
  }

  window.userManager = {
    init: loadUserList,
    closeModal: closeModal,
    copyPassword: copyPassword,
  };

  window.handleAdminSelfUpdate = handleAdminSelfUpdate;
  window.handleUserAction = handleUserAction;

  window.addEventListener("DOMContentLoaded", () => {
    if (document.querySelector(".user-manager-container")) {
      // Intentionally empty
    }
  });
})();
