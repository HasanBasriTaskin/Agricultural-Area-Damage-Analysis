"use client";

import React, { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { Sidebar } from "@/components/Sidebar";
import { Activity, Server, Cpu, ListChecks, CheckCircle2, Clock, XCircle, RefreshCw, ShieldAlert, FileText } from "lucide-react";
import { toast } from "sonner";

interface QueueStats {
  workers_online: number;
  active_tasks_count: number;
  reserved_tasks_count: number;
  scheduled_tasks_count: number;
  workers: string[];
}

interface AdminJob {
  id: string;
  aoi_name: string;
  user_email: string;
  status: string;
  sar_status?: string;
  ms_status?: string;
  weather_status?: string;
  event_date?: string;
  created_at?: string;
  error_message?: string;
}

export default function AdminJobsPage() {
  const { data: session, status: authStatus } = useSession();
  const [stats, setStats] = useState<QueueStats | null>(null);
  const [jobs, setJobs] = useState<AdminJob[]>([]);
  const [loading, setLoading] = useState(true);

  const isAdmin = session?.user?.role === "admin";

  const fetchMonitoringData = async () => {
    if (!isAdmin) return;
    setLoading(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

      const [statsRes, jobsRes] = await Promise.all([
        fetch(`${apiUrl}/api/v1/admin/queue-stats`, {
          headers: { Authorization: `Bearer ${session?.accessToken}` },
        }),
        fetch(`${apiUrl}/api/v1/admin/jobs`, {
          headers: { Authorization: `Bearer ${session?.accessToken}` },
        }),
      ]);

      if (statsRes.ok) {
        const statsData = await statsRes.json();
        setStats(statsData);
      }
      if (jobsRes.ok) {
        const jobsData = await jobsRes.json();
        setJobs(jobsData);
      }
    } catch (err) {
      toast.error("İzleme verileri alınırken hata oluştu.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (authStatus === "authenticated" && isAdmin) {
      fetchMonitoringData();
    } else if (authStatus !== "loading" && !isAdmin) {
      setLoading(false);
    }
  }, [authStatus, session, isAdmin]);

  if (!isAdmin && authStatus !== "loading") {
    return (
      <div className="min-h-screen flex bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 transition-colors">
        <Sidebar />
        <main className="flex-1 p-12 flex flex-col items-center justify-center text-center space-y-4">
          <ShieldAlert className="w-16 h-16 text-amber-500 animate-bounce" />
          <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-100">Yetkisiz Erişim (403 Forbidden)</h2>
          <p className="text-xs text-zinc-600 dark:text-zinc-400 max-w-md">
            Sistem ve kuyruk izleme paneline sadece <b className="text-amber-600 dark:text-amber-400">ADMIN</b> rolündeki yöneticiler erişebilir.
          </p>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 transition-colors duration-200">
      <Sidebar />

      <main className="flex-1 p-8 overflow-y-auto max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-zinc-200 dark:border-zinc-800">
          <div>
            <h1 className="text-xl font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
              <Activity className="w-5 h-5 text-amber-600 dark:text-amber-400" />
              Sistem Sağlığı & Celery Kuyruk İzleme
            </h1>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
              Canlı çalışan Celery worker'ları, asenkron analiz kuyruğu ve tüm sistem işlerinin durumu.
            </p>
          </div>

          <button
            onClick={fetchMonitoringData}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-white dark:bg-zinc-900 hover:bg-zinc-100 dark:hover:bg-zinc-800 border border-zinc-300 dark:border-zinc-800 text-zinc-700 dark:text-zinc-300 text-xs font-semibold transition-all cursor-pointer shadow-sm"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-emerald-500" : ""}`} />
            <span>Kuyruğu Yenile</span>
          </button>
        </div>

        {/* Metric Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 rounded-2xl bg-white dark:bg-zinc-900/70 border border-zinc-200 dark:border-zinc-800 shadow-md space-y-2">
            <div className="flex items-center justify-between text-xs text-zinc-500 dark:text-zinc-400">
              <span>Aktif Worker Sayısı</span>
              <Server className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            </div>
            <p className="text-2xl font-bold font-mono text-zinc-900 dark:text-zinc-100">
              {stats?.workers_online ?? 0}
            </p>
            <p className="text-[11px] text-emerald-600 dark:text-emerald-400/80 font-medium">
              ● Celery Cluster Çevrimiçi
            </p>
          </div>

          <div className="p-4 rounded-2xl bg-white dark:bg-zinc-900/70 border border-zinc-200 dark:border-zinc-800 shadow-md space-y-2">
            <div className="flex items-center justify-between text-xs text-zinc-500 dark:text-zinc-400">
              <span>Çalışan Görevler (Active)</span>
              <Cpu className="w-4 h-4 text-sky-600 dark:text-sky-400" />
            </div>
            <p className="text-2xl font-bold font-mono text-zinc-900 dark:text-zinc-100">
              {stats?.active_tasks_count ?? 0}
            </p>
            <p className="text-[11px] text-zinc-500 font-medium">
              Paralel SAR/MS/Weather Pipeline
            </p>
          </div>

          <div className="p-4 rounded-2xl bg-white dark:bg-zinc-900/70 border border-zinc-200 dark:border-zinc-800 shadow-md space-y-2">
            <div className="flex items-center justify-between text-xs text-zinc-500 dark:text-zinc-400">
              <span>Bekleyen Görevler (Reserved)</span>
              <Clock className="w-4 h-4 text-amber-600 dark:text-amber-400" />
            </div>
            <p className="text-2xl font-bold font-mono text-zinc-900 dark:text-zinc-100">
              {stats?.reserved_tasks_count ?? 0}
            </p>
            <p className="text-[11px] text-zinc-500 font-medium">
              Redis Kuyruğunda Bekleyen
            </p>
          </div>

          <div className="p-4 rounded-2xl bg-white dark:bg-zinc-900/70 border border-zinc-200 dark:border-zinc-800 shadow-md space-y-2">
            <div className="flex items-center justify-between text-xs text-zinc-500 dark:text-zinc-400">
              <span>Toplam Sistem İşi</span>
              <ListChecks className="w-4 h-4 text-purple-600 dark:text-purple-400" />
            </div>
            <p className="text-2xl font-bold font-mono text-zinc-900 dark:text-zinc-100">
              {jobs.length}
            </p>
            <p className="text-[11px] text-zinc-500 font-medium">
              Kayıtlı Analiz Görevi
            </p>
          </div>
        </div>

        {/* Global Jobs Table */}
        <div className="bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800/80 rounded-2xl overflow-hidden shadow-xl backdrop-blur-md transition-colors">
          <div className="p-4 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-800 dark:text-zinc-300 font-mono">
              Tüm Kullanıcıların Analiz İşleri
            </h3>
            <span className="text-[11px] text-zinc-500">{jobs.length} Kayıt</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-zinc-100/80 dark:bg-zinc-950/80 border-b border-zinc-200 dark:border-zinc-800 text-[11px] font-mono text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">
                <tr>
                  <th className="py-3.5 px-4">İş ID</th>
                  <th className="py-3.5 px-4">Kullanıcı</th>
                  <th className="py-3.5 px-4">Alan (AOI)</th>
                  <th className="py-3.5 px-4">Genel Durum</th>
                  <th className="py-3.5 px-4">Pipeline Durumları</th>
                  <th className="py-3.5 px-4">Tarih</th>
                  <th className="py-3.5 px-4 text-right">Rapor</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800/60 font-medium">
                {jobs.map((job) => (
                  <tr key={job.id} className="hover:bg-zinc-50 dark:hover:bg-zinc-800/30 transition-colors">
                    <td className="py-3 px-4 font-mono text-zinc-500 dark:text-zinc-400 text-[11px]">
                      {job.id.substring(0, 8)}...
                    </td>
                    <td className="py-3 px-4 text-zinc-700 dark:text-zinc-300">
                      {job.user_email}
                    </td>
                    <td className="py-3 px-4 text-zinc-800 dark:text-zinc-200">
                      {job.aoi_name}
                    </td>
                    <td className="py-3 px-4">
                      {job.status === "done" ? (
                        <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-semibold">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Tamamlandı
                        </span>
                      ) : job.status === "failed" ? (
                        <span className="inline-flex items-center gap-1 text-red-600 dark:text-red-400 font-semibold">
                          <XCircle className="w-3.5 h-3.5" /> Hata
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-amber-600 dark:text-amber-400 font-semibold animate-pulse">
                          <Clock className="w-3.5 h-3.5" /> İşleniyor
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-[11px] font-mono text-zinc-600 dark:text-zinc-400 space-x-1.5">
                      <span className="bg-zinc-100 dark:bg-zinc-950 px-1.5 py-0.5 rounded border border-zinc-300 dark:border-zinc-800">
                        SAR: {job.sar_status || "-"}
                      </span>
                      <span className="bg-zinc-100 dark:bg-zinc-950 px-1.5 py-0.5 rounded border border-zinc-300 dark:border-zinc-800">
                        MS: {job.ms_status || "-"}
                      </span>
                      <span className="bg-zinc-100 dark:bg-zinc-950 px-1.5 py-0.5 rounded border border-zinc-300 dark:border-zinc-800">
                        Hava: {job.weather_status || "-"}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-zinc-500 dark:text-zinc-400 text-[11px]">
                      {job.created_at ? new Date(job.created_at).toLocaleString("tr-TR") : "-"}
                    </td>
                    <td className="py-3 px-4 text-right">
                      {job.status === "done" && (
                        <a
                          href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/jobs/${job.id}/export/pdf`}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-200 text-[11px] font-semibold border border-zinc-300 dark:border-zinc-700 transition-all shadow-sm"
                        >
                          <FileText className="w-3 h-3 text-red-500 dark:text-red-400" />
                          PDF
                        </a>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  );
}
