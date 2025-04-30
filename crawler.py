from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import concurrent.futures
import os

def crawl_year(year):
    # Setup headless Chrome options for CI
    options = Options()
    options.add_argument("--headless")  # Headless mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 15)

    driver.get("https://libportal.manipal.edu/MIT/Question%20Paper.aspx")
    time.sleep(2)

    pdfs = []

    def find_and_click_folder(target_name):
        time.sleep(2)
        folder_links = driver.find_elements(By.XPATH, "//a[starts-with(@id, 'ctl') and contains(@href, '__doPostBack') and img[contains(@src, 'folder')]]")
        for folder in folder_links:
            if folder.text.strip() == target_name:
                print(f"📂 Found target folder: {target_name}")
                wait.until(EC.element_to_be_clickable(folder)).click()
                time.sleep(2)
                return True
        print(f"❌ Could not find folder: {target_name}")
        return False

    def crawl_folder(path_so_far, depth=0):
        time.sleep(2)
        folder_links = driver.find_elements(By.XPATH, "//a[starts-with(@id, 'ctl') and contains(@href, '__doPostBack') and img[contains(@src, 'folder')]]")
        folder_texts = [a.text.strip() for a in folder_links]

        for idx, folder in enumerate(folder_links):
            label = folder_texts[idx]
            if label == "..":
                continue
            print("📂" + "  " * depth + f"Entering: {label}")

            fresh_folder_links = driver.find_elements(By.XPATH, "//a[starts-with(@id, 'ctl') and contains(@href, '__doPostBack') and img[contains(@src, 'folder')]]")
            fresh_folder = None
            for f in fresh_folder_links:
                if f.text.strip() == label:
                    fresh_folder = f
                    break

            if fresh_folder:
                wait.until(EC.element_to_be_clickable(fresh_folder)).click()
                time.sleep(2)
                crawl_folder(path_so_far + [label], depth + 1)
                back_folder = driver.find_elements(By.XPATH, "//a[contains(text(), '..')]")
                if back_folder:
                    wait.until(EC.element_to_be_clickable(back_folder[0])).click()
                    time.sleep(2)

        pdf_links = driver.find_elements(By.XPATH, "//a[contains(@href, '.pdf')]")
        for pdf in pdf_links:
            href = pdf.get_attribute("href")
            name = pdf.text.strip()
            if href:
                record = {
                    "path": path_so_far,
                    "name": name,
                    "url": href
                }
                print("📄" + "  " * depth + f"{name}")
                pdfs.append(record)

    try:
        print(f"🔍 Looking for {year} folder...")
        found_year = find_and_click_folder(str(year))

        if found_year:
            crawl_folder([str(year)])
        else:
            print(f"Starting from root since {year} folder wasn't found")
            crawl_folder([])

        os.makedirs("pdf_results", exist_ok=True)
        output_file = f"pdf_results/{year}_pdfs.json"
        with open(output_file, "w") as f:
            json.dump(pdfs, f, indent=2)

        print(f"\n✅ Year {year}: Total PDFs collected: {len(pdfs)}")
        return year, len(pdfs)

    finally:
        driver.quit()

def main():
    os.makedirs("pdf_results", exist_ok=True)
    years_to_crawl = [2019, 2015, 2014,2013,2012,2011]

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(years_to_crawl)) as executor:
        future_to_year = {executor.submit(crawl_year, year): year for year in years_to_crawl}
        for future in concurrent.futures.as_completed(future_to_year):
            year = future_to_year[future]
            try:
                year, count = future.result()
                print(f"✔ Completed crawling for {year} with {count} PDFs")
            except Exception as e:
                print(f"❌ Error crawling {year}: {e}")

if __name__ == '__main__':
    main()
