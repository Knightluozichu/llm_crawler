import base64
from io import BytesIO
from pathlib import Path
from typing import Dict

import pandas as pd
import streamlit as st

from data_processor import DataProcessor
from data_save import JobDatabase
from visualizer import DataVisualizer
from llm_hr import LLMHR


class JobUI:
    """
    Streamlit UI 主界面封装类。
    - 负责加载数据，管理会话状态，并与 DataProcessor、DataVisualizer 配合进行可视化与求职功能。
    """
    def __init__(self, data_root: Path):
        self.data_root = data_root
        self.data_dir = data_root / 'data'
        self._init_session_state()

        # 从会话状态获取或初始化
        self.data_processor = st.session_state['data_processor']
        self.visualizer = st.session_state['visualizer']
        self.hr = LLMHR()

    def _init_session_state(self):
        """统一初始化会话状态。"""
        default_states = {
            'resume_text': "",
            'llm_mode': "本地 Ollama",
            'local_model': "",
            'openai_key': "",
            'data_loaded': False,
            'optimized_resumes': {},
            'button_clicked': {},
            'job_matches': None,
            'matched_jobs_displayed': False,
            'current_job_index': None,
            'resume_generation_requested': {},
            'deepseek_key': "",
            'data_processor': None,
            'visualizer': None,
            'global_storage_type': '数据库'
        }
        for k, v in default_states.items():
            if k not in st.session_state:
                st.session_state[k] = v

    def _load_data(self):
        """用户在侧边栏或页面上选择 CSV 或数据库，并加载数据。"""
        if st.session_state['data_loaded']:
            st.info("数据已加载。若需重新加载，请重新选择并点击按钮。")

        source_type = st.selectbox("选择数据源", ["CSV文件", "数据库表"])
        if source_type == "CSV文件":
            csv_files = list(self.data_dir.glob('*.csv'))
            if not csv_files:
                st.error("数据目录下未找到任何 CSV 文件，请先准备好数据文件。")
                return None

            selected_file = st.selectbox("请选择数据文件", [f.name for f in csv_files])
            if st.button("加载并分析CSV数据"):
                data_file = self.data_dir / selected_file
                try:
                    if not data_file.exists():
                        st.error(f"数据文件不存在: {data_file}")
                        return None

                    # 初始化数据处理与可视化
                    self.data_processor = DataProcessor(data_file)
                    self.visualizer = DataVisualizer(self.data_processor)
                    st.session_state['data_processor'] = self.data_processor
                    st.session_state['visualizer'] = self.visualizer
                    st.session_state['data_loaded'] = True

                    st.success(f"成功加载CSV文件: {selected_file}")
                    return True

                except Exception as e:
                    st.error(f"加载数据失败: {str(e)}")
                    return None
        else:
            # 数据库表加载
            try:
                db = JobDatabase()
                table_names = db.get_table_names()
                if not table_names:
                    st.error("数据库中没有有效的表")
                    return None

                selected_table = st.selectbox("选择数据表", options=table_names)
                if st.button("加载并分析数据库数据"):
                    table_data = db.get_table_data(selected_table)
                    if not table_data:
                        st.error(f"表 {selected_table} 为空或读取失败")
                        return None

                    columns = [
                        'id', 'position_name', 'company_name', 'salary', 'work_city',
                        'work_exp', 'education', 'company_size', 'company_type',
                        'industry', 'position_url', 'job_summary', 'welfare', 'salary_count'
                    ]
                    df = pd.DataFrame(table_data, columns=columns)

                    temp_csv = self.data_dir / 'temp_db_data.csv'
                    df.to_csv(temp_csv, index=False)

                    self.data_processor = DataProcessor(temp_csv)
                    self.visualizer = DataVisualizer(self.data_processor)
                    st.session_state['data_processor'] = self.data_processor
                    st.session_state['visualizer'] = self.visualizer
                    st.session_state['data_loaded'] = True
                    st.session_state['selected_table'] = selected_table
                    st.session_state['table_data'] = table_data

                    st.success(f"成功加载数据表: {selected_table}")
                    return True

            except Exception as e:
                st.error(f"加载数据库失败: {str(e)}")
                return None

        return None

    def _setup_llm_settings(self):
        """设置 LLM 模式（本地/Ollama、OpenAI、Deepseek）。"""
        st.sidebar.header("AI 设置")
        mode_options = ["本地 Ollama", "OpenAI 在线模型", "Deepseek 在线模型"]
        llm_mode = st.sidebar.radio("选择 LLM 模式", options=mode_options, key="llm_mode")

        if llm_mode == "本地 Ollama":
            self.hr.change_llm_mode("local")
            local_models = self.hr.get_local_models()
            selected_model = st.sidebar.selectbox("选择本地模型", local_models, key="local_model_select")
            st.session_state['local_model'] = selected_model
            self.hr.set_local_model(selected_model)
        elif llm_mode == "OpenAI 在线模型":
            self.hr.change_llm_mode("openai")
            openai_key = st.sidebar.text_input(
                "输入 OpenAI API Key (必填)",
                value=st.session_state.get('openai_key', ""),
                type="password"
            )
            st.session_state['openai_key'] = openai_key
        else:
            self.hr.change_llm_mode("deepseek")
            deepseek_key = st.sidebar.text_input(
                "输入 Deepseek API Key (必填)",
                value=st.session_state.get('deepseek_key', ""),
                type="password"
            )
            st.session_state['deepseek_key'] = deepseek_key

    def setup_sidebar(self) -> Dict:
        """侧边栏筛选条件：薪资范围、工作经验、学历、公司类型、福利标签"""
        st.sidebar.header("筛选条件")

        if not (self.data_processor and self.visualizer):
            return {}

        df = self.visualizer.processed_data

        if len(df) > 0:
            min_val = max(0, int(df['avg_salary'].min()))
            max_val = max(50, int(df['avg_salary'].max()))
            if min_val == max_val:
                max_val = min_val + 10
        else:
            min_val, max_val = 0, 50

        salary_range = st.sidebar.slider(
            "薪资范围 (千元)",
            min_value=min_val,
            max_value=max_val,
            value=(min_val, max_val)
        )

        max_exp = int(df['work_exp'].max()) if len(df) else 10
        selected_exp = st.sidebar.slider("最大工作经验 (年)", min_value=0, max_value=max_exp, value=max_exp)

        edu_options = ['不限', '大专', '本科', '硕士', '博士']
        education = st.sidebar.select_slider("最低学历要求", options=edu_options, value='不限')
        education_idx = edu_options.index(education)

        company_types = df['company_type'].unique().tolist()
        selected_company_types = st.sidebar.multiselect(
            "公司类型",
            options=company_types,
            default=company_types
        )

        # 收集 welfare_tags
        all_welfare_tags = []
        for tags in df.get('welfare_tags', []):
            if isinstance(tags, list):
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
        """上传并解析简历文件（PDF、Word）。"""
        uploaded_file = st.file_uploader("上传简历（PDF或Word）", type=["pdf", "doc", "docx"])
        if uploaded_file is not None:
            file_type = uploaded_file.name.split('.')[-1].lower()
            file_bytes = uploaded_file.read()
            new_text = self.hr.parse_resume(file_bytes, file_type)

            if new_text != st.session_state['resume_text']:
                st.session_state['resume_text'] = new_text
                st.success("简历上传并解析成功！")

    def _show_basic_analysis_tab(self, tab):
        """
        1. 基础分析：
           - 薪资分布、学历、经验、公司类型
           - 词云
           - 岗位分布（原先在 _show_job_distribution_tab 的内容）
           - 技能需求（原先在 _show_skill_demand_tab 的内容）
        """
        with tab:
            st.subheader("基础分析")
            if not self.visualizer:
                st.warning("请先加载数据")
                return

            # 原始基础分析
            st.plotly_chart(self.visualizer.plot_salary_distribution(), use_container_width=True, 
                            key="basic_salary_dist")

            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(self.visualizer.plot_education_pie(), use_container_width=True, 
                                key="basic_education_pie")
            with col2:
                st.plotly_chart(self.visualizer.plot_experience_bar(), use_container_width=True, 
                                key="basic_experience_bar")

            col3, col4 = st.columns(2)
            with col3:
                st.plotly_chart(self.visualizer.plot_company_type_pie(), use_container_width=True, 
                                key="basic_company_type_pie")
            with col4:
                st.plotly_chart(self.visualizer.plot_job_distribution_bar(), use_container_width=True, 
                            key="job_dist_bar")
                
            col5, col6 = st.columns(2)
            with col5:
                st.plotly_chart(self.visualizer.plot_job_distribution_pie(), use_container_width=True, 
                            key="job_dist_pie")
            with col6:
                st.plotly_chart(self.visualizer.plot_skill_bar(), use_container_width=True,
                            key="skill_bar_chart")
                
            wordcloud_data = self.visualizer.plot_wordcloud()
            if wordcloud_data:
                st.image(BytesIO(base64.b64decode(wordcloud_data)), caption='职位描述关键词云图')
            else:
                st.warning("无法生成词云，可能无有效职位描述数据")


    def _show_insights_tab(self, tab):
        """2. 岗位洞察报表"""
        with tab:
            st.subheader("岗位洞察报表")
            if not self.visualizer:
                st.warning("请先加载数据")
                return

            insights = self.visualizer.generate_job_insights()
            col1, col2, col3 = st.columns(3)
            col1.metric("平均薪资", f"{insights['salary']['avg']} 千元")
            col2.metric("最低薪资", f"{insights['salary']['min']} 千元")
            col3.metric("最高薪资", f"{insights['salary']['max']} 千元")

            st.write("职位描述高频关键词 TOP 10：", ", ".join(insights['keywords']))

            fig_salary, fig_exp = self.visualizer.plot_insights_summary(insights)
            st.plotly_chart(fig_salary, use_container_width=True, key="insights_salary_dist")
            st.plotly_chart(fig_exp, use_container_width=True, key="insights_exp_bar")

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
        """3. 求职中心：简历匹配、定制化修改、打分。"""
        with tab:
            st.subheader("求职中心：简历匹配与定制化修改")
            self._handle_resume_upload()

            if st.session_state['resume_text']:
                st.write("---")
                st.subheader("已解析的简历内容")
                st.write(st.session_state['resume_text'])

            st.warning("请注意保护个人信息隐私，如使用在线模型时需确保已了解相关风险。")

            if st.button("开始匹配") or st.session_state['matched_jobs_displayed']:
                if not st.session_state['resume_text']:
                    st.error("请先上传并解析简历文件！")
                else:
                    if not st.session_state['matched_jobs_displayed']:
                        df = self.visualizer.processed_data
                        # job_matches = self.hr.match_jobs_with_resume(
                        job_matches = self.hr.match_jobs_with_resume_llm(
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

                            with st.expander(f"🔧 修改简历以匹配岗位: {match['job_name']}"):
                                modify_button_key = f"modify_{job_index}"
                                already_optimized = job_index in st.session_state['optimized_resumes']

                                if st.button(
                                    "查看优化后的简历" if already_optimized else f"生成针对 {match['job_name']} 的优化简历",
                                    key=modify_button_key
                                ):
                                    st.session_state['resume_generation_requested'][job_index] = True

                                if st.session_state['resume_generation_requested'].get(job_index):
                                    if not already_optimized:
                                        with st.spinner("正在生成优化后的简历..."):
                                            final_resume = self.hr.modify_resume_for_job(
                                                original_resume=st.session_state['resume_text'],
                                                job_description=(
                                                    f"{match['job_name']} | {match['company_name']} | "
                                                    f"薪资: {match['salary_range']}"
                                                ),
                                                # llm_mode=(
                                                #     "local" if st.session_state['llm_mode'] == "本地 Ollama"
                                                #     else "openai" if st.session_state['llm_mode'] == "OpenAI 在线模型"
                                                #     else "Deepseek 在线模型"
                                                # ),
                                                # openai_key=st.session_state.get('openai_key', ""),
                                                # deepseek_key=st.session_state.get('deepseek_key', "")
                                            )
                                            st.session_state['optimized_resumes'][job_index] = {
                                                'resume': final_resume,
                                                'job_name': match['job_name']
                                            }

                                    st.write("---")
                                    st.subheader("AI优化后的简历内容:")
                                    st.write(st.session_state['optimized_resumes'][job_index]['resume'])

                                    dl_data = st.session_state['optimized_resumes'][job_index]['resume'].encode("utf-8")
                                    st.download_button(
                                        label="下载修改后简历 (txt)",
                                        data=dl_data,
                                        file_name=f"modified_resume_{match['job_name']}.txt",
                                        mime="text/plain"
                                    )

            if st.button("对简历进行打分"):
                # report = self.hr.score_resume(st.session_state['resume_text'])
                report = self.hr.score_resume_llm(st.session_state['resume_text'])
                st.subheader("简历评分报告")
                st.write(report)

    def run(self):
        """Streamlit 应用主入口。"""
        # Removed set_page_config as it's now in visual_data.py
        
        load_result = self._load_data()
        if load_result or st.session_state.get('data_loaded', False):
            self.data_processor = st.session_state['data_processor']
            self.visualizer = st.session_state['visualizer']

            self._setup_llm_settings()
            filters = self.setup_sidebar()
            if self.data_processor and self.visualizer and filters:
                filtered_df = self.data_processor.filter_data(filters)
                self.visualizer.processed_data = filtered_df

            # 只保留三个主要选项卡
            tab_basic, tab_insights, tab_jobsearch = st.tabs([
                "基础分析",      # tab_basic
                "岗位洞察报表",  # tab_insights
                "求职中心"       # tab_jobsearch
            ])

            # 调用各自的显示方法
            self._show_basic_analysis_tab(tab_basic)
            self._show_insights_tab(tab_insights)
            self._show_job_search_tab(tab_jobsearch)

        else:
            st.info("请先选择并加载数据文件")