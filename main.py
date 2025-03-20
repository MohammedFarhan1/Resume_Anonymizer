import os
import tempfile
import fitz  # PyMuPDF
import streamlit as st
import tempfile
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from threading import Thread
from groq import Groq
from streamlit_lottie import st_lottie

# Initialize Flask App
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend-backend communication

# Load API Key from Environment Variable
GROQ_API_KEY = "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"
if not GROQ_API_KEY:
    raise ValueError("Missing GROQ API Key! Set it in environment variables.")
client = Groq(api_key=GROQ_API_KEY)

# Function to extract text from PDF
def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = "\n".join(page.get_text() for page in doc)
    return text

# Flask Route to Process PDF and Remove Personal Info
@app.route("/process", methods=["POST"])
def process_pdf():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['file']
    
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        file.save(temp_file.name)
        text = extract_text_from_pdf(temp_file.name)
    
    os.remove(temp_file.name)  # Clean up temporary file
    
    # Send text to Groq API for anonymization
    prompt = f"Remove all personal information from this text:\n{text}"
    response = client.chat.completions.create(
        model="mixtral-8x7b-32768",
        messages=[{"role": "user", "content": prompt}],
    )
    cleaned_text = response.choices[0].message.content.strip()
    return jsonify({"cleaned_text": cleaned_text})

# Start Flask Server in a Separate Thread
def run_flask():
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)

# Ensure the Flask server runs only once
if 'flask_thread' not in st.session_state:
    st.session_state.flask_thread = Thread(target=run_flask, daemon=True)
    st.session_state.flask_thread.start()

# Streamlit UI
# Page configuration
st.set_page_config(
    page_title="PDF Text Anonymizer",
    page_icon="🔒",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stTitle {
        font-size: 3rem !important;
        color: #2E4057;
        text-align: center;
        margin-bottom: 2rem;
    }
    .upload-section {
        background-color: #f8f9fa;
        padding: 2rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stButton>button {
        background-color: #2E4057;
        color: white;
        border-radius: 5px;
        padding: 0.5rem 1rem;
        font-weight: 500;
    }
    .success-message {
        padding: 1rem;
        border-radius: 5px;
        background-color: #d4edda;
        color: #155724;
        margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)

# Load Lottie animation
def load_lottie_url(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

# Layout
col1, col2, col3 = st.columns([1,2,1])

with col2:
    st.title("📄 Resume Anonymizer")
    
    # Animation
    lottie_url = "https://assets5.lottiefiles.com/packages/lf20_sz683rqy.json"
    lottie_json = load_lottie_url(lottie_url)
    if lottie_json:
        st_lottie(lottie_json, height=200)

    # Information cards
# Replace the existing information cards section with this:
    st.markdown("""
    <div style='display: flex; justify-content: space-between; margin: 2rem 0;'>
        <div style='background: #2E4057; padding: 1rem; border-radius: 5px; flex: 1; margin: 0 0.5rem; color: white;'>
            <h4 style='color: #ffffff;'>🔒 Secure Processing</h4>
            <p style='color: #ffffff;'>Your documents are processed securely and deleted immediately after processing.</p>
        </div>
        <div style='background: #2E4057; padding: 1rem; border-radius: 5px; flex: 1; margin: 0 0.5rem; color: white;'>
            <h4 style='color: #ffffff;'>🤖 AI-Powered</h4>
            <p style='color: #ffffff;'>Advanced AI technology ensures accurate identification and anonymization of sensitive data.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)


    # File upload section
    st.markdown("<div class='upload-section'>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"], 
                                   help="Upload a PDF file to anonymize its contents")

    if uploaded_file is not None:
        with st.spinner("🔄 Processing your document..."):
            # Create progress bar
            progress_bar = st.progress(0)
            
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                temp_file.write(uploaded_file.getvalue())
                temp_file_path = temp_file.name
                progress_bar.progress(30)

            # Send file to backend
            try:
                with open(temp_file_path, "rb") as f:
                    files = {"file": f}
                    response = requests.post("http://127.0.0.1:5000/process", files=files)
                progress_bar.progress(70)
                
                os.remove(temp_file_path)  # Clean up temporary file
                
                if response.status_code == 200:
                    progress_bar.progress(100)
                    anonymized_text = response.json()["cleaned_text"]
                    
                    # Success message
                    st.markdown("<div class='success-message'>✅ Document processed successfully!</div>", 
                              unsafe_allow_html=True)
                    
                    # Results section
                    st.markdown("### 📝 Anonymized Text")
                    st.text_area("", anonymized_text, height=300)
                    
                    try:
                        # Download section
                        st.markdown("### 💾 Download Results")
                        txt_file = "anonymized_text.txt"
                        with open(txt_file, "w", encoding="utf-8") as f:
                            f.write(anonymized_text)
                        
                        with open(txt_file, "rb") as f:
                            st.download_button(
                                label="📥 Download Anonymized Text",
                                data=f,
                                file_name="anonymized_text.txt",
                                mime="text/plain",
                                key="download_button"
                            )
                        
                        os.remove(txt_file)  # Remove after downloading
                        
                        # Add Reset Button after download
                        if 'download_button' in st.session_state:
                            st.markdown("<br>", unsafe_allow_html=True)
                            
                            # Custom styling for reset button
                            st.markdown("""
                                <style>
                                div[data-testid="stButton"] button:last-child {
                                    background-color: #dc3545;
                                    color: white;
                                    border: none;
                                    padding: 0.5rem 1rem;
                                    font-weight: 500;
                                    width: 100%;
                                    margin-top: 1rem;
                                }
                                div[data-testid="stButton"] button:last-child:hover {
                                    background-color: #c82333;
                                }
                                </style>
                            """, unsafe_allow_html=True)
                            
                            if st.button("🔄 Reset Application", key="reset_button"):
                                # Clear file uploader
                                st.session_state['uploaded_file'] = None
                                
                                # Clear download button state
                                if 'download_button' in st.session_state:
                                    del st.session_state['download_button']
                                
                                # Remove temp file if exists
                                if os.path.exists("anonymized_text.txt"):
                                    os.remove("anonymized_text.txt")
                                
                                # Clear all other session state variables
                                for key in list(st.session_state.keys()):
                                    del st.session_state[key]
                                
                                # Rerun the app
                                st.experimental_rerun()
                            
                        # Footer
                        st.markdown("""
                        <div style='text-align: center; margin-top: 2rem; padding: 1rem; color: #6c757d;'>
                            <p>Made with ❤️ for privacy and security</p>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    except Exception as e:
                        st.error(f"❌ An error occurred: {str(e)}")
            except Exception as e:
                st.error(f"❌ An error occurred while processing the file: {str(e)}")
