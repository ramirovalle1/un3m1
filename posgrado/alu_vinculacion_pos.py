import random
import sys
import calendar
from datetime import datetime, timedelta, date

import openpyxl
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
import xlwt
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template import Context
from django.template.loader import get_template
from django.urls import reverse
from xlwt import *
from django.shortcuts import render, redirect
from decorators import secure_module, last_access
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from .models import *
from django.db.models import Sum, Q, F, FloatField
from .forms import *
from sga.funciones import log, generar_nombre, convertir_fecha_invertida, convertir_fecha, MiPaginador
from sga.templatetags.sga_extras import encrypt
from sga.tasks import send_html_mail
from sga.models import CUENTAS_CORREOS, Inscripcion


@login_required(redirect_field_name='ret', login_url='/loginsga')
@last_access
# @secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    hoy = datetime.now().date()
    usuario = request.user
    data['persona'] = persona = request.session['persona']
    periodo = request.session['periodo']
    perfilprincipal = request.session['perfilprincipal']
    data['email_domain'] = EMAIL_DOMAIN

    if persona.es_estudiante() or persona.es_inscripcionaspirante():
        if request.method == 'POST':
            data = {}
            action = data['action'] = request.POST['action']

            if action == 'addproyectovinculacion':
                try:
                    form = ProyectoVinculacionForm(request.POST, request.FILES)
                    valid_ext, file = ['.pdf', '.PDF'], None

                    if 'evidencia' in request.FILES:
                        file = request.FILES['evidencia']
                        if file:
                            if file.size > 4194304:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo es mayor a 4 Mb."})
                            else:
                                newfilesd = file._name
                                ext = newfilesd[newfilesd.rfind("."):]

                                if ext in valid_ext:
                                    file._name = generar_nombre("evidencia_", file._name)
                                else:
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, Solo archivos con extención .pdf"})

                    inscripcion = Inscripcion.objects.filter(persona=persona, coordinacion_id=7, activo=True, status=True).order_by('-id').first()
                    if form.is_valid():
                        proyectovinculacion = ProyectoVinculacion(titulo=form.cleaned_data['titulo'], descripcion=form.cleaned_data['descripcion'].strip().upper())
                        proyectovinculacion.save(request)
                        participanteproyecto = ParticipanteProyectoVinculacionPos(inscripcion=inscripcion,
                                                                                  proyectovinculacion_id=proyectovinculacion.pk,
                                                                                  tipoevidencia=form.cleaned_data['tipoevidencia'])

                        if int(form.cleaned_data['tipoevidencia']) == 1:
                            if file and participanteproyecto:
                                participanteproyecto.evidencia = file
                        else:
                            if 'evidencia' in request.POST:
                                if len(request.POST.getlist('evidencia')):
                                    participanteproyecto.evidencia = request.POST.getlist('evidencia')[0].strip()

                        participanteproyecto.save(request)
                        log(u'Adiciono proyecto de vinculacion: %s' % proyectovinculacion, request, "add")
                        log(u'Adiciono participante de proyecto de vinculacion: %s' % participanteproyecto, request, "add")
                        return JsonResponse({"result": 'ok'}, safe=False)
                    else:
                        print([{k: v[0]} for k, v in form.errors.items()])
                        return JsonResponse({"result": "bad", "mensaje": u"Error al validar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'editproyectovinculacion':
                try:
                    form = ProyectoVinculacionForm(request.POST, request.FILES)
                    participantepv = ParticipanteProyectoVinculacionPos.objects.get(pk=int(encrypt(request.POST['id'])))
                    proyectov = ProyectoVinculacion.objects.get(pk=participantepv.proyectovinculacion_id)
                    valid_ext, file = ['.pdf', '.PDF'], None

                    if 'evidencia' in request.FILES:
                        file = request.FILES['evidencia']
                        if file:
                            if file.size > 4194304:
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"Error, archivo es mayor a 4 Mb."})
                            else:
                                newfilesd = file._name
                                ext = newfilesd[newfilesd.rfind("."):]

                                if ext in valid_ext:
                                    file._name = generar_nombre("evidencia_", file._name)
                                else:
                                    return JsonResponse(
                                        {"result": "bad", "mensaje": u"Error, Solo archivos con extención .pdf"})

                    if form.is_valid():
                        proyectov.titulo = form.cleaned_data['titulo']
                        proyectov.descripcion = form.cleaned_data['descripcion'].strip().upper()
                        proyectov.save(request)

                        if int(form.cleaned_data['tipoevidencia']) == 1:
                            if file:
                                participantepv.evidencia = file
                        else:
                            if 'evidencia' in request.POST:
                                if len(request.POST.getlist('evidencia')):
                                    participantepv.evidencia = request.POST.getlist('evidencia')[0].strip()

                        participantepv.tipoevidencia = form.cleaned_data['tipoevidencia']
                        participantepv.save(request)

                        log(u'Editó proyecto de vinculacion: %s' % proyectov, request, "edit")
                        log(u'Editó participante de proyecto de vinculacion: %s' % participantepv, request, "edit")
                        return JsonResponse({"result": 'ok'}, safe=False)
                    else:
                        print([{k: v[0]} for k, v in form.errors.items()])
                        return JsonResponse({"result": "bad", "mensaje": u"Error al validar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'deleteproyectovinculacion':
                try:
                    ppv = ParticipanteProyectoVinculacionPos.objects.get(pk=int(encrypt(request.POST['id'])))
                    pv = ProyectoVinculacion.objects.get(pk=ppv.proyectovinculacion.pk)
                    ppv.status = pv.status = False
                    ppv.save(request)
                    pv.save(request)
                    log(u'Eliminó proyecto de vinculación: %s' % ppv, request, "del")
                    return JsonResponse({'error': False, "message": 'Registro eliminado correctamente.'}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})


            return HttpResponseRedirect('/alu_vinculacion_pos')
        # INICIO GET
        else:
            if 'action' in request.GET:
                action = data['action'] = request.GET['action']

                if action == 'addproyectovinculacion':
                    try:
                        data['title'] = "Agregar proyecto de vinculación"
                        form = ProyectoVinculacionForm()
                        data['form'] = form
                        data['tipoevidencia'] = 0
                        return render(request, "alu_vinculacion_pos/modal/addproyectovinculacion.html", data)
                    except Exception as ex:
                        pass

                if action == 'editproyectovinculacion':
                    try:
                        ppv = ParticipanteProyectoVinculacionPos.objects.get(pk=int(encrypt(request.GET['idppv'])))
                        data['title'] = "%s" % ppv.proyectovinculacion.titulo
                        form = ProyectoVinculacionForm(initial={'titulo': ppv.proyectovinculacion.titulo,
                                                                'descripcion': ppv.proyectovinculacion.descripcion,
                                                                'tipoevidencia': ppv.tipoevidencia})
                        data['form'] = form
                        data['tipoevidencia'] = ppv.tipoevidencia
                        data['id'] = ppv.pk
                        data['evidencia_value'] = ppv.evidencia
                        return render(request, "alu_vinculacion_pos/modal/addproyectovinculacion.html", data)
                    except Exception as ex:
                        pass

                if action == 'mostrardetalleaprobacion_view':
                    try:
                        proyectov = ProyectoVinculacion.objects.filter(pk=int(encrypt(request.GET['id']))).first()
                        # detalle = DetalleAprobacionProyecto.objects.filter(proyectovinculacion_id=proyectov.pk, status=True).order_by('fecha_creacion')
                        # data['detalleaprobacion'] = detalle
                        data['proyectovinculacion'] = proyectov
                        data['estadochoices'] = ESTADO_PROYECTO_VINCULACION
                        template = get_template("adm_vinculacion_pos/modal/mostrardetalleaprobacion_view.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    except Exception as ex:
                        pass

                return HttpResponseRedirect('/alu_vinculacion_pos')
            else:
                try:
                    data['title'] = u'Mis proyectos de vinculación'
                    filtro = Q(proyectovinculacion__status=True) & Q(status=True)
                    inscripcion = Inscripcion.objects.filter(persona=persona, coordinacion_id=7, activo=True, status=True).order_by('-id').first()
                    if inscripcion:
                        filtro = filtro & Q(inscripcion_id=inscripcion.pk)

                    search, url_vars = request.GET.get('s', ''), ''
                    if search:
                        filtro = filtro & (Q(proyectovinculacion__titulo__icontains=search.strip()) | Q(inscripcion__persona__cedula=search.strip()))
                        url_vars += '&s=' + search
                        data['search'] = search

                    listado = ParticipanteProyectoVinculacionPos.objects.filter(filtro)
                    paging = MiPaginador(listado, 20)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                            p = int(request.GET['page'])
                        else:
                            p = paginasesion
                        try:
                            page = paging.page(p)
                        except:
                            p = 1
                        page = paging.page(p)
                    except:
                        page = paging.page(p)
                    request.session['paginador'] = p
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['listado'] = page.object_list
                    data['totcount'] = listado.count()
                    data['email_domain'] = EMAIL_DOMAIN
                    data['proyectosvinculacion'] = page.object_list
                    # model = ParticipanteProyectoVinculacionPos.objects.filter(filtro).order_by('-id').first().proyectovinculacion if ParticipanteProyectoVinculacionPos.objects.filter(filtro).exists() else None
                    # if model:
                    #     data['notisolicitud'] = model.get_detalleaprobacion().order_by('-id').first().descripcion if len(model.get_detalleaprobacion().values('id')) == 2 else ''

                    return render(request, 'alu_vinculacion_pos/view.html', data)
                except Exception as ex:
                    import sys
                    print('Error on line {} exception --> {}'.format(sys.exc_info()[-1].tb_lineno, ex.__str__()))
                    return HttpResponseRedirect("/?info=Error de conexión")
    else:
        return HttpResponseRedirect("/?info=Usted no pertenece al grupo de estudiantes.")
