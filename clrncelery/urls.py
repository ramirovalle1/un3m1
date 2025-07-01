from django.urls import path, include

urlpatterns = [path(r'^celery-progress/', include('celery_progress.urls'))]
