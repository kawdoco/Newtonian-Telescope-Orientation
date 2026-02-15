# Setup Guide - Newtonian Telescope Simulator

## ⚠️ SECURITY: Remove Exposed API Key

Your OpenAI API key has been exposed in the repository. You MUST:

1. **Revoke the compromised key immediately:**
   - Go to: https://platform.openai.com/api-keys
   - Delete the key: `sk-proj-GD67GU0-...` (starts with the one exposed)
   - Create a NEW API key

2. **Never commit API keys again!**
   - Use `.env` files (never commit)
   - Use `.env.example` for templates
   - Check `.gitignore` includes `.env` and `key.env`

3. **Clean Git history** (if needed):
   ```bash
   # Remove the exposed key from git history
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch key.env" \
     --prune-empty --tag-name-filter cat -- --all
   
   git push -f origin main
   ```

## Installation

### 1. Create Environment Variables

**Option A: Using .env file (Recommended)**
```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your OpenAI API key
# (Don't commit this file!)
```

**Option B: Set System Environment Variable**
```powershell
# Windows PowerShell
$env:OPENAI_API_KEY = "your-api-key-here"

# Or set permanently (Admin PowerShell):
[Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "your-api-key-here", "User")
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

If `pyaudio` installation fails on Windows, use:
```bash
pip install pipwin
pipwin install pyaudio
```

### 3. Download Skyfield Data (first run only)

The skyfield library needs to download ephemeris data on first use (~150MB):
```bash
python -c "from skyfield.api import load; load('de421.bsp')"
```

### 4. Run the Application

```bash
python main.py
```

**Login credentials:**
- Username: `telescope`
- Password: `6789`

## Voice Commands

### Preset Locations
- "Polaris" / "North Star"
- "Zenith" / "Straight up"
- "Horizon North/East/South/West"

### Celestial Objects (Real-time positions)
- "Moon"
- "Sun"
- "Mars"
- "Jupiter"
- "Saturn"
- "Venus"
- "Mercury"
- "Uranus"
- "Neptune"

### Manual Controls
- "Azimuth 120 elevation 45"
- "Altitude 30"

## Troubleshooting

### Microphone not detected
```bash
# Test microphone
python -c "import speech_recognition as sr; sr.Microphone()"
```

### Skyfield download timeout
```bash
# Download manually
python -c "from skyfield.api import load; load('de421.bsp')"
```

### API Key not found
- Check `OPENAI_API_KEY` is set
- Restart terminal after setting environment variable
- Verify with: `echo $env:OPENAI_API_KEY` (PowerShell)

## File Structure

```
Newtonian-Telescope-Orientation/
├── main.py              # Main application
├── ai.py                # Voice & AI controls
├── loging.py            # Login window
├── requirements.txt     # Python dependencies
├── .env.example         # Template for environment variables
├── .env                 # (Local only, not committed)
├── .gitignore          # Git ignore rules
└── Image/              # UI images
```

## Security Checklist

- ✅ API key removed from code
- ✅ `.env` in `.gitignore`
- ✅ Use `OPENAI_API_KEY` environment variable
- ✅ `.env.example` provided as template
- ✅ Never commit `key.env` or `.env` files

