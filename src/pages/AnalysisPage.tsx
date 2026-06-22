import { useState } from "react";
import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import ETIGauge from "../components/ETIGauge";
import { Footer } from "./LandingPage";
import type { Page } from "../App";

interface AnalysisPageProps {
  result: any;
  setPage: (p: Page) => void;
}

const THREAT_COLORS: Record<string, string> = {
  Critical: "#ff4444",
  High:     "#ff9944",
  Moderate: "#ffcc00",
  Low:      "#57f1db",
};

/* ── small reusable card wrapper ── */
function Card({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div
      className="glass-panel rounded-xl"
      style={{ ...style }}
    >
      {children}
    </div>
  );
}

export default function AnalysisPage({ result, setPage }: AnalysisPageProps) {
  const [showHeatmap, setShowHeatmap] = useState(false);

  if (!result) {
    return (
      <div className="flex items-center justify-center h-96" style={{ color: "var(--on-surface-variant)" }}>
        No result.{" "}
        <button onClick={() => setPage("upload")} style={{ color: "var(--primary)", marginLeft: 8, background: "none", border: "none", cursor: "pointer" }}>
          Go back
        </button>
      </div>
    );
  }

  const feat = result.features ?? {};
  const eti  = result.eti ?? {};
  const threatColor = THREAT_COLORS[eti.threat_level] ?? "var(--primary)";

  const sampleId  = `MC-${new Date().toISOString().slice(0, 10).replace(/-/g, "")}-${Math.floor(Math.random() * 1000).toString().padStart(3, "0")}`;
  const analyzedOn = new Date(result.timestamp ?? Date.now()).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });

  const measurements = [
    { label: "Feret Diameter",  value: feat.feret_diameter?.toFixed(1)  ?? "—", unit: feat.unit ?? "px" },
    { label: "Martin's Diameter", value: feat.martin_diameter?.toFixed(1) ?? "—", unit: feat.unit ?? "px" },
    { label: "Aspect Ratio",    value: feat.aspect_ratio?.toFixed(1)    ?? "—", unit: "Ratio" },
    { label: "Area",            value: feat.area?.toFixed(0)            ?? "—", unit: feat.unit ? `${feat.unit}²` : "px²" },
    { label: "Perimeter",       value: feat.perimeter?.toFixed(1)       ?? "—", unit: feat.unit ?? "px" },
  ];

  const displayImage = showHeatmap && result.gradcam_heatmap_b64
    ? `data:image/png;base64,${result.gradcam_heatmap_b64}`
    : result.imageUrl;

  /* shared label style */
  const sectionLabel: React.CSSProperties = {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: "0.75rem",
    letterSpacing: "0.08em",
    color: "var(--primary)",
    marginBottom: "0.75rem",
  };

  return (
    <div className="min-h-screen pt-20" style={{ background: "var(--background)" }}>
      <main className="max-w-7xl mx-auto px-4 md:px-8 py-8 md:py-12">

        {/* ── Header ── */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8"
        >
          <div>
            <h1 className="text-3xl font-bold mb-1" style={{ fontFamily: "'Hanken Grotesk', sans-serif", color: "var(--on-surface)" }}>
              Analysis Results
            </h1>
            <p className="text-sm" style={{ color: "var(--on-surface-variant)" }}>
              Sample ID: {sampleId} &nbsp;•&nbsp; Analysed on {analyzedOn}
            </p>
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            {[
              { icon: "flag", label: "FLAG PREDICTION AS INCORRECT" },
              { icon: "bookmark_add", label: "SAVE TO DASHBOARD" },
            ].map(({ icon, label }) => (
              <button
                key={label}
                className="flex items-center gap-2 text-xs px-4 py-2 rounded transition-colors"
                style={{ border: "1px solid var(--outline-variant)", color: "var(--on-surface-variant)", background: "none", fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.04em", cursor: "pointer" }}
                onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.background = "var(--surface-container-high)")}
                onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.background = "none")}
              >
                <span className="material-symbols-outlined" style={{ fontSize: "14px" }}>{icon}</span>
                {label}
              </button>
            ))}
            <button
              onClick={() => setPage("upload")}
              className="flex items-center justify-center w-9 h-9 rounded transition-colors"
              style={{ border: "1px solid var(--outline-variant)", color: "var(--on-surface-variant)", background: "none", cursor: "pointer" }}
              onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.background = "var(--surface-container-high)")}
              onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.background = "none")}
              title="New analysis"
            >
              <span className="material-symbols-outlined" style={{ fontSize: "16px" }}>restart_alt</span>
            </button>
          </div>
        </motion.div>

        {/* ── Main 2-col grid ── */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-5">

          {/* Left — image viewer */}
          <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.1 }}>
            <Card>
              {/* Card header */}
              <div className="flex items-center justify-between px-5 py-3" style={{ borderBottom: "1px solid rgba(60,74,70,0.3)" }}>
                <span style={sectionLabel}>MORPHOLOGICAL CAPTURE</span>
                {/* Heatmap toggle */}
                <label className="flex items-center gap-2 cursor-pointer select-none">
                  <span className="text-xs" style={{ color: "var(--on-surface-variant)" }}>Show heatmap</span>
                  <div
                    onClick={() => setShowHeatmap((v) => !v)}
                    className="relative rounded-full transition-colors duration-200"
                    style={{ width: 36, height: 20, background: showHeatmap ? "var(--primary)" : "var(--surface-container-high)", cursor: "pointer" }}
                  >
                    <div
                      className="absolute top-1 rounded-full transition-all duration-200"
                      style={{ width: 12, height: 12, background: "#fff", left: showHeatmap ? 20 : 4 }}
                    />
                  </div>
                </label>
              </div>

              {/* Image */}
              <div className="relative">
                {displayImage ? (
                  <img src={displayImage} alt="microplastic" className="w-full object-cover" style={{ maxHeight: 340, minHeight: 240 }} />
                ) : (
                  <div className="flex items-center justify-center" style={{ height: 280, color: "var(--outline)" }}>No image</div>
                )}
                {feat.scale_um_per_px && (
                  <div className="absolute bottom-3 right-3 text-xs px-3 py-1 rounded" style={{ background: "rgba(0,0,0,0.75)", color: "var(--on-surface-variant)", fontFamily: "'JetBrains Mono', monospace" }}>
                    Scale: {feat.scale_um_per_px} μm/px
                  </div>
                )}
              </div>
            </Card>
          </motion.div>

          {/* Right column */}
          <div className="flex flex-col gap-5">

            {/* Primary classification */}
            <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.15 }}>
              <Card style={{ padding: "1.25rem" }}>
                <p style={sectionLabel}>PRIMARY CLASSIFICATION</p>
                <div className="flex items-baseline gap-3 mb-4">
                  <span className="text-5xl font-bold" style={{ fontFamily: "'Hanken Grotesk', sans-serif", color: "var(--on-surface)" }}>
                    {result.predicted_class ?? "—"}
                  </span>
                  <span className="text-lg font-semibold" style={{ color: "var(--primary)" }}>
                    {result.confidence ? `${(result.confidence * 100).toFixed(0)}% confidence` : ""}
                  </span>
                </div>
                {/* Probability bars */}
                {result.class_probabilities && (
                  <div className="space-y-2">
                    {Object.entries(result.class_probabilities as Record<string, number>).map(([cls, prob]) => (
                      <div key={cls} className="flex items-center gap-3">
                        <span className="text-xs w-20" style={{ fontFamily: "'JetBrains Mono', monospace", color: "var(--on-surface-variant)" }}>{cls}</span>
                        <div className="flex-1 rounded-full overflow-hidden" style={{ height: 4, background: "var(--surface-container-high)" }}>
                          <div
                            className="h-full rounded-full transition-all duration-700"
                            style={{ width: `${(prob * 100).toFixed(1)}%`, background: cls === result.predicted_class ? "var(--primary)" : "var(--surface-container-highest)" }}
                          />
                        </div>
                        <span className="text-xs w-10 text-right" style={{ fontFamily: "'JetBrains Mono', monospace", color: "var(--outline)" }}>
                          {(prob * 100).toFixed(1)}%
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            </motion.div>

            {/* Geometric measurements */}
            <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.2 }}>
              <Card style={{ padding: "1.25rem" }}>
                <p style={sectionLabel}>GEOMETRIC MEASUREMENTS</p>
                <table className="w-full text-sm">
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--outline-variant)" }}>
                      <th className="text-left pb-2 font-normal" style={{ color: "var(--outline)" }}>Metric</th>
                      <th className="text-right pb-2 font-normal" style={{ color: "var(--outline)" }}>Value</th>
                      <th className="text-right pb-2 font-normal" style={{ color: "var(--outline)" }}>Unit</th>
                    </tr>
                  </thead>
                  <tbody>
                    {measurements.map((m) => (
                      <tr key={m.label} style={{ borderBottom: "1px solid rgba(60,74,70,0.2)" }}>
                        <td className="py-2" style={{ color: "var(--on-surface-variant)" }}>{m.label}</td>
                        <td className="py-2 text-right" style={{ fontFamily: "'JetBrains Mono', monospace", color: "var(--primary)" }}>{m.value}</td>
                        <td className="py-2 text-right text-xs" style={{ color: "var(--outline)" }}>{m.unit}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            </motion.div>

            {/* ETI gauge */}
            <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.25 }}>
              <Card style={{ padding: "1.25rem", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div>
                  <p style={sectionLabel}>ECOLOGICAL THREAT INDEX</p>
                  <div
                    className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold"
                    style={{ background: `${threatColor}22`, color: threatColor, border: `1px solid ${threatColor}44` }}
                  >
                    {eti.threat_level ?? "—"} Risk
                  </div>
                </div>
                <ETIGauge score={eti.score ?? 0} color={threatColor} size={90} />
              </Card>
            </motion.div>
          </div>
        </div>

        {/* ── Summary report ── */}
        {result.stakeholderReport && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35 }}>
            <Card style={{ padding: "1.5rem", marginBottom: "1.25rem" }}>
              <p className="flex items-center gap-2 mb-4" style={sectionLabel}>
                <span className="material-symbols-outlined" style={{ fontSize: "14px" }}>description</span>
                SUMMARY REPORT
              </p>
              <div style={{ color: "var(--on-surface-variant)", lineHeight: 1.75, fontFamily: "'Inter', sans-serif", fontSize: "0.9375rem" }}>
                <ReactMarkdown>{result.stakeholderReport}</ReactMarkdown>
              </div>
            </Card>
          </motion.div>
        )}

        {/* Integrity hash */}
        {result.integrityHash && (
          <p className="text-xs mb-6" style={{ fontFamily: "'JetBrains Mono', monospace", color: "var(--surface-container-highest)" }}>
            SHA-256: {result.integrityHash}
          </p>
        )}
      </main>

      <Footer />
    </div>
  );
}
