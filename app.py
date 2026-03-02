import streamlit as st
import pandas as pd
import requests
import time

# --- Page configuration ---
st.set_page_config(page_title="SG Engineering Job Automator", layout="wide")

st.title("🛠️ Senior Engineer Job Search Automator")
st.subheader("Direct API Access: ELV, Healthcare & Infrastructure")

# --- Sidebar: API Credentials ---
# You can get these for free at developer.adzuna.com
st.sidebar.header("API Configuration")
ADZUNA_APP_ID = st.sidebar.text_input("Adzuna App ID", type="password")
ADZUNA_APP_KEY = st.sidebar.text_input("Adzuna App Key", type="password")

# --- Sidebar: Search Filters ---
keywords = st.sidebar.text_input("Keywords", "Senior Engineer ELV Hospital")
location = st.sidebar.text_input("Location", "Singapore")
results_count = st.sidebar.slider("Number of results", 10, 50, 20)

# Salary Filter (Adzuna handles this natively in the API)
min_salary = st.sidebar.number_input("Min Monthly Salary (SGD)", value=8000)

# --- The Logic ---
def fetch_jobs_adzuna(app_id, app_key, query, loc, count, salary):
    # Adzuna uses annual salary, so we convert your monthly input
    annual_min = salary * 12
    
    # Adzuna API Endpoint for Singapore (sg)
    url = f"https://api.adzuna.com/v1/api/jobs/sg/search/1"
    params = {
        'app_id': app_id,
        'app_key': app_key,
        'results_per_page': count,
        'what': query,
        'where': loc,
        'salary_min': annual_min,
        'content-type': 'application/json'
    }
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            jobs = []
            for item in data.get('results', []):
                # Senior Engineer Logic: Skip anything with "Junior" in title
                if "junior" in item.get('title', '').lower():
                    continue
                
                jobs.append({
                    "Title": item.get('title'),
                    "Company": item.get('company', {}).get('display_name'),
                    "Location": item.get('location', {}).get('display_name'),
                    "Monthly Salary (Est)": round(item.get('salary_min', 0) / 12) if item.get('salary_min') else "N/A",
                    "Source": item.get('redirect_url').split('/')[2], # Shows the original site
                    "Link": item.get('redirect_url')
                })
            return jobs
        else:
            st.error(f"API Error: {response.status_code}. Check your credentials.")
            return []
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return []

# --- Execution ---
if st.button("Run Engineering Scan"):
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        st.warning("Please enter your Adzuna API credentials in the sidebar.")
    else:
        with st.spinner('Accessing SG Job Aggregator...'):
            results = fetch_jobs_adzuna(ADZUNA_APP_ID, ADZUNA_APP_KEY, keywords, location, results_count, min_salary)
            
            if results:
                df = pd.DataFrame(results)
                st.success(f"Found {len(df)} Senior-level matches!")
                
                # Make links clickable
                st.dataframe(
                    df, 
                    column_config={"Link": st.column_config.LinkColumn("Apply Link")},
                    use_container_width=True
                )
                
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("Download CSV Tracker", csv, "sg_engineering_jobs.csv", "text/csv")
            else:
                st.info("No jobs found matching those exact criteria. Try broadening your keywords.")

st.divider()
st.info("💡 **Why use an API?** Scraping Indeed directly often triggers 'Bot Detection'. This API version is stable, legal, and pulls data from multiple sites (Indeed, JobStreet, etc.) at once.")
