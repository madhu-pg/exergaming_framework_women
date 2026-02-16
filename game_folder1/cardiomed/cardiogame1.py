import cv2
import mediapipe as mp
import numpy as np
import os
import pygame
import time
import csv
import json
import datetime
import os, sys

# Add path to parent directory to import path_utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from path_utils import get_app_root, get_data_dir, get_game_asset_dir

# --------- RESOLVE APP ROOT DIRECTORY ---------
GAME_DIR = get_game_asset_dir('game_folder1/cardiomed')
APP_ROOT = get_data_dir()  # For CSV/JSON writes

# ------------------ MEDIAPIPE SETUP ------------------
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

def angle_between(v1, v2):
    """Returns the unsigned angle in degrees between vectors v1 and v2"""
    v1 = np.array(v1)
    v2 = np.array(v2)
    if np.linalg.norm(v1) == 0 or np.linalg.norm(v2) == 0:
        return 0.0
    v1_u = v1 / np.linalg.norm(v1)
    v2_u = v2 / np.linalg.norm(v2)
    angle = np.arccos(np.clip(np.dot(v1_u, v2_u), -1.0, 1.0))
    return np.degrees(angle)

# ------------------ LOAD ASSETS ------------------
bg = cv2.imread(os.path.join(GAME_DIR, "background.png"))
if bg is None:
    raise FileNotFoundError("background.png not found!")

screen_height, screen_width = bg.shape[:2]

folder = GAME_DIR
plant_images = []
for i in range(1, 10):  # 1-9 images
    path = os.path.join(folder, f"plant_stage{i}-removebg-preview.png")
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(f"Plant image not found: {path}")
    plant_images.append(img)

growth_threshold = 3
TOTAL_PLANT_STAGES = 12
MAX_STAGE_INDEX = TOTAL_PLANT_STAGES - 1

# ------------------ 4 SETS STRUCTURE ------------------
TOTAL_SETS = 4
SET_DURATION_SECONDS = 120
REST_DURATION_SECONDS = 40
MAX_SCORE = 48
POINTS_PER_SET = 12

plant_index = 0
current_set = 1
consecutive_correct = 0
stage_incremented = False
growth_cooldown = 0
COOLDOWN_FRAMES = 20

# ------------------ PYGAME INITIALIZATION ------------------
try:
    pygame.mixer.init()
except Exception:
    pass
pygame.display.init()
pygame.display.set_mode((1, 1))
pygame.font.init()

try:
    correct_sound = pygame.mixer.Sound(os.path.join(GAME_DIR, "correct-156911.mp3"))
except Exception:
    correct_sound = None

# Fonts
SCORE_FONT = pygame.font.SysFont("Arial", 38, bold=True)
TIMER_FONT = pygame.font.SysFont("Arial", 60, bold=True)
OUTPUT_TITLE_FONT = pygame.font.SysFont("Arial", 70, bold=True)
OUTPUT_SCORE_FONT = pygame.font.SysFont("Arial", 50, bold=True)
OUTPUT_DESC_FONT = pygame.font.SysFont("Arial", 40, bold=True)
OUTPUT_HINT_FONT = pygame.font.SysFont("Arial", 36, bold=False)
REST_FONT = pygame.font.SysFont("Arial", 50, bold=True)

# Colors (BGR for OpenCV)
SCORE_COLOR = (212, 175, 55)
SCORE_BG_RGBA = (10, 30, 80, 220)
TIMER_COLOR = (255, 255, 255)
TIMER_BG_RGBA = (0, 0, 0, 180)
REST_COLOR = (255, 165, 0)
REST_BG_RGBA = (0, 0, 50, 200)

WEBCAM_BORDER_VIOLET = (148, 0, 211)
WEBCAM_BORDER_GREEN = (0, 255, 0)
BORDER_GREEN_DURATION = 1.0
last_score_time = 0.0

# ------------------ TIMER & STATE SETUP ------------------
start_time = 0.0
timer_started = False
is_resting = False
rest_start_time = 0.0
set_completed = False

# ------------------ SCORE DESCRIPTIONS ------------------
score_descriptions = [
    "", "Getting started!", "Good start!", "Building momentum!", 
    "Solid progress!", "Halfway there!", "Strong performance!", 
    "Excellent work!", "Nearly perfect!", "Amazing effort!", "Perfect score!"
]

# ------------------ HELPER FUNCTIONS ------------------
def render_text_surface_pygame(text, font, fg=(255,255,255), bg_rgba=None, padding=12):
    text_surf = font.render(text, True, fg)
    text_w, text_h = text_surf.get_size()
    surf_w, surf_h = text_w + 2*padding, text_h + 2*padding
    surf = pygame.Surface((surf_w, surf_h), flags=pygame.SRCALPHA, depth=32)
    surf = surf.convert_alpha()
    if bg_rgba is not None:
        if len(bg_rgba) == 4:
            r, g, b, a = bg_rgba[2], bg_rgba[1], bg_rgba[0], bg_rgba[3]
        elif len(bg_rgba) == 3:
            r, g, b, a = bg_rgba[2], bg_rgba[1], bg_rgba[0], 255
        else:
            r, g, b, a = 0, 0, 0, 255
        surf.fill((r, g, b, a))
    surf.blit(text_surf, (padding, padding))
    raw_str = pygame.image.tostring(surf, "RGBA", False)
    arr = np.frombuffer(raw_str, dtype=np.uint8).reshape((surf_h, surf_w, 4))
    return arr

def blend_rgba_onto_bgr(target_bgr, src_rgba, top_left):
    x, y = top_left
    h_src, w_src = src_rgba.shape[:2]
    if x >= target_bgr.shape[1] or y >= target_bgr.shape[0]:
        return target_bgr
    w_clip = min(w_src, target_bgr.shape[1] - x)
    h_clip = min(h_src, target_bgr.shape[0] - y)
    src = src_rgba[:h_clip, :w_clip].astype(np.float32) / 255.0
    dst = target_bgr[y:y+h_clip, x:x+w_clip].astype(np.float32) / 255.0
    alpha = src[..., 3:4]
    src_rgb = src[..., :3]
    out_rgb = src_rgb * alpha + dst * (1 - alpha)
    target_bgr[y:y+h_clip, x:x+w_clip] = (out_rgb * 255).astype(np.uint8)
    return target_bgr

def create_panel_rgba(panel_w, panel_h, bg_rgba):
    if len(bg_rgba) == 4:
        r, g, b, a = bg_rgba[2], bg_rgba[1], bg_rgba[0], bg_rgba[3]
    elif len(bg_rgba) == 3:
        r, g, b, a = bg_rgba[2], bg_rgba[1], bg_rgba[0], 255
    else:
        r, g, b, a = 0, 0, 0, 180
    panel = np.zeros((panel_h, panel_w, 4), dtype=np.uint8)
    panel[..., 0] = r
    panel[..., 1] = g
    panel[..., 2] = b
    panel[..., 3] = a
    return panel

def overlay_image(bg_img, fg, x, y):
    h, w = fg.shape[:2]
    h = min(h, bg_img.shape[0] - y)
    w = min(w, bg_img.shape[1] - x)
    fg = fg[:h, :w]
    if fg.shape[2] == 4:
        alpha = fg[:, :, 3] / 255.0
        for c in range(3):
            bg_img[y:y+h, x:x+w, c] = (alpha * fg[:, :, c] + (1 - alpha) * bg_img[y:y+h, x:x+w, c])
    else:
        bg_img[y:y+h, x:x+w] = fg
    return bg_img
def get_set_feedback(score):
    if score <= 3:
        return "Getting started"
    elif score <= 7:
        return "Good effort"
    elif score <= 10:
        return "Strong performance"
    else:
        return "Excellent set!"
def get_final_feedback(total_score):
    if total_score <= 9:
        return "Needs more practice"
    elif total_score <= 18:
        return "Fair performance"
    elif total_score <= 27:
        return "Good cardio endurance"
    elif total_score <= 33:
        return "Excellent workout performance"
    else:
        return "Perfect workout – outstanding!"

# ------------------ FIXED REST SCREEN ------------------
def show_rest_screen(current_set, next_set, set_score):
    out_img = bg.copy()
    panel_w = min(1100, screen_width - 200)
    panel_h = min(700, screen_height - 200)
    panel_x = (screen_width - panel_w) // 2
    panel_y = (screen_height - panel_h) // 2

    panel_rgba = create_panel_rgba(panel_w, panel_h, REST_BG_RGBA)
    out_img = blend_rgba_onto_bgr(out_img, panel_rgba, (panel_x, panel_y))

    title = f"Set {current_set+1} Complete!"
    feedback = get_set_feedback(set_score)
    score_text = f"Set {current_set+1} Score: {set_score}/12"
    feedback_text = f"Feedback: {feedback}"
    next_text = f"Set {next_set+1} starts in..."
    instruction = "Get ready for next set - REST"
    

    # Title
    title_surf = render_text_surface_pygame(title, OUTPUT_TITLE_FONT, fg=REST_COLOR, bg_rgba=None, padding=30)
    tx = panel_x + (panel_w - title_surf.shape[1]) // 2
    ty = panel_y + 30
    out_img = blend_rgba_onto_bgr(out_img, title_surf, (tx, ty))

    # Set Score (Big Green)
    score_surf = render_text_surface_pygame(score_text, OUTPUT_SCORE_FONT, fg=(0,240,0), bg_rgba=None, padding=25)
    sx = panel_x + (panel_w - score_surf.shape[1]) // 2
    sy = ty + title_surf.shape[0] + 10
    out_img = blend_rgba_onto_bgr(out_img, score_surf, (sx, sy))
    feedback = get_set_feedback(set_score)
    feedback_text = f"Feedback: {feedback}"

    feedback_surf = render_text_surface_pygame(
        feedback_text,
        OUTPUT_DESC_FONT,
        fg=(255, 215, 0),
        bg_rgba=None,
        padding=20
    )

    fy = sy + score_surf.shape[0] + 10   # <-- sy is now guaranteed
    fx = panel_x + (panel_w - feedback_surf.shape[1]) // 2

    out_img = blend_rgba_onto_bgr(out_img, feedback_surf, (fx, fy))

    # Next set text
    next_surf = render_text_surface_pygame(next_text, OUTPUT_DESC_FONT, fg=(255,255,255), bg_rgba=None, padding=20)
    nx = panel_x + (panel_w - next_surf.shape[1]) // 2
    ny = sy + score_surf.shape[0] + 40
    out_img = blend_rgba_onto_bgr(out_img, next_surf, (nx, ny))

    # Instruction
    instr_surf = render_text_surface_pygame(instruction, OUTPUT_HINT_FONT, fg=(220,220,220), bg_rgba=None, padding=15)
    ix = panel_x + (panel_w - instr_surf.shape[1]) // 2
    iy = panel_y + panel_h - instr_surf.shape[0] - 40
    out_img = blend_rgba_onto_bgr(out_img, instr_surf, (ix, iy))

    return out_img, panel_x, panel_w, ny

# ------------------ OUTPUT SCREEN ------------------
def show_output_screen(final_score):
    session = {"name": "", "age": "", "height": "", "weight": "", "exercise": "unknown"}
    session_file = os.path.join(APP_ROOT, "current_session.json")
    
    if os.path.exists(session_file):
        try:
            with open(session_file, "r") as f:
                session = json.load(f)
        except Exception:
            pass

    display_score = min(final_score, MAX_SCORE)
    title = "Cardio Workout Complete!"
    score_line = f"Total Score: {display_score}/{MAX_SCORE}"
    desc = get_final_feedback(display_score)

    instruction = "Press ESC or Q to exit"

    # Save to CSV
    try:
        csv_file = os.path.join(APP_ROOT, "exergame_results.csv")
        file_exists = os.path.isfile(csv_file)
        now = datetime.datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")

        with open(csv_file, "a", newline="") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Name", "Age", "Height_cm", "Weight_kg", "Exercise_Type", "Score", "Feedback", "Date", "Time"])
            writer.writerow([
                session.get("name", ""), session.get("age", ""), session.get("height", ""),
                session.get("weight", ""), session.get("exercise", ""), display_score, desc, date_str, time_str
            ])
    except Exception:
        pass

    out_img = bg.copy()
    panel_w = min(1100, screen_width - 200)
    panel_h = min(600, screen_height - 200)
    panel_x = (screen_width - panel_w) // 2
    panel_y = (screen_height - panel_h) // 2

    panel_rgba = create_panel_rgba(panel_w, panel_h, (20, 20, 20, 220))
    out_img = blend_rgba_onto_bgr(out_img, panel_rgba, (panel_x, panel_y))

    title_surf = render_text_surface_pygame(title, OUTPUT_TITLE_FONT, fg=(255,255,255), bg_rgba=None, padding=30)
    tx = panel_x + (panel_w - title_surf.shape[1]) // 2
    ty = panel_y + 20
    out_img = blend_rgba_onto_bgr(out_img, title_surf, (tx, ty))

    score_surf = render_text_surface_pygame(score_line, OUTPUT_SCORE_FONT, fg=(0,255,0), bg_rgba=None, padding=30)
    sx = panel_x + (panel_w - score_surf.shape[1]) // 2
    sy = ty + title_surf.shape[0] + 20
    out_img = blend_rgba_onto_bgr(out_img, score_surf, (sx, sy))

    desc_surf = render_text_surface_pygame(desc, OUTPUT_DESC_FONT, fg=(212,175,55), bg_rgba=None, padding=24)
    dx = panel_x + (panel_w - desc_surf.shape[1]) // 2
    dy = sy + score_surf.shape[0] + 40
    out_img = blend_rgba_onto_bgr(out_img, desc_surf, (dx, dy))

    instr_surf = render_text_surface_pygame(instruction, OUTPUT_HINT_FONT, fg=(220,220,220), bg_rgba=None, padding=12)
    ix = panel_x + (panel_w - instr_surf.shape[1]) // 2
    iy = panel_y + panel_h - instr_surf.shape[0] - 30
    out_img = blend_rgba_onto_bgr(out_img, instr_surf, (ix, iy))

    while True:
        cv2.imshow("Garden Growth", out_img)
        k = cv2.waitKey(10) & 0xFF
        if k == 27 or k == ord('q'):
            cap.release()
            cv2.destroyAllWindows()
            pygame.font.quit()
            pygame.display.quit()
            pygame.mixer.quit()
            exit()
        if k == 13:
            return

# ------------------ WINDOW + CAMERA ------------------
cv2.namedWindow("Garden Growth", cv2.WINDOW_NORMAL)
cv2.setWindowProperty("Garden Growth", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

base_offset_y = 100
forward_shift_per_stage = 8

# ------------------ MAIN GAME LOOP ------------------
total_score = 0
set_scores = [0] * TOTAL_SETS

with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False
        results = pose.process(image)
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        # ------------------ POSE DETECTION ------------------
        if results.pose_landmarks:
            lm = results.pose_landmarks.landmark

            # Left arm
            shoulder_l = np.array([lm[mp_pose.PoseLandmark.LEFT_SHOULDER].x, lm[mp_pose.PoseLandmark.LEFT_SHOULDER].y])
            wrist_l = np.array([lm[mp_pose.PoseLandmark.LEFT_WRIST].x, lm[mp_pose.PoseLandmark.LEFT_WRIST].y])
            hip_l = np.array([lm[mp_pose.PoseLandmark.LEFT_HIP].x, lm[mp_pose.PoseLandmark.LEFT_HIP].y])
            torso_vec_l = hip_l - shoulder_l
            arm_vec_l = wrist_l - shoulder_l
            angle_l = angle_between(torso_vec_l, arm_vec_l)
            angle_l = +angle_l if wrist_l[0] > shoulder_l[0] else -angle_l
            angle_l = np.clip(angle_l, -90, 90)
            left_arm_status = "Arm Open/Outward" if angle_l >= 0 else "Arm Crossed"

            # Right arm
            shoulder_r = np.array([lm[mp_pose.PoseLandmark.RIGHT_SHOULDER].x, lm[mp_pose.PoseLandmark.RIGHT_SHOULDER].y])
            wrist_r = np.array([lm[mp_pose.PoseLandmark.RIGHT_WRIST].x, lm[mp_pose.PoseLandmark.RIGHT_WRIST].y])
            hip_r = np.array([lm[mp_pose.PoseLandmark.RIGHT_HIP].x, lm[mp_pose.PoseLandmark.RIGHT_HIP].y])
            torso_vec_r = hip_r - shoulder_r
            arm_vec_r = wrist_r - shoulder_r
            angle_r = angle_between(torso_vec_r, arm_vec_r)
            angle_r = +angle_r if wrist_r[0] < shoulder_r[0] else -angle_r
            angle_r = np.clip(angle_r, -90, 90)
            right_arm_status = "Arm Open/Outward" if angle_r >= 0 else "Arm Crossed"

            # Legs
            ankle_l = np.array([lm[mp_pose.PoseLandmark.LEFT_ANKLE].x, lm[mp_pose.PoseLandmark.LEFT_ANKLE].y])
            ankle_r = np.array([lm[mp_pose.PoseLandmark.RIGHT_ANKLE].x, lm[mp_pose.PoseLandmark.RIGHT_ANKLE].y])
            ankle_distance = np.linalg.norm(ankle_r - ankle_l)
            leg_state = "Legs Open" if ankle_distance > 0.25 else "Legs Closed"

            current_pose_correct = (left_arm_status == "Arm Crossed" and
                                  right_arm_status == "Arm Crossed" and
                                  leg_state == "Legs Closed")

            if current_pose_correct and not is_resting:
                consecutive_correct += 1
                if consecutive_correct >= growth_threshold and not stage_incremented and total_score < MAX_SCORE:
                    plant_index = min(plant_index + 1, MAX_STAGE_INDEX)
                    growth_cooldown = COOLDOWN_FRAMES
                    stage_incremented = True
                    last_score_time = time.time()
                    
                    if set_scores[current_set-1] < POINTS_PER_SET:
                        set_scores[current_set-1] += 1
                    total_score += 1

                    # ✅ STOP SET WHEN MAX SCORE REACHED
                    if set_scores[current_set-1] >= POINTS_PER_SET:
                        set_completed = True

                        
                    try:
                        if correct_sound:
                            correct_sound.play()
                    except Exception:
                        pass
            else:
                consecutive_correct = 0
                stage_incremented = False

        # ------------------ FIXED STATE MANAGEMENT ------------------
        now = time.time()
        
        if is_resting:
            rest_elapsed = now - rest_start_time
            rest_remaining = max(0, REST_DURATION_SECONDS - rest_elapsed)
            
            if rest_remaining <= 0:
                is_resting = False
                plant_index = 0
                consecutive_correct = 0
                stage_incremented = False
                start_time = now
                timer_started = True
                current_set += 1
                set_completed = False

                if current_set > TOTAL_SETS:
                    show_output_screen(total_score)
                    break
            else:
                # Show rest screen with set score
                current_set_score = set_scores[current_set - 1]
                rest_img, panel_x, panel_w, ny = show_rest_screen(current_set-1, current_set, current_set_score)
                
                # COUNTDOWN TIMER - TRANSPARENT BACKGROUND
                countdown_text = f"{int(rest_remaining)}s"
                countdown_surf = render_text_surface_pygame(countdown_text, REST_FONT, fg=(255,255,0), bg_rgba=None, padding=40)
                cx = panel_x + (panel_w - countdown_surf.shape[1]) // 2
                cy = ny + 60
                rest_img = blend_rgba_onto_bgr(rest_img, countdown_surf, (cx, cy))

                
                cv2.imshow('Garden Growth', rest_img)
                cv2.waitKey(10)
                continue
        else:
            if not timer_started:
                start_time = now
                timer_started = True

            elapsed_f = now - start_time
            remaining_f = SET_DURATION_SECONDS - elapsed_f

            # ✅ END SET IF TIME UP OR SCORE COMPLETED
            if remaining_f <= 0 or set_completed:
                set_completed = False  # reset for next set

                if current_set < TOTAL_SETS:
                    is_resting = True
                    rest_start_time = now
                    timer_started = False
                else:
                    show_output_screen(total_score)
                    break

        # ------------------ RENDER FRAME ------------------
        if not is_resting:  # Only render game during sets
            frame_game = bg.copy()
            
            # Plant display (20 stages, cycle through 9 images)
            display_img_index = plant_index % 9
            ph, pw = plant_images[display_img_index].shape[:2]
            max_width = int(screen_width * 0.5)
            max_height = int(screen_height * 0.5)
            scale_w = max_width / pw
            scale_h = max_height / ph
            scale_factor = min(scale_w, scale_h)
            plant_resized = cv2.resize(plant_images[display_img_index], (int(pw*scale_factor), int(ph*scale_factor)))
            
            center_x = screen_width // 2
            center_y = screen_height // 2
            plant_h, plant_w = plant_resized.shape[:2]
            plant_x = center_x - plant_w // 2
            plant_y = center_y - plant_h // 2 + base_offset_y + (plant_index * forward_shift_per_stage)
            frame_game = overlay_image(frame_game, plant_resized, plant_x, plant_y)

            # Webcam
            webcam_small = cv2.resize(frame, (300, 225))
            if results.pose_landmarks:
                mp_drawing.draw_landmarks(webcam_small, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
            ws_x, ws_y = 10, 10
            frame_game[ws_y:ws_y+225, ws_x:ws_x+300] = webcam_small

            # Webcam border
            border_color = WEBCAM_BORDER_VIOLET
            if time.time() - last_score_time <= BORDER_GREEN_DURATION:
                border_color = WEBCAM_BORDER_GREEN
            cv2.rectangle(frame_game, (ws_x-6, ws_y-6), (ws_x+300+6, ws_y+225+6), border_color, thickness=6)

            # Timer
            remaining_f = max(0, SET_DURATION_SECONDS - (now - start_time))
            mins = int(remaining_f) // 60
            secs = int(remaining_f) % 60
            timer_text = f"Set {current_set} - {mins:02d}:{secs:02d}"
            
            timer_surf_rgba = render_text_surface_pygame(timer_text, TIMER_FONT, fg=TIMER_COLOR, bg_rgba=TIMER_BG_RGBA, padding=12)
            tx = (screen_width - timer_surf_rgba.shape[1]) // 2
            ty = 20
            frame_game = blend_rgba_onto_bgr(frame_game, timer_surf_rgba, (tx, ty))

            # Score display
            current_set_score = set_scores[current_set - 1]
            score_text = f"Set Score: {current_set_score}/12 | Set {current_set}"
            score_surf_rgba = render_text_surface_pygame(score_text, SCORE_FONT, fg=SCORE_COLOR, bg_rgba=SCORE_BG_RGBA, padding=5)
            sx = screen_width - score_surf_rgba.shape[1] - 20
            sy = 20
            frame_game = blend_rgba_onto_bgr(frame_game, score_surf_rgba, (sx, sy))

            cv2.imshow('Garden Growth', frame_game)

        k = cv2.waitKey(10) & 0xFF
        if k == ord('q') or k == 27:
            break

cap.release()
cv2.destroyAllWindows()
pygame.font.quit()
pygame.display.quit()
pygame.mixer.quit()
