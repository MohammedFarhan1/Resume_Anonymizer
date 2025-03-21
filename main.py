import os
import tempfile
import fitz  # PyMuPDF
import streamlit as st
import requests
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from threading import Thread
from groq import Groq
from dotenv import load_dotenv
from streamlit_lottie import st_lottie
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask App with updated CORS
app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Accept"],
        "expose_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True,
        "max_age": 120
    }
})

# Load environment variables
load_dotenv()

# Load API Key from Environment Variable
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("Missing GROQ API Key! Set it in environment variables.")

# Initialize Groq client
client = Groq(api_key=GROQ_API_KEY)

# Function to extract text from PDF
def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = "\n".join(page.get_text() for page in doc)
    return text

@app.route("/process", methods=["POST", "OPTIONS"])
def process_pdf():
    # Handle CORS preflight requests
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
        response.headers.add("Access-Control-Allow-Methods", "POST,OPTIONS")
        return response

    temp_file = None
    try:
        logger.debug("Received request to /process endpoint")
        logger.debug(f"Request headers: {dict(request.headers)}")
        
        if 'file' not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
        
        file = request.files['file']
        
        if file.filename == "":
            return jsonify({"error": "No selected file"}), 400
        
        # Add content type check
        if not file.content_type == 'application/pdf':
            return jsonify({"error": "Invalid file type. Please upload a PDF file"}), 400
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            file.save(temp_file.name)
            text = extract_text_from_pdf(temp_file.name)
        
        # Send text to Groq API for anonymization
        prompt = f"""
        Please anonymize the following text by removing or replacing:
        1. Names
        2. Phone numbers
        3. Email addresses
        4. Physical addresses
        5. Dates of birth
        6. Social security numbers
        7. Any other personally identifiable information
        
        Here's the text to anonymize:
        {text}
        """
        
        response = client.chat.completions.create(
            model="mixtral-8x7b-32768-v0.1-groq",
            messages=[{
                "role": "system",
                "content": "You are an expert at anonymizing documents while preserving their professional context."
            },
            {
                "role": "user",
                "content": prompt
            }]
        )
        cleaned_text = response.choices[0].message.content.strip()
        
        return jsonify({"cleaned_text": cleaned_text})
    
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
    finally:
        if temp_file and os.path.exists(temp_file.name):
            os.remove(temp_file.name)

# Start Flask Server in a Separate Thread
def run_flask():
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)

# Set page config first, before any other Streamlit commands
st.set_page_config(
    page_title="PDF Text Anonymizer",
    page_icon="🔒",
    layout="wide"
)

def main():
    # Ensure the Flask server runs only once
    if 'flask_thread' not in st.session_state:
        st.session_state.flask_thread = Thread(target=run_flask, daemon=True)
        st.session_state.flask_thread.start()
    
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

    # Page Layout
    col1, col2, col3 = st.columns([1,2,1])

    with col2:
        st.title("📄 Resume Anonymizer")
        
        # Information cards
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
                progress_bar = st.progress(0)
                
                try:
                    # Save uploaded file temporarily
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                        temp_file.write(uploaded_file.getvalue())
                        temp_file_path = temp_file.name
                        progress_bar.progress(30)

                    # Send file to backend
                    with open(temp_file_path, "rb") as f:
                        files = {
                            "file": (
                                uploaded_file.name,
                                f,
                                "application/pdf"
                            )
                        }
                        
                        response = requests.post(
                            "http://127.0.0.1:5000/process",
                            files=files,
                            headers={
                                "Accept": "application/json",
                                "Access-Control-Allow-Origin": "*"
                            }
                        )
                        
                        progress_bar.progress(70)
                        
                        if response.status_code == 200:
                            progress_bar.progress(100)
                            result = response.json()
                            
                            # Success message
                            st.markdown("<div class='success-message'>✅ Document processed successfully!</div>", 
                                      unsafe_allow_html=True)
                            
                            # Display results
                            st.markdown("### 📝 Anonymized Text")
                            st.text_area("", result["cleaned_text"], height=300)
                            
                            # Download button
                            st.download_button(
                                label="📥 Download Anonymized Text",
                                data=result["cleaned_text"],
                                file_name="anonymized_text.txt",
                                mime="text/plain"
                            )
                        else:
                            st.error(f"Error: {response.status_code} - {response.text}")
                            logger.error(f"Server response: {response.text}")
                
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
                    logger.error(f"Processing error: {str(e)}")
                
                finally:
                    # Clean up temporary file
                    if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                        os.remove(temp_file_path)

        st.markdown("</div>", unsafe_allow_html=True)
        
        # Footer
        st.markdown("""
        <div style='text-align: center; margin-top: 2rem; padding: 1rem; color: #6c757d;'>
            <p>Made with ❤️ for privacy and security</p>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
