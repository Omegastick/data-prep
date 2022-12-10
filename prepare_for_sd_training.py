"""Script that prepares a dataset for training.

Given a directory, it recursively searches for images in that directory and copies them into an output directory.
It also converts the "tags" field of the metadata to a .txt file with the same name (comma-separated).
"""

import os
import shutil
from pathlib import Path

import tqdm
import typer

from dataset import DatasetDirectory

app = typer.Typer()


@app.command()
def prepare_dataset(
    input_dir: str = typer.Argument(..., help="Directory containing images to process"),
    output_dir: str = typer.Argument(..., help="Directory to save processed images"),
    aesthetic_score: float = typer.Option(0.0, help="Aesthetic score to filter images by"),
):
    dataset = DatasetDirectory(input_dir)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for image in tqdm.tqdm(dataset):
        if aesthetic_score > 0 and (found_score := image.metadata.get("aesthetic_score", 0.0)) < aesthetic_score:
            if found_score == 0.0:
                typer.echo(f"Warning: no aesthetic score for {image.path}")
            continue

        output_path: Path = Path(output_dir) / image.path.name
        with open(output_path.with_suffix(".txt"), "w") as f:
            f.write(", ".join(image.tags))
        shutil.copy(image.path, output_path)


if __name__ == "__main__":
    app()
