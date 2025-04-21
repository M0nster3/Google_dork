import requests
import time

CLASH_API = "http://127.0.0.1:9182"
CLASH_API_SECRET = "821409689"  # 设置为 Clash 配置中的 secret，如果没有就留空

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {CLASH_API_SECRET}" if CLASH_API_SECRET else None
}
HEADERS = {k: v for k, v in HEADERS.items() if v is not None}

def list_proxy_groups():
    resp = requests.get(f"{CLASH_API}/proxies", headers=HEADERS)
    data = resp.json()
    groups = []
    for name, proxy in data["proxies"].items():
        if "all" in proxy:  # 可切换的分组
            groups.append(name)
    return groups

def choose_group(groups):
    print("📦 可用代理组列表：")
    for idx, name in enumerate(groups):
        print(f"{idx + 1}. {name}")
    while True:
        try:
            choice = int(input("请输入要使用的代理组编号："))
            if 1 <= choice <= len(groups):
                return groups[choice - 1]
            else:
                print("⚠️ 编号超出范围，请重新输入。")
        except ValueError:
            print("⚠️ 请输入数字。")

def get_proxies(group):
    resp = requests.get(f"{CLASH_API}/proxies", headers=HEADERS)
    data = resp.json()
    if group not in data["proxies"]:
        raise ValueError(f"找不到代理组 {group}")
    nodes = data["proxies"][group]["all"]
    return nodes

def switch_proxy(group, node_name):
    print(f"🔁 正在切换到节点: {node_name}")
    resp = requests.put(
        f"{CLASH_API}/proxies/{group}",
        json={"name": node_name},
        headers=HEADERS
    )
    if resp.status_code == 204:
        print(f"✅ 节点切换成功: {node_name}")
    else:
        print(f"❌ 节点切换失败: {node_name}")

def do_task():
    try:
        proxies = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}
        r = requests.get("http://httpbin.org/ip", proxies=proxies, timeout=10)
        print("🌐 当前 IP:", r.json()["origin"])
    except Exception as e:
        print("⚠️ 请求失败:", e)

def main():
    groups = list_proxy_groups()
    if not groups:
        print("❌ 未找到可切换的代理组。")
        return

    group = choose_group(groups)
    nodes = get_proxies(group)
    print(f"\n🌍 共获取到 {len(nodes)} 个节点: {nodes}\n")

    for node in nodes:
        try:
            switch_proxy(group, node)
            time.sleep(2)  # 等待代理生效
            do_task()
        except Exception as e:
            print(f"⚠️ 节点 {node} 任务失败: {e}")
        print("-" * 40)

if __name__ == "__main__":
    main()
