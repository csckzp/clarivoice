import { useState, useEffect, useCallback, useRef } from "react";
import { listen } from "@tauri-apps/api/event";
import { open } from "@tauri-apps/plugin-dialog";
import "./App.css";

const BACKEND = "http://127.0.0.1:8765";
const AUDIO_EXTS = ["mp3", "wav", "flac", "ogg", "aac", "m4a", "opus", "wma"];

type Phase = "idle" | "file_ready" | "processing" | "complete" | "error";

interface FileInfo {
  path: string;
  name: string;
}

interface JobStatus {
  status: string;
  progress: number;
  message: string;
  output_file: string | null;
  error: string | null;
}

function basename(p: string) {
  return p.split(/[/\\]/).pop() ?? p;
}

export default function App() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [file, setFile] = useState<FileInfo | null>(null);
  const [outputFormat, setOutputFormat] = useState<"wav" | "mp3">("wav");
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [backendReady, setBackendReady] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Poll backend /health until ready ──────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      try {
        const res = await fetch(`${BACKEND}/health`);
        if (res.ok && !cancelled) {
          setBackendReady(true);
          return;
        }
      } catch {
        // not ready yet
      }
      if (!cancelled) setTimeout(check, 1000);
    };
    check();
    return () => { cancelled = true; };
  }, []);

  // ── Tauri drag-and-drop events ────────────────────────────────────────────
  useEffect(() => {
    const unlisteners: Array<() => void> = [];

    (async () => {
      unlisteners.push(
        await listen("tauri://drag-enter", () => setIsDragging(true)),
        await listen("tauri://drag-leave", () => setIsDragging(false)),
        await listen<{ paths: string[] }>("tauri://drag-drop", (evt) => {
          setIsDragging(false);
          const p = evt.payload.paths?.[0];
          if (!p) return;
          const ext = p.split(".").pop()?.toLowerCase() ?? "";
          if (AUDIO_EXTS.includes(ext)) {
            setFile({ path: p, name: basename(p) });
            setPhase("file_ready");
          }
        }),
      );
    })();

    return () => unlisteners.forEach((fn) => fn());
  }, []);

  // ── Poll job status ───────────────────────────────────────────────────────
  useEffect(() => {
    if (!jobId) return;
    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${BACKEND}/status/${jobId}`);
        const data: JobStatus = await res.json();
        setJobStatus(data);
        if (data.status === "complete") {
          clearInterval(pollRef.current!);
          setPhase("complete");
        } else if (data.status === "error") {
          clearInterval(pollRef.current!);
          setPhase("error");
        }
      } catch {
        // backend temporarily unreachable — keep polling
      }
    }, 500);
    return () => clearInterval(pollRef.current!);
  }, [jobId]);

  // ── Actions ───────────────────────────────────────────────────────────────
  const handleBrowse = useCallback(async () => {
    const selected = await open({
      multiple: false,
      filters: [{ name: "Audio", extensions: AUDIO_EXTS }],
    });
    if (typeof selected === "string") {
      setFile({ path: selected, name: basename(selected) });
      setPhase("file_ready");
    }
  }, []);

  const handleProcess = useCallback(async () => {
    if (!file) return;
    setPhase("processing");
    setJobStatus(null);
    try {
      const res = await fetch(`${BACKEND}/process`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_path: file.path, output_format: outputFormat }),
      });
      const data = await res.json();
      if (data.job_id) {
        setJobId(data.job_id);
      } else {
        throw new Error(data.detail ?? "No job ID returned");
      }
    } catch (e) {
      setJobStatus({
        status: "error",
        progress: 0,
        message: String(e),
        output_file: null,
        error: String(e),
      });
      setPhase("error");
    }
  }, [file, outputFormat]);

  const handleReset = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    setPhase("idle");
    setFile(null);
    setJobId(null);
    setJobStatus(null);
  }, []);

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="app">
      <header className="header">
        <div className="logo">
          <span className="logo-wave">≋</span>
          <span className="logo-text">ClarIvoice</span>
        </div>
        <p className="tagline">Restore archival recordings in two clicks</p>
      </header>

      <main className="main">
        {!backendReady && (
          <div className="status-banner">Starting audio engine…</div>
        )}

        {/* ── Idle: drop zone ── */}
        {phase === "idle" && (
          <div
            className={`dropzone${isDragging ? " dragging" : ""}`}
            onClick={handleBrowse}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === "Enter" && handleBrowse()}
          >
            <div className="dropzone-icon">🎙</div>
            <p className="dropzone-primary">Drop your audio file here</p>
            <p className="dropzone-secondary">or click to browse</p>
            <p className="dropzone-formats">MP3 · WAV · FLAC · OGG · AAC · M4A</p>
          </div>
        )}

        {/* ── File selected ── */}
        {phase === "file_ready" && file && (
          <div className="file-ready">
            <div className="file-card">
              <span className="file-icon">🎵</span>
              <div className="file-info">
                <span className="file-name">{file.name}</span>
                <button className="btn-link" onClick={handleReset}>
                  Change
                </button>
              </div>
            </div>

            <div className="format-row">
              <span className="format-label">Output format</span>
              <div className="format-toggle">
                {(["wav", "mp3"] as const).map((fmt) => (
                  <button
                    key={fmt}
                    className={`toggle-btn${outputFormat === fmt ? " active" : ""}`}
                    onClick={() => setOutputFormat(fmt)}
                  >
                    {fmt.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>

            <button
              className="btn-process"
              onClick={handleProcess}
              disabled={!backendReady}
            >
              {backendReady ? "Enhance Audio" : "Starting engine…"}
            </button>
          </div>
        )}

        {/* ── Processing ── */}
        {phase === "processing" && (
          <div className="processing">
            {file && <p className="processing-file">{file.name}</p>}
            <div className="progress-track">
              <div
                className="progress-fill"
                style={{ width: `${jobStatus?.progress ?? 0}%` }}
              />
            </div>
            <p className="processing-msg">
              {jobStatus?.message ?? "Submitting job…"}
            </p>
            <p className="processing-pct">{jobStatus?.progress ?? 0}%</p>
          </div>
        )}

        {/* ── Complete ── */}
        {phase === "complete" && jobId && (
          <div className="complete">
            <div className="complete-check">✓</div>
            <p className="complete-title">Enhancement complete!</p>
            <audio
              className="audio-player"
              controls
              src={`${BACKEND}/download/${jobId}`}
            />
            <a
              className="btn-download"
              href={`${BACKEND}/download/${jobId}`}
              download
            >
              Download enhanced file
            </a>
            <button className="btn-link" onClick={handleReset}>
              Process another file
            </button>
          </div>
        )}

        {/* ── Error ── */}
        {phase === "error" && (
          <div className="error-section">
            <p className="error-title">Processing failed</p>
            <p className="error-msg">
              {jobStatus?.message ?? "An unexpected error occurred."}
            </p>
            <button className="btn-process" onClick={handleReset}>
              Try again
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
