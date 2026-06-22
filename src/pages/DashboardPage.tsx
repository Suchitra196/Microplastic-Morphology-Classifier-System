import { useState } from "react";
import { motion } from "framer-motion";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { ChevronLeft, ChevronRight, AlertTriangle } from "lucide-react";
import type { Page } from "../App";
import { Footer } from "./LandingPage";

interface DashboardPageProps { setPage: (p: Page) => void; }

/* ── mock data ── */
const ETI_TREND = [
  { date: "Oct 1", eti: 1.2 }, { date: "Oct 4", eti: 2.0 }, { date: "Oct 8", eti: 2.8 },
  { date: "Oct 11", eti: 3.5 }, { date: "Oct 15", eti: 4.2 }, { date: "Oct 18", eti: 5.0 },
  { date: "Oct 22", eti: 6.1 }, { date: "Oct 25", eti: 7.2 }, { date: "Oct 29", eti: 8.4 },
];

const SAMPLES = [
  { date: "2024-10-24", site: "Site Alpha-1", morphology: "Fiber",    eti: 8.4, status: "CRITICAL" },
  { date: "2024-10-23", site: "Site Beta-2",  morphology: "Fragment", eti: 6.2, status: "HIGH" },
  { date: "2024-10-23", site: "Site Gamma-3", morphology: "Pellet",   eti: 3.1, status: "LOW" },
  { date: "2024-10-22", site: "Site Delta-1", morphology: "Film",     eti: 4.8, status: "MEDIUM" },
];

const ALERTS = [
  { level: "CRITICAL ETI", color: "#ff4444", time: "10m ago", title: "High concentration of toxic fibers detected.", body: "Site Alpha-1 recorded ETI score 8.4, exceeding threshold." },
  { level: "CRITICAL ETI", color: "#ff4444", time: "1h ago",  title: "Anomalous fragment clustering.", body: "Site Gamma-3 reported sudden spike in fragment volume." },
  { level: "HIGH ETI",     color: "#ff9944", time: "4h ago",  title: "Elevated pellet count.", body: "Site Beta-2 shows increasing trend in pellet morphology." },
];

const STATUS_COLORS: Record<string, string> = { CRITICAL: "#ff4444", HIGH: "#ff9944", MEDIUM: "#ffcc00", LOW: "#57f1db" };

const ChartTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg px-3 py-2 text-xs" style={{ background: "var(--surface-container)", border: "1px solid var(--outline-variant)", color: "var(--on-surface)" }}>
      <p style={{ color: "var(--primary)", fontFamily: "'JetBrains Mono', monospace" }}>{label}</p>
      <p>ETI: {payload[0].value}</p>
    </div>
  );
};

export default function DashboardPage({ setPage }: DashboardPageProps) {
  const stats = [
    { label: "TOTAL SAMPLES",  value: "12,405", sub: <span style={{ color: "var(--primary)" }}>↑ +4.2%</span> },
    { label: "AVERAGE ETI",    value: "4.7",    sub: <span style={{ color: "var(--on-surface-variant)" }}>— Stable</span> },
    { label: "HIGH/CRITICAL",  value: <span style={{ color: "#ff9944" }}>842</span>, sub: <span style={{ color: "#ff9944" }}><AlertTriangle size={11} className="inline mr-1" />Needs attention</span> },
    { label: "COMMON MORPH",   value: "Fiber",  sub: <span style={{ color: "var(--on-surface-variant)" }}>48% of total</span> },
  ];

  return (
    <div className="min-h-screen pt-20" style={{ background: "var(--background)" }}>
      <main className="max-w-7xl mx-auto px-4 md:px-8 py-8 md:py-12">
        <div className="flex gap-6">

          {/* ── Main column ── */}
          <div className="flex-1 min-w-0">

            {/* Page header */}
            <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
              <div className="flex items-center justify-between mb-2">
                <h1 className="text-3xl font-bold" style={{ fontFamily: "'Hanken Grotesk', sans-serif", color: "var(--on-surface)" }}>
                  Analysis History
                </h1>
                <div className="flex gap-2">
                  {["Table view", "Map view"].map((v, i) => (
                    <button key={v} className="flex items-center gap-2 px-3 py-2 rounded text-xs transition-colors" style={{ border: "1px solid var(--outline-variant)", color: i === 0 ? "var(--on-surface)" : "var(--on-surface-variant)", background: i === 0 ? "var(--surface-container)" : "none", fontFamily: "'JetBrains Mono', monospace", cursor: "pointer" }}>
                      <span className="material-symbols-outlined" style={{ fontSize: "14px" }}>{i === 0 ? "table_rows" : "map"}</span>
                      {v}
                    </button>
                  ))}
                </div>
              </div>
              <p className="text-sm" style={{ color: "var(--on-surface-variant)" }}>Review longitudinal data and morphological trends.</p>
            </motion.div>

            {/* Stats cards */}
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }} className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              {stats.map((s, i) => (
                <div key={i} className="glass-panel rounded-xl p-5 relative overflow-hidden">
                  <p className="text-xs mb-2" style={{ fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.06em", color: "var(--outline)" }}>{s.label}</p>
                  <p className="text-3xl font-bold mb-1" style={{ fontFamily: "'Hanken Grotesk', sans-serif", color: "var(--on-surface)" }}>{s.value}</p>
                  <p className="text-xs">{s.sub}</p>
                  <div className="absolute bottom-0 right-0 rounded-tl-full opacity-10" style={{ width: 60, height: 60, background: "var(--primary)" }} />
                </div>
              ))}
            </motion.div>

            {/* ETI Trend chart */}
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="glass-panel rounded-xl p-5 mb-6">
              <div className="flex items-center justify-between mb-5">
                <p className="text-xs" style={{ fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.08em", color: "var(--primary)" }}>
                  ENVIRONMENTAL THREAT INDEX (ETI) TRENDS
                </p>
                <div className="text-xs px-3 py-1 rounded" style={{ border: "1px solid var(--outline-variant)", color: "var(--on-surface-variant)", cursor: "pointer", fontFamily: "'JetBrains Mono', monospace" }}>
                  Last 30 Days ▾
                </div>
              </div>
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={ETI_TREND} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="etiGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#57f1db" stopOpacity={0.35} />
                      <stop offset="100%" stopColor="#57f1db" stopOpacity={0.01} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(60,74,70,0.4)" />
                  <XAxis dataKey="date" tick={{ fill: "var(--outline)", fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: "var(--outline)", fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }} axisLine={false} tickLine={false} domain={[0, 10]} />
                  <Tooltip content={<ChartTooltip />} />
                  <Area type="monotone" dataKey="eti" stroke="#57f1db" strokeWidth={2.5} fill="url(#etiGrad)"
                    dot={{ r: 4, fill: "#57f1db", strokeWidth: 0 }}
                    activeDot={{ r: 6, fill: "#57f1db", stroke: "var(--background)", strokeWidth: 2 }} />
                </AreaChart>
              </ResponsiveContainer>
            </motion.div>

            {/* Filter bar */}
            <div className="flex items-center gap-3 mb-4 flex-wrap">
              {[
                { icon: "calendar_today", label: "Oct 1 – Oct 31, 2024" },
                { icon: "filter_alt",     label: "All Threats ▾" },
                { icon: "category",       label: "All Morphologies ▾" },
              ].map(({ icon, label }) => (
                <button key={label} className="flex items-center gap-2 text-xs px-3 py-2 rounded transition-colors" style={{ border: "1px solid var(--outline-variant)", color: "var(--on-surface-variant)", background: "none", fontFamily: "'JetBrains Mono', monospace", cursor: "pointer" }}>
                  <span className="material-symbols-outlined" style={{ fontSize: "13px" }}>{icon}</span>
                  {label}
                </button>
              ))}
              <button className="ml-auto text-xs px-3 py-2 rounded" style={{ border: "1px solid var(--outline-variant)", color: "var(--on-surface-variant)", background: "none", fontFamily: "'JetBrains Mono', monospace", cursor: "pointer" }}>
                ✕ Clear Filters
              </button>
            </div>

            {/* Table */}
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }} className="glass-panel rounded-xl overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr style={{ background: "var(--surface-container-lowest)", borderBottom: "1px solid var(--outline-variant)" }}>
                    {["SAMPLE", "DATE", "SITE", "MORPHOLOGY", "ETI SCORE", "STATUS"].map((h) => (
                      <th key={h} className="text-left px-4 py-3 text-xs font-medium" style={{ fontFamily: "'JetBrains Mono', monospace", color: "var(--outline)", letterSpacing: "0.06em" }}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {SAMPLES.map((s, i) => (
                    <tr key={i}
                      style={{ borderBottom: "1px solid rgba(60,74,70,0.3)", cursor: "pointer", transition: "background 0.15s" }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-container)")}
                      onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                    >
                      <td className="px-4 py-3">
                        <div className="w-7 h-7 rounded flex items-center justify-center text-xs font-bold" style={{ background: "rgba(87,241,219,0.1)", color: "var(--primary)" }}>›</div>
                      </td>
                      <td className="px-4 py-3" style={{ color: "var(--on-surface-variant)", fontFamily: "'JetBrains Mono', monospace", fontSize: "0.8125rem" }}>{s.date}</td>
                      <td className="px-4 py-3" style={{ color: "var(--on-surface)" }}>{s.site}</td>
                      <td className="px-4 py-3" style={{ color: "var(--on-surface)" }}>{s.morphology}</td>
                      <td className="px-4 py-3 font-medium" style={{ fontFamily: "'JetBrains Mono', monospace", color: STATUS_COLORS[s.status] ?? "var(--on-surface)" }}>{s.eti}</td>
                      <td className="px-4 py-3">
                        <span className="text-xs font-semibold px-2 py-1 rounded" style={{ background: `${STATUS_COLORS[s.status] ?? "#666"}22`, color: STATUS_COLORS[s.status] ?? "var(--outline)", border: `1px solid ${STATUS_COLORS[s.status] ?? "#666"}44`, fontFamily: "'JetBrains Mono', monospace" }}>
                          {s.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Pagination */}
              <div className="flex items-center justify-between px-4 py-3" style={{ borderTop: "1px solid var(--outline-variant)", background: "var(--surface-container-lowest)" }}>
                <span className="text-xs" style={{ fontFamily: "'JetBrains Mono', monospace", color: "var(--outline)" }}>Showing 1-4 of 12,405</span>
                <div className="flex items-center gap-1">
                  <button className="w-7 h-7 rounded flex items-center justify-center" style={{ border: "1px solid var(--outline-variant)", color: "var(--outline)", background: "none", cursor: "pointer" }}>
                    <ChevronLeft size={13} />
                  </button>
                  {[1, 2, 3].map((n) => (
                    <button key={n} className="w-7 h-7 rounded flex items-center justify-center text-xs" style={{ border: n === 1 ? "1px solid var(--primary)" : "1px solid var(--outline-variant)", color: n === 1 ? "var(--primary)" : "var(--outline)", background: "none", cursor: "pointer", fontFamily: "'JetBrains Mono', monospace" }}>{n}</button>
                  ))}
                  <span className="text-xs" style={{ color: "var(--outline)" }}>…</span>
                  <button className="w-7 h-7 rounded flex items-center justify-center" style={{ border: "1px solid var(--outline-variant)", color: "var(--outline)", background: "none", cursor: "pointer" }}>
                    <ChevronRight size={13} />
                  </button>
                </div>
              </div>
            </motion.div>
          </div>

          {/* ── Alerts panel ── */}
          <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.15 }} className="w-72 flex-shrink-0">
            <div className="glass-panel rounded-xl overflow-hidden">
              <div className="flex items-center gap-2 px-5 py-4" style={{ borderBottom: "1px solid var(--outline-variant)" }}>
                <span className="material-symbols-outlined" style={{ fontSize: "18px", color: "var(--on-surface)" }}>notifications</span>
                <h2 className="font-semibold" style={{ fontFamily: "'Hanken Grotesk', sans-serif", color: "var(--on-surface)" }}>Recent Alerts</h2>
              </div>

              {ALERTS.map((a, i) => (
                <div key={i} className="px-4 py-4 text-sm" style={{ borderBottom: i < ALERTS.length - 1 ? "1px solid rgba(60,74,70,0.3)" : "none", background: `${a.color}08` }}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-semibold px-2 py-0.5 rounded" style={{ background: `${a.color}22`, color: a.color, border: `1px solid ${a.color}44`, fontFamily: "'JetBrains Mono', monospace" }}>{a.level}</span>
                    <span className="text-xs" style={{ fontFamily: "'JetBrains Mono', monospace", color: "var(--outline)" }}>{a.time}</span>
                  </div>
                  <p className="font-medium mb-1 text-xs" style={{ color: "var(--on-surface)" }}>{a.title}</p>
                  <p className="text-xs mb-2" style={{ color: "var(--on-surface-variant)" }}>{a.body}</p>
                  <button className="text-xs" style={{ color: "var(--primary)", background: "none", border: "none", cursor: "pointer", padding: 0, fontFamily: "'JetBrains Mono', monospace" }}>View Analysis</button>
                </div>
              ))}

              <div className="px-4 py-3" style={{ borderTop: "1px solid var(--outline-variant)" }}>
                <button className="w-full text-sm py-2 rounded transition-colors" style={{ border: "1px solid var(--outline-variant)", color: "var(--on-surface-variant)", background: "none", cursor: "pointer", fontFamily: "'JetBrains Mono', monospace", fontSize: "0.75rem" }}
                  onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.background = "var(--surface-container-high)")}
                  onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.background = "none")}
                >
                  View All Alerts
                </button>
              </div>
            </div>
          </motion.div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
