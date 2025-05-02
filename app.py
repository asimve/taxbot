import streamlit as st
import pandas as pd
import openai
import io
import pdfplumber

# ---- Setup ----
st.set_page_config(page_title="DesiTaxBot – Your Personal Tax Assistant")
st.title("🧾 DesiTaxBot – India's Personal CA")

# ---- Sidebar ----
st.sidebar.header("User Info")
income_type = st.sidebar.selectbox(
    "Income Source", 
    ["Freelance", "Options Trading", "Salaried", "Rental Income", "Multiple"]
)
is_gst_registered = st.sidebar.radio("Are you GST Registered?", ["Yes", "No"])
state = st.sidebar.selectbox(
    "Your State", 
    ["Delhi", "Maharashtra", "Karnataka", "Other"]
)

# ---- File Upload ----
st.header("📤 Upload Bank or Ledger Statement")
uploaded_file = st.file_uploader(
    "Upload your bank statement (CSV or PDF)", type=["csv", "pdf"]
)

# ---- Description Box ----
with st.expander("💬 Describe your income sources in your own words"):
    user_description = st.text_area(
        "E.g. I am a freelancer working on Upwork and also earning rental income"
    )

# ---- Submit Button ----
if st.button("🔍 Analyze My Tax Position"):
    with st.spinner("Preparing your tax analysis..."):
        # Ensure file uploaded
        if uploaded_file is None:
            st.warning("Please upload a CSV or PDF file before analyzing.")
            st.stop()

        # Determine file type
        file_ext = uploaded_file.name.split('.')[-1].lower()
        df = None

        # CSV handling
        if file_ext == 'csv':
            try:
                df = pd.read_csv(uploaded_file)
            except Exception as e:
                st.error(f"Error reading CSV: {e}")
                st.stop()

        # PDF handling
        elif file_ext == 'pdf':
            pdf_bytes = uploaded_file.read()
            success = False
            # Attempt without password
            try:
                with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                    tables = []
                    for page in pdf.pages:
                        tbl = page.extract_table()
                        if tbl:
                            tables.append(pd.DataFrame(tbl[1:], columns=tbl[0]))
                    if tables:
                        df = pd.concat(tables, ignore_index=True)
                        success = True
            except Exception as first_err:
                # If PDF is encrypted, prompt for password
                err_repr = repr(first_err).lower()
                if 'pdfpasswordincorrect' in err_repr or 'encrypted' in err_repr:
                    pwd = st.text_input(
                        "This PDF is encrypted. Enter password:", type="password"
                    )
                    if pwd:
                        try:
                            with pdfplumber.open(
                                io.BytesIO(pdf_bytes), password=pwd
                            ) as pdf:
                                tables = []
                                for page in pdf.pages:
                                    tbl = page.extract_table()
                                    if tbl:
                                        tables.append(pd.DataFrame(tbl[1:], columns=tbl[0]))
                                if tables:
                                    df = pd.concat(tables, ignore_index=True)
                                    success = True
                        except Exception as pwd_err:
                            st.error(f"Password incorrect or parsing failed: {pwd_err}")
                            st.stop()
                    else:
                        st.error("PDF password required to proceed.")
                        st.stop()
                else:
                    st.error(f"Error processing PDF: {first_err}")
                    st.stop()

            if not success:
                st.error("No tabular data found in the PDF.")
                st.stop()

        else:
            st.error("Unsupported file type. Please upload CSV or PDF.")
            st.stop()

        # Display parsed data
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

        # Initialize OpenAI client
        api_key = st.secrets.get("OPENAI_API_KEY")
        if not api_key:
            st.error("OPENAI_API_KEY not found in secrets. Please configure your app secrets.")
            st.stop()
        client = openai.OpenAI(api_key=api_key)

        # Call the API
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
        except Exception as api_err:
            st.error(f"OpenAI API error: {api_err}")

# ---- Footer ----
st.markdown("---")
st.caption("DesiTaxBot is a prototype and helps prepare tax analysis only.")
