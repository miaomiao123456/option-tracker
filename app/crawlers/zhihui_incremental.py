"""
智汇期讯增量爬虫 - 每日爬取所有品种研报
功能：
1. 每日自动爬取所有品种的最新研报
2. 提取：交易逻辑、相关数据、风险因素、原文链接
3. 保存到数据库
4. 使用AI对数据进行总结
"""
import logging
from datetime import date, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.crawlers.zhihui_spider import ZhihuiQixunSpider
from app.models.models import ResearchReport, MarketFullView
from app.models.database import SessionLocal

logger = logging.getLogger(__name__)


class ZhihuiIncrementalCrawler:
    """智汇期讯增量爬虫"""

    def __init__(self):
        self.spider = ZhihuiQixunSpider()

    def crawl_daily_reports(
        self,
        target_date: Optional[date] = None,
        save_to_db: bool = True
    ) -> Dict:
        """
        爬取指定日期所有品种的研报（增量）

        Args:
            target_date: 目标日期，默认今天
            save_to_db: 是否保存到数据库

        Returns:
            {
                "total_fetched": 100,
                "total_saved": 95,
                "total_duplicates": 5,
                "varieties": ["AU", "RB", "CU", ...],
                "reports_by_variety": {
                    "AU": 10,
                    "RB": 15,
                    ...
                }
            }
        """
        if target_date is None:
            target_date = date.today()

        logger.info(f"开始爬取 {target_date} 的研报数据...")

        # 1. 获取品种列表
        varieties = self.spider.fetch_variety_list()
        if not varieties:
            logger.error("无法获取品种列表")
            return {"error": "无法获取品种列表"}

        logger.info(f"获取到 {len(varieties)} 个品种")

        # 2. 逐个品种爬取研报（因为不指定品种会权限不足）
        all_reports = []

        for variety in varieties:
            variety_code = variety['variety_code']
            logger.info(f"正在爬取品种 {variety_code} ({variety['variety_name']}) 的研报...")

            page = 1
            limit = 100

            while True:
                result = self.spider.fetch_research_reports(
                    variety_code=variety_code,
                    start_date=target_date,
                    end_date=target_date,
                    view_port="全部",
                    page=page,
                    limit=limit
                )

                reports = result.get('reports', [])
                total = result.get('total', 0)

                if not reports:
                    break

                all_reports.extend(reports)
                logger.info(f"  第 {page} 页: 获取 {len(reports)} 条研报（品种总共 {total} 条）")

                # 如果已获取全部，停止
                if len(all_reports) >= total or len(reports) < limit:
                    break

                page += 1

        logger.info(f"✅ 共爬取 {len(all_reports)} 条研报")

        # 3. 统计
        stats = {
            "total_fetched": len(all_reports),
            "total_saved": 0,
            "total_duplicates": 0,
            "varieties": list(set([r['variety_code'] for r in all_reports if r['variety_code']])),
            "reports_by_variety": {}
        }

        # 统计每个品种的研报数
        for report in all_reports:
            variety = report['variety_code']
            if variety:
                stats['reports_by_variety'][variety] = stats['reports_by_variety'].get(variety, 0) + 1

        # 4. 保存到数据库
        if save_to_db:
            saved, duplicates = self._save_reports_to_db(all_reports, target_date)
            stats['total_saved'] = saved
            stats['total_duplicates'] = duplicates

        return stats

    def _save_reports_to_db(self, reports: List[Dict], target_date: date) -> tuple:
        """
        保存研报到数据库

        Returns:
            (saved_count, duplicate_count)
        """
        db = SessionLocal()
        saved_count = 0
        duplicate_count = 0

        try:
            for report in reports:
                # 检查是否已存在（根据 report_id 和 publish_date）
                exists = db.query(ResearchReport).filter(
                    and_(
                        ResearchReport.report_id == report['report_id'],
                        ResearchReport.publish_date == report['publish_date']
                    )
                ).first()

                if exists:
                    duplicate_count += 1
                    logger.debug(f"跳过重复研报: {report['report_id']}")
                    continue

                # 创建新记录
                # 将字符串日期转换为date对象
                from datetime import datetime
                publish_date_obj = datetime.strptime(report['publish_date'], '%Y-%m-%d').date() if isinstance(report['publish_date'], str) else report['publish_date']

                db_report = ResearchReport(
                    report_id=report['report_id'],
                    comm_code=report['variety_code'],
                    variety_name=report['variety'],
                    institution_id=report.get('institution_id'),
                    institution_name=report['institution_name'],
                    publish_date=publish_date_obj,
                    view_port=report['view_port'],
                    sentiment=report['sentiment'],
                    trade_logic=report['trade_logic'],
                    related_data=report['related_data'],
                    risk_factor=report['risk_factor'],
                    report_link=report['link']
                )

                db.add(db_report)
                saved_count += 1

            db.commit()
            logger.info(f"✅ 保存 {saved_count} 条研报到数据库（跳过 {duplicate_count} 条重复）")

        except Exception as e:
            logger.error(f"保存研报到数据库失败: {e}")
            db.rollback()
            raise
        finally:
            db.close()

        return saved_count, duplicate_count

    def crawl_market_overview(self, target_date: Optional[date] = None) -> Dict:
        """
        爬取多空全景数据

        Args:
            target_date: 目标日期，默认今天

        Returns:
            {
                "total_saved": 50,
                "varieties": ["AU", "RB", ...]
            }
        """
        if target_date is None:
            target_date = date.today()

        logger.info(f"开始爬取 {target_date} 的多空全景数据...")

        # 1. 爬取数据
        full_view_data = self.spider.fetch_full_view(target_date)

        if not full_view_data:
            logger.error("无法获取多空全景数据")
            return {"error": "无法获取多空全景数据"}

        logger.info(f"获取到 {len(full_view_data)} 个品种的多空全景数据")

        # 2. 保存到数据库
        db = SessionLocal()
        saved_count = 0

        try:
            for item in full_view_data:
                # 检查是否已存在
                exists = db.query(MarketFullView).filter(
                    and_(
                        MarketFullView.comm_code == item['variety_code'],
                        MarketFullView.record_date == target_date
                    )
                ).first()

                if exists:
                    # 更新
                    exists.excessive_num = item['excessive_num']
                    exists.excessive_ratio = item['excessive_ratio']
                    exists.neutral_num = item['neutral_num']
                    exists.neutral_ratio = item['neutral_ratio']
                    exists.empty_num = item['empty_num']
                    exists.empty_ratio = item['empty_ratio']
                    exists.total_num = item['sum']
                    exists.more_port = item['more_port']
                    exists.more_rate = item['more_rate']
                    exists.main_sentiment = item['main_sentiment']
                else:
                    # 新建
                    db_item = MarketFullView(
                        comm_code=item['variety_code'],
                        variety_name=item['variety_name'],
                        record_date=target_date,
                        excessive_num=item['excessive_num'],
                        excessive_ratio=item['excessive_ratio'],
                        neutral_num=item['neutral_num'],
                        neutral_ratio=item['neutral_ratio'],
                        empty_num=item['empty_num'],
                        empty_ratio=item['empty_ratio'],
                        total_num=item['sum'],
                        more_port=item['more_port'],
                        more_rate=item['more_rate'],
                        main_sentiment=item['main_sentiment']
                    )
                    db.add(db_item)

                saved_count += 1

            db.commit()
            logger.info(f"✅ 保存/更新 {saved_count} 条多空全景数据")

        except Exception as e:
            logger.error(f"保存多空全景数据失败: {e}")
            db.rollback()
            raise
        finally:
            db.close()

        return {
            "total_saved": saved_count,
            "varieties": [item['variety_code'] for item in full_view_data]
        }

    def get_daily_summary(
        self,
        target_date: Optional[date] = None,
        variety_code: Optional[str] = None
    ) -> Dict:
        """
        获取指定日期的研报总结

        Args:
            target_date: 目标日期
            variety_code: 品种代码，为空则获取全部

        Returns:
            {
                "date": "2025-12-25",
                "variety_code": "AU",
                "total_reports": 10,
                "bull_count": 6,
                "bear_count": 2,
                "neutral_count": 2,
                "main_institutions": ["永安期货", "中信期货"],
                "key_logics": [...],
                "key_risks": [...]
            }
        """
        if target_date is None:
            target_date = date.today()

        db = SessionLocal()

        try:
            # 查询
            query = db.query(ResearchReport).filter(
                ResearchReport.publish_date == target_date
            )

            if variety_code:
                query = query.filter(ResearchReport.comm_code == variety_code)

            reports = query.all()

            if not reports:
                return {
                    "date": target_date.isoformat(),
                    "variety_code": variety_code,
                    "total_reports": 0,
                    "message": "暂无研报数据"
                }

            # 统计
            bull_count = sum(1 for r in reports if r.sentiment == 'bull')
            bear_count = sum(1 for r in reports if r.sentiment == 'bear')
            neutral_count = sum(1 for r in reports if r.sentiment == 'neutral')

            # 主要机构
            institutions = {}
            for r in reports:
                if r.institution_name:
                    institutions[r.institution_name] = institutions.get(r.institution_name, 0) + 1

            main_institutions = sorted(institutions.items(), key=lambda x: x[1], reverse=True)[:5]

            # 关键交易逻辑
            key_logics = [r.trade_logic for r in reports if r.trade_logic and r.trade_logic.strip()][:10]

            # 关键风险因素
            key_risks = [r.risk_factor for r in reports if r.risk_factor and r.risk_factor.strip()][:10]

            return {
                "date": target_date.isoformat(),
                "variety_code": variety_code or "全部",
                "total_reports": len(reports),
                "bull_count": bull_count,
                "bear_count": bear_count,
                "neutral_count": neutral_count,
                "main_institutions": [inst[0] for inst in main_institutions],
                "key_logics": key_logics,
                "key_risks": key_risks,
                "reports": [
                    {
                        "institution": r.institution_name,
                        "view": r.view_port,
                        "logic": r.trade_logic,
                        "data": r.related_data,
                        "risk": r.risk_factor,
                        "link": r.report_link
                    }
                    for r in reports
                ]
            }

        finally:
            db.close()


async def test_incremental_crawler():
    """测试增量爬虫"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    crawler = ZhihuiIncrementalCrawler()

    # 1. 测试爬取今日研报
    logger.info("=" * 60)
    logger.info("测试：爬取今日所有品种研报")
    logger.info("=" * 60)

    stats = crawler.crawl_daily_reports(
        target_date=date.today(),
        save_to_db=True
    )

    logger.info(f"\n爬取统计:")
    logger.info(f"  - 总共爬取: {stats['total_fetched']} 条")
    logger.info(f"  - 保存到库: {stats['total_saved']} 条")
    logger.info(f"  - 重复跳过: {stats['total_duplicates']} 条")
    logger.info(f"  - 涉及品种: {len(stats['varieties'])} 个")
    logger.info(f"  - 品种列表: {', '.join(sorted(stats['varieties']))}")

    # 2. 测试爬取多空全景
    logger.info("\n" + "=" * 60)
    logger.info("测试：爬取今日多空全景数据")
    logger.info("=" * 60)

    overview_stats = crawler.crawl_market_overview(target_date=date.today())
    logger.info(f"\n多空全景统计:")
    logger.info(f"  - 保存品种: {overview_stats['total_saved']} 个")

    # 3. 测试获取总结
    logger.info("\n" + "=" * 60)
    logger.info("测试：获取今日研报总结（黄金 AU）")
    logger.info("=" * 60)

    summary = crawler.get_daily_summary(
        target_date=date.today(),
        variety_code="AU"
    )

    logger.info(f"\n黄金研报总结:")
    logger.info(f"  - 研报总数: {summary['total_reports']} 篇")
    logger.info(f"  - 看多: {summary.get('bull_count', 0)} | 看空: {summary.get('bear_count', 0)} | 中性: {summary.get('neutral_count', 0)}")
    if summary.get('main_institutions'):
        logger.info(f"  - 主要机构: {', '.join(summary['main_institutions'])}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_incremental_crawler())
