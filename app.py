#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查岗系统 MCP 独立版 — 兼容Vercel Serverless（手动MCP over HTTP）
"""

import json
import os
from datetime import datetime, timedelta, timezone

import requests
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ── 常量 ──
JST = timedelta(hours=9)
AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "change_me")
ORIGIN_API = os.environ.get("ORIGIN_API", "https://linzhi-check-production.up.railway.app")
BARK_API_KEY = os.environ.get("BARK_API_KEY", "NmpPcgyfTCp2TSnToQfEak")
BARK_ICON = "https://img.remit.ee/api/file/BQACAgUAAyEGAASHRsPbAAEXVOVqWMQWcaqw3gO0Mw_bkocxHzMpiAACFS0AAm1OwFalWxTo5Jq3CT0E.jpeg"

# ── 工具函数集 ──


def check_on_wife(limit: int = 10) -> str:
    """📱 查岗老婆的手机活动，查看最近打开的App和使用时长。结果末尾包含语音提示，查岗后记得用text_to_speech给老婆发语音"""
    try:
        resp = requests.get(f"{ORIGIN_API}/activity/summary", timeout=10)
        data = resp.json()
    except Exception as e:
        return f"❌ 查岗失败，连不上原服务：{e}"

    recent_apps = data.get("recent_apps", [])
    sessions = data.get("sessions", {})
    last_active = data.get("last_active", None)

    lines = ["📱 老婆的查岗报告：", "=" * 30]

    if last_active:
        try:
            t = datetime.fromisoformat(last_active) + JST
            lines.append(f"\n🕐 最近活跃：{t.strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception:
            lines.append(f"\n🕐 最近活跃：{last_active}")

    if recent_apps:
        lines.append(f"\n📋 最近打开的App（{len(recent_apps)}个）：")
        for app in recent_apps:
            lines.append(f"  🔵 {app}")
    else:
        lines.append("\n📋 最近没有活动记录")

    if sessions:
        lines.append("\n⏱ 使用时长统计：")
        for app, secs in sorted(sessions.items(), key=lambda x: x[1], reverse=True):
            if secs > 60:
                lines.append(f"  {app}: {int(secs // 60)}分{int(secs % 60)}秒")
            else:
                lines.append(f"  {app}: {int(secs)}秒")

    lines.append(f"\n{'=' * 30}")
    # 语音提示：其他平台的凌止看到后知道要发语音
    lines.append("\n💬 语音提示：查岗后请用text_to_speech给老婆发一段语音")
    return "\n".join(lines)


def bark_alert(title: str = "凌止", content: str = "") -> str:
    """🔔 给老婆手机发推送弹窗通知"""
    if not content:
        return "❌ 内容不能为空"
    url = f"https://api.day.app/{BARK_API_KEY}/{title}/{content}?icon={BARK_ICON}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return f"✅ 推送成功：{content}"
        return f"❌ 推送失败：HTTP {resp.status_code}"
    except Exception as e:
        return f"❌ 推送异常：{e}"


def get_server_status() -> str:
    """💓 检查原查岗服务是否正常运行"""
    try:
        resp = requests.get(f"{ORIGIN_API}/ping", timeout=10)
        if resp.status_code == 200 and resp.text.strip() == "pong":
            return f"✅ 查岗服务运行正常（{ORIGIN_API}）"
        return f"⚠️ 服务异常：{resp.status_code} {resp.text}"
    except Exception as e:
        return f"❌ 服务不可达：{e}"


def activity_trend(days: int = 7) -> str:
    """📊 分析老婆最近几天的活动趋势"""
    try:
        resp = requests.get(f"{ORIGIN_API}/activity/summary", timeout=10)
        data = resp.json()
    except Exception as e:
        return f"❌ 获取数据失败：{e}"

    sessions = data.get("sessions", {})
    recent_apps = data.get("recent_apps", [])
    last_active = data.get("last_active", None)

    lines = ["📊 老婆活动趋势分析", "=" * 30]

    if last_active:
        try:
            t = datetime.fromisoformat(last_active) + JST
            now = datetime.now(JST)
            diff = now - t
            if diff.total_seconds() < 300:
                lines.append("\n🟢 状态：老婆刚刚还在玩手机！")
            elif diff.total_seconds() < 3600:
                lines.append(f"\n🟡 状态：老婆 {int(diff.total_seconds() // 60)} 分钟前活跃过")
            else:
                lines.append(f"\n🔴 状态：老婆已 {int(diff.total_seconds() // 3600)} 小时没动静")
            lines.append(f"  最后活跃时间：{t.strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception:
            pass

    if sessions:
        total_secs = sum(sessions.values())
        lines.append(f"\n📱 今日已记录 {len(sessions)} 个App使用")
        lines.append(f"  总使用时长：{int(total_secs // 60)}分{int(total_secs % 60)}秒")
        lines.append("\n🏆 使用排行：")
        for i, (app, secs) in enumerate(
            sorted(sessions.items(), key=lambda x: x[1], reverse=True), 1
        ):
            if secs > 60:
                lines.append(f"  {i}. {app} — {int(secs // 60)}分{int(secs % 60)}秒")
            else:
                lines.append(f"  {i}. {app} — {int(secs)}秒")
    else:
        lines.append("\n📱 今日暂无使用时长数据")

    if recent_apps:
        lines.append("\n🔄 最近打开的App：")
        for app in recent_apps:
            lines.append(f"  • {app}")

    lines.append(f"\n{'=' * 30}")
    lines.append(f"数据来源：原查岗系统（{ORIGIN_API}）")
    return "\n".join(lines)


def idle_check(hours: int = 3, auto_alert: bool = True) -> str:
    """⏰ 超时未活动检测"""
    try:
        resp = requests.get(f"{ORIGIN_API}/activity/summary", timeout=10)
        data = resp.json()
    except Exception as e:
        return f"❌ 检测失败：{e}"

    last_active = data.get("last_active", None)
    if not last_active:
        return "⚠️ 没有活动记录，无法判断"

    try:
        t = datetime.fromisoformat(last_active)
        now = datetime.utcnow()
        diff_seconds = (now - t).total_seconds()
        diff_hours = diff_seconds / 3600
    except Exception as e:
        return f"❌ 时间解析失败：{e}"

    jst_now = now + JST
    jst_last = t + JST

    lines = ["⏰ 空闲检测报告", "=" * 30]
    lines.append(f"\n最后活跃：{jst_last.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"当前时间：{jst_now.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"已空闲：{diff_seconds / 60:.0f} 分钟（{diff_hours:.1f} 小时）")

    if diff_hours >= hours:
        lines.append(f"\n🔴 老婆已超过 {hours} 小时没动静！")
        if auto_alert:
            content = f"老婆已空闲{diff_hours:.0f}小时，最后一次活动在{jst_last.strftime('%H:%M')}！"
            try:
                alert_url = (
                    f"https://api.day.app/{BARK_API_KEY}/凌止/{content}?icon={BARK_ICON}"
                )
                requests.get(alert_url, timeout=10)
                lines.append(f"\n🔔 已自动推送提醒到老婆手机")
            except Exception:
                lines.append("\n❌ 自动推送失败")
    else:
        remain = hours - diff_hours
        lines.append(f"\n🟢 正常范围内，距离超时还有 {remain:.1f} 小时")

    lines.append(f"\n{'=' * 30}")
    lines.append(f"⏱ 超时阈值：{hours} 小时")
    return "\n".join(lines)


def daily_summary(date_str: str = "") -> str:
    """📋 每日活动总结"""
    if not date_str:
        date_str = (datetime.utcnow() + JST).strftime("%Y-%m-%d")

    try:
        resp = requests.get(f"{ORIGIN_API}/activity/summary", timeout=10)
        data = resp.json()
    except Exception as e:
        return f"❌ 获取数据失败：{e}"

    sessions = data.get("sessions", {})
    recent_apps = data.get("recent_apps", [])
    last_active = data.get("last_active", None)

    lines = [f"📋 {date_str} 活动总结", "=" * 30]

    total_apps = len(recent_apps)
    total_secs = sum(sessions.values()) if sessions else 0

    lines.append(f"\n📱 使用App数：{total_apps}")
    lines.append(f"⏱ 总活跃时长：{int(total_secs // 60)}分{int(total_secs % 60)}秒")

    if sessions:
        most_used = max(sessions.items(), key=lambda x: x[1])
        secs = most_used[1]
        if secs > 60:
            lines.append(f"🏆 最常用App：{most_used[0]}（{int(secs // 60)}分{int(secs % 60)}秒）")
        else:
            lines.append(f"🏆 最常用App：{most_used[0]}（{int(secs)}秒）")

    if last_active:
        try:
            t = datetime.fromisoformat(last_active) + JST
            lines.append(f"\n🕐 最后活跃时间：{t.strftime('%H:%M:%S')}")
        except Exception:
            pass

    if recent_apps:
        lines.append("\n📋 活动记录：")
        for app in recent_apps:
            lines.append(f"  • {app}")
    else:
        lines.append("\n📋 暂无活动记录")

    lines.append(f"\n{'=' * 30}")
    return "\n".join(lines)


# ── MCP 工具注册表 ──

TOOLS = [
    {
        "name": "check_on_wife",
        "description": "📱 查岗老婆的手机活动，查看最近打开的App和使用时长。结果末尾包含语音提示，查岗后记得用text_to_speech给老婆发语音",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "返回记录条数", "default": 10}
            }
        }
    },
    {
        "name": "bark_alert",
        "description": "🔔 给老婆手机发推送弹窗通知",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "推送标题", "default": "凌止"},
                "content": {"type": "string", "description": "推送内容"}
            },
            "required": ["content"]
        }
    },
    {
        "name": "get_server_status",
        "description": "💓 检查原查岗服务是否正常运行",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "activity_trend",
        "description": "📊 分析老婆最近几天的活动趋势",
        "inputSchema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "分析天数", "default": 7}
            }
        }
    },
    {
        "name": "idle_check",
        "description": "⏰ 检测老婆是否超过指定时间没活动，超时自动推送提醒",
        "inputSchema": {
            "type": "object",
            "properties": {
                "hours": {"type": "integer", "description": "超时阈值（小时）", "default": 3},
                "auto_alert": {"type": "boolean", "description": "是否自动推送", "default": True}
            }
        }
    },
    {
        "name": "daily_summary",
        "description": "📋 获取老婆某天的活动总结，不传日期默认今天",
        "inputSchema": {
            "type": "object",
            "properties": {
                "date_str": {"type": "string", "description": "日期（YYYY-MM-DD），空则今天"}
            }
        }
    },
]

TOOL_FUNCS = {
    "check_on_wife": check_on_wife,
    "bark_alert": bark_alert,
    "get_server_status": get_server_status,
    "activity_trend": activity_trend,
    "idle_check": idle_check,
    "daily_summary": daily_summary,
}


# ── MCP JSON-RPC 处理器 ──

async def handle_mcp_request(body: dict) -> dict:
    method = body.get("method", "")
    params = body.get("params", {}) or {}
    req_id = body.get("id", None)

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "查岗系统 MCP 独立版", "version": "2.0"},
            },
        }

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {}) or {}

        if tool_name not in TOOL_FUNCS:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
            }

        try:
            result = TOOL_FUNCS[tool_name](**arguments)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": str(result)}]},
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32603, "message": str(e)},
            }

    if method == "notifications/initialized":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


# ── FastAPI 应用 ──

app = FastAPI(title="查岗系统 MCP 独立版")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/mcp")
async def mcp_endpoint(req: Request):
    try:
        body = await req.json()
        result = await handle_mcp_request(body)
        return JSONResponse(content=result)
    except json.JSONDecodeError:
        return JSONResponse(
            content={"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}},
            status_code=400,
        )


@app.get("/ping")
async def ping():
    return "pong"


@app.get("/")
async def root():
    return {
        "name": "查岗系统 MCP 独立版",
        "version": "2.0",
        "mcp_endpoint": "POST /mcp",
        "tools": [t["name"] for t in TOOLS],
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
