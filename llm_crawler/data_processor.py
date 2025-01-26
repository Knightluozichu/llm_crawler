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
        解析薪资字符串，形如 "1.5万-2万"、"2.2万-4万" 等，统一转换为 [min_k, max_k] (千元)。
        若无法识别，则返回 [0.0, 0.0]。
        
        假设:
          - "1.5万" => 15 (千)
          - "2万"   => 20 (千)
        """
        # 常见格式： X万-Y万
        pattern = r'(\d+(\.\d+)?)万-(\d+(\.\d+)?)万'
        match = re.search(pattern, salary_str)
        if match:
            min_val = float(match.group(1)) * 10
            max_val = float(match.group(3)) * 10
            return [min_val, max_val]
        
        # 若只有第一个数字后带 万，如 "2.2万-4"
        pattern2 = r'(\d+(\.\d+)?)万-(\d+(\.\d+)?)'
        match2 = re.search(pattern2, salary_str)
        if match2:
            min_val = float(match2.group(1)) * 10
            max_val = float(match2.group(3)) * 10
            return [min_val, max_val]
        
        return [0.0, 0.0]
        
    def _parse_experience(self, exp_str: str) -> float:
        """
        解析工作经验字符串：
        - 若包含 '不限' 或 '无经验' 等，则视作 0 年
        - 若能提取数字，则取第一个出现的数字
        - 否则返回 0.0
        
        :param exp_str: 如 "3年", "经验不限", "无经验", ...
        :return: 工作年限的数值
        """
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