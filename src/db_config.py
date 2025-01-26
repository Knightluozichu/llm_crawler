import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class DatabaseConfig:
    """
    Database configuration class
    """
    
    # MySQL Configuration
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'llm_crawler')
    MYSQL_CHARSET = 'utf8mb4'

    # MongoDB Configuration
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
    MONGO_DATABASE = os.getenv('MONGO_DATABASE', 'llm_crawler')
    MONGO_COLLECTION = os.getenv('MONGO_COLLECTION', 'raw_data')

    @classmethod
    def get_mysql_connection_string(cls):
        """
        Generate MySQL connection string
        """
        return f"mysql+mysqlconnector://{cls.MYSQL_USER}:{cls.MYSQL_PASSWORD}@" \
               f"{cls.MYSQL_HOST}:{cls.MYSQL_PORT}/{cls.MYSQL_DATABASE}?charset={cls.MYSQL_CHARSET}"

    @classmethod
    def get_mongo_connection_string(cls):
        """
        Generate MongoDB connection string
        """
        return f"{cls.MONGO_URI}{cls.MONGO_DATABASE}"
