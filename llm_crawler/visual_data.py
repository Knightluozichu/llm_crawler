import streamlit as st
from pathlib import Path
from ui_module import JobUI

def main():
    """
    Streamlit 应用入口点。
    通过实例化并运行 JobUI 类，实现 AI 岗位分析可视化 & 求职功能。
    """
    # 假设本文件与其他 .py 文件在同一包下
    data_root = Path(__file__).parent.parent
    job_ui = JobUI(data_root)
    job_ui.run()

if __name__ == "__main__":
    main()