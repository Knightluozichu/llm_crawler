import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import jieba
import streamlit as st
from collections import Counter
import re
from wordcloud import WordCloud
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import os
from pathlib import Path
import matplotlib.font_manager as fm
from io import BytesIO
import requests
from requests.exceptions import ConnectionError
import time

# ========== Ollama本地服务相关示例函数 ==========

OLLAMA_BASE_URL = "http://127.0.0.1:11434"

def get_local_models():
    """获取Ollama可用模型列表(示例)，如果连接失败或接口结构有变，可自行调整。"""
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
                return ["无法获取本地模型列表"]
        except ConnectionError:
            if attempt < max_retries - 1:
                print(f"连接Ollama服务失败, {retry_delay}秒后重试...")
                time.sleep(retry_delay)
            else:
                print("无法连接到Ollama服务, 请确保服务已启动")
                return ["无法连接到Ollama服务"]
        except Exception as e:
            print(f"获取模型列表时发生错误: {str(e)}")
            return [f"获取本地模型列表时出错: {str(e)}"]

# ========== 模拟/占位: LLM 调用的简历解析、匹配与修改逻辑 ==========

def parse_resume(file_bytes, file_type):
    """
    占位函数：解析用户上传的简历（PDF或Word），返回文本内容。
    实际可使用 PyMuPDF、PyPDF2、python-docx 等库处理。
    """
    try:
        if file_type == "pdf":
            # 示例处理 PDF
            return "【PDF简历】这里是解析得到的简历文本内容……"
        elif file_type in ["docx", "doc"]:
            # 示例处理 Word
            return "【Word简历】这里是解析得到的简历文本内容……"
        else:
            return "暂不支持的文件类型，无法解析。"
    except Exception:
        return "解析失败，请检查简历文件格式或内容。"

def match_jobs_with_resume(resume_text, job_df, llm_mode, openai_key=None):
    """
    将简历与 job_df 的岗位数据进行匹配，并返回前 10 条最匹配结果。
    这里的逻辑仅作演示，可根据需要调用真实大模型或更复杂的算法。

    返回示例格式：
    [
      {
        "job_name": "...",
        "company_name": "...",
        "match_score": 0.85,
        "match_reason": "匹配原因说明，如技能点对应",
        "salary_range": "10-15k",
        "job_index": 123   # 原表中的index或唯一ID
      },
      ...
    ]
    """
    # 简化方式：根据 resume_text 中出现的技能/关键词 与 岗位 job_summary 进行匹配
    if not resume_text or job_df.empty:
        return []

    # 分词简历
    resume_tokens = set(jieba.lcut(resume_text.lower()))
    
    results = []
    for idx, row in job_df.iterrows():
        summary = str(row.get('job_summary', '')).lower()
        salary = str(row.get('salary', '面议'))
        job_name = str(row.get('position_name', '未知岗位'))
        comp_name = str(row.get('company_name', '未知公司'))
        
        # 分词岗位描述
        summary_tokens = set(jieba.lcut(summary))
        
        # 简易匹配度计算：交集词数 / (简历词数+岗位词数的一部分)
        common_tokens = resume_tokens.intersection(summary_tokens)
        # 避免除零错误，增加一个最小值1
        match_score = len(common_tokens) / (len(summary_tokens) + 1)
        
        # 简单模拟打分区间 0-1, 也可进一步缩放、权重处理
        match_reason = f"简历与岗位描述存在 {len(common_tokens)} 个相同关键词"
        
        results.append({
            "job_name": job_name,
            "company_name": comp_name,
            "match_score": round(match_score, 2),
            "match_reason": match_reason,
            "salary_range": salary,
            "job_index": idx
        })
    
    # 按匹配度排序后，取前10条
    results.sort(key=lambda x: x["match_score"], reverse=True)
    top_10 = results[:10]
    
    return top_10

def modify_resume_for_job(original_resume, job_description, llm_mode, openai_key=None):
    """
    基于 original_resume 与 job_description，生成个性化修改后的简历文本。
    可在此调用本地LLM或OpenAI API。
    此处仍为演示示例。
    """
    new_resume = (
        "【AI修改后的简历示例】\n\n"
        f"=== 原简历部分内容 ===\n{original_resume[:100]}...\n\n"
        f"=== 目标岗位需求 ===\n{job_description}\n\n"
        "=== 优化后简历示例 ===\n"
        "这里添加更契合目标岗位的技能描述，突出匹配的项目经验、技术栈等。"
    )
    return new_resume

# ========== 可视化部分的DataVisualizer类 ==========

class DataVisualizer:
    def __init__(self, csv_path):
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"找不到数据文件: {csv_path}")
        self.df = pd.read_csv(csv_path)
        self.preprocess_data()
        
    def preprocess_data(self):
        """预处理数据，如提取工资上下限"""
        def extract_salary(salary_str):
            if pd.isna(salary_str):
                return [None, None]
            nums = re.findall(r'(\d+\.?\d*)', str(salary_str))
            if len(nums) >= 2:
                return [float(nums[0]), float(nums[1])]
            return [None, None]
            
        self.df[['min_salary', 'max_salary']] = pd.DataFrame(
            self.df['salary'].apply(extract_salary).tolist()
        )
        self.df['avg_salary'] = (self.df['min_salary'] + self.df['max_salary']) / 2
        
        # 填充空值
        self.df['education'] = self.df['education'].fillna('未说明')
        self.df['work_exp'] = self.df['work_exp'].fillna('经验不限')
        self.df['company_type'] = self.df['company_type'].fillna('其他')
        
    def plot_salary_distribution(self):
        """绘制薪资分布箱线图"""
        fig = px.box(
            self.df, 
            y=['min_salary', 'max_salary'],
            title='薪资分布(单位:千元/月)'
        )
        return fig
    
    def plot_education_pie(self):
        """绘制学历要求饼图"""
        edu_counts = self.df['education'].value_counts()
        fig = px.pie(
            values=edu_counts.values, 
            names=edu_counts.index,
            title='学历要求分布'
        )
        return fig
    
    def plot_experience_bar(self):
        """绘制工作经验要求条形图"""
        exp_counts = self.df['work_exp'].value_counts()
        fig = px.bar(
            x=exp_counts.index,
            y=exp_counts.values,
            title='工作经验要求分布'
        )
        return fig
    
    def plot_company_type_pie(self):
        """绘制公司类型饼图"""
        type_counts = self.df['company_type'].value_counts()
        fig = px.pie(
            values=type_counts.values,
            names=type_counts.index,
            title='公司类型分布'
        )
        return fig
    
    def generate_job_wordcloud(self):
        """生成职位描述词云"""
        text = ' '.join(self.df['job_summary'].dropna())
        words = jieba.cut(text)
        word_freq = Counter(words)
        
        stopwords = set(['的', '了', '和', '与', '等', '及'])
        word_freq = {k: v for k, v in word_freq.items() 
                     if k not in stopwords and len(k) > 1}
        
        fonts = [f for f in fm.findSystemFonts() if os.path.exists(f)]
        font_path = None
        for font in fonts:
            if any(name in font.lower() for name in [
                'simhei', 'msyh', 'simsun', 'simkai',
                'pingfang', 'heiti', 'songti'
            ]):
                font_path = font
                break
        
        if not font_path:
            st.warning("未找到合适的中文字体，词云可能无法正确显示中文")
            font_path = fonts[0] if fonts else None
            
        try:
            wc = WordCloud(
                width=800,
                height=400,
                background_color='white',
                font_path=font_path
            )
            wc.generate_from_frequencies(word_freq)
            return wc.to_image()
        except Exception as e:
            st.error(f"生成词云时发生错误: {str(e)}")
            return None
    
    def plot_welfare_bars(self):
        """绘制福利关键词统计条形图"""
        welfare_text = ' '.join(self.df['welfare'].dropna())
        welfare_words = jieba.cut(welfare_text)
        word_freq = Counter(welfare_words)
        
        stopwords = set(['的', '了', '和', '与', '等', '及'])
        word_freq = {k: v for k, v in word_freq.items() 
                     if k not in stopwords and len(k) > 1}
        top_10 = dict(sorted(word_freq.items(), 
                             key=lambda x: x[1], 
                             reverse=True)[:10])
        
        fig = px.bar(
            x=list(top_10.keys()),
            y=list(top_10.values()),
            title='Top 10 福利关键词'
        )
        return fig

    def generate_job_insights(self):
        """生成岗位洞察报表"""
        insights = {}
        salary_insights = {
            "平均薪资": f"{self.df['avg_salary'].mean():.2f}K",
            "最高薪资": f"{self.df['max_salary'].max():.2f}K",
            "最低薪资": f"{self.df['min_salary'].min():.2f}K"
        }
        insights['薪资分析'] = salary_insights
        
        exp_insights = self.df['work_exp'].value_counts().to_dict()
        insights['经验要求分布'] = exp_insights
        
        edu_insights = self.df['education'].value_counts().to_dict()
        insights['学历要求分布'] = edu_insights
        
        text = ' '.join(self.df['job_summary'].dropna())
        words = jieba.cut(text)
        word_freq = Counter(words)
        
        tech_keywords = [
            'python', 'java', 'ai', '算法', '深度学习', '机器学习',
            'linux', 'docker', 'kubernetes', '数据库', 'sql',
            'tensorflow', 'pytorch', '大模型', 'llm', 'cuda'
        ] 
        
        tech_freq = {
            k: v for k, v in word_freq.items() 
            if k.lower() in tech_keywords
        }
        insights['热门技术需求'] = dict(sorted(
            tech_freq.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10])
        
        return insights
    
    def plot_insights_summary(self, insights):
        """绘制洞察报表可视化图表"""
        salary_ranges = pd.cut(
            self.df['avg_salary'].dropna(), 
            bins=[0, 10, 20, 30, 40, float('inf')],
            labels=['0-10k', '10-20k', '20-30k', '30-40k', '40k+']
        )
        
        salary_dist = salary_ranges.value_counts()
        fig_salary = px.bar(
            x=salary_dist.index, 
            y=salary_dist.values,
            title='薪资区间分布'
        )
        
        tech_freq = insights['热门技术需求']
        fig_skills = px.bar(
            x=list(tech_freq.keys()),
            y=list(tech_freq.values()),
            title='热门技术需求TOP10'
        )
        
        return fig_salary, fig_skills

    def plot_skill_matching(self, user_skills):
        """绘制技能匹配度雷达图（演示）"""
        job_skills = ' '.join(self.df['job_summary'].dropna())
        job_words = jieba.lcut(job_skills)
        
        job_skill_counts = Counter(job_words)
        
        stopwords = set(['的', '了', '和', '与', '等', '及'])
        job_skill_counts = Counter({
            k: v for k, v in job_skill_counts.items()
            if k not in stopwords and len(k) > 1
        })
        
        top_skills = dict(job_skill_counts.most_common(10))
        
        user_skill_counts = {skill: 1 for skill in user_skills}
        
        skills = list(top_skills.keys())
        job_freq = [top_skills.get(skill, 0) for skill in skills]
        user_freq = [user_skill_counts.get(skill, 0) for skill in skills]
        
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=job_freq,
            theta=skills,
            fill='toself',
            name='市场需求'
        ))
        fig.add_trace(go.Scatterpolar(
            r=user_freq,
            theta=skills,
            fill='toself',
            name='我的技能'
        ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, max(job_freq + user_freq) + 5]
                )
            ),
            title='技能匹配度雷达图'
        )
        return fig
    
    def plot_skill_salary_premium(self):
        """绘制热门技能的薪资溢价柱状图"""
        popular_skills = [
            'python', 'java', 'ai', '算法', '深度学习', '机器学习',
            'linux', 'docker', 'kubernetes', '数据库', 'sql',
            'tensorflow', 'pytorch', '大模型', 'llm', 'cuda'
        ]
        salary_with_skill = []
        salary_without_skill = []
        
        for skill in popular_skills:
            mask = self.df['job_summary'].str.contains(skill, case=False, na=False)
            avg_with = self.df.loc[mask, 'avg_salary'].mean()
            avg_without = self.df.loc[~mask, 'avg_salary'].mean()
            salary_with_skill.append(avg_with)
            salary_without_skill.append(avg_without)
        
        fig = go.Figure(data=[
            go.Bar(name='含该技能的岗位平均薪资', x=popular_skills, y=salary_with_skill),
            go.Bar(name='不含该技能的岗位平均薪资', x=popular_skills, y=salary_without_skill)
        ])
        fig.update_layout(
            barmode='group', 
            title='热门技能的薪资溢价对比',
            xaxis_title='技能',
            yaxis_title='平均薪资（千元/月）'
        )
        return fig
    
    def plot_welfare_salary_scatter(self):
        """绘制福利丰富度与薪资的散点图"""
        self.df['welfare_count'] = self.df['welfare'].apply(
            lambda x: len(str(x).split(',')) if pd.notna(x) else 0
        )
        fig = px.scatter(
            self.df, 
            x='avg_salary', 
            y='welfare_count',
            color='company_type',
            size='welfare_count',
            hover_data=['company_name'],
            title='福利丰富度与薪资关系',
            labels={'avg_salary':'平均薪资（千元/月）', 'welfare_count':'福利数量'}
        )
        return fig
    
    def plot_job_description_length(self):
        """绘制职位描述长度与薪资的散点图"""
        self.df['jd_length'] = self.df['job_summary'].apply(
            lambda x: len(str(x)) if pd.notna(x) else 0
        )
        fig = px.scatter(
            self.df, 
            x='jd_length', 
            y='avg_salary',
            color='education',
            size='jd_length',
            hover_data=['position_name'],
            title='职位描述长度与薪资关系',
            labels={'jd_length':'职位描述字数', 'avg_salary':'平均薪资（千元/月）'}
        )
        return fig
    
    def plot_company_promotion_opportunities(self):
        """绘制公司规模/类型与培训晋升机会的雷达图（示例逻辑）"""
        self.df['promotion_opportunity'] = self.df['job_summary'].apply(
            lambda x: 1 if '晋升' in str(x) else 0
        )
        self.df['training_opportunity'] = self.df['job_summary'].apply(
            lambda x: 1 if '培训' in str(x) else 0
        )
        
        company_sizes = self.df['company_size'].unique()
        promotion = []
        training = []
        for size in company_sizes:
            subset = self.df[self.df['company_size'] == size]
            promo_rate = subset['promotion_opportunity'].mean() * 100
            train_rate = subset['training_opportunity'].mean() * 100
            promotion.append(promo_rate)
            training.append(train_rate)
        
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=promotion,
            theta=company_sizes,
            fill='toself',
            name='晋升机会率 (%)'
        ))
        fig.add_trace(go.Scatterpolar(
            r=training,
            theta=company_sizes,
            fill='toself',
            name='培训机会率 (%)'
        ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )
            ),
            title='公司规模与培训晋升机会比较雷达图'
        )
        return fig

    def filter_jobs(self, education=None, experience=None, skills=None, welfare=None):
        """根据多条件筛选岗位"""
        filtered = self.df
        if education:
            filtered = filtered[filtered['education'] == education]
        if experience:
            filtered = filtered[filtered['work_exp'] == experience]
        if skills:
            skill_pattern = '|'.join(skills)
            filtered = filtered[filtered['job_summary'].str.contains(skill_pattern, case=False, na=False)]
        if welfare:
            welfare_pattern = '|'.join(welfare)
            filtered = filtered[filtered['welfare'].str.contains(welfare_pattern, case=False, na=False)]
        return filtered

    def plot_filtered_salary_distribution(self, filtered_df):
        """绘制筛选后薪资分布箱线图"""
        fig = px.box(
            filtered_df, 
            y=['min_salary', 'max_salary'],
            title='筛选后薪资分布(单位:千元/月)'
        )
        return fig

# ========== Streamlit 应用入口 ==========

def main():
    """新的主入口，仅初始化JobUI"""
    from .ui_module import JobUI
    import streamlit as st
    
    data_root = Path(__file__).parent.parent
    job_ui = JobUI(data_root)
    job_ui.run()

# 保留LLM相关功能函数
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import jieba
import streamlit as st
from collections import Counter
import re
from wordcloud import WordCloud
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import os
from pathlib import Path
import matplotlib.font_manager as fm
from io import BytesIO
import requests
from requests.exceptions import ConnectionError
import time

# ========== Ollama本地服务相关示例函数 ==========

OLLAMA_BASE_URL = "http://127.0.0.1:11434"

def get_local_models():
    """获取Ollama可用模型列表(示例)，如果连接失败或接口结构有变，可自行调整。"""
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
                return ["无法获取本地模型列表"]
        except ConnectionError:
            if attempt < max_retries - 1:
                print(f"连接Ollama服务失败, {retry_delay}秒后重试...")
                time.sleep(retry_delay)
            else:
                print("无法连接到Ollama服务, 请确保服务已启动")
                return ["无法连接到Ollama服务"]
        except Exception as e:
            print(f"获取模型列表时发生错误: {str(e)}")
            return [f"获取本地模型列表时出错: {str(e)}"]

# ========== 模拟/占位: LLM 调用的简历解析、匹配与修改逻辑 ==========

def parse_resume(file_bytes, file_type):
    """
    占位函数：解析用户上传的简历（PDF或Word），返回文本内容。
    实际可使用 PyMuPDF、PyPDF2、python-docx 等库处理。
    """
    try:
        if file_type == "pdf":
            # 示例处理 PDF
            return "【PDF简历】这里是解析得到的简历文本内容……"
        elif file_type in ["docx", "doc"]:
            # 示例处理 Word
            return "【Word简历】这里是解析得到的简历文本内容……"
        else:
            return "暂不支持的文件类型，无法解析。"
    except Exception:
        return "解析失败，请检查简历文件格式或内容。"

def match_jobs_with_resume(resume_text, job_df, llm_mode, openai_key=None):
    """
    将简历与 job_df 的岗位数据进行匹配，并返回前 10 条最匹配结果。
    这里的逻辑仅作演示，可根据需要调用真实大模型或更复杂的算法。

    返回示例格式：
    [
      {
        "job_name": "...",
        "company_name": "...",
        "match_score": 0.85,
        "match_reason": "匹配原因说明，如技能点对应",
        "salary_range": "10-15k",
        "job_index": 123   # 原表中的index或唯一ID
      },
      ...
    ]
    """
    # 简化方式：根据 resume_text 中出现的技能/关键词 与 岗位 job_summary 进行匹配
    if not resume_text or job_df.empty:
        return []

    # 分词简历
    resume_tokens = set(jieba.lcut(resume_text.lower()))
    
    results = []
    for idx, row in job_df.iterrows():
        summary = str(row.get('job_summary', '')).lower()
        salary = str(row.get('salary', '面议'))
        job_name = str(row.get('position_name', '未知岗位'))
        comp_name = str(row.get('company_name', '未知公司'))
        
        # 分词岗位描述
        summary_tokens = set(jieba.lcut(summary))
        
        # 简易匹配度计算：交集词数 / (简历词数+岗位词数的一部分)
        common_tokens = resume_tokens.intersection(summary_tokens)
        # 避免除零错误，增加一个最小值1
        match_score = len(common_tokens) / (len(summary_tokens) + 1)
        
        # 简单模拟打分区间 0-1, 也可进一步缩放、权重处理
        match_reason = f"简历与岗位描述存在 {len(common_tokens)} 个相同关键词"
        
        results.append({
            "job_name": job_name,
            "company_name": comp_name,
            "match_score": round(match_score, 2),
            "match_reason": match_reason,
            "salary_range": salary,
            "job_index": idx
        })
    
    # 按匹配度排序后，取前10条
    results.sort(key=lambda x: x["match_score"], reverse=True)
    top_10 = results[:10]
    
    return top_10

def modify_resume_for_job(original_resume, job_description, llm_mode, openai_key=None):
    """
    基于 original_resume 与 job_description，生成个性化修改后的简历文本。
    可在此调用本地LLM或OpenAI API。
    此处仍为演示示例。
    """
    new_resume = (
        "【AI修改后的简历示例】\n\n"
        f"=== 原简历部分内容 ===\n{original_resume[:100]}...\n\n"
        f"=== 目标岗位需求 ===\n{job_description}\n\n"
        "=== 优化后简历示例 ===\n"
        "这里添加更契合目标岗位的技能描述，突出匹配的项目经验、技术栈等。"
    )
    return new_resume

# ========== 可视化部分的DataVisualizer类 ==========

class DataVisualizer:
    def __init__(self, csv_path):
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"找不到数据文件: {csv_path}")
        self.df = pd.read_csv(csv_path)
        self.preprocess_data()
        
    def preprocess_data(self):
        """预处理数据，如提取工资上下限"""
        def extract_salary(salary_str):
            if pd.isna(salary_str):
                return [None, None]
            nums = re.findall(r'(\d+\.?\d*)', str(salary_str))
            if len(nums) >= 2:
                return [float(nums[0]), float(nums[1])]
            return [None, None]
            
        self.df[['min_salary', 'max_salary']] = pd.DataFrame(
            self.df['salary'].apply(extract_salary).tolist()
        )
        self.df['avg_salary'] = (self.df['min_salary'] + self.df['max_salary']) / 2
        
        # 填充空值
        self.df['education'] = self.df['education'].fillna('未说明')
        self.df['work_exp'] = self.df['work_exp'].fillna('经验不限')
        self.df['company_type'] = self.df['company_type'].fillna('其他')
        
    def plot_salary_distribution(self):
        """绘制薪资分布箱线图"""
        fig = px.box(
            self.df, 
            y=['min_salary', 'max_salary'],
            title='薪资分布(单位:千元/月)'
        )
        return fig
    
    def plot_education_pie(self):
        """绘制学历要求饼图"""
        edu_counts = self.df['education'].value_counts()
        fig = px.pie(
            values=edu_counts.values, 
            names=edu_counts.index,
            title='学历要求分布'
        )
        return fig
    
    def plot_experience_bar(self):
        """绘制工作经验要求条形图"""
        exp_counts = self.df['work_exp'].value_counts()
        fig = px.bar(
            x=exp_counts.index,
            y=exp_counts.values,
            title='工作经验要求分布'
        )
        return fig
    
    def plot_company_type_pie(self):
        """绘制公司类型饼图"""
        type_counts = self.df['company_type'].value_counts()
        fig = px.pie(
            values=type_counts.values,
            names=type_counts.index,
            title='公司类型分布'
        )
        return fig
    
    def generate_job_wordcloud(self):
        """生成职位描述词云"""
        text = ' '.join(self.df['job_summary'].dropna())
        words = jieba.cut(text)
        word_freq = Counter(words)
        
        stopwords = set(['的', '了', '和', '与', '等', '及'])
        word_freq = {k: v for k, v in word_freq.items() 
                     if k not in stopwords and len(k) > 1}
        
        fonts = [f for f in fm.findSystemFonts() if os.path.exists(f)]
        font_path = None
        for font in fonts:
            if any(name in font.lower() for name in [
                'simhei', 'msyh', 'simsun', 'simkai',
                'pingfang', 'heiti', 'songti'
            ]):
                font_path = font
                break
        
        if not font_path:
            st.warning("未找到合适的中文字体，词云可能无法正确显示中文")
            font_path = fonts[0] if fonts else None
            
        try:
            wc = WordCloud(
                width=800,
                height=400,
                background_color='white',
                font_path=font_path
            )
            wc.generate_from_frequencies(word_freq)
            return wc.to_image()
        except Exception as e:
            st.error(f"生成词云时发生错误: {str(e)}")
            return None
    
    def plot_welfare_bars(self):
        """绘制福利关键词统计条形图"""
        welfare_text = ' '.join(self.df['welfare'].dropna())
        welfare_words = jieba.cut(welfare_text)
        word_freq = Counter(welfare_words)
        
        stopwords = set(['的', '了', '和', '与', '等', '及'])
        word_freq = {k: v for k, v in word_freq.items() 
                     if k not in stopwords and len(k) > 1}
        top_10 = dict(sorted(word_freq.items(), 
                             key=lambda x: x[1], 
                             reverse=True)[:10])
        
        fig = px.bar(
            x=list(top_10.keys()),
            y=list(top_10.values()),
            title='Top 10 福利关键词'
        )
        return fig

    def generate_job_insights(self):
        """生成岗位洞察报表"""
        insights = {}
        salary_insights = {
            "平均薪资": f"{self.df['avg_salary'].mean():.2f}K",
            "最高薪资": f"{self.df['max_salary'].max():.2f}K",
            "最低薪资": f"{self.df['min_salary'].min():.2f}K"
        }
        insights['薪资分析'] = salary_insights
        
        exp_insights = self.df['work_exp'].value_counts().to_dict()
        insights['经验要求分布'] = exp_insights
        
        edu_insights = self.df['education'].value_counts().to_dict()
        insights['学历要求分布'] = edu_insights
        
        text = ' '.join(self.df['job_summary'].dropna())
        words = jieba.cut(text)
        word_freq = Counter(words)
        
        tech_keywords = [
            'python', 'java', 'ai', '算法', '深度学习', '机器学习',
            'linux', 'docker', 'kubernetes', '数据库', 'sql',
            'tensorflow', 'pytorch', '大模型', 'llm', 'cuda'
        ] 
        
        tech_freq = {
            k: v for k, v in word_freq.items() 
            if k.lower() in tech_keywords
        }
        insights['热门技术需求'] = dict(sorted(
            tech_freq.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10])
        
        return insights
    
    def plot_insights_summary(self, insights):
        """绘制洞察报表可视化图表"""
        salary_ranges = pd.cut(
            self.df['avg_salary'].dropna(), 
            bins=[0, 10, 20, 30, 40, float('inf')],
            labels=['0-10k', '10-20k', '20-30k', '30-40k', '40k+']
        )
        
        salary_dist = salary_ranges.value_counts()
        fig_salary = px.bar(
            x=salary_dist.index, 
            y=salary_dist.values,
            title='薪资区间分布'
        )
        
        tech_freq = insights['热门技术需求']
        fig_skills = px.bar(
            x=list(tech_freq.keys()),
            y=list(tech_freq.values()),
            title='热门技术需求TOP10'
        )
        
        return fig_salary, fig_skills

    def plot_skill_matching(self, user_skills):
        """绘制技能匹配度雷达图（演示）"""
        job_skills = ' '.join(self.df['job_summary'].dropna())
        job_words = jieba.lcut(job_skills)
        
        job_skill_counts = Counter(job_words)
        
        stopwords = set(['的', '了', '和', '与', '等', '及'])
        job_skill_counts = Counter({
            k: v for k, v in job_skill_counts.items()
            if k not in stopwords and len(k) > 1
        })
        
        top_skills = dict(job_skill_counts.most_common(10))
        
        user_skill_counts = {skill: 1 for skill in user_skills}
        
        skills = list(top_skills.keys())
        job_freq = [top_skills.get(skill, 0) for skill in skills]
        user_freq = [user_skill_counts.get(skill, 0) for skill in skills]
        
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=job_freq,
            theta=skills,
            fill='toself',
            name='市场需求'
        ))
        fig.add_trace(go.Scatterpolar(
            r=user_freq,
            theta=skills,
            fill='toself',
            name='我的技能'
        ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, max(job_freq + user_freq) + 5]
                )
            ),
            title='技能匹配度雷达图'
        )
        return fig
    
    def plot_skill_salary_premium(self):
        """绘制热门技能的薪资溢价柱状图"""
        popular_skills = [
            'python', 'java', 'ai', '算法', '深度学习', '机器学习',
            'linux', 'docker', 'kubernetes', '数据库', 'sql',
            'tensorflow', 'pytorch', '大模型', 'llm', 'cuda'
        ]
        salary_with_skill = []
        salary_without_skill = []
        
        for skill in popular_skills:
            mask = self.df['job_summary'].str.contains(skill, case=False, na=False)
            avg_with = self.df.loc[mask, 'avg_salary'].mean()
            avg_without = self.df.loc[~mask, 'avg_salary'].mean()
            salary_with_skill.append(avg_with)
            salary_without_skill.append(avg_without)
        
        fig = go.Figure(data=[
            go.Bar(name='含该技能的岗位平均薪资', x=popular_skills, y=salary_with_skill),
            go.Bar(name='不含该技能的岗位平均薪资', x=popular_skills, y=salary_without_skill)
        ])
        fig.update_layout(
            barmode='group', 
            title='热门技能的薪资溢价对比',
            xaxis_title='技能',
            yaxis_title='平均薪资（千元/月）'
        )
        return fig
    
    def plot_welfare_salary_scatter(self):
        """绘制福利丰富度与薪资的散点图"""
        self.df['welfare_count'] = self.df['welfare'].apply(
            lambda x: len(str(x).split(',')) if pd.notna(x) else 0
        )
        fig = px.scatter(
            self.df, 
            x='avg_salary', 
            y='welfare_count',
            color='company_type',
            size='welfare_count',
            hover_data=['company_name'],
            title='福利丰富度与薪资关系',
            labels={'avg_salary':'平均薪资（千元/月）', 'welfare_count':'福利数量'}
        )
        return fig
    
    def plot_job_description_length(self):
        """绘制职位描述长度与薪资的散点图"""
        self.df['jd_length'] = self.df['job_summary'].apply(
            lambda x: len(str(x)) if pd.notna(x) else 0
        )
        fig = px.scatter(
            self.df, 
            x='jd_length', 
            y='avg_salary',
            color='education',
            size='jd_length',
            hover_data=['position_name'],
            title='职位描述长度与薪资关系',
            labels={'jd_length':'职位描述字数', 'avg_salary':'平均薪资（千元/月）'}
        )
        return fig
    
    def plot_company_promotion_opportunities(self):
        """绘制公司规模/类型与培训晋升机会的雷达图（示例逻辑）"""
        self.df['promotion_opportunity'] = self.df['job_summary'].apply(
            lambda x: 1 if '晋升' in str(x) else 0
        )
        self.df['training_opportunity'] = self.df['job_summary'].apply(
            lambda x: 1 if '培训' in str(x) else 0
        )
        
        company_sizes = self.df['company_size'].unique()
        promotion = []
        training = []
        for size in company_sizes:
            subset = self.df[self.df['company_size'] == size]
            promo_rate = subset['promotion_opportunity'].mean() * 100
            train_rate = subset['training_opportunity'].mean() * 100
            promotion.append(promo_rate)
            training.append(train_rate)
        
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=promotion,
            theta=company_sizes,
            fill='toself',
            name='晋升机会率 (%)'
        ))
        fig.add_trace(go.Scatterpolar(
            r=training,
            theta=company_sizes,
            fill='toself',
            name='培训机会率 (%)'
        ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )
            ),
            title='公司规模与培训晋升机会比较雷达图'
        )
        return fig

    def filter_jobs(self, education=None, experience=None, skills=None, welfare=None):
        """根据多条件筛选岗位"""
        filtered = self.df
        if education:
            filtered = filtered[filtered['education'] == education]
        if experience:
            filtered = filtered[filtered['work_exp'] == experience]
        if skills:
            skill_pattern = '|'.join(skills)
            filtered = filtered[filtered['job_summary'].str.contains(skill_pattern, case=False, na=False)]
        if welfare:
            welfare_pattern = '|'.join(welfare)
            filtered = filtered[filtered['welfare'].str.contains(welfare_pattern, case=False, na=False)]
        return filtered

    def plot_filtered_salary_distribution(self, filtered_df):
        """绘制筛选后薪资分布箱线图"""
        fig = px.box(
            filtered_df, 
            y=['min_salary', 'max_salary'],
            title='筛选后薪资分布(单位:千元/月)'
        )
        return fig

# ========== Streamlit 应用入口 ==========

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import jieba
import streamlit as st
from collections import Counter
import re
from wordcloud import WordCloud
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import os
from pathlib import Path
import matplotlib.font_manager as fm
from io import BytesIO
import requests
from requests.exceptions import ConnectionError
import time

# ========== Ollama本地服务相关示例函数 ==========

OLLAMA_BASE_URL = "http://127.0.0.1:11434"

def get_local_models():
    """获取Ollama可用模型列表(示例)，如果连接失败或接口结构有变，可自行调整。"""
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
                return ["无法获取本地模型列表"]
        except ConnectionError:
            if attempt < max_retries - 1:
                print(f"连接Ollama服务失败, {retry_delay}秒后重试...")
                time.sleep(retry_delay)
            else:
                print("无法连接到Ollama服务, 请确保服务已启动")
                return ["无法连接到Ollama服务"]
        except Exception as e:
            print(f"获取模型列表时发生错误: {str(e)}")
            return [f"获取本地模型列表时出错: {str(e)}"]

# ========== 模拟/占位: LLM 调用的简历解析、匹配与修改逻辑 ==========

def parse_resume(file_bytes, file_type):
    """
    占位函数：解析用户上传的简历（PDF或Word），返回文本内容。
    实际可使用 PyMuPDF、PyPDF2、python-docx 等库处理。
    """
    try:
        if file_type == "pdf":
            # 示例处理 PDF
            return "【PDF简历】这里是解析得到的简历文本内容……"
        elif file_type in ["docx", "doc"]:
            # 示例处理 Word
            return "【Word简历】这里是解析得到的简历文本内容……"
        else:
            return "暂不支持的文件类型，无法解析。"
    except Exception:
        return "解析失败，请检查简历文件格式或内容。"

def match_jobs_with_resume(resume_text, job_df, llm_mode, openai_key=None):
    """
    将简历与 job_df 的岗位数据进行匹配，并返回前 10 条最匹配结果。
    这里的逻辑仅作演示，可根据需要调用真实大模型或更复杂的算法。

    返回示例格式：
    [
      {
        "job_name": "...",
        "company_name": "...",
        "match_score": 0.85,
        "match_reason": "匹配原因说明，如技能点对应",
        "salary_range": "10-15k",
        "job_index": 123   # 原表中的index或唯一ID
      },
      ...
    ]
    """
    # 简化方式：根据 resume_text 中出现的技能/关键词 与 岗位 job_summary 进行匹配
    if not resume_text or job_df.empty:
        return []

    # 分词简历
    resume_tokens = set(jieba.lcut(resume_text.lower()))
    
    results = []
    for idx, row in job_df.iterrows():
        summary = str(row.get('job_summary', '')).lower()
        salary = str(row.get('salary', '面议'))
        job_name = str(row.get('position_name', '未知岗位'))
        comp_name = str(row.get('company_name', '未知公司'))
        
        # 分词岗位描述
        summary_tokens = set(jieba.lcut(summary))
        
        # 简易匹配度计算：交集词数 / (简历词数+岗位词数的一部分)
        common_tokens = resume_tokens.intersection(summary_tokens)
        # 避免除零错误，增加一个最小值1
        match_score = len(common_tokens) / (len(summary_tokens) + 1)
        
        # 简单模拟打分区间 0-1, 也可进一步缩放、权重处理
        match_reason = f"简历与岗位描述存在 {len(common_tokens)} 个相同关键词"
        
        results.append({
            "job_name": job_name,
            "company_name": comp_name,
            "match_score": round(match_score, 2),
            "match_reason": match_reason,
            "salary_range": salary,
            "job_index": idx
        })
    
    # 按匹配度排序后，取前10条
    results.sort(key=lambda x: x["match_score"], reverse=True)
    top_10 = results[:10]
    
    return top_10

def modify_resume_for_job(original_resume, job_description, llm_mode, openai_key=None):
    """
    基于 original_resume 与 job_description，生成个性化修改后的简历文本。
    可在此调用本地LLM或OpenAI API。
    此处仍为演示示例。
    """
    new_resume = (
        "【AI修改后的简历示例】\n\n"
        f"=== 原简历部分内容 ===\n{original_resume[:100]}...\n\n"
        f"=== 目标岗位需求 ===\n{job_description}\n\n"
        "=== 优化后简历示例 ===\n"
        "这里添加更契合目标岗位的技能描述，突出匹配的项目经验、技术栈等。"
    )
    return new_resume

# ========== 可视化部分的DataVisualizer类 ==========

class DataVisualizer:
    def __init__(self, csv_path):
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"找不到数据文件: {csv_path}")
        self.df = pd.read_csv(csv_path)
        self.preprocess_data()
        
    def preprocess_data(self):
        """预处理数据，如提取工资上下限"""
        def extract_salary(salary_str):
            if pd.isna(salary_str):
                return [None, None]
            nums = re.findall(r'(\d+\.?\d*)', str(salary_str))
            if len(nums) >= 2:
                return [float(nums[0]), float(nums[1])]
            return [None, None]
            
        self.df[['min_salary', 'max_salary']] = pd.DataFrame(
            self.df['salary'].apply(extract_salary).tolist()
        )
        self.df['avg_salary'] = (self.df['min_salary'] + self.df['max_salary']) / 2
        
        # 填充空值
        self.df['education'] = self.df['education'].fillna('未说明')
        self.df['work_exp'] = self.df['work_exp'].fillna('经验不限')
        self.df['company_type'] = self.df['company_type'].fillna('其他')
        
    def plot_salary_distribution(self):
        """绘制薪资分布箱线图"""
        fig = px.box(
            self.df, 
            y=['min_salary', 'max_salary'],
            title='薪资分布(单位:千元/月)'
        )
        return fig
    
    def plot_education_pie(self):
        """绘制学历要求饼图"""
        edu_counts = self.df['education'].value_counts()
        fig = px.pie(
            values=edu_counts.values, 
            names=edu_counts.index,
            title='学历要求分布'
        )
        return fig
    
    def plot_experience_bar(self):
        """绘制工作经验要求条形图"""
        exp_counts = self.df['work_exp'].value_counts()
        fig = px.bar(
            x=exp_counts.index,
            y=exp_counts.values,
            title='工作经验要求分布'
        )
        return fig
    
    def plot_company_type_pie(self):
        """绘制公司类型饼图"""
        type_counts = self.df['company_type'].value_counts()
        fig = px.pie(
            values=type_counts.values,
            names=type_counts.index,
            title='公司类型分布'
        )
        return fig
    
    def generate_job_wordcloud(self):
        """生成职位描述词云"""
        text = ' '.join(self.df['job_summary'].dropna())
        words = jieba.cut(text)
        word_freq = Counter(words)
        
        stopwords = set(['的', '了', '和', '与', '等', '及'])
        word_freq = {k: v for k, v in word_freq.items() 
                     if k not in stopwords and len(k) > 1}
        
        fonts = [f for f in fm.findSystemFonts() if os.path.exists(f)]
        font_path = None
        for font in fonts:
            if any(name in font.lower() for name in [
                'simhei', 'msyh', 'simsun', 'simkai',
                'pingfang', 'heiti', 'songti'
            ]):
                font_path = font
                break
        
        if not font_path:
            st.warning("未找到合适的中文字体，词云可能无法正确显示中文")
            font_path = fonts[0] if fonts else None
            
        try:
            wc = WordCloud(
                width=800,
                height=400,
                background_color='white',
                font_path=font_path
            )
            wc.generate_from_frequencies(word_freq)
            return wc.to_image()
        except Exception as e:
            st.error(f"生成词云时发生错误: {str(e)}")
            return None
    
    def plot_welfare_bars(self):
        """绘制福利关键词统计条形图"""
        welfare_text = ' '.join(self.df['welfare'].dropna())
        welfare_words = jieba.cut(welfare_text)
        word_freq = Counter(welfare_words)
        
        stopwords = set(['的', '了', '和', '与', '等', '及'])
        word_freq = {k: v for k, v in word_freq.items() 
                     if k not in stopwords and len(k) > 1}
        top_10 = dict(sorted(word_freq.items(), 
                             key=lambda x: x[1], 
                             reverse=True)[:10])
        
        fig = px.bar(
            x=list(top_10.keys()),
            y=list(top_10.values()),
            title='Top 10 福利关键词'
        )
        return fig

    def generate_job_insights(self):
        """生成岗位洞察报表"""
        insights = {}
        salary_insights = {
            "平均薪资": f"{self.df['avg_salary'].mean():.2f}K",
            "最高薪资": f"{self.df['max_salary'].max():.2f}K",
            "最低薪资": f"{self.df['min_salary'].min():.2f}K"
        }
        insights['薪资分析'] = salary_insights
        
        exp_insights = self.df['work_exp'].value_counts().to_dict()
        insights['经验要求分布'] = exp_insights
        
        edu_insights = self.df['education'].value_counts().to_dict()
        insights['学历要求分布'] = edu_insights
        
        text = ' '.join(self.df['job_summary'].dropna())
        words = jieba.cut(text)
        word_freq = Counter(words)
        
        tech_keywords = [
            'python', 'java', 'ai', '算法', '深度学习', '机器学习',
            'linux', 'docker', 'kubernetes', '数据库', 'sql',
            'tensorflow', 'pytorch', '大模型', 'llm', 'cuda'
        ] 
        
        tech_freq = {
            k: v for k, v in word_freq.items() 
            if k.lower() in tech_keywords
        }
        insights['热门技术需求'] = dict(sorted(
            tech_freq.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10])
        
        return insights
    
    def plot_insights_summary(self, insights):
        """绘制洞察报表可视化图表"""
        salary_ranges = pd.cut(
            self.df['avg_salary'].dropna(), 
            bins=[0, 10, 20, 30, 40, float('inf')],
            labels=['0-10k', '10-20k', '20-30k', '30-40k', '40k+']
        )
        
        salary_dist = salary_ranges.value_counts()
        fig_salary = px.bar(
            x=salary_dist.index, 
            y=salary_dist.values,
            title='薪资区间分布'
        )
        
        tech_freq = insights['热门技术需求']
        fig_skills = px.bar(
            x=list(tech_freq.keys()),
            y=list(tech_freq.values()),
            title='热门技术需求TOP10'
        )
        
        return fig_salary, fig_skills

    def plot_skill_matching(self, user_skills):
        """绘制技能匹配度雷达图（演示）"""
        job_skills = ' '.join(self.df['job_summary'].dropna())
        job_words = jieba.lcut(job_skills)
        
        job_skill_counts = Counter(job_words)
        
        stopwords = set(['的', '了', '和', '与', '等', '及'])
        job_skill_counts = Counter({
            k: v for k, v in job_skill_counts.items()
            if k not in stopwords and len(k) > 1
        })
        
        top_skills = dict(job_skill_counts.most_common(10))
        
        user_skill_counts = {skill: 1 for skill in user_skills}
        
        skills = list(top_skills.keys())
        job_freq = [top_skills.get(skill, 0) for skill in skills]
        user_freq = [user_skill_counts.get(skill, 0) for skill in skills]
        
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=job_freq,
            theta=skills,
            fill='toself',
            name='市场需求'
        ))
        fig.add_trace(go.Scatterpolar(
            r=user_freq,
            theta=skills,
            fill='toself',
            name='我的技能'
        ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, max(job_freq + user_freq) + 5]
                )
            ),
            title='技能匹配度雷达图'
        )
        return fig
    
    def plot_skill_salary_premium(self):
        """绘制热门技能的薪资溢价柱状图"""
        popular_skills = [
            'python', 'java', 'ai', '算法', '深度学习', '机器学习',
            'linux', 'docker', 'kubernetes', '数据库', 'sql',
            'tensorflow', 'pytorch', '大模型', 'llm', 'cuda'
        ]
        salary_with_skill = []
        salary_without_skill = []
        
        for skill in popular_skills:
            mask = self.df['job_summary'].str.contains(skill, case=False, na=False)
            avg_with = self.df.loc[mask, 'avg_salary'].mean()
            avg_without = self.df.loc[~mask, 'avg_salary'].mean()
            salary_with_skill.append(avg_with)
            salary_without_skill.append(avg_without)
        
        fig = go.Figure(data=[
            go.Bar(name='含该技能的岗位平均薪资', x=popular_skills, y=salary_with_skill),
            go.Bar(name='不含该技能的岗位平均薪资', x=popular_skills, y=salary_without_skill)
        ])
        fig.update_layout(
            barmode='group', 
            title='热门技能的薪资溢价对比',
            xaxis_title='技能',
            yaxis_title='平均薪资（千元/月）'
        )
        return fig
    
    def plot_welfare_salary_scatter(self):
        """绘制福利丰富度与薪资的散点图"""
        self.df['welfare_count'] = self.df['welfare'].apply(
            lambda x: len(str(x).split(',')) if pd.notna(x) else 0
        )
        fig = px.scatter(
            self.df, 
            x='avg_salary', 
            y='welfare_count',
            color='company_type',
            size='welfare_count',
            hover_data=['company_name'],
            title='福利丰富度与薪资关系',
            labels={'avg_salary':'平均薪资（千元/月）', 'welfare_count':'福利数量'}
        )
        return fig
    
    def plot_job_description_length(self):
        """绘制职位描述长度与薪资的散点图"""
        self.df['jd_length'] = self.df['job_summary'].apply(
            lambda x: len(str(x)) if pd.notna(x) else 0
        )
        fig = px.scatter(
            self.df, 
            x='jd_length', 
            y='avg_salary',
            color='education',
            size='jd_length',
            hover_data=['position_name'],
            title='职位描述长度与薪资关系',
            labels={'jd_length':'职位描述字数', 'avg_salary':'平均薪资（千元/月）'}
        )
        return fig
    
    def plot_company_promotion_opportunities(self):
        """绘制公司规模/类型与培训晋升机会的雷达图（示例逻辑）"""
        self.df['promotion_opportunity'] = self.df['job_summary'].apply(
            lambda x: 1 if '晋升' in str(x) else 0
        )
        self.df['training_opportunity'] = self.df['job_summary'].apply(
            lambda x: 1 if '培训' in str(x) else 0
        )
        
        company_sizes = self.df['company_size'].unique()
        promotion = []
        training = []
        for size in company_sizes:
            subset = self.df[self.df['company_size'] == size]
            promo_rate = subset['promotion_opportunity'].mean() * 100
            train_rate = subset['training_opportunity'].mean() * 100
            promotion.append(promo_rate)
            training.append(train_rate)
        
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=promotion,
            theta=company_sizes,
            fill='toself',
            name='晋升机会率 (%)'
        ))
        fig.add_trace(go.Scatterpolar(
            r=training,
            theta=company_sizes,
            fill='toself',
            name='培训机会率 (%)'
        ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )
            ),
            title='公司规模与培训晋升机会比较雷达图'
        )
        return fig

    def filter_jobs(self, education=None, experience=None, skills=None, welfare=None):
        """根据多条件筛选岗位"""
        filtered = self.df
        if education:
            filtered = filtered[filtered['education'] == education]
        if experience:
            filtered = filtered[filtered['work_exp'] == experience]
        if skills:
            skill_pattern = '|'.join(skills)
            filtered = filtered[filtered['job_summary'].str.contains(skill_pattern, case=False, na=False)]
        if welfare:
            welfare_pattern = '|'.join(welfare)
            filtered = filtered[filtered['welfare'].str.contains(welfare_pattern, case=False, na=False)]
        return filtered

    def plot_filtered_salary_distribution(self, filtered_df):
        """绘制筛选后薪资分布箱线图"""
        fig = px.box(
            filtered_df, 
            y=['min_salary', 'max_salary'],
            title='筛选后薪资分布(单位:千元/月)'
        )
        return fig

# ========== Streamlit 应用入口 ==========

def main():
    st.title('AI岗位分析可视化 & 求职系统')

    # 初始化 session state 
    if 'resume_text' not in st.session_state:
        st.session_state['resume_text'] = ""
    if 'llm_mode' not in st.session_state:
        st.session_state['llm_mode'] = "本地 Ollama"
    if 'local_model' not in st.session_state:
        st.session_state['local_model'] = ""
    if 'openai_key' not in st.session_state:
        st.session_state['openai_key'] = ""

    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent
    data_dir = project_root / 'data'
    csv_files = [f for f in data_dir.glob('*.csv')]
    
    if not csv_files:
        st.error("数据目录下未找到任何 CSV 文件，请先准备好数据文件。")
        return
    
    selected_file = st.selectbox("请选择数据文件", [f.name for f in csv_files])
    
    if st.button("加载并分析数据"):
        data_file = data_dir / selected_file
        st.session_state['data_file'] = data_file
        st.session_state['data_loaded'] = True

    if 'data_loaded' in st.session_state and st.session_state['data_loaded']:
        data_file = st.session_state['data_file']
        st.write(f"正在尝试读取文件: {data_file}")
        
        try:
            if not os.path.exists(data_file):
                st.error(
                    f"数据文件不存在: {data_file}\n"
                    f"请确保在项目根目录 {project_root} 下存在 data/ 文件和相应CSV数据"
                )
                return
                
            viz = DataVisualizer(str(data_file))
            
            st.write(f"成功读取数据，共 {len(viz.df)} 条记录")
            
            # ========== 多Tab布局，加入“求职”功能 ========== 
            tab1, tab2, tab3 = st.tabs(["基础分析", "岗位洞察报表", "求职"])
            
            # ========== Tab1: 基础分析 ========== 
            with tab1:
                st.plotly_chart(viz.plot_salary_distribution())
                
                col1, col2 = st.columns(2)
                with col1:
                    st.plotly_chart(viz.plot_education_pie())
                with col2:
                    st.plotly_chart(viz.plot_experience_bar())
                    
                col3, col4 = st.columns(2)
                with col3:
                    st.plotly_chart(viz.plot_company_type_pie())
                with col4:
                    st.plotly_chart(viz.plot_welfare_bars())
                
                wordcloud = viz.generate_job_wordcloud()
                if wordcloud:
                    st.image(wordcloud, caption='职位描述关键词云图')
            
            # ========== Tab2: 岗位洞察报表 ========== 
            with tab2:
                insights = viz.generate_job_insights()
                
                st.header("岗位市场洞察")
                
                st.subheader("💰 薪资分析")
                salary_insights = insights['薪资分析']
                cols = st.columns(3)
                cols[0].metric("平均薪资", salary_insights['平均薪资'])
                cols[1].metric("最高薪资", salary_insights['最高薪资'])
                cols[2].metric("最低薪资", salary_insights['最低薪资'])
                
                fig_salary, fig_skills = viz.plot_insights_summary(insights)
                st.plotly_chart(fig_salary, key="salary_distribution")
                
                st.subheader("💻 技能需求分析")
                st.plotly_chart(fig_skills, key="skills_analysis")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("📚 学历要求占比")
                    st.write(insights['学历要求分布'])
                with col2:
                    st.subheader("⏳ 经验要求占比")
                    st.write(insights['经验要求分布'])
                
                if st.button("导出洞察报表"):
                    df_insights = pd.DataFrame.from_dict(insights, orient='index')
                    csv_str = df_insights.to_csv()
                    st.download_button(
                        label="下载CSV报表",
                        data=csv_str,
                        file_name='job_insights.csv',
                        mime='text/csv',
                    )
                
                st.subheader("🔍 职位要求与个人匹配度分析")
                user_skills = st.text_input("请输入您的技能，以逗号分隔", "python,深度学习,docker")
                user_skills = [skill.strip() for skill in user_skills.split(',') if skill.strip()]
                if user_skills:
                    fig_matching = viz.plot_skill_matching(user_skills)
                    st.plotly_chart(fig_matching)
                
                st.subheader("💸 热门技能的薪资溢价")
                fig_premium = viz.plot_skill_salary_premium()
                st.plotly_chart(fig_premium, key="skill_salary_premium")
                
                st.subheader("🎁 福利丰富度与薪资关系")
                fig_welfare_salary = viz.plot_welfare_salary_scatter()
                st.plotly_chart(fig_welfare_salary, key="welfare_salary_scatter")
                
                st.subheader("📄 职位描述长度与薪资关系")
                fig_jd_length = viz.plot_job_description_length()
                st.plotly_chart(fig_jd_length, key="jd_length_scatter")
                
                st.subheader("🏢 公司规模与培训晋升机会")
                fig_promotion = viz.plot_company_promotion_opportunities()
                st.plotly_chart(fig_promotion, key="company_promotion_opportunities")
                
                st.subheader("🔧 多条件组合筛选")
                edu_options = viz.df['education'].unique().tolist()
                exp_options = viz.df['work_exp'].unique().tolist()
                welfare_options = list(
                    set(word for w in viz.df['welfare'].dropna() for word in w.split(','))
                )
                
                selected_edu = st.selectbox("选择学历要求", [None] + edu_options)
                selected_exp = st.selectbox("选择工作经验", [None] + exp_options)
                
                selected_skills = st.text_input("输入技能筛选，以逗号分隔", "")
                selected_skills = [skill.strip() for skill in selected_skills.split(',') if skill.strip()]
                
                selected_welfare = st.multiselect("选择福利", welfare_options)
                
                if st.button("应用筛选"):
                    filtered_df = viz.filter_jobs(
                        education=selected_edu,
                        experience=selected_exp,
                        skills=selected_skills,
                        welfare=selected_welfare
                    )
                    st.write(f"筛选后共有 {len(filtered_df)} 个职位")
                    fig_filtered_salary = viz.plot_filtered_salary_distribution(filtered_df)
                    st.plotly_chart(fig_filtered_salary, key="filtered_salary_distribution")
            
            # ========== Tab3: 求职 ========== 
            with tab3:
                st.header("求职中心：简历匹配与定制化修改")
                
                # (1) 上传简历
                uploaded_file = st.file_uploader(
                    "上传简历（PDF或Word）",
                    type=["pdf", "doc", "docx"],
                    key="resume_uploader"
                )
                
                if uploaded_file is not None:
                    file_type = uploaded_file.name.split('.')[-1].lower()
                    file_bytes = uploaded_file.read()
                    
                    new_text = parse_resume(file_bytes, file_type)
                    if new_text != st.session_state['resume_text']:
                        st.session_state['resume_text'] = new_text
                        st.success("简历上传并解析成功！")
                        st.write("简历解析结果：")
                        st.write(new_text[:300] + "..." if len(new_text) > 300 else new_text)

                # 显示已解析的简历文本
                if st.session_state['resume_text']:
                    st.write("---")
                    st.subheader("已解析的简历内容")
                    display_text = (
                        st.session_state['resume_text'][:300] + "..." 
                        if len(st.session_state['resume_text']) > 300 
                        else st.session_state['resume_text']
                    )
                    st.write(display_text)
                
                st.warning("请注意保护个人信息隐私，如使用在线模型时需确保已了解相关风险。")
                
                # (2) 选择 LLM 模式
                llm_mode = st.radio(
                    "选择LLM模式",
                    options=["本地 Ollama", "OpenAI 在线模型"],
                    key="llm_mode_radio",
                    index=0 if st.session_state['llm_mode'] == "本地 Ollama" else 1
                )
                st.session_state['llm_mode'] = llm_mode

                if llm_mode == "本地 Ollama":
                    local_models = get_local_models()
                    selected_model = st.selectbox(
                        "选择本地模型",
                        local_models,
                        key="local_model_select"
                    )
                    st.session_state['local_model'] = selected_model
                else:
                    openai_key = st.text_input(
                        "输入 OpenAI API Key (必填)",
                        value=st.session_state.get('openai_key', ""),
                        type="password",
                        key="openai_key_input"
                    )
                    st.session_state['openai_key'] = openai_key

                # (3) 匹配按钮
                if st.button("开始匹配", key="start_matching"):
                    if not st.session_state['resume_text']:
                        st.error("请先上传并解析简历文件！")
                    elif llm_mode == "OpenAI 在线模型" and not st.session_state['openai_key']:
                        st.error("请输入 OpenAI API Key！")
                    else:
                        st.info("正在进行岗位匹配，请稍候...")
                        job_matches = match_jobs_with_resume(
                            resume_text=st.session_state['resume_text'],
                            job_df=viz.df,
                            llm_mode="local" if llm_mode == "本地 Ollama" else "openai",
                            openai_key=st.session_state.get('openai_key', "")
                        )
                        
                        if job_matches:
                            st.success("已找到前 10 条最匹配岗位：")
                            for i, match in enumerate(job_matches):
                                st.markdown(f"**{i+1}. 岗位名称:** {match['job_name']}")
                                st.markdown(f"**公司名称:** {match['company_name']}")
                                st.markdown(f"**匹配度评分:** {match['match_score']}")
                                st.markdown(f"**匹配原因:** {match['match_reason']}")
                                st.markdown(f"**薪资范围:** {match['salary_range']}")
                                
                                # (4) 简历修改
                                with st.expander(f"🔧 修改简历以匹配岗位: {match['job_name']}"):
                                    # 为每个岗位增加单独的按钮
                                    if st.button(f"生成针对 {match['job_name']} 的优化简历", key=f"modify_{i}"):
                                        # 调用修改函数
                                        final_resume = modify_resume_for_job(
                                            original_resume=st.session_state['resume_text'],
                                            job_description=(f"{match['job_name']} | {match['company_name']} | "
                                                             f"薪资: {match['salary_range']}"),
                                            llm_mode=("local" if llm_mode=="本地 Ollama" else "openai"),
                                            openai_key=st.session_state.get('openai_key', "")
                                        )
                                        st.write("---")
                                        st.subheader("AI优化后的简历内容:")
                                        st.write(final_resume)
                                        dl_data = final_resume.encode("utf-8")
                                        st.download_button(
                                            label="下载修改后简历 (txt)",
                                            data=dl_data,
                                            file_name="modified_resume.txt",
                                            mime="text/plain"
                                        )
                        else:
                            st.warning("未找到匹配岗位或简历内容不足。")

        except Exception as e:
            st.error(f"发生错误: {str(e)}\n错误类型: {type(e).__name__}")
            import traceback
            st.code(traceback.format_exc())

if __name__ == "__main__":
    main()
