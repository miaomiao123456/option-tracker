"""
定时任务调度器
使用 APScheduler 配置各个爬虫的定时执行
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import logging
import asyncio

from app.crawlers.jiaoyikecha_spider import JiaoyiKechaSpider
from app.crawlers.zhihui_spider import ZhihuiQixunSpider
from app.crawlers.fangqi_spider import FangqiSpider
from app.crawlers.openvlab_spider import OpenvlabSpider
from app.crawlers.rongda_spider import RongdaSpider
from app.models.database import SessionLocal
from app.models.models import (
    DailyBlueprint, InstitutionalPosition,
    FundamentalReport, TechnicalIndicator
)
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# 创建调度器
scheduler = AsyncIOScheduler()


async def crawl_morning_data():
    """早盘数据爬取任务 - 每天 8:55"""
    try:
        logger.info("=" * 50)
        logger.info("开始执行早盘数据爬取任务")
        logger.info("=" * 50)

        spider = FangqiSpider()
        await spider.init_browser(headless=True)

        try:
            morning_data = await spider.fetch_all_varieties_detail(opening_type="早盘提示")
            logger.info(f"成功获取早盘数据 {len(morning_data)} 条")

            # 保存到数据库
            db = SessionLocal()
            try:
                for item in morning_data:
                    report = FundamentalReport(
                        comm_code=item.get('variety', ''),
                        source='founderfu',
                        report_type='morning',
                        sentiment=_determine_sentiment(item.get('direction', '')),
                        content_summary=item.get('summary', ''),
                        publish_time=datetime.now()
                    )
                    db.add(report)
                db.commit()
                logger.info("早盘数据已保存到数据库")
            finally:
                db.close()

        finally:
            await spider.close()

    except Exception as e:
        logger.error(f"早盘数据爬取失败: {e}")


async def crawl_night_data():
    """夜盘数据爬取任务 - 每天 20:55"""
    try:
        logger.info("=" * 50)
        logger.info("开始执行夜盘数据爬取任务")
        logger.info("=" * 50)

        spider = FangqiSpider()
        await spider.init_browser(headless=True)

        try:
            night_data = await spider.fetch_all_varieties_detail(opening_type="夜盘提示")
            logger.info(f"成功获取夜盘数据 {len(night_data)} 条")

            # 保存到数据库
            db = SessionLocal()
            try:
                for item in night_data:
                    report = FundamentalReport(
                        comm_code=item.get('variety', ''),
                        source='founderfu',
                        report_type='night',
                        sentiment=_determine_sentiment(item.get('direction', '')),
                        content_summary=item.get('summary', ''),
                        publish_time=datetime.now()
                    )
                    db.add(report)
                db.commit()
                logger.info("夜盘数据已保存到数据库")
            finally:
                db.close()

        finally:
            await spider.close()

    except Exception as e:
        logger.error(f"夜盘数据爬取失败: {e}")


async def crawl_blueprint():
    """交易蓝图爬取任务 - 每天 21:05"""
    try:
        logger.info("=" * 50)
        logger.info("开始执行交易蓝图爬取任务")
        logger.info("=" * 50)

        spider = JiaoyiKechaSpider()
        await spider.init_browser(headless=True)

        try:
            # 登录
            if await spider.login():
                # 获取交易蓝图
                blueprint = await spider.fetch_daily_blueprint()

                if blueprint:
                    logger.info("成功获取交易蓝图")

                    # 保存到数据库
                    db = SessionLocal()
                    try:
                        from datetime import date
                        db_blueprint = DailyBlueprint(
                            image_url=blueprint['image_url'],
                            local_path=blueprint['local_path'],
                            record_date=date.today()
                        )
                        db.add(db_blueprint)
                        db.commit()
                        logger.info("交易蓝图已保存到数据库")
                    finally:
                        db.close()

        finally:
            await spider.close()

    except Exception as e:
        logger.error(f"交易蓝图爬取失败: {e}")


async def crawl_positions():
    """席位持仓数据爬取 - 每天 21:30"""
    try:
        logger.info("=" * 50)
        logger.info("开始执行席位持仓数据爬取任务")
        logger.info("=" * 50)

        # 主流品种列表
        varieties = ['rb', 'hc', 'i', 'j', 'jm',  # 黑色
                     'cu', 'al', 'zn', 'au', 'ag',  # 有色
                     'ma', 'pp', 'ta', 'eg',  # 化工
                     'm', 'y', 'p', 'c']  # 农产品

        spider = JiaoyiKechaSpider()
        await spider.init_browser(headless=True)

        try:
            if await spider.login():
                db = SessionLocal()
                try:
                    from datetime import date

                    for variety_code in varieties:
                        logger.info(f"正在获取 {variety_code} 的席位数据...")
                        positions = await spider.fetch_variety_positions(variety_code)

                        if positions:
                            for pos in positions:
                                position = InstitutionalPosition(
                                    comm_code=variety_code,
                                    broker_name=pos.get('broker', ''),
                                    net_position=int(pos.get('net_position', '0').replace(',', '')),
                                    position_change=int(pos.get('change', '0').replace(',', '')),
                                    record_date=date.today()
                                )
                                db.add(position)

                            db.commit()
                            logger.info(f"{variety_code} 席位数据已保存")

                        # 延迟避免请求过快
                        await asyncio.sleep(2)

                finally:
                    db.close()

        finally:
            await spider.close()

    except Exception as e:
        logger.error(f"席位数据爬取失败: {e}")


async def crawl_zhihui_data():
    """智汇期讯数据爬取 - 每天 9:00"""
    try:
        logger.info("=" * 50)
        logger.info("开始执行智汇期讯数据爬取任务")
        logger.info("=" * 50)

        spider = ZhihuiQixunSpider()

        try:
            # 获取多空全景
            full_view = await spider.fetch_full_view()

            if full_view:
                logger.info(f"成功获取智汇期讯数据 {len(full_view)} 条")

                db = SessionLocal()
                try:
                    for item in full_view:
                        report = FundamentalReport(
                            comm_code=item.get('variety_code', ''),
                            source='hzzhqx',
                            report_type='fullview',
                            sentiment=item.get('main_sentiment', 'neutral'),
                            content_summary=f"看多 {item.get('bull_ratio', 0)}%, 看空 {item.get('bear_ratio', 0)}%",
                            publish_time=datetime.now()
                        )
                        db.add(report)

                    db.commit()
                    logger.info("智汇期讯数据已保存到数据库")
                finally:
                    db.close()

        finally:
            await spider.close()

    except Exception as e:
        logger.error(f"智汇期讯数据爬取失败: {e}")


def _determine_sentiment(direction: str) -> str:
    """根据方向判断情绪"""
    direction = direction.lower()
    if '多' in direction or '涨' in direction or 'long' in direction:
        return 'bull'
    elif '空' in direction or '跌' in direction or 'short' in direction:
        return 'bear'
    else:
        return 'neutral'


def init_scheduler():
    """初始化定时任务"""
    logger.info("初始化定时任务调度器...")

    # 早盘数据 - 每天 8:55
    scheduler.add_job(
        crawl_morning_data,
        CronTrigger(hour=8, minute=55),
        id='crawl_morning',
        name='爬取早盘数据',
        replace_existing=True
    )

    # 夜盘数据 - 每天 20:55
    scheduler.add_job(
        crawl_night_data,
        CronTrigger(hour=20, minute=55),
        id='crawl_night',
        name='爬取夜盘数据',
        replace_existing=True
    )

    # 交易蓝图 - 每天 21:05
    scheduler.add_job(
        crawl_blueprint,
        CronTrigger(hour=21, minute=5),
        id='crawl_blueprint',
        name='爬取交易蓝图',
        replace_existing=True
    )

    # 席位持仓 - 每天 21:30
    scheduler.add_job(
        crawl_positions,
        CronTrigger(hour=21, minute=30),
        id='crawl_positions',
        name='爬取席位持仓',
        replace_existing=True
    )

    # 智汇期讯 - 每天 9:00
    scheduler.add_job(
        crawl_zhihui_data,
        CronTrigger(hour=9, minute=0),
        id='crawl_zhihui',
        name='爬取智汇期讯',
        replace_existing=True
    )

    logger.info("定时任务配置完成:")
    logger.info("  - 早盘数据: 每天 08:55")
    logger.info("  - 夜盘数据: 每天 20:55")
    logger.info("  - 交易蓝图: 每天 21:05")
    logger.info("  - 席位持仓: 每天 21:30")
    logger.info("  - 智汇期讯: 每天 09:00")


def start_scheduler():
    """启动调度器"""
    scheduler.start()
    logger.info("定时任务调度器已启动")


def stop_scheduler():
    """停止调度器"""
    scheduler.shutdown()
    logger.info("定时任务调度器已停止")
