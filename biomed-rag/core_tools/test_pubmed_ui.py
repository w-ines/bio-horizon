# test_pubmed_ui.py
import streamlit as st
from pubmed_tool import search_pubmed, PubMedSearchEngine

st.set_page_config(page_title="PubMed Advanced Search Tester", layout="wide")

st.title("🔬 PubMed Advanced Search - Test Interface")
st.markdown("Test des nouvelles fonctionnalités : filtres avancés + caching Redis")

# Sidebar - Configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Query
    query = st.text_input(
        "🔍 Search Query",
        value="CRISPR gene editing",
        help="Supports PubMed syntax: [Title], [MeSH], AND, OR"
    )
    
    # Basic params
    max_results = st.slider("Max Results", 5, 50, 10)
    
    st.divider()
    
    # Advanced Filters
    st.subheader("🎯 Advanced Filters")
    
    # Publication Types
    pub_types = st.multiselect(
        "Publication Types",
        ["Clinical Trial", "Meta-Analysis", "Review", "RCT", 
         "Systematic Review", "Case Reports", "Research Article"],
        help="Filter by publication type"
    )
    
    # Journals
    journals_input = st.text_area(
        "Journals (one per line)",
        value="Nature\nScience\nCell",
        help="Filter by specific journals"
    )
    journals = [j.strip() for j in journals_input.split("\n") if j.strip()]
    
    # Language
    language = st.selectbox(
        "Language",
        ["", "eng", "fre", "ger", "spa"],
        format_func=lambda x: "All" if x == "" else x
    )
    
    # Species
    species = st.multiselect(
        "Species/Organism",
        ["Humans", "Mice", "Rats", "Escherichia coli"],
        help="Filter by species"
    )
    
    # Date range
    st.divider()
    st.subheader("📅 Date Range")
    col1, col2 = st.columns(2)
    with col1:
        mindate = st.text_input("Min Date", "2024", help="YYYY or YYYY/MM/DD")
    with col2:
        maxdate = st.text_input("Max Date", "", help="YYYY or YYYY/MM/DD")
    
    # Search button
    st.divider()
    search_btn = st.button("🔍 Search PubMed", type="primary", use_container_width=True)

# Main area - Results
if search_btn:
    with st.spinner("🔄 Searching PubMed..."):
        import time
        start_time = time.time()
        
        result = search_pubmed(
            query=query,
            max_results=max_results,
            publication_types=pub_types if pub_types else None,
            journals=journals if journals else None,
            language=language if language else "",
            species=species if species else None,
            mindate=mindate,
            maxdate=maxdate,
            fetch_details=True
        )
        
        elapsed = time.time() - start_time
    
    # Display results
    if "error" in result:
        st.error(f"❌ Error: {result['error']}")
    else:
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Results", result['total'])
        with col2:
            st.metric("PMIDs Returned", len(result['pmids']))
        with col3:
            st.metric("Articles Fetched", len(result['articles']))
        with col4:
            st.metric("Query Time", f"{elapsed:.2f}s")
        
        # Cache indicator
        if elapsed < 0.5:
            st.success("💾 Cache Hit! (Fast response)")
        else:
            st.info("🌐 API Call (First time or cache miss)")
        
        st.divider()
        
        # Articles display
        if result['articles']:
            st.subheader(f"📚 Articles ({len(result['articles'])} fetched)")
            
            for i, article in enumerate(result['articles'], 1):
                with st.expander(f"**{i}. {article['title']}**"):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.markdown(f"**Journal:** {article['journal']}")
                        st.markdown(f"**Date:** {article['pub_date']}")
                        st.markdown(f"**PMID:** [{article['pmid']}](https://pubmed.ncbi.nlm.nih.gov/{article['pmid']})")
                        
                        if article['authors']:
                            st.markdown(f"**Authors:** {', '.join(article['authors'][:3])}" + 
                                      (f" et al." if len(article['authors']) > 3 else ""))
                    
                    with col2:
                        if article['mesh_terms']:
                            st.markdown("**MeSH Terms:**")
                            for term in article['mesh_terms'][:5]:
                                st.markdown(f"- {term}")
                    
                    if article['abstract']:
                        st.markdown("**Abstract:**")
                        st.text_area("", article['abstract'], height=150, key=f"abstract_{i}", disabled=True)
        else:
            st.warning("No articles found with current filters")

# Footer
st.divider()
st.markdown("""
### 💡 Tips
- **Cache Test**: Run same query twice to see caching in action
- **Advanced Syntax**: Use `[Title]`, `[MeSH]`, `AND`, `OR` in query
- **Filters**: Combine multiple filters for precise results
""")