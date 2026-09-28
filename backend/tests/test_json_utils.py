"""容错 JSON 解析的单元测试。"""

from __future__ import annotations

import pytest

from app.core.json_utils import extract_json


def test_plain_json():
    assert extract_json('{"a": 1}') == {"a": 1}


def test_fenced_json():
    text = '这是结果:\n```json\n{"city": "北京", "days": []}\n```\n以上。'
    assert extract_json(text) == {"city": "北京", "days": []}


def test_fenced_without_language():
    text = "```\n{\"a\": [1, 2, 3]}\n```"
    assert extract_json(text) == {"a": [1, 2, 3]}


def test_leading_and_trailing_prose():
    text = '好的，我来规划：{"city": "上海"} 希望有帮助！'
    assert extract_json(text) == {"city": "上海"}


def test_trailing_comma_repair():
    assert extract_json('{"a": 1, "b": 2,}') == {"a": 1, "b": 2}


def test_line_comment_repair():
    text = '{\n  "a": 1, // 这是注释\n  "b": 2\n}'
    assert extract_json(text) == {"a": 1, "b": 2}


def test_truncated_json_is_closed():
    text = '{"city": "北京", "days": [{"day_index": 0, "attractions": [{"name": "故宫"'
    result = extract_json(text)
    assert result["city"] == "北京"
    assert result["days"][0]["attractions"][0]["name"] == "故宫"


def test_nested_braces_inside_strings():
    text = '{"note": "使用 {花括号} 与 \\"引号\\"", "ok": true}'
    assert extract_json(text) == {"note": '使用 {花括号} 与 "引号"', "ok": True}


def test_empty_raises():
    with pytest.raises(ValueError):
        extract_json("")


def test_no_json_raises():
    with pytest.raises(ValueError):
        extract_json("这里完全没有 JSON")


# --------------------------------------------------------------------------- #
# 重复逗号容错（collapse_duplicate_commas）
# --------------------------------------------------------------------------- #
def test_duplicate_comma_is_repaired():
    assert extract_json('{"a": 1,, "b": 2}') == {"a": 1, "b": 2}


def test_duplicate_comma_with_spaces_is_repaired():
    assert extract_json('{"a": 1, , "b": 2}') == {"a": 1, "b": 2}


def test_triple_comma_is_repaired():
    assert extract_json('{"a": 1,,, "b": 2}') == {"a": 1, "b": 2}


def test_duplicate_comma_inside_string_is_preserved():
    """字符串值内部的 ",," 不能被误改。"""
    text = '{"note": "a,,b", "c": 1}'
    assert extract_json(text) == {"note": "a,,b", "c": 1}


def test_duplicate_comma_in_array_is_repaired():
    assert extract_json('{"a": [1,, 2]}') == {"a": [1, 2]}


def test_collapse_duplicate_commas_directly():
    from app.core.json_utils import collapse_duplicate_commas

    assert collapse_duplicate_commas('{"a": 1,, "b": 2}') == '{"a": 1, "b": 2}'
    assert collapse_duplicate_commas('["x",, "y"]') == '["x", "y"]'
    # 合法 JSON 不受影响
    assert collapse_duplicate_commas('{"a": [1, 2], "b": "x,y"}') == '{"a": [1, 2], "b": "x,y"}'
