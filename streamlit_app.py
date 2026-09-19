"""
Streamlit Community Cloud entrypoint for Zomato AI Restaurant Recommender.
Enables 1-click deployment from GitHub at https://share.streamlit.io.
"""
import os
import sys

# Ensure project root is on sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Bridge Streamlit Cloud secrets into environment variables for app.config.Settings
try:
    import streamlit as st
    if hasattr(st, "secrets"):
        for key, val in st.secrets.items():
            if isinstance(val, str) and val.strip():
                os.environ[key] = val.strip()
                os.environ[key.upper()] = val.strip()
                os.environ[key.lower()] = val.strip()
except Exception:
    pass

from ui.streamlit_app import main

if __name__ == "__main__":
    main()
