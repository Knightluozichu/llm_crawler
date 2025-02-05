from DrissionPage import ChromiumPage

# 创建一个 ChromiumPage 对象
page = ChromiumPage()

# 打开一个网页
page.get('https://www.baidu.com')

# 打印网页标题
print(page.title)