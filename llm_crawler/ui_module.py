import base64
from io import BytesIO
from pathlib import Path
from typing import Dict

import pandas as pd
import streamlit as st

from data_processor import DataProcessor
from visualizer import DataVisualizer
from llm_hr import LLMHR  # 新增

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
        self.hr = LLMHR()  # 新增：使用 LLMHR
        
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
        # 新增：优化简历相关的状态
        if 'optimized_resumes' not in st.session_state:
            st.session_state['optimized_resumes'] = {}
        if 'button_clicked' not in st.session_state:
            st.session_state['button_clicked'] = {}
        if 'job_matches' not in st.session_state:
            st.session_state['job_matches'] = None
        if 'matched_jobs_displayed' not in st.session_state:
            st.session_state['matched_jobs_displayed'] = False
        if 'current_job_index' not in st.session_state:
            st.session_state['current_job_index'] = None
        if 'resume_generation_requested' not in st.session_state:
            st.session_state['resume_generation_requested'] = {}
        if 'deepseek_key' not in st.session_state:
            st.session_state['deepseek_key'] = ""

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
        mode_options = ["本地 Ollama", "OpenAI 在线模型", "Deepseek 在线模型"]
        llm_mode = st.sidebar.radio(
            "选择 LLM 模式",
            options=mode_options,
            key="llm_mode"  # 直接使用 key 管理选中的值
        )

        if llm_mode == "本地 Ollama":
            local_models = self.hr.get_local_models()  # 新引用
            selected_model = st.sidebar.selectbox(
                "选择本地模型",
                local_models,
                key="local_model_select"
            )
            st.session_state['local_model'] = selected_model
        elif llm_mode == "OpenAI 在线模型":
            openai_key = st.sidebar.text_input(
                "输入 OpenAI API Key (必填)",
                value=st.session_state.get('openai_key', ""),
                type="password",
                key="openai_key_input"
            )
            st.session_state['openai_key'] = openai_key
        elif llm_mode == "Deepseek 在线模型":  # 保持与 llm_hr.py 中的判断一致
            deepseek_key = st.sidebar.text_input(
                "输入 Deepseek API Key (必填)",
                value=st.session_state.get('deepseek_key', ""),
                type="password",
                key="deepseek_key_input"
            )
            st.session_state['deepseek_key'] = deepseek_key

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
            
            new_text = self.hr.parse_resume(file_bytes, file_type)  # 新引用
            if new_text != st.session_state['resume_text']:
                st.session_state['resume_text'] = new_text
                st.success("简历上传并解析成功！")
                
                # 自动匹配并打分
                if self.visualizer:
                    df = self.visualizer.processed_data
                    job_matches = self.hr.match_jobs_with_resume(  # 新引用
                        resume_text=new_text,
                        job_df=df
                    )
                    st.session_state['auto_job_matches'] = job_matches
                    st.session_state['auto_resume_score'] = self.hr.score_resume(new_text)  # 新引用

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
                # 移除截断, 直接输出全文
                st.write(st.session_state['resume_text'])
            
            st.warning("请注意保护个人信息隐私，如使用在线模型时需确保已了解相关风险。")
            
            # 确保 session_state 中存在优化后的简历
            if 'optimized_resumes' not in st.session_state:
                st.session_state['optimized_resumes'] = {}
            
            # 开始匹配
            if st.button("开始匹配") or st.session_state['matched_jobs_displayed']:
                if not st.session_state['resume_text']:
                    st.error("请先上传并解析简历文件！")
                else:
                    if not st.session_state['matched_jobs_displayed']:
                        # 只在第一次点击时执行匹配
                        df = self.visualizer.processed_data
                        job_matches = self.hr.match_jobs_with_resume(  # 新引用
                            resume_text=st.session_state['resume_text'],
                            job_df=df
                        )
                        st.session_state['job_matches'] = job_matches
                        st.session_state['matched_jobs_displayed'] = True
                    
                    if st.session_state['job_matches']:
                        st.success("已找到前 10 条最匹配岗位：")
                        for i, match in enumerate(st.session_state['job_matches']):
                            job_index = match['job_index']
                            
                            st.markdown(f"**{i+1}. 岗位名称:** {match['job_name']}")
                            st.markdown(f"**公司名称:** {match['company_name']}")
                            st.markdown(f"**匹配度评分:** {match['match_score']}")
                            st.markdown(f"**匹配原因:** {match['match_reason']}")
                            st.markdown(f"**薪资范围:** {match['salary_range']}")
                            
                            # 简历修改功能
                            with st.expander(f"🔧 修改简历以匹配岗位: {match['job_name']}"):
                                modify_button_key = f"modify_{job_index}"
                                
                                # 检查是否已经生成过优化简历
                                already_optimized = job_index in st.session_state['optimized_resumes']
                                
                                if st.button(
                                    "查看优化后的简历" if already_optimized else f"生成针对 {match['job_name']} 的优化简历",
                                    key=modify_button_key
                                ):
                                    st.session_state['resume_generation_requested'][job_index] = True
                                
                                # 处理简历生成请求
                                if st.session_state['resume_generation_requested'].get(job_index):
                                    if not already_optimized:
                                        with st.spinner("正在生成优化后的简历..."):
                                            final_resume = self.hr.modify_resume_for_job(  # 新引用
                                                original_resume=st.session_state['resume_text'],
                                                job_description=(
                                                    f"{match['job_name']} | {match['company_name']} | "
                                                    f"薪资: {match['salary_range']}"
                                                ),
                                                llm_mode=(
                                                    "local" if st.session_state['llm_mode'] == "本地 Ollama"
                                                    else "openai" if st.session_state['llm_mode'] == "OpenAI 在线模型"
                                                    else "Deepseek 在线模型"  # 与 llm_hr.py 中保持一致
                                                ),
                                                openai_key=st.session_state.get('openai_key', ""),
                                                deepseek_key=st.session_state.get('deepseek_key', "")
                                            )
                                            st.session_state['optimized_resumes'][job_index] = {
                                                'resume': final_resume,
                                                'job_name': match['job_name']
                                            }
                                    
                                    # 显示优化后的简历
                                    st.write("---")
                                    st.subheader("AI优化后的简历内容:")
                                    st.write(st.session_state['optimized_resumes'][job_index]['resume'])
                                    
                                    # 下载按钮
                                    dl_data = st.session_state['optimized_resumes'][job_index]['resume'].encode("utf-8")
                                    st.download_button(
                                        label="下载修改后简历 (txt)",
                                        data=dl_data,
                                        file_name=f"modified_resume_{match['job_name']}.txt",
                                        mime="text/plain"
                                    )

            # 新增简历打分功能
            if st.button("对简历进行打分"):
                report = self.hr.score_resume(st.session_state['resume_text'])  # 新引用
                st.subheader("简历评分报告")
                st.write(report)
                
            # 显示优化后的简历
            if 'current_optimized_resume' in st.session_state:
                st.write("---")
                st.subheader(f"已优化的简历内容 (针对岗位: {st.session_state['current_job_name']})")
                st.write(st.session_state['current_optimized_resume'])

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
