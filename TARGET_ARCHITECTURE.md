# OptionAlpha 重构后目标架构

**创建时间**: 2024-12-16
**文档用途**: 定义重构后的目标状态,作为重构指导
**重要性**: ⭐⭐⭐⭐⭐

---

## 🎯 重构目标

### 核心目标
1. **代码部署云端化** - 减少本地资源占用
2. **数据存储云端化** - 提升数据安全性和访问性能
3. **架构优化** - 提升系统可维护性和扩展性
4. **功能增强** - 实现四维度深度分析

### 重构后预期收益
- ✅ 释放本地存储 260MB+
- ✅ 降低本地CPU/内存占用
- ✅ 支持远程访问
- ✅ 数据自动备份
- ✅ 系统稳定性提升
- ✅ 功能更强大

---

## 🏗️ 目标架构设计

### 架构图
```
                          ┌─────────────────────┐
                          │   域名 + HTTPS      │
                          │  your-domain.com    │
                          └──────────┬──────────┘
                                     │
                          ┌──────────▼──────────┐
                          │   Nginx (反向代理)   │
                          │   SSL证书           │
                          └──────────┬──────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              │                      │                      │
     ┌────────▼────────┐   ┌────────▼────────┐   ┌────────▼────────┐
     │ FastAPI应用     │   │  MySQL 8.0      │   │  对象存储OSS    │
     │ (Docker容器)    │   │  (云数据库RDS)  │   │  (图片/PDF)     │
     │                 │   │                 │   │                 │
     │ - API服务       │   │ - 主库          │   │ - 蓝图图片      │
     │ - 定时任务      │   │ - 自动备份      │   │ - 研报PDF       │
     │ - 数据爬虫      │   │ - 读写分离      │   │                 │
     └─────────────────┘   └─────────────────┘   └─────────────────┘
              │
     ┌────────▼────────┐
     │  Redis缓存      │
     │  (可选)         │
     └─────────────────┘
```

### 技术选型

#### 云服务商选择
**推荐**: 阿里云 / 腾讯云
**理由**:
- 国内访问速度快
- 文档完善,社区活跃
- 价格合理
- 服务稳定

#### 服务器配置
```yaml
类型: 轻量应用服务器
配置: 2核4GB 60GB SSD
系统: Ubuntu 22.04 LTS
带宽: 3Mbps (可升级)
成本: ¥60-80/月
```

#### 数据库方案
```yaml
方案: SQLite (推荐，继续使用)
  - 当前数据库: option_tracker.db (10MB)
  - 直接上传到云端服务器
  - 无需额外配置
  - 性能完全够用 (数据量小，单用户)
  - 成本: ¥0
  - 备份: 定时复制.db文件
```

**为什么选择SQLite？**
- ✅ 数据量小 (当前10MB，年增长<50MB)
- ✅ 单用户系统，无并发写入压力
- ✅ 读多写少，查询速度毫秒级
- ✅ 零维护成本，部署简单
- ✅ 完全免费

#### 文件存储
```yaml
方案: 对象存储OSS
用途:
  - 交易蓝图图片
  - 研报PDF文件
  - 数据库备份
成本: 按用量计费,预计¥5-10/月
```

---

## 📂 目录结构 (重构后)

```
optionalpha-cloud/
├── docker-compose.yml          # Docker编排
├── Dockerfile                  # 应用镜像
├── requirements.txt            # Python依赖
├── .env.production            # 生产环境变量
├── .env.example               # 环境变量示例
├── .dockerignore              # Docker忽略文件
├── .gitignore                 # Git忽略文件
│
├── app/                       # 应用主目录
│   ├── __init__.py
│   ├── main.py               # FastAPI入口
│   │
│   ├── core/                 # 核心模块
│   │   ├── config.py         # 配置管理
│   │   ├── database.py       # 数据库连接
│   │   └── security.py       # 安全认证
│   │
│   ├── api/                  # API路由 (重构)
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── virtual_real_ratio.py
│   │   │   ├── term_structure.py
│   │   │   ├── capital_position.py
│   │   │   ├── research_report.py
│   │   │   └── opportunity.py      # 新增:机会雷达
│   │   └── deps.py           # 依赖注入
│   │
│   ├── models/               # 数据模型
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── warehouse.py      # 虚实比模型
│   │   ├── position.py       # 席位模型
│   │   ├── report.py         # 研报模型
│   │   └── structure.py      # 新增:期限结构模型
│   │
│   ├── schemas/              # Pydantic Schema
│   │   ├── __init__.py
│   │   ├── virtual_real_ratio.py
│   │   ├── term_structure.py
│   │   └── opportunity.py
│   │
│   ├── services/             # 业务逻辑
│   │   ├── __init__.py
│   │   ├── virtual_real_ratio_service.py
│   │   ├── term_structure_service.py
│   │   ├── capital_service.py
│   │   ├── report_service.py
│   │   └── opportunity_service.py   # 新增:机会识别
│   │
│   ├── crawlers/             # 爬虫模块
│   │   ├── __init__.py
│   │   ├── base.py           # 爬虫基类
│   │   ├── zhihui.py
│   │   ├── jiaoyikecha.py
│   │   ├── uqer.py
│   │   └── decorators.py     # DataCollector装饰器
│   │
│   ├── tasks/                # 定时任务 (重构)
│   │   ├── __init__.py
│   │   ├── scheduler.py      # 调度器
│   │   ├── data_tasks.py     # 数据爬取任务
│   │   ├── analysis_tasks.py # 分析任务
│   │   └── backup_tasks.py   # 备份任务
│   │
│   └── utils/                # 工具函数
│       ├── __init__.py
│       ├── logger.py         # 日志工具
│       ├── cache.py          # 缓存工具
│       └── oss.py            # OSS上传工具
│
├── frontend/                 # 前端文件 (分离)
│   ├── index.html           # 总览
│   ├── virtual_real_ratio.html
│   ├── term_structure.html
│   ├── capital_position.html
│   ├── research_report.html
│   ├── opportunity_radar.html  # 新增:机会雷达
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   └── images/
│   └── components/          # Vue组件
│
├── migrations/              # 数据库迁移
│   ├── versions/
│   └── env.py
│
├── tests/                   # 测试文件
│   ├── __init__.py
│   ├── test_api/
│   ├── test_services/
│   └── test_crawlers/
│
├── scripts/                 # 脚本工具
│   ├── migrate_sqlite_to_mysql.py  # 数据迁移
│   ├── init_db.py                  # 数据库初始化
│   └── deploy.sh                   # 部署脚本
│
├── logs/                    # 日志目录
│   ├── app.log
│   ├── crawler.log
│   └── task.log
│
├── nginx/                   # Nginx配置
│   ├── nginx.conf
│   └── ssl/
│       ├── cert.pem
│       └── key.pem
│
└── docs/                    # 文档
    ├── API.md
    ├── DEPLOYMENT.md
    └── CHANGELOG.md
```

---

## 🗄️ 数据库设计 (重构后)

### SQLite 数据库 (继续使用)

**无需迁移！** 直接使用现有的 `option_tracker.db`

#### 新增表: term_structure_history (关键!)
```sql
CREATE TABLE term_structure_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comm_code VARCHAR(20) NOT NULL COMMENT '品种代码',
    variety_name VARCHAR(50) COMMENT '品种名称',
    record_date DATE NOT NULL COMMENT '记录日期',

    -- 结构信息
    market_structure VARCHAR(20) COMMENT '市场结构: 正向市场/反向市场',
    structure_type VARCHAR(20) COMMENT 'Contango/Backwardation',

    -- 价格数据
    near_month_contract VARCHAR(20) COMMENT '近月合约',
    near_month_price DECIMAL(10,2) COMMENT '近月价格',
    far_month_contract VARCHAR(20) COMMENT '远月合约',
    far_month_price DECIMAL(10,2) COMMENT '远月价格',

    -- 价差数据
    price_spread DECIMAL(10,2) COMMENT '价差(远月-近月)',
    spread_pct DECIMAL(10,4) COMMENT '价差百分比',

    -- 统计指标
    structure_score INT COMMENT '结构强度评分(0-100)',
    roll_yield DECIMAL(10,4),

    -- 合约详情JSON
    contracts_detail TEXT,  -- SQLite用TEXT存储JSON

    -- 时间戳
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX idx_ts_code_date ON term_structure_history(comm_code, record_date);
CREATE INDEX idx_ts_date ON term_structure_history(record_date);
CREATE INDEX idx_ts_structure ON term_structure_history(market_structure);
```

#### 新增表: opportunity_signals (机会信号)
```sql
CREATE TABLE opportunity_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comm_code VARCHAR(20) NOT NULL,
    variety_name VARCHAR(50),
    signal_date DATE NOT NULL,

    -- 四维度评分
    vr_ratio_score INT COMMENT '虚实比得分(0-100)',
    structure_score INT COMMENT '期限结构得分(0-100)',
    capital_score INT COMMENT '资金席位得分(0-100)',
    report_score INT COMMENT '研报评级得分(0-100)',

    -- 综合评分
    total_score INT COMMENT '总分',
    opportunity_level VARCHAR(10) COMMENT '机会等级: S/A/B/C',
    direction VARCHAR(10) COMMENT '方向: 多/空',

    -- 信号类型
    signal_type VARCHAR(50),
    signal_details TEXT,  -- SQLite用TEXT存储JSON

    -- 触发条件
    dimension_count INT,
    is_resonance INTEGER,  -- SQLite用INTEGER代替BOOLEAN (0/1)

    -- 时间戳
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX idx_op_code_date ON opportunity_signals(comm_code, signal_date);
CREATE INDEX idx_op_level ON opportunity_signals(opportunity_level);
CREATE INDEX idx_op_score ON opportunity_signals(total_score DESC);
```

#### 优化表: warehouse_receipts (增强)
```sql
ALTER TABLE warehouse_receipts
ADD COLUMN percentile_30d DECIMAL(5,2) COMMENT '30日百分位',
ADD COLUMN percentile_90d DECIMAL(5,2) COMMENT '90日百分位',
ADD COLUMN mean_30d DECIMAL(10,2) COMMENT '30日均值',
ADD COLUMN std_30d DECIMAL(10,2) COMMENT '30日标准差',
ADD COLUMN zscore DECIMAL(10,4) COMMENT 'Z-score',
ADD COLUMN change_rate_3d DECIMAL(10,4) COMMENT '3日变化率',
ADD COLUMN change_rate_7d DECIMAL(10,4) COMMENT '7日变化率',
ADD COLUMN acceleration DECIMAL(10,4) COMMENT '加速度',
ADD COLUMN signal_type VARCHAR(50) COMMENT '信号类型',
ADD COLUMN signal_score INT COMMENT '信号得分';
```

#### 优化表: research_reports (增强)
```sql
ALTER TABLE research_reports
ADD COLUMN institution_weight DECIMAL(5,2) COMMENT '机构权重',
ADD COLUMN consistency_score INT COMMENT '一致性得分',
ADD COLUMN trend VARCHAR(20) COMMENT '趋势: 上调/下调/持平';
```

**注意**: SQLite无需数据迁移！直接使用现有数据库文件。

---

## 🐳 Docker配置

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安装Playwright (如需要)
RUN pip install playwright==1.41.0 && \
    playwright install chromium && \
    playwright install-deps chromium

# 复制应用代码
COPY app/ ./app/
COPY frontend/ ./frontend/
COPY migrations/ ./migrations/
COPY scripts/ ./scripts/

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

### docker-compose.yml (SQLite简化版)
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
      - ./option_tracker.db:/app/data/option_tracker.db  # 挂载SQLite数据库
      - ./logs:/app/logs
      - ./backups:/app/backups  # 备份目录
    restart: always
    networks:
      - optionalpha_network

  nginx:
    image: nginx:alpine
    container_name: optionalpha_nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - ./frontend:/usr/share/nginx/html:ro
    depends_on:
      - app
    restart: always
    networks:
      - optionalpha_network

networks:
  optionalpha_network:
    driver: bridge
```

**简化说明**：
- ❌ 去掉MySQL容器 (使用SQLite)
- ❌ 去掉Redis容器 (暂不需要缓存)
- ✅ 直接挂载SQLite数据库文件
- ✅ 部署更简单，资源占用更低


### .env.production示例 (SQLite版)
```bash
# 数据库配置
DATABASE_URL=sqlite:////app/data/option_tracker.db

# 数据源Token
ZHIHUI_AUTH_TOKEN=your_token
UQER_TOKEN=your_token
JYK_USER=your_username
JYK_PASS=your_password

# API Keys
GEMINI_API_KEY=your_key
GEMINI_BASE_URL=https://www.apillm.online/v1

# 飞书告警
FEISHU_WEBHOOK=your_webhook

# OSS配置
OSS_ENDPOINT=oss-cn-shanghai.aliyuncs.com
OSS_ACCESS_KEY_ID=your_key_id
OSS_ACCESS_KEY_SECRET=your_secret
OSS_BUCKET_NAME=optionalpha

# 应用配置
DEBUG=False
LOG_LEVEL=INFO
WORKERS=2
```

---

## 🚀 部署流程

### Step 1: 服务器准备
```bash
# 1. 购买阿里云/腾讯云轻量服务器
#    配置: 2核4GB Ubuntu 22.04

# 2. SSH登录服务器
ssh root@your_server_ip

# 3. 更新系统
apt update && apt upgrade -y

# 4. 安装Docker
curl -fsSL https://get.docker.com | bash

# 5. 安装Docker Compose
apt install docker-compose -y

# 6. 创建应用目录
mkdir -p /opt/optionalpha
cd /opt/optionalpha
```

### Step 2: 代码部署
```bash
# 方式A: Git克隆 (推荐)
git clone <your_repo_url> .

# 方式B: 手动上传
# 本地执行:
rsync -avz --exclude='__pycache__' \
      --exclude='.git' \
      --exclude='backups' \
      --exclude='option_tracker.db' \
      ./ root@your_server_ip:/opt/optionalpha/
```

### Step 3: 数据库迁移
```bash
# 1. 本地导出SQLite数据
sqlite3 option_tracker.db .dump > full_export.sql

# 2. 上传到服务器
scp full_export.sql root@your_server_ip:/opt/optionalpha/

# 3. 服务器上启动MySQL
cd /opt/optionalpha
docker-compose up -d mysql

# 4. 等待MySQL启动 (约30秒)
sleep 30

# 5. 转换并导入数据
python3 scripts/migrate_sqlite_to_mysql.py
```

### Step 4: 配置环境变量
```bash
# 1. 创建生产环境配置
cp .env.example .env.production

# 2. 编辑配置
nano .env.production
# 填入实际的Token和密码

# 3. 生成Nginx SSL证书
certbot certonly --standalone -d your-domain.com
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/ssl/cert.pem
cp /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/ssl/key.pem
```

### Step 5: 启动服务
```bash
# 1. 构建并启动所有服务
docker-compose up -d

# 2. 查看日志
docker-compose logs -f app

# 3. 检查服务状态
docker-compose ps

# 4. 验证API
curl http://localhost:8000/health
```

### Step 6: 配置域名
```bash
# 1. 在域名服务商添加A记录
# your-domain.com -> your_server_ip

# 2. 等待DNS生效 (约10分钟)

# 3. 测试访问
curl https://your-domain.com/health
```

---

## 📊 功能增强清单

### Phase 1: 虚实比增强 ✅
- [x] 后端计算30日/90日百分位
- [x] 后端计算3日/7日变化率
- [x] 后端计算加速度
- [x] 后端计算Z-score
- [x] 信号识别: 极端退潮/加速/低位
- [x] 前端表格增加"历史位置"列
- [x] 前端增加"交易信号"模块
- [x] 详情卡片多维度展示

### Phase 2: 期限结构历史化 ✅
- [x] 创建term_structure_history表
- [x] 修改爬虫,每日保存到数据库
- [x] 计算结构持续天数
- [x] 计算价差变化率
- [x] 识别结构转换信号
- [x] 开发独立前端页面
- [x] 价差趋势图表

### Phase 3: 研报评级增强 ✅
- [x] 计算一致性指标
- [x] 识别评级变化信号
- [x] 识别分歧转一致
- [x] 前端一致性可视化
- [x] 评级变化时间轴

### Phase 4: 资金席位增强 ✅
- [x] 计算Top5集中度
- [x] 计算多空分歧度
- [x] 识别新增主力
- [x] 识别资金流入加速
- [x] 开发独立前端页面
- [x] 资金流向可视化

### Phase 5: 机会雷达 ✅
- [x] 创建opportunity_signals表
- [x] 四维度评分系统
- [x] 信号共振识别
- [x] S/A/B/C级分类
- [x] 开发opportunity_radar.html
- [x] 实时推送告警

---

## 🔒 安全增强

### API认证
```python
# app/core/security.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
```

### CORS配置
```python
# 生产环境限制CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com"],  # 只允许自己的域名
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

### 环境变量加密
```bash
# 使用密钥管理服务
# 阿里云: KMS
# 腾讯云: KMS
# AWS: Secrets Manager
```

---

## 📈 监控与日志

### 日志配置
```python
# app/utils/logger.py
import logging
from logging.handlers import RotatingFileHandler

def setup_logger():
    logger = logging.getLogger("optionalpha")
    logger.setLevel(logging.INFO)

    # 文件处理器 (自动轮转)
    file_handler = RotatingFileHandler(
        "logs/app.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )

    # 格式化
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    return logger
```

### 监控指标
- API响应时间
- 数据库查询性能
- 定时任务执行状态
- 爬虫成功率
- 系统资源使用率

---

## 💰 成本估算

### 月度成本 (方案A: 自建MySQL)
| 项目 | 配置 | 成本 |
|-----|------|------|
| 轻量服务器 | 2核4GB 60GB | ¥60 |
| 域名 | .com域名 | ¥4 (¥50/年) |
| SSL证书 | Let's Encrypt | ¥0 (免费) |
| OSS存储 | 10GB + 流量 | ¥5 |
| **总计** | | **¥69/月** |

### 年度成本
- 服务器: ¥60 × 12 = ¥720
- 域名: ¥50
- OSS: ¥5 × 12 = ¥60
- **总计**: ¥830/年

---

## ✅ 重构验收标准

### 功能验收
- [ ] 所有8个页面正常访问
- [ ] 所有API接口正常响应
- [ ] 10个定时任务正常执行
- [ ] 数据正常爬取和存储
- [ ] 增强功能全部实现

### 性能验收
- [ ] API响应时间 < 500ms
- [ ] 页面加载时间 < 2s
- [ ] 数据库查询 < 100ms
- [ ] 定时任务无遗漏

### 稳定性验收
- [ ] 连续运行7天无崩溃
- [ ] 数据准确性100%
- [ ] 告警推送及时
- [ ] 自动备份正常

---

**文档创建时间**: 2024-12-16
**最后更新**: 2024-12-16
**文档状态**: 目标架构定义,待实施
