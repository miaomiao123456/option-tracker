# SQLite 简化部署方案总结

**创建时间**: 2024-12-16
**目的**: 使用SQLite简化云端部署，降低成本和复杂度

---

## 📊 方案对比

### 原方案 (MySQL)
```yaml
架构:
  - FastAPI应用
  - MySQL 8.0容器
  - Redis缓存
  - Nginx反向代理

月度成本: ¥230
  - 服务器: ¥60
  - MySQL RDS: ¥100-150
  - Redis: ¥50
  - OSS: ¥10

部署复杂度: ★★★★☆
  - 需要配置MySQL
  - 需要数据迁移脚本
  - 需要配置Redis
  - 部署时间: 2天
```

### 新方案 (SQLite) ✅ 推荐
```yaml
架构:
  - FastAPI应用
  - SQLite数据库文件
  - Nginx反向代理

月度成本: ¥64
  - 服务器: ¥60
  - 域名: ¥4
  - 其他: ¥0

部署复杂度: ★★☆☆☆
  - 直接上传.db文件
  - 无需数据迁移
  - 无需额外配置
  - 部署时间: 半天
```

**节省**: ¥166/月 (¥1992/年)

---

## 💡 为什么选择SQLite？

### ✅ 适合的理由

1. **数据量小**
   - 当前: 10MB
   - 年增长: <50MB
   - 10年后预计: <500MB

2. **单用户系统**
   - 无并发写入
   - 主要是定时任务(10个)
   - 读多写少

3. **性能完全够用**
   - 查询速度: 毫秒级
   - 支持百万级数据
   - 当前4000条记录

4. **零维护成本**
   - 无需数据库服务器
   - 无需配置权限
   - 单文件备份超简单

5. **部署超级简单**
   - 上传.db文件即可
   - 无需安装MySQL
   - 无需配置连接

### ❌ 不需要MySQL的场景

您的系统**没有**以下需求:
- ❌ 高并发写入 (您只有定时任务)
- ❌ 多用户同时修改 (单用户系统)
- ❌ 复杂多表事务 (业务逻辑简单)
- ❌ TB级数据量 (10年才1GB)
- ❌ 读写分离 (读写都不多)

---

## 📦 简化后的部署架构

```
云服务器 (2核4GB)
├── Docker
│   ├── FastAPI应用容器
│   └── Nginx容器
│
├── SQLite数据库
│   └── option_tracker.db (10MB)
│
└── 备份
    └── 定时复制.db文件
```

---

## 🚀 快速部署步骤

### 1. 准备阶段 (本地)
```bash
# 备份数据库
cp option_tracker.db option_tracker_backup.db

# 打包项目
tar -czf optionalpha.tar.gz \
    --exclude='backups' \
    --exclude='__pycache__' \
    app/ config/ scripts/ frontend/ *.py requirements.txt option_tracker.db
```

### 2. 服务器准备
```bash
# 购买云服务器 (阿里云/腾讯云)
# 配置: 2核4GB Ubuntu 22.04

# 安装Docker
curl -fsSL https://get.docker.com | bash
apt install docker-compose -y
```

### 3. 代码部署
```bash
# 上传项目
scp optionalpha.tar.gz root@your_server_ip:/opt/

# 服务器解压
ssh root@your_server_ip
cd /opt
tar -xzf optionalpha.tar.gz
cd optionalpha

# 创建数据目录
mkdir -p data
mv option_tracker.db data/
```

### 4. 配置环境
```bash
# 创建.env.production
cat > .env.production << EOF
DATABASE_URL=sqlite:////app/data/option_tracker.db
ZHIHUI_AUTH_TOKEN=your_token
UQER_TOKEN=your_token
JYK_USER=your_user
JYK_PASS=your_pass
GEMINI_API_KEY=your_key
FEISHU_WEBHOOK=your_webhook
DEBUG=False
LOG_LEVEL=INFO
EOF
```

### 5. 创建docker-compose.yml
```yaml
version: '3.8'

services:
  app:
    build: .
    container_name: optionalpha_app
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:////app/data/option_tracker.db
      - ZHIHUI_AUTH_TOKEN=${ZHIHUI_AUTH_TOKEN}
      - UQER_TOKEN=${UQER_TOKEN}
      - JYK_USER=${JYK_USER}
      - JYK_PASS=${JYK_PASS}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - FEISHU_WEBHOOK=${FEISHU_WEBHOOK}
    volumes:
      - ./data/option_tracker.db:/app/data/option_tracker.db
      - ./logs:/app/logs
      - ./backups:/app/backups
    restart: always

  nginx:
    image: nginx:alpine
    container_name: optionalpha_nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./frontend:/usr/share/nginx/html:ro
    depends_on:
      - app
    restart: always
```

### 6. 启动服务
```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f app

# 验证
curl http://localhost:8000/health
```

### 7. 配置域名和SSL
```bash
# 申请SSL证书
apt install certbot -y
certbot certonly --standalone -d your-domain.com

# 配置Nginx SSL
# (参考MIGRATION_CHECKLIST.md)
```

---

## 💾 备份策略 (SQLite)

### 方案1: 定时复制文件
```bash
# 创建备份脚本
cat > /opt/optionalpha/backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
cp /opt/optionalpha/data/option_tracker.db \
   /opt/optionalpha/backups/option_tracker_${DATE}.db

# 只保留最近7天
find /opt/optionalpha/backups -name "*.db" -mtime +7 -delete
EOF

chmod +x /opt/optionalpha/backup.sh

# 添加到crontab (每天3点)
echo "0 3 * * * /opt/optionalpha/backup.sh" | crontab -
```

### 方案2: 直接下载到本地
```bash
# 每周下载一次到本地Mac
scp root@your_server_ip:/opt/optionalpha/data/option_tracker.db \
    ~/Desktop/option_tracker_backup_$(date +%Y%m%d).db
```

---

## 📈 性能监控

### SQLite性能指标
```bash
# 查看数据库大小
ls -lh data/option_tracker.db

# 查看表数量
sqlite3 data/option_tracker.db "SELECT COUNT(*) FROM sqlite_master WHERE type='table';"

# 查询性能测试
time sqlite3 data/option_tracker.db "SELECT * FROM warehouse_receipts WHERE record_date='2024-12-16';"
```

预期性能:
- 查询时间: <10ms
- 数据库大小: 10-50MB
- CPU占用: <5%
- 内存占用: <100MB

---

## 🔄 升级到MySQL的时机

**只有以下情况才考虑升级**:

1. 数据库文件 >1GB
2. 并发写入需求 (多用户)
3. 需要读写分离
4. 查询响应时间 >100ms
5. 需要复杂的事务处理

**目前完全不需要！**

---

## ✅ 验收标准

### 部署成功标准
- [ ] 服务器访问正常 (http://your_server_ip:8000)
- [ ] API响应正常 (curl http://localhost:8000/health)
- [ ] 数据库查询正常 (sqlite3 data/option_tracker.db)
- [ ] 定时任务运行正常 (docker logs optionalpha_app)
- [ ] 域名访问正常 (https://your-domain.com)

### 性能达标
- [ ] API响应时间 <500ms
- [ ] 页面加载时间 <2s
- [ ] CPU占用 <10%
- [ ] 内存占用 <500MB

### 稳定性验证
- [ ] 连续运行7天无崩溃
- [ ] 数据准确性100%
- [ ] 备份正常执行

---

## 📞 常见问题

### Q1: SQLite会不会太慢？
**A**: 不会！您的数据量10MB，查询毫秒级。MySQL的优势在并发写入，您没有这个需求。

### Q2: SQLite会不会不安全？
**A**: 和MySQL一样安全。数据安全靠备份策略，不是数据库类型。

### Q3: 未来数据量大了怎么办？
**A**: SQLite支持TB级数据。您的年增长<50MB，10年才500MB，完全够用。

### Q4: 能不能多用户访问？
**A**: SQLite支持多用户**读取**，只是写入串行。您是定时任务写入，完全没问题。

### Q5: 会不会数据丢失？
**A**: 设置好备份策略（每天备份+本地下载），比MySQL更安全（单文件复制超简单）。

---

## 🎯 总结

### 核心优势
1. ✅ **成本低**: ¥64/月 vs ¥230/月
2. ✅ **部署快**: 半天 vs 2天
3. ✅ **维护简单**: 零配置 vs 需要DBA知识
4. ✅ **性能够用**: 毫秒级查询
5. ✅ **安全可靠**: 单文件备份超简单

### 适用场景 ✅
- 个人/小团队使用
- 数据量 <1GB
- 单用户系统
- 定时任务为主
- 读多写少

### 不适用场景 ❌
- 高并发写入 (您没有)
- 多用户同时修改 (您没有)
- TB级数据量 (您没有)

**结论**: SQLite完美适合您的系统！

---

**文档创建**: 2024-12-16
**最后更新**: 2024-12-16
**作者**: Claude
**用途**: SQLite简化部署方案说明
