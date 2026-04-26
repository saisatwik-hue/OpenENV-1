---
title: "OpenEnv: Training an LLM to Manage Enterprise Email with GRPO"
thumbnail: /blog/assets/openenv-email-triage/thumbnail.png
authors:
  - user: saisatwik1234567
---

# 🏆 OpenEnv: Training an LLM to Manage Enterprise Email

*How we built a complete RL training environment for enterprise email management and trained a language model to handle P0 outages, GDPR breaches, and customer complaints — all with shaped rewards.*

---

## The Problem

Knowledge workers spend **28% of their workday on email**. Yet there is no standardised environment to train or benchmark AI agents on email management tasks.

We built one.

---

## What We Built

**OpenEnv: Email Triage & Response** is a complete AI agent training environment with:

- **50 realistic enterprise emails** — from P0 database outages to phishing attacks to customer refund requests
- **3 tasks** of increasing difficulty (Easy → Medium → Hard)
- **Dense shaped rewards** — feedback at every step, not just the end
- **12 API endpoints** including WebSocket support for `openenv-core` clients
- **Live monitoring dashboard** with real-time reward charts

🔗 **Live Environment:** https://saisatwik1234567-email-triage-and-response-environment.hf.space

---

## The 3 Novel Innovations

### 1. Synonym-Aware Keyword Grading
Standard keyword graders reject legitimate paraphrasing. If the expected keyword is "refund" and the agent writes "reimbursement" — a naive grader gives 0 points.

Our grader uses **synonym groups**:
```python
synonyms["e009"] = [
    ["refund", "reimburse", "credit", "money back"],  # any = full credit
    ["apologize", "sorry", "apologies", "regret"],
    ["approved", "authorize", "granted", "confirmed"],
]
```
Any word in the group = full credit. This is how human teachers grade.

### 2. Kendall Tau Prioritization Scoring
We don't just ask "did you process all emails?" We ask **"did you process urgent ones first?"**

```python
# For every pair (i,j) of processed emails:
if priority[email_i] >= priority[email_j]:
    concordant += 1   # correct order ✅
else:
    discordant += 1   # wrong order ❌

score = concordant / (concordant + discordant)
# 1.0 = perfect order, 0.5 = random, 0.0 = completely reversed
```

### 3. Dense Shaped Rewards
```python
reward = (grader_score - 0.5) * 0.8    # centred at 0
if score >= 0.85: reward += 0.1         # excellence bonus
if is_critical and action == "archive": reward -= 0.3  # critical penalty
```

---

## Training with GRPO

We trained **Qwen2.5-1.5B-Instruct** using GRPO (Group Relative Policy Optimisation) from HF TRL:

```python
from trl import GRPOConfig, GRPOTrainer
from unsloth import FastLanguageModel

grpo_config = GRPOConfig(
    num_generations=4,        # 4 completions per prompt
    learning_rate=5e-6,
    num_train_epochs=3,
    temperature=0.7,
    beta=0.1,                 # KL penalty prevents forgetting
)

trainer = GRPOTrainer(
    model=model,
    reward_funcs=[compute_episode_reward],  # our OpenEnv grader!
    args=grpo_config,
    train_dataset=train_dataset,
)
trainer.train()
```

---

## Results: Before vs After Training

| | Before Training | After Training |
|---|---|---|
| Task 1 (Easy) | ~0.45 | **0.92** |
| Task 2 (Medium) | ~0.38 | **0.81** |
| Task 3 (Hard) | ~0.31 | **0.74** |
| **Average** | ~0.38 | **0.82** |

The model learned to:
- ✅ **Escalate P0 incidents** instead of archiving them
- ✅ **Use professional tone** with proper openers and closers
- ✅ **Include relevant keywords** in responses (refund, apologize, etc.)
- ✅ **Prioritize urgent emails** before newsletters and spam

---

## Try It Yourself

**Colab notebook:** https://colab.research.google.com/drive/1yEVvyttO8KK2q1TfTcBSvadw8ke5LkLY#scrollTo=vLM3cO9wGrZr

**Live environment:**
```python
import httpx

BASE = "https://saisatwik1234567-email-triage-and-response-environment.hf.space"

# Reset
obs = httpx.post(f"{BASE}/reset?task_id=task_1").json()["observation"]

# Step
result = httpx.post(f"{BASE}/step?task_id=task_1", json={
    "action_type": "escalate",
    "email_id": "e001",
    "category": "urgent",
    "priority_score": 1.0,
    "escalate_to": "backend-oncall"
}).json()
print(f"Reward: {result['reward']}")  # +0.500

# Grade
grade = httpx.post(f"{BASE}/grader?task_id=task_1").json()
print(f"Score: {grade['episode_score']} | Grade: {grade['grade_letter']}")
```

---

## About This Project

Built for the **Meta × Scaler OpenEnv Hackathon 2024**.

- 🏆 **Round 1: Cleared**
- 📊 Demo Score: **0.927 / 1.0** — All 3 Tasks PASS
- 🔗 GitHub: https://github.com/saisatwik-hue/OpenENV
- 🤗 HF Space: https://huggingface.co/spaces/saisatwik1234567/Email-triage-and-response-environment

*Theme: #3.2 Personalized Tasks — Real-world email management*
