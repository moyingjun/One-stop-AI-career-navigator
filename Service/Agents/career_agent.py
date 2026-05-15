"""
Service/Agents/career_agent.py — 职业规划 Agent

包含两个 Agent：
  - CareerPlanAgent       — 职业规划流式生成 Agent
  - CareerSuggestAgent    — 推荐问题生成 Agent（非流式）
"""

import json
from typing import List, Optional

from Service.Agents.base_agent import BaseAgent
from Service.Agents.prompts.career_prompts import (
    CAREER_SYSTEM_PROMPT,
    DEFAULT_SUGGESTIONS,
    SUGGESTIONS_SYSTEM_PROMPT,
    build_career_user_prompt,
    build_suggestions_user_prompt,
)


class CareerPlanAgent(BaseAgent):
    """职业规划流式生成 Agent。"""

    temperature: float = 0.7
    max_tokens: int = 4096

    def build_messages(
        self,
        resume_text: str = "",
        user_confusion: str = "",
        **kwargs,
    ) -> List[dict]:
        """
        构建职业规划消息列表。

        参数：
            resume_text    — 候选人简历文本
            user_confusion — 用户的职业困惑或期望
        """
        user_prompt = build_career_user_prompt(resume_text, user_confusion)
        merged = (
            f"{CAREER_SYSTEM_PROMPT}\n\n"
            "====================\n\n"
            "【最高指令】：禁止复述我提供的材料，直接输出你的核心结论！\n\n"
            f"{user_prompt}"
        )
        return [{"role": "user", "content": merged}]

    async def on_stream_complete(
        self,
        full_text: str,
        resume_text: str = "",
        user_confusion: str = "",
        user_id: Optional[int] = None,
        **kwargs,
    ) -> Optional[int]:
        """
        流式输出完成后写入历史记录数据库。

        参数：
            full_text      — 完整 AI 回复文本
            resume_text    — 候选人简历
            user_confusion — 用户困惑
            user_id        — 当前用户 ID
        """
        if not full_text:
            return None

        try:
            from Service.Utils.databases.db import insert_record

            record_id = insert_record(
                category="career_planning",
                user_input=f"困惑: {user_confusion[:200]}",
                ai_result=full_text[:5000],
                scores=None,
                extra_data={
                    "resume_text": resume_text[:2000],
                    "user_confusion": user_confusion[:500],
                },
                user_id=user_id,
            )
            return record_id
        except Exception as db_err:
            print(f"[CareerPlanAgent] 数据库写入失败: {db_err}")
            return None


class CareerSuggestAgent(BaseAgent):
    """职业推荐问题生成 Agent（非流式）。"""

    temperature: float = 0.7
    max_tokens: int = 512

    def build_messages(self, resume_text: str = "", **kwargs) -> List[dict]:
        """
        构建推荐问题生成消息列表。

        参数：
            resume_text — 候选人简历文本
        """
        user_prompt = build_suggestions_user_prompt(resume_text)
        merged = (
            f"{SUGGESTIONS_SYSTEM_PROMPT}\n\n"
            "====================\n\n"
            "【最高指令】：禁止复述我提供的材料，直接输出你的核心结论！\n\n"
            f"{user_prompt}"
        )
        return [{"role": "user", "content": merged}]

    async def get_suggestions(self, resume_text: str) -> List[str]:
        """
        生成职业推荐问题列表。

        参数：
            resume_text — 候选人简历文本

        返回：
            包含 4 个推荐问题的字符串列表；生成失败时返回默认兜底列表
        """
        raw = await self.complete(resume_text=resume_text)
        if not raw:
            return DEFAULT_SUGGESTIONS

        return self._parse_suggestions(raw)

    @staticmethod
    def _parse_suggestions(text: str) -> List[str]:
        """
        从模型回复中解析推荐问题 JSON 数组。

        参数：
            text — 模型原始回复文本

        返回：
            字符串列表；解析失败时返回默认兜底列表
        """
        try:
            start = text.find("[")
            end = text.rfind("]") + 1
            if start != -1 and end > start:
                arr = json.loads(text[start:end])
                if isinstance(arr, list) and len(arr) > 0:
                    return [str(item).strip() for item in arr if str(item).strip()]
        except (json.JSONDecodeError, ValueError):
            pass
        return DEFAULT_SUGGESTIONS
