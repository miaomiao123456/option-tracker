"""
智汇期讯爬虫 - 简化版 (使用HTTP API + authorization token)
功能：
1. 获取品种列表 - API: /api/public/variety/list
2. 获取多空全景数据 - API: /api/report/overallView
3. 获取研报淘金数据 - API: /api/report/viewPoint/listPage
"""
import requests
import logging
from datetime import datetime, date
from typing import Optional, List, Dict
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class ZhihuiQixunSpider:
    """智汇期讯爬虫 - 使用HTTP API"""

    def __init__(self, auth_token: str = None):
        from config.settings import get_settings
        settings = get_settings()

        self.base_url = "https://hzzhqx.com"
        # authorization token (从settings或环境变量中获取)
        self.auth_token = auth_token or getattr(settings, 'ZHIHUI_AUTH_TOKEN', '141b6b1d-9513-4fc1-96b2-6fce17e7c8e4')
        self.save_dir = Path(__file__).parent.parent.parent / "智汇期讯" / "data"
        self.save_dir.mkdir(parents=True, exist_ok=True)

        self.headers = {
            'Accept': 'application/json, text/plain, */*',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'zh-platform': 'WEB',
            'authorization': self.auth_token
        }

    def fetch_variety_list(self) -> List[Dict]:
        """
        获取品种列表
        API: https://hzzhqx.com/api/public/variety/list
        """
        try:
            logger.info("开始获取品种列表...")

            url = f"{self.base_url}/api/public/variety/list"
            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('result'):
                    # 扁平化品种列表
                    varieties = []
                    for sector in data['result']:
                        for variety in sector.get('varietyList', []):
                            varieties.append({
                                'variety_id': variety.get('varietyId'),
                                'variety_code': variety.get('varietyCode', '').upper(),
                                'variety_name': variety.get('varietyName'),
                                'sector_id': variety.get('sectorId'),
                                'sector_name': variety.get('sectorName'),
                                'pinyin': variety.get('pinyin'),
                                'first_pinyin': variety.get('firstPinyin')
                            })

                    logger.info(f"✅ 成功获取 {len(varieties)} 个品种")
                    return varieties
                else:
                    logger.error(f"API返回错误: {data.get('errDesc')}")
                    return []
            else:
                logger.error(f"请求失败，状态码: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"获取品种列表失败: {e}")
            return []

    def fetch_full_view(self, publish_date: Optional[date] = None) -> List[Dict]:
        """
        获取多空全景数据
        API: https://hzzhqx.com/api/report/overallView
        """
        if publish_date is None:
            publish_date = date.today()

        date_str = publish_date.strftime('%Y-%m-%d')

        try:
            logger.info(f"开始获取多空全景数据 (日期: {date_str})...")

            url = f"{self.base_url}/api/report/overallView"
            params = {
                'publishDate': date_str,
                'sectorId': '',
                'morePort': '全部'
            }

            response = requests.get(url, headers=self.headers, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()

                if data.get('success') and data.get('result'):
                    results = self._parse_full_view(data['result'])
                    logger.info(f"✅ 成功获取多空全景数据 {len(results)} 条")

                    # 保存数据
                    self._save_data(results, "多空全景")

                    return results
                else:
                    logger.error(f"API返回错误: {data.get('errDesc')}")
                    return []
            else:
                logger.error(f"请求失败，状态码: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"获取多空全景数据失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _parse_full_view(self, result_list: List[Dict]) -> List[Dict]:
        """解析多空全景API返回数据"""
        parsed_results = []

        for item in result_list:
            try:
                parsed_item = {
                    "variety_code": item.get("varietyCode", "").upper(),
                    "variety_name": item.get("varietyName", ""),
                    "excessive_ratio": item.get("excessiveRate", 0),  # 看多占比
                    "neutral_ratio": item.get("neutralRate", 0),      # 中性占比
                    "empty_ratio": item.get("emptyRate", 0),          # 看空占比
                    "excessive_num": item.get("excessiveNum", 0),     # 看多数量
                    "neutral_num": item.get("neutralNum", 0),         # 中性数量
                    "empty_num": item.get("emptyNum", 0),             # 看空数量
                    "sum": item.get("sum", 0),                        # 总数
                    "more_port": item.get("morePort", ""),            # 主流观点
                    "more_rate": item.get("moreRate", 0),             # 主流观点比例
                    "main_sentiment": self._map_sentiment(item.get("morePort", "")),
                    "record_time": datetime.now().isoformat()
                }
                parsed_results.append(parsed_item)
            except Exception as e:
                logger.debug(f"解析单条数据失败: {e}")
                continue

        return parsed_results

    def _map_sentiment(self, more_port: str) -> str:
        """将中文观点映射为英文"""
        if "偏多" in more_port or "看多" in more_port:
            return "bull"
        elif "偏空" in more_port or "看空" in more_port:
            return "bear"
        else:
            return "neutral"

    def fetch_research_reports(
        self,
        variety_code: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        view_port: str = "全部",
        page: int = 1,
        limit: int = 20
    ) -> Dict:
        """
        获取研报淘金数据
        API: https://hzzhqx.com/api/report/viewPoint/listPage

        Args:
            variety_code: 品种代码，如 'RB', 'AU'，默认全部
            start_date: 开始日期，默认今天
            end_date: 结束日期，默认今天
            view_port: 观点筛选（全部/看多/看空/中性）
            page: 页码
            limit: 每页数量

        Returns:
            {
                "reports": [
                    {
                        "report_id": 12345,
                        "publish_date": "2025-12-01",
                        "variety_code": "RB",
                        "variety": "螺纹钢",
                        "institution_name": "永安期货",
                        "view_port": "看多",
                        "trade_logic": "成本支撑...",
                        "related_data": "库存数据...",
                        "risk_factor": "需求走弱...",
                        "link": "http://...",
                        "sentiment": "bull"
                    },
                    ...
                ],
                "total": 100,
                "page": 1,
                "limit": 20
            }
        """
        if start_date is None:
            start_date = date.today()
        if end_date is None:
            end_date = date.today()

        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')

        try:
            logger.info(f"开始获取研报淘金数据 (品种: {variety_code or '全部'}, 日期: {start_str}~{end_str})...")

            url = f"{self.base_url}/api/report/viewPoint/listPage"
            params = {
                'page': page,
                'limit': limit,
                'startDate': start_str,
                'endDate': end_str,
                'institutionIds': '',
                'varietyCode': variety_code or '',
                'viewPort': view_port
            }

            response = requests.get(url, headers=self.headers, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()

                if data.get('success') and data.get('result'):
                    # API返回的是 records 字段,不是 list
                    reports = self._parse_research_reports(data['result'].get('records', []))
                    total = data['result'].get('total', 0)  # 也是total字段,不是totalCount
                    logger.info(f"✅ 成功获取研报数据 {len(reports)} 条 (总共{total}条)")

                    # 保存数据
                    if reports:
                        self._save_data({
                            "reports": reports,
                            "total": total,
                            "query": {
                                "variety_code": variety_code,
                                "start_date": start_str,
                                "end_date": end_str,
                                "view_port": view_port
                            }
                        }, f"研报淘金_{variety_code or '全部'}")

                    return {
                        "reports": reports,
                        "total": total,
                        "page": page,
                        "limit": limit
                    }
                else:
                    logger.error(f"API返回错误: {data.get('errDesc')}")
                    return {"reports": [], "total": 0}
            else:
                logger.error(f"请求失败，状态码: {response.status_code}")
                return {"reports": [], "total": 0}

        except Exception as e:
            logger.error(f"获取研报淘金数据失败: {e}")
            import traceback
            traceback.print_exc()
            return {"reports": [], "total": 0}

    def _parse_research_reports(self, report_list: List[Dict]) -> List[Dict]:
        """解析研报淘金数据"""
        parsed_reports = []

        for item in report_list:
            try:
                parsed_report = {
                    "report_id": item.get("id", 0),
                    "publish_date": item.get("publishDate", ""),
                    "variety_code": item.get("varietyCode", "").upper(),
                    "variety": item.get("variety", ""),
                    "institution_id": item.get("institutionId", ""),
                    "institution_name": item.get("institutionName", ""),
                    "view_port": item.get("viewPort", ""),  # 观点:看多/看空/中性
                    "trade_logic": item.get("tradeLogic", ""),  # 交易逻辑
                    "related_data": item.get("relatedData", ""),  # 相关数据
                    "risk_factor": item.get("riskFactor", ""),  # 风险因素
                    "link": item.get("link", ""),  # PDF下载地址
                    "sentiment": self._map_viewpoint(item.get("viewPort", ""))
                }
                parsed_reports.append(parsed_report)
            except Exception as e:
                logger.debug(f"解析研报数据失败: {e}")
                continue

        return parsed_reports

    def _map_viewpoint(self, view_port: str) -> str:
        """将观点映射为sentiment"""
        if "看多" in view_port or "偏多" in view_port:
            return "bull"
        elif "看空" in view_port or "偏空" in view_port:
            return "bear"
        else:
            return "neutral"

    def _save_data(self, data, data_type: str):
        """保存数据到本地JSON文件"""
        today = date.today().strftime('%Y%m%d')
        filename = f"{today}_{data_type}.json"
        filepath = self.save_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"数据已保存至: {filepath}")


async def main():
    """测试函数"""
    from datetime import timedelta
    spider = ZhihuiQixunSpider()

    # 测试品种列表
    logger.info("=" * 50)
    logger.info("测试品种列表API")
    logger.info("=" * 50)
    varieties = spider.fetch_variety_list()
    if varieties:
        logger.info(f"品种列表示例 (前5个):")
        for v in varieties[:5]:
            logger.info(f"  {v['variety_code']} - {v['variety_name']} ({v['sector_name']})")

    # 测试多空全景
    logger.info("\n" + "=" * 50)
    logger.info("测试多空全景API")
    logger.info("=" * 50)
    full_view = spider.fetch_full_view()
    if full_view:
        logger.info(f"多空全景示例 (前5条):")
        for item in full_view[:5]:
            logger.info(f"  {item['variety_code']} {item['variety_name']}: "
                      f"看多{item['excessive_num']}({item['excessive_ratio']}%), "
                      f"看空{item['empty_num']}({item['empty_ratio']}%), "
                      f"主流:{item['more_port']}")

    # 测试研报淘金(最近7天的螺纹钢研报)
    logger.info("\n" + "=" * 50)
    logger.info("测试研报淘金API - 螺纹钢(RB)")
    logger.info("=" * 50)
    end_date = date.today()
    start_date = end_date - timedelta(days=7)

    reports_data = spider.fetch_research_reports(
        variety_code="RB",
        start_date=start_date,
        end_date=end_date,
        limit=10
    )

    if reports_data['reports']:
        logger.info(f"研报示例 (前3条):")
        for report in reports_data['reports'][:3]:
            logger.info(f"  {report['publish_date']} - {report['institution_name']} - {report['view_port']}")
            if report['trade_logic']:
                logger.info(f"    交易逻辑: {report['trade_logic'][:80]}...")
            if report['risk_factor']:
                logger.info(f"    风险因素: {report['risk_factor'][:80]}...")
    else:
        logger.warning("未获取到研报数据,可能需要检查token或API权限")

    # 测试研报淘金 - 获取全部品种的今日研报
    logger.info("\n" + "=" * 50)
    logger.info("测试研报淘金API - 全部品种(今日)")
    logger.info("=" * 50)

    all_reports_data = spider.fetch_research_reports(
        variety_code=None,  # 全部品种
        start_date=date.today(),
        end_date=date.today(),
        limit=20
    )

    if all_reports_data['reports']:
        logger.info(f"今日研报总数: {all_reports_data['total']} 条")
        logger.info(f"返回示例 (前5条):")
        for report in all_reports_data['reports'][:5]:
            logger.info(f"  {report['variety']} - {report['institution_name']} - {report['view_port']}")
    else:
        logger.warning("未获取到今日研报数据")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    import asyncio
    asyncio.run(main())
