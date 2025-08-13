import streamlit as st
from components.file_uploader import file_upload_component
from components.result_display import display_gemini_results, display_raw_json
from utils.excel_extractor import extract_excel_info
from utils.gemini_processor import GeminiProcessor

st.set_page_config(page_title="Document Info Extractor", layout="wide")
st.title("🔍 Document Info Extractor")
st.write("Upload Excel files for AI-powered contextual analysis and structuring")

uploaded_file = file_upload_component()

if uploaded_file:
    st.success(f"File '{uploaded_file.name}' uploaded successfully.")
    if uploaded_file.name.lower().endswith((".xlsx", ".xls")):
        
        # Step 1: Extract Excel data
        st.info("📈 Step 1: Extracting Excel data...")
        with st.spinner("Analyzing Excel file structure..."):
            extracted_info = extract_excel_info(uploaded_file)
        
        if extracted_info and not extracted_info.get("error"):
            st.success("✅ Excel data extracted successfully!")
            
            # Step 2: Send to Gemini for contextual structuring
            st.info("🤖 Step 2: Sending to Gemini AI for contextual analysis...")
            
            gemini_processor = GeminiProcessor()
            
            with st.spinner("AI is analyzing your data contextually..."):
                gemini_response = gemini_processor.structure_excel_data(extracted_info)
            
            if gemini_response.get("success"):
                st.success("✅ AI analysis completed successfully!")
                
                # Display the structured results
                display_gemini_results(gemini_response)
                
                # Option to view raw data
                st.subheader("🔧 Debug Information")
                col1, col2 = st.columns(2)
                with col1:
                    display_raw_json(extracted_info, "Original Excel Data")
                with col2:
                    display_raw_json(gemini_response, "Gemini AI Response")
            
            else:
                st.error("❌ AI analysis failed")
                display_gemini_results(gemini_response)  # This will show error details
                
                # Show original extracted data as fallback
                st.subheader("📊 Fallback: Original Excel Data")
                # Show basic summary
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Sheets", extracted_info["total_sheets"])
                with col2:
                    st.metric("File Name", extracted_info["file_name"])
                
                # Show sheet details
                for sheet_name, sheet_info in extracted_info["sheets"].items():
                    with st.expander(f"📋 Sheet: {sheet_name}"):
                        subcol1, subcol2 = st.columns(2)
                        with subcol1:
                            st.write(f"**Rows:** {sheet_info['total_rows']}")
                            st.write(f"**Columns:** {sheet_info['total_columns']}")
                        with subcol2:
                            st.write(f"**Column Names:** {', '.join(sheet_info['columns']['names'][:3])}{'...' if len(sheet_info['columns']['names']) > 3 else ''}")
        
        else:
            st.error("❌ Failed to extract Excel data. Check console for details.")
    else:
        st.info("📄 Currently only Excel files (.xlsx, .xls) are supported.")
else:
    st.info("Please upload a PDF, Excel, or Word file.")

