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


@router.get("/latest-date")
async def get_latest_trading_date(db: Session = Depends(get_db)):
    """
    获取数据库中最新的交易日期
    用于前端日期选择器默认值
    """
    try:
        # 从ResearchReport表查询最新日期(实际有数据的日期)
        latest_record = db.query(ResearchReport.publish_date).order_by(
            desc(ResearchReport.publish_date)
        ).first()

        if latest_record:
            return {
                "success": True,
                "latest_date": latest_record[0].strftime('%Y-%m-%d')
            }
        else:
            # 如果没有数据,返回当前日期
            return {
                "success": True,
                "latest_date": date.today().strftime('%Y-%m-%d')
            }
    except Exception as e:
        logger.error(f"获取最新交易日期失败: {e}")
        return {
            "success": False,
            "latest_date": date.today().strftime('%Y-%m-%d')
        }


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
    comm_code: Optional[str] = Query(None, description="品种代码筛选,如RB"),
    db: Session = Depends(get_db)
):
    """
    获取智汇期讯研报淘金数据
    改为从market_full_view表查询机构观点汇总数据
    """
    try:
        # 解析日期
        if query_date:
            target_date = datetime.strptime(query_date, '%Y-%m-%d').date()
        else:
            target_date = date.today()

        # 从market_full_view表查询
        query = db.query(MarketFullView).filter(
            MarketFullView.record_date == target_date
        )

        # 如果指定了品种代码,则筛选
        if comm_code:
            query = query.filter(MarketFullView.comm_code == comm_code.upper())

        market_data_list = query.all()

        # 转换为研报格式的字典
        reports_list = [
            {
                "report_id": f"{data.comm_code}_{target_date.strftime('%Y%m%d')}",
                "comm_code": data.comm_code,
                "variety_name": data.variety_name,
                "institution_name": "智汇期讯机构汇总",
                "publish_date": target_date.strftime('%Y-%m-%d'),
                "view_port": data.more_port,
                "sentiment": data.main_sentiment,
                "trade_logic": f"看多{data.excessive_num}家({data.excessive_ratio:.1f}%)，中性{data.neutral_num}家({data.neutral_ratio:.1f}%)，看空{data.empty_num}家({data.empty_ratio:.1f}%)" if data.excessive_num is not None else "",
                "related_data": f"共{data.total_num}家机构发表观点" if data.total_num else "",
                "risk_factor": f"主流观点占比{data.more_rate:.1f}%，请关注市场情绪变化" if data.more_rate is not None else "",
                "report_link": ""
            }
            for data in market_data_list
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
    从MarketFullView表查询智汇期讯多空全景数据
    """
    try:
        # 解析日期
        if query_date:
            target_date = datetime.strptime(query_date, '%Y-%m-%d').date()
        else:
            target_date = date.today()

        # 从MarketFullView表查询该品种的数据
        market_data = db.query(MarketFullView).filter(
            and_(
                MarketFullView.comm_code == comm_code.upper(),
                MarketFullView.record_date == target_date
            )
        ).first()

        if not market_data:
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

        # 构建研报汇总
        summary = {
            "trade_logic": f"市场主流观点为{market_data.more_port}，占比{market_data.more_rate:.1f}%。"
                          f"看多机构{market_data.excessive_num}家({market_data.excessive_ratio:.1f}%)，"
                          f"中性{market_data.neutral_num}家({market_data.neutral_ratio:.1f}%)，"
                          f"看空{market_data.empty_num}家({market_data.empty_ratio:.1f}%)。",
            "related_data": f"共有{market_data.total_num}家机构发表观点，"
                           f"市场情绪倾向{market_data.main_sentiment}。",
            "risk_factor": "基于机构观点统计，建议关注市场情绪变化和基本面数据。"
        }

        return {
            "success": True,
            "comm_code": comm_code.upper(),
            "variety_name": market_data.variety_name,
            "date": target_date.strftime('%Y-%m-%d'),
            "reports_count": market_data.total_num,
            "summary": summary
        }

    except Exception as e:
        logger.error(f"获取研报汇总失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/enhanced-analysis/{comm_code}")
async def get_research_enhanced_analysis(
    comm_code: str,
    query_date: Optional[str] = Query(None, description="查询日期 YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    """
    获取研报增强分析 (Phase 2新增)
    包含: 一致性指标、变化信号、Bull-Bear指数
    """
    from app.services.research_enhancement_service import ResearchEnhancementService

    try:
        # 解析日期
        if query_date:
            target_date = datetime.strptime(query_date, '%Y-%m-%d').date()
        else:
            # 获取最新日期
            latest_record = db.query(MarketFullView.record_date).order_by(
                desc(MarketFullView.record_date)
            ).first()
            target_date = latest_record[0] if latest_record else date.today()

        # 创建增强服务
        service = ResearchEnhancementService(db)

        # 计算所有增强指标
        result = service.calculate_all_enhancements(comm_code.upper(), target_date)

        return {
            "success": True,
            **result
        }

    except Exception as e:
        logger.error(f"获取研报增强分析失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sentiment-score/{comm_code}")
async def get_research_sentiment_score(
    comm_code: str,
    query_date: Optional[str] = Query(None, description="查询日期 YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    """
    获取研报情绪得分 (用于多维度综合分析)
    返回: -5 到 +5 的得分和理由
    """
    from app.services.research_enhancement_service import ResearchEnhancementService

    try:
        # 解析日期
        if query_date:
            target_date = datetime.strptime(query_date, '%Y-%m-%d').date()
        else:
            latest_record = db.query(MarketFullView.record_date).order_by(
                desc(MarketFullView.record_date)
            ).first()
            target_date = latest_record[0] if latest_record else date.today()

        # 创建增强服务
        service = ResearchEnhancementService(db)

        # 获取评分
        score, reasons = service.get_research_score_for_综合分析(comm_code.upper(), target_date)

        return {
            "success": True,
            "comm_code": comm_code.upper(),
            "analysis_date": target_date.isoformat(),
            "score": score,
            "reasons": reasons
        }

    except Exception as e:
        logger.error(f"获取研报情绪得分失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
