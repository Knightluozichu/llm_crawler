# %%
from selenium import webdriver
import time
import re
import json
import pandas as pd
from pathlib import Path
import logging
import os
import streamlit as st
from data_save import JobDatabase

# # 对连接进行缓存源网页内容
# def cache_page(url):
#     driver = webdriver.Chrome()
#     driver.get(url)
#     # 等待页面加载完成
#     time.sleep(2)
#     # 获取源码
#     page_source = driver.page_source
#     driver.quit()
#     return page_source

def allPage(url):
    driver = webdriver.Chrome()
    # 无头模式
    # options = webdriver.ChromeOptions()
    # options.add_argument('--headless')
    # driver = webdriver.Chrome(options=options)
    driver.get(url)
    # 等待页面加载完成
    time.sleep(1)
    # 获取源码
    page_source = driver.page_source
    # 从源码中提取总页数
    pattern = r'"pageSize":(.*?),"searchCondition"'
    countPage = re.findall(pattern, page_source, re.S)
    if countPage:
        countPage = int(countPage[0])
    driver.quit()
    return countPage

def cache_all_page(url: str, max_pages: int = 1, existing_driver=None, city=None, keyword=None, table_name=None):
    """抓取指定页数的数据"""
    driver = existing_driver
    should_quit = False
    
    try:
        if not driver:
            # 使用普通模式创建浏览器（不使用无头模式）
            driver = webdriver.Chrome()
            should_quit = True
        
        base_url = url.split('/p')[0]
        
        for page in range(1, max_pages + 1):
            if st:  # 检查是否在Streamlit环境中
                st.write(f"正在抓取第 {page}/{max_pages} 页...")
            
            page_url = f"{base_url}/p{page}"
            driver.get(page_url)
            time.sleep(2)  # 等待页面加载
            
            page_source = driver.page_source
            df = extract_data(page_source)
            
            if not df.empty:
                # save_to_csv(df, f'{city}_{keyword}.csv')
                if table_name:
                    save_to_database(df, table_name)
                else:
                    save_to_database(df)  # 使用默认'jobs'表
            else:
                st.warning(f"第 {page} 页数据为空")
    
    except Exception as e:
        print(f"抓取过程中出错: {e}")
        if st:
            st.error(f"抓取出错: {e}")
        raise e
        
    finally:
        if should_quit and driver:
            driver.quit()

def extract_data(page_source):
    """提取职位数据
    Args:
        page_source: JSON格式的页面源码
    Returns:
        DataFrame: 包含职位信息的数据框
    """
    try:
        # 提取JSON字符串
        json_res = r'__INITIAL_STATE__=(.*?)</script>'
        jsonl = re.findall(json_res, page_source, re.S)
        
        if not jsonl:
            logging.error("未找到职位数据")
            return pd.DataFrame()
            
        # 解析第一个匹配的JSON对象
        data = json.loads(jsonl[0])
        positions = data.get('positionList', [])
        
        if not positions:
            logging.warning("未找到职位列表数据")
            return pd.DataFrame()
            
        # 提取需要的字段
        job_list = []
        for pos in positions:
            if not isinstance(pos, dict):
                continue
                
            job = {
                'position_name': pos.get('name', ''),
                'company_name': pos.get('companyName', ''),
                'salary': pos.get('salary60', ''),
                'work_city': pos.get('workCity', ''),
                'work_exp': pos.get('workingExp', ''),
                'education': pos.get('education', ''),
                'company_size': pos.get('companySize', ''),
                'company_type': pos.get('propertyName', ''),
                'industry': pos.get('industryName', ''),
                'position_url': pos.get('positionURL', ''),
                'job_summary': pos.get('jobSummary', ''),
                'welfare': ','.join(pos.get('welfareTagList', [])),
                'salary_count': pos.get('salaryCount', ''),
            }
            job_list.append(job)
            
        # 转换为DataFrame
        df = pd.DataFrame(job_list)
        
        # 基本数据清洗 
        df = df.fillna('')  # 填充空值
        df['welfare'] = df['welfare'].str.strip()  # 清理福利标签
        
        return df
        
    except json.JSONDecodeError as e:
        logging.error(f"JSON解析错误: {e}")
        return pd.DataFrame()
    except Exception as e:
        logging.error(f"数据提取错误: {e}")
        return pd.DataFrame()
        
def save_to_csv(df, filename):
    """保存数据到CSV文件"""
    filename_path = Path(__file__).parent.parent / f'data/{filename}'
    try:
        if os.path.exists(filename_path):
            # 如果文件存在,追加数据,不包含header  
            df.to_csv(filename_path, mode='a', header=False, index=False, encoding='utf-8-sig')
            print(f"数据已追加到 {filename_path}")  # 改为print
            st.write(f"数据已追加到 {filename_path}")  # 添加UI反馈
        else:
            # 如果文件不存在,创建新文件
            df.to_csv(filename_path, index=False, encoding='utf-8-sig') 
            print(f"新文件已创建: {filename_path}")  # 改为print
            st.write(f"新文件已创建: {filename_path}")  # 添加UI反馈
    except Exception as e:
        print(f"保存CSV文件失败: {e}")  # 改为print
        st.error(f"保存CSV文件失败: {e}")  # 添加错误提示

def analyze_data(df):
    """分析职位数据
    Args:
        df: 包含职位信息的DataFrame
    Returns:
        dict: 分析结果
    """
    analysis = {
        'total_count': len(df),
        'salary_stats': df['salary'].value_counts().to_dict(),
        'edu_stats': df['education'].value_counts().to_dict(),
        'exp_stats': df['work_exp'].value_counts().to_dict(),
        'company_type_stats': df['company_type'].value_counts().to_dict()
    }
    return analysis

def save_to_database(df, table_name='jobs'):
    """
    Save job data to SQLite database
    Args:
        df: DataFrame containing job information
        table_name: Name of the table to save data to (default: 'jobs')
    """
    
    # Initialize database
    db = JobDatabase()
    db.create_table(table_name)
    
    # Insert each row into database
    for _, row in df.iterrows():
        try:
            db.insert_job(
                table_name=table_name,  # 添加 table_name 参数
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
            if st:
                st.write(f"Added job: {row['position_name']} at {row['company_name']}")
                
        except Exception as e:
            print(f"Error saving job to database: {e}")
            if st:
                st.error(f"Error saving job to database: {e}")


# 添加命令行入口
if __name__ == '__main__':
    # 设置日志级别
    logging.basicConfig(level=logging.INFO)
    
    # 测试数据提取
# 添加命令行入口
if __name__ == '__main__':
    # 设置日志级别
    logging.basicConfig(level=logging.INFO)
    
    # 测试数据提取
    # test_file = Path(__file__).parent / 'test.txt'
    # if not test_file.exists():
    #     raise FileNotFoundError("测试文件不存在")

    # # 测试数据提取
    # with open(test_file, 'r', encoding='utf-8') as f:
    #     test_data = f.read()
    
    # # print(f"测试数据预览:{test_data}")
    # df = extract_data(test_data)
    # print("提取的数据预览:")
    # print(df.head())
    
    # # 保存数据
    # save_to_csv(df, 'search_job.csv')
    
    # # 分析数据
    # analysis = analyze_data(df)
    # print("\n数据分析结果:")
    # print(json.dumps(analysis, indent=2, ensure_ascii=False))
    
    # 测试总页数
    url=r'https://www.zhaopin.com/sou/jl530/in-1/kw01O00U80EG06G03F01N0/p1?sl=0000,9999999&el=-1&we=-1&et=-1&ct=0&cs=-1'
    countPage = allPage(url)
    print(countPage)
# %%
