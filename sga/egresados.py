# -*- coding: UTF-8 -*-
import random
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count
from django.db.models.query_utils import Q
from django.forms.models import model_to_dict
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.datetime_safe import datetime
from xlwt import *
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import EgresadoForm
from sga.funciones import MiPaginador, log
from sga.models import Egresado, Inscripcion, Carrera, AsignaturaMalla, RecordAcademico


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    miscarreras = Carrera.objects.filter(grupocoordinadorcarrera__group__in=persona.grupos()).distinct()
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'edit':
            try:
                egresado = Egresado.objects.get(pk=request.POST['id'])
                f = EgresadoForm(request.POST)
                if f.is_valid():
                    egresado.notaegreso = f.cleaned_data['notaegreso']
                    egresado.fechaegreso = f.cleaned_data['fechaegreso']
                    egresado.save(request)
                    log(u'Modifico egresado: %s' % egresado, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'del':
            try:
                egresado = Egresado.objects.get(pk=request.POST['id'])
                log(u'Elimino egresado: %s' % egresado, request, "del")
                egresado.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'actualizarlistos':
            try:
                inscripciones = Inscripcion.objects.annotate(materias=Count('recordacademico')).filter(cumplimiento=False, materias__gte=35).exclude(egresado__notaegreso__gt=0)
                for inscripcion in inscripciones:
                    inscripcion.actualizar_cumplimiento()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad"})

        elif action == 'egresar':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                f = EgresadoForm(request.POST)
                if f.is_valid():
                    if not Egresado.objects.filter(inscripcion=inscripcion).exists():
                        egresado = Egresado(inscripcion=inscripcion,
                                            # notaegreso=f.cleaned_data['notaegreso'],
                                            notaegreso=inscripcion.promedio_record(),
                                            fechaegreso=f.cleaned_data['fechaegreso'])
                        egresado.save(request)
                        log(u'Adiciono egresado: %s nota: %s' % (egresado, str(egresado.notaegreso)), request, "edit")
                    else:
                        egresado = Egresado.objects.filter(inscripcion=inscripcion)[0]
                    return JsonResponse({"result": "ok", "id": egresado.id})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Listado de alumnos egresados'
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'edit':
                try:
                    data['title'] = u'Editar egreso'
                    egresado = Egresado.objects.filter(inscripcion__carrera__in=miscarreras).get(pk=request.GET['id'])
                    initial = model_to_dict(egresado)
                    calif = 0
                    if egresado.notaegreso>0:
                        calif = egresado.notaegreso
                    else:
                        calif = egresado.inscripcion.promedio_record()

                    form = EgresadoForm(initial={'fechaegreso': egresado.fechaegreso,
                                                 'notaegreso': calif })
                    # form.deshabilitar_notaegreso()
                    data['egresado'] = egresado
                    data['form'] = form
                    return render(request, "egresados/edit.html", data)
                except Exception as ex:
                    pass

            elif action == 'del':
                try:
                    data['title'] = u'Borrar egreso'
                    data['egresado'] = Egresado.objects.filter(inscripcion__carrera__in=miscarreras).get(pk=request.GET['id'])
                    return render(request, "egresados/del.html", data)
                except Exception as ex:
                    pass

            elif action == 'egresar':
                try:
                    data['title'] = u'Egresar alumno'
                    inscripcion = Inscripcion.objects.filter(carrera__in=miscarreras).get(pk=request.GET['id'])
                    data['inscripcion'] = inscripcion
                    if inscripcion.recordacademico_set.exists():
                        fechaegreso = inscripcion.recordacademico_set.order_by('-fecha')[0].fecha
                    else:
                        fechaegreso = datetime.now().date()
                    form = EgresadoForm(initial={'fechaegreso': fechaegreso, 'notaegreso': inscripcion.promedio_record()})
                    form.deshabilitar_notaegreso()
                    data['form'] = form
                    return render(request, "egresados/egresar.html", data)
                except Exception as ex:
                    pass

            elif action == 'egresadosfalta':
                try:
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    ws.write_merge(0, 0, 0, 7, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=exp_xls_post_part_' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"CEDULA", 6000),
                        (u"NOMBRE", 6000),
                        (u"CARRERA", 6000),
                        (u"EMAIL", 6000),
                        (u"EMAIL INSTITUCIONAL", 6000),
                        (u"TELEFONO CONVENCIONAL", 4000),
                        (u"CELULAR", 6000),
                        (u"DIRECCION", 6000),
                        (u"NACIONALIDAD", 3000),
                        (u"SECCIÓN", 5000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]

                    row_num = 4
                    for inscripcion in Inscripcion.objects.filter(status=True).order_by('coordinacion', 'carrera'):
                        malla = inscripcion.carrera.malla()
                        asignaturas = AsignaturaMalla.objects.filter(malla=malla)
                        if asignaturas.count() > 0:
                            bandera = 0
                            for asignatura in asignaturas:
                                if bandera == 0:
                                    if not RecordAcademico.objects.filter(inscripcion=inscripcion,
                                                                          asignatura=asignatura.asignatura,
                                                                          aprobada=True, status=True).exists():
                                        bandera = 1
                            if bandera == 0:
                                if Egresado.objects.filter(inscripcion=inscripcion, status=True).exists():
                                    bandera = 1
                            if bandera == 0:
                                campo1 = inscripcion.persona.cedula
                                campo2 = inscripcion.persona.nombre_completo_inverso()
                                campo3 = malla.carrera.nombre
                                campo4 = inscripcion.persona.email
                                campo5 = inscripcion.persona.emailinst
                                campo6 = inscripcion.persona.telefono_conv
                                campo7 = inscripcion.persona.telefono
                                campo8 = inscripcion.persona.direccion_completa()
                                campo9 = inscripcion.persona.nacionalidad
                                campo10 = inscripcion.sesion.nombre

                                ws.write(row_num, 0, campo1, font_style2)
                                ws.write(row_num, 1, campo2, font_style2)
                                ws.write(row_num, 2, campo3, font_style2)
                                ws.write(row_num, 3, campo4, font_style2)
                                ws.write(row_num, 4, campo5, font_style2)
                                ws.write(row_num, 5, campo6, font_style2)
                                ws.write(row_num, 6, campo7, font_style2)
                                ws.write(row_num, 7, campo8, font_style2)
                                ws.write(row_num, 8, campo9, font_style2)
                                ws.write(row_num, 9, campo10, font_style2)
                                row_num += 1

                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            search = None
            ids = None
            inscripcionid = None
            if 's' in request.GET:
                search = request.GET['s']
                ss = search.split(' ')
                while '' in ss:
                    ss.remove('')
                if len(ss) == 1:
                    egresados = Egresado.objects.filter(inscripcion__carrera__in=miscarreras).filter(Q(inscripcion__persona__nombres__icontains=search) |
                                                                                                     Q(inscripcion__persona__apellido1__icontains=search) |
                                                                                                     Q(inscripcion__persona__apellido2__icontains=search) |
                                                                                                     Q(inscripcion__persona__cedula__icontains=search) |
                                                                                                     Q(inscripcion__persona__pasaporte__icontains=search) |
                                                                                                     Q(inscripcion__identificador__icontains=search)).distinct()
                else:
                    egresados = Egresado.objects.filter(inscripcion__carrera__in=miscarreras).filter(Q(inscripcion__persona__apellido1__icontains=ss[0]) &
                                                                                                     Q(inscripcion__persona__apellido2__icontains=ss[1])).distinct()
            elif 'inscripcionid' in request.GET:
                inscripcionid = request.GET['inscripcionid']
                egresados = Egresado.objects.filter(inscripcion__carrera__in=miscarreras).filter(inscripcion__id=inscripcionid)
            elif 'id' in request.GET:
                ids = request.GET['id']
                egresados = Egresado.objects.filter(inscripcion__carrera__in=miscarreras).filter(id=ids).order_by('inscripcion__persona')
            else:
                egresados = Egresado.objects.filter(inscripcion__carrera__in=miscarreras).order_by('inscripcion__persona')
            paging = MiPaginador(egresados, 25)
            p = 1
            try:
                paginasesion = 1
                if 'paginador' in request.session:
                    paginasesion = int(request.session['paginador'])
                if 'page' in request.GET:
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
            data['page'] = page
            data['rangospaging'] = paging.rangos_paginado(p)
            data['egresados'] = page.object_list
            data['search'] = search if search else ""
            data['inscripcionid'] = inscripcionid if inscripcionid else ""
            data['ids'] = ids if ids else ""
            return render(request, "egresados/view.html", data)