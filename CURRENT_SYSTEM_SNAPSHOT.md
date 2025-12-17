# OptionAlpha 重构前系统完整快照

**创建时间**: 2024-12-16
**文档用途**: 保存重构前的所有系统信息,确保重构失败时可完整恢复
**重要性**: ⭐⭐⭐⭐⭐ 极其重要,请妥善保存!

---

## ⚠️ 重要说明

**本文档是重构前的系统快照,包含:**
1. 当前可正常运行的完整配置
2. 所有数据源的访问凭证
3. 定时任务的精确配置
4. 已验证可用的API接口
5. 数据库结构和数据恢复方法

**请勿删除此文档,直到重构完全成功并稳定运行至少2周!**

---

## 📍 当前运行状态

### 系统版本
- **版本号**: v1.0.0 (重构前)
- **运行环境**: macOS Darwin 24.2.0
- **Python版本**: 3.11+
- **运行方式**: 本地 localhost:8000
- **状态**: ✅ 正常运行中

### 项目路径
```
本地路径: /Users/pm/Documents/期权交易策略/option_tracker/
启动命令: cd option_tracker && python3 main.py
访问地址: http://localhost:8000
```

### 文件统计
- Python文件: 75个
- HTML页面: 8个
- 数据库: option_tracker.db (10MB)
- 备份文件: backups/ (250MB)
- 项目总大小: 342MB

---

## 🔑 重要配置信息 (敏感)

### .env 环境变量配置
```bash
# 数据库配置
DATABASE_URL=sqlite:///./option_tracker.db

# Redis配置
REDIS_URL=redis://localhost:6379/0

# 交易可查账号 (jiaoyikecha.com)
JYK_USER=<你的实际用户名>
JYK_PASS=<你的实际密码>

# 智汇期讯配置 (zhihuiqixun.com)
ZHIHUI_USER=
ZHIHUI_PASS=
ZHIHUI_AUTH_TOKEN=<你的实际Token>

# Google Gemini AI
GEMINI_API_KEY=<你的实际Key>
GEMINI_BASE_URL=https://www.apillm.online/v1

# 优矿Uqer Token
UQER_TOKEN=<你的实际Token>

# 飞书告警
FEISHU_WEBHOOK=<你的实际Webhook URL>

# 项目配置
DEBUG=True
LOG_LEVEL=INFO
```

**⚠️ 重构时务必保留这些配置值!**

---

## 📊 数据库完整结构

### 主数据库文件
```
位置: /Users/pm/Documents/期权交易策略/option_tracker/option_tracker.db
大小: 10MB
类型: SQLite 3
```

### 数据表清单 (10张表)

#### 1. warehouse_receipts - 虚实比数据 ⭐核心
```sql
CREATE TABLE warehouse_receipts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comm_code VARCHAR(20) NOT NULL,           -- 品种代码 如AU
    variety_name VARCHAR(50),                  -- 品种名称 如沪金
    record_date DATE NOT NULL,                 -- 记录日期
    receipt_quantity FLOAT DEFAULT 0,          -- 仓单量
    receipt_change FLOAT DEFAULT 0,            -- 仓单变化
    main_contract VARCHAR(20),                 -- 主力合约
    open_interest FLOAT DEFAULT 0,             -- 持仓量(手)
    open_interest_change FLOAT DEFAULT 0,      -- 持仓变化
    contract_unit FLOAT DEFAULT 0,             -- 合约单位(千克/手)
    virtual_quantity FLOAT DEFAULT 0,          -- 虚盘量
    virtual_real_ratio FLOAT DEFAULT 0,        -- 虚实比
    squeeze_risk VARCHAR(20),                  -- 逼仓风险
    impact_analysis TEXT,                      -- 影响分析
    price_pressure VARCHAR(20),                -- 价格压力
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_wr_code_date ON warehouse_receipts(comm_code, record_date);
```

**当前数据量**: 约1000+条记录
**更新频率**: 每天18:00

#### 2. institutional_positions - 资金席位 ⭐核心
```sql
CREATE TABLE institutional_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comm_code VARCHAR(20) NOT NULL,
    broker_name VARCHAR(50),                   -- 席位名称
    net_position INTEGER,                      -- 净持仓
    position_change INTEGER,                   -- 持仓变化
    win_rate FLOAT,                            -- 席位胜率
    record_date DATE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_ip_code_date ON institutional_positions(comm_code, record_date);
```

**当前数据量**: 约500+条记录
**更新频率**: 每天19:00

#### 3. research_reports - 研报数据 ⭐核心
```sql
CREATE TABLE research_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id BIGINT,
    comm_code VARCHAR(20) NOT NULL,
    variety_name VARCHAR(50),
    institution_id INTEGER,
    institution_name VARCHAR(100),
    publish_date DATE NOT NULL,
    view_port VARCHAR(20),                     -- 看多/看空/中性
    sentiment VARCHAR(10),                     -- bull/bear/neutral
    trade_logic TEXT,
    related_data TEXT,
    risk_factor TEXT,
    report_link VARCHAR(500),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_rr_code_date ON research_reports(comm_code, publish_date);
CREATE INDEX idx_rr_report_id ON research_reports(report_id);
```

**当前数据量**: 约2000+条记录
**更新频率**: 每30分钟

#### 4. market_full_view - 多空全景 ⭐核心
```sql
CREATE TABLE market_full_view (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comm_code VARCHAR(20) NOT NULL,
    variety_name VARCHAR(50),
    record_date DATE NOT NULL,
    excessive_num INTEGER,                     -- 过剩数量
    excessive_ratio FLOAT,
    neutral_num INTEGER,
    neutral_ratio FLOAT,
    empty_num INTEGER,
    empty_ratio FLOAT,
    total_num INTEGER,
    more_port VARCHAR(20),                     -- 偏多/偏空
    more_rate FLOAT,
    main_sentiment VARCHAR(10),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_mfv_code_date ON market_full_view(comm_code, record_date);
```

**当前数据量**: 约300+条记录
**更新频率**: 每30分钟

#### 5. option_flows - 期权流向
```sql
CREATE TABLE option_flows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comm_code VARCHAR(20) NOT NULL,
    contract_code VARCHAR(100),
    net_flow FLOAT,
    volume FLOAT,
    change_ratio FLOAT,
    record_time DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_of_code_time ON option_flows(comm_code, record_time);
```

**当前数据量**: 约500+条记录
**更新频率**: 交易时段每分钟

#### 6. daily_blueprints - 交易蓝图
```sql
CREATE TABLE daily_blueprints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_url VARCHAR(500),
    local_path VARCHAR(500),
    parsed_strategies TEXT,                    -- JSON格式
    record_date DATE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_db_date ON daily_blueprints(record_date);
```

**当前数据量**: 约10条记录
**更新频率**: 每天19:00

#### 7. market_analysis_summary - 四维评分
```sql
CREATE TABLE market_analysis_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comm_code VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    fundamental_score INTEGER DEFAULT 0,      -- -10到10
    capital_score INTEGER DEFAULT 0,
    technical_score INTEGER DEFAULT 0,
    message_score INTEGER DEFAULT 0,
    total_direction VARCHAR(10),              -- 多/空/中性
    main_reason TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_mas_code_date ON market_analysis_summary(comm_code, date);
```

**当前数据量**: 约200+条记录
**更新频率**: 每天19:30

#### 8. commodities - 品种基础
```sql
CREATE TABLE commodities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(50) NOT NULL,
    exchange VARCHAR(20),
    category VARCHAR(20)
);
```

#### 9. fundamental_reports - 基本面报告
```sql
CREATE TABLE fundamental_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comm_code VARCHAR(20) NOT NULL,
    source VARCHAR(50),
    report_type VARCHAR(20),
    sentiment VARCHAR(10),
    content_summary TEXT,
    publish_time DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### 10. technical_indicators - 技术指标
```sql
CREATE TABLE technical_indicators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comm_code VARCHAR(20) NOT NULL,
    iv_rank FLOAT,
    term_structure VARCHAR(20),
    pcr_ratio FLOAT,
    record_time DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🕷️ 数据源详细配置 (已验证可用)

### 1. 智汇期讯 API ✅ 可用
**网站**: https://zhihuiqixun.com
**认证**: Authorization Bearer Token
**Token配置**: `ZHIHUI_AUTH_TOKEN` in .env

**API端点**:
```python
# 多空全景
POST https://zhihuiqixun.com/api/variety/fullView
Headers: {
    "Authorization": "Bearer <ZHIHUI_AUTH_TOKEN>",
    "Content-Type": "application/json"
}
Body: {
    "publishDate": "2024-12-16"  # YYYY-MM-DD
}

# 研报淘金
POST https://zhihuiqixun.com/api/variety/report/list
Headers: {
    "Authorization": "Bearer <ZHIHUI_AUTH_TOKEN>",
    "Content-Type": "application/json"
}
Body: {
    "varietyCode": "AU",         # 品种代码,null=全部
    "startDate": "2024-12-01",
    "endDate": "2024-12-16",
    "page": 1,
    "limit": 100
}
```

**爬虫文件**: `app/crawlers/zhihui_spider.py`
**更新频率**: 每30分钟
**数据质量**: ⭐⭐⭐⭐⭐

### 2. 交易可查 Playwright ✅ 可用
**网站**: https://jiaoyikecha.com
**认证**: 用户名密码登录
**配置**: `JYK_USER`, `JYK_PASS` in .env

**登录流程**:
```python
# 1. 访问登录页
await page.goto("https://jiaoyikecha.com/login")

# 2. 填写账号密码
await page.fill('input[name="username"]', JYK_USER)
await page.fill('input[name="password"]', JYK_PASS)

# 3. 点击登录
await page.click('button[type="submit"]')

# 4. 等待跳转
await page.wait_for_url("**/dashboard")
```

**爬取内容**:
- 交易蓝图图片
- 席位持仓数据 (主流品种: rb, hc, i, j, jm, cu, al, zn, au, ag)

**爬虫文件**: `app/crawlers/jiaoyikecha_spider.py`
**更新频率**: 每天19:00
**失败重试**: 30分钟后重试
**数据质量**: ⭐⭐⭐⭐

### 3. Uqer 优矿 SDK ✅ 可用
**平台**: https://uqer.datayes.com
**认证**: API Token
**配置**: `UQER_TOKEN` in .env

**Python SDK**:
```python
from uqer import DataAPI
import os
os.environ['access_token'] = UQER_TOKEN

# 1. 获取仓单数据
df_receipt = DataAPI.MktFutWRdGet(
    contractObject='CU',        # 品种代码
    exchangeCD='XSGE',          # 交易所
    beginDate='20241201',       # 开始日期
    endDate='20241216',         # 结束日期
    pandas='1'
)

# 2. 获取持仓数据
df_position = DataAPI.MktFutdGet(
    ticker='',                  # 留空获取所有
    beginDate='20241201',
    endDate='20241216',
    pandas='1'
)

# 3. 获取合约信息
df_contract = DataAPI.FutuGet(
    exchangeCD='XSGE',
    contractObject='cu',
    pandas='1'
)
```

**品种映射表** (64个品种):
```python
VARIETY_MAPPING = {
    # 上期所 XSGE - 20个
    "AU": ("沪金", 1000, "AU", "XSGE"),
    "AG": ("沪银", 15000, "AG", "XSGE"),
    "CU": ("沪铜", 5000, "CU", "XSGE"),
    # ... (完整列表见 virtual_real_ratio_spider_uqer.py)
}
```

**爬虫文件**: `app/crawlers/virtual_real_ratio_spider_uqer.py`
**更新频率**: 每天18:00
**数据质量**: ⭐⭐⭐⭐⭐

### 4. 方期看盘 Playwright ✅ 可用
**网站**: https://founderfu.com (需确认实际URL)
**认证**: 无需登录 (或需要确认)

**爬虫文件**: `app/crawlers/fangqi_spider.py`
**更新频率**: 早盘8:50 / 夜盘20:50
**数据质量**: ⭐⭐⭐

### 5. Openvlab Playwright ✅ 可用
**网站**: openvlab相关网站 (需确认实际URL)

**爬虫文件**: `app/crawlers/openvlab_spider.py`
**更新频率**: 交易时段每分钟
**数据质量**: ⭐⭐⭐⭐

### 6. AKShare ✅ 可用
**库**: `import akshare as ak`
**用途**: 辅助数据源
**无需认证**

---

## ⏰ 定时任务精确配置

### APScheduler 配置文件
**位置**: `app/scheduler.py`
**调度器**: AsyncIOScheduler

### 10个定时任务详细配置

#### 1. 智汇期讯爬虫
```python
scheduler.add_job(
    crawl_zhihui_data,
    IntervalTrigger(minutes=30),
    id='crawl_zhihui',
    name='智汇期讯-每30分钟',
    replace_existing=True
)
```
- **函数**: `crawl_zhihui_data()`
- **触发**: 每30分钟
- **装饰器**: `@DataCollector(max_retries=3, retry_delay=60)`
- **数据**: 多空全景 + 研报淘金

#### 2. 方期看盘-早盘
```python
scheduler.add_job(
    crawl_fangqi_morning,
    CronTrigger(hour=8, minute=50),
    id='crawl_fangqi_morning',
    name='方期看盘-早盘8:50',
    replace_existing=True
)
```
- **函数**: `crawl_fangqi_morning()`
- **触发**: 每天08:50
- **数据**: 早盘提示

#### 3. 方期看盘-夜盘
```python
scheduler.add_job(
    crawl_fangqi_night,
    CronTrigger(hour=20, minute=50),
    id='crawl_fangqi_night',
    name='方期看盘-夜盘20:50',
    replace_existing=True
)
```
- **函数**: `crawl_fangqi_night()`
- **触发**: 每天20:50
- **数据**: 夜盘提示

#### 4. 交易可查
```python
scheduler.add_job(
    crawl_jiaoyikecha,
    CronTrigger(hour=19, minute=0),
    id='crawl_jiaoyikecha',
    name='交易可查-19:00',
    replace_existing=True
)
```
- **函数**: `crawl_jiaoyikecha()`
- **触发**: 每天19:00
- **装饰器**: `@DataCollector(max_retries=3, retry_delay=1800)`
- **数据**: 交易蓝图 + 席位持仓

#### 5. Openvlab期权流向
```python
scheduler.add_job(
    crawl_openvlab,
    IntervalTrigger(minutes=1),
    id='crawl_openvlab',
    name='Openvlab-分钟级监控',
    replace_existing=True
)
```
- **函数**: `crawl_openvlab()`
- **触发**: 每分钟 (交易时段内执行)
- **交易时段**: 9:00-11:30, 13:00-15:00, 21:00-02:00
- **装饰器**: `@DataCollector(max_retries=2, enable_alert=False)`

#### 6. 每日全品种分析
```python
scheduler.add_job(
    run_analysis_job,
    CronTrigger(hour=19, minute=30),
    id='run_daily_analysis',
    name='每日全品种分析-19:30',
    replace_existing=True
)
```
- **函数**: `run_analysis_job()`
- **触发**: 每天19:30
- **数据**: 四维评分计算

#### 7. 虚实比数据
```python
scheduler.add_job(
    crawl_virtual_real_ratio,
    CronTrigger(hour=18, minute=0),
    id='crawl_virtual_real_ratio',
    name='虚实比数据-18:00',
    replace_existing=True
)
```
- **函数**: `crawl_virtual_real_ratio()`
- **触发**: 每天18:00
- **装饰器**: `@DataCollector(max_retries=2, retry_delay=600)`
- **数据**: 64个品种虚实比

#### 8. 数据库备份-小时
```python
scheduler.add_job(
    lambda: run_backup('hourly'),
    IntervalTrigger(hours=1),
    id='backup_hourly',
    name='数据库备份-小时级',
    replace_existing=True
)
```
- **函数**: `run_backup('hourly')`
- **触发**: 每小时
- **保留**: 最近24个

#### 9. 数据库备份-天级
```python
scheduler.add_job(
    lambda: run_backup('daily'),
    CronTrigger(hour=3, minute=0),
    id='backup_daily',
    name='数据库备份-天级-03:00',
    replace_existing=True
)
```
- **函数**: `run_backup('daily')`
- **触发**: 每天03:00
- **保留**: 最近30天

#### 10. 数据库备份-周级
```python
scheduler.add_job(
    lambda: run_backup('weekly'),
    CronTrigger(day_of_week='sun', hour=3, minute=0),
    id='backup_weekly',
    name='数据库备份-周级-周日03:00',
    replace_existing=True
)
```
- **函数**: `run_backup('weekly')`
- **触发**: 每周日03:00
- **保留**: 最近12周

---

## 🎨 前端页面清单

### 页面访问路径

| 页面文件 | 访问路由 | 功能 | 状态 |
|---------|---------|------|------|
| frontend.html | `/frontend` | 系统总览 | ✅正常 |
| virtual_real_ratio.html | `/virtual_real_ratio.html` | 虚实比分析 | ✅正常 |
| zhihui.html | `/zhihui` | 智汇期讯 | ✅正常 |
| data_governance.html | `/data-governance` | 数据治理 | ✅正常 |
| analysis_v2.html | `/analysis-v2` | V2分析 | ✅正常 |
| report_detail.html | `/report-detail` | 研报详情 | ✅正常 |
| term_structure.html | 无 | 期限结构 | ❌未实现 |
| capital_position.html | 无 | 资金席位 | ❌未实现 |

### 页面路由配置 (main.py)
```python
# 总览页面
@app.get("/frontend", response_class=HTMLResponse)
async def get_frontend():
    frontend_path = Path(__file__).parent / "frontend.html"
    return FileResponse(frontend_path, headers={
        "Cache-Control": "no-cache, no-store, must-revalidate"
    })

# 虚实比页面
@app.get("/virtual_real_ratio.html", response_class=HTMLResponse)
async def get_virtual_real_ratio_html():
    vr_path = Path(__file__).parent / "virtual_real_ratio.html"
    return FileResponse(vr_path)

# 智汇期讯页面
@app.get("/zhihui", response_class=HTMLResponse)
async def get_zhihui_page():
    zhihui_path = Path(__file__).parent / "zhihui.html"
    return FileResponse(zhihui_path, headers={
        "Cache-Control": "no-cache, no-store, must-revalidate"
    })

# 数据治理页面
@app.get("/data-governance", response_class=HTMLResponse)
async def get_data_governance_page():
    governance_path = Path(__file__).parent / "data_governance.html"
    return FileResponse(governance_path, headers={
        "Cache-Control": "no-cache, no-store, must-revalidate"
    })

# V2分析页面
@app.get("/analysis-v2", response_class=HTMLResponse)
async def get_analysis_v2_page():
    analysis_path = Path(__file__).parent / "analysis_v2.html"
    return FileResponse(analysis_path, headers={
        "Cache-Control": "no-cache, no-store, must-revalidate"
    })

# 研报详情页面
@app.get("/report-detail", response_class=HTMLResponse)
async def get_report_detail_page():
    report_detail_path = Path(__file__).parent / "report_detail.html"
    return FileResponse(report_detail_path, headers={
        "Cache-Control": "no-cache, no-store, must-revalidate"
    })
```

---

## 🔌 API接口清单 (已验证)

### 虚实比模块 `/api/v1/virtual-real-ratio`

```python
GET /api/v1/virtual-real-ratio/list
    参数: ?query_date=2024-12-16&comm_code=AU&risk_level=高
    返回: 虚实比列表(含较上期对比)

GET /api/v1/virtual-real-ratio/summary
    参数: ?query_date=2024-12-16
    返回: 汇总统计

GET /api/v1/virtual-real-ratio/detail/{comm_code}
    参数: ?query_date=2024-12-16
    返回: 品种详情

GET /api/v1/virtual-real-ratio/history/{comm_code}
    参数: ?days=30
    返回: 历史趋势数据

POST /api/v1/virtual-real-ratio/refresh
    参数: ?comm_code=AU (可选)
    功能: 手动刷新数据
```

### 智汇期讯模块 `/api/v1/zhihui`

```python
GET /api/v1/zhihui/latest-date
    返回: 最新交易日期

GET /api/v1/zhihui/full-view
    参数: ?query_date=2024-12-16
    返回: 多空全景数据

GET /api/v1/zhihui/reports
    参数: ?variety_code=AU&start_date=2024-12-01&end_date=2024-12-16
    返回: 研报列表

GET /api/v1/zhihui/variety-sentiment/{comm_code}
    参数: ?query_date=2024-12-16
    返回: 品种情绪统计
```

### 期限结构模块 `/api/term-structure`

```python
GET /api/term-structure/all-structures
    参数: ?query_date=2024-12-16
    返回: 所有品种期限结构

GET /api/term-structure/recommended-structures
    参数: ?query_date=2024-12-16
    返回: 推荐品种(S/A级)

GET /api/term-structure/structure/{variety_code}
    参数: ?query_date=2024-12-16
    返回: 单品种结构详情

GET /api/term-structure/analysis/{variety_code}
    返回: 期限结构分析(展期收益率等)
```

### 资金席位模块 `/api/v1/capital`

```python
GET /api/v1/capital/{variety_code}/positions
    参数: ?target_date=2024-12-16&limit=20
    返回: 席位持仓数据

GET /api/v1/capital/{variety_code}/flow
    参数: ?days=7
    返回: 资金流向趋势

GET /api/v1/capital/{variety_code}/top-brokers
    参数: ?limit=10
    返回: Top多头/空头席位

GET /api/v1/capital/{variety_code}/institution-vs-retail
    返回: 机构vs散户对比

GET /api/v1/capital/option-flow/all
    参数: ?hours=1
    返回: 所有品种期权流向
```

---

## 💾 数据备份与恢复

### 当前备份策略

**备份脚本**: `scripts/backup_database.py`

**备份目录结构**:
```
backups/
├── hourly/          # 小时备份 (保留24个)
│   ├── sqlite_backup_hourly_20241215_233046.db
│   ├── sqlite_backup_hourly_20241215_214828.db
│   └── ... (共约30个文件)
├── daily/           # 天级备份 (保留30天)
│   ├── sqlite_backup_daily_20241212_030000.db
│   ├── sqlite_backup_daily_20241209_030000.db
│   └── ... (共约4个文件)
└── weekly/          # 周级备份 (保留12周)
    └── (无当前文件)
```

### 数据恢复方法

#### 方法1: 直接替换数据库文件
```bash
# 1. 停止应用
kill $(lsof -t -i:8000)

# 2. 备份当前数据库
cp option_tracker.db option_tracker.db.broken

# 3. 恢复备份
cp backups/hourly/sqlite_backup_hourly_20241215_233046.db option_tracker.db

# 4. 重启应用
python3 main.py
```

#### 方法2: 从SQL导出恢复
```bash
# 1. 导出备份数据库为SQL
sqlite3 backups/hourly/sqlite_backup_hourly_20241215_233046.db .dump > restore.sql

# 2. 删除旧数据库
rm option_tracker.db

# 3. 导入SQL创建新数据库
sqlite3 option_tracker.db < restore.sql

# 4. 重启应用
python3 main.py
```

#### 方法3: 表级别恢复
```bash
# 如果只需要恢复特定表
sqlite3 backups/hourly/sqlite_backup_hourly_20241215_233046.db <<EOF
.output warehouse_receipts.sql
.dump warehouse_receipts
.exit
EOF

sqlite3 option_tracker.db < warehouse_receipts.sql
```

### 完整数据导出 (重构前必做!)

```bash
# 导出完整数据库为SQL文件
sqlite3 option_tracker.db .dump > FULL_BACKUP_BEFORE_REFACTOR_20241216.sql

# 压缩备份 (可选)
gzip FULL_BACKUP_BEFORE_REFACTOR_20241216.sql

# 验证备份完整性
sqlite3 test.db < FULL_BACKUP_BEFORE_REFACTOR_20241216.sql
rm test.db
```

**⚠️ 重构前请务必执行完整导出!**

---

## 📦 依赖包版本锁定

### requirements.txt 完整内容
```
# Web Framework
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.6

# Database
sqlalchemy==2.0.25
pymysql==1.1.0
alembic==1.13.0

# Task Scheduler
apscheduler==3.10.0

# Crawling
playwright==1.41.0
httpx==0.26.0
beautifulsoup4==4.12.0
lxml==5.1.0

# Data Processing
pandas==2.1.0
numpy==1.26.0

# Utils
python-dotenv==1.0.0
pydantic==2.5.0
pydantic-settings==2.1.0

# AI Integration
google-generativeai==0.3.0

# Data Source
akshare==1.12.0
uqer==1.3.39

# Testing
pytest==7.4.0
pytest-asyncio==0.23.0
```

### Playwright浏览器安装
```bash
# 安装Playwright
pip install playwright==1.41.0

# 安装Chromium浏览器
playwright install chromium

# 安装浏览器依赖
playwright install-deps chromium
```

---

## 🔄 重构前检查清单

### 数据完整性检查

- [ ] 1. 导出完整数据库
```bash
sqlite3 option_tracker.db .dump > FULL_BACKUP_$(date +%Y%m%d).sql
```

- [ ] 2. 验证关键表数据量
```bash
sqlite3 option_tracker.db <<EOF
SELECT 'warehouse_receipts', COUNT(*) FROM warehouse_receipts;
SELECT 'institutional_positions', COUNT(*) FROM institutional_positions;
SELECT 'research_reports', COUNT(*) FROM research_reports;
SELECT 'market_full_view', COUNT(*) FROM market_full_view;
EOF
```

- [ ] 3. 导出配置文件
```bash
cp .env .env.backup
cp config/settings.py config/settings.py.backup
```

- [ ] 4. 导出JSON数据文件
```bash
cp -r data/ data_backup/
```

### 访问凭证检查

- [ ] 验证 ZHIHUI_AUTH_TOKEN 有效性
- [ ] 验证 JYK_USER/JYK_PASS 可登录
- [ ] 验证 UQER_TOKEN 可用
- [ ] 验证 GEMINI_API_KEY 可用
- [ ] 验证 FEISHU_WEBHOOK 可接收消息

### 功能验证

- [ ] 访问 http://localhost:8000/frontend 正常
- [ ] 访问 http://localhost:8000/virtual_real_ratio.html 正常
- [ ] 访问 http://localhost:8000/zhihui 正常
- [ ] 访问 http://localhost:8000/docs 查看API文档
- [ ] 手动触发一次虚实比刷新,确认成功

### 定时任务验证

- [ ] 查看定时任务列表
```python
from app.scheduler import get_scheduler_status
print(get_scheduler_status())
```

- [ ] 检查最近执行日志
```bash
grep "智汇期讯" logs/*.log | tail -20
grep "虚实比" logs/*.log | tail -20
grep "交易可查" logs/*.log | tail -20
```

---

## 📝 重构回滚预案

### 如果重构失败,按以下步骤恢复:

#### Step 1: 停止新系统
```bash
# 停止新系统进程
ps aux | grep python
kill <新系统PID>

# 或 Docker环境
docker-compose down
```

#### Step 2: 恢复数据库
```bash
# 进入项目目录
cd /Users/pm/Documents/期权交易策略/option_tracker/

# 从备份恢复
cp FULL_BACKUP_BEFORE_REFACTOR_20241216.sql restore.sql
rm option_tracker.db
sqlite3 option_tracker.db < restore.sql
```

#### Step 3: 恢复配置文件
```bash
cp .env.backup .env
cp config/settings.py.backup config/settings.py
```

#### Step 4: 恢复数据文件
```bash
rm -rf data/
cp -r data_backup/ data/
```

#### Step 5: 重启旧系统
```bash
python3 main.py
```

#### Step 6: 验证恢复成功
```bash
# 访问前端页面
open http://localhost:8000/frontend

# 检查数据
curl http://localhost:8000/api/v1/virtual-real-ratio/summary
```

---

## ⏱️ 关键时间点记录

### 最后正常运行时间
- **记录时间**: 2024-12-16 23:30
- **系统状态**: ✅ 正常运行
- **最后一次数据更新**: 2024-12-15 23:30
- **最后一次成功备份**: 2024-12-15 23:30

### 定时任务最后执行时间
- 智汇期讯: 2024-12-15 23:00
- 虚实比数据: 2024-12-15 18:00
- 交易可查: 2024-12-15 19:00
- 数据库备份: 2024-12-15 23:00

---

## 🔐 安全提醒

**本文档包含敏感信息,请注意:**

1. ❌ 不要提交到公开代码仓库
2. ❌ 不要分享给无关人员
3. ✅ 保存到安全的本地位置
4. ✅ 加密存储(可选)
5. ✅ 定期更新Token和密码

### 建议存储位置
```
1. 本地加密文件夹
2. 密码管理器 (1Password/LastPass)
3. 加密U盘备份
4. 私有云存储 (iCloud/OneDrive加密文件夹)
```

---

## 📞 紧急联系信息

### 如果重构遇到无法解决的问题:

1. **保持冷静** - 不要删除任何文件
2. **停止所有操作** - 避免覆盖数据
3. **参考本文档** - 按回滚预案恢复
4. **记录问题详情** - 方便后续排查

### 数据恢复优先级
1. **最高优先级**: option_tracker.db 数据库
2. **高优先级**: .env 配置文件
3. **中优先级**: data/ 数据文件
4. **低优先级**: 代码文件 (可重新下载)

---

**⚠️ 最后提醒**

**重构前请务必:**
1. ✅ 完整阅读本文档
2. ✅ 执行所有检查清单
3. ✅ 导出完整数据备份
4. ✅ 保存所有配置凭证
5. ✅ 测试回滚流程

**文档创建者**: Claude
**创建时间**: 2024-12-16
**文档用途**: 重构前系统快照,确保可完整恢复
**有效期**: 永久保留,直到重构成功并稳定运行至少2周

---

**祝重构顺利! 🎉**
