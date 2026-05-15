"""
Service/Agents/resume_agent.py — 简历诊断 Agent

负责：
  1. 构建简历诊断消息列表（调用 prompts/resume_prompts.py）
  2. 流式输出完成后提取六维评分并写入数据库
"""

import json
import re
from typing import List, Optional

from Service.Agents.base_agent import BaseAgent
from Service.Agents.prompts.resume_prompts import (
    RESUME_DIAGNOSIS_SYSTEM_PROMPT,
    build_resume_user_prompt,
)


class ResumeDiagnosisAgent(BaseAgent):
    """简历诊断专家 Agent。"""

    temperature: float = 0.7
    max_tokens: int = 4096

    def build_messages(
        self,
        resume_text: str = "",
        target_role: str = "",
        jd_text: str = "",
        **kwargs,
    ) -> List[dict]:
        """
        构建简历诊断消息列表。

        将 System Prompt 和用户 Prompt 合并为单条 user 消息，
        符合当前 DeepSeek API 的调用惯例。

        参数：
            resume_text — 候选人简历文本
            target_role — 目标岗位名称
            jd_text     — 岗位描述（可为空）
        """
        user_prompt = build_resume_user_prompt(
            resume_text=resume_text.replace("\r\n", "\n").strip(),
            target_role=target_role.replace("\r\n", "\n").strip(),
            jd_text=jd_text.replace("\r\n", "\n").strip(),
        )
        merged = (
            f"{RESUME_DIAGNOSIS_SYSTEM_PROMPT}\n\n"
            "====================\n\n"
            "【最高指令】：禁止复述我提供的材料，直接输出你的核心结论！\n\n"
            f"{user_prompt}"
        )
        return [{"role": "user", "content": merged}]

    async def on_stream_complete(
        self,
        full_text: str,
        resume_text: str = "",
        target_role: str = "",
        jd_text: str = "",
        user_id: Optional[int] = None,
        **kwargs,
    ) -> Optional[int]:
        """
        流式输出完成后：提取六维评分，写入历史记录数据库。

        参数：
            full_text   — 完整 AI 回复文本
            resume_text — 候选人简历（用于 extra_data 存档）
            target_role — 目标岗位
            jd_text     — 岗位描述
            user_id     — 当前用户 ID（可为 None，游客模式）

        返回：
            record_id — 数据库记录 ID
        """
        if not full_text:
            return None

        # 从 Markdown 代码块中提取六维评分 JSON
        scores = None
        try:
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', full_text)
            if json_match:
                scores = json.loads(json_match.group(1))
        except Exception:
            pass

        try:
            from Service.Utils.databases.db import insert_record

            record_id = insert_record(
                category="resume_diagnosis",
                user_input=f"目标岗位: {target_role or '未指定'}",
                ai_result=full_text[:5000],
                scores=scores,
                extra_data={
                    "resume_text": resume_text[:2000],
                    "target_role": target_role,
                    "jd_text": jd_text[:1000],
                },
                user_id=user_id,
            )
            return record_id
        except Exception as db_err:
            print(f"[ResumeDiagnosisAgent] 数据库写入失败: {db_err}")
            return None
