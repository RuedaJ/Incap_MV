from __future__ import annotations

import streamlit as st


def init_state() -> None:
    if "portfolio_gdf" not in st.session_state:
        st.session_state["portfolio_gdf"] = None
    if "screen_results" not in st.session_state:
        st.session_state["screen_results"] = None


def get_state(key: str):
    return st.session_state.get(key)
