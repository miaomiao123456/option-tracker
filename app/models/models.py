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
    impact_analysis = Column(Text, comment="影响分析")
    price_pressure = Column(String(20), comment="价格压力: 上涨/下跌/中性")

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
