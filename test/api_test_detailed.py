import requests
import json

# 你的Cookie
XUEQIU_COOKIE = "xq_a_token=646296e3dc9581be9ca594e0177e818eef6e6977; xq_r_token=d0bcc78d11b5fdc4f3c6b2e6dd180ed793502600"

# 请求头
headers = {
    "Cookie": XUEQIU_COOKIE,
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Accept": "application/json",
    "Referer": "https://xueqiu.com",
    "X-Requested-With": "XMLHttpRequest"
}

def test_api(url, params=None, name="测试API"):
    """测试一个API并打印详细结果"""
    print(f"\n{'='*80}")
    print(f"测试: {name}")
    print(f"URL: {url}")
    if params:
        print(f"参数: {params}")
    print(f"{'='*80}")
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"响应结构: {list(data.keys())}")
                
                # 保存响应到文件
                filename = f"test_{name.replace(' ', '_')}.json"
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"完整响应已保存到: {filename}")
                
                # 详细打印文章列表
                print("\n文章列表:")
                print("-"*80)
                
                if "items" in data:
                    items = data.get("items", [])
                    print(f"共找到 {len(items)} 篇文章:")
                    for i, item in enumerate(items, 1):
                        if "original_status" in item:
                            article = item["original_status"]
                            title = article.get("title", "无标题")
                            user = article.get("user", {})
                            screen_name = user.get("screen_name", "未知用户")
                            print(f"{i}. {title} - {screen_name}")
                elif "list" in data:
                    articles = data.get("list", [])
                    print(f"共找到 {len(articles)} 篇文章:")
                    for i, item in enumerate(articles, 1):
                        if "data" in item:
                            try:
                                data_str = item["data"]
                                article_data = json.loads(data_str)
                                title = article_data.get("title", article_data.get("text", "无标题"))
                                # 提取用户信息
                                screen_name = article_data.get("screen_name", "未知用户")
                                print(f"{i}. {title} - {screen_name}")
                            except Exception as e:
                                # 如果解析失败，尝试其他方式
                                print(f"{i}. 无法解析文章数据")
            except Exception as e:
                print(f"解析JSON失败: {e}")
                print(f"响应内容: {response.text[:500]}...")
        else:
            print(f"响应内容: {response.text}")
    except Exception as e:
        print(f"请求失败: {e}")

print("雪球热门页面API详细测试工具")
print("='*80")
print("此工具将测试多个可能的热门页面API")
print("请查看每个API返回的文章列表，找到与你在页面上看到的一致的那个")
print("='*80")

# 测试各种可能的热门API
test_api("https://xueqiu.com/statuses/hot/list.json", {"count": 20, "page": 1}, "热门列表")
test_api("https://xueqiu.com/v4/statuses/public_timeline_by_category.json", {"since_id": -1, "max_id": -1, "count": 20, "category": -1}, "公共时间线-全部")
test_api("https://xueqiu.com/v4/statuses/public_timeline_by_category.json", {"since_id": -1, "max_id": -1, "count": 20, "category": 6}, "公共时间线-热门")
test_api("https://xueqiu.com/v4/statuses/public_timeline_by_category.json", {"since_id": -1, "max_id": -1, "count": 20, "category": 105}, "公共时间线-专栏")
test_api("https://xueqiu.com/v4/statuses/public_timeline_by_category.json", {"since_id": -1, "max_id": -1, "count": 20, "category": 111}, "公共时间线-问答")

print("\n" + "="*80)
print("测试完成！")
print("请查看上面的文章列表，找到与你在页面上看到的一致的API")
print("然后告诉我该API的名称，我会更新程序")
print("="*80)
