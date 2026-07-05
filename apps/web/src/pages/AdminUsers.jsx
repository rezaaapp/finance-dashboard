import {
  Check,
  Copy,
  Eye,
  EyeOff,
  Pencil,
  Plus,
  PlayCircle,
  Trash2,
  Lock,
  RefreshCw,
  ShieldCheck,
  UserCog,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  deleteAdminUser,
  getAdminUsers,
  impersonateAdminUser,
  updateAdminUser,
  updateAdminUserRole,
  provisionAdminTestUser,
} from "../api/adminApi";
import { isUatProvisioningAllowed } from "../utils/environment";
import {
  buildCredentialText,
  defaultWorkspaceName,
  generateUatPassword,
} from "../utils/uatCredentials";

const ROLE_OPTIONS = [
  {
    value: "super_admin",
    label: "Super Admin",
    description: "Bisa kelola semua user dan semua konfigurasi.",
  },
  {
    value: "owner",
    label: "Owner",
    description: "User utama workspace dengan akses premium.",
  },
  {
    value: "member",
    label: "Member",
    description: "Pasangan/anggota workspace dengan akses premium terbatas.",
  },
  {
    value: "user",
    label: "User Free Plan",
    description: "Akses dasar dengan fitur premium terkunci.",
  },
];

const CAPABILITY_ROWS = [
  {
    feature: "Melihat Grafik & Analisis Dasar",
    super_admin: { state: "yes", text: "Semua User" },
    owner: { state: "yes", text: "Aktif" },
    member: { state: "yes", text: "Aktif" },
    user: { state: "yes", text: "Aktif" },
  },
  {
    feature: "Advanced Analytics & Decision Alert",
    super_admin: { state: "yes", text: "Semua User" },
    owner: { state: "yes", text: "Aktif (Premium)" },
    member: { state: "yes", text: "Aktif (Premium)" },
    user: { state: "locked", text: "Terkunci (Gated)" },
  },
  {
    feature: "Shortcut Link ke Google Sheets",
    super_admin: { state: "no", text: "Tidak Perlu" },
    owner: { state: "yes", text: "Aktif" },
    member: { state: "yes", text: "Aktif" },
    user: { state: "yes", text: "Aktif" },
  },
  {
    feature: "Ubah Konfigurasi Google Sheet ID",
    super_admin: { state: "yes", text: "Bisa Semua" },
    owner: { state: "yes", text: "Aktif" },
    member: { state: "no", text: "Sembunyi / Read-Only" },
    user: { state: "yes", text: "Aktif" },
  },
  {
    feature: "Mengundang Pasangan ke Workspace",
    super_admin: { state: "no", text: "Tidak Perlu" },
    owner: { state: "yes", text: "Aktif (Premium)" },
    member: { state: "no", text: "Tidak Bisa" },
    user: { state: "locked", text: "Terkunci (Gated)" },
  },
  {
    feature: "Impersonate Akun & Kelola User",
    super_admin: { state: "yes", text: "Bisa Semua" },
    owner: { state: "no", text: "Tidak Bisa" },
    member: { state: "no", text: "Tidak Bisa" },
    user: { state: "no", text: "Tidak Bisa" },
  },
];

const ROLE_LABELS = {
  super_admin: "Super Admin",
  owner: "Owner",
  member: "Member",
  user: "User Free Plan",
};

const formatDate = (value) => {
  if (!value) {
    return "-";
  }

  return new Intl.DateTimeFormat("id-ID", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
};

const CapabilityIcon = ({ state }) => {
  if (state === "locked") {
    return <Lock size={16} className="text-[var(--color-alert-text)]" />;
  }

  if (state === "yes") {
    return <Check size={16} className="text-[var(--color-accent)]" />;
  }

  return <X size={16} className="text-[var(--color-danger)]" />;
};

const EMPTY_FORM = {
  email: "",
  name: "",
  role: "owner",
  password: "",
  workspaceName: "",
};

const AdminUsers = ({ onImpersonate, onUnauthorized, systemInfoState }) => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [savingUserId, setSavingUserId] = useState("");
  const [deletingUserId, setDeletingUserId] = useState("");
  const [formMode, setFormMode] = useState("");
  const [editingUserId, setEditingUserId] = useState("");
  const [formData, setFormData] = useState(EMPTY_FORM);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [createdCredential, setCreatedCredential] = useState(null);
  const [copyNotice, setCopyNotice] = useState("");
  const canProvisionTestUser = isUatProvisioningAllowed(systemInfoState?.data);

  const totalByRole = useMemo(() => (
    ROLE_OPTIONS.reduce((accumulator, role) => {
      accumulator[role.value] = users.filter((user) => (
        user.role === role.value
      )).length;

      return accumulator;
    }, {})
  ), [users]);

  const loadUsers = useCallback(async () => {
    try {
      setLoading(true);
      setError("");
      const data = await getAdminUsers();

      setUsers(data.users || []);
    } catch (err) {
      console.error("Failed to load admin users.");

      if (err?.response?.status === 401) {
        onUnauthorized();
        return;
      }

      if (err?.response?.status === 403) {
        setError("Hanya super admin yang bisa membuka halaman ini.");
        return;
      }

      setError("Tidak bisa memuat daftar user.");
    } finally {
      setLoading(false);
    }
  }, [onUnauthorized]);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  const openCreateForm = () => {
    if (!canProvisionTestUser) return;
    setFormMode("create");
    setEditingUserId("");
    setFormData(EMPTY_FORM);
    setNotice("");
    setError("");
    setShowPassword(false);
  };

  const openEditForm = (user) => {
    setFormMode("edit");
    setEditingUserId(user.id);
    setFormData({
      email: user.email,
      name: user.name,
      role: user.role,
    });
    setNotice("");
    setError("");
  };

  const closeForm = () => {
    setFormMode("");
    setEditingUserId("");
    setFormData(EMPTY_FORM);
  };

  const handleFormChange = (field, value) => {
    setFormData((currentFormData) => ({
      ...currentFormData,
      [field]: value,
      ...(field === "name" && (
        !currentFormData.workspaceName
        || currentFormData.workspaceName === defaultWorkspaceName(currentFormData.name)
      ) ? { workspaceName: defaultWorkspaceName(value) } : {}),
    }));
  };

  const handleCopyCredential = async () => {
    if (!createdCredential) return;
    try {
      await navigator.clipboard.writeText(buildCredentialText(createdCredential));
      setCopyNotice("Credential berhasil disalin.");
    } catch {
      setCopyNotice("Credential belum dapat disalin. Salin detail secara manual.");
    }
  };

  const handleSaveUser = async (event) => {
    event.preventDefault();

    const payload = {
      email: formData.email.trim().toLowerCase(),
      name: formData.name.trim(),
      role: formData.role,
    };

    if (formMode === "create") {
      payload.password = formData.password;
      payload.workspace_name = formData.workspaceName.trim();
      if (!payload.password || !payload.workspace_name) {
        setError("Password dan Workspace Name wajib diisi.");
        return;
      }
    }

    try {
      setSavingUserId(editingUserId || "new");
      setError("");
      setNotice("");

      if (formMode === "create") {
        const data = await provisionAdminTestUser(payload);

        setUsers((currentUsers) => [data.user, ...currentUsers]);
        setCreatedCredential({
          url: window.location.origin,
          email: data.email,
          password: formData.password,
          workspace: data.workspace_name,
        });
        setCopyNotice("");
        setNotice(`User ${data.user.email} berhasil dibuat.`);
      } else {
        const data = await updateAdminUser(editingUserId, payload);

        setUsers((currentUsers) => (
          currentUsers.map((user) => (
            user.id === data.user.id ? data.user : user
          ))
        ));
        setNotice(`User ${data.user.email} berhasil diubah.`);
        window.alert(`User ${data.user.email} berhasil diubah.`);
      }

      closeForm();
    } catch (err) {
      console.error("Failed to save admin user.");

      if (err?.response?.status === 401) {
        onUnauthorized();
        return;
      }

      if (err?.response?.status === 403) {
        setError(err?.response?.data?.detail || "Sesi Anda tidak punya akses provisioning.");
        return;
      }

      if (err?.response?.status === 409) {
        setError("Email tersebut sudah terdaftar.");
        window.alert("Email tersebut sudah terdaftar.");
        return;
      }

      const message =
        err?.response?.data?.detail
        || "Tidak bisa menyimpan user.";

      setError(message);
      window.alert(message);
    } finally {
      setSavingUserId("");
    }
  };

  const handleRoleChange = async (userId, role) => {
    try {
      setSavingUserId(userId);
      setError("");
      setNotice("");

      const data = await updateAdminUserRole(userId, role);
      const updatedUser = data.user;

      setUsers((currentUsers) => (
        currentUsers.map((user) => (
          user.id === updatedUser.id ? updatedUser : user
        ))
      ));
      setNotice(`Role ${updatedUser.email} diubah menjadi ${ROLE_LABELS[role]}.`);
    } catch (err) {
      console.error("Failed to update admin user role.");

      if (err?.response?.status === 401) {
        onUnauthorized();
        return;
      }

      if (err?.response?.status === 403) {
        setError("Sesi Anda tidak punya akses super admin.");
        return;
      }

      setError("Tidak bisa mengubah role user.");
    } finally {
      setSavingUserId("");
    }
  };

  const handleDeleteUser = async (user) => {
    const shouldDelete = window.confirm(
      `Delete user ${user.email}? Data workspace membership dan token user juga akan ikut terhapus.`
    );

    if (!shouldDelete) {
      return;
    }

    try {
      setDeletingUserId(user.id);
      setError("");
      setNotice("");

      await deleteAdminUser(user.id);
      setUsers((currentUsers) => (
        currentUsers.filter((currentUser) => currentUser.id !== user.id)
      ));
      setNotice(`User ${user.email} berhasil dihapus.`);
    } catch (err) {
      console.error("Failed to delete admin user.");

      if (err?.response?.status === 401) {
        onUnauthorized();
        return;
      }

      if (err?.response?.status === 403) {
        setError("Sesi Anda tidak punya akses super admin.");
        return;
      }

      setError("Tidak bisa menghapus user.");
    } finally {
      setDeletingUserId("");
    }
  };

  const handleImpersonateUser = async (user) => {
    try {
      setSavingUserId(user.id);
      setError("");
      setNotice("");

      const data = await impersonateAdminUser(user.id);

      onImpersonate({
        token: data.token,
        username: data.user.name,
        email: data.user.email,
        userId: data.user.id,
        role: data.user.role,
        provider: "impersonation",
      });
    } catch (err) {
      console.error("Failed to impersonate admin user.");

      if (err?.response?.status === 401) {
        onUnauthorized();
        return;
      }

      setError("Tidak bisa masuk sebagai user ini.");
    } finally {
      setSavingUserId("");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="inline-flex items-center gap-2 rounded-lg bg-[var(--color-accent-bg)] px-3 py-1 text-sm font-bold text-accent">
            <ShieldCheck size={16} />
            Super Admin
          </div>

          <h2 className="mt-3 text-2xl font-bold text-main sm:text-3xl">
            User & Role Management
          </h2>

          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
            Atur role akun yang login ke dashboard. Role ini menjadi dasar
            gating fitur MVP sebelum nanti diturunkan ke permission yang lebih
            granular.
          </p>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row">
          {canProvisionTestUser && (
            <button
              type="button"
              onClick={openCreateForm}
              className="primary-button h-11 rounded-lg px-4 font-semibold"
            >
              <Plus size={18} />
              Provision UAT User
            </button>
          )}

          <button
            type="button"
            onClick={loadUsers}
            className="secondary-button h-11 rounded-lg px-4 font-semibold"
            disabled={loading}
          >
            <RefreshCw size={18} className={loading ? "animate-spin" : ""} />
            Refresh
          </button>
        </div>
      </div>

      {!canProvisionTestUser && (
        <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] px-4 py-3 text-sm text-muted">
          Provisioning user tester hanya tersedia di LOCAL DEV, DEV, atau UAT.
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {ROLE_OPTIONS.map((role) => (
          <div key={role.value} className="panel rounded-lg p-4">
            <p className="text-sm font-bold text-main">
              {role.label}
            </p>
            <p className="mt-1 text-3xl font-bold text-accent">
              {totalByRole[role.value] || 0}
            </p>
            <p className="mt-2 text-sm leading-6 text-muted">
              {role.description}
            </p>
          </div>
        ))}
      </div>

      {notice && (
        <div className="rounded-lg border border-[var(--color-accent)] bg-[var(--color-accent-bg)] px-4 py-3 text-sm font-semibold text-accent">
          {notice}
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-[var(--color-danger)] bg-[var(--color-danger-bg)] px-4 py-3 text-sm font-semibold text-[var(--color-danger)]">
          {error}
        </div>
      )}

      {formMode && (
        <section className="panel rounded-lg p-4 shadow-lg">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h3 className="text-lg font-bold text-main">
              {formMode === "create" ? "Provision UAT User" : "Modify User"}
            </h3>

            <button
              type="button"
              onClick={closeForm}
              className="theme-toggle h-10 rounded-lg px-3 text-sm font-semibold"
            >
              Cancel
            </button>
          </div>

          <form
            onSubmit={handleSaveUser}
            className="grid grid-cols-1 gap-4 lg:grid-cols-2"
          >
            <label className="block">
              <span className="mb-2 block text-sm font-bold text-soft">
                Email
              </span>
              <input
                type="email"
                value={formData.email}
                onChange={(event) => handleFormChange("email", event.target.value)}
                className="form-control w-full rounded-lg px-3 py-2"
                placeholder="gelashijau@gmail.com"
                required
              />
            </label>

            {formMode === "create" && (
              <label className="block">
                <span className="mb-2 block text-sm font-bold text-soft">Workspace Name</span>
                <input
                  value={formData.workspaceName}
                  onChange={(event) => handleFormChange("workspaceName", event.target.value)}
                  className="form-control w-full rounded-lg px-3 py-2"
                  placeholder="Andi's Household"
                  required
                />
              </label>
            )}

            {formMode === "create" && (
              <label className="block">
                <span className="mb-2 block text-sm font-bold text-soft">Password</span>
                <div className="flex gap-2">
                  <div className="form-control flex min-w-0 flex-1 items-center rounded-lg pr-2">
                    <input
                      type={showPassword ? "text" : "password"}
                      value={formData.password}
                      onChange={(event) => handleFormChange("password", event.target.value)}
                      className="min-w-0 flex-1 bg-transparent px-3 py-2 outline-none"
                      autoComplete="new-password"
                      minLength={10}
                      required
                    />
                    <button type="button" onClick={() => setShowPassword((value) => !value)} className="rounded-lg p-2 text-muted" aria-label={showPassword ? "Sembunyikan password" : "Tampilkan password"}>
                      {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                    </button>
                  </div>
                  <button type="button" onClick={() => handleFormChange("password", generateUatPassword())} className="secondary-button rounded-lg px-3 py-2 text-sm font-semibold">Generate</button>
                </div>
                <span className="mt-2 block text-xs text-muted">Minimal 10 karakter dengan huruf besar, huruf kecil, angka, dan simbol.</span>
              </label>
            )}

            <label className="block">
              <span className="mb-2 block text-sm font-bold text-soft">
                Name
              </span>
              <input
                value={formData.name}
                onChange={(event) => handleFormChange("name", event.target.value)}
                className="form-control w-full rounded-lg px-3 py-2"
                placeholder="gelas-test"
                required
              />
            </label>

            <label className="block">
              <span className="mb-2 block text-sm font-bold text-soft">
                Role
              </span>
              <select
                value={formData.role}
                onChange={(event) => handleFormChange("role", event.target.value)}
                className="form-control w-full rounded-lg px-3 py-2"
              >
                {ROLE_OPTIONS.filter((role) => (
                  formMode !== "create" || role.value !== "super_admin"
                )).map((role) => (
                  <option key={role.value} value={role.value}>
                    {role.label}
                  </option>
                ))}
              </select>
            </label>

            <div className="flex items-end lg:col-span-2 lg:justify-end">
              <button
                type="submit"
                className="primary-button h-11 w-full rounded-lg px-4 font-semibold lg:w-auto"
                disabled={
                  savingUserId === "new"
                  || (Boolean(editingUserId) && savingUserId === editingUserId)
                }
              >
                {formMode === "create" ? "Create User" : "Save"}
              </button>
            </div>
          </form>
        </section>
      )}

      <section className="panel rounded-lg p-4 shadow-lg">
        <div className="mb-4 flex items-center gap-2">
          <UserCog size={20} className="text-accent" />
          <h3 className="text-lg font-bold text-main">
            Daftar User
          </h3>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-[760px] w-full border-collapse text-left">
            <thead>
              <tr className="table-header">
                <th className="px-4 py-3 text-sm font-bold">User</th>
                <th className="px-4 py-3 text-sm font-bold">Role</th>
                <th className="px-4 py-3 text-sm font-bold">Dibuat</th>
                <th className="px-4 py-3 text-sm font-bold">Terakhir Update</th>
                <th className="px-4 py-3 text-sm font-bold">Action</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="5" className="px-4 py-8 text-center text-muted">
                    Memuat user...
                  </td>
                </tr>
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan="5" className="px-4 py-8 text-center text-muted">
                    Belum ada user yang login.
                  </td>
                </tr>
              ) : users.map((user) => (
                <tr key={user.id} className="table-row table-border">
                  <td className="px-4 py-4">
                    <div className="font-bold text-main">{user.name}</div>
                    <div className="mt-1 text-sm text-muted">{user.email}</div>
                  </td>
                  <td className="px-4 py-4">
                    <select
                      value={user.role}
                      onChange={(event) => handleRoleChange(
                        user.id,
                        event.target.value
                      )}
                      disabled={savingUserId === user.id}
                      className="form-control min-w-48 rounded-lg px-3 py-2 text-sm font-semibold"
                    >
                      {ROLE_OPTIONS.map((role) => (
                        <option key={role.value} value={role.value}>
                          {role.label}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="px-4 py-4 text-sm text-muted">
                    {formatDate(user.created_at)}
                  </td>
                  <td className="px-4 py-4 text-sm text-muted">
                    {savingUserId === user.id
                      ? "Menyimpan..."
                      : formatDate(user.updated_at)
                    }
                  </td>
                  <td className="px-4 py-4">
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => openEditForm(user)}
                        className="theme-toggle h-10 w-10 rounded-lg p-0"
                        aria-label={`Modify ${user.email}`}
                        title="Modify User"
                      >
                        <Pencil size={16} />
                      </button>

                      <button
                        type="button"
                        onClick={() => handleImpersonateUser(user)}
                        disabled={savingUserId === user.id}
                        className="theme-toggle h-10 w-10 rounded-lg p-0"
                        aria-label={`Test access as ${user.email}`}
                        title="Test Access"
                      >
                        <PlayCircle size={16} />
                      </button>

                      <button
                        type="button"
                        onClick={() => handleDeleteUser(user)}
                        disabled={deletingUserId === user.id}
                        className="theme-toggle h-10 w-10 rounded-lg p-0 text-[var(--color-danger)]"
                        aria-label={`Delete ${user.email}`}
                        title="Delete User"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel rounded-lg p-4 shadow-lg">
        <h3 className="text-lg font-bold text-main">
          Matriks Akses MVP
        </h3>

        <div className="mt-4 overflow-x-auto">
          <table className="min-w-[920px] w-full border-collapse text-left">
            <thead>
              <tr className="table-header">
                <th className="px-4 py-3 text-sm font-bold">
                  Komponen / Fitur di Dashboard
                </th>
                <th className="px-4 py-3 text-sm font-bold">Super Admin</th>
                <th className="px-4 py-3 text-sm font-bold">Owner</th>
                <th className="px-4 py-3 text-sm font-bold">Member</th>
                <th className="px-4 py-3 text-sm font-bold">User Free Plan</th>
              </tr>
            </thead>
            <tbody>
              {CAPABILITY_ROWS.map((row) => (
                <tr key={row.feature} className="table-row table-border">
                  <td className="px-4 py-3 font-semibold text-main">
                    {row.feature}
                  </td>
                  {["super_admin", "owner", "member", "user"].map((role) => (
                    <td key={role} className="px-4 py-3">
                      <div className="flex items-center gap-2 text-sm font-semibold">
                        <CapabilityIcon state={row[role].state} />
                        <span>{row[role].text}</span>
                      </div>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {createdCredential && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 p-4" role="presentation">
          <div className="w-full max-w-lg rounded-3xl bg-white p-6 shadow-xl dark:bg-[var(--color-panel)]" role="dialog" aria-modal="true" aria-labelledby="credential-title">
            <h2 id="credential-title" className="text-xl font-bold text-main">User berhasil dibuat.</h2>
            <p className="mt-2 text-sm leading-6 text-muted">Password hanya ditampilkan sekarang. Simpan credential sebelum menutup panel ini.</p>
            <dl className="mt-5 grid gap-3 rounded-2xl border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-4 text-sm">
              <div><dt className="font-bold text-muted">URL</dt><dd className="mt-1 break-all text-main">{createdCredential.url}</dd></div>
              <div><dt className="font-bold text-muted">Email</dt><dd className="mt-1 break-all text-main">{createdCredential.email}</dd></div>
              <div><dt className="font-bold text-muted">Password</dt><dd className="mt-1 break-all font-mono text-main">{createdCredential.password}</dd></div>
              <div><dt className="font-bold text-muted">Workspace</dt><dd className="mt-1 text-main">{createdCredential.workspace}</dd></div>
            </dl>
            <p className="mt-4 text-sm leading-6 text-muted">Silakan Login, buka Settings, Connect Google, tambahkan URL spreadsheet, Test Connection, Save Source, lalu Sync Now. Setelah itu buka Dashboard.</p>
            {copyNotice && <p className="mt-3 text-sm font-semibold text-accent" role="status">{copyNotice}</p>}
            <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
              <button type="button" onClick={() => { setCreatedCredential(null); setCopyNotice(""); }} className="secondary-button rounded-xl px-4 py-2 font-bold">Selesai</button>
              <button type="button" onClick={handleCopyCredential} className="primary-button rounded-xl px-4 py-2 font-bold"><Copy size={17} />Copy Credential</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminUsers;
