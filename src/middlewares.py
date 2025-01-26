import random
from scrapy import signals
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.utils.response import response_status_message

class RandomUserAgentMiddleware:
    """随机 User-Agent 中间件"""
    
    def __init__(self, user_agents):
        self.user_agents = user_agents

    @classmethod
    def from_crawler(cls, crawler):
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        return cls(user_agents)

    def process_request(self, request, spider):
        request.headers['User-Agent'] = random.choice(self.user_agents)

class ProxyMiddleware:
    """代理中间件"""
    
    def __init__(self, proxy_list):
        self.proxy_list = proxy_list

    @classmethod
    def from_crawler(cls, crawler):
        proxy_list = [
            'http://proxy1.example.com:8080',
            'http://proxy2.example.com:8080',
            'http://proxy3.example.com:8080'
        ]
        return cls(proxy_list)

    def process_request(self, request, spider):
        proxy = random.choice(self.proxy_list)
        request.meta['proxy'] = proxy

class CustomRetryMiddleware(RetryMiddleware):
    """自定义重试中间件"""
    
    def process_response(self, request, response, spider):
        if response.status in [403, 429]:
            reason = response_status_message(response.status)
            return self._retry(request, reason, spider) or response
        return super().process_response(request, response, spider)
