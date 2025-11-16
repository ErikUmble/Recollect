from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import requests
import os
import csv
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback

def get_page_issues(driver):
    # Create a dict to store titles and links
    title_link_dict = dict()

    # Get the table of newspapers from the current page
    table_class = "views-element-container"
    table_elements = driver.find_elements(By.CLASS_NAME, table_class)

    # Find and extract all issue names and links for page
    if len(table_elements) == 0:
        print("ERROR: No table elements found.")
    else:
        first = table_elements[0]
        issues = first.find_elements(By.CSS_SELECTOR, "[data-history-node-id]")
        for curr_issue in issues:
            h2 = curr_issue.find_element(By.TAG_NAME, "h2")
            link = h2.find_element(By.TAG_NAME, "a")
            href = link.get_attribute("href")
            text = link.text
            title_link_dict[text] = href

    return title_link_dict

def step_through_pages(driver):
    # Get information for first page
    title_link_dict = get_page_issues(driver)

    # Step through remaining pages and collect information
    for curr_page in range(2, 58):

        navigation_bar = driver.find_elements(By.TAG_NAME, "nav")[4]
        list_items = navigation_bar.find_elements(By.CSS_SELECTOR, "li.page-item")
        found = False
        for item in list_items:
            try:
                link = item.find_element(By.TAG_NAME, "a")
                if link.text.isdigit() and int(link.text.strip()) == curr_page:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link)
                    clickable_link = WebDriverWait(driver, 20).until(
                        EC.element_to_be_clickable((By.XPATH, f".//a[text()='{link.text.strip()}']"))
                    )
                    found = True
                    driver.execute_script("arguments[0].click();", clickable_link)
                    WebDriverWait(driver, 10).until(EC.staleness_of(navigation_bar))
                    temp_dict = get_page_issues(driver)
                    title_link_dict = title_link_dict | temp_dict
                    break
            except:
                continue

        if not found:
            next_link = driver.find_element(By.CSS_SELECTOR, "[title='Go to next page']")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_link)
            clickable_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, f".//a[title='Go to next page']"))
            )
            driver.execute_script("arguments[0].click();", clickable_link)
            WebDriverWait(driver, 10).until(EC.staleness_of(navigation_bar))

    return title_link_dict

def generate_issue_dictionary():
    opts = Options()
    opts.add_argument("--headless")                # use the modern headless mode
    opts.add_argument("--no-sandbox")              # handy for CI or Docker
    opts.add_argument("--disable-dev-shm-usage")   # avoids /dev/shm issues in containers

    driver = webdriver.Chrome(options=opts)   # Selenium Manager grabs the right driver
    driver.get('https://digitalassets.archives.rpi.edu/do/235be3d2-f018-48af-a413-b50e16dd6dc7')

    title_link_dict = step_through_pages(driver)
    
    with open("title_link.csv", "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        # Write header
        writer.writerow(["title", "link"])
        # Write rows
        for title, link in title_link_dict.items():
            writer.writerow([title, link])

    driver.quit()

def download_page(driver, img_url, local_path, page_num):
    # Get cookies from Selenium
    selenium_cookies = driver.get_cookies()  # list of dicts
    cookies = {c['name']: c['value'] for c in selenium_cookies}

    # Set headers to mimic browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
    }

    # Download image
    response = requests.get(img_url, headers=headers, cookies=cookies, stream=True)
    file_name = local_path + f"/page{page_num}.jpg"
    with open(file_name, "wb") as f:
        for chunk in response.iter_content(1024):
            f.write(chunk)


def save_issue(title, link):

    opts = Options()
    opts.add_argument("--headless")                # use the modern headless mode
    opts.add_argument("--no-sandbox")              # handy for CI or Docker
    opts.add_argument("--disable-dev-shm-usage")   # avoids /dev/shm issues in containers

    driver = webdriver.Chrome(options=opts)   # Selenium Manager grabs the right driver
    driver.get(link + "#mode/1up")

    # Extract the total number of pages
    pages_text = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "BRcurrentpage"))
    )
    pages_string = pages_text.text.strip()
    num_pages = int(pages_string.split(" ")[-1])

    # Create directory to store this issue's images
    local_dir = "./" + title.replace(" ", "_")
    os.makedirs(local_dir, exist_ok=True)  # won’t raise an error if it already exists

    # Save first page
    page_container = driver.find_element(By.CSS_SELECTOR, f".BRpagecontainer.pagediv0")
    page_img = page_container.find_element(By.TAG_NAME, "img")
    img_url = page_img.get_attribute("src")
    download_page(driver, img_url, local_dir, 1)

    # Start loop for saving remaining pages
    for page in range(1, num_pages):

        # Get the appropriate page
        driver.get(link + f"#page/{page+1}/mode/1up")

        # Get the image url
        page_container = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, f".BRpagecontainer.pagediv{page}"))
        )
        page_img = page_container.find_element(By.TAG_NAME, "img")
        img_url = page_img.get_attribute("src")

        # Download page
        download_page(driver, img_url, local_dir, page+1)

    driver.quit()

def save_all_issues(csv_path):
    with open(csv_path, newline="") as csvfile:
        reader = list(csv.DictReader(csvfile))  # convert to list to get total length
        for row in tqdm(reader, desc="Downloading issues", unit="issue"):
            
            title = row["title"]
            link = row["link"]
            
            # Construct the directory name
            local_dir = "./" + title.replace(" ", "_")

            # Check if it exists
            if os.path.exists(local_dir):
                tqdm.write(f"{title} already downloaded, skipping...")
                continue
            else:
                save_issue(title, link)

def save_all_issues_parallel(csv_path, max_workers=2):
    with open(csv_path, newline="") as csvfile:
        reader = list(csv.DictReader(csvfile))

    # Filter issues that are not yet downloaded
    tasks = [(row["title"], row["link"]) for row in reader if not os.path.exists("./" + row["title"].replace(" ", "_"))]

    # Using ThreadPoolExecutor instead of ProcessPoolExecutor
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(save_issue, title, link): title for title, link in tasks}
        
        for future in tqdm(as_completed(futures), total=len(futures), desc="Downloading issues", unit="issue"):
            title = futures[future]
            try:
                future.result()  # raises exception if save_issue failed
            except Exception as e:
                # Log the error and capture traceback
                tqdm.write(f"Error downloading {title}: {e}")
                traceback_str = traceback.format_exc()
                tqdm.write(f"Traceback:\n{traceback_str}")

def main():
    
    #generate_issue_dictionary()
    csv_path = "./title_link.csv"
    save_all_issues_parallel(csv_path, max_workers=5)

if __name__ == "__main__":
    main()