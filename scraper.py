import json
import os
import re
import time
from bs4 import BeautifulSoup
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests

# 1. Google Sheet Auth
scope = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive',
]
creds_dict = json.loads(os.environ['GCP_SA_KEY'])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Sheet ka exact naam daalein
SHEET_NAME = 'Oman_Tenders_Tracker'
sh = client.open(SHEET_NAME)

try:
  worksheet = sh.worksheet('Cybersecurity_Tenders')
except gspread.WorksheetNotFound:
  worksheet = sh.add_worksheet(
      title='Cybersecurity_Tenders', rows='1000', cols='8'
  )
  worksheet.append_row([
      'Tender No',
      'Title',
      'Agency',
      'Purchase Deadline',
      'Submission Deadline',
      'Status',
      'Scraped Date',
  ])

# 2. Keywords Setup
CYBER_KEYWORDS = [
    'cyber security',
    'cybersecurity',
    'information security',
    'infosec',
    'soc',
    'security operations center',
    'siem',
    'firewall',
    'endpoint security',
    'vulnerability assessment',
    'penetration testing',
    'vapt',
    'dlp',
    'zero trust',
    'network security',
    'threat intelligence',
    'edr',
    'xdr',
    'iso 27001',
    'ciso',
    'iam',
    'identity and access',
    'waf',
    'ddos',
    'pam',
    'cloud security',
    'الأمن السيبراني',
    'أمن المعلومات',
]


def is_cyber(text):
  t = text.lower()
  return any(kw in t for kw in CYBER_KEYWORDS)


# 3. Scrape Loop (Portal Pages)
headers = {'User-Agent': 'Mozilla/5.0'}
base_url = (
    'https://etendering.tenderboard.gov.om/supplier/public/tender/list' # Portal URL
)
matched_rows = []

print('Starting Scraper...')
for page in range(1, 40): # Maximum archive pages
  try:
    res = requests.get(
        base_url, params={'page': page}, headers=headers, timeout=15
    )
    if res.status_code != 200:
      break

    soup = BeautifulSoup(res.text, 'html.parser')
    rows = soup.find_all('tr', class_='tender-row')
    if not rows:
      break

    for r in rows:
      cols = [c.text.strip() for c in r.find_all('td')]
      if not cols:
        continue
      title = cols[1] if len(cols) > 1 else ''

      if is_cyber(title):
        matched_rows.append([
            cols[0] if len(cols) > 0 else '',
            title,
            cols[2] if len(cols) > 2 else '',
            cols[3] if len(cols) > 3 else '',
            cols[4] if len(cols) > 4 else '',
            cols[5] if len(cols) > 5 else '',
            time.strftime('%Y-%m-%d'),
        ])
    time.sleep(1)
  except Exception as e:
    print(f'Error on page {page}: {e}')
    break

# 4. Batch Append to Google Sheet
if matched_rows:
  worksheet.append_rows(matched_rows)
  print(f'Successfully added {len(matched_rows)} tenders to Google Sheet!')
else:
  print('No matching tenders found.')

