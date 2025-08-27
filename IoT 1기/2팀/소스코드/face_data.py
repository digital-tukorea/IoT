# 얼굴 인식 데이터 생성

import cv2
import os

# 절대 경로를 사용하여 haarcascade 파일 경로 설정
haarcascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
face_classifier = cv2.CascadeClassifier(haarcascade_path)

def face_extractor(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_classifier.detectMultiScale(gray, 1.3, 5)

    if len(faces) == 0:
        return None

    for (x, y, w, h) in faces:
        cropped_face = img[y:y+h, x:x+w]

    return cropped_face

# 저장할 디렉토리 설정
base_dir = r'/home/qwer/project/face'
if not os.path.exists(base_dir):
    os.makedirs(base_dir)

# 사용자 이름 입력받기
user_name = input("Enter the name of the user: ").strip()
user_dir = os.path.join(base_dir, user_name)
if not os.path.exists(user_dir):
    os.makedirs(user_dir)

cap = cv2.VideoCapture(0)
count = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    face = face_extractor(frame)
    if face is not None:
        count += 1
        face = cv2.resize(face, (200, 200))
        face = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)

        file_name_path = os.path.join(user_dir, f'{count}.jpg')
        cv2.imwrite(file_name_path, face)

        cv2.putText(face, str(count), (50, 50), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow('Face Cropper', face)
    else:
        print("Face not Found")
        pass

    if cv2.waitKey(1) == 13 or count == 100:  # Enter 키를 누르거나 100개의 얼굴 이미지가 저장되면 종료
        break

cap.release()
cv2.destroyAllWindows()
print(f'Collecting Samples Complete for {user_name}!!!')
