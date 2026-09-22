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
    wait = WebDriverWait(driver, 10)

    driver.get("https://libportal.manipal.edu/MIT/Question%20Paper.aspx")
    time.sleep(0.5)

    pdfs = []

    def get_folder_links():
        return driver.find_elements(By.XPATH, "//a[starts-with(@id, 'ctl') and contains(@href, '__doPostBack') and img[contains(@src, 'folder')]]")

    def click_folder_by_name(target_name):
        for folder in get_folder_links():
            if folder.text.strip() == target_name:
                wait.until(EC.element_to_be_clickable(folder)).click()
                time.sleep(0.3)
                return True
        return False

    def find_and_click_folder(target_name):
        if click_folder_by_name(target_name):
            print(f"📂 Found target folder: {target_name}")
            return True
        print(f"❌ Could not find folder: {target_name}")
        return False

    def crawl_folder(path_so_far, depth=0):
        folder_links = get_folder_links()
        for folder in folder_links:
            label = folder.text.strip()
            if label == "..":
                continue
            print("📂" + "  " * depth + f"Entering: {label}")
            try:
                if not click_folder_by_name(label):
                    continue
                crawl_folder(path_so_far + [label], depth + 1)
                back_folder = driver.find_elements(By.XPATH, "//a[contains(text(), '..')]")
                if back_folder:
                    wait.until(EC.element_to_be_clickable(back_folder[0])).click()
                    time.sleep(0.3)
            except Exception:
                # Ignore folders that disappear or fail to click during traversal.
                continue

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
        os.makedirs("output", exist_ok=True)

        pdf_file = f"pdf_results/{year}_pdfs.json"
        with open(pdf_file, "w") as f:
            json.dump(pdfs, f, indent=2)

        output_file = f"output/{year}_pdfs.json"
        with open(output_file, "w") as f:
            json.dump(pdfs, f, indent=2)

        print(f"\n✅ Year {year}: Total PDFs collected: {len(pdfs)}")
        return year, len(pdfs)

    finally:
        driver.quit()

def main():
    os.makedirs("pdf_results", exist_ok=True)
    years_to_crawl = [2025]
    os.makedirs("output", exist_ok=True)


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
