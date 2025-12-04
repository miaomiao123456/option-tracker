import asyncio
from playwright.async_api import async_playwright

async def inspect_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=1000)
        page = await browser.new_page()
        
        print("正在打开智汇期讯首页...")
        await page.goto("https://hzzhqx.com/home")
        
        print("\n等待10秒,请查看页面...")
        await asyncio.sleep(10)
        
        # 获取页面HTML
        content = await page.content()
        with open("zhihui_home_page.html", "w", encoding="utf-8") as f:
            f.write(content)
        print("页面HTML已保存到 zhihui_home_page.html")
        
        # 查找所有input
        inputs = await page.query_selector_all("input")
        print(f"\n找到 {len(inputs)} 个input元素:")
        for i, inp in enumerate(inputs):
            placeholder = await inp.get_attribute("placeholder")
            input_type = await inp.get_attribute("type")
            input_class = await inp.get_attribute("class")
            print(f"  {i+1}. type={input_type}, placeholder={placeholder}, class={input_class}")
        
        print("\n按Enter继续...")
        input()
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_page())
