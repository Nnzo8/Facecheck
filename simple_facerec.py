import face_recognition
import cv2
from dbhelperSQLITE import *
import numpy as np
import pickle

class SimpleFacerec:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_names = []

        # Resize frame for a faster speed
        self.frame_resizing = 0.25

    def load_encoding_images(self, new_student=None):
        """
        Load encoding images from the database
        :param new_student: Information about the new student to be added
        :return:
        """
        # Load existing encodings from file
        encoded = self.load_encodings_from_file()

        # Add encoding for the new student
        if new_student:
            try:
                img = cv2.imread("static/img/" + str(new_student["img_path"]))
                rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                new_encoding = face_recognition.face_encodings(rgb_img)[0]
                self.known_face_encodings.append({"idno": new_student["idno"], "encoding": new_encoding})
                self.known_face_names.append(new_student["lastname"])
                print(f"{new_student['lastname']} ENCODING DONE!")
                # Save encodings to file
                self.save_encodings_to_file()
            except Exception as e:
                print(f"Error encoding {new_student['lastname']}: {e}")
            
        else:
            if not encoded:
                # Get all student records from the database
                students = getall('students')

                # Loop through each student
                for student in students:
                    try:
                        # Read the image file from the specified image path in the database
                        img = cv2.imread("static/img/" + str(student["img_path"]))

                        # Convert the image to RGB format
                        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

                        # Get the face encoding for the first face in the image
                        img_encoding = face_recognition.face_encodings(rgb_img)[0]

                        # Append the encoding and name to the lists
                        self.known_face_encodings.append({"idno": student["idno"], "encoding": img_encoding})
                        self.known_face_names.append(student["lastname"])

                        print(f"{student['lastname']} ENCODING DONE!")
                    except Exception as e:
                        print(f"Error encoding {student['lastname']}: {e}")
                print(f"DONE ENCODING ALL STUDENTS!")
                
                # Save encodings to file
                self.save_encodings_to_file()


    def save_encodings_to_file(self):
        with open("encodings.pkl", "wb") as file:
            pickle.dump((self.known_face_encodings, self.known_face_names), file)
            print(f"DONE ENCODING AND SAVED TO FILE!")

    def load_encodings_from_file(self)->bool:
        try:
            with open("encodings.pkl", "rb") as file:
                print(f"ENCODING FILE FOUND!")
                self.known_face_encodings, self.known_face_names = pickle.load(file)
                print(f"DONE LOAD ENCODING FROM FILE!")
                return True
        except FileNotFoundError:
            # File does not exist, initialize empty lists
            print(f"ENCODING FILE NOT FOUND!")
            self.known_face_encodings = []
            self.known_face_names = []
            return False

    def detect_known_faces(self, frame):
        small_frame = cv2.resize(frame, (0, 0), fx=self.frame_resizing, fy=self.frame_resizing)
        # Find all the faces and face encodings in the current frame of video
        # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

        face_info = []
        for face_encoding in face_encodings:
            # See if the face is a match for the known face(s)
            matches = face_recognition.compare_faces([entry["encoding"] for entry in self.known_face_encodings], face_encoding)
            info = {"idno": "Unknown", "lastname": "Unknown"}

            # Or instead, use the known face with the smallest distance to the new face
            face_distances = face_recognition.face_distance([entry["encoding"] for entry in self.known_face_encodings], face_encoding)
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                idno = self.known_face_encodings[best_match_index]["idno"]
                lastname = self.known_face_names[best_match_index]
                
                #print(f"IDNO: {idno}")
                #print(f"LASTNAME: {lastname}")

                info["idno"] = idno
                info["lastname"] = lastname

            face_info.append(info)

        # Convert to numpy array to adjust coordinates with frame resizing quickly
        face_locations = np.array(face_locations)
        face_locations = face_locations / self.frame_resizing
        return face_locations.astype(int), face_info
