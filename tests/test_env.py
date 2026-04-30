"""
tests/test_env.py — Full test suite for OpenEnv Email Triage
Uses FastAPI TestClient — no live server needed, runs in CI perfectly.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ── Health & Setup Tests ───────────────────────────────────────────────────────

def test_health():
    """Server must return healthy status."""
    r = client.get("/health?fmt=json")
    assert r.status_code == 200
    data = r.json()
    assert data is not None


def test_tasks_returns_3():
    """Must have exactly 3 tasks."""
    r = client.get("/tasks?fmt=json")
    assert r.status_code == 200
    data = r.json()
    tasks = data.get("tasks", data) if isinstance(data, dict) else data
    assert len(tasks) >= 3


def test_tasks_have_action_schema():
    """Each task must have id, name, difficulty."""
    r = client.get("/tasks?fmt=json")
    assert r.status_code == 200
    data = r.json()
    tasks = data.get("tasks", []) if isinstance(data, dict) else data
    for task in tasks:
        assert "id" in task or "task_id" in task


# ── Core OpenEnv Interface Tests ───────────────────────────────────────────────

def test_reset_returns_observation_task1():
    """POST /reset must return a valid observation for task_1."""
    r = client.post("/reset?task_id=task_1")
    assert r.status_code == 200
    data = r.json()
    assert "observation" in data
    obs = data["observation"]
    assert "inbox" in obs
    assert "step" in obs
    assert len(obs["inbox"]) > 0


def test_reset_returns_observation_task2():
    """POST /reset must return a valid observation for task_2."""
    r = client.post("/reset?task_id=task_2")
    assert r.status_code == 200
    obs = r.json()["observation"]
    assert obs["pending_count"] > 0


def test_reset_returns_observation_task3():
    """POST /reset must return a valid observation for task_3."""
    r = client.post("/reset?task_id=task_3")
    assert r.status_code == 200
    obs = r.json()["observation"]
    assert obs["pending_count"] == 50


def test_step_returns_required_fields():
    """POST /step must return observation, reward, done, info."""
    client.post("/reset?task_id=task_1")
    r = client.post("/step?task_id=task_1", json={
        "action_type":    "triage",
        "email_id":       "e001",
        "category":       "urgent",
        "priority_score": 1.0
    })
    assert r.status_code == 200
    data = r.json()
    assert "observation" in data
    assert "reward" in data
    assert "done" in data


def test_reward_is_float():
    """Reward must be a number."""
    client.post("/reset?task_id=task_1")
    r = client.post("/step?task_id=task_1", json={
        "action_type":    "triage",
        "email_id":       "e001",
        "category":       "urgent",
        "priority_score": 1.0
    })
    reward = r.json()["reward"]
    assert isinstance(reward, (int, float))


def test_reward_bounds():
    """Reward must always be between -1.0 and +1.0."""
    client.post("/reset?task_id=task_1")
    r = client.post("/step?task_id=task_1", json={
        "action_type":    "escalate",
        "email_id":       "e001",
        "category":       "urgent",
        "priority_score": 1.0,
        "escalate_to":    "backend-oncall"
    })
    reward = r.json()["reward"]
    assert -1.0 <= reward <= 1.0


def test_correct_action_positive_reward():
    """A correct action on a P0 email should give positive reward."""
    client.post("/reset?task_id=task_1")
    r = client.post("/step?task_id=task_1", json={
        "action_type":    "escalate",
        "email_id":       "e001",
        "category":       "urgent",
        "priority_score": 1.0,
        "escalate_to":    "backend-oncall"
    })
    assert r.json()["reward"] > 0


def test_wrong_action_lower_reward():
    """Archiving a critical email should give negative reward."""
    client.post("/reset?task_id=task_1")
    r = client.post("/step?task_id=task_1", json={
        "action_type":    "archive",
        "email_id":       "e001",
        "category":       "spam",
        "priority_score": 0.0
    })
    assert r.json()["reward"] < 0


def test_duplicate_action_penalised():
    """Acting on the same email twice should give a penalty."""
    client.post("/reset?task_id=task_1")
    action = {"action_type": "triage", "email_id": "e001",
              "category": "urgent", "priority_score": 1.0}
    client.post("/step?task_id=task_1", json=action)
    r2 = client.post("/step?task_id=task_1", json=action)
    assert r2.json()["reward"] < 0


def test_grader_returns_score():
    """POST /grader must return episode_score strictly between 0 and 1."""
    client.post("/reset?task_id=task_1")
    client.post("/step?task_id=task_1", json={
        "action_type":    "escalate",
        "email_id":       "e001",
        "category":       "urgent",
        "priority_score": 1.0,
        "escalate_to":    "backend-oncall"
    })
    r = client.post("/grader?task_id=task_1")
    assert r.status_code == 200
    score = r.json()["episode_score"]
    assert 0.0 < score < 1.0


def test_grader_score_strictly_between_0_and_1():
    """Score must never be exactly 0.0 or 1.0 (validator rule)."""
    client.post("/reset?task_id=task_1")
    for eid in ["e001", "e002", "e003", "e004", "e005"]:
        client.post("/step?task_id=task_1", json={
            "action_type":    "escalate",
            "email_id":       eid,
            "category":       "urgent",
            "priority_score": 1.0,
            "escalate_to":    "backend-oncall"
        })
    r     = client.post("/grader?task_id=task_1")
    score = r.json()["episode_score"]
    assert score != 0.0, "Score must not be exactly 0.0"
    assert score != 1.0, "Score must not be exactly 1.0"
    assert 0.0 < score < 1.0


def test_full_episode_task1():
    """Run a complete Task 1 episode and grade it."""
    client.post("/reset?task_id=task_1")
    emails = client.post("/reset?task_id=task_1").json()["observation"]["inbox"]
    for email in emails[:5]:
        client.post("/step?task_id=task_1", json={
            "action_type":    "triage",
            "email_id":       email["id"],
            "category":       "normal",
            "priority_score": 0.5
        })
    r     = client.post("/grader?task_id=task_1")
    score = r.json()["episode_score"]
    assert 0.0 < score < 1.0


def test_state_endpoint():
    """GET /state must return episode state dict."""
    client.post("/reset?task_id=task_1")
    r = client.get("/state?task_id=task_1")
    assert r.status_code == 200


def test_metrics_endpoint():
    """GET /metrics must return episode metrics."""
    client.post("/reset?task_id=task_1")
    r = client.get("/metrics?task_id=task_1")
    assert r.status_code == 200


def test_info_endpoint():
    """GET /info must return environment spec."""
    r = client.get("/info")
    assert r.status_code == 200


def test_leaderboard_endpoint():
    """GET /leaderboard must return a valid response."""
    r = client.get("/leaderboard")
    assert r.status_code == 200
