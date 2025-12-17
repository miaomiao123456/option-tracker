"""
研报评级增强分析服务
Phase 2: 实现评级一致性指标、变化信号、情绪指数
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
import numpy as np
from app.models.models import MarketFullView, ResearchReport


class ResearchEnhancementService:
    """研报评级增强分析服务"""

    def __init__(self, db: Session):
        self.db = db

    def calculate_consistency_metrics(
        self,
        comm_code: str,
        target_date: date
    ) -> Dict[str, Any]:
        """
        计算评级一致性指标

        Args:
            comm_code: 品种代码
            target_date: 目标日期

        Returns:
            一致性指标字典
        """
        # 获取当日的市场全景数据
        record = self.db.query(MarketFullView).filter(
            MarketFullView.comm_code == comm_code,
            MarketFullView.record_date == target_date
        ).first()

        if not record:
            return {
                "consistency_score": None,
                "bull_count": 0,
                "bear_count": 0,
                "neutral_count": 0,
                "total_count": 0,
                "dominant_view": "无数据",
                "dominant_ratio": 0,
                "divergence_level": "无数据"
            }

        bull_count = record.excessive_num or 0
        neutral_count = record.neutral_num or 0
        bear_count = record.empty_num or 0
        total_count = record.total_num or 0

        if total_count == 0:
            return {
                "consistency_score": 0,
                "bull_count": 0,
                "bear_count": 0,
                "neutral_count": 0,
                "total_count": 0,
                "dominant_view": "无数据",
                "dominant_ratio": 0,
                "divergence_level": "无数据"
            }

        # 计算一致性得分 (0-100)
        # 一致性 = 主流观点占比,越高越一致
        dominant_ratio = record.more_rate or 0
        consistency_score = dominant_ratio

        # 判断主流观点
        dominant_view = record.more_port or "中性"

        # 计算分歧度等级
        if dominant_ratio >= 80:
            divergence_level = "高度一致"
        elif dominant_ratio >= 70:
            divergence_level = "较一致"
        elif dominant_ratio >= 60:
            divergence_level = "略有分歧"
        else:
            divergence_level = "严重分歧"

        return {
            "consistency_score": round(consistency_score, 2),
            "bull_count": bull_count,
            "bear_count": bear_count,
            "neutral_count": neutral_count,
            "total_count": total_count,
            "dominant_view": dominant_view,
            "dominant_ratio": round(dominant_ratio, 2),
            "divergence_level": divergence_level
        }

    def calculate_rating_change_signals(
        self,
        comm_code: str,
        target_date: date,
        lookback_days: int = 7
    ) -> Dict[str, Any]:
        """
        计算评级变化信号 (7日对比)

        Args:
            comm_code: 品种代码
            target_date: 目标日期
            lookback_days: 回溯天数

        Returns:
            评级变化信号
        """
        # 获取当前记录
        current = self.db.query(MarketFullView).filter(
            MarketFullView.comm_code == comm_code,
            MarketFullView.record_date == target_date
        ).first()

        if not current:
            return {
                "has_change": False,
                "change_type": "无数据",
                "bull_change": 0,
                "bear_change": 0,
                "signal_strength": "无",
                "signal_description": "无数据"
            }

        # 获取N天前的记录
        past_date = target_date - timedelta(days=lookback_days)
        past = self.db.query(MarketFullView).filter(
            MarketFullView.comm_code == comm_code,
            MarketFullView.record_date <= past_date
        ).order_by(desc(MarketFullView.record_date)).first()

        if not past:
            return {
                "has_change": False,
                "change_type": "历史数据不足",
                "bull_change": 0,
                "bear_change": 0,
                "signal_strength": "无",
                "signal_description": "历史数据不足"
            }

        # 计算变化
        bull_change = (current.excessive_num or 0) - (past.excessive_num or 0)
        bear_change = (current.empty_num or 0) - (past.empty_num or 0)

        bull_ratio_change = (current.excessive_ratio or 0) - (past.excessive_ratio or 0)
        bear_ratio_change = (current.empty_ratio or 0) - (past.empty_ratio or 0)

        # 判断变化类型
        change_type = "无明显变化"
        signal_strength = "无"
        signal_description = ""

        if bull_change >= 3:
            change_type = "转向看多"
            if bull_change >= 5:
                signal_strength = "强"
                signal_description = f"新增{bull_change}家看多机构,市场情绪转向看多"
            else:
                signal_strength = "中"
                signal_description = f"新增{bull_change}家看多机构,看多情绪增强"
        elif bear_change >= 3:
            change_type = "转向看空"
            if bear_change >= 5:
                signal_strength = "强"
                signal_description = f"新增{bear_change}家看空机构,市场情绪转向看空"
            else:
                signal_strength = "中"
                signal_description = f"新增{bear_change}家看空机构,看空情绪增强"
        elif bull_change <= -3:
            change_type = "看多减少"
            signal_strength = "中"
            signal_description = f"减少{abs(bull_change)}家看多机构,看多情绪减弱"
        elif bear_change <= -3:
            change_type = "看空减少"
            signal_strength = "中"
            signal_description = f"减少{abs(bear_change)}家看空机构,看空情绪减弱"

        # 检测观点转换 (从看空转看多,或从看多转看空)
        past_dominant = past.more_port
        current_dominant = current.more_port

        if past_dominant == "偏空" and current_dominant == "偏多":
            change_type = "观点逆转(空→多)"
            signal_strength = "强"
            signal_description = f"市场主流观点从看空转为看多,强烈转向信号!"
        elif past_dominant == "偏多" and current_dominant == "偏空":
            change_type = "观点逆转(多→空)"
            signal_strength = "强"
            signal_description = f"市场主流观点从看多转为看空,强烈转向信号!"

        return {
            "has_change": change_type != "无明显变化",
            "change_type": change_type,
            "bull_change": bull_change,
            "bear_change": bear_change,
            "bull_ratio_change": round(bull_ratio_change, 2),
            "bear_ratio_change": round(bear_ratio_change, 2),
            "signal_strength": signal_strength,
            "signal_description": signal_description,
            "past_dominant": past_dominant,
            "current_dominant": current_dominant
        }

    def calculate_bull_bear_index(
        self,
        comm_code: str,
        target_date: date
    ) -> Dict[str, Any]:
        """
        计算Bull-Bear综合情绪指数

        指数范围: -100 到 +100
        +100 = 100%看多
        0 = 中性
        -100 = 100%看空

        Args:
            comm_code: 品种代码
            target_date: 目标日期

        Returns:
            情绪指数字典
        """
        record = self.db.query(MarketFullView).filter(
            MarketFullView.comm_code == comm_code,
            MarketFullView.record_date == target_date
        ).first()

        if not record or not record.total_num:
            return {
                "bb_index": 0,
                "index_level": "中性",
                "index_description": "无数据",
                "extreme_signal": None
            }

        # 计算Bull-Bear Index
        # BBI = (看多占比 - 看空占比) × 100
        bull_ratio = record.excessive_ratio or 0
        bear_ratio = record.empty_ratio or 0

        bb_index = (bull_ratio - bear_ratio)

        # 判断指数等级
        if bb_index >= 50:
            index_level = "极度乐观"
            index_description = f"市场极度乐观,{bull_ratio:.1f}%看多 vs {bear_ratio:.1f}%看空"
            extreme_signal = "狂热预警"  # 可能过于乐观
        elif bb_index >= 30:
            index_level = "乐观"
            index_description = f"市场偏乐观,{bull_ratio:.1f}%看多 vs {bear_ratio:.1f}%看空"
            extreme_signal = None
        elif bb_index >= 10:
            index_level = "偏乐观"
            index_description = f"市场略偏乐观"
            extreme_signal = None
        elif bb_index > -10:
            index_level = "中性"
            index_description = f"市场情绪中性"
            extreme_signal = None
        elif bb_index > -30:
            index_level = "偏悲观"
            index_description = f"市场略偏悲观"
            extreme_signal = None
        elif bb_index > -50:
            index_level = "悲观"
            index_description = f"市场偏悲观,{bear_ratio:.1f}%看空 vs {bull_ratio:.1f}%看多"
            extreme_signal = None
        else:
            index_level = "极度悲观"
            index_description = f"市场极度悲观,{bear_ratio:.1f}%看空 vs {bull_ratio:.1f}%看多"
            extreme_signal = "恐慌预警"  # 可能过于悲观

        return {
            "bb_index": round(bb_index, 2),
            "index_level": index_level,
            "index_description": index_description,
            "extreme_signal": extreme_signal,
            "bull_ratio": round(bull_ratio, 2),
            "bear_ratio": round(bear_ratio, 2)
        }

    def calculate_all_enhancements(
        self,
        comm_code: str,
        target_date: date
    ) -> Dict[str, Any]:
        """
        计算所有研报增强指标

        Args:
            comm_code: 品种代码
            target_date: 目标日期

        Returns:
            包含所有增强指标的字典
        """
        # 1. 一致性指标
        consistency = self.calculate_consistency_metrics(comm_code, target_date)

        # 2. 变化信号
        change_signals = self.calculate_rating_change_signals(comm_code, target_date)

        # 3. Bull-Bear指数
        bb_index = self.calculate_bull_bear_index(comm_code, target_date)

        # 合并所有结果
        result = {
            "comm_code": comm_code,
            "analysis_date": target_date.isoformat(),
            "consistency": consistency,
            "change_signals": change_signals,
            "bb_index": bb_index
        }

        return result

    def get_research_score_for_综合分析(
        self,
        comm_code: str,
        target_date: date
    ) -> Tuple[float, List[str]]:
        """
        为多维度综合分析提供研报维度得分

        Returns:
            (得分, 理由列表)
            得分范围: -5 到 +5
        """
        # 获取增强指标
        enhancements = self.calculate_all_enhancements(comm_code, target_date)

        consistency = enhancements["consistency"]
        bb_index_data = enhancements["bb_index"]

        # 基础得分 (基于Bull-Bear Index)
        bb_index = bb_index_data["bb_index"]

        if bb_index >= 50:
            base_score = 5
        elif bb_index >= 30:
            base_score = 3
        elif bb_index >= 10:
            base_score = 1
        elif bb_index > -10:
            base_score = 0
        elif bb_index > -30:
            base_score = -1
        elif bb_index > -50:
            base_score = -3
        else:
            base_score = -5

        # 一致性加成 (一致性越高,信号越可靠)
        consistency_score = consistency["consistency_score"] or 0
        if consistency_score >= 80:
            base_score *= 1.2  # 高度一致,得分加成20%
        elif consistency_score < 60:
            base_score *= 0.8  # 严重分歧,得分折扣20%

        # 限制在-5到+5范围
        final_score = max(-5, min(5, base_score))

        # 生成理由
        reasons = []

        if abs(final_score) >= 3:
            if final_score > 0:
                reasons.append(
                    f"✅ 研报机构多数看多({bb_index_data['bull_ratio']:.1f}%),基本面支撑"
                )
            else:
                reasons.append(
                    f"❌ 研报机构多数看空({bb_index_data['bear_ratio']:.1f}%),基本面承压"
                )

        # 一致性提示
        if consistency_score >= 80:
            reasons.append(
                f"✅ 机构观点高度一致({consistency_score:.0f}%),信号可靠性高"
            )
        elif consistency_score < 60:
            reasons.append(
                f"⚠️ 机构观点分歧较大,建议结合其他维度综合判断"
            )

        # 极端情绪预警
        if bb_index_data["extreme_signal"]:
            reasons.append(
                f"⚠️ {bb_index_data['extreme_signal']}: {bb_index_data['index_description']}"
            )

        return (round(final_score, 2), reasons)
