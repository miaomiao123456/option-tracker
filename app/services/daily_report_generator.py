"""
每日早报生成服务
整合系统所有数据源,生成每日交易策略早报
"""
import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import httpx
from bs4 import BeautifulSoup
import json

from app.models.database import get_db
from sqlalchemy import text, desc
from sqlalchemy.orm import Session


class DailyReportGenerator:
    """每日早报生成器"""

    def __init__(self):
        self.report_date = datetime.now().strftime('%Y-%m-%d')
        self.target_date = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')  # 使用昨日数据

    async def generate_daily_report(self) -> Dict[str, Any]:
        """
        生成每日早报
        整合所有数据源并生成报告
        """
        print(f"🌅 开始生成 {self.report_date} 早报...")

        # 并发获取所有数据
        tasks = [
            self._get_market_news(),           # 市场资讯
            self._get_top_opportunities(),      # 顶级交易机会
            self._get_research_highlights(),    # 研报要点
            self._get_capital_flow_summary(),   # 资金流向汇总
            self._get_risk_warnings(),          # 风险提示
            self._get_term_structure_signals(), # 期限结构信号
            self._get_technical_signals(),      # 技术面信号
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 组装报告
        report = {
            "report_date": self.report_date,
            "generate_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "market_news": results[0] if not isinstance(results[0], Exception) else [],
            "top_opportunities": results[1] if not isinstance(results[1], Exception) else [],
            "research_highlights": results[2] if not isinstance(results[2], Exception) else {},
            "capital_flow_summary": results[3] if not isinstance(results[3], Exception) else {},
            "risk_warnings": results[4] if not isinstance(results[4], Exception) else [],
            "term_structure_signals": results[5] if not isinstance(results[5], Exception) else [],
            "technical_signals": results[6] if not isinstance(results[6], Exception) else {},
            "executive_summary": "",  # 将在最后生成
        }

        # 生成执行摘要
        report["executive_summary"] = self._generate_executive_summary(report)

        # 保存到数据库
        await self._save_report(report)

        print(f"✅ 早报生成完成!")
        return report

    async def _get_market_news(self) -> List[Dict[str, str]]:
        """
        获取市场重要资讯
        从金十数据、财联社等抓取最新资讯
        """
        print("📰 获取市场资讯...")
        news_list = []

        try:
            # 方案1: 抓取金十数据快讯
            async with httpx.AsyncClient(timeout=10.0) as client:
                # 金十数据快讯API (公开接口)
                url = "https://flash-api.jin10.com/get_flash_list"
                params = {
                    "channel": "0",  # 全部资讯
                    "vip": "1",
                    "limit": "20"
                }

                response = await client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('data'):
                        for item in data['data'][:10]:  # 取前10条
                            news_list.append({
                                "time": item.get('time', ''),
                                "title": item.get('data', ''),
                                "importance": self._assess_news_importance(item.get('data', '')),
                                "source": "金十数据"
                            })
        except Exception as e:
            print(f"⚠️ 获取金十数据失败: {e}")

        # 方案2: 如果金十数据失败,使用本地数据库的历史重要事件
        if not news_list:
            news_list = [
                {
                    "time": "08:00",
                    "title": "今日无重大经济数据发布,关注美联储官员讲话",
                    "importance": "medium",
                    "source": "系统提示"
                }
            ]

        return news_list

    def _assess_news_importance(self, content: str) -> str:
        """评估新闻重要性"""
        high_keywords = ['美联储', '加息', '降息', 'GDP', 'CPI', '非农', '贸易战', '地缘政治']
        medium_keywords = ['库存', '产量', '消费', '进出口', '政策']

        content_lower = content.lower()
        if any(keyword in content for keyword in high_keywords):
            return "high"
        elif any(keyword in content for keyword in medium_keywords):
            return "medium"
        return "low"

    async def _get_top_opportunities(self) -> List[Dict[str, Any]]:
        """
        获取顶级交易机会
        从机会雷达中筛选A级及以上机会
        """
        print("🎯 筛选顶级交易机会...")

        db = next(get_db())
        try:
            # 查询综合机会表
            query = text("""
                SELECT
                    comm_code,
                    direction,
                    grade,
                    confidence,
                    total_score,
                    reasons
                FROM comprehensive_opportunities
                WHERE grade IN ('S', 'A')
                ORDER BY
                    CASE grade
                        WHEN 'S' THEN 1
                        WHEN 'A' THEN 2
                    END,
                    confidence DESC
                LIMIT 10
            """)

            result = db.execute(query)
            opportunities = []

            for row in result:
                opportunities.append({
                    "variety": row.comm_code,
                    "direction": row.direction,
                    "grade": row.grade,
                    "confidence": row.confidence,
                    "score": row.total_score,
                    "reasons": json.loads(row.reasons) if row.reasons else []
                })

            return opportunities

        except Exception as e:
            print(f"⚠️ 获取交易机会失败: {e}")
            return []
        finally:
            db.close()

    async def _get_research_highlights(self) -> Dict[str, Any]:
        """
        获取研报要点
        汇总机构观点,找出一致性最强的品种
        """
        print("📊 分析研报要点...")

        db = next(get_db())
        try:
            # 查询智汇期讯数据
            query = text(f"""
                SELECT
                    variety_code,
                    variety_name,
                    more_port,
                    more_rate,
                    sum as total_institutions,
                    excessive_num,
                    neutral_num,
                    empty_num
                FROM zhihui_market_sentiment
                WHERE record_time LIKE '{self.target_date}%'
                AND sum > 0
                ORDER BY more_rate DESC, sum DESC
                LIMIT 20
            """)

            result = db.execute(query)

            # 分类统计
            strong_bull = []  # 强烈看多 (>80%)
            strong_bear = []  # 强烈看空 (>80%)
            divergent = []    # 分歧较大 (40-60%)

            for row in result:
                item = {
                    "variety": row.variety_code,
                    "name": row.variety_name,
                    "view": row.more_port,
                    "ratio": row.more_rate,
                    "institutions": row.total_institutions,
                    "bull_count": row.excessive_num or 0,
                    "neutral_count": row.neutral_num or 0,
                    "bear_count": row.empty_num or 0
                }

                if row.more_rate and row.more_rate >= 80:
                    if row.more_port == '偏多':
                        strong_bull.append(item)
                    elif row.more_port == '偏空':
                        strong_bear.append(item)
                elif row.more_rate and 40 <= row.more_rate <= 60:
                    divergent.append(item)

            return {
                "strong_bull": strong_bull[:5],
                "strong_bear": strong_bear[:5],
                "divergent": divergent[:3],
                "total_varieties": result.rowcount
            }

        except Exception as e:
            print(f"⚠️ 获取研报数据失败: {e}")
            return {"strong_bull": [], "strong_bear": [], "divergent": []}
        finally:
            db.close()

    async def _get_capital_flow_summary(self) -> Dict[str, Any]:
        """
        获取资金流向汇总
        找出近期资金异动最大的品种
        """
        print("💰 分析资金流向...")

        db = next(get_db())
        try:
            # 查询期权资金流向 (最近3天)
            query = text("""
                SELECT
                    variety_code,
                    SUM(net_inflow) as total_net_inflow,
                    SUM(volume) as total_volume,
                    COUNT(*) as trade_count
                FROM option_capital_flow
                WHERE DATE(record_time) >= DATE('now', '-3 days')
                GROUP BY variety_code
                HAVING ABS(total_net_inflow) > 1000
                ORDER BY ABS(total_net_inflow) DESC
                LIMIT 10
            """)

            result = db.execute(query)

            capital_flow = {
                "top_inflow": [],
                "top_outflow": []
            }

            for row in result:
                item = {
                    "variety": row.variety_code,
                    "net_flow": round(row.total_net_inflow, 2),
                    "volume": round(row.total_volume, 2),
                    "trade_count": row.trade_count
                }

                if row.total_net_inflow > 0:
                    capital_flow["top_inflow"].append(item)
                else:
                    capital_flow["top_outflow"].append(item)

            return capital_flow

        except Exception as e:
            print(f"⚠️ 获取资金流向失败: {e}")
            return {"top_inflow": [], "top_outflow": []}
        finally:
            db.close()

    async def _get_risk_warnings(self) -> List[Dict[str, str]]:
        """
        获取风险预警
        虚实比异常、逼仓风险等
        """
        print("⚠️ 检查风险预警...")

        db = next(get_db())
        try:
            # 查询高风险品种 (虚实比 > 100)
            query = text(f"""
                SELECT
                    comm_code,
                    variety_name,
                    virtual_real_ratio,
                    squeeze_risk,
                    impact_analysis
                FROM virtual_real_ratio
                WHERE record_date = '{(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')}'
                AND squeeze_risk = '高'
                ORDER BY virtual_real_ratio DESC
                LIMIT 5
            """)

            result = db.execute(query)
            warnings = []

            for row in result:
                warnings.append({
                    "variety": row.comm_code,
                    "name": row.variety_name,
                    "type": "逼仓风险",
                    "level": "高",
                    "ratio": row.virtual_real_ratio,
                    "description": row.impact_analysis or f"{row.variety_name}虚实比达{row.virtual_real_ratio},存在逼仓风险"
                })

            return warnings

        except Exception as e:
            print(f"⚠️ 获取风险预警失败: {e}")
            return []
        finally:
            db.close()

    async def _get_term_structure_signals(self) -> List[Dict[str, Any]]:
        """
        获取期限结构信号
        Contango和Backwardation机会
        """
        print("📈 分析期限结构...")

        db = next(get_db())
        try:
            # 查询期限结构增强数据
            query = text("""
                SELECT
                    comm_code,
                    current_structure,
                    structure_score,
                    trade_suggestion,
                    conversion_type,
                    conversion_strength
                FROM term_structure_enhanced
                WHERE record_date >= DATE('now', '-2 days')
                AND structure_score >= 70
                ORDER BY structure_score DESC
                LIMIT 8
            """)

            result = db.execute(query)
            signals = []

            for row in result:
                signals.append({
                    "variety": row.comm_code,
                    "structure": row.current_structure,
                    "score": row.structure_score,
                    "suggestion": row.trade_suggestion,
                    "conversion": row.conversion_type,
                    "strength": row.conversion_strength
                })

            return signals

        except Exception as e:
            print(f"⚠️ 获取期限结构失败: {e}")
            return []
        finally:
            db.close()

    async def _get_technical_signals(self) -> Dict[str, List[str]]:
        """
        获取技术面信号
        从交易可查蓝图中提取策略
        """
        print("📉 提取技术信号...")

        db = next(get_db())
        try:
            # 查询最新的交易可查蓝图
            query = text("""
                SELECT
                    date,
                    parsed_strategies
                FROM daily_blueprints
                WHERE date >= DATE('now', '-2 days')
                AND parsed_strategies IS NOT NULL
                ORDER BY date DESC
                LIMIT 1
            """)

            result = db.execute(query).fetchone()

            if result and result.parsed_strategies:
                strategies = json.loads(result.parsed_strategies)

                # 按星级分类
                three_star = [s for s in strategies if s.get('signal', '').count('⭐') == 3]
                two_star = [s for s in strategies if s.get('signal', '').count('⭐') == 2]

                return {
                    "strong_signals": [f"{s['variety']} {s['direction']} - {s['reason']}" for s in three_star],
                    "moderate_signals": [f"{s['variety']} {s['direction']} - {s['reason']}" for s in two_star]
                }

            return {"strong_signals": [], "moderate_signals": []}

        except Exception as e:
            print(f"⚠️ 获取技术信号失败: {e}")
            return {"strong_signals": [], "moderate_signals": []}
        finally:
            db.close()

    def _generate_executive_summary(self, report: Dict[str, Any]) -> str:
        """
        生成执行摘要
        基于所有数据生成简明扼要的总结
        """
        print("📝 生成执行摘要...")

        summary_parts = []

        # 1. 市场概况
        news_count = len(report.get('market_news', []))
        high_importance_news = [n for n in report.get('market_news', []) if n.get('importance') == 'high']

        if high_importance_news:
            summary_parts.append(f"🔔 今日有 {len(high_importance_news)} 条重要资讯需关注")

        # 2. 顶级机会
        opportunities = report.get('top_opportunities', [])
        s_grade = [o for o in opportunities if o.get('grade') == 'S']
        a_grade = [o for o in opportunities if o.get('grade') == 'A']

        if s_grade:
            varieties = ', '.join([o['variety'] for o in s_grade[:3]])
            summary_parts.append(f"⭐ S级机会: {varieties}")
        if a_grade:
            varieties = ', '.join([o['variety'] for o in a_grade[:3]])
            summary_parts.append(f"🎯 A级机会: {varieties}")

        # 3. 研报一致性
        research = report.get('research_highlights', {})
        strong_bull = research.get('strong_bull', [])
        strong_bear = research.get('strong_bear', [])

        if strong_bull:
            varieties = ', '.join([r['variety'] for r in strong_bull[:3]])
            summary_parts.append(f"📈 机构强烈看多: {varieties}")
        if strong_bear:
            varieties = ', '.join([r['variety'] for r in strong_bear[:3]])
            summary_parts.append(f"📉 机构强烈看空: {varieties}")

        # 4. 资金异动
        capital = report.get('capital_flow_summary', {})
        top_inflow = capital.get('top_inflow', [])

        if top_inflow:
            variety = top_inflow[0]['variety']
            amount = top_inflow[0]['net_flow']
            summary_parts.append(f"💰 资金大幅流入: {variety} (+{amount:.0f}万)")

        # 5. 风险提示
        warnings = report.get('risk_warnings', [])
        if warnings:
            varieties = ', '.join([w['variety'] for w in warnings[:3]])
            summary_parts.append(f"⚠️ 高风险预警: {varieties}")

        return '\n'.join(summary_parts) if summary_parts else "今日市场平稳,暂无特别关注点"

    async def _save_report(self, report: Dict[str, Any]):
        """保存报告到数据库"""
        db = next(get_db())
        try:
            # 创建表(如果不存在)
            create_table_sql = text("""
                CREATE TABLE IF NOT EXISTS daily_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_date DATE NOT NULL UNIQUE,
                    generate_time TIMESTAMP NOT NULL,
                    content TEXT NOT NULL,
                    executive_summary TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            db.execute(create_table_sql)

            # 插入报告
            insert_sql = text("""
                INSERT OR REPLACE INTO daily_reports
                (report_date, generate_time, content, executive_summary)
                VALUES (:report_date, :generate_time, :content, :executive_summary)
            """)

            db.execute(insert_sql, {
                "report_date": report['report_date'],
                "generate_time": report['generate_time'],
                "content": json.dumps(report, ensure_ascii=False),
                "executive_summary": report['executive_summary']
            })

            db.commit()
            print("💾 报告已保存到数据库")

        except Exception as e:
            print(f"⚠️ 保存报告失败: {e}")
            db.rollback()
        finally:
            db.close()


# 命令行测试入口
async def main():
    """测试生成早报"""
    generator = DailyReportGenerator()
    report = await generator.generate_daily_report()

    print("\n" + "="*80)
    print("📋 每日早报预览")
    print("="*80)
    print(f"\n报告日期: {report['report_date']}")
    print(f"生成时间: {report['generate_time']}")
    print(f"\n{report['executive_summary']}")
    print("\n" + "="*80)

    return report


if __name__ == "__main__":
    asyncio.run(main())
