"""
多模态环境感知系统
功能：
1. 摄像头 - 人脸/物体检测
2. 手势识别 - 挥手、点头、摇头
3. 麦克风 - 音频采集
4. 屏幕截图 - 桌面捕获
5. 远程指令 - HTTP接口控制
6. 意图分析 - 保存到文档
"""

import cv2
import json
import time
import math
import threading
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from collections import deque

# --- 依赖检查 ---
try:
    from ultralytics import YOLO
except ImportError:
    print("请安装: pip install ultralytics")
    exit(1)

try:
    import pyautogui
except ImportError:
    print("请安装: pip install pyautogui")
    exit(1)

try:
    import sounddevice as sd
except ImportError:
    print("请安装: pip install sounddevice")
    exit(1)

try:
    from flask import Flask, request, jsonify
except ImportError:
    print("请安装: pip install flask")
    exit(1)

try:
    import mediapipe as mp
except ImportError:
    print("请安装: pip install mediapipe")
    exit(1)


class GestureRecognizer:
    """手势识别器"""

    def __init__(self):
        # MediaPipe Hand Landmarker (new API)
        BaseOptions = mp.tasks.BaseOptions
        HandLandmarker = mp.tasks.vision.HandLandmarker
        HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions

        hand_model_path = "B:/shixun/ai_face/hand_landmarker.task"
        hand_options = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=hand_model_path),
            num_hands=2
        )
        self.hands = HandLandmarker.create_from_options(hand_options)

        # MediaPipe Face Landmarker (new API)
        FaceLandmarker = mp.tasks.vision.FaceLandmarker
        FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions

        face_model_path = "B:/shixun/ai_face/face_landmarker.task"
        face_options = FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=face_model_path),
            num_faces=1
        )
        self.face_mesh = FaceLandmarker.create_from_options(face_options)

        # 历史记录用于判断动作
        self.hand_history = deque(maxlen=30)
        self.head_history = deque(maxlen=30)

        # 手势状态
        self.current_gesture = "none"
        self.gesture_confidence = 0.0

        # 点头/摇头参数
        self.nod_count = 0
        self.shake_count = 0
        self.last_nod_time = 0
        self.last_shake_time = 0

    def recognize_hand_gesture(self, frame: np.ndarray) -> Dict[str, Any]:
        """识别手部手势（挥手）"""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        result = self.hands.detect(mp_image)

        gesture = {
            "type": "none",
            "confidence": 0.0,
            "hand_count": 0,
            "is_waving": False
        }

        if result.hand_landmarks:
            gesture["hand_count"] = len(result.hand_landmarks)

            for hand_landmarks in result.hand_landmarks:
                wrist = hand_landmarks[0]
                index_tip = hand_landmarks[8]

                self.hand_history.append({
                    "x": wrist.x,
                    "y": wrist.y,
                    "index_x": index_tip.x,
                    "time": time.time()
                })

                if len(self.hand_history) >= 10:
                    recent = list(self.hand_history)[-10:]
                    x_positions = [h["x"] for h in recent]
                    x_range = max(x_positions) - min(x_positions)

                    if x_range > 0.15:
                        gesture["type"] = "wave"
                        gesture["confidence"] = min(0.9, x_range * 3)
                        gesture["is_waving"] = True
                        break

        return gesture

    def recognize_head_gesture(self, frame: np.ndarray) -> Dict[str, Any]:
        """识别头部动作（点头、摇头）"""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        result = self.face_mesh.detect(mp_image)

        gesture = {
            "type": "none",
            "confidence": 0.0,
            "is_nodding": False,
            "is_shaking": False
        }

        if result.face_landmarks:
            face_landmarks = result.face_landmarks[0]

            nose_tip = face_landmarks[1]
            forehead = face_landmarks[10]
            left_cheek = face_landmarks[234]
            right_cheek = face_landmarks[454]

            self.head_history.append({
                "nose_y": nose_tip.y,
                "forehead_y": forehead.y,
                "nose_x": nose_tip.x,
                "left_x": left_cheek.x,
                "right_x": right_cheek.x,
                "time": time.time()
            })

            if len(self.head_history) >= 15:
                recent = list(self.head_history)[-15:]
                nose_y_positions = [h["nose_y"] for h in recent]
                y_range = max(nose_y_positions) - min(nose_y_positions)

                direction_changes = 0
                for i in range(1, len(nose_y_positions)):
                    if i > 1:
                        prev_diff = nose_y_positions[i-1] - nose_y_positions[i-2]
                        curr_diff = nose_y_positions[i] - nose_y_positions[i-1]
                        if prev_diff * curr_diff < 0:
                            direction_changes += 1

                if direction_changes >= 3 and 0.02 < y_range < 0.15:
                    current_time = time.time()
                    if current_time - self.last_nod_time > 1.0:
                        self.nod_count += 1
                        self.last_nod_time = current_time
                        gesture["type"] = "nod"
                        gesture["confidence"] = min(0.9, direction_changes / 5)
                        gesture["is_nodding"] = True

            if len(self.head_history) >= 15:
                recent = list(self.head_history)[-15:]
                nose_x_positions = [h["nose_x"] for h in recent]
                x_range = max(nose_x_positions) - min(nose_x_positions)

                direction_changes = 0
                for i in range(1, len(nose_x_positions)):
                    if i > 1:
                        prev_diff = nose_x_positions[i-1] - nose_x_positions[i-2]
                        curr_diff = nose_x_positions[i] - nose_x_positions[i-1]
                        if prev_diff * curr_diff < 0:
                            direction_changes += 1

                if direction_changes >= 3 and 0.02 < x_range < 0.15:
                    current_time = time.time()
                    if current_time - self.last_shake_time > 1.0:
                        self.shake_count += 1
                        self.last_shake_time = current_time
                        gesture["type"] = "shake"
                        gesture["confidence"] = min(0.9, direction_changes / 5)
                        gesture["is_shaking"] = True

        return gesture

    def recognize_gesture(self, frame: np.ndarray) -> Dict[str, Any]:
        """综合手势识别"""
        hand_gesture = self.recognize_hand_gesture(frame)
        head_gesture = self.recognize_head_gesture(frame)

        # 优先级：挥手 > 点头 > 摇头
        if hand_gesture["is_waving"]:
            self.current_gesture = "wave"
            self.gesture_confidence = hand_gesture["confidence"]
            return {
                "type": "wave",
                "confidence": hand_gesture["confidence"],
                "description": "检测到挥手动作",
                "hand_count": hand_gesture["hand_count"]
            }
        elif head_gesture["is_nodding"]:
            self.current_gesture = "nod"
            self.gesture_confidence = head_gesture["confidence"]
            return {
                "type": "nod",
                "confidence": head_gesture["confidence"],
                "description": "检测到点头动作",
                "nod_count": self.nod_count
            }
        elif head_gesture["is_shaking"]:
            self.current_gesture = "shake"
            self.gesture_confidence = head_gesture["confidence"]
            return {
                "type": "shake",
                "confidence": head_gesture["confidence"],
                "description": "检测到摇头动作",
                "shake_count": self.shake_count
            }
        else:
            self.current_gesture = "none"
            self.gesture_confidence = 0.0
            return {
                "type": "none",
                "confidence": 0.0,
                "description": "未检测到手势",
                "hand_count": hand_gesture["hand_count"]
            }

    def reset_counters(self):
        """重置计数器"""
        self.nod_count = 0
        self.shake_count = 0


class EnvironmentSensor:
    """环境感知器"""

    def __init__(self, save_dir: str = None):
        if save_dir is None:
            save_dir = str(Path(__file__).parent)
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(exist_ok=True)

        # YOLO模型（强制用CPU）
        self.model = YOLO("yolov8n.pt")
        self.model.to("cpu")
        print("[系统] YOLO模型加载成功 (CPU模式)")

        # 手势识别器
        self.gesture_recognizer = GestureRecognizer()
        print("[系统] 手势识别器加载成功")

        # 摄像头
        self.camera = None
        self.camera_running = False

        # 音频参数
        self.sample_rate = 16000
        self.audio_duration = 3
        self.audio_running = False

        # 环境状态
        self.env_state = {
            "timestamp": "",
            "camera": {
                "detected_objects": [],
                "face_detected": False,
                "person_count": 0
            },
            "gesture": {
                "current": "none",
                "confidence": 0.0,
                "description": "",
                "history": []
            },
            "audio": {
                "volume_level": 0,
                "is_speaking": False,
                "audio_path": ""
            },
            "screen": {
                "screenshot_path": "",
                "resolution": ""
            },
            "intent": {
                "primary": "unknown",
                "confidence": 0.0,
                "description": ""
            }
        }

    def start_camera(self):
        """启动摄像头"""
        self.camera = cv2.VideoCapture(0)
        if not self.camera.isOpened():
            print("[错误] 无法打开摄像头")
            return False
        self.camera_running = True
        print("[摄像头] 已启动")
        return True

    def capture_frame(self) -> Optional[np.ndarray]:
        """捕获一帧"""
        if self.camera and self.camera.isOpened():
            ret, frame = self.camera.read()
            if ret:
                return frame
        return None

    def detect_objects(self, frame: np.ndarray) -> Dict[str, Any]:
        """检测物体，返回最大的人（离摄像头最近）"""
        results = self.model(frame)
        detected = {
            "objects": [],
            "person_count": 0,
            "face_detected": False,
            "largest_person_box": None,
            "largest_person_area": 0
        }

        for r in results:
            boxes = r.boxes
            if boxes is not None:
                for box in boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    name = r.names[cls]
                    detected["objects"].append({
                        "name": name,
                        "confidence": round(conf, 2)
                    })
                    if name == "person":
                        detected["person_count"] += 1
                        detected["face_detected"] = True
                        # 计算面积，找到最大的人
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        area = (x2 - x1) * (y2 - y1)
                        if area > detected["largest_person_area"]:
                            detected["largest_person_area"] = area
                            detected["largest_person_box"] = [int(x1), int(y1), int(x2), int(y2)]

        return detected

    def crop_largest_person(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """裁剪最大人物区域"""
        box = self.env_state["camera"].get("largest_person_box")
        if box is None:
            return None
        x1, y1, x2, y2 = box
        h, w = frame.shape[:2]
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(w, x2)
        y2 = min(h, y2)
        return frame[y1:y2, x1:x2]

    def detect_gesture(self, frame: np.ndarray) -> Dict[str, Any]:
        """检测手势（只分析最大人物）"""
        # 裁剪最大人物区域
        person_frame = self.crop_largest_person(frame)
        if person_frame is None or person_frame.size == 0:
            return {
                "type": "none",
                "confidence": 0.0,
                "description": "未检测到人物",
                "hand_count": 0
            }

        gesture = self.gesture_recognizer.recognize_gesture(person_frame)
        self.env_state["gesture"]["current"] = gesture["type"]
        self.env_state["gesture"]["confidence"] = gesture["confidence"]
        self.env_state["gesture"]["description"] = gesture["description"]

        # 记录手势历史
        if gesture["type"] != "none":
            self.env_state["gesture"]["history"].append({
                "time": datetime.now().isoformat(),
                "type": gesture["type"],
                "confidence": gesture["confidence"]
            })
            if len(self.env_state["gesture"]["history"]) > 10:
                self.env_state["gesture"]["history"] = self.env_state["gesture"]["history"][-10:]

        return gesture

    def capture_screenshot(self) -> str:
        """截取屏幕"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = self.save_dir / f"screen_{timestamp}.png"
        screenshot = pyautogui.screenshot()
        screenshot.save(str(filepath))
        resolution = f"{screenshot.width}x{screenshot.height}"
        self.env_state["screen"]["resolution"] = resolution
        print(f"[屏幕] 截图已保存: {filepath}")
        return str(filepath)

    def record_audio(self) -> str:
        """录制音频"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = self.save_dir / f"audio_{timestamp}.wav"

        print(f"[麦克风] 录音中... ({self.audio_duration}秒)")
        audio_data = sd.rec(
            int(self.audio_duration * self.sample_rate),
            samplerate=self.sample_rate,
            channels=1,
            dtype='float32'
        )
        sd.wait()
        print("[麦克风] 录音完成")

        # 计算音量
        volume = np.sqrt(np.mean(audio_data**2))
        self.env_state["audio"]["volume_level"] = round(float(volume), 4)
        self.env_state["audio"]["is_speaking"] = volume > 0.01

        # 保存音频
        import scipy.io.wavfile as wavfile
        wavfile.write(str(filepath), self.sample_rate, (audio_data * 32767).astype(np.int16))
        print(f"[麦克风] 音频已保存: {filepath}")
        return str(filepath)

    def analyze_intent(self) -> Dict[str, Any]:
        """分析用户意图"""
        intent = {
            "primary": "unknown",
            "confidence": 0.0,
            "description": "",
            "suggestions": []
        }

        cam = self.env_state["camera"]
        audio = self.env_state["audio"]
        gesture = self.env_state["gesture"]

        # 基于检测结果推断意图
        if cam["person_count"] > 0:
            intent["primary"] = "user_present"
            intent["confidence"] = 0.8
            intent["description"] = f"检测到 {cam['person_count']} 人"
            intent["suggestions"].append("用户在场，可进行交互")

        if audio["is_speaking"]:
            intent["primary"] = "user_speaking"
            intent["confidence"] = 0.9
            intent["description"] = "检测到语音活动"
            intent["suggestions"].append("用户正在说话，建议聆听")

        # 手势意图
        if gesture["current"] == "wave":
            intent["primary"] = "user_greeting"
            intent["confidence"] = gesture["confidence"]
            intent["description"] = "用户在挥手打招呼"
            intent["suggestions"].append("用户在打招呼，建议回应")
        elif gesture["current"] == "nod":
            intent["primary"] = "user_agreeing"
            intent["confidence"] = gesture["confidence"]
            intent["description"] = "用户在点头表示同意"
            intent["suggestions"].append("用户表示同意或确认")
        elif gesture["current"] == "shake":
            intent["primary"] = "user_disagreeing"
            intent["confidence"] = gesture["confidence"]
            intent["description"] = "用户在摇头表示不同意"
            intent["suggestions"].append("用户表示不同意或拒绝")

        if cam["person_count"] == 0 and not audio["is_speaking"] and gesture["current"] == "none":
            intent["primary"] = "no_activity"
            intent["confidence"] = 0.7
            intent["description"] = "未检测到用户活动"
            intent["suggestions"].append("用户不在或未活动")

        self.env_state["intent"] = intent
        return intent

    def save_state(self):
        """保存环境状态到JSON"""
        self.env_state["timestamp"] = datetime.now().isoformat()
        filepath = self.save_dir / "env_state.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.env_state, f, ensure_ascii=False, indent=2)
        print(f"[状态] 已保存: {filepath}")

    def save_intent(self):
        """保存意图到文档"""
        intent = self.env_state["intent"]
        gesture = self.env_state["gesture"]
        audio = self.env_state["audio"]
        filepath = self.save_dir / "data.txt"

        with open(filepath, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*50}\n")
            f.write(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"意图: {intent['primary']}\n")
            f.write(f"描述: {intent['description']}\n")

            if gesture["current"] != "none":
                f.write(f"手势: {gesture['current']} (置信度: {gesture['confidence']:.2f})\n")

            if audio.get("is_speaking"):
                f.write(f"语音: 检测到说话 (音量: {audio.get('volume_level', 0):.4f})\n")

        print(f"[记录] {intent['primary']}: {intent['description']}")

    def release(self):
        """释放资源"""
        if self.camera:
            self.camera.release()
        self.camera_running = False
        print("[系统] 资源已释放")


class RemoteController:
    """远程指令控制器"""

    def __init__(self, sensor: EnvironmentSensor, port: int = 5000):
        self.sensor = sensor
        self.app = Flask(__name__)
        self.port = port
        self._setup_routes()

    def _setup_routes(self):
        @self.app.route("/status", methods=["GET"])
        def get_status():
            return jsonify(self.sensor.env_state)

        @self.app.route("/screenshot", methods=["POST"])
        def take_screenshot():
            path = self.sensor.capture_screenshot()
            return jsonify({"status": "ok", "path": path})

        @self.app.route("/record", methods=["POST"])
        def record_audio():
            path = self.sensor.record_audio()
            return jsonify({"status": "ok", "path": path})

        @self.app.route("/detect", methods=["POST"])
        def detect():
            frame = self.sensor.capture_frame()
            if frame is not None:
                detected = self.sensor.detect_objects(frame)
                self.sensor.env_state["camera"].update(detected)
                return jsonify({"status": "ok", "detected": detected})
            return jsonify({"status": "error", "message": "无法捕获帧"})

        @self.app.route("/gesture", methods=["POST"])
        def detect_gesture():
            frame = self.sensor.capture_frame()
            if frame is not None:
                gesture = self.sensor.detect_gesture(frame)
                return jsonify({"status": "ok", "gesture": gesture})
            return jsonify({"status": "error", "message": "无法捕获帧"})

        @self.app.route("/analyze", methods=["POST"])
        def analyze():
            frame = self.sensor.capture_frame()
            if frame is not None:
                detected = self.sensor.detect_objects(frame)
                self.sensor.env_state["camera"].update(detected)
                self.sensor.detect_gesture(frame)

            intent = self.sensor.analyze_intent()
            self.sensor.save_state()
            self.sensor.save_intent()
            return jsonify({"status": "ok", "intent": intent})

        @self.app.route("/full_scan", methods=["POST"])
        def full_scan():
            """完整扫描：摄像头+手势+截图+录音+分析"""
            # 摄像头检测
            frame = self.sensor.capture_frame()
            if frame is not None:
                detected = self.sensor.detect_objects(frame)
                self.sensor.env_state["camera"].update(detected)
                self.sensor.detect_gesture(frame)

            # 截图
            self.sensor.capture_screenshot()

            # 录音
            self.sensor.record_audio()

            # 分析意图
            intent = self.sensor.analyze_intent()
            self.sensor.save_state()
            self.sensor.save_intent()

            return jsonify({
                "status": "ok",
                "state": self.sensor.env_state,
                "intent": intent
            })

    def start(self):
        print(f"[远程] HTTP服务启动: http://0.0.0.0:{self.port}")
        self.app.run(host="0.0.0.0", port=self.port, debug=False)


def main():
    print("=" * 50)
    print("多模态环境感知系统（自动检测）")
    print("=" * 50)

    sensor = EnvironmentSensor()

    if not sensor.start_camera():
        print("[错误] 无法启动摄像头")
        return

    print("[系统] 开始自动检测，按 'q' 退出")

    last_gesture = "none"
    last_speaking = False
    frame_count = 0
    audio_buffer = np.zeros(sensor.sample_rate, dtype='float32')
    audio_thread = None

    def capture_audio_nonblocking():
        nonlocal audio_buffer
        try:
            data = sd.rec(int(0.3 * sensor.sample_rate),
                         samplerate=sensor.sample_rate,
                         channels=1, dtype='float32')
            sd.wait()
            audio_buffer = data.flatten()
        except:
            pass

    try:
        while True:
            frame = sensor.capture_frame()
            if frame is None:
                continue

            frame_count += 1

            # 每3帧跑一次YOLO（降低负载）
            if frame_count % 3 == 0:
                detected = sensor.detect_objects(frame)
                sensor.env_state["camera"].update(detected)

            # 每2帧跑一次手势识别
            if frame_count % 2 == 0:
                gesture = sensor.detect_gesture(frame)
            else:
                gesture = {"type": sensor.env_state["gesture"]["current"]}

            # 非阻塞音频检测（后台线程）
            if audio_thread is None or not audio_thread.is_alive():
                audio_thread = threading.Thread(target=capture_audio_nonblocking, daemon=True)
                audio_thread.start()
                volume = np.sqrt(np.mean(audio_buffer**2)) if audio_buffer.size > 0 else 0
                is_speaking = volume > 0.01
                sensor.env_state["audio"]["is_speaking"] = is_speaking
                sensor.env_state["audio"]["volume_level"] = round(float(volume), 4)
            else:
                is_speaking = sensor.env_state["audio"]["is_speaking"]

            # 手势变化 -> 立即记录
            if gesture["type"] != "none" and gesture["type"] != last_gesture:
                sensor.env_state["gesture"]["current"] = gesture["type"]
                sensor.env_state["gesture"]["confidence"] = gesture.get("confidence", 0)
                sensor.env_state["gesture"]["description"] = gesture.get("description", "")
                intent = sensor.analyze_intent()
                sensor.save_intent()
                print(f"[检测] 手势: {gesture['type']}")

            # 说话状态变化 -> 立即记录
            if is_speaking and not last_speaking:
                sensor.env_state["gesture"]["current"] = "none"
                intent = sensor.analyze_intent()
                sensor.save_intent()
                print(f"[检测] 语音活动")

            last_gesture = gesture["type"]
            last_speaking = is_speaking

            # 显示画面
            annotated = frame.copy()
            box = sensor.env_state["camera"].get("largest_person_box")
            if box is not None:
                x1, y1, x2, y2 = box
                cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(annotated, "TARGET", (x1, y1 - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            if gesture["type"] != "none":
                cv2.putText(annotated, f"Gesture: {gesture['type']}",
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.imshow("Environment Sensor", annotated)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        pass
    finally:
        sensor.release()
        cv2.destroyAllWindows()
        print("[系统] 程序已退出")


if __name__ == "__main__":
    main()
