#!/usr/bin/env python3

import json
import logging
import os
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

import click
import requests


def download(url, dest_dir, session_id):
    fullpath = unquote(urlsplit(url).path)
    filename = PurePosixPath(fullpath).name
    try:
        os.mkdir(dest_dir)
    except FileExistsError:
        pass
    req = get(url, session_id)
    file = Path(dest_dir, filename)
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
        return
    if 'body' not in data:
        return
    return data['body']


def get_posts(creator, session_id):
    limit = 300
    url = f'https://api.fanbox.cc/post.listCreator?creatorId={creator}&limit={limit}'

    req = get(url, session_id)
    req.raise_for_status()

    try:
        data = req.json()
    except ValueError:
        return
    if 'body' not in data or 'items' not in data['body']:
        return
    if 'nextUrl' in data['body'] and data['body']['nextUrl'] is not None:
        logging.warning(f"Only the first {limit} posts in the fanbox are downloaded.")
    return data['body']['items']


@click.command()
@click.option('-c', '--cookie-file', required=True)
@click.option('-o', '--output', default='.')
@click.argument('creator')
def main(cookie_file, output, creator):
    with open(cookie_file) as f:
        session_id = f.read().strip()

    posts = get_posts(creator, session_id)
    for post in posts:
        data = get_post(post['id'], session_id)
        dest_dir = Path(output, post['id'])
        try:
            os.mkdir(dest_dir)
        except FileExistsError:
            pass
        with open(dest_dir / 'metadata.json', 'w') as f:
            json.dump(data, f)

        if 'images' in data['body']:
            for image in data['body']['images']:
                download(image['originalUrl'], dest_dir, session_id)
        if 'files' in data['body']:
            for file in data['body']['files']:
                download(file['url'], dest_dir, session_id)
