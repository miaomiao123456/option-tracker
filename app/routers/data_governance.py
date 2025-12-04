"""
数据治理 API
提供数据源管理、采集日志、质量指标查询
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from app.models.database import get_db
from app.models.data_governance import DataSource, DataCollectionLog, DataQualityMetric
from datetime import datetime, timedelta
from typing import List, Optional

router = APIRouter()  # 移除这里的prefix，在main.py中统一设置


@router.get("/dashboard/overview")
async def get_dashboard_overview(db: Session = Depends(get_db)):
    """
    数据看板总览
    返回所有数据源的概况
    """
    # 统计数据源
    total_sources = db.query(DataSource).count()
    active_sources = db.query(DataSource).filter_by(is_active=True).count()

    # 按类型统计
    sources_by_type = db.query(
        DataSource.source_type,
        func.count(DataSource.id).label('count')
    ).group_by(DataSource.source_type).all()

    # 按分类统计
    sources_by_category = db.query(
        DataSource.category,
        func.count(DataSource.id).label('count')
    ).group_by(DataSource.category).all()

    # 健康状态统计
    health_stats = db.query(
        DataSource.health_status,
        func.count(DataSource.id).label('count')
    ).group_by(DataSource.health_status).all()

    # 最近24小时采集统计
    since = datetime.now() - timedelta(hours=24)
    recent_logs = db.query(
        DataCollectionLog.status,
        func.count(DataCollectionLog.id).label('count')
    ).filter(
        DataCollectionLog.collect_time >= since
    ).group_by(DataCollectionLog.status).all()

    success_count = next((l.count for l in recent_logs if l.status == 'success'), 0)
    failed_count = next((l.count for l in recent_logs if l.status == 'failed'), 0)
    total_logs = sum(l.count for l in recent_logs)

    return {
        "summary": {
            "total_sources": total_sources,
            "active_sources": active_sources,
            "inactive_sources": total_sources - active_sources
        },
        "by_type": {t.source_type: t.count for t in sources_by_type},
        "by_category": {c.category: c.count for c in sources_by_category},
        "health_status": {h.health_status: h.count for h in health_stats},
        "recent_collection_24h": {
            "total": total_logs,
            "success": success_count,
            "failed": failed_count,
            "success_rate": round(success_count / total_logs * 100, 2) if total_logs > 0 else 0
        }
    }


@router.get("/sources")
async def list_data_sources(
    source_type: Optional[str] = None,
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    获取数据源列表
    可按类型、分类、状态筛选
    """
    query = db.query(DataSource)

    if source_type:
        query = query.filter(DataSource.source_type == source_type)
    if category:
        query = query.filter(DataSource.category == category)
    if is_active is not None:
        query = query.filter(DataSource.is_active == is_active)

    sources = query.order_by(DataSource.source_name).all()

    # 计算数据新鲜度
    now = datetime.now()
    result = []

    for source in sources:
        freshness_hours = None
        freshness_status = "unknown"

        if source.last_collect_time:
            delta = now - source.last_collect_time
            freshness_hours = round(delta.total_seconds() / 3600, 1)

            # 根据更新频率判断新鲜度
            if source.update_frequency == 'realtime' and freshness_hours > 1:
                freshness_status = "stale"
            elif source.update_frequency == 'hourly' and freshness_hours > 3:
                freshness_status = "stale"
            elif source.update_frequency == 'daily' and freshness_hours > 30:
                freshness_status = "stale"
            elif source.update_frequency == 'weekly' and freshness_hours > 200:
                freshness_status = "stale"
            else:
                freshness_status = "fresh"

        result.append({
            "id": source.id,
            "source_name": source.source_name,
            "source_type": source.source_type,
            "category": source.category,
            "provider": source.provider,
            "url": source.url,
            "update_frequency": source.update_frequency,
            "is_active": source.is_active,
            "health_status": source.health_status,
            "last_collect_time": source.last_collect_time,
            "last_collect_status": source.last_collect_status,
            "last_record_count": source.last_record_count,
            "freshness_hours": freshness_hours,
            "freshness_status": freshness_status,
            "description": source.description
        })

    return {"sources": result}


@router.get("/sources/{source_id}")
async def get_source_detail(source_id: int, db: Session = Depends(get_db)):
    """获取数据源详情"""
    source = db.query(DataSource).filter_by(id=source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="数据源不存在")

    # 获取最近10次采集日志
    recent_logs = db.query(DataCollectionLog).filter_by(
        source_id=source_id
    ).order_by(desc(DataCollectionLog.collect_time)).limit(10).all()

    # 统计最近30天成功率
    since = datetime.now() - timedelta(days=30)
    logs_30d = db.query(
        DataCollectionLog.status,
        func.count(DataCollectionLog.id).label('count')
    ).filter(
        DataCollectionLog.source_id == source_id,
        DataCollectionLog.collect_time >= since
    ).group_by(DataCollectionLog.status).all()

    success_count = next((l.count for l in logs_30d if l.status == 'success'), 0)
    total_count = sum(l.count for l in logs_30d)

    return {
        "source": {
            "id": source.id,
            "source_name": source.source_name,
            "source_type": source.source_type,
            "category": source.category,
            "provider": source.provider,
            "url": source.url,
            "description": source.description,
            "update_frequency": source.update_frequency,
            "cron_expression": source.cron_expression,
            "data_fields": source.data_fields,
            "dependencies": source.dependencies,
            "is_active": source.is_active,
            "health_status": source.health_status,
            "created_at": source.created_at,
            "updated_at": source.updated_at
        },
        "statistics": {
            "success_rate_30d": round(success_count / total_count * 100, 2) if total_count > 0 else 0,
            "total_collections_30d": total_count,
            "success_count_30d": success_count
        },
        "recent_logs": [
            {
                "id": log.id,
                "collect_time": log.collect_time,
                "status": log.status,
                "duration_seconds": log.duration_seconds,
                "records_collected": log.records_collected,
                "quality_score": log.data_quality_score,
                "error_message": log.error_message
            }
            for log in recent_logs
        ]
    }


@router.get("/collection-logs")
async def get_collection_logs(
    source_name: Optional[str] = None,
    status: Optional[str] = None,
    hours: int = Query(24, ge=1, le=720),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    获取数据采集日志
    可按数据源、状态、时间范围筛选
    """
    since = datetime.now() - timedelta(hours=hours)
    query = db.query(DataCollectionLog).filter(
        DataCollectionLog.collect_time >= since
    )

    if source_name:
        query = query.filter(DataCollectionLog.source_name == source_name)
    if status:
        query = query.filter(DataCollectionLog.status == status)

    logs = query.order_by(desc(DataCollectionLog.collect_time)).limit(limit).all()

    return {
        "logs": [
            {
                "id": log.id,
                "source_name": log.source_name,
                "collect_time": log.collect_time,
                "status": log.status,
                "duration_seconds": log.duration_seconds,
                "records_collected": log.records_collected,
                "records_inserted": log.records_inserted,
                "quality_score": log.data_quality_score,
                "missing_rate": log.missing_rate,
                "error_message": log.error_message
            }
            for log in logs
        ]
    }


@router.get("/quality/trends")
async def get_quality_trends(
    source_name: str,
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """
    获取数据质量趋势
    返回最近N天的质量指标变化
    """
    since = datetime.now() - timedelta(days=days)

    metrics = db.query(DataQualityMetric).filter(
        DataQualityMetric.source_name == source_name,
        DataQualityMetric.metric_date >= since
    ).order_by(DataQualityMetric.metric_date).all()

    return {
        "source_name": source_name,
        "period_days": days,
        "trends": [
            {
                "date": m.metric_date,
                "quality_score": m.quality_score,
                "null_rate": m.null_rate,
                "duplicate_rate": m.duplicate_rate,
                "freshness_hours": m.freshness_hours,
                "total_records": m.total_records
            }
            for m in metrics
        ]
    }


@router.get("/dependencies/graph")
async def get_dependency_graph(db: Session = Depends(get_db)):
    """
    获取数据源依赖关系图
    用于可视化数据流向
    """
    sources = db.query(DataSource).all()

    nodes = []
    edges = []

    for source in sources:
        # 节点
        nodes.append({
            "id": source.id,
            "name": source.source_name,
            "type": source.source_type,
            "category": source.category,
            "health": source.health_status
        })

        # 边（依赖关系）
        if source.dependencies:
            for dep_name in source.dependencies:
                dep_source = db.query(DataSource).filter_by(source_name=dep_name).first()
                if dep_source:
                    edges.append({
                        "from": dep_source.id,
                        "to": source.id,
                        "label": "依赖"
                    })

    return {
        "nodes": nodes,
        "edges": edges
    }


@router.post("/sources/{source_id}/toggle")
async def toggle_source_status(source_id: int, db: Session = Depends(get_db)):
    """启用/禁用数据源"""
    source = db.query(DataSource).filter_by(id=source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="数据源不存在")

    source.is_active = not source.is_active
    db.commit()

    return {
        "source_id": source_id,
        "source_name": source.source_name,
        "is_active": source.is_active
    }
