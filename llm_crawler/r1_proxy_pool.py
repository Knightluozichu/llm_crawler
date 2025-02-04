import time
import random
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# 初始化 ChromeDriver，采用无头模式和其他反爬措施
def init_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")               # 无头模式
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36")
    # 使用 Service 对象来指定 chromedriver 路径
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

# 从 89ip.cn 抓取代理
def fetch_proxies_89ip(driver, page):
    url = f"https://www.89ip.cn/index_{page}.html"
    print(f"正在抓取 89ip: {url}")
    driver.get(url)
    time.sleep(random.uniform(3, 5))
    proxies = []
    try:
        rows = driver.find_elements(By.XPATH, '//table/tbody/tr')
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) >= 2:
                ip = cols[0].text.strip()
                port = cols[1].text.strip()
                proxies.append(f"{ip}:{port}")
    except Exception as e:
        print("抓取 89ip 代理异常：", e)
    return proxies

# 从 kuaidaili 抓取代理
def fetch_proxies_kuaidaili(driver, page):
    url = f"https://www.kuaidaili.com/free/dps/{page}/"
    print(f"正在抓取 快代理: {url}")
    driver.get(url)
    time.sleep(random.uniform(3, 5))
    proxies = []
    try:
        rows = driver.find_elements(By.XPATH, '//table/tbody/tr')
        for row in rows:
            ip = row.find_element(By.XPATH, './td[1]').text.strip()
            port = row.find_element(By.XPATH, './td[2]').text.strip()
            proxies.append(f"{ip}:{port}")
    except Exception as e:
        print("抓取 快代理 异常：", e)
    return proxies

# 从 iphaiwai 抓取代理
def fetch_proxies_iphaiwai(driver, page):
    url = f"https://www.iphaiwai.com/free/{page}/"
    print(f"正在抓取 iphaiwai: {url}")
    driver.get(url)
    time.sleep(random.uniform(3, 5))
    proxies = []
    try:
        rows = driver.find_elements(By.XPATH, '//table/tbody/tr')
        for row in rows:
            ip = row.find_element(By.XPATH, './td[1]').text.strip()
            port = row.find_element(By.XPATH, './td[2]').text.strip()
            proxies.append(f"{ip}:{port}")
    except Exception as e:
        print("抓取 iphaiwai 异常：", e)
    return proxies

# 检查代理是否有效
def check_proxy(proxy):
    proxies = {
        "http": f"http://{proxy}",
        "https": f"http://{proxy}"
    }
    try:
        response = requests.get("http://httpbin.org/ip", proxies=proxies, timeout=5)
        if response.status_code == 200:
            print(f"代理 {proxy} 可用")
            return True
    except Exception as e:
        print(f"代理 {proxy} 检查失败：{e}")
    return False

def main():
    driver = init_driver()
    valid_proxies = set()
    pages = range(1, 3)
    
    for page in pages:
        proxies_89ip = fetch_proxies_89ip(driver, page)
        proxies_kuaidaili = fetch_proxies_kuaidaili(driver, page)
        proxies_iphaiwai = fetch_proxies_iphaiwai(driver, page)
        all_proxies = proxies_89ip + proxies_kuaidaili + proxies_iphaiwai
        
        for proxy in all_proxies:
            if check_proxy(proxy):
                valid_proxies.add(proxy)
        
        time.sleep(random.uniform(2, 4))
    
    driver.quit()
    
    with open("valid_proxies.txt", "w") as f:
        for proxy in valid_proxies:
            f.write(proxy + "\n")
    print("有效代理已保存到 valid_proxies.txt")

if __name__ == '__main__':
    main()