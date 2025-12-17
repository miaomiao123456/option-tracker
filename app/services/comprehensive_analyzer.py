"""
多维度综合分析服务 - Phase 5
整合三个维度: 虚实比(15%) + 期限结构(30%) + 研报(25%) = 70%
资金维度(30%)待Phase 4完成后补充
"""

from typing import Optional, Dict, Any, List, Tuple
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import desc
import logging

from app.models.models import (
    WarehouseReceipt,
    TermStructureHistory,
    MarketFullView
)
from app.services.vr_enhancement_service import VREnhancementService
from app.services.term_structure_analyzer import TermStructureAnalyzer
from app.services.research_enhancement_service import ResearchEnhancementService

logger = logging.getLogger(__name__)


class ComprehensiveAnalyzer:
    """
    多维度综合分析器

    权重配置(三维度版本):
    - 期限结构: 42.8% (30/70)
    - 研报基本面: 35.7% (25/70)
    - 虚实比: 21.4% (15/70)
    总计: 100%

    注: 资金维度(30%)待补充后,权重将重新调整为:
    期限结构30% + 资金30% + 研报25% + 虚实比15%
    """

    def __init__(self, db: Session):
        self.db = db

        # 三维度权重(归一化到100%)
        self.weights = {
            "term": 0.428,      # 期限结构 30/70
            "research": 0.357,  # 研报基本面 25/70
            "vr": 0.214        # 虚实比 15/70
        }

        # 创建各维度分析器
        self.vr_service = VREnhancementService(db)
        self.term_analyzer = TermStructureAnalyzer(db)
        self.research_service = ResearchEnhancementService(db)

    def analyze(
        self,
        comm_code: str,
        target_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        执行多维度综合分析

        Args:
            comm_code: 品种代码
            target_date: 分析日期,默认为最新日期

        Returns:
            综合分析结果
        """
        # 使用最新日期
        if not target_date:
            target_date = self._get_latest_date()

        logger.info(f"开始综合分析: {comm_code} @ {target_date}")

        # 1. 获取各维度得分
        scores = self._calculate_all_dimension_scores(comm_code, target_date)

        # 2. 计算综合得分
        total_score = self._calculate_total_score(scores)

        # 3. 判断方向和强度
        direction_info = self._get_direction_and_strength(total_score)

        # 4. 生成分析理由
        reasons = self._generate_reasons(scores, direction_info)

        # 5. 生成风险提示
        risks = self._generate_risks(comm_code, target_date, scores, direction_info)

        # 6. 计算置信度
        confidence = self._calculate_confidence(scores, direction_info)

        return {
            "comm_code": comm_code,
            "analysis_date": target_date.isoformat(),
            "total_score": round(total_score, 2),
            "direction": direction_info["direction"],
            "strength": direction_info["strength"],
            "grade": direction_info["grade"],
            "confidence": confidence,
            "dimensions": {
                "term_score": scores["term_score"],
                "research_score": scores["research_score"],
                "vr_score": scores["vr_score"],
                "capital_score": None  # 待补充
            },
            "weights": self.weights,
            "reasons": reasons,
            "risks": risks,
            "raw_data": scores.get("raw_data", {})
        }

    def _get_latest_date(self) -> date:
        """获取最新的数据日期"""
        # 从期限结构表获取最新日期
        latest = self.db.query(TermStructureHistory.record_date).order_by(
            desc(TermStructureHistory.record_date)
        ).first()

        return latest[0] if latest else date.today()

    def _calculate_all_dimension_scores(
        self,
        comm_code: str,
        target_date: date
    ) -> Dict[str, Any]:
        """计算各维度得分"""

        scores = {
            "term_score": 0,
            "research_score": 0,
            "vr_score": 0,
            "term_reasons": [],
            "research_reasons": [],
            "vr_reasons": [],
            "raw_data": {}
        }

        # 1. 期限结构得分 (-5 到 +5)
        try:
            term_score, term_reasons = self.term_analyzer.get_term_structure_score_for_综合分析(
                comm_code, target_date
            )
            scores["term_score"] = term_score
            scores["term_reasons"] = term_reasons

            # 获取原始数据
            term_data = self.db.query(TermStructureHistory).filter(
                TermStructureHistory.comm_code == comm_code,
                TermStructureHistory.record_date == target_date
            ).first()

            if term_data:
                scores["raw_data"]["term_structure"] = {
                    "structure_type": term_data.structure_type,
                    "price_spread": term_data.price_spread,
                    "grade": term_data.grade
                }
        except Exception as e:
            logger.warning(f"期限结构得分计算失败: {e}")
            scores["term_reasons"] = ["期限结构数据不可用"]

        # 2. 研报基本面得分 (-5 到 +5)
        try:
            research_score, research_reasons = self.research_service.get_research_score_for_综合分析(
                comm_code, target_date
            )
            scores["research_score"] = research_score
            scores["research_reasons"] = research_reasons

            # 获取原始数据
            research_data = self.db.query(MarketFullView).filter(
                MarketFullView.comm_code == comm_code,
                MarketFullView.record_date == target_date
            ).first()

            if research_data:
                scores["raw_data"]["research"] = {
                    "excessive_ratio": research_data.excessive_ratio,
                    "empty_ratio": research_data.empty_ratio,
                    "more_port": research_data.more_port
                }
        except Exception as e:
            logger.warning(f"研报得分计算失败: {e}")
            scores["research_reasons"] = ["研报数据不可用"]

        # 3. 虚实比辅助得分 (-2 到 +2)
        try:
            vr_score, vr_reasons = self._calculate_vr_assist_score(
                comm_code, target_date, scores["term_score"], scores["research_score"]
            )
            scores["vr_score"] = vr_score
            scores["vr_reasons"] = vr_reasons

            # 获取原始数据
            vr_data = self.db.query(WarehouseReceipt).filter(
                WarehouseReceipt.comm_code == comm_code,
                WarehouseReceipt.record_date == target_date
            ).first()

            if vr_data:
                scores["raw_data"]["vr"] = {
                    "virtual_real_ratio": vr_data.virtual_real_ratio,
                    "squeeze_risk": vr_data.squeeze_risk,
                    "signal_type": vr_data.signal_type
                }
        except Exception as e:
            logger.warning(f"虚实比得分计算失败: {e}")
            scores["vr_reasons"] = ["虚实比数据不可用"]

        return scores

    def _calculate_vr_assist_score(
        self,
        comm_code: str,
        target_date: date,
        term_score: float,
        research_score: float
    ) -> Tuple[float, List[str]]:
        """
        计算虚实比辅助得分
        虚实比不能独立判断方向,只能辅助验证其他维度的信号
        """
        # 获取虚实比数据
        vr_data = self.db.query(WarehouseReceipt).filter(
            WarehouseReceipt.comm_code == comm_code,
            WarehouseReceipt.record_date == target_date
        ).first()

        if not vr_data:
            return (0, ["虚实比数据不可用"])

        ratio = vr_data.virtual_real_ratio or 0
        signal_type = vr_data.signal_type or ""
        score = 0
        reasons = []

        # 虚实比辅助逻辑:
        # 1. 如果其他维度都看多,虚实比可以验证强度
        if term_score > 0 and research_score > 0:
            # 多头趋势
            if ratio > 100:
                score = -1  # 虽然看多,但逼仓风险高,减分
                reasons.append("⚠️ 虚实比过高(逼仓风险),虽看多但需谨慎")
            elif ratio > 50:
                score = 0  # 中性
                reasons.append("ℹ️ 虚实比适中,看多信号有效")
            else:
                score = 1  # 低虚实比,安全的多头
                reasons.append("✅ 虚实比较低,库存充足,看多较安全")

        # 2. 如果其他维度都看空,虚实比可以验证强度
        elif term_score < 0 and research_score < 0:
            # 空头趋势
            if ratio < 20:
                score = -1  # 库存充足,看空信号更强
                reasons.append("✅ 虚实比低,库存充足,看空信号强")
            elif ratio < 50:
                score = 0  # 中性
                reasons.append("ℹ️ 虚实比适中,看空信号有效")
            else:
                score = 1  # 高虚实比,看空需谨慎
                reasons.append("⚠️ 虚实比较高,看空需注意逼仓风险")

        # 3. 如果方向不一致,虚实比不提供信号
        else:
            score = 0
            reasons.append("ℹ️ 其他维度信号分歧,虚实比暂不做判断")

        # 信号增强
        if signal_type and "退潮" in signal_type:
            reasons.append(f"📊 虚实比信号: {signal_type}")

        return (score, reasons)

    def _calculate_total_score(self, scores: Dict[str, Any]) -> float:
        """计算加权综合得分"""
        total = (
            scores["term_score"] * self.weights["term"] +
            scores["research_score"] * self.weights["research"] +
            scores["vr_score"] * self.weights["vr"]
        )

        return total

    def _get_direction_and_strength(self, total_score: float) -> Dict[str, Any]:
        """根据综合得分判断方向和强度"""

        if total_score >= 3.5:
            return {
                "direction": "多头",
                "strength": "强烈看多",
                "grade": "S",
                "color": "danger",
                "confidence_base": 95
            }
        elif total_score >= 2.0:
            return {
                "direction": "多头",
                "strength": "看多",
                "grade": "A",
                "color": "warning",
                "confidence_base": 80
            }
        elif total_score >= 0.5:
            return {
                "direction": "多头",
                "strength": "偏多",
                "grade": "B",
                "color": "success",
                "confidence_base": 60
            }
        elif total_score > -0.5:
            return {
                "direction": "中性",
                "strength": "中性",
                "grade": "C",
                "color": "info",
                "confidence_base": 40
            }
        elif total_score > -2.0:
            return {
                "direction": "空头",
                "strength": "偏空",
                "grade": "B",
                "color": "success",
                "confidence_base": 60
            }
        elif total_score > -3.5:
            return {
                "direction": "空头",
                "strength": "看空",
                "grade": "A",
                "color": "warning",
                "confidence_base": 80
            }
        else:
            return {
                "direction": "空头",
                "strength": "强烈看空",
                "grade": "S",
                "color": "danger",
                "confidence_base": 95
            }

    def _generate_reasons(
        self,
        scores: Dict[str, Any],
        direction_info: Dict[str, Any]
    ) -> List[str]:
        """生成分析理由"""
        reasons = []

        # 添加综合结论
        reasons.append(
            f"🎯 综合判断: {direction_info['strength']} "
            f"(得分: {scores.get('term_score', 0) * self.weights['term'] + scores.get('research_score', 0) * self.weights['research'] + scores.get('vr_score', 0) * self.weights['vr']:.2f}分)"
        )

        # 添加各维度理由
        if scores.get("term_reasons"):
            reasons.extend(scores["term_reasons"])

        if scores.get("research_reasons"):
            reasons.extend(scores["research_reasons"])

        if scores.get("vr_reasons"):
            reasons.extend(scores["vr_reasons"])

        return reasons

    def _generate_risks(
        self,
        comm_code: str,
        target_date: date,
        scores: Dict[str, Any],
        direction_info: Dict[str, Any]
    ) -> List[str]:
        """生成风险提示"""
        risks = []

        # 1. 维度分歧风险
        term_score = scores.get("term_score", 0)
        research_score = scores.get("research_score", 0)

        # 如果期限结构和研报方向相反
        if (term_score > 1 and research_score < -1) or (term_score < -1 and research_score > 1):
            risks.append("⚠️ 期限结构与研报观点严重分歧,建议谨慎操作")

        # 2. 虚实比风险
        vr_data = scores.get("raw_data", {}).get("vr", {})
        if vr_data:
            ratio = vr_data.get("virtual_real_ratio", 0)
            if ratio > 100 and direction_info["direction"] == "多头":
                risks.append(f"⚠️ 虚实比高达{ratio:.0f},逼仓风险极高,需警惕反转")

        # 3. 置信度低风险
        confidence = direction_info.get("confidence_base", 50)
        if confidence < 60:
            risks.append("⚠️ 各维度信号较弱,建议等待更明确信号")

        # 4. 数据缺失风险
        missing_dims = []
        if not scores.get("term_reasons"):
            missing_dims.append("期限结构")
        if not scores.get("research_reasons"):
            missing_dims.append("研报")

        if missing_dims:
            risks.append(f"⚠️ 缺少{'/'.join(missing_dims)}数据,分析完整性受限")

        # 5. 三维度版本提示
        risks.append("ℹ️ 当前为三维度分析版本(缺资金维度),待资金数据补充后准确性将提升")

        return risks

    def _calculate_confidence(
        self,
        scores: Dict[str, Any],
        direction_info: Dict[str, Any]
    ) -> int:
        """计算置信度"""
        base_confidence = direction_info.get("confidence_base", 50)

        # 根据维度一致性调整
        term_score = scores.get("term_score", 0)
        research_score = scores.get("research_score", 0)

        # 如果两个主要维度方向一致,提升置信度
        if (term_score > 1 and research_score > 1) or (term_score < -1 and research_score < -1):
            base_confidence = min(100, base_confidence + 10)

        # 如果方向相反,降低置信度
        elif (term_score > 1 and research_score < -1) or (term_score < -1 and research_score > 1):
            base_confidence = max(30, base_confidence - 20)

        # 数据完整性调整
        available_dims = sum([
            1 if scores.get("term_reasons") else 0,
            1 if scores.get("research_reasons") else 0,
            1 if scores.get("vr_reasons") else 0
        ])

        if available_dims < 2:
            base_confidence = max(30, base_confidence - 15)

        return base_confidence
