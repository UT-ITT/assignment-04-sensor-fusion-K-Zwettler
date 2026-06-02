import cv2
import numpy as np
import sys

if len(sys.argv) <= 4:
    print("Specify your input image, the output destination and the result's resolution")
    sys.exit()

# get parameters from command line input
input_file = sys.argv[1]
output_destination = sys.argv[2]
resolution_x = sys.argv[3]
resolution_y = sys.argv[4]

dest_width = int(resolution_x)
dest_height = int(resolution_y)

img = cv2.imread(str(input_file))

# counter for drawn points
point_ctr = 0
points = []

# destination window to transform image into
destination = np.float32(np.array([[0, 0], [dest_width, 0], [dest_width, dest_height], [0, dest_height]]))

# original image to set back to after pressing esc
orig_img = img.copy()
img_transformed = None

WINDOW_NAME = 'Preview Window'

cv2.namedWindow(WINDOW_NAME)

# transforms the image formed by points into the shape of the destination window
def transform_image(points): 
    global img_transformed

    points = np.float32(np.array(points))

    # get transformation matrix
    mat = cv2.getPerspectiveTransform(points, destination)
    # transform image
    img_transformed = cv2.warpPerspective(img, mat, (dest_width, dest_height), flags=cv2.INTER_LINEAR)

    return img_transformed

# handles mouse inputs
def mouse_callback(event, x, y, flags, param):
    global img, point_ctr, points

    if event == cv2.EVENT_LBUTTONDOWN:
        # draw circles
        img = cv2.circle(img, (x, y), 5, (255, 0, 0), -1)
        cv2.imshow(WINDOW_NAME, img)
        point_ctr += 1
        points.append((x, y))

        # if four points were drawn, transform the image
        if point_ctr == 4: 
            img_transformed = transform_image(points)
            cv2.imshow('Result', img_transformed)

cv2.imshow(WINDOW_NAME, img)

cv2.setMouseCallback(WINDOW_NAME, mouse_callback)

# handle keyboard inputs 
while True: 
    key = cv2.waitKey(1) & 0xFF
    if key == 27: 
        points = []
        point_ctr = 0
        img = orig_img.copy()
        cv2.imshow(WINDOW_NAME, img)
        continue
    
    if key == ord('s'):
        if img_transformed is None: 
            print("No transformed image to save!")
        else: 
            cv2.imwrite(output_destination, img_transformed)
    
    if key == ord('q'):
        break

cv2.destroyAllWindows()





    
