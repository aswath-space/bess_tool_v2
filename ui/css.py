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

def get_tooltip_css():
    """
    Returns the CSS for custom tooltips using the .tooltip class.
    """
    return """
    <style>
    .tooltip {
        position: relative;
        display: inline-block;
        cursor: help;
        opacity: 0.6;
        margin-left: 4px;
    }
    .tooltip .tooltiptext {
        visibility: hidden;
        width: 200px;
        background-color: #333;
        color: #fff;
        text-align: center;
        border-radius: 6px;
        padding: 8px;
        position: absolute;
        z-index: 100;
        bottom: 150%; /* Position above */
        left: 50%;
        margin-left: -100px; /* Center */
        opacity: 0;
        transition: opacity 0.3s;
        font-size: 0.75rem;
        font-weight: normal;
        line-height: 1.4;
        pointer-events: none;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .tooltip:hover .tooltiptext {
        visibility: visible;
        opacity: 1;
    }
    .tooltip:hover {
        opacity: 1;
    }
    /* Arrow for the tooltip */
    .tooltip .tooltiptext::after {
        content: "";
        position: absolute;
        top: 100%;
        left: 50%;
        margin-left: -5px;
        border-width: 5px;
        border-style: solid;
        border-color: #333 transparent transparent transparent;
    }
    </style>
    """
