# 🖐️ VoxWave

A macOS desktop assistant that combines **hand gestures** and **voice commands** to control system functions, Spotify playback, and Chrome tabs.  
Built using `Python`, `MediaPipe`, `SpeechRecognition`, and `rumps`.  

This is an experimental personal project designed to explore multimodal control on macOS.

---

## 🚀 Features

- Hand gestures detected via webcam (MediaPipe) to control:
  - System **volume**
  - **Scrolling** in active app
  - Screen **brightness**
- Voice control for:
  - Activating gesture modes
  - Spotify music playback (global or within playlist)
  - Chrome tab control (next tab, close tab, new tab, etc.)
- Menubar badge to show current gesture mode
- macOS system sounds + voice feedback
- Robust fallback handling and disambiguation for Spotify track/artist matching

---

## 💻 Tech Stack
- Python 3.9+
- OpenCV
- MediaPipe
- SpeechRecognition (Google Speech API)
- rumps (menubar app framework)
- pyautogui (for scroll simulation)
- spotipy (Spotify Web API client)

---

## 📝 Installation

## Clone the repository
git clone https://github.com/humzah-malik/macGesture.git
cd hand-gesture-voice-assistant

## Set up virtual environment
python3 -m venv venv
source venv/bin/activate

## Install dependencies
pip install -r requirements.txt

## Usage Instructions
Gesture Modes

Use the voice command to activate a mode:
"scrolling" -> scrolling mode; 
"volume" -> volume mode; 
"brightness" -> brightness mode; 
"off" -> stop webcam tracking

In each mode, perform gestures:
Index finger up -> Volume up / Scroll down / Brightness up; 
Index + middle finger up -> Volume down / Scroll up / Brightness down

## Voice Commands
General
"quit/exit (app)" -> fully close the app; 
"off" -> stop camera tracking but keeps assistant active

## Spotify Commands
You can fully control Spotify by voice.The app connects via your logged-in Spotify account using Spotipy.

Global Play Commands (search entire Spotify library):
- "Spotify play [track]" -> Play any song globally by track name.
- "play [track by artist]" -> Play a specific song by both title and artist.
- After “Spotify play [track]” → multiple results → "[artist]" -> If multiple versions exist, say “[artist name]”.

Playlist Mode (play from your personal playlists):
- "Spotify playlist [playlist name]" -> Enter playlist mode.
- "[track name]" -> Play a track from the selected playlist by name.
- "exit playlist" -> Exit playlist mode back to global search

Spotify Playback Controls (always available):
- "pause Spotify" -> Pause Spotify playback
- "resume Spotify" -> Resume Spotify playback
- "next Spotify" -> Play next track
- "previous Spotify" -> Play previous track

Notes for Spotify:
Notes:
- Commands are case-insensitive.
- Voice feedback is provided if disambiguation is needed.
- Spotify must be open and playing once for device detection.

## Chrome Commands
- "Chrome play" / "Chrome pause" -> play/pause YouTube or Spotify Web
- "Chrome new tab" -> open new tab
- "Chrome close tab" -> close current tab
- "Chrome next tab" / "Chrome previous tab" -> switch tabs

## Future Improvements (Wishlist)
- Add customizable gesture recognition
- Support for Safari + other apps
- Improve Spotify error handling + offline mode
- macOS app bundling for easy distribution
- GUI settings panel
- Add whisper / LLM offline speech model support