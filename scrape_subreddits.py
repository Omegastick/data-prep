import asyncio
import json
import mimetypes
import os
from dataclasses import dataclass

import aiohttp
import asyncpraw
import typer
from asyncpraw.exceptions import AsyncPRAWException
from asyncpraw.models import Submission
from asyncpraw.models import Subreddit as PRAWSubreddit
from asyncprawcore.exceptions import AsyncPrawcoreException

from dataset import DatasetDirectory


@dataclass
class Subreddit:
    name: str
    description: str


SUBREDDITS: list[Subreddit] = [
    Subreddit("itookapicture", "Photography"),
    Subreddit("portraits", "Portrait photography"),
    Subreddit("art", "Art"),
    Subreddit("malefashion", "Fashion"),
    Subreddit("techwear", "Techwear"),
    Subreddit("techwearclothing", "Techwear"),
    Subreddit("darkwearclothing", "Darkwear"),
    Subreddit("JustNiceFits", "Outfits"),
]


app = typer.Typer()


async def get_submission(
    submission: Submission,
    subreddit: PRAWSubreddit,
    description: str,
    dataset: DatasetDirectory,
    session: aiohttp.ClientSession,
) -> None:
    if any(image.path.name.startswith(f"{subreddit.display_name}{submission.id}") for image in dataset):
        typer.echo(f"Skipping '{submission.title}' because it already exists")
        return

    typer.echo(f"Fetching {submission.title}")
    try:
        await submission.load()
    except (AsyncPRAWException, AsyncPrawcoreException) as e:
        typer.echo(f"Error: {e} for {submission.url}")
        return

    urls = []
    if hasattr(submission, "media_metadata"):
        for image in submission.media_metadata.values():
            urls.append((image["s"]["u"], image["id"]))
    else:
        urls.append((submission.url, submission.id))

    for url in urls:
        try:
            response = await session.get(url[0], timeout=360)
        except asyncio.TimeoutError:
            typer.echo(f"Error: Timeout for {submission.url}")
            return
        except aiohttp.ClientError:
            typer.echo(f"Error: ClientError for {submission.url}")
            return

        if response.status != 200:
            typer.echo(f"Error: {response.status} for {submission.url}")
            return

        extension = mimetypes.guess_extension(response.headers["content-type"])
        if extension is None:
            typer.echo(f"Could not determine extension for {submission.url}")
            return

        file_name = f"{subreddit.display_name}{submission.id}_{url[1]}{extension}"

        metadata = {
            "title": submission.title.replace("ITAP", "photo"),
            "nsfw": submission.over_18,
            "source": "reddit",
            "subreddit": subreddit.display_name,
            "description": description,
            "url": submission.url,
        }

        try:
            dataset.create_image(await response.read(), file_name, metadata)
        except asyncio.TimeoutError:
            typer.echo(f"Error: Timeout for {submission.url}")
            return
        except aiohttp.ClientError:
            typer.echo(f"Error: ClientError for {submission.url}")
            return
        except OSError as e:
            typer.echo(f"Error saving {submission.url}: {e}")
            return

        typer.echo(f"Saved {file_name}")


async def scrape_subreddit(subreddit: Subreddit, reddit: asyncpraw.Reddit, dataset: DatasetDirectory):
    typer.echo(f"Scraping {subreddit.name}")

    praw_subreddit: PRAWSubreddit = await reddit.subreddit(subreddit.name)
    try:
        await praw_subreddit.load()
    except (AsyncPRAWException, AsyncPrawcoreException) as e:
        typer.echo(f"Error: {e} for {subreddit.name}")
        return

    submissions = praw_subreddit.top("all", limit=3000)
    tasks = []

    async with aiohttp.ClientSession() as session:
        async for submission in submissions:
            submission: Submission

            if submission.link_flair_text is not None and "meme" in submission.link_flair_text.lower():
                continue

            tasks.append(get_submission(submission, praw_subreddit, subreddit.description, dataset, session))

        await asyncio.gather(*tasks)


async def main(data_dir: str) -> None:
    os.makedirs(data_dir, exist_ok=True)
    dataset = DatasetDirectory(data_dir)

    with asyncpraw.Reddit(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        user_agent="get_subreddits.py",
    ) as reddit:
        for subreddit in SUBREDDITS:
            await scrape_subreddit(subreddit, reddit, dataset)
        await reddit.close()


@app.command()
def run(data_dir: str = typer.Argument(..., help="Path to the dataset directory")):
    asyncio.run(main(data_dir))


if __name__ == "__main__":
    app()
