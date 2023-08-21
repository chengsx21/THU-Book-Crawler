import json
import os
import re
from typing import List, Dict, Tuple
import requests
from bs4 import BeautifulSoup as BS
from PIL import Image

def get_auth() -> Tuple[str, Dict[str, str], str]:
    config_file_path="./config.json"
    with open(config_file_path, "r") as f:
        data = json.load(f)
    url = data["URL"]
    user_agent = data["User-Agent"]
    cookie = data["Cookie"]
    pdf_file_name = data["Title"] + ".pdf"
    headers = {
        "User-Agent": user_agent,
        "Cookie": cookie
    }
    return url, headers, pdf_file_name

def get_response(url: str, headers: Dict[str, str]) -> str:
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            error_info = "请您登录个人INFO账户查看教参全文"
            if error_info in response.text:
                exit("[Failure] Check your configeration file, please")
            print("[Success] Start downloading...")
            return response.text
    except Exception:
        exit("[Failure] Check your configeration file, please")

def get_book_urls(response: str) -> Tuple[List[str], str]:
    soup = BS(response, "lxml")
    links = soup.find_all('a', href=lambda href: href and href.startswith('/book'))
    book_urls = []
    for link in links:
        url = link.get('href').replace("index.html", "")
        book_urls.append("http://reserves.lib.tsinghua.edu.cn" + url)
    folder_path = os.path.join("example", re.findall(r'//(.*?)/', book_urls[0])[1])
    return book_urls, folder_path

def get_token_and_page_count(book_urls: List[str]) -> Tuple[List[str], List[int]]:
    tokens = []
    pages = []
    for book_url in book_urls:
        config_url = book_url + js_path
        response = requests.get(config_url)
        token = re.findall(r'bookConfig.CreatedTime ="(.*?)"', response.text)[0]
        tokens.append(token)
        page = re.findall(r'bookConfig.totalPageCount=(.*?);', response.text)[0]
        pages.append(int(page))
        print("[INFO] Token %s with %s pages" % (token, page))
    return tokens, pages

def download_pictures() -> None:
    if not os.path.exists(folder_path):
        os.mkdir(folder_path)

    for index, book_url in enumerate(book_urls):    
        token = tokens[index]
        page_count = pages[index]
        for page in range(1, page_count + 1, 1):
            image_url = f"{book_url}/files/mobile/{page}.jpg?{token}"
            response = requests.get(image_url)
        
            if response.status_code == 200:
                image_path = os.path.join(folder_path, f"{index+1}-{page}.jpg")
                with open(image_path, "wb") as f:
                    f.write(response.content)
                print(f"[INFO] Successfully downloaded page {index+1}-{page}")
            else:
                print(f"[INFO] Failed to download page {index+1}-{page}")

def custom_sort(file_name: str) -> Tuple[int, int]:
    parts = file_name.split("/")[2].split(".")[0]
    chapter_part = parts.split("-")[0]
    page_part = parts.split("-")[1]
    return int(chapter_part), int(page_part)

def combine_imgs_pdf(pdf_file_name: str) -> None:
    pdf_file_path = os.path.join(folder_path, pdf_file_name)
    jpg_files = os.listdir(folder_path)
    files = []
    sources = []
    for file in jpg_files:
        files.append(os.path.join(folder_path, file))
    files.sort(key=custom_sort)

    output = Image.open(files[0])
    files.pop(0)
    for file in files:
        print(f"[INFO] Combining page {file}")
        png_file = Image.open(file)
        if png_file.mode == "RGB":
            png_file = png_file.convert("RGB")
        sources.append(png_file)
    output.save(pdf_file_path, "pdf", save_all=True, append_images=sources)
    print(f"[INFO] Successfully saved to {pdf_file_path}")

if __name__ == "__main__":
    js_path = "mobile/javascript/config.js"
    url, headers, pdf_file_name = get_auth()
    response = get_response(url, headers)
    book_urls, folder_path = get_book_urls(response)
    tokens, pages = get_token_and_page_count(book_urls)
    download_pictures()
    combine_imgs_pdf(pdf_file_name)
    