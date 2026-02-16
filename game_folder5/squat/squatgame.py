# <same imports and top-of-file code as you had>
import os
import csv
import json
import datetime
import os, sys

# Suppress MediaPipe and TensorFlow warnings
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["MEDIAPIPE_DISABLE_LOGGING"] = "1"

import cv2
import mediapipe as mp
import numpy as np
import pygame
import sys
import time

# Add path to parent directory to import path_utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from path_utils import get_app_root, get_data_dir, get_game_asset_dir

# --------- RESOLVE APP ROOT DIRECTORY ---------
GAME_DIR = get_game_asset_dir('game_folder5/squat')
APP_ROOT = get_data_dir()  # For CSV/JSON writes

# ---------------- CONFIG ----------------
BG_FILE = "background.png"
AVATAR_FILE = "avatar (1).png"
BRICK_FILE = "brick.png"
CELEBRATE_FILE = "celebrate.png"

# Changed: always 5 bricks per squat for each step in sequence
BRICK_PER_SQUAT = [5, 5, 5, 5, 5]
CYCLES = 2  # total cycles
SQUAT_ANGLE_DOWN = 90
SQUAT_ANGLE_UP = 130
MIN_FRAMES = 3
# ---------------- SET & REST CONSTANTS ----------------
TOTAL_SETS = 3
POINTS_PER_SET = 6
MAX_POINTS = 6
MAX_FINAL_SCORE = TOTAL_SETS * MAX_POINTS  # 32

SET_DURATION = 120      # seconds per set
REST_DURATION = 45      # seconds rest between sets

# total squats required = entries * cycles = 5 * 2 = 10
TOTAL_SQUATS_REQUIRED = len(BRICK_PER_SQUAT) * CYCLES

# Timer (2 minutes)
GAME_DURATION = 120  # seconds

# Webcam border flash length (seconds)
BORDER_GREEN_DURATION = 1.0

# ---------------- MediaPipe setup ----------------
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

def calculate_angle(a, b, c):
    a = np.array(a); b = np.array(b); c = np.array(c)
    radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    if angle > 180.0:
        angle = 360 - angle
    return angle

# ---------------- Pygame fullscreen setup ----------------
pygame.init()
# initialize pygame & audio
# initialize mixer (safe to call even if mixer already initialized)
try:
    pygame.mixer.init()
except Exception as e:
    print(f"⚠️ pygame.mixer.init() failed: {e}")

# load correct-answer sound (safe fallback)
correct_sound = None
try:
    correct_sound = pygame.mixer.Sound("correct-156911.mp3")
    # optional: set a sensible volume (0.0 to 1.0)
    correct_sound.set_volume(0.7)
except Exception as e:
    print(f"⚠️ Failed to load sound 'correct-156911.MP3': {e}")

info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Tower of Strength - Fullscreen Mode")
clock = pygame.time.Clock()

# ---------------- Safe image loader ----------------
def safe_load(path):
    try:
        img = pygame.image.load(path)
        return img
    except Exception as e:
        print(f"⚠️ Failed to load {path}: {e}")
        return None

# Load & scale images
bg = safe_load(BG_FILE)
if bg:
    bg = pygame.transform.scale(bg, (WIDTH, HEIGHT))
else:
    bg = pygame.Surface((WIDTH, HEIGHT))
    bg.fill((180, 220, 255))  # fallback sky-blue background

avatar = safe_load(AVATAR_FILE)
brick_img = safe_load(BRICK_FILE)
celebrate = safe_load(CELEBRATE_FILE)

# Fallbacks
if avatar is None:
    avatar = pygame.Surface((200, 400), pygame.SRCALPHA)
    pygame.draw.ellipse(avatar, (200, 80, 150), avatar.get_rect())

if brick_img is None:
    brick_w = int(WIDTH * 0.08)
    brick_h = int(brick_w * 0.5)
    brick_img = pygame.Surface((brick_w, brick_h), pygame.SRCALPHA)
    pygame.draw.rect(brick_img, (178, 34, 34), brick_img.get_rect(), border_radius=8)

# Scale sprite sizes (KEEP proportions similar to earlier simple script)
avatar_w = int(WIDTH * 0.45)
avatar_h = int(HEIGHT * 0.75)
avatar = pygame.transform.smoothscale(avatar, (avatar_w, avatar_h))

brick_w = int(WIDTH * 0.08)
# preserve brick aspect ratio from loaded brick_img
if brick_img.get_width() != 0:
    brick_h = int(brick_img.get_height() * brick_w / brick_img.get_width())
else:
    brick_h = int(brick_w * 0.5)
brick_img = pygame.transform.smoothscale(brick_img, (brick_w, brick_h))

if celebrate:
    celebrate = pygame.transform.scale(celebrate, (int(WIDTH * 0.5), int(HEIGHT * 0.5)))

# ---------------- Layout setup ----------------
GROUND_Y = int(HEIGHT * 0.95)
# initial avatar Y (stands on ground)
AVATAR_X = WIDTH // 2 - avatar_w // 2 + 150
AVATAR_Y_BASE = GROUND_Y - avatar_h
AVATAR_Y = AVATAR_Y_BASE

# ---------------- Game state ----------------
brick_rows = []
current_sequence_idx = 0
squat_count = 0
in_squat = False
frames_squat = 0
frames_stand = 0
squats_needed = TOTAL_SQUATS_REQUIRED
last_score_time = 0.0

# ---------------- Camera setup ----------------
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Preview configuration
PREVIEW_FRAC = 0.30   # preview width as fraction of screen width
PREVIEW_POS = (10, 10)  # top-left corner for preview
MIRROR_PREVIEW = True   # flip preview horizontally for a selfie view

# ---------------- Fonts (pygame) ----------------
HUD_FONT = pygame.font.SysFont(None, int(WIDTH * 0.03))
TIMER_FONT = pygame.font.SysFont(None, int(WIDTH * 0.04), bold=True)
OUTPUT_TITLE_FONT = pygame.font.SysFont(None, int(WIDTH * 0.06), bold=True)
OUTPUT_SCORE_FONT = pygame.font.SysFont(None, int(WIDTH * 0.08), bold=True)
OUTPUT_DESC_FONT = pygame.font.SysFont(None, int(WIDTH * 0.035))
# ---------------- SET STATE VARIABLES ----------------
current_set = 1
set_scores = [0] * TOTAL_SETS
total_score = 0

# score descriptions for 10 points (index 0 unused)
score_descriptions = [
    "",
    "Nice start — keep going!",
    "Good — squating with control!",
    "Steady — squats improving!",
    "Strong — form getting better!",
    "Solid — consistent reps!",
    "Very strong — great stability!",
    "Powerful — excellent technique!",
    "Outstanding — high control!",
    "Exceptional — near perfect!",
    "Perfect — superb performance!"
]
def show_rest_screen(set_no, set_score):
    clock = pygame.time.Clock()
    start = time.time()

    title_font = pygame.font.SysFont(None, int(WIDTH * 0.07), bold=True)
    text_font  = pygame.font.SysFont(None, int(WIDTH * 0.04))
    fb_font    = pygame.font.SysFont(None, int(WIDTH * 0.038))

    # Simple per‑set feedback based on set_score (0–MAX_POINTS)
    if set_score <= 2:
        fb_text = "Feedback: Good start – try to go a bit deeper in your squats next set."
    elif set_score <= 4:
        fb_text = "Feedback: Nice effort – keep your back straight and control the movement."
    elif set_score < MAX_POINTS:
        fb_text = "Feedback: Strong set – maintain this form and pace."
    else:  # set_score == MAX_POINTS
        fb_text = "Feedback: Excellent! You completed all squats in this set."

    while True:
        elapsed = time.time() - start
        remaining = max(0, REST_DURATION - int(elapsed))

        screen.fill((20, 20, 40))

        title = title_font.render(f"Set {set_no} Complete!", True, (255, 200, 0))
        score = text_font.render(f"Set Score: {set_score}/{MAX_POINTS}", True, (0, 255, 0))
        rest  = text_font.render(f"Next set starts in {remaining}s", True, (255, 255, 255))
        fb    = fb_font.render(fb_text, True, (255, 215, 0))

        screen.blit(title, title.get_rect(center=(WIDTH//2, HEIGHT//2 - 140)))
        screen.blit(score, score.get_rect(center=(WIDTH//2, HEIGHT//2 - 40)))
        screen.blit(fb,    fb.get_rect(center=(WIDTH//2, HEIGHT//2 + 40)))
        screen.blit(rest,  rest.get_rect(center=(WIDTH//2, HEIGHT//2 + 130)))

        pygame.display.update()
        clock.tick(30)

        if remaining <= 0:
            return
def get_final_feedback(score, max_score):
    """Return a single feedback line based on total score ratio."""
    if max_score <= 0:
        return ""

    ratio = score / max_score

    if score == 0:
        return "Let’s try again – begin with comfortable, shallow squats at your own pace."
    elif ratio <= 0.25:
        return "Good start! You’ve begun strengthening – aim for a few more squats next time."
    elif ratio <= 0.5:
        return "Nice work! You’re building leg strength and control with each squat."
    elif ratio <= 0.75:
        return "Great stamina! You maintained good effort through most of the sets."
    elif ratio < 1.0:
        return "Almost perfect! Just a little more depth or consistency to reach full score."
    else:  # ratio == 1.0
        return "Excellent! You completed the full strengthening tower with strong, controlled squats."


# ---------------- Output screen (pygame) ----------------
def show_output_screen(final_score):
        # ---------- LOAD SESSION DATA (NON-BLOCKING) ----------
    session = {
        "name": "",
        "age": "",
        "height": "",
        "weight": "",
        "exercise": "unknown"
    }

    session_file = os.path.join(APP_ROOT, "current_session.json")
    if os.path.exists(session_file):
        try:
            with open(session_file, "r") as f:
                session = json.load(f)
        except Exception:
            pass

    display_score = final_score                   # 0 .. MAX_FINAL_SCORE
    title = "Strengthening Output"
    score_line = f"Score: {display_score}/{MAX_FINAL_SCORE}"

    desc = get_final_feedback(display_score, MAX_FINAL_SCORE)
    instruction = "Press ESC or Q to exit and continue strengthening exercise"

        # ---------- SAVE RESULT TO CSV ----------
    try:
        csv_file = os.path.join(APP_ROOT, "exergame_results.csv")
        file_exists = os.path.isfile(csv_file)

        now = datetime.datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")

        with open(csv_file, "a", newline="") as f:
            writer = csv.writer(f)

            if not file_exists:
                writer.writerow([
                    "Name", "Age", "Height_cm", "Weight_kg",
                    "Exercise_Type", "Score", "Feedback",
                    "Date", "Time"
                ])

            writer.writerow([
                session.get("name", ""),
                session.get("age", ""),
                session.get("height", ""),
                session.get("weight", ""),
                session.get("exercise", ""),
                display_score,
                desc,
                date_str,
                time_str
            ])
    except Exception:
        pass

    # create translucent panel surface
    panel_w = min(1100, WIDTH - 200)
    panel_h = min(700, HEIGHT - 150)
    panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    panel.fill((20, 20, 20, 220))  # dark translucent

    # render texts onto panel using pygame fonts
    # Title
    title_surf = OUTPUT_TITLE_FONT.render(title, True, (255,255,255))
    score_surf = OUTPUT_SCORE_FONT.render(score_line, True, (0,255,0))
    desc_surf = OUTPUT_DESC_FONT.render(desc, True, (212,175,55))
    instr_surf = OUTPUT_DESC_FONT.render(instruction, True, (220,220,220))

    # positions
    tx = (panel_w - title_surf.get_width()) // 2
    ty = 40
    sx = (panel_w - score_surf.get_width()) // 2
    sy = ty + title_surf.get_height() + 20
    dx = (panel_w - desc_surf.get_width()) // 2
    dy = sy + score_surf.get_height() + 24
    ix = (panel_w - instr_surf.get_width()) // 2
    iy = panel_h - instr_surf.get_height() - 40

    panel.blit(title_surf, (tx, ty))
    panel.blit(score_surf, (sx, sy))
    panel.blit(desc_surf, (dx, dy))
    panel.blit(instr_surf, (ix, iy))

    # center panel on screen
    px = (WIDTH - panel_w) // 2
    py = (HEIGHT - panel_h) // 2

    # show until ESC/Q (exit) or ENTER (continue)
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); cap.release(); cv2.destroyAllWindows(); sys.exit(0)
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE or ev.key == pygame.K_q:
                    pygame.quit(); cap.release(); cv2.destroyAllWindows(); sys.exit(0)
                if ev.key == pygame.K_RETURN:
                    return

        screen.blit(bg, (0,0))
        screen.blit(panel, (px, py))
        pygame.display.flip()
        clock.tick(30)

# ---------------- Game loop ----------------
def run_game():
    global current_set, total_score, set_scores
    global frames_stand, frames_squat, squat_count, in_squat, brick_rows, AVATAR_Y

    # Reset tower / avatar / squat state for this set
    def reset_set_state():
        global brick_rows, squat_count, in_squat, frames_squat, frames_stand, AVATAR_Y
        brick_rows = []
        squat_count = 0
        in_squat = False
        frames_squat = 0
        frames_stand = 0
        AVATAR_Y = AVATAR_Y_BASE

    reset_set_state()
    set_start_time = time.time()
    last_score_time = 0.0
    SCORE_FLASH_DURATION = 1.0

    with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
        running = True
        while running:
            ret, frame = cap.read()
            if not ret:
                print("❌ Camera not detected. Exiting.")
                running = False
                break

            elapsed = time.time() - set_start_time
            remaining = max(0, SET_DURATION - int(elapsed))
            current_set_score = set_scores[current_set - 1]

            # End current set if max points reached OR time is up
            if current_set_score >= MAX_POINTS or remaining <= 0:
                if current_set < TOTAL_SETS:
                    show_rest_screen(current_set, current_set_score)
                    current_set += 1
                    total_score += current_set_score
                    reset_set_state()
                    set_start_time = time.time()
                    continue
                else:
                    total_score += current_set_score
                    break

            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image.flags.writeable = False
            results = pose.process(image)
            image.flags.writeable = True

            knee_angle = None
            try:
                lm = results.pose_landmarks.landmark
                h_img, w_img, _ = frame.shape
                hip = [lm[mp_pose.PoseLandmark.RIGHT_HIP.value].x * w_img,
                       lm[mp_pose.PoseLandmark.RIGHT_HIP.value].y * h_img]
                knee = [lm[mp_pose.PoseLandmark.RIGHT_KNEE.value].x * w_img,
                        lm[mp_pose.PoseLandmark.RIGHT_KNEE.value].y * h_img]
                ankle = [lm[mp_pose.PoseLandmark.RIGHT_ANKLE.value].x * w_img,
                         lm[mp_pose.PoseLandmark.RIGHT_ANKLE.value].y * h_img]
                knee_angle = calculate_angle(hip, knee, ankle)
            except Exception:
                knee_angle = None

            # -------------------- LIVE SKELETAL PREVIEW (top-left) --------------------
            vis_frame = frame.copy()
            if results.pose_landmarks:
                mp_drawing.draw_landmarks(
                    vis_frame,
                    results.pose_landmarks,
                    mp_pose.POSE_CONNECTIONS,
                    mp_drawing.DrawingSpec(color=(0,255,0), thickness=2, circle_radius=2),
                    mp_drawing.DrawingSpec(color=(0,0,255), thickness=2, circle_radius=2)
                )

            vis_rgb = cv2.cvtColor(vis_frame, cv2.COLOR_BGR2RGB)
            if MIRROR_PREVIEW:
                vis_rgb = cv2.flip(vis_rgb, 1)
            vis_rgb = np.ascontiguousarray(vis_rgb)

            h_vis, w_vis = vis_rgb.shape[:2]
            try:
                cam_surf = pygame.image.frombuffer(vis_rgb.tobytes(), (w_vis, h_vis), 'RGB')
            except Exception:
                cam_surf = pygame.surfarray.make_surface(np.transpose(vis_rgb, (1, 0, 2)))

            preview_w = int(WIDTH * PREVIEW_FRAC)
            preview_h = int(preview_w * (h_vis / w_vis))
            cam_surf = pygame.transform.smoothscale(cam_surf, (preview_w, preview_h))

            # ---- Squat detection ----
            if knee_angle is not None:
                if knee_angle < SQUAT_ANGLE_DOWN:
                    frames_squat += 1
                    frames_stand = 0
                elif knee_angle > SQUAT_ANGLE_UP:
                    frames_stand += 1
                    frames_squat = 0
                else:
                    frames_squat = 0
                    frames_stand = 0

                if frames_squat >= MIN_FRAMES:
                    in_squat = True

                if in_squat and frames_stand >= MIN_FRAMES:
                    in_squat = False
                    if squat_count < squats_needed:
                        # Clear tower only when a full sequence of squats finishes
                        if (squat_count != 0) and ((squat_count % len(BRICK_PER_SQUAT)) == 0):
                            brick_rows = []
                            AVATAR_Y = AVATAR_Y_BASE

                        bricks_to_add = 5
                        squat_count += 1
                        last_score_time = time.time()

                        # Only count toward set score up to MAX_POINTS per set
                        if current_set_score < MAX_POINTS:
                            set_scores[current_set - 1] += 1

                        # play correct sound on score increment (non-blocking)
                        try:
                            if correct_sound:
                                correct_sound.play()
                        except Exception as e:
                            print(f"⚠️ Failed to play sound: {e}")

                        # Build new brick layer centered
                        total_row_width = bricks_to_add * brick_w
                        start_x = WIDTH // 2 - total_row_width // 2
                        row_y = GROUND_Y - (len(brick_rows) + 1) * brick_h - 10
                        row = [(start_x + i * brick_w, row_y) for i in range(bricks_to_add)]
                        brick_rows.append(row)

                        # After appending, move avatar to stand on top of newest row
                        AVATAR_Y = row_y - avatar_h - 5

            # ---- Event handling ----
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                        running = False

            # ---- Draw scene ----
            screen.blit(bg, (0, 0))

            # Draw stacked bricks
            for row in brick_rows:
                for (bx, by) in row:
                    screen.blit(brick_img, (bx, by))

            # Draw avatar (use current AVATAR_Y)
            screen.blit(avatar, (AVATAR_X, int(AVATAR_Y)))

            # Draw camera preview box + border
            preview_bg = pygame.Surface((preview_w + 8, preview_h + 8), pygame.SRCALPHA)
            preview_bg.fill((255, 255, 255, 200))
            pb_x, pb_y = PREVIEW_POS

            time_since_score = time.time() - last_score_time
            if 0 <= time_since_score <= BORDER_GREEN_DURATION:
                border_col = (0, 255, 0)  # green
            else:
                border_col = (148, 0, 211)  # violet

            pygame.draw.rect(preview_bg, border_col + (255,), preview_bg.get_rect(), width=6, border_radius=6)
            screen.blit(preview_bg, (pb_x, pb_y))
            screen.blit(cam_surf, (pb_x + 4, pb_y + 4))

            # HUD (timer top-center, score top-right)
            mins, secs = divmod(remaining, 60)
            timer_text = f"{mins:02d}:{secs:02d}"
            timer_surf = TIMER_FONT.render(timer_text, True, (255,255,255))
            timer_x = (WIDTH - timer_surf.get_width()) // 2
            timer_y = 10
            rect_pad = 12
            pygame.draw.rect(screen, (0,0,0,180),
                             (timer_x-rect_pad, timer_y-rect_pad,
                              timer_surf.get_width()+2*rect_pad,
                              timer_surf.get_height()+2*rect_pad),
                             border_radius=8)
            screen.blit(timer_surf, (timer_x, timer_y))

            # Score (squats)
            score_surf = HUD_FONT.render(f"Squats: {squat_count}/{POINTS_PER_SET}", True, (0,0,0))
            score_x = WIDTH - score_surf.get_width() - 40
            score_y = 20
            pygame.draw.rect(screen, (255,255,255,220),
                             (score_x-10, score_y-8,
                              score_surf.get_width()+20,
                              score_surf.get_height()+16),
                             border_radius=8)
            screen.blit(score_surf, (score_x, score_y))

            # Bricks count
            total_bricks = sum(len(r) for r in brick_rows)
            bricks_surf = HUD_FONT.render(f"Bricks: {total_bricks}", True, (0,0,0))
            screen.blit(bricks_surf, (score_x, score_y + score_surf.get_height() + 8))

            # Set score HUD
            set_score_surf = HUD_FONT.render(
                f"SET {current_set}: {set_scores[current_set-1]}/{MAX_POINTS}",
                True, (0, 0, 0)
            )
            screen.blit(set_score_surf, (score_x, score_y + score_surf.get_height() + 30))

            # Celebration when set‑max reached
            if set_scores[current_set - 1] >= MAX_POINTS:
                msg_font = pygame.font.SysFont(None, int(WIDTH * 0.06))
                msg = msg_font.render("🏆 Set Complete! Great Strength!", True, (0, 120, 0))
                screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, int(HEIGHT * 0.12)))
                if celebrate:
                    screen.blit(celebrate, (WIDTH // 2 - celebrate.get_width() // 2, int(HEIGHT * 0.25)))

            pygame.display.flip()
            clock.tick(30)

    # After loop, show output screen
    restart = show_output_screen(total_score)
    return restart
 

# ---- RUN (allow restart) ----
while True:
    restart_game = run_game()
    if restart_game:
        current_set = 1
        total_score = 0
        set_scores = [0] * TOTAL_SETS
        continue
    else:
        break

# ---- Cleanup ----
cap.release()
pygame.quit()
cv2.destroyAllWindows()

