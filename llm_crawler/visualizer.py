import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from typing import Dict, List, Any
from collections import Counter
from pathlib import Path

from data_processor import DataProcessor

class DataVisualizer:
    def __init__(self, data_processor: DataProcessor):
        self.data_processor = data_processor
        self.processed_data = data_processor.get_processed_data()

    # ==================== 原有方法（保留） ====================

    def generate_job_insights(self) -> Dict[str, Any]:
        insights = {}

        avg_salary = round(self.processed_data['avg_salary'].mean(), 1)
        min_salary = self.processed_data['min_salary'].min()
        max_salary = self.processed_data['max_salary'].max()
        insights['salary'] = {
            'avg': avg_salary,
            'min': min_salary,
            'max': max_salary
        }

        # 高频关键词
        all_words = [word for words_list in self.processed_data['job_desc_words'] for word in words_list]
        counter = Counter(all_words)
        top_words = counter.most_common(20)
        insights['keywords'] = [word for (word, freq) in top_words]

        return insights

    def plot_salary_distribution(self) -> go.Figure:
        fig = px.histogram(
            self.processed_data,
            x='avg_salary',
            nbins=30,
            labels={'avg_salary': '平均薪资 (千元)'},
            title='薪资分布'
        )
        fig.update_layout(
            xaxis_title='平均薪资 (千元)',
            yaxis_title='职位数量',
            showlegend=False
        )
        return fig

    def plot_education_pie(self) -> go.Figure:
        edu_map = {0: '不限', 1: '大专', 2: '本科', 3: '硕士', 4: '博士'}
        edu_data = self.processed_data['education'].map(edu_map)
        edu_counts = edu_data.value_counts()

        fig = px.pie(
            edu_counts,
            values=edu_counts.values,
            names=edu_counts.index,
            title='学历要求分布'
        )
        return fig

    def plot_experience_bar(self) -> go.Figure:
        exp_counts = self.processed_data['work_exp'].value_counts().sort_index()

        fig = px.bar(
            exp_counts,
            x=exp_counts.index,
            y=exp_counts.values,
            labels={'x': '工作经验 (年)', 'y': '职位数量'},
            title='工作经验要求分布'
        )
        return fig

    def plot_company_type_pie(self) -> go.Figure:
        company_counts = self.processed_data['company_type'].value_counts()

        fig = px.pie(
            company_counts,
            values=company_counts.values,
            names=company_counts.index,
            title='公司类型分布'
        )
        return fig

    def plot_salary_by_experience(self) -> go.Figure:
        fig = px.box(
            self.processed_data,
            x='work_exp',
            y='avg_salary',
            labels={'x': '工作经验 (年)', 'y': '平均薪资 (千元)'},
            title='薪资与工作经验关系'
        )
        return fig

    def plot_salary_by_education(self) -> go.Figure:
        edu_salary = self.processed_data.groupby('education')['avg_salary'].mean().reset_index()
        fig = px.bar(
            edu_salary,
            x='education',
            y='avg_salary',
            labels={'education': '学历', 'avg_salary': '平均薪资 (千元)'},
            title='学历与薪资关系'
        )
        return fig

    def plot_company_size_dist(self) -> go.Figure:
        fig = px.histogram(
            self.processed_data,
            x='company_size',
            nbins=20,
            labels={'company_size': '公司规模'},
            title='公司规模分布'
        )
        return fig

    def plot_position_industry_dist(self) -> go.Figure:
        group_data = self.processed_data.groupby('industry')['industry'].count().reset_index(name='count')
        fig = px.pie(
            group_data,
            values='count',
            names='industry',
            title='职位行业分布'
        )
        return fig

    def plot_wordcloud(self) -> str:
        if 'job_desc_words' not in self.processed_data.columns:
            return None

        all_words = [word for words_list in self.processed_data['job_desc_words'] for word in words_list]
        counter = Counter(all_words)

        try:
            font_paths = [
                '/System/Library/Fonts/PingFang.ttc',
                '/System/Library/Fonts/STHeiti Light.ttc',
                '/System/Library/Fonts/Arial Unicode.ttf'
            ]

            font_path = None
            for path in font_paths:
                if Path(path).exists():
                    font_path = path
                    break

            if not font_path:
                wc = WordCloud(width=800, height=400)
            else:
                wc = WordCloud(font_path=font_path, width=800, height=400)

            wc.generate_from_frequencies(counter)

            img = BytesIO()
            plt.figure(figsize=(10, 5))
            plt.imshow(wc, interpolation='bilinear')
            plt.axis('off')
            plt.savefig(img, format='png', bbox_inches='tight', pad_inches=0)
            plt.close()
            return base64.b64encode(img.getvalue()).decode()

        except Exception as e:
            print(f"生成词云时出错: {str(e)}")
            return None

    def plot_insights_summary(self, insights: Dict[str, Any]) -> (go.Figure, go.Figure):
        """
        绘制薪资区间分布 & 工作经验与薪资关系
        """
        bins = [0, 5000, 10000, 15000, 100000]
        labels = ['0-5k', '5k-10k', '10k-15k', '>15k']

        salary_bins = pd.cut(
            self.processed_data['avg_salary'],
            bins=bins,
            labels=labels
        )
        salary_dist = salary_bins.value_counts().sort_index()

        fig_salary = px.bar(
            salary_dist,
            x=salary_dist.index,
            y=salary_dist.values,
            title='薪资区间分布',
            labels={'x': '薪资区间 (千元)', 'y': '职位数量'}
        )

        salary_by_exp = self.processed_data.groupby('work_exp')['avg_salary'].mean().reset_index()
        fig_exp = px.bar(
            salary_by_exp,
            x='work_exp',
            y='avg_salary',
            labels={'work_exp': '工作经验 (年)', 'avg_salary': '平均薪资 (千元)'},
            title='工作经验与薪资关系'
        )

        return fig_salary, fig_exp

    # ==================== 以下为根据需求明细新增的示例方法 ====================

    # 1. 岗位分布
    def plot_job_distribution_bar(self, city_col='work_city') -> go.Figure:
        city_counts = self.processed_data[city_col].value_counts()
        fig = px.bar(
            city_counts,
            x=city_counts.index,
            y=city_counts.values,
            labels={'x': '城市', 'y': '岗位数量'},
            title='岗位分布（城市）'
        )
        return fig

    def plot_job_distribution_pie(self, industry_col='industry') -> go.Figure:
        industry_counts = self.processed_data[industry_col].value_counts()
        fig = px.pie(
            industry_counts,
            values=industry_counts.values,
            names=industry_counts.index,
            title='岗位分布（行业）'
        )
        return fig

    def plot_job_distribution_map(self, lat_col='latitude', lon_col='longitude') -> go.Figure:
        if lat_col not in self.processed_data.columns or lon_col not in self.processed_data.columns:
            return go.Figure()  # 空图

        fig = px.scatter_mapbox(
            self.processed_data,
            lat=lat_col,
            lon=lon_col,
            hover_name='company_name',
            hover_data=['position_name', 'avg_salary'],
            zoom=3,
            height=500
        )
        fig.update_layout(
            mapbox_style="open-street-map",
            title="岗位地理分布图"
        )
        return fig

    # 2. 技能需求
    def plot_skill_heatmap(self, skill_freq_df: pd.DataFrame = None) -> go.Figure:
        if skill_freq_df is None or skill_freq_df.empty:
            return go.Figure()

        fig = px.imshow(
            skill_freq_df,
            labels=dict(color="需求量"),
            x=skill_freq_df.columns,
            y=skill_freq_df.index,
            title='技能需求热力图'
        )
        return fig

    def plot_skill_bar(self, skill_col='skill_name', count_col='skill_count') -> go.Figure:
        if skill_col not in self.processed_data.columns or count_col not in self.processed_data.columns:
            return go.Figure()

        df_skill = (
            self.processed_data
            .groupby(skill_col)[count_col]
            .sum()
            .reset_index()
            .sort_values(count_col, ascending=False)
        )
        fig = px.bar(
            df_skill,
            x=skill_col,
            y=count_col,
            title='技能需求量对比',
            labels={skill_col: '技能名称', count_col: '需求量'}
        )
        return fig

    def plot_skill_radar(self, skill_stats: Dict[str, float] = None) -> go.Figure:
        if not skill_stats:
            return go.Figure()

        categories = list(skill_stats.keys())
        values = list(skill_stats.values())
        values.append(values[0])
        categories.append(categories[0])

        fig = go.Figure(
            data=go.Scatterpolar(
                r=values,
                theta=categories,
                fill='toself',
                name='技能多样性'
            )
        )
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            title='技能多样性雷达图'
        )
        return fig

    # 3. 晋升路径
    def plot_promotion_tree(self, promotion_data: pd.DataFrame = None) -> go.Figure:
        if promotion_data is None or promotion_data.empty:
            return go.Figure()

        fig = px.treemap(
            promotion_data,
            path=['source_position', 'target_position'],
            values='value',
            title='晋升路径树状图'
        )
        return fig

    def plot_promotion_flow(self, promotion_data: pd.DataFrame = None) -> go.Figure:
        if promotion_data is None or promotion_data.empty:
            return go.Figure()

        all_nodes = list(set(promotion_data['source'].unique()) | set(promotion_data['target'].unique()))
        node_idx_map = {node: i for i, node in enumerate(all_nodes)}

        fig = go.Figure(
            data=[go.Sankey(
                node=dict(
                    pad=15,
                    thickness=20,
                    line=dict(color="black", width=0.5),
                    label=all_nodes
                ),
                link=dict(
                    source=promotion_data['source'].map(node_idx_map),
                    target=promotion_data['target'].map(node_idx_map),
                    value=promotion_data['value']
                )
            )]
        )
        fig.update_layout(title_text="晋升流程图", font_size=10)
        return fig

    def plot_promotion_heatmap(self, promotion_matrix: pd.DataFrame = None) -> go.Figure:
        if promotion_matrix is None or promotion_matrix.empty:
            return go.Figure()

        fig = px.imshow(
            promotion_matrix,
            labels=dict(color="晋升可能性"),
            x=promotion_matrix.columns,
            y=promotion_matrix.index,
            title='晋升路径热力图'
        )
        return fig

    # 4. 薪资水平
    def plot_salary_box(self, group_col='position_name', value_col='avg_salary') -> go.Figure:
        if group_col not in self.processed_data.columns or value_col not in self.processed_data.columns:
            return go.Figure()

        fig = px.box(
            self.processed_data,
            x=group_col,
            y=value_col,
            title='薪资分布箱线图',
            labels={group_col: '职位', value_col: '薪资（千元）'}
        )
        return fig

    def plot_salary_bar(self, group_col='department', value_col='avg_salary') -> go.Figure:
        if group_col not in self.processed_data.columns or value_col not in self.processed_data.columns:
            return go.Figure()

        df_group = self.processed_data.groupby(group_col)[value_col].mean().reset_index()
        fig = px.bar(
            df_group,
            x=group_col,
            y=value_col,
            title='平均薪资对比',
            labels={group_col: '部门/职位', value_col: '平均薪资（千元）'}
        )
        return fig

    def plot_salary_heatmap(self, city_col='work_city', avg_col='avg_salary') -> go.Figure:
        return go.Figure()  # 占位空图

    # 5. 员工满意度
    def plot_satisfaction_bar(self, group_col='department', satisfaction_col='satisfaction') -> go.Figure:
        if group_col not in self.processed_data.columns or satisfaction_col not in self.processed_data.columns:
            return go.Figure()

        df_group = self.processed_data.groupby(group_col)[satisfaction_col].mean().reset_index()
        fig = px.bar(
            df_group,
            x=group_col,
            y=satisfaction_col,
            title='满意度对比',
            labels={group_col: '部门/职位', satisfaction_col: '满意度'}
        )
        return fig

    def plot_satisfaction_radar(self, satisfaction_dict: Dict[str, float] = None) -> go.Figure:
        if not satisfaction_dict:
            return go.Figure()

        categories = list(satisfaction_dict.keys())
        values = list(satisfaction_dict.values())
        values.append(values[0])
        categories.append(categories[0])

        fig = go.Figure(
            data=go.Scatterpolar(
                r=values,
                theta=categories,
                fill='toself',
                name='满意度雷达图'
            )
        )
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            title='满意度多维度雷达图'
        )
        return fig

    def plot_satisfaction_heatmap(self, city_col='work_city', satisfaction_col='satisfaction') -> go.Figure:
        return go.Figure()  # 占位空图

    # 6. 工作地点分布
    def plot_location_map(self, lat_col='latitude', lon_col='longitude') -> go.Figure:
        return self.plot_job_distribution_map(lat_col, lon_col)

    def plot_location_bar(self, city_col='work_city') -> go.Figure:
        return self.plot_job_distribution_bar(city_col)

    # 7. 工作量与效率
    def plot_workload_bar(self, group_col='department', workload_col='workload') -> go.Figure:
        if group_col not in self.processed_data.columns or workload_col not in self.processed_data.columns:
            return go.Figure()

        df_group = self.processed_data.groupby(group_col)[workload_col].sum().reset_index()
        fig = px.bar(
            df_group,
            x=group_col,
            y=workload_col,
            title='部门工作量对比',
            labels={group_col: '部门', workload_col: '工作量'}
        )
        return fig

    def plot_workload_line(self, time_col='date', workload_col='workload') -> go.Figure:
        if time_col not in self.processed_data.columns or workload_col not in self.processed_data.columns:
            return go.Figure()

        df_time = (
            self.processed_data
            .groupby(time_col)[workload_col]
            .sum()
            .reset_index()
            .sort_values(time_col)
        )
        fig = px.line(
            df_time,
            x=time_col,
            y=workload_col,
            title='工作量时间趋势',
            labels={time_col: '时间', workload_col: '工作量'}
        )
        return fig

    def plot_workload_heatmap(self, group_row='department', group_col='position_name', workload_col='workload') -> go.Figure:
        if any(col not in self.processed_data.columns for col in [group_row, group_col, workload_col]):
            return go.Figure()

        pivot_data = self.processed_data.pivot_table(
            index=group_row,
            columns=group_col,
            values=workload_col,
            aggfunc='sum'
        ).fillna(0)

        fig = px.imshow(
            pivot_data,
            labels=dict(color="工作量"),
            x=pivot_data.columns,
            y=pivot_data.index,
            title='工作量分布热力图'
        )
        return fig

    # 8. 总结与建议
    def plot_summary_bar(self, summary_data: Dict[str, float]) -> go.Figure:
        if not summary_data:
            return go.Figure()

        df_summary = pd.DataFrame(list(summary_data.items()), columns=['维度', '数值'])
        fig = px.bar(
            df_summary,
            x='维度',
            y='数值',
            title='关键指标总结'
        )
        return fig

    def plot_summary_radar(self, summary_data: Dict[str, float]) -> go.Figure:
        if not summary_data:
            return go.Figure()

        categories = list(summary_data.keys())
        values = list(summary_data.values())
        values.append(values[0])
        categories.append(categories[0])

        fig = go.Figure(
            data=go.Scatterpolar(
                r=values,
                theta=categories,
                fill='toself',
                name='综合指标'
            )
        )
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            title='综合指标雷达图'
        )
        return fig

    def generate_comprehensive_report(self) -> str:
        return (
            "综合报告示例：\n"
            "1. 岗位分布：上海岗位最多，占比45%。\n"
            "2. 技能需求：Python最受欢迎，占比60%。\n"
            "3. 晋升路径：从初级工程师到高级工程师平均2年。\n"
            "4. 薪资水平：平均薪资15k，最高薪资30k。\n"
            "5. 员工满意度：整体满意度评分为7.5。\n"
            "6. 工作地点：北上广深占比70%。\n"
            "7. 工作量与效率：Q2工作量高峰，工作效率整体提升10%。\n"
            "8. 建议：加强技能培训、优化薪资结构、关注晋升通道。\n"
        )


if __name__ == "__main__":
    pass