# -*- coding: latin-1 -*-
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.db.models.query_utils import Q
from datetime import datetime
from decorators import last_access
from sga.commonviews import adduserdata


@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    data['currenttime'] = datetime.now()
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        if 'action' in request.GET:
            action = request.GET['action']

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Chat'
                return render(request, "ws/chat/index.html", data)
            except Exception as ex:
                pass


def room(request, room_name):
    data = {}
    adduserdata(request, data)
    data['currenttime'] = datetime.now()
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        if 'action' in request.GET:
            action = request.GET['action']
            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Chat'
                data['room_name'] = room_name
                return render(request, 'ws/chat/room.html', data)
            except Exception as ex:
                pass
