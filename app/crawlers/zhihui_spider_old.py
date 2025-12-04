"""
智汇期讯爬虫 - hzzhqx.com (需要登录)
功能：
1. 多空全景模块 - 获取所有品种的主流观点及占比
   API: https://hzzhqx.com/api/report/overallView?publishDate=YYYY-MM-DD&sectorId=&morePort=全部
   字段: varietyCode, varietyName, excessiveNum, neutralNum, emptyNum, morePort, moreRate
2. 研报淘金模块 - 获取机构观点、交易逻辑、相关数据、风险因素
   API: https://hzzhqx.com/api/report/viewPoint/listPage
   字段: publishDate, variety, varietyCode, institutionName, viewPort, tradeLogic, relatedData, riskFactor, link
"""
import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict
import json
from pathlib import Path
from playwright.async_api import async_playwright, Browser, Page

logger = logging.getLogger(__name__)


class ZhihuiQixunSpider:
    """智汇期讯爬虫 - 使用Playwright登录后调用API"""

    def __init__(self, username: str = None, password: str = None):
        from config.settings import get_settings
        settings = get_settings()

        self.base_url = "https://hzzhqx.com"
        self.username = username or settings.ZHIHUI_USER or "18321399574"
        self.password = password or settings.ZHIHUI_PASS or "yi2013405"
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.save_dir = Path(__file__).parent.parent.parent / "智汇期讯" / "data"
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.cookies = None
        # cookies文件路径
        self.cookies_file = Path(__file__).parent.parent.parent / ".cookies" / "zhihui_cookies.json"

    async def load_cookies(self) -> bool:
        """加载保存的cookies"""
        try:
            if self.cookies_file.exists():
                with open(self.cookies_file, 'r', encoding='utf-8') as f:
                    self.cookies = json.load(f)
                logger.info(f"已加载cookies: {len(self.cookies)}个")
                return True
            else:
                logger.warning(f"cookies文件不存在: {self.cookies_file}")
                return False
        except Exception as e:
            logger.error(f"加载cookies失败: {e}")
            return False

    async def init_browser(self, headless: bool = True):
        """初始化浏览器"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=headless,
            args=['--no-sandbox']
        )
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )

        # 加载cookies
        if await self.load_cookies():
            await context.add_cookies(self.cookies)
            logger.info("cookies已注入到浏览器")

        self.page = await context.new_page()
        logger.info("浏览器初始化成功")

    async def login(self) -> bool:
        """登录智汇期讯 - 优先使用cookies"""
        try:
            logger.info("开始登录智汇期讯...")

            # 访问首页检查cookies是否有效
            try:
                await self.page.goto("https://hzzhqx.com/home", wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(2)

                # 检查是否已经登录（cookies有效）
                if await self.page.query_selector("text=退出") or await self.page.query_selector(".user-info"):
                    logger.info("✅ cookies有效，已自动登录")
                    return True
                else:
                    logger.warning("cookies已失效或不存在，需要重新登录")
                    logger.info("请运行 'python3 save_cookies.py' 手动登录并保存cookies")
                    return False

            except Exception as e:
                logger.warning(f"导航可能被重定向中断 (这是正常的): {e}")

            await asyncio.sleep(3)  # 等待页面加载完成

            # 0. 先尝试关闭可能存在的广告弹窗
            close_button_selectors = [
                ".layui-layer-close",  # layui弹窗关闭按钮
                ".el-dialog__close",   # Element UI弹窗关闭
                ".close-btn",
                "button:has-text('关闭')",
                "div[class*='close']",
                ".modal-close"
            ]

            for selector in close_button_selectors:
                try:
                    close_btn = await self.page.query_selector(selector)
                    if close_btn and await close_btn.is_visible():
                        await close_btn.click()
                        logger.info(f"关闭了弹窗: {selector}")
                        await asyncio.sleep(1)
                        break
                except:
                    continue

            # 1. 点击首页的登录按钮，弹出登录框
            login_trigger_selectors = [
                "div.login-btn",
                "span:has-text('登录')",
                "a:has-text('登录')",
                ".header-login",
                "text=登录"
            ]

            trigger_clicked = False
            for selector in login_trigger_selectors:
                try:
                    elem = await self.page.query_selector(selector)
                    if elem and await elem.is_visible():
                        await elem.click()
                        logger.info(f"点击了登录入口: {selector}")
                        trigger_clicked = True
                        await asyncio.sleep(3) # 等待弹窗/表单出现
                        break
                except:
                    continue

            if not trigger_clicked:
                logger.warning("未找到首页登录入口，尝试直接查找输入框(可能已在登录页)")

            # 2. 查找用户名输入框
            username_selectors = [
                "input[placeholder*='手机']",
                "input[placeholder*='用户名']",
                "input[type='tel']",
                "input[type='text']",
                "input.el-input__inner",  # Element UI
                ".login-form input:nth-child(1)",
                "form input:first-of-type"
            ]
            
            username_input = None
            for selector in username_selectors:
                try:
                    username_input = await self.page.wait_for_selector(selector, timeout=5000, state="visible")
                    if username_input:
                        logger.info(f"找到用户名输入框: {selector}")
                        break
                except:
                    continue
            
            if username_input:
                await username_input.fill(self.username)
                logger.info("已填写用户名")
            else:
                # 打印所有input元素用于调试
                all_inputs = await self.page.query_selector_all("input")
                logger.error(f"未找到用户名输入框,页面共有 {len(all_inputs)} 个input元素")
                return False

            # 3. 查找并填写密码
            password_selectors = [
                "input[type='password']",
                "input[placeholder*='密码']",
                ".login-form input:nth-child(2)",
                "form input:last-of-type"
            ]
            
            password_input = None
            for selector in password_selectors:
                try:
                    password_input = await self.page.wait_for_selector(selector, timeout=5000, state="visible")
                    if password_input:
                        logger.info(f"找到密码输入框: {selector}")
                        break
                except:
                    continue
                    
            if password_input:
                await password_input.fill(self.password)
                logger.info("已填写密码")
            else:
                logger.error("未找到密码输入框")
                return False

            await asyncio.sleep(1)

            # 4. 点击提交按钮
            submit_button_selectors = [
                "button:has-text('登录')",
                "button:has-text('登 录')",
                ".login-btn",
                "button[type='submit']",
                ".el-button--primary"
            ]
            
            submit_button = None
            for selector in submit_button_selectors:
                # 排除首页的登录入口按钮，只找表单内的提交按钮
                buttons = await self.page.query_selector_all(selector)
                for btn in buttons:
                    if await btn.is_visible():
                        submit_button = btn
                        break
                if submit_button:
                    logger.info(f"找到提交按钮: {selector}")
                    break
                    
            if submit_button:
                await submit_button.click()
                logger.info("已点击提交按钮")
            else:
                logger.error("未找到提交按钮")
                return False

            # 等待登录成功 - 检查是否跳转或出现用户信息
            await asyncio.sleep(3)

            # 保存cookies
            self.cookies = await self.page.context.cookies()
            logger.info(f"登录成功,已保存 {len(self.cookies)} 个Cookie")

            return True

        except Exception as e:
            logger.error(f"登录失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def fetch_full_view(self, publish_date: Optional[date] = None) -> List[Dict]:
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

            # 使用页面的evaluate方法通过浏览器发起请求(带Cookie)
            response_text = await self.page.evaluate(f"""
                async () => {{
                    const response = await fetch('{url}?publishDate={date_str}&sectorId=&morePort=全部', {{
                        method: 'GET',
                        headers: {{
                            'Accept': 'application/json',
                            'Referer': '{self.base_url}/report/fullView'
                        }}
                    }});
                    return await response.text();
                }}
            """)

            data = json.loads(response_text)

            if data.get('success') and data.get('result'):
                results = self._parse_full_view(data['result'])
                logger.info(f"成功获取多空全景数据 {len(results)} 条")
                return results
            else:
                logger.error(f"API返回错误: {data.get('errDesc')}")
                return []

        except Exception as e:
            logger.error(f"获取多空全景数据失败: {e}")
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
                    "main_sentiment": self._map_sentiment(item.get("morePort", ""))
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

    async def fetch_research_reports(
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

            # 构建参数
            params_str = f"page={page}&limit={limit}&startDate={start_str}&endDate={end_str}&institutionIds=&varietyCode={variety_code or ''}&viewPort={view_port}"

            # 使用页面的evaluate方法通过浏览器发起请求(带Cookie)
            response_text = await self.page.evaluate(f"""
                async () => {{
                    const response = await fetch('{url}?{params_str}', {{
                        method: 'GET',
                        headers: {{
                            'Accept': 'application/json',
                            'Referer': '{self.base_url}/report/fullView'
                        }}
                    }});
                    return await response.text();
                }}
            """)

            data = json.loads(response_text)

            if data.get('success') and data.get('result'):
                reports = self._parse_research_reports(data['result'].get('list', []))
                total = data['result'].get('totalCount', 0)
                logger.info(f"成功获取研报数据 {len(reports)} 条 (总共{total}条)")

                return {
                    "reports": reports,
                    "total": total,
                    "page": page,
                    "limit": limit
                }
            else:
                logger.error(f"API返回错误: {data.get('errDesc')}")
                return {"reports": [], "total": 0}

        except Exception as e:
            logger.error(f"获取研报淘金数据失败: {e}")
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

    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
            logger.info("浏览器已关闭")


async def main():
    """测试函数"""
    spider = ZhihuiQixunSpider()

    try:
        # 初始化浏览器
        await spider.init_browser(headless=False)  # 测试时显示浏览器

        # 登录
        if not await spider.login():
            logger.error("登录失败,退出测试")
            return

        await asyncio.sleep(2)

        # 测试多空全景
        logger.info("=" * 50)
        logger.info("测试多空全景API")
        logger.info("=" * 50)
        full_view = await spider.fetch_full_view()
        if full_view:
            spider._save_data(full_view, "多空全景")
            logger.info(f"示例数据 (前3条):")
            for item in full_view[:3]:
                logger.info(f"  {item['variety_code']} {item['variety_name']}: "
                          f"看多{item['excessive_num']}({item['excessive_ratio']}%), "
                          f"看空{item['empty_num']}({item['empty_ratio']}%), "
                          f"主流:{item['more_port']}")

        # 测试研报淘金(黄金品种)
        logger.info("=" * 50)
        logger.info("测试研报淘金API - 黄金(au)")
        logger.info("=" * 50)
        end_date = date.today()
        start_date = end_date - timedelta(days=7)

        reports_data = await spider.fetch_research_reports(
            variety_code="au",
            start_date=start_date,
            end_date=end_date,
            limit=10
        )

        if reports_data['reports']:
            spider._save_data(reports_data, "研报淘金_黄金")
            logger.info(f"示例研报 (前2条):")
            for report in reports_data['reports'][:2]:
                logger.info(f"  {report['institution_name']} - {report['view_port']}")
                logger.info(f"    交易逻辑: {report['trade_logic'][:50]}...")

    finally:
        await spider.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())
