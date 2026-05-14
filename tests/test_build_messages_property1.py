"""
Property-based tests for build_messages() — Property 1: system message always present.

**Validates: Requirements 3.6**

Property: For any valid ChatRequest, build_messages() must always return a list
whose first element has role == 'system' and content containing '你是一个专业面试官'.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from hypothesis import given, settings
from hypothesis import strategies as st

from Router.interview import build_messages, ChatRequest


@given(
    st.builds(
        ChatRequest,
        user_query=st.text(min_size=1),
        history=st.lists(
            st.fixed_dictionaries(
                {
                    "role": st.sampled_from(["user", "assistant"]),
                    "content": st.text(),
                }
            )
        ),
        resume_text=st.text(),
        jd_text=st.text(),
        difficulty=st.sampled_from(["beginner", "standard", "p8"]),
    )
)
@settings(max_examples=100)
def test_system_message_always_present(request: ChatRequest):
    """
    Property 1: The first message returned by build_messages() is always a
    system message whose content contains '你是一个专业面试官'.

    This holds regardless of user_query, history, resume_text, jd_text, or
    difficulty level.
    """
    messages = build_messages(request)

    # The message list must be non-empty
    assert len(messages) > 0, "build_messages() must return at least one message"

    first_message = messages[0]

    # First message must be the system message
    assert first_message["role"] == "system", (
        f"Expected first message role to be 'system', got '{first_message['role']}'"
    )

    # System message content must contain the interviewer identity string
    assert "你是一个专业面试官" in first_message["content"], (
        f"Expected '你是一个专业面试官' in system message content, "
        f"but got: {first_message['content'][:200]!r}"
    )
