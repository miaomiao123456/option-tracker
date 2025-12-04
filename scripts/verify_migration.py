"""
数据迁移验证脚本
对比 SQLite 和 PostgreSQL 数据库的数据一致性
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from pathlib import Path
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def verify_migration(sqlite_db_path: str, pg_connection_string: str):
    """
    验证数据迁移的完整性和一致性

    Args:
        sqlite_db_path: SQLite 数据库文件路径
        pg_connection_string: PostgreSQL 连接字符串

    Returns:
        bool: 验证是否通过
    """
    logger.info("=" * 60)
    logger.info("开始验证数据迁移")
    logger.info("=" * 60)

    # 检查 SQLite 数据库是否存在
    if not os.path.exists(sqlite_db_path):
        logger.error(f"❌ SQLite 数据库文件不存在: {sqlite_db_path}")
        return False

    try:
        # 创建 SQLite 连接
        sqlite_engine = create_engine(f'sqlite:///{sqlite_db_path}', echo=False)
        SqliteSession = sessionmaker(bind=sqlite_engine)
        sqlite_session = SqliteSession()

        # 创建 PostgreSQL 连接
        pg_engine = create_engine(pg_connection_string, echo=False)
        PgSession = sessionmaker(bind=pg_engine)
        pg_session = PgSession()

        logger.info("✅ 数据库连接成功")

    except Exception as e:
        logger.error(f"❌ 数据库连接失败: {e}")
        return False

    # 获取表列表
    sqlite_inspector = inspect(sqlite_engine)
    pg_inspector = inspect(pg_engine)

    sqlite_tables = set(sqlite_inspector.get_table_names())
    pg_tables = set(pg_inspector.get_table_names())

    logger.info(f"\n📊 SQLite 表数: {len(sqlite_tables)}")
    logger.info(f"📊 PostgreSQL 表数: {len(pg_tables)}")

    # 检查缺失的表
    missing_in_pg = sqlite_tables - pg_tables
    extra_in_pg = pg_tables - sqlite_tables

    if missing_in_pg:
        logger.warning(f"\n⚠️  PostgreSQL 中缺失的表: {', '.join(missing_in_pg)}")

    if extra_in_pg:
        logger.info(f"\nℹ️  PostgreSQL 中额外的表: {', '.join(extra_in_pg)}")

    # 对比每个表的记录数
    logger.info("\n" + "=" * 60)
    logger.info("对比表记录数")
    logger.info("=" * 60)

    all_match = True
    total_sqlite_records = 0
    total_pg_records = 0
    verification_results = []

    for table_name in sorted(sqlite_tables):
        if table_name not in pg_tables:
            logger.warning(f"\n❌ 表 {table_name} 在 PostgreSQL 中不存在，跳过")
            verification_results.append({
                'table': table_name,
                'status': 'missing',
                'sqlite_count': None,
                'pg_count': None
            })
            all_match = False
            continue

        try:
            # 查询 SQLite 记录数
            sqlite_count = sqlite_session.execute(
                text(f'SELECT COUNT(*) FROM "{table_name}"')
            ).scalar()

            # 查询 PostgreSQL 记录数
            pg_count = pg_session.execute(
                text(f'SELECT COUNT(*) FROM "{table_name}"')
            ).scalar()

            total_sqlite_records += sqlite_count
            total_pg_records += pg_count

            # 对比记录数
            match = sqlite_count == pg_count
            status = "✅" if match else "❌"

            logger.info(f"\n  📋 表: {table_name}")
            logger.info(f"    SQLite:     {sqlite_count:>6} 条")
            logger.info(f"    PostgreSQL: {pg_count:>6} 条")
            logger.info(f"    状态: {status} {'一致' if match else '不一致'}")

            verification_results.append({
                'table': table_name,
                'status': 'match' if match else 'mismatch',
                'sqlite_count': sqlite_count,
                'pg_count': pg_count,
                'diff': abs(sqlite_count - pg_count) if not match else 0
            })

            if not match:
                all_match = False
                logger.warning(f"    ⚠️  差异: {abs(sqlite_count - pg_count)} 条记录")

        except Exception as e:
            logger.error(f"\n❌ 验证表 {table_name} 失败: {e}")
            verification_results.append({
                'table': table_name,
                'status': 'error',
                'sqlite_count': None,
                'pg_count': None,
                'error': str(e)
            })
            all_match = False

    # 抽样验证数据内容（可选）
    logger.info("\n" + "=" * 60)
    logger.info("抽样验证数据内容")
    logger.info("=" * 60)

    sample_tables = ['data_sources', 'data_collection_logs']

    for table_name in sample_tables:
        if table_name not in sqlite_tables or table_name not in pg_tables:
            continue

        try:
            # 获取表的列
            columns = [col['name'] for col in sqlite_inspector.get_columns(table_name)]

            # 从 SQLite 获取前5条记录
            sqlite_sample = sqlite_session.execute(
                text(f'SELECT * FROM "{table_name}" LIMIT 5')
            ).fetchall()

            # 从 PostgreSQL 获取前5条记录
            pg_sample = pg_session.execute(
                text(f'SELECT * FROM "{table_name}" LIMIT 5')
            ).fetchall()

            logger.info(f"\n  📋 表 {table_name} 抽样对比:")
            logger.info(f"    样本数: {min(len(sqlite_sample), len(pg_sample))}")

            # 简单对比第一条记录（如果存在）
            if sqlite_sample and pg_sample:
                logger.info(f"    ✅ 数据样本存在")
            elif not sqlite_sample and not pg_sample:
                logger.info(f"    ℹ️  表为空")
            else:
                logger.warning(f"    ⚠️  样本数量不一致")
                all_match = False

        except Exception as e:
            logger.warning(f"  ⚠️  抽样验证失败: {e}")

    # 生成验证报告
    logger.info("\n" + "=" * 60)
    logger.info("验证报告")
    logger.info("=" * 60)

    matched_tables = sum(1 for r in verification_results if r['status'] == 'match')
    mismatched_tables = sum(1 for r in verification_results if r['status'] == 'mismatch')
    missing_tables = sum(1 for r in verification_results if r['status'] == 'missing')
    error_tables = sum(1 for r in verification_results if r['status'] == 'error')

    logger.info(f"\n  📊 总表数: {len(verification_results)}")
    logger.info(f"  ✅ 一致的表: {matched_tables}")
    logger.info(f"  ❌ 不一致的表: {mismatched_tables}")
    logger.info(f"  ⚠️  缺失的表: {missing_tables}")
    logger.info(f"  ⚠️  验证错误: {error_tables}")

    logger.info(f"\n  📝 SQLite 总记录数: {total_sqlite_records}")
    logger.info(f"  📝 PostgreSQL 总记录数: {total_pg_records}")

    if total_sqlite_records == total_pg_records:
        logger.info(f"  ✅ 总记录数一致")
    else:
        logger.warning(f"  ❌ 总记录数不一致，差异: {abs(total_sqlite_records - total_pg_records)}")

    # 保存详细报告到文件
    report_file = Path(__file__).parent.parent / f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("数据迁移验证报告\n")
        f.write("=" * 60 + "\n")
        f.write(f"生成时间: {datetime.now()}\n")
        f.write(f"SQLite 数据库: {sqlite_db_path}\n")
        f.write(f"PostgreSQL: {pg_connection_string.split('@')[1] if '@' in pg_connection_string else 'N/A'}\n")
        f.write("\n" + "=" * 60 + "\n")
        f.write("详细结果\n")
        f.write("=" * 60 + "\n\n")

        for result in verification_results:
            f.write(f"表名: {result['table']}\n")
            f.write(f"  状态: {result['status']}\n")
            if result.get('sqlite_count') is not None:
                f.write(f"  SQLite 记录数: {result['sqlite_count']}\n")
                f.write(f"  PostgreSQL 记录数: {result['pg_count']}\n")
                if result['status'] == 'mismatch':
                    f.write(f"  差异: {result['diff']} 条\n")
            if result.get('error'):
                f.write(f"  错误: {result['error']}\n")
            f.write("\n")

        f.write("=" * 60 + "\n")
        f.write("汇总统计\n")
        f.write("=" * 60 + "\n")
        f.write(f"总表数: {len(verification_results)}\n")
        f.write(f"一致的表: {matched_tables}\n")
        f.write(f"不一致的表: {mismatched_tables}\n")
        f.write(f"缺失的表: {missing_tables}\n")
        f.write(f"验证错误: {error_tables}\n")
        f.write(f"\nSQLite 总记录数: {total_sqlite_records}\n")
        f.write(f"PostgreSQL 总记录数: {total_pg_records}\n")
        f.write(f"差异: {abs(total_sqlite_records - total_pg_records)}\n")

    logger.info(f"\n📄 详细报告已保存至: {report_file}")

    # 关闭连接
    sqlite_session.close()
    pg_session.close()

    # 最终结果
    logger.info("\n" + "=" * 60)
    if all_match and matched_tables == len(verification_results):
        logger.info("✅ 验证通过！数据迁移成功！")
        logger.info("=" * 60)
        return True
    else:
        logger.error("❌ 验证失败！存在数据不一致")
        logger.info("=" * 60)
        logger.info("\n建议:")
        logger.info("  1. 检查导入日志中的错误信息")
        logger.info("  2. 对比不一致的表，查找原因")
        logger.info("  3. 必要时重新运行导入脚本")
        return False


if __name__ == "__main__":
    # SQLite 数据库路径
    project_root = Path(__file__).parent.parent
    sqlite_db = project_root / "option_tracker.db"

    # PostgreSQL 连接字符串（从配置读取）
    try:
        from config.settings import get_settings
        settings = get_settings()
        pg_connection = settings.DATABASE_URL

        # 检查是否为 PostgreSQL
        if not pg_connection.startswith('postgresql'):
            logger.error("❌ 配置中的 DATABASE_URL 不是 PostgreSQL 连接字符串")
            logger.info("   请在 .env 文件中设置:")
            logger.info("   DATABASE_URL=postgresql://user:password@localhost:5432/dbname")
            sys.exit(1)

    except Exception as e:
        logger.error(f"❌ 无法读取配置: {e}")
        logger.info("   请确保 .env 文件存在并配置了 DATABASE_URL")
        sys.exit(1)

    # 执行验证
    success = verify_migration(str(sqlite_db), pg_connection)

    if success:
        logger.info("\n🎉 数据验证成功！")
        logger.info("   ✅ SQLite 和 PostgreSQL 数据一致")
        logger.info("   ✅ 可以安全使用 PostgreSQL 数据库")
    else:
        logger.error("\n❌ 数据验证失败！")
        logger.info("   ⚠️  请检查验证报告，解决数据不一致问题")
        sys.exit(1)
