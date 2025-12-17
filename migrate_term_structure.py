#!/usr/bin/env python3
"""
期限结构历史化迁移脚本 (Phase 3.3 + 3.4)
功能:
1. 创建 term_structure_history 表
2. 从 JSON 数据迁移到数据库
"""
import sqlite3
import json
import sys
from pathlib import Path
from datetime import datetime, date

def migrate_database(db_path='option_tracker.db', json_dir='data'):
    """执行数据库迁移"""
    print("📊 开始执行期限结构历史化迁移...")
    print(f"📂 数据库路径: {db_path}")
    print(f"📂 JSON数据目录: {json_dir}")

    # 检查数据库文件是否存在
    if not Path(db_path).exists():
        print(f"❌ 错误: 数据库文件 {db_path} 不存在")
        return False

    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # === Phase 3.3: 创建表和索引 ===
        print("\n🔧 Phase 3.3: 创建 term_structure_history 表...")

        # 检查表是否已存在
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='term_structure_history'
        """)

        if cursor.fetchone():
            print("⚠️  term_structure_history 表已存在")
            cursor.execute("SELECT COUNT(*) FROM term_structure_history")
            count = cursor.fetchone()[0]
            print(f"   当前记录数: {count} 条")

            # 询问是否清空
            print("\n⚠️  检测到表已存在,选项:")
            print("   1. 清空后重新导入")
            print("   2. 追加导入(保留现有数据)")
            print("   3. 跳过导入")

            # 这里简化处理,直接追加
            print("   📝 将追加导入新数据...")
        else:
            print("✅ 开始创建表...")

            # 创建表
            cursor.execute("""
                CREATE TABLE term_structure_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    comm_code VARCHAR(20) NOT NULL,
                    variety_name VARCHAR(50),
                    record_date DATE NOT NULL,

                    -- 结构类型
                    structure_type VARCHAR(20),
                    market_structure VARCHAR(20),
                    structure_desc TEXT,

                    -- 合约信息
                    near_contract VARCHAR(20),
                    far_contract VARCHAR(20),
                    near_price FLOAT,
                    far_price FLOAT,
                    near_volume INTEGER,
                    near_oi INTEGER,

                    -- 价差分析
                    price_spread FLOAT,
                    spread_pct FLOAT,
                    roll_yield FLOAT,

                    -- Phase 3 增强字段 - 结构分析
                    structure_strength FLOAT,
                    structure_days INTEGER,
                    structure_score FLOAT,
                    grade VARCHAR(5),
                    recommend INTEGER DEFAULT 0,

                    -- Phase 3 增强字段 - 历史位置
                    spread_percentile_30d FLOAT,
                    spread_percentile_90d FLOAT,
                    spread_mean_30d FLOAT,
                    spread_std_30d FLOAT,

                    -- Phase 3 增强字段 - 变化率
                    spread_change_3d FLOAT,
                    spread_change_7d FLOAT,

                    -- 交易建议
                    trade_suggestion VARCHAR(20),

                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建索引
            cursor.execute("""
                CREATE INDEX idx_ts_comm_code
                ON term_structure_history(comm_code)
            """)

            cursor.execute("""
                CREATE INDEX idx_ts_record_date
                ON term_structure_history(record_date)
            """)

            cursor.execute("""
                CREATE INDEX idx_ts_comm_date
                ON term_structure_history(comm_code, record_date)
            """)

            print("✅ 表和索引创建成功")

        # === Phase 3.4: 迁移 JSON 数据 ===
        print("\n🔄 Phase 3.4: 开始迁移 JSON 数据...")

        # 读取 JSON 文件
        json_path = Path(json_dir) / 'term_structure_data_all.json'
        if not json_path.exists():
            print(f"⚠️  警告: {json_path} 不存在,尝试 term_structure_data.json")
            json_path = Path(json_dir) / 'term_structure_data.json'

        if not json_path.exists():
            print(f"❌ 错误: JSON 数据文件不存在")
            conn.close()
            return False

        print(f"📖 读取 JSON 文件: {json_path}")
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # JSON是字典格式 {品种代码: 品种数据}
        # 获取所有品种
        if isinstance(data, dict):
            # 检查是否有date字段
            import_date = date.today().isoformat()
            if 'date' in data:
                import_date = data['date']
                varieties_dict = {k: v for k, v in data.items() if k != 'date'}
            else:
                varieties_dict = data

            varieties = list(varieties_dict.values())
        else:
            # 旧格式兼容
            varieties = data.get('varieties', [])
            import_date = data.get('date', date.today().isoformat())

        print(f"   数据日期: {import_date}")
        print(f"   品种数量: {len(varieties)}")

        # 插入数据
        inserted_count = 0
        skipped_count = 0

        for variety in varieties:
            comm_code = variety.get('variety_code', '')
            variety_name = variety.get('variety_name', '')

            # 检查是否已存在
            cursor.execute("""
                SELECT COUNT(*) FROM term_structure_history
                WHERE comm_code = ? AND record_date = ?
            """, (comm_code, import_date))

            if cursor.fetchone()[0] > 0:
                skipped_count += 1
                continue

            # 获取近月合约信息
            contracts = variety.get('contracts', [])
            if len(contracts) >= 2:
                near = contracts[0]
                far = contracts[1]

                near_contract = near.get('symbol', '')
                near_price = near.get('price', 0)
                near_volume = near.get('volume', 0)
                near_oi = near.get('open_interest', 0)

                far_contract = far.get('symbol', '')
                far_price = far.get('price', 0)

                # 计算价差
                price_spread = far_price - near_price if near_price else 0
                spread_pct = (price_spread / near_price * 100) if near_price else 0
            else:
                near_contract = far_contract = ""
                near_price = far_price = near_volume = near_oi = 0
                price_spread = spread_pct = 0

            # 判断结构类型
            market_structure = variety.get('market_structure', '')
            if '正向' in market_structure or 'Contango' in market_structure:
                structure_type = 'Contango'
            elif '反向' in market_structure or 'Backwardation' in market_structure:
                structure_type = 'Backwardation'
            else:
                structure_type = 'Neutral'

            # 插入数据
            cursor.execute("""
                INSERT INTO term_structure_history (
                    comm_code, variety_name, record_date,
                    structure_type, market_structure, structure_desc,
                    near_contract, far_contract, near_price, far_price,
                    near_volume, near_oi,
                    price_spread, spread_pct,
                    structure_score, grade, recommend,
                    trade_suggestion
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                comm_code,
                variety_name,
                import_date,
                structure_type,
                market_structure,
                variety.get('structure_desc', ''),
                near_contract,
                far_contract,
                near_price,
                far_price,
                near_volume,
                near_oi,
                price_spread,
                spread_pct,
                variety.get('structure_score', 0),
                variety.get('grade', ''),
                1 if variety.get('recommend', False) else 0,
                variety.get('trade_suggestion', '')
            ))

            inserted_count += 1

        # 提交事务
        conn.commit()

        print(f"✅ 成功导入 {inserted_count} 条记录")
        if skipped_count > 0:
            print(f"⏭️  跳过 {skipped_count} 条已存在记录")

        # 验证导入结果
        cursor.execute("SELECT COUNT(*) FROM term_structure_history")
        total_count = cursor.fetchone()[0]

        cursor.execute("""
            SELECT structure_type, COUNT(*) as count
            FROM term_structure_history
            WHERE record_date = ?
            GROUP BY structure_type
        """, (import_date,))

        print("\n📊 导入结果统计 (本次导入):")
        print("-" * 50)
        for row in cursor.fetchall():
            structure = row[0] or 'NULL'
            count = row[1]
            print(f"  {structure:20s}: {count:>4d} 条")
        print("-" * 50)
        print(f"  数据库总记录数: {total_count} 条")

        # 显示推荐品种
        cursor.execute("""
            SELECT comm_code, variety_name, structure_type, structure_score, grade
            FROM term_structure_history
            WHERE record_date = ? AND recommend = 1
            ORDER BY structure_score DESC
        """, (import_date,))

        recommended = cursor.fetchall()
        if recommended:
            print(f"\n⭐ 推荐品种 ({len(recommended)}个):")
            print("-" * 70)
            for r in recommended:
                print(f"  [{r[4]}] {r[1]:8s} ({r[0]:4s}) | {r[2]:20s} | 得分: {r[3]:.1f}")
            print("-" * 70)

        print("\n✅ 期限结构历史化迁移成功完成!")

        # 显示后续步骤
        print("\n📌 后续操作:")
        print("  1. 重启服务: cd option_tracker && python3 main.py")
        print("  2. 访问API: http://localhost:8000/api/v1/term-structure/history")
        print("  3. Phase 3.5: 实现结构转换信号识别")
        print("  4. Phase 3.6: 实现价差历史分析")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 获取路径参数
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        script_dir = Path(__file__).parent
        db_path = script_dir / 'option_tracker.db'

    if len(sys.argv) > 2:
        json_dir = sys.argv[2]
    else:
        script_dir = Path(__file__).parent
        json_dir = script_dir / 'data'

    # 执行迁移
    success = migrate_database(str(db_path), str(json_dir))

    # 返回退出码
    sys.exit(0 if success else 1)
