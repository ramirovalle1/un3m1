# -*- coding: latin-1 -*-
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import last_access

@last_access
@transaction.atomic()
def view(request):
    data = {}
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = 'About'
                return render(request, "about1.html", data)
            except Exception as ex:
                pass
