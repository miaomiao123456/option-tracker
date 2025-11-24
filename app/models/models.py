"""数据库模型定义"""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text, Enum as SQLEnum, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
import enum

Base = declarative_base()


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

    id = Column(BigInteger, primary_key=True, autoincrement=True)
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

    id = Column(BigInteger, primary_key=True, autoincrement=True)
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

    id = Column(BigInteger, primary_key=True, autoincrement=True)
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

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    comm_code = Column(String(20), nullable=False, index=True)
    iv_rank = Column(Float, comment="隐含波动率排位")
    term_structure = Column(String(20), comment="期限结构: contango/back")
    pcr_ratio = Column(Float, comment="看跌看涨比率")
    record_time = Column(DateTime, nullable=False)

    created_at = Column(DateTime, default=func.now())


class DailyBlueprint(Base):
    """交易可查-日度交易蓝图"""
    __tablename__ = "daily_blueprints"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    image_url = Column(String(500), comment="图片URL")
    local_path = Column(String(500), comment="本地路径")
    parsed_strategies = Column(Text, comment="解析的策略(JSON格式)")
    record_date = Column(Date, nullable=False, index=True)

    created_at = Column(DateTime, default=func.now())
