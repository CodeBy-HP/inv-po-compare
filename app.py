import streamlit as st
from components.file_uploader import file_upload_component
from components.result_display import display_gemini_results, display_raw_json
from utils.excel_extractor import extract_excel_info
from utils.word_extractor import extract_word_info
from utils.pdf_extractor import extract_pdf_info
from utils.gemini_processor import GeminiProcessor

st.set_page_config(page_title="Document Info Extractor", layout="wide")
st.title("🔍 Document Info Extractor")
st.write("Upload Excel, Word, or PDF files for AI-powered contextual analysis and structuring")

uploaded_file = file_upload_component()

if uploaded_file:
    st.success(f"File '{uploaded_file.name}' uploaded successfully.")
    
    # Determine file type and extract accordingly
    file_name_lower = uploaded_file.name.lower()
    extracted_info = None
    document_type = None
    
    if file_name_lower.endswith((".xlsx", ".xls")):
        document_type = "Excel"
        st.info("📈 Step 1: Extracting Excel data...")
        with st.spinner("Analyzing Excel file structure..."):
            extracted_info = extract_excel_info(uploaded_file)
    
    elif file_name_lower.endswith((".docx", ".doc")):
        document_type = "Word"
        st.info("� Step 1: Extracting Word document data...")
        with st.spinner("Analyzing Word document structure..."):
            extracted_info = extract_word_info(uploaded_file)
    
    elif file_name_lower.endswith(".pdf"):
        document_type = "PDF"
        st.info("📑 Step 1: Extracting PDF data...")
        with st.spinner("Analyzing PDF document structure..."):
            extracted_info = extract_pdf_info(uploaded_file)
    
    else:
        st.error("❌ Unsupported file format. Please upload Excel (.xlsx, .xls), Word (.docx, .doc), or PDF files.")
    
    # Process the extracted data if successful
    if extracted_info and not extracted_info.get("error"):
        st.success(f"✅ {document_type} data extracted successfully!")
        
        # Step 2: Send to Gemini for contextual structuring
        st.info("🤖 Step 2: Sending to Gemini AI for contextual analysis...")
        
        gemini_processor = GeminiProcessor()
        
        with st.spinner("AI is analyzing your data contextually..."):
            gemini_response = gemini_processor.structure_document_data(extracted_info, document_type)
        
        if gemini_response.get("success"):
            st.success("✅ AI analysis completed successfully!")
            
            # Display the structured results
            display_gemini_results(gemini_response)
            
            # Option to view raw data
            st.subheader("🔧 Debug Information")
            col1, col2 = st.columns(2)
            with col1:
                display_raw_json(extracted_info, f"Original {document_type} Data")
            with col2:
                display_raw_json(gemini_response, "Gemini AI Response")
        
        else:
            st.error("❌ AI analysis failed")
            display_gemini_results(gemini_response)  # This will show error details
            
            # Show original extracted data as fallback
            st.subheader(f"📊 Fallback: Original {document_type} Data")
            display_raw_json(extracted_info, f"Original {document_type} Data")
    
    elif extracted_info and extracted_info.get("error"):
        st.error(f"❌ Failed to extract {document_type} data. Check console for details.")
        display_raw_json(extracted_info, f"Error Details")
else:
    st.info("Please upload an Excel, Word, or PDF file to get started.")

