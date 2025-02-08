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
import json

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== 修正后的导入 ==========
from langchain_ollama import OllamaLLM
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain

ollama_BASE_URL = "http://127.0.0.1:11434"


# 拆分 langchain 逻辑到独立类
class LLMIntegration:
    def __init__(
        self,
        llm_mode: str,
        openai_key: Optional[str] = None,
        deepseek_key: Optional[str] = None,
    ):
        self.llm_mode = llm_mode.strip().lower()  # 标准化模式字符串
        self.openai_key = openai_key
        self.deepseek_key = deepseek_key
        self.ollama_model = None
        
    def change_llm_mode(self, llm_mode: str):
        """改变 llm_mode 属性，确保标准化处理"""
        self.llm_mode = llm_mode.strip().lower()
        
    def set_local_model(self, model: str):
        """设置 ollama 的本地模型"""
        self.ollama_model = model

    def call_llm(self, prompt: str) -> str:
        """
        通用的 LLM 调用逻辑，不区分具体任务，返回 LLM 输出文本
        """
        logger.info(f"llm_mode: {self.llm_mode}")
        if self.llm_mode == "local":
            llm = OllamaLLM(
                base_url=ollama_BASE_URL, 
                model="llama3.2:latest" if self.ollama_model is None else self.ollama_model, 
                temperature=0.1
            )
        elif self.llm_mode == "openai":
            llm = ChatOpenAI(
                openai_api_key=self.openai_key, 
                model_name="gpt-4", 
                temperature=0.1
            )
        elif self.llm_mode == "deepseek":
            if not self.deepseek_key:
                return "请提供 Deepseek API Key"
            llm = ChatOpenAI(
                api_key=self.deepseek_key,
                model_name="deepseek-chat",
                temperature=0.1,
                base_url="https://api.deepseek.com/v1",
            )
        else:
            return "无效的LLM模式"
        try:
            # 使用通用 prompt 模板包装
            prompt_template = ChatPromptTemplate.from_messages([
                ("system", "你是一名专业HR，请根据提示完成任务。输出返回结果以 json 形式"),
                ("user", "{input}")
            ])
            chain = LLMChain(llm=llm, prompt=prompt_template)
            response = chain.invoke({"input": prompt})
            
            # 检查返回结果是否为空
            if not response or "text" not in response:
                logger.error("LLM 返回了无效的响应格式")
                return ""
            
            return response["text"]

        except Exception as e:
            logger.info(f"----------\n{prompt}\n----------")
            logger.error(f"LLM调用失败: {str(e)}")
            return f"LLM调用失败: {str(e)}"


class LLMHR:
    def __init__(
        self,
        llm_mode: str = "openai",
        openai_key: Optional[str] = None,
        deepseek_key: Optional[str] = None,
    ):
        # 初始化 LLMIntegration 实例作为成员变量
        self.llm_integration = LLMIntegration(llm_mode, openai_key, deepseek_key)

    # 改变 llm_mode 属性
    def change_llm_mode(self, llm_mode: str):
        self.llm_integration.change_llm_mode(llm_mode)
        
        
    # 设置 ollama 的本地模型
    def set_local_model(self, model: str):
        self.llm_integration.set_local_model(model)
    
    def _call_llm(self, prompt: str) -> str:
        """
        封装统一的 LLM 调用逻辑
        """
        return self.llm_integration.call_llm(prompt)

    def get_local_models(self) -> List[str]:
        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                response = requests.get(f"{ollama_BASE_URL}/api/tags", timeout=5)
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    return [model["name"] for model in models] or ["未找到可用模型"]
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

    def parse_resume(self, file_bytes: bytes, file_type: str) -> str:
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


    def modify_resume_for_job(self, original_resume: str, job_description: str) -> str:
        """
        简历优化：根据岗位描述优化简历
        """
        prompt = f"""
请根据岗位需求优化简历内容。保持专业且简洁，突出与岗位相关的技能和经验。

# 岗位描述
{job_description}

# 原始简历
{original_resume}

请输出优化后的简历内容：
"""
        return self._call_llm(prompt)

    def _extract_json_from_text(self, text: str) -> Optional[str]:
        """
        从文本中提取 JSON 字符串。
        支持提取 {} 或 [] 包裹的 JSON，并处理可能的前缀后缀文本。
        """
        if not text or not text.strip():
            return None
            
        # 尝试查找第一个有效的 JSON 块（{} 或 []）
        json_pattern = r'(\{(?:[^{}]|(?:\{[^{}]*\}))*\}|\[(?:[^\[\]]|(?:\[[^\[\]]*\]))*\])'
        match = re.search(json_pattern, text, re.DOTALL)
        
        if match:
            potential_json = match.group(1).strip()
            try:
                # 验证提取的内容是否为有效 JSON
                json.loads(potential_json)
                return potential_json
            except json.JSONDecodeError:
                return None
        return None

    def match_jobs_with_resume_llm(
        self, resume_text: str, job_df: pd.DataFrame
    ) -> List[Dict[str, Any]]:
        """
        使用 LLM 对简历和岗位信息进行匹配分析，返回 JSON 格式的匹配结果列表。
        每个元素包含：
          - job_name: 岗位名称
          - company_name: 公司名称
          - match_score: 匹配分数（0-1之间的浮点数）
          - match_reason: 匹配原因说明
        """
        if not resume_text or job_df.empty:
            logger.warning("简历文本为空或岗位列表为空")
            return []

        jobs_summary = []
        for idx, row in job_df.iterrows():
            job_name = row.get("position_name", "未知岗位")
            comp_name = row.get("company_name", "未知公司")
            summary = row.get("job_summary", "")
            salary = row.get("salary", "面议")
            jobs_summary.append(
                f"岗位: {job_name}\n公司: {comp_name}\n薪资: {salary}\n描述: {summary}"
            )

        # 加强 prompt，确保严格的 JSON 输出
        prompt = f"""请将以下简历与岗位进行匹配分析，并以严格的 JSON 格式输出结果。

# 分析要求
1. 评估简历与每个岗位的匹配程度
2. 给出0-1之间的匹配分数（分数越高表示匹配度越高）
3. 简要说明匹配原因，包括技能匹配度、经验要求等关键因素

# 简历文本
{resume_text}

# 岗位列表
{chr(10).join(jobs_summary)}

# 输出要求
1. 必须且只能输出一个合法的 JSON 数组
2. 不要包含任何其他文字说明
3. 不要使用 Markdown 代码块
4. 每个数组元素必须包含以下字段：
   - job_name: 岗位名称（字符串）
   - company_name: 公司名称（字符串）
   - match_score: 匹配分数（0-1之间的浮点数）
   - match_reason: 匹配原因说明（不超过50字的字符串）
5. 结果必须按匹配分数从高到低排序

示例格式（仅供参考格式，请根据实际内容输出）：
[{{"job_name":"软件工程师","company_name":"科技公司","match_score":0.85,"match_reason":"技能匹配度高"}}]

重要：只输出 JSON 数组，不要有任何其他内容！"""

        response_text = self._call_llm(prompt)
        logger.debug(f"LLM 返回的原始文本: {response_text}")
        
        # 尝试提取和解析 JSON
        if not response_text or not response_text.strip():
            logger.error("LLM 返回了空的结果")
            return []
            
        # 尝试提取 JSON 内容
        json_str = self._extract_json_from_text(response_text)
        if not json_str:
            # logger.error("未能从 LLM 返回结果中提取有效的 JSON")
            logger.error(f"未能从 LLM 返回结果中提取有效的 JSON 原始返回文本: {response_text}")
            return []
            
        try:
            # 解析 JSON
            result = json.loads(json_str)
            
            # 验证结果格式
            if not isinstance(result, list):
                logger.error("LLM 返回的结果不是列表格式")
                return []
                
            # 验证和清理每个结果项
            valid_results = []
            for item in result:
                if not isinstance(item, dict):
                    continue
                    
                # 确保必要字段存在且格式正确
                if not all(k in item for k in ["job_name", "company_name", "match_score", "match_reason"]):
                    continue
                    
                # 确保 match_score 是 0-1 之间的浮点数
                try:
                    score = float(item["match_score"])
                    if not 0 <= score <= 1:
                        continue
                    # 标准化分数格式
                    item["match_score"] = round(score, 2)
                except (ValueError, TypeError):
                    continue
                    
                # 清理文本字段
                item["job_name"] = str(item["job_name"]).strip()
                item["company_name"] = str(item["company_name"]).strip()
                item["match_reason"] = str(item["match_reason"]).strip()[:50]  # 限制长度
                
                valid_results.append(item)
            
            # 按匹配分数排序
            valid_results.sort(key=lambda x: float(x["match_score"]), reverse=True)
            
            # 添加额外信息
            for idx, item in enumerate(valid_results):
                item["job_index"] = idx
                item["salary_range"] = (
                    job_df.iloc[idx].get("salary", "面议")
                    if idx < len(job_df)
                    else "未知"
                )
            return valid_results
            
        except json.JSONDecodeError as e:
            logger.error(f"解析 JSON 失败: {e}")
            logger.debug(f"尝试解析的 JSON 字符串: {json_str}")
            return []
        except Exception as e:
            logger.error(f"处理匹配结果时发生错误: {e}")
            return []
   

    def score_resume_llm(self, resume_text: str) -> str:
        """
        使用 LLM 对简历进行评分，并输出详细评分报告
        评分标准：
          - 工作经历（40分）：评估工作经验的相关性、连续性和进步性
          - 教育背景（20分）：评估学历水平和专业相关性
          - 技能（30分）：评估技术技能的广度和深度
          - 优势（10分）：评估个人特长和竞争优势
        """
        prompt = f"""
请对以下简历进行全面评估和打分。

# 评分标准
1. 工作经历（40分）：
   - 工作经验的相关性
   - 职业发展的连续性
   - 职位晋升的进步性

2. 教育背景（20分）：
   - 学历水平
   - 专业相关性
   - 学习成果

3. 技能（30分）：
   - 专业技能的广度
   - 核心技能的深度
   - 技能的实践程度

4. 优势（10分）：
   - 个人特长
   - 竞争优势

# 简历文本
{resume_text}

# 输出要求
请输出评分报告，格式如下：
工作经历得分: XX/40
教育背景得分: XX/20
技能得分: XX/30
优势得分: XX/10
综合得分: XX/100

每项得分后请附带简要说明（不超过50字）。
"""
        return self._call_llm(prompt)
