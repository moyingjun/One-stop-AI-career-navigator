"""
Property-Based Test — Property 7: Evaluation scores unaffected by WARNING count

Validates: Requirements 7.3

The router's evaluate_interview endpoint must NOT apply any arithmetic deduction
based on the number of [WARNING] markers in the conversation history.
Score computation is delegated entirely to the LLM (call_deepseek); whatever
JSON the LLM returns is passed through unchanged.

Test strategy:
  - Mock call_deepseek to always return a fixed, deterministic score JSON.
  - Call evaluate_interview with histories containing 0, 1, 2, and 3 [WARNING]
    markers respectively.
  - Assert that the returned scores are identical across all four cases,
    proving no arithmetic deduction is applied by the router layer.
"""

import sys
import os
import json
import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock

# ---------------------------------------------------------------------------
# Path setup — make the Router package importable from the project root
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from Router.interview import evaluate_interview, EvaluateRequest  # noqa: E402

# ---------------------------------------------------------------------------
# Fixed score JSON that the mocked LLM always returns
# ---------------------------------------------------------------------------
FIXED_SCORE_JSON = (
    '{"professional": 75, "logic": 80, "communication": 70, '
    '"problemSolving": 65, "potential": 85, "resilience": 60, '
    '"comment": "表现良好"}'
)

EXPECTED_SCORES = {
    "professional": 75,
    "logic": 80,
    "communication": 70,
    "problemSolving": 65,
    "potential": 85,
    "resilience": 60,
    "comment": "表现良好",
}

# ---------------------------------------------------------------------------
# Helper — build a minimal conversation history with N [WARNING] markers
# ---------------------------------------------------------------------------

def _build_history(warning_count: int) -> list[dict]:
    """Return a history list that contains exactly `warning_count` [WARNING] markers."""
    history = [
        {"role": "user", "content": "你好，我准备好了"},
        {"role": "assistant", "content": "好的，我们开始面试。请先做个自我介绍。"},
        {"role": "user", "content": "我叫张三，有三年后端开发经验。"},
    ]
    for i in range(warning_count):
        history.append({
            "role": "assistant",
            "content": f"[WARNING] 你的回答完全是无效输入！这是第{i + 1}次警告。",
        })
        history.append({
            "role": "user",
            "content": "asdasd",
        })
    return history


# ---------------------------------------------------------------------------
# Property 7 tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scores_unaffected_by_zero_warnings():
    """
    **Validates: Requirements 7.3**

    With 0 [WARNING] markers the router must return the exact scores
    produced by the LLM — no modification applied.
    """
    request = EvaluateRequest(
        user_query="请评估",
        history=_build_history(0),
    )

    with patch("Router.interview.call_deepseek", new_callable=AsyncMock) as mock_llm, \
         patch("Router.interview.insert_record"):
        mock_llm.return_value = FIXED_SCORE_JSON

        response = await evaluate_interview(request)

    assert response["success"] is True
    data = response["data"]
    assert data["professional"] == EXPECTED_SCORES["professional"]
    assert data["logic"] == EXPECTED_SCORES["logic"]
    assert data["communication"] == EXPECTED_SCORES["communication"]
    assert data["problemSolving"] == EXPECTED_SCORES["problemSolving"]
    assert data["potential"] == EXPECTED_SCORES["potential"]
    assert data["resilience"] == EXPECTED_SCORES["resilience"]


@pytest.mark.asyncio
async def test_scores_unaffected_by_one_warning():
    """
    **Validates: Requirements 7.3**

    With 1 [WARNING] marker the router must NOT deduct any points.
    Scores must be identical to the LLM's raw output.
    """
    request = EvaluateRequest(
        user_query="请评估",
        history=_build_history(1),
    )

    with patch("Router.interview.call_deepseek", new_callable=AsyncMock) as mock_llm, \
         patch("Router.interview.insert_record"):
        mock_llm.return_value = FIXED_SCORE_JSON

        response = await evaluate_interview(request)

    assert response["success"] is True
    data = response["data"]
    assert data["professional"] == EXPECTED_SCORES["professional"], (
        f"Expected {EXPECTED_SCORES['professional']} but got {data['professional']} "
        "(router must not deduct for 1 WARNING)"
    )
    assert data["logic"] == EXPECTED_SCORES["logic"]
    assert data["communication"] == EXPECTED_SCORES["communication"]
    assert data["problemSolving"] == EXPECTED_SCORES["problemSolving"]
    assert data["potential"] == EXPECTED_SCORES["potential"]
    assert data["resilience"] == EXPECTED_SCORES["resilience"]


@pytest.mark.asyncio
async def test_scores_unaffected_by_two_warnings():
    """
    **Validates: Requirements 7.3**

    With 2 [WARNING] markers the router must NOT deduct any points.
    Scores must be identical to the LLM's raw output.
    """
    request = EvaluateRequest(
        user_query="请评估",
        history=_build_history(2),
    )

    with patch("Router.interview.call_deepseek", new_callable=AsyncMock) as mock_llm, \
         patch("Router.interview.insert_record"):
        mock_llm.return_value = FIXED_SCORE_JSON

        response = await evaluate_interview(request)

    assert response["success"] is True
    data = response["data"]
    assert data["professional"] == EXPECTED_SCORES["professional"], (
        f"Expected {EXPECTED_SCORES['professional']} but got {data['professional']} "
        "(router must not deduct for 2 WARNINGs)"
    )
    assert data["logic"] == EXPECTED_SCORES["logic"]
    assert data["communication"] == EXPECTED_SCORES["communication"]
    assert data["problemSolving"] == EXPECTED_SCORES["problemSolving"]
    assert data["potential"] == EXPECTED_SCORES["potential"]
    assert data["resilience"] == EXPECTED_SCORES["resilience"]


@pytest.mark.asyncio
async def test_scores_unaffected_by_three_warnings():
    """
    **Validates: Requirements 7.3**

    With 3 [WARNING] markers the router must NOT deduct any points.
    Scores must be identical to the LLM's raw output.
    The old EVALUATE_SYSTEM_PROMPT_V1 would have zeroed all scores at ≥3 warnings;
    the refactored endpoint using EVALUATE_SYSTEM_PROMPT_V2 must not do this.
    """
    request = EvaluateRequest(
        user_query="请评估",
        history=_build_history(3),
    )

    with patch("Router.interview.call_deepseek", new_callable=AsyncMock) as mock_llm, \
         patch("Router.interview.insert_record"):
        mock_llm.return_value = FIXED_SCORE_JSON

        response = await evaluate_interview(request)

    assert response["success"] is True
    data = response["data"]
    assert data["professional"] == EXPECTED_SCORES["professional"], (
        f"Expected {EXPECTED_SCORES['professional']} but got {data['professional']} "
        "(router must not zero scores for 3 WARNINGs)"
    )
    assert data["logic"] == EXPECTED_SCORES["logic"]
    assert data["communication"] == EXPECTED_SCORES["communication"]
    assert data["problemSolving"] == EXPECTED_SCORES["problemSolving"]
    assert data["potential"] == EXPECTED_SCORES["potential"]
    assert data["resilience"] == EXPECTED_SCORES["resilience"]


@pytest.mark.asyncio
async def test_scores_identical_across_all_warning_counts():
    """
    **Validates: Requirements 7.3**

    Parametric assertion: scores returned for 0, 1, 2, and 3 WARNING histories
    must all be identical, confirming the router applies zero arithmetic
    deduction regardless of WARNING count.
    """
    results = {}

    for warning_count in range(4):  # 0, 1, 2, 3
        request = EvaluateRequest(
            user_query="请评估",
            history=_build_history(warning_count),
        )

        with patch("Router.interview.call_deepseek", new_callable=AsyncMock) as mock_llm, \
             patch("Router.interview.insert_record"):
            mock_llm.return_value = FIXED_SCORE_JSON
            response = await evaluate_interview(request)

        assert response["success"] is True, (
            f"evaluate_interview failed for {warning_count} warnings"
        )
        results[warning_count] = response["data"]

    # All score dicts must be equal — no deduction applied by the router
    score_keys = ["professional", "logic", "communication", "problemSolving", "potential", "resilience"]
    baseline = results[0]

    for warning_count in [1, 2, 3]:
        for key in score_keys:
            assert results[warning_count][key] == baseline[key], (
                f"Score '{key}' differs between 0 warnings ({baseline[key]}) "
                f"and {warning_count} warnings ({results[warning_count][key]}). "
                "The router must not apply arithmetic deduction based on WARNING count."
            )
