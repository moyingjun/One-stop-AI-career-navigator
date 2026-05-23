"""
Service/Utils/llm_provider_config.py — 多 LLM Provider 轻量配置层

支持通过 .env 配置多个 Provider，运行时根据 provider_id 动态选择：
  - MIMO_API_KEY / MIMO_BASE_URL / MIMO_MODEL_NAME
  - DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL / DEEPSEEK_MODEL_NAME

向后兼容：
  - 保留 LLM_API_KEY / LLM_BASE_URL / LLM_MODEL_NAME 作为 fallback Provider，
    避免现有 .env 失效。

安全约束：
  - api_key 仅在后端使用，公开接口必须通过 to_public_dict() 输出脱敏后的字段。

本模块为纯配置读取，无业务逻辑、无数据库依赖。
"""

import os
from typing import Optional

# Provider 默认 ID
LLM_DEFAULT_PROVIDER: str = (os.getenv("LLM_DEFAULT_PROVIDER") or "").strip().lower() or "mimo"


def _normalize_base_url(url: str) -> str:
    """统一补 /chat/completions 后缀，与现有 llm_client 行为一致。"""
    url = (url or "").strip()
    if not url:
        return ""
    if not url.endswith("chat/completions"):
        url = f"{url.rstrip('/')}/chat/completions"
    return url


class LLMProvider:
    """单个 Provider 的不可变配置载体（仅服务端可见）。"""

    def __init__(
        self,
        id: str,
        display_name: str,
        api_key: str,
        base_url: str,
        model_name: str,
        is_fallback: bool = False,
    ):
        self.id = id
        self.display_name = display_name
        self.api_key = (api_key or "").strip()
        self.base_url = _normalize_base_url(base_url)
        self.model_name = (model_name or "").strip()
        self.is_fallback = is_fallback

    @property
    def is_configured(self) -> bool:
        """三要素齐备才视为可用。"""
        return bool(self.api_key and self.base_url and self.model_name)

    @property
    def status(self) -> str:
        """unconfigured 表示缺少 api_key/base_url/model 任一项。"""
        return "online" if self.is_configured else "unconfigured"

    def to_public_dict(self, is_default: bool = False) -> dict:
        """
        生成给前端的安全字段（绝不包含 api_key / base_url）。

        前端只需要 id / display_name / model_name / status / is_default
        来渲染下拉和当前 Provider 提示。
        """
        return {
            "id": self.id,
            "display_name": self.display_name,
            "model_name": self.model_name,
            "status": self.status,
            "is_default": is_default,
        }


def _load_providers() -> dict:
    """
    从环境变量读取所有已知 Provider 配置。

    返回 {provider_id: LLMProvider}。
    """
    providers = {}

    # MiMo
    providers["mimo"] = LLMProvider(
        id="mimo",
        display_name="MiMo 2.5",
        api_key=os.getenv("MIMO_API_KEY", ""),
        base_url=os.getenv("MIMO_BASE_URL", ""),
        model_name=os.getenv("MIMO_MODEL_NAME", "mimo-v2.5"),
    )

    # DeepSeek
    providers["deepseek"] = LLMProvider(
        id="deepseek",
        display_name="DeepSeek V4",
        api_key=os.getenv("DEEPSEEK_API_KEY", ""),
        base_url=os.getenv("DEEPSEEK_BASE_URL", ""),
        model_name=os.getenv("DEEPSEEK_MODEL_NAME", "deepseek-v4-flash"),
    )

    # 通用 fallback Provider（兼容旧 LLM_* 环境变量）
    fallback_key = os.getenv("LLM_API_KEY", "")
    fallback_url = os.getenv("LLM_BASE_URL", "")
    fallback_model = os.getenv("LLM_MODEL_NAME", "")
    if fallback_key and fallback_url and fallback_model:
        providers["default"] = LLMProvider(
            id="default",
            display_name="Default LLM",
            api_key=fallback_key,
            base_url=fallback_url,
            model_name=fallback_model,
            is_fallback=True,
        )

    return providers


def get_provider(provider_id: Optional[str] = None) -> Optional[LLMProvider]:
    """
    按 ID 取 Provider；不传或不存在时回退默认 Provider。

    返回 None 仅当所有 Provider 都未配置（极端情况）。
    """
    providers = _load_providers()

    # 用户指定 ID
    if provider_id:
        normalized = provider_id.strip().lower()
        if normalized in providers and providers[normalized].is_configured:
            return providers[normalized]
        # 不存在或未配置 → 静默回退默认（不向前端暴露内部状态）

    # 默认 Provider
    default_id = LLM_DEFAULT_PROVIDER
    if default_id in providers and providers[default_id].is_configured:
        return providers[default_id]

    # 默认未配置 → 找第一个 configured 的
    for p in providers.values():
        if p.is_configured:
            return p

    return None


def list_public_providers() -> list[dict]:
    """
    返回前端可用的 Provider 列表（脱敏）。

    包含 unconfigured 状态的 Provider 用于让前端显示"未配置"灰态，
    但不包含 fallback default Provider（用户不应感知）。
    """
    providers = _load_providers()
    default_id = LLM_DEFAULT_PROVIDER

    # 如果默认 ID 是 "default"（fallback），用 "mimo" 作为前端默认显示
    if default_id == "default" or default_id not in providers:
        default_id = "mimo" if "mimo" in providers else next(iter(providers))

    out = []
    for pid, provider in providers.items():
        if provider.is_fallback:
            continue  # 不向前端暴露 fallback default Provider
        out.append(provider.to_public_dict(is_default=(pid == default_id)))
    return out


def get_default_provider_public() -> Optional[dict]:
    """返回当前默认 Provider 的脱敏字段。"""
    provider = get_provider(None)
    if not provider:
        return None
    is_default = provider.id == LLM_DEFAULT_PROVIDER
    return provider.to_public_dict(is_default=is_default)
