"""
Generate synthetic exit interviews for Meridian Logistics (fictional).

These exist so the aggregate view has something in it. You cannot conduct
sixty real exit interviews to demo a tool, and an empty dashboard demonstrates
nothing.

The distribution is deliberately weighted so that Northgate night shift shows
a commute-and-shift-pattern cluster with very short intent-to-leave timing.
That mirrors the quantitative finding in the companion dataset — the point
being that quantitative and qualitative signals should triangulate. Attrition
data tells you where; exit interviews tell you why. Neither is much use alone.

Transcripts and codings are generated together so they're internally
consistent. The Groq coding path is used for live interviews only.
"""

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import store

SEED = 20260803
random.seed(SEED)

SITES = ["Northgate", "Westbrook", "Southfield", "Eastvale", "Harlow Cross"]
SHIFTS = ["Days", "Lates", "Nights", "Weekend"]
DEPTS = ["Pick & Pack", "Outbound", "Inbound", "Transport", "Engineering", "Support"]

Q = {
    "open": "Thanks for making the time. To start — can you tell me about your decision to leave?",
    "timing": "When did you first start thinking about leaving?",
    "trigger": "Was there a particular moment that made up your mind?",
    "counter": "Is there anything the company could have done differently that would have kept you?",
    "manager": "How would you describe your relationship with your line manager?",
    "onboard": "Thinking back to your first few weeks — how well set up did you feel?",
    "recommend": "Would you recommend working here to someone you know?",
    "close": "Anything else you think we should know?",
}


# ── Story templates by driver ────────────────────────────────────────
STORIES = {
    "commute_nights": {
        "primary_driver": "Commute and location",
        "secondary": ["Shift pattern and hours"],
        "preventability": "Preventable",
        "intent_timing": "Within first month",
        "trigger_type": "Gradual accumulation",
        "sentiment": "Mixed",
        "themes": ["night bus stopped running", "two hour commute home",
                   "shift pattern not explained at interview"],
        "answers": {
            "open": [
                "Honestly it came down to getting home. The shift finishes at six in the morning and the first bus isn't until seven twenty. So I'm sat in the car park for over an hour, every single shift, and then it's another hour on the bus. The job itself was alright. It was the getting there and back that finished me.",
                "It's the travel. I don't drive, and there's no way of getting home from nights without waiting around for ages. By the time I got in I'd lost half the morning. I was shattered all the time and it wasn't the work doing it.",
                "The role was fine, the money was fine. But nobody told me at interview that nights meant I'd be stuck at the site until the buses started. If I'd known that I probably wouldn't have taken it.",
            ],
            "timing": [
                "Pretty much straight away. First or second week I remember thinking, I can't do this for long.",
                "Within the first month. It wasn't a decision as such, more that I knew it wasn't going to work.",
                "Almost immediately if I'm honest. I stuck it out longer than I wanted to because I needed the money.",
            ],
            "trigger": [
                "Not really one thing. It just built up. One morning I was waiting in the rain and thought, that's enough.",
                "I got offered something closer to home. That was the push, but I'd been looking for a while.",
                "My partner started doing more hours so the childcare stopped working with my getting home so late.",
            ],
            "counter": [
                "A shuttle. Even just for the night shift finish. Or if the shift ended at five so I could get the first bus.",
                "Being straight with me at interview would have helped. I'd have made a different choice and not wasted anyone's time.",
                "Honestly, transport. That's it. Everything else I could have lived with.",
            ],
            "manager": [
                "He was fine. Approachable enough. I did mention the travel a couple of times but there wasn't much he could do about it.",
                "Good, actually. No complaints there. She knew a few of us were struggling to get home but it's not her decision is it.",
                "Alright. I didn't see much of him being on nights, but when I did he was reasonable.",
            ],
            "onboard": [
                "The training was okay. Nobody mentioned the transport thing though and I think they knew.",
                "Bit thrown in at the deep end but I picked it up. That wasn't the problem.",
                "Fine on the job itself. Nothing at all about the practical side of doing nights.",
            ],
            "recommend": [
                "For days, yes. For nights I'd tell them to check how they're getting home first.",
                "Depends if they drive. If they drive it's a decent job.",
                "I'd warn them about the shift, but the place itself is alright.",
            ],
            "close": [
                "Just that I'm not the only one. Three of us started around the same time on nights and we've all gone.",
                "It's a shame really because I liked the team.",
                "No, that's it. Thanks for asking though, nobody's asked before.",
            ],
        },
    },
    "expectations": {
        "primary_driver": "Role expectations mismatch",
        "secondary": ["Onboarding and training"],
        "preventability": "Preventable",
        "intent_timing": "Within first month",
        "trigger_type": "Gradual accumulation",
        "sentiment": "Negative",
        "themes": ["job different to advert", "no proper handover", "targets unrealistic for new starters"],
        "answers": {
            "open": [
                "The job wasn't what I was told it would be. I was expecting a lot more variety and it turned out to be the same task all shift. That's fine if you know going in, but I didn't.",
                "I don't think the role was described accurately. The pace was much higher than I was led to believe and the targets applied from week one.",
                "It just wasn't the job I applied for. Simple as that really.",
            ],
            "timing": ["First couple of weeks.", "Within the first month, definitely.",
                       "About three weeks in when I realised it wasn't going to change."],
            "trigger": ["Nothing specific. I just stopped seeing the point.",
                        "I got put on the same line for the fourth week running.",
                        "A friend told me about an opening somewhere else."],
            "counter": ["Be honest in the advert. That's all.",
                        "A proper induction would have helped. And a bit of leeway on targets while you learn.",
                        "Probably not by the time I'd decided. But at the start, yes."],
            "manager": ["Fine personally, but stretched. He had too many people to look after.",
                        "I barely spoke to mine.", "She was okay. Busy."],
            "onboard": ["Not well at all. Half a day and then on the line.",
                        "There wasn't really one. Someone showed me where things were.",
                        "Rushed. I was learning from whoever was next to me."],
            "recommend": ["Not really.", "I'd tell them to ask a lot of questions first.",
                          "Probably not, no."],
            "close": ["No, that's about it.", "Just that the advert should match the job.",
                      "I think you'd keep more people if the first month was better."],
        },
    },
    "progression": {
        "primary_driver": "Career progression",
        "secondary": ["Compensation and benefits"],
        "preventability": "Partially preventable",
        "intent_timing": "Six to twelve months",
        "trigger_type": "External opportunity",
        "sentiment": "Mixed",
        "themes": ["no route to team leader", "applied internally twice", "external role offered more responsibility"],
        "answers": {
            "open": [
                "I've been here nearly three years and I've applied for two team leader roles internally. Both went to external hires. After the second one I started looking properly.",
                "There wasn't anywhere for me to go. I like the place but I'm not going to stand still for another two years.",
                "I got offered a supervisor role elsewhere. I'd have stayed if there'd been something similar here.",
            ],
            "timing": ["After I didn't get the second internal role. So maybe eight months ago.",
                       "About a year ago I started thinking about it seriously.",
                       "Six months or so."],
            "trigger": ["Getting the offer. Before that I was just thinking about it.",
                        "The second rejection, really. That told me what I needed to know.",
                        "A recruiter contacted me and I took the call, which I wouldn't have a year ago."],
            "counter": ["A conversation about where I was going would have helped. Nobody ever had one with me.",
                        "If I'd got either of those roles I'd still be here.",
                        "Some kind of development plan. Anything, really."],
            "manager": ["Good. He supported both applications. It's above him where it went wrong.",
                        "She was great, genuinely. That's the part I'll miss.",
                        "Fine. Not much of a career conversation ever, but no issues."],
            "onboard": ["That was years ago now. It was fine.",
                        "Good, actually. Better than I expected.",
                        "I don't remember any problems with it."],
            "recommend": ["Yes, for a first job. Less so if you want to progress.",
                          "Yeah I would. It's a decent employer.",
                          "For the right person, yes."],
            "close": ["Look at internal candidates properly. That's my only thing.",
                      "No hard feelings, I've enjoyed it mostly.",
                      "Just that people notice when the same roles keep going outside."],
        },
    },
    "manager": {
        "primary_driver": "Management relationship",
        "secondary": ["Team and culture"],
        "preventability": "Preventable",
        "intent_timing": "Three to six months",
        "trigger_type": "Specific incident",
        "sentiment": "Negative",
        "themes": ["favouritism on shift allocation", "raised concern and nothing happened", "spoken to in front of others"],
        "answers": {
            "open": [
                "It was my supervisor, if I'm honest. The way people were spoken to. I raised it once and nothing came of it, so I stopped bothering.",
                "There was a difference in how certain people were treated, particularly around shift swaps and overtime. It wore me down.",
                "I didn't feel respected. That's the short version.",
            ],
            "timing": ["Maybe four months in, once I'd seen the pattern.",
                       "Three or four months.", "About five months in."],
            "trigger": ["I was pulled up in front of the whole shift over something that wasn't my fault.",
                        "There was an incident with overtime allocation and I'd had enough.",
                        "Someone else got the swap I'd asked for first. It sounds small but it was the last one."],
            "counter": ["Someone actually looking into it when I raised it.",
                        "A different supervisor, honestly. The job was fine.",
                        "If HR had followed up I might have stayed."],
            "manager": ["That's the whole reason I'm leaving, so — not good.",
                        "Poor. I don't think he should be managing people.",
                        "Difficult. I got on with everyone else."],
            "onboard": ["Fine. No issues at the start.",
                        "That part was okay.", "Good, actually. It went wrong later."],
            "recommend": ["Not on that shift.", "No.", "Depends who they'd be working for."],
            "close": ["I'd like to think someone looks at it.",
                      "Other people feel the same, they just haven't said.",
                      "No. Thanks for listening."],
        },
    },
    "pay": {
        "primary_driver": "Compensation and benefits",
        "secondary": [],
        "preventability": "Partially preventable",
        "intent_timing": "Six to twelve months",
        "trigger_type": "External opportunity",
        "sentiment": "Mixed",
        "themes": ["agency staff paid more for same role", "no increase in two years", "better rate down the road"],
        "answers": {
            "open": [
                "Money, mainly. There's a place ten minutes further on paying nearly two pounds an hour more for the same work.",
                "I found out the agency lads on my line were on more than me and I'd been here two years. That was hard to take.",
                "I haven't had a rise since I started and everything's gone up. I couldn't keep doing it.",
            ],
            "timing": ["When I found out about the agency rates. Maybe nine months ago.",
                       "Last year some time.", "About eight months ago."],
            "trigger": ["Getting the offer.", "Seeing the vacancy advertised at a higher rate than I'm on.",
                        "Bills, basically. It stopped adding up."],
            "counter": ["Match it, or close to it. I didn't want to leave.",
                        "Just explain the agency thing. Nobody would.",
                        "A rise. It's not complicated."],
            "manager": ["Good. He tried to get me something and couldn't.",
                        "Fine, it's not his call.", "No complaints about her at all."],
            "onboard": ["Fine.", "Good.", "No problems."],
            "recommend": ["Yes, but check the rate against elsewhere first.",
                          "It's a decent place, just not the best paid.",
                          "Yeah, with that caveat."],
            "close": ["Look at what the agencies are getting versus your own people.",
                      "No, that's it.", "I'd come back if the pay was right."],
        },
    },
    "personal": {
        "primary_driver": "Personal circumstances",
        "secondary": [],
        "preventability": "Not preventable",
        "intent_timing": "Three to six months",
        "trigger_type": "Personal circumstance",
        "sentiment": "Positive",
        "themes": ["relocating with family", "returning to study", "caring responsibilities"],
        "answers": {
            "open": [
                "Nothing to do with the job at all. We're moving back closer to my parents, they're getting older and need a hand.",
                "I've got a place at college in September. It's something I've wanted to do for a while.",
                "My partner's job is relocating and we're going with it. I'd have stayed otherwise.",
            ],
            "timing": ["Only when the move came up, so a few months.",
                       "When I applied for the course, around four months ago.",
                       "It wasn't really a decision about the job."],
            "trigger": ["The house sale going through.", "Getting the offer from the college.",
                        "My partner's role being confirmed."],
            "counter": ["Nothing, honestly. It's not about the company.",
                        "No, this one's on me. I've enjoyed working here.",
                        "Not unless you've got a site up there."],
            "manager": ["Really good. He's been supportive about the whole thing.",
                        "Excellent. I'll miss her.", "Very good, no complaints."],
            "onboard": ["Good.", "Really well handled actually.", "Fine, yes."],
            "recommend": ["Definitely.", "Yes, absolutely.", "Yeah I would."],
            "close": ["Just thanks really. It's been a good couple of years.",
                      "I'd come back if we ever moved this way again.",
                      "No, all good."],
        },
    },
}

# Which story fits which segment. Northgate nights is deliberately loaded.
# The commute story is night-shift-only — it's about buses not running after
# a 6am finish, so it cannot coherently appear on a day shift. Letting it leak
# across segments would produce themes that contradict their own transcripts.
SEGMENT_WEIGHTS = {
    ("Northgate", "Nights"): {"commute_nights": 0.50, "expectations": 0.16, "manager": 0.10,
                              "pay": 0.10, "progression": 0.06, "personal": 0.08},
    "_nights_default":       {"commute_nights": 0.16, "pay": 0.20, "personal": 0.20,
                              "progression": 0.16, "manager": 0.14, "expectations": 0.14},
    "_default":              {"progression": 0.22, "pay": 0.20, "personal": 0.26,
                              "manager": 0.13, "expectations": 0.19},
}


def weights_for(site, shift):
    if (site, shift) in SEGMENT_WEIGHTS:
        return SEGMENT_WEIGHTS[(site, shift)]
    if shift == "Nights":
        return SEGMENT_WEIGHTS["_nights_default"]
    return SEGMENT_WEIGHTS["_default"]


def build_transcript(story: dict) -> str:
    a = story["answers"]
    order = ["open", "timing", "trigger", "counter", "manager", "onboard", "recommend", "close"]
    lines = ["Agent: Before we start — this is recorded and the transcript is used to improve how we work. Your answers are reported in aggregate, not attributed to you individually. You can skip anything or stop at any point. Is that okay?",
             "Leaver: Yeah, that's fine."]
    for key in order:
        lines.append(f"Agent: {Q[key]}")
        lines.append(f"Leaver: {random.choice(a[key])}")
    lines.append("Agent: That's really helpful, thank you. All the best with what's next.")
    return "\n".join(lines)


def build_coding(story: dict) -> dict:
    return {
        "primary_driver": story["primary_driver"],
        "secondary_drivers": story["secondary"],
        "preventability": story["preventability"],
        "regrettable": random.choices(["Regrettable", "Non-regrettable", "Unclear"],
                                      weights=[0.45, 0.30, 0.25])[0],
        "intent_timing": story["intent_timing"],
        "trigger_type": story["trigger_type"],
        "overall_sentiment": story["sentiment"],
        "manager_sentiment": ("Negative" if story["primary_driver"] == "Management relationship"
                              else random.choices(["Positive", "Mixed", "Not discussed"],
                                                  weights=[0.5, 0.3, 0.2])[0]),
        "would_return": random.choices([True, False, None], weights=[0.35, 0.45, 0.20])[0],
        "themes": random.sample(story["themes"], k=min(len(story["themes"]),
                                                       random.randint(2, 3))),
        "key_verbatim": random.choice(story["answers"]["open"])[:150],
        "summary": f"Left primarily due to {story['primary_driver'].lower()}. "
                   f"Coded as {story['preventability'].lower()}.",
    }


def generate(n: int = 120):
    store.init()
    # Segment mix roughly follows where leavers actually come from. Scaled so
    # most segments clear the minimum reporting threshold — a demo where only
    # one row is reportable doesn't show the analysis working.
    base = (
        [("Northgate", "Nights")] * 14 +
        [("Northgate", "Days")] * 6 + [("Northgate", "Lates")] * 5 +
        [("Westbrook", "Days")] * 6 + [("Westbrook", "Nights")] * 5 +
        [("Southfield", "Lates")] * 6 + [("Southfield", "Days")] * 5 +
        [("Eastvale", "Days")] * 5 + [("Eastvale", "Weekend")] * 5 +
        [("Harlow Cross", "Lates")] * 5 + [("Harlow Cross", "Nights")] * 4
    )
    segments = base * 2
    random.shuffle(segments)

    written = 0
    for i, (site, shift) in enumerate(segments[:n]):
        w = weights_for(site, shift)
        key = random.choices(list(w.keys()), weights=list(w.values()))[0]
        story = STORIES[key]

        # Tenure correlates with the reason
        if story["intent_timing"] in ("Within first month", "One to three months"):
            tenure = random.randint(1, 7)
        elif story["intent_timing"] == "Three to six months":
            tenure = random.randint(5, 14)
        else:
            tenure = random.randint(12, 46)

        store.save_interview(
            conversation_id=f"seed-{i:04d}",
            transcript=build_transcript(story),
            coding=build_coding(story),
            site=site,
            shift_pattern=shift,
            department=random.choice(DEPTS),
            tenure_months=tenure,
            duration_seconds=random.randint(280, 640),
            consent_given=True,
            source="seed",
        )
        written += 1

    return written


if __name__ == "__main__":
    n = generate()
    print(f"Seeded {n} exit interviews into {store.DB_PATH}")
    print(f"Total in database: {store.count()}")
