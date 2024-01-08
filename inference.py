import joblib

# 加载模型
model = joblib.load('train/model/model.pkl')
import cv2
import mediapipe as mp
import time
import numpy as np
from img2pose.img2pose import draw_hands

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# 创建手势识别对象
hands = mp_hands.Hands(min_detection_confidence=0.6, min_tracking_confidence=0.6)
track_num = 15
# 打开摄像头
cap = cv2.VideoCapture(0)
pose_list = []
fourcc = cv2.VideoWriter_fourcc(*'mp4v') 

while cap.isOpened():
    success, image = cap.read()
    if not success:
        print("Ignoring empty camera frame.")
        continue
    image, results = draw_hands(image, hands, mp_hands, mp_drawing, mp_drawing_styles)
    if results.multi_hand_landmarks:
        pose_list.append([ [landmark.x, landmark.y, landmark.z] for landmark in results.multi_hand_landmarks[0].landmark])
    if len(pose_list) > track_num:
        pose_list.pop(0)
    if len(pose_list) == track_num:
        input_data = [pose for pose in pose_list]
        input_data = np.array(input_data)
        input_data = input_data.reshape(1, -1)
        # 使用模型预测概率
        probabilities = model.predict_proba(input_data)
        label_dict = {0: 'click', 1: 'knock', 2: 'none', 3: 'open', 4: 'screen shot', 5: 'scroll down', 6: 'scroll left', 7: 'scroll right', 8:'scroll up'}
        # 打印每个标签的概率
        # 找到非none的最大概率
        max_prob = 0
        max_prob_label = 0
        for i, prob in enumerate(probabilities[0]):
            if prob > max_prob and label_dict[i] != 'none':
                max_prob = prob
                max_prob_label = i
        if max_prob < 0.4:
            max_prob_label = 2
        if max_prob_label != 2:
            print('Predicted label:', model.predict(input_data)[0], 'max_prob_label',label_dict[max_prob_label])
    cv2.imshow('MediaPipe Hands', image)
    if cv2.waitKey(5) & 0xFF == 27:
        break

hands.close()
cap.release()