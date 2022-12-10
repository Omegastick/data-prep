"""CLI utility that removes underscores from tags."""

import tqdm
import typer

from dataset import DatasetDirectory, Image

app = typer.Typer()


def process_image(image: Image) -> None:
    old_tags = image.tags
    image.tags = [tag.replace("_", " ") for tag in image.tags]

    if old_tags != image.tags:
        typer.echo(f"Removing underscores from tags in {image.path}")
        image.save_metadata()


@app.command()
def main(dataset_path: str):
    """Removes underscores from tags."""
    dataset = DatasetDirectory(dataset_path)
    for image in tqdm.tqdm(dataset):
        process_image(image)


if __name__ == "__main__":
    app()
