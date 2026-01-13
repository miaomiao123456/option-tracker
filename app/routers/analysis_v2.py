"""
V2分析系统API路由
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import pandas as pd
from pathlib import Path
import glob

from app.models.database import get_db
from app.models.models import Commodity

router = APIRouter()

# 数据文件路径
# 修复: __file__ 在 app/routers/analysis_v2.py
# parent = app/routers -> parent.parent = app -> parent.parent.parent = option_tracker (项目根目录)
DATA_DIR = Path(__file__).parent.parent.parent


@router.get("/overview")
async def get_analysis_overview(db: Session = Depends(get_db)):
    """
    获取V2分析总览数据
    修改:基于commodities主品种列表返回所有品种,无数据显示null
    返回所有57个品种的5维度分析结果
    """
    try:
        # 获取所有品种列表
        all_commodities = db.query(Commodity).all()
        commodity_dict = {c.code: c.name for c in all_commodities}

        csv_path = DATA_DIR / "期权分析_总览_V2.csv"

        if not csv_path.exists():
            # CSV不存在时,返回所有品种的空结构
            data = []
            for code, name in commodity_dict.items():
                data.append({
                    "品种": code,
                    "综合方向": None,
                    "综合星级": None,
                    "净得分": None,
                    "研报分析_方向": None,
                    "研报分析_星级": None,
                    "虚实比PCR_方向": None,
                    "虚实比PCR_星级": None,
                    "期限结构_方向": None,
                    "期限结构_星级": None,
                    "波动率背离_方向": None,
                    "波动率背离_星级": None,
                    "资金面_方向": None,
                    "资金面_星级": None
                })

            return {
                "success": True,
                "data": data,
                "stats": {
                    "total": len(commodity_dict),
                    "long": 0,
                    "short": 0,
                    "neutral": 0
                }
            }

        df = pd.read_csv(csv_path)

        # 标准化品种代码函数
        def normalize_code(code: str) -> str:
            """将CSV中的品种代码标准化为commodities表格式"""
            # 移除_o后缀
            code = code.replace('_o', '').replace('_O', '')
            # 转大写
            return code.upper()

        # 构建品种代码到数据的映射
        existing_data = {}
        for _, row in df.iterrows():
            original_code = row['品种']
            normalized_code = normalize_code(original_code)
            # 保留原始品种代码在数据中，但用标准化代码作为key
            row_dict = row.to_dict()
            existing_data[normalized_code] = row_dict

        # 基于所有品种构建返回数据
        data = []
        for code, name in commodity_dict.items():
            if code in existing_data:
                # 有数据的品种
                row_dict = existing_data[code]
                # 将品种代码替换为标准化代码
                row_dict['品种'] = code
                data.append(row_dict)
            else:
                # 无数据的品种 - 返回null结构
                data.append({
                    "品种": code,
                    "综合方向": None,
                    "综合星级": None,
                    "净得分": None,
                    "研报分析_方向": None,
                    "研报分析_星级": None,
                    "虚实比PCR_方向": None,
                    "虚实比PCR_星级": None,
                    "期限结构_方向": None,
                    "期限结构_星级": None,
                    "波动率背离_方向": None,
                    "波动率背离_星级": None,
                    "资金面_方向": None,
                    "资金面_星级": None
                })

        # 统计信息 - 只统计有数据的品种
        long_count = sum(1 for d in data if d.get('综合方向') == '多头')
        short_count = sum(1 for d in data if d.get('综合方向') == '空头')
        neutral_count = sum(1 for d in data if d.get('综合方向') == '中性')

        stats = {
            "total": len(data),
            "long": long_count,
            "short": short_count,
            "neutral": neutral_count
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
        # 先尝试原样查找
        csv_path = DATA_DIR / f"品种详情_{variety_id}_分析信号_V2.csv"

        # 如果不存在,尝试查找类似的文件
        if not csv_path.exists():
            # 列出所有可能的文件
            pattern = str(DATA_DIR / f"品种详情_*{variety_id}*_分析信号_V2.csv")
            matches = glob.glob(pattern)

            if matches:
                csv_path = Path(matches[0])
            else:
                # 返回空数据而不是404
                return {
                    "success": True,
                    "variety": variety_id,
                    "signals": [],
                    "message": f"品种{variety_id}的分析信号数据暂无"
                }

        df = pd.read_csv(csv_path)
        data = df.to_dict('records')

        return {
            "success": True,
            "variety": variety_id,
            "signals": data
        }

    except Exception as e:
        # 返回错误但不抛出异常
        return {
            "success": False,
            "variety": variety_id,
            "signals": [],
            "error": str(e)
        }


@router.get("/variety/{variety_id}/term-structure")
async def get_variety_term_structure(variety_id: str):
    """
    获取单个品种的期限结构数据
    """
    try:
        # 先尝试原样查找
        csv_path = DATA_DIR / f"品种详情_{variety_id}_期限结构.csv"

        # 如果不存在,尝试查找类似的文件
        if not csv_path.exists():
            pattern = str(DATA_DIR / f"品种详情_*{variety_id}*_期限结构.csv")
            matches = glob.glob(pattern)

            if matches:
                csv_path = Path(matches[0])
            else:
                # 返回空数据而不是404
                return {
                    "success": True,
                    "variety": variety_id,
                    "term_structure": [],
                    "message": f"品种{variety_id}的期限结构数据暂无"
                }

        df = pd.read_csv(csv_path)
        data = df.to_dict('records')

        return {
            "success": True,
            "variety": variety_id,
            "term_structure": data
        }

    except Exception as e:
        # 返回错误但不抛出异常
        return {
            "success": False,
            "variety": variety_id,
            "term_structure": [],
            "error": str(e)
        }


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
