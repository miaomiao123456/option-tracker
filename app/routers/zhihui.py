"""
智汇期讯API路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from app.models.database import get_db
from app.models.models import ResearchReport, MarketFullView
from datetime import date, datetime, timedelta
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/full-view")
async def get_full_view(
    query_date: Optional[str] = Query(None, description="查询日期 YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    """
    获取智汇期讯多空全景数据
    优先从数据库获取,没有则实时爬取并保存
    """
    from app.crawlers.zhihui_spider import ZhihuiQixunSpider

    try:
        # 解析日期
        if query_date:
            target_date = datetime.strptime(query_date, '%Y-%m-%d').date()
        else:
            target_date = date.today()

        # 先从数据库查询
        records = db.query(MarketFullView).filter(
            MarketFullView.record_date == target_date
        ).all()

        # 如果数据库没有数据,从API获取并保存
        if not records:
            logger.info(f"数据库中没有{target_date}的多空全景数据,开始爬取...")
            spider = ZhihuiQixunSpider()
            full_view_data = spider.fetch_full_view(publish_date=target_date)

            # 保存到数据库
            for item in full_view_data:
                record = MarketFullView(
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
                db.add(record)

            db.commit()
            logger.info(f"成功保存{len(full_view_data)}条多空全景数据到数据库")

            # 重新查询
            records = db.query(MarketFullView).filter(
                MarketFullView.record_date == target_date
            ).all()

        # 转换为字典
        full_view_data = [
            {
                "variety_code": r.comm_code,
                "variety_name": r.variety_name,
                "excessive_num": r.excessive_num,
                "excessive_ratio": r.excessive_ratio,
                "neutral_num": r.neutral_num,
                "neutral_ratio": r.neutral_ratio,
                "empty_num": r.empty_num,
                "empty_ratio": r.empty_ratio,
                "sum": r.total_num,
                "more_port": r.more_port,
                "more_rate": r.more_rate,
                "main_sentiment": r.main_sentiment
            }
            for r in records
        ]

        return {
            "success": True,
            "date": target_date.strftime('%Y-%m-%d'),
            "data": full_view_data,
            "total": len(full_view_data)
        }

    except Exception as e:
        logger.error(f"获取多空全景数据失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/research-reports")
async def get_research_reports(
    query_date: Optional[str] = Query(None, description="查询日期 YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    """
    获取智汇期讯研报淘金数据
    从数据库获取,如果没有则实时爬取
    """
    try:
        # 解析日期
        if query_date:
            target_date = datetime.strptime(query_date, '%Y-%m-%d').date()
        else:
            target_date = date.today()

        # 先从数据库查询
        reports = db.query(ResearchReport).filter(
            ResearchReport.publish_date == target_date
        ).all()

        # 如果数据库没有数据,从API获取
        if not reports:
            logger.info(f"数据库中没有{target_date}的研报数据,开始爬取...")
            from app.crawlers.zhihui_spider import ZhihuiQixunSpider

            spider = ZhihuiQixunSpider()
            # 获取当天的所有研报 (可能有很多页,这里先获取100条)
            reports_data = spider.fetch_research_reports(
                start_date=target_date,
                end_date=target_date,
                limit=100
            )

            # 保存到数据库
            for report_dict in reports_data['reports']:
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

            db.commit()
            logger.info(f"成功保存{len(reports_data['reports'])}条研报到数据库")

            # 重新查询
            reports = db.query(ResearchReport).filter(
                ResearchReport.publish_date == target_date
            ).all()

        # 转换为字典
        reports_list = [
            {
                "report_id": r.report_id,
                "comm_code": r.comm_code,
                "variety_name": r.variety_name,
                "institution_name": r.institution_name,
                "publish_date": r.publish_date.strftime('%Y-%m-%d'),
                "view_port": r.view_port,
                "sentiment": r.sentiment,
                "trade_logic": r.trade_logic or "",
                "related_data": r.related_data or "",
                "risk_factor": r.risk_factor or "",
                "report_link": r.report_link
            }
            for r in reports
        ]

        return {
            "success": True,
            "date": target_date.strftime('%Y-%m-%d'),
            "data": reports_list,
            "total": len(reports_list)
        }

    except Exception as e:
        logger.error(f"获取研报数据失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/research-summary")
async def get_research_summary(
    comm_code: str = Query(..., description="品种代码,如RB"),
    query_date: Optional[str] = Query(None, description="查询日期 YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    """
    获取某个品种的研报汇总
    使用AI汇总交易逻辑、相关数据、风险因素
    """
    try:
        # 解析日期
        if query_date:
            target_date = datetime.strptime(query_date, '%Y-%m-%d').date()
        else:
            target_date = date.today()

        # 查询该品种在指定日期的所有研报
        reports = db.query(ResearchReport).filter(
            and_(
                ResearchReport.comm_code == comm_code.upper(),
                ResearchReport.publish_date == target_date
            )
        ).all()

        if not reports:
            return {
                "success": True,
                "comm_code": comm_code.upper(),
                "date": target_date.strftime('%Y-%m-%d'),
                "reports_count": 0,
                "summary": {
                    "trade_logic": "暂无研报数据",
                    "related_data": "暂无研报数据",
                    "risk_factor": "暂无研报数据"
                }
            }

        # 收集所有研报的内容
        trade_logics = [r.trade_logic for r in reports if r.trade_logic]
        related_datas = [r.related_data for r in reports if r.related_data]
        risk_factors = [r.risk_factor for r in reports if r.risk_factor]

        # 使用AI汇总(如果内容较多)
        if len(trade_logics) > 1:
            # 调用AI汇总服务
            from app.services.analysis import summarize_research_reports

            summary = summarize_research_reports(
                trade_logics=trade_logics,
                related_datas=related_datas,
                risk_factors=risk_factors,
                variety_name=reports[0].variety_name
            )
        else:
            # 单个研报直接返回
            summary = {
                "trade_logic": trade_logics[0] if trade_logics else "暂无数据",
                "related_data": related_datas[0] if related_datas else "暂无数据",
                "risk_factor": risk_factors[0] if risk_factors else "暂无数据"
            }

        # 返回详细研报列表
        reports_list = [
            {
                "institution_name": r.institution_name,
                "view_port": r.view_port,
                "sentiment": r.sentiment
            }
            for r in reports
        ]

        return {
            "success": True,
            "comm_code": comm_code.upper(),
            "variety_name": reports[0].variety_name if reports else "",
            "date": target_date.strftime('%Y-%m-%d'),
            "reports_count": len(reports),
            "reports": reports_list,
            "summary": summary
        }

    except Exception as e:
        logger.error(f"获取研报汇总失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
