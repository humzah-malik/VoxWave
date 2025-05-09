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

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id="f8f7d5f92d924d28b15832cc32d69557",
    client_secret="4195eeff05614d929e6881dcf1855353",
    redirect_uri="http://127.0.0.1:8888/callback",
    scope="user-read-playback-state user-modify-playback-state"
))

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

def play_track(track_name):
    devices = sp.devices().get('devices', [])
    if not devices:
        print("No active Spotify device found.")
        os.system("say 'No active Spotify device. Open Spotify and play a song.'")
        return

    results = sp.search(q=track_name, type='track', limit=1)
    tracks = results.get('tracks', {}).get('items', [])
    if tracks:
        track_uri = tracks[0]['uri']
        sp.start_playback(device_id=devices[0]['id'], uris=[track_uri])
        print(f"Playing: {tracks[0]['name']} by {tracks[0]['artists'][0]['name']}")
        os.system(f"say 'Playing {tracks[0]['name']}'")
    else:
        print("Track not found.")
        os.system("say 'Track not found on Spotify'")

# Menubar badge
app = rumps.App("✋")

def set_badge(text=""):
    app.title = text

gesture_mode = None  # shared between threads

# Finger pose helpers
def is_finger_up(lm, tip, pip):
    return lm[tip].y < lm[pip].y

def is_index_only(lm):
    return (is_finger_up(lm, 8, 6) and
            not any(is_finger_up(lm, t, p) for t, p in [(12,10), (16,14), (20,18)]))

def is_index_and_middle(lm):
    return (is_finger_up(lm, 8, 6) and is_finger_up(lm, 12, 10) and
            not any(is_finger_up(lm, t, p) for t, p in [(16,14), (20,18)]))

# Voice command logic
def execute_voice_command(cmd: str):
    global gesture_mode
    cmd = cmd.lower()

    if "scrolling" in cmd:
        gesture_mode = "scrolling"
        print("→ Mode: Scrolling")
    elif "volume" in cmd:
        gesture_mode = "volume"
        print("→ Mode: Volume")
    elif "brightness" in cmd:
        gesture_mode = "brightness"
        print("→ Mode: Brightness")
    elif "spotify" in cmd:
        if "play" in cmd:
            song = cmd.split("play", 1)[1].strip()
            if not song:
                os.system("say 'Please say the song name after play'")
                return
            play_track(song)
        elif "pause" in cmd:
            os.system("osascript -e 'tell application \"Spotify\" to pause'")
            os.system("say 'Paused'")
        elif "resume" in cmd:
            os.system("osascript -e 'tell application \"Spotify\" to play'")
            os.system("say 'Resumed'")
        elif "next" in cmd and "track" in cmd:
            os.system("osascript -e 'tell application \"Spotify\" to next track'")
            os.system("say 'Next track'")
        elif "previous" in cmd and "track" in cmd:
            os.system("osascript -e 'tell application \"Spotify\" to previous track'")
            time.sleep(0.1)
            os.system("osascript -e 'tell application \"Spotify\" to previous track'")
            os.system("say 'Previous track'")
        else:
            os.system("say 'Please say Spotify play followed by a song name'")
        
    elif "off" in cmd:
        gesture_mode = "off"
        print("→ Mode: Off")
        subprocess.Popen(["afplay", "/System/Library/Sounds/Submarine.aiff"])

def voice_command_listener():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
    print("Voice assistant ready")
    while True:
        with mic as source:
            audio = recognizer.listen(source, phrase_time_limit=3)
        try:
            command = recognizer.recognize_google(audio)
            print(f"Heard: {command}")
            execute_voice_command(command)
        except (sr.UnknownValueError, sr.RequestError):
            continue
        except (ConnectionResetError, urllib.error.URLError):
            print("⚠️ Connection issue. Retrying in 1s.")
            time.sleep(1)
            continue

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

    while True:
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
        badge_txt = "Vol" if gesture_mode == "volume" else "Scroll" if gesture_mode == "scrolling" else "Bright" if gesture_mode == "brightness" else ""
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
    app.run()  # keeps the rumps badge running on main thread