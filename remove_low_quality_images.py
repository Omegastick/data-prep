"""CLI Utility that filters images below a certain aesthetic score."""

import os

import tqdm
import typer

from dataset import DatasetDirectory, Image

app = typer.Typer()


@app.command()
def main(
    data_dir: str = typer.Argument(..., help="Directory to process"),
    min_score: float = typer.Argument(..., help="Minimum aesthetic score to filter by"),
    remove_invalid: bool = typer.Option(False, help="Remove images missing an aesthetic score (such as broken images)"),
) -> None:
    dataset = DatasetDirectory(data_dir)

    images_to_delete: list[Image] = []

    for image in tqdm.tqdm(dataset):
        if "aesthetic_score" not in image.metadata:
            if remove_invalid:
                images_to_delete.append(image)
                continue
            typer.echo(f"No aesthetic score for {image.path}, skipping...")
            continue
        if image.metadata["aesthetic_score"] < min_score:
            images_to_delete.append(image)

    percentage = (len(images_to_delete) / len(dataset)) * 100.0
    prompt = (
        f"Filtering {data_dir} by aesthetic score {min_score} would delete "
        f"{len(images_to_delete)}/{len(dataset)} ({percentage:.2f}%), continue?"
    )
    delete = typer.confirm(prompt)
    if not delete:
        return

    for image in tqdm.tqdm(images_to_delete):
        os.remove(image.path)
        os.remove(image.metadata_path)

    typer.echo(f"Deleted {len(images_to_delete)} images")


if __name__ == "__main__":
    app()
