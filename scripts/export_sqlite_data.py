"""
SQLite 数据导出脚本
将 SQLite 数据库导出为 JSON 格式
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine, MetaData, inspect
from sqlalchemy.orm import sessionmaker
import json
from datetime import datetime, date
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def serialize_value(value):
    """序列化特殊类型的值"""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    elif isinstance(value, bytes):
        return value.decode('utf-8', errors='ignore')
    return value


def export_sqlite_to_json(sqlite_db_path: str, output_file: str):
    """
    导出 SQLite 数据库到 JSON 文件

    Args:
        sqlite_db_path: SQLite 数据库文件路径
        output_file: 输出 JSON 文件路径
    """
    logger.info("=" * 60)
    logger.info("开始导出 SQLite 数据")
    logger.info("=" * 60)

    # 检查数据库文件是否存在
    if not os.path.exists(sqlite_db_path):
        logger.error(f"❌ SQLite 数据库文件不存在: {sqlite_db_path}")
        return False

    # 创建数据库连接
    engine = create_engine(f'sqlite:///{sqlite_db_path}', echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

    # 获取所有表名
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    logger.info(f"📊 发现 {len(tables)} 个表")

    # 存储所有表的数据
    export_data = {}
    total_records = 0

    try:
        for table_name in tables:
            logger.info(f"  📋 正在导出表: {table_name}")

            # 获取表的所有列
            columns = [col['name'] for col in inspector.get_columns(table_name)]

            # 查询所有数据
            result = session.execute(f"SELECT * FROM {table_name}")
            rows = result.fetchall()

            # 转换为字典列表
            table_data = []
            for row in rows:
                row_dict = {}
                for i, col_name in enumerate(columns):
                    row_dict[col_name] = serialize_value(row[i])
                table_data.append(row_dict)

            export_data[table_name] = {
                'columns': columns,
                'rows': table_data,
                'count': len(table_data)
            }

            total_records += len(table_data)
            logger.info(f"    ✅ 导出 {len(table_data)} 条记录")

        # 写入 JSON 文件
        logger.info(f"\n💾 正在写入文件: {output_file}")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        # 显示导出摘要
        logger.info("\n" + "=" * 60)
        logger.info("✅ 导出完成！")
        logger.info("=" * 60)
        logger.info(f"  📊 总表数: {len(tables)}")
        logger.info(f"  📝 总记录数: {total_records}")
        logger.info(f"  💾 文件大小: {os.path.getsize(output_file) / 1024:.2f} KB")
        logger.info(f"  📁 输出文件: {output_file}")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"❌ 导出失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        session.close()


if __name__ == "__main__":
    # SQLite 数据库路径
    project_root = Path(__file__).parent.parent
    sqlite_db = project_root / "option_tracker.db"

    # 输出 JSON 文件路径
    output_json = project_root / "data_export.json"

    # 执行导出
    success = export_sqlite_to_json(str(sqlite_db), str(output_json))

    if success:
        logger.info("\n🎉 数据导出成功！")
        logger.info(f"   下一步: 运行 import_to_postgresql.py 导入数据到 PostgreSQL")
    else:
        logger.error("\n❌ 数据导出失败！")
        sys.exit(1)
