# -*- coding: utf-8 -*-
import os
import pickle
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def is_login_success(driver):
    """判断是否登录成功"""
    try:
        # 使用显式等待查找登录状态元素
        wait = WebDriverWait(driver, 5)
        user_element = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "c-login__top__name"))
        )
        print("检测到登录状态元素，登录成功")
        return True
    except Exception as e:
        print(f"未检测到登录状态元素，登录失败: {e}")
        return False

def get_logged_in_driver(url=None, cookies_file="cookies.pkl", chrome_options=None):
    """
    获取一个已登录的WebDriver实例
    
    Args:
        url (str): 目标URL，如果为None则使用zlzp首页
        cookies_file (str): Cookie文件保存路径
        chrome_options (Options): Chrome浏览器配置，如果为None则使用默认配置
    
    Returns:
        webdriver.Chrome: 已登录的WebDriver实例
    """
    if url is None:
        url = "https://www.zhaopin.com/"
        
    if chrome_options is None:
        chrome_options = Options()
        
    driver = webdriver.Chrome(options=chrome_options)
    
    # 尝试使用已保存的cookies
    if os.path.exists(cookies_file):
        print("检测到本地存在Cookies文件，尝试加载...")
        driver.get("https://www.zhaopin.com/")
        
        with open(cookies_file, "rb") as f:
            cookies = pickle.load(f)
        for cookie in cookies:
            if 'expiry' in cookie:
                del cookie['expiry']
            driver.add_cookie(cookie)
        
        driver.get(url)
        time.sleep(3)
        
        if is_login_success(driver):
            print("已检测到登录状态，无需手动登录！")
            return driver
        print("Cookie 似乎已经失效，需要手动登录...")
    else:
        print("本地无Cookies文件，需要手动登录...")
    
    # 执行手动登录流程
    driver.get(url)
    input("请在浏览器中完成登录后，按回车继续...")
    
    if is_login_success(driver):
        cookies = driver.get_cookies()
        with open(cookies_file, "wb") as f:
            pickle.dump(cookies, f)
        print("登录成功，Cookie已保存/更新到本地文件。")
        return driver
    else:
        print("登录失败，请重新检查。")
        driver.quit()
        return None

def main():
    """示例用法"""
    url = "https://www.zhaopin.com/sou/jl538/in100000000/kw01L00O80EO062/p1?el=-1&et=-1&ct=0&cs=-1&sl=0000,9999999&at=3791f21ae1a44ac89aad75a585f71a6b&rt=0572626bdbc541f987fe084b59b7774b&userID=662930804"
    
    driver = get_logged_in_driver(url=url)
    if driver:
        # 业务操作演示
        time.sleep(5)
        driver.quit()

if __name__ == "__main__":
    main()