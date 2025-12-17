#!/usr/bin/env python3
"""
虚实比字段迁移脚本
将 price_pressure 字段迁移到 market_activity
"""
import sqlite3
import sys
from pathlib import Path

def migrate_database(db_path='option_tracker.db'):
    """执行数据库迁移"""
    print("📊 开始执行虚实比字段迁移...")
    print(f"📂 数据库路径: {db_path}")

    # 检查数据库文件是否存在
    if not Path(db_path).exists():
        print(f"❌ 错误: 数据库文件 {db_path} 不存在")
        return False

    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 检查market_activity字段是否已存在
        cursor.execute("PRAGMA table_info(warehouse_receipts)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'market_activity' in columns:
            print("⚠️  market_activity 字段已存在")

            # 检查是否有数据需要更新
            cursor.execute("SELECT COUNT(*) FROM warehouse_receipts WHERE market_activity IS NULL")
            null_count = cursor.fetchone()[0]

            if null_count > 0:
                print(f"📝 发现 {null_count} 条记录的 market_activity 为空,将进行填充...")
            else:
                print("✅ 所有记录的 market_activity 已填充,无需迁移")
                conn.close()
                return True
        else:
            print("➕ 添加 market_activity 字段...")
            cursor.execute("ALTER TABLE warehouse_receipts ADD COLUMN market_activity VARCHAR(20)")
            print("✅ market_activity 字段添加成功")

        # 迁移数据
        print("\n🔄 开始迁移数据...")
        cursor.execute("""
            UPDATE warehouse_receipts
            SET market_activity = CASE
                WHEN virtual_real_ratio > 100 THEN '极度活跃'
                WHEN virtual_real_ratio > 50 THEN '活跃'
                WHEN virtual_real_ratio > 20 THEN '平稳'
                ELSE '平淡'
            END
            WHERE market_activity IS NULL OR market_activity = ''
        """)

        updated_rows = cursor.rowcount
        print(f"✅ 成功更新 {updated_rows} 条记录")

        # 验证迁移结果
        cursor.execute("""
            SELECT market_activity, COUNT(*) as count
            FROM warehouse_receipts
            GROUP BY market_activity
            ORDER BY market_activity
        """)

        print("\n📊 迁移结果统计:")
        print("-" * 40)
        for row in cursor.fetchall():
            activity = row[0] if row[0] else 'NULL'
            count = row[1]
            print(f"  {activity:12s}: {count:>6d} 条")
        print("-" * 40)

        # 提交事务
        conn.commit()
        print("\n✅ 数据库迁移成功完成!")

        # 显示提示信息
        print("\n📌 后续操作:")
        print("  1. 重启服务: cd option_tracker && python3 main.py")
        print("  2. 访问页面: http://localhost:8000/virtual_real_ratio.html")
        print("  3. 点击「更新所有数据」按钮刷新最新数据")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 获取数据库路径
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        # 默认路径
        script_dir = Path(__file__).parent
        db_path = script_dir / 'option_tracker.db'

    # 执行迁移
    success = migrate_database(str(db_path))

    # 返回退出码
    sys.exit(0 if success else 1)
