# -*- coding: UTF-8 -*-
import json
from decimal import Decimal

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
from django.core.serializers import serialize

from bd.models import LogQuery, get_deleted_objects, LogEntryLogin, CronogramaCoordinacion, CronogramaCarrera
from decorators import secure_module
from bd.forms import *
from inno.models import PeriodoAcademia, PeriodoMalla, DetallePeriodoMalla
from matricula.models import PeriodoMatricula, FechaCuotaRubro, CostoOptimoMalla
from sga.commonviews import adduserdata
from django.db import connection, transaction
from django.template import Context
import sys
from django.template.loader import get_template
from sga.funciones import log, puede_realizar_accion, puede_realizar_accion_is_superuser, logquery, convertir_fecha, \
    resetear_clave, convertir_fecha_invertida, null_to_decimal
from sga.models import Persona, LogEntryBackup, LogEntryBackupdos, AgregacionEliminacionMaterias, Inscripcion, Modulo, \
    ModuloGrupo, Periodo, TipoPeriodo, CoordinadorCarrera, Sede, Nivel, PeriodoGrupoSocioEconomico
from sga.templatetags.sga_extras import encrypt
from socioecon.models import GrupoSocioEconomico


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    #
    # try:
    #     puede_realizar_accion(request, 'bd.puede_acceder_periodo_academico')
    # except Exception as ex:
    #     return HttpResponseRedirect(f"/?info={ex.__str__()}")
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'loadDataTable':
            try:
                txt_filter = request.POST['sSearch'] if request.POST['sSearch'] else ''
                limit = int(request.POST['iDisplayLength']) if request.POST['iDisplayLength'] else 25
                offset = int(request.POST['iDisplayStart']) if request.POST['iDisplayStart'] else 0
                visible = int(request.POST['visible']) if request.POST['visible'] else 0
                activo = int(request.POST['activo']) if request.POST['activo'] else 0
                valida_asistencia = int(request.POST['valida_asistencia']) if request.POST['valida_asistencia'] else 0
                visiblehorario = int(request.POST['visiblehorario']) if request.POST['visiblehorario'] else 0
                matriculacionactiva = int(request.POST['matriculacionactiva']) if request.POST['matriculacionactiva'] else 0
                tipo_periodo = int(request.POST['tipo_periodo']) if request.POST['tipo_periodo'] else 0
                crontabactivo = int(request.POST['crontabactivo']) if request.POST['crontabactivo'] else 0
                aaData = []
                tCount = 0
                periodos = Periodo.objects.filter().order_by('-inicio')
                if not persona.usuario.is_staff:
                    periodos = periodos.filter(status=True)
                if txt_filter:
                    search = txt_filter.strip()
                    periodos = periodos.filter(Q(nombre__icontains=search))

                if activo > 0:
                    periodos = periodos.filter(activo=(activo == 1))

                if visible > 0:
                    periodos = periodos.filter(visible=(visible == 1))

                if valida_asistencia > 0:
                    periodos = periodos.filter(valida_asistencia=(valida_asistencia == 1))

                if visiblehorario > 0:
                    periodos = periodos.filter(visiblehorario=(visiblehorario == 1))

                if matriculacionactiva > 0:
                    periodos = periodos.filter(matriculacionactiva=(matriculacionactiva == 1))

                if tipo_periodo > 0:
                    periodos = periodos.filter(tipo_id=tipo_periodo)

                if crontabactivo > 0:
                    if crontabactivo == 1:
                        if PeriodoCrontab.objects.values("id").all().exists():
                            ePeriodoCrontabs = PeriodoCrontab.objects.filter(is_activo=True)
                            periodos = periodos.filter(pk__in=ePeriodoCrontabs.values_list("periodo_id", flat=True).distinct())
                    else:
                        if PeriodoCrontab.objects.values("id").all().exists():
                            ePeriodoCrontabs = PeriodoCrontab.objects.filter(is_activo=True)
                            periodos = periodos.exclude(pk__in=ePeriodoCrontabs.values_list("periodo_id", flat=True).distinct())

                tCount = periodos.count()
                if offset == 0:
                    rows = periodos[offset:limit]
                else:
                    rows = periodos[offset:offset + limit]
                aaData = []
                for row in rows:
                    ePeriodoCrontab = None
                    if PeriodoCrontab.objects.values("id").filter(periodo_id=row.id).exists():
                        ePeriodoCrontab = PeriodoCrontab.objects.filter(periodo_id=row.id)[0]
                    ePeriodoMatricula = None
                    if PeriodoMatricula.objects.values("id").filter(periodo_id=row.id).exists():
                        ePeriodoMatricula = PeriodoMatricula.objects.filter(periodo_id=row.id)[0]
                    aaData.append([row.id,
                                   row.nombre,
                                   {"inicio": row.inicio,
                                    "fin": row.fin,
                                    "inicio_agregacion": row.inicio_agregacion,
                                    "limite_agregacion": row.limite_agregacion,
                                    "limite_retiro": row.limite_retiro,
                                    "fecha_inicio_agregacion": row.fechainicioagregacion,
                                    "fecha_fin_agregacion": row.fechafinagregacion,
                                    "fecha_fin_retiro": row.fechafinquitar,
                                    },
                                   row.tipo.nombre,
                                   {"valida_asistencia": row.valida_asistencia,
                                    "activo": row.activo,
                                    "visible": row.visible,
                                    "visiblehorario": row.visiblehorario,
                                    "matriculacionactiva": row.matriculacionactiva,
                                    "crontabactivo": ePeriodoCrontab.is_activo if ePeriodoCrontab else False,
                                    },
                                   {"id": row.id,
                                    "nombre": row.nombre,
                                    "valida_cronograma": ePeriodoMatricula.valida_cronograma if ePeriodoMatricula else False,
                                    "tiene_cronograma": ePeriodoMatricula.tiene_cronograma_coordinaciones() if ePeriodoMatricula else False,
                                    },
                                   ])
                return JsonResponse({"result": "ok", "data": aaData, "iTotalRecords": tCount, "iTotalDisplayRecords": tCount})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos. %s" % ex.__str__(), "data": [], "iTotalRecords": 0, "iTotalDisplayRecords": 0})

        elif action == 'saveAcademicPeriod':
            try:
                id = int(request.POST['id']) if 'id' in request.POST and request.POST['id'] and int(request.POST['id']) != 0 else None
                typeForm = 'edit' if id else 'new'
                f = PeriodoForm(request.POST)
                f.set_delete()
                if not f.is_valid():
                    # [(k, v[0]) for k, v in f.errors.items()]
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                if typeForm == 'new':
                    puede_realizar_accion(request, 'bd.puede_agregar_periodo_academico')
                    if Periodo.objects.filter(nombre=f.cleaned_data['nombre']).exists():
                        raise NameError(u"Nombre debe ser único")

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
                                      visible=f.cleaned_data['visible'],
                                      visiblehorario=f.cleaned_data['visiblehorario'],
                                      valor_maximo=f.cleaned_data['valor_maximo'],
                                      fechainicioagregacion=f.cleaned_data['fecha_inicio_agregacion'],
                                      fechafinagregacion=f.cleaned_data['fecha_fin_agregacion'],
                                      fechafinquitar=f.cleaned_data['fecha_fin_quitar'],
                                      marcardefecto=f.cleaned_data['marcardefecto'],
                                      )
                    periodo.save(request)
                    periodoactual = request.session['periodo']
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
                    log(u'Adicionado periodo: %s' % periodo, request, "add")
                else:
                    puede_realizar_accion(request, 'bd.puede_modificar_periodo_academico')
                    if not Periodo.objects.filter(pk=id).exists():
                        raise NameError(u"No existe formulario a editar")
                    if Periodo.objects.filter(nombre=f.cleaned_data['nombre']).exclude(pk=id).exists():
                        raise NameError(u"Nombre debe ser única")
                    periodo = Periodo.objects.get(pk=id)
                    if periodo.nivel_set.values('id').filter(fin__gt=f.cleaned_data['fin']).exists():
                        raise NameError(u"La fecha fin no pueder ser menor a un nivel existente.")
                    if periodo.nivel_set.values('id').filter(inicio__lt=f.cleaned_data['inicio']).exists():
                        raise NameError(u"La fecha inicio no pueder ser mayor a un nivel existente.")
                    periodo.nombre = f.cleaned_data['nombre']
                    periodo.inicio = f.cleaned_data['inicio']
                    periodo.fin = f.cleaned_data['fin']
                    periodo.activo = True
                    periodo.tipo = f.cleaned_data['tipo']
                    periodo.evaluaciondocentemateria = True
                    periodo.valida_asistencia = f.cleaned_data['valida_asistencia']
                    periodo.visible = f.cleaned_data['visible']
                    periodo.visiblehorario = f.cleaned_data['visiblehorario']
                    periodo.inicio_agregacion = f.cleaned_data['inicio_agregacion']
                    periodo.limite_agregacion = f.cleaned_data['limite_agregacion']
                    periodo.limite_retiro = f.cleaned_data['limite_retiro']
                    periodo.porcentaje_gratuidad = f.cleaned_data['porcentaje_gratuidad']
                    periodo.valor_maximo = f.cleaned_data['valor_maximo']
                    periodo.fechainicioagregacion = f.cleaned_data['fecha_inicio_agregacion']
                    periodo.fechafinagregacion = f.cleaned_data['fecha_fin_agregacion']
                    periodo.fechafinquitar = f.cleaned_data['fecha_fin_quitar']
                    periodo.marcardefecto = f.cleaned_data['marcardefecto']
                    periodo.save(request)
                    log(u'Edito periodo lectivo: %s' % periodo, request, "edit")
                return JsonResponse({"result": "ok", "mensaje": u"Se guardo correctamente el periodo académico"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar el periodo académico. %s" % ex.__str__()})

        elif action == 'deleteAcademicPeriod':
            try:
                puede_realizar_accion(request, 'bd.puede_eliminar_periodo_academico')
                if not 'id' in request.POST or not request.POST['id']:
                    raise NameError(u"No se encontro registro a eliminar")
                object_id = int(request.POST['id'])
                if not Periodo.objects.filter(pk=object_id).exists():
                    raise NameError(u"No se encontro registro a eliminar")
                ePeriodo = Periodo.objects.get(pk=object_id)
                log(u'Elimino periodo académico: %s' % ePeriodo, request, "del")
                ePeriodo.delete()
                return JsonResponse({"result": "ok", "mensaje": u"Se elimino correctamente el periodo académico"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar el periodo académico. %s" % ex.__str__()})

        elif action == 'savePeriodoGrupo':
            try:
                id = int(request.POST['id']) if 'id' in request.POST and request.POST['id'] and int(request.POST['id']) != 0 else None
                f = PeriodoForm(request.POST)
                f.set_delete_grupos()
                typeForm = 'edit' if id else 'view'
                if not f.is_valid():
                    raise NameError(u"Debe ingresar la información en todos los campos")
                if typeForm == 'edit':
                    puede_realizar_accion(request, 'bd.puede_modificar_periodo_academico_grupo')
                    if not Periodo.objects.filter(pk=id).exists():
                        raise NameError(u"No existe formulario a editar")
                    ePeriodo = Periodo.objects.get(pk=id)
                    if PeriodoGrupo.objects.filter(periodo=ePeriodo).exists():
                        periodogrupo = PeriodoGrupo.objects.get(periodo=ePeriodo)
                        periodogrupo.visible = f.cleaned_data['visible']
                        periodogrupo.save(request)
                        if 'gruposs' in request.POST:
                            gruposs = json.loads(request.POST['gruposs'])
                            gruposs = [int(x) for x in gruposs]
                            gruposs_aux = periodogrupo.grupos.all()
                            for g in gruposs_aux:
                                if not g.id in gruposs:
                                    periodogrupo.grupos.remove(g)
                                    g.save()
                            for grupo in Group.objects.filter(pk__in=gruposs):
                                periodogrupo.grupos.add(grupo)
                        log(u'Edito periodo académico grupo: %s' % periodogrupo, request, "edit")
                    else:
                        periodogrupo = PeriodoGrupo(periodo=ePeriodo,
                                                    visible=f.cleaned_data['visible'],
                                                    )
                        periodogrupo.save(request)
                        if 'gruposs' in request.POST:
                            gruposs = json.loads(request.POST['gruposs'])
                            grupos = Group.objects.filter(pk__in=gruposs)
                            for g in grupos:
                                periodogrupo.grupos.add(g)
                        log(u'Adiciono periodo académico grupo: %s' % periodogrupo, request, "add")

                return JsonResponse({"result": "ok", "mensaje": u"Se guardo correctamente el grupo de modulo"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar el grupo de modulo. %s" % ex.__str__()})

        elif action == 'savePeriodoMatricula':
            try:
                id = int(request.POST['id']) if 'id' in request.POST and request.POST['id'] and int(request.POST['id']) != 0 else None
                f = PeriodoMatriculaForm(request.POST)
                typeForm = 'edit' if id else 'view'
                periodomatricula = None
                if not f.is_valid():
                    # [(k, v[0]) for k, v in f.errors.items()]
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                if typeForm == 'edit':
                    puede_realizar_accion(request, 'bd.puede_modificar_periodo_academico_matriculacion')
                    if not Periodo.objects.filter(pk=id).exists():
                        raise NameError(u"No existe formulario a editar")
                    ePeriodo = Periodo.objects.get(pk=id)
                    ePeriodo.inicio_agregacion = f.cleaned_data['inicio_agregacion']
                    ePeriodo.limite_agregacion = f.cleaned_data['limite_agregacion']
                    ePeriodo.limite_retiro = f.cleaned_data['limite_retiro']
                    ePeriodo.fechainicioagregacion = f.cleaned_data['fecha_inicio_agregacion']
                    ePeriodo.fechafinagregacion = f.cleaned_data['fecha_fin_agregacion']
                    ePeriodo.fechafinquitar = f.cleaned_data['fecha_fin_quitar']
                    ePeriodo.matriculacionactiva = f.cleaned_data['activo']
                    ePeriodo.tipocalculo = f.cleaned_data['tipocalculo']
                    ePeriodo.save(request)
                    log(u'Edito periodo lectivo: %s' % ePeriodo, request, "edit")
                    if PeriodoMatricula.objects.filter(periodo=ePeriodo).exists():
                        periodomatricula = PeriodoMatricula.objects.get(periodo=ePeriodo)
                        periodomatricula.activo = f.cleaned_data['activo']
                        periodomatricula.tipo = f.cleaned_data['tipo']
                        periodomatricula.valida_coordinacion = f.cleaned_data['valida_coordinacion']
                        periodomatricula.valida_cronograma = f.cleaned_data['valida_cronograma']
                        periodomatricula.valida_materia_carrera = f.cleaned_data['valida_materia_carrera']
                        periodomatricula.valida_seccion = f.cleaned_data['valida_seccion']
                        periodomatricula.valida_cupo_materia = f.cleaned_data['valida_cupo_materia']
                        periodomatricula.valida_horario_materia = f.cleaned_data['valida_horario_materia']
                        periodomatricula.valida_conflicto_horario = f.cleaned_data['valida_conflicto_horario']
                        periodomatricula.bloquea_por_deuda = f.cleaned_data['bloquea_por_deuda']
                        periodomatricula.ver_cupo_materia = f.cleaned_data['ver_cupo_materia']
                        periodomatricula.ver_horario_materia = f.cleaned_data['ver_horario_materia']
                        periodomatricula.ver_profesor_materia = f.cleaned_data['ver_profesor_materia']
                        periodomatricula.valida_deuda = f.cleaned_data['valida_deuda']
                        periodomatricula.ver_deduda = f.cleaned_data['ver_deduda']
                        periodomatricula.valida_cuotas_rubro = f.cleaned_data['valida_cuotas_rubro']
                        periodomatricula.num_cuotas_rubro = f.cleaned_data['num_cuotas_rubro']
                        periodomatricula.monto_rubro_cuotas = f.cleaned_data['monto_rubro_cuotas']
                        periodomatricula.valida_gratuidad = f.cleaned_data['valida_gratuidad']
                        periodomatricula.porcentaje_perdidad_parcial_gratuidad = f.cleaned_data['porcentaje_perdidad_parcial_gratuidad']
                        periodomatricula.porcentaje_perdidad_total_gratuidad = f.cleaned_data['porcentaje_perdidad_total_gratuidad']
                        periodomatricula.valida_materias_maxima = f.cleaned_data['valida_materias_maxima']
                        periodomatricula.num_materias_maxima = f.cleaned_data['num_materias_maxima']
                        periodomatricula.valida_terminos = f.cleaned_data['valida_terminos']
                        periodomatricula.terminos = f.cleaned_data['terminos']
                        periodomatricula.valida_login = f.cleaned_data['valida_login']
                        periodomatricula.valida_redirect_panel = f.cleaned_data['valida_redirect_panel']
                        periodomatricula.valida_envio_mail = f.cleaned_data['valida_envio_mail']
                        periodomatricula.ver_eliminar_matricula = f.cleaned_data['ver_eliminar_matricula']
                        periodomatricula.puede_agregar_materia = f.cleaned_data['puede_agregar_materia']
                        periodomatricula.seguridad_remove_materia = f.cleaned_data['seguridad_remove_materia']
                        periodomatricula.num_matriculas = f.cleaned_data['num_matriculas']
                        periodomatricula.num_materias_maxima_ultima_matricula = f.cleaned_data['num_materias_maxima_ultima_matricula']
                        periodomatricula.puede_agregar_materia_rubro_pagados = f.cleaned_data['puede_agregar_materia_rubro_pagados']
                        periodomatricula.puede_eliminar_materia_rubro_pagados = f.cleaned_data['puede_eliminar_materia_rubro_pagados']
                        periodomatricula.puede_agregar_materia_rubro_diferidos = f.cleaned_data['puede_agregar_materia_rubro_diferidos']
                        periodomatricula.puede_eliminar_materia_rubro_diferidos = f.cleaned_data['puede_eliminar_materia_rubro_diferidos']
                        periodomatricula.valida_proceos_matricula_especial = f.cleaned_data['valida_proceos_matricula_especial']
                        periodomatricula.proceso_matricula_especial = f.cleaned_data['proceso_matricula_especial']
                        periodomatricula.valida_uso_carnet = f.cleaned_data['valida_uso_carnet']
                        periodomatricula.configuracion_carnet = f.cleaned_data['configuracion_carnet']
                        periodomatricula.valida_configuracion_ultima_matricula = f.cleaned_data['valida_configuracion_ultima_matricula']
                        periodomatricula.configuracion_ultima_matricula = f.cleaned_data['configuracion_ultima_matricula']
                        periodomatricula.fecha_vencimiento_rubro = f.cleaned_data['fecha_vencimiento_rubro']
                        periodomatricula.valida_rubro_acta_compromiso = f.cleaned_data['valida_rubro_acta_compromiso']
                        periodomatricula.mostrar_terminos_examenes = f.cleaned_data['mostrar_terminos_examenes']
                        periodomatricula.terminos_examenes = f.cleaned_data['terminos_examenes']
                        periodomatricula.save(request)
                        if 'tiporubross' in request.POST:
                            tiporubross = json.loads(request.POST['tiporubross'])
                            if tiporubross:
                                tiporubross = [int(x) for x in tiporubross]
                                tiporubros_aux = periodomatricula.tiporubro.all()
                                for t in tiporubros_aux:
                                    if not t.id in tiporubross:
                                        periodomatricula.tiporubro.remove(t)
                                        t.save()
                                for tipo in TipoOtroRubro.objects.filter(pk__in=tiporubross):
                                    periodomatricula.tiporubro.add(tipo)
                            else:
                                for t in periodomatricula.tiporubro.all():
                                    periodomatricula.tiporubro.remove(t)
                                    t.save()
                        if 'coordinacioness' in request.POST:
                            coordinacioness = json.loads(request.POST['coordinacioness'])
                            if coordinacioness:
                                coordinacioness = [int(x) for x in coordinacioness]
                                coordinacion_aux = periodomatricula.coordinacion.all()
                                for c in coordinacion_aux:
                                    if not c.id in coordinacioness:
                                        periodomatricula.coordinacion.remove(c)
                                        c.save()
                                for coordinacion in Coordinacion.objects.filter(pk__in=coordinacioness):
                                    periodomatricula.coordinacion.add(coordinacion)
                            else:
                                for c in periodomatricula.coordinacion.all():
                                    periodomatricula.coordinacion.remove(c)
                                    c.save()
                        if 'cronograma' in request.POST:
                            cronogramas = json.loads(request.POST['cronograma'])
                            if cronogramas:
                                cids = []
                                for cronograma in cronogramas:
                                    if not CronogramaCoordinacion.objects.filter(pk=cronograma['id']).exists():
                                        cc = CronogramaCoordinacion(coordinacion_id=cronograma['coordinacion_id'],
                                                                    fechainicio=convertir_fecha_invertida(cronograma['fechainicio']),
                                                                    fechafin=convertir_fecha_invertida(cronograma['fechafin']),
                                                                    activo=cronograma['activo'],
                                                                    )
                                        cc.save(request)
                                    else:
                                        cc = CronogramaCoordinacion.objects.get(pk=cronograma['id'])
                                        cc.coordinacion_id = cronograma['coordinacion_id']
                                        cc.fechainicio = convertir_fecha_invertida(cronograma['fechainicio'])
                                        cc.fechafin = convertir_fecha_invertida(cronograma['fechafin'])
                                        cc.activo = cronograma['activo']
                                        cc.save(request)
                                    cids.append(cc.id)
                                cronogramas_aux = periodomatricula.cronograma_coordinaciones()
                                for c in cronogramas_aux:
                                    if not c.id in cids:
                                        periodomatricula.cronograma.remove(c)
                                        c.save()

                                for cro in CronogramaCoordinacion.objects.filter(pk__in=cids):
                                    periodomatricula.cronograma.add(cro)
                            else:
                                cronogramas = periodomatricula.cronograma_coordinaciones()
                                cronogramas_aux = CronogramaCoordinacion.objects.filter(pk__in=periodomatricula.cronograma_coordinaciones())
                                for c in cronogramas:
                                    periodomatricula.cronograma.remove(c)
                                    c.save()
                                for c in cronogramas_aux:
                                    c.delete()

                        if 'fechas' in request.POST:
                            fechas = json.loads(request.POST['fechas'])
                            if fechas:
                                fids = []
                                fechas_aux = periodomatricula.fecha_cuotas_rubro()
                                for fc in fechas:
                                    if not FechaCuotaRubro.objects.filter(pk=fc['id']).exists():
                                        eFechaCuotaRubro = FechaCuotaRubro(periodo=periodomatricula,
                                                                           cuota=fc['cuota'],
                                                                           fecha=convertir_fecha_invertida(fc['fecha']),
                                                                           )
                                        eFechaCuotaRubro.save(request)
                                        log(u'Adiciono fecha de rubro académico matricula: %s' % eFechaCuotaRubro, request, "add")
                                    else:
                                        eFechaCuotaRubro = FechaCuotaRubro.objects.get(pk=fc['id'])
                                        eFechaCuotaRubro.cuota = fc['cuota']
                                        eFechaCuotaRubro.fecha = convertir_fecha_invertida(fc['fecha'])
                                        eFechaCuotaRubro.save(request)
                                        log(u'Edito fecha de rubro académico matricula: %s' % eFechaCuotaRubro, request, "edit")
                                    fids.append(eFechaCuotaRubro.id)

                                for fc in fechas_aux:
                                    if not fc.id in fids:
                                        log(u'Elimino fecha de rubro académico matricula: %s' % fc, request, "del")
                                        fc.delete()
                            else:
                                fechas_aux = periodomatricula.fecha_cuotas_rubro()
                                for fc in fechas_aux:
                                    log(u'Elimino fecha de rubro académico matricula: %s' % fc, request, "del")
                                    fc.delete()
                        log(u'Edito periodo académico matricula: %s' % periodomatricula, request, "edit")
                    else:
                        periodomatricula = PeriodoMatricula(periodo=ePeriodo,
                                                            activo=f.cleaned_data['activo'],
                                                            tipo=f.cleaned_data['tipo'],
                                                            valida_coordinacion=f.cleaned_data['valida_coordinacion'],
                                                            valida_cronograma=f.cleaned_data['valida_cronograma'],
                                                            valida_materia_carrera=f.cleaned_data['valida_materia_carrera'],
                                                            valida_seccion=f.cleaned_data['valida_seccion'],
                                                            valida_cupo_materia=f.cleaned_data['valida_cupo_materia'],
                                                            valida_horario_materia=f.cleaned_data['valida_horario_materia'],
                                                            valida_conflicto_horario=f.cleaned_data['valida_conflicto_horario'],
                                                            bloquea_por_deuda=f.cleaned_data['bloquea_por_deuda'],
                                                            ver_cupo_materia=f.cleaned_data['ver_cupo_materia'],
                                                            ver_horario_materia=f.cleaned_data['ver_horario_materia'],
                                                            ver_profesor_materia=f.cleaned_data['ver_profesor_materia'],
                                                            valida_deuda=f.cleaned_data['valida_deuda'],
                                                            ver_deduda=f.cleaned_data['ver_deduda'],
                                                            valida_cuotas_rubro=f.cleaned_data['valida_cuotas_rubro'],
                                                            num_cuotas_rubro=f.cleaned_data['num_cuotas_rubro'],
                                                            monto_rubro_cuotas=f.cleaned_data['monto_rubro_cuotas'],
                                                            valida_gratuidad=f.cleaned_data['valida_gratuidad'],
                                                            porcentaje_perdidad_parcial_gratuidad=f.cleaned_data['porcentaje_perdidad_parcial_gratuidad'],
                                                            porcentaje_perdidad_total_gratuidad=f.cleaned_data['porcentaje_perdidad_total_gratuidad'],
                                                            valida_materias_maxima=f.cleaned_data['valida_materias_maxima'],
                                                            num_materias_maxima=f.cleaned_data['num_materias_maxima'],
                                                            valida_terminos=f.cleaned_data['valida_terminos'],
                                                            terminos=f.cleaned_data['terminos'],
                                                            valida_login=f.cleaned_data['valida_login'],
                                                            valida_redirect_panel=f.cleaned_data['valida_redirect_panel'],
                                                            valida_envio_mail=f.cleaned_data['valida_envio_mail'],
                                                            ver_eliminar_matricula=f.cleaned_data['ver_eliminar_matricula'],
                                                            puede_agregar_materia=f.cleaned_data['puede_agregar_materia'],
                                                            seguridad_remove_materia=f.cleaned_data['seguridad_remove_materia'],
                                                            puede_agregar_materia_rubro_pagados=f.cleaned_data['puede_agregar_materia_rubro_pagados'],
                                                            puede_eliminar_materia_rubro_pagados=f.cleaned_data['puede_eliminar_materia_rubro_pagados'],
                                                            puede_agregar_materia_rubro_diferidos=f.cleaned_data['puede_agregar_materia_rubro_diferidos'],
                                                            puede_eliminar_materia_rubro_diferidos=f.cleaned_data['puede_eliminar_materia_rubro_diferidos'],
                                                            num_matriculas=f.cleaned_data['num_matriculas'],
                                                            num_materias_maxima_ultima_matricula=f.cleaned_data['num_materias_maxima_ultima_matricula'],
                                                            valida_proceos_matricula_especial=f.cleaned_data['valida_proceos_matricula_especial'],
                                                            proceso_matricula_especial=f.cleaned_data['proceso_matricula_especial'],
                                                            valida_uso_carnet=f.cleaned_data['valida_uso_carnet'],
                                                            configuracion_carnet=f.cleaned_data['configuracion_carnet'],
                                                            fecha_vencimiento_rubro=f.cleaned_data['fecha_vencimiento_rubro'],
                                                            valida_rubro_acta_compromiso=f.cleaned_data['valida_rubro_acta_compromiso'],
                                                            mostrar_terminos_examenes=f.cleaned_data['mostrar_terminos_examenes'],
                                                            terminos_examenes=f.cleaned_data['terminos_examenes'],
                                                            )
                        periodomatricula.save(request)
                        if 'coordinacioness' in request.POST:
                            coordinacioness = json.loads(request.POST['coordinacioness'])
                            if coordinacioness:
                                coordinaciones = Coordinacion.objects.filter(pk__in=coordinacioness)
                                for c in coordinaciones:
                                    periodomatricula.coordinacion.add(c)
                        if 'tiporubross' in request.POST:
                            tiporubross = json.loads(request.POST['tiporubross'])
                            if tiporubross:
                                tiporubros = TipoOtroRubro.objects.filter(pk__in=tiporubross)
                                for tipo in tiporubros:
                                    periodomatricula.tiporubro.add(tipo)
                        if 'cronograma' in request.POST:
                            cronogramas = json.loads(request.POST['cronograma'])
                            if cronogramas:
                                cids = []
                                for cronograma in cronogramas:
                                    if not CronogramaCoordinacion.objects.filter(pk=cronograma['id']).exists():
                                        cc = CronogramaCoordinacion(coordinacion_id=int(cronograma['coordinacion_id']),
                                                                    fechainicio=convertir_fecha_invertida(cronograma['fechainicio']),
                                                                    fechafin=convertir_fecha_invertida(cronograma['fechafin']),
                                                                    activo=cronograma['activo'],
                                                                    )
                                        cc.save(request)
                                    else:
                                        cc = CronogramaCoordinacion.objects.get(pk=cronograma['id'])
                                        cc.coordinacion_id = int(cronograma['coordinacion_id'])
                                        cc.fechainicio = convertir_fecha_invertida(cronograma['fechainicio'])
                                        cc.fechafin = convertir_fecha_invertida(cronograma['fechafin'])
                                        cc.activo = cronograma['activo']
                                        cc.save(request)
                                    cids.append(cc.id)
                                for cro in CronogramaCoordinacion.objects.filter(pk__in=cids):
                                    periodomatricula.cronograma.add(cro)
                        if 'fechas' in request.POST:
                            fechas = json.loads(request.POST['fechas'])
                            if fechas:
                                for fc in fechas:
                                    if not FechaCuotaRubro.objects.filter(pk=fc['id']).exists():
                                        eFechaCuotaRubro = FechaCuotaRubro(periodo=periodomatricula,
                                                                           cuota=fc['cuota'],
                                                                           fecha=convertir_fecha_invertida(fc['fecha']),
                                                                           )
                                        eFechaCuotaRubro.save(request)
                                        log(u'Adiciono fecha de rubro académico matricula: %s' % eFechaCuotaRubro, request, "add")
                                    else:
                                        eFechaCuotaRubro = FechaCuotaRubro.objects.get(pk=fc['id'])
                                        eFechaCuotaRubro.cuota = fc['cuota']
                                        eFechaCuotaRubro.fecha = convertir_fecha_invertida(fc['fecha'])
                                        eFechaCuotaRubro.save(request)
                                        log(u'Edito fecha de rubro académico matricula: %s' % eFechaCuotaRubro, request, "edit")
                        log(u'Adiciono periodo académico matricula: %s' % periodomatricula, request, "add")
                    periodomatricula_json = None
                    if periodomatricula:
                        # periodomatricula_json = serializers.serialize("json", periodomatricula, fields=("id", "activo", "lastName"))
                        periodomatricula_json = json.loads(serialize("json", [periodomatricula]))
                return JsonResponse({"result": "ok", "mensaje": u"Se guardo correctamente la configuración de la matriculación", 'periodomatricula_json': periodomatricula_json})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'saveBloqueoHorarios':
            try:
                if not Nivel.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"No se encontro datos del nivel")
                nivel = Nivel.objects.get(pk=request.POST['id'])
                extension = nivel.extension()
                if not 'value' in request.POST:
                    raise NameError(u"No se encontro datos que procesar")
                extension.visible = True if 'value' in request.POST and request.POST['value'] == 'y' else False
                extension.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'saveBloqueoProfesor':
            try:
                if not Nivel.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"No se encontro datos del nivel")
                nivel = Nivel.objects.get(pk=request.POST['id'])
                extension = nivel.extension()
                if not 'value' in request.POST:
                    raise NameError(u"No se encontro datos que procesar")
                extension.modificardocente = True if 'value' in request.POST and request.POST['value'] == 'y' else False
                extension.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'saveBloqueoCupos':
            try:
                if not Nivel.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"No se encontro datos del nivel")
                nivel = Nivel.objects.get(pk=request.POST['id'])
                extension = nivel.extension()
                if not 'value' in request.POST:
                    raise NameError(u"No se encontro datos que procesar")
                extension.puedematricular = True if 'value' in request.POST and request.POST['value'] == 'y' else False
                extension.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'saveFechasNivel':
            try:
                if not Nivel.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"No se encontro datos del nivel")
                nivel = Nivel.objects.get(pk=request.POST['id'])
                if not 'value' in request.POST or not request.POST['value']:
                    raise NameError(u"No se encontro datos que procesar")
                if not 'field' in request.POST or not request.POST['field']:
                    raise NameError(u"No se encontro campo que procesar")
                field = request.POST['field']
                value = convertir_fecha(request.POST['value'])

                if field == 'fechainicioagregacion':
                    if not nivel.periodo.inicio:
                        raise NameError(u"Fecha inicio del periodo académico no encontrada para validar.")
                    # if value < nivel.periodo.inicio:
                    #     raise NameError(u"Fecha inicio de agregación no puede ser manor a la fecha inicio del periodo académico.")
                    nivel.fechainicioagregacion = value

                if field == 'fechatopematricula':
                    if not nivel.fechainicioagregacion:
                        raise NameError(u"Fecha inicio de agregación no encontrada para validar.")
                    if value < nivel.fechainicioagregacion:
                        raise NameError(u"Fecha ordinaria de matrícula no puede ser menor a la fecha inicio de agregación.")
                    nivel.fechatopematricula = value

                if field == 'fechatopematriculaex':
                    if not nivel.fechatopematricula:
                        raise NameError(u"Fecha ordinaria no encontrada para validar.")
                    if value < nivel.fechatopematricula:
                        raise NameError(u"Fecha extraordinaria de matricula no puede ser menor a la fecha ordinaria.")
                    nivel.fechatopematriculaex = value

                if field == 'fechatopematriculaes':
                    if not nivel.fechatopematriculaex:
                        raise NameError(u"Fecha extraordinaria no encontrada para validar.")
                    if value < nivel.fechatopematriculaex:
                        raise NameError(u"Fecha especial de matricula no puede ser menor a la fecha extraordinaria.")
                    if not nivel.fin:
                        raise NameError(u"Fecha fin del nivel no encontrada para validar.")
                    if value > nivel.fin:
                        raise NameError(u"Fecha especial de matricula no puede ser mayor a la fecha fin del nivel.")
                    nivel.fechatopematriculaes = value

                if field == 'fechafinagregacion':
                    if not nivel.fechatopematriculaex:
                        raise NameError(u"Fecha extraordinaria no encontrada para validar.")
                    if value < nivel.fechatopematriculaex:
                        raise NameError(u"Fecha fin de agregación no puede ser menor a la fecha extraordinaria.")
                    if value > nivel.fin:
                        raise NameError(u"Fecha fin de agregación no puede ser mayor a la fecha fin del nivel.")
                    nivel.fechafinagregacion = value

                if field == 'fechafinquitar':
                    if not nivel.fechatopematriculaes:
                        raise NameError(u"Fecha especial no encontrada para validar.")
                    if not nivel.fechafinagregacion:
                        raise NameError(u"Fecha fin de agregación no encontrada para validar.")
                    if value < nivel.fechatopematriculaes:
                        raise NameError(u"Fecha fin de retiro no puede ser menor a la fecha especial.")
                    if value < nivel.fechafinagregacion:
                        raise NameError(u"Fecha fin de retiro no puede ser menor a la fecha fin de agregación")
                    if value > nivel.fin:
                        raise NameError(u"Fecha fin de retiro no puede ser mayor a la fecha fin del nivel.")
                    nivel.fechafinquitar = value

                nivel.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'savePeriodoFinanciero':
            try:
                id = int(request.POST['id']) if 'id' in request.POST and request.POST['id'] and int(request.POST['id']) != 0 else None
                f = PeriodoFinancieroForm(request.POST)
                typeForm = 'edit' if id else 'view'
                if not f.is_valid():
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                if typeForm == 'edit':
                    puede_realizar_accion(request, 'bd.puede_modificar_periodo_academico_finanzas')
                    if not Periodo.objects.filter(pk=id).exists():
                        raise NameError(u"No existe formulario a editar")
                    ePeriodo = Periodo.objects.get(pk=id)
                    ePeriodo.porcentaje_gratuidad = f.cleaned_data['porcentaje_gratuidad']
                    ePeriodo.valor_maximo = f.cleaned_data['valor_maximo']
                    ePeriodo.save(request)
                    log(u'Edito periodo lectivo: %s' % ePeriodo, request, "edit")
                    if 'grupos' in request.POST:
                        grupos = json.loads(request.POST['grupos'])
                        if grupos:
                            # grupos = [int(x) for x in grupos]
                            grupos_ids = [int(x['id']) for x in grupos]
                            grupos_aux = ePeriodo.periodogruposocioeconomico_set.filter(status=True)
                            for gse in grupos_aux:
                                if not gse.id in grupos_ids:
                                    log(f'Elimino grupo socioeconomico ({gse.__str__()}) del periodo ({ePeriodo.__str__()})',request, "del")
                                    gse.delete()
                            for gse in grupos:
                                if PeriodoGrupoSocioEconomico.objects.values("id").filter(pk=int(gse['id']), gruposocioeconomico_id=int(gse['gruposocioeconomico_id'])).exists():
                                    grupo = PeriodoGrupoSocioEconomico.objects.get(pk=int(gse['id']), gruposocioeconomico_id=int(gse['gruposocioeconomico_id']))
                                    grupo.valor = Decimal(gse['valor']).quantize(Decimal('.01'))
                                    grupo.save(request)
                                    log(f'Edito grupo socioeconomico ({gse.__str__()}) del periodo ({ePeriodo.__str__()})', request, "edit")
                                else:
                                    grupo = PeriodoGrupoSocioEconomico(gruposocioeconomico_id=int(gse['gruposocioeconomico_id']),
                                                                       valor=Decimal(gse['valor']).quantize(Decimal('.01')),
                                                                       periodo=ePeriodo)
                                    grupo.save(request)
                                    log(f'Adiciono grupo socioeconomico ({gse.__str__()}) del periodo ({ePeriodo.__str__()})', request, "add")
                        else:
                            for gse in ePeriodo.periodogruposocioeconomico_set.filter(status=True):
                                log(f'Elimino grupo socioeconomico ({gse.__str__()}) del periodo ({ePeriodo.__str__()})',request, "del")
                                gse.delete()
                return JsonResponse({"result": "ok", "mensaje": u"Se guardo correctamente."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'savePeriodoAcademia':
            try:
                id = int(request.POST['id']) if 'id' in request.POST and request.POST['id'] and int(request.POST['id']) != 0 else None
                f = PeriodoAcademiaForm(request.POST)
                typeForm = 'edit' if id else 'view'
                if not f.is_valid():
                    # [(k, v[0]) for k, v in f.errors.items()]
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                if typeForm == 'edit':
                    puede_realizar_accion(request, 'bd.puede_modificar_periodo_academico_academia')
                    if not Periodo.objects.filter(pk=id).exists():
                        raise NameError(u"No existe formulario a editar")
                    ePeriodo = Periodo.objects.get(pk=id)
                    if PeriodoAcademia.objects.filter(periodo=ePeriodo).exists():
                        periodoacademia = PeriodoAcademia.objects.get(periodo=ePeriodo)
                        periodoacademia.fecha_limite_horario_tutoria = f.cleaned_data['fecha_limite_horario_tutoria']
                        periodoacademia.version_cumplimiento_recurso = f.cleaned_data['version_cumplimiento_recurso']
                        periodoacademia.cierra_materia = f.cleaned_data['cierra_materia']
                        periodo_ids = ""
                        if 'periodos_relacionadoss' in request.POST:
                            periodos_relacionadoss = json.loads(request.POST['periodos_relacionadoss'])
                            if periodos_relacionadoss:
                                ids = []
                                periodoss = Periodo.objects.filter(pk__in=periodos_relacionadoss)
                                for p in periodoss:
                                    ids.append(str(p.id))
                                if ids:
                                    periodo_ids = ",".join(ids)
                        if periodo_ids:
                            periodoacademia.periodos_relacionados = periodo_ids
                        periodoacademia.tipo_modalidad = f.cleaned_data['tipo_modalidad']
                        periodoacademia.utiliza_asistencia_ws = f.cleaned_data['utiliza_asistencia_ws']
                        periodoacademia.utiliza_asistencia_redis = f.cleaned_data['utiliza_asistencia_redis']
                        periodoacademia.puede_cerrar_clase = f.cleaned_data['puede_cerrar_clase']
                        periodoacademia.puede_eliminar_clase = f.cleaned_data['puede_eliminar_clase']
                        periodoacademia.puede_editar_contenido_academico_clase = f.cleaned_data['puede_editar_contenido_academico_clase']
                        periodoacademia.puede_cambiar_asistencia_clase = f.cleaned_data['puede_cambiar_asistencia_clase']
                        periodoacademia.num_dias_cambiar_asistencia_clase = f.cleaned_data['num_dias_cambiar_asistencia_clase']
                        periodoacademia.valida_asistencia_pago = f.cleaned_data['valida_asistencia_pago']
                        periodoacademia.valida_clases_horario_estricto = f.cleaned_data['valida_clases_horario_estricto']
                        periodoacademia.min_clases_apertura_antes_pro = f.cleaned_data['min_clases_apertura_antes_pro'] if f.cleaned_data['valida_clases_horario_estricto'] else None
                        periodoacademia.min_clases_apertura_despues_pro = f.cleaned_data['min_clases_apertura_despues_pro'] if f.cleaned_data['valida_clases_horario_estricto'] else None
                        periodoacademia.min_clases_apertura_antes_alu = f.cleaned_data['min_clases_apertura_antes_alu'] if f.cleaned_data['valida_clases_horario_estricto'] else None
                        periodoacademia.min_clases_apertura_despues_alu = f.cleaned_data['min_clases_apertura_despues_alu'] if f.cleaned_data['valida_clases_horario_estricto'] else None
                        periodoacademia.puede_solicitar_clase_diferido_pro = f.cleaned_data['puede_solicitar_clase_diferido_pro']
                        periodoacademia.proceso_solicitud_clase_diferido_pro = f.cleaned_data['proceso_solicitud_clase_diferido_pro'] if f.cleaned_data['puede_solicitar_clase_diferido_pro'] else None
                        periodoacademia.valida_asistencia_in_home = f.cleaned_data['valida_asistencia_in_home']
                        periodoacademia.save(request)
                        log(u'Edito periodo académico academia: %s' % periodoacademia, request, "edit")
                    else:
                        periodo_ids = ""
                        if 'periodos_relacionadoss' in request.POST:
                            periodos_relacionadoss = json.loads(request.POST['periodos_relacionadoss'])
                            if periodos_relacionadoss:
                                ids = []
                                periodoss = Periodo.objects.filter(pk__in=periodos_relacionadoss)
                                for p in periodoss:
                                    ids.append(str(p.id))
                                if ids:
                                    periodo_ids = ",".join(ids)
                        periodoacademia = PeriodoAcademia(periodo=ePeriodo,
                                                          fecha_limite_horario_tutoria=f.cleaned_data['fecha_limite_horario_tutoria'],
                                                          version_cumplimiento_recurso=f.cleaned_data['version_cumplimiento_recurso'],
                                                          cierra_materia=f.cleaned_data['cierra_materia'],
                                                          periodos_relacionados=periodo_ids if periodo_ids else None,
                                                          tipo_modalidad=f.cleaned_data['tipo_modalidad'],
                                                          utiliza_asistencia_ws=f.cleaned_data['utiliza_asistencia_ws'],
                                                          utiliza_asistencia_redis=f.cleaned_data['utiliza_asistencia_redis'],
                                                          puede_cerrar_clase=f.cleaned_data['puede_cerrar_clase'],
                                                          puede_eliminar_clase=f.cleaned_data['puede_eliminar_clase'],
                                                          puede_editar_contenido_academico_clase=f.cleaned_data['puede_editar_contenido_academico_clase'],
                                                          puede_cambiar_asistencia_clase=f.cleaned_data['puede_cambiar_asistencia_clase'],
                                                          num_dias_cambiar_asistencia_clase=f.cleaned_data['num_dias_cambiar_asistencia_clase'],
                                                          valida_asistencia_pago=f.cleaned_data['valida_asistencia_pago'],
                                                          valida_clases_horario_estricto=f.cleaned_data['valida_clases_horario_estricto'],
                                                          min_clases_apertura_antes_pro=f.cleaned_data['min_clases_apertura_antes_pro'] if f.cleaned_data['valida_clases_horario_estricto'] else None,
                                                          min_clases_apertura_despues_pro=f.cleaned_data['min_clases_apertura_despues_pro'] if f.cleaned_data['valida_clases_horario_estricto'] else None,
                                                          min_clases_apertura_antes_alu=f.cleaned_data['min_clases_apertura_antes_alu'] if f.cleaned_data['valida_clases_horario_estricto'] else None,
                                                          min_clases_apertura_despues_alu=f.cleaned_data['min_clases_apertura_despues_alu'] if f.cleaned_data['valida_clases_horario_estricto'] else None,
                                                          puede_solicitar_clase_diferido_pro=f.cleaned_data['puede_solicitar_clase_diferido_pro'],
                                                          proceso_solicitud_clase_diferido_pro=f.cleaned_data['proceso_solicitud_clase_diferido_pro'] if f.cleaned_data['puede_solicitar_clase_diferido_pro'] and f.cleaned_data['proceso_solicitud_clase_diferido_pro'] else None,
                                                          valida_asistencia_in_home=f.cleaned_data['valida_asistencia_in_home'],
                                                          )
                        log(u'Adiciono periodo académico academia: %s' % periodoacademia, request, "add")
                        periodoacademia.save(request)
                return JsonResponse({"result": "ok", "mensaje": u"Se guardo correctamente la configuración de lo académico"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'savePeriodoCrontab':
            try:
                id = int(request.POST['id']) if 'id' in request.POST and request.POST['id'] and int(request.POST['id']) != 0 else None
                f = PeriodoCrontabForm(request.POST)
                typeForm = 'edit' if id else 'view'
                if not f.is_valid():
                    # [(k, v[0]) for k, v in f.errors.items()]
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                if typeForm == 'edit':
                    puede_realizar_accion(request, 'bd.puede_modificar_periodo_crontab')
                    if not Periodo.objects.filter(pk=id).exists():
                        raise NameError(u"No existe formulario a editar")
                    ePeriodo = Periodo.objects.get(pk=id)
                    if PeriodoCrontab.objects.filter(periodo=ePeriodo).exists():
                        periodocrontab = PeriodoCrontab.objects.get(periodo=ePeriodo)
                        periodocrontab.type = f.cleaned_data['type']
                        periodocrontab.is_activo = f.cleaned_data['is_activo']
                        periodocrontab.upgrade_level_inscription = f.cleaned_data['upgrade_level_inscription']
                        periodocrontab.upgrade_level_enrollment = f.cleaned_data['upgrade_level_enrollment']
                        periodocrontab.upgrade_state_enrollment = f.cleaned_data['upgrade_state_enrollment']
                        periodocrontab.create_lesson_previa = f.cleaned_data['create_lesson_previa']
                        periodocrontab.delete_lesson_previa = f.cleaned_data['delete_lesson_previa']
                        periodocrontab.notify_student_activities = f.cleaned_data['notify_student_activities']
                        periodocrontab.bloqueo_state_enrollment = f.cleaned_data['bloqueo_state_enrollment']
                        periodocrontab.save(request)
                        log(u'Edito periodo crontab: %s' % periodocrontab, request, "edit")
                    else:
                        periodocrontab = PeriodoCrontab(periodo=ePeriodo,
                                                        type=f.cleaned_data['type'],
                                                        is_activo=f.cleaned_data['is_activo'],
                                                        upgrade_level_inscription=f.cleaned_data['upgrade_level_inscription'],
                                                        upgrade_level_enrollment=f.cleaned_data['upgrade_level_enrollment'],
                                                        upgrade_state_enrollment=f.cleaned_data['upgrade_state_enrollment'],
                                                        create_lesson_previa=f.cleaned_data['create_lesson_previa'],
                                                        delete_lesson_previa=f.cleaned_data['delete_lesson_previa'],
                                                        notify_student_activities=f.cleaned_data['notify_student_activities'],
                                                        bloqueo_state_enrollment=f.cleaned_data['bloqueo_state_enrollment'],
                                                        )
                        periodocrontab.save(request)
                        log(u'Edito periodo crontab: %s' % periodocrontab, request, "add")

                return JsonResponse({"result": "ok", "mensaje": u"Se guardo correctamente la configuración del crontab"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'saveCronogramaCoordinacion':
            try:
                idcc = int(request.POST['idcc']) if 'idcc' in request.POST and request.POST['idcc'] and int(request.POST['idcc']) != 0 else None
                idpm = int(request.POST['idpm']) if 'idpm' in request.POST and request.POST['idpm'] and int(request.POST['idpm']) != 0 else None
                # typeForm = request.POST['typeForm'] if 'typeForm' in request.POST and request.POST['typeForm'] and str(request.POST['typeForm']) in ['new', 'edit', 'view'] else None
                # if typeForm is None:
                #     raise NameError(u"No se encontro el tipo de formulario")
                if idpm is None:
                    raise NameError(u"No se encontro parametro de periodo a planificar")
                if not PeriodoMatricula.objects.values("id").filter(pk=idpm).exists():
                    raise NameError(u"No existe formulario")
                ePeriodoMatricula = PeriodoMatricula.objects.get(pk=idpm)
                typeForm = 'edit' if idcc else 'new'
                f = MatriculaCronogramaCoordinacionForm(request.POST)
                if not f.is_valid():
                    # [(k, v[0]) for k, v in f.errors.items()]
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                puede_realizar_accion(request, 'bd.puede_modificar_periodo_academico_matriculacion')
                if typeForm == 'edit':
                    if not CronogramaCoordinacion.objects.filter(pk=idcc).exists():
                        raise NameError(u"No existe formulario a editar")
                    eCronogramaCoordinacion = CronogramaCoordinacion.objects.get(pk=idcc)
                    if not eCronogramaCoordinacion.id in ePeriodoMatricula.cronograma_coordinaciones().values_list("id", flat=True):
                        raise NameError(u"No existe formulario a editar")
                    eCronogramaCoordinacion.fechainicio = f.cleaned_data['fechainicio']
                    eCronogramaCoordinacion.horainicio = f.cleaned_data['horainicio']
                    eCronogramaCoordinacion.fechafin = f.cleaned_data['fechafin']
                    eCronogramaCoordinacion.horafin = f.cleaned_data['horafin']
                    eCronogramaCoordinacion.activo = f.cleaned_data['activo']
                    eCronogramaCoordinacion.save(request)
                    log(u'Edito cronograma de coordinacion de matricula: %s' % eCronogramaCoordinacion, request, "edit")
                else:
                    if f.cleaned_data['coordinacion'].id in ePeriodoMatricula.cronograma_coordinaciones().values_list("coordinacion__id", flat=True):
                        raise NameError(u"Coordinación ya existe.")
                    eCronogramaCoordinacion = CronogramaCoordinacion(coordinacion=f.cleaned_data['coordinacion'],
                                                                     fechainicio=f.cleaned_data['fechainicio'],
                                                                     horainicio=f.cleaned_data['horainicio'],
                                                                     fechafin=f.cleaned_data['fechafin'],
                                                                     horafin=f.cleaned_data['horafin'],
                                                                     activo=f.cleaned_data['activo'])
                    eCronogramaCoordinacion.save(request)
                    ePeriodoMatricula.cronograma.add(eCronogramaCoordinacion.id)
                    log(u'Adiciono cronograma de coordinacion de matricula: %s' % eCronogramaCoordinacion, request, "add")
                return JsonResponse({"result": "ok", "mensaje": u"Se guardo correctamente cronograma de coordinación"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'deleteCronogramaCoordinacion':
            try:
                puede_realizar_accion(request, 'bd.puede_modificar_periodo_academico_matriculacion')
                idcc = int(request.POST['idcc']) if 'idcc' in request.POST and request.POST['idcc'] and int(request.POST['idcc']) != 0 else None
                idpm = int(request.POST['idpm']) if 'idpm' in request.POST and request.POST['idpm'] and int(request.POST['idpm']) != 0 else None
                if idpm is None:
                    raise NameError(u"No se encontro parametro de periodo")
                if idcc is None:
                    raise NameError(u"No se encontro parametro de coordinación")
                if not PeriodoMatricula.objects.values("id").filter(pk=idpm).exists():
                    raise NameError(u"No existe periodo")
                if not CronogramaCoordinacion.objects.values("id").filter(pk=idcc).exists():
                    raise NameError(u"No existe cronograma de coordinación")

                ePeriodoMatricula = PeriodoMatricula.objects.get(pk=idpm)
                eCronogramaCoordinacion = CronogramaCoordinacion.objects.get(pk=idcc)
                if not ePeriodoMatricula.tiene_cronograma_coordinaciones():
                    raise NameError(U"No existe cronograma de coordinación a eliminar")
                if not eCronogramaCoordinacion.id in ePeriodoMatricula.cronograma_coordinaciones().values_list("id", flat=True):
                    raise NameError(U"No existe coordinación planificada a eliminar")
                ePeriodoMatricula.cronograma.remove(eCronogramaCoordinacion.id)
                eCronogramaCoordinacion.delete()
                log(u'Elimino cronograma de coordinacion de matricula: %s' % eCronogramaCoordinacion, request, "del")
                return JsonResponse({"result": "ok", "mensaje": u"Se elimino correctamente cronograma de coordinación"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'saveCronogramaCarrera':
            try:
                idc = int(request.POST['idc']) if 'idc' in request.POST and request.POST['idc'] and int(request.POST['idc']) != 0 else None
                idcc = int(request.POST['idcc']) if 'idcc' in request.POST and request.POST['idcc'] and int(request.POST['idcc']) != 0 else None
                if idc is None:
                    raise NameError(u"No se encontro parametro de coordinacion a planificar")
                if not CronogramaCoordinacion.objects.values("id").filter(pk=idc).exists():
                    raise NameError(u"No existe coordinación")
                eCronogramaCoordinacion = CronogramaCoordinacion.objects.get(pk=idc)
                typeForm = 'edit' if idcc else 'new'
                f = MatriculaCronogramaCarreraForm(request.POST)
                if not f.is_valid():
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                puede_realizar_accion(request, 'bd.puede_modificar_periodo_academico_matriculacion')
                if typeForm == 'edit':
                    if not CronogramaCarrera.objects.filter(pk=idcc).exists():
                        raise NameError(u"No existe formulario a editar")
                    eCronogramaCarrera = CronogramaCarrera.objects.get(pk=idcc)
                    if not eCronogramaCarrera.id in eCronogramaCoordinacion.cronogramacarreras().values_list("id", flat=True):
                        raise NameError(u"No existe formulario a editar")
                    eCronogramaCarrera.fechainicio = f.cleaned_data['fechainicio']
                    eCronogramaCarrera.horainicio = f.cleaned_data['horainicio']
                    eCronogramaCarrera.fechafin = f.cleaned_data['fechafin']
                    eCronogramaCarrera.horafin = f.cleaned_data['horafin']
                    eCronogramaCarrera.activo = f.cleaned_data['activo']
                    eCronogramaCarrera.save(request)
                    log(u'Edito cronograma de carrera de matricula: %s' % eCronogramaCarrera, request, "edit")
                else:
                    # if f.cleaned_data['carrera'].id in eCronogramaCoordinacion.cronogramacarreras().values_list("carrera__id", flat=True):
                    #     raise NameError(u"Carrera ya existe.")
                    eCronogramaCarrera = CronogramaCarrera(carrera=f.cleaned_data['carrera'],
                                                           fechainicio=f.cleaned_data['fechainicio'],
                                                           horainicio=f.cleaned_data['horainicio'],
                                                           fechafin=f.cleaned_data['fechafin'],
                                                           horafin=f.cleaned_data['horafin'],
                                                           activo=f.cleaned_data['activo'])
                    eCronogramaCarrera.save(request)
                    eCronogramaCoordinacion.cronogramacarrera.add(eCronogramaCarrera.id)
                    log(u'Adiciono cronograma de carrera de matricula: %s' % eCronogramaCarrera, request, "add")
                niveless = request.POST.get('niveless', None)
                if not niveless:
                    raise NameError(u"Seleccione los niveles")
                sesioness = request.POST.get('sesioness', None)
                if not sesioness:
                    raise NameError(u"Seleccione las jornadas")
                if niveless:
                    niveless = json.loads(niveless)
                    if niveless:
                        niveless = [int(x) for x in niveless]
                        niveless_aux = eCronogramaCarrera.niveles()
                        for n in niveless_aux:
                            if not n.id in niveless:
                                eCronogramaCarrera.nivel.remove(n)
                                # n.save()
                        for nivel in NivelMalla.objects.filter(pk__in=niveless):
                            eCronogramaCarrera.nivel.add(nivel)
                    else:
                        for n in eCronogramaCarrera.niveles():
                            eCronogramaCarrera.nivel.remove(n)
                            # n.save()
                if sesioness:
                    sesioness = json.loads(sesioness)
                    if sesioness:
                        sesioness = [int(x) for x in sesioness]
                        sesioness_aux = eCronogramaCarrera.sesiones()
                        for n in sesioness_aux:
                            if not n.id in sesioness:
                                eCronogramaCarrera.sesion.remove(n)
                                # n.save()
                        for sesion in Sesion.objects.filter(pk__in=sesioness):
                            eCronogramaCarrera.sesion.add(sesion)
                    else:
                        for s in eCronogramaCarrera.sesiones():
                            eCronogramaCarrera.sesion.remove(s)
                            # n.save()
                fechahorainicio = eCronogramaCoordinacion.cronogramacarreras().values('fechainicio', 'horainicio').distinct().order_by('fechainicio', 'horainicio')[0]
                fechahorafin = eCronogramaCoordinacion.cronogramacarreras().values('fechafin', 'horafin').distinct().order_by('-fechafin', '-horafin')[0]
                eCronogramaCoordinacion.fechainicio = fechahorainicio.get('fechainicio')
                eCronogramaCoordinacion.horainicio = fechahorainicio.get('horainicio')
                eCronogramaCoordinacion.fechafin = fechahorafin.get('fechafin')
                eCronogramaCoordinacion.horafin = fechahorafin.get('horafin')
                eCronogramaCoordinacion.save(request)

                return JsonResponse({"result": "ok", "mensaje": u"Se guardo correctamente cronograma de carrera"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'deleteCronogramaCarrera':
            try:
                puede_realizar_accion(request, 'bd.puede_modificar_periodo_academico_matriculacion')
                idc = int(request.POST['idc']) if 'idc' in request.POST and request.POST['idc'] and int(request.POST['idc']) != 0 else None
                idcc = int(request.POST['idcc']) if 'idcc' in request.POST and request.POST['idcc'] and int(request.POST['idcc']) != 0 else None
                if idc is None:
                    raise NameError(u"No se encontro parametro de cronograma de coordinación")
                if idcc is None:
                    raise NameError(u"No se encontro parametro de cronograma de carrera")
                if not CronogramaCoordinacion.objects.values("id").filter(pk=idc).exists():
                    raise NameError(u"No existe cronograma de coordinación")
                if not CronogramaCarrera.objects.values("id").filter(pk=idcc).exists():
                    raise NameError(u"No existe cronograma de carrera")

                eCronogramaCoordinacion = CronogramaCoordinacion.objects.get(pk=idc)
                eCronogramaCarrera = CronogramaCarrera.objects.get(pk=idcc)
                if not eCronogramaCoordinacion.tiene_cronogramacarreras():
                    raise NameError(U"No existe cronograma de carrera a eliminar")
                if not eCronogramaCarrera.id in eCronogramaCoordinacion.cronogramacarreras().values_list("id", flat=True):
                    raise NameError(U"No existe carrera planificada a eliminar")
                eCronogramaCoordinacion.cronogramacarrera.remove(eCronogramaCarrera.id)
                eCronogramaCarrera.delete()
                log(u'Elimino cronograma de carrera de matricula: %s' % eCronogramaCarrera, request, "del")
                if eCronogramaCoordinacion.tiene_cronogramacarreras():
                    fechahorainicio = eCronogramaCoordinacion.cronogramacarreras().values('fechainicio', 'horainicio').distinct().order_by('fechainicio', 'horainicio')[0]
                    fechahorafin = eCronogramaCoordinacion.cronogramacarreras().values('fechafin', 'horafin').distinct().order_by('-fechafin', '-horafin')[0]
                    eCronogramaCoordinacion.fechainicio = fechahorainicio.get('fechainicio')
                    eCronogramaCoordinacion.horainicio = fechahorainicio.get('horainicio')
                    eCronogramaCoordinacion.fechafin = fechahorafin.get('fechafin')
                    eCronogramaCoordinacion.horafin = fechahorafin.get('horafin')
                    eCronogramaCoordinacion.save(request)
                return JsonResponse({"result": "ok", "mensaje": u"Se elimino correctamente cronograma de carrera"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'savePeriodoMalla':
            try:
                id = int(request.POST['id']) if 'id' in request.POST and request.POST['id'] and int(request.POST['id']) != 0 else None
                idp = int(request.POST['idp']) if 'idp' in request.POST and request.POST['idp'] and int(request.POST['idp']) != 0 else None
                ePeriodo = Periodo.objects.filter(pk=idp).first()
                ePeriodoMalla = PeriodoMalla.objects.filter(pk=id).first()
                f = PeriodoMallaForm(request.POST)
                typeForm = 'edit' if id else 'new'
                if not f.is_valid():
                    for k, v in f.errors.items():
                        raise NameError(f'{k} : {v[0]}')
                if ePeriodo is None:
                    raise NameError(u"No se encontro datos del periodo")
                if typeForm == 'edit':
                    ePeriodoMalla.tipocalculo = f.cleaned_data['tipocalculo']
                    ePeriodoMalla.configuracion = f.cleaned_data['configuracion']
                    ePeriodoMalla.vct = f.cleaned_data['vct']
                    ePeriodoMalla.save(request)
                    log(u'Edito Periodo Malla de finanzas: %s' % ePeriodoMalla, request, "edit")
                    if 'detalle' in request.POST:
                        detalle = json.loads(request.POST['detalle'])
                        if detalle:
                            iddetex = []
                            for item in detalle:
                                eDetallePeriodoMalla = ePeriodoMalla.detalleperiodomalla_set.filter(status=True, gruposocioeconomico_id=int(item['gruposocioeconomico_id'])).first()
                                if eDetallePeriodoMalla is None:
                                    eDetallePeriodoMalla = DetallePeriodoMalla(
                                        periodomalla=ePeriodoMalla,
                                        gruposocioeconomico_id=int(item['gruposocioeconomico_id']),
                                        valor=float(item['valor'])
                                    )
                                    eDetallePeriodoMalla.save(request)
                                    log(u'Adiciono Detalle Periodo Malla de finanzas: %s' % eDetallePeriodoMalla, request, "add")
                                else:
                                    eDetallePeriodoMalla.valor = float(item['valor'])
                                    eDetallePeriodoMalla.save(request)
                                    log(u'Edito Detalle Periodo Malla de finanzas: %s' % eDetallePeriodoMalla, request, "edit")
                                iddetex.append(eDetallePeriodoMalla.id)

                            eDetallesPeriodoMallaDelete = ePeriodoMalla.detalleperiodomalla_set.exclude(id__in=iddetex)
                            for eDetallePeriodo in eDetallesPeriodoMallaDelete:
                                eDetallePeriodo.delete()
                                log(u'Elimino Detalle Periodo Malla de finanzas: %s' % eDetallePeriodo, request, "del")

                else:
                    #Nuevo Periodo Malla
                    ePeriodoMalla = PeriodoMalla(
                        periodo=ePeriodo,
                        tipocalculo=f.cleaned_data['tipocalculo'],
                        malla=f.cleaned_data['malla'],
                        configuracion=f.cleaned_data['configuracion'],
                        vct=f.cleaned_data['vct']
                    )
                    ePeriodoMalla.save(request)
                    print(ePeriodoMalla)
                    log(u'Adiciono Periodo Malla de finanzas: %s' % ePeriodoMalla, request, "add")
                    if 'detalle' in request.POST:
                        detalle = json.loads(request.POST['detalle'])
                        if detalle:
                            for item in detalle:
                                eDetallePeriodoMalla = DetallePeriodoMalla(
                                    periodomalla=ePeriodoMalla,
                                    gruposocioeconomico_id=int(item['gruposocioeconomico_id']),
                                    valor=float(item['valor'])
                                )
                                eDetallePeriodoMalla.save(request)
                                log(u'Adiciono Detalle Periodo Malla de finanzas: %s' % eDetallePeriodoMalla, request, "add")
                                print('------------>', eDetallePeriodoMalla)
                return JsonResponse({"result": "ok", 'idp': idp})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'saveCostoOptimo':
            try:
                if not 'idp' in request.POST:
                    raise NameError(u"No se encontro parametro de periodo")
                if not 'rangominimo' in request.POST:
                    raise NameError(u"No se encontro valor del rango mínimo")
                if not 'rangomaximo' in request.POST:
                    raise NameError(u"No se encontro valor del rango máximo")
                if not 'costooptimo' in request.POST:
                    raise NameError(u"No se encontro valor del costo óptimo")
                idp = int(request.POST['idp'])
                if not Malla.objects.values("id").filter(pk=request.POST['malla']).exists():
                    raise NameError(u"No se ecnontro la malla")
                if not Periodo.objects.values("id").filter(pk=idp).exists():
                    raise NameError(u"No se ecnontro el periodo")
                rangominimo = request.POST['rangominimo']
                rangominimo = null_to_decimal((Decimal(rangominimo).quantize(Decimal('.01'))))
                rangomaximo = request.POST['rangomaximo']
                rangomaximo = null_to_decimal((Decimal(rangomaximo).quantize(Decimal('.01'))))
                costooptimo = request.POST['costooptimo']
                costooptimo = null_to_decimal((Decimal(costooptimo).quantize(Decimal('.01'))))

                eMalla = Malla.objects.get(pk=request.POST['malla'])
                ePeriodo = Periodo.objects.get(pk=idp)
                eCostoOptimoMalla = eMalla.carga_costooptimomalla(ePeriodo)
                if eCostoOptimoMalla:
                    eCostoOptimoMalla.rangominimo = rangominimo
                    eCostoOptimoMalla.rangomaximo = rangomaximo
                    eCostoOptimoMalla.costooptimo = costooptimo
                    eCostoOptimoMalla.save(request)
                    log(u'Edito configuración de calculo por nivel de cobro de matrícula: %s' % eCostoOptimoMalla, request, "edit")

                else:
                    eCostoOptimoMalla = CostoOptimoMalla(periodo=ePeriodo,
                                                         malla=eMalla,
                                                         rangominimo=rangominimo,
                                                         rangomaximo=rangomaximo,
                                                         costooptimo=costooptimo,
                                                         )
                    eCostoOptimoMalla.save(request)
                    log(u'Adiciono configuración de calculo por nivel de cobro de matrícula: %s' % eCostoOptimoMalla, request, "add")
                eCostoOptimoMalla.crear_editar_calculo_niveles(request)
                return JsonResponse({"result": True, 'aData': {'costomatricula': eCostoOptimoMalla.costomatricula,
                                                               'nombremalla': '%s' % eMalla.nombre_corto(),
                                                               'horastotales': '%.2f' % eMalla.suma_horas_validacion_itinerario(),
                                                               'creditostotales': '%.2f' % eMalla.suma_creditos_validacion_itinerario(),
                                                               'niveles': '%s' % eMalla.cantidad_niveles(),
                                                               'costomatricula': '%.2f' % eMalla.carga_costooptimomalla(ePeriodo).costomatricula if eMalla.carga_costooptimomalla(ePeriodo) else '0.00'
                                                               }})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'ejecutarextraerdatos':
            try:
                if not 'idp' in request.POST:
                    raise NameError(u"No se encontro parametro de periodo")
                if not 'idop' in request.POST:
                    raise NameError(u"No se encontro parametro de periodo a extraer")
                idp = int(request.POST['idp'])
                idotrop = int(request.POST['idop'])
                if not Periodo.objects.values("id").filter(pk=idp).exists():
                    raise NameError(u"No se ecnontro el periodo")
                if not Periodo.objects.values("id").filter(pk=idotrop).exists():
                    raise NameError(u"No se ecnontro el periodo a extraer")

                ePeriodo = Periodo.objects.get(pk=idp)
                eOtroPeriodo = Periodo.objects.get(pk=idotrop)
                if ePeriodo.tipocalculo == 6 and eOtroPeriodo.tipocalculo == 6:

                    eOtroMaterias = Materia.objects.filter(status=True, nivel__periodo=eOtroPeriodo)
                    eOtroCostoOptimoMallas = CostoOptimoMalla.objects.filter(periodo=eOtroPeriodo, status=True)
                    eOtroMallas = Malla.objects.filter(pk__in=eOtroMaterias.values_list('asignaturamalla__malla__id', flat=True).union(eOtroCostoOptimoMallas.values_list("malla__id", flat=True))).distinct().order_by('carrera__nombre')

                    eMaterias = Materia.objects.filter(status=True, nivel__periodo=ePeriodo)
                    eCostoOptimoMallas = CostoOptimoMalla.objects.filter(periodo=ePeriodo, status=True)
                    eMallas = Malla.objects.filter(pk__in=eMaterias.values_list('asignaturamalla__malla__id', flat=True).union(eCostoOptimoMallas.values_list("malla__id", flat=True))).distinct().order_by('carrera__nombre')

                    for malla in eMallas:
                        if malla.id in eOtroMallas.values_list('id', flat=True):
                            eOtroCostoOptimoMalla = malla.carga_costooptimomalla(eOtroPeriodo)
                            if eOtroCostoOptimoMalla:
                                eCostoOptimoMalla = malla.carga_costooptimomalla(ePeriodo)
                                if eCostoOptimoMalla:
                                    eCostoOptimoMalla.rangominimo = eOtroCostoOptimoMalla.rangominimo
                                    eCostoOptimoMalla.rangomaximo = eOtroCostoOptimoMalla.rangomaximo
                                    eCostoOptimoMalla.costooptimo = eOtroCostoOptimoMalla.costooptimo
                                    eCostoOptimoMalla.save(request)
                                else:
                                    eCostoOptimoMalla = CostoOptimoMalla(periodo=ePeriodo,
                                                                         malla=malla,
                                                                         rangominimo=eOtroCostoOptimoMalla.rangominimo,
                                                                         rangomaximo=eOtroCostoOptimoMalla.rangomaximo,
                                                                         costooptimo=eOtroCostoOptimoMalla.costooptimo,
                                                                         )
                                    eCostoOptimoMalla.save(request)
                                eCostoOptimoMalla.crear_editar_calculo_niveles(request)
                    log(u'Ejecutó extración de datos financieros del periodo %s al periodo %s.' % (eOtroPeriodo, ePeriodo), request, "edit")
                return JsonResponse({"result": "ok", "mensaje": u"Proceso ejecutado con éxito."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al extraer datos del periodo académico. %s" % ex.__str__()})

        elif action == 'saveCostoOptimoMalla':
            try:
                if not 'id' in request.POST:
                    raise NameError(u"No se encontro parametro de malla")
                if not 'idp' in request.POST:
                    raise NameError(u"No se encontro parametro de periodo")
                if not 'rangominimo' in request.POST:
                    raise NameError(u"No se encontro valor del rango mínimo")
                if not 'rangomaximo' in request.POST:
                    raise NameError(u"No se encontro valor del rango máximo")
                if not 'costooptimo' in request.POST:
                    raise NameError(u"No se encontro valor del costo óptimo")
                id = int(request.POST['id'])
                idp = int(request.POST['idp'])
                if not Malla.objects.values("id").filter(pk=id).exists():
                    raise NameError(u"No se ecnontro la malla")
                if not Periodo.objects.values("id").filter(pk=idp).exists():
                    raise NameError(u"No se ecnontro el periodo")
                rangominimo = request.POST['rangominimo']
                rangominimo = null_to_decimal((Decimal(rangominimo).quantize(Decimal('.01'))))
                rangomaximo = request.POST['rangomaximo']
                rangomaximo = null_to_decimal((Decimal(rangomaximo).quantize(Decimal('.01'))))
                costooptimo = request.POST['costooptimo']
                costooptimo = null_to_decimal((Decimal(costooptimo).quantize(Decimal('.01'))))
                eMalla = Malla.objects.get(pk=id)
                ePeriodo = Periodo.objects.get(pk=idp)
                eCostoOptimoMalla = eMalla.carga_costooptimomalla(ePeriodo)
                if eCostoOptimoMalla:
                    eCostoOptimoMalla.rangominimo = rangominimo
                    eCostoOptimoMalla.rangomaximo = rangomaximo
                    eCostoOptimoMalla.costooptimo = costooptimo
                    eCostoOptimoMalla.save(request)
                    log(u'Edito configuración de calculo por nivel de cobro de matrícula: %s' % eCostoOptimoMalla, request, "edit")

                else:
                    eCostoOptimoMalla = CostoOptimoMalla(periodo=ePeriodo,
                                                         malla=eMalla,
                                                         rangominimo=rangominimo,
                                                         rangomaximo=rangomaximo,
                                                         costooptimo=costooptimo,
                                                         )
                    eCostoOptimoMalla.save(request)
                    log(u'Adiciono configuración de calculo por nivel de cobro de matrícula: %s' % eCostoOptimoMalla, request, "add")
                eCostoOptimoMalla.crear_editar_calculo_niveles(request)
                return JsonResponse({"result": True, 'aData': {'costomatricula': eCostoOptimoMalla.costomatricula}})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'loadFormAcademicPeriod':
                try:
                    typeForm = request.GET['typeForm'] if 'typeForm' in request.GET and request.GET['typeForm'] and str(request.GET['typeForm']) in ['new', 'edit', 'view'] else None
                    if typeForm is None:
                        raise NameError(u"No se encontro el tipo de formulario")
                    f = PeriodoForm()
                    f.set_delete()
                    ePeriodo = None
                    id = 0
                    data['sedes'] = Sede.objects.all()
                    if typeForm in ['edit', 'view']:
                        id = int(request.GET['id']) if 'id' in request.GET and request.GET['id'] and int(request.GET['id']) != 0 else None
                        if not Periodo.objects.filter(pk=id).exists():
                            raise NameError(u"No existe formulario a editar")
                        ePeriodo = Periodo.objects.get(pk=id)
                        f.set_initial(ePeriodo, None)
                        if typeForm == 'view':
                            f.view()
                        if typeForm == 'edit':
                            puede_realizar_accion(request, 'bd.puede_modificar_periodo_academico')
                        data['ePeriodo'] = ePeriodo
                    else:
                        puede_realizar_accion(request, 'bd.puede_agregar_periodo_academico')
                        f.set_initial(ePeriodo)
                        data['ePeriodo'] = ePeriodoActual = request.session['periodo']
                    data['form'] = f
                    data['frmName'] = "frmAcademicPeriod"
                    data['id'] = id
                    template = get_template("adm_sistemas/academic_period/frm.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            elif action == 'loadFormGroups':
                try:
                    typeForm = request.GET['typeForm'] if 'typeForm' in request.GET and request.GET['typeForm'] and str(request.GET['typeForm']) in ['edit', 'view'] else None
                    if typeForm is None:
                        raise NameError(u"No se encontro el tipo de formulario")
                    f = PeriodoForm()
                    f.set_delete_grupos()
                    ePeriodo = None
                    id = 0
                    data['sedes'] = Sede.objects.all()
                    if typeForm in ['edit', 'view']:
                        id = int(request.GET['id']) if 'id' in request.GET and request.GET['id'] and int(request.GET['id']) != 0 else None
                        if not Periodo.objects.filter(pk=id).exists():
                            raise NameError(u"No existe formulario a editar")
                        ePeriodo = Periodo.objects.get(pk=id)
                        f.set_initial(ePeriodo, 'grupos')
                        if typeForm == 'view':
                            f.view()
                        if typeForm == 'edit':
                            puede_realizar_accion(request, 'bd.puede_modificar_periodo_academico_grupo')
                        data['ePeriodo'] = ePeriodo
                    data['form'] = f
                    data['frmName'] = "frmAcademicPeriodGroups"
                    data['id'] = id
                    template = get_template("adm_sistemas/academic_period/frm_groups.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            elif action == 'loadFormMatriculacion':
                try:
                    typeForm = request.GET['typeForm'] if 'typeForm' in request.GET and request.GET['typeForm'] and str(request.GET['typeForm']) in ['edit', 'view'] else None
                    if typeForm is None:
                        raise NameError(u"No se encontro el tipo de formulario")
                    f = PeriodoMatriculaForm()
                    ePeriodo = None
                    ePeriodoMatricula = None
                    cronograma = []
                    fechas = []
                    id = 0
                    if typeForm in ['edit', 'view']:
                        id = int(request.GET['id']) if 'id' in request.GET and request.GET['id'] and int(request.GET['id']) != 0 else None
                        if not Periodo.objects.filter(pk=id).exists():
                            raise NameError(u"No existe formulario a editar")
                        ePeriodo = Periodo.objects.get(pk=id)
                        f.set_initial(ePeriodo)
                        if PeriodoMatricula.objects.filter(periodo=ePeriodo).exists():
                            ePeriodoMatricula = PeriodoMatricula.objects.get(periodo=ePeriodo)
                            for c in ePeriodoMatricula.cronograma_coordinaciones():
                                cronograma.append({"id": c.id,
                                                   "coordinacion_id": c.coordinacion.id,
                                                   "coordinacion": c.coordinacion.__str__(),
                                                   "fechainicio": c.fechainicio.__str__(),
                                                   "fechafin": c.fechafin.__str__(),
                                                   "activo": c.activo,
                                                   })
                            for fc in ePeriodoMatricula.fecha_cuotas_rubro():
                                fechas.append({"id": fc.id,
                                               "cuota": fc.cuota,
                                               "fecha": fc.fecha.__str__()})

                        if typeForm == 'view':
                            f.view()
                        if typeForm == 'edit':
                            puede_realizar_accion(request, 'bd.puede_modificar_periodo_academico_matriculacion')
                    data['ePeriodo'] = ePeriodo
                    data['ePeriodoMatricula'] = ePeriodoMatricula
                    data['form'] = f
                    data['frmName'] = "frmAcademicPeriodMatriculacion"
                    data['id'] = id
                    template = get_template("adm_sistemas/academic_period/frm_matriculacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content, 'cronograma': cronograma, 'fecha': fechas})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            elif action == 'loadFormNiveles':
                try:
                    typeForm = request.GET['typeForm'] if 'typeForm' in request.GET and request.GET['typeForm'] and str(request.GET['typeForm']) in ['edit', 'view'] else None
                    if typeForm is None:
                        raise NameError(u"No se encontro el tipo de formulario")
                    ePeriodo = None
                    eNiveles = None
                    id = 0
                    if typeForm in ['edit', 'view']:
                        id = int(request.GET['id']) if 'id' in request.GET and request.GET['id'] and int(request.GET['id']) != 0 else None
                        if not Periodo.objects.filter(pk=id).exists():
                            raise NameError(u"No existe formulario a editar")
                        ePeriodo = Periodo.objects.get(pk=id)
                        eNiveles = Nivel.objects.filter(periodo=ePeriodo)
                        if typeForm == 'view':
                            # f.view()
                            pass
                        if typeForm == 'edit':
                            puede_realizar_accion(request, 'bd.puede_modificar_periodo_academico_niveles')
                    data['title'] = u'Niveles académicos'
                    data['ePeriodo'] = ePeriodo
                    data['typeForm'] = typeForm
                    data['eNiveles'] = eNiveles
                    data['coordinaciones'] = persona.mis_coordinaciones()
                    data['frmName'] = "frmAcademicPeriodMatriculacion"
                    data['id'] = id
                    template = get_template("adm_sistemas/academic_period/frm_niveles.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            elif action == 'loadFormFananciero':
                try:
                    typeForm = request.GET['typeForm'] if 'typeForm' in request.GET and request.GET['typeForm'] and str(request.GET['typeForm']) in ['edit', 'view'] else None
                    if typeForm is None:
                        raise NameError(u"No se encontro el tipo de formulario")
                    ePeriodo = None
                    grupos_socioeconomico = []
                    periodos_mallas = []
                    f = PeriodoFinancieroForm()
                    template_html_name = 'frm_finanzas.html'
                    id = 0
                    if typeForm in ['edit', 'view']:
                        id = int(request.GET['id']) if 'id' in request.GET and request.GET['id'] and int(request.GET['id']) != 0 else None
                        if not Periodo.objects.values("id").filter(pk=id).exists():
                            raise NameError(u"No existe formulario a editar")
                        ePeriodo = Periodo.objects.get(pk=id)
                        if ePeriodo.tipocalculo == 1:
                            f = PeriodoFinancieroForm()
                            template_html_name = 'frm_finanzas.html'
                        elif ePeriodo.tipocalculo in (2, 3, 4, 5):
                            f = PeriodoFinancieroForm2()
                            template_html_name = 'frm_finanzas2.html'
                        elif ePeriodo.tipocalculo == 6:
                            eMaterias = Materia.objects.filter(status=True, nivel__periodo=ePeriodo)
                            eCostoOptimoMallas = CostoOptimoMalla.objects.filter(periodo=ePeriodo, status=True)
                            eMallas = Malla.objects.filter(pk__in=eMaterias.values_list('asignaturamalla__malla__id', flat=True).union(eCostoOptimoMallas.values_list("malla__id", flat=True))).distinct().order_by('carrera__nombre')
                            data['eMallas'] = eMallas
                            data['listaMallas'] = [{'id': x.id, 'malla': u'%s' % x} for x in Malla.objects.filter(status=True).exclude(pk__in=eMallas.values_list('id', flat=True))]
                            template_html_name = 'frm_finanzas3.html'
                            data['listaotrosperiodos'] = [{'id': x.id, 'periodo': u'%s' % x} for x in Periodo.objects.filter(status=True, tipocalculo=6).exclude(pk=id)]
                        else:
                            raise NameError(u"No existe configuración de tipo de calculo de matrícula")
                        f.set_initial(ePeriodo)
                        if typeForm == 'view':
                            f.view()
                        if typeForm == 'edit':
                            puede_realizar_accion(request, 'bd.puede_modificar_periodo_academico_finanzas')
                        if ePeriodo.tipocalculo == 1:
                            for gse in ePeriodo.periodogruposocioeconomico_set.filter(status=True):
                                grupos_socioeconomico.append({"id": gse.id,
                                                              "gruposocioeconomico": gse.gruposocioeconomico.__str__(),
                                                              "gruposocioeconomico_id": gse.gruposocioeconomico.id,
                                                              "valor": gse.valor})
                        elif ePeriodo.tipocalculo in (2, 3, 4, 5):
                            for pmalla in ePeriodo.periodomalla_set.filter(status=True):
                                periodos_mallas.append({"id": pmalla.id,
                                                        "malla": pmalla.malla.__str__(),
                                                        "tipocalculo": pmalla.get_tipocalculo_display(),
                                                        #"configuracion": pmalla.valor,
                                                        "vct": pmalla.vct})
                        elif ePeriodo.tipocalculo == 6:
                            data['eGrupoSocioEconomicos'] = eGrupoSocioEconomicos = GrupoSocioEconomico.objects.filter(status=True)
                    data['ePeriodo'] = ePeriodo
                    data['form'] = f
                    data['frmName'] = "frmAcademicPeriodFinanciero"
                    data['id'] = id
                    data['typeForm'] = typeForm
                    template = get_template(f"adm_sistemas/academic_period/{template_html_name}")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content, 'grupos': grupos_socioeconomico, 'mallas': periodos_mallas})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            elif action == 'loadDetalleCostoNiveles':
                try:
                    id = int(request.GET['id']) if 'id' in request.GET and request.GET['id'] and int(request.GET['id']) != 0 else None
                    idp = int(request.GET['idp']) if 'idp' in request.GET and request.GET['idp'] and int(request.GET['idp']) != 0 else None
                    if not Malla.objects.values("id").filter(pk=id).exists():
                        raise NameError(u"No existe parametro de malla")
                    if not Periodo.objects.values("id").filter(pk=idp).exists():
                        raise NameError(u"No existe parametro de periodo")
                    eMalla = Malla.objects.get(pk=id)
                    ePeriodo = Periodo.objects.get(pk=idp)
                    if not CostoOptimoMalla.objects.values("id").filter(malla=eMalla, periodo=ePeriodo).exists():
                        raise NameError(u"No existe configuración de malla en periodo")
                    eCostoOptimoMalla = CostoOptimoMalla.objects.get(malla=eMalla, periodo=ePeriodo)
                    data['ePeriodo'] = ePeriodo
                    data['eMalla'] = eMalla
                    data['eCostoOptimoMalla'] = eCostoOptimoMalla
                    data['eGrupoSocioEconomicos'] = eGrupoSocioEconomicos = GrupoSocioEconomico.objects.filter(status=True)
                    template = get_template(f"adm_sistemas/academic_period/detallecostoniveles.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            elif action == 'loadFormAcademia':
                try:
                    typeForm = request.GET['typeForm'] if 'typeForm' in request.GET and request.GET['typeForm'] and str(request.GET['typeForm']) in ['edit', 'view'] else None
                    if typeForm is None:
                        raise NameError(u"No se encontro el tipo de formulario")
                    f = PeriodoAcademiaForm()
                    ePeriodo = None
                    ePeriodoAcademia = None
                    id = 0
                    if typeForm in ['edit', 'view']:
                        id = int(request.GET['id']) if 'id' in request.GET and request.GET['id'] and int(request.GET['id']) != 0 else None
                        if not Periodo.objects.filter(pk=id).exists():
                            raise NameError(u"No existe formulario a editar")
                        ePeriodo = Periodo.objects.get(pk=id)
                        f.set_initial(ePeriodo)
                        if PeriodoAcademia.objects.filter(periodo=ePeriodo).exists():
                            ePeriodoAcademia = PeriodoAcademia.objects.get(periodo=ePeriodo)
                        if typeForm == 'view':
                            f.view()
                        if typeForm == 'edit':
                            puede_realizar_accion(request, 'bd.puede_modificar_periodo_academico_academia')
                    data['ePeriodo'] = ePeriodo
                    data['ePeriodoAcademia'] = ePeriodoAcademia
                    data['form'] = f
                    data['frmName'] = "frmAcademicPeriodAcademia"
                    data['id'] = id
                    template = get_template("adm_sistemas/academic_period/frm_academia.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            elif action == 'loadFormPeriodoMalla':
                try:
                    typeForm = request.GET['typeForm'] if 'typeForm' in request.GET and request.GET['typeForm'] and str(request.GET['typeForm']) in ['new', 'edit', 'view'] else None
                    idp = int(request.GET['idp']) if 'idp' in request.GET and request.GET['idp'] and int(request.GET['idp']) != 0 else None
                    if typeForm is None:
                        raise NameError(u"No se encontro el tipo de formulario")
                    f = PeriodoMallaForm()
                    ePeriodo = Periodo.objects.filter(pk=idp).first()
                    ePeriodoMalla = None
                    mallas_exclude = list(PeriodoMalla.objects.filter(periodo=ePeriodo).values_list('malla_id', flat=True).distinct())
                    id = 0
                    grupos = []
                    if typeForm in ['edit', 'view']:
                        id = int(request.GET['id']) if 'id' in request.GET and request.GET['id'] and int(request.GET['id']) != 0 else None
                        if ePeriodo is None:
                            raise NameError(u"No existe formulario a editar")
                        ePeriodoMalla = PeriodoMalla.objects.filter(pk=id).first()
                        if ePeriodoMalla is None:
                            raise NameError(u"No existe formulario a editar")
                        f.set_initial(ePeriodoMalla)
                        if typeForm == 'view':
                            f.view()
                        if typeForm == 'edit':
                            puede_realizar_accion(request, 'bd.puede_modificar_periodo_crontab')
                            f.deshabilitar_campo('malla')
                        eDetallesPeriodoMalla = ePeriodoMalla.detalleperiodomalla_set.filter(status=True)
                        for eDetallePeriodo in eDetallesPeriodoMalla:
                            grupo = model_to_dict(eDetallePeriodo)
                            grupo['periodomalla_id'] = eDetallePeriodo.periodomalla.id
                            grupo['periodomalla'] = eDetallePeriodo.periodomalla.__str__()
                            grupo['gruposocioeconomico_id'] = eDetallePeriodo.gruposocioeconomico.id
                            grupo['gruposocioeconomico'] = eDetallePeriodo.gruposocioeconomico.__str__()
                            grupos.append(grupo)
                    else:
                        #pregrado
                        mallas_clasificacion = Malla.objects.filter(carrera__coordinacion__id__in=[7, 9, 10])
                        if ePeriodo.clasificacion == 2:
                            #posgrado
                            mallas_clasificacion = Malla.objects.exclude(carrera__coordinacion__id__in=[7, 10])
                        elif ePeriodo.clasificacion == 3:
                            #admision
                            mallas_clasificacion = Malla.objects.exclude(carrera__coordinacion__id=9)

                        mallas_clasificacion = list(mallas_clasificacion.values_list('id', flat=True).distinct())
                        mallas_exclude.extend(mallas_clasificacion)
                        mallas_exclude.extend([353, 22, 32]) #EXCLUYENDO MALLAS DE INGLES Y COMPUTACIÓN

                        f.fields['malla'].queryset = Malla.objects.filter(status=True).exclude(id__in=mallas_exclude)

                    data['ePeriodo'] = ePeriodo
                    data['ePeriodoMalla'] = ePeriodoMalla
                    data['form'] = f
                    data['frmName'] = "frmPeriodoMalla"
                    data['id'] = id
                    template = get_template("adm_sistemas/academic_period/frm_periodo_malla.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content, 'grupos':grupos})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            elif action == 'loadFormCrontab':
                try:
                    typeForm = request.GET['typeForm'] if 'typeForm' in request.GET and request.GET['typeForm'] and str(request.GET['typeForm']) in ['edit', 'view'] else None
                    if typeForm is None:
                        raise NameError(u"No se encontro el tipo de formulario")
                    f = PeriodoCrontabForm()
                    ePeriodo = None
                    ePeriodoCrontab = None
                    id = 0
                    if typeForm in ['edit', 'view']:
                        id = int(request.GET['id']) if 'id' in request.GET and request.GET['id'] and int(request.GET['id']) != 0 else None
                        if not Periodo.objects.filter(pk=id).exists():
                            raise NameError(u"No existe formulario a editar")
                        ePeriodo = Periodo.objects.get(pk=id)
                        f.set_initial(ePeriodo)
                        if PeriodoCrontab.objects.filter(periodo=ePeriodo).exists():
                            ePeriodoCrontab = PeriodoCrontab.objects.get(periodo=ePeriodo)
                        if typeForm == 'view':
                            f.view()
                        if typeForm == 'edit':
                            puede_realizar_accion(request, 'bd.puede_modificar_periodo_crontab')
                    data['ePeriodo'] = ePeriodo
                    data['ePeriodoCrontab'] = ePeriodoCrontab
                    data['form'] = f
                    data['frmName'] = "frmCrontabPeriod"
                    data['id'] = id
                    template = get_template("adm_sistemas/academic_period/frm_crontab.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            elif action == 'loadRegistrationSchedule':
                try:
                    typeForm = request.GET['typeForm'] if 'typeForm' in request.GET and request.GET['typeForm'] and str(request.GET['typeForm']) in ['edit', 'view'] else None
                    id = int(request.GET['id']) if 'id' in request.GET and request.GET['id'] else None
                    if typeForm is None:
                        raise NameError(u"No se encontro el tipo de formulario")
                    if id is None:
                        raise NameError(u"No se encontro parametro de periodo a planificar")
                    if not Periodo.objects.values("id").filter(pk=id).exists():
                        raise NameError(u"No existe periodo a planificar")
                    ePeriodo = Periodo.objects.get(pk=id)
                    if not PeriodoMatricula.objects.values("id").filter(periodo=ePeriodo).exists():
                        raise NameError(u"No existe periodo de matriculación a planificar, favor configure la matriculación")
                    ePeriodoMatricula = PeriodoMatricula.objects.get(periodo=ePeriodo)
                    if not ePeriodoMatricula.valida_cronograma:
                        raise NameError(u"Periodo de matriculación no permite validación de cronograma")
                    if typeForm in ['edit', 'view']:
                        if typeForm == 'view':
                            # f.view()
                            pass
                        if typeForm == 'edit':
                            pass
                    data['title'] = u'Cronograma de matriculación'
                    data['ePeriodo'] = ePeriodo
                    data['ePeriodoMatricula'] = ePeriodoMatricula
                    data['typeForm'] = typeForm
                    template = get_template("adm_sistemas/academic_period/view_cronograma_matriculacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            elif action == 'loadFormCronogramaCoordinacion':
                try:
                    typeForm = request.GET['typeForm'] if 'typeForm' in request.GET and request.GET['typeForm'] and str(request.GET['typeForm']) in ['new', 'edit', 'view'] else None
                    idpm = int(request.GET['idpm']) if 'idpm' in request.GET and request.GET['idpm'] and int(request.GET['idpm']) != 0 else None
                    idcc = int(request.GET['idcc']) if 'idcc' in request.GET and request.GET['idcc'] and int(request.GET['idcc']) != 0 else None
                    if typeForm is None:
                        raise NameError(u"No se encontro el tipo de formulario")
                    if idpm is None:
                        raise NameError(u"No se encontro parametro de periodo a planificar")
                    if not PeriodoMatricula.objects.values("id").filter(pk=idpm).exists():
                        raise NameError(u"No existe formulario")
                    ePeriodoMatricula = PeriodoMatricula.objects.get(pk=idpm)
                    eCronogramaCoordinacion = None
                    f = MatriculaCronogramaCoordinacionForm()
                    if typeForm in ['edit', 'view']:
                        if idcc is None:
                            raise NameError(u"No se encontro parametro de coordinación a planificar")
                        if not CronogramaCoordinacion.objects.filter(pk=idcc).exists():
                            raise NameError(u"No existe formulario a editar")
                        eCronogramaCoordinacion = CronogramaCoordinacion.objects.get(pk=idcc)
                        f.set_initial(eCronogramaCoordinacion)
                        f.editar(eCronogramaCoordinacion)
                        if typeForm == 'view':
                            f.view()
                        if typeForm == 'edit':
                            puede_realizar_accion(request, 'bd.puede_modificar_periodo_academico_matriculacion')
                    else:
                        puede_realizar_accion(request, 'bd.puede_modificar_periodo_academico_matriculacion')

                    data['ePeriodoMatricula'] = ePeriodoMatricula
                    data['eCronogramaCoordinacion'] = eCronogramaCoordinacion
                    data['typeForm'] = typeForm
                    data['form'] = f
                    data['frmName'] = "frmCronogramaCoordinacion"
                    data['idcc'] = idcc if not idcc is None else 0
                    data['idpm'] = idpm
                    template = get_template("adm_sistemas/academic_period/frm_cronogramacoordinacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            elif action == 'loadFormCronogramaCarrera':
                try:
                    typeForm = request.GET['typeForm'] if 'typeForm' in request.GET and request.GET['typeForm'] and str(request.GET['typeForm']) in ['new', 'edit', 'view'] else None
                    idc = int(request.GET['idc']) if 'idc' in request.GET and request.GET['idc'] and int(request.GET['idc']) != 0 else None
                    idcc = int(request.GET['idcc']) if 'idcc' in request.GET and request.GET['idcc'] and int(request.GET['idcc']) != 0 else None
                    if typeForm is None:
                        raise NameError(u"No se encontro el tipo de formulario")
                    if idc is None:
                        raise NameError(u"No se encontro parametro de coordinación")
                    if not CronogramaCoordinacion.objects.values("id").filter(pk=idc).exists():
                        raise NameError(u"No existe cronograma de coordinación")
                    eCronogramaCoordinacion = CronogramaCoordinacion.objects.get(pk=idc)
                    eCronogramaCarrera = None
                    f = MatriculaCronogramaCarreraForm()
                    if typeForm in ['edit', 'view']:
                        if idcc is None:
                            raise NameError(u"No se encontro parametro de coordinación a planificar")
                        if not CronogramaCarrera.objects.filter(pk=idcc).exists():
                            raise NameError(u"No existe formulario a editar")
                        eCronogramaCarrera = CronogramaCarrera.objects.get(pk=idcc)
                        f.set_initial(eCronogramaCarrera)
                        f.editar(eCronogramaCarrera)
                        if typeForm == 'view':
                            f.view()
                        if typeForm == 'edit':
                            puede_realizar_accion(request, 'bd.puede_modificar_periodo_academico_matriculacion')
                    else:
                        f.adicionar(eCronogramaCoordinacion)
                        puede_realizar_accion(request, 'bd.puede_modificar_periodo_academico_matriculacion')
                    data['eNiveles'] = NivelMalla.objects.filter(status=True)
                    data['eCronogramaCoordinacion'] = eCronogramaCoordinacion
                    data['eCronogramaCarrera'] = eCronogramaCarrera
                    data['typeForm'] = typeForm
                    data['form'] = f
                    data['frmName'] = "frmCronogramaCarrera"
                    data['idcc'] = idcc if not idcc is None else 0
                    data['idc'] = idc
                    template = get_template("adm_sistemas/academic_period/frm_cronogramacarrera.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            return HttpResponseRedirect(request.path)

        else:
            try:
                data['title'] = 'Administración de Periodos Académicos'
                data['tipos_periodos'] = tipos_periodos = TipoPeriodo.objects.all()
                data['coordinaciones'] = Coordinacion.objects.all()
                data['grupos_socioeconomicos'] = GrupoSocioEconomico.objects.filter(status=True)
                return render(request, "adm_sistemas/academic_period/view.html", data)
            except Exception as ex:
                pass
