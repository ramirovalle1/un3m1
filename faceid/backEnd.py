# -*- coding: latin-1 -*-
import base64
import io
import os
import random
import sys
import json
import re
import numpy as np
import xlrd
from PIL import Image
import cv2
from settings import BASE_DIR, SITE_STORAGE
from datetime import datetime
from sga.funciones import elimina_tildes
from sga.models import Persona

# THIRDPARTY_FOLDER = os.path.join(BASE_DIR, 'faceid', 'thirdparty')
# detector = cv2.CascadeClassifier(THIRDPARTY_FOLDER + os.sep + 'haarcascade_frontalface_default.xml')
# recognizer = cv2.face.LBPHFaceRecognizer_create()


# # Create a connection witn databse
# conn = sqlite3.connect('db.sqlite3')
# if conn != 0:
#     print("Connection Successful")
# else:
#     print('Connection Failed')
#     exit()

# Creating table if it doesn't already exists
# conn.execute('''create table if not exists facedata ( id int primary key, name char(20) not null)''')

# class FaceRecognition:
#
#     def faceDetect(self, request, persona):
#         try:
#             if not 'images' in request.POST:
#                 raise NameError(f"No se encontro imagenes")
#             PATH_DATASET = os.path.join(SITE_STORAGE, 'media', 'users', 'dataset')
#             # output_folder = os.path.join(DATASET_USEROUTPUT_FOLDER, elimina_tildes(persona.usuario.username))
#             output_folder = os.path.join(PATH_DATASET)
#             try:
#                 os.makedirs(output_folder)
#             except Exception as ex:
#                 pass
#             data_images = request.POST.get('images')
#             data_images_parse = json.loads(data_images)
#             contador = 0
#             for data_image_parse in data_images_parse:
#
#                 imagestr = re.search('base64,(.*)', data_image_parse).group(1)
#                 imagestr = base64.b64decode(imagestr)
#                 tempImage = io.BytesIO(imagestr)
#                 pil_img = Image.open(tempImage)
#                 #pil_img.save(fileimage, format="png")
#                 # username = elimina_tildes(persona.usuario.username)
#                 numpy_image = np.array(pil_img)
#                 user_id = persona.usuario.id
#                 contador += 1
#                 fileimage = (output_folder + os.sep + f"User.{user_id}.{str(contador)}.png")
#                 # opencv_image = cv2.cvtColor(numpy_image, cv2.COLOR_RGB2BGR)
#                 # gray = cv2.cvtColor(numpy_image, cv2.COLOR_BGR2GRAY)
#                 # cv2.imwrite(fileimage, gray)
#                 # faces = detector.detectMultiScale(gray, 1.3, 5)
#                 # faces = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30), flags=cv2.CV_HAAR_SCALE_IMAGE)
#                 # faces = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
#                 # for (x, y, w, h) in faces:
#                 #     cv2.rectangle(numpy_image, (x, y), (x + w, y + h), (255, 0, 0), 2)
#                 #     cv2.imwrite(fileimage, gray[y:y + h, x:x + w])
#             return True, ''
#         except Exception as ex:
#             return False, ex.__str__()
#
#     def trainFace(self, request, persona):
#         try:
#             # Path for face image database
#             PATH_DATASET = os.path.join(SITE_STORAGE, 'media', 'users', 'dataset')
#             PATH_TRAINER = os.path.join(SITE_STORAGE, 'media', 'users', 'trainer')
#             output_dataset = os.path.join(PATH_DATASET)
#             try:
#                 os.makedirs(output_dataset)
#             except Exception as ex:
#                 pass
#
#             output_trainer = os.path.join(PATH_TRAINER)
#             try:
#                 os.makedirs(output_trainer)
#             except Exception as ex:
#                 pass
#             print("\n Training faces. It will take a few seconds. Wait ...")
#             faces, ids = getImagesAndLabels(PATH_DATASET)
#             recognizer.train(faces, np.array(ids))
#             # Save the model into trainer/trainer.yml
#             recognizer.save(output_trainer + os.sep + 'trainer.yml')  # recognizer.save() worked on Mac, but not on Pi
#             # Print the numer of faces trained and end program
#             print("\n {0} faces trained. Exiting Program".format(len(np.unique(ids))))
#             return True, ''
#         except Exception as ex:
#             return False, ex.__str__()
#
#     def recognizeFace(self, request):
#         try:
#             if not 'image' in request.POST:
#                 raise NameError(f"No se encontro imagen")
#             data_image = request.POST.get('image')
#             if not data_image:
#                 raise NameError(f"No se encontro archivo de imagen")
#             PATH_DATASET_TEMP = os.path.join(SITE_STORAGE, 'media', 'users', 'temp')
#             # output_folder = os.path.join(DATASET_USEROUTPUT_FOLDER, elimina_tildes(persona.usuario.username))
#             output_folder_temp = os.path.join(PATH_DATASET_TEMP)
#             try:
#                 os.makedirs(output_folder_temp)
#             except Exception as ex:
#                 pass
#
#             PATH_TRAINER = os.path.join(SITE_STORAGE, 'media', 'users', 'trainer')
#             output_trainer = os.path.join(PATH_TRAINER)
#             recognizer.read(output_trainer + os.sep + 'trainer.yml')
#             # faceCascade = detector
#             # font = cv2.FONT_HERSHEY_SIMPLEX
#             confidence = 0
#             imagestr = re.search('base64,(.*)', data_image).group(1)
#             imagestr = base64.b64decode(imagestr)
#             tempImage = io.BytesIO(imagestr)
#             pil_img = Image.open(tempImage)
#             fileimage_rgb = (output_folder_temp + os.sep + f"rgb_{random.randint(1, 10000).__str__()}_{datetime.now().strftime('%m%d%Y_%H%M%S')}.png")
#             pil_img.save(fileimage_rgb, format="png")
#             numpy_image = np.array(pil_img)
#             # fileimage_gray = (output_folder_temp + os.sep + f"gray_{random.randint(1, 10000).__str__()}_{datetime.now().strftime('%m%d%Y_%H%M%S')}.png")
#             # gray = cv2.cvtColor(numpy_image, cv2.COLOR_BGR2GRAY)
#             # cv2.imwrite(fileimage_gray, gray)
#             img = cv2.imread(fileimage_rgb)
#             gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
#             faces = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
#             ePersona = None
#             for (x, y, w, h) in faces:
#                 cv2.rectangle(numpy_image, (x, y), (x + w, y + h), (0, 255, 0), 2)
#                 face_id, confidence = recognizer.predict(gray[y:y + h, x:x + w])
#                 # Check if confidence is less then 100 ==> "0" is perfect match
#                 if (confidence < 100):
#                     name = 'Detected'
#                     if Persona.objects.values("id").filter(usuario_id=face_id).exists():
#                         ePersona = Persona.objects.get(usuario_id=face_id)
#                     else:
#                         name = "Unknown"
#                 else:
#                     name = "Unknown"
#                 if confidence > 50:
#                     break
#             print("\n Exiting Program")
#             if ePersona is None:
#                 raise NameError(u"No se encontro la persona")
#             return ePersona, ''
#         except Exception as ex:
#             return None, ex.__str__()


# function to get the images and label data
# def getImagesAndLabels(path):
#     imagePaths = [os.path.join(path, f) for f in os.listdir(path)]
#     faceSamples = []
#     ids = []
#     for imagePath in imagePaths:
#         PIL_img = Image.open(imagePath).convert('L')  # convert it to grayscale
#         img_numpy = np.array(PIL_img, 'uint8')
#         face_id = int(os.path.split(imagePath)[-1].split(".")[1])
#         faces = detector.detectMultiScale(img_numpy)
#         for (x, y, w, h) in faces:
#             faceSamples.append(img_numpy[y:y + h, x:x + w])
#             ids.append(face_id)
#     return faceSamples, ids