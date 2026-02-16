import cv2
import mediapipe as mp
import numpy as np
import math
import time

# ------------------ SETTINGS ------------------
FRAME_WIDTH, FRAME_HEIGHT = 1280, 720
NUM_IMAGES = 4
MAX_CYCLES = 3  # repeat 3 times
TOTAL_POINTS = NUM_IMAGES * MAX_CYCLES  # 12 points
TIMER_SEC = 120  # 2 minutes countdown

# ------------------ LOAD IMAGES ------------------
avatar_images = [
    cv2.imread("image-1-removebg-preview.png", cv2.IMREAD_UNCHANGED),
    cv2.imread("image-2-removebg-preview.png", cv2.IMREAD_UNCHANGED),
    cv2.imread("image-3-removebg-preview.png", cv2.IMREAD_UNCHANGED),
    cv2.imread("image-4-removebg-preview.png", cv2.IMREAD_UNCHANGED)
]
background = cv2.imread("backgroundstretch.png")
if background is not None:
    background = cv2.resize(background, (FRAME_WIDTH, FRAME_HEIGHT))

# ------------------ FUNCTIONS ------------------
def calculate_leg_angle(hip, knee):
    hip = np.array(hip)
    knee = np.array(knee)
    v = knee - hip
    ref = np.array([0, 1])  # vertical down
    dot = np.dot(v, ref)
    norm_v = np.linalg.norm(v)
    norm_ref = np.linalg.norm(ref)
    if norm_v == 0 or norm_ref == 0:
        return 0
    angle_rad = np.arccos(np.clip(dot / (norm_v * norm_ref), -1.0, 1.0))
    return np.degrees(angle_rad)

def calculate_support_knee_angle(hip, knee, ankle):
    hip = np.array(hip)
    knee = np.array(knee)
    ankle = np.array(ankle)
    v1 = hip - knee
    v2 = ankle - knee
    dot = np.dot(v1, v2)
    denom = np.linalg.norm(v1) * np.linalg.norm(v2)
    if denom == 0:
        return 180
    angle_rad = np.arccos(np.clip(dot / denom, -1.0, 1.0))
    angle_deg = np.degrees(angle_rad)
    return 180 - angle_deg  # straight leg = 0°

def overlay_avatar(bg, avatar):
    if avatar is None:
        return bg
    h, w = avatar.shape[:2]
    x_offset = (FRAME_WIDTH - w) // 2
    y_offset = (FRAME_HEIGHT - h) // 2
    if avatar.shape[2] == 4:
        alpha_s = avatar[:, :, 3] / 255.0
        alpha_l = 1.0 - alpha_s
        for c in range(3):
            bg[y_offset:y_offset+h, x_offset:x_offset+w, c] = (
                alpha_s * avatar[:, :, c] +
                alpha_l * bg[y_offset:y_offset+h, x_offset:x_offset+w, c]
            )
    else:
        bg[y_offset:y_offset+h, x_offset:x_offset+w] = avatar
    return bg

# ------------------ GAME STATE ------------------
score = 0
lift_stage = 0
lift_active = False
cycles_done = 0

# Resize avatars for consistency (50% screen width)
for i in range(len(avatar_images)):
    if avatar_images[i] is not None:
        scale = 0.5 * FRAME_WIDTH / avatar_images[i].shape[1]
        new_w = int(avatar_images[i].shape[1] * scale)
        new_h = int(avatar_images[i].shape[0] * scale)
        avatar_images[i] = cv2.resize(avatar_images[i], (new_w, new_h), interpolation=cv2.INTER_AREA)

# ------------------ MEDIAPIPE INIT ------------------
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
cap = cv2.VideoCapture(0)

# Fullscreen window setup
cv2.namedWindow("Stretch Game", cv2.WINDOW_NORMAL)
cv2.setWindowProperty("Stretch Game", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

start_time = time.time()

with mp_pose.Pose(min_detection_confidence=0.7, min_tracking_confidence=0.7) as pose:
    while cap.isOpened() and cycles_done < MAX_CYCLES:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(frame_rgb)

        angle_leg = 0
        angle_support = 0

        if results.pose_landmarks:
            lm = results.pose_landmarks.landmark

            hip_r = [lm[mp_pose.PoseLandmark.RIGHT_HIP.value].x, lm[mp_pose.PoseLandmark.RIGHT_HIP.value].y]
            knee_r = [lm[mp_pose.PoseLandmark.RIGHT_KNEE.value].x, lm[mp_pose.PoseLandmark.RIGHT_KNEE.value].y]
            angle_leg = calculate_leg_angle(hip_r, knee_r)

            hip_l = [lm[mp_pose.PoseLandmark.LEFT_HIP.value].x, lm[mp_pose.PoseLandmark.LEFT_HIP.value].y]
            knee_l = [lm[mp_pose.PoseLandmark.LEFT_KNEE.value].x, lm[mp_pose.PoseLandmark.LEFT_KNEE.value].y]
            ankle_l = [lm[mp_pose.PoseLandmark.LEFT_ANKLE.value].x, lm[mp_pose.PoseLandmark.LEFT_ANKLE.value].y]
            angle_support = calculate_support_knee_angle(hip_l, knee_l, ankle_l)

        # ------------------ GAME LOGIC ------------------
        if (20 <= angle_leg <= 60) and (0 <= angle_support <= 15):
            lift_active = True
        elif lift_active and (0 <= angle_leg <= 10) and (0 <= angle_support <= 15):
            if score < TOTAL_POINTS:
                score += 1
            lift_stage = score % NUM_IMAGES  # update avatar based on score
            lift_active = False
            if lift_stage == 0:
                cycles_done += 1

        # ------------------ BUILD GAME FRAME ------------------
        frame_game = background.copy() if background is not None else 255*np.ones((FRAME_HEIGHT, FRAME_WIDTH,3),dtype=np.uint8)
        frame_game = overlay_avatar(frame_game, avatar_images[lift_stage])

        # ------------------ Overlay small skeletal webcam ------------------
        small_frame = cv2.resize(frame, (320, 240))
        if results.pose_landmarks:
            mp_drawing.draw_landmarks(small_frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
        frame_game[0:240, 0:320] = small_frame

        # ------------------ Overlay Score ------------------
        cv2.rectangle(frame_game, (FRAME_WIDTH-270,10), (FRAME_WIDTH-10,60), (0,0,0), -1)
        cv2.putText(frame_game, f"Score: {score}/{TOTAL_POINTS}", (FRAME_WIDTH-260,50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0,255,255), 3)

        # ------------------ Overlay Timer ------------------
        elapsed = int(time.time() - start_time)
        remaining = max(TIMER_SEC - elapsed,0)
        mins, secs = divmod(remaining,60)
        timer_text = f"{mins:02d}:{secs:02d}"
        cv2.rectangle(frame_game, (FRAME_WIDTH//2-90,10),(FRAME_WIDTH//2+90,60),(0,0,0),-1)
        cv2.putText(frame_game, timer_text,(FRAME_WIDTH//2-70,50),
                    cv2.FONT_HERSHEY_SIMPLEX,1.2,(0,255,0),3)

        cv2.imshow("Stretch Game", frame_game)

        if remaining <= 0:
            break
        if cv2.waitKey(10) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
