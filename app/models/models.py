"""数据库模型定义"""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text, Enum as SQLEnum, BigInteger
from sqlalchemy.sql import func
from datetime import datetime
import enum

# 导入共享的Base
from app.models.base import Base


class DirectionEnum(enum.Enum):
    """方向枚举"""
    LONG = "多"
    SHORT = "空"
    NEUTRAL = "中性"


class Commodity(Base):
    """品种基础表"""
    __tablename__ = "commodities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=False, comment="品种代码")
    name = Column(String(50), nullable=False, comment="品种名称")
    exchange = Column(String(20), comment="交易所")
    category = Column(String(20), comment="分类")


class MarketAnalysisSummary(Base):
    """四维评分总览表"""
    __tablename__ = "market_analysis_summary"

    id = Column(Integer, primary_key=True, autoincrement=True)
    comm_code = Column(String(20), nullable=False, index=True, comment="品种代码")
    date = Column(Date, nullable=False, index=True, comment="日期")

    # 四维评分 (-10 到 10)
    fundamental_score = Column(Integer, default=0, comment="基本面分数")
    capital_score = Column(Integer, default=0, comment="资金面分数")
    technical_score = Column(Integer, default=0, comment="技术面分数")
    message_score = Column(Integer, default=0, comment="消息面分数")

    # 综合结论
    total_direction = Column(SQLEnum(DirectionEnum), comment="综合方向")
    main_reason = Column(Text, comment="核心原因")

    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")


class FundamentalReport(Base):
    """基本面数据表"""
    __tablename__ = "fundamental_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    comm_code = Column(String(20), nullable=False, index=True)
    source = Column(String(50), comment="数据来源: hzzhqx/founderfu")
    report_type = Column(String(20), comment="报告类型: morning/night/deep")
    sentiment = Column(String(10), comment="情绪: bull/bear/neutral")
    content_summary = Column(Text, comment="内容摘要")
    publish_time = Column(DateTime, comment="发布时间")

    created_at = Column(DateTime, default=func.now())


class InstitutionalPosition(Base):
    """机构资金数据表"""
    __tablename__ = "institutional_positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    comm_code = Column(String(20), nullable=False, index=True)
    broker_name = Column(String(50), comment="席位名称")
    net_position = Column(Integer, comment="净持仓")
    position_change = Column(Integer, comment="增减仓变化")
    win_rate = Column(Float, comment="席位胜率")
    record_date = Column(Date, nullable=False, index=True)

    created_at = Column(DateTime, default=func.now())


class TechnicalIndicator(Base):
    """技术面数据表"""
    __tablename__ = "technical_indicators"

    id = Column(Integer, primary_key=True, autoincrement=True)
    comm_code = Column(String(20), nullable=False, index=True)
    iv_rank = Column(Float, comment="隐含波动率排位")
    term_structure = Column(String(20), comment="期限结构: contango/back")
    pcr_ratio = Column(Float, comment="看跌看涨比率")
    record_time = Column(DateTime, nullable=False)

    created_at = Column(DateTime, default=func.now())


class DailyBlueprint(Base):
    """交易可查-日度交易蓝图"""
    __tablename__ = "daily_blueprints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    image_url = Column(String(500), comment="图片URL")
    local_path = Column(String(500), comment="本地路径")
    parsed_strategies = Column(Text, comment="解析的策略(JSON格式)")
    record_date = Column(Date, nullable=False, index=True)

    created_at = Column(DateTime, default=func.now())


class OptionFlow(Base):
    """期权资金流向表 - Openvlab数据"""
    __tablename__ = "option_flows"

    id = Column(Integer, primary_key=True, autoincrement=True)
    comm_code = Column(String(20), nullable=False, index=True, comment="品种代码")
    contract_code = Column(String(100), comment="合约代码")
    net_flow = Column(Float, comment="净流入(万)")
    volume = Column(Float, comment="成交量变化(万)")
    change_ratio = Column(Float, comment="变化比例")
    record_time = Column(DateTime, nullable=False, index=True, comment="记录时间")

    created_at = Column(DateTime, default=func.now())


class ContractInfo(Base):
    """合约信息表 - 用于计算市值"""
    __tablename__ = "contract_infos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    comm_code = Column(String(20), unique=True, nullable=False, comment="品种代码")
    multiplier = Column(Integer, default=10, comment="合约乘数")
    latest_price = Column(Float, default=0, comment="最新价格")
    price_update_time = Column(DateTime, default=func.now(), onupdate=func.now())

    created_at = Column(DateTime, default=func.now())


class ResearchReport(Base):
    """研报淘金数据表 - 智汇期讯"""
    __tablename__ = "research_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(BigInteger, comment="研报ID")
    comm_code = Column(String(20), nullable=False, index=True, comment="品种代码")
    variety_name = Column(String(50), comment="品种名称")
    institution_id = Column(Integer, comment="机构ID")
    institution_name = Column(String(100), comment="机构名称")
    publish_date = Column(Date, nullable=False, index=True, comment="发布日期")
    view_port = Column(String(20), comment="观点: 看多/看空/中性")
    sentiment = Column(String(10), comment="情绪: bull/bear/neutral")
    trade_logic = Column(Text, comment="交易逻辑")
    related_data = Column(Text, comment="相关数据")
    risk_factor = Column(Text, comment="风险因素")
    report_link = Column(String(500), comment="PDF链接")

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class MarketFullView(Base):
    """多空全景数据表 - 智汇期讯"""
    __tablename__ = "market_full_view"

    id = Column(Integer, primary_key=True, autoincrement=True)
    comm_code = Column(String(20), nullable=False, index=True, comment="品种代码")
    variety_name = Column(String(50), comment="品种名称")
    record_date = Column(Date, nullable=False, index=True, comment="记录日期")
    excessive_num = Column(Integer, default=0, comment="看多数量")
    excessive_ratio = Column(Float, default=0, comment="看多占比")
    neutral_num = Column(Integer, default=0, comment="中性数量")
    neutral_ratio = Column(Float, default=0, comment="中性占比")
    empty_num = Column(Integer, default=0, comment="看空数量")
    empty_ratio = Column(Float, default=0, comment="看空占比")
    total_num = Column(Integer, default=0, comment="总数")
    more_port = Column(String(20), comment="主流观点")
    more_rate = Column(Float, default=0, comment="主流观点比例")
    main_sentiment = Column(String(10), comment="主流情绪: bull/bear/neutral")

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class WarehouseReceipt(Base):
    """仓单日报表 - 用于计算虚实比"""
    __tablename__ = "warehouse_receipts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    comm_code = Column(String(20), nullable=False, index=True, comment="品种代码,如AU")
    variety_name = Column(String(50), comment="品种名称,如沪金")
    record_date = Column(Date, nullable=False, index=True, comment="记录日期")

    # 仓单数据(库存)
    receipt_quantity = Column(Float, default=0, comment="仓单量/库存")
    receipt_change = Column(Float, default=0, comment="仓单变化")

    # 持仓数据
    main_contract = Column(String(20), comment="主力合约代码")
    open_interest = Column(Float, default=0, comment="期货主连持仓量(手)")
    open_interest_change = Column(Float, default=0, comment="持仓量变化(手)")

    # 合约信息
    contract_unit = Column(Float, default=0, comment="合约单位(千克/手)")

    # 虚实比计算
    virtual_quantity = Column(Float, default=0, comment="虚盘量 = 持仓量*合约单位/2")
    virtual_real_ratio = Column(Float, default=0, comment="虚实比 = 虚盘量/仓单量")

    # 影响分析
    squeeze_risk = Column(String(20), comment="逼仓风险: 高/中/低/无")
    impact_analysis = Column(Text, comment="风险提示")
    market_activity = Column(String(20), comment="市场活跃度: 极度活跃/活跃/平稳/平淡")

    # Phase 1 增强字段 - 历史位置指标
    percentile_30d = Column(Float, comment="30日百分位")
    percentile_90d = Column(Float, comment="90日百分位")
    mean_30d = Column(Float, comment="30日均值")
    std_30d = Column(Float, comment="30日标准差")
    zscore = Column(Float, comment="Z-score统计值")

    # Phase 1 增强字段 - 变化率指标
    change_rate_3d = Column(Float, comment="3日变化率")
    change_rate_7d = Column(Float, comment="7日变化率")
    acceleration = Column(Float, comment="加速度指标")

    # Phase 1 增强字段 - 信号标识
    signal_type = Column(String(50), comment="信号类型")
    signal_score = Column(Integer, comment="信号得分(0-100)")

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class TermStructureHistory(Base):
    """期限结构历史表 - Phase 3"""
    __tablename__ = "term_structure_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    comm_code = Column(String(20), nullable=False, index=True, comment="品种代码")
    variety_name = Column(String(50), comment="品种名称")
    record_date = Column(Date, nullable=False, index=True, comment="记录日期")

    # 结构类型
    structure_type = Column(String(20), comment="结构类型: Contango/Backwardation")
    market_structure = Column(String(20), comment="市场结构: 正向市场/反向市场")
    structure_desc = Column(Text, comment="结构描述")

    # 合约信息
    near_contract = Column(String(20), comment="近月合约代码")
    far_contract = Column(String(20), comment="远月合约代码")
    near_price = Column(Float, comment="近月合约价格")
    far_price = Column(Float, comment="远月合约价格")
    near_volume = Column(Integer, comment="近月成交量")
    near_oi = Column(Integer, comment="近月持仓量")

    # 完整合约列表 (JSON格式)
    contracts_json = Column(Text, comment="合约列表JSON")

    # 价差分析
    price_spread = Column(Float, comment="价差(远月-近月)")
    spread_pct = Column(Float, comment="价差百分比")
    roll_yield = Column(Float, comment="展期收益率")

    # Phase 3 增强字段 - 结构分析
    structure_strength = Column(Float, comment="结构强度(价差绝对值)")
    structure_days = Column(Integer, comment="当前结构持续天数")
    structure_score = Column(Float, comment="结构评分(0-100)")
    grade = Column(String(5), comment="结构等级: S/A/B/C")
    recommend = Column(Integer, default=0, comment="是否推荐: 1=推荐, 0=不推荐")

    # Phase 3 增强字段 - 历史位置
    spread_percentile_30d = Column(Float, comment="价差30日百分位")
    spread_percentile_90d = Column(Float, comment="价差90日百分位")
    spread_mean_30d = Column(Float, comment="价差30日均值")
    spread_std_30d = Column(Float, comment="价差30日标准差")

    # Phase 3 增强字段 - 变化率
    spread_change_3d = Column(Float, comment="价差3日变化率")
    spread_change_7d = Column(Float, comment="价差7日变化率")

    # 交易建议
    trade_suggestion = Column(String(20), comment="交易建议: 做多/做空/观望")

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
