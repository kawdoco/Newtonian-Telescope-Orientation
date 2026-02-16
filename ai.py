import speech_recognition as sr
import os
import re
import pyttsx3
from datetime import datetime
from openai import OpenAI
from skyfield.api import load, wgs84
import threading


_engine = None
_speech_lock = threading.Lock()

ASSISTANT_NAME = "skysy"
WAKE_WORD_REQUIRED = True

def _init_engine():
    global _engine
    try:
        if _engine is None:
            _engine = pyttsx3.init("sapi5")
            _voices = _engine.getProperty("voices")
            if _voices and len(_voices) > 1:
                _engine.setProperty("voice", _voices[1].id)
            _engine.setProperty("rate", 170)
    except Exception as e:
        print(f"Speech engine initialization error: {e}")
        _engine = None

_init_engine()


def speech(audio: str) -> None:
    def _speak():
        global _engine
        with _speech_lock:
            try:
                if _engine is None:
                    _init_engine()
                if _engine is not None:
                    _engine.say(audio)
                    _engine.runAndWait()
                else:
                    print(f"[Speech disabled] {audio}")
            except Exception as e:
                print(f"Speech error: {e}")
                print(f"[Speech fallback] {audio}")
    
    thread = threading.Thread(target=_speak, daemon=True)
    thread.start()


def _strip_wake_word(command: str) -> tuple[bool, str]:
    pattern = rf"\b(?:hey\s+)?{re.escape(ASSISTANT_NAME)}\b[,\s]*"
    if re.search(pattern, command, flags=re.IGNORECASE):
        cleaned = re.sub(pattern, "", command, count=1, flags=re.IGNORECASE).strip()
        return True, cleaned
    return False, command


try:
    
    SKYFIELD_AVAILABLE = True
except ImportError:
    SKYFIELD_AVAILABLE = False

api_key = os.environ.get("OPEN_API_KEY", "OPEN_API_KEY")
client = OpenAI(api_key=api_key) if api_key != "OPEN_API_KEY" else None

# Check if AI is available
if client:
    print("✓ OpenAI connection established - AI agent available")
else:
    print("⚠ OpenAI API key not found - AI agent disabled (using keyword matching only)")


def ask_ai(question):
    if client is None:
        print("AI agent not available (no API key)")
        return None
    
    #print(f"Consulting AI agent to interpret: '{question}'")
    speech("Consulting AI assistant")
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", 
            messages=[
                {"role": "system", "content": "You are a telescope control assistant. Extract the celestial object name from the user's command. Supported objects: sun, moon, mercury, venus, mars, jupiter, saturn, uranus, neptune. Reply with ONLY the object name or 'unknown' if not recognized. Examples: 'show me mars' -> 'mars', 'track the red planet' -> 'mars', 'point to jupiter' -> 'jupiter'."},
                {"role": "user", "content": question}
            ],
            max_tokens=20,
            temperature=0.3
        )
        result = response.choices[0].message.content.strip().lower()
        print(f"AI agent identified: '{result}'")
        return result
    except Exception as e:
        #print(f"❌ AI Error: {str(e)}")
        speech("AI assistant unavailable")
        return None


def get_celestial_coordinates(object_name, latitude, longitude):
    if not SKYFIELD_AVAILABLE:
        return None
    
    try:
        ts = load.timescale()
        eph = load('de421.bsp')  # Planetary ephemeris
        
        t = ts.now()
        
        observer = wgs84.latlon(latitude, longitude)
        
        object_name = object_name.lower().strip()
        
        celestial_objects = {
            'sun': eph['sun'],
            'moon': eph['moon'],
            'mercury': eph['mercury'],
            'venus': eph['venus'],
            'mars': eph['mars'],
            'jupiter': eph['jupiter barycenter'],
            'saturn': eph['saturn barycenter'],
            'uranus': eph['uranus barycenter'],
            'neptune': eph['neptune barycenter'],
        }
        
        if object_name not in celestial_objects:
            print(f"Object '{object_name}' not recognized")
            return None
        
        earth = eph['earth']
        target = celestial_objects[object_name]
        
        astrometric = (earth + observer).at(t).observe(target)
        alt, az, distance = astrometric.apparent().altaz()
        
        azimuth = az.degrees
        elevation = alt.degrees
        
        print(f"{object_name.title()}: Az={azimuth:.2f}°, El={elevation:.2f}°")
        
        if elevation < 0:
            print(f"Warning: {object_name.title()} is below horizon")
            print(f"Rotating telescope to position - will be visible when it rises")
            speech(f"Tracking {object_name}. Warning: Currently below horizon at elevation {elevation:.1f} degrees")
        else:
            speech(f"Tracking {object_name}. Azimuth {azimuth:.1f} degrees, elevation {elevation:.1f} degrees")
        
        return (azimuth, elevation)
        
    except Exception as e:
        print(f"Error calculating coordinates for {object_name}: {str(e)}")
        return None


def takeCommand():
    r = sr.Recognizer()
    
    try:
        with sr.Microphone() as source:
            print("Listening...")
            r.pause_threshold = 1
            r.energy_threshold = 300
            r.adjust_for_ambient_noise(source, duration=0.5)
            
            try:
                audio = r.listen(source, timeout=5, phrase_time_limit=10)
            except sr.WaitTimeoutError:
                print("No speech detected...")
                speech("No speech detected. Please try again.")
                return "None"
        
        print("Processing...")
        query = r.recognize_google(audio, language='en-in')
        print(f"You Said: {query}")

        woke, cleaned = _strip_wake_word(query)
        if WAKE_WORD_REQUIRED and not woke:
            speech(f"Say {ASSISTANT_NAME} to wake me up")
            return "None"

        if woke and not cleaned:
            speech("Yes?")
            return "None"

        speech(f"Processing command: {cleaned}")
        return cleaned
        
    except sr.UnknownValueError:
        print("Could not understand audio")
        speech("Could not understand audio")
        return "None"
    except sr.RequestError as e:
        print(f"Could not request results; {e}")
        speech("Could not request results from speech recognition service")
        return "None"
    except OSError as e:
        print(f"Microphone error: {e}")
        speech("Microphone error detected")
        return "None"
    except Exception as e:
        print(f"Error: {str(e)}")
        speech("An error occurred while processing your command")
        return "None"


def parse_telescope_command(command, latitude=0.0, longitude=0.0):
    command = command.lower()
    
    # Preset commands
    presets = {
        "polaris": (0, 45),
        "north star": (0, 45),
        "zenith": (0, 90),
        "straight up": (0, 90),
        "horizon north": (0, 0),
        "horizon east": (90, 0),
        "horizon south": (180, 0),
        "horizon west": (270, 0),
    }
    
    for key, (az, el) in presets.items():
        if key in command:
            speech(f"Moving to {key}")
            return ("preset", az, el, key)

    az_match = re.search(r'azimuth\s+(\d+)', command)
    el_match = re.search(r'elevation\s+(\d+)', command)
    
    if az_match or el_match:
        az = int(az_match.group(1)) if az_match else None
        el = int(el_match.group(1)) if el_match else None
        return ("manual", az, el, None)
    
    celestial_keywords = ['moon', 'sun', 'mars', 'jupiter', 'saturn', 'venus', 'mercury', 'uranus', 'neptune']
    
    for keyword in celestial_keywords:
        if keyword in command:
            print(f"Direct match found: {keyword}")
            coords = get_celestial_coordinates(keyword, latitude, longitude)
            if coords:
                return ("celestial", coords[0], coords[1], keyword)
            return (None, None, None, None)
    
    if client:
        print("No direct match - using AI agent for interpretation...")
        ai_object = ask_ai(command)
        if ai_object and ai_object != 'unknown':
            print(f"AI agent successfully interpreted command as: {ai_object}")
            coords = get_celestial_coordinates(ai_object, latitude, longitude)
            if coords:
                return ("celestial", coords[0], coords[1], ai_object)
        else:
            print("AI agent could not interpret command")
    else:
        print("AI agent not available - command not recognized")
    
    return (None, None, None, None)