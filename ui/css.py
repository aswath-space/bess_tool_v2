import streamlit as st
import os

def load_css(file_name):
    """
    Loads a CSS file and injects it into the Streamlit app using markdown.
    Args:
        file_name (str): Relative path to the CSS file.
    """
    try:
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"Error: CSS file not found at {file_name}")
