"""
虚实比增强分析服务
Phase 1.2-1.4: 实现历史位置、变化率、信号识别计算
"""

from typing import Optional, List, Dict, Any
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc
import numpy as np
from app.models.models import WarehouseReceipt


class VREnhancementService:
    """虚实比增强分析服务"""

    def __init__(self, db: Session):
        self.db = db

    def calculate_historical_position(
        self,
        comm_code: str,
        target_date: date,
        window_30d: int = 30,
        window_90d: int = 90
    ) -> Dict[str, Any]:
        """
        计算历史位置指标

        Args:
            comm_code: 品种代码
            target_date: 目标日期
            window_30d: 30日窗口期
            window_90d: 90日窗口期

        Returns:
            包含百分位、均值、标准差、Z-score的字典
        """
        # 获取30日和90日历史数据
        start_date_90d = target_date - timedelta(days=window_90d)
        start_date_30d = target_date - timedelta(days=window_30d)

        # 查询90日数据
        records_90d = self.db.query(WarehouseReceipt).filter(
            WarehouseReceipt.comm_code == comm_code,
            WarehouseReceipt.record_date >= start_date_90d,
            WarehouseReceipt.record_date <= target_date
        ).order_by(WarehouseReceipt.record_date).all()

        # 查询30日数据
        records_30d = [r for r in records_90d if r.record_date >= start_date_30d]

        # 获取当前值
        current_record = next(
            (r for r in records_90d if r.record_date == target_date),
            None
        )

        if not current_record or len(records_30d) < 5:
            # 数据不足，返回空值
            return {
                "percentile_30d": None,
                "percentile_90d": None,
                "mean_30d": None,
                "std_30d": None,
                "zscore": None
            }

        current_ratio = current_record.virtual_real_ratio

        # 提取虚实比值列表
        ratios_30d = np.array([r.virtual_real_ratio for r in records_30d])
        ratios_90d = np.array([r.virtual_real_ratio for r in records_90d])

        # 计算30日指标
        percentile_30d = self._calculate_percentile(current_ratio, ratios_30d)
        mean_30d = float(np.mean(ratios_30d))
        std_30d = float(np.std(ratios_30d))

        # 计算90日百分位
        percentile_90d = self._calculate_percentile(current_ratio, ratios_90d)

        # 计算Z-score (使用30日均值和标准差)
        zscore = (current_ratio - mean_30d) / std_30d if std_30d > 0 else 0

        return {
            "percentile_30d": round(percentile_30d, 2),
            "percentile_90d": round(percentile_90d, 2),
            "mean_30d": round(mean_30d, 2),
            "std_30d": round(std_30d, 2),
            "zscore": round(zscore, 4)
        }

    def calculate_change_rates(
        self,
        comm_code: str,
        target_date: date
    ) -> Dict[str, Any]:
        """
        计算变化率和加速度

        Args:
            comm_code: 品种代码
            target_date: 目标日期

        Returns:
            包含3日/7日变化率和加速度的字典
        """
        # 查询最近7日数据
        start_date = target_date - timedelta(days=10)  # 多查几天以确保有足够数据
        records = self.db.query(WarehouseReceipt).filter(
            WarehouseReceipt.comm_code == comm_code,
            WarehouseReceipt.record_date >= start_date,
            WarehouseReceipt.record_date <= target_date
        ).order_by(WarehouseReceipt.record_date).all()

        if len(records) < 2:
            return {
                "change_rate_3d": None,
                "change_rate_7d": None,
                "acceleration": None
            }

        # 按日期排序
        records_sorted = sorted(records, key=lambda x: x.record_date)

        # 获取当前记录
        current_idx = next(
            (i for i, r in enumerate(records_sorted) if r.record_date == target_date),
            None
        )

        if current_idx is None:
            return {
                "change_rate_3d": None,
                "change_rate_7d": None,
                "acceleration": None
            }

        current_ratio = records_sorted[current_idx].virtual_real_ratio

        # 计算3日变化率
        change_rate_3d = None
        if current_idx >= 2:
            ratio_3d_ago = records_sorted[current_idx - 2].virtual_real_ratio
            if ratio_3d_ago > 0:
                change_rate_3d = (current_ratio - ratio_3d_ago) / ratio_3d_ago

        # 计算7日变化率
        change_rate_7d = None
        if current_idx >= 6:
            ratio_7d_ago = records_sorted[current_idx - 6].virtual_real_ratio
            if ratio_7d_ago > 0:
                change_rate_7d = (current_ratio - ratio_7d_ago) / ratio_7d_ago

        # 计算加速度 (二阶导数)
        # acceleration = (今日变化率 - 昨日变化率)
        acceleration = None
        if current_idx >= 2:
            ratios = [records_sorted[i].virtual_real_ratio for i in range(max(0, current_idx - 2), current_idx + 1)]
            if len(ratios) == 3 and all(r > 0 for r in ratios):
                # 一阶导数 (变化率)
                change_1 = (ratios[1] - ratios[0]) / ratios[0]
                change_2 = (ratios[2] - ratios[1]) / ratios[1]
                # 二阶导数 (加速度)
                acceleration = change_2 - change_1

        return {
            "change_rate_3d": round(change_rate_3d, 4) if change_rate_3d is not None else None,
            "change_rate_7d": round(change_rate_7d, 4) if change_rate_7d is not None else None,
            "acceleration": round(acceleration, 4) if acceleration is not None else None
        }

    def identify_signals(
        self,
        comm_code: str,
        target_date: date,
        historical_position: Dict[str, Any],
        change_rates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        识别交易信号

        Args:
            comm_code: 品种代码
            target_date: 目标日期
            historical_position: 历史位置指标
            change_rates: 变化率指标

        Returns:
            信号类型和得分
        """
        signals = []
        score = 0

        percentile_30d = historical_position.get("percentile_30d")
        percentile_90d = historical_position.get("percentile_90d")
        zscore = historical_position.get("zscore")
        change_rate_3d = change_rates.get("change_rate_3d")
        change_rate_7d = change_rates.get("change_rate_7d")
        acceleration = change_rates.get("acceleration")

        # 信号1: 极端退潮 (虚实比处于历史低位)
        if percentile_30d is not None and percentile_30d < 10:
            signals.append("极端退潮")
            score += 40
        elif percentile_30d is not None and percentile_30d < 20:
            signals.append("低位退潮")
            score += 20

        # 信号2: 加速退潮 (加速度明显负值)
        if acceleration is not None and acceleration < -0.1:
            signals.append("加速退潮")
            score += 30

        # 信号3: Z-score极端值 (统计异常)
        if zscore is not None:
            if zscore < -2:
                signals.append("统计低位")
                score += 25
            elif zscore > 2:
                signals.append("统计高位")
                score -= 20  # 高位是负面信号

        # 信号4: 7日持续下降
        if change_rate_7d is not None and change_rate_7d < -0.2:
            signals.append("持续下降")
            score += 15

        # 信号5: 反转信号 (低位+加速度转正)
        if (percentile_30d is not None and percentile_30d < 20 and
            acceleration is not None and acceleration > 0.05):
            signals.append("低位反转")
            score += 50

        # 确定信号类型
        if not signals:
            signal_type = "无明显信号"
            score = 0
        else:
            signal_type = " | ".join(signals)

        # 得分限制在0-100
        score = max(0, min(100, score))

        return {
            "signal_type": signal_type,
            "signal_score": score
        }

    def calculate_all_enhancements(
        self,
        comm_code: str,
        target_date: date
    ) -> Dict[str, Any]:
        """
        计算所有增强指标

        Args:
            comm_code: 品种代码
            target_date: 目标日期

        Returns:
            包含所有增强指标的字典
        """
        # 1. 计算历史位置
        historical_position = self.calculate_historical_position(comm_code, target_date)

        # 2. 计算变化率
        change_rates = self.calculate_change_rates(comm_code, target_date)

        # 3. 识别信号
        signals = self.identify_signals(
            comm_code,
            target_date,
            historical_position,
            change_rates
        )

        # 合并所有指标
        result = {
            **historical_position,
            **change_rates,
            **signals
        }

        return result

    def update_record_enhancements(
        self,
        comm_code: str,
        target_date: date
    ) -> bool:
        """
        更新数据库中的增强字段

        Args:
            comm_code: 品种代码
            target_date: 目标日期

        Returns:
            是否更新成功
        """
        try:
            # 计算所有增强指标
            enhancements = self.calculate_all_enhancements(comm_code, target_date)

            # 查找对应记录
            record = self.db.query(WarehouseReceipt).filter(
                WarehouseReceipt.comm_code == comm_code,
                WarehouseReceipt.record_date == target_date
            ).first()

            if not record:
                return False

            # 更新字段
            record.percentile_30d = enhancements["percentile_30d"]
            record.percentile_90d = enhancements["percentile_90d"]
            record.mean_30d = enhancements["mean_30d"]
            record.std_30d = enhancements["std_30d"]
            record.zscore = enhancements["zscore"]
            record.change_rate_3d = enhancements["change_rate_3d"]
            record.change_rate_7d = enhancements["change_rate_7d"]
            record.acceleration = enhancements["acceleration"]
            record.signal_type = enhancements["signal_type"]
            record.signal_score = enhancements["signal_score"]

            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            print(f"❌ 更新增强字段失败 {comm_code} @ {target_date}: {e}")
            return False

    def batch_update_all_records(
        self,
        target_date: Optional[date] = None
    ) -> Dict[str, int]:
        """
        批量更新所有品种的增强字段

        Args:
            target_date: 目标日期，为None则更新最新日期

        Returns:
            更新统计信息
        """
        # 确定目标日期
        if target_date is None:
            latest_date = self.db.query(WarehouseReceipt.record_date).order_by(
                desc(WarehouseReceipt.record_date)
            ).first()
            if not latest_date:
                return {"success": 0, "failed": 0}
            target_date = latest_date[0]

        # 获取该日期的所有品种
        records = self.db.query(WarehouseReceipt).filter(
            WarehouseReceipt.record_date == target_date
        ).all()

        success_count = 0
        failed_count = 0

        print(f"🔄 开始批量更新 {target_date} 的增强字段...")
        print(f"📊 共 {len(records)} 个品种需要更新")

        for record in records:
            success = self.update_record_enhancements(record.comm_code, target_date)
            if success:
                success_count += 1
                print(f"  ✅ {record.comm_code} ({record.variety_name})")
            else:
                failed_count += 1
                print(f"  ❌ {record.comm_code} ({record.variety_name})")

        print(f"\n✅ 更新完成: 成功 {success_count}, 失败 {failed_count}")

        return {
            "success": success_count,
            "failed": failed_count,
            "total": len(records)
        }

    @staticmethod
    def _calculate_percentile(value: float, data: np.ndarray) -> float:
        """
        计算value在data中的百分位

        Args:
            value: 当前值
            data: 历史数据数组

        Returns:
            百分位 (0-100)
        """
        if len(data) == 0:
            return 50.0

        # 计算有多少个值小于等于当前值
        count_below = np.sum(data <= value)
        percentile = (count_below / len(data)) * 100

        return percentile
