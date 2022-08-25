import base64
import json
import os
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import requests
from dotenv import load_dotenv

from util import encode_url

load_dotenv(override=True)
base_url = "https://api.spotify.com/v1"
access_token = None

app = FastAPI(debug=True)

origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def req(method, url, headers=None, body=None):
    """Written like this if I want to switch to asyncio"""

    request = {"url": url, "data": body, "headers": headers}
    method_upper = method.upper()

    if method_upper.upper() == "POST":
        response = requests.post(**request)
    if method_upper.upper() == "GET":
        response = requests.get(**request)

    if not response.ok:
        raise RuntimeError(f"Error in post request: {request}\nGot response: {response.text}")
    return response.json()

def get_access_token():
    auth = base64.b64encode(f"{os.getenv('CLIENT_ID')}:{os.getenv('CLIENT_SECRET')}".encode("utf-8"))
    headers = {
        "Authorization": f"Basic {str(auth, 'utf-8')}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    body = "grant_type=client_credentials"

    response = req(
        "POST", f"https://accounts.spotify.com/api/token", headers=headers, body=body
    )
    response["expires_at"] = response["expires_in"] + time.time()
    return response


def process_tracks_from_search(response):
    tracks = response["tracks"]["items"]
    processed = []
    for track in tracks:
        processed_track = {
            "title": track["name"],
            "artist": track["artists"][0]["name"],
            "album": track["album"]["name"],
            "spotifyId": track["id"]
        }
        processed.append(processed_track)
    return processed
    


@app.middleware("http")
async def check_access_token(request: Request, call_next):
    # TODO: avoid global
    global access_token

    if not access_token or access_token["expires_at"] <= time.time():
        try:
            access_token = get_access_token()
        except RuntimeError as e:
            access_token = None
            raise e
    response = await call_next(request)
    return response


@app.get("/spotify")
async def search(query: str):
    # TODO: avoid global
    global access_token

    if not query:
        return []

    url = base_url + f"/search?type=track&q={encode_url(query)}&limit=10"
    headers = {
        "Authorization": f"Bearer {access_token['access_token']}",
        "Content-Type": "application/json",
    }
    response = req("GET", url, headers)
    processed = process_tracks_from_search(response)
    return processed

