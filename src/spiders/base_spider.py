import scrapy
from scrapy import signals
from scrapy.exceptions import CloseSpider
from scrapy.http import Request
from scrapy.utils.project import get_project_settings
from scrapy.utils.response import response_status_message
from twisted.internet.error import TimeoutError, TCPTimedOutError
from twisted.web._newclient import ResponseFailed

class BaseSpider(scrapy.Spider):
    """
    Base spider class with common functionality for all spiders
    """
    
    custom_settings = {
        'RETRY_ENABLED': True,
        'RETRY_TIMES': 3,
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429],
        'DOWNLOAD_TIMEOUT': 60,
        'DOWNLOAD_MAXSIZE': 10 * 1024 * 1024,  # 10MB
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.settings = get_project_settings()
        self.failed_urls = []

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.handle_spider_closed, signals.spider_closed)
        return spider

    def handle_spider_closed(self, spider, reason):
        """
        Handle spider closed signal
        """
        if self.failed_urls:
            self.logger.warning(f"Failed URLs: {len(self.failed_urls)}")
            self.logger.debug(f"Failed URLs list: {self.failed_urls}")

    def start_requests(self):
        """
        Generate initial requests
        """
        for url in self.start_urls:
            yield Request(
                url=url,
                callback=self.parse,
                errback=self.handle_error,
                meta={
                    'max_retry_times': self.settings.get('RETRY_TIMES'),
                    'download_timeout': self.settings.get('DOWNLOAD_TIMEOUT'),
                }
            )

    def handle_error(self, failure):
        """
        Handle request errors
        """
        if failure.check(TimeoutError, TCPTimedOutError, ResponseFailed):
            url = failure.request.url
            self.failed_urls.append(url)
            self.logger.error(f"TimeoutError: {url}")
        elif failure.check(HttpError):
            response = failure.value.response
            self.logger.error(f"HttpError: {response.url} - {response.status}")
        else:
            self.logger.error(repr(failure))

    def parse(self, response):
        """
        Default parse method to be overridden by child classes
        """
        raise NotImplementedError("Please implement parse method in child class")
