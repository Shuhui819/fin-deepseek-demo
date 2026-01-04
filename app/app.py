import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

import streamlit as st
from src.ft_adapter import hello

st.set_page_config(page_title="Finance Deepseek Demo", layout="wide")
st.title("Finance Deepseek Demo")
st.write("✅ Streamlit 页面已成功打开")
st.write(hello())
