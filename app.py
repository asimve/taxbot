import streamlit as st
import pandas as pd
import openai
import json
import pdfplumber
import io

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
uploaded_file = st.file_uploader("Upload your bank statement (CSV or PDF)", type=["csv", "pdf"])

# ---- Description Box ----
with st.expander("💬 Describe your income sources in your own words"):
    user_description = st.text_area("E.g. I am a freelancer working on Upwork and also earning rental income")

# ---- Submit Button ----nif st.button("🔍 Analyze My Tax Position"):
    with st.spinner("Preparing your tax analysis..."):
        # Validate upload
        if uploaded_file is None:
            st.warning("Please upload a CSV or PDF file before analyzing.")
            st.stop()

        # Read and parse uploaded file
        file_ext = uploaded_file.name.split('.')[-1].lower()
        try:
            if file_ext == 'csv':
                df = pd.read_csv(uploaded_file)
            elif file_ext == 'pdf':
                pdf_bytes = uploaded_file.read()
                tables = []
                with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                    for page in pdf.pages:
                        tbl = page.extract_table()
                        if tbl:
                            df_page = pd.DataFrame(tbl[1:], columns=tbl[0])
                            tables.append(df_page)
                if tables:
                    df = pd.concat(tables, ignore_index=True)
                else:
                    st.error("No tabular data found in the uploaded PDF.")
                    st.stop()
            else:
                st.error("Unsupported file type.")
                st.stop()

            st.success("Statement uploaded successfully!")
            st.dataframe(df.head())
        except Exception as e:
            st.error(f"Error processing file: {repr(e)}")
            st.stop()

        # Build prompt for OpenAI
        prompt = f"""
You are a smart Indian tax advisor AI.
User's income source is: {income_type}
GST Registered: {is_gst_registered}
State: {state}
Description: {user_description}

Analyze the uploaded bank/ledger data and suggest:
  - The correct ITR form
  - Key deductions applicable
  - Any red flags or alerts
Provide the answer concisely without disclaimers.
"""

        openai.api_key = st.secrets.get("OPENAI_API_KEY")
        if not openai.api_key:
            st.error("OPENAI_API_KEY not found in secrets. Please configure your app secrets.")
            st.stop()
        
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
            st.error(f"Error from OpenAI API: {repr(e)}")

# ---- Footer ----
st.markdown("---")
st.caption("DesiTaxBot is a prototype and helps prepare tax analysis only.")
