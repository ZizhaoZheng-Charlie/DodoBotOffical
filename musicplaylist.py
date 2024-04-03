import asyncio
from pytube import YouTube
from pytube import Search
from pytube import Playlist
import discord
from collections import deque
import os
import re
from dotenv import load_dotenv
import spotify


load_dotenv()

# play audio with URL or song name
async def play_audio(voice, queue):
    global playList, title
    playList = queue
    link = playList.popleft()
    try:
        yt = YouTube(link)
    except:
        yt = Search(link).results[0]
    stream = yt.streams.filter(only_audio=True).first()
    title = re.sub(r'[\\/*?:"<>|]', "", yt.title)
    stream.download(filename=f"{title}.mp3")
    audio = discord.FFmpegPCMAudio(f"{title}.mp3", executable="ffmpeg.exe")
    voice.play(audio)
    
    # waiting for the audio to end
    while voice.is_playing():
        await asyncio.sleep(1)

    # loop the playlist until end
    if playList:
        os.remove(f"{title}.mp3")
        await play_audio(voice, playList)


# play audio depends on the result of speech to text
def play_audio_by_result(video_result, voice):
    global title
    if "title" in globals() and os.path.exists(f"{title}.mp3"):
        os.remove(f"{title}.mp3")
    search_result = Search(video_result).results[0]
    dl = search_result.streams.filter(only_audio=True).first()
    title = re.sub(r'[\\/*?:"<>|]', "", search_result.title)
    dl.download(filename=f"{title}.mp3")
    audio = discord.FFmpegPCMAudio(f"{title}.mp3", executable="ffmpeg.exe")
    voice.play(audio)

# append the youtube link into the playlist
async def youtube_link(link):
    global link_title
    category = link[11:]
    new_list = deque()
    if category.startswith("/playlist?list="):
        try:
            p = Playlist(link)
        except:
            link_title = "link doesn't work"
            return new_list
        link_title = p.title
        p_urls = p.video_urls
        new_list.extend(p_urls)
    elif category.startswith("/watch?v="):
        try:
            link_title = YouTube(link).title
        except:
            link_title = "link doesn't work"
            return new_list
        new_list.append(link)
    elif category.startswith("/shorts/"):
        try:
            link_title = YouTube(link).title
        except:
            link_title = "link doesn't work"
            return new_list
        new_list.append(link)
    else:
        link_title = "link doesn't work"
        return new_list

    return new_list

# append the spotify link into the playlist
async def spotify_link(link, playList):
    global link_title
    try:
        result = spotify.search_URL(link)
    except:
        link_title = "link doesn't work"
        return playList
    
    if "error" in result:
        link_title = "link doesn't work"
        return playList  
    spotify_list = link.split("/")

    if "album" in spotify_list:
        data = result["tracks"]
        link_title = f"{result['name']} by {result['artists'][0]['name']}"

        for song in data["items"]:
            track = f"{song['name']} by {await spotify.song_artists_in_album(song)}"
            playList.append(track)

        if data["next"]:
            playList += await spotify.list_of_Song_by_next_page_in_album(data["next"])

    elif "playlist" in spotify_list:
        data = result["tracks"]
        link_title = f"{result['name']} by {result['owner']['display_name']}"

        for song in data["items"]:
            track = ""
            songname = song["track"]["name"]
            track = f"{songname} by {await spotify.song_artists_in_playlist(song)}"
            playList.append(track)

        if data["next"]:
            playList += await spotify.list_of_Song_by_next_page_in_playlist(
                data["next"]
            )

    elif "artist" in spotify_list:
        link_title = f"{result['tracks'][0]['artists'][0]['name']} Top tracks"
        for song in result["tracks"]:
            track = f"{song['name']} by {await spotify.song_artists_in_album(song)}"
            playList.append(track)

    elif "track" in spotify_list:
        song_name = await spotify.song_artists_in_album(result)
        link_title = f"{result['name']} by {song_name}"
        playList.append(f"{result['name']} by {song_name}")

    else:
        link_title = "This can only find song, albums, artists, and playlists"
    return playList

# search song using message contents, only get the first results
async def spotify_search(search):
    update_search = search.replace(" ", "+")
    data = await spotify.search_song(update_search)
    print(data)
    if data["total"] == 0:
        return None

    return f'{data["items"][0]["name"]} by {await spotify.song_artists_in_album(data["items"][0])}'

# search artists using message contents, only get the first results
async def spotify_artist(search, playList):
    global link_title
    update_search = search.replace(" ", "+")
    data = await spotify.search_for_artist(update_search)

    if data["total"] == 0:
        return None

    result = await spotify.search_song_by_artistID(data["items"][0]["id"])
    link_title = f"{result[0]['artists'][0]['name']} Top tracks"

    for song in result:
        track = f"{song['name']} by {await spotify.song_artists_in_album(song)}"
        playList.append(track)

    return playList

# search albums using message contents, only get the first results
async def spotify_album(search, playList):
    global link_title
    update_search = search.replace(" ", "+")
    data = await spotify.search_for_album(update_search)
    if data["total"] == 0:
        return None
    result = data['items'][0]
    link_title = f"{result['name']} by {result['artists'][0]['name']}"
    data = await spotify.search_by_albumID(result["id"])
    for song in data["items"]:
        track = f"{song['name']} by {await spotify.song_artists_in_album(song)}"
        playList.append(track)

    if data["next"]:
        playList += await spotify.list_of_Song_by_next_page_in_album(data["next"])

    return playList

# search playlist using message contents, only get the first results
async def spotify_playlist(search, playList):
    global link_title
    update_search = search.replace(" ", "+")
    data = await spotify.search_for_playlist(update_search)
    if data["total"] == 0:
        return None
    result = data['items'][0]
    link_title = f"{result['name']} by {result['owner']['display_name']}"
    data = await spotify.search_by_albumID(result["id"])
    for song in data["items"]:
            track = ""
            songname = song["track"]["name"]
            track = f"{songname} by {await spotify.song_artists_in_playlist(song)}"
            playList.append(track)

    if data["next"]:
        playList += await spotify.list_of_Song_by_next_page_in_playlist(
            data["next"]
        )
    return playList