"""
CLI that resizes all images in a directory (recursively) so that the maximum side length is set
according to the --max_side_length flag and saves the output as the specified file type.

Also moves any associated metadata files, and adds resolution tags from before resizing.
"""

import json
import os
import pathlib

import typer
from PIL import Image

app = typer.Typer()


def resize_image(image: Image.Image, max_side_length: int) -> Image.Image:
    """
    Resize an image so that the maximum side length is set to the specified value.
    """
    width, height = image.size
    if width > height:
        new_width = max_side_length
        new_height = int(max_side_length * height / width)
    else:
        new_width = int(max_side_length * width / height)
        new_height = max_side_length
    return image.resize((new_width, new_height)).convert("RGB")


def add_resolution_tags(image: Image.Image, metadata: dict, low_resolution: int, high_resolution: int) -> dict:
    """
    Add resolution tags to the metadata of an image.
    """
    width, height = image.size
    max_side_length = max(width, height)

    if "tags" not in metadata:
        metadata["tags"] = []

    if max_side_length <= low_resolution:
        metadata["tags"].append("lowres")
    elif max_side_length >= high_resolution:
        metadata["tags"].append("highres")

    return metadata


def load_metadata(image_path: str) -> dict:
    with open(f"{image_path}.json") as json_file:
        return json.load(json_file)


@app.command()
def process_dataset(
    input_dir: str = typer.Argument(..., help="Directory containing images to resize"),
    output_dir: str = typer.Argument(..., help="Directory to save resized images"),
    max_side_length: int = typer.Option(768, help="Maximum side length of resized images"),
    file_type: str = typer.Option("webp", help="File type to save resized images as"),
    low_resolution: int = typer.Option(768, help="Maximum side length of low resolution images"),
    high_resolution: int = typer.Option(1440, help="Maximum side length of high resolution images"),
):
    """
    Resize all images in a directory (recursively) so that the maximum side length is set
    according to the --max_side_length flag and saves the output as the specified file type.
    """
    for root, _, files in os.walk(input_dir):
        for file in files:
            if not file.endswith(("jpg", "jpeg", "png", "webp")):
                continue
            image = Image.open(os.path.join(root, file))

            metadata = load_metadata(os.path.join(root, file))
            metadata = add_resolution_tags(image, metadata, low_resolution, high_resolution)

            image = resize_image(image, max_side_length)

            output_path = os.path.join(output_dir, os.path.relpath(root, input_dir))
            pathlib.Path(output_path).mkdir(parents=True, exist_ok=True)
            file_name = os.path.splitext(file)[0]
            image.save(os.path.join(output_path, f"{file_name}.{file_type}"))

            with open(os.path.join(output_path, f"{file_name}.{file_type}.json"), "w") as json_file:
                json.dump(metadata, json_file)

            print(f"Resized {file} and saved to {output_path}")


if __name__ == "__main__":
    app()
