"""
定时任务调度器
使用 APScheduler 配置各个爬虫的定时执行

爬虫时间配置：
- 智汇期讯: 每30分钟一次
- 方期看盘: 早盘8:50 / 夜盘20:50
- 交易可查: 19:00爬取，失败30分钟重试
- Openvlab: 交易时段分钟级监控 (9:00-11:30, 13:00-15:00)
- 融达数据分析家: 每天15:00
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, date
import logging
import asyncio

from app.crawlers.jiaoyikecha_spider import JiaoyiKechaSpider
from app.crawlers.zhihui_spider import ZhihuiQixunSpider
from app.crawlers.fangqi_spider import FangqiSpider
from app.crawlers.openvlab_spider import OpenvlabSpider
from app.crawlers.rongda_spider import RongdaSpider
from app.services.blueprint_parser import BlueprintParser
from app.services.data_collector import DataCollector
import json
from app.models.database import SessionLocal
from app.models.models import (
    DailyBlueprint, InstitutionalPosition,
    FundamentalReport, TechnicalIndicator, OptionFlow
)
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# 创建调度器
scheduler = AsyncIOScheduler()

# ========================================
# 智汇期讯爬虫 - 每30分钟一次
# ========================================
@DataCollector(
    source_name="智汇期讯-多空全景",
    max_retries=3,
    retry_delay=60,
    timeout=120,
    enable_alert=True
)
async def crawl_zhihui_data():
    """智汇期讯数据爬取 - 每30分钟一次"""
    logger.info("=" * 50)
    logger.info("[智汇期讯] 开始执行数据爬取任务")
    logger.info("=" * 50)

    from app.models.models import MarketFullView, ResearchReport
    spider = ZhihuiQixunSpider()

    try:
        # 1. 获取多空全景数据
        full_view = spider.fetch_full_view()

        if full_view:
            logger.info(f"[智汇期讯] 成功获取多空全景数据 {len(full_view)} 条")

            db = SessionLocal()
            try:
                today = date.today()
                # 保存多空全景数据到MarketFullView表
                for item in full_view:
                    # 检查是否已存在
                    existing = db.query(MarketFullView).filter(
                        MarketFullView.comm_code == item['variety_code'],
                        MarketFullView.record_date == today
                    ).first()

                    if existing:
                        # 更新现有记录
                        existing.excessive_num = item['excessive_num']
                        existing.excessive_ratio = item['excessive_ratio']
                        existing.neutral_num = item['neutral_num']
                        existing.neutral_ratio = item['neutral_ratio']
                        existing.empty_num = item['empty_num']
                        existing.empty_ratio = item['empty_ratio']
                        existing.total_num = item['sum']
                        existing.more_port = item['more_port']
                        existing.more_rate = item['more_rate']
                        existing.main_sentiment = item['main_sentiment']
                    else:
                        # 创建新记录
                        record = MarketFullView(
                            comm_code=item['variety_code'],
                            variety_name=item['variety_name'],
                            record_date=today,
                            excessive_num=item['excessive_num'],
                            excessive_ratio=item['excessive_ratio'],
                            neutral_num=item['neutral_num'],
                            neutral_ratio=item['neutral_ratio'],
                            empty_num=item['empty_num'],
                            empty_ratio=item['empty_ratio'],
                            total_num=item['sum'],
                            more_port=item['more_port'],
                            more_rate=item['more_rate'],
                            main_sentiment=item['main_sentiment']
                        )
                        db.add(record)

                db.commit()
                logger.info("[智汇期讯] 多空全景数据已保存到数据库")
            finally:
                db.close()

        # 2. 获取研报淘金数据
        logger.info("[智汇期讯] 开始获取研报淘金数据...")
        reports_data = spider.fetch_research_reports(
            variety_code=None,  # 获取所有品种
            start_date=date.today(),
            end_date=date.today(),
            limit=100  # 每次最多100条
        )

        if reports_data and reports_data.get('reports'):
            logger.info(f"[智汇期讯] 成功获取研报数据 {len(reports_data['reports'])} 条")

            db = SessionLocal()
            try:
                today = date.today()
                for report_dict in reports_data['reports']:
                    # 检查是否已存在（根据report_id）
                    existing = db.query(ResearchReport).filter(
                        ResearchReport.report_id == report_dict['report_id']
                    ).first()

                    if not existing:
                        report = ResearchReport(
                            report_id=report_dict['report_id'],
                            comm_code=report_dict['variety_code'],
                            variety_name=report_dict['variety'],
                            institution_id=report_dict['institution_id'],
                            institution_name=report_dict['institution_name'],
                            publish_date=datetime.strptime(report_dict['publish_date'], '%Y-%m-%d').date(),
                            view_port=report_dict['view_port'],
                            sentiment=report_dict['sentiment'],
                            trade_logic=report_dict['trade_logic'],
                            related_data=report_dict['related_data'],
                            risk_factor=report_dict['risk_factor'],
                            report_link=report_dict['link']
                        )
                        db.add(report)

                db.commit()
                logger.info(f"[智汇期讯] 研报数据已保存到数据库")
            finally:
                db.close()

        return {"full_view": len(full_view) if full_view else 0,
                "reports": len(reports_data.get('reports', [])) if reports_data else 0}

    except Exception as e:
        logger.error(f"[智汇期讯] 数据爬取失败: {e}")
        import traceback
        traceback.print_exc()
        raise


# ========================================
# 方期看盘爬虫 - 早盘8:50 / 夜盘20:50
# ========================================
async def crawl_fangqi_morning():
    """方期看盘早盘数据爬取 - 每天 8:50"""
    try:
        logger.info("=" * 50)
        logger.info("[方期看盘-早盘] 开始执行数据爬取任务")
        logger.info("=" * 50)

        spider = FangqiSpider()
        await spider.init_browser(headless=True)

        try:
            morning_data = await spider.fetch_all_varieties_detail(opening_type="早盘提示")
            logger.info(f"[方期看盘-早盘] 成功获取数据 {len(morning_data)} 条")

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
                logger.info("[方期看盘-早盘] 数据已保存到数据库")
            finally:
                db.close()

        finally:
            await spider.close()

    except Exception as e:
        logger.error(f"[方期看盘-早盘] 数据爬取失败: {e}")


async def crawl_fangqi_night():
    """方期看盘夜盘数据爬取 - 每天 20:50"""
    try:
        logger.info("=" * 50)
        logger.info("[方期看盘-夜盘] 开始执行数据爬取任务")
        logger.info("=" * 50)

        spider = FangqiSpider()
        await spider.init_browser(headless=True)

        try:
            night_data = await spider.fetch_all_varieties_detail(opening_type="夜盘提示")
            logger.info(f"[方期看盘-夜盘] 成功获取数据 {len(night_data)} 条")

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
                logger.info("[方期看盘-夜盘] 数据已保存到数据库")
            finally:
                db.close()

        finally:
            await spider.close()

    except Exception as e:
        logger.error(f"[方期看盘-夜盘] 数据爬取失败: {e}")


# ========================================
# 交易可查爬虫 - 19:00爬取
# ========================================
@DataCollector(
    source_name="交易可查-每日蓝图",
    max_retries=3,
    retry_delay=1800,  # 30分钟重试
    timeout=300,
    enable_alert=True
)
async def crawl_jiaoyikecha():
    """交易可查爬虫 - 19:00爬取，DataCollector自动重试"""
    logger.info("=" * 50)
    logger.info("[交易可查] 开始执行数据爬取任务")
    logger.info("=" * 50)

    spider = JiaoyiKechaSpider()
    await spider.init_browser(headless=True)

    try:
        # 登录
        if await spider.login():
            # 获取交易蓝图
            blueprint = await spider.fetch_daily_blueprint()

            if blueprint:
                logger.info("[交易可查] 成功获取交易蓝图")

                # 保存到数据库
                db = SessionLocal()
                try:
                    # Parse strategies
                    strategies_json = "[]"
                    try:
                        parser = BlueprintParser()
                        strategies = parser.parse_image(blueprint.get('local_path'))
                        strategies_json = json.dumps(strategies, ensure_ascii=False)
                        logger.info(f"[交易可查] 成功解析 {len(strategies)} 条策略")
                    except Exception as e:
                        logger.error(f"[交易可查] 策略解析失败: {e}")

                    db_blueprint = DailyBlueprint(
                        image_url=blueprint.get('image_url'),
                        local_path=blueprint.get('local_path'),
                        record_date=date.today(),
                        parsed_strategies=strategies_json,
                        created_at=datetime.now()
                    )
                    db.add(db_blueprint)
                    db.commit()
                    logger.info("[交易可查] 蓝图已保存到数据库")
                finally:
                    db.close()

                # 获取席位数据
                await _crawl_jyk_positions(spider)

                return {"blueprint": blueprint, "strategies": strategies_json}
            else:
                raise Exception("未获取到蓝图数据")
        else:
            raise Exception("登录失败")

    finally:
        await spider.close()


async def _crawl_jyk_positions(spider: JiaoyiKechaSpider):
    """爬取席位持仓数据"""
    try:
        logger.info("[交易可查] 开始爬取席位持仓数据...")

        # 主流品种列表
        varieties = ['rb', 'hc', 'i', 'j', 'jm', 'cu', 'al', 'zn', 'au', 'ag']

        db = SessionLocal()
        try:
            for variety_code in varieties:
                logger.info(f"[交易可查] 正在获取 {variety_code} 的席位数据...")
                positions = await spider.fetch_variety_positions(variety_code)

                if positions:
                    for pos in positions:
                        try:
                            net_pos = pos.get('net_position', '0')
                            if isinstance(net_pos, str):
                                net_pos = int(net_pos.replace(',', '').replace(' ', '') or '0')
                            change = pos.get('change', '0')
                            if isinstance(change, str):
                                change = int(change.replace(',', '').replace(' ', '') or '0')

                            position = InstitutionalPosition(
                                comm_code=variety_code.upper(),
                                broker_name=pos.get('broker', ''),
                                net_position=net_pos,
                                position_change=change,
                                record_date=date.today(),
                                created_at=datetime.now()
                            )
                            db.add(position)
                        except (ValueError, TypeError) as e:
                            logger.warning(f"解析持仓数据失败: {e}")
                            continue

                    logger.info(f"[交易可查] {variety_code} 席位数据已添加")

                await asyncio.sleep(2)  # 延迟避免请求过快

            db.commit()
            logger.info("[交易可查] 所有席位数据已保存")

        finally:
            db.close()

    except Exception as e:
        logger.error(f"[交易可查] 席位数据爬取失败: {e}")


# ========================================
# Openvlab爬虫 - 交易时段分钟级监控
# 9:00-11:30, 13:00-15:00
# ========================================
@DataCollector(
    source_name="openvlab-期权流向",
    max_retries=2,
    retry_delay=120,
    timeout=60,
    enable_alert=False  # 频繁运行，不发送告警
)
async def crawl_openvlab():
    """Openvlab期权数据爬取 - 交易时段分钟级监控"""
    now = datetime.now()
    current_time = now.time()

    # 检查是否在交易时间内
    # 日盘: 9:00-11:30, 13:00-15:00
    # 夜盘: 21:00-次日02:00
    morning_start = datetime.strptime("09:00", "%H:%M").time()
    morning_end = datetime.strptime("11:30", "%H:%M").time()
    afternoon_start = datetime.strptime("13:00", "%H:%M").time()
    afternoon_end = datetime.strptime("15:00", "%H:%M").time()
    night_start = datetime.strptime("21:00", "%H:%M").time()
    night_end = datetime.strptime("02:00", "%H:%M").time()

    # 夜盘跨越午夜,需要特殊处理
    is_night_time = (current_time >= night_start) or (current_time <= night_end)

    is_trading_time = (
        (morning_start <= current_time <= morning_end) or
        (afternoon_start <= current_time <= afternoon_end) or
        is_night_time
    )

    if not is_trading_time:
        logger.debug("[Openvlab] 非交易时间，跳过")
        return []

    logger.info(f"[Openvlab] 开始执行数据爬取 ({now.strftime('%H:%M:%S')})")

    spider = OpenvlabSpider()
    await spider.init_browser(headless=True)

    try:
        # 获取期权流数据
        option_flow = await spider.fetch_option_flow_data()

        if option_flow:
            logger.info(f"[Openvlab] 成功获取期权流数据 {len(option_flow)} 条")

            db = SessionLocal()
            try:
                for item in option_flow:
                    flow_record = OptionFlow(
                        comm_code=item.get('variety', ''),
                        contract_code=item.get('contract_code', ''),
                        net_flow=item.get('net_flow', 0),
                        volume=item.get('volume', 0),
                        change_ratio=item.get('change_ratio', 0),
                        record_time=datetime.now(),
                        created_at=datetime.now()
                    )
                    db.add(flow_record)

                db.commit()
                logger.info("[Openvlab] 数据已保存到数据库")
            finally:
                db.close()

        return option_flow

    finally:
        await spider.close()


# ========================================
# 融达数据分析家爬虫 - 每天15:00
# ========================================
async def crawl_rongda():
    """融达数据分析家爬取 - 每天 15:00"""
    try:
        logger.info("=" * 50)
        logger.info("[融达数据分析家] 开始执行数据爬取任务")
        logger.info("=" * 50)

        spider = RongdaSpider()
        await spider.init_browser(headless=True)

        try:
            # 获取期限结构数据
            term_data = await spider.fetch_market_structure()

            if term_data:
                logger.info(f"[融达数据分析家] 成功获取期限结构数据 {len(term_data)} 条")

                db = SessionLocal()
                try:
                    for item in term_data:
                        indicator = TechnicalIndicator(
                            comm_code=item.get('variety', ''),
                            term_structure=item.get('structure_type'),  # contango/back
                            record_time=datetime.now(),
                            created_at=datetime.now()
                        )
                        db.add(indicator)

                    db.commit()
                    logger.info("[融达数据分析家] 数据已保存到数据库")
                finally:
                    db.close()

        finally:
            await spider.close()

    except Exception as e:
        logger.error(f"[融达数据分析家] 数据爬取失败: {e}")


# ========================================
# 辅助函数
# ========================================
def _determine_sentiment(direction: str) -> str:
    """根据方向判断情绪"""
    direction = direction.lower()
    if '多' in direction or '涨' in direction or 'long' in direction:
        return 'bull'
    elif '空' in direction or '跌' in direction or 'short' in direction:
        return 'bear'
    else:
        return 'neutral'


# ========================================
# 调度器管理
# ========================================
def init_scheduler():
    """初始化定时任务"""
    logger.info("=" * 60)
    logger.info("初始化定时任务调度器...")
    logger.info("=" * 60)

    # 1. 智汇期讯 - 每30分钟一次
    scheduler.add_job(
        crawl_zhihui_data,
        IntervalTrigger(minutes=30),
        id='crawl_zhihui',
        name='智汇期讯-每30分钟',
        replace_existing=True
    )

    # 2. 方期看盘-早盘 - 每天 8:50
    scheduler.add_job(
        crawl_fangqi_morning,
        CronTrigger(hour=8, minute=50),
        id='crawl_fangqi_morning',
        name='方期看盘-早盘8:50',
        replace_existing=True
    )

    # 3. 方期看盘-夜盘 - 每天 20:50
    scheduler.add_job(
        crawl_fangqi_night,
        CronTrigger(hour=20, minute=50),
        id='crawl_fangqi_night',
        name='方期看盘-夜盘20:50',
        replace_existing=True
    )

    # 4. 交易可查 - 每天 19:00 (失败30分钟重试)
    scheduler.add_job(
        crawl_jiaoyikecha,
        CronTrigger(hour=19, minute=0),
        id='crawl_jiaoyikecha',
        name='交易可查-19:00',
        replace_existing=True
    )

    # 5. Openvlab - 交易时段每分钟监控
    #    9:00-11:30, 13:00-15:00
    scheduler.add_job(
        crawl_openvlab,
        IntervalTrigger(minutes=1),
        id='crawl_openvlab',
        name='Openvlab-分钟级监控',
        replace_existing=True
    )

    # 6. 融达数据分析家 - 已禁用 (不再爬取该网站)
    # scheduler.add_job(
    #     crawl_rongda,
    #     CronTrigger(hour=15, minute=0),
    #     id='crawl_rongda',
    #     name='融达数据分析家-15:00',
    #     replace_existing=True
    # )

    # 7. 每日全品种分析 - 每天 21:30 (所有数据爬取完成后)
    from app.services.analysis import AnalysisService
    from app.models.database import SessionLocal
    
    async def run_analysis_job():
        db = SessionLocal()
        try:
            service = AnalysisService(db)
            service.run_daily_analysis()
        finally:
            db.close()

    scheduler.add_job(
        run_analysis_job,
        CronTrigger(hour=19, minute=30),
        id='run_daily_analysis',
        name='每日全品种分析-19:30',
        replace_existing=True
    )

    # 8. 虚实比数据爬取 - 每天18:00
    @DataCollector(
        source_name="虚实比数据-AKShare",
        max_retries=2,
        retry_delay=600,
        timeout=180,
        enable_alert=True
    )
    async def crawl_virtual_real_ratio():
        """虚实比数据爬取 - 每天18:00"""
        logger.info("=" * 50)
        logger.info("[虚实比] 开始执行数据爬取任务")
        logger.info("=" * 50)

        from app.crawlers.virtual_real_ratio_spider_uqer import VirtualRealRatioSpiderUqer
        from app.services.uqer_sdk_client import init_uqer_sdk_client
        from config.settings import get_settings

        # 初始化优矿SDK客户端
        settings = get_settings()
        if settings.UQER_TOKEN:
            init_uqer_sdk_client(settings.UQER_TOKEN)
        else:
            logger.error("[虚实比] 优矿Token未配置")
            return

        db = SessionLocal()
        try:
            spider = VirtualRealRatioSpiderUqer(db=db)
            results = spider.crawl_all_varieties()

            success_count = sum(1 for v in results.values() if v)
            total_count = len(results)

            logger.info(f"[虚实比] 数据爬取完成: 成功 {success_count}/{total_count} 个品种")

            if success_count > 0:
                logger.info("[虚实比] ✅ 至少部分品种更新成功")
            else:
                logger.warning("[虚实比] ⚠️ 所有品种更新失败")

        except Exception as e:
            logger.error(f"[虚实比] 数据爬取失败: {e}")
            raise
        finally:
            db.close()

    scheduler.add_job(
        lambda: asyncio.create_task(crawl_virtual_real_ratio()),
        CronTrigger(hour=18, minute=0),
        id='crawl_virtual_real_ratio',
        name='虚实比数据-18:00',
        replace_existing=True
    )

    # 9. 数据库备份任务
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from scripts.backup_database import DatabaseBackup

    def run_backup(backup_type: str):
        """执行数据库备份"""
        try:
            backup_manager = DatabaseBackup()
            success = backup_manager.create_backup(backup_type)
            if success:
                logger.info(f"✅ {backup_type} 备份完成")
            else:
                logger.error(f"❌ {backup_type} 备份失败")
        except Exception as e:
            logger.error(f"❌ {backup_type} 备份异常: {e}")

    # 小时级备份 - 每小时执行
    scheduler.add_job(
        lambda: run_backup('hourly'),
        IntervalTrigger(hours=1),
        id='backup_hourly',
        name='数据库备份-小时级',
        replace_existing=True
    )

    # 天级备份 - 每天凌晨3点
    scheduler.add_job(
        lambda: run_backup('daily'),
        CronTrigger(hour=3, minute=0),
        id='backup_daily',
        name='数据库备份-天级-03:00',
        replace_existing=True
    )

    # 周级备份 - 每周日凌晨3点
    scheduler.add_job(
        lambda: run_backup('weekly'),
        CronTrigger(day_of_week='sun', hour=3, minute=0),
        id='backup_weekly',
        name='数据库备份-周级-周日03:00',
        replace_existing=True
    )

    logger.info("")
    logger.info("定时任务配置完成:")
    logger.info("  ┌──────────────────────────────────────────────────────┐")
    logger.info("  │  智汇期讯        │ 每 30 分钟一次                    │")
    logger.info("  │  方期看盘-早盘   │ 每天 08:50                        │")
    logger.info("  │  方期看盘-夜盘   │ 每天 20:50                        │")
    logger.info("  │  交易可查        │ 每天 19:00 (失败30分钟重试)       │")
    logger.info("  │  Openvlab        │ 交易时段每分钟 (日盘+夜盘21-02)  │")
    logger.info("  │  每日全品种分析  │ 每天 19:30                        │")
    logger.info("  │  虚实比数据      │ 每天 18:00                        │")
    logger.info("  │  数据库备份-小时 │ 每小时一次                        │")
    logger.info("  │  数据库备份-天级 │ 每天 03:00                        │")
    logger.info("  │  数据库备份-周级 │ 每周日 03:00                      │")
    logger.info("  └──────────────────────────────────────────────────────┘")
    logger.info("")


def start_scheduler():
    """启动调度器"""
    scheduler.start()
    logger.info("✅ 定时任务调度器已启动")

    # 列出所有任务
    jobs = scheduler.get_jobs()
    logger.info(f"当前活跃任务数: {len(jobs)}")
    for job in jobs:
        logger.info(f"  - {job.name}: 下次执行 {job.next_run_time}")


def stop_scheduler():
    """停止调度器"""
    scheduler.shutdown()
    logger.info("定时任务调度器已停止")


def get_scheduler_status():
    """获取调度器状态"""
    jobs = scheduler.get_jobs()
    return {
        "running": scheduler.running,
        "job_count": len(jobs),
        "jobs": [
            {
                "id": job.id,
                "name": job.name,
                "next_run": str(job.next_run_time) if job.next_run_time else None
            }
            for job in jobs
        ]
    }
