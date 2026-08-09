"""
Exit interview pipeline.

    Voice ──▶ ElevenLabs agent ──▶ post-call webhook ──▶ Groq coding ──▶ SQLite
                                                                          │
                                                              aggregate ◀─┘
                                                              dashboard

The agent conducts the interview. This service receives the transcript when the
call ends, codes it against a fixed frame, stores it, and exposes the aggregate.

The interesting inversion is that voice is the *input* here. Everywhere else in
analytics, voice is a worse way to deliver something a screen does better. For
collecting qualitative data at scale it's the other way round — people say more
out loud than they type, they elaborate when prompted, and they'll tell an
agent things they won't put in a form their manager might read.
"""

import hashlib
import hmac
import os
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from . import analysis, coding, store

app = FastAPI(title="Exit Interview Pipeline", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

WEBHOOK_SECRET = os.getenv("ELEVENLABS_WEBHOOK_SECRET", "")


@app.on_event("startup")
def _startup():
    store.init()


# ── Post-call webhook ─────────────────────────────────────────────────
def _verify(body: bytes, signature: Optional[str]) -> bool:
    """ElevenLabs signs post-call webhooks with an HMAC. Without verification
    anyone who finds the URL can inject fabricated interviews into the
    aggregate, which is a worse failure than the endpoint being down."""
    if not WEBHOOK_SECRET:
        return True  # unset in local dev
    if not signature:
        return False
    expected = hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    provided = signature.split("=")[-1].strip()
    return hmac.compare_digest(expected, provided)


def _flatten_transcript(payload: dict) -> str:
    """ElevenLabs sends the transcript as a list of turns."""
    turns = payload.get("transcript") or payload.get("data", {}).get("transcript") or []
    if isinstance(turns, str):
        return turns
    lines = []
    for t in turns:
        role = t.get("role", "")
        msg = (t.get("message") or "").strip()
        if not msg:
            continue
        speaker = "Agent" if role in ("agent", "assistant") else "Leaver"
        lines.append(f"{speaker}: {msg}")
    return "\n".join(lines)


@app.post("/webhook/post-call")
async def post_call(request: Request,
                    elevenlabs_signature: Optional[str] = Header(None)):
    raw = await request.body()
    if not _verify(raw, elevenlabs_signature):
        raise HTTPException(status_code=401, detail="Bad signature")

    payload = await request.json()
    data = payload.get("data", payload)

    conversation_id = data.get("conversation_id") or data.get("conversationId") or ""
    transcript = _flatten_transcript(payload)

    # Dynamic variables are set when the call is initiated, so the segment is
    # known without asking the leaver to state it.
    meta = data.get("conversation_initiation_client_data", {}).get("dynamic_variables", {}) or {}

    if not transcript.strip():
        return {"status": "ignored", "reason": "empty transcript"}

    # Consent is checked by the agent at the top of the call and written to a
    # dynamic variable. An interview without consent is discarded, not stored
    # and hidden — the transcript should not exist.
    if str(meta.get("consent_given", "true")).lower() in ("false", "no", "0"):
        return {"status": "discarded", "reason": "consent not given"}

    try:
        codes = coding.code_transcript(transcript)
    except coding.CodingError as e:
        # Store the transcript uncoded rather than losing it. A failed coding
        # run is recoverable later; a lost interview is not.
        store.save_interview(
            conversation_id=conversation_id, transcript=transcript,
            coding={"coding_error": str(e)},
            site=meta.get("site"), shift_pattern=meta.get("shift_pattern"),
            department=meta.get("department"),
            tenure_months=_int(meta.get("tenure_months")),
            duration_seconds=_int(data.get("metadata", {}).get("call_duration_secs")),
        )
        return {"status": "stored_uncoded", "error": str(e)}

    row_id = store.save_interview(
        conversation_id=conversation_id,
        transcript=transcript,
        coding=codes,
        site=meta.get("site"),
        shift_pattern=meta.get("shift_pattern"),
        department=meta.get("department"),
        tenure_months=_int(meta.get("tenure_months")),
        duration_seconds=_int(data.get("metadata", {}).get("call_duration_secs")),
    )
    return {"status": "ok", "id": row_id, "primary_driver": codes["primary_driver"]}


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


# ── Analysis API ──────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "interviews": store.count()}


@app.get("/api/overview")
def api_overview(site: Optional[str] = None, shift: Optional[str] = None):
    return analysis.overview(site, shift)


@app.get("/api/segments")
def api_segments(min_interviews: int = 8):
    return analysis.by_segment(min_interviews)


@app.get("/api/themes")
def api_themes(site: Optional[str] = None, shift: Optional[str] = None):
    return analysis.themes(site, shift)


@app.get("/api/verbatims")
def api_verbatims(site: Optional[str] = None, shift: Optional[str] = None,
                  driver: Optional[str] = None):
    return analysis.verbatims(site, shift, driver)


@app.get("/api/headline")
def api_headline():
    return analysis.headline()


# ── Dashboard ─────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def dashboard():
    agent_id = os.getenv("ELEVENLABS_AGENT_ID", "")
    o = analysis.overview()
    head = analysis.headline()
    seg = analysis.by_segment()["segments"]
    th = analysis.themes()["themes"]

    if o.get("interviews", 0) == 0:
        return HTMLResponse("<p style='font-family:sans-serif;padding:3rem'>"
                            "No interviews yet. Run <code>python scripts/seed_interviews.py</code>.</p>")

    drivers_html = "".join(
        f"""<div class="bar-row">
              <span class="bar-label">{d['driver']}</span>
              <div class="bar-track"><div class="bar-fill" style="width:{min(d['pct']*3.2, 100)}%"></div></div>
              <span class="bar-val">{d['pct']:.0f}%</span>
            </div>"""
        for d in o["top_drivers"])

    intent_html = "".join(
        f"""<div class="bar-row">
              <span class="bar-label">{k}</span>
              <div class="bar-track"><div class="bar-fill alt" style="width:{min(v/o['interviews']*100*3.2, 100)}%"></div></div>
              <span class="bar-val">{v}</span>
            </div>"""
        for k, v in o["intent_timing"].items())

    seg_html = "".join(
        f"""<tr class="{'flag' if i == 0 else ''}">
              <td>{s['site']}</td><td>{s['shift']}</td><td class="num">{s['interviews']}</td>
              <td class="num">{s['preventable_count']}</td>
              <td class="num">{s['preventable_pct']:.0f}%</td>
              <td class="num">{s['early_intent_pct']:.0f}%</td>
              <td>{s['top_driver']}</td>
            </tr>"""
        for i, s in enumerate(seg[:10]))

    themes_html = "".join(
        f'<span class="chip">{t["theme"]} <b>{t["count"]}</b></span>' for t in th[:14])

    widget = (f'<elevenlabs-convai agent-id="{agent_id}"></elevenlabs-convai>'
              f'<script src="https://unpkg.com/@elevenlabs/convai-widget-embed" async '
              f'type="text/javascript"></script>') if agent_id else ""

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Exit interviews — Meridian Logistics</title>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{{--bg:#f4efe8;--surface:#fbf8f4;--ink:#1b1714;--muted:#7a6c5f;
--accent:#9b4f2e;--accent-soft:#e8d3c6;--line:#ddd0c2;--flag:#f5e6dd;}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--ink);font-family:Inter,system-ui,sans-serif;
line-height:1.6;padding:2.5rem 1.5rem 4rem}}
.wrap{{max-width:940px;margin:0 auto}}
.eyebrow{{font-size:.68rem;letter-spacing:.14em;text-transform:uppercase;
color:var(--accent);margin-bottom:.6rem}}
h1{{font-family:Fraunces,Georgia,serif;font-weight:700;font-size:clamp(1.8rem,4vw,2.5rem);
line-height:1.1;margin-bottom:1rem}}
.lede{{color:var(--muted);max-width:60ch;margin-bottom:2.5rem}}
.headline{{background:var(--surface);border:1px solid var(--line);border-left:3px solid var(--accent);
border-radius:12px;padding:1.5rem;margin-bottom:2rem}}
.headline p{{margin-bottom:.5rem;font-size:.95rem}}
.headline p:last-child{{margin-bottom:0}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
gap:1px;background:var(--line);border:1px solid var(--line);border-radius:12px;
overflow:hidden;margin-bottom:2.5rem}}
.stat{{background:var(--surface);padding:1.1rem 1.25rem}}
.stat-v{{font-family:Fraunces,serif;font-weight:700;font-size:1.9rem;color:var(--accent);line-height:1}}
.stat-l{{font-size:.65rem;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin-top:.4rem}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;margin-bottom:2rem}}
@media(max-width:720px){{.grid{{grid-template-columns:1fr}}}}
.card{{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:1.4rem}}
.card h2{{font-family:Fraunces,serif;font-size:1rem;font-weight:600;margin-bottom:1rem}}
.bar-row{{display:grid;grid-template-columns:1fr 90px 42px;gap:.6rem;align-items:center;
margin-bottom:.5rem;font-size:.8rem}}
.bar-label{{color:var(--ink);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.bar-track{{height:6px;background:var(--accent-soft);border-radius:99px;overflow:hidden}}
.bar-fill{{height:100%;background:var(--accent);border-radius:99px}}
.bar-fill.alt{{background:#7a6c5f}}
.bar-val{{text-align:right;color:var(--muted);font-variant-numeric:tabular-nums}}
table{{width:100%;border-collapse:collapse;font-size:.82rem}}
th{{text-align:left;font-size:.62rem;letter-spacing:.09em;text-transform:uppercase;
color:var(--muted);font-weight:600;padding:.5rem .6rem;border-bottom:1px solid var(--line)}}
td{{padding:.55rem .6rem;border-bottom:1px solid var(--line)}}
td.num{{text-align:right;font-variant-numeric:tabular-nums}}
tr.flag td{{background:var(--flag);font-weight:500}}
.chip{{display:inline-block;background:var(--bg);border:1px solid var(--line);
border-radius:99px;padding:.25rem .7rem;font-size:.75rem;margin:0 .35rem .45rem 0}}
.chip b{{color:var(--accent);margin-left:.2rem}}
.note{{font-size:.75rem;color:var(--muted);margin-top:2rem;padding-top:1.5rem;
border-top:1px solid var(--line)}}
</style></head><body><div class="wrap">
<div class="eyebrow">Synthetic data · demonstration</div>
<h1>Exit interviews, conducted by voice and coded at scale</h1>
<p class="lede">A voice agent conducts the interview, the transcript is coded
against a fixed frame, and the aggregate is what you see here. The value isn't
the conversation — it's being able to code every leaver instead of a sample.</p>

<div class="headline">{"".join(f"<p>{l}</p>" for l in head["detail"])}</div>

<div class="stats">
  <div class="stat"><div class="stat-v">{o['interviews']}</div><div class="stat-l">Interviews</div></div>
  <div class="stat"><div class="stat-v">{o['preventable_pct']:.0f}%</div><div class="stat-l">Preventable</div></div>
  <div class="stat"><div class="stat-v">{o['early_intent_pct']:.0f}%</div><div class="stat-l">Decided in first 3 months</div></div>
  <div class="stat"><div class="stat-v">{o['would_return_pct']:.0f}%</div><div class="stat-l">Would return</div></div>
  <div class="stat"><div class="stat-v">{o['median_tenure_months']:.0f}</div><div class="stat-l">Median tenure (months)</div></div>
</div>

<div class="grid">
  <div class="card"><h2>Primary driver</h2>{drivers_html}</div>
  <div class="card"><h2>When they first thought about leaving</h2>{intent_html}</div>
</div>

<div class="card" style="margin-bottom:1.5rem">
  <h2>Preventable leaving by segment</h2>
  <table><thead><tr><th>Site</th><th>Shift</th><th class="num">n</th>
  <th class="num">Prev.</th><th class="num">Prev. %</th><th class="num">Early intent</th>
  <th>Top driver</th></tr></thead><tbody>{seg_html}</tbody></table>
</div>

<div class="card"><h2>Recurring themes</h2>{themes_html}</div>

{widget}
<p class="note">All interviews are synthetic, generated for demonstration. No
real person's exit interview is represented. In a live deployment, consent is
captured at the start of every call, responses are reported in aggregate only,
and segments below a minimum sample size are not reported separately.</p>
</div></body></html>"""
