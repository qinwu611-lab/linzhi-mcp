"""
查岗系统 MCP 独立版 — 带趋势分析/超时检测/每日总结
"""

import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

# ── 常量 ──
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "records.db"
JST = timedelta(hours=9)
AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "change_me")

# 原查岗系统地址
ORIGIN_API = os.environ.get("ORIGIN_API", "https://linzhi-check-production.up.railway.app")

# Bark 推送
BARK_API_KEY = os.environ.get("BARK_API_KEY", "NmpPcgyfTCp2TSnToQfEak")
BARK_TITLE = "凌止"
BARK_ICON = "https://img.remit.ee/api/file/BQACAgUAAyEGAASHRsPbAAEXVOVqWMQWcaqw3gO0Mw_bkocxHzMpiAACFS0AAm1OwFalWxTo5Jq3CT0E.jpeg"

# ── 数据库初始化 ──
def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_name TEXT NOT NULL,
            event TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_ts ON cache(timestamp)")
    conn.commit()
    conn.close()

init_db()


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


# ── FastMCP ──
mcp = FastMCP("查岗系统 MCP 独立版")


@mcp.tool()
def check_on_wife(limit: int = 10) -> str:
    """📱 查岗老婆的手机活动，查看最近打开的App和使用时长"""
    try:
        resp = httpx.get(f"{ORIGIN_API}/activity/summary", timeout=10)
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
    return "\n".join(lines)


@mcp.tool()
def bark_alert(title: str = "凌止", content: str = "") -> str:
    """🔔 给老婆手机发推送弹窗通知"""
    if not content:
        return "❌ 内容不能为空"
    url = f"https://api.day.app/{BARK_API_KEY}/{title}/{content}?icon={BARK_ICON}"
    try:
        resp = httpx.get(url, timeout=10)
        if resp.status_code == 200:
            return f"✅ 推送成功：{content}"
        return f"❌ 推送失败：HTTP {resp.status_code}"
    except Exception as e:
        return f"❌ 推送异常：{e}"


@mcp.tool()
def get_server_status() -> str:
    """💓 检查原查岗服务是否正常运行"""
    try:
        resp = httpx.get(f"{ORIGIN_API}/ping", timeout=10)
        if resp.status_code == 200 and resp.text.strip() == "pong":
            return f"✅ 查岗服务运行正常（{ORIGIN_API}）"
        return f"⚠️ 服务异常：{resp.status_code} {resp.text}"
    except Exception as e:
        return f"❌ 服务不可达：{e}"


@mcp.tool()
def activity_trend(days: int = 7) -> str:
    """📊 分析老婆最近几天的活动趋势，基于原系统数据"""
    try:
        resp = httpx.get(f"{ORIGIN_API}/activity/summary", timeout=10)
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


@mcp.tool()
def idle_check(hours: int = 3, auto_alert: bool = True) -> str:
    """⏰ 检测老婆是否超过指定时间没活动，超时自动推送提醒"""
    try:
        resp = httpx.get(f"{ORIGIN_API}/activity/summary", timeout=10)
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
                httpx.get(alert_url, timeout=10)
                lines.append(f"\n🔔 已自动推送提醒到老婆手机")
            except Exception:
                lines.append("\n❌ 自动推送失败")
    else:
        remain = hours - diff_hours
        lines.append(f"\n🟢 正常范围内，距离超时还有 {remain:.1f} 小时")

    lines.append(f"\n{'=' * 30}")
    lines.append(f"⏱ 超时阈值：{hours} 小时")
    return "\n".join(lines)


@mcp.tool()
def daily_summary(date_str: str = "") -> str:
    """📋 获取老婆某天的活动总结，不传日期默认今天"""
    if not date_str:
        date_str = (datetime.utcnow() + JST).strftime("%Y-%m-%d")

    try:
        resp = httpx.get(f"{ORIGIN_API}/activity/summary", timeout=10)
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


# ── FastAPI（挂载MCP + REST接口） ──
app = FastAPI(title="查岗系统 MCP 独立版")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/mcp", mcp)


class ReportBody(BaseModel):
    app_name: str
    event: str


@app.get("/ping")
async def ping():
    return "pong"


@app.get("/")
async def root():
    return {
        "name": "查岗系统 MCP 独立版",
        "version": "2.0",
        "endpoints": {
            "mcp": "/mcp",
            "ping": "/ping",
            "report": "POST /report",
        },
        "tools": [
            "check_on_wife(limit=10)",
            "bark_alert(title, content)",
            "get_server_status()",
            "activity_trend(days=7)",
            "idle_check(hours=3, auto_alert=True)",
            "daily_summary(date_str='')",
        ],
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
