#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import time
import logging
from typing import Optional, Dict, List
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BossLogin:
    """BOSS直聘登录管理类"""
    
    def __init__(self, cookie_path: str):
        """
        初始化登录管理器
        
        Args:
            cookie_path: cookie文件保存路径
        """
        self.cookie_path = str(cookie_path)  # 确保是字符串类型
        self.base_url = "https://www.zhipin.com"
        self.login_url = "https://www.zhipin.com/web/user/?ka=header-login"
        
    def init_driver(self) -> Optional[webdriver.Chrome]:
        """
        初始化Chrome WebDriver
        
        Returns:
            Optional[webdriver.Chrome]: 成功返回driver实例，失败返回None
        """
        try:
            options = Options()
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            # 添加自定义header
            options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            driver = webdriver.Chrome(options=options)
            driver.set_window_size(1920, 1080)
            return driver
        except Exception as e:
            logger.error(f"初始化WebDriver失败: {e}")
            return None

    def save_cookies(self, driver: webdriver.Chrome) -> bool:
        """
        保存cookies到文件
        
        Args:
            driver: WebDriver实例
            
        Returns:
            bool: 保存是否成功
        """
        try:
            cookies = driver.get_cookies()
            # 过滤和处理cookie
            processed_cookies = []
            for cookie in cookies:
                # 移除可能导致问题的字段
                cookie.pop('expiry', None)
                cookie.pop('sameSite', None)
                processed_cookies.append(cookie)
                
            with open(self.cookie_path, 'w', encoding='utf-8') as f:
                json.dump(processed_cookies, f)
            logger.info("Cookies保存成功")
            return True
        except Exception as e:
            logger.error(f"保存cookies失败: {e}")
            return False

    def load_cookies(self, driver: webdriver.Chrome) -> bool:
        """
        从文件加载cookies
        
        Args:
            driver: WebDriver实例
            
        Returns:
            bool: 加载是否成功
        """
        try:
            if not os.path.exists(self.cookie_path):
                logger.info("Cookie文件不存在")
                return False
                
            with open(self.cookie_path, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
                
            # 先访问目标网站
            driver.get(self.base_url)
            time.sleep(2)
            
            # 添加cookies
            for cookie in cookies:
                try:
                    driver.add_cookie(cookie)
                except Exception as e:
                    logger.warning(f"添加单个cookie失败: {e}")
                    continue
            
            logger.info("Cookies加载完成")
            return True
        except Exception as e:
            logger.error(f"加载cookies失败: {e}")
            return False

    def check_login_status(self, driver: webdriver.Chrome) -> bool:
        """
        检查是否已登录
        
        Args:
            driver: WebDriver实例
            
        Returns:
            bool: 是否已登录
        """
        try:
            driver.get(self.base_url)
            time.sleep(3)  # 等待页面加载
            
            # 检查登录状态的多个可能元素
            login_indicators = [
                "//div[contains(@class, 'user-nav')]",     # 用户导航区域
                "//a[contains(@href, '/web/geek/')]",      # 个人主页链接
                "//div[contains(@class, 'avatar')]"        # 头像区域
            ]
            
            for indicator in login_indicators:
                try:
                    element = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, indicator))
                    )
                    if element.is_displayed():
                        logger.info("检测到登录状态")
                        return True
                except:
                    continue
            
            logger.info("未检测到登录状态")
            return False
        except Exception as e:
            logger.error(f"检查登录状态时发生错误: {e}")
            return False

    def login(self) -> Optional[webdriver.Chrome]:
        """
        执行登录流程
        
        Returns:
            Optional[webdriver.Chrome]: 登录成功返回driver实例，失败返回None
        """
        driver = None
        try:
            driver = self.init_driver()
            if not driver:
                return None

            # 尝试加载cookies
            if self.load_cookies(driver):
                if self.check_login_status(driver):
                    logger.info("使用cookies登录成功")
                    return driver
                else:
                    logger.info("cookies已失效，需要重新登录")
            
            # 如果cookie登录失败，等待手动登录
            driver.get(self.login_url)
            logger.info("等待手动登录...")
            
            # 等待登录成功
            max_wait_time = 300  # 最多等待5分钟
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                if self.check_login_status(driver):
                    logger.info("登录成功")
                    self.save_cookies(driver)
                    return driver
                time.sleep(2)
            
            logger.error("登录超时")
            return None
            
        except Exception as e:
            logger.error(f"登录过程发生错误: {e}")
            if driver:
                driver.quit()
            return None

def get_logged_in_driver(cookie_path: str) -> Optional[webdriver.Chrome]:
    """
    获取已登录的WebDriver实例
    
    Args:
        cookie_path: cookie文件保存路径
        
    Returns:
        Optional[webdriver.Chrome]: 登录成功返回driver实例，失败返回None
    """
    login_manager = BossLogin(cookie_path)
    return login_manager.login()
