# -*- coding: latin-1 -*-
import json
import random
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from xlwt import *
from decorators import secure_module, last_access
from settings import BECA_MODELO_NUEVO
from sga.commonviews import adduserdata, obtener_reporte
from sga.forms import BecarioForm, ConsiderarForm
from sga.funciones import log, MiPaginador, puede_realizar_accion
from sga.models import InscripcionBecario, TipoBeca, Inscripcion, \
    Matricula, HistoriaRetirnoInscripcionBecario


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'edit':
            try:
                becario = InscripcionBecario.objects.get(pk=request.POST['id'])
                f = BecarioForm(request.POST)
                if f.is_valid():
                    tipobeca = f.cleaned_data['tipobeca']
                    if tipobeca.beneficiomonetario:
                        montobeneficio = f.cleaned_data['montobeneficio']
                        montomensual = f.cleaned_data['montomensual']
                        cantidadmeses = f.cleaned_data['cantidadmeses']
                        porciento = 0
                    else:
                        porciento = f.cleaned_data['porciento']
                        montobeneficio = 0
                        montomensual = 0
                        cantidadmeses = 0
                    becario.porciento = porciento
                    becario.montobeneficio = montobeneficio
                    becario.montomensual = montomensual
                    becario.cantidadmeses = cantidadmeses
                    becario.tipobeca = tipobeca
                    becario.tipobecarecibe = f.cleaned_data['tipobecarecibe']
                    becario.motivo = f.cleaned_data['motivo']
                    becario.save(request)
                    log(u'Actualizo becario: %s' % becario, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deshabilitar':
            try:
                becario = InscripcionBecario.objects.get(pk=request.POST['id'])
                f = ConsiderarForm(request.POST)
                if f.is_valid():
                    retiro = HistoriaRetirnoInscripcionBecario(becario=becario,
                                                               fecharetiro=datetime.now().date(),
                                                               motivoretiro=f.cleaned_data['motivo'])
                    retiro.save(request)
                    becario.activo = False
                    becario.save(request)
                    log(u'Retiro de becario: %s' % becario, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'habilitar':
            try:
                becario = InscripcionBecario.objects.get(pk=request.POST['id'])
                becario.activo = True
                becario.save(request)
                log(u'Habilito becario: %s' % becario, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'tipobeca':
            try:
                tipobeca = TipoBeca.objects.get(pk=request.POST['id'])
                return JsonResponse({"result": "ok", "economico": tipobeca.beneficiomonetario})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'asignarbeca':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                f = BecarioForm(request.POST)
                if f.is_valid():
                    if InscripcionBecario.objects.filter(inscripcion=inscripcion).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe un registro de becacario."})
                    tipobeca = f.cleaned_data['tipobeca']
                    if tipobeca.beneficiomonetario:
                        montomensual = f.cleaned_data['montomensual']
                        cantidadmeses = int(f.cleaned_data['cantidadmeses'])
                        porciento = 0
                        montobeneficio = round(montomensual * cantidadmeses, 2)
                    else:
                        porciento = f.cleaned_data['porciento']
                        montobeneficio = 0
                        montomensual = 0
                        cantidadmeses = 0
                    becario = InscripcionBecario(inscripcion=inscripcion,
                                                 porciento=porciento,
                                                 montomensual=montomensual,
                                                 cantidadmeses=cantidadmeses,
                                                 montobeneficio=montobeneficio,
                                                 tipobeca=tipobeca,
                                                 motivo=f.cleaned_data['motivo'],
                                                 fecha=datetime.now().date(),
                                                 tipobecarecibe=f.cleaned_data['tipobecarecibe'])
                    becario.save(request)
                    log(u'Adiciono becario: %s' % becario, request, "add")
                    return JsonResponse({"result": "ok", 'id': becario.id})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'aplicarbeca':
            try:
                matricula = Matricula.objects.get(pk=request.POST['id'])
                becario = matricula.inscripcion.beca_asignada()
                if matricula and matricula.becado:
                    return JsonResponse({"result": "bad", "mensaje": u"Ya una beca fue aplicada a esta matricula."})
                if becario.tipobeca.beneficiomonetario:
                    matricula.montomensual = becario.montomensual
                    matricula.cantidadmeses = becario.cantidadmeses
                    matricula.montobeneficio = becario.montobeneficio
                    matricula.porcientobeca = 0
                else:
                    matricula.porcientobeca = becario.porciento
                    matricula.montobeneficio = 0
                    matricula.montomensual = 0
                    matricula.cantidadmeses = 0
                matricula.beneficiomonetario = becario.tipobeca.beneficiomonetario
                matricula.becaexterna = becario.tipobeca.becaexterna
                matricula.observaciones = becario.motivo
                matricula.tipobeca = becario.tipobeca
                matricula.tipobecarecibe = becario.tipobecarecibe
                matricula.becado = True
                matricula.save(request)
                log(u'Aplicar beca a matricula: %s - %s [%s]' % (matricula, matricula.becado, matricula.id), request, "edit")
                return JsonResponse({"result": "ok", 'id': becario.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Listado de estudiantes becados'
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'edit':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_becas')
                    data['title'] = u'Editar becario'
                    data['becario'] = becario = InscripcionBecario.objects.get(pk=request.GET['id'])
                    form = BecarioForm(initial={'porciento': becario.porciento,
                                                'tipobeca': becario.tipobeca,
                                                'montobeneficio': becario.montobeneficio,
                                                'montomensual': becario.montomensual,
                                                'cantidadmeses': becario.cantidadmeses,
                                                'motivo': becario.motivo,
                                                'tipobecarecibe': becario.tipobecarecibe})
                    form.editar(becario.tipobeca)
                    data['form'] = form
                    return render(request, "adm_becarios/edit.html", data)
                except Exception as ex:
                    pass

            elif action == 'asignarbeca':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_becas')
                    data['title'] = u'Asignar una Beca'
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['id'])
                    data['form'] = BecarioForm()
                    return render(request, "adm_becarios/asignarbeca.html", data)
                except Exception as ex:
                    pass

            elif action == 'aplicarbeca':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_becas')
                    data['title'] = u'Aplica beca a matricula'
                    data['becario'] = InscripcionBecario.objects.get(pk=request.GET['id'])
                    data['matricula'] = Matricula.objects.get(pk=request.GET['idm'])
                    return render(request, "adm_becarios/aplicarbeca.html", data)
                except Exception as ex:
                    pass

            elif action == 'deshabilitar':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_becas')
                    data['title'] = u'Deshabilitar becario'
                    data['becario'] = InscripcionBecario.objects.get(pk=request.GET['id'])
                    data['form'] = ConsiderarForm(request.POST)
                    return render(request, "adm_becarios/deshabilitar.html", data)
                except Exception as ex:
                    pass

            elif action == 'habilitar':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_becas')
                    data['title'] = u'Habilitar becario'
                    data['becario'] = InscripcionBecario.objects.get(pk=request.GET['id'])
                    return render(request, "adm_becarios/habilitar.html", data)
                except Exception as ex:
                    pass

            elif action == 'becas':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_becas')
                    data['title'] = u'Listado de becas'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    data['reporte_0'] = obtener_reporte('historial_becas')
                    data['matriculas'] = inscripcion.matricula_set.filter(becado=True)
                    return render(request, "adm_becarios/becas.html", data)
                except Exception as ex:
                    pass

            elif action == 'descarga':
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
                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=exp_xls_post_part_' + random.randint(1, 10000).__str__() + '.xls'

                    columns = [
                        (u"CEDULA", 5000),
                        (u"ESTUDIANTE", 6000),
                        (u"TIPO BECA/MOTIVO", 6000),
                        (u"INSTITUCIÓN", 6000),
                        (u"PROM. RECORD", 6000),
                        (u"PORC. ACTUAL", 6000),
                        (u"VALOR MENSUAL", 6000),
                        (u"CANTIDAD MESES", 6000),
                        (u"MONTO TOTAL", 6000),
                        (u"BECA APLICADA", 6000),
                        (u"MATRICULA", 6000),
                        (u"PORC. PERIODO", 6000),
                        (u"MONTO PERIODO", 6000),
                        (u"FECHA", 6000),
                        (u"ACTIVO", 6000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]

                    becarios = InscripcionBecario.objects.all().order_by('-activo', 'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')
                    row_num = 4
                    for becario in becarios:
                        matricula = becario.inscripcion.matricula_periodo(periodo)
                        i = 0
                        campo1 = becario.inscripcion.persona.nombre_completo_inverso()

                        if becario.activo:
                            campo2 = becario.tipobeca.nombre
                        else:
                            campo2 = str(becario.datos_retiro().fecharetiro)+" - "+ becario.datos_retiro().motivoretiro

                        campo3 = ""
                        if becario.get_tipobecarecibe_display != 0:
                            campo3 = becario.get_tipobecarecibe_display()

                        campo4 = becario.inscripcion.promedio_record()

                        campo5 = ""
                        if becario.activo:
                            if not becario.tipobeca.beneficiomonetario:
                                campo5 = becario.porciento

                        campo6 = ""
                        if becario.activo:
                            if becario.tipobeca.beneficiomonetario:
                                campo6 = becario.montomensual

                        campo7 = ""
                        if becario.activo:
                            if becario.tipobeca.beneficiomonetario:
                                campo7 = becario.cantidadmeses

                        campo8 = ""
                        if becario.activo:
                            if becario.tipobeca.beneficiomonetario:
                                campo8 = becario.montobeneficio

                        campo9 = "NO"
                        if matricula and matricula.becado:
                            campo9 = "SI"

                        campo10 = "NO"
                        if matricula:
                            campo10 = "SI"

                        campo11 = ""
                        if matricula and matricula.becado:
                            if not matricula.beneficiomonetario:
                                campo11 = matricula.porcientobeca

                        campo12 = ""
                        if matricula and matricula.becado:
                            if matricula.beneficiomonetario:
                                campo12 = matricula.montobeneficio

                        campo13 = becario.fecha

                        campo14 = "NO"
                        if becario.activo:
                            campo14 = "SI"

                        campo15 = becario.inscripcion.persona.cedula

                        ws.write(row_num, 0, campo15, font_style2)
                        ws.write(row_num, 1, campo1, font_style2)
                        ws.write(row_num, 2, campo2, font_style2)
                        ws.write(row_num, 3, campo3, font_style2)
                        ws.write(row_num, 4, campo4, font_style2)
                        ws.write(row_num, 5, campo5, font_style2)
                        ws.write(row_num, 6, campo6, font_style2)
                        ws.write(row_num, 7, campo7, font_style2)
                        ws.write(row_num, 8, campo8, font_style2)
                        ws.write(row_num, 9, campo9, font_style2)
                        ws.write(row_num, 10, campo10, font_style2)
                        ws.write(row_num, 11, campo11, font_style2)
                        ws.write(row_num, 12, campo12, font_style2)
                        ws.write(row_num, 13, campo13, style1)
                        ws.write(row_num, 14, campo14, font_style2)
                        # while i < len(r):
                        #     # ws.write(row_num, i, r[i], font_style)
                        #     # ws.col(i).width = columns[i][1]
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass


            return HttpResponseRedirect(request.path)
        else:
            search = None
            tipo = None
            activo = None
            ids = None
            iid = None
            if 'id' in request.GET:
                ids = int(request.GET['id'])
                becarios = InscripcionBecario.objects.filter(id=ids).distinct()
            elif 'iid' in request.GET:
                iid = int(request.GET['iid'])
                becarios = InscripcionBecario.objects.filter(inscripcion__id=iid).distinct()
            elif 's' in request.GET:
                search = request.GET['s']
                ss = search.split(' ')
                if len(ss) == 1:
                    becarios = InscripcionBecario.objects.filter(Q(inscripcion__persona__nombres__icontains=search) |
                                                                 Q(inscripcion__persona__apellido1__icontains=search) |
                                                                 Q(inscripcion__persona__apellido2__icontains=search) |
                                                                 Q(inscripcion__persona__cedula__icontains=search) |
                                                                 Q(inscripcion__persona__pasaporte__icontains=search) |
                                                                 Q(inscripcion__identificador__icontains=search) |
                                                                 Q(inscripcion__inscripciongrupo__grupo__nombre__icontains=search) |
                                                                 Q(inscripcion__carrera__nombre__icontains=search) |
                                                                 Q(inscripcion__persona__usuario__username__icontains=search)).distinct().order_by('-activo', 'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')
                else:
                    becarios = InscripcionBecario.objects.filter(Q(inscripcion__persona__apellido1__icontains=ss[0]) &
                                                                 Q(inscripcion__persona__apellido2__icontains=ss[1])).distinct().order_by('-activo', 'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')
            else:
                becarios = InscripcionBecario.objects.all().order_by('-activo', 'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')
            if 't' in request.GET:
                tipo = int(request.GET['t'])
                if tipo > 0:
                    becarios = becarios.filter(tipobeca__id=tipo).distinct()
            if 'a' in request.GET:
                activo = int(request.GET['a'])
                if activo > 0:
                    if activo == 1:
                        becarios = becarios.filter(activo=True).distinct()
                    else:
                        becarios = becarios.filter(activo=False).distinct()
            paging = MiPaginador(becarios, 25)
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
            data['ids'] = ids if ids else ""
            data['iid'] = iid if iid else ""
            data['tipoid'] = tipo if tipo else ""
            data['activoid'] = activo if activo else ""
            data['becarios'] = page.object_list
            data['tipobecas'] = TipoBeca.objects.all()
            data['beca_modelo_nuevo'] = BECA_MODELO_NUEVO
            return render(request, "adm_becarios/view.html", data)