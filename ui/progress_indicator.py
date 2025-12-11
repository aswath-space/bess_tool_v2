"""
Progress Indicator Component
=============================

This component displays a visual progress bar showing which stage of the
user journey the user is currently on.

User Journey Stages:
--------------------
1. PV Baseline - Establish the baseline revenue (The Anchor)
2. Battery Solution - Show the value of adding battery (The Upsell)
3. Investment Decision - Provide financial metrics (The Decision)

Visual Design:
--------------
A horizontal progress bar at the top of the page showing:
- Completed stages: Green checkmark
- Current stage: Blue highlight
- Future stages: Gray

This provides visual feedback and helps users understand where they are
in the analysis process.

Author: [Your Name]
Date: 2025-12-11
"""

import streamlit as st


def render_progress_indicator(current_stage: int):
    """
    Progress indicator removed - user prefers clean layout without sidebar.
    """
    pass  # No-op - progress is implicit in the stage flow


def render_stage_header(stage_number: int, title: str, description: str):
    """
    Render a consistent header for each stage section.
    
    This creates a visually distinct header for each stage with an icon,
    title, and description.
    
    Parameters:
    -----------
    stage_number : int
        Stage number (1, 2, or 3)
    title : str
        Stage title (e.g., "PV Baseline")
    description : str
        Brief description of what this stage does
        
    Example:
    --------
    >>> render_stage_header(
    >>>     stage_number=1,
    >>>     title="PV Baseline",
    >>>     description="Establish your solar park's baseline revenue"
    >>> )
    """
    
    # Choose icon and color based on stage
    if stage_number == 1:
        icon = "☀️"
        color = "#f59e0b"  # Amber
    elif stage_number == 2:
        icon = "🔋"
        color = "#3b82f6"  # Blue
    else:
        icon = "📊"
        color = "#10b981"  # Green
    
    # Custom CSS for stage header
    header_css = f"""
    <style>
    .stage-header {{
        padding: 1.5rem;
        border-left: 4px solid {color};
        background: linear-gradient(to right, rgba(59, 130, 246, 0.05), transparent);
        border-radius: 8px;
        margin: 2rem 0 1rem 0;
    }}
    
    .stage-header-title {{
        font-size: 1.5rem;
        font-weight: 700;
        color: {color};
        margin: 0 0 0.5rem 0;
    }}
    
    .stage-header-description {{
        font-size: 1rem;
        color: #64748b;
        margin: 0;
    }}
    </style>
    """
    
    header_html = f"""
    {header_css}
    <div class="stage-header">
        <div class="stage-header-title">{icon} Stage {stage_number}: {title}</div>
        <div class="stage-header-description">{description}</div>
    </div>
    """
    
    st.markdown(header_html, unsafe_allow_html=True)
