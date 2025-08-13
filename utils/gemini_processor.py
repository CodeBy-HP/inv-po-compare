import streamlit as st
import google.generativeai as genai
import json
from typing import Dict, Any


class GeminiProcessor:
    def __init__(self):
        """Initialize Gemini API with the API key from Streamlit secrets."""
        try:
            api_key = st.secrets["gemini"]["api_key"]
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel("gemini-2.0-flash-exp")
            print("[DEBUG] Gemini API initialized successfully")
        except Exception as e:
            print(f"[ERROR] Failed to initialize Gemini API: {e}")
            self.model = None

    def structure_document_data(
        self, document_data: Dict[str, Any], document_type: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Process and structure any document data (Excel, PDF, Word, scanned images, etc.)
        using Gemini for contextual analysis.
        """
        if not self.model:
            return {"error": "Gemini API not initialized"}

        try:
            # Create a comprehensive prompt
            prompt = self._create_universal_structuring_prompt(
                document_data, document_type
            )

            print(f"[DEBUG] Sending {document_type} data to Gemini for contextual analysis...")
            print(f"[DEBUG] Prompt length: {len(prompt)} characters")

            # Send to Gemini
            response = self.model.generate_content(prompt)
            print("[DEBUG] Received response from Gemini")

            # Parse JSON response
            structured_data = self._parse_gemini_response(response.text)
            return structured_data

        except Exception as e:
            error_msg = f"Failed to process {document_type} with Gemini: {str(e)}"
            print(f"[ERROR] {error_msg}")
            return {"error": error_msg}

    def structure_excel_data(self, excel_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Legacy method for Excel data - internally uses the universal method.
        """
        return self.structure_document_data(excel_data, "Excel")

    def _create_universal_structuring_prompt(
        self, document_data: Dict[str, Any], document_type: str
    ) -> str:
        """
        Create a detailed prompt for Gemini to normalize and structure document data
        into a predefined JSON schema.
        """
        prompt = f"""
You are an expert in processing purchase orders (PO) and invoices.

I have extracted raw data from a document (could be PDF, Excel, Word, scanned image, or any other source).
The extraction may come from OCR, table parsing, or plain text, so the formatting can be inconsistent, incomplete, or ambiguous.

Your job is to analyze this data contextually and produce a **fully normalized, structured JSON output**
using ONLY the predefined standard business keys below.

RAW EXTRACTED DATA:
{json.dumps(document_data, indent=2)}

TASK:
1. **Context Detection**: Determine if the data is related to Purchase Orders, Invoices, or both.

2. **Standardized Key Mapping**:
   - Even if the raw data uses synonyms, abbreviations, or different column orders, map them to these exact keys only:
     - purchase_order_id  
     - invoice_id  
     - vendor_name  
     - vendor_id  
     - customer_name  
     - customer_id  
     - product_number  
     - product_name  
     - units  
     - unit_price  
     - tax_rate  
     - tax_amount  
     - total_value  
     - currency  
     - issue_date  
     - due_date  
     - payment_terms

3. **Entity Grouping**:
   - Group line items under their respective PO or invoice based on IDs or context.

4. **Dates**:
   - Return all dates in YYYY-MM-DD format when possible.

5. **Value Selection Rules**:
   - Always choose the base price per unit as `unit_price` (not the item price if both are present).
   - If total_value is missing but units and unit_price are present, calculate it as:
     `total_value = units * unit_price` (include tax_amount if tax_rate is provided).

OUTPUT FORMAT:
Respond ONLY with valid JSON in the following format:

{{
  "document_type": "purchase_order | invoice | mixed",
  "documents": [
    {{
      "purchase_order_id": "...",
      "invoice_id": "...",
      "vendor_name": "...",
      "vendor_id": "...",
      "customer_name": "...",
      "customer_id": "...",
      "line_items": [
        {{
          "product_number": "...",
          "product_name": "...",
          "units": 0,
          "unit_price": 0.00,
          "tax_rate": 0.00,
          "tax_amount": 0.00,
          "total_value": 0.00,
          "currency": "INR"
        }}
      ],
      "issue_date": "YYYY-MM-DD",
      "due_date": "YYYY-MM-DD",
      "payment_terms": "..."
    }}
  ]
}}

IMPORTANT:
- Use ONLY the above standard keys in the JSON.
- If a value is missing and cannot be calculated, return null but still include the key.
- Ensure valid JSON without comments or extra text.
"""
        return prompt

    def _parse_gemini_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse and validate Gemini's JSON response.
        """
        try:
            # Clean up response (remove markdown formatting if present)
            cleaned_response = response_text.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]

            # Parse JSON
            structured_data = json.loads(cleaned_response.strip())
            print("[DEBUG] Successfully parsed Gemini response")
            print(f"[DEBUG] Structured data keys: {list(structured_data.keys())}")

            return {
                "success": True,
                "data": structured_data,
                "raw_response_length": len(response_text),
            }

        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse JSON from Gemini: {e}")
            print(f"[DEBUG] Raw response: {response_text[:500]}...")
            return {
                "success": False,
                "error": "Invalid JSON response from Gemini",
                "raw_response": response_text[:1000],
            }
        except Exception as e:
            print(f"[ERROR] Unexpected error parsing response: {e}")
            return {
                "success": False,
                "error": str(e),
                "raw_response": response_text[:1000],
            }
