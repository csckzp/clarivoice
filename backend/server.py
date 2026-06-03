import threading
import uuid
from pathlib import Path
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from denoise import denoise
from polish import polish

app = FastAPI(title="ClarIvoice Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

jobs: Dict[str, dict] = {}


class ProcessRequest(BaseModel):
    file_path: str
    output_format: str = "wav"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/process")
def process(req: ProcessRequest):
    if not Path(req.file_path).is_file():
        raise HTTPException(status_code=400, detail="File not found")

    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "pending",
        "progress": 0,
        "message": "Queued",
        "output_file": None,
        "error": None,
    }

    t = threading.Thread(
        target=_run_pipeline,
        args=(job_id, req.file_path, req.output_format),
        daemon=True,
    )
    t.start()

    return {"job_id": job_id}


@app.get("/status/{job_id}")
def get_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]


@app.get("/download/{job_id}")
def download(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    job = jobs[job_id]
    if job["status"] != "complete":
        raise HTTPException(status_code=400, detail="Job not complete")
    out = job["output_file"]
    return FileResponse(
        path=out,
        filename=Path(out).name,
        media_type="application/octet-stream",
    )


def _progress(job_id: str):
    def cb(pct: int, msg: str):
        jobs[job_id]["progress"] = pct
        jobs[job_id]["message"] = msg

    return cb


def _run_pipeline(job_id: str, input_path: str, output_format: str):
    cb = _progress(job_id)
    try:
        jobs[job_id]["status"] = "processing"
        cb(5, "Starting pipeline...")

        denoised = denoise(input_path, job_id, cb)
        polished = polish(denoised, job_id, output_format, cb)

        jobs[job_id]["status"] = "complete"
        jobs[job_id]["output_file"] = polished
        cb(100, "Done!")
    except Exception as exc:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(exc)
        jobs[job_id]["message"] = f"Error: {exc}"
