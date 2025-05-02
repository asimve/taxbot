import streamlit as st
import pandas as pd
import io
import pdfplumber
import openai
import requests

# ---- Setup ----
st.set_page_config(page_title="DesiTaxBot – Your Personal Tax Assistant")
st.title("🧾 DesiTaxBot – India's Personal CA")

# ---- Sidebar ----
st.sidebar.header("User Info")
income_type = st.sidebar.selectbox(
    "Income Source", ["Freelance", "Options Trading", "Salaried", "Rental Income", "Multiple"]
)
is_gst_registered = st.sidebar.radio("Are you GST Registered?", ["Yes", "No"])
state = st.sidebar.selectbox(
    "Your State", ["Delhi", "Maharashtra", "Karnataka", "Other"]
)

# ---- File Upload ----
st.header("📤 Upload Bank or Ledger Statement")
uploaded_file = st.file_uploader(
    "Upload your bank statement (CSV or PDF)", type=["csv", "pdf"]
)

# ---- PDF Encryption Pre-check ----
pdf_bytes = None
pdf_encrypted = False
pdf_password = None
if uploaded_file and uploaded_file.name.lower().endswith('.pdf'):
    pdf_bytes = uploaded_file.read()
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)):
            pass
    except Exception as e:
        err = repr(e).lower()
        if 'password' in err or 'encrypted' in err:
            pdf_encrypted = True
        else:
            st.error(f"Error reading PDF: {e}")
            st.stop()
    if pdf_encrypted:
        pdf_password = st.text_input("This PDF is encrypted. Enter password:", type="password")

# ---- Income Description ----
with st.expander("💬 Describe your income sources in your own words"):
    user_description = st.text_area(
        "E.g. I am a freelancer working on Upwork and also earning rental income"
    )

# ---- Analyze Button ----
if st.button("🔍 Analyze My Tax Position"):
    with st.spinner("Preparing your tax analysis..."):
        # Validate upload
        if not uploaded_file:
            st.warning("Please upload a CSV or PDF file.")
            st.stop()

        # Parse file
        if uploaded_file.name.lower().endswith('.csv'):
            try:
                df = pd.read_csv(uploaded_file)
            except Exception as e:
                st.error(f"Error reading CSV: {e}")
                st.stop()
        else:
            if pdf_encrypted and not pdf_password:
                st.error("PDF password is required to extract data.")
                st.stop()
            try:
                with pdfplumber.open(io.BytesIO(pdf_bytes), password=pdf_password) as pdf:
                    tables = []
                    for page in pdf.pages:
                        tbl = page.extract_table()
                        if tbl:
                            tables.append(pd.DataFrame(tbl[1:], columns=tbl[0]))
                    if not tables:
                        st.error("No tabular data found in the PDF.")
                        st.stop()
                    df = pd.concat(tables, ignore_index=True)
            except Exception as e:
                st.error(f"Error processing PDF: {e}")
                st.stop()

        # Optional: filter last 3 months
        date_cols = [c for c in df.columns if isinstance(c, str) and 'date' in c.lower()]
        if date_cols:
            try:
                c = date_cols[0]
                df[c] = pd.to_datetime(df[c], errors='coerce')
                cutoff = pd.Timestamp.now() - pd.DateOffset(months=3)
                df = df[df[c] >= cutoff]
            except:
                pass

        st.success("Statement uploaded successfully!")
        st.dataframe(df.head())

        # Build LLM prompt
        prompt = f"""
You are a smart Indian tax advisor AI.
User's income source: {income_type}
GST Registered: {is_gst_registered}
State: {state}
Description: {user_description}
Provide:
- Correct ITR form
- Key deductions
- Any red flags
Based on last 3 months of transactions.
"""

        # Prepare clients
        openai_key = st.secrets.get("OPENAI_API_KEY")
        hf_token = st.secrets.get("HUGGINGFACE_TOKEN")

        answer = None

        # Try OpenAI
        if openai_key:
            client = openai.OpenAI(api_key=openai_key)
            try:
                resp = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role":"system","content":"You are a CA for Indian tax filers."},
                              {"role":"user","content":prompt}]
                )
                answer = resp.choices[0].message.content
            except Exception as oe:
                # Quota error
                if 'insufficient_quota' in repr(oe).lower():
                    st.warning("OpenAI quota exceeded.")
                else:
                    st.error(f"OpenAI error: {oe}")

        # Fallback to Hugging Face Inference
        if not answer and hf_token:
            try:
                headers = {"Authorization": f"Bearer {hf_token}"}
                json_data = {"inputs": prompt}
                r = requests.post(
                    "https://api-inference.huggingface.co/models/google/flan-t5-large",
                    headers=headers, json=json_data
                )
                if r.status_code == 200:
                    answer = r.json()[0]['generated_text']
                else:
                    st.error(f"HuggingFace API error {r.status_code}: {r.text}")
            except Exception as he:
                st.error(f"HuggingFace error: {he}")

        if not answer:
            st.error("No LLM available. Please configure an API key (OpenAI or Hugging Face).")
            st.stop()

        # Show answer
        st.markdown("---")
        st.subheader("🧾 Tax Summary")
        st.write(answer)

# Footer
st.markdown("---")
st.caption("DesiTaxBot prototype — requires valid LLM API key.")
