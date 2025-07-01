# -*- coding: latin-1 -*-
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.db import transaction, connection
from datetime import datetime
from django.db.models import Q
from django.template.loader import get_template
from decorators import secure_module, last_access
from sga.commonviews import adduserdata

from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt_alu, encrypt
from bib.models import Documento, ReferenciaWeb, ReservaDocumento


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    # if not perfilprincipal.es_estudiante():
    #     return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    # inscripcion = perfilprincipal.inscripcion
    if request.method == 'POST':
        action = request.POST['action']


    else:
            try:
                enespera = 1
                data['title'] = u'Bibliotecas Virtuales'


                data['enespera'] = enespera
                data['bibliotecas'] = ReferenciaWeb.objects.all().order_by('id')
                return render(request, "adm_bibliotecavirtual/view.html", data)
            except Exception as ex:
                pass
