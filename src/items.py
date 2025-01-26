import scrapy

class ArticleItem(scrapy.Item):
    """文章Item类"""
    url = scrapy.Field()  # 文章URL
    title = scrapy.Field()  # 文章标题
    content = scrapy.Field()  # 文章内容
    published_at = scrapy.Field()  # 发布日期
    source = scrapy.Field()  # 来源网站
    crawled_at = scrapy.Field()  # 爬取时间
    keywords = scrapy.Field()  # 关键词
    summary = scrapy.Field()  # 摘要
    author = scrapy.Field()  # 作者
    category = scrapy.Field()  # 分类
    tags = scrapy.Field()  # 标签
    image_urls = scrapy.Field()  # 图片URL列表
    images = scrapy.Field()  # 图片信息
    metadata = scrapy.Field()  # 元数据
