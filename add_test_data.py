#!/usr/bin/env python3
"""
添加测试数据到数据库
"""
import sqlite3
from datetime import datetime, date
from pathlib import Path

def add_test_data():
    """添加示例分析数据"""
    db_path = Path("option_tracker.db")

    if not db_path.exists():
        print("❌ 数据库文件不存在")
        return

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # 今天的日期
    today = date.today()

    # 示例商品的四维分析数据
    test_data = [
        # (code, fundamental, capital, technical, message, direction, reason)
        ("RB", 2, 3, 1, 2, "LONG", "基本面向好,资金持续流入,技术面突破关键阻力位"),
        ("HC", 1, 2, 2, 1, "LONG", "跟随螺纹上涨,资金面配合"),
        ("I", -1, -2, -1, -1, "SHORT", "需求转弱,机构减仓明显"),
        ("J", 1, 1, 0, 1, "LONG", "供应偏紧,多头氛围"),
        ("JM", 0, -1, -1, 0, "SHORT", "技术面破位,资金流出"),
        ("CU", 3, 2, 2, 2, "LONG", "美元走弱,有色金属全面上涨"),
        ("AL", 2, 1, 1, 2, "LONG", "电力紧张预期,铝价受支撑"),
        ("ZN", -2, -1, -2, -1, "SHORT", "需求疲软,锌价承压"),
        ("AU", 1, 2, 2, 1, "LONG", "避险需求上升,黄金走强"),
        ("AG", 2, 3, 2, 2, "LONG", "工业需求回升,白银表现强劲"),
    ]

    print(f"开始添加 {len(test_data)} 条分析数据...")

    added = 0
    for code, f_score, c_score, t_score, m_score, direction, reason in test_data:
        try:
            # 检查是否已存在
            cursor.execute("""
                SELECT id FROM market_analysis_summary
                WHERE comm_code = ? AND date = ?
            """, (code, str(today)))

            if cursor.fetchone():
                print(f"  ⏭️  {code} 今日数据已存在")
                continue

            # 插入数据
            cursor.execute("""
                INSERT INTO market_analysis_summary
                (comm_code, date, fundamental_score, capital_score, technical_score,
                 message_score, total_direction, main_reason, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                code,
                str(today),
                f_score,
                c_score,
                t_score,
                m_score,
                direction,
                reason,
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))

            added += 1
            total_score = f_score + c_score + t_score + m_score
            print(f"  ✅ {code}: {direction} (总分{total_score:+d})")

        except Exception as e:
            print(f"  ❌ {code} 添加失败: {e}")
            continue

    conn.commit()
    conn.close()

    print(f"\n完成! 共添加 {added} 条分析数据")
    print(f"日期: {today}")
    print("\n现在刷新前端页面应该可以看到数据了!")

if __name__ == "__main__":
    add_test_data()
