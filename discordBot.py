import discord
import os
from dotenv import load_dotenv
from pytube import YouTube
from pytube import Search
from collections import deque
import musicplaylist
import re
import asyncio
import speech_recognition as sr
import pyttsx3


load_dotenv()
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.presences = True
playList = deque()
client = discord.Client(intents=intents)
engine = pyttsx3.init()


@client.event
async def on_connect():
    print("We have logged in as {0.user}".format(client))


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("[hello]"):
        await message.channel.send(f"hello! {message.author.name}", tts=True)

    # connects the bot to voice channel
    if message.content.startswith("[connect]"):
        await message.delete()
        if message.author.voice:

            channel = message.author.voice.channel

            await channel.connect()
        else:
            await message.channel.send("you are not in voice channel")

    # exit the bot from terminal
    if message.content.startswith("[quit]"):
        await message.delete()
        exit()

    # disconnect the bot
    if message.content.startswith("[dc]"):
        voice_user = []
        await message.delete()
        for voiceClient in client.voice_clients:
            voice_user.append(voiceClient.user)

        if client.user in voice_user:
            idx = voice_user.index(client.user)
            if len(playList) != 0:
                musicplaylist.playList.clear()
            if os.path.exists(f"{musicplaylist.title}.mp3"):
                client.voice_clients[idx].stop()
                await asyncio.sleep(0.5)
                os.remove(f"{musicplaylist.title}.mp3")
            await client.voice_clients[idx].disconnect()

        else:
            await message.channel.send("The bot is not in the voice channel")
    # play audio depends on URL or message.content
    if message.content.startswith("[radio]"):

        if len(message.content.split(" ", 1)) == 1:
            await message.channel.send(
                "this cmd is for playing music with a simply link or name of the music, any other help please use [help]"
            )
            await message.delete()
            return

        if not message.author.voice:
            await message.channel.send("You are not in a voice channel")
            await message.delete()
            return

        if client.user not in message.author.voice.channel.members:
            channel = message.author.voice.channel
            voice = await channel.connect()
        else:
            voice = client.voice_clients[0]

        await message.delete()
        cmd = message.content
        new_list = deque()
        link_title = ""
        link = ""
        if "youtube.com" in cmd.split(" ", 1)[1]:
            cmd_idx = cmd.split(" ", 1)[1].find("youtube.com")
            update_cmd = cmd.split(" ", 1)[1][cmd_idx:]
            new_list.extend(await musicplaylist.youtube_link(update_cmd))
            link_title = musicplaylist.link_title

            if link_title.startswith("link doesn't work"):
                await message.channel.send(link_title)
                return
            link = cmd.split(" ", 1)[1]

        elif "open.spotify.com" in cmd.split(" ", 1)[1]:
            cmd_idx = cmd.split(" ", 1)[1].find("open.spotify.com")
            update_cmd = cmd.split(" ", 1)[1][cmd_idx:]
            new_list = await musicplaylist.spotify_link(update_cmd, new_list)
            link_title = musicplaylist.link_title
            if link_title.startswith(
                "This can only find song, albums, artists, and playlists"
            ):
                await message.channel.send(link_title)
                return
            elif link_title.startswith("link doesn't work"):
                await message.channel.send(link_title)
                return
            link = cmd.split(" ", 1)[1]
        elif cmd.split(" ", 2)[1].startswith("yt"):
            search = Search(message.content.split(" ", 2)[2]).results
            if len(search) == 0:
                await message.channel.send("No result is being found")
                return
            new_list.append(message.content.split(" ", 2)[2])
            link_title = message.content.split(" ", 2)[2]
            link = "YouTube search don't have link"
        elif cmd.split(" ", 2)[1].startswith("artists"):
            new_list = await musicplaylist.spotify_artist(
                message.content.split(" ", 2)[2], new_list
            )
            if new_list == None:
                await message.channel.send("No artists being found")
                return
            link_title = musicplaylist.link_title
            link = musicplaylist.link
        elif cmd.split(" ", 2)[1].startswith("albums"):
            new_list = await musicplaylist.spotify_album(
                message.content.split(" ", 2)[2], new_list
            )
            if new_list == None:
                await message.channel.send("No album being found")
                return
            link_title = musicplaylist.link_title
            link = musicplaylist.link
        elif cmd.split(" ", 2)[1].startswith("playlists"):
            new_list = await musicplaylist.spotify_playlist(
                message.content.split(" ", 2)[2], new_list
            )
            if new_list == None:
                await message.channel.send("No album being found")
                return
            link_title = musicplaylist.link_title
            link = musicplaylist.link
        else:
            link_title = await musicplaylist.spotify_search(
                message.content.split(" ", 1)[1]
            )
            if link_title == None:
                await message.channel.send("No song being found")
                return
            new_list.append(link_title)
            link = musicplaylist.link

        playList.extend(new_list)
        await message.channel.send(f"Added {link_title} to the playlist")
        await message.channel.send(f"```URL Link: {link}```")
        if client.voice_clients[0].source:
            return

        await musicplaylist.play_audio(voice, playList)

    # pause the audio
    if message.content.startswith("[pause]"):
        await message.delete()
        if client.voice_clients[0].is_playing():
            client.voice_clients[0].pause()
        else:
            client.voice_clients[0].resume()

    # skip the audio to next audio in the playlist
    if message.content.startswith("[skip]"):
        await message.delete()
        if not client.voice_clients or not client.voice_clients[0].is_connected():
            await message.channel.send(
                "I am not currently connected to a voice channel."
            )
            return

        if len(playList) == 0:
            await message.channel.send("There are no items in the playlist to skip.")
            return

        client.voice_clients[0].stop()

    # clear whole playlist and the current playing audio
    if message.content.startswith("[clear]"):
        await message.delete()
        if client.voice_clients and (
            client.voice_clients[0].is_playing() or client.voice_clients[0].is_paused()
        ):
            # Stop the playback
            client.voice_clients[0].stop()
            # Await the stop to ensure it's completed
            await asyncio.sleep(1)
            # Assuming musicplaylist.title contains the title of the currently playing song
            if os.path.exists(f"{musicplaylist.title}.mp3"):
                # Remove the corresponding MP3 file
                os.remove(f"{musicplaylist.title}.mp3")

        # Clear the playlist
        playList.clear()

    # show the current queue
    if message.content.startswith("[queue]"):
        if (
            not message.guild.voice_client
            or not message.guild.voice_client.is_playing()
        ):
            await message.channel.send("There is no song currently playing.")
        else:
            current_song = "Currently playing: "
            if message.guild.voice_client.source:
                current_song += musicplaylist.title
            await message.channel.send(current_song)

        if playList:
            queue_info = "Queue:\n"

            for idx, link in enumerate(playList, start=1):
                try:
                    yt = YouTube(link)
                    title = re.sub(r'[\\/*?:"<>|]', "", yt.title)
                    queue_info += f"{idx}. {title}\n"
                except:
                    queue_info += f"{idx}. {link}\n"
                if idx == 10:
                    break
                await message.channel.send(queue_info)
        else:
            await message.channel.send("The queue is empty.")

        # show the cmd that bot offers
    if message.content.startswith("[help]"):
        await message.delete()
        if len(message.content.split(" ", 1)) == 1:
            await message.channel.send(
                "```"
                + "Command descrption and usage: \n"
                + "[connect]: the bot to connect to the voice channel of the user who issued the command. \n"
                + "[dc]: disconnect the bot from the voice channel it is currently in, if it is present in any voice channel. \n"
                + "[radio]: used to play music in a voice channel. It accepts various types of inputs, such as YouTube links, Spotify links, or search queries for YouTube or Spotify. For futher information use: [help] cmd \n"
                + "[pause]: used to pause or resume audio playback in the voice channel where the bot is currently connected. \n"
                + "[skip]:  used to skip the current item in the playlist and move to the next one. \n"
                + "[clear]: used to clear the playlist and stop the currently playing audio, if any. \n"
                + "[queue]:  used to display the currently playing song (if any) and the upcoming songs in the queue. \n"
                + "[help]: It allows users to get information about available commands and their usages. \n"
                + "```"
            )
            return

        help = message.content.split(" ", 1)

        if help[1].startswith("radio"):
            await message.channel.send(
                "```"
                + "Parameters:"
                + "\t simply search looking first song in spotify search\n"
                + "\tyt: look the first youtube result in youtube search\n"
                + "\talbums: look the first album result in spotify search\n"
                + "\tartists: look the first artist result in spotify search\n"
                + "\tplaylist: look the first playlist result in spotify search\n"
                + "Example: \n"
                + "\t[radio] https://open.spotify.com/artist/5JZ7CnR6gTvEMKX4g70Amv?si=4bj8VGu3QA-N_G2zprlFow \n"
                + "\t[radio] https://www.youtube.com/shorts/jeCvbd7gejE \n"
                + "\t[radio] Fly Me To The Moon \n"
                + "\t[radio] yt keep learning \n"
                + "\t[radio] albums adventure \n"
                + "\t[radio] artists lauv \n"
                + "\t[radio] playlist lofi"
                + "```"
            )
        else:
            await message.channel.send(" no such cmd futher informations")


# the bot has voice recognition
@client.event
async def on_voice_state_update(member, before, after):
    if client.voice_clients:
        voice_client = client.voice_clients[0]
        await asyncio.sleep(2)
        while after.channel and not before.channel:
            try:
                r = sr.Recognizer()
                r.pause_threshold = 1.5
                r.phrase_threshold = 0.5
                timeout = 1.5
                with sr.Microphone(device_index=2) as source:
                    audio = r.listen(source, timeout=1, phrase_time_limit=2.5)
            except sr.WaitTimeoutError:
                continue
            try:
                text = r.recognize_google(audio)
                print(text)
                await asyncio.sleep(1)
                if text.startswith("play"):
                    video_title = text.split(" ", 1)
                    if len(video_title) == 1:

                        if voice_client.is_playing():
                            voice_client.pause()
                        engine.say("Try again with the command")
                        engine.runAndWait()
                        engine.stop()
                        voice_client.resume()
                        continue

                    if voice_client.is_playing() or voice_client.is_paused():
                        search_result = Search(video_title).results[0]
                        playList.append(search_result.title)
                        if voice_client.is_playing():
                            voice_client.pause()
                        engine.say(f"Added {search_result.title} to playlist.")
                        engine.runAndWait()
                        engine.stop()
                        voice_client.resume()
                        continue

                    musicplaylist.play_audio_by_result(video_title, voice_client)

                if text.startswith("show playlist"):
                    if not voice_client.is_playing():
                        engine.say("There is no song currently playing")
                        engine.runAndWait()
                    else:
                        engine.say(f"Currently playing: {musicplaylist.title}")
                        engine.runAndWait()

                    if playList:
                        engine.say("Queue")
                        for i, song in enumerate(playList, start=1):
                            try:
                                yt = YouTube(song)
                                title = re.sub(r'[\\/*?:"<>|]', "", yt.title)
                            except:
                                title = song
                            
                            engine.say(f"{i} {title}")
                            engine.runAndWait()
                            if i == 10:
                                break
                    else:
                        engine.say("The queue is empty")
                        engine.runAndWait()

                    engine.stop()

                if text.startswith("pause the music"):
                    if voice_client.is_playing():
                        voice_client.pause()
                    else:
                        voice_client.resume()

                if text.startswith("skip"):
                    if len(playList) == 0:
                        engine.say("There are no items in the playlist to skip.")
                        engine.runAndWait()
                        engine.stop()
                        continue
                    voice_client.stop()

                if not voice_client.source and playList:
                    voice_client.stop()
                    await asyncio.sleep(2)
                    video_title = playList.popleft()
                    musicplaylist.play_audio_by_result(video_title, voice_client)
            except sr.UnknownValueError:
                await asyncio.sleep(1)
            await asyncio.sleep(0.3)


client.run(os.getenv("TOKEN"))
