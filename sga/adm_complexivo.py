# -*- coding: UTF-8 -*-

from django.db.models import Q, Avg
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template

from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import ComplexivoPeriodoForm, ApNeExamenComplexivoForm, PreInscripcionForm, MoverInscritoComplexivoForm
from sga.funciones import MiPaginador, generar_nombre, log
from sga.models import ComplexivoPeriodo, ExamenComplexivo, RecordAcademico, AsignaturaAyudantiaComplexivo, \
    Inscripcion, CUENTAS_CORREOS, ComplexivoPeriodo_Modalidades, Modalidad, Coordinacion, Carrera, NivelMalla
from xlwt import *
import random
from sga.tasks import conectar_cuenta, send_html_mail

@login_required(redirect_field_name='ret', login_url='/loginsga')
@transaction.atomic()
@last_access
@secure_module
def view(request):
    data = {}
    adduserdata(request, data)
    hoy = datetime.now().date()
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'add':
            try:
                f = ComplexivoPeriodoForm(request.POST)
                if f.is_valid():
                    if f.cleaned_data['fecha_inicio'] > f.cleaned_data['fecha_fin']:
                        return JsonResponse({"result": "bad", "mensaje": u"Ingrese bien las Fechas."})
                    # if ComplexivoPeriodo.objects.filter(fecha_inicio__lte=f.cleaned_data['fecha_inicio'], fecha_fin__gte=f.cleaned_data['fecha_inicio']).exists():
                    #     return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Ya existe un cronograma en las fechas ingresadas(Fecha Iniciio)."}), content_type="application/json")
                    # if ComplexivoPeriodo.objects.filter(fecha_inicio__lte=f.cleaned_data['fecha_fin'], fecha_fin__gte=f.cleaned_data['fecha_fin']).exists():
                    #     return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Ya existe un cronograma en las fechas ingresadas(Fecha Fin)."}), content_type="application/json")
                    # if ComplexivoPeriodo.objects.filter(fecha_inicio__gte=f.cleaned_data['fecha_inicio'], fecha_fin__lte=f.cleaned_data['fecha_fin']).exists():
                    #     return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Ya existe un cronograma en las fechas ingresadas(Fecha Inicio-Fin)."}), content_type="application/json")
                    complexivoperiodo = ComplexivoPeriodo(nombre=f.cleaned_data['nombre'],
                                                          fecha_inicio=f.cleaned_data['fecha_inicio'],
                                                          fecha_fin=f.cleaned_data['fecha_fin'],
                                                          observacion=f.cleaned_data['observacion'],
                                                          principal=f.cleaned_data['principal'],
                                                          tipocomplexivo=f.cleaned_data['tipocomplexivo'],
                                                          modulo=f.cleaned_data['modulo'],
                                                          # ayudantia=f.cleaned_data['ayudantia'],
                                                          cupo=f.cleaned_data['cupo'],
                                                          coordinacion=f.cleaned_data['coordinacion'],
                                                          nivel=f.cleaned_data['nivel']
                                                          )
                    complexivoperiodo.save(request)
                    # complexivoperiodo.carreras = f.cleaned_data['carreras']
                    for carr in f.cleaned_data['carreras']:
                        complexivoperiodo.carreras.add(carr)
                    log(u'Agrego periodo complexivo: %s' % complexivoperiodo, request, "add")
                    listamodalidades = Modalidad.objects.filter(pk__in=f.cleaned_data['modalidades'])
                    if listamodalidades:
                        for modalidad in listamodalidades:
                            detalle_modalidad_complexivoperiodo = ComplexivoPeriodo_Modalidades(complexivoperiodo=complexivoperiodo,
                                                                             modalidad=modalidad
                                                                             )
                            detalle_modalidad_complexivoperiodo.save(request)
                            log(u'Agrego detalle modalidad periodo complexivo: %s' % detalle_modalidad_complexivoperiodo, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'edit':
            try:
                complexivoperiodo = ComplexivoPeriodo.objects.get(pk=request.POST['id'])
                f = ComplexivoPeriodoForm(request.POST)
                if f.is_valid():
                    if f.cleaned_data['fecha_inicio'] > f.cleaned_data['fecha_fin']:
                        return JsonResponse({"result": "bad", "mensaje": u"Ingrese bien las Fechas."})
                    # if ComplexivoPeriodo.objects.filter(fecha_inicio__lte=f.cleaned_data['fecha_inicio'], fecha_fin__gte=f.cleaned_data['fecha_inicio']).exclude(pk=request.POST['id']).exists():
                    #     return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Ya existe un cronograma en las fechas ingresadas(Fecha Iniciio)."}), content_type="application/json")
                    # if ComplexivoPeriodo.objects.filter(fecha_inicio__lte=f.cleaned_data['fecha_fin'], fecha_fin__gte=f.cleaned_data['fecha_fin']).exclude(pk=request.POST['id']).exists():
                    #     return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Ya existe un cronograma en las fechas ingresadas(Fecha Fin)."}), content_type="application/json")
                    # if ComplexivoPeriodo.objects.filter(fecha_inicio__gte=f.cleaned_data['fecha_inicio'], fecha_fin__lte=f.cleaned_data['fecha_fin']).exclude(pk=request.POST['id']).exists():
                    #     return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Ya existe un cronograma en las fechas ingresadas(Fecha Inicio-Fin)."}), content_type="application/json")
                    complexivoperiodo.nombre = f.cleaned_data['nombre']
                    complexivoperiodo.fecha_inicio = f.cleaned_data['fecha_inicio']
                    complexivoperiodo.cupo = f.cleaned_data['cupo']
                    complexivoperiodo.fecha_fin = f.cleaned_data['fecha_fin']
                    complexivoperiodo.observacion = f.cleaned_data['observacion']
                    complexivoperiodo.principal = f.cleaned_data['principal']
                    complexivoperiodo.modulo = f.cleaned_data['modulo']
                    complexivoperiodo.tipocomplexivo = f.cleaned_data['tipocomplexivo']
                    # complexivoperiodo.ayudantia = f.cleaned_data['ayudantia']
                    complexivoperiodo.coordinacion = f.cleaned_data['coordinacion']
                    # complexivoperiodo.carreras = f.cleaned_data['carreras']
                    complexivoperiodo.carreras.clear()
                    for carr in f.cleaned_data['carreras']:
                        complexivoperiodo.carreras.add(carr)
                    complexivoperiodo.nivel = f.cleaned_data['nivel']
                    complexivoperiodo.save(request)
                    log(u'Modifico periodo complexivo: %s' % complexivoperiodo, request, "edit")
                    listamodalidades = Modalidad.objects.filter(pk__in=f.cleaned_data['modalidades'])
                    listamodalidades_complexivoperiodo = ComplexivoPeriodo_Modalidades.objects.filter(complexivoperiodo=complexivoperiodo)
                    log(u'Elimino detalle modalidad periodo complexivo: %s' % listamodalidades_complexivoperiodo,request, "del")
                    listamodalidades_complexivoperiodo.delete()
                    if listamodalidades:
                        for modalidad in listamodalidades:
                            detalle_modalidad_complexivoperiodo = ComplexivoPeriodo_Modalidades(
                                complexivoperiodo=complexivoperiodo,
                                modalidad=modalidad
                                )
                            detalle_modalidad_complexivoperiodo.save(request)
                            log(u'Agrego detalle modalidad periodo complexivo: %s' % detalle_modalidad_complexivoperiodo,request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addestudiante':
            try:
                form = PreInscripcionForm(request.POST)
                if form.is_valid():
                    grupo = ComplexivoPeriodo.objects.get(pk=request.POST['id'])
                    if not int(form.cleaned_data['estudiante']) > 0:
                        return JsonResponse({"result": "bad", "mensaje": u"Ingrese un estudiante."})
                    inscripcion = Inscripcion.objects.get(pk=int(form.cleaned_data['estudiante']), status=True)
                    if grupo.examencomplexivo_set.filter(status=True, inscripcion=inscripcion).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El estudiante que ingreso ya existe."})
                    examencomplexivo = ExamenComplexivo(inscripcion=inscripcion, complexivoperiodo=grupo)
                    examencomplexivo.save(request)
                    send_html_mail("PreInscripción", "emails/prematricula.html", {'sistema': request.session['nombresistema'], 'examencomplexivo': examencomplexivo}, inscripcion.persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[4][1])
                    log(u'Adiciono al alumno %s al complexivo: %s' % (inscripcion.persona, grupo), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos.(%s)" % ex})

        if action == 'edit_estado':
            try:
                f = ApNeExamenComplexivoForm(request.POST, request.FILES)
                if f.is_valid():
                    examencomplexivo = ExamenComplexivo.objects.get(pk=request.POST['id'])
                    if examencomplexivo.estadosolicitud in [ 4, 5, 6]:
                        return JsonResponse({"result": "bad", "mensaje": u"El registro esta en uso."})
                    examencomplexivo.estadosolicitud = f.data['est']
                    examencomplexivo.observacion = f.cleaned_data['observacion']
                    newfile = None
                    if 'informe' in request.FILES:
                        newfile = request.FILES['informe']
                        newfile._name = generar_nombre("informe_decano_", newfile._name)
                        examencomplexivo.informe = newfile
                    examencomplexivo.save(request)
                    mensaje = 'Aprobar' if examencomplexivo.estadosolicitud == 2 else 'Negar'
                    log(u'%s solicitud complexivo: %s' %(mensaje, examencomplexivo), request, "edit")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delete':
            try:
                complexivoperiodo = ComplexivoPeriodo.objects.get(pk=request.POST['id'])
                complexivoperiodo.delete()
                log(u'Elimino periodo complexivo: %s' % complexivoperiodo, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'mover':
            try:
                form = MoverInscritoComplexivoForm(request.POST)
                if form.is_valid():
                    inscrito = ExamenComplexivo.objects.get(pk=request.POST['id'])
                    inscrito.complexivoperiodo_id= form.cleaned_data['curso']
                    inscrito.save()
                log(u'movió  inscrito %s de periodo complexivo' % (inscrito), request, "del")
                return JsonResponse({"result": False}, safe=False)

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Adicionar Pre-inscripcion'
                    data['form'] = ComplexivoPeriodoForm(initial={'modalidades': Modalidad.objects.all()})
                    return render(request, 'adm_complexivo/add.html', data)
                except Exception as ex:
                    pass
            if action == 'carreras':
                try:
                    carreras = []
                    id = request.GET['coordinacion'] if not request.GET['coordinacion'] == '' else 0
                    if Coordinacion.objects.filter(id=id).exists():
                        for c in Coordinacion.objects.get(id=id).carrera.filter(nombre__icontains=request.GET['q']):
                            carreras.append({'id': c.id, 'text': c.nombre })
                    return JsonResponse(carreras, safe=False)
                except Exception as e:
                    pass
            if action == 'modalidades':
                try:
                    modalidades = []
                    if request.GET['carreras'] != 'null':
                        carreras = request.GET['carreras'].split(',')
                        modali = Carrera.objects.filter(id__in=carreras).values('modalidad').distinct()
                        for m in Modalidad.objects.filter(status=True, id__in=modali):
                            modalidades.append({'id': m.id, 'text': m.nombre })
                    else:
                        for m in Modalidad.objects.filter(status=True):
                            modalidades.append({'id': m.id, 'text': m.nombre})
                    return JsonResponse(modalidades, safe=False)
                except Exception as e:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Modificar Pre-inscripcion'
                    data['periodolectivo'] = periodo = ComplexivoPeriodo.objects.get(pk=request.GET['id'])
                    mod_ids = periodo.complexivoperiodo_modalidades_set.values_list('modalidad_id').all()
                    modalidades = Modalidad.objects.filter(pk__in=mod_ids)
                    data['form'] = ComplexivoPeriodoForm(initial={'nombre': periodo.nombre,
                                                                  'fecha_inicio': periodo.fecha_inicio,
                                                                  'fecha_fin': periodo.fecha_fin,
                                                                  'cupo': periodo.cupo,
                                                                  'observacion': periodo.observacion,
                                                                  'modulo': periodo.modulo,
                                                                  'tipocomplexivo': periodo.tipocomplexivo,
                                                                  # 'ayudantia': periodo.ayudantia,
                                                                  'principal': periodo.principal,
                                                                  'nivel': periodo.nivel,
                                                                  'coordinacion': periodo.coordinacion,
                                                                  'carreras': periodo.carreras.all(),
                                                                  'modalidades': modalidades
                                                                  })
                    return render(request, 'adm_complexivo/edit.html', data)
                except Exception as ex:
                    pass

            if action == 'delete':
                try:
                    data['title'] = u'Eliminar cronograma de Pre-inscripcion'
                    data['periodo'] = ComplexivoPeriodo.objects.get(pk=request.GET['id'])
                    return render(request, 'adm_complexivo/delete.html', data)
                except Exception as ex:
                    pass

            if action == 'edit_estado':
                try:
                    estado = request.GET['est']
                    mensaje = 'Aprobar' if estado == '2' else 'Negar'
                    data['title'] = u'{} solicitud'.format(mensaje)
                    data['periodo'] = periodo = ExamenComplexivo.objects.get(pk=request.GET['id'])
                    data['idins'] = request.GET['idins']
                    data['est'] = estado
                    form = ApNeExamenComplexivoForm(initial={'estadosolicitud':estado})
                    form.aprobar_rechazar()
                    data['form'] = form
                    return render(request, 'adm_complexivo/edit_estado.html', data)
                except Exception as ex:
                    pass

            if action == 'reporte':
                try:
                    periodo = request.GET['periodo']
                    complexivo = ComplexivoPeriodo.objects.get(id=periodo)
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    subtitle = easyxf('font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    ws.write_merge(0, 0, 0, 14, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 14, complexivo.nombre, subtitle)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=exp_xls_complexivo_' + random.randint(1, 10000).__str__() + '.xls'

                    columns = [
                        (u"PERIODO", 6000),
                        (u"FACULTAD", 12000),
                        (u"CARRERA", 12000),
                        (u"NIVEL", 6000),
                        (u"CEDULA", 6000),
                        (u"ALUMNO", 12000),
                        (u"CELULAR", 6000),
                        (u"CONVENCIONAL", 6000),
                        (u"EMAIL", 10000),
                        (u"EMAIL INSTITUCIONAL", 10000),
                        (u"EGRESADO", 4000),
                        (u"INSCRIPCION", 4000),
                        (u"PROMEDIO", 4000),
                        (u"ASIGNATURA", 6000),
                        (u"ESTADO", 6000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    inscritos = ExamenComplexivo.objects.filter(complexivoperiodo=int(periodo)).order_by("inscripcion__coordinacion__nombre", "inscripcion__carrera__nombre", "inscripcion__persona")
                    row_num = 4

                    for r in inscritos:
                        m = r.inscripcion.mi_nivel()
                        promgeneral = RecordAcademico.objects.filter(inscripcion=r.inscripcion,validapromedio=True, aprobada=True).aggregate(promedio=Avg('nota'))['promedio']
                        if promgeneral:
                            promediogeneral = round(promgeneral, 2)
                        else:
                            promediogeneral = 0
                        nomasginatura = ''
                        if AsignaturaAyudantiaComplexivo.objects.filter(examencomplexivo=r).exists():
                            complexivoasignatura = AsignaturaAyudantiaComplexivo.objects.get(examencomplexivo=r)
                            nomasginatura = complexivoasignatura.asignatura.nombre
                        nivel = m.nivel.nombre if m else ""
                        ws.write(row_num, 0, r.complexivoperiodo.nombre, font_style2)
                        ws.write(row_num, 1, r.inscripcion.coordinacion.nombre, font_style2)
                        ws.write(row_num, 2, r.inscripcion.carrera.nombre, font_style2)
                        ws.write(row_num, 3, nivel, font_style2)
                        ws.write(row_num, 4, r.inscripcion.persona.cedula, font_style2)
                        ws.write(row_num, 5, r.inscripcion.persona.nombre_completo_inverso(), font_style2)
                        ws.write(row_num, 6, r.inscripcion.persona.telefono if r.inscripcion.persona.telefono else "", font_style2)
                        ws.write(row_num, 7, r.inscripcion.persona.telefono_conv if r.inscripcion.persona.telefono_conv else "", font_style2)
                        ws.write(row_num, 8, r.inscripcion.persona.email if r.inscripcion.persona.email else "", font_style2)
                        ws.write(row_num, 9, r.inscripcion.persona.emailinst if r.inscripcion.persona.emailinst else "", font_style2)
                        ws.write(row_num, 10, "SI" if r.egresado else "NO", font_style2)
                        ws.write(row_num, 11, r.inscripcion.id, font_style2)
                        ws.write(row_num, 12, promediogeneral, font_style2)
                        ws.write(row_num, 13, nomasginatura, font_style2)
                        ws.write(row_num, 14, r.get_estadosolicitud_display(), font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            if action == 'inscritos':
                try:
                    data['title'] = u'Inscritos en Pre-inscripcion'
                    data['idins'] = request.GET['id']
                    data['complexivo'] = complexivo = ComplexivoPeriodo.objects.get(id=int(request.GET['id']))
                    solicitudes = solicitudes_aux = complexivo.examencomplexivo_set.filter(status=True)
                    carreras = Carrera.objects.filter(id__in=solicitudes.values_list('inscripcion__carrera_id', flat=True).distinct())
                    search = None
                    tipo = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        ss = search.split(' ')
                        if len(ss) == 1:
                            solicitudes = solicitudes.filter(Q(inscripcion__carrera__nombre__icontains=search) |
                                                                Q(inscripcion__coordinacion__nombre__icontains=search) |
                                                                Q(inscripcion__persona__nombres__icontains=search) |
                                                                Q(inscripcion__persona__apellido1__icontains=search) |
                                                                Q(inscripcion__persona__apellido2__icontains=search))
                        else:
                            solicitudes = solicitudes.filter(Q(inscripcion__persona__apellido1__icontains=ss[0]) &
                            Q(inscripcion__persona__apellido2__icontains=ss[1]))

                    carreraselect = 0
                    if 'c' in request.GET:
                        carreraselect = int(request.GET['c'])
                        if carreraselect > 0:
                            solicitudes = solicitudes.filter(inscripcion__carrera_id=carreraselect)

                    niveles = NivelMalla.objects.filter(
                        id__in=solicitudes.values_list('inscripcion__inscripcionnivel__nivel_id', flat=True).distinct())

                    nivelselect = 0
                    if 'niv' in request.GET:
                        nivelselect = int(request.GET['niv'])
                        if nivelselect > 0:
                            solicitudes = solicitudes.filter(inscripcion__inscripcionnivel__nivel_id=nivelselect)

                    estadosolicitudselect = 0
                    if 'ests' in request.GET:
                        estadosolicitudselect = int(request.GET['ests'])
                        if estadosolicitudselect > 0:
                            solicitudes = solicitudes.filter(estadosolicitud=estadosolicitudselect)

                    solicitudes = solicitudes.order_by("estadosolicitud",
                                         "inscripcion__coordinacion__nombre",
                                         "inscripcion__carrera__nombre",
                                         "inscripcion__persona")

                    paging = MiPaginador(solicitudes, 25)
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
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data['nivelselect'] = nivelselect
                    data['carreraselect'] = carreraselect
                    data['estadosolicitudselect'] = estadosolicitudselect
                    data['carreras'] = carreras
                    data['niveles'] = niveles
                    data['solicitudes'] = page.object_list
                    data['countsolicitudas'] = solicitudes.filter(estadosolicitud=1).count()
                    data['countaprobadas'] = solicitudes.filter(estadosolicitud=2).count()
                    data['countnegadas'] = solicitudes.filter(estadosolicitud=3).count()
                    data['counttotales'] = solicitudes_aux.count()
                    data['periodoc'] = int(request.GET['id'])
                    return render(request, "adm_complexivo/view_inscritos.html", data)
                except Exception as ex:
                    pass

            if action == 'buscarestudiante':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    grupo = ComplexivoPeriodo.objects.get(pk=request.GET['idg'])
                    idestudiantes = grupo.examencomplexivo_set.values_list('inscripcion__id', flat=False).filter(status=True)
                    inscripciones = Inscripcion.objects.filter(Q(status=True), Q(activo=True), Q(graduado__isnull=True)).exclude(Q(id__in=idestudiantes) | Q(retirocarrera__isnull=False))
                    if len(s) == 1:
                        inscripciones = inscripciones.filter(Q(persona__nombres__icontains=q)|Q(persona__apellido1__icontains=q)|Q(persona__apellido2__icontains=q)|Q(persona__cedula__contains=q), Q(status= True), coordinacion=grupo.coordinacion).distinct()[:25]
                    elif len(s) == 2:
                        inscripciones = inscripciones.filter((Q(persona__apellido1__contains=s[0]) & Q(persona__apellido2__contains=s[1]))| (Q(persona__nombres__icontains=s[0]) & Q(persona__nombres__icontains=s[1]))).filter(status=True, coordinacion=grupo.coordinacion).distinct()[:25]
                    else:
                        inscripciones = inscripciones.filter(Q(persona__apellido1__contains=s[0]) & Q(persona__apellido2__contains=s[1]) & Q(persona__nombres__icontains=s[2])).filter(status=True, coordinacion=grupo.coordinacion).distinct()[:25]
                    data = {"result": "ok","results": [{"id": x.id, "name": x.flexbox_repr()} for x in inscripciones]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'addestudiante':
                data['title'] = u'Adicionar Estudiante'
                try:
                    data['grupo'] = ComplexivoPeriodo.objects.get(pk=request.GET['id'])
                    data['form'] = PreInscripcionForm()
                    return render(request, 'adm_complexivo/addestudiantes.html', data)
                except Exception as ex:
                    pass


            if action == 'mover':
                try:
                    data['id'] = id = request.GET['id']
                    data['form2'] = MoverInscritoComplexivoForm()
                    template = get_template("adm_complexivo/moverinscrito.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'buscarmodulo':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    query = ComplexivoPeriodo.objects.filter(status=True)
                    if len(s) == 1:
                        per = query.filter((Q(nombre__icontains=q))).distinct()[:15]
                    elif len(s) == 2:
                        per = query.filter((Q(nombre__icontains=s[0]) & Q(nombre__icontains=s[1])) ).distinct()[:15]

                    data = {"result": "ok",
                            "results": [{"id": x.id, "name": str(x.nombre)}
                                        for x in per]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass


            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Cronograma de Pre-inscripcion'
            search = None
            tipo = None
            complexivos = ComplexivoPeriodo.objects.filter(status=True).order_by('-fecha_inicio', '-id')
            coordinaciones = Coordinacion.objects.filter(status=True, pk__in=complexivos.values_list('coordinacion_id', flat=True).distinct())
            niveles = NivelMalla.objects.filter(id__in=complexivos.values_list('nivel', flat=True).distinct())
            if 's' in request.GET:
                search = request.GET['s']
                complexivos = complexivos.filter(nombre__icontains=search).order_by('-fecha_inicio', '-id')

            coordinacionselect = 0
            if 'co' in request.GET:
                coordinacionselect = int(request.GET['co'])
                if coordinacionselect > 0:
                    complexivos = complexivos.filter(coordinacion_id=coordinacionselect)

            nivelselect = 0
            if 'niv' in request.GET:
                nivelselect = int(request.GET['niv'])
                if nivelselect > 0:
                    complexivos = complexivos.filter(nivel_id=nivelselect)

            modalidadselect = 0
            if 'm' in request.GET:
                modalidadselect = int(request.GET['m'])
                if modalidadselect > 0:
                    complexivos = complexivos.filter(complexivoperiodo_modalidades__modalidad_id=modalidadselect)

            paging = MiPaginador(complexivos, 25)

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
            data['rangospaging'] = paging.rangos_paginado(p)
            data['page'] = page
            data['search'] = search if search else ""
            data['coordinacionselect'] = coordinacionselect
            data['nivelselect'] = nivelselect
            data['modalidadselect'] = modalidadselect
            data['coordinaciones'] = coordinaciones
            data['niveles'] = niveles
            data['periodoscomplexivo'] = page.object_list
            return render(request, "adm_complexivo/view.html", data)
