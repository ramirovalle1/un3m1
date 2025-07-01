# -*- coding: latin-1 -*-
import sys
from datetime import datetime, timedelta, date
from django.contrib.auth.decorators import login_required
from django.db import transaction, connections
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decimal import Decimal
import calendar
from django.db.models import Q, Sum, ExpressionWrapper, F, TimeField, DateTimeField, Prefetch
from django.template.context import Context
from django.template.loader import get_template
from decorators import last_access
from inno.models import SubactividadDetalleDistributivo
from investigacion.models import BitacoraActividadDocente, HistorialBitacoraActividadDocente
from sagest.models import InformeGenerado, PermisoInstitucional, LogDia
from settings import MATRICULACION_LIBRE, VER_SILABO_MALLA, VER_PLAN_ESTUDIO
from sga.commonviews import adduserdata, obtener_reporte
from sga.forms import CompendioPlagioForm
from sga.funciones import log, variable_valor, MiPaginador, convertir_fecha, actualizar_resumen
from sga.funciones_templatepdf import evidenciassilabosxcarrera
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
import collections
from sga.models import Profesor, miinstitucion, RespuestaEvaluacionAcreditacion, Rubrica, RespuestaRubrica, \
    DetalleRespuestaRubrica, \
    ActividadDetalleInstrumentoPar, \
    DetalleDistributivo, CriterioTipoObservacionEvaluacion, ProfesorDistributivoHoras, PaeActividadesPeriodoAreas, \
    Persona, PonenciasInvestigacion, CapituloLibroInvestigacion, LibroInvestigacion, ArticuloInvestigacion, Materia, \
    MateriaCursoEscuelaComplementaria, CUENTAS_CORREOS, ProfesorMateria, Silabo, ComplexivoGrupoTematica, AvTutorias, \
    MateriaAsignada, CriterioDocencia, AvPreguntaRespuesta, AvTutoriasAlumnos, TareaSilaboSemanal, \
    GuiaEstudianteSilaboSemanal, ForoSilaboSemanal, TestSilaboSemanal, GuiaDocenteSilaboSemanal, \
    DiapositivaSilaboSemanal, MaterialAdicionalSilaboSemanal, CompendioSilaboSemanal, Carrera, ArchivoTitulacion, \
    PeriodoGrupoTitulacion, ComplexivoExamen, EvidenciaActividadDetalleDistributivo, VideoMagistralSilaboSemanal, \
    PracticasPreprofesionalesInscripcion, InformeMensualDocentesPPP, CriterioDocenciaPeriodoTitulacion, RubricaPreguntas, \
    MESES_CHOICES, ClaseActividad, Clase, ClaseAsincronica
from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt
from dateutil.rrule import MONTHLY, rrule
from posgrado.models import DetalleRespuestaRubricaPosgrado, RespuestaEvaluacionAcreditacionPosgrado, \
    RespuestaRubricaPosgrado, DetalleRespuestaRubricaPos

def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)


# def evaluado_directivo_periodo(self, periodo, par, materia):
#     return RespuestaEvaluacionAcreditacion.objects.values('id').filter(tipoinstrumento=4, proceso__periodo=periodo,
#                                                                            profesor=self, evaluador=par).exists()

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
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    data['title'] = u'Evaluación del docente por pares y directivos'
    data['periodo'] = periodo = request.session['periodo']
    data['proceso'] = proceso = periodo.proceso_evaluativo()
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'evaluar':
                try:
                    profesor = Profesor.objects.get(pk=int(request.POST['idp']))
                    materia = None
                    if int(request.POST['idm']) > 0:
                        materia = Materia.objects.get(pk=int(request.POST['idm']))
                    coordinaciondistributivo = ProfesorDistributivoHoras.objects.filter(periodo=proceso.periodo, profesor=profesor, status=True)[0]
                    if RespuestaEvaluacionAcreditacion.objects.filter(proceso__periodo=periodo, profesor=profesor, evaluador=persona,tipoinstrumento=int(request.POST['tipo'])).exists():
                        return JsonResponse({"result": "bad", 'mensaje': u'Evaluación ya existe.'})
                    materiarevision = None
                    evaluacion = RespuestaEvaluacionAcreditacion(proceso=proceso,
                                                                 tipoinstrumento=int(request.POST['tipo']),
                                                                 profesor=profesor,
                                                                 evaluador=persona,
                                                                 fecha=datetime.now(),
                                                                 # coordinacion=profesor.coordinacion,
                                                                 coordinacion=coordinaciondistributivo.coordinacion,
                                                                 carrera=profesor.carrera_principal_periodo(periodo),
                                                                 tipomejoras_id=request.POST['nommejoras'],
                                                                 tipocontinua_id=request.POST['nomcontinua'],
                                                                 accionmejoras=request.POST['accionmejoras'],
                                                                 formacioncontinua=request.POST['formacioncontinua'],
                                                                 materia=materia if materia is not None else None)
                    evaluacion.save(request)
                    listarespuesta = []
                    for elemento in request.POST['lista'].split(';'):
                        individuales = elemento.split(':')
                        rubricapregunta = RubricaPreguntas.objects.get(pk=int(individuales[0]))
                        rubrica = rubricapregunta.rubrica
                        if not RespuestaRubrica.objects.filter(respuestaevaluacion=evaluacion, rubrica=rubrica).exists():
                            respuestarubrica = RespuestaRubrica(respuestaevaluacion=evaluacion,
                                                                rubrica=rubrica,
                                                                valor=0)
                            respuestarubrica.save(request)
                        else:
                            respuestarubrica = RespuestaRubrica.objects.filter(respuestaevaluacion=evaluacion, rubrica=rubrica)[0]
                        listarespuesta.append(respuestarubrica.id)
                        justificacion = individuales[2] if len(individuales) > 2 and individuales[2] is not None else None
                        detalle = DetalleRespuestaRubrica(respuestarubrica=respuestarubrica,
                                                          rubricapregunta=rubricapregunta,
                                                          valor=float(individuales[1]),
                                                          justificacion=justificacion)
                        detalle.save(request)
                        respuestarubrica.save()
                    evaluacion.save()
                    # for elemento in request.POST['lista'].split(';'):
                    #     individuales = elemento.split(':')
                    #     rubrica = Rubrica.objects.get(pk=int(individuales[0]))
                    #     respuestarubrica = RespuestaRubrica(respuestaevaluacion=evaluacion,
                    #                                         rubrica=rubrica,
                    #                                         valor=float(individuales[1]))
                    #     respuestarubrica.save(request)
                    #     for rubricapregunta in rubrica.mis_preguntas():
                    #         detalle = DetalleRespuestaRubrica(respuestarubrica=respuestarubrica,
                    #                                           rubricapregunta=rubricapregunta,
                    #                                           valor=respuestarubrica.valor)
                    #         detalle.save(request)
                    #     respuestarubrica.save(request)
                    # evaluacion.save(request)
                    distributivo = profesor.distributivohoraseval(periodo)
                    resumen = distributivo.resumen_evaluacion_acreditacion()
                    resumen.actualizar_resumen()
                    log(u'Evaluacion del profesor por par o directivo: %s' % profesor, request, "add")
                    # send_html_mail("Evaluacion docente realizada.", "emails/evaluaciondocente.html", {'sistema': request.session['nombresistema'], 'd': evaluacion, 't': miinstitucion()}, persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[2][1])
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    eline = 'Error on line {} {}'.format(sys.exc_info()[-1].tb_lineno, ex.__str__())
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % eline})

            if action == 'evaluarposgrado':
                try:
                    profesor = Profesor.objects.get(pk=int(request.POST['idp']))
                    materia = None
                    if int(request.POST['idm']) > 0:
                        materia = Materia.objects.get(pk=int(request.POST['idm']))
                    coordinaciondistributivo = ProfesorDistributivoHoras.objects.filter(periodo=proceso.periodo, profesor=profesor, status=True)[0]
                    if RespuestaEvaluacionAcreditacionPosgrado.objects.filter(proceso__periodo=periodo, profesor=profesor, evaluador=persona,tipoinstrumento=int(request.POST['tipo']), materia=materia).exists():
                        return JsonResponse({"result": "bad", 'mensaje': u'Evaluación ya existe.'})
                    materiarevision = None
                    evaluacion = RespuestaEvaluacionAcreditacionPosgrado(proceso=proceso,
                                                                 tipoinstrumento=int(request.POST['tipo']),
                                                                 profesor=profesor,
                                                                 evaluador=persona,
                                                                 fecha=datetime.now(),
                                                                 coordinacion=coordinaciondistributivo.coordinacion,
                                                                 carrera=profesor.carrera_principal_periodo(periodo),
                                                                 tipomejoras_id=request.POST['nommejoras'],
                                                                 accionmejoras=request.POST['accionmejoras'],
                                                                 materia=materia if materia is not None else None)
                    evaluacion.save(request)
                    listarespuesta = []
                    for elemento in request.POST['lista'].split(';'):
                        individuales = elemento.split(':')
                        rubricapregunta = RubricaPreguntas.objects.get(pk=int(individuales[0]))
                        rubrica = rubricapregunta.rubrica
                        if not RespuestaRubricaPosgrado.objects.filter(respuestaevaluacion=evaluacion, rubrica=rubrica).exists():
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

                    # evaluacion.save()
                    # distributivo = profesor.distributivohoraseval(periodo)
                    # resumen = distributivo.resumen_evaluacion_acreditacion()
                    # actualizar_resumen(resumen)
                    # resumen.actualizar_resumen()
                    log(u'Evaluacion del profesor por par o directivo: %s' % profesor, request, "add")
                    # send_html_mail("Evaluacion docente realizada.", "emails/evaluaciondocente.html", {'sistema': request.session['nombresistema'], 'd': evaluacion, 't': miinstitucion()}, persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[2][1])
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'evaluarrevision':
                try:
                    profesor = Profesor.objects.get(pk=int(request.POST['idp']))
                    coordinaciondistributivo = ProfesorDistributivoHoras.objects.get(periodo=proceso.periodo, profesor=profesor, status=True)
                    if RespuestaEvaluacionAcreditacion.objects.filter(proceso__periodo=periodo, profesor=profesor, tipoprofesor_id=request.POST['tipoprofe'], materia_id=request.POST['codimate'], evaluador=persona,tipoinstrumento=int(request.POST['tipo'])).exists():
                        return JsonResponse({"result": "bad", 'mensaje': u'Evaluación ya existe.'})
                    materiarevision = request.POST['codimate']
                    tipoprofe = request.POST['tipoprofe']
                    evaluacion = RespuestaEvaluacionAcreditacion(proceso=proceso,
                                                                 tipoinstrumento=int(request.POST['tipo']),
                                                                 profesor=profesor,
                                                                 evaluador=persona,
                                                                 fecha=datetime.now(),
                                                                 materia_id=materiarevision,
                                                                 tipoprofesor_id=tipoprofe,
                                                                 coordinacion=coordinaciondistributivo.coordinacion,
                                                                 carrera=profesor.carrera_principal_periodo(periodo),
                                                                 tipomejoras_id=request.POST['nommejoras'],
                                                                 accionmejoras=request.POST['accionmejoras'])
                    evaluacion.save(request)
                    for elemento in request.POST['lista'].split(';'):
                        individuales = elemento.split(':')
                        rubrica = Rubrica.objects.get(pk=int(individuales[0]))
                        respuestarubrica = RespuestaRubrica(respuestaevaluacion=evaluacion,
                                                            rubrica=rubrica,
                                                            valor=float(individuales[1]))
                        respuestarubrica.save(request)
                        for rubricapregunta in rubrica.mis_preguntas():
                            detalle = DetalleRespuestaRubrica(respuestarubrica=respuestarubrica,
                                                              rubricapregunta=rubricapregunta,
                                                              valor=respuestarubrica.valor)
                            detalle.save(request)
                        respuestarubrica.save(request)
                    evaluacion.save(request)
                    log(u'Evaluacion del profesor revision: %s' % profesor, request, "add")
                    send_html_mail("Evaluación docente realizada.", "emails/evaluaciondocente.html", {'sistema': request.session['nombresistema'], 'd': evaluacion, 't': miinstitucion(), 'tituloemail': "Evaluación docente realizada"}, persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[2][1])
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'listasubmejoras':
                try:
                    combomejoras = CriterioTipoObservacionEvaluacion.objects.get(pk=request.POST['id'])
                    tipoinstrumento = request.POST['tipoins']
                    lista = []
                    for detmejoras in combomejoras.tipoobservacionevaluacion_set.filter(tipoinstrumento=tipoinstrumento, tipo=1, status=True, activo=True).order_by('nombre'):
                        lista.append([detmejoras.id, detmejoras.nombre.upper()])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'calculaclases':
                try:
                    fechaevaluacion = '2021-02-21'
                    codrubrica = int(request.POST['codrubrica'])
                    codiprofe = request.POST['codiprofe']
                    cursor = connections['sga_select'].cursor()
                    valorprecargado = 0
                    variableoculta = 0
                    if codrubrica == 564:
                        proma = ProfesorMateria.objects.filter(profesor_id=codiprofe, materia__nivel__periodo_id=112,status=True).exclude(materia__asignaturamalla__nivelmalla_id__in=[7,8],materia__asignaturamalla__malla__carrera_id__in=[111,3,1,110])
                        if proma:
                            sql = """select distinct ten.codigoclase,ten.dia,ten.turno_id,ten.inicio,ten.fin,ten.materia_id,ten.tipohorario, 
                                        ten.horario,ten.rangofecha,ten.rangodia,sincronica.fecha as sincronica,asincronica.fechaforo as asincronica, asignatura, paralelo,asincronica.idforomoodle as idforomoodle,
                                        case 
                                        WHEN asincronica.idforomoodle is null  THEN 0 
                                        WHEN asincronica.idforomoodle is not null  THEN 1 
                                        end as tieneforomoodle,
                                        ten.comienza,ten.termina,nolaborables.fecha,nolaborables.observaciones,ten.nivelmalla,ten.idnivelmalla,ten.idcarrera,ten.idcoordinacion,ten.tipoprofesor_id,extract(week from ten.rangofecha::date) as numerosemana,ten.tipoprofesor 
                                        from (select distinct cla.tipoprofesor_id,cla.id as codigoclase, 
                                        cla.dia,cla.turno_id,cla.inicio,cla.fin,cla.materia_id,cla.tipohorario, 
                                        case 
                                        WHEN cla.tipohorario in(2,8)  THEN 2 
                                        WHEN cla.tipohorario in(7,9)  THEN 7 
                                        end as horario, 
                                        CURRENT_DATE + generate_series(cla.inicio- CURRENT_DATE, cla.fin - CURRENT_DATE ) as rangofecha, 
                                        eXTRACT (isodow  FROM  CURRENT_DATE + generate_series(cla.inicio- CURRENT_DATE, cla.fin - CURRENT_DATE )) as rangodia,asig.nombre as asignatura, mate.paralelo as paralelo,tur.comienza,tur.termina,nimalla.nombre as nivelmalla,nimalla.id as idnivelmalla,malla.carrera_id as idcarrera,coorcar.coordinacion_id as idcoordinacion,tipro.nombre as tipoprofesor 
                                        from sga_clase cla , sga_materia mate, sga_asignaturamalla asimalla,sga_asignatura asig,sga_turno tur,sga_nivel niv,sga_nivelmalla nimalla,sga_malla malla,sga_carrera carre, sga_coordinacion_carrera coorcar, sga_tipoprofesor tipro 
                                        where cla.profesor_id=%s and cla.materia_id = mate.id and mate.asignaturamalla_id = asimalla.id and asimalla.malla_id=malla.id and asimalla.asignatura_id = asig.id and cla.turno_id=tur.id and asimalla.nivelmalla_id=nimalla.id and malla.carrera_id=carre.id and coorcar.carrera_id=carre.id 
                                        AND cla.tipohorario IN (8, 9, 2, 7) and mate.id in%s and mate.nivel_id=niv.id and cla.tipoprofesor_id=tipro.id and niv.periodo_id=112  
                                        ) as ten 
                                        left join 
                                        (select clas.materia_id,asi.fecha_creacion::timestamp::date as fecha,asi.fecha_creacion as fecharegistro 
                                        from sga_clasesincronica asi, sga_clase clas 
                                        where asi.clase_id=clas.id and clas.profesor_id=%s
                                        ) as sincronica on ten.rangofecha=fecha and ten.horario=2 
                                        left join 
                                        (select  clas.materia_id,asi.fechaforo,asi.idforomoodle, clas.tipoprofesor_id 
                                        from sga_claseasincronica asi, sga_clase clas 
                                        where asi.clase_id=clas.id 
                                        ) as asincronica on asincronica.materia_id=ten.materia_id and ten.rangofecha=asincronica.fechaforo and ten.horario=2 and ten.tipoprofesor_id=asincronica.tipoprofesor_id 
                                        left join 
                                        (select nolab.observaciones, nolab.fecha from sga_diasnolaborable nolab 
                                        where nolab.periodo_id=112) as nolaborables on nolaborables.fecha = ten.rangofecha 
                                        where ten.dia=ten.rangodia and ten.rangofecha <= '%s' 
                                        and ten.tipoprofesor_id=1
                                        and nolaborables.observaciones is null
                                    """ % (codiprofe,tuple(proma.values_list('materia_id',flat=True)),codiprofe,fechaevaluacion)
                            cursor.execute(sql)
                            results = cursor.fetchall()
                            contadorasistencias = 0
                            contadortotal = 0
                            for r in results:
                                contadortotal = contadortotal + 1
                                if r[15] > 0:
                                    contadorasistencias = contadorasistencias + 1
                            resultado = round(((contadorasistencias * 100) / contadortotal),0)
                            valorprecargado = 0
                            if resultado <= 20:
                                valorprecargado =1
                            if resultado >= 21 and resultado <= 40:
                                valorprecargado =2
                            if resultado >= 41 and resultado <= 60:
                                valorprecargado =3
                            if resultado >= 61 and resultado <= 80:
                                valorprecargado =4
                            if resultado >= 81:
                                valorprecargado =5
                        else:
                            valorprecargado = 1
                            variableoculta = 1
                    if codrubrica == 565:
                        sql = """select sil.materia_id,count(distinct tar.id) as total
                                    from sga_tareasilabosemanal tar,sga_silabosemanal semanal,sga_silabo sil
                                    where tar.silabosemanal_id=semanal.id
                                    and semanal.silabo_id=sil.id
                                    and tar."status"=True
                                    and semanal."status"=True
                                    and sil."status"=True
                                    and tar.estado_id=4
                                    and sil.materia_id in(
                                    select proma.materia_id from sga_profesormateria proma,sga_materia mate,sga_nivel ni
                                    where proma.materia_id=mate.id
                                    and mate.nivel_id=ni.id
                                    and proma."status"=True
                                    and mate."status"=True
                                    and ni."status"=True
                                    and ni.periodo_id=112
                                    and proma.profesor_id=%s
                                    and proma.tipoprofesor_id in(1,11,12))
                                    and semanal.fechafinciosemana <='%s'
                                    group by sil.materia_id
                                                        """ % (codiprofe, fechaevaluacion)
                        cursor.execute(sql)
                        results = cursor.fetchall()
                        contadorasistencias = 0
                        contadortotal = 0
                        for r in results:
                            contadortotal = contadortotal + 1
                            contadorasistencias = contadorasistencias + r[1]
                        resultado = round((contadorasistencias / contadortotal),0)
                        valorprecargado = 0
                        if resultado <= 1:
                            valorprecargado = 1
                        if resultado == 2:
                            valorprecargado = 3
                        if resultado >= 3:
                            valorprecargado = 5
                    if codrubrica == 567:
                        sql = """select sil.materia_id,tar.estado_id,count(distinct tar.id) as total
                                    from sga_forosilabosemanal tar,sga_silabosemanal semanal,sga_silabo sil
                                    where tar.silabosemanal_id=semanal.id
                                    and semanal.silabo_id=sil.id
                                    and tar."status"=True
                                    and semanal."status"=True
                                    and sil."status"=True
                                    and tar.estado_id=4
                                    and sil.materia_id in(
                                    select proma.materia_id from sga_profesormateria proma,sga_materia mate,sga_nivel ni
                                    where proma.materia_id=mate.id
                                    and mate.nivel_id=ni.id
                                    and proma."status"=True
                                    and mate."status"=True
                                    and ni."status"=True
                                    and ni.periodo_id=112
                                    and proma.profesor_id=%s
                                    and proma.tipoprofesor_id in(1,11,12))
                                    and semanal.fechafinciosemana <='%s'
                                    group by sil.materia_id,tar.estado_id
                                                        """ % (codiprofe, fechaevaluacion)
                        cursor.execute(sql)
                        results = cursor.fetchall()
                        contadorasistencias = 0
                        contadortotal = 0
                        totalrechazados = 0
                        totalmoodles = 0
                        if results:
                            for r in results:
                                contadortotal = contadortotal + 1
                                if r[1] == 3:
                                    totalrechazados = totalrechazados + r[2]
                                if r[1] == 4:
                                    totalmoodles = totalmoodles + r[2]
                            valorprecargado = 0
                            if totalmoodles == totalrechazados or totalmoodles < totalrechazados:
                                valorprecargado = 3
                            if totalmoodles > totalrechazados:
                                valorprecargado = 5
                        else:
                            valorprecargado = 3
                            variableoculta = 1
                    if codrubrica == 569:
                        sql = """select sil.materia_id,count(distinct tar.id) as total
                                    from sga_testsilabosemanal tar,sga_silabosemanal semanal,sga_silabo sil
                                    where tar.silabosemanal_id=semanal.id
                                    and semanal.silabo_id=sil.id
                                    and tar."status"=True
                                    and semanal."status"=True
                                    and sil."status"=True
                                    and tar.estado_id=4
                                    and sil.materia_id in(
                                    select proma.materia_id from sga_profesormateria proma,sga_materia mate,sga_nivel ni
                                    where proma.materia_id=mate.id
                                    and mate.nivel_id=ni.id
                                    and proma."status"=True
                                    and mate."status"=True
                                    and ni."status"=True
                                    and ni.periodo_id=112
                                    and proma.profesor_id=%s
                                    and proma.tipoprofesor_id in(1,11,12))
                                    and semanal.fechafinciosemana <='%s'
                                    group by sil.materia_id
                                                        """ % (codiprofe, fechaevaluacion)
                        cursor.execute(sql)
                        results = cursor.fetchall()
                        contadorasistencias = 0
                        contadortotal = 0
                        for r in results:
                            contadortotal = contadortotal + 1
                            contadorasistencias = contadorasistencias + r[1]
                        resultado = round((contadorasistencias / contadortotal),0)
                        valorprecargado = 0
                        if resultado <= 1:
                            valorprecargado = 1
                        if resultado == 2:
                            valorprecargado = 3
                        if resultado >= 3:
                            valorprecargado = 5
                    if codrubrica == 571:
                        if ProfesorMateria.objects.filter(materia__nivel__periodo_id=112,tipoprofesor_id=12,profesor_id=codiprofe,status=True).exists():
                            sql = """select sil.materia_id,count(distinct tar.id) as total
                                        from sga_compendiosilabosemanal tar,sga_silabosemanal semanal,sga_silabo sil
                                        where tar.silabosemanal_id=semanal.id
                                        and semanal.silabo_id=sil.id
                                        and tar."status"=True
                                        and semanal."status"=True
                                        and sil."status"=True
                                        and tar.estado_id=4
                                        and sil.materia_id in(
                                        select proma.materia_id from sga_profesormateria proma,sga_materia mate,sga_nivel ni
                                        where proma.materia_id=mate.id
                                        and mate.nivel_id=ni.id
                                        and proma."status"=True
                                        and mate."status"=True
                                        and ni."status"=True
                                        and ni.periodo_id=112
                                        and proma.profesor_id=%s
                                        and proma.tipoprofesor_id in(1,11,12))
                                        and semanal.fechafinciosemana <='%s'
                                        group by sil.materia_id
                                                            """ % (codiprofe, fechaevaluacion)
                            cursor.execute(sql)
                            results = cursor.fetchall()
                            contadorasistencias = 0
                            contadortotal = 0
                            if results:
                                for r in results:
                                    contadortotal = contadortotal + 1
                                    contadorasistencias = contadorasistencias + r[1]
                                resultado = round((contadorasistencias / contadortotal),0)
                            else:
                                resultado = 1
                            valorprecargado = 0
                            if resultado <= 2:
                                valorprecargado = 1
                            if resultado == 3:
                                valorprecargado = 2
                            if resultado == 4:
                                valorprecargado = 3
                            if resultado == 5:
                                valorprecargado = 4
                            if resultado >= 6:
                                valorprecargado = 5
                        else:
                            variableoculta = 1
                    if codrubrica == 573:
                        sql = """select sil.materia_id,count(distinct tar.id) as total
                                    from sga_diapositivasilabosemanal tar,sga_silabosemanal semanal,sga_silabo sil
                                    where tar.silabosemanal_id=semanal.id
                                    and semanal.silabo_id=sil.id
                                    and tar."status"=True
                                    and semanal."status"=True
                                    and sil."status"=True
                                    and tar.estado_id=4
                                    and sil.materia_id in(
                                    select proma.materia_id from sga_profesormateria proma,sga_materia mate,sga_nivel ni
                                    where proma.materia_id=mate.id
                                    and mate.nivel_id=ni.id
                                    and proma."status"=True
                                    and mate."status"=True
                                    and ni."status"=True
                                    and ni.periodo_id=112
                                    and proma.profesor_id=%s
                                    and proma.tipoprofesor_id in(1,11,12))
                                    and semanal.fechafinciosemana <='%s'
                                    group by sil.materia_id
                                                        """ % (codiprofe, fechaevaluacion)
                        cursor.execute(sql)
                        results = cursor.fetchall()
                        contadorasistencias = 0
                        contadortotal = 0
                        if results:
                            for r in results:
                                contadortotal = contadortotal + 1
                                contadorasistencias = contadorasistencias + r[1]
                            resultado = round((contadorasistencias / contadortotal),0)
                        else:
                            resultado = 1
                        valorprecargado = 0
                        if resultado <= 2:
                            valorprecargado = 1
                        if resultado == 3:
                            valorprecargado = 2
                        if resultado == 4:
                            valorprecargado = 3
                        if resultado == 5:
                            valorprecargado = 4
                        if resultado >= 6:
                            valorprecargado = 5
                    if codrubrica == 575:
                        sql = """select sil.materia_id,count(distinct tar.id) as total
                                    from sga_tareapracticasilabosemanal tar,sga_silabosemanal semanal,sga_silabo sil
                                    where tar.silabosemanal_id=semanal.id
                                    and semanal.silabo_id=sil.id
                                    and tar."status"=True
                                    and semanal."status"=True
                                    and sil."status"=True
                                    and tar.estado_id=4
                                    and sil.materia_id in(
                                    select proma.materia_id from sga_profesormateria proma,sga_materia mate,sga_nivel ni
                                    where proma.materia_id=mate.id
                                    and mate.nivel_id=ni.id
                                    and proma."status"=True
                                    and mate."status"=True
                                    and ni."status"=True
                                    and ni.periodo_id=112
                                    and proma.profesor_id=%s
                                    and proma.tipoprofesor_id in(1,11,12))
                                    and semanal.fechafinciosemana <='%s'
                                    group by sil.materia_id
                                                        """ % (codiprofe, fechaevaluacion)
                        cursor.execute(sql)
                        results = cursor.fetchall()
                        contadorasistencias = 0
                        contadortotal = 0
                        if results:
                            for r in results:
                                contadortotal = contadortotal + 1
                                contadorasistencias = contadorasistencias + r[1]
                            resultado = round((contadorasistencias / contadortotal),0)
                        else:
                            resultado = 1
                            variableoculta = 1
                        valorprecargado = 0
                        if resultado <= 1:
                            valorprecargado = 1
                        if resultado == 2:
                            valorprecargado = 3
                        if resultado >= 3:
                            valorprecargado = 5
                    if codrubrica == 577:
                        if ProfesorMateria.objects.filter(materia__nivel__periodo_id=112, tipoprofesor_id=12, profesor_id=codiprofe, status=True).exists():
                            sql = """select sil.materia_id,count(distinct tar.id) as total
                                        from sga_guiaestudiantesilabosemanal tar,sga_silabosemanal semanal,sga_silabo sil
                                        where tar.silabosemanal_id=semanal.id
                                        and semanal.silabo_id=sil.id
                                        and tar."status"=True
                                        and semanal."status"=True
                                        and sil."status"=True
                                        and tar.estado_id=4
                                        and sil.materia_id in(
                                        select proma.materia_id from sga_profesormateria proma,sga_materia mate,sga_nivel ni
                                        where proma.materia_id=mate.id
                                        and mate.nivel_id=ni.id
                                        and proma."status"=True
                                        and mate."status"=True
                                        and ni."status"=True
                                        and ni.periodo_id=112
                                        and proma.profesor_id=%s
                                        and proma.tipoprofesor_id in(1,11,12))
                                        and semanal.fechafinciosemana <='%s'
                                        group by sil.materia_id
                                                            """ % (codiprofe, fechaevaluacion)
                            cursor.execute(sql)
                            results = cursor.fetchall()
                            contadorasistencias = 0
                            contadortotal = 0
                            if results:
                                for r in results:
                                    contadortotal = contadortotal + 1
                                    contadorasistencias = contadorasistencias + r[1]
                                resultado = round((contadorasistencias / contadortotal),0)
                            else:
                                resultado = 1
                            valorprecargado = 0
                            if resultado <= 1:
                                valorprecargado = 1
                            if resultado == 2:
                                valorprecargado = 3
                            if resultado >= 3:
                                valorprecargado = 5
                        else:
                            variableoculta = 1
                    return JsonResponse({'result': 'ok', "valor": valorprecargado, "oculta": variableoculta})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'validacionesrubricas':
                try:
                    idrubrica = int(request.POST['idrubrica'])
                    if idrubrica == 567:
                        itemselect = 3
                    return JsonResponse({'result': 'ok', 'itemselect': itemselect})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})


            if action == 'listacontinua':
                try:
                    combomejoras = CriterioTipoObservacionEvaluacion.objects.get(pk=request.POST['id'])
                    tipoinstrumento = request.POST['tipoins']
                    lista = []
                    for detmejoras in combomejoras.tipoobservacionevaluacion_set.filter(tipoinstrumento=tipoinstrumento, tipo=2, status=True, activo=True).order_by('nombre'):
                        lista.append([detmejoras.id, detmejoras.nombre.upper()])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'seguimientosilabo':
                try:
                    data['title'] = u'Seguimiento de sílabo'
                    if 'id' in request.POST:
                        data['title'] = u'Seguimiento de Sílabo'
                        materia = Materia.objects.get(pk=request.POST['id'])
                        data['silabo'] = materia.silabo_actual()
                        data['profesormateria'] = ProfesorMateria.objects.filter(materia=materia, status=True)[0]
                        silabo = materia.silabo_actual()
                        data['semanas'] = silabo.silabosemanal_set.filter(status=True).order_by('numsemana')
                        template = get_template("pro_personaevaluacion/seguimientosilabo.html")
                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            if action == 'detalleaprobacion':
                try:
                    data['silabo'] = silabo = Silabo.objects.get(pk=int(request.POST['id']))
                    data['historialaprobacion'] = silabo.aprobarsilabo_set.filter(status=True).order_by('-id').exclude(estadoaprobacion=variable_valor('PENDIENTE_SILABO'))
                    data['aprobar'] = variable_valor('APROBAR_SILABO')
                    data['rechazar'] = variable_valor('RECHAZAR_SILABO')
                    data['pendiente'] = variable_valor('PENDIENTE_SILABO')
                    template = get_template("pro_personaevaluacion/detalleaprobacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                    pass

            if action == 'programaanalitico_pdf':
                try:
                    materia = Materia.objects.get(pk=request.POST['id'])
                    data['proanalitico'] = pro = materia.asignaturamalla.programaanaliticoasignatura_set.filter(status=True, activo=True)[0]
                    return conviert_html_to_pdf(
                        'mallas/programanalitico_pdf.html',
                        {
                            'pagesize': 'A4',
                            'data': pro.plananalitico_pdf(periodo),
                        }
                    )
                except Exception as ex:
                    pass

            if action == 'mostrarsilabodigital':
                try:
                    if 'idm' in request.POST:
                        data['silabo'] = silabo = Silabo.objects.get(materia_id=int(request.POST['idm']), status=True, profesor=int(request.POST['idp']))
                        return  conviert_html_to_pdf(
                            'pro_planificacion/silabo_pdf.html',
                            {
                                'pagesize': 'A4',
                                'data': silabo.silabo_pdf(),
                            }
                        )
                except Exception as ex:
                    pass

            elif action == 'informedocente':
                mensaje = "Problemas al generar el informe de actividades."
                try:
                    profesordistributivo = ProfesorDistributivoHoras.objects.get(pk=int(encrypt(request.POST['idd'])))
                    fechaini = request.POST['fini']
                    cadena = fechaini.split('-')
                    fechaini = cadena[2] + '-' + cadena[1] + '-' + cadena[0]
                    fechaffin = request.POST['ffin']
                    cadena = fechaffin.split('-')
                    fechaffin = cadena[2] + '-' + cadena[1] + '-' + cadena[0]
                    return conviert_html_to_pdf('adm_criteriosactividadesdocente/informe_actividad_docente_pdf.html', {'pagesize': 'A4','data': profesordistributivo.profesor.informe_actividades_mensual_docente(periodo, fechaini, fechaffin, 'TODO')})
                except Exception as ex:
                    return HttpResponseRedirect("/pro_personaevaluacion?info=%s" % mensaje)

            elif action == 'informe_seguimiento_general':
                mensaje = "Problemas al generar el informe"
                try:
                    materias = []
                    lista1 = ""
                    listacarreras = []
                    coord = 0
                    suma = 0
                    coordinacion = None
                    profesormateria = None
                    finio = request.POST['fini']
                    ffino = request.POST['ffin']
                    finic = finio
                    ffinc = ffino
                    opcionreport = int(request.POST['opcionreport'])
                    profesor = Profesor.objects.get(id=int(encrypt(request.POST['idprof'])))
                    # 1: grado virtual
                    if opcionreport == 1:
                        profesormateria = ProfesorMateria.objects.filter(profesor=profesor,
                                                                         materia__nivel__modalidad_id=3,
                                                                         materia__nivel__periodo=periodo,
                                                                         activo=True).exclude(
                            materia__nivel__nivellibrecoordinacion__coordinacion_id=9).distinct().order_by('desde',
                                                                                                           'materia__asignatura__nombre')
                    # 2 virtual admision
                    if opcionreport == 2:
                        coord = 9
                        profesormateria = ProfesorMateria.objects.filter(profesor=profesor,
                                                                         materia__nivel__modalidad_id=3,
                                                                         materia__nivel__periodo=periodo, activo=True,
                                                                         materia__nivel__nivellibrecoordinacion__coordinacion_id=9).distinct().order_by(
                            'desde', 'materia__asignatura__nombre')
                        # coordinacion = profesormateria[0].materia.carrera.coordinacionvalida
                    # 3 presencial admision
                    if opcionreport == 3:
                        coord = 9
                        profesormateria = ProfesorMateria.objects.filter(profesor=profesor,
                                                                         materia__nivel__periodo=periodo,
                                                                         activo=True,
                                                                         materia__nivel__nivellibrecoordinacion__coordinacion_id=9).exclude(
                            materia__nivel__modalidad_id=3).distinct().order_by('desde', 'materia__asignatura__nombre')
                        # coordinacion = profesormateria[0].materia.carrera.coordinacionvalida
                    if profesormateria:
                        suma = profesormateria.aggregate(total=Sum('hora'))['total']
                        lista = []
                        for x in profesormateria:
                            materias.append(x.materia)
                            if x.materia.carrera():
                                carrera = x.materia.carrera()
                                if not carrera in listacarreras:
                                    listacarreras.append(carrera)
                                lista.append(carrera)
                        cuenta1 = collections.Counter(lista).most_common(1)
                        carrera = cuenta1[0][0]
                        coordinacion = carrera.coordinacionvalida
                        matriculados = MateriaAsignada.objects.filter(materiaasignadaretiro__isnull=True,
                                                                      matricula__estado_matricula__in=[2,3],
                                                                      materia__id__in=profesormateria.values_list(
                                                                          'materia__id', flat=True)).distinct()
                        for x in matriculados:
                            if x.id != matriculados.order_by('-id')[0].id:
                                if x.matricula.inscripcion.persona.idusermoodle:
                                    lista1 += str(x.matricula.inscripcion.persona.idusermoodle) + ","
                            else:
                                lista1 += str(x.matricula.inscripcion.persona.idusermoodle)
                    distributivo = \
                        ProfesorDistributivoHoras.objects.filter(periodo=periodo, profesor=profesor, status=True)[
                            0] if ProfesorDistributivoHoras.objects.filter(periodo=periodo, profesor=profesor,
                                                                           status=True).exists() else None
                    titulaciones = distributivo.profesor.persona.mis_titulaciones()
                    titulaciones = titulaciones.filter(titulo__nivel_id__in=[3, 4])
                    if opcionreport == 3:
                        # asistencia
                        asistencias_registradas = 0
                        asistencias_no_registradas = 0
                        asistencias_dias_feriados = 0
                        asistencias_dias_suspension = 0
                        resultado = []
                        fechas_clases = []
                        lista_clases_dia_x_fecha = []
                        for profesormate in profesormateria:
                            data_asistencia = profesormate.asistencia_docente(finic, ffinc, periodo, True,
                                                                              lista_clases_dia_x_fecha)
                            asistencias_registradas += data_asistencia['total_asistencias_registradas']
                            asistencias_no_registradas += data_asistencia['total_asistencias_no_registradas']
                            asistencias_dias_feriados += data_asistencia['total_asistencias_dias_feriados']
                            asistencias_dias_suspension += data_asistencia['total_asistencias_dias_suspension']
                            lista_clases_dia_x_fecha = data_asistencia['lista_clases_dia_x_fecha']
                            for fecha_clase in data_asistencia['lista_fechas_clases']:
                                if (fecha_clase in fechas_clases) == 0:
                                    fechas_clases.append(fecha_clase)

                        # marcadas
                        marcadas = None
                        marcadas = LogDia.objects.filter(persona=distributivo.profesor.persona, fecha__in=fechas_clases,
                                                         status=True).order_by('fecha')
                        total = None
                        i = 0
                        subtotal = None
                        totalfinal = 0
                        if marcadas:
                            for m in marcadas:
                                if m.procesado:
                                    i = i + 1
                                    logmarcada = m.logmarcada_set.filter(status=True).order_by('time')
                                    if logmarcada.count() >= 2:
                                        horas1 = logmarcada[0]
                                        horas2 = logmarcada[1]
                                        formato = "%H:%M:%S"
                                        subtotal = datetime.strptime(str(horas2.time.time()),
                                                                     formato) - datetime.strptime(
                                            str(horas1.time.time()), formato)
                                        if logmarcada.count() == 4:
                                            horas3 = logmarcada[2]
                                            horas4 = logmarcada[3]
                                            subtotal += datetime.strptime(str(horas4.time.time()),
                                                                          formato) - datetime.strptime(
                                                str(horas3.time.time()), formato)
                                        if i == 1:
                                            total = subtotal
                                        else:
                                            total = total + subtotal
                        if total:
                            sec = total.total_seconds()
                            hours = sec // 3600
                            minutes = (sec // 60) - (hours * 60)
                            totalfinal = str(int(hours)) + ':' + str(int(minutes)) + ': 00'
                        # -------------------------------------------------------------
                        porcentaje = 0
                        # asistencias_reg = asistencias_registradas + asistencias_dias_feriados + asistencias_dias_suspension
                        asistencias_reg = asistencias_registradas
                        if (asistencias_reg + asistencias_no_registradas) > 0:
                            porcentaje = Decimal(
                                ((asistencias_reg * 100) / (asistencias_reg + asistencias_no_registradas))).quantize(
                                Decimal('.01'))
                        resultado.append((asistencias_reg, asistencias_no_registradas, porcentaje))
                    return conviert_html_to_pdf('pro_cronograma/informe_seguimiento.html', {'pagesize': 'A4',
                                                                                            'data': {
                                                                                                'distributivo': distributivo,
                                                                                                'periodo': periodo,
                                                                                                'fini': finio,
                                                                                                'ffin': ffino,
                                                                                                'finic': finic,
                                                                                                'ffinc': ffinc,
                                                                                                'suma': suma,
                                                                                                'materias': materias,
                                                                                                'titulaciones': titulaciones,
                                                                                                'opcionreport': opcionreport,
                                                                                                'resultado': resultado if opcionreport == 3 else None,
                                                                                                'coord': coord,
                                                                                                'coordinacion': coordinacion,
                                                                                                'listacarreras': listacarreras,
                                                                                                'lista': lista1}})
                except Exception as ex:
                    return HttpResponseRedirect("/adm_criteriosactividadesdocente?info=%s" % mensaje)

            elif action == 'detalletarea':
                try:
                    tipo = int(request.POST['codtipo'])
                    if tipo == 1:
                        data['tarea'] = tarea = TareaSilaboSemanal.objects.get(pk=int(request.POST['idtar']))
                        data['historialaprobacion'] = tarea.historialaprobaciontarea_set.filter(status=True).order_by('id')
                        template = get_template("aprobar_silabo/detalletarea.html")
                    if tipo == 2:
                        data['foro'] = foro = ForoSilaboSemanal.objects.get(pk=int(request.POST['idtar']))
                        data['historialaprobacion'] = foro.historialaprobacionforo_set.filter(status=True).order_by('id')
                        template = get_template("aprobar_silabo/detalleforo.html")
                    if tipo == 3:
                        data['test'] = test = TestSilaboSemanal.objects.get(pk=int(request.POST['idtar']))
                        data['historialaprobacion'] = test.historialaprobaciontest_set.filter(status=True).order_by('id')
                        template = get_template("aprobar_silabo/detalletest.html")
                    if tipo == 4:
                        data['guiaestudiante'] = guiaestudiante = GuiaEstudianteSilaboSemanal.objects.get(pk=int(request.POST['idtar']))
                        data['historialaprobacion'] = guiaestudiante.historialaprobacionguiaestudiante_set.filter(status=True).order_by('id')
                        template = get_template("aprobar_silabo/detalleguiaestudiante.html")
                    if tipo == 5:
                        data['guiadocente'] = guiadocente = GuiaDocenteSilaboSemanal.objects.get(pk=int(request.POST['idtar']))
                        data['historialaprobacion'] = guiadocente.historialaprobacionguiadocente_set.filter(status=True).order_by('id')
                        template = get_template("aprobar_silabo/detalleguiadocente.html")
                    if tipo == 6:
                        data['diapositiva'] = diapositiva = DiapositivaSilaboSemanal.objects.get(pk=int(request.POST['idtar']))
                        data['historialaprobacion'] = diapositiva.historialaprobaciondiapositiva_set.filter(status=True).order_by('id')
                        template = get_template("aprobar_silabo/detallediapositiva.html")
                    if tipo == 7:
                        data['title'] = u'Evidencia Practicas'
                        data['form'] = CompendioPlagioForm
                        # data['id'] = request.GET['id']
                        # data['idevidencia'] = request.GET['idevidencia']
                        data['compendio'] = compendio = CompendioSilaboSemanal.objects.get(pk=int(request.POST['idtar']))
                        data['historialaprobacion'] = compendio.historialaprobacioncompendio_set.filter(status=True).order_by('id')
                        template = get_template("aprobar_silabo/detallecompendio.html")
                    if tipo == 8:
                        data['material'] = material = MaterialAdicionalSilaboSemanal.objects.get(pk=int(request.POST['idtar']))
                        data['historialaprobacion'] = material.historialaprobacionmaterial_set.filter(status=True).order_by('id')
                        template = get_template("aprobar_silabo/detallematerial.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                    pass

            elif action == 'evidenciasilabos_pdf':
                try:
                    evaluado = Persona.objects.get(pk=int(request.POST['idpersona']))
                    evidencias = evidenciassilabosxcarrera(periodo, evaluado)
                    return evidencias
                except Exception as ex:
                    pass

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'evaluar':
                try:
                    data['title'] = u'Evaluación del profesor'
                    data['profesor'] = profesor = Profesor.objects.get(pk=int(request.GET['id']))
                    data['tipoinstrumento'] = tipo = int(request.GET['t'])

                    materia = None
                    if 'idm' in request.GET:
                        data['materia'] = materia = Materia.objects.get(pk=int(request.GET['idm']))

                    # data['combomejoras'] = TipoObservacionEvaluacion.objects.filter(tipoinstrumento=3, tipo=1, status=True).order_by('nombre')
                    data['combomejoras'] = CriterioTipoObservacionEvaluacion.objects.filter(tipoobservacionevaluacion__tipoinstrumento=tipo, tipoobservacionevaluacion__tipo=1, tipoobservacionevaluacion__status=True,tipoobservacionevaluacion__activo=True).order_by('nombre').distinct()
                    # data['combocontinuas'] = TipoObservacionEvaluacion.objects.filter(tipoinstrumento=3, tipo=2, status=True).order_by('nombre')
                    data['combocontinuas'] = CriterioTipoObservacionEvaluacion.objects.filter(tipoobservacionevaluacion__tipoinstrumento=tipo, tipoobservacionevaluacion__tipo=2, tipoobservacionevaluacion__status=True,tipoobservacionevaluacion__activo=True).order_by('nombre').distinct()
                    if tipo == 3:
                        data['rubricas'] = rubricas = profesor.mis_rubricas_par(periodo, persona)
                        data['actividadespar'] = persona.mis_actividades_par(profesor, proceso)
                    if tipo == 4:
                        if proceso.versioninstrumentodirectivo == 2:
                            if proceso.periodo.tipo.id == 3:
                                estado = True
                                resultados = RespuestaEvaluacionAcreditacionPosgrado.objects.values('evaluador_id').filter(
                                    status=True,
                                    tipoinstrumento=4,
                                    proceso__periodo=periodo,
                                    profesor=profesor,
                                    materia=materia,
                                    respuestarubricaposgrado__rubrica__para_directivo=True).exclude(respuestarubricaposgrado__rubrica__rvigente=True)
                                if resultados.exists():
                                    estado = False

                                lista1 = Rubrica.objects.filter(habilitado=True,
                                                                proceso__periodo=periodo,
                                                                para_directivo=True, rvigente=estado).distinct()

                                data['rubricas'] = rubricas = lista1
                            else:
                                data['rubricas'] = rubricas = profesor.mis_rubricas_directivo_par(periodo, persona)
                        else:
                            data['rubricas'] = rubricas = profesor.mis_rubricas_directivo(periodo)
                    if tipo == 5:
                        tipoprofe = int(request.GET['tipoprofe'])
                        data['rubricas'] = rubricas = profesor.mis_rubricas_directivorevision(periodo,tipoprofe)
                    data['tiene_docencia'] = rubricas.filter(tipo_criterio=1).exists()
                    data['tiene_investigacion'] = rubricas.filter(tipo_criterio=2).exists()
                    data['tiene_gestion'] = rubricas.filter(tipo_criterio=3).exists()

                    if periodo.tipo.id == 3:
                        return render(request, "pro_personaevaluacion/evaluarposgrado.html", data)
                    elif tipo == 5:
                        data['tipoprofe'] = int(request.GET['tipoprofe'])
                        data['codimate'] = int(request.GET['codimate'])
                        return render(request, "pro_personaevaluacion/evaluarrevision.html", data)
                    else:
                        return render(request, "pro_personaevaluacion/evaluar.html", data)
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
                    template = get_template("pro_personaevaluacion/modal/detallecalses.html")
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
                        template = get_template("pro_personaevaluacion/modal/detalleresumen.html")
                    elif request.GET['flag'] == 'asistencias':
                        template = get_template("pro_personaevaluacion/modal/detalleasistencias.html")
                    else:
                        template = get_template("pro_personaevaluacion/modal/detalleactividadesdocente.html")
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
                    template = get_template("pro_personaevaluacion/modal/detalleplananalitico.html")
                    return JsonResponse({"result": "ok", 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'verpublicaciones':
                try:
                    data['title'] = u'Publicaciones de Articulos'
                    data['profesor'] = profesorpub = Profesor.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['articulos'] = ArticuloInvestigacion.objects.select_related().filter(participantesarticulos__profesor__persona=profesorpub.persona, status=True, participantesarticulos__status=True).order_by('revista__nombre', 'numero', 'nombre')
                    data['ponencias'] = PonenciasInvestigacion.objects.select_related().filter(participanteponencias__profesor__persona=profesorpub.persona, status=True, participanteponencias__status=True)
                    data['capitulolibro'] = CapituloLibroInvestigacion.objects.select_related().filter(participantecapitulolibros__profesor__persona=profesorpub.persona, status=True, participantecapitulolibros__status=True)
                    data['libros'] = LibroInvestigacion.objects.select_related().filter(participantelibros__profesor__persona=profesorpub.persona, status=True, participantelibros__status=True)
                    return render(request, "pro_personaevaluacion/publicaciones.html", data)
                except Exception as ex:
                    pass

            elif action == 'listacomplementarias':
                try:
                    data['title'] = u'Actividades Complementarias'
                    idprofesor = int(encrypt(request.GET['profesorid']))
                    data['actividades'] = actividad = PaeActividadesPeriodoAreas.objects.filter((Q(paefechaactividad__tutor_id=idprofesor) | Q(tutorprincipal_id=idprofesor)), periodoarea__periodo=periodo, status=True, paefechaactividad__status=True).order_by('nombre').distinct()
                    data['profesor'] = profesor = Profesor.objects.get(pk=idprofesor)
                    return render(request, "pro_personaevaluacion/listacomplementarias.html", data)
                except Exception as ex:
                    pass

            elif action == 'listacursos':
                try:
                    data['title'] = u'Actividades Complementarias'
                    data['profesor'] = profesor = Profesor.objects.get(pk=int(request.GET['profesorid']))
                    data['materiascursos'] = MateriaCursoEscuelaComplementaria.objects.filter(fecha_fin__year=(datetime.now().year), profesor=profesor).distinct().order_by('-fecha_inicio')
                    return render(request, "pro_personaevaluacion/listacursos.html", data)
                except Exception as ex:
                    pass

            elif action == 'tutoriasexamencomplexivo':
                try:
                    data['title'] = u'Tutoria de examen complexivo'
                    data['profesor'] = profesor = Profesor.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['grupos'] = ComplexivoGrupoTematica.objects.filter(status=True, tematica__tutor__participante__persona__id=profesor.persona.id, tematica__periodo__fechainicio__gte=periodo.inicio, tematica__periodo__fechainicio__lte=periodo.fin).order_by('tematica__tematica__tema')
                    # data['materiascursos'] = MateriaCursoEscuelaComplementaria.objects.filter(fecha_fin__year=(datetime.now().year), profesor=profesor).distinct().order_by('-fecha_inicio')
                    return render(request, "pro_personaevaluacion/vertutoriaexamencomplexivo.html", data)
                except Exception as ex:
                    pass

            elif action == 'listasilabos':
                try:
                    data['title'] = u'Planificación de tareas y actividades del profesor'
                    persona = request.session['persona']
                    data['profesor'] = profesor = Profesor.objects.get(pk=int(request.GET['profesorid']))
                    # if PermisoPeriodo.objects.filter(periodo=periodo).exists():
                    data['permiso'] = True
                    # else:
                    #     data['permiso'] = False

                    data['materias'] = materia = Materia.objects.filter(profesormateria__profesor=profesor,
                                                                        profesormateria__principal=True,
                                                                        nivel__periodo=periodo,
                                                                        nivel__periodo__visible=True).distinct().order_by('asignatura')
                    data['matriculacion_libre'] = MATRICULACION_LIBRE
                    data['ver_silabo_malla'] = VER_SILABO_MALLA
                    data['ver_plan_estudio'] = VER_PLAN_ESTUDIO
                    return render(request, "pro_personaevaluacion/listasilabos.html", data)
                except Exception as ex:
                    pass

            elif action == 'listar_silabos':
                try:
                    data['title'] = u'Sílabo de digital'
                    if 'id' in request.GET:
                        data['materia'] = materia = Materia.objects.get(pk=int(request.GET['id']))
                        data['pidencrip'] = request.GET['pid']
                        data['silabos'] = materia.silabo_set.filter(status=True).order_by('fecha_creacion')
                        data['aprobar'] = variable_valor('APROBAR_SILABO')
                        data['rechazar'] = variable_valor('RECHAZAR_SILABO')
                        data['pendiente'] = variable_valor('PENDIENTE_SILABO')
                        template = get_template("pro_personaevaluacion/silabodigital.html")
                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'listadopoa':
                try:
                    data['title'] = u'Informes POA'
                    consultadirector = None
                    # d=periodo.fin.year
                    data['profesordir'] = personadir = Persona.objects.get(pk=int(request.GET['personaid']))
                    if InformeGenerado.objects.filter(personadirector=personadir ,periodopoa__ingresar=True, status=True, periodopoa__anio=periodo.fin.year):
                        consultadirector = InformeGenerado.objects.filter(personadirector=personadir, periodopoa__ingresar=True, status=True, periodopoa__anio=periodo.fin.year).order_by('mes','tipo')
                    if InformeGenerado.objects.filter(personacarrera=personadir, status=True, periodopoa__ingresar=True, periodopoa__anio=periodo.fin.year):
                        if not consultadirector:
                            consultadirector = InformeGenerado.objects.filter(personacarrera=personadir, periodopoa__ingresar=True, status=True, periodopoa__anio=periodo.fin.year).order_by('mes', 'tipo')
                        else:
                            consultadirector = InformeGenerado.objects.filter(personacarrera=personadir, periodopoa__ingresar=True, status=True, periodopoa__anio=periodo.fin.year).order_by('mes', 'tipo')
                            # consultadirector = InformeGenerado.objects.filter(personacarrera=personadir, periodopoa__ingresar=True, status=True, periodopoa__anio=periodo.fin.year).order_by('mes', 'tipo') | consultadirector
                    data['informenespoa'] = consultadirector
                    return render(request, "pro_personaevaluacion/listadopoa.html", data)
                except Exception as ex:
                    pass

            elif action == 'veratividades':
                try:
                    data['title'] = u'Ver Actividades'
                    periodo = request.session['periodo']
                    data['iddetallepar'] = request.GET['iddetallepar']
                    data['profesor'] = profesor = Profesor.objects.get(pk=int(request.GET['id']))
                    data['iddetallepares'] = ActividadDetalleInstrumentoPar.objects.values_list('detalledistributivo', flat=True).filter(detallepar_id=request.GET['iddetallepar'])
                    data['distributivo_horas'] = profesor.distributivohoraseval(periodo)
                    return render(request, "pro_personaevaluacion/veractividades.html", data)
                except Exception as ex:
                    pass

            elif action == 'veratividadesdirectivos':
                try:
                    data['title'] = u'Ver Actividades'
                    periodo = request.session['periodo']
                    data['profesor'] = profesor = Profesor.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['iddetallepares'] = DetalleDistributivo.objects.values_list('id', flat=True).filter(distributivo__profesor=profesor,distributivo__periodo=periodo,status=True,distributivo__status=True).distinct()
                    data['distributivo_horas'] = profesor.distributivohoraseval(periodo)
                    # ASISTENCIA DOCENTE
                    fini = periodo.inicio
                    if periodo.fin >= datetime.now().date():
                        ffin = datetime.now().date() - timedelta(days=1)
                    else:
                        ffin = periodo.fin
                    data['fini'] = fini
                    data['ffin'] = ffin
                    data['distributivo'] = ProfesorDistributivoHoras.objects.get(periodo=periodo, profesor=profesor)
                    data['profesormaterias'] = profesormateria = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__periodo=periodo, tipoprofesor_id__in=[1, 2, 5, 6]).distinct().order_by('desde', 'materia__asignatura__nombre')
                    asistencias_registradas = 0
                    asistencias_no_registradas = 0
                    asistencias_dias_feriados = 0
                    asistencias_dias_suspension = 0
                    resultado = []
                    fechas_clases = []
                    for profesormate in profesormateria:
                        data_asistencia = profesormate.asistencia_docente(fini, ffin, periodo)
                        asistencias_registradas += data_asistencia['total_asistencias_registradas']
                        asistencias_no_registradas += data_asistencia['total_asistencias_no_registradas']
                        asistencias_dias_feriados += data_asistencia['total_asistencias_dias_feriados']
                        asistencias_dias_suspension += data_asistencia['total_asistencias_dias_suspension']
                        for fecha_clase in data_asistencia['lista_fechas_clases']:
                            if (fecha_clase in fechas_clases) == 0:
                                fechas_clases.append(fecha_clase)
                    porcentaje = 0
                    asistencias_reg = asistencias_registradas + asistencias_dias_feriados + asistencias_dias_suspension
                    if (asistencias_reg + asistencias_no_registradas) > 0:
                        porcentaje = Decimal(((asistencias_reg * 100) / (asistencias_reg + asistencias_no_registradas))).quantize( Decimal('.01'))
                    resultado.append((asistencias_reg, asistencias_no_registradas, porcentaje))
                    data['resultado'] = resultado
                    data['usamoodle'] = periodo.usa_moodle
                    return render(request, "pro_personaevaluacion/veractividades.html", data)
                except Exception as ex:
                    pass

            elif action == 'veratividadesdirectivosnew':
                try:
                    data['title'] = u'Ver Actividades'
                    data['tipoevi'] = int(encrypt(request.GET['tipoevi']))
                    periodo = request.session['periodo']
                    data['CRITERIO_IMPARTICION_CLASE_ID'] = variable_valor('CRITERIO_IMPARTICION_CLASE_ID')
                    data['profesor'] = profesor = Profesor.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['iddetallepares'] = DetalleDistributivo.objects.values_list('id', flat=True).filter(distributivo__profesor=profesor,distributivo__periodo=periodo,status=True,distributivo__status=True).distinct()
                    data['tutoriaspracticas'] = PracticasPreprofesionalesInscripcion.objects.filter(status=True, tutorunemi=profesor, culminada=False).distinct().exclude(estadosolicitud=3).count()
                    data['distributivo_horas'] = profesor.distributivohoraseval(periodo)
                    # VER LISTADO DE ACTIVIDADES EVALUADOR

                    data['evaluador'] = persona.detalleinstrumentoevaluacionparacreditacion_set.filter(proceso=proceso,
                                                                                                       evaluado=profesor,
                                                                                                       status=True).first()
                    data['evaluadirec'] = persona.detalleinstrumentoevaluaciondirectivoacreditacion_set.filter(
                        proceso=proceso, evaluado=profesor, status=True).first()
                    # ASISTENCIA DOCENTE
                    fini = periodo.inicio
                    if periodo.fin >= datetime.now().date():
                        ffin = datetime.now().date() - timedelta(days=1)
                    else:
                        ffin = periodo.fin
                    data['fini'] = fini
                    data['ffin'] = ffin
                    data['persona'] = persona
                    data['distributivo'] = ProfesorDistributivoHoras.objects.get(periodo=periodo, profesor=profesor)
                    data['modalidadpresencial'] = [1, 2]
                    data['nopedirevidencia'] = [37, 9, 106, 30, 1, 4, 15, 16, 21, 4, 3, 99, 105, 61, 7, 53, 81]
                    data['modalidadlinea'] = [3]
                    data['reporte_11'] = obtener_reporte('evidencias_distributivo')
                    return render(request, "pro_personaevaluacion/veratividadesdirectivosnew.html", data)
                except Exception as ex:
                    pass

            elif action == 'veratividadesdirectivos_posgrado':
                try:
                    data['title'] = u'Ver Actividades'
                    data['tipoevi'] = int(encrypt(request.GET['tipoevi']))
                    periodo = request.session['periodo']
                    data['CRITERIO_IMPARTICION_CLASE_ID'] = variable_valor('CRITERIO_IMPARTICION_CLASE_ID')
                    data['profesor'] = profesor = Profesor.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['materia'] = materia = Materia.objects.get(pk=int(encrypt(request.GET['idm'])))
                    data['iddetallepares'] = DetalleDistributivo.objects.values_list('id', flat=True).filter(distributivo__profesor=profesor,distributivo__periodo=periodo,status=True,distributivo__status=True).distinct()
                    data['tutoriaspracticas'] = PracticasPreprofesionalesInscripcion.objects.filter(status=True, tutorunemi=profesor, culminada=False).distinct().exclude(estadosolicitud=3).count()
                    data['distributivo_horas'] = profesor.distributivohoraseval(periodo)
                    # ASISTENCIA DOCENTE
                    fini = periodo.inicio
                    if periodo.fin >= datetime.now().date():
                        ffin = datetime.now().date() - timedelta(days=1)
                    else:
                        ffin = periodo.fin
                    data['fini'] = fini
                    data['ffin'] = ffin
                    data['persona'] = persona
                    # data['distributivo'] = ProfesorDistributivoHoras.objects.get(periodo=periodo, profesor=profesor)
                    data['distributivo'] = ProfesorDistributivoHoras.objects.filter(periodo=periodo, profesor=profesor).first()
                    data['modalidadpresencial'] = [1, 2]
                    data['nopedirevidencia'] = [37, 9, 106, 30, 1, 4, 15, 16, 21, 4, 3, 99, 105, 61, 7, 53, 81]
                    data['modalidadlinea'] = [3]
                    data['reporte_11'] = obtener_reporte('evidencias_distributivo')
                    return render(request, "pro_personaevaluacion/veratividadesdirectivosnew.html", data)
                except Exception as ex:
                    pass

            elif action == 'verrecursosposgrado':
                try:
                    data['title'] = u'Ver Actividades'
                    data['profesor'] = eProfesor = Profesor.objects.get(status=True, pk=int(encrypt(request.GET['profesorid'])))
                    data['materia'] = eMateria = Materia.objects.get(status=True, pk=int(encrypt(request.GET['materiaid'])))

                    eSemanas = []
                    for semana in eMateria.silabo_actual().listado_semanal():
                        eDiapositiva = eCompendio = eVideoMagistral = eMaterialAdicional = eGuiaEstudiante = eTest = \
                            eTaller = eExposicion = eForo = eTarea = eAnalisis = eTrabajo = None
                        if DiapositivaSilaboSemanal.objects.filter(status=True, silabosemanal=semana).exists():
                            eDiapositiva = DiapositivaSilaboSemanal.objects.filter(status=True, silabosemanal=semana).order_by('-id').first()
                        if CompendioSilaboSemanal.objects.filter(status=True, silabosemanal=semana).exists():
                            eCompendio = CompendioSilaboSemanal.objects.filter(status=True, silabosemanal=semana).order_by('-id').first()
                        if VideoMagistralSilaboSemanal.objects.filter(status=True, silabosemanal=semana).exists():
                            eVideoMagistral = VideoMagistralSilaboSemanal.objects.filter(status=True, silabosemanal=semana).order_by('-id').first()
                        if MaterialAdicionalSilaboSemanal.objects.filter(status=True, silabosemanal=semana).exists():
                            eMaterialAdicional = MaterialAdicionalSilaboSemanal.objects.filter(status=True, silabosemanal=semana).order_by('-id')
                        if GuiaEstudianteSilaboSemanal.objects.filter(status=True, silabosemanal=semana).exists():
                            eGuiaEstudiante = GuiaEstudianteSilaboSemanal.objects.filter(status=True, silabosemanal=semana).order_by('-id').first()
                        #ACD
                        if TestSilaboSemanal.objects.filter(status=True, silabosemanal=semana).exists():
                            eTest = TestSilaboSemanal.objects.filter(status=True, silabosemanal=semana).order_by('-id')
                        if TareaSilaboSemanal.objects.filter(status=True, silabosemanal=semana, nombre__icontains='TALLER_').exists():
                            eTaller = TareaSilaboSemanal.objects.filter(status=True, silabosemanal=semana, nombre__icontains='TALLER_').order_by('-id')
                        if TareaSilaboSemanal.objects.filter(status=True, silabosemanal=semana, nombre__icontains='TALLER_').exists():
                            eExposicion = TareaSilaboSemanal.objects.filter(status=True, silabosemanal=semana, nombre__icontains='EXPOSICIÓN_').order_by('-id')
                        #AA
                        if ForoSilaboSemanal.objects.filter(status=True, silabosemanal=semana).exists():
                            eForo = ForoSilaboSemanal.objects.filter(status=True, silabosemanal=semana).order_by('-nombre')
                        if TareaSilaboSemanal.objects.filter(status=True, silabosemanal=semana, nombre__icontains='TAREA_').exists():
                            eTarea = TareaSilaboSemanal.objects.filter(status=True, silabosemanal=semana, nombre__icontains='TAREA_').order_by('-id')
                        if TareaSilaboSemanal.objects.filter(status=True, silabosemanal=semana, nombre__icontains='ANÁLISIS').exists():
                            eAnalisis = TareaSilaboSemanal.objects.filter(status=True, silabosemanal=semana, nombre__icontains='ANÁLISIS').order_by('-id')
                        if TareaSilaboSemanal.objects.filter(status=True, silabosemanal=semana, nombre__icontains='TRABAJO').exists():
                            eTrabajo = TareaSilaboSemanal.objects.filter(status=True, silabosemanal=semana, nombre__icontains='TRABAJO').order_by('-id')

                        eSemanas.append({
                            "inicio": semana.fechainiciosemana,
                            "fin": semana.fechafinciosemana,
                            "semana": semana.numsemana,
                            "eDiapositiva": eDiapositiva,
                            "eCompendio": eCompendio,
                            "eVideoMagistral": eVideoMagistral,
                            "eMaterialAdicional": eMaterialAdicional,
                            "eGuiaEstudiante": eGuiaEstudiante,
                            #ACD
                            "eTest": eTest,
                            "eTaller": eTaller,
                            "eExposicion": eExposicion,
                            # AA
                            "eForo": eForo,
                            "eTarea": eTarea,
                            "eAnalisis": eAnalisis,
                            "eTrabajo": eTrabajo
                        })

                    data['eSemanas'] = eSemanas
                    return render(request, "pro_personaevaluacion/verrecursosposgrado.html", data)
                except Exception as ex:
                    pass

            elif action == 'listatutorias':
                try:
                    from django.db import connection
                    data['title'] = u'Tutorías de Prácticas Pre Profesionales'
                    search = None
                    tipo = None
                    ids = None
                    data['profesor'] = profesor = Profesor.objects.get(pk=int(encrypt(request.GET['profesorid'])))
                    if 's' in request.GET:
                        search = request.GET['s']
                        if search.isdigit():
                            tutoriaspracticas = PracticasPreprofesionalesInscripcion.objects.filter(Q(inscripcion__persona__cedula__icontains=search),status=True,
                                                                                                    tutorunemi=profesor).order_by('-fecha_creacion').distinct()
                        else:
                            search = request.GET['s'].strip()
                            ss = search.split(' ')
                            if len(ss) == 1:
                                tutoriaspracticas = PracticasPreprofesionalesInscripcion.objects.filter(
                                    Q(inscripcion__persona__apellido1__icontains=search) |
                                    Q(inscripcion__persona__apellido2__icontains=search) |
                                    Q(inscripcion__persona__nombres__icontains=search),
                                    status=True, tutorunemi=profesor).order_by('-fecha_creacion').distinct()
                            else:
                                tutoriaspracticas = PracticasPreprofesionalesInscripcion.objects.select_related().filter(
                                    Q(inscripcion__persona__apellido1__icontains=ss[0]) &
                                    Q(inscripcion__persona__apellido2__icontains=ss[1]),
                                    status=True, tutorunemi=profesor).order_by('-fecha_creacion').distinct()
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        tutoriaspracticas = PracticasPreprofesionalesInscripcion.objects.filter(pk=ids,status=True,tutorunemi=profesor).order_by('-fecha_creacion').distinct()
                    else:
                        tutoriaspracticas = PracticasPreprofesionalesInscripcion.objects.select_related().filter(status=True,tutorunemi=profesor,culminada=False).distinct().exclude(estadosolicitud=3).order_by('-fecha_creacion').distinct()

                    if 'tipo' in request.GET:
                        tipo=int(request.GET['tipo'])
                        search1 = int(request.GET['tipo'])
                        if search1 != 0:
                            if search1 == 10:
                                tutoriaspracticas = PracticasPreprofesionalesInscripcion.objects.filter(
                                    culminada=True, status=True,tutorunemi=profesor).order_by('-fecha_creacion').distinct()
                            else:
                                if search1 == 11:
                                    llenardocentes = []
                                    cursor = connection.cursor()
                                    sql = "select ins.id from sga_practicaspreprofesionalesinscripcion ins,sga_detalleevidenciaspracticaspro evid where ins.id=evid.inscripcionpracticas_id and ins.status=true and evid.status=True and evid.estadotutor=0 and evid.estadorevision=1 and ins.tutorunemi_id="+str(profesor.id)+" and evid.evidencia_id in (9,10,11,13)"
                                    cursor.execute(sql)
                                    results = cursor.fetchall()
                                    for r in results:
                                        llenardocentes.append(r[0])
                                    tutoriaspracticas = tutoriaspracticas.filter(pk__in=llenardocentes, status=True).order_by('-fecha_creacion')
                                elif search1 == 12:
                                    llenardocentes = []
                                    cursor = connection.cursor()
                                    # sql1 = "select ins.id from sga_practicaspreprofesionalesinscripcion ins,sga_detalleevidenciaspracticaspro evid where ins.id=evid.inscripcionpracticas_id and ins.status=true and evid.status=True and evid.estadorevision=3 and ins.tutorunemi_id=" + str(profesor.id) + " and evid.evidencia_id in (9,10,11,13)"
                                    sql1 = "select ins.id from sga_practicaspreprofesionalesinscripcion ins,sga_detalleevidenciaspracticaspro evid where ins.id=evid.inscripcionpracticas_id and ins.status=true and evid.status=True and ins.tutorunemi_id=" + str(profesor.id) + " and evid.evidencia_id in (9,10,11,13) and evid.fechainicio is not null and evid.fechafin is not null and evid.estadotutor=0 group by ins.id"
                                    cursor.execute(sql1)
                                    results = cursor.fetchall()
                                    for r in results:
                                        llenardocentes.append(r[0])
                                    tutoriaspracticas = tutoriaspracticas.filter(pk__in=llenardocentes,status=True).order_by('-fecha_creacion')
                                elif search1 == 13:
                                    llenardocentes = []
                                    cursor = connection.cursor()
                                    # sql1 = "select ins.id from sga_practicaspreprofesionalesinscripcion ins,sga_detalleevidenciaspracticaspro evid where ins.id=evid.inscripcionpracticas_id and ins.status=true and evid.status=True and evid.estadorevision=3 and ins.tutorunemi_id=" + str(profesor.id) + " and evid.evidencia_id in (9,10,11,13)"
                                    sql1 = "select ins.id from sga_practicaspreprofesionalesinscripcion ins,sga_detalleevidenciaspracticaspro evid where ins.id=evid.inscripcionpracticas_id and ins.status=true and evid.status=True and ins.tutorunemi_id=" + str(profesor.id) + " and evid.evidencia_id in (9,10,11,13) and (evid.estadorevision=3 or evid.estadotutor=3 ) group by ins.id"
                                    cursor.execute(sql1)
                                    results = cursor.fetchall()
                                    for r in results:
                                        llenardocentes.append(r[0])
                                    tutoriaspracticas = tutoriaspracticas.filter(pk__in=llenardocentes,status=True).order_by('-fecha_creacion')
                                elif search1 == 14:
                                    tutoriaspracticas = tutoriaspracticas.filter(estadosolicitud=1, culminada=False, status=True).order_by('-fecha_creacion')

                    paging = MiPaginador(tutoriaspracticas, 10)
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
                    data['tutoriaspracticas'] = page.object_list
                    data['search'] = search if search else ""
                    data['tipo'] = tipo if tipo else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "pro_personaevaluacion/listatutorias.html", data)
                except Exception as ex:
                    pass

            elif action == 'verevidencia':
                try:
                    data['title'] = u'Ver Evidencia'
                    data['profesor'] = profesorseleccionado = Profesor.objects.get(pk=int(encrypt(request.GET['profesorid'])))
                    data['opcion'] = int(encrypt(request.GET['opcion']))
                    data['tipoevi'] = int(encrypt(request.GET['tipoevi']))
                    data['detalledistributivo'] = detalledistributivo = DetalleDistributivo.objects.get(pk=int(encrypt(request.GET['id'])), distributivo__profesor=profesorseleccionado, status=True)
                    if actividad := detalledistributivo.actividaddetalledistributivo_set.filter(status=True,
                                                                                                vigente=True).first():
                        data['subactividades'] = SubactividadDetalleDistributivo.objects.filter(
                            actividaddetalledistributivo=actividad,
                            subactividaddocenteperiodo__criterio__status=True,
                            status=True
                        ).prefetch_related(
                            Prefetch(
                                'evidenciaactividaddetalledistributivo_set',
                                queryset=EvidenciaActividadDetalleDistributivo.objects.order_by('desde'),
                                to_attr='evidencias'
                            )
                        )
                    data['evidenciaactividaddetalledistributivo'] = EvidenciaActividadDetalleDistributivo.objects.filter(criterio=detalledistributivo).order_by('desde')
                    data['evidenciaseliminadas'] = EvidenciaActividadDetalleDistributivo.objects.filter(
                        ((Q(desde__gte=periodo.inicio) & Q(hasta__lte=periodo.fin)) |
                         (Q(desde__lte=periodo.inicio) & Q(hasta__gte=periodo.fin)) |
                         (Q(desde__lte=periodo.fin) & Q(desde__gte=periodo.inicio)) |
                         (Q(hasta__gte=periodo.inicio) & Q(hasta__lte=periodo.fin)))
                        ,criterio_id__isnull=False, actividaddetalledistributivo__id__isnull=True,usuario_creacion=profesorseleccionado.persona.usuario).order_by('desde')
                    data['listado'] = listado = InformeMensualDocentesPPP.objects.filter(status=True, persona=profesorseleccionado).order_by('-fechageneracion')
                    data['liscount'] = listado.count()
                    data['fechainicio'] = periodo.inicio
                    data['fechafin'] = datetime.now().date()
                    return render(request, "pro_personaevaluacion/verevidencia.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadobitacora':
                try:
                    data['title'] = u'Listado de registros de bitácora'
                    data['profesor'] = profesorseleccionado = Profesor.objects.get(pk=int(encrypt(request.GET['profesorid'])))
                    data['opcion'] = int(encrypt(request.GET['opcion']))
                    data['tipoevi'] = int(encrypt(request.GET['tipoevi']))
                    listadomeses = []
                    dias_plazo_llenar_bitacora = variable_valor('PLAZO_DIAS_LLENAR_BITACORA_DOCENTE')
                    data['detalledistributivo'] = detalledistributivo = DetalleDistributivo.objects.get(pk=int(encrypt(request.GET['id'])), distributivo__profesor=profesorseleccionado, status=True)
                    data['evidenciasdistributivo'] = evidenciasdistributivo = detalledistributivo.evidenciaactividaddetalledistributivo_set.filter(status=True).order_by('desde')
                    registrobitacoras = detalledistributivo.bitacoraactividaddocente_set.filter(status=True).order_by('fechaini').annotate(fechamaxima=ExpressionWrapper(F('fechafin') + timedelta(days=dias_plazo_llenar_bitacora), output_field=DateTimeField()))
                    data['evidenciaactividaddetalledistributivo'] = registrobitacoras.filter(fechamaxima__gte=datetime.now())
                    fechas_mensuales = list(rrule(MONTHLY, dtstart=periodo.inicio, until=periodo.fin))
                    fechaactual = datetime.now().date()
                    fechabitacora = "2023-05-31" #Desde esta fecha la evidencias de llenar bitacora comenzaron a llenar, fechas atras llenaban informes
                    fechabitacora = datetime.strptime(fechabitacora, "%Y-%m-%d").date()
                    for fecha in fechas_mensuales:
                        ultimo_dia = fecha.replace(day=calendar.monthrange(fecha.year, fecha.month)[1])
                        primer_dia = fecha.replace(day=1)
                        numeromes = fecha.month
                        anio = fecha.year
                        nomostrar = 0

                        # Genera cabecera de bitácora
                        if primer_dia.date() <= datetime.now().date() and not detalledistributivo.bitacoraactividaddocente_set.filter(fechafin__month=ultimo_dia.month, fechafin__year=ultimo_dia.year, profesor=profesorseleccionado, status=True).exists():
                            mesbitacora = BitacoraActividadDocente(profesor=profesorseleccionado, criterio=detalledistributivo, nombre='REGISTRO DE BITÁCORA MES DE: ' + MESES_CHOICES[ultimo_dia.month - 1][1].upper(), fechaini=primer_dia, fechafin=ultimo_dia)
                            mesbitacora.save(request)
                            h = HistorialBitacoraActividadDocente(bitacora=mesbitacora, persona=persona, estadorevision=mesbitacora.estadorevision)
                            h.save(request)
                            nomostrar = 1
                        # -------------------------------------------------------------------------

                        for bita in registrobitacoras:
                            if bita.fechaini.month == fecha.month:
                                nomostrar = 1

                        for evi in evidenciasdistributivo:
                            if evi.hasta.month == fecha.month:
                                nomostrar = 1

                        if nomostrar == 0:
                            if fechaactual >= primer_dia.date():
                                if ultimo_dia.date() > fechabitacora:
                                    listadomeses.append([primer_dia, anio, '01', str(numeromes), str(ultimo_dia.day), ultimo_dia.date() + timedelta(days=dias_plazo_llenar_bitacora)])

                    data['fechaactual'] = fechaactual
                    data['listadomeses'] = listadomeses
                    data['periodo'] = periodo
                    data['bitacoras'] = registrobitacoras.filter(fechamaxima__lte=datetime.now(), fecha_creacion__gte=fechabitacora)
                    return render(request, "pro_personaevaluacion/listadobitacora.html", data)
                except Exception as ex:
                    pass

            elif action == 'ver_detalleevidenciabitacora':
                try:
                    data['title'] = u'Listado actividades bitacora'

                    dias_plazo_llenar_bitacora = variable_valor('PLAZO_DIAS_LLENAR_BITACORA_DOCENTE')
                    valida_registro_tardio_bitacora, now = False, datetime.now().date()
                    codigoprofesor = request.GET['codigoprofesor']
                    mesbitacora = BitacoraActividadDocente.objects.get(pk=int(request.GET['idbitacora']))
                    data['detalledistributivo'] = detalledistributivo = DetalleDistributivo.objects.get(pk=mesbitacora.criterio.id, distributivo__profesor_id=codigoprofesor, status=True)

                    data['mesbitacora'] = mesbitacora
                    data['listadodetalle'] = listadodetalle = mesbitacora.detallebitacoradocente_set.filter(status=True).annotate(diferencia=ExpressionWrapper(F('horafin') - F('horainicio'), output_field=TimeField())).order_by('fecha', 'horainicio', 'horafin')
                    if mesbitacora.criterio.criteriodocenciaperiodo:
                        claseactividad = ClaseActividad.objects.filter(detalledistributivo__criteriodocenciaperiodo=mesbitacora.criterio.criteriodocenciaperiodo, detalledistributivo__distributivo__profesor_id=codigoprofesor, status=True).order_by('inicio', 'dia', 'turno__comienza')

                    if mesbitacora.criterio.criterioinvestigacionperiodo:
                        claseactividad = ClaseActividad.objects.filter(detalledistributivo__criterioinvestigacionperiodo=mesbitacora.criterio.criterioinvestigacionperiodo, detalledistributivo__distributivo__profesor_id=codigoprofesor, status=True).order_by('inicio', 'dia', 'turno__comienza')

                    if mesbitacora.criterio.criteriogestionperiodo:
                        claseactividad = ClaseActividad.objects.filter(detalledistributivo__criteriogestionperiodo=mesbitacora.criterio.criteriogestionperiodo, detalledistributivo__distributivo__profesor_id=codigoprofesor, status=True).order_by('inicio', 'dia', 'turno__comienza')

                    diasclas = claseactividad.values_list('dia', 'turno_id')
                    dt = mesbitacora.fechaini
                    end = mesbitacora.fechafin
                    step = timedelta(days=1)

                    result = []
                    while dt <= end:
                        dias_nolaborables = periodo.dias_nolaborables(dt)
                        if not dias_nolaborables:
                            for dclase in diasclas:
                                if dt.isocalendar()[2] == dclase[0]:
                                    result.append(dt.strftime('%Y-%m-%d'))
                        dt += step

                    data['totalhorasplanificadas'] = totalhorasplanificadas = len(result)
                    totalhorasregistradas, totalhorasaprobadas, porcentaje_cumplimiento = 0, 0, 0

                    if th := listadodetalle.filter(status=True).aggregate(total=Sum('diferencia'))['total']:
                        horas, minutos = (th.total_seconds() / 3600).__str__().split('.')
                        totalhorasregistradas = float("%s.%s" % (horas, round(float('0.' + minutos) * 60)))

                    if th := listadodetalle.filter(estadoaprobacion=2, status=True).aggregate(total=Sum('diferencia'))['total']:
                        horas, minutos = (th.total_seconds() / 3600).__str__().split('.')
                        totalhorasaprobadas = float("%s.%s" % (horas, round(float('0.' + minutos) * 60)))

                    data['totalhorasregistradas'] = totalhorasregistradas
                    data['totalhorasaprobadas'] = totalhorasaprobadas

                    if totalhorasplanificadas:
                        if mesbitacora.estadorevision == 3:
                            porcentaje_cumplimiento = 100 if totalhorasaprobadas > totalhorasplanificadas else round((totalhorasaprobadas / totalhorasplanificadas) * 100, 2)
                        else:
                            porcentaje_cumplimiento = 100 if totalhorasregistradas > totalhorasplanificadas else round((totalhorasregistradas / totalhorasplanificadas) * 100, 2)


                    data['porcentaje_cumplimiento'] = porcentaje_cumplimiento
                    data['valida_registro_tardio_bitacora'] = valida_registro_tardio_bitacora
                    template = get_template("pro_personaevaluacion/ver_detalleevidenciabitacora.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'evidenciatitulacion':
                try:
                    data['title'] = u"Grupo de línea de investigación"
                    data['tipoevi'] = int(encrypt(request.GET['tipoevi']))
                    idcrite = request.GET['idcrite']
                    data['nomprofesor'] = nomprofesor = Profesor.objects.get(pk=int(encrypt(request.GET['idprofesor'])))
                    periodotitulacion = int(encrypt(request.GET['per'])) if 'per' in request.GET else 0
                    data['archivos'] = ArchivoTitulacion.objects.filter(vigente=True, tipotitulacion__tipo=2)
                    listadoperiodos = CriterioDocenciaPeriodoTitulacion.objects.values_list('titulacion_id').filter(criterio_id=idcrite,status=True)
                    data['titperiodos'] = periodos = PeriodoGrupoTitulacion.objects.filter(pk__in=listadoperiodos, status=True)
                    grupos = ComplexivoGrupoTematica.objects.filter(status=True, tematica__tutor__participante__persona__id=nomprofesor.persona.id).order_by('tematica__tematica__tema')
                    grs = ComplexivoGrupoTematica.objects.filter(Q(status=True), Q(presidentepropuesta__persona=nomprofesor.persona)| Q(secretariopropuesta__persona=nomprofesor.persona) | Q(delegadopropuesta__persona=nomprofesor.persona)).order_by('-fechadefensa', '-horadefensa')
                    examenes = ComplexivoExamen.objects.filter(docente=nomprofesor, alternativa__status=True).order_by('-fechaexamen')
                    data['opcion'] = int(encrypt(request.GET['opcion']))
                    if periodos:
                        data['perid'] = periodos.order_by('-id')[0]
                    else:
                        data['perid'] = None
                    data['docente'] = nomprofesor
                    if periodotitulacion > 0:
                        data['perid'] = PeriodoGrupoTitulacion.objects.get(pk=periodotitulacion)
                        grupos = grupos.filter(tematica__periodo_id__in=periodos.values_list('id'))
                        grs = grs.filter(tematica__periodo_id__in=periodos.values_list('id'))
                        examenes = examenes.filter(alternativa__grupotitulacion__periodogrupo_id__in=periodos.values_list('id'), alternativa__status=True)
                    else:
                        if periodos:
                            data['perid'] = periodos.order_by('-id')[0]
                        else:
                            data['perid'] = None
                        grupos = grupos.filter(tematica__periodo_id__in=periodos.values_list('id'))
                        grs = grs.filter(tematica__periodo_id__in=periodos.values_list('id'))
                        examenes = examenes.filter(alternativa__grupotitulacion__periodogrupo_id__in=periodos.values_list('id'), alternativa__status=True)
                    grupossustentacion = []
                    for gr in grs:
                        if gr.tiene_propuesta_aceptada():
                            grupossustentacion.append(gr)
                    data['grupos'] = grupos
                    data['grupossustentacion'] = grupossustentacion
                    data['examenes'] = examenes
                    return render(request, "pro_personaevaluacion/verevidenciatitulacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'informe_seguimiento_generalevidencia':
                mensaje = "error"
                try:
                    materias=[]
                    listacarreras = []
                    coord = 0
                    suma = 0
                    coordinacion = None
                    profesormateria = None
                    # finio = request.POST['fini']
                    # ffino = request.POST['ffin']
                    # finic = convertir_fecha(finio)
                    # ffinc = convertir_fecha(ffino)
                    opcionreport = 1
                    lista1=""
                    data['criterio'] = CriterioDocencia.objects.get(pk=request.GET['idcriteriodocencia'])
                    data['profesor'] = profesor = Profesor.objects.get(pk=int(encrypt(request.GET['id'])))
                    # 1: grado virtual
                    # if opcionreport == 1:
                    profesormateria = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__modalidad_id=3, materia__nivel__periodo=periodo,activo=True).exclude(materia__nivel__nivellibrecoordinacion__coordinacion_id=9).distinct().order_by('desde', 'materia__asignatura__nombre')
                    # 2 virtual admision
                    # if opcionreport == 2:
                    #     coord=9
                    #     profesormateria = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__modalidad_id=3, materia__nivel__periodo=periodo, activo=True, materia__nivel__nivellibrecoordinacion__coordinacion_id=9).distinct().order_by('desde', 'materia__asignatura__nombre')
                    # # 3 presencial admision
                    # if opcionreport == 3:
                    #     coord = 9
                    #     profesormateria = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__periodo=periodo, activo=True, materia__nivel__nivellibrecoordinacion__coordinacion_id=9).exclude(materia__nivel__modalidad_id=3).distinct().order_by('desde', 'materia__asignatura__nombre')

                    if profesormateria:
                        suma = profesormateria.aggregate(total=Sum('hora'))['total']
                        lista = []
                        for x in profesormateria:
                            materias.append(x.materia)
                            if x.materia.carrera():
                                carrera = x.materia.carrera()
                                if not carrera in listacarreras:
                                    listacarreras.append(carrera)
                                lista.append(carrera)
                        cuenta1 = collections.Counter(lista).most_common(1)
                        carrera = cuenta1[0][0]
                        coordinacion = carrera.coordinacionvalida
                        matriculados = MateriaAsignada.objects.filter(materiaasignadaretiro__isnull=True,
                                                                      matricula__estado_matricula__in=[2,3],
                                                                      materia__id__in=profesormateria.values_list(
                                                                          'materia__id', flat=True)).distinct()
                        for x in matriculados:
                            if x.id != matriculados.order_by('-id')[0].id:
                                if x.matricula.inscripcion.persona.idusermoodle:
                                    lista1 += str(x.matricula.inscripcion.persona.idusermoodle) + ","
                            else:
                                lista1 += str(x.matricula.inscripcion.persona.idusermoodle)
                    distributivo = ProfesorDistributivoHoras.objects.filter(periodo=periodo, profesor=profesor, status=True)[0] if ProfesorDistributivoHoras.objects.filter(periodo=periodo, profesor=profesor, status=True).exists() else None
                    titulaciones = distributivo.profesor.persona.mis_titulaciones()
                    titulaciones = titulaciones.filter(titulo__nivel_id__in=[3, 4])

                    data['distributivo'] = distributivo
                    data['periodo'] = periodo
                    data['suma'] = suma
                    data['materias'] = materias
                    data['titulaciones'] = titulaciones
                    data['opcionreport'] = opcionreport
                    data['coord'] = coord
                    data['coordinacion'] = coordinacion
                    data['listacarreras'] = listacarreras
                    data['lista'] = lista1
                    return render(request, "pro_personaevaluacion/veractividadestemaforo.html", data)
                except Exception as ex:
                    return HttpResponseRedirect("/pro_personaevaluacion?info=%s" % mensaje)

            elif action == 'informe_seguimiento_generaltodaevidencia':
                mensaje = "error"
                try:
                    materias=[]
                    listacarreras = []
                    coord = 0
                    suma = 0
                    coordinacion = None
                    profesormateria = None
                    opcionreport = 1
                    lista1=""
                    data['criterio'] = CriterioDocencia.objects.get(pk=request.GET['idcriteriodocencia'])
                    data['profesor'] = profesor = Profesor.objects.get(pk=int(encrypt(request.GET['id'])))
                    profesormateria = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__periodo=periodo, activo=True).exclude(materia__nivel__nivellibrecoordinacion__coordinacion_id=9).distinct().order_by('desde', 'materia__asignatura__nombre')
                    if profesormateria:
                        suma = profesormateria.aggregate(total=Sum('hora'))['total']
                        lista = []
                        for x in profesormateria:
                            materias.append(x.materia)
                            if x.materia.carrera():
                                carrera = x.materia.carrera()
                                if not carrera in listacarreras:
                                    listacarreras.append(carrera)
                                lista.append(carrera)
                        cuenta1 = collections.Counter(lista).most_common(1)
                        carrera = cuenta1[0][0]
                        coordinacion = carrera.coordinacionvalida
                        matriculados = MateriaAsignada.objects.filter(materiaasignadaretiro__isnull=True,
                                                                      matricula__estado_matricula__in=[2,3],
                                                                      materia__id__in=profesormateria.values_list(
                                                                          'materia__id', flat=True)).distinct()
                        for x in matriculados:
                            if x.id != matriculados.order_by('-id')[0].id:
                                if x.matricula.inscripcion.persona.idusermoodle:
                                    lista1 += str(x.matricula.inscripcion.persona.idusermoodle) + ","
                            else:
                                lista1 += str(x.matricula.inscripcion.persona.idusermoodle)
                    distributivo = ProfesorDistributivoHoras.objects.filter(periodo=periodo, profesor=profesor, status=True)[0] if ProfesorDistributivoHoras.objects.filter(periodo=periodo, profesor=profesor, status=True).exists() else None
                    titulaciones = distributivo.profesor.persona.mis_titulaciones()
                    titulaciones = titulaciones.filter(titulo__nivel_id__in=[3, 4])

                    data['distributivo'] = distributivo
                    data['periodo'] = periodo
                    data['suma'] = suma
                    data['materias'] = materias
                    data['titulaciones'] = titulaciones
                    data['opcionreport'] = opcionreport
                    data['coord'] = coord
                    data['coordinacion'] = coordinacion
                    data['listacarreras'] = listacarreras
                    data['lista'] = lista1
                    return render(request, "pro_personaevaluacion/vertodasactividades.html", data)
                except Exception as ex:
                    return HttpResponseRedirect("/pro_personaevaluacion?info=%s" % mensaje)

            elif action == 'informe_seguimiento_generalrecursos':
                mensaje = "error"
                try:
                    materias=[]
                    listacarreras = []
                    coord = 0
                    suma = 0
                    coordinacion = None
                    profesormateria = None
                    opcionreport = 1
                    lista1=""
                    data['criterio'] = CriterioDocencia.objects.get(pk=request.GET['idcriteriodocencia'])
                    data['profesor'] = profesor = Profesor.objects.get(pk=int(encrypt(request.GET['id'])))
                    # 1: grado virtual
                    # if opcionreport == 1:
                    profesormateria = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__modalidad_id=3, materia__nivel__periodo=periodo,activo=True).exclude(materia__nivel__nivellibrecoordinacion__coordinacion_id=9).distinct().order_by('desde', 'materia__asignatura__nombre')
                    # 2 virtual admision
                    # if opcionreport == 2:
                    #     coord=9
                    #     profesormateria = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__modalidad_id=3, materia__nivel__periodo=periodo, activo=True, materia__nivel__nivellibrecoordinacion__coordinacion_id=9).distinct().order_by('desde', 'materia__asignatura__nombre')
                    # # 3 presencial admision
                    # if opcionreport == 3:
                    #     coord = 9
                    #     profesormateria = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__periodo=periodo, activo=True, materia__nivel__nivellibrecoordinacion__coordinacion_id=9).exclude(materia__nivel__modalidad_id=3).distinct().order_by('desde', 'materia__asignatura__nombre')

                    if profesormateria:
                        suma = profesormateria.aggregate(total=Sum('hora'))['total']
                        lista = []
                        for x in profesormateria:
                            materias.append(x.materia)
                            if x.materia.carrera():
                                carrera = x.materia.carrera()
                                if not carrera in listacarreras:
                                    listacarreras.append(carrera)
                                lista.append(carrera)
                        cuenta1 = collections.Counter(lista).most_common(1)
                        carrera = cuenta1[0][0]
                        coordinacion = carrera.coordinacionvalida
                        matriculados = MateriaAsignada.objects.filter(materiaasignadaretiro__isnull=True,
                                                                      matricula__estado_matricula__in=[2,3],
                                                                      materia__id__in=profesormateria.values_list('materia__id', flat=True)).distinct()
                        for x in matriculados:
                            if x.id != matriculados.order_by('-id')[0].id:
                                if x.matricula.inscripcion.persona.idusermoodle:
                                    lista1 += str(x.matricula.inscripcion.persona.idusermoodle) + ","
                            else:
                                lista1 += str(x.matricula.inscripcion.persona.idusermoodle)
                    distributivo = ProfesorDistributivoHoras.objects.filter(periodo=periodo, profesor=profesor, status=True)[0] if ProfesorDistributivoHoras.objects.filter(periodo=periodo, profesor=profesor, status=True).exists() else None
                    titulaciones = distributivo.profesor.persona.mis_titulaciones()
                    titulaciones = titulaciones.filter(titulo__nivel_id__in=[3, 4])

                    data['distributivo'] = distributivo
                    data['periodo'] = periodo
                    data['suma'] = suma
                    data['materias'] = materias
                    data['titulaciones'] = titulaciones
                    data['opcionreport'] = opcionreport
                    data['coord'] = coord
                    data['coordinacion'] = coordinacion
                    data['listacarreras'] = listacarreras
                    data['lista'] = lista1
                    return render(request, "pro_personaevaluacion/veractividadesrecursos.html", data)
                except Exception as ex:
                    return HttpResponseRedirect("/pro_personaevaluacion?info=%s" % mensaje)

            elif action == 'informe_seguimiento_generalrecursosvideos':
                mensaje = "error"
                try:
                    materias=[]
                    listacarreras = []
                    coord = 0
                    suma = 0
                    coordinacion = None
                    profesormateria = None
                    opcionreport = 1
                    lista1=""
                    data['criterio'] = CriterioDocencia.objects.get(pk=request.GET['idcriteriodocencia'])
                    data['profesor'] = profesor = Profesor.objects.get(pk=int(encrypt(request.GET['id'])))
                    # 1: grado virtual
                    # if opcionreport == 1:
                    profesormateria = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__modalidad_id=3, materia__nivel__periodo=periodo,activo=True).distinct().order_by('desde', 'materia__asignatura__nombre')

                    if profesormateria:
                        suma = profesormateria.aggregate(total=Sum('hora'))['total']
                        lista = []
                        for x in profesormateria:
                            materias.append(x.materia)
                            if x.materia.carrera():
                                carrera = x.materia.carrera()
                                if not carrera in listacarreras:
                                    listacarreras.append(carrera)
                                lista.append(carrera)
                        cuenta1 = collections.Counter(lista).most_common(1)
                        carrera = cuenta1[0][0]
                        coordinacion = carrera.coordinacionvalida
                        matriculados = MateriaAsignada.objects.filter(materiaasignadaretiro__isnull=True,
                                                                      matricula__estado_matricula__in=[2,3],
                                                                      materia__id__in=profesormateria.values_list('materia__id', flat=True)).distinct()
                        for x in matriculados:
                            if x.id != matriculados.order_by('-id')[0].id:
                                if x.matricula.inscripcion.persona.idusermoodle:
                                    lista1 += str(x.matricula.inscripcion.persona.idusermoodle) + ","
                            else:
                                lista1 += str(x.matricula.inscripcion.persona.idusermoodle)
                    distributivo = ProfesorDistributivoHoras.objects.filter(periodo=periodo, profesor=profesor, status=True)[0] if ProfesorDistributivoHoras.objects.filter(periodo=periodo, profesor=profesor, status=True).exists() else None
                    titulaciones = distributivo.profesor.persona.mis_titulaciones()
                    titulaciones = titulaciones.filter(titulo__nivel_id__in=[3, 4])

                    data['distributivo'] = distributivo
                    data['periodo'] = periodo
                    data['suma'] = suma
                    data['materias'] = materias
                    data['titulaciones'] = titulaciones
                    data['opcionreport'] = opcionreport
                    data['coord'] = coord
                    data['coordinacion'] = coordinacion
                    data['listacarreras'] = listacarreras
                    data['lista'] = lista1
                    return render(request, "pro_personaevaluacion/veractividadesrecursosvideos.html", data)
                except Exception as ex:
                    return HttpResponseRedirect("/pro_personaevaluacion?info=%s" % mensaje)

            elif action == 'listadotutoriasindividualesgrupales':
                mensaje = "error"
                try:
                    materias=[]
                    listacarreras = []
                    coord = 0
                    suma = 0
                    coordinacion = None
                    profesormateria = None
                    opcionreport = 1
                    lista1=""
                    data['criterio'] = CriterioDocencia.objects.get(pk=request.GET['idcriteriodocencia'])
                    data['profesor'] = profesor = Profesor.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['profesormateria'] = profesormateria = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__modalidad_id=1, materia__nivel__periodo=periodo,activo=True).exclude(materia__nivel__nivellibrecoordinacion__coordinacion_id=9).distinct().order_by('desde', 'materia__asignatura__nombre')

                    return render(request, "pro_personaevaluacion/listadotutoriasindividualesgrupales.html", data)
                except Exception as ex:
                    return HttpResponseRedirect("/pro_personaevaluacion?info=%s" % mensaje)

            elif action == 'evidenciasvideoautor':
                try:
                    data['criterio'] = CriterioDocencia.objects.get(pk=request.GET['idcriteriodocencia'])
                    data['profesor'] = profesor = Profesor.objects.get(pk=int(encrypt(request.GET['id'])))
                    from django.db import connection
                    cursor = connection.cursor()
                    sql = """
                        SELECT ca.nombre AS carrera,a.nombre AS asignatura, con.descripcion AS Contenido, uni.orden ,uni.descripcion AS Unidad, 
                        tem.orden, tem.descripcion AS tema, vtem.video, vtem.fecha_creacion AS fechacreatema,
                        stem.orden, stem.descripcion AS subtema, vste.video, vste.fecha_creacion  AS fechacreasubtema
                        FROM sga_autorprogramaanalitico pa
                        INNER JOIN sga_programaanaliticoasignatura pas ON pas.id=pa.programaanalitico_id
                        INNER JOIN sga_asignaturamalla ama ON ama.id=pas.asignaturamalla_id
                        INNER JOIN sga_malla ma ON ma.id=ama.malla_id
                        INNER JOIN sga_carrera ca ON ca.id=ma.carrera_id
                        INNER JOIN sga_asignatura a ON a.id=ama.asignatura_id
                        left JOIN sga_contenidoresultadoprogramaanalitico con ON con.programaanaliticoasignatura_id=pas.id
                        left JOIN sga_unidadresultadoprogramaanalitico uni ON uni.contenidoresultadoprogramaanalitico_id=con.id
                        left JOIN sga_temaunidadresultadoprogramaanalitico tem ON tem.unidadresultadoprogramaanalitico_id=uni.id
                        left JOIN sga_subtemaunidadresultadoprogramaanalitico stem ON stem.temaunidadresultadoprogramaanalitico_id=tem.id
                        LEFT JOIN sga_videotemaprogramaanalitico vtem ON vtem.tema_id=tem.id
                        LEFT JOIN sga_videosubtemaprogramaanalitico vste ON vste.subtema_id=stem.id
                        WHERE pa.autor_id=%s AND pa.periodo_id=%s AND ( not vtem.id ISNULL or not vste.id ISNULL)
                        ORDER BY ca.nombre,a.nombre, uni.orden, tem.orden, stem.orden
                    """ % (int(encrypt(request.GET['id'])), periodo.id)
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    data['resultado'] = results

                    return render(request, "pro_personaevaluacion/evidenciasvideoautor.html", data)
                except Exception as ex:
                    return HttpResponseRedirect("/pro_personaevaluacion")

            elif action == 'tutoriaindividual':
                try:
                    data['criterio'] = CriterioDocencia.objects.get(pk=request.GET['idcriteriodocencia'])
                    data['profesor'] = profesor = Profesor.objects.get(pk=int(encrypt(request.GET['id'])))
                    idmat = int(encrypt(request.GET['idmat']))
                    data['tutorias'] = AvPreguntaRespuesta.objects.filter(status=True,avpreguntadocente__status=True,
                                                                          avpreguntadocente__materiaasignada__matricula__inscripcion__persona__status=True,
                                                                          avpreguntadocente__materiaasignada__materia__status=True,
                                                                          avpreguntadocente__materiaasignada__materia__id=idmat)
                    materia=Materia.objects.get(pk=idmat)
                    data['carrera']= materia.asignaturamalla.malla.carrera.nombre_completo()
                    data['asignatura'] = materia.asignatura.nombre
                    data['docente'] = profesor.persona.nombre_completo()
                    periodo=materia.nivel.periodo
                    data['paralelo']=materia.paralelo
                    data['nivel'] = materia.asignaturamalla.nivelmalla
                    data['carrera1'] = carrera1 = materia.asignaturamalla.malla.carrera
                    facultad= carrera1.coordinaciones()
                    for x in facultad:
                        facultad = x.nombre
                    data['facultad'] = facultad
                    return render(request, "pro_personaevaluacion/reporteindividual.html", data)
                except Exception as ex:
                    pass

            elif action == 'tutoriamasivo':
                try:
                    data['criterio'] = CriterioDocencia.objects.get(pk=request.GET['idcriteriodocencia'])
                    data['profesor'] = profesor = Profesor.objects.get(pk=int(encrypt(request.GET['id'])))
                    idmat = int(encrypt(request.GET['idmat']))
                    data['tutorias'] = tutorias = AvTutoriasAlumnos.objects.filter(status=True,avtutorias__materia=idmat)
                    data['materia'] = materia = Materia.objects.get(pk=idmat)
                    data['carrera'] = carrera = materia.asignaturamalla.malla.carrera
                    data['asignatura'] = materia.asignatura.nombre
                    data['docente'] = profesor.persona.nombre_completo()
                    data['periodo'] = materia.nivel.periodo
                    data['paralelo'] = materia.paralelo
                    data['nivel'] = materia.asignaturamalla.nivelmalla
                    data['coordina'] = coordina = carrera.coordinaciones()
                    facultad = ''
                    for x in coordina:
                        facultad=x.nombre
                    data['facultad'] = facultad
                    return render(request, "pro_personaevaluacion/tutoriamasivo.html", data)
                except Exception as ex:
                    pass

            elif action == 'informe_seguimiento_generalmensajes':
                mensaje = "error"
                try:
                    materias=[]
                    listacarreras = []
                    coord = 0
                    suma = 0
                    coordinacion = None
                    profesormateria = None
                    opcionreport = 1
                    lista1=""
                    data['criterio'] = CriterioDocencia.objects.get(pk=request.GET['idcriteriodocencia'])
                    data['profesor'] = profesor = Profesor.objects.get(pk=int(encrypt(request.GET['id'])))
                    profesormateria = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__modalidad_id=3, materia__nivel__periodo=periodo,activo=True).exclude(materia__nivel__nivellibrecoordinacion__coordinacion_id=9).distinct().order_by('desde', 'materia__asignatura__nombre')

                    if profesormateria:
                        suma = profesormateria.aggregate(total=Sum('hora'))['total']
                        lista = []
                        for x in profesormateria:
                            materias.append(x.materia)
                            if x.materia.carrera():
                                carrera = x.materia.carrera()
                                if not carrera in listacarreras:
                                    listacarreras.append(carrera)
                                lista.append(carrera)
                        cuenta1 = collections.Counter(lista).most_common(1)
                        carrera = cuenta1[0][0]
                        coordinacion = carrera.coordinacionvalida
                        matriculados = MateriaAsignada.objects.filter(materiaasignadaretiro__isnull=True,
                                                                      matricula__estado_matricula__in=[2,3],
                                                                      materia__id__in=profesormateria.values_list('materia__id', flat=True)).distinct()
                        for x in matriculados:
                            if x.id != matriculados.order_by('-id')[0].id:
                                if x.matricula.inscripcion.persona.idusermoodle:
                                    lista1 += str(x.matricula.inscripcion.persona.idusermoodle) + ","
                            else:
                                lista1 += str(x.matricula.inscripcion.persona.idusermoodle)
                    distributivo = ProfesorDistributivoHoras.objects.filter(periodo=periodo, profesor=profesor, status=True)[0] if ProfesorDistributivoHoras.objects.filter(periodo=periodo, profesor=profesor, status=True).exists() else None
                    titulaciones = distributivo.profesor.persona.mis_titulaciones()
                    titulaciones = titulaciones.filter(titulo__nivel_id__in=[3, 4])

                    data['distributivo'] = distributivo
                    data['periodo'] = periodo
                    data['suma'] = suma
                    data['materias'] = materias
                    data['titulaciones'] = titulaciones
                    data['opcionreport'] = opcionreport
                    data['coord'] = coord
                    data['coordinacion'] = coordinacion
                    data['listacarreras'] = listacarreras
                    data['lista'] = lista1
                    return render(request, "pro_personaevaluacion/veractividadesmensajes.html", data)
                except Exception as ex:
                    return HttpResponseRedirect("/pro_personaevaluacion?info=%s" % mensaje)

            elif action == 'evidenciaadmision':
                mensaje = "error"
                try:
                    materias=[]
                    listacarreras = []
                    coord = 0
                    suma = 0
                    coordinacion = None
                    profesormateria = None
                    opcionreport = 1
                    lista1=""
                    data['criterio'] = CriterioDocencia.objects.get(pk=request.GET['idcriteriodocencia'])
                    data['profesor'] = profesor = Profesor.objects.get(pk=int(encrypt(request.GET['id'])))
                    profesormateria = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__periodo=periodo,activo=True, materia__nivel__nivellibrecoordinacion__coordinacion_id=9).distinct().order_by('desde', 'materia__asignatura__nombre')

                    if profesormateria:
                        suma = profesormateria.aggregate(total=Sum('hora'))['total']
                        lista = []
                        for x in profesormateria:
                            materias.append(x.materia)
                            if x.materia.carrera():
                                carrera = x.materia.carrera()
                                if not carrera in listacarreras:
                                    listacarreras.append(carrera)
                                lista.append(carrera)
                        cuenta1 = collections.Counter(lista).most_common(1)
                        carrera = cuenta1[0][0]
                        coordinacion = carrera.coordinacionvalida
                        matriculados = MateriaAsignada.objects.filter(materiaasignadaretiro__isnull=True,
                                                                      matricula__estado_matricula__in=[2,3],
                                                                      materia__id__in=profesormateria.values_list('materia__id', flat=True)).distinct()
                        for x in matriculados:
                            if x.id != matriculados.order_by('-id')[0].id:
                                if x.matricula.inscripcion.persona.idusermoodle:
                                    lista1 += str(x.matricula.inscripcion.persona.idusermoodle) + ","
                            else:
                                lista1 += str(x.matricula.inscripcion.persona.idusermoodle)
                    distributivo = ProfesorDistributivoHoras.objects.filter(periodo=periodo, profesor=profesor, status=True)[0] if ProfesorDistributivoHoras.objects.filter(periodo=periodo, profesor=profesor, status=True).exists() else None
                    titulaciones = distributivo.profesor.persona.mis_titulaciones()
                    titulaciones = titulaciones.filter(titulo__nivel_id__in=[3, 4])

                    data['distributivo'] = distributivo
                    data['periodo'] = periodo
                    data['suma'] = suma
                    data['materias'] = materias
                    data['titulaciones'] = titulaciones
                    data['opcionreport'] = opcionreport
                    data['coord'] = coord
                    data['coordinacion'] = coordinacion
                    data['listacarreras'] = listacarreras
                    data['lista'] = lista1
                    return render(request, "pro_personaevaluacion/evidenciaadmision.html", data)
                except Exception as ex:
                    return HttpResponseRedirect("/pro_personaevaluacion?info=%s" % mensaje)

            elif action == 'verasistencias':
                try:
                    data['title'] = u'Asistencias a clases docentes en el periodo'
                    periodo = request.session['periodo']
                    inicio = periodo.inicio
                    if periodo.fin >= datetime.now().date():
                        fin = datetime.now().date() - timedelta(days=1)
                    else:
                        fin = periodo.fin
                    if not 'profesorid' in request.GET:
                        raise NameError('Error')
                    profesorid = int(encrypt(request.GET['profesorid']))
                    profesor = Profesor.objects.get(id=profesorid)
                    asistencias_registradas = 0
                    asistencias_no_registradas = 0
                    asistencias_dias_feriados = 0
                    asistencias_dias_examen = 0
                    asistencias_dias_suspension = 0
                    origen_solicitado = 0
                    origen_movil = 0
                    origen_coordinador = 0
                    origen_profesor = 0
                    asistencias_dias_tutoria = 0
                    resultado = []
                    clases = []
                    profesormaterias = ProfesorMateria.objects.filter(profesor=profesor, status=True, activo=True, materia__nivel__periodo=periodo,tipoprofesor_id__in=[1, 2, 5,6]).distinct().order_by('desde', 'materia__asignatura__nombre')
                    for profesormateria in profesormaterias:
                        data_asistencia = profesormateria.asistencia_docente(inicio, fin, periodo)
                        asistencias_registradas += data_asistencia['total_asistencias_registradas']
                        asistencias_no_registradas += data_asistencia['total_asistencias_no_registradas']
                        asistencias_dias_feriados += data_asistencia['total_asistencias_dias_feriados']
                        asistencias_dias_examen += data_asistencia['total_asistencias_dias_examen']
                        asistencias_dias_tutoria += data_asistencia['total_asistencias_dias_tutoria']
                        asistencias_dias_suspension += data_asistencia['total_asistencias_dias_suspension']
                        origen_solicitado += data_asistencia['origen_solicitado']
                        origen_movil += data_asistencia['origen_movil']
                        origen_coordinador += data_asistencia['origen_coordinador']
                        origen_profesor += data_asistencia['origen_profesor']
                        clases.extend(data_asistencia['clases'])
                    clases.sort(key=lambda clasesimp: (clasesimp[4], clasesimp[10]), reverse=True)
                    porcentaje = 0
                    if (asistencias_registradas + asistencias_no_registradas) > 0:
                        porcentaje = Decimal((((asistencias_registradas + asistencias_dias_feriados + asistencias_dias_suspension) * 100) / (asistencias_registradas + asistencias_no_registradas + asistencias_dias_feriados +asistencias_dias_suspension ))).quantize(Decimal('.01'))
                    origen_profesor = origen_coordinador + origen_profesor
                    total_asistencia_registradas = asistencias_registradas + asistencias_dias_feriados + asistencias_dias_suspension
                    resultado.append((asistencias_registradas, asistencias_no_registradas, origen_solicitado, origen_movil, origen_coordinador, origen_profesor, asistencias_dias_feriados + asistencias_dias_suspension, porcentaje, asistencias_dias_examen, total_asistencia_registradas))
                    data['profesor'] = profesor
                    data['clases'] = clases
                    data['resultado'] = resultado
                    return render(request, "pro_personaevaluacion/verasistencias.html", data)
                except Exception as ex:
                    pass

            elif action == 'listar_recursossilabos':
                try:
                    data['silabocab'] = silabocab = Silabo.objects.get(pk=request.GET['id'], status=True)
                    data['silabosemanal'] = silabocab.silabosemanal_set.filter(status=True)
                    data['pdi'] = request.GET['pid']
                    return render(request, "pro_personaevaluacion/listarecursossilabos.html", data)
                except Exception as ex:
                    pass


            elif action == 'verasistencias_new':
                try:
                    data['title'] = u'Detalle clases sincrónicas y asincrónicas'
                    data['hoy'] = hoy = datetime.now().date()
                    cursor = connections['default'].cursor()
                    listaasistencias = []
                    profesor = Profesor.objects.get(id=int(encrypt(request.GET['profesorid'])))
                    sql = "select distinct ten.codigoclase,ten.dia,ten.turno_id,ten.inicio,ten.fin,ten.materia_id,ten.tipohorario, " \
                          "ten.horario,ten.rangofecha, " \
                          "ten.rangodia,sincronica.fecha as sincronica,asincronica.fechaforo as asincronica, asignatura, paralelo,asincronica.idforomoodle as idforomoodle,ten.comienza,ten.termina,nolaborables.fecha,nolaborables.observaciones,ten.nivelmalla,ten.idnivelmalla,ten.idcarrera,ten.idcoordinacion " \
                          "from ( " \
                          "select distinct cla.id as codigoclase, " \
                          "cla.dia,cla.turno_id,cla.inicio,cla.fin,cla.materia_id, " \
                          "cla.tipohorario, " \
                          "case " \
                          "WHEN cla.tipohorario in(2,8)  THEN 2 " \
                          "WHEN cla.tipohorario in(7,9)  THEN 7 " \
                          "end as horario, " \
                          "CURRENT_DATE + generate_series(cla.inicio- CURRENT_DATE, cla.fin - CURRENT_DATE ) as rangofecha, " \
                          "EXTRACT (isodow  FROM  CURRENT_DATE + generate_series(cla.inicio- CURRENT_DATE, cla.fin - CURRENT_DATE )) as rangodia,asig.nombre as asignatura, mate.paralelo as paralelo,tur.comienza,tur.termina,nimalla.nombre as nivelmalla,nimalla.id as idnivelmalla,malla.carrera_id as idcarrera,coorcar.coordinacion_id as idcoordinacion " \
                          "from sga_clase cla , sga_materia mate, sga_asignaturamalla asimalla,sga_asignatura asig,sga_turno tur,sga_nivel niv,sga_nivelmalla nimalla,sga_malla malla,sga_carrera carre, sga_coordinacion_carrera coorcar " \
                          "where cla.profesor_id=" + str(profesor.id) + " and cla.materia_id = mate.id and mate.asignaturamalla_id = asimalla.id and asimalla.malla_id=malla.id and asimalla.asignatura_id = asig.id and cla.turno_id=tur.id and asimalla.nivelmalla_id=nimalla.id and malla.carrera_id=carre.id and coorcar.carrera_id=carre.id " \
                                                                        "AND cla.tipohorario IN (8, 9, 2, 7) and mate.nivel_id=niv.id and niv.periodo_id=" + str(periodo.id) + "  " \
                                                                                                                                                                               ") as ten " \
                                                                                                                                                                               "left join " \
                                                                                                                                                                               "( " \
                                                                                                                                                                               "select clas.materia_id,asi.fecha_creacion::timestamp::date as fecha,asi.fecha_creacion as fecharegistro " \
                                                                                                                                                                               "from sga_clasesincronica asi, sga_clase clas " \
                                                                                                                                                                               "where asi.clase_id=clas.id and clas.profesor_id=" + str(profesor.id) + " " \
                                                                                                                                                                                                                                                       ") as sincronica on ten.rangofecha=fecha and ten.horario=2 " \
                                                                                                                                                                                                                                                       "left join " \
                                                                                                                                                                                                                                                       "( " \
                                                                                                                                                                                                                                                       "select  clas.materia_id,asi.fechaforo,asi.idforomoodle " \
                                                                                                                                                                                                                                                       "from sga_claseasincronica asi, sga_clase clas " \
                                                                                                                                                                                                                                                       "where asi.clase_id=clas.id " \
                                                                                                                                                                                                                                                       ") as asincronica on asincronica.materia_id=ten.materia_id and ten.rangofecha=asincronica.fechaforo and ten.horario=7 " \
                                                                                                                                                                                                                                                       "left join " \
                                                                                                                                                                                                                                                       "(select nolab.observaciones, nolab.fecha from sga_diasnolaborable nolab " \
                                                                                                                                                                                                                                                       "where nolab.periodo_id=" + str(periodo.id) + ") as nolaborables on nolaborables.fecha = ten.rangofecha " \
                                                                                                                                                                                                                                                                                                     "where ten.dia=ten.rangodia and ten.rangofecha <='"+ str(hoy) +"' order by ten.rangofecha,materia_id,ten.turno_id,tipohorario"
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    totalsincronica = 0
                    totalasincronica = 0
                    totalplansincronica = 0
                    totalplanasincronica = 0
                    for cuentamarcadas in results:
                        sinasistencia = False
                        if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id=cuentamarcadas[21], nivelmalla_id=cuentamarcadas[20], status=True).exists():
                            if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id=cuentamarcadas[21], nivelmalla_id=cuentamarcadas[20], fecha=cuentamarcadas[8], status=True).exists():
                                sinasistencia = True
                        else:
                            if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id=cuentamarcadas[21], nivelmalla_id__isnull=True, status=True).exists():
                                if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id=cuentamarcadas[21], nivelmalla_id__isnull=True, fecha=cuentamarcadas[8], status=True).exists():
                                    sinasistencia = True
                            else:
                                if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id__isnull=True, nivelmalla_id__isnull=True, status=True).exists():
                                    if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id__isnull=True, nivelmalla_id__isnull=True, fecha=cuentamarcadas[8], status=True).exists():
                                        sinasistencia = True
                                else:
                                    if periodo.diasnolaborable_set.filter(coordinacion_id__isnull=True, carrera_id__isnull=True, nivelmalla_id__isnull=True, status=True).exists():
                                        if periodo.diasnolaborable_set.filter(coordinacion_id__isnull=True, carrera_id__isnull=True, nivelmalla_id__isnull=True, fecha=cuentamarcadas[8], status=True).exists():
                                            sinasistencia = True
                        listaasistencias.append([cuentamarcadas[0], cuentamarcadas[1], cuentamarcadas[2], cuentamarcadas[3],
                                                 cuentamarcadas[4], cuentamarcadas[5], cuentamarcadas[6], cuentamarcadas[7],
                                                 cuentamarcadas[8], cuentamarcadas[9], cuentamarcadas[10], cuentamarcadas[11],
                                                 cuentamarcadas[12], cuentamarcadas[13], cuentamarcadas[14], cuentamarcadas[15],
                                                 cuentamarcadas[16], cuentamarcadas[17], cuentamarcadas[18], cuentamarcadas[19],
                                                 sinasistencia])
                        if cuentamarcadas[7] == 2:
                            totalsincronica += 1
                        if cuentamarcadas[7] == 7:
                            totalasincronica += 1
                        # if cuentamarcadas[10]:
                        #     totalplansincronica += 1
                        totalplansincronica += 1
                        if cuentamarcadas[11]:
                            totalplanasincronica += 1
                    data['listaasistencias'] = listaasistencias
                    data['totalsincronica'] = totalsincronica
                    data['totalasincronica'] = totalasincronica
                    data['totalplansincronica'] = totalplansincronica
                    data['totalplanasincronica'] = totalplanasincronica
                    data['procentajesincronica'] = (totalplansincronica * 100) / totalsincronica
                    data['procentajeasincronica'] = (totalplanasincronica * 100) / totalasincronica
                    data['retorno'] = 'pro_personaevaluacion'
                    data['profesor'] = profesor
                    return render(request, "pro_clases/detalleclases.html", data)
                except Exception as ex:
                    pass

            elif action == 'verasistencias_link':
                try:
                    data['title'] = u'Detalle clases sincrónicas y asincrónicas'
                    data['hoy'] = hoy = datetime.now().date()
                    cursor = connections['default'].cursor()
                    listaasistencias = []
                    profesor = Profesor.objects.get(id=int(encrypt(request.GET['profesorid'])))
                    sql = "select distinct ten.codigoclase,ten.dia,ten.turno_id,ten.inicio,ten.fin,ten.materia_id,ten.tipohorario, " \
                          "ten.horario,ten.rangofecha, " \
                          "ten.rangodia,sincronica.fecha as sincronica,asincronica.fechaforo as asincronica, asignatura, paralelo,asincronica.idforomoodle as idforomoodle,ten.comienza,ten.termina,nolaborables.fecha,nolaborables.observaciones,ten.nivelmalla,ten.idnivelmalla,ten.idcarrera,ten.idcoordinacion,ten.tipoprofesor_id,extract(week from ten.rangofecha::date) as numerosemana,ten.tipoprofesor,asincronica.enlaceuno,asincronica.enlacedos,asincronica.enlacetres " \
                          "from ( select distinct cla.tipoprofesor_id,cla.id as codigoclase, " \
                          "cla.dia,cla.turno_id,cla.inicio,cla.fin,cla.materia_id, " \
                          "cla.tipohorario, " \
                          "case " \
                          "WHEN cla.tipohorario in(2,8)  THEN 2 " \
                          "WHEN cla.tipohorario in(7,9)  THEN 7 " \
                          "end as horario, " \
                          "CURRENT_DATE + generate_series(cla.inicio- CURRENT_DATE, cla.fin - CURRENT_DATE ) as rangofecha, " \
                          "EXTRACT (isodow  FROM  CURRENT_DATE + generate_series(cla.inicio- CURRENT_DATE, cla.fin - CURRENT_DATE )) as rangodia,asig.nombre as asignatura, mate.paralelo as paralelo,tur.comienza,tur.termina,nimalla.nombre as nivelmalla,nimalla.id as idnivelmalla,malla.carrera_id as idcarrera,coorcar.coordinacion_id as idcoordinacion,tipro.nombre as tipoprofesor " \
                          "from sga_clase cla , sga_materia mate, sga_asignaturamalla asimalla,sga_asignatura asig,sga_turno tur,sga_nivel niv,sga_nivelmalla nimalla,sga_malla malla,sga_carrera carre, sga_coordinacion_carrera coorcar, sga_tipoprofesor tipro " \
                          "where cla.profesor_id=" + str(profesor.id) + " and cla.materia_id = mate.id and mate.asignaturamalla_id = asimalla.id and asimalla.malla_id=malla.id and asimalla.asignatura_id = asig.id and cla.turno_id=tur.id and asimalla.nivelmalla_id=nimalla.id and malla.carrera_id=carre.id and coorcar.carrera_id=carre.id " \
                                                                        "AND cla.tipohorario IN (8, 9, 2, 7) and mate.nivel_id=niv.id and cla.tipoprofesor_id=tipro.id and niv.periodo_id=" + str(periodo.id) + "  " \
                                                                                                                                                                                                                ") as ten " \
                                                                                                                                                                                                                "left join " \
                                                                                                                                                                                                                "(select clas.materia_id,asi.fecha_creacion::timestamp::date as fecha,asi.fecha_creacion as fecharegistro " \
                                                                                                                                                                                                                "from sga_clasesincronica asi, sga_clase clas " \
                                                                                                                                                                                                                "where asi.clase_id=clas.id and clas.profesor_id=" + str(profesor.id) + " " \
                                                                                                                                                                                                                                                                                        ") as sincronica on ten.rangofecha=fecha and ten.horario=2 " \
                                                                                                                                                                                                                                                                                        "left join " \
                                                                                                                                                                                                                                                                                        "(select  clas.materia_id,asi.fechaforo,asi.idforomoodle, clas.tipoprofesor_id,enlaceuno,enlacedos,enlacetres " \
                                                                                                                                                                                                                                                                                        "from sga_claseasincronica asi, sga_clase clas " \
                                                                                                                                                                                                                                                                                        "where asi.clase_id=clas.id " \
                                                                                                                                                                                                                                                                                        ") as asincronica on asincronica.materia_id=ten.materia_id and ten.rangofecha=asincronica.fechaforo and ten.horario=2 and ten.tipoprofesor_id=asincronica.tipoprofesor_id " \
                                                                                                                                                                                                                                                                                        "left join " \
                                                                                                                                                                                                                                                                                        "(select nolab.observaciones, nolab.fecha from sga_diasnolaborable nolab " \
                                                                                                                                                                                                                                                                                        "where nolab.periodo_id=" + str(periodo.id) + ") as nolaborables on nolaborables.fecha = ten.rangofecha " \
                                                                                                                                                                                                                                                                                                                                      "where ten.dia=ten.rangodia and ten.rangofecha <'" + str(hoy) + "' order by ten.rangofecha,materia_id,ten.turno_id,tipohorario"
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    totalsincronica = 0
                    totalasincronica = 0
                    totalplansincronica = 0
                    totalplanasincronica = 0
                    for cuentamarcadas in results:
                        sinasistencia = False
                        if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id=cuentamarcadas[21],  nivelmalla_id=cuentamarcadas[20], status=True).exists():
                            if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id=cuentamarcadas[21], nivelmalla_id=cuentamarcadas[20], fecha=cuentamarcadas[8], status=True).exists():
                                sinasistencia = True
                        else:
                            if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id=cuentamarcadas[21], nivelmalla_id__isnull=True, status=True).exists():
                                if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id=cuentamarcadas[21], nivelmalla_id__isnull=True, fecha=cuentamarcadas[8], status=True).exists():
                                    sinasistencia = True
                            else:
                                if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id__isnull=True, nivelmalla_id__isnull=True, status=True).exists():
                                    if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id__isnull=True, nivelmalla_id__isnull=True, fecha=cuentamarcadas[8], status=True).exists():
                                        sinasistencia = True
                                else:
                                    if periodo.diasnolaborable_set.filter(coordinacion_id__isnull=True, carrera_id__isnull=True, nivelmalla_id__isnull=True, status=True).exists():
                                        if periodo.diasnolaborable_set.filter(coordinacion_id__isnull=True, carrera_id__isnull=True, nivelmalla_id__isnull=True, fecha=cuentamarcadas[8], status=True).exists():
                                            sinasistencia = True
                        listaasistencias.append([cuentamarcadas[0], cuentamarcadas[1], cuentamarcadas[2], cuentamarcadas[3],
                                                 cuentamarcadas[4], cuentamarcadas[5], cuentamarcadas[6], cuentamarcadas[7],
                                                 cuentamarcadas[8], cuentamarcadas[9], cuentamarcadas[10], cuentamarcadas[11],
                                                 cuentamarcadas[12], cuentamarcadas[13], cuentamarcadas[14], cuentamarcadas[15],
                                                 cuentamarcadas[16], cuentamarcadas[17], cuentamarcadas[18], cuentamarcadas[19],
                                                 sinasistencia, cuentamarcadas[24], cuentamarcadas[25], cuentamarcadas[26],
                                                 cuentamarcadas[27], cuentamarcadas[28]])

                        if cuentamarcadas[7] == 2:
                            totalsincronica += 1
                        if cuentamarcadas[7] == 7:
                            totalasincronica += 1
                        totalplansincronica += 1
                        if cuentamarcadas[11]:
                            totalplanasincronica += 1
                    data['listaasistencias'] = listaasistencias
                    data['totalsincronica'] = totalsincronica
                    data['totalasincronica'] = totalasincronica
                    data['totalplansincronica'] = totalplansincronica
                    data['totalplanasincronica'] = totalplanasincronica
                    data['retorno'] = 'pro_personaevaluacion'
                    data['profesor'] = profesor
                    return render(request, "pro_personaevaluacion/verasistencias_link.html", data)
                except Exception as ex:
                    pass

            elif action == 'verasistencias_linkmateria':
                try:
                    data['title'] = u'Detalle clases sincrónicas y asincrónicas'
                    data['hoy'] = hoy = datetime.now().date()
                    cursor = connections['default'].cursor()
                    listaasistencias = []
                    codmateria = int(encrypt(request.GET['materiaid']))
                    profesor = Profesor.objects.get(id=int(encrypt(request.GET['profesorid'])))
                    sql = "select distinct ten.codigoclase,ten.dia,ten.turno_id,ten.inicio,ten.fin,ten.materia_id,ten.tipohorario, " \
                          "ten.horario,ten.rangofecha, " \
                          "ten.rangodia,sincronica.fecha as sincronica,asincronica.fechaforo as asincronica, asignatura, paralelo,asincronica.idforomoodle as idforomoodle,ten.comienza,ten.termina,nolaborables.fecha,nolaborables.observaciones,ten.nivelmalla,ten.idnivelmalla,ten.idcarrera,ten.idcoordinacion,ten.tipoprofesor_id,extract(week from ten.rangofecha::date) as numerosemana,ten.tipoprofesor,asincronica.enlaceuno,asincronica.enlacedos,asincronica.enlacetres " \
                          "from ( select distinct cla.tipoprofesor_id,cla.id as codigoclase, " \
                          "cla.dia,cla.turno_id,cla.inicio,cla.fin,cla.materia_id, " \
                          "cla.tipohorario, " \
                          "case " \
                          "WHEN cla.tipohorario in(2,8)  THEN 2 " \
                          "WHEN cla.tipohorario in(7,9)  THEN 7 " \
                          "end as horario, " \
                          "CURRENT_DATE + generate_series(cla.inicio- CURRENT_DATE, cla.fin - CURRENT_DATE ) as rangofecha, " \
                          "EXTRACT (isodow  FROM  CURRENT_DATE + generate_series(cla.inicio- CURRENT_DATE, cla.fin - CURRENT_DATE )) as rangodia,asig.nombre as asignatura, mate.paralelo as paralelo,tur.comienza,tur.termina,nimalla.nombre as nivelmalla,nimalla.id as idnivelmalla,malla.carrera_id as idcarrera,coorcar.coordinacion_id as idcoordinacion,tipro.nombre as tipoprofesor " \
                          "from sga_clase cla , sga_materia mate, sga_asignaturamalla asimalla,sga_asignatura asig,sga_turno tur,sga_nivel niv,sga_nivelmalla nimalla,sga_malla malla,sga_carrera carre, sga_coordinacion_carrera coorcar, sga_tipoprofesor tipro " \
                          "where cla.materia_id=" + str(codmateria) + " and cla.profesor_id=" + str(profesor.id) + " and cla.materia_id = mate.id and mate.asignaturamalla_id = asimalla.id and asimalla.malla_id=malla.id and asimalla.asignatura_id = asig.id and cla.turno_id=tur.id and asimalla.nivelmalla_id=nimalla.id and malla.carrera_id=carre.id and coorcar.carrera_id=carre.id " \
                                                                                                                   "AND cla.tipohorario IN (8, 9, 2, 7) and mate.nivel_id=niv.id and cla.tipoprofesor_id=tipro.id and niv.periodo_id=" + str(periodo.id) + "  " \
                                                                                                                                                                                                                                                           ") as ten " \
                                                                                                                                                                                                                                                           "left join " \
                                                                                                                                                                                                                                                           "(select clas.materia_id,asi.fecha_creacion::timestamp::date as fecha,asi.fecha_creacion as fecharegistro " \
                                                                                                                                                                                                                                                           "from sga_clasesincronica asi, sga_clase clas " \
                                                                                                                                                                                                                                                           "where asi.clase_id=clas.id and clas.profesor_id=" + str(profesor.id) + " " \
                                                                                                                                                                                                                                                                                                                                   ") as sincronica on ten.rangofecha=fecha and ten.horario=2 " \
                                                                                                                                                                                                                                                                                                                                   "left join " \
                                                                                                                                                                                                                                                                                                                                   "(select  clas.materia_id,asi.fechaforo,asi.idforomoodle, clas.tipoprofesor_id,enlaceuno,enlacedos,enlacetres " \
                                                                                                                                                                                                                                                                                                                                   "from sga_claseasincronica asi, sga_clase clas " \
                                                                                                                                                                                                                                                                                                                                   "where asi.clase_id=clas.id " \
                                                                                                                                                                                                                                                                                                                                   ") as asincronica on asincronica.materia_id=ten.materia_id and ten.rangofecha=asincronica.fechaforo and ten.horario=2 and ten.tipoprofesor_id=asincronica.tipoprofesor_id " \
                                                                                                                                                                                                                                                                                                                                   "left join " \
                                                                                                                                                                                                                                                                                                                                   "(select nolab.observaciones, nolab.fecha from sga_diasnolaborable nolab " \
                                                                                                                                                                                                                                                                                                                                   "where nolab.periodo_id=" + str(periodo.id) + ") as nolaborables on nolaborables.fecha = ten.rangofecha " \
                                                                                                                                                                                                                                                                                                                                                                                 "where ten.dia=ten.rangodia and ten.rangofecha <'" + str(hoy) + "' order by ten.rangofecha,materia_id,ten.turno_id,tipohorario"
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    totalsincronica = 0
                    totalasincronica = 0
                    totalplansincronica = 0
                    totalplanasincronica = 0
                    for cuentamarcadas in results:
                        sinasistencia = False
                        if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id=cuentamarcadas[21],  nivelmalla_id=cuentamarcadas[20], status=True).exists():
                            if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id=cuentamarcadas[21], nivelmalla_id=cuentamarcadas[20], fecha=cuentamarcadas[8], status=True).exists():
                                sinasistencia = True
                        else:
                            if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id=cuentamarcadas[21], nivelmalla_id__isnull=True, status=True).exists():
                                if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id=cuentamarcadas[21], nivelmalla_id__isnull=True, fecha=cuentamarcadas[8], status=True).exists():
                                    sinasistencia = True
                            else:
                                if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id__isnull=True, nivelmalla_id__isnull=True, status=True).exists():
                                    if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id__isnull=True, nivelmalla_id__isnull=True, fecha=cuentamarcadas[8], status=True).exists():
                                        sinasistencia = True
                                else:
                                    if periodo.diasnolaborable_set.filter(coordinacion_id__isnull=True, carrera_id__isnull=True, nivelmalla_id__isnull=True, status=True).exists():
                                        if periodo.diasnolaborable_set.filter(coordinacion_id__isnull=True, carrera_id__isnull=True, nivelmalla_id__isnull=True, fecha=cuentamarcadas[8], status=True).exists():
                                            sinasistencia = True
                        listaasistencias.append([cuentamarcadas[0], cuentamarcadas[1], cuentamarcadas[2], cuentamarcadas[3],
                                                 cuentamarcadas[4], cuentamarcadas[5], cuentamarcadas[6], cuentamarcadas[7],
                                                 cuentamarcadas[8], cuentamarcadas[9], cuentamarcadas[10], cuentamarcadas[11],
                                                 cuentamarcadas[12], cuentamarcadas[13], cuentamarcadas[14], cuentamarcadas[15],
                                                 cuentamarcadas[16], cuentamarcadas[17], cuentamarcadas[18], cuentamarcadas[19],
                                                 sinasistencia, cuentamarcadas[24], cuentamarcadas[25], cuentamarcadas[26],
                                                 cuentamarcadas[27], cuentamarcadas[28]])

                        if cuentamarcadas[7] == 2:
                            totalsincronica += 1
                        if cuentamarcadas[7] == 7:
                            totalasincronica += 1
                        totalplansincronica += 1
                        if cuentamarcadas[11]:
                            totalplanasincronica += 1
                    data['listaasistencias'] = listaasistencias
                    data['totalsincronica'] = totalsincronica
                    data['totalasincronica'] = totalasincronica
                    data['totalplansincronica'] = totalplansincronica
                    data['totalplanasincronica'] = totalplanasincronica
                    data['retorno'] = 'pro_personaevaluacion'
                    data['profesor'] = profesor
                    return render(request, "pro_personaevaluacion/verasistencias_link.html", data)
                except Exception as ex:
                    pass

            elif action == 'asistencias_linkmateria':
                try:
                    data['title'] = u'Detalle clases sincrónicas y asincrónicas'
                    data['hoy'] = hoy = datetime.now().date()
                    cursor = connections['default'].cursor()
                    listaasistencias = []
                    profesor = Profesor.objects.get(id=int(encrypt(request.GET['profesorid'])))
                    sql = "select distinct ten.codigoclase,ten.dia,ten.turno_id,ten.inicio,ten.fin,ten.materia_id,ten.tipohorario, " \
                          "ten.horario,ten.rangofecha, " \
                          "ten.rangodia,sincronica.fecha as sincronica,asincronica.fechaforo as asincronica, asignatura, paralelo,asincronica.idforomoodle as idforomoodle,ten.comienza,ten.termina,nolaborables.fecha,nolaborables.observaciones,ten.nivelmalla,ten.idnivelmalla,ten.idcarrera,ten.idcoordinacion,ten.tipoprofesor_id,extract(week from ten.rangofecha::date) as numerosemana,ten.tipoprofesor,asincronica.enlaceuno,asincronica.enlacedos,asincronica.enlacetres " \
                          "from ( select distinct cla.tipoprofesor_id,cla.id as codigoclase, " \
                          "cla.dia,cla.turno_id,cla.inicio,cla.fin,cla.materia_id, " \
                          "cla.tipohorario, " \
                          "case " \
                          "WHEN cla.tipohorario in(2,8)  THEN 2 " \
                          "WHEN cla.tipohorario in(7,9)  THEN 7 " \
                          "end as horario, " \
                          "CURRENT_DATE + generate_series(cla.inicio- CURRENT_DATE, cla.fin - CURRENT_DATE ) as rangofecha, " \
                          "EXTRACT (isodow  FROM  CURRENT_DATE + generate_series(cla.inicio- CURRENT_DATE, cla.fin - CURRENT_DATE )) as rangodia,asig.nombre as asignatura, mate.paralelo as paralelo,tur.comienza,tur.termina,nimalla.nombre as nivelmalla,nimalla.id as idnivelmalla,malla.carrera_id as idcarrera,coorcar.coordinacion_id as idcoordinacion,tipro.nombre as tipoprofesor " \
                          "from sga_clase cla , sga_materia mate, sga_asignaturamalla asimalla,sga_asignatura asig,sga_turno tur,sga_nivel niv,sga_nivelmalla nimalla,sga_malla malla,sga_carrera carre, sga_coordinacion_carrera coorcar, sga_tipoprofesor tipro " \
                          "where cla.profesor_id=" + str(profesor.id) + " and tipro.id!=10 and cla.materia_id = mate.id and mate.asignaturamalla_id = asimalla.id and asimalla.malla_id=malla.id and asimalla.asignatura_id = asig.id and cla.turno_id=tur.id and asimalla.nivelmalla_id=nimalla.id and malla.carrera_id=carre.id and coorcar.carrera_id=carre.id " \
                                                                        "AND cla.tipohorario IN (8, 9, 2, 7) and mate.nivel_id=niv.id and cla.tipoprofesor_id=tipro.id and niv.periodo_id=" + str(periodo.id) + "  " \
                                                                                                                                                                                                                ") as ten " \
                                                                                                                                                                                                                "left join " \
                                                                                                                                                                                                                "(select clas.materia_id,asi.fecha_creacion::timestamp::date as fecha,asi.fecha_creacion as fecharegistro " \
                                                                                                                                                                                                                "from sga_clasesincronica asi, sga_clase clas " \
                                                                                                                                                                                                                "where asi.clase_id=clas.id and clas.profesor_id=" + str(profesor.id) + " " \
                                                                                                                                                                                                                                                                                        ") as sincronica on ten.rangofecha=fecha and ten.horario=2 " \
                                                                                                                                                                                                                                                                                        "left join " \
                                                                                                                                                                                                                                                                                        "(select  clas.materia_id,asi.fechaforo,asi.idforomoodle, clas.tipoprofesor_id,enlaceuno,enlacedos,enlacetres " \
                                                                                                                                                                                                                                                                                        "from sga_claseasincronica asi, sga_clase clas " \
                                                                                                                                                                                                                                                                                        "where asi.clase_id=clas.id " \
                                                                                                                                                                                                                                                                                        ") as asincronica on asincronica.materia_id=ten.materia_id and ten.rangofecha=asincronica.fechaforo and ten.horario=2 and ten.tipoprofesor_id=asincronica.tipoprofesor_id " \
                                                                                                                                                                                                                                                                                        "left join " \
                                                                                                                                                                                                                                                                                        "(select nolab.observaciones, nolab.fecha from sga_diasnolaborable nolab " \
                                                                                                                                                                                                                                                                                        "where nolab.periodo_id=" + str(periodo.id) + ") as nolaborables on nolaborables.fecha = ten.rangofecha " \
                                                                                                                                                                                                                                                                                                                                      "where ten.dia=ten.rangodia and ten.rangofecha <'" + str(hoy) + "' order by materia_id,ten.rangofecha,ten.turno_id,tipohorario"
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    totalsincronica = 0
                    totalasincronica = 0
                    totalplansincronica = 0
                    totalplanasincronica = 0
                    for cuentamarcadas in results:
                        sinasistencia = False
                        if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id=cuentamarcadas[21],  nivelmalla_id=cuentamarcadas[20], status=True).exists():
                            if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id=cuentamarcadas[21], nivelmalla_id=cuentamarcadas[20], fecha=cuentamarcadas[8], status=True).exists():
                                sinasistencia = True
                        else:
                            if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id=cuentamarcadas[21], nivelmalla_id__isnull=True, status=True).exists():
                                if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id=cuentamarcadas[21], nivelmalla_id__isnull=True, fecha=cuentamarcadas[8], status=True).exists():
                                    sinasistencia = True
                            else:
                                if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id__isnull=True, nivelmalla_id__isnull=True, status=True).exists():
                                    if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id__isnull=True, nivelmalla_id__isnull=True, fecha=cuentamarcadas[8], status=True).exists():
                                        sinasistencia = True
                                else:
                                    if periodo.diasnolaborable_set.filter(coordinacion_id__isnull=True, carrera_id__isnull=True, nivelmalla_id__isnull=True, status=True).exists():
                                        if periodo.diasnolaborable_set.filter(coordinacion_id__isnull=True, carrera_id__isnull=True, nivelmalla_id__isnull=True, fecha=cuentamarcadas[8], status=True).exists():
                                            sinasistencia = True
                        listaasistencias.append([cuentamarcadas[0], cuentamarcadas[1], cuentamarcadas[2], cuentamarcadas[3],
                                                 cuentamarcadas[4], cuentamarcadas[5], cuentamarcadas[6], cuentamarcadas[7],
                                                 cuentamarcadas[8], cuentamarcadas[9], cuentamarcadas[10], cuentamarcadas[11],
                                                 cuentamarcadas[12], cuentamarcadas[13], cuentamarcadas[14], cuentamarcadas[15],
                                                 cuentamarcadas[16], cuentamarcadas[17], cuentamarcadas[18], cuentamarcadas[19],
                                                 sinasistencia, cuentamarcadas[24], cuentamarcadas[25], cuentamarcadas[26],
                                                 cuentamarcadas[27], cuentamarcadas[28]])

                        if cuentamarcadas[7] == 2:
                            totalsincronica += 1
                        if cuentamarcadas[7] == 7:
                            totalasincronica += 1
                        totalplansincronica += 1
                        if cuentamarcadas[11]:
                            totalplanasincronica += 1
                    data['listaasistencias'] = listaasistencias
                    data['totalsincronica'] = totalsincronica
                    data['totalasincronica'] = totalasincronica
                    data['totalplansincronica'] = totalplansincronica
                    data['totalplanasincronica'] = totalplanasincronica
                    data['retorno'] = 'pro_personaevaluacion'
                    data['profesor'] = profesor
                    return render(request, "pro_personaevaluacion/asistencias_linkmateria.html", data)
                except Exception as ex:
                    pass

            elif action == 'vertutorias':
                try:
                    data['title'] = u'Tutorias de acompañamiento acádemico'
                    periodo = request.session['periodo']
                    fini = periodo.inicio
                    ffin = periodo.fin
                    if not 'profesorid' in request.GET:
                        raise NameError('Error')
                    data['profesor'] = profesor = Profesor.objects.get(id=int(encrypt(request.GET['profesorid'])))
                    profesormateria = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__periodo=periodo,tipoprofesor_id__in=[1, 2, 5,6]).distinct().order_by('desde', 'materia__asignatura__nombre')
                    data['tutorias'] = tutorias = AvTutorias.objects.filter(Q(materia__in=profesormateria.values_list('materia__id')), Q(materia__profesormateria__profesor=profesor), Q(fecha__range=(fini, ffin)))
                    return render(request, "pro_personaevaluacion/vertutorias.html", data)
                except Exception as ex:
                    pass

            elif action == 'vermarcadas':
                try:
                    data['title'] = u'Marcadas biométrico del docentes en el periodo'
                    periodo = request.session['periodo']
                    fechas_clases = []
                    fini = periodo.inicio
                    if periodo.fin >= datetime.now().date():
                        ffin = datetime.now().date() - timedelta(days=1)
                    else:
                        ffin = periodo.fin
                    if not 'profesorid' in request.GET:
                        raise NameError('Error')
                    profesor = Profesor.objects.get(pk=int(encrypt(request.GET['profesorid'])))
                    distributivo = ProfesorDistributivoHoras.objects.get(periodo=periodo, profesor=profesor)
                    # permisos **************************************************
                    permisos = PermisoInstitucional.objects.filter(solicita=profesor.persona, permisoinstitucionaldetalle__fechainicio__gte=fini, permisoinstitucionaldetalle__fechafin__lte=ffin, status=True)
                    # profesormateria*********************************************
                    profesormateria = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__periodo=periodo, tipoprofesor_id__in=[1, 2, 5, 6]).distinct().order_by('desde', 'materia__asignatura__nombre')
                    # ASISTENCIA
                    fechas_clases = []
                    for profesormate in profesormateria:
                        data_asistencia = profesormate.asistencia_docente(fini, ffin, periodo)
                        for fecha_clase in data_asistencia['lista_fechas_clases']:
                            if (fecha_clase in fechas_clases) == 0:
                                fechas_clases.append(fecha_clase)
                    # marcadas
                    if distributivo.coordinacion.id == 9:
                        marcadas = LogDia.objects.filter(persona=profesor.persona, fecha__in=fechas_clases,status=True).order_by('fecha')
                    else:
                        marcadas = LogDia.objects.filter(persona=profesor.persona, fecha__gte=fini, fecha__lte=ffin, status=True).order_by('fecha')
                    total = None
                    i = 0
                    subtotal = None
                    totalfinal = 0
                    if marcadas:
                        for m in marcadas:
                            if m.procesado:
                                i = i + 1
                                logmarcada = m.logmarcada_set.filter(status=True).order_by('time')
                                horas1 = logmarcada[0]
                                horas2 = logmarcada[1]
                                formato = "%H:%M:%S"
                                subtotal = datetime.strptime(str(horas2.time.time()), formato) - datetime.strptime(
                                    str(horas1.time.time()), formato)
                                if logmarcada.count() == 4:
                                    horas3 = logmarcada[2]
                                    horas4 = logmarcada[3]
                                    subtotal += datetime.strptime(str(horas4.time.time()), formato) - datetime.strptime(
                                        str(horas3.time.time()), formato)
                                if i == 1:
                                    total = subtotal
                                else:
                                    total = total + subtotal
                    if total:
                        sec = total.total_seconds()
                        hours = sec // 3600
                        minutes = (sec // 60) - (hours * 60)
                        totalfinal = str(int(hours)) + ':' + str(int(minutes)) + ': 00'
                    data['marcadas'] = marcadas
                    data['total'] = totalfinal
                    data['profesor'] = profesor
                    return render(request, "pro_personaevaluacion/marcadas.html", data)
                except Exception as ex:
                    pass

            elif action == 'docgeneral':
                try:
                    data['title'] = u'Recurso del aula virtual'
                    if not 'profesorid' in request.GET:
                        raise NameError('Error')
                    profesor = Profesor.objects.get(pk=int(encrypt(request.GET['profesorid'])))
                    periodo = request.session['periodo']
                    data['materias'] = Materia.objects.filter(profesormateria__profesor=profesor,nivel__periodo=periodo, nivel__periodo__visible=True).distinct().order_by('asignatura')
                    data['profesor'] = profesor
                    return render(request, "pro_personaevaluacion/docgeneral.html", data)
                except Exception as ex:
                    pass

            elif action == 'consultar':
                try:
                    data['title'] = u'Consulta de evaluación en el periodo'
                    data['profesor'] = profesor = Profesor.objects.get(pk=int(request.GET['id']))
                    data['persona'] = persona
                    data['tipoinstrumento'] = tipo = int(request.GET['t'])
                    evaluacion = None
                    if tipo == 3:
                        data['rubricas'] = rubricas = profesor.mis_rubricas_par(periodo, persona)
                        data['evaluacion'] = evaluacion = profesor.dato_evaluado_par_periodo(periodo, persona)
                        data['actividadespar'] = persona.mis_actividades_par(profesor, proceso)
                    if tipo == 4:
                        if proceso.versioninstrumentodirectivo == 2:
                            if proceso.periodo.tipo.id == 3:
                                eMateria = None
                                if 'idm' in request.GET:
                                    data['eMateria'] = eMateria = Materia.objects.get(pk=int(request.GET['idm']))
                                estado = True
                                resultados = RespuestaEvaluacionAcreditacionPosgrado.objects.values('evaluador_id').filter(
                                    status=True,
                                    tipoinstrumento=4,
                                    proceso__periodo=periodo,
                                    profesor=profesor,
                                    materia=eMateria,
                                    respuestarubricaposgrado__rubrica__para_directivo=True).exclude(respuestarubricaposgrado__rubrica__rvigente=True)

                                if resultados.exists():
                                    estado = False

                                lista1 = Rubrica.objects.filter(habilitado=True,
                                                                proceso__periodo=periodo,
                                                                para_directivo=True, rvigente=estado).distinct()

                                data['rubricas'] = rubricas = lista1
                                data['evaluacion'] = evaluacion = dato_evaluado_directivo_periodo(profesor, periodo, persona, eMateria)
                            else:
                                data['rubricas'] = rubricas = profesor.mis_rubricas_directivo_par(periodo, persona)
                        else:
                            data['rubricas'] = rubricas = profesor.mis_rubricas_directivo(periodo)
                            data['evaluacion'] = evaluacion =profesor.dato_evaluado_directivo_periodo(periodo, persona)
                    if tipo == 5:
                        tipoprofe = int(request.GET['tipoprofe'])
                        idmate = int(request.GET['idmate'])
                        data['rubricas'] = rubricas = profesor.mis_rubricas_directivorevision(periodo,tipoprofe)
                        data['evaluacion'] = evaluacion = profesor.dato_evaluado_directivorevision_periodo(periodo, persona, tipoprofe, idmate)
                    data['tiene_docencia'] = rubricas.filter(tipo_criterio=1).exists()
                    data['tiene_investigacion'] = rubricas.filter(tipo_criterio=2).exists()
                    data['tiene_gestion'] = rubricas.filter(tipo_criterio=3).exists()
                    if periodo.tipo.id == 3:
                        return render(request, "pro_personaevaluacion/consultarposgrado.html", data)
                    else:
                        return render(request, "pro_personaevaluacion/consultar.html", data)
                except Exception as ex:
                    pass

            elif action == 'permisoinstitucional':
                try:
                    data['title'] = u'Permiso Institucional.'
                    search = None
                    ids = None
                    # if Departamento.objects.filter(responsable=persona, permisogeneral=True).exists():
                    #     departamento = Departamento.objects.all()
                    # else:
                    #     departamento = Departamento.objects.filter(responsable=persona)
                    profesor = Profesor.objects.get(pk=int(encrypt(request.GET['profesorid'])))
                    personaid = profesor.persona.id

                    plantillas = PermisoInstitucional.objects.filter(solicita__id=personaid, fechasolicitud__gte=periodo.inicio, fechasolicitud__lte=periodo.fin).exclude(solicita=persona).order_by('estadosolicitud', '-fechasolicitud')
                    # if 's' in request.GET:
                    #     search = request.GET['s'].strip()
                    #     ss = search.split(' ')
                    #     if len(ss) == 1:
                    #         plantillas = plantillas.filter(Q(solicita__nombres__icontains=search) |
                    #                                        Q(solicita__apellido1__icontains=search) |
                    #                                        Q(solicita__apellido2__icontains=search) |
                    #                                        Q(solicita__cedula__icontains=search) |
                    #                                        Q(
                    #                                            solicita__pasaporte__icontains=search)).distinct().order_by(
                    #             'estadosolicitud', '-fechasolicitud')
                    #     else:
                    #         plantillas = plantillas.filter(Q(solicita__apellido1__icontains=ss[0]) & Q(
                    #             solicita__apellido2__icontains=ss[1])).distinct().order_by('estadosolicitud',
                    #                                                                        '-fechasolicitud')
                    paging = MiPaginador(plantillas, 20)
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
                    data['permisos'] = page.object_list
                    return render(request, "pro_personaevaluacion/permisoinstitucional.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                # data['profesores_pares'] = profesores_pares = profesores_pares = persona.detalleinstrumentoevaluacionparacreditacion_set.filter(proceso=proceso, status=True).distinct().order_by('evaluado__persona')
                profesores_pares = persona.detalleinstrumentoevaluacionparacreditacion_set.filter(proceso=proceso, status=True).distinct().order_by('evaluado__persona')
                numerofilas = 15
                paging = MiPaginador(profesores_pares, numerofilas)
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
                data['page'] = page
                data['numerofilasguiente'] = numerofilasguiente
                data['numeropagina'] = p
                data['rangospaging'] = paging.rangos_paginado(p)
                data['profesores_pares'] = page.object_list

                data['persona'] = persona
                data['reporte_1'] = obtener_reporte('hoja_vida_sagest')

                # data['profesores_directivos'] = profesores_directivos = Profesor.objects.filter(detalleinstrumentoevaluaciondirectivoacreditacion__evaluador=persona, detalleinstrumentoevaluaciondirectivoacreditacion__proceso=proceso, detalleinstrumentoevaluaciondirectivoacreditacion__status=True).distinct().order_by('persona')
                # profesores_directivos = Profesor.objects.filter(detalleinstrumentoevaluaciondirectivoacreditacion__evaluador=persona, detalleinstrumentoevaluaciondirectivoacreditacion__proceso=proceso, detalleinstrumentoevaluaciondirectivoacreditacion__status=True).distinct().order_by('persona')
                profesores_directivos = persona.detalleinstrumentoevaluaciondirectivoacreditacion_set.filter(proceso=proceso, status=True).distinct().order_by('evaluado__persona')

                if proceso.periodo.tipo.id == 3:
                    data['codigosevaluacion'] = persona.respuestaevaluacionacreditacion_set.values_list('materia_id', flat=True).filter(tipoinstrumento=4, proceso=proceso, profesor_id__in=profesores_directivos.values_list('evaluado_id'))
                    data['codigosevaluacionnew'] = persona.respuestaevaluacionacreditacionposgrado_set.values_list('materia_id', flat=True).filter(tipoinstrumento=4, proceso=proceso, profesor_id__in=profesores_directivos.values_list('evaluado_id'))
                else:
                    data['codigosevaluacion'] = persona.respuestaevaluacionacreditacion_set.values_list('profesor_id', flat=True).filter(tipoinstrumento=4, proceso=proceso, profesor_id__in=profesores_directivos.values_list('evaluado_id'))

                numerofilasdir = 15
                pagingdir = MiPaginador(profesores_directivos, numerofilasdir)
                pdir = 1
                try:
                    paginasesiondir = 1
                    if 'paginadordir' in request.session:
                        paginasesiondir = int(request.session['paginadordir'])
                    if 'pagedir' in request.GET:
                        pdir = int(request.GET['pagedir'])
                        if pdir == 1:
                            numerofilasguientedir = numerofilasdir
                        else:
                            numerofilasguientedir = numerofilasdir * (pdir - 1)
                    else:
                        pdir = paginasesiondir
                        if pdir == 1:
                            numerofilasguientedir = numerofilasdir
                        else:
                            numerofilasguientedir = numerofilasdir * (pdir - 1)
                    try:
                        pagedir = pagingdir.page(pdir)
                    except:
                        pdir = 1
                    pagedir = pagingdir.page(pdir)
                except:
                    pagedir = pagingdir.page(pdir)
                request.session['paginadordir'] = pdir
                data['pagingdir'] = pagingdir
                data['pagedir'] = pagedir
                data['numerofilasguientedir'] = numerofilasguientedir
                data['numeropaginadir'] = pdir
                data['rangospagingdir'] = pagingdir.rangos_paginado(pdir)
                data['profesores_directivos'] = pagedir.object_list

                if not profesores_pares and not profesores_directivos:
                    return HttpResponseRedirect('/?info=No tiene asignado ningun docente para evaluar')
                listadoprofesores = ''
                # comentado por ricardo por motivo que no se dio la evaluacion de rubricas de revision
                # if Carrera.objects.filter(coordinadorcarrera__persona_id=persona.id,  coordinadorcarrera__periodo=periodo).exists():
                #     carreras = Carrera.objects.values_list('id').filter(coordinadorcarrera__persona_id=persona.id, coordinadorcarrera__periodo=periodo).distinct()
                #     if Rubrica.objects.filter(proceso__periodo=periodo, tipoprofesor__isnull=False, status=True).exists():
                #         listatipoprofesor = Rubrica.objects.values_list('tipoprofesor_id').filter(proceso__periodo=periodo, status=True).distinct()
                #         listadoprofesores = ProfesorMateria.objects.filter(materia__nivel__periodo=periodo, materia__asignaturamalla__malla__carrera_id__in=carreras, tipoprofesor_id__in=listatipoprofesor, status=True).order_by('profesor__persona__apellido1')
                data['listadoprofesores'] = listadoprofesores
                data['reporte_2'] = obtener_reporte('detalleevaluacionrevision')
                return render(request, "pro_personaevaluacion/view.html", data)
            except Exception as ex:
                pass
