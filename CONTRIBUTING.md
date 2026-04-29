# Contributing to OpenEnv: Email Triage & Response

Thank you for your interest in contributing. This document explains how to add emails, tasks, and improvements.

---

## Quick Start

```bash
git clone https://github.com/saisatwik-hue/OpenENV-1
cd OpenENV-1
pip install -r requirements.txt
uvicorn app.main:app --port 7860
```

Open http://127.0.0.1:7860 — you should see the dashboard.

Run tests:
```bash
pytest tests/ -v
# Expected: 17 passed
```

---

## Project Structure

```
OpenENV-1/
├── app/
│   ├── main.py              ← FastAPI server (12 endpoints)
│   ├── environment.py       ← Core: reset/step/state/grade
│   ├── models.py            ← Pydantic data models
│   ├── data.py              ← 50 emails + ground truth + synonyms
│   └── tasks/
│       ├── task1_triage.py      ← Easy grader
│       ├── task2_response.py    ← Synonym-aware response grader
│       └── task3_inbox_zero.py  ← Kendall tau prioritisation grader
├── rubric_system.py         ← Composable rubric grading system
├── server/app.py            ← OpenEnv entry point
├── inference.py             ← Baseline agent
└── tests/test_env.py        ← 17 automated tests
```

---

## How to Add a New Email

Open `app/data.py` and add an entry to the `EMAILS` list:

```python
{
    "id": "e051",
    "subject": "Your subject line here",
    "sender": "sender@company.com",
    "sender_domain": "company.com",
    "timestamp": "2024-01-15T09:00:00Z",
    "body": "Full email body text here...",
    "has_attachments": False,
    "thread_depth": 0,
    "word_count": 50,
    "ground_truth": {
        "category": "urgent",           # urgent/normal/low/spam/internal/external
        "priority_score": 0.95,         # 0.0 (not urgent) to 1.0 (critical)
        "requires_response": True,
        "correct_action": "escalate",   # triage/respond/escalate/archive/flag/skip
        "escalate_to": "backend-oncall",
        "response_keywords": ["acknowledge", "investigating", "priority"],
    }
}
```

Then run the tests to make sure nothing breaks:
```bash
pytest tests/ -v
```

---

## How to Add Synonym Groups

Synonym groups make the response grader smarter. Open `app/data.py` and find `SYNONYM_GROUPS`. Add an entry for your email:

```python
SYNONYM_GROUPS["e051"] = [
    ["escalate", "urgent", "immediate", "priority"],     # group 1
    ["investigate", "look into", "examine", "check"],    # group 2
    ["acknowledge", "confirm", "received", "noted"],     # group 3
]
```

Any word from any group = full credit for that group.

---

## How to Add a New Task

1. Create `app/tasks/task4_yourname.py`:

```python
from app.data import EMAILS

class YourTask:
    name        = "Your Task Name"
    difficulty  = "medium"          # easy/medium/hard
    max_steps   = 30
    pass_threshold = 0.75
    description = "What the agent needs to do"

    def get_emails(self):
        return [e for e in EMAILS if e["ground_truth"]["category"] == "urgent"][:15]

    def grade_action(self, action, email):
        # Your grading logic here
        # Return: {"total": 0.0-1.0, "breakdown": {...}}
        pass

    def compute_episode_score(self, graded):
        scores = [g["total"] for g in graded]
        return {"score": sum(scores)/len(scores), "breakdown": {}}
```

2. Register it in `app/tasks/registry.py`:
```python
from app.tasks.task4_yourname import YourTask

TASK_REGISTRY = {
    "task_1": TriageTask,
    "task_2": ResponseTask,
    "task_3": InboxZeroTask,
    "task_4": YourTask,        # add this line
}
```

3. Add to `openenv.yaml` tasks list:
```yaml
tasks:
  - id: task_4
    name: "Your Task Name"
    difficulty: medium
    max_steps: 30
    pass_threshold: 0.75
```

---

## Reporting Issues

Open a GitHub Issue with:
- What you tried
- What you expected
- What actually happened
- Your Python version and OS

---

## Code Style

- Use type hints where possible
- Keep functions under 40 lines
- Every new grader needs at least one test in `tests/test_env.py`
- Scores must be clamped to `(0.0001, 0.9999)` — never exactly 0 or 1

---

MIT License — contributions welcome.
