"""CLI for adding basic tags from filenames and metadata to a dataset."""

import re
from typing import List

import tqdm
import typer

from dataset import DatasetDirectory, Image

app = typer.Typer()


def tag_nsfw(image: Image) -> None:
    """Tag an image as nsfw if the metadata says it is."""
    nsfw_fields = ["nsfw", "is_mature", "is_adult", "over_18"]
    if any(image.metadata.get(field, False) for field in nsfw_fields):
        image.add_tag("nsfw")


def tag_filename(image: Image) -> None:
    """Tag an image based on its filename.

    Does some basic cleaning of the title to remove underscores, dashes, and random character strings."""
    filename = image.path.name

    filename = filename.replace("_", " ")
    filename = filename.replace("-", " ")

    filename = filename[: filename.index(".")]

    if image.metadata.get("category", None) == "imgur":
        # imgur_6eYvod6_Title.jpg
        filename = filename[14:]

    if "subreddit" in image.metadata or any(
        ["subreddit" in x for x in image.metadata.get("crosspost_parent_list", [])]
    ):
        # d2lrcb Oh man.webp
        filename = filename[filename.index(" ") + 1 :]

    # Remove random character strings
    words: List[str] = []
    for word in filename.split():
        if len(word) > 20:
            continue
        if len(word) > 5 and word.isnumeric():
            continue
        if len(word) > 7 and not any(c in word for c in "aeiou"):
            continue
        words.append(word)
    filename = " ".join(words)

    if filename:
        image.add_tag(filename)


def tag_subfolders(image: Image) -> None:
    """Tag an image with its subfolders, ignoring "reg" subfolder for regularization images."""
    for subfolder in image.subfolders:
        if subfolder != "reg":
            image.add_tag(subfolder.replace("_", " "))


def tag_title(image: Image) -> None:
    """Tag an image with its title if it has one."""
    title = image.metadata.get("title", None)
    if title:
        image.add_tag(title)


def tag_cateories(image: Image) -> None:
    """Tag an image with its categories."""
    categories: List[str] | str = image.metadata.get("categories", None) or image.metadata.get("category", None)
    if not isinstance(categories, list):
        categories = [categories]
    if categories:
        for category in categories:
            image.add_tag(category)


def tag_source(image: Image) -> None:
    """Tag an image with its source."""
    source = image.metadata.get("source", None)
    if source:
        image.add_tag(source)


def tag_description(image: Image) -> None:
    """Tag an image with its description."""
    description = image.metadata.get("description", None)
    if description:
        image.add_tag(description)


def split_camel_case(input: str) -> list[str]:
    matches = re.finditer(".+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)", input)
    return [m.group(0) for m in matches]


def tag_subreddit(image: Image) -> None:
    """Tag an image with its subreddit."""
    subreddit = image.metadata.get("subreddit", None)
    if not subreddit:
        return

    subreddit = " ".join(split_camel_case(subreddit))
    subreddit = subreddit.replace("_", " ").replace("-", " ")
    image.add_tag(subreddit)


@app.command()
def tag(
    data_dir: str = typer.Argument(..., help="Directory containing images to process"),
    nsfw: bool = typer.Option(False, help="Tag images as nsfw if the metadata says it is"),
    title: bool = typer.Option(False, help="Tag images with their title if it has one"),
    filename: bool = typer.Option(False, help="Tag images with their filename"),
    subfolders: bool = typer.Option(False, help="Tag images with their subfolders"),
    categories: bool = typer.Option(False, help="Tag images with their categories"),
    source: bool = typer.Option(False, help="Tag images with their source"),
    description: bool = typer.Option(False, help="Tag images with their description"),
    subreddit: bool = typer.Option(False, help="Tag images with their subreddit"),
    preview: bool = typer.Option(False, "--preview", "-p", help="Print the tags instead of saving them"),
) -> None:
    """Add basic tags to a dataset."""
    dataset = DatasetDirectory(data_dir)

    for image in tqdm.tqdm(dataset.images):
        if nsfw:
            tag_nsfw(image)
        if filename:
            tag_filename(image)
        if subfolders:
            tag_subfolders(image)
        if title:
            tag_title(image)
        if categories:
            tag_cateories(image)
        if source:
            tag_source(image)
        if description:
            tag_description(image)
        if subreddit:
            tag_subreddit(image)

        if preview:
            typer.echo(f"Image: {image.path} - {image.tags}")
        else:
            image.save_metadata()


if __name__ == "__main__":
    app()
