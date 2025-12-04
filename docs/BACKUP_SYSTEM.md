# 数据库备份系统配置指南

## 📋 概述

OptionAlpha 配置了多级自动备份系统，确保数据安全：
- **小时级备份**: 每小时一次，保留最近 24 个
- **天级备份**: 每天凌晨 3:00，保留最近 30 天
- **周级备份**: 每周日凌晨 3:00，保留最近 12 周

## 🔧 备份系统架构

### 1. 备份脚本

位置: `scripts/backup_database.py`

支持功能:
- ✅ SQLite 热备份
- ✅ PostgreSQL pg_dump 备份
- ✅ 自动清理旧备份
- ✅ 手动恢复功能

### 2. 自动调度

备份任务已集成到 APScheduler 中，随应用自动启动。

配置位置: `app/scheduler.py`

## 📁 备份目录结构

```
option_tracker/
└── backups/
    ├── hourly/          # 小时级备份
    │   ├── sqlite_backup_hourly_20251201_100000.db
    │   └── pg_backup_hourly_20251201_110000.dump
    ├── daily/           # 天级备份
    │   ├── sqlite_backup_daily_20251201_030000.db
    │   └── pg_backup_daily_20251201_030000.dump
    └── weekly/          # 周级备份
        ├── sqlite_backup_weekly_20251124_030000.db
        └── pg_backup_weekly_20251124_030000.dump
```

## 🚀 使用方法

### 手动创建备份

```bash
# 创建小时级备份
python3 scripts/backup_database.py backup --type hourly

# 创建天级备份
python3 scripts/backup_database.py backup --type daily

# 创建周级备份
python3 scripts/backup_database.py backup --type weekly
```

### 列出所有备份

```bash
python3 scripts/backup_database.py list
```

输出示例:
```
📁 Hourly 备份 (24 个):
  - sqlite_backup_hourly_20251201_140000.db
    时间: 2025-12-01 14:00:00
    大小: 2048.50 KB
  ...

📁 Daily 备份 (7 个):
  - sqlite_backup_daily_20251201_030000.db
    时间: 2025-12-01 03:00:00
    大小: 2048.50 KB
  ...
```

### 恢复备份

```bash
# 恢复指定的备份文件
python3 scripts/backup_database.py restore --file backups/daily/sqlite_backup_daily_20251201_030000.db
```

**注意**:
- 恢复前会自动备份当前数据库
- SQLite 备份会直接覆盖现有数据库
- PostgreSQL 备份会清空现有数据后恢复

## ⏰ 自动备份时间表

| 备份类型 | 执行时间 | 保留策略 | 最大保留时间 |
|---------|---------|---------|-------------|
| 小时级 | 每小时一次 | 保留 24 个 | 7 天 |
| 天级 | 每天 03:00 | 保留 30 个 | 90 天 |
| 周级 | 每周日 03:00 | 保留 12 个 | 365 天 |

## 📊 备份文件命名规则

### SQLite 备份
```
sqlite_backup_{类型}_{时间戳}.db
例如: sqlite_backup_daily_20251201_030000.db
```

### PostgreSQL 备份
```
pg_backup_{类型}_{时间戳}.dump
例如: pg_backup_daily_20251201_030000.dump
```

## 🔍 监控备份状态

### 查看定时任务

```bash
# 查看所有定时任务
curl http://localhost:8000/api/v1/scheduler/status
```

返回示例:
```json
{
  "running": true,
  "job_count": 9,
  "jobs": [
    {
      "id": "backup_hourly",
      "name": "数据库备份-小时级",
      "next_run": "2025-12-01 15:00:00"
    },
    {
      "id": "backup_daily",
      "name": "数据库备份-天级-03:00",
      "next_run": "2025-12-02 03:00:00"
    }
  ]
}
```

### 查看备份日志

```bash
# 查看最近的备份日志
tail -f logs/app.log | grep "备份"
```

## 💾 存储空间管理

### 估算存储需求

假设单个数据库备份大小为 **2 MB**:

| 备份类型 | 数量 | 单个大小 | 总空间 |
|---------|-----|---------|--------|
| 小时级 | 24 | 2 MB | 48 MB |
| 天级 | 30 | 2 MB | 60 MB |
| 周级 | 12 | 2 MB | 24 MB |
| **总计** | **66** | **2 MB** | **132 MB** |

### 清理备份空间

备份系统会自动清理旧备份，无需手动干预。

如需手动清理:
```bash
# 删除小时级备份（保留最新5个）
cd backups/hourly
ls -t | tail -n +6 | xargs rm -f

# 删除所有超过30天的备份
find backups/ -name "*.db" -mtime +30 -delete
find backups/ -name "*.dump" -mtime +30 -delete
```

## 🔧 高级配置

### 修改保留策略

编辑 `scripts/backup_database.py`:

```python
# 修改保留数量
if backup_type == "hourly":
    keep_count = 48  # 改为保留 48 小时
    max_age_days = 7
elif backup_type == "daily":
    keep_count = 60  # 改为保留 60 天
    max_age_days = 180
```

### 修改备份时间

编辑 `app/scheduler.py`:

```python
# 修改天级备份时间为凌晨2点
scheduler.add_job(
    lambda: run_backup('daily'),
    CronTrigger(hour=2, minute=0),  # 从3点改为2点
    id='backup_daily',
    name='数据库备份-天级-02:00',
    replace_existing=True
)
```

### 禁用某个级别的备份

编辑 `app/scheduler.py`，注释掉相应的 `scheduler.add_job`:

```python
# 禁用小时级备份
# scheduler.add_job(
#     lambda: run_backup('hourly'),
#     IntervalTrigger(hours=1),
#     id='backup_hourly',
#     name='数据库备份-小时级',
#     replace_existing=True
# )
```

## 🚨 故障恢复流程

### 场景1: 数据损坏需要恢复

1. **停止应用**
   ```bash
   pkill -f "python3 main.py"
   ```

2. **选择备份文件**
   ```bash
   python3 scripts/backup_database.py list
   ```

3. **执行恢复**
   ```bash
   python3 scripts/backup_database.py restore --file backups/daily/sqlite_backup_daily_20251201_030000.db
   ```

4. **重启应用**
   ```bash
   python3 main.py
   ```

### 场景2: 误删除数据

1. **确认误删时间点**
   - 如果是1小时内: 使用小时级备份
   - 如果是今天: 使用今天的天级备份
   - 如果更早: 使用周级备份

2. **按场景1流程恢复**

### 场景3: 迁移到新服务器

1. **在新服务器上安装应用**

2. **复制最新备份文件**
   ```bash
   scp backups/daily/sqlite_backup_daily_20251201_030000.db user@new-server:/path/to/option_tracker/
   ```

3. **在新服务器上恢复**
   ```bash
   python3 scripts/backup_database.py restore --file sqlite_backup_daily_20251201_030000.db
   ```

## 📝 最佳实践

### 1. 定期验证备份

每月至少验证一次备份可用性:
```bash
# 创建测试数据库
cp backups/daily/latest_backup.db test_restore.db

# 尝试连接
sqlite3 test_restore.db "SELECT COUNT(*) FROM data_sources;"
```

### 2. 异地备份

定期将备份文件复制到其他位置:
```bash
# 同步到云存储
rsync -av backups/ /path/to/cloud/storage/

# 或使用 rclone 同步到云盘
rclone sync backups/ remote:option_tracker_backups/
```

### 3. 监控磁盘空间

设置告警，当磁盘空间低于 1GB 时通知:
```bash
df -h . | awk 'NR==2 {print $4}'
```

### 4. 备份前数据一致性检查

对于 PostgreSQL，在备份前运行:
```sql
VACUUM ANALYZE;
```

对于 SQLite:
```sql
PRAGMA integrity_check;
```

## 🔗 相关文档

- [PostgreSQL 备份恢复官方文档](https://www.postgresql.org/docs/current/backup.html)
- [SQLite 备份 API](https://www.sqlite.org/backup.html)
- [APScheduler 定时任务文档](https://apscheduler.readthedocs.io/)

---

**更新时间**: 2025-12-01
**维护者**: OptionAlpha Team
