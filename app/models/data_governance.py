"""
数据治理模型
用于记录数据源、采集日志、质量指标
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, JSON
from sqlalchemy.sql import func
from app.models.base import Base


class DataSource(Base):
    """数据源表 - 记录所有数据来源"""
    __tablename__ = "data_sources"

    id = Column(Integer, primary_key=True, index=True)
    source_name = Column(String(100), unique=True, nullable=False, comment="数据源名称")
    source_type = Column(String(50), nullable=False, comment="类型: api/spider/file/service")
    category = Column(String(50), comment="分类: 基本面/技术面/资金面/消息面")

    # 来源详情
    provider = Column(String(100), comment="提供方: akshare/智汇期讯/百度OCR等")
    url = Column(String(500), comment="URL或API地址")
    method = Column(String(20), comment="获取方式: GET/POST/crawl/local")

    # 更新配置
    update_frequency = Column(String(50), comment="更新频率: realtime/hourly/daily/weekly")
    cron_expression = Column(String(100), comment="Cron表达式")

    # 数据说明
    description = Column(Text, comment="数据源说明")
    data_fields = Column(JSON, comment="数据字段列表")
    dependencies = Column(JSON, comment="依赖的其他数据源")

    # 状态
    is_active = Column(Boolean, default=True, comment="是否启用")
    health_status = Column(String(20), default="unknown", comment="健康状态: healthy/warning/critical/unknown")

    # 元数据
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 最后采集信息
    last_collect_time = Column(DateTime, comment="最后采集时间")
    last_collect_status = Column(String(20), comment="最后采集状态: success/failed")
    last_record_count = Column(Integer, comment="最后采集记录数")


class DataCollectionLog(Base):
    """数据采集日志表 - 记录每次数据采集"""
    __tablename__ = "data_collection_logs"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, nullable=False, comment="数据源ID")
    source_name = Column(String(100), nullable=False, comment="数据源名称")

    # 采集信息
    collect_time = Column(DateTime, nullable=False, comment="采集时间")
    status = Column(String(20), nullable=False, comment="状态: success/failed/partial")
    duration_seconds = Column(Integer, comment="耗时（秒）")

    # 数据统计
    records_collected = Column(Integer, default=0, comment="采集记录数")
    records_inserted = Column(Integer, default=0, comment="插入记录数")
    records_updated = Column(Integer, default=0, comment="更新记录数")
    records_failed = Column(Integer, default=0, comment="失败记录数")

    # 质量指标
    data_quality_score = Column(Float, comment="数据质量评分 0-100")
    missing_rate = Column(Float, comment="缺失率 %")
    duplicate_rate = Column(Float, comment="重复率 %")

    # 错误信息
    error_message = Column(Text, comment="错误信息")
    error_traceback = Column(Text, comment="错误堆栈")

    # 其他元数据
    extra_metadata = Column(JSON, comment="其他元数据")
    created_at = Column(DateTime, server_default=func.now())


class DataQualityMetric(Base):
    """数据质量指标表 - 记录数据质量"""
    __tablename__ = "data_quality_metrics"

    id = Column(Integer, primary_key=True, index=True)
    source_name = Column(String(100), nullable=False, comment="数据源名称")
    table_name = Column(String(100), comment="数据表名")

    # 时间
    metric_date = Column(DateTime, nullable=False, comment="指标日期")

    # 完整性指标
    total_records = Column(Integer, comment="总记录数")
    null_count = Column(Integer, comment="空值数量")
    null_rate = Column(Float, comment="空值率 %")

    # 准确性指标
    outlier_count = Column(Integer, comment="异常值数量")
    outlier_rate = Column(Float, comment="异常值率 %")

    # 一致性指标
    duplicate_count = Column(Integer, comment="重复记录数")
    duplicate_rate = Column(Float, comment="重复率 %")

    # 时效性指标
    latest_record_time = Column(DateTime, comment="最新记录时间")
    freshness_hours = Column(Float, comment="数据新鲜度（小时）")

    # 综合评分
    quality_score = Column(Float, comment="质量评分 0-100")

    created_at = Column(DateTime, server_default=func.now())
