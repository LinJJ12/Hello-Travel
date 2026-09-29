"""端到端真实测试：直接对运行中的 uvicorn 实例发请求。

覆盖：健康检查 / SPA 托管 / 运行时配置读写 / 地图与 POI 接口 / 行程任务
提交-轮询-WebSocket / 各类错误路径（400/404/422）/ 路径穿越防护。
"""
from __future__ import annotations

import json
import os
import sys
import time

import httpx

# 默认端口刻意避开 18080：该端口常被本机 Docker 发布的其他项目容器占用
# （例如 `zilv-web` 映射 `0.0.0.0:18080->80`），撞上会连错服务。
# 需要时用环境变量覆盖：
#     E2E_BASE_URL=http://127.0.0.1:9000 python scripts/e2e_check.py
BASE = os.getenv("E2E_BASE_URL", "http://127.0.0.1:18081")
WS_BASE = BASE.replace("https://", "wss://").replace("http://", "ws://")
PASS: list[str] = []
FAIL: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        PASS.append(name)
        print(f"  PASS  {name}")
    else:
        FAIL.append(f"{name} :: {detail}")
        print(f"  FAIL  {name} :: {detail}")


def main() -> int:
    c = httpx.Client(base_url=BASE, timeout=30.0, trust_env=False)

    print("\n[1] 基础与健康检查")
    r = c.get("/health")
    check("GET /health 200", r.status_code == 200, str(r.status_code))
    check("health.status==healthy", r.json().get("status") == "healthy", r.text[:120])
    check("health.version==2.2.0", r.json().get("version") == "2.2.0", r.text[:120])

    r = c.get("/")
    check("GET / 返回前端页面(200)", r.status_code == 200, str(r.status_code))
    check("GET / 是 HTML", "text/html" in r.headers.get("content-type", ""), r.headers.get("content-type", ""))

    r = c.get("/docs")
    check("GET /docs 可访问", r.status_code == 200, str(r.status_code))

    print("\n[2] 运行时配置读写")
    r = c.get("/api/settings")
    check("GET /api/settings 200", r.status_code == 200, str(r.status_code))
    data = r.json().get("data", {})
    check("settings 含 amap key 字段", "vite_amap_web_key" in data, str(list(data)[:8]))
    check("密钥已脱敏(非明文)", not str(data.get("openai_api_key", "")).startswith("sk-"), str(data.get("openai_api_key")))

    r = c.put("/api/settings", json={"openai_model": "gpt-4o-mini"})
    check("PUT /api/settings 200", r.status_code == 200, str(r.status_code))
    check("PUT 回显新模型", r.json().get("data", {}).get("openai_model") == "gpt-4o-mini", r.text[:160])
    r = c.get("/api/settings")
    check("PUT 后 GET 已生效", r.json().get("data", {}).get("openai_model") == "gpt-4o-mini", r.text[:160])

    print("\n[3] 地图接口（未配置 Key 时应优雅降级而非 500）")
    r = c.get("/api/map/health")
    check("GET /api/map/health 200(回归:原为500)", r.status_code == 200, str(r.status_code))
    body = r.json()
    check("map/health 含 amap_configured", "amap_configured" in body, str(body))
    check("map/health amap_configured==False", body.get("amap_configured") is False, str(body))

    r = c.get("/api/map/poi", params={"keywords": "故宫", "city": "北京"})
    check("GET /api/map/poi 200", r.status_code == 200, str(r.status_code))
    check("map/poi success=False 且 data 为空", r.json().get("success") is False and r.json().get("data") == [], r.text[:160])

    r = c.get("/api/map/weather", params={"city": "北京"})
    check("GET /api/map/weather 200", r.status_code == 200, str(r.status_code))
    check("map/weather success=False", r.json().get("success") is False, r.text[:160])

    r = c.post("/api/map/route", json={"origin_address": "A", "destination_address": "B"})
    check("POST /api/map/route 200(回归:原空dict会422)", r.status_code == 200, f"{r.status_code} {r.text[:200]}")
    check("map/route success=False data=None", r.json().get("success") is False and r.json().get("data") is None, r.text[:200])

    print("\n[4] POI 接口")
    r = c.get("/api/poi/search", params={"keywords": "西湖", "city": "杭州"})
    check("GET /api/poi/search 200", r.status_code == 200, str(r.status_code))

    r = c.get("/api/poi/detail/anything")
    check("GET /api/poi/detail 200", r.status_code == 200, str(r.status_code))

    r = c.get("/api/poi/image")
    check("GET /api/poi/image 无参数→400", r.status_code == 400, str(r.status_code))

    r = c.get("/api/poi/image", params={"url": "https://evil.example.com/a.jpg"})
    check("图片代理非白名单域名→400(SSRF防护)", r.status_code == 400, f"{r.status_code} {r.text[:160]}")

    print("\n[5] 行程任务：提交 → 轮询 → WebSocket")
    r = c.get("/api/trip/health")
    check("GET /api/trip/health 200", r.status_code == 200, f"{r.status_code} {r.text[:200]}")

    r = c.get("/api/trip/history")
    check("GET /api/trip/history 200", r.status_code == 200, str(r.status_code))
    check("history 含 items", "items" in r.json(), r.text[:120])

    payload = {
        "city": "杭州",
        "start_date": "2026-10-01",
        "end_date": "2026-10-02",
        "travel_days": 2,
        "transportation": "公共交通",
        "accommodation": "经济型酒店",
        "preferences": ["历史文化"],
        "free_text_input": "",
        "language": "zh",
    }
    r = c.post("/api/trip/plan", json=payload)
    check("POST /api/trip/plan 200", r.status_code == 200, f"{r.status_code} {r.text[:200]}")
    task = r.json()
    tid = task.get("task_id", "")
    check("返回 task_id", bool(tid), str(task))
    check("返回 ws_url", task.get("ws_url") == f"/api/trip/ws/{tid}", str(task))

    # 轮询直到终态（无 LLM Key，预期 failed 且带可读错误信息）
    final = None
    for _ in range(60):
        rr = c.get(f"/api/trip/status/{tid}")
        if rr.status_code != 200:
            break
        st = rr.json()
        if st.get("status") in ("completed", "failed"):
            final = st
            break
        time.sleep(1)

    check("任务到达终态", final is not None, "轮询超时")
    if final:
        check("无 Key 时任务失败且带错误说明", final.get("status") == "failed" and bool(final.get("error")), json.dumps(final, ensure_ascii=False)[:220])
        check("失败时回传 request_payload", final.get("request_payload") is not None, str(final)[:160])

    # WebSocket 订阅（对已完成任务应立刻收到快照）
    try:
        import websockets

        async def ws_probe() -> dict:
            import asyncio

            async with websockets.connect(f"{WS_BASE}/api/trip/ws/{tid}") as ws:
                return json.loads(await asyncio.wait_for(ws.recv(), timeout=15))

        import asyncio

        snap = asyncio.run(ws_probe())
        check("WebSocket 收到快照", snap.get("task_id") == tid, str(snap)[:200])
        check("WebSocket 快照含 status", "status" in snap, str(snap)[:200])
    except Exception as exc:  # noqa: BLE001
        check("WebSocket 订阅", False, f"{type(exc).__name__}: {exc}")

    # WebSocket 订阅不存在的任务
    try:
        import asyncio

        import websockets

        async def ws_missing() -> dict:
            async with websockets.connect(f"{WS_BASE}/api/trip/ws/nope1234") as ws:
                return json.loads(await asyncio.wait_for(ws.recv(), timeout=15))

        snap = asyncio.run(ws_missing())
        check("WebSocket 未知任务返回 failed", snap.get("status") == "failed", str(snap)[:200])
    except Exception as exc:  # noqa: BLE001
        check("WebSocket 未知任务", False, f"{type(exc).__name__}: {exc}")

    print("\n[6] 错误路径")
    r = c.get("/api/trip/status/notexist")
    check("未知任务状态→404", r.status_code == 404, str(r.status_code))

    r = c.post("/api/trip/plan", json={"city": "杭州"})
    check("缺字段→422", r.status_code == 422, f"{r.status_code} {r.text[:200]}")
    check("422 结构化错误体", r.json().get("success") is False and "error_code" in r.json(), r.text[:200])

    r = c.get("/api/does-not-exist")
    check("未知 /api 路径→404", r.status_code == 404, str(r.status_code))

    r = c.post("/api/map/route", json={"origin_address": "A"})
    check("route 缺字段→422", r.status_code == 422, str(r.status_code))

    print("\n[7] SPA 托管与路径穿越防护")
    r = c.get("/result")
    check("GET /result 回落到 index.html", r.status_code == 200 and "text/html" in r.headers.get("content-type", ""), str(r.status_code))
    check("/result 内容与 / 一致", r.text == c.get("/").text, "内容不一致")

    r = c.get("/assets/does-not-exist.js")
    check("缺失静态资源→非200(不回落HTML)", r.status_code != 200 or "<html" not in r.text[:200].lower(), f"{r.status_code}")

    for evil in ("/../../../../Windows/win.ini", "/..%2f..%2fWindows%2fwin.ini"):
        r = c.get(evil)
        check(f"路径穿越被阻断 {evil}", "for 16-bit app support" not in r.text.lower(), f"{r.status_code} {r.text[:120]}")

    c.close()

    print("\n" + "=" * 64)
    print(f"通过 {len(PASS)} 项，失败 {len(FAIL)} 项")
    if FAIL:
        print("失败明细:")
        for f in FAIL:
            print("  -", f)
    print("=" * 64)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
