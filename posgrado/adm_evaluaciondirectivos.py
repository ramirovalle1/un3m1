from sga.commonviews import adduserdata
from django.contrib.auth.decorators import login_required
from django.db import transaction, connections
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.db.models.query_utils import Q
from datetime import datetime
from sga.models import DetalleInstrumentoEvaluacionDirectivoAcreditacion, Periodo, Materia, Carrera, Profesor, \
    CriterioTipoObservacionEvaluacion, Rubrica, ProfesorDistributivoHoras, RubricaPreguntas, RespuestaEvaluacionAcreditacion, \
    Clase, ClaseAsincronica, EvidenciaActividadDetalleDistributivo
from django.template.loader import get_template
from sga.funciones import MiPaginador, log, evaluo_director_2, evaluo_coordinador_2, variable_valor, convertir_fecha
from posgrado.models import DetalleFechasEvalDirMateria, CohorteMaestria, EscuelaPosgrado, RespuestaEvaluacionAcreditacionPosgrado, \
    RespuestaRubricaPosgrado, DetalleRespuestaRubricaPos
from django.shortcuts import render
from typing import Any, Hashable, Iterable, Optional
from sagest.models import Departamento
from datetime import timedelta
def buscar_dicc(it: Iterable[dict], clave: Hashable, valor: Any) -> Optional[dict]:
    for dicc in it:
        if dicc[clave] == valor:
            return dicc
    return None

def dato_evaluado_directivo_periodo(self, periodo, par, materia):
    if RespuestaEvaluacionAcreditacionPosgrado.objects.filter(tipoinstrumento=4, proceso__periodo=periodo, profesor=self, materia=materia,
                                                           evaluador=par).exists():
        return RespuestaEvaluacionAcreditacionPosgrado.objects.filter(tipoinstrumento=4, proceso__periodo=periodo, profesor=self, materia=materia,
                                                           evaluador=par)[0]
    elif RespuestaEvaluacionAcreditacion.objects.filter(tipoinstrumento=4, proceso__periodo=periodo, profesor=self, materia=materia,
                                                           evaluador=par).exists():
        return RespuestaEvaluacionAcreditacion.objects.filter(tipoinstrumento=4, proceso__periodo=periodo, profesor=self, materia=materia,
                                                           evaluador=par)[0]
    else:
        return None

@login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
# @last_access
@transaction.atomic()

def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']
    miscarreras = persona.mis_carreras()
    # data['DOMINIO_DEL_SISTEMA'] = dominio_sistema = dominio_sistema_base(request)

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'evaluarposgrado':
            try:
                profesor = Profesor.objects.get(pk=int(request.POST['idp']))
                materia = None
                materia = Materia.objects.get(pk=int(request.POST['idm']))
                coordinaciondistributivo = ProfesorDistributivoHoras.objects.filter(periodo=materia.nivel.periodo, profesor=profesor, status=True)[0]
                if RespuestaEvaluacionAcreditacionPosgrado.objects.filter(proceso__periodo=periodo, profesor=profesor,
                                                                          evaluador=persona,
                                                                          tipoinstrumento=int(request.POST['tipo']),
                                                                          materia=materia).exists():
                    return JsonResponse({"result": "bad", 'mensaje': u'Evaluación ya existe.'})
                materiarevision = None

                proceso = materia.nivel.periodo.proceso_evaluativo()
                evaluacion = RespuestaEvaluacionAcreditacionPosgrado(proceso=proceso,
                                                                     tipoinstrumento=int(request.POST['tipo']),
                                                                     profesor=profesor,
                                                                     evaluador=persona,
                                                                     fecha=datetime.now(),
                                                                     coordinacion=coordinaciondistributivo.coordinacion,
                                                                     carrera=materia.asignaturamalla.malla.carrera,
                                                                     tipomejoras_id=request.POST['nommejoras'],
                                                                     accionmejoras=request.POST['accionmejoras'],
                                                                     materia=materia if materia is not None else None)
                evaluacion.save(request)
                listarespuesta = []
                for elemento in request.POST['lista'].split(';'):
                    individuales = elemento.split(':')
                    rubricapregunta = RubricaPreguntas.objects.get(pk=int(individuales[0]))
                    rubrica = rubricapregunta.rubrica
                    if not RespuestaRubricaPosgrado.objects.filter(respuestaevaluacion=evaluacion,
                                                                   rubrica=rubrica).exists():
                        respuestarubrica = RespuestaRubricaPosgrado(respuestaevaluacion=evaluacion,
                                                                    rubrica=rubrica,
                                                                    valor=0)
                        respuestarubrica.save(request)
                    else:
                        respuestarubrica = RespuestaRubricaPosgrado.objects.filter(respuestaevaluacion=evaluacion, rubrica=rubrica)[0]
                    listarespuesta.append(respuestarubrica.id)
                    justificacion = individuales[2] if len(individuales) > 2 and individuales[2] is not None else None

                    detalle = DetalleRespuestaRubricaPos(respuestarubrica=respuestarubrica,
                                                         rubricapregunta=rubricapregunta,
                                                         valor=float(individuales[1]),
                                                         justificacion=justificacion)
                    detalle.save(request)
                    respuestarubrica.save()

                if DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.filter(status=True, materia=materia, evaluador=persona, evaluado=profesor).exists():
                    eDeta = DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.filter(status=True, materia=materia, evaluador=persona, evaluado=profesor).first()
                    eDeta.evalua = True
                    eDeta.save(request)
                log(u'Evaluacion del profesor por par o directivo: %s' % profesor, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'listasubmejoras':
            try:
                combomejoras = CriterioTipoObservacionEvaluacion.objects.get(pk=request.POST['id'])
                tipoinstrumento = request.POST['tipoins']
                lista = []
                for detmejoras in combomejoras.tipoobservacionevaluacion_set.filter(tipoinstrumento=tipoinstrumento, tipo=1, status=True, activo=True).order_by('nombre'):
                    lista.append([detmejoras.id, detmejoras.nombre.upper()])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'cargar_cohortes_ofer':
                try:
                    lista = []
                    ePeriodos = Periodo.objects.filter(status=True, tipo_id=3).exclude(nombre__icontains='TITUL').order_by('-id')

                    for ePeriodo in ePeriodos:
                        if not buscar_dicc(lista, 'id', ePeriodo.id):
                            lista.append({'id': ePeriodo.id, 'nombre': ePeriodo.__str__()})
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'selectcarrera':
                try:
                    if 'id' in request.GET:
                        lista = []
                        eCarreras = Carrera.objects.filter(status=True, escuelaposgrado__id=int(request.GET['id']))
                        for eCarrera in eCarreras:
                            lista.append([eCarrera.id, eCarrera.__str__().title()])
                        return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'selectperiodo':
                try:
                    if 'id' in request.GET:
                        lista = []
                        eCohortes = CohorteMaestria.objects.filter(status=True, periodoacademico__isnull=False,
                                                             maestriaadmision__carrera_id=int(request.GET['id']))
                        for eCohorte in eCohortes:
                            lista.append([eCohorte.periodoacademico.id, eCohorte.descripcion.title()])
                        return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'selectparalelo':
                try:
                    if 'id' in request.GET:
                        lista = []
                        eParalelos = Materia.objects.filter(status=True,
                                                            nivel__periodo__id=int(request.GET['id'])).values_list('paralelo', flat=True).order_by('paralelo').distinct()
                        for eParalelo in eParalelos:
                            lista.append([eParalelo, eParalelo])
                        return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'evaluar':
                try:
                    data['title'] = u'Evaluación del profesor'
                    data['profesor'] = profesor = Profesor.objects.get(pk=int(request.GET['id']))
                    data['tipoinstrumento'] = tipo = int(request.GET['t'])

                    materia = None
                    data['materia'] = materia = Materia.objects.get(pk=int(request.GET['idm']))
                    data['ePeriodo'] = ePeriodo = materia.nivel.periodo
                    data['combomejoras'] = CriterioTipoObservacionEvaluacion.objects.filter(tipoobservacionevaluacion__tipoinstrumento=tipo, tipoobservacionevaluacion__tipo=1, tipoobservacionevaluacion__status=True,tipoobservacionevaluacion__activo=True).order_by('nombre').distinct()
                    data['combocontinuas'] = CriterioTipoObservacionEvaluacion.objects.filter(tipoobservacionevaluacion__tipoinstrumento=tipo, tipoobservacionevaluacion__tipo=2, tipoobservacionevaluacion__status=True,tipoobservacionevaluacion__activo=True).order_by('nombre').distinct()
                    estado = True
                    resultados = RespuestaEvaluacionAcreditacionPosgrado.objects.values('evaluador_id').filter(
                        status=True,
                        tipoinstrumento=4,
                        proceso__periodo=ePeriodo,
                        profesor=profesor,
                        materia=materia,
                        respuestarubricaposgrado__rubrica__para_directivo=True).exclude(respuestarubricaposgrado__rubrica__rvigente=True)
                    if resultados.exists():
                        estado = False

                    lista1 = Rubrica.objects.filter(habilitado=True,
                                                    proceso__periodo=ePeriodo,
                                                    para_directivo=True, rvigente=estado).distinct()

                    data['rubricas'] = rubricas = lista1
                    data['tiene_docencia'] = rubricas.filter(tipo_criterio=1).exists()
                    data['tiene_investigacion'] = rubricas.filter(tipo_criterio=2).exists()
                    data['tiene_gestion'] = rubricas.filter(tipo_criterio=3).exists()
                    return render(request,"adm_evaluaciondirectivos/evaluarposgrado.html", data)
                except Exception as ex:
                    pass

            elif action == 'consultar':
                try:
                    data['title'] = u'Consulta de evaluación en el periodo'
                    data['profesor'] = profesor = Profesor.objects.get(pk=int(request.GET['id']))
                    data['persona'] = persona
                    data['tipoinstrumento'] = tipo = int(request.GET['t'])
                    evaluacion = None
                    eMateria = None
                    data['eMateria'] = eMateria = Materia.objects.get(pk=int(request.GET['idm']))
                    data['ePeriodo'] = ePeriodo = eMateria.nivel.periodo
                    estado = True
                    resultados = RespuestaEvaluacionAcreditacionPosgrado.objects.values('evaluador_id').filter(
                        status=True,
                        tipoinstrumento=4,
                        proceso__periodo=ePeriodo,
                        profesor=profesor,
                        materia=eMateria,
                        respuestarubricaposgrado__rubrica__para_directivo=True).exclude(respuestarubricaposgrado__rubrica__rvigente=True)

                    if resultados.exists():
                        estado = False

                    lista1 = Rubrica.objects.filter(habilitado=True,
                                                    proceso__periodo=ePeriodo,
                                                    para_directivo=True, rvigente=estado).distinct()

                    data['rubricas'] = rubricas = lista1
                    data['evaluacion'] = evaluacion = dato_evaluado_directivo_periodo(profesor, ePeriodo, persona, eMateria)
                    data['tiene_docencia'] = rubricas.filter(tipo_criterio=1).exists()
                    data['tiene_investigacion'] = rubricas.filter(tipo_criterio=2).exists()
                    data['tiene_gestion'] = rubricas.filter(tipo_criterio=3).exists()
                    return render(request, "adm_evaluaciondirectivos/consultarposgrado.html", data)
                except Exception as ex:
                    pass

            elif action == 'verdetalleclases':
                try:
                    data['id'] = request.GET['id']
                    eMateria = Materia.objects.get(status=True, pk=int(request.GET['id']))
                    eProfesor = Profesor.objects.get(status=True, pk=int(request.GET['idp']))
                    ePeriodo = eMateria.nivel.periodo
                    idclases = Clase.objects.filter(status=True, materia=eMateria).values_list('id', flat=True)
                    data['eClasesAsincronicas'] = ClaseAsincronica.objects.filter(status=True, clase__id__in=idclases).order_by('id')

                    eDistributivo = ProfesorDistributivoHoras.objects.filter(periodo=ePeriodo, profesor=eProfesor, status=True)
                    tipo = 'FACULTAD'

                    if tipo == 'FACULTAD':
                        if not eDistributivo.exists():
                            mensaje = "No registra actividades de docencia, verifique el periodo."
                            raise NameError('Error')
                    if eDistributivo:
                        eDistributivo = eDistributivo[0]

                    data['eDistributivo'] = eDistributivo
                    template = get_template("adm_evaluaciondirectivos/modal/detallecalses.html")
                    return JsonResponse({"result": "ok", 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'veractividadesdocente':
                try:
                    data['id'] = request.GET['id']
                    eMateria = Materia.objects.get(status=True, pk=int(request.GET['id']))
                    eProfesor = Profesor.objects.get(status=True, pk=int(request.GET['idp']))
                    ePeriodo = eMateria.nivel.periodo

                    tieneevaluacion = 'NO'
                    if eMateria.respuestaevaluacionacreditacion_set.filter(tipoinstrumento=1, status=True).exists():
                        tieneevaluacion = 'SI'

                    fini = eMateria.inicio
                    ffin = eMateria.fin
                    fechainiresta = fini - timedelta(days=4)
                    fechafinresta = ffin - timedelta(days=4)
                    finicresta = fechainiresta
                    ffincresta = fechafinresta

                    eDistributivo = ProfesorDistributivoHoras.objects.filter(periodo=ePeriodo, profesor=eProfesor, status=True)
                    tipo = 'FACULTAD'

                    if tipo == 'FACULTAD':
                        if not eDistributivo.exists():
                            mensaje = "No registra actividades de docencia, verifique el periodo."
                            raise NameError('Error')
                    if eDistributivo:
                        eDistributivo = eDistributivo[0]

                    evidencias = EvidenciaActividadDetalleDistributivo.objects.filter(Q(criterio__distributivo=eDistributivo) & ((Q(desde__gte=fini) & Q(hasta__lte=ffin)) | (Q(desde__lte=fini) & Q(hasta__gte=ffin)) | (Q(desde__lte=ffin) & Q(desde__gte=fini)) | (Q(hasta__gte=fini) & Q(hasta__lte=ffin)))).distinct().order_by('desde')
                    evidenciasgestion = None
                    evidenciasinvestigacion = None
                    evidenciasdocencia = None
                    if evidencias:
                        if evidencias.filter(criterio__criteriogestionperiodo__isnull=False).exists():
                            evidenciasgestion = evidencias.filter(criterio__criteriogestionperiodo__isnull=False)
                        if evidencias.filter(criterio__criterioinvestigacionperiodo__isnull=False).exists():
                            evidenciasinvestigacion = evidencias.filter(
                                criterio__criterioinvestigacionperiodo__isnull=False)
                        if evidencias.filter(criterio__criteriodocenciaperiodo__isnull=False).exists():
                            evidenciasdocencia = evidencias.filter(criterio__criteriodocenciaperiodo__isnull=False)
                    # profesormateria*********************************************
                    profesormateria = eMateria.profesormateria_set.filter(profesor=eProfesor, tipoprofesor_id__in=[1, 2, 5, 6, 10, 11, 12, 14, 15, 17], activo=True).distinct().order_by('desde', 'materia__asignatura__nombre')
                    eAsignaturas = profesormateria

                    listaasistencias = []
                    cursor = connections['default'].cursor()
                    sql = """
                        SELECT DISTINCT ten.codigoclase,ten.dia,ten.turno_id,ten.inicio,ten.fin,ten.materia_id,ten.tipohorario, ten.horario,ten.rangofecha, ten.rangodia,0 AS sincronica,asincronica.fechaforo AS asincronica, asignatura, paralelo,asincronica.idforomoodle AS idforomoodle,ten.comienza,ten.termina,nolaborables.fecha,nolaborables.observaciones,ten.nivelmalla,ten.idnivelmalla,ten.idcarrera,ten.idcoordinacion,ten.tipoprofesor_id, EXTRACT(week
                        FROM ten.rangofecha:: DATE) AS numerosemana,ten.tipoprofesor,ten.subirenlace, CASE EXTRACT(dow
                        FROM ten.rangofecha) WHEN 1 THEN 'Lunes' WHEN 2 THEN 'Martes' WHEN 3 THEN 'Miercoles' WHEN 4 THEN 'Jueves' WHEN 5 THEN 'Viernes' WHEN 6 THEN 'Sabado' ELSE 'Domingo' END AS nombredia,asincronica.enlaceuno,asincronica.enlacedos,asincronica.enlacetres
                        FROM (
                        SELECT DISTINCT cla.tipoprofesor_id,cla.id AS codigoclase, cla.dia,cla.turno_id,cla.inicio,cla.fin,cla.materia_id, cla.tipohorario, CASE WHEN cla.tipohorario in(2,8) THEN 2 WHEN cla.tipohorario in(7,9) THEN 7 END AS horario, CURRENT_DATE + generate_series(cla.inicio- CURRENT_DATE, cla.fin - CURRENT_DATE) AS rangofecha, EXTRACT (isodow
                        FROM CURRENT_DATE + generate_series(cla.inicio- CURRENT_DATE, cla.fin - CURRENT_DATE)) AS rangodia,asig.nombre AS asignatura, mate.paralelo AS paralelo,tur.comienza,tur.termina,nimalla.nombre AS nivelmalla,nimalla.id AS idnivelmalla,malla.carrera_id AS idcarrera,coorcar.coordinacion_id AS idcoordinacion,tipro.nombre AS tipoprofesor,cla.subirenlace
                        FROM sga_clase cla, sga_materia mate, sga_asignaturamalla asimalla,sga_asignatura asig,sga_turno tur,sga_nivel niv,sga_nivelmalla nimalla,sga_malla malla,sga_carrera carre, sga_coordinacion_carrera coorcar, sga_tipoprofesor tipro
                        WHERE cla.status AND cla.activo AND cla.profesor_id=%s AND cla.materia_id = mate.id AND mate.asignaturamalla_id = asimalla.id AND asimalla.malla_id=malla.id AND asimalla.asignatura_id = asig.id AND cla.turno_id=tur.id AND asimalla.nivelmalla_id=nimalla.id AND malla.carrera_id=carre.id AND coorcar.carrera_id=carre.id AND cla.tipohorario IN (8, 9, 2, 7) AND mate.nivel_id=niv.id AND cla.tipoprofesor_id=tipro.id AND niv.periodo_id=%s) AS ten 
                        left JOIN (
                            SELECT clas.materia_id,asi.fechaforo,asi.idforomoodle, clas.tipoprofesor_id,asi.enlaceuno,asi.enlacedos,asi.enlacetres
                            FROM sga_claseasincronica asi, sga_clase clas
                            WHERE asi.clase_id=clas.id and asi.status and clas.status
                        ) AS asincronica ON asincronica.materia_id=ten.materia_id AND ten.rangofecha=asincronica.fechaforo AND ten.horario in(2,7) AND ten.tipoprofesor_id=asincronica.tipoprofesor_id 
                        left JOIN (
                            SELECT nolab.observaciones, nolab.fecha
                            FROM sga_diasnolaborable nolab
                            WHERE nolab.periodo_id=%s AND nolab.status
                        ) AS nolaborables ON nolaborables.fecha = ten.rangofecha
                        WHERE ten.dia=ten.rangodia AND ten.materia_id = %s AND 
                            EXTRACT(week FROM ten.rangofecha:: DATE) IN (
                                SELECT semana FROM sga_silabosemanal silabosemanal 
                                INNER JOIN sga_silabo silabo ON (silabosemanal.silabo_id = silabo.id) 
                                WHERE (silabo.materia_id = %s AND silabo.status AND silabosemanal.status)
                            )
                        ORDER BY ten.rangofecha,materia_id,ten.comienza,tipohorario
                    """ % (str(eProfesor.id), str(ePeriodo.id), str(ePeriodo.id), str(eMateria.id), str(eMateria.id))
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    totalsincronica = 0
                    totalasincronica = 0
                    totalplansincronica = 0
                    totalplanasincronica = 0
                    for cuentamarcadas in results:
                        sinasistencia = False
                        if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22],
                                                              carrera_id=cuentamarcadas[21],
                                                              nivelmalla_id=cuentamarcadas[20], status=True).exists():
                            if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22],
                                                                  carrera_id=cuentamarcadas[21],
                                                                  nivelmalla_id=cuentamarcadas[20],
                                                                  fecha=cuentamarcadas[8], status=True).exists():
                                sinasistencia = True
                        else:
                            if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22],
                                                                  carrera_id=cuentamarcadas[21],
                                                                  nivelmalla_id__isnull=True, status=True).exists():
                                if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22],
                                                                      carrera_id=cuentamarcadas[21],
                                                                      nivelmalla_id__isnull=True,
                                                                      fecha=cuentamarcadas[8], status=True).exists():
                                    sinasistencia = True
                            else:
                                if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22],
                                                                      carrera_id__isnull=True,
                                                                      nivelmalla_id__isnull=True, status=True).exists():
                                    if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22],
                                                                          carrera_id__isnull=True,
                                                                          nivelmalla_id__isnull=True,
                                                                          fecha=cuentamarcadas[8],
                                                                          status=True).exists():
                                        sinasistencia = True
                                else:
                                    if periodo.diasnolaborable_set.filter(coordinacion_id__isnull=True,
                                                                          carrera_id__isnull=True,
                                                                          nivelmalla_id__isnull=True,
                                                                          status=True).exists():
                                        if periodo.diasnolaborable_set.filter(coordinacion_id__isnull=True,
                                                                              carrera_id__isnull=True,
                                                                              nivelmalla_id__isnull=True,
                                                                              fecha=cuentamarcadas[8],
                                                                              status=True).exists():
                                            sinasistencia = True
                        # listaasistencias = []
                        listaasistencias.append(
                            [cuentamarcadas[0], cuentamarcadas[1], cuentamarcadas[2], cuentamarcadas[3],
                             cuentamarcadas[4], cuentamarcadas[5], cuentamarcadas[6], cuentamarcadas[7],
                             cuentamarcadas[8], cuentamarcadas[9], cuentamarcadas[10], cuentamarcadas[11],
                             cuentamarcadas[12], cuentamarcadas[13], cuentamarcadas[14], cuentamarcadas[15],
                             cuentamarcadas[16], cuentamarcadas[17], cuentamarcadas[18], cuentamarcadas[19],
                             sinasistencia, cuentamarcadas[24], cuentamarcadas[25], cuentamarcadas[26],
                             cuentamarcadas[27], cuentamarcadas[28], cuentamarcadas[29], cuentamarcadas[30]])

                        if not sinasistencia:
                            if cuentamarcadas[7] == 2:
                                totalsincronica += 1
                            if cuentamarcadas[7] == 7:
                                totalasincronica += 1
                            totalplansincronica += 1
                            if cuentamarcadas[11]:
                                totalplanasincronica += 1
                    try:
                        procentajesincronica = (totalplansincronica * 100) / totalsincronica
                    except ZeroDivisionError:
                        procentajesincronica = 0
                    try:
                        procentajeasincronica = (totalplanasincronica * 100) / totalasincronica
                    except ZeroDivisionError:
                        procentajeasincronica = 0

                    total_planificada = (totalsincronica + totalasincronica)
                    total_realizadas = (totalplanasincronica + totalplansincronica)
                    porcentaje_total = 0
                    try:
                        porcentaje_total = ((total_realizadas * 100) / total_planificada) if ((total_realizadas * 100) / total_planificada) <= 100 else 100
                    except ZeroDivisionError:
                        pass
                    cambiodenominacion = convertir_fecha('01-03-2023')
                    eTipoprofesor = 'PROFESOR' if eMateria.inicio >= cambiodenominacion or eMateria.fin >= cambiodenominacion else '%s' % eMateria.tipo_profesormateria(eDistributivo.profesor)

                    data['total_planificada'] = total_planificada
                    data['total_realizadas'] = total_realizadas
                    data['porcentaje_total'] = porcentaje_total
                    data['eDistributivo'] = eDistributivo
                    data['eListaasistencias'] = listaasistencias
                    data['eMateria'] = eMateria
                    data['finicresta'] = finicresta
                    data['ffincresta'] = ffincresta
                    data['eTipoprofesor'] = eTipoprofesor
                    data['eAsignaturas'] = eAsignaturas
                    data['tieneevaluacion'] = tieneevaluacion
                    data['ePeriodo'] = ePeriodo
                    data['hoy'] = datetime.now().date()
                    if request.GET['flag'] == 'resumen':
                        template = get_template("adm_evaluaciondirectivos/modal/detalleresumen.html")
                    elif request.GET['flag'] == 'asistencias':
                        template = get_template("adm_evaluaciondirectivos/modal/detalleasistencias.html")
                    else:
                        template = get_template("adm_evaluaciondirectivos/modal/detalleactividadesdocente.html")
                    return JsonResponse({"result": "ok", 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'verdetallesilabo':
                try:
                    data['id'] = request.GET['id']
                    eMateria = Materia.objects.get(status=True, pk=int(request.GET['id']))
                    data['eProfesor'] = Profesor.objects.get(status=True, pk=int(request.GET['idp']))
                    ePeriodo = eMateria.nivel.periodo
                    data['materia'] = eMateria
                    data['facultad'] = eMateria.asignaturamalla.malla.carrera.coordinaciones()[0]
                    data['silabos'] = eMateria.silabo_set.all()
                    data['aprobar'] = variable_valor('APROBAR_SILABO')
                    data['rechazar'] = variable_valor('RECHAZAR_SILABO')
                    data['pendiente'] = variable_valor('PENDIENTE_SILABO')
                    d = datetime.now()
                    data['horasegundo'] = d.strftime('%Y%m%d_%H%M%S')
                    template = get_template("adm_evaluaciondirectivos/modal/detalleplananalitico.html")
                    return JsonResponse({"result": "ok", 'data': template.render(data)})
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Evaluación de directivos Posgrado'
                url_vars = ''
                search = request.GET.get('s', None)
                search2 = request.GET.get('s2', None)
                desde = request.GET.get('desde', '')
                hasta = request.GET.get('hasta', '')
                escuela = request.GET.get('escuela', '')
                maestria = request.GET.get('maestria', '')
                peri = request.GET.get('periodoa', '')
                paralelo = request.GET.get('paralelo', '')
                estado = request.GET.get('estado', '')

                if DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.filter(status=True, evaluador=persona, coordinacion_id=7, materia__isnull=False, inicio__isnull=True, fin__isnull=True).order_by('-id'):
                    migrar_datos(persona)

                filtro = Q(status=True, evaluador=persona, coordinacion_id=7, materia__isnull=False)
                if search:
                    data['search'] = search
                    ss = search.split(' ')
                    if len(ss) == 1:
                        filtro = filtro & (Q(materia__asignaturamalla__asignatura__nombre__icontains=search))
                        url_vars += "&s={}".format(search)
                    elif len(ss) == 2:
                        filtro = filtro & (Q(materia__asignaturamalla__asignatura__nombre__icontains=ss[0]) &
                                           Q(materia__asignaturamalla__asignatura__nombre__icontains=ss[1]))
                        url_vars += "&s={}".format(ss)
                    else:
                        filtro = filtro & (Q(materia__asignaturamalla__asignatura__nombre__icontains=ss[0]) &
                                           Q(materia__asignaturamalla__asignatura__nombre__icontains=ss[1]) &
                                           Q(materia__asignaturamalla__asignatura__nombre__icontains=ss[2]))
                        url_vars += "&s={}".format(ss)

                if search2:
                    data['search2'] = search2
                    ss = search2.split(' ')
                    if len(ss) == 1:
                        filtro = filtro & (Q(evaluado__persona__apellido1__icontains=search2) |
                                                 Q(evaluado__persona__apellido2__icontains=search2) |
                                                 Q(evaluado__persona__nombres__icontains=search2) |
                                                 Q(evaluado__persona__cedula__icontains=search2))
                        url_vars += "&s2={}".format(search2)
                    elif len(ss) == 2:
                        filtro = filtro & (Q(evaluado__persona__apellido1__icontains=ss[0]) &
                                                 Q(evaluado__persona__apellido2__icontains=ss[1]))
                        url_vars += "&s2={}".format(ss)
                    else:
                        filtro = filtro & (Q(evaluado__persona__apellido1__icontains=ss[0]) &
                                            Q(evaluado__persona__apellido2__icontains=ss[1]) &
                                           Q(evaluado__persona__nombres__icontains=ss[2]))
                        url_vars += "&s2={}".format(ss)

                if escuela:
                    data['escuela'] = int(escuela)
                    filtro = filtro & Q(materia__asignaturamalla__malla__carrera__escuelaposgrado__id=int(escuela))
                    url_vars += "&escuela={}".format(escuela)

                if maestria:
                    data['maestria'] = int(maestria)
                    filtro = filtro & Q(materia__asignaturamalla__malla__carrera__id=int(maestria))
                    url_vars += "&maestria={}".format(maestria)

                if peri:
                    data['periodoa'] = int(peri)
                    filtro = filtro & Q(materia__nivel__periodo_id=int(peri))
                    url_vars += "&periodoa={}".format(peri)

                if paralelo:
                    data['paralelo'] = paralelo
                    filtro = filtro & Q(materia__paralelo=paralelo)
                    url_vars += "&paralelo={}".format(peri)

                if desde and hasta:
                    data['desde'] = desde
                    data['hasta'] = hasta
                    # query = DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.filter(filtro).order_by('-id')
                    # eDetalle = DetalleFechasEvalDirMateria.objects.filter(status=True, materia__id__in=query.values_list('materia__id', flat=True), inicio__range=(desde, hasta))
                    filtro = filtro & Q(inicio__range=(desde, hasta))
                    url_vars += "&desde={}".format(desde)
                    url_vars += "&hasta={}".format(hasta)

                elif desde:
                    data['desde'] = desde
                    # query = DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.filter(filtro).order_by('-id')
                    # eDetalle = DetalleFechasEvalDirMateria.objects.filter(status=True, materia__id__in=query.values_list('materia__id', flat=True), inicio__gte=desde)
                    filtro = filtro & Q(inicio__gte=desde)
                    url_vars += "&desde={}".format(hasta)

                elif hasta:
                    data['hasta'] = hasta
                    # query = DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.filter(filtro).order_by('-id')
                    # eDetalle = DetalleFechasEvalDirMateria.objects.filter(status=True, materia__id__in=query.values_list('materia__id', flat=True), inicio__lte=hasta)
                    filtro = filtro & Q(inicio__lte=hasta)
                    url_vars += "&hasta={}".format(hasta)

                if estado:
                    data['estado'] = int(estado)
                    if int(estado) == 1:
                        filtro = filtro & Q(evalua=True)
                    elif int(estado) == 2:
                        filtro = filtro & Q(evalua=False)
                    elif int(estado) == 3:
                        # query = DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.filter(filtro).order_by('-id')
                        # eDetalle = DetalleFechasEvalDirMateria.objects.filter(status=True, materia__id__in=query.values_list('materia__id', flat=True), fin__lt=datetime.now().date())
                        filtro = filtro & Q(fin__lt=datetime.now().date())
                    url_vars += "&estado={}".format(estado)

                # if filtro2:
                #     query = DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.filter(filtro2).order_by('-id')
                # else:
                query = DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.filter(filtro).order_by('-fin')

                paging = MiPaginador(query, 10)
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
                data['paging'] = paging
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['search'] = search if search else ""
                data["url_params"] = url_vars
                data["url_vars"] = url_vars
                data["eModulos"] = page.object_list
                data["eCount"] = query.count()

                profesores_directivos = persona.detalleinstrumentoevaluaciondirectivoacreditacion_set.filter(proceso__periodo__tipo__id=3, status=True).distinct().order_by('evaluado__persona')
                data['codigosevaluacion'] = persona.respuestaevaluacionacreditacion_set.values_list('materia_id', flat=True).filter(tipoinstrumento=4, proceso__periodo__tipo__id=3, profesor_id__in=profesores_directivos.values_list('evaluado_id'))
                data['codigosevaluacionnew'] = persona.respuestaevaluacionacreditacionposgrado_set.values_list('materia_id', flat=True).filter(tipoinstrumento=4, proceso__periodo__tipo__id=3, profesor_id__in=profesores_directivos.values_list('evaluado_id'))

                # old = persona.respuestaevaluacionacreditacion_set.values_list('materia_id', flat=True).filter(tipoinstrumento=4, proceso__periodo__tipo__id=3, profesor_id__in=profesores_directivos.values_list('evaluado_id'), materia__id__in=query.values_list('materia__id', flat=True)).count()
                # new = persona.respuestaevaluacionacreditacionposgrado_set.values_list('materia_id', flat=True).filter(tipoinstrumento=4, proceso__periodo__tipo__id=3, profesor_id__in=profesores_directivos.values_list('evaluado_id'), materia__id__in=query.values_list('materia__id', flat=True)).count()
                data['eEvaluados'] = query.filter(evalua=True).count()
                data['eNoEvaluados'] = query.filter(evalua=False).count()

                es_director = False
                if Departamento.objects.filter(pk=216, responsable=persona).exists():
                    data["eEscuelas"] = EscuelaPosgrado.objects.filter(status=True, pk=1)
                    es_director = True
                elif Departamento.objects.filter(pk=215, responsable=persona).exists():
                    data["eEscuelas"] = EscuelaPosgrado.objects.filter(status=True, pk=2)
                    es_director = True
                elif Departamento.objects.filter(pk=163, responsable=persona).exists():
                    data["eEscuelas"] = EscuelaPosgrado.objects.filter(status=True, pk=3)
                    es_director = True
                else:
                    ides = query.values_list('materia__asignaturamalla__malla__carrera__escuelaposgrado__id', flat=True).order_by('materia__asignaturamalla__malla__carrera__escuelaposgrado__id').distinct()
                    data["eEscuelas"] = EscuelaPosgrado.objects.filter(status=True, id__in=ides)
                data['es_director'] = es_director
                return render(request, "adm_evaluaciondirectivos/view.html", data)
            except Exception as ex:
                pass


def migrar_datos(ePersona):
    try:
        filtro = Q(status=True, evaluador=ePersona, coordinacion_id=7, materia__isnull=False, inicio__isnull=True, fin__isnull=True)
        eDetalles = DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.filter(filtro).order_by('-id')

        c = 0
        for eDetalle in eDetalles:
            if DetalleFechasEvalDirMateria.objects.filter(status=True, materia=eDetalle.materia, inicio__isnull=False,
                                                          fin__isnull=False).exists():
                eDeta = DetalleFechasEvalDirMateria.objects.filter(status=True, materia=eDetalle.materia,
                                                                   inicio__isnull=False, fin__isnull=False).first()
                if not eDetalle.inicio:
                    eDetalle.inicio = eDeta.inicio
                if not eDetalle.fin:
                    eDetalle.fin = eDeta.fin

                if evaluo_director_2(eDetalle):
                    eDetalle.evalua = True
                if evaluo_coordinador_2(eDetalle):
                    eDetalle.evalua = True
                eDetalle.save()
                c += 1
            else:
                if not DetalleFechasEvalDirMateria.objects.filter(status=True, materia=eDetalle.materia).exists():
                    eDetalle2 = DetalleFechasEvalDirMateria(materia=eDetalle.materia, inicio='2024-10-01', fin='2024-10-01')
                    eDetalle2.save()
                else:
                    eDetalle2 = DetalleFechasEvalDirMateria.objects.filter(status=True, materia=eDetalle.materia).first()
                    eDetalle2.inicio ='2024-10-01'
                    eDetalle2.fin ='2024-10-01'
                    eDetalle2.save()
                if evaluo_director_2(eDetalle):
                    eDetalle.evalua = True
                if evaluo_coordinador_2(eDetalle):
                    eDetalle.evalua = True
                eDetalle.save()
            print(f'{c}.- {eDetalle.evaluado}, {eDetalle.materia}, {eDetalle.inicio}, {eDetalle.fin}, {eDetalle.evalua}')
    except Exception as ex:
        pass
