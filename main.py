import cv2
import mediapipe as mp
import pyautogui
import time
import os

# === Setup ===
mp_hands = mp.solutions.hands
hands    = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)
mp_draw  = mp.solutions.drawing_utils
cap      = cv2.VideoCapture(0)

# === Config ===
scroll_amount    = 2
scroll_interval  = 0.15
last_scroll_time = time.time()

volume_step      = 5
volume_interval  = 0.5
last_volume_time = time.time()

# === State ===
current_gesture = None  # 'vol_up', 'vol_down', 'scroll_up', 'scroll_down'

# === Finger‐pose helpers ===
def is_finger_up(lm, tip, pip):
    return lm[tip].y < lm[pip].y

def is_thumb_only(lm):
    # Thumb extended horizontally, all other fingers down
    thumb_ext   = abs(lm[4].x - lm[3].x) > 0.04
    others_down = all(
        not is_finger_up(lm, tip, pip)
        for tip, pip in [(8,6), (12,10), (16,14), (20,18)]
    )
    return thumb_ext and others_down

def is_pinky_only(lm):
    # Pinky up, thumb NOT extended, and index/middle/ring down
    pinky_up     = is_finger_up(lm, 20, 18)
    thumb_not_ext = abs(lm[4].x - lm[3].x) < 0.04
    others_down  = all(
        not is_finger_up(lm, tip, pip)
        for tip, pip in [(8,6), (12,10), (16,14)]
    )
    return pinky_up and thumb_not_ext and others_down

def is_index_only(lm):
    # Index up, middle/ring/pinky down
    return is_finger_up(lm, 8, 6) and not any(
        is_finger_up(lm, tip, pip)
        for tip, pip in [(12,10), (16,14), (20,18)]
    )

def is_index_and_middle(lm):
    return is_finger_up(lm, 8, 6) and is_finger_up(lm, 12, 10)

# === Gesture processors ===
def process_volume(lm, now):
    global current_gesture, last_volume_time

    # Volume UP: thumb only
    if (current_gesture in (None, 'vol_up')
        and is_thumb_only(lm)
        and now - last_volume_time >= volume_interval):
        os.system(
            f"osascript -e 'set volume output volume (output volume of (get volume settings) + {volume_step})'"
        )
        last_volume_time = now
        current_gesture  = 'vol_up'
        return 'Volume UP'

    # Volume DOWN: pinky only
    if (current_gesture in (None, 'vol_down')
        and is_pinky_only(lm)
        and now - last_volume_time >= volume_interval):
        os.system(
            f"osascript -e 'set volume output volume (output volume of (get volume settings) - {volume_step})'"
        )
        last_volume_time = now
        current_gesture  = 'vol_down'
        return 'Volume DOWN'

    # Reset when neither thumb‐only nor pinky‐only is held
    if current_gesture in ('vol_up','vol_down') and not (is_thumb_only(lm) or is_pinky_only(lm)):
        current_gesture = None

    return None

def process_scroll(lm, now):
    global current_gesture, last_scroll_time

    # Scroll DOWN: index only
    if (current_gesture in (None, 'scroll_down')
        and is_index_only(lm)
        and now - last_scroll_time >= scroll_interval):
        pyautogui.scroll(-scroll_amount)
        last_scroll_time = now
        current_gesture  = 'scroll_down'
        return 'Scrolling Down'

    # Scroll UP: index + middle
    if (current_gesture in (None, 'scroll_up')
        and is_index_and_middle(lm)
        and now - last_scroll_time >= scroll_interval):
        pyautogui.scroll(scroll_amount)
        last_scroll_time = now
        current_gesture  = 'scroll_up'
        return 'Scrolling Up'

    # Reset when neither scroll gesture is held
    if current_gesture in ('scroll_down','scroll_up') and not (is_index_only(lm) or is_index_and_middle(lm)):
        current_gesture = None

    return None

# === Main Loop ===
while True:
    success, frame = cap.read()
    if not success:
        break

    frame = cv2.flip(frame, 1)
    rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    res   = hands.process(rgb)
    now   = time.time()
    status_text = "No Hand Detected"

    if res.multi_hand_landmarks:
        lm = res.multi_hand_landmarks[0].landmark
        mp_draw.draw_landmarks(frame, res.multi_hand_landmarks[0], mp_hands.HAND_CONNECTIONS)

        # Volume first, then scroll
        status = process_volume(lm, now)
        if status:
            status_text = status
        else:
            status_text = process_scroll(lm, now) or "No Gesture"

    # Draw status
    color = (0,255,0) if status_text not in ("No Hand Detected","No Gesture") else (150,150,150)
    cv2.putText(frame, status_text, (10,50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

    cv2.imshow("Gesture Controller", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()