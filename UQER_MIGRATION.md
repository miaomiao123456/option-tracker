# 优矿数据源迁移指南

## 概述

本项目已将数据源从 AKShare **完全迁移**到优矿(uqer.datayes.com)平台,以获取更稳定、全面和权威的期货数据。

## 迁移内容

### 1. 虚实比数据 ✅ 已完全迁移
- **原数据源**: AKShare
  - `ak.futures_inventory_em()` - 仓单数据
  - `ak.futures_zh_daily_sina()` - 持仓量数据

- **新数据源**: 优矿API (已完全迁移)
  - 仓单数据: `DataAPI.MktFutWRdGet` - 期货仓单日报
  - 持仓量数据: `DataAPI.MktFutdGet` - 期货日行情(包含持仓量openInt)

### 2. 期限结构数据 ✅ 已完全迁移
- **原数据源**: AKShare `ak.futures_main_sina()`
- **新数据源**: 优矿API
  - `DataAPI.FutuGet` - 获取期货合约信息
  - `DataAPI.MktFutdGet` - 获取期货日行情数据

## 配置步骤

### 1. 获取优矿API Token

1. 访问 [优矿平台](https://uqer.datayes.com)
2. 注册/登录账号
3. 进入"个人中心" -> "API管理"
4. 获取您的 API Token

### 2. 配置环境变量

在项目根目录的 `.env` 文件中添加优矿Token:

```env
# 优矿API配置
UQER_TOKEN=your_uqer_token_here
```

### 3. 使用新的数据爬虫

#### 虚实比数据爬取

```python
from app.crawlers.virtual_real_ratio_spider_uqer import VirtualRealRatioSpiderUqer
from app.services.uqer_client import init_uqer_client
from config.settings import get_settings

# 初始化优矿客户端
settings = get_settings()
init_uqer_client(settings.UQER_TOKEN)

# 创建爬虫实例
spider = VirtualRealRatioSpiderUqer()

# 爬取单个品种
spider.crawl_single_variety("AU")  # 沪金

# 爬取所有品种
results = spider.crawl_all_varieties()
```

#### 期限结构数据更新

```python
from option_tracker.scripts.update_term_structure_data_uqer import TermStructureUpdaterUqer

# 创建更新器
updater = TermStructureUpdaterUqer()

# 更新所有品种数据
all_data, recommended_data = updater.update_all_varieties()
```

或者直接运行脚本:

```bash
cd option_tracker
python scripts/update_term_structure_data_uqer.py
```

## 新增文件说明

### 核心模块

1. **`app/services/uqer_client.py`** - 优矿API客户端
   - `UqerClient` 类: 封装优矿API调用
   - `get_futures_contracts()`: 获取期货合约信息
   - `get_futures_daily()`: 获取期货日行情
   - `get_main_contract_daily()`: 获取主力合约行情

2. **`app/crawlers/virtual_real_ratio_spider_uqer.py`** - 基于优矿的虚实比爬虫
   - 使用优矿API获取持仓量数据
   - 仓单数据暂时保留AKShare (优矿无对应接口)

3. **`scripts/update_term_structure_data_uqer.py`** - 基于优矿的期限结构数据更新脚本
   - 完全使用优矿API获取合约和行情数据
   - 支持所有主要期货品种

### 配置更新

- **`config/settings.py`**: 新增 `UQER_TOKEN` 配置项

## API使用说明

### 优矿API端点

#### 1. DataAPI.FutuGet - 获取期货合约信息

```python
client = get_uqer_client()
contracts = client.get_futures_contracts(
    contract_object="cu",  # 合约标的(铜)
    exchange_cd="XSGE",    # 交易所(上期所)
    contract_status="1"    # 上市交易
)
```

返回字段:
- `secID`: 证券编码
- `ticker`: 合约代码
- `contractObject`: 合约标的
- `exchangeCD`: 交易所
- `lastTradeDate`: 最后交易日
- `contMultNum`: 合约乘数

#### 2. DataAPI.MktFutdGet - 获取期货日行情

```python
client = get_uqer_client()
daily_data = client.get_futures_daily(
    ticker="cu2501",            # 合约代码
    begin_date="20250101",      # 开始日期
    end_date="20250131",        # 结束日期
    exchange_cd="XSGE"          # 交易所
)
```

返回字段:
- `tradeDate`: 交易日期
- `ticker`: 合约代码
- `openPrice`: 开盘价
- `highestPrice`: 最高价
- `lowestPrice`: 最低价
- `closePrice`: 收盘价
- `settlPrice`: 结算价
- `turnoverVol`: 成交量
- `turnoverValue`: 成交金额
- `openInt`: **持仓量** (用于虚实比计算)

#### 3. DataAPI.MktFutWRdGet - 获取期货仓单日报 (新增)

```python
client = get_uqer_client()
warehouse_data = client.get_warehouse_receipt(
    contract_object="CU",       # 品种代码(大写)
    exchange_cd="XSGE",         # 交易所
    begin_date="20250101",      # 开始日期
    end_date="20250131"         # 结束日期
)
```

返回字段:
- `tradeDate`: 交易日期
- `contractObject`: 品种代码
- `exchangeCD`: 交易市场
- `prevWarehouseStock`: 上期仓单量
- `warehouseStock`: **本期仓单量** (用于虚实比计算)
- `warehouseStockChg`: **仓单量增减** (用于虚实比计算)

### 品种代码映射

#### 交易所代码
- `XSGE`: 上海期货交易所
- `XDCE`: 大连商品交易所
- `XZCE`: 郑州商品交易所
- `CCFX`: 中国金融期货交易所

#### 合约标的格式 (重要变更)

**仓单数据API (MktFutWRdGet) 要求使用大写品种代码:**

| 交易所 | 品种示例 | 仓单API格式 | 行情API格式 |
|--------|---------|------------|------------|
| 上期所 | 铜 | `CU` | `cu` |
| 上期所 | 黄金 | `AU` | `au` |
| 大商所 | 铁矿石 | `I` | `i` |
| 大商所 | 豆粕 | `M` | `m` |
| 郑商所 | 白糖 | `SR` | `SR` |
| 郑商所 | 棉花 | `CF` | `CF` |

注意:
- 上期所和大商所的**仓单API**使用**大写**字母
- 上期所和大商所的**行情API**使用**小写**字母
- 郑商所统一使用大写字母

## 数据对比

### 虚实比数据 - ✅ 已完全迁移

| 数据项 | AKShare来源 | 优矿来源 | 状态 |
|--------|------------|----------|------|
| 仓单量 | `futures_inventory_em` | `MktFutWRdGet.warehouseStock` | ✅ 已迁移 |
| 仓单增减 | `futures_inventory_em` | `MktFutWRdGet.warehouseStockChg` | ✅ 已迁移 |
| 持仓量 | `futures_zh_daily_sina` | `MktFutdGet.openInt` | ✅ 已迁移 |
| 主力合约 | 自动识别 | 按持仓量筛选 | ✅ 已迁移 |

**迁移状态**: 100% 完成,无需依赖AKShare

### 期限结构数据 - ✅ 已完全迁移

| 数据项 | AKShare来源 | 优矿来源 | 状态 |
|--------|------------|----------|------|
| 合约列表 | `futures_main_sina` | `FutuGet` | ✅ 已迁移 |
| 合约价格 | `futures_main_sina` | `MktFutdGet` | ✅ 已迁移 |
| 成交量 | `futures_main_sina` | `MktFutdGet.turnoverVol` | ✅ 已迁移 |
| 持仓量 | `futures_main_sina` | `MktFutdGet.openInt` | ✅ 已迁移 |

**迁移状态**: 100% 完成,无需依赖AKShare

## 注意事项

### 1. 数据完整性 ✅
所有数据已完全迁移到优矿API,包括:
- ✅ 仓单数据 (使用 `DataAPI.MktFutWRdGet`)
- ✅ 持仓量数据 (使用 `DataAPI.MktFutdGet`)
- ✅ 期限结构数据 (使用 `DataAPI.FutuGet` + `DataAPI.MktFutdGet`)

**无需保留 AKShare 依赖**,可完全使用优矿平台数据。

### 2. 品种代码格式
优矿不同API对品种代码的大小写要求不同:
- **仓单API**: 必须使用大写,如 `CU`, `AU`, `I`, `M`
- **行情API(上期所/大商所)**: 使用小写,如 `cu`, `au`, `i`, `m`
- **郑商所**: 统一使用大写,如 `SR`, `CF`, `TA`

代码中已做好映射处理,无需手动转换。

### 3. API限流
优矿API可能有请求频率限制,建议:
- 在循环中添加适当的延迟 (`time.sleep(0.2)`)
- 使用缓存机制减少重复请求
- 合理安排定时任务执行时间

### 4. 数据更新时间
- 期货结算价通常在 16:20 更新
- 仓单数据每日更新
- 建议在 15:05 或更晚时间运行数据更新脚本
- 周末和节假日无数据

### 5. 错误处理
新的爬虫已添加完善的错误处理和日志记录。如遇到问题:
1. 检查日志输出
2. 确认 Token 配置正确
3. 验证网络连接
4. 查看优矿API文档确认接口状态

## 兼容性说明

### AKShare依赖状态
- ✅ **已完全移除对AKShare的依赖**
- 所有数据源已迁移到优矿API
- 可安全卸载AKShare (如果项目其他部分不需要)

### 数据库结构
无需修改,新爬虫保持与原数据库结构完全兼容。

### API接口
原有的 FastAPI 路由无需修改,数据格式保持一致。

## 测试建议

### 1. 测试优矿API连接

```python
from app.services.uqer_client import UqerClient

token = "your_token_here"
client = UqerClient(token)

# 测试获取铜合约
contracts = client.get_futures_contracts(contract_object="cu", exchange_cd="XSGE")
print(contracts.head() if contracts is not None else "连接失败")

# 测试获取仓单数据
warehouse = client.get_warehouse_receipt(contract_object="CU", exchange_cd="XSGE")
print(warehouse if warehouse is not None else "仓单数据获取失败")
```

### 2. 测试虚实比爬虫

```bash
cd option_tracker
python -c "from app.crawlers.virtual_real_ratio_spider_uqer import VirtualRealRatioSpiderUqer; spider = VirtualRealRatioSpiderUqer(); spider.crawl_single_variety('AU')"
```

### 3. 测试期限结构更新

```bash
cd option_tracker
python scripts/update_term_structure_data_uqer.py
```

## 迁移建议

### 完整切换方案
由于已100%完成迁移,建议:
1. 测试优矿API连接和数据获取
2. 验证数据准确性
3. 对比新旧数据源结果(可选)
4. 确认无误后直接使用新爬虫
5. 可考虑移除AKShare依赖

### 回滚方案
如需回退到 AKShare (不推荐):
1. 继续使用原有的爬虫文件
   - `app/crawlers/virtual_real_ratio_spider.py`
   - `scripts/update_term_structure_data.py`
2. 原文件已保留,无需修改

## 技术支持

如遇到问题或需要优化,请联系开发团队或提交 Issue。

---

**更新日期**: 2025-12-08
**版本**: v1.0
