#!/usr/bin/env python3
"""
添加虚实比增强字段到 warehouse_receipts 表
Phase 1.1: 数据库字段增强
"""

import sqlite3
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

def add_enhancement_columns():
    """添加虚实比增强分析字段"""

    db_path = Path(__file__).parent.parent / "option_tracker.db"

    if not db_path.exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        return False

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # 要添加的字段列表
    new_columns = [
        # 历史位置指标
        ("percentile_30d", "DECIMAL(5,2)", "30日百分位"),
        ("percentile_90d", "DECIMAL(5,2)", "90日百分位"),
        ("mean_30d", "DECIMAL(10,2)", "30日均值"),
        ("std_30d", "DECIMAL(10,2)", "30日标准差"),
        ("zscore", "DECIMAL(10,4)", "Z-score统计值"),

        # 变化率指标
        ("change_rate_3d", "DECIMAL(10,4)", "3日变化率"),
        ("change_rate_7d", "DECIMAL(10,4)", "7日变化率"),
        ("acceleration", "DECIMAL(10,4)", "加速度指标"),

        # 信号标识
        ("signal_type", "VARCHAR(50)", "信号类型"),
        ("signal_score", "INTEGER", "信号得分(0-100)"),
    ]

    print("🔧 开始添加虚实比增强字段...")
    print(f"📍 数据库路径: {db_path}")
    print()

    # 检查并添加每个字段
    for col_name, col_type, comment in new_columns:
        try:
            # 检查字段是否已存在
            cursor.execute(f"PRAGMA table_info(warehouse_receipts)")
            existing_columns = [row[1] for row in cursor.fetchall()]

            if col_name in existing_columns:
                print(f"⏭️  字段已存在: {col_name} - {comment}")
                continue

            # 添加字段
            sql = f"ALTER TABLE warehouse_receipts ADD COLUMN {col_name} {col_type}"
            cursor.execute(sql)
            conn.commit()
            print(f"✅ 添加字段成功: {col_name} {col_type} - {comment}")

        except sqlite3.Error as e:
            print(f"❌ 添加字段失败 {col_name}: {e}")
            conn.rollback()
            return False

    print()
    print("=" * 60)
    print("✅ 所有字段添加完成!")
    print("=" * 60)

    # 验证新表结构
    print("\n📋 当前 warehouse_receipts 表结构:")
    cursor.execute("PRAGMA table_info(warehouse_receipts)")
    columns = cursor.fetchall()

    print(f"\n共 {len(columns)} 个字段:")
    for col in columns:
        col_id, col_name, col_type, not_null, default_val, pk = col
        print(f"  {col_id:2d}. {col_name:20s} {col_type:15s}")

    conn.close()
    return True

if __name__ == "__main__":
    print("🚀 虚实比增强 - 数据库字段升级脚本")
    print("=" * 60)
    print()

    success = add_enhancement_columns()

    if success:
        print("\n✅ 数据库升级成功!")
        print("\n下一步:")
        print("  1. 实现历史位置计算逻辑 (Phase 1.2)")
        print("  2. 实现变化率计算逻辑 (Phase 1.3)")
        print("  3. 实现信号识别逻辑 (Phase 1.4)")
        sys.exit(0)
    else:
        print("\n❌ 数据库升级失败!")
        sys.exit(1)
