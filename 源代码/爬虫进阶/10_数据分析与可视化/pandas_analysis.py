# -*- coding: utf-8 -*-
# @Desc: pandas 数据分析工具

import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger


class DataFrameAnalyzer:
    """DataFrame 数据分析器"""

    def __init__(self, data: List[Dict[str, Any]]):
        """
        初始化分析器

        Args:
            data: 字典列表形式的数据
        """
        self.df = pd.DataFrame(data)
        logger.info(f"加载数据: {len(self.df)} 行, {len(self.df.columns)} 列")

    @classmethod
    def from_csv(cls, file_path: str, **kwargs) -> 'DataFrameAnalyzer':
        """从 CSV 文件创建分析器"""
        df = pd.read_csv(file_path, **kwargs)
        return cls(df.to_dict('records'))

    @classmethod
    def from_json(cls, file_path: str, **kwargs) -> 'DataFrameAnalyzer':
        """从 JSON 文件创建分析器"""
        df = pd.read_json(file_path, **kwargs)
        return cls(df.to_dict('records'))

    def info(self) -> Dict[str, Any]:
        """获取数据集基本信息"""
        return {
            "rows": len(self.df),
            "columns": len(self.df.columns),
            "column_names": self.df.columns.tolist(),
            "dtypes": self.df.dtypes.to_dict(),
            "memory_usage": self.df.memory_usage(deep=True).sum(),
            "null_counts": self.df.isnull().sum().to_dict(),
        }

    def describe(self, include: str = 'all') -> pd.DataFrame:
        """获取描述性统计"""
        return self.df.describe(include=include)

    def value_counts(self, column: str, top_n: int = 10) -> pd.Series:
        """统计某列的值分布"""
        return self.df[column].value_counts().head(top_n)

    def group_by_count(self, group_col: str) -> pd.Series:
        """按列分组计数"""
        return self.df.groupby(group_col).size().sort_values(ascending=False)

    def group_by_sum(self, group_col: str, value_col: str) -> pd.Series:
        """按列分组求和"""
        return self.df.groupby(group_col)[value_col].sum().sort_values(ascending=False)

    def group_by_mean(self, group_col: str, value_col: str) -> pd.Series:
        """按列分组求均值"""
        return self.df.groupby(group_col)[value_col].mean().sort_values(ascending=False)

    def group_by_agg(
        self,
        group_col: str,
        agg_dict: Dict[str, List[str]]
    ) -> pd.DataFrame:
        """
        按列分组并进行多种聚合

        Args:
            group_col: 分组列
            agg_dict: 聚合字典，如 {'views': ['sum', 'mean'], 'likes': ['max', 'min']}
        """
        return self.df.groupby(group_col).agg(agg_dict)

    def pivot_table(
        self,
        values: str,
        index: str,
        columns: str,
        aggfunc: str = 'sum',
        fill_value: Any = 0
    ) -> pd.DataFrame:
        """创建数据透视表"""
        return pd.pivot_table(
            self.df,
            values=values,
            index=index,
            columns=columns,
            aggfunc=aggfunc,
            fill_value=fill_value
        )

    def correlation(self, columns: List[str] = None) -> pd.DataFrame:
        """计算相关系数矩阵"""
        if columns:
            return self.df[columns].corr()
        return self.df.select_dtypes(include=['number']).corr()

    def filter(self, condition: str) -> 'DataFrameAnalyzer':
        """
        根据条件筛选数据

        Args:
            condition: 查询条件，如 "views > 1000 and category == '技术'"
        """
        filtered_df = self.df.query(condition)
        return DataFrameAnalyzer(filtered_df.to_dict('records'))

    def sort(self, by: str, ascending: bool = False) -> 'DataFrameAnalyzer':
        """排序"""
        sorted_df = self.df.sort_values(by=by, ascending=ascending)
        return DataFrameAnalyzer(sorted_df.to_dict('records'))

    def top_n(self, n: int, by: str) -> pd.DataFrame:
        """获取 Top N"""
        return self.df.nlargest(n, by)

    def bottom_n(self, n: int, by: str) -> pd.DataFrame:
        """获取 Bottom N"""
        return self.df.nsmallest(n, by)


class TimeSeriesAnalyzer:
    """时间序列分析器"""

    def __init__(self, df: pd.DataFrame, date_col: str):
        """
        初始化时间序列分析器

        Args:
            df: 数据框
            date_col: 日期列名
        """
        self.df = df.copy()
        self.date_col = date_col

        # 转换日期列
        self.df[date_col] = pd.to_datetime(self.df[date_col], errors='coerce')
        self.df = self.df.dropna(subset=[date_col])
        self.df = self.df.set_index(date_col)

        logger.info(f"时间序列分析器初始化: {len(self.df)} 条记录")

    def resample(
        self,
        freq: str,
        value_col: str,
        agg_func: str = 'sum'
    ) -> pd.DataFrame:
        """
        重采样

        Args:
            freq: 频率，如 'D'(天), 'W'(周), 'M'(月)
            value_col: 值列
            agg_func: 聚合函数
        """
        return self.df.resample(freq)[value_col].agg(agg_func)

    def rolling(
        self,
        window: int,
        value_col: str,
        agg_func: str = 'mean'
    ) -> pd.Series:
        """
        滚动窗口统计

        Args:
            window: 窗口大小
            value_col: 值列
            agg_func: 聚合函数
        """
        return getattr(self.df[value_col].rolling(window=window), agg_func)()

    def growth_rate(self, value_col: str, periods: int = 1) -> pd.Series:
        """
        计算增长率

        Args:
            value_col: 值列
            periods: 周期数
        """
        return self.df[value_col].pct_change(periods=periods) * 100

    def trend_analysis(self, value_col: str) -> Dict[str, Any]:
        """
        趋势分析

        Returns:
            包含趋势统计信息的字典
        """
        series = self.df[value_col]
        growth = series.pct_change().dropna()

        return {
            "start_value": series.iloc[0],
            "end_value": series.iloc[-1],
            "total_change": series.iloc[-1] - series.iloc[0],
            "total_change_pct": (series.iloc[-1] - series.iloc[0]) / series.iloc[0] * 100,
            "avg_growth_rate": growth.mean() * 100,
            "max_growth_rate": growth.max() * 100,
            "min_growth_rate": growth.min() * 100,
            "positive_periods": (growth > 0).sum(),
            "negative_periods": (growth < 0).sum(),
        }

    def seasonal_decompose(
        self,
        value_col: str,
        period: int = 7
    ) -> Dict[str, pd.Series]:
        """
        季节性分解（简化版）

        Args:
            value_col: 值列
            period: 周期
        """
        series = self.df[value_col]

        # 移动平均作为趋势
        trend = series.rolling(window=period, center=True).mean()

        # 去趋势
        detrended = series - trend

        # 季节性（按周期位置平均）
        seasonal = detrended.groupby(
            detrended.index.dayofweek
        ).transform('mean')

        # 残差
        residual = series - trend - seasonal

        return {
            "original": series,
            "trend": trend,
            "seasonal": seasonal,
            "residual": residual
        }


class StatisticsCalculator:
    """统计计算器"""

    @staticmethod
    def percentile(series: pd.Series, q: float) -> float:
        """计算分位数"""
        return series.quantile(q)

    @staticmethod
    def iqr(series: pd.Series) -> float:
        """计算四分位距"""
        return series.quantile(0.75) - series.quantile(0.25)

    @staticmethod
    def outliers(series: pd.Series, method: str = 'iqr') -> pd.Series:
        """
        检测异常值

        Args:
            series: 数据序列
            method: 检测方法 ('iqr' 或 'zscore')

        Returns:
            布尔序列，True 表示异常值
        """
        if method == 'iqr':
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            return (series < lower) | (series > upper)
        elif method == 'zscore':
            z_scores = (series - series.mean()) / series.std()
            return abs(z_scores) > 3
        else:
            raise ValueError(f"Unknown method: {method}")

    @staticmethod
    def distribution_stats(series: pd.Series) -> Dict[str, float]:
        """计算分布统计量"""
        return {
            "count": series.count(),
            "mean": series.mean(),
            "std": series.std(),
            "min": series.min(),
            "q25": series.quantile(0.25),
            "median": series.median(),
            "q75": series.quantile(0.75),
            "max": series.max(),
            "skewness": series.skew(),
            "kurtosis": series.kurtosis(),
        }


def demo():
    """演示 pandas 数据分析功能"""
    print("=" * 50)
    print("pandas 数据分析演示")
    print("=" * 50)

    # 模拟数据
    data = [
        {"title": "Python入门", "category": "技术", "views": 15000, "likes": 320, "date": "2024-01-15"},
        {"title": "爬虫教程", "category": "技术", "views": 12000, "likes": 280, "date": "2024-01-16"},
        {"title": "美食分享", "category": "生活", "views": 8000, "likes": 450, "date": "2024-01-17"},
        {"title": "数据分析", "category": "技术", "views": 18000, "likes": 520, "date": "2024-01-18"},
        {"title": "旅行日记", "category": "生活", "views": 10000, "likes": 380, "date": "2024-01-19"},
        {"title": "机器学习", "category": "技术", "views": 20000, "likes": 600, "date": "2024-01-20"},
    ]

    # 创建分析器
    analyzer = DataFrameAnalyzer(data)

    # 基本信息
    print("\n1. 数据集信息:")
    info = analyzer.info()
    print(f"   行数: {info['rows']}, 列数: {info['columns']}")
    print(f"   列名: {info['column_names']}")

    # 描述性统计
    print("\n2. 描述性统计:")
    print(analyzer.describe())

    # 分组统计
    print("\n3. 按分类分组统计:")
    print(analyzer.group_by_agg('category', {'views': ['sum', 'mean'], 'likes': ['sum', 'mean']}))

    # Top N
    print("\n4. 浏览量 Top 3:")
    print(analyzer.top_n(3, 'views'))

    # 分布统计
    print("\n5. 浏览量分布统计:")
    stats = StatisticsCalculator.distribution_stats(analyzer.df['views'])
    for key, value in stats.items():
        print(f"   {key}: {value:.2f}")

    print("\n" + "=" * 50)
    print("演示完成")
    print("=" * 50)


if __name__ == "__main__":
    demo()
