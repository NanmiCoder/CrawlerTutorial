# -*- coding: utf-8 -*-
# @Desc: 数据可视化工具

import os
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger

# 可选依赖
try:
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
    matplotlib.rcParams['axes.unicode_minus'] = False
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    logger.warning("matplotlib 未安装")

try:
    from pyecharts.charts import Bar, Line, Pie, Scatter, WordCloud as PyWordCloud
    from pyecharts import options as opts
    from pyecharts.globals import ThemeType
    HAS_PYECHARTS = True
except ImportError:
    HAS_PYECHARTS = False
    logger.warning("pyecharts 未安装")


class MatplotlibCharts:
    """Matplotlib 静态图表生成器"""

    def __init__(self, figsize: Tuple[int, int] = (10, 6), dpi: int = 150):
        """
        初始化

        Args:
            figsize: 图表大小 (宽, 高)
            dpi: 分辨率
        """
        if not HAS_MATPLOTLIB:
            raise ImportError("请安装 matplotlib: pip install matplotlib")

        self.figsize = figsize
        self.dpi = dpi

    def line_chart(
        self,
        x_data: List,
        y_data: List,
        title: str,
        xlabel: str,
        ylabel: str,
        output_path: str,
        color: str = 'steelblue',
        marker: str = 'o'
    ) -> str:
        """绘制折线图"""
        plt.figure(figsize=self.figsize)
        plt.plot(x_data, y_data, marker=marker, linewidth=2, markersize=6, color=color)
        plt.title(title, fontsize=14)
        plt.xlabel(xlabel, fontsize=12)
        plt.ylabel(ylabel, fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_path, dpi=self.dpi)
        plt.close()
        logger.info(f"折线图已保存: {output_path}")
        return output_path

    def multi_line_chart(
        self,
        x_data: List,
        y_data_dict: Dict[str, List],
        title: str,
        xlabel: str,
        ylabel: str,
        output_path: str
    ) -> str:
        """绘制多条折线图"""
        plt.figure(figsize=self.figsize)

        for label, y_data in y_data_dict.items():
            plt.plot(x_data, y_data, marker='o', label=label, linewidth=2)

        plt.title(title, fontsize=14)
        plt.xlabel(xlabel, fontsize=12)
        plt.ylabel(ylabel, fontsize=12)
        plt.legend(loc='best')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_path, dpi=self.dpi)
        plt.close()
        logger.info(f"多折线图已保存: {output_path}")
        return output_path

    def bar_chart(
        self,
        categories: List[str],
        values: List,
        title: str,
        xlabel: str,
        ylabel: str,
        output_path: str,
        horizontal: bool = False,
        color: str = 'steelblue'
    ) -> str:
        """绘制柱状图"""
        plt.figure(figsize=self.figsize)

        if horizontal:
            plt.barh(categories, values, color=color)
            plt.xlabel(ylabel)
            plt.ylabel(xlabel)
        else:
            plt.bar(categories, values, color=color)
            plt.xlabel(xlabel)
            plt.ylabel(ylabel)

        plt.title(title, fontsize=14)
        plt.tight_layout()
        plt.savefig(output_path, dpi=self.dpi)
        plt.close()
        logger.info(f"柱状图已保存: {output_path}")
        return output_path

    def grouped_bar_chart(
        self,
        categories: List[str],
        data_dict: Dict[str, List],
        title: str,
        xlabel: str,
        ylabel: str,
        output_path: str
    ) -> str:
        """绘制分组柱状图"""
        import numpy as np

        plt.figure(figsize=self.figsize)

        x = np.arange(len(categories))
        width = 0.8 / len(data_dict)

        for i, (label, values) in enumerate(data_dict.items()):
            offset = (i - len(data_dict) / 2 + 0.5) * width
            plt.bar(x + offset, values, width, label=label)

        plt.xlabel(xlabel, fontsize=12)
        plt.ylabel(ylabel, fontsize=12)
        plt.title(title, fontsize=14)
        plt.xticks(x, categories)
        plt.legend()
        plt.tight_layout()
        plt.savefig(output_path, dpi=self.dpi)
        plt.close()
        logger.info(f"分组柱状图已保存: {output_path}")
        return output_path

    def pie_chart(
        self,
        labels: List[str],
        sizes: List,
        title: str,
        output_path: str,
        explode_max: bool = True
    ) -> str:
        """绘制饼图"""
        plt.figure(figsize=(10, 8))

        explode = None
        if explode_max:
            max_idx = sizes.index(max(sizes))
            explode = [0.05 if i == max_idx else 0 for i in range(len(sizes))]

        plt.pie(
            sizes,
            labels=labels,
            explode=explode,
            autopct='%1.1f%%',
            startangle=90,
            colors=plt.cm.Set3.colors[:len(labels)]
        )
        plt.title(title, fontsize=14)
        plt.axis('equal')
        plt.tight_layout()
        plt.savefig(output_path, dpi=self.dpi)
        plt.close()
        logger.info(f"饼图已保存: {output_path}")
        return output_path

    def scatter_chart(
        self,
        x_data: List,
        y_data: List,
        title: str,
        xlabel: str,
        ylabel: str,
        output_path: str,
        color: str = 'steelblue',
        alpha: float = 0.6
    ) -> str:
        """绘制散点图"""
        plt.figure(figsize=self.figsize)
        plt.scatter(x_data, y_data, c=color, alpha=alpha, s=50)
        plt.title(title, fontsize=14)
        plt.xlabel(xlabel, fontsize=12)
        plt.ylabel(ylabel, fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_path, dpi=self.dpi)
        plt.close()
        logger.info(f"散点图已保存: {output_path}")
        return output_path

    def histogram(
        self,
        data: List,
        title: str,
        xlabel: str,
        ylabel: str,
        output_path: str,
        bins: int = 20,
        color: str = 'steelblue'
    ) -> str:
        """绘制直方图"""
        plt.figure(figsize=self.figsize)
        plt.hist(data, bins=bins, color=color, edgecolor='white', alpha=0.7)
        plt.title(title, fontsize=14)
        plt.xlabel(xlabel, fontsize=12)
        plt.ylabel(ylabel, fontsize=12)
        plt.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_path, dpi=self.dpi)
        plt.close()
        logger.info(f"直方图已保存: {output_path}")
        return output_path


class PyechartsCharts:
    """Pyecharts 交互式图表生成器"""

    def __init__(self, theme: str = 'light'):
        """
        初始化

        Args:
            theme: 主题名称
        """
        if not HAS_PYECHARTS:
            raise ImportError("请安装 pyecharts: pip install pyecharts")

        self.theme = getattr(ThemeType, theme.upper(), ThemeType.LIGHT)

    def bar_chart(
        self,
        categories: List[str],
        values: List,
        title: str,
        output_path: str,
        series_name: str = "数量"
    ) -> str:
        """创建交互式柱状图"""
        bar = (
            Bar(init_opts=opts.InitOpts(theme=self.theme))
            .add_xaxis(categories)
            .add_yaxis(series_name, values)
            .set_global_opts(
                title_opts=opts.TitleOpts(title=title),
                toolbox_opts=opts.ToolboxOpts(is_show=True),
                datazoom_opts=opts.DataZoomOpts(is_show=True)
            )
        )
        bar.render(output_path)
        logger.info(f"交互式柱状图已保存: {output_path}")
        return output_path

    def stacked_bar_chart(
        self,
        categories: List[str],
        data_dict: Dict[str, List],
        title: str,
        output_path: str
    ) -> str:
        """创建堆叠柱状图"""
        bar = Bar(init_opts=opts.InitOpts(theme=self.theme))
        bar.add_xaxis(categories)

        for name, values in data_dict.items():
            bar.add_yaxis(name, values, stack="stack1")

        bar.set_global_opts(
            title_opts=opts.TitleOpts(title=title),
            toolbox_opts=opts.ToolboxOpts(is_show=True),
            legend_opts=opts.LegendOpts(is_show=True)
        )
        bar.render(output_path)
        logger.info(f"堆叠柱状图已保存: {output_path}")
        return output_path

    def line_chart(
        self,
        x_data: List,
        y_data_dict: Dict[str, List],
        title: str,
        output_path: str
    ) -> str:
        """创建交互式折线图"""
        line = Line(init_opts=opts.InitOpts(theme=self.theme))
        line.add_xaxis(x_data)

        for name, y_data in y_data_dict.items():
            line.add_yaxis(
                name,
                y_data,
                is_smooth=True,
                markpoint_opts=opts.MarkPointOpts(
                    data=[
                        opts.MarkPointItem(type_="max", name="最大值"),
                        opts.MarkPointItem(type_="min", name="最小值"),
                    ]
                ),
                markline_opts=opts.MarkLineOpts(
                    data=[opts.MarkLineItem(type_="average", name="平均值")]
                )
            )

        line.set_global_opts(
            title_opts=opts.TitleOpts(title=title),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
            toolbox_opts=opts.ToolboxOpts(is_show=True),
            legend_opts=opts.LegendOpts(is_show=True)
        )
        line.render(output_path)
        logger.info(f"交互式折线图已保存: {output_path}")
        return output_path

    def pie_chart(
        self,
        data: List[Tuple[str, int]],
        title: str,
        output_path: str,
        rose_type: str = None
    ) -> str:
        """
        创建交互式饼图

        Args:
            data: [(名称, 数值), ...] 列表
            title: 标题
            output_path: 输出路径
            rose_type: 玫瑰图类型 ('radius' 或 'area')
        """
        pie = Pie(init_opts=opts.InitOpts(theme=self.theme))

        if rose_type:
            pie.add(
                "",
                data,
                radius=["30%", "70%"],
                rosetype=rose_type
            )
        else:
            pie.add("", data, radius=["30%", "70%"])

        pie.set_global_opts(
            title_opts=opts.TitleOpts(title=title),
            legend_opts=opts.LegendOpts(
                orient="vertical",
                pos_top="15%",
                pos_left="2%"
            )
        )
        pie.set_series_opts(
            label_opts=opts.LabelOpts(formatter="{b}: {d}%")
        )
        pie.render(output_path)
        logger.info(f"交互式饼图已保存: {output_path}")
        return output_path

    def scatter_chart(
        self,
        data: List[Tuple[float, float]],
        title: str,
        output_path: str,
        series_name: str = "数据"
    ) -> str:
        """创建交互式散点图"""
        scatter = (
            Scatter(init_opts=opts.InitOpts(theme=self.theme))
            .add_xaxis([d[0] for d in data])
            .add_yaxis(series_name, [d[1] for d in data])
            .set_global_opts(
                title_opts=opts.TitleOpts(title=title),
                toolbox_opts=opts.ToolboxOpts(is_show=True),
                xaxis_opts=opts.AxisOpts(type_="value"),
            )
        )
        scatter.render(output_path)
        logger.info(f"交互式散点图已保存: {output_path}")
        return output_path

    def wordcloud_chart(
        self,
        words: List[Tuple[str, int]],
        title: str,
        output_path: str,
        shape: str = "circle"
    ) -> str:
        """
        创建交互式词云

        Args:
            words: [(词语, 频次), ...] 列表
            title: 标题
            output_path: 输出路径
            shape: 形状 ('circle', 'cardioid', 'diamond', 'triangle-forward', 'triangle', 'pentagon', 'star')
        """
        wc = (
            PyWordCloud(init_opts=opts.InitOpts(theme=self.theme))
            .add(
                "",
                words,
                word_size_range=[20, 100],
                shape=shape
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(title=title),
                toolbox_opts=opts.ToolboxOpts(is_show=True)
            )
        )
        wc.render(output_path)
        logger.info(f"交互式词云已保存: {output_path}")
        return output_path


class ChartFactory:
    """图表工厂类"""

    def __init__(self, output_dir: str = "./charts"):
        """
        初始化

        Args:
            output_dir: 输出目录
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        self.matplotlib = MatplotlibCharts() if HAS_MATPLOTLIB else None
        self.pyecharts = PyechartsCharts() if HAS_PYECHARTS else None

    def get_output_path(self, filename: str) -> str:
        """获取输出路径"""
        return os.path.join(self.output_dir, filename)

    def create_bar(
        self,
        categories: List[str],
        values: List,
        title: str,
        filename: str,
        chart_type: str = 'matplotlib'
    ) -> str:
        """创建柱状图"""
        output_path = self.get_output_path(filename)

        if chart_type == 'matplotlib' and self.matplotlib:
            return self.matplotlib.bar_chart(
                categories, values, title, "分类", "数值", output_path
            )
        elif chart_type == 'pyecharts' and self.pyecharts:
            return self.pyecharts.bar_chart(categories, values, title, output_path)
        else:
            raise ValueError(f"Chart type '{chart_type}' not available")

    def create_line(
        self,
        x_data: List,
        y_data_dict: Dict[str, List],
        title: str,
        filename: str,
        chart_type: str = 'matplotlib'
    ) -> str:
        """创建折线图"""
        output_path = self.get_output_path(filename)

        if chart_type == 'matplotlib' and self.matplotlib:
            return self.matplotlib.multi_line_chart(
                x_data, y_data_dict, title, "X轴", "Y轴", output_path
            )
        elif chart_type == 'pyecharts' and self.pyecharts:
            return self.pyecharts.line_chart(x_data, y_data_dict, title, output_path)
        else:
            raise ValueError(f"Chart type '{chart_type}' not available")

    def create_pie(
        self,
        data: List[Tuple[str, int]],
        title: str,
        filename: str,
        chart_type: str = 'matplotlib'
    ) -> str:
        """创建饼图"""
        output_path = self.get_output_path(filename)

        if chart_type == 'matplotlib' and self.matplotlib:
            labels = [d[0] for d in data]
            sizes = [d[1] for d in data]
            return self.matplotlib.pie_chart(labels, sizes, title, output_path)
        elif chart_type == 'pyecharts' and self.pyecharts:
            return self.pyecharts.pie_chart(data, title, output_path)
        else:
            raise ValueError(f"Chart type '{chart_type}' not available")


def demo():
    """演示图表生成功能"""
    print("=" * 50)
    print("数据可视化工具演示")
    print("=" * 50)

    # 测试数据
    categories = ["Python", "Java", "JavaScript", "Go", "Rust"]
    values = [85, 70, 75, 45, 30]

    x_data = ["1月", "2月", "3月", "4月", "5月"]
    y_data = {
        "浏览量": [1000, 1200, 1500, 1300, 1800],
        "点赞数": [100, 150, 200, 180, 250]
    }

    pie_data = [
        ("技术", 45),
        ("生活", 30),
        ("娱乐", 15),
        ("其他", 10)
    ]

    print("\n可用的图表类型:")

    if HAS_MATPLOTLIB:
        print("  - Matplotlib (静态图表): 已安装")
        print("    示例: charts.matplotlib.bar_chart(...)")
    else:
        print("  - Matplotlib: 未安装 (pip install matplotlib)")

    if HAS_PYECHARTS:
        print("  - Pyecharts (交互式图表): 已安装")
        print("    示例: charts.pyecharts.bar_chart(...)")
    else:
        print("  - Pyecharts: 未安装 (pip install pyecharts)")

    print("\n示例数据:")
    print(f"  柱状图数据: {dict(zip(categories, values))}")
    print(f"  折线图数据: {y_data}")
    print(f"  饼图数据: {pie_data}")

    print("\n使用示例:")
    print("""
    from chart_demo import ChartFactory

    factory = ChartFactory(output_dir="./output")

    # 创建柱状图
    factory.create_bar(categories, values, "编程语言流行度", "bar.png")

    # 创建折线图
    factory.create_line(x_data, y_data, "月度数据趋势", "line.png")

    # 创建饼图
    factory.create_pie(pie_data, "内容分类分布", "pie.png")

    # 创建交互式图表 (HTML)
    factory.create_bar(categories, values, "编程语言流行度", "bar.html", chart_type='pyecharts')
    """)

    print("\n" + "=" * 50)
    print("演示完成")
    print("=" * 50)


if __name__ == "__main__":
    demo()
