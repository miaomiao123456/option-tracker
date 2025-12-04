# OptionAlpha 数据字典

## 📋 概述

本文档详细描述了 OptionAlpha 期权交易策略系统的所有数据表结构、字段定义以及数据来源信息。

**数据库类型**: SQLite / PostgreSQL
**字符编码**: UTF-8
**更新时间**: 2025-12-01

---

## 📊 核心业务表

### 1. commodities - 品种基础表

**用途**: 存储期货/期权品种的基本信息

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | Integer | PRIMARY KEY | 自增主键 |
| code | String(20) | UNIQUE, NOT NULL | 品种代码（如 RB、CU） |
| name | String(50) | NOT NULL | 品种名称（如 螺纹钢、铜） |
| exchange | String(20) | - | 交易所（SHFE、DCE、CZCE、GFEX、INE） |
| category | String(20) | - | 分类（黑色、有色、能化、农产品） |

**数据来源**: 手动维护 + API自动同步
**更新频率**: 新品种上市时更新

---

### 2. market_analysis_summary - 四维评分总览表

**用途**: 存储综合市场分析结果，包含基本面、资金面、技术面、消息面四维评分

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | Integer | PRIMARY KEY | 自增主键 |
| comm_code | String(20) | NOT NULL, INDEX | 品种代码 |
| date | Date | NOT NULL, INDEX | 日期 |
| fundamental_score | Integer | DEFAULT 0 | 基本面分数 (-10 到 10) |
| capital_score | Integer | DEFAULT 0 | 资金面分数 (-10 到 10) |
| technical_score | Integer | DEFAULT 0 | 技术面分数 (-10 到 10) |
| message_score | Integer | DEFAULT 0 | 消息面分数 (-10 到 10) |
| total_direction | Enum | - | 综合方向（多/空/中性） |
| main_reason | Text | - | 核心原因 |
| created_at | DateTime | - | 创建时间 |
| updated_at | DateTime | - | 更新时间 |

**数据来源**: AI分析服务（Gemini API）
**爬虫**: 无（由分析服务生成）
**更新频率**: 每天 19:30

---

### 3. fundamental_reports - 基本面数据表

**用途**: 存储各数据源的基本面研究报告

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | Integer | PRIMARY KEY | 自增主键 |
| comm_code | String(20) | NOT NULL, INDEX | 品种代码 |
| source | String(50) | - | 数据来源（hzzhqx/founderfu） |
| report_type | String(20) | - | 报告类型（morning/night/deep） |
| sentiment | String(10) | - | 情绪（bull/bear/neutral） |
| content_summary | Text | - | 内容摘要 |
| publish_time | DateTime | - | 发布时间 |
| created_at | DateTime | - | 创建时间 |

**数据来源**:
- **智汇期讯（hzzhqx）**: 多空全景、观点列表
  - 爬虫: `app/crawlers/zhihui_spider.py`
  - URL: https://hzzhqx.com
  - API:
    - 品种列表: `https://hzzhqx.com/api/public/variety/list`
    - 多空全景: `https://hzzhqx.com/api/report/overallView`
  - 采集频率: 每 30 分钟
  - 需要登录: 是（使用 ZHIHUI_AUTH_TOKEN）

- **方期看盘（founderfu）**: 早盘/夜盘评分
  - 爬虫: `app/crawlers/fangqi_spider.py`
  - URL: https://fxq.founderfu.com
  - API: `https://fxq.founderfu.com/pc/jiandaoyun/ratingprediction/list`
  - 采集频率: 早盘 08:50 / 夜盘 20:50
  - 需要登录: 否

**更新频率**: 实时（按爬虫调度）

---

### 4. institutional_positions - 机构资金数据表

**用途**: 存储机构席位持仓数据

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | Integer | PRIMARY KEY | 自增主键 |
| comm_code | String(20) | NOT NULL, INDEX | 品种代码 |
| broker_name | String(50) | - | 席位名称（如 永安期货） |
| net_position | Integer | - | 净持仓（手） |
| position_change | Integer | - | 增减仓变化（手） |
| win_rate | Float | - | 席位胜率（0-1） |
| record_date | Date | NOT NULL, INDEX | 记录日期 |
| created_at | DateTime | - | 创建时间 |

**数据来源**:
- **智汇期讯（hzzhqx）**: 席位分析
  - 爬虫: `app/crawlers/zhihui_spider.py`
  - URL: https://hzzhqx.com
  - 采集频率: 每 30 分钟

**更新频率**: 每 30 分钟

---

### 5. technical_indicators - 技术面数据表

**用途**: 存储技术指标数据

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | Integer | PRIMARY KEY | 自增主键 |
| comm_code | String(20) | NOT NULL, INDEX | 品种代码 |
| iv_rank | Float | - | 隐含波动率排位（0-100） |
| term_structure | String(20) | - | 期限结构（contango/back） |
| pcr_ratio | Float | - | 看跌看涨比率 |
| record_time | DateTime | NOT NULL | 记录时间 |
| created_at | DateTime | - | 创建时间 |

**数据来源**:
- **Openvlab**: 期权技术指标
  - 爬虫: `app/crawlers/openvlab_spider.py`
  - URL: https://www.openvlab.cn
  - 页面:
    - 资金流向: `https://www.openvlab.cn/flow`
    - 分时数据: `https://www.openvlab.cn`
  - 采集频率: 交易时段每分钟（9:00-11:30, 13:00-15:00, 21:00-02:00）
  - 需要登录: 否

**更新频率**: 交易时段每分钟

---

### 6. daily_blueprints - 日度交易蓝图表

**用途**: 存储交易可查的日度策略截图和解析结果

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | Integer | PRIMARY KEY | 自增主键 |
| image_url | String(500) | - | 图片URL |
| local_path | String(500) | - | 本地存储路径 |
| parsed_strategies | Text | - | 解析的策略（JSON格式） |
| record_date | Date | NOT NULL, INDEX | 记录日期 |
| created_at | DateTime | - | 创建时间 |

**数据来源**:
- **交易可查（jiaoyikecha）**: 日度交易蓝图截图
  - 爬虫: `app/crawlers/jiaoyikecha_spider.py`
  - URL: https://www.jiaoyikecha.com
  - API: `https://www.jiaoyikecha.com/ajax/guangao.php?v=cd42afe7`
  - 采集频率: 每天 19:00（失败后 30 分钟重试）
  - 需要登录: 是（使用 JYK_USER/JYK_PASS）
  - 说明: 使用 Playwright 自动化登录并截图

**更新频率**: 每天 19:00

---

### 7. option_flows - 期权资金流向表

**用途**: 存储期权资金流向数据

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | Integer | PRIMARY KEY | 自增主键 |
| comm_code | String(20) | NOT NULL, INDEX | 品种代码 |
| contract_code | String(100) | - | 合约代码 |
| net_flow | Float | - | 净流入（万元） |
| volume | Float | - | 成交量变化（万手） |
| change_ratio | Float | - | 变化比例（%） |
| record_time | DateTime | NOT NULL, INDEX | 记录时间 |
| created_at | DateTime | - | 创建时间 |

**数据来源**:
- **Openvlab**: 期权资金流向
  - 爬虫: `app/crawlers/openvlab_spider.py`
  - URL: https://www.openvlab.cn/flow
  - 采集频率: 交易时段每分钟
  - 需要登录: 否

**更新频率**: 交易时段每分钟

---

### 8. contract_infos - 合约信息表

**用途**: 存储合约的基本信息，用于市值计算

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | Integer | PRIMARY KEY | 自增主键 |
| comm_code | String(20) | UNIQUE, NOT NULL | 品种代码 |
| multiplier | Integer | DEFAULT 10 | 合约乘数 |
| latest_price | Float | DEFAULT 0 | 最新价格 |
| price_update_time | DateTime | - | 价格更新时间 |
| created_at | DateTime | - | 创建时间 |

**数据来源**:
- **Openvlab**: 合约价格数据
  - 爬虫: `app/crawlers/openvlab_spider.py`
  - URL: https://www.openvlab.cn
  - 采集频率: 交易时段每分钟

**更新频率**: 交易时段每分钟

---

## 🔧 数据治理表

### 9. data_sources - 数据源注册表

**用途**: 注册所有数据源，用于监控和管理

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | Integer | PRIMARY KEY | 自增主键 |
| source_name | String(100) | UNIQUE, NOT NULL | 数据源名称 |
| source_type | String(20) | NOT NULL | 类型（api/spider/service/file） |
| description | Text | - | 数据源描述 |
| health_status | String(20) | DEFAULT 'healthy' | 健康状态（healthy/warning/error） |
| last_collect_time | DateTime | - | 最近采集时间 |
| success_rate | Float | DEFAULT 100.0 | 成功率（%） |
| avg_duration | Float | DEFAULT 0 | 平均耗时（秒） |
| is_enabled | Boolean | DEFAULT TRUE | 是否启用 |
| created_at | DateTime | - | 创建时间 |
| updated_at | DateTime | - | 更新时间 |

**数据来源**: 系统自动注册
**更新频率**: 每次采集后更新

**已注册数据源列表**:

| 数据源名称 | 类型 | 爬虫URL | 采集频率 |
|-----------|------|---------|---------|
| 智汇期讯-多空全景 | spider | https://hzzhqx.com | 每 30 分钟 |
| 智汇期讯-观点列表 | spider | https://hzzhqx.com | 每 30 分钟 |
| 方期看盘-早盘 | spider | https://fxq.founderfu.com | 每天 08:50 |
| 方期看盘-夜盘 | spider | https://fxq.founderfu.com | 每天 20:50 |
| 交易可查-日度蓝图 | spider | https://www.jiaoyikecha.com | 每天 19:00 |
| Openvlab-资金流向 | spider | https://www.openvlab.cn/flow | 每分钟（交易时段） |
| Openvlab-分时数据 | spider | https://www.openvlab.cn | 每分钟（交易时段） |
| Gemini-AI分析 | service | https://www.apillm.online/v1 | 每天 19:30 |

---

### 10. data_collection_logs - 数据采集日志表

**用途**: 记录每次数据采集的详细日志

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | Integer | PRIMARY KEY | 自增主键 |
| source_name | String(100) | NOT NULL, INDEX | 数据源名称 |
| collect_time | DateTime | NOT NULL, INDEX | 采集时间 |
| status | String(20) | NOT NULL | 状态（success/failed） |
| records_collected | Integer | DEFAULT 0 | 采集记录数 |
| duration | Float | DEFAULT 0 | 耗时（秒） |
| error_message | Text | - | 错误信息 |
| retry_count | Integer | DEFAULT 0 | 重试次数 |
| data_quality_score | Float | - | 数据质量分数（0-100） |
| created_at | DateTime | - | 创建时间 |

**数据来源**: 系统自动记录
**更新频率**: 每次采集时记录
**保留策略**: 保留 90 天

---

### 11. data_quality_metrics - 数据质量指标表

**用途**: 记录数据质量历史趋势

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | Integer | PRIMARY KEY | 自增主键 |
| source_name | String(100) | NOT NULL, INDEX | 数据源名称 |
| metric_date | Date | NOT NULL, INDEX | 指标日期 |
| completeness | Float | - | 完整性（%） |
| accuracy | Float | - | 准确性（%） |
| timeliness | Float | - | 及时性（%） |
| consistency | Float | - | 一致性（%） |
| overall_score | Float | - | 综合分数（0-100） |
| created_at | DateTime | - | 创建时间 |

**数据来源**: 系统自动计算
**更新频率**: 每天汇总一次
**保留策略**: 永久保留

---

## 🗂️ 数据源详细信息

### 智汇期讯（hzzhqx）

**网站**: https://hzzhqx.com
**类型**: Web爬虫（需要登录）
**爬虫文件**: `app/crawlers/zhihui_spider.py`

**API 接口**:
```
GET https://hzzhqx.com/api/public/variety/list
    返回: 品种列表

GET https://hzzhqx.com/api/report/overallView
    参数: publishDate (YYYY-MM-DD), sectorId, morePort
    返回: 多空全景数据
```

**认证方式**:
- 需要在 `.env` 中配置 `ZHIHUI_AUTH_TOKEN`
- Token 通过 HTTP Header `Authorization: Bearer {token}` 传递

**数据表**: fundamental_reports, institutional_positions

**采集时间**: 每 30 分钟

---

### 方期看盘（founderfu）

**网站**: https://fxq.founderfu.com
**类型**: Web爬虫（无需登录）
**爬虫文件**: `app/crawlers/fangqi_spider.py`

**API 接口**:
```
POST https://fxq.founderfu.com/pc/jiandaoyun/ratingprediction/list
    返回: 评分预测数据
```

**数据表**: fundamental_reports

**采集时间**:
- 早盘: 每天 08:50
- 夜盘: 每天 20:50

---

### 交易可查（jiaoyikecha）

**网站**: https://www.jiaoyikecha.com
**类型**: Web爬虫（需要登录）
**爬虫文件**: `app/crawlers/jiaoyikecha_spider.py`

**API 接口**:
```
GET https://www.jiaoyikecha.com/ajax/guangao.php?v=cd42afe7
    返回: 广告位信息（包含蓝图图片）
```

**认证方式**:
- 需要在 `.env` 中配置 `JYK_USER` 和 `JYK_PASS`
- 使用 Playwright 自动化登录
- 登录后截图保存

**数据表**: daily_blueprints

**采集时间**: 每天 19:00（失败后 30 分钟重试）

**特殊说明**:
- 需要浏览器自动化（Playwright）
- 截图存储在 `screenshots/` 目录

---

### Openvlab

**网站**: https://www.openvlab.cn
**类型**: Web爬虫（无需登录）
**爬虫文件**: `app/crawlers/openvlab_spider.py`

**页面**:
```
GET https://www.openvlab.cn/flow
    爬取: 期权资金流向数据

GET https://www.openvlab.cn
    爬取: 分时数据、合约价格
```

**数据表**: option_flows, technical_indicators, contract_infos

**采集时间**:
- 交易时段每分钟
  - 日盘: 9:00-11:30, 13:00-15:00
  - 夜盘: 21:00-02:00

**特殊说明**:
- 使用 Playwright 渲染 JavaScript
- 实时监控交易时段

---

### 融达数据分析家（rongda）

**网站**: https://dt.rongdaqh.com
**类型**: Web爬虫（已禁用）
**爬虫文件**: `app/crawlers/rongda_spider.py`

**状态**: 已禁用，不再采集

---

### Gemini AI 分析服务

**API**: https://www.apillm.online/v1
**类型**: AI服务
**配置**: `config/settings.py`

**认证方式**:
- 需要在 `.env` 中配置 `GEMINI_API_KEY`

**数据表**: market_analysis_summary

**执行时间**: 每天 19:30

**服务文件**: `app/services/analysis.py`

---

## 📈 数据流向图

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│   智汇期讯      │────>│ fundamental_     │      │                 │
│   (30min)       │      │ reports          │      │                 │
└─────────────────┘      └──────────────────┘      │                 │
                                                    │                 │
┌─────────────────┐      ┌──────────────────┐      │                 │
│   方期看盘      │────>│ fundamental_     │      │  market_        │
│   (08:50,20:50) │      │ reports          │────>│  analysis_      │
└─────────────────┘      └──────────────────┘      │  summary        │
                                                    │                 │
┌─────────────────┐      ┌──────────────────┐      │                 │
│   Openvlab      │────>│ technical_       │      │  (AI分析)       │
│   (每分钟)      │      │ indicators       │      │                 │
└─────────────────┘      └──────────────────┘      └─────────────────┘

┌─────────────────┐      ┌──────────────────┐
│   交易可查      │────>│ daily_           │
│   (19:00)       │      │ blueprints       │
└─────────────────┘      └──────────────────┘

┌─────────────────┐      ┌──────────────────┐
│   所有爬虫      │────>│ data_collection_ │
│                 │      │ logs             │
└─────────────────┘      └──────────────────┘
```

---

## 🔐 配置说明

所有敏感配置存储在 `.env` 文件中：

```bash
# 数据库配置
DATABASE_URL=sqlite:///./option_tracker.db
# 或使用 PostgreSQL
DATABASE_URL=postgresql://user:password@localhost:5432/option_tracker

# 智汇期讯
ZHIHUI_AUTH_TOKEN=your_token_here

# 交易可查
JYK_USER=your_username
JYK_PASS=your_password

# Gemini API
GEMINI_API_KEY=your_api_key
GEMINI_BASE_URL=https://www.apillm.online/v1

# 飞书告警
FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
```

---

## 📊 数据统计

### 当前系统数据规模（示例）

| 数据表 | 记录数 | 增长速率 | 存储大小 |
|--------|--------|----------|----------|
| commodities | 50 | 极慢 | < 10 KB |
| market_analysis_summary | 1,500 | 50/天 | ~ 500 KB |
| fundamental_reports | 10,000 | 200/天 | ~ 5 MB |
| institutional_positions | 50,000 | 1,000/天 | ~ 20 MB |
| technical_indicators | 100,000 | 5,000/天 | ~ 50 MB |
| daily_blueprints | 365 | 1/天 | ~ 100 MB（含图片） |
| option_flows | 500,000 | 20,000/天 | ~ 200 MB |
| contract_infos | 50 | 极慢 | < 10 KB |
| data_collection_logs | 50,000 | 2,000/天 | ~ 30 MB |

**总计**: 约 400 MB（不含图片文件）

---

## 🔄 数据更新时间表

| 时间 | 任务 | 数据表 |
|------|------|--------|
| 每 30 分钟 | 智汇期讯爬虫 | fundamental_reports, institutional_positions |
| 08:50 | 方期看盘早盘 | fundamental_reports |
| 20:50 | 方期看盘夜盘 | fundamental_reports |
| 19:00 | 交易可查蓝图 | daily_blueprints |
| 19:30 | AI全品种分析 | market_analysis_summary |
| 每分钟（交易时段） | Openvlab监控 | option_flows, technical_indicators, contract_infos |
| 每小时 | 小时级备份 | - |
| 每天 03:00 | 天级备份 | - |
| 每周日 03:00 | 周级备份 | - |

---

## 📝 维护建议

### 数据清理策略

1. **data_collection_logs**: 保留 90 天，定期清理
2. **option_flows**: 保留 180 天，定期归档
3. **daily_blueprints**: 图片文件定期压缩归档

### 索引优化

建议为以下字段创建索引：
```sql
-- 品种代码索引（高频查询）
CREATE INDEX idx_comm_code ON market_analysis_summary(comm_code);
CREATE INDEX idx_fundamental_comm_code ON fundamental_reports(comm_code);
CREATE INDEX idx_institutional_comm_code ON institutional_positions(comm_code);

-- 时间索引（范围查询）
CREATE INDEX idx_market_date ON market_analysis_summary(date);
CREATE INDEX idx_collection_time ON data_collection_logs(collect_time);
CREATE INDEX idx_option_flow_time ON option_flows(record_time);

-- 组合索引（复合查询）
CREATE INDEX idx_comm_date ON market_analysis_summary(comm_code, date);
```

### 备份策略

参考 [备份系统文档](BACKUP_SYSTEM.md)

---

## 🔗 相关文档

- [数据治理指南](DATA_GOVERNANCE.md)
- [PostgreSQL 迁移指南](POSTGRESQL_SETUP.md)
- [备份系统配置](BACKUP_SYSTEM.md)
- [飞书告警设置](FEISHU_SETUP.md)

---

**文档版本**: v1.0
**最后更新**: 2025-12-01
**维护者**: OptionAlpha Team
