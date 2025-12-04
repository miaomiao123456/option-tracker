"""
交易可查爬虫 - jiaoyikecha.com
功能：
1. 登录获取session
2. 爬取席位资金数据
3. 爬取每日交易蓝图图片（带标题和日期识别）
"""
import asyncio
import logging
from datetime import datetime, date
from typing import Optional, List, Dict
from playwright.async_api import async_playwright, Page, Browser
from config.settings import get_settings
from pathlib import Path
import json
import time
import base64
import re
from openai import OpenAI

logger = logging.getLogger(__name__)
settings = get_settings()


class JiaoyiKechaSpider:
    """交易可查爬虫类"""

    # 真实期货品种列表（用于验证AI识别结果）
    VALID_VARIETIES = {
        '20号胶', 'BR橡胶', 'LU燃油', 'PTA', 'PVC', '三十年债', '上证50',
        '不锈钢', '丙烯', '中证1000', '中证500', '乙二醇', '二年债', '五年债',
        '十年债', '原木', '原油', '双胶纸', '塑料', '多晶硅', '对二甲苯', '尿素',
        '工业硅', '棉花', '棕榈油', '橡胶', '氧化铝', '沥青', '沪深300', '沪金',
        '沪铅', '沪铜', '沪铝', '沪银', '沪锌', '沪锡', '沪镍', '液化气', '淀粉',
        '烧碱', '热卷', '焦炭', '焦煤', '燃料油', '玉米', '玻璃', '瓶片', '生猪',
        '甲醇', '白糖', '短纤', '硅铁', '碳酸锂', '红枣', '纯碱', '纯苯', '纸浆',
        '聚丙烯', '花生', '苯乙烯', '苹果', '菜籽油', '菜籽粕', '螺纹钢', '豆一',
        '豆二', '豆油', '豆粕', '铁矿石', '铝合金', '锰硅', '集运欧线', '鸡蛋'
    }

    def __init__(self):
        self.settings = settings
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.is_logged_in = False
        self.save_dir = Path(__file__).parent.parent.parent / "交易可查" / "images"
        self.save_dir.mkdir(parents=True, exist_ok=True)

        # 初始化Gemini客户端用于图片识别
        self.ai_client = OpenAI(
            api_key=settings.GEMINI_API_KEY,
            base_url=settings.GEMINI_BASE_URL
        )

    async def init_browser(self, headless: bool = True):
        """初始化浏览器"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=headless,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        self.page = await context.new_page()
        logger.info("浏览器初始化成功")

    async def login(self) -> bool:
        """登录交易可查"""
        try:
            logger.info("开始登录交易可查...")
            
            # 访问页面
            await self.page.goto("https://www.jiaoyikecha.com/", wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(3)
            
            # 检查是否已经登录
            if await self.page.query_selector("text=退出") or await self.page.query_selector("text=个人中心"):
                logger.info("检测到已经登录")
                return True

            logger.info(f"当前页面标题: {await self.page.title()}")
            
            # 检查是否直接显示了输入框 (有时会直接在登录页)
            try:
                # 等待登录按钮 OR 输入框
                try:
                    # 尝试多种登录按钮选择器
                    login_btns = ["text=登录", ".login-btn", "a:has-text('登录')"]
                    found_btn = False
                    for btn in login_btns:
                        if await self.page.is_visible(btn):
                            logger.info(f"找到登录按钮: {btn}")
                            # 关闭弹窗
                            close_btn = await self.page.query_selector(".close-btn, .layui-layer-close")
                            if close_btn: await close_btn.click()
                            
                            await self.page.click(btn, force=True)
                            found_btn = True
                            break
                    
                    if not found_btn:
                        logger.info("未找到显式登录按钮")
                except Exception as e:
                    logger.info(f"点击登录按钮过程异常: {e}")

                await self.page.wait_for_selector("input[placeholder*='手机号']", timeout=5000)
                logger.info("找到登录输入框")
            except Exception as e:
                logger.warning(f"未找到登录入口: {e}")
                # 打印页面源码片段
                content = await self.page.content()
                logger.info(f"页面源码片段: {content[:500]}...")
                
                # 再次检查是否已登录
                if await self.page.query_selector("text=退出"):
                    return True
                return False

            # 输入账号密码
            await self.page.fill("input[placeholder*='手机号']", self.settings.JYK_USER)
            await self.page.fill("input[placeholder*='密码']", self.settings.JYK_PASS)

            # 点击登录按钮
            await self.page.click("button:has-text('登录')", force=True)

            # 等待登录成功 - 可能跳转到首页或个人中心
            try:
                await self.page.wait_for_url("**/user/home", timeout=15000)
                self.is_logged_in = True
                logger.info("登录成功!")
                return True
            except:
                # 检查是否已经在主页
                current_url = self.page.url
                if "user" in current_url or "home" in current_url:
                    self.is_logged_in = True
                    logger.info("登录成功!")
                    return True
                else:
                    logger.error(f"登录失败，当前URL: {current_url}")
                    return False

        except Exception as e:
            logger.error(f"登录过程出错: {e}")
            return False

    async def fetch_daily_blueprint(self, target_date: Optional[date] = None) -> Optional[Dict]:
        """
        获取每日交易蓝图
        - 只爬取标题包含"交易蓝图"的图片
        - 从图片上识别真实日期
        返回: {image_url, local_path, date, title}
        """
        if target_date is None:
            target_date = date.today()

        try:
            logger.info(f"开始获取交易蓝图...")

            # 使用最新的API端点
            api_url = "https://www.jiaoyikecha.com/ajax/guangao.php?v=cd42afe7"

            response = await self.page.evaluate(f"""
                async () => {{
                    const res = await fetch('{api_url}', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                            'X-Requested-With': 'XMLHttpRequest'
                        }},
                        body: 'path=/'
                    }});
                    return await res.json();
                }}
            """)

            if response and response.get('code') == 0:
                image_url = response.get('data', {}).get('adall', {}).get('imageUrl')

                if image_url:
                    logger.info(f"成功获取图片URL: {image_url}")

                    # 先下载到临时文件
                    temp_path = await self._download_to_temp(image_url)

                    # 使用AI分析图片内容
                    analysis = self._analyze_blueprint_image(temp_path)

                    if not analysis:
                        logger.warning("图片分析失败")
                        temp_path.unlink()  # 删除临时文件
                        return None

                    # 检查标题是否包含"交易蓝图"
                    title = analysis.get('title', '')
                    if '交易蓝图' not in title and '蓝图' not in title:
                        logger.warning(f"图片标题不是交易蓝图: {title}")
                        temp_path.unlink()  # 删除临时文件
                        return None

                    # 获取识别的日期
                    recognized_date = analysis.get('date', '')
                    if not recognized_date or len(recognized_date) != 8:
                        logger.warning(f"未能识别有效日期: {recognized_date}, 使用默认日期")
                        recognized_date = target_date.strftime('%Y%m%d')

                    # 将临时文件重命名为正确的日期
                    final_path = self.save_dir / f"{recognized_date}.jpg"
                    temp_path.rename(final_path)

                    # 解析蓝图策略
                    strategies = self._parse_blueprint_strategies(final_path)

                    logger.info(f"✅ 成功获取交易蓝图 - 标题: {title}, 日期: {recognized_date}, 策略数: {len(strategies)}")

                    return {
                        "image_url": image_url,
                        "local_path": str(final_path),
                        "date": recognized_date,
                        "title": title,
                        "strategies": strategies
                    }
                else:
                    logger.warning("API返回中未找到imageUrl")

            # 方法2：如果API失败，尝试访问用户首页
            await self.page.goto("https://www.jiaoyikecha.com/#/user/home")
            await self.page.wait_for_timeout(3000)

            # 查找图片元素
            img_selector = "img[src*='uploadfile']"
            img_element = await self.page.query_selector(img_selector)

            if img_element:
                image_url = await img_element.get_attribute('src')

                # 下载并分析
                temp_path = await self._download_to_temp(image_url)
                analysis = self._analyze_blueprint_image(temp_path)

                if analysis and ('交易蓝图' in analysis.get('title', '') or '蓝图' in analysis.get('title', '')):
                    recognized_date = analysis.get('date', target_date.strftime('%Y%m%d'))
                    final_path = self.save_dir / f"{recognized_date}.jpg"
                    temp_path.rename(final_path)

                    return {
                        "image_url": image_url,
                        "local_path": str(final_path),
                        "date": recognized_date,
                        "title": analysis.get('title', '')
                    }
                else:
                    temp_path.unlink()

            logger.warning("未找到符合条件的交易蓝图图片")
            return None

        except Exception as e:
            logger.error(f"获取交易蓝图失败: {e}")
            return None

    async def _download_to_temp(self, url: str) -> Path:
        """下载图片到临时文件"""
        import httpx

        temp_filename = f"temp_{int(time.time())}.jpg"
        temp_filepath = self.save_dir / temp_filename

        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()

            with open(temp_filepath, 'wb') as f:
                f.write(response.content)

        logger.info(f"图片已下载到临时文件: {temp_filepath}")
        return temp_filepath

    def _parse_blueprint_strategies(self, image_path: Path) -> List[Dict]:
        """
        使用AI解析蓝图图片中的交易策略
        返回: [{'variety': str, 'direction': str, 'signal': str, 'reason': str}]
        """
        try:
            # 将图片转为base64
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')

            # 调用Gemini Vision API
            response = self.ai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """请仔细分析这张交易蓝图图片，提取所有交易策略信息。

**操作术语定义**：
- **加多** = 增加多头持仓 = 看多信号 📈 （主要信号）
- **加空** = 增加空头持仓 = 看空信号 📉 （主要信号）
- **减多** = 减少多头持仓 = 看空信号 📉 （次要信号）
- **减空** = 减少空头持仓 = 看多信号 📈 （次要信号）

**重要规则**：
1. **散户（五大散户席位/五大家人席位）**：反向操作
   - 散户**加多** → 做空（反向）
   - 散户**加空** → 做多（反向）

2. **机构（外资席位、五大机构席位）**：同向操作
   - 外资/机构**加多** → 做多（同向）
   - 外资/机构**加空** → 做空（同向）

3. **强度评定**（⭐数量）：
   - ⭐⭐⭐⭐⭐（5星）：三方都有操作（散户+外资+机构），或有"大力"、"大幅"等强烈程度词
   - ⭐⭐⭐⭐（4星）：至少两方有操作，或单方有"继续"、"持续"、"中幅"等程度词
   - ⭐⭐⭐（3星）：单方操作且有"小幅"等词
   - ⭐⭐（2星以下）：弱信号，不提取

4. **程度描述词**（增强信号）：
   - 大幅、大力：5星
   - 中幅、继续、持续：4星
   - 小幅：3星

5. **策略生成优先级**（重要！）：
   - **优先级1**：明确的"加多"或"加空"操作（强进场信号）
   - **优先级2**："减多"或"减空"仅在以下情况提取：
     - 与"加多/加空"配合使用时（如：散户减多+机构加多）
     - 有明确的"继续减"、"大幅减"等强程度词
   - 单独的"减多"或"减空"（无程度词）通常不生成策略

**示例分析**：
- 图片显示"五大家人席位小幅减多焦煤，五大机构减空焦煤" → 焦煤做多，⭐⭐⭐，理由"散户小幅减多,机构减空,综合做多"
- 图片显示"外资加多花生" → 做多，⭐⭐⭐⭐，理由"外资加多,同向做多"
- 图片显示"五大家人加多烧碱，五大机构加空烧碱" → 做空，⭐⭐⭐⭐⭐，理由"散户加多,机构加空,反向做空"

请以JSON数组格式返回，格式：
```json
[
  {"variety": "品种名称", "direction": "做多/做空", "signal": "⭐⭐⭐⭐⭐", "reason": "简要理由"}
]
```

**注意**：
1. **只提取⭐⭐⭐（3星）及以上的策略**
2. **variety必须是具体品种名**（如"焦煤"、"螺纹钢"、"白银"），不要搞错焦煤和焦炭！
3. **reason要说明是散户还是机构操作**，以及具体动作
4. **优先提取"加多/加空"的强信号策略**
"""
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2000
            )

            # 解析响应
            content = response.choices[0].message.content.strip()
            logger.info(f"AI策略解析结果: {content[:300]}...")

            # 提取JSON
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                json_str = content

            strategies = json.loads(json_str)

            # 筛选出4星及以上的策略，并验证品种名称
            high_strength_strategies = []
            invalid_varieties = []

            for strategy in strategies:
                signal = strategy.get('signal', '')
                star_count = signal.count('⭐')

                if star_count >= 4:
                    variety = strategy.get('variety', '')

                    # 验证品种名称
                    if variety in self.VALID_VARIETIES:
                        high_strength_strategies.append(strategy)
                    else:
                        # 尝试模糊匹配
                        matched = self._fuzzy_match_variety(variety)
                        if matched:
                            logger.info(f"⚠️  品种名称修正: '{variety}' → '{matched}'")
                            strategy['variety'] = matched
                            high_strength_strategies.append(strategy)
                        else:
                            invalid_varieties.append(variety)
                            logger.warning(f"❌ 无效品种已过滤: '{variety}'")

            if invalid_varieties:
                logger.warning(f"过滤掉的无效品种: {', '.join(invalid_varieties)}")

            logger.info(f"✅ 解析到 {len(strategies)} 条策略，其中 {len(high_strength_strategies)} 条为4星及以上（已验证品种）")
            return high_strength_strategies

        except Exception as e:
            logger.error(f"解析策略失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _fuzzy_match_variety(self, variety: str) -> Optional[str]:
        """
        模糊匹配品种名称
        处理AI识别错误的品种名（如"空铁锰" → "锰硅"）
        """
        # 常见误识别映射
        corrections = {
            '空铁锰': '锰硅',
            '铁锰': '锰硅',
            '空硅铁': '硅铁',
            '银': '沪银',
            '白银': '沪银',
            '焦': '焦炭',  # 如果只有"焦"，默认焦炭
            '螺旋桨油': '棕榈油',
            '棕油': '棕榈油',
        }

        # 精确映射
        if variety in corrections:
            return corrections[variety]

        # 模糊匹配：如果品种名包含在真实品种中
        for valid_variety in self.VALID_VARIETIES:
            if variety in valid_variety or valid_variety in variety:
                # 避免误匹配（如"铁"匹配到"硅铁"和"铁矿石"）
                if len(variety) >= 2:
                    return valid_variety

        return None

    def _analyze_blueprint_image(self, image_path: Path) -> Optional[Dict]:
        """
        使用AI分析蓝图图片，提取标题和日期
        返回: {'title': str, 'date': str (YYYYMMDD格式)} 或 None
        """
        try:
            # 将图片转为base64
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')

            # 获取当前年份
            current_year = datetime.now().year

            # 调用Gemini Vision API
            response = self.ai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"""请分析这张图片,提取以下信息:
1. 图片标题(如果有"交易蓝图"或类似文字)
2. 图片上的日期

注意事项:
- 图片上的日期通常只显示月日(如"11.26"),请使用当前年份{current_year}补全
- 如果图片上显示"11.26",则日期应为"{current_year}1126"
- 日期格式必须是YYYYMMDD(8位数字)

请以JSON格式返回,例如:
{{"title": "交易蓝图", "date": "{current_year}1126"}}

如果图片上没有这些信息或不是交易蓝图,返回:
{{"title": "", "date": ""}}"""
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500
            )

            # 解析响应
            content = response.choices[0].message.content.strip()
            logger.info(f"AI识别结果: {content}")

            # 提取JSON
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                json_str = content

            result = json.loads(json_str)
            return result

        except Exception as e:
            logger.error(f"分析图片失败: {e}")
            return None

    async def fetch_variety_positions(self, variety_code: str) -> Optional[List[Dict]]:
        """
        获取品种的席位持仓数据
        variety_code: 如 'rb' (螺纹钢)
        """
        try:
            logger.info(f"开始获取 {variety_code} 的席位数据...")

            url = f"https://www.jiaoyikecha.com/#/variety/structure?code={variety_code}"
            # 增加超时时间
            await self.page.goto(url, wait_until="networkidle", timeout=30000)
            await self.page.wait_for_timeout(5000)

            # 等待表格加载
            try:
                await self.page.wait_for_selector("table", timeout=20000)
            except:
                logger.warning(f"{variety_code} 未找到表格，尝试查找其他元素")
                # 可能是数据未加载或需要点击某个tab
                pass

            # 提取表格数据 - 针对特定席位
            # 目标席位: 东方财富, 国泰君安, 东证期货
            positions = await self.page.evaluate("""
                () => {
                    const rows = document.querySelectorAll('table tbody tr');
                    const data = [];
                    const targetBrokers = ['东方财富', '国泰君安', '东证期货'];

                    rows.forEach(row => {
                        const cells = row.querySelectorAll('td');
                        if (cells.length > 0) {
                            const brokerName = cells[0]?.textContent?.trim() || '';
                            
                            // 检查是否是目标席位 (模糊匹配)
                            const isTarget = targetBrokers.some(target => brokerName.includes(target));
                            
                            if (isTarget) {
                                data.push({
                                    broker: brokerName,
                                    net_position: cells[1]?.textContent?.trim() || '0',
                                    change: cells[2]?.textContent?.trim() || '0',
                                    ratio: cells[3]?.textContent?.trim() || '0'
                                });
                            }
                        }
                    });

                    return data;
                }
            """)

            logger.info(f"成功获取 {len(positions)} 条目标席位数据")
            return positions

        except Exception as e:
            logger.error(f"获取席位数据失败: {e}")
            return None

    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
            logger.info("浏览器已关闭")


async def main():
    """测试函数"""
    spider = JiaoyiKechaSpider()

    try:
        # 初始化浏览器
        await spider.init_browser(headless=True)

        # 登录
        if await spider.login():
            # 获取交易蓝图
            blueprint = await spider.fetch_daily_blueprint()
            if blueprint:
                logger.info(f"交易蓝图数据: {json.dumps(blueprint, ensure_ascii=False, indent=2)}")

            # 获取螺纹钢席位数据
            positions = await spider.fetch_variety_positions('rb')
            if positions:
                logger.info(f"席位数据示例: {json.dumps(positions[:3], ensure_ascii=False, indent=2)}")

    finally:
        await spider.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
