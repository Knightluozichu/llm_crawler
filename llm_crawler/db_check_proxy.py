import requests

def check_proxy(proxy):
    try:
        # 配置代理
        proxies = {
            'http': f'http://{proxy}',
            'https': f'http://{proxy}'
        }
        # 发送请求，设置超时时间为 5 秒
        response = requests.get('http://httpbin.org/get', proxies=proxies, timeout=5)
        # 检查响应状态码
        if response.status_code == 200:
            return True
        else:
            return False
    except requests.RequestException:
        return False

def main():
    valid_proxies = []
    # 读取代理文件
    with open('valid_proxies.txt', 'r') as file:
        proxies = file.read().splitlines()
    # 检查每个代理
    for proxy in proxies:
        if check_proxy(proxy):
            valid_proxies.append(proxy)
            print(f'{proxy} 是有效的代理。')
        else:
            print(f'{proxy} 是无效的代理。')
    # 打印有效的代理列表
    print('\n有效的代理列表：')
    for proxy in valid_proxies:
        print(proxy)

if __name__ == "__main__":
    main()