"""
一键式 PostgreSQL 迁移脚本
自动执行完整的数据库迁移流程
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import shutil
from pathlib import Path
from datetime import datetime
import logging
import subprocess

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def run_command(command: str, description: str) -> bool:
    """
    执行系统命令并返回结果

    Args:
        command: 要执行的命令
        description: 命令描述

    Returns:
        bool: 执行是否成功
    """
    logger.info(f"\n🔧 {description}")
    logger.info(f"   执行命令: {command}")

    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )

        if result.stdout:
            logger.info(result.stdout)

        logger.info(f"✅ {description} - 完成")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {description} - 失败")
        if e.stderr:
            logger.error(f"错误信息: {e.stderr}")
        return False


def migrate_to_postgresql(skip_backup: bool = False, skip_init: bool = False):
    """
    一键式迁移到 PostgreSQL

    Args:
        skip_backup: 跳过备份步骤（不推荐）
        skip_init: 跳过数据库初始化步骤（如果已初始化）

    Returns:
        bool: 迁移是否成功
    """
    logger.info("=" * 80)
    logger.info("🚀 开始 PostgreSQL 数据库迁移")
    logger.info("=" * 80)

    project_root = Path(__file__).parent.parent
    sqlite_db = project_root / "option_tracker.db"
    export_json = project_root / "data_export.json"
    scripts_dir = project_root / "scripts"

    # 检查 SQLite 数据库是否存在
    if not sqlite_db.exists():
        logger.error(f"❌ SQLite 数据库不存在: {sqlite_db}")
        logger.info("   如果这是全新安装，请直接配置 PostgreSQL 并初始化数据库")
        return False

    # 检查配置
    logger.info("\n📋 检查配置...")
    try:
        from config.settings import get_settings
        settings = get_settings()
        pg_connection = settings.DATABASE_URL

        if not pg_connection.startswith('postgresql'):
            logger.error("❌ DATABASE_URL 不是 PostgreSQL 连接字符串")
            logger.info("   请在 .env 文件中配置:")
            logger.info("   DATABASE_URL=postgresql://user:password@localhost:5432/dbname")
            return False

        logger.info(f"✅ PostgreSQL 配置正确")
        logger.info(f"   目标数据库: {pg_connection.split('@')[1] if '@' in pg_connection else 'N/A'}")

    except Exception as e:
        logger.error(f"❌ 配置读取失败: {e}")
        return False

    # 步骤1: 备份 SQLite 数据库
    if not skip_backup:
        logger.info("\n" + "=" * 80)
        logger.info("步骤 1/5: 备份 SQLite 数据库")
        logger.info("=" * 80)

        backup_name = f"option_tracker.db.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_path = project_root / backup_name

        try:
            shutil.copy2(sqlite_db, backup_path)
            logger.info(f"✅ 备份成功: {backup_name}")
            logger.info(f"   文件大小: {backup_path.stat().st_size / 1024:.2f} KB")
        except Exception as e:
            logger.error(f"❌ 备份失败: {e}")
            return False
    else:
        logger.info("\n⚠️  跳过备份步骤（不推荐）")

    # 步骤2: 导出 SQLite 数据
    logger.info("\n" + "=" * 80)
    logger.info("步骤 2/5: 导出 SQLite 数据")
    logger.info("=" * 80)

    export_script = scripts_dir / "export_sqlite_data.py"
    if not run_command(f"python3 {export_script}", "导出 SQLite 数据"):
        logger.error("❌ 数据导出失败，迁移中止")
        return False

    # 验证导出文件
    if not export_json.exists():
        logger.error(f"❌ 导出文件不存在: {export_json}")
        return False

    logger.info(f"✅ 导出文件: {export_json}")
    logger.info(f"   文件大小: {export_json.stat().st_size / 1024:.2f} KB")

    # 步骤3: 初始化 PostgreSQL 表结构
    if not skip_init:
        logger.info("\n" + "=" * 80)
        logger.info("步骤 3/5: 初始化 PostgreSQL 表结构")
        logger.info("=" * 80)

        init_command = 'python3 -c "from app.models.database import init_db; init_db()"'
        if not run_command(init_command, "初始化数据库表结构"):
            logger.warning("⚠️  数据库初始化失败，可能表已存在")
            logger.info("   如果表已存在，这是正常的，继续迁移...")
    else:
        logger.info("\n⚠️  跳过数据库初始化步骤")

    # 步骤4: 导入数据到 PostgreSQL
    logger.info("\n" + "=" * 80)
    logger.info("步骤 4/5: 导入数据到 PostgreSQL")
    logger.info("=" * 80)

    import_script = scripts_dir / "import_to_postgresql.py"
    if not run_command(f"python3 {import_script}", "导入数据到 PostgreSQL"):
        logger.error("❌ 数据导入失败，迁移中止")
        logger.info("\n📝 回滚建议:")
        logger.info("   1. 恢复 .env 配置为 SQLite")
        logger.info(f"   2. 如需重试，请检查 PostgreSQL 日志")
        return False

    # 步骤5: 验证数据一致性
    logger.info("\n" + "=" * 80)
    logger.info("步骤 5/5: 验证数据一致性")
    logger.info("=" * 80)

    verify_script = scripts_dir / "verify_migration.py"
    verification_success = run_command(f"python3 {verify_script}", "验证数据一致性")

    # 生成最终报告
    logger.info("\n" + "=" * 80)
    logger.info("📊 迁移完成报告")
    logger.info("=" * 80)

    report_content = f"""
迁移时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

执行步骤:
  ✅ 1. 备份 SQLite 数据库 {'(跳过)' if skip_backup else ''}
  ✅ 2. 导出 SQLite 数据
  ✅ 3. 初始化 PostgreSQL 表结构 {'(跳过)' if skip_init else ''}
  ✅ 4. 导入数据到 PostgreSQL
  {'✅' if verification_success else '❌'} 5. 验证数据一致性

迁移文件:
  - 备份文件: {backup_name if not skip_backup else 'N/A'}
  - 导出文件: data_export.json

下一步操作:
"""

    if verification_success:
        report_content += """
  ✅ 数据验证通过！

  1. 测试应用功能
     python3 main.py
     curl http://localhost:8000/api/v1/summary/overview

  2. 确认无误后，可以删除导出文件和备份
     rm data_export.json
     rm option_tracker.db.backup_*

  3. （可选）保留 SQLite 作为额外备份
     mv option_tracker.db option_tracker.db.old
"""
    else:
        report_content += """
  ❌ 数据验证失败！

  1. 查看验证报告
     cat migration_report_*.txt

  2. 如需回滚到 SQLite:
     - 编辑 .env 文件
       DATABASE_URL=sqlite:///./option_tracker.db
     - 重启应用
       python3 main.py

  3. 如需重新迁移:
     - 检查 PostgreSQL 日志
     - 清空 PostgreSQL 表
     - 重新运行迁移脚本
"""

    logger.info(report_content)

    # 保存报告到文件
    report_file = project_root / f"migration_final_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("PostgreSQL 数据库迁移报告\n")
        f.write("=" * 80 + "\n")
        f.write(report_content)

    logger.info(f"\n📄 完整报告已保存至: {report_file}")

    # 返回最终结果
    logger.info("\n" + "=" * 80)
    if verification_success:
        logger.info("🎉 迁移成功！数据已完整迁移到 PostgreSQL")
        logger.info("=" * 80)
        return True
    else:
        logger.error("⚠️  迁移完成，但数据验证失败，请检查验证报告")
        logger.info("=" * 80)
        return False


def show_pre_migration_checklist():
    """显示迁移前检查清单"""
    logger.info("=" * 80)
    logger.info("📋 迁移前检查清单")
    logger.info("=" * 80)
    logger.info("""
请确认以下事项:

□ PostgreSQL 已安装并运行
  brew services list | grep postgresql

□ 数据库和用户已创建
  psql postgres -c "\\l" | grep option_tracker

□ .env 文件已配置 PostgreSQL 连接
  DATABASE_URL=postgresql://user:password@localhost:5432/dbname

□ psycopg2 驱动已安装
  pip3 list | grep psycopg2

□ 应用已停止运行
  pkill -f "python3 main.py"

□ 有足够的磁盘空间（建议至少 1GB）
  df -h .

完成所有检查后，继续迁移...
""")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='一键式 PostgreSQL 数据库迁移')
    parser.add_argument('--skip-backup', action='store_true', help='跳过备份步骤（不推荐）')
    parser.add_argument('--skip-init', action='store_true', help='跳过数据库初始化（如果已初始化）')
    parser.add_argument('--force', action='store_true', help='跳过检查清单，直接开始迁移')

    args = parser.parse_args()

    # 显示检查清单
    if not args.force:
        show_pre_migration_checklist()

        response = input("\n是否继续迁移？(yes/no): ").strip().lower()
        if response not in ['yes', 'y', '是']:
            logger.info("❌ 用户取消迁移")
            sys.exit(0)

    # 执行迁移
    logger.info("\n🚀 开始迁移...")

    success = migrate_to_postgresql(
        skip_backup=args.skip_backup,
        skip_init=args.skip_init
    )

    if success:
        logger.info("\n✅ 迁移成功完成！")
        logger.info("   请测试应用功能，确认无误后可删除备份文件")
        sys.exit(0)
    else:
        logger.error("\n❌ 迁移失败！")
        logger.info("   请查看日志，解决问题后重试")
        sys.exit(1)
