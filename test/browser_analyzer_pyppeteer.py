import asyncio
from pyppeteer import launch
import json

async def main():
    # 启动浏览器
    browser = await launch(headless=False)  # 非无头模式，让用户可以看到浏览器
    page = await browser.newPage()
    
    # 设置用户代理
    await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15')
    
    # 设置Cookie
    cookie = "xq_a_token=646296e3dc9581be9ca594e0177e818eef6e6977; xq_r_token=d0bcc78d11b5fdc4f3c6b2e6dd180ed793502600"
    cookies = []
    for cookie_item in cookie.split('; '):
        name, value = cookie_item.split('=', 1)
        cookies.append({
            'name': name,
            'value': value,
            'domain': 'xueqiu.com',
            'path': '/',
            'expires': -1
        })
    
    await page.setCookie(*cookies)
    
    print("浏览器已启动，正在打开雪球网站...")
    
    # 打开雪球网站
    await page.goto('https://xueqiu.com')
    await page.waitFor(3000)  # 等待页面加载
    
    print("\n已打开雪球网站")
    print("请确认是否已登录")
    print("登录完成后，按Enter键继续...")
    input()
    
    # 监听网络请求
    requests = []
    
    async def log_request(request):
        url = request.url
        if 'xueqiu.com' in url and ('hot' in url or 'list' in url or 'timeline' in url):
            requests.append({
                'url': url,
                'method': request.method,
                'headers': dict(request.headers),
                'postData': request.postData
            })
    
    # 开启请求监听
    page.on('request', log_request)
    
    print("\n正在进入热门页面...")
    
    # 尝试点击热门标签
    try:
        await page.waitForSelector('a[href="/hot"]', timeout=10000)
        await page.click('a[href="/hot"]')
        await page.waitFor(3000)
        
        print(f"\n当前URL: {page.url}")
        print("\n请在浏览器中点击你想要的列表（比如'专栏'）")
        print("点击后，按Enter键继续...")
        input()
        
        # 等待网络请求完成
        await page.waitFor(2000)
        
        # 打印找到的API请求
        print("\n" + "="*80)
        print("找到的相关API请求：")
        print("="*80)
        
        for i, req in enumerate(requests, 1):
            print(f"\n{i}. URL: {req['url']}")
            print(f"   方法: {req['method']}")
            if req['postData']:
                print(f"   数据: {req['postData']}")
        
        print("\n" + "="*80)
        print("分析完成！")
        print("请查看上面的API请求，找到与热门页面相关的API")
        print("告诉我你选择的API URL")
        
    except Exception as e:
        print(f"操作失败: {str(e)}")
        print("请手动操作浏览器，然后查看开发者工具中的网络请求")
    finally:
        # 等待用户查看
        print("\n按Enter键关闭浏览器...")
        input()
        await browser.close()
        print("浏览器已关闭")

if __name__ == "__main__":
    asyncio.run(main())
