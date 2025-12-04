# 爬虫系统增强方案

## 核心问题分析

### 当前问题
1. ❌ 爬虫失败无感知（运行了但没数据也不知道）
2. ❌ 失败不重试（网络抖动就失败）
3. ❌ 无监控告警（深夜失败无人知）
4. ❌ 数据未持久化（写入失败就丢失）
5. ❌ 无执行日志（不知道何时运行过）

### 解决方案架构

```
┌─────────────────────────────────────────────────┐
│         APScheduler (调度器)                     │
│  - 定时触发                                      │
│  - Cron表达式                                    │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│         爬虫任务包装器 (Wrapper)                 │
│  - 错误捕获                                      │
│  - 重试机制（最多3次）                           │
│  - 超时控制                                      │
│  - 数据验证                                      │
└────────────────┬────────────────────────────────┘
                 │
        ┌────────┴────────┐
        │                 │
        ▼                 ▼
┌──────────────┐    ┌──────────────┐
│  执行爬虫    │    │  记录日志    │
│  保存数据    │    │  发送告警    │
└──────────────┘    └──────────────┘
        │                 │
        └────────┬────────┘
                 ▼
        ┌────────────────┐
        │  PostgreSQL    │
        │  - 任务记录表  │
        │  - 数据表      │
        └────────────────┘
```

## Day 1-2: 任务记录系统

### 1. 创建任务记录表
```sql
-- 爬虫执行记录表
CREATE TABLE crawler_task_logs (
    id SERIAL PRIMARY KEY,
    task_name VARCHAR(100) NOT NULL,
    spider_name VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,  -- running, success, failed, retrying
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    duration_seconds INTEGER,
    records_count INTEGER DEFAULT 0,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_task_name_time ON crawler_task_logs(task_name, start_time DESC);
CREATE INDEX idx_status ON crawler_task_logs(status);
```

### 2. 爬虫包装器
```python
# app/crawlers/base_crawler.py
from typing import Callable, Any
from datetime import datetime
import traceback
import time
from functools import wraps
from app.models.database import SessionLocal
from app.models.models import CrawlerTaskLog

class CrawlerWrapper:
    """爬虫任务包装器 - 提供重试、日志、告警功能"""

    def __init__(
        self,
        task_name: str,
        spider_name: str,
        max_retries: int = 3,
        retry_delay: int = 60,  # 重试延迟（秒）
        timeout: int = 300,     # 超时时间（秒）
        notify_on_failure: bool = True
    ):
        self.task_name = task_name
        self.spider_name = spider_name
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.notify_on_failure = notify_on_failure

    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            task_log = self._create_task_log()
            retry_count = 0

            while retry_count <= self.max_retries:
                try:
                    # 执行爬虫
                    start_time = time.time()
                    result = func(*args, **kwargs)
                    duration = int(time.time() - start_time)

                    # 验证结果
                    if not self._validate_result(result):
                        raise ValueError("爬取数据为空或无效")

                    # 记录成功
                    self._update_task_log(
                        task_log,
                        status='success',
                        duration=duration,
                        records_count=len(result) if isinstance(result, list) else 1,
                        retry_count=retry_count
                    )

                    # 成功后发送通知（如果是重试成功）
                    if retry_count > 0:
                        self._send_notification(
                            f"✅ {self.task_name} 重试成功",
                            f"重试{retry_count}次后成功，获取{len(result) if isinstance(result, list) else 1}条数据"
                        )

                    return result

                except Exception as e:
                    retry_count += 1
                    error_msg = f"{str(e)}\n{traceback.format_exc()}"

                    if retry_count <= self.max_retries:
                        # 还有重试机会
                        self._update_task_log(
                            task_log,
                            status='retrying',
                            error_message=error_msg,
                            retry_count=retry_count
                        )

                        print(f"⚠️ {self.task_name} 失败，{self.retry_delay}秒后重试（{retry_count}/{self.max_retries}）")
                        time.sleep(self.retry_delay)
                    else:
                        # 最终失败
                        duration = int(time.time() - start_time)
                        self._update_task_log(
                            task_log,
                            status='failed',
                            duration=duration,
                            error_message=error_msg,
                            retry_count=retry_count - 1
                        )

                        # 发送失败告警
                        if self.notify_on_failure:
                            self._send_notification(
                                f"❌ {self.task_name} 最终失败",
                                f"重试{self.max_retries}次后仍失败\n错误: {str(e)}"
                            )

                        raise

        return wrapper

    def _create_task_log(self) -> int:
        """创建任务记录"""
        db = SessionLocal()
        try:
            log = CrawlerTaskLog(
                task_name=self.task_name,
                spider_name=self.spider_name,
                status='running',
                start_time=datetime.now()
            )
            db.add(log)
            db.commit()
            db.refresh(log)
            return log.id
        finally:
            db.close()

    def _update_task_log(
        self,
        task_id: int,
        status: str,
        duration: int = None,
        records_count: int = 0,
        error_message: str = None,
        retry_count: int = 0
    ):
        """更新任务记录"""
        db = SessionLocal()
        try:
            log = db.query(CrawlerTaskLog).filter_by(id=task_id).first()
            if log:
                log.status = status
                log.end_time = datetime.now()
                if duration:
                    log.duration_seconds = duration
                log.records_count = records_count
                log.error_message = error_message
                log.retry_count = retry_count
                db.commit()
        finally:
            db.close()

    def _validate_result(self, result: Any) -> bool:
        """验证结果有效性"""
        if result is None:
            return False
        if isinstance(result, (list, dict)) and len(result) == 0:
            return False
        return True

    def _send_notification(self, title: str, content: str):
        """发送钉钉/企业微信通知"""
        try:
            from app.services.notification import send_dingtalk_alert
            send_dingtalk_alert(title, content)
        except Exception as e:
            print(f"发送通知失败: {e}")
```

### 3. 使用示例
```python
# app/crawlers/zhihui_spider.py
from app.crawlers.base_crawler import CrawlerWrapper

@CrawlerWrapper(
    task_name="智汇期讯-多空全景",
    spider_name="zhihui_spider",
    max_retries=3,
    retry_delay=60,
    timeout=300
)
def crawl_zhihui_sentiment():
    """爬取智汇期讯数据"""
    # ... 原有爬虫逻辑 ...
    return data  # 返回数据列表

# 调度器中使用
scheduler.add_job(
    crawl_zhihui_sentiment,
    'cron',
    hour=20,
    minute=30,
    id='zhihui_sentiment'
)
```

## Day 3-4: 告警通知系统

### 1. 钉钉机器人通知
```python
# app/services/notification.py
import requests
import hmac
import hashlib
import base64
import time
from urllib.parse import quote_plus
from config.settings import get_settings

settings = get_settings()

def send_dingtalk_alert(title: str, content: str, at_all: bool = False):
    """
    发送钉钉机器人通知

    配置步骤：
    1. 钉钉群 -> 群设置 -> 智能群助手 -> 添加机器人 -> 自定义
    2. 安全设置：选择"加签"
    3. 复制Webhook和密钥到 .env
    """
    webhook = settings.DINGTALK_WEBHOOK
    secret = settings.DINGTALK_SECRET

    if not webhook:
        print("⚠️ 未配置钉钉Webhook")
        return

    # 计算签名
    timestamp = str(round(time.time() * 1000))
    secret_enc = secret.encode('utf-8')
    string_to_sign = f'{timestamp}\n{secret}'
    string_to_sign_enc = string_to_sign.encode('utf-8')
    hmac_code = hmac.new(
        secret_enc,
        string_to_sign_enc,
        digestmod=hashlib.sha256
    ).digest()
    sign = quote_plus(base64.b64encode(hmac_code))

    # 构建URL
    url = f"{webhook}&timestamp={timestamp}&sign={sign}"

    # 消息内容
    message = {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": f"## {title}\n\n{content}\n\n> 时间: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        }
    }

    if at_all:
        message["at"] = {"isAtAll": True}

    # 发送
    try:
        resp = requests.post(url, json=message, timeout=5)
        if resp.status_code == 200:
            print(f"✅ 钉钉通知发送成功: {title}")
        else:
            print(f"❌ 钉钉通知发送失败: {resp.text}")
    except Exception as e:
        print(f"❌ 钉钉通知异常: {e}")


def send_daily_report():
    """每日爬虫执行报告"""
    from app.models.database import SessionLocal
    from app.models.models import CrawlerTaskLog
    from sqlalchemy import func
    from datetime import datetime, timedelta

    db = SessionLocal()
    try:
        # 统计今日任务
        today = datetime.now().date()
        stats = db.query(
            CrawlerTaskLog.status,
            func.count(CrawlerTaskLog.id).label('count')
        ).filter(
            func.date(CrawlerTaskLog.start_time) == today
        ).group_by(CrawlerTaskLog.status).all()

        total = sum(s.count for s in stats)
        success = next((s.count for s in stats if s.status == 'success'), 0)
        failed = next((s.count for s in stats if s.status == 'failed'), 0)

        success_rate = (success / total * 100) if total > 0 else 0

        content = f"""
### 📊 今日爬虫执行情况

- **总任务数**: {total}
- **成功**: {success} ✅
- **失败**: {failed} ❌
- **成功率**: {success_rate:.1f}%

---

### 明细
"""
        for stat in stats:
            emoji = "✅" if stat.status == "success" else "❌" if stat.status == "failed" else "⚠️"
            content += f"- {emoji} {stat.status}: {stat.count}次\n"

        send_dingtalk_alert("每日爬虫报告", content)

    finally:
        db.close()
```

### 2. 环境变量配置
```python
# .env
DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=xxxxx
DINGTALK_SECRET=SECxxxxxxxxxxxxx
```

## Day 5: 监控面板

### 1. 爬虫健康检查API
```python
# app/routers/admin.py
from fastapi import APIRouter, Depends
from sqlalchemy import func, desc
from app.models.database import get_db
from app.models.models import CrawlerTaskLog
from datetime import datetime, timedelta

router = APIRouter(prefix="/admin", tags=["管理"])

@router.get("/crawler/health")
async def crawler_health_check(db = Depends(get_db)):
    """爬虫健康检查"""

    # 最近24小时任务统计
    since = datetime.now() - timedelta(hours=24)

    tasks = db.query(
        CrawlerTaskLog.task_name,
        CrawlerTaskLog.status,
        func.count(CrawlerTaskLog.id).label('count'),
        func.max(CrawlerTaskLog.start_time).label('last_run')
    ).filter(
        CrawlerTaskLog.start_time >= since
    ).group_by(
        CrawlerTaskLog.task_name,
        CrawlerTaskLog.status
    ).all()

    # 汇总
    task_summary = {}
    for task in tasks:
        if task.task_name not in task_summary:
            task_summary[task.task_name] = {
                'success': 0,
                'failed': 0,
                'last_run': None
            }

        task_summary[task.task_name][task.status] = task.count
        task_summary[task.task_name]['last_run'] = task.last_run

    # 计算健康状态
    for name, stats in task_summary.items():
        total = stats['success'] + stats['failed']
        stats['success_rate'] = (stats['success'] / total * 100) if total > 0 else 0

        # 健康状态判断
        if stats['success_rate'] >= 90:
            stats['health'] = 'healthy'
        elif stats['success_rate'] >= 70:
            stats['health'] = 'warning'
        else:
            stats['health'] = 'critical'

    return {
        "timestamp": datetime.now(),
        "tasks": task_summary
    }

@router.get("/crawler/logs")
async def get_crawler_logs(
    limit: int = 50,
    status: str = None,
    db = Depends(get_db)
):
    """获取爬虫执行日志"""
    query = db.query(CrawlerTaskLog).order_by(desc(CrawlerTaskLog.start_time))

    if status:
        query = query.filter(CrawlerTaskLog.status == status)

    logs = query.limit(limit).all()

    return {
        "logs": [
            {
                "id": log.id,
                "task_name": log.task_name,
                "status": log.status,
                "start_time": log.start_time,
                "duration": log.duration_seconds,
                "records": log.records_count,
                "error": log.error_message,
                "retry_count": log.retry_count
            }
            for log in logs
        ]
    }
```

### 2. 简单的监控前端
```html
<!-- admin/crawler_monitor.html -->
<!DOCTYPE html>
<html>
<head>
    <title>爬虫监控</title>
    <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
    <script src="https://unpkg.com/element-plus"></script>
    <link rel="stylesheet" href="https://unpkg.com/element-plus/dist/index.css" />
</head>
<body>
    <div id="app">
        <h1>爬虫健康监控</h1>

        <!-- 健康状态 -->
        <div v-for="(task, name) in health.tasks" :key="name">
            <h3>{{ name }}</h3>
            <p>状态: <span :class="task.health">{{ task.health }}</span></p>
            <p>成功率: {{ task.success_rate.toFixed(1) }}%</p>
            <p>最后运行: {{ task.last_run }}</p>
        </div>

        <!-- 执行日志 -->
        <h2>最近执行日志</h2>
        <table>
            <tr v-for="log in logs" :key="log.id">
                <td>{{ log.task_name }}</td>
                <td>{{ log.status }}</td>
                <td>{{ log.start_time }}</td>
                <td>{{ log.duration }}s</td>
                <td>{{ log.records }}条</td>
            </tr>
        </table>
    </div>

    <script>
        const { createApp } = Vue;
        createApp({
            data() {
                return {
                    health: { tasks: {} },
                    logs: []
                }
            },
            mounted() {
                this.fetchHealth();
                this.fetchLogs();
                // 每30秒刷新
                setInterval(() => {
                    this.fetchHealth();
                    this.fetchLogs();
                }, 30000);
            },
            methods: {
                async fetchHealth() {
                    const res = await fetch('/api/v1/admin/crawler/health');
                    this.health = await res.json();
                },
                async fetchLogs() {
                    const res = await fetch('/api/v1/admin/crawler/logs');
                    const data = await res.json();
                    this.logs = data.logs;
                }
            }
        }).use(ElementPlus).mount('#app');
    </script>
</body>
</html>
```

## 测试清单

### 功能测试
- [ ] 正常执行爬虫，记录日志
- [ ] 模拟网络失败，验证重试
- [ ] 验证失败后发送钉钉通知
- [ ] 验证成功率统计正确
- [ ] 验证监控面板显示正常

### 压力测试
- [ ] 6个爬虫同时运行，无冲突
- [ ] 连续失败3次后停止重试
- [ ] 数据库并发写入无锁

### 告警测试
- [ ] 失败告警能收到
- [ ] 每日报告定时发送
- [ ] @所有人功能正常
