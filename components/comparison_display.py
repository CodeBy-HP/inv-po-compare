import streamlit as st
import pandas as pd
from typing import Dict, Any

def display_comparison_results(comparison_result: Dict[str, Any]):
    """
    Display minimal, professional comparison results with debugging info
    """
    
    # 🐛 DEBUG: Show what we received
    with st.expander("🔍 DEBUG - Comparison Data Structure", expanded=False):
        st.subheader("Raw Comparison Result Received")
        st.json(comparison_result)
        st.write(f"**Data type:** {type(comparison_result)}")
        st.write(f"**Keys:** {list(comparison_result.keys()) if isinstance(comparison_result, dict) else 'Not a dict'}")
    
    # Extract the actual comparison data
    comparison_data = comparison_result.get("data", {}) if isinstance(comparison_result, dict) else comparison_result
    
    # 🐛 DEBUG: Show format detection
    with st.expander("🔍 DEBUG - Format Detection", expanded=False):
        st.write(f"**comparison_result.get('format'):** {comparison_result.get('format') if isinstance(comparison_result, dict) else 'N/A'}")
        st.write(f"**comparison_data.get('format'):** {comparison_data.get('format') if isinstance(comparison_data, dict) else 'N/A'}")
        st.write(f"**'comparison_results' in comparison_data:** {'comparison_results' in comparison_data if isinstance(comparison_data, dict) else 'N/A'}")
        st.write(f"**'comparison_table' in comparison_data:** {'comparison_table' in comparison_data if isinstance(comparison_data, dict) else 'N/A'}")
    
    # Handle new JSON format
    if comparison_result.get("format") == "json" and "comparison_results" in comparison_data:
        comparison_results = comparison_data["comparison_results"]
        summary = comparison_data.get("summary", {})
        
        st.markdown("### Invoice vs Purchase Order Comparison")
        
        # 🐛 DEBUG: Show data analysis
        with st.expander("🔍 DEBUG - JSON Data Analysis", expanded=False):
            st.subheader("Comparison Results Analysis")
            st.write(f"**Total comparison results:** {len(comparison_results)}")
            st.write(f"**Summary data:** {summary}")
            
            # Show sample result structure
            if comparison_results:
                st.write("**Sample result structure:**")
                st.json(comparison_results[0])
        
        # Calculate metrics
        total_items = len(comparison_results)
        mismatch_count = sum(1 for item in comparison_results if item.get("status") == "Mismatch")
        match_count = total_items - mismatch_count
        
        # Summary header
        if mismatch_count > 0:
            st.markdown(f"""
            <div style="background: #e74c3c; color: white; padding: 1rem; border-radius: 5px; text-align: center; margin-bottom: 2rem;">
                <h3 style="margin: 0;">ISSUES FOUND: {mismatch_count} mismatches out of {total_items} items</h3>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background: #27ae60; color: white; padding: 1rem; border-radius: 5px; text-align: center; margin-bottom: 2rem;">
                <h3 style="margin: 0;">ALL GOOD: All {total_items} items match perfectly!</h3>
            </div>
            """, unsafe_allow_html=True)
        
        # Convert to DataFrame for better display
        try:
            df_data = []
            for item in comparison_results:
                df_data.append({
                    "Product": item.get("product_number", "N/A"),
                    "PO Units": item.get("po_units", ""),
                    "Invoice Units": item.get("invoice_units", ""),
                    "PO Price": f"₹{item.get('po_unit_price', 0):,.2f}" if item.get('po_unit_price') else "",
                    "Invoice Price": f"₹{item.get('invoice_unit_price', 0):,.2f}" if item.get('invoice_unit_price') else "",
                    "PO Total": f"₹{item.get('po_total_value', 0):,.2f}" if item.get('po_total_value') else "",
                    "Invoice Total": f"₹{item.get('invoice_total_value', 0):,.2f}" if item.get('invoice_total_value') else "",
                    "Status": item.get("status", "Unknown"),
                    "Details": item.get("discrepancy_details", "")
                })
            
            df = pd.DataFrame(df_data)
            
            # Style the dataframe
            def style_status(val):
                if val == "Match":
                    return "background-color: #d4edda; color: #155724"
                elif val == "Mismatch":
                    return "background-color: #f8d7da; color: #721c24"
                return ""
            
            styled_df = df.style.applymap(style_status, subset=['Status'])
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
            
            # Show mismatches only section
            if mismatch_count > 0:
                st.markdown("### Issues Requiring Attention")
                mismatch_items = [item for item in comparison_results if item.get("status") == "Mismatch"]
                
                for item in mismatch_items:
                    with st.container():
                        st.markdown(f"**Product: {item.get('product_number', 'N/A')}**")
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.write(f"PO Units: {item.get('po_units', 'N/A')}")
                            st.write(f"Invoice Units: {item.get('invoice_units', 'N/A')}")
                        with col2:
                            st.write(f"PO Price: ₹{item.get('po_unit_price', 0):,.2f}" if item.get('po_unit_price') else "PO Price: N/A")
                            st.write(f"Invoice Price: ₹{item.get('invoice_unit_price', 0):,.2f}" if item.get('invoice_unit_price') else "Invoice Price: N/A")
                        with col3:
                            st.write(f"PO Total: ₹{item.get('po_total_value', 0):,.2f}" if item.get('po_total_value') else "PO Total: N/A")
                            st.write(f"Invoice Total: ₹{item.get('invoice_total_value', 0):,.2f}" if item.get('invoice_total_value') else "Invoice Total: N/A")
                        
                        if item.get('discrepancy_details'):
                            st.info(f"**Issue:** {item.get('discrepancy_details')}")
                        
                        st.divider()
            
        except Exception as e:
            st.error(f"Error creating comparison table: {e}")
            st.json(comparison_results)  # Fallback to raw JSON
    
    # Handle legacy markdown table format
    elif comparison_result.get("format") == "markdown_table" or comparison_data.get("format") == "markdown_table":
        comparison_table = comparison_data.get("comparison_table", "") or comparison_result.get("comparison_table", "")
        
        st.markdown("### Invoice vs Purchase Order Comparison")
        
        # 🐛 DEBUG: Show table analysis
        with st.expander("🔍 DEBUG - Table Analysis", expanded=False):
            st.subheader("Markdown Table Breakdown")
            lines = comparison_table.split('\n')
            st.write(f"**Total lines:** {len(lines)}")
            for i, line in enumerate(lines[:10]):  # Show first 10 lines
                st.text(f"Line {i}: {line}")
            if len(lines) > 10:
                st.text("... (truncated)")
        
        # Display the markdown table
        if comparison_table:
            # Count matches and mismatches for summary
            lines = comparison_table.split('\n')
            data_rows = [line for line in lines if '|' in line and not line.startswith('|---')]
            if len(data_rows) > 2:  # Skip header rows
                total_items = len(data_rows) - 2
                mismatch_count = sum(1 for row in data_rows[2:] if 'Mismatch' in row)
                match_count = total_items - mismatch_count
                
                # 🐛 DEBUG: Show counting logic
                with st.expander("🔍 DEBUG - Item Counting", expanded=False):
                    st.write(f"**All lines:** {len(lines)}")
                    st.write(f"**Lines with |:** {len([l for l in lines if '|' in l])}")
                    st.write(f"**Data rows:** {len(data_rows)}")
                    st.write(f"**Total items (excluding headers):** {total_items}")
                    st.write(f"**Mismatch count:** {mismatch_count}")
                    st.write(f"**Match count:** {match_count}")
                
                # Summary header
                if mismatch_count > 0:
                    st.markdown(f"""
                    <div style="background: #e74c3c; color: white; padding: 1rem; border-radius: 5px; text-align: center; margin-bottom: 2rem;">
                        <h3 style="margin: 0;">ISSUES FOUND: {mismatch_count} mismatches out of {total_items} items</h3>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="background: #27ae60; color: white; padding: 1rem; border-radius: 5px; text-align: center; margin-bottom: 2rem;">
                        <h3 style="margin: 0;">ALL GOOD: All {total_items} items match perfectly!</h3>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Display the comparison table
            st.markdown(comparison_table)
        else:
            st.error("No comparison data available")
    
    # Handle raw text fallback
    elif comparison_result.get("format") == "raw_text" or comparison_data.get("format") == "raw_text":
        st.warning("⚠️ Received response in text format - displaying as-is")
        comparison_text = comparison_data.get("comparison_table", "") or comparison_result.get("comparison_table", "")
        st.text(comparison_text)
    
    else:
        # Fallback for old JSON format (if any)
        st.warning("⚠️ Received unexpected data format - showing raw data")
        summary = comparison_data.get("comparison_summary", {})
        discrepancies = summary.get("items_with_discrepancies", 0)
        total_items = summary.get("total_items_compared", 0)
        status = summary.get("overall_status", "UNKNOWN")
        
        # Status Header
        status_color = "#e74c3c" if status == "FAIL" else "#27ae60" if status == "PASS" else "#f39c12"
        st.markdown(f"""
        <div style="background: {status_color}; color: white; padding: 1rem; border-radius: 5px; text-align: center; margin-bottom: 2rem;">
            <h3 style="margin: 0;">{status}: {discrepancies} discrepancies found in {total_items} items</h3>
        </div>
        """, unsafe_allow_html=True)
        
        if discrepancies > 0:
            # Show only items with discrepancies in clean table
            line_items = comparison_data.get("line_item_comparison", [])
            problem_items = [item for item in line_items if item.get("overall_item_status") in ["FAIL", "WARNING"]]
            
            if problem_items:
                st.markdown("### Issues Found")
                for i, item in enumerate(problem_items):
                    product_info = item.get("product_identification", {})
                    product_name = product_info.get("product_name", "Unknown Product")
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**{product_name}**")
                        discrepancies = item.get("discrepancy_details", [])
                        for disc in discrepancies:
                            st.markdown(f"• {disc}")
                    
                    with col2:
                        total_info = item.get("total_amount_comparison", {})
                        diff = total_info.get("amount_difference", 0)
                        if diff != 0:
                            st.metric("Amount Diff", f"${diff:,.2f}")
                    
                    if i < len(problem_items) - 1:
                        st.divider()
        
        else:
            st.success("✅ All items match perfectly!")

def display_comparison_metrics(comparison_data: Dict[str, Any]):
    """
    Display key metrics from the comparison
    """
    summary = comparison_data.get("comparison_summary", {})
    financial = comparison_data.get("financial_summary", {})
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_items = summary.get("total_items_compared", 0)
        st.metric("Total Items", total_items)
    
    with col2:
        discrepancy_items = summary.get("items_with_discrepancies", 0)
        discrepancy_rate = (discrepancy_items / total_items * 100) if total_items > 0 else 0
        st.metric("Discrepancy Rate", f"{discrepancy_rate:.1f}%", 
                 delta=f"{discrepancy_items} items")
    
    with col3:
        amount_diff = financial.get("total_difference", 0)
        st.metric("Amount Difference", f"${amount_diff:,.2f}")
    
    with col4:
        status = summary.get("overall_status", "UNKNOWN")
        status_emoji = "🟢" if status == "PASS" else "🔴" if status == "FAIL" else "🟡"
        st.metric("Status", f"{status_emoji} {status}")
