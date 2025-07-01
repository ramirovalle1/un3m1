# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction, connection
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
import time
from xlwt import *
from django.template.loader import get_template
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import FechaDocenteParesForm
from sga.funciones import log, puede_realizar_accion, puede_realizar_accion_afirmativo
from sga.models import Profesor, Persona, DetalleInstrumentoEvaluacionParAcreditacion, ActividadDetalleInstrumentoPar, DetalleDistributivo, Coordinacion, \
    DocenteFechaPares, ProfesorDistributivoHoras, DetalleInstrumentoEvaluacionDirectivoAcreditacion


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    data['proceso'] = proceso = data['periodo'].proceso_evaluativoacreditacion()
    periodo = request.session['periodo']
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']
        coordinacion = Coordinacion.objects.get(pk=request.POST['idfacu'])
        if action == 'asignarevaluacionpar':
            try:
                lista = request.POST['listaprofesores']
                if lista:
                    elementos = lista.split('#')
                    for elemento in elementos:
                        individuales = elemento.split(',')
                        profesor = Profesor.objects.get(pk=int(individuales[0]))
                        for elementoevaluador in individuales[2].split(':'):
                            elementoactividades = elementoevaluador.split('=')
                            evaluador = Persona.objects.get(pk=int(elementoactividades[0]))
                            if not DetalleInstrumentoEvaluacionParAcreditacion.objects.filter(proceso=proceso, evaluado=profesor, coordinacion=coordinacion, evaluador=evaluador).exists():
                                detalle = DetalleInstrumentoEvaluacionParAcreditacion(proceso=proceso,
                                                                                      evaluado=profesor,
                                                                                      coordinacion=coordinacion,
                                                                                      evaluador=evaluador)
                                detalle.save(request)
                                for actividad in elementoactividades[1].split('-'):
                                    actividadperiodo = DetalleDistributivo.objects.get(pk=int(actividad))
                                    actividaddetalle = ActividadDetalleInstrumentoPar(detallepar=detalle,
                                                                                      detalledistributivo=actividadperiodo)
                                    actividaddetalle.save(request)
                log(u'Ingresó lista de pares en instrumento evaluacion: %s' % coordinacion, request, "edit")
                listahoras = []
                llenardocentes = []
                data['title'] = u'Seleccion de pares para evaluación de los profesores'
                data['profesoresevaluadores'] = Profesor.objects.filter(profesordistributivohoras__periodo=proceso.periodo, profesordistributivohoras__tablaponderacion__isnull=False).distinct()
                data['coordinacion'] = coordinacion
                listaprodoc = DetalleDistributivo.objects.values('distributivo__profesor','distributivo__profesor__persona__apellido1','distributivo__profesor__persona__apellido2','distributivo__profesor__persona__nombres','distributivo__profesor__coordinacion__alias','distributivo__profesor__categoria__nombre').filter(distributivo__periodo=proceso.periodo, criteriodocenciaperiodo__isnull=False, evaluapar=True, distributivo__profesor__coordinacion=coordinacion).distinct().order_by('distributivo__profesor__persona__apellido1')
                listaproinv = DetalleDistributivo.objects.values('distributivo__profesor','distributivo__profesor__persona__apellido1','distributivo__profesor__persona__apellido2','distributivo__profesor__persona__nombres','distributivo__profesor__coordinacion__alias','distributivo__profesor__categoria__nombre').filter(distributivo__periodo=proceso.periodo, criterioinvestigacionperiodo_id__isnull=False, evaluapar=True, distributivo__profesor__coordinacion=coordinacion).distinct().order_by('distributivo__profesor__persona__apellido1')
                listaproges = DetalleDistributivo.objects.values('distributivo__profesor','distributivo__profesor__persona__apellido1','distributivo__profesor__persona__apellido2','distributivo__profesor__persona__nombres','distributivo__profesor__coordinacion__alias','distributivo__profesor__categoria__nombre').filter(distributivo__periodo=proceso.periodo, criteriogestionperiodo_id__isnull=False, evaluapar=True, distributivo__profesor__coordinacion=coordinacion).distinct().order_by('distributivo__profesor__persona__apellido1')
                data['profe'] = listaprodoc | listaproinv | listaproges
                data['carreras'] = carreras = coordinacion.carrera.all()
                data['facultad'] = Coordinacion.objects.all()
                data['codifacu'] = coordinacion
                data['listahoras'] = data['profe']
                data['finalizo'] = proceso.finalizo()
                return render(request, "adm_evaluaciondocentesacreditacioncoordvice/view.html", data)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addfechas':
            try:
                # listaaplicar 1 par, 2 directivo, 3 todos
                listaaplicar = []
                listaaplicar.append(3 if request.POST['apdirec']=='true' else 1)
                distributivo = ProfesorDistributivoHoras.objects.get(profesor_id=request.POST['idprofesor'], periodo_id=request.POST['idperiodo'], coordinacion_id=request.POST['idfacu'], status=True)
                fechasparevaluacion = distributivo.asignar_fecha_par_y_directivo_evaluacion(request, request.POST['lugar'], request.POST['fecha'], request.POST['horaini'], request.POST['horafin'], True, listaaplicar)
                # fecha = request.POST['fecha']
                # cadena = fecha.split('-')
                # fecha = cadena[2] + '-' + cadena[1] + '-' + cadena[0]
                # if DocenteFechaPares.objects.filter(profesor_id=request.POST['idprofesor'],periodo_id=request.POST['idperiodo'],coordinacion_id=request.POST['idfacu'], status=True).exists():
                #     return JsonResponse({"result": "bad", "mensaje": u"Ya existe fecha a ingresar."})
                # else:
                #     fechasdocentes = DocenteFechaPares(profesor_id=request.POST['idprofesor'],
                #                                        periodo_id=request.POST['idperiodo'],
                #                                        coordinacion_id=request.POST['idfacu'],
                #                                        fecha=fecha,
                #                                        horainicio=request.POST['horaini'],
                #                                        lugar=request.POST['lugar'],
                #                                        horafin=request.POST['horafin'])
                #     fechasdocentes.save(request)
                return JsonResponse({"result": "ok", "creacion":fechasparevaluacion.usuario_creacion.__str__(),"lugar":fechasparevaluacion.lugar, "idfechasdocentes": fechasparevaluacion.id, "profesor": fechasparevaluacion.profesor.id, "periodo": fechasparevaluacion.periodo.id,"idfecha": fechasparevaluacion.id, "fecha": fechasparevaluacion.fecha, "hinicio": fechasparevaluacion.horainicio, "hfin": fechasparevaluacion.horafin})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'delfechadocente':
            try:
                fechadocentes = DocenteFechaPares.objects.get(pk=request.POST['id'])
                return JsonResponse({"result": "ok", 'codigofecha':fechadocentes.id , 'apellido1': fechadocentes.profesor.persona.apellido1, 'apellido2': fechadocentes.profesor.persona.apellido2, 'nombres': fechadocentes.profesor.persona.nombres})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'eliminarfechadocente':
            try:
                # listaaplicar 1 par, 2 directivo, 3 todos
                listaaplicar = []
                listaaplicar.append(3 if request.POST['deldirectivo']=='true' else 1)
                fechadocentes = DocenteFechaPares.objects.get(pk=request.POST['codigofecha'])
                distributivo = ProfesorDistributivoHoras.objects.get(profesor=fechadocentes.profesor,  periodo=fechadocentes.periodo, coordinacion=fechadocentes.coordinacion, status=True)
                distributivo.eliminar_fecha_par_y_directivo_evaluacion(request, listaaplicar)
                # fechadocentes.status = False
                # fechadocentes.save(request)
                # log(u'Elimino fecha de par evaluacion en evaluacion de docentes: id[%s] profesor[%s] - periodo[%s] - [%s - %s - %s - %s]' % ( fechadocentes.id, fechadocentes.profesor, fechadocentes.periodo, fechadocentes.fecha, fechadocentes.horainicio, fechadocentes.horafin,fechadocentes.lugar), request, "del")
                return JsonResponse({"result": "ok", 'idperiodo':fechadocentes.periodo.id, 'idprofesor':fechadocentes.profesor.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'deletepar':
            try:
                detalles = DetalleInstrumentoEvaluacionParAcreditacion.objects.get(pk=request.POST['id'])
                detalles.delete()
                log(u"Eliminó asignación de Pares: Profesor: %s; Evaluador: %s; Coordinacion: %s" % (detalles.evaluado, detalles.evaluador, detalles.coordinacion), request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        if action == 'addpar':
            try:

                lista = request.POST['listaprofe']
                if lista:
                    individuales = lista.split(',')
                    detindividuales = individuales[3]
                    # DetalleInstrumentoEvaluacionParAcreditacion.objects.filter(proceso=proceso, evaluado_id=int(individuales[0]), coordinacion_id=int(individuales[2]), evaluador_id=int(individuales[1])).delete()
                    DetalleInstrumentoEvaluacionParAcreditacion.objects.filter(proceso=proceso, evaluado_id=int(individuales[0]), evaluador_id=int(individuales[1])).delete()
                    coordinaciondistributivo = ProfesorDistributivoHoras.objects.get(periodo=proceso.periodo, profesor_id=individuales[0], status=True)
                    detalle = DetalleInstrumentoEvaluacionParAcreditacion(proceso=proceso,
                                                                          evaluado_id=int(individuales[0]),
                                                                          coordinacion=coordinaciondistributivo.coordinacion,
                                                                          evaluador_id=int(individuales[1]))
                    detalle.save(request)
                    for actividad in individuales[3].split(':'):
                        actividadperiodo = DetalleDistributivo.objects.get(pk=int(actividad))
                        actividaddetalle = ActividadDetalleInstrumentoPar(detallepar=detalle,
                                                                          detalledistributivo=actividadperiodo)
                        actividaddetalle.save(request)
                    actplanificadas = proceso.periodo.actividadesactivas(int(individuales[0]))
                    return JsonResponse({"result": "ok","mensajeactividades": actplanificadas})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        if action == 'listaactividades':
            try:
                data = {}
                lista = request.POST['idact']
                idact = lista.split('_')
                profesor = Profesor.objects.get(pk=int(request.POST['id']))
                actividades = profesor.detalle_distributivo(periodo).exclude(evaluapar=False)
                actividadesselec = ActividadDetalleInstrumentoPar.objects.values_list('detalledistributivo_id','detallepar__evaluador_id').filter(detallepar__proceso=proceso, detallepar__evaluado_id=int(idact[1]))
                actividadessele = actividadesselec.values_list('detalledistributivo_id', flat=True).filter(detallepar__evaluador_id=int(idact[3]))
                actividadesseleccionadas = actividadesselec.values_list('detalledistributivo_id', flat=True)
                data['actividades'] = actividades
                data['actividadesselec'] = actividadessele
                data['actividadesseleccionadas'] = actividadesseleccionadas
                template = get_template("adm_evaluaciondocentesacreditacioncoordvice/listaactividades.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'eliminarasigpares':
            try:

                if DetalleInstrumentoEvaluacionParAcreditacion.objects.filter(proceso=proceso,evaluado_id=int(request.POST['evaluado']),coordinacion_id=int(request.POST['idfacu']),evaluador_id=int(request.POST['evaluador'])).exists():
                    detalles = DetalleInstrumentoEvaluacionParAcreditacion.objects.get(proceso=proceso, evaluado_id=int(request.POST['evaluado']), coordinacion_id=int(request.POST['idfacu']), evaluador_id=int(request.POST['evaluador']))
                    detalles.delete()
                    log(u"Eliminó asignación de Pares: Profesor: %s; Evaluador: %s; Coordinacion: %s" % (detalles.evaluado, detalles.evaluador, detalles.coordinacion), request, "del")
                actplanificadas = proceso.periodo.actividadesactivas(int(request.POST['evaluado']))
                return JsonResponse({"result": "ok","mensajeactividad":actplanificadas})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'listadelpar':
            try:
                valor = request.POST['id']
                lista = valor.split('_')
                persona= Persona.objects.get(pk=lista[3])
                nombres = persona.nombre_completo()
                idevaluado = lista[1]
                idcoordinacion = lista[2]
                idevaluador = lista[3]
                return JsonResponse({"result": "ok", 'evaluador': nombres, 'idevaluado': idevaluado, 'idcoordinacion': idcoordinacion, 'idevaluador': idevaluador})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'reporteparevaluacion':
            mensaje = "Problemas al generar el informe de actividades."
            try:
                __author__ = 'Unemi'
                title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False
                wb = Workbook(encoding='utf-8')
                ws = wb.add_sheet('exp_xls_post_part')
                ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                response = HttpResponse(content_type="application/ms-excel")
                texto = coordinacion.nombre
                texto_sin_coma = texto.replace(",", "")
                response['Content-Disposition'] = 'attachment; filename=EVALUACION_PROFESORES_'+texto_sin_coma.__str__()+'.xls'

                columns = [
                    (u"PROFESOR", 10000),
                    (u"CORREO PERSONAL", 6000),
                    (u"CORREO INSTITUCIONAL", 6000),
                    (u"COORDINACIÓN", 3000),
                    (u"CATEGORIZACIÓN", 6000),
                    (u"FECHA", 3000),
                    (u"HORA INICIO", 3000),
                    (u"HORA FIN", 3000),
                    (u"LUGAR", 6000),
                    (u"EVALUADOR", 10000),
                    (u"CORREO PERSONAL", 6000),
                    (u"CORREO INSTITUCIONAL", 6000),
                    (u"ACTIVIDAD", 6000),
                ]
                row_num=3

                for col_num in range(len(columns)):
                    ws.write(row_num, col_num, columns[col_num][0], font_style)
                    ws.col(col_num).width = columns[col_num][1]

                if puede_realizar_accion_afirmativo(request, 'sga.puede_ver_pares_generales'):
                    listaprodoc = DetalleDistributivo.objects.values('distributivo__profesor__id',
                                                                     'distributivo__profesor',
                                                                     'distributivo__profesor__persona__apellido1',
                                                                     'distributivo__profesor__persona__apellido2',
                                                                     'distributivo__profesor__persona__nombres',
                                                                     'distributivo__coordinacion__alias',
                                                                     'distributivo__profesor__categoria__nombre',
                                                                     'distributivo__coordinacion_id').filter(distributivo__periodo=proceso.periodo, criteriodocenciaperiodo__isnull=False,distributivo__coordinacion=coordinacion).distinct().order_by('distributivo__profesor__persona__apellido1')
                    listaproinv = DetalleDistributivo.objects.values('distributivo__profesor__id',
                                                                     'distributivo__profesor',
                                                                     'distributivo__profesor__persona__apellido1',
                                                                     'distributivo__profesor__persona__apellido2',
                                                                     'distributivo__profesor__persona__nombres',
                                                                     'distributivo__coordinacion__alias',
                                                                     'distributivo__profesor__categoria__nombre',
                                                                     'distributivo__coordinacion_id').filter(distributivo__periodo=proceso.periodo, criterioinvestigacionperiodo_id__isnull=False,distributivo__coordinacion=coordinacion).distinct().order_by('distributivo__profesor__persona__apellido1')
                    listaproges = DetalleDistributivo.objects.values('distributivo__profesor__id',
                                                                     'distributivo__profesor',
                                                                     'distributivo__profesor__persona__apellido1',
                                                                     'distributivo__profesor__persona__apellido2',
                                                                     'distributivo__profesor__persona__nombres',
                                                                     'distributivo__coordinacion__alias',
                                                                     'distributivo__profesor__categoria__nombre',
                                                                     'distributivo__coordinacion_id').filter(distributivo__periodo=proceso.periodo,criteriogestionperiodo_id__isnull=False, distributivo__coordinacion=coordinacion).distinct().order_by('distributivo__profesor__persona__apellido1')
                    detalledistributivo = listaprodoc | listaproinv | listaproges
                else:
                    evaluaciondirectivos = DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.values_list('evaluado_id').filter(proceso=proceso, coordinacion=coordinacion,evaluador=persona).distinct()
                    detalledistributivo = DetalleDistributivo.objects.values('distributivo__profesor__id',
                                                                             'distributivo__profesor',
                                                                             'distributivo__profesor__persona__apellido1',
                                                                             'distributivo__profesor__persona__apellido2',
                                                                             'distributivo__profesor__persona__nombres',
                                                                             'distributivo__coordinacion__alias',
                                                                             'distributivo__profesor__categoria__nombre',
                                                                             'distributivo__coordinacion_id').filter(distributivo__periodo=proceso.periodo, distributivo__profesor__id__in=evaluaciondirectivos).distinct().order_by('distributivo__profesor__persona__apellido1')
                row_num = 4
                for detalle in detalledistributivo:
                    i = 0
                    campo1 = u'%s %s %s'%(detalle['distributivo__profesor__persona__apellido1'], detalle['distributivo__profesor__persona__apellido2'], detalle['distributivo__profesor__persona__nombres'])
                    campo2 = u'%s'%(detalle['distributivo__coordinacion__alias'])
                    campo3 = u'%s'%(detalle['distributivo__profesor__categoria__nombre'])
                    campo4 = ''
                    campo5 = ''
                    campo6 = ''
                    campo7 = ''
                    campo8 = ''
                    campo9 = ''
                    campo10 = ''
                    campo11 = ''
                    campo12 = ''
                    campo13 = ''
                    profesoresfechas = coordinacion.docente_fechaspares(detalle['distributivo__profesor__id'], proceso.periodo.id, detalle['distributivo__coordinacion_id'])
                    if profesoresfechas:
                        for fechaprofe in profesoresfechas:
                            campo4 = u'%s'%(fechaprofe.fecha.strftime('%d-%m-%Y') if fechaprofe.fecha else '')
                            campo5 = u'%s'%(fechaprofe.horainicio.strftime("%H:%M") if fechaprofe.horainicio else '')
                            campo6 = u'%s'%(fechaprofe.horafin.strftime("%H:%M") if fechaprofe.horafin else '')
                            campo7 = u'%s'%(fechaprofe.lugar if fechaprofe.lugar else '')
                            campo10 = u'%s'%(fechaprofe.profesor.persona.email if fechaprofe.profesor.persona.email else '')
                            campo11 = u'%s'%(fechaprofe.profesor.persona.emailinst if fechaprofe.profesor.persona.emailinst else '')
                    if periodo.id<90:
                        evaluadoresseleccionados = proceso.evaluadores_seleccionados_partotal(detalle['distributivo__profesor'])
                    else:
                        evaluadoresseleccionados = proceso.evaluadores_seleccionados_partotal_coordinacion( detalle['distributivo__profesor'], coordinacion)
                    if evaluadoresseleccionados:
                        for detalleselec in evaluadoresseleccionados:
                            campo8 = u'%s'%(detalleselec.evaluador if detalleselec.evaluador else '')
                            campo12 = u'%s' % (detalleselec.evaluador.email if detalleselec.evaluador.email else '')
                            campo13 = u'%s' % (detalleselec.evaluador.emailinst if detalleselec.evaluador.emailinst else '')
                            for actividad in detalleselec.mis_actividades():
                                campo9 = u'%s'%(actividad.detalledistributivo.nombre() if actividad.detalledistributivo.nombre() else '')
                                ws.write(row_num, 0, campo1, font_style2)
                                ws.write(row_num, 1, campo10, font_style2)
                                ws.write(row_num, 2, campo11, font_style2)
                                ws.write(row_num, 3, campo2, font_style2)
                                ws.write(row_num, 4, campo3, font_style2)
                                ws.write(row_num, 5, campo4, font_style2)
                                ws.write(row_num, 6, campo5, font_style2)
                                ws.write(row_num, 7, campo6, font_style2)
                                ws.write(row_num, 8, campo7, font_style2)
                                ws.write(row_num, 9, campo8, font_style2)
                                ws.write(row_num, 10, campo12, font_style2)
                                ws.write(row_num, 11, campo13, font_style2)
                                ws.write(row_num, 12, campo9, font_style2)
                                row_num += 1
                    else:
                        ws.write(row_num, 0, campo1, font_style2)
                        ws.write(row_num, 1, campo10, font_style2)
                        ws.write(row_num, 2, campo11, font_style2)
                        ws.write(row_num, 3, campo2, font_style2)
                        ws.write(row_num, 4, campo3, font_style2)
                        ws.write(row_num, 5, campo4, font_style2)
                        ws.write(row_num, 6, campo5, font_style2)
                        ws.write(row_num, 7, campo6, font_style2)
                        ws.write(row_num, 8, campo7, font_style2)
                        ws.write(row_num, 10, campo12, font_style2)
                        ws.write(row_num, 11, campo13, font_style2)
                        ws.write(row_num, 12, campo9, font_style2)
                        row_num += 1
                wb.save(response)
                return response
            except Exception as ex:
                return HttpResponseRedirect("/adm_evaluaciondocentesacreditacioncoordvice?info=%s" % mensaje)


                #return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'deletepar':
                try:
                    data['title'] = u'Eliminar asinación de Pares'
                    data['evaluadorpar'] = DetalleInstrumentoEvaluacionParAcreditacion.objects.get(proceso=proceso,
                                                                                                   evaluado_id=request.GET['profesor'],
                                                                                                   coordinacion=request.GET['coordinacion'],
                                                                                                   evaluador_id=request.GET['evaluador'])
                    return render(request, 'adm_evaluaciondocentesacreditacioncoordvice/deleteevalpar.html', data)
                except Exception as ex:
                    pass

            if action == 'consultacoordinacion':
                try:
                    if 'idfacu' in request.GET:
                        coordinacionfac = Coordinacion.objects.get(pk=request.GET['idfacu'])
                    else:
                        coordinacionfac = Coordinacion.objects.all()[0]
                    listahoras = []
                    llenardocentes = []
                    data['title'] = u'Seleccion de pares para evaluación de los profesores'
                    data['profesoresevaluadores'] = ProfesorDistributivoHoras.objects.filter(periodo=proceso.periodo).distinct()
                    data['coordinacion'] = coordinacionfac
                    try:
                        puede_realizar_accion(request, 'sga.puede_ver_pares_generales')
                        listaprodoc = DetalleDistributivo.objects.values('distributivo__profesor__id', 'distributivo__profesor','distributivo__profesor__persona__apellido1','distributivo__profesor__persona__apellido2','distributivo__profesor__persona__nombres','distributivo__coordinacion__alias','distributivo__profesor__categoria__nombre','distributivo__coordinacion_id').filter(distributivo__periodo=proceso.periodo,criteriodocenciaperiodo__isnull=False,distributivo__coordinacion=coordinacionfac).distinct().order_by('distributivo__profesor__persona__apellido1')
                        listaproinv = DetalleDistributivo.objects.values('distributivo__profesor__id', 'distributivo__profesor','distributivo__profesor__persona__apellido1','distributivo__profesor__persona__apellido2','distributivo__profesor__persona__nombres','distributivo__coordinacion__alias','distributivo__profesor__categoria__nombre','distributivo__coordinacion_id').filter(distributivo__periodo=proceso.periodo,criterioinvestigacionperiodo_id__isnull=False,distributivo__coordinacion=coordinacionfac).distinct().order_by('distributivo__profesor__persona__apellido1')
                        listaproges = DetalleDistributivo.objects.values('distributivo__profesor__id', 'distributivo__profesor','distributivo__profesor__persona__apellido1','distributivo__profesor__persona__apellido2','distributivo__profesor__persona__nombres','distributivo__coordinacion__alias','distributivo__profesor__categoria__nombre','distributivo__coordinacion_id').filter(distributivo__periodo=proceso.periodo,criteriogestionperiodo_id__isnull=False,distributivo__coordinacion=coordinacionfac).distinct().order_by('distributivo__profesor__persona__apellido1')
                        profe = listaprodoc | listaproinv | listaproges
                    except Exception as ex:
                        evaluaciondirectivos = DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.values_list('evaluado_id').filter(proceso=proceso, coordinacion=coordinacionfac, evaluador=persona)
                        profe = DetalleDistributivo.objects.values('distributivo__profesor__id', 'distributivo__profesor','distributivo__profesor__persona__apellido1','distributivo__profesor__persona__apellido2','distributivo__profesor__persona__nombres','distributivo__coordinacion__alias','distributivo__profesor__categoria__nombre','distributivo__coordinacion_id').filter(distributivo__periodo=proceso.periodo, distributivo__profesor__id__in=evaluaciondirectivos).distinct().order_by('distributivo__profesor__persona__apellido1')
                    data['profe'] = profe
                    data['carreras'] = carreras = coordinacionfac.carrera.all()
                    data['facultad'] = Coordinacion.objects.all()
                    data['codifacu'] = coordinacionfac
                    data['listahoras'] = data['profe']
                    data['finalizo'] = not proceso.finalizopar()
                    # data['finalizo'] = True
                    data['idperiodo'] = proceso.periodo.id
                    form = FechaDocenteParesForm()
                    data['form'] = form
                    data['horactual'] = time.strftime('%H:%M:%S')
                    return render(request, "adm_evaluaciondocentesacreditacioncoordvice/view.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:

            if 'coordinacion' in request.GET:
                coordinacionfac = request.GET['coordinacion']
            else:
                coordinacionfac = Coordinacion.objects.all()[0]

            listahoras = []
            llenardocentes = []
            data['title'] = u'Seleccion de pares para evaluación de los profesores'
            data['profesoresevaluadores'] = ProfesorDistributivoHoras.objects.filter(periodo=proceso.periodo).distinct()
            data['coordinacion'] = coordinacionfac
            try:
                puede_realizar_accion(request, 'sga.puede_ver_pares_generales')
                listaprodoc = DetalleDistributivo.objects.values('distributivo__profesor__id', 'distributivo__profesor','distributivo__profesor__persona__apellido1','distributivo__profesor__persona__apellido2','distributivo__profesor__persona__nombres','distributivo__coordinacion__alias','distributivo__profesor__categoria__nombre','distributivo__coordinacion_id').filter(distributivo__periodo=proceso.periodo,criteriodocenciaperiodo__isnull=False,distributivo__coordinacion=coordinacionfac).distinct().order_by('distributivo__profesor__persona__apellido1')
                listaproinv = DetalleDistributivo.objects.values('distributivo__profesor__id', 'distributivo__profesor','distributivo__profesor__persona__apellido1','distributivo__profesor__persona__apellido2','distributivo__profesor__persona__nombres','distributivo__coordinacion__alias','distributivo__profesor__categoria__nombre','distributivo__coordinacion_id').filter(distributivo__periodo=proceso.periodo,criterioinvestigacionperiodo_id__isnull=False,distributivo__coordinacion=coordinacionfac).distinct().order_by('distributivo__profesor__persona__apellido1')
                listaproges = DetalleDistributivo.objects.values('distributivo__profesor__id', 'distributivo__profesor','distributivo__profesor__persona__apellido1','distributivo__profesor__persona__apellido2','distributivo__profesor__persona__nombres','distributivo__coordinacion__alias','distributivo__profesor__categoria__nombre','distributivo__coordinacion_id').filter(distributivo__periodo=proceso.periodo,criteriogestionperiodo_id__isnull=False,distributivo__coordinacion=coordinacionfac).distinct().order_by('distributivo__profesor__persona__apellido1')
                profe = listaprodoc | listaproinv | listaproges
            except Exception as ex:
                evaluaciondirectivos = DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.values_list('evaluado_id').filter(proceso=proceso, coordinacion=coordinacionfac, evaluador=persona).distinct()
                profe = DetalleDistributivo.objects.values('distributivo__profesor__id', 'distributivo__profesor','distributivo__profesor__persona__apellido1', 'distributivo__profesor__persona__apellido2','distributivo__profesor__persona__nombres','distributivo__coordinacion__alias','distributivo__profesor__categoria__nombre','distributivo__coordinacion_id').filter(distributivo__periodo=proceso.periodo, distributivo__profesor__id__in=evaluaciondirectivos).distinct().order_by('distributivo__profesor__persona__apellido1')
            data['profe'] = profe
            data['carreras'] = carreras = coordinacionfac.carrera.all()
            data['facultad'] = Coordinacion.objects.all()
            data['codifacu'] = coordinacionfac
            data['listahoras'] = data['profe']
            data['form'] =  FechaDocenteParesForm()
            data['horactual'] = time.strftime('%H:%M:%S')
            data['idperiodo'] = proceso.periodo.id
            # data['finalizo'] = proceso.finalizopar()
            data['finalizo'] = not proceso.finalizopar()
            return render(request, "adm_evaluaciondocentesacreditacioncoordvice/view.html", data)