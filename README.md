# 期权交易跟踪器 - OptionAlpha

## 项目概述

面向散户的期货期权交易四维分析系统，帮助散户从基本面、消息面、机构资金面、技术面四大维度分析交易品种。

## 当前进展 ✅

### 1. 后端架构 (已完成)
- ✅ FastAPI 框架搭建
- ✅ SQLAlchemy ORM + 数据库模型设计
- ✅ 环境配置管理 (.env + pydantic-settings)
- ✅ 项目目录结构规划

### 2. 数据库设计 (已完成)
已创建以下核心表：
- `commodities` - 品种基础表
- `market_analysis_summary` - 四维评分总览表
- `fundamental_reports` - 基本面数据表
- `institutional_positions` - 机构资金数据表
- `technical_indicators` - 技术面数据表
- `daily_blueprints` - 交易蓝图表

### 3. 爬虫模块 (部分完成)
#### ✅ 已完成：
- **交易可查爬虫** (`jiaoyikecha_spider.py`)
  - Playwright 自动登录
  - 席位持仓数据获取
  - 每日交易蓝图图片下载
  - **蓝图解析器** (`blueprint_parser.py`) ✅
    - 基于 Vision API (GPT-4o) 自动解析图片
    - 智能识别交易方向 (散户反向/机构跟随)
    - 自动提取策略强度和理由
    - 自动入库并提供 API 查询

- **智汇期讯爬虫** (`zhihui_spider.py`)
  - 多空全景数据获取
  - 研报淘金数据获取
  - 观点聚合功能

#### 🔄 进行中：
- 方期看盘爬虫
- Openvlab 爬虫
- 融达数据爬虫

## 项目结构

```
option_tracker/
├── main.py                     # FastAPI 主应用入口
├── requirements.txt            # 依赖包
├── .env                        # 环境配置
├── config/
│   ├── settings.py            # 配置管理
│   └── __init__.py
├── app/
│   ├── models/
│   │   ├── models.py          # SQLAlchemy 数据模型
│   │   ├── database.py        # 数据库连接
│   │   └── __init__.py
│   ├── crawlers/
│   │   ├── jiaoyikecha_spider.py    # 交易可查爬虫 ✅
│   │   ├── zhihui_spider.py         # 智汇期讯爬虫 ✅
│   │   └── __init__.py
│   ├── routers/               # API 路由 (待开发)
│   ├── services/              # 业务逻辑 (待开发)
│   └── utils/                 # 工具函数
└── tests/                     # 测试用例
```

## 技术栈

### 后端
- **框架**: FastAPI 0.109
- **ORM**: SQLAlchemy 2.0
- **数据库**: SQLite (开发) / MySQL (生产)
- **任务队列**: Celery + Redis (待实现)

### 爬虫
- **动态渲染**: Playwright 1.41
- **HTTP 请求**: httpx 0.26
- **数据解析**: BeautifulSoup4 + lxml

### 前端 (已优化)
- 基于 Vue 3 + Element Plus
- 集成 ECharts 图表
- **新增功能**:
  - 交易蓝图策略展示 (做多/做空分离)
  - 历史数据日期选择器
  - 融达数据结构分析展示

## 快速开始

### 1. 安装依赖

```bash
cd option_tracker
pip install -r requirements.txt
playwright install chromium
```

### 2. 配置环境变量

编辑 `.env` 文件，填入你的账号信息：
```env
JYK_USER=18321399574
JYK_PASS=yi2013405
GEMINI_API_KEY=sk-IJhu2VBNt2G97XJeE6F82dD8047c4a2989326250068aA1F5
```

### 3. 初始化数据库

```bash
python main.py  # 启动时自动创建数据库表
```

### 4. 测试爬虫

```bash
# 测试交易可查爬虫
cd app/crawlers
python jiaoyikecha_spider.py

# 测试智汇期讯爬虫
python zhihui_spider.py
```

### 5. 启动API服务

```bash
uvicorn main:app --reload --port 8000
```

访问 http://localhost:8000/docs 查看API文档

## 后续开发计划

### 第一阶段：完成爬虫模块 (优先级: 高)

1. **方期看盘爬虫**
   - 早盘数据 (8:50)
   - 夜盘数据 (20:50)
   - 品种方向、强度、总结、资讯、逻辑、策略

2. **Openvlab 爬虫**
   - 期权合约数据
   - 分时行情波动率背离
   - 需要逆向分析API接口

3. **融达数据爬虫**
   - Contango/Back 结构识别
   - 期限结构数据

### 第二阶段：后端API开发 (优先级: 高)

创建以下API端点：

**总览模块** (`/api/v1/summary`)
- `GET /top-movers` - 多空前3品种
- `GET /overview` - 全品种四维总览
- `GET /search?q=rb` - 品种搜索

**基本面模块** (`/api/v1/fundamental`)
- `GET /{variety_code}` - 获取品种基本面数据
- `GET /{variety_code}/reports` - 获取研报列表

**资金面模块** (`/api/v1/capital`)
- `GET /{variety_code}/positions` - 席位持仓数据
- `GET /{variety_code}/flow` - 资金流向

**技术面模块** (`/api/v1/technical`)
- `GET /{variety_code}/indicators` - 技术指标
- `GET /{variety_code}/structure` - 期限结构

**日报模块** (`/api/v1/daily`)
- `GET /blueprint` - 获取交易蓝图 (支持日期查询) ✅
- `GET /blueprints` - 获取蓝图策略详情 (JSON格式) ✅
- `POST /generate-strategy` - 生成策略建议 ✅

### 第三阶段：定时任务配置 (优先级: 中)

使用 APScheduler 或 Celery Beat 配置：

| 任务 | 时间 | 频率 |
|------|------|------|
| 爬取早盘数据 | 08:55 | 每天 |
| 爬取夜盘数据 | 20:55 | 每天 |
| 爬取交易蓝图 | 21:05 | 每天 |
| 计算四维评分 | 21:10 | 每天 |
| 爬取席位数据 | 21:30 | 每天 |

### 第四阶段：前端优化 (优先级: 中)

基于现有 `小橘交易策略系统-v2.html` 进行优化：

1. **总览页面**
   - 多空 Top3 展示
   - 品种搜索功能
   - 四维雷达图

2. **详情页面**
   - 基本面研报展示
   - 资金面席位图表 (ECharts)
   - 技术面波动率曲线

3. **消息面页面**
   - 嵌入金十数据 iframe

4. **日报页面**
   - 交易蓝图展示 ✅
   - 自动生成的策略建议 ✅
   - 历史策略回溯功能 ✅

## Gemini AI 系统设计建议

完整的 Gemini AI 设计方案已保存在：
- `system_design_by_gemini.md`

核心建议：
1. 采用前后端分离架构
2. 使用 Playwright 处理动态网站
3. Redis 缓存热点数据
4. Celery 处理定时爬取任务
5. Vue3 + ECharts 前端可视化

## 现有代码复用

项目已整合现有代码：
- ✅ `/交易可查/daily_image_fetcher.py` - 优化后集成到新爬虫中
- ✅ `/智汇期讯/爬取AI解读.py` - 逻辑迁移到 `zhihui_spider.py`
- 🔄 `/小橘交易策略系统-v2.html` - 待与后端API对接

## 安全注意事项

1. ⚠️ 不要将 `.env` 文件提交到 git
2. ⚠️ 账号密码使用环境变量管理
3. ⚠️ 爬虫需遵守网站 robots.txt
4. ⚠️ 控制爬取频率，避免IP封禁

## 问题排查

### 爬虫登录失败
- 检查 `.env` 中账号密码是否正确
- 网站可能有验证码，需要手动处理
- 使用 `headless=False` 查看浏览器实际操作

### Playwright 安装失败
```bash
# 指定代理（如果需要）
export PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright/
playwright install chromium
```

### 数据库连接错误
- 确保 SQLite 文件路径有写入权限
- MySQL 需要先创建数据库：`CREATE DATABASE option_tracker;`

## 贡献者

- PM - 项目发起人
- Claude (Sonnet 4.5) - 系统架构与代码生成
- Gemini Pro - 系统设计建议

## License

Private Project - All Rights Reserved

---

**下一步行动**: 建议按照上述开发计划，优先完成剩余爬虫模块，然后开发API接口，最后对接前端页面。所有任务可以选择"yes"自动继续开发！
