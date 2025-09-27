# src/MBA/app_launcher.py
def main():
    """
    Starts Streamlit for the MBA app by resolving the module file path and
    invoking 'streamlit run <file>'. This avoids the '-m' flag (not supported).
    """
    import sys
    from importlib import import_module
    from streamlit.web.cli import main as stcli

    # Import the module to get its __file__ on disk
    module = import_module("MBA.streamlit_app")
    script_path = module.__file__  # absolute path to streamlit_app.py

    # Build argv for 'streamlit run <file>'
    sys.argv = [
        "streamlit",
        "run",
        script_path,
        # Optional flags you can keep or remove:
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
    ]

    stcli()
