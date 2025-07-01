# -*- coding: UTF-8 -*-
from django.contrib import messages
from django.contrib.admin.models import LogEntry, ADDITION, DELETION
from django.contrib.admin.utils import unquote
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction, router
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.utils.encoding import force_str

from bd.models import LogQuery, get_deleted_objects, LogEntryLogin
from decorators import secure_module
from bd.forms import *
from sga.commonviews import adduserdata
from django.db import connection, transaction
from django.template import Context
import sys
from django.template.loader import get_template
from sga.funciones import log, puede_realizar_accion, puede_realizar_accion_is_superuser, logquery, convertir_fecha, \
    resetear_clave
from sga.models import Persona, LogEntryBackup, LogEntryBackupdos, AgregacionEliminacionMaterias, Inscripcion, Modulo, \
    ModuloGrupo, VisitaModulos
from sga.templatetags.sga_extras import encrypt
from django.db.models import Q, Sum, Count, Max, F
from django.db.models.functions import Cast
from django.db.models import FloatField


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = 'Visitas de Modulos del Sistema'

                desde, hasta, criterio, filtro, url_vars = request.GET.get("desde", ''), request.GET.get("hasta", ''), request.GET.get("criterio",''), Q(status=True), ''

                if desde:
                    data["desde"] = desde
                    url_vars += "&desde={}".format(desde)
                    filtro = filtro & Q(fecha_visita__gte=desde)

                if hasta:
                    data["hasta"] = hasta
                    url_vars += "&hasta={}".format(hasta)
                    filtro = filtro & Q(fecha_visita__lte=hasta)
                data["url_vars"] = url_vars
                visitas_ = VisitaModulos.objects.filter(filtro).order_by('-pk')
                topvisitas = visitas_.values_list('modulo_url', flat=True).annotate(visitas=Count('modulo')).values('modulo__url', 'modulo__nombre', 'visitas', 'modulo__icono').order_by('-visitas')
                data['topvisitas'] = topvisitas
                data['no_vistos'] = Modulo.objects.filter(status=True, activo=True).exclude(id__in=visitas_.values_list('modulo__id', flat=True))
                return render(request, "adm_sistemas/modules/viewvisite.html", data)
            except Exception as ex:
                msg_ex = 'Error on line {} - {}'.format(sys.exc_info()[-1].tb_lineno, str(ex))
                return JsonResponse({"result": False, 'data': str(msg_ex)})
