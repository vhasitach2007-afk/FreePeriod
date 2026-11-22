import streamlit as st
from supabase import create_client


def get_client():
    """Return a Supabase client scoped to the current Streamlit browser session.

    Do not cache this client globally: its auth session belongs to one signed-in user.
    """
    if "_supabase_client" not in st.session_state:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_ANON_KEY"]
        st.session_state["_supabase_client"] = create_client(url, key)
    return st.session_state["_supabase_client"]
