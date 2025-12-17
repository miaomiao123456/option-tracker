# OptionAlpha - 期货期权交易四维分析系统

## 📋 产品概述

**项目名称**: OptionAlpha (期权交易跟踪器)
**版本**: v1.0.0
**定位**: 期货期权交易多维度数据分析与交易机会识别系统
**架构**: FastAPI + SQLite + Vue3 + Element Plus + ECharts

### 核心价值
通过**四维度数据分析**(虚实比、期限结构、资金席位、研报评级)，自动识别高胜率交易机会，辅助期货期权交易决策。

---

## 📊 系统现状

### 项目规模
- **Python文件**: 75个
- **HTML前端页面**: 8个
- **数据库大小**: 10MB (主库) + 250MB (备份)
- **项目总大小**: 342MB
- **数据表**: 10+张表
- **品种覆盖**: 64个期货品种

### 技术栈
```yaml
后端框架: FastAPI 0.109+
数据库: SQLite (生产环境建议MySQL/PostgreSQL)
任务调度: APScheduler 3.10+
爬虫引擎: Playwright + httpx + BeautifulSoup4
数据处理: Pandas + NumPy
AI集成: Google Gemini API
数据源SDK: AKShare + Uqer (优矿)
前端: Vue 3 + Element Plus + ECharts 5
```

### 部署方式
- **当前**: 本地运行 (localhost:8000)
- **启动命令**: `uvicorn main:app --host 0.0.0.0 --port 8000 --reload`
- **定时任务**: 10个自动任务 (智汇期讯/交易可查/虚实比等)

---

## 🎯 四维度数据分析体系

### 1. 虚实比维度 (情绪面)
**定义**: 持仓量与可交割仓单的比值，衡量市场投机情绪和逼仓风险

**数据来源**:
- 仓单数据: Uqer API (`DataAPI.MktFutWRdGet`)
- 持仓数据: Uqer API (`DataAPI.MktFutdGet`)

**计算公式**:
```
虚实比 = 主力合约持仓量(手) ÷ 仓单量
```

**风险分级**:
- 虚实比 > 100: 高风险 (极高逼仓风险)
- 虚实比 50-100: 中风险 (存在逼仓风险)
- 虚实比 20-50: 低风险 (相对平衡)
- 虚实比 < 20: 无风险 (库存充足)

**已有指标**:
- ✅ 当前虚实比
- ✅ 仓单量/持仓量
- ✅ 较前日变化(绝对值/百分比)
- ✅ 逼仓风险等级
- ✅ 价格压力判断
- ✅ 历史趋势(30-365天)

**缺失指标** (待实现):
- ❌ 历史百分位数 (30日/90日)
- ❌ 变化率 (3日/7日)
- ❌ 加速度指标
- ❌ 标准差区间
- ❌ 情绪退潮信号
- ❌ 情绪加速信号

**数据表**: `warehouse_receipts`
**API接口**:
- `/api/v1/virtual-real-ratio/list` - 列表查询
- `/api/v1/virtual-real-ratio/summary` - 汇总统计
- `/api/v1/virtual-real-ratio/detail/{comm_code}` - 品种详情
- `/api/v1/virtual-real-ratio/history/{comm_code}` - 历史趋势
- `/api/v1/virtual-real-ratio/refresh` - 手动刷新

**前端页面**: `virtual_real_ratio.html`

**更新频率**: 每天18:00自动爬取

---

### 2. 期限结构维度 (方向面)
**定义**: 近月合约与远月合约的价格关系，判断市场对未来预期

**结构类型**:
- **Contango (正向市场)**: 远月 > 近月，供应充裕，做空机会
- **Backwardation (反向市场)**: 近月 > 远月，供应紧张，做多机会

**数据来源**:
- 合约价格: Uqer API (`DataAPI.MktFutdGet`)
- 主力合约识别: 按持仓量自动筛选

**已有指标**:
- ✅ Contango/Backwardation分类
- ✅ 结构描述
- ✅ 交易建议 (做多/做空)
- ✅ 交易理由
- ✅ 所有合约价格序列
- ✅ 展期收益率计算
- ✅ 套利机会识别

**缺失指标** (待实现):
- ❌ **历史结构数据** (关键!)
- ❌ 结构转换信号 (Contango↔Back)
- ❌ 价差变化率 (3日/7日)
- ❌ 结构持续天数
- ❌ 价差历史分位数
- ❌ 结构强度评分

**数据存储**:
- ⚠️ **当前**: JSON文件 (每次覆盖，无历史)
  - `data/term_structure_data.json` (推荐品种)
  - `data/term_structure_data_all.json` (全品种)
- ⚠️ **问题**: 无法判断结构转换
- ✅ **建议**: 改为数据库存储

**API接口**:
- `/api/term-structure/all-structures` - 所有品种结构
- `/api/term-structure/recommended-structures` - 推荐品种(S/A级)
- `/api/term-structure/structure/{variety_code}` - 单品种结构
- `/api/term-structure/analysis/{variety_code}` - 结构分析

**前端页面**: ❌ 无独立页面 (需新增)

**更新频率**: 每天20:48更新 (定时任务待确认)

---

### 3. 资金席位维度 (力量面)
**定义**: 大型机构资金流向，判断主力行为和资金力量

**数据来源**:
- ⚠️ **待确认**: `institutional_positions` 表
- 可能来源: 交易可查网站爬虫

**已有指标**:
- ✅ 席位持仓数据 (broker_name, net_position)
- ✅ 持仓变化 (position_change)
- ✅ Top多头/空头席位
- ✅ 资金流向趋势 (7天)
- ✅ 机构vs散户对比

**缺失指标** (待实现):
- ❌ 集中度指标 (Top5占比)
- ❌ 多空分歧度
- ❌ 新增主力识别
- ❌ 资金流入加速度
- ❌ 一致性做多/做空信号

**数据表**: `institutional_positions`
**API接口**:
- `/api/v1/capital/{variety_code}/positions` - 席位持仓
- `/api/v1/capital/{variety_code}/flow` - 资金流向
- `/api/v1/capital/{variety_code}/top-brokers` - Top席位
- `/api/v1/capital/{variety_code}/institution-vs-retail` - 机构vs散户

**前端页面**: ❌ 无独立页面 (需新增)

**更新频率**: 每天19:00 (交易可查爬虫)

**⚠️ 关键问题**:
- 需确认数据来源的可靠性和可持续性
- Uqer API无席位持仓接口，如何获取数据?

---

### 4. 研报评级维度 (基本面)
**定义**: 专业机构研究报告的观点汇总，判断基本面共识

**数据来源**:
- 智汇期讯API (zhihuiqixun.com)
- 数据类型: 多空全景 + 研报淘金

**已有指标**:
- ✅ 研报观点 (看多/看空/中性)
- ✅ 机构名称
- ✅ 发布日期
- ✅ 交易逻辑
- ✅ 相关数据
- ✅ 风险因素
- ✅ PDF链接
- ✅ 多空全景数据 (过剩/中性/空虚比例)

**缺失指标** (待实现):
- ❌ 评级一致性指标 (看多机构数/看空机构数)
- ❌ 评级变化信号 (7日新增看多/看空)
- ❌ 机构影响力权重
- ❌ 从分歧到一致的转换信号
- ❌ 综合情绪指数

**数据表**:
- `research_reports` - 研报详情
- `market_full_view` - 多空全景

**API接口**:
- `/api/v1/zhihui/full-view` - 多空全景
- `/api/v1/zhihui/reports` - 研报列表
- `/api/v1/zhihui/variety-sentiment/{comm_code}` - 品种情绪
- `/api/v1/zhihui/latest-date` - 最新交易日

**前端页面**: `zhihui.html` (智汇期讯)

**更新频率**: 每30分钟一次

---

## 🗂️ 数据库结构

### 核心数据表

#### 1. warehouse_receipts (虚实比数据)
```sql
CREATE TABLE warehouse_receipts (
    id INTEGER PRIMARY KEY,
    comm_code VARCHAR(20),        -- 品种代码 (如AU)
    variety_name VARCHAR(50),      -- 品种名称 (如沪金)
    record_date DATE,              -- 记录日期
    receipt_quantity FLOAT,        -- 仓单量
    receipt_change FLOAT,          -- 仓单变化
    main_contract VARCHAR(20),     -- 主力合约
    open_interest FLOAT,           -- 持仓量(手)
    open_interest_change FLOAT,    -- 持仓变化
    contract_unit FLOAT,           -- 合约单位(千克/手)
    virtual_quantity FLOAT,        -- 虚盘量
    virtual_real_ratio FLOAT,      -- 虚实比
    squeeze_risk VARCHAR(20),      -- 逼仓风险(高/中/低/无)
    impact_analysis TEXT,          -- 影响分析
    price_pressure VARCHAR(20),    -- 价格压力(上涨/下跌/中性)
    created_at DATETIME,
    updated_at DATETIME
);
```

#### 2. institutional_positions (资金席位)
```sql
CREATE TABLE institutional_positions (
    id INTEGER PRIMARY KEY,
    comm_code VARCHAR(20),
    broker_name VARCHAR(50),       -- 席位名称
    net_position INTEGER,          -- 净持仓
    position_change INTEGER,       -- 持仓变化
    win_rate FLOAT,                -- 席位胜率
    record_date DATE,
    created_at DATETIME
);
```

#### 3. research_reports (研报评级)
```sql
CREATE TABLE research_reports (
    id INTEGER PRIMARY KEY,
    report_id BIGINT,              -- 研报ID
    comm_code VARCHAR(20),
    variety_name VARCHAR(50),
    institution_id INTEGER,
    institution_name VARCHAR(100),
    publish_date DATE,
    view_port VARCHAR(20),         -- 观点(看多/看空/中性)
    sentiment VARCHAR(10),         -- 情绪(bull/bear/neutral)
    trade_logic TEXT,              -- 交易逻辑
    related_data TEXT,             -- 相关数据
    risk_factor TEXT,              -- 风险因素
    report_link VARCHAR(500),      -- PDF链接
    created_at DATETIME,
    updated_at DATETIME
);
```

#### 4. market_full_view (多空全景)
```sql
CREATE TABLE market_full_view (
    id INTEGER PRIMARY KEY,
    comm_code VARCHAR(20),
    variety_name VARCHAR(50),
    record_date DATE,
    excessive_num INTEGER,         -- 过剩数量
    excessive_ratio FLOAT,         -- 过剩比例
    neutral_num INTEGER,           -- 中性数量
    neutral_ratio FLOAT,
    empty_num INTEGER,             -- 空虚数量
    empty_ratio FLOAT,
    total_num INTEGER,             -- 总研报数
    more_port VARCHAR(20),         -- 多空观点(偏多/偏空)
    more_rate FLOAT,               -- 看多比例
    main_sentiment VARCHAR(10),    -- 主情绪
    created_at DATETIME,
    updated_at DATETIME
);
```

#### 5. option_flows (期权资金流向)
```sql
CREATE TABLE option_flows (
    id INTEGER PRIMARY KEY,
    comm_code VARCHAR(20),
    contract_code VARCHAR(100),
    net_flow FLOAT,                -- 净流入(万)
    volume FLOAT,                  -- 成交量变化
    change_ratio FLOAT,            -- 变化比例
    record_time DATETIME,
    created_at DATETIME
);
```

#### 6. daily_blueprints (交易蓝图)
```sql
CREATE TABLE daily_blueprints (
    id INTEGER PRIMARY KEY,
    image_url VARCHAR(500),
    local_path VARCHAR(500),
    parsed_strategies TEXT,        -- JSON格式策略
    record_date DATE,
    created_at DATETIME
);
```

#### 7. market_analysis_summary (四维评分总览)
```sql
CREATE TABLE market_analysis_summary (
    id INTEGER PRIMARY KEY,
    comm_code VARCHAR(20),
    date DATE,
    fundamental_score INTEGER,     -- 基本面分数 (-10到10)
    capital_score INTEGER,         -- 资金面分数
    technical_score INTEGER,       -- 技术面分数
    message_score INTEGER,         -- 消息面分数
    total_direction VARCHAR(10),   -- 综合方向(多/空/中性)
    main_reason TEXT,              -- 核心原因
    created_at DATETIME,
    updated_at DATETIME
);
```

---

## 🕷️ 数据源与爬虫

### 已实现的数据源

#### 1. 智汇期讯 (zhihuiqixun.com)
- **数据类型**: 多空全景 + 研报淘金
- **爬虫文件**: `app/crawlers/zhihui_spider.py`
- **更新频率**: 每30分钟
- **认证方式**: Authorization Token
- **配置**: `ZHIHUI_AUTH_TOKEN` in `.env`
- **数据质量**: ⭐⭐⭐⭐⭐ 优秀

#### 2. 交易可查 (jiaoyikecha.com)
- **数据类型**: 交易蓝图 + 席位持仓
- **爬虫文件**: `app/crawlers/jiaoyikecha_spider.py`
- **更新频率**: 每天19:00
- **认证方式**: 用户名密码登录
- **配置**: `JYK_USER`, `JYK_PASS`
- **失败重试**: 30分钟后重试
- **数据质量**: ⭐⭐⭐⭐ 良好

#### 3. 方期看盘 (founderfu.com)
- **数据类型**: 早盘/夜盘提示
- **爬虫文件**: `app/crawlers/fangqi_spider.py`
- **更新频率**: 早盘8:50 / 夜盘20:50
- **使用Playwright**: 需要浏览器环境
- **数据质量**: ⭐⭐⭐ 一般

#### 4. Openvlab
- **数据类型**: 期权资金流向
- **爬虫文件**: `app/crawlers/openvlab_spider.py`
- **更新频率**: 交易时段每分钟 (9:00-11:30, 13:00-15:00, 21:00-02:00)
- **数据质量**: ⭐⭐⭐⭐ 良好

#### 5. Uqer 优矿 (uqer.io)
- **数据类型**: 仓单 + 持仓 + 合约价格
- **SDK集成**: `app/services/uqer_sdk_client.py`
- **API接口**:
  - `DataAPI.MktFutWRdGet` - 仓单日报
  - `DataAPI.MktFutdGet` - 期货日行情
  - `DataAPI.FutuGet` - 合约信息
- **配置**: `UQER_TOKEN` in `.env`
- **更新频率**: 虚实比每天18:00
- **数据质量**: ⭐⭐⭐⭐⭐ 优秀

#### 6. AKShare
- **数据类型**: 期货行情数据
- **库集成**: `import akshare as ak`
- **用途**: 辅助数据源
- **数据质量**: ⭐⭐⭐⭐ 良好

---

## 🎨 前端页面

### 已实现页面

#### 1. frontend.html - 系统总览
- **路由**: `/frontend` or `/`
- **功能**:
  - 61个品种四维评分展示
  - 多头/空头/中性品种统计
  - 品种卡片展示(评分、方向、理由)
  - 品种详情弹窗
- **技术**: Vue 3 + Element Plus

#### 2. virtual_real_ratio.html - 虚实比分析
- **路由**: `/virtual_real_ratio.html`
- **功能**:
  - 统计概览(总品种/高中低风险)
  - 高风险品种预警
  - 虚实比排行榜
  - 与上期对比(变化率)
  - 历史趋势图表
  - 手动刷新数据
- **技术**: Vue 3 + Element Plus + ECharts

#### 3. zhihui.html - 智汇期讯
- **路由**: `/zhihui` or `/zhihui.html`
- **功能**:
  - 多空全景展示
  - 研报列表展示
  - 品种情绪统计
  - 研报详情查看
  - 机构观点汇总
- **技术**: Vue 3 + Element Plus

#### 4. data_governance.html - 数据治理
- **路由**: `/data-governance`
- **功能**:
  - 数据源健康监控
  - 爬虫执行状态
  - 数据更新时间
  - 异常告警
- **技术**: Vue 3 + Element Plus

#### 5. analysis_v2.html - V2分析总览
- **路由**: `/analysis-v2`
- **功能**:
  - V2版本分析系统入口
  - 多维度数据整合展示
- **技术**: Vue 3 + Element Plus

#### 6. report_detail.html - 研报详情
- **路由**: `/report-detail`
- **功能**: 研报详细信息展示

---

## ⚙️ 定时任务配置

### 自动任务列表

| 任务名称 | 执行时间 | 功能 | 数据源 |
|---------|---------|------|-------|
| 智汇期讯 | 每30分钟 | 多空全景+研报 | 智汇期讯API |
| 方期看盘-早盘 | 每天08:50 | 早盘提示 | 方期网站 |
| 方期看盘-夜盘 | 每天20:50 | 夜盘提示 | 方期网站 |
| 交易可查 | 每天19:00 | 蓝图+席位 | 交易可查网站 |
| Openvlab | 交易时段每分钟 | 期权流向 | Openvlab |
| 虚实比数据 | 每天18:00 | 虚实比计算 | Uqer API |
| 每日分析 | 每天19:30 | 四维评分 | 综合计算 |
| 数据库备份-小时 | 每小时 | SQLite备份 | 本地 |
| 数据库备份-天级 | 每天03:00 | 天级备份 | 本地 |
| 数据库备份-周级 | 周日03:00 | 周级备份 | 本地 |

### 定时任务配置文件
- `app/scheduler.py` - 调度器主文件
- 使用APScheduler库
- 支持Cron和Interval触发

---

## 🚨 数据治理与监控

### DataCollector装饰器
智能数据收集器,提供自动重试、超时控制、异常告警

**功能**:
- 自动重试机制 (max_retries)
- 失败延迟重试 (retry_delay)
- 超时控制 (timeout)
- 飞书告警 (enable_alert)
- 执行日志记录

**使用示例**:
```python
@DataCollector(
    source_name="虚实比数据",
    max_retries=3,
    retry_delay=600,
    timeout=180,
    enable_alert=True
)
async def crawl_data():
    pass
```

### 飞书告警
- **配置**: `FEISHU_WEBHOOK` in `.env`
- **触发条件**: 数据源异常、爬取失败
- **告警内容**: 数据源名称、失败原因、重试次数

---

## 💾 数据备份策略

### 备份配置
- **脚本**: `scripts/backup_database.py`
- **备份目录**: `backups/`
- **SQLite源文件**: `option_tracker.db`

### 备份频率
1. **小时级备份** - 每小时
   - 目录: `backups/hourly/`
   - 保留: 最近24个备份
   - 文件名: `sqlite_backup_hourly_YYYYMMDD_HHMMSS.db`

2. **天级备份** - 每天凌晨3点
   - 目录: `backups/daily/`
   - 保留: 最近30天
   - 文件名: `sqlite_backup_daily_YYYYMMDD_HHMMSS.db`

3. **周级备份** - 每周日凌晨3点
   - 目录: `backups/weekly/`
   - 保留: 最近12周
   - 文件名: `sqlite_backup_weekly_YYYYMMDD_HHMMSS.db`

### 当前占用
- **主数据库**: 10MB
- **备份总量**: 约250MB (30个小时备份 + 4个天级备份)
- ⚠️ **问题**: 本地备份占用空间大,影响电脑性能

---

## 🔧 配置管理

### 环境变量 (.env)
```bash
# 数据库
DATABASE_URL=sqlite:///./option_tracker.db

# Redis
REDIS_URL=redis://localhost:6379/0

# 账号配置
JYK_USER=your_username
JYK_PASS=your_password
ZHIHUI_USER=
ZHIHUI_PASS=
ZHIHUI_AUTH_TOKEN=your_token

# API Keys
GEMINI_API_KEY=your_key
GEMINI_BASE_URL=https://www.apillm.online/v1
UQER_TOKEN=your_uqer_token

# 飞书告警
FEISHU_WEBHOOK=your_webhook_url

# 项目配置
DEBUG=True
LOG_LEVEL=INFO
```

### 配置文件
- `config/settings.py` - 配置类定义
- 使用`pydantic-settings`管理
- 支持`.env`文件自动加载

---

## 📦 依赖管理

### 核心依赖 (requirements.txt)
```
# Web Framework
fastapi>=0.109.0
uvicorn[standard]>=0.27.0

# Database
sqlalchemy>=2.0.25
alembic>=1.13.0

# Task Scheduler
apscheduler>=3.10.0

# Crawling
playwright>=1.41.0
httpx>=0.26.0
beautifulsoup4>=4.12.0

# Data Processing
pandas>=2.1.0
numpy>=1.26.0

# Data Source
akshare>=1.12.0
uqer>=1.3.39

# AI Integration
google-generativeai>=0.3.0
```

---

## 🎯 优化功能点 (待实现)

### Phase 1: 虚实比增强 (高优先级)

#### 1.1 新增指标计算
- [ ] 30日历史百分位
- [ ] 90日历史百分位
- [ ] 30日均值和标准差
- [ ] Z-score (当前值距离均值的标准差倍数)
- [ ] 3日/7日变化率
- [ ] 加速度指标 (变化趋势)

#### 1.2 信号识别
- [ ] 情绪极端信号 (虚实比>90分位)
- [ ] 情绪退潮信号 (从高位>80分位快速回落>15%)
- [ ] 情绪加速信号 (连续上升且加速度>0)
- [ ] 情绪低位企稳 (<20分位)

#### 1.3 API增强
- [ ] 新增 `/enhanced-list` 接口返回增强指标
- [ ] 后端计算百分位/变化率/加速度
- [ ] 缓存优化提升性能

#### 1.4 页面优化
- [ ] 表格新增"历史位置"列 (百分位 + 进度条)
- [ ] 表格新增"趋势信号"列 (退潮/加速/常态)
- [ ] 顶部新增"交易信号"模块
- [ ] 详情卡片展示多维度对比

**预计工作量**: 8-10小时

---

### Phase 2: 研报评级增强 (高优先级)

#### 2.1 新增指标计算
- [ ] 一致性指标 (看多机构数/看空机构数/一致性得分)
- [ ] 评级变化信号 (7日新增看多/看空)
- [ ] 从分歧到一致的转换识别
- [ ] 综合情绪指数

#### 2.2 信号识别
- [ ] 一致看多/看空信号 (3+机构同向)
- [ ] 评级上调/下调信号 (7日内变化)
- [ ] 分歧转一致信号 (关键转折点)

#### 2.3 页面优化
- [ ] 一致性可视化展示
- [ ] 评级变化时间轴
- [ ] 机构观点对比
- [ ] 情绪强度仪表盘

**预计工作量**: 6-8小时

---

### Phase 3: 期限结构历史化 (中高优先级)

#### 3.1 数据库改造
- [ ] 新建 `term_structure_history` 表
```sql
CREATE TABLE term_structure_history (
    id INTEGER PRIMARY KEY,
    comm_code VARCHAR(20),
    variety_name VARCHAR(50),
    record_date DATE,
    market_structure VARCHAR(20),  -- 正向/反向
    near_month_price FLOAT,
    far_month_price FLOAT,
    price_spread FLOAT,
    spread_pct FLOAT,
    structure_score INT,
    created_at DATETIME
);
```

#### 3.2 爬虫修改
- [ ] 修改定时任务,每日保存而非覆盖JSON
- [ ] 数据同时写入数据库和JSON (兼容期)
- [ ] 历史数据导入脚本

#### 3.3 新增指标
- [ ] 结构持续天数
- [ ] 价差变化率 (3日/7日)
- [ ] 价差历史分位数
- [ ] 结构转换信号 (Back→Contango / Contango→Back)

#### 3.4 页面开发
- [ ] 新增 `term_structure.html` 独立页面
- [ ] 结构转换信号展示
- [ ] 价差趋势图表
- [ ] 结构历史回溯

**预计工作量**: 12-15小时

---

### Phase 4: 资金席位增强 (中优先级)

#### 4.1 数据源确认
- [ ] ⚠️ 确认席位数据来源和可持续性
- [ ] 评估数据质量
- [ ] 确认更新频率

#### 4.2 新增指标
- [ ] Top5集中度 (多头/空头占比)
- [ ] 多空分歧度
- [ ] 新增主力识别 (新进Top10)
- [ ] 资金流入加速度
- [ ] 席位方向一致性

#### 4.3 信号识别
- [ ] 集中流入信号 (Top5净增仓>10%)
- [ ] 撤离转向信号 (单边减仓>15%)
- [ ] 分歧加剧信号 (多空胶着)

#### 4.4 页面开发
- [ ] 新增 `capital_position.html` 独立页面
- [ ] 资金流向可视化
- [ ] 席位排行榜
- [ ] 机构vs散户对比

**预计工作量**: 10-12小时

---

### Phase 5: 机会雷达总览 (高优先级)

#### 5.1 多维度信号共振
- [ ] 四维度信号评分系统
- [ ] 信号共振识别逻辑
- [ ] S/A/B/C级机会分类

#### 5.2 综合评分公式
```
机会总分 = 虚实比得分×0.3 + 期限结构得分×0.35
         + 资金席位得分×0.25 + 研报评级得分×0.1
```

#### 5.3 页面开发
- [ ] 新增 `opportunity_radar.html` 机会雷达页面
- [ ] S级机会列表 (3+维度共振)
- [ ] A级机会列表 (3维度)
- [ ] 机会详情卡片 (四维度数据聚合)
- [ ] 实时推送 (S级机会告警)

**预计工作量**: 10-12小时

---

## ☁️ 云端迁移方案

### 当前问题
1. **本地存储占用大**: 342MB项目 + 250MB备份
2. **电脑性能影响**: 定时任务占用CPU/内存
3. **数据安全风险**: 电脑关机数据停止更新
4. **无法远程访问**: 只能本地localhost访问

### 迁移目标
1. 代码部署到云服务器
2. 数据库迁移到云端
3. 定时任务云端执行
4. 远程访问API和前端
5. 释放本地存储空间

### 推荐方案

#### 方案A: 轻量级云服务 (推荐)
**适合**: 个人使用,成本低

**架构**:
```
阿里云/腾讯云轻量应用服务器 (2核4G 60GB)
├─ FastAPI应用 (Docker部署)
├─ MySQL 8.0 (替代SQLite)
├─ Nginx (反向代理)
└─ 定时任务 (APScheduler)
```

**成本**: 约¥50-80/月

**优点**:
- 成本低
- 配置简单
- 适合个人项目

**缺点**:
- 单机部署,无高可用
- 性能有限

#### 方案B: 分离式架构 (适合扩展)
**适合**: 数据量大,需要扩展

**架构**:
```
应用服务器 (云服务器)
├─ FastAPI应用 (Docker)
└─ 定时任务

数据库 (云数据库RDS)
├─ MySQL 8.0
└─ 自动备份

对象存储 (OSS)
└─ 图片/PDF文件存储
```

**成本**: 约¥200-300/月

**优点**:
- 数据库独立,性能好
- 自动备份,安全性高
- 可扩展性强

**缺点**:
- 成本较高
- 配置复杂

#### 方案C: Serverless (最省钱)
**适合**: 访问量小,定时任务为主

**架构**:
```
函数计算 (阿里云FC / 腾讯云SCF)
├─ 定时触发器 → 爬虫函数
└─ HTTP触发器 → API函数

云数据库 (按量付费)
└─ MySQL Serverless
```

**成本**: 约¥20-50/月

**优点**:
- 成本最低
- 按使用量付费
- 自动扩容

**缺点**:
- 冷启动延迟
- 不适合长连接
- 开发调试复杂

### 迁移步骤 (方案A详细)

#### Step 1: 云服务器准备
```bash
# 1. 购买云服务器 (阿里云/腾讯云)
#    配置: 2核4G 60GB
#    系统: Ubuntu 22.04 LTS

# 2. 安装Docker
curl -fsSL https://get.docker.com | bash

# 3. 安装Docker Compose
sudo apt install docker-compose

# 4. 安装MySQL
sudo apt install mysql-server
```

#### Step 2: 数据库迁移
```bash
# 1. 导出SQLite数据
sqlite3 option_tracker.db .dump > backup.sql

# 2. 转换为MySQL格式
# 使用工具: sqlite3-to-mysql
pip install sqlite3-to-mysql
sqlite3mysql --sqlite-file option_tracker.db \
             --mysql-database optionalpha \
             --mysql-user root \
             --mysql-password your_password

# 3. 修改DATABASE_URL
# 原: sqlite:///./option_tracker.db
# 新: mysql+pymysql://root:password@localhost/optionalpha
```

#### Step 3: 应用容器化
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装Playwright浏览器
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium
RUN playwright install-deps chromium

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=mysql+pymysql://root:password@mysql/optionalpha
    volumes:
      - ./data:/app/data
    depends_on:
      - mysql
    restart: always

  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: your_password
      MYSQL_DATABASE: optionalpha
    volumes:
      - mysql_data:/var/lib/mysql
    restart: always

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - app
    restart: always

volumes:
  mysql_data:
```

#### Step 4: 部署流程
```bash
# 1. 上传代码到云服务器
rsync -avz --exclude='.git' \
      --exclude='__pycache__' \
      --exclude='backups' \
      ./ user@server:/opt/optionalpha/

# 2. 启动服务
cd /opt/optionalpha
docker-compose up -d

# 3. 检查日志
docker-compose logs -f app

# 4. 配置Nginx反向代理
# 绑定域名,配置HTTPS证书
```

#### Step 5: 数据备份优化
```bash
# 云端备份策略
# 1. MySQL自动备份 (每天凌晨3点)
mysqldump --all-databases > /backup/mysql_$(date +%Y%m%d).sql

# 2. 只保留最近7天备份
find /backup -name "mysql_*.sql" -mtime +7 -delete

# 3. 定期同步到OSS (可选)
aliyun oss cp /backup/mysql_$(date +%Y%m%d).sql \
              oss://your-bucket/backups/
```

#### Step 6: 域名和HTTPS
```bash
# 1. 申请免费SSL证书 (Let's Encrypt)
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com

# 2. 自动续期
sudo certbot renew --dry-run
```

### 本地清理
迁移完成后,本地可删除:
```
✅ backups/ 文件夹 (250MB)
✅ __pycache__/ 缓存 (若干)
✅ option_tracker.db (10MB)
⚠️ 保留源代码用于本地开发
```

### 成本估算 (方案A)
- 云服务器: ¥60/月
- 域名: ¥50/年 ≈ ¥4/月
- SSL证书: 免费 (Let's Encrypt)
- 总计: 约¥65/月

---

## 📝 开发规范

### 代码结构
```
option_tracker/
├── main.py                 # FastAPI入口
├── app/
│   ├── models/            # 数据模型
│   │   ├── base.py
│   │   ├── database.py
│   │   └── models.py
│   ├── routers/           # API路由
│   │   ├── summary.py
│   │   ├── fundamental.py
│   │   ├── capital.py
│   │   ├── technical.py
│   │   ├── virtual_real_ratio.py
│   │   ├── term_structure.py
│   │   ├── zhihui.py
│   │   └── ...
│   ├── crawlers/          # 爬虫模块
│   │   ├── zhihui_spider.py
│   │   ├── jiaoyikecha_spider.py
│   │   ├── fangqi_spider.py
│   │   ├── virtual_real_ratio_spider_uqer.py
│   │   └── ...
│   ├── services/          # 业务服务
│   │   ├── uqer_sdk_client.py
│   │   ├── data_collector.py
│   │   ├── analysis.py
│   │   └── ...
│   └── scheduler.py       # 定时任务
├── config/
│   └── settings.py        # 配置管理
├── scripts/               # 脚本工具
│   ├── backup_database.py
│   └── ...
├── data/                  # 数据文件
│   ├── term_structure_data.json
│   └── ...
├── backups/               # 备份目录
│   ├── hourly/
│   ├── daily/
│   └── weekly/
├── frontend.html          # 前端页面
├── virtual_real_ratio.html
├── zhihui.html
├── requirements.txt
└── .env                   # 环境变量
```

### 命名规范
- 文件名: 小写下划线 `virtual_real_ratio.py`
- 类名: 大驼峰 `VirtualRealRatioSpider`
- 函数名: 小写下划线 `get_virtual_real_ratio()`
- 变量名: 小写下划线 `comm_code`
- 常量: 大写下划线 `VARIETY_MAPPING`

### API路由规范
```
/api/v1/{module}/{action}
```
示例:
- `/api/v1/virtual-real-ratio/list`
- `/api/v1/zhihui/full-view`
- `/api/v1/capital/{variety_code}/positions`

---

## 🐛 已知问题

### 高优先级
1. **期限结构无历史数据** - JSON覆盖导致无法判断转换
2. **资金席位数据源不明** - 需确认来源和可持续性
3. **本地备份占用大** - 250MB备份影响性能
4. **无远程访问** - 只能本地访问

### 中优先级
1. **缺少百分位指标** - 虚实比无历史位置参考
2. **缺少信号识别** - 无自动交易机会提醒
3. **缺少机会雷达** - 无多维度共振展示
4. **缺少独立页面** - 期限结构、资金席位无独立页面

### 低优先级
1. **SQLite性能** - 并发写入性能差
2. **无用户系统** - 无登录认证
3. **无权限控制** - 所有API公开
4. **无日志查询** - 日志只在控制台

---

## 📚 技术文档

### API文档
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 数据库文档
- 使用SQLAlchemy ORM
- 迁移工具: Alembic (未启用)

### 爬虫文档
- Playwright: 浏览器自动化
- httpx: HTTP异步客户端
- BeautifulSoup4: HTML解析

---

## 🔐 安全建议

### 当前问题
- ❌ `.env` 文件包含敏感信息
- ❌ 无API认证机制
- ❌ CORS配置为 `*` (全部允许)
- ❌ 密码明文存储

### 改进建议
1. **环境变量加密** - 使用密钥管理服务
2. **API Token认证** - JWT/OAuth2
3. **CORS限制** - 只允许特定域名
4. **密码加密** - bcrypt哈希存储
5. **HTTPS部署** - SSL证书

---

## 📞 联系与支持

### 项目信息
- **项目名称**: OptionAlpha
- **版本**: v1.0.0
- **开发者**: PM
- **文档版本**: 2024-12-16

### 重构检查清单
在重构时,请确保:
- [ ] 所有10个定时任务都已配置
- [ ] 5个数据源的Token/密码已设置
- [ ] 数据库表结构完整迁移
- [ ] 8个前端页面都能访问
- [ ] DataCollector装饰器正常工作
- [ ] 飞书告警配置正确
- [ ] 备份策略已调整(云端)

---

## 🎯 下一步行动建议

### 立即执行
1. **备份重要数据** - 导出当前数据库
2. **停止本地备份** - 减少磁盘占用
3. **选择云服务商** - 阿里云/腾讯云轻量服务器

### 1周内完成
1. **购买云服务器** - 2核4G配置
2. **数据库迁移** - SQLite → MySQL
3. **应用容器化** - 编写Dockerfile
4. **部署到云端** - Docker Compose部署

### 2-4周完成
1. **虚实比增强** - 百分位+信号识别
2. **研报评级优化** - 一致性计算
3. **期限结构历史化** - 建表+爬虫改造
4. **机会雷达开发** - 多维度共振

---

**文档创建时间**: 2024-12-16
**最后更新**: 2024-12-16
**文档用途**: 项目重构参考,确保信息完整,避免功能丢失
