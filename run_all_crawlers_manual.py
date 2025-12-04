"""
手动执行所有爬虫任务
包括：智汇期讯、方期看盘、交易可查(蓝图+席位)、Openvlab
"""
import asyncio
import logging
import sys
from pathlib import Path
from datetime import date, datetime
import json

sys.path.append(str(Path(__file__).parent))

from app.crawlers.zhihui_spider import ZhihuiQixunSpider
from app.crawlers.fangqi_spider import FangqiSpider
from app.crawlers.jiaoyikecha_spider import JiaoyiKechaSpider
from app.crawlers.openvlab_spider import OpenvlabSpider
from app.models.database import SessionLocal
from app.models.models import (
    DailyBlueprint, FundamentalReport,
    InstitutionalPosition, OptionFlow
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def crawl_zhihui():
    """爬取智汇期讯数据"""
    print("\n" + "=" * 60)
    print("【1/4】智汇期讯 - 多空全景")
    print("=" * 60)

    try:
        spider = ZhihuiQixunSpider()
        data = spider.fetch_full_view()

        if data:
            db = SessionLocal()
            try:
                for item in data:
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
                print(f"✅ 智汇期讯: 成功保存 {len(data)} 条数据")
            finally:
                db.close()
        else:
            print("❌ 智汇期讯: 未获取到数据")

    except Exception as e:
        print(f"❌ 智汇期讯爬取失败: {e}")


async def crawl_fangqi():
    """爬取方期看盘数据"""
    print("\n" + "=" * 60)
    print("【2/4】方期看盘 - 夜盘提示")
    print("=" * 60)

    try:
        spider = FangqiSpider()
        night_data = await spider.fetch_night_data()

        if night_data:
            varieties = spider.parse_variety_list(night_data)
            db = SessionLocal()
            try:
                for item in varieties:
                    sentiment = 'bull' if item['direction'] == '多' else 'bear'
                    report = FundamentalReport(
                        comm_code=item.get('variety_code', ''),
                        source='founderfu',
                        report_type='night',
                        sentiment=sentiment,
                        content_summary=f"{item['smallbreeds']} - 风险值:{item['rating']}",
                        publish_time=datetime.now()
                    )
                    db.add(report)
                db.commit()
                print(f"✅ 方期看盘: 成功保存 {len(varieties)} 条数据")
            finally:
                db.close()
        else:
            print("❌ 方期看盘: 未获取到数据")

    except Exception as e:
        print(f"❌ 方期看盘爬取失败: {e}")


async def crawl_jiaoyikecha():
    """爬取交易可查数据 - 蓝图 + 席位"""
    print("\n" + "=" * 60)
    print("【3/4】交易可查 - 蓝图 + 席位持仓")
    print("=" * 60)

    spider = JiaoyiKechaSpider()
    db = SessionLocal()

    try:
        print("初始化浏览器...")
        await spider.init_browser(headless=True)

        print("登录交易可查...")
        if not await spider.login():
            print("❌ 登录失败")
            return

        print("✅ 登录成功")

        # 1. 获取交易蓝图
        print("\n获取交易蓝图...")
        blueprint = await spider.fetch_daily_blueprint()

        if blueprint:
            date_str = blueprint['date']
            record_date = date(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]))

            strategies_json = json.dumps(blueprint.get('strategies', []), ensure_ascii=False)

            # 检查是否已存在
            existing = db.query(DailyBlueprint).filter(
                DailyBlueprint.record_date == record_date
            ).first()

            if existing:
                existing.image_url = blueprint['image_url']
                existing.local_path = blueprint['local_path']
                existing.parsed_strategies = strategies_json
            else:
                new_blueprint = DailyBlueprint(
                    image_url=blueprint['image_url'],
                    local_path=blueprint['local_path'],
                    parsed_strategies=strategies_json,
                    record_date=record_date
                )
                db.add(new_blueprint)

            db.commit()
            print(f"✅ 交易蓝图: 成功保存 ({record_date})")
            print(f"   策略数: {len(blueprint.get('strategies', []))}")
        else:
            print("❌ 未获取到蓝图")

        # 2. 获取席位持仓数据
        print("\n获取席位持仓数据...")
        varieties = ['rb', 'hc', 'i', 'j', 'jm', 'cu', 'al', 'zn', 'au', 'ag']

        saved_count = 0
        for variety_code in varieties:
            print(f"  正在获取 {variety_code.upper()} 席位数据...")
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
                        saved_count += 1
                    except (ValueError, TypeError) as e:
                        logger.warning(f"解析 {variety_code} 持仓数据失败: {e}")
                        continue

            await asyncio.sleep(2)  # 延迟避免请求过快

        db.commit()
        print(f"✅ 席位持仓: 成功保存 {saved_count} 条数据")

    except Exception as e:
        print(f"❌ 交易可查爬取失败: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        await spider.close()
        db.close()


async def crawl_openvlab():
    """爬取Openvlab期权流数据"""
    print("\n" + "=" * 60)
    print("【4/4】Openvlab - 期权资金流")
    print("=" * 60)

    spider = OpenvlabSpider()

    try:
        print("初始化浏览器...")
        await spider.init_browser(headless=True)

        print("获取期权流数据...")
        option_flow = await spider.fetch_option_flow_data()

        if option_flow:
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
                print(f"✅ Openvlab: 成功保存 {len(option_flow)} 条数据")
            finally:
                db.close()
        else:
            print("❌ Openvlab: 未获取到数据")

    except Exception as e:
        print(f"❌ Openvlab爬取失败: {e}")
    finally:
        await spider.close()


async def main():
    """主函数 - 顺序执行所有爬虫"""
    print("\n" + "🚀" * 30)
    print("开始手动执行所有爬虫任务")
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🚀" * 30)

    start_time = datetime.now()

    # 顺序执行所有爬虫
    await crawl_zhihui()
    await crawl_fangqi()
    await crawl_jiaoyikecha()
    await crawl_openvlab()

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print("\n" + "=" * 60)
    print(f"✅ 所有爬虫任务执行完成")
    print(f"   总耗时: {duration:.2f} 秒")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
