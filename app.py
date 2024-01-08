import cv2
import mediapipe as mp
import streamlit as st
from img2pose.img2pose import draw_hands
from control.autogui_utils import controller
from PIL import Image
import os
import time
st.set_page_config(layout="wide")
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# 在侧边栏添加选项
st.sidebar.title("Settings")
confidence = st.sidebar.slider("Confidence", 0.0, 1.0, 0.6)
mode = st.sidebar.selectbox("Control Mode", [0, 1])
scroll_mode = st.sidebar.selectbox("Scroll Mode", [0, 1])
real_resolution_w, real_resolution_h = controller.get_real_resolution()
ctrl_resolution_w, ctrl_resolution_h = controller.get_screen_size()
speed_rate_w = st.sidebar.slider("Speed Rate W", 0, int(real_resolution_w), int(real_resolution_w // 25))
speed_rate_h = st.sidebar.slider("Speed Rate H", 0, int(real_resolution_h), int(real_resolution_h // 25))
scroll_acceleration = st.sidebar.slider("Scroll Acceleration", 1.0, 1.5, 1.1)
enable_audio = st.sidebar.checkbox("Enable Audio")
enable_large_language_model = st.sidebar.checkbox("Enable Large Language Model API")

# 添加网址输入框
url = st.sidebar.text_input("URL", "https://github.com/cnsdqd-dyb/-HCI-homework-post-wimp-hand-tracking-interactive-system")

# 创建手势识别对象
hands = mp_hands.Hands(min_detection_confidence=confidence, min_tracking_confidence=confidence)

# 打开摄像头
cap = cv2.VideoCapture(0)
ctrl = controller(use_audio=enable_audio, use_llm=enable_large_language_model)
ctrl.scroll_mode = scroll_mode
ctrl.scroll_accelleration = scroll_acceleration
ctrl.speed_rate = [speed_rate_w, speed_rate_h]


col1, col2 = st.columns(2)

with col2:
# 在右侧添加一些交互组件
    st.title("Interactive Components")

    # 添加一个滑块
    slider = st.slider("Slider", 0, 100, 50)

    # 添加一个选择框
    selectbox = st.selectbox("Selectbox", ["Option 1", "Option 2", "Option 3"])

    # 添加一个复选框
    checkbox = st.checkbox("Checkbox")

    # 添加一个输入框
    text_input = st.text_input("Text Input")

    # 添加一个日期选择器
    date_input = st.date_input("Date Input")

    # 添加一个文件上传器
    file_uploader = st.file_uploader("File Uploader")

    # 添加一个颜色选择器
    color_picker = st.color_picker("Color Picker")

    # 添加一个按钮
    button = st.button("Button")

    # 添加一个单选按钮
    radio = st.radio("Radio", ["Option 1", "Option 2", "Option 3"])

    # 添加一个数字输入框
    number_input = st.number_input("Number Input")

    # 添加一个时间选择器
    time_input = st.time_input("Time Input")

    # 添加一个多行文本输入框
    text_area = st.text_area("Text Area")

    # 添加一个进度条
    progress = st.progress(0)
    for i in range(100):
        progress.progress(i + 1)

with col1:
    st.title("Hand Gesture Recognition")
    # 创建一个占位符，我们将在这里显示图像
    image_placeholder = st.empty()

    # 如果启用了音频，检查是否有音频文件
    if enable_audio:
        audio_files = [f for f in os.listdir() if f.endswith('.wav') or f.endswith('.mp3')]
        if audio_files:
            selected_audio = st.selectbox("Select an audio file", audio_files)
            st.audio(selected_audio)
        else:
            st.write("No audio files found.")

    # 创建占位符以显示控制器信息
    position_placeholder = st.empty()
    speed_placeholder = st.empty()
    status_placeholder = st.empty()
    time_cost_placeholder = st.empty()

    def get_status_icon(status):
        # 定义一个字典，其中键是状态，值是对应的Unicode字符
        status_icons = {
            'scroll up': '⬆️',
            'scroll down': '⬇️',
            'scroll left': '⬅️',
            'scroll right': '➡️',
            'click': '🖱️',
            'right click': '🖱️',
            'double click': '🖱️',
            'drag': '🖐️',
            'pause': '⏸️',
            'open': '📂',
            'screen shot': '📸',
            'knock': '👊',
            'move': '🚶',
            'type write': '⌨️'
        }

        # 返回当前状态对应的Unicode字符，如果状态不在字典中，则返回一个默认的字符
        return status_icons.get(status, '❓')

    while cap.isOpened():
        start_time = time.time()

        success, image = cap.read()
        ctrl.hand_screen_width = image.shape[1]
        ctrl.hand_screen_height = image.shape[0]
        if not success:
            print("Ignoring empty camera frame.")
            continue

        image, results = draw_hands(image, hands, mp_hands, mp_drawing, mp_drawing_styles)
            
        ctrl.add_physical_move_track(results, mode=mode)

        # 将OpenCV图像转换为PIL图像，以便Streamlit可以显示
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(image)
        
        # 在Streamlit应用中显示图像
        image_placeholder.image(image, caption=str(ctrl.current_state), use_column_width=True)

        # 更新控制器信息
        position_placeholder.markdown(f"## Control Position: {ctrl.position()}")
        speed_placeholder.text(f"Control Speed: {ctrl.move_speed}")
        status_placeholder.markdown(f"## Control Status: {ctrl.current_state}" + get_status_icon(ctrl.current_state))
        time_cost_placeholder.text(f"Time Cost: {time.time() - start_time}")

        if cv2.waitKey(5) & 0xFF == 27:
            break


hands.close()
cap.release()
