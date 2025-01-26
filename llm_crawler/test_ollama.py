import requests
from requests.exceptions import ConnectionError
import time

OLLAMA_BASE_URL = "http://127.0.0.1:11434"

def get_local_models():
    """获取Ollama可用模型列表"""
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                return [model['name'] for model in models]
            else:
                print(f"API返回错误状态码: {response.status_code}")
                return None
                
        except ConnectionError:
            if attempt < max_retries - 1:
                print(f"连接Ollama服务失败, {retry_delay}秒后重试...")
                time.sleep(retry_delay)
            else:
                print("无法连接到Ollama服务, 请确保服务已启动")
                return None
                
        except Exception as e:
            print(f"获取模型列表时发生错误: {str(e)}")
            return None

def check_ollama_health():
    """检查Ollama服务是否正常运行"""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/version", timeout=2)
        return response.status_code == 200
    except:
        return False

# 使用示例
if check_ollama_health():
    models = get_local_models()
    if models:
        print(f"可用模型: {models}")
else:
    print("Ollama服务未运行，请先启动服务")