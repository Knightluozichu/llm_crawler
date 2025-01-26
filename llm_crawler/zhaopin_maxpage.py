from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
import time
import logging

def test_page_input(url: str, test_page: int = 99999, existing_driver=None) -> tuple:
    """
    测试页码输入框功能
    
    Args:
        url: 智联招聘搜索页面URL
        test_page: 要测试输入的页码值
        existing_driver: 复用现有的driver
        
    Returns:
        tuple: (原始页码值, 更新后的页码值)
        
    Example:
        >>> url = 'https://www.zhaopin.com/sou/...'
        >>> original, updated = test_page_input(url, 100)
        >>> print(f"原始值: {original}, 更新后: {updated}")
    """
    driver = None
    should_quit = False
    try:
        if existing_driver:
            driver = existing_driver
            driver.get(url)
        else:
            # 对于获取总页数，使用普通模式而不是无头模式
            driver = webdriver.Chrome()
            should_quit = True
            driver.get(url)
            
        wait = WebDriverWait(driver, 10)
        
        page_number_input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".soupager__pagebox__goinp"))
        )
        
        original_value = page_number_input.get_attribute('value')
        
        page_number_input.clear()
        page_number_input.send_keys(str(test_page))
        time.sleep(1)  # 等待输入生效
        
        new_value = page_number_input.get_attribute('value')
        return original_value, new_value
        
    except Exception as e:
        logging.error(f"测试页码输入时发生错误: {e}")
        return None, None
        
    finally:
        if driver and should_quit:
            driver.quit()

if __name__ == '__main__':
    # 设置日志级别
    logging.basicConfig(level=logging.INFO)
    
    # 测试URL
    test_url = r'https://www.zhaopin.com/sou/jl538/in100000000/kw01L00O80EO062/p1?el=-1&et=-1&ct=0&cs=-1&sl=0000,9999999&at=3791f21ae1a44ac89aad75a585f71a6b&rt=0572626bdbc541f987fe084b59b7774b&userID=662930804'
    
    
    # 测试页码输入
    orig, updated = test_page_input(test_url)
    print(f"原始页码值: {orig}")
    print(f"更新后的页码值: {updated}")