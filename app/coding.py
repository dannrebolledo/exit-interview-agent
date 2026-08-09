"""
Turn an exit interview transcript into structured codes.

Uses Groq because it's free at this volume and fast enough that coding can
happen inline on the post-call webhook rather than as a batch job.

A note on why this is an LLM job at all: manual coding of exit interviews is
the standard approach and it is why most organisations code a sample rather
than the population. Automating it is what makes 100% coverage possible. The
trade-off is that you inherit the model's judgement, which is why the prompt
pushes hard toward "Unclear" over inference — an under-coded interview is
recoverable, a confidently wrong one quietly corrupts the aggregate.
"""

from __future__ import annotations

import json
import os
import re
from typing import Optional

import httpx

from .schema import build_coding_prompt

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


class CodingError(RuntimeError):
    pass


def _extract_json(text: str) -> dict:
    """Models wrap JSON in fences and preamble no matter how firmly you ask
    them not to. Strip it rather than failing the whole interview."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise CodingError(f"No JSON object found in model output: {text[:200]}")
    return json.loads(text[start:end + 1])


def code_transcript(transcript: str, timeout: float = 45.0) -> dict:
    if not GROQ_API_KEY:
        raise CodingError("GROQ_API_KEY is not set")
    if not transcript or len(transcript.strip()) < 80:
        raise CodingError("Transcript too short to code meaningfully")

    payload = {
        "model": GROQ_MODEL,
        "temperature": 0.1,          # coding should be reproducible
        "max_tokens": 900,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system",
             "content": "You are a careful qualitative coder. You return only valid JSON."},
            {"role": "user", "content": build_coding_prompt(transcript)},
        ],
    }

    with httpx.Client(timeout=timeout) as client:
        r = client.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}",
                     "Content-Type": "application/json"},
            json=payload,
        )
    if r.status_code != 200:
        raise CodingError(f"Groq returned {r.status_code}: {r.text[:300]}")

    content = r.json()["choices"][0]["message"]["content"]
    coding = _extract_json(content)
    return _normalise(coding)


def _normalise(coding: dict) -> dict:
    """Defensive tidy-up. Models occasionally return a string where the schema
    says array, or invent a category. Neither should break the aggregate."""
    from .schema import (PRIMARY_DRIVERS, PREVENTABILITY, REGRETTABLE,
                         INTENT_TIMING, TRIGGER_TYPE, SENTIMENT)

    def clamp(value, allowed, default="Unclear"):
        if isinstance(value, str):
            for a in allowed:
                if value.strip().lower() == a.lower():
                    return a
        return default if default in allowed else allowed[-1]

    secondary = coding.get("secondary_drivers") or []
    if isinstance(secondary, str):
        secondary = [secondary]
    secondary = [d for d in secondary
                 if isinstance(d, str) and d in PRIMARY_DRIVERS][:3]

    themes = coding.get("themes") or []
    if isinstance(themes, str):
        themes = [themes]
    themes = [str(t).strip().lower() for t in themes][:5]

    return {
        "primary_driver": clamp(coding.get("primary_driver"), PRIMARY_DRIVERS,
                                default="Personal circumstances"),
        "secondary_drivers": secondary,
        "preventability": clamp(coding.get("preventability"), PREVENTABILITY),
        "regrettable": clamp(coding.get("regrettable"), REGRETTABLE),
        "intent_timing": clamp(coding.get("intent_timing"), INTENT_TIMING),
        "trigger_type": clamp(coding.get("trigger_type"), TRIGGER_TYPE),
        "overall_sentiment": clamp(coding.get("overall_sentiment"), SENTIMENT,
                                   default="Mixed"),
        "manager_sentiment": clamp(coding.get("manager_sentiment"),
                                   SENTIMENT + ["Not discussed"],
                                   default="Not discussed"),
        "would_return": coding.get("would_return"),
        "themes": themes,
        "key_verbatim": str(coding.get("key_verbatim") or "")[:300],
        "summary": str(coding.get("summary") or "")[:600],
    }
