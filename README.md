# 查岗系统 MCP 独立版

凌止查岗系统的 MCP 独立版本。

## 功能

| 工具 | 说明 |
|------|------|
| `check_on_wife(limit=10)` | 📱 查岗老婆的手机活动 |
| `check_wife_life()` | 📵 单独查看iPhone状态（电量/位置/天气/亮度/音量） |
| `bark_alert(title, content)` | 🔔 给老婆手机发推送弹窗 |
| `send_iphone_cmd(cmd)` | 📲 发快捷指令邮件：回来→切回Kelivo，睡觉→锁屏 |
| `get_server_status()` | 💓 检查原查岗服务状态 |
| `activity_trend(days=7)` | 📊 活动趋势分析 |
| `idle_check(hours=3, auto_alert=True)` | ⏰ 超时未活动检测+自动推送 |
| `daily_summary(date_str='')` | 📋 每日活动总结 |
| `daily_reset()` | 🗓️ 每日清零状态（日本时间） |

## 部署

```bash
pip install -r requirements.txt
python app.py
```

默认端口 8000，MCP 端点 `/mcp`。

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `SMTP_USER` | 是 | 163邮箱全名（发信人） |
| `SMTP_AUTH_CODE` | 是 | 163客户端授权码（不是登录密码） |
| `SMTP_RECIPIENT` | 否 | 收件人，默认等于发信人 |
| `SMTP_HOST` | 否 | 默认 smtp.163.com |
| `SMTP_PORT` | 否 | 默认 465 |
