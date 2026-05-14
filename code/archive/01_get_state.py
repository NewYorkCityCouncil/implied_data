import requests
from collections import defaultdict
from flatten_json import flatten
exec(open('../tokens.R').read())

API_KEY = stateleg_key
LAW_ID = "EDN"

################################################################################
# get laws
################################################################################

# Pull all text
structure_url = f"https://legislation.nysenate.gov/api/3/laws/{LAW_ID}?full=true&key={API_KEY}"
response = requests.get(structure_url).json()

# Flatten 
flat_json = flatten(response['result']['documents']['documents'], '.')
flat_text = {key: value * 2 for key, value in flat_json.items() if "text" in key.lower()} 

# Pull text and save out
flat_text = [value for key, value in flat_text.items()]
flat_text = " ".join(flat_text)
with open("data/input/nys_code/Education_adcode.txt", "a") as f:
  f.write("Now the file has more content!")


################################################################################
# get rules
################################################################################

import requests
from bs4 import BeautifulSoup
import time
import re

BASE_URL = "https://www.law.cornell.edu"
# Starting point for all Education regulations
TITLE_8_URL = "https://www.law.cornell.edu/regulations/new-york/title-8"

def get_soup(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        return BeautifulSoup(r.text, 'html.parser')
    except Exception as e:
        print(f"Error loading {url}: {e}")
        return None

def scrape_title_8(url):
    soup = get_soup(url)
    if not soup: return

    # Check if this is a "leaf node" (a page with actual regulation text)
    # Cornell usually puts the regulation text inside a 'div' with class 'content' 
    # and the section number in the title/h1
    reg_text = soup.find('div', class_='content')
    if reg_text and "§" in soup.title.text:
        section_title = soup.title.text.strip()
        print(f"--- Extracting Text: {section_title} ---")
        return {section_title: reg_text.get_text(separator='\n', strip=True)}

    # Otherwise, find all links that stay within Title 8 to keep digging
    results = {}
    links = soup.find_all('a', href=True)
    
    # We only want links that look like part of the Title 8 hierarchy
    # Avoiding external links or footer links
    sub_links = []
    for l in links:
        href = l['href']
        if "/regulations/new-york/title-8" in href or "/regulations/new-york/8-NYCRR" in href:
            full_url = BASE_URL + href if href.startswith('/') else href
            if full_url != url: # Avoid infinite loops
                sub_links.append(full_url)

    # Unique links only
    for sub_url in list(set(sub_links))[:5]: # Limit for testing! Remove [:5] for full scrape
        time.sleep(1) # Be a good guest
        data = scrape_title_8(sub_url)
        if data:
            results.update(data)
            
    return results

if __name__ == "__main__":
    # Start the engine
    all_education_regs = scrape_title_8(TITLE_8_URL)
    
    # Save results
    with open("ny_title_8_regs.txt", "w", encoding="utf-8") as f:
        for title, body in all_education_regs.items():
            f.write(f"{title}\n{body}\n\n{'='*50}\n\n")
            

################################################################################
# get charter
################################################################################