from flask import Flask,render_template,request,redirect,url_for,flash,session,Response, jsonify
from dbhelperSQLITE import *
import cv2
import face_recognition
from simple_facerec import SimpleFacerec
from flask_socketio import SocketIO
from datetime import datetime
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = "!@#$%"
socketio = SocketIO(app)
	
imagefolder = "static/img"
app.config["UPLOAD_FOLDER"] = imagefolder

sfr = SimpleFacerec()
sfr.load_encoding_images()

global present_std
global present_student
global reset
reset = False
present_std = []
present_student = []

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response
    
@app.route("/logout")
def logout()->None:
	if "username" in session:
		session.pop("username")
		flash("Account has been logged out successfully!")
	return redirect(url_for('login'))

@app.route("/login", methods=['POST', 'GET'])
def login() -> None:
    if "username" not in session:
        if request.method == "POST":
            email: str = request.form['email']
            pword: str = request.form['password']
            # set a static user validation
            user = userlogin('accounts', email=email, password=pword)
            print(user)
            if user:
                session['username'] = email
                flash("Account has been logged in successfully!")
                return redirect(url_for('home'))
            else:
                flash("Invalid username or password!")
    return render_template("login.html", title="Login")
    
def gen_frames_admin():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error opening video capture.")
        return

    students_dict = {'0001': 0, 'Unknown': 0}
    print(f"students_dict: {students_dict}")

    present_adm = []
    present_admin = []

    while True:
        success, frame = cap.read()
        if not success:
            print("Error reading frame from the camera.")
            break
        else:
            # Process the frame, detect faces, etc.
            face_locations, face_info = sfr.detect_known_faces(frame)
            for face_loc, name_info in zip(face_locations, face_info):
                y1, x2, y2, x1 = face_loc[0], face_loc[1], face_loc[2], face_loc[3]

                # Convert name_info["lastname"] and name_info["idno"] to strings
                lastname_str = str(name_info["lastname"])
                idno_str = str(name_info["idno"])
                
                # Check if the detected student is the admin with ID '0001'
                if idno_str == '0001':
                    students_dict[idno_str] += 1
                else:
                    idno_str = 'Unknown'
                    students_dict[idno_str] += 1

                if students_dict[idno_str] < 10 and "Unknown" not in idno_str:
                    students_dict[idno_str] += 1
                elif "Unknown" not in idno_str and idno_str not in present_admin:
                    present_admin.append(idno_str)
                    std = getrecord('students', idno=idno_str)
                    if std[0] not in present_adm:
                        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        present_adm.append({**std[0], 'time': current_time})  # student is checked and marked present
                        socketio.emit('update_table', {'username': 'admin', 'password': 'admin123'}, room=current_request_sid)
                    #print(f"RESULTS: {present_adm}")

                text = f"{lastname_str}"  # Display lastname and idno on separate lines

                if idno_str in present_admin:
                    # Emit a message to the client to update the table
                    # add a session here use the admin 0001
                    # redirect the url to home
                    cv2.putText(frame, "Checked", (x1, y1 - 35), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 240, 0), 2)
                cv2.putText(frame, text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 4)

            # Encode the frame as JPEG
            _, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    cap.release()

    
@app.route('/video_feed_admin')
def video_feed_admin():
    return Response(gen_frames_admin(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route("/register")
def register()->None:
    if "username" in session:
        global users
        students = getall('students')
        #print(users)
        return render_template("register.html",title="Register", students=students)
    else:
        return redirect(url_for('login'))
	
	
@app.route("/saveimage", methods=['POST'])
def saveimage() -> str:
    file = request.files['webcam']
    idno = request.args.get('idno')
    lastname = request.args.get('lastname')
    firstname = request.args.get('firstname')
    course = request.args.get('course')
    level = request.args.get('level')

    img_path = idno + ".jpg"
    student_info = {}
    try:
        success = addrecord('students', idno=idno, lastname=lastname, firstname=firstname, course=course, level=level, img_path=img_path)
        student_info = {"idno": idno, "lastname": lastname, "img_path": img_path}
        
    except Exception as e:
        success = False

    if success:
        filename = imagefolder + "/" + img_path
        file.save(filename)
        sfr.load_encoding_images(new_student=student_info)
    else:
        return "Failed", 400
    return "Success", 200

@app.route("/")
def home()->None:
    if "username" in session:
        print(f"PRESENT STUDENTS: {present_std}")
        return render_template("home.html",title="Home")
    else:
        return redirect(url_for('login'))

def generate_frames():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error opening video capture.")
        return

    students_idno = getall_idno('students')
    students_idno.append("Unknown")

    students_dict = {idno: 0 for idno in students_idno}
    
    global reset
    if reset:
        present_std.clear()
        present_student.clear()
        reset = not reset
        print("RESET")
        
    while True:
        success, frame = cap.read()
        if not success:
            print("Error reading frame from the camera.")
            break
        else:
            # Process the frame, detect faces, etc.
            face_locations, face_info = sfr.detect_known_faces(frame)
            for face_loc, name_info in zip(face_locations, face_info):
                y1, x2, y2, x1 = face_loc[0], face_loc[1], face_loc[2], face_loc[3]

                # Convert name_info["lastname"] and name_info["idno"] to strings
                lastname_str = str(name_info["lastname"])
                idno_str = str(name_info["idno"])
                # print(idno_str)
                if students_dict[idno_str] < 10 and "Unknown" not in idno_str:
                    students_dict[idno_str] += 1
                elif "Unknown" not in idno_str and idno_str not in present_student:
                    present_student.append(idno_str)
                    std = getrecord('students', idno=idno_str)
                    if std[0] not in present_std:
                        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        present_std.append({**std[0], 'time': current_time}) # student is checked and marked present
                        
                        socketio.emit('update_table', {'idno': std[0]['idno'], 'lastname': std[0]['lastname'], 'firstname': std[0]['firstname'], 'course': std[0]['course'], 'level': std[0]['level'], 'time': current_time}, room=current_request_sid)
                    #print(f"RESULTS: {present_std}")
                    #print(f"RESULTS: {present_student}")

                text = f"{lastname_str}"  # Display lastname and idno on separate lines
                #print(f"PRESENT STUDENT: {present_student}")
                #print(f"IDNO STR: {idno_str}")
                if idno_str in present_student:
                    # Emit a message to the client to update the table
                    cv2.putText(frame, "Checked", (x1, y1 - 35), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 240, 0), 2)
                cv2.putText(frame, text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 4)
            # Encode the frame as JPEG
            _, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    cap.release()
    
current_request_sid = None  # Initialize the variable outside the loop

@socketio.on('connect')
def handle_connect():
    global current_request_sid
    current_request_sid = request.sid
    print('Client connected')
    
@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/attendance')
def video():
    if "username" in session:
        print(f"PRESENT STUDENTS: {present_std}")
        return render_template('video.html', present_students=present_std, title="Attendance")
    else:
        return redirect(url_for('login'))
        
@app.route('/reset')
def reset():
    if "username" in session:
        present_std.clear()
        present_student.clear()
        global reset
        reset = True
        return redirect(url_for('video'))
    else:
        return redirect(url_for('login'))

@app.route('/save', methods=['POST'])
def save():
    if "username" in session:
        filename: str = request.form['filename']
        print(f"PRESENT STUDENT - SAVE: {present_std}")
        
        # Create a DataFrame from the present_std list
        df = pd.DataFrame(present_std)

        # Specify the directory for the "attendance" folder
        attendance_dir = os.path.join(os.getcwd(), 'attendance')

        # Create the "attendance" directory if it doesn't exist
        os.makedirs(attendance_dir, exist_ok=True)

        # Create the "attendance" directory if it doesn't exist
        os.makedirs("attendance", exist_ok=True)

        # Save the DataFrame to an Excel file in the "attendance" directory
        excel_filename = os.path.join(attendance_dir, f"{filename}.xlsx")
        df.to_excel(excel_filename, index=False)
        print(f"ATTENDANCE SAVED!")
        
        present_std.clear()
        present_student.clear()
        global reset
        reset = True
        flash("Attendance Saved!")
        return redirect(url_for('home'))
    else:
        return redirect(url_for('login'))

@app.route('/students')
def students():
    if "username" in session:
        students = getall('students')
        return render_template('students.html', students=students)
    else:
        return redirect(url_for('login'))

if __name__=="__main__":
	app.run(host="0.0.0.0",debug=True)


