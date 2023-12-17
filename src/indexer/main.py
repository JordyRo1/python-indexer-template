"""Apibara indexer entrypoint."""

import asyncio
from functools import wraps
import os
from dotenv import load_dotenv
import click

from indexer.indexer import run_indexer
load_dotenv()

DNA_TOKEN = os.environ.get("DNA_TOKEN")
MONGODB_URL = os.environ.get("MONGODB_URL")

def async_command(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


@click.group()
def cli():
    pass


@cli.command()
@click.option("--server-url", default=None, help="Apibara stream url.")
@click.option("--mongo-url", default=None, help="MongoDB url.")
@click.option("--restart", is_flag=True, help="Restart indexing from the beginning.")
@async_command
async def start(server_url, mongo_url, restart):
    """Start the Apibara indexer."""
    if server_url is None:
        server_url = os.getenv("SERVER_URL")
    if mongo_url is None:
        mongo_url = MONGODB_URL
        # mongo_url = "mongodb://apibara:apibara@localhost:27017"

    print("Starting Apibara indexer...")
    print(f"   Server url: {server_url}")
    await run_indexer(
        restart=restart,
        server_url=server_url,
        mongo_url=mongo_url,
        dna_token=DNA_TOKEN,
    )
