# -*- coding: UTF-8 -*-
from django.contrib import messages
from django.contrib.admin.models import LogEntry, ADDITION, DELETION
from django.contrib.admin.utils import unquote
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction, router
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
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
# @secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'cambiar_lugar_grupo':
            try:
                with transaction.atomic():
                    c_modulos = request.POST.getlist('c_modulos', [])
                    for x in c_modulos:
                        cm = json.loads(x)
                        cm["pk_origen"] = int(cm["pk_origen"])
                        cm["pk_destino"] = int(cm["pk_destino"])
                        cm["orden"] = int(cm["orden"])
                        if cm["pk_destino"] > 0:
                            mg_origen = ModuloCategorias.objects.get(pk=cm["pk_origen"])
                            mg_destino = ModuloCategorias.objects.get(pk=cm["pk_destino"])
                            modulo = Modulo.objects.get(pk=cm['pk_modulo'])
                            modulo.orden = cm["orden"]
                            modulo.save(request)
                            modulo.categorias.remove(mg_origen)
                            modulo.categorias.add(mg_destino)
                            modulo.save(request)
                    # log(request, mg_destino, 'Se cambió un módulo de grupo', modulo.nombre)
                    messages.success(request, "Grupos de urls cambiados correctamente")
            except ValueError as e:
                messages.error(request, str(e))
            except Exception as ex:
                messages.error(request, "Hubo un error, intente nuevamente")
            return redirect(request.path)
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = 'Arbol de Categorias SGA '
                data['categorias'] = ModuloCategorias.objects.filter(status=True).order_by('prioridad')
                return render(request, "adm_sistemas/modules/viewcategoriassga.html", data)
            except Exception as ex:
                msg_ex = 'Error on line {} - {}'.format(sys.exc_info()[-1].tb_lineno, str(ex))
                return JsonResponse({"result": False, 'data': str(msg_ex)})
