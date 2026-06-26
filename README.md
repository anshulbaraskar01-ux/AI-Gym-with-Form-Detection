# AI Fitness Trainer

A real-time AI-powered fitness form checker web application.

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the server:**
   ```bash
   python backend/main.py
   ```

3. **Open in browser:**
   - Main app: http://localhost:8000

## Full Documentation

See [GUIDE.md](GUIDE.md) for complete setup instructions, usage guide, and troubleshooting.

## Features

- Real-time pose detection and form analysis
- Multiple exercise types supported
- WebSocket-based real-time feedback
- Modern responsive web interface

## Current Status

⚠️ AI pose detection is temporarily disabled (showing dummy feedback). See GUIDE.md for details.
│   └── requirements.txt   ← Python dependencies
│
└── frontend/
    ├── index.html          ← Main UI (served by FastAPI)
    ├── css/
    │   └── style.css       ← Industrial dark theme
    └── js/
        └── app.js          ← WebSocket client + camera + UI
```

---

## Setup & Run

### 1 — Install Python dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2 — Start the backend server
```bash
python main.py
# OR
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 3 — Open the app
Visit **http://localhost:8000** in your browser (Chrome recommended).

Click **START SESSION** and allow camera access.

---

## How It Works

### Backend Pipeline (`main.py`)

1. **WebSocket endpoint** `/ws/pose` receives raw JPEG bytes from the browser
2. **MediaPipe Pose** detects 33 body landmarks
3. **`calculate_angle(a, b, c)`** uses the dot-product formula to find joint angles
4. **`analyze_squat(angles)`** applies rule-based thresholds:
   | Joint | Good range | Feedback |
   |-------|-----------|---------|
   | Knee  | 80–110°  | Bend more / too deep |
   | Back  | >150°    | Keep it straight |
   | Hip   | 80–140°  | Push hips back |
   | Ankle | >60°     | Keep heels down |
5. **Bad joints** are re-drawn in **red** on the annotated frame
6. JSON response sent back: `{ image, feedback, angles, bad_joints }`

### Frontend (`app.js`)

- Captures webcam frames every `1000/15` ms ≈ 15 FPS
- Encodes as JPEG via `<canvas>.toBlob()`
- Sends raw bytes over WebSocket
- Receives JSON → paints annotated image → updates feedback/angles/score

---

## Extending the App

### Add a new exercise (e.g. Push-up)
```python
def analyze_pushup(angles: dict) -> tuple[list, list]:
    feedback, bad_joints = [], []
    elbow_angle = angles.get("left_elbow", 180)
    
    if elbow_angle > 160:
        feedback.append("⬇️  Lower your body — bend your elbows")
        bad_joints += [LANDMARKS.LEFT_ELBOW.value, LANDMARKS.RIGHT_ELBOW.value]
    elif elbow_angle < 80:
        feedback.append("⬆️  Push back up")
    elif 85 <= elbow_angle <= 110:
        feedback.append("✅  Perfect depth!")
    
    return feedback, bad_joints
```

Then call it from `process_frame()` instead of `analyze_squat()`.

### Add a rep counter
Track angle going below threshold (down phase) then above (up phase):
```python
# In state dict
rep_state = "up"   # or "down"
rep_count = 0

if knee_angle < 100 and rep_state == "up":
    rep_state = "down"
elif knee_angle > 150 and rep_state == "down":
    rep_state = "up"
    rep_count += 1
```

---

## Tips for Best Results

- Use **good lighting** (face a window or lamp)
- Your **full body** should be visible in frame
- Wear **fitted clothing** for better landmark detection
- Use **Chrome** or **Edge** for best WebRTC support

---

## Tech Stack

| Layer       | Technology              |
|-------------|-------------------------|
| Frontend    | HTML5, CSS3, Vanilla JS |
| Backend     | Python 3.10+, FastAPI   |
| Pose Model  | MediaPipe BlazePose     |
| CV          | OpenCV                  |
| Transport   | WebSocket (binary)      |
