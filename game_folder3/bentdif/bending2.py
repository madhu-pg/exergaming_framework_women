import cv2
import mediapipe as mp
import numpy as np
import math
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
GAME_DIR = get_game_asset_dir('game_folder3/bentdif')
APP_ROOT = get_data_dir()  # For CSV/JSON writes



# ------------------ SETTINGS ------------------
FRAME_WIDTH, FRAME_HEIGHT = 1280, 720
WEBCAM_W, WEBCAM_H = 320, 220
BORDER_GREEN_DURATION = 1.0
# ------------------ SET STRUCTURE (CARDIO STYLE) ------------------
TOTAL_SETS = 5
SET_DURATION_SECONDS = 120
REST_DURATION_SECONDS = 25

POINTS_PER_SET = 16
MAX_SCORE = 80 # = 16 * 5

growth_threshold = 1     # reps needed for 1 point
progress_increment = 0.03

# ------------------ ASSETS ------------------
# Avatar images: avatar.png (left-colored), avatar1.png (right-colored)
ASSETS_DIR = os.path.dirname(os.path.abspath(__file__))

avatar_left = cv2.imread(os.path.join(ASSETS_DIR, "avatar.png"), cv2.IMREAD_UNCHANGED)
avatar_right = cv2.imread(os.path.join(ASSETS_DIR, "avatar1.png"), cv2.IMREAD_UNCHANGED)

avatar_default = avatar_left if avatar_left is not None else avatar_right

ASSETS_DIR = os.path.dirname(os.path.abspath(__file__))

obj_left = cv2.imread(os.path.join(ASSETS_DIR, "black.png"), cv2.IMREAD_UNCHANGED)
obj_left_colored = cv2.imread(os.path.join(ASSETS_DIR, "colored.png"), cv2.IMREAD_UNCHANGED)
obj_right = cv2.imread(os.path.join(ASSETS_DIR, "black - Copy.png"), cv2.IMREAD_UNCHANGED)
obj_right_colored = cv2.imread(os.path.join(ASSETS_DIR, "colored - Copy.png"), cv2.IMREAD_UNCHANGED)

ASSETS_DIR = os.path.dirname(os.path.abspath(__file__))

background = cv2.imread(os.path.join(ASSETS_DIR, "background.png"))

if background is not None:
    background = cv2.resize(background, (FRAME_WIDTH, FRAME_HEIGHT))
else:
    background = 255 * np.ones((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)

# ------------------ PYGAME (fonts + sound) ------------------
try:
    pygame.mixer.init()
except Exception:
    pass
pygame.display.init()
pygame.display.set_mode((1, 1))   # tiny hidden window so surfaces work
pygame.font.init()

# Load increment sound (same filename used previously)
increment_sound = None
try:
    if os.path.exists("correct-156911.mp3"):
        increment_sound = pygame.mixer.Sound("correct-156911.mp3")
except Exception:
    increment_sound = None

# Fonts (Pygame)
TIMER_FONT = pygame.font.SysFont("Arial", 48, bold=True)
SCORE_FONT = pygame.font.SysFont("Arial", 44, bold=True)
OUTPUT_TITLE_FONT = pygame.font.SysFont("Arial", 80, bold=True)
OUTPUT_SCORE_FONT = pygame.font.SysFont("Arial", 80, bold=True)
OUTPUT_DESC_FONT = pygame.font.SysFont("Arial", 44, bold=True)
OUTPUT_HINT_FONT = pygame.font.SysFont("Arial", 32, bold=False)

# Colors (R,G,B)
TIMER_COLOR = (255, 255, 255)
TIMER_BG_RGBA = (0, 0, 0, 180)
SCORE_COLOR = (212, 175, 55)
SCORE_BG_RGBA = (10, 30, 80, 220)
WEBCAM_BORDER_VIOLET = (148, 0, 211)  # BGR when used with OpenCV rect
WEBCAM_BORDER_GREEN = (0, 255, 0)

# ------------------ SCORE DESCRIPTIONS (index 0 unused; 1..10) ------------------
score_descriptions = [
    "",
    "Nice start — keep going!",
    "Good — bending with control!",
    "Steady — balance improving!",
    "Strong — form getting better!",
    "Solid — consistent reps!",
    "Very strong — great stability!",
    "Powerful — excellent technique!",
    "Outstanding — high control!",
    "Exceptional — near perfect!",
    "Perfect — superb performance!"
]

# ------------------ HELPERS: pygame text -> RGBA numpy and blend ------------------
def render_text_surface_pygame(text, font, fg=(255,255,255), bg_rgba=None, padding=10):
    surf_text = font.render(text, True, fg)
    w, h = surf_text.get_size()
    surf_w, surf_h = w + 2*padding, h + 2*padding
    surf = pygame.Surface((surf_w, surf_h), flags=pygame.SRCALPHA, depth=32)
    surf = surf.convert_alpha()
    if bg_rgba is not None:
        # bg_rgba given as (B,G,R,A) -> convert to (R,G,B,A)
        if len(bg_rgba) == 4:
            r, g, b, a = bg_rgba[2], bg_rgba[1], bg_rgba[0], bg_rgba[3]
        elif len(bg_rgba) == 3:
            r, g, b, a = bg_rgba[2], bg_rgba[1], bg_rgba[0], 255
        else:
            r, g, b, a = 0, 0, 0, 255
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

# ------------------ IMAGE OVERLAY (RGBA aware) ------------------
def overlay_image(bg, fg, x, y, scale=1.0):
    if fg is None:
        return bg
    fg_h, fg_w = fg.shape[:2]
    new_w = max(1, int(fg_w * scale))
    new_h = max(1, int(fg_h * scale))
    fg_resized = cv2.resize(fg, (new_w, new_h), interpolation=cv2.INTER_AREA)
    h, w = fg_resized.shape[:2]
    if x < 0: x = 0
    if y < 0: y = 0
    if x >= bg.shape[1] or y >= bg.shape[0]:
        return bg
    if x + w > bg.shape[1]:
        w = bg.shape[1] - x
        fg_resized = fg_resized[:, :w]
    if y + h > bg.shape[0]:
        h = bg.shape[0] - y
        fg_resized = fg_resized[:h, :]
    if fg_resized.shape[2] == 4:
        alpha = fg_resized[:, :, 3] / 255.0
        for c in range(3):
            bg[y:y+h, x:x+w, c] = alpha * fg_resized[:, :, c] + (1-alpha) * bg[y:y+h, x:x+w, c]
    else:
        bg[y:y+h, x:x+w] = fg_resized
    return bg

def blend_object(uncolored, colored, progress):
    if uncolored is None or colored is None:
        return uncolored if colored is None else colored
    # clamp progress 0..1
    p = float(max(0.0, min(1.0, progress)))
    return cv2.addWeighted(colored, p, uncolored, 1.0 - p, 0)

# ------------------ ANGLE / GAME HELPERS ------------------
def calculate_angle(a, b, c):
    a = np.array(a); b = np.array(b); c = np.array(c)
    radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
    angle = np.abs(radians*180.0/np.pi)
    if angle > 180.0:
        angle = 360.0 - angle
    return angle

# ------------------ MEDIAPIPE SETUP ------------------
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

cv2.namedWindow("Stretch Painting Game", cv2.WINDOW_NORMAL)
cv2.setWindowProperty("Stretch Painting Game", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

# ------------------ GAME STATE ------------------
left_progress = 0.0
right_progress = 0.0
left_score_sub = 0
right_score_sub = 0
overall_score = 0
active_side = "left"   # start with left active
progress_increment = progress_increment
last_score_time = 0.0
current_set = 1
set_scores = [0] * TOTAL_SETS

rep_counter = 0
is_resting = False
rest_start_time = 0.0
show_set_screen = False
set_screen_start_time = 0.0
SET_SCREEN_DURATION = 3   # seconds


# Timer control
start_time = time.time()
timer_started = False
  # we start timer immediately (can change to start on first frame if needed)


STRETCH_ANGLE_THRESHOLD = 160  # smaller = more leaning

# ------------------ OUTPUT SCREEN (no webcam) ------------------
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
    title = "Stretching Output"
    score_line = f"Score: {display_score}/{MAX_SCORE}"

    desc = score_descriptions[display_score] if 0 < display_score <= MAX_SCORE else ""
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

    out_img = background.copy()

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
    score_surf = render_text_surface_pygame(score_line, OUTPUT_SCORE_FONT, fg=(0,255,0), bg_rgba=None, padding=30)
    sx = panel_x + (panel_w - score_surf.shape[1]) // 2
    sy = ty + title_surf.shape[0] + 20
    out_img = blend_rgba_onto_bgr(out_img, score_surf, (sx, sy))

    # Desc (wrap to lines to fit)
    def wrap_text_to_lines(text, font, max_w, padding=20):
        if not text:
            return []
        words = text.split()
        lines = []
        cur = ""
        for w in words:
            test = (cur + " " + w).strip() if cur else w
            text_w, _ = font.size(test)
            if text_w + 2*padding <= max_w:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines

    desc_lines = wrap_text_to_lines(desc, OUTPUT_DESC_FONT, panel_w, padding=20)
    current_y = sy + score_surf.shape[0] + 40
    for line in desc_lines:
        surf = render_text_surface_pygame(line, OUTPUT_DESC_FONT, fg=(212,175,55), bg_rgba=None, padding=20)
        dx = panel_x + max((panel_w - surf.shape[1])//2, 10)
        dx = min(dx, panel_x + panel_w - surf.shape[1] - 10)
        out_img = blend_rgba_onto_bgr(out_img, surf, (dx, current_y))
        current_y += surf.shape[0] + 12

    desc_bottom_y = current_y - 12 if desc_lines else (sy + score_surf.shape[0])

    # Instruction placement
    instr_surf = render_text_surface_pygame(instruction, OUTPUT_HINT_FONT, fg=(220,220,220), bg_rgba=None, padding=12)
    ix = panel_x + (panel_w - instr_surf.shape[1]) // 2
    desired_iy = desc_bottom_y + 40
    min_iy = panel_y + panel_h - instr_surf.shape[0] - 40
    iy = min(desired_iy, min_iy)
    iy = max(iy, desc_bottom_y + 10)
    out_img = blend_rgba_onto_bgr(out_img, instr_surf, (ix, iy))

    # wait for ESC/Q or ENTER
    while True:
        cv2.imshow("Stretch Painting Game", out_img)
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
def show_set_completion_screen(set_no, set_score):
    screen = background.copy()

    text1 = f"SET {set_no} COMPLETED"
    text2 = f"Total Score: {overall_score}/{MAX_SCORE}"
    text3 = "Get Ready for Next Set"

    surf1 = render_text_surface_pygame(text1, OUTPUT_TITLE_FONT, (255,255,255), None, 20)
    surf2 = render_text_surface_pygame(text2, OUTPUT_DESC_FONT, (0,255,0), None, 20)
    surf3 = render_text_surface_pygame(text3, OUTPUT_HINT_FONT, (200,200,200), None, 10)

    screen = blend_rgba_onto_bgr(screen, surf1, ((FRAME_WIDTH - surf1.shape[1])//2, 220))
    screen = blend_rgba_onto_bgr(screen, surf2, ((FRAME_WIDTH - surf2.shape[1])//2, 330))
    screen = blend_rgba_onto_bgr(screen, surf3, ((FRAME_WIDTH - surf3.shape[1])//2, 420))

    cv2.imshow("Stretch Painting Game", screen)
    cv2.waitKey(1)
    
def show_rest_screen(current_set, next_set, set_score, rest_remaining):
    out_img = background.copy()

    panel_w = min(1000, FRAME_WIDTH - 200)
    panel_h = min(650, FRAME_HEIGHT - 200)
    panel_x = (FRAME_WIDTH - panel_w) // 2
    panel_y = (FRAME_HEIGHT - panel_h) // 2

    panel_rgba = np.zeros((panel_h, panel_w, 4), dtype=np.uint8)
    panel_rgba[..., :3] = 20
    panel_rgba[..., 3] = 220
    out_img = blend_rgba_onto_bgr(out_img, panel_rgba, (panel_x, panel_y))

    title = f"SET {current_set} COMPLETED"
    score_text = f"Set Score: {set_score}/{POINTS_PER_SET}"
    desc = score_descriptions[min(set_score, len(score_descriptions)-1)]
    next_text = f"Next Set ({next_set}) starts in"
    countdown = f"{int(rest_remaining)} s"

    title_surf = render_text_surface_pygame(title, OUTPUT_TITLE_FONT, (255,255,255), None, 25)
    score_surf = render_text_surface_pygame(score_text, OUTPUT_SCORE_FONT, (0,255,0), None, 25)
    desc_surf = render_text_surface_pygame(desc, OUTPUT_DESC_FONT, (212,175,55), None, 20)
    next_surf = render_text_surface_pygame(next_text, OUTPUT_HINT_FONT, (220,220,220), None, 15)
    time_surf = render_text_surface_pygame(countdown, TIMER_FONT, (255,255,0), None, 15)

    y = panel_y + 10
    for surf in [title_surf, score_surf, desc_surf, next_surf, time_surf]:
        x = panel_x + (panel_w - surf.shape[1]) // 2
        out_img = blend_rgba_onto_bgr(out_img, surf, (x, y))
        y += surf.shape[0] + 10

    return out_img



# ------------------ MAIN LOOP ------------------
with mp_pose.Pose(min_detection_confidence=0.7, min_tracking_confidence=0.7) as pose:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.flip(frame, 1)
        h_frame, w_frame = frame.shape[:2]

        # resize background and start frame
        game_frame = cv2.resize(background, (w_frame, h_frame))

        # overlay avatar depending on active_side
        avatar_to_draw = avatar_left if active_side == "left" else avatar_right
        # scale avatar to fit nicely (MATCHED to simple script: multiplier 0.8)
        if avatar_to_draw is not None:
            scale_a = min(w_frame / avatar_to_draw.shape[1] * 0.8, h_frame / avatar_to_draw.shape[0] * 0.8)
            ax = w_frame // 2 - int(avatar_to_draw.shape[1] * scale_a / 2)
            ay = h_frame // 2 - int(avatar_to_draw.shape[0] * scale_a / 2)
            game_frame = overlay_image(game_frame, avatar_to_draw, ax, ay, scale=scale_a)

        # object positions and scalings (butterfly/object scale fixed to 0.2)
        obj_scale = 0.4
        move_offset = int(w_frame * 0.05)
        left_x = int(w_frame * 0.01) - move_offset
        left_y = h_frame // 2 - int(obj_left.shape[0] * obj_scale / 2)
        right_x = int(w_frame * 0.70) - move_offset
        right_y = h_frame // 2 - int(obj_right.shape[0] * obj_scale / 2)

        # pose detection
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(img_rgb)

        try:
            lm = results.pose_landmarks.landmark

            left_shoulder = [lm[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x * w_frame,
                             lm[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y * h_frame]
            left_hip = [lm[mp_pose.PoseLandmark.LEFT_HIP.value].x * w_frame,
                        lm[mp_pose.PoseLandmark.LEFT_HIP.value].y * h_frame]
            left_knee = [lm[mp_pose.PoseLandmark.LEFT_KNEE.value].x * w_frame,
                         lm[mp_pose.PoseLandmark.LEFT_KNEE.value].y * h_frame]

            right_shoulder = [lm[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x * w_frame,
                              lm[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y * h_frame]
            right_hip = [lm[mp_pose.PoseLandmark.RIGHT_HIP.value].x * w_frame,
                         lm[mp_pose.PoseLandmark.RIGHT_HIP.value].y * h_frame]
            right_knee = [lm[mp_pose.PoseLandmark.RIGHT_KNEE.value].x * w_frame,
                          lm[mp_pose.PoseLandmark.RIGHT_KNEE.value].y * h_frame]

            left_angle = calculate_angle(left_shoulder, left_hip, left_knee)
            right_angle = calculate_angle(right_shoulder, right_hip, right_knee)

            # sequential coloring logic from your original:
            if active_side == "left":
                # detect left bending (angle smaller means bent)
                if left_angle < STRETCH_ANGLE_THRESHOLD and left_score_sub < 1:
                    left_progress = min(1.0, left_progress + progress_increment)
                    if left_progress >= 1.0:
                        left_score_sub = 1
                        left_progress = 0.0
                        active_side = "right"
            else:
                if right_angle < STRETCH_ANGLE_THRESHOLD and right_score_sub < 1:
                    right_progress = min(1.0, right_progress + progress_increment)
                    if right_progress >= 1.0:
                        right_score_sub = 1
                        right_progress = 0.0
                        active_side = "left"

            # update overall score when either subscore completed
            if left_score_sub == 1 or right_score_sub == 1:

                rep_counter += 1   # count completed reps

                left_score_sub = 0
                right_score_sub = 0
                left_progress = 0.0
                right_progress = 0.0

                if rep_counter >= growth_threshold:
                    if not is_resting and overall_score < MAX_SCORE:
                        if set_scores[current_set - 1] < POINTS_PER_SET:
                            set_scores[current_set - 1] += 1
                            overall_score += 1
                            last_score_time = time.time()

                            # ---- SET COMPLETED ----
                            if set_scores[current_set - 1] >= POINTS_PER_SET:
                                show_set_screen = True
                                set_screen_start_time = time.time()
                                timer_started = False

                            if increment_sound:
                                increment_sound.play()

                    rep_counter = 0
       
        except Exception:
            # no landmarks or processing error
            pass

        # blended objects
        blended_left = blend_object(obj_left, obj_left_colored, left_progress)
        blended_right = blend_object(obj_right, obj_right_colored, right_progress)
        game_frame = overlay_image(game_frame, blended_left, left_x, left_y, scale=obj_scale)
        game_frame = overlay_image(game_frame, blended_right, right_x, right_y, scale=obj_scale)

        # active side indicator arrow
        indicator_color = (0, 255, 255)
        indicator_thickness = 4
        if active_side == "left":
            start = (left_x + int(obj_left.shape[1]*obj_scale/2), left_y - 60)
            end = (left_x + int(obj_left.shape[1]*obj_scale/2), left_y)
            cv2.arrowedLine(game_frame, start, end, indicator_color, indicator_thickness, tipLength=0.5)
        else:
            start = (right_x + int(obj_right.shape[1]*obj_scale/2), right_y - 60)
            end = (right_x + int(obj_right.shape[1]*obj_scale/2), right_y)
            cv2.arrowedLine(game_frame, start, end, indicator_color, indicator_thickness, tipLength=0.5)

        # small skeletal webcam top-left
        small_frame = cv2.resize(frame, (WEBCAM_W, WEBCAM_H))
        if results.pose_landmarks:
            mp_drawing.draw_landmarks(small_frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
        ws_x, ws_y = 10, 10
        game_frame[ws_y:ws_y+WEBCAM_H, ws_x:ws_x+WEBCAM_W] = small_frame

        # webcam border violet normally, green flash on increment
        border_color = WEBCAM_BORDER_VIOLET
        if time.time() - last_score_time <= BORDER_GREEN_DURATION:
            border_color = WEBCAM_BORDER_GREEN
        cv2.rectangle(game_frame, (ws_x-6, ws_y-6), (ws_x+WEBCAM_W+6, ws_y+WEBCAM_H+6), border_color, thickness=6)

        # ---------- TIMER (pygame rendered, top centre) ----------
        now = time.time()

        if show_set_screen:
            show_set_completion_screen(current_set, set_scores[current_set - 1])

            if time.time() - set_screen_start_time >= SET_SCREEN_DURATION:
                show_set_screen = False
                is_resting = True
                rest_start_time = time.time()
            continue

      

        if is_resting:
            rest_elapsed = now - rest_start_time
            rest_remaining = REST_DURATION_SECONDS - rest_elapsed

            if rest_remaining <= 0:
                is_resting = False
                timer_started = False
                start_time = now
                current_set += 1

                if current_set > TOTAL_SETS:
                    show_output_screen(overall_score)
                    break
            else:
                rest_img = show_rest_screen(
                    current_set=current_set,
                    next_set=current_set + 1,
                    set_score=set_scores[current_set - 1],
                    rest_remaining=rest_remaining
                )

                cv2.imshow("Stretch Painting Game", rest_img)
                cv2.waitKey(10)
                continue


        else:
            if not timer_started:
                start_time = now
                timer_started = True

            elapsed = now - start_time
            remaining = SET_DURATION_SECONDS - elapsed

            if remaining <= 0:
                if current_set < TOTAL_SETS:
                    is_resting = True
                    rest_start_time = now
                    timer_started = False
                else:
                    show_output_screen(overall_score)
                    break

            remaining = max(0, remaining)
            mins, secs = divmod(int(remaining), 60)
            timer_text = f"Set {current_set} - {mins:02d}:{secs:02d}"
            timer_surf = render_text_surface_pygame(
            timer_text, TIMER_FONT, fg=TIMER_COLOR, bg_rgba=TIMER_BG_RGBA, padding=12
            )
            tx = (w_frame - timer_surf.shape[1]) // 2
            ty = 10
            game_frame = blend_rgba_onto_bgr(game_frame, timer_surf, (tx, ty))

        # ---------- SCORE (pygame rendered, top right) ----------
        score_text = f"Set {current_set}: {set_scores[current_set-1]}/12"
        score_surf = render_text_surface_pygame(score_text, SCORE_FONT, fg=SCORE_COLOR, bg_rgba=SCORE_BG_RGBA, padding=10)
        sx = w_frame - score_surf.shape[1] - 20
        sy = 10
        game_frame = blend_rgba_onto_bgr(game_frame, score_surf, (sx, sy))

        # show
        cv2.imshow("Stretch Painting Game", game_frame)

        # end conditions: time up or full score or user quit
        
        
        if cv2.waitKey(10) & 0xFF == ord('q'):
            break

# cleanup
cap.release()
cv2.destroyAllWindows()
pygame.font.quit()
pygame.display.quit()
pygame.mixer.quit()
