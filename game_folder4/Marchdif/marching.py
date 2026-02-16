import cv2
import mediapipe as mp
import numpy as np

# Mediapipe setup
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

# Angle calculation
def calculate_angle(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    ba = a - b
    bc = c - b
    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
    angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))
    return np.degrees(angle)

# Suggested marching thresholds
LOWER_ANGLE = 140   # knee up
UPPER_ANGLE = 175   # leg down

# Direction flags
dir_left = 0
dir_right = 0

# Rep counters
rep_left = 0
rep_right = 0

# Consecutive frame counters
frames_left_up = 0
frames_left_down = 0
frames_right_up = 0
frames_right_down = 0
MIN_FRAMES = 3  # Minimum consecutive frames to confirm movement

# Video capture
cap = cv2.VideoCapture(0)

with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Mediapipe processing
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False
        results = pose.process(image)
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        if results.pose_landmarks:
            h, w, _ = image.shape
            lm = results.pose_landmarks.landmark

            # Draw full skeleton in RED
            mp_drawing.draw_landmarks(
                image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                mp_drawing.DrawingSpec(color=(0, 0, 255), thickness=2, circle_radius=2),
                mp_drawing.DrawingSpec(color=(0, 0, 255), thickness=2, circle_radius=2)
            )

            # Left leg joints
            hip_L = [lm[mp_pose.PoseLandmark.LEFT_HIP.value].x * w,
                     lm[mp_pose.PoseLandmark.LEFT_HIP.value].y * h]
            knee_L = [lm[mp_pose.PoseLandmark.LEFT_KNEE.value].x * w,
                      lm[mp_pose.PoseLandmark.LEFT_KNEE.value].y * h]
            ankle_L = [lm[mp_pose.PoseLandmark.LEFT_ANKLE.value].x * w,
                       lm[mp_pose.PoseLandmark.LEFT_ANKLE.value].y * h]

            # Right leg joints
            hip_R = [lm[mp_pose.PoseLandmark.RIGHT_HIP.value].x * w,
                     lm[mp_pose.PoseLandmark.RIGHT_HIP.value].y * h]
            knee_R = [lm[mp_pose.PoseLandmark.RIGHT_KNEE.value].x * w,
                      lm[mp_pose.PoseLandmark.RIGHT_KNEE.value].y * h]
            ankle_R = [lm[mp_pose.PoseLandmark.RIGHT_ANKLE.value].x * w,
                       lm[mp_pose.PoseLandmark.RIGHT_ANKLE.value].y * h]

            # Calculate raw angles
            angle_L = calculate_angle(hip_L, knee_L, ankle_L)
            angle_R = calculate_angle(hip_R, knee_R, ankle_R)

            # --- Consecutive-frame check for left leg ---
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

            # --- Consecutive-frame check for right leg ---
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

            # Draw knee lines in BLUE (raw)
            def draw_line(hip, knee, ankle):
                cv2.line(image, tuple(map(int, hip)), tuple(map(int, knee)), (255, 0, 0), 3)
                cv2.line(image, tuple(map(int, knee)), tuple(map(int, ankle)), (255, 0, 0), 3)
                cv2.circle(image, tuple(map(int, hip)), 6, (255, 0, 0), -1)
                cv2.circle(image, tuple(map(int, knee)), 6, (255, 0, 0), -1)
                cv2.circle(image, tuple(map(int, ankle)), 6, (255, 0, 0), -1)

            draw_line(hip_L, knee_L, ankle_L)
            draw_line(hip_R, knee_R, ankle_R)

            # Display real-time angles and reps
            cv2.putText(image, f"L Angle: {int(angle_L)}", (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.putText(image, f"L Reps: {rep_left}", (50, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(image, f"R Angle: {int(angle_R)}", (250, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.putText(image, f"R Reps: {rep_right}", (250, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # Optional: Knee Up debug
            if dir_left == 1:
                cv2.putText(image, "L Knee Up", (50, 110),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            if dir_right == 1:
                cv2.putText(image, "R Knee Up", (250, 110),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        cv2.imshow("Marching Counter Both Legs (Raw + Consecutive Frames)", image)

        if cv2.waitKey(10) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
