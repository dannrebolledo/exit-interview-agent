"""
Create or update the exit interview agent on ElevenLabs, from code.

Why bother when you could click through their dashboard: the system prompt is
the most important artefact in this project and the one you'll iterate on most.
Keeping it in the repo means changes are diffable, reviewable and revertible.
Clicking it into a web form means the version you demoed and the version you
described are gradually different and you won't know which.

Usage:

    export ELEVENLABS_API_KEY=sk_...

    # Create it
    python scripts/create_agent.py --create

    # Push prompt changes to an existing agent
    python scripts/create_agent.py --update AGENT_ID

    # See what would be sent without sending it
    python scripts/create_agent.py --dry-run

The prompt lives in prompts/exit_interview.md so you can edit it without
touching Python.
"""

import argparse
import json
import os
import sys
from pathlib import Path

import httpx

API_BASE = "https://api.elevenlabs.io/v1/convai"
API_KEY = os.getenv("ELEVENLABS_API_KEY", "")

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "exit_interview.md"

# Voice: a calm, neutral British voice suits this better than anything bright.
# Browse voices at elevenlabs.io/app/voice-library and swap the ID.
DEFAULT_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "XrExE9yKIg1WjnnlVkGX")  # Matilda

FIRST_MESSAGE = (
    "Thanks for making the time. Before we start — this is recorded, and the "
    "transcript is used to improve how we work. Your answers are reported in "
    "aggregate, not attributed to you individually. You can skip any question "
    "or stop at any point. Is that okay?"
)


def load_prompt() -> str:
    if not PROMPT_PATH.exists():
        sys.exit(f"Prompt file not found: {PROMPT_PATH}")
    text = PROMPT_PATH.read_text(encoding="utf-8").strip()
    if len(text) < 200:
        sys.exit("Prompt looks suspiciously short — check the file.")
    return text


def build_config() -> dict:
    return {
        "name": "Exit Interview — Meridian Logistics",
        "tags": ["exit-interview", "people-analytics", "demo"],
        "conversation_config": {
            "agent": {
                # Fixed first message so consent cannot be skipped by the model
                # deciding to open differently on a given run.
                "first_message": FIRST_MESSAGE,
                "language": "en",
                "prompt": {
                    "prompt": load_prompt(),
                    # This use case needs judgement — when to probe, when to
                    # stop, when someone is upset. Worth a capable model.
                    "llm": os.getenv("ELEVENLABS_LLM", "gpt-4o"),
                    "temperature": 0.3,
                    "max_tokens": 180,
                },
            },
            "tts": {
                "voice_id": DEFAULT_VOICE_ID,
                # Flash is real-time. The expressive models add latency that
                # makes a sensitive conversation feel stilted.
                "model_id": "eleven_flash_v2_5",
                "stability": 0.6,
                "similarity_boost": 0.75,
            },
            "turn": {
                # Deliberately long. People pause when thinking about something
                # difficult and cutting them off is exactly the wrong behaviour
                # in an exit interview.
                "turn_timeout": 14,
            },
        },
    }


def request(method: str, path: str, payload: dict | None = None) -> dict:
    if not API_KEY:
        sys.exit("ELEVENLABS_API_KEY is not set.")
    url = f"{API_BASE}{path}"
    with httpx.Client(timeout=60) as c:
        r = c.request(
            method, url,
            headers={"xi-api-key": API_KEY, "Content-Type": "application/json"},
            json=payload,
        )
    if r.status_code >= 400:
        print(f"\nHTTP {r.status_code} from {url}")
        try:
            print(json.dumps(r.json(), indent=2)[:2000])
        except json.JSONDecodeError:
            print(r.text[:1000])
        print("\nIf this is a 422, the config schema has moved since this script "
              "was written. Check elevenlabs.io/docs/api-reference/agents/create "
              "and adjust build_config(). The error above names the offending field.")
        sys.exit(1)
    return r.json()


def main():
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--create", action="store_true", help="Create a new agent")
    g.add_argument("--update", metavar="AGENT_ID", help="Update an existing agent")
    g.add_argument("--dry-run", action="store_true", help="Print the payload only")
    g.add_argument("--list", action="store_true", help="List your agents")
    args = p.parse_args()

    if args.dry_run:
        cfg = build_config()
        cfg["conversation_config"]["agent"]["prompt"]["prompt"] = (
            cfg["conversation_config"]["agent"]["prompt"]["prompt"][:300] + "\n... [truncated]")
        print(json.dumps(cfg, indent=2))
        return

    if args.list:
        data = request("GET", "/agents")
        agents = data.get("agents", [])
        if not agents:
            print("No agents found.")
        for a in agents:
            print(f"{a.get('agent_id')}  {a.get('name')}")
        return

    if args.create:
        result = request("POST", "/agents/create", build_config())
        agent_id = result.get("agent_id")
        print(f"\nCreated agent: {agent_id}")
        print("\nNext:")
        print(f"  1. Set ELEVENLABS_AGENT_ID={agent_id} on Render to embed the widget")
        print( "  2. In the dashboard, set the post-call webhook to:")
        print( "     https://YOUR_APP.onrender.com/webhook/post-call")
        print( "  3. Make the agent public if you want the widget to work for others")
        print(f"\n  Test it now: https://elevenlabs.io/app/agents/{agent_id}")
        return

    if args.update:
        result = request("PATCH", f"/agents/{args.update}", build_config())
        print(f"Updated agent {result.get('agent_id', args.update)}")
        print("Prompt changes are live immediately.")


if __name__ == "__main__":
    main()
