from dotenv import load_dotenv
import os
import base64
from requests import post, get
import json

load_dotenv()

client_id = os.getenv("SPOTIFY_ID")
client_secret = os.getenv("SPOTIFY_SECRET")

# get the Api token
def get_token():
    auth_string = client_id + ":" + client_secret
    auth_byte = auth_string.encode("utf-8")
    auth_base64 = str(base64.b64encode(auth_byte), "utf-8")

    url = "https://accounts.spotify.com/api/token"

    headers = {
        "Authorization": "Basic " + auth_base64,
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {"grant_type": "client_credentials"}
    result = post(url, headers=headers, data=data)
    json_result = json.loads(result.content)
    token = json_result["access_token"]
    return token


token = get_token()

# get access to modification for spotify
def get_auth_header(token):
    return {"Authorization": "Bearer " + token}


# search for artist
async def search_for_artist(artist_name):
    url = "https://api.spotify.com/v1/search"
    headers = get_auth_header(token)

    query = f"?q={artist_name}&type=artist&limit=1"

    query_url = url + query
    result = get(query_url, headers=headers)
    json_result = json.loads(result.content)["artists"]
    return json_result

#search the top tracks by artistID
async def search_song_by_artistID(artist_id):
    url = f"https://api.spotify.com/v1/artists/{artist_id}/top-tracks?country=US"
    headers = get_auth_header(token)
    result = get(url, headers=headers)
    json_result = json.loads(result.content)["tracks"]

    return json_result

# search for album
async def search_for_album(album_name):
    url = "https://api.spotify.com/v1/search"
    headers = get_auth_header(token)

    query = f"?q={album_name}&type=album&limit=1"

    query_url = url + query
    result = get(query_url, headers=headers)
    json_result = json.loads(result.content)["albums"]
    return json_result

#result the first album with ID
async def search_by_albumID(album_id):
    url = f"https://api.spotify.com/v1/albums/{album_id}/tracks"
    headers = get_auth_header(token)
    result = get(url, headers=headers)
    json_result = json.loads(result.content)

    return json_result

# search for playlist
async def search_for_playlist(playlist_name):
    url = "https://api.spotify.com/v1/search"
    headers = get_auth_header(token)

    query = f"?q={playlist_name}&type=playlist&limit=1"
    query_url = url + query
    result = get(query_url, headers=headers)
    json_result = json.loads(result.content)["playlists"]
    return json_result

# result playlist by playlist ID
async def search_by_playlistID(playlist_id):
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    headers = get_auth_header(token)
    result = get(url, headers=headers)
    json_result = json.loads(result.content)

    return json_result

# search for song
async def search_song(song):
    url = "https://api.spotify.com/v1/search?"
    headers = get_auth_header(token)

    query = f"q={song}&type=track&limit=1"
    query_url = url + query
    result = get(query_url, headers=headers)
    json_result = json.loads(result.content)["tracks"]
    print(json_result)
    return json_result

# use URL to open the spotify with tracks, playlists, albums, and artists
def search_URL(url):
    headers = get_auth_header(token)
    spotify_list = url[8:].split("/")
    if "album" in spotify_list:
        post_url = "https://api.spotify.com/v1/albums/"
        query = f"{spotify_list[2][:22]}"
        query_url = post_url + query
        result = get(query_url, headers=headers)
        json_result = json.loads(result.content)
    elif "playlist" in spotify_list:
        post_url = "https://api.spotify.com/v1/playlists/"
        query = f"{spotify_list[2][:22]}"
        query_url = post_url + query
        result = get(query_url, headers=headers)
        json_result = json.loads(result.content)
    elif "artist" in spotify_list:
        post_url = "https://api.spotify.com/v1/artists/"
        query = f"{spotify_list[2][:22]}"
        query_url = post_url + query + "/top-tracks"
        result = get(query_url, headers=headers)
        json_result = json.loads(result.content)
    elif "track" in spotify_list:
        post_url = "https://api.spotify.com/v1/tracks/"
        query = f"{spotify_list[2][:22]}"
        query_url = post_url + query
        result = get(query_url, headers=headers)
        json_result = json.loads(result.content)
    else:
        return
    return json_result

# use api uri to get next page info
def search_by_api(api_link):
    headers = get_auth_header(token)
    result = get(api_link, headers=headers)
    json_result = json.loads(result.content)
    return json_result

# get the artists name for each song in the playlist
async def song_artists_in_playlist(song):
    if len(song["track"]["artists"]) == 0:
        return None
    if len(song["track"]["artists"]) == 1:
        return song["track"]["artists"][0]["name"]
    artists = ""
    for idx, artist in enumerate(song["track"]["artists"]):
        artists += f"{artist['name']}, "

    return str(artists[:-2])

# get list of next page's song in the playlist
async def list_of_Song_by_next_page_in_playlist(api_link):
    data = search_by_api(api_link)

    tracks = []
    for idx, song in enumerate(data["items"]):
        songname = song["track"]["name"]

        track = f"{songname} by {await song_artists_in_playlist(song)}"
        tracks.append(track)

    if data["next"]:
        tracks += await list_of_Song_by_next_page_in_playlist(data["next"])

    return tracks

#get the artists name for each song in the album
async def song_artists_in_album(song):
    if len(song["artists"]) == 0:
        return None
    if len(song["artists"]) == 1:
        return song["artists"][0]["name"]
    artists = ""
    for idx, artist in enumerate(song["artists"]):
        artists += f"{artist['name']}, "

    return str(artists[:-2])

# get list of next page's song in the album
async def list_of_Song_by_next_page_in_album(api_link):
    data = search_by_api(api_link)

    tracks = []
    for idx, song in enumerate(data["items"]):
        songname = song["name"]

        track = f"{songname} by {await song_artists_in_album(song)}"
        tracks.append(track)

    if data["next"]:
        tracks += await list_of_Song_by_next_page_in_album(data["next"])

    return tracks
