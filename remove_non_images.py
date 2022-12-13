"""CLI Utility that removes non-image files (with their metadata) from a directory."""

import os
from pathlib import Path

import tqdm
import typer

app = typer.Typer()


@app.command()
def remove_non_images(directory: Path = typer.Argument(..., exists=True, file_okay=False, dir_okay=True)) -> None:
    """Removes non-image files from a directory recursively, prompting the user before deleting."""
    files_to_delete: list[Path] = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = Path(root, file)
            if all(
                [
                    suffix not in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".json"]
                    for suffix in file_path.suffixes
                ]
            ):
                files_to_delete.append(file_path)

    typer.echo([str(file) for file in files_to_delete])
    delete = typer.confirm(f"Delete {len(files_to_delete)} files?")
    if not delete:
        return

    for file in tqdm.tqdm(files_to_delete):
        os.remove(file)
        os.remove(file.with_suffix(file.suffix + ".json"))


if __name__ == "__main__":
    app()
