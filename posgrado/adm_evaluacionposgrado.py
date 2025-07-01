from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction
from sga.commonviews import adduserdata, traerNotificaciones
from django.shortcuts import render
from django.db.models.query_utils import Q
from sga.funciones import MiPaginador, log, notificacion, actualizar_resumen, frecuencia_preguntas_hetero, \
    frecuencia_preguntas_auto, frecuencia_preguntas_dir, cantidad_evaluacion_docente, cantidad_evaluacion_auto, \
    evaluo_director, evaluo_coordinador, cantidad_evaluacion_directivos, respuestasevaluacionaccionmejoras, \
    respuestasevaluacionformacioncontinua, ids_eval_zero, ids_eval_auto, ids_eval_director, ids_eval_coordinador
from sga.models import ProfesorMateria, Carrera, Materia, Persona, DetalleInstrumentoEvaluacionDirectivoAcreditacion, \
    Notificacion, Periodo, Rubrica, MateriaAsignada, Coordinacion
from sagest.models import Departamento
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from posgrado.models import CohorteMaestria, DetalleFechasEvalDirMateria, InscripcionEncuestaSatisfaccionDocente, \
    EscuelaPosgrado, DetalleResultadosEvaluacionPosgrado, RespuestaEvaluacionAcreditacionPosgrado, EncuestaSatisfaccionDocente, PreguntaEncuestaSatisfaccionDocente, \
    OpcionCuadriculaEncuestaSatisfaccionDocente, InscripcionEncuestaSatisfaccionDocente, \
    RespuestaCuadriculaEncuestaSatisfaccionDocente
from posgrado.forms import EditarFechasEvaluacionForm, AsignarFechasMasivoForm, ProcesarResultadosMasivoForm, EncuestaSatisfaccionDocenteForm, PreguntaEncuestaSatisfaccionDocenteForm, OpcionCuadriculaSatisfaccionDocenteForm, \
    EvidenciaColorPreguntaEncuestaForm
from django.template.loader import get_template
import xlsxwriter
import io
from sga.excelbackground import reporte_modulos_posgrado
from typing import Any, Hashable, Iterable, Optional
import ast
from sga.funcionesxhtml2pdf import conviert_html_to_pdf

def number_to_excel_col(num):
    col_str = ""
    while num > 0:
        num, remainder = divmod(num - 1, 26)
        col_str = chr(65 + remainder) + col_str
    return col_str

def buscar_dicc(it: Iterable[dict], clave: Hashable, valor: Any) -> Optional[dict]:
    for dicc in it:
        if dicc[clave] == valor:
            return dicc
    return None

def fecha_vencida(obj, tipo):
    from posgrado.models import DetalleFechasEvalDirMateria
    try:
        estado = 'NO CONFIGURADO'
        if tipo == 1:
            if obj.inicioeval and obj.fineval:
                if datetime.now().date() > obj.fineval:
                    estado = 'FINALIZADA'
                else:
                    estado = 'EN CURSO'
        elif tipo == 2:
            if obj.inicioevalauto and obj.finevalauto:
                if datetime.now().date() > obj.finevalauto:
                    estado = 'FINALIZADA'
                else:
                    estado = 'EN CURSO'
        elif tipo == 3:
            if DetalleFechasEvalDirMateria.objects.filter(status=True, materia=obj).exists():
                eDetalle = DetalleFechasEvalDirMateria.objects.filter(status=True, materia=obj).first()
                if datetime.now().date() > eDetalle.fin:
                    estado = 'FINALIZADA'
                else:
                    estado = 'EN CURSO'
        return estado
    except Exception as ex:
        pass

def object_dir(obj):
    eDetalle = None
    if DetalleFechasEvalDirMateria.objects.filter(status=True, materia=obj.materia).exists():
        eDetalle = DetalleFechasEvalDirMateria.objects.filter(status=True, materia=obj.materia).first()
    return eDetalle

def object_proces(obj):
    eDetalle = None
    if DetalleResultadosEvaluacionPosgrado.objects.filter(status=True, materia=obj.materia).exists():
        eDetalle = DetalleResultadosEvaluacionPosgrado.objects.filter(status=True, materia=obj.materia).first()
    return eDetalle

def cincoacien(valor):
    return round((valor * 100 / 5), 2)

def obj_eval_hetero(obj, mate, evaluador):
    from posgrado.models import RespuestaEvaluacionAcreditacionPosgrado
    objeto = None
    if RespuestaEvaluacionAcreditacionPosgrado.objects.filter(proceso=obj.materia.nivel.periodo.proceso_evaluativo(),
                                                              tipoinstrumento=1, profesor=obj.profesor,
                                                              evaluador=evaluador, materia=obj.materia,
                                                              materiaasignada=mate).exists():
        objeto = RespuestaEvaluacionAcreditacionPosgrado.objects.filter(proceso=obj.materia.nivel.periodo.proceso_evaluativo(),
                                                              tipoinstrumento=1, profesor=obj.profesor,
                                                              evaluador=evaluador, materia=obj.materia,
                                                              materiaasignada=mate).first()

    return objeto

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

        if action == 'editfechashetero':
            try:
                eMateria = Materia.objects.get(pk=int(request.POST['id']))
                f = EditarFechasEvaluacionForm(request.POST)
                f.editar()
                if f.is_valid():
                    eMateria.inicioeval = f.cleaned_data['inicio']
                    eMateria.fineval = f.cleaned_data['fin']
                    eMateria.save(request)
                    log(u'Editó fechas de evaluación hetero: %s' % eMateria, request, "edit")
                    return JsonResponse({"result": False, 'mensaje': 'Edicion Exitosa'})
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editfechasevaluaciones':
            try:
                f = AsignarFechasMasivoForm(request.POST)
                if f.is_valid():
                    if f.cleaned_data['tipo'] == '0':
                        return JsonResponse({"result": True, 'mensaje': 'Seleccione un tipo de evaluación válido'})

                    desde = hasta = escuela = maestria = peri = paralelo = estado = modulo = ''
                    if 'desde' in request.POST:
                        desde = request.POST['desde']

                    if 'hasta' in request.POST:
                        hasta = request.POST['hasta']

                    if 'escuela' in request.POST:
                        escuela = request.POST['escuela']

                    if 'maestria' in request.POST:
                        maestria = request.POST['maestria']

                    if 'periodoa' in request.POST:
                        peri = request.POST['periodoa']

                    if 'paralelo' in request.POST:
                        paralelo = request.POST['paralelo']

                    if 'estado' in request.POST:
                        estado = request.POST['estado']

                    if 'modulo' in request.POST:
                        modulo = request.POST['modulo']

                    filtro = Q(status=True, materia__nivel__periodo__tipo__id=3, tipoprofesor__id=11, materia__fin__lt=datetime.now().date())
                    filtro2 = None

                    if escuela:
                        filtro = filtro & Q(materia__asignaturamalla__malla__carrera__escuelaposgrado__id=int(escuela))

                    if maestria:
                        filtro = filtro & Q(materia__asignaturamalla__malla__carrera__id=int(maestria))

                    if peri:
                        filtro = filtro & Q(materia__nivel__periodo_id=int(peri))

                    if paralelo:
                        filtro = filtro & Q(materia__paralelo=paralelo)

                    if modulo:
                        if int(modulo) == 1:
                            filtro = filtro & Q(materia__cerrado=True)
                        elif int(modulo) == 2:
                            filtro = filtro & Q(materia__cerrado=True)

                    if desde and hasta:
                        filtro = filtro & Q(materia__fin__range=(desde, hasta))
                    elif desde:
                        filtro = filtro & Q(materia__fin__gte=desde)
                    elif hasta:
                        filtro = filtro & Q(materia__fin__lte=hasta)

                    if estado:
                        if int(estado) == 1:
                            filtro = filtro & Q(materia__inicioeval__isnull=True)
                        elif int(estado) == 2:
                            filtro = filtro & Q(materia__inicioevalauto__isnull=True)
                        elif int(estado) == 3:
                            query = ProfesorMateria.objects.filter(filtro).order_by('-id')
                            iddet = DetalleFechasEvalDirMateria.objects.filter(
                                materia__id__in=query.values_list('materia__id', flat=True)).values_list('materia__id',
                                                                                                         flat=True).distinct()
                            query = ProfesorMateria.objects.filter(filtro).order_by('-id').exclude(
                                materia__id__in=iddet)
                            filtro = filtro & Q(materia__id__in=query.values_list('materia__id', flat=True).distinct())
                        if int(estado) == 4:
                            filtro = filtro & Q(materia__inicioeval__isnull=False)
                        elif int(estado) == 5:
                            filtro = filtro & Q(materia__inicioevalauto__isnull=False)
                        elif int(estado) == 6:
                            query = ProfesorMateria.objects.filter(filtro).order_by('-id')
                            iddet = DetalleFechasEvalDirMateria.objects.filter(
                                materia__id__in=query.values_list('materia__id', flat=True)).distinct()
                            filtro = filtro & Q(materia__id__in=iddet)
                        elif int(estado) == 7:
                            query = ProfesorMateria.objects.filter(filtro).order_by('-id')
                            iddet = DetalleResultadosEvaluacionPosgrado.objects.filter(
                                materia__id__in=query.values_list('materia__id', flat=True)).values_list('materia__id',
                                                                                                         flat=True).distinct()
                            filtro = filtro & Q(materia__id__in=iddet)
                        elif int(estado) == 8:
                            query = ProfesorMateria.objects.filter(filtro).order_by('-id')
                            iddet = DetalleResultadosEvaluacionPosgrado.objects.filter(
                                materia__id__in=query.values_list('materia__id', flat=True)).values_list('materia__id',
                                                                                                         flat=True).distinct()
                            query = ProfesorMateria.objects.filter(filtro).order_by('-id').exclude(
                                materia__id__in=iddet)
                            filtro = filtro & Q(materia__id__in=query.values_list('materia__id', flat=True).distinct())
                        elif int(estado) == 9:
                            query = ProfesorMateria.objects.filter(filtro).order_by('-id')
                            iddet = InscripcionEncuestaSatisfaccionDocente.objects.filter(status=True, materiaasignada__materia__id__in=query.values_list('materia__id', flat=True), encuesta__tipo=2).values_list('materiaasignada__materia__id', flat=True).order_by('materiaasignada__materia__id').distinct()
                            filtro = filtro & Q(materia__id__in=iddet)
                        elif int(estado) == 10:
                            query = ProfesorMateria.objects.filter(filtro).order_by('-id')
                            iddet = InscripcionEncuestaSatisfaccionDocente.objects.filter(status=True, materiaasignada__materia__id__in=query.values_list('materia__id', flat=True), encuesta__tipo=2).values_list('materiaasignada__materia__id', flat=True).order_by('materiaasignada__materia__id').distinct()
                            query = ProfesorMateria.objects.filter(filtro).order_by('-id').exclude(materia__id__in=iddet)
                            filtro = filtro & Q(materia__id__in=query.values_list('materia__id', flat=True).distinct())
                        elif int(estado) == 11:
                            query = ProfesorMateria.objects.filter(filtro).order_by('-id')
                            ids = ids_eval_zero(query.values_list('id', flat=True))
                            filtro2 = Q(status=True, materia__nivel__periodo__tipo__id=3, tipoprofesor__id=11, materia__fin__lt=datetime.now().date(), materia__id__in=ids)
                        elif int(estado) == 12:
                            query = ProfesorMateria.objects.filter(filtro).order_by('-id')
                            ids = ids_eval_auto(query.values_list('id', flat=True))
                            filtro2 = Q(status=True, materia__nivel__periodo__tipo__id=3, tipoprofesor__id=11, materia__fin__lt=datetime.now().date(), materia__id__in=ids)
                        elif int(estado) == 13:
                            query = ProfesorMateria.objects.filter(filtro).order_by('-id')
                            ids = ids_eval_director(query.values_list('id', flat=True))
                            filtro2 = Q(status=True, materia__nivel__periodo__tipo__id=3, tipoprofesor__id=11, materia__fin__lt=datetime.now().date(), materia__id__in=ids)
                        elif int(estado) == 14:
                            query = ProfesorMateria.objects.filter(filtro).order_by('-id')
                            ids = ids_eval_coordinador(query.values_list('id', flat=True))
                            filtro2 = Q(status=True, materia__nivel__periodo__tipo__id=3, tipoprofesor__id=11, materia__fin__lt=datetime.now().date(), materia__id__in=ids)

                    if filtro2:
                        eProfesorMaterias = ProfesorMateria.objects.filter(filtro2).order_by('-id')
                    else:
                        eProfesorMaterias = ProfesorMateria.objects.filter(filtro).order_by('-id')

                    for eProfesorMateria in eProfesorMaterias:
                        if f.cleaned_data['tipo'] == '1':
                            if f.cleaned_data['config']:
                                eProfesorMateria.materia.inicioeval = datetime.now().date()
                                eProfesorMateria.materia.fineval = datetime.now().date() + timedelta(days=f.cleaned_data['dias'])
                            else:
                                eProfesorMateria.materia.inicioeval = f.cleaned_data['inicio']
                                eProfesorMateria.materia.fineval = f.cleaned_data['fin']
                            eProfesorMateria.materia.save(request)
                            log(u'Editó fechas de evaluación hetero: %s' % eProfesorMateria.materia, request, "edit")
                        elif f.cleaned_data['tipo'] == '2':
                            if f.cleaned_data['config']:
                                eProfesorMateria.materia.inicioevalauto = datetime.now().date()
                                eProfesorMateria.materia.finevalauto = datetime.now().date() + timedelta(days=f.cleaned_data['dias'])
                            else:
                                eProfesorMateria.materia.inicioevalauto = f.cleaned_data['inicio']
                                eProfesorMateria.materia.finevalauto = f.cleaned_data['fin']
                            eProfesorMateria.materia.save(request)
                            eProfesorMateria = eProfesorMateria.materia.profesores_materia2()[0]
                            titulo = 'AUTOEVALUACIÓN PENDIENTE'
                            cuerpo = f'Saludos, Msc. {eProfesorMateria.profesor.persona}, módulo: {eProfesorMateria.materia.asignatura}, paralelo {eProfesorMateria.materia.paralelo}, cohorte {eProfesorMateria.materia.nivel.periodo}. La evaluación estará activa desde {eProfesorMateria.materia.inicioevalauto} hasta {eProfesorMateria.materia.finevalauto}. Por favor, realizarla en el tiempo acordado.'
                            notificacion(titulo, cuerpo,
                                         eProfesorMateria.profesor.persona, None, '/pro_autoevaluacion',
                                         eProfesorMateria.profesor.persona.pk, 1, 'sga',
                                         eProfesorMateria.profesor.persona, None)
                            log(u'Notificó autoevaluación: %s' % eProfesorMateria.profesor.persona, request, "edit")
                            log(u'Editó fechas de evaluación auto: %s' % eProfesorMateria.materia, request, "edit")
                        elif f.cleaned_data['tipo'] == '3':
                            proceso = eProfesorMateria.materia.nivel.periodo.proceso_evaluativoacreditacion()
                            lista = []
                            eCarrera = eProfesorMateria.materia.asignaturamalla.malla.carrera
                            if eCarrera.escuelaposgrado:
                                if eCarrera.escuelaposgrado.id == 1:
                                    eDirector = Persona.objects.get(pk=Departamento.objects.get(pk=216).responsable.id)
                                    lista.append(eDirector.id)
                                elif eCarrera.escuelaposgrado.id == 2:
                                    eDirector = Persona.objects.get(pk=Departamento.objects.get(pk=215).responsable.id)
                                    lista.append(eDirector.id)
                                elif eCarrera.escuelaposgrado.id == 3:
                                    eDirector = Persona.objects.get(pk=Departamento.objects.get(pk=163).responsable.id)
                                    lista.append(eDirector.id)
                                else:
                                    return JsonResponse(
                                        {"result": True, 'message': 'No existe director de escuela para esta carrera'})
                            else:
                                return JsonResponse(
                                    {"result": True, 'message': 'No existe director de escuela para esta carrera'})

                            if CohorteMaestria.objects.filter(status=True, maestriaadmision__carrera=eCarrera).exists():
                                eCoordinador = CohorteMaestria.objects.filter(status=True,
                                                                              maestriaadmision__carrera=eCarrera).order_by(
                                    '-id').first().coordinador
                                lista.append(eCoordinador.id)
                            else:
                                return JsonResponse({"result": True, 'message': 'No existe coordinador de escuela para esta carrera'})

                            evaluadores = Persona.objects.filter(id__in=lista)

                            for evaluador in evaluadores:
                                tipodirector = 1
                                if proceso.paresinvestigacionvinculacion_set.values('id').filter(persona=evaluador,
                                                                                                 tipo=2,
                                                                                                 activo=True,
                                                                                                 status=True).exists():
                                    tipodirector = 2
                                if proceso.paresinvestigacionvinculacion_set.values('id').filter(persona=evaluador,
                                                                                                 tipo=3,
                                                                                                 activo=True,
                                                                                                 status=True).exists():
                                    tipodirector = 3
                                if not DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.filter(status=True,
                                                                                                        proceso=proceso,
                                                                                                        coordinacion_id=7,
                                                                                                        evaluado=eProfesorMateria.profesor,
                                                                                                        evaluador=evaluador,
                                                                                                        materia=eProfesorMateria.materia).exists():
                                    detalle = DetalleInstrumentoEvaluacionDirectivoAcreditacion(proceso=proceso,
                                                                                                evaluado=eProfesorMateria.profesor,
                                                                                                coordinacion_id=7,
                                                                                                evaluador=evaluador,
                                                                                                tipodirector=tipodirector,
                                                                                                materia=eProfesorMateria.materia)
                                    detalle.save(request)
                                else:
                                    detalle = DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.filter(
                                        status=True,
                                        proceso=proceso,
                                        coordinacion_id=7,
                                        evaluado=eProfesorMateria.profesor,
                                        evaluador=evaluador,
                                        materia=eProfesorMateria.materia).first()

                                # detalle.inicio = f.cleaned_data['inicio']
                                # detalle.fin = f.cleaned_data['fin']
                                if f.cleaned_data['config']:
                                    detalle.inicio = datetime.now().date()
                                    detalle.fin = datetime.now().date() + timedelta(days=f.cleaned_data['dias'])
                                else:
                                    detalle.inicio = f.cleaned_data['inicio']
                                    detalle.fin = f.cleaned_data['fin']

                                detalle.save(request)

                                if not evaluo_director(eProfesorMateria):
                                        titulo = 'EVALUACIÓN DE DIRECTIVOS PENDIENTE'
                                        cuerpo = f'Saludos, el docente a evaluar es: Msc. {detalle.evaluado.persona}, módulo: {detalle.materia.asignatura}, paralelo {detalle.materia.paralelo}, cohorte {detalle.materia.nivel.periodo}. La evaluación estará activa desde {proceso.instrumentodirectivoinicio} hasta {proceso.instrumentodirectivofin}. Por favor, realizarla en el tiempo acordado.'
                                        notificacion(titulo, cuerpo,
                                                     detalle.evaluador, None, '/pro_personaevaluacion',
                                                     detalle.evaluador.pk, 1, 'sga',
                                                     detalle.evaluador, None)
                                        log(u'Adiciono directivo evaluador en evaluación docente: proceso[%s] - profesor[%s] - direcEva[%s]' % (proceso, eProfesorMateria.profesor, evaluador), request, "add")

                                if not evaluo_coordinador(eProfesorMateria):
                                    titulo = 'EVALUACIÓN DE DIRECTIVOS PENDIENTE'
                                    cuerpo = f'Saludos, el docente a evaluar es: Msc. {detalle.evaluado.persona}, módulo: {detalle.materia.asignatura}, paralelo {detalle.materia.paralelo}, cohorte {detalle.materia.nivel.periodo}. La evaluación estará activa desde {proceso.instrumentodirectivoinicio} hasta {proceso.instrumentodirectivofin}. Por favor, realizarla en el tiempo acordado.'
                                    notificacion(titulo, cuerpo,
                                                 detalle.evaluador, None, '/pro_personaevaluacion',
                                                 detalle.evaluador.pk, 1, 'sga',
                                                 detalle.evaluador, None)
                                    log(u'Adiciono directivo evaluador en evaluación docente: proceso[%s] - profesor[%s] - direcEva[%s]' % (proceso, eProfesorMateria.profesor, evaluador), request, "add")

                            if not DetalleFechasEvalDirMateria.objects.filter(status=True, materia=eProfesorMateria.materia).exists():
                                eDetalle = DetalleFechasEvalDirMateria(materia=eProfesorMateria.materia)
                                eDetalle.save(request)
                            else:
                                eDetalle = DetalleFechasEvalDirMateria.objects.filter(status=True, materia=eProfesorMateria.materia).first()

                            if f.cleaned_data['config']:
                                eDetalle.inicio = datetime.now().date()
                                eDetalle.fin = datetime.now().date() + timedelta(days=f.cleaned_data['dias'])
                            else:
                                eDetalle.inicio = f.cleaned_data['inicio']
                                eDetalle.fin = f.cleaned_data['fin']
                            eDetalle.save(request)
                            log(u'Editó fechas de evaluación de directivos: %s' % eProfesorMateria.materia, request, "edit")
                        elif f.cleaned_data['tipo'] == '4':
                            if not InscripcionEncuestaSatisfaccionDocente.objects.filter(status=True,
                                                                                         profesormateria=eProfesorMateria,
                                                                                         encuesta=f.cleaned_data['encuesta']).exists():
                                if f.cleaned_data['config']:
                                    eInscripcion = InscripcionEncuestaSatisfaccionDocente(encuesta=f.cleaned_data['encuesta'],
                                                                                          profesormateria=eProfesorMateria,
                                                                                          inicio=datetime.now().date(),
                                                                                          fin=datetime.now().date() + timedelta(days=f.cleaned_data['dias']))
                                    eInscripcion.save(request)
                                else:
                                    eInscripcion = InscripcionEncuestaSatisfaccionDocente(encuesta=f.cleaned_data['encuesta'],
                                                                                          profesormateria=eProfesorMateria,
                                                                                          inicio=f.cleaned_data['inicio'],
                                                                                          fin=f.cleaned_data['fin'])
                                    eInscripcion.save(request)

                                log(u'Adicionó encuesta de satisfacción: %s' % eInscripcion, request, "add")
                            else:
                                eInscripcion = InscripcionEncuestaSatisfaccionDocente.objects.filter(status=True,
                                                                                                     profesormateria=eProfesorMateria,
                                                                                                     encuesta=f.cleaned_data['encuesta']).first()
                                if f.cleaned_data['config']:
                                    eInscripcion.inicio = datetime.now().date()
                                    eInscripcion.fin = datetime.now().date() + timedelta(days=f.cleaned_data['dias'])
                                else:
                                    eInscripcion.inicio = f.cleaned_data['inicio']
                                    eInscripcion.fin = f.cleaned_data['fin']
                                eInscripcion.save(request)
                                log(u'Actualizó fechas de encuestado de satisfacción: %s' % eInscripcion, request, "edit")

                            titulo = 'ENCUESTA DE SATISFACCIÓN'
                            cuerpo = f'Saludos, Msc. {eProfesorMateria.profesor.persona}, módulo: {eProfesorMateria.materia.asignatura}, paralelo {eProfesorMateria.materia.paralelo}, cohorte {eProfesorMateria.materia.nivel.periodo}. La ENCUESTA estará activa desde {eInscripcion.inicio} hasta {eInscripcion.fin}. Por favor, realizarla en el tiempo acordado.'
                            notificacion(titulo, cuerpo,
                                         eProfesorMateria.profesor.persona, None, '/pro_autoevaluacion',
                                         eProfesorMateria.profesor.persona.pk, 1, 'sga',
                                         eProfesorMateria.profesor.persona, None)

                    return JsonResponse({"result": False, 'mensaje': 'Edicion Exitosa'})
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'procesarresultadosmasivo':
            try:
                f = ProcesarResultadosMasivoForm(request.POST)
                if f.is_valid():
                    eIdsModulos = request.POST['ids'].split(',')

                    for eId in eIdsModulos:
                        eModulo = ProfesorMateria.objects.get(pk=eId)
                        frecuencia_preguntas_hetero(eModulo)
                        cantidad_hetero = cantidad_evaluacion_docente(eModulo)

                        frecuencia_preguntas_auto(eModulo)
                        evaluo_auto = False
                        cantidad_auto = cantidad_evaluacion_auto(eModulo)
                        if cantidad_auto > 0:
                            evaluo_auto = True

                        frecuencia_preguntas_dir(eModulo)

                        director = evaluo_director(eModulo)
                        coordinador = evaluo_coordinador(eModulo)

                        distributivo = eModulo.profesor.distributivohoraseval(eModulo.materia.nivel.periodo)
                        if distributivo:
                            resumen = distributivo.resumen_evaluacion_acreditacion()
                            res = actualizar_resumen(resumen, eModulo.materia.id)

                            if res == 'procesado':
                                eDetalle = DetalleResultadosEvaluacionPosgrado(materia=eModulo.materia,
                                                                               procesado=True,
                                                                               descripcion='Ejecución exitosa',
                                                                               total=cantidad_hetero,
                                                                               auto=evaluo_auto,
                                                                               director=director,
                                                                               coordinador=coordinador)
                                eDetalle.save(request)
                                log(u'Procesó resultados de: %s' % eDetalle.materia, request, "edit")
                            else:
                                return JsonResponse({"result": True,
                                                     "mensaje": f"Ha ocurrido un error al procesar los resultados. Intente más tarde"})
                        else:
                            return JsonResponse({"result": True,
                                                 "mensaje": f"El módulo {eModulo.materia} no cuenta con horas de distributivo"})
                    return JsonResponse({"result": False, 'mensaje': 'Edicion Exitosa'})
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editfechasauto':
            try:
                eMateria = Materia.objects.get(pk=int(request.POST['id']))
                f = EditarFechasEvaluacionForm(request.POST)
                f.editar()
                if f.is_valid():
                    eMateria.inicioevalauto = f.cleaned_data['inicio']
                    eMateria.finevalauto = f.cleaned_data['fin']
                    eMateria.save(request)

                    eProfesorMateria = eMateria.profesores_materia2()[0]
                    titulo = 'AUTOEVALUACIÓN PENDIENTE'
                    cuerpo = f'Saludos, Msc. {eProfesorMateria.profesor.persona}, módulo: {eProfesorMateria.materia.asignatura}, paralelo {eProfesorMateria.materia.paralelo}, cohorte {eProfesorMateria.materia.nivel.periodo}. La evaluación estará activa desde {eProfesorMateria.materia.inicioevalauto} hasta {eProfesorMateria.materia.finevalauto}. Por favor, realizarla en el tiempo acordado.'
                    notificacion(titulo, cuerpo,
                                 eProfesorMateria.profesor.persona, None, '/pro_autoevaluacion',
                                 eProfesorMateria.profesor.persona.pk, 1, 'sga',
                                 eProfesorMateria.profesor.persona, None)
                    log(u'Notificó autoevaluación: %s' % eProfesorMateria.profesor.persona, request, "edit")

                    log(u'Editó fechas de evaluación auto: %s' % eMateria, request, "edit")
                    return JsonResponse({"result": False, 'mensaje': 'Edicion Exitosa'})
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editfechasdir':
            try:
                eProfesorMateria = ProfesorMateria.objects.get(pk=int(request.POST['id']))
                proceso = eProfesorMateria.materia.nivel.periodo.proceso_evaluativoacreditacion()
                lista = []
                eCarrera = eProfesorMateria.materia.asignaturamalla.malla.carrera
                if eCarrera.escuelaposgrado:
                    if eCarrera.escuelaposgrado.id == 1:
                        eDirector = Persona.objects.get(pk=Departamento.objects.get(pk=216).responsable.id)
                        lista.append(eDirector.id)
                    elif eCarrera.escuelaposgrado.id == 2:
                        eDirector = Persona.objects.get(pk=Departamento.objects.get(pk=215).responsable.id)
                        lista.append(eDirector.id)
                    elif eCarrera.escuelaposgrado.id == 3:
                        eDirector = Persona.objects.get(pk=Departamento.objects.get(pk=163).responsable.id)
                        lista.append(eDirector.id)
                    else:
                        return JsonResponse({"result": True, 'message': 'No existe director de escuela para esta carrera'})
                else:
                    return JsonResponse({"result": True, 'message': 'No existe director de escuela para esta carrera'})

                if CohorteMaestria.objects.filter(status=True, maestriaadmision__carrera=eCarrera).exists():
                    eCoordinador = CohorteMaestria.objects.filter(status=True,
                                                                  maestriaadmision__carrera=eCarrera).order_by('-id').first().coordinador
                    lista.append(eCoordinador.id)
                else:
                    return JsonResponse({"result": True, 'message': 'No existe coordinador de escuela para esta carrera'})

                evaluadores = Persona.objects.filter(id__in=lista)

                eDetalle = DetalleFechasEvalDirMateria.objects.filter(status=True, materia=eProfesorMateria.materia).first()
                f = EditarFechasEvaluacionForm(request.POST)
                f.editar_2()
                if f.is_valid():
                    for evaluador in evaluadores:
                        tipodirector = 1
                        if proceso.paresinvestigacionvinculacion_set.values('id').filter(persona=evaluador, tipo=2,
                                                                                         activo=True,
                                                                                         status=True).exists():
                            tipodirector = 2
                        if proceso.paresinvestigacionvinculacion_set.values('id').filter(persona=evaluador, tipo=3,
                                                                                         activo=True,
                                                                                         status=True).exists():
                            tipodirector = 3
                        if not DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.filter(status=True,
                                                                                                proceso=proceso,
                                                                                                coordinacion_id=7,
                                                                                                evaluado=eProfesorMateria.profesor,
                                                                                                evaluador=evaluador,
                                                                                                materia=eProfesorMateria.materia).exists():
                            detalle = DetalleInstrumentoEvaluacionDirectivoAcreditacion(proceso=proceso,
                                                                                        evaluado=eProfesorMateria.profesor,
                                                                                        coordinacion_id=7,
                                                                                        evaluador=evaluador,
                                                                                        tipodirector=tipodirector,
                                                                                        materia=eProfesorMateria.materia)
                            detalle.save(request)

                            log(u'Adiciono directivo evaluador en evaluación docente: proceso[%s] - profesor[%s] - direcEva[%s]' % (
                            proceso, eProfesorMateria.profesor, evaluador), request, "add")
                        else:
                            detalle = DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.filter(status=True,
                                                                                                proceso=proceso,
                                                                                                coordinacion_id=7,
                                                                                                evaluado=eProfesorMateria.profesor,
                                                                                                evaluador=evaluador,
                                                                                                materia=eProfesorMateria.materia).first()

                        detalle.inicio = f.cleaned_data['inicio']
                        detalle.fin = f.cleaned_data['fin']
                        detalle.save(request)

                    eDetalle.inicio = f.cleaned_data['inicio']
                    eDetalle.fin = f.cleaned_data['fin']
                    eDetalle.save(request)

                    log(u'Editó fechas de evaluación de directivos: %s' % eProfesorMateria.materia, request, "edit")
                    return JsonResponse({"result": False, 'mensaje': 'Edicion Exitosa'})
                else:
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addfechassatis':
            try:
                profesormateria = ProfesorMateria.objects.get(pk=int(request.POST['id']))
                f = EditarFechasEvaluacionForm(request.POST)
                f.editar_3()
                if f.is_valid():
                    if not InscripcionEncuestaSatisfaccionDocente.objects.filter(status=True,
                                                                                 profesormateria=profesormateria,
                                                                                 encuesta=f.cleaned_data['encuesta']).exists():
                        eInscripcion = InscripcionEncuestaSatisfaccionDocente(encuesta=f.cleaned_data['encuesta'],
                                                                              profesormateria=profesormateria,
                                                                              inicio=f.cleaned_data['inicio'],
                                                                              fin=f.cleaned_data['fin'])
                        eInscripcion.save(request)

                        log(u'Adicionó encuesta de satisfacción: %s' % eInscripcion, request, "add")
                    else:
                        eInscripcion = InscripcionEncuestaSatisfaccionDocente.objects.filter(status=True,
                                                                                             profesormateria=profesormateria,
                                                                                             encuesta=f.cleaned_data['encuesta']).first()
                        eInscripcion.inicio = f.cleaned_data['inicio']
                        eInscripcion.fin = f.cleaned_data['fin']
                        eInscripcion.save(request)
                        log(u'Actualizó fechas de encuestado de satisfacción: %s' % eInscripcion, request, "edit")

                    titulo = 'ENCUESTA DE SATISFACCIÓN'
                    cuerpo = f'Saludos, Msc. {profesormateria.profesor.persona}, módulo: {profesormateria.materia.asignatura}, paralelo {profesormateria.materia.paralelo}, cohorte {profesormateria.materia.nivel.periodo}. La ENCUESTA estará activa desde {eInscripcion.inicio} hasta {eInscripcion.fin}. Por favor, realizarla en el tiempo acordado.'
                    notificacion(titulo, cuerpo,
                                 profesormateria.profesor.persona, None, '/pro_autoevaluacion',
                                 profesormateria.profesor.persona.pk, 1, 'sga',
                                 profesormateria.profesor.persona, None)
                    log(u'Notificó encuesta de satisfacción: %s' % profesormateria.profesor.persona, request, "edit")
                    return JsonResponse({"result": False, 'mensaje': 'Edicion Exitosa'})
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addfechassatis_est':
            try:
                profesormateria = ProfesorMateria.objects.get(pk=int(request.POST['id']))
                eMatriculados = MateriaAsignada.objects.filter(status=True, matricula__estado_matricula__in=[2, 3], materia=profesormateria.materia,
                                                               matricula__retiradomatricula=False)

                f = EditarFechasEvaluacionForm(request.POST)
                f.editar_3()
                if f.is_valid():
                    for eMatriculado in eMatriculados:
                        if not InscripcionEncuestaSatisfaccionDocente.objects.filter(status=True,
                                                                                     materiaasignada=eMatriculado,
                                                                                     encuesta=f.cleaned_data['encuesta']).exists():
                            eInscripcion = InscripcionEncuestaSatisfaccionDocente(encuesta=f.cleaned_data['encuesta'],
                                                                                  materiaasignada=eMatriculado,
                                                                                  inicio=f.cleaned_data['inicio'],
                                                                                  fin=f.cleaned_data['fin'])
                            eInscripcion.save(request)

                            log(u'Adicionó encuesta de satisfacción: %s' % eInscripcion, request, "add")
                        else:
                            eInscripcion = InscripcionEncuestaSatisfaccionDocente.objects.filter(status=True,
                                                                                                 materiaasignada=eMatriculado,
                                                                                                 encuesta=f.cleaned_data['encuesta']).first()
                            eInscripcion.inicio = f.cleaned_data['inicio']
                            eInscripcion.fin = f.cleaned_data['fin']
                            eInscripcion.save(request)
                            log(u'Actualizó fechas de encuestado de satisfacción: %s' % eInscripcion, request, "edit")

                        titulo = 'ENCUESTA DE SATISFACCIÓN'
                        cuerpo = f'Saludos, {eMatriculado.matricula.inscripcion.persona}, módulo: {profesormateria.materia.asignatura}, paralelo {profesormateria.materia.paralelo}, cohorte {profesormateria.materia.nivel.periodo}. La ENCUESTA de satisfacción estará activa desde {eInscripcion.inicio} hasta {eInscripcion.fin}. Por favor, realizarla en el tiempo acordado.'
                        notificacion(titulo, cuerpo,
                                     eMatriculado.matricula.inscripcion.persona, None, '/pro_autoevaluacion',
                                     eMatriculado.matricula.inscripcion.persona.pk, 1, 'sga',
                                     eMatriculado.matricula.inscripcion.persona, None)
                        log(u'Notificó encuesta de satisfacción: %s' % eMatriculado.matricula.inscripcion.persona, request, "edit")
                    return JsonResponse({"result": False, 'mensaje': 'Edicion Exitosa'})
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'procesar_resultados':
            try:
                eModulo = ProfesorMateria.objects.get(pk=int(request.POST['id']))
                frecuencia_preguntas_hetero(eModulo)
                cantidad_hetero = cantidad_evaluacion_docente(eModulo)

                frecuencia_preguntas_auto(eModulo)
                evaluo_auto = False
                cantidad_auto = cantidad_evaluacion_auto(eModulo)
                if cantidad_auto > 0:
                    evaluo_auto = True

                frecuencia_preguntas_dir(eModulo)

                director = evaluo_director(eModulo)
                coordinador = evaluo_coordinador(eModulo)

                distributivo = eModulo.profesor.distributivohoraseval(eModulo.materia.nivel.periodo)
                if distributivo:
                    resumen = distributivo.resumen_evaluacion_acreditacion()
                    res = actualizar_resumen(resumen, eModulo.materia.id)

                    if res == 'procesado':
                        eDetalle = DetalleResultadosEvaluacionPosgrado(materia=eModulo.materia,
                                                                       procesado=True,
                                                                       descripcion='Ejecución exitosa',
                                                                       total=cantidad_hetero,
                                                                       auto=evaluo_auto,
                                                                       director=director,
                                                                       coordinador=coordinador)
                        eDetalle.save(request)
                        log(u'Procesó resultados de: %s' % eDetalle.materia, request, "edit")
                        return JsonResponse({"result": 'ok', "mensaje": u"Resultados procesados correctamente"})
                    else:
                        return JsonResponse({"result": 'bad',
                                             "mensaje": f"Ha ocurrido un error al procesar los resultados. Intente más tarde"})
                else:
                    return JsonResponse({"result": 'bad', "mensaje": f"El módulo {eModulo.materia} no cuenta con horas de distributivo"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": 'bad', "mensaje": f"Ocurrio un error al eliminar: {ex.__str__()}"})

        elif action == 'informeevaluacionipecotro2':
            mensaje = "Problemas al generar el informe."
            try:
                eMateria = Materia.objects.get(pk=request.POST['idmat'])
                eProfesorMateria = ProfesorMateria.objects.filter(status=True, materia=eMateria, tipoprofesor__id__in=[11], materia__nivel__periodo=eMateria.nivel.periodo).first()
                proceso = eMateria.nivel.periodo.proceso_evaluativoacreditacion()
                coordinacionprofesor = Coordinacion.objects.get(pk=7)
                eEvalConfig = DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.filter(status=True, proceso=proceso, coordinacion=coordinacionprofesor, evaluado=eProfesorMateria.profesor, materia=eMateria).values_list('evaluador__id', flat=True).order_by('evaluador__id').distinct().count()
                hoy = datetime.now().date()

                return conviert_html_to_pdf('niveles/informeevaluacionipec2.html',
                                            {'pagesize': 'A4',
                                             'eMateria': eMateria,
                                             'eMatriculados': eMateria.cantidad_matriculas_materia_sin_retirados(),
                                             'eEvalConfig': eEvalConfig,
                                             'eProfesorMateria': eProfesorMateria,
                                             'eEvaluadoresHetero': cantidad_evaluacion_docente(eProfesorMateria),
                                             'eEvaluadoresAuto': cantidad_evaluacion_auto(eProfesorMateria),
                                             'eEvaluadoresDir': cantidad_evaluacion_directivos(eProfesorMateria),

                                             'eEvaluoDir': evaluo_director(eProfesorMateria),
                                             'eEvaluoCor': evaluo_coordinador(eProfesorMateria),


                                             'frecuencia_preguntas_hetero': frecuencia_preguntas_hetero(eProfesorMateria),
                                             'frecuencia_preguntas_auto': frecuencia_preguntas_auto(eProfesorMateria),
                                             'frecuencia_preguntas_dir': frecuencia_preguntas_dir(eProfesorMateria),
                                             'respuestas_hetero': respuestasevaluacionaccionmejoras(eMateria, eMateria.nivel.periodo, eProfesorMateria.profesor, 1),
                                             'respuestas_hetero_me': respuestasevaluacionformacioncontinua(eMateria, eMateria.nivel.periodo, eProfesorMateria.profesor, 1),
                                             'respuestas_auto_me': respuestasevaluacionformacioncontinua(eMateria, eMateria.nivel.periodo, eProfesorMateria.profesor, 2),
                                             'respuestas_dir_me': respuestasevaluacionformacioncontinua(eMateria, eMateria.nivel.periodo, eProfesorMateria.profesor, 4),
                                             'persona': persona,
                                             'hoy': hoy,
                                             'periodo': eMateria.nivel.periodo
                                             })
            except Exception as ex:
                return HttpResponseRedirect("/niveles?info=%s" % mensaje)

        elif action == 'addencuestasatisfaccion':
            try:
                f = EncuestaSatisfaccionDocenteForm(request.POST)
                if f.is_valid():
                    if not EncuestaSatisfaccionDocente.objects.filter(status=True, descripcion__iexact=f.cleaned_data['descripcion']).exists():
                        eEncuesta = EncuestaSatisfaccionDocente(descripcion=f.cleaned_data['descripcion'],
                                                                tipo=f.cleaned_data['tipo'],
                                                                leyenda=f.cleaned_data['leyenda'],
                                                                activo=f.cleaned_data['activo'],
                                                                obligatoria=f.cleaned_data['obligatoria'])
                        eEncuesta.save(request)

                        log(u'Adicionó encuesta de satisfacción de docente: %s' % eEncuesta, request, "add")
                        return JsonResponse({"result": False, 'mensaje': 'Adición Exitosa'})
                    else:
                        return JsonResponse({"result": True, 'mensaje': 'Ya existe una encuesta con ese nombre'})
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addpreguntasatisfaccion':
            try:
                eEncuesta = EncuestaSatisfaccionDocente.objects.get(status=True, pk=int(request.POST['id']))
                f = PreguntaEncuestaSatisfaccionDocenteForm(request.POST)
                if request.POST['pregunta']:
                    f.edit_pregunta(int(request.POST['pregunta']))
                if f.is_valid():
                    if not PreguntaEncuestaSatisfaccionDocente.objects.filter(status=True, encuesta=eEncuesta, descripcion__iexact=f.cleaned_data['descripcion']).exists():
                        ePregunta = PreguntaEncuestaSatisfaccionDocente(encuesta=eEncuesta,
                                                                        tipo=f.cleaned_data['tipo'],
                                                                        descripcion=f.cleaned_data['descripcion'],
                                                                        observacionporno=f.cleaned_data['observacionporno'],
                                                                        orden=f.cleaned_data['orden'],
                                                                        obligatoria=f.cleaned_data['obligatoria'])
                        ePregunta.save(request)

                        eOpciones = OpcionCuadriculaEncuestaSatisfaccionDocente.objects.filter(status=True, pregunta=f.cleaned_data['pregunta']).order_by('orden')

                        for eOpcion in eOpciones:
                            eOpcionCuadricula = OpcionCuadriculaEncuestaSatisfaccionDocente(pregunta=ePregunta,
                                                                                            descripcion=eOpcion.descripcion,
                                                                                            orden=eOpcion.orden,
                                                                                            valor=eOpcion.valor,
                                                                                            tipoopcion=eOpcion.tipoopcion)

                            eOpcionCuadricula.save(request)
                            log(u'Adicionó ocpión de encuesta de satisfacción de docente: %s' % eOpcionCuadricula, request, "add")

                        log(u'Adicionó pregunta de encuesta de satisfacción de docente: %s' % ePregunta, request, "add")
                        return JsonResponse({"result": False, 'mensaje': 'Adición Exitosa'})
                    else:
                        return JsonResponse({"result": True, 'mensaje': 'Ya existe una encuesta con ese nombre'})
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addcolumnafila':
            try:
                ePregunta = PreguntaEncuestaSatisfaccionDocente.objects.get(status=True, pk=int(request.POST['id']))
                f = OpcionCuadriculaSatisfaccionDocenteForm(request.POST)
                if f.is_valid():
                    if request.POST['men'] == 'colu':
                        eOpcionCuadricula = OpcionCuadriculaEncuestaSatisfaccionDocente(pregunta=ePregunta,
                                                                                        descripcion=f.cleaned_data['descripcion'],
                                                                                        orden=f.cleaned_data['orden'],
                                                                                        valor=f.cleaned_data['valor'],
                                                                                        tipoopcion=2)

                        eOpcionCuadricula.save(request)
                    else:
                        eOpcionCuadricula = OpcionCuadriculaEncuestaSatisfaccionDocente(pregunta=ePregunta,
                                                                                        descripcion=f.cleaned_data['descripcion'],
                                                                                        orden=f.cleaned_data['orden'],
                                                                                        valor=f.cleaned_data['valor'],
                                                                                        tipoopcion=1)

                        eOpcionCuadricula.save(request)
                    return JsonResponse({"result": False, 'mensaje': 'Adición Exitosa'})
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editcolumnafila':
            try:
                eOpcion = OpcionCuadriculaEncuestaSatisfaccionDocente.objects.get(status=True, pk=int(request.POST['id']))
                f = OpcionCuadriculaSatisfaccionDocenteForm(request.POST)
                if f.is_valid():
                    if request.POST['men'] == 'colu':
                        eOpcion.descripcion = f.cleaned_data['descripcion']
                        eOpcion.orden = f.cleaned_data['orden']
                        eOpcion.valor = f.cleaned_data['valor']
                        eOpcion.secuenciapregunta = f.cleaned_data['secuenciapregunta']
                        eOpcion.save(request)
                    else:
                        eOpcion.descripcion = f.cleaned_data['descripcion']
                        eOpcion.orden = f.cleaned_data['orden']
                        eOpcion.valor = f.cleaned_data['valor']
                        eOpcion.save(request)
                    return JsonResponse({"result": False, 'mensaje': 'Adición Exitosa'})
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editpreguntasatisfaccion':
            try:
                ePregunta = PreguntaEncuestaSatisfaccionDocente.objects.get(status=True, pk=int(request.POST['id']))
                f = PreguntaEncuestaSatisfaccionDocenteForm(request.POST)
                if 'pregunta' in request.POST:
                    f.edit_pregunta(int(request.POST['pregunta']))

                if f.is_valid():
                    orden = int(f.cleaned_data['orden'])
                    if orden == 0:
                        return JsonResponse({"result": True, 'mensaje': 'El orden no puede ser cero'})

                    if not PreguntaEncuestaSatisfaccionDocente.objects.filter(status=True, encuesta=ePregunta.encuesta, descripcion__iexact=f.cleaned_data['descripcion']).exclude(pk=ePregunta.id).exists():
                        if not PreguntaEncuestaSatisfaccionDocente.objects.filter(status=True, encuesta=ePregunta.encuesta, orden=orden).exclude(pk=ePregunta.id).exists():
                            ePregunta.tipo = f.cleaned_data['tipo']
                            ePregunta.descripcion = f.cleaned_data['descripcion']
                            ePregunta.orden = f.cleaned_data['orden']
                            ePregunta.obligatoria = f.cleaned_data['obligatoria']
                            ePregunta.save(request)
                            log(u'Editó pregunta de encuesta de satisfacción de docente: %s' % ePregunta, request, "edit")

                            if not OpcionCuadriculaEncuestaSatisfaccionDocente.objects.filter(status=True, pregunta=ePregunta).exists():
                                eOpciones = OpcionCuadriculaEncuestaSatisfaccionDocente.objects.filter(status=True,
                                                                                                       pregunta=f.cleaned_data['pregunta']).order_by('orden')
                                for eOpcion in eOpciones:
                                    eOpcionCuadricula = OpcionCuadriculaEncuestaSatisfaccionDocente(
                                        pregunta=ePregunta,
                                        descripcion=eOpcion.descripcion,
                                        orden=eOpcion.orden,
                                        valor=eOpcion.valor,
                                        tipoopcion=eOpcion.tipoopcion)

                                    eOpcionCuadricula.save(request)
                                    log(u'Editó ocpión de encuesta de satisfacción de docente: %s' % eOpcionCuadricula, request, "edit")

                            return JsonResponse({"result": False, 'mensaje': 'Adición Exitosa'})
                        else:
                            return JsonResponse({"result": True, 'mensaje': 'Ya existe una pregunta con número de orden'})
                    else:
                        return JsonResponse({"result": True, 'mensaje': 'Ya existe una pregunta con ese nombre'})
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editopcionsatisfaccion':
            try:
                eOpcion = OpcionCuadriculaEncuestaSatisfaccionDocente.objects.get(status=True, pk=int(request.POST['id']))
                f = OpcionCuadriculaSatisfaccionDocenteForm(request.POST)
                if f.is_valid():
                    orden = int(f.cleaned_data['orden'])
                    if orden == 0:
                        return JsonResponse({"result": True, 'mensaje': 'El orden no puede ser cero'})

                    if not OpcionCuadriculaEncuestaSatisfaccionDocente.objects.filter(status=True, pregunta=eOpcion.pregunta, descripcion__iexact=f.cleaned_data['descripcion']).exclude(pk=eOpcion.id).exists():
                        eOpcion.descripcion = f.cleaned_data['descripcion']
                        eOpcion.valor = f.cleaned_data['valor']
                        eOpcion.orden = f.cleaned_data['orden']
                        eOpcion.save(request)
                        log(u'Editó opción de pregunta de encuesta de satisfacción de docente: %s' % eOpcion, request, "edit")
                        return JsonResponse({"result": False, 'mensaje': 'Adición Exitosa'})
                    else:
                        return JsonResponse({"result": True, 'mensaje': 'Ya existe una pregunta con ese nombre'})
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editencuestasatisfaccion':
            try:
                eEncuesta = EncuestaSatisfaccionDocente.objects.get(status=True, pk=int(request.POST['id']))

                f = EncuestaSatisfaccionDocenteForm(request.POST)
                if f.is_valid():
                    if not EncuestaSatisfaccionDocente.objects.filter(status=True, descripcion__iexact=f.cleaned_data['descripcion']).exclude(pk=eEncuesta.id).exists():
                        eEncuesta.descripcion = f.cleaned_data['descripcion']
                        eEncuesta.leyenda = f.cleaned_data['leyenda']
                        eEncuesta.activo = f.cleaned_data['activo']
                        eEncuesta.obligatoria = f.cleaned_data['obligatoria']

                        eEncuesta.save(request)

                        log(u'Adicionó encuesta de satisfacción de docente: %s' % eEncuesta, request, "add")
                        return JsonResponse({"result": False, 'mensaje': 'Adición Exitosa'})
                    else:
                        return JsonResponse({"result": True, 'mensaje': 'Ya existe una encuesta con ese nombre'})
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteencuestasa':
            try:
                eEncuesta = EncuestaSatisfaccionDocente.objects.get(pk=int(request.POST['id']))

                if RespuestaCuadriculaEncuestaSatisfaccionDocente.objects.filter(status=True,
                                                                                 inscripcionencuesta__encuesta=eEncuesta).exists():
                    return JsonResponse({"result": 'bad', "mensaje": u"No puede eliminar esta encuesta debido a que ya ha sido respondida."})

                eEncuesta.status = False
                eEncuesta.save(request)
                log(u'Eliminó la encuesta de satisfacción: %s' % eEncuesta, request, "del")
                return JsonResponse({"result": 'ok', "mensaje": u"Encuesta eliminada correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": 'bad', "mensaje": f"Ocurrio un error al eliminar: {ex.__str__()}"})

        elif action == 'deletepregunta':
            try:
                ePregunta = PreguntaEncuestaSatisfaccionDocente.objects.get(pk=int(request.POST['id']))

                if RespuestaCuadriculaEncuestaSatisfaccionDocente.objects.filter(status=True, pregunta=ePregunta).exists():
                    return JsonResponse({"result": 'bad', "mensaje": u"No puede eliminar esta pregunta debido a que ya ha sido respondida."})

                ePregunta.status = False
                ePregunta.save(request)
                log(u'Eliminó la pregunta de la encuesta de satisfacción: %s' % ePregunta, request, "del")
                return JsonResponse({"result": 'ok', "mensaje": u"Pregunta eliminada correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": 'bad', "mensaje": f"Ocurrio un error al eliminar: {ex.__str__()}"})

        elif action == 'deleteopcion':
            try:
                eOpcion = OpcionCuadriculaEncuestaSatisfaccionDocente.objects.get(pk=int(request.POST['id']))

                if RespuestaCuadriculaEncuestaSatisfaccionDocente.objects.filter(status=True,
                                                                                 opcioncuadricula=eOpcion).exists():
                    return JsonResponse({"result": 'bad', "mensaje": u"No puede eliminar esta opción debido a que fue seleccionada como respuesta por un docente."})

                eOpcion.status = False
                eOpcion.save(request)
                log(u'Eliminó la opción de la preguntas de encuesta de satisfacción: %s' % eOpcion.pregunta, request, "del")
                return JsonResponse({"result": 'ok', "mensaje": u"Pregunta eliminada correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": 'bad', "mensaje": f"Ocurrio un error al eliminar: {ex.__str__()}"})

        elif action == 'consultadatos':
            try:
                eEncuesta = EncuestaSatisfaccionDocente.objects.get(pk=int(request.POST['id']))
                eMateria = Materia.objects.get(pk=int(request.POST['idm']))
                inicio = fin = ''
                if eEncuesta.tipo == 1:
                    if InscripcionEncuestaSatisfaccionDocente.objects.filter(status=True, profesormateria__materia=eMateria,
                                                                             encuesta=eEncuesta).exists():
                        eObjeto = InscripcionEncuestaSatisfaccionDocente.objects.filter(status=True, profesormateria__materia=eMateria,
                                                                             encuesta=eEncuesta).first()
                        inicio = eObjeto.inicio
                        fin = eObjeto.fin
                else:
                    if InscripcionEncuestaSatisfaccionDocente.objects.filter(status=True, materiaasignada__materia=eMateria,
                                                                             encuesta=eEncuesta).exists():
                        eObjeto = InscripcionEncuestaSatisfaccionDocente.objects.filter(status=True, materiaasignada__materia=eMateria,
                                                                             encuesta=eEncuesta).first()

                        inicio = eObjeto.inicio
                        fin = eObjeto.fin
                    return JsonResponse({"result": "ok", "inicio": inicio, "fin": fin})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"%s"%(ex)})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'editfechashetero':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = Materia.objects.get(status=True, pk=int(request.GET['id']))
                    data['action'] = request.GET['action']
                    form = EditarFechasEvaluacionForm(initial={'materia': filtro.__str__(),
                                                               'inicio': filtro.inicioeval,
                                                               'fin': filtro.fineval})
                    form.editar()
                    data['form2'] = form
                    template = get_template("adm_evaluacionposgrado/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'editfechasauto':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = Materia.objects.get(status=True, pk=int(request.GET['id']))
                    data['action'] = request.GET['action']
                    form = EditarFechasEvaluacionForm(initial={'materia': filtro.__str__(),
                                                               'inicio': filtro.inicioevalauto,
                                                               'fin': filtro.finevalauto})
                    form.editar()
                    data['form2'] = form
                    template = get_template("adm_evaluacionposgrado/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'editfechasdir':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = ProfesorMateria.objects.get(status=True, pk=int(request.GET['id']))
                    eDirector = eCoordinador = inicio = fin = None
                    eCarrera = filtro.materia.asignaturamalla.malla.carrera
                    if eCarrera.escuelaposgrado:
                        if eCarrera.escuelaposgrado.id == 1:
                            eDirector = Persona.objects.get(pk=Departamento.objects.get(pk=216).responsable.id)
                        elif eCarrera.escuelaposgrado.id == 2:
                            eDirector = Persona.objects.get(pk=Departamento.objects.get(pk=215).responsable.id)
                        elif eCarrera.escuelaposgrado.id == 3:
                            eDirector = Persona.objects.get(pk=Departamento.objects.get(pk=163).responsable.id)
                        else:
                            return JsonResponse({"result": False, 'message': 'No existe director de escuela para esta carrera'})
                    else:
                        return JsonResponse({"result": False, 'message': 'No existe director de escuela para esta carrera'})

                    if CohorteMaestria.objects.filter(status=True, maestriaadmision__carrera=eCarrera).exists():
                        eCoordinador = CohorteMaestria.objects.filter(status=True, maestriaadmision__carrera=eCarrera).order_by('-id').first().coordinador
                    else:
                        return JsonResponse({"result": False, 'message': 'No existe coordinador de escuela para esta carrera'})

                    if DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.filter(status=True,
                                                                                        coordinacion_id=7,
                                                                                        materia=filtro.materia,
                                                                                        evaluado=filtro.profesor,
                                                                                        inicio__isnull=False,
                                                                                        fin__isnull=False).exists():
                        eDeta = DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.filter(status=True,
                                                                                        coordinacion_id=7,
                                                                                        materia=filtro.materia,
                                                                                        evaluado=filtro.profesor,
                                                                                        inicio__isnull=False,
                                                                                        fin__isnull=False).first()
                        inicio = eDeta.inicio
                        fin = eDeta.fin

                    if not DetalleFechasEvalDirMateria.objects.filter(status=True, materia=filtro.materia).exists():
                        eDeta = DetalleFechasEvalDirMateria(materia=filtro.materia)
                        eDeta.save(request)
                    else:
                        eDeta = DetalleFechasEvalDirMateria.objects.filter(status=True, materia=filtro.materia).first()

                    data['action'] = request.GET['action']
                    form = EditarFechasEvaluacionForm(initial={'materia': filtro.materia.__str__(),
                                                               'director': eDirector.__str__(),
                                                               'coordinador':eCoordinador.__str__(),
                                                               'inicio': inicio,
                                                               'fin': fin})
                    form.editar_2()
                    data['form2'] = form
                    template = get_template("adm_evaluacionposgrado/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'addfechassatis':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = ProfesorMateria.objects.get(status=True, pk=int(request.GET['id']))
                    data['action'] = request.GET['action']
                    form = EditarFechasEvaluacionForm(initial={'materia': filtro.materia.__str__()})
                    form.fields['encuesta'].queryset = EncuestaSatisfaccionDocente.objects.filter(status=True, activo=True, tipo=1)
                    form.editar_3()
                    data['form2'] = form
                    template = get_template("adm_evaluacionposgrado/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'addfechassatis_est':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = ProfesorMateria.objects.get(status=True, pk=int(request.GET['id']))
                    data['action'] = request.GET['action']
                    form = EditarFechasEvaluacionForm(initial={'materia': filtro.materia.__str__()})
                    form.fields['encuesta'].queryset = EncuestaSatisfaccionDocente.objects.filter(status=True, activo=True, tipo=2)
                    form.editar_3()
                    data['form2'] = form
                    template = get_template("adm_evaluacionposgrado/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'editfechasevaluaciones':
                try:
                    data['id'] = request.GET['id']
                    data['action'] = request.GET['action']

                    filtro = Q(status=True, materia__nivel__periodo__tipo__id=3, tipoprofesor__id=11, materia__fin__lt=datetime.now().date())
                    filtro2 = None
                    data['desde'] = desde = request.GET.get('desde', '')
                    data['hasta'] = hasta = request.GET.get('hasta', '')
                    data['escuela'] = escuela = request.GET.get('escuela', '')
                    data['maestria'] = maestria = request.GET.get('maestria', '')
                    data['periodoa'] = peri = request.GET.get('periodoa', '')
                    data['paralelo'] = paralelo = request.GET.get('paralelo', '')
                    data['estado'] = estado = request.GET.get('estado', '')
                    data['modulo'] = modulo = request.GET.get('modulo', '')

                    if escuela:
                        filtro = filtro & Q(materia__asignaturamalla__malla__carrera__escuelaposgrado__id=int(escuela))

                    if maestria:
                        filtro = filtro & Q(materia__asignaturamalla__malla__carrera__id=int(maestria))

                    if peri:
                        filtro = filtro & Q(materia__nivel__periodo_id=int(peri))

                    if paralelo:
                        filtro = filtro & Q(materia__paralelo=paralelo)

                    if modulo:
                        if int(modulo) == 1:
                            filtro = filtro & Q(materia__cerrado=True)
                        elif int(modulo) == 2:
                            filtro = filtro & Q(materia__cerrado=True)

                    if desde and hasta:
                        filtro = filtro & Q(materia__fin__range=(desde, hasta))
                    elif desde:
                        filtro = filtro & Q(materia__fin__gte=desde)
                    elif hasta:
                        filtro = filtro & Q(materia__fin__lte=hasta)

                    if estado:
                        if int(estado) == 1:
                            filtro = filtro & Q(materia__inicioeval__isnull=True)
                        elif int(estado) == 2:
                            filtro = filtro & Q(materia__inicioevalauto__isnull=True)
                        elif int(estado) == 3:
                            query = ProfesorMateria.objects.filter(filtro).order_by('-id')
                            iddet = DetalleFechasEvalDirMateria.objects.filter(
                                materia__id__in=query.values_list('materia__id', flat=True)).values_list('materia__id',
                                                                                                         flat=True).distinct()
                            query = ProfesorMateria.objects.filter(filtro).order_by('-id').exclude(
                                materia__id__in=iddet)
                            filtro = filtro & Q(materia__id__in=query.values_list('materia__id', flat=True).distinct())
                        if int(estado) == 4:
                            filtro = filtro & Q(materia__inicioeval__isnull=False)
                        elif int(estado) == 5:
                            filtro = filtro & Q(materia__inicioevalauto__isnull=False)
                        elif int(estado) == 6:
                            query = ProfesorMateria.objects.filter(filtro).order_by('-id')
                            iddet = DetalleFechasEvalDirMateria.objects.filter(
                                materia__id__in=query.values_list('materia__id', flat=True)).distinct()
                            filtro = filtro & Q(materia__id__in=iddet)
                        elif int(estado) == 7:
                            query = ProfesorMateria.objects.filter(filtro).order_by('-id')
                            iddet = DetalleResultadosEvaluacionPosgrado.objects.filter(
                                materia__id__in=query.values_list('materia__id', flat=True)).values_list('materia__id',
                                                                                                         flat=True).distinct()
                            filtro = filtro & Q(materia__id__in=iddet)
                        elif int(estado) == 8:
                            query = ProfesorMateria.objects.filter(filtro).order_by('-id')
                            iddet = DetalleResultadosEvaluacionPosgrado.objects.filter(
                                materia__id__in=query.values_list('materia__id', flat=True)).values_list('materia__id',
                                                                                                         flat=True).distinct()
                            query = ProfesorMateria.objects.filter(filtro).order_by('-id').exclude(
                                materia__id__in=iddet)
                            filtro = filtro & Q(materia__id__in=query.values_list('materia__id', flat=True).distinct())
                        elif int(estado) == 9:
                            query = ProfesorMateria.objects.filter(filtro).order_by('-id')
                            iddet = InscripcionEncuestaSatisfaccionDocente.objects.filter(status=True, materiaasignada__materia__id__in=query.values_list('materia__id', flat=True), encuesta__tipo=2).values_list('materiaasignada__materia__id', flat=True).order_by('materiaasignada__materia__id').distinct()
                            filtro = filtro & Q(materia__id__in=iddet)
                        elif int(estado) == 10:
                            query = ProfesorMateria.objects.filter(filtro).order_by('-id')
                            iddet = InscripcionEncuestaSatisfaccionDocente.objects.filter(status=True, materiaasignada__materia__id__in=query.values_list('materia__id', flat=True), encuesta__tipo=2).values_list('materiaasignada__materia__id', flat=True).order_by('materiaasignada__materia__id').distinct()
                            query = ProfesorMateria.objects.filter(filtro).order_by('-id').exclude(materia__id__in=iddet)
                            filtro = filtro & Q(materia__id__in=query.values_list('materia__id', flat=True).distinct())
                        elif int(estado) == 11:
                            query = ProfesorMateria.objects.filter(filtro).order_by('-id')
                            ids = ids_eval_zero(query.values_list('id', flat=True))
                            filtro2 = Q(status=True, materia__nivel__periodo__tipo__id=3, tipoprofesor__id=11, materia__fin__lt=datetime.now().date(), materia__id__in=ids)
                        elif int(estado) == 12:
                            query = ProfesorMateria.objects.filter(filtro).order_by('-id')
                            ids = ids_eval_auto(query.values_list('id', flat=True))
                            filtro2 = Q(status=True, materia__nivel__periodo__tipo__id=3, tipoprofesor__id=11, materia__fin__lt=datetime.now().date(), materia__id__in=ids)
                        elif int(estado) == 13:
                            query = ProfesorMateria.objects.filter(filtro).order_by('-id')
                            ids = ids_eval_director(query.values_list('id', flat=True))
                            filtro2 = Q(status=True, materia__nivel__periodo__tipo__id=3, tipoprofesor__id=11, materia__fin__lt=datetime.now().date(), materia__id__in=ids)
                        elif int(estado) == 14:
                            query = ProfesorMateria.objects.filter(filtro).order_by('-id')
                            ids = ids_eval_coordinador(query.values_list('id', flat=True))
                            filtro2 = Q(status=True, materia__nivel__periodo__tipo__id=3, tipoprofesor__id=11, materia__fin__lt=datetime.now().date(), materia__id__in=ids)

                    if filtro2:
                        query = ProfesorMateria.objects.filter(filtro2).order_by('-id')
                    else:
                        query = ProfesorMateria.objects.filter(filtro).order_by('-id')

                    materias = ''

                    for qu in query:
                        materias += f'{qu.materia.asignatura.nombre.title()} - {qu.materia.paralelo}\n'

                    form = AsignarFechasMasivoForm(initial={'detalle': materias})
                    data['form2'] = form
                    template = get_template("adm_evaluacionposgrado/modal/formmodalmasivo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'procesarresultadosmasivo':
                try:
                    ids = None
                    materias = ''
                    if 'ids' in request.GET:
                        ids = request.GET['ids']
                    data['ids'] = ids
                    if not ids == '':
                        query = ProfesorMateria.objects.filter(status=True, tipoprofesor__id=11, materia__nivel__periodo__tipo__id=3,
                                                                       materia__fin__lt=datetime.now().date(),
                                                                       id__in=ids.split(','))

                        if query.count() > 10:
                            return JsonResponse({"result": False, "mensaje": 'No puede procesar resultados de más de 10 módulos. El máximo es 10'})

                        for qu in query:
                            materias += f'{qu.materia.asignatura.nombre.title()} - {qu.materia.paralelo}\n'

                        form = ProcesarResultadosMasivoForm(initial={'detalle': materias})
                        data['form2'] = form
                        data['action'] = "procesarresultadosmasivo"
                        template = get_template("adm_evaluacionposgrado/modal/formmodalmasivo.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    else:
                        return JsonResponse({"result": False, "mensaje": 'Por favor, seleccione al menos un módulo para procesar resultados'})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

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

            elif action == 'verresultadosevaluacion':
                try:
                    eModulo = ProfesorMateria.objects.get(status=True, pk=int(request.GET['id']))
                    eProfesor = eModulo.profesor
                    distributivo = eProfesor.distributivohoraseval(eModulo.materia.nivel.periodo)
                    if distributivo:
                        resumen = distributivo.resumen_evaluacion_acreditacion() if distributivo is not None else None
                    else:
                        resumen = None
                    data['eResumen'] = resumen
                    template = get_template("adm_evaluacionposgrado/modal/formmodalresultados.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'reporteseguimientoeval':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('seguimiento_eval_docente')
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 15)
                    ws.set_column(2, 5, 30)
                    ws.set_column(6, 6, 20)
                    ws.set_column(7, 7, 40)
                    ws.set_column(8, 9, 20)
                    ws.set_column(10, 40, 30)

                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    desde = request.GET.get('desde', '')
                    hasta = request.GET.get('hasta', '')
                    escuela = request.GET.get('escuela', '')
                    maestria = request.GET.get('maestria', '')
                    peri = request.GET.get('periodoa', '')
                    paralelo = request.GET.get('paralelo', '')
                    estado = request.GET.get('estado', '')

                    ws.merge_range('A1:AO1', 'SEGUMIENTO DE MÓDULOS DE EVALUACIÓN DOCENT DE POSGRADO', formatotitulo_filtros)

                    ws.write(1, 0, 'N°', formatoceldacab)
                    ws.write(1, 1, 'ID', formatoceldacab)
                    ws.write(1, 2, 'Escuela', formatoceldacab)
                    ws.write(1, 3, 'Maestría', formatoceldacab)
                    ws.write(1, 4, 'Cohorte', formatoceldacab)
                    ws.write(1, 5, 'Módulo', formatoceldacab)
                    ws.write(1, 6, 'Paralelo', formatoceldacab)
                    ws.write(1, 7, 'Docente', formatoceldacab)
                    ws.write(1, 8, 'Inicio', formatoceldacab)
                    ws.write(1, 9, 'Fin', formatoceldacab)
                    ws.write(1, 10, 'Inicio eval_hetero', formatoceldacab)
                    ws.write(1, 11, 'Fin eval_hetero', formatoceldacab)
                    ws.write(1, 12, 'Estado eval_hetero', formatoceldacab)
                    ws.write(1, 13, 'Total evaluados', formatoceldacab)
                    ws.write(1, 14, 'Total matriculados', formatoceldacab)

                    ws.write(1, 15, 'Inicio eval_auto', formatoceldacab)
                    ws.write(1, 16, 'Fin eval_auto', formatoceldacab)
                    ws.write(1, 17, 'Estado eval_auto', formatoceldacab)
                    ws.write(1, 18, '¿Realizó Autoevaluación?', formatoceldacab)

                    ws.write(1, 19, 'Inicio eval_dir', formatoceldacab)
                    ws.write(1, 20, 'Fin eval_dir', formatoceldacab)
                    ws.write(1, 21, 'Estado eval_dir', formatoceldacab)
                    ws.write(1, 22, '¿Evaluado por Director?', formatoceldacab)
                    ws.write(1, 23, '¿Evaluado por Coordinador?', formatoceldacab)

                    ws.write(1, 24, '¿Procesado?', formatoceldacab)
                    ws.write(1, 25, 'Fecha de procesado', formatoceldacab)
                    ws.write(1, 26, 'Hora de procesado', formatoceldacab)

                    ws.write(1, 27, 'eval_hetero', formatoceldacab)
                    ws.write(1, 28, 'eval_hetero (%)', formatoceldacab)
                    ws.write(1, 29, 'eval_auto', formatoceldacab)
                    ws.write(1, 30, 'eval_auto (%)', formatoceldacab)
                    ws.write(1, 31, 'eval_directivo', formatoceldacab)
                    ws.write(1, 32, 'eval_directivo (%)', formatoceldacab)
                    ws.write(1, 33, 'evalp_hetero', formatoceldacab)
                    ws.write(1, 34, 'evalp_hetero (%)', formatoceldacab)
                    ws.write(1, 35, 'evalp_auto', formatoceldacab)
                    ws.write(1, 36, 'evalp_auto (%)', formatoceldacab)
                    ws.write(1, 37, 'evalp_directivo', formatoceldacab)
                    ws.write(1, 38, 'evalp_directivo (%)', formatoceldacab)
                    ws.write(1, 39, 'total_eval_abs', formatoceldacab)
                    ws.write(1, 40, 'total_eval_rel', formatoceldacab)

                    filtro = Q(status=True, tipoprofesor__id=11, materia__nivel__periodo__tipo__id=3, materia__fin__lt=datetime.now().date())

                    if escuela:
                        filtro = filtro & Q(materia__asignaturamalla__malla__carrera__escuelaposgrado__id=int(escuela))

                    if maestria:
                        filtro = filtro & Q(materia__asignaturamalla__malla__carrera__id=int(maestria))

                    if peri:
                        filtro = filtro & Q(materia__nivel__periodo_id=int(peri))

                    if paralelo:
                        filtro = filtro & Q(materia__paralelo=paralelo)

                    if desde and hasta:
                        filtro = filtro & Q(materia__fin__range=(desde, hasta))
                    elif desde:
                        filtro = filtro & Q(materia__fin__gte=desde)
                    elif hasta:
                        filtro = filtro & Q(materia__fin__lte=hasta)

                    if estado:
                        if int(estado) == 1:
                            filtro = filtro & Q(materia__inicioeval__isnull=True)
                        elif int(estado) == 2:
                            filtro = filtro & Q(materia__inicioevalauto__isnull=True)
                        elif int(estado) == 3:
                            query = ProfesorMateria.objects.filter(filtro).order_by('-id')
                            iddet = DetalleFechasEvalDirMateria.objects.filter(
                                materia__id__in=query.values_list('materia__id', flat=True)).values_list('materia__id',
                                                                                                         flat=True).distinct()
                            query = ProfesorMateria.objects.filter(filtro).order_by('-id').exclude(
                                materia__id__in=iddet)
                            filtro = filtro & Q(materia__id__in=query.values_list('materia__id', flat=True).distinct())
                        if int(estado) == 4:
                            filtro = filtro & Q(materia__inicioeval__isnull=False)
                        elif int(estado) == 5:
                            filtro = filtro & Q(materia__inicioevalauto__isnull=False)
                        elif int(estado) == 6:
                            query = ProfesorMateria.objects.filter(filtro).order_by('-id')
                            iddet = DetalleFechasEvalDirMateria.objects.filter(
                                materia__id__in=query.values_list('materia__id', flat=True)).distinct()
                            filtro = filtro & Q(materia__id__in=iddet)
                        elif int(estado) == 7:
                            query = ProfesorMateria.objects.filter(filtro).order_by('-id')
                            iddet = DetalleResultadosEvaluacionPosgrado.objects.filter(
                                materia__id__in=query.values_list('materia__id', flat=True)).values_list('materia__id',
                                                                                                         flat=True).distinct()
                            filtro = filtro & Q(materia__id__in=iddet)
                        elif int(estado) == 8:
                            query = ProfesorMateria.objects.filter(filtro).order_by('-id')
                            iddet = DetalleResultadosEvaluacionPosgrado.objects.filter(
                                materia__id__in=query.values_list('materia__id', flat=True)).values_list('materia__id',
                                                                                                         flat=True).distinct()
                            query = ProfesorMateria.objects.filter(filtro).order_by('-id').exclude(
                                materia__id__in=iddet)
                            filtro = filtro & Q(materia__id__in=query.values_list('materia__id', flat=True).distinct())

                    eProfesorMaterias = ProfesorMateria.objects.filter(filtro).order_by('-id')

                    filas_recorridas = 3
                    cont = 1
                    for eProfesorMateria in eProfesorMaterias:
                        eMatriculados = eProfesorMateria.materia.materiaasignada_set.values("id").filter(status=True, matricula__estado_matricula__in=[2, 3], matricula__retiradomatricula=False).exclude(retiramateria=True).count()
                        eDir = object_dir(eProfesorMateria)
                        eRes = object_proces(eProfesorMateria)

                        distributivo = eProfesorMateria.profesor.distributivohoraseval(eProfesorMateria.materia.nivel.periodo)
                        if distributivo:
                            resumen = distributivo.resumen_evaluacion_acreditacion() if distributivo is not None else None
                        else:
                            resumen = None

                        ws.write('A%s' % filas_recorridas, str(cont), formatoceldaleft)
                        ws.write('B%s' % filas_recorridas, str(eProfesorMateria.id), formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, str(eProfesorMateria.materia.asignaturamalla.malla.carrera.escuelaposgrado.nombre if eProfesorMateria.materia.asignaturamalla.malla.carrera.escuelaposgrado else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('D%s' % filas_recorridas, str(eProfesorMateria.materia.asignaturamalla.malla.carrera), formatoceldaleft)
                        ws.write('E%s' % filas_recorridas, str(eProfesorMateria.materia.nivel.periodo.cohorte_maestria()), formatoceldaleft)
                        ws.write('F%s' % filas_recorridas, str(eProfesorMateria.materia.asignaturamalla.asignatura.nombre), formatoceldaleft)
                        ws.write('G%s' % filas_recorridas, str(eProfesorMateria.materia.paralelo), formatoceldaleft)
                        ws.write('H%s' % filas_recorridas, str(eProfesorMateria.profesor.persona), formatoceldaleft)
                        ws.write('I%s' % filas_recorridas, str(eProfesorMateria.materia.inicio), formatoceldaleft)
                        ws.write('J%s' % filas_recorridas, str(eProfesorMateria.materia.fin), formatoceldaleft)

                        ws.write('K%s' % filas_recorridas, str(eProfesorMateria.materia.inicioeval if eProfesorMateria.materia.inicioeval else 'NO CONFIGURADO'), formatoceldaleft)
                        ws.write('L%s' % filas_recorridas, str(eProfesorMateria.materia.fineval if eProfesorMateria.materia.fineval else 'NO CONFIGURADO'), formatoceldaleft)
                        ws.write('M%s' % filas_recorridas, str(fecha_vencida(eProfesorMateria.materia, 1)), formatoceldaleft)
                        ws.write('N%s' % filas_recorridas, cantidad_evaluacion_docente(eProfesorMateria), formatoceldaleft)
                        ws.write('O%s' % filas_recorridas, eMatriculados, formatoceldaleft)

                        ws.write('P%s' % filas_recorridas, str(eProfesorMateria.materia.inicioevalauto if eProfesorMateria.materia.inicioevalauto else 'NO CONFIGURADO'), formatoceldaleft)
                        ws.write('Q%s' % filas_recorridas, str(eProfesorMateria.materia.finevalauto if eProfesorMateria.materia.finevalauto else 'NO CONFIGURADO'), formatoceldaleft)
                        ws.write('R%s' % filas_recorridas, str(fecha_vencida(eProfesorMateria.materia, 2)), formatoceldaleft)
                        ws.write('S%s' % filas_recorridas, str('SI' if cantidad_evaluacion_auto(eProfesorMateria) > 0 else 'NO'), formatoceldaleft)

                        ws.write('T%s' % filas_recorridas, str(eDir.inicio if eDir else 'NO CONFIGURADO'), formatoceldaleft)
                        ws.write('U%s' % filas_recorridas, str(eDir.fin if eDir else 'NO CONFIGURADO'), formatoceldaleft)
                        ws.write('V%s' % filas_recorridas, str(fecha_vencida(eProfesorMateria.materia, 3)), formatoceldaleft)
                        ws.write('W%s' % filas_recorridas, str('SI' if evaluo_director(eProfesorMateria) else 'NO'), formatoceldaleft)
                        ws.write('X%s' % filas_recorridas, str('SI' if evaluo_coordinador(eProfesorMateria) else 'NO'), formatoceldaleft)

                        ws.write('Y%s' % filas_recorridas, str('SI' if eRes else 'NO PROCESADO'), formatoceldaleft)
                        ws.write('Z%s' % filas_recorridas, str(eRes.fecha_creacion.date().strftime('%d-%m-%Y') if eRes else 'NO PROCESADO'), formatoceldaleft)
                        ws.write('AA%s' % filas_recorridas, str(eRes.fecha_creacion.time().strftime('%I:%M %p') if eRes else 'NO PROCESADO'), formatoceldaleft)

                        ws.write('AB%s' % filas_recorridas, resumen.promedio_docencia_hetero if resumen else 0, formatoceldaleft)
                        ws.write('AC%s' % filas_recorridas, f'{cincoacien(resumen.promedio_docencia_hetero)} %' if resumen else 0, formatoceldaleft)
                        ws.write('AD%s' % filas_recorridas, resumen.promedio_docencia_auto if resumen else 0, formatoceldaleft)
                        ws.write('AE%s' % filas_recorridas, f'{cincoacien(resumen.promedio_docencia_auto)} %' if resumen else 0, formatoceldaleft)
                        ws.write('AF%s' % filas_recorridas, resumen.promedio_docencia_directivo if resumen else 0, formatoceldaleft)
                        ws.write('AG%s' % filas_recorridas, f'{cincoacien(resumen.promedio_docencia_directivo)} %' if resumen else 0, formatoceldaleft)
                        ws.write('AH%s' % filas_recorridas, resumen.valor_tabla_docencia_hetero if resumen else 0, formatoceldaleft)
                        ws.write('AI%s' % filas_recorridas, f'{cincoacien(resumen.valor_tabla_docencia_hetero)} %' if resumen else 0, formatoceldaleft)
                        ws.write('AJ%s' % filas_recorridas, resumen.valor_tabla_docencia_auto if resumen else 0, formatoceldaleft)
                        ws.write('AK%s' % filas_recorridas, f'{cincoacien(resumen.valor_tabla_docencia_auto)} %' if resumen else 0, formatoceldaleft)
                        ws.write('AL%s' % filas_recorridas, resumen.valor_tabla_docencia_directivo if resumen else 0, formatoceldaleft)
                        ws.write('AM%s' % filas_recorridas, f'{cincoacien(resumen.valor_tabla_docencia_directivo)} %' if resumen else 0, formatoceldaleft)
                        ws.write('AN%s' % filas_recorridas, resumen.resultado_docencia if resumen else 0, formatoceldaleft)
                        ws.write('AO%s' % filas_recorridas, f'{cincoacien(resumen.resultado_docencia)} %' if resumen else 0, formatoceldaleft)

                        filas_recorridas += 1
                        print(f'{cont}/{eProfesorMaterias.count()}')
                        cont += 1

                    workbook.close()
                    output.seek(0)
                    filename = f'Seguimiento_Evaluacion_docente_{datetime.now().date()}_{datetime.now().time()}.xlsx'
                    response = HttpResponse(output,

                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'reporteevaluadores':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('evaluadores')
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 15)
                    ws.set_column(2, 2, 35)
                    ws.set_column(3, 3, 15)
                    ws.set_column(4, 4, 40)
                    ws.set_column(5, 5, 40)
                    ws.set_column(6, 8, 15)

                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    ide = request.GET.get('ide', '')
                    idm = request.GET.get('idm', '')

                    eProfesorMateria = ProfesorMateria.objects.get(status=True, pk=int(idm))

                    idr = RespuestaEvaluacionAcreditacionPosgrado.objects.filter(
                        proceso=eProfesorMateria.materia.nivel.periodo.proceso_evaluativo(),
                        tipoinstrumento=1, profesor=eProfesorMateria.profesor,
                        materia=eProfesorMateria.materia).values_list('materiaasignada__id', flat=True).distinct()

                    ws.merge_range('A1:I1', f'EVALUADORES DEL MÓDULO {eProfesorMateria.materia.asignatura} - {eProfesorMateria.materia.paralelo} - {eProfesorMateria.profesor.persona}', formatotitulo_filtros)

                    ws.write(1, 0, 'N°', formatoceldacab)
                    ws.write(1, 1, 'Cédula', formatoceldacab)
                    ws.write(1, 2, 'Maestrante', formatoceldacab)
                    ws.write(1, 3, 'Teléfono', formatoceldacab)
                    ws.write(1, 4, 'Email', formatoceldacab)
                    ws.write(1, 5, 'Email institucional', formatoceldacab)
                    ws.write(1, 6, 'Fecha', formatoceldacab)
                    ws.write(1, 7, 'Hora', formatoceldacab)
                    ws.write(1, 8, 'Estado', formatoceldacab)

                    filtro = Q(status=True, matricula__estado_matricula__in=[2, 3], matricula__retiradomatricula=False, materia=eProfesorMateria.materia)

                    if ide:
                        if int(ide) == 1:
                            filtro = filtro & (Q(id__in=idr))
                        else:
                            idq = MateriaAsignada.objects.filter(filtro).values_list('id', flat=True).order_by('id').exclude(id__in=idr)
                            filtro = filtro & (Q(id__in=idq))

                    query = MateriaAsignada.objects.filter(filtro).order_by('-id')

                    filas_recorridas = 3
                    cont = 1
                    for eMaestrantre in query:
                        eRespuesta = obj_eval_hetero(eProfesorMateria, eMaestrantre, eMaestrantre.matricula.inscripcion.persona)
                        ws.write('A%s' % filas_recorridas, str(cont), formatoceldaleft)
                        ws.write('B%s' % filas_recorridas, str(eMaestrantre.matricula.inscripcion.persona.cedula), formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, str(eMaestrantre.matricula.inscripcion.persona.__str__()), formatoceldaleft)
                        ws.write('D%s' % filas_recorridas, str(eMaestrantre.matricula.inscripcion.persona.telefono), formatoceldaleft)
                        ws.write('E%s' % filas_recorridas, str(eMaestrantre.matricula.inscripcion.persona.email), formatoceldaleft)
                        ws.write('F%s' % filas_recorridas, str(eMaestrantre.matricula.inscripcion.persona.emailinst), formatoceldaleft)
                        ws.write('G%s' % filas_recorridas, str(eRespuesta.fecha_creacion.date() if eRespuesta else 'SIN EVALUAR'), formatoceldaleft)
                        ws.write('H%s' % filas_recorridas, str(eRespuesta.fecha_creacion.time().strftime('%I:%M %p') if eRespuesta else 'SIN EVALUAR'), formatoceldaleft)
                        ws.write('I%s' % filas_recorridas, str('EVALUADO' if eRespuesta else 'SIN EVALUAR'), formatoceldaleft)

                        filas_recorridas += 1
                        print(f'{cont}/{query.count()}')
                        cont += 1

                    workbook.close()
                    output.seek(0)
                    filename = f'Evaluadores{datetime.now().date()}_{datetime.now().time()}.xlsx'
                    response = HttpResponse(output,

                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'reporteevaluadores_satis':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('evaluadores_satis')
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 15)
                    ws.set_column(2, 2, 35)
                    ws.set_column(3, 3, 15)
                    ws.set_column(4, 4, 40)
                    ws.set_column(5, 5, 40)
                    ws.set_column(6, 8, 15)

                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    ide = request.GET.get('ide', '')
                    iden = request.GET.get('iden', '')
                    idm = request.GET.get('idm', '')

                    eProfesorMateria = ProfesorMateria.objects.get(status=True, pk=int(idm))

                    ws.merge_range('A1:I1', f'EVALUADORES DEL MÓDULO {eProfesorMateria.materia.asignatura} - {eProfesorMateria.materia.paralelo} - {eProfesorMateria.profesor.persona}', formatotitulo_filtros)

                    ws.write(1, 0, 'N°', formatoceldacab)
                    ws.write(1, 1, 'Cédula', formatoceldacab)
                    ws.write(1, 2, 'Maestrante', formatoceldacab)
                    ws.write(1, 3, 'Teléfono', formatoceldacab)
                    ws.write(1, 4, 'Email', formatoceldacab)
                    ws.write(1, 5, 'Email institucional', formatoceldacab)
                    ws.write(1, 6, 'Fecha', formatoceldacab)
                    ws.write(1, 7, 'Hora', formatoceldacab)
                    ws.write(1, 8, 'Estado', formatoceldacab)

                    filtro = Q(status=True, materiaasignada__materia=eProfesorMateria.materia)

                    if ide:
                        if int(ide) == 1:
                            filtro = filtro & (Q(respondio=True))
                        else:
                            filtro = filtro & (Q(respondio=False))

                    if iden:
                        filtro = filtro & (Q(encuesta__id=int(iden)))

                    query = InscripcionEncuestaSatisfaccionDocente.objects.filter(filtro).order_by('-id')

                    filas_recorridas = 3
                    cont = 1
                    for eMaestrantre in query:
                        ws.write('A%s' % filas_recorridas, str(cont), formatoceldaleft)
                        ws.write('B%s' % filas_recorridas, str(eMaestrantre.materiaasignada.matricula.inscripcion.persona.cedula), formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, str(eMaestrantre.materiaasignada.matricula.inscripcion.persona.__str__()), formatoceldaleft)
                        ws.write('D%s' % filas_recorridas, str(eMaestrantre.materiaasignada.matricula.inscripcion.persona.telefono), formatoceldaleft)
                        ws.write('E%s' % filas_recorridas, str(eMaestrantre.materiaasignada.matricula.inscripcion.persona.email), formatoceldaleft)
                        ws.write('F%s' % filas_recorridas, str(eMaestrantre.materiaasignada.matricula.inscripcion.persona.emailinst), formatoceldaleft)
                        ws.write('G%s' % filas_recorridas, str(eMaestrantre.fecha_eval().date() if eMaestrantre.respondio else 'SIN EVALUAR'), formatoceldaleft)
                        ws.write('H%s' % filas_recorridas, str(eMaestrantre.fecha_eval().time().strftime('%I:%M %p') if eMaestrantre.respondio else 'SIN EVALUAR'), formatoceldaleft)
                        ws.write('I%s' % filas_recorridas, str('EVALUADO' if eMaestrantre.respondio else 'SIN EVALUAR'), formatoceldaleft)

                        filas_recorridas += 1
                        print(f'{cont}/{query.count()}')
                        cont += 1

                    workbook.close()
                    output.seek(0)
                    filename = f'Evaluadores{datetime.now().date()}_{datetime.now().time()}.xlsx'
                    response = HttpResponse(output,

                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'reporte_por_profesores':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('profesores')
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 15)
                    ws.set_column(2, 5, 30)
                    ws.set_column(6, 6, 20)
                    ws.set_column(7, 7, 40)
                    ws.set_column(8, 9, 20)
                    ws.set_column(10, 40, 30)

                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})

                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    formatoceldaleft_red = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'fg_color': '#FF0000', 'font_color': 'black'})

                    formatoceldaleft_yelow = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'fg_color': '#FFFF00', 'font_color': 'black'})

                    formatoceldaleft_green = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'fg_color': '#92D050', 'font_color': 'black'})

                    desde = request.GET.get('desde', '')
                    hasta = request.GET.get('hasta', '')
                    escuela = request.GET.get('escuela', '')
                    maestria = request.GET.get('maestria', '')
                    peri = request.GET.get('periodoa', '')
                    paralelo = request.GET.get('paralelo', '')
                    estado = request.GET.get('estado', '')

                    ws.merge_range('A1:Q1', 'UNIVERSIDAD ESTATAL DE MILAGRO', formatotitulo_filtros)
                    ws.merge_range('A2:Q2', 'VICERRECTORADO DE INVESTIGACIÓN Y POSGRADOS', formatotitulo_filtros)
                    ws.merge_range('A3:Q3', 'REPORTE MENSUAL DE DESEMPEÑO ACADEMICO -MES-', formatotitulo_filtros)
                    ws.merge_range('A4:Q4', 'Evaluación de Desempeño', formatotitulo_filtros)
                    ws.merge_range('A5:Q5', 'Facultad de POSGRADOS', formatotitulo_filtros)
                    ws.merge_range('A6:Q6', 'Ponderaciones Especificas por Profesor', formatotitulo_filtros)

                    ws.write(6, 0, 'Número', formatoceldacab)
                    ws.write(6, 1, 'Cédula', formatoceldacab)
                    ws.write(6, 2, 'Profesor', formatoceldacab)
                    ws.write(6, 3, 'Periodo', formatoceldacab)
                    ws.write(6, 4, 'Módulo', formatoceldacab)
                    ws.write(6, 5, 'Paralelo', formatoceldacab)
                    ws.write(6, 6, 'Hetero Ev', formatoceldacab)
                    ws.write(6, 7, 'Auto EV', formatoceldacab)
                    ws.write(6, 8, 'Coord Ev', formatoceldacab)
                    ws.write(6, 9, 'Direct Ev.', formatoceldacab)
                    ws.write(6, 10, 'Decano Ev', formatoceldacab)
                    ws.write(6, 11, 'Hetero Ev', formatoceldacab)  # Puedes cambiar este y los siguientes si son duplicados o necesitas otros nombres.
                    ws.write(6, 12, 'Auto EV', formatoceldacab)
                    ws.write(6, 13, 'Coord Ev', formatoceldacab)
                    ws.write(6, 14, 'Direct Ev.', formatoceldacab)
                    ws.write(6, 15, 'Decano Ev', formatoceldacab)
                    ws.write(6, 16, 'Total', formatoceldacab)

                    filtro = Q(status=True, tipoprofesor__id=11, materia__nivel__periodo__tipo__id=3, materia__fin__lt=datetime.now().date())

                    if escuela:
                        filtro = filtro & Q(materia__asignaturamalla__malla__carrera__escuelaposgrado__id=int(escuela))

                    if maestria:
                        filtro = filtro & Q(materia__asignaturamalla__malla__carrera__id=int(maestria))

                    if peri:
                        filtro = filtro & Q(materia__nivel__periodo_id=int(peri))

                    if paralelo:
                        filtro = filtro & Q(materia__paralelo=paralelo)

                    if desde and hasta:
                        filtro = filtro & Q(materia__fin__range=(desde, hasta))
                    elif desde:
                        filtro = filtro & Q(materia__fin__gte=desde)
                    elif hasta:
                        filtro = filtro & Q(materia__fin__lte=hasta)

                    if estado:
                        if int(estado) == 1:
                            filtro = filtro & Q(materia__inicioeval__isnull=True)
                        elif int(estado) == 2:
                            filtro = filtro & Q(materia__inicioevalauto__isnull=True)
                        elif int(estado) == 3:
                            query = ProfesorMateria.objects.filter(filtro).order_by('-id')
                            iddet = DetalleFechasEvalDirMateria.objects.filter(
                                materia__id__in=query.values_list('materia__id', flat=True)).values_list('materia__id',
                                                                                                         flat=True).distinct()
                            query = ProfesorMateria.objects.filter(filtro).order_by('-id').exclude(
                                materia__id__in=iddet)
                            filtro = filtro & Q(materia__id__in=query.values_list('materia__id', flat=True).distinct())
                        if int(estado) == 4:
                            filtro = filtro & Q(materia__inicioeval__isnull=False)
                        elif int(estado) == 5:
                            filtro = filtro & Q(materia__inicioevalauto__isnull=False)
                        elif int(estado) == 6:
                            query = ProfesorMateria.objects.filter(filtro).order_by('-id')
                            iddet = DetalleFechasEvalDirMateria.objects.filter(
                                materia__id__in=query.values_list('materia__id', flat=True)).distinct()
                            filtro = filtro & Q(materia__id__in=iddet)
                        elif int(estado) == 7:
                            query = ProfesorMateria.objects.filter(filtro).order_by('-id')
                            iddet = DetalleResultadosEvaluacionPosgrado.objects.filter(
                                materia__id__in=query.values_list('materia__id', flat=True)).values_list('materia__id',
                                                                                                         flat=True).distinct()
                            filtro = filtro & Q(materia__id__in=iddet)
                        elif int(estado) == 8:
                            query = ProfesorMateria.objects.filter(filtro).order_by('-id')
                            iddet = DetalleResultadosEvaluacionPosgrado.objects.filter(
                                materia__id__in=query.values_list('materia__id', flat=True)).values_list('materia__id',
                                                                                                         flat=True).distinct()
                            query = ProfesorMateria.objects.filter(filtro).order_by('-id').exclude(
                                materia__id__in=iddet)
                            filtro = filtro & Q(materia__id__in=query.values_list('materia__id', flat=True).distinct())

                    eProfesorMaterias = ProfesorMateria.objects.filter(filtro).order_by('-id')
                    filas_recorridas = 8
                    cont = 1
                    for eProfesorMateria in eProfesorMaterias:
                        distributivo = eProfesorMateria.profesor.distributivohoraseval(eProfesorMateria.materia.nivel.periodo)
                        if distributivo:
                            resumen = distributivo.resumen_evaluacion_acreditacion() if distributivo is not None else None
                        else:
                            resumen = None
                        ws.write('A%s' % filas_recorridas, str(cont), formatoceldaleft)
                        ws.write('B%s' % filas_recorridas, str(eProfesorMateria.profesor.persona.identificacion()), formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, str(eProfesorMateria.profesor.persona.__str__()), formatoceldaleft)
                        ws.write('D%s' % filas_recorridas, str(eProfesorMateria.materia.nivel.periodo), formatoceldaleft)
                        ws.write('E%s' % filas_recorridas, str(eProfesorMateria.materia.asignaturamalla.asignatura.nombre), formatoceldaleft)
                        ws.write('F%s' % filas_recorridas, str(eProfesorMateria.materia.paralelo), formatoceldaleft)
                        ws.write('G%s' % filas_recorridas, str('VERDADERO' if cantidad_evaluacion_docente(eProfesorMateria) > 0 else 'FALSO'), formatoceldaleft)
                        ws.write('H%s' % filas_recorridas, str('VERDADERO' if cantidad_evaluacion_auto(eProfesorMateria) > 0 else 'FALSO'), formatoceldaleft)
                        ws.write('I%s' % filas_recorridas, str('VERDADERO' if evaluo_coordinador(eProfesorMateria) else 'FALSO'), formatoceldaleft)
                        ws.write('J%s' % filas_recorridas, str('VERDADERO' if evaluo_director(eProfesorMateria) else 'FALSO'), formatoceldaleft)
                        ws.write('K%s' % filas_recorridas, str('FALSO'), formatoceldaleft)

                        ws.write('L%s' % filas_recorridas, f'{cincoacien(resumen.promedio_docencia_hetero)} %' if resumen else 0, formatoceldaleft)
                        ws.write('M%s' % filas_recorridas, f'{cincoacien(resumen.promedio_docencia_auto)} %' if resumen else 0, formatoceldaleft)
                        ws.write('N%s' % filas_recorridas, f'{cincoacien(resumen.promedio_docencia_directivo)} %' if resumen else 0, formatoceldaleft)
                        ws.write('O%s' % filas_recorridas, f'{cincoacien(resumen.promedio_docencia_directivo)} %' if resumen else 0, formatoceldaleft)
                        ws.write('P%s' % filas_recorridas, str('NO APLICA'), formatoceldaleft)
                        ws.write('Q%s' % filas_recorridas, f'{cincoacien(resumen.resultado_docencia)} %' if resumen else 0, formatoceldaleft)

                        filas_recorridas += 1
                        print(f'{cont}/{eProfesorMaterias.count()}')
                        cont += 1

                    workbook.close()
                    output.seek(0)
                    filename = f'Profesores_{datetime.now().date()}_{datetime.now().time()}.xlsx'
                    response = HttpResponse(output,

                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'cargar_cohortes_ofer':
                try:
                    lista = []
                    ePeriodos = Periodo.objects.filter(status=True, tipo_id=3).exclude(nombre__icontains='TITUL').order_by('-id')

                    for ePeriodo in ePeriodos:
                        if not buscar_dicc(lista, 'id', ePeriodo.id):
                            lista.append({'id': ePeriodo.id, 'nombre': ePeriodo.__str__()})
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'reportedemodulosposgrado':
                try:
                    notifi = Notificacion(cuerpo='Generación de reporte de excel en progreso',
                                          titulo='Reporte de Módulos Posgrado', destinatario=persona,
                                          url='',
                                          prioridad=1, app_label='SGA',
                                          fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2,
                                          en_proceso=True)
                    notifi.save(request)
                    reporte_modulos_posgrado(request=request, notiid=notifi.id).start()
                    return JsonResponse({"result": True,
                                         "mensaje": u"El reporte de Módulos Posgrado se está realizando. Verifique su apartado de notificaciones después de unos minutos.",
                                         "btn_notificaciones": traerNotificaciones(request, data, persona)})
                except Exception as ex:
                    pass

            elif action == 'reportedeperiodosposgrado':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('periodos')
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 15)
                    ws.set_column(2, 2, 40)
                    ws.set_column(3, 3, 20)
                    ws.set_column(4, 4, 20)
                    ws.set_column(5, 5, 20)
                    ws.set_column(6, 6, 20)
                    ws.set_column(7, 7, 20)
                    ws.set_column(8, 8, 20)
                    ws.set_column(9, 9, 20)
                    ws.set_column(10, 10, 20)
                    ws.set_column(11, 11, 20)
                    ws.set_column(12, 12, 20)
                    ws.set_column(13, 13, 20)
                    ws.set_column(14, 14, 20)

                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    formatoceldaleft2 = workbook.add_format(
                        {'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    formatoceldaleft3 = workbook.add_format(
                        {'text_wrap': True, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    decimalformat = workbook.add_format({'num_format': '#,##0.00 %', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    decimalformat2 = workbook.add_format({'num_format': '#,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    cohorte = 0
                    desde = hasta = ''

                    if 'cohorte' in request.GET:
                        cohorte = request.GET['cohorte']

                    ws.merge_range('A1:O1', 'Peridos de posgrado', formatotitulo_filtros)

                    ws.write(2, 0, 'N°', formatoceldacab)
                    ws.write(2, 1, 'Id', formatoceldacab)
                    ws.write(2, 2, 'Periodo', formatoceldacab)
                    ws.write(2, 3, 'Fecha de inicio', formatoceldacab)
                    ws.write(2, 4, 'Fecha de fin', formatoceldacab)
                    ws.write(2, 5, 'Inicio (hetero general)', formatoceldacab)
                    ws.write(2, 6, 'Fin (hetero general)', formatoceldacab)
                    ws.write(2, 7, 'Rúbricas (hetero)', formatoceldacab)
                    ws.write(2, 8, 'Inicio (auto general)', formatoceldacab)
                    ws.write(2, 9, 'Fin (auto general)', formatoceldacab)
                    ws.write(2, 10, 'Rúbricas (auto)', formatoceldacab)
                    ws.write(2, 11, 'Inicio (directivos general)', formatoceldacab)
                    ws.write(2, 12, 'Fin (directivos general)', formatoceldacab)
                    ws.write(2, 13, '¿Activa?', formatoceldacab)
                    ws.write(2, 14, 'Rúbricas (directivos)', formatoceldacab)

                    filtro = Q(tipo__id=3, status=True)
                    if cohorte != "":
                        lista_cadenas = ast.literal_eval(request.GET['cohorte'])
                        lista_enteros = list(map(int, lista_cadenas))

                        if len(lista_enteros) > 0 and 0 not in lista_enteros:
                            filtro = filtro & Q(id__in=lista_enteros)

                    ePeriodos = Periodo.objects.filter(filtro).exclude(nombre__icontains='TITUL').order_by('-id')

                    filas_recorridas = 4
                    cont = 1
                    for ePeriodo in ePeriodos:
                        eProceso = ePeriodo.proceso_evaluativoacreditacion()
                        eRubricasHetero = Rubrica.objects.filter(status=True, habilitado=True, proceso=eProceso,
                                                                 para_hetero=True).count()
                        eRubricasAuto = Rubrica.objects.filter(status=True, habilitado=True, proceso=eProceso,
                                                               para_auto=True).count()
                        eRubricasDirectivos = Rubrica.objects.filter(status=True, habilitado=True, proceso=eProceso,
                                                                     para_directivo=True).count()

                        ws.write('A%s' % filas_recorridas, str(cont), formatoceldaleft)
                        ws.write('B%s' % filas_recorridas, str(ePeriodo.id), formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, str(ePeriodo.nombre), formatoceldaleft)
                        ws.write('D%s' % filas_recorridas, str(ePeriodo.inicio), formatoceldaleft)
                        ws.write('E%s' % filas_recorridas, str(ePeriodo.fin), formatoceldaleft)
                        ws.write('F%s' % filas_recorridas, str(eProceso.instrumentoheteroinicio), formatoceldaleft)
                        ws.write('G%s' % filas_recorridas, str(eProceso.instrumentoheterofin), formatoceldaleft)
                        ws.write('H%s' % filas_recorridas, str(eRubricasHetero), formatoceldaleft)
                        ws.write('I%s' % filas_recorridas, str(eProceso.instrumentoautoinicio), formatoceldaleft)
                        ws.write('J%s' % filas_recorridas, str(eProceso.instrumentoautofin), formatoceldaleft)
                        ws.write('K%s' % filas_recorridas, str(eRubricasAuto), formatoceldaleft)
                        ws.write('L%s' % filas_recorridas, str(eProceso.instrumentodirectivoinicio), formatoceldaleft)
                        ws.write('M%s' % filas_recorridas, str(eProceso.instrumentodirectivofin), formatoceldaleft)
                        ws.write('N%s' % filas_recorridas, str('SI' if eProceso.instrumentodirectivoactivo else 'NO'), formatoceldaleft)
                        ws.write('O%s' % filas_recorridas, str(eRubricasDirectivos), formatoceldaleft)

                        filas_recorridas += 1
                        print(f'{cont}/{ePeriodos.count()}')
                        cont += 1

                    workbook.close()
                    output.seek(0)
                    fecha_hora_actual = datetime.now().date()
                    filename = 'PeriodosPosgrado_' + str(fecha_hora_actual) + '.xlsx'
                    response = HttpResponse(output,

                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'reportededocentesposgrado':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('docentes')
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 15)
                    ws.set_column(2, 2, 30)
                    ws.set_column(3, 3, 30)
                    ws.set_column(4, 4, 30)
                    ws.set_column(5, 5, 15)
                    ws.set_column(6, 6, 40)
                    ws.set_column(7, 7, 30)
                    ws.set_column(8, 8, 35)
                    ws.set_column(9, 9, 15)
                    ws.set_column(10, 10, 15)
                    ws.set_column(11, 11, 15)
                    ws.set_column(12, 13, 15)

                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    cohorte = 0
                    desde = hasta = ''

                    if 'cohorte' in request.GET:
                        cohorte = request.GET['cohorte']

                    if 'desde' in request.GET:
                        desde = request.GET['desde']
                    if 'hasta' in request.GET:
                        hasta = request.GET['hasta']

                    ws.merge_range('A1:N1', 'Docentes autor 2 de posgrado', formatotitulo_filtros)

                    ws.write(2, 0, 'N°', formatoceldacab)
                    ws.write(2, 1, 'Cédula', formatoceldacab)
                    ws.write(2, 2, 'Apellidos y nombres', formatoceldacab)
                    ws.write(2, 3, 'Correo Unemi', formatoceldacab)
                    ws.write(2, 4, 'Correo Personal', formatoceldacab)
                    ws.write(2, 5, 'Teléfono', formatoceldacab)
                    ws.write(2, 6, 'Periodo', formatoceldacab)
                    ws.write(2, 7, 'Maestría', formatoceldacab)
                    ws.write(2, 8, 'Módulo', formatoceldacab)
                    ws.write(2, 9, 'Paralelo', formatoceldacab)
                    ws.write(2, 10, 'Inicio', formatoceldacab)
                    ws.write(2, 11, 'Fin', formatoceldacab)
                    ws.write(2, 12, 'Estado', formatoceldacab)
                    ws.write(2, 13, 'Realizó autoevaluación', formatoceldacab)

                    filtro = Q(status=True, tipoprofesor__id=11, materia__nivel__periodo__tipo__id=3)

                    if cohorte != "":
                        lista_cadenas = ast.literal_eval(request.GET['cohorte'])
                        lista_enteros = list(map(int, lista_cadenas))

                        if len(lista_enteros) > 0 and 0 not in lista_enteros:
                            filtro = filtro & Q(materia__nivel__periodo__id__in=lista_enteros)

                    if desde and hasta:
                        filtro = filtro & Q(materia__fin__range=(desde, hasta))
                    elif desde:
                        filtro = filtro & Q(materia__fin__gte=desde)
                    elif hasta:
                        filtro = filtro & Q(materia__fin__lte=hasta)

                    eProfesorMaterias = ProfesorMateria.objects.filter(filtro).order_by('-id')

                    filas_recorridas = 4
                    cont = 1
                    for eProfesorMateria in eProfesorMaterias:
                        eEvaluadoresAuto = cantidad_evaluacion_auto(eProfesorMateria)
                        eEvaluadoresAuto = eEvaluadoresAuto if eEvaluadoresAuto is not None else 0

                        ws.write('A%s' % filas_recorridas, str(cont), formatoceldaleft)
                        ws.write('B%s' % filas_recorridas, str(eProfesorMateria.profesor.persona.identificacion()), formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, str(eProfesorMateria.profesor.persona), formatoceldaleft)
                        ws.write('D%s' % filas_recorridas, str(eProfesorMateria.profesor.persona.emailinst), formatoceldaleft)
                        ws.write('E%s' % filas_recorridas, str(eProfesorMateria.profesor.persona.email), formatoceldaleft)
                        ws.write('F%s' % filas_recorridas, str(eProfesorMateria.profesor.persona.telefono), formatoceldaleft)
                        ws.write('G%s' % filas_recorridas, str(eProfesorMateria.materia.nivel.periodo), formatoceldaleft)
                        ws.write('H%s' % filas_recorridas, str(eProfesorMateria.materia.asignaturamalla.malla.carrera), formatoceldaleft)
                        ws.write('I%s' % filas_recorridas, str(eProfesorMateria.materia.asignaturamalla.asignatura.nombre), formatoceldaleft)
                        ws.write('J%s' % filas_recorridas, str(eProfesorMateria.materia.paralelo), formatoceldaleft)
                        ws.write('K%s' % filas_recorridas, str(eProfesorMateria.materia.inicio), formatoceldaleft)
                        ws.write('L%s' % filas_recorridas, str(eProfesorMateria.materia.fin), formatoceldaleft)
                        ws.write('M%s' % filas_recorridas, str('CERRADO' if eProfesorMateria.materia.cerrado else 'ABIERTO'), formatoceldaleft)
                        ws.write('N%s' % filas_recorridas, str('SI' if eEvaluadoresAuto > 0 else 'NO'), formatoceldaleft)

                        filas_recorridas += 1
                        print(f'{cont}/{eProfesorMaterias.count()}')
                        cont += 1

                    workbook.close()
                    output.seek(0)
                    fecha_hora_actual = datetime.now().date()
                    filename = 'DocentesPosgrado_' + str(fecha_hora_actual) + '.xlsx'
                    response = HttpResponse(output,

                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'addencuestasatisfaccion':
                try:
                    data['title'] = u'Adicionar encuesta de satisfacción'
                    data['action'] = request.GET['action']
                    form = EncuestaSatisfaccionDocenteForm()
                    data['form2'] = form
                    template = get_template("adm_evaluacionposgrado/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'addcolumnafila':
                try:
                    data['title'] = u'Adicionar encuesta de satisfacción'
                    ePregunta = PreguntaEncuestaSatisfaccionDocente.objects.get(status=True, pk=int(request.GET['id']))
                    data['id'] = ePregunta.id
                    data['men'] = request.GET['men']
                    form = OpcionCuadriculaSatisfaccionDocenteForm()
                    if request.GET['men'] == 'colu':
                        form.no_mostrar_col()
                        # form.fields['secuenciapregunta'].queryset = PreguntaEncuestaSatisfaccionDocente.objects.filter(status=True, encuesta=ePregunta.encuesta).exclude(pk=ePregunta.id).order_by('id')
                    else:
                        form.no_mostrar_fil()
                    data['action'] = 'addcolumnafila'
                    data['form2'] = form
                    template = get_template("adm_evaluacionposgrado/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'editcolumnafila':
                try:
                    data['title'] = u'Adicionar encuesta de satisfacción'
                    eOpcion = OpcionCuadriculaEncuestaSatisfaccionDocente.objects.get(status=True, pk=int(request.GET['id']))
                    data['id'] = eOpcion.id
                    data['men'] = request.GET['men']
                    form = OpcionCuadriculaSatisfaccionDocenteForm(initial={'descripcion':eOpcion.descripcion,
                                                                            'valor':eOpcion.valor,
                                                                            'orden': eOpcion.orden})
                    if request.GET['men'] == 'colu':
                        form.no_mostrar_col()
                        form.fields['secuenciapregunta'].queryset = PreguntaEncuestaSatisfaccionDocente.objects.filter(status=True, encuesta=eOpcion.pregunta.encuesta).exclude(pk=eOpcion.pregunta.id).order_by('id')
                    else:
                        form.no_mostrar_fil()
                    data['action'] = 'editcolumnafila'
                    data['form2'] = form
                    template = get_template("adm_evaluacionposgrado/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'ver_encuestas_satisfaccion':
                try:
                    data['title'] = u'Encuestas de satisfacción Posgrado'

                    filtros = Q(status=True)
                    s = request.GET.get('s', '')
                    ide = request.GET.get('ide', '0')
                    idt = request.GET.get('idt', '0')
                    url_vars = ''

                    if s:
                        filtros = filtros & (Q(descripcion__icontains=s) | Q(leyenda__icontains=s))
                        data['s'] = f"{s}"
                        url_vars += f"&s={s}"

                    if int(ide):
                        if int(ide) == 1:
                            filtros = filtros & (Q(activo=True))
                        else:
                            filtros = filtros & (Q(activo=False))
                        data['ide'] = f"{ide}"
                        url_vars += f"&ide={ide}"

                    if int(idt):
                        filtros = filtros & (Q(tipo=int(idt)))
                        data['idt'] = f"{idt}"
                        url_vars += f"&idt={idt}"

                    eEncuestas = EncuestaSatisfaccionDocente.objects.filter(filtros)
                    paging = MiPaginador(eEncuestas, 25)
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
                    data['eEncuestas'] = page.object_list
                    data['url_vars'] = url_vars
                    data['count'] = eEncuestas.count()
                    return render(request,"adm_evaluacionposgrado/encuestassatisfaccion.html", data)
                except Exception as ex:
                    pass

            elif action == 'ver_preguntas_satisfaccion':
                try:
                    data['title'] = u'Preguntas de encuestas de satisfacción Posgrado'

                    eEncuesta = EncuestaSatisfaccionDocente.objects.get(status=True, pk=int(request.GET['id']))

                    filtros = Q(status=True, encuesta=eEncuesta)
                    s = request.GET.get('s', '')
                    idt = request.GET.get('idt', '0')
                    url_vars = ''

                    if s:
                        filtros = filtros & (Q(descripcion__icontains=s) | Q(leyenda__icontains=s))
                        data['s'] = f"{s}"
                        url_vars += f"&s={s}"

                    if int(idt):
                        if int(idt) == 1:
                            filtros = filtros & (Q(activo=True))
                            data['idt'] = f"{idt}"
                            url_vars += f"&idt={idt}"
                        elif int(idt) == 2:
                            filtros = filtros & (Q(activo=False))
                            data['idt'] = f"{idt}"
                            url_vars += f"&idt={idt}"

                    ePreguntas = PreguntaEncuestaSatisfaccionDocente.objects.filter(filtros).order_by('orden')
                    paging = MiPaginador(ePreguntas, 25)
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
                    data['ePreguntas'] = page.object_list
                    data['url_vars'] = url_vars
                    data['count'] = ePreguntas.count()
                    data['eEncuesta'] = eEncuesta
                    return render(request,"adm_evaluacionposgrado/preguntassatisfaccion.html", data)
                except Exception as ex:
                    pass

            elif action == 'ver_opciones_satisfaccion':
                try:
                    data['title'] = u'Opciones de cuadricula'

                    ePregunta = PreguntaEncuestaSatisfaccionDocente.objects.get(status=True, pk=int(request.GET['id']))

                    eOpciones = OpcionCuadriculaEncuestaSatisfaccionDocente.objects.filter(status=True, pregunta=ePregunta).order_by('orden')
                    data['eOpciones'] = eOpciones
                    data['ePregunta'] = ePregunta
                    return render(request,"adm_evaluacionposgrado/cuadriculaopciones.html", data)
                except Exception as ex:
                    pass

            elif action == 'verevaluadores':
                try:
                    data['title'] = u'Listado de evaluaciones ejecutadas'
                    data['eProfesorMateria'] = eProfesorMateria = ProfesorMateria.objects.get(status=True, pk=int(request.GET['idm']))
                    idr = RespuestaEvaluacionAcreditacionPosgrado.objects.filter(
                        proceso=eProfesorMateria.materia.nivel.periodo.proceso_evaluativo(),
                        tipoinstrumento=1, profesor=eProfesorMateria.profesor,
                        materia=eProfesorMateria.materia).values_list('materiaasignada__id', flat=True).distinct()

                    filtro = Q(status=True, matricula__estado_matricula__in=[2, 3], matricula__retiradomatricula=False, materia=eProfesorMateria.materia)

                    url_vars = f'&action=verevaluadores&idm=' + request.GET['idm']
                    search = request.GET.get('s', None)
                    ide = request.GET.get('ide', '')

                    if ide:
                        if int(ide) == 1:
                            filtro = filtro & (Q(id__in=idr))
                        else:
                            idq = MateriaAsignada.objects.filter(filtro).values_list('id', flat=True).order_by('id').exclude(id__in=idr)
                            filtro = filtro & (Q(id__in=idq))
                        data['ide'] = int(ide)
                        url_vars += f"&ide={ide}"

                    if search:
                        data['search'] = search
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro = filtro & (Q(matricula__inscripcion__persona__apellido1__icontains=search) |
                                                     Q(matricula__inscripcion__persona__apellido2__icontains=search) |
                                                     Q(matricula__inscripcion__persona__nombres__icontains=search) |
                                                     Q(matricula__inscripcion__persona__cedula__icontains=search))
                            url_vars += "&s={}".format(search)
                        elif len(ss) == 2:
                            filtro = filtro & (Q(matricula__inscripcion__persona__apellido1__icontains=ss[0]) &
                                                     Q(matricula__inscripcion__persona__apellido2__icontains=ss[1]))
                            url_vars += "&s={}".format(ss)
                        else:
                            filtro = filtro & (Q(matricula__inscripcion__persona__apellido1__icontains=ss[0]) &
                                                Q(matricula__inscripcion__persona__apellido2__icontains=ss[1]) &
                                               Q(matricula__inscripcion__persona__nombres__icontains=ss[2]))
                            url_vars += "&s={}".format(ss)

                    query = MateriaAsignada.objects.filter(filtro).order_by('-id')
                    paging = MiPaginador(query, 25)
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
                    data["eEvaluadores"] = page.object_list
                    data["eCount"] = query.count()
                    data["eEvaluados"] = idr.count()
                    return render(request, "adm_evaluacionposgrado/view_evaluadores.html", data)
                except Exception as ex:
                    pass

            elif action == 'verevaluadoressatisfaccion':
                try:
                    data['title'] = u'Listado de evaluaciones ejecutadas'
                    data['eProfesorMateria'] = eProfesorMateria = ProfesorMateria.objects.get(status=True, pk=int(request.GET['idm']))

                    filtro = Q(status=True, materiaasignada__materia=eProfesorMateria.materia)

                    url_vars = f'&action=verevaluadoressatisfaccion&idm=' + request.GET['idm']
                    search = request.GET.get('s', None)
                    ide = request.GET.get('ide', '')
                    iden = request.GET.get('iden', '')

                    if ide:
                        if int(ide) == 1:
                            filtro = filtro & (Q(respondio=True))
                        else:
                            filtro = filtro & (Q(respondio=False))
                        data['ide'] = int(ide)
                        url_vars += f"&ide={ide}"

                    if iden:
                        filtro = filtro & (Q(encuesta__id=int(iden)))
                        data['iden'] = int(iden)
                        url_vars += f"&iden={iden}"

                    if search:
                        data['search'] = search
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro = filtro & (Q(materiaasignada__matricula__inscripcion__persona__apellido1__icontains=search) |
                                                     Q(materiaasignada__matricula__inscripcion__persona__apellido2__icontains=search) |
                                                     Q(materiaasignada__matricula__inscripcion__persona__nombres__icontains=search) |
                                                     Q(materiaasignada__matricula__inscripcion__persona__cedula__icontains=search))
                            url_vars += "&s={}".format(search)
                        elif len(ss) == 2:
                            filtro = filtro & (Q(materiaasignada__matricula__inscripcion__persona__apellido1__icontains=ss[0]) &
                                                     Q(materiaasignada__matricula__inscripcion__persona__apellido2__icontains=ss[1]))
                            url_vars += "&s={}".format(ss)
                        else:
                            filtro = filtro & (Q(materiaasignada__matricula__inscripcion__persona__apellido1__icontains=ss[0]) &
                                                Q(materiaasignada__matricula__inscripcion__persona__apellido2__icontains=ss[1]) &
                                               Q(materiaasignada__matricula__inscripcion__persona__nombres__icontains=ss[2]))
                            url_vars += "&s={}".format(ss)

                    query = InscripcionEncuestaSatisfaccionDocente.objects.filter(filtro).order_by('-id')
                    paging = MiPaginador(query, 25)
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
                    data["eEvaluadores"] = page.object_list
                    data["eCount"] = query.count()
                    data["eEvaluados"] = query.filter(respondio=True).count()
                    data["eNoEvaluados"] = query.filter(respondio=False).count()
                    data["eEncuestas"] = EncuestaSatisfaccionDocente.objects.filter(status=True, id__in=query.values_list('encuesta__id', flat=True).order_by('encuesta__id').distinct())
                    return render(request, "adm_evaluacionposgrado/viewevaluadores_satis.html", data)
                except Exception as ex:
                    pass

            elif action == 'addpreguntasatisfaccion':
                try:
                    data['title'] = u'Adicionar pregunta'
                    data['action'] = request.GET['action']
                    eEncuesta = EncuestaSatisfaccionDocente.objects.get(status=True, pk=int(request.GET['ide']))
                    form = PreguntaEncuestaSatisfaccionDocenteForm()
                    form.no_mostrar()

                    idp = OpcionCuadriculaEncuestaSatisfaccionDocente.objects.filter(status=True,
                                                                                     pregunta__encuesta=eEncuesta).values_list('pregunta__id', flat=True)

                    form.fields['pregunta'].queryset = PreguntaEncuestaSatisfaccionDocente.objects.filter(status=True, id__in=idp)
                    data['form2'] = form
                    data['id'] = eEncuesta.id
                    template = get_template("adm_evaluacionposgrado/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'editencuestasatisfaccion':
                try:
                    eEncuesta = EncuestaSatisfaccionDocente.objects.get(status=True, pk=int(request.GET['id']))
                    data['id'] = eEncuesta.id
                    data['title'] = u'Adicionar formato de certificado'
                    data['action'] = request.GET['action']
                    form = EncuestaSatisfaccionDocenteForm(initial={'descripcion': eEncuesta.descripcion,
                                                                    'leyenda': eEncuesta.leyenda,
                                                                    'activo': eEncuesta.activo,
                                                                    'obligatoria': eEncuesta.obligatoria})
                    data['form2'] = form
                    template = get_template("adm_evaluacionposgrado/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'editpreguntasatisfaccion':
                try:
                    ePregunta = PreguntaEncuestaSatisfaccionDocente.objects.get(status=True, pk=int(request.GET['id']))
                    data['id'] = ePregunta.id
                    data['title'] = u'Editar preguntas de encuestas de satisfacción'
                    data['action'] = request.GET['action']
                    form = PreguntaEncuestaSatisfaccionDocenteForm(initial={'tipo': ePregunta.tipo,
                                                                            'descripcion': ePregunta.descripcion,
                                                                            'orden': ePregunta.orden,
                                                                            'obligatoria': ePregunta.obligatoria})
                    form.no_mostrar()

                    idp = OpcionCuadriculaEncuestaSatisfaccionDocente.objects.filter(status=True, pregunta__encuesta=ePregunta.encuesta).values_list('pregunta__id', flat=True)

                    form.fields['pregunta'].queryset = PreguntaEncuestaSatisfaccionDocente.objects.filter(status=True, id__in=idp)
                    data['form2'] = form
                    template = get_template("adm_evaluacionposgrado/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'editopcionsatisfaccion':
                try:
                    eOpcion = OpcionCuadriculaEncuestaSatisfaccionDocente.objects.get(status=True, pk=int(request.GET['id']))
                    data['id'] = eOpcion.id
                    data['title'] = u'Editar opción de preguntas de encuestas de satisfacción'
                    data['action'] = request.GET['action']
                    form = OpcionCuadriculaSatisfaccionDocenteForm(initial={'descripcion': eOpcion.descripcion,
                                                                            'valor': eOpcion.valor,
                                                                            'orden': eOpcion.orden})
                    form.no_mostrar_col()
                    data['form2'] = form
                    template = get_template("adm_evaluacionposgrado/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'resultadossatisfaccion':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('datos')
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 15)
                    ws.set_column(2, 2, 35)
                    ws.set_column(3, 3, 40)
                    ws.set_column(4, 4, 35)
                    ws.set_column(5, 5, 15)
                    ws.set_column(6, 6, 15)
                    ws.set_column(7, 7, 40)
                    ws.set_column(8, 8, 15)
                    ws.set_column(9, 9, 15)
                    ws.set_column(10, 25, 40)


                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    formatoceldaleft2 = workbook.add_format(
                        {'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    formatoceldaleft3 = workbook.add_format(
                        {'text_wrap': True, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    decimalformat = workbook.add_format({'num_format': '#,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    decimalformat2 = workbook.add_format({'num_format': '#,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    eEncuesta = EncuestaSatisfaccionDocente.objects.get(pk=int(request.GET['id']))
                    eInscritos = InscripcionEncuestaSatisfaccionDocente.objects.filter(status=True, encuesta=eEncuesta)

                    ws.merge_range('A1:O1', f'Encuestados - {eEncuesta.descripcion}', formatotitulo_filtros)

                    ws.write(2, 0, 'N°', formatoceldacab)
                    ws.write(2, 1, 'Id', formatoceldacab)
                    ws.write(2, 2, 'Carrera', formatoceldacab)
                    ws.write(2, 3, 'Periodo', formatoceldacab)
                    ws.write(2, 4, 'Materia', formatoceldacab)
                    ws.write(2, 5, 'Paralelo', formatoceldacab)
                    ws.write(2, 6, 'Cédula', formatoceldacab)
                    ws.write(2, 7, 'Encuestado', formatoceldacab)
                    ws.write(2, 8, 'Inicio', formatoceldacab)
                    ws.write(2, 9, 'Fin', formatoceldacab)

                    c = 10
                    for ePregunta in eEncuesta.preguntas():
                        ws.write(2, c, f'{ePregunta.descripcion}', formatoceldacab)
                        c += 1

                    filas_recorridas = 4
                    cont = 1
                    for eInscrito in eInscritos:
                        ws.write('A%s' % filas_recorridas, str(cont), formatoceldaleft)
                        ws.write('B%s' % filas_recorridas, str(eInscrito.id), formatoceldaleft)
                        if eInscrito.encuesta.tipo == 1:
                            ws.write('C%s' % filas_recorridas, str(eInscrito.profesormateria.materia.asignaturamalla.malla.carrera), formatoceldaleft)
                            ws.write('D%s' % filas_recorridas, str(eInscrito.profesormateria.materia.nivel.periodo), formatoceldaleft)
                            ws.write('E%s' % filas_recorridas, str(eInscrito.profesormateria.materia.asignaturamalla.asignatura.nombre), formatoceldaleft)
                            ws.write('F%s' % filas_recorridas, str(eInscrito.profesormateria.materia.paralelo), formatoceldaleft)
                            ws.write('G%s' % filas_recorridas, str(eInscrito.profesormateria.profesor.persona.cedula), formatoceldaleft)
                            ws.write('H%s' % filas_recorridas, str(eInscrito.profesormateria.profesor.persona), formatoceldaleft)
                        else:
                            ws.write('C%s' % filas_recorridas, str(eInscrito.materiaasignada.materia.asignaturamalla.malla.carrera), formatoceldaleft)
                            ws.write('D%s' % filas_recorridas, str(eInscrito.materiaasignada.materia.nivel.periodo), formatoceldaleft)
                            ws.write('E%s' % filas_recorridas, str(eInscrito.materiaasignada.materia.asignaturamalla.asignatura.nombre), formatoceldaleft)
                            ws.write('F%s' % filas_recorridas, str(eInscrito.materiaasignada.materia.paralelo), formatoceldaleft)
                            ws.write('G%s' % filas_recorridas, str(eInscrito.materiaasignada.matricula.inscripcion.persona.cedula), formatoceldaleft)
                            ws.write('H%s' % filas_recorridas, str(eInscrito.materiaasignada.matricula.inscripcion.persona), formatoceldaleft)
                        ws.write('I%s' % filas_recorridas, str(eInscrito.inicio), formatoceldaleft)
                        ws.write('J%s' % filas_recorridas, str(eInscrito.fin), formatoceldaleft)

                        i = 11
                        for ePregunta in eEncuesta.preguntas():
                            eRespuesta = ePregunta.respuesta_inscrito(eInscrito)
                            if eRespuesta:
                                ws.write(f'{number_to_excel_col(i)}%s' % filas_recorridas, eRespuesta.opcioncuadricula.valor, decimalformat)
                            else:
                                ws.write(f'{number_to_excel_col(i)}%s' % filas_recorridas, 'No ha respondido', formatoceldaleft)
                            i += 1

                        filas_recorridas += 1
                        print(f'{cont}/{eInscritos.count()}')
                        cont += 1

                    workbook.close()
                    output.seek(0)
                    fecha_hora_actual = datetime.now().date()
                    filename = 'ResultadoEncuestaSatisfaccion_' + str(fecha_hora_actual) + '.xlsx'
                    response = HttpResponse(output,

                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'resultadossatisfaccion_mate':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)

                    ide = InscripcionEncuestaSatisfaccionDocente.objects.filter(status=True, materiaasignada__materia__id=int(request.GET['id'])).values_list('encuesta__id', flat=True).distinct()
                    eEncuestas = EncuestaSatisfaccionDocente.objects.filter(id__in=ide)

                    for eEncuesta in eEncuestas:
                        ws = workbook.add_worksheet(f'datos_{eEncuesta.id}')
                        ws.set_column(0, 0, 10)
                        ws.set_column(1, 1, 15)
                        ws.set_column(2, 2, 35)
                        ws.set_column(3, 3, 40)
                        ws.set_column(4, 4, 35)
                        ws.set_column(5, 5, 15)
                        ws.set_column(6, 6, 15)
                        ws.set_column(7, 7, 40)
                        ws.set_column(8, 8, 15)
                        ws.set_column(9, 9, 15)
                        ws.set_column(10, 25, 40)


                        formatotitulo_filtros = workbook.add_format(
                            {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14})

                        formatoceldacab = workbook.add_format(
                            {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})
                        formatoceldaleft = workbook.add_format(
                            {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                        formatoceldaleft2 = workbook.add_format(
                            {'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                        formatoceldaleft3 = workbook.add_format(
                            {'text_wrap': True, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                        decimalformat = workbook.add_format({'num_format': '#,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                        decimalformat2 = workbook.add_format({'num_format': '#,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                        ws.merge_range('A1:J1', f'Encuestados - {eEncuesta.descripcion}', formatotitulo_filtros)

                        ws.write(1, 0, 'N°', formatoceldacab)
                        ws.write(1, 1, 'Id', formatoceldacab)
                        ws.write(1, 2, 'Carrera', formatoceldacab)
                        ws.write(1, 3, 'Periodo', formatoceldacab)
                        ws.write(1, 4, 'Materia', formatoceldacab)
                        ws.write(1, 5, 'Paralelo', formatoceldacab)
                        ws.write(1, 6, 'Cédula', formatoceldacab)
                        ws.write(1, 7, 'Encuestado', formatoceldacab)
                        ws.write(1, 8, 'Inicio', formatoceldacab)
                        ws.write(1, 9, 'Fin', formatoceldacab)

                        c = 10
                        for ePregunta in eEncuesta.preguntas():
                            ws.write(1, c, f'{ePregunta.descripcion}', formatoceldacab)
                            c += 1

                        eInscritos = InscripcionEncuestaSatisfaccionDocente.objects.filter(status=True, encuesta=eEncuesta,
                                                                                           materiaasignada__materia__id=int(request.GET['id']))

                        filas_recorridas = 3
                        cont = 1
                        for eInscrito in eInscritos:
                            ws.write('A%s' % filas_recorridas, str(cont), formatoceldaleft)
                            ws.write('B%s' % filas_recorridas, str(eInscrito.id), formatoceldaleft)
                            if eInscrito.encuesta.tipo == 1:
                                ws.write('C%s' % filas_recorridas, str(eInscrito.profesormateria.materia.asignaturamalla.malla.carrera), formatoceldaleft)
                                ws.write('D%s' % filas_recorridas, str(eInscrito.profesormateria.materia.nivel.periodo), formatoceldaleft)
                                ws.write('E%s' % filas_recorridas, str(eInscrito.profesormateria.materia.asignaturamalla.asignatura.nombre), formatoceldaleft)
                                ws.write('F%s' % filas_recorridas, str(eInscrito.profesormateria.materia.paralelo), formatoceldaleft)
                                ws.write('G%s' % filas_recorridas, str(eInscrito.profesormateria.profesor.persona.cedula), formatoceldaleft)
                                ws.write('H%s' % filas_recorridas, str(eInscrito.profesormateria.profesor.persona), formatoceldaleft)
                            else:
                                ws.write('C%s' % filas_recorridas, str(eInscrito.materiaasignada.materia.asignaturamalla.malla.carrera), formatoceldaleft)
                                ws.write('D%s' % filas_recorridas, str(eInscrito.materiaasignada.materia.nivel.periodo), formatoceldaleft)
                                ws.write('E%s' % filas_recorridas, str(eInscrito.materiaasignada.materia.asignaturamalla.asignatura.nombre), formatoceldaleft)
                                ws.write('F%s' % filas_recorridas, str(eInscrito.materiaasignada.materia.paralelo), formatoceldaleft)
                                ws.write('G%s' % filas_recorridas, str(eInscrito.materiaasignada.matricula.inscripcion.persona.cedula), formatoceldaleft)
                                ws.write('H%s' % filas_recorridas, str(eInscrito.materiaasignada.matricula.inscripcion.persona), formatoceldaleft)
                            ws.write('I%s' % filas_recorridas, str(eInscrito.inicio), formatoceldaleft)
                            ws.write('J%s' % filas_recorridas, str(eInscrito.fin), formatoceldaleft)

                            i = 11
                            for ePregunta in eEncuesta.preguntas():
                                eRespuesta = ePregunta.respuesta_inscrito(eInscrito)
                                if eRespuesta:
                                    ws.write(f'{number_to_excel_col(i)}%s' % filas_recorridas, eRespuesta.opcioncuadricula.valor, decimalformat)
                                else:
                                    ws.write(f'{number_to_excel_col(i)}%s' % filas_recorridas, 'No ha respondido', formatoceldaleft)
                                i += 1

                            filas_recorridas += 1
                            print(f'{cont}/{eInscritos.count()}')
                            cont += 1

                    workbook.close()
                    output.seek(0)
                    fecha_hora_actual = datetime.now().date()
                    filename = 'ResultadoEncuestaSatisfaccion_' + str(fecha_hora_actual) + '.xlsx'
                    response = HttpResponse(output,

                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Evaluación docente de Posgrado'
                url_vars = ''
                filtro2 = None
                search = request.GET.get('s', None)
                search2 = request.GET.get('s2', None)
                desde = request.GET.get('desde', '')
                hasta = request.GET.get('hasta', '')
                escuela = request.GET.get('escuela', '')
                maestria = request.GET.get('maestria', '')
                peri = request.GET.get('periodoa', '')
                paralelo = request.GET.get('paralelo', '')
                estado = request.GET.get('estado', '')
                modulo = request.GET.get('modulo', '')

                filtro = Q(status=True, materia__nivel__periodo__tipo__id=3, tipoprofesor__id=11, materia__fin__lt=datetime.now().date())

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
                        filtro = filtro & (Q(profesor__persona__apellido1__icontains=search2) |
                                                 Q(profesor__persona__apellido2__icontains=search2) |
                                                 Q(profesor__persona__nombres__icontains=search2) |
                                                 Q(profesor__persona__cedula__icontains=search2))
                        url_vars += "&s2={}".format(search2)
                    elif len(ss) == 2:
                        filtro = filtro & (Q(profesor__persona__apellido1__icontains=ss[0]) &
                                                 Q(profesor__persona__apellido2__icontains=ss[1]))
                        url_vars += "&s2={}".format(ss)
                    else:
                        filtro = filtro & (Q(profesor__persona__apellido1__icontains=ss[0]) &
                                            Q(profesor__persona__apellido2__icontains=ss[1]) &
                                           Q(profesor__persona__nombres__icontains=ss[2]))
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

                if modulo:
                    data['modulo'] = int(modulo)
                    if int(modulo) == 1:
                        filtro = filtro & Q(materia__cerrado=True)
                    elif int(modulo) == 2:
                        filtro = filtro & Q(materia__cerrado=True)
                    url_vars += "&modulo={}".format(peri)

                if desde and hasta:
                    data['desde'] = desde
                    data['hasta'] = hasta
                    filtro = filtro & Q(materia__fin__range=(desde, hasta))
                    url_vars += "&desde={}".format(desde)
                    url_vars += "&hasta={}".format(hasta)

                elif desde:
                    data['desde'] = desde
                    filtro = filtro & Q(materia__fin__gte=desde)
                    url_vars += "&desde={}".format(hasta)

                elif hasta:
                    data['hasta'] = hasta
                    filtro = filtro & Q(materia__fin__lte=hasta)
                    url_vars += "&hasta={}".format(hasta)

                if estado:
                    data['estado'] = int(estado)
                    if int(estado) == 1:
                        filtro = filtro & Q(materia__inicioeval__isnull=True)
                    elif int(estado) == 2:
                        filtro = filtro & Q(materia__inicioevalauto__isnull=True)
                    elif int(estado) == 3:
                        query = ProfesorMateria.objects.filter(filtro).order_by('-id')
                        iddet = DetalleFechasEvalDirMateria.objects.filter(materia__id__in=query.values_list('materia__id', flat=True)).values_list('materia__id', flat=True).distinct()
                        query = ProfesorMateria.objects.filter(filtro).order_by('-id').exclude(materia__id__in=iddet)
                        filtro = filtro & Q(materia__id__in=query.values_list('materia__id', flat=True).distinct())
                    if int(estado) == 4:
                        filtro = filtro & Q(materia__inicioeval__isnull=False)
                    elif int(estado) == 5:
                        filtro = filtro & Q(materia__inicioevalauto__isnull=False)
                    elif int(estado) == 6:
                        query = ProfesorMateria.objects.filter(filtro).order_by('-id')
                        iddet = DetalleFechasEvalDirMateria.objects.filter(materia__id__in=query.values_list('materia__id', flat=True)).distinct()
                        filtro = filtro & Q(materia__id__in=iddet)
                    elif int(estado) == 7:
                        query = ProfesorMateria.objects.filter(filtro).order_by('-id')
                        iddet = DetalleResultadosEvaluacionPosgrado.objects.filter(materia__id__in=query.values_list('materia__id', flat=True)).values_list('materia__id', flat=True).distinct()
                        filtro = filtro & Q(materia__id__in=iddet)
                    elif int(estado) == 8:
                        query = ProfesorMateria.objects.filter(filtro).order_by('-id')
                        iddet = DetalleResultadosEvaluacionPosgrado.objects.filter(materia__id__in=query.values_list('materia__id', flat=True)).values_list('materia__id', flat=True).distinct()
                        query = ProfesorMateria.objects.filter(filtro).order_by('-id').exclude(materia__id__in=iddet)
                        filtro = filtro & Q(materia__id__in=query.values_list('materia__id', flat=True).distinct())
                    elif int(estado) == 9:
                        query = ProfesorMateria.objects.filter(filtro).order_by('-id')
                        iddet = InscripcionEncuestaSatisfaccionDocente.objects.filter(status=True, materiaasignada__materia__id__in=query.values_list('materia__id', flat=True), encuesta__tipo=2).values_list('materiaasignada__materia__id', flat=True).order_by('materiaasignada__materia__id').distinct()
                        filtro = filtro & Q(materia__id__in=iddet)
                    elif int(estado) == 10:
                        query = ProfesorMateria.objects.filter(filtro).order_by('-id')
                        iddet = InscripcionEncuestaSatisfaccionDocente.objects.filter(status=True, materiaasignada__materia__id__in=query.values_list('materia__id', flat=True), encuesta__tipo=2).values_list('materiaasignada__materia__id', flat=True).order_by('materiaasignada__materia__id').distinct()
                        query = ProfesorMateria.objects.filter(filtro).order_by('-id').exclude(materia__id__in=iddet)
                        filtro = filtro & Q(materia__id__in=query.values_list('materia__id', flat=True).distinct())
                    elif int(estado) == 11:
                        query = ProfesorMateria.objects.filter(filtro).order_by('-id')
                        ids = ids_eval_zero(query.values_list('id', flat=True))
                        filtro2 = Q(status=True, materia__nivel__periodo__tipo__id=3, tipoprofesor__id=11, materia__fin__lt=datetime.now().date(), materia__id__in=ids)
                    elif int(estado) == 12:
                        query = ProfesorMateria.objects.filter(filtro).order_by('-id')
                        ids = ids_eval_auto(query.values_list('id', flat=True))
                        filtro2 = Q(status=True, materia__nivel__periodo__tipo__id=3, tipoprofesor__id=11, materia__fin__lt=datetime.now().date(), materia__id__in=ids)
                    elif int(estado) == 13:
                        query = ProfesorMateria.objects.filter(filtro).order_by('-id')
                        ids = ids_eval_director(query.values_list('id', flat=True))
                        filtro2 = Q(status=True, materia__nivel__periodo__tipo__id=3, tipoprofesor__id=11, materia__fin__lt=datetime.now().date(), materia__id__in=ids)
                    elif int(estado) == 14:
                        query = ProfesorMateria.objects.filter(filtro).order_by('-id')
                        ids = ids_eval_coordinador(query.values_list('id', flat=True))
                        filtro2 = Q(status=True, materia__nivel__periodo__tipo__id=3, tipoprofesor__id=11, materia__fin__lt=datetime.now().date(), materia__id__in=ids)

                    url_vars += "&estado={}".format(estado)

                if filtro2:
                    query = ProfesorMateria.objects.filter(filtro2).order_by('-id')
                else:
                    query = ProfesorMateria.objects.filter(filtro).order_by('-id')
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
                data["eSinheteros"] = query.filter(materia__inicioeval__isnull=True).count()
                data["eSinAuto"] = query.filter(materia__inicioevalauto__isnull=True).count()
                iddet = DetalleFechasEvalDirMateria.objects.filter(materia__id__in=query.values_list('materia__id', flat=True)).values_list('materia__id', flat=True).distinct()
                data["eSinDir"] = query.exclude(materia__id__in=iddet).count()
                iddet = DetalleResultadosEvaluacionPosgrado.objects.filter(materia__id__in=query.values_list('materia__id', flat=True)).values_list('materia__id', flat=True).distinct()
                data["eSinProcesadas"] = query.exclude(materia__id__in=iddet).count()
                data["eProcesadas"] = query.filter(materia__id__in=iddet).count()

                iddet2 = InscripcionEncuestaSatisfaccionDocente.objects.filter(status=True, materiaasignada__materia__id__in=query.values_list('materia__id', flat=True), encuesta__tipo=2).values_list('materiaasignada__materia__id', flat=True).order_by('materiaasignada__materia__id').distinct()
                data["eSinSatisEst"] = query.exclude(materia__id__in=iddet2).count()
                data["eConSatisEst"] = query.filter(materia__id__in=iddet2).count()
                data["eEscuelas"] = EscuelaPosgrado.objects.filter(status=True)
                return render(request, "adm_evaluacionposgrado/view.html", data)
            except Exception as ex:
                pass
