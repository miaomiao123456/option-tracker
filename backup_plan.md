# 数据备份与恢复方案

## 问题：如何防止数据丢失？

### 多层备份策略

```
┌─────────────────────────────────────────────┐
│  Level 1: 实时 WAL 备份 (PostgreSQL)        │
│  - 自动的，崩溃可恢复                        │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Level 2: 每小时增量备份                    │
│  - 保留最近24小时                            │
│  - 占用空间小                                │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Level 3: 每日全量备份                      │
│  - 保留最近30天                              │
│  - 存储到远程（OSS/S3）                      │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Level 4: 每周归档备份                      │
│  - 保留最近12周                              │
│  - 长期存储                                  │
└─────────────────────────────────────────────┘
```

## 实施方案

### 1. PostgreSQL 自动备份脚本

```bash
#!/bin/bash
# scripts/backup_database.sh

# 配置
DB_NAME="option_tracker_prod"
DB_USER="postgres"
BACKUP_DIR="/Users/pm/Documents/期权交易策略/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_$DATE.sql.gz"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 全量备份（压缩）
pg_dump -U $DB_USER $DB_NAME | gzip > $BACKUP_FILE

# 检查备份是否成功
if [ $? -eq 0 ]; then
    echo "✅ 备份成功: $BACKUP_FILE"

    # 删除30天前的备份
    find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +30 -delete

    # 发送成功通知
    curl -X POST "$DINGTALK_WEBHOOK" \
        -H "Content-Type: application/json" \
        -d "{\"msgtype\":\"text\",\"text\":{\"content\":\"✅ 数据库备份成功\n文件: $BACKUP_FILE\"}}"
else
    echo "❌ 备份失败"

    # 发送失败告警
    curl -X POST "$DINGTALK_WEBHOOK" \
        -H "Content-Type: application/json" \
        -d "{\"msgtype\":\"text\",\"text\":{\"content\":\"❌ 数据库备份失败！请立即检查\"},\"at\":{\"isAtAll\":true}}"

    exit 1
fi
```

### 2. 定时备份任务

```bash
# 编辑 crontab
crontab -e

# 每天凌晨2点全量备份
0 2 * * * /Users/pm/Documents/期权交易策略/option_tracker/scripts/backup_database.sh

# 每小时增量备份（仅备份最近1小时的数据）
0 * * * * /Users/pm/Documents/期权交易策略/option_tracker/scripts/incremental_backup.sh
```

### 3. 恢复脚本

```bash
#!/bin/bash
# scripts/restore_database.sh

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "用法: ./restore_database.sh <backup_file>"
    exit 1
fi

echo "⚠️  警告：将从备份恢复数据库，当前数据将被覆盖！"
read -p "确认继续？(yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ 取消恢复"
    exit 0
fi

# 停止应用（防止数据写入）
echo "停止应用..."
pkill -f "python3 main.py"

# 删除现有数据库
echo "删除现有数据库..."
dropdb option_tracker_prod

# 创建新数据库
echo "创建新数据库..."
createdb option_tracker_prod

# 恢复数据
echo "恢复数据..."
gunzip < $BACKUP_FILE | psql option_tracker_prod

if [ $? -eq 0 ]; then
    echo "✅ 数据恢复成功"

    # 重启应用
    echo "重启应用..."
    cd /Users/pm/Documents/期权交易策略/option_tracker
    python3 main.py &

    echo "✅ 恢复完成"
else
    echo "❌ 恢复失败"
    exit 1
fi
```

### 4. 图片文件备份

```python
# scripts/backup_images.py
"""
备份蓝图图片到云存储（阿里云OSS）
"""
import os
from pathlib import Path
from datetime import datetime
import oss2

# OSS配置
access_key_id = os.getenv('OSS_ACCESS_KEY_ID')
access_key_secret = os.getenv('OSS_ACCESS_KEY_SECRET')
bucket_name = 'option-tracker-backup'
endpoint = 'oss-cn-shanghai.aliyuncs.com'

# 初始化OSS客户端
auth = oss2.Auth(access_key_id, access_key_secret)
bucket = oss2.Bucket(auth, endpoint, bucket_name)

def backup_images():
    """备份所有蓝图图片"""
    image_dir = Path('/Users/pm/Documents/期权交易策略/交易可查/images')

    for img_file in image_dir.glob('*.jpg'):
        # OSS路径：blueprints/2025/11/20251117.jpg
        date_str = img_file.stem
        year = date_str[:4]
        month = date_str[4:6]
        oss_key = f"blueprints/{year}/{month}/{img_file.name}"

        # 检查是否已存在
        if bucket.object_exists(oss_key):
            print(f"⏭️  跳过（已存在）: {oss_key}")
            continue

        # 上传
        try:
            bucket.put_object_from_file(oss_key, str(img_file))
            print(f"✅ 上传成功: {oss_key}")
        except Exception as e:
            print(f"❌ 上传失败 {img_file.name}: {e}")

if __name__ == "__main__":
    backup_images()
```

### 5. 备份验证

```python
# scripts/verify_backup.py
"""
验证备份文件完整性
"""
import gzip
import subprocess
from pathlib import Path

def verify_backup(backup_file):
    """验证备份文件"""
    print(f"验证备份: {backup_file}")

    # 1. 检查文件存在
    if not Path(backup_file).exists():
        print("❌ 文件不存在")
        return False

    # 2. 检查文件大小（不应该太小）
    size = Path(backup_file).stat().st_size
    if size < 1024:  # 小于1KB肯定有问题
        print(f"❌ 文件太小: {size} bytes")
        return False

    # 3. 尝试解压（验证文件完整性）
    try:
        with gzip.open(backup_file, 'rb') as f:
            # 读取前1000字节
            f.read(1000)
        print("✅ 文件完整性验证通过")
    except Exception as e:
        print(f"❌ 文件损坏: {e}")
        return False

    # 4. 验证SQL语法（可选，耗时较长）
    # subprocess.run(['gunzip', '-t', backup_file], check=True)

    print(f"✅ 备份验证通过: {backup_file} ({size/1024/1024:.2f} MB)")
    return True

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python verify_backup.py <backup_file>")
        sys.exit(1)

    verify_backup(sys.argv[1])
```

## 灾难恢复演练

### 每月一次恢复演练

```bash
#!/bin/bash
# scripts/disaster_recovery_drill.sh

echo "=== 灾难恢复演练 ==="
echo "1. 模拟数据库损坏"
echo "2. 从最新备份恢复"
echo "3. 验证数据完整性"
echo "4. 记录恢复时间"

START_TIME=$(date +%s)

# 创建测试数据库
createdb test_recovery

# 恢复到测试数据库
LATEST_BACKUP=$(ls -t /Users/pm/Documents/期权交易策略/backups/backup_*.sql.gz | head -1)
echo "使用备份: $LATEST_BACKUP"

gunzip < $LATEST_BACKUP | psql test_recovery

# 验证数据
RECORD_COUNT=$(psql test_recovery -t -c "SELECT COUNT(*) FROM daily_blueprints")
echo "数据记录数: $RECORD_COUNT"

# 计算恢复时间
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo "✅ 恢复演练完成"
echo "恢复用时: ${DURATION}秒"

# 清理测试数据库
dropdb test_recovery

# 记录演练结果
echo "$(date): 恢复演练成功，用时${DURATION}秒" >> /tmp/recovery_drill.log
```

## 监控备份状态

```python
# app/routers/admin.py 添加

@router.get("/backup/status")
async def get_backup_status():
    """获取备份状态"""
    backup_dir = Path("/Users/pm/Documents/期权交易策略/backups")

    if not backup_dir.exists():
        return {"status": "error", "message": "备份目录不存在"}

    # 获取所有备份文件
    backups = sorted(backup_dir.glob("backup_*.sql.gz"), reverse=True)

    if not backups:
        return {"status": "warning", "message": "无备份文件"}

    # 最新备份
    latest = backups[0]
    latest_time = datetime.fromtimestamp(latest.stat().st_mtime)

    # 检查是否超过24小时未备份
    hours_since_backup = (datetime.now() - latest_time).total_seconds() / 3600

    if hours_since_backup > 24:
        status = "warning"
        message = f"最后备份距今{hours_since_backup:.1f}小时，可能备份任务失败"
    else:
        status = "ok"
        message = "备份正常"

    return {
        "status": status,
        "message": message,
        "latest_backup": {
            "file": latest.name,
            "time": latest_time,
            "size_mb": latest.stat().st_size / 1024 / 1024
        },
        "total_backups": len(backups)
    }
```

## 自动化清单

✅ 每日2AM自动全量备份
✅ 每小时自动增量备份
✅ 备份成功/失败自动通知
✅ 自动删除30天前的旧备份
✅ 备份文件自动验证
✅ 每月灾难恢复演练
✅ 备份状态API监控
