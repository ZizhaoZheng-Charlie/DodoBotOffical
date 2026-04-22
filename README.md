# DodoBot

A modern Discord music bot. YouTube + Spotify, slash commands, rich embeds with interactive controls, and auto-recommend. Designed to run 24/7 on an AWS `t3.micro` EC2 free-tier instance.

Rewritten in 2026: migrated off the unmaintained `pytube` to `yt-dlp 2026.3+`, `discord.py 2.7+`, `spotipy`. Speech-recognition features removed.

## Features

- `/play` with a **multi-result picker** - if your query matches several tracks, a dropdown appears so you can pick the right one before anything is enqueued.
- **Rich embeds** for every response: now-playing shows title, thumbnail, duration, uploader, queue length, and auto-recommend state.
- **Interactive control panel** attached to the now-playing message: Pause/Resume, Skip, Shuffle, Auto-recommend toggle, Refresh, Disconnect (discord buttons).
- **Auto-recommend mode**: when the queue empties and auto-recommend is ON, the bot pulls the YouTube Mix of the last track and keeps playing related songs.
- **Direct URL support**: paste any YouTube video / playlist / shorts link, or any Spotify track / album / playlist / artist link, and it just works. No picker shown for direct URLs (it goes straight into the queue).
- **Streaming, not downloading**: `yt-dlp` extracts the stream URL and `FFmpeg` pipes it directly to Discord - no temp files written to disk.

## Slash commands

| Command | Description |
|---------|-------------|
| `/play query:<text or URL>` | Enqueue a song. Text queries show a 5-result picker; URLs enqueue directly. |
| `/pause` | Pause or resume playback. |
| `/skip` | Skip the current track. |
| `/queue` | Show the upcoming queue. |
| `/shuffle` | Shuffle the queue. |
| `/clear` | Clear the queue and stop playback. |
| `/autorecommend` | Toggle auto-recommend mode. |
| `/disconnect` | Disconnect the bot from voice. |

## Environment variables

Copy `.env.example` to `.env` and fill in:

```env
DISCORD_TOKEN=<your bot token>
SPOTIFY_CLIENT_ID=<optional>
SPOTIFY_CLIENT_SECRET=<optional>
```

- **`DISCORD_TOKEN`** (required) - the bot token from the [Discord developer portal](https://discord.com/developers/applications).
- **`SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET`** (optional) - Spotify Web API app credentials. Without them the bot still plays YouTube fine; Spotify URLs will return a friendly error.
  - Heads up: as of 2026, Spotify restricts the Client Credentials flow to apps whose owner has an active Spotify Premium subscription. If you hit `403 premium required`, upgrade the app-owner account.

Legacy names `TOKEN`, `SPOTIFY_ID`, `SPOTIFY_SECRET` are still honoured so existing `.env` files keep working.

## Local run

Requires Python 3.11+ and `ffmpeg` on the `PATH`.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env   # then edit .env
python -m bot.main
```

On Linux/macOS:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then edit .env
python -m bot.main
```

## Tests

```powershell
pip install -r requirements-dev.txt
python -m pytest                    # unit tests only
python -m pytest -m integration     # live yt-dlp + spotify checks
python -m ruff check .
```

## AWS deployment (free tier)

**Why EC2 and not Lambda?** A Discord music bot needs a **persistent WebSocket gateway** and a **UDP voice connection**. AWS Lambda has a 15-minute execution cap and charges per millisecond - a 24/7 WebSocket cannot run there, and Lambda does not support UDP at all. Lambda is only useful for stateless HTTP-Interactions bots (no voice).

**So the deployment target is a single `t3.micro` EC2 instance** (AWS 12-month free tier: 750 hours/month - exactly enough for one instance running 24/7). After the 12-month window it costs ~$7.50/month, or drop to `t4g.nano` (ARM Graviton) for ~$3/month.

### Provision with one command

From a machine with `aws-cli` authenticated:

```powershell
.\deploy\launch.ps1 -Region us-east-1 -RepoUrl https://github.com/<you>/<repo>.git
```

This:

1. Creates a key pair `dodobot-key` (PEM saved to `deploy\dodobot-key.pem`, locked down via `icacls`).
2. Creates a `dodobot-sg` security group that only allows SSH from your current public IP.
3. Finds the latest Amazon Linux 2023 AMI.
4. Launches a `t3.micro` with 30 GB gp3, passing `deploy/bootstrap.sh` as user-data.

`bootstrap.sh` runs on first boot and:
- installs Python 3.12, git, and a static ffmpeg build,
- creates the `dodobot` system user,
- clones this repo to `/opt/dodobot`,
- creates a venv and installs `requirements.txt`,
- installs `deploy/dodobot.service` and enables it.

### Upload your `.env`

The service won't start until `DISCORD_TOKEN` is populated.

```powershell
scp -i .\deploy\dodobot-key.pem .\.env ec2-user@<public-ip>:/tmp/.env
ssh -i .\deploy\dodobot-key.pem ec2-user@<public-ip> `
  'sudo mv /tmp/.env /opt/dodobot/.env && sudo chown dodobot:dodobot /opt/dodobot/.env && sudo chmod 600 /opt/dodobot/.env && sudo systemctl restart dodobot'
```

### Logs

```powershell
ssh -i .\deploy\dodobot-key.pem ec2-user@<public-ip> 'sudo journalctl -u dodobot -f'
```

### Updating

SSH in and:

```bash
cd /opt/dodobot
sudo -u dodobot git pull
sudo -u dodobot .venv/bin/pip install -r requirements.txt
sudo systemctl restart dodobot
```

## Project layout

```
bot/
  main.py           # entry; builds bot, syncs slash commands
  config.py         # env loading
  audio.py          # yt-dlp streaming + FFmpeg source + YouTube Mix fetch
  search.py         # URL routing (YouTube / Spotify / text query)
  queue.py          # per-guild GuildQueue
  player.py         # playback loop, voice client, auto-recommend
  embeds.py         # rich-embed builders
  spotify_client.py # spotipy wrapper: URLs + search
  cogs/
    music.py        # Music cog (slash commands)
    views.py        # SongPickerView + ControlPanelView
deploy/
  launch.ps1        # AWS CLI provisioning
  bootstrap.sh      # EC2 user-data
  dodobot.service   # systemd unit
tests/              # pytest suite
```

## What changed from v1

- Removed: `speech_recognition`, `pyttsx3`, `pyaudio`, `gtts`, and all voice-command code.
- Removed: 82 MB `ffmpeg.exe` Windows binary from the repo (installed on-host instead).
- Removed: `[prefix]` message commands (`[radio]`, `[sradio]`, `[pause]`, etc.) in favour of slash commands.
- Removed: `pytube` (unmaintained; YouTube detection loops broke).
- Removed: download-to-disk playback (`<title>.mp3` files). Everything streams now.
- Added: multi-result picker, interactive button panel, rich embeds, auto-recommend.
- Added: systemd service, EC2 bootstrap scripts, AWS CLI one-shot launcher.

## License

See `LICENSE` in the repo.
