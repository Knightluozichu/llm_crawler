import base64
from io import BytesIO
from pathlib import Path
from typing import Dict

import pandas as pd
import streamlit as st

from data_processor import DataProcessor
from visualizer import DataVisualizer

# ========== LLM 相关示例函数 ==========

import requests
import time
import jieba
from requests.exceptions import ConnectionError

OLLAMA_BASE_URL = "http://127.0.0.1:11434"


def get_local_models():
    """
    获取 Ollama 本地可用模型列表(示例)。
    若连接失败或接口结构有变，可自行调整。
    """
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


def parse_resume(file_bytes, file_type):
    """
    占位函数：解析用户上传的简历（PDF或Word），返回文本内容。
    可使用 PyMuPDF、PyPDF2、python-docx 等库进行真实解析。
    """
    try:
        if file_type == "pdf":
            return "【PDF简历示例】这里是解析后的简历文本..."
        elif file_type in ["docx", "doc"]:
            return "【Word简历示例】这里是解析后的简历文本..."
        else:
            return "暂不支持的文件类型，无法解析。"
    except Exception:
        return "解析失败，请检查简历文件格式或内容。"


def match_jobs_with_resume(resume_text, job_df, llm_mode, openai_key=None):
    """
    将简历与 job_df 进行简单匹配，返回前 10 条最匹配结果 (演示)。
    实际可改为复杂算法或调用大模型。
    
    :param resume_text: 解析后的简历文本
    :param job_df: 已筛选/处理后的 DataFrame
    :param llm_mode: "local" 或 "openai"
    :param openai_key: 若使用 openai，需要提供 key
    :return: list of dict
    """
    if not resume_text or job_df.empty:
        return []

    # 分词简历文本
    resume_tokens = set(jieba.lcut(resume_text.lower()))
    
    results = []
    for idx, row in job_df.iterrows():
        summary = str(row.get('job_summary', '')).lower()
        salary = str(row.get('salary', '面议'))
        job_name = str(row.get('position_name', '未知岗位'))
        comp_name = str(row.get('company_name', '未知公司'))
        
        # 分词岗位描述
        summary_tokens = set(jieba.lcut(summary))
        
        # 简易匹配度 = 交集词数 / (岗位关键词总数 + 1)
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
    
    # 排序取前 10
    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results[:10]


def modify_resume_for_job(original_resume, job_description, llm_mode, openai_key=None):
    """
    基于 original_resume 与 job_description，生成个性化修改后的简历文本 (演示)。
    """
    new_resume = (
        "【AI修改后的简历示例】\n\n"
        f"=== 原简历部分内容 ===\n{original_resume[:100]}...\n\n"
        f"=== 目标岗位需求 ===\n{job_description}\n\n"
        "=== 优化后简历示例 ===\n"
        "根据岗位需求匹配技能亮点，突出相关项目经验及技术栈。"
    )
    return new_resume


# ========== 主 UI 类 ==========

class JobUI:
    """
    Streamlit UI 主界面封装类。
    - 负责加载数据，管理会话状态，并与 DataProcessor、DataVisualizer 配合进行可视化与求职功能。
    """
    def __init__(self, data_root: Path):
        self.data_root = data_root
        self.data_dir = data_root / 'data'
        self._init_session_state()
        self.data_processor = None
        self.visualizer = None
        
    def _init_session_state(self):
        """初始化会话状态"""
        if 'resume_text' not in st.session_state:
            st.session_state['resume_text'] = ""
        if 'llm_mode' not in st.session_state:
            st.session_state['llm_mode'] = "本地 Ollama"
        if 'local_model' not in st.session_state:
            st.session_state['local_model'] = ""
        if 'openai_key' not in st.session_state:
            st.session_state['openai_key'] = ""
        if 'data_loaded' not in st.session_state:
            st.session_state['data_loaded'] = False

    def _load_data(self):
        """
        侧边栏或页面选择 CSV 文件并加载，
        用 DataProcessor 进行预处理，然后初始化 DataVisualizer。
        """
        csv_files = [f for f in self.data_dir.glob('*.csv')]
        if not csv_files:
            st.error("数据目录下未找到任何 CSV 文件，请先准备好数据文件。")
            return None
        
        selected_file = st.selectbox("请选择数据文件", [f.name for f in csv_files])
        
        if st.button("加载并分析数据") or st.session_state.get('data_loaded', False):
            data_file = self.data_dir / selected_file
            try:
                if not data_file.exists():
                    st.error(f"数据文件不存在: {data_file}")
                    return None
                    
                # 只有在未加载或文件变化时才重新加载
                if (not self.data_processor or 
                    str(data_file) != getattr(self.data_processor, 'current_file', None)):
                    self.data_processor = DataProcessor(data_file)
                    self.visualizer = DataVisualizer(self.data_processor)
                    # 保存当前文件路径以便后续比较
                    self.data_processor.current_file = str(data_file)
                
                st.session_state['data_loaded'] = True
                st.success(f"成功加载数据文件: {selected_file}")
                
                return True
                
            except Exception as e:
                st.error(f"加载数据失败: {str(e)}")
                return None
        
    def _setup_llm_settings(self):
        """
        侧边栏：设置 LLM 相关配置
        """
        st.sidebar.header("AI 设置")
        llm_mode = st.sidebar.radio(
            "选择 LLM 模式",
            options=["本地 Ollama", "OpenAI 在线模型"],
            index=0 if st.session_state['llm_mode'] == "本地 Ollama" else 1
        )
        st.session_state['llm_mode'] = llm_mode

        if llm_mode == "本地 Ollama":
            local_models = get_local_models()
            selected_model = st.sidebar.selectbox(
                "选择本地模型",
                local_models,
                key="local_model_select"
            )
            st.session_state['local_model'] = selected_model
        else:
            openai_key = st.sidebar.text_input(
                "输入 OpenAI API Key (必填)",
                value=st.session_state.get('openai_key', ""),
                type="password",
                key="openai_key_input"
            )
            st.session_state['openai_key'] = openai_key

    def setup_sidebar(self) -> Dict:
        """
        侧边栏：设置多项筛选条件并返回筛选器字典。
        - 薪资范围 (min, max) (单位：千元)
        - work_exp (最大年限)
        - education (0~4)
        - company_type (多选)
        - welfare_tags (多选)
        
        :return: dict 格式的各项筛选条件
        """
        st.sidebar.header("筛选条件")
        
        if not (self.data_processor and self.visualizer):
            return {}
        
        df = self.visualizer.processed_data
        
        # 薪资范围
        min_val = int(df['avg_salary'].min()) if len(df) else 0
        max_val = int(df['avg_salary'].max()) if len(df) else 50
        salary_range = st.sidebar.slider(
            "薪资范围 (千元)",
            min_value=min_val,
            max_value=max_val,
            value=(min_val, max_val)
        )
        
        # 工作经验 (work_exp)
        max_exp = int(df['work_exp'].max()) if len(df) else 10
        selected_exp = st.sidebar.slider(
            "最大工作经验 (年)",
            min_value=0,
            max_value=max_exp,
            value=max_exp
        )
        
        # 学历要求
        edu_options = ['不限', '大专', '本科', '硕士', '博士']
        education = st.sidebar.select_slider(
            "最低学历要求",
            options=edu_options,
            value='不限'
        )
        education_idx = edu_options.index(education)
        
        # 公司类型
        company_types = df['company_type'].unique().tolist()
        selected_company_types = st.sidebar.multiselect(
            "公司类型",
            options=company_types,
            default=company_types
        )
        
        # 福利标签
        all_welfare_tags = []
        for tags in df['welfare_tags']:
            all_welfare_tags.extend(tags)
        welfare_options = list(set(all_welfare_tags))
        selected_welfare_tags = st.sidebar.multiselect(
            "福利标签",
            options=welfare_options,
            default=[]
        )
        
        return {
            'salary_range': salary_range,
            'work_exp': selected_exp,
            'education': education_idx,
            'company_type': selected_company_types,
            'welfare_tags': selected_welfare_tags
        }

    def _handle_resume_upload(self):
        """
        页面中：上传并解析简历文件（PDF、Word）。
        解析后存入 session_state['resume_text']。
        """
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

    def _show_basic_analysis_tab(self, tab):
        """
        选项卡 1：显示基础可视化分析，包括薪资、学历、经验、公司类型分布等。
        """
        with tab:
            st.subheader("基础分析")
            if not self.visualizer:
                st.warning("请先加载数据")
                return
            
            st.plotly_chart(self.visualizer.plot_salary_distribution(), use_container_width=True)
            
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(self.visualizer.plot_education_pie(), use_container_width=True)
            with col2:
                st.plotly_chart(self.visualizer.plot_experience_bar(), use_container_width=True)
                
            col3, col4 = st.columns(2)
            with col3:
                st.plotly_chart(self.visualizer.plot_company_type_pie(), use_container_width=True)
            with col4:
                st.info("更多图表可在此扩展，如行业分布等...")
            
            wordcloud_data = self.visualizer.generate_job_wordcloud()
            if wordcloud_data:
                st.image(
                    BytesIO(base64.b64decode(wordcloud_data)), 
                    caption='职位描述关键词云图'
                )
            else:
                st.warning("无法生成词云，可能无有效职位描述数据")

    def _show_insights_tab(self, tab):
        """
        选项卡 2：显示岗位洞察报表，包括薪资、关键词等关键指标。
        """
        with tab:
            st.subheader("岗位洞察报表")
            if not self.visualizer:
                st.warning("请先加载数据")
                return
            
            insights = self.visualizer.generate_job_insights()
            
            # 展示关键薪资指标
            col1, col2, col3 = st.columns(3)
            col1.metric("平均薪资", f"{insights['salary']['avg']} 千元")
            col2.metric("最低薪资", f"{insights['salary']['min']} 千元")
            col3.metric("最高薪资", f"{insights['salary']['max']} 千元")
            
            # 展示高频关键词
            st.write("职位描述高频关键词 TOP 10：", ", ".join(insights['keywords']))
            
            # 绘制洞察可视化
            fig_salary, fig_keywords = self.visualizer.plot_insights_summary(insights)
            st.plotly_chart(fig_salary, use_container_width=True)
            st.plotly_chart(fig_keywords, use_container_width=True)
            
            # 导出洞察
            if st.button("导出洞察报表"):
                df_insights = pd.DataFrame.from_dict(insights, orient='index')
                csv_str = df_insights.to_csv()
                st.download_button(
                    label="下载 CSV 报表",
                    data=csv_str,
                    file_name='job_insights.csv',
                    mime='text/csv'
                )

    def _show_job_search_tab(self, tab):
        """
        选项卡 3：求职功能，包括简历上传、匹配与简历定制化修改。
        """
        with tab:
            st.subheader("求职中心：简历匹配与定制化修改")
            
            # 上传简历
            self._handle_resume_upload()
            
            # 若已上传简历，显示当前简历概览
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
            
            # 开始匹配
            if st.button("开始匹配"):
                if not st.session_state['resume_text']:
                    st.error("请先上传并解析简历文件！")
                else:
                    # 如果用户选择了OpenAI模式，但没填key
                    if (st.session_state['llm_mode'] == "OpenAI 在线模型" and 
                        not st.session_state['openai_key']):
                        st.error("请输入 OpenAI API Key！")
                        return
                    
                    st.info("正在进行岗位匹配，请稍候...")
                    
                    # 使用 processed_data 进行匹配
                    df = self.visualizer.processed_data
                    job_matches = match_jobs_with_resume(
                        resume_text=st.session_state['resume_text'],
                        job_df=df,
                        llm_mode=(
                            "local" if st.session_state['llm_mode'] == "本地 Ollama"
                            else "openai"
                        ),
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
                            
                            # 简历修改功能
                            with st.expander(f"🔧 修改简历以匹配岗位: {match['job_name']}"):
                                if st.button(f"生成针对 {match['job_name']} 的优化简历", key=f"modify_{i}"):
                                    final_resume = modify_resume_for_job(
                                        original_resume=st.session_state['resume_text'],
                                        job_description=(
                                            f"{match['job_name']} | {match['company_name']} | "
                                            f"薪资: {match['salary_range']}"
                                        ),
                                        llm_mode=(
                                            "local" if st.session_state['llm_mode'] == "本地 Ollama"
                                            else "openai"
                                        ),
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

    def run(self):
        """
        Streamlit 应用的主入口函数
        """
        st.set_page_config(
            page_title="AI岗位分析可视化 & 求职系统",
            layout="wide",
            initial_sidebar_state="expanded"
        )

        # 显示主界面标题
        st.title("AI 岗位分析可视化 & 求职系统")
        
        # 第一步：加载数据（如果需要）
        load_result = self._load_data()
        
        # 只有成功加载数据后才显示后续内容
        if load_result or st.session_state.get('data_loaded', False):
            # 第二步：设置 LLM 配置（侧边栏）
            self._setup_llm_settings()
            
            # 第三步：设置筛选条件（侧边栏）
            filters = self.setup_sidebar()
            
            # 应用筛选条件
            if self.data_processor and self.visualizer and filters:
                filtered_df = self.data_processor.filter_data(filters)
                self.visualizer.processed_data = filtered_df
            
            # 第四步：创建多选项卡
            tab1, tab2, tab3 = st.tabs(["基础分析", "岗位洞察报表", "求职"])
            
            self._show_basic_analysis_tab(tab1)
            self._show_insights_tab(tab2)
            self._show_job_search_tab(tab3)
        else:
            st.info("请先选择并加载数据文件")
