"""
从 HTML 生成 4K (3840x2160) 500 DPI 透明背景 PNG
支持 Playwright 和 Selenium 两种方式
"""
import os
import sys

def try_playwright():
    """尝试使用 Playwright"""
    try:
        from playwright.async_api import async_playwright
        import asyncio
        
        async def generate():
            html_file = "style6_4k.html"
            output_file = "nozomi_hikari_final_v2_no_shadow.png"
            
            if not os.path.exists(html_file):
                print(f"错误：找不到文件 {html_file}")
                return
            
            async with async_playwright() as p:
                print("启动浏览器 (Playwright)...")
                browser = await p.chromium.launch()
                page = await browser.new_page()
                
                # 设置视口大小为 4K
                await page.set_viewport_size({"width": 3840, "height": 2160})
                
                # 加载 HTML 文件
                html_path = os.path.abspath(html_file)
                file_url = f"file:///{html_path.replace(os.sep, '/')}"
                print(f"加载文件: {file_url}")
                await page.goto(file_url)
                
                # 等待字体和内容加载
                print("等待内容加载...")
                await page.wait_for_timeout(3000)
                
                # 截图，omit_background=True 生成透明背景
                print(f"正在截图并保存到: {output_file}")
                # 确保背景透明
                await page.evaluate("document.body.style.backgroundColor = 'transparent'")
                await page.screenshot(
                    path=output_file,
                    omit_background=True,  # 透明背景
                    full_page=True
                )
                
                await browser.close()
                print(f"完成！图片已保存至: {output_file}")
                print(f"分辨率: 3840x2160")
                print("注意：PNG 的 DPI 信息需要在保存后单独设置")
        
        asyncio.run(generate())
        return True
    except ImportError:
        return False
    except Exception as e:
        print(f"Playwright 错误: {e}")
        return False

def try_selenium():
    """尝试使用 Selenium"""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        import time
        
        html_file = "style6_4k.html"
        output_file = "nozomi_hikari_final_v2_no_shadow.png"
        
        if not os.path.exists(html_file):
            print(f"错误：找不到文件 {html_file}")
            return False
        
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=3840,2160')
        chrome_options.add_argument('--disable-gpu')
        
        print("启动浏览器 (Selenium)...")
        driver = webdriver.Chrome(options=chrome_options)
        
        html_path = os.path.abspath(html_file)
        file_url = f"file:///{html_path.replace(os.sep, '/')}"
        print(f"加载文件: {file_url}")
        driver.get(file_url)
        
        print("等待内容加载...")
        time.sleep(3)
        
        driver.set_window_size(3840, 2160)
        
        print(f"正在截图并保存到: {output_file}")
        driver.save_screenshot(output_file)
        
        driver.quit()
        print(f"完成！图片已保存至: {output_file}")
        print(f"分辨率: 3840x2160")
        print("注意：PNG 的 DPI 信息需要在保存后单独设置")
        return True
    except ImportError:
        return False
    except Exception as e:
        print(f"Selenium 错误: {e}")
        return False

def set_dpi_with_pil():
    """使用 PIL 设置 PNG 的 DPI 信息"""
    try:
        from PIL import Image
        
        output_file = "nozomi_hikari_final_v2_no_shadow.png"
        if not os.path.exists(output_file):
            print(f"错误：找不到文件 {output_file}")
            return False
        
        print("设置 PNG DPI 为 500...")
        img = Image.open(output_file)
        
        # 保存时设置 DPI
        img.save(output_file, dpi=(500, 500))
        print(f"已设置 DPI 为 500")
        return True
    except ImportError:
        print("警告：PIL 未安装，无法设置 DPI")
        return False
    except Exception as e:
        print(f"设置 DPI 时出错: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("生成 4K (3840x2160) 500 DPI 透明背景 PNG")
    print("=" * 50)
    
    # 尝试 Playwright
    if try_playwright():
        set_dpi_with_pil()
        sys.exit(0)
    
    # 尝试 Selenium
    if try_selenium():
        set_dpi_with_pil()
        sys.exit(0)
    
    # 都失败了
    print("\n" + "=" * 50)
    print("错误：未找到可用的浏览器自动化工具")
    print("=" * 50)
    print("\n请安装以下任一工具：")
    print("\n方案 1 - Playwright (推荐):")
    print("  pip install playwright")
    print("  playwright install chromium")
    print("\n方案 2 - Selenium:")
    print("  pip install selenium")
    print("  (需要下载 ChromeDriver)")
    print("\n或者手动打开 style6_4k.html 并截图")
    sys.exit(1)
