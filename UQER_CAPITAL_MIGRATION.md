# 优矿资金数据源切换完成报告

## 项目概述

成功将资金面数据源从交易可查切换到优矿平台,使用优矿提供的官方期货数据API。

## 完成时间

2025-12-23

## 使用的API

**DataAPI.MktFutOiRatioGet** - 期货多空持仓比例

### API说明
- **功能**: 获取品种级别的多空总持仓数据
- **数据粒度**: 品种级(非席位级)
- **更新频率**: 日度
- **权限**: 您的token可正常访问

### 返回字段
```python
{
    'contractObject': 'CU',           # 品种代码
    'contractObjectCn': '阴极铜',      # 品种中文名
    'tradeDate': '2025-12-19',        # 交易日期
    'longOpenInt': 378450,            # 多单总持仓
    'shortOpenInt': 395151,           # 空单总持仓
    'ratio': 104.413,                 # 多空比
    'prodID': 165                     # 产品ID
}
```

## 实施内容

### 1. SDK客户端扩展 ✅

**文件**: `app/services/uqer_sdk_client.py`

新增方法:
- `get_member_positions()`: 期货会员持仓排名(需专业版,保留接口)
- `get_net_positions()`: 计算净持仓(需专业版,保留接口)
- `get_oi_ratio()`: **获取多空持仓比例(当前使用)** ✅

代码位置: `uqer_sdk_client.py:210-392`

### 2. 资金爬虫实现 ✅

**文件**: `app/crawlers/capital_spider_uqer.py`

核心功能:
```python
class CapitalSpiderUqer:
    def fetch_variety_positions(variety_code, target_date):
        """获取单个品种的多空持仓数据"""

    def fetch_all_varieties_positions(target_date):
        """批量获取所有品种"""

    def save_positions_to_db(variety_code, positions):
        """保存到数据库"""

    def update_all_positions(target_date):
        """一键更新所有品种到数据库"""
```

特点:
- 自动品种代码映射(小写→大写)
- 自动交易所识别
- 计算持仓变化(对比前3天数据)
- 完整的错误处理和日志

### 3. 定时任务配置 ✅

**文件**: `app/scheduler.py`

```python
@DataCollector(
    source_name="优矿-席位持仓",
    max_retries=3,
    retry_delay=600,
    timeout=600,
    enable_alert=True
)
def crawl_capital_positions_uqer():
    """优矿席位持仓数据爬取 - 每天16:00"""
```

调度配置:
- 执行时间: 每天16:00
- 自动重试: 3次,间隔10分钟
- 监控告警: 启用
- 数据治理: 自动记录采集日志

代码位置: `scheduler.py:373-403, 584-591`

### 4. 数据源注册 ✅

**文件**: `scripts/init_data_sources.py`

注册信息:
```python
{
    "source_name": "优矿-席位持仓",
    "source_type": "api",
    "category": "capital",
    "provider": "优矿(Uqer)",
    "update_frequency": "daily",
    "data_fields": [
        "contractObject", "contractObjectCn", "tradeDate",
        "longOpenInt", "shortOpenInt", "ratio"
    ]
}
```

## 测试结果

### 测试脚本
`scripts/test_capital_spider_uqer.py`

### 测试结果 ✅

```
============================================================
测试总结
============================================================
✅ PASS - 单个品种测试
✅ PASS - 保存到数据库测试
✅ PASS - 多个品种测试
============================================================
```

### 示例数据

**铜(CU)**:
- 多单持仓: 374,827
- 空单持仓: 398,980
- 净持仓: -24,153 (空头占优)
- 持仓变化: -1,272

**黄金(AU)**:
- 多单持仓: 数据可获取
- 空单持仓: 数据可获取
- 净持仓: +149,140 (多头占优)

## 数据对比

### 优矿数据 vs 交易可查数据

| 维度 | 优矿(当前) | 交易可查(原有) |
|------|-----------|---------------|
| 数据来源 | 官方API | 网页爬虫 |
| 数据粒度 | 品种级总持仓 | 席位排名Top20 |
| 数据可靠性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| 更新及时性 | T+0日 | T+0日 |
| 稳定性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ (易失效) |
| 数据详细度 | 总量 | 具体席位 |

### 数据结构变化

**原有格式** (交易可查):
```python
{
    'broker_name': '东方财富期货',
    'net_position': 12000,
    'position_change': 500,
    'win_rate': 0.65
}
```

**新格式** (优矿):
```python
{
    'broker_name': '市场总持仓(多:374827|空:398980)',
    'net_position': -24153,
    'position_change': -1272,
    'win_rate': None
}
```

## 优势与限制

### ✅ 优势

1. **数据可靠**: 来自官方API,权威性高
2. **稳定性好**: 不依赖网页结构,不会因页面改版失效
3. **易维护**: 无需处理登录、验证码等问题
4. **监控完善**: 集成DataCollector自动监控和告警
5. **成本低**: 免费token即可使用

### ⚠️ 限制

1. **数据粒度**: 只有品种级总持仓,没有具体席位排名
2. **无胜率数据**: 不提供席位历史胜率
3. **免费限制**:
   - ❌ 无法访问`MktFutMLRGet`(会员多单排名)
   - ❌ 无法访问`MktFutMSRGet`(会员空单排名)
   - ❌ 无法访问`MktFutMTRGet`(会员总排名)
   - ❌ 无法访问`MktFutTdaGet`(成交持仓汇总)
   - ✅ 可访问`MktFutOiRatioGet`(多空持仓比例)

## 未来升级路径

如果需要更详细的席位数据,可考虑:

1. **升级优矿专业版**
   - 解锁全部期货数据API
   - 获取Top20席位排名详情
   - 费用: 咨询 400-0820-386

2. **保留双数据源**
   - 优矿: 品种级总体趋势
   - 交易可查: 具体席位排名
   - 互补验证,提高可靠性

3. **其他数据源**
   - Wind/Choice (需付费)
   - 交易所官网 (需爬虫)

## 启用方式

### 1. 注册数据源
```bash
cd /Users/pm/Documents/期权交易策略/option_tracker
python scripts/init_data_sources.py
```

### 2. 启动定时任务
定时任务已配置在`scheduler.py`中,系统启动时自动加载:
```bash
python main.py
```

### 3. 手动测试
```bash
python scripts/test_capital_spider_uqer.py
```

## 数据查询示例

```python
from app.models.database import SessionLocal
from app.models.models import InstitutionalPosition
from datetime import date

db = SessionLocal()

# 查询铜的持仓数据
positions = db.query(InstitutionalPosition).filter(
    InstitutionalPosition.comm_code == 'cu',
    InstitutionalPosition.record_date == date.today()
).all()

for pos in positions:
    print(f"{pos.broker_name}: 净持仓={pos.net_position}, 变化={pos.position_change}")
```

## 文件清单

### 新增文件
- `app/crawlers/capital_spider_uqer.py` - 优矿资金爬虫
- `scripts/test_capital_spider_uqer.py` - 测试脚本
- `UQER_CAPITAL_MIGRATION.md` - 本文档

### 修改文件
- `app/services/uqer_sdk_client.py` - 扩展SDK方法
- `app/scheduler.py` - 添加定时任务
- `scripts/init_data_sources.py` - 注册数据源

## 总结

✅ 成功完成资金数据源从交易可查到优矿的切换
✅ 所有测试通过,数据采集正常
✅ 集成到定时任务系统,每天16:00自动更新
✅ 提供品种级别的多空持仓数据,反映市场整体资金面

虽然因免费版限制无法获取详细的席位排名,但**品种级的多空总持仓数据足以反映资金面整体趋势**,且数据更加稳定可靠。
