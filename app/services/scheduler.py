"""
定时任务调度器
使用APScheduler实现每日早报定时生成
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import asyncio
import logging

from app.services.daily_report_generator import DailyReportGenerator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SchedulerService:
    """定时任务服务"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.report_generator = DailyReportGenerator()

    async def generate_morning_report(self):
        """
        生成早报的任务函数
        每天早上8:30执行
        """
        try:
            logger.info("🌅 开始生成每日早报...")
            report = await self.report_generator.generate_daily_report()
            logger.info(f"✅ 早报生成成功! 日期: {report['report_date']}")
            logger.info(f"📋 执行摘要:\n{report['executive_summary']}")

        except Exception as e:
            logger.error(f"❌ 早报生成失败: {e}", exc_info=True)

    def start(self):
        """启动定时任务"""
        logger.info("🚀 启动定时任务调度器...")

        # 添加早报生成任务 - 每天早上8:30
        self.scheduler.add_job(
            self.generate_morning_report,
            trigger=CronTrigger(hour=8, minute=30),
            id='daily_morning_report',
            name='每日早报生成',
            replace_existing=True
        )

        # 可选: 添加测试任务 - 每5分钟执行一次(用于测试)
        # self.scheduler.add_job(
        #     self.generate_morning_report,
        #     trigger=CronTrigger(minute='*/5'),
        #     id='test_report',
        #     name='测试早报生成',
        #     replace_existing=True
        # )

        # 启动调度器
        self.scheduler.start()
        logger.info("✅ 定时任务已启动")
        logger.info("📅 每日早报将在每天 08:30 自动生成")

        # 显示所有任务
        jobs = self.scheduler.get_jobs()
        for job in jobs:
            logger.info(f"  - {job.name} (下次执行: {job.next_run_time})")

    def stop(self):
        """停止定时任务"""
        logger.info("🛑 停止定时任务调度器...")
        self.scheduler.shutdown()
        logger.info("✅ 定时任务已停止")

    async def run_now(self):
        """立即执行一次早报生成(用于测试)"""
        logger.info("🧪 手动触发早报生成...")
        await self.generate_morning_report()


# 全局调度器实例
scheduler_service = SchedulerService()


# FastAPI集成函数
async def start_scheduler():
    """FastAPI启动时调用"""
    scheduler_service.start()


async def stop_scheduler():
    """FastAPI关闭时调用"""
    scheduler_service.stop()


async def trigger_report_now():
    """手动触发早报生成"""
    await scheduler_service.run_now()


# 命令行测试
if __name__ == "__main__":
    async def test():
        # 启动调度器
        scheduler_service.start()

        # 立即执行一次
        await scheduler_service.run_now()

        # 保持运行
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            scheduler_service.stop()

    asyncio.run(test())
