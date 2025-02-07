import streamlit as st
from pathlib import Path
from ui_module import JobUI

# Must be the first Streamlit command
st.set_page_config(
    page_title="AI岗位分析可视化 & 求职系统",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """
    Streamlit 应用入口点。
    通过实例化并运行 JobUI 类，实现 AI 岗位分析可视化 & 求职功能。
    """
    st.title("职位数据分析")
    
    # 添加侧边栏导航
    with st.sidebar:
        st.header("功能导航")
        if st.button("🔍 前往数据抓取页面", use_container_width=True):
            st.switch_page("pages/o1_zhilian_ui.py")
        
        st.markdown("---")
    
    # 初始化会话状态
    if 'data_loaded' not in st.session_state:
        st.session_state.data_loaded = False
    
    # 主界面
    data_root = Path(__file__).parent.parent
    job_ui = JobUI(data_root)
    job_ui.run()

if __name__ == "__main__":
    main()