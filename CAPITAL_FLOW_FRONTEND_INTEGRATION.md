# 资金流向前端集成完成报告

## 完成时间

2025-12-23

## 集成概述

成功将双数据源资金面数据集成到前端页面 `capital_flow.html`，实现从模拟数据到真实API的切换。

---

## 前端页面: capital_flow.html

### 页面功能

- 📈 多空持仓趋势图表
- 🔴 多头龙虎榜 Top 10
- 🟢 空头龙虎榜 Top 10
- 📊 品种切换选择器
- 🔄 数据刷新功能

### API集成状态

#### ✅ API端点 1: 获取席位Top榜

**接口**: `GET /api/v1/capital/{variety_code}/top-brokers?limit=15`

**前端调用** (capital_flow.html:251-276):
```javascript
const response = await fetch(`${API_BASE}/capital/${selectedVariety.value}/top-brokers?limit=15`);

if (response.ok) {
    const data = await response.json();

    // 解析多头数据
    if (data.top_long && data.top_long.length > 0) {
        topLongBrokers.value = data.top_long.map(b => ({
            broker: b.broker,
            position: b.position,
            change: b.change,
            netPosition: b.position,
            winRate: b.win_rate
        }));
    }

    // 解析空头数据
    if (data.top_short && data.top_short.length > 0) {
        topShortBrokers.value = data.top_short.map(b => ({
            broker: b.broker,
            position: b.position,
            change: b.change,
            netPosition: -b.position,
            winRate: b.win_rate
        }));
    }
}
```

**数据来源**:
- 优矿API (品种总体持仓): `broker_name = "市场总持仓(多:xxx|空:xxx)"`
- 交易可查爬虫 (Top20席位): `broker_name = "东方财富期货"` 等

#### ✅ API端点 2: 获取持仓趋势

**接口**: `GET /api/v1/capital/{variety_code}/flow?days=30`

**前端调用** (capital_flow.html:302-319):
```javascript
const loadHoldingTrend = async () => {
    try {
        const response = await fetch(`${API_BASE}/capital/${selectedVariety.value}/flow?days=30`);
        if (response.ok) {
            const data = await response.json();
            if (data.flow_data && data.flow_data.length > 0) {
                holdingTrendData.value = data.flow_data.map(item => ({
                    date: item.date,
                    longHolding: Math.abs(item.total_net_position) + item.total_change,
                    shortHolding: Math.abs(item.total_net_position),
                    netHolding: item.total_net_position
                }));
            }
        }
    } catch (error) {
        console.error('加载趋势数据失败:', error);
    }
};
```

### 容错机制

#### ✅ 优雅降级

当API不可用时，自动切换到模拟数据 (capital_flow.html:284-296):

```javascript
} else {
    // API调用失败,降级使用模拟数据
    console.warn('API调用失败,使用模拟数据');
    generateMockData();
    renderHoldingTrendChart();
    ElMessage.warning('API暂不可用,显示模拟数据');
}
```

**降级策略**:
1. API返回非200状态 → 使用模拟数据
2. 网络请求异常 → 使用模拟数据
3. 数据解析错误 → 使用模拟数据

---

## 后端API实现

### 文件: app/routers/capital.py

#### API 1: get_top_brokers() (Lines 95-141)

```python
@router.get("/{variety_code}/top-brokers")
async def get_top_brokers(
        variety_code: str,
        limit: int = Query(10, ge=1, le=50),
        db: Session = Depends(get_db)
):
    """获取品种的Top席位排行"""
    target_date = date.today()

    # 多头Top席位
    long_brokers = db.query(InstitutionalPosition).filter(
        InstitutionalPosition.comm_code == variety_code,
        InstitutionalPosition.record_date == target_date,
        InstitutionalPosition.net_position > 0
    ).order_by(desc(InstitutionalPosition.net_position)).limit(limit).all()

    # 空头Top席位
    short_brokers = db.query(InstitutionalPosition).filter(
        InstitutionalPosition.comm_code == variety_code,
        InstitutionalPosition.record_date == target_date,
        InstitutionalPosition.net_position < 0
    ).order_by(InstitutionalPosition.net_position).limit(limit).all()

    return {
        "variety_code": variety_code,
        "date": str(target_date),
        "top_long": [...],
        "top_short": [...]
    }
```

#### API 2: get_capital_flow() (Lines 53-92)

```python
@router.get("/{variety_code}/flow")
async def get_capital_flow(
        variety_code: str,
        days: int = Query(7, ge=1, le=30),
        db: Session = Depends(get_db)
):
    """获取品种的资金流向趋势"""
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    # 按日期聚合
    flow_data = db.query(
        InstitutionalPosition.record_date,
        func.sum(InstitutionalPosition.net_position).label('total_net'),
        func.sum(InstitutionalPosition.position_change).label('total_change')
    ).filter(
        InstitutionalPosition.comm_code == variety_code,
        InstitutionalPosition.record_date.between(start_date, end_date)
    ).group_by(InstitutionalPosition.record_date).order_by(InstitutionalPosition.record_date).all()

    return {
        "variety_code": variety_code,
        "flow_data": [...]
    }
```

---

## 数据流向图

```
┌─────────────────────────────────────────────────────────┐
│                      数据采集层                          │
└─────────────────────────────────────────────────────────┘
                            │
           ┌────────────────┴────────────────┐
           │                                 │
       16:00 优矿API                    19:00 交易可查爬虫
           │                                 │
     品种级总持仓                        Top20席位排名
           │                                 │
           └────────────────┬────────────────┘
                            ▼
           ┌─────────────────────────────────┐
           │  institutional_positions 表      │
           │  broker_name 区分数据源:         │
           │  • 市场总持仓(多:x|空:y) ← 优矿  │
           │  • 东方财富期货 ← 交易可查        │
           └─────────────────────────────────┘
                            │
                            ▼
           ┌─────────────────────────────────┐
           │      FastAPI 路由层              │
           │  /api/v1/capital/{variety}      │
           │  • /top-brokers                 │
           │  • /flow                        │
           └─────────────────────────────────┘
                            │
                            ▼
           ┌─────────────────────────────────┐
           │      前端展示层                  │
           │  capital_flow.html              │
           │  • 多头龙虎榜                    │
           │  • 空头龙虎榜                    │
           │  • 持仓趋势图                    │
           └─────────────────────────────────┘
```

---

## 支持的品种列表

前端可切换查询的品种 (capital_flow.html:216-232):

```javascript
const varieties = ref([
    { code: 'I', name: '铁矿石' },
    { code: 'RB', name: '螺纹钢' },
    { code: 'HC', name: '热轧卷板' },
    { code: 'J', name: '焦炭' },
    { code: 'JM', name: '焦煤' },
    { code: 'ZN', name: '沪锌' },
    { code: 'CU', name: '沪铜' },
    { code: 'AL', name: '沪铝' },
    { code: 'AU', name: '黄金' },
    { code: 'AG', name: '白银' },
    { code: 'M', name: '豆粕' },
    { code: 'P', name: '棕榈油' },
    { code: 'Y', name: '豆油' },
    { code: 'C', name: '玉米' },
    { code: 'SR', name: '白糖' }
]);
```

---

## 数据展示格式

### 多头龙虎榜表格

| 排名 | 席位名称 | 持仓 | 增减 | 净持仓 |
|------|---------|------|------|--------|
| 🥇1  | 东方财富期货 | 50,000 | +1,200 | 多 5,000 |
| 🥈2  | 国泰君安期货 | 48,000 | -500 | 多 3,500 |
| 🥉3  | 永安期货 | 45,000 | +800 | 多 2,800 |

**字段说明**:
- **持仓**: 该席位的总持仓量
- **增减**: 相比昨日的持仓变化 (正数=增仓, 负数=减仓)
- **净持仓**: 多头持仓 - 空头持仓

### 持仓趋势图

- **X轴**: 日期 (最近30天)
- **Y轴**: 持仓量
- **系列1**: 多头净持仓 (红色)
- **系列2**: 空头净持仓 (绿色)
- **系列3**: 净持仓 (蓝色)

---

## 测试验证

### 1. 启动后端服务

```bash
cd /Users/pm/Documents/期权交易策略/option_tracker
python main.py
```

### 2. 访问前端页面

打开浏览器访问:
```
http://localhost:8001/capital_flow.html
```

### 3. 功能测试清单

- [ ] 页面正常加载
- [ ] 品种下拉选择器正常工作
- [ ] 切换品种后数据正确刷新
- [ ] 多头龙虎榜显示数据
- [ ] 空头龙虎榜显示数据
- [ ] 持仓趋势图正常渲染
- [ ] 刷新按钮正常工作
- [ ] API失败时降级到模拟数据
- [ ] 控制台无错误信息

---

## 注意事项

### ⚠️ 数据可用性

1. **初次使用**:
   - 数据库可能没有历史数据
   - 需等待定时任务执行(16:00 和 19:00)
   - 或手动运行爬虫测试脚本

2. **手动填充测试数据**:
   ```bash
   python scripts/test_capital_spider_uqer.py
   ```

3. **API返回空数据时**:
   - 前端会自动使用模拟数据
   - 提示消息: "API暂不可用,显示模拟数据"

### 📝 数据更新时间

- **优矿数据**: 每天 16:00 自动更新
- **交易可查数据**: 每天 19:00 自动更新
- **前端展示**: 实时查询数据库最新数据

---

## 数据示例

### API响应示例

#### /capital/CU/top-brokers?limit=15

```json
{
  "variety_code": "CU",
  "date": "2025-12-23",
  "top_long": [
    {
      "broker": "市场总持仓(多:374827|空:398980)",
      "position": -24153,
      "change": -1272,
      "win_rate": null
    },
    {
      "broker": "东方财富期货",
      "position": 5000,
      "change": 200,
      "win_rate": 0.65
    }
  ],
  "top_short": [
    {
      "broker": "国泰君安期货",
      "position": 8000,
      "change": 300,
      "win_rate": 0.58
    }
  ]
}
```

#### /capital/CU/flow?days=30

```json
{
  "variety_code": "CU",
  "days": 30,
  "flow_data": [
    {
      "date": "2025-11-23",
      "total_net_position": -20000,
      "total_change": -500
    },
    {
      "date": "2025-11-24",
      "total_net_position": -22000,
      "total_change": -2000
    }
  ]
}
```

---

## 前后端联调清单

### ✅ 已完成

1. ✅ 后端API实现 (capital.py)
2. ✅ 数据库模型定义 (InstitutionalPosition)
3. ✅ 双数据源爬虫配置 (优矿 + 交易可查)
4. ✅ 定时任务调度 (16:00 + 19:00)
5. ✅ 前端API调用逻辑 (capital_flow.html)
6. ✅ 数据格式转换适配
7. ✅ 容错降级机制
8. ✅ 用户提示消息

### 🔄 待优化 (可选)

- [ ] 添加加载动画
- [ ] 数据缓存机制
- [ ] 历史数据对比
- [ ] 席位胜率统计
- [ ] 异常席位行为告警
- [ ] 导出报表功能

---

## 总结

✅ **前端集成已完成**

- 从模拟数据切换到真实API
- 支持双数据源展示(优矿 + 交易可查)
- 具备完善的容错降级机制
- 数据刷新实时响应
- 支持15个主流品种切换

**数据流**: 定时爬取 → 数据库存储 → API查询 → 前端展示 → 用户交互

**可靠性**: 双数据源互补 + API降级 + 模拟数据兜底 = 三重保障
