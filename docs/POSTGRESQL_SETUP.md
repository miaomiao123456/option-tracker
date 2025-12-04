# PostgreSQL 安装与配置指南（macOS）

## ⚡ 快速开始（一键迁移）

如果你已经完成了 PostgreSQL 的安装和配置，可以使用一键迁移脚本：

```bash
cd /Users/pm/Documents/期权交易策略/option_tracker
python3 scripts/migrate_to_postgresql.py
```

该脚本会自动执行：
1. ✅ 备份 SQLite 数据库
2. ✅ 导出数据为 JSON
3. ✅ 初始化 PostgreSQL 表结构
4. ✅ 导入数据到 PostgreSQL
5. ✅ 验证数据一致性

**命令行选项**:
- `--skip-backup`: 跳过备份（不推荐）
- `--skip-init`: 跳过表结构初始化（如果已初始化）
- `--force`: 跳过确认，直接执行

如果是首次设置，请继续阅读下面的详细步骤。

---

## 📦 安装 PostgreSQL

### 方法一：使用 Homebrew（推荐）

```bash
# 1. 安装 PostgreSQL
brew install postgresql@15

# 2. 启动 PostgreSQL 服务
brew services start postgresql@15

# 3. 验证安装
psql --version
```

### 方法二：使用 Postgres.app

1. 下载 [Postgres.app](https://postgresapp.com/)
2. 将应用拖到 Applications 文件夹
3. 双击打开 Postgres.app
4. 点击 "Initialize" 创建数据库服务器

---

## 🔧 创建数据库和用户

### 1. 连接到 PostgreSQL

```bash
psql postgres
```

### 2. 创建数据库和用户

在 `psql` 命令行中执行：

```sql
-- 创建用户
CREATE USER optionalpha WITH PASSWORD 'your_secure_password';

-- 创建数据库
CREATE DATABASE option_tracker OWNER optionalpha;

-- 授予权限
GRANT ALL PRIVILEGES ON DATABASE option_tracker TO optionalpha;

-- 退出
\q
```

### 3. 测试连接

```bash
psql -U optionalpha -d option_tracker -h localhost
```

输入密码后，如果看到 `option_tracker=#` 提示符，说明连接成功。

---

## ⚙️ 配置项目

### 1. 安装 PostgreSQL 驱动

```bash
pip3 install psycopg2-binary
```

### 2. 更新配置文件

编辑 `.env` 文件，添加 PostgreSQL 连接信息：

```bash
# 注释掉或删除 SQLite 配置
# DATABASE_URL=sqlite:///./option_tracker.db

# 添加 PostgreSQL 配置
DATABASE_URL=postgresql://optionalpha:your_secure_password@localhost:5432/option_tracker
```

**连接字符串格式说明：**
```
postgresql://用户名:密码@主机:端口/数据库名
```

### 3. 更新 settings.py

确保 `config/settings.py` 支持从环境变量读取：

```python
class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./option_tracker.db"  # 默认值

    class Config:
        env_file = ".env"
```

---

## 🔄 数据迁移

### 方法一：使用迁移脚本（推荐）

运行自动迁移脚本：

```bash
cd /Users/pm/Documents/期权交易策略/option_tracker
python3 scripts/migrate_to_postgresql.py
```

脚本会自动：
1. 备份 SQLite 数据库
2. 导出数据为 JSON
3. 在 PostgreSQL 中创建表
4. 导入数据
5. 验证数据一致性

### 方法二：手动迁移

#### 1. 备份 SQLite 数据

```bash
cp option_tracker.db option_tracker.db.backup_$(date +%Y%m%d_%H%M%S)
```

#### 2. 导出数据

```bash
python3 scripts/export_sqlite_data.py
```

会生成 `data_export.json` 文件。

#### 3. 初始化 PostgreSQL 表结构

```bash
# 临时修改 .env 使用 PostgreSQL
DATABASE_URL=postgresql://optionalpha:password@localhost:5432/option_tracker

# 运行数据库初始化
python3 -c "from app.models.database import init_db; init_db()"
```

#### 4. 导入数据

```bash
python3 scripts/import_to_postgresql.py
```

#### 5. 验证数据

```bash
python3 scripts/verify_migration.py
```

---

## ✅ 验证迁移

### 1. 检查表是否创建成功

```bash
psql -U optionalpha -d option_tracker -c "\dt"
```

应该看到所有表：
- commodities
- market_analysis_summary
- fundamental_reports
- institutional_positions
- technical_indicators
- daily_blueprints
- option_flows
- contract_infos
- data_sources
- data_collection_logs
- data_quality_metrics

### 2. 检查数据记录数

```bash
psql -U optionalpha -d option_tracker -c "
SELECT
    table_name,
    (SELECT COUNT(*) FROM information_schema.tables WHERE table_name = t.table_name) as row_count
FROM information_schema.tables t
WHERE table_schema = 'public'
ORDER BY table_name;
"
```

### 3. 对比 SQLite 和 PostgreSQL 数据量

```bash
python3 scripts/compare_databases.py
```

---

## 🚀 启动应用

### 1. 确认配置

检查 `.env` 文件中的 `DATABASE_URL` 已更新为 PostgreSQL。

### 2. 启动服务

```bash
python3 main.py
```

### 3. 测试 API

```bash
curl http://localhost:8000/api/v1/summary/overview
```

---

## 🔧 PostgreSQL 常用命令

### 连接数据库

```bash
psql -U optionalpha -d option_tracker
```

### psql 内部命令

```sql
\l              -- 列出所有数据库
\c database     -- 切换数据库
\dt             -- 列出所有表
\d table_name   -- 查看表结构
\du             -- 列出所有用户
\q              -- 退出
```

### SQL 查询示例

```sql
-- 查看数据源数量
SELECT COUNT(*) FROM data_sources;

-- 查看最近的采集日志
SELECT source_name, collect_time, status, records_collected
FROM data_collection_logs
ORDER BY collect_time DESC
LIMIT 10;

-- 查看数据质量统计
SELECT source_name, AVG(data_quality_score) as avg_score
FROM data_collection_logs
WHERE data_quality_score IS NOT NULL
GROUP BY source_name;
```

---

## 🛠️ 故障排查

### 问题1：无法连接数据库

**错误信息**:
```
could not connect to server: Connection refused
```

**解决方案**:
```bash
# 检查 PostgreSQL 服务状态
brew services list

# 重启服务
brew services restart postgresql@15
```

### 问题2：密码认证失败

**错误信息**:
```
FATAL: password authentication failed for user "optionalpha"
```

**解决方案**:
1. 确认 `.env` 中的密码正确
2. 重置密码：
```sql
ALTER USER optionalpha WITH PASSWORD 'new_password';
```

### 问题3：数据库不存在

**错误信息**:
```
FATAL: database "option_tracker" does not exist
```

**解决方案**:
```bash
psql postgres
```
```sql
CREATE DATABASE option_tracker OWNER optionalpha;
```

### 问题4：表不存在

**解决方案**:
```bash
python3 -c "from app.models.database import init_db; init_db()"
```

---

## 📊 性能优化建议

### 1. 创建索引

```sql
-- 为常用查询字段创建索引
CREATE INDEX idx_data_collection_logs_source ON data_collection_logs(source_name);
CREATE INDEX idx_data_collection_logs_time ON data_collection_logs(collect_time);
CREATE INDEX idx_data_sources_type ON data_sources(source_type);
CREATE INDEX idx_fundamental_reports_code ON fundamental_reports(comm_code);
```

### 2. 配置连接池

在 `app/models/database.py` 中：

```python
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,        # 连接池大小
    max_overflow=20,     # 最大溢出连接数
    pool_recycle=3600    # 连接回收时间（秒）
)
```

### 3. 启用 WAL 模式（预写日志）

PostgreSQL 默认已启用，无需配置。

---

## 🔄 回滚到 SQLite

如果需要回滚到 SQLite：

### 1. 停止应用

```bash
# 停止正在运行的服务
pkill -f "python3 main.py"
```

### 2. 恢复配置

编辑 `.env`：
```bash
DATABASE_URL=sqlite:///./option_tracker.db
```

### 3. 恢复数据库文件

```bash
# 如果有备份
cp option_tracker.db.backup_20251130_160000 option_tracker.db
```

### 4. 重启应用

```bash
python3 main.py
```

---

## 📝 最佳实践

### 1. 定期备份

```bash
# 备份数据库
pg_dump -U optionalpha -d option_tracker -F c -f backup_$(date +%Y%m%d).dump

# 恢复数据库
pg_restore -U optionalpha -d option_tracker -c backup_20251130.dump
```

### 2. 监控连接数

```sql
SELECT COUNT(*) FROM pg_stat_activity;
```

### 3. 查看慢查询

```sql
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

---

## 🔗 参考资料

- [PostgreSQL 官方文档](https://www.postgresql.org/docs/)
- [SQLAlchemy PostgreSQL 方言](https://docs.sqlalchemy.org/en/14/dialects/postgresql.html)
- [Homebrew PostgreSQL](https://formulae.brew.sh/formula/postgresql@15)

---

**更新时间**: 2025-11-30
**适用版本**: PostgreSQL 15+
**操作系统**: macOS
