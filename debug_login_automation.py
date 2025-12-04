"""
调试登录自动化 - 尝试自动登录并保存cookies
带详细日志和截图功能
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

COOKIES_DIR = Path(__file__).parent / ".cookies"
COOKIES_DIR.mkdir(exist_ok=True)

DEBUG_DIR = Path(__file__).parent / "debug_screenshots"
DEBUG_DIR.mkdir(exist_ok=True)


async def debug_zhihui_login():
    """调试智汇期讯登录"""
    logger.info("=" * 70)
    logger.info("开始调试智汇期讯登录")
    logger.info("=" * 70)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()

        try:
            # 步骤1: 访问页面
            logger.info("步骤1: 访问登录页面")
            await page.goto("https://hzzhqx.com/home", wait_until="domcontentloaded", timeout=60000)
            await page.screenshot(path=DEBUG_DIR / "zhihui_01_初始页面.png")
            await asyncio.sleep(3)

            # 步骤2: 检查并关闭可能的弹窗
            logger.info("步骤2: 检查弹窗")
            popup_selectors = [
                ".el-dialog__close",
                ".el-icon-close",
                "[class*='close']",
                "[class*='modal-close']",
                "button:has-text('关闭')",
                "button:has-text('取消')",
            ]

            for selector in popup_selectors:
                try:
                    close_btn = await page.query_selector(selector)
                    if close_btn:
                        logger.info(f"找到关闭按钮: {selector}")
                        await close_btn.click()
                        await asyncio.sleep(1)
                        break
                except:
                    pass

            await page.screenshot(path=DEBUG_DIR / "zhihui_02_关闭弹窗后.png")

            # 步骤3: 查找并点击登录按钮
            logger.info("步骤3: 查找并点击登录按钮")
            login_entry_selectors = [
                "button:has-text('登录')",
                "button:has-text('登錄')",
                "text=登录",
                "a:has-text('登录')",
                "[class*='login-btn']",
            ]

            login_clicked = False
            for selector in login_entry_selectors:
                try:
                    login_btn = await page.query_selector(selector)
                    if login_btn and await login_btn.is_visible():
                        logger.info(f"找到登录按钮: {selector}")
                        await login_btn.click()
                        login_clicked = True
                        break
                except Exception as e:
                    logger.debug(f"尝试 {selector} 失败: {e}")

            if not login_clicked:
                logger.error("未找到登录按钮")
                return False

            # 等待登录对话框出现
            logger.info("等待登录对话框出现...")
            await asyncio.sleep(3)  # 等待动画完成
            await page.screenshot(path=DEBUG_DIR / "zhihui_03_点击登录后.png")

            # 步骤4: 查找登录表单(在对话框内)
            logger.info("步骤4: 查找登录表单")

            # 检查是否有iframe
            frames = page.frames
            logger.info(f"页面共有 {len(frames)} 个frame")

            # 首先尝试在对话框内查找
            # 等待对话框出现
            try:
                await page.wait_for_selector(".el-dialog", state="visible", timeout=5000)
                logger.info("检测到对话框已显示")
            except:
                logger.warning("未检测到对话框，继续在整个页面查找")

            # 在主页面和所有iframe中查找输入框
            all_frames = [page] + page.frames

            username_input = None
            password_input = None
            target_frame = None

            for frame in all_frames:
                try:
                    # 查找用户名输入框（优先在可见的对话框内查找）
                    username_selectors = [
                        ".el-dialog input[type='text']",
                        ".el-dialog input[type='tel']",
                        ".el-dialog input[placeholder*='手机']",
                        ".el-dialog input[placeholder*='账号']",
                        "input[type='text']",
                        "input[type='tel']",
                        "input[placeholder*='手机']",
                        "input[placeholder*='账号']",
                        "input[placeholder*='用户']",
                        "input[name*='user']",
                        "input[name*='phone']",
                        "input[name*='mobile']",
                    ]

                    for selector in username_selectors:
                        elements = await frame.query_selector_all(selector)
                        for elem in elements:
                            try:
                                if await elem.is_visible():
                                    username_input = elem
                                    target_frame = frame
                                    logger.info(f"找到用户名输入框: {selector} (在 {'主页面' if frame == page else 'iframe'})")
                                    break
                            except:
                                pass
                        if username_input:
                            break

                    if username_input:
                        break
                except:
                    pass

            if not username_input:
                logger.error("❌ 未找到用户名输入框")
                await page.screenshot(path=DEBUG_DIR / "zhihui_04_ERROR_未找到输入框.png")

                # 输出页面HTML帮助调试
                html_content = await page.content()
                with open(DEBUG_DIR / "zhihui_page_source.html", 'w', encoding='utf-8') as f:
                    f.write(html_content)
                logger.info(f"页面HTML已保存到: {DEBUG_DIR / 'zhihui_page_source.html'}")

                return False

            # 查找密码输入框
            password_selectors = [
                ".el-dialog input[type='password']",
                ".el-dialog input[placeholder*='密码']",
                "input[type='password']",
                "input[placeholder*='密码']",
                "input[name*='pass']",
            ]

            for selector in password_selectors:
                try:
                    elem = await target_frame.query_selector(selector)
                    if elem:
                        try:
                            if await elem.is_visible():
                                password_input = elem
                                logger.info(f"找到密码输入框: {selector}")
                                break
                        except:
                            pass
                except:
                    pass

            if not password_input:
                logger.error("❌ 未找到密码输入框")
                await page.screenshot(path=DEBUG_DIR / "zhihui_05_ERROR_未找到密码框.png")
                return False

            # 步骤5: 填写账号密码
            logger.info("步骤5: 填写登录信息")
            await username_input.fill("18321399574")
            await asyncio.sleep(0.5)
            await password_input.fill("yi2013405")
            await asyncio.sleep(0.5)
            await page.screenshot(path=DEBUG_DIR / "zhihui_06_填写完成.png")

            # 步骤6: 点击登录按钮
            logger.info("步骤6: 点击登录按钮")
            login_button_selectors = [
                "button:has-text('登录')",
                "button:has-text('登錄')",
                "button[type='submit']",
                "[class*='login-btn']",
                "[class*='submit']",
            ]

            login_button_clicked = False
            for selector in login_button_selectors:
                try:
                    btn = await target_frame.query_selector(selector)
                    if btn and await btn.is_visible():
                        logger.info(f"找到登录按钮: {selector}")
                        await btn.click()
                        login_button_clicked = True
                        break
                except Exception as e:
                    logger.debug(f"尝试点击 {selector} 失败: {e}")

            if not login_button_clicked:
                # 尝试按Enter键提交
                logger.info("未找到登录按钮，尝试按Enter提交")
                await password_input.press("Enter")

            await asyncio.sleep(5)
            await page.screenshot(path=DEBUG_DIR / "zhihui_07_登录后.png")

            # 步骤7: 检查登录状态
            logger.info("步骤7: 检查登录状态")
            current_url = page.url
            logger.info(f"当前URL: {current_url}")

            cookies = await context.cookies()
            logger.info(f"当前cookies数量: {len(cookies)}")

            # 检查是否有登录后的元素
            logged_in_selectors = [
                "text=退出",
                "text=登出",
                "text=个人中心",
                "[class*='user-info']",
            ]

            logged_in = False
            for selector in logged_in_selectors:
                try:
                    elem = await page.query_selector(selector)
                    if elem:
                        logged_in = True
                        logger.info(f"✅ 检测到登录成功标志: {selector}")
                        break
                except:
                    pass

            if logged_in or len(cookies) > 5:
                logger.info("✅ 登录成功！保存cookies...")
                cookies_file = COOKIES_DIR / "zhihui_cookies.json"
                with open(cookies_file, 'w', encoding='utf-8') as f:
                    json.dump(cookies, f, ensure_ascii=False, indent=2)
                logger.info(f"✅ Cookies已保存: {cookies_file} (共{len(cookies)}个)")
                return True
            else:
                logger.error("❌ 登录可能失败")
                await page.screenshot(path=DEBUG_DIR / "zhihui_08_ERROR_登录失败.png")
                return False

        except Exception as e:
            logger.error(f"调试过程出错: {e}")
            await page.screenshot(path=DEBUG_DIR / "zhihui_99_EXCEPTION.png")
            return False
        finally:
            logger.info("等待10秒供查看...")
            await asyncio.sleep(10)
            await browser.close()


async def debug_rongda_login():
    """调试融达数据登录"""
    logger.info("=" * 70)
    logger.info("开始调试融达数据登录")
    logger.info("=" * 70)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()

        try:
            # 步骤1: 访问页面
            logger.info("步骤1: 访问登录页面")
            await page.goto("https://dt.rongdaqh.com/finance_and_economics/calendar",
                          wait_until="domcontentloaded", timeout=60000)
            await page.screenshot(path=DEBUG_DIR / "rongda_01_初始页面.png")
            await asyncio.sleep(3)

            # 步骤2: 查找并点击登录标签页
            logger.info("步骤2: 查找登录标签页")
            tab_selectors = [
                "text=账号密码登录",
                "text=密码登录",
                "[class*='tab']:has-text('密码')",
                "[role='tab']:has-text('密码')",
            ]

            for selector in tab_selectors:
                try:
                    tab = await page.query_selector(selector)
                    if tab:
                        logger.info(f"找到登录标签页: {selector}")
                        await tab.click()
                        await asyncio.sleep(1)
                        break
                except:
                    pass

            await page.screenshot(path=DEBUG_DIR / "rongda_02_点击标签页后.png")

            # 步骤3: 查找输入框
            logger.info("步骤3: 查找输入框")

            # 等待输入框变为可见
            await asyncio.sleep(2)

            username_input = None
            password_input = None

            # 查找所有input，包括隐藏的
            all_inputs = await page.query_selector_all("input")
            logger.info(f"页面共有 {len(all_inputs)} 个input元素")

            for input_elem in all_inputs:
                try:
                    input_type = await input_elem.get_attribute("type")
                    placeholder = await input_elem.get_attribute("placeholder")
                    is_visible = await input_elem.is_visible()

                    logger.info(f"  - input type={input_type}, placeholder={placeholder}, visible={is_visible}")

                    if is_visible:
                        if input_type in ["text", "tel"] and not username_input:
                            username_input = input_elem
                            logger.info(f"  ✓ 设为用户名输入框")
                        elif input_type == "password" and not password_input:
                            password_input = input_elem
                            logger.info(f"  ✓ 设为密码输入框")
                except:
                    pass

            if not username_input or not password_input:
                logger.error(f"❌ 输入框不完整: 用户名={username_input is not None}, 密码={password_input is not None}")
                await page.screenshot(path=DEBUG_DIR / "rongda_03_ERROR_输入框不完整.png")

                # 保存页面HTML
                html_content = await page.content()
                with open(DEBUG_DIR / "rongda_page_source.html", 'w', encoding='utf-8') as f:
                    f.write(html_content)
                logger.info(f"页面HTML已保存到: {DEBUG_DIR / 'rongda_page_source.html'}")

                return False

            # 步骤4: 填写登录信息
            logger.info("步骤4: 填写登录信息")
            await username_input.fill("18321399574")
            await asyncio.sleep(0.5)
            await password_input.fill("yi2013405")
            await asyncio.sleep(0.5)
            await page.screenshot(path=DEBUG_DIR / "rongda_04_填写完成.png")

            # 步骤5: 点击登录按钮
            logger.info("步骤5: 点击登录按钮")
            login_button_selectors = [
                "button:has-text('登录')",
                "button:has-text('登錄')",
                "button[type='submit']",
                "[class*='login-btn']",
            ]

            login_button_clicked = False
            for selector in login_button_selectors:
                try:
                    btn = await page.query_selector(selector)
                    if btn and await btn.is_visible():
                        logger.info(f"找到登录按钮: {selector}")
                        await btn.click()
                        login_button_clicked = True
                        break
                except:
                    pass

            if not login_button_clicked:
                logger.info("未找到登录按钮，尝试按Enter提交")
                await password_input.press("Enter")

            await asyncio.sleep(5)
            await page.screenshot(path=DEBUG_DIR / "rongda_05_登录后.png")

            # 步骤6: 检查登录状态
            logger.info("步骤6: 检查登录状态")
            current_url = page.url
            logger.info(f"当前URL: {current_url}")

            cookies = await context.cookies()
            logger.info(f"当前cookies数量: {len(cookies)}")

            if len(cookies) > 5:
                logger.info("✅ 登录成功！保存cookies...")
                cookies_file = COOKIES_DIR / "rongda_cookies.json"
                with open(cookies_file, 'w', encoding='utf-8') as f:
                    json.dump(cookies, f, ensure_ascii=False, indent=2)
                logger.info(f"✅ Cookies已保存: {cookies_file} (共{len(cookies)}个)")
                return True
            else:
                logger.error("❌ 登录可能失败")
                await page.screenshot(path=DEBUG_DIR / "rongda_06_ERROR_登录失败.png")
                return False

        except Exception as e:
            logger.error(f"调试过程出错: {e}")
            await page.screenshot(path=DEBUG_DIR / "rongda_99_EXCEPTION.png")
            return False
        finally:
            logger.info("等待10秒供查看...")
            await asyncio.sleep(10)
            await browser.close()


async def main():
    """主函数"""
    logger.info("\n\n")
    logger.info("=" * 70)
    logger.info("🔍 登录自动化调试工具")
    logger.info("=" * 70)
    logger.info(f"截图将保存到: {DEBUG_DIR}")
    logger.info("=" * 70)

    # 测试智汇期讯
    success1 = await debug_zhihui_login()

    # 等待3秒
    await asyncio.sleep(3)

    # 测试融达数据
    success2 = await debug_rongda_login()

    logger.info("\n" + "=" * 70)
    logger.info("调试结果:")
    logger.info(f"  智汇期讯: {'✅ 成功' if success1 else '❌ 失败'}")
    logger.info(f"  融达数据: {'✅ 成功' if success2 else '❌ 失败'}")
    logger.info("=" * 70)
    logger.info(f"\n请查看截图了解详情: {DEBUG_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
