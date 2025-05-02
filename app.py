import streamlit as st
import pandas as pd
import openai
import json

# ---- Setup ----
st.set_page_config(page_title="DesiTaxBot – Your Personal Tax Assistant")
st.title("🧾 DesiTaxBot – India's Personal CA")

# ---- Sidebar ----
st.sidebar.header("User Info")
income_type = st.sidebar.selectbox("Income Source", ["Freelance", "Options Trading", "Salaried", "Rental Income", "Multiple"])
is_gst_registered = st.sidebar.radio("Are you GST Registered?", ["Yes", "No"])
state = st.sidebar.selectbox("Your State", ["Delhi", "Maharashtra", "Karnataka", "Other"])

# ---- File Upload ----
st.header("📤 Upload Bank or Ledger Statement")
uploaded_file = st.file_uploader("Upload your bank statement (CSV preferred)", type=["csv"])

# ---- Description Box ----
with st.expander("💬 Describe your income sources in your own words"):
    user_description = st.text_area("E.g. I am a freelancer working on Upwork and also earning rental income")

# ---- Submit Button ----
if st.button("🔍 Analyze My Tax Position"):
    with st.spinner("Talking to CA..."):
        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)
                st.success("Statement uploaded successfully!")
                st.dataframe(df.head())
            except Exception as e:
                st.error(f"Error reading file: {e}")
                st.stop()
        
        # Build prompt for OpenAI
        prompt = f"""
        You are a smart Indian tax advisor AI.
        User's income source is: {income_type}
        GST Registered: {is_gst_registered}
        State: {state}
        Description: {user_description}

        Suggest applicable ITR form, key deductions, and red flags if any.
        Don't give legal disclaimers. Be direct.
        """

        openai.api_key = st.secrets["OPENAI_API_KEY"]

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a CA for Indian tax filers."},
                    {"role": "user", "content": prompt}
                ]
            )
            answer = response.choices[0].message.content
            st.markdown("---")
            st.subheader("🧾 Tax Summary")
            st.write(answer)
        except Exception as e:
            st.error(f"OpenAI error: {e}")

# ---- Footer ----
st.markdown("---")
st.caption("DesiTaxBot is a prototype and does not file taxes on your behalf (yet!).")
