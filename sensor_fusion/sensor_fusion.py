from DIPPID import SensorUDP
import pyglet
import numpy as np
import cv2
import cv2.aruco as aruco
import sys
from PIL import Image
import threading
import time

PORT = 5700

window = pyglet.window.Window(width=640, height=480)
frame_transformed = None
phone_marker_pos = pyglet.shapes.Circle(0, 0, 10, color=(255, 0, 0))  
predicted_marker_pos = pyglet.shapes.Circle(0, 0, 10, color=(0, 255, 0))
alpha = 0.8 

video_id = 0

if len(sys.argv) > 1:
    video_id = int(sys.argv[1])

# Create a video capture object for the webcam
cap = cv2.VideoCapture(video_id)

# Define the ArUco dictionary, parameters, and detector
aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_6X6_250)
aruco_params = aruco.DetectorParameters()
detector = aruco.ArucoDetector(aruco_dict, aruco_params)

class PosePredictor:
    def __init__(self, x, y, height, acc_rate=100):
        self.sensor = SensorUDP(PORT)
        self.sensor.register_callback('button_1', self.handle_button_press)

        self.acc_rate = acc_rate
        self.alpha = alpha

        self.cam_height = height
        self.cam_x = x
        self.cam_y = y

        self.vel = np.array([0.0, 0.0])
        self.imu_pos = np.array([x, y])

        self.running = True

        self.acc_thread = threading.Thread(target=self.handle_accelerometer, daemon=True)
        self.acc_thread.start()
        self.reset_flag = False

    def handle_button_press(self, data):
        if float(data) == 1.0:
            self.reset_flag = True

    def handle_accelerometer(self):
        # wait until accelerometer is initialized
        while 'accelerometer' not in self.sensor.get_capabilities():
            time.sleep(0.1)

        dt = 1 / self.acc_rate

        while self.running:
            if self.reset_flag:
                self.vel = np.array([0.0, 0.0])
                self.imu_pos = np.array([self.cam_x, self.cam_y])
                self.reset_flag = False

            acc = self.sensor.get_value('accelerometer')
            vel_acc = np.array([acc['x'], acc['y']])

            self.vel += vel_acc * dt
            # damping
            self.vel *= 0.98 
            
            self.imu_pos += self.vel * dt

            time.sleep(dt)

pose_predicter = None

# converts OpenCV image to PIL image and then to pyglet texture
def cv2glet(img,fmt):
    '''Assumes image is in BGR color space. Returns a pyimg object'''
    if fmt == 'GRAY':
      rows, cols = img.shape
      channels = 1
    else:
      rows, cols, channels = img.shape

    raw_img = Image.fromarray(img).tobytes()

    top_to_bottom_flag = -1
    bytes_per_row = channels*cols
    pyimg = pyglet.image.ImageData(width=cols, 
                                   height=rows, 
                                   fmt=fmt, 
                                   data=raw_img, 
                                   pitch=top_to_bottom_flag*bytes_per_row)
    return pyimg


def get_transformed_frame(corners, frame):
    # list of means to determine which aruco marker marks which corner
    means = []
    # fill the means list
    for i in range(4): 
        means.append(np.mean(corners[i][0], axis=0))

    BR, BL, TR, TL = None, None, None, None
    means_arr = np.array(means)
    # center of all aruco markers
    center = means_arr.mean(axis=0)

    # extract x and y values and sort them 
    x_values = means_arr[:, 0]
    y_values = means_arr[:, 1]
    x_values = np.sort(x_values)
    y_values = np.sort(y_values)
    
    # assign the right rectangle position
    for i in range(4):
        if means[i][0] > center[0]:
            if means[i][1] > center[1]:
                BR = i
            else:
                TR = i
        else: 
            if means[i][1] > center[1]:
                BL = i
            else: 
                TL = i

    # get the corner closest to the middle
    def inner_corner(idx):
        corners_i = corners[idx][0]
        dists = np.linalg.norm(corners_i - center, axis=1)
        return corners_i[np.argmin(dists)]

    # assign the points
    point_BL = tuple(inner_corner(BL))
    point_TL = tuple(inner_corner(TL))
    point_TR = tuple(inner_corner(TR))
    point_BR = tuple(inner_corner(BR))

    points = np.array([point_TL, point_TR, point_BR, point_BL])

    # width and height of destination are determined by resolution of webcam
    dest_width = frame.shape[1]
    dest_height = frame.shape[0]
    # destination window to transform image into
    destination = np.float32(np.array([[0, 0], [dest_width, 0], [dest_width, dest_height], [0, dest_height]]))
    # get transformation matrix
    mat = cv2.getPerspectiveTransform(points, destination)
    # transform image
    frame_transformed = cv2.warpPerspective(frame, mat, (dest_width, dest_height), flags=cv2.INTER_LINEAR)

    return frame_transformed, mat

def predict_position(x_cam, y_cam):
    global predicted_marker_pos, pose_predicter

    height = pose_predicter.cam_height

    cam = np.array([x_cam, y_cam])
    imu = pose_predicter.imu_pos

    fused = pose_predicter.alpha * cam + (1 - pose_predicter.alpha) * imu

    predicted_marker_pos.x = fused[0]
    predicted_marker_pos.y = height - fused[1]
    

def update(dt):
    global frame_transformed, pose_predicter

    # Capture a frame from the webcam
    ret, frame = cap.read()
    if not ret: 
        return
    
    # if there are less than four aruco marker, just display the camera frame
    frame_transformed = frame.copy()

    # Convert the frame to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Detect ArUco markers in the frame
    corners, ids, _ = detector.detectMarkers(gray)
    corners = np.array(corners)

    # Check if marker is detected
    if ids is not None:
        if ids.shape[0] == 4: 
            frame_transformed, _ = get_transformed_frame(corners, frame)
        elif ids.shape[0] == 5:
            pos = None
            for i in range(5):
                if ids[i] == 5:
                    pos = i
            corners_frame = corners.copy()
            if pos is not None: 
                corners_frame = np.delete(corners_frame, pos, axis=0)
            frame_transformed, mat = get_transformed_frame(corners_frame, frame)
            center = np.mean(corners[pos][0], axis=0)
            cv2_point = np.array([[[center[0], center[1]]]], dtype=np.float32)
            transformed_point = cv2.perspectiveTransform(cv2_point, mat)
            x = transformed_point[0][0][0]
            y = transformed_point[0][0][1]
            if pose_predicter is None:
                pose_predicter = PosePredictor(x, y, frame_transformed.shape[0])

            phone_marker_pos.x = x
            phone_marker_pos.y = frame_transformed.shape[0] - y

            if 'accelerometer' in pose_predicter.sensor.get_capabilities():
                predict_position(x, y)

def cleanup():
    global pose_predicter
    if pose_predicter:
        pose_predicter.running = False
        pose_predicter.acc_thread.join()
    cap.release

@window.event
def on_close():
    cleanup()
    pyglet.app.exit()

@window.event
def on_key_press(symbol, modifiers):
    global pose_predicter

    if symbol == pyglet.window.key.UP:
        pose_predicter.alpha = min(0.99, pose_predicter.alpha + 0.02)

    if symbol == pyglet.window.key.DOWN:
        pose_predicter.alpha = max(0.0, pose_predicter.alpha - 0.02)

    # close the window when key 'q' is pressed
    if symbol == pyglet.window.key.Q:
        window.close()

@window.event
def on_draw():
    window.clear()

    if frame_transformed is not None: 
        img = cv2glet(frame_transformed, 'BGR')
        img.blit(0, 0)
    
    phone_marker_pos.draw()
    predicted_marker_pos.draw()
        


pyglet.clock.schedule_interval(update, 1/60.0)
pyglet.app.run()

"""
short paragraph on alpha values is in Readme.
"""
