# 使用 drissionpage 爬取 Boss 直聘的上海 Unity 数据
from DrissionPage import ChromiumPage
import pandas as pd
import time
from DrissionPage.errors import ElementNotFoundError
import pathlib

job_kw = "unity"
job_city = "101020100"  # 上海

# 创建一个 ChromiumPage 对象
page = ChromiumPage()

# 监听含有职位列表数据的请求
page.listen.start('wapi/zpgeek/search/joblist.json')

# 打开职位列表页面
page.get(f'https://www.zhipin.com/web/geek/job?query=unity&city=101020100')

# 等待并获取初始数据包
packet = page.listen.wait(timeout=10)
if not packet:
    print("错误：未捕获到初始数据，请检查网络或页面加载状态")
    page.quit()
    exit()
data = packet.response.body
print(f"捕获到初始数据")

# 存储所有职位信息
all_jobs = []
page_num = 1

try:
    while packet:
        # 处理当前页数据
        if 'zpData' in data and 'jobList' in data['zpData']:
            job_list = data['zpData']['jobList']
            for job in job_list:
                job_info = {
                    '岗位名称': job.get('jobName', ''),
                    '薪资': job.get('salaryDesc', ''),
                    '工作经验要求': job.get('jobExperience', ''),
                    '学历要求': job.get('jobDegree', ''),
                    '城市': job.get('cityName', ''),
                    '区域': job.get('areaDistrict', ''),
                    '商圈': job.get('businessDistrict', ''),
                    '公司名称': job.get('brandName', ''),
                    '公司规模': job.get('brandScaleName', ''),
                    '行业': job.get('brandIndustry', ''),
                    '福利待遇': job.get('welfareList', []),
                    '技能要求': job.get('skills', [])
                }
                all_jobs.append(job_info)
            print(f"成功获取第 {page_num} 页数据")
        else:
            print(f"第 {page_num} 页数据结构异常，跳过处理")
            break

        # 尝试翻页
        try:
            # 查找下一页按钮
            next_btn = page.ele('css:.options-pages a > .ui-icon-arrow-right', timeout=5)
            if not next_btn:
                print("未找到有效的下一页按钮")
                break

            # 点击下一页按钮
            next_btn.click()
            print("已点击下一页按钮")
        except ElementNotFoundError:
            print("未找到下一页按钮")
            break
        packet = page.listen.wait(timeout=10)
        if not packet:
            print("获取新页面数据超时")
            break
        data = packet.response.body
        page_num += 1

except Exception as e:
    print(f"运行异常: {repr(e)}")

finally:
    # 数据保存
    if all_jobs:
        df = pd.DataFrame(all_jobs)
        filename = f"boss_{job_kw}_{job_city}.csv"
        data_dir = pathlib.Path('data')
        data_dir.mkdir(exist_ok=True)
        df.to_csv(data_dir/filename, index=False, encoding='utf-8-sig')
        print(f"成功保存 {len(all_jobs)} 条数据到 {filename}")
    else:
        print("未获取到有效数据")

    page.quit()