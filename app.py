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

        filename = uploaded_file.name.lower()
        # Read CSV or PDF
        if filename.endswith('.csv'):
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

        # ---- Optional: Filter last 3 months ----
        date_cols = [col for col in df.columns if isinstance(col, str) and 'date' in col.lower()]
        if date_cols:
            try:
                col = date_cols[0]
                df[col] = pd.to_datetime(df[col], errors='coerce')
                cutoff = pd.Timestamp.now() - pd.DateOffset(months=3)
                df = df[df[col] >= cutoff]
            except Exception:
                pass

        # Show parsed data
        st.success("Statement uploaded successfully!")
        st.dataframe(df.head())

        # ---- Build Prompt ----
        prompt = f"""
You are a smart Indian tax advisor AI.
User's income source is: {income_type}
GST Registered: {is_gst_registered}
State: {state}
Description: {user_description}

Analyze the provided transactions (last 3 months if available) and suggest:
- Correct ITR form
- Key deductions
- Any red flags
Respond concisely.
"""

        # ---- OpenAI Call with Fallback on Quota ----
        api_key = st.secrets.get("OPENAI_API_KEY")
        if not api_key:
            st.error("OPENAI_API_KEY not found in secrets.")
            st.stop()
        client = openai.OpenAI(api_key=api_key)

        # Try GPT-3.5-turbo first
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a CA for Indian tax filers."},
                    {"role": "user", "content": prompt}
                ]
            )
            answer = response.choices[0].message.content
        except Exception as e:
            err = repr(e).lower()
            # Fallback to text-davinci-003 if quota exceeded
            if 'insufficient_quota' in err or 'rate limit' in err:
                st.info("GPT-3.5-turbo quota exceeded; falling back to text-davinci-003...")
                try:
                    resp2 = client.completions.create(
                        model="text-davinci-003",
                        prompt=prompt,
                        max_tokens=500
                    )
                    answer = resp2.choices[0].text.strip()
                except Exception as e2:
                    st.error(f"Fallback OpenAI API error: {e2}")
                    st.stop()
            else:
                st.error(f"OpenAI API error: {e}")
                st.stop()

        # Display answer
        st.markdown("---")
        st.subheader("🧾 Tax Summary")
        st.write(answer)

# ---- Footer ----
st.markdown("---")
st.caption("DesiTaxBot is a prototype and helps prepare tax analysis only.")
