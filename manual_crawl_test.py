#!/usr/bin/env python3
"""
手动触发所有爬虫执行一次 - 验证爬虫功能
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from app.scheduler import (
    crawl_zhihui_data,
    crawl_fangqi_morning,
    crawl_fangqi_night,
    crawl_jiaoyikecha,
    crawl_openvlab,
    crawl_rongda
)
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def main():
    """手动执行所有爬虫"""
    print("=" * 80)
    print("🚀 开始手动执行所有爬虫（验证功能）")
    print("=" * 80)
    print()

    results = {
        "success": [],
        "failed": []
    }

    # 1. 智汇期讯
    print("1️⃣  执行智汇期讯爬虫...")
    print("-" * 80)
    try:
        await crawl_zhihui_data()
        results["success"].append("智汇期讯")
        print("✅ 智汇期讯 - 执行完成\n")
    except Exception as e:
        results["failed"].append(("智汇期讯", str(e)))
        print(f"❌ 智汇期讯 - 执行失败: {e}\n")

    # 2. 方期看盘-早盘
    print("2️⃣  执行方期看盘-早盘爬虫...")
    print("-" * 80)
    try:
        await crawl_fangqi_morning()
        results["success"].append("方期看盘-早盘")
        print("✅ 方期看盘-早盘 - 执行完成\n")
    except Exception as e:
        results["failed"].append(("方期看盘-早盘", str(e)))
        print(f"❌ 方期看盘-早盘 - 执行失败: {e}\n")

    # 3. 方期看盘-夜盘
    print("3️⃣  执行方期看盘-夜盘爬虫...")
    print("-" * 80)
    try:
        await crawl_fangqi_night()
        results["success"].append("方期看盘-夜盘")
        print("✅ 方期看盘-夜盘 - 执行完成\n")
    except Exception as e:
        results["failed"].append(("方期看盘-夜盘", str(e)))
        print(f"❌ 方期看盘-夜盘 - 执行失败: {e}\n")

    # 4. 交易可查
    print("4️⃣  执行交易可查爬虫...")
    print("-" * 80)
    try:
        await crawl_jiaoyikecha()
        results["success"].append("交易可查")
        print("✅ 交易可查 - 执行完成\n")
    except Exception as e:
        results["failed"].append(("交易可查", str(e)))
        print(f"❌ 交易可查 - 执行失败: {e}\n")

    # 5. Openvlab
    print("5️⃣  执行Openvlab爬虫...")
    print("-" * 80)
    try:
        await crawl_openvlab()
        results["success"].append("Openvlab")
        print("✅ Openvlab - 执行完成\n")
    except Exception as e:
        results["failed"].append(("Openvlab", str(e)))
        print(f"❌ Openvlab - 执行失败: {e}\n")

    # 6. 融达数据分析家
    print("6️⃣  执行融达数据分析家爬虫...")
    print("-" * 80)
    try:
        await crawl_rongda()
        results["success"].append("融达数据分析家")
        print("✅ 融达数据分析家 - 执行完成\n")
    except Exception as e:
        results["failed"].append(("融达数据分析家", str(e)))
        print(f"❌ 融达数据分析家 - 执行失败: {e}\n")

    # 汇总结果
    print("=" * 80)
    print("📊 执行结果汇总")
    print("=" * 80)
    print(f"\n✅ 成功: {len(results['success'])} 个")
    for name in results["success"]:
        print(f"   - {name}")

    print(f"\n❌ 失败: {len(results['failed'])} 个")
    for name, error in results["failed"]:
        print(f"   - {name}: {error[:100]}...")

    print("\n" + "=" * 80)
    print("🎯 所有爬虫已手动执行一次")
    print("现在它们将按照正常时间表自动运行:")
    print("  - 智汇期讯: 每30分钟")
    print("  - 方期看盘-早盘: 每天08:50")
    print("  - 方期看盘-夜盘: 每天20:50")
    print("  - 交易可查: 每天19:00 (失败30分钟重试)")
    print("  - Openvlab: 交易时段每分钟 (日盘+夜盘21-02)")
    print("  - 融达数据分析家: 每天15:00")
    print("=" * 80)

    # 查询数据库看看有多少数据
    print("\n📦 检查数据库中的数据...")
    try:
        import sqlite3
        conn = sqlite3.connect("option_tracker.db")
        cursor = conn.cursor()

        # 检查各个表的数据量
        tables = [
            ("fundamental_reports", "基本面研报"),
            ("institutional_positions", "机构持仓"),
            ("technical_indicators", "技术指标"),
            ("daily_blueprints", "交易蓝图"),
            ("market_analysis_summary", "综合分析")
        ]

        print()
        for table_name, display_name in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"  {display_name} ({table_name}): {count} 条")

        conn.close()
    except Exception as e:
        print(f"  ⚠️  数据库查询失败: {e}")


if __name__ == "__main__":
    asyncio.run(main())
