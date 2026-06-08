import cv2
import numpy as np
import pyglet
from PIL import Image
import sys
import cv2.aruco as aruco
import random

class Ball:
    def __init__(self, x, y, vx, vy, color, is_bad, radius):
        self.x = x
        self.y = y
        # velocities
        self.vx = vx
        self.vy = vy
        self.radius = radius
        self.alive = True
        self.shape = pyglet.shapes.Circle(x, y, radius, color=color)
        self.is_bad = is_bad
    
    # update the ball so that it flies into the window from the bottom and drops down again
    def update(self, dt):
        self.vy -= 600 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.shape.x = int(self.x)
        self.shape.y = int(self.y)

    def draw(self):
        self.shape.draw()

class Game:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.balls = []
        self.score = 0
        self.spawn_interval = 1.0
        self.spawn_timer = 0.0
        self.ball_counter = 0

    def spawn_ball(self, radius=20):
        # spawn a ball with random starting position and velocity
        x = random.randrange(radius, self.width - radius)
        vx = random.uniform(-50, 50)
        vy = random.uniform(600, 800)
        # spawn a "bad" ball every fifth time, that leads to losing score points
        if self.ball_counter >= 5:
            ball = Ball(x, -radius, vx, vy, (255, 0, 0), True, radius)
            self.ball_counter = 0
        else: 
            ball = Ball(x, -radius, vx, vy, (0, 0, 255), False, radius)
        self.balls.append(ball)
        self.ball_counter += 1


    def update(self, dt, hand_contour):
        self.spawn_timer += dt
        # spawn balls after certain amount of time
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer = 0.0
            self.spawn_ball()
        
        for ball in self.balls: 
            ball.update(dt)

        # if hand was detected, check if it collides with any balls
        if hand_contour is not None: 
            self.check_hand_collision(hand_contour)
        
        # update the balls list
        self.balls = [b for b in self.balls if b.alive and -100 < b.x < self.width+100 and -200 < b.y < self.height+200] 

    def check_hand_collision(self, hand_contour):
        # check if any ball collides with the hand contour
        for ball in self.balls:
            dist = cv2.pointPolygonTest(hand_contour, (ball.x, ball.y), True)
            if dist >= -ball.radius:
                ball.alive = False
                if ball.is_bad == True:
                    self.score -= 2
                else: 
                    self.score += 1

    def draw(self, frame):
        for ball in self.balls:
            ball.draw()


window = pyglet.window.Window(width=640, height=480)
game = Game(640, 480)

# score label
score_label_shadow = pyglet.text.Label(
    '0', font_name='Arial', font_size=40, x=12, y=window.height-52,
    color=(0, 0, 0, 220)
)
score_label = pyglet.text.Label(
    '0', font_name='Arial Bold', font_size=40, x=10, y=window.height-50,
    color=(255, 215, 0, 255)
)
motivation_text = pyglet.text.Label(
    "Destroy the Blue Balls!", font_name="Arial", font_size=30, x=150, y=window.height-52, color=(255, 215, 0, 220)
)
show_mot_text = False

frame_transformed = None

video_id = 0

if len(sys.argv) > 1:
    video_id = int(sys.argv[1])

# Create a video capture object for the webcam
cap = cv2.VideoCapture(video_id)

# Define the ArUco dictionary, parameters, and detector
aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_6X6_250)
aruco_params = aruco.DetectorParameters()
detector = aruco.ArucoDetector(aruco_dict, aruco_params)


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

# detects the contour of a hand and returns the coordiantes of it
def detect_hand(frame_transformed):
    hsv = cv2.cvtColor(frame_transformed, cv2.COLOR_BGR2HSV)

    lower = np.array([0, 30, 60])
    upper = np.array([25, 255, 255])
    mask = cv2.inRange(hsv, lower, upper)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    # get the contour of the hand
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours: 
        return None
    
    c = max(contours, key=cv2.contourArea)
    return c

# extracts the area between the aruco markers, warps it into rectangle and returns it 
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
        if means[i][0] == x_values[2] or means[i][0] == x_values[3]:
            if means[i][1] == y_values[2] or means[i][1] == y_values[3]:
                BR = i
            else:
                TR = i
        elif means[i][1] == y_values[2] or means[i][1] == y_values[3]:
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

    return frame_transformed


def update(dt):
    global frame_transformed, show_mot_text

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

    # Check if marker is detected
    if ids is not None:
        if ids.shape[0] == 4: 
            frame_transformed = get_transformed_frame(corners, frame)
            hand_contour = detect_hand(frame_transformed)
            game.update(dt, hand_contour)
            show_mot_text = True
        else: 
            show_mot_text = False
                
@window.event
def on_draw():
    window.clear()
    if frame_transformed is not None: 
        img = cv2glet(frame_transformed, 'BGR')
        img.blit(0, 0)
    
    game.draw(None)  
    # draw score
    score_label_shadow.text = str(game.score)
    score_label.text = str(game.score)
    score_label_shadow.draw()
    score_label.draw()
    # draw motivation text if game is running
    if show_mot_text:
        motivation_text.draw()

# close the window when key 'q' is pressed
@window.event
def on_key_press(symbol, modifiers):
    if symbol == pyglet.window.key.Q:
        sys.exit(0)

pyglet.clock.schedule_interval(update, 1/60.0)
pyglet.app.run()


