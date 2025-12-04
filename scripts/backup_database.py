"""
多级数据库备份脚本
支持小时级、天级、周级备份，自动清理旧备份
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import shutil
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import logging
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DatabaseBackup:
    """数据库备份管理器"""

    def __init__(self, project_root: Optional[Path] = None):
        """
        初始化备份管理器

        Args:
            project_root: 项目根目录路径
        """
        self.project_root = project_root or Path(__file__).parent.parent
        self.backup_dir = self.project_root / "backups"

        # 创建备份目录结构
        self.hourly_dir = self.backup_dir / "hourly"
        self.daily_dir = self.backup_dir / "daily"
        self.weekly_dir = self.backup_dir / "weekly"

        for dir_path in [self.hourly_dir, self.daily_dir, self.weekly_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # 读取配置
        try:
            from config.settings import get_settings
            self.settings = get_settings()
            self.db_url = self.settings.DATABASE_URL
        except Exception as e:
            logger.error(f"❌ 无法读取配置: {e}")
            self.db_url = None

    def is_postgresql(self) -> bool:
        """判断当前是否使用 PostgreSQL"""
        return self.db_url and self.db_url.startswith('postgresql')

    def backup_sqlite(self, backup_path: Path) -> bool:
        """
        备份 SQLite 数据库

        Args:
            backup_path: 备份文件路径

        Returns:
            bool: 备份是否成功
        """
        sqlite_db = self.project_root / "option_tracker.db"

        if not sqlite_db.exists():
            logger.error(f"❌ SQLite 数据库不存在: {sqlite_db}")
            return False

        try:
            # 使用 .backup 命令进行热备份
            import sqlite3
            conn = sqlite3.connect(str(sqlite_db))
            backup_conn = sqlite3.connect(str(backup_path))

            with backup_conn:
                conn.backup(backup_conn)

            conn.close()
            backup_conn.close()

            file_size = backup_path.stat().st_size / 1024
            logger.info(f"✅ SQLite 备份成功: {backup_path.name} ({file_size:.2f} KB)")
            return True

        except Exception as e:
            logger.error(f"❌ SQLite 备份失败: {e}")
            return False

    def backup_postgresql(self, backup_path: Path) -> bool:
        """
        备份 PostgreSQL 数据库

        Args:
            backup_path: 备份文件路径

        Returns:
            bool: 备份是否成功
        """
        if not self.db_url:
            logger.error("❌ 无法读取 DATABASE_URL")
            return False

        try:
            # 解析连接字符串
            # postgresql://user:password@host:port/dbname
            from urllib.parse import urlparse
            parsed = urlparse(self.db_url)

            username = parsed.username
            password = parsed.password
            hostname = parsed.hostname
            port = parsed.port or 5432
            database = parsed.path.lstrip('/')

            # 设置环境变量（避免密码提示）
            env = os.environ.copy()
            env['PGPASSWORD'] = password

            # 使用 pg_dump 备份
            cmd = [
                'pg_dump',
                '-h', hostname,
                '-p', str(port),
                '-U', username,
                '-F', 'c',  # custom format
                '-f', str(backup_path),
                database
            ]

            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                check=True
            )

            file_size = backup_path.stat().st_size / 1024
            logger.info(f"✅ PostgreSQL 备份成功: {backup_path.name} ({file_size:.2f} KB)")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ PostgreSQL 备份失败: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"❌ PostgreSQL 备份失败: {e}")
            return False

    def create_backup(self, backup_type: str = "hourly") -> bool:
        """
        创建备份

        Args:
            backup_type: 备份类型 (hourly/daily/weekly)

        Returns:
            bool: 备份是否成功
        """
        logger.info("=" * 60)
        logger.info(f"开始 {backup_type} 备份")
        logger.info("=" * 60)

        # 确定备份目录
        if backup_type == "hourly":
            target_dir = self.hourly_dir
        elif backup_type == "daily":
            target_dir = self.daily_dir
        elif backup_type == "weekly":
            target_dir = self.weekly_dir
        else:
            logger.error(f"❌ 未知的备份类型: {backup_type}")
            return False

        # 生成备份文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if self.is_postgresql():
            backup_filename = f"pg_backup_{backup_type}_{timestamp}.dump"
            backup_path = target_dir / backup_filename
            success = self.backup_postgresql(backup_path)
        else:
            backup_filename = f"sqlite_backup_{backup_type}_{timestamp}.db"
            backup_path = target_dir / backup_filename
            success = self.backup_sqlite(backup_path)

        if success:
            # 清理旧备份
            self.cleanup_old_backups(backup_type)

        return success

    def cleanup_old_backups(self, backup_type: str):
        """
        清理旧备份文件

        Args:
            backup_type: 备份类型 (hourly/daily/weekly)
        """
        # 确定保留策略
        if backup_type == "hourly":
            target_dir = self.hourly_dir
            keep_count = 24  # 保留最近 24 小时
            max_age_days = 7  # 超过 7 天的直接删除
        elif backup_type == "daily":
            target_dir = self.daily_dir
            keep_count = 30  # 保留最近 30 天
            max_age_days = 90  # 超过 90 天的直接删除
        elif backup_type == "weekly":
            target_dir = self.weekly_dir
            keep_count = 12  # 保留最近 12 周
            max_age_days = 365  # 超过 1 年的直接删除
        else:
            return

        try:
            # 获取所有备份文件
            if self.is_postgresql():
                pattern = f"pg_backup_{backup_type}_*.dump"
            else:
                pattern = f"sqlite_backup_{backup_type}_*.db"

            backup_files = sorted(
                target_dir.glob(pattern),
                key=lambda f: f.stat().st_mtime,
                reverse=True
            )

            # 删除超过最大年龄的文件
            cutoff_time = datetime.now() - timedelta(days=max_age_days)
            deleted_old = 0

            for backup_file in backup_files:
                file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                if file_time < cutoff_time:
                    backup_file.unlink()
                    deleted_old += 1

            # 只保留最新的 N 个文件
            if len(backup_files) > keep_count:
                for backup_file in backup_files[keep_count:]:
                    if backup_file.exists():  # 可能已经被上面删除
                        backup_file.unlink()

            deleted_excess = max(0, len(backup_files) - keep_count - deleted_old)

            if deleted_old > 0 or deleted_excess > 0:
                logger.info(f"🗑️  清理旧备份: 删除 {deleted_old + deleted_excess} 个文件")
                logger.info(f"   保留最新 {min(keep_count, len(backup_files))} 个备份")

        except Exception as e:
            logger.warning(f"⚠️  清理旧备份失败: {e}")

    def list_backups(self):
        """列出所有备份文件"""
        logger.info("=" * 60)
        logger.info("备份文件列表")
        logger.info("=" * 60)

        for backup_type, target_dir in [
            ("hourly", self.hourly_dir),
            ("daily", self.daily_dir),
            ("weekly", self.weekly_dir)
        ]:
            backup_files = sorted(
                target_dir.glob("*"),
                key=lambda f: f.stat().st_mtime,
                reverse=True
            )

            logger.info(f"\n📁 {backup_type.capitalize()} 备份 ({len(backup_files)} 个):")

            if not backup_files:
                logger.info("   (无备份文件)")
                continue

            for backup_file in backup_files[:5]:  # 只显示最新 5 个
                file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                file_size = backup_file.stat().st_size / 1024
                logger.info(f"   - {backup_file.name}")
                logger.info(f"     时间: {file_time.strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(f"     大小: {file_size:.2f} KB")

            if len(backup_files) > 5:
                logger.info(f"   ... 还有 {len(backup_files) - 5} 个备份")

    def restore_backup(self, backup_file: Path) -> bool:
        """
        恢复备份

        Args:
            backup_file: 备份文件路径

        Returns:
            bool: 恢复是否成功
        """
        logger.info("=" * 60)
        logger.info(f"开始恢复备份: {backup_file.name}")
        logger.info("=" * 60)

        if not backup_file.exists():
            logger.error(f"❌ 备份文件不存在: {backup_file}")
            return False

        # 根据文件扩展名判断备份类型
        if backup_file.suffix == '.db':
            return self._restore_sqlite(backup_file)
        elif backup_file.suffix == '.dump':
            return self._restore_postgresql(backup_file)
        else:
            logger.error(f"❌ 未知的备份文件类型: {backup_file.suffix}")
            return False

    def _restore_sqlite(self, backup_file: Path) -> bool:
        """恢复 SQLite 备份"""
        sqlite_db = self.project_root / "option_tracker.db"

        try:
            # 备份当前数据库
            if sqlite_db.exists():
                current_backup = self.project_root / f"option_tracker.db.before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                shutil.copy2(sqlite_db, current_backup)
                logger.info(f"✅ 当前数据库已备份至: {current_backup.name}")

            # 恢复备份
            shutil.copy2(backup_file, sqlite_db)
            logger.info(f"✅ SQLite 数据库恢复成功")
            return True

        except Exception as e:
            logger.error(f"❌ SQLite 恢复失败: {e}")
            return False

    def _restore_postgresql(self, backup_file: Path) -> bool:
        """恢复 PostgreSQL 备份"""
        if not self.db_url:
            logger.error("❌ 无法读取 DATABASE_URL")
            return False

        try:
            from urllib.parse import urlparse
            parsed = urlparse(self.db_url)

            username = parsed.username
            password = parsed.password
            hostname = parsed.hostname
            port = parsed.port or 5432
            database = parsed.path.lstrip('/')

            # 设置环境变量
            env = os.environ.copy()
            env['PGPASSWORD'] = password

            # 使用 pg_restore 恢复
            cmd = [
                'pg_restore',
                '-h', hostname,
                '-p', str(port),
                '-U', username,
                '-d', database,
                '-c',  # 清空现有数据
                str(backup_file)
            ]

            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                check=True
            )

            logger.info(f"✅ PostgreSQL 数据库恢复成功")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ PostgreSQL 恢复失败: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"❌ PostgreSQL 恢复失败: {e}")
            return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='数据库备份管理')
    parser.add_argument('action', choices=['backup', 'list', 'restore'],
                        help='操作类型: backup(创建备份)/list(列出备份)/restore(恢复备份)')
    parser.add_argument('--type', choices=['hourly', 'daily', 'weekly'],
                        default='daily', help='备份类型（仅用于 backup）')
    parser.add_argument('--file', type=str, help='备份文件路径（仅用于 restore）')

    args = parser.parse_args()

    backup_manager = DatabaseBackup()

    if args.action == 'backup':
        success = backup_manager.create_backup(args.type)
        if success:
            logger.info(f"\n✅ {args.type} 备份创建成功")
            sys.exit(0)
        else:
            logger.error(f"\n❌ {args.type} 备份创建失败")
            sys.exit(1)

    elif args.action == 'list':
        backup_manager.list_backups()

    elif args.action == 'restore':
        if not args.file:
            logger.error("❌ 请使用 --file 指定要恢复的备份文件")
            sys.exit(1)

        backup_file = Path(args.file)
        success = backup_manager.restore_backup(backup_file)

        if success:
            logger.info("\n✅ 数据库恢复成功")
            sys.exit(0)
        else:
            logger.error("\n❌ 数据库恢复失败")
            sys.exit(1)
