import { useState, useCallback, useEffect, useRef } from "react";
import { useDropzone } from "react-dropzone";
import type { Page } from "../App";
import { Footer } from "./LandingPage";

interface UploadPageProps {
  setPage: (p: Page) => void;
  onResult: (result: any) => void;
}

const STATUSES = [
  "Segmenting background geometry...",
  "Extracting morphological features...",
  "Applying classification model...",
  "Scoring confidence metrics...",
  "Finalizing report...",
];

export default function UploadPage({ setPage, onResult }: UploadPageProps) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [scale, setScale] = useState<number>(1.25);
  const [siteId, setSiteId] = useState<string>("");
  const [notes, setNotes] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusText, setStatusText] = useState(STATUSES[0]);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const onDrop = useCallback((accepted: File[]) => {
    const f = accepted[0];
    if (!f) return;
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setError(null);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "image/*": [".tif", ".jpg", ".jpeg", ".png"] },
    maxFiles: 1,
  });

  const removeFile = (e: React.MouseEvent) => {
    e.stopPropagation();
    setFile(null);
    setPreview(null);
  };

  useEffect(() => {
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, []);

  const startFakeProgress = () => {
    let p = 0;
    let si = 0;
    setProgress(0);
    setStatusText(STATUSES[0]);
    intervalRef.current = setInterval(() => {
      p += Math.floor(Math.random() * 5) + 1;
      if (p >= 95) p = 95;
      setProgress(p);
      const expected = Math.floor((p / 100) * STATUSES.length);
      if (expected > si && expected < STATUSES.length) {
        si = expected;
        setStatusText(STATUSES[si]);
      }
    }, 160);
  };

  const stopFakeProgress = () => {
    if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current = null; }
  };

  const handleRunAnalysis = async () => {
    if (!file) return;
    setError(null);
    setLoading(true);
    startFakeProgress();
    try {
      const fd = new FormData();
      fd.append("image", file);
      fd.append("scale_um_per_px", String(scale));
      if (siteId) fd.append("site_id", siteId);
      if (notes) fd.append("notes", notes);
      const res = await fetch("/api/analyze", { method: "POST", body: fd });
      if (!res.ok) {
        const errData: any = await res.json().catch(() => ({}));
        throw new Error(errData.error ?? `Server error ${res.status}`);
      }
      const data = await res.json();
      stopFakeProgress();
      setProgress(100);
      setStatusText("Analysis Complete.");
      await new Promise((r) => setTimeout(r, 800));
      setLoading(false);
      onResult(data);
    } catch (e: any) {
      stopFakeProgress();
      setLoading(false);
      setProgress(0);
      setError(e.message ?? "Analysis failed");
    }
  };

  /* ─────────── shared style helpers ─────────── */
  const inputStyle: React.CSSProperties = {
    width: "100%",
    background: "var(--surface-container-lowest)",
    border: "1px solid var(--outline-variant)",
    borderRadius: "0.25rem",
    padding: "10px 16px",
    fontFamily: "'Inter', sans-serif",
    fontSize: "0.9375rem",
    color: "var(--on-surface)",
    outline: "none",
    transition: "border-color 0.15s, box-shadow 0.15s",
  };

  return (
    <div className="min-h-screen pt-20" style={{ background: "var(--background)" }}>
      <main className="max-w-7xl mx-auto px-4 md:px-8 py-8 md:py-12">

        {/* ── Page header ── */}
        <div className="flex items-center gap-3 mb-8">
          <button
            onClick={() => setPage("landing")}
            aria-label="Go back"
            className="w-10 h-10 flex items-center justify-center rounded-full transition-colors"
            style={{ color: "var(--on-surface-variant)", background: "none", border: "none", cursor: "pointer" }}
            onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.background = "var(--surface-container-high)")}
            onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.background = "none")}
          >
            <span className="material-symbols-outlined">arrow_back</span>
          </button>
          <div>
            <h1
              className="font-bold"
              style={{ fontFamily: "'Hanken Grotesk', sans-serif", fontSize: "2rem", color: "var(--on-surface)" }}
            >
              New analysis
            </h1>
            <p className="mt-1 text-sm" style={{ color: "var(--on-surface-variant)" }}>
              Upload a sample image and configure classification parameters.
            </p>
          </div>
        </div>

        {/* ── Configuration grid ── */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">

          {/* ── Left col: Sample Input ── */}
          <div className="lg:col-span-7 flex flex-col gap-6">
            <div
              className="glass-panel rounded-xl overflow-hidden flex flex-col"
              style={{ boxShadow: "0 8px 32px rgba(0,0,0,0.5)" }}
            >
              <div
                className="px-6 py-4"
                style={{ borderBottom: "1px solid rgba(60,74,70,0.3)", background: "rgba(28,27,27,0.5)" }}
              >
                <h2 className="font-semibold text-lg" style={{ fontFamily: "'Hanken Grotesk', sans-serif", color: "var(--on-surface)" }}>
                  Sample Input
                </h2>
              </div>
              <div className="p-6">
                <div
                  {...getRootProps()}
                  className={`w-full h-80 rounded-xl border-2 border-dashed flex flex-col items-center justify-center transition-all duration-300 relative cursor-pointer group${isDragActive ? " dropzone-active" : ""}`}
                  style={{
                    borderColor: isDragActive ? "var(--primary)" : "var(--outline)",
                    background: "rgba(14,14,14,0.40)",
                    boxShadow: "inset 0 0 20px rgba(0,0,0,0.5)",
                  }}
                >
                  <input {...getInputProps()} accept=".tif,.jpg,.jpeg,.png" />

                  {file && preview ? (
                    /* Selected state */
                    <div className="absolute inset-0 glass-panel flex flex-col p-6 rounded-xl">
                      <div
                        className="w-full flex-1 rounded-lg overflow-hidden relative mb-4"
                        style={{ background: "var(--surface-container-highest)", border: "1px solid var(--outline-variant)" }}
                      >
                        <img src={preview} alt="Sample preview" className="w-full h-full object-cover opacity-70" />
                        <div className="absolute inset-0" style={{ background: "linear-gradient(to top, var(--background) 0%, transparent 50%)" }} />
                      </div>
                      <div
                        className="flex items-center justify-between w-full p-3 rounded-lg pointer-events-auto"
                        style={{ background: "var(--surface-container-low)", border: "1px solid rgba(60,74,70,0.5)" }}
                      >
                        <div className="flex items-center gap-3">
                          <span className="material-symbols-outlined" style={{ color: "var(--primary)" }}>image</span>
                          <div>
                            <p className="text-xs font-medium" style={{ fontFamily: "'JetBrains Mono', monospace", color: "var(--on-surface)" }}>{file.name}</p>
                            <p className="text-xs opacity-70" style={{ fontFamily: "'JetBrains Mono', monospace", color: "var(--on-surface-variant)" }}>{(file.size / (1024 * 1024)).toFixed(2)} MB</p>
                          </div>
                        </div>
                        <button
                          onClick={removeFile}
                          className="p-2 rounded-full transition-colors"
                          style={{ color: "var(--error)", background: "none", border: "none", cursor: "pointer" }}
                          onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.background = "rgba(147,0,10,0.3)")}
                          onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.background = "none")}
                        >
                          <span className="material-symbols-outlined" style={{ fontSize: "20px" }}>delete</span>
                        </button>
                      </div>
                    </div>
                  ) : (
                    /* Default / empty state */
                    <div className="flex flex-col items-center justify-center pointer-events-none">
                      <div
                        className="w-16 h-16 rounded-full flex items-center justify-center mb-4 transition-all duration-300"
                        style={{
                          background: "rgba(42,42,42,0.80)",
                          border: "1px solid var(--outline-variant)",
                          boxShadow: "0 0 15px rgba(255,255,255,0.05)",
                        }}
                      >
                        <span className="material-symbols-outlined" style={{ fontSize: "32px", color: "var(--primary)" }}>cloud_upload</span>
                      </div>
                      <p className="text-lg font-semibold mb-2" style={{ fontFamily: "'Hanken Grotesk', sans-serif", color: "var(--on-surface)" }}>
                        Drag and drop file here
                      </p>
                      <p className="text-sm mb-6 text-center max-w-xs" style={{ color: "var(--on-surface-variant)" }}>
                        Supported formats: TIFF, JPEG, PNG. Maximum file size: 50MB.
                      </p>
                      <button
                        type="button"
                        className="px-4 py-2 rounded transition-colors pointer-events-auto"
                        style={{
                          border: "1px solid var(--outline)",
                          color: "var(--on-surface)",
                          background: "var(--surface-container)",
                          fontFamily: "'JetBrains Mono', monospace",
                          fontSize: "0.75rem",
                          cursor: "pointer",
                        }}
                        onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "rgba(87,241,219,0.5)"; (e.currentTarget as HTMLElement).style.boxShadow = "0 0 10px rgba(45,212,191,0.2)"; }}
                        onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--outline)"; (e.currentTarget as HTMLElement).style.boxShadow = "none"; }}
                      >
                        Browse files
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* ── Right col: Analysis Parameters ── */}
          <div className="lg:col-span-5 flex flex-col gap-6">
            <div
              className="glass-panel rounded-xl overflow-hidden flex flex-col"
              style={{ boxShadow: "0 8px 32px rgba(0,0,0,0.5)" }}
            >
              <div
                className="px-6 py-4"
                style={{ borderBottom: "1px solid rgba(60,74,70,0.3)", background: "rgba(28,27,27,0.5)" }}
              >
                <h2 className="font-semibold text-lg" style={{ fontFamily: "'Hanken Grotesk', sans-serif", color: "var(--on-surface)" }}>
                  Analysis Parameters
                </h2>
              </div>
              <div className="p-6 flex flex-col gap-6">

                {/* Scale calibration */}
                <div className="flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-medium flex items-center gap-2" style={{ fontFamily: "'JetBrains Mono', monospace", color: "var(--on-surface)", letterSpacing: "0.05em" }}>
                      Scale Calibration
                      <div className="relative group cursor-help">
                        <span className="material-symbols-outlined" style={{ fontSize: "16px", color: "rgba(87,241,219,0.7)" }}>info</span>
                        <div
                          className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-3 rounded opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-20 pointer-events-none text-xs leading-tight"
                          style={{ background: "var(--surface-bright)", border: "1px solid var(--outline-variant)", color: "var(--on-surface)", boxShadow: "0 8px 32px rgba(0,0,0,0.6)" }}
                        >
                          Define the physical size of one pixel to ensure accurate morphological measurements.
                        </div>
                      </div>
                    </label>
                  </div>
                  <div className="relative flex items-center w-full">
                    <input
                      id="scale-input"
                      type="number"
                      min={0.01}
                      step={0.01}
                      value={scale}
                      onChange={(e) => setScale(parseFloat(e.target.value) || 1.25)}
                      style={{ ...inputStyle, borderRadius: "0.25rem 0 0 0.25rem", paddingRight: "48px" }}
                      onFocus={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--primary)"; (e.currentTarget as HTMLElement).style.boxShadow = "0 0 8px rgba(45,212,191,0.4)"; }}
                      onBlur={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--outline-variant)"; (e.currentTarget as HTMLElement).style.boxShadow = "none"; }}
                    />
                    <div
                      className="flex items-center justify-center min-w-[80px] px-4 py-2.5 text-xs"
                      style={{
                        background: "var(--surface-container)",
                        border: "1px solid var(--outline-variant)",
                        borderLeft: "none",
                        borderRadius: "0 0.25rem 0.25rem 0",
                        fontFamily: "'JetBrains Mono', monospace",
                        color: "var(--on-surface-variant)",
                      }}
                    >
                      µm / px
                    </div>
                    {/* Stepper */}
                    <div className="absolute flex flex-col" style={{ right: 81, top: 1, bottom: 1, borderLeft: "1px solid var(--outline-variant)", background: "var(--surface-container)" }}>
                      <button type="button" onClick={() => setScale((s) => Math.round((s + 0.01) * 100) / 100)} className="flex-1 px-1.5 flex items-center justify-center transition-colors" style={{ color: "var(--on-surface-variant)", background: "none", border: "none", borderBottom: "1px solid var(--outline-variant)", cursor: "pointer" }} onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "var(--surface-container-high)"; (e.currentTarget as HTMLElement).style.color = "var(--primary)"; }} onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "none"; (e.currentTarget as HTMLElement).style.color = "var(--on-surface-variant)"; }}>
                        <span className="material-symbols-outlined" style={{ fontSize: "14px" }}>expand_less</span>
                      </button>
                      <button type="button" onClick={() => setScale((s) => Math.max(0.01, Math.round((s - 0.01) * 100) / 100))} className="flex-1 px-1.5 flex items-center justify-center transition-colors" style={{ color: "var(--on-surface-variant)", background: "none", border: "none", cursor: "pointer" }} onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "var(--surface-container-high)"; (e.currentTarget as HTMLElement).style.color = "var(--primary)"; }} onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "none"; (e.currentTarget as HTMLElement).style.color = "var(--on-surface-variant)"; }}>
                        <span className="material-symbols-outlined" style={{ fontSize: "14px" }}>expand_more</span>
                      </button>
                    </div>
                  </div>
                </div>

                <hr style={{ borderColor: "rgba(60,74,70,0.5)" }} />

                {/* Site ID */}
                <div className="flex flex-col gap-2">
                  <label className="text-xs font-medium" style={{ fontFamily: "'JetBrains Mono', monospace", color: "var(--on-surface)", letterSpacing: "0.05em" }}>
                    Sample Site Identification
                  </label>
                  <input
                    type="text"
                    placeholder="e.g., Station_A_Depth_5m"
                    value={siteId}
                    onChange={(e) => setSiteId(e.target.value)}
                    style={inputStyle}
                    onFocus={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--primary)"; (e.currentTarget as HTMLElement).style.boxShadow = "0 0 8px rgba(45,212,191,0.4)"; }}
                    onBlur={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--outline-variant)"; (e.currentTarget as HTMLElement).style.boxShadow = "none"; }}
                  />
                </div>

                {/* Notes */}
                <div className="flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-medium" style={{ fontFamily: "'JetBrains Mono', monospace", color: "var(--on-surface)", letterSpacing: "0.05em" }}>
                      Procedural Notes
                    </label>
                    <span className="text-xs opacity-70" style={{ color: "var(--on-surface-variant)" }}>Optional</span>
                  </div>
                  <textarea
                    rows={3}
                    placeholder="Enter any specific environmental conditions or collection methodology notes here..."
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    style={{ ...inputStyle, resize: "vertical" }}
                    onFocus={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--primary)"; (e.currentTarget as HTMLElement).style.boxShadow = "0 0 8px rgba(45,212,191,0.4)"; }}
                    onBlur={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--outline-variant)"; (e.currentTarget as HTMLElement).style.boxShadow = "none"; }}
                  />
                </div>

                {/* Error */}
                {error && (
                  <div className="rounded px-4 py-3 text-sm" style={{ background: "rgba(147,0,10,0.2)", border: "1px solid rgba(255,180,171,0.3)", color: "var(--error)" }}>
                    {error}
                  </div>
                )}
              </div>
            </div>

            {/* Action row */}
            <div className="flex items-center justify-end gap-4">
              <button
                type="button"
                onClick={() => setPage("landing")}
                className="px-5 py-2.5 rounded text-sm transition-colors"
                style={{ border: "1px solid var(--outline-variant)", color: "var(--on-surface)", background: "none", fontFamily: "'JetBrains Mono', monospace", cursor: "pointer" }}
                onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "var(--surface-container-high)"; (e.currentTarget as HTMLElement).style.borderColor = "var(--outline)"; }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "none"; (e.currentTarget as HTMLElement).style.borderColor = "var(--outline-variant)"; }}
              >
                Cancel
              </button>
              <button
                id="run-analysis-btn"
                type="button"
                disabled={!file || loading}
                onClick={handleRunAnalysis}
                className="flex items-center gap-2 px-6 py-2.5 rounded text-sm font-medium transition-all"
                style={{
                  background: "var(--primary-container)",
                  color: "var(--on-primary-container)",
                  border: "none",
                  fontFamily: "'JetBrains Mono', monospace",
                  cursor: file && !loading ? "pointer" : "not-allowed",
                  opacity: file && !loading ? 1 : 0.5,
                  boxShadow: file && !loading ? "0 0 10px rgba(45,212,191,0.2)" : "none",
                }}
              >
                <span className="material-symbols-outlined" style={{ fontSize: "20px" }}>science</span>
                {loading ? "Running..." : "Run analysis"}
              </button>
            </div>
          </div>
        </div>
      </main>

      <Footer />

      {/* ── Processing overlay ── */}
      <div
        className="fixed inset-0 flex items-center justify-center z-50 transition-opacity duration-300"
        style={{
          background: "rgba(19,19,19,0.85)",
          backdropFilter: "blur(12px)",
          opacity: loading ? 1 : 0,
          pointerEvents: loading ? "auto" : "none",
        }}
      >
        <div
          className="glass-panel rounded-xl p-8 w-full max-w-md mx-4 flex flex-col items-center transition-transform duration-300"
          style={{
            border: "1px solid rgba(87,241,219,0.3)",
            boxShadow: "0 0 40px rgba(45,212,191,0.2)",
            transform: loading ? "scale(1)" : "scale(0.95)",
          }}
        >
          {/* Spinning rings */}
          <div className="relative w-20 h-20 mb-6 flex items-center justify-center">
            <svg
              className="absolute inset-0 w-full h-full"
              viewBox="0 0 100 100"
              fill="none"
              style={{ animation: "spin 3s linear infinite" }}
            >
              <circle cx="50" cy="50" r="46" stroke="var(--surface-variant)" strokeDasharray="20 10" strokeWidth="4" />
            </svg>
            <svg
              className="absolute inset-0 w-full h-full"
              viewBox="0 0 100 100"
              fill="none"
              style={{ animation: "spin 2s linear infinite reverse" }}
            >
              <circle cx="50" cy="50" r="36" stroke="var(--primary)" strokeDasharray="60 40" strokeWidth="3" />
            </svg>
            <span
              className="material-symbols-outlined icon-fill relative z-10"
              style={{ fontSize: "32px", color: "var(--primary)", filter: "drop-shadow(0 0 8px rgba(87,241,219,0.8))" }}
            >
              memory
            </span>
          </div>

          <h3 className="font-semibold text-xl mb-2" style={{ fontFamily: "'Hanken Grotesk', sans-serif", color: "var(--on-surface)" }}>
            Analyzing Sample
          </h3>
          <p className="mb-8 h-6 text-sm text-center transition-opacity" style={{ fontFamily: "'JetBrains Mono', monospace", color: "rgba(87,241,219,0.8)" }}>
            {statusText}
          </p>

          {/* Progress bar */}
          <div className="w-full flex flex-col gap-2">
            <div className="w-full h-2 rounded-full overflow-hidden" style={{ background: "var(--surface-container-highest)", border: "1px solid rgba(60,74,70,0.3)" }}>
              <div
                className="h-full rounded-full transition-all duration-300 ease-out"
                style={{
                  width: `${progress}%`,
                  background: "var(--primary)",
                  boxShadow: "0 0 10px rgba(87,241,219,0.8)",
                }}
              />
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs" style={{ fontFamily: "'JetBrains Mono', monospace", color: "var(--outline)" }}>
                {progress < 33 ? "Phase 1/3" : progress < 66 ? "Phase 2/3" : "Phase 3/3"}
              </span>
              <span className="text-xs font-medium" style={{ fontFamily: "'JetBrains Mono', monospace", color: "var(--primary)" }}>
                {progress}%
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Spin keyframe */}
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
