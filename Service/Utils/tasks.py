"""
Service/Utils/tasks.py — Celery 异步任务定义

⚠️  Sync/Async 边界说明：
    Celery worker 运行在独立的同步进程中，与 FastAPI 的 asyncio 事件循环完全隔离。
    此文件中的所有 task 函数必须是普通同步函数（def），绝对不能使用 async def。
    Resend SDK 的调用是同步阻塞 I/O，在 Celery worker 中这是正确且安全的。
"""

import logging

import resend

from Service.Settings.config import RESEND_API_KEY
from Service.Utils.celery_app import celery_app

logger = logging.getLogger(__name__)

# 配置 Resend API Key（在 worker 进程中初始化一次即可）
resend.api_key = RESEND_API_KEY

# 发件人地址（生产域名：onestopainav.com 已在 Resend 完成 DNS 验证）
_FROM_ADDRESS = "One-stop AI Navigator <noreply@onestopainav.com>"


@celery_app.task(
    name="send_verification_email",
    bind=True,
    max_retries=3,
    default_retry_delay=10,  # 重试间隔 10 秒
)
def send_verification_email(self, email: str, code: str) -> dict:
    """
    同步 Celery task：通过 Resend SDK 发送邮箱验证码邮件。

    ⚠️  此函数必须保持同步（def），Celery 不支持 async task（除非使用特殊插件）。
        数据库写入已在 FastAPI 侧的 async service 中完成并 commit，
        此处仅负责网络 I/O（发邮件），不操作数据库。

    参数：
        email — 收件人邮箱地址
        code  — 6 位数字验证码

    返回：
        {"status": "sent", "email": email} — 发送成功
        发送失败时自动重试（最多 3 次），超出重试次数后抛出异常
    """
    try:
        # 1. 纯文本备份（html + text 双通道，物理降低垃圾邮件评分）
        text_content = (
            f"【One-stop AI Navigator】尊敬的先生/女士，您好！\n\n"
            f"您的登录验证码是：{code}\n\n"
            f"该验证码 5 分钟内有效，请勿泄露给他人。\n"
            f"如非本人操作，请直接忽略此邮件，您的账户依然安全。\n\n"
            f"— One-stop AI Navigator\n"
            f"  https://onestopainav.com"
        )

        # 2. 赛博暗黑霓虹 HTML 模板（全内联 CSS，兼容 Gmail / 网易 / QQ 邮箱）
        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>验证码 — One-stop AI Navigator</title></head>
<body style="margin: 0; padding: 0; background-color: #050505; font-family: 'Helvetica Neue', Arial, sans-serif;">
  <!-- Gmail 预览文本欺骗片段：对用户不可见，但 Gmail 扫描时优先读取此段，
       能有效中和后续大段 CSS 带来的"广告嫌疑"，提升事务性邮件评分 -->
  <div style="display: none; max-height: 0px; overflow: hidden; opacity: 0;">这是您的安全登录凭证，包含一次性验证码，请查收并妥善保管。</div>
  <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #0A0A10; padding: 30px 16px;">
    <tr>
      <td align="center">
        <!-- 主卡片：霓虹紫边框 + 外发光 + 顶部青色高亮线 -->
        <table width="560" cellpadding="0" cellspacing="0" border="0"
               style="max-width: 560px; width: 100%; background-color: #0A0A10;
                      border: 1px solid #7B61FF; border-radius: 16px;
                      box-shadow: 0 0 25px rgba(123, 97, 255, 0.45);
                      border-top: 3px solid #00D2FF;">

          <!-- 顶部赛博 Banner 图（网易/QQ 屏蔽外链时降级为纯色背景） -->
          <tr>
            <td style="padding: 0; line-height: 0; font-size: 0; background-color: #0D0D1A; border-radius: 13px 13px 0 0;">
              <img src="https://images.unsplash.com/photo-1563089145-599997674d42?q=80&w=600&auto=format&fit=crop"
                   alt="" width="560"
                   style="width: 100%; max-width: 560px; height: 140px; object-fit: cover;
                          display: block; opacity: 0.8; border-radius: 13px 13px 0 0;">
            </td>
          </tr>

          <!-- 正文区域 -->
          <tr>
            <td style="padding: 36px 36px 28px 36px;">

              <!-- 品牌 Logo 文字（渐变，Outlook 降级为 #00D2FF 纯色） -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 28px;">
                <tr>
                  <td align="center">
                    <div style="font-family: 'Arial Black', 'Helvetica Neue', Arial, sans-serif;
                                font-size: 26px; font-weight: 900; letter-spacing: -0.5px;
                                background: linear-gradient(135deg, #7B61FF 0%, #00D2FF 100%);
                                -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                                color: #00D2FF;">One-stop AI Navigator</div>
                    <div style="font-size: 11px; color: #4B5563; margin-top: 5px;
                                letter-spacing: 4px; text-transform: uppercase;">一站式 AI 领航员</div>
                  </td>
                </tr>
              </table>

              <!-- 正文 -->
              <p style="color: #F3F4F6; font-size: 15px; font-weight: 500; margin: 0 0 10px 0;">尊敬的 {email} 用户，您好：</p>
              <p style="color: #9CA3AF; font-size: 14px; line-height: 1.7; margin: 0 0 28px 0;">
                您正在登录 <span style="color: #00D2FF; font-weight: 600;">onestopainav.com</span>，请使用下方的 6 位安全动态密钥验证您的身份。该密钥将在
                <span style="color: #00D2FF; font-weight: 700;">5 分钟</span>后失效。
              </p>

              <!-- 验证码展示块：青色内发光边框 -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 28px;">
                <tr>
                  <td align="center"
                      style="padding: 26px 20px;
                             background-color: #050508;
                             border: 1px solid rgba(0, 210, 255, 0.35);
                             border-radius: 10px;">
                    <span style="font-size: 36px; font-weight: 900; color: #00D2FF;
                                 letter-spacing: 12px; font-family: 'Courier New', Courier, monospace;">{code}</span>
                  </td>
                </tr>
              </table>

              <!-- 安全提示 -->
              <p style="color: #4B5563; font-size: 12px; text-align: center; margin: 0; line-height: 1.6;">
                [ SECURITY NOTICE ]<br>
                如果这不是您本人的请求，请直接忽略此邮件。<br>您的账户资产目前处于安全受控状态。
              </p>

            </td>
          </tr>

          <!-- 底部版权 -->
          <tr>
            <td style="padding: 14px 36px 18px 36px; background-color: #050508;
                       border-top: 1px solid #111118; text-align: center; border-radius: 0 0 15px 15px;">
              <p style="color: #374151; font-size: 11px; margin: 0; letter-spacing: 0.5px;">
                © 2026 onestopainav.com. All rights reserved.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

        # 3. 终极组装参数（html + text 双通道发送）
        params: resend.Emails.SendParams = {
            "from": _FROM_ADDRESS,
            "to": [email],  # Resend SDK 要求列表格式
            "subject": "【One-stop AI Navigator】您的安全验证码",
            "text": text_content,
            "html": html_content,
        }
        response = resend.Emails.send(params)
        logger.info("验证码邮件发送成功 | email=%s | resend_id=%s", email, response.get("id"))
        return {"status": "sent", "email": email}

    except Exception as exc:
        logger.warning(
            "验证码邮件发送失败，准备重试 | email=%s | error=%s | retry=%d/%d",
            email,
            str(exc),
            self.request.retries,
            self.max_retries,
        )
        # 自动重试，超出 max_retries 后异常会被 Celery 记录为 FAILURE
        raise self.retry(exc=exc)
