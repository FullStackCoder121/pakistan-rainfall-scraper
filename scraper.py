import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from tqdm import tqdm
import os

# Base URL
url = "https://nwfc.pmd.gov.pk/new/rainfall.php"

# Start session
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0"
})

# Step 1: Fetch station options
response = session.get(url)
soup = BeautifulSoup(response.text, 'html.parser')
stations = soup.select("select[name='station'] option")
station_list = [(opt['value'], opt.text.strip()) for opt in stations if opt['value'].isdigit()]

# Step 2: Prepare to store scraped data
rainfall_data = []

# Step 3: Scrape each station using tqdm
print("\n📊 Scraping Rainfall Data...\n")
for station_id, station_name in tqdm(station_list, desc="🔍 Scraping", unit="station"):
    form_data = {
        'station': station_id,
        'filter': 'station'
    }

    try:
        res = session.post(url, data=form_data, timeout=10)
        page = BeautifulSoup(res.text, 'html.parser')
        table = page.find("table", class_="table table-bordered")

        if table:
            rows = table.find_all("tr")[1:]  # skip headers
            for row in rows:
                cols = row.find_all("td")
                if len(cols) == 4:
                    date = cols[3].text.strip()
                    
                    # Skip if date is missing
                    if not date:
                        continue

                    entry = {
                        'Station ID': station_id,
                        'Station Name': station_name,
                        'Province': cols[0].text.strip(),
                        'Reported Station': cols[1].text.strip(),
                        'Rainfall (mm)': cols[2].text.strip(),
                        'Date': date
                    }

                    rainfall_data.append(entry)

                    # 👇 Live output row by row
                    print(f"{entry['Station ID']}, {entry['Station Name']}, {entry['Province']}, "
                          f"{entry['Reported Station']}, {entry['Rainfall (mm)']}, {entry['Date']}")

    except Exception as e:
        print(f"❌ Error on {station_name}: {e}")

    time.sleep(0.5)  # Respect server

# Step 4: Convert to DataFrame
new_df = pd.DataFrame(rainfall_data)

# Step 5: Remove rows with blank or NaT in date before proceeding
new_df = new_df[new_df['Date'].str.strip() != ""]

# Step 6: Load existing CSV if exists, then merge
csv_file = "pakistan_rainfall_data.csv"
if os.path.exists(csv_file):
    existing_df = pd.read_csv(csv_file)
    combined_df = pd.concat([existing_df, new_df], ignore_index=True)
else:
    combined_df = new_df

# Step 7: Convert Date column to datetime and clean
combined_df['Date'] = pd.to_datetime(combined_df['Date'], errors='coerce', dayfirst=True)
combined_df = combined_df.dropna(subset=['Date'])  # remove rows where Date couldn't be parsed
combined_df = combined_df.drop_duplicates(subset=['Station ID', 'Date', 'Reported Station'])

# Step 8: Sort and save
combined_df = combined_df.sort_values(by='Date', ascending=False)
combined_df.to_csv(csv_file, index=False)

print("\n✅ Scraping completed successfully!")
print(f"📁 Updated data saved to: {csv_file}\n")
