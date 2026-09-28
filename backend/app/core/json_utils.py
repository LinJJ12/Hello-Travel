"""LLM 输出 JSON 的容错解析。

大模型返回的 JSON 常有各种瑕疵：包裹在 Markdown 代码块里、带行尾注释、
有多余尾逗号、被 ``max_tokens`` 截断导致括号不闭合等。
原实现只做简单的 ``find("```json")``，一旦格式略有偏差就整体失败并回退到
"占位景点" 兜底方案。

参考 TripStar / TripMate 等开源项目的做法，这里实现多级降级解析：
    1. 剥离 Markdown 代码围栏
    2. 用括号配平扫描截取第一个完整的 JSON 对象
    3. 修复行尾注释与尾逗号
    4. 补齐被截断的括号
    5. 逐级尝试 ``json.loads``，任一成功即返回
"""

from __future__ import annotations

import json
import re
from typing import Any

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)
_LINE_COMMENT_RE = re.compile(r"(?m)(?<![:/])//(?![^\n]*://).*$")
_TRAILING_COMMA_RE = re.compile(r",\s*([}\]])")


def strip_code_fences(text: str) -> str:
    """移除 Markdown 代码块围栏，返回其中的内容。"""
    match = _FENCE_RE.search(text)
    if match:
        return match.group(1).strip()
    return text.strip()


def extract_balanced_object(text: str) -> str | None:
    """扫描文本，返回第一个括号配平的 ``{...}`` 片段（正确处理字符串与转义）。"""
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def collapse_duplicate_commas(text: str) -> str:
    """折叠字符串**外部**的连续逗号（LLM 偶发 `,,` 或 `, ,`）。

    与正则方案不同，这里用状态机跟踪 ``in_string``/转义，确保字符串值内部的
    ``",,"`` 不会被误改。
    """
    out: list[str] = []
    in_string = False
    escaped = False
    # 逗号后暂存的空白：若后面还是逗号则一并丢弃，否则原样回填
    pending_space: list[str] = []

    def flush_pending() -> None:
        if pending_space:
            out.extend(pending_space)
            pending_space.clear()

    for char in text:
        if in_string:
            flush_pending()
            out.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            flush_pending()
            in_string = True
            out.append(char)
        elif char == ",":
            if out and out[-1] == ",":
                pending_space.clear()
                continue
            pending_space.clear()
            out.append(char)
        elif char.isspace():
            if out and out[-1] == ",":
                pending_space.append(char)
            else:
                out.append(char)
        else:
            flush_pending()
            out.append(char)

    flush_pending()
    return "".join(out)


def repair_json_text(text: str) -> str:
    """修复常见的 JSON 瑕疵：行尾注释、尾逗号与重复逗号。"""
    text = _LINE_COMMENT_RE.sub("", text)
    text = collapse_duplicate_commas(text)
    text = _TRAILING_COMMA_RE.sub(r"\1", text)
    return text


def close_unbalanced(text: str) -> str:
    """补齐被截断而未闭合的字符串与括号。"""
    stack: list[str] = []
    in_string = False
    escaped = False

    for char in text:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            stack.append("}")
        elif char == "[":
            stack.append("]")
        elif char in "}]" and stack and stack[-1] == char:
            stack.pop()

    if in_string:
        text += '"'
    text = re.sub(r",\s*$", "", text.rstrip())
    while stack:
        text += stack.pop()
    return text


def extract_json(text: str) -> Any:
    """从 LLM 输出中解析 JSON 对象。

    Raises:
        ValueError: 所有降级策略都失败时抛出。
    """
    if not text or not text.strip():
        raise ValueError("LLM 返回内容为空")

    stripped = strip_code_fences(text)
    candidates = [stripped]
    for source in (stripped, text):
        balanced = extract_balanced_object(source)
        if balanced:
            candidates.append(balanced)

    seen: set[str] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        for transform in (lambda s: s, repair_json_text, lambda s: repair_json_text(close_unbalanced(s))):
            try:
                return json.loads(transform(candidate))
            except (ValueError, TypeError):
                continue

    raise ValueError("无法从 LLM 输出中解析出 JSON")
