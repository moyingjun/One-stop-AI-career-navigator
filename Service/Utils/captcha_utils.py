"""
Service/Utils/captcha_utils.py — Cloudflare Turnstile 人机验证工具

提供异步函数 verify_turnstile(token)，供 Router 层在处理敏感接口前调用。

开发模式：当 TURNSTILE_SECRET_KEY == 'mock_secret' 时直接返回 True，
          无需真实网络请求，方便本地开发和测试。
生产模式：向 Cloudflare Siteverify API 发起 POST 请求，校验前端传来的 token。
"""

import logging

import httpx

from Service.Settings.config import TURNSTILE_SECRET_KEY

logger = logging.getLogger(__name__)

# Cloudflare Turnstile 服务端验证接口
_TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"

# 开发模式标识
_IS_MOCK = TURNSTILE_SECRET_KEY == "mock_secret"


async def verify_turnstile(token: str) -> bool:
    """
    异步验证 Cloudflare Turnstile 人机验证 token。

    开发模式（TURNSTILE_SECRET_KEY == 'mock_secret'）：
        直接返回 True，跳过真实网络请求。

    生产模式：
        使用 httpx.AsyncClient 向 Cloudflare 发起 POST 请求，
        解析响应中的 success 字段。

    参数：
        token — 前端 Turnstile widget 生成的验证 token

    返回：
        True  — 验证通过（或开发模式跳过）
        False — 验证失败（token 无效、过期、网络异常等）
    """
    # ── 开发模式：直接放行 ──
    if _IS_MOCK:
        logger.debug("Turnstile 处于 mock 模式，跳过真实验证")
        return True

    # ── 生产模式：调用 Cloudflare API ──
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                _TURNSTILE_VERIFY_URL,
                data={
                    "secret": TURNSTILE_SECRET_KEY,
                    "response": token,
                },
            )
            response.raise_for_status()
            result = response.json()
            success: bool = result.get("success", False)

            if not success:
                error_codes = result.get("error-codes", [])
                logger.warning("Turnstile 验证失败 | error_codes=%s", error_codes)

            return success

    except httpx.TimeoutException:
        logger.error("Turnstile 验证超时")
        return False
    except httpx.HTTPStatusError as exc:
        logger.error("Turnstile API 返回异常状态码 | status=%d", exc.response.status_code)
        return False
    except Exception as exc:
        logger.error("Turnstile 验证发生未知异常 | error=%s", str(exc))
        return False
