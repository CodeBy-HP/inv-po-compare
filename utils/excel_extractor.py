import pandas as pd
import streamlit as st
import json
from typing import Dict, Any

def extract_excel_info(uploaded_file) -> Dict[str, Any]:
    """
    Extract structured information from Excel file for LLM processing
    """
    try:
        # Read all sheets
        excel_data = pd.read_excel(uploaded_file, sheet_name=None)
        
        structured_info = {
            "file_name": uploaded_file.name,
            "total_sheets": len(excel_data),
            "sheets": {}
        }
        
        for sheet_name, df in excel_data.items():
            # Clean and analyze the dataframe
            sheet_info = {
                "sheet_name": sheet_name,
                "total_rows": len(df),
                "total_columns": len(df.columns),
                "columns": {
                    "names": df.columns.tolist(),
                    "data_types": df.dtypes.astype(str).to_dict()
                },
                "all_data": df.fillna("").to_dict(orient="records"),
                "sample_preview": {
                    "first_3_rows": df.head(3).fillna("").to_dict(orient="records"),
                    "last_3_rows": df.tail(3).fillna("").to_dict(orient="records") if len(df) > 3 else []
                },
                "summary_statistics": {},
                "potential_key_columns": [],
                "empty_cells_count": df.isnull().sum().to_dict()
            }
            
            # Add summary statistics for numeric columns
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                sheet_info["summary_statistics"] = df[numeric_cols].describe().fillna("").to_dict()
            
            # Identify potential key columns (columns with unique or mostly unique values)
            for col in df.columns:
                unique_ratio = df[col].nunique() / len(df) if len(df) > 0 else 0
                if unique_ratio > 0.8:  # More than 80% unique values
                    sheet_info["potential_key_columns"].append({
                        "column": col,
                        "unique_ratio": round(unique_ratio, 2),
                        "unique_values": min(10, df[col].nunique())  # Show up to 10 unique values
                    })
            
            structured_info["sheets"][sheet_name] = sheet_info
        
        # Print structured information in a clean JSON format
        print("\n" + "="*80)
        print("EXCEL FILE ANALYSIS - STRUCTURED FORMAT FOR LLM")
        print("="*80)
        print(json.dumps(structured_info, indent=2, ensure_ascii=False))
        print("="*80 + "\n")
        
        return structured_info
        
    except Exception as e:
        error_info = {
            "error": True,
            "message": str(e),
            "file_name": uploaded_file.name if uploaded_file else "Unknown"
        }
        print(f"\n[ERROR] Excel extraction failed:")
        print(json.dumps(error_info, indent=2))
        return error_info
