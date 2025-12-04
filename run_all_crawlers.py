import asyncio
import logging
from app.crawlers.zhihui_spider import ZhihuiQixunSpider
from app.crawlers.fangqi_spider import FangqiSpider
from app.crawlers.rongda_spider import RongdaSpider
from app.crawlers.openvlab_spider import OpenvlabSpider
# from app.crawlers.jiaoyikecha_spider import JiaoyiKechaSpider # JYK might be slow/need login, skip for quick demo or try later
from app.services.analysis import AnalysisService
from app.models.database import SessionLocal
from app.models.models import FundamentalReport, TechnicalIndicator, ContractInfo, Commodity, OptionFlow
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_crawlers():
    db = SessionLocal()
    
    # 0. Ensure Commodities exist (Seed data)
    # We need some commodities to attach data to
    commodities = [
        ("RB", "螺纹钢"), ("CU", "沪铜"), ("AU", "沪金"), ("AG", "沪银"),
        ("M", "豆粕"), ("Y", "豆油"), ("OI", "菜油"), ("P", "棕榈油"),
        ("I", "铁矿石"), ("J", "焦炭"), ("JM", "焦煤"), ("C", "玉米"),
        ("CF", "棉花"), ("SR", "白糖"), ("TA", "PTA"), ("MA", "甲醇"),
        ("PP", "聚丙烯"), ("L", "塑料"), ("V", "PVC"), ("HC", "热卷")
    ]
    for code, name in commodities:
        if not db.query(Commodity).filter_by(code=code).first():
            db.add(Commodity(code=code, name=name))
            # Add default contract info
            db.add(ContractInfo(comm_code=code, multiplier=10, latest_price=3000)) # Mock price
    db.commit()
    
    # 1. Zhihui Qixun
    logger.info("Running Zhihui Spider...")
    zh_spider = ZhihuiQixunSpider()
    await zh_spider.init_browser(headless=True)
    try:
        if await zh_spider.login():
            full_view = await zh_spider.fetch_full_view()
            for item in full_view:
                report = FundamentalReport(
                    comm_code=item.get('variety_code', ''),
                    source='hzzhqx',
                    report_type='fullview',
                    sentiment=item.get('main_sentiment', 'neutral'),
                    content_summary=f"看多 {item.get('excessive_ratio', 0)}%, 看空 {item.get('empty_ratio', 0)}%",
                    publish_time=datetime.now()
                )
                db.add(report)
            db.commit()
    except Exception as e:
        logger.error(f"Zhihui Error: {e}")
    finally:
        await zh_spider.close()

    # 2. Fangqi
    logger.info("Running Fangqi Spider...")
    fq_spider = FangqiSpider()
    try:
        # Night data (latest)
        night_data = await fq_spider.fetch_night_data()
        if night_data:
            varieties = fq_spider.parse_variety_list(night_data)
            for item in varieties:
                report = FundamentalReport(
                    comm_code=item.get('variety_code', ''),
                    source='founderfu',
                    report_type='night',
                    sentiment='bull' if item.get('direction') == '多' else 'bear',
                    content_summary=f"方期评级: {item.get('rating')}",
                    publish_time=datetime.now()
                )
                db.add(report)
            db.commit()
    except Exception as e:
        logger.error(f"Fangqi Error: {e}")
    finally:
        await fq_spider.close()

    # 3. Rongda
    logger.info("Running Rongda Spider...")
    rd_spider = RongdaSpider()
    await rd_spider.init_browser(headless=True)
    try:
        term_data = await rd_spider.fetch_market_structure()
        for item in term_data:
            # Map Chinese variety name to code if possible, or skip
            # For demo, we might need a mapper. 
            # Rongda returns 'variety' name like '螺纹钢'.
            # Simple mapper:
            name_map = {c[1]: c[0] for c in commodities}
            code = name_map.get(item.get('variety', ''), '')
            
            if code:
                indicator = TechnicalIndicator(
                    comm_code=code,
                    term_structure=item.get('structure_type'),
                    record_time=datetime.now()
                )
                db.add(indicator)
        db.commit()
    except Exception as e:
        logger.error(f"Rongda Error: {e}")
    finally:
        await rd_spider.close()

    # 4. Openvlab
    logger.info("Running Openvlab Spider...")
    ov_spider = OpenvlabSpider()
    await ov_spider.init_browser(headless=True)
    try:
        flow_data = await ov_spider.fetch_option_flow_data()
        for item in flow_data:
            flow = OptionFlow(
                comm_code=item.get('variety', ''),
                contract_code=item.get('contract_code', ''),
                net_flow=item.get('net_flow', 0),
                volume=item.get('volume', 0),
                change_ratio=item.get('change_ratio', 0),
                record_time=datetime.now()
            )
            db.add(flow)
        db.commit()
    except Exception as e:
        logger.error(f"Openvlab Error: {e}")
    finally:
        await ov_spider.close()

    # 5. Run Analysis
    logger.info("Running Analysis...")
    service = AnalysisService(db)
    service.run_daily_analysis()
    
    db.close()
    logger.info("Done!")

if __name__ == "__main__":
    asyncio.run(run_crawlers())
