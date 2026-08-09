"""
The coding frame for exit interviews.

This is the analytical core of the whole thing. A voice agent that collects
beautiful conversations and produces an unstructured pile of transcripts has
not helped anyone. The value is created here, in the decision about what to
code and how.

Two fields do most of the work:

`preventability` — whether the organisation could realistically have kept this
person. Exit reporting that doesn't separate preventable from unpreventable
leaving produces a number nobody can act on, because "people leave for personal
reasons" and "people leave because their manager is difficult" arrive in the
same bucket.

`intent_timing` — how long before resigning the person first started thinking
about it. This is the single most useful question in exit interviewing and it
is almost never asked. It tells you the size of your intervention window. If
people decide at four months and leave at nine, you have five months of warning
you are currently doing nothing with.
"""

PRIMARY_DRIVERS = [
    "Compensation and benefits",
    "Career progression",
    "Management relationship",
    "Workload and pressure",
    "Shift pattern and hours",
    "Commute and location",
    "Role expectations mismatch",
    "Team and culture",
    "Job security",
    "Onboarding and training",
    "Health and wellbeing",
    "Personal circumstances",
    "Better external offer",
]

PREVENTABILITY = [
    "Preventable",           # org action could plausibly have retained them
    "Partially preventable",  # some factors in scope, some not
    "Not preventable",        # relocation, health, career change, retirement
    "Unclear",
]

REGRETTABLE = ["Regrettable", "Non-regrettable", "Unclear"]

INTENT_TIMING = [
    "Before starting",        # they knew during onboarding — a hiring/RJP failure
    "Within first month",
    "One to three months",
    "Three to six months",
    "Six to twelve months",
    "Over a year",
    "Unclear",
]

TRIGGER_TYPE = [
    "Specific incident",
    "Gradual accumulation",
    "External opportunity",
    "Personal circumstance",
    "Unclear",
]

SENTIMENT = ["Positive", "Mixed", "Negative"]


CODING_SCHEMA = {
    "primary_driver": PRIMARY_DRIVERS,
    "secondary_drivers": PRIMARY_DRIVERS,
    "preventability": PREVENTABILITY,
    "regrettable": REGRETTABLE,
    "intent_timing": INTENT_TIMING,
    "trigger_type": TRIGGER_TYPE,
    "overall_sentiment": SENTIMENT,
    "manager_sentiment": SENTIMENT + ["Not discussed"],
}


CODING_PROMPT = """You are coding an exit interview transcript for a workforce
analytics team. Return ONLY a JSON object, no preamble, no markdown fences.

Code strictly from what the person actually said. Do not infer motives they did
not express. Where the transcript does not support a judgement, use "Unclear"
rather than guessing — a missing code is recoverable, a wrong one is not.

Fields:

- primary_driver: the single most important reason they left. One of:
  {primary_drivers}

- secondary_drivers: array of 0-3 other contributing reasons, same list.
  Only include reasons they actually raised.

- preventability: could the organisation realistically have retained them?
  One of: {preventability}

- regrettable: would the organisation want to have kept this person, based on
  any signal in the transcript about their performance or contribution? One of:
  {regrettable}

- intent_timing: how long into their tenure did they first start thinking
  about leaving? One of: {intent_timing}

- trigger_type: what moved them from thinking about it to acting? One of:
  {trigger_type}

- overall_sentiment: their overall tone about the organisation. One of:
  {sentiment}

- manager_sentiment: their tone specifically about their line manager. One of:
  {manager_sentiment}

- would_return: true, false, or null if not discussed

- themes: array of 2-5 short theme labels in your own words, lower case,
  e.g. "night bus stopped running", "no handover on first shift"

- key_verbatim: the single most useful direct quote from the transcript, under
  30 words, quoted exactly

- summary: two sentences, factual, no editorialising

Transcript:
---
{transcript}
---"""


def build_coding_prompt(transcript: str) -> str:
    return CODING_PROMPT.format(
        primary_drivers=" | ".join(PRIMARY_DRIVERS),
        preventability=" | ".join(PREVENTABILITY),
        regrettable=" | ".join(REGRETTABLE),
        intent_timing=" | ".join(INTENT_TIMING),
        trigger_type=" | ".join(TRIGGER_TYPE),
        sentiment=" | ".join(SENTIMENT),
        manager_sentiment=" | ".join(SENTIMENT + ["Not discussed"]),
        transcript=transcript.strip(),
    )
