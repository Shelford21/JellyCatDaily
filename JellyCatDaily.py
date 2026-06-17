import streamlit as st
import base64

st.set_page_config(layout="wide")

with open("JellyCatDaily.png", "rb") as f:
    img = base64.b64encode(f.read()).decode()

st.markdown(f"""
<style>
.main .block-container {{
    padding: 0;
    max-width: 100%;
}}

.fullscreen-img {{
    width: 100vw;
    height: 100vh;
    object-fit: cover;
    display: block;
}}
</style>

<img class="fullscreen-img"
     src="data:image/jpeg;base64,{img}">
""", unsafe_allow_html=True)
#JellyCatDaily.png
