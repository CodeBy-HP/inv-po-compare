import streamlit as st
import json
from typing import Dict, Any, List
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
import io

def extract_pdf_info(uploaded_file) -> Dict[str, Any]:
    """
    Extract structured information from PDF document using Azure AI Document Intelligence
    """
    try:
        # Get Azure credentials from Streamlit secrets
        endpoint = st.secrets["azure"]["endpoint"]
        key = st.secrets["azure"]["key"]
        
        # Initialize Azure AI Document Intelligence client
        document_intelligence_client = DocumentIntelligenceClient(
            endpoint=endpoint, 
            credential=AzureKeyCredential(key)
        )
        
        print(f"[DEBUG] Initialized Azure AI Document Intelligence client")
        print(f"[DEBUG] Endpoint: {endpoint}")
        print(f"[DEBUG] Processing PDF: {uploaded_file.name}")
        
        # Convert uploaded file to bytes for Azure AI processing
        file_bytes = uploaded_file.read()
        uploaded_file.seek(0)  # Reset file pointer for potential re-reading
        print(f"[DEBUG] File size: {len(file_bytes)} bytes")
        
        # Start with prebuilt-invoice model as it's most commonly available
        try:
            print("[DEBUG] Trying prebuilt-invoice model...")
            poller = document_intelligence_client.begin_analyze_document(
                "prebuilt-invoice", 
                AnalyzeDocumentRequest(bytes_source=file_bytes)
            )
            
            print("[DEBUG] Document analysis started with prebuilt-invoice...")
            result = poller.result()
            model_used = "prebuilt-invoice"
            print("[DEBUG] Document analysis completed with prebuilt-invoice")
            
        except Exception as invoice_error:
            print(f"[DEBUG] prebuilt-invoice failed: {str(invoice_error)}")
            
            # Try fallback models
            models_to_try = ["prebuilt-layout", "prebuilt-read"]
            result = None
            model_used = None
            
            for model_name in models_to_try:
                try:
                    print(f"[DEBUG] Trying fallback model: {model_name}")
                    poller = document_intelligence_client.begin_analyze_document(
                        model_name, 
                        AnalyzeDocumentRequest(bytes_source=file_bytes)
                    )
                    
                    print(f"[DEBUG] Document analysis started with {model_name}...")
                    result = poller.result()
                    model_used = model_name
                    print(f"[DEBUG] Document analysis completed with {model_name}")
                    break
                    
                except Exception as model_error:
                    print(f"[DEBUG] Model {model_name} failed: {str(model_error)}")
                    continue
            
            if result is None:
                raise Exception(f"All Azure AI models failed. Original error: {str(invoice_error)}")
        
        print(f"[DEBUG] Successfully used model: {model_used}")
        
        # Structure the extracted information for our system
        structured_info = {
            "file_name": uploaded_file.name,
            "document_type": "PDF",
            "extraction_method": f"Azure AI Document Intelligence ({model_used})",
            "content": {
                "pages": [],
                "tables": [],
                "key_value_pairs": [],
                "entities": [],
                "paragraphs": [],
                "raw_text": ""
            },
            "metadata": {
                "model_used": model_used,
                "confidence_scores": {}
            }
        }
        
        # Handle different result structures based on model used
        if model_used == "prebuilt-invoice" and hasattr(result, 'documents') and result.documents:
            print("[DEBUG] Processing as invoice document")
            # For invoice model, we get structured invoice data
            structured_info["invoice_data"] = _extract_invoice_specific_data(result.documents)
            
            # Also extract basic content if available
            if hasattr(result, 'pages') and result.pages:
                structured_info["pages"] = len(result.pages)
                for page_idx, page in enumerate(result.pages):
                    page_info = {
                        "page_number": page_idx + 1,
                        "lines": []
                    }
                    if hasattr(page, 'lines') and page.lines:
                        for line in page.lines:
                            page_info["lines"].append({
                                "content": line.content if hasattr(line, 'content') else str(line),
                                "confidence": getattr(line, 'confidence', None)
                            })
                    structured_info["content"]["pages"].append(page_info)
        
        else:
            print(f"[DEBUG] Processing as general document with model: {model_used}")
            # For other models, extract what's available
            if hasattr(result, 'pages') and result.pages:
                structured_info["pages"] = len(result.pages)
                for page_idx, page in enumerate(result.pages):
                    page_info = {
                        "page_number": page_idx + 1,
                        "lines": [],
                        "words": len(page.words) if hasattr(page, 'words') and page.words else 0
                    }
                    
                    # Extract lines from the page
                    if hasattr(page, 'lines') and page.lines:
                        for line in page.lines:
                            page_info["lines"].append({
                                "content": line.content if hasattr(line, 'content') else str(line),
                                "confidence": getattr(line, 'confidence', None)
                            })
                    
                    structured_info["content"]["pages"].append(page_info)
            
            # Extract paragraphs if available
            if hasattr(result, 'paragraphs') and result.paragraphs:
                for para_idx, paragraph in enumerate(result.paragraphs):
                    para_info = {
                        "paragraph_number": para_idx + 1,
                        "content": paragraph.content if hasattr(paragraph, 'content') else str(paragraph),
                        "confidence": getattr(paragraph, 'confidence', None),
                        "role": getattr(paragraph, 'role', None)
                    }
                    structured_info["content"]["paragraphs"].append(para_info)
            
            # Extract tables if available
            if hasattr(result, 'tables') and result.tables:
                for table_idx, table in enumerate(result.tables):
                    table_info = {
                        "table_number": table_idx + 1,
                        "rows": getattr(table, 'row_count', 0),
                        "columns": getattr(table, 'column_count', 0),
                        "cells": []
                    }
                    
                    # Extract table cells
                    if hasattr(table, 'cells') and table.cells:
                        for cell in table.cells:
                            cell_info = {
                                "content": cell.content if hasattr(cell, 'content') else str(cell),
                                "row_index": getattr(cell, 'row_index', 0),
                                "column_index": getattr(cell, 'column_index', 0),
                                "confidence": getattr(cell, 'confidence', None)
                            }
                            table_info["cells"].append(cell_info)
                    
                    structured_info["content"]["tables"].append(table_info)
            
            # Extract key-value pairs if available
            if hasattr(result, 'key_value_pairs') and result.key_value_pairs:
                for kv_pair in result.key_value_pairs:
                    kv_info = {
                        "key": kv_pair.key.content if hasattr(kv_pair, 'key') and kv_pair.key else None,
                        "value": kv_pair.value.content if hasattr(kv_pair, 'value') and kv_pair.value else None,
                        "confidence": getattr(kv_pair, 'confidence', None)
                    }
                    structured_info["content"]["key_value_pairs"].append(kv_info)
        
        # Print structured information in a clean JSON format
        print("\n" + "="*80)
        print("PDF DOCUMENT ANALYSIS - STRUCTURED FORMAT FOR LLM")
        print("="*80)
        print(json.dumps(structured_info, indent=2, ensure_ascii=False))
        print("="*80 + "\n")
        
        return structured_info
        
    except Exception as e:
        error_info = {
            "error": True,
            "message": str(e),
            "file_name": uploaded_file.name if uploaded_file else "Unknown",
            "document_type": "PDF"
        }
        print(f"\n[ERROR] PDF extraction failed:")
        print(json.dumps(error_info, indent=2))
        return error_info

def _extract_invoice_specific_data(documents) -> List[Dict[str, Any]]:
    """
    Extract invoice-specific structured data from Azure AI results
    """
    invoices_data = []
    
    for idx, invoice in enumerate(documents):
        invoice_info = {
            "invoice_number": idx + 1,
            "basic_info": {},
            "vendor_info": {},
            "customer_info": {},
            "financial_info": {},
            "items": [],
            "dates": {},
            "addresses": {}
        }
        
        # Basic invoice information
        basic_fields = {
            "InvoiceId": "invoice_id",
            "PurchaseOrder": "purchase_order"
        }
        
        for field_name, key in basic_fields.items():
            field = invoice.fields.get(field_name)
            if field:
                invoice_info["basic_info"][key] = {
                    "value": field.value_string if hasattr(field, 'value_string') else str(field.value),
                    "confidence": field.confidence
                }
        
        # Vendor information
        vendor_fields = {
            "VendorName": "name",
            "VendorAddress": "address",
            "VendorAddressRecipient": "address_recipient"
        }
        
        for field_name, key in vendor_fields.items():
            field = invoice.fields.get(field_name)
            if field:
                value = field.value_address if hasattr(field, 'value_address') else field.value_string
                invoice_info["vendor_info"][key] = {
                    "value": str(value),
                    "confidence": field.confidence
                }
        
        # Customer information
        customer_fields = {
            "CustomerName": "name",
            "CustomerId": "id",
            "CustomerAddress": "address",
            "CustomerAddressRecipient": "address_recipient"
        }
        
        for field_name, key in customer_fields.items():
            field = invoice.fields.get(field_name)
            if field:
                value = field.value_address if hasattr(field, 'value_address') else field.value_string
                invoice_info["customer_info"][key] = {
                    "value": str(value),
                    "confidence": field.confidence
                }
        
        # Financial information
        financial_fields = {
            "InvoiceTotal": "total",
            "SubTotal": "subtotal",
            "TotalTax": "total_tax",
            "AmountDue": "amount_due",
            "PreviousUnpaidBalance": "previous_balance"
        }
        
        for field_name, key in financial_fields.items():
            field = invoice.fields.get(field_name)
            if field and hasattr(field, 'value_currency') and field.value_currency:
                invoice_info["financial_info"][key] = {
                    "amount": field.value_currency.amount if field.value_currency.amount is not None else 0,
                    "currency": getattr(field.value_currency, 'currency_symbol', 'USD'),
                    "confidence": getattr(field, 'confidence', 0)
                }
        
        # Date information
        date_fields = {
            "InvoiceDate": "invoice_date",
            "DueDate": "due_date",
            "ServiceStartDate": "service_start",
            "ServiceEndDate": "service_end"
        }
        
        for field_name, key in date_fields.items():
            field = invoice.fields.get(field_name)
            if field and hasattr(field, 'value_date') and field.value_date:
                invoice_info["dates"][key] = {
                    "value": str(field.value_date),
                    "confidence": getattr(field, 'confidence', 0)
                }
        
        # Extract line items
        items_field = invoice.fields.get("Items")
        if items_field and hasattr(items_field, 'value_array'):
            for item_idx, item in enumerate(items_field.value_array):
                item_info = {"item_number": item_idx + 1}
                
                item_fields = {
                    "Description": "description",
                    "Quantity": "quantity", 
                    "UnitPrice": "unit_price",
                    "Amount": "amount",
                    "ProductCode": "product_code",
                    "Tax": "tax"
                }
                
                for field_name, key in item_fields.items():
                    field = item.value_object.get(field_name)
                    if field:
                        if hasattr(field, 'value_currency') and field.value_currency:
                            item_info[key] = {
                                "amount": field.value_currency.amount if field.value_currency.amount is not None else 0,
                                "currency": getattr(field.value_currency, 'currency_symbol', 'USD'),
                                "confidence": getattr(field, 'confidence', 0)
                            }
                        elif hasattr(field, 'value_number') and field.value_number is not None:
                            item_info[key] = {
                                "value": field.value_number,
                                "confidence": getattr(field, 'confidence', 0)
                            }
                        elif hasattr(field, 'value_string') and field.value_string:
                            item_info[key] = {
                                "value": field.value_string,
                                "confidence": getattr(field, 'confidence', 0)
                            }
                
                invoice_info["items"].append(item_info)
        
        invoices_data.append(invoice_info)
    
    return invoices_data
