import streamlit as st
import pandas as pd
from datetime import date
from ..storage import load_df, add_rows

st.set_page_config(page_title="Lead Lab", page_icon="🎯")

st.title("🎯 Lead Lab — Research-only Entry")
st.caption("DBS Entertainment / The Scene Projects — local form for adding leads. No outreach.")

with st.form("lead_form", clear_on_submit=True):
    company = st.text_input("Company *")
    website = st.text_input("Website")
    contact = st.text_input("ContactName")
    role = st.text_input("Role")
    email = st.text_input("Email")
    category = st.selectbox("Category", ["Podcast","Zine","Network","Event","Other"], index=0)
    whyfit = st.text_area("WhyFit (short rationale)")
    source = st.text_input("SourceURL")
    notes = st.text_area("Notes")
    submitted = st.form_submit_button("Save lead")

if submitted:
    if not company.strip():
        st.error("Company is required.")
    else:
        row = {
            "Company": company.strip(),
            "Website": website.strip(),
            "ContactName": contact.strip(),
            "Role": role.strip(),
            "Email": email.strip(),
            "Category": category,
            "WhyFit": whyfit.strip(),
            "SourceURL": source.strip(),
            "Notes": notes.strip(),
            "Status": "New",
            "DateAdded": date.today().isoformat(),
        }
        add_rows([row])
        st.success("Lead saved locally.")

st.divider()

st.subheader("Current local leads")
df = load_df()
st.dataframe(df, use_container_width=True)