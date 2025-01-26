from src.spiders.base_spider import BaseSpider
from src.items import ArticleItem
from scrapy.http import Request
from scrapy.selector import Selector
from urllib.parse import urljoin

class TechBlogSpider(BaseSpider):
    """
    技术博客爬虫示例
    """
    name = 'tech_blog'
    allowed_domains = ['example-tech-blog.com']
    start_urls = ['https://example-tech-blog.com/articles']

    def parse(self, response):
        """
        解析文章列表页
        """
        sel = Selector(response)
        articles = sel.css('div.article-item')
        
        for article in articles:
            item = ArticleItem()
            item['title'] = article.css('h2.title::text').get()
            item['url'] = urljoin(response.url, article.css('a::attr(href)').get())
            item['summary'] = article.css('p.summary::text').get()
            item['publish_date'] = article.css('span.date::text').get()
            
            # 请求文章详情页
            yield Request(
                url=item['url'],
                callback=self.parse_article,
                meta={'item': item}
            )

        # 处理分页
        next_page = sel.css('a.next-page::attr(href)').get()
        if next_page:
            yield Request(
                url=urljoin(response.url, next_page),
                callback=self.parse
            )

    def parse_article(self, response):
        """
        解析文章详情页
        """
        item = response.meta['item']
        sel = Selector(response)
        
        item['content'] = sel.css('div.article-content').get()
        item['tags'] = sel.css('div.tags a::text').getall()
        item['author'] = sel.css('span.author::text').get()
        
        yield item
