"""
Property-based tests for build_messages() — Property 8:
Resume and JD context present in every LLM call.

Validates: Requirements 3.4, 3.5
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from hypothesis import given, settings
from hypothesis import strategies as st

from Router.interview import build_messages, ChatRequest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_request(**kwargs) -> ChatRequest:
    """Build a minimal ChatRequest with sensible defaults."""
    defaults = {
        "user_query": "请开始面试",
        "history": [],
        "resume_text": "",
        "jd_text": "",
        "difficulty": "standard",
    }
    defaults.update(kwargs)
    return ChatRequest(**defaults)


# ---------------------------------------------------------------------------
# Test 1 — Resume context present when resume_text is non-empty
# Validates: Requirements 3.4
# **Validates: Requirements 3.4**
# ---------------------------------------------------------------------------

@given(resume_text=st.text(min_size=1))
@settings(max_examples=50)
def test_resume_context_present_in_system_message(resume_text: str):
    """
    Property 8a: For any ChatRequest where resume_text is non-empty,
    build_messages(r)[0]['content'] must contain the (stripped, truncated)
    resume text so the LLM always has the candidate's resume in context.
    """
    request = _make_request(resume_text=resume_text)
    messages = build_messages(request)

    system_content = messages[0]["content"]

    # Only assert when the stripped text is non-empty (mirrors build_messages logic)
    stripped = resume_text.strip()
    if stripped:
        expected_substring = stripped[:4000]
        assert expected_substring in system_content, (
            f"Expected resume substring not found in system message.\n"
            f"resume_text (first 80 chars): {repr(resume_text[:80])}\n"
            f"expected_substring (first 80 chars): {repr(expected_substring[:80])}"
        )


# ---------------------------------------------------------------------------
# Test 2 — JD context present when jd_text is non-empty
# Validates: Requirements 3.5
# **Validates: Requirements 3.5**
# ---------------------------------------------------------------------------

@given(jd_text=st.text(min_size=1))
@settings(max_examples=50)
def test_jd_context_present_in_system_message(jd_text: str):
    """
    Property 8b: For any ChatRequest where jd_text is non-empty,
    build_messages(r)[0]['content'] must contain the (stripped, truncated)
    JD text so the LLM always has the target role description in context.
    """
    request = _make_request(jd_text=jd_text)
    messages = build_messages(request)

    system_content = messages[0]["content"]

    # Only assert when the stripped text is non-empty (mirrors build_messages logic)
    stripped = jd_text.strip()
    if stripped:
        expected_substring = stripped[:3000]
        assert expected_substring in system_content, (
            f"Expected JD substring not found in system message.\n"
            f"jd_text (first 80 chars): {repr(jd_text[:80])}\n"
            f"expected_substring (first 80 chars): {repr(expected_substring[:80])}"
        )


# ---------------------------------------------------------------------------
# Test 3 — Blind mode: resume marker absent when resume_text is empty
# Validates: Requirements 3.4
# **Validates: Requirements 3.4**
# ---------------------------------------------------------------------------

@given(
    jd_text=st.one_of(st.just(""), st.text()),
    difficulty=st.sampled_from(["beginner", "standard", "p8"]),
)
@settings(max_examples=50)
def test_blind_mode_no_resume_marker_when_resume_empty(jd_text: str, difficulty: str):
    """
    Property 8c: For any ChatRequest where resume_text is the empty string '',
    build_messages(r)[0]['content'] must NOT contain '这是候选人的简历：',
    confirming that blind mode correctly omits the resume section.
    """
    request = _make_request(resume_text="", jd_text=jd_text, difficulty=difficulty)
    messages = build_messages(request)

    system_content = messages[0]["content"]

    assert "这是候选人的简历：" not in system_content, (
        "Resume marker '这是候选人的简历：' should not appear when resume_text is empty, "
        "but it was found in the system message."
    )
