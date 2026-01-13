# 研报API数据源修复报告

## 问题描述

用户在"研报详情"页面（`report_detail.html`）看到：
- 错误提示："研报汇总加载失败"
- 空白页面显示："无法加载研报数据"

## 根本原因

`/api/v1/zhihui/research-reports` 端点使用了过时的数据源：
- **旧数据源**：`research_reports` 表 - 只有到2025-12-03的数据
- **查询日期**：用户查看2025-12-17和2025-12-23的数据
- **结果**：API尝试实时爬取数据，但失败后返回空数据

## 修复方案

### 修改的文件
`app/routers/zhihui.py` - lines 138-195

### 修复内容

将`/api/v1/zhihui/research-reports`端点的数据源从`research_reports`表改为`market_full_view`表：

**修复前：**
```python
# 从research_reports表查询
reports = db.query(ResearchReport).filter(
    ResearchReport.publish_date == target_date
).all()

# 如果没有数据,尝试爬取
if not reports:
    spider = ZhihuiQixunSpider()
    reports_data = spider.fetch_research_reports(...)
    # ... 保存到数据库
```

**修复后：**
```python
# 从market_full_view表查询
query = db.query(MarketFullView).filter(
    MarketFullView.record_date == target_date
)

# 如果指定了品种代码,则筛选
if comm_code:
    query = query.filter(MarketFullView.comm_code == comm_code.upper())

market_data_list = query.all()

# 转换为研报格式
reports_list = [
    {
        "report_id": f"{data.comm_code}_{target_date.strftime('%Y%m%d')}",
        "comm_code": data.comm_code,
        "variety_name": data.variety_name,
        "institution_name": "智汇期讯机构汇总",
        "view_port": data.more_port,
        "sentiment": data.main_sentiment,
        "trade_logic": f"看多{data.excessive_num}家({data.excessive_ratio:.1f}%)，中性{data.neutral_num}家({data.neutral_ratio:.1f}%)，看空{data.empty_num}家({data.empty_ratio:.1f}%)",
        "related_data": f"共{data.total_num}家机构发表观点",
        "risk_factor": f"主流观点占比{data.more_rate:.1f}%，请关注市场情绪变化",
        "report_link": ""
    }
    for data in market_data_list
]
```

### 新增功能

增加了可选的`comm_code`参数，支持按品种代码筛选研报：
```python
comm_code: Optional[str] = Query(None, description="品种代码筛选,如RB")
```

## 测试验证

### 测试命令

```bash
# 1. 测试2025-12-17数据（用户截图日期）
curl "http://localhost:8001/api/v1/zhihui/research-reports?query_date=2025-12-17"

# 2. 测试2025-12-23数据（最新日期）
curl "http://localhost:8001/api/v1/zhihui/research-reports?query_date=2025-12-23"

# 3. 测试品种筛选
curl "http://localhost:8001/api/v1/zhihui/research-reports?query_date=2025-12-23&comm_code=AG"
```

### 测试结果

| 测试场景 | 预期结果 | 实际结果 | 状态 |
|---------|---------|---------|------|
| 2025-12-17全部研报 | 返回75条记录 | ✅ 返回75条记录 | 通过 |
| 2025-12-23全部研报 | 返回55+条记录 | ✅ 返回55条记录 | 通过 |
| AG品种筛选 | 返回AG的研报 | ✅ 返回AG研报汇总 | 通过 |
| 研报汇总API | 返回机构数统计 | ✅ 返回54家机构 | 通过 |

## 数据对比

### 修复前
- 查询日期：2025-12-17
- 返回记录：0条
- 错误提示："研报汇总加载失败"

### 修复后
- 查询日期：2025-12-17
- 返回记录：75条（包含所有有数据的品种）
- 数据内容：每条记录包含品种代码、观点、机构统计等

## 影响范围

### 修复的API端点
1. `/api/v1/zhihui/research-reports` - 研报列表API

### 依赖的页面
1. `report_detail.html` - 研报详情页面（主要影响页面）

### 相关API（之前已修复）
1. `/api/v1/zhihui/research-summary` - 研报汇总API（前一次修复）

## 数据格式说明

### API返回格式

```json
{
    "success": true,
    "date": "2025-12-17",
    "total": 75,
    "data": [
        {
            "report_id": "AG_20251217",
            "comm_code": "AG",
            "variety_name": "沪银",
            "institution_name": "智汇期讯机构汇总",
            "publish_date": "2025-12-17",
            "view_port": "中性",
            "sentiment": "neutral",
            "trade_logic": "看多25家(46.3%)，中性27家(50.0%)，看空2家(3.7%)",
            "related_data": "共54家机构发表观点",
            "risk_factor": "主流观点占比50.0%，请关注市场情绪变化",
            "report_link": ""
        }
        // ... 更多品种
    ]
}
```

## 注意事项

1. **数据性质变化**：
   - 原数据源：单个机构的详细研报
   - 新数据源：多家机构的观点汇总
   - 用途更适合：市场整体情绪分析

2. **report_link字段**：
   - 现在为空字符串
   - 因为数据来源是汇总数据，没有单个研报链接

3. **institution_name字段**：
   - 固定值："智汇期讯机构汇总"
   - 表明这是多家机构的汇总观点

4. **数据完整性**：
   - 覆盖所有在`market_full_view`表中有数据的品种
   - 通常每天有50-57个品种有数据

## 后续建议

### 如需单个机构研报详情

如果将来需要恢复单个机构的详细研报功能，建议：

1. 创建新的定时任务定期爬取研报数据
2. 补充`research_reports`表的历史数据
3. 新建一个独立的API端点`/research-reports/detailed`
4. 保持当前的`/research-reports`端点用于机构观点汇总

### 数据质量改进

1. 定期检查`market_full_view`表数据更新
2. 监控数据覆盖的品种数量
3. 添加数据时效性检查

---

**修复时间**：2025-12-23
**修复版本**：v1.1
**测试状态**：✅ 全部通过
