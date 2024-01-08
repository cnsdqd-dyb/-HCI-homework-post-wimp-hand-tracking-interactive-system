import cv2
import mediapipe as mp
import time
from img2pose.img2pose import draw_hands
from control.autogui_utils import controller

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# 创建手势识别对象
hands = mp_hands.Hands(min_detection_confidence=0.6, min_tracking_confidence=0.6)

# 打开摄像头
cap = cv2.VideoCapture(0)
ctrl = controller()
ctrl.move_monitor()
while cap.isOpened():
    success, image = cap.read()
    ctrl.hand_screen_width = image.shape[1]
    ctrl.hand_screen_height = image.shape[0]
    if not success:
        print("Ignoring empty camera frame.")
        continue
    # start_time = time.time()
    image, results = draw_hands(image, hands, mp_hands, mp_drawing, mp_drawing_styles)
    # print(time.time() - start_time)
        
    ctrl.add_physical_move_track(results,mode=1)
    cv2.putText(image, str(ctrl.current_state), (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    cv2.imshow('MediaPipe Hands', image)
    if cv2.waitKey(5) & 0xFF == 27:
        break

hands.close()
cap.release()



