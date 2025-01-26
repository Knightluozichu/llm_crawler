import requests
import time
import jieba
from requests.exceptions import ConnectionError
from PyPDF2 import PdfReader
import docx
import re
from io import BytesIO
from typing import List, Dict, Optional, Any
import logging
import pandas as pd

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== 修正后的导入 ==========
from langchain_community.llms import Ollama
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain

ollama_BASE_URL = "http://127.0.0.1:11434"

def get_local_models() -> List[str]:
    """
    获取 ollama 本地可用模型列表
    """
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            response = requests.get(f"{ollama_BASE_URL}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                return [model['name'] for model in models] or ["未找到可用模型"]
            logger.error(f"API返回错误状态码: {response.status_code}")
            return ["无法获取本地模型列表"]
        except ConnectionError:
            if attempt < max_retries - 1:
                logger.warning(f"连接ollama服务失败, {retry_delay}秒后重试...")
                time.sleep(retry_delay)
                continue
            logger.error("无法连接到ollama服务")
            return ["无法连接到ollama服务"]
        except Exception as e:
            logger.error(f"获取模型列表时发生错误: {str(e)}")
            return [f"获取本地模型列表时出错: {str(e)}"]

def parse_resume(file_bytes: bytes, file_type: str) -> str:
    """
    解析简历文件
    """
    try:
        if file_type == "pdf":
            reader = PdfReader(BytesIO(file_bytes))
            text = []
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text.append(extracted)
            return "\n".join(text) if text else "PDF内容为空"
            
        elif file_type in ["docx", "doc"]:
            doc = docx.Document(BytesIO(file_bytes))
            text = [para.text for para in doc.paragraphs if para.text.strip()]
            return "\n".join(text) if text else "Word文档内容为空"
            
        return "不支持的文件类型"
        
    except Exception as e:
        logger.error(f"解析{file_type}文件失败: {str(e)}")
        return f"解析失败: {str(e)}"

def match_jobs_with_resume(resume_text: str, job_df: pd.DataFrame, llm_mode: str, openai_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    简历与岗位匹配
    """
    if not resume_text or job_df.empty:
        return []

    resume_tokens = set(jieba.lcut(resume_text.lower()))
    
    results = []
    for idx, row in job_df.iterrows():
        summary = str(row.get('job_summary', '')).lower()
        salary = str(row.get('salary', '面议'))
        job_name = str(row.get('position_name', '未知岗位'))
        comp_name = str(row.get('company_name', '未知公司'))
        
        summary_tokens = set(jieba.lcut(summary))
        
        common_tokens = resume_tokens.intersection(summary_tokens)
        match_score = len(common_tokens) / (len(summary_tokens) + 1)
        
        match_reason = f"简历与岗位描述存在 {len(common_tokens)} 个相同关键词"
        
        results.append({
            "job_name": job_name,
            "company_name": comp_name,
            "match_score": round(match_score, 2),
            "match_reason": match_reason,
            "salary_range": salary,
            "job_index": idx
        })
    
    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results[:10]

def score_resume(resume_text: str) -> str:
    """
    简历评分
    """
    work_pattern = r"工作经历[:：](.*?)教育背景[:：]"
    edu_pattern = r"教育背景[:：](.*?)技能[:：]"
    skill_pattern = r"技能[:：](.*?)优势[:：]"
    adv_pattern = r"优势[:：](.*)"

    work_match = re.search(work_pattern, resume_text, re.S)
    edu_match = re.search(edu_pattern, resume_text, re.S)
    skill_match = re.search(skill_pattern, resume_text, re.S)
    adv_match = re.search(adv_pattern, resume_text, re.S)

    work_score = 40 if work_match else 0
    edu_score = 20 if edu_match else 0
    skill_score = 30 if skill_match else 0
    adv_score = 10 if adv_match else 0
    total_score = work_score + edu_score + skill_score + adv_score

    report_lines = [
        f"工作经历得分: {work_score}/40",
        f"教育背景得分: {edu_score}/20",
        f"技能得分: {skill_score}/30",
        f"优势得分: {adv_score}/10",
        f"综合得分: {total_score}/100"
    ]
    return "\n".join(report_lines)

def modify_resume_for_job(original_resume: str, job_description: str, llm_mode: str, openai_key: Optional[str] = None) -> str:
    """
    简历优化核心函数
    """
    # 使用聊天模型专用模板
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", "你是一名专业HR，需要根据岗位需求优化简历。请保持专业且简洁。"),
        ("user", """
        # 岗位描述
        {job_description}

        # 原始简历
        {original_resume}

        请输出优化后的简历内容：
        """)
    ])

    # 模型选择逻辑
    if llm_mode == "local":
        llm = Ollama(
            base_url=ollama_BASE_URL,
            model="llama3.2:latest",
            temperature=0.5
        )
    elif llm_mode == "openai":
        llm = ChatOpenAI(
            openai_api_key=openai_key,
            model_name="gpt-4-1106-preview",  # 使用最新模型
            temperature=0.7
        )
    else:
        return "无效的LLM模式"

    # 构建处理链
    chain = LLMChain(llm=llm, prompt=prompt_template)
    
    # 执行请求
    try:
        response = chain.invoke({
            "job_description": job_description,
            "original_resume": original_resume
        })
        return response["text"]
    except Exception as e:
        logger.error(f"简历优化失败: {str(e)}")
        return f"优化服务暂时不可用: {str(e)}"