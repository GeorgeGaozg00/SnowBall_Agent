from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import time
import json

# 配置Chrome浏览器，启用网络监控
chrome_options = Options()
# 不使用无头模式，让用户可以看到浏览器
# chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

# 启用性能日志，捕获网络请求
caps = DesiredCapabilities.CHROME
caps['goog:loggingPrefs'] = {'performance': 'ALL'}

driver = webdriver.Chrome(options=chrome_options, desired_capabilities=caps)
print("浏览器已启动，正在打开雪球网站...")

def extract_requests(logs):
    """从性能日志中提取网络请求"""
    requests = []
    for entry in logs:
        try:
            message = json.loads(entry['message'])
            message = message['message']
            if message['method'] == 'Network.requestWillBeSent':
                request = message['params']['request']
                url = request['url']
                if 'xueqiu.com' in url and ('hot' in url or 'list' in url or 'timeline' in url):
                    requests.append({
                        'url': url,
                        'method': request['method'],
                        'headers': request.get('headers', {}),
                        'postData': request.get('postData', '')
                    })
        except:
            pass
    return requests

try:
    # 打开雪球网站
    driver.get("https://xueqiu.com")
    print("\n已打开雪球网站")
    print("请手动登录雪球账号")
    print("登录完成后，按Enter键继续...")
    input()
    
    print("\n登录成功！正在进入热门页面...")
    
    # 尝试点击热门标签
    try:
        hot_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "热门"))
        )
        print("找到热门标签，点击进入...")
        hot_tab.click()
        time.sleep(3)
        
        print(f"\n当前URL: {driver.current_url}")
        print("\n请在浏览器中点击你想要的列表（比如'专栏'）")
        print("点击后，按Enter键继续...")
        input()
        
        # 提取网络请求
        logs = driver.get_log('performance')
        requests = extract_requests(logs)
        
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
    driver.quit()
    print("浏览器已关闭")
