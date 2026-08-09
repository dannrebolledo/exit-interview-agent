"""
Simulate an ElevenLabs post-call webhook.

The point of this is to test the coding pipeline before you've built an agent,
and to test it repeatably afterwards. It POSTs a transcript to /webhook/post-call
in exactly the shape ElevenLabs sends, so if this works, a real call will work.

Usage:

    # Use one of the built-in example transcripts
    python scripts/simulate_call.py --example commute
    python scripts/simulate_call.py --example manager
    python scripts/simulate_call.py --example personal

    # Or type your own answers interactively — you play the leaver
    python scripts/simulate_call.py --interactive

    # Point at a deployed instance
    python scripts/simulate_call.py --example commute --url https://your-app.onrender.com

Requires GROQ_API_KEY to be set wherever the server is running, since the
server does the coding, not this script.
"""

import argparse
import json
import sys
import uuid

import httpx

DEFAULT_URL = "http://localhost:8000"

QUESTIONS = [
    "Can you tell me about your decision to leave?",
    "When did you first start thinking about leaving?",
    "Was there a particular moment that made up your mind?",
    "Is there anything the company could have done differently that would have kept you?",
    "How would you describe your relationship with your line manager?",
    "Thinking back to your first few weeks — how well set up did you feel?",
    "Would you recommend working here to someone you know?",
    "Anything else you think we should know?",
]

EXAMPLES = {
    "commute": {
        "meta": {"site": "Northgate", "shift_pattern": "Nights",
                 "department": "Pick & Pack", "tenure_months": 5},
        "answers": [
            "It came down to getting home, really. The shift finishes at six in the morning and the first bus isn't until twenty past seven. So I'm sat in the car park for over an hour every single shift, then another hour on the bus. The job itself was fine. It was the travel that finished me.",
            "Pretty much straight away, first or second week. I knew it wasn't going to work long term.",
            "Not one thing. It built up. One morning I was stood in the rain waiting and I thought, that's enough of this.",
            "A shuttle would have done it. Even just for the night finish. Or being straight with me at interview about what the shift actually meant.",
            "He was alright, no complaints. I mentioned the travel a couple of times but it's not something he can fix.",
            "The training on the job was okay. Nobody said a word about how you'd get home though, and I think they knew.",
            "For days, yes. For nights I'd tell them to work out how they're getting home before they sign anything.",
            "Just that I'm not the only one. Three of us started around the same time on nights and we've all gone now.",
        ],
    },
    "manager": {
        "meta": {"site": "Southfield", "shift_pattern": "Lates",
                 "department": "Outbound", "tenure_months": 9},
        "answers": [
            "Honestly it was my supervisor. The way people got spoken to on shift. I raised it once and nothing happened, so I stopped bothering and started looking.",
            "About four months in, once I'd seen it wasn't a one-off.",
            "I got pulled up in front of the whole shift over something that wasn't my fault. That was the moment.",
            "Someone actually looking into it when I raised it would have helped. The job itself was fine.",
            "That's the reason I'm leaving, so — not good. I got on with everyone else there.",
            "Onboarding was fine, no problems at the start. It went wrong later.",
            "Not on that shift, no.",
            "Other people feel the same, they just haven't said anything. I'd like to think someone looks at it.",
        ],
    },
    "personal": {
        "meta": {"site": "Eastvale", "shift_pattern": "Days",
                 "department": "Transport", "tenure_months": 31},
        "answers": [
            "Nothing to do with the job at all. We're moving back closer to my parents, they're getting on and need a hand.",
            "Only when the move came up, so a few months ago. It wasn't really a decision about work.",
            "The house sale going through, that was it.",
            "Nothing honestly. Unless you've got a site up there. I'd have stayed otherwise.",
            "Really good. He's been supportive about the whole thing.",
            "Good, that was years ago now but it was handled well.",
            "Definitely, yes.",
            "Just thanks really. It's been a good few years.",
        ],
    },
}

CONSENT = ("Thanks for making the time. Before we start — this is recorded, and the "
           "transcript is used to improve how we work. Your answers are reported in "
           "aggregate, not attributed to you individually. You can skip any question "
           "or stop at any point. Is that okay?")


def build_turns(answers: list[str]) -> list[dict]:
    turns = [
        {"role": "agent", "message": CONSENT},
        {"role": "user", "message": "Yeah, that's fine."},
    ]
    for q, a in zip(QUESTIONS, answers):
        turns.append({"role": "agent", "message": q})
        turns.append({"role": "user", "message": a})
    turns.append({"role": "agent",
                  "message": "That's really helpful, thank you. All the best with what's next."})
    return turns


def interactive() -> tuple[list[str], dict]:
    print("\nYou're the leaver. Answer as you like — press Enter to skip a question.\n")
    site = input("Site [Northgate]: ").strip() or "Northgate"
    shift = input("Shift [Nights]: ").strip() or "Nights"
    dept = input("Department [Pick & Pack]: ").strip() or "Pick & Pack"
    tenure = input("Tenure in months [5]: ").strip() or "5"

    answers = []
    for i, q in enumerate(QUESTIONS, 1):
        print(f"\n[{i}/{len(QUESTIONS)}] {q}")
        answers.append(input("> ").strip() or "I'd rather not say.")

    return answers, {"site": site, "shift_pattern": shift,
                     "department": dept, "tenure_months": int(tenure)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--example", choices=list(EXAMPLES), help="Use a built-in transcript")
    p.add_argument("--interactive", action="store_true", help="Type your own answers")
    p.add_argument("--url", default=DEFAULT_URL, help="Base URL of the running service")
    p.add_argument("--show-transcript", action="store_true")
    args = p.parse_args()

    if args.interactive:
        answers, meta = interactive()
    elif args.example:
        ex = EXAMPLES[args.example]
        answers, meta = ex["answers"], ex["meta"]
    else:
        p.error("Pass --example or --interactive")

    turns = build_turns(answers)

    if args.show_transcript:
        print("\n--- transcript ---")
        for t in turns:
            who = "Agent " if t["role"] == "agent" else "Leaver"
            print(f"{who}: {t['message']}")
        print("--- end ---\n")

    # This payload shape mirrors what ElevenLabs actually sends.
    payload = {
        "type": "post_call_transcription",
        "data": {
            "conversation_id": f"sim-{uuid.uuid4().hex[:10]}",
            "metadata": {"call_duration_secs": 60 + len(answers) * 35},
            "conversation_initiation_client_data": {"dynamic_variables": {
                **meta, "consent_given": "true"}},
        },
        "transcript": turns,
    }

    url = args.url.rstrip("/") + "/webhook/post-call"
    print(f"POST {url} ...")
    try:
        r = httpx.post(url, json=payload, timeout=90)
    except httpx.ConnectError:
        print(f"\nCouldn't reach {args.url}. Is the server running?"
              f"\n  uvicorn app.main:app --reload\n")
        sys.exit(1)

    print(f"HTTP {r.status_code}")
    try:
        body = r.json()
    except json.JSONDecodeError:
        print(r.text[:500]); sys.exit(1)

    print(json.dumps(body, indent=2))

    if body.get("status") == "stored_uncoded":
        print("\nThe transcript was stored but coding failed — usually GROQ_API_KEY "
              "is not set on the server. Everything else worked.")
    elif body.get("status") == "ok":
        print(f"\nCoded and stored. Refresh {args.url} to see it in the aggregate.")


if __name__ == "__main__":
    main()
