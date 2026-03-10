<script>
  export let apiUrls = {};
  export let user = null;
  export let roles = [];

  // Edit mode if user is provided
  const editMode = !!user;

  let username = user ? user.username : '';
  let email = user ? user.email : '';
  let firstName = user ? user.first_name : '';
  let lastName = user ? user.last_name : '';
  let isActive = user ? user.is_active : true;
  let selectedRoleIds = user ? (user.roleIds || []) : [];

  // Password fields only in create mode
  let password = '';
  let password2 = '';

  let saving = false;
  let error = null;
  let fieldErrors = {};

  function getCsrf() {
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? m[1] : '';
  }

  function toggleRole(roleId) {
    if (selectedRoleIds.includes(roleId)) {
      selectedRoleIds = selectedRoleIds.filter(id => id !== roleId);
    } else {
      selectedRoleIds = [...selectedRoleIds, roleId];
    }
  }

  async function submit() {
    saving = true;
    error = null;
    fieldErrors = {};

    // Client-side validation
    if (!editMode) {
      if (!username.trim()) { fieldErrors.username = 'Username is required.'; }
      if (!password) { fieldErrors.password = 'Password is required.'; }
      else if (password.length < 8) { fieldErrors.password = 'Password must be at least 8 characters.'; }
      if (password !== password2) { fieldErrors.password2 = 'Passwords do not match.'; }
    }
    if (!email.trim()) { fieldErrors.email = 'Email is required.'; }

    if (Object.keys(fieldErrors).length > 0) {
      saving = false;
      return;
    }

    const payload = {
      email: email.trim(),
      first_name: firstName.trim(),
      last_name: lastName.trim(),
      is_active: isActive,
    };

    if (!editMode) {
      payload.username = username.trim();
      payload.password = password;
    }

    const url = editMode ? apiUrls.userDetail : apiUrls.users;
    const method = editMode ? 'PATCH' : 'POST';

    try {
      const res = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrf(),
        },
        body: JSON.stringify(payload),
      });

      saving = false;

      if (res.ok) {
        // Redirect to list
        window.location.href = apiUrls.listUrl;
      } else {
        const d = await res.json();
        if (typeof d === 'object') {
          for (const [k, v] of Object.entries(d)) {
            fieldErrors[k] = Array.isArray(v) ? v.join(' ') : String(v);
          }
          error = 'Please fix the errors below.';
        } else {
          error = String(d);
        }
      }
    } catch (e) {
      saving = false;
      error = 'Network error. Please try again.';
    }
  }
</script>

<div class="space-y-6">

  {#if error}
    <div class="px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-800">
      {error}
    </div>
  {/if}

  <!-- Account Info -->
  <div>
    <h3 class="text-base font-semibold text-gray-900 mb-4 pb-2 border-b border-gray-200">
      Account Information
    </h3>
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">

      <!-- Username -->
      {#if !editMode}
        <div class="sm:col-span-2">
          <label class="block text-sm font-medium text-gray-700 mb-1">
            Username <span class="text-red-500">*</span>
          </label>
          <input
            type="text"
            bind:value={username}
            class="block w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            placeholder="username"
          />
          {#if fieldErrors.username}
            <p class="mt-1 text-xs text-red-600">{fieldErrors.username}</p>
          {/if}
        </div>
      {:else}
        <div class="sm:col-span-2">
          <label class="block text-sm font-medium text-gray-700 mb-1">Username</label>
          <p class="px-3 py-2 text-sm text-gray-900 bg-gray-50 border border-gray-200 rounded-lg font-mono">{username}</p>
          <p class="mt-1 text-xs text-gray-400">Username cannot be changed after account creation.</p>
        </div>
      {/if}

      <!-- First Name -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">First Name</label>
        <input
          type="text"
          bind:value={firstName}
          class="block w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          placeholder="First name"
        />
      </div>

      <!-- Last Name -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Last Name</label>
        <input
          type="text"
          bind:value={lastName}
          class="block w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          placeholder="Last name"
        />
      </div>

      <!-- Email -->
      <div class="sm:col-span-2">
        <label class="block text-sm font-medium text-gray-700 mb-1">
          Email <span class="text-red-500">*</span>
        </label>
        <input
          type="email"
          bind:value={email}
          class="block w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          placeholder="email@example.com"
        />
        {#if fieldErrors.email}
          <p class="mt-1 text-xs text-red-600">{fieldErrors.email}</p>
        {/if}
      </div>

      <!-- Password — create only -->
      {#if !editMode}
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            Password <span class="text-red-500">*</span>
          </label>
          <input
            type="password"
            bind:value={password}
            class="block w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            placeholder="At least 8 characters"
          />
          {#if fieldErrors.password}
            <p class="mt-1 text-xs text-red-600">{fieldErrors.password}</p>
          {/if}
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            Confirm Password <span class="text-red-500">*</span>
          </label>
          <input
            type="password"
            bind:value={password2}
            class="block w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            placeholder="Repeat password"
          />
          {#if fieldErrors.password2}
            <p class="mt-1 text-xs text-red-600">{fieldErrors.password2}</p>
          {/if}
          <p class="mt-1 text-xs text-gray-400">Minimum 8 characters.</p>
        </div>
      {/if}

    </div>
  </div>

  <!-- Roles & Access -->
  <div>
    <h3 class="text-base font-semibold text-gray-900 mb-4 pb-2 border-b border-gray-200">
      Roles & Access
    </h3>
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-6">

      <!-- Roles checkboxes -->
      <div>
        <p class="text-sm font-medium text-gray-700 mb-2">Roles</p>
        <div class="space-y-2 border border-gray-200 rounded-lg p-3 bg-gray-50">
          {#if roles.length > 0}
            {#each roles as role}
              <label class="flex items-center gap-3 cursor-pointer group">
                <input
                  type="checkbox"
                  checked={selectedRoleIds.includes(role.id)}
                  on:change={() => toggleRole(role.id)}
                  class="h-4 w-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
                />
                <span class="text-sm text-gray-700 group-hover:text-gray-900">{role.name}</span>
              </label>
            {/each}
          {:else}
            <p class="text-sm text-gray-400 italic">No roles defined.</p>
          {/if}
        </div>
      </div>

      <!-- Status -->
      <div class="space-y-4">
        <div class="flex items-center gap-3">
          <input
            type="checkbox"
            id="is_active"
            bind:checked={isActive}
            class="h-4 w-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
          />
          <label for="is_active" class="text-sm font-medium text-gray-700 cursor-pointer">
            Active Account
          </label>
        </div>
        <p class="text-xs text-gray-400">Inactive users cannot log in.</p>
      </div>

    </div>
  </div>

  <!-- Footer -->
  <div class="flex items-center justify-end gap-3 pt-4 border-t border-gray-200">
    <a
      href={apiUrls.listUrl}
      class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
    >
      Cancel
    </a>
    <button
      on:click={submit}
      disabled={saving}
      class="px-6 py-2 text-sm font-medium text-white bg-indigo-600 border border-transparent rounded-lg hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
    >
      {saving ? 'Saving...' : (editMode ? 'Save Changes' : 'Create User')}
    </button>
  </div>

</div>
