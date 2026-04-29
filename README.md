# 📧 OpenEnv: Email Triage & Response

[![Tests](https://github.com/saisatwik-hue/OpenENV-1/actions/workflows/test.yml/badge.svg)](https://github.com/saisatwik-hue/OpenENV-1/actions)
[![Score](https://img.shields.io/badge/Score-0.927%2F1.0-22c55e?style=flat-square)](/)
[![Tasks](https://img.shields.io/badge/Tasks-3%20PASS-22c55e?style=flat-square)](/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker)](/)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python)](/)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
[![HF Space](https://img.shields.io/badge/Live%20Demo-HF%20Spaces-FF6B2B?style=flat-square)](https://saisatwik1234567-email-triage-and-response-environment.hf.space)

A training environment where language models learn to manage enterprise email through reinforcement learning.

**Live:** https://saisatwik1234567-email-triage-and-response-environment.hf.space  
**Training:** https://colab.research.google.com/drive/1yEVvyttO8KK2q1TfTcBSvadw8ke5LkLY  
**Blog:** https://huggingface.co/blog/saisatwik1234567/the-inbox-that-could-bring-down-a-company

---

## The Problem

Knowledge workers spend 28% of their workday on email. A missed P0 alert. An ignored GDPR deadline. A phishing attempt that slipped through. These are real consequences of email handled without judgment.

This project is a training environment where a language model learns to handle enterprise email through trial and reward — reading emails, deciding what to do, receiving feedback after every action, and gradually improving.

---

## Verified Scores

| Task | Difficulty | Score | Threshold | Result |
|---|---|---|---|---|
| Task 1: Email Triage | 🟢 Easy | **0.9999** | ≥ 75% | ✅ PASS |
| Task 2: Response Drafting | 🟡 Medium | **0.8893** | ≥ 78% | ✅ PASS |
| Task 3: Inbox Zero Sprint | 🔴 Hard | **0.8911** | ≥ 68% | ✅ PASS |
| **Average** | | **0.9268** | | ✅ ALL PASS |

Phase 1 validation ✅ · Phase 2 validation ✅ · Round 1 cleared ✅

---

## Training Results

![Reward Curve](training_results.png)

| | Before Training | After Training |
|---|---|---|
| Average Score | 0.682 | 0.710 |
| P0 Escalation | ❌ Archives them | ✅ Escalates correctly |
| Spam Detection | ❌ Responds politely | ✅ Archives immediately |
| Priority Order | ❌ Random | ✅ Urgent first |
| Pass Threshold | ❌ Fails | ✅ Passes |

📓 [Open Training Notebook in Colab →](https://colab.research.google.com/drive/1yEVvyttO8KK2q1TfTcBSvadw8ke5LkLY)

---

## What's Inside

**50 enterprise emails** across 6 categories:

```
urgent   ████████████  12 (24%) — P0 outages, GDPR, security alerts
normal   ███████████████ 15 (30%) — complaints, approvals, disputes
external ██████ 6 (12%) — partners, press, conferences
internal ███████ 7 (14%) — all-hands, IT, HR
low      ██████ 6 (12%) — newsletters, reminders
spam     ████ 4  (8%)  — phishing, fake domains
```

**Three tasks:**
- **Task 1 (Easy)** — Sort and prioritise 20 emails
- **Task 2 (Medium)** — Draft responses with synonym-aware grading
- **Task 3 (Hard)** — Process all 50 in the right priority order

---

## Three Things That Make This Different

### 1. Synonym-Aware Grading
```python
# "reimbursement" scores the same as "refund" — they mean the same thing
synonyms["e009"] = [
    ["refund", "reimburse", "credit", "money back"],
    ["apologize", "sorry", "apologies", "regret"],
    ["approved", "authorize", "granted", "confirmed"],
]
```

### 2. Kendall Tau Prioritisation
```python
# Did you handle urgent emails BEFORE low-priority ones?
score = concordant_pairs / (concordant + discordant)
# 1.0 = perfect order. 0.5 = random. 0.0 = completely reversed.
```

### 3. Shaped Rewards Every Step
```python
reward = (grader_score - 0.5) * 0.8        # feedback after every action
if score >= 0.85: reward += 0.10            # excellence bonus
if is_critical and action == "archive":
    reward -= 0.30                          # never archive a P0
```

---

## Quick Start

```bash
git clone https://github.com/saisatwik-hue/OpenENV-1
cd OpenENV-1
pip install -r requirements.txt
uvicorn app.main:app --port 7860
# Open http://127.0.0.1:7860
```

Or with Docker:
```bash
docker build -t openenv . && docker run -p 7860:7860 openenv
```

---

## Using the Rubric System

```python
from rubric_system import make_triage_composer

composer = make_triage_composer()
result   = composer.grade(action, email)

print(result['total'])       # 0.0001 to 0.9999
print(result['breakdown'])   # per-rubric scores and reasons
```

---

## API Reference

```python
import httpx

BASE = "https://saisatwik1234567-email-triage-and-response-environment.hf.space"

# Start episode
obs = httpx.post(f"{BASE}/reset?task_id=task_1").json()["observation"]

# Take action
result = httpx.post(f"{BASE}/step?task_id=task_1", json={
    "action_type":    "escalate",
    "email_id":       "e001",
    "category":       "urgent",
    "priority_score": 1.0,
    "escalate_to":    "backend-oncall"
}).json()
print(f"Reward: {result['reward']}")   # +0.50

# Get score
grade = httpx.post(f"{BASE}/grader?task_id=task_1").json()
print(f"Score: {grade['episode_score']}  Grade: {grade['grade_letter']}")
```

**All endpoints:**

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/reset` | Start a new episode |
| `POST` | `/step` | Execute one action |
| `GET` | `/state` | Current episode state |
| `GET` | `/tasks` | Task list with full schema |
| `POST` | `/grader` | Score the episode |
| `GET` | `/metrics` | Live episode stats |
| `GET` | `/leaderboard` | Score leaderboard |
| `POST` | `/leaderboard/submit` | Submit your score |
| `GET` | `/info` | Full environment spec |
| `GET` | `/health` | System status |
| `GET` | `/` | Live dashboard |
| `GET` | `/docs` | Swagger UI |

---

## Tests

```bash
pytest tests/ -v
# 17 passed in 2.3s
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add emails, tasks, and rubrics.

---

## License

MIT — open source, free to use for research and production.
