"""
Property-based tests for build_messages() — Property 2: user message always last.

**Validates: Requirements 3.7, 3.8**

Property: For any valid ChatRequest, the last message in the list returned by
build_messages() must always have role='user' and content equal to r.user_query.
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
def test_user_message_always_last(r: ChatRequest):
    """
    **Validates: Requirements 3.7, 3.8**

    Property 2: The last message produced by build_messages() must always be
    the current user message — regardless of history length, resume/JD content,
    or difficulty level.

    Assertions:
    - The final message role is 'user'.
    - The final message content equals r.user_query exactly.
    - The total message count is at least 2 (system prompt + user message).
    """
    messages = build_messages(r)

    # At minimum there must be a system message and the user message
    assert len(messages) >= 2, (
        f"Expected at least 2 messages (system + user), got {len(messages)}"
    )

    last_message = messages[-1]

    assert last_message["role"] == "user", (
        f"Expected last message role to be 'user', got '{last_message['role']}'"
    )

    assert last_message["content"] == r.user_query, (
        f"Expected last message content to equal user_query.\n"
        f"  user_query:       {r.user_query!r}\n"
        f"  last msg content: {last_message['content']!r}"
    )
