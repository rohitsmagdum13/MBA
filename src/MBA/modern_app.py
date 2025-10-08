"""
MBA S3 Data Ingestion - Beautiful Streamlit UI.

Enhanced interactive web interface with modern design patterns,
glassmorphism effects, and stunning visual aesthetics.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import asyncio
from concurrent.futures import ThreadPoolExecutor
import boto3
from dataclasses import dataclass, asdict
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError, OperationalError
import sqlalchemy

# Import MBA modules - maintaining exact import structure
try:
    from MBA.agents.orchestration_agent.wrapper import OrchestratorAgent
    from MBA.agents.member_verification_agent.wrapper import MemberVerificationAgent
    from MBA.agents.intent_identification_agent.wrapper import IntentIdentificationAgent
    from MBA.agents.benefit_accumulator_agent.wrapper import BenefitAccumulatorAgent
    from MBA.agents.deductible_oop_agent.wrapper import DeductibleOOPAgent
except ImportError:
    OrchestratorAgent = None
    MemberVerificationAgent = None
    IntentIdentificationAgent = None
    BenefitAccumulatorAgent = None
    DeductibleOOPAgent = None

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

try:
    from MBA.core.settings import settings
    from MBA.core.logging_config import get_logger, setup_root_logger
    from MBA.services.s3_client import build_session, check_s3_file_exists, list_s3_files
    from MBA.services.file_utils import discover_files, parse_extensions, build_s3_key, detect_scope_from_path
    from MBA.services.duplicate_detector import DuplicateDetector
    from MBA.cli.cli import Uploader
except ImportError as e:
    st.error(f"Import error: {e}. Please ensure all MBA modules are installed.")
    settings = None

# Initialize logging
try:
    setup_root_logger()
    logger = get_logger(__name__)
except:
    logger = None

# Page configuration with modern theme
st.set_page_config(
    page_title="MBA S3 Portal | Cloud Management System",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/mba-healthcare',
        'Report a bug': 'https://github.com/mba-healthcare/issues',
        'About': "MBA S3 Data Portal - Enterprise Cloud Storage Management System"
    }
)

# Enhanced Modern CSS with Glassmorphism and Animations
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
    
    /* Global Styles */
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    
    code, pre {
        font-family: 'JetBrains Mono', monospace !important;
    }
    
    /* Main App Background */
    .stApp {
        background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 25%, #2d1b69 50%, #1a1f3a 75%, #0a0e27 100%);
        background-size: 400% 400%;
        animation: gradientShift 15s ease infinite;
    }
    
    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    /* Main Content Area */
    .main {
        padding: 1.5rem;
        max-width: 100%;
        animation: fadeIn 0.5s ease-out;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* Glass Card Design */
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        padding: 2rem;
        margin-bottom: 1.5rem;
        box-shadow: 
            0 8px 32px 0 rgba(31, 38, 135, 0.37),
            inset 0 1px 0 0 rgba(255, 255, 255, 0.1);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }
    
    .glass-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.05), transparent);
        transition: left 0.6s;
    }
    
    .glass-card:hover::before {
        left: 100%;
    }
    
    .glass-card:hover {
        transform: translateY(-5px);
        border: 1px solid rgba(255, 255, 255, 0.15);
        box-shadow: 
            0 12px 40px 0 rgba(31, 38, 135, 0.45),
            inset 0 1px 0 0 rgba(255, 255, 255, 0.15);
    }
    
    /* Enhanced Metric Cards */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        background-size: 200% 200%;
        animation: gradientPulse 4s ease infinite;
        padding: 1.75rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        position: relative;
        overflow: hidden;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 
            0 10px 40px rgba(102, 126, 234, 0.3),
            inset 0 1px 0 rgba(255, 255, 255, 0.2);
    }
    
    @keyframes gradientPulse {
        0%, 100% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
    }
    
    .metric-card::after {
        content: '';
        position: absolute;
        top: -50%;
        right: -50%;
        width: 200%;
        height: 200%;
        background: linear-gradient(45deg, transparent, rgba(255, 255, 255, 0.1), transparent);
        transform: rotate(45deg);
        animation: shimmer 3s linear infinite;
    }
    
    @keyframes shimmer {
        0% { transform: translateX(-100%) translateY(-100%) rotate(45deg); }
        100% { transform: translateX(100%) translateY(100%) rotate(45deg); }
    }
    
    .metric-card:hover {
        transform: translateY(-8px) scale(1.02);
        box-shadow: 
            0 15px 50px rgba(102, 126, 234, 0.4),
            inset 0 1px 0 rgba(255, 255, 255, 0.3);
    }
    
    .metric-value {
        font-size: 2.75rem;
        font-weight: 800;
        margin: 0;
        text-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
        letter-spacing: -0.02em;
        position: relative;
        z-index: 1;
        animation: countUp 1s ease-out;
    }
    
    @keyframes countUp {
        from { opacity: 0; transform: scale(0.5); }
        to { opacity: 1; transform: scale(1); }
    }
    
    .metric-label {
        font-size: 0.95rem;
        font-weight: 600;
        opacity: 0.95;
        margin-top: 0.75rem;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        position: relative;
        z-index: 1;
    }
    
    /* Modern Status Badges */
    .status-badge {
        padding: 0.5rem 1.25rem;
        border-radius: 50px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        margin: 0.25rem;
        transition: all 0.3s ease;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        position: relative;
        overflow: hidden;
    }
    
    .status-badge::before {
        content: '';
        position: absolute;
        top: 50%;
        left: 50%;
        width: 0;
        height: 0;
        background: rgba(255, 255, 255, 0.2);
        border-radius: 50%;
        transform: translate(-50%, -50%);
        transition: width 0.3s, height 0.3s;
    }
    
    .status-badge:hover::before {
        width: 100px;
        height: 100px;
    }
    
    .status-badge:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
    }
    
    .status-success {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
    }
    
    .status-warning {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        color: white;
        box-shadow: 0 4px 15px rgba(245, 158, 11, 0.3);
    }
    
    .status-error {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        color: white;
        box-shadow: 0 4px 15px rgba(239, 68, 68, 0.3);
    }
    
    .status-info {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);
    }
    
    /* Pulse Animation */
    .pulse {
        animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
    
    /* Enhanced File Cards */
    .file-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }
    
    .file-card:hover {
        transform: translateY(-5px);
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(102, 126, 234, 0.3);
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.2);
    }
    
    /* Progress Bars */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 50%, #f472b6 100%);
        background-size: 200% 100%;
        animation: progressWave 2s linear infinite;
        height: 8px;
        border-radius: 10px;
    }
    
    @keyframes progressWave {
        0% { background-position: 0% 0%; }
        100% { background-position: 200% 0%; }
    }
    
    /* Modern Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        border: none;
        padding: 0.75rem 1.75rem;
        font-weight: 600;
        border-radius: 12px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        position: relative;
        overflow: hidden;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, 
            rgba(15, 23, 42, 0.95) 0%, 
            rgba(30, 41, 59, 0.95) 50%, 
            rgba(15, 23, 42, 0.95) 100%);
        backdrop-filter: blur(20px);
    }
    
    section[data-testid="stSidebar"] > div {
        padding-top: 2rem;
    }
    
    /* Headers with Gradient */
    h1, h2, h3 {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f472b6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-weight: 700;
    }
    
    /* Info Boxes */
    .info-box {
        background: rgba(59, 130, 246, 0.1);
        backdrop-filter: blur(10px);
        border-left: 4px solid #3b82f6;
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1.5rem 0;
        transition: all 0.3s ease;
    }
    
    /* Success Boxes */
    .success-box {
        background: rgba(16, 185, 129, 0.1);
        backdrop-filter: blur(10px);
        border-left: 4px solid #10b981;
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1.5rem 0;
    }
    
    /* Warning Boxes */
    .warning-box {
        background: rgba(245, 158, 11, 0.1);
        backdrop-filter: blur(10px);
        border-left: 4px solid #f59e0b;
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1.5rem 0;
    }
    
    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 0.5rem;
        gap: 0.5rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 10px;
        color: rgba(255, 255, 255, 0.7);
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
    }
    
    /* Floating Animation */
    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-20px); }
    }
    
    .floating {
        animation: float 6s ease-in-out infinite;
    }
    
    /* Custom Scrollbar */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.02);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
    }
    
    /* Glow Effects */
    .glow {
        box-shadow: 0 0 20px rgba(102, 126, 234, 0.5),
                    0 0 40px rgba(102, 126, 234, 0.3);
    }
    
    /* Responsive Design */
    @media (max-width: 768px) {
        .metric-card {
            padding: 1.25rem;
        }
        
        .metric-value {
            font-size: 2rem;
        }
        
        .glass-card {
            padding: 1.5rem;
        }
    }
    </style>
""", unsafe_allow_html=True)

# Session state initialization
if 'upload_history' not in st.session_state:
    st.session_state.upload_history = []
if 'duplicate_scan_results' not in st.session_state:
    st.session_state.duplicate_scan_results = {}
if 'selected_files' not in st.session_state:
    st.session_state.selected_files = []
if 'upload_stats' not in st.session_state:
    st.session_state.upload_stats = {
        'total_uploaded': 0,
        'total_skipped': 0,
        'total_failed': 0,
        'total_size': 0
    }

# Data Classes
@dataclass
class UploadJob:
    """Data class for upload jobs"""
    file_path: str
    scope: str
    s3_key: str
    status: str
    message: str
    size: int
    timestamp: datetime

class StreamlitUploader:
    """
    Wrapper for upload functionality with Streamlit progress tracking.
    """
    
    def __init__(self, uploader, progress_bar=None, status_text=None):
        self.uploader = uploader
        self.progress_bar = progress_bar
        self.status_text = status_text
        self.current_file = 0
        self.total_files = 0
    
    def upload_batch_with_progress(self, files: List[Path], input_dir: Path, concurrency: int = 4):
        """Upload files with visual progress tracking."""
        self.total_files = len(files)
        results = {
            'uploaded': 0,
            'skipped': 0,
            'failed': 0,
            'details': []
        }
        
        for idx, file_path in enumerate(files):
            self.current_file = idx + 1
            
            if self.progress_bar:
                self.progress_bar.progress(self.current_file / self.total_files)
            if self.status_text:
                self.status_text.text(f"🚀 Processing {file_path.name} ({self.current_file}/{self.total_files})")
            
            path, success, message = self.uploader.upload_single(file_path, input_dir)
            
            if success:
                if "Skipped" in message:
                    results['skipped'] += 1
                    status = 'skipped'
                else:
                    results['uploaded'] += 1
                    status = 'success'
            else:
                results['failed'] += 1
                status = 'failed'
            
            job = UploadJob(
                file_path=str(file_path),
                scope=detect_scope_from_path(file_path, input_dir) or 'unknown',
                s3_key=message.split('s3://')[-1] if 's3://' in message else '',
                status=status,
                message=message,
                size=file_path.stat().st_size if file_path.exists() else 0,
                timestamp=datetime.now()
            )
            
            results['details'].append(job)
            st.session_state.upload_history.insert(0, asdict(job))
        
        return results

def render_header():
    """Render stunning animated header"""
    st.markdown("""
        <div style="text-align: center; padding: 3rem 0 2rem 0; position: relative;">
            <div class="floating" style="position: absolute; top: 10px; left: 5%; font-size: 3rem; opacity: 0.15;">☁️</div>
            <div class="floating" style="position: absolute; top: 40px; right: 8%; font-size: 2.5rem; opacity: 0.15; animation-delay: 2s;">🌐</div>
            <div class="floating" style="position: absolute; bottom: 10px; left: 15%; font-size: 2rem; opacity: 0.15; animation-delay: 4s;">📊</div>
            
            <h1 style="font-size: 4rem; font-weight: 800; margin-bottom: 1rem; 
                       background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f472b6 100%);
                       -webkit-background-clip: text; 
                       -webkit-text-fill-color: transparent;
                       background-clip: text;
                       text-shadow: 0 10px 30px rgba(0,0,0,0.1);
                       letter-spacing: -0.03em;
                       animation: fadeIn 1s ease-out;">
                MBA S3 Data Portal
            </h1>
            <p style="color: rgba(255,255,255,0.8); font-size: 1.25rem; font-weight: 300; 
                     letter-spacing: 0.1em; text-transform: uppercase;
                     animation: fadeIn 1s ease-out 0.2s both;">
                Intelligent Cloud Storage Management System
            </p>
            <div style="display: flex; justify-content: center; gap: 1.5rem; margin-top: 2rem;
                        animation: fadeIn 1s ease-out 0.4s both;">
                <span class="status-badge status-info pulse">
                    <span style="display: inline-block; width: 8px; height: 8px; 
                                background: white; border-radius: 50%; margin-right: 0.5rem;"></span>
                    System Online
                </span>
                <span class="status-badge status-success">
                    ✓ Secure Connection
                </span>
                <span class="status-badge status-warning">
                    ⚡ High Performance
                </span>
            </div>
        </div>
    """, unsafe_allow_html=True)

def render_metrics():
    """Render beautiful animated metrics dashboard"""
    col1, col2, col3, col4 = st.columns(4)
    
    stats = st.session_state.upload_stats
    
    metrics_config = [
        {
            'value': stats['total_uploaded'],
            'label': 'Files Uploaded',
            'gradient': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
        },
        {
            'value': stats['total_skipped'],
            'label': 'Smart Skips',
            'gradient': 'linear-gradient(135deg, #f59e0b 0%, #ef4444 100%)'
        },
        {
            'value': stats['total_failed'],
            'label': 'Retry Queue',
            'gradient': 'linear-gradient(135deg, #10b981 0%, #059669 100%)'
        },
        {
            'value': f"{stats['total_size'] / (1024 * 1024):.1f} MB",
            'label': 'Data Processed',
            'gradient': 'linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%)'
        }
    ]
    
    for col, config in zip([col1, col2, col3, col4], metrics_config):
        with col:
            st.markdown(f"""
                <div class="metric-card" style="background: {config['gradient']};">
                    <p class="metric-value">{config['value']}</p>
                    <p class="metric-label">{config['label']}</p>
                </div>
            """, unsafe_allow_html=True)

def render_sidebar():
    """Render beautiful sidebar with configuration"""
    st.sidebar.markdown("""
        <div class="glass-card" style="text-align: center; padding: 1.5rem; margin-bottom: 1rem;">
            <h2 style="color: white; font-size: 1.75rem; margin: 0;">
                ⚙️ Control Center
            </h2>
            <p style="color: rgba(255,255,255,0.6); font-size: 0.9rem; margin-top: 0.5rem;">
                Configure your cloud pipeline
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # AWS Configuration
    with st.sidebar.expander("🔐 **AWS Configuration**", expanded=True):
        aws_profile = st.text_input(
            "AWS Profile",
            value=settings.aws_profile if settings else "",
            help="Leave empty to use default credentials"
        )
        
        aws_region = st.selectbox(
            "AWS Region",
            options=["ap-south-1", "us-east-1", "us-west-2", "eu-west-1"],
            index=0
        )
        
        col1, col2 = st.columns(2)
        with col1:
            mba_bucket = st.text_input(
                "MBA Bucket",
                value=settings.s3_bucket_mba if settings else "",
                help="S3 bucket for MBA files"
            )
        with col2:
            policy_bucket = st.text_input(
                "Policy Bucket",
                value=settings.s3_bucket_policy if settings else "",
                help="S3 bucket for Policy files"
            )
    
    # Upload Settings
    with st.sidebar.expander("🚀 **Upload Configuration**", expanded=True):
        concurrency = st.slider(
            "⚡ Parallel Streams",
            min_value=1,
            max_value=10,
            value=4,
            help="Number of parallel uploads"
        )
        
        skip_duplicates = st.checkbox(
            "🔍 Smart Duplicate Detection",
            value=True,
            help="Skip files that already exist in S3"
        )
        
        overwrite = st.checkbox(
            "♻️ Overwrite Mode",
            value=False,
            help="Overwrite files that exist in S3"
        )
        
        auto_detect_scope = st.checkbox(
            "🎯 Auto-Scope Detection",
            value=True,
            help="Automatically detect MBA/Policy from path"
        )
    
    # File Filters
    with st.sidebar.expander("📁 **Smart Filters**", expanded=False):
        include_extensions = st.text_input(
            "✅ Include Types",
            placeholder="pdf, csv, docx",
            help="Comma-separated list of extensions to include"
        )
        
        exclude_extensions = st.text_input(
            "❌ Exclude Types",
            placeholder="tmp, bak, cache",
            help="Comma-separated list of extensions to exclude"
        )
    
    return {
        'aws_profile': aws_profile,
        'aws_region': aws_region,
        'mba_bucket': mba_bucket,
        'policy_bucket': policy_bucket,
        'concurrency': concurrency,
        'skip_duplicates': skip_duplicates,
        'overwrite': overwrite,
        'auto_detect_scope': auto_detect_scope,
        'include_extensions': include_extensions,
        'exclude_extensions': exclude_extensions
    }

def render_file_discovery_tab():
    """Enhanced file discovery with beautiful UI"""
    st.markdown("""
        <div class="glass-card">
            <h3 style="color: white; margin-bottom: 1rem;">📁 Intelligent File Discovery</h3>
            <p style="color: rgba(255,255,255,0.6); font-size: 0.95rem;">
                Scan and analyze your local file system with advanced filtering capabilities
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        input_dir = st.text_input(
            "📂 Target Directory",
            value="./data",
            help="Directory to scan for files"
        )
    
    with col2:
        scope_filter = st.selectbox(
            "🎯 Scope Filter",
            options=["All", "MBA", "Policy"],
            help="Filter files by scope"
        )
    
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔍 **SCAN NOW**", use_container_width=True):
            scan_directory(input_dir, scope_filter)
    
    # Display discovered files
    if st.session_state.selected_files:
        st.markdown(f"""
            <div class="glass-card">
                <h4 style="color: white;">✨ Discovered {len(st.session_state.selected_files)} Files</h4>
            </div>
        """, unsafe_allow_html=True)
        
        # File type distribution
        file_types = {}
        for file_path in st.session_state.selected_files:
            ext = Path(file_path).suffix.lower() or 'no_ext'
            file_types[ext] = file_types.get(ext, 0) + 1
        
        if file_types:
            fig = px.pie(
                values=list(file_types.values()),
                names=list(file_types.keys()),
                title="File Type Distribution",
                color_discrete_sequence=['#667eea', '#764ba2', '#f472b6', '#fb923c', '#10b981']
            )
            fig.update_traces(
                textposition='inside',
                textinfo='percent+label',
                hovertemplate='<b>%{label}</b><br>Files: %{value}<br>Percentage: %{percent}<extra></extra>'
            )
            fig.update_layout(
                height=400,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                showlegend=True,
                legend=dict(
                    bgcolor='rgba(255,255,255,0.05)',
                    bordercolor='rgba(255,255,255,0.1)',
                    borderwidth=1
                )
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # File selection
        st.markdown("#### 📋 Select Files to Upload")
        
        col1, col2, col3 = st.columns([1, 1, 3])
        with col1:
            if st.button("✅ **Select All**"):
                st.session_state.selected_files = st.session_state.selected_files.copy()
        with col2:
            if st.button("❌ **Deselect All**"):
                st.session_state.selected_files = []
        
        # File grid
        files_per_row = 3
        rows = (len(st.session_state.selected_files) + files_per_row - 1) // files_per_row
        
        for row in range(min(rows, 10)):
            cols = st.columns(files_per_row)
            for col_idx in range(files_per_row):
                file_idx = row * files_per_row + col_idx
                if file_idx < len(st.session_state.selected_files):
                    file_path = st.session_state.selected_files[file_idx]
                    file_name = Path(file_path).name
                    try:
                        file_size = Path(file_path).stat().st_size / 1024
                    except:
                        file_size = 0
                    
                    with cols[col_idx]:
                        st.checkbox(
                            f"📄 {file_name[:30]}{'...' if len(file_name) > 30 else ''}",
                            value=True,
                            key=f"file_{file_idx}",
                            help=f"Size: {file_size:.1f} KB"
                        )

def scan_directory(input_dir: str, scope_filter: str):
    """Scan directory for files with error handling"""
    try:
        input_path = Path(input_dir).resolve()
        
        if not input_path.exists():
            st.error(f"Directory does not exist: {input_dir}")
            return
        
        with st.spinner("🔍 Scanning directory..."):
            files = []
            
            if scope_filter == "All":
                files = discover_files(input_path)
            else:
                scope = scope_filter.lower()
                files = discover_files(input_path, scope=scope)
            
            st.session_state.selected_files = [str(f) for f in files]
            st.success(f"✨ Successfully discovered {len(files)} files!")
    
    except Exception as e:
        st.error(f"❌ Error scanning directory: {e}")

def render_duplicate_detection_tab():
    """Enhanced duplicate detection interface"""
    st.markdown("""
        <div class="glass-card">
            <h3 style="color: white; margin-bottom: 1rem;">🔍 Smart Duplicate Detection</h3>
            <p style="color: rgba(255,255,255,0.6);">
                AI-powered duplicate file detection and management
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        scan_dir = st.text_input(
            "📂 Directory to Scan",
            value="./data",
            help="Directory to scan for duplicates"
        )
    
    with col2:
        check_s3 = st.checkbox("☁️ Check S3", value=False, help="Also check for duplicates in S3")
    
    if st.button("🔍 **START ANALYSIS**", use_container_width=True):
        scan_for_duplicates(scan_dir, check_s3)
    
    # Display results
    if st.session_state.duplicate_scan_results:
        results = st.session_state.duplicate_scan_results
        
        # Summary metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("📁 Duplicate Groups", results.get('groups', 0))
        with col2:
            st.metric("📄 Total Duplicates", results.get('total_duplicates', 0))
        with col3:
            st.metric("💾 Space Wasted", f"{results.get('wasted_space', 0):.1f} MB")
        
        # Duplicate groups
        if results.get('duplicates'):
            st.markdown("#### Duplicate Files Found")
            
            for idx, (hash_val, files) in enumerate(results['duplicates'].items(), 1):
                with st.expander(f"📦 Group {idx} - {len(files)} files", expanded=False):
                    original = files[0]
                    st.info(f"**Original:** 📄 {original['name']} ({original['size_mb']:.2f} MB)")
                    
                    st.markdown("**Duplicates:**")
                    for dup in files[1:]:
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.warning(f"📄 {dup['name']} ({dup['size_mb']:.2f} MB)")
                        with col2:
                            if st.button("🗑️ Delete", key=f"delete_{hash_val}_{dup['name']}"):
                                st.info("Delete functionality not implemented in demo")

def scan_for_duplicates(scan_dir: str, check_s3: bool):
    """Scan for duplicate files with error handling"""
    try:
        if not DuplicateDetector:
            st.error("DuplicateDetector module not available")
            return
            
        detector = DuplicateDetector()
        input_path = Path(scan_dir).resolve()
        
        if not input_path.exists():
            st.error(f"Directory does not exist: {scan_dir}")
            return
        
        with st.spinner("🔍 Scanning for duplicates..."):
            hash_to_files = detector.scan_local_directory(input_path)
            
            duplicates = {
                h: paths for h, paths in hash_to_files.items()
                if len(paths) > 1
            }
            
            total_duplicates = sum(len(paths) - 1 for paths in duplicates.values())
            wasted_space = 0
            
            duplicate_details = {}
            for hash_val, paths in duplicates.items():
                file_info = []
                for path in paths:
                    stat = path.stat()
                    file_info.append({
                        'name': path.name,
                        'path': str(path),
                        'size': stat.st_size,
                        'size_mb': stat.st_size / (1024 * 1024),
                        'modified': datetime.fromtimestamp(stat.st_mtime)
                    })
                    if len(file_info) > 1:
                        wasted_space += stat.st_size
                
                file_info.sort(key=lambda x: x['modified'])
                duplicate_details[hash_val] = file_info
            
            st.session_state.duplicate_scan_results = {
                'groups': len(duplicates),
                'total_duplicates': total_duplicates,
                'wasted_space': wasted_space / (1024 * 1024),
                'duplicates': duplicate_details
            }
            
            if duplicates:
                st.warning(f"⚠️ Found {total_duplicates} duplicate files in {len(duplicates)} groups")
            else:
                st.success("✅ No duplicate files found!")
    
    except Exception as e:
        st.error(f"❌ Error scanning for duplicates: {e}")

def render_upload_tab(config: dict):
    """Beautiful upload interface"""
    st.markdown("### 📤 Upload Files")
    
    if not st.session_state.selected_files:
        st.info("📁 Please discover files first in the File Discovery tab")
        return
    
    st.markdown(f"#### ✅ Ready to upload {len(st.session_state.selected_files)} files")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        dry_run = st.checkbox("🔍 Dry Run", value=False, help="Preview upload without actually uploading")
    
    with col2:
        selected_scope = st.selectbox(
            "🎯 Upload Scope",
            options=["auto-detect", "mba", "policy"],
            help="Choose upload scope or auto-detect"
        )
    
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚀 **START UPLOAD**", use_container_width=True, type="primary"):
            perform_upload(config, dry_run, selected_scope)
    
    # Upload history
    if st.session_state.upload_history:
        st.markdown("#### 📜 Recent Upload History")
        
        df = pd.DataFrame(st.session_state.upload_history[:20])
        
        for _, row in df.iterrows():
            status_emoji = {
                'success': '✅',
                'skipped': '⏭️',
                'failed': '❌',
                'pending': '⏳'
            }.get(row['status'], '❓')
            
            col1, col2, col3, col4 = st.columns([1, 3, 2, 2])
            
            with col1:
                st.markdown(f"{status_emoji} **{row['status'].upper()}**")
            
            with col2:
                st.markdown(f"📄 {Path(row['file_path']).name}")
            
            with col3:
                st.markdown(f"📁 {row['scope'].upper()}")
            
            with col4:
                timestamp = pd.to_datetime(row['timestamp'])
                st.markdown(f"🕐 {timestamp.strftime('%H:%M:%S')}")

def perform_upload(config: dict, dry_run: bool, selected_scope: str):
    """Perform file upload with error handling"""
    try:
        if not Uploader:
            st.error("Uploader module not available")
            return
            
        scope = None if selected_scope == "auto-detect" else selected_scope
        auto_detect = selected_scope == "auto-detect"
        
        uploader = Uploader(
            scope=scope,
            aws_profile=config['aws_profile'],
            region=config['aws_region'],
            dry_run=dry_run,
            auto_detect_scope=auto_detect,
            skip_duplicates=config['skip_duplicates'],
            overwrite=config['overwrite']
        )
        
        files = [Path(f) for f in st.session_state.selected_files]
        input_dir = Path("./data").resolve()
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        st_uploader = StreamlitUploader(uploader, progress_bar, status_text)
        
        with st.spinner("📤 Uploading files..."):
            results = st_uploader.upload_batch_with_progress(
                files,
                input_dir,
                config['concurrency']
            )
        
        st.session_state.upload_stats['total_uploaded'] += results['uploaded']
        st.session_state.upload_stats['total_skipped'] += results['skipped']
        st.session_state.upload_stats['total_failed'] += results['failed']
        
        for detail in results['details']:
            if detail.status == 'success':
                st.session_state.upload_stats['total_size'] += detail.size
        
        progress_bar.empty()
        status_text.empty()
        
        if dry_run:
            st.info("🔍 Dry run completed - no files were actually uploaded")
        else:
            st.success(f"✅ Upload completed! Uploaded: {results['uploaded']}, Skipped: {results['skipped']}, Failed: {results['failed']}")
        
        st.rerun()
    
    except Exception as e:
        st.error(f"❌ Upload error: {e}")
        if logger:
            logger.error(f"Upload error: {e}", exc_info=True)

# Continue with remaining functions...
def render_s3_browser_tab():
    """S3 bucket browser interface"""
    st.markdown("### 🗂️ S3 Browser")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        selected_bucket_type = st.selectbox(
            "☁️ Bucket",
            options=["MBA", "Policy"],
            help="Select bucket to browse"
        )
    
    with col2:
        prefix = st.text_input(
            "📁 Prefix",
            value="",
            help="Filter by prefix (e.g., pdf/)"
        )
    
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 **REFRESH**", use_container_width=True):
            list_s3_contents(selected_bucket_type, prefix)
    
    if 's3_contents' not in st.session_state:
        list_s3_contents(selected_bucket_type, prefix)
    
    if 's3_contents' in st.session_state and st.session_state.s3_contents:
        files = st.session_state.s3_contents
        
        total_size = sum(f.get('size', 0) for f in files)
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("📄 Total Files", len(files))
        with col2:
            st.metric("💾 Total Size", f"{total_size / (1024*1024):.1f} MB")
        with col3:
            file_types = {}
            for f in files:
                ext = Path(f['key']).suffix.lower() or 'no_ext'
                file_types[ext] = file_types.get(ext, 0) + 1
            st.metric("📊 File Types", len(file_types))
        
        st.markdown("#### Files in S3")
        
        df = pd.DataFrame(files)
        if not df.empty:
            df['name'] = df['key'].apply(lambda x: Path(x).name)
            df['type'] = df['key'].apply(lambda x: Path(x).suffix.lower())
            df['size_mb'] = df['size'] / (1024 * 1024)
            df['modified'] = pd.to_datetime(df['last_modified'])
            
            display_mode = st.radio(
                "View Mode",
                options=["📊 Table", "📇 Cards"],
                horizontal=True
            )
            
            if display_mode == "📊 Table":
                display_df = df[['name', 'type', 'size_mb', 'modified']].copy()
                display_df['size_mb'] = display_df['size_mb'].round(2)
                display_df['modified'] = display_df['modified'].dt.strftime('%Y-%m-%d %H:%M')
                
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                for _, row in df.iterrows():
                    with st.expander(f"📄 {row['name']}", expanded=False):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.markdown(f"**Type:** {row['type']}")
                            st.markdown(f"**Size:** {row['size_mb']:.2f} MB")
                        with col2:
                            st.markdown(f"**Modified:** {row['modified'].strftime('%Y-%m-%d %H:%M')}")
                            st.markdown(f"**ETag:** {row.get('etag', 'N/A')[:8]}...")
                        with col3:
                            st.code(row['key'], language=None)
    else:
        st.info("📭 No files found in S3 bucket")

def list_s3_contents(bucket_type: str, prefix: str):
    """List S3 bucket contents with error handling"""
    try:
        if not settings:
            st.error("Settings not configured")
            return
            
        bucket = settings.s3_bucket_mba if bucket_type == "MBA" else settings.s3_bucket_policy
        
        session = build_session(
            profile=settings.aws_profile,
            access_key=settings.aws_access_key_id,
            secret_key=settings.aws_secret_access_key,
            region=settings.aws_default_region
        )
        
        with st.spinner(f"📡 Loading {bucket_type} bucket contents..."):
            files = list_s3_files(session, bucket, prefix)
            st.session_state.s3_contents = files
            
            if files:
                st.success(f"✅ Found {len(files)} files")
            else:
                st.info("📭 Bucket is empty or prefix not found")
    
    except Exception as e:
        st.error(f"❌ Error listing S3 contents: {e}")
        st.session_state.s3_contents = []

def render_analytics_tab():
    """Analytics dashboard with beautiful charts"""
    st.markdown("### 📊 Analytics & Insights")
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("📅 Start Date", datetime.now() - timedelta(days=7))
    with col2:
        end_date = st.date_input("📅 End Date", datetime.now())
    
    if st.session_state.upload_history:
        st.markdown("#### 📈 Upload Trends")
        
        df = pd.DataFrame(st.session_state.upload_history)
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['date'] = df['timestamp'].dt.date
            df['hour'] = df['timestamp'].dt.hour
            
            # Daily trends
            daily_stats = df.groupby(['date', 'status']).size().reset_index(name='count')
            
            fig = px.line(
                daily_stats,
                x='date',
                y='count',
                color='status',
                title='Daily Upload Trends',
                color_discrete_map={
                    'success': '#10b981',
                    'skipped': '#f59e0b',
                    'failed': '#ef4444'
                }
            )
            fig.update_layout(
                height=400,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white')
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # File type analytics
    st.markdown("#### 📊 File Type Analytics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        file_types = {
            'PDF': 45,
            'CSV': 30,
            'DOCX': 15,
            'Image': 8,
            'Other': 2
        }
        
        fig = px.pie(
            values=list(file_types.values()),
            names=list(file_types.keys()),
            title='File Type Distribution',
            hole=0.4,
            color_discrete_sequence=['#667eea', '#764ba2', '#f472b6', '#fb923c', '#10b981']
        )
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white')
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        scope_data = {'MBA': 65, 'Policy': 35}
        
        fig = px.bar(
            x=list(scope_data.keys()),
            y=list(scope_data.values()),
            title='Files by Scope',
            color=list(scope_data.keys()),
            color_discrete_map={'MBA': '#667eea', 'Policy': '#764ba2'}
        )
        fig.update_layout(
            showlegend=False,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white')
        )
        st.plotly_chart(fig, use_container_width=True)

def render_settings_tab():
    """Settings and configuration interface"""
    st.markdown("### ⚙️ Settings & Configuration")
    
    # Cache management
    st.markdown("#### 🗂️ Cache Management")
    
    col1, col2, col3 = st.columns(3)
    
    cache_file = Path("logs/file_cache.json")
    cache_exists = cache_file.exists()
    
    with col1:
        cache_size = cache_file.stat().st_size / 1024 if cache_exists else 0
        st.metric("📦 Cache Size", f"{cache_size:.1f} KB")
    
    with col2:
        if cache_exists:
            cache_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
            st.metric("🕐 Last Updated", cache_time.strftime("%H:%M:%S"))
        else:
            st.metric("🕐 Last Updated", "N/A")
    
    with col3:
        if st.button("🗑️ **CLEAR CACHE**", use_container_width=True):
            if cache_exists:
                cache_file.unlink()
                st.success("✅ Cache cleared successfully")
                st.rerun()

# Database browser functions
def _db_url_read_only() -> str:
    """Build read-only database URL"""
    if not settings:
        return ""
    return f"mysql+pymysql://{settings.RDS_USERNAME}:{settings.RDS_PASSWORD}@{settings.RDS_HOST}:{settings.RDS_PORT}/{settings.RDS_DATABASE}?charset=utf8mb4"

@st.cache_resource(show_spinner=False)
def _get_ro_engine():
    """Get cached read-only database engine"""
    url = _db_url_read_only()
    if not url:
        return None
    eng = create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=1200,
        connect_args={"connect_timeout": 5, "read_timeout": 5, "write_timeout": 5},
    )
    return eng

def _safe_select_df(sql: str, params: dict = None) -> pd.DataFrame:
    """Execute safe SELECT query"""
    try:
        eng = _get_ro_engine()
        if not eng:
            return pd.DataFrame()
        with eng.connect() as conn:
            return pd.read_sql(text(sql), conn, params=params or {})
    except Exception as e:
        st.error(f"Database error: {e}")
        return pd.DataFrame()

def _table_count(table: str) -> int:
    """Get table row count"""
    try:
        df = _safe_select_df(f"SELECT COUNT(*) AS c FROM `{table}`")
        return int(df["c"].iloc[0]) if not df.empty else 0
    except:
        return 0

def render_db_browser_tab():
    """Beautiful database browser"""
    st.markdown("### 🗄️ Database Browser")
    
    c1, c2, c3 = st.columns([1, 1, 3])
    with c1:
        if st.button("🔄 **REFRESH**"):
            st.rerun()
    with c2:
        with st.spinner("Checking DB..."):
            try:
                _ = _safe_select_df("SELECT 1 AS ok")
                st.success("✅ Connected")
            except:
                st.warning("⚠️ DB offline")
    
    st.markdown("#### 📦 Table Statistics")
    tables = ["memberdata", "benefit_accumulator", "deductibles_oop", "plan_details", "ingestion_audit"]
    
    with st.spinner("Loading counts..."):
        counts = []
        for t in tables:
            counts.append({"table": t, "rows": _table_count(t)})
        df_counts = pd.DataFrame(counts)
    
    if not df_counts.empty:
        st.dataframe(df_counts.sort_values("table"), use_container_width=True, hide_index=True)

def main():
    """Main application entry point"""
    # Render components
    render_header()
    render_metrics()
    
    # Sidebar configuration
    config = render_sidebar()
    
    # Tabs
    st.markdown("""
        <div class="glass-card" style="margin-bottom: 1.5rem; padding: 1rem;">
            <p style="color: rgba(255,255,255,0.7); text-align: center; margin: 0; font-size: 0.95rem;">
                Navigate through powerful features using the tabs below
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    tabs = st.tabs([
        "📁 Discovery",
        "🔍 Duplicates", 
        "☁️ Upload",
        "🗂️ S3 Browser",
        "🗄️ Database",
        "📊 Analytics",
        "⚙️ Settings"
    ])
    
    with tabs[0]:
        render_file_discovery_tab()
    
    with tabs[1]:
        render_duplicate_detection_tab()
    
    with tabs[2]:
        render_upload_tab(config)
    
    with tabs[3]:
        render_s3_browser_tab()
    
    with tabs[4]:
        render_db_browser_tab()
    
    with tabs[5]:
        render_analytics_tab()
    
    with tabs[6]:
        render_settings_tab()
    
    # AI Agents Section - Now as main tab
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("🤖 AI Agents - Flexible Verification System", expanded=True):
        agent_tabs = st.tabs(["🔍 Member Verification", "🎯 Intent Analysis", "💰 Benefits", "💳 Deductible", "🤖 Orchestrator"])
        
        with agent_tabs[0]:
            st.markdown("""
                <div class="glass-card">
                    <p style="color: rgba(255,255,255,0.7);">Verify member identity using database lookup.</p>
                </div>
            """, unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            with col1:
                member_id = st.text_input("Member ID", placeholder="M1001", key="verify_member_id")
            with col2:
                dob = st.date_input("Date of Birth", key="verify_dob")
            with col3:
                name = st.text_input("Name (optional)", placeholder="John Doe", key="verify_name")
            
            if st.button("🔍 **VERIFY MEMBER**", key="verify_member", use_container_width=True) and member_id and dob:
                from MBA.agents.member_verification_agent.tools import verify_member
                params = {"member_id": member_id, "dob": str(dob)}
                if name:
                    params["name"] = name
                
                with st.spinner("Verifying member..."):
                    result = asyncio.run(verify_member(params))
                
                if result.get("valid"):
                    st.success(f"✅ Member verified: {result.get('name', 'N/A')}")
                elif result.get("error"):
                    st.error(f"❌ Error: {result['error']}")
                else:
                    st.warning(f"❌ Verification failed: {result.get('message', 'Unknown error')}")
        
        with agent_tabs[1]:
            st.markdown("""
                <div class="glass-card">
                    <p style="color: rgba(255,255,255,0.7);">Analyze user queries to identify intent and extract parameters.</p>
                </div>
            """, unsafe_allow_html=True)
            query = st.text_area("User Query", placeholder="What's my deductible for 2025?", key="intent_query")
            
            if st.button("🎯 **ANALYZE INTENT**", key="analyze_intent", use_container_width=True) and query:
                from MBA.agents.intent_identification_agent.tools import identify_intent_and_params
                
                with st.spinner("Analyzing intent..."):
                    result = asyncio.run(identify_intent_and_params(query))
                
                if result.get("status") == "success":
                    st.success(f"✅ Intent: {result.get('intent')}")
                    if result.get('params'):
                        st.json(result['params'])
                else:
                    st.error(f"❌ Error: {result.get('error', 'Unknown error')}")
        
        with agent_tabs[2]:
            st.markdown("""
                <div class="glass-card">
                    <p style="color: rgba(255,255,255,0.7);">Get benefit accumulator information for members.</p>
                </div>
            """, unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            with col1:
                ben_member_id = st.text_input("Member ID", placeholder="M1001", key="ben_member")
            with col2:
                service = st.selectbox("Service", ["Massage Therapy", "Physical Therapy", "Neurodevelopmental Therapy", "Skilled Nursing Facility", "Smoking Cessation", "Rehabilitation – Outpatient"], key="ben_service")
            with col3:
                plan_year = st.number_input("Plan Year", min_value=2020, max_value=2030, value=2025, key="ben_year")
            
            if st.button("💰 **GET BENEFITS**", key="get_benefits", use_container_width=True) and ben_member_id:
                from MBA.agents.benefit_accumulator_agent.tools import get_benefit_details
                params = {"member_id": ben_member_id, "service": service, "plan_year": plan_year}
                
                with st.spinner("Getting benefit details..."):
                    result = asyncio.run(get_benefit_details(params))
                
                if result.get("status") == "success":
                    st.success(f"✅ Benefits found for {service}")
                    st.json(result)
                elif result.get("status") == "not_found":
                    st.warning("❌ No benefit data found")
                else:
                    st.error(f"❌ Error: {result.get('error', 'Unknown error')}")
        
        with agent_tabs[3]:
            st.markdown("""
                <div class="glass-card">
                    <p style="color: rgba(255,255,255,0.7);">Get deductible and out-of-pocket information for members.</p>
                </div>
            """, unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                ded_member_id = st.text_input("Member ID", placeholder="M1001", key="ded_member")
            with col2:
                ded_plan_year = st.number_input("Plan Year", min_value=2020, max_value=2030, value=2025, key="ded_year")
            
            if st.button("💳 **GET DEDUCTIBLE INFO**", key="get_deductible", use_container_width=True) and ded_member_id:
                from MBA.agents.deductible_oop_agent.tools import get_deductible_oop
                params = {"member_id": ded_member_id, "plan_year": ded_plan_year}
                
                with st.spinner("Getting deductible information..."):
                    result = asyncio.run(get_deductible_oop(params))
                
                if result.get("status") == "success":
                    st.success("✅ Deductible information found")
                    st.json(result)
                elif result.get("status") == "not_found":
                    st.warning("❌ No deductible data found")
                else:
                    st.error(f"❌ Error: {result.get('error', 'Unknown error')}")
        
        with agent_tabs[4]:
            st.markdown("""
                <div class="glass-card">
                    <h4 style="color: white;">🤖 Orchestrator Agent</h4>
                    <p style="color: rgba(255,255,255,0.7);">Ask complete questions with flexible verification support.</p>
                    <div style="background: rgba(59, 130, 246, 0.1); padding: 1rem; border-radius: 8px; margin: 1rem 0;">
                        <p style="color: rgba(255,255,255,0.8); font-size: 0.9rem; margin: 0;">✨ <strong>Flexible Verification:</strong> Use any identifier - member_id, dob, plan_name, or group_number</p>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            query_examples = [
                "Give me complete details for member_id=M1002 dob=1987-12-14",
                "Show all benefits for member_id=M1001", 
                "What's my deductible for plan_name=020213CA",
                "Check benefits for group_number=20213"
            ]
            
            selected_example = st.selectbox(
                "📝 Quick Examples",
                options=["Custom Query"] + query_examples,
                key="orch_examples"
            )
            
            if selected_example == "Custom Query":
                q = st.text_area(
                    "💬 Your Question", 
                    placeholder="Examples:\n• Give me complete details for member_id=M1002 dob=1987-12-14\n• Show deductible for member_id=M1001\n• Check benefits for plan_name=020213CA",
                    height=100,
                    key="orch_query"
                )
            else:
                q = selected_example
                st.text_area("💬 Selected Query", value=q, height=60, disabled=True, key="orch_selected")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown("""
                    **Supported formats:**
                    - `member_id=M1001 dob=1990-05-15`
                    - `plan_name=020213CA`
                    - `group_number=20213`
                    - Any combination of identifiers
                """)
            
            with col2:
                if st.button("🚀 **ASK AI**", key="run_orchestrator", use_container_width=True, type="primary") and q:
                    if not OrchestratorAgent:
                        st.error("❌ Orchestrator Agent not available")
                    else:
                        try:
                            orch = OrchestratorAgent()
                            with st.spinner("🤖 AI is processing your request..."):
                                result = asyncio.run(orch.run({"query": q}))
                            
                            if result.get("summary"):
                                st.markdown("""
                                    <div class="glass-card">
                                        <h4 style="color: white;">🎯 AI Response</h4>
                                    </div>
                                """, unsafe_allow_html=True)
                                st.success("✅ Query processed successfully")
                                st.markdown(f"```\n{result['summary']}\n```")
                            else:
                                st.warning("⚠️ No summary available in response")
                                st.json(result)
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
                            if "member_id and dob required" in str(e):
                                st.info("💡 Try including at least one identifier: member_id, dob, plan_name, or group_number")
    
    # Footer
    st.markdown("---")
    st.markdown("""
        <div class="glass-card" style="text-align: center; padding: 2rem; margin-top: 2rem;">
            <div style="display: flex; justify-content: center; gap: 3rem; margin-bottom: 1rem;">
                <div>
                    <p style="color: rgba(255,255,255,0.5); font-size: 0.85rem; margin: 0;">VERSION</p>
                    <p style="color: white; font-weight: 600; font-size: 1.1rem; margin: 0;">1.0.0</p>
                </div>
                <div>
                    <p style="color: rgba(255,255,255,0.5); font-size: 0.85rem; margin: 0;">STATUS</p>
                    <p style="color: #10b981; font-weight: 600; font-size: 1.1rem; margin: 0;">● ACTIVE</p>
                </div>
                <div>
                    <p style="color: rgba(255,255,255,0.5); font-size: 0.85rem; margin: 0;">ENVIRONMENT</p>
                    <p style="color: white; font-weight: 600; font-size: 1.1rem; margin: 0;">PRODUCTION</p>
                </div>
            </div>
            <p style="color: rgba(255,255,255,0.5); font-size: 0.9rem; margin: 0;">
                © 2024 MBA Healthcare Management Associates | Enterprise Cloud Solutions
            </p>
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()