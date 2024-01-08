import cv2
import mediapipe as mp
import time
from img2pose.img2pose import draw_hands
from control.autogui_utils import controller
import json
import sys

if sys.platform.startswith('win'):
    import msvcrt
    get_char = msvcrt.getch
else:
    import termios, fcntl, sys, os
    def get_char():
        fd = sys.stdin.fileno()
        oldterm = termios.tcgetattr(fd)
        newattr = termios.tcgetattr(fd)
        newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
        termios.tcsetattr(fd, termios.TCSANOW, newattr)
        try:
            result = sys.stdin.read(1)
        except IOError:
            pass
        finally:
            termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)
        return result
    
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
idx = 0
frame_num = 0
label = "open"
# 创建手势识别对象
hands = mp_hands.Hands(min_detection_confidence=0.6, min_tracking_confidence=0.6)
# Open the video file
cap = cv2.VideoCapture(f'train/data/{label}.mp4')

# Initialize variables
last_input = None
track_list = []
result_list = []

while cap.isOpened():
    # Read the next frame
    ret, frame = cap.read()
    if not ret:
        break
    image, results = draw_hands(frame, hands, mp_hands, mp_drawing, mp_drawing_styles)
    
    if results.multi_hand_landmarks:
        if len(results.multi_hand_landmarks) > 1:
            continue
        for hand_landmarks in results.multi_hand_landmarks:
            track_list.append(hand_landmarks.landmark)
    else:
        continue
    # Show the frame
    cv2.imshow('Frame', image)

    # Ask for user input
    print(f'Frame {frame_num}:')
    user_input = get_char()
    print(user_input)
    if user_input == b'1':
        result_list.append(label)
    else:
        result_list.append('none')

    # If the user input has changed from 'true' to 'false', save the results list
    if last_input == b'1' and user_input != b'1':
        output = []
        for track, result in zip(track_list, result_list):
            output.append({
                'track': [ [landmark.x, landmark.y, landmark.z] for landmark in track ],
                'result': result
            })
        with open(f'train/json_file/{label}_{idx}.json', 'w') as f:
            json.dump(output, f)
        idx += 1
        track_list = []
        result_list = []
        frame_num = 0


    # Update the last input
    last_input = user_input
    frame_num += 1
    # Break the loop if 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
if len(track_list) > 0:
    output = []
    for track, result in zip(track_list, result_list):
        output.append({
            'track': [ [landmark.x, landmark.y, landmark.z] for landmark in track ],
            'result': result
        })
    with open(f'train/json_file/{label}_{idx}.json', 'w') as f:
        json.dump(output, f)
    idx += 1
    track_list = []
    result_list = []
    frame_num = 0
# Release the VideoCapture and VideoWriter
cap.release()

# Close all OpenCV windows
cv2.destroyAllWindows()

# scroll down #
# scroll up #
# scroll right #
# scroll left #
# knock #
# screenshot #
# open #
# click #

# move
# two
# drag
# pause
# type write