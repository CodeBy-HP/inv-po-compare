import streamlit as st
from typing import Optional

def file_upload_component() -> Optional[st.runtime.uploaded_file_manager.UploadedFile]:
    st.subheader("Upload your document")
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["pdf", "xlsx", "xls", "docx", "doc"],
        help="Supported formats: PDF, Excel, Word"
    )
    return uploaded_file
