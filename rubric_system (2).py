"""
rubric_system.py — OpenEnv Rubric-based Grading System

Implements the official OpenEnv Rubric pattern:
- Composable rubrics that can be mixed and stacked
- Each rubric scores one dimension independently
- Final score = weighted combination of all rubrics
- Compatible with openenv.core.env_server.Transform
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


# ── Base Rubric ────────────────────────────────────────────────────────────────

@dataclass
class RubricResult:
    """Result from a single rubric evaluation."""
    rubric_name:  str
    score:        float          # 0.0 to 1.0
    weight:       float          # how much this rubric counts
    weighted:     float          # score * weight
    reason:       str = ""       # human-readable explanation
    details:      dict = field(default_factory=dict)


class Rubric(ABC):
    """
    Base class for all rubrics.

    Every rubric evaluates one dimension of an action
    and returns a score between 0.0 and 1.0.
    Rubrics are composable — stack them freely.
    """

    def __init__(self, weight: float = 1.0, name: str = ""):
        self.weight = weight
        self.name   = name or self.__class__.__name__

    @abstractmethod
    def evaluate(self, action: dict, email: dict) -> RubricResult:
        """Score this dimension. Returns RubricResult."""
        ...

    def __call__(self, action: dict, email: dict) -> RubricResult:
        result = self.evaluate(action, email)
        result.rubric_name = self.name
        result.weight      = self.weight
        result.weighted    = result.score * self.weight
        return result


# ── Individual Rubrics ────────────────────────────────────────────────────────

class CategoryRubric(Rubric):
    """
    Scores whether the agent classified the email into the correct category.

    Scoring:
      Exact match              → 1.0  (full credit)
      Related category         → 0.5  (partial credit)
      Completely wrong         → 0.0
    """

    RELATED = {
        "urgent":   ["normal"],
        "normal":   ["urgent", "external"],
        "external": ["normal"],
        "internal": ["normal"],
        "low":      ["internal"],
        "spam":     [],
    }

    def __init__(self, weight: float = 0.40):
        super().__init__(weight=weight, name="CategoryAccuracy")

    def evaluate(self, action: dict, email: dict) -> RubricResult:
        predicted = str(action.get("category", "")).lower().strip()
        correct   = email["ground_truth"]["category"]
        gt_related = self.RELATED.get(correct, [])

        if predicted == correct:
            score  = 1.0
            reason = f"Correct: {predicted}"
        elif predicted in gt_related:
            score  = 0.50
            reason = f"Close: predicted {predicted}, correct {correct}"
        else:
            score  = 0.0
            reason = f"Wrong: predicted {predicted}, correct {correct}"

        return RubricResult(
            rubric_name = self.name,
            score       = score,
            weight      = self.weight,
            weighted    = score * self.weight,
            reason      = reason,
            details     = {"predicted": predicted, "correct": correct},
        )


class PriorityRubric(Rubric):
    """
    Scores how accurately the agent estimated the urgency score (0.0-1.0).

    Tiered forgiveness — small errors still earn partial credit:
      Error ≤ 0.10  → 1.0
      Error ≤ 0.25  → 0.75
      Error ≤ 0.40  → 0.40
      Error ≤ 0.60  → 0.15
      Error > 0.60  → 0.0
    """

    TIERS = [
        (0.10, 1.00),
        (0.25, 0.75),
        (0.40, 0.40),
        (0.60, 0.15),
    ]

    def __init__(self, weight: float = 0.30):
        super().__init__(weight=weight, name="PriorityEstimation")

    def evaluate(self, action: dict, email: dict) -> RubricResult:
        try:
            predicted = max(0.0, min(1.0, float(action.get("priority_score", 0.5) or 0.5)))
        except (TypeError, ValueError):
            predicted = 0.5

        correct = email["ground_truth"]["priority_score"]
        error   = abs(predicted - correct)

        score = 0.0
        for threshold, pts in self.TIERS:
            if error <= threshold:
                score = pts
                break

        return RubricResult(
            rubric_name = self.name,
            score       = score,
            weight      = self.weight,
            weighted    = score * self.weight,
            reason      = f"Error {error:.3f} → {score:.2f} score",
            details     = {"predicted": predicted, "correct": correct, "error": error},
        )


class ActionRubric(Rubric):
    """
    Scores whether the agent chose the correct action type.

    Scoring:
      Exact match              → 1.0
      Acceptable alternative   → 0.50
      Wrong                    → 0.0
    """

    ACCEPTABLE = {
        "escalate": ["flag"],
        "respond":  ["triage"],
        "triage":   ["respond"],
        "archive":  ["skip"],
        "flag":     ["escalate"],
        "skip":     ["archive"],
    }

    def __init__(self, weight: float = 0.30):
        super().__init__(weight=weight, name="ActionCorrectness")

    def evaluate(self, action: dict, email: dict) -> RubricResult:
        predicted = str(action.get("action_type", "archive")).lower()
        correct   = email["ground_truth"]["correct_action"]
        alt       = self.ACCEPTABLE.get(correct, [])

        if predicted == correct:
            score  = 1.0
            reason = f"Correct action: {predicted}"
        elif predicted in alt:
            score  = 0.50
            reason = f"Acceptable: {predicted} (correct: {correct})"
        else:
            score  = 0.0
            reason = f"Wrong action: {predicted} (correct: {correct})"

        return RubricResult(
            rubric_name = self.name,
            score       = score,
            weight      = self.weight,
            weighted    = score * self.weight,
            reason      = reason,
            details     = {"predicted": predicted, "correct": correct},
        )


class KeywordRubric(Rubric):
    """
    Synonym-aware keyword coverage rubric.

    Scores how many synonym groups the response covers.
    ANY word in a synonym group counts as a full group match.
    This is the most novel rubric in the system.
    """

    def __init__(self, synonym_groups: dict[str, list[list[str]]],
                 weight: float = 0.40):
        super().__init__(weight=weight, name="KeywordCoverage")
        self.synonym_groups = synonym_groups

    def evaluate(self, action: dict, email: dict) -> RubricResult:
        eid      = email.get("id", "")
        response = str(action.get("response_text", "")).lower()
        groups   = self.synonym_groups.get(eid, [])

        if not groups:
            return RubricResult(
                rubric_name = self.name,
                score       = 1.0,
                weight      = self.weight,
                weighted    = self.weight,
                reason      = "No keywords required",
            )

        hits = []
        for group in groups:
            matched = next((w for w in group if w in response), None)
            hits.append(matched is not None)

        coverage = sum(hits) / len(hits)

        return RubricResult(
            rubric_name = self.name,
            score       = coverage,
            weight      = self.weight,
            weighted    = coverage * self.weight,
            reason      = f"{sum(hits)}/{len(hits)} keyword groups covered",
            details     = {
                "groups":   len(groups),
                "hits":     sum(hits),
                "coverage": round(coverage, 3),
            },
        )


class ToneRubric(Rubric):
    """
    Scores professional tone in email responses.

    Checks for: professional opening, appropriate urgency language,
    professional closing.
    """

    OPENERS  = ["dear", "hi", "hello", "thank you", "greetings"]
    URGENCY  = ["immediately", "urgently", "asap", "right away", "priority"]
    CLOSERS  = ["regards", "sincerely", "best", "thank you", "kind regards"]

    def __init__(self, weight: float = 0.20):
        super().__init__(weight=weight, name="ToneQuality")

    def evaluate(self, action: dict, email: dict) -> RubricResult:
        response = str(action.get("response_text", "")).lower()
        gt       = email["ground_truth"]

        if not response or len(response.split()) < 10:
            return RubricResult(
                rubric_name = self.name,
                score       = 0.0,
                weight      = self.weight,
                weighted    = 0.0,
                reason      = "Response too short",
            )

        checks  = {}
        checks["professional_opener"] = any(o in response for o in self.OPENERS)
        checks["professional_closer"] = any(c in response for c in self.CLOSERS)

        if gt.get("priority_score", 0) >= 0.80:
            checks["urgency_language"] = any(u in response for u in self.URGENCY)
        else:
            checks["urgency_language"] = True  # not required for low-priority

        checks["adequate_length"] = len(response.split()) >= 20

        score  = sum(checks.values()) / len(checks)
        passed = [k for k, v in checks.items() if v]

        return RubricResult(
            rubric_name = self.name,
            score       = score,
            weight      = self.weight,
            weighted    = score * self.weight,
            reason      = f"{len(passed)}/{len(checks)} tone checks passed",
            details     = checks,
        )


class CriticalEmailRubric(Rubric):
    """
    Penalty rubric: heavy deduction if a critical email is archived.

    Critical = priority_score >= 0.88
    Archiving a critical email = -0.80 on this rubric
    """

    THRESHOLD = 0.88

    def __init__(self, weight: float = 0.15):
        super().__init__(weight=weight, name="CriticalHandling")

    def evaluate(self, action: dict, email: dict) -> RubricResult:
        priority    = email["ground_truth"]["priority_score"]
        action_type = action.get("action_type", "")

        if priority < self.THRESHOLD:
            return RubricResult(
                rubric_name = self.name,
                score       = 1.0,
                weight      = self.weight,
                weighted    = self.weight,
                reason      = "Not a critical email",
            )

        if action_type == "archive":
            score  = 0.0
            reason = f"CRITICAL email archived! Priority={priority:.2f}"
        elif action_type in ["escalate", "respond", "flag"]:
            score  = 1.0
            reason = f"Critical email handled correctly: {action_type}"
        else:
            score  = 0.40
            reason = f"Critical email: acceptable but not ideal: {action_type}"

        return RubricResult(
            rubric_name = self.name,
            score       = score,
            weight      = self.weight,
            weighted    = score * self.weight,
            reason      = reason,
            details     = {"priority": priority, "action": action_type},
        )


# ── Rubric Composer ───────────────────────────────────────────────────────────

class RubricComposer:
    """
    Composes multiple rubrics into a single grader.

    Weights are normalised automatically — they don't need to sum to 1.0.
    This makes it easy to add/remove rubrics without manual rebalancing.
    """

    def __init__(self, rubrics: list[Rubric]):
        self.rubrics = rubrics
        total        = sum(r.weight for r in rubrics)
        # Normalise weights
        for r in self.rubrics:
            r.weight = r.weight / total

    def grade(self, action: dict, email: dict) -> dict:
        """Grade one action against one email. Returns full breakdown."""
        results = [rubric(action, email) for rubric in self.rubrics]
        total   = sum(r.weighted for r in results)

        # Clamp strictly between 0 and 1 (validator requirement)
        clamped = max(0.0001, min(0.9999, total))

        return {
            "total":     round(clamped, 4),
            "breakdown": {
                r.rubric_name: {
                    "score":    round(r.score, 4),
                    "weight":   round(r.weight, 4),
                    "weighted": round(r.weighted, 4),
                    "reason":   r.reason,
                    "details":  r.details,
                }
                for r in results
            },
            "rubrics_used": len(results),
        }


# ── Pre-built Composers ───────────────────────────────────────────────────────

def make_triage_composer() -> RubricComposer:
    """Task 1 — Email Triage rubric set."""
    return RubricComposer([
        CategoryRubric(weight=0.40),
        PriorityRubric(weight=0.30),
        ActionRubric(weight=0.30),
    ])


def make_response_composer(synonym_groups: dict) -> RubricComposer:
    """Task 2 — Response Drafting rubric set."""
    return RubricComposer([
        ActionRubric(weight=0.20),
        KeywordRubric(synonym_groups, weight=0.40),
        ToneRubric(weight=0.20),
        PriorityRubric(weight=0.20),
    ])


def make_inbox_zero_composer(synonym_groups: dict) -> RubricComposer:
    """Task 3 — Inbox Zero Sprint rubric set."""
    return RubricComposer([
        CategoryRubric(weight=0.25),
        PriorityRubric(weight=0.20),
        ActionRubric(weight=0.20),
        CriticalEmailRubric(weight=0.20),
        ToneRubric(weight=0.15),
    ])


# ── Demo / Test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Sample email (matches our environment format)
    sample_email = {
        "id":   "e001",
        "subject": "CRITICAL: Production database down",
        "sender":  "alerts@pagerduty.com",
        "ground_truth": {
            "category":      "urgent",
            "priority_score": 1.0,
            "correct_action": "escalate",
        }
    }

    # Perfect action
    perfect_action = {
        "action_type":    "escalate",
        "category":       "urgent",
        "priority_score": 1.0,
        "escalate_to":    "backend-oncall",
    }

    # Bad action
    bad_action = {
        "action_type":    "archive",
        "category":       "spam",
        "priority_score": 0.0,
    }

    composer = make_triage_composer()

    print("=== RUBRIC SYSTEM TEST ===\n")

    print("Perfect action:")
    result = composer.grade(perfect_action, sample_email)
    print(f"  Total score: {result['total']}")
    for name, detail in result['breakdown'].items():
        print(f"  {name}: {detail['score']:.2f} × {detail['weight']:.2f} = {detail['weighted']:.3f}  ({detail['reason']})")

    print("\nBad action (archive P0):")
    result2 = composer.grade(bad_action, sample_email)
    print(f"  Total score: {result2['total']}")
    for name, detail in result2['breakdown'].items():
        print(f"  {name}: {detail['score']:.2f} × {detail['weight']:.2f} = {detail['weighted']:.3f}  ({detail['reason']})")
