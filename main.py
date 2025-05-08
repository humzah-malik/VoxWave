import cv2
import mediapipe as mp
import pyautogui
import time
import os
import threading
import speech_recognition as sr

# Setup Mediapipe Hands
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=2,
                       min_detection_confidence=0.4,
                       min_tracking_confidence=0.7)
mp_draw = mp.solutions.drawing_utils
cap = cv2.VideoCapture(0)

# Config
scroll_amount = 2
scroll_interval = 0.15
volume_step = 5
volume_interval = 0.5
last_scroll_time = time.time()
last_volume_time = time.time()

# State
current_gesture = None  # e.g., 'scroll_down', 'vol_up', etc.
gesture_mode = None     # either 'scrolling', 'volume', etc.
feedback_message = ""   # printed on screen to confirm mode switch

# Finger‑pose helpers
def is_finger_up(lm, tip, pip):
    return lm[tip].y < lm[pip].y

def is_index_only(lm):
    return (is_finger_up(lm, 8, 6) and
            not is_finger_up(lm, 12, 10) and
            not is_finger_up(lm, 16, 14) and
            not is_finger_up(lm, 20, 18))

def is_index_and_middle(lm):
    return (is_finger_up(lm, 8, 6) and is_finger_up(lm, 12, 10) and
            not is_finger_up(lm, 16, 14) and not is_finger_up(lm, 20, 18))

# Volume helpers
def perform_volume_up(now):
    global last_volume_time
    os.system(f"osascript -e 'set volume output volume (output volume of (get volume settings) + {volume_step})'")
    last_volume_time = now
    return 'Volume UP'

def perform_volume_down(now):
    global last_volume_time
    os.system(f"osascript -e 'set volume output volume (output volume of (get volume settings) - {volume_step})'")
    last_volume_time = now
    return 'Volume DOWN'

def process_volume_gesture(lm, now):
    global current_gesture
    if (current_gesture in (None, 'vol_up') and is_index_only(lm) and
            now - last_volume_time >= volume_interval):
        current_gesture = 'vol_up'
        return perform_volume_up(now)
    if (current_gesture in (None, 'vol_down') and is_index_and_middle(lm) and
            now - last_volume_time >= volume_interval):
        current_gesture = 'vol_down'
        return perform_volume_down(now)
    if current_gesture in ('vol_up', 'vol_down') and not (is_index_only(lm) or is_index_and_middle(lm)):
        current_gesture = None
    return None

# Scroll helpers
def process_scroll_gesture(lm, now):
    global current_gesture, last_scroll_time
    if (current_gesture in (None, 'scroll_down') and is_index_only(lm) and
            now - last_scroll_time >= scroll_interval):
        pyautogui.scroll(-scroll_amount)
        last_scroll_time = now
        current_gesture = 'scroll_down'
        return 'Scrolling Down'
    if (current_gesture in (None, 'scroll_up') and is_index_and_middle(lm) and
            now - last_scroll_time >= scroll_interval):
        pyautogui.scroll(scroll_amount)
        last_scroll_time = now
        current_gesture = 'scroll_up'
        return 'Scrolling Up'
    if current_gesture in ('scroll_down', 'scroll_up') and not (is_index_only(lm) or is_index_and_middle(lm)):
        current_gesture = None
    return None

#  Voice command helpers 
def execute_voice_command(cmd: str):
    global gesture_mode, feedback_message
    cmd_lower = cmd.lower()

    #  Gesture mode switchers 
    if 'scrolling' in cmd_lower:
        gesture_mode = 'scrolling'
        feedback_message = "🌀 Gesture Mode: Scrolling"
        print(feedback_message)
        return
    if 'volume' in cmd_lower:
        gesture_mode = 'volume'
        feedback_message = "🔊 Gesture Mode: Volume"
        print(feedback_message)
        return

    #  Always available voice commands 
    if "spotify" in cmd_lower:
        if "play" in cmd_lower or "pause" in cmd_lower:
            os.system("osascript -e 'tell application \"Spotify\" to playpause'")
        elif "next" in cmd_lower and "track" in cmd_lower:
            os.system("osascript -e 'tell application \"Spotify\" to next track'")
        elif "previous" in cmd_lower and "track" in cmd_lower:
            os.system("osascript -e 'tell application \"Spotify\" to previous track'")
            time.sleep(0.1)
            os.system("osascript -e 'tell application \"Spotify\" to previous track'")
    elif "chrome" in cmd_lower and ("play" in cmd_lower or "pause" in cmd_lower):
        os.system('osascript -e \'tell application "Google Chrome" to activate\'')
        os.system('osascript -e \'tell application "System Events" to keystroke " " \'')
    elif "mute" in cmd_lower:
        os.system("osascript -e 'set volume output muted true'")
    elif "unmute" in cmd_lower:
        os.system("osascript -e 'set volume output muted false'")

#  Voice Listener 
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

# Start voice listener
threading.Thread(target=voice_command_listener, daemon=True).start()

#  Main Gesture Loop 
while True:
    success, frame = cap.read()
    if not success:
        break

    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    res = hands.process(rgb)
    now = time.time()
    status_text = "No Hand Detected"

    if res.multi_hand_landmarks:
        lm = res.multi_hand_landmarks[0].landmark
        mp_draw.draw_landmarks(frame, res.multi_hand_landmarks[0], mp_hands.HAND_CONNECTIONS)

        if gesture_mode == 'volume':
            status = process_volume_gesture(lm, now)
        elif gesture_mode == 'scrolling':
            status = process_scroll_gesture(lm, now)
        else:
            status = None

        status_text = status or "No Gesture"

    # Draw gesture status and mode feedback
    color = (0, 255, 0) if status_text not in ("No Hand Detected", "No Gesture") else (150, 150, 150)
    cv2.putText(frame, status_text, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

    if feedback_message:
        cv2.putText(frame, feedback_message, (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

    cv2.imshow("Gesture + Voice Controller", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()