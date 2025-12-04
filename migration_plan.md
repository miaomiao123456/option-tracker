# 数据库迁移计划

## Day 1: 本地PostgreSQL环境搭建

### 1. 安装PostgreSQL
```bash
# macOS
brew install postgresql@15
brew services start postgresql@15

# 创建数据库
createdb option_tracker_prod
```

### 2. 安装Python依赖
```bash
pip install psycopg2-binary alembic
```

### 3. 数据库配置
```python
# config/settings.py
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://localhost/option_tracker_prod"
)
```

## Day 2: 数据迁移脚本

### 1. 导出SQLite数据
```python
# scripts/export_sqlite_data.py
import sqlite3
import json
from datetime import datetime

def export_all_tables():
    conn = sqlite3.connect('option_tracker.db')
    conn.row_factory = sqlite3.Row

    tables = [
        'commodities',
        'commodity_aliases',
        'daily_blueprints',
        'fundamental_reports',
        'option_flows',
        'institutional_positions',
        'contract_infos',
        'technical_indicators',
        'market_analysis_summary'
    ]

    data = {}
    for table in tables:
        cursor = conn.execute(f"SELECT * FROM {table}")
        rows = [dict(row) for row in cursor.fetchall()]
        data[table] = rows

    with open('data_backup.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    print(f"✅ 导出完成，共{len(data)}个表")
    conn.close()

if __name__ == "__main__":
    export_all_tables()
```

### 2. 导入PostgreSQL
```python
# scripts/import_to_postgres.py
import json
from app.models.database import SessionLocal, engine
from app.models import models

def import_all_data():
    with open('data_backup.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    db = SessionLocal()
    try:
        # 导入品种数据
        for item in data['commodities']:
            commodity = models.Commodity(**item)
            db.add(commodity)

        # 导入其他表...
        # (类似逻辑)

        db.commit()
        print("✅ 数据导入成功")
    except Exception as e:
        db.rollback()
        print(f"❌ 导入失败: {e}")
    finally:
        db.close()
```

## Day 3: 测试与切换

### 1. 双写验证
```python
# 同时写入SQLite和PostgreSQL，对比数据一致性
# 运行24小时，确保无问题
```

### 2. 性能测试
```python
# 测试并发写入
# 测试查询性能
# 测试数据完整性
```

### 3. 正式切换
```python
# 停止所有爬虫
# 最后一次全量导出SQLite
# 导入PostgreSQL
# 修改配置，启用PostgreSQL
# 重启所有服务
# SQLite作为备份保留7天
```

## 回滚方案

如果PostgreSQL出问题：
1. 立即切换回SQLite配置
2. 从最新备份恢复
3. 重启服务
4. 预计恢复时间：<5分钟
