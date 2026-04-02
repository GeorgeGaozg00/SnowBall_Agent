
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
            
            # 尝试保存完整响应到文件
            filename = f'test_{name.replace(" ", "_")}.json'
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"\n完整响应已保存到: {filename}")
            
            # 打印前几篇文章的标题
            if "items" in data:
                items = data.get("items", [])
                print(f"\n找到 {len(items)} 个项目:")
                for i, item in enumerate(items[:5]):
                    if "original_status" in item:
                        article = item["original_status"]
                        print(f"  {i+1}. {article.get('title', '无标题')[:50]}")
                    elif "title" in item:
                        print(f"  {i+1}. {item.get('title', '无标题')[:50]}")
            elif "list" in data:
                articles = data.get("list", [])
                print(f"\n找到 {len(articles)} 篇文章:")
                for i, article in enumerate(articles[:5]):
                    if "title" in article:
                        print(f"  {i+1}. {article.get('title', '无标题')[:50]}")
            
            return data
        else:
            print(f"响应内容: {resp.text[:500]}")
            return None
            
    except Exception as e:
        print(f"请求失败: {str(e)}")
        return None

print("="*80)
print("雪球热门页面API详细测试")
print("="*80)
print("\n请在浏览器中打开雪球网站，点击'热门'页面")
print("然后按F12打开开发者工具，查看Network标签")
print("找到相关的API请求，告诉我们URL和参数")
print("\n现在先测试所有可能的热门相关API...\n")

# 测试各种可能的热门API
test_api("https://xueqiu.com/statuses/hot/list.json", {"count": 20, "page": 1}, "热门列表1")
test_api("https://xueqiu.com/v4/statuses/public_timeline_by_category.json", {"since_id": -1, "max_id": -1, "count": 20, "category": -1}, "公共时间线-全部")
test_api("https://xueqiu.com/v4/statuses/public_timeline_by_category.json", {"since_id": -1, "max_id": -1, "count": 20, "category": 6}, "公共时间线-热门")
test_api("https://xueqiu.com/v4/statuses/public_timeline_by_category.json", {"since_id": -1, "max_id": -1, "count": 20, "category": 105}, "公共时间线-专栏")
test_api("https://xueqiu.com/v4/statuses/public_timeline_by_category.json", {"since_id": -1, "max_id": -1, "count": 20, "category": 111}, "公共时间线-问答")
test_api("https://xueqiu.com/statuses/hot/stock_list.json", {"count": 20}, "热门股票")
test_api("https://xueqiu.com/v4/statuses/hot/list.json", {"count": 20}, "热门列表2")
test_api("https://xueqiu.com/api/statuses/hot/list", {"count": 20}, "热门列表3")

print("\n" + "="*80)
print("测试完成！请查看生成的JSON文件")
print("或者在浏览器中查看Network标签，找到热门页面的API")
print("="*80)
