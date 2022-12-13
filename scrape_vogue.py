import json
import os
from dataclasses import dataclass

import aiohttp
import typer

URL = "https://vogue-street-style-prod01.k8s.us-east-1--production.containers.aws.conde.io/results"
import asyncio


@dataclass
class Image:
    name: str
    credit: str
    url: str
    description: str
    tags: list[str]


def process_tags(tags: list[str]) -> list[str]:
    split_tags = [tag.split("/") for tag in tags]
    only_last = [tag[-1] for tag in split_tags if len(tag) > 1]
    dedashed = [tag.replace("-", " ") for tag in only_last]
    return dedashed


async def get_image(image: Image, output_dir: str, session: aiohttp.ClientSession) -> None:
    async with session.get(image.url) as response:
        if response.status != 200:
            typer.echo(f"Error downloading {image.url} - {response.status}")

        file_path = os.path.join(output_dir, image.name.replace(" ", "_"))
        try:
            with open(file_path, "wb") as f:
                f.write(await response.read())
        except OSError:
            typer.echo(f"Error saving {image.url} to {file_path}")
            return

        metadata_file_name = file_path + ".json"
        metadata = {
            "source": "vogue",
            "credit": image.credit.replace("Photographed by", " ").strip(),
            "description": image.description.replace("Image may contain: ", "").strip(),
            "tags": process_tags(image.tags),
        }
        try:
            with open(metadata_file_name, "w") as f:
                json.dump(metadata, f)
        except OSError:
            typer.echo(f"Error saving metadata for {image.url} to {metadata_file_name}")
            return

        typer.echo(f"Downloaded {image.url} to {file_path}")


async def get_page(page: int, size: int, session: aiohttp.ClientSession) -> list[Image]:
    body = {"filters": ["fashion-tags/street-style"], "page": page, "size": size}
    async with session.post(URL, json=body) as response:
        if response.status != 200:
            typer.echo(f"Error getting page {page} - {response.status}")
            return []

        data = await response.json()
        return [
            Image(
                name=image["caption"],
                credit=image["photo_credit"],
                url=image["imageUrlMaster"],
                description=image["altText"],
                tags=image["tags"],
            )
            for image in data
        ]


app = typer.Typer()


async def main(output_dir: str):
    async with aiohttp.ClientSession() as session:
        page = 1
        images = await get_page(page, 100, session)
        while images:
            await asyncio.gather(*[get_image(image, output_dir, session) for image in images])
            page += 1
            images = await get_page(page, 100, session)


@app.command()
def scrape(output_dir: str = typer.Argument(..., help="Directory to save images to")) -> None:
    typer.echo(f"Saving images to {output_dir}")
    os.makedirs(output_dir, exist_ok=True)

    asyncio.run(main(output_dir))


if __name__ == "__main__":
    app()
