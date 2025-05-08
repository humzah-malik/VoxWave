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
#from rumps import mainthread

# Sounds
def ding():
    subprocess.Popen(['afplay', '/System/Library/Sounds/Glass.aiff'])

def beep():
    subprocess.Popen(['afplay', '/System/Library/Sounds/Pop.aiff'])

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
    elif "spotify" in cmd:
        if "play" in cmd or "pause" in cmd:
            os.system("osascript -e 'tell application \"Spotify\" to playpause'")
        elif "next" in cmd and "track" in cmd:
            os.system("osascript -e 'tell application \"Spotify\" to next track'")
        elif "previous" in cmd and "track" in cmd:
            os.system("osascript -e 'tell application \"Spotify\" to previous track'")
            time.sleep(0.1)
            os.system("osascript -e 'tell application \"Spotify\" to previous track'")
    elif "chrome" in cmd and ("play" in cmd or "pause" in cmd):
        os.system('osascript -e \'tell application "Google Chrome" to activate\'')
        os.system('osascript -e \'tell application "System Events" to keystroke " " \'')
    elif "mute" in cmd:
        os.system("osascript -e 'set volume output muted true'")
    elif "unmute" in cmd:
        os.system("osascript -e 'set volume output muted false'")

def voice_command_listener():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
    print("🔊 Voice assistant ready")
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
    cap = cv2.VideoCapture(0)

    # Config
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
        success, frame = cap.read()
        if not success:
            break
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
                    os.system(f"osascript -e 'set volume output volume "
                              f"(output volume of (get volume settings) + {volume_step})'")
                    current_gesture = 'vol_up'
                    last_volume_time = now

                elif (current_gesture in (None, 'vol_down') and is_index_and_middle(lm) and
                        now - last_volume_time >= volume_interval):
                    beep()
                    os.system(f"osascript -e 'set volume output volume "
                              f"(output volume of (get volume settings) - {volume_step})'")
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

        # Mode switch sound
        if gesture_mode != last_mode:
            ding()
            last_mode = gesture_mode

        # Badge update
        badge_txt = "Vol" if gesture_mode == "volume" else "Scroll" if gesture_mode == "scrolling" else ""
        if badge_txt != last_badge:
            set_badge(badge_txt)
            last_badge = badge_txt

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

# Main
if __name__ == "__main__":
    threading.Thread(target=voice_command_listener, daemon=True).start()
    threading.Thread(target=gesture_worker, daemon=True).start()
    app.run()  # keeps the rumps badge running on main thread