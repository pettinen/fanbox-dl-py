import json
import os
import sys
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

import click
import requests


def download(url, dest_dir, clobber, session_id):
    fullpath = unquote(urlsplit(url).path)
    filename = PurePosixPath(fullpath).name
    try:
        os.mkdir(dest_dir)
    except FileExistsError:
        pass
    req = get(url, session_id)
    file = Path(dest_dir, filename)
    if clobber or not file.exists():
        with open(file, 'wb') as f:
            f.write(req.content)


def get(url, session_id):
    return requests.get(
        url,
        cookies={'FANBOXSESSID': session_id},
        headers={'Origin': 'https://fanbox.cc'}
    )


def get_post(post_id, session_id):
    url = f'https://api.fanbox.cc/post.info?postId={post_id}'

    req = get(url, session_id)
    req.raise_for_status()

    try:
        data = req.json()
    except ValueError:
        return None
    if 'body' not in data:
        return None
    return data['body']


def get_posts(creator, session_id):
    limit = 300
    url = f'https://api.fanbox.cc/post.listCreator?creatorId={creator}&limit={limit}'

    req = get(url, session_id)
    req.raise_for_status()

    try:
        data = req.json()
    except ValueError:
        return None
    if 'body' not in data or 'items' not in data['body']:
        return None
    if 'nextUrl' in data['body'] and data['body']['nextUrl'] is not None:
        print(f"Warning: Only the {limit} newest posts in the fanbox are downloaded.", file=sys.stderr)
    return data['body']['items']


@click.command()
@click.option('-c', '--cookie-file', required=True)
@click.option('-o', '--output', default='.', show_default=True)
@click.option('--clobber/--no-clobber', default=False, show_default=True)
@click.argument('creator')
def main(cookie_file, output, clobber, creator):
    with open(cookie_file) as f:
        session_id = f.read().strip()

    posts = get_posts(creator, session_id)
    if posts is None:
        print(f"Error: Couldn't fetch posts of {creator}", file=sys.stderr)
        sys.exit(1)

    posts_len = len(posts)
    for i, post in enumerate(posts):
        print(f"Fetching post {post['id']} ({i + 1}/{posts_len})", file=sys.stderr)
        data = get_post(post['id'], session_id)
        if data is None:
            print(f"Warning: Couldn't fetch post {post['id']}", file=sys.stderr)
            continue

        dest_dir = Path(output, post['id'])
        try:
            os.mkdir(dest_dir)
        except FileExistsError:
            pass

        metadata_path = dest_dir / 'metadata.json'
        if clobber or not metadata_path.exists():
            with open(metadata_path, 'w') as f:
                json.dump(data, f)

        if 'images' in data['body']:
            for image in data['body']['images']:
                download(image['originalUrl'], dest_dir, clobber, session_id)
        if 'files' in data['body']:
            for file in data['body']['files']:
                download(file['url'], dest_dir, clobber, session_id)
