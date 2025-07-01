# -*- coding: UTF-8 -*-
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render


def view(request):
    data = {}

    if request.method == 'POST':
        action = request.POST['action']

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = 'Sitio sin internet'
            return render(request, "offline.html", data)
