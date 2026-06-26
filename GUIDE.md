# AI Fitness Trainer

A real-time AI-powered fitness form checker web application that analyzes your exercise form using computer vision and provides instant feedback via webcam.

## Features

- **Real-time Pose Detection**: Uses MediaPipe for accurate body pose estimation
- **Exercise Form Analysis**: Currently supports squat form analysis with rule-based feedback
- **WebSocket Communication**: Low-latency real-time feedback between frontend and backend
- **Multiple Exercise Pages**: Dedicated pages for different workout types (calisthenics, cardio, strength, etc.)
- **Responsive Web Interface**: Modern UI with live video feed and feedback display
- **FastAPI Backend**: High-performance Python backend with automatic API documentation

## Prerequisites

- Python 3.8 or higher
- Webcam (for pose detection)
- Modern web browser with WebRTC support

## Installation

### 1. Clone or Download the Project

Ensure you have the project files in a directory (e.g., `Anshuls_pro`).

### 2. Set Up Python Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
# source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install all required packages including:
- FastAPI (web framework)
- MediaPipe (pose detection)
- OpenCV (computer vision)
- Uvicorn (ASGI server)
- And other dependencies

## Running the Application

### Start the Server

```bash
python backend/main.py
```

You should see output like:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [XXXX] using StatReload
INFO:     Started server process [XXXX]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Access the Application

Open your web browser and navigate to:
- **Main Application**: http://localhost:8000
- **AI Feedback Page**: http://localhost:8000/ai-feedback
- **Workout Plan**: http://localhost:8000/ai-workout-plan
- **Calisthenics**: http://localhost:8000/calisthenics
- **Cardio**: http://localhost:8000/cardio
- **Strength Training**: http://localhost:8000/strength
- **Yoga & Flexibility**: http://localhost:8000/yoga-flex
- **Recovery**: http://localhost:8000/recovery
- **Combat Sports**: http://localhost:8000/combat
- **Cycling**: http://localhost:8000/cycling
- **Account**: http://localhost:8000/account

## Usage

1. **Grant Camera Permission**: When you first visit the site, allow camera access
2. **Start Session**: Click the "START SESSION" button
3. **Position Yourself**: Stand in front of the camera with your full body visible
4. **Perform Exercise**: Do squats (or other exercises on respective pages)
5. **Get Feedback**: Real-time feedback appears on the right panel
6. **View Angles**: Joint angles are displayed and updated live
7. **Stop Session**: Click "STOP" when finished

## Current Status

⚠️ **Note**: The AI pose detection is currently disabled and showing dummy feedback ("AI temporarily disabled — please check back later"). This is due to MediaPipe API changes in version 0.10.x. The application structure is complete and ready for pose detection integration.

## Project Structure

```
Anshuls_pro/
│
├── backend/
│   ├── main.py              # FastAPI application with WebSocket endpoints
│
├── frontend/
│   ├── index.html           # Main application page
│   ├── ai_feedback.html     # AI feedback interface
│   ├── ai_form.html         # Form analysis page
│   ├── ai_workout_plan.html # Workout planning
│   ├── calisthenics.html    # Bodyweight exercises
│   ├── cardio.html          # Cardiovascular training
│   ├── combat.html          # Martial arts/combat
│   ├── cycling.html         # Cycling workouts
│   ├── recovery.html        # Recovery and mobility
│   ├── strength.html        # Weight training
│   ├── yoga_flex.html       # Yoga and flexibility
│   ├── account.html         # User account page
│   ├── loin_ai.html         # Additional AI features
│   ├── app.js               # Frontend JavaScript logic
│   └── style.css            # Application styling
│
├── requirements.txt         # Python dependencies
├── README.md               # This file
└── .venv/                  # Virtual environment (created during setup)
```

## API Endpoints

### WebSocket
- `ws://localhost:8000/ws/pose` - Real-time pose analysis

### HTTP Routes
- `GET /` - Main application
- `GET /ai-feedback` - AI feedback page
- `GET /ai-form` - Form analysis
- `GET /ai-workout-plan` - Workout planning
- `GET /calisthenics` - Calisthenics page
- `GET /cardio` - Cardio page
- `GET /combat` - Combat page
- `GET /cycling` - Cycling page
- `GET /recovery` - Recovery page
- `GET /strength` - Strength page
- `GET /yoga-flex` - Yoga page
- `GET /account` - Account page
- `GET /loin-ai` - AI features page

## Troubleshooting

### Server Won't Start
- Ensure you're in the correct directory
- Check that virtual environment is activated
- Verify all dependencies are installed: `pip list`
- Check Python version: `python --version`

### Camera Not Working
- Ensure browser has camera permissions
- Try refreshing the page
- Check if another application is using the camera
- Use HTTPS in production (browsers require secure context for camera access)

### WebSocket Connection Failed
- Verify server is running on port 8000
- Check firewall settings
- Ensure no proxy is interfering

### MediaPipe Issues
- Current version has API compatibility issues
- For full functionality, consider downgrading MediaPipe or updating the pose detection code
- The application works with dummy feedback for demonstration

### Port Already in Use
- Kill existing processes: `netstat -ano | findstr :8000`
- Or change port in `backend/main.py`: `port=8001`

## Development

### Adding New Exercises
1. Create new HTML file in `frontend/`
2. Add route in `backend/main.py`
3. Implement exercise-specific feedback rules in `analyze_squat()` function
4. Update frontend JavaScript if needed

### Improving AI Feedback
- Integrate LLM APIs for personalized feedback
- Add more pose landmarks analysis
- Implement exercise recognition beyond squats

### Performance Optimization
- Reduce WebSocket message frequency
- Optimize image compression
- Implement frame rate limiting

## Technologies Used

- **Backend**: FastAPI, Python, WebSockets
- **Frontend**: HTML5, CSS3, JavaScript, WebRTC
- **AI/ML**: MediaPipe Pose Detection
- **Computer Vision**: OpenCV
- **Real-time Communication**: WebSockets

## License

This project is for educational and personal use.

## Contributing

Feel free to submit issues and enhancement requests!