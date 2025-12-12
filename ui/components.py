
import streamlit as st

def render_metric_card(label, value, delta=None, delta_color="normal", help_text=None, subtext=None):
    """
    Render a styled metric card using custom HTML.
    
    Parameters:
    -----------
    label : str
        The title of the metric
    value : str
        The main value to display
    delta : str, optional
        The change/delta to display (e.g. "+5%")
    delta_color : str, optional
        "normal" (green), "inverse" (red), or "off" (gray)
    help_text : str, optional
        Tooltip text
    subtext : str, optional
        Small text below the value (NOTE: To ensure consistent heights, specific implementations 
        might choose to omit this or move it to tooltip)
    """
    
    # Delta styling
    delta_html = ""
    if delta:
        if delta_color == "normal":
            color = "#10b981" # Green
            icon = "↑"
        elif delta_color == "inverse":
            color = "#ef4444" # Red
            icon = "↓"
        else:
            color = "#6b7280" # Gray
            icon = ""

        # Smart Logic: Only show arrow if delta looks numeric (starts with digit, symbol, or currency)
        # If it's a text label (e.g. "Review Required", "Healthy"), skip the arrow.
        clean_delta = delta.strip()
        is_numeric_delta = clean_delta and (clean_delta[0].isdigit() or clean_delta[0] in ['+', '-', '€', '$', '£', '¥'])
        if not is_numeric_delta:
            icon = ""
        
        delta_html = f'<div style="color: {color}; font-size: 0.875rem; font-weight: 500; margin-left: auto;">{icon} {clean_delta}</div>'

    help_html = ""
    if help_text:
        # CSS Tooltip Approach with SVG Icon
        # SVG info icon (outline version)
        svg_icon = '''<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="opacity: 0.6; margin-left: 4px; vertical-align: text-bottom;"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>'''
        help_html = f'''<div class="tooltip">{svg_icon}<span class="tooltiptext">{help_text}</span></div>'''

    subtext_html = ""
    if subtext:
        # Render subtext if provided (caller responsibility to manage height consistency)
        subtext_html = f'<div style="font-size: 0.75rem; color: gray; margin-top: 0.25rem;">{subtext}</div>'
    
    html_content = f"""
<div style="
    background-color: var(--bg-secondary);
    padding: 1rem;
    border-radius: 0.75rem;
    border: 1px solid rgba(128, 128, 128, 0.2);
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
    display: flex;
    flex-direction: column;
    justify-content: center;
    height: 100%;
    min-height: 150px;
    margin-bottom: 1rem;
">
    <div style="font-size: 0.875rem; font-weight: 500; opacity: 0.8; margin-bottom: 0.5rem; display: flex; align-items: center;">
        {label} {help_html}
    </div>
    <div style="display: flex; align-items: baseline; gap: 0.5rem; flex-wrap: wrap;">
        <div style="font-size: 1.75rem; font-weight: 600; color: var(--text-main); white-space: nowrap;">{value}</div>
        {delta_html}
    </div>
    {subtext_html}
</div>
"""
    # Flatten HTML by removing all leading indentation from each line
    return "\n".join([line.lstrip() for line in html_content.split("\n")])
