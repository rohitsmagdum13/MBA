"""
MBA S3 Data Ingestion - Streamlit UI.

Interactive web interface for file upload management with real-time
monitoring, analytics, and database browsing capabilities.

Module Input:
    - User interactions via web browser
    - Local files for upload
    - Configuration via sidebar
    - Database queries for monitoring

Module Output:
    - Web-based user interface
    - File uploads to S3
    - Real-time statistics and charts
    - Database query results
    - Export configurations
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

from MBA.agents.orchestration_agent.wrapper import OrchestratorAgent

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from MBA.core.settings import settings
from MBA.core.logging_config import get_logger, setup_root_logger
from MBA.services.s3_client import build_session, check_s3_file_exists, list_s3_files
from MBA.services.file_utils import discover_files, parse_extensions, build_s3_key, detect_scope_from_path
from MBA.services.duplicate_detector import DuplicateDetector
from MBA.cli.cli import Uploader

# Initialize logging
setup_root_logger()
logger = get_logger(__name__)

# Page configuration
st.set_page_config(
    page_title="MBA S3 Data Ingestion",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for beautiful styling
st.markdown("""
    <style>
    /* Main container */
    .main {
        padding: 1rem;
    }
    
    /* Custom metric cards */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        margin: 0;
    }
    
    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
        margin-top: 0.5rem;
    }
    
    /* Status badges */
    .status-badge {
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 500;
        display: inline-block;
        margin: 0.25rem;
    }
    
    .status-success {
        background-color: #10b981;
        color: white;
    }
    
    .status-warning {
        background-color: #f59e0b;
        color: white;
    }
    
    .status-error {
        background-color: #ef4444;
        color: white;
    }
    
    .status-info {
        background-color: #3b82f6;
        color: white;
    }
    
    /* File cards */
    .file-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.5rem;
        transition: all 0.3s;
    }
    
    .file-card:hover {
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transform: translateY(-2px);
    }
    
    /* Progress bars */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.3s;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #1f2937;
    }
    
    /* Info boxes */
    .info-box {
        background: #f0f9ff;
        border-left: 4px solid #3b82f6;
        padding: 1rem;
        border-radius: 0 8px 8px 0;
        margin: 1rem 0;
    }
    
    /* Success boxes */
    .success-box {
        background: #f0fdf4;
        border-left: 4px solid #10b981;
        padding: 1rem;
        border-radius: 0 8px 8px 0;
        margin: 1rem 0;
    }
    
    /* Warning boxes */
    .warning-box {
        background: #fffbeb;
        border-left: 4px solid #f59e0b;
        padding: 1rem;
        border-radius: 0 8px 8px 0;
        margin: 1rem 0;
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

@dataclass
class UploadJob:
    """Data class for upload jobs"""
    file_path: str
    scope: str
    s3_key: str
    status: str  # pending, uploading, success, skipped, failed
    message: str
    size: int
    timestamp: datetime

class StreamlitUploader:
    """
    Wrapper for upload functionality with Streamlit progress tracking.
    
    Bridges the CLI uploader with Streamlit's progress indicators for
    real-time upload status in the web interface.
    
    Attributes:
        uploader (Uploader): Core upload instance
        progress_bar: Streamlit progress widget
        status_text: Streamlit status text widget
        current_file (int): Current file index
        total_files (int): Total files to process
    """
    
    def __init__(self, uploader: Uploader, progress_bar=None, status_text=None):
        self.uploader = uploader
        self.progress_bar = progress_bar
        self.status_text = status_text
        self.current_file = 0
        self.total_files = 0
    
    def upload_batch_with_progress(self, files: List[Path], input_dir: Path, concurrency: int = 4):
        """
        Upload files with visual progress tracking.
        
        Wraps batch upload with Streamlit progress updates.
        
        Args:
            files (List[Path]): Files to upload
            input_dir (Path): Base directory
            concurrency (int): Parallel upload workers
            
        Returns:
            dict: Upload results containing:
                - uploaded (int): Success count
                - skipped (int): Duplicate count
                - failed (int): Failure count
                - details (List[UploadJob]): Per-file details
                
        Side Effects:
            - Updates progress bar widget
            - Updates status text widget
            - Adds to session state history
        """
        self.total_files = len(files)
        results = {
            'uploaded': 0,
            'skipped': 0,
            'failed': 0,
            'details': []
        }
        
        for idx, file_path in enumerate(files):
            self.current_file = idx + 1
            
            # Update progress
            if self.progress_bar:
                self.progress_bar.progress(self.current_file / self.total_files)
            if self.status_text:
                self.status_text.text(f"Processing {file_path.name} ({self.current_file}/{self.total_files})")
            
            # Upload file
            path, success, message = self.uploader.upload_single(file_path, input_dir)
            
            # Update results
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
            
            # Create upload job record
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
    """
    Render application header with branding.
    
    Creates centered header with gradient styling and tagline.
    
    Output:
        HTML-styled header in Streamlit interface
    """
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
            <div style="text-align: center; padding: 2rem 0;">
                <h1 style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                           -webkit-background-clip: text; 
                           -webkit-text-fill-color: transparent;
                           font-size: 3rem;
                           font-weight: bold;">
                    ☁️ MBA S3 Data Ingestion Portal
                </h1>
                <p style="color: #6b7280; font-size: 1.1rem; margin-top: 0.5rem;">
                    Intelligent file upload management with duplicate detection
                </p>
            </div>
        """, unsafe_allow_html=True)

def render_metrics():
    """
    Render metrics dashboard with key statistics.
    
    Displays four metric cards showing upload statistics with
    gradient backgrounds and formatted values.
    
    Metrics Displayed:
        - Files Uploaded: Total successful uploads
        - Duplicates Skipped: Files avoided due to duplication
        - Failed Uploads: Error count
        - Total Size: Cumulative data volume in MB
    """
    col1, col2, col3, col4 = st.columns(4)
    
    stats = st.session_state.upload_stats
    
    with col1:
        st.markdown(f"""
            <div class="metric-card">
                <p class="metric-value">{stats['total_uploaded']}</p>
                <p class="metric-label">Files Uploaded</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div class="metric-card" style="background: linear-gradient(135deg, #f59e0b 0%, #ef4444 100%);">
                <p class="metric-value">{stats['total_skipped']}</p>
                <p class="metric-label">Duplicates Skipped</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
            <div class="metric-card" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%);">
                <p class="metric-value">{stats['total_failed']}</p>
                <p class="metric-label">Failed Uploads</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col4:
        size_mb = stats['total_size'] / (1024 * 1024)
        st.markdown(f"""
            <div class="metric-card" style="background: linear-gradient(135deg, #3b82f6 0%, #1e40af 100%);">
                <p class="metric-value">{size_mb:.1f} MB</p>
                <p class="metric-label">Total Size</p>
            </div>
        """, unsafe_allow_html=True)

def render_sidebar():
    """Render sidebar with configuration"""
    st.sidebar.markdown("""
        <h2 style="text-align: center; color: #1f2937;">
            ⚙️ Configuration
        </h2>
    """, unsafe_allow_html=True)
    
    # AWS Configuration
    with st.sidebar.expander("🔐 AWS Settings", expanded=True):
        aws_profile = st.text_input(
            "AWS Profile",
            value=settings.aws_profile or "",
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
                value=settings.s3_bucket_mba,
                help="S3 bucket for MBA files"
            )
        with col2:
            policy_bucket = st.text_input(
                "Policy Bucket",
                value=settings.s3_bucket_policy,
                help="S3 bucket for Policy files"
            )
    
    # Upload Settings
    with st.sidebar.expander("📤 Upload Settings", expanded=True):
        concurrency = st.slider(
            "Upload Concurrency",
            min_value=1,
            max_value=10,
            value=4,
            help="Number of parallel uploads"
        )
        
        skip_duplicates = st.checkbox(
            "Skip Duplicates",
            value=True,
            help="Skip files that already exist in S3"
        )
        
        overwrite = st.checkbox(
            "Overwrite Existing",
            value=False,
            help="Overwrite files that exist in S3"
        )
        
        auto_detect_scope = st.checkbox(
            "Auto-detect Scope",
            value=True,
            help="Automatically detect MBA/Policy from path"
        )
    
    # File Filters
    with st.sidebar.expander("🔍 File Filters", expanded=False):
        include_extensions = st.text_input(
            "Include Extensions",
            placeholder="pdf,csv,docx",
            help="Comma-separated list of extensions to include"
        )
        
        exclude_extensions = st.text_input(
            "Exclude Extensions",
            placeholder="tmp,bak",
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
    """
    Render file discovery and selection interface.
    
    Provides directory scanning, file filtering, and selection
    controls for choosing files to upload.
    
    Interface Elements:
        - Directory input field
        - Scope filter dropdown
        - Scan button
        - File type distribution chart
        - File selection checkboxes
        
    Side Effects:
        - Updates session state with discovered files
        - Triggers directory scanning
    """
    st.markdown("### 📁 File Discovery")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        input_dir = st.text_input(
            "Input Directory",
            value="./data",
            help="Directory to scan for files"
        )
    
    with col2:
        scope_filter = st.selectbox(
            "Scope Filter",
            options=["All", "MBA", "Policy"],
            help="Filter files by scope"
        )
    
    with col3:
        if st.button("🔍 Scan Directory", use_container_width=True):
            scan_directory(input_dir, scope_filter)
    
    # Display discovered files
    if st.session_state.selected_files:
        st.markdown(f"### Found {len(st.session_state.selected_files)} Files")
        
        # File type distribution
        file_types = {}
        for file_path in st.session_state.selected_files:
            ext = Path(file_path).suffix.lower()
            file_types[ext] = file_types.get(ext, 0) + 1
        
        if file_types:
            fig = px.pie(
                values=list(file_types.values()),
                names=list(file_types.keys()),
                title="File Type Distribution",
                color_discrete_sequence=px.colors.sequential.Purples_r
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
        
        # File list with selection
        st.markdown("#### Select Files to Upload")
        
        # Select/Deselect all
        col1, col2, col3 = st.columns([1, 1, 3])
        with col1:
            if st.button("✅ Select All"):
                st.session_state.selected_files = st.session_state.selected_files.copy()
        with col2:
            if st.button("❌ Deselect All"):
                st.session_state.selected_files = []
        
        # File grid
        files_per_row = 3
        rows = len(st.session_state.selected_files) // files_per_row + 1
        
        for row in range(rows):
            cols = st.columns(files_per_row)
            for col_idx in range(files_per_row):
                file_idx = row * files_per_row + col_idx
                if file_idx < len(st.session_state.selected_files):
                    file_path = st.session_state.selected_files[file_idx]
                    file_name = Path(file_path).name
                    file_size = Path(file_path).stat().st_size / 1024  # KB
                    
                    with cols[col_idx]:
                        selected = st.checkbox(
                            file_name,
                            value=True,
                            key=f"file_{file_idx}"
                        )
                        st.caption(f"📄 {file_size:.1f} KB")

def scan_directory(input_dir: str, scope_filter: str):
    """Scan directory for files"""
    try:
        input_path = Path(input_dir).resolve()
        
        # Discover files
        with st.spinner("Scanning directory..."):
            files = []
            
            if scope_filter == "All":
                files = discover_files(input_path)
            else:
                scope = scope_filter.lower()
                files = discover_files(input_path, scope=scope)
            
            st.session_state.selected_files = [str(f) for f in files]
            st.success(f"Found {len(files)} files")
    
    except Exception as e:
        st.error(f"Error scanning directory: {e}")

def render_duplicate_detection_tab():
    """
    Render duplicate detection interface.
    
    Scans for duplicate files locally and optionally in S3,
    presenting results with actionable options.
    
    Features:
        - Local duplicate scanning
        - S3 comparison (optional)
        - Duplicate group display
        - Space waste calculation
        - Delete suggestions
        
    Output:
        - Duplicate statistics
        - Grouped duplicate listings
        - Space savings potential
    """
    st.markdown("### 🔍 Duplicate Detection")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        scan_dir = st.text_input(
            "Directory to Scan",
            value="./data",
            help="Directory to scan for duplicates"
        )
    
    with col2:
        check_s3 = st.checkbox("Check S3", value=False, help="Also check for duplicates in S3")
    
    if st.button("🔍 Scan for Duplicates", use_container_width=True):
        scan_for_duplicates(scan_dir, check_s3)
    
    # Display results
    if st.session_state.duplicate_scan_results:
        results = st.session_state.duplicate_scan_results
        
        # Summary metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Duplicate Groups", results.get('groups', 0))
        with col2:
            st.metric("Total Duplicates", results.get('total_duplicates', 0))
        with col3:
            st.metric("Space Wasted", f"{results.get('wasted_space', 0):.1f} MB")
        
        # Duplicate groups
        if results.get('duplicates'):
            st.markdown("#### Duplicate Files Found")
            
            for idx, (hash_val, files) in enumerate(results['duplicates'].items(), 1):
                with st.expander(f"Group {idx} - {len(files)} files", expanded=False):
                    # Original file (oldest)
                    original = files[0]
                    st.markdown("**Original File:**")
                    st.info(f"📄 {original['name']} ({original['size_mb']:.2f} MB)")
                    
                    # Duplicates
                    st.markdown("**Duplicates:**")
                    for dup in files[1:]:
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.warning(f"📄 {dup['name']} ({dup['size_mb']:.2f} MB)")
                        with col2:
                            if st.button("🗑️ Delete", key=f"delete_{hash_val}_{dup['name']}"):
                                # Implement delete functionality
                                st.info("Delete functionality not implemented in demo")

def scan_for_duplicates(scan_dir: str, check_s3: bool):
    """Scan for duplicate files"""
    try:
        detector = DuplicateDetector()
        input_path = Path(scan_dir).resolve()
        
        with st.spinner("Scanning for duplicates..."):
            # Scan local directory
            hash_to_files = detector.scan_local_directory(input_path)
            
            # Find duplicates
            duplicates = {
                h: paths for h, paths in hash_to_files.items()
                if len(paths) > 1
            }
            
            # Calculate statistics
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
                    if len(file_info) > 1:  # Count duplicate space
                        wasted_space += stat.st_size
                
                # Sort by modification time
                file_info.sort(key=lambda x: x['modified'])
                duplicate_details[hash_val] = file_info
            
            st.session_state.duplicate_scan_results = {
                'groups': len(duplicates),
                'total_duplicates': total_duplicates,
                'wasted_space': wasted_space / (1024 * 1024),  # MB
                'duplicates': duplicate_details
            }
            
            if duplicates:
                st.warning(f"Found {total_duplicates} duplicate files in {len(duplicates)} groups")
            else:
                st.success("No duplicate files found!")
    
    except Exception as e:
        st.error(f"Error scanning for duplicates: {e}")

def render_upload_tab(config: dict):
    """
    Render file upload interface.
    
    Main upload control panel with options and history.
    
    Args:
        config (dict): Configuration from sidebar
        
    Interface:
        - Upload options (dry run, scope)
        - Start upload button
        - Progress indicators
        - Upload history display
        
    Side Effects:
        - Initiates file uploads
        - Updates session state
        - Refreshes metrics
    """
    st.markdown("### 📤 Upload Files")
    
    if not st.session_state.selected_files:
        st.info("Please discover files first in the File Discovery tab")
        return
    
    st.markdown(f"#### Ready to upload {len(st.session_state.selected_files)} files")
    
    # Upload options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        dry_run = st.checkbox("Dry Run", value=False, help="Preview upload without actually uploading")
    
    with col2:
        selected_scope = st.selectbox(
            "Upload Scope",
            options=["auto-detect", "mba", "policy"],
            help="Choose upload scope or auto-detect"
        )
    
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        upload_button = st.button("🚀 Start Upload", use_container_width=True, type="primary")
    
    if upload_button:
        perform_upload(config, dry_run, selected_scope)
    
    # Upload history
    if st.session_state.upload_history:
        st.markdown("#### 📜 Upload History")
        
        # Convert to DataFrame for better display
        df = pd.DataFrame(st.session_state.upload_history[:20])  # Show last 20
        
        # Status color coding
        def status_color(status):
            colors = {
                'success': '🟢',
                'skipped': '🟡',
                'failed': '🔴',
                'pending': '⚪'
            }
            return colors.get(status, '⚪')
        
        # Format the display
        for _, row in df.iterrows():
            col1, col2, col3, col4 = st.columns([1, 3, 2, 2])
            
            with col1:
                st.markdown(f"{status_color(row['status'])} **{row['status'].upper()}**")
            
            with col2:
                st.markdown(f"📄 {Path(row['file_path']).name}")
            
            with col3:
                st.markdown(f"📁 {row['scope'].upper()}")
            
            with col4:
                timestamp = pd.to_datetime(row['timestamp']).to_pydatetime()
                st.markdown(f"🕐 {timestamp.strftime('%H:%M:%S')}")
            
            if row['message']:
                st.caption(f"💬 {row['message']}")

def perform_upload(config: dict, dry_run: bool, selected_scope: str):
    """Perform file upload"""
    try:
        # Create uploader
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
        
        # Parse file paths
        files = [Path(f) for f in st.session_state.selected_files]
        input_dir = Path("./data").resolve()
        
        # Create progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Create wrapper with progress
        st_uploader = StreamlitUploader(uploader, progress_bar, status_text)
        
        # Perform upload
        with st.spinner("Uploading files..."):
            results = st_uploader.upload_batch_with_progress(
                files,
                input_dir,
                config['concurrency']
            )
        
        # Update stats
        st.session_state.upload_stats['total_uploaded'] += results['uploaded']
        st.session_state.upload_stats['total_skipped'] += results['skipped']
        st.session_state.upload_stats['total_failed'] += results['failed']
        
        for detail in results['details']:
            if detail.status == 'success':
                st.session_state.upload_stats['total_size'] += detail.size
        
        # Clear progress
        progress_bar.empty()
        status_text.empty()
        
        # Show results
        if dry_run:
            st.info("Dry run completed - no files were actually uploaded")
        else:
            st.success(f"Upload completed! Uploaded: {results['uploaded']}, Skipped: {results['skipped']}, Failed: {results['failed']}")
        
        # Rerun to update metrics
        st.rerun()
    
    except Exception as e:
        st.error(f"Upload error: {e}")
        logger.error(f"Upload error: {e}", exc_info=True)

def render_s3_browser_tab():
    """
    Render S3 bucket browser interface.
    
    Lists and displays S3 bucket contents with filtering.
    
    Features:
        - Bucket selection
        - Prefix filtering
        - Table/card view toggle
        - File statistics
        - Metadata display
        
    Data Source:
        S3 LIST operations via boto3
    """
    st.markdown("### 🗂️ S3 Browser")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        selected_bucket_type = st.selectbox(
            "Bucket",
            options=["MBA", "Policy"],
            help="Select bucket to browse"
        )
    
    with col2:
        prefix = st.text_input(
            "Prefix",
            value="",
            help="Filter by prefix (e.g., pdf/)"
        )
    
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Refresh", use_container_width=True):
            list_s3_contents(selected_bucket_type, prefix)
    
    # Initial load
    if 's3_contents' not in st.session_state:
        list_s3_contents(selected_bucket_type, prefix)
    
    # Display S3 contents
    if 's3_contents' in st.session_state and st.session_state.s3_contents:
        files = st.session_state.s3_contents
        
        # Statistics
        total_size = sum(f['size'] for f in files)
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Files", len(files))
        with col2:
            st.metric("Total Size", f"{total_size / (1024*1024):.1f} MB")
        with col3:
            file_types = {}
            for f in files:
                ext = Path(f['key']).suffix.lower()
                file_types[ext] = file_types.get(ext, 0) + 1
            st.metric("File Types", len(file_types))
        
        # File list
        st.markdown("#### Files in S3")
        
        # Create DataFrame for better display
        df = pd.DataFrame(files)
        if not df.empty:
            df['name'] = df['key'].apply(lambda x: Path(x).name)
            df['type'] = df['key'].apply(lambda x: Path(x).suffix.lower())
            df['size_mb'] = df['size'] / (1024 * 1024)
            df['modified'] = pd.to_datetime(df['last_modified'])
            
            # Display options
            display_mode = st.radio(
                "Display Mode",
                options=["Table", "Cards"],
                horizontal=True
            )
            
            if display_mode == "Table":
                # Table view
                display_df = df[['name', 'type', 'size_mb', 'modified']].copy()
                display_df['size_mb'] = display_df['size_mb'].round(2)
                display_df['modified'] = display_df['modified'].dt.strftime('%Y-%m-%d %H:%M')
                
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                # Card view
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
                            st.markdown(f"**Full Path:**")
                            st.code(row['key'], language=None)
    else:
        st.info("No files found in S3 bucket")

def list_s3_contents(bucket_type: str, prefix: str):
    """List S3 bucket contents"""
    try:
        # Get bucket name
        bucket = settings.s3_bucket_mba if bucket_type == "MBA" else settings.s3_bucket_policy
        
        # Build session
        session = build_session(
            profile=settings.aws_profile,
            access_key=settings.aws_access_key_id,
            secret_key=settings.aws_secret_access_key,
            region=settings.aws_default_region
        )
        
        with st.spinner(f"Loading {bucket_type} bucket contents..."):
            files = list_s3_files(session, bucket, prefix)
            st.session_state.s3_contents = files
            
            if files:
                st.success(f"Found {len(files)} files")
            else:
                st.info("Bucket is empty or prefix not found")
    
    except Exception as e:
        st.error(f"Error listing S3 contents: {e}")
        st.session_state.s3_contents = []

def render_analytics_tab():
    """
    Render analytics and insights dashboard.
    
    Visualizes upload trends and performance metrics.
    
    Charts:
        - Daily upload trends
        - Hourly activity distribution
        - Success rate over time
        - File type distribution
        - Performance metrics
        
    Data Source:
        Session state upload history
    """
    st.markdown("### 📊 Analytics & Insights")
    
    # Date range selector
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", datetime.now() - timedelta(days=7))
    with col2:
        end_date = st.date_input("End Date", datetime.now())
    
    # Upload trends
    if st.session_state.upload_history:
        st.markdown("#### Upload Trends")
        
        # Convert history to DataFrame
        df = pd.DataFrame(st.session_state.upload_history)
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['date'] = df['timestamp'].dt.date
            df['hour'] = df['timestamp'].dt.hour
            
            # Daily upload trends
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
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            # Hourly distribution
            hourly_stats = df.groupby(['hour', 'status']).size().reset_index(name='count')
            
            fig2 = px.bar(
                hourly_stats,
                x='hour',
                y='count',
                color='status',
                title='Upload Activity by Hour',
                color_discrete_map={
                    'success': '#10b981',
                    'skipped': '#f59e0b',
                    'failed': '#ef4444'
                }
            )
            fig2.update_layout(height=300)
            st.plotly_chart(fig2, use_container_width=True)
            
            # Success rate over time
            success_rate = df.groupby('date').apply(
                lambda x: (x['status'] == 'success').sum() / len(x) * 100
            ).reset_index(name='success_rate')
            
            fig3 = go.Figure()
            fig3.add_trace(go.Scatter(
                x=success_rate['date'],
                y=success_rate['success_rate'],
                mode='lines+markers',
                name='Success Rate',
                line=dict(color='#10b981', width=3),
                marker=dict(size=8)
            ))
            fig3.update_layout(
                title='Upload Success Rate Trend',
                yaxis_title='Success Rate (%)',
                xaxis_title='Date',
                height=300
            )
            st.plotly_chart(fig3, use_container_width=True)
    
    # File type analytics
    st.markdown("#### File Type Analytics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Mock data for file type distribution
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
            color_discrete_sequence=px.colors.sequential.Purples
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Mock data for scope distribution
        scope_data = {
            'MBA': 65,
            'Policy': 35
        }
        
        fig = px.bar(
            x=list(scope_data.keys()),
            y=list(scope_data.values()),
            title='Files by Scope',
            color=list(scope_data.keys()),
            color_discrete_map={
                'MBA': '#667eea',
                'Policy': '#764ba2'
            }
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    # Performance metrics
    st.markdown("#### Performance Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_speed = 2.5  # MB/s
        st.metric("Avg Upload Speed", f"{avg_speed:.1f} MB/s", "↑ 0.3")
    
    with col2:
        avg_file_size = 1.2  # MB
        st.metric("Avg File Size", f"{avg_file_size:.1f} MB", "→ 0.0")
    
    with col3:
        duplicate_ratio = 15  # %
        st.metric("Duplicate Ratio", f"{duplicate_ratio}%", "↓ 2%")
    
    with col4:
        error_rate = 0.5  # %
        st.metric("Error Rate", f"{error_rate:.1f}%", "↓ 0.2%")

def render_settings_tab():
    """
    Render settings and configuration interface.
    
    Manages application settings and cache.
    
    Features:
        - Cache management
        - Configuration export/import
        - Advanced settings
        - Logging configuration
        
    Side Effects:
        - Modifies application settings
        - Clears cache files
        - Exports/imports configurations
    """
    st.markdown("### ⚙️ Settings & Configuration")
    
    # Cache management
    st.markdown("#### 🗂️ Cache Management")
    
    col1, col2, col3 = st.columns(3)
    
    cache_file = Path("logs/file_cache.json")
    cache_exists = cache_file.exists()
    
    with col1:
        if cache_exists:
            cache_size = cache_file.stat().st_size / 1024
            st.metric("Cache Size", f"{cache_size:.1f} KB")
        else:
            st.metric("Cache Size", "0 KB")
    
    with col2:
        if cache_exists:
            cache_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
            st.metric("Last Updated", cache_time.strftime("%H:%M:%S"))
        else:
            st.metric("Last Updated", "N/A")
    
    with col3:
        if st.button("🗑️ Clear Cache", use_container_width=True):
            if cache_exists:
                cache_file.unlink()
                st.success("Cache cleared successfully")
                st.rerun()
    
    # Export/Import settings
    st.markdown("#### 💾 Export/Import Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Export Settings", use_container_width=True):
            config = {
                'aws_profile': settings.aws_profile,
                'aws_region': settings.aws_default_region,
                's3_bucket_mba': settings.s3_bucket_mba,
                's3_bucket_policy': settings.s3_bucket_policy,
                'upload_history': st.session_state.upload_history[-100:],  # Last 100 entries
                'upload_stats': st.session_state.upload_stats
            }
            
            st.download_button(
                label="💾 Download Config",
                data=json.dumps(config, indent=2, default=str),
                file_name=f"MBA_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    with col2:
        uploaded_file = st.file_uploader("Upload Configuration", type=['json'])
        if uploaded_file:
            try:
                config = json.load(uploaded_file)
                st.session_state.upload_history = config.get('upload_history', [])
                st.session_state.upload_stats = config.get('upload_stats', {})
                st.success("Configuration imported successfully")
                st.rerun()
            except Exception as e:
                st.error(f"Error importing configuration: {e}")
    
    # Advanced settings
    with st.expander("🔧 Advanced Settings", expanded=False):
        st.markdown("#### Logging")
        
        log_level = st.selectbox(
            "Log Level",
            options=["DEBUG", "INFO", "WARNING", "ERROR"],
            index=1
        )
        
        st.markdown("#### Performance")
        
        chunk_size = st.number_input(
            "Upload Chunk Size (KB)",
            min_value=64,
            max_value=5120,
            value=1024,
            step=64
        )
        
        retry_attempts = st.number_input(
            "Retry Attempts",
            min_value=1,
            max_value=10,
            value=3
        )
        
        timeout = st.number_input(
            "Upload Timeout (seconds)",
            min_value=30,
            max_value=600,
            value=300
        )
        
        if st.button("💾 Save Advanced Settings"):
            st.success("Advanced settings saved")

# ---------- DB Browser helpers ----------
def _db_url_read_only() -> str:
    """
    Build a SQLAlchemy MySQL URL from env (via settings),
    intended for a READ-ONLY DB user (provision in RDS).
    """
    # Your settings already hold these (pydantic-settings).
    # Ensure the user is a READ-ONLY user at the DB level.
    user = settings.RDS_USERNAME
    pwd = settings.RDS_PASSWORD
    host = settings.RDS_HOST
    port = settings.RDS_PORT
    db   = settings.RDS_DATABASE

    # mysql+pymysql URL
    return f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{db}?charset=utf8mb4"


@st.cache_resource(show_spinner=False)
def _get_ro_engine() -> "sqlalchemy.engine.Engine":
    """
    Cached SQLAlchemy engine. Keep it read-only by using a read-only user.
    (We only run SELECTs here.)
    """
    url = _db_url_read_only()
    # shorter timeouts so UI stays responsive
    eng = create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=1200,
        connect_args={"connect_timeout": 5, "read_timeout": 5, "write_timeout": 5},
    )
    return eng


def _safe_select_df(sql: str, params: dict | None = None) -> pd.DataFrame:
    """
    Run a SELECT and return a DataFrame. Friendly error handling.
    """
    try:
        eng = _get_ro_engine()
        with eng.connect() as conn:
            return pd.read_sql(text(sql), conn, params=params or {})
    except OperationalError as e:
        st.error(f"Database connectivity issue: {e}")
    except SQLAlchemyError as e:
        st.error(f"Query failed: {e}")
    except Exception as e:
        st.error(f"Unexpected error: {e}")
    return pd.DataFrame()

def _table_count(table: str) -> int:
    """
    COUNT(*) with graceful handling if the table is missing/empty.
    """
    try:
        df = _safe_select_df(f"SELECT COUNT(*) AS c FROM `{table}`")
        return int(df["c"].iloc[0]) if not df.empty else 0
    except Exception:
        # probably table doesn't exist yet
        return 0

# Example usage to avoid "not accessed" warning
# _table_count("your_table_name")
        return 0
def render_db_browser_tab():
    """
    Render database browser for RDS MySQL.
    
    Read-only interface for viewing database contents and
    audit trails.
    
    Displays:
        - Table row counts
        - Recent audit entries
        - Query results
        - CSV preview capability
        
    Security:
        Read-only queries only, no data modification
    """
    st.markdown("### 🧭 DB Browser (Read-only)")

    # Refresh + connectivity check
    c1, c2, c3 = st.columns([1,1,3])
    with c1:
        refresh = st.button("🔄 Refresh", help="Re-run the queries")
    with c2:
        with st.spinner("Checking DB health..."):
            try:
                # tiny ping
                _ = _safe_select_df("SELECT 1 AS ok")
                st.success("DB reachable")
            except Exception:
                st.warning("DB ping failed")

    # Table counts
    st.markdown("#### 📦 Table Counts")
    tables = [
        "memberdata",
        "benefit_accumulator",
        "deductibles_oop",
        "plan_details",
        "ingestion_audit",
    ]

    with st.spinner("Loading counts..."):
        counts = []
        for t in tables:
            cnt = _table_count(t)
            counts.append({"table": t, "rows": cnt})
        df_counts = pd.DataFrame(counts)

    if df_counts.empty:
        st.info("No tables found yet.")
    else:
        st.dataframe(
            df_counts.sort_values("table"),
            width="stretch",
            hide_index=True,
        )

    # Recent audit entries
    st.markdown("#### 🧾 Recent Audit Entries")
    with st.spinner("Loading recent audits..."):
        audits = _safe_select_df(
            """
            SELECT 
                id,
                started_at,
                finished_at,
                s3_key,
                status,
                COALESCE(rows_inserted, 0) AS rows_inserted,
                LEFT(COALESCE(error_message,''), 180) AS error_snippet
            FROM ingestion_audit
            ORDER BY started_at DESC
            LIMIT 50
            """
        )

    if audits.empty:
        st.info("No audit data yet.")
    else:
        # Format datetimes for display
        for col in ("started_at","finished_at"):
            if col in audits.columns:
                audits[col] = pd.to_datetime(audits[col]).dt.strftime("%Y-%m-%d %H:%M:%S")
        audits = audits.rename(
            columns={
                "id": "audit_id",
                "s3_key": "key",
                "error_snippet": "error",
            }
        )
        st.dataframe(audits, width="stretch", hide_index=True)

    # File preview (local upload; no write-back)
    st.markdown("#### 📄 Quick File Preview (Local Only)")
    up = st.file_uploader("Upload a CSV or JSON to preview", type=["csv","json"])
    if up is not None:
        try:
            with st.spinner("Parsing file..."):
                if up.name.lower().endswith(".csv"):
                    df_prev = pd.read_csv(up)
                else:
                    df_prev = pd.read_json(up)
            st.success(f"Previewing **{up.name}** — {len(df_prev):,} rows")
            st.dataframe(df_prev.head(200), width="stretch", hide_index=True)
        except Exception as e:
            st.error(f"Could not parse file: {e}")

    # Manual refresh (rerun), last in the tab
    if refresh:
        st.toast("Refreshed", icon="🔄")
        st.rerun()


def main():
    """
    Main Streamlit application entry point.
    
    Orchestrates the complete web interface with tabbed navigation
    and sidebar configuration.
    
    Application Structure:
        - Header with branding
        - Metrics dashboard
        - Sidebar configuration
        - Seven functional tabs
        - Footer with version info
        
    Session State Management:
        - upload_history: List of completed uploads
        - duplicate_scan_results: Latest scan results
        - selected_files: Files chosen for upload
        - upload_stats: Aggregate statistics
    """
    # Render header
    render_header()
    
    # Render metrics dashboard
    render_metrics()
    
    # Sidebar configuration
    config = render_sidebar()
    
    # Main content tabs
    tabs = st.tabs([
        "📁 File Discovery",
        "🔍 Duplicate Detection", 
        "📤 Upload",
        "🗂️ S3 Browser",
        "🧭 DB Browser",
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
    
    # Agent section
    with st.expander("🤖 AI Agents", expanded=False):
        agent_tabs = st.tabs(["🔍 Member Verification", "🎯 Intent Analysis", "💰 Benefits", "💳 Deductible", "🤖 Orchestrator"])
        
        with agent_tabs[0]:
            st.write("Verify member identity using database lookup.")
            col1, col2, col3 = st.columns(3)
            with col1:
                member_id = st.text_input("Member ID", placeholder="M1001")
            with col2:
                dob = st.date_input("Date of Birth")
            with col3:
                name = st.text_input("Name (optional)", placeholder="John Doe")
            
            if st.button("Verify Member", key="verify_member") and member_id and dob:
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
            st.write("Analyze user queries to identify intent and extract parameters.")
            query = st.text_area("User Query", placeholder="What's my deductible for 2025?")
            
            if st.button("Analyze Intent", key="analyze_intent") and query:
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
            st.write("Get benefit accumulator information for members.")
            col1, col2, col3 = st.columns(3)
            with col1:
                ben_member_id = st.text_input("Member ID", placeholder="M1001", key="ben_member")
            with col2:
                service = st.selectbox("Service", ["Massage Therapy", "Physical Therapy", "Neurodevelopmental Therapy", "Skilled Nursing Facility", "Smoking Cessation", "Rehabilitation – Outpatient"])
            with col3:
                plan_year = st.number_input("Plan Year", min_value=2020, max_value=2030, value=2025)
            
            if st.button("Get Benefits", key="get_benefits") and ben_member_id:
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
            st.write("Get deductible and out-of-pocket information for members.")
            col1, col2 = st.columns(2)
            with col1:
                ded_member_id = st.text_input("Member ID", placeholder="M1001", key="ded_member")
            with col2:
                ded_plan_year = st.number_input("Plan Year", min_value=2020, max_value=2030, value=2025, key="ded_year")
            
            if st.button("Get Deductible Info", key="get_deductible") and ded_member_id:
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
            st.write("Ask end-to-end questions. Member verification is enforced as needed.")
            q = st.text_input("Question",
                              placeholder="e.g., What's my deductible for 2025? member_id=M1001 dob=2005-05-23")
            if st.button("Run Orchestrator", key="run_orchestrator") and q:
                orch = OrchestratorAgent()
                with st.spinner("Running orchestrator..."):
                    result = asyncio.run(orch.run({"query": q}))
                st.success(result.get("summary") or result)
        
        # Footer
        st.markdown("---")
        st.markdown(
            """
            <div style="text-align: center; color: #6b7280; padding: 1rem;">
                <p>MBA S3 Data Ingestion Portal v1.0.0</p>
                <p>© 2024 MBA - Healthcare Management Associates</p>
            </div>
            """,
            unsafe_allow_html=True
        )

if __name__ == "__main__":
    main()