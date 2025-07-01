import io
import json
import os
import sys
import pyqrcode
import xlwt
from django.core.paginator import Paginator
from xlwt import *
from django.db import transaction, connection
import random
from urllib.parse import urlencode
import sga
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Max, F, Sum
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404
from decorators import secure_module, last_access
from sagest.forms import ActivoFijoForm, ActivoTecnologicoForm, ComponenteActivoForm, GrupoBienForm, ComponenteCatalogoActivoForm
from sagest.models import ActivoFijo

from settings import DEBUG, SITE_ROOT
from decorators import secure_module
from sga.commonviews import adduserdata, obtener_reporte
from sga.funciones import MiPaginador, log
from django.template.loader import get_template
from django.forms import model_to_dict

from sga.templatetags.sga_extras import sumarfecha

from sga.funcionesxhtml2pdf import conviert_html_to_pdf, conviert_html_to_pdfsave, \
    conviert_html_to_pdfsaveinformeinventarioactivostecnologicos, \
    conviert_html_to_pdfsaveqrcertificado, conviert_html_to_pdf_name, \
    conviert_html_to_pdfsaveinformeactivo


@last_access
@transaction.atomic()
def view(request):
    data = {}
    h = 'https'
    if DEBUG:
        h = 'http'
    base_url = request.META['HTTP_HOST']
    try:
        if request.method == 'POST':
            pass
        else:
            if 'action' in request.GET:
                action = request.GET['action']
                if action == 'qr_presentacion':
                    try:

                        data['activo'] = ActivoFijo.objects.get(pk=int(request.GET['id']))
                        query = {'q': 'django encrypt link'}
                        encoded_query = urlencode(query)
                        return render(request, "at_activostecnologicos/detalleQR.html".format(encoded_query), data)
                    except Exception as ex:
                        return HttpResponseRedirect(request.path)
                else:
                    return HttpResponseRedirect(request.path)
            else:
                return HttpResponseRedirect(request.path)
    except Exception as ex:
        return HttpResponseRedirect(request.path)
