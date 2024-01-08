import pyautogui
from win32 import win32api, win32gui, win32print
from win32.lib import win32con
from win32.win32api import GetSystemMetrics
import time
import threading
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from img2pose.utils import hand_angle, h_gesture
from train.utils import load_model, get_label
# move(x, y, duration=num_seconds)
# moveRel(xOffset, yOffset, duration=num_seconds)
# moveTo(x, y, duration=num_seconds)
# click(x, y, button='left')
# rightClick
# doubleClick
# dragTo
# dragRel
# drag
# mouseDown
# mouseUp
# scroll
# press
# hotkey
# typewrite



class controller():
    def __init__(self):
        self.screen_width, self.screen_height = controller.get_screen_size()
        self.real_screen_width, self.real_screen_height = controller.get_real_resolution()
        self.hand_screen_width, self.hand_screen_height = 1, 1
        self.physical_track = []
        self.move_speed = [0, 0]
        self.speed_rate = [self.real_screen_width / self.hand_screen_width, self.real_screen_height / self.hand_screen_height]
        self.calculate_cutoff = 10
        self.theta = 0.2
        self.depth_rate = 0
        self.static_pose_list = [] # 用于静态手势识别

        self.model = load_model()
        self.landmark_list = []
        self.track_pose_list = [] # 用于动态手势识别
        self.gesture_interval = 1

        self.current_state = None
        self.last_state = None
        self.last_action_time = time.time()

        self.scroll_accelleration = 1.1
        self.scroll_speed = 1
        self.scroll_max_speed = min(self.real_screen_width, self.real_screen_height) // 2

        self.drag_down = False
        pyautogui.FAILSAFE=False

    
    def get_real_resolution():
        """获取真实的分辨率"""
        hDC = win32gui.GetDC(0)
        # 横向分辨率
        w = win32print.GetDeviceCaps(hDC, win32con.DESKTOPHORZRES)
        # 纵向分辨率
        h = win32print.GetDeviceCaps(hDC, win32con.DESKTOPVERTRES)
        return w, h


    def get_screen_size():
        """获取缩放后的分辨率"""
        w = GetSystemMetrics (0)
        h = GetSystemMetrics (1)
        return w, h

    def sort_hands(self, results):
        # 左手为0，右手为1
        if results.multi_hand_landmarks:
            if len(results.multi_hand_landmarks) <= 1:
                return results
            else:
                if results.multi_hand_landmarks[0].landmark[0].x > results.multi_hand_landmarks[1].landmark[0].x:
                    results.multi_hand_landmarks[0], results.multi_hand_landmarks[1] = results.multi_hand_landmarks[1], results.multi_hand_landmarks[0]
                return results
        else:
            return results
    
    def update_static_pose(self,results):
        gesture_str = None
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                hand_local = []
                for i in range(21):
                    x = hand_landmarks.landmark[i].x * self.hand_screen_width
                    y = hand_landmarks.landmark[i].y * self.hand_screen_height
                    hand_local.append((x,y))
                if hand_local:
                    angle_list = hand_angle(hand_local)
                    gesture_str = h_gesture(angle_list)
        
        self.static_pose_list.append(gesture_str)
        if len(self.static_pose_list) > 20:
            self.static_pose_list.pop(0)
        
        if len(self.static_pose_list) < 10:
            return None
        else:
            # 按权重累计
            gesture_dict = {}
            for i in range(len(self.static_pose_list)):
                if self.static_pose_list[i] != None:
                    if self.static_pose_list[i] not in gesture_dict:
                        gesture_dict[self.static_pose_list[i]] = i / len(self.static_pose_list)
                    else:
                        gesture_dict[self.static_pose_list[i]] += i / len(self.static_pose_list)
            # 找到最大的权重
            max_weight = 0
            max_gesture = None
            for gesture in gesture_dict:
                if gesture_dict[gesture] > max_weight:
                    max_weight = gesture_dict[gesture]
                    max_gesture = gesture
            return max_gesture
    
    def update_track_pose(self, results):
        gesture = get_label(self.model, results, self.landmark_list)
        self.track_pose_list.append([gesture, time.time()])
        
        return self.track_pose_list[-1][0]
    
    def update_current_state(self, results):
        current_gesture = self.update_static_pose(results)
       
        current_track = self.update_track_pose(results)

        if self.last_action_time + self.gesture_interval < time.time() and \
            (self.current_state == 'reset' or self.current_state == None or \
             self.current_state == 'none' or current_gesture == 'five'):
            # 假设 动态手势优先级更高
            if current_track != 'none':
                self.current_state = current_track
                self.last_action_time = time.time()
            else:
                if current_gesture == 'one':
                    self.current_state = 'move'
                elif current_gesture == 'fist':
                    self.current_state = 'drag'
                elif current_gesture == 'six':
                    self.current_state = 'type write'
                    self.last_action_time = time.time() + 1
                elif current_gesture == 'two':
                    self.current_state = 'double click'
                elif current_gesture == 'five':
                    self.current_state = 'reset'
                    self.last_state = None
                    self.scroll_speed = 100
                    if self.drag_down:
                        pyautogui.mouseUp()
                        self.drag_down = False
                else:
                    self.current_state = None
                    self.scroll_speed = 100
                
    def add_physical_move_track(self, results, control_hand=0, mode = 0, control_node=8):
        root_x = 0
        root_y = 0
        root_z = 0
        
        results = self.sort_hands(results)

        self.update_current_state(results)

        # TYPE1
        if results.multi_hand_landmarks:
            if mode == 0:
                for hand_no, hand_landmarks in enumerate(results.multi_hand_landmarks):
                    if hand_no != control_hand:
                        continue
                    for landmark in hand_landmarks.landmark:
                        if landmark.HasField('visibility') and landmark.visibility < 0.5:
                            continue
                        if landmark.HasField('presence') and landmark.presence < 0.5:
                            continue
                        root_x += landmark.x
                        root_y += landmark.y
                        root_z += landmark.z
                root_x /= len(results.multi_hand_landmarks)
                root_y /= len(results.multi_hand_landmarks)
                root_z /= len(results.multi_hand_landmarks)

            elif mode == 1:
                for hand_no, hand_landmarks in enumerate(results.multi_hand_landmarks):
                    if hand_no != control_hand:
                        continue
                    root_x = hand_landmarks.landmark[control_node].x
                    root_y = hand_landmarks.landmark[control_node].y
                    root_z = hand_landmarks.landmark[control_node].z
                    
            self.physical_track.append([root_x, root_y])
            root_z = min(root_z, 2 * 1e-6)
            root_z = max(root_z, -8 * 1e-8)
            self.depth_rate = root_z * 2e7
        else :
            self.physical_track.append([None, None])
            self.depth_rate = 0
    
    def move_check(self, results, control_hand=0, mode = 0, control_node=8):
        results = self.sort_hands(results)
        # 4号节点为大拇指 8号节点为食指指尖
        if results.multi_hand_landmarks:
            for hand_no, hand_landmarks in enumerate(results.multi_hand_landmarks):
                if hand_no != control_hand:
                    continue
                # 4 8 需要贴近
                distance = (hand_landmarks.landmark[4].x - hand_landmarks.landmark[8].x) ** 2 + (hand_landmarks.landmark[4].y - hand_landmarks.landmark[8].y) ** 2 + (hand_landmarks.landmark[4].z - hand_landmarks.landmark[8].z) ** 2
                # print(distance)
                if distance > 0.0008:
                    self.move_speed = [0, 0]
                    self.physical_track = []
                    return False
                else:
                    return True

    def update_move_speed(self):
        if len(self.physical_track) < 2:
            return
        # Calculate the new speed
        calculate_track = self.physical_track[-self.calculate_cutoff:]
        # 坐标中包含None值，转换成帧数id和坐标值
        calculate_track = [[i, v] for i, v in enumerate(calculate_track) if v[0] != None]
        # 如果没有有效的坐标，直接返回
        if len(calculate_track) < 2:
            return
        # 计算速度
        calculate_speed = [0, 0]
        for i in range(len(calculate_track) - 1):
            calculate_speed[0] += (calculate_track[i + 1][1][0] - calculate_track[i][1][0]) / (calculate_track[i + 1][0] - calculate_track[i][0])
            calculate_speed[1] += (calculate_track[i + 1][1][1] - calculate_track[i][1][1]) / (calculate_track[i + 1][0] - calculate_track[i][0])
        calculate_speed[0] /= len(calculate_track) - 1
        calculate_speed[1] /= len(calculate_track) - 1
        calculate_speed[0] *= self.speed_rate[0] * (self.depth_rate + 1)
        calculate_speed[1] *= self.speed_rate[1] * (self.depth_rate + 1)

        self.move_speed[0] = self.move_speed[0] * self.theta + calculate_speed[0] * (1 - self.theta)
        self.move_speed[1] = self.move_speed[1] * self.theta + -calculate_speed[1] * (1 - self.theta)
        


    def move_mouse(self):
        time_interval = 0.1
        while True:
            try:
                start_time = time.time()
                if self.current_state == self.last_state:
                    time.sleep(time_interval)
                    continue
                t = None
                if self.current_state == 'scroll up':
                    self.scroll_speed *= self.scroll_accelleration
                    self.scroll_speed = min(self.scroll_speed, self.scroll_max_speed)
                    t = threading.Thread(target=pyautogui.scroll, args=[-int(self.scroll_speed)])
                elif self.current_state == 'scroll down':
                    self.scroll_speed *= self.scroll_accelleration
                    self.scroll_speed = min(self.scroll_speed, self.scroll_max_speed)
                    t = threading.Thread(target=pyautogui.scroll, args=[int(self.scroll_speed)])
                elif self.current_state == 'scroll left':
                    self.scroll_speed *= self.scroll_accelleration
                    self.scroll_speed = min(self.scroll_speed, self.scroll_max_speed)
                    t = threading.Thread(target=pyautogui.hscroll, args=[int(self.scroll_speed)])
                elif self.current_state == 'scroll right':
                    self.scroll_speed *= self.scroll_accelleration
                    self.scroll_speed = min(self.scroll_speed, self.scroll_max_speed)
                    t = threading.Thread(target=pyautogui.hscroll, args=[-int(self.scroll_speed)])
                elif self.current_state == 'click':
                    t = threading.Thread(target=pyautogui.click)
                    self.last_state = self.current_state
                elif self.current_state == 'right click':
                    pyautogui.rightClick()
                    self.last_state = self.current_state
                elif self.current_state == 'double click':
                    pyautogui.doubleClick()
                    self.last_state = self.current_state
                elif self.current_state == 'drag':
                    if not self.drag_down:
                        pyautogui.mouseDown()
                        self.drag_down = True
                    self.update_move_speed()
                    t = threading.Thread(target=pyautogui.moveRel, args=[self.move_speed[0], self.move_speed[1]])
                elif self.current_state == 'pause':
                    ...
                    self.last_state = self.current_state
                elif self.current_state == 'open':
                    # ctrl + z
                    t = threading.Thread(target=pyautogui.hotkey, args=['ctrl', 'z'])
                    self.last_state = self.current_state
                elif self.current_state == 'screen shot':
                    pyautogui.screenshot("screenshot.png")
                    self.last_state = self.current_state
                elif self.current_state == 'knock':
                    ...
                    self.last_state = self.current_state
                elif self.current_state == 'move':
                    self.update_move_speed()
                    # Move the mouse
                    t = threading.Thread(target=pyautogui.moveRel, args=[self.move_speed[0], self.move_speed[1]])

                elif self.current_state == 'type write':
                    pyautogui.typewrite('Hello world!')
                    self.last_state = self.current_state
                else:
                    ...
                if t:
                    t.setDaemon(True)
                    t.start()
                if time.time() - start_time < time_interval:
                    time.sleep(time_interval - (time.time() - start_time))
            except Exception as e:
                print(e)
                continue
                


    def move_monitor(self):
        # 自动启动一个新的线程，用于控制鼠标
        t = threading.Thread(target=self.move_mouse)
        t.setDaemon(True)
        t.start()