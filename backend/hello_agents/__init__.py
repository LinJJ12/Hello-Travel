"""本地 hello_agents 兼容层。

在保留原有 ``HelloAgentsLLM`` / ``SimpleAgent`` / ``MCPTool`` 接口的前提下，
为 LLM 调用补充超时、指数退避重试与统一日志，并提供结构化 JSON 生成能力。
"""

from __future__ import annotations

import os
import re
from typing import Any

from app.core.json_utils import extract_json
from app.core.logging import get_logger
from app.core.retry import retry_sync

from .tools import MCPTool

logger = get_logger(__name__)

# 需要重试的异常类型（网络/限流/服务端错误）
_RETRYABLE_ERRORS: tuple[type[BaseException], ...] = (Exception,)

# 明确不应重试的异常（配置/鉴权问题，重试无意义）
_FATAL_MARKERS = ("invalid_api_key", "incorrect api key", "authentication", "unauthorized")


class LLMError(RuntimeError):
    """LLM 调用失败的统一异常。"""


class HelloAgentsLLM:
    """OpenAI 兼容的轻量 LLM 包装器。"""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 120.0,
        max_retries: int = 3,
    ) -> None:
        from openai import OpenAI

        api_key = api_key or os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        base_url = (
            base_url
            or os.getenv("LLM_BASE_URL")
            or os.getenv("OPENAI_BASE_URL")
            or "https://api.openai.com/v1"
        )
        model = model or os.getenv("LLM_MODEL_ID") or os.getenv("OPENAI_MODEL") or "gpt-4"

        if not api_key:
            raise ValueError("未配置 LLM_API_KEY 或 OPENAI_API_KEY")

        self.provider = "openai-compatible"
        self.model = model
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self._client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout, max_retries=0)

    def _chat(self, messages: list[dict[str, str]], temperature: float, max_tokens: int) -> str:
        def _call() -> str:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""

        def _on_retry(attempt: int, exc: BaseException, delay: float) -> None:
            logger.warning("LLM 调用第 %s 次失败(%s)，%.1fs 后重试", attempt, exc, delay)

        try:
            return retry_sync(
                _call,
                attempts=self.max_retries,
                base_delay=1.0,
                factor=2.0,
                max_delay=10.0,
                exceptions=_RETRYABLE_ERRORS,
                on_retry=_on_retry,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("LLM 调用最终失败: %s", exc)
            raise LLMError(f"LLM 调用失败: {exc}") from exc

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> str:
        """生成文本。"""
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self._chat(messages, temperature, max_tokens)

    def generate_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> Any:
        """生成并解析为 JSON 对象（自动容错修复）。"""
        raw = self.generate(prompt, system_prompt=system_prompt, temperature=temperature, max_tokens=max_tokens)
        return extract_json(raw)


class SimpleAgent:
    """极简 Agent 兼容层。"""

    def __init__(self, name: str, llm: HelloAgentsLLM, system_prompt: str = "") -> None:
        self.name = name
        self.llm = llm
        self.system_prompt = system_prompt
        self._tools: list[Any] = []

    def add_tool(self, tool: Any) -> None:
        self._tools.append(tool)

    def list_tools(self) -> list[Any]:
        return list(self._tools)

    def run(self, prompt: str) -> str:
        tool_call_match = re.search(r"\[TOOL_CALL:([a-zA-Z0-9_]+):([^\]]+)\]", prompt)
        if tool_call_match and self._tools:
            tool_name = tool_call_match.group(1)
            argument_text = tool_call_match.group(2)
            arguments: dict[str, str] = {}
            for part in argument_text.split(","):
                if "=" in part:
                    key, value = part.split("=", 1)
                    arguments[key.strip()] = value.strip()

            tool = next(
                (candidate for candidate in self._tools if getattr(candidate, "name", None) == tool_name),
                self._tools[0],
            )
            return tool.run(
                {"action": "call_tool", "tool_name": tool_name, "arguments": arguments}
            )

        return self.llm.generate(prompt, system_prompt=self.system_prompt)


__all__ = ["HelloAgentsLLM", "SimpleAgent", "MCPTool", "LLMError"]
