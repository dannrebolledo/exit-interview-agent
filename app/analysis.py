"""
Aggregate analysis over coded exit interviews.

The point of coding every interview rather than a sample is that you can then
ask population-level questions. Three that matter:

1. What proportion of leaving was preventable? A turnover number that mixes
   "relocating to Scotland" with "supervisor is difficult" is not actionable.
   Splitting it changes the conversation from "turnover is 24%" to "roughly
   half of it we could have done something about".

2. How long is the intervention window? Intent-to-leave timing tells you how
   much warning you had. If people decide at month one and leave at month six,
   you have five months of signal you're currently ignoring.

3. Does the qualitative signal agree with the quantitative one? If attrition
   data flags a site and exit interviews from that site cluster on one theme,
   that's a finding. If they don't agree, one of them is measuring something
   you haven't understood yet.
"""

from __future__ import annotations

from collections import Counter
from typing import Optional

from . import store

# Ordered so charts and summaries read chronologically rather than by volume
INTENT_ORDER = [
    "Before starting", "Within first month", "One to three months",
    "Three to six months", "Six to twelve months", "Over a year", "Unclear",
]

EARLY_INTENT = {"Before starting", "Within first month", "One to three months"}


def _codes(rows: list[dict], field: str) -> Counter:
    return Counter(r["coding"].get(field) for r in rows if r["coding"].get(field))


def _pct(n: int, d: int) -> float:
    return round(n / d * 100, 1) if d else 0.0


def overview(site: Optional[str] = None, shift: Optional[str] = None) -> dict:
    rows = store.all_interviews(site, shift)
    n = len(rows)
    if n == 0:
        return {"interviews": 0, "message": "No interviews match that filter."}

    prevent = _codes(rows, "preventability")
    preventable = prevent.get("Preventable", 0) + prevent.get("Partially preventable", 0)

    drivers = _codes(rows, "primary_driver")
    intent = _codes(rows, "intent_timing")
    early_intent = sum(v for k, v in intent.items() if k in EARLY_INTENT)

    returns = [r["coding"].get("would_return") for r in rows]
    would_return = sum(1 for x in returns if x is True)
    return_asked = sum(1 for x in returns if x is not None)

    return {
        "scope": " ".join(filter(None, [site, shift])) or "All sites",
        "interviews": n,
        "preventable_pct": _pct(preventable, n),
        "preventability_breakdown": dict(prevent),
        "top_drivers": [{"driver": d, "count": c, "pct": _pct(c, n)}
                        for d, c in drivers.most_common(5)],
        "early_intent_pct": _pct(early_intent, n),
        "intent_timing": {k: intent.get(k, 0) for k in INTENT_ORDER if intent.get(k)},
        "sentiment": dict(_codes(rows, "overall_sentiment")),
        "manager_sentiment": dict(_codes(rows, "manager_sentiment")),
        "would_return_pct": _pct(would_return, return_asked),
        "median_tenure_months": _median([r["tenure_months"] for r in rows
                                         if r["tenure_months"] is not None]),
    }


def _median(vals: list) -> Optional[float]:
    if not vals:
        return None
    s = sorted(vals)
    m = len(s) // 2
    return float(s[m]) if len(s) % 2 else round((s[m - 1] + s[m]) / 2, 1)


def themes(site: Optional[str] = None, shift: Optional[str] = None,
           limit: int = 12) -> dict:
    rows = store.all_interviews(site, shift)
    c = Counter()
    for r in rows:
        for t in r["coding"].get("themes", []):
            c[t] += 1
    return {
        "scope": " ".join(filter(None, [site, shift])) or "All sites",
        "interviews": len(rows),
        "themes": [{"theme": t, "count": n, "pct": _pct(n, len(rows))}
                   for t, n in c.most_common(limit)],
    }


def by_segment(min_interviews: int = 8) -> dict:
    """Where is preventable leaving concentrated?

    The threshold matters more than it looks. With a low minimum, a segment
    with four interviews and four preventable codes reports 100% and tops the
    ranking on noise alone. Anyone reading the output would chase the wrong
    site. Segments below the threshold are still returned, flagged and
    unranked, because silently dropping them is its own kind of lie.
    """
    rows = store.all_interviews()
    buckets: dict[tuple, list] = {}
    for r in rows:
        key = (r["site"], r["shift_pattern"])
        buckets.setdefault(key, []).append(r)

    ranked, below = [], []
    for (site, shift), group in buckets.items():
        prevent = _codes(group, "preventability")
        preventable = prevent.get("Preventable", 0) + prevent.get("Partially preventable", 0)
        drivers = _codes(group, "primary_driver")
        intent = _codes(group, "intent_timing")
        early = sum(v for k, v in intent.items() if k in EARLY_INTENT)
        top = drivers.most_common(1)[0] if drivers else ("Unclear", 0)

        entry = {
            "site": site,
            "shift": shift,
            "interviews": len(group),
            "preventable_count": preventable,
            "preventable_pct": _pct(preventable, len(group)),
            "early_intent_pct": _pct(early, len(group)),
            "top_driver": top[0],
            "top_driver_pct": _pct(top[1], len(group)),
        }
        (ranked if len(group) >= min_interviews else below).append(entry)

    # Rank on preventable volume first, rate second. A segment losing twelve
    # people preventably matters more than one losing three, even at a lower
    # percentage.
    ranked.sort(key=lambda x: (x["preventable_count"], x["preventable_pct"]), reverse=True)
    below.sort(key=lambda x: x["interviews"], reverse=True)

    return {
        "segments": ranked,
        "below_threshold": below,
        "min_interviews": min_interviews,
        "note": f"Segments with fewer than {min_interviews} interviews are listed "
                f"separately and not ranked — percentages on small samples are unstable.",
    }


def verbatims(site: Optional[str] = None, shift: Optional[str] = None,
              driver: Optional[str] = None, limit: int = 8) -> dict:
    rows = store.all_interviews(site, shift)
    if driver:
        rows = [r for r in rows
                if r["coding"].get("primary_driver", "").lower() == driver.lower()]
    out = []
    for r in rows[:limit]:
        q = r["coding"].get("key_verbatim")
        if q:
            out.append({
                "quote": q,
                "site": r["site"],
                "shift": r["shift_pattern"],
                "tenure_months": r["tenure_months"],
                "driver": r["coding"].get("primary_driver"),
            })
    return {"verbatims": out, "count": len(out)}


def headline() -> dict:
    """The one-paragraph version, for the top of the dashboard."""
    o = overview()
    seg = by_segment()["segments"]
    if not seg or o.get("interviews", 0) == 0:
        return {"headline": "No interviews recorded yet.", "detail": []}

    worst = seg[0]
    top_driver = o["top_drivers"][0] if o["top_drivers"] else None
    t = themes(worst["site"], worst["shift"], limit=1)["themes"]
    top_theme = t[0]["theme"] if t else None

    lines = [
        f"{o['preventable_pct']:.0f}% of leaving in this sample was coded as preventable "
        f"or partially preventable, across {o['interviews']} interviews.",
        f"{o['early_intent_pct']:.0f}% of leavers first thought about leaving within "
        f"three months of joining — that is the intervention window.",
    ]
    if top_driver:
        lines.append(f"The most common primary driver is {top_driver['driver'].lower()} "
                     f"at {top_driver['pct']:.0f}%.")
    lines.append(f"Preventable leaving is most concentrated at {worst['site']} "
                 f"{worst['shift'].lower()} shift ({worst['preventable_pct']:.0f}%), "
                 f"driven by {worst['top_driver'].lower()}.")
    if top_theme:
        lines.append(f'The recurring theme there is "{top_theme}".')

    return {"headline": " ".join(lines[:2]), "detail": lines}
