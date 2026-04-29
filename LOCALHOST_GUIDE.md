# Running OpenEnv Locally — Step by Step Guide

## What You Need
- A computer (Windows / Mac / Linux)
- Internet connection (first time only, to download packages)
- That's it

---

## Step 1 — Install Python

### Windows
1. Go to **python.org/downloads**
2. Click the big yellow **Download Python 3.11** button
3. Run the downloaded file
4. ⚠️ **IMPORTANT** — tick **"Add Python to PATH"** checkbox before clicking Install
5. Click **Install Now**
6. Wait until it says "Setup was successful" → close

### Mac
Open Terminal (Cmd + Space → type "Terminal" → Enter) and run:
```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install python@3.11
```

### Test Python installed correctly
Open Command Prompt (Windows) or Terminal (Mac) and type:
```
python --version
```
Should show: `Python 3.11.x`

---

## Step 2 — Download the Project

### Option A — Download ZIP (easiest)
1. Go to: **github.com/saisatwik-hue/OpenENV-1**
2. Click green **Code** button
3. Click **Download ZIP**
4. Right-click the downloaded ZIP → **Extract All**
5. Open the extracted folder

### Option B — Git Clone
```bash
git clone https://github.com/saisatwik-hue/OpenENV-1.git
cd OpenENV-1
```

---

## Step 3 — Open Terminal in the Project Folder

### Windows
1. Open File Explorer
2. Navigate to the OpenENV-1 folder
3. Click the address bar at the top → type `cmd` → press Enter
4. A black Command Prompt window opens — you're in the right folder

### Mac / Linux
```bash
cd /path/to/OpenENV-1
```

---

## Step 4 — Install All Dependencies

Copy and paste this command:
```bash
pip install fastapi "uvicorn[standard]" pydantic httpx python-multipart PyYAML websockets
```

Wait for it to finish (1-2 minutes). You'll see lots of green text — that's normal.

---

## Step 5 — Start the Server

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 7860
```

You'll see:
```
INFO:     Uvicorn running on http://127.0.0.1:7860
INFO:     Application startup complete.
```

✅ **The server is running!**

---

## Step 6 — Open in Browser

Open Chrome/Firefox and go to:
```
http://127.0.0.1:7860
```

You'll see the dark OpenEnv dashboard. 🎉

---

## Step 7 — Test It Works

Open a **second** terminal window (keep the server running in the first one).

### Quick Test
```bash
# Health check
curl http://127.0.0.1:7860/health

# Start an episode
curl -X POST "http://127.0.0.1:7860/reset?task_id=task_1"

# Take an action
curl -X POST "http://127.0.0.1:7860/step?task_id=task_1" \
  -H "Content-Type: application/json" \
  -d '{"action_type":"escalate","email_id":"e001","category":"urgent","priority_score":1.0,"escalate_to":"backend-oncall"}'

# Get your score
curl -X POST "http://127.0.0.1:7860/grader?task_id=task_1"
```

### Windows users — use this format instead:
```bash
curl -X POST "http://127.0.0.1:7860/step?task_id=task_1" -H "Content-Type: application/json" -d "{\"action_type\":\"escalate\",\"email_id\":\"e001\",\"category\":\"urgent\",\"priority_score\":1.0,\"escalate_to\":\"backend-oncall\"}"
```

---

## All URLs to Visit

| URL | What you see |
|-----|-------------|
| `http://127.0.0.1:7860` | Live dashboard |
| `http://127.0.0.1:7860/health` | Green ONLINE status page |
| `http://127.0.0.1:7860/tasks` | All 3 tasks with schema |
| `http://127.0.0.1:7860/docs` | Swagger interactive API docs |
| `http://127.0.0.1:7860/metrics?task_id=task_1` | Live episode metrics |
| `http://127.0.0.1:7860/info` | Full environment spec |

---

## Run with Docker (Alternative)

If you have Docker installed:
```bash
docker build -t openenv .
docker run -p 7860:7860 openenv
```

Then open `http://127.0.0.1:7860` — same result, no Python install needed.

---

## Run All Tests

```bash
pip install pytest
pytest tests/ -v
```

Expected output:
```
17 passed in 2.3s ✅
```

---

## Stop the Server

Click in the terminal window where the server is running and press:
```
Ctrl + C
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `python not found` | Reinstall Python — tick "Add to PATH" |
| `pip not found` | Use `python -m pip install ...` |
| `Port already in use` | Change port: `--port 8080` then open `127.0.0.1:8080` |
| `ModuleNotFoundError: fastapi` | Run `pip install fastapi uvicorn pydantic` again |
| Dashboard loads but shows error | Click Reset Environment button first |
| Slow on first load | Normal — Python loads packages into memory first time |

---

## Python Quick Start (Full Episode)

```python
import httpx

BASE = "http://127.0.0.1:7860"

# 1. Start episode
obs = httpx.post(f"{BASE}/reset?task_id=task_1").json()["observation"]
print(f"Inbox: {obs['pending_count']} emails waiting")

# 2. Take actions
emails_to_process = obs["inbox"][:5]
for email in emails_to_process:
    result = httpx.post(f"{BASE}/step?task_id=task_1", json={
        "action_type":    "triage",
        "email_id":       email["id"],
        "category":       "normal",
        "priority_score": 0.5
    }).json()
    print(f"  {email['id']}: reward = {result['reward']}")

# 3. Get score
grade = httpx.post(f"{BASE}/grader?task_id=task_1").json()
print(f"\nScore: {grade['episode_score']}")
print(f"Grade: {grade['grade_letter']}")
print(f"Passed: {grade['passed']}")
```

Save as `run_episode.py` and run with `python run_episode.py`
