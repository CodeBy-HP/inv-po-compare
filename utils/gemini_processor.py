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
            print(f"[DEBUG] Input data summary:")
            if isinstance(document_data, dict):
                if 'sheets' in document_data:
                    for sheet_name, sheet_data in document_data['sheets'].items():
                        if 'all_data' in sheet_data:
                            print(f"  - Sheet '{sheet_name}': {len(sheet_data['all_data'])} rows")
                else:
                    print(f"  - Document keys: {list(document_data.keys())}")

            # Send to Gemini
            response = self.model.generate_content(prompt)
            print("[DEBUG] Received response from Gemini")
            print(f"[DEBUG] Response length: {len(response.text)} characters")

            # Parse JSON response
            structured_data = self._parse_gemini_response(response.text)
            
            # Additional debug info about the structured result
            if structured_data.get("success"):
                data = structured_data.get("data", {})
                if 'documents' in data:
                    for i, doc in enumerate(data['documents']):
                        if 'line_items' in doc:
                            print(f"[DEBUG] Document {i+1}: {len(doc['line_items'])} line items structured")
                        
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
        Create a detailed prompt for Gemini to structure any document data (Excel, PDF, Word)
        """
        prompt = f"""
You are an expert in processing purchase orders (PO) and invoices.

I have extracted raw data from a document (could be PDF, Excel, Word, scanned image, or any other source).
The extraction may come from OCR, table parsing, or plain text, so the formatting can be inconsistent, incomplete, or ambiguous.

Your job is to analyze this data contextually and produce a **fully normalized, structured JSON output** using ONLY the predefined standard business keys below.

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
- If a value is missing, return null but still include the key.
- Do not calculate missing values; leave them null if not found.
- Always select the base price per unit as `unit_price` when available.
- Ensure valid JSON without comments or extra text.
"""
        return prompt

    def _parse_gemini_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse and validate Gemini's JSON response with robust error handling.
        """
        try:
            print(f"[DEBUG] Raw response length: {len(response_text)}")
            print(f"[DEBUG] Raw response preview: {response_text[:200]}...")
            
            # Clean up response (remove markdown formatting if present)
            cleaned_response = response_text.strip()
            
            # Remove markdown code blocks
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            elif cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]
                
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            
            # Remove any leading/trailing text that's not JSON
            lines = cleaned_response.split('\n')
            start_idx = 0
            end_idx = len(lines)
            
            # Find first line that starts with {
            for i, line in enumerate(lines):
                if line.strip().startswith('{'):
                    start_idx = i
                    break
            
            # Find last line that ends with }
            for i in range(len(lines)-1, -1, -1):
                if lines[i].strip().endswith('}'):
                    end_idx = i + 1
                    break
            
            # Extract JSON portion
            json_lines = lines[start_idx:end_idx]
            json_text = '\n'.join(json_lines).strip()
            
            print(f"[DEBUG] Cleaned JSON length: {len(json_text)}")
            print(f"[DEBUG] Cleaned JSON preview: {json_text[:200]}...")

            # Parse JSON
            structured_data = json.loads(json_text)
            print("[DEBUG] Successfully parsed Gemini response")
            print(f"[DEBUG] Structured data keys: {list(structured_data.keys())}")
            
            # Validate required fields
            if "line_items" in structured_data:
                item_count = len(structured_data["line_items"])
                print(f"[DEBUG] Found {item_count} line items in response")

            return {
                "success": True,
                "data": structured_data,
                "raw_response_length": len(response_text),
            }

        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse JSON from Gemini: {e}")
            print(f"[DEBUG] Problematic JSON: {json_text[:800] if 'json_text' in locals() else 'N/A'}...")
            return {
                "success": False,
                "error": f"Invalid JSON response from Gemini: {str(e)}",
                "raw_response": response_text[:1000],
            }
        except Exception as e:
            print(f"[ERROR] Unexpected error parsing response: {e}")
            return {
                "success": False,
                "error": str(e),
                "raw_response": response_text[:1000],
            }
    
    def compare_invoice_vs_po(self, invoice_data: Dict[str, Any], po_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare invoice and purchase order data to find discrepancies
        """
        if not self.model:
            return {"error": "Gemini API not initialized"}
        
        try:
            # Create comparison prompt
            prompt = self._create_comparison_prompt(invoice_data, po_data)
            
            print("[DEBUG] Sending invoice vs PO comparison to Gemini...")
            print(f"[DEBUG] Prompt length: {len(prompt)} characters")
            print(f"[DEBUG] Comparison input summary:")
            
            # Debug info about input data
            if 'documents' in invoice_data:
                for i, doc in enumerate(invoice_data['documents']):
                    if 'line_items' in doc:
                        print(f"  - Invoice document {i+1}: {len(doc['line_items'])} line items")
            
            if 'documents' in po_data:
                for i, doc in enumerate(po_data['documents']):
                    if 'line_items' in doc:
                        print(f"  - PO document {i+1}: {len(doc['line_items'])} line items")
            
            # Send to Gemini
            response = self.model.generate_content(prompt)
            
            print("[DEBUG] Received comparison response from Gemini")
            print(f"[DEBUG] Response length: {len(response.text)} characters")
            print(f"[DEBUG] Response preview: {response.text[:300]}...")
            
            # Parse JSON response
            try:
                response_text = response.text.strip()
                
                # Find JSON boundaries
                start_idx = 0
                end_idx = len(response_text)
                
                # Look for JSON start
                if response_text.find('{') != -1:
                    start_idx = response_text.find('{')
                
                # Look for JSON end
                if response_text.rfind('}') != -1:
                    end_idx = response_text.rfind('}') + 1
                
                # Extract JSON portion
                json_text = response_text[start_idx:end_idx].strip()
                print(f"[DEBUG] Extracted JSON length: {len(json_text)}")
                
                # Parse JSON
                comparison_data = json.loads(json_text)
                print("[DEBUG] Successfully parsed comparison JSON")
                
                if "comparison_results" in comparison_data:
                    result_count = len(comparison_data["comparison_results"])
                    print(f"[DEBUG] Found {result_count} comparison results")
                
                comparison_result = {
                    "success": True,
                    "data": comparison_data,
                    "format": "json"
                }
                
                return comparison_result
                
            except json.JSONDecodeError as e:
                print(f"[ERROR] Failed to parse comparison JSON: {e}")
                print(f"[DEBUG] Raw response: {response.text[:500]}...")
                
                # Fallback: treat as raw text
                comparison_result = {
                    "success": True,
                    "data": {
                        "comparison_table": response.text.strip(),
                        "format": "raw_text"
                    },
                    "raw_response": response.text
                }
                return comparison_result
            
        except Exception as e:
            error_msg = f"Failed to compare documents with Gemini: {str(e)}"
            print(f"[ERROR] {error_msg}")
            return {"error": error_msg}
    
    def _create_comparison_prompt(self, invoice_data: Dict[str, Any], po_data: Dict[str, Any]) -> str:
        """
        Create a detailed prompt for Gemini to compare invoice vs purchase order
        """
        comparison_prompt = f"""
You are an expert in comparing purchase order (PO) and invoice line items.

You will be given **two structured JSON documents** — one for a Purchase Order and one for an Invoice — both following the same schema.

TASK:
1. Compare ONLY the "line_items" arrays in both documents.
2. Before comparison, normalize product_number by extracting ONLY the numeric part (ignore any letters, prefixes, or symbols).
   Example: "VI-3423" and "3423" should be considered the same product_number.
3. Match products based on this normalized product_number.
4. For each matched product, compare:
   - units
   - unit_price
   - tax_rate
   - tax_amount
   - total_value
   - currency
5. If total_value is missing but units and unit_price are present, calculate it for comparison purposes only.
6. Include unmatched products from either document in the output.

**INPUT DATA**:
Purchase Order JSON:
{json.dumps(po_data, indent=2)}

Invoice JSON:
{json.dumps(invoice_data, indent=2)}

**OUTPUT FORMAT**:
Respond ONLY with valid JSON in this exact format:

{{
  "comparison_results": [
    {{
      "product_number": "normalized_product_id",
      "po_units": number_or_null,
      "invoice_units": number_or_null,
      "po_unit_price": number_or_null,
      "invoice_unit_price": number_or_null,
      "po_tax_rate": number_or_null,
      "invoice_tax_rate": number_or_null,
      "po_tax_amount": number_or_null,
      "invoice_tax_amount": number_or_null,
      "po_total_value": number_or_null,
      "invoice_total_value": number_or_null,
      "po_currency": "string_or_null",
      "invoice_currency": "string_or_null",
      "status": "Match|Mismatch",
      "discrepancy_details": "detailed explanation if mismatch"
    }}
  ],
  "summary": {{
    "total_items": number,
    "matched_items": number,
    "mismatched_items": number,
    "po_only_items": number,
    "invoice_only_items": number
  }}
}}

IMPORTANT RULES:
- "status" should be "Match" if all compared fields match (within ±0.01 for numeric values), otherwise "Mismatch"
- Include all products from both documents, even if unmatched
- Use null for missing values, not empty strings
- Normalize product numbers by removing prefixes like "VI-", "CB.", etc.
- Return ONLY valid JSON, no markdown formatting or extra text
"""
        return comparison_prompt
