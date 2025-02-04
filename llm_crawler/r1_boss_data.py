# 好的，现在从valid_proxies.txt，交叉使用不同的代理 ip 爬取数据，该下面代码，最终只需要输出完整的 python 代码就行。
import os
import pickle
import time
import random
import json
import csv
from urllib.parse import quote
from typing import Dict, List


import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException


BOSS_COOKIE_FILE = "boss_cookie.pkl"
BASE_JSON_URL = "https://www.zhipin.com/wapi/zpgeek/search/joblist.json"
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
]


class BossZPCrawler:
    def __init__(self, headless=False):
        self.driver = self._configure_driver(headless)
        self.seen_jobs = set()  # 去重容器
        self.retry_max = 3      # 最大重试次数
        self.crawl_delay = (3, 7)  # 随机延迟范围


    def _configure_driver(self, headless: bool):
        """配置浏览器驱动，绕过检测"""
        options = uc.ChromeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-web-security")
        options.add_argument("--disable-site-isolation-trials")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        
        if headless:
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")


        # 动态User-Agent
        options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")


        # 使用undetected-chromedriver绕过检测
        driver = uc.Chrome(options=options)
        
        # 屏蔽常见自动化特征
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.chrome = {runtime: {}};
            """}
        )
        return driver


    def _load_cookies(self):
        """加载本地Cookie"""
        self.driver.get("https://www.zhipin.com")
        time.sleep(2)
        
        if not os.path.exists(BOSS_COOKIE_FILE):
            return False


        with open(BOSS_COOKIE_FILE, "rb") as f:
            cookies = pickle.load(f)
            for cookie in cookies:
                if 'zhipin.com' in cookie['domain']:
                    self.driver.add_cookie(cookie)
        self.driver.refresh()
        return True


    def _manual_login(self):
        """手动登录并保存Cookie"""
        self.driver.get("https://www.zhipin.com")
        print("请手动完成登录并等待页面跳转...")
        input("确认登录成功并按回车继续 >>> ")
        with open(BOSS_COOKIE_FILE, "wb") as f:
            pickle.dump(self.driver.get_cookies(), f)
        print("Cookies已持久化存储")


    def _anti_detect_check(self) -> bool:
        """检测验证码"""
        try:
            self.driver.find_element(By.CSS_SELECTOR, 'div.verify-wrap')
            print("检测到验证码，请手动处理！")
            input("处理完成后按回车继续 >>> ")
            return True
        except:
            return False


    def _construct_query_params(self, page: int) -> Dict:
        """构造请求参数"""
        return {
            "scene": "1",
            "query": "unity",
            "city": "101020100",  # 上海城市代码
            "page": str(page),
            "pageSize": "30",
            "radius": "",
            "degree": "",
            "salary": "",
            "jobType": "",
            "experience": "",
            "scale": "",
            "stage": "",
            "position": "",
            "partTime": "",
            "multiBusinessDistrict": "",
            "multiSubway": "",
            "publishedTime": "",
            "comprehensiveScore": "",
            "sortType": str(random.randint(0, 2)),  # 随机排序
            "latitude": "",
            "longitude": ""
        }


    def _fetch_page_data(self, page: int) -> List[Dict]:
        """抓取单页数据"""
        for _ in range(self.retry_max):
            try:
                # 动态参数编码
                params = self._construct_query_params(page)
                encoded_params = "&".join(
                    [f"{k}={quote(v) if v else ''}" for k, v in params.items()]
                )
                target_url = f"{BASE_JSON_URL}?{encoded_params}"


                # 模拟用户行为
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight*Math.random())")
                time.sleep(random.uniform(0.5, 1.5))


                self.driver.get(target_url)
                time.sleep(random.uniform(*self.crawl_delay))


                if self._anti_detect_check():
                    continue


                # 解析JSON数据
                pre = self.driver.find_element(By.TAG_NAME, 'pre')
                response = json.loads(pre.text)
                
                if response['code'] == 37:
                    raise Exception("触发反爬机制 code=37")
                
                return response['zpData']['jobList']
            
            except WebDriverException as e:
                print(f"页面获取异常: {str(e)}")
                time.sleep(10)
            except json.JSONDecodeError:
                print("JSON解析失败，可能遭遇反爬")
                self.driver.save_screenshot(f'error_{int(time.time())}.png')
        return []


    def _process_job_data(self, raw_data: List[Dict]) -> List[List]:
        """清洗数据"""
        clean_data = []
        for job in raw_data:
            job_id = job.get('encryptJobId')
            if not job_id or job_id in self.seen_jobs:
                continue
            
            self.seen_jobs.add(job_id)
            clean_data.append([
                job.get('jobName', ''),
                job.get('brandName', ''),
                job.get('bossName', ''),
                job.get('salaryDesc', ''),
                job.get('jobExperience', ''),
                job.get('jobDegree', ''),
                job.get('cityName', ''),
                job.get('areaDistrict', ''),
                job.get('infoDesc', ''),
                job.get('companyTagList', ''),
                job.get('tagList', ''),
                f"https://www.zhipin.com/job_detail/{job_id}.html",
                time.strftime("%Y-%m-%d %H:%M:%S")
            ])
        return clean_data


    def execute_crawl(self, max_pages=5):
        """执行爬虫"""
        if not self._load_cookies():
            self._manual_login()


        all_jobs = []
        current_page = 1
        
        while current_page <= max_pages:
            print(f"正在抓取第 {current_page} 页...")
            raw_data = self._fetch_page_data(current_page)
            
            if not raw_data:
                print(f"第 {current_page} 页无数据，终止爬取")
                break
            
            processed = self._process_job_data(raw_data)
            all_jobs.extend(processed)
            print(f"第 {current_page} 页获取到 {len(processed)} 条有效数据")
            
            current_page += 1
            time.sleep(random.randint(4, 8))  # 模拟人工翻页间隔


        self._save_to_csv(all_jobs)
        self.driver.quit()


    def _save_to_csv(self, data: List[List]):
        """保存数据到CSV"""
        if not data:
            print("无有效数据需要保存")
            return


        filename = f"BOSS_上海Unity岗位_{time.strftime('%Y%m%d%H%M')}.csv"
        headers = [
            "职位名称", "公司名称", "招聘官", "薪资范围",
            "经验要求", "学历要求", "城市", "区域", 
            "职位链接", "公司福利", "公司标签", "岗位标签", "采集时间"
        ]


        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(data)
        
        print(f"数据已保存至 {filename}，总计 {len(data)} 条记录")


if __name__ == "__main__":
    crawler = BossZPCrawler(headless=False)  # 调试时可关闭无头模式
    crawler.execute_crawl(max_pages=10)
