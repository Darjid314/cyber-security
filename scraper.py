import json
import os
import re
import time
from bs4 import BeautifulSoup
from google.oauth2.service_account import Credentials
import gspread
import requests

# 1. Google Sheet Authentication (Modern & Robust)
scope = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
]

# Secret read karein
raw_creds = os.environ.get('GCP_SA_KEY', '')

try:
  creds_dict = json.loads(raw_creds)
except Exception:
  # Agar JSON formatting me newline issue ho
  creds_dict = json.loads(raw_creds.replace('\n', '\\n'))

# Ensure private key newline characters are intact
if 'private_key' in creds_dict:
  creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')

creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
client = gspread.authorize(creds)

# Sheet open karein (Aapki Google Sheet ka exact title)
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
for page in range(1, 40):
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
