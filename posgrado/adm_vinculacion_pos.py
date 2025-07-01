import ast
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
from sga.models import CUENTAS_CORREOS, MateriaAsignada
import io
import xlsxwriter

@login_required(redirect_field_name='ret', login_url='/loginsga')
@last_access
#@secure_module
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
    carreras = persona.mis_carreras()
    if persona.es_administrativo():
        if request.method == 'POST':
            action = data['action'] = request.POST['action']

            if action == 'aprobarproyectovinculacion':
                try:
                    form = DetalleAprobacionProyectoForm(request.POST)
                    form.individual()
                    # if not int(encrypt(request.POST['iddap'])):
                    proyectov = ProyectoVinculacion.objects.get(pk=int(encrypt(request.POST['id'])))
                    if form.is_valid():
                        detalleaprobacion = DetalleAprobacionProyecto(observacion=form.cleaned_data['observacion'],
                                                                      estadoaprobacion=form.cleaned_data['estadoaprobacion'],
                                                                      proyectovinculacion_id=proyectov.pk,
                                                                      persona=persona)

                        proyectov.estadoaprobacion = form.cleaned_data['estadoaprobacion']
                        proyectov.save(request)
                        detalleaprobacion.save(request)
                        log(u'Agregó detalle aprobacion proyecto: %s' % proyectov, request, "aprobarproyectovinculacion")
                        return JsonResponse({'error': False, "message": 'Aprobado'}, safe=False)
                    else:
                        print([{k: v[0]} for k, v in form.errors.items()])
                        return JsonResponse({"result": "bad", "mensaje": u"Error al validar los datos."})
                    # else:
                    #     detalleap = DetalleAprobacionProyecto.objects.get(pk=int(encrypt(request.POST['iddap'])))
                    #     proyectov = ProyectoVinculacion.objects.filter(pk=detalleap.proyectovinculacion.pk, status=True).first()
                    #     if form.is_valid():
                    #         detalleap.observacion = form.cleaned_data['observacion']
                    #         detalleap.estadoaprobacion = proyectov.estadoaprobacion = form.cleaned_data[
                    #             'estadoaprobacion']
                    #         proyectov.save(request)
                    #         detalleap.save(request)
                    #         log(u'Editó aprobacion proyecto de vinculación posgrado: %s' % proyectov, request, "edit")
                    #         return JsonResponse({'error': False, "message": 'Aprobado'}, safe=False)
                    #     else:
                    #         print([{k: v[0]} for k, v in form.errors.items()])
                    #         return JsonResponse({"result": "bad", "mensaje": u"Error al validar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'aprobarmasivo':
                try:
                    form = DetalleAprobacionProyectoForm(request.POST)
                    form.individual()
                    if form.is_valid():
                        for proyecto in request.POST.getlist('proyecto'):
                            proyectov = ProyectoVinculacion.objects.get(pk=proyecto)
                            detalleaprobacion = DetalleAprobacionProyecto(observacion=form.cleaned_data['observacion'],
                                                                          estadoaprobacion=form.cleaned_data['estadoaprobacion'],
                                                                          proyectovinculacion_id=proyecto,
                                                                          persona=persona)

                            proyectov.estadoaprobacion = form.cleaned_data['estadoaprobacion']
                            proyectov.save(request)
                            detalleaprobacion.save(request)
                            log(u'Agregó detalle aprobacion proyecto: %s' % proyectov, request, "add")
                        return JsonResponse({'error': False, "message": 'Aprobado'}, safe=False)
                    else:
                        print([{k: v[0]} for k, v in form.errors.items()])
                        return JsonResponse({"result": "bad", "mensaje": u"Error al validar los datos."})

                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'aprobarseleccionados':
                try:
                    id_string = request.POST.get('ids', 0)
                    id_list = ast.literal_eval(id_string)
                    eParticipanteProyectoVinculacionPoss = ParticipanteProyectoVinculacionPos.objects.filter(status=True, pk__in=id_list)
                    for participante in eParticipanteProyectoVinculacionPoss:
                        detalleaprobacion = DetalleAprobacionProyecto(observacion='',
                                                                      estadoaprobacion=1,
                                                                      proyectovinculacion=participante.proyectovinculacion,
                                                                      persona=persona)

                        participante.proyectovinculacion.estadoaprobacion = 1
                        participante.proyectovinculacion.save(request)
                        detalleaprobacion.save(request)
                        log(u'Agregó detalle aprobacion proyecto: %s' % participante.proyectovinculacion, request, "add")
                    return JsonResponse({'error': False, "message": 'Aprobado'}, safe=False)


                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'rechazarseleccionados':
                try:
                    id_string = request.POST.get('ids', 0)
                    id_list = ast.literal_eval(id_string)
                    eParticipanteProyectoVinculacionPoss = ParticipanteProyectoVinculacionPos.objects.filter(status=True, pk__in=id_list)
                    for participante in eParticipanteProyectoVinculacionPoss:
                        detalleaprobacion = DetalleAprobacionProyecto(observacion='',
                                                                      estadoaprobacion=3,
                                                                      proyectovinculacion=participante.proyectovinculacion,
                                                                      persona=persona)

                        participante.proyectovinculacion.estadoaprobacion = 3
                        participante.proyectovinculacion.save(request)
                        detalleaprobacion.save(request)
                        log(u'Agregó detalle aprobacion proyecto: %s' % participante.proyectovinculacion, request, "add")
                    return JsonResponse({'error': False, "message": 'Rechazados'}, safe=False)


                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'editaprobarproyectovinculacion':
                try:
                    form = DetalleAprobacionProyectoForm(request.POST)
                    detalleap = DetalleAprobacionProyecto.objects.get(pk=int(encrypt(request.POST['id'])))
                    proyectov = ProyectoVinculacion.objects.filter(pk=detalleap.proyectovinculacion.pk, status=True).first()
                    if form.is_valid():
                        detalleap.observacion = form.cleaned_data['observacion']
                        detalleap.estadoaprobacion = proyectov.estadoaprobacion = form.cleaned_data['estadoaprobacion']
                        proyectov.save(request)
                        detalleap.save(request)
                        log(u'Editó aprobacion proyecto de vinculación posgrado: %s' % proyectov, request, "edit")
                        return JsonResponse({'error': False, "message": 'Aprobado'}, safe=False)
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

            if 'reportedetalleproyectos':
                try:
                    __author__ = 'Unemi'

                    filtro = Q(status=True)
                    fi = request.POST['fi'] if 'fi' in request.POST else ''
                    ff = request.POST['ff'] if 'ff' in request.POST else ''

                    if fi:
                        filtro = filtro & Q(fecha_creacion__gte=fi)

                    if ff:
                        filtro = filtro & Q(fecha_creacion__lte=ff)

                    if int(request.POST['ea']):
                        filtro = filtro & Q(proyectovinculacion__estadoaprobacion=request.POST['ea'])

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('%s' % hoy)
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 50)
                    ws.set_column(2, 2, 15)
                    ws.set_column(3, 3, 50)
                    ws.set_column(4, 4, 10)
                    ws.set_column(5, 5, 10)
                    ws.set_column(6, 6, 10)

                    formatotitulo_filtros = workbook.add_format({'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14})
                    formatosubtitulo_filtros = workbook.add_format({'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 12})
                    formatoceldacab = workbook.add_format({'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247','font_color': 'white'})
                    formatoceldaleft = workbook.add_format({'text_wrap': True, 'align': 'left', 'valign': 'vcenter', 'border': 1})
                    formatoceldacenter = workbook.add_format({'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})
                    ws.merge_range('A1:G1', "REPORTE DE PROYECTOS DE VINCULACIÓN", formatotitulo_filtros)
                    # pv = ParticipanteProyectoVinculacionPos.objects.filter(filtro).order_by('fecha_creacion', 'id')
                    # if pv:
                    #         ws.merge_range('A1:G1', "Desde: %s Hasta: %s" % (fi if fi else pv.first().fecha_creacion.date(), ff if ff else pv.last().fecha_creacion.date()), formatosubtitulo_filtros)
                    ws.write(1, 0, 'N°', formatoceldacab)
                    ws.write(1, 1, 'NOMBRES', formatoceldacab)
                    ws.write(1, 2, 'CEDULA', formatoceldacab)
                    ws.write(1, 3, 'TÍTULO DEL PROYECTO', formatoceldacab)
                    ws.write(1, 4, 'TIENE EVIDENCIA', formatoceldacab)
                    ws.write(1, 5, 'TIPO EVIDENCIA', formatoceldacab)
                    ws.write(1, 6, 'ESTADO', formatoceldacab)

                    filas_recorridas = 3
                    cont = 1
                    for pv in ParticipanteProyectoVinculacionPos.objects.filter(filtro).order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2'):
                        ws.write('A%s' % filas_recorridas, str(cont), formatoceldacenter)
                        ws.write('B%s' % filas_recorridas, str(pv.inscripcion.persona.nombre_completo_inverso()), formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, str(pv.inscripcion.persona.identificacion()), formatoceldacenter)
                        ws.write('D%s' % filas_recorridas, str(pv.proyectovinculacion.titulo), formatoceldaleft)
                        ws.write('E%s' % filas_recorridas, 'SI' if pv.evidencia else 'NO', formatoceldacenter)
                        ws.write('F%s' % filas_recorridas, 'PDF' if pv.tipoevidencia == 1 else 'LINK', formatoceldacenter)
                        ws.write('G%s' % filas_recorridas, str(pv.proyectovinculacion.get_estadoaprobacion_display()), formatoceldacenter)
                        filas_recorridas += 1
                        cont += 1

                    workbook.close()
                    output.seek(0)
                    filename = 'detalle_proyectos_vinculacion.xlsx'
                    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path + '?info=Error de conexión.')
        else:
            if 'info' in request.GET:
                data['info'] = request.GET['info']

            if 'action' in request.GET:
                action = data['action'] = request.GET['action']
                if action == 'aprobarproyectovinculacion':
                    try:
                        if DetalleAprobacionProyecto.objects.filter(proyectovinculacion_id=int(encrypt(request.GET['id'])), status=True).exists():
                            detalle = DetalleAprobacionProyecto.objects.filter(proyectovinculacion_id=int(encrypt(request.GET['id'])), status=True).first()
                            form = DetalleAprobacionProyectoForm(initial=model_to_dict(detalle))
                            data['iddap'] = detalle.pk
                        else:
                            form = DetalleAprobacionProyectoForm()

                        form.individual()
                        data['form'] = form
                        data['id'] = int(encrypt(request.GET['id']))
                        template = get_template("adm_vinculacion_pos/modal/aprobarproyectovinculacion.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    except Exception as ex:
                        pass

                if action == 'editaprobarproyectovinculacion':
                    try:
                        detalle = DetalleAprobacionProyecto.objects.filter(proyectovinculacion_id=int(encrypt(request.GET['id'])), status=True).first()
                        form = DetalleAprobacionProyectoForm(initial=model_to_dict(detalle))
                        data['form'] = form
                        data['id'] = detalle.pk
                        template = get_template("adm_vinculacion_pos/modal/aprobarproyectovinculacion.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    except Exception as ex:
                        pass

                if action == 'mostrardetalleaprobacion_view':
                    try:
                        proyectov = ProyectoVinculacion.objects.filter(pk=int(encrypt(request.GET['id']))).first()
                        detalle = DetalleAprobacionProyecto.objects.filter(proyectovinculacion_id=proyectov.pk, status=True).order_by('fecha_creacion')
                        data['detalleaprobacion'] = detalle
                        data['proyectovinculacion'] = proyectov
                        data['estadochoices'] = ESTADO_PROYECTO_VINCULACION
                        template = get_template("adm_vinculacion_pos/modal/mostrardetalleaprobacion_view.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    except Exception as ex:
                        pass

                if action == 'aprobarmasivo':
                    try:
                        filtro = Q(proyectovinculacion__status=True) & Q(status=True) & Q(proyectovinculacion__estadoaprobacion=2)
                        search = request.GET.get('s', '')

                        if search:
                            if len(search.strip().split(' ')) > 1:
                                filtro = filtro & (Q(inscripcion__persona__apellido1__icontains=search.split(' ')[0]) | Q(inscripcion__persona__apellido2__icontains=search.split(' ')[1]) | Q(proyectovinculacion__titulo__icontains=search.strip()))
                            else:
                                filtro = filtro & (Q(proyectovinculacion__titulo__icontains=search.strip()) | Q(inscripcion__persona__cedula=search.strip()) | Q(inscripcion__persona__apellido1__icontains=search.strip()) | Q(inscripcion__persona__apellido2__icontains=search.strip()))

                        listado = ParticipanteProyectoVinculacionPos.objects.filter(filtro)
                        form = DetalleAprobacionProyectoForm()
                        form.masivo([(x.proyectovinculacion.id, f"{x.inscripcion.persona.nombre_completo_inverso()} - {x.proyectovinculacion.titulo if not len(x.proyectovinculacion.titulo) > 50 else x.proyectovinculacion.titulo[:50] }") for x in listado])
                        data['form'] = form
                        template = get_template("adm_vinculacion_pos/modal/aprobarproyectovinculacion.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    except Exception as ex:
                        pass

                if action == 'aprobarseleccionados':
                    try:
                        ids = request.GET.getlist('ids[]')
                        eParticipanteProyectoVinculacionPoss = ParticipanteProyectoVinculacionPos.objects.filter(status=True, pk__in=ids)
                        data['eParticipanteProyectoVinculacionPoss'] = eParticipanteProyectoVinculacionPoss
                        data['ids'] = ids
                        template = get_template('adm_vinculacion_pos/modal/modalViewSeleccionado.html')
                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", 'data': json_content})

                        return render(request, '', data)
                    except Exception as ex:
                        pass
                if action == 'rechazarseleccionados':
                    try:
                        ids = request.GET.getlist('ids[]')
                        eParticipanteProyectoVinculacionPoss = ParticipanteProyectoVinculacionPos.objects.filter(status=True, pk__in=ids)
                        data['eParticipanteProyectoVinculacionPoss'] = eParticipanteProyectoVinculacionPoss
                        data['ids'] = ids
                        template = get_template('adm_vinculacion_pos/modal/modalViewSeleccionado.html')
                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", 'data': json_content})

                        return render(request, '', data)
                    except Exception as ex:
                        pass


                return HttpResponseRedirect('/adm_vinculacion_pos?info=Error de conexión.')
            else:

                data['title'] = u'Proyectos de vinculación'
                filtro = Q(proyectovinculacion__status=True) & Q(status=True)
                search, estado, url_vars = request.GET.get('s', ''), request.GET.get('ea', '2'), ''
                data['numperpage'] = num = 15
                # listadoinscripciones = ParticipanteProyectoVinculacionPos.objects.values_list('inscripcion_id', flat=True).filter(status=True)
                # data['materiaasignada'] = MateriaAsignada.objects.filter(matricula__inscripcion__in=listadoinscripciones, status=True).distinct()

                if search:
                    if len(search.strip().split(' ')) > 1:
                        filtro = filtro & (Q(inscripcion__persona__apellido1__icontains=search.split(' ')[0]) | Q(inscripcion__persona__apellido2__icontains=search.split(' ')[1]) | Q(proyectovinculacion__titulo__icontains=search.strip()))
                    else:
                        filtro = filtro & (Q(proyectovinculacion__titulo__icontains=search.strip()) | Q(inscripcion__persona__cedula=search.strip()) | Q(inscripcion__persona__apellido1__icontains=search.strip()) | Q(inscripcion__persona__apellido2__icontains=search.strip()))
                    url_vars += '&s=' + search
                    data['s'] = search

                if int(estado):
                    filtro = filtro & (Q(proyectovinculacion__estadoaprobacion=estado))
                    url_vars += '&ea=' + estado
                    data['ea'] = estado
                if persona.usuario.is_superuser:
                    listado = ParticipanteProyectoVinculacionPos.objects.filter(filtro)
                else:
                    listado = ParticipanteProyectoVinculacionPos.objects.filter(filtro).filter( inscripcion__carrera__in= carreras)
                paging = MiPaginador(listado , num)
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
                data['email_domain'] = EMAIL_DOMAIN
                data['proyectosvinculacion'] = page.object_list
                data['url_vars'] = url_vars
                data['estadochoices'] = ESTADO_PROYECTO_VINCULACION
                data['count'] = ParticipanteProyectoVinculacionPos.objects.values('id').filter(filtro).count()
                return render(request, 'adm_vinculacion_pos/view.html', data)
    else:
        return HttpResponseRedirect("/?info=Usted no pertenece al grupo de administrativos.")
