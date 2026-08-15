"use client";

import React, { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { Sidebar } from "@/components/Sidebar";
import { History, Calendar, CheckCircle2, Clock, XCircle, FileText, ArrowUpRight, Search, RefreshCw } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";

interface JobItem {
  id: string;
  aoi_id: string;
  aoi_name?: string;
  status: string;
  event_date: string;
  created_at: string;
  user_email?: string;
}

export default function JobsPage() {
  const { data: session, status: authStatus } = useSession();
  const [jobs, setJobs] = useState<JobItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const token = session?.accessToken;
      const isAdmin = session?.user?.role === "admin";
      const endpoint = isAdmin ? "/api/v1/admin/jobs" : "/api/v1/jobs/";
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

      const res = await fetch(`${apiUrl}${endpoint}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });

      if (res.ok) {
        const data = await res.json();
        setJobs(data);
      } else {
        toast.error("Geçmiş analizler yüklenirken hata oluştu.");
      }
    } catch (err) {
      console.error(err);
      toast.error("Sunucuya bağlanılamadı.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (authStatus !== "loading") {
      fetchJobs();
    }
  }, [authStatus, session]);

  const filteredJobs = jobs.filter((j) =>
    (j.id || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
    (j.aoi_name || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
    (j.status || "").toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "done":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="w-3.5 h-3.5" /> Tamamlandı
          </span>
        );
      case "failed":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-red-500/15 text-red-600 dark:text-red-400 border border-red-500/30">
            <XCircle className="w-3.5 h-3.5" /> Başarısız
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30 animate-pulse">
            <Clock className="w-3.5 h-3.5" /> İşleniyor
          </span>
        );
    }
  };

  return (
    <div className="min-h-screen flex bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 transition-colors duration-200">
      <Sidebar />

      <main className="flex-1 p-8 overflow-y-auto max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-zinc-200 dark:border-zinc-800">
          <div>
            <h1 className="text-xl font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
              <History className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
              Analiz Geçmişi ve Arşiv
            </h1>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
              Daha önce gerçekleştirilen tarımsal hasar tespiti kayıtları ve rapor çıktıları.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="w-4 h-4 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="ID, Alan veya Durum ara..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="bg-white dark:bg-zinc-900 border border-zinc-300 dark:border-zinc-800 rounded-xl pl-9 pr-4 py-2 text-xs text-zinc-900 dark:text-zinc-100 focus:outline-none focus:border-emerald-500 transition-colors w-64 shadow-sm"
              />
            </div>
            <button
              onClick={fetchJobs}
              className="p-2 rounded-xl bg-white dark:bg-zinc-900 hover:bg-zinc-100 dark:hover:bg-zinc-800 border border-zinc-300 dark:border-zinc-800 text-zinc-700 dark:text-zinc-300 transition-all cursor-pointer shadow-sm"
              title="Yenile"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-emerald-500" : ""}`} />
            </button>
          </div>
        </div>

        {/* Jobs Table */}
        <div className="bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800/80 rounded-2xl overflow-hidden shadow-xl backdrop-blur-md transition-colors">
          {loading ? (
            <div className="p-12 text-center text-xs text-zinc-500 dark:text-zinc-400 flex items-center justify-center gap-2">
              <RefreshCw className="w-4 h-4 animate-spin text-emerald-500" />
              Kayıtlar yükleniyor...
            </div>
          ) : filteredJobs.length === 0 ? (
            <div className="p-12 text-center space-y-3">
              <History className="w-10 h-10 text-zinc-400 dark:text-zinc-600 mx-auto" />
              <p className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Henüz kaydedilmiş analiz bulunamadı.</p>
              <p className="text-xs text-zinc-500">Harita üzerinden yeni bir alan seçip analizi başlatabilirsiniz.</p>
              <Link
                href="/"
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition-all mt-2 shadow-md shadow-emerald-950/20"
              >
                Yeni Analiz Başlat
              </Link>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-zinc-100/80 dark:bg-zinc-950/80 border-b border-zinc-200 dark:border-zinc-800 text-[11px] font-mono text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">
                  <tr>
                    <th className="py-3.5 px-4">İş ID</th>
                    <th className="py-3.5 px-4">Çalışma Alanı (AOI)</th>
                    <th className="py-3.5 px-4">Olay Tarihi</th>
                    <th className="py-3.5 px-4">Durum</th>
                    <th className="py-3.5 px-4">Oluşturulma</th>
                    <th className="py-3.5 px-4 text-right">İşlemler</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800/60 font-medium">
                  {filteredJobs.map((job) => (
                    <tr key={job.id} className="hover:bg-zinc-50 dark:hover:bg-zinc-800/30 transition-colors">
                      <td className="py-3 px-4 font-mono text-zinc-500 dark:text-zinc-400 text-[11px]">
                        {job.id.substring(0, 8)}...
                      </td>
                      <td className="py-3 px-4 text-zinc-800 dark:text-zinc-200">
                        {job.aoi_name || "İsimsiz Parsel"}
                      </td>
                      <td className="py-3 px-4 text-zinc-600 dark:text-zinc-300 flex items-center gap-1.5">
                        <Calendar className="w-3.5 h-3.5 text-zinc-400" />
                        {job.event_date ? new Date(job.event_date).toLocaleDateString("tr-TR") : "-"}
                      </td>
                      <td className="py-3 px-4">
                        {getStatusBadge(job.status)}
                      </td>
                      <td className="py-3 px-4 text-zinc-500 dark:text-zinc-400 text-[11px]">
                        {job.created_at ? new Date(job.created_at).toLocaleString("tr-TR") : "-"}
                      </td>
                      <td className="py-3 px-4 text-right space-x-2">
                        {job.status === "done" && (
                          <a
                            href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/jobs/${job.id}/export/pdf`}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-200 text-[11px] font-semibold border border-zinc-300 dark:border-zinc-700 transition-all shadow-sm"
                          >
                            <FileText className="w-3 h-3 text-red-500 dark:text-red-400" />
                            PDF Raporu
                          </a>
                        )}
                        <Link
                          href={`/?jobId=${job.id}`}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-emerald-500/10 dark:bg-emerald-600/20 hover:bg-emerald-500/20 dark:hover:bg-emerald-600/30 text-emerald-600 dark:text-emerald-400 text-[11px] font-semibold border border-emerald-500/30 transition-all"
                        >
                          Görüntüle
                          <ArrowUpRight className="w-3 h-3" />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
