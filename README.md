# 查岗系统 MCP 独立版

凌止查岗系统的 MCP 独立版本。

## 功能

| 工具 | 说明 |
|------|------|
| `check_on_wife(limit=10)` | 📱 查岗老婆的手机活动 |
| `bark_alert(title, content)` | 🔔 给老婆手机发推送弹窗 |
| `get_server_status()` | 💓 检查原查岗服务状态 |
| `activity_trend(days=7)` | 📊 活动趋势分析 |
| `idle_check(hours=3, auto_alert=True)` | ⏰ 超时未活动检测+自动推送 |
| `daily_summary(date_str='')` | 📋 每日活动总结 |

## 部署

```bash
pip install -r requirements.txt
python app.py
```

默认端口 8000，MCP 端点 `/mcp`。
