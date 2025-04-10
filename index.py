import argparse
import os
import time
import json
import hashlib
import threading
import requests
import webbrowser

from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Load environment variables
load_dotenv()

LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")
LASTFM_SHARED_SECRET = os.getenv("LASTFM_SHARED_SECRET")
SESSION_FILE = "lastfm_session.json"
PORT = 8080

token_holder = {"token": None}


# ========== LAST.FM AUTH AND SCROBBLE UTILS ==========


def generate_api_sig(params):
    sig_str = "".join(f"{k}{params[k]}" for k in sorted(params))
    sig_str += LASTFM_SHARED_SECRET
    return hashlib.md5(sig_str.encode("utf-8")).hexdigest()


def get_session_key(token):
    sig_params = {
        "method": "auth.getSession",
        "api_key": LASTFM_API_KEY,
        "token": token,
    }

    full_params = dict(sig_params)
    full_params["api_sig"] = generate_api_sig(sig_params)
    full_params["format"] = "json"

    response = requests.post("https://ws.audioscrobbler.com/2.0/", data=full_params)
    return response.json()


def start_local_server():
    import http.server
    import socketserver

    class TokenHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            if "/?token=" in self.path:
                token = self.path.split("token=")[1]
                token_holder["token"] = token
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"<h1>Token received! You can close this window.</h1>")
            else:
                self.send_response(400)
                self.end_headers()

    with socketserver.TCPServer(("", PORT), TokenHandler) as httpd:
        httpd.handle_request()


def save_session_key(session_data):
    with open(SESSION_FILE, "w") as f:
        json.dump(session_data, f, indent=2)


def load_session_key():
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r") as f:
                return json.load(f)["key"]
        except Exception:
            return None
    return None


def ensure_authenticated():
    session_key = load_session_key()
    if not session_key:
        print("[+] Launching browser to authenticate with Last.fm...")
        threading.Thread(target=start_local_server).start()
        url = f"https://www.last.fm/api/auth/?api_key={LASTFM_API_KEY}&cb=http://localhost:{PORT}"
        webbrowser.open(url)

        while not token_holder["token"]:
            time.sleep(1)

        print(f"[+] Token received: {token_holder['token']}")
        session_data = get_session_key(token_holder["token"])
        print("[DEBUG] Session response from Last.fm:", session_data)

        if "session" in session_data:
            session_key = session_data["session"]["key"]
            save_session_key(session_data["session"])
            print(f"[+] Authenticated! Session key: {session_key}")
        else:
            print("❌ Failed to authenticate.")
            exit(1)
    return session_key


def scrobble_track(session_key, artist, track, timestamp):
    params = {
        "method": "track.scrobble",
        "artist": artist,
        "track": track,
        "timestamp": str(timestamp),
        "api_key": LASTFM_API_KEY,
        "sk": session_key,
        "format": "json",
    }
    params["api_sig"] = generate_api_sig(params)
    response = requests.post("https://ws.audioscrobbler.com/2.0/", data=params)
    return response.json()


def scrobble_track_batch(session_key, tracks):
    if not tracks:
        return {}

    params = {
        "method": "track.scrobble",
        "api_key": LASTFM_API_KEY,
        "sk": session_key,
        "format": "json",
    }

    for i, (artist, title, timestamp) in enumerate(tracks):
        params[f"artist[{i}]"] = artist
        params[f"track[{i}]"] = title
        params[f"timestamp[{i}]"] = str(timestamp)

    sig_params = {k: v for k, v in params.items() if k != "format"}
    params["api_sig"] = generate_api_sig(sig_params)

    response = requests.post("https://ws.audioscrobbler.com/2.0/", data=params)

    try:
        result = response.json()
    except Exception:
        print("❌ Failed to parse Last.fm response.")
        return {}

    if "scrobbles" in result:
        scrobbles = result["scrobbles"].get("scrobble", [])
        if isinstance(scrobbles, dict):
            scrobbles = [scrobbles]

        for i, scrobble in enumerate(scrobbles):
            if (
                "ignoredMessage" in scrobble
                and scrobble["ignoredMessage"]["code"] != "0"
            ):
                msg = scrobble["ignoredMessage"]["#text"]
                print(f"⚠️  Track {i+1} was ignored: {msg}")
            if scrobble.get("artist", {}).get("corrected") == "1":
                corrected_artist = scrobble["artist"]["#text"]
                print(f"📝 Artist was corrected to: {corrected_artist}")
            if scrobble.get("track", {}).get("corrected") == "1":
                corrected_track = scrobble["track"]["#text"]
                print(f"📝 Track name was corrected to: {corrected_track}")

    return result


def get_scrobble_count(username):
    params = {
        "method": "user.getInfo",
        "user": username,
        "api_key": LASTFM_API_KEY,
        "format": "json",
    }
    response = requests.get("https://ws.audioscrobbler.com/2.0/", params=params)
    return int(response.json()["user"]["playcount"])


# ========== SPOTIFY INTEGRATION ==========


def get_spotify_tracks_from_playlist(playlist_url):
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope="playlist-read-private"))
    playlist_id = playlist_url.split("/")[-1].split("?")[0]
    results = sp.playlist_items(playlist_id)
    tracks = []

    for item in results["items"]:
        track = item["track"]
        if track:
            artist = track["artists"][0]["name"]
            title = track["name"]
            tracks.append((artist, title))
    return tracks


# ========== MAIN CLI ==========


def main():
    parser = argparse.ArgumentParser(description="Last.fm CLI Scrobbler")
    parser.add_argument("--playlist", help="Spotify playlist URL")
    parser.add_argument("--track", help="Track in format 'Artist - Song'")
    parser.add_argument(
        "--loop", type=int, help="Number of times to scrobble", default=1
    )
    parser.add_argument("--user", required=True, help="Your Last.fm username")
    args = parser.parse_args()

    session_key = ensure_authenticated()

    if args.playlist:
        print(f"[+] Loading playlist from Spotify: {args.playlist}")
        tracks = get_spotify_tracks_from_playlist(args.playlist)
        use_batch = True
    elif args.track:
        if " - " not in args.track:
            print("❌ Use format: 'Artist - Song'")
            return
        artist, title = args.track.split(" - ", 1)
        tracks = [(artist.strip(), title.strip())]
        use_batch = False
    else:
        print("❌ Please provide either --playlist or --track")
        return

    print(f"[+] Preparing to scrobble {len(tracks)} track(s)")
    loop = args.loop
    if loop == 1:
        user_input = input(
            "Press Enter to scrobble once, or enter a number to loop that many times: "
        )
        if user_input.isdigit():
            loop = int(user_input)

    initial_count = get_scrobble_count(args.user)
    print(f"🎧 You currently have {initial_count} scrobbles on Last.fm")

    for i in range(loop):
        print(f"\n🔁 Loop {i+1}/{loop}")
        if use_batch:
            batch = []
            for artist, title in tracks:
                timestamp = int(time.time())
                print(f"🎵 Queued: {artist} – {title}")
                batch.append((artist, title, timestamp - 60))
            print(f"[+] Sending batch of {len(batch)} track(s)...")
            scrobble_track_batch(session_key, batch)
            time.sleep(2)
        else:
            for artist, title in tracks:
                timestamp = int(time.time())
                print(f"🎵 Scrobbling: {artist} – {title}")
                scrobble_track(session_key, artist, title, timestamp - 60)
                time.sleep(1.5)

    final_count = get_scrobble_count(args.user)
    print(
        f"\n✅ Done! New scrobble count: {final_count} (added {final_count - initial_count})"
    )


if __name__ == "__main__":
    main()
