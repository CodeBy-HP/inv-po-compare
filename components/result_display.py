import streamlit as st
import pandas as pd
from typing import Dict, Any

def display_gemini_results(gemini_response: Dict[str, Any]):
    """
    Display Gemini's structured analysis results in the Streamlit UI
    """
    if not gemini_response.get("success"):
        st.error("❌ Failed to get structured analysis from Gemini")
        with st.expander("🔍 Debug Information"):
            st.write("**Error:**", gemini_response.get("error", "Unknown error"))
            if "raw_response" in gemini_response:
                st.write("**Raw Response (first 1000 chars):**")
                st.code(gemini_response["raw_response"])
        return
    
    data = gemini_response["data"]
    
    # Analysis Summary
    st.subheader("🎯 Analysis Summary")
    summary = data.get("analysis_summary", {})
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Data Type", summary.get("data_type", "Unknown"))
    with col2:
        st.metric("Confidence", summary.get("confidence_level", "Unknown"))
    with col3:
        st.metric("Use Case", summary.get("primary_use_case", "Unknown"))
    
    # Structured Data
    if "structured_data" in data:
        st.subheader("📊 Structured Data")
        
        # Entities
        entities = data["structured_data"].get("entities", [])
        if entities:
            st.write("**🏢 Business Entities Found:**")
            entities_df = pd.DataFrame(entities)
            st.dataframe(entities_df, use_container_width=True)
        
        # Relationships
        relationships = data["structured_data"].get("relationships", [])
        if relationships:
            st.write("**🔗 Data Relationships:**")
            relationships_df = pd.DataFrame(relationships)
            st.dataframe(relationships_df, use_container_width=True)
    
    # Data Quality
    if "data_quality" in data:
        st.subheader("🔍 Data Quality Assessment")
        quality = data["data_quality"]
        
        col1, col2 = st.columns(2)
        with col1:
            completeness = quality.get("completeness_score", 0)
            st.metric("Completeness Score", f"{completeness:.1%}")
        
        with col2:
            issues = quality.get("issues_found", [])
            st.metric("Issues Found", len(issues))
        
        if issues:
            st.write("**⚠️ Issues Found:**")
            for issue in issues:
                st.warning(issue)
        
        recommendations = quality.get("recommendations", [])
        if recommendations:
            st.write("**💡 Recommendations:**")
            for rec in recommendations:
                st.info(rec)
    
    # Business Insights
    if "business_insights" in data:
        st.subheader("💼 Business Insights")
        insights = data["business_insights"]
        
        for i, insight in enumerate(insights):
            with st.expander(f"💡 Insight {i+1}: {insight.get('insight', 'No title')[:50]}..."):
                st.write("**Insight:**", insight.get("insight", ""))
                st.write("**Supporting Data:**", insight.get("supporting_data", ""))
                st.write("**Actionability:**", insight.get("actionability", ""))
    
    # Suggested Visualizations
    if "suggested_visualizations" in data:
        st.subheader("📈 Suggested Visualizations")
        viz_suggestions = data["suggested_visualizations"]
        
        for viz in viz_suggestions:
            with st.container():
                st.write(f"**📊 {viz.get('chart_type', 'Unknown Chart')}**")
                st.write(f"*Purpose:* {viz.get('purpose', 'No purpose specified')}")
                if viz.get('data_columns'):
                    st.write(f"*Columns to use:* {', '.join(viz['data_columns'])}")
                st.divider()

def display_raw_json(data: Dict[str, Any], title: str = "Raw JSON Data"):
    """
    Display raw JSON data in an expandable section for debugging
    """
    with st.expander(f"🔧 {title}"):
        st.json(data)
