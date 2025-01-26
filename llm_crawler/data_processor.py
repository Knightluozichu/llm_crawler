import pandas as pd
from pathlib import Path
from typing import Dict, List
import re
import numpy as np
from collections import Counter
import jieba

class DataProcessor:
    def __init__(self, data_path: Path):
        self.raw_data = self._load_data(data_path)
        self.processed_data = self._process_data()
        
    def _load_data(self, data_path: Path) -> pd.DataFrame:
        """加载原始数据"""
        df = pd.read_csv(data_path)
        
        # 数据清洗
        df = df.dropna(subset=['job_name', 'company_name', 'salary'])
        df = df.drop_duplicates(subset=['job_name', 'company_name'])
        
        return df
        
    def _process_data(self) -> pd.DataFrame:
        """处理原始数据"""
        df = self.raw_data.copy()
        
        # 处理薪资
        df[['min_salary', 'max_salary']] = df['salary'].apply(
            self._parse_salary
        ).apply(pd.Series)
        df['avg_salary'] = (df['min_salary'] + df['max_salary']) / 2
        
        # 处理工作经验
        df['experience'] = df['experience'].apply(self._parse_experience)
        
        # 处理学历
        df['education'] = df['education'].apply(self._parse_education)
        
        # 处理公司类型
        df['company_type'] = df['company_type'].fillna('未知')
        
        # 处理职位描述
        df['job_desc_words'] = df['job_desc'].apply(self._extract_keywords)
        
        # 处理技能要求
        df['skill_words'] = df['skills'].apply(self._extract_skills)
        
        # 处理福利标签
        df['welfare_tags'] = df['welfare'].apply(self._parse_welfare_tags)
        
        return df
        
    def get_processed_data(self) -> pd.DataFrame:
        """获取处理后的数据"""
        return self.processed_data
        
    def filter_data(self, filters: Dict) -> pd.DataFrame:
        """根据筛选条件过滤数据"""
        df = self.processed_data.copy()
        
        # 薪资筛选
        df = df[
            (df['avg_salary'] >= filters['salary_range'][0]) &
            (df['avg_salary'] <= filters['salary_range'][1])
        ]
        
        # 经验筛选
        df = df[df['experience'] <= filters['experience']]
        
        # 学历筛选
        df = df[df['education'] >= filters['education']]
        
        # 公司类型筛选
        if filters['company_type']:
            df = df[df['company_type'].isin(filters['company_type'])]
            
        # 福利标签筛选
        if filters['welfare_tags']:
            df = df[
                df['welfare_tags'].apply(
                    lambda tags: any(tag in tags for tag in filters['welfare_tags'])
                )
            ]
            
        return df
        
    def _parse_salary(self, salary_str: str) -> List[float]:
        """解析薪资字符串"""
        pattern = r'(\d+\.?\d*)-(\d+\.?\d*)千/月'
        match = re.search(pattern, salary_str)
        if match:
            return [float(match.group(1)), float(match.group(2))]
        return [0.0, 0.0]
        
    def _parse_experience(self, exp_str: str) -> float:
        """解析工作经验"""
        if '不限' in exp_str:
            return 0.0
        pattern = r'(\d+\.?\d*)'
        match = re.search(pattern, exp_str)
        if match:
            return float(match.group(1))
        return 0.0
        
    def _parse_education(self, edu_str: str) -> int:
        """解析学历要求"""
        edu_map = {
            '不限': 0,
            '大专': 1,
            '本科': 2,
            '硕士': 3,
            '博士': 4
        }
        for key, value in edu_map.items():
            if key in edu_str:
                return value
        return 0
        
    def _extract_keywords(self, text: str) -> List[str]:
        """提取职位描述关键词"""
        if pd.isna(text):
            return []
        words = jieba.lcut(text)
        return [word for word in words if len(word) > 1]
        
    def _extract_skills(self, skills_str: str) -> List[str]:
        """提取技能关键词"""
        if pd.isna(skills_str):
            return []
        skills = re.split(r'[、,，]', skills_str)
        return [skill.strip() for skill in skills if skill.strip()]
        
    def _parse_welfare_tags(self, welfare_str: str) -> List[str]:
        """解析福利标签"""
        if pd.isna(welfare_str):
            return []
        tags = re.split(r'[、,，]', welfare_str)
        return [tag.strip() for tag in tags if tag.strip()]
