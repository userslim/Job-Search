import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time

st.set_page_config(page_title="SG Job Automator: Engineering", layout="wide")

st.title("🛠️ Senior Engineer Job Search Automator")
st.subheader("Targeting: ELV, Healthcare Infrastructure & Statutory Compliance")

# User Inputs based on your Resume
keywords = st.sidebar.text_input("Keywords", "Senior Engineer ELV Hospital")
location = st.sidebar.text_input("Location", "Singapore")
pages = st.sidebar.slider("Pages to Scan", 1, 5, 2)

def fetch_jobs(keyword, loc, pg):
    job_list = []
    # Indeed Search URL - We use a common User-Agent to avoid immediate blocks
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }
    
    for i in range(0, pg * 10, 10):
        url = f"https://sg.indeed.com/jobs?q={keyword.replace(' ', '+')}&l={loc}&start={i}"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            jobs = soup.find_all('div', class_='job_seen_beacon')
            
            for job in jobs:
                title = job.find('h2').text if job.find('h2') else "N/A"
                company = job.find('span', {'data-testid': 'company-name'}).text if job.find('span', {'data-testid': 'company-name'}) else "N/A"
                link = "https://sg.indeed.com" + job.find('a')['href'] if job.find('a') else "#"
                
                # Filter logic: Ensure it's not a 'Junior' role
                if "junior" not in title.lower():
                    job_list.append({"Title": title, "Company": company, "Link": link})
        
        time.sleep(2) # Engineering safety delay
    return job_list

if st.button("Run Automation"):
    with st.spinner('Scanning sg.indeed.com for high-value matches...'):
        results = fetch_jobs(keywords, location, pages)
        if results:
            df = pd.DataFrame(results)
            st.success(f"Found {len(df)} matching roles!")
            
            # Displaying as a clean table
            st.dataframe(df, use_container_width=True)
            
            # Export for your personal tracking
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Download Job Tracker (CSV)", csv, "jobs.csv", "text/csv")
        else:
            st.error("Access blocked or no jobs found. (Indeed has high security; try again in 5 mins)")

st.info("Pro-Tip: Use this tool to find 'ELV' and 'Statutory' roles before they get crowded.")