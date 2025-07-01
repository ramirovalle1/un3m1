import os
import cv2
# import dlib
import numpy as np
import firebase_admin
from settings import BASE_DIR, SITE_STORAGE
from firebase_admin import credentials
from firebase_admin import firestore

# Importar las bibliotecas necesarias para la detección de rostros y reconocimiento facial
THIRDPARTY_FOLDER = os.path.join(BASE_DIR, 'faceid', 'thirdparty')
face_cascade = cv2.CascadeClassifier(THIRDPARTY_FOLDER + os.sep + 'haarcascade_frontalface_default.xml')
model = cv2.face.LBPHFaceRecognizer_create()


# Cargar el modelo de detección de puntos de referencia faciales pre-entrenado
# landmark_predictor = dlib.shape_predictor(THIRDPARTY_FOLDER + os.sep + 'shape_predictor_68_face_landmarks.dat')


# Inicializar la aplicación de Firebase
cred = credentials.Certificate(THIRDPARTY_FOLDER + os.sep + 'unemifirebase-dcd5a1754bbd.json')
firebase_admin.initialize_app(cred)
db = firestore.client()


# Función para extraer los rostros y las etiquetas de las imágenes
def extract_faces_labels(images):
    faces = []
    labels = []

    for image_path, label in images:
        image = cv2.imread(image_path)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Detectar rostros en la imagen
        face_rects = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

        for (x, y, w, h) in face_rects:
            face = gray[y:y+h, x:x+w]
            faces.append(face)
            labels.append(label)

    return faces, labels


# Función para almacenar los datos de características faciales en Firebase
def store_faces_in_firestore(faces, labels):
    model.train(faces, np.array(labels))  # Entrenar el modelo desde cero con todos los datos

    for face, label in zip(faces, labels):
        # Obtener las características faciales del rostro actual
        features = model.predict(face)[0]

        # Crear un nuevo documento en la colección "faces" de Firestore
        doc_ref = db.collection('faces').document()
        doc_ref.set({
            'label': str(label),
            'features': features
        })


# Función para entrenar el modelo de reconocimiento facial
def train_model(images):
    faces, labels = extract_faces_labels(images)
    store_faces_in_firestore(faces, labels)


# Función para realizar el reconocimiento facial en una imagen desconocida
def recognize_face(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Detectar rostros en la imagen
    face_rects = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

    for (x, y, w, h) in face_rects:
        face = gray[y:y+h, x:x+w]

        # Realizar el reconocimiento facial utilizando el modelo de FisherFaces
        label, confidence = model.predict(face)

        if confidence < 100:  # Umbral de confianza para la coincidencia
            return label

    return "Desconocido"


# Ejemplo de entrenamiento y reconocimiento facial con almacenamiento en Firebase
if __name__ == '__main__':
    # Ejemplo de imágenes de entrenamiento con etiquetas
    images = [
        ((THIRDPARTY_FOLDER + os.sep + 'fotos' + os.sep + 'amonteross.jpg'), 1),
        ((THIRDPARTY_FOLDER + os.sep + 'fotos' + os.sep + 'apilozop2.jpg'), 2),
        ((THIRDPARTY_FOLDER + os.sep + 'fotos' + os.sep + 'avalcarcelz.jpg'), 3),
        # Agrega más imágenes de entrenamiento con sus respectivas etiquetas
    ]

    # Entrenar el modelo de reconocimiento facial y almacenar en Firebase
    train_model(images)

    # Reconocimiento facial en una imagen desconocida
    image_unknown = cv2.imread(THIRDPARTY_FOLDER + os.sep + 'crodriguezn.jpg')
    result = recognize_face(image_unknown)

    print("Resultado del reconocimiento facial:", result)
