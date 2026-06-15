# Question Anti-Patterns Reference

Detection patterns and fixes for common interview question problems. The validation script uses these patterns to catch issues before they compromise research quality.

---

## Anti-Pattern 1: Leading Questions

**What it is:** Questions that suggest the "right" answer or contain assumptions.

**Detection patterns:**
```
- "Would you say that X is..."
- "Don't you think..."
- "Isn't it true that..."
- "Would you agree that..."
- "How much do you love..."
- "How frustrating was..."  (assumes frustration)
- "How difficult is..."  (assumes difficulty)
- "How helpful was..."  (assumes helpfulness)
- Questions with "obviously" or "clearly"
- Questions ending with "right?" or "correct?"
```

**Examples:**

| ❌ Leading | ✅ Neutral |
|-----------|-----------|
| "How frustrating was the onboarding?" | "How would you describe the onboarding experience?" |
| "Would you say the pricing is confusing?" | "Walk me through how you understood the pricing." |
| "Don't you think the dashboard is cluttered?" | "What's your reaction to the dashboard?" |
| "How helpful was the tutorial?" | "What was your experience with the tutorial?" |

**Fix pattern:** Remove the assumption. Open with "How would you describe...", "What was your experience with...", "Tell me about..."

---

## Anti-Pattern 2: Double-Barreled Questions

**What it is:** Two questions joined together, making it unclear which one is being answered.

**Detection patterns:**
```
- Questions containing " and " with two distinct topics
- Questions containing " or " asking about different things
- Questions with multiple question marks
- Questions asking about two time periods
- Questions about two different people/roles
```

**Examples:**

| ❌ Double-barreled | ✅ Split |
|-------------------|---------|
| "How was the onboarding and what did you think of the dashboard?" | Q1: "How was the onboarding?" Q2: "What did you think of the dashboard?" |
| "Did you find it easy to use and would you recommend it?" | Q1: "How easy was it to use?" Q2: "Would you recommend it? Why/why not?" |
| "What do you and your team think about the pricing?" | Q1: "What do you think about the pricing?" Q2: "What does your team think?" |

**Fix pattern:** Split into separate questions. Ask one thing at a time.

---

## Anti-Pattern 3: Hypothetical/Future Questions

**What it is:** Asking what someone "would" do instead of what they actually did. People are poor predictors of their own future behavior.

**Detection patterns:**
```
- "Would you..."
- "Will you..."
- "Could you see yourself..."
- "Do you think you would..."
- "If we built X, would you..."
- "How likely are you to..."
- "Can you imagine..."
- "In the future, would you..."
```

**Examples:**

| ❌ Hypothetical | ✅ Behavioral |
|----------------|--------------|
| "Would you pay for this feature?" | "Tell me about the last time you paid for a tool. What made it worth it?" |
| "Will you use this daily?" | "How often did you use [similar thing] in the past month?" |
| "Would you recommend this to a colleague?" | "Have you recommended tools to colleagues before? What made you do that?" |
| "If we added X, would you use it?" | "When have you needed something like X? What did you do?" |

**Fix pattern:** Reframe to past behavior. "Tell me about a time when..." or "When was the last time you..."

**Exception:** Hypotheticals are okay as follow-ups to past behavior: "You mentioned you did X—would you do that again?"

---

## Anti-Pattern 4: Yes/No Closed Questions

**What it is:** Questions that can be answered in one word, shutting down exploration.

**Detection patterns:**
```
- Questions starting with "Did you..."
- Questions starting with "Do you..."
- Questions starting with "Is it..."
- Questions starting with "Are you..."
- Questions starting with "Was it..."
- Questions starting with "Have you..."
- Questions starting with "Can you..." (when asking ability, not requesting action)
```

**Examples:**

| ❌ Closed | ✅ Open |
|----------|--------|
| "Did you find it easy?" | "How did you find the experience?" |
| "Do you like the design?" | "What's your reaction to the design?" |
| "Was it confusing?" | "Walk me through what happened when you first saw it." |
| "Have you used competitors?" | "Tell me about other tools you've tried for this." |

**Fix pattern:** Convert to open questions starting with "How...", "What...", "Tell me about...", "Walk me through...", "Describe..."

**Exception:** Closed questions are okay for:
- Screening ("Do you currently use X?")
- Clarification ("Did you mean the mobile app?")
- Confirmation before moving on ("Okay, so you switched in March—is that right?")

---

## Anti-Pattern 5: Jargon and Insider Language

**What it is:** Using product names, technical terms, or internal language that participants may not understand or may interpret differently.

**Detection patterns:**
```
- Product feature names (unless participant introduced them)
- Technical terms (API, UI, UX, dashboard, workflow, integration)
- Business jargon (ROI, stakeholder, leverage, synergy)
- Acronyms not spelled out
- Internal project names
- Assumed knowledge ("the new feature", "the update")
```

**Examples:**

| ❌ Jargon | ✅ Plain Language |
|----------|------------------|
| "How do you use the analytics dashboard?" | "How do you check how things are going?" |
| "What's your workflow for onboarding?" | "Walk me through what you do when you're getting started." |
| "How did the API integration go?" | "How did you connect it to your other tools?" |
| "What did you think of the Q3 update?" | "What did you notice that was different recently?" |

**Fix pattern:** Use the participant's language. If you must use a term, define it or let them introduce it first.

**Flag for review:** Any jargon should be flagged for the researcher to consider whether it's appropriate for this participant.

---

## Anti-Pattern 6: Confirmation Bias Framing

**What it is:** Questions structured to confirm a hypothesis rather than explore openly.

**Detection patterns:**
```
- Questions that only ask about one side (problems but not successes)
- Questions assuming a behavior happened ("When you struggled with X...")
- Questions with embedded conclusions ("Since X is difficult...")
- Questions seeking validation ("We think X—what do you think?")
- Selective follow-ups (only probing answers that match hypothesis)
```

**Examples:**

| ❌ Confirming | ✅ Exploring |
|--------------|-------------|
| "What problems did you have with onboarding?" | "How would you describe your onboarding experience?" |
| "Since the pricing is complex, how did you navigate it?" | "Walk me through how you figured out pricing." |
| "We believe users need X—do you agree?" | "When you're doing [task], what do you find yourself needing?" |
| "When you got frustrated with Y..." | "What happened when you encountered Y?" |

**Fix pattern:** Frame questions neutrally. Allow for positive, negative, and neutral responses. Follow up on all types of answers, not just confirming ones.

---

## Anti-Pattern 7: Multiple Choice Questions

**What it is:** Questions that provide options, limiting responses to researcher's imagination.

**Detection patterns:**
```
- "Was it A, B, or C?"
- "Did you feel X or Y?"
- "Which matters more, A or B?"
- "Would you describe it as X, Y, or Z?"
```

**Examples:**

| ❌ Multiple Choice | ✅ Open |
|-------------------|--------|
| "Was it fast, slow, or about right?" | "How would you describe the speed?" |
| "Did you feel frustrated or confused?" | "What were you feeling at that moment?" |
| "Which mattered more—price or features?" | "What mattered most when you were deciding?" |

**Fix pattern:** Remove the options. Let participants generate their own descriptions.

---

## Anti-Pattern 8: Compound Questions with Setup

**What it is:** Long preambles that frame or bias the question before asking it.

**Detection patterns:**
```
- Questions preceded by lengthy context
- "A lot of people say X. Do you..."
- "We've heard that X. What do you..."
- "Our data shows X. How do you..."
- Questions starting with "So..." after researcher monologue
```

**Examples:**

| ❌ Compound | ✅ Direct |
|------------|----------|
| "We've been hearing from a lot of customers that the pricing page is confusing and they don't understand the tiers. What's your experience been?" | "Walk me through what happened when you looked at pricing." |
| "So given that you mentioned the onboarding was tricky and you had to figure things out on your own, how did that make you feel?" | "You mentioned figuring things out on your own—say more about that." |

**Fix pattern:** Ask the question directly. Let the participant provide the context. If you need to reference something they said, keep it short.

---

## Validation Checklist

For each question in the guide, verify:

| Check | Pass Criteria |
|-------|---------------|
| Not leading | No assumptions, no suggested answers |
| Single focus | One question at a time |
| Behavioral | Asks about past, not hypothetical future |
| Open-ended | Cannot be answered yes/no |
| Plain language | No jargon or insider terms |
| Neutral framing | Allows positive/negative/neutral responses |
| No options | Doesn't provide multiple choice |
| Direct | No lengthy preamble |

---

## Severity Levels

| Level | Action | Examples |
|-------|--------|----------|
| 🔴 Critical | Must fix before using guide | Leading questions, confirmation bias framing |
| 🟡 Warning | Fix or flag for researcher awareness | Jargon, hypotheticals, closed questions |
| 🟢 Note | Consider adjusting | Long preambles, mild assumptions |
