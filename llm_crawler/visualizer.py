import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from typing import Dict, List
from collections import Counter

class DataVisualizer:
    def __init__(self, data_processor):
        self.data_processor = data_processor
        self.processed_data = data_processor.get_processed_data()
        
    def generate_job_insights(self) -> Dict:
        """生成职位数据洞察"""
        insights = {}
        
        # 薪资洞察
        insights['salary'] = {
            'avg': round(self.processed_data['avg_salary'].mean(), 1),
            'min': self.processed_data['min_salary'].min(),
            'max': self.processed_data['max_salary'].max()
        }
        
        # 技能洞察
        all_skills = [
            skill for skills in self.processed_data['skill_words'] 
            for skill in skills
        ]
        skill_counter = Counter(all_skills)
        insights['skills'] = [
            skill[0] for skill in skill_counter.most_common(10)
        ]
        
        return insights
        
    def plot_salary_distribution(self):
        """绘制薪资分布图"""
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
        
    def plot_education_pie(self):
        """绘制学历分布饼图"""
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
        
    def plot_experience_bar(self):
        """绘制工作经验柱状图"""
        exp_counts = self.processed_data['experience'].value_counts().sort_index()
        
        fig = px.bar(
            exp_counts,
            x=exp_counts.index,
            y=exp_counts.values,
            labels={'x': '工作经验 (年)', 'y': '职位数量'},
            title='工作经验要求分布'
        )
        return fig
        
    def plot_company_type_pie(self):
        """绘制公司类型饼图"""
        company_counts = self.processed_data['company_type'].value_counts()
        
        fig = px.pie(
            company_counts,
            values=company_counts.values,
            names=company_counts.index,
            title='公司类型分布'
        )
        return fig
        
    def generate_job_wordcloud(self):
        """生成职位描述词云"""
        all_words = [
            word for words in self.processed_data['job_desc_words'] 
            for word in words
        ]
        if not all_words:
            return None
            
        word_freq = Counter(all_words)
        wc = WordCloud(
            font_path='simhei.ttf',
            width=800,
            height=400,
            background_color='white'
        ).generate_from_frequencies(word_freq)
        
        # 将词云转换为base64图片
        img = BytesIO()
        plt.figure(figsize=(10, 5))
        plt.imshow(wc, interpolation='bilinear')
        plt.axis('off')
        plt.savefig(img, format='png', bbox_inches='tight', pad_inches=0)
        plt.close()
        img.seek(0)
        return base64.b64encode(img.getvalue()).decode()
