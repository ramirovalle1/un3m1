from django.views.decorators import gzip
from django.shortcuts import render
from django.http.response import StreamingHttpResponse, HttpResponseServerError
from faceid.camera import VideoCamera


# Create your views here.


def index(request):
    return render(request, 'faceid/stream.html')


def gen(camera):
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

@gzip.gzip_page
def video_feed(request):
    try:
        cam = VideoCamera()
        return StreamingHttpResponse(gen(cam), content_type='multipart/x-mixed-replace; boundary=frame')
    except HttpResponseServerError as ex:  # This is bad! replace it with proper handling
        print(f"aborted: {ex.__str__()}")