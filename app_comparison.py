import streamlit as st
from components.result_display import display_gemini_results, display_raw_json
from utils.excel_extractor import extract_excel_info
from utils.word_extractor import extract_word_info
from utils.pdf_extractor import extract_pdf_info
from utils.gemini_processor import GeminiProcessor

# Configure page
st.set_page_config(
    page_title="Invoice vs PO Analyzer", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Minimal header
st.markdown("""
<div style="text-align: center; padding: 1rem 0; border-bottom: 1px solid #ddd; margin-bottom: 2rem;">
    <h1 style="color: #2c3e50; margin: 0; font-weight: 300;">Invoice vs Purchase Order Analyzer</h1>
    <p style="color: #7f8c8d; margin: 0.5rem 0 0 0;">Automated discrepancy detection and comparison</p>
</div>
""", unsafe_allow_html=True)

# Streamlined upload section
st.markdown("### Upload Documents")
col1, col2 = st.columns(2)

with col1:
    invoice_file = st.file_uploader(
        "Invoice",
        type=["pdf", "xlsx", "xls", "docx", "doc"],
        key="invoice_upload"
    )

with col2:
    po_file = st.file_uploader(
        "Purchase Order",
        type=["pdf", "xlsx", "xls", "docx", "doc"],
        key="po_upload"
    )

def process_document(uploaded_file):
    """Helper function to process a document and return extracted data + type"""
    file_name_lower = uploaded_file.name.lower()
    
    if file_name_lower.endswith((".xlsx", ".xls")):
        return extract_excel_info(uploaded_file), "Excel"
    elif file_name_lower.endswith((".docx", ".doc")):
        return extract_word_info(uploaded_file), "Word"
    elif file_name_lower.endswith(".pdf"):
        return extract_pdf_info(uploaded_file), "PDF"
    else:
        return {"error": True, "message": "Unsupported file format"}, None

# Process files when both are uploaded
if invoice_file and po_file:
    st.success("✅ Both files uploaded successfully!")
    
    # Process Invoice
    st.info("🔄 Step 1: Processing Invoice...")
    invoice_extracted = None
    invoice_type = None
    
    with st.spinner("Extracting invoice data..."):
        invoice_extracted, invoice_type = process_document(invoice_file)
    
    if invoice_extracted and not invoice_extracted.get("error"):
        st.success(f"✅ Invoice data extracted ({invoice_type})")
        
        # 🐛 DEBUG: Show raw extracted invoice data
        with st.expander("🔍 DEBUG - Raw Invoice Extraction", expanded=False):
            st.subheader("Step 1A: Raw Invoice Data")
            st.json(invoice_extracted)
            if hasattr(invoice_extracted, 'keys'):
                st.write(f"**Data keys:** {list(invoice_extracted.keys())}")
                if 'sheets' in invoice_extracted:
                    for sheet_name, sheet_data in invoice_extracted['sheets'].items():
                        if 'all_data' in sheet_data:
                            st.write(f"**{sheet_name} - Total rows:** {len(sheet_data['all_data'])}")
        
        # Send invoice to Gemini for structuring
        with st.spinner("AI analyzing invoice..."):
            gemini_processor = GeminiProcessor()
            invoice_structured = gemini_processor.structure_document_data(invoice_extracted, invoice_type)
        
        if invoice_structured.get("success"):
            st.success("✅ Invoice structured by AI")
            
            # 🐛 DEBUG: Show structured invoice data
            with st.expander("🔍 DEBUG - Structured Invoice Data", expanded=False):
                st.subheader("Step 1B: AI Structured Invoice")
                structured_data = invoice_structured.get("data", {})
                st.json(structured_data)
                if 'documents' in structured_data:
                    for i, doc in enumerate(structured_data['documents']):
                        if 'line_items' in doc:
                            st.write(f"**Document {i+1} - Line items:** {len(doc['line_items'])}")
            
            # Process Purchase Order
            st.info("🔄 Step 2: Processing Purchase Order...")
            po_extracted = None
            po_type = None
            
            with st.spinner("Extracting PO data..."):
                po_extracted, po_type = process_document(po_file)
            
            if po_extracted and not po_extracted.get("error"):
                st.success(f"✅ PO data extracted ({po_type})")
                
                # 🐛 DEBUG: Show raw extracted PO data
                with st.expander("🔍 DEBUG - Raw PO Extraction", expanded=False):
                    st.subheader("Step 2A: Raw PO Data")
                    st.json(po_extracted)
                    if hasattr(po_extracted, 'keys'):
                        st.write(f"**Data keys:** {list(po_extracted.keys())}")
                        if 'sheets' in po_extracted:
                            for sheet_name, sheet_data in po_extracted['sheets'].items():
                                if 'all_data' in sheet_data:
                                    st.write(f"**{sheet_name} - Total rows:** {len(sheet_data['all_data'])}")
                
                # Send PO to Gemini for structuring
                with st.spinner("AI analyzing PO..."):
                    po_structured = gemini_processor.structure_document_data(po_extracted, po_type)
                
                if po_structured.get("success"):
                    st.success("✅ PO structured by AI")
                    
                    # 🐛 DEBUG: Show structured PO data
                    with st.expander("🔍 DEBUG - Structured PO Data", expanded=False):
                        st.subheader("Step 2B: AI Structured PO")
                        structured_data = po_structured.get("data", {})
                        st.json(structured_data)
                        if 'documents' in structured_data:
                            for i, doc in enumerate(structured_data['documents']):
                                if 'line_items' in doc:
                                    st.write(f"**Document {i+1} - Line items:** {len(doc['line_items'])}")
                    
                    # Step 3: Compare documents
                    st.info("🔄 Step 3: Comparing Invoice vs Purchase Order...")
                    
                    with st.spinner("AI comparing documents for discrepancies..."):
                        comparison_result = gemini_processor.compare_invoice_vs_po(
                            invoice_structured["data"], 
                            po_structured["data"]
                        )
                    
                    if comparison_result.get("success"):
                        st.success("✅ Comparison completed!")
                        
                        # 🐛 DEBUG: Show comparison input data and result
                        with st.expander("🔍 DEBUG - Comparison Process", expanded=False):
                            st.subheader("Step 3A: Data Sent to Comparison")
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write("**Invoice Data for Comparison:**")
                                st.json(invoice_structured["data"])
                            with col2:
                                st.write("**PO Data for Comparison:**")
                                st.json(po_structured["data"])
                            
                            st.subheader("Step 3B: Raw Comparison Response")
                            st.text(comparison_result.get("raw_response", "No raw response"))
                            
                            st.subheader("Step 3C: Processed Comparison Result")
                            st.json(comparison_result["data"])
                        
                        # Display comparison results
                        from components.comparison_display import display_comparison_results
                        
                        # 🐛 DEBUG: Show what we're passing to display
                        with st.expander("🔍 DEBUG - Data Flow to Display", expanded=False):
                            st.subheader("Full comparison_result structure:")
                            st.write(f"**Type:** {type(comparison_result)}")
                            st.write(f"**Keys:** {list(comparison_result.keys()) if isinstance(comparison_result, dict) else 'Not a dict'}")
                            st.json(comparison_result)
                            
                            st.subheader("Just the data portion:")
                            st.write(f"**Type:** {type(comparison_result['data'])}")
                            st.write(f"**Keys:** {list(comparison_result['data'].keys()) if isinstance(comparison_result['data'], dict) else 'Not a dict'}")
                            st.json(comparison_result["data"])
                        
                        # Pass the full result (includes format info) instead of just data
                        display_comparison_results(comparison_result)
                        
                        # Simplified debug section (moved detailed debug above)
                        with st.expander("🔧 Quick Debug Summary", expanded=False):
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.write("**Invoice Processing**")
                                st.write(f"Raw extraction: {invoice_type}")
                                st.write(f"AI success: {invoice_structured.get('success')}")
                            with col2:
                                st.write("**PO Processing**")
                                st.write(f"Raw extraction: {po_type}")
                                st.write(f"AI success: {po_structured.get('success')}")
                            with col3:
                                st.write("**Comparison**")
                                st.write(f"Success: {comparison_result.get('success')}")
                                st.write(f"Format: {comparison_result['data'].get('format', 'unknown')}")
                                display_raw_json(comparison_result, "Comparison Result")
                    
                    else:
                        st.error("❌ Comparison failed")
                        error_msg = comparison_result.get("error", "Unknown error")
                        st.error(error_msg)
                        
                        # Show debug info for troubleshooting
                        if "raw_response" in comparison_result:
                            with st.expander("🔍 Raw Response Debug"):
                                st.text(comparison_result["raw_response"][:2000])
                
                else:
                    st.error("❌ Failed to structure PO data")
                    error_msg = po_structured.get("error", "Unknown error")
                    st.error(error_msg)
                    
                    # Show debug info for troubleshooting
                    if "raw_response" in po_structured:
                        with st.expander("🔍 Raw Response Debug"):
                            st.text(po_structured["raw_response"][:2000])
            
            else:
                st.error("❌ Failed to extract PO data")
        
        else:
            st.error("❌ Failed to structure invoice data")
            error_msg = invoice_structured.get("error", "Unknown error")
            st.error(error_msg)
            
            # Show debug info for troubleshooting
            if "raw_response" in invoice_structured:
                with st.expander("🔍 Raw Response Debug"):
                    st.text(invoice_structured["raw_response"][:2000])
    
    else:
        st.error("❌ Failed to extract invoice data")

elif invoice_file or po_file:
    st.info("📁 Please upload both Invoice and Purchase Order files to begin comparison")
else:
    st.info("📁 Please upload both Invoice and Purchase Order files to get started")
