# 双数据源资金面数据方案

## 方案概述

采用**优矿 + 交易可查**双数据源配合使用,互补优势,全方位覆盖资金面数据。

## 数据源分工

### 数据源1: 优矿 (品种总体趋势)

**API**: `DataAPI.MktFutOiRatioGet`

**执行时间**: 每天 16:00

**数据类型**: 品种级别的多空总持仓

**返回字段**:
```python
{
    'contractObject': 'CU',           # 品种代码
    'contractObjectCn': '阴极铜',      # 品种中文名
    'tradeDate': '2025-12-19',        # 交易日期
    'longOpenInt': 378450,            # 多单总持仓量
    'shortOpenInt': 395151,           # 空单总持仓量
    'ratio': 104.413,                 # 多空比
}
```

**优势**:
- ✅ 官方API,数据权威可靠
- ✅ 稳定性好,不会失效
- ✅ 涵盖所有品种
- ✅ 反映市场整体多空力量对比

**应用场景**:
- 判断品种整体多空趋势
- 计算市场净持仓(多单-空单)
- 监控持仓变化趋势

**示例数据**:
```
铜(CU):
  多单持仓: 374,827
  空单持仓: 398,980
  净持仓: -24,153 (空头占优)
  持仓变化: -1,272
```

---

### 数据源2: 交易可查 (具体席位分布)

**来源**: 网页爬虫

**执行时间**: 每天 19:00 (随交易蓝图一起爬取)

**数据类型**: Top20席位排名

**返回字段**:
```python
{
    'broker_name': '东方财富期货',     # 席位名称
    'net_position': 12000,           # 净持仓
    'position_change': 500,          # 持仓变化
    'win_rate': 0.65                 # 历史胜率(如有)
}
```

**优势**:
- ✅ 具体席位排名,可识别机构行为
- ✅ Top20席位详细数据
- ✅ 可分析机构vs散户
- ✅ 免费获取

**应用场景**:
- 识别强势席位
- 追踪明星席位动向
- 分析机构资金流向

**爬取品种**:
```python
['rb', 'hc', 'i', 'j', 'jm',  # 黑色系
 'cu', 'al', 'zn', 'au', 'ag'] # 有色金属
```

---

## 数据互补关系

| 维度 | 优矿 | 交易可查 |
|------|------|---------|
| 数据粒度 | 品种级总量 | 席位级明细 |
| 覆盖范围 | 全品种 | 10个主流品种 |
| 数据深度 | 总持仓+比例 | Top20席位 |
| 可靠性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| 更新时间 | 16:00 | 19:00 |
| 分析维度 | 宏观趋势 | 微观结构 |

### 互补示例

**场景**: 分析铜的资金面

**优矿数据显示**:
- 净持仓: -24,153 (空头占优)
- 持仓变化: -1,272 (空头增加)

**交易可查数据显示**:
- 东方财富: 净多单 +5,000
- 国泰君安: 净空单 -8,000
- 东证期货: 净空单 -6,000

**综合分析**:
市场整体偏空,且主力席位分歧:东方财富看多,国泰君安、东证期货看空,空方力量更强。

---

## 数据存储

### 数据库表: `institutional_positions`

```sql
CREATE TABLE institutional_positions (
    id INTEGER PRIMARY KEY,
    comm_code VARCHAR(20),        -- 品种代码
    broker_name VARCHAR(50),      -- 席位/来源标识
    net_position INTEGER,         -- 净持仓
    position_change INTEGER,      -- 持仓变化
    win_rate FLOAT,              -- 胜率
    record_date DATE,            -- 记录日期
    created_at TIMESTAMP
);
```

### broker_name 格式区分

**优矿数据**:
```python
broker_name = "市场总持仓(多:374827|空:398980)"
```

**交易可查数据**:
```python
broker_name = "东方财富期货"
broker_name = "国泰君安期货"
```

### 查询示例

```python
from datetime import date
from app.models.database import SessionLocal
from app.models.models import InstitutionalPosition

db = SessionLocal()

# 1. 查询品种总体趋势(优矿数据)
market_total = db.query(InstitutionalPosition).filter(
    InstitutionalPosition.comm_code == 'cu',
    InstitutionalPosition.broker_name.like('市场总持仓%'),
    InstitutionalPosition.record_date == date.today()
).first()

# 2. 查询具体席位排名(交易可查数据)
top_brokers = db.query(InstitutionalPosition).filter(
    InstitutionalPosition.comm_code == 'CU',
    ~InstitutionalPosition.broker_name.like('市场总持仓%'),
    InstitutionalPosition.record_date == date.today()
).order_by(InstitutionalPosition.net_position.desc()).limit(10).all()
```

---

## 定时任务配置

### 1. 优矿席位数据 (16:00)

```python
@DataCollector(
    source_name="优矿-席位持仓",
    max_retries=3,
    retry_delay=600,
    timeout=600,
    enable_alert=True
)
def crawl_capital_positions_uqer():
    """优矿席位持仓数据爬取"""
    spider = CapitalSpiderUqer()
    result = spider.update_all_positions(top_n=20)
    return result
```

**调度配置**:
```python
scheduler.add_job(
    crawl_capital_positions_uqer,
    CronTrigger(hour=16, minute=0),
    id='crawl_capital_positions_uqer',
    name='优矿-席位持仓-16:00'
)
```

### 2. 交易可查席位数据 (19:00)

```python
@DataCollector(
    source_name="交易可查-每日蓝图",
    max_retries=3,
    retry_delay=1800,
    timeout=300,
    enable_alert=True
)
async def crawl_jiaoyikecha():
    """交易可查爬虫 - 蓝图 + 席位数据"""
    spider = JiaoyiKechaSpider()
    await spider.init_browser(headless=True)

    if await spider.login():
        # 1. 获取交易蓝图
        blueprint = await spider.fetch_daily_blueprint()

        # 2. 获取席位数据
        await _crawl_jyk_positions(spider)

    await spider.close()
```

**调度配置**:
```python
scheduler.add_job(
    crawl_jiaoyikecha,
    CronTrigger(hour=19, minute=0),
    id='crawl_jiaoyikecha',
    name='交易可查-19:00'
)
```

---

## 数据采集流程

```
┌─────────────────────────────────────────┐
│         每日数据采集时间轴               │
└─────────────────────────────────────────┘

16:00 ──► 优矿爬取启动
          ├─ 获取所有品种多空持仓比例
          ├─ 计算净持仓和持仓变化
          └─ 保存到 institutional_positions
               broker_name = "市场总持仓(多:xxx|空:xxx)"

19:00 ──► 交易可查爬取启动
          ├─ 获取交易蓝图图片
          ├─ AI解析蓝图策略
          ├─ 爬取Top20席位持仓
          │   ├─ rb, hc, i, j, jm
          │   └─ cu, al, zn, au, ag
          └─ 保存到 institutional_positions
               broker_name = "东方财富期货" 等
```

---

## 数据质量监控

### DataCollector 自动监控

两个数据源都集成了`DataCollector`装饰器:

```python
✅ 自动记录采集日志
✅ 失败自动重试 (3次)
✅ 数据质量评分
✅ 飞书告警通知
✅ 更新健康状态
```

### 监控指标

**优矿数据源**:
- 采集品种数
- 数据完整性
- API响应时间

**交易可查数据源**:
- 登录成功率
- 席位数据条数
- 蓝图解析成功率

---

## API 接口使用

### 获取品种资金面数据

```python
# API: GET /api/capital/{variety_code}/positions
# 返回: 优矿总持仓 + 交易可查Top20席位

{
    "variety_code": "cu",
    "date": "2025-12-23",
    "market_total": {
        "source": "优矿",
        "long_oi": 374827,
        "short_oi": 398980,
        "net_position": -24153,
        "position_change": -1272
    },
    "top_brokers": [
        {
            "source": "交易可查",
            "broker": "东方财富期货",
            "net_position": 5000,
            "change": 200,
            "rank": 1
        },
        ...
    ]
}
```

---

## 优势总结

### ✅ 双数据源互补

1. **宏观+微观**: 既有整体趋势,又有席位细节
2. **权威+实时**: 优矿官方数据 + 交易可查实时爬取
3. **广度+深度**: 全品种覆盖 + 主流品种深度分析
4. **稳定+灵活**: API稳定 + 爬虫可调整

### ✅ 分析维度丰富

- **趋势判断**: 看净持仓正负
- **力量对比**: 看多空比例
- **机构行为**: 看Top席位动向
- **资金流向**: 看持仓变化

### ✅ 风险分散

- 单一数据源失效不影响整体
- 数据交叉验证提高可靠性
- 多维度分析降低误判

---

## 后续优化方向

1. **数据融合展示**
   - 在前端同时显示两个数据源
   - 标注数据来源
   - 突出显示数据差异

2. **智能分析**
   - 当市场总持仓与Top20席位方向相反时告警
   - 识别异常席位行为
   - 计算机构vs散户持仓比

3. **历史回测**
   - 统计席位胜率
   - 分析席位跟随效果
   - 优化席位选择策略

---

## 总结

✅ **双数据源方案已完成配置**

- 优矿: 16:00 品种总体趋势
- 交易可查: 19:00 席位排名明细
- 数据互补,分析更全面
- 自动采集,监控完善

**数据流**: 两个数据源 → 同一张表 → 通过broker_name区分 → API统一返回

**可靠性**: 即使一个数据源失效,另一个依然可用,确保资金面数据持续可得。
