import cv2
import mediapipe as mp
import numpy as np
import time
import pygame
import os
import csv
import json
import datetime
import os, sys

# Add path to parent directory to import path_utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from path_utils import get_app_root, get_data_dir, get_game_asset_dir

# --------- RESOLVE APP ROOT DIRECTORY ---------
GAME_DIR = get_game_asset_dir('game_folder6/twistdif')
APP_ROOT = get_data_dir()  # For CSV/JSON writes

# ------------------ SETTINGS ------------------
FRAME_WIDTH, FRAME_HEIGHT = 1280, 720
WEBCAM_W, WEBCAM_H = 200, 140
# ------------------ SET & REST SETTINGS ------------------
TOTAL_SETS = 5
SET_DURATION = 180        # seconds per set
REST_DURATION = 20        # seconds rest
POINTS_PER_SET = 15       # max points per set
MAX_FINAL_SCORE = TOTAL_SETS * POINTS_PER_SET
DISPLAY_FPS_DELAY = 6
BORDER_GREEN_DURATION = 1.0

# ------------------ ASSET PATHS ------------------
BG_PATH = os.path.join(GAME_DIR, "backgorund.png")
LEFT_TOP_PATH = os.path.join(GAME_DIR, "left top.png")
RIGHT_TOP_PATH = os.path.join(GAME_DIR, "right top.png")
AVATAR_LEFT_PATH = os.path.join(GAME_DIR, "left avatar.png")
AVATAR_RIGHT_PATH = os.path.join(GAME_DIR, "right avatar.png")
INCREMENT_SOUND = os.path.join(GAME_DIR, "correct-156911.mp3")

# ------------------ VISUAL SETTINGS ------------------
LEFT_TOP_POS = (0.18, 0.60)
RIGHT_TOP_POS = (0.82, 0.60)
AVATAR_POS = (0.50, 0.52)
TOP_WIDTH_FRAC = 0.14
AVATAR_WIDTH_FRAC = 0.45
SPIN_DURATION_FRAMES = 14
SPIN_SPEED_DEG_PER_FRAME = 30

# -------------- detection/timing parameters --------------
TWIST_THRESHOLD = 0.05
HOLD_FRAMES_REQUIRED = 5   # frames required to confirm a twist hold

# ------------------ PYGAME / FONTS ------------------
try:
    pygame.mixer.init()
except Exception:
    pass
pygame.display.init()
pygame.display.set_mode((1, 1))
pygame.font.init()
TIMER_FONT = pygame.font.SysFont("Arial", 40, bold=True)
SCORE_FONT = pygame.font.SysFont("Arial", 36, bold=True)
OUTPUT_TITLE_FONT = pygame.font.SysFont("Arial", 72, bold=True)
OUTPUT_SCORE_FONT = pygame.font.SysFont("Arial", 80, bold=True)
OUTPUT_DESC_FONT = pygame.font.SysFont("Arial", 36, bold=True)
OUTPUT_HINT_FONT = pygame.font.SysFont("Arial", 24, bold=False)

TIMER_COLOR = (255, 255, 255)
TIMER_BG_RGBA = (0, 0, 0, 180)
SCORE_COLOR = (212, 175, 55)
SCORE_BG_RGBA = (10, 30, 80, 220)
WEBCAM_BORDER_VIOLET = (148, 0, 211)
WEBCAM_BORDER_GREEN = (0, 255, 0)

score_descriptions = [
    "", "Nice start — keep going!", "Good — twisting with control!", "Steady — twist improving!",
    "Strong — twist getting better!", "Solid — consistent reps!", "Very strong — great stability!",
    "Powerful — excellent technique!", "Outstanding — high control!", "Exceptional — near perfect!",
    "Perfect — superb performance!"
]

# ------------------ HELPER FUNCTIONS ------------------
def render_text_surface_pygame(text, font, fg=(255,255,255), bg_rgba=None, padding=8):
    surf_text = font.render(text, True, fg)
    w, h = surf_text.get_size()
    surf_w, surf_h = w + 2*padding, h + 2*padding
    surf = pygame.Surface((surf_w, surf_h), flags=pygame.SRCALPHA, depth=32).convert_alpha()
    if bg_rgba is not None:
        if len(bg_rgba) == 4:
            r, g, b, a = bg_rgba[2], bg_rgba[1], bg_rgba[0], bg_rgba[3]
        else:
            r, g, b, a = bg_rgba[2], bg_rgba[1], bg_rgba[0], 255
        surf.fill((r, g, b, a))
    surf.blit(surf_text, (padding, padding))
    raw = pygame.image.tostring(surf, "RGBA", False)
    arr = np.frombuffer(raw, dtype=np.uint8).reshape((surf_h, surf_w, 4))
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
    out = src_rgb * alpha + dst * (1 - alpha)
    target_bgr[y:y+h_clip, x:x+w_clip] = (out * 255).astype(np.uint8)
    return target_bgr

def load_rgba(path):
    if os.path.exists(path):
        im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if im is None:
            return None
        if im.ndim == 3 and im.shape[2] == 3:
            b,g,r = cv2.split(im); a = np.ones(b.shape, dtype=b.dtype)*255
            im = cv2.merge([b,g,r,a])
        return im
    return None

def overlay_rgba_on_bgr(bg_bgr, fg_rgba, top_left):
    if fg_rgba is None:
        return bg_bgr
    x,y = top_left
    fh, fw = fg_rgba.shape[:2]
    bh, bw = bg_bgr.shape[:2]
    if x >= bw or y >= bh:
        return bg_bgr
    w = min(fw, bw - x)
    h = min(fh, bh - y)
    if w <= 0 or h <= 0:
        return bg_bgr
    fg = fg_rgba[:h, :w]
    b,g,r,a = cv2.split(fg)
    alpha = (a.astype(np.float32)/255.0)[...,None]
    for c, channel in enumerate([b,g,r]):
        bg_bgr[y:y+h, x:x+w, c] = (channel.astype(np.float32)*alpha[...,0] + bg_bgr[y:y+h, x:x+w, c].astype(np.float32)*(1-alpha[...,0])).astype(np.uint8)
    return bg_bgr

def rotate_rgba(img, angle_deg):
    if img is None:
        return None
    h,w = img.shape[:2]
    center = (w/2, h/2)
    M = cv2.getRotationMatrix2D(center, angle_deg, 1.0)
    cos = abs(M[0,0]); sin = abs(M[0,1])
    new_w = int((h * sin) + (w * cos))
    new_h = int((h * cos) + (w * sin))
    M[0,2] += (new_w/2) - center[0]; M[1,2] += (new_h/2) - center[1]
    return cv2.warpAffine(img, M, (new_w, new_h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0,0,0,0))

def resize_preserve_aspect_rgba(img, target_w=None, target_h=None):
    if img is None:
        return None
    h,w = img.shape[:2]
    if target_w is not None:
        scale = target_w / w
    else:
        scale = target_h / h
    nw = max(1, int(w*scale)); nh = max(1, int(h*scale))
    return cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)

def get_set_feedback(set_score):
    if set_score == 0:
        return "Let’s get started — focus on controlled twists."
    elif set_score <= 3:
        return "Nice start — try holding the twist a bit longer."
    elif set_score <= 6:
        return "Good effort — control and balance improving."
    elif set_score < POINTS_PER_SET:
        return "Strong set — maintain this consistency."
    else:
        return "Excellent! Perfect control this set."


def show_rest_screen(set_no, set_score):
    start = time.time()

    while True:
        remaining = max(0, REST_DURATION - int(time.time() - start))

        img = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)
        cv2.putText(img, f"SET {set_no} COMPLETE!",
                    (350, 200), cv2.FONT_HERSHEY_SIMPLEX, 2,
                    (0, 255, 0), 4)

        cv2.putText(img, f"Set Score: {set_score}/{POINTS_PER_SET}",
                    (420, 300), cv2.FONT_HERSHEY_SIMPLEX, 1.4,
                    (255, 255, 255), 3)
        feedback = get_set_feedback(set_score)

        cv2.putText(img, feedback,
                    (300, 360),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.1,
                    (255, 215, 0),
                    3)

        cv2.putText(img, f"Next set starts in {remaining}s",
                    (400, 400), cv2.FONT_HERSHEY_SIMPLEX, 1.2,
                    (200, 200, 200), 3)

        cv2.imshow("Twist Top Game", img)
        key = cv2.waitKey(30) & 0xFF

        if key in [27, ord('q')]:
            cap.release()
            cv2.destroyAllWindows()
            pygame.quit()
            exit()

        if remaining <= 0:
            return

# ------------------ OUTPUT SCREEN ------------------
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

    display_score = final_score
    title = "Twisting Output"
    ratio = display_score / MAX_FINAL_SCORE

    if ratio == 1.0:
        desc = "Perfect — excellent control across all sets!"
    elif ratio >= 0.75:
        desc = "Outstanding — strong and consistent twisting!"
    elif ratio >= 0.5:
        desc = "Good effort — keep improving your control!"
    elif ratio > 0:
        desc = "Nice start — focus on holding twists longer."
    else:
        desc = "Let’s try again — start slow and steady."

    score_line = f"Score: {display_score}/{MAX_FINAL_SCORE}"

    desc = score_descriptions[min(display_score, POINTS_PER_SET)]

    instruction = "Press ESC or Q to exit (or ENTER to continue)"
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

    out_img = np.ones((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8) * 20
    panel_w = min(1100, FRAME_WIDTH - 200)
    panel_h = min(900, FRAME_HEIGHT - 150)
    panel_x = (FRAME_WIDTH - panel_w) // 2
    panel_y = (FRAME_HEIGHT - panel_h) // 2

    # translucent panel RGBA
    panel_rgba = np.zeros((panel_h, panel_w, 4), dtype=np.uint8)
    panel_rgba[..., 0] = 20
    panel_rgba[..., 1] = 20
    panel_rgba[..., 2] = 20
    panel_rgba[..., 3] = 220
    out_img = blend_rgba_onto_bgr(out_img, panel_rgba, (panel_x, panel_y))

    # Title
    title_surf = render_text_surface_pygame(title, OUTPUT_TITLE_FONT, fg=(255,255,255), bg_rgba=None, padding=30)
    tx = panel_x + (panel_w - title_surf.shape[1]) // 2
    ty = panel_y + 20
    out_img = blend_rgba_onto_bgr(out_img, title_surf, (tx, ty))

    # Score
    score_surf = render_text_surface_pygame(score_line, OUTPUT_SCORE_FONT, fg=(0,255,0), bg_rgba=None, padding=20)
    sx = panel_x + (panel_w - score_surf.shape[1]) // 2
    sy = ty + title_surf.shape[0] + 20
    out_img = blend_rgba_onto_bgr(out_img, score_surf, (sx, sy))

    # Description
    if desc:
        desc_surf = render_text_surface_pygame(desc, OUTPUT_DESC_FONT, fg=(212,175,55), bg_rgba=None, padding=20)
        dx = panel_x + (panel_w - desc_surf.shape[1]) // 2
        dy = sy + score_surf.shape[0] + 20
        out_img = blend_rgba_onto_bgr(out_img, desc_surf, (dx, dy))
    else:
        dy = sy + score_surf.shape[0] + 20

    # Instruction
    instr_surf = render_text_surface_pygame(instruction, OUTPUT_HINT_FONT, fg=(200,200,200), bg_rgba=None, padding=10)
    ix = panel_x + (panel_w - instr_surf.shape[1]) // 2
    iy = dy + 60
    out_img = blend_rgba_onto_bgr(out_img, instr_surf, (ix, iy))

    while True:
        cv2.imshow("Twist Top Game", out_img)
        k = cv2.waitKey(10) & 0xFF
        if k in [27, ord('q')]:
            cap.release()
            cv2.destroyAllWindows()
            pygame.font.quit()
            pygame.mixer.quit()
            exit()
        if k == 13:
            return

# ------------------ LOAD ASSETS ------------------
bg_rgba = load_rgba(BG_PATH)
left_top_rgba = load_rgba(LEFT_TOP_PATH)
right_top_rgba = load_rgba(RIGHT_TOP_PATH)
avatar_left_rgba = load_rgba(AVATAR_LEFT_PATH)
avatar_right_rgba = load_rgba(AVATAR_RIGHT_PATH)

increment_sound = None
try:
    if os.path.exists(INCREMENT_SOUND):
        increment_sound = pygame.mixer.Sound(INCREMENT_SOUND)
except Exception:
    increment_sound = None

# ------------------ POSE SETUP ------------------
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose
cap = cv2.VideoCapture(0)
cv2.namedWindow("Twist Top Game", cv2.WINDOW_NORMAL)
cv2.setWindowProperty("Twist Top Game", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

# ------------------ GAME STATE ------------------
score = 0   # score for current set


hold_count = 0
counted_this_hold = False
left_spin_counter = right_spin_counter = 0
left_spin_angle = right_spin_angle = 0.0

current_set = 1
set_scores = [0] * TOTAL_SETS
total_score = 0
set_start_time = time.time()
active_side = "left"
last_score_time = 0.0
# ------------------ MAIN LOOP ------------------
with mp_pose.Pose(min_detection_confidence=0.7, min_tracking_confidence=0.7) as pose:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(rgb)

        detected_status = None
        if results.pose_landmarks:
            lm = results.pose_landmarks.landmark
            left_shoulder = lm[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
            right_shoulder = lm[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
            left_hip = lm[mp_pose.PoseLandmark.LEFT_HIP.value]
            right_hip = lm[mp_pose.PoseLandmark.RIGHT_HIP.value]
            shoulder_x_diff = left_shoulder.x - right_shoulder.x
            hip_x_diff = left_hip.x - right_hip.x

            if shoulder_x_diff > TWIST_THRESHOLD and hip_x_diff > TWIST_THRESHOLD:
                detected_status = "Left Twist"
            elif shoulder_x_diff < -TWIST_THRESHOLD and hip_x_diff < -TWIST_THRESHOLD:
                detected_status = "Right Twist"

        # Alternation logic (only respond to active_side)
        if detected_status == f"{active_side.capitalize()} Twist":
            hold_count += 1
        else:
            if detected_status is None:
                counted_this_hold = False
            hold_count = 0

        if hold_count >= HOLD_FRAMES_REQUIRED and not counted_this_hold:
            if score < POINTS_PER_SET:
                score += 1
                set_scores[current_set - 1] = score

            counted_this_hold = True
            last_score_time = time.time()

            if active_side == "left":
                left_spin_counter = SPIN_DURATION_FRAMES
                left_spin_angle = 0.0
            else:
                right_spin_counter = SPIN_DURATION_FRAMES
                right_spin_angle = 0.0

            try:
                if increment_sound:
                    increment_sound.play()
            except Exception:
                pass

            # toggle side and require release before next count
            active_side = "right" if active_side == "left" else "left"
            hold_count = 0

        # ----- DRAW BACKGROUND -----
        if bg_rgba is not None:
            bg_bgr = cv2.cvtColor(bg_rgba, cv2.COLOR_BGRA2BGR) if bg_rgba.shape[2] == 4 else bg_rgba.copy()
            canvas = cv2.resize(bg_bgr, (w, h), interpolation=cv2.INTER_AREA)
        else:
            canvas = np.ones((h, w, 3), dtype=np.uint8) * 255

        # ----- Tops -----
        top_w = int(w * TOP_WIDTH_FRAC)
        left_top_x = int(w * LEFT_TOP_POS[0] - top_w/2)
        left_top_y = int(h * LEFT_TOP_POS[1] - top_w/2)
        right_top_x = int(w * RIGHT_TOP_POS[0] - top_w/2)
        right_top_y = int(h * RIGHT_TOP_POS[1] - top_w/2)

        def spin_and_draw(canvas_in, top_img, counter, angle, pos):
            canvas_local = canvas_in
            x, y = pos
            if counter > 0 and top_img is not None:
                angle += SPIN_SPEED_DEG_PER_FRAME
                rotated = rotate_rgba(top_img, angle)
                if rotated is not None:
                    rw, rh = rotated.shape[1], rotated.shape[0]
                    cx = x + top_w//2 - rw//2
                    cy = y + top_w//2 - rh//2
                    canvas_local = overlay_rgba_on_bgr(canvas_local, rotated, (max(0, cx), max(0, cy)))
                counter -= 1
            else:
                if top_img is not None:
                    t = resize_preserve_aspect_rgba(top_img, target_w=top_w)
                    canvas_local = overlay_rgba_on_bgr(canvas_local, t, (x, y))
            return canvas_local, counter, angle

        canvas, left_spin_counter, left_spin_angle = spin_and_draw(canvas, left_top_rgba, left_spin_counter, left_spin_angle, (left_top_x, left_top_y))
        canvas, right_spin_counter, right_spin_angle = spin_and_draw(canvas, right_top_rgba, right_spin_counter, right_spin_angle, (right_top_x, right_top_y))

        # ----- Avatar (centered, large) -----
        # choose avatar based on which side is active or spinning
        if left_spin_counter > 0 or active_side == "left":
            avatar_rgba = avatar_left_rgba
        else:
            avatar_rgba = avatar_right_rgba

        if avatar_rgba is not None:
            avatar_w = int(w * AVATAR_WIDTH_FRAC)
            av = resize_preserve_aspect_rgba(avatar_rgba, target_w=avatar_w)
            av_h, av_w = av.shape[:2]
            av_x = int(w * AVATAR_POS[0] - av_w/2)
            av_y = int(h * AVATAR_POS[1] - av_h/2)
            canvas = overlay_rgba_on_bgr(canvas, av, (av_x, av_y))

        # ----- Webcam (TOP-LEFT) -----
        small = cv2.resize(frame, (WEBCAM_W, WEBCAM_H))
        if results.pose_landmarks:
            mp_drawing.draw_landmarks(small, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
        ws_x, ws_y = 10, 10
        canvas[ws_y:ws_y+WEBCAM_H, ws_x:ws_x+WEBCAM_W] = small
        border_color = WEBCAM_BORDER_GREEN if time.time() - last_score_time <= BORDER_GREEN_DURATION else WEBCAM_BORDER_VIOLET
        cv2.rectangle(canvas, (ws_x-6, ws_y-6), (ws_x+WEBCAM_W+6, ws_y+WEBCAM_H+6), border_color, 4)

        # ----- HUD (Timer center, Score top-right) -----
        elapsed = time.time() - set_start_time
        remaining = max(0, int(SET_DURATION - elapsed))

        mins, secs = divmod(remaining, 60)
        timer_text = f"{mins:02d}:{secs:02d}"
        timer_surf = render_text_surface_pygame(timer_text, TIMER_FONT, fg=TIMER_COLOR, bg_rgba=TIMER_BG_RGBA, padding=8)
        canvas = blend_rgba_onto_bgr(canvas, timer_surf, ((w - timer_surf.shape[1])//2, 6))
        score_line = f"SET {current_set}/{TOTAL_SETS}  |  {score}/{POINTS_PER_SET}"

        score_surf = render_text_surface_pygame(score_line, SCORE_FONT, fg=SCORE_COLOR, bg_rgba=SCORE_BG_RGBA, padding=8)
        canvas = blend_rgba_onto_bgr(canvas, score_surf, (w - score_surf.shape[1] - 20, 10))

        # ----- Hint / Active side -----
        cv2.putText(canvas, f"Active: {active_side.upper()} — Twist {active_side.upper()} to score",
                    (40, h - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (230,230,230), 2, cv2.LINE_AA)

        cv2.imshow("Twist Top Game", canvas)
        key = cv2.waitKey(DISPLAY_FPS_DELAY) & 0xFF
        if key == 27 or key == ord('q'):
            break

        # termination conditions
        if remaining <= 0 or score >= POINTS_PER_SET:

            total_score += score

            if current_set < TOTAL_SETS:
                show_rest_screen(current_set, score)

                # move to next set
                current_set += 1
                score = 0
                set_start_time = time.time()
                hold_count = 0
                counted_this_hold = False
                continue

            else:
                # all sets completed
                show_output_screen(total_score)
                break


# cleanup
cap.release()
cv2.destroyAllWindows()
pygame.font.quit()
pygame.mixer.quit()
