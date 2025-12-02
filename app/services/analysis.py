"""
四维分析服务
核心逻辑：
1. 汇总基本面、资金面、技术面、消息面数据
2. 计算各维度得分 (-10 ~ 10)
3. 判定综合方向 (多/空/中性)
"""
import logging
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.models import (
    MarketAnalysisSummary, Commodity, FundamentalReport,
    InstitutionalPosition, TechnicalIndicator, OptionFlow,
    ContractInfo, DirectionEnum
)

logger = logging.getLogger(__name__)


class AnalysisService:
    def __init__(self, db: Session):
        self.db = db

    def run_daily_analysis(self, target_date: Optional[date] = None):
        """执行每日全品种分析"""
        if target_date is None:
            target_date = date.today()
            
        logger.info(f"开始执行每日分析: {target_date}")

        # 获取所有活跃品种
        commodities = self.db.query(Commodity).all()
        
        for comm in commodities:
            try:
                self.analyze_commodity(comm.code, target_date)
            except Exception as e:
                logger.error(f"分析品种 {comm.code} 失败: {e}")

    def analyze_commodity(self, comm_code: str, target_date: date):
        """分析单个品种"""
        # 1. 基本面评分
        fund_score, fund_reason = self._analyze_fundamental(comm_code, target_date)
        
        # 2. 资金面评分
        cap_score, cap_reason = self._analyze_capital(comm_code, target_date)
        
        # 3. 技术面评分
        tech_score, tech_reason = self._analyze_technical(comm_code, target_date)
        
        # 4. 消息面评分
        msg_score, msg_reason = self._analyze_message(comm_code, target_date)
        
        # 5. 综合判定
        total_score = fund_score + cap_score + tech_score + msg_score
        
        direction = DirectionEnum.NEUTRAL
        if total_score >= 5:
            direction = DirectionEnum.LONG
        elif total_score <= -5:
            direction = DirectionEnum.SHORT
            
        # 汇总理由
        reasons = []
        if fund_reason: reasons.append(f"[基本面] {fund_reason}")
        if cap_reason: reasons.append(f"[资金面] {cap_reason}")
        if tech_reason: reasons.append(f"[技术面] {tech_reason}")
        if msg_reason: reasons.append(f"[消息面] {msg_reason}")
        
        main_reason = "\n".join(reasons)
        
        # 保存结果
        summary = self.db.query(MarketAnalysisSummary).filter(
            MarketAnalysisSummary.comm_code == comm_code,
            MarketAnalysisSummary.date == target_date
        ).first()
        
        if not summary:
            summary = MarketAnalysisSummary(
                comm_code=comm_code,
                date=target_date
            )
            
        summary.fundamental_score = fund_score
        summary.capital_score = cap_score
        summary.technical_score = tech_score
        summary.message_score = msg_score
        summary.total_direction = direction
        summary.main_reason = main_reason
        summary.updated_at = datetime.now()
        
        self.db.add(summary)
        self.db.commit()
        
        logger.info(f"品种 {comm_code} 分析完成: {direction.value} (分: {total_score})")

    def _analyze_fundamental(self, comm_code: str, target_date: date) -> (int, str):
        """
        基本面分析逻辑
        数据源: 智汇期讯(hzzhqx), 方期看盘(founderfu)
        """
        score = 0
        reasons = []
        
        # 获取最近3天的研报
        start_date = target_date - timedelta(days=3)
        reports = self.db.query(FundamentalReport).filter(
            FundamentalReport.comm_code == comm_code,
            FundamentalReport.publish_time >= start_date
        ).all()
        
        bull_count = 0
        bear_count = 0
        
        for report in reports:
            if report.sentiment == 'bull':
                bull_count += 1
            elif report.sentiment == 'bear':
                bear_count += 1
                
        if bull_count > bear_count:
            score = 5
            reasons.append(f"近3日看多研报{bull_count}篇 > 看空{bear_count}篇")
        elif bear_count > bull_count:
            score = -5
            reasons.append(f"近3日看空研报{bear_count}篇 > 看多{bull_count}篇")
        else:
            reasons.append("多空研报数量持平")
            
        return score, "; ".join(reasons)

    def _analyze_capital(self, comm_code: str, target_date: date) -> (int, str):
        """
        资金面分析逻辑
        规则:
        1. 散户(东方财富): 净多>2亿 -> 看空; 净空>2亿 -> 看多 (反向指标)
        2. 机构(国泰君安/东证期货): 净空>5亿 -> 看空; 净多>5亿 -> 看多 (正向指标)
        """
        score = 0
        reasons = []
        
        # 获取合约乘数和最新价格用于计算市值
        contract_info = self.db.query(ContractInfo).filter(
            ContractInfo.comm_code == comm_code
        ).first()
        
        multiplier = contract_info.multiplier if contract_info else 10
        price = contract_info.latest_price if contract_info else 0
        
        if price == 0:
            return 0, "缺失价格数据，无法计算资金市值"
            
        # 获取最新持仓数据
        positions = self.db.query(InstitutionalPosition).filter(
            InstitutionalPosition.comm_code == comm_code,
            InstitutionalPosition.record_date == target_date
        ).all()
        
        # 散户逻辑 (东方财富)
        east_money = next((p for p in positions if "东方财富" in p.broker_name), None)
        if east_money:
            net_val = east_money.net_position * price * multiplier
            if net_val > 200_000_000: # 净多超2亿
                score -= 3
                reasons.append("散户(东财)大幅净多(反向看空)")
            elif net_val < -200_000_000: # 净空超2亿
                score += 3
                reasons.append("散户(东财)大幅净空(反向看多)")
                
        # 机构逻辑 (国泰君安, 东证期货)
        institutions = [p for p in positions if "国泰君安" in p.broker_name or "东证期货" in p.broker_name]
        for inst in institutions:
            net_val = inst.net_position * price * multiplier
            if net_val < -500_000_000: # 净空超5亿
                score -= 4
                reasons.append(f"机构({inst.broker_name})大幅净空")
            elif net_val > 500_000_000: # 净多超5亿
                score += 4
                reasons.append(f"机构({inst.broker_name})大幅净多")
                
        return min(max(score, -10), 10), "; ".join(reasons)

    def _analyze_technical(self, comm_code: str, target_date: date) -> (int, str):
        """
        技术面分析逻辑
        数据源: 融达数据(期限结构), OpenVLab(波动率背离)
        """
        score = 0
        reasons = []
        
        # 1. 期限结构 (融达)
        # 查找最近的记录
        tech_ind = self.db.query(TechnicalIndicator).filter(
            TechnicalIndicator.comm_code == comm_code
        ).order_by(TechnicalIndicator.record_time.desc()).first()
        
        if tech_ind:
            # 假设 Contango (升水) 天然空头? 用户需求: "Contango结构天然空头"
            if "contango" in str(tech_ind.term_structure).lower():
                score -= 3
                reasons.append("期限结构Contango(天然空头)")
            # 假设 Back (贴水) 天然多头? 用户需求: "back结构天然多头"
            elif "back" in str(tech_ind.term_structure).lower():
                score += 3
                reasons.append("期限结构Back(天然多头)")
                
        # 2. 波动率背离 (OpenVLab) - 暂时没有直接存储背离标志，需从OptionFlow推导或增加字段
        # 这里简化处理，如果有OptionFlow大额异动也算
        flows = self.db.query(OptionFlow).filter(
            OptionFlow.comm_code == comm_code,
            OptionFlow.record_time >= datetime.combine(target_date, datetime.min.time())
        ).all()
        
        if flows:
            net_flow_sum = sum(f.net_flow for f in flows if f.net_flow)
            if net_flow_sum > 1000: # 假设阈值
                score += 2
                reasons.append("期权资金大幅净流入")
            elif net_flow_sum < -1000:
                score -= 2
                reasons.append("期权资金大幅净流出")
                
        return min(max(score, -10), 10), "; ".join(reasons)

    def _analyze_message(self, comm_code: str, target_date: date) -> (int, str):
        """
        消息面分析
        目前主要是金十数据嵌入，后端难以量化，暂时给0分或基于人工录入
        """
        return 0, ""


def summarize_research_reports(
    trade_logics: List[str],
    related_datas: List[str],
    risk_factors: List[str],
    variety_name: str
) -> Dict[str, str]:
    """
    使用AI汇总多个研报的内容
    """
    from config.settings import get_settings
    import google.generativeai as genai

    settings = get_settings()

    try:
        # 配置Gemini API
        genai.configure(
            api_key=settings.GEMINI_API_KEY,
            transport='rest',
            client_options={'api_endpoint': settings.GEMINI_BASE_URL.replace('/v1', '')}
        )

        model = genai.GenerativeModel('gemini-pro')

        # 构建提示词
        prompt = f"""
你是一位专业的期货市场分析师,需要对以下{variety_name}品种的多份研报进行智能提炼和总结。

### 交易逻辑部分:
{chr(10).join(f"{i+1}. {logic}" for i, logic in enumerate(trade_logics))}

### 相关数据部分:
{chr(10).join(f"{i+1}. {data}" for i, data in enumerate(related_datas))}

### 风险因素部分:
{chr(10).join(f"{i+1}. {risk}" for i, risk in enumerate(risk_factors))}

请按以下要求进行智能提炼总结(每部分100-150字):

**交易逻辑总结要求:**
1. 提炼核心观点共识,用"【核心观点】"标注最重要的1-2个观点
2. 如有分歧,用"【多空分歧】"标注
3. 控制在80-120字,突出关键逻辑链条
4. 用简洁专业语言,分点表述

**相关数据总结要求:**
1. 用"【关键数据】"标注最重要的2-3个数据指标
2. 用"【变化趋势】"标注显著的变化
3. 控制在60-100字,突出异常数据或拐点
4. 必须包含具体数字和百分比

**风险因素总结要求:**
1. 用"【主要风险】"标注最重要的风险
2. 用"【次要风险】"标注其他风险
3. 控制在60-80字,按影响程度排序
4. 简明扼要,避免泛泛而谈

请严格按以下格式输出,确保标注清晰:

交易逻辑汇总:
[你的总结内容]

相关数据汇总:
[你的总结内容]

风险因素汇总:
[你的总结内容]
"""

        # 调用API
        response = model.generate_content(prompt)
        result_text = response.text

        # 解析返回结果
        summary = {
            "trade_logic": "",
            "related_data": "",
            "risk_factor": ""
        }

        # 更智能的解析逻辑
        lines = result_text.split('\n')
        current_section = None
        current_content = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检测段落标题
            if '交易逻辑' in line and '汇总' in line:
                if current_section and current_content:
                    summary[current_section] = '\n'.join(current_content).strip()
                current_section = 'trade_logic'
                current_content = []
            elif '相关数据' in line and '汇总' in line:
                if current_section and current_content:
                    summary[current_section] = '\n'.join(current_content).strip()
                current_section = 'related_data'
                current_content = []
            elif '风险因素' in line and '汇总' in line:
                if current_section and current_content:
                    summary[current_section] = '\n'.join(current_content).strip()
                current_section = 'risk_factor'
                current_content = []
            elif current_section and line and not line.startswith('['):
                # 累积内容(排除提示符)
                current_content.append(line)

        # 保存最后一个段落
        if current_section and current_content:
            summary[current_section] = '\n'.join(current_content).strip()

        # 如果解析失败,使用简单拼接作为降级方案
        if not summary["trade_logic"] and trade_logics:
            # 提取前3条,并简化格式
            logics = trade_logics[:3]
            summary["trade_logic"] = "【核心观点】\n" + "\n".join(f"• {logic[:100]}..." if len(logic) > 100 else f"• {logic}" for logic in logics)

        if not summary["related_data"] and related_datas:
            # 提取前3条,突出数字
            datas = related_datas[:3]
            summary["related_data"] = "【关键数据】\n" + "\n".join(f"• {data[:100]}..." if len(data) > 100 else f"• {data}" for data in datas)

        if not summary["risk_factor"] and risk_factors:
            # 提取前2条主要风险
            risks = risk_factors[:2]
            summary["risk_factor"] = "【主要风险】\n" + "\n".join(f"• {risk[:80]}..." if len(risk) > 80 else f"• {risk}" for risk in risks)

        return summary

    except Exception as e:
        logger.error(f"AI汇总失败: {e}")
        import traceback
        traceback.print_exc()
        # 降级方案:结构化拼接前3条
        result = {}

        if trade_logics:
            logics = trade_logics[:3]
            result["trade_logic"] = "【核心观点】\n" + "\n".join(f"• {logic[:100]}..." if len(logic) > 100 else f"• {logic}" for logic in logics)
        else:
            result["trade_logic"] = "暂无数据"

        if related_datas:
            datas = related_datas[:3]
            result["related_data"] = "【关键数据】\n" + "\n".join(f"• {data[:100]}..." if len(data) > 100 else f"• {data}" for data in datas)
        else:
            result["related_data"] = "暂无数据"

        if risk_factors:
            risks = risk_factors[:2]
            result["risk_factor"] = "【主要风险】\n" + "\n".join(f"• {risk[:80]}..." if len(risk) > 80 else f"• {risk}" for risk in risks)
        else:
            result["risk_factor"] = "暂无数据"

        return result
