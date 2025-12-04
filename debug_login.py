import asyncio
from playwright.async_api import async_playwright

async def debug_login():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # 可视化模式
        page = await browser.new_page()
        
        print("正在打开智汇期讯登录页...")
        await page.goto("https://hzzhqx.com/login")
        
        print("等待30秒,请手动查看页面结构...")
        await asyncio.sleep(30)
        
        # 尝试查找所有input元素
        inputs = await page.query_selector_all("input")
        print(f"\n找到 {len(inputs)} 个input元素:")
        for i, inp in enumerate(inputs):
            placeholder = await inp.get_attribute("placeholder")
            input_type = await inp.get_attribute("type")
            input_name = await inp.get_attribute("name")
            input_id = await inp.get_attribute("id")
            print(f"  {i+1}. type={input_type}, placeholder={placeholder}, name={name}, id={input_id}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_login())
