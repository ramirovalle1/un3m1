# import the necessary packages
import os
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import numpy as np
# import urllib
from urllib.request import urlopen
import json
import cv2
from settings import BASE_DIR, SITE_STORAGE

#https://pyimagesearch.com/2015/05/11/creating-a-face-detection-api-with-python-and-opencv-in-just-5-minutes/

THIRDPARTY_FOLDER = os.path.join(BASE_DIR, 'faceid', 'thirdparty')
# FACE_DETECTOR_PATH = "{thirdparty_path}/cascades/haarcascade_frontalface_default.xml".format(thirdparty_path=THIRDPARTY_FOLDER)
# detector = cv2.CascadeClassifier(THIRDPARTY_FOLDER + os.sep + 'haarcascade_frontalface_default.xml')


@csrf_exempt
def detect(request):
    # initialize the data dictionary to be returned by the request
    data = {"success": False}

    # check to see if this is a post request
    if request.method == "POST":
        # check to see if an image was uploaded
        if request.FILES.get("image", None) is not None:
            # grab the uploaded image
            image = _grab_image(stream=request.FILES["image"])

        # otherwise, assume that a URL was passed in
        else:
            # grab the URL from the request
            url = request.POST.get("url", None)

            # if the URL is None, then return an error
            if url is None:
                data["error"] = "No URL provided."
                return JsonResponse(data)

            # load the image and convert
            image = _grab_image(url=url)

        # convert the image to grayscale, load the face cascade detector,
        # and detect faces in the image
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        detector = cv2.CascadeClassifier(THIRDPARTY_FOLDER + os.sep + 'haarcascade_frontalface_default.xml')
        # detector = cv2.CascadeClassifier(FACE_DETECTOR_PATH)
        # rects = detector.detectMultiScale(image, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30), flags=cv2.CV_HAAR_SCALE_IMAGE)
        rects = detector.detectMultiScale(image, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        # construct a list of bounding boxes from the detection
        rects = [(int(x), int(y), int(x + w), int(y + h)) for (x, y, w, h) in rects]

        # update the data dictionary with the faces detected
        data.update({"num_faces": len(rects), "faces": rects, "success": True})
    # return a JSON response
    return JsonResponse(data)


def _grab_image(path=None, stream=None, url=None):
    # if the path is not None, then load the image from disk
    if path is not None:
        image = cv2.imread(path)
    # otherwise, the image does not reside on disk
    else:
        # if the URL is not None, then download the image
        if url is not None:
            resp = urlopen(url)
            data = resp.read()
        # if the stream is not None, then the image has been uploaded
        elif stream is not None:
            data = stream.read()
        # convert the image to a NumPy array and then read it into
        # OpenCV format
        image = np.asarray(bytearray(data), dtype="uint8")
        image = cv2.imdecode(image, cv2.IMREAD_COLOR)

    # return the image
    return image