import speech_recognition as sr
import os
import re
from datetime import datetime
from openai import OpenAI
try:
    from skyfield.api import load, wgs84
    SKYFIELD_AVAILABLE = True
except ImportError:
    SKYFIELD_AVAILABLE = False

api_key = os.environ.get("OPENAI_API_KEY", "OPEN_API_KEY")
client = OpenAI(api_key=api_key) if api_key != "OPEN_API_KEY" else None


def ask_ai(question):
    """
    OpenAI API call to help interpret celestial object commands
    """
    if client is None:
        return None
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", 
            messages=[
                {"role": "system", "content": "You are a telescope assistant. Extract the celestial object name from the user's command. Reply with ONLY the object name (moon, mars, jupiter, saturn, venus, mercury, sun, etc.) or 'unknown' if not a celestial object."},
                {"role": "user", "content": question}
            ],
            max_tokens=20,
            temperature=0.3
        )
        return response.choices[0].message.content.strip().lower()
    except Exception as e:
        print(f"AI Error: {str(e)}")
        return None


def get_celestial_coordinates(object_name, latitude, longitude):
    """
    Calculate azimuth and elevation for celestial objects
    Returns: (azimuth, elevation) in degrees or None if failed
    """
    if not SKYFIELD_AVAILABLE:
        print("Skyfield library not available. Install with: pip install skyfield")
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
        
        return (azimuth, elevation)
        
    except Exception as e:
        print(f"Error calculating coordinates for {object_name}: {str(e)}")
        return None


def takeCommand():
    """
    Voice recognition function using Google Speech Recognition
    Returns the recognized text or "None" if failed
    """
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
                return "None"
        
        print("Recognizing...")
        query = r.recognize_google(audio, language='en-in')
        print(f"You Said: {query}")
        return query
        
    except sr.UnknownValueError:
        print("Could not understand audio")
        return "None"
    except sr.RequestError as e:
        print(f"Could not request results; {e}")
        return "None"
    except OSError as e:
        print(f"Microphone error: {e}")
        return "None"
    except Exception as e:
        print(f"Error: {str(e)}")
        return "None"


def parse_telescope_command(command, latitude=0.0, longitude=0.0):
    """
    Parse voice commands for telescope control
    Returns: (command_type, azimuth, elevation) or (None, None, None)
    """
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
            return ("preset", az, el)

    az_match = re.search(r'azimuth\s+(\d+)', command)
    el_match = re.search(r'elevation\s+(\d+)', command)
    
    if az_match or el_match:
        az = int(az_match.group(1)) if az_match else None
        el = int(el_match.group(1)) if el_match else None
        return ("manual", az, el)
    
    celestial_keywords = ['moon', 'sun', 'mars', 'jupiter', 'saturn', 'venus', 'mercury', 'uranus', 'neptune']
    
    for keyword in celestial_keywords:
        if keyword in command:
            coords = get_celestial_coordinates(keyword, latitude, longitude)
            if coords:
                return ("celestial", coords[0], coords[1])
            return (None, None, None)
    
    if client:
        ai_object = ask_ai(command)
        if ai_object and ai_object != 'unknown':
            coords = get_celestial_coordinates(ai_object, latitude, longitude)
            if coords:
                return ("celestial", coords[0], coords[1])
    
    return (None, None, None)