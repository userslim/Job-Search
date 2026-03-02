import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re

st.set_page_config(page_title="SG Job Automator: Engineering", layout="wide")

st.title("🛠️ Senior Engineer Job Search Automator")
st.subheader("Targeting: ELV, Healthcare Infrastructure & Statutory Compliance")

# Sidebar inputs
keywords = st.sidebar.text_input("Keywords", "Senior Engineer ELV Hospital")
location = st.sidebar.text_input("Location", "Singapore")
pages = st.sidebar.slider("Pages to Scan", 1, 5, 2)

# Salary filter toggle
enable_salary_filter = st.sidebar.checkbox("Filter by salary (8k–10k SGD/month)", value=True)
if enable_salary_filter:
    salary_min = st.sidebar.number_input("Min monthly salary (SGD)", min_value=0, value=8000, step=500)
    salary_max = st.sidebar.number_input("Max monthly salary (SGD)", min_value=0, value=10000, step=500)
else:
    salary_min, salary_max = 0, 1_000_000  # no effective filter

def parse_salary(text):
    """
    Extract monthly salary range from text.
    Returns (min_salary, max_salary) in SGD per month, or (None, None) if not found.
    """
    if not text:
        return None, None

    # Remove commas and normalize
    text = text.replace(',', '').lower()

    # Patterns: $5,000 - $6,000 a month, $60,000 - $72,000 a year, etc.
    # Look for numbers with possible $ prefix and k suffix
    numbers = re.findall(r'\$?(\d+)(?:\s*k)?', text)
    numbers = [int(n) * 1000 if 'k' in part else int(n) for n, part in zip(numbers, re.findall(r'\$?(\d+)(\s*k)?', text))]

    if len(numbers) == 0:
        return None, None

    # Determine if annual or monthly
    if 'year' in text or 'annual' in text or 'per annum' in text:
        # Convert annual to monthly
        numbers = [n / 12 for n in numbers]

    # If only one number, treat as exact
    if len(numbers) == 1:
        min_sal = max_sal = numbers[0]
    else:
        min_sal = min(numbers)
        max_sal = max(numbers)

    return round(min_sal, 0), round(max_sal, 0)

def fetch_jobs(keyword, loc, pg):
    job_list = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }

    for i in range(0, pg * 10, 10):
        url = f"https://sg.indeed.com/jobs?q={keyword.replace(' ', '+')}&l={loc}&start={i}"
        try:
            response = requests.get(url, headers=headers, timeout=10)
        except Exception as e:
            st.warning(f"Request failed: {e}")
            continue

        if response.status_code != 200:
            st.warning(f"HTTP {response.status_code} – skipping page")
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        jobs = soup.find_all('div', class_='job_seen_beacon')

        for job in jobs:
            title_elem = job.find('h2')
            title = title_elem.text if title_elem else "N/A"

            # Skip junior roles (as before)
            if "junior" in title.lower():
                continue

            company_elem = job.find('span', {'data-testid': 'company-name'})
            company = company_elem.text if company_elem else "N/A"

            link_elem = job.find('a')
            link = "https://sg.indeed.com" + link_elem['href'] if link_elem and link_elem.get('href') else "#"

            # --- Salary extraction ---
            salary_elem = job.find('div', {'data-testid': 'attribute_snippet_testid'}) or \
                          job.find('div', class_='salary-snippet') or \
                          job.find('span', class_='estimated-salary')
            salary_text = salary_elem.text if salary_elem else None
            min_sal, max_sal = parse_salary(salary_text)

            # Apply salary filter (if enabled)
            if enable_salary_filter:
                # Include job if we have salary and it overlaps with target range
                if min_sal is not None and max_sal is not None:
                    # Check overlap
                    if max_sal < salary_min or min_sal > salary_max:
                        continue  # no overlap
                else:
                    # No salary info – optionally skip (you can change this)
                    continue

            # Add to list
            job_list.append({
                "Title": title,
                "Company": company,
                "Salary (SGD/month)": f"{min_sal:.0f}–{max_sal:.0f}" if min_sal and max_sal else "Not shown",
                "Link": link
            })

        time.sleep(2)  # Be polite

    return job_list

if st.button("Run Automation"):
    with st.spinner('Scanning sg.indeed.com for high-value matches...'):
        results = fetch_jobs(keywords, location, pages)

        if results:
            df = pd.DataFrame(results)
            st.success(f"Found {len(df)} matching roles (filtered by salary if enabled)!")

            # Display clickable links (Streamlit doesn't render HTML in dataframe, so we show as text)
            st.dataframe(df, use_container_width=True)

            # Export
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Download Job Tracker (CSV)", csv, "jobs.csv", "text/csv")
        else:
            st.error("No jobs found. Indeed may have blocked the request or no jobs match the salary filter.")

st.info("Pro-Tip: Salary extraction is experimental. If you see few results, try disabling the salary filter.")
