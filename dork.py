#!/usr/bin/env python3
# encoding: utf-8

import threading
import tempfile
import requests
import random
import sys
import time
from googlesearch import search  # type: ignore
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
temp_file = None
temp_path = ""
print_lock = threading.Lock()

# 设置 HTTP 代理环境变量，使 googlesearch 使用代理
os.environ['HTTP_PROXY'] = "http://127.0.0.1:7890"
os.environ['HTTPS_PROXY'] = "http://127.0.0.1:7890"

# ========== CONFIG ==========
CLASH_API_BASE = "http://127.0.0.1:9090"
CLASH_API_SECRET = ""  # 将在运行时输入
TEST_URL = "https://www.google.com"
MAX_RETRIES = 5
SEARCH_PAUSE = 2
THREADS = 5
# ============================

def get_headers():
    return {
        "Content-Type": "application/json",
        **({"Authorization": f"Bearer {CLASH_API_SECRET}"} if CLASH_API_SECRET else {})
    }

def list_proxy_groups():
    try:
        response = requests.get(f"{CLASH_API_BASE}/proxies", headers=get_headers(), timeout=5)
        data = response.json()
        return [k for k, v in data['proxies'].items() if 'all' in v]
    except Exception as e:
        print(f"[!] 获取代理组失败: {e}")
        return []

def choose_proxy_group(groups):
    print("\n[+] 可切换的代理组：")
    for idx, group in enumerate(groups):
        print(f"{idx + 1}. {group}")
    while True:
        choice = input("请输入要使用的代理组编号: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(groups):
            return groups[int(choice) - 1]
        print("⚠️ 输入无效，请重试。")

def get_all_proxies(group):
    try:
        response = requests.get(f"{CLASH_API_BASE}/proxies", headers=get_headers(), timeout=5).json()
        return response['proxies'][group]['all']
    except Exception as e:
        print(f"[!] 获取代理列表失败: {e}")
        return []

def switch_proxy(group, proxy_name):
    try:
        r = requests.put(f"{CLASH_API_BASE}/proxies/{group}", headers=get_headers(), json={"name": proxy_name})
        return r.status_code == 204
    except Exception as e:
        print(f"[!] 切换代理失败: {e}")
        return False

def get_current_clash_proxy(group):
    try:
        response = requests.get(f"{CLASH_API_BASE}/proxies/{group}", headers=get_headers(), timeout=5).json()
        return response.get("now", "未知")
    except Exception:
        return "未知"

def test_proxy(group, proxy_name):
    if switch_proxy(group, proxy_name):
        time.sleep(1)
        try:
            response = requests.get(TEST_URL, timeout=5)
            return proxy_name if response.status_code == 200 else None
        except:
            return None
    return None

def get_working_proxies(group, proxies):
    print(f"🌍 正在并发检测代理可用性，共 {len(proxies)} 个节点...")
    working = []
    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        future_map = {executor.submit(test_proxy, group, proxy): proxy for proxy in proxies}
        for future in as_completed(future_map):
            result = future.result()
            if result:
                print(f"✅ 可用节点: {result}")
                working.append(result)
    if not working:
        print("❌ 没有可用节点，请检查 Clash 或配置。")
    return working

def logger(logfile, data):
    if logfile:
        with open(logfile, "a", encoding="utf-8") as f:
            f.write(str(data) + "\n")

def get_current_ip():
    try:
        proxies = {
            "http": "http://127.0.0.1:7890",
            "https": "http://127.0.0.1:7890"
        }
        ip = requests.get("https://api.ipify.org", proxies=proxies, timeout=5).text.strip()
        return ip
    except Exception:
        return "未知 IP"

def perform_search(group, dork, amount, proxies, logfile):
    for attempt in range(MAX_RETRIES):
        proxy = random.choice(proxies)
        switch_proxy(group, proxy)
        time.sleep(1)
        current_used = get_current_clash_proxy(group)
        ip = get_current_ip()

        with print_lock:
            print(f"🌐 请求节点 [{proxy}]，当前使用节点 [{current_used}]，出口IP [{ip}] \n♻️ 搜索: {dork}")
            try:
                results = search(
                    term=dork,
                    num_results=int(amount),
                    sleep_interval=SEARCH_PAUSE
                )
                valid_results = [url for url in results if url.startswith("http")]

                if valid_results:
                    logger(logfile, f"{dork}")
                    for i, url in enumerate(valid_results, 1):
                        print(f"[+] {i}: {url}")
                        logger(logfile, f"{url}")
                else:
                    print("[-] 未找到有效结果。")
                print("\n")
                logger(logfile, "\n")
                return
            except Exception as e:
                print(f"[!] 搜索失败（尝试 {attempt+1}/{MAX_RETRIES}）: {e}")
                time.sleep(2)
    print(f"[×] 放弃搜索: {dork}")

def replace_domain_in_dork(dork_line, domain):
    """将 dork 行中的 mgm.mo 替换为指定域名"""
    return dork_line.replace("mgm.mo", domain.strip())

def main():
    global CLASH_API_BASE, CLASH_API_SECRET
    print("=== Dorks- 并发搜索 + Clash 节点自动检测 ===\n")

    clash_host = input("[+] 输入 Clash API 地址（默认 http://127.0.0.1:9090）: ").strip()
    if clash_host:
        CLASH_API_BASE = clash_host  # 使用自定义地址
    else:
        CLASH_API_BASE = "http://127.0.0.1:9090"  # 默认值
    CLASH_API_SECRET = input("[+] 如果有 Clash API 密钥，请输入（留空则跳过）: ").strip()

    proxy_groups = list_proxy_groups()
    if not proxy_groups:
        print("[×] 获取代理组失败，程序终止。")
        return

    group = choose_proxy_group(proxy_groups)

    domains_file = input("\n[+] 输入 domain 文件路径: ").strip()
    dork_file = input("\n[+] 输入 dork 文件路径: ").strip()
    try:
        # 创建临时文件
        temp_file = tempfile.NamedTemporaryFile(
            mode='w', 
            delete=False,
            encoding='utf-8',
            suffix='.txt'
        )
        temp_path = temp_file.name
        print(f"[*] 创建临时文件: {temp_path}")

        # 读取域名列表
        with open(domains_file, "r") as f:
            domains = [line.strip() for line in f if line.strip()]

        # 读取 dork 模板
        with open(dork_file, "r") as f:
            dork_template = f.readlines()

        # 为每个域名生成替换后的 dork
        for domain in domains:
            for line in dork_template:
                replaced_line = replace_domain_in_dork(line, domain)
                temp_file.write(replaced_line)

        # 关闭文件确保内容写入磁盘
        temp_file.close()
        
        print(f"[*] 临时文件内容已生成，路径: {temp_path}")
        
        # 这里可以添加处理临时文件的代码
        # 例如：调用其他函数处理生成的 dork
        # 处理完成后文件会被自动删除


        with open(temp_path, "r", encoding="utf-8") as f:

            dorks = [line.strip() for line in f if line.strip()]


        amount = input("[+] 每个 Dork 搜索多少条结果？(默认10): ").strip()
        amount = int(amount) if amount.isdigit() else 10

        save = input("[+] 是否保存结果到文件？(Y/N): ").strip().lower()
        logfile = input("[+] 日志文件名: ").strip() if save == 'y' else None

        proxies = get_all_proxies(group)
        if not proxies:
            print("[×] 无法获取代理列表。")
            return

        working_proxies = get_working_proxies(group, proxies)
        if not working_proxies:
            return

        print(f"\n[✓] 共 {len(working_proxies)} 个可用节点，开始执行 Dork 搜索...\n")

        with ThreadPoolExecutor(max_workers=THREADS) as executor:
            futures = [executor.submit(perform_search, group, dork, amount, working_proxies, logfile) for dork in dorks]
            for future in as_completed(futures):
                future.result()

        print("\n[*] 所有 Dork 搜索完成！")
    except FileNotFoundError as e:
        print(f"错误: 文件不存在 - {e.filename}")
    except Exception as e:
        print(f"发生错误: {str(e)}")
    finally:
            # 确保删除临时文件
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                    print(f"\n[*] 已清理临时文件: {temp_path}")
                except Exception as e:
                    print(f"[!] 删除临时文件失败: {str(e)}")

if __name__ == "__main__":
    main()

