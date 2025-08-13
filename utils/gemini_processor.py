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
            self._original_data = None  # Store original data for post-processing
            print("[DEBUG] Gemini API initialized successfully")
        except Exception as e:
            print(f"[ERROR] Failed to initialize Gemini API: {e}")
            self.model = None
            self._original_data = None

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
            # Store original data for post-processing
            self._original_data = document_data
            
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
            3. **Summary Field Extraction and Cross-Check**:
                - Extract summary fields such as total, subtotal, and total_tax if present in the document.
                - If summary fields are present, use them for the overall invoice/PO totals and tax.
                - If summary fields are missing, calculate totals by summing all line items and tax amounts.
                - If there is a mismatch between calculated and summary totals, include both and flag the discrepancy in the output.

            4. **Tax Rate and Amount Handling**:
                - Extract tax rates and amounts from both line items and summary tables.
                - If tax rate is given as a percentage (e.g., "9%"), convert to decimal (0.09).

            5. **Currency Normalization**:
                - Always return currency as "INR" and ignore symbols like "₹".

            6. **Fallback Logic**:
                - If any value is missing, infer it from other available fields (e.g., calculate total_value if missing).

            7. **Contextual Awareness**:
                - Use all available context from both line items and summary fields to ensure accuracy.

            8. **Strict Output Format**:
                - Respond ONLY with valid JSON using the schema below.
                - Use null for missing values, not empty strings.
                - Do not add any extra commentary or markdown.
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

3. **CRITICAL: Financial Data Extraction**:
   - Look for financial_info sections containing total, subtotal, total_tax amounts
   - For line items: extract units, unit_price, tax_rate, tax_amount from items array
   - For invoices: total_value should include taxes (subtotal + total_tax)
   - If CGST + SGST are present, combine them (e.g., 9% + 9% = 18% = 0.18)
   - Use financial_info.total.amount as the final invoice total when available

4. **Entity Grouping**:
   - Group line items under their respective PO or invoice based on IDs or context.

4. **Dates**:
   - Return all dates in YYYY-MM-DD format when possible.

5. **Value Selection Rules**:
   - Always choose the base price per unit as `unit_price` (not the item price if both are present)
   - For total_value: Use financial_info.total.amount if available, otherwise calculate as subtotal + tax
   - For tax calculations: Look for CGST + SGST values and combine them
   - If tax rate is percentage (e.g., "9%"), convert to decimal (0.09)
   - Always prioritize summary financial data over calculated values

6. **CALCULATION EXAMPLE** (for the given invoice):
   - Product: Bajaj 2000 TM 20L
   - Units: 30, Unit Price: 3389
   - Subtotal: 30 × 3389 = 101,670
   - CGST: 9,150.30 (9%), SGST: 9,150.30 (9%) = Total Tax: 18,300.60
   - Tax Rate: 18% (0.18), Tax Amount: 18,300.60
   - Total Value: 101,670 + 18,300.60 = 119,970.60

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
- Use ONLY the above standard keys in the JSON
- CRITICAL: Extract financial totals from financial_info section when available
- For invoices: total_value should be the final amount including all taxes
- If financial_info.total.amount exists, use it as the invoice total
- If tax breakdown exists (CGST + SGST), combine them into tax_rate and tax_amount
- Always return currency as "INR" (ignore ₹ symbols)
- If a value is missing, return null but still include the key
- Ensure valid JSON without comments or extra text
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
            
            # Apply post-processing to fix financial calculations
            structured_data = self._post_process_financial_data(structured_data)
            
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
    
    def _post_process_financial_data(self, structured_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Post-process financial data to ensure correct calculations using original Azure AI data
        """
        print("[DEBUG] Post-processing financial data...")
        
        if "documents" not in structured_data:
            return structured_data
        
        # Get original financial info from Azure AI if available
        original_financial_info = {}
        if hasattr(self, '_original_data') and self._original_data:
            original_financial_info = self._original_data.get('financial_info', {})
            print(f"[DEBUG] Original financial_info available: {list(original_financial_info.keys())}")
        
        for doc in structured_data["documents"]:
            if "line_items" not in doc:
                continue
                
            print(f"[DEBUG] Processing {len(doc['line_items'])} line items...")
            
            # Get document totals from original data if available
            document_total = None
            document_subtotal = None
            document_tax_total = None
            
            if original_financial_info:
                if 'total' in original_financial_info:
                    document_total = original_financial_info['total'].get('amount', 0)
                    print(f"[DEBUG] Using original document total: {document_total}")
                
                if 'subtotal' in original_financial_info:
                    document_subtotal = original_financial_info['subtotal'].get('amount', 0)
                    print(f"[DEBUG] Using original document subtotal: {document_subtotal}")
                
                if 'total_tax' in original_financial_info:
                    document_tax_total = original_financial_info['total_tax'].get('amount', 0)
                    print(f"[DEBUG] Using original document tax total: {document_tax_total}")
            
            # Calculate total from line items for comparison
            calculated_subtotal = 0
            calculated_tax_total = 0
            
            for item in doc["line_items"]:
                # Fix individual line item calculations
                units = item.get("units", 0) or 0
                unit_price = item.get("unit_price", 0) or 0
                tax_rate = item.get("tax_rate", 0) or 0
                
                if units > 0 and unit_price > 0:
                    # Calculate subtotal (before tax)
                    subtotal = units * unit_price
                    calculated_subtotal += subtotal
                    
                    # Calculate tax amount
                    if tax_rate > 0:
                        # If tax_rate is between 0 and 1, it's already decimal
                        # If it's > 1, convert from percentage
                        if tax_rate > 1:
                            tax_rate = tax_rate / 100
                        
                        tax_amount = subtotal * tax_rate
                        calculated_tax_total += tax_amount
                        item["tax_amount"] = round(tax_amount, 2)
                        item["tax_rate"] = tax_rate
                    else:
                        item["tax_amount"] = 0
                        item["tax_rate"] = 0
                    
                    # For line item total, always calculate from subtotal + tax
                    total_value = subtotal + item.get("tax_amount", 0)
                    item["total_value"] = round(total_value, 2)
                    
                    print(f"[DEBUG] Item {item.get('product_number', 'N/A')}: {units} x {unit_price} = {subtotal}, tax: {item.get('tax_amount', 0)}, total: {total_value}")
            
            # Use original document totals if available and different from calculated
            calculated_total = calculated_subtotal + calculated_tax_total
            print(f"[DEBUG] Calculated from line items - Subtotal: {calculated_subtotal}, Tax: {calculated_tax_total}, Total: {calculated_total}")
            
            # If we have original totals that differ significantly, use them
            if document_total and abs(document_total - calculated_total) > 1:
                print(f"[DEBUG] Using original document total {document_total} instead of calculated {calculated_total}")
                # Store document-level totals for comparison
                doc["document_totals"] = {
                    "subtotal": document_subtotal or calculated_subtotal,
                    "tax_total": document_tax_total or calculated_tax_total,
                    "total": document_total,
                    "original_data_used": True
                }
            else:
                doc["document_totals"] = {
                    "subtotal": calculated_subtotal,
                    "tax_total": calculated_tax_total,
                    "total": calculated_total,
                    "original_data_used": False
                }
        
        return structured_data
    
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
   Example: "VI-3423" and "3423" should be considered the same product_number. There is one more concern is that sometime the product ids are missing from the invoices or pos or maybe the extracted product id is acutally a HSN/SAC, thus please if you think if there is the case please match the products based on the description of the product and perform fuzzy matching on each item.
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
