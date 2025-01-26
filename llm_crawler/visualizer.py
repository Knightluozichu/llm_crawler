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


class DataVisualizer:
    """
    数据可视化类，用于对处理后的职位数据进行分析和图表绘制。
    适配最新的数据列：position_name, company_name, salary, work_exp, education, ...
    """

    def __init__(self, data_processor):
        """
        初始化 DataVisualizer，并获取预处理后的 DataFrame。
        
        :param data_processor: 已初始化并处理过数据的 DataProcessor 实例
        """
        self.data_processor = data_processor
        self.processed_data = data_processor.get_processed_data()
        
    def generate_job_insights(self) -> Dict[str, Any]:
        """
        生成职位数据洞察，包括薪资和常见关键词等分析。
        
        :return: 包含薪资等信息的字典
        """
        insights = {}
        
        # 薪资洞察
        avg_salary = round(self.processed_data['avg_salary'].mean(), 1)
        min_salary = self.processed_data['min_salary'].min()
        max_salary = self.processed_data['max_salary'].max()
        insights['salary'] = {
            'avg': avg_salary,
            'min': min_salary,
            'max': max_salary
        }
        
        # 此处可统计常见高频词（基于 job_desc_words）
        all_words = [
            w for words_list in self.processed_data['job_desc_words'] 
            for w in words_list
        ]
        counter = Counter(all_words)
        # 取前 10 个关键词
        top_words = counter.most_common(10)
        insights['keywords'] = [word for (word, freq) in top_words]
        
        return insights
        
    def plot_salary_distribution(self) -> go.Figure:
        """
        绘制薪资分布图（直方图）。
        
        :return: Plotly Figure 对象
        """
        fig = px.histogram(
            self.processed_data,
            x='avg_salary',
            nbins=20,
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
        """
        绘制学历要求分布饼图。
        
        :return: Plotly Figure 对象
        """
        edu_map = {
            0: '不限',
            1: '大专',
            2: '本科',
            3: '硕士',
            4: '博士'
        }
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
        """
        绘制工作经验要求分布柱状图 (列: work_exp)。
        
        :return: Plotly Figure 对象
        """
        if 'work_exp' not in self.processed_data.columns:
            # 如果数据里缺少 work_exp 列，则返回空图
            return go.Figure()
        
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
        """
        绘制公司类型分布饼图。
        
        :return: Plotly Figure 对象
        """
        if 'company_type' not in self.processed_data.columns:
            return go.Figure()
        
        company_counts = self.processed_data['company_type'].value_counts()
        
        fig = px.pie(
            company_counts,
            values=company_counts.values,
            names=company_counts.index,
            title='公司类型分布'
        )
        return fig
        
    def generate_job_wordcloud(self) -> str:
        """
        生成职位描述词云，并以 Base64 编码的形式返回图像数据。
        若无职位描述或生成失败，则返回 None。
        
        :return: Base64 编码的词云图片数据（若无法生成则返回 None）
        """
        if 'job_desc_words' not in self.processed_data.columns:
            return None
        
        all_words = [
            word 
            for words_list in self.processed_data['job_desc_words'] 
            for word in words_list
        ]
        if not all_words:
            return None
            
        word_freq = Counter(all_words)
        
        try:
            # Mac 系统默认中文字体路径
            font_paths = [
                '/System/Library/Fonts/PingFang.ttc',  # PingFang
                '/System/Library/Fonts/STHeiti Light.ttc',  # Heiti
                '/System/Library/Fonts/Arial Unicode.ttf'  # Arial Unicode
            ]
            
            # 尝试可用的字体
            font_path = None
            for path in font_paths:
                if Path(path).exists():
                    font_path = path
                    break
                    
            if not font_path:
                # 若找不到可用字体，则不指定 font_path
                wc = WordCloud(width=800, height=400)
            else:
                wc = WordCloud(font_path=font_path, width=800, height=400)

            wc.generate_from_frequencies(word_freq)
            
            # 将词云转换为 Base64 图片
            img = BytesIO()
            plt.figure(figsize=(10, 5))
            plt.imshow(wc, interpolation='bilinear')
            plt.axis('off')
            plt.savefig(img, format='png', bbox_inches='tight', pad_inches=0)
            plt.close()
            img.seek(0)
            return base64.b64encode(img.getvalue()).decode()
            
        except Exception as e:
            print(f"生成词云时出错: {str(e)}")
            return None
    
    def plot_insights_summary(self, insights: Dict[str, Any]) -> (go.Figure, go.Figure):
        """
        绘制整体洞察的可视化，返回两个示例图表：
        1. 薪资区间分布 (柱状图)
        2. 高频关键词 TOP 10 (柱状图)
        
        :param insights: generate_job_insights() 方法返回的洞察数据
        :return: (fig_salary, fig_keywords) 两个 Plotly Figure 对象
        """
        # 薪资区间统计
        if 'avg_salary' not in self.processed_data.columns:
            return go.Figure(), go.Figure()
        
        bins = [0, 5, 10, 15, 20, 30, 40, 1000]  # 简化分段
        labels = ['0-5k', '5-10k', '10-15k', '15-20k', '20-30k', '30-40k', '40k+']
        salary_bins = pd.cut(
            self.processed_data['avg_salary'],
            bins=bins,
            labels=labels,
            include_lowest=True
        )
        salary_dist = salary_bins.value_counts().sort_index()
        
        fig_salary = px.bar(
            salary_dist,
            x=salary_dist.index,
            y=salary_dist.values,
            title='薪资区间分布',
            labels={'x': '平均薪资区间 (千元)', 'y': '职位数量'}
        )
        
        # 高频关键词
        keywords = insights.get('keywords', [])
        fig_keywords = go.Figure()
        if keywords:
            # 统计关键词出现次数
            word_count = Counter()
            for words_list in self.processed_data['job_desc_words']:
                for w in words_list:
                    if w in keywords:
                        word_count[w] += 1
            # 转为列表进行排序再绘制
            data = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
            x_vals = [t[0] for t in data]
            y_vals = [t[1] for t in data]
            fig_keywords = px.bar(
                x=x_vals,
                y=y_vals,
                labels={'x': '关键词', 'y': '出现次数'},
                title='高频关键词 TOP 10'
            )
        return fig_salary, fig_keywords