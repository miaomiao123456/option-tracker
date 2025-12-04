# 飞书机器人告警配置指南

## 🤖 创建飞书机器人

### 1. 在飞书群中添加机器人

1. 打开飞书群聊
2. 点击右上角 **设置** → **群机器人** → **添加机器人**
3. 选择 **自定义机器人**
4. 设置机器人名称，如：`OptionAlpha数据告警`
5. 点击 **添加**

### 2. 获取 Webhook 地址

添加机器人后，系统会生成一个 Webhook 地址，格式如下：

```
https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

复制这个地址备用。

### 3. 配置到项目

在项目的 `.env` 文件中添加：

```bash
FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/你的webhook地址
```

## 📨 告警消息示例

当数据采集失败时，你会收到如下格式的飞书消息：

```
🚨 数据采集失败告警 - 智汇期讯-多空全景

数据源: 智汇期讯-多空全景

状态: ❌ 采集失败

重试次数: 4 次

错误信息:
```
Connection timeout
```

时间: 2025-11-30 16:00:00

---

请及时检查系统日志并处理！

📅 发送时间: 2025-11-30 16:00:00
```

## ✅ 测试告警

可以手动测试飞书告警功能：

```python
from app.services.data_collector import send_feishu_alert

send_feishu_alert(
    title="测试告警",
    content="这是一条测试消息，用于验证飞书机器人配置是否正确"
)
```

或者使用命令行：

```bash
python3 -c "
from app.services.data_collector import send_feishu_alert
send_feishu_alert('测试告警', '飞书机器人配置成功！')
"
```

## 🎨 消息格式说明

飞书告警使用**富文本卡片**格式，具有以下特点：

- ✅ 红色标题，醒目显示告警信息
- ✅ 支持 Markdown 格式
- ✅ 自动添加时间戳
- ✅ 支持代码块显示错误信息

## 🔧 高级配置

### 1. 自定义消息颜色

修改 `data_collector.py` 中的 `template` 字段：

```python
"header": {
    "title": {
        "tag": "plain_text",
        "content": title
    },
    "template": "red"  # 可选: red, blue, wathet, turquoise, green, yellow, orange, grey
}
```

### 2. 添加按钮

在 `elements` 中添加按钮组件：

```python
{
    "tag": "action",
    "actions": [
        {
            "tag": "button",
            "text": {
                "tag": "plain_text",
                "content": "查看日志"
            },
            "url": "http://localhost:8000/api/v1/data-governance/collection-logs",
            "type": "primary"
        }
    ]
}
```

### 3. @指定人员

添加 at 功能，在消息中 @ 特定成员：

```python
{
    "tag": "div",
    "text": {
        "tag": "lark_md",
        "content": "<at user_id=\"ou_xxxx\">@张三</at> 请及时处理"
    }
}
```

## 📋 常见问题

**Q: 告警消息没有发送成功？**

A: 检查以下几点：
1. 确认 `.env` 文件中的 `FEISHU_WEBHOOK` 配置正确
2. 检查网络连接是否正常
3. 查看系统日志中的错误信息

**Q: 如何查看告警日志？**

A: 查看系统日志：
```bash
tail -f logs/app.log | grep "飞书告警"
```

**Q: 如何禁用告警？**

A: 在使用 `@DataCollector` 装饰器时设置 `enable_alert=False`：

```python
@DataCollector(
    source_name="数据源名称",
    enable_alert=False  # 禁用告警
)
async def crawl_data():
    pass
```

## 🔗 参考文档

- [飞书机器人开发文档](https://open.feishu.cn/document/ukTMukTMukTM/ucTM5YjL3ETO24yNxkjN)
- [飞书卡片消息构建工具](https://open.feishu.cn/tool/cardbuilder)

---

**更新时间**: 2025-11-30
