import pandas as pd
from pathlib import Path
from typing import Dict, List
import re
import jieba


class DataProcessor:
    """
    数据处理类，用于加载、清洗并预处理招聘信息数据。
    适配最新 CSV 格式（列示例：position_name, company_name, salary, work_city, work_exp, 等）。
    """

    def __init__(self, data_path: Path):
        """
        初始化 DataProcessor 并执行数据加载与预处理。
        
        :param data_path: 数据文件的路径
        """
        self.raw_data = self._load_data(data_path)
        self.processed_data = self._process_data()
        
    def _load_data(self, data_path: Path) -> pd.DataFrame:
        """
        加载原始数据并执行基础清洗操作。
        - 删除缺失 position_name、company_name、salary 的行
        - 删除重复的 (position_name, company_name) 组合
        
        :param data_path: 数据文件的路径
        :return: 清洗后的 DataFrame
        """
        df = pd.read_csv(data_path)
        
        # 基础清洗
        df = df.dropna(subset=['position_name', 'company_name', 'salary'])
        df = df.drop_duplicates(subset=['position_name', 'company_name'])
        
        return df
        
    def _process_data(self) -> pd.DataFrame:
        """
        进一步处理数据，包括：
        - 薪资解析：提取最小、最大、平均薪资（单位：千元）
        - 工作经验解析
        - 学历解析
        - 公司类型空值填充
        - 职位描述分词（job_summary -> job_desc_words）
        - 福利拆分（welfare -> welfare_tags）
        
        :return: 处理完成的 DataFrame
        """
        df = self.raw_data.copy()
        
        df ['work_exp'] = df['work_exp'].fillna('经验不限')
        df['education'] = df['education'].fillna('不限')
        
        # 如果没有company_type'列，填充为'未知'
        if 'company_type' not in df.columns:
            df['company_type'] = '未知'
        
        # 处理薪资
        df[['min_salary', 'max_salary']] = df['salary'].apply(
            self._parse_salary
        ).apply(pd.Series)
        df['avg_salary'] = (df['min_salary'] + df['max_salary']) / 2
        
        # 处理工作经验 (列名 work_exp)
        df['work_exp'] = df['work_exp'].apply(self._parse_experience)
        
        # 处理学历 (education)
        df['education'] = df['education'].apply(self._parse_education)
        
        # 处理公司类型
        df['company_type'] = df['company_type'].fillna('未知')
        
        # 处理职位描述 (job_summary -> 分词)
        df['job_desc_words'] = df['job_summary'].apply(self._extract_keywords)
        
        # 处理福利 (welfare -> welfare_tags)
        df['welfare_tags'] = df['welfare'].apply(self._parse_welfare_tags)
        
        return df
        
    def get_processed_data(self) -> pd.DataFrame:
        """
        获取预处理完成的数据。
        
        :return: 处理后的 DataFrame
        """
        return self.processed_data
        
    def filter_data(self, filters: Dict) -> pd.DataFrame:
        """
        根据筛选条件过滤数据。
        筛选条件包括：
          - salary_range: (min, max) 薪资区间 (千元)
          - work_exp: 最大年限
          - education: 最低学历数值编码
          - company_type: 公司类型列表
          - welfare_tags: 至少包含任意一个的福利标签列表
        
        :param filters: 包含各项筛选条件的字典
        :return: 过滤后的 DataFrame
        """
        df = self.processed_data.copy()
        
        # 薪资筛选
        df = df[
            (df['avg_salary'] >= filters['salary_range'][0]) &
            (df['avg_salary'] <= filters['salary_range'][1])
        ]
        
        # 经验筛选
        df = df[df['work_exp'] <= filters['work_exp']]
        
        # 学历筛选
        df = df[df['education'] >= filters['education']]
        
        # 公司类型筛选
        if filters['company_type']:
            df = df[df['company_type'].isin(filters['company_type'])]
            
        # 福利标签筛选（只要岗位包含任意一个所选标签，即视为符合）
        if filters['welfare_tags']:
            df = df[
                df['welfare_tags'].apply(
                    lambda tags: any(tag in tags for tag in filters['welfare_tags'])
                )
            ]
            
        return df
        
    def _parse_salary(self, salary_str: str) -> List[float]:
        """
        解析薪资字符串，返回 [min_k, max_k] (千元)
        """
        # 检查是否包含薪资次数信息
        salary_count_pattern = r'(\d+)薪'
        salary_count_match = re.search(salary_count_pattern, salary_str)
        if salary_count_match and 'salary_count' not in self.raw_data.columns:
            self.raw_data['salary_count'] = 12  

        if salary_count_match:
            salary_count = int(salary_count_match.group(1))
            current_index = self.raw_data[self.raw_data['salary'] == salary_str].index[-1]
            self.raw_data.loc[current_index, 'salary_count'] = salary_count

        # 处理面议情况
        if any(kw in salary_str for kw in ['面议', '面谈', '待定']):
            return [0.1, 0.1]

        # 处理 K 单位的薪资格式 (支持 15K-25K 和 15-25K)
        k_pattern = r'(\d+(\.\d+)?)[Kk]?-(\d+(\.\d+)?)[Kk]'
        k_match = re.search(k_pattern, salary_str)
        if k_match and ('K' in salary_str.upper() or 'k' in salary_str):
            min_val = float(k_match.group(1))
            max_val = float(k_match.group(3))
            return [min_val, max_val]

        # 处理万为单位的薪资 (X万-Y万)
        pattern = r'(\d+(\.\d+)?)万-(\d+(\.\d+)?)万'
        match = re.search(pattern, salary_str)
        if match:
            min_val = float(match.group(1)) * 10
            max_val = float(match.group(3)) * 10
            return [min_val, max_val]

        # 处理首个数字带万的情况 (2.2万-4)
        pattern2 = r'(\d+(\.\d+)?)万-(\d+(\.\d+)?)'
        match2 = re.search(pattern2, salary_str)
        if match2:
            min_val = float(match2.group(1)) * 10
            max_val = float(match2.group(3))
            return [min_val, max_val]

        # 处理日薪 (150-200元/天)
        day_pattern = r'(\d+)-(\d+)元/天'
        day_match = re.search(day_pattern, salary_str)
        if day_match:
            min_day = float(day_match.group(1))
            max_day = float(day_match.group(2))
            # 假设每月工作22天，转换为月薪(千元)
            return [min_day * 22 / 1000, max_day * 22 / 1000]

        # 如果无法匹配任何格式，返回默认值
        return [0.1, 0.1]
    
    
    def _parse_experience(self, exp_str: str) -> float:
        """
        解析工作经验字符串：
        - 若包含 '不限' 或 '无经验' 等，则视作 0 年
        - 若能提取数字，则取第一个出现的数字
        - 否则返回 0.0
        
        :param exp_str: 如 "3年", "经验不限", "无经验", ...
        :return: 工作年限的数值
        """
        # if pd.isna(exp_str):
        #     return 0.0
        # exp_str = str(exp_str)
        if any(kw in exp_str for kw in ['不限', '无经验']):
            return 0.0
        pattern = r'(\d+(\.\d+)?)'
        match = re.search(pattern, exp_str)
        if match:
            return float(match.group(1))
        return 0.0
        
    def _parse_education(self, edu_str: str) -> int:
        """
        解析学历要求字符串，并转换为数值编码：
          '不限' -> 0
          '大专' -> 1
          '本科' -> 2
          '硕士' -> 3
          '博士' -> 4
        默认为 0（不限）
        
        :param edu_str: 学历描述字符串
        :return: 对应的数值编码
        """
        # if pd.isna(edu_str):
        #     return 0
        # edu_str = str(edu_str)
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
        """
        对职位描述 (job_summary) 进行分词，提取长度大于1的切词结果。
        
        :param text: 职位描述文本
        :return: 分词结果列表
        """
        if pd.isna(text):
            return []
        words = jieba.lcut(text)
        return [word.strip() for word in words if len(word.strip()) > 1]
        
    def _parse_welfare_tags(self, welfare_str: str) -> List[str]:
        """
        解析福利标签（按逗号或顿号分隔）。
        
        :param welfare_str: 福利描述字符串
        :return: 福利标签列表
        """
        if pd.isna(welfare_str):
            return []
        tags = re.split(r'[、,，]', welfare_str)
        return [tag.strip() for tag in tags if tag.strip()]