# A function that watches a folder and reads new files as soon as they are there 
# Then, continues the program

import cv2
import time
import numpy as np
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import pickle
from copy import deepcopy

from PIL import Image

from face_detector import FaceDetector
from sketcher import Sketcher
from path_generator import Face_paths_generator, preprocessor
from local_painter import Leonao_painter

def normalizePaths(input_paths):
    # Make sure the output here will be in 0-1 and not in pixels (probably in the function already)
    # Scale all values in face_inner_paths and face_outer_paths to 0-1

    # Get the maximum value of tuples in lists of lists in face_inner_paths and face_outer_paths
    # Divide all values in face_inner_paths and face_outer_paths by the maximum value
    x_max = 0.0
    x_min = 512.0
    y_max = 0.0
    y_min = 512.0

    for paths in input_paths: # TODO: Not efficient, maybe needs to be changed
        for list in paths:
            for tuples in list:
                (x,y) = tuples
                if x > x_max:
                    x_max = x
                if x < x_min:
                    x_min = x
                if y > y_max:
                    y_max = y
                if y < y_min:
                    y_min = y
    
    print("X max: ", x_max)
    print("X min: ", x_min)
    print("Y max: ", y_max)
    print("Y min: ", y_min)

    if x_max - x_min > y_max - y_min:
        longest_side = x_max - x_min
    else:
        longest_side = y_max - y_min
    all_paths_list = input_paths
    for p, paths in enumerate(all_paths_list):
        for i, list in enumerate(paths):
            for j, tuples in enumerate(list):
                (x,y) = tuples
                all_paths_list[p][i][j] = [(x - x_min)/longest_side, (y - y_min)/longest_side]
    
    return all_paths_list

class Watcher():
    def __init__(self, DIRECTORY_TO_WATCH):
        self.observer = Observer()
        self.DIRECTORY_TO_WATCH = DIRECTORY_TO_WATCH
        print("Watching: " + self.DIRECTORY_TO_WATCH)

    def run(self):
        event_handler = Handler()
        self.observer.schedule(event_handler, self.DIRECTORY_TO_WATCH, recursive=True)
        self.observer.start()
        try:
            while True:
                time.sleep(5) # This is not the polling time, so 5s is not slowing us down
        except:
            self.observer.stop()
            print("Error")

        self.observer.join()

sketcher = Sketcher()

face_paths_gen = Face_paths_generator()

class Handler(FileSystemEventHandler):

    @staticmethod
    def on_any_event(event):
        print(f"Received event - {event}")


        if event.is_directory:
            #print("Received directory event - %s.", event.src_path)
            return None

        elif event.event_type == 'modified':
            file = event.src_path
            print("Received modified event - %s.", file)

            if file[-15:] == "detect_face.jpg":
                print("Detecting face")
                img = cv2.imread(file)
                faceDetector = FaceDetector()
                bbox, _ = faceDetector.detect_face(img)
                print(bbox)
                with open(DIRECTORY_TO_WATCH + "/" + "face_detection_result.txt", "w") as f:
                    f.write(str(bbox))
            elif file[-15:] == "sketch_face.jpg":
                print("Sketching face")
                img = cv2.imread(file)
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                output_img, output_face_mask = sketcher.run(img)
                output_img = output_img*255
                ret,output_img = cv2.threshold(output_img,127,255,cv2.THRESH_BINARY)

                cv2.imwrite(DIRECTORY_TO_WATCH + "/" + "thresholded.bmp", (output_img).astype(np.uint8))

                l_painter = Leonao_painter()
                
                # Preprocess the image 
                output_img = preprocessor(output_img)

                # Invert the image
                output_img = (output_img-255)*(-1)

                inner_sketch = output_img*output_face_mask
                outer_sketch = output_img*(1-output_face_mask)
                noFaceSeperation = True
                if noFaceSeperation:
                    cv2.imwrite(DIRECTORY_TO_WATCH + "/" + "outer_sketch.bmp", (output_img).astype(np.uint8))
                    cv2.imwrite(DIRECTORY_TO_WATCH + "/" + "inner_sketch.bmp", (output_img).astype(np.uint8))
                    face_inner_paths = face_paths_gen.get_face_outer_path(DIRECTORY_TO_WATCH + "/" + "outer_sketch.bmp")
                    face_outer_paths = []
                
                else:

                    cv2.imwrite(DIRECTORY_TO_WATCH + "/" + "outer_sketch.bmp", (outer_sketch).astype(np.uint8))
                    cv2.imwrite(DIRECTORY_TO_WATCH + "/" + "inner_sketch.bmp", (inner_sketch).astype(np.uint8))


                    # Potentially simplyfing the lines more

                    face_outer_paths = face_paths_gen.get_face_outer_path(DIRECTORY_TO_WATCH + "/" + "outer_sketch.bmp")
                    face_inner_paths = face_paths_gen.get_face_inner_path(DIRECTORY_TO_WATCH + "/" + "inner_sketch.bmp")


                face_outer_paths_original = deepcopy(face_outer_paths)
                face_inner_paths_original = deepcopy(face_inner_paths)

                all_paths_list = normalizePaths([face_inner_paths, face_outer_paths])

                
                all_paths = {"inner": all_paths_list[0], "outer": all_paths_list[1]}
                print("All Paths size: ", (len(all_paths["inner"]) + len(all_paths["outer"])))
                print("All Path points amount: ", sum([len(list) for list in all_paths["inner"]]) + sum([len(list) for list in all_paths["outer"]]))
                with open(DIRECTORY_TO_WATCH + "/" + "sketcher_result.pkl", "wb") as f:
                    pickle.dump(all_paths, f, protocol=2)

                #l_painter.draw(face_outer_paths_original, face_inner_paths_original)

                return None



if __name__ == '__main__':
    DIRECTORY_TO_WATCH = "/home/hrsa/leonao/src/leonao/watchfolder/"
    w = Watcher(DIRECTORY_TO_WATCH)
    w.run()