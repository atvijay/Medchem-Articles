import requests
import pandas as pd
import streamlit as st
from datetime import datetime
import time

# --- 1. Dashboard Configuration ---
st.set_page_config(page_title="MedChem Articles Dashboard", layout="wide")

# Your Elsevier API Key for Cell/ScienceDirect
ELSEVIER_API_KEY = "53600672464eaa44118e455655e8d412" 

JOURNAL_BINS = {
    "Medicinal Chemistry": {
        "issns": ["0022-2623", "1948-5875", "1860-7179", "2632-8682", "1359-6446", "0968-0896", "0960-894X", "1552-4450", "1078-8956", "2451-9456"],
        "display": "JMC, ACS MCL, ChemMedChem, RSC, DDT, BMCL, Nature, Cell"
    },
    "Cheminformatics & CompChem": {
        "issns": ["1758-2946", "1549-9596", "0022-2623"],
        "display": "J. Cheminform, JCIM, J. Med. Chem."
    },
    "DMPK": {
        "issns": ["1347-4367", "1880-0920", "0022-2623"],
        "display": "DMPK Journal, J. Med. Chem."
    }
}

# --- 2. Helper Functions ---

def get_image_url(doi, publisher):
    """Predicts graphical abstract URLs for ACS and RSC journals"""
    suffix = doi.split("/")[-1]
    if "American Chemical Society" in publisher:
        # Standard ACS TOC pattern
        return f"https://pubs.acs.org/cms/10.1021/{suffix}/asset/images/medium/{suffix}_abs.gif"
    elif "Royal Society of Chemistry" in publisher:
        # Standard RSC TOC pattern
        return f"https://www.rsc.org/library/RO/img/graphical-abstracts/{suffix.lower()}.gif"
    return None

def fetch_stratified_data(issn_list, depth):
    """Loops through each journal to ensure a diverse feed"""
    base_url = "https://api.crossref.org/works"
    results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()

    for idx, issn in enumerate(issn_list):
        status_text.text(f"Fetching from ISSN: {issn}...")
        params = {
            'filter': f'type:journal-article,issn:{issn}',
            'sort': 'published', 'order': 'desc', 'rows': depth
        }
        try:
            response = requests.get(base_url, params=params, timeout=10)
            if response.status_code == 200:
                items = response.json().get('message', {}).get('items', [])
                for item in items:
                    d_parts = item.get('issued', {}).get('date-parts', [[2026, 1, 1]])[0]
                    doi = item.get('DOI')
                    pub = item.get('publisher', 'Unknown')
                    
                    results.append({
                        'SortDate': datetime(d_parts[0], d_parts[1] if len(d_parts)>1 else 1, d_parts[2] if len(d_parts)>2 else 1),
                        'DisplayDate': f"{d_parts[0]}-{d_parts[1]:02d}",
                        'Journal': item.get('container-title', ['N/A'])[0],
                        'Title': item.get('title', ['No Title'])[0],
                        'DOI': doi,
                        'Publisher': pub,
                        'Image': get_image_url(doi, pub)
                    })
            time.sleep(0.1) # Be polite to the API
        except: continue
        progress_bar.progress((idx + 1) / len(issn_list))

    status_text.empty()
    progress_bar.empty()
    return results

# --- 3. Sidebar UI ---
st.sidebar.title(" Journal Feeds")
discipline = st.sidebar.radio("Select Category:", list(JOURNAL_BINS.keys()))
st.sidebar.info(f"**Targeting:** {JOURNAL_BINS[discipline]['display']}")
limit_per_journal = st.sidebar.slider("Articles per journal:", 2, 15, 5)

# --- 4. Main Display ---
st.title(f" {discipline} Feed")

if st.button(f"Pull Latest from {discipline}"):
    with st.spinner("Compiling cross-journal feed..."):
        data = fetch_stratified_data(JOURNAL_BINS[discipline]['issns'], limit_per_journal)
        
        if data:
            df = pd.DataFrame(data).sort_values(by='SortDate', ascending=False)
            
            for _, row in df.iterrows():
                with st.container():
                    col1, col2 = st.columns([1, 3])
                    
                    with col1:
                        # --- CRITICAL FIX: The Type Check ---
                        img_val = row['Image']
                        if isinstance(img_val, str) and img_val.strip():
                            try:
                                st.image(img_val, use_container_width=True)
                            except:
                                st.caption("🖼️ Preview Blocked")
                        else:
                            # Elsevier specific note
                            if "Elsevier" in row['Publisher'] or "Cell" in row['Publisher']:
                                st.info("Elsevier: View via DOI")
                            else:
                                st.caption("No Preview Available")
                    
                    with col2:
                        st.markdown(f"#### [{row['Title']}](https://doi.org/{row['DOI']})")
                        st.write(f"**{row['Journal']}** | {row['DisplayDate']}")
                        st.caption(f"DOI: {row['DOI']} | Publisher: {row['Publisher']}")
                    
                    st.divider()
        else:
            st.warning("No articles found.")
