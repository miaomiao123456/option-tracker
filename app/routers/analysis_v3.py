"""
V3分析API路由
提供V3优化后的分析数据接口
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime
import sys
import os
import pandas as pd

# 添加option_tracker目录到路径
option_tracker_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
parent_dir = os.path.dirname(option_tracker_dir)  # 用于访问生成的CSV文件
sys.path.insert(0, option_tracker_dir)

router = APIRouter(prefix="/api/v3/analysis", tags=["V3分析"])


@router.get("/overview")
async def get_overview():
    """
    获取V3分析总览
    返回所有品种的综合分析数据
    """
    try:
        # 尝试直接读取已生成的CSV文件(更快)
        csv_path = os.path.join(parent_dir, '期权分析_总览_V2.csv')
        long_top5_path = os.path.join(parent_dir, '期权分析_多头Top5_V2.csv')
        short_top5_path = os.path.join(parent_dir, '期权分析_空头Top5_V2.csv')

        if os.path.exists(csv_path):
            overview_df = pd.read_csv(csv_path)
            long_top5_df = pd.read_csv(long_top5_path) if os.path.exists(long_top5_path) else pd.DataFrame()
            short_top5_df = pd.read_csv(short_top5_path) if os.path.exists(short_top5_path) else pd.DataFrame()

            # 检查文件是否新鲜(1小时内)
            file_mtime = os.path.getmtime(csv_path)
            file_age_hours = (datetime.now().timestamp() - file_mtime) / 3600

            data_source = "cached" if file_age_hours < 1 else "file"

            return {
                "status": "success",
                "data": {
                    "overview": overview_df.to_dict('records'),
                    "long_top5": long_top5_df.to_dict('records') if not long_top5_df.empty else [],
                    "short_top5": short_top5_df.to_dict('records') if not short_top5_df.empty else [],
                    "stats": {
                        "total": len(overview_df),
                        "long": len(overview_df[overview_df['综合方向'] == '多头']),
                        "short": len(overview_df[overview_df['综合方向'] == '空头']),
                        "neutral": len(overview_df[overview_df['综合方向'] == '中性'])
                    },
                    "update_time": datetime.fromtimestamp(file_mtime).isoformat(),
                    "data_source": data_source,
                    "file_age_hours": round(file_age_hours, 2)
                }
            }

        # 如果文件不存在,运行V3分析
        else:
            return await refresh_analysis()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加载分析数据失败: {str(e)}")


@router.post("/refresh")
async def refresh_analysis():
    """
    强制刷新分析数据
    运行V3分析系统生成最新数据
    """
    try:
        from option_analysis_system_v3 import OptionAnalysisSystemV3

        # 使用缓存加速
        analyzer = OptionAnalysisSystemV3(use_cache=True)
        overview_df, top5_results = analyzer.run_full_analysis()

        return {
            "status": "success",
            "data": {
                "overview": overview_df.to_dict('records'),
                "long_top5": top5_results['多头Top5'].to_dict('records'),
                "short_top5": top5_results['空头Top5'].to_dict('records'),
                "stats": {
                    "total": len(overview_df),
                    "long": len(overview_df[overview_df['综合方向'] == '多头']),
                    "short": len(overview_df[overview_df['综合方向'] == '空头']),
                    "neutral": len(overview_df[overview_df['综合方向'] == '中性'])
                },
                "update_time": datetime.now().isoformat(),
                "data_source": "real-time"
            },
            "message": "分析数据已刷新"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刷新分析数据失败: {str(e)}")


@router.get("/variety/{variety_code}")
async def get_variety_detail(variety_code: str):
    """
    获取单个品种的详细分析
    """
    try:
        signal_file = os.path.join(parent_dir, f'品种详情_{variety_code}_分析信号_V2.csv')

        if os.path.exists(signal_file):
            signals_df = pd.read_csv(signal_file)

            return {
                "status": "success",
                "data": {
                    "variety": variety_code,
                    "signals": signals_df.to_dict('records'),
                    "update_time": datetime.fromtimestamp(os.path.getmtime(signal_file)).isoformat()
                }
            }
        else:
            raise HTTPException(status_code=404, detail=f"品种 {variety_code} 的详情数据不存在")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加载品种详情失败: {str(e)}")


@router.get("/config")
async def get_config():
    """
    获取当前配置参数
    """
    try:
        import config

        return {
            "status": "success",
            "data": {
                "research_analysis": config.RESEARCH_ANALYSIS,
                "pcr_analysis": config.PCR_ANALYSIS,
                "term_structure": config.TERM_STRUCTURE,
                "cache_settings": config.CACHE_SETTINGS,
                "parallel_processing": config.PARALLEL_PROCESSING
            }
        }

    except Exception as e:
        return {
            "status": "error",
            "message": "配置文件未找到,使用默认配置",
            "data": None
        }
