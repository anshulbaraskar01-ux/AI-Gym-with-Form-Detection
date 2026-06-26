/**
 * FormAI — Frontend Application
 * ================================
 * Responsibilities:
 *   1. Access the user's webcam
 *   2. Capture frames at a target FPS
 *   3. Send each frame to the FastAPI WebSocket
 *   4. Receive annotated frame + feedback JSON
 *   5. Paint the annotated frame on the canvas
 *   6. Update feedback list, angle chips, score ring
 */

"use strict";

// ─── Configuration ──────────────────────────────────────────────────────────
const CONFIG = {
  WS_URL:       "ws://localhost:8000/ws/pose",
  TARGET_FPS:   15,           // Frames per second to send to backend
  JPEG_QUALITY: 0.75,         // Canvas toBlob quality (0–1)
  CANVAS_WIDTH: 640,          // Processing resolution width
  CANVAS_HEIGHT: 480,         // Processing resolution height
};

// ─── DOM References ──────────────────────────────────────────────────────────
const webcamEl      = document.getElementById("webcam");
const canvasEl      = document.getElementById("canvas");
const ctx           = canvasEl.getContext("2d");
const startBtn      = document.getElementById("startBtn");
const stopBtn       = document.getElementById("stopBtn");
const statusPill    = document.getElementById("statusPill");
const statusText    = statusPill.querySelector(".status-text");
const fpsDisplay    = document.getElementById("fpsDisplay");
const feedbackList  = document.getElementById("feedbackList");
const anglesGrid    = document.getElementById("anglesGrid");
const scoreRing     = document.getElementById("scoreRing");
const scoreNumber   = document.getElementById("scoreNumber");
const scoreLabel    = document.getElementById("scoreLabel");
const cameraOverlay = document.getElementById("cameraOverlay");

// ─── State ───────────────────────────────────────────────────────────────────
let socket      = null;   // WebSocket instance
let stream      = null;   // MediaStream from webcam
let sendLoop    = null;   // setInterval handle
let isRunning   = false;
let frameCount  = 0;
let lastFpsTime = performance.now();

// Score ring circumference (r=34 → C = 2π·34 ≈ 213.6)
const RING_CIRCUMFERENCE = 2 * Math.PI * 34;

// ─── Helpers ─────────────────────────────────────────────────────────────────

/**
 * Classify a feedback string into a CSS class for colour-coding.
 * Looks for emoji/keyword hints in the message.
 */
function classifyFeedback(text) {
  if (text.includes("✅"))  return "good";
  if (text.includes("🔴") || text.includes("⚠️")) return "error";
  if (text.includes("🔍") || text.includes("🧍")) return "idle";
  return "warn";   // ⬇️ 📐 👟 etc.
}

/** Compute a 0–100 form score from the current feedback list. */
function computeScore(feedbackItems) {
  if (!feedbackItems || feedbackItems.length === 0) return null;
  const goodCount  = feedbackItems.filter(f => f.includes("✅")).length;
  const totalRules = feedbackItems.length;
  return Math.round((goodCount / totalRules) * 100);
}

/** Update the circular score ring. */
function updateScoreRing(score) {
  if (score === null) {
    scoreNumber.textContent = "—";
    scoreLabel.textContent  = "Waiting…";
    scoreRing.style.strokeDashoffset = RING_CIRCUMFERENCE;
    scoreRing.className = "score-fill";
    return;
  }

  // Dash offset: 0 = full ring, CIRCUMFERENCE = empty ring
  const offset = RING_CIRCUMFERENCE * (1 - score / 100);
  scoreRing.style.strokeDashoffset = offset;
  scoreNumber.textContent = score;

  // Colour the ring
  scoreRing.classList.remove("good", "warn", "bad");
  if (score >= 70)      { scoreRing.classList.add("good"); scoreLabel.textContent = "Looking great!"; }
  else if (score >= 40) { scoreRing.classList.add("warn"); scoreLabel.textContent = "Needs work"; }
  else                  { scoreRing.classList.add("bad");  scoreLabel.textContent = "Poor form"; }
}

/** Update connection status pill. */
function setStatus(connected) {
  if (connected) {
    statusPill.classList.add("connected");
    statusText.textContent = "LIVE";
  } else {
    statusPill.classList.remove("connected");
    statusText.textContent = "OFFLINE";
  }
}

/** Update the feedback panel with new messages. */
function renderFeedback(messages) {
  feedbackList.innerHTML = "";

  if (!messages || messages.length === 0) {
    feedbackList.innerHTML =
      '<li class="feedback-item feedback-item--idle">No feedback yet</li>';
    return;
  }

  messages.forEach(msg => {
    const li = document.createElement("li");
    const cls = classifyFeedback(msg);
    li.className = `feedback-item feedback-item--${cls}`;
    li.textContent = msg;
    feedbackList.appendChild(li);
  });
}

/** Update angle chips from angles object. */
function renderAngles(angles) {
  const chips = anglesGrid.querySelectorAll(".angle-chip");
  chips.forEach(chip => {
    const key = chip.dataset.key;
    const val = angles[key];
    const valEl = chip.querySelector(".angle-val");
    if (val !== undefined) {
      valEl.textContent = `${Math.round(val)}°`;
    }
  });
}

/** Highlight bad-joint angle chips in red. */
function highlightBadJoints(badJoints) {
  // Map landmark indices → joint names used in angle chips
  const JOINT_MAP = {
    11: "left_shoulder", 12: "right_shoulder",
    23: "left_hip",      24: "right_hip",
    25: "left_knee",     26: "right_knee",
    27: "left_ankle",    28: "right_ankle",
    13: "left_elbow",    14: "right_elbow",
  };

  const badKeys = new Set(badJoints.map(idx => JOINT_MAP[idx]).filter(Boolean));

  anglesGrid.querySelectorAll(".angle-chip").forEach(chip => {
    if (badKeys.has(chip.dataset.key)) {
      chip.classList.add("bad");
    } else {
      chip.classList.remove("bad");
    }
  });
}

// ─── FPS Counter ─────────────────────────────────────────────────────────────

function tickFPS() {
  frameCount++;
  const now = performance.now();
  const elapsed = now - lastFpsTime;
  if (elapsed >= 1000) {
    const fps = Math.round((frameCount / elapsed) * 1000);
    fpsDisplay.textContent = fps;
    frameCount  = 0;
    lastFpsTime = now;
  }
}

// ─── Frame Capture & Send ─────────────────────────────────────────────────────

/**
 * Draw the current webcam frame onto the canvas,
 * encode it as JPEG bytes, and send over WebSocket.
 */
function captureAndSend() {
  if (!socket || socket.readyState !== WebSocket.OPEN) return;

  // Paint latest webcam frame onto offscreen canvas
  ctx.drawImage(webcamEl, 0, 0, CONFIG.CANVAS_WIDTH, CONFIG.CANVAS_HEIGHT);

  // Encode canvas to JPEG blob, then convert to ArrayBuffer and send
  canvasEl.toBlob(
    (blob) => {
      if (!blob) return;
      blob.arrayBuffer().then(buf => {
        if (socket && socket.readyState === WebSocket.OPEN) {
          socket.send(buf);
          tickFPS();
        }
      });
    },
    "image/jpeg",
    CONFIG.JPEG_QUALITY,
  );
}

// ─── WebSocket ────────────────────────────────────────────────────────────────

function connectWebSocket() {
  socket = new WebSocket(CONFIG.WS_URL);
  socket.binaryType = "arraybuffer";

  socket.addEventListener("open", () => {
    console.log("✅ WebSocket connected");
    setStatus(true);

    // Start sending frames at target FPS
    const interval = Math.round(1000 / CONFIG.TARGET_FPS);
    sendLoop = setInterval(captureAndSend, interval);
  });

  socket.addEventListener("message", (event) => {
    const data = JSON.parse(event.data);

    // 1. Paint the annotated image returned by the backend
    if (data.image) {
      const img = new Image();
      img.onload = () => {
        ctx.clearRect(0, 0, canvasEl.width, canvasEl.height);
        ctx.drawImage(img, 0, 0, canvasEl.width, canvasEl.height);
      };
      img.src = `data:image/jpeg;base64,${data.image}`;
    }

    // 2. Render feedback messages
    renderFeedback(data.feedback || []);

    // 3. Update angle chips
    renderAngles(data.angles || {});

    // 4. Highlight bad joints
    highlightBadJoints(data.bad_joints || []);

    // 5. Compute + display form score
    const score = computeScore(data.feedback);
    updateScoreRing(score);
  });

  socket.addEventListener("close", () => {
    console.log("❌ WebSocket closed");
    setStatus(false);
    if (isRunning) {
      // Attempt reconnect after 2 s if session is still active
      setTimeout(connectWebSocket, 2000);
    }
  });

  socket.addEventListener("error", (err) => {
    console.error("WebSocket error:", err);
  });
}

// ─── Session Control ─────────────────────────────────────────────────────────

async function startSession() {
  try {
    // 1. Request webcam access
    stream = await navigator.mediaDevices.getUserMedia({
      video: { width: CONFIG.CANVAS_WIDTH, height: CONFIG.CANVAS_HEIGHT },
      audio: false,
    });

    webcamEl.srcObject = stream;

    // Wait for the video to be ready
    await new Promise(resolve => { webcamEl.onloadedmetadata = resolve; });

    // Set canvas to match video dimensions
    canvasEl.width  = CONFIG.CANVAS_WIDTH;
    canvasEl.height = CONFIG.CANVAS_HEIGHT;

    // 2. Hide camera-off overlay
    cameraOverlay.classList.add("hidden");

    // 3. Connect WebSocket
    isRunning = true;
    connectWebSocket();

    // 4. Update UI
    startBtn.disabled = true;
    stopBtn.disabled  = false;

  } catch (err) {
    alert(`Could not access webcam: ${err.message}\nPlease allow camera permission.`);
    console.error(err);
  }
}

function stopSession() {
  isRunning = false;

  // Stop sending frames
  if (sendLoop) { clearInterval(sendLoop); sendLoop = null; }

  // Close WebSocket
  if (socket) { socket.close(); socket = null; }

  // Stop webcam tracks
  if (stream) {
    stream.getTracks().forEach(t => t.stop());
    stream = null;
  }

  // Show camera-off overlay
  cameraOverlay.classList.remove("hidden");

  // Reset UI
  setStatus(false);
  fpsDisplay.textContent = "—";
  renderFeedback([]);
  updateScoreRing(null);
  startBtn.disabled = false;
  stopBtn.disabled  = true;

  // Clear canvas
  ctx.clearRect(0, 0, canvasEl.width, canvasEl.height);
}

// ─── Event Listeners ─────────────────────────────────────────────────────────

startBtn.addEventListener("click", startSession);
stopBtn.addEventListener("click", stopSession);

// Stop cleanly when the tab is closed
window.addEventListener("beforeunload", stopSession);
