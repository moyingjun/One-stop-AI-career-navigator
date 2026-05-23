"""
Router/llm_provider_router.py — LLM Provider 列表查询路由

提供两个端点：
  - GET /api/llm/providers — 返回所有可用 Provider（脱敏）
  - GET /api/llm/current   — 返回当前默认 Provider 信息

🛡️ 安全约束：
  - 响应字段白名单：id / display_name / model_name / status / is_default
  - 严格不返回 api_key、base_url 等敏感字段
"""

from fastapi import APIRouter

from Service.Utils.llm_provider_config import (
    get_default_provider_public,
    list_public_providers,
)

router = APIRouter(prefix="/api/llm", tags=["LLM Provider"])


@router.get("/providers")
async def list_providers():
    """
    返回所有可见的 Provider 列表（脱敏）。

    响应：
        [
          { "id": "mimo", "display_name": "MiMo 2.5", "model_name": "mimo-v2.5",
            "status": "online", "is_default": true },
          { "id": "deepseek", ... }
        ]
    """
    return {"success": True, "providers": list_public_providers()}


@router.get("/current")
async def current_provider():
    """返回当前默认 Provider 信息。"""
    provider = get_default_provider_public()
    return {"success": True, "provider": provider}
