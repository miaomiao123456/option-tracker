# OptionAlpha 重构迁移检查清单

**创建时间**: 2024-12-16
**文档用途**: 重构过程中的详细操作步骤和检查点
**使用方法**: 按顺序执行,每完成一项打✅

---

## 📋 重构前准备 (必做!)

### A. 数据备份 (最重要!)

- [ ] **A1. 导出完整SQLite数据库**
```bash
cd /Users/pm/Documents/期权交易策略/option_tracker
sqlite3 option_tracker.db .dump > FULL_BACKUP_20241216.sql
```
验证: `ls -lh FULL_BACKUP_20241216.sql` 应显示文件大小 > 1MB

- [ ] **A2. 压缩备份文件**
```bash
gzip FULL_BACKUP_20241216.sql
```
验证: `ls -lh FULL_BACKUP_20241216.sql.gz`

- [ ] **A3. 复制到安全位置**
```bash
# 复制到桌面
cp FULL_BACKUP_20241216.sql.gz ~/Desktop/

# 复制到iCloud (如果有)
cp FULL_BACKUP_20241216.sql.gz ~/Library/Mobile\ Documents/com~apple~CloudDocs/

# 复制到U盘 (如果有)
cp FULL_BACKUP_20241216.sql.gz /Volumes/YourUSB/
```
验证: 至少有2个备份副本

- [ ] **A4. 验证备份完整性**
```bash
# 解压并测试导入
gunzip -c FULL_BACKUP_20241216.sql.gz > test_restore.sql
sqlite3 test.db < test_restore.sql
sqlite3 test.db "SELECT COUNT(*) FROM warehouse_receipts;"
rm test.db test_restore.sql
```
验证: 应显示数据条数 > 0

- [ ] **A5. 备份配置文件**
```bash
cp .env .env.backup_20241216
cp config/settings.py config/settings.py.backup_20241216
```

- [ ] **A6. 备份JSON数据文件**
```bash
mkdir -p data_backup_20241216
cp -r data/* data_backup_20241216/
```

- [ ] **A7. 备份整个项目目录 (可选)**
```bash
cd /Users/pm/Documents/期权交易策略/
tar -czf option_tracker_full_backup_20241216.tar.gz option_tracker/ \
    --exclude='option_tracker/backups' \
    --exclude='option_tracker/__pycache__'
```

---

### B. 环境检查

- [ ] **B1. 记录当前Python版本**
```bash
python3 --version
```
记录结果: _______________

- [ ] **B2. 记录当前依赖版本**
```bash
pip freeze > requirements_current_20241216.txt
```

- [ ] **B3. 测试当前系统运行**
```bash
# 启动系统
cd /Users/pm/Documents/期权交易策略/option_tracker
python3 main.py
```
验证: 访问 http://localhost:8000/frontend 正常

- [ ] **B4. 测试API接口**
```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/virtual-real-ratio/summary
```
验证: 返回正常JSON数据

- [ ] **B5. 记录数据库表数据量**
```bash
sqlite3 option_tracker.db <<EOF
.mode column
SELECT 'warehouse_receipts', COUNT(*) FROM warehouse_receipts
UNION ALL SELECT 'institutional_positions', COUNT(*) FROM institutional_positions
UNION ALL SELECT 'research_reports', COUNT(*) FROM research_reports
UNION ALL SELECT 'market_full_view', COUNT(*) FROM market_full_view;
EOF
```
记录结果:
- warehouse_receipts: _____ 条
- institutional_positions: _____ 条
- research_reports: _____ 条
- market_full_view: _____ 条

---

### C. Token和密码确认

- [ ] **C1. 验证智汇期讯Token**
```bash
curl -X POST https://zhihuiqixun.com/api/variety/fullView \
  -H "Authorization: Bearer $ZHIHUI_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"publishDate":"2024-12-16"}'
```
验证: 返回数据,无401错误

- [ ] **C2. 验证Uqer Token**
```bash
# 在Python中测试
python3 << EOF
import os
os.environ['access_token'] = '$UQER_TOKEN'
from uqer import DataAPI
df = DataAPI.MktFutWRdGet(contractObject='CU', exchangeCD='XSGE', pandas='1')
print(f"成功获取 {len(df)} 条数据")
EOF
```
验证: 显示成功获取数据

- [ ] **C3. 验证交易可查账号**
```
手动登录: https://jiaoyikecha.com
用户名: _______
密码: _______
```
验证: 能正常登录

- [ ] **C4. 验证Gemini API Key**
```bash
curl https://generativelanguage.googleapis.com/v1/models \
  -H "x-goog-api-key: $GEMINI_API_KEY"
```
验证: 返回模型列表

- [ ] **C5. 验证飞书Webhook**
```bash
curl -X POST $FEISHU_WEBHOOK \
  -H "Content-Type: application/json" \
  -d '{"msg_type":"text","content":{"text":"测试消息"}}'
```
验证: 飞书群收到消息

---

### D. 创建恢复点

- [ ] **D1. 记录当前git状态 (如果使用git)**
```bash
git status > git_status_before_refactor.txt
git log -5 > git_log_before_refactor.txt
```

- [ ] **D2. 创建系统快照时间戳**
```bash
echo "重构前系统快照时间: $(date)" > REFACTOR_TIMESTAMP.txt
```

- [ ] **D3. 测试回滚流程 (重要!)**
```bash
# 在测试目录模拟回滚
mkdir -p /tmp/rollback_test
cd /tmp/rollback_test
cp ~/Desktop/FULL_BACKUP_20241216.sql.gz .
gunzip FULL_BACKUP_20241216.sql.gz
sqlite3 test.db < FULL_BACKUP_20241216.sql
sqlite3 test.db "SELECT COUNT(*) FROM warehouse_receipts;"
rm -rf /tmp/rollback_test
```
验证: 能正常恢复数据

---

## 🚀 云服务器准备

### E. 购买云服务器

- [ ] **E1. 选择云服务商**
- [ ] 阿里云
- [ ] 腾讯云
- [ ] 华为云
- [ ] 其他: _______

- [ ] **E2. 购买轻量应用服务器**
配置要求:
- CPU: 2核
- 内存: 4GB
- 硬盘: 60GB SSD
- 带宽: 3Mbps
- 系统: Ubuntu 22.04 LTS

记录信息:
- 公网IP: ___.___.___.___
- 内网IP: ___.___.___.___
- SSH端口: _______
- root密码: _______

- [ ] **E3. 配置安全组**
开放端口:
- 22 (SSH)
- 80 (HTTP)
- 443 (HTTPS)
- 8000 (API,可选)

- [ ] **E4. SSH登录测试**
```bash
ssh root@your_server_ip
```
验证: 能正常登录

---

### F. 服务器基础配置

- [ ] **F1. 更新系统**
```bash
ssh root@your_server_ip
apt update && apt upgrade -y
```

- [ ] **F2. 安装Docker**
```bash
curl -fsSL https://get.docker.com | bash
docker --version
```
验证: 显示Docker版本号

- [ ] **F3. 安装Docker Compose**
```bash
apt install docker-compose -y
docker-compose --version
```
验证: 显示Docker Compose版本号

- [ ] **F4. 创建应用目录**
```bash
mkdir -p /opt/optionalpha
cd /opt/optionalpha
pwd
```
验证: 显示 /opt/optionalpha

- [ ] **F5. 配置时区**
```bash
timedatectl set-timezone Asia/Shanghai
date
```
验证: 显示正确的北京时间

- [ ] **F6. 配置防火墙 (可选)**
```bash
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
ufw status
```

---

### G. 域名配置 (可选但推荐)

- [ ] **G1. 购买域名**
域名: _________________

- [ ] **G2. 配置DNS解析**
添加A记录:
- 主机记录: @ 或 www
- 记录类型: A
- 记录值: your_server_ip
- TTL: 600

- [ ] **G3. 等待DNS生效**
```bash
# 本地检查
ping your-domain.com
```
验证: 解析到正确的服务器IP

- [ ] **G4. 申请SSL证书**
```bash
# 服务器上执行
apt install certbot -y
certbot certonly --standalone -d your-domain.com
```
验证: 证书保存在 /etc/letsencrypt/live/

---

## 📦 代码部署

### H. 代码上传

- [ ] **H1. 清理本地项目 (可选)**
```bash
cd /Users/pm/Documents/期权交易策略/option_tracker
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -name "*.pyc" -delete
```

- [ ] **H2. 打包项目 (方式A)**
```bash
tar -czf option_tracker_deploy.tar.gz \
    --exclude='backups' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='option_tracker.db' \
    app/ config/ scripts/ frontend/ *.py *.txt *.md
```

- [ ] **H3. 上传到服务器**
```bash
scp option_tracker_deploy.tar.gz root@your_server_ip:/opt/optionalpha/
```
验证: 上传成功,无错误

- [ ] **H4. 服务器上解压**
```bash
ssh root@your_server_ip
cd /opt/optionalpha
tar -xzf option_tracker_deploy.tar.gz
ls -la
```
验证: 目录结构正确

- [ ] **H5. 创建必要目录**
```bash
mkdir -p logs data backups/daily backups/hourly backups/weekly
chmod 755 logs data backups
```

---

### I. 环境配置

- [ ] **I1. 创建.env.production文件**
```bash
cd /opt/optionalpha
nano .env.production
```
粘贴配置:
```bash
# 数据库配置 (SQLite)
DATABASE_URL=sqlite:////app/data/option_tracker.db

# Token配置 (从本地.env复制)
ZHIHUI_AUTH_TOKEN=your_actual_token
UQER_TOKEN=your_actual_token
JYK_USER=your_username
JYK_PASS=your_password
GEMINI_API_KEY=your_key
FEISHU_WEBHOOK=your_webhook

# 生产环境配置
DEBUG=False
LOG_LEVEL=INFO
```

- [ ] **I2. 验证环境变量**
```bash
cat .env.production | grep -v "^#" | grep -v "^$"
```
验证: 所有必要Token都已填写

---

### J. Docker配置

- [ ] **J1. 创建Dockerfile**
```bash
nano Dockerfile
```
粘贴内容 (见 TARGET_ARCHITECTURE.md)

- [ ] **J2. 创建docker-compose.yml**
```bash
nano docker-compose.yml
```
粘贴内容 (见 TARGET_ARCHITECTURE.md)

- [ ] **J3. 创建.dockerignore**
```bash
cat > .dockerignore << EOF
__pycache__
*.pyc
*.pyo
*.pyd
.git
.gitignore
backups
*.db
*.log
.env
EOF
```

- [ ] **J4. 构建Docker镜像**
```bash
docker-compose build
```
验证: 构建成功,无错误

---

## 🗄️ 数据库部署 (SQLite)

### K. 上传SQLite数据库

- [ ] **K1. 上传数据库文件到服务器**
```bash
# 本地执行
scp option_tracker.db root@your_server_ip:/opt/optionalpha/
```

- [ ] **K2. 验证文件上传成功**
```bash
ssh root@your_server_ip
cd /opt/optionalpha
ls -lh option_tracker.db
```
验证: 文件大小约10MB

- [ ] **K3. 创建数据目录**
```bash
mkdir -p /opt/optionalpha/data
mv option_tracker.db /opt/optionalpha/data/
chmod 644 /opt/optionalpha/data/option_tracker.db
```

- [ ] **K4. 验证数据库可访问**
```bash
sqlite3 /opt/optionalpha/data/option_tracker.db "SELECT COUNT(*) FROM warehouse_receipts;"
```
验证: 返回数据条数

**优势**:
- ✅ 无需数据迁移
- ✅ 无需配置MySQL
- ✅ 部署时间从2天缩短到半天
- ✅ 月度成本节省¥150-200



---

## 🚀 启动服务

### L. 首次启动

- [ ] **L1. 启动所有服务**
```bash
docker-compose up -d
```

- [ ] **L2. 检查容器状态**
```bash
docker-compose ps
```
验证: 所有容器状态为 Up

- [ ] **L3. 查看应用日志**
```bash
docker-compose logs -f app
```
验证: 无ERROR日志,看到"Application startup complete"

- [ ] **L4. 测试健康检查**
```bash
curl http://localhost:8000/health
```
验证: 返回 {"status":"healthy"}

- [ ] **L5. 测试API接口**
```bash
curl http://localhost:8000/api/v1/virtual-real-ratio/summary
```
验证: 返回正常数据

- [ ] **L6. 测试前端页面**
```bash
curl http://localhost:8000/frontend
```
验证: 返回HTML内容

---

### M. 外网访问配置

- [ ] **M1. 配置Nginx (如果使用域名)**
```bash
nano nginx/nginx.conf
```
粘贴配置 (见示例)

- [ ] **M2. 重启Nginx**
```bash
docker-compose restart nginx
```

- [ ] **M3. 测试HTTP访问**
```bash
# 本地电脑测试
curl http://your-domain.com/health
```
验证: 返回健康状态

- [ ] **M4. 测试HTTPS访问 (如果配置了SSL)**
```bash
curl https://your-domain.com/health
```
验证: 返回健康状态

- [ ] **M5. 浏览器测试**
访问: https://your-domain.com/frontend
验证: 页面正常显示

---

## ✅ 功能验证

### N. 基础功能验证

- [ ] **N1. 总览页面**
访问: https://your-domain.com/frontend
检查:
  - [ ] 品种列表显示
  - [ ] 四维评分显示
  - [ ] 点击品种详情正常

- [ ] **N2. 虚实比页面**
访问: https://your-domain.com/virtual_real_ratio.html
检查:
  - [ ] 数据列表显示
  - [ ] 统计数据正确
  - [ ] 历史趋势图表正常

- [ ] **N3. 智汇期讯页面**
访问: https://your-domain.com/zhihui
检查:
  - [ ] 多空全景数据显示
  - [ ] 研报列表显示
  - [ ] 数据更新正常

- [ ] **N4. 数据治理页面**
访问: https://your-domain.com/data-governance
检查:
  - [ ] 数据源状态显示
  - [ ] 任务执行记录显示

---

### O. 定时任务验证

- [ ] **O1. 检查调度器状态**
```bash
docker exec -it optionalpha_app python3 -c "
from app.scheduler import get_scheduler_status
import json
print(json.dumps(get_scheduler_status(), indent=2))
"
```
验证: 显示10个任务列表

- [ ] **O2. 手动触发虚实比刷新**
```bash
curl -X POST http://localhost:8000/api/v1/virtual-real-ratio/refresh
```
验证: 返回成功消息

- [ ] **O3. 查看任务日志**
```bash
docker-compose logs app | grep "智汇期讯"
docker-compose logs app | grep "虚实比"
docker-compose logs app | grep "交易可查"
```
验证: 看到任务执行日志

- [ ] **O4. 等待自动任务执行**
等待30分钟,观察智汇期讯任务自动执行
```bash
docker-compose logs -f app
```
验证: 看到任务自动触发

---

### P. 数据爬取验证

- [ ] **P1. 验证智汇期讯爬虫**
检查数据库:
```bash
docker exec -it optionalpha_mysql mysql -uroot -p -e "
USE optionalpha;
SELECT * FROM market_full_view ORDER BY record_date DESC LIMIT 5;
"
```
验证: 有今天的数据

- [ ] **P2. 验证虚实比爬虫**
```bash
docker exec -it optionalpha_mysql mysql -uroot -p -e "
USE optionalpha;
SELECT comm_code, virtual_real_ratio, record_date
FROM warehouse_receipts
ORDER BY record_date DESC LIMIT 10;
"
```
验证: 数据更新

- [ ] **P3. 验证研报数据**
```bash
docker exec -it optionalpha_mysql mysql -uroot -p -e "
USE optionalpha;
SELECT COUNT(*), MAX(publish_date) FROM research_reports;
"
```
验证: 有最新研报

---

## 🔄 性能测试

### Q. 压力测试 (可选)

- [ ] **Q1. API响应时间**
```bash
for i in {1..10}; do
  time curl http://localhost:8000/api/v1/virtual-real-ratio/summary
done
```
验证: 平均响应时间 < 500ms

- [ ] **Q2. 并发测试**
```bash
ab -n 100 -c 10 http://localhost:8000/health
```
验证: 成功率100%

- [ ] **Q3. 内存占用**
```bash
docker stats --no-stream
```
验证: 应用内存 < 500MB

---

## 📱 告警测试

### R. 飞书告警验证

- [ ] **R1. 测试告警发送**
```bash
# 手动触发一个失败的爬虫看告警
docker exec -it optionalpha_app python3 -c "
from app.services.data_collector import send_feishu_alert
send_feishu_alert('测试数据源', Exception('测试错误'), 1)
"
```
验证: 飞书群收到告警消息

- [ ] **R2. 查看告警日志**
```bash
docker-compose logs app | grep "告警"
```

---

## 🔐 安全检查

### S. 安全配置验证

- [ ] **S1. 检查防火墙**
```bash
ssh root@your_server_ip
ufw status
```
验证: 只开放必要端口

- [ ] **S2. 检查Docker容器安全**
```bash
docker-compose exec app whoami
```
验证: 不是root用户运行

- [ ] **S3. 检查环境变量**
```bash
docker-compose exec app env | grep TOKEN
```
验证: Token不在日志中明文显示

- [ ] **S4. 检查SSL证书**
```bash
openssl s_client -connect your-domain.com:443 -servername your-domain.com
```
验证: 证书有效

---

## 📊 监控配置

### T. 日志监控

- [ ] **T1. 配置日志轮转**
```bash
nano /etc/logrotate.d/optionalpha
```
粘贴:
```
/opt/optionalpha/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0644 root root
}
```

- [ ] **T2. 测试日志轮转**
```bash
logrotate -f /etc/logrotate.d/optionalpha
ls -lh /opt/optionalpha/logs/
```

---

## 🎉 重构完成验证

### U. 最终检查清单

- [ ] **U1. 所有页面正常访问**
  - [ ] /frontend
  - [ ] /virtual_real_ratio.html
  - [ ] /zhihui
  - [ ] /data-governance
  - [ ] /analysis-v2
  - [ ] /report-detail

- [ ] **U2. 所有API正常响应**
  - [ ] /health
  - [ ] /api/v1/virtual-real-ratio/*
  - [ ] /api/v1/zhihui/*
  - [ ] /api/v1/capital/*
  - [ ] /api/term-structure/*

- [ ] **U3. 定时任务正常执行**
  - [ ] 智汇期讯 (30分钟)
  - [ ] 虚实比 (每天18:00)
  - [ ] 交易可查 (每天19:00)
  - [ ] 数据分析 (每天19:30)
  - [ ] 数据备份 (每小时+每天)

- [ ] **U4. 数据准确性验证**
  - [ ] 数据条数与本地一致
  - [ ] 最新数据正常更新
  - [ ] 历史数据完整

- [ ] **U5. 性能达标**
  - [ ] API响应 < 500ms
  - [ ] 页面加载 < 2s
  - [ ] 内存占用 < 500MB
  - [ ] CPU占用 < 50%

- [ ] **U6. 稳定性验证**
连续运行7天:
  - [ ] Day 1: 正常
  - [ ] Day 2: 正常
  - [ ] Day 3: 正常
  - [ ] Day 4: 正常
  - [ ] Day 5: 正常
  - [ ] Day 6: 正常
  - [ ] Day 7: 正常

---

## 🔚 本地清理 (重构成功后)

### V. 释放本地空间

⚠️ **警告: 只有在云端系统稳定运行至少2周后,才执行以下操作!**

- [ ] **V1. 停止本地服务**
```bash
# 找到进程
lsof -i:8000
# 杀掉进程
kill <PID>
```

- [ ] **V2. 删除备份文件**
```bash
cd /Users/pm/Documents/期权交易策略/option_tracker
rm -rf backups/hourly/*
rm -rf backups/daily/*
rm -rf backups/weekly/*
```
释放空间: ~250MB

- [ ] **V3. 删除数据库文件 (可选)**
```bash
# 先确保有云端备份!
rm option_tracker.db
rm optionalpha.db
rm data/option_tracker.db
```
释放空间: ~10MB

- [ ] **V4. 清理Python缓存**
```bash
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -name "*.pyc" -delete
```
释放空间: ~5MB

- [ ] **V5. 保留的文件**
保留以下文件用于本地开发:
- app/ 源代码
- config/ 配置文件
- scripts/ 脚本
- requirements.txt
- .env.backup_20241216 (备份的环境变量)
- FULL_BACKUP_20241216.sql.gz (完整备份)

总释放空间: **260MB+**

---

## 📝 记录与文档

### W. 更新文档

- [ ] **W1. 记录服务器信息**
创建文件: `SERVER_INFO.md`
```markdown
# 服务器信息

## 基本信息
- 云服务商: _______
- 公网IP: ___.___.___.___
- 域名: your-domain.com
- SSH端口: 22

## 访问地址
- 前端: https://your-domain.com
- API文档: https://your-domain.com/docs
- 健康检查: https://your-domain.com/health

## 数据库
- 类型: MySQL 8.0
- 地址: localhost:3306
- 数据库名: optionalpha
- 备份周期: 每天

## 重要路径
- 应用目录: /opt/optionalpha
- 日志目录: /opt/optionalpha/logs
- 数据目录: /opt/optionalpha/data
```

- [ ] **W2. 更新README.md**
添加部署说明

- [ ] **W3. 创建CHANGELOG.md**
记录重构变更

---

## 🆘 故障排查

### X. 常见问题

#### 问题1: 容器无法启动
```bash
# 查看日志
docker-compose logs app

# 常见原因:
# 1. 环境变量配置错误
# 2. 数据库连接失败
# 3. 端口被占用

# 解决方法:
docker-compose down
docker-compose up -d
```

#### 问题2: API返回500错误
```bash
# 查看应用日志
docker-compose logs -f app | tail -100

# 检查数据库连接
docker-compose exec app python3 -c "
from app.core.database import engine
engine.connect()
print('数据库连接成功')
"
```

#### 问题3: 定时任务不执行
```bash
# 检查调度器状态
docker-compose exec app python3 -c "
from app.scheduler import get_scheduler_status
print(get_scheduler_status())
"

# 重启应用
docker-compose restart app
```

#### 问题4: 数据不更新
```bash
# 手动触发爬虫
curl -X POST http://localhost:8000/api/v1/virtual-real-ratio/refresh

# 查看爬虫日志
docker-compose logs app | grep "爬取"
```

---

## 📞 紧急回滚

### Y. 如果重构失败

⚠️ **如遇到无法解决的问题,立即执行回滚!**

- [ ] **Y1. 停止云端服务**
```bash
ssh root@your_server_ip
cd /opt/optionalpha
docker-compose down
```

- [ ] **Y2. 本地恢复数据库**
```bash
cd /Users/pm/Documents/期权交易策略/option_tracker
cp option_tracker.db option_tracker.db.broken  # 备份当前
cp ~/Desktop/FULL_BACKUP_20241216.sql.gz .
gunzip FULL_BACKUP_20241216.sql.gz
sqlite3 option_tracker.db < FULL_BACKUP_20241216.sql
```

- [ ] **Y3. 恢复配置文件**
```bash
cp .env.backup_20241216 .env
```

- [ ] **Y4. 启动本地服务**
```bash
python3 main.py
```

- [ ] **Y5. 验证恢复成功**
访问: http://localhost:8000/frontend
验证: 系统正常运行

---

## ✅ 重构完成确认

### Z. 最终签署

- [ ] **所有检查项已完成**
- [ ] **云端系统稳定运行7天+**
- [ ] **数据准确无误**
- [ ] **性能符合预期**
- [ ] **本地备份已保存**

**重构完成时间**: _______________
**签署人**: _______________

---

**祝重构顺利! 🎉**

**如有问题,参考以下文档:**
- CURRENT_SYSTEM_SNAPSHOT.md - 重构前系统快照
- TARGET_ARCHITECTURE.md - 目标架构
- PRODUCT_DOCUMENTATION.md - 产品完整文档
