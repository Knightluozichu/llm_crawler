from math import e
import pathlib
import time
import pandas as pd
from DrissionPage import ChromiumPage
from DrissionPage.errors import ElementNotFoundError
from DrissionPage import  Chromium, ChromiumOptions
from data_save import JobDatabase

def save_to_database(df, table_name='jobs'):
    """
    Save job data to SQLite database
    Args:
        df: DataFrame containing job information
        table_name: Name of the table to save data to (default: 'jobs')
    """
    # Initialize database
    db = JobDatabase()
    
    # 检查表是否存在，如果不存在则创建
    if table_name not in db.get_table_names():
        db.create_table(table_name)
    
    # Insert each row into database
    for _, row in df.iterrows():
        try:
            db.insert_job(
                table_name=table_name,
                position_name=row['position_name'],
                company_name=row['company_name'], 
                salary=row['salary'],
                work_city=row['work_city'],
                work_exp=row['work_exp'],
                education=row['education'],
                company_size=row['company_size'],
                company_type=row['company_type'],
                industry=row['industry'],
                position_url=row['position_url'],
                job_summary=row['job_summary'],
                welfare=row['welfare'],
                salary_count=row['salary_count']
            )
            print(f"Added job: {row['position_name']} at {row['company_name']}")
            # if st:
            #     st.write(f"Added job: {row['position_name']} at {row['company_name']}")
                
        except Exception as e:
            print(f"插入数据失败: {e}")
            # if st:
            #     st.error(f"插入数据失败: {e}")
class BossScraper:
    def __init__(self, job_kw, job_city, proxy=None, data_dir='data'):
        """
        初始化 BossScraper 对象。
        :param job_kw: 职位关键词
        :param job_city: 城市编号，例如上海为 "101020100"
        :param proxy: 代理设置，可以是 "ip:port" 字符串或代理字典
        :param data_dir: 数据保存目录
        """
        self.job_kw = job_kw
        self.job_city = job_city
        self.base_url = "https://www.zhipin.com/web/geek/job"
        self.proxy = proxy

        # 如果提供了代理，则转换为字典格式
        if proxy:

            print(f"初始代理已设置为: {proxy}")
            co = ChromiumOptions()
            co.set_proxy(f'http://{proxy}')
            self.page = ChromiumPage(addr_or_opts=co)
            
        else:
            self.page = ChromiumPage()

        # 监听包含职位列表数据的接口请求
        self.page.listen.start('wapi/zpgeek/search/joblist.json')
        self.all_jobs = []
        # 使用集合存储已添加岗位的去重键，例如 (岗位名称, 公司名称)
        self.seen_jobs = set()
        self.data_dir = pathlib.Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

    def set_proxy(self, proxy_ip_port):
        """
        动态设置代理 ip, 格式可以为 "ip:port" 字符串或代理字典。
        此方法会退出当前页面实例，并重新初始化以应用新的代理设置。
        """
        try:
            self.page.quit()
        except Exception:
            pass

        self.proxy = proxy_ip_port
        if proxy_ip_port:
            print(f"初始代理已设置为: {proxy_ip_port}")
            co = ChromiumOptions()
            co.set_proxy(f'http://{proxy_ip_port}')
            self.page = ChromiumPage(addr_or_opts=co)
        else:
            self.page = ChromiumPage()
        self.page.listen.start('wapi/zpgeek/search/joblist.json')

    def fetch_data(self, page_number):
        """
        根据页码构造 URL，刷新页面以获取数据包。
        :param page_number: 页码
        :return: 响应数据的 body 部分
        """
        url = f'{self.base_url}?query={self.job_kw}&city={self.job_city}&page={page_number}'
        print(f"正在请求：{url}")
        self.page.get(url=url)
        packet = self.page.listen.wait(timeout=10)
        if not packet:
            raise TimeoutError("获取数据超时，请检查网络或页面加载状态")
        return packet.response.body

    def parse_jobs(self, data):
        """
        解析页面返回的数据，提取职位信息列表。
        :param data: 页面返回的 json 数据
        :return: 职位信息列表
        """
        jobs = []
        if 'zpData' in data and 'jobList' in data['zpData']:
            for job in data['zpData']['jobList']:
                job_info = {
                    'position_name': job.get('jobName', ''),
                    'salary': job.get('salaryDesc', ''),
                    'work_exp': job.get('jobExperience', ''),
                    'education': job.get('jobDegree', ''),
                    'work_city': job.get('cityName', ''),
                    # '区域': job.get('areaDistrict', ''),
                    # '商圈': job.get('businessDistrict', ''),
                    'company_name': job.get('brandName', ''),
                    'company_size': job.get('brandScaleName', ''),
                    'industry': job.get('brandIndustry', ''),
                    'welfare': job.get('welfareList', []),
                    'job_summary': job.get('skills', [])
                }
                jobs.append(job_info)
        return jobs

    def run(self):
        """
        主运行函数：循环抓取每一页数据，直到遇到空数据、异常或数据不再增加。
        在抓取过程中，对职位进行去重（以岗位名称和公司名称为唯一标识）。
        """
        page_number = 1
        previous_job_count = 0
        while True:
            try:
                print(f"正在获取第 {page_number} 页数据")
                data = self.fetch_data(page_number)
                page_jobs = self.parse_jobs(data)
                if not page_jobs:
                    print(f"第 {page_number} 页数据为空或数据结构异常，停止翻页")
                    print(f"异常数据:{data}")
                    break
                for job in page_jobs:
                    key = (job.get('position_name', ''), job.get('company_name', ''))
                    if key not in self.seen_jobs:
                        self.all_jobs.append(job)
                        self.seen_jobs.add(key)
                current_job_count = len(self.all_jobs)
                print(f"成功获取第 {page_number} 页数据，累计 {current_job_count} 条去重后的职位")
                if current_job_count == previous_job_count:
                    print("数据不再增加，停止抓取")
                    break
                previous_job_count = current_job_count
                page_number += 1
            except Exception as e:
                print(f"获取第 {page_number} 页数据时发生异常: {repr(e)}")
                break

    def save_data(self, table_name):
        # """
        # 保存爬取的职位数据到 CSV 文件。
        # """
        # if self.all_jobs:
        #     df = pd.DataFrame(self.all_jobs)
        #     filename = f"boss_{self.job_kw}_{self.job_city}.csv"
        #     file_path = self.data_dir / filename
        #     df.to_csv(file_path, index=False, encoding='utf-8-sig')
        #     print(f"成功保存 {len(self.all_jobs)} 条数据到 {file_path}")
        # else:
        #     print("未获取到有效数据，数据保存被跳过")
        """
        保存爬取的职位数据到数据库。
        """
        if self.all_jobs:
            df = pd.DataFrame(self.all_jobs)
            save_to_database(df, table_name)
        else:
            print("未获取到有效数据，数据保存被跳过")

    def quit(self):
        """
        退出浏览器并清理资源。
        """
        self.page.quit()
        
    # 在代码中添加如下测试代码
    def test_proxy(self):
        self.page.get('https://httpbin.org/ip')
        return self.page.html  # 查看返回的IP是否是代理IP


if __name__ == "__main__":
    import sqlite3
    print(sqlite3.sqlite_version)
    # job_kw = "unity"
    # job_city = "101020100"  # 上海的城市编号
    
    # proxy = "183.7.120.127:20831"
    # scraper = BossScraper(job_kw, job_city, proxy=proxy)

    # try:
    #     print("测试代理连接...")
    #     IP = scraper.test_proxy()  # 验证代理是否工作
    #     print(f"检查代理IP: {IP}")
    #     if IP['origin'] == proxy.split(':')[0]:
    #         print("代理测试通过")
    #     else:
    #         print("代理测试失败")
    #         raise ConnectionError("代理测试失败")
    #     scraper.run()
    # finally:
    #     scraper.save_data()
    #     scraper.quit()