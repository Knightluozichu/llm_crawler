import streamlit as st
from typing import Dict, List
from .data_processor import DataProcessor
from .visualizer import DataVisualizer
from pathlib import Path
import base64
from io import BytesIO

class JobUI:
    def __init__(self, data_root: Path):
        self.data_root = data_root
        self.data_dir = data_root / 'data'
        self._init_session_state()
        
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
        """加载数据文件"""
        csv_files = [f for f in self.data_dir.glob('*.csv')]
        if not csv_files:
            st.error("数据目录下未找到任何 CSV 文件，请先准备好数据文件。")
            return None
            
        selected_file = st.selectbox("请选择数据文件", [f.name for f in csv_files])
        
        if st.button("加载并分析数据"):
            data_file = self.data_dir / selected_file
            try:
                if not data_file.exists():
                    st.error(f"数据文件不存在: {data_file}")
                    return None
                    
                self.visualizer = DataVisualizer(str(data_file))
                st.session_state['data_loaded'] = True
                st.rerun()
                
            except Exception as e:
                st.error(f"加载数据失败: {str(e)}")
                return None
        
    def setup_sidebar(self):
        """设置侧边栏筛选条件"""
        st.sidebar.header("筛选条件")
        
        # 薪资范围
        min_salary = int(self.visualizer.processed_data['min_salary'].min())
        max_salary = int(self.visualizer.processed_data['max_salary'].max())
        salary_range = st.sidebar.slider(
            "薪资范围 (千元)",
            min_value=min_salary,
            max_value=max_salary,
            value=(min_salary, max_salary)
        )
        
        # 工作经验
        max_exp = int(self.visualizer.processed_data['experience'].max())
        experience = st.sidebar.slider(
            "工作经验 (年)",
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
        
        # 公司类型
        company_types = self.visualizer.processed_data['company_type'].unique().tolist()
        selected_company_types = st.sidebar.multiselect(
            "公司类型",
            options=company_types,
            default=company_types
        )
        
        # 福利标签
        all_welfare_tags = [
            tag for tags in self.visualizer.processed_data['welfare_tags'] 
            for tag in tags
        ]
        welfare_options = list(set(all_welfare_tags))
        selected_welfare_tags = st.sidebar.multiselect(
            "福利标签",
            options=welfare_options,
            default=[]
        )
        
        return {
            'salary_range': salary_range,
            'experience': experience,
            'education': edu_options.index(education),
            'company_type': selected_company_types,
            'welfare_tags': selected_welfare_tags
        }
        
    def display_insights(self):
        """展示数据洞察"""
        st.header("职位数据洞察")
        
        # 获取洞察数据
        insights = self.visualizer.generate_job_insights()
        
        # 展示关键指标
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("平均薪资", f"{insights['salary']['avg']} 千元")
        with col2:
            st.metric("最低薪资", f"{insights['salary']['min']} 千元")
        with col3:
            st.metric("最高薪资", f"{insights['salary']['max']} 千元")
            
        # 展示热门技能
        st.subheader("热门技能要求")
        st.write(", ".join(insights['skills']))
        
    def display_visualizations(self):
        """展示可视化图表"""
        st.header("数据可视化")
        
        # 薪资分布
        st.subheader("薪资分布")
        salary_fig = self.visualizer.plot_salary_distribution()
        st.plotly_chart(salary_fig, use_container_width=True)
        
        # 学历分布
        st.subheader("学历要求分布")
        edu_fig = self.visualizer.plot_education_pie()
        st.plotly_chart(edu_fig, use_container_width=True)
        
        # 工作经验分布
        st.subheader("工作经验要求分布")
        exp_fig = self.visualizer.plot_experience_bar()
        st.plotly_chart(exp_fig, use_container_width=True)
        
        # 公司类型分布
        st.subheader("公司类型分布")
        company_fig = self.visualizer.plot_company_type_pie()
        st.plotly_chart(company_fig, use_container_width=True)
        
        # 职位描述词云
        st.subheader("职位描述词云")
        wordcloud_img = self.visualizer.generate_job_wordcloud()
        if wordcloud_img:
            st.image(BytesIO(base64.b64decode(wordcloud_img)))
        else:
            st.warning("无法生成词云，可能缺少职位描述数据")
            
    def _setup_llm_settings(self):
        """设置LLM相关配置"""
        st.sidebar.header("AI设置")
        llm_mode = st.sidebar.radio(
            "选择LLM模式",
            options=["本地 Ollama", "OpenAI 在线模型"],
            index=0 if st.session_state['llm_mode'] == "本地 Ollama" else 1
        )
        st.session_state['llm_mode'] = llm_mode

        if llm_mode == "本地 Ollama":
            from .visual_data import get_local_models
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

    def _handle_resume_upload(self):
        """处理简历上传"""
        uploaded_file = st.file_uploader(
            "上传简历（PDF或Word）",
            type=["pdf", "doc", "docx"],
            key="resume_uploader"
        )
        
        if uploaded_file is not None:
            from .visual_data import parse_resume
            file_type = uploaded_file.name.split('.')[-1].lower()
            file_bytes = uploaded_file.read()
            
            new_text = parse_resume(file_bytes, file_type)
            if new_text != st.session_state['resume_text']:
                st.session_state['resume_text'] = new_text
                st.success("简历上传并解析成功！")
                st.write("简历解析结果：")
                st.write(new_text[:300] + "..." if len(new_text) > 300 else new_text)

    def _show_basic_analysis_tab(self, tab):
        """显示基础分析选项卡"""
        with tab:
            st.plotly_chart(self.visualizer.plot_salary_distribution())
            
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(self.visualizer.plot_education_pie())
            with col2:
                st.plotly_chart(self.visualizer.plot_experience_bar())
                
            col3, col4 = st.columns(2)
            with col3:
                st.plotly_chart(self.visualizer.plot_company_type_pie())
            with col4:
                st.plotly_chart(self.visualizer.plot_welfare_bars())
            
            wordcloud = self.visualizer.generate_job_wordcloud()
            if wordcloud:
                st.image(BytesIO(base64.b64decode(wordcloud)), caption='职位描述关键词云图')

    def _show_insights_tab(self, tab):
        """显示洞察报表选项卡"""
        with tab:
            insights = self.visualizer.generate_job_insights()
            
            st.header("岗位市场洞察")
            
            st.subheader("💰 薪资分析")
            salary_insights = insights['薪资分析']
            cols = st.columns(3)
            cols[0].metric("平均薪资", salary_insights['平均薪资'])
            cols[1].metric("最高薪资", salary_insights['最高薪资'])
            cols[2].metric("最低薪资", salary_insights['最低薪资'])
            
            fig_salary, fig_skills = self.visualizer.plot_insights_summary(insights)
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

    def _show_job_search_tab(self, tab):
        """显示求职功能选项卡"""
        with tab:
            st.header("求职中心：简历匹配与定制化修改")
            self._handle_resume_upload()
            
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
            
            # 显示匹配结果
            if st.button("开始匹配", key="start_matching"):
                from .visual_data import match_jobs_with_resume, modify_resume_for_job
                
                if not st.session_state['resume_text']:
                    st.error("请先上传并解析简历文件！")
                elif st.session_state['llm_mode'] == "OpenAI 在线模型" and not st.session_state['openai_key']:
                    st.error("请输入 OpenAI API Key！")
                else:
                    st.info("正在进行岗位匹配，请稍候...")
                    job_matches = match_jobs_with_resume(
                        resume_text=st.session_state['resume_text'],
                        job_df=self.visualizer.df,
                        llm_mode="local" if st.session_state['llm_mode'] == "本地 Ollama" else "openai",
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
                                        job_description=(f"{match['job_name']} | {match['company_name']} | "
                                                        f"薪资: {match['salary_range']}"),
                                        llm_mode=("local" if st.session_state['llm_mode']=="本地 Ollama" else "openai"),
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
        """运行主界面"""
        st.set_page_config(
            page_title="AI岗位分析可视化 & 求职系统",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # 加载数据
        if not self._load_data():
            return
            
        # 初始化侧边栏
        self._setup_llm_settings()
        filters = self.setup_sidebar()
        
        # 创建多选项卡布局
        tab1, tab2, tab3 = st.tabs(["基础分析", "岗位洞察报表", "求职"])
        
        # 过滤数据
        filtered_data = self.visualizer.filter_jobs(
            education=filters['education'],
            experience=filters['experience'],
            skills=[],
            welfare=filters['welfare_tags']
        )
        self.visualizer.df = filtered_data
        
        # 显示各选项卡内容
        self._show_basic_analysis_tab(tab1)
        self._show_insights_tab(tab2) 
        self._show_job_search_tab(tab3)
