import { useState } from "react";
import Navbar from "./components/Navbar";
import LandingPage from "./pages/LandingPage";
import UploadPage from "./pages/UploadPage";
import AnalysisPage from "./pages/AnalysisPage";
import DashboardPage from "./pages/DashboardPage";

export type Page = "landing" | "upload" | "results" | "dashboard";

export default function App() {
  const [page, setPage] = useState<Page>("landing");
  const [analysisResult, setAnalysisResult] = useState<any>(null);

  return (
    <div className="min-h-screen" style={{ background: "var(--background)" }}>
      <Navbar page={page} setPage={setPage} />

      {page === "landing" && <LandingPage setPage={setPage} />}

      {page === "upload" && (
        <UploadPage
          setPage={setPage}
          onResult={(result) => {
            setAnalysisResult(result);
            setPage("results");
          }}
        />
      )}

      {page === "results" && (
        <AnalysisPage result={analysisResult} setPage={setPage} />
      )}

      {page === "dashboard" && <DashboardPage setPage={setPage} />}
    </div>
  );
}
