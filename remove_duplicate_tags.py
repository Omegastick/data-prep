"""CLI utility that looks at the tags for each image, and if one is a subset of another, removes it."""

import typer

from dataset import DatasetDirectory, Image

app = typer.Typer()

def process_image(image: Image) -> None:
    """Removes tags from an image that are subsets of other tags."""
    tags = image.tags
    removed = False
    for tag in tags:
        if any(tag.lower() in other.lower() for other in tags if other != tag):
            typer.echo(f"Removing tag '{tag}' from {image.path}")
            image.remove_tag(tag)
            removed = True
    
    if removed:
        image.save_metadata()

@app.command()
def main(dataset_path: str):
    """Removes tags from images that are subsets of other tags."""
    dataset = DatasetDirectory(dataset_path)
    for image in dataset.images:
        process_image(image)

if __name__ == "__main__":
    app()

        