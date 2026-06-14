# 30-Day Client Acquisition Playbook

> Realistic, executable, hour-by-hour. Goal: $300-1000 in month 1, $1000-3000/month by month 3-6.

---

## Day 0 — Setup (today, ~3 hours)

### Morning (90 min) — Accounts

- [ ] Create Upwork account
  - Real name + professional headshot (or generated AI avatar)
  - Title: "AI Application Engineer | Java Backend | Multi-Agent Systems | RAG"
  - Use the Overview from `career/PROFILE_KIT.md`
- [ ] Create / update LinkedIn profile
  - Use the headline + about from `career/PROFILE_KIT.md`
  - Add GitHub repo + ERP AI Copilot landing page as Featured items
- [ ] Set Upwork email alerts for: "AI agent", "LangChain", "RAG", "OpenAI", "GPT-4", "Java backend", "PostgreSQL AI"
- [ ] Set Google Alerts: "AI agent consulting", "RAG engineer freelancer"

### Afternoon (90 min) — Portfolio

- [ ] Make sure GitHub README is the English version (`README.en.md`) or replace `README.md` with it
- [ ] Commit `LANDING_PAGE.md` to repo (root or `docs/`)
- [ ] Commit `career/PROFILE_KIT.md` (private or public — your call)
- [ ] Add a `hire-me.md` link in repo pointing to Upwork / your email
- [ ] Make first blog post draft:
  - Title: "I built an ERP AI Copilot in 14 days. Here's what I learned."
  - Publish to: dev.to, Medium, or Hashnode

---

## Day 1-7 — First 5 Upwork proposals

### Daily routine (45 min/day)

```
Morning (25 min):
1. Open Upwork → "Find Work" → search your keywords
2. Sort: "Newest first" → "Client hire rate ≥ 50%" → "Payment verified"
3. Find 1-2 good postings
4. Apply using template A/B/C/D/E from PROFILE_KIT.md
5. Customize: [Client name], [their use case], and ONE specific question

Evening (20 min):
1. Check Upwork inbox — respond to any messages within 4 hours
2. LinkedIn: send 5 personalized connection requests to CTOs at AI startups
3. Update your tracker spreadsheet
```

### Target: 5 proposals by end of week 1

Likely outcome: **0-1 responses** (normal — Upwork has a 5-15% response rate for new accounts)

### Tracking spreadsheet columns

| Date | Platform | Project/Person | Hook used | Status | Next action | $ quoted |
|------|----------|----------------|-----------|--------|-------------|----------|

---

## Day 8-14 — Diversify channels

### Add these 3 channels

#### Channel 1: Twitter / X (60 min/day)

Follow + engage with these accounts:
- @LangChainAI
- @llama_index
- @AnthropicAI
- @OpenAI
- @swyx (DX)
- @labenz (CX)

Post 1 tweet per day (rotate between):
- **Insight tweet**: "Spent the weekend debugging NL→SQL safety. Here's the 4-layer guardrail pattern I landed on: [link to blog post]"
- **Build-in-public tweet**: "Day 23 of building ERP AI Copilot. Today: hit 200ms latency on RAG queries. Here's how: [thread]"
- **Question tweet**: "Anyone else hit [specific issue]? Curious how you solved it."

#### Channel 2: IndieHackers (30 min/week)

- Post on Show section: "I built an open-source ERP AI Copilot — looking for feedback"
- Reply to threads in #ai, #saas, #freelancing
- DM people who ask AI-related questions

#### Channel 3: Cold email (5 emails/week)

Find 20 AI startups via Crunchbase / ProductHunt. Send 5 emails per week using this template:

```
Subject: 15-min call about [Company name]'s AI roadmap?

Hi [Founder name],

Saw [Company name] on ProductHunt — congrats on the launch.
[Specific thing about their product that caught your eye].

I build production AI systems end-to-end (RAG, NL→SQL,
multi-agent). Recent work: github.com/blank5this/MACS
(open-source, MIT, 256 tests).

If you're exploring AI features for [their product area],
I'd love to chat for 15 minutes. No pitch — just curious
what's on your roadmap.

— [Your name]
[LinkedIn] · [Upwork]
```

**Tracking**: add to spreadsheet with "cold email" tag.

---

## Day 15-21 — First interview / trial project

### Likely scenario: 1-2 interviews booked, 0 hires yet

#### If you land an interview:

Prepare these 3 stories (use STAR format):

**Story 1 — Technical depth**:
> "Situation: ERP project needed NL→SQL over PostgreSQL.
> Task: Build safe translator, no SQL injection possible.
> Action: 4-layer guardrail (AST whitelist / SQL keyword blacklist / statement-type whitelist / parameterized queries).
> Result: 256 tests passing, including 50+ adversarial injection attempts that all get blocked."

**Story 2 — Speed of execution**:
> "Situation: Wanted to ship an MVP in 14 days to validate the market.
> Task: Build Text2SQL + RAG + multi-agent + web UI from scratch.
> Action: Used existing MACS framework as foundation. Focused on 3 use cases only.
> Result: Working demo, MIT licensed, 256 tests, 3 demo videos, full docs."

**Story 3 — Cross-stack integration**:
> "Situation: Client had Java backend + wanted to add AI features.
> Task: Add natural-language Q&A without touching Java code.
> Action: Built Python FastAPI layer that calls Java REST APIs as MCP tools.
> Result: AI features live in 2 weeks, zero Java refactor needed."

### If they offer a small trial project ($100-300):

**DO IT.** Even at $15/hr. First review is worth 5x the hourly rate.

---

## Day 22-30 — Double down on what's working

### Analyze your tracker

Count per channel:
- Proposals sent vs responses (Upwork)
- Cold emails sent vs replies
- LinkedIn connections vs replies
- Twitter impressions vs DMs

The channel with the **highest response rate** → double down.

If Upwork is 5% response → keep going, increase volume to 7-10/week
If LinkedIn is 15% response → spend 1 hour/day on it
If cold email is 20% response → send 10/week

---

## Realistic income expectations

| Month | Income | Path |
|-------|--------|------|
| 1 | $0-300 | First small fixed-price project |
| 2 | $300-1000 | Repeat clients + 1-2 new |
| 3 | $1000-2000 | Strong Upwork profile + referrals |
| 4-6 | $2000-3000+ | Multiple clients, $20-25/hr after reviews |

**To break $3000/month consistently** (month 6+):
- Get 5+ 5-star reviews on Upwork
- 2-3 repeat clients
- Niche down (e.g., "AI for ERP / inventory / e-commerce")
- Raise rate to $25-35/hr

---

## Common mistakes to avoid

### ❌ Don't apply to projects you can't actually do

If a client wants computer vision model training — don't fake it. Skip.

### ❌ Don't compete on price

$5/hr AI engineers exist but they can't do this work. You're competing on quality + speed + safety, not price.

### ❌ Don't burn out on volume

5 quality proposals/day > 20 low-quality ones. Upwork's algorithm punishes low response rates.

### ❌ Don't disappear after first proposal

Reply to every client message within 4 hours during your work day. Upwork's "responsiveness" score matters for ranking.

### ❌ Don't give away the farm on trial projects

Define scope: "I'll do [X] for $Y in Z days." If they want more, quote more.

---

## What to do when you don't have any work

### Build in public

- Write a blog post: "How I built [X] in [Y] days"
- Record a 5-min tutorial video
- Open-source a small library you built for the project
- Update your GitHub README with a new feature

### Reach out proactively

- DM 3 former colleagues: "I'm freelancing in AI, here's my portfolio, know anyone who needs this?"
- Post in 3 relevant Slack/Discord communities (e.g., LangChain Discord, MLOps Community)
- Comment on 5 LinkedIn posts per day from target clients (with substance, not "Great post!")

---

## The 30-day milestone

By Day 30, you should have:
- [ ] 20+ Upwork proposals sent
- [ ] 1+ interview completed
- [ ] 50+ LinkedIn connections made
- [ ] 1+ blog post published
- [ ] 1+ cold email reply
- [ ] Updated GitHub README + demo video
- [ ] 1 small paid project ($100+)

**If you hit this milestone, you're ahead of 80% of freelancers.** Stay the course.

---

## Bonus: pricing negotiation cheat sheet

| Client says | You respond |
|-------------|-------------|
| "What's your rate?" | "$18-25/hr depending on project complexity. For fixed-price: I scope it first, then quote." |
| "Can you do it for $10/hr?" | "I can't sustainably do that. My floor is $15/hr for ongoing work. For a fixed-price [X], I can do $Y." |
| "How fast can you start?" | "Within 24 hours. What timezone are you in? I'm UTC+8 but flexible." |
| "We need it done in 3 days" | "Tight timeline. I can prioritize if budget reflects it — fixed-price $Z for 3-day delivery vs 7-day standard." |
| "Can you do a test task first?" | "Sure — a small scoped task ($50-100) so you can evaluate. I deliver, you decide if we continue." |

---

## Tools you'll need (all free / cheap)

| Tool | Cost | Purpose |
|------|------|---------|
| Upwork | 10% fee (you keep 90%) | Find clients |
| LinkedIn | Free | Network with CTOs |
| GitHub | Free | Portfolio |
| Notion | Free | Tracking spreadsheet |
| Calendly | Free | Schedule calls |
| Loom | Free | Record video updates for clients |
| Fiverr / Upwork contract | Free (built-in) | Protect yourself legally |

**Total monthly cost**: $0
**Minimum revenue to break even**: $1 (any first paid project)