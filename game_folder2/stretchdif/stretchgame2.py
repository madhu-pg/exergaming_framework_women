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
GAME_DIR = get_game_asset_dir('game_folder2/stretchdif')
APP_ROOT = get_data_dir()  # For CSV/JSON writes

# ------------------ SETTINGS ------------------
FRAME_WIDTH, FRAME_HEIGHT = 1280, 720
NUM_IMAGES = 4                    # 2 minutes countdown
WEBCAM_W, WEBCAM_H = 320, 240

# ------------------ SET STRUCTURE (LIKE CARDIO GAME) ------------------
TOTAL_SETS = 5
SET_DURATION_SECONDS = 120
REST_DURATION_SECONDS = 25
POINTS_PER_SET = 16
MAX_SCORE = 80 # = 16 * 5


# ------------------ LOAD IMAGES ------------------
avatar_images = [
    cv2.imread(os.path.join(GAME_DIR, "image-1 (1).png"), cv2.IMREAD_UNCHANGED),
    cv2.imread(os.path.join(GAME_DIR, "image-2 (1).png"), cv2.IMREAD_UNCHANGED),
    cv2.imread(os.path.join(GAME_DIR, "image-3 (1).png"), cv2.IMREAD_UNCHANGED),
    cv2.imread(os.path.join(GAME_DIR, "image-4 (1).png"), cv2.IMREAD_UNCHANGED)
]
background = cv2.imread(os.path.join(GAME_DIR, "backgroundstretch.png"))
if background is not None:
    background = cv2.resize(background, (FRAME_WIDTH, FRAME_HEIGHT))
else:
    background = 255*np.ones((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)

# ------------------ PYGAME INIT (fonts + sound) ------------------
# Needed so pygame can create Surfaces even without visible window
try:
    pygame.mixer.init()
except Exception:
    pass
pygame.display.init()
pygame.display.set_mode((1, 1))
pygame.font.init()

# load increment sound (same filename as your previous code)
try:
    increment_sound = pygame.mixer.Sound(os.path.join(GAME_DIR, "correct-156911.mp3"))
except Exception:
    increment_sound = None

# Fonts (Pygame SysFont)
TIMER_FONT = pygame.font.SysFont("Arial", 48, bold=True)
SCORE_FONT = pygame.font.SysFont("Arial", 44, bold=True)
OUTPUT_TITLE_FONT = pygame.font.SysFont("Arial", 80, bold=True)
OUTPUT_SCORE_FONT = pygame.font.SysFont("Arial", 70, bold=True)
OUTPUT_DESC_FONT = pygame.font.SysFont("Arial", 30, bold=True)
OUTPUT_HINT_FONT = pygame.font.SysFont("Arial", 32, bold=False)

# Colors (R,G,B)
TIMER_COLOR = (255, 255, 255)
TIMER_BG_RGBA = (0, 0, 0, 180)
SCORE_COLOR = (212, 175, 55)    # gold
SCORE_BG_RGBA = (10, 30, 80, 220)
WEBCAM_BORDER_VIOLET = (148, 0, 211)  # (B,G,R) approx for OpenCV rectangle
WEBCAM_BORDER_GREEN = (0, 255, 0)
BORDER_GREEN_DURATION = 1.0

# ------------------ SCORE DESCRIPTIONS (index 0 unused; 1..12) ------------------
score_descriptions = [
    "",  # placeholder
    "Beginner — start building strength!",
    "Good effort — keep lifting the knee higher!",
    "Steady — form improving!",
    "Better — control and balance improving!",
    "Strong — consistent reps!",
    "Very Strong — excellent stability!",
    "Balanced — both legs gaining strength!",
    "Powerful — great form & control!",
    "Robust — excellent muscle engagement!",
    "Outstanding — near perfect performance!",
    "Exceptional — great endurance!",
    "Perfect — superb strengthening!"
]

# ------------------ HELPERS: render pygame text -> RGBA numpy and blend ------------------
def render_text_surface_pygame(text, font, fg=(255,255,255), bg_rgba=None, padding=12):
    """Return RGBA numpy array (H,W,4) of rendered text (Pygame Surface -> tostring)."""
    text_surf = font.render(text, True, fg)
    text_w, text_h = text_surf.get_size()
    surf_w, surf_h = text_w + 2*padding, text_h + 2*padding
    surf = pygame.Surface((surf_w, surf_h), flags=pygame.SRCALPHA, depth=32)
    surf = surf.convert_alpha()
    if bg_rgba is not None:
        # bg_rgba expected in (B,G,R,A) like earlier code; convert to (R,G,B,A)
        if len(bg_rgba) == 4:
            r, g, b, a = bg_rgba[2], bg_rgba[1], bg_rgba[0], bg_rgba[3]
        elif len(bg_rgba) == 3:
            r, g, b, a = bg_rgba[2], bg_rgba[1], bg_rgba[0], 255
        else:
            r, g, b, a = 0, 0, 0, 255
        surf.fill((r, g, b, a))
    surf.blit(text_surf, (padding, padding))
    raw = pygame.image.tostring(surf, "RGBA", False)
    arr = np.frombuffer(raw, dtype=np.uint8).reshape((surf_h, surf_w, 4))
    return arr

def blend_rgba_onto_bgr(target_bgr, src_rgba, top_left):
    """Alpha-blend RGBA numpy onto target BGR numpy at top_left (x,y)."""
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

# ------------------ AVATAR OVERLAY ------------------
def overlay_avatar(bg_img, avatar):
    if avatar is None:
        return bg_img
    h, w = avatar.shape[:2]
    x_offset = (FRAME_WIDTH - w) // 2
    y_offset = (FRAME_HEIGHT - h) // 2
    # ensure ROI fits
    if y_offset < 0 or x_offset < 0:
        return bg_img
    if avatar.shape[2] == 4:
        alpha_s = avatar[:, :, 3] / 255.0
        alpha_l = 1.0 - alpha_s
        for c in range(3):
            bg_img[y_offset:y_offset+h, x_offset:x_offset+w, c] = (
                alpha_s * avatar[:, :, c] +
                alpha_l * bg_img[y_offset:y_offset+h, x_offset:x_offset+w, c]
            )
    else:
        bg_img[y_offset:y_offset+h, x_offset:x_offset+w] = avatar
    return bg_img

# Resize avatars (scale so avatar width ~ 50% of frame width)
for i in range(len(avatar_images)):
    if avatar_images[i] is not None:
        scale = 0.5 * FRAME_WIDTH / avatar_images[i].shape[1]
        new_w = int(avatar_images[i].shape[1] * scale)
        new_h = int(avatar_images[i].shape[0] * scale)
        avatar_images[i] = cv2.resize(avatar_images[i], (new_w, new_h), interpolation=cv2.INTER_AREA)

# ------------------ POSE ANGLES ------------------
def calculate_leg_angle(hip, knee):
    """Angle of thigh to vertical (degrees). hip,knee: normalized coords or pixels."""
    hip = np.array(hip)
    knee = np.array(knee)
    v = knee - hip
    ref = np.array([0, 1])  # vertical down
    norm_v = np.linalg.norm(v)
    if norm_v == 0:
        return 0.0
    dot = np.dot(v, ref)
    angle_rad = math.acos(np.clip(dot / norm_v, -1.0, 1.0))
    return math.degrees(angle_rad)

def calculate_support_knee_angle(hip, knee, ankle):
    """Knee angle of supporting leg (0 = straight). returns 0..180 where 0 is straight."""
    hip = np.array(hip)
    knee = np.array(knee)
    ankle = np.array(ankle)
    v1 = hip - knee
    v2 = ankle - knee
    denom = np.linalg.norm(v1) * np.linalg.norm(v2)
    if denom == 0:
        return 180.0
    angle_rad = math.acos(np.clip(np.dot(v1, v2) / denom, -1.0, 1.0))
    angle_deg = math.degrees(angle_rad)
    return 180.0 - angle_deg  # straight -> 0

# ------------------ MEDIAPIPE INIT ------------------
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

cv2.namedWindow("Stretch Game", cv2.WINDOW_NORMAL)
cv2.setWindowProperty("Stretch Game", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

# ------------------ GAME STATE ------------------
# ------------------ GAME STATE ------------------
total_score = 0
current_set = 1
set_scores = [0] * TOTAL_SETS

lift_active = False
last_score_time = 0.0

# timer / rest
start_time = 0.0
timer_started = False
is_resting = False
rest_start_time = 0.0

def show_rest_screen(current_set, rest_remaining, set_scores, POINTS_PER_SET):
    out_img = background.copy()

    panel_w = 800
    panel_h = 450   # a bit taller to fit more lines
    panel_x = (FRAME_WIDTH - panel_w) // 2
    panel_y = (FRAME_HEIGHT - panel_h) // 2

    panel = np.zeros((panel_h, panel_w, 4), dtype=np.uint8)
    panel[..., :3] = 20
    panel[..., 3] = 220
    out_img = blend_rgba_onto_bgr(out_img, panel, (panel_x, panel_y))

    # Set title (current set done, next set info)
    if current_set < TOTAL_SETS:
        title = f"Set {current_set} Complete! Next: Set {current_set + 1}"
    else:
        title = f"Set {current_set} Complete!"

    # Current set score line
    current_set_score = set_scores[current_set - 1]
    score_line = f"Set {current_set} Score: {current_set_score}/{POINTS_PER_SET}"

    # Simple feedback based on set score
    if current_set_score <= 4:
        feedback_msg = "Feedback: Good start, try to lift the knee a bit higher next set."
    elif current_set_score <= 8:
        feedback_msg = "Feedback: Nice effort, maintain your balance and keep the tempo."
    elif current_set_score < POINTS_PER_SET:
        feedback_msg = "Feedback: Strong work, aim for full range and consistency."
    else:
        feedback_msg = "Feedback: Excellent! You completed all reps in this set."

    timer = f"Rest: {int(rest_remaining)}s"
    hint = "Get ready for the next set. Breathe, relax shoulders, and stay in position."

    title_surf   = render_text_surface_pygame(title,   OUTPUT_TITLE_FONT, fg=(255,255,255))
    score_surf   = render_text_surface_pygame(score_line, OUTPUT_SCORE_FONT, fg=(0,255,0))
    fb_surf      = render_text_surface_pygame(feedback_msg, OUTPUT_HINT_FONT, fg=(212,175,55))
    timer_surf   = render_text_surface_pygame(timer,   OUTPUT_SCORE_FONT, fg=(255,255,0))
    hint_surf    = render_text_surface_pygame(hint,    OUTPUT_HINT_FONT, fg=(220,220,220))

    y = panel_y + 40
    out_img = blend_rgba_onto_bgr(
        out_img,
        title_surf,
        (panel_x + (panel_w - title_surf.shape[1]) // 2, y)
    )

    y += title_surf.shape[0] + 8
    out_img = blend_rgba_onto_bgr(
        out_img,
        score_surf,
        (panel_x + (panel_w - score_surf.shape[1]) // 2, y)
    )

    y += score_surf.shape[0] + 8
    out_img = blend_rgba_onto_bgr(
        out_img,
        fb_surf,
        (panel_x + (panel_w - fb_surf.shape[1]) // 2, y)
    )

    y += fb_surf.shape[0] + 10
    out_img = blend_rgba_onto_bgr(
        out_img,
        timer_surf,
        (panel_x + (panel_w - timer_surf.shape[1]) // 2, y)
    )

    y += timer_surf.shape[0] + 10
    out_img = blend_rgba_onto_bgr(
        out_img,
        hint_surf,
        (panel_x + (panel_w - hint_surf.shape[1]) // 2, y)
    )

    return out_img


# ------------------ OUTPUT SCREEN (no webcam) ------------------
def show_output_screen(final_score):
    """Full-screen translucent panel with Pygame-rendered text (no webcam).
    This version wraps the description and ensures the instruction line never overlaps
    or falls outside the translucent panel.
    """
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
    title = "Strengthening Output"
    score_line = f"Score: {display_score}/{MAX_SCORE}"
    last_set_score = set_scores[-1]  # score of final set (0–12)
    desc = score_descriptions[last_set_score]
    instruction = "Press ESC or Q to exit and continue stretching exercise"
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

    # make panel a bit taller to avoid crowding
    panel_w = min(1100, FRAME_WIDTH - 200)
    panel_h = min(700, FRAME_HEIGHT - 150)   # keep the taller panel
    panel_x = (FRAME_WIDTH - panel_w) // 2
    panel_y = (FRAME_HEIGHT - panel_h) // 2

    # translucent panel (RGBA); stored as RGBA numpy for blending
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

    # Big Score (highlight)
    score_surf = render_text_surface_pygame(score_line, OUTPUT_SCORE_FONT, fg=(0,255,0), bg_rgba=None, padding=30)
    sx = panel_x + (panel_w - score_surf.shape[1]) // 2
    sy = ty + title_surf.shape[0] + 20
    out_img = blend_rgba_onto_bgr(out_img, score_surf, (sx, sy))

    # --- Wrap description text to fit panel width ---
    def wrap_text_to_lines(text, font, max_width, padding=20):
        """Return list of line strings that fit within max_width (considering padding)."""
        if not text:
            return []
        words = text.split()
        lines = []
        cur = ""
        for w in words:
            test = (cur + " " + w).strip() if cur else w
            # use pygame font.size to measure width of text (fast)
            text_w, _ = font.size(test)
            if text_w + 2*padding <= max_width:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines

    desc_lines = wrap_text_to_lines(desc, OUTPUT_DESC_FONT, panel_w, padding=20)

    # Render each desc line and stack them
    line_gap = 12
    current_y = sy + score_surf.shape[0] + 40  # start a bit below score
    rendered_desc_surfaces = []
    for line in desc_lines:
        surf = render_text_surface_pygame(line, OUTPUT_DESC_FONT, fg=(212,175,55), bg_rgba=None, padding=20)
        rendered_desc_surfaces.append(surf)
    # If no lines (empty desc), keep current_y unchanged
    for surf in rendered_desc_surfaces:
        w_s, h_s = surf.shape[1], surf.shape[0]
        # center, but ensure at least 10px left margin
        dx = panel_x + max((panel_w - w_s)//2, 10)
        # clamp dx so it doesn't overflow to the right
        dx = min(dx, panel_x + panel_w - w_s - 10)
        out_img = blend_rgba_onto_bgr(out_img, surf, (dx, current_y))
        current_y += h_s + line_gap

    desc_bottom_y = current_y - line_gap if rendered_desc_surfaces else (sy + score_surf.shape[0])

    # Instruction (move below description with safe padding)
    instr_surf = render_text_surface_pygame(instruction, OUTPUT_HINT_FONT, fg=(220,220,220), bg_rgba=None, padding=12)
    instr_w, instr_h = instr_surf.shape[1], instr_surf.shape[0]
    ix = panel_x + (panel_w - instr_w) // 2
    # place instruction at least 40px below description, but inside panel bottom
    desired_iy = desc_bottom_y + 40
    min_iy = panel_y + panel_h - instr_h - 40
    iy = min(desired_iy, min_iy)
    # ensure iy is not above the description_bottom_y (safety)
    iy = max(iy, desc_bottom_y + 10)
    out_img = blend_rgba_onto_bgr(out_img, instr_surf, (ix, iy))

    # show until ESC/Q (quit) or ENTER (continue)
    while True:
        cv2.imshow("Stretch Game", out_img)
        k = cv2.waitKey(10) & 0xFF
        if k == 27 or k == ord('q'):   # ESC or q -> exit
            cap.release()
            cv2.destroyAllWindows()
            pygame.font.quit()
            pygame.display.quit()
            pygame.mixer.quit()
            exit()
        if k == 13:  # ENTER -> return to main loop
            return


# ------------------ MAIN LOOP ------------------
with mp_pose.Pose(min_detection_confidence=0.6, min_tracking_confidence=0.6) as pose:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.flip(frame, 1)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(frame_rgb)

        # default angles
        angle_leg = 0.0
        angle_support = 180.0

        # choose raising_side based on current score:
        # scores 0..5 -> next increments are 1..6 => raising left, right support
        # scores 6..11 -> increments 7..12 => raising right, left support
        current_set_score = set_scores[current_set - 1]
        raising_left_first_half = (current_set_score < (POINTS_PER_SET // 2))


        if results.pose_landmarks:
            lm = results.pose_landmarks.landmark
            # normalized coords [x,y]; keep them as-is for angle math
            # LEFT landmarks
            left_hip = [lm[mp_pose.PoseLandmark.LEFT_HIP.value].x, lm[mp_pose.PoseLandmark.LEFT_HIP.value].y]
            left_knee = [lm[mp_pose.PoseLandmark.LEFT_KNEE.value].x, lm[mp_pose.PoseLandmark.LEFT_KNEE.value].y]
            left_ankle = [lm[mp_pose.PoseLandmark.LEFT_ANKLE.value].x, lm[mp_pose.PoseLandmark.LEFT_ANKLE.value].y]
            # RIGHT landmarks
            right_hip = [lm[mp_pose.PoseLandmark.RIGHT_HIP.value].x, lm[mp_pose.PoseLandmark.RIGHT_HIP.value].y]
            right_knee = [lm[mp_pose.PoseLandmark.RIGHT_KNEE.value].x, lm[mp_pose.PoseLandmark.RIGHT_KNEE.value].y]
            right_ankle = [lm[mp_pose.PoseLandmark.RIGHT_ANKLE.value].x, lm[mp_pose.PoseLandmark.RIGHT_ANKLE.value].y]

            if raising_left_first_half:
                # left leg should raise; compute left thigh angle and right support knee angle
                angle_leg = calculate_leg_angle(left_hip, left_knee)
                angle_support = calculate_support_knee_angle(right_hip, right_knee, right_ankle)
            else:
                # right leg should raise; compute right thigh angle and left support knee angle
                angle_leg = calculate_leg_angle(right_hip, right_knee)
                angle_support = calculate_support_knee_angle(left_hip, left_knee, left_ankle)

        # ------------------ GAME LOGIC: detect successful rep ------------------
        # Criteria: thigh angle between 20..60 (raised) and support knee near straight (0..15)
        if (20 <= angle_leg <= 60) and (0 <= angle_support <= 15):
            lift_active = True
        elif lift_active and (0 <= angle_leg <= 10) and (0 <= angle_support <= 15):
            if not is_resting and total_score < MAX_SCORE:
                if set_scores[current_set-1] < POINTS_PER_SET:
                    set_scores[current_set-1] += 1
                    total_score += 1
                    last_score_time = time.time()

                    try:
                        if increment_sound:
                            increment_sound.play()
                    except Exception:
                        pass
            lift_active = False


        # ------------------ BUILD FRAME ------------------
        frame_game = background.copy()
        # overlay current avatar based on lift_stage
        lift_stage = total_score % NUM_IMAGES
        frame_game = overlay_avatar(frame_game, avatar_images[lift_stage])


        # small skeletal webcam top-left
        small_frame = cv2.resize(frame, (WEBCAM_W, WEBCAM_H))
        if results.pose_landmarks:
            mp_drawing.draw_landmarks(small_frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
        ws_x, ws_y = 10, 10
        frame_game[ws_y:ws_y+WEBCAM_H, ws_x:ws_x+WEBCAM_W] = small_frame

        # webcam border color: violet normally; green for recent increment
        border_color = WEBCAM_BORDER_VIOLET
        if time.time() - last_score_time <= BORDER_GREEN_DURATION:
            border_color = WEBCAM_BORDER_GREEN
        cv2.rectangle(frame_game, (ws_x-6, ws_y-6), (ws_x+WEBCAM_W+6, ws_y+WEBCAM_H+6), border_color, thickness=6)

        # ---------- TIMER: start only when game screen first shows ----------
        # ---------- SET-BASED TIMER LOGIC ----------
        now = time.time()

        if is_resting:
            rest_elapsed = now - rest_start_time
            rest_remaining = REST_DURATION_SECONDS - rest_elapsed

            if rest_remaining <= 0:
                is_resting = False
                timer_started = False
                start_time = now
                current_set += 1

                if current_set > TOTAL_SETS:
                    show_output_screen(total_score)
                    break
            else:
                rest_img = show_rest_screen(current_set, rest_remaining, set_scores, POINTS_PER_SET)
                cv2.imshow("Stretch Game", rest_img)
                cv2.waitKey(10)
                continue


        else:
            if not timer_started:
                start_time = now
                timer_started = True

            elapsed = now - start_time
            remaining_f = SET_DURATION_SECONDS - elapsed
            # 🔥 NEW: Check if current set is maxed out
            if set_scores[current_set-1] >= POINTS_PER_SET:  # e.g., 12 points in current set
                remaining_f = 0  # force end of current set
            if remaining_f <= 0:
                if current_set < TOTAL_SETS:
                    is_resting = True
                    rest_start_time = now
                    timer_started = False
                else:
                    show_output_screen(total_score)
                    break

            remaining_f = max(0, remaining_f)
            mins = int(remaining_f) // 60
            secs = int(remaining_f) % 60
            timer_text = f"Set {current_set} - {mins:02d}:{secs:02d}"

            timer_surf = render_text_surface_pygame(
                timer_text, TIMER_FONT,
                fg=TIMER_COLOR, bg_rgba=TIMER_BG_RGBA, padding=12
            )
            tx = (FRAME_WIDTH - timer_surf.shape[1]) // 2
            ty = 10
            frame_game = blend_rgba_onto_bgr(frame_game, timer_surf, (tx, ty))


        # ---------- SCORE (top right) ----------
        # ---------- SCORE (top right) ----------
# In the main loop, change the SCORE text:
        score_text = f"Set {current_set}: {set_scores[current_set-1]}/12 | Total: {total_score}/{MAX_SCORE}"
        score_surf = render_text_surface_pygame(
            score_text, SCORE_FONT,
            fg=SCORE_COLOR, bg_rgba=SCORE_BG_RGBA, padding=10
        )
        sx = FRAME_WIDTH - score_surf.shape[1] - 20
        sy = 10
        frame_game = blend_rgba_onto_bgr(frame_game, score_surf, (sx, sy))

        # show frame
        cv2.imshow("Stretch Game", frame_game)

        # -------------- end conditions --------------

        

        if cv2.waitKey(10) & 0xFF == ord('q'):
            break

# cleanup
cap.release()
cv2.destroyAllWindows()
pygame.font.quit()
pygame.display.quit()
pygame.mixer.quit()