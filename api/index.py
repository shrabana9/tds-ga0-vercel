"""Vercel serverless FastAPI endpoint: POST /api/latency
Body: {"regions": ["emea", "amer"], "threshold_ms": 158}
Returns per-region avg_latency, p95_latency, avg_uptime and breaches computed from the bundled telemetry."""
import json
import math
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

TELEMETRY = json.loads((Path(__file__).parent / "telemetry.json").read_text(encoding="utf-8"))

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], expose_headers=["*"])


class Query(BaseModel):
    regions: list[str]
    threshold_ms: float


def percentile(values, p):
    s = sorted(values)
    r = (len(s) - 1) * p
    lo = math.floor(r)
    frac = r - lo
    return s[lo] + frac * (s[lo + 1] - s[lo]) if lo + 1 < len(s) else s[lo]


def region_stats(region, threshold):
    rows = [t for t in TELEMETRY if t["region"] == region]
    if not rows:
        return {"region": region, "avg_latency": None, "p95_latency": None, "avg_uptime": None, "breaches": 0}
    lat = [t["latency_ms"] for t in rows]
    up = [t["uptime_pct"] for t in rows]
    return {
        "region": region,
        "avg_latency": round(sum(lat) / len(lat), 2),
        "p95_latency": round(percentile(lat, 0.95), 2),
        "avg_uptime": round(sum(up) / len(up), 3),
        "breaches": sum(1 for v in lat if v > threshold),
    }


@app.post("/api/latency")
@app.post("/")
def latency(q: Query):
    return {"regions": [region_stats(r, q.threshold_ms) for r in q.regions]}


@app.get("/api/latency")
@app.get("/")
def info():
    return {"ok": True, "usage": "POST a JSON body with regions and threshold_ms"}
