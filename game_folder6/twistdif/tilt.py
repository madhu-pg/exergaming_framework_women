import cv2
import mediapipe as mp

mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

cap = cv2.VideoCapture(0)

with mp_pose.Pose(min_detection_confidence=0.7,
                  min_tracking_confidence=0.7) as pose:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(rgb)

        status = "No Person"

        if results.pose_landmarks:
            lm = results.pose_landmarks.landmark

            # Shoulder landmarks
            left_shoulder = lm[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
            right_shoulder = lm[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
            shoulder_x_diff = abs(left_shoulder.x - right_shoulder.x)

            # Hip landmarks
            left_hip = lm[mp_pose.PoseLandmark.LEFT_HIP.value]
            right_hip = lm[mp_pose.PoseLandmark.RIGHT_HIP.value]
            hip_x_diff = abs(left_hip.x - right_hip.x)

            # Combine shoulders and hips with SAME thresholds as Z-plane version
            if shoulder_x_diff < 0.05 and hip_x_diff < 0.05:
                status = "Twist Detected"
            elif shoulder_x_diff > 0.15 or hip_x_diff > 0.15:
                status = "facing forward/ stable"
            else:
                status = "Neutral / Slight Shift"

            # Display X differences for debugging
            cv2.putText(frame, f'Shoulder X-diff: {shoulder_x_diff:.3f}', (40, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 200, 0), 2)
            cv2.putText(frame, f'Hip X-diff: {hip_x_diff:.3f}', (40, 100),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 200, 0), 2)

        # Display status
        cv2.putText(frame, status, (40, 140),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
        cv2.imshow("Standing Twist Detection (XY Plane)", frame)

        if cv2.waitKey(10) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
