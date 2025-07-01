# -*- coding: UTF-8 -*-
import sys

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
import time
from django.db.models import Q

from django.template.loader import get_template

from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import FechaDocenteParesForm
from sga.funciones import log, MiPaginador
from sga.models import Profesor, Persona, \
    DetalleInstrumentoEvaluacionParAcreditacion, ActividadDetalleInstrumentoPar, DetalleDistributivo, \
    DocenteFechaPares, ProfesorDistributivoHoras, ResponsableCoordinacion, Coordinacion, \
    DetalleInstrumentoEvaluacionDirectivoAcreditacion, TIPO_DIR_EVALUA


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    data['proceso'] = proceso = data['periodo'].proceso_evaluativoacreditacion()
    data['periodo'] = periodo = request.session['periodo']
    data['persona'] = persona = request.session['persona']
    es_evaluador = False
    es_investigador = False
    es_vinculacion = False
    if persona.es_responsablecoordinacion(periodo):
        responsablecoordinacion = persona.responsablecoordinacion(periodo)
        coordinacion = responsablecoordinacion.coordinacion
    elif persona.es_coordinadorcarrera(periodo):
        responsablecarrera = persona.coordinadorcarreras(periodo)
        coordinacion = responsablecarrera[0].coordinacion()
    elif persona.es_evaluador_investigacion():
        es_evaluador = True
        data['es_evaluador'] = es_evaluador
        if persona.es_tipo_evaluador_investigacion():
            es_investigador = True
            data['es_investigador'] = es_investigador
        if persona.es_tipo_evaluador_vinculacion():
            es_vinculacion = True
            data['es_vinculacion'] = es_vinculacion
    else:
        return HttpResponseRedirect(
            "/?info=Este modulo solo es para uso de los responsables de carreras o de la coordinacion.")
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'asignarevaluacionpar':
            try:
                # detalles = proceso.detalleinstrumentoevaluacionparacreditacion_set.filter(coordinacion=coordinacion)
                # detalles.delete()
                lista = request.POST['listaprofesores']
                if lista:
                    elementos = lista.split('#')
                    for elemento in elementos:
                        individuales = elemento.split(',')
                        profesor = Profesor.objects.get(pk=int(individuales[0]))
                        for elementoevaluador in individuales[2].split(':'):
                            elementoactividades = elementoevaluador.split('=')
                            evaluador = Persona.objects.get(pk=int(elementoactividades[0]))
                            if not DetalleInstrumentoEvaluacionParAcreditacion.objects.filter(proceso=proceso,
                                                                                              evaluado=profesor,
                                                                                              coordinacion=coordinacion,
                                                                                              evaluador=evaluador).exists():
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
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deletepar':
            try:
                detalles = DetalleInstrumentoEvaluacionParAcreditacion.objects.get(pk=request.POST['id'])
                detalles.delete()
                log(u"Eliminó asignación de Pares: Profesor: %s; Evaluador: %s; Coordinacion: %s" % (
                    detalles.evaluado, detalles.evaluador, detalles.coordinacion), request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        if action == 'addpar':
            try:
                lista = request.POST['listaprofe']
                tipodir = request.POST['tipodir']
                if lista:
                    individuales = lista.split(',')
                    detindividuales = individuales[3]
                    # if DetalleInstrumentoEvaluacionParAcreditacion.objects.filter(proceso=proceso,evaluado_id=int(individuales[0]),coordinacion_id=2,evaluador_id=int(individuales[1])).exists():
                    # DetalleInstrumentoEvaluacionParAcreditacion.objects.filter(proceso=proceso, evaluado_id=int(individuales[0]), coordinacion_id=int(individuales[2]), evaluador_id=int(individuales[1])).delete()
                    DetalleInstrumentoEvaluacionParAcreditacion.objects.filter(proceso=proceso,
                                                                               evaluado_id=int(individuales[0]),
                                                                               evaluador_id=int(individuales[1])).delete()
                    coordinaciondistributivo = ProfesorDistributivoHoras.objects.get(periodo=proceso.periodo,
                                                                                     profesor_id=individuales[0],
                                                                                     status=True)
                    detalle = DetalleInstrumentoEvaluacionParAcreditacion(proceso=proceso,
                                                                          tipodirector=tipodir,
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
                    return JsonResponse({"result": "ok", "mensajeactividades": actplanificadas})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        if action == 'addfechas':
            try:
                if DocenteFechaPares.objects.filter(profesor_id=request.POST['idprofesor'],
                                                    periodo_id=request.POST['idperiodo'],
                                                    tipodirector=request.POST['tipodir'],
                                                    coordinacion_id=request.POST['idfacu'], status=True).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"Ya existe fecha a ingresar."})
                else:
                    fecha = request.POST['fecha']
                    coordinaciondistributivo = ProfesorDistributivoHoras.objects.filter(profesor_id=request.POST['idprofesor'],
                                                                                        periodo_id=request.POST['idperiodo'], status=True)[0]
                    fechasdocentes = DocenteFechaPares(profesor_id=request.POST['idprofesor'],
                                                       periodo_id=request.POST['idperiodo'],
                                                       coordinacion=coordinaciondistributivo.coordinacion,
                                                       fecha=fecha,
                                                       tipodirector=request.POST['tipodir'],
                                                       horainicio=request.POST['horaini'],
                                                       lugar=request.POST['lugar'],
                                                       horafin=request.POST['horafin'])
                    fechasdocentes.save(request)
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'delfechadocente':
            try:
                fechadocentes = DocenteFechaPares.objects.get(pk=request.POST['id'])
                return JsonResponse({"result": "ok", 'codigofecha': fechadocentes.id,
                                     'apellido1': fechadocentes.profesor.persona.apellido1,
                                     'apellido2': fechadocentes.profesor.persona.apellido2,
                                     'nombres': fechadocentes.profesor.persona.nombres})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'eliminarfechadocente':
            try:
                fechadocentes = DocenteFechaPares.objects.get(pk=request.POST['codigofecha'])
                idprofesor = fechadocentes.profesor.id
                idperiodo = fechadocentes.periodo.id
                fechadocentes.status = False
                fechadocentes.save(request)
                return JsonResponse({"result": "ok", 'idperiodo': idperiodo, 'idprofesor': idprofesor})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'listaactividades':
            try:
                lista = request.POST['idact']
                idact = lista.split('_')
                data['detallepardir'] = detallepardir = DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.filter(proceso=proceso, evaluador_id=persona.id, evaluado_id=int(request.POST['id']))[0]
                tipodir = detallepardir.tipodirector
                itemdesabilita = ''
                if tipodir == 1:
                    itemdesabilita = ['INVESTIGACION', 'VINCULACIÓN']
                if tipodir == 2:
                    itemdesabilita = ['VINCULACIÓN', 'DOCENCIA', 'GESTION']
                if tipodir == 3:
                    itemdesabilita = ['INVESTIGACION', 'DOCENCIA', 'GESTION']
                data['itemdesabilita'] = itemdesabilita
                profesor = Profesor.objects.get(pk=int(request.POST['id']))
                # if not persona.es_evaluador_investigacion():
                actividades = profesor.detalle_distributivo(periodo).exclude(evaluapar=False)
                # else:
                #     if persona.es_tipo_evaluador_investigacion():
                #         actividades = profesor.detalle_distributivo_investigacion(periodo).exclude(evaluapar=False)
                #     if persona.es_tipo_evaluador_investigacion():
                #         actividades = profesor.detalle_distributivo_vinculacion(periodo).exclude(evaluapar=False)

                # actividadesselec = ActividadDetalleInstrumentoPar.objects.values_list('detalledistributivo_id', 'detallepar__evaluador_id').filter(detallepar__proceso=proceso, detallepar__evaluado_id=int(idact[1]), detallepar__coordinacion_id=int(idact[2]))
                actividadesselec = ActividadDetalleInstrumentoPar.objects.values_list('detalledistributivo_id',
                                                                                      'detallepar__evaluador_id').filter(
                    detallepar__proceso=proceso, detallepar__evaluado_id=int(idact[1]))
                actividadessele = actividadesselec.values_list('detalledistributivo_id', flat=True).filter(
                    detallepar__evaluador_id=int(idact[3]))
                actividadesseleccionadas = actividadesselec.values_list('detalledistributivo_id', flat=True)
                data['actividades'] = actividades
                data['actividadesselec'] = actividadessele
                data['actividadesseleccionadas'] = actividadesseleccionadas
                template = get_template("adm_evaluaciondocentesacreditacioncoord/listaactividades.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'eliminarasigpares':
            try:
                if DetalleInstrumentoEvaluacionParAcreditacion.objects.filter(proceso=proceso,
                                                                              evaluado_id=int(request.POST['evaluado']),
                                                                              coordinacion_id=int(
                                                                                  request.POST['coordinacion']),
                                                                              evaluador_id=int(request.POST[
                                                                                                   'evaluador'])).exists():
                    detalles = DetalleInstrumentoEvaluacionParAcreditacion.objects.get(proceso=proceso, evaluado_id=int(
                        request.POST['evaluado']), coordinacion_id=int(request.POST['coordinacion']), evaluador_id=int(
                        request.POST['evaluador']))
                    detalles.delete()
                    log(u"Eliminó asignación de Pares: Profesor: %s; Evaluador: %s; Coordinacion: %s" % (
                        detalles.evaluado, detalles.evaluador, detalles.coordinacion), request, "del")
                actplanificadas = proceso.periodo.actividadesactivas(int(request.POST['evaluado']))
                return JsonResponse({"result": "ok", "mensajeactividad": actplanificadas})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'listadelpar':
            try:
                valor = request.POST['id']
                lista = valor.split('_')
                persona = Persona.objects.get(pk=lista[3])
                nombres = persona.nombre_completo()
                idevaluado = lista[1]
                idcoordinacion = lista[2]
                idevaluador = lista[3]
                return JsonResponse(
                    {"result": "ok", 'evaluador': nombres, 'idevaluado': idevaluado, 'idcoordinacion': idcoordinacion,
                     'idevaluador': idevaluador})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'verdocentespares':
            try:
                data['profesoresevaluadores'] = ProfesorDistributivoHoras.objects.filter(periodo=proceso.periodo,
                                                                                         profesor__persona__real=True,
                                                                                         activo=True).exclude(coordinacion_id__in=[9]).order_by('profesor__persona__apellido1', 'profesor__persona__apellido2')
                template = get_template("adm_evaluaciondocentesacreditacioncoord/verdocentespares.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'deletepar':
                try:
                    data['title'] = u'Eliminar asinación de Pares'
                    data['evaluadorpar'] = DetalleInstrumentoEvaluacionParAcreditacion.objects.get(proceso=proceso,
                                                                                                   evaluado_id=
                                                                                                   request.GET[
                                                                                                       'profesor'],
                                                                                                   coordinacion=
                                                                                                   request.GET[
                                                                                                       'coordinacion'],
                                                                                                   evaluador_id=
                                                                                                   request.GET[
                                                                                                       'evaluador'])
                    return render(request, 'adm_evaluaciondocentesacreditacioncoord/deleteevalpar.html', data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                listahoras = []
                llenardocentes = []
                search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''
                if not request.session['periodo'].visible:
                    return HttpResponseRedirect("/?info=Periodo Inactivo.")
                data['title'] = u'Seleccionar pares evaluadores'
                # data['profesoresevaluadores'] = ProfesorDistributivoHoras.objects.filter(periodo=proceso.periodo, activo=True).distinct()
                # data['coordinaciones'] = coordinaciones = persona.mis_coordinaciones()
                carreras = None
                listaprofesores = None
                if not es_evaluador:
                    carreras = coordinacion.carreras()

                responsablecarrera = ResponsableCoordinacion.objects.values_list('coordinacion_id', flat=True).filter(
                    persona=persona, periodo=periodo)
                # coordinaciones = Coordinacion.objects.filter(pk__in=responsablecarrera).order_by('id')
                coordinaciones = Coordinacion.objects.filter(
                    pk__in=ProfesorDistributivoHoras.objects.values_list('coordinacion_id').filter(periodo=proceso.periodo,
                                                                                                   activo=True)).order_by(
                    'id')
                data['coordinaciones'] = coordinaciones

                # data['coordinaciones'] = coordinaciones = persona.mis_coordinaciones()

                if 'idcoor' in request.GET:
                    data['coordinacion'] = idcoordinacion = coordinaciones.get(pk=request.GET['idcoor'])
                else:
                    if coordinaciones:
                        data['coordinacion'] = idcoordinacion = coordinaciones[0]
                # if persona.es_responsablecoordinacion(periodo):

                data['es_evaluador'] = es_evaluador

                # if not es_evaluador:
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    url_vars += f'&s={search}'
                    ss = search.split(' ')
                    if len(ss) == 1:
                        listaprofesores = DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.filter(
                            Q(evaluado__persona__nombres__icontains=search) |
                            Q(evaluado__persona__apellido1__icontains=search) |
                            Q(evaluado__persona__apellido2__icontains=search) |
                            Q(evaluado__persona__cedula__icontains=search) |
                            Q(evaluado__persona__pasaporte__icontains=search),
                            proceso_id=proceso.id, evaluado__persona__real=True, evaluador_id=persona.id,
                            status=True).order_by('evaluado__persona__apellido1', 'evaluado__persona__apellido2')
                    else:
                        listaprofesores = DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.filter(
                            Q(evaluado__persona__apellido1__icontains=ss[0]) &
                            Q(evaluado__persona__apellido2__icontains=ss[1]),
                            proceso_id=proceso.id, evaluado__persona__real=True, evaluador_id=persona.id,
                            status=True).order_by('evaluado__persona__apellido1', 'evaluado__persona__apellido2')
                else:
                    listaprofesores = DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.filter(
                        proceso_id=proceso.id, evaluado__persona__real=True, evaluador_id=persona.id,
                        status=True).order_by('evaluado__persona__apellido1', 'evaluado__persona__apellido2')
                    # listaprofesores = DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.values_list('evaluado_id').filter(proceso_id=proceso.id, evaluador_id=persona.id, status=True)
                    # listaprofesores = ProfesorDistributivoHoras.objects.values_list('profesor','profesor__persona__apellido1', 'profesor__persona__apellido2', 'profesor__persona__nombres', 'carrera__nombre', 'carrera__id', 'coordinacion__alias', 'profesor__categoria__nombre','coordinacion').filter(profesor__id__in=listaprofesores, periodo_id=proceso.periodo.id, activo=True, status=True).exclude(profesor__persona=persona).distinct().order_by('profesor__persona__apellido1','profesor__persona__apellido2')
                    # elif persona.es_coordinadorcarrera(periodo):
                    #     listaprofesores = DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.values_list('evaluado_id').filter(proceso=proceso, evaluador=persona, status=True)
                    #     data['coordinacion'] = coordinacion
                    #     responsablecarrera = persona.coordinadorcarreras(periodo)
                    #     carreras = responsablecarrera.values_list('carrera__id')
                    #     listaprofesores = ProfesorDistributivoHoras.objects.values_list('profesor', 'profesor__persona__apellido1', 'profesor__persona__apellido2','profesor__persona__nombres', 'carrera__nombre', 'carrera__id', 'coordinacion__alias','profesor__categoria__nombre','coordinacion').filter(profesor__id__in=listaprofesores, activo=True, periodo=proceso.periodo).exclude(profesor__persona=persona).distinct().order_by('profesor__persona__apellido1','profesor__persona__apellido2')
                # else:
                #     if persona.es_tipo_evaluador_investigacion():
                #         if 's' in request.GET:
                #             search = request.GET['s'].strip()
                #             url_vars += f'&s={search}'
                #             ss = search.split(' ')
                #             if len(ss) == 1:
                #                 listaprofesores = DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.filter(
                #                     Q(evaluado__persona__nombres__icontains=search) |
                #                     Q(evaluado__persona__apellido1__icontains=search) |
                #                     Q(evaluado__persona__apellido2__icontains=search) |
                #                     Q(evaluado__persona__cedula__icontains=search) |
                #                     Q(evaluado__persona__pasaporte__icontains=search),
                #                     proceso_id=proceso.id, evaluado__persona__real=True, status=True).order_by(
                #                     'evaluado__persona__apellido1', 'evaluado__persona__apellido2')
                #             else:
                #                 listaprofesores = DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.filter(
                #                     Q(evaluado__persona__apellido1__icontains=ss[0]) &
                #                     Q(evaluado__persona__apellido2__icontains=ss[1]),
                #                     proceso_id=proceso.id, evaluado__persona__real=True,
                #                     status=True).order_by('evaluado__persona__apellido1', 'evaluado__persona__apellido2')
                #
                #                 Q(evaluado__persona__apellido2__icontains=ss[1]),
                #         else:
                #             profesores_investigacion = ProfesorDistributivoHoras.objects.values_list('profesor_id',
                #                                                                                      flat=True).filter(
                #                 periodo=periodo, status=True, horasinvestigacion__gt=0)
                #             listaprofesores = DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.filter(
                #                 proceso_id=proceso.id, evaluado__persona__real=True,
                #                 evaluado_id__in=profesores_investigacion,
                #                 status=True).order_by('evaluado__persona__apellido1', 'evaluado__persona__apellido2')
                #     if persona.es_tipo_evaluador_vinculacion():
                #         if 's' in request.GET:
                #             search = request.GET['s'].strip()
                #             url_vars += f'&s={search}'
                #             ss = search.split(' ')
                #             if len(ss) == 1:
                #                 listaprofesores = DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.filter(
                #                     Q(evaluado__persona__nombres__icontains=search) |
                #                     Q(evaluado__persona__apellido1__icontains=search) |
                #                     Q(evaluado__persona__apellido2__icontains=search) |
                #                     Q(evaluado__persona__cedula__icontains=search) |
                #                     Q(evaluado__persona__pasaporte__icontains=search),
                #                     proceso_id=proceso.id, evaluado__persona__real=True, status=True).order_by(
                #                     'evaluado__persona__apellido1', 'evaluado__persona__apellido2')
                #             else:
                #                 listaprofesores = DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.filter(
                #                     Q(evaluado__persona__apellido1__icontains=ss[0]) &
                #                     Q(evaluado__persona__apellido2__icontains=ss[1]),
                #                     proceso_id=proceso.id, evaluado__persona__real=True,
                #                     status=True).order_by('evaluado__persona__apellido1', 'evaluado__persona__apellido2')
                #
                #                 Q(evaluado__persona__apellido2__icontains=ss[1]),
                #         else:
                #             profesores_investigacion = ProfesorDistributivoHoras.objects.values_list('profesor_id',
                #                                                                                      flat=True).filter(
                #                 periodo=periodo, status=True, horasvinculacion__gt=0)
                #             listaprofesores = DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.filter(
                #                 proceso_id=proceso.id, evaluado__persona__real=True,
                #                 evaluado_id__in=profesores_investigacion,
                #                 status=True).order_by('evaluado__persona__apellido1', 'evaluado__persona__apellido2')

                numerofilas = 25
                paging = MiPaginador(listaprofesores, numerofilas)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session:
                        paginasesion = int(request.session['paginador'])
                    if 'page' in request.GET:
                        p = int(request.GET['page'])
                        if p == 1:
                            numerofilasguiente = numerofilas
                        else:
                            numerofilasguiente = numerofilas * (p - 1)
                    else:
                        p = paginasesion
                        if p == 1:
                            numerofilasguiente = numerofilas
                        else:
                            numerofilasguiente = numerofilas * (p - 1)
                    try:
                        page = paging.page(p)
                    except:
                        p = 1
                    page = paging.page(p)
                except:
                    page = paging.page(p)
                request.session['paginador'] = p
                data['paging'] = paging
                data['numerofilasguiente'] = numerofilasguiente
                data['numeropagina'] = p
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['search'] = search if search else ""
                data["url_vars"] = url_vars
                data['listahoras'] = page.object_list

                data['carreras'] = carreras
                # data['profe'] = listaprofesores
                form = FechaDocenteParesForm()
                data['form'] = form
                data['horactual'] = time.strftime('%H:%M:%S')
                data['idperiodo'] = proceso.periodo.id
                data['listatipoevalua'] = TIPO_DIR_EVALUA
                # data['listahoras'] = listaprofesores
                data['finalizo'] = proceso.finalizoplanificaconpares()
                return render(request, "adm_evaluaciondocentesacreditacioncoord/view.html", data)
            except Exception as ex:
                transaction.set_rollback(True)
                eline = 'Error on line {} {}'.format(sys.exc_info()[-1].tb_lineno, ex.__str__())
                return JsonResponse({"result": "bad", "mensaje": u"Error: %s" % eline})

