/**
 * Express server — Microplastic Morphology Classifier
 * =====================================================
 * Pipeline:
 *  1. Upload image → proxy to FastAPI ML service (POST /classify)
 *     • OpenCV feature extraction (real Feret/Martin/aspect ratio)
 *     • MobileNetV2 CNN classification (Fiber / Fragment / Film)
 *     • Grad-CAM heatmap generation
 *     • ETI (Ecological Threat Index) scoring
 *
 *  2. Gemini is called ONLY to generate a plain-language stakeholder
 *     report from the structured JSON result — not for classification.
 *
 *  3. A real SHA-256 hash of (image bytes + result JSON) is computed
 *     and appended to ml-service/hash_log.jsonl as an append-only log.
 *     This is NOT blockchain — it is tamper-evident local logging.
 *
 * Environment variables (see .env.example):
 *   GEMINI_API_KEY   — Gemini API key
 *   ML_SERVICE_URL   — FastAPI service base URL (default: http://localhost:8001)
 */

import express from "express";
import { createServer as createViteServer } from "vite";
import path from "path";
import cors from "cors";
import multer from "multer";
import { createHash } from "crypto";
import { appendFileSync, existsSync, mkdirSync } from "fs";
import { GoogleGenAI } from "@google/genai";
import * as dotenv from "dotenv";

dotenv.config();

const app   = express();
const PORT  = 3000;
const upload = multer({ storage: multer.memoryStorage() });

const ai  = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });
const ML_URL = process.env.ML_SERVICE_URL ?? "http://localhost:8001";

// Append-only hash log — one JSON object per line (JSONL)
const HASH_LOG = path.join(process.cwd(), "ml-service", "hash_log.jsonl");
if (!existsSync(path.dirname(HASH_LOG))) {
  mkdirSync(path.dirname(HASH_LOG), { recursive: true });
}

// ── SHA-256 helper ───────────────────────────────────────────────────────
function sha256(imageBytes: Buffer, resultJson: string): string {
  return createHash("sha256")
    .update(imageBytes)
    .update(resultJson)
    .digest("hex");
}

// ── Gemini stakeholder report ────────────────────────────────────────────
async function generateStakeholderReport(mlResult: Record<string, unknown>): Promise<string> {
  const prompt = `
You are an environmental scientist writing a brief, plain-language report for a
non-technical stakeholder (e.g. a policy-maker or journalist).

You have received the following structured analysis of a microplastic particle
detected in a water sample. Summarise it in 3-4 clear sentences. Do NOT make up
any numbers — use only the values provided. Avoid jargon where possible.

Analysis data:
${JSON.stringify(mlResult, null, 2)}

Write the stakeholder report now:
`.trim();

  const response = await ai.models.generateContent({
    model: "gemini-2.0-flash",
    contents: [{ parts: [{ text: prompt }] }],
  });
  return response.text?.trim() ?? "Report generation failed.";
}

// ── main server ───────────────────────────────────────────────────────────
async function startServer() {
  app.use(cors());
  app.use(express.json({ limit: "50mb" }));

  // ── POST /api/analyze ─────────────────────────────────────────────────
  app.post("/api/analyze", upload.single("image"), async (req: any, res) => {
    try {
      const file = req.file;
      if (!file) {
        return res.status(400).json({ error: "No image uploaded" });
      }

      const scaleParam = req.body?.scale_um_per_px;

      // 1. Call the FastAPI ML service
      const formData = new FormData();
      const blob = new Blob([file.buffer], { type: file.mimetype });
      formData.append("image", blob, file.originalname ?? "image.jpg");
      if (scaleParam) {
        formData.append("scale_um_per_px", String(scaleParam));
      }

      let mlResult: Record<string, unknown>;
      try {
        const mlResponse = await fetch(`${ML_URL}/classify`, {
          method:  "POST",
          body:    formData,
        });
        if (!mlResponse.ok) {
          const errText = await mlResponse.text();
          throw new Error(`ML service error ${mlResponse.status}: ${errText}`);
        }
        mlResult = await mlResponse.json() as Record<string, unknown>;
      } catch (err: any) {
        console.error("ML service unreachable:", err.message);
        return res.status(503).json({
          error: "ML service unavailable. Start it with: uvicorn ml-service.api.main:app --port 8001",
        });
      }

      // 2. Gemini — plain-language report only (not classification)
      let stakeholderReport = "";
      try {
        // Strip the large base64 heatmap from what we send to Gemini
        const { gradcam_heatmap_b64, ...mlResultForGemini } = mlResult;
        stakeholderReport = await generateStakeholderReport(mlResultForGemini);
      } catch (err: any) {
        console.warn("Gemini report generation failed:", err.message);
        stakeholderReport = "Stakeholder report unavailable (Gemini API error).";
      }

      // 3. SHA-256 integrity hash (NOT blockchain — tamper-evident log)
      const resultJson = JSON.stringify(mlResult);
      const integrityHash = sha256(file.buffer, resultJson);
      const timestamp = new Date().toISOString();

      // Append to append-only log
      const logEntry = JSON.stringify({
        hash:      integrityHash,
        timestamp,
        predicted_class: mlResult.predicted_class,
        eti_score:       (mlResult.eti as any)?.score,
      });
      try {
        appendFileSync(HASH_LOG, logEntry + "\n", "utf8");
      } catch (e) {
        console.warn("Could not write hash log:", e);
      }

      // 4. Return combined response
      res.json({
        ...mlResult,
        stakeholderReport,
        integrityHash,
        hashNote: "SHA-256(image bytes + result JSON). Stored in ml-service/hash_log.jsonl.",
        timestamp,
        imageUrl: `data:${file.mimetype};base64,${file.buffer.toString("base64")}`,
      });
    } catch (error) {
      console.error("Analysis error:", error);
      res.status(500).json({ error: "Analysis failed" });
    }
  });

  // ── GET /api/health ───────────────────────────────────────────────────
  app.get("/api/health", async (req, res) => {
    let mlServiceStatus = "unknown";
    try {
      const r = await fetch(`${ML_URL}/health`, { signal: AbortSignal.timeout(2000) });
      const body = await r.json() as Record<string, unknown>;
      mlServiceStatus = body.status as string ?? "unknown";
    } catch {
      mlServiceStatus = "unreachable";
    }
    res.json({
      status:         "ok",
      mlService:      mlServiceStatus,
      mlServiceUrl:   ML_URL,
    });
  });

  // ── Vite dev middleware / static production ───────────────────────────
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Express server → http://localhost:${PORT}`);
    console.log(`ML service URL → ${ML_URL}`);
    console.log(`Hash log       → ${HASH_LOG}`);
  });
}

startServer();
