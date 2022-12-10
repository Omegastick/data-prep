"""Script to find (and optionally remove) duplicate images (and associated metadata files) recursively through a dataset."""

import hashlib
import os

import typer

app = typer.Typer()


def get_hash(file_path: str) -> str:
    """Get the hash of a file."""
    with open(file_path, "rb") as f:
        file_hash = hashlib.sha256()
        while chunk := f.read(8192):
            file_hash.update(chunk)
    return file_hash.hexdigest()


def find_duplicates(dir_path: str) -> dict:
    """Find duplicate images in a directory."""
    hashes = {}
    for root, _, files in os.walk(dir_path):
        for file in files:
            file_path = os.path.join(root, file)
            file_hash = get_hash(file_path)
            if file_hash in hashes:
                hashes[file_hash].append(file_path)
            else:
                hashes[file_hash] = [file_path]
    return {k: v for k, v in hashes.items() if len(v) > 1}


def remove_duplicates(duplicates: dict) -> None:
    """Remove duplicate images."""
    for duplicate in duplicates.values():
        for file_path in duplicate[1:]:
            os.remove(file_path)
            if os.path.exists(file_path + ".json"):
                os.remove(file_path + ".json")


@app.command()
def main(
    dir_path: str = typer.Argument(..., help="Path to the directory to find duplicates in"),
    remove: bool = typer.Option(False, "--remove", "-r", help="Remove duplicate images"),
):
    """Find (and optionally remove) duplicate images (and associated metadata files) recursively through a dataset."""
    duplicates = find_duplicates(dir_path)
    if duplicates:
        typer.echo(f"Found {len(duplicates)} duplicate images:")
        for duplicate in duplicates.values():
            typer.echo(duplicate)
        if remove:
            remove_duplicates(duplicates)
            typer.echo("Removed duplicates")
    else:
        typer.echo("No duplicates found")


if __name__ == "__main__":
    app()
