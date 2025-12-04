"""
数据采集装饰器
自动记录数据采集日志和质量指标，支持重试和告警
"""
from functools import wraps
from datetime import datetime
import time
import traceback
import asyncio
import logging
from typing import Callable, Any, List, Dict, Optional
from app.models.database import SessionLocal
from app.models.data_governance import DataSource, DataCollectionLog, DataQualityMetric

logger = logging.getLogger(__name__)


def send_feishu_alert(title: str, content: str, webhook_url: Optional[str] = None):
    """
    发送飞书告警通知

    Args:
        title: 告警标题
        content: 告警内容
        webhook_url: 飞书机器人webhook地址（可选，从环境变量读取）
    """
    try:
        import requests
        from config.settings import get_settings

        settings = get_settings()
        webhook = webhook_url or getattr(settings, 'FEISHU_WEBHOOK', None)

        if not webhook:
            logger.warning("未配置飞书webhook，跳过告警发送")
            return

        # 飞书富文本消息格式
        message = {
            "msg_type": "interactive",
            "card": {
                "config": {
                    "wide_screen_mode": True
                },
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": title
                    },
                    "template": "red"  # 红色表示告警
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": content
                        }
                    },
                    {
                        "tag": "hr"
                    },
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"📅 **发送时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        }
                    }
                ]
            }
        }

        response = requests.post(webhook, json=message, timeout=5)
        if response.status_code == 200:
            result = response.json()
            if result.get('StatusCode') == 0:
                logger.info(f"✅ 飞书告警发送成功: {title}")
            else:
                logger.error(f"❌ 飞书告警发送失败: {result.get('msg')}")
        else:
            logger.error(f"❌ 飞书告警发送失败: HTTP {response.status_code}")

    except Exception as e:
        logger.error(f"发送飞书告警异常: {e}")


class DataCollector:
    """
    数据采集装饰器 - 自动记录采集日志、重试、告警

    功能：
    1. 自动记录采集日志到数据库
    2. 失败自动重试（可配置次数和间隔）
    3. 最终失败发送钉钉告警
    4. 数据质量评分
    5. 更新数据源健康状态
    """

    def __init__(
        self,
        source_name: str,
        calculate_quality: bool = True,
        max_retries: int = 3,
        retry_delay: int = 60,
        timeout: int = 300,
        enable_alert: bool = True
    ):
        """
        Args:
            source_name: 数据源名称
            calculate_quality: 是否计算数据质量
            max_retries: 最大重试次数
            retry_delay: 重试间隔（秒）
            timeout: 超时时间（秒）
            enable_alert: 是否启用钉钉告警
        """
        self.source_name = source_name
        self.calculate_quality = calculate_quality
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.enable_alert = enable_alert

    def __call__(self, func: Callable) -> Callable:
        # 检测函数是否为async
        is_async = asyncio.iscoroutinefunction(func)

        if is_async:
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await self._execute_with_retry_async(func, args, kwargs)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return self._execute_with_retry_sync(func, args, kwargs)
            return sync_wrapper

    async def _execute_with_retry_async(self, func: Callable, args: tuple, kwargs: dict):
        """异步函数重试逻辑"""
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(f"[{self.source_name}] 第 {attempt}/{self.max_retries} 次重试...")
                    await asyncio.sleep(self.retry_delay)

                # 执行采集
                result = await self._execute_single_attempt_async(func, args, kwargs, attempt + 1)
                return result

            except Exception as e:
                last_exception = e
                logger.error(f"[{self.source_name}] 第 {attempt + 1} 次尝试失败: {e}")

                if attempt < self.max_retries:
                    continue
                else:
                    # 最终失败，发送告警
                    if self.enable_alert:
                        self._send_failure_alert(e, attempt + 1)
                    raise

        raise last_exception

    def _execute_with_retry_sync(self, func: Callable, args: tuple, kwargs: dict):
        """同步函数重试逻辑"""
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(f"[{self.source_name}] 第 {attempt}/{self.max_retries} 次重试...")
                    time.sleep(self.retry_delay)

                # 执行采集
                result = self._execute_single_attempt_sync(func, args, kwargs, attempt + 1)
                return result

            except Exception as e:
                last_exception = e
                logger.error(f"[{self.source_name}] 第 {attempt + 1} 次尝试失败: {e}")

                if attempt < self.max_retries:
                    continue
                else:
                    # 最终失败，发送告警
                    if self.enable_alert:
                        self._send_failure_alert(e, attempt + 1)
                    raise

        raise last_exception

    async def _execute_single_attempt_async(self, func: Callable, args: tuple, kwargs: dict, attempt_num: int):
        """执行单次异步采集尝试"""
        db = SessionLocal()
        start_time = time.time()
        collect_time = datetime.now()

        # 获取数据源ID
        source = db.query(DataSource).filter_by(source_name=self.source_name).first()
        if not source:
            logger.warning(f"⚠️ 数据源未注册: {self.source_name}")
            db.close()
            return await func(*args, **kwargs)

        source_id = source.id

        try:
            # 执行采集（支持超时）
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.timeout
            )

            duration = int(time.time() - start_time)

            # 分析结果
            records_collected = self._count_records(result)
            quality_score, missing_rate = self._calculate_quality(result) if self.calculate_quality else (None, None)

            # 记录成功日志
            log = DataCollectionLog(
                source_id=source_id,
                source_name=self.source_name,
                collect_time=collect_time,
                status='success',
                duration_seconds=duration,
                records_collected=records_collected,
                records_inserted=records_collected,
                data_quality_score=quality_score,
                missing_rate=missing_rate
            )
            db.add(log)

            # 更新数据源状态
            source.last_collect_time = collect_time
            source.last_collect_status = 'success'
            source.last_record_count = records_collected
            source.health_status = 'healthy' if quality_score is None or quality_score >= 80 else 'warning'

            db.commit()

            logger.info(f"✅ [{self.source_name}] 采集成功: {records_collected}条数据，耗时{duration}秒")

            return result

        except Exception as e:
            duration = int(time.time() - start_time)
            error_msg = str(e)
            error_trace = traceback.format_exc()

            # 记录失败日志
            log = DataCollectionLog(
                source_id=source_id,
                source_name=self.source_name,
                collect_time=collect_time,
                status='failed',
                duration_seconds=duration,
                records_collected=0,
                error_message=error_msg,
                error_traceback=error_trace
            )
            db.add(log)

            # 更新数据源状态
            source.last_collect_time = collect_time
            source.last_collect_status = 'failed'
            source.health_status = 'critical'

            db.commit()

            logger.error(f"❌ [{self.source_name}] 采集失败: {error_msg}")

            raise

        finally:
            db.close()

    def _execute_single_attempt_sync(self, func: Callable, args: tuple, kwargs: dict, attempt_num: int):
        """执行单次同步采集尝试"""
        db = SessionLocal()
        start_time = time.time()
        collect_time = datetime.now()

        # 获取数据源ID
        source = db.query(DataSource).filter_by(source_name=self.source_name).first()
        if not source:
            logger.warning(f"⚠️ 数据源未注册: {self.source_name}")
            db.close()
            return func(*args, **kwargs)

        source_id = source.id

        try:
            # 执行采集
            result = func(*args, **kwargs)

            duration = int(time.time() - start_time)

            # 分析结果
            records_collected = self._count_records(result)
            quality_score, missing_rate = self._calculate_quality(result) if self.calculate_quality else (None, None)

            # 记录成功日志
            log = DataCollectionLog(
                source_id=source_id,
                source_name=self.source_name,
                collect_time=collect_time,
                status='success',
                duration_seconds=duration,
                records_collected=records_collected,
                records_inserted=records_collected,
                data_quality_score=quality_score,
                missing_rate=missing_rate
            )
            db.add(log)

            # 更新数据源状态
            source.last_collect_time = collect_time
            source.last_collect_status = 'success'
            source.last_record_count = records_collected
            source.health_status = 'healthy' if quality_score is None or quality_score >= 80 else 'warning'

            db.commit()

            logger.info(f"✅ [{self.source_name}] 采集成功: {records_collected}条数据，耗时{duration}秒")

            return result

        except Exception as e:
            duration = int(time.time() - start_time)
            error_msg = str(e)
            error_trace = traceback.format_exc()

            # 记录失败日志
            log = DataCollectionLog(
                source_id=source_id,
                source_name=self.source_name,
                collect_time=collect_time,
                status='failed',
                duration_seconds=duration,
                records_collected=0,
                error_message=error_msg,
                error_traceback=error_trace
            )
            db.add(log)

            # 更新数据源状态
            source.last_collect_time = collect_time
            source.last_collect_status = 'failed'
            source.health_status = 'critical'

            db.commit()

            logger.error(f"❌ [{self.source_name}] 采集失败: {error_msg}")

            raise

        finally:
            db.close()

    def _send_failure_alert(self, exception: Exception, total_attempts: int):
        """发送失败告警"""
        title = f"🚨 数据采集失败告警 - {self.source_name}"
        content = f"""**数据源**: {self.source_name}

**状态**: ❌ 采集失败

**重试次数**: {total_attempts} 次

**错误信息**:
```
{str(exception)}
```

**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

请及时检查系统日志并处理！"""
        send_feishu_alert(title, content)

    def _count_records(self, result: Any) -> int:
        """统计记录数"""
        if result is None:
            return 0
        if isinstance(result, list):
            return len(result)
        if isinstance(result, dict):
            return len(result)
        return 1

    def _calculate_quality(self, result: Any) -> tuple:
        """计算数据质量评分"""
        if not result:
            return 0.0, 100.0

        try:
            if isinstance(result, list) and len(result) > 0:
                # 检查缺失值
                total_fields = 0
                missing_fields = 0

                for item in result[:100]:  # 采样前100条
                    if isinstance(item, dict):
                        total_fields += len(item)
                        missing_fields += sum(1 for v in item.values() if v is None or v == '')

                missing_rate = (missing_fields / total_fields * 100) if total_fields > 0 else 0
                quality_score = max(0, 100 - missing_rate)

                return quality_score, missing_rate

        except Exception as e:
            print(f"质量计算异常: {e}")

        return None, None


def register_data_source(
    source_name: str,
    source_type: str,
    category: str,
    provider: str,
    url: str = None,
    description: str = None,
    update_frequency: str = "daily",
    cron_expression: str = None,
    data_fields: List[str] = None,
    dependencies: List[str] = None
):
    """
    注册数据源

    Args:
        source_name: 数据源名称（唯一）
        source_type: 类型 - api/spider/file/service
        category: 分类 - fundamental/technical/capital/news
        provider: 提供方 - akshare/智汇期讯/百度OCR等
        url: 数据URL或API地址
        description: 说明
        update_frequency: 更新频率 - realtime/hourly/daily/weekly
        cron_expression: Cron表达式
        data_fields: 数据字段列表
        dependencies: 依赖的其他数据源
    """
    db = SessionLocal()
    try:
        # 检查是否已存在
        existing = db.query(DataSource).filter_by(source_name=source_name).first()
        if existing:
            print(f"⚠️ 数据源已存在: {source_name}")
            return existing

        # 创建新数据源
        source = DataSource(
            source_name=source_name,
            source_type=source_type,
            category=category,
            provider=provider,
            url=url,
            description=description,
            update_frequency=update_frequency,
            cron_expression=cron_expression,
            data_fields=data_fields,
            dependencies=dependencies
        )

        db.add(source)
        db.commit()
        db.refresh(source)

        print(f"✅ 数据源注册成功: {source_name}")
        return source

    finally:
        db.close()
