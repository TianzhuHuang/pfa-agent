"""Shared page utilities — auth gate + theme injection."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
from app.theme import inject_theme, theme_toggle
from app.auth import render_auth_sidebar


def page_init() -> dict:
    """Standard page initialization. Returns user dict.

    Injects theme, renders auth sidebar, stops page if not logged in.
    """
    inject_theme()
    user = render_auth_sidebar()
    theme_toggle()

    if not user.get("user_id"):
        st.warning("请先登录。")
        st.stop()

    return user
