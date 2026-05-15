from .jobResume_model import uploadBody
from .interview_model import ChatRequest, EvaluateRequest
from .resume_model import ResumeDiagnoseRequest
from .career_model import CareerPlanRequest, CareerSuggestionsRequest
from .agent_model import AgentChatRequest, ChatMessage
from .auth_model import RegisterRequest, LoginRequest, AuthResponse
from .history_model import SaveRecordRequest

__all__ = [
    "uploadBody",
    "ChatRequest", "EvaluateRequest",
    "ResumeDiagnoseRequest",
    "CareerPlanRequest", "CareerSuggestionsRequest",
    "AgentChatRequest", "ChatMessage",
    "RegisterRequest", "LoginRequest", "AuthResponse",
    "SaveRecordRequest",
]
