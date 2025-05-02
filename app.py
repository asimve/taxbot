import streamlit as st
import pandas as pd
import io
import pdfplumber
import openai

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

# ---- Pre-process PDF encryption ----
pdf_bytes = None
pdf_encrypted = False
pdf_password = None
if uploaded_file and uploaded_file.name.lower().endswith('.pdf'):
    pdf_bytes = uploaded_file.read()
    try:
        # Try opening without password
        with pdfplumber.open(io.BytesIO(pdf_bytes)):
            pass
    except Exception as e:
        # Detect encryption error
        err = repr(e).lower()
        if 'password' in err or 'encrypted' in err:
            pdf_encrypted = True
        else:
            st.error(f"Error reading PDF: {e}")
            st.stop()
    if pdf_encrypted:
        pdf_password = st.text_input("This PDF is encrypted. Enter password:", type="password")

# ---- Description Box ----
with st.expander("💬 Describe your income sources in your own words"):
    user_description = st.text_area(
        "E.g. I am a freelancer working on Upwork and also earning rental income"
    )

# ---- Analyze Button ----
if st.button("🔍 Analyze My Tax Position"):
    with st.spinner("Preparing your tax analysis..."):
        # Validation
        if not uploaded_file:
            st.warning("Please upload a CSV or PDF file.")
            st.stop()

        filename = uploaded_file.name.lower()
        if filename.endswith('.csv'):
            try:
                df = pd.read_csv(uploaded_file)
            except Exception as e:
                st.error(f"Error reading CSV: {e}")
                st.stop()

        elif filename.endswith('.pdf'):
            # Require password if encrypted
            if pdf_encrypted and not pdf_password:
                st.error("PDF password is required to extract data.")
                st.stop()
            # Extract tables
            try:
                with pdfplumber.open(
                    io.BytesIO(pdf_bytes), password=pdf_password
                ) as pdf:
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

        else:
            st.error("Unsupported file type. Please upload a CSV or PDF.")
            st.stop()

        # Show parsed data
        st.success("Statement uploaded successfully!")
        st.dataframe(df.head())

        # Build LLM prompt
        prompt = f"""
You are a smart Indian tax advisor AI.
User's income source is: {income_type}
GST Registered: {is_gst_registered}
State: {state}
Description: {user_description}

Analyze the uploaded data and suggest:
- Correct ITR form
- Key deductions
- Any red flags
Respond concisely.
"""

        # OpenAI v1 client
        api_key = st.secrets.get("OPENAI_API_KEY")
        if not api_key:
            st.error("OPENAI_API_KEY not found in secrets.")
            st.stop()
        client = openai.OpenAI(api_key=api_key)

        try:
            response = client.chat.completions.create(
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
            st.error(f"OpenAI API error: {e}")

# ---- Footer ----
st.markdown("---")
st.caption("DesiTaxBot is a prototype and helps prepare tax analysis only.")
