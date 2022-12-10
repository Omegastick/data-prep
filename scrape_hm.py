"""
Script that scrapes the H&M website for images, saving them in a directory along with metadata
containing their gender, category, and caption.
"""

import json
import mimetypes
import os
import re
from dataclasses import dataclass
from typing import List, Tuple

import requests
import typer
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2) AppleWebKit/601.3.9 (KHTML, like Gecko) Version/9.0.2 Safari/601.3.9"
}

BASE_URL = "https://www2.hm.com/en_gb"
BASE_URL_QUERY = "?sort=stock&image-size=small&image=model"

CATEGORIES = [
    ("/ladies/shop-by-product/dresses.html", "Woman Dresses"),
    ("/ladies/shop-by-product/tops.html", "Woman Tops"),
    ("/ladies/shop-by-product/jackets-and-coats.html", "Woman Jackets & Coats"),
    ("/ladies/shop-by-product/cardigans-and-jumpers.html", "Woman Cardigans & Jumpers"),
    ("/ladies/shop-by-product/blazers-and-waistcoats.html", "Woman Blazers"),
    ("/ladies/shop-by-product/shoes.html", "Woman Shoes"),
    ("/ladies/shop-by-product/boots.html", "Woman Boots"),
    ("/ladies/shop-by-product/trousers.html", "Woman Trousers & Leggings"),
    ("/ladies/shop-by-product/jeans.html", "Woman Jeans"),
    ("/ladies/shop-by-product/shirts-and-blouses.html", "Woman Shirts & Blouses"),
    ("/ladies/shop-by-product/hoodies-sweatshirts.html", "Woman Sweatshirts & Hoodies"),
    ("/ladies/shop-by-product/skirts.html", "Woman Skirts"),
    ("/ladies/shop-by-product/loungewear.html", "Woman Loungewear"),
    ("/ladies/shop-by-product/nightwear.html", "Woman Nightwear"),
    ("/ladies/shop-by-product/bags.html", "Woman Bags"),
    ("/ladies/shop-by-product/accessories.html", "Woman Accessories"),
    ("/ladies/shop-by-product/basics.html", "Woman Basics"),
    ("/ladies/shop-by-product/premium-selection.html", "Woman Premium Selection"),
    ("/ladies/shop-by-product/maternity-wear.html", "Woman Maternity Wear"),
    ("/ladies/shop-by-product/hm-plus.html", "Woman Plus Sizes"),
    ("/ladies/shop-by-product/shorts.html", "Woman Shorts"),
    ("/ladies/shop-by-product/swimwear.html", "Woman Swimwear & Beachwear"),
    ("/ladies/shop-by-product/jumpsuits-playsuits.html", "Woman Jumpsuits & Playsuits"),
    ("/ladies/shop-by-product/sportswear.html", "Woman Sportswear"),
    ("/ladies/shop-by-product/lingerie.html", "Woman Lingerie"),
    ("/ladies/shop-by-product/socks-and-tights.html", "Woman Socks & Tights"),
    ("/men/shop-by-product/hoodies-sweatshirts.html", "Man Hoodies & Sweatshirts"),
    ("/men/shop-by-product/jackets-and-coats.html", "Man Jackets & Coats"),
    ("/men/shop-by-product/cardigans-and-jumpers.html", "Man Jumpers & Cardigans"),
    ("/men/shop-by-product/trousers.html", "Man Trousers"),
    ("/men/shop-by-product/shirts.html", "Man Shirts"),
    ("/men/shop-by-product/t-shirts-and-tanks.html", "Man T-shirts & Tops"),
    ("/men/shop-by-product/suits-blazers.html", "Man Suits & Blazers"),
    ("/men/shop-by-product/shoes.html", "Man Shoes"),
    ("/men/shop-by-product/jeans.html", "Man Jeans"),
    ("/men/shop-by-product/sportswear.html", "Man Sportswear"),
    ("/men/shop-by-product/underwear.html", "Man Underwear"),
    ("/men/shop-by-product/nightwear-loungewear.html", "Man Nightwear & Loungewear"),
    ("/men/shop-by-product/basics.html", "Man Basics"),
    ("/men/shop-by-product/accessories.html", "Man Accessories"),
    ("/men/shop-by-product/socks.html", "Man Socks"),
    ("/men/shop-by-product/premium-selection.html", "Man Premium Selection"),
    ("/men/shop-by-product/knitwear.html", "Man Knitwear"),
    ("/men/shop-by-product/shorts.html", "Man Shorts"),
    ("/men/shop-by-product/swimwear.html", "Man Swimwear"),
]

app = typer.Typer()


@dataclass
class Item:
    name: str
    image_url: str
    category: str


def get_url(category_url: str, page_size: int, page: int) -> str:
    url = f"{BASE_URL}{category_url}{BASE_URL_QUERY}"
    url_with_page_size = f"{url}&page-size={page_size}"
    url_with_offset = f"{url_with_page_size}&offset={page_size * page}"
    return url_with_offset


def write_item(item: Item, image_data: bytes, directory: str, extension: str) -> None:
    print(f"Writing {item.name} to {directory}")
    with open(f"{directory}/{item.name}{extension}", "wb") as f:
        f.write(image_data)

    with open(f"{directory}/{item.name}{extension}.json", "w") as f:
        json.dump({"category": item.category, "title": item.name, "source": "h&m"}, f)


def scrape_url(url: str, image_count: int, category: str) -> List[Item]:
    print(f"Fetching {image_count} images from {category} - {url}")
    response = requests.get(get_url(url, image_count, 0), headers=HEADERS)
    soup = BeautifulSoup(response.content, "lxml")

    items: List[Item] = []
    for scraped_item in soup.select(".hm-product-item"):
        name = scraped_item.select(".link")[0].text
        raw_image_url = scraped_item.select(".item-image")[0]["data-src"]
        if not isinstance(raw_image_url, str):
            raise ValueError(f"Image URL for {name} is not a string: {raw_image_url}")
        image_url = "https:" + raw_image_url

        # Replace res[s/m] with res[l]
        image_url = re.sub(r"res[s|m]", "resl", image_url)

        # Replace "product/style" with "product/main"
        image_url = re.sub(r"product/style", "product/main", image_url)

        name = name.replace("/", " ").strip()
        category = category.replace("/", " ").strip()
        items.append(Item(name, image_url, category))

    return items


def fetch_images(items: List[Item], data_dir: str) -> None:
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    for item in items:
        print(f"Fetching {item.name} - {item.image_url}")
        response = requests.get(item.image_url, headers=HEADERS)
        if response.status_code != 200:
            print(f"Failed to download image for {item.name} - {response.status_code}")
            continue

        content_type = response.headers["content-type"]
        extension = mimetypes.guess_extension(content_type)
        if extension is None:
            raise ValueError(f"Could not determine extension for {item.name}")

        write_item(item, response.content, data_dir, extension)


@app.command()
def scrape(
    output_dir: str = typer.Argument(..., help="Directory to save scraped images to"),
    count: int = typer.Argument(200, help="Number of images to scrape per category"),
):
    for category_url, category in CATEGORIES:
        print(f"Scraping {category} - {category_url}")
        items = scrape_url(category_url, count, category)
        fetch_images(items, output_dir + "/" + category)


if __name__ == "__main__":
    app()
