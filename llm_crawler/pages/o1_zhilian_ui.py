#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
招聘爬虫主模块（示例）

功能概览：
1. ConfigManager：负责加载与合并配置
2. WebDriverManager：统一管理 Chrome WebDriver 的创建、退出、Cookies 等
3. ZhilianScraper：智联招聘爬虫（只包含核心抓取逻辑，不直接依赖 Streamlit）
4. BossScraper：BOSS直聘爬虫（示例性实现，同样只包含核心抓取逻辑）
5. UIComponents：基于 Streamlit 的界面逻辑（表单、按钮等）
6. SessionManager：管理 Streamlit 会话状态
7. main 函数：程序入口，整合并调度各部分

由于此示例先不管外部文件，部分函数和依赖（如 encode_kw、get_logged_in_driver 等）使用占位实现。
"""


import os
import sys
import json
import logging
import pathlib
from typing import Optional, Dict, List, Tuple, Any

import streamlit as st
import pandas as pd

import zhilian_login
from kw import encode_kw
import zhaopin_maxpage
from ri_boss_data import BossScraper
from zhaopin_dataextuce import allPage, cache_all_page, save_to_csv


# =============== 日志配置 ===============

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =============== 配置管理类 ===============

class ConfigManager:
    """
    配置管理类，负责加载、合并和验证配置。
    可在真实项目中进一步封装从远端/数据库读取的逻辑。
    """

    def __init__(self, default_config: Dict[str, Any], parent_dir: pathlib.Path):
        """
        Args:
            default_config: 默认配置的字典
            parent_dir: 项目根目录，用于在本地查找 zhaopin.json
        """
        self.parent_dir = parent_dir
        self.config = self.load_and_merge_config(default_config)

    def load_and_merge_config(self, default: dict) -> dict:
        """
        加载 zhaopin.json 并与默认配置合并。
        若没有 zhaopin.json 或解析异常，则使用默认配置。
        """
        config = default.get("data", {})
        config_path = self.parent_dir / 'zhaopin.json'
        if config_path.exists():
            try:
                with config_path.open('r', encoding='utf-8') as f:
                    custom_config = json.load(f).get('data', {})
                for key in config.keys():
                    if key in custom_config:
                        if not any(item.get("name") == "不限" for item in custom_config[key]):
                            custom_config[key].insert(0, {"code": "0", "name": "不限"})
                        merged = [item for item in custom_config[key] if item.get("name") != "不限"]
                        config[key].extend(merged)
            except Exception as e:
                logger.error(f"加载自定义配置失败: {e}")
        return config

    def validate_option_data(self, key: str) -> List[Tuple[str, str]]:
        """
        验证并格式化配置选项，如城市列表、行业列表等。
        返回值为 [(code, name), ...] 的列表。
        """
        default = [{"code": "0", "name": "不限"}]
        validated_options: List[Tuple[str, str]] = []
        try:
            options = self.config.get(key, default)
            for option in options:
                if not isinstance(option, dict):
                    logger.warning(f"选项格式不正确: {option}")
                    continue
                code = str(option.get("code", "0"))
                name = str(option.get("name", "不限"))
                validated_options.append((code, name))

            # 确保第一个是 "不限"
            if not validated_options or validated_options[0][1] != "不限":
                validated_options.insert(0, ("0", "不限"))
        except Exception as e:
            logger.warning(f"获取 {key} 选项时出错: {e}")
            validated_options = [(str(default[0]["code"]), str(default[0]["name"]))]
        return validated_options


# =============== WebDriver 管理类 ===============

class WebDriverManager:
    """
    WebDriver 管理类，负责浏览器驱动的初始化和管理，如 Cookies、退出等。
    """

    def __init__(self):
        self.init_retries = 0
        self.max_retries = 3
        self._driver = None
        self._cookies = None

    @property
    def driver(self):
        """获取当前的 WebDriver 实例"""
        return self._driver

    @driver.setter
    def driver(self, driver):
        """设置 WebDriver 实例，如已存在其他driver，需要先退出旧的"""
        if self._driver and self._driver != driver:
            try:
                self._driver.quit()
            except Exception:
                pass
        self._driver = driver

    def save_cookies(self):
        """保存当前 driver 的 cookies 到内存（示例）"""
        if self._driver:
            self._cookies = self._driver.get_cookies()

    def load_cookies(self, url: str):
        """将内存中的 cookies 加载到当前 driver，刷新页面"""
        if self._driver and self._cookies:
            self._driver.get(url)
            for cookie in self._cookies:
                try:
                    self._driver.add_cookie(cookie)
                except Exception as e:
                    logger.warning(f"添加 cookie 失败: {e}")
            self._driver.refresh()

    def init_driver(self):
        """初始化 Chrome WebDriver，若失败则重试最多3次"""
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options

        while self.init_retries < self.max_retries:
            try:
                options = Options()
                options.add_argument('--disable-gpu')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-blink-features=AutomationControlled')
                options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

                driver = webdriver.Chrome(options=options)
                driver.set_window_size(1920, 1080)
                self.driver = driver
                return self.driver

            except Exception as e:
                self.init_retries += 1
                logger.error(f"WebDriver 初始化失败 (重试 {self.init_retries}/{self.max_retries}): {e}")

        logger.error("WebDriver 初始化失败，已达最大重试次数")
        return None

    def quit(self):
        """关闭 WebDriver 并清理资源"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logger.error(f"关闭 WebDriver 失败: {e}")
            finally:
                self.driver = None
                self._cookies = None


# =============== 智联招聘爬虫类 ===============

class ZhilianScraper:
    """
    智联招聘爬虫，示例中仅包含核心抓取逻辑，不直接使用 Streamlit。
    """

    def __init__(self, driver: Any):
        """
        Args:
            driver: 已登录的（或可用的）WebDriver 实例
        """
        if not driver:
            raise ValueError("ZhilianScraper 需要一个有效的 WebDriver 实例")
        self.driver = driver

    def get_total_pages(self, url: str) -> int:
        """
        获取搜索结果总页数。若失败则返回 0。
        """
        try:
            orig, updated = zhaopin_maxpage.test_page_input(url, existing_driver=self.driver)
            logger.info(f"测试翻页输入 - 原始页码: {orig}, 可用最大页码: {updated}")
            return updated
        except Exception as e:
            logger.error(f"获取总页数失败: {e}")
            return 0

    def crawl_pages(self, url: str, max_pages: int, table_name: str = "jobs") -> None:
        """
        爬取指定数量页的数据。
        真实项目中应在此执行循环翻页、页面解析、数据存储等。
        """
        try:
            cache_all_page(url, max_pages=max_pages, existing_driver=self.driver,table_name=table_name)
        except Exception as e:
            logger.error(f"数据爬取失败: {e}")
            # 爬虫只做日志，不直接调用UI层

    def quit(self):
        """关闭 WebDriver 并清理资源"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logger.error(f"关闭 WebDriver 失败: {e}")
            finally:
                self.driver = None
                self._cookies = None

# =============== UI 组件类 ===============

class UIComponents:
    """
    负责渲染 Streamlit 界面元素，如侧边栏、表单等。
    将爬虫或底层逻辑与 UI 分离，便于测试和维护。
    """

    def __init__(self, wdm: WebDriverManager, config_manager: ConfigManager):
        self.wdm = wdm
        self.config_manager = config_manager

    def render_sidebar(self):
        """渲染侧边栏，包含平台选择和登录操作"""
        with st.sidebar:
            st.title("爬虫平台选择")
            platform = st.radio(
                "选择招聘平台：",
                ["智联招聘", "BOSS直聘"],
                key="platform"
            )

            if platform == "智联招聘":
                st.session_state.current_platform = "zhilian"
                # 登录逻辑
                if not st.session_state.zhilian_login_status:
                    with st.form("zhilian_login"):
                        st.subheader("智联招聘登录")
                        cookie_path = st.text_input(
                            "Cookie文件路径",
                            value="cookies/zhilian_cookies.pkl",
                            help="请输入cookie文件的保存路径"
                        )
                        submitted = st.form_submit_button("登录")
                        if submitted:
                            try:
                                driver = zhilian_login.get_logged_in_driver(cookie_path)
                                if driver:
                                    st.session_state.zhilian_login_status = True
                                    st.success("智联招聘登录成功")
                                    # 使用 property setter 设置 driver
                                    self.wdm.driver = driver
                                    st.session_state.driver = driver  # 保存到session state
                                    self.wdm.save_cookies()
                                else:
                                    st.error("智联招聘登录失败，请检查登录状态或 cookie 文件")
                            except Exception as e:
                                st.error(f"登录过程出现错误: {e}")
                else:
                    st.success("已登录智联招聘")
                    if st.button("退出登录"):
                        self.wdm.quit()
                        st.session_state.zhilian_login_status = False
                        st.experimental_rerun()

            else:
                st.session_state.current_platform = "boss"
                # 示例中若需要 BOSS 登录，可在此追加
                # st.warning("示例：BOSS直聘尚未实现侧边栏登录逻辑")
                st.session_state.boss_login_status = True

            st.markdown("---")

    def render_zhilian_search_form(self):
        """
        渲染智联招聘搜索表单，生成搜索链接的部分放在一个表单中，
        后续的爬取操作则在表单外展示。
        """
        if not st.session_state.zhilian_login_status:
            st.warning("请先登录智联招聘")
            return

        # 第一部分：表单 - 生成搜索链接
        with st.form("zhilian_search_form"):
            st.subheader("基本搜索条件")
            col1, col2 = st.columns(2)

            hot_cities = self.config_manager.config.get("hotCity", [])
            industries = self.config_manager.config.get("industry", [])

            with col1:
                st.selectbox(
                    "城市",
                    options=[(c["code"], c["name"]) for c in hot_cities],
                    format_func=lambda x: x[1],
                    key="city"
                )
                st.text_input(
                    "职位关键词",
                    key="position",
                    help="请输入职位关键词"
                )

            with col2:
                st.selectbox(
                    "行业",
                    options=[(i["code"], i["name"]) for i in industries],
                    format_func=lambda x: x[1],
                    key="industry"
                )

            st.markdown("---")
            st.subheader("筛选条件")

            salary_type = self.config_manager.config.get("salaryType", [])
            work_exp_type = self.config_manager.config.get("workExpType", [])
            company_size = self.config_manager.config.get("companySize", [])
            education_type = self.config_manager.config.get("educationType", [])
            job_status = self.config_manager.config.get("jobStatus", [])
            company_type = self.config_manager.config.get("companyType", [])

            col3, col4 = st.columns(2)
            with col3:
                st.selectbox(
                    "薪资范围",
                    options=[(s["code"], s["name"]) for s in salary_type],
                    format_func=lambda x: x[1],
                    key="salary"
                )
                st.selectbox(
                    "工作经验",
                    options=[(w["code"], w["name"]) for w in work_exp_type],
                    format_func=lambda x: x[1],
                    key="work_exp"
                )
                st.selectbox(
                    "公司规模",
                    options=[(c["code"], c["name"]) for c in company_size],
                    format_func=lambda x: x[1],
                    key="company_size"
                )

            with col4:
                st.selectbox(
                    "学历要求",
                    options=[(e["code"], e["name"]) for e in education_type],
                    format_func=lambda x: x[1],
                    key="education"
                )
                st.selectbox(
                    "工作性质",
                    options=[(j["code"], j["name"]) for j in job_status],
                    format_func=lambda x: x[1],
                    key="job_type"
                )
                st.selectbox(
                    "公司性质",
                    options=[(c["code"], c["name"]) for c in company_type],
                    format_func=lambda x: x[1],
                    key="company_type"
                )

            # 表单内仅用 form_submit_button
            search_submitted = st.form_submit_button("生成搜索链接")

        # 当表单提交后，将生成的链接及最大页数存入 session_state，便于后续 UI 始终显示
        if search_submitted:
            link = self.generate_zhilian_url()
            if link:
                st.session_state.generated_link = link
                # 确保 WebDriver 已初始化
                if not self.wdm.driver:
                    st.error("WebDriver 未初始化，请先登录智联招聘")
                else:
                    zscraper = ZhilianScraper(self.wdm.driver)
                    max_pages = zscraper.get_total_pages(link)
                    if max_pages == 0:
                        st.error("无法获取有效的总页数，请检查输入参数或网络状态。")
                    else:
                        # 将 max_pages 转为整数，确保类型正确
                        st.session_state.max_pages = int(max_pages)
            else:
                st.error("生成链接失败，请检查输入参数。")

        # 如果已生成链接，则持续显示后续 UI 控件
        if "generated_link" in st.session_state and st.session_state.generated_link:
            st.success("链接生成成功：")
            st.write(st.session_state.generated_link)
            if st.session_state.max_pages > 0:  # 此时 max_pages 已经是整数类型
                max_pages = st.session_state.max_pages
                st.write(f"系统检测到的最大页码：{max_pages}")
                page_crawl_str = st.text_input("要爬取的【最大页数】", value=str(max_pages))
                
                # 添加保存方式选择控件：追加到总表 或 新建单独的表
                # save_mode = st.radio("请选择保存方式", ("追加到总表", "新建单独的表"), key="save_mode")
                
                # 此处按钮在表单外使用，不会受到限制
                star_crawl = st.button("开始爬取")
                if star_crawl:
                    try:
                        page_crawl = int(page_crawl_str)
                        if page_crawl < 1 or page_crawl > max_pages:
                            st.error(f"请输入有效的页码范围（1 ~ {max_pages}）")
                        else:
                            zscraper = ZhilianScraper(self.wdm.driver)
                            table_name = "jobs"
                            # # 根据保存方式确定 table_name
                            # if save_mode == "追加到总表":
                            #     table_name = "jobs"
                            # else:
                            #     # 新建单独的表，表名规则：城市名 + 职位关键词
                            #     city_name = st.session_state.city[1] if st.session_state.city and len(st.session_state.city) > 1 else ""
                            #     keyword = st.session_state.position.strip() if st.session_state.position else ""
                            #     if not city_name or not keyword:
                            #         st.error("新建表名需要有效的城市和职位关键词")
                            #         return
                            #     # 去除城市名中的"市"字，并将关键词中的空格替换为下划线
                            #     city_name = city_name.replace("市", "")
                            #     keyword = keyword.replace(" ", "_")
                            #     table_name = f"{city_name}_{keyword}"
                            
                            # 调用爬虫时传入 table_name 参数
                            zscraper.crawl_pages(st.session_state.generated_link, page_crawl, table_name=table_name)
                            st.success(f"爬取完成！数据已保存到表 '{table_name}'，请检查日志或数据库查看结果。")
                            zscraper.quit()
                    except ValueError:
                        st.error("页码输入非法，请输入数字。")

    def render_boss_form(self):
        """
        渲染 BOSS 直聘相关的表单示例。
        """
        st.title("BOSS直聘数据爬取")
        st.info("BOSS直聘无需登录，可直接开始爬取")

        with st.form("boss_crawler_form"):
            st.subheader("搜索配置")

            col1, col2 = st.columns(2)
            with col1:
                job_keyword = st.text_input("职位关键词", help="输入要搜索的职位关键词，例如：'python开发'")
                city_mapping = {
                    "上海": "101020100",
                    "北京": "101010100",
                    "广州": "101280100",
                    "深圳": "101280600",
                    "杭州": "101210100",
                    "成都": "101270100"
                }
                selected_city = st.selectbox("选择城市", options=list(city_mapping.keys()))

            with col2:
                use_proxy = st.checkbox("使用代理", value=False)
                proxy = None
                if use_proxy:
                    proxy_ip = st.text_input("代理IP", help="请输入代理服务器的IP地址")
                    proxy_port = st.text_input("代理端口", help="请输入代理服务器的端口号")
                    if proxy_ip and proxy_port:
                        proxy = f"{proxy_ip}:{proxy_port}"

            st.markdown("---")
            st.subheader("保存配置")
            
            # 添加保存方式选择控件：追加到总表 或 新建单独的表
            # save_mode = st.radio("请选择保存方式", ("追加到总表", "新建单独的表"), key="boss_save_mode")
            
            submitted = st.form_submit_button("开始爬取")

            if submitted:
                if not job_keyword:
                    st.error("请输入职位关键词")
                    return

                progress_bar = st.progress(0)
                status_text = st.empty()

                city_code = city_mapping[selected_city]
                data_dir = self.config_manager.parent_dir / 'data'
                scraper = BossScraper(
                    job_kw=job_keyword,
                    job_city=city_code,
                    proxy=proxy,
                    data_dir=str(data_dir)
                )

                # 如果使用代理，则进行测试
                if use_proxy and proxy:
                    status_text.text("正在测试代理...")
                    try:
                        # TODO: 实现代理测试逻辑
                        st.warning("代理测试功能尚未实现，继续使用设置的代理。")
                    except Exception as e:
                        st.error(f"代理测试失败: {e}")
                        return

                try:
                    status_text.text("正在爬取数据...")
                    scraper.run()
                    progress_bar.progress(50)

                    status_text.text("正在保存数据...")
                    # # 根据保存方式确定 table_name
                    # if save_mode == "追加到总表":
                    table_name = "jobs"
                    # else:
                    #     # 新建单独的表，表名规则：城市名 + 职位关键词
                    #     table_name = f"{selected_city}_{job_keyword}".replace(" ", "_")
                    
                    scraper.save_data(table_name)
                    progress_bar.progress(100)

                    # 释放资源
                    scraper.quit()

                    status_text.text("数据爬取完成！")
                    st.success(f"成功爬取 {len(scraper.all_jobs)} 条职位数据，已保存到表 '{table_name}'")

                    # 显示数据预览
                    if scraper.all_jobs:
                        df = pd.DataFrame(scraper.all_jobs)
                        st.subheader("数据预览")
                        st.dataframe(df.head())

                except Exception as e:
                    st.error(f"爬取过程中发生错误: {str(e)}")
                    if scraper:
                        scraper.quit()

    def generate_zhilian_url(self) -> str:
        """
        根据用户在 session_state 中的选项，生成智联搜索链接
        """
        base_url = "https://www.zhaopin.com/sou"
        city_code = st.session_state.city[0]
        position_raw = st.session_state.position
        position_encoded = encode_kw(position_raw) if position_raw else ""
        industry = st.session_state.industry[0]
        page = 1  # 搜索链接初始页，固定为 1

        url_parts = [base_url]
        if city_code != "0":
            url_parts.append(f"jl{city_code}")
        if industry != "0":
            url_parts.append(f"in{industry}")
        if position_encoded:
            url_parts.append(position_encoded)
        url_parts.append(f"p{page}")
        url = "/".join(url_parts)

        # 拼可选参数
        optional_map = [
            ('salary', 'sl'),
            ('education', 'el'),
            ('work_exp', 'we'),
            ('job_type', 'et'),
            ('company_type', 'ct'),
            ('company_size', 'cs')
        ]
        query_params = []
        for param, q in optional_map:
            value = st.session_state[param][0]
            if value != "0":
                query_params.append(f"{q}={value}")

        if query_params:
            url += "?" + "&".join(query_params)

        return url


# =============== Session 管理类 ===============

class SessionManager:
    """管理 Streamlit 的会话状态，防止重复初始化。"""

    @staticmethod
    def initialize_session_state() -> None:
        if 'init_done' not in st.session_state:
            st.session_state.init_done = True
            # 通用
            st.session_state.login_status = False
            st.session_state.login_error = None

            # 平台相关
            st.session_state.current_platform = "zhilian"
            st.session_state.zhilian_login_status = False
            st.session_state.boss_login_status = False

            # 搜索相关
            st.session_state.generated_link = ""
            st.session_state.position = ""
            st.session_state.max_pages = 0  # 添加最大页数
            # 下拉框默认
            st.session_state.city = ("0", "不限")
            st.session_state.industry = ("0", "不限")
            st.session_state.salary = ("0", "不限")
            st.session_state.work_exp = ("0", "不限")
            st.session_state.company_size = ("0", "不限")
            st.session_state.education = ("0", "不限")
            st.session_state.job_type = ("0", "不限")
            st.session_state.company_type = ("0", "不限")
            
            # WebDriver相关
            st.session_state.driver = None

            logger.info("会话状态初始化完成")


# =============== 主函数 ===============

def main():
    st.title("职位数据抓取工具 - 示例")
    SessionManager.initialize_session_state()

    # 项目根目录（假设当前文件即在根目录，也可根据需要动态获取）
    current_dir = pathlib.Path(__file__).resolve().parent
    parent_dir = current_dir.parent

    DEFAULT_CONFIG = {
        "data": {
            "hotCity": [
                {"code": "530", "name": "北京"},
                {"code": "538", "name": "上海"},
                {"code": "599", "name": "广州"},
            ],
            "industry": [
                {"code": "0", "name": "不限"},
                {"code": "10100", "name": "IT软件"},
                {"code": "20000", "name": "电子商务"}
            ],
            "salaryType": [
                {"code": "0", "name": "不限"},
                {"code": "10,20", "name": "1-2万/月"},
            ],
            "educationType": [
                {"code": "0", "name": "不限"},
                {"code": "5", "name": "本科"},
            ],
            "workExpType": [
                {"code": "0", "name": "不限"},
                {"code": "103", "name": "1-3年"},
            ],
            "jobStatus": [
                {"code": "0", "name": "不限"},
                {"code": "1", "name": "全职"},
            ],
            "companySize": [
                {"code": "0", "name": "不限"},
                {"code": "3", "name": "100-499人"},
            ],
            "companyType": [
                {"code": "0", "name": "不限"},
                {"code": "1", "name": "民营"}
            ]
        }
    }

    # 初始化配置与 WebDriver
    config_manager = ConfigManager(DEFAULT_CONFIG, parent_dir)
    wdm = WebDriverManager()
    
    # 如果session中已有driver，复用它
    if "driver" in st.session_state and st.session_state.driver is not None:
        wdm.driver = st.session_state.driver

    # 渲染 UI
    ui = UIComponents(wdm, config_manager)
    ui.render_sidebar()

    if st.session_state.current_platform == "zhilian":
        ui.render_zhilian_search_form()
    else:
        ui.render_boss_form()


if __name__ == "__main__":
    main()