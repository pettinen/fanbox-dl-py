import json
import os
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Optional
from urllib.parse import unquote, urlsplit

import click
import requests


def download(url: str, dest_dir: Path, clobber: bool, session_id: str) -> None:
    fullpath = unquote(urlsplit(url).path)
    filename = PurePosixPath(fullpath).name

    req = get(url, session_id)
    file = Path(dest_dir, filename)
    if clobber or not file.exists():
        with open(file, "wb") as f:
            f.write(req.content)


def get(url: str, session_id: str) -> requests.Response:
    return requests.get(
        url,
        cookies={"FANBOXSESSID": session_id},
        headers={"Origin": "https://fanbox.cc"},
    )


def get_post(post_id: str, session_id: str) -> Any:
    url = f"https://api.fanbox.cc/post.info?postId={post_id}"

    req = get(url, session_id)
    req.raise_for_status()

    try:
        data = req.json()
    except ValueError:
        return None
    if "body" not in data:
        return None
    return data["body"]


def get_posts(creator: str, session_id: str) -> Any:
    limit = 300
    url = f"https://api.fanbox.cc/post.listCreator?creatorId={creator}&limit={limit}"

    req = get(url, session_id)
    req.raise_for_status()

    try:
        data = req.json()
    except ValueError:
        return None
    if "body" not in data or "items" not in data["body"]:
        return None
    if "nextUrl" in data["body"] and data["body"]["nextUrl"] is not None:
        print(
            f"Warning: Only the {limit} newest posts in the fanbox are downloaded.",
            file=sys.stderr,
        )
    return data["body"]["items"]


@click.command()
@click.option("-c", "--cookie-file", required=True)
@click.option("-o", "--output", default=".", show_default=True)
@click.option("--clobber/--no-clobber", default=False, show_default=True)
@click.argument("creator")
def main(cookie_file: str, output: str, clobber: bool, creator: str) -> None:
    with open(cookie_file) as f:
        session_id = f.read().strip()

    posts = get_posts(creator, session_id)
    if posts is None:
        print(f"Error: Couldn't fetch posts of {creator}", file=sys.stderr)
        sys.exit(1)

    posts_len = len(posts)
    for i, post in enumerate(posts):
        print(f"Fetching post {post['id']} ({i + 1}/{posts_len})", file=sys.stderr)
        data = get_post(post["id"], session_id)
        if data is None or "body" not in data or not data["body"]:
            print(f"Warning: Couldn't fetch post {post['id']}", file=sys.stderr)
            continue

        dest_dir = Path(output, post["id"])
        try:
            os.mkdir(dest_dir)
        except FileExistsError:
            pass

        metadata_path = dest_dir / "metadata.json"
        if clobber or not metadata_path.exists():
            with open(metadata_path, "w") as f:
                json.dump(data, f)

        urls = set()
        for image in data["body"].get("images", []):
            urls.add(image["originalUrl"])
        for image in data["body"].get("imageMap", {}).values():
            urls.add(image["originalUrl"])
        for file in data["body"].get("files", []):
            urls.add(file["url"])
        for file in data["body"].get("fileMap", {}).values():
            urls.add(file["url"])

        for url in urls:
            download(url, dest_dir, clobber, session_id)
