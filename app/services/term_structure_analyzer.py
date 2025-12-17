"""
期限结构分析服务 - Phase 3.5 & 3.6
功能:
1. 结构转换信号识别 (Contango ↔ Backwardation)
2. 价差历史分析 (百分位、变化率)
3. 为综合分析提供期限结构得分
"""

from typing import Optional, Dict, Any, List, Tuple
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
import numpy as np

from app.models.models import TermStructureHistory


class TermStructureAnalyzer:
    """期限结构分析器"""

    def __init__(self, db: Session):
        self.db = db

    def detect_structure_conversion(
        self,
        comm_code: str,
        target_date: date,
        lookback_days: int = 7
    ) -> Dict[str, Any]:
        """
        检测期限结构转换信号 (Phase 3.5核心功能)

        Args:
            comm_code: 品种代码
            target_date: 目标日期
            lookback_days: 回溯天数

        Returns:
            结构转换信号字典
        """
        # 获取当前记录
        current = self.db.query(TermStructureHistory).filter(
            TermStructureHistory.comm_code == comm_code,
            TermStructureHistory.record_date == target_date
        ).first()

        if not current:
            return {
                "has_conversion": False,
                "conversion_type": "无数据",
                "current_structure": None,
                "past_structure": None,
                "conversion_strength": "无",
                "signal_description": "无当前数据",
                "days_since_conversion": 0
            }

        # 获取N天前的记录
        past_date = target_date - timedelta(days=lookback_days)
        past = self.db.query(TermStructureHistory).filter(
            TermStructureHistory.comm_code == comm_code,
            TermStructureHistory.record_date <= past_date
        ).order_by(desc(TermStructureHistory.record_date)).first()

        if not past:
            return {
                "has_conversion": False,
                "conversion_type": "历史数据不足",
                "current_structure": current.structure_type,
                "past_structure": None,
                "conversion_strength": "无",
                "signal_description": "历史数据不足,无法判断转换",
                "days_since_conversion": 0
            }

        # 判断是否发生转换
        current_type = current.structure_type
        past_type = past.structure_type

        has_conversion = current_type != past_type
        conversion_type = "无转换"
        conversion_strength = "无"
        signal_description = ""

        if has_conversion:
            if past_type == "Contango" and current_type == "Backwardation":
                conversion_type = "正向→反向(空转多)"
                conversion_strength = "强"
                signal_description = (
                    f"⚠️ 结构重大转换!从正向市场转为反向市场,市场预期从看空转为看多。"
                    f"近月合约价格超过远月,供应紧张信号!"
                )
            elif past_type == "Backwardation" and current_type == "Contango":
                conversion_type = "反向→正向(多转空)"
                conversion_strength = "强"
                signal_description = (
                    f"⚠️ 结构重大转换!从反向市场转为正向市场,市场预期从看多转为看空。"
                    f"远月合约价格超过近月,库存压力增加!"
                )
            elif past_type == "Neutral" and current_type == "Contango":
                conversion_type = "中性→正向"
                conversion_strength = "中"
                signal_description = "市场从平衡转向正向,预期偏空"
            elif past_type == "Neutral" and current_type == "Backwardation":
                conversion_type = "中性→反向"
                conversion_strength = "中"
                signal_description = "市场从平衡转向反向,预期偏多"
            else:
                conversion_type = f"{past_type}→{current_type}"
                conversion_strength = "弱"
                signal_description = "结构发生变化"

        else:
            signal_description = f"结构保持{current_type},无转换信号"

        # 计算当前结构持续天数
        days_since_conversion = self._calculate_structure_持续天数(
            comm_code, target_date, current_type
        )

        # 价差变化分析
        spread_change = (current.price_spread or 0) - (past.price_spread or 0)
        spread_change_pct = (
            (spread_change / abs(past.price_spread) * 100)
            if past.price_spread and abs(past.price_spread) > 0.01
            else 0
        )

        return {
            "has_conversion": has_conversion,
            "conversion_type": conversion_type,
            "current_structure": current_type,
            "past_structure": past_type,
            "conversion_strength": conversion_strength,
            "signal_description": signal_description,
            "days_since_conversion": days_since_conversion,
            "current_spread": current.price_spread,
            "past_spread": past.price_spread,
            "spread_change": round(spread_change, 2),
            "spread_change_pct": round(spread_change_pct, 2)
        }

    def _calculate_structure_持续天数(
        self,
        comm_code: str,
        target_date: date,
        current_type: str
    ) -> int:
        """计算当前结构持续了多少天"""
        # 获取最近30天的记录
        past_30d = target_date - timedelta(days=30)
        records = self.db.query(TermStructureHistory).filter(
            TermStructureHistory.comm_code == comm_code,
            TermStructureHistory.record_date >= past_30d,
            TermStructureHistory.record_date <= target_date
        ).order_by(desc(TermStructureHistory.record_date)).all()

        if not records:
            return 0

        # 倒序计数,直到遇到不同的结构类型
        days = 0
        for record in records:
            if record.structure_type == current_type:
                days += 1
            else:
                break

        return days

    def analyze_spread_history(
        self,
        comm_code: str,
        target_date: date,
        lookback_30d: bool = True,
        lookback_90d: bool = True
    ) -> Dict[str, Any]:
        """
        价差历史分析 (Phase 3.6核心功能)

        Args:
            comm_code: 品种代码
            target_date: 目标日期
            lookback_30d: 是否计算30日指标
            lookback_90d: 是否计算90日指标

        Returns:
            价差分析字典
        """
        # 获取当前记录
        current = self.db.query(TermStructureHistory).filter(
            TermStructureHistory.comm_code == comm_code,
            TermStructureHistory.record_date == target_date
        ).first()

        if not current or current.price_spread is None:
            return {
                "current_spread": None,
                "spread_percentile_30d": None,
                "spread_percentile_90d": None,
                "spread_mean_30d": None,
                "spread_std_30d": None,
                "spread_zscore": None,
                "spread_change_3d": None,
                "spread_change_7d": None,
                "spread_status": "无数据"
            }

        current_spread = current.price_spread

        result = {
            "current_spread": round(current_spread, 2),
            "spread_pct": round(current.spread_pct or 0, 2)
        }

        # 30日分析
        if lookback_30d:
            past_30d = target_date - timedelta(days=30)
            records_30d = self.db.query(TermStructureHistory.price_spread).filter(
                TermStructureHistory.comm_code == comm_code,
                TermStructureHistory.record_date >= past_30d,
                TermStructureHistory.record_date <= target_date,
                TermStructureHistory.price_spread.isnot(None)
            ).all()

            if records_30d:
                spreads_30d = [r[0] for r in records_30d]
                result["spread_percentile_30d"] = self._calculate_percentile(
                    current_spread, spreads_30d
                )
                result["spread_mean_30d"] = round(np.mean(spreads_30d), 2)
                result["spread_std_30d"] = round(np.std(spreads_30d), 2)

                # Z-score
                if result["spread_std_30d"] > 0:
                    result["spread_zscore"] = round(
                        (current_spread - result["spread_mean_30d"]) / result["spread_std_30d"],
                        2
                    )
                else:
                    result["spread_zscore"] = 0

        # 90日分析
        if lookback_90d:
            past_90d = target_date - timedelta(days=90)
            records_90d = self.db.query(TermStructureHistory.price_spread).filter(
                TermStructureHistory.comm_code == comm_code,
                TermStructureHistory.record_date >= past_90d,
                TermStructureHistory.record_date <= target_date,
                TermStructureHistory.price_spread.isnot(None)
            ).all()

            if records_90d:
                spreads_90d = [r[0] for r in records_90d]
                result["spread_percentile_90d"] = self._calculate_percentile(
                    current_spread, spreads_90d
                )

        # 变化率分析
        # 3日变化率
        past_3d = target_date - timedelta(days=3)
        record_3d = self.db.query(TermStructureHistory).filter(
            TermStructureHistory.comm_code == comm_code,
            TermStructureHistory.record_date <= past_3d,
            TermStructureHistory.price_spread.isnot(None)
        ).order_by(desc(TermStructureHistory.record_date)).first()

        if record_3d and record_3d.price_spread:
            change_3d = current_spread - record_3d.price_spread
            result["spread_change_3d"] = round(
                (change_3d / abs(record_3d.price_spread) * 100)
                if abs(record_3d.price_spread) > 0.01 else 0,
                2
            )
        else:
            result["spread_change_3d"] = None

        # 7日变化率
        past_7d = target_date - timedelta(days=7)
        record_7d = self.db.query(TermStructureHistory).filter(
            TermStructureHistory.comm_code == comm_code,
            TermStructureHistory.record_date <= past_7d,
            TermStructureHistory.price_spread.isnot(None)
        ).order_by(desc(TermStructureHistory.record_date)).first()

        if record_7d and record_7d.price_spread:
            change_7d = current_spread - record_7d.price_spread
            result["spread_change_7d"] = round(
                (change_7d / abs(record_7d.price_spread) * 100)
                if abs(record_7d.price_spread) > 0.01 else 0,
                2
            )
        else:
            result["spread_change_7d"] = None

        # 判断价差状态
        result["spread_status"] = self._judge_spread_status(result)

        return result

    def _calculate_percentile(self, value: float, data: List[float]) -> float:
        """计算百分位"""
        if not data:
            return 50.0

        return round(
            (sum(1 for x in data if x <= value) / len(data)) * 100,
            2
        )

    def _judge_spread_status(self, analysis: Dict) -> str:
        """判断价差状态"""
        percentile_30d = analysis.get("spread_percentile_30d", 50)
        zscore = analysis.get("spread_zscore", 0)
        change_7d = analysis.get("spread_change_7d", 0)

        if percentile_30d is None:
            return "数据不足"

        if percentile_30d >= 90:
            status = "历史极高位"
        elif percentile_30d >= 70:
            status = "历史高位"
        elif percentile_30d >= 30:
            status = "历史中位"
        elif percentile_30d >= 10:
            status = "历史低位"
        else:
            status = "历史极低位"

        # 加上变化趋势
        if change_7d and abs(change_7d) > 10:
            if change_7d > 0:
                status += " (快速扩大)"
            else:
                status += " (快速收窄)"

        return status

    def get_term_structure_score_for_综合分析(
        self,
        comm_code: str,
        target_date: date
    ) -> Tuple[float, List[str]]:
        """
        为多维度综合分析提供期限结构得分

        Returns:
            (得分, 理由列表)
            得分范围: -5 到 +5
        """
        # 获取当前记录
        current = self.db.query(TermStructureHistory).filter(
            TermStructureHistory.comm_code == comm_code,
            TermStructureHistory.record_date == target_date
        ).first()

        if not current:
            return (0, ["无期限结构数据"])

        # 获取转换信号
        conversion = self.detect_structure_conversion(comm_code, target_date)

        # 获取价差分析
        spread_analysis = self.analyze_spread_history(comm_code, target_date)

        # 基础得分 (基于结构类型)
        structure_type = current.structure_type

        if structure_type == "Backwardation":
            base_score = 3  # 反向市场,看多
        elif structure_type == "Contango":
            base_score = -3  # 正向市场,看空
        else:
            base_score = 0  # 中性

        # 转换信号加成
        if conversion["has_conversion"]:
            if conversion["conversion_strength"] == "强":
                if "空转多" in conversion["conversion_type"]:
                    base_score = 5  # 强烈看多信号
                elif "多转空" in conversion["conversion_type"]:
                    base_score = -5  # 强烈看空信号

        # 价差百分位调整
        percentile_30d = spread_analysis.get("spread_percentile_30d", 50)
        if percentile_30d is not None:
            # 如果是Contango
            if structure_type == "Contango":
                # 价差极大(90分位以上),看空更强
                if percentile_30d >= 90:
                    base_score -= 1
                # 价差极小(10分位以下),可能即将转换
                elif percentile_30d <= 10:
                    base_score += 0.5

            # 如果是Backwardation
            elif structure_type == "Backwardation":
                # 价差极大(90分位以上),看多更强
                if percentile_30d >= 90:
                    base_score += 1
                # 价差极小(10分位以下),可能即将转换
                elif percentile_30d <= 10:
                    base_score -= 0.5

        # 限制在-5到+5范围
        final_score = max(-5, min(5, base_score))

        # 生成理由
        reasons = []

        if abs(final_score) >= 3:
            if structure_type == "Backwardation":
                reasons.append(
                    f"✅ 期限结构为反向市场(Backwardation),近月升水"
                    f"{abs(spread_analysis['current_spread']):.0f}元,供应紧张"
                )
            elif structure_type == "Contango":
                reasons.append(
                    f"❌ 期限结构为正向市场(Contango),远月升水"
                    f"{abs(spread_analysis['current_spread']):.0f}元,库存压力"
                )

        # 转换信号提示
        if conversion["has_conversion"] and conversion["conversion_strength"] == "强":
            reasons.append(
                f"⚠️ {conversion['conversion_type']}: {conversion['signal_description']}"
            )

        # 价差位置提示
        if percentile_30d is not None and (percentile_30d >= 90 or percentile_30d <= 10):
            reasons.append(
                f"📊 价差处于{spread_analysis['spread_status']}"
            )

        # 持续天数
        if conversion["days_since_conversion"] >= 7:
            reasons.append(
                f"ℹ️ 当前结构已持续{conversion['days_since_conversion']}天"
            )

        return (round(final_score, 2), reasons)

    def calculate_all_enhancements(
        self,
        comm_code: str,
        target_date: date
    ) -> Dict[str, Any]:
        """
        计算所有期限结构增强指标

        Args:
            comm_code: 品种代码
            target_date: 目标日期

        Returns:
            包含所有增强指标的字典
        """
        # 1. 结构转换信号
        conversion = self.detect_structure_conversion(comm_code, target_date)

        # 2. 价差历史分析
        spread_analysis = self.analyze_spread_history(comm_code, target_date)

        # 3. 综合得分
        score, reasons = self.get_term_structure_score_for_综合分析(
            comm_code, target_date
        )

        return {
            "comm_code": comm_code,
            "analysis_date": target_date.isoformat(),
            "conversion": conversion,
            "spread_analysis": spread_analysis,
            "score": score,
            "reasons": reasons
        }
