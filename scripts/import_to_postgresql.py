"""
PostgreSQL 数据导入脚本
从 JSON 文件导入数据到 PostgreSQL
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
from pathlib import Path
import logging
from datetime import datetime
from sqlalchemy import create_engine, text, MetaData, inspect
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def parse_datetime(value):
    """解析日期时间字符串"""
    if not value:
        return None
    try:
        # 尝试解析 ISO 格式
        return datetime.fromisoformat(value)
    except:
        return value


def import_json_to_postgresql(json_file: str, pg_connection_string: str):
    """
    从 JSON 文件导入数据到 PostgreSQL

    Args:
        json_file: JSON 数据文件路径
        pg_connection_string: PostgreSQL 连接字符串
    """
    logger.info("=" * 60)
    logger.info("开始导入数据到 PostgreSQL")
    logger.info("=" * 60)

    # 检查 JSON 文件是否存在
    if not os.path.exists(json_file):
        logger.error(f"❌ JSON 文件不存在: {json_file}")
        return False

    # 读取 JSON 数据
    logger.info(f"📖 读取数据文件: {json_file}")
    with open(json_file, 'r', encoding='utf-8') as f:
        export_data = json.load(f)

    logger.info(f"📊 发现 {len(export_data)} 个表")

    # 创建 PostgreSQL 连接
    try:
        engine = create_engine(pg_connection_string, echo=False)
        Session = sessionmaker(bind=engine)
        session = Session()

        # 测试连接
        session.execute(text("SELECT 1"))
        logger.info("✅ PostgreSQL 连接成功")

    except Exception as e:
        logger.error(f"❌ 无法连接到 PostgreSQL: {e}")
        return False

    # 获取 PostgreSQL 中的表信息
    inspector = inspect(engine)
    pg_tables = inspector.get_table_names()

    if not pg_tables:
        logger.error("❌ PostgreSQL 中没有表，请先运行数据库初始化")
        logger.info("   提示: python3 -c \"from app.models.database import init_db; init_db()\"")
        return False

    logger.info(f"📋 PostgreSQL 中有 {len(pg_tables)} 个表")

    # 导入数据
    total_imported = 0
    failed_tables = []

    try:
        for table_name, table_data in export_data.items():
            logger.info(f"\n  📋 正在导入表: {table_name}")

            # 检查表是否存在
            if table_name not in pg_tables:
                logger.warning(f"    ⚠️  表 {table_name} 在 PostgreSQL 中不存在，跳过")
                failed_tables.append(table_name)
                continue

            rows = table_data['rows']
            columns = table_data['columns']

            if not rows:
                logger.info(f"    ℹ️  表 {table_name} 没有数据，跳过")
                continue

            # 清空现有数据（可选）
            # session.execute(text(f"TRUNCATE TABLE {table_name} CASCADE"))
            # logger.info(f"    🗑️  已清空表 {table_name}")

            # 批量插入数据
            imported_count = 0
            failed_count = 0

            for row in rows:
                try:
                    # 构建插入语句
                    col_names = ', '.join([f'"{col}"' for col in columns])
                    placeholders = ', '.join([f':{col}' for col in columns])
                    sql = f'INSERT INTO "{table_name}" ({col_names}) VALUES ({placeholders})'

                    # 转换数据类型
                    row_data = {}
                    for col in columns:
                        value = row.get(col)
                        # 尝试解析日期时间
                        if isinstance(value, str) and ('T' in value or 'created_at' in col or 'updated_at' in col or 'time' in col or 'date' in col):
                            value = parse_datetime(value)
                        row_data[col] = value

                    session.execute(text(sql), row_data)
                    imported_count += 1

                except Exception as e:
                    failed_count += 1
                    logger.debug(f"    ⚠️  插入失败: {e}")

            # 提交事务
            session.commit()

            total_imported += imported_count
            logger.info(f"    ✅ 导入 {imported_count} 条记录{f' (失败 {failed_count} 条)' if failed_count > 0 else ''}")

        # 更新序列（PostgreSQL 自增 ID）
        logger.info("\n📊 更新自增序列...")
        for table_name in pg_tables:
            try:
                # 查找主键列
                pk_columns = inspector.get_pk_constraint(table_name)['constrained_columns']
                if pk_columns and len(pk_columns) == 1:
                    pk_col = pk_columns[0]

                    # 获取最大 ID
                    result = session.execute(text(f'SELECT MAX("{pk_col}") FROM "{table_name}"'))
                    max_id = result.scalar()

                    if max_id:
                        # 更新序列
                        sequence_name = f'{table_name}_{pk_col}_seq'
                        session.execute(text(f"SELECT setval('{sequence_name}', {max_id})"))
                        logger.info(f"    ✅ 更新序列 {sequence_name} -> {max_id}")

            except Exception as e:
                logger.debug(f"    ⚠️  更新序列失败 ({table_name}): {e}")

        session.commit()

        # 显示导入摘要
        logger.info("\n" + "=" * 60)
        logger.info("✅ 导入完成！")
        logger.info("=" * 60)
        logger.info(f"  📊 成功导入表数: {len(export_data) - len(failed_tables)}")
        logger.info(f"  📝 总记录数: {total_imported}")
        if failed_tables:
            logger.warning(f"  ⚠️  跳过的表: {', '.join(failed_tables)}")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
        return False

    finally:
        session.close()


if __name__ == "__main__":
    # JSON 数据文件路径
    project_root = Path(__file__).parent.parent
    json_file = project_root / "data_export.json"

    # PostgreSQL 连接字符串（从环境变量或配置读取）
    import sys
    sys.path.insert(0, str(project_root))

    # 尝试从配置读取
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

    # 执行导入
    success = import_json_to_postgresql(str(json_file), pg_connection)

    if success:
        logger.info("\n🎉 数据导入成功！")
        logger.info(f"   下一步: 运行 verify_migration.py 验证数据一致性")
    else:
        logger.error("\n❌ 数据导入失败！")
        sys.exit(1)
