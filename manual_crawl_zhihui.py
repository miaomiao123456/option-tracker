"""
手动执行智汇期讯研报爬虫 - 获取今日全量数据
"""
import sys
import logging
from pathlib import Path
from datetime import date, datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from app.crawlers.zhihui_spider import ZhihuiQixunSpider
from app.models.database import SessionLocal
from app.models.models import MarketFullView, ResearchReport

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """手动执行爬虫"""
    logger.info("=" * 60)
    logger.info("手动执行智汇期讯研报全量爬虫")
    logger.info("=" * 60)

    spider = ZhihuiQixunSpider()

    try:
        # 1. 获取多空全景数据
        logger.info("\n步骤 1: 获取多空全景数据...")
        full_view = spider.fetch_full_view()

        if full_view:
            logger.info(f"✅ 成功获取多空全景数据 {len(full_view)} 条")

            db = SessionLocal()
            try:
                today = date.today()
                saved_count = 0
                updated_count = 0

                for item in full_view:
                    existing = db.query(MarketFullView).filter(
                        MarketFullView.comm_code == item['variety_code'],
                        MarketFullView.record_date == today
                    ).first()

                    if existing:
                        # 更新现有记录
                        existing.excessive_num = item['excessive_num']
                        existing.excessive_ratio = item['excessive_ratio']
                        existing.neutral_num = item['neutral_num']
                        existing.neutral_ratio = item['neutral_ratio']
                        existing.empty_num = item['empty_num']
                        existing.empty_ratio = item['empty_ratio']
                        existing.total_num = item['sum']
                        existing.more_port = item['more_port']
                        existing.more_rate = item['more_rate']
                        existing.main_sentiment = item['main_sentiment']
                        updated_count += 1
                    else:
                        # 创建新记录
                        record = MarketFullView(
                            comm_code=item['variety_code'],
                            variety_name=item['variety_name'],
                            record_date=today,
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
                        db.add(record)
                        saved_count += 1

                db.commit()
                logger.info(f"✅ 多空全景数据已保存: 新增{saved_count}条, 更新{updated_count}条")
            finally:
                db.close()

        # 2. 获取研报淘金数据 - 分批获取以确保获取全部数据
        logger.info("\n步骤 2: 获取研报淘金数据（全量）...")

        total_reports = []
        page = 1
        page_size = 100

        while True:
            logger.info(f"正在获取第 {page} 页...")
            reports_data = spider.fetch_research_reports(
                variety_code=None,
                start_date=date.today(),
                end_date=date.today(),
                page=page,
                limit=page_size
            )

            if not reports_data or not reports_data.get('reports'):
                logger.info("没有更多数据")
                break

            page_reports = reports_data['reports']
            total_reports.extend(page_reports)

            logger.info(f"第 {page} 页获取到 {len(page_reports)} 条研报")

            # 如果本页数据少于page_size，说明已经是最后一页
            if len(page_reports) < page_size:
                logger.info("已到最后一页")
                break

            page += 1

            # 安全限制，最多获取10页
            if page > 10:
                logger.warning("已达到最大页数限制(10页)")
                break

        logger.info(f"\n✅ 共获取到 {len(total_reports)} 份研报")

        # 统计机构分布
        institutions = {}
        for r in total_reports:
            inst = r.get('institution_name', '未知')
            institutions[inst] = institutions.get(inst, 0) + 1

        logger.info("\n机构统计:")
        for inst, count in sorted(institutions.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {inst}: {count}份")

        # 保存到数据库
        if total_reports:
            db = SessionLocal()
            try:
                saved_count = 0
                skipped_count = 0

                for report_dict in total_reports:
                    # 检查是否已存在
                    existing = db.query(ResearchReport).filter(
                        ResearchReport.report_id == report_dict['report_id']
                    ).first()

                    if not existing:
                        report = ResearchReport(
                            report_id=report_dict['report_id'],
                            comm_code=report_dict['variety_code'],
                            variety_name=report_dict['variety'],
                            institution_id=report_dict['institution_id'],
                            institution_name=report_dict['institution_name'],
                            publish_date=datetime.strptime(report_dict['publish_date'], '%Y-%m-%d').date(),
                            view_port=report_dict['view_port'],
                            sentiment=report_dict['sentiment'],
                            trade_logic=report_dict['trade_logic'],
                            related_data=report_dict['related_data'],
                            risk_factor=report_dict['risk_factor'],
                            report_link=report_dict['link']
                        )
                        db.add(report)
                        saved_count += 1
                    else:
                        skipped_count += 1

                db.commit()
                logger.info(f"\n✅ 研报数据已保存到数据库: 新增{saved_count}条, 已存在{skipped_count}条")
            finally:
                db.close()

        logger.info("\n" + "=" * 60)
        logger.info("✅ 全量爬虫执行完成！")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"\n❌ 爬虫执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
