import cv2
import mediapipe as mp
import pyautogui
import time
import os
import subprocess
import threading
import speech_recognition as sr
import rumps
import urllib.error
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import difflib
import sys

def sample_energy(seconds=3):
    r = sr.Recognizer(); r.dynamic_energy_threshold=False
    with sr.Microphone() as src:
        print("Speak or play music for", seconds, "seconds…")
        r.listen(src, phrase_time_limit=seconds)
        print("Peak energy measured:", r.energy_threshold)

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id="f8f7d5f92d924d28b15832cc32d69557",
    client_secret="4195eeff05614d929e6881dcf1855353",
    redirect_uri="http://127.0.0.1:8888/callback",
    scope="user-read-playback-state user-modify-playback-state playlist-read-private playlist-read-collaborative"
))

quit_app = False

# Sounds
def ding():
    subprocess.Popen(['afplay', '/System/Library/Sounds/Glass.aiff'])

def beep():
    subprocess.Popen(['afplay', '/System/Library/Sounds/Pop.aiff'])

def increase_brightness():
    os.system("osascript -e 'tell application \"System Events\" to key code 144'")  # F2

def decrease_brightness():
    os.system("osascript -e 'tell application \"System Events\" to key code 145'")  # F1

def increase_volume():
    os.system("osascript -e 'set volume output volume (output volume of (get volume settings) + 5)'")

def decrease_volume():
    os.system("osascript -e 'set volume output volume (output volume of (get volume settings) - 5)'")


def get_playlist_tracks(playlist_uri):
    """
    Fetches *all* tracks from a Spotify playlist, paging through if >100 items.
    Returns a list of track dicts.
    """
    tracks = []
    results = sp.playlist_items(
        playlist_uri,
        fields="items.track.name,items.track.artists,items.track.uri,next",
        limit=100
    )
    tracks.extend(results["items"])
    # page through
    while results.get("next"):
        results = sp.next(results)
        tracks.extend(results["items"])
    return [item["track"] for item in tracks]


def play_track(track, from_playlist=False):
    devices = get_spotify_devices()
    if not devices:
        os.system("say 'No active Spotify device. Please open Spotify and start playing a track.'")
        return

    if from_playlist:
        all_tracks = get_playlist_tracks(spotify_state["playlist_uri"])
        # 1) try exact match (case‑insensitive)
        exact = [t for t in all_tracks if t["name"].lower().strip() == track.lower().strip()]
        if len(exact) == 1:
            # only one → just play it
            t = exact[0]
            sp.start_playback(
                device_id=devices[0]["id"],
                context_uri=spotify_state["playlist_uri"],
                offset={"uri": t["uri"]}
            )
            os.system(f"say 'Playing {t['name']} by {t['artists'][0]['name']} from your playlist.'")
            return

        elif len(exact) > 1:
            # several tracks with the same title → ask for artist
            spotify_state["last_results"] = exact        # store full track dicts
            # collect every unique artist name that appears on those versions
            artist_set = set(a["name"] for t in exact for a in t["artists"])
            options = ", ".join(sorted(artist_set))
            os.system(f"say 'Multiple tracks named {track}. Say the artist name. Options are: {options}'")
            return

        # 2) fallback fuzzy (on lowercased names)
        names_lower = [t["name"].lower().strip() for t in all_tracks]
        closest = difflib.get_close_matches(track.lower().strip(), names_lower, n=1, cutoff=0.5)
        if not closest:
            os.system("say 'No matching tracks found in that playlist.'")
            return

        # map fuzzy match back to track dict
        match_name = closest[0]
        matches = [t for t in all_tracks if t["name"].lower().strip() == match_name]

        # now mirror your old disambiguation / playback logic:
        if len(matches) == 1:
            track = matches[0]
            sp.start_playback(
                device_id=devices[0]["id"],
                context_uri=spotify_state["playlist_uri"],
                offset={"uri": track["uri"]}
            )
            os.system(f"say 'Playing {track['name']} by {track['artists'][0]['name']} from your playlist.'")
        else:
            spotify_state["last_results"] = matches
            artist_set = set(a["name"] for t in matches for a in t["artists"])
            artists = ", ".join(sorted(artist_set))
            os.system(f"say 'Multiple tracks named {track}. Say the artist name. Options are: {artists}'")
        return


    # --- GLOBAL SEARCH WITH EXACT → FUZZY ---
    results = sp.search(q=track, type="track", limit=10)
    tracks = results.get("tracks", {}).get("items", [])
    if not tracks:
        os.system("say 'No matching tracks found.'")
        return

    # 1) exact (case-insensitive)
    exact_matches = [
        t for t in tracks
        if t["name"].lower().strip() == track.lower().strip()
    ]
    if len(exact_matches) == 1:
        # only one perfect match  → play it
        t = exact_matches[0]
        sp.start_playback(device_id=devices[0]["id"], uris=[t["uri"]])
        os.system(f"say 'Playing {t['name']} by {t['artists'][0]['name']}'")
        return

    elif len(exact_matches) > 1:
        # several tracks with that title → ask which artist
        spotify_state["last_results"] = exact_matches   # store full track dicts
        spotify_state["mode"] = "search"               # mark that we’re in global disambiguation
        artist_set = set(a["name"] for t in exact_matches for a in t["artists"])
        options = ", ".join(sorted(artist_set))
        os.system(f"say 'Multiple tracks named {track}. Say the artist name. Options are: {options}'")
        return

    # 2) fuzzy on lowercased names
    names_lower = [t["name"].lower().strip() for t in tracks]
    closest = difflib.get_close_matches(track.lower().strip(), names_lower, n=1, cutoff=0.5)
    if not closest:
        os.system("say 'No matching tracks found.'")
        return

    match_name = closest[0]
    matches = [t for t in tracks if t["name"].lower().strip() == match_name]

    if len(matches) == 1:
        t = matches[0]
        sp.start_playback(device_id=devices[0]["id"], uris=[t["uri"]])
        os.system(f"say 'Playing {t['name']} by {t['artists'][0]['name']}'")
    else:
        spotify_state["last_results"] = matches
        artist_set = set(a["name"] for t in matches for a in t["artists"])
        artists = ", ".join(sorted(artist_set))
        os.system(f"say 'Multiple results found. Say the artist name. Options are: {artists}'")

spotify_state = {
    "mode": None,          # "search" or "playlist"
    "last_results": [],    # list of (track_name, artist_name, uri)
    "playlist_uri": None,  # URI of selected playlist
}

def clear_playlist_mode():
    spotify_state["mode"] = None
    spotify_state["last_results"] = []
    spotify_state["playlist_uri"] = None
    print("[INFO] Playlist mode exited, disambiguation cleared.")
    os.system("say 'Exited playlist mode. You can now use Spotify play to search globally.'")


def play_by_artist(artist_query):
    """
    Resolve artist after duplicate-title prompt (playlist or global).
    """
    q = artist_query.lower().strip()
    if "exit playlist" in q:
        clear_playlist_mode()
        return

    if not spotify_state["last_results"]:
        os.system("say 'No pending track selection.'")
        return

    # map every artist name → the track that features them
    artist_map = {}
    for t in spotify_state["last_results"]:
        for a in t["artists"]:
            artist_map[a["name"].lower()] = t

    closest = difflib.get_close_matches(q, artist_map.keys(), n=1, cutoff=0.5)
    if not closest:
        os.system("say 'No matching artist found. Please say the artist name again or say exit playlist.'")
        return

    chosen = artist_map[closest[0]]
    devices = get_spotify_devices()
    if not devices:
        os.system("say 'No active Spotify device.'")
        return

    if spotify_state["mode"] == "playlist":
        sp.start_playback(
            device_id=devices[0]["id"],
            context_uri=spotify_state["playlist_uri"],
            offset={"uri": chosen["uri"]}
        )
    else:  # global search
        sp.start_playback(device_id=devices[0]["id"], uris=[chosen["uri"]])

    os.system(f"say 'Playing {chosen['name']} by {chosen['artists'][0]['name']}.'")
    clear_playlist_mode()          # reset disambiguation / mode

def get_playlist_tracks(playlist_uri):
    tracks = []
    results = sp.playlist_items(
        playlist_uri,
        fields="items.track.name,items.track.artists,items.track.uri,next",
        limit=100
    )
    tracks.extend(results["items"])
    # follow next pages
    while results.get("next"):
        results = sp.next(results)
        tracks.extend(results["items"])
    # return just the track dicts
    return [item["track"] for item in tracks]

def get_spotify_devices():
    try:
        return sp.devices().get("devices", [])
    except Exception as e:
        print(f"[Spotify devices] error: {e}")
        os.system("say 'Spotify connection lost. Please retry.'")
        return []

def safe_spotify_call(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except Exception as e:
        print(f"[Spotify API] error: {e}")
        os.system("say 'Spotify connection lost or unavailable.'")
        return None

# Menubar badge
app = rumps.App("✋")

def set_badge(text=""):
    app.title = text

gesture_mode = None  # shared between threads
quit_app = False

# Finger pose helpers
def is_finger_up(lm, tip, pip):
    return lm[tip].y < lm[pip].y

def is_index_only(lm):
    return (is_finger_up(lm, 8, 6) and
            not any(is_finger_up(lm, t, p) for t, p in [(12,10), (16,14), (20,18)]))

def is_index_and_middle(lm):
    return (is_finger_up(lm, 8, 6) and is_finger_up(lm, 12, 10) and
            not any(is_finger_up(lm, t, p) for t, p in [(16,14), (20,18)]))

def execute_voice_command(cmd: str):
    global gesture_mode
    cmd = cmd.lower().strip()

    global quit_app
    if cmd in ("quit", "quit app", "exit app"):
        os.system("say 'Shutting down. Goodbye.'")
        quit_app = True
        sys.exit(0)

    # 0) Gesture Modes FIRST — always accessible
    if "scrolling" in cmd:
        gesture_mode = "scrolling"
        print("→ Mode: Scrolling")
        return
    if "volume" in cmd:
        gesture_mode = "volume"
        print("→ Mode: Volume")
        return
    if "brightness" in cmd:
        gesture_mode = "brightness"
        print("→ Mode: Brightness")
        return
    if "off" in cmd:
        gesture_mode = "off"
        print("→ Mode: Off")
        subprocess.Popen(["afplay", "/System/Library/Sounds/Submarine.aiff"])
        return
    
    if cmd.startswith("play") and spotify_state["mode"] != "playlist":
        track_query = cmd[4:].strip()
        if not track_query:
            os.system("say 'Track not found. Please try again'")
            return

        # Check if user said "track by artist"
        if " by " in track_query:
            track_name, artist_name = track_query.split(" by ", 1)
            track_name = track_name.strip()
            artist_name = artist_name.strip()
            # Use special combined search
            query = f"track:{track_name} artist:{artist_name}"
            results = sp.search(q=query, type="track", limit=1)
            tracks = results.get("tracks", {}).get("items", [])
            if tracks:
                t = tracks[0]
                sp.start_playback(device_id=get_spotify_devices()[0]["id"], uris=[t["uri"]])
                os.system(f"say 'Playing {t['name']} by {t['artists'][0]['name']}'")
            else:
                os.system("say 'No matching track and artist found.'")
        else:
            # Regular track search
            play_track(track_query, from_playlist=False)
        return
    
    # 5) Chrome commands
    if "chrome" in cmd:
        # bring Chrome to front
        os.system('osascript -e \'tell application "Google Chrome" to activate\'')
        # play/pause in web player
        if "play" in cmd or "pause" in cmd:
            os.system('osascript -e \'tell application "System Events" to keystroke " " \'')
            return
        if "new tab" in cmd:
            os.system('osascript -e \'tell application "System Events" to keystroke "t" using {command down}\'')
            return
        if "close tab" in cmd:
            os.system('osascript -e \'tell application "System Events" to keystroke "w" using {command down}\'')
            return
        if "next tab" in cmd:
            os.system('osascript -e \'tell application "System Events" to key code 124 using {command down, option down}\'')
            return
        if "previous tab" in cmd:
            os.system('osascript -e \'tell application "System Events" to key code 123 using {command down, option down}\'')
            return

    # 1) Explicit exit from playlist mode
    if spotify_state["mode"] == "playlist" and "exit playlist" in cmd:
        clear_playlist_mode()
        return

    # 2) Playlist‐mode direct track name (no “spotify play” needed)
    if spotify_state["mode"] == "playlist" and "spotify" not in cmd:
        play_track(cmd, from_playlist=True)
        return

    # 4) Spotify commands
    if "spotify" in cmd:
        # — Select a playlist —
        if "playlist" in cmd:
            playlist_name = cmd.split("playlist", 1)[1].strip().lower()

            # fetch playlists first
            results = sp.current_user_playlists(limit=50)

            # build a normalized name list
            playlist_names = [item["name"].lower().strip() for item in results["items"]]
            closest = difflib.get_close_matches(playlist_name, playlist_names, n=1, cutoff=0.5)

            if closest:
                target = closest[0]
                for item in results["items"]:
                    if item["name"].lower().strip() == target:
                        spotify_state["playlist_uri"] = item["uri"]
                        spotify_state["mode"] = "playlist"
                        os.system(f"say 'Playlist {item['name']} selected. Say the track name.'")
                        return

            os.system("say 'Playlist not found. Please say the playlist name again.'")
            return

        # — Global play (only when NOT in playlist mode) —
        if "play" in cmd and spotify_state["mode"] != "playlist":
            track = cmd.split("play", 1)[1].strip()
            if not track:
                os.system("say 'Track not found. Please try again'")
                return
            play_track(track, from_playlist=False)
            return

        # — Pause/Resume/Next/Previous —
        if "pause" in cmd:
            os.system("osascript -e 'tell application \"Spotify\" to pause'")
            os.system("say 'Paused'")
            return
        if "resume" in cmd:
            os.system("osascript -e 'tell application \"Spotify\" to play'")
            os.system("say 'Resumed'")
            return
        if "next" in cmd:
            os.system("osascript -e 'tell application \"Spotify\" to next track'")
            os.system("say 'Next track'")
            return
        if "previous" in cmd:
            os.system("osascript -e 'tell application \"Spotify\" to previous track'")
            os.system("say 'Previous track'")
            return

    # 6) Fallback: unrecognized command — do nothing or add logging here

def voice_command_listener():
    global quit_app
    recognizer = sr.Recognizer()

    recognizer.dynamic_energy_threshold = False
    recognizer.energy_threshold = 3000
    recognizer.pause_threshold = 0.6
    recognizer.non_speaking_duration = 0.4

    mic = sr.Microphone()
    with mic as source:
        recognizer.adjust_for_ambient_noise(source)

    print("Voice assistant ready (Google Speech Recognition)")

    while not quit_app:
        with mic as source:
            audio = recognizer.listen(source, phrase_time_limit=4)

        try:
            command = recognizer.recognize_google(audio)
            print(f"Heard: {command}")

            subprocess.call([
                'osascript', '-e',
                'tell application "Spotify" to set sound volume to 60'
            ])

            if "exit playlist" in command.lower():
                execute_voice_command(command)
                continue

            if spotify_state["last_results"]:
                play_by_artist(command)
            else:
                execute_voice_command(command)

        except (sr.UnknownValueError, sr.RequestError):
            pass
        except (ConnectionResetError, urllib.error.URLError):
            print(" Connection issue. Retrying in 1s.")
            time.sleep(1)
        finally:
            # ─── restore Spotify ↑ ───────────────────────────
            subprocess.call([
                'osascript', '-e',
                'tell application "Spotify" to set sound volume to 100'
            ])


# Gesture thread
def gesture_worker():
    global gesture_mode
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(max_num_hands=2,
                           min_detection_confidence=0.4,
                           min_tracking_confidence=0.7)
    
    cap = None  # initialize as None
    scroll_amount = 2
    scroll_interval = 0.15
    volume_step = 5
    volume_interval = 0.5
    last_scroll_time = time.time()
    last_volume_time = time.time()
    current_gesture = None
    last_mode = None
    last_badge = ""

    while not quit_app:
        #  OFF MODE: release webcam and skip frame 
        if gesture_mode == "off":
            if cap:
                cap.release()
                cap = None
            badge_txt = "Off"
            if badge_txt != last_badge:
                set_badge(badge_txt)
                last_badge = badge_txt
            time.sleep(0.1)
            continue

        #  ON MODE: reinitialize webcam if needed
        if not cap:
            cap = cv2.VideoCapture(0)

        success, frame = cap.read()
        if not success:
            continue

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = hands.process(rgb)
        now = time.time()

        if res.multi_hand_landmarks:
            lm = res.multi_hand_landmarks[0].landmark

            if gesture_mode == "volume":
                if (current_gesture in (None, 'vol_up') and is_index_only(lm) and
                        now - last_volume_time >= volume_interval):
                    beep()
                    increase_volume()
                    current_gesture = 'vol_up'
                    last_volume_time = now

                elif (current_gesture in (None, 'vol_down') and is_index_and_middle(lm) and
                        now - last_volume_time >= volume_interval):
                    beep()
                    decrease_volume()
                    current_gesture = 'vol_down'
                    last_volume_time = now

                elif current_gesture in ('vol_up', 'vol_down') and not (is_index_only(lm) or is_index_and_middle(lm)):
                    current_gesture = None

            elif gesture_mode == "scrolling":
                if (current_gesture in (None, 'scroll_down') and is_index_only(lm) and
                        now - last_scroll_time >= scroll_interval):
                    pyautogui.scroll(-scroll_amount)
                    current_gesture = 'scroll_down'
                    last_scroll_time = now

                elif (current_gesture in (None, 'scroll_up') and is_index_and_middle(lm) and
                        now - last_scroll_time >= scroll_interval):
                    pyautogui.scroll(scroll_amount)
                    current_gesture = 'scroll_up'
                    last_scroll_time = now

                elif current_gesture in ('scroll_down', 'scroll_up') and not (is_index_only(lm) or is_index_and_middle(lm)):
                    current_gesture = None

            elif gesture_mode == "brightness":
                if (current_gesture in (None, 'bright_up') and is_index_only(lm) and
                        now - last_volume_time >= volume_interval):
                    beep()
                    increase_brightness()
                    current_gesture = 'bright_up'
                    last_volume_time = now

                elif (current_gesture in (None, 'bright_down') and is_index_and_middle(lm) and
                        now - last_volume_time >= volume_interval):
                    beep()
                    decrease_brightness()
                    current_gesture = 'bright_down'
                    last_volume_time = now

                elif current_gesture in ('bright_up', 'bright_down') and not (is_index_only(lm) or is_index_and_middle(lm)):
                    current_gesture = None

        # Mode switch sound
        if gesture_mode != last_mode:
            ding()
            last_mode = gesture_mode

        # Badge update
        badge_txt = "Vol" if gesture_mode == "volume" else "Scroll" if gesture_mode == "scrolling" else "Bright" if gesture_mode == "brightness" else""
        if badge_txt != last_badge:
            set_badge(badge_txt)
            last_badge = badge_txt

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    if cap:
        cap.release()
    cv2.destroyAllWindows()

# Main
if __name__ == "__main__":
    threading.Thread(target=voice_command_listener, daemon=True).start()
    threading.Thread(target=gesture_worker, daemon=True).start()
    app.run()