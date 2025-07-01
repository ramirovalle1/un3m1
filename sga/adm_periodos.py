# -*- coding: latin-1 -*-
from datetime import datetime, timedelta
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from django.template.loader import get_template
from inno.forms import DetalleEvaluacionComponentePeriodoForm
from sga.forms import PeriodoForm, CronogramaMatriculacionForm, CronogramaMatriculacionFormModulo, \
    CronogramaMatriculacionFormPre, PeriodoGrupoSocioEconomicoForm, TopeAlumnosPrimeroForm, \
    PeriodoVariablesGrupoSocioEconomicoForm, LineamientoRecursoPeriodoForm, UnidadesPeriodoForm
from sga.funciones import MiPaginador, log, null_to_numeric, puede_realizar_accion, puede_realizar_accion_afirmativo
from inno.models import DetalleEvaluacionComponentePeriodo
from sga.models import Periodo, PeriodoMatriculacion, Coordinacion, CoordinadorCarrera, \
    PeriodoPreMatriculacion, PeriodoPreMatriculacionModulo, PeriodoGrupoSocioEconomico, TopeAlumnosPrimero, \
    LineamientoRecursoPeriodo, UnidadesPeriodo, CalificacionDetalleRubricaTitulacionPosgrado, EvaluacionComponentePeriodo
from socioecon.models import GrupoSocioEconomico
from inno.models import ConfiguracionRecurso

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                periodoactual = request.session['periodo']
                f = PeriodoForm(request.POST)
                if f.is_valid():
                    periodo = Periodo(nombre=f.cleaned_data['nombre'],
                                      inicio=f.cleaned_data['inicio'],
                                      fin=f.cleaned_data['fin'],
                                      activo=True,
                                      tipo=f.cleaned_data['tipo'],
                                      evaluaciondocentemateria=True,
                                      valida_asistencia=f.cleaned_data['valida_asistencia'],
                                      inicio_agregacion=f.cleaned_data['inicio_agregacion'],
                                      limite_agregacion=f.cleaned_data['limite_agregacion'],
                                      limite_retiro=f.cleaned_data['limite_retiro'],
                                      porcentaje_gratuidad=f.cleaned_data['porcentaje_gratuidad'],
                                      visiblehorario=f.cleaned_data['visiblehorario'],
                                      valor_maximo=f.cleaned_data['valor_maximo'],
                                      anio=f.cleaned_data['anio'],
                                      clasificacion=f.cleaned_data['clasificacion'],
                                      cohorte=f.cleaned_data['cohorte'],
                                      usa_moodle=True,
                                      aplicasilabodigital=True)
                    periodo.save(request)
                    if int(f.cleaned_data['clasificacion']) == 2 and f.cleaned_data['tipo'].id == 3:
                        periodo.categoria=4
                        periodo.urlmoodle='https://aulaposgrado.unemi.edu.ec'
                        periodo.keymoodle='65293afed416ee1dc5dd1b137c35f03d'
                        periodo.rolprofesortutor=9
                        periodo.rolprofesor=9
                        periodo.rolestudiante=10
                        periodo.save(request)
                    periodo.get_periodoacademia()
                    for coordinacion in Coordinacion.objects.all():
                        for carrera in coordinacion.carrera.all():
                            if not carrera.coordinadorcarrera_set.values('id').filter(periodo=periodo, sede=coordinacion.sede).exists():
                                if carrera.coordinadorcarrera_set.values('id').filter(sede=coordinacion.sede, periodo=periodoactual).exists():
                                    coordinadoranterior = carrera.coordinadorcarrera_set.filter(sede=coordinacion.sede, periodo=periodoactual)[0].persona
                                    coordinador = CoordinadorCarrera(carrera=carrera,
                                                                     periodo=periodo,
                                                                     sede=coordinacion.sede,
                                                                     persona=coordinadoranterior)
                                    coordinador.save(request)
                    if f.cleaned_data['tipo'].id == 2:
                        id_periodos = ConfiguracionRecurso.objects.values_list('periodo_id',flat=True).filter(status=True).exclude(id=periodo.id).distinct()
                        if id_periodos:
                            if Periodo.objects.filter(status=True, tipo=2,id__in=id_periodos).exists():
                                periodo_origen = Periodo.objects.filter(status=True, tipo=2,id__in=id_periodos).latest('id')
                                for config in ConfiguracionRecurso.objects.filter(status=True, periodo=periodo_origen):
                                    if not ConfiguracionRecurso.objects.filter(status=True, periodo=periodo,
                                                                               tiporecurso=config.tiporecurso,
                                                                               carrera=config.carrera).exists():
                                        formatos = config.formato.all()
                                        formato_destino = config
                                        formato_destino.periodo = periodo
                                        formato_destino.pk = None
                                        formato_destino.save(request)
                                        for format in formatos:
                                            formato_destino.formato.add(format)
                                        # formato_destino.formato = formatos
                                log(u'Importa formatos de recuros del periodo %s: al periodo %s' % (periodo_origen, periodo), request, "edit")
                    log(u'Adicionado periodo: %s' % periodo, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addcronograma':
            try:
                periodo = Periodo.objects.get(pk=request.POST['id'])
                f = CronogramaMatriculacionForm(request.POST)
                if f.is_valid():
                    if PeriodoMatriculacion.objects.values('id').filter(periodo=periodo, nivelmalla=f.cleaned_data['nivelmalla'],
                                                                        carrera=f.cleaned_data['carrera'], modalidad=f.cleaned_data['modalidad']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe un cronograma de matriculacion con estos datos."})
                    periodo = PeriodoMatriculacion(periodo=periodo,
                                                   nivelmalla=f.cleaned_data['nivelmalla'],
                                                   carrera=f.cleaned_data['carrera'],
                                                   modalidad=f.cleaned_data['modalidad'],
                                                   fecha_inicio=f.cleaned_data['inicio'],
                                                   prematricula=f.cleaned_data['prematricula'],
                                                   dias=f.cleaned_data['dias'],
                                                   fecha_fin=f.cleaned_data['fin'])
                    periodo.save(request)
                    log(u'Adicionado periodo de matriculacion: %s' % periodo, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addcronogramapre':
            try:
                periodo = Periodo.objects.get(pk=request.POST['id'])
                f = CronogramaMatriculacionFormPre(request.POST)
                if f.is_valid():
                    if PeriodoPreMatriculacion.objects.values('id').filter(periodo=periodo, nivelmalla=f.cleaned_data['nivelmalla'],
                                                                           carrera=f.cleaned_data['carrera'], modalidad=f.cleaned_data['modalidad']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe un cronograma de prematriculacion con estos datos."})
                    periodo = PeriodoPreMatriculacion(periodo=periodo,
                                                      nivelmalla=f.cleaned_data['nivelmalla'],
                                                      carrera=f.cleaned_data['carrera'],
                                                      modalidad=f.cleaned_data['modalidad'],
                                                      fecha_inicio=f.cleaned_data['inicio'],
                                                      fecha_fin=f.cleaned_data['fin'])
                    periodo.save(request)
                    log(u'Adicionado periodo de prematriculacion: %s' % periodo, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addtopealumnos':
            try:
                periodo = Periodo.objects.get(pk=request.POST['id'])
                f = TopeAlumnosPrimeroForm(request.POST)
                if f.is_valid():
                    if TopeAlumnosPrimero.objects.values('id').filter(periodo=periodo, carrera=f.cleaned_data['carrera']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe una carrera."})
                    topealumnosprimero = TopeAlumnosPrimero(periodo=periodo,
                                                            carrera=f.cleaned_data['carrera'],
                                                            cantidad=f.cleaned_data['cantidad'])
                    topealumnosprimero.save(request)
                    log(u'Adicionado tope carrera: %s' % periodo, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deltopealumnos':
            try:
                topealumnosprimero = TopeAlumnosPrimero.objects.get(pk=request.POST['id'])
                topealumnosprimero.status = False
                topealumnosprimero.save(request)
                log(u"Elimino tope carrera: %s" % topealumnosprimero, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'addlineamiento':
            try:
                periodo = Periodo.objects.get(pk=request.POST['id'])
                f = LineamientoRecursoPeriodoForm(request.POST)
                if f.is_valid():
                    if LineamientoRecursoPeriodo.objects.values('id').filter(periodo=periodo, tipoprofesor=f.cleaned_data['tipoprofesor'], tiporecurso=f.cleaned_data['tiporecurso'], nivelacion=f.cleaned_data['nivelacion']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe un lineamiento."})
                    lineamiento = LineamientoRecursoPeriodo(periodo=periodo,
                                                            tipoprofesor=f.cleaned_data['tipoprofesor'],
                                                            tiporecurso=f.cleaned_data['tiporecurso'],
                                                            cantidad=f.cleaned_data['cantidad'],
                                                            nivelacion=f.cleaned_data['nivelacion'],
                                                            aplicapara=f.cleaned_data['aplicapara']
                                                            )
                    lineamiento.save(request)
                    log(u'Adicionado lineamiento: %s' % periodo, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'dellineamiento':
            try:
                lineamiento = LineamientoRecursoPeriodo.objects.get(pk=request.POST['id'])
                log(u"Elimino linemamiento: %s %s %s" % (lineamiento.tipoprofesor,lineamiento.tiporecurso,lineamiento.cantidad ), request, "del")
                lineamiento.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'addunidades':
            try:
                periodo = Periodo.objects.get(pk=request.POST['id'])
                f = UnidadesPeriodoForm(request.POST)
                if f.is_valid():
                    unidades = UnidadesPeriodo(periodo=periodo,
                                               descripcion=f.cleaned_data['descripcion'],
                                               tipoprofesor=f.cleaned_data['tipoprofesor'],
                                               fechainicio=f.cleaned_data['fechainicio'],
                                               fechafin=f.cleaned_data['fechafin'],
                                               orden=f.cleaned_data['orden'],
                                               nivelacion=f.cleaned_data['nivelacion'])
                    unidades.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editunidad':
            try:
                f = UnidadesPeriodoForm(request.POST)
                if f.is_valid():
                    unidad = UnidadesPeriodo.objects.get(pk=request.POST['id'])
                    unidad.descripcion = f.cleaned_data['descripcion']
                    unidad.tipoprofesor = f.cleaned_data['tipoprofesor']
                    unidad.fechainicio = f.cleaned_data['fechainicio']
                    unidad.fechafin = f.cleaned_data['fechafin']
                    unidad.orden = f.cleaned_data['orden']
                    unidad.nivelacion = f.cleaned_data['nivelacion']
                    unidad.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delunidad':
            try:
                unidad = UnidadesPeriodo.objects.get(pk=request.POST['id'])
                log(u"Elimino unidad: %s" % unidad.descripcion, request, "del")
                unidad.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'addgrupo':
            try:
                periodo = Periodo.objects.get(pk=request.POST['id'])
                f = PeriodoGrupoSocioEconomicoForm(request.POST)
                if f.is_valid():
                    if PeriodoGrupoSocioEconomico.objects.values('id').filter(periodo=periodo, gruposocioeconomico=f.cleaned_data['gruposocioeconomico'], status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe un grupo al periodo."})
                    periodogruposocioeconomico = PeriodoGrupoSocioEconomico(periodo=periodo,
                                                                            gruposocioeconomico=f.cleaned_data['gruposocioeconomico'],
                                                                            valor=Decimal(f.cleaned_data['valor']).quantize(Decimal('.01')))
                    periodogruposocioeconomico.save(request)
                    log(u'Adicionado grupo al periodo: %s' % periodogruposocioeconomico, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editgrupo':
            try:
                periodogruposocioeconomico = PeriodoGrupoSocioEconomico.objects.get(pk=request.POST['idgrupo'])
                f = PeriodoGrupoSocioEconomicoForm(request.POST)
                if f.is_valid():
                    periodogruposocioeconomico.valor = Decimal(f.cleaned_data['valor']).quantize(Decimal('.01'))
                    periodogruposocioeconomico.save(request)
                    log(u"Modifico grupo al periodo: %s" % periodogruposocioeconomico, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addcronogramapremodulo':
            try:
                periodo = Periodo.objects.get(pk=request.POST['id'])
                f = CronogramaMatriculacionFormModulo(request.POST)
                if f.is_valid():
                    if PeriodoPreMatriculacionModulo.objects.values('id').filter(periodo=periodo, nivelmalla=f.cleaned_data['nivelmalla'], carrera=f.cleaned_data['carrera'], modalidad=f.cleaned_data['modalidad']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe un cronograma de prematriculacion modulo con estos datos."})
                    periodo = PeriodoPreMatriculacionModulo(periodo=periodo,
                                                            nivelmalla=f.cleaned_data['nivelmalla'],
                                                            carrera=f.cleaned_data['carrera'],
                                                            modalidad=f.cleaned_data['modalidad'],
                                                            fecha_inicio=f.cleaned_data['inicio'],
                                                            fecha_fin=f.cleaned_data['fin'])
                    periodo.save(request)
                    log(u'Adicionado periodo de prematriculacion modulo: %s' % periodo, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editcronograma':
            try:
                cronograma = PeriodoMatriculacion.objects.get(pk=request.POST['id'])
                f = CronogramaMatriculacionForm(request.POST)
                if f.is_valid():
                    cronograma.fecha_inicio = f.cleaned_data['inicio']
                    cronograma.fecha_fin = f.cleaned_data['fin']
                    cronograma.prematricula = f.cleaned_data['prematricula']
                    cronograma.dias = f.cleaned_data['dias']
                    cronograma.save(request)
                    log(u'Edit cronograma periodo de prematriculacion modulo: %s' % cronograma, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'cambiaestado':
            try:
                periodolec = Periodo.objects.get(pk=request.POST['periodoid'])
                if periodolec.visible:
                    periodolec.visible = False
                else:
                    periodolec.visible = True
                log(u'Edit estado visible periodo lectivo: %s' % periodolec, request, "edit")
                periodolec.save(request)
                return JsonResponse({'result': 'ok', 'valor': periodolec.visible})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'cambiaestadohorario':
            try:
                periodolec = Periodo.objects.get(pk=request.POST['periodoid'])
                if periodolec.visiblehorario:
                    periodolec.visiblehorario = False
                else:
                    periodolec.visiblehorario = True
                log(u'Edit estado visible horario (%s) periodo lectivo: %s' % (periodolec.visiblehorario, periodolec), request, "edit")
                periodolec.save(request)
                return JsonResponse({'result': 'ok', 'valor': periodolec.visiblehorario})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editcronogramapre':
            try:
                cronograma = PeriodoPreMatriculacion.objects.get(pk=request.POST['id'])
                f = CronogramaMatriculacionFormPre(request.POST)
                if f.is_valid():
                    cronograma.fecha_inicio = f.cleaned_data['inicio']
                    cronograma.fecha_fin = f.cleaned_data['fin']
                    cronograma.save(request)
                    log(u'Edit cronograma periodo pre lectivo: %s' % cronograma, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editcronogramapremodulo':
            try:
                cronograma = PeriodoPreMatriculacionModulo.objects.get(pk=request.POST['id'])
                f = CronogramaMatriculacionFormModulo(request.POST)
                if f.is_valid():
                    cronograma.fecha_inicio = f.cleaned_data['inicio']
                    cronograma.fecha_fin = f.cleaned_data['fin']
                    cronograma.save(request)
                    log(u'Edit cronograma periodo premodulo lectivo: %s' % cronograma, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'edit':
            try:
                f = PeriodoForm(request.POST)
                if f.is_valid():
                    periodo = Periodo.objects.get(pk=request.POST['id'])
                    # if periodo.nivel_set.values('id').filter(fin__gt=f.cleaned_data['fin']).exists():
                    #     return JsonResponse({"result": "bad", "mensaje": u"La fecha fin no pueder ser menor a un nivel existente."})
                    # if periodo.nivel_set.values('id').filter(inicio__lt=f.cleaned_data['inicio']).exists():
                    #     return JsonResponse({"result": "bad", "mensaje": u"La fecha inicio no pueder ser mayor a un nivel existente."})
                    periodo.nombre = f.cleaned_data['nombre']
                    periodo.inicio = f.cleaned_data['inicio']
                    periodo.fin = f.cleaned_data['fin']
                    periodo.activo = True
                    periodo.anio = f.cleaned_data['anio']
                    periodo.tipo = f.cleaned_data['tipo']
                    periodo.evaluaciondocentemateria = True
                    periodo.valida_asistencia = f.cleaned_data['valida_asistencia']
                    periodo.visiblehorario = f.cleaned_data['visiblehorario']
                    periodo.inicio_agregacion = f.cleaned_data['inicio_agregacion']
                    periodo.limite_agregacion = f.cleaned_data['limite_agregacion']
                    periodo.limite_retiro = f.cleaned_data['limite_retiro']
                    periodo.porcentaje_gratuidad = f.cleaned_data['porcentaje_gratuidad']
                    periodo.valor_maximo = f.cleaned_data['valor_maximo']
                    periodo.clasificacion = f.cleaned_data['clasificacion']
                    periodo.cohorte = f.cleaned_data['cohorte']
                    if int(f.cleaned_data['clasificacion']) == 2 and f.cleaned_data['tipo'].id == 3:
                        periodo.categoria=4
                        periodo.urlmoodle='https://aulaposgrado.unemi.edu.ec'
                        periodo.keymoodle='65293afed416ee1dc5dd1b137c35f03d'
                        periodo.rolprofesortutor=9
                        periodo.rolprofesor=9
                        periodo.rolestudiante=10
                    periodo.save(request)
                    periodo.get_periodoacademia()
                    log(u'Edito periodo lectivo: %s' % periodo, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'edittopealumnos':
            try:
                f = TopeAlumnosPrimeroForm(request.POST)
                if f.is_valid():
                    topealumnosprimero = TopeAlumnosPrimero.objects.get(pk=request.POST['id'])
                    topealumnosprimero.cantidad = f.cleaned_data['cantidad']
                    topealumnosprimero.save(request)
                    log(u'Edito tope carrera: %s' % topealumnosprimero, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delperiodo':
            try:
                periodo = Periodo.objects.get(pk=request.POST['id'])
                log(u"Elimino periodo: %s" % periodo, request, "del")
                periodo.delete()
                return JsonResponse({"result": "ok", "id": periodo.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'delgrupo':
            try:
                periodogruposocioeconomico = PeriodoGrupoSocioEconomico.objects.get(pk=request.POST['id'])
                periodogruposocioeconomico.status = False
                periodogruposocioeconomico.save(request)
                log(u"Elimino grupo socio economico del periodo: %s" % periodogruposocioeconomico, request, "del")
                return JsonResponse({"result": "ok", "id": periodogruposocioeconomico.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'delcronograma':
            try:
                periodo = PeriodoMatriculacion.objects.get(pk=request.POST['id'])
                log(u"Elimino cronograma de matriculacion: %s" % periodo, request, "del")
                periodo.delete()
                return JsonResponse({"result": "ok", "id": periodo.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'delcronogramapre':
            try:
                periodo = PeriodoPreMatriculacion.objects.get(pk=request.POST['id'])
                log(u"Elimino cronograma de prematriculacion: %s" % periodo, request, "del")
                periodo.delete()
                return JsonResponse({"result": "ok", "id": periodo.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'gruposocioeconomico':
            try:
                f = PeriodoVariablesGrupoSocioEconomicoForm(request.POST)
                if f.is_valid():
                    periodo = Periodo.objects.get(pk=request.POST['id'])
                    periodo.presupuesto = f.cleaned_data['presupuesto']
                    periodo.totalestudiantes = f.cleaned_data['totalestudiantes']
                    periodo.semestreanio = f.cleaned_data['semestreanio']
                    periodo.limite = f.cleaned_data['limite']
                    periodo.nivelmalla = f.cleaned_data['nivelmalla']
                    periodo.creditocarrera = f.cleaned_data['creditocarrera']
                    periodo.save(request)
                    calculo = 0
                    try:
                        calculo = ((((periodo.presupuesto / periodo.totalestudiantes) * (1 / periodo.semestreanio)) * (periodo.limite / 100)) / (periodo.creditocarrera / periodo.nivelmalla))
                    except:
                        pass
                    PeriodoGrupoSocioEconomico.objects.filter(periodo=periodo).delete()
                    porcentaje = 100
                    for gruposocioeconomico in GrupoSocioEconomico.objects.filter(status=True).order_by('id'):
                        valor = (calculo * porcentaje) / 100
                        periodogruposocioeconomico = PeriodoGrupoSocioEconomico(periodo=periodo,
                                                                                gruposocioeconomico=gruposocioeconomico,
                                                                                valor=valor)
                        periodogruposocioeconomico.save(request)
                        porcentaje -= 20

                    log(u"Calculo variable periodo: %s" % periodo, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'updatecantidad':
            try:
                componenteperiodo = EvaluacionComponentePeriodo.objects.get(pk=request.POST['idcodigo'])
                componenteperiodo.cantidad = request.POST['cantidad']
                componenteperiodo.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al actualizar los datos."})

        if action == 'importarlineamiento':
            try:
                periodoimp = Periodo.objects.get(pk=request.POST['idper'])
                lineamientoimp = periodoimp.lineamientorecursoperiodo_set.filter(status=True).order_by('tipoprofesor_id')
                if lineamientoimp:
                    periodo = Periodo.objects.get(pk=request.POST['id'])
                    lineamiento = periodo.lineamientorecursoperiodo_set.filter(status=True).order_by('tipoprofesor_id')
                    contador=0
                    for lin in lineamientoimp:
                        if not lineamiento.filter(tiporecurso=lin.tiporecurso, tipoprofesor_id=lin.tipoprofesor_id).exists():
                            newlineamiento = LineamientoRecursoPeriodo(tiporecurso=lin.tiporecurso, cantidad=lin.cantidad, tipoprofesor_id=lin.tipoprofesor_id, periodo = periodo)
                            newlineamiento.save()
                            contador+= 1
                    if contador != 0 :
                        return JsonResponse({"result": "ok", "mensaje": u"Se importaron "+ str(contador) +" lineamientos."})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Datos ya existentes."})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Este periodo no tiene lineamientos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al importar los datos."})

        if action == 'importarcomponente':
            try:
                puede_realizar_accion(request, 'inno.puede_configurar_componente_periodo')
                periodoimp = Periodo.objects.get(pk=request.POST['idper'])
                componenteimp = periodoimp.evaluacioncomponenteperiodo_set.filter(status=True).order_by('parcial','componente_id')
                if componenteimp:
                    periodo = Periodo.objects.get(pk=request.POST['id'])
                    componente = periodo.evaluacioncomponenteperiodo_set.filter(status=True).order_by('parcial','componente_id')
                    contador=0
                    for comp in componenteimp:
                        if not componente.filter(componente= comp.componente, parcial= comp.parcial).exists():
                            newcomponente = EvaluacionComponentePeriodo(componente= comp.componente, parcial= comp.parcial, cantidad=comp.cantidad, periodo = periodo)
                            newcomponente.save()
                            contador+= 1
                    if contador != 0 :
                        return JsonResponse({"result": "ok", "mensaje": u"Se importaron "+ str(contador) +" componentes."})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Datos ya existentes."})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Este periodo no tiene componentes."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": f"Error al importar los datos. {ex}"})

        elif action == 'adddetallecomponente':
            try:
                with transaction.atomic():
                    puede_realizar_accion(request, 'inno.puede_configurar_componente_periodo')
                    f = DetalleEvaluacionComponentePeriodoForm(request.POST)
                    ecp = EvaluacionComponentePeriodo.objects.get(pk=int(request.POST['idp']))
                    f.iniciar(ecp)
                    if f.is_valid():
                        registro = DetalleEvaluacionComponentePeriodo(evaluacioncomponenteperiodo=ecp, actividad=f.cleaned_data['actividad'], cantidad=f.cleaned_data['cantidad'], obligatorio=f.cleaned_data['obligatorio'])
                        registro.save(request)
                        log(u'Adicionó detalle evaluacion componente periodo: %s' % (registro), request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s'%ex}, safe=False)

        elif action == 'editdetallecomponente':
            try:
                with transaction.atomic():
                    puede_realizar_accion(request, 'inno.puede_configurar_componente_periodo')
                    registro = DetalleEvaluacionComponentePeriodo.objects.get(pk=request.POST['id'])
                    f = DetalleEvaluacionComponentePeriodoForm(request.POST)
                    f.editar(registro)
                    if f.is_valid():
                        registro.actividad = f.cleaned_data['actividad']
                        registro.cantidad = f.cleaned_data['cantidad']
                        registro.obligatorio = f.cleaned_data['obligatorio']
                        registro.save(request)
                        log(u'Editó registro detalle evaluacion componente periodo: %s' % registro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": f"Intentelo más tarde. {ex}"}, safe=False)

        elif action == 'deletedetallecomponente':
            try:
                with transaction.atomic():
                    puede_realizar_accion(request, 'inno.puede_configurar_componente_periodo')
                    registro = DetalleEvaluacionComponentePeriodo.objects.get(pk=int(request.POST['id']))
                    log(u'Eliminó registro supervisar práctica Salud: %s' % registro, request, "delete")
                    registro.delete()
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'eliminarcomponentes':
            try:
                puede_realizar_accion(request, 'inno.puede_configurar_componente_periodo')
                periodo = Periodo.objects.get(pk=request.POST['id'])
                componente = periodo.evaluacioncomponenteperiodo_set.filter(status=True).order_by('parcial','componente_id')
                for comp in componente:
                    comp.status = False
                    comp.save()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'eliminarlineamientos':
            try:
                periodo = Periodo.objects.get(pk=request.POST['id'])
                lineamiento = periodo.lineamientorecursoperiodo_set.filter(status=True)
                for lin in lineamiento:
                    lin.status = False
                    lin.save()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data = {}
        adduserdata(request, data)
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Abrir un nuevo período'
                    data['form'] = PeriodoForm(initial={'inicio': datetime.now().date(),
                                                        'fin': (datetime.now() + timedelta(days=180)).date(),
                                                        'inicio_agregacion': (datetime.now() + timedelta(days=15)).date(),
                                                        'limite_agregacion': (datetime.now() + timedelta(days=30)).date(),
                                                        'limite_retiro': (datetime.now() + timedelta(days=30)).date(),
                                                        'valida_asistencia': True})
                    return render(request, "adm_periodos/add.html", data)
                except Exception as ex:
                    pass

            elif action == 'edit':
                try:
                    data['title'] = u'Editar periodo'
                    periodo = Periodo.objects.get(pk=request.GET['id'])
                    form = PeriodoForm(initial={'nombre': periodo.nombre,
                                                'inicio': periodo.inicio,
                                                'fin': periodo.fin,
                                                'tipo': periodo.tipo,
                                                'anio': periodo.anio,
                                                'inicio_agregacion': periodo.inicio_agregacion,
                                                'limite_agregacion': periodo.limite_agregacion,
                                                'limite_retiro': periodo.limite_retiro,
                                                'visiblehorario': periodo.visiblehorario,
                                                'valida_asistencia': True,
                                                'porcentaje_gratuidad': periodo.porcentaje_gratuidad,
                                                'valor_maximo': periodo.valor_maximo,
                                                'clasificacion': periodo.clasificacion,
                                                'cohorte':periodo.cohorte})
                    data['form'] = form
                    data['periodo'] = periodo
                    return render(request, "adm_periodos/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'delperiodo':
                try:
                    data['title'] = u'Eliminar período'
                    data['periodo'] = Periodo.objects.get(pk=request.GET['id'])
                    return render(request, "adm_periodos/delperiodo.html", data)
                except Exception as ex:
                    pass

            if action == 'cromatriculacion':
                try:
                    data['title'] = u'Cronograma de matriculación'
                    data['periodoc'] = periodo = Periodo.objects.get(pk=request.GET['id'])
                    data['cronogramas'] = periodo.periodomatriculacion_set.all().order_by('carrera', 'nivelmalla')
                    return render(request, "adm_periodos/cromatriculacion.html", data)
                except Exception as ex:
                    pass

            if action == 'croprematriculacion':
                try:
                    data['title'] = u'Cronograma de prematriculación'
                    data['periodo'] = periodo = Periodo.objects.get(pk=request.GET['id'])
                    data['cronogramas'] = periodo.periodoprematriculacion_set.all().order_by('carrera', 'nivelmalla')
                    return render(request, "adm_periodos/croprematriculacion.html", data)
                except Exception as ex:
                    pass

            if action == 'topealumnos':
                try:
                    data['title'] = u'Cantidad de alumnos a primero'
                    data['periodo'] = periodo = Periodo.objects.get(pk=request.GET['id'])
                    data['topealumnosprimeros'] = topealumnosprimero  = TopeAlumnosPrimero.objects.filter(periodo=periodo, status=True).order_by('carrera')
                    data['cantidad'] = null_to_numeric(topealumnosprimero.aggregate(suma=Sum('cantidad'))['suma'])
                    return render(request, "adm_periodos/topealumnos.html", data)
                except Exception as ex:
                    pass

            if action == 'listadolineamientos':
                try:
                    data['title'] = u'Listado de lineamiento recurso de aprendizaje'
                    data['periodo'] = periodo = Periodo.objects.get(pk=request.GET['id'])
                    data['periodosimportar'] = Periodo.objects.filter(status=True, tipo_id=2).exclude(pk=request.GET['id']).order_by("-inicio")
                    data['hoy'] = datetime.now().date()
                    data['listado'] = periodo.lineamientorecursoperiodo_set.filter(status=True).order_by('nivelacion', 'tipoprofesor_id')
                    return render(request, "adm_periodos/listadolineamientos.html", data)
                except Exception as ex:
                    pass

            if action == 'listadounidades':
                try:
                    data['title'] = u'Listado de unidades'
                    data['periodo'] = periodo = Periodo.objects.get(pk=request.GET['id'])
                    data['hoy'] = datetime.now().date()
                    data['listado'] = periodo.unidadesperiodo_set.filter(status=True).order_by('nivelacion','orden')
                    return render(request, "adm_periodos/listadounidades.html", data)
                except Exception as ex:
                    pass

            if action == 'listadocomponentes':
                try:
                    data['title'] = u'Listado de componentes'
                    data['puede_configurar'] = puede_realizar_accion_afirmativo(request, 'inno.puede_configurar_componente_periodo')
                    data['periodo'] = periodo = Periodo.objects.get(pk=request.GET['id'])
                    data['periodosimportar'] = Periodo.objects.filter(status=True, tipo_id=2).exclude(pk=request.GET['id']).order_by("-inicio")
                    data['hoy'] = datetime.now().date()
                    data['listado'] = periodo.evaluacioncomponenteperiodo_set.filter(status=True).order_by('parcial','componente_id')
                    return render(request, "adm_periodos/listadocomponentes.html", data)
                except Exception as ex:
                    pass

            elif action == 'adddetallecomponente':
                try:
                    data['action'] = request.GET['action']
                    data['title'] = u'Adicionar turno'
                    data['idp'] = idp = int(request.GET['idp'])
                    ecp = EvaluacionComponentePeriodo.objects.get(pk=idp)
                    form = DetalleEvaluacionComponentePeriodoForm()
                    form.iniciar(ecp)
                    data['form'] = form
                    template = get_template("adm_periodos/modal/formdetalle.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'editdetallecomponente':
                try:
                    data['title'] = u'Editar registro supervisión'
                    data['action'] = request.GET['action']
                    if id := int(request.GET.get('id', 0)): data['id'] = id
                    if id > 0:
                        data['registro'] = registro = DetalleEvaluacionComponentePeriodo.objects.get(pk=id)
                        f = DetalleEvaluacionComponentePeriodoForm(initial={'cantidad': registro.cantidad, 'obligatorio': registro.obligatorio})
                        f.editar(registro)
                        data['form'] = f
                        template = get_template("adm_periodos/modal/formdetalle.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    else:
                        return JsonResponse({"result": False, "mensaje": u"Problemas al obtener los datos. Intente nuevamente más tarde."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos. Intente nuevamente más tarde."})

            if action == 'croprematriculacionmodulo':
                try:
                    data['title'] = u'Cronograma de prematriculación modulos'
                    data['periodo'] = periodo = Periodo.objects.get(pk=request.GET['id'])
                    data['cronogramas'] = periodo.periodoprematriculacionmodulo_set.all().order_by('carrera', 'nivelmalla')
                    return render(request, "adm_periodos/croprematriculacionmodulo.html", data)
                except Exception as ex:
                    pass

            if action == 'addcronograma':
                try:
                    data['title'] = u'Adicionar cronograma de matriculación'
                    data['periodo'] = Periodo.objects.get(pk=request.GET['id'])
                    data['form'] = CronogramaMatriculacionForm(initial={'inicio': datetime.now().date(),
                                                                        'fin': datetime.now().date()})
                    return render(request, "adm_periodos/addcronograma.html", data)
                except Exception as ex:
                    pass

            if action == 'addcronogramapre':
                try:
                    data['title'] = u'Adicionar cronograma de prematriculación'
                    data['periodo'] = Periodo.objects.get(pk=request.GET['id'])
                    data['form'] = CronogramaMatriculacionFormPre()
                    return render(request, "adm_periodos/addcronogramapre.html", data)
                except Exception as ex:
                    pass

            if action == 'addtopealumnos':
                try:
                    data['title'] = u'Adicionar tope estudiantes a primero'
                    data['periodo'] = Periodo.objects.get(pk=request.GET['id'])
                    data['form'] = TopeAlumnosPrimeroForm()
                    return render(request, "adm_periodos/addtopealumnos.html", data)
                except Exception as ex:
                    pass

            if action == 'edittopealumnos':
                try:
                    data['title'] = u'Editar tope estudiantes a primero'
                    topealumnosprimero = TopeAlumnosPrimero.objects.get(pk=request.GET['id'])
                    form = TopeAlumnosPrimeroForm(initial={'carrera': topealumnosprimero.carrera,
                                                           'cantidad': topealumnosprimero.cantidad})
                    form.editar()
                    data['form'] = form
                    data['topealumnosprimero'] = topealumnosprimero
                    data['periodo'] = topealumnosprimero.periodo
                    return render(request, "adm_periodos/edittopealumnos.html", data)
                except Exception as ex:
                    pass

            if action == 'deltopealumnos':
                try:
                    data['title'] = u'Eliminar carrera tope estudiantes a primero'
                    data['topealumnosprimero'] = topealumnosprimero = TopeAlumnosPrimero.objects.get(pk=request.GET['id'])
                    data['periodo'] = topealumnosprimero.periodo
                    return render(request, "adm_periodos/deltopealumnos.html", data)
                except Exception as ex:
                    pass

            if action == 'addlineamiento':
                try:
                    data['title'] = u'Adicionar lineamiento'
                    data['periodo'] = Periodo.objects.get(pk=request.GET['id'])
                    data['form'] = LineamientoRecursoPeriodoForm()
                    return render(request, "adm_periodos/addlineamiento.html", data)
                except Exception as ex:
                    pass

            if action == 'dellineamiento':
                try:
                    data['title'] = u'Eliminar lineamiento'
                    data['itemlineamiento'] = LineamientoRecursoPeriodo.objects.get(pk=request.GET['id'])
                    return render(request, "adm_periodos/dellineamiento.html", data)
                except Exception as ex:
                    pass

            if action == 'addunidades':
                try:
                    data['title'] = u'Adicionar lineamiento'
                    data['periodo'] = Periodo.objects.get(pk=request.GET['id'])
                    data['form'] = UnidadesPeriodoForm()
                    return render(request, "adm_periodos/addunidades.html", data)
                except Exception as ex:
                    pass

            if action == 'editunidad':
                try:
                    data['title'] = u'Editar unidades'
                    data['unidad'] = unidad = UnidadesPeriodo.objects.get(pk=request.GET['id'])
                    form = UnidadesPeriodoForm(initial={'descripcion': unidad.descripcion,
                                                        'tipoprofesor': unidad.tipoprofesor,
                                                        'fechainicio': unidad.fechainicio,
                                                        'fechafin': unidad.fechafin,
                                                        'orden': unidad.orden})
                    data['form'] = form
                    data['periodo'] = unidad.periodo
                    return render(request, "adm_periodos/editunidad.html", data)
                except Exception as ex:
                    pass

            if action == 'delunidad':
                try:
                    data['title'] = u'Eliminar Unidad'
                    data['itemunidad'] = UnidadesPeriodo.objects.get(pk=request.GET['id'])
                    return render(request, "adm_periodos/delunidad.html", data)
                except Exception as ex:
                    pass

            if action == 'addcronogramapremodulo':
                try:
                    data['title'] = u'Adicionar cronograma de prematriculación modulo'
                    data['periodo'] = Periodo.objects.get(pk=request.GET['id'])
                    data['form'] = CronogramaMatriculacionFormModulo()
                    return render(request, "adm_periodos/addcronogramapremodulo.html", data)
                except Exception as ex:
                    pass

            if action == 'addgrupo':
                try:
                    data['title'] = u'Adicionar grupo socio económico al Periodo'
                    data['periodo'] = Periodo.objects.get(pk=request.GET['idperiodo'])
                    data['form'] = PeriodoGrupoSocioEconomicoForm()
                    return render(request, "adm_periodos/addgrupo.html", data)
                except Exception as ex:
                    pass

            if action == 'editgrupo':
                try:
                    data['title'] = u'Editar grupo socio económico al Periodo'
                    data['periodogruposocioeconomico'] = periodogruposocioeconomico = PeriodoGrupoSocioEconomico.objects.get(pk=request.GET['idgrupo'])
                    form = PeriodoGrupoSocioEconomicoForm(initial={'gruposocioeconomico': periodogruposocioeconomico.gruposocioeconomico,
                                                                   'valor': periodogruposocioeconomico.valor})
                    form.editar()
                    data['form'] = form
                    return render(request, "adm_periodos/editgrupo.html", data)
                except Exception as ex:
                    pass

            if action == 'delgrupo':
                try:
                    data['title'] = u'Eliminar grupo socio económico al Periodo'
                    data['periodogruposocioeconomico'] = periodogruposocioeconomico = PeriodoGrupoSocioEconomico.objects.get(pk=request.GET['id'])
                    return render(request, "adm_periodos/delgrupo.html", data)
                except Exception as ex:
                    pass

            if action == 'editcronograma':
                try:
                    data['title'] = u'Editar cronograma de matriculación'
                    cronograma = PeriodoMatriculacion.objects.get(pk=request.GET['id'])
                    data['cronograma'] = cronograma
                    form = CronogramaMatriculacionForm(initial={'inicio': cronograma.fecha_inicio,
                                                                'fin': cronograma.fecha_fin,
                                                                'carrera': cronograma.carrera,
                                                                'modalidad': cronograma.modalidad,
                                                                'prematricula': cronograma.prematricula,
                                                                'dias': cronograma.dias,
                                                                'nivelmalla': cronograma.nivelmalla})
                    form.editar()
                    data['form'] = form
                    return render(request, "adm_periodos/editcronograma.html", data)
                except Exception as ex:
                    pass

            if action == 'editcronogramapre':
                try:
                    data['title'] = u'Editar cronograma de prematriculación'
                    cronograma = PeriodoPreMatriculacion.objects.get(pk=request.GET['id'])
                    data['cronograma'] = cronograma
                    form = CronogramaMatriculacionFormPre(initial={'inicio': cronograma.fecha_inicio,
                                                                   'fin': cronograma.fecha_fin,
                                                                   'carrera': cronograma.carrera,
                                                                   'modalidad': cronograma.modalidad,
                                                                   'nivelmalla': cronograma.nivelmalla})
                    form.editar()
                    data['form'] = form
                    return render(request, "adm_periodos/editcronogramapre.html", data)
                except Exception as ex:
                    pass

            if action == 'editcronogramapremodulo':
                try:
                    data['title'] = u'Editar cronograma de prematriculación modulo'
                    cronograma = PeriodoPreMatriculacionModulo.objects.get(pk=request.GET['id'])
                    data['cronograma'] = cronograma
                    form = CronogramaMatriculacionFormModulo(initial={'inicio': cronograma.fecha_inicio,
                                                                      'fin': cronograma.fecha_fin,
                                                                      'carrera': cronograma.carrera,
                                                                      'modalidad': cronograma.modalidad,
                                                                      'nivelmalla': cronograma.nivelmalla})
                    form.editar()
                    data['form'] = form
                    return render(request, "adm_periodos/editcronogramapremodulo.html", data)
                except Exception as ex:
                    pass

            if action == 'delcronograma':
                try:
                    data['title'] = u'Eliminar cronograma de matriculación'
                    data['cronograma'] = PeriodoMatriculacion.objects.get(pk=request.GET['id'])
                    return render(request, "adm_periodos/delcronograma.html", data)
                except Exception as ex:
                    pass

            if action == 'delcronogramapre':
                try:
                    data['title'] = u'Eliminar cronograma de prematriculación'
                    data['cronograma'] = PeriodoPreMatriculacion.objects.get(pk=request.GET['id'])
                    return render(request, "adm_periodos/delcronogramapre.html", data)
                except Exception as ex:
                    pass

            if action == 'gruposocioeconomico':
                try:
                    data['title'] = u'Valor Grupo Socio Económico'
                    data['periodogrupo'] = periodo1 = Periodo.objects.get(pk=request.GET['id'])
                    data['periodogruposocioeconomico'] = PeriodoGrupoSocioEconomico.objects.filter(periodo=periodo1, status=True).order_by('-id')
                    form = PeriodoVariablesGrupoSocioEconomicoForm(initial={'presupuesto': periodo1.presupuesto,
                                                                            'totalestudiantes': periodo1.totalestudiantes,
                                                                            'semestreanio': periodo1.semestreanio,
                                                                            'limite': periodo1.limite,
                                                                            'nivelmalla': periodo1.nivelmalla,
                                                                            'creditocarrera': periodo1.creditocarrera})
                    data['form'] = form
                    data['permite_modificar'] = not periodo1.matriculados().values('id').exists()
                    return render(request, "adm_periodos/gruposocioeconomico.html", data)
                except Exception as ex:
                    pass

            if action == 'deshabprematricula':
                try:
                    periodo = Periodo.objects.get(pk=request.GET['id'])
                    periodo.prematriculacionactiva = False
                    periodo.save(request)
                    log(u"deshabilito pre matricula: %s" % periodo, request, "edit")
                    return HttpResponseRedirect('/adm_periodos')
                except Exception as ex:
                    pass

            if action == 'habprematricula':
                try:
                    periodo = Periodo.objects.get(pk=request.GET['id'])
                    periodo.prematriculacionactiva = True
                    periodo.save(request)
                    log(u"habilito pre matricula: %s" % periodo, request, "edit")
                    return HttpResponseRedirect('/adm_periodos')
                except Exception as ex:
                    pass

            if action == 'deshabmatricula':
                try:
                    periodo = Periodo.objects.get(pk=request.GET['id'])
                    periodo.matriculacionactiva = False
                    periodo.save(request)
                    log(u"deshabilito matricula: %s" % periodo, request, "edit")
                    return HttpResponseRedirect('/adm_periodos')
                except Exception as ex:
                    pass

            if action == 'habmatricula':
                try:
                    periodo = Periodo.objects.get(pk=request.GET['id'])
                    periodo.matriculacionactiva = True
                    periodo.save(request)
                    log(u"habilito matricula: %s" % periodo, request, "edit")
                    return HttpResponseRedirect('/adm_periodos')
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Periodos lectivos de la institución'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
                periodos = Periodo.objects.filter(Q(nombre__icontains=search) |
                                                  Q(tipo__nombre__icontains=search)).distinct().order_by("-inicio")
            elif 'id' in request.GET:
                ids = request.GET['id']
                periodos = Periodo.objects.filter(id=ids).order_by("-inicio")
            else:
                periodos = Periodo.objects.all().order_by("-inicio")
            paging = MiPaginador(periodos, 25)
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
            data['periodos'] = page.object_list
            return render(request, "adm_periodos/view.html", data)