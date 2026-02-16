import cv2
import mediapipe as mp
import math
import pygame
import sys
import time

# ---------------- INIT PYGAME ------------------
pygame.init()
WIDTH, HEIGHT = 800, 500
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Knee Bend Bunny Game")
font = pygame.font.Font(None, 36)
big_font = pygame.font.Font(None, 60)

# Load and scale background image
background = pygame.image.load("bg.jpg")
background = pygame.transform.scale(background, (WIDTH, HEIGHT))

# Load and resize bunny images
bunny_stand = pygame.image.load("stand.png")
bunny_jump = pygame.image.load("jump.png")
bunny_stand = pygame.transform.scale(bunny_stand, (120, 120))
bunny_jump = pygame.transform.scale(bunny_jump, (120, 120))

# ---------------- INIT MEDIAPIPE ------------------
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose
pose = mp_pose.Pose()

# ---------------- ANGLE FUNCTIONS ------------------
def calculate_angle_atan(a, b, c):
    a = [a.x, a.y]
    b = [b.x, b.y]
    c = [c.x, c.y]
    radians = math.atan2(c[1]-b[1], c[0]-b[0]) - math.atan2(a[1]-b[1], a[0]-b[0])
    angle = abs(radians * 180.0 / math.pi)
    return 360 - angle if angle > 180 else angle

def calculate_angle_cosine(a, b, c):
    ba = [a.x - b.x, a.y - b.y]
    bc = [c.x - b.x, c.y - b.y]

    dot_product = ba[0]*bc[0] + ba[1]*bc[1]
    magnitude_ba = math.hypot(ba[0], ba[1])
    magnitude_bc = math.hypot(bc[0], bc[1])

    if magnitude_ba == 0 or magnitude_bc == 0:
        return 0

    cosine_angle = dot_product / (magnitude_ba * magnitude_bc)
    cosine_angle = max(-1, min(1, cosine_angle))

    angle = math.acos(cosine_angle)
    return math.degrees(angle)

# ---------------- INITIAL STATE ------------------
cap = cv2.VideoCapture(0)
score = 0
knee_bent = False
ball_visible = True
game_over = False
win = False
start_time = time.time()
duration = 120  # seconds

# ---------------- MAIN LOOP ------------------
while True:
    ret, frame = cap.read()
    if not ret:
        break
    frame_rgb = cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB)
    results = pose.process(frame_rgb)

    screen.blit(background, (0, 0))
    bunny_pose = bunny_stand

    elapsed_time = int(time.time() - start_time)
    remaining_time = max(0, duration - elapsed_time)

    angle_atan = 0
    angle_cos = 0

    if not game_over and results.pose_landmarks:
        landmarks = results.pose_landmarks.landmark
        hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP]
        knee = landmarks[mp_pose.PoseLandmark.RIGHT_KNEE]
        ankle = landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE]

        angle_atan = calculate_angle_atan(hip, knee, ankle)
        angle_cos = calculate_angle_cosine(hip, knee, ankle)

        # Jump detection logic
        if angle_atan < 130:
            bunny_pose = bunny_jump
            if not knee_bent:
                score += 1
                knee_bent = True
                ball_visible = False
        elif angle_atan > 130:
            bunny_pose = bunny_stand
            knee_bent = False
            ball_visible = True

    # Game over conditions
    if score >= 15:
        game_over = True
        win = True
    elif remaining_time == 0:
        game_over = True
        win = False

    # Draw bunny
    bunny_x = 340
    bunny_y = 150
    screen.blit(bunny_pose, (bunny_x, bunny_y))

    # Draw obstacle ball
    if ball_visible and not game_over:
        ball_color = (128, 0, 128)
        ball_radius = 20
        ball_center = (bunny_x + 60, bunny_y + 120)
        pygame.draw.circle(screen, ball_color, ball_center, ball_radius)

    # Draw score and timer
    score_text = font.render(f"Reps: {score}", True, (0, 0, 0))
    time_text = font.render(f"Time Left: {remaining_time}s", True, (255, 0, 0))
    screen.blit(score_text, (10, 10))
    screen.blit(time_text, (10, 50))

    # Display angle values
    angle_atan_text = font.render(f"Atan Angle: {int(angle_atan)}°", True, (0, 100, 200))
    angle_cos_text = font.render(f"Cosine Angle: {int(angle_cos)}°", True, (200, 100, 0))
    screen.blit(angle_atan_text, (10, 90))
    screen.blit(angle_cos_text, (10, 130))

    # Show warning if angles differ too much
    if abs(angle_atan - angle_cos) > 5:
        mismatch_text = font.render("⚠️ Angles Differ!", True, (255, 0, 0))
        screen.blit(mismatch_text, (10, 170))

    # Game over display
    if game_over:
        result_text = big_font.render("You Win!" if win else "Time's Up!", True, (0, 150, 0) if win else (200, 0, 0))
        screen.blit(result_text, (WIDTH // 2 - result_text.get_width() // 2, HEIGHT // 2 - 30))

    # Event handler
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            cap.release()
            cv2.destroyAllWindows()
            pygame.quit()
            sys.exit()

    pygame.display.flip()
