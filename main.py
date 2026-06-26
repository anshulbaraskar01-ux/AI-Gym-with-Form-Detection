"""
AI Fitness Form Checker - FastAPI Backend
=========================================
Receives webcam frames, runs MediaPipe pose detection,
calculates joint angles, applies feedback rules, and
returns annotated results to the frontend.
"""

import cv2
import numpy as np
import mediapipe as mp
import base64
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import os

# ─── App Setup ────────────────────────────────────────────────────────────────
app = FastAPI(title="AI Fitness Form Checker", version="1.0.0")

# Allow frontend to connect (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the frontend static files
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# ─── MediaPipe Setup ──────────────────────────────────────────────────────────
# Temporarily disabled due to API changes in mediapipe 0.10
# Will use dummy feedback for now


# ─── Angle Calculation ────────────────────────────────────────────────────────

def calculate_angle(a: list, b: list, c: list) -> float:
    """
    Calculate the angle at point B formed by rays B→A and B→C.
    
    Args:
        a: [x, y] of the first point  (e.g. hip)
        b: [x, y] of the vertex point (e.g. knee)
        c: [x, y] of the third point  (e.g. ankle)
    
    Returns:
        Angle in degrees (0–180)
    """
    a, b, c = np.array(a), np.array(b), np.array(c)

    # Vectors from vertex B
    ba = a - b
    bc = c - b

    # Dot product formula: cos θ = (ba · bc) / (|ba| * |bc|)
    cosine_angle = np.dot(ba, bc) / (
        np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6  # avoid div-by-zero
    )
    cosine_angle = np.clip(cosine_angle, -1.0, 1.0)      # clamp for arccos
    angle = np.degrees(np.arccos(cosine_angle))
    return round(angle, 1)


def get_landmark_coords(landmarks, idx: int, w: int, h: int) -> list:
    """Return [x_pixel, y_pixel] for a given landmark index."""
    lm = landmarks[idx]
    return [int(lm.x * w), int(lm.y * h)]


# ─── Feedback Rules ───────────────────────────────────────────────────────────

def analyze_squat(angles: dict) -> tuple[list, list]:
    """
    Rule-based feedback engine for squat form.
    
    Returns:
        feedback   – list of feedback strings shown to the user
        bad_joints – list of landmark indices to highlight in red
    """
    feedback   = []
    bad_joints = []

    knee_angle  = angles.get("knee_avg", 180)
    hip_angle   = angles.get("hip_avg", 180)
    back_angle  = angles.get("back", 180)
    ankle_angle = angles.get("ankle_avg", 180)

    # ── Knee Rules ──────────────────────────────────────────
    if knee_angle > 160:
        feedback.append("⬇️  Bend your knees more to start the squat")
        bad_joints += [25, 26]  # LEFT_KNEE, RIGHT_KNEE

    elif knee_angle < 60:
        feedback.append("⚠️  Knees bent too deep — risk of injury")
        bad_joints += [25, 26]

    elif 80 <= knee_angle <= 110:
        feedback.append("✅  Good knee bend depth!")

    # ── Back Rules ──────────────────────────────────────────
    if back_angle < 150:
        feedback.append("🔴  Keep your back straight — you're leaning too far forward")
        bad_joints += [11, 12, 23, 24]  # shoulders and hips
    elif back_angle > 170:
        feedback.append("✅  Back posture looks great!")

    # ── Hip Rules ───────────────────────────────────────────
    if hip_angle > 160 and knee_angle < 130:
        feedback.append("📐  Push your hips back more (sit back, not just down)")
        bad_joints += [23, 24]

    # ── Ankle Rules ─────────────────────────────────────────
    if ankle_angle < 60:
        feedback.append("👟  Keep your heels on the ground")
        bad_joints += [27, 28]

    # Default message when standing
    if knee_angle > 155 and not feedback:
        feedback.append("🧍  Stand straight and begin your squat")

    return feedback, list(set(bad_joints))  # deduplicate joints


# ─── Frame Processing ─────────────────────────────────────────────────────────

def process_frame(image_bytes: bytes) -> dict:
    """
    Dummy pipeline: decode → return with dummy feedback.
    TODO: Integrate MediaPipe pose detection.
    """
    # 1. Decode JPEG bytes → OpenCV image
    np_arr = np.frombuffer(image_bytes, np.uint8)
    frame  = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if frame is None:
        return {"error": "Could not decode image"}

    h, w, _ = frame.shape

    # 2. Run MediaPipe Pose (disabled)
    # mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
    # results = pose_landmarker.detect(mp_image)

    if not results.pose_landmarks:
        # No pose detected
        feedback = ["No pose detected — stand in frame"]
        angles = {}
        bad_joints = []
    else:
        # 3. Extract landmark coordinates
        landmarks = results.pose_landmarks[0]  # first pose

        # Key points for squat analysis (indices from MediaPipe)
        left_hip   = get_landmark_coords(landmarks, 23, w, h)  # LEFT_HIP
        right_hip  = get_landmark_coords(landmarks, 24, w, h)  # RIGHT_HIP
        left_knee  = get_landmark_coords(landmarks, 25, w, h)  # LEFT_KNEE
        right_knee = get_landmark_coords(landmarks, 26, w, h)  # RIGHT_KNEE
        left_ankle = get_landmark_coords(landmarks, 27, w, h)  # LEFT_ANKLE
        right_ankle= get_landmark_coords(landmarks, 28, w, h)  # RIGHT_ANKLE
        left_shoulder = get_landmark_coords(landmarks, 11, w, h)  # LEFT_SHOULDER
        right_shoulder= get_landmark_coords(landmarks, 12, w, h)  # RIGHT_SHOULDER

        # 4. Calculate angles
        left_knee_angle  = calculate_angle(left_hip, left_knee, left_ankle)
        right_knee_angle = calculate_angle(right_hip, right_knee, right_ankle)
        left_hip_angle   = calculate_angle(left_shoulder, left_hip, left_knee)
        right_hip_angle  = calculate_angle(right_shoulder, right_hip, right_knee)
        back_angle       = calculate_angle(left_shoulder, left_hip, right_hip)  # approx
        left_ankle_angle = calculate_angle(left_knee, left_ankle, [left_ankle[0], left_ankle[1] + 50])  # vertical
        right_ankle_angle= calculate_angle(right_knee, right_ankle, [right_ankle[0], right_ankle[1] + 50])

        angles = {
            "left_knee":  left_knee_angle,
            "right_knee": right_knee_angle,
            "left_hip":   left_hip_angle,
            "right_hip":  right_hip_angle,
            "back":       back_angle,
            "left_ankle": left_ankle_angle,
            "right_ankle":right_ankle_angle,
            "knee_avg":   (left_knee_angle + right_knee_angle) / 2,
            "hip_avg":    (left_hip_angle + right_hip_angle) / 2,
            "ankle_avg":  (left_ankle_angle + right_ankle_angle) / 2,
        }

        # 5. Generate feedback
        feedback, bad_joints = analyze_squat(angles)

        # 6. Annotate the frame (simple drawing for now)
        for i, landmark in enumerate(landmarks):
            x, y = int(landmark.x * w), int(landmark.y * h)
            cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)

    # 7. Encode back to base64
    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    img_b64 = base64.b64encode(buf).decode()

    return {
        "image":      img_b64,
        "feedback":   feedback,
        "angles":     angles,
        "bad_joints": bad_joints,
    }


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """Serve the main frontend page."""
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/ai-feedback")
async def ai_feedback():
    """Serve the AI feedback page."""
    return FileResponse(os.path.join(FRONTEND_DIR, "ai_feedback.html"))


@app.get("/ai-form")
async def ai_form():
    """Serve the AI form page."""
    return FileResponse(os.path.join(FRONTEND_DIR, "ai_form.html"))


@app.get("/ai-workout-plan")
async def ai_workout_plan():
    """Serve the AI workout plan page."""
    return FileResponse(os.path.join(FRONTEND_DIR, "ai_workout_plan.html"))


@app.get("/calisthenics")
async def calisthenics():
    """Serve the calisthenics page."""
    return FileResponse(os.path.join(FRONTEND_DIR, "calisthenics.html"))


@app.get("/cardio")
async def cardio():
    """Serve the cardio page."""
    return FileResponse(os.path.join(FRONTEND_DIR, "cardio.html"))


@app.get("/combat")
async def combat():
    """Serve the combat page."""
    return FileResponse(os.path.join(FRONTEND_DIR, "combat.html"))


@app.get("/cycling")
async def cycling():
    """Serve the cycling page."""
    return FileResponse(os.path.join(FRONTEND_DIR, "cycling.html"))


@app.get("/recovery")
async def recovery():
    """Serve the recovery page."""
    return FileResponse(os.path.join(FRONTEND_DIR, "recovery.html"))


@app.get("/strength")
async def strength():
    """Serve the strength page."""
    return FileResponse(os.path.join(FRONTEND_DIR, "strength.html"))


@app.get("/yoga-flex")
async def yoga_flex():
    """Serve the yoga flex page."""
    return FileResponse(os.path.join(FRONTEND_DIR, "yoga_flex.html"))


@app.get("/account")
async def account():
    """Serve the account page."""
    return FileResponse(os.path.join(FRONTEND_DIR, "account.html"))


@app.get("/loin-ai")
async def loin_ai():
    """Serve the loin AI page."""
    return FileResponse(os.path.join(FRONTEND_DIR, "loin_ai.html"))


@app.websocket("/ws/pose")
async def websocket_pose(ws: WebSocket):
    """
    WebSocket endpoint for real-time pose analysis.
    
    Protocol:
      Client → Server : raw JPEG bytes
      Server → Client : JSON { image, feedback, angles, bad_joints }
    """
    await ws.accept()
    print("✅ Client connected")

    try:
        while True:
            # Receive raw frame bytes from the browser
            data = await ws.receive_bytes()

            # Run the full pose pipeline
            result = process_frame(data)

            # Send JSON response back
            await ws.send_text(json.dumps(result))

    except WebSocketDisconnect:
        print("❌ Client disconnected")
    except Exception as e:
        print(f"⚠️  Error: {e}")
        await ws.close()


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,   # auto-reload on code changes during development
    )
