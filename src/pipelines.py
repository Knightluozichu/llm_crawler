import pymongo
import mysql.connector
from src.db_config import MONGODB_CONFIG, MYSQL_CONFIG
from itemadapter import ItemAdapter

class MongoDBPipeline:
    """MongoDB 数据存储管道"""
    
    def open_spider(self, spider):
        """爬虫启动时连接数据库"""
        self.client = pymongo.MongoClient(MONGODB_CONFIG['uri'])
        self.db = self.client[MONGODB_CONFIG['database']]
        self.collection = self.db[MONGODB_CONFIG['collection']]
        
    def close_spider(self, spider):
        """爬虫关闭时断开连接"""
        self.client.close()
        
    def process_item(self, item, spider):
        """处理Item"""
        item_dict = ItemAdapter(item).asdict()
        self.collection.update_one(
            {'url': item_dict['url']},
            {'$set': item_dict},
            upsert=True
        )
        return item

class MySQLPipeline:
    """MySQL 数据存储管道"""
    
    def open_spider(self, spider):
        """爬虫启动时连接数据库"""
        self.connection = mysql.connector.connect(
            host=MYSQL_CONFIG['host'],
            user=MYSQL_CONFIG['user'],
            password=MYSQL_CONFIG['password'],
            database=MYSQL_CONFIG['database']
        )
        self.cursor = self.connection.cursor()
        
        # 创建文章表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INT AUTO_INCREMENT PRIMARY KEY,
                url VARCHAR(512) UNIQUE,
                title TEXT,
                content LONGTEXT,
                published_at DATETIME,
                source VARCHAR(128),
                crawled_at DATETIME,
                keywords TEXT,
                summary TEXT,
                author VARCHAR(256),
                category VARCHAR(128),
                tags TEXT,
                metadata JSON
            )
        ''')
        self.connection.commit()
        
    def close_spider(self, spider):
        """爬虫关闭时断开连接"""
        self.cursor.close()
        self.connection.close()
        
    def process_item(self, item, spider):
        """处理Item"""
        item_dict = ItemAdapter(item).asdict()
        
        # 插入或更新数据
        self.cursor.execute('''
            INSERT INTO articles (
                url, title, content, published_at, source, crawled_at,
                keywords, summary, author, category, tags, metadata
            ) VALUES (
                %s, %s, %s, %s, %s, NOW(),
                %s, %s, %s, %s, %s, %s
            )
            ON DUPLICATE KEY UPDATE
                title = VALUES(title),
                content = VALUES(content),
                published_at = VALUES(published_at),
                source = VALUES(source),
                crawled_at = VALUES(crawled_at),
                keywords = VALUES(keywords),
                summary = VALUES(summary),
                author = VALUES(author),
                category = VALUES(category),
                tags = VALUES(tags),
                metadata = VALUES(metadata)
        ''', (
            item_dict['url'],
            item_dict['title'],
            item_dict['content'],
            item_dict['published_at'],
            item_dict['source'],
            item_dict['keywords'],
            item_dict['summary'],
            item_dict['author'],
            item_dict['category'],
            item_dict['tags'],
            item_dict['metadata']
        ))
        self.connection.commit()
        return item
