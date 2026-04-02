
import requests
import json

# 配置
XUEQIU_COOKIE = "xq_a_token=646296e3dc9581be9ca594e0177e818eef6e6977; xq_r_token=d0bcc78d11b5fdc4f3c6b2e6dd180ed793502600"

headers = {
    "Cookie": XUEQIU_COOKIE,
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Accept": "application/json",
    "Referer": "https://xueqiu.com",
    "X-Requested-With": "XMLHttpRequest"
}

def test_api(url, params=None, name="测试API"):
    """测试一个API并打印结果"""
    print(f"\n{'='*80}")
    print(f"测试: {name}")
    print(f"URL: {url}")
    if params:
        print(f"参数: {params}")
    print(f"{'='*80}")
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"状态码: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"\n响应结构: {list(data.keys())}")
            
            # 打印前200个字符
            print(f"\n响应内容预览: {json.dumps(data, ensure_ascii=False)[:500]}...")
            
            # 尝试保存完整响应到文件
            with open(f'test_{name.replace(" ", "_")}.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"\n完整响应已保存到: test_{name.replace(' ', '_')}.json")
            
            return data
        else:
            print(f"响应内容: {resp.text[:500]}")
            return None
            
    except Exception as e:
        print(f"请求失败: {str(e)}")
        return None

print("="*80)
print("雪球热门页面API测试工具")
print("="*80)
print("\n请在浏览器中打开雪球网站，点击'热门'页面")
print("然后按F12打开开发者工具，查看Network标签")
print("找到相关的API请求，告诉我们URL和参数")
print("\n或者，我先尝试一些可能的API...")

# 测试一些可能的热门页面API
test_api("https://xueqiu.com/statuses/hot/list.json", {"count": 10, "page": 1}, "热门列表")
test_api("https://xueqiu.com/v4/statuses/public_timeline_by_category.json", {"since_id": -1, "max_id": -1, "count": 20, "category": -1}, "公共时间线")
test_api("https://xueqiu.com/v4/statuses/user_timeline.json", {"user_id": 1, "count": 10}, "用户时间线")
test_api("https://xueqiu.com/statuses/hot/stock_list.json", {"count": 20}, "热门股票列表")
test_api("https://xueqiu.com/v4/stock/quote.json", {"code": "SH000001"}, "股票行情")

print("\n" + "="*80)
print("测试完成！请查看生成的JSON文件")
print("或者在浏览器中查看Network标签，找到热门页面的API")
print("="*80)
