"use client";

import React, { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { Sidebar } from "@/components/Sidebar";
import { Users, UserPlus, Shield, Check, X, Trash2, RefreshCw, ShieldAlert } from "lucide-react";
import { toast } from "sonner";

interface UserItem {
  id: string;
  email: string;
  role: "admin" | "analyst" | "viewer";
  is_active: boolean;
  created_at?: string;
}

export default function AdminUsersPage() {
  const { data: session, status: authStatus } = useSession();
  const [users, setUsers] = useState<UserItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newEmail, setNewEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newRole, setNewRole] = useState<"admin" | "analyst" | "viewer">("viewer");

  const isAdmin = session?.user?.role === "admin";

  const fetchUsers = async () => {
    if (!isAdmin) return;
    setLoading(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiUrl}/api/v1/admin/users/`, {
        headers: { Authorization: `Bearer ${session?.accessToken}` },
      });

      if (res.ok) {
        const data = await res.json();
        setUsers(data);
      } else {
        toast.error("Kullanıcı listesi alınamadı.");
      }
    } catch (err) {
      toast.error("Sunucu bağlantı hatası.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (authStatus === "authenticated" && isAdmin) {
      fetchUsers();
    } else if (authStatus !== "loading" && !isAdmin) {
      setLoading(false);
    }
  }, [authStatus, session, isAdmin]);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiUrl}/api/v1/admin/users/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.accessToken}`,
        },
        body: JSON.stringify({
          email: newEmail,
          password: newPassword,
          role: newRole,
        }),
      });

      if (res.ok) {
        toast.success("Kullanıcı başarıyla oluşturuldu.");
        setShowAddModal(false);
        setNewEmail("");
        setNewPassword("");
        fetchUsers();
      } else {
        const err = await res.json();
        toast.error(`Kullanıcı eklenemedi: ${err.detail || "Bilinmeyen hata"}`);
      }
    } catch (err) {
      toast.error("İstek sırasında hata oluştu.");
    }
  };

  const handleRoleChange = async (userId: string, role: string) => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiUrl}/api/v1/admin/users/${userId}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.accessToken}`,
        },
        body: JSON.stringify({ role }),
      });

      if (res.ok) {
        toast.success("Kullanıcı rolü güncellendi.");
        fetchUsers();
      } else {
        const err = await res.json();
        toast.error(err.detail || "Rol güncellenemedi.");
      }
    } catch (err) {
      toast.error("Rol güncellenirken hata oluştu.");
    }
  };

  const handleToggleActive = async (userId: string, currentActive: boolean) => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiUrl}/api/v1/admin/users/${userId}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.accessToken}`,
        },
        body: JSON.stringify({ is_active: !currentActive }),
      });

      if (res.ok) {
        toast.success("Kullanıcı durumu güncellendi.");
        fetchUsers();
      } else {
        const err = await res.json();
        toast.error(err.detail || "Durum güncellenemedi.");
      }
    } catch (err) {
      toast.error("Durum güncellenirken hata oluştu.");
    }
  };

  const handleDeleteUser = async (userId: string) => {
    if (!confirm("Bu kullanıcıyı silmek istediğinize emin misiniz?")) return;
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiUrl}/api/v1/admin/users/${userId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${session?.accessToken}` },
      });

      if (res.ok) {
        toast.success("Kullanıcı silindi.");
        fetchUsers();
      } else {
        const err = await res.json();
        toast.error(err.detail || "Kullanıcı silinemedi.");
      }
    } catch (err) {
      toast.error("Silme işleminde hata oluştu.");
    }
  };

  if (!isAdmin && authStatus !== "loading") {
    return (
      <div className="min-h-screen flex bg-zinc-950 text-zinc-100">
        <Sidebar />
        <main className="flex-1 p-12 flex flex-col items-center justify-center text-center space-y-4">
          <ShieldAlert className="w-16 h-16 text-amber-500 animate-bounce" />
          <h2 className="text-xl font-bold text-zinc-100">Yetkisiz Erişim (403 Forbidden)</h2>
          <p className="text-xs text-zinc-400 max-w-md">
            Kullanıcı yönetimi paneline sadece <b className="text-amber-400">ADMIN</b> rolündeki yöneticiler erişebilir. Lütfen yetkili bir hesapla oturum açınız.
          </p>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex bg-zinc-950 text-zinc-100">
      <Sidebar />

      <main className="flex-1 p-8 overflow-y-auto max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-zinc-800">
          <div>
            <h1 className="text-xl font-bold text-zinc-100 flex items-center gap-2">
              <Users className="w-5 h-5 text-amber-400" />
              Kullanıcı Yönetimi (RBAC)
            </h1>
            <p className="text-xs text-zinc-400 mt-1">
              Sistemdeki kullanıcı hesaplarını, erişim rollerini (Admin, Analist, İzleyici) ve aktiflik durumlarını yönetin.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowAddModal(true)}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-lg shadow-emerald-950/40 transition-all cursor-pointer"
            >
              <UserPlus className="w-4 h-4" />
              <span>Yeni Kullanıcı Ekle</span>
            </button>
            <button
              onClick={fetchUsers}
              className="p-2 rounded-xl bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 transition-all cursor-pointer"
              title="Yenile"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-emerald-400" : ""}`} />
            </button>
          </div>
        </div>

        {/* Users Table */}
        <div className="bg-zinc-900/60 border border-zinc-800/80 rounded-2xl overflow-hidden shadow-xl backdrop-blur-md">
          {loading ? (
            <div className="p-12 text-center text-xs text-zinc-400 flex items-center justify-center gap-2">
              <RefreshCw className="w-4 h-4 animate-spin text-amber-400" />
              Kullanıcılar yükleniyor...
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-zinc-950/80 border-b border-zinc-800 text-[11px] font-mono text-zinc-400 uppercase tracking-wider">
                  <tr>
                    <th className="py-3.5 px-4">E-posta</th>
                    <th className="py-3.5 px-4">Erişim Rolü</th>
                    <th className="py-3.5 px-4">Durum</th>
                    <th className="py-3.5 px-4">Kayıt Tarihi</th>
                    <th className="py-3.5 px-4 text-right">İşlemler</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800/60 font-medium">
                  {users.map((user) => {
                    const isSelf = user.id === session?.user?.id;
                    return (
                      <tr key={user.id} className="hover:bg-zinc-800/30 transition-colors">
                        <td className="py-3.5 px-4 text-zinc-100 flex items-center gap-2">
                          <div className="w-7 h-7 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center text-[10px] font-bold text-zinc-300">
                            {user.email.substring(0, 2).toUpperCase()}
                          </div>
                          <span>{user.email}</span>
                          {isSelf && (
                            <span className="text-[10px] bg-amber-500/20 text-amber-400 px-2 py-0.5 rounded-full font-mono font-bold">
                              Sen
                            </span>
                          )}
                        </td>
                        <td className="py-3.5 px-4">
                          <select
                            value={user.role}
                            onChange={(e) => handleRoleChange(user.id, e.target.value)}
                            disabled={isSelf}
                            className={`bg-zinc-950 border rounded-lg px-2.5 py-1 text-xs font-mono font-bold cursor-pointer transition-colors ${
                              user.role === "admin"
                                ? "text-red-400 border-red-500/40 bg-red-500/10"
                                : user.role === "analyst"
                                ? "text-blue-400 border-blue-500/40 bg-blue-500/10"
                                : "text-zinc-400 border-zinc-700 bg-zinc-900"
                            } disabled:opacity-60 disabled:cursor-not-allowed`}
                          >
                            <option value="admin">ADMIN</option>
                            <option value="analyst">ANALYST</option>
                            <option value="viewer">VIEWER</option>
                          </select>
                        </td>
                        <td className="py-3.5 px-4">
                          <button
                            onClick={() => handleToggleActive(user.id, user.is_active)}
                            disabled={isSelf}
                            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold transition-all cursor-pointer ${
                              user.is_active
                                ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/25"
                                : "bg-zinc-800 text-zinc-500 border border-zinc-700 hover:bg-zinc-700/50"
                            } disabled:opacity-60 disabled:cursor-not-allowed`}
                          >
                            {user.is_active ? <Check className="w-3 h-3" /> : <X className="w-3 h-3" />}
                            {user.is_active ? "Aktif" : "Pasif"}
                          </button>
                        </td>
                        <td className="py-3.5 px-4 text-zinc-400 text-[11px]">
                          {user.created_at ? new Date(user.created_at).toLocaleDateString("tr-TR") : "-"}
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          <button
                            onClick={() => handleDeleteUser(user.id)}
                            disabled={isSelf}
                            className="p-1.5 rounded-lg bg-zinc-800 hover:bg-red-500/20 text-zinc-400 hover:text-red-400 border border-zinc-700 hover:border-red-500/30 transition-all cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
                            title={isSelf ? "Kendinizi silemezsiniz" : "Kullanıcıyı Sil"}
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Create User Modal */}
        {showAddModal && (
          <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 w-full max-w-md space-y-4 shadow-2xl">
              <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                <h3 className="font-bold text-sm text-zinc-100 flex items-center gap-2">
                  <UserPlus className="w-4 h-4 text-emerald-400" />
                  Yeni Kullanıcı Tanımla
                </h3>
                <button
                  onClick={() => setShowAddModal(false)}
                  className="text-zinc-500 hover:text-zinc-300"
                >
                  ✕
                </button>
              </div>

              <form onSubmit={handleCreateUser} className="space-y-3">
                <div>
                  <label className="text-xs text-zinc-300">E-posta</label>
                  <input
                    type="email"
                    required
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                    placeholder="kullanici@damage.org"
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-xs text-zinc-100 mt-1 focus:outline-none focus:border-emerald-500"
                  />
                </div>

                <div>
                  <label className="text-xs text-zinc-300">Şifre</label>
                  <input
                    type="password"
                    required
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="En az 6 karakter"
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-xs text-zinc-100 mt-1 focus:outline-none focus:border-emerald-500"
                  />
                </div>

                <div>
                  <label className="text-xs text-zinc-300">Rol</label>
                  <select
                    value={newRole}
                    onChange={(e) => setNewRole(e.target.value as any)}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-xs text-zinc-100 mt-1 focus:outline-none focus:border-emerald-500"
                  >
                    <option value="viewer">İzleyici (Viewer)</option>
                    <option value="analyst">Tarım Analisti (Analyst)</option>
                    <option value="admin">Sistem Yöneticisi (Admin)</option>
                  </select>
                </div>

                <div className="flex items-center justify-end gap-2 pt-3">
                  <button
                    type="button"
                    onClick={() => setShowAddModal(false)}
                    className="px-4 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-xs font-semibold text-zinc-300 cursor-pointer"
                  >
                    İptal
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white cursor-pointer shadow-lg shadow-emerald-950/40"
                  >
                    Kaydet
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
