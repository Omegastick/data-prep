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
    credit: str | None
    url: str
    description: str | None
    tags: list[str]


def process_tags(tags: list[str]) -> list[str]:
    split_tags = [tag.split("/") for tag in tags]
    only_last = [tag[-1] for tag in split_tags if len(tag) > 1]
    dedashed = [tag.replace("-", " ") for tag in only_last]
    return dedashed


async def get_image(image: Image, output_dir: str, session: aiohttp.ClientSession) -> None:
    file_path = os.path.join(output_dir, image.name.replace(" ", "_"))
    if os.path.exists(file_path):
        typer.echo(f"Skipping {image.url} - already exists")
        return

    async with session.get(image.url) as response:
        if response.status != 200:
            typer.echo(f"Error downloading {image.url} - {response.status}")

        try:
            with open(file_path, "wb") as f:
                f.write(await response.read())
        except OSError:
            typer.echo(f"Error saving {image.url} to {file_path}")
            return

        metadata_file_name = file_path + ".json"
        metadata = {
            "source": "vogue",
            "tags": process_tags(image.tags),
        }
        if image.credit:
            metadata["credit"] = (image.credit.replace("Photographed by", " ").strip(),)
        if image.description:
            metadata["description"] = image.description.replace("Image may contain: ", "").strip()

        try:
            with open(metadata_file_name, "w") as f:
                json.dump(metadata, f)
        except OSError:
            typer.echo(f"Error saving metadata for {image.url} to {metadata_file_name}")
            return

        typer.echo(f"Downloaded {image.url} to {file_path}")


async def get_page(page: int, size: int, filters: list[str], session: aiohttp.ClientSession) -> list[Image]:
    body = {"filters": filters, "page": page, "size": size}
    async with session.post(URL, json=body) as response:
        if response.status != 200:
            typer.echo(f"Error getting page {page} - {response.status}")
            return []

        data = await response.json()
        return [
            Image(
                name=image["imageUrlMaster"].split("/")[-1],
                credit=image.get("photo_credit"),
                url=image["imageUrlMaster"],
                description=image.get("altText"),
                tags=image["tags"] if "tags" in image else [],
            )
            for image in data
        ]


app = typer.Typer()


async def main(output_dir: str, filters: list[str]):
    async with aiohttp.ClientSession() as session:
        page = 1
        images = await get_page(page, 100, filters, session)
        while images:
            await asyncio.gather(*[get_image(image, output_dir, session) for image in images])
            page += 1
            images = await get_page(page, 100, filters, session)


@app.command()
def scrape(
    output_dir: str = typer.Argument(..., help="Directory to save images to"),
    filters: list[str] = typer.Argument(None, help="Filters to apply to the search"),
) -> None:
    typer.echo(f"Saving images to {output_dir}")
    os.makedirs(output_dir, exist_ok=True)

    asyncio.run(main(output_dir, filters))


if __name__ == "__main__":
    app()
