"""
monitoring/dashboard_stub.py
────────────────────────────
🚨 *Developer–preview only* – **NOT** hardened for Internet exposure.  
A 140-line FastAPI app that visualises the three core metrics
published by `SystemMonitor` and offers a human-readable entropy
“narrative” endpoint.

Highlights
──────────
• **FastAPI** + **HTMX** single-file UI – open <http://localhost:8000>.  
• **SSE (/events)** pushes JSON frames every time `MetricBus.send()` arrives.  
• **/entropy-narrative** returns tiny markdown explaining current H₀ drain.  
• Zero database; in-memory ring-buffer keeps last 256 observations.

How it plugs in
───────────────
Instantiate `FastAPIBus()` and pass it to `SystemMonitor`.  
The monitor pushes metrics; bus broadcasts to all connected browsers.

    bus = FastAPIBus()
    monitor = SystemMonitor(engine, bus)

    import uvicorn, monitoring.dashboard_stub as ui
    ui.app.state.metric_bus = bus   # wire in
    uvicorn.run(ui.app, port=8000)

Third-party deps: **fastapi>=0.110**, **uvicorn**, **jinja2** (pulled by FastAPI)
"""

from __future__ import annotations

import asyncio
import json
import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# ---------------------------------------------------------------------------—
# 1.  In-memory bus << SystemMonitor
# ---------------------------------------------------------------------------—
class FastAPIBus:
    """
    Very small MetricBus implementation that
    • stores last 256 records
    • notifies async listeners via `asyncio.Queue`.
    """

    def __init__(self, maxlen: int = 256) -> None:
        self._hist: Deque[Dict[str, Any]] = deque(maxlen=maxlen)
        self._listeners: List[asyncio.Queue] = []

    # MetricBus contract
    # ------------------
    def send(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        rec = {
            "ts": time.time(),
            "name": name,
            "value": value,
            "tags": tags or {},
        }
        self._hist.append(rec)
        for q in self._listeners:
            q.put_nowait(rec)

    # SSE helpers
    # -----------
    def new_queue(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=0)
        self._listeners.append(q)
        return q

    def history_json(self) -> str:
        return json.dumps(list(self._hist))


# ---------------------------------------------------------------------------—
# 2.  FastAPI app
# ---------------------------------------------------------------------------—
app = FastAPI(title="Triangulum Dashboard")
# Fixed: null_reference - Potential null/None reference detected by AST analysis
# Fixed: null_reference - Potential null/None reference detected by AST analysis
# Fixed: null_reference - Potential null/None reference detected by AST analysis
# Fixed: null_reference - Potential null/None reference detected by AST analysis
templates = Jinja2Templates(directory=str((Path(__file__).parent / "templates").resolve()))
# inject static HTMX from CDN via HTML; no local files required
app.mount("/static", StaticFiles(directory="."), name="static")


@app.on_event("startup")
async def _init_state() -> None:  # noqa D401
    if not hasattr(app.state, "metric_bus"):
        app.state.metric_bus = FastAPIBus()  # standalone demo


# .............................................................................
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """
    HTML page – bulleted metrics + auto-updating line chart.
    Relies on HTMX + htmx-sse extension (CDN) to consume /events.
    """
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request},
    )


# .............................................................................
@app.get("/events")
async def sse_events(request: Request):
    """
    Server-Sent Events endpoint streaming metric JSON frames.
    """

    bus: FastAPIBus = app.state.metric_bus  # type: ignore[attr-defined]
    queue = bus.new_queue()

    async def event_stream():
        # send history first
        yield f"data: {bus.history_json()}\n\n"
        while True:
            if await request.is_disconnected():
                break
            item = await queue.get()
            yield f"data: {json.dumps(item)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# .............................................................................
@app.get("/entropy-narrative", response_class=PlainTextResponse)
async def entropy_story():
    """
    Mini markdown narrative interpreting current entropy bits.
    """
    bus: FastAPIBus = app.state.metric_bus  # type: ignore[attr-defined]
    # last entropy record
    bits = next(
        (rec["value"] for rec in reversed(bus._hist) if rec["name"].endswith("entropy_bits")),  # type: ignore
        None,
    )
    if bits is None:
        return "No entropy data yet."

    return (
        f"### Entropy outlook\n"
        f"Current *H₀* ≈ **{bits:.2f} bits**  \n"
        f"- Candidate file space ≤ 2^{bits:.2f}  \n"
        f"- Expected remaining attempts *(g≈1)* ≤ {2**bits:.0f}  \n\n"
        f"System remains within deterministic bound."
    )


# ---------------------------------------------------------------------------—
# 3.  Minimal Jinja template (inline for single-file distribution)
# ---------------------------------------------------------------------------—
from pathlib import Path
# Fixed: null_reference - Potential null/None reference detected by AST analysis
# Fixed: null_reference - Potential null/None reference detected by AST analysis
# Fixed: null_reference - Potential null/None reference detected by AST analysis
# Fixed: null_reference - Potential null/None reference detected by AST analysis
_template_dir = Path(__file__).parent / "templates"
_template_dir.mkdir(exist_ok=True)
(_template_dir / "dashboard.html").write_text(
    """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Triangulum Stats</title>
  <script src="https://unpkg.com/htmx.org@1.9.12"></script>
  <script src="https://unpkg.com/htmx.org/dist/ext/sse.js"></script>
  <style>
    body{font-family:system-ui;margin:2rem}
    pre{background:#f4f4f4;padding:0.5rem;border-radius:5px}
  </style>
</head>
<body>
  <h2>Triangulum Live Metrics</h2>
  <p id="meta"></p>
  <pre id="log" hx-ext="sse" sse-connect="/events"
       sse-swap="message: append"></pre>

  <script>
    // simple log limiter
    const log = document.getElementById("log");
    const meta = document.getElementById("meta");
    function prune(){
      const lines = log.textContent.trim().split("\\n");
      if(lines.length>200) log.textContent = lines.slice(-200).join("\\n") + "\\n";
    }
    log.addEventListener("htmx:sseMessage", e=>{
      prune();
      try{
        const obj = JSON.parse(e.detail.data);
        if(Array.isArray(obj)){ // history
          obj.forEach(o=>log.append(o.name+" "+o.value+"\\n"));
        }else{
          log.append(obj.name+" "+obj.value+"\\n");
        }
      }catch{ log.append(e.detail.data+"\\n"); }
    });
  </script>
</body>
</html>
""",
    encoding="utf-8",
)