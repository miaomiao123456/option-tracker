"""
交易可查爬虫 - 爬取并保存到数据库
"""
import asyncio
import logging
import sys
import json
from pathlib import Path
from datetime import date

sys.path.append(str(Path(__file__).parent))

from app.crawlers.jiaoyikecha_spider import JiaoyiKechaSpider
from app.models.database import SessionLocal
from app.models.models import DailyBlueprint

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    """爬取并保存到数据库"""
    spider = JiaoyiKechaSpider()
    db = SessionLocal()

    try:
        print("=" * 60)
        print("1. 初始化浏览器...")
        await spider.init_browser(headless=True)

        print("=" * 60)
        print("2. 登录交易可查...")
        if not await spider.login():
            print("❌ 登录失败")
            return

        print("✅ 登录成功")

        print("=" * 60)
        print("3. 获取交易蓝图...")
        blueprint_data = await spider.fetch_daily_blueprint()

        if not blueprint_data:
            print("❌ 未获取到蓝图数据")
            return

        print(f"✅ 成功获取蓝图:")
        print(f"   标题: {blueprint_data.get('title')}")
        print(f"   日期: {blueprint_data.get('date')}")
        print(f"   策略数: {len(blueprint_data.get('strategies', []))}")

        # 解析日期
        date_str = blueprint_data['date']
        record_date = date(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]))

        # 检查数据库中是否已存在
        existing = db.query(DailyBlueprint).filter(
            DailyBlueprint.record_date == record_date
        ).first()

        # 准备策略JSON
        strategies_json = json.dumps(blueprint_data.get('strategies', []), ensure_ascii=False)

        if existing:
            print("=" * 60)
            print("4. 更新数据库记录...")
            existing.image_url = blueprint_data['image_url']
            existing.local_path = blueprint_data['local_path']
            existing.parsed_strategies = strategies_json
            db.commit()
            print("✅ 数据库记录已更新")
        else:
            print("=" * 60)
            print("4. 保存到数据库...")
            new_blueprint = DailyBlueprint(
                image_url=blueprint_data['image_url'],
                local_path=blueprint_data['local_path'],
                parsed_strategies=strategies_json,
                record_date=record_date
            )
            db.add(new_blueprint)
            db.commit()
            print("✅ 数据已保存到数据库")

        # 显示保存的策略
        print("=" * 60)
        print(f"📊 已保存 {len(blueprint_data.get('strategies', []))} 条高强度策略:")
        for idx, strategy in enumerate(blueprint_data.get('strategies', []), 1):
            print(f"\n{idx}. {strategy.get('variety')} - {strategy.get('direction')}")
            print(f"   强度: {strategy.get('signal')}")
            print(f"   理由: {strategy.get('reason')}")

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        await spider.close()
        db.close()
        print("=" * 60)
        print("✅ 完成")

if __name__ == "__main__":
    asyncio.run(main())
