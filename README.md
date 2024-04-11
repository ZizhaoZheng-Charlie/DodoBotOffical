# Discord Bot Commands

This repository contains a collection of commands for a Discord bot. Each command is triggered by a specific prefix and performs a specific action within a Discord server.

## Basic Requirements

- All requirements could be install from the requirement.txt
- Python 3.7 or higher
- Discord.py library (install via `pip install discord.py`)
- pytube library (install via `pip install pytube`)
- asyncio library (included in Python standard library)
- re library (included in Python standard library)
- pyaudio library (install via `pip install pyaudio`)
- python-dotenv library (install via `pip install python-dotenv`)
- pynacl library (install via `pip install pynacl`)
- ffmpeg-python library (install via `pip install ffmpeg-python` and ffmpeg)
- Discord API key
- Spotify API key

## Voice Requirements (only avaliable for the who started the discord bot)

- pyttsx3 library (install via `pip install pyttsx3`)
- SpeechRecognition (install via `pip install SpeechRecognition`)
- pyaudio (install via `pip install pyaudio`)

## Commands

### [help]

**Description:** This command displays a list of available commands or provides information about a specific command.

### [connect]

**Description:** This command allows the bot to connect to the voice channel of the user who issued the command.

### [radio]

**Description:** This command is used to play music in a voice channel. It accepts various types of inputs, such as YouTube links, Spotify links, or search queries for YouTube or Spotify.

### [pause]

**Description:** This command is used to pause or resume audio playback in the currently connected voice channel.

### [skip]

**Description:** This command is used to skip the current item in the playlist and move to the next one.

### [clear]

**Description:** This command is used to clear the playlist and stop the currently playing audio, if any.

### [queue]

**Description:** This command is used to display the currently playing song (if any) and the upcoming songs in the queue.

### [shuffle]

**Description:** This command is shuffle the current queue of songs.

### [sradio]

**Description:** This command is shuffle the added playlist or songs into the queue.
## Usage

To use these commands, prefix each command with the corresponding prefix (e.g., `[help]`, `[connect]`, etc.) in a Discord server where the bot is present.

## Notes

- Some commands require the bot to be connected to a voice channel.
- Ensure that necessary permissions are granted for the bot to perform actions within the server.

## Voice Command

### play

**Description** This command play the audio by Youtube searchs the parameters

### pause the music

**Description** This command pause and unpause the audio

### skip

**Description:** This command is used to skip the current item in the playlist and move to the next one.

### show playlist

**Description:** This command is used to display the currently playing song (if any) and the upcoming songs in the queue.

