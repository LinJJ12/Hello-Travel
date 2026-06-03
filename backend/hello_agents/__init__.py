"""本地 hello_agents 兼容层。"""

from .tools import MCPTool


class HelloAgentsLLM:
    """OpenAI 兼容的轻量 LLM 包装器。"""

    def __init__(self):
        import os
        from openai import OpenAI

        # 从环境变量读取配置，避免循环依赖
        api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1"
        model = os.getenv("LLM_MODEL_ID") or os.getenv("OPENAI_MODEL") or "gpt-4"

        if not api_key:
            raise ValueError("未配置 LLM_API_KEY 或 OPENAI_API_KEY")

        self.provider = "openai-compatible"
        self.model = model
        self._client = OpenAI(api_key=api_key, base_url=base_url)

    def generate(self, prompt: str, system_prompt: str | None = None, temperature: float = 0.2, max_tokens: int = 4096) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""


class SimpleAgent:
    """极简 Agent 兼容层。"""

    def __init__(self, name: str, llm: HelloAgentsLLM, system_prompt: str = ""):
        self.name = name
        self.llm = llm
        self.system_prompt = system_prompt
        self._tools = []

    def add_tool(self, tool):
        self._tools.append(tool)

    def list_tools(self):
        return list(self._tools)

    def run(self, prompt: str) -> str:
        import re

        tool_call_match = re.search(r"\[TOOL_CALL:([a-zA-Z0-9_]+):([^\]]+)\]", prompt)
        if tool_call_match and self._tools:
            tool_name = tool_call_match.group(1)
            argument_text = tool_call_match.group(2)
            arguments = {}
            for part in argument_text.split(","):
                if "=" in part:
                    key, value = part.split("=", 1)
                    arguments[key.strip()] = value.strip()

            tool = None
            for candidate in self._tools:
                if getattr(candidate, "name", None) == tool_name:
                    tool = candidate
                    break
            if tool is None:
                tool = self._tools[0]

            return tool.run({
                "action": "call_tool",
                "tool_name": tool_name,
                "arguments": arguments,
            })

        return self.llm.generate(prompt, system_prompt=self.system_prompt)
