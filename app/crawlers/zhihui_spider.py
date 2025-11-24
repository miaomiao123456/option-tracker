"""
智汇期讯爬虫 - hzzhqx.com
功能：
1. 多空全景模块 - 获取所有品种的主流观点及占比
2. 研报淘金模块 - 获取机构观点、交易逻辑、相关数据、风险因素
"""
import asyncio
import logging
from datetime import datetime, date
from typing import Optional, List, Dict
import httpx
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FundamentalView:
    """基本面观点数据结构"""
    variety_code: str
    variety_name: str
    bull_ratio: float  # 看多占比
    bear_ratio: float  # 看空占比
    neutral_ratio: float  # 中性占比
    main_sentiment: str  # 主流观点: bull/bear/neutral
    reasons: List[str]  # 支撑理由


@dataclass
class ResearchReport:
    """研报数据结构"""
    variety_code: str
    variety_name: str
    institution: str  # 机构名称
    viewpoint: str  # 观点
    logic: str  # 交易逻辑
    data_support: str  # 相关数据
    risk_factors: str  # 风险因素
    publish_date: date


class ZhihuiQixunSpider:
    """智汇期讯爬虫"""

    def __init__(self):
        self.base_url = "https://hzzhqx.com"
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Referer": "https://hzzhqx.com/",
                "Accept": "application/json, text/plain, */*"
            },
            timeout=30.0
        )

    async def fetch_full_view(self) -> List[Dict]:
        """
        获取多空全景数据
        URL: https://hzzhqx.com/report/fullView
        """
        try:
            logger.info("开始获取多空全景数据...")

            # 尝试不同的API端点
            endpoints = [
                "/api/report/fullView",
                "/api/v1/report/fullView",
                "/report/fullView/data"
            ]

            for endpoint in endpoints:
                try:
                    url = f"{self.base_url}{endpoint}"
                    response = await self.client.get(url)

                    if response.status_code == 200:
                        data = response.json()
                        logger.info(f"成功从 {endpoint} 获取数据")
                        return self._parse_full_view(data)
                except Exception as e:
                    logger.debug(f"端点 {endpoint} 请求失败: {e}")
                    continue

            # 如果API请求都失败，尝试直接请求页面并解析
            logger.warning("API请求失败，尝试解析页面...")
            return await self._scrape_full_view_page()

        except Exception as e:
            logger.error(f"获取多空全景数据失败: {e}")
            return []

    def _parse_full_view(self, data: Dict) -> List[Dict]:
        """解析多空全景API返回数据"""
        results = []

        if isinstance(data, dict) and 'data' in data:
            items = data.get('data', [])
        elif isinstance(data, list):
            items = data
        else:
            items = []

        for item in items:
            try:
                result = {
                    "variety_code": item.get("code", ""),
                    "variety_name": item.get("name", ""),
                    "bull_ratio": float(item.get("bullRatio", 0) or 0),
                    "bear_ratio": float(item.get("bearRatio", 0) or 0),
                    "neutral_ratio": float(item.get("neutralRatio", 0) or 0),
                    "main_sentiment": self._determine_sentiment(item),
                    "sources": item.get("sources", [])
                }
                results.append(result)
            except Exception as e:
                logger.debug(f"解析单条数据失败: {e}")
                continue

        return results

    def _determine_sentiment(self, item: Dict) -> str:
        """根据占比确定主流情绪"""
        bull = float(item.get("bullRatio", 0) or 0)
        bear = float(item.get("bearRatio", 0) or 0)
        neutral = float(item.get("neutralRatio", 0) or 0)

        if bull > bear and bull > neutral:
            return "bull"
        elif bear > bull and bear > neutral:
            return "bear"
        else:
            return "neutral"

    async def _scrape_full_view_page(self) -> List[Dict]:
        """通过页面抓取多空全景数据(备用方案)"""
        # 这里可以使用Playwright进行页面抓取
        logger.warning("页面抓取功能待实现")
        return []

    async def fetch_research_points(self, variety_code: Optional[str] = None) -> List[Dict]:
        """
        获取研报淘金数据
        URL: https://hzzhqx.com/report/points
        """
        try:
            logger.info(f"开始获取研报淘金数据... (品种: {variety_code or '全部'})")

            endpoints = [
                "/api/report/points",
                "/api/v1/report/points"
            ]

            params = {}
            if variety_code:
                params["code"] = variety_code

            for endpoint in endpoints:
                try:
                    url = f"{self.base_url}{endpoint}"
                    response = await self.client.get(url, params=params)

                    if response.status_code == 200:
                        data = response.json()
                        return self._parse_research_points(data)
                except Exception as e:
                    logger.debug(f"端点 {endpoint} 请求失败: {e}")
                    continue

            return []

        except Exception as e:
            logger.error(f"获取研报淘金数据失败: {e}")
            return []

    def _parse_research_points(self, data: Dict) -> List[Dict]:
        """解析研报淘金数据"""
        results = []

        if isinstance(data, dict) and 'data' in data:
            items = data.get('data', [])
        elif isinstance(data, list):
            items = data
        else:
            items = []

        for item in items:
            try:
                result = {
                    "variety_code": item.get("code", ""),
                    "variety_name": item.get("name", ""),
                    "institution": item.get("institution", ""),
                    "viewpoint": item.get("viewpoint", ""),
                    "logic": item.get("logic", ""),
                    "data_support": item.get("data", ""),
                    "risk_factors": item.get("risk", ""),
                    "publish_date": item.get("publishDate", "")
                }
                results.append(result)
            except Exception as e:
                logger.debug(f"解析研报数据失败: {e}")
                continue

        return results

    async def aggregate_viewpoints(self, variety_code: str) -> Dict:
        """
        聚合同一品种的所有研报观点
        按观点分类汇总交易逻辑、数据支撑、风险因素
        """
        reports = await self.fetch_research_points(variety_code)

        if not reports:
            return {}

        # 按观点分组
        grouped = {"bull": [], "bear": [], "neutral": []}

        for report in reports:
            viewpoint = report.get("viewpoint", "").lower()
            if "多" in viewpoint or "涨" in viewpoint or "bull" in viewpoint:
                grouped["bull"].append(report)
            elif "空" in viewpoint or "跌" in viewpoint or "bear" in viewpoint:
                grouped["bear"].append(report)
            else:
                grouped["neutral"].append(report)

        # 汇总每组的数据
        aggregated = {}
        for sentiment, reports_list in grouped.items():
            if reports_list:
                aggregated[sentiment] = {
                    "count": len(reports_list),
                    "institutions": list(set(r.get("institution", "") for r in reports_list)),
                    "logics": [r.get("logic", "") for r in reports_list if r.get("logic")],
                    "data_supports": [r.get("data_support", "") for r in reports_list if r.get("data_support")],
                    "risk_factors": [r.get("risk_factors", "") for r in reports_list if r.get("risk_factors")]
                }

        return aggregated

    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()


async def main():
    """测试函数"""
    spider = ZhihuiQixunSpider()

    try:
        # 获取多空全景
        full_view = await spider.fetch_full_view()
        logger.info(f"获取到 {len(full_view)} 条多空全景数据")
        if full_view:
            logger.info(f"示例: {full_view[:2]}")

        # 获取研报淘金
        reports = await spider.fetch_research_points()
        logger.info(f"获取到 {len(reports)} 条研报数据")

    finally:
        await spider.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
