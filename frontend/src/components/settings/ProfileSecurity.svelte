<script>
  export let apiUrls = {};

  let oldPassword = '';
  let newPassword = '';
  let confirmPassword = '';
  let saving = false;
  let error = null;
  let fieldErrors = {};
  let success = false;

  function getCsrf() {
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? m[1] : '';
  }

  async function changePassword() {
    saving = true;
    error = null;
    fieldErrors = {};

    if (newPassword !== confirmPassword) {
      fieldErrors.confirmPassword = 'Passwords do not match.';
      saving = false;
      return;
    }
    if (newPassword.length < 8) {
      fieldErrors.newPassword = 'Password must be at least 8 characters.';
      saving = false;
      return;
    }

    try {
      const res = await fetch(apiUrls.changePassword, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrf(),
        },
        body: JSON.stringify({
          old_password: oldPassword,
          new_password: newPassword,
          confirm_password: confirmPassword,
        }),
      });

      saving = false;

      if (res.ok) {
        success = true;
        oldPassword = '';
        newPassword = '';
        confirmPassword = '';
        setTimeout(() => (success = false), 4000);
      } else {
        const d = await res.json();
        if (d.old_password) fieldErrors.oldPassword = Array.isArray(d.old_password) ? d.old_password.join(' ') : d.old_password;
        if (d.new_password) fieldErrors.newPassword = Array.isArray(d.new_password) ? d.new_password.join(' ') : d.new_password;
        if (d.non_field_errors || d.detail) error = d.non_field_errors?.[0] || d.detail;
      }
    } catch (e) {
      saving = false;
      error = 'Network error. Please try again.';
    }
  }
</script>

<div class="space-y-6">

  {#if success}
    <div class="px-4 py-3 rounded-lg bg-green-50 border border-green-200 text-sm text-green-800">
      Password changed successfully.
    </div>
  {/if}

  {#if error}
    <div class="px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-800">
      {error}
    </div>
  {/if}

  <!-- Change Password Form -->
  <div class="bg-white border border-gray-200 rounded-lg p-6">
    <h3 class="text-lg font-medium text-gray-900 mb-6">Change Password</h3>

    <div class="space-y-5">

      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Current Password</label>
        <input
          type="password"
          bind:value={oldPassword}
          class="block w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          placeholder="Enter your current password"
        />
        {#if fieldErrors.oldPassword}
          <p class="mt-1 text-xs text-red-600">{fieldErrors.oldPassword}</p>
        {/if}
      </div>

      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">New Password</label>
        <input
          type="password"
          bind:value={newPassword}
          class="block w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          placeholder="At least 8 characters"
        />
        {#if fieldErrors.newPassword}
          <p class="mt-1 text-xs text-red-600">{fieldErrors.newPassword}</p>
        {/if}
      </div>

      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Confirm New Password</label>
        <input
          type="password"
          bind:value={confirmPassword}
          class="block w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          placeholder="Repeat your new password"
        />
        {#if fieldErrors.confirmPassword}
          <p class="mt-1 text-xs text-red-600">{fieldErrors.confirmPassword}</p>
        {/if}
      </div>

      <!-- Password Requirements -->
      <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 class="text-sm font-medium text-blue-800 mb-2">Password Requirements</h4>
        <ul class="text-sm text-blue-700 space-y-1">
          <li>- At least 8 characters long</li>
          <li>- Cannot be too similar to your personal information</li>
          <li>- Cannot be a commonly used password</li>
          <li>- Cannot be entirely numeric</li>
        </ul>
      </div>

      <!-- Actions -->
      <div class="flex justify-end space-x-3">
        <a
          href="/settings/profile/"
          class="bg-white py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          Cancel
        </a>
        <button
          on:click={changePassword}
          disabled={saving || !oldPassword || !newPassword || !confirmPassword}
          class="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
        >
          {saving ? 'Changing...' : 'Update Password'}
        </button>
      </div>

    </div>
  </div>

  <!-- Security Tips -->
  <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
    <h3 class="text-lg font-medium text-yellow-800 mb-4">Security Tips</h3>
    <ul class="text-sm text-yellow-700 space-y-2">
      <li>Use a strong, unique password that you don't use elsewhere.</li>
      <li>Change your password regularly, especially if you suspect it may be compromised.</li>
      <li>Keep your login credentials secure and don't share them with others.</li>
      <li>Log out of your account when using shared or public computers.</li>
    </ul>
  </div>

</div>
