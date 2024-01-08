import joblib
import numpy as np

def load_model():
    # 加载模型
    model = joblib.load('train/model/model.pkl')
    return model

label_dict = {0: 'click', 1: 'knock', 2: 'none', 3: 'open', 4: 'screen shot', 5: 'scroll down', 6: 'scroll left', 7: 'scroll right', 8:'scroll up'}

def move_check(results, control_hand=0):
    # 4号节点为大拇指 8号节点为食指指尖
    if results.multi_hand_landmarks:
        for hand_no, hand_landmarks in enumerate(results.multi_hand_landmarks):
            if hand_no != control_hand:
                continue
            # 4 8 需要贴近
            distance = (hand_landmarks.landmark[4].x - hand_landmarks.landmark[8].x) ** 2 + (hand_landmarks.landmark[4].y - hand_landmarks.landmark[8].y) ** 2 + (hand_landmarks.landmark[4].z - hand_landmarks.landmark[8].z) ** 2
            # print(distance)
            if distance > 0.0008:
                return False
            else:
                return True
                
def get_label(model, results, pose_list, track_num=15):
    max_prob = 0
    max_prob_label = 2
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
        # 打印每个标签的概率
        # 找到非none的最大概率
        for i, prob in enumerate(probabilities[0]):
            if prob > max_prob and label_dict[i] != 'none':
                # print(prob, end=' ')
                max_prob = prob
                max_prob_label = i
        if max_prob < 0.4:
            max_prob_label = 2
        if probabilities[0][0] > 0.1 and move_check(results, 0):
            max_prob_label = 0
        if probabilities[0][3] > 0.3:
            max_prob_label = 3
        # if max_prob_label != 2:
        #     print('Predicted label:', model.predict(input_data)[0], 'max_prob_label',label_dict[max_prob_label])
    
    return label_dict[max_prob_label]