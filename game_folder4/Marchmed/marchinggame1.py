import cv2
import mediapipe as mp
import numpy as np
import pygame
import sys
import time
import os
import csv
import json
import datetime
import os, sys

# Add path to parent directory to import path_utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from path_utils import get_app_root, get_data_dir, get_game_asset_dir

# --------- RESOLVE APP ROOT DIRECTORY ---------
GAME_DIR = get_game_asset_dir('game_folder4/Marchmed')
APP_ROOT = get_data_dir()  # For CSV/JSON writes

pygame.init()

# ---------- SETTINGS ----------
info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Supermom Hydration Quest – Marching Game")

# ---------- LOAD IMAGES ----------
bg = pygame.image.load(os.path.join(GAME_DIR, "parks.png"))
bg = pygame.transform.scale(bg, (WIDTH, HEIGHT))

avatar = pygame.image.load(os.path.join(GAME_DIR, "running.png"))
avatar_w, avatar_h = int(WIDTH * 0.20), int(HEIGHT * 0.50)
avatar = pygame.transform.scale(avatar, (avatar_w, avatar_h))

bottle_img = pygame.image.load(os.path.join(GAME_DIR, "glassing.png"))
bottle_w, bottle_h = int(WIDTH * 0.04), int(HEIGHT * 0.30)
bottle_img = pygame.transform.scale(bottle_img, (bottle_w, bottle_h))

dest = pygame.image.load(os.path.join(GAME_DIR, "desti.png"))
dest_w, dest_h = int(WIDTH * 0.05), int(HEIGHT * 0.40)
dest = pygame.transform.scale(dest, (dest_w, dest_h))

# ---------- MUSIC (play on score increment) ----------
# Keep filename 156911.mp3 in same folder
step_sound = None
try:
    pygame.mixer.init()
    step_sound = pygame.mixer.Sound(os.path.join(GAME_DIR, "correct-156911.mp3"))
except Exception as e:
    step_sound = None
    # continue silently if sound cannot be loaded

# ---------- CONSTANTS ----------
# ---------- SET & REST CONSTANTS ----------
TOTAL_SETS = 4
POINTS_PER_SET = 10
MAX_POINTS = 10

SET_DURATION = 120      # seconds per set
REST_DURATION = 20      # seconds rest between sets

# ---------- MEDIAPIPE SETUP ----------
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

# ---------- HELPER: ANGLE ----------
def calculate_angle(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    ba = a - b
    bc = c - b
    denom = (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
    cosine_angle = np.dot(ba, bc) / denom
    angle = np.degrees(np.arccos(np.clip(cosine_angle, -1.0, 1.0)))
    return angle

def show_rest_screen(set_no, set_score):
    clock = pygame.time.Clock()
    start = time.time()

    title_font = pygame.font.SysFont("Arial", 72, bold=True)
    text_font = pygame.font.SysFont("Arial", 48)
    fb_font   = pygame.font.SysFont("Arial", 40)

    # Simple per‑set feedback based on score (0–8)
    if set_score <= 2:
        fb_text = "Feedback: Good start! Try to lift knees a bit higher next set."
    elif set_score <= 5:
        fb_text = "Feedback: Nice effort! Maintain rhythm and balance."
    elif set_score < MAX_POINTS:
        fb_text = "Feedback: Strong performance! Aim for all bottles next time."
    else:  # set_score == MAX_POINTS
        fb_text = "Feedback: Excellent! You collected all hydration points!"

    while True:
        elapsed = time.time() - start
        remaining = max(0, REST_DURATION - int(elapsed))

        screen.fill((20, 20, 40))

        title = title_font.render(f"Set {set_no} Complete!", True, (255, 200, 0))
        score = text_font.render(f"Set Score: {set_score}/{MAX_POINTS}", True, (0, 255, 0))
        rest  = text_font.render(f"Next set starts in {remaining}s", True, (255, 255, 255))
        fb    = fb_font.render(fb_text, True, (255, 215, 0))

        screen.blit(title, title.get_rect(center=(WIDTH//2, HEIGHT//2 - 150)))
        screen.blit(score, score.get_rect(center=(WIDTH//2, HEIGHT//2 - 40)))
        screen.blit(fb,    fb.get_rect(center=(WIDTH//2, HEIGHT//2 + 40)))
        screen.blit(rest,  rest.get_rect(center=(WIDTH//2, HEIGHT//2 + 140)))

        pygame.display.update()
        clock.tick(30)

        if remaining <= 0:
            return


# ---------- OUTPUT SCREEN FUNCTION (no webcam) ----------
def show_output_screen(final_score):
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

    title = "Marching Output"
    max_points = MAX_POINTS * TOTAL_SETS     # 12 * 4 = 48
    true_score = final_score                 # 48 when all sets done


        # Range‑based feedback on TOTAL score (0 – max_points)
    def get_final_feedback(score, max_score):
        ratio = score / max_score if max_score > 0 else 0.0

        if score == 0:
            return "Let’s try again! Start with gentle knee lifts at your own pace."
        elif ratio <= 0.25:
            return "Good start! You’ve begun your hydration quest — keep moving in the next sessions."
        elif ratio <= 0.5:
            return "Nice work! You’re building stamina and consistency with your marching."
        elif ratio <= 0.75:
            return "Great stamina! You marched strongly and stayed committed to the routine."
        elif ratio < 1.0:
            return "Almost perfect! Just a little more effort to reach full hydration quest completion."
        else:  # ratio == 1.0
            return "Excellent! You completed the hydration quest perfectly with full energy!"

    # Fonts
    title_font = pygame.font.SysFont('Arial', 72, bold=True)
    score_font = pygame.font.SysFont('Arial', 64, bold=True)
    desc_font = pygame.font.SysFont('Arial', 36)
    instr_font = pygame.font.SysFont('Arial', 28)

    clock = pygame.time.Clock()
    showing = True
    result = False  # True -> restart, False -> exit

    # Create a white box background with rounded corners look
    box_w, box_h = int(WIDTH * 0.7), int(HEIGHT * 0.6)
    box_x, box_y = (WIDTH - box_w) // 2, (HEIGHT - box_h) // 2

    # Prepare text content
    display_score = final_score              # 0 – max_points
    score_line = f"Score: {display_score}/{max_points}"
    desc = get_final_feedback(display_score, max_points)


    # ---------- SAVE RESULT TO CSV (NON-BLOCKING) ----------
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

    while showing:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                    result = False
                    showing = False
                elif event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                    result = True
                    showing = False

        # Draw overlay
        screen.fill((30, 30, 30))  # dark background

        # White box
        pygame.draw.rect(screen, (255, 255, 255), (box_x, box_y, box_w, box_h), border_radius=12)

        # Title
        title_surf = title_font.render(title, True, (0, 120, 0))
        title_rect = title_surf.get_rect(center=(WIDTH // 2, box_y + 60))
        screen.blit(title_surf, title_rect)

        # Score line
        score_surf = score_font.render(score_line, True, (0, 0, 0))
        score_rect = score_surf.get_rect(center=(WIDTH // 2, box_y + 150))
        screen.blit(score_surf, score_rect)

        # Description (wrap if too long)
        desc_lines = []
        max_line_chars = 60
        if len(desc) <= max_line_chars:
            desc_lines = [desc]
        else:
            words = desc.split()
            cur = ""
            for w in words:
                if len(cur) + len(w) + 1 <= max_line_chars:
                    cur = (cur + " " + w).strip()
                else:
                    desc_lines.append(cur)
                    cur = w
            if cur:
                desc_lines.append(cur)

        for i, line in enumerate(desc_lines):
            d_surf = desc_font.render(line, True, (40, 40, 40))
            d_rect = d_surf.get_rect(center=(WIDTH // 2, box_y + 230 + i * 40))
            screen.blit(d_surf, d_rect)

        # Instruction text
        instr = "Press ESC or Q to exit and continue strengthening exercise"
        instr_surf = instr_font.render(instr, True, (80, 80, 80))
        instr_rect = instr_surf.get_rect(center=(WIDTH // 2, box_y + box_h - 50))
        screen.blit(instr_surf, instr_rect)

        pygame.display.update()
        clock.tick(30)

    return result

# ---------- SET STATE VARIABLES ----------
current_set = 1
set_scores = [0] * TOTAL_SETS
total_score = 0

# ---------- MAIN GAME FUNCTION ----------
def run_game():
    global current_set, total_score, set_scores

    # Game parameters
    LOWER_ANGLE = 140
    UPPER_ANGLE = 160
    MIN_FRAMES = 3

    # State variables (reset at start of each set)
    path_y = 0
    step_distance = 0
    bottle_positions = []
    avatar_x = 0
    avatar_y = 0
    destination_pos = (0, 0)

    # Reset path and bottles for each set
    def reset_path_and_bottles():
        nonlocal path_y, step_distance, bottle_positions, avatar_x, avatar_y, destination_pos
        path_y = int(HEIGHT * 0.90)
        step_distance = (WIDTH - 300) // MAX_POINTS
        bottle_positions = [(200 + i * step_distance, path_y - bottle_h) for i in range(MAX_POINTS)]
        avatar_x = 10
        avatar_y = path_y - avatar_h
        destination_pos = (WIDTH - dest_w - 80, path_y - dest_h)

    # Initialize for first set
    reset_path_and_bottles()

    # Exercise counters
    dir_left = dir_right = 0
    rep_left = rep_right = 0
    frames_left_up = frames_left_down = 0
    frames_right_up = frames_right_down = 0
    total_steps = 0

    # Timing
    set_start_time = time.time()
    last_score_time = 0
    SCORE_FLASH_DURATION = 0.5
    game_over = False

    # Fonts
    big_font = pygame.font.SysFont('Arial', 70, bold=True)
    medium_font = pygame.font.SysFont('Arial', 40)

    cam_x, cam_y = 20, 20
    cam_w, cam_h = 320, 240
    border_thickness = 6

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    clock = pygame.time.Clock()

    with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
        while cap.isOpened():
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    cap.release()
                    cv2.destroyAllWindows()
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    cap.release()
                    cv2.destroyAllWindows()
                    pygame.quit()
                    sys.exit()

            # Time remaining
            elapsed = time.time() - set_start_time
            remaining = max(0, SET_DURATION - int(elapsed))
            current_set_score = set_scores[current_set - 1]

            # End current set if 12 points reached OR time is up
            if current_set_score >= MAX_POINTS or remaining <= 0:
                if current_set < TOTAL_SETS:
                    # Show rest screen for this set (12/12)
                    show_rest_screen(current_set, current_set_score)
                    current_set += 1
                    # Reset all counters for next set
                    total_steps = 0
                    rep_left = rep_right = 0
                    frames_left_up = frames_left_down = 0
                    frames_right_up = frames_right_down = 0
                    reset_path_and_bottles()
                    set_start_time = time.time()
                    continue
                else:
                    # All 4 sets done → exit game loop
                    break

            # Read frame
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape

            # Mediapipe pose
            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image.flags.writeable = False
            results = pose.process(image)
            image.flags.writeable = True
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

            angle_L = angle_R = 0.0

            if results.pose_landmarks:
                lm = results.pose_landmarks.landmark

                # Get key points
                hip_L = [lm[mp_pose.PoseLandmark.LEFT_HIP.value].x * w, lm[mp_pose.PoseLandmark.LEFT_HIP.value].y * h]
                knee_L = [lm[mp_pose.PoseLandmark.LEFT_KNEE.value].x * w, lm[mp_pose.PoseLandmark.LEFT_KNEE.value].y * h]
                ankle_L = [lm[mp_pose.PoseLandmark.LEFT_ANKLE.value].x * w, lm[mp_pose.PoseLandmark.LEFT_ANKLE.value].y * h]
                hip_R = [lm[mp_pose.PoseLandmark.RIGHT_HIP.value].x * w, lm[mp_pose.PoseLandmark.RIGHT_HIP.value].y * h]
                knee_R = [lm[mp_pose.PoseLandmark.RIGHT_KNEE.value].x * w, lm[mp_pose.PoseLandmark.RIGHT_KNEE.value].y * h]
                ankle_R = [lm[mp_pose.PoseLandmark.RIGHT_ANKLE.value].x * w, lm[mp_pose.PoseLandmark.RIGHT_ANKLE.value].y * h]

                angle_L = calculate_angle(hip_L, knee_L, ankle_L)
                angle_R = calculate_angle(hip_R, knee_R, ankle_R)

                # Left leg logic
                if angle_L < LOWER_ANGLE:
                    frames_left_up += 1
                else:
                    frames_left_up = 0
                if frames_left_up >= MIN_FRAMES and dir_left == 0:
                    dir_left = 1
                if angle_L > UPPER_ANGLE:
                    frames_left_down += 1
                else:
                    frames_left_down = 0
                if frames_left_down >= MIN_FRAMES and dir_left == 1:
                    rep_left += 1
                    dir_left = 0

                # Right leg logic
                if angle_R < LOWER_ANGLE:
                    frames_right_up += 1
                else:
                    frames_right_up = 0
                if frames_right_up >= MIN_FRAMES and dir_right == 0:
                    dir_right = 1
                if angle_R > UPPER_ANGLE:
                    frames_right_down += 1
                else:
                    frames_right_down = 0
                if frames_right_down >= MIN_FRAMES and dir_right == 1:
                    rep_right += 1
                    dir_right = 0

                # Step update (strict rep equality)
                if rep_left == rep_right and rep_left > total_steps:
                    total_steps += 1
                    total_score += 1
                    set_scores[current_set - 1] += 1

                    if step_sound:
                        step_sound.play()
                    last_score_time = time.time()

                    # Pick up first bottle
                    if bottle_positions:
                        bottle_positions.pop(0)
                        # Move avatar forward
                        avatar_x = 10 + total_steps * step_distance
                        if avatar_x > destination_pos[0] - avatar_w:
                            avatar_x = destination_pos[0] - avatar_w
    # Draw landmarks
                mp_drawing.draw_landmarks(
                    image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                    mp_drawing.DrawingSpec(color=(0,255,0), thickness=2, circle_radius=3),
                    mp_drawing.DrawingSpec(color=(255,0,0), thickness=2)
                )
            # Prepare camera surface
            small_frame = cv2.resize(image, (cam_w, cam_h))
            small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            surf = pygame.surfarray.make_surface(np.rot90(small_frame))

            # Draw scene
            screen.blit(bg, (0, 0))
            screen.blit(avatar, (avatar_x, avatar_y))
            for pos in bottle_positions:
                screen.blit(bottle_img, pos)
            screen.blit(dest, destination_pos)

            # Webcam & border
            screen.blit(surf, (cam_x, cam_y))
            now = time.time()
            if now - last_score_time <= SCORE_FLASH_DURATION:
                border_color = (0, 255, 0)
            else:
                border_color = (148, 0, 211)
            pygame.draw.rect(screen, border_color, (cam_x - border_thickness, cam_y - border_thickness,
                                                    cam_w + 2*border_thickness, cam_h + 2*border_thickness),
                             border_thickness)

            # Timer top center
            mins = remaining // 60
            secs = remaining % 60
            timer_text = big_font.render(f"{int(mins):02d}:{int(secs):02d}", True, (0,0,0))
            timer_bg_rect = timer_text.get_rect(center=(WIDTH//2, 40))
            pygame.draw.rect(screen, (255,255,255), timer_bg_rect.inflate(20,10))
            screen.blit(timer_text, timer_bg_rect.topleft)

            # Score top-right
            current_set_score = set_scores[current_set - 1]
            total_current_score = sum(set_scores)  # 0–48
            score_text = medium_font.render(
                f"SET {current_set}: {current_set_score}/{MAX_POINTS}  |  TOTAL {total_current_score}/{MAX_POINTS * TOTAL_SETS}",
                True, (0, 0, 0)
            )
            score_rect = score_text.get_rect(topright=(WIDTH - 40, 20))
            pygame.draw.rect(screen, (255,255,255), score_rect.inflate(20,12))
            screen.blit(score_text, score_rect.topleft)

            pygame.display.update()
            clock.tick(30)

            if game_over:
                break

    cap.release()
    cv2.destroyAllWindows()


    # After loop, show output screen (no webcam). If user presses ENTER, restart; if ESC or Q then exit.
    restart = show_output_screen(total_score)
    return restart


# ---------- RUN (allow restart) ----------
while True:
    restart_game = run_game()
    if restart_game:
        current_set = 1
        total_score = 0
        set_scores = [0] * TOTAL_SETS
        continue
    else:
        pygame.quit()
        sys.exit()