import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re
from random import uniform
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

st.set_page_config(page_title="SG Job Automator: Engineering", layout="wide")

st.title("🛠️ Senior Engineer Job Search Automator")
st.subheader("Targeting: ELV, Healthcare Infrastructure & Statutory Compliance")

# Sidebar inputs
keywords = st.sidebar.text_input("Keywords", "Senior Engineer ELV Hospital")
location = st.sidebar.text_input("Location", "Singapore")
pages = st.sidebar.slider("Pages to Scan", 1, 5, 2)

# Job portal choice
portal = st.sidebar.selectbox("Job Portal", ["Indeed", "JobStreet"])

# Salary filter
enable_salary_filter = st.sidebar.checkbox("Filter by salary (8k–10k SGD/month)", value=True)
if enable_salary_filter:
    salary_min = st.sidebar.number_input("Min monthly salary (SGD)", min_value=0, value=8000, step=500)
    salary_max = st.sidebar.number_input("Max monthly salary (SGD)", min_value=0, value=10000, step=500)
else:
    salary_min, salary_max = 0, 1_000_000

# --- Helper functions ---
def parse_salary(text):
    """Extract monthly salary range from text."""
    if not text:
        return None, None
    text = text.replace(',', '').lower()
    # Match patterns like $5,000, $6k, $5000 - $6000, $60k - $72k per year
    numbers = re.findall(r'\$?(\d+(?:\.\d+)?)\s*(k)?', text)
    if not numbers:
        return None, None

    # Convert to numbers, handling 'k' suffix
    values = []
    for num, k in numbers:
        val = float(num)
        if k:
            val *= 1000
        values.append(val)

    # Determine if annual (keywords present)
    if 'year' in text or 'annual' in text or 'per annum' in text:
        values = [v / 12 for v in values]

    min_sal = min(values)
    max_sal = max(values)
    return round(min_sal), round(max_sal)

def create_session():
    """Create a requests session with retry strategy and browser-like headers."""
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))

    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    })
    return session

def fetch_indeed(session, keyword, loc, pg):
    job_list = []
    base_url = "https://sg.indeed.com/jobs"
    for start in range(0, pg * 10, 10):
        params = {
            'q': keyword,
            'l': loc,
            'start': start
        }
        try:
            resp = session.get(base_url, params=params, timeout=15)
            if resp.status_code != 200:
                st.warning(f"Indeed returned HTTP {resp.status_code} – skipping page")
                continue
        except Exception as e:
            st.warning(f"Request error: {e}")
            continue

        soup = BeautifulSoup(resp.text, 'html.parser')
        jobs = soup.find_all('div', class_='job_seen_beacon')
        for job in jobs:
            title_elem = job.find('h2')
            if not title_elem:
                continue
            title = title_elem.text.strip()
            if 'junior' in title.lower():
                continue

            company_elem = job.find('span', {'data-testid': 'company-name'})
            company = company_elem.text.strip() if company_elem else 'N/A'

            link_elem = job.find('a')
            link = 'https://sg.indeed.com' + link_elem['href'] if link_elem and link_elem.get('href') else '#'

            # Salary
            salary_elem = job.find('div', {'data-testid': 'attribute_snippet_testid'}) or \
                          job.find('div', class_='salary-snippet')
            salary_text = salary_elem.text.strip() if salary_elem else None
            min_sal, max_sal = parse_salary(salary_text)

            if enable_salary_filter:
                if min_sal and max_sal:
                    if max_sal < salary_min or min_sal > salary_max:
                        continue
                else:
                    continue  # skip jobs without salary info (optional)

            job_list.append({
                'Title': title,
                'Company': company,
                'Salary (SGD/month)': f'{min_sal}–{max_sal}' if min_sal and max_sal else 'Not shown',
                'Link': link
            })

        time.sleep(uniform(3, 5))  # random delay
    return job_list

def fetch_jobstreet(session, keyword, loc, pg):
    # JobStreet SG search URL structure
    job_list = []
    base_url = "https://www.jobstreet.com.sg/en/job-search/"
    # They use 'keywords' and 'location' params
    for page in range(1, pg + 1):
        params = {
            'keywords': keyword,
            'location': loc,
            'page': page
        }
        try:
            resp = session.get(base_url, params=params, timeout=15)
            if resp.status_code != 200:
                st.warning(f"JobStreet returned HTTP {resp.status_code}")
                continue
        except Exception as e:
            st.warning(f"JobStreet error: {e}")
            continue

        soup = BeautifulSoup(resp.text, 'html.parser')
        # JobStreet cards – this may change; inspect actual classes
        jobs = soup.find_all('article', {'data-automation': 'normalJob'})
        for job in jobs:
            title_elem = job.find('a', {'data-automation': 'jobTitle'})
            if not title_elem:
                continue
            title = title_elem.text.strip()
            if 'junior' in title.lower():
                continue

            company_elem = job.find('a', {'data-automation': 'jobCompany'})
            company = company_elem.text.strip() if company_elem else 'N/A'

            link = title_elem.get('href')
            if link and not link.startswith('http'):
                link = 'https://www.jobstreet.com.sg' + link

            # Salary snippet
            salary_elem = job.find('span', {'data-automation': 'jobSalary'})
            salary_text = salary_elem.text.strip() if salary_elem else None
            min_sal, max_sal = parse_salary(salary_text)

            if enable_salary_filter:
                if min_sal and max_sal:
                    if max_sal < salary_min or min_sal > salary_max:
                        continue
                else:
                    continue

            job_list.append({
                'Title': title,
                'Company': company,
                'Salary (SGD/month)': f'{min_sal}–{max_sal}' if min_sal and max_sal else 'Not shown',
                'Link': link
            })

        time.sleep(uniform(2, 4))
    return job_list

# --- Main ---
if st.button("Run Automation"):
    session = create_session()
    with st.spinner(f'Scanning {portal} for high-value matches...'):
        if portal == 'Indeed':
            results = fetch_indeed(session, keywords, location, pages)
        else:
            results = fetch_jobstreet(session, keywords, location, pages)

        if results:
            df = pd.DataFrame(results)
            st.success(f"Found {len(df)} matching roles!")
            st.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Download Job Tracker (CSV)", csv, "jobs.csv", "text/csv")
        else:
            st.error("No jobs found. Possible reasons:\n"
                     "- Blocked by the site (try JobStreet or use a VPN)\n"
                     "- No jobs match your salary filter\n"
                     "- The site’s HTML structure changed – update selectors")

st.info("⚠️ Indeed has strong anti‑scraping measures. If you keep getting 401, try JobStreet or use the site’s own search.")
