"""
V2分析系统API路由
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import pandas as pd
from pathlib import Path

router = APIRouter()

# 数据文件路径
DATA_DIR = Path(__file__).parent.parent.parent.parent


@router.get("/overview")
async def get_analysis_overview():
    """
    获取V2分析总览数据
    返回所有61个品种的5维度分析结果
    """
    try:
        csv_path = DATA_DIR / "期权分析_总览_V2.csv"

        if not csv_path.exists():
            raise HTTPException(status_code=404, detail="分析数据未找到，请先运行分析系统")

        df = pd.read_csv(csv_path)

        # 转换为字典列表
        data = df.to_dict('records')

        # 统计信息
        stats = {
            "total": len(df),
            "long": len(df[df['综合方向'] == '多头']),
            "short": len(df[df['综合方向'] == '空头']),
            "neutral": len(df[df['综合方向'] == '中性'])
        }

        return {
            "success": True,
            "data": data,
            "stats": stats
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取数据失败: {str(e)}")


@router.get("/top5/{direction}")
async def get_top5(direction: str):
    """
    获取Top5品种
    direction: 'long' 或 'short'
    """
    try:
        if direction == 'long':
            csv_path = DATA_DIR / "期权分析_多头Top5_V2.csv"
        elif direction == 'short':
            csv_path = DATA_DIR / "期权分析_空头Top5_V2.csv"
        else:
            raise HTTPException(status_code=400, detail="direction必须是'long'或'short'")

        if not csv_path.exists():
            raise HTTPException(status_code=404, detail="Top5数据未找到")

        df = pd.read_csv(csv_path)
        data = df.to_dict('records')

        return {
            "success": True,
            "data": data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取数据失败: {str(e)}")


@router.get("/variety/{variety_id}/signals")
async def get_variety_signals(variety_id: str):
    """
    获取单个品种的分析信号详情
    """
    try:
        csv_path = DATA_DIR / f"品种详情_{variety_id}_分析信号_V2.csv"

        if not csv_path.exists():
            raise HTTPException(status_code=404, detail=f"品种{variety_id}的分析信号未找到")

        df = pd.read_csv(csv_path)
        data = df.to_dict('records')

        return {
            "success": True,
            "variety": variety_id,
            "signals": data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取数据失败: {str(e)}")


@router.get("/variety/{variety_id}/term-structure")
async def get_variety_term_structure(variety_id: str):
    """
    获取单个品种的期限结构数据
    """
    try:
        csv_path = DATA_DIR / f"品种详情_{variety_id}_期限结构.csv"

        if not csv_path.exists():
            raise HTTPException(status_code=404, detail=f"品种{variety_id}的期限结构未找到")

        df = pd.read_csv(csv_path)
        data = df.to_dict('records')

        return {
            "success": True,
            "variety": variety_id,
            "term_structure": data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取数据失败: {str(e)}")


@router.post("/refresh")
async def refresh_analysis():
    """
    重新运行分析系统
    """
    try:
        import subprocess

        script_path = DATA_DIR / "option_analysis_system_v2.py"

        if not script_path.exists():
            raise HTTPException(status_code=404, detail="分析脚本未找到")

        # 异步运行分析脚本
        result = subprocess.run(
            ["python3", str(script_path)],
            cwd=str(DATA_DIR),
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"分析失败: {result.stderr}")

        return {
            "success": True,
            "message": "分析完成",
            "output": result.stdout
        }

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="分析超时（>5分钟）")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"运行失败: {str(e)}")
