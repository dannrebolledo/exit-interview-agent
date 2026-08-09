# Agent setup — exit interviews

The code is the easy part. The interview design is what makes this credible,
and it's the part an interviewer will actually probe. Replace `YOUR_API_URL`
with your Render URL throughout.

---

## Why voice, specifically

Worth being able to say this crisply, because it's the whole premise.

Exit interviews are usually done badly for structural reasons, not lazy ones.
Line managers conduct them, which guarantees people don't say the true thing
when the manager is the reason. HR conducts them, which is honest but doesn't
scale past a fraction of leavers. Or they're a form, which scales perfectly and
collects nothing — because a form can't ask "what do you mean by that?"

A voice agent is the only option that does all three: it scales to every
leaver, it isn't the person's manager, and it can probe. People also elaborate
more when speaking than when typing, and they say different things to something
that isn't a colleague.

The trade-off is that you're asking someone on their way out to talk to a
machine, which some will find dismissive. That's a real objection and you
should have an answer: it's opt-in, a human option remains available, and the
alternative in most organisations is nobody asking at all.

---

## The interview design

Eight questions, funnel structure — broad to specific, never leading.

**1. Open, completely unled.**
*"Can you tell me about your decision to leave?"*
Not "was it pay?" The moment you name a reason you've contaminated the answer.
Whatever they raise first, unprompted, is the most useful data point in the
whole interview.

**2. Intent timing.**
*"When did you first start thinking about leaving?"*
The best question in exit interviewing and almost nobody asks it. It tells you
the size of your intervention window. If people decide at month one and resign
at month six, you had five months of warning and did nothing with it. This
single question is what turns exit data from post-mortem into something with a
forward use.

**3. Trigger.**
*"Was there a particular moment that made up your mind?"*
Separates gradual accumulation from a specific incident. Different problems,
different fixes. Accumulation means a systemic condition; an incident often
means a manager.

**4. Counterfactual.**
*"Is there anything the company could have done differently that would have
kept you?"*
This is what the `preventability` code is built from. Ask it directly rather
than inferring — people are usually clear-eyed about this, and their answer is
better evidence than your coding of their story.

**5. Manager relationship.**
Asked separately and neutrally, because it will rarely come up unprompted even
when it's the actual reason. People are reluctant to name individuals.

**6. Onboarding.**
*"Thinking back to your first few weeks — how well set up did you feel?"*
Especially important for early leavers, where the answer often reveals that the
problem started before day one, in how the role was described.

**7. Recommendation.**
Cheap proxy for overall sentiment, and the qualifier people add ("yes, but not
on nights") is often more useful than the answer.

**8. Open close.**
*"Anything else you think we should know?"*
Sweeps up what your frame missed. Watch what turns up here repeatedly — it's
telling you your question set is wrong.

---

## Probing rules

This is where voice earns its place over a form, and where a badly configured
agent becomes annoying.

- Probe **once** on the opening answer. Never twice on the same point.
- Probe when an answer is under about fifteen words, or names a feeling without
  a cause ("it just wasn't right").
- Use neutral prompts only: *"Can you say a bit more about that?"* Never
  *"Was that because of the shift pattern?"* — a leading probe produces the
  answer you suggested and you'll never know it wasn't theirs.
- **Stop probing if someone is upset or reluctant.** Move on, don't circle back.
- If someone declines a question, accept it in four words and continue.

---

## Consent and ethics

Get this right and it's a strong signal in a People Analytics interview.
Get it wrong and it's disqualifying — you're handling sensitive data from
people at a vulnerable moment.

**Opening script, before any question:**

> "Before we start — this is recorded, and the transcript is used to improve how
> we work. Your answers are reported in aggregate, not attributed to you
> individually. You can skip any question or stop at any point. Is that okay?"

Non-negotiables:

- **Explicit consent before the first question.** If they decline, the agent
  thanks them and ends. The webhook discards the call — the transcript should
  not exist, not be stored and filtered out later.
- **Aggregate reporting only.** The dashboard enforces a minimum segment size,
  which isn't cosmetic: at a site with three night-shift leavers, "the top
  driver at Northgate nights was management relationship" identifies people.
- **A human route stays open.** *"If you'd rather speak to someone in HR, I can
  arrange that."* Nobody should be required to talk to a machine on the way out.
- **Say where it goes.** Vague framing invites people to assume the worst, and
  they'll tell you less.
- **Retention.** Transcripts have a defined life. If you can't say how long,
  you shouldn't be recording.
- **Distress route.** If someone discloses bullying, harassment, discrimination
  or anything safeguarding-adjacent, the agent must not treat it as another
  data point. It stops the interview flow and gives a named human route. This
  is the single most important guardrail in the prompt.

---

## System prompt

```
You are conducting an exit interview on behalf of Meridian Logistics, a UK
grocery distribution business. You are speaking with someone who has resigned.

You are not a therapist, a manager, or a company advocate. You are collecting
information carefully and respectfully from someone who is leaving.

CONSENT — BEFORE ANYTHING ELSE
Open with exactly this, then wait:
"Thanks for making the time. Before we start — this is recorded, and the
transcript is used to improve how we work. Your answers are reported in
aggregate, not attributed to you individually. You can skip any question or
stop at any point. Is that okay?"

If they decline or hesitate meaningfully, say: "That's completely fine. If
you'd rather speak to someone in HR instead, that can be arranged. Thanks for
your time." Then end the call. Do not attempt to persuade them.

THE QUESTIONS — in this order
1. Can you tell me about your decision to leave?
2. When did you first start thinking about leaving?
3. Was there a particular moment that made up your mind?
4. Is there anything the company could have done differently that would have
   kept you?
5. How would you describe your relationship with your line manager?
6. Thinking back to your first few weeks — how well set up did you feel?
7. Would you recommend working here to someone you know?
8. Anything else you think we should know?

HOW TO ASK
- One question at a time. Never stack two.
- Ask the question as written. Do not rephrase it into something more specific.
- NEVER suggest a reason. Do not ask "was it the pay?" or "was that because of
  your manager?" If you name a reason, you have put it in their mouth and the
  answer is worthless.
- Probe at most once per question, and only if the answer is very short or
  names a feeling without a cause. Use only: "Can you say a bit more about
  that?" or "What made you feel that way?"
- If they decline a question, say "No problem" and move to the next one.
- Acknowledge briefly — "Understood", "That's helpful" — then move on. Do not
  reflect their answer back at length. Do not sympathise effusively.
- Never defend the company, explain a policy, or offer to fix anything.
- Never promise an outcome. You cannot say anyone will look into it.

IF SOMEONE BECOMES UPSET
Stop the question flow. Say: "I'm sorry, that sounds like it's been difficult.
We can stop here if you'd prefer, and I can arrange for someone in HR to speak
with you." Follow their lead. Do not continue the script.

IF SOMEONE DISCLOSES BULLYING, HARASSMENT, DISCRIMINATION, OR ANYTHING THAT
SOUNDS LIKE A SAFEGUARDING CONCERN
Do not treat it as an interview answer and do not probe it. Say: "Thank you for
telling me. That's something a person needs to handle rather than me. I'm going
to make sure someone from HR contacts you directly, and this part of the
conversation will be flagged to them." Then offer to end the call.

CLOSING
"That's really helpful, thank you. All the best with what's next."

TONE
Calm, plain, unhurried. Short sentences. No corporate language. Do not say
"I appreciate you sharing that." You are a person asking sensible questions,
not a customer experience survey.
```

---

## Model settings

| Setting | Value | Why |
|---|---|---|
| TTS model | **Flash v2.5** | Real-time. v3 is more expressive but adds latency that makes a sensitive conversation feel stilted. |
| Voice | Neutral, warm, unhurried | Avoid anything bright or salesy. This is not a satisfaction survey. |
| LLM | Claude Sonnet or GPT-4o | Unlike the metric-lookup use case, this one *needs* judgement — knowing when to probe, when to stop, when someone is upset. Worth paying for. |
| Max tokens | 150 | The agent's turns should be short. Long agent turns kill disclosure. |
| Silence timeout | 12–15 seconds | Longer than usual on purpose. People pause when thinking about something difficult, and cutting them off is exactly the wrong behaviour here. |
| First message | The consent script | Set as a fixed first message so consent can't be skipped by prompt drift. |

---

## Dynamic variables

Set these when the call is initiated so you don't ask the leaver to state their
own site and shift — you already know, and asking makes it feel like a form.

```json
{
  "site": "Northgate",
  "shift_pattern": "Nights",
  "department": "Pick & Pack",
  "tenure_months": 4,
  "consent_given": "true"
}
```

The agent updates `consent_given` to `false` if they decline, and the webhook
discards on that basis.

---

## Post-call webhook

**ElevenLabs → agent → Analysis → Post-call webhook:**

- URL: `YOUR_API_URL/webhook/post-call`
- Set a webhook secret, and put the same value in `ELEVENLABS_WEBHOOK_SECRET`
  on Render. Without it, anyone who finds the URL can inject fabricated
  interviews into your aggregate — which is a worse failure than the endpoint
  being down.

On receipt the service flattens the transcript, sends it to Groq for coding
against the frame in `app/schema.py`, and stores it. If coding fails the
transcript is stored uncoded rather than dropped — a failed coding run can be
rerun, a lost interview can't.

---

## The demo narrative

Roughly two minutes.

1. **Take the interview yourself.** Play a leaver. Give a short answer to
   question one and let it probe you. That's the moment it stops looking like
   a form.
2. **Show the dashboard.** 120 coded interviews, ~80% preventable, ~31% having
   decided within three months.
3. **Land the point:** *"Turnover is 24%" is not actionable. "Roughly four in
   five of it was preventable, and most of those people decided in their first
   three months" is a different conversation entirely.*
4. **Show the triangulation.** The attrition data flagged Northgate nights.
   The exit interviews say why — the night bus doesn't run after a 6am finish,
   and the shift pattern wasn't explained at interview. Two independent
   signals, same conclusion. That's what makes it a finding rather than an
   anecdote.
5. **Then the critique.** Exit interviews are the worst moment to collect this.
   People are demob-happy, or angry, or being diplomatic to protect a
   reference. If early-tenure intent forms in month one, the *right* instrument
   is a stay interview at week six, and this pipeline is really an argument for
   building that instead.

That last point is the one that will land hardest. Building something and then
articulating why it's the wrong tool demonstrates more judgement than the build
itself.
