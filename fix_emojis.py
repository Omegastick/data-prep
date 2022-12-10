"""Python script to replace all emojis in filenames with their human readable text"""

import os
import unicodedata

import typer

app = typer.Typer()


def replace_emoji(filename: str) -> str:
    """Replaces all emojis in a filename with their human readable text"""
    new_filename = filename
    for char in filename:
        if unicodedata.category(char).startswith("So"):
            new_filename = new_filename.replace(char, f":{unicodedata.name(char).lower()}:")
    return new_filename


@app.command()
def main(
    directory: str = typer.Argument(..., help="Directory to replace emojis in"),
    preview: bool = typer.Option(False, "--preview", "-p", help="Preview the changes that will be made"),
):
    for root, _, files in os.walk(directory):
        for file in files:
            new_filename = replace_emoji(file)
            if new_filename == file:
                continue
            typer.echo(f"{os.path.join(root, file)} -> {os.path.join(root, new_filename)}")
            if not preview:
                os.rename(os.path.join(root, file), os.path.join(root, new_filename))


if __name__ == "__main__":
    app()
