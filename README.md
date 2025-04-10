# 🎧 last.fm-spoofer

A custom Python CLI that scrobbles tracks to [Last.fm](https://www.last.fm) — from **Spotify playlists** or **manual track input**. Includes real-time updates, looping, and automatic batching. Perfect for boosting your stats or just vibing with some fake nostalgia.

## ⚡ Features

- ✅ Scrobble any track manually (artist + title)
- ✅ Scrobble full Spotify playlists
- ✅ Choose how many times to loop scrobbles
- ✅ Automatically uses batch scrobbling for efficiency
- ✅ Shows your current and updated scrobble count
- ✅ Logs ignored tracks and Last.fm metadata corrections

---

## 🔧 Setup

### 1. Clone the Repo

```bash
git clone https://github.com/opsec-bot/last.fm-spoofer.git
cd last.fm-spoofer
```

### 2. Install Requirements

```bash
pip install -r requirements.txt
```

Or manually:

```bash
pip install requests spotipy python-dotenv
```

### 3. Set Up `.env`

Create a `.env` file in the project root with the following:

```env
LASTFM_API_KEY=your_lastfm_api_key
LASTFM_SHARED_SECRET=your_lastfm_shared_secret

SPOTIPY_CLIENT_ID=your_spotify_client_id
SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
SPOTIPY_REDIRECT_URI=http://localhost:8888/callback/
```

> Make sure you register your Spotify app at [developer.spotify.com](https://developer.spotify.com) and your Last.fm app at [www.last.fm/api](https://www.last.fm/api).

Also, add this redirect URI in your Spotify app settings:

```
http://localhost:8888/callback/
```

---

## 🚀 Usage

### 🔂 Scrobble a Single Track

```bash
python index.py --track "PSY - Gangnam Style" --user your_lastfm_username
```

You’ll be prompted to loop it as many times as you want.

---

### 🎵 Scrobble a Full Spotify Playlist

```bash
python index.py --playlist https://open.spotify.com/playlist/your_playlist_id --user your_lastfm_username
```

This will batch scrobble all tracks in the playlist. You can loop them too:

```bash
python index.py --playlist https://open.spotify.com/playlist/... --user your_lastfm_username --loop 5
```

---

## 🧠 Notes

- All scrobbles are timestamped as if they just happened.
- If Last.fm corrects or ignores a track, you'll see it in the output.

---
