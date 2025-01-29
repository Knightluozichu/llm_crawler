import streamlit as st
import json
import os
import time
import pickle
import base64
from selenium import webdriver
from kw import encode_kw
from zhaopin_dataextuce import cache_all_page
from zhilian_login import get_logged_in_driver, is_login_success
from zhaopin_maxpage import test_page_input
import atexit

######################################
# 1. 通用功能函数区
######################################

def update_append_mode():
    """更新配置状态"""
    if 'append_to_jobs' not in st.session_state:
        st.session_state.append_to_jobs = True

def initialize_append_mode():
    update_append_mode()
    st.session_state.append_to_jobs = st.radio(
        "数据保存模式",
        ["汇入jobs总表", "保存为单独文件"],
        index=0 if st.session_state.append_to_jobs else 1,
        key="append_mode"
    )
    st.session_state.append_to_jobs = (st.session_state.append_mode == "汇入jobs总表")

def quit_all_drivers():
    """退出所有活跃的driver"""
    try:
        if st.session_state.driver:
            st.session_state.driver.quit()
            st.session_state.driver = None
            st.session_state.login_status = False
    except Exception as e:
        print(f"关闭浏览器时出错: {e}")

def cleanup():
    """程序退出时调用的清理函数"""
    quit_all_drivers()

atexit.register(cleanup)

def has_valid_cookies(cookie_path):
    """检查是否存在有效的cookie文件"""
    try:
        if os.path.exists(cookie_path):
            with open(cookie_path, 'rb') as f:
                cookies = pickle.load(f)
                return bool(cookies)
        return False
    except:
        return False

def save_cookies(driver, cookie_path):
    """保存cookies到文件"""
    if driver:
        cookies = driver.get_cookies()
        with open(cookie_path, 'wb') as f:
            pickle.dump(cookies, f)

def load_cookies(driver, cookie_path):
    """从文件加载cookies"""
    try:
        with open(cookie_path, 'rb') as f:
            cookies = pickle.load(f)
            for cookie in cookies:
                try:
                    driver.add_cookie(cookie)
                except:
                    continue
        return True
    except Exception as e:
        print(f"加载cookies失败: {e}")
        return False

def delete_cookies(cookie_path):
    """删除本地cookie文件"""
    try:
        if os.path.exists(cookie_path):
            os.remove(cookie_path)
            if 'has_cookies' in st.session_state:
                st.session_state.has_cookies = False
            if 'login_status' in st.session_state:
                st.session_state.login_status = False
            return True
        return False
    except Exception as e:
        print(f"删除cookie文件失败: {e}")
        return False

def check_login_status(url=None, force_check=False):
    """
    优先使用cookies进行判断的登录状态检查:
    - 如果有cookie且非强制检查, 直接视为已登录
    - 如果没有cookie, 需要重新登录
    """
    if st.session_state.has_cookies and not force_check:
        return True
    if not st.session_state.has_cookies:
        st.warning("需要登录后才能继续操作")
        return False
    return st.session_state.login_status

######################################
# 2. 默认配置
######################################

DEFAULT_CONFIG = {
    "data": {
        "hotCity": [{"code": "530", "name": "北京"}, {"code": "538", "name": "上海"}],
        "industry": [{"code": "0", "name": "不限"}, {"code": "10100", "name": "IT软件"}],
        "salaryType": [{"code": "0,0", "name": "不限"}, {"code": "10,20", "name": "1-2万/月"}],
        "educationType": [{"code": "0", "name": "不限"}, {"code": "5", "name": "本科"}],
        "workExpType": [{"code": "0", "name": "不限"}, {"code": "103", "name": "1-3年"}],
        "jobStatus": [{"code": "0", "name": "不限"}, {"code": "1", "name": "全职"}],
        "companySize": [{"code": "0", "name": "不限"}, {"code": "3", "name": "100-499人"}],
        "companyType": [{"code": "0", "name": "不限"}, {"code": "1", "name": "民营"}]
    }
}

######################################
# 3. 初始化会话状态
######################################

if 'init_done' not in st.session_state:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    st.session_state.cookie_path = os.path.join(current_dir, 'zhilian_cookies.pkl')
    st.session_state.config_path = os.path.join(current_dir, 'zhaopin.json')
    st.session_state.has_cookies = has_valid_cookies(st.session_state.cookie_path)
    st.session_state.login_status = st.session_state.has_cookies
    st.session_state.show_crawler_config = False
    st.session_state.total_pages = 0
    st.session_state.generated_link = ""
    st.session_state.extract_pages = 1
    st.session_state.driver = None
    st.session_state.last_check_time = 0
    st.session_state.init_done = True

######################################
# 4. 加载配置文件
######################################

try:
    with open(st.session_state.config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)['data']
except FileNotFoundError:
    st.warning(f"配置文件 {st.session_state.config_path} 未找到，使用默认配置")
    config = DEFAULT_CONFIG['data']
except json.JSONDecodeError:
    st.warning("配置文件格式错误，使用默认配置")
    config = DEFAULT_CONFIG['data']

######################################
# 5. 生成链接相关函数
######################################

def validate_option_data(data, field_name):
    """验证选项数据格式并规范化"""
    try:
        return [
            (str(item.get("code", "0")), str(item.get("name", "不限"))) 
            for item in data.get(field_name, [{"code": "0", "name": "不限"}])
        ]
    except Exception as e:
        st.warning(f"处理{field_name}数据时出错: {str(e)}")
        return [("0", "不限")]

def generate_url():
    """根据用户选择和输入生成智联搜索链接"""
    base_url = "https://www.zhaopin.com/sou/"
    
    city_code = st.session_state.city[0]
    position_raw = st.session_state.position 
    position_encoded = encode_kw(position_raw) if position_raw else ""
    industry = st.session_state.industry[0]
    page = st.session_state.page
    salary_range = st.session_state.salary[0]
    education = st.session_state.education[0]
    work_exp = st.session_state.work_exp[0]
    job_type = st.session_state.job_type[0]
    company_type = st.session_state.company_type[0]
    company_size = st.session_state.company_size[0]

    # 拼接URL
    url = f"{base_url}jl{city_code}/in{industry}/{position_encoded}/p{page}"
    url += f"?sl={salary_range}"
    url += f"&el={education}"
    url += f"&we={work_exp}"
    url += f"&et={job_type}"
    url += f"&ct={company_type}"
    url += f"&cs={company_size}"
    
    # 如果URL有更新, 则重置 session_state.total_pages
    if url != st.session_state.generated_link:
        st.session_state.generated_link = url
        st.session_state.total_pages = 0
    return url

######################################
# 6. 主页面布局：链接生成器
######################################

st.title("zlzp链接生成器")

# 基本搜索条件
st.subheader("基本搜索条件")
col1, col2 = st.columns(2)
with col1:
    st.selectbox(
        "城市", 
        options=validate_option_data(config, "hotCity"),
        format_func=lambda x: x[1],
        key="city"
    )
with col2:
    st.text_input("职位关键词", value="python", key="position")

# 行业与薪资
col3, col4 = st.columns(2)
with col3:
    st.selectbox(
        "行业", 
        options=validate_option_data(config, "industry"),
        format_func=lambda x: x[1],
        key="industry"
    )
with col4:
    st.selectbox(
        "薪资范围",
        options=validate_option_data(config, "salaryType"),
        format_func=lambda x: x[1],
        key="salary"
    )

# 筛选条件
st.subheader("筛选条件")
col5, col6 = st.columns(2)
with col5:
    st.selectbox(
        "学历要求",
        options=validate_option_data(config, "educationType"),
        format_func=lambda x: x[1],
        key="education"
    )
    st.selectbox(
        "工作经验",
        options=validate_option_data(config, "workExpType"),
        format_func=lambda x: x[1],
        key="work_exp"
    )
with col6:
    st.selectbox(
        "工作类型",
        options=validate_option_data(config, "jobStatus"),
        format_func=lambda x: x[1],
        key="job_type"
    )
    st.selectbox(
        "公司规模",
        options=validate_option_data(config, "companySize"),
        format_func=lambda x: x[1],
        key="company_size"
    )

st.selectbox(
    "公司类型",
    options=validate_option_data(config, "companyType"),
    format_func=lambda x: x[1],
    key="company_type"
)

# 分页
st.number_input("页码", min_value=1, value=1, key="page")

# 生成链接并显示
col_gen, col_copy = st.columns([2, 1])
with col_gen:
    if st.button("生成链接", key="gen_link_btn"):
        generated_link = generate_url()
        st.session_state.generated_link = generated_link
        st.success("链接已生成:")
        st.code(generated_link)

with col_copy:
    if st.session_state.generated_link:
        st.button(
            "复制链接",
            key="copy_link_btn",
            on_click=lambda: st.write(
                f'<script>navigator.clipboard.writeText("{st.session_state.generated_link}")</script>',
                unsafe_allow_html=True
            )
        )

if st.session_state.generated_link and not st.session_state.get("gen_link_btn"):
    st.code(st.session_state.generated_link)

######################################
# 7. 侧边栏：登录与Cookie管理
######################################

st.sidebar.title("登录状态")

# 手动登录按钮
if st.sidebar.button("手动登录", key="manual_login_btn"):
    try:
        # 如果当前没有可用driver或尚未登录，则进行登录流程
        if not (st.session_state.driver and is_login_success(st.session_state.driver)):
            save_cookies(st.session_state.driver, st.session_state.cookie_path)
            driver = get_logged_in_driver()
            # 尝试加载cookies后刷新
            if load_cookies(driver, st.session_state.cookie_path):
                driver.refresh()
            if driver and is_login_success(driver):
                st.session_state.login_status = True
                st.session_state.driver = driver
                save_cookies(driver, st.session_state.cookie_path)
                st.sidebar.success("登录成功！")
                quit_all_drivers()  # 登录成功后关闭浏览器
            else:
                st.sidebar.error("登录失败，请重试")
                if driver:
                    driver.quit()
        else:
            st.sidebar.info("已经处于登录状态")
    except Exception as e:
        st.sidebar.error(f"登录过程中出错: {str(e)}")

# Cookie状态及删除
if st.session_state.has_cookies:
    if st.sidebar.button("删除Cookie", key="delete_cookie_btn", type="secondary"):
        if delete_cookies(st.session_state.cookie_path):
            st.sidebar.success("Cookie已删除")
            st.rerun()
        else:
            st.sidebar.error("删除Cookie失败")
    st.sidebar.success("Cookie状态：已存在 ✅")
else:
    st.sidebar.warning("Cookie状态：未找到 ❌")

######################################
# 8. 抓取数据配置与执行
######################################

if st.button("抓取数据配置", key="crawler_config_btn") or st.session_state.show_crawler_config:
    st.session_state.show_crawler_config = True
    initialize_append_mode()
    if not st.session_state.generated_link:
        st.warning("请先生成链接，再点击此按钮")
    else:
        # 如果总页数还未获取，先获取总页数
        if st.session_state.total_pages == 0:
            try:
                with st.spinner('获取总页数...'):
                    temp_driver = webdriver.Chrome()
                    try:
                        if os.path.exists(st.session_state.cookie_path):
                            temp_driver.get("https://www.zhaopin.com")
                            load_cookies(temp_driver, st.session_state.cookie_path)
                        
                        orig, max_page = test_page_input(
                            st.session_state.generated_link,
                            existing_driver=temp_driver
                        )
                        
                        if max_page:
                            st.session_state.total_pages = int(max_page)
                            st.success(f"获取成功！总页数: {st.session_state.total_pages}")
                        else:
                            st.error("无法获取总页数")
                    finally:
                        temp_driver.quit()
            except Exception as e:
                st.error(f"获取页数失败: {str(e)}")

        # 检查登录并开始抓取数据
        if check_login_status() and st.session_state.total_pages > 0:
            st.info(f"总页数: {st.session_state.total_pages}")
            
            st.session_state.extract_pages = st.number_input(
                "选择抓取页数", 
                min_value=1, 
                max_value=st.session_state.total_pages,
                value=st.session_state.extract_pages,
                key="extract_pages_input"
            )
            
            if st.button("开始抓取", key="start_crawl_btn"):
                try:
                    progress_text = st.empty()
                    status_text = st.empty()
                    progress_dots = st.empty()
                    
                    crawler_driver = webdriver.Chrome()
                    try:
                        # 加载cookies
                        if os.path.exists(st.session_state.cookie_path):
                            crawler_driver.get("https://www.zhaopin.com")
                            load_cookies(crawler_driver, st.session_state.cookie_path)
                        
                        # 获取城市和搜索关键字
                        city = st.session_state.city[1]  # 使用城市名称
                        keyword = st.session_state.position  # 搜索关键词
                        
                        # 正式开始抓取
                        cache_all_page(
                            st.session_state.generated_link, 
                            max_pages=st.session_state.extract_pages,
                            existing_driver=crawler_driver,
                            city=city,
                            keyword=keyword,
                            table_name= "jobs" if st.session_state.append_to_jobs else f"{city}_{keyword}_jobs"  # 保存到jobs表
                        )
                        
                        status_text.success("✅ 数据抓取完成")
                        
                        # 显示下载按钮
                        csv_path = os.path.join(
                            os.path.dirname(st.session_state.cookie_path), 
                            '../data/search_job.csv'
                        )
                        csv_path = os.path.abspath(csv_path)
                        if os.path.exists(csv_path):
                            with open(csv_path, 'rb') as f:
                                csv_data = f.read()
                            b64 = base64.b64encode(csv_data).decode()
                            href = f'<a href="data:file/csv;base64,{b64}" download="search_job.csv">下载数据文件</a>'
                            st.markdown(href, unsafe_allow_html=True)
                    
                    finally:
                        crawler_driver.quit()
                        progress_text.empty()
                        progress_dots.empty()
                
                except Exception as e:
                    st.error(f"抓取失败: {str(e)}")
                    progress_text.empty()
                    status_text.empty()
                    progress_dots.empty()
        else:
            st.warning("请先登录后再进行数据抓取")