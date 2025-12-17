"""
多维度综合分析API - Phase 5
提供品种综合分析和机会雷达总览
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import date, datetime
from typing import Optional, List
import logging

from app.models.database import get_db
from app.models.models import TermStructureHistory, MarketFullView
from app.services.comprehensive_analyzer import ComprehensiveAnalyzer

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/analysis/{comm_code}")
async def get_comprehensive_analysis(
    comm_code: str,
    query_date: Optional[str] = Query(None, description="查询日期 YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    """
    获取品种的多维度综合分析 (Phase 5核心功能)

    整合三个维度:
    - 期限结构 (42.8%)
    - 研报基本面 (35.7%)
    - 虚实比 (21.4%)

    返回综合得分、方向判断、等级、理由和风险提示
    """
    try:
        comm_code = comm_code.upper()

        # 解析日期
        if query_date:
            target_date = datetime.strptime(query_date, '%Y-%m-%d').date()
        else:
            # 获取最新日期
            latest_record = db.query(TermStructureHistory.record_date).order_by(
                desc(TermStructureHistory.record_date)
            ).first()
            target_date = latest_record[0] if latest_record else date.today()

        # 创建综合分析器
        analyzer = ComprehensiveAnalyzer(db)

        # 执行分析
        result = analyzer.analyze(comm_code, target_date)

        return {
            "success": True,
            **result
        }

    except Exception as e:
        logger.error(f"综合分析失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/opportunities")
async def get_opportunity_radar(
    min_grade: str = Query("B", description="最低等级: S/A/B"),
    db: Session = Depends(get_db)
):
    """
    机会雷达总览 (Phase 5.4)

    扫描所有品种,识别S/A/B级交易机会

    参数:
    - min_grade: 最低等级(S/A/B),默认B级以上
    """
    try:
        # 获取最新日期
        latest_record = db.query(TermStructureHistory.record_date).order_by(
            desc(TermStructureHistory.record_date)
        ).first()

        if not latest_record:
            return {
                "success": False,
                "message": "无可用数据"
            }

        target_date = latest_record[0]

        # 获取所有有数据的品种
        varieties = db.query(TermStructureHistory.comm_code, TermStructureHistory.variety_name).filter(
            TermStructureHistory.record_date == target_date
        ).distinct().all()

        logger.info(f"开始扫描 {len(varieties)} 个品种...")

        # 创建分析器
        analyzer = ComprehensiveAnalyzer(db)

        # 分析所有品种
        opportunities = {
            "S": [],  # S级机会
            "A": [],  # A级机会
            "B": []   # B级机会
        }

        for comm_code, variety_name in varieties:
            try:
                result = analyzer.analyze(comm_code, target_date)

                grade = result["grade"]
                if grade in ["S", "A", "B"]:
                    opportunities[grade].append({
                        "comm_code": comm_code,
                        "variety_name": variety_name,
                        "total_score": result["total_score"],
                        "direction": result["direction"],
                        "strength": result["strength"],
                        "confidence": result["confidence"],
                        "reasons": result["reasons"][:3],  # 只取前3条理由
                        "grade": grade
                    })

            except Exception as e:
                logger.warning(f"分析 {comm_code} 失败: {e}")
                continue

        # 按得分排序
        for grade in ["S", "A", "B"]:
            opportunities[grade].sort(
                key=lambda x: abs(x["total_score"]),
                reverse=True
            )

        # 根据min_grade过滤
        grade_order = {"S": 0, "A": 1, "B": 2}
        min_grade_level = grade_order.get(min_grade, 2)

        filtered_opportunities = []
        for grade in ["S", "A", "B"]:
            if grade_order[grade] <= min_grade_level:
                filtered_opportunities.extend(opportunities[grade])

        # 统计
        stats = {
            "total_scanned": len(varieties),
            "total_opportunities": len(filtered_opportunities),
            "s_count": len(opportunities["S"]),
            "a_count": len(opportunities["A"]),
            "b_count": len(opportunities["B"]),
            "bull_count": sum(1 for o in filtered_opportunities if o["direction"] == "多头"),
            "bear_count": sum(1 for o in filtered_opportunities if o["direction"] == "空头")
        }

        return {
            "success": True,
            "analysis_date": target_date.isoformat(),
            "min_grade": min_grade,
            "stats": stats,
            "opportunities": filtered_opportunities
        }

    except Exception as e:
        logger.error(f"机会雷达扫描失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/opportunities/top")
async def get_top_opportunities(
    limit: int = Query(10, description="返回数量"),
    direction: Optional[str] = Query(None, description="方向筛选: 多头/空头"),
    db: Session = Depends(get_db)
):
    """
    获取Top N交易机会

    按综合得分排序,返回最强的N个机会
    """
    try:
        # 获取最新日期
        latest_record = db.query(TermStructureHistory.record_date).order_by(
            desc(TermStructureHistory.record_date)
        ).first()

        if not latest_record:
            return {
                "success": False,
                "message": "无可用数据"
            }

        target_date = latest_record[0]

        # 获取所有品种
        varieties = db.query(TermStructureHistory.comm_code, TermStructureHistory.variety_name).filter(
            TermStructureHistory.record_date == target_date
        ).distinct().all()

        # 创建分析器
        analyzer = ComprehensiveAnalyzer(db)

        # 分析所有品种
        all_opportunities = []

        for comm_code, variety_name in varieties:
            try:
                result = analyzer.analyze(comm_code, target_date)

                # 方向筛选
                if direction and result["direction"] != direction:
                    continue

                all_opportunities.append({
                    "comm_code": comm_code,
                    "variety_name": variety_name,
                    "total_score": result["total_score"],
                    "direction": result["direction"],
                    "strength": result["strength"],
                    "grade": result["grade"],
                    "confidence": result["confidence"],
                    "reasons": result["reasons"][:3]
                })

            except Exception as e:
                logger.warning(f"分析 {comm_code} 失败: {e}")
                continue

        # 按得分绝对值排序
        all_opportunities.sort(
            key=lambda x: abs(x["total_score"]),
            reverse=True
        )

        # 取Top N
        top_opportunities = all_opportunities[:limit]

        return {
            "success": True,
            "analysis_date": target_date.isoformat(),
            "direction_filter": direction,
            "total_analyzed": len(varieties),
            "total_matched": len(all_opportunities),
            "limit": limit,
            "opportunities": top_opportunities
        }

    except Exception as e:
        logger.error(f"获取Top机会失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_market_stats(db: Session = Depends(get_db)):
    """
    获取市场统计数据

    统计各等级机会数量、多空分布等
    """
    try:
        # 获取最新日期
        latest_record = db.query(TermStructureHistory.record_date).order_by(
            desc(TermStructureHistory.record_date)
        ).first()

        if not latest_record:
            return {
                "success": False,
                "message": "无可用数据"
            }

        target_date = latest_record[0]

        # 获取所有品种
        varieties = db.query(TermStructureHistory.comm_code, TermStructureHistory.variety_name).filter(
            TermStructureHistory.record_date == target_date
        ).distinct().all()

        # 创建分析器
        analyzer = ComprehensiveAnalyzer(db)

        # 统计
        stats = {
            "total_varieties": len(varieties),
            "grade_distribution": {"S": 0, "A": 0, "B": 0, "C": 0},
            "direction_distribution": {"多头": 0, "空头": 0, "中性": 0},
            "avg_score": 0,
            "avg_confidence": 0
        }

        scores = []
        confidences = []

        for comm_code, _ in varieties:
            try:
                result = analyzer.analyze(comm_code, target_date)

                stats["grade_distribution"][result["grade"]] += 1
                stats["direction_distribution"][result["direction"]] += 1
                scores.append(result["total_score"])
                confidences.append(result["confidence"])

            except Exception as e:
                logger.warning(f"分析 {comm_code} 失败: {e}")
                continue

        if scores:
            stats["avg_score"] = round(sum(scores) / len(scores), 2)
        if confidences:
            stats["avg_confidence"] = round(sum(confidences) / len(confidences), 1)

        return {
            "success": True,
            "analysis_date": target_date.isoformat(),
            "stats": stats
        }

    except Exception as e:
        logger.error(f"获取市场统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
