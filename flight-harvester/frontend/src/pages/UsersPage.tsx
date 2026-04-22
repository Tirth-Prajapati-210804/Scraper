import { type FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  createUser,
  listUsers,
  updateUser,
  type UserCreatePayload,
  type UserRecord,
  type UserUpdatePayload,
} from "../api/users";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Modal } from "../components/ui/Modal";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { usePageTitle } from "../utils/usePageTitle";

// ── User form modal ───────────────────────────────────────────────────────────

interface UserFormModalProps {
  open: boolean;
  onClose: () => void;
  initial: UserRecord | null;
  onSaved: () => void;
}

function UserFormModal({ open, onClose, initial, onSaved }: UserFormModalProps) {
  const { showToast } = useToast();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("viewer");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initial) {
      setFullName(initial.full_name);
      setEmail(initial.email);
      setRole(initial.role);
      setPassword("");
    } else {
      setFullName("");
      setEmail("");
      setPassword("");
      setRole("viewer");
    }
    setError(null);
  }, [initial, open]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      if (initial) {
        const payload: UserUpdatePayload = { full_name: fullName, email, role };
        if (password) payload.password = password;
        await updateUser(initial.id, payload);
        showToast("User updated", "success");
      } else {
        const payload: UserCreatePayload = { full_name: fullName, email, password, role };
        await createUser(payload);
        showToast("User created", "success");
      }
      onSaved();
      onClose();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Failed to save user.";
      setError(msg);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={initial ? "Edit User" : "Add User"}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="field-label">Full Name</label>
          <input
            className="field-input"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            required
            autoFocus
          />
        </div>
        <div>
          <label className="field-label">Email</label>
          <input
            type="email"
            className="field-input"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
        <div>
          <label className="field-label">
            Password{initial && <span className="ml-1 text-slate-400">(leave blank to keep current)</span>}
          </label>
          <input
            type="password"
            className="field-input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required={!initial}
            minLength={8}
            placeholder={initial ? "••••••••" : ""}
          />
        </div>
        <div>
          <label className="field-label">Role</label>
          <select
            className="field-input"
            value={role}
            onChange={(e) => setRole(e.target.value)}
          >
            <option value="viewer">Viewer</option>
            <option value="admin">Admin</option>
          </select>
        </div>

        {error && (
          <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>
        )}

        <div className="flex justify-end gap-2 pt-1">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" loading={saving}>
            {initial ? "Save changes" : "Create user"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export function UsersPage() {
  usePageTitle("User Management");
  const { user: currentUser } = useAuth();
  const navigate = useNavigate();
  const { showToast } = useToast();

  const [users, setUsers] = useState<UserRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<UserRecord | null>(null);

  // Guard: non-admins redirected to dashboard
  useEffect(() => {
    if (currentUser && currentUser.role !== "admin") {
      navigate("/");
    }
  }, [currentUser, navigate]);

  async function load() {
    setLoading(true);
    try {
      setUsers(await listUsers());
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []); // load once on mount

  function openAdd() {
    setEditing(null);
    setModalOpen(true);
  }

  function openEdit(u: UserRecord) {
    setEditing(u);
    setModalOpen(true);
  }

  async function handleToggleActive(u: UserRecord) {
    const action = u.is_active ? "deactivate" : "activate";
    if (!window.confirm(`${u.is_active ? "Deactivate" : "Activate"} user "${u.full_name}"?`)) return;
    try {
      await updateUser(u.id, { is_active: !u.is_active });
      showToast(`User ${action}d`, "success");
      load();
    } catch {
      showToast(`Failed to ${action} user`, "error");
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-slate-900">User Management</h1>
        <Button variant="primary" onClick={openAdd}>
          Add User
        </Button>
      </div>

      <Card>
        {loading ? (
          <p className="py-8 text-center text-sm text-slate-400">Loading…</p>
        ) : users.length === 0 ? (
          <p className="py-8 text-center text-sm text-slate-400">No users found.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs uppercase tracking-wider text-slate-500">
                  <th className="px-3 py-2.5">Full Name</th>
                  <th className="px-3 py-2.5">Email</th>
                  <th className="px-3 py-2.5">Role</th>
                  <th className="px-3 py-2.5">Status</th>
                  <th className="px-3 py-2.5">Created</th>
                  <th className="px-3 py-2.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u, i) => (
                  <tr key={u.id} className={`${i % 2 !== 0 ? "bg-slate-50/50" : ""} ${!u.is_active ? "opacity-60" : ""}`}>
                    <td className="px-3 py-2 font-medium text-slate-800">{u.full_name}</td>
                    <td className="px-3 py-2 text-slate-600">{u.email}</td>
                    <td className="px-3 py-2">
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                          u.role === "admin"
                            ? "bg-brand-100 text-brand-700"
                            : "bg-slate-100 text-slate-600"
                        }`}
                      >
                        {u.role}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                          u.is_active
                            ? "bg-green-100 text-green-700"
                            : "bg-slate-100 text-slate-500"
                        }`}
                      >
                        {u.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-slate-400">
                      {new Date(u.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-3 py-2 text-right">
                      <div className="flex justify-end gap-2">
                        <button
                          onClick={() => openEdit(u)}
                          className="rounded px-2 py-1 text-xs text-brand-600 hover:bg-brand-50"
                        >
                          Edit
                        </button>
                        {u.id !== currentUser?.id && (
                          <button
                            onClick={() => handleToggleActive(u)}
                            className={`rounded px-2 py-1 text-xs ${
                              u.is_active
                                ? "text-amber-600 hover:bg-amber-50"
                                : "text-green-600 hover:bg-green-50"
                            }`}
                          >
                            {u.is_active ? "Deactivate" : "Activate"}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <UserFormModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        initial={editing}
        onSaved={load}
      />
    </div>
  );
}
