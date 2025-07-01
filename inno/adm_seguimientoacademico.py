# -*- coding: latin-1 -*-
import json
import calendar
import random
import io
import os
import math
import base64
import numpy as np
import matplotlib.pyplot as plt
from django.contrib import messages
from datetime import datetime, date, timedelta
from django.contrib.admin.models import LogEntry
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from django.template.base import kwarg_re
from django.template.context import Context
from django.template.loader import get_template
from django.db.models import Q, F, Value, Count, Case, When, ExpressionWrapper, FloatField, Subquery, OuterRef, Exists
from django.db.models.functions import Concat, Coalesce
from django.db import transaction, connections, models
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.excelbackground import limpiar_cache_encuesta_silabo
from sga.funciones import MiPaginador, log, Round2, convertir_lista, Round4, generar_nombre, variable_valor
from sga.models import Materia, ProfesorMateria, Profesor, Modulo, Clase, ModuloGrupo, Modalidad, TemaAsistencia, \
    SubTemaAsistencia, SubTemaAdicionalAsistencia, Silabo, SilaboSemanal, ResponsableCoordinacion, Carrera, Malla, \
    NivelMalla, Asignatura, Paralelo, Notificacion, Coordinacion, CoordinadorCarrera, EncuestaGrupoEstudiantes, \
    Inscripcion, Matricula, MateriaAsignada, Encuesta, ProfesorDistributivoHoras, Periodo
from sga.funcionesxhtml2pdf import conviert_html_to_pdf, conviert_html_to_pdf_name, convert_html_to_pdf
from sga.templatetags.sga_extras import encrypt, informe_actividades_mensual_docente_v4_extra
from settings import DEBUG, SITE_STORAGE
from inno.models import EncuestaGrupoEstudianteSeguimientoSilabo, InscripcionEncuestaEstudianteSeguimientoSilabo, \
    PreguntaEncuestaGrupoEstudiantes, RespuestaPreguntaEncuestaSilaboGrupoEstudiantes
from inno.forms import InscripcionEncuestaEstudianteSeguimientoSilaboForm


@login_required(redirect_field_name='ret', login_url='/loginsga')
@transaction.atomic()
# @secure_module
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    fechahoy = datetime.now().date()
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_administrativo():
        return HttpResponseRedirect("/?info=Solo los perfiles administrativos pueden ingresar al modulo.")

    data['periodo'] = periodo = request.session['periodo']
    if persona.es_profesor():
        idcoordinacion = persona.profesor().coordinacion.id
        coordinacion = persona.profesor().coordinacion
        data['profesor'] = profesor = persona.profesor()
    es_administrativo = perfilprincipal.es_administrativo()
    dominio_sistema = 'https://sga.unemi.edu.ec'

    if DEBUG:
        dominio_sistema = 'http://localhost:8000'

    data["DOMINIO_DEL_SISTEMA"] = dominio_sistema

    if not es_administrativo:
        return HttpResponseRedirect("/?info=El Módulo está disponible para administrativos.")

    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']
            # if action == 'asignarencuestasilabo':
            #     try:
            #         # Obtener IDs de inscripciones que cumplen con las condiciones dadas
            #         ids_inscripciones = Inscripcion.objects.filter(
            #             status=True,
            #             matricula__retiradomatricula=False,
            #             matricula__nivel__periodo_id=periodo,
            #             coordinacion_id__in=[1, 2, 3, 4, 5]
            #         ).values_list('id', flat=True)
            #         f = InscripcionEncuestaEstudianteSeguimientoSilaboForm(request.POST)
            #         if f.is_valid():
            #             if ids_inscripciones:
            #                 encuesta_estudiante_silabo = EncuestaGrupoEstudianteSeguimientoSilabo(
            #                     encuestagrupoestudiantes=f.cleaned_data['encuesta'],
            #                     fechainicioencuesta=f.cleaned_data['fechainicioencuesta'],
            #                     fechafinencuesta=f.cleaned_data['fechafinencuesta'],
            #                     categoria=True)
            #                 encuesta_estudiante_silabo.save(request)
            #                 for id_ins in ids_inscripciones:
            #                     ids_matriculas = Matricula.objects.values_list('id', flat=True).filter(
            #                         inscripcion_id=id_ins,
            #                         nivel__periodo_id=periodo,
            #                         status=True)
            #                     if ids_matriculas:
            #                         for id_matricula in ids_matriculas:
            #                             ids_materias = MateriaAsignada.objects.values_list('materia_id',
            #                                                                                flat=True).filter(
            #                                 status=True,
            #                                 matricula_id=id_matricula,
            #                                 materia__profesormateria__status=True,
            #                                 materia__profesormateria__tipoprofesor__in=[
            #                                     1, 14],
            #                                 materia__profesormateria__activo=True,
            #                                 materia__profesormateria__hora__gt=0,
            #                                 materia__profesormateria__principal=True,
            #                                 materia__profesormateria__desde__lte=fechahoy,
            #                                 materia__profesormateria__hasta__gte=fechahoy
            #                             )
            #                             encuesta_seguimiento = None
            #                             bandera = False
            #                             if ids_materias:
            #                                 for id_mat in ids_materias:
            #                                     if not InscripcionEncuestaEstudianteSeguimientoSilabo.objects.filter(
            #                                             encuesta=f.cleaned_data['encuesta'],
            #                                             inscripcion_id=id_ins,
            #                                             status=True).exists():
            #                                         encuesta_seguimiento = InscripcionEncuestaEstudianteSeguimientoSilabo(
            #                                             encuesta=f.cleaned_data['encuesta'],
            #                                             inscripcion_id=id_ins,
            #                                             materia_id=id_mat)
            #                                         encuesta_seguimiento.save(request)
            #                                         bandera = True
            #                             if bandera == True:
            #                                 log(u'Adicionó nueva encuesta: %s' % encuesta_seguimiento, request, "add")
            #             return JsonResponse({"result": False, "mensaje": u"Encuesta aplicada."})
            #         else:
            #             transaction.set_rollback(True)
            #             return JsonResponse(
            #                 {'result': "bad", "form": [{k: v[0]} for k, v in f.errors.items()],
            #                  "mensaje": "Error en el formulario"})
            #     except Exception as ex:
            #         transaction.set_rollback(True)
            #         return JsonResponse({"result": "bad", "mensaje": u"Error al asignar la encuesta"})

            if action == 'editencuesta':
                try:
                    f = InscripcionEncuestaEstudianteSeguimientoSilaboForm(request.POST)
                    f.fields['encuesta'].required = False
                    if f.is_valid():
                        encuesta_estudiante_silabo = EncuestaGrupoEstudianteSeguimientoSilabo.objects.get(
                            pk=encrypt(request.POST['id']))
                        # encuesta_estudiante_silabo.encuestagrupoestudiantes = f.cleaned_data['encuesta']
                        encuesta_estudiante_silabo.fechainicioencuesta = f.cleaned_data['fechainicioencuesta']
                        encuesta_estudiante_silabo.fechafinencuesta = f.cleaned_data['fechafinencuesta']
                        encuesta_estudiante_silabo.save(request)
                        datos = {'periodo': periodo}
                        limpiar_cache_encuesta_silabo(request=request, data=datos).start()
                        log(u'Modificó encuesta : %s' % encuesta_estudiante_silabo, request, "edit")
                        return JsonResponse({"result": False, 'mensaje': 'Edicion Exitosa'})
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse(
                            {'result': "bad", "form": [{k: v[0]} for k, v in f.errors.items()],
                             "mensaje": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})

            elif action == 'reportesseguimientoacademico':
                try:

                    now = datetime.now()
                    fileurl, filename = '', ''
                    tiporeporte = int(encrypt(request.POST.get('t', encrypt(0))))

                    folder_pdf = os.path.join(SITE_STORAGE, 'media', 'informespoacarrera', '')
                    os.makedirs(folder_pdf, exist_ok=True)
                    os.makedirs(os.path.join(folder_pdf, f"{now.year}", ''), exist_ok=True)

                    data['now'] = now
                    carrera = Carrera.objects.filter(id=request.POST.get('c', None)).first()

                    if tiporeporte == 1:
                        if not carrera:
                            if director_car := periodo.coordinadorcarrera_set.filter(tipo=3, persona=persona, status=True, carrera__coordinacion=9).first():
                                carrera = director_car.carrera
                        periodosconsulta = request.POST.getlist('periodos')
                        if not periodosconsulta or periodosconsulta == ['']:
                            raise NameError('Por favor seleccione al menos un periodo')
                        if anio := int(request.POST.get('a', 0)):
                            periodospasados = []
                            periodosactual = list(map(int, periodosconsulta))
                            excluded = Q(nombre__icontains='PLANIFICAC')
                            periodo1 = Periodo.objects.filter(id__in=periodosactual, inicio__year=anio, inicio__month__lte=7).exists()
                            periodo2 = Periodo.objects.filter(id__in=periodosactual, inicio__year=anio, inicio__month__gt=7).exists()
                            if anio == 2024:
                                periodo1 and periodospasados.append(177)
                                periodo2 and periodospasados.append(224)
                            else:
                                aniopasado = anio - 1
                                materiascoordadm = Materia.objects.filter(inicio__year=aniopasado, asignaturamalla__malla__carrera__coordinacion=9, status=True, asignaturamalla__asignatura__modulo=False).values_list('nivel__periodo', flat=True).distinct()
                                periodospasados1 = Periodo.objects.filter(id__in=materiascoordadm, inicio__year=aniopasado, inicio__month__lte=7).values_list('id', flat=True).exclude(excluded).exclude(tipo__in=[7, 8])
                                periodospasados2 = Periodo.objects.filter(id__in=materiascoordadm, inicio__year=aniopasado, inicio__month__gt=7).values_list('id', flat=True).exclude(excluded).exclude(tipo__in=[7, 8])
                                periodo1 and periodospasados.append(*list(periodospasados1))
                                periodo2 and periodospasados.append(*list(periodospasados2))
                            data['resultados'] = reporte_nivelacion_carrera(request=request, carrera=carrera, periodos=periodosactual)
                            data['historicos'] = reporte_nivelacion_carrera(request=request, carrera=carrera, periodos=periodospasados)
                            datos_actual, datos_anteri = data['resultados']['ejecucion'], data['historicos']['ejecucion']
                            aclabels = [f'Ef. Niv. ({anio - 1})', f'Ef. Niv. ({anio})']
                            acvalues = [datos_anteri[5][1], datos_actual[5][1]]

                            color = ['gray', 'blue']
                            if acvalues[0] > acvalues[1]:
                                color.sort(reverse=False)

                            plt.figure(figsize=(6, 1.5))
                            plt.barh(aclabels, acvalues, color=color, height=0.25)

                            plt.title(f'Análisis comparativo de variables: año {anio} vs año {anio-1}', fontsize=9)

                            for i, value in enumerate(acvalues):
                                plt.text(value + 1, i, f'{value}%', va='center', fontsize=7)

                            plt.xlim(0, 100)
                            plt.xticks(fontsize=7)
                            plt.yticks(ticks=[0.02, 1 - 0.02], labels=aclabels, fontsize=7)

                            for spine in plt.gca().spines.values():
                                spine.set_linewidth(0.5)

                            texto_descriptivo = "*Se muestra el analisis por año en funcion de los periodos " \
                                                "seleccionados "
                            plt.figtext(0.5, -0.1, texto_descriptivo, wrap=True, horizontalalignment='center', fontsize=6)

                            buffer = io.BytesIO()
                            plt.savefig(buffer, format='png', dpi=600, bbox_inches='tight', transparent=True)
                            plt.close()
                            buffer.seek(0)
                            imagencomparativo64 = base64.b64encode(buffer.read()).decode('utf-8')
                            plt.close()

                            data['img_analisis'] = imagencomparativo64
                            data['img_utilidad'] = get_funcion_utilidad(datos_actual[5][1])

                            filename = generar_nombre(f'{persona.usuario.username}_recn_', '') + '.pdf'

                    if tiporeporte in [2, 3]:
                        if not carrera:
                            if director_car := periodo.coordinadorcarrera_set.filter(tipo=3, persona=persona, status=True, carrera__coordinacion__in=(1,2,3,4,5)).first():
                                carrera = director_car.carrera
                        carreras = [carrera.pk]
                        eperiodo = request.POST['periodos']
                        filename = generar_nombre(f'{persona.usuario.username}_rpc_', '') + '.pdf'
                        data = data | reporte_permanencia_carrera(carreras=carreras, periodo=eperiodo, tiporeporte=tiporeporte)

                    # Generacion de archivo .pdf
                    fileroute = os.path.join(os.path.join(SITE_STORAGE, 'media', 'informespoacarrera', f'{now.year}', ''))
                    if filename and convert_html_to_pdf(f'adm_seguimientoacademico/reportes_poa/pdf/reporte_{tiporeporte}.html', data, filename, fileroute):
                        fileurl = f"media/informespoacarrera/{now.year}/" + filename

                    template = get_template(f"adm_seguimientoacademico/reportes_poa/detallereporte_{tiporeporte}.html")
                    return JsonResponse({"result": 'ok', 'fileurl': fileurl, 'html': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": 'bad', 'mensaje': f"{ex}"})

            elif action == 'activar_desactivar_encuesta':
                try:
                    encuesta_estudiante_silabo = EncuestaGrupoEstudianteSeguimientoSilabo.objects.values_list(
                        'encuestagrupoestudiantes', flat=True).filter(
                        pk=encrypt(request.POST['id']))
                    encuesta = EncuestaGrupoEstudiantes.objects.get(pk__in=encuesta_estudiante_silabo)
                    if encuesta.activo == True:
                        encuesta.activo = False
                    else:
                        encuesta.activo = True
                    encuesta.save(request)
                    datos = {'periodo': periodo}
                    limpiar_cache_encuesta_silabo(request=request, data=datos).start()
                    log(u'Modificó encuesta : %s' % encuesta, request, "edit")
                    return JsonResponse({"result": False, 'mensaje': 'Edicion Exitosa'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})

            elif action == 'traeralumnos':
                try:
                    f = InscripcionEncuestaEstudianteSeguimientoSilaboForm(request.POST)
                    id_encuesta = None
                    if f.is_valid():
                        if EncuestaGrupoEstudianteSeguimientoSilabo.objects.filter(status=True,
                                                                                   fechafinencuesta__gte=fechahoy,
                                                                                   encuestagrupoestudiantes__activo=True).exists():
                            return JsonResponse({"result": True,
                                                 "mensaje": u"No se puede asignar una nueva encuesta mientras otra esté activa."})
                        listaenviar = Inscripcion.objects.values_list('id',
                                      'persona__apellido1',
                                      'persona__apellido2',
                                      'persona__nombres').order_by(
                            'persona__apellido1').filter(
                            status=True,
                            matricula__retiradomatricula=False,
                            matricula__nivel__periodo_id=periodo,
                            coordinacion_id__in=[1, 2, 3, 4, 5]
                        )
                        if listaenviar:
                            id_encuesta = f.cleaned_data['encuesta']
                            id_encuesta_seguimiento_silabo = EncuestaGrupoEstudianteSeguimientoSilabo.objects.values_list('id',flat=True).filter(status = True, encuestagrupoestudiantes_id=id_encuesta.id).order_by('id').last()
                            encuesta_estudiante_silabo = EncuestaGrupoEstudianteSeguimientoSilabo.objects.get(
                                pk=id_encuesta_seguimiento_silabo)
                            encuesta_estudiante_silabo.fechainicioencuesta = f.cleaned_data['fechainicioencuesta']
                            encuesta_estudiante_silabo.fechafinencuesta = f.cleaned_data['fechafinencuesta']
                            encuesta_estudiante_silabo.save(request)
                            # encuesta_estudiante_silabo = EncuestaGrupoEstudianteSeguimientoSilabo(
                            #     encuestagrupoestudiantes=f.cleaned_data['encuesta'],
                            #     fechainicioencuesta=f.cleaned_data['fechainicioencuesta'],
                            #     fechafinencuesta=f.cleaned_data['fechafinencuesta'],
                            #     categoria=True)
                            # encuesta_estudiante_silabo.save(request)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse(
                            {'result': "bad", "form": [{k: v[0]} for k, v in f.errors.items()],
                             "mensaje": "Error en el formulario"})
                    return JsonResponse(
                        {"result": "ok", "cantidad": len(listaenviar), "inscritos": convertir_lista(listaenviar), "id_encuesta":id_encuesta.id})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al listar los estudiantes."})

            elif action == 'asignar_encuesta_individual':
                try:
                    ids_matriculas = Matricula.objects.values_list('id', flat=True).filter(
                        inscripcion_id=request.POST['id_ins'],
                        nivel__periodo_id=periodo,
                        status=True)
                    if ids_matriculas:
                        for id_matricula in ids_matriculas:
                            ids_materias = MateriaAsignada.objects.values_list('materia_id',
                                                                               flat=True).filter(
                                status=True,
                                matricula_id=id_matricula,
                                materia__profesormateria__status=True,
                                materia__profesormateria__tipoprofesor__in=[
                                    1, 14],
                                materia__profesormateria__activo=True,
                                materia__profesormateria__hora__gt=0,
                                materia__profesormateria__principal=True,
                                materia__profesormateria__desde__lte=fechahoy,
                                materia__profesormateria__hasta__gte=fechahoy
                            )
                            encuesta_seguimiento = None
                            bandera = False
                            if ids_materias:
                                for id_mat in ids_materias:
                                    if not InscripcionEncuestaEstudianteSeguimientoSilabo.objects.filter(
                                            encuesta_id=request.POST['id_encuesta'],
                                            inscripcion_id=request.POST['id_ins'],
                                            materia_id=id_mat,
                                            status=True).exists():
                                        encuesta_seguimiento = InscripcionEncuestaEstudianteSeguimientoSilabo(
                                            encuesta_id=request.POST['id_encuesta'],
                                            inscripcion_id=request.POST['id_ins'],
                                            materia_id=id_mat)
                                        encuesta_seguimiento.save(request)
                                        bandera = True
                            if bandera == True:
                                log(u'Adicionó nueva encuesta: %s' % encuesta_seguimiento, request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al asignar la encuesta."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
            reportes = [
                {
                    'name': f'Reporte de eficiencia del curso de nivelación de carreras',
                    'icon': 'bi bi-file-binary-fill',
                    'category': 1,
                    'type': 1
                },
                {
                    'name': f'Reporte de permanencia de carrera',
                    'icon': 'fa fa-users',
                    'category': 1,
                    'type': 2
                },
                {
                    'name': f'Reporte de permanencia de carrera (GHE)',
                    'icon': 'fa fa-users',
                    'category': 1,
                    'type': 3
                }
            ]

            if action == 'reportesseguimientoacademico':
                try:
                    data['title'] = f"Reportes para POA de carrera"
                    now = datetime.now()
                    periodosactual = []
                    anioconsulta = list(range(now.year-30, now.year + 1))
                    anioconsulta.sort(reverse=True)
                    data['reportes'] = reportes
                    data['anioconsulta'] = anioconsulta
                    data['periodosactual'] = periodosactual
                    data['coordinadorcarrera'] = periodo.coordinadorcarrera_set.filter(persona=persona, tipo=3, status=True).exclude(carrera__coordinacion=9).first()
                    return render(request, 'adm_seguimientosilabo/reportes.html', data)
                except Exception as ex:
                    pass

            if action == 'get-imagen-formula':
                try:
                    tipo = int(encrypt(request.GET['t']))
                    return JsonResponse({'result':'ok', 'img': get_formula_img(tipo)})
                except Exception as ex:
                    return JsonResponse({'result':'bad', 'mensaje': ex.__str__()})

            if action == 'load-periodos-consulta':
                try:
                    from sga.models import MESES_CHOICES
                    anio = int(request.GET['a'])
                    tipoinforme = int(encrypt(request.GET['t']))
                    lista_periodos = get_periodos_validos(anio=anio, tipoinforme=tipoinforme, periodo=periodo, persona=persona)
                    if not lista_periodos:
                        raise NameError(f"No existe oferta académica de la carrera en el año seleccionado")
                    return JsonResponse({'result': 'ok', 'periodos': list(lista_periodos.values_list('id', 'nombre'))})
                except Exception as ex:
                    return JsonResponse({'result': 'bad', 'mensaje': ex.__str__()})

            if action == 'seguimiento-clases-videos':
                try:
                    if not persona.usuario.has_perm('inno.puede_evaluar_videos_clases_virtuales'):
                        raise NameError(
                            f'Estimad{"a" if persona.es_mujer() else "o"} {persona.nombre_completo().split()[0].title()}, no tiene permisos para visualizar esta pantalla.')

                    data['title'] = u'Detalle de clases sincrónicas y asincrónicas'
                    profesoresmateria = ProfesorMateria.objects.filter(
                        materia__asignaturamalla__malla__carrera__modalidad=3, materia__nivel__periodo=periodo,
                        profesor__activo=True, activo=True, materia__status=True, profesor__status=True,
                        status=True).values_list('profesor', flat=True).distinct()
                    data['profesores'] = Profesor.objects.filter(pk__in=profesoresmateria)
                    return render(request, 'adm_seguimientosilabo/seguimientoclasesvideos.html', data)
                except Exception as ex:
                    return HttpResponseRedirect(request.path + f'?info={ex=}')

            if action == 'asignarrespuestas':
                try:
                    inscripciones = InscripcionEncuestaEstudianteSeguimientoSilabo.objects.filter(status=True)[:240000]
                    preguntas = PreguntaEncuestaGrupoEstudiantes.objects.filter(status=True, encuesta_id=75)

                    # Iterar sobre cada inscripción y cada pregunta para crear registros en inno_respuestapreguntaencuestasilabogrupoestudiantes
                    for inscripcion in inscripciones:
                        for pregunta in preguntas:
                            # Generar valor aleatorio para "respuesta" ('SI' o 'NO')
                            valor_respuesta = random.choice(['SI', 'NO'])

                            # Crear registro en inno_respuestapreguntaencuestasilabogrupoestudiantes
                            if not RespuestaPreguntaEncuestaSilaboGrupoEstudiantes.objects.filter(
                                    inscripcionencuestasilabo_id=inscripcion.id,
                                    pregunta_id=pregunta.id,
                                    status=True).exists():
                                respuesta = RespuestaPreguntaEncuestaSilaboGrupoEstudiantes.objects.create(
                                    inscripcionencuestasilabo_id=inscripcion.id,
                                    pregunta_id=pregunta.id,
                                    respuesta=valor_respuesta,
                                    respuestaporno=''
                                )
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})

            elif action == 'estadistica_encuesta':
                try:
                    data['title'] = u'Resultados estadísticos'
                    data['id'] = id = request.GET.get('id')
                    # filtro = Q(status=True, inscripcionencuestasilabo__materia__nivel__periodo=periodo, inscripcionencuestasilabo__materia__profesormateria__tipoprofesor__in=[1, 14],
                    #            inscripcionencuestasilabo__materia__profesormateria__activo=True, inscripcionencuestasilabo__materia__profesormateria__status=True,
                    #            inscripcionencuestasilabo__materia__profesormateria__principal = True, inscripcionencuestasilabo__materia__profesormateria__hora__gt=0
                    #            )
                    filtro = Q(status=True, inscripcionencuestasilabo__materia__nivel__periodo=periodo, inscripcionencuestasilabo__materia__profesormateria__tipoprofesor__in=[1, 14])
                    url_vars, search = f'&action=estadistica_encuesta&id={id}', ''

                    #-----------DIRECTIVOS-----------#
                    idsdirectivos = [25320, 26985]
                    data['super_directivos'] = super_directivos = False
                    if persona.pk in idsdirectivos or persona.usuario.groups.filter(
                            name__startswith='VICERREC').distinct().exists():
                        data['super_directivos'] = super_directivos = True

                    carreras = 0
                    asignaturaselected = 0
                    nivelselected = 0
                    paraleloselected = '0'
                    carrerasselected = 0
                    director_car = False
                    if not super_directivos:
                        # miscarreras = persona.mis_carreras_tercer_nivel()
                        # tiene_carreras_director = True if miscarreras else False
                        querydecano = ResponsableCoordinacion.objects.filter(periodo=periodo, status=True,coordinacion__in = [1,2,3,4,5],
                                                                             persona=persona, tipo=1)
                        # if not querydecano:
                        #     if not tiene_carreras_director:
                        #         return HttpResponseRedirect(f"{request.path}?info=Debe tener carreras asignadas.")
                        # es_director_carr = querydecano.exists() if querydecano.exists() else False

                        data['es_decano'] = es_decano = querydecano.exists()
                        # carreras = carreras_imparte_ids(profesor)
                        if not es_decano:
                            profesor = persona.profesor()
                            director_car = False
                            if profesor:
                                carreras = []
                                distributivo = ProfesorDistributivoHoras.objects.filter(periodo_id=periodo.pk,
                                                                                        profesor=profesor)
                                if distributivo:
                                    carreras_coord = distributivo[0].coordinacion.listadocarreras(periodo)
                                    for carr in carreras_coord:
                                        if persona == carr.coordinador(periodo,
                                                                       distributivo[0].coordinacion.sede).persona:
                                            carreras.append(carr.id)
                                    if carreras:
                                        director_car = CoordinadorCarrera.objects.filter(carrera__in=carreras,
                                                                                         periodo=periodo,
                                                                                         status=True,
                                                                                         persona=persona,
                                                                                         tipo=3).first()
                        # director_car = CoordinadorCarrera.objects.filter(periodo=periodo,
                        #                                                  status=True, persona=persona, tipo=3).first()
                        if director_car:
                            data['carrera'] = director_car = director_car.carrera
                            data['facultad'] = distributivo[0].coordinacion.nombre
                            data['es_director_carr'] = True
                        # CARRERAS
                        if not es_decano and not director_car:
                            return HttpResponseRedirect(f"{request.path}?info=Debe constar como decano o director de carrera en el periodo seleccionado. {periodo.nombre}")

                        if es_decano:
                            idcoordinacion = ResponsableCoordinacion.objects.values_list('coordinacion_id',
                                                                                         flat=True).filter(
                                periodo=periodo, status=True, persona=persona).first()
                            if idcoordinacion == 2 or idcoordinacion == 3:
                                idcoordinacion = (2, 3)
                            else:
                                idcoordinacion = (idcoordinacion,)
                            contador = querydecano.count()
                            carrerasin = None
                            if contador > 1:
                                carrerasin = querydecano[0].coordinacion.carrera.filter(status=True)
                                for i in range(1, contador):
                                    carrerasin = carrerasin.union(
                                        querydecano[i].coordinacion.carrera.filter(status=True))
                            else:
                                carrerasin = querydecano[0].coordinacion.carrera.filter(status=True)
                            carrerasin_lista = list(carrerasin)
                            mallacarrerasdecano = Malla.objects.filter(status=True, carrera__in=carrerasin_lista)
                            carreras = []
                            for carr in mallacarrerasdecano:
                                if carr.uso_en_periodo(periodo):
                                    carreras.append(carr.carrera.id)
                            data['carreras'] = Carrera.objects.filter(id__in=carreras, status=True)
                            # filtro = filtro & Q(profesor__coordinacion__id__in=idcoordinacion)
                        else:
                        #--------------------FILTROS DIRECTORES-------------------#
                            # ASIGNATURAS
                            data['asignaturas'] = asignaturas = Asignatura.objects.filter(
                                id__in=Materia.objects.values_list('asignatura_id', flat=True).filter(
                                    asignaturamalla__malla__carrera__id__in=carreras,
                                    asignaturamalla__transversal=False,
                                    nivel__periodo=periodo, status=True).distinct().order_by(
                                    'asignaturamalla__nivelmalla__nombre'), status=True)

                            # NIVEL
                            data['nivel'] = nivel = NivelMalla.objects.filter(
                                id__in=Materia.objects.values_list('asignaturamalla__nivelmalla__id',
                                                                   flat=True).filter(
                                    asignaturamalla__malla__carrera__id__in=carreras, status=True,
                                    nivel__periodo=periodo).distinct().order_by(
                                    'asignaturamalla__nivelmalla__nombre'), status=True)

                    else:
                        data['facultades'] = Coordinacion.objects.filter(id__in=(1, 2, 4, 5), status=True)
                        if 'facu' in request.GET and int(request.GET['facu']) > 0:
                            data['facultadeselected'] = facultadeselected = int(request.GET['facu'])
                            url_vars += f'&facu={facultadeselected}'
                            if facultadeselected == 2:
                                idcoordinacion = (2, 3)
                            else:
                                idcoordinacion = (facultadeselected,)
                            # filtro = filtro & Q(profesor__coordinacion__id__in=idcoordinacion)
                            coordinacion = Coordinacion.objects.filter(id__in=idcoordinacion, status=True)
                            contador = coordinacion.count()
                            carrerasin = None
                            if contador > 1:
                                carrerasin = coordinacion[0].carrera.filter(status=True)
                                for i in range(1, contador):
                                    carrerasin = carrerasin.union(coordinacion[i].carrera.filter(status=True))
                            else:
                                carrerasin = coordinacion[0].carrera.filter(status=True)
                            carrerasin_lista = list(carrerasin)
                            mallacarrerasdecano = Malla.objects.filter(status=True, carrera__in=carrerasin_lista)
                            carreras = []
                            for carr in mallacarrerasdecano:
                                if carr.uso_en_periodo(periodo):
                                    carreras.append(carr.carrera.id)
                            data['carreras'] = Carrera.objects.filter(id__in=carreras, status=True)
                        else:
                            filtro = filtro & Q(inscripcionencuestasilabo__materia__profesormateria__profesor__coordinacion__id__in=[1,2,3,4,5])
                            coordinacion = Coordinacion.objects.filter(id__in=[1,2,3,4,5], status=True)
                            contador = coordinacion.count()
                            carrerasin = None
                            if contador > 1:
                                carrerasin = coordinacion[0].carrera.filter(status=True)
                                for i in range(1, contador):
                                    carrerasin = carrerasin.union(coordinacion[i].carrera.filter(status=True))
                            else:
                                carrerasin = coordinacion[0].carrera.filter(status=True)
                            carrerasin_lista = list(carrerasin)
                            mallacarrerasdecano = Malla.objects.filter(status=True, carrera__in=carrerasin_lista)
                            carreras = []
                            for carr in mallacarrerasdecano:
                                if carr.uso_en_periodo(periodo):
                                    carreras.append(carr.carrera.id)


                    #----------------------FILTRADO POR DOCENTE-----------------------------#

                    if 's' in request.GET:
                        search = request.GET['s']
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro = filtro & (Q(inscripcionencuestasilabo__materia__profesormateria__profesor__persona__nombres__icontains=search) |
                                               Q(inscripcionencuestasilabo__materia__profesormateria__profesor__persona__apellido1__icontains=search) |
                                               Q(inscripcionencuestasilabo__materia__profesormateria__profesor__persona__apellido2__icontains=search) |
                                               Q(inscripcionencuestasilabo__materia__profesormateria__profesor__persona__cedula__icontains=search) |
                                               Q(inscripcionencuestasilabo__materia__profesormateria__profesor__persona__pasaporte__icontains=search))
                        else:
                            filtro = filtro & (Q(inscripcionencuestasilabo__materia__profesormateria__profesor__persona__apellido1__icontains=ss[0]) &
                                               Q(inscripcionencuestasilabo__materia__profesormateria__profesor__persona__apellido2__icontains=ss[1]))
                        url_vars += f"&s={search}"

                    #----------------------FILTRADO POR CARRERAS-----------------------------#

                    if 'carr' in request.GET and int(request.GET['carr']) > 0:
                        carreras = []
                        data['carrerasselected'] = carrerasselected = int(request.GET['carr'])
                        url_vars += f'&carr={carrerasselected}'
                        carreras.append(carrerasselected)
                        filtro = filtro & Q(inscripcionencuestasilabo__materia__asignaturamalla__malla__carrera__id__in=carreras)
                        ############################
                        # ASIGNATURAS
                        data['asignaturas'] = asignaturas = Asignatura.objects.filter(
                            id__in=Materia.objects.values_list('asignatura_id', flat=True).filter(
                                asignaturamalla__malla__carrera__id__in=carreras,
                                asignaturamalla__transversal=False,
                                nivel__periodo=periodo, status=True).distinct().order_by(
                                'asignaturamalla__nivelmalla__nombre'), status=True)

                        # NIVEL
                        data['nivel'] = nivel = NivelMalla.objects.filter(
                            id__in=Materia.objects.values_list('asignaturamalla__nivelmalla__id',
                                                               flat=True).filter(
                                asignaturamalla__malla__carrera__id__in=carreras, status=True,
                                nivel__periodo=periodo).distinct().order_by(
                                'asignaturamalla__nivelmalla__nombre'), status=True)

                    if 'asig' in request.GET and int(request.GET['asig']) > 0:
                        asignaturaselected = int(request.GET['asig'])
                        url_vars += f'&asig={asignaturaselected}'
                        filtro = filtro & Q(inscripcionencuestasilabo__materia__asignaturamalla__asignatura__id=asignaturaselected)
                        data['nivel'] = nivel = NivelMalla.objects.filter(
                            id__in=Materia.objects.values_list('asignaturamalla__nivelmalla__id',
                                                               flat=True).filter(
                                asignaturamalla__malla__carrera__id__in=carreras,
                                asignaturamalla__asignatura__id=asignaturaselected, status=True,
                                nivel__periodo=periodo).distinct().order_by(
                                'asignaturamalla__nivelmalla__nombre'), status=True)
                    if 'niv' in request.GET and int(request.GET['niv']) > 0:
                        nivelselected = int(request.GET['niv'])
                        url_vars += f'&niv={nivelselected}'
                        filtro = filtro & Q(inscripcionencuestasilabo__materia__asignaturamalla__nivelmalla__id=nivelselected)
                        # PARALELOS
                        data['paralelos'] = Paralelo.objects.filter(
                            nombre__in=Materia.objects.values_list('paralelo', flat=True).filter(status=True,
                                                                                                 asignaturamalla__malla__carrera__id__in=carreras,
                                                                                                 asignaturamalla__nivelmalla__id=nivelselected).distinct(),
                            status=True)
                        if 'par' in request.GET and request.GET['par'] != '0':
                            paraleloselected = request.GET['par']
                            data['paraleloid'] = paraleloselected
                            url_vars += f'&par={paraleloselected}'
                            filtro = filtro & Q(inscripcionencuestasilabo__materia__paralelo=paraleloselected)

                    data['encuesta'] = encuesta = EncuestaGrupoEstudiantes.objects.filter(status=True,encuestagrupoestudianteseguimientosilabo__id=int(encrypt(request.GET['id'])))
                    data['indicadores'] = RespuestaPreguntaEncuestaSilaboGrupoEstudiantes.objects.values(
                        'pregunta__id', 'pregunta__descripcion', 'pregunta__orden'
                    ).annotate(
                        cantidad_si=Coalesce(Count(Case(When(respuesta='SI', then=1))), Value(0)),
                        cantidad_no=Coalesce(Count(Case(When(respuesta='NO', then=1))), Value(0))
                        # cantidad_sinresponder=Coalesce(Count(Case(When(inscripcionencuestasilabo__respondio=False, then=1))), Value(0))
                    ).filter(
                        ~Q(respuesta__isnull=True), filtro, status=True, inscripcionencuestasilabo__respondio=True,
                        inscripcionencuestasilabo__materia__asignaturamalla__malla__carrera_id__in=carreras).distinct().order_by(
                        'pregunta__orden')

                    data['hoy'] = datetime.now().date()

                    data['carrerasselected'] = carrerasselected
                    data['asignaturaselected'] = asignaturaselected
                    data['nivelselected'] = nivelselected
                    data['paraleloselected'] = paraleloselected
                    data['s'] = search if search else ""

                    return render(request, "adm_seguimientosilabo/estadisticas_encuesta.html", data)
                except Exception as ex:
                    pass

            if action == 'verencuestas':
                try:
                    idsdirectivos = [25320, 26985]
                    data['hoy'] = hoy = datetime.now().date()
                    data['super_directivos'] = super_directivos = False
                    if persona.pk in idsdirectivos or persona.usuario.groups.filter(
                            name__startswith='VICERREC').distinct().exists():
                        data['super_directivos'] = super_directivos = True
                    data['title'] = u'Encuestas seguimiento al sílabo'
                    data['encuestas'] = encuestas = EncuestaGrupoEstudiantes.objects.filter(
                        id__in=EncuestaGrupoEstudianteSeguimientoSilabo.objects.values_list(
                            'encuestagrupoestudiantes_id',
                            flat=True).filter(categoria=True, status=True),
                        status=True).order_by('fecha_creacion').distinct()
                    return render(request, 'adm_seguimientosilabo/verencuestas.html', data)
                except Exception as ex:
                    return HttpResponseRedirect(request.path + f'?info={ex=}')

            if action == 'editencuesta':
                try:
                    data['title'] = u'Modificar encuesta'
                    data['action'] = request.GET['action']
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data[
                        'inscripcion_encuesta'] = encuesta_estudiante_silabo = EncuestaGrupoEstudianteSeguimientoSilabo.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    form = InscripcionEncuestaEstudianteSeguimientoSilaboForm(
                        initial={'encuesta': encuesta_estudiante_silabo.encuestagrupoestudiantes,
                                 'fechainicioencuesta': encuesta_estudiante_silabo.fechainicioencuesta,
                                 'fechafinencuesta': encuesta_estudiante_silabo.fechafinencuesta
                                 })
                    form.deshabilitar_campo('encuesta')
                    data['form'] = form
                    template = get_template("adm_seguimientosilabo/modal/encuestaseguimiento.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            if action == 'detalle-clases-videos':
                try:
                    data['title'] = u'Detalle clases sincrónicas y asincrónicas'

                    cursor = connections['default'].cursor()
                    data['hoy'] = hoy = datetime.now().date()
                    data['materia'] = materia = Materia.objects.get(pk=request.GET.get('id'))

                    data_extra = {}
                    profesor = Profesor.objects.get(pk=request.GET.get('profesor'))
                    sql = profesor.get_sql_query_clase_sincronica_y_asincronica(periodo)
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    modalidad, coordinacion = None, None
                    totalsincronica, totalasincronica, totalplansincronica, totalplanasincronica = 0, 0, 0, 0
                    listaasistencias = []
                    silabo = Silabo.objects.filter(profesor=profesor, materia=materia, status=True).first()
                    results = list(filter(lambda x: x[5] == materia.pk, results))
                    for cuentamarcadas in results:
                        clase = Clase.objects.get(pk=cuentamarcadas[0], status=True)
                        unidades_temp = []
                        try:
                            silabosemanal = silabo.silabosemanal_set.filter(semana=cuentamarcadas[24],
                                                                            status=True).first()
                            clase.__setattr__('numsemana', silabosemanal.numsemana)
                            for u in silabosemanal.unidades_silabosemanal():
                                pk = u.temaunidadresultadoprogramaanalitico.unidadresultadoprogramaanalitico.id
                                temas_temp = [(t.temaunidadresultadoprogramaanalitico,
                                               silabosemanal.subtemas_silabosemanal(
                                                   t.temaunidadresultadoprogramaanalitico),
                                               silabosemanal.subtemas_adicionales(t.pk)) for t in
                                              silabosemanal.temas_silabosemanal(pk)]
                                unidades_temp.append({
                                    'unidad': f'UNIDAD {u.temaunidadresultadoprogramaanalitico.unidadresultadoprogramaanalitico.orden} {u.temaunidadresultadoprogramaanalitico.unidadresultadoprogramaanalitico.descripcion}',
                                    'temas': temas_temp})
                        except Exception as ex:
                            ...
                        clase.__setattr__('unidades', unidades_temp)
                        clase.__setattr__('semana', cuentamarcadas[24])
                        clase.__setattr__('rangofecha', cuentamarcadas[8])
                        clase.__setattr__('rangodia', cuentamarcadas[9])
                        clase.__setattr__('sincronica', cuentamarcadas[10])
                        clase.__setattr__('asincronica', cuentamarcadas[11])
                        clase.__setattr__('fecha_feriado', cuentamarcadas[17])
                        clase.__setattr__('observacion_feriado', cuentamarcadas[18])
                        totalsincronica += 1 if cuentamarcadas[7] == 2 else 0
                        totalasincronica += 1 if cuentamarcadas[7] == 7 else 0
                        totalplansincronica += 1
                        totalplanasincronica += 1 if cuentamarcadas[11] else 0
                        coordinacion = clase.materia.coordinacion()
                        sincronica = clase.clasesincronica_set.filter(numerosemana=cuentamarcadas[24],
                                                                      fechaforo=cuentamarcadas[8], status=True)
                        asincronica = clase.claseasincronica_set.filter(numerosemana=cuentamarcadas[24],
                                                                        fechaforo=cuentamarcadas[8], status=True)
                        listaasistencias.append(
                            {'clase': clase, 'sincronicas': sincronica, 'asincronicas': asincronica})

                    data['profesor'] = profesor
                    data['coordinacion'] = coordinacion
                    data['listaasistencias'] = listaasistencias
                    data['totalsincronica'] = totalsincronica
                    data['totalasincronica'] = totalasincronica
                    data['totalplansincronica'] = totalplansincronica
                    data['totalplanasincronica'] = totalplanasincronica
                    template = get_template('adm_seguimientosilabo/detalleclasesvideos.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'get-materias':
                try:
                    materias = ProfesorMateria.objects.filter(materia__asignaturamalla__malla__carrera__modalidad=3,
                                                              profesor_id=request.GET.get('pk'),
                                                              materia__nivel__periodo=periodo, profesor__activo=True,
                                                              activo=True, materia__status=True, profesor__status=True,
                                                              status=True).values_list('materia_id',
                                                                                       'materia__asignaturamalla__asignatura__nombre',
                                                                                       'materia__paralelo').distinct()
                    return JsonResponse({'result': 'ok', 'data': list(materias)})
                except Exception as ex:
                    pass

            if action == 'verseguimientosilabo':
                try:
                    from sga.excelbackground import reporte_general_seguimiento_silabo,  reporte_general_seguimiento_silabo_excel, reporte_general_seguimiento_silabo_v2
                    idsdirectivos = [25320, 26985, 38488]
                    if not persona.usuario.has_perm(
                            'inno.puede_ver_seguimiento_silabo') and not persona.pk in idsdirectivos:
                        raise NameError(
                            f'Estimad{"a" if persona.es_mujer() else "o"} {persona.nombre_completo().split()[0].title()}, no tiene permisos para visualizar esta pantalla.')
                    data['super_directivos'] = super_directivos = False
                    # if persona.pk in idsdirectivos or persona.usuario.groups.filter(
                    #         name__startswith='VICERREC').distinct().exists():
                    if persona.pk in idsdirectivos:
                        data['super_directivos'] = super_directivos = True
                    carreras = []
                    asignaturaselected = 0
                    nivelselected = 0
                    paraleloselected = '0'
                    carrerasselected = 0
                    director_car = False
                    data['title'] = u'Seguimiento al sílabo del docente'
                    filtro = Q(status=True, materia__nivel__periodo=periodo, principal = True, activo = True, profesor__persona__real=True) & Q(
                        tipoprofesor__in=(1, 14))
                    url_vars, search = '&action=verseguimientosilabo', ''
                    if not super_directivos:
                        # miscarreras = persona.mis_carreras_tercer_nivel()
                        # tiene_carreras_director = True if miscarreras else False
                        querydecano = ResponsableCoordinacion.objects.filter(periodo=periodo, status=True, coordinacion__in = [1,2,3,4,5],
                                                                             persona=persona, tipo=1)
                        # if not querydecano:
                        #     if not tiene_carreras_director:
                        #         return HttpResponseRedirect(f"{request.path}?info=Debe tener carreras asignadas.")
                        # es_director_carr = querydecano.exists() if querydecano.exists() else False

                        data['es_decano'] = es_decano = querydecano.exists()
                        # carreras = carreras_imparte_ids(profesor)
                        if not es_decano:
                            profesor = persona.profesor()
                            director_car = False
                            director_car = periodo.coordinadorcarrera_set.filter(tipo=3, persona = persona, status = True, carrera__coordinacion__id__in = [1,2,3,4,5])
                            # VALIDACION CON DISTRIBUTIVO
                            # if profesor:
                            #     carreras = []
                            #     distributivo = ProfesorDistributivoHoras.objects.filter(periodo_id=periodo.pk,
                            #                                                             profesor=profesor)
                            #     if distributivo:
                            #         carreras_coord = distributivo[0].coordinacion.listadocarreras(periodo)
                            #         for carr in carreras_coord:
                            #             if persona == carr.coordinador(periodo, distributivo[0].coordinacion.sede).persona:
                            #                 carreras.append(carr.id)
                            #         if carreras:
                            #             director_car = CoordinadorCarrera.objects.filter(carrera__in=carreras,
                            #                                                              periodo=periodo,
                            #                                                              status=True,
                            #                                                              persona=persona,
                            #                                                              tipo=3).first()
                        # director_car = CoordinadorCarrera.objects.filter(periodo=periodo,
                        #                                                  status=True, persona=persona, tipo=3).first()
                        if director_car:
                            mallacarreras = Malla.objects.filter(status=True, carrera__in=director_car.values_list('carrera',flat=True))
                            carreras = []
                            for carr in mallacarreras:
                                if carr.uso_en_periodo(periodo):
                                    carreras.append(carr.carrera.id)
                                    data['carrera'] = carr.carrera.nombre
                                    data['facultad'] = carr.carrera.mi_coordinacion()
                                    # carreras.append(director_car[0].carrera.id)
                                    data['es_director_carr'] = True
                        # CARRERAS
                        if not es_decano and not director_car:
                            return HttpResponseRedirect(f"{request.path}?info=Debe constar como decano o director de carrera en el periodo seleccionado. {periodo.nombre}")
                        if es_decano:
                            idcoordinacion = ResponsableCoordinacion.objects.values_list('coordinacion_id',
                                                                                         flat=True).filter(
                                periodo=periodo, status=True, persona=persona).first()
                            if idcoordinacion == 2 or idcoordinacion == 3:
                                idcoordinacion = (2, 3)
                            else:
                                idcoordinacion = (idcoordinacion,)
                            contador = querydecano.count()
                            carrerasin = None
                            if contador > 1:
                                carrerasin = querydecano[0].coordinacion.carrera.filter(status=True)
                                for i in range(1, contador):
                                    carrerasin = carrerasin.union(
                                        querydecano[i].coordinacion.carrera.filter(status=True))
                            else:
                                carrerasin = querydecano[0].coordinacion.carrera.filter(status=True)
                            carrerasin_lista = list(carrerasin)
                            mallacarrerasdecano = Malla.objects.filter(status=True, carrera__in=carrerasin_lista)
                            carreras = []
                            for carr in mallacarrerasdecano:
                                if carr.uso_en_periodo(periodo):
                                    carreras.append(carr.carrera.id)
                            data['carreras'] = Carrera.objects.filter(id__in=carreras, status=True)
                            # filtro = filtro & Q(profesor__coordinacion__id__in=idcoordinacion)
                        else:
                            # ASIGNATURAS
                            data['asignaturas'] = asignaturas = Asignatura.objects.filter(
                                id__in=Materia.objects.values_list('asignatura_id', flat=True).filter(
                                    asignaturamalla__malla__carrera__id__in=carreras,
                                    asignaturamalla__transversal=False,
                                    nivel__periodo=periodo, status=True).exclude(asignaturamalla__tipomateria__id = 3).distinct().order_by(
                                    'asignaturamalla__nivelmalla__nombre'), status=True)

                            # NIVEL
                            data['nivel'] = nivel = NivelMalla.objects.filter(
                                id__in=Materia.objects.values_list('asignaturamalla__nivelmalla__id',
                                                                   flat=True).filter(
                                    asignaturamalla__malla__carrera__id__in=carreras, status=True,
                                    nivel__periodo=periodo).distinct().order_by(
                                    'asignaturamalla__nivelmalla__nombre'), status=True)
                        # filtro = filtro & Q(materia__asignaturamalla__malla__carrera__id__in=carreras)

                    else:
                        data['facultades'] = Coordinacion.objects.filter(id__in=(1, 2, 4, 5), status=True)
                        if 'facu' in request.GET and int(request.GET['facu']) > 0:
                            data['facultadeselected'] = facultadeselected = int(request.GET['facu'])
                            url_vars += f'&facu={facultadeselected}'
                            if facultadeselected == 2:
                                idcoordinacion = (2, 3)
                            else:
                                idcoordinacion = (facultadeselected,)
                            # filtro = filtro & Q(profesor__coordinacion__id__in=idcoordinacion)
                            coordinacion = Coordinacion.objects.filter(id__in=idcoordinacion, status=True)
                            contador = coordinacion.count()
                            carrerasin = None
                            if contador > 1:
                                carrerasin = coordinacion[0].carrera.filter(status=True)
                                for i in range(1, contador):
                                    carrerasin = carrerasin.union(coordinacion[i].carrera.filter(status=True))
                            else:
                                carrerasin = coordinacion[0].carrera.filter(status=True)
                            carrerasin_lista = list(carrerasin)
                            mallacarrerasdecano = Malla.objects.filter(status=True, carrera__in=carrerasin_lista)
                            carreras = []
                            for carr in mallacarrerasdecano:
                                if carr.uso_en_periodo(periodo):
                                    carreras.append(carr.carrera.id)
                            data['carreras'] = Carrera.objects.filter(id__in=carreras, status=True)
                        else:
                            filtro = filtro & Q(profesor__coordinacion__id__in=[1,2,3,4,5])
                            coordinacion = Coordinacion.objects.filter(id__in=[1,2,3,4,5], status=True)
                            contador = coordinacion.count()
                            carrerasin = None
                            if contador > 1:
                                carrerasin = coordinacion[0].carrera.filter(status=True)
                                for i in range(1, contador):
                                    carrerasin = carrerasin.union(coordinacion[i].carrera.filter(status=True))
                            else:
                                carrerasin = coordinacion[0].carrera.filter(status=True)
                            carrerasin_lista = list(carrerasin)
                            mallacarrerasdecano = Malla.objects.filter(status=True, carrera__in=carrerasin_lista)
                            carreras = []
                            for carr in mallacarrerasdecano:
                                if carr.uso_en_periodo(periodo):
                                    carreras.append(carr.carrera.id)
                    filtro = filtro & Q(materia__asignaturamalla__malla__carrera__id__in=carreras)
                        # else:
                        #     filtro = filtro & Q(profesor__coordinacion__id__in=(1,2,3,4,5))
                    if 's' in request.GET:
                        search = request.GET['s']
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro = filtro & (Q(profesor__persona__nombres__icontains=search) |
                                               Q(profesor__persona__apellido1__icontains=search) |
                                               Q(profesor__persona__apellido2__icontains=search) |
                                               Q(profesor__persona__cedula__icontains=search) |
                                               Q(profesor__persona__pasaporte__icontains=search))
                        else:
                            filtro = filtro & (Q(profesor__persona__apellido1__icontains=ss[0]) &
                                               Q(profesor__persona__apellido2__icontains=ss[1]))
                        url_vars += f"&s={search}"

                    if 'carr' in request.GET and int(request.GET['carr']) > 0:
                        carreras = []
                        data['carrerasselected'] = carrerasselected = int(request.GET['carr'])
                        url_vars += f'&carr={carrerasselected}'
                        carreras.append(carrerasselected)
                        filtro = filtro & Q(materia__asignaturamalla__malla__carrera__id__in=carreras)
                        ############################
                        # ASIGNATURAS
                        data['asignaturas'] = asignaturas = Asignatura.objects.filter(
                            id__in=Materia.objects.values_list('asignatura_id', flat=True).filter(
                                asignaturamalla__malla__carrera__id__in=carreras,
                                asignaturamalla__transversal=False,
                                nivel__periodo=periodo, status=True).exclude(asignaturamalla__tipomateria__id = 3).distinct().order_by(
                                'asignaturamalla__nivelmalla__nombre'), status=True)

                        # NIVEL
                        data['nivel'] = nivel = NivelMalla.objects.filter(
                            id__in=Materia.objects.values_list('asignaturamalla__nivelmalla__id',
                                                               flat=True).filter(
                                asignaturamalla__malla__carrera__id__in=carreras, status=True,
                                nivel__periodo=periodo).distinct().order_by(
                                'asignaturamalla__nivelmalla__nombre'), status=True)

                    if 'asig' in request.GET and int(request.GET['asig']) > 0:
                        asignaturaselected = int(request.GET['asig'])
                        url_vars += f'&asig={asignaturaselected}'
                        filtro = filtro & Q(materia__asignaturamalla__asignatura__id=asignaturaselected)
                        data['nivel'] = nivel = NivelMalla.objects.filter(
                            id__in=Materia.objects.values_list('asignaturamalla__nivelmalla__id',
                                                               flat=True).filter(
                                asignaturamalla__malla__carrera__id__in=carreras,
                                asignaturamalla__asignatura__id=asignaturaselected, status=True,
                                nivel__periodo=periodo).distinct().order_by(
                                'asignaturamalla__nivelmalla__nombre'), status=True)
                    if 'niv' in request.GET and int(request.GET['niv']) > 0:
                        nivelselected = int(request.GET['niv'])
                        url_vars += f'&niv={nivelselected}'
                        filtro = filtro & Q(materia__asignaturamalla__nivelmalla__id=nivelselected)
                        # PARALELOS
                        data['paralelos'] = Paralelo.objects.filter(
                            nombre__in=Materia.objects.values_list('paralelo', flat=True).filter(status=True,
                                                                                                 asignaturamalla__malla__carrera__id__in=carreras,
                                                                                                 asignaturamalla__nivelmalla__id=nivelselected).distinct(),
                            status=True)
                        if 'par' in request.GET and request.GET['par'] != '0':
                            paraleloselected = request.GET['par']
                            data['paraleloid'] = paraleloselected
                            url_vars += f'&par={paraleloselected}'
                            filtro = filtro & Q(materia__paralelo=paraleloselected)
                    listado = Profesor.objects.filter(
                        pk__in=ProfesorMateria.objects.values_list('profesor', flat=True).filter(
                            filtro).distinct()).order_by('persona__apellido1', 'persona__apellido2')
                    # PREGUNTAR SI TIENE HORARIO DE ACTIVIDADES APROBADO
                    periodoposgrado = False
                    if periodo.tipo_id in [3, 4]:
                        periodoposgrado = True
                    data['tienehorarioaprobado'] = periodo.claseactividadestado_set.filter(profesor__in=listado,
                                                                                           estadosolicitud=2,
                                                                                           status=True).exists() if not periodoposgrado else True
                    # Inicio paginación
                    data['listado'] = listado
                    paging = MiPaginador(listado, 3)
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
                    data['url_vars'] = url_vars
                    data['profesoresmaterias'] = page.object_list
                    # Fin paginación
                    data['carreras2'] = carreras
                    data['carrerasselected'] = carrerasselected
                    data['asignaturaselected'] = asignaturaselected
                    data['nivelselected'] = nivelselected
                    data['paraleloselected'] = paraleloselected
                    # data['carreras'] = carreras = Carrera.objects.filter(status=True, coordinacion__id=9).order_by(
                    #     'modalidad')

                    # SEGUIMIENTO SILABO - RECURSOS PLANIFICADOS
                    # if 'fechaini' in request.GET:
                    #     fechaini = request.GET['fechaini']
                    #     fechainisplit = fechaini.split('-')
                    #     yearini = int(fechainisplit[0])
                    #     monthini = int(fechainisplit[1])
                    #     dayini = int(fechainisplit[2])
                    #     if 'fechames' in request.GET:
                    #         fechames = request.GET['fechames']
                    #         fechasplit = fechames.split('-')
                    #         year = int(fechasplit[0])
                    #         month = int(fechasplit[1])
                    #         last_day = int(fechasplit[2])
                    # else:
                    data['fechaactual'] = fechaactual = datetime.now().date()

                    ########################### INICIO DE FECHA POR MES #######################################
                    # now = datetime.now()
                    # yearini = now.year
                    # year = now.year
                    # dayini = 1
                    # # month = now.month
                    # dia = int(now.day)
                    # if dia >= 28:
                    #     month = now.month
                    #     monthini = now.month
                    # else:
                    #     if int(now.month) == 1:
                    #         month = int(now.month)
                    #         monthini = int(now.month)
                    #     else:
                    #         month = int(now.month) - 1
                    #         monthini = int(now.month) - 1
                    # last_day = calendar.monthrange(year, month)[1]
                    # calendar.monthrange(year, month)
                    # start = date(yearini, monthini, dayini)
                    # data['fini'] = fini = str(start.day) + '-' + str(start.month) + '-' + str(start.year)
                    # end = date(year, month, last_day)
                    # data['ffin'] = ffin = str(end.day) + '-' + str(end.month) + '-' + str(end.year)
                    ###################################################################################

                    data['fini'] = fini = str(periodo.inicio)
                    data['ffin'] = ffin = str(periodo.fin)
                    data['MOSTRAR_RESULTADOS_SILABO'] = variable_valor('MOSTRAR_RESULTADOS_SILABO')
                    data['DESCARGAR_REPORTE_SILABO'] = variable_valor('DESCARGAR_REPORTE_SILABO')
                    data['s'] = search if search else ""
                    # -----EXPORTAR PDF------
                    if 'exportar_seguimiento_pdf' in request.GET:
                        noti = Notificacion(cuerpo='Reporte en proceso', titulo='PDF seguimiento al sílabo del docente',
                                            destinatario=persona,
                                            # url="/notificacion",
                                            url='',
                                            prioridad=1, app_label='SGA',
                                            fecha_hora_visible=datetime.now() + timedelta(days=1),
                                            tipo=2, en_proceso=True)
                        noti.save(request)
                        # reporte_general_seguimiento_silabo(request=request, data=data, notiid=noti.pk,
                        #                                    periodo=periodo).start()
                        reporte_general_seguimiento_silabo_v2(request=request, data=data, notiid=noti.pk,
                                                           periodo=periodo).start()
                        return JsonResponse({'result': True})
                    elif 'exportar_seguimiento_excel' in request.GET:
                        noti = Notificacion(cuerpo='Reporte en proceso', titulo='Excel seguimiento al sílabo del docente',
                                            destinatario=persona,
                                            # url="/notificacion",
                                            url='',
                                            prioridad=1, app_label='SGA',
                                            fecha_hora_visible=datetime.now() + timedelta(days=1),
                                            tipo=2, en_proceso=True)
                        noti.save(request)
                        reporte_general_seguimiento_silabo_excel(request=request, data=data, notiid=noti.pk,
                                                           periodo=periodo).start()
                        return JsonResponse({'result': True})
                    return render(request, "adm_seguimientosilabo/view.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"{request.path}?info=No puede acceder al módulo. {ex}")

            if action == 'verdetallerecursos':
                try:
                    data['id'] = request.GET['id']
                    data['idmateria'] = request.GET['idmateria']
                    data['materia'] = Materia.objects.get(pk=request.GET['idmateria'])
                    profe = Profesor.objects.get(pk=request.GET['id'])
                    # if 'fechaini' in request.GET:
                    #     fechaini = request.GET['fechaini']
                    #     fechainisplit = fechaini.split('-')
                    #     yearini = int(fechainisplit[0])
                    #     monthini = int(fechainisplit[1])
                    #     dayini = int(fechainisplit[2])
                    #     if 'fechames' in request.GET:
                    #         fechames = request.GET['fechames']
                    #         fechasplit = fechames.split('-')
                    #         year = int(fechasplit[0])
                    #         month = int(fechasplit[1])
                    #         last_day = int(fechasplit[2])
                    # else:
                    # fechames = datetime.now().date()
                    # now = datetime.now()
                    # yearini = now.year
                    # year = now.year
                    # dayini = 1
                    # # month = now.month
                    # dia = int(now.day)
                    # if dia >= 28:
                    #     month = now.month
                    #     monthini = now.month
                    # else:
                    #     if int(now.month) == 1:
                    #         month = int(now.month)
                    #         monthini = int(now.month)
                    #     else:
                    #         month = int(now.month) - 1
                    #         monthini = int(now.month) - 1
                    # last_day = calendar.monthrange(year, month)[1]
                    # calendar.monthrange(year, month)
                    # start = date(yearini, monthini, dayini)
                    # fini = str(start.day) + '-' + str(start.month) + '-' + str(start.year)
                    # end = date(year, month, last_day)
                    # ffin = str(end.day) + '-' + str(end.month) + '-' + str(end.year)
                    ##########################################################################

                    fini = str(periodo.inicio)
                    ffin = str(periodo.fin)
                    data['data'] = informe_actividades_mensual_docente_v4_extra(profe, periodo, fini, ffin, 'FACULTAD')
                    template = get_template("adm_seguimientosilabo/modal/verdetallerecursos.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'verdetalletemas':
                try:
                    data['idprofe'] = profe = request.GET['id']
                    data['idmateria'] = request.GET['idmateria']
                    data['periodo'] = periodo
                    data['materia'] = materia = Materia.objects.get(pk=request.GET['idmateria'])
                    if persona.pk == 38488:
                        template = get_template("adm_seguimientosilabo/modal/verdetalletemas_V2.html")
                    else:
                        template = get_template("adm_seguimientosilabo/modal/verdetalletemas.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'verdetalletemas_v2':
                try:
                    dataset2 = []
                    ahora = datetime.now().date()
                    cursor = connections['sga_select'].cursor()
                    semanasferiado = list(set([f.isocalendar()[1] for f in
                                               periodo.diasnolaborable_set.filter(status=True, activo=True).values_list(
                                                   'fecha', flat=True)]))
                    filtro = Q(profesor_id=request.GET['id'], materia_id = request.GET['idmateria'], materia__nivel__periodo=periodo, status=True)
                    for pm in ProfesorMateria.objects.filter(filtro).distinct('materia',
                                                                              'materia__asignaturamalla__asignatura__nombre').order_by(
                            'materia__asignaturamalla__asignatura__nombre'):
                        dataset1 = []
                        temasmarcados, subtemasmarcados = 0, 0
                        temasplanificados, subtemasplanificados = 0, 0
                        es_titulacion = False
                        silabos_semanales = SilaboSemanal.objects.filter(silabo=pm.materia.silabo_actual(),
                                                                          fechainiciosemana__lte=ahora,
                                                                          status=True).order_by('numsemana')
                        if not silabos_semanales:
                            materia_titulacion = Materia.objects.get(pk=request.GET['idmateria'], status=True)
                            if materia_titulacion.modeloevaluativo.id == 66:
                                es_titulacion = True
                        for silabosemanal in silabos_semanales:
                            fechainicio, fechafin = silabosemanal.fechainiciosemana, silabosemanal.fechafinciosemana + timedelta(
                                weeks=1)
                            if fechainicio.isocalendar()[1] in semanasferiado:
                                fechafin += timedelta(weeks=1)

                            temas = silabosemanal.detallesilabosemanaltema_set.filter(
                                temaunidadresultadoprogramaanalitico__status=True, status=True).distinct()
                            listatemassubtemas = []
                            for tema in temas:
                                marcada, fechamarcada = '-', None
                                if fechafin <= ahora:
                                    marcada = 0
                                    if temaasistencia := tema.temaasistencia_set.values_list('fecha',
                                                                                             'usuario_creacion',
                                                                                             'fecha_creacion').filter(
                                            tema__silabosemanal=silabosemanal, status=True).order_by('fecha').first():
                                        fechamarcada, usuario_creacion, fecha_creacion = temaasistencia
                                        if fechamarcada and fechamarcada < fechafin:
                                            marcada = 100
                                            temasmarcados += 1
                                            if not usuario_creacion == 1 and fecha_creacion:
                                                descripcion = f"{tema.temaunidadresultadoprogramaanalitico.descripcion}".upper()
                                                sql = f"""
                                                                        select change_message from django_admin_log 
                                                                        where (
                                                                            user_id = {usuario_creacion}
                                                                            and change_message ilike '%{descripcion}%'
                                                                            and (action_time)::DATE = '{fecha_creacion.date()}'
                                                                            and extract(hour from action_time) = {fecha_creacion.hour}
                                                                            and extract(minute from action_time) = {fecha_creacion.minute}
                                                                            and action_flag = 1
                                                                        )
                                                                        limit 1
                                                                    """
                                                cursor.execute(sql)
                                                if change_message := cursor.fetchone():
                                                    change_message = change_message[0]
                                                    if auditoria := change_message[change_message.find('--IP'):]:
                                                        len(auditoria) > 5 and tema.__setattr__('mensaje', auditoria)

                                    temasplanificados += 1
                                tema.__setattr__('marcada', marcada)
                                tema.__setattr__('fechamarcada', fechamarcada)
                                subtemas = silabosemanal.detallesilabosemanalsubtema_set.filter(
                                    subtemaunidadresultadoprogramaanalitico__temaunidadresultadoprogramaanalitico=tema.temaunidadresultadoprogramaanalitico,
                                    subtemaunidadresultadoprogramaanalitico__status=True,
                                    subtemaunidadresultadoprogramaanalitico__temaunidadresultadoprogramaanalitico__isnull=False,
                                    subtemaunidadresultadoprogramaanalitico__temaunidadresultadoprogramaanalitico__status=True,
                                    status=True).distinct()
                                for subtema in subtemas:
                                    marcada, fechamarcada = '-', None
                                    if fechafin <= ahora:
                                        marcada = 0
                                        if subtemaasistencia := subtema.subtemaasistencia_set.values_list('fecha',
                                                                                                          'usuario_creacion',
                                                                                                          'fecha_creacion').filter(
                                                subtema__silabosemanal=silabosemanal, status=True).order_by(
                                                'fecha').first():
                                            fechamarcada, usuario_creacion, fecha_creacion = subtemaasistencia
                                            if fechamarcada < fechafin:
                                                marcada = 100
                                                subtemasmarcados += 1
                                                if not usuario_creacion == 1 and fecha_creacion:
                                                    descripcion = f"{subtema.subtemaunidadresultadoprogramaanalitico.descripcion}".upper()
                                                    sql = f"""
                                                                                select change_message from django_admin_log 
                                                                                where (
                                                                                    user_id = {usuario_creacion}
                                                                                    and change_message ilike '%{descripcion}%'
                                                                                    and (action_time)::DATE = '{fecha_creacion.date()}'
                                                                                    and extract(hour from action_time) = {fecha_creacion.hour}
                                                                                    and extract(minute from action_time) = {fecha_creacion.minute}
                                                                                    and action_flag = 1
                                                                                )
                                                                                limit 1
                                                                            """
                                                    cursor.execute(sql)
                                                    if change_message := cursor.fetchone():
                                                        change_message = change_message[0]
                                                        if auditoria := change_message[change_message.find('--IP'):]:
                                                            len(auditoria) > 5 and subtema.__setattr__('mensaje',
                                                                                                       auditoria)

                                        subtemasplanificados += 1
                                    subtema.__setattr__('marcada', marcada)
                                    subtema.__setattr__('fechamarcada', fechamarcada)
                                listatemassubtemas.append({'tema': tema, 'subtemas': subtemas})
                            dataset1.append({'silabosemanal': silabosemanal, 'contenido': listatemassubtemas,
                                             'plazomaximo': fechafin})
                        porcentaje = 0
                        porcentaje_sobre_30 = 0
                        try:
                            if not es_titulacion:
                                totalmarcados, totalplanificados = temasmarcados + subtemasmarcados, temasplanificados + subtemasplanificados
                                porcentaje = (totalmarcados / totalplanificados) * 100
                            else:
                                porcentaje = 100
                            porcentaje_sobre_30 = (porcentaje * 30) / 100

                        except ZeroDivisionError as ex:
                            ...
                        dataset2.append(
                            {'materia': pm.materia, 'contenido': dataset1, 'porcentajetotal': f"{porcentaje:.2f}", 'porcentaje_sobre_30': f"{porcentaje_sobre_30:.2f}"})
                    data['dataset'] = dataset2
                    template = get_template("adm_seguimientosilabo/modal/verdetalletemas_V3.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'verdetalleencuestas':
                try:
                    data['idprofe'] = profe = request.GET['id']
                    data['idmateria'] = materia = request.GET['idmateria']

                    preguntas_con_respuestas = RespuestaPreguntaEncuestaSilaboGrupoEstudiantes.objects.values(
                        'pregunta__id', 'pregunta__descripcion'
                    ).annotate(
                        cantidad_si=Coalesce(Count(Case(When(respuesta='SI', then=1))), Value(0)),
                        cantidad_no=Coalesce(Count(Case(When(respuesta='NO', then=1))), Value(0)),
                        cantidad_total=F('cantidad_si') + F('cantidad_no'),
                        porcentaje=Round4((F('cantidad_si') * 100) / F('cantidad_total'))
                    ).filter(
                        ~Q(respuesta__isnull=True), status=True, inscripcionencuestasilabo__encuesta__encuestagrupoestudianteseguimientosilabo__periodo = periodo,inscripcionencuestasilabo__materia__id=materia).distinct()
                    suma_total = 0
                    porcentaje_total = 0
                    porcentaje_sobre30 = 0
                    cont = 0
                    if preguntas_con_respuestas.exists():
                        data['preguntas'] = preguntas_con_respuestas
                        for pregunta in preguntas_con_respuestas:
                            suma_total += pregunta['porcentaje']
                            cont += 1
                    else:
                        data[
                            'preguntas'] = preguntas_con_respuestas = RespuestaPreguntaEncuestaSilaboGrupoEstudiantes.objects.values(
                            'pregunta__id', 'pregunta__descripcion'
                        ).annotate(
                            cantidad_si=Value('-'),
                            cantidad_no=Value('-'),
                            cantidad_total=Value('-'),
                            porcentaje=Value('-')
                        ).filter(
                            ~Q(respuesta__isnull=True), status=True, inscripcionencuestasilabo__encuesta__encuestagrupoestudianteseguimientosilabo__periodo = periodo,inscripcionencuestasilabo__materia__id=materia).distinct()
                    if cont > 0:
                        data['porcentaje_total'] = porcentaje_total = round((suma_total / cont), 2)
                        data['porcentaje_sobre30'] = round(((porcentaje_total * 30) / 100), 2)
                    else:
                        data['porcentaje_total'] = 0
                        data['porcentaje_sobre30'] = 0
                    template = get_template("adm_seguimientosilabo/modal/verdetalleencuestas.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'asignarencuestasilabo':
                try:
                    data['title'] = u'Asignar Encuesta'
                    data['action'] = 'traeralumnos'
                    data['form'] = InscripcionEncuestaEstudianteSeguimientoSilaboForm()
                    template = get_template("adm_seguimientosilabo/modal/encuestaseguimiento.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)

        else:
            try:
                data['title'] = u'Seguimiento académico'
                modulos = []
                modulos_seguimiento = []
                modulos_evaluar = []
                if es_administrativo:
                    if persona.usuario.has_perm('inno.puede_ver_seguimiento_silabo'):
                        modulos.append(541)
                        if variable_valor('SUBMODULOS_SEGUIMIENTO_IDS'):
                            modulos_seguimiento = list(int(i) for i in variable_valor('SUBMODULOS_SEGUIMIENTO_IDS'))

                    if persona.usuario.has_perm('inno.puede_evaluar_videos_clases_virtuales'):
                        modulos.append(539)
                        if variable_valor('SUBMODULOS_EVALUAR_IDS'):
                            modulos_evaluar = list(int(i) for i in variable_valor('SUBMODULOS_EVALUAR_IDS'))

                    if periodo.coordinadorcarrera_set.filter(persona=persona, sede=1, tipo=3, status=True).exists():
                        modulos.append(569)

                    data['enlaceatras'] = "/"
                    data['modulos2'] = Modulo.objects.filter(id__in=modulos + modulos_seguimiento + modulos_evaluar, submodulo=True, status=True).order_by('-nombre')
                return render(request, "adm_seguimientosilabo/panel.html", data)
            except Exception as ex:
                return HttpResponseRedirect(f"/?info=No puede acceder al módulo")


def carreras_imparte_ids(profesor):
    carreras = []
    try:
        materias = profesor.materias_imparte()
        for materia in materias:
            if not materia.asignaturamalla.malla.carrera.id in carreras:
                carreras.append(materia.asignaturamalla.malla.carrera.id)
        return carreras
    except Exception as ex:
        return []


def reporte_nivelacion_carrera(**kwargs):
    try:
        from sga.models import MatriculacionPrimerNivelCarrera
        periodosconsulta = kwargs.pop('periodos')
        request, carrera = kwargs.pop('request'), kwargs.pop('carrera')
        persona, periodo = request.session.get('persona'), request.session.get('periodo')
        filtroperiodo = Q(id__in=periodosconsulta) if periodosconsulta else Q(id=periodo.pk)
        periodos = Periodo.objects.filter(filtroperiodo, status=True)
        nombreperiodos = ''
        for i, value in enumerate(periodos):
            nombreperiodos += f"{value.nombre}"
            if not i + 1 == len(periodos):
                nombreperiodos += ' | '
        data, data2 = {}, []

        filtrobase = Q(materia__asignaturamalla__malla__carrera=carrera, retiramateria=False, materia__status=True, matricula__inscripcion__persona__real=True, status=True)
        aprobado1ramatricula = MateriaAsignada.objects.values_list('matricula__inscripcion__persona', flat=True).filter(filtrobase & Q(materia__cerrado=True, matriculas=1, materia__nivel__periodo__in=periodos, estado=1)).order_by('matricula__inscripcion__persona__cedula').distinct('matricula__inscripcion__persona__cedula').count()
        aprobado2damatricula = MateriaAsignada.objects.values_list('matricula__inscripcion__persona', flat=True).filter(filtrobase & Q(materia__cerrado=True, matriculas=2, materia__nivel__periodo__in=periodos, estado=1)).order_by('matricula__inscripcion__persona__cedula').distinct('matricula__inscripcion__persona__cedula').count()
        einiciaronnivelacion = MateriaAsignada.objects.values_list('matricula__inscripcion__persona', flat=True).filter(filtrobase & Q(materia__nivel__periodo__in=periodos)).order_by('matricula__inscripcion__persona__cedula').distinct('matricula__inscripcion__persona__cedula').count()

        filtrcount = Q(materia__asignaturamalla__malla__carrera__coordinacion__in=[1,2,3,4,5], retiramateria=False, materia__status=True, matricula__inscripcion__persona__real=True, materia__nivel__periodo=periodo, status=True)
        countestudianteunemi = MateriaAsignada.objects.values_list('matricula__inscripcion__persona', flat=True).filter(filtrcount).exclude(matricula__inscripcion__graduado__estadograduado=True).exclude(matricula__inscripcion__graduado__status=True).distinct('matricula__inscripcion__persona').count()
        
        porcentajetotal, p, w,  = 0, 100, 1
        a, b, c = aprobado1ramatricula, aprobado2damatricula, einiciaronnivelacion

        if countestudianteunemi <= 2875:
            p = 72.1306
        elif 2876 <= countestudianteunemi <= 7176:
            p = 80.3708
        elif 7177 <= countestudianteunemi <= 36487:
            p = 94.3268
        try:
            p = p / 100
            porcentajetotal = truncar_a_n_digitos(((a + b)/c) * 100 * p * w, 4)
        except ZeroDivisionError as ex:
            pass

        puntuacion = 1
        try:
            x1, x2, y1, y2 = 29.61, 76.73, 0, 1
            pendiente = (y2 - y1) / ((x2 / 100) - (x1 / 100))
            if x1 <= porcentajetotal < x2:
                puntuacion = truncar_a_n_digitos(pendiente * ((porcentajetotal / 100) - (x1 / 100)), 4)
            elif porcentajetotal < x1:
                puntuacion = 0
        except Exception as ex:
            pass

        columnas = [(f"NE.Ap.1Mat", aprobado1ramatricula),
                    (f"NE.Ap.2Mat", aprobado2damatricula),
                    (f"NE.Inc.Niv", einiciaronnivelacion),
                    (f"p", p), (f"w", w),
                    (f"Ef.Niv.", porcentajetotal)]

        coordinacion, decanofacultad = carrera.coordinacion_carrera(), None
        if configuracionmatricula := MatriculacionPrimerNivelCarrera.objects.filter(configuracion__periodopregrado=periodo, carreraadmision=carrera, status=True).first():
            carreragrado = configuracionmatricula.carrerapregrado
            coordinacion = carreragrado.coordinacion_carrera()
            if decano := periodo.responsablecoordinacion_set.filter(coordinacion=carreragrado.coordinacion_carrera(), tipo=1, status=True).first():
                decanofacultad = decano.persona

        data['persona'] = persona
        data['carrera'] = carrera
        data['ejecucion'] = columnas
        data['puntuacion'] = puntuacion
        data['formula'] = get_formula_img(1)
        data['decanofacultad'] = decanofacultad
        data['nombreperiodos'] = nombreperiodos
        data['porcentajetotal'] = porcentajetotal
        data['coordinacion'] = coordinacion
        return data
    except Exception as ex:
        print(ex.__str__())


def reporte_permanencia_carrera(**kwargs):
    try:
        from io import BytesIO
        import matplotlib.pyplot as plt
        from sga.models import Matricula, Credo, Periodo, Matricula
        data = {}
        carreras = kwargs.pop('carreras')
        tiporeporte = kwargs.pop('tiporeporte')
        periodo_actual = kwargs.pop('periodo')

        periodo_actual = Periodo.objects.get(id=periodo_actual)
        periodo_pasado = get_periodo_pasado(carreras, periodo_actual)

        periodo_historico_actual = periodo_pasado
        periodo_historico_pasado = get_periodo_pasado(carreras, periodo_historico_actual)

        null4default = False
        resultados_ghe = []
        img_analisiscomparativo = ''
        filtrobasematricula = Q(inscripcion__carrera__in=carreras, status=True)
        if tiporeporte == 3:
            personaghe = []
            discapacidad, beneficiariasbono, enfermedadcatastrofica = [], [], []
            religion, migrante, etnia, socioeco, ruralidad, vulnerabilidad = [], [], [], [], [], []
            for matricula in Matricula.objects.filter(Q(nivel__periodo=periodo_pasado, nivelmalla__orden=1), filtrobasematricula).order_by('inscripcion_id').distinct('inscripcion_id'):
                persona = matricula.inscripcion.persona
                tienevulnerabilidad = False
                __migrante1 = persona.migrantepersona_set.filter(verificado=True, status=True).first()
                __migrante2 = persona.paisnacimiento and persona.pais and persona.paisnacimiento.pk == 1 and not persona.pais.pk == 1
                try:
                    if __discapacidad := persona.perfilinscripcion_set.filter(tienediscapacidad=True, porcientodiscapacidad__gte=30, verificadiscapacidad=True, status=True).first():
                        # Personas con discapacidad con un porcentaje mínimo del 30% debidamente calificado por el órgano competente
                        discapacidad.append((__discapacidad.tipodiscapacidad, persona))
                        tienevulnerabilidad = True
                    elif null4default:
                        # Personas cuidadoras y beneficiarias del Bono Joaquín Gallegos Lara que consten en los registros administrativos del Ministerio de Inclusión Económica y Social
                        beneficiariasbono.append(('Bono Joaquín Gallegos Lara', persona))
                        tienevulnerabilidad = True
                    elif null4default:
                        # Víctimas de violencia sexual o de género con la denuncia presentada ante la autoridad competente
                        tienevulnerabilidad = True
                    elif __migrante1 or __migrante2:
                        # Personas ecuatorianas residentes en el exterior o migrantes retornados con la certificación de la instancia competente
                        if __migrante1:
                            migrante.append((__migrante1.paisresidencia, persona))
                            personaghe.append(persona.pk)
                        else:
                            migrante.append((persona.pais, persona))
                            personaghe.append(persona.pk)
                        tienevulnerabilidad = True
                    elif null4default:
                        # Hijas e hijos de las víctimas de femicidio, esta información será verificada a partir de los datos
                        # proporcionados por la autoridad competente
                        tienevulnerabilidad = True
                    elif null4default:
                        # Personas que adolezcan de enfermedades catastróficas o de alta complejidad, que consten en los
                        # registros del organismo rector de la política de salud pública
                        tienevulnerabilidad = True
                    elif null4default:
                        # Personas que en alguna etapa de su niñez o adolescencia fueron ingresadas en una unidad de
                        # atención de acogimiento institucional como medida de protección, emitida por la autoridad competente
                        tienevulnerabilidad = True
                except Exception as ex:
                    ...

                pueblosnacionalidades1 = persona.perfilinscripcion_set.filter(estadoarchivoraza=2, nacionalidadindigena__status=True, status=True).first()
                pueblosnacionalidades2 = persona.perfilinscripcion_set.filter(estadoarchivoraza=2, raza=1, status=True).first()

                if __grupoecon := persona.fichasocioeconomicainec_set.filter(grupoeconomico=5, grupoeconomico__status=True, status=True).first(): # Grupo socioeconómico
                    socioeco.append((__grupoecon.grupoeconomico.nombre, persona))
                    personaghe.append(persona.pk)
                elif persona.sectorlugar == 2 or persona.zona == 2: # Ruralidad
                    ruralidad.append((f"{persona.direccion_completa()}", persona))
                    personaghe.append(persona.pk)
                elif null4default: # Territorialidad
                    continue
                elif tienevulnerabilidad: #  Condiciones de vulnerabilidad
                    personaghe.append(persona.pk)
                elif pueblosnacionalidades1 or pueblosnacionalidades2: # Pueblos y nacionalidades
                    if pueblosnacionalidades1:
                        etnia.append((pueblosnacionalidades1.nacionalidadindigena, persona))
                    else:
                        etnia.append((pueblosnacionalidades2.raza, persona))
                    personaghe.append(persona.pk)
                elif null4default: # Primera Generación: personas aspirantes que forman parte de la primera generación dentro de sus hogares en aspirar a una carrera de tercer nivel.
                    continue

            filtrobasematricula &= Q(inscripcion__persona__in=personaghe)

            resultados_ghe.append({'orden': 1, 'indicador': 'Condición socio económica', 'data': socioeco})
            resultados_ghe.append({'orden': 2, 'indicador': 'Ruralidad', 'data': ruralidad})
            resultados_ghe.append({'orden': 3, 'indicador': 'Territorialidad', 'data': []})
            resultados_ghe.append({'orden': 4, 'indicador': 'Condiciones de vulnerabilidad', 'data': [{'indicador': 'Personas con discapacidad con un porcentaje mínimo del 30%', 'data': discapacidad}, {'indicador': 'Personas ecuatorianas residentes en el exterior o migrantes retornados', 'data': migrante}, {'indicador': 'Personas que adolezcan de enfermedades catastróficas o de alta complejidad', 'data': enfermedadcatastrofica}]})
            resultados_ghe.append({'orden': 5, 'indicador': 'Pueblos y nacionalidades', 'data': etnia})
            resultados_ghe.append({'orden': 6, 'indicador': 'Primera generación', 'data': []})

            labels, sizes = [], []
            for r in resultados_ghe:
                labels.append(r['indicador'])
                if not r['orden'] == 4:
                    sizes.append(len(r['data']))
                else:
                    values = 0
                    for d in r['data']:
                        values += len(d['data'])
                    sizes.append(values)

            colors = ['#ff9999','#66b3ff','#99ff99','#ffcc99', '#c2c2f0', '#ffb3e6']
            plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90, pctdistance=0.85)
            plt.axis('equal')
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=600, bbox_inches='tight', transparent=True)
            buf.seek(0)
            data['img_distribucionpoblacion'] = base64.b64encode(buf.getvalue()).decode('utf-8')
            buf.close()
            plt.close()

        columnas = []
        for pactual, ppasado in [(periodo_actual, periodo_pasado), (periodo_historico_actual, periodo_historico_pasado)]:
            matriculadossemestreanterior = Matricula.objects.values_list('inscripcion').filter(Q(nivel__periodo=ppasado, nivelmalla__orden=1), filtrobasematricula).distinct()
            matriculadossemestreencursoo = Matricula.objects.values_list('inscripcion').filter(Q(nivel__periodo=pactual, inscripcion__in=matriculadossemestreanterior), filtrobasematricula).distinct().count()
            matriculadossemestreanterior = matriculadossemestreanterior.count()

            try:
                porcentaje = (matriculadossemestreencursoo/matriculadossemestreanterior) * 100
            except ZeroDivisionError as ex:
                porcentaje = 0

            porcentaje = truncar_a_n_digitos(porcentaje, 2)
            columnas.append([('M.Sem.Ant', f'Número de estudiantes matriculados en la carrera que iniciaron el primer nivel el semestre anterior ({ppasado.nombre})'.capitalize(), matriculadossemestreanterior),
                             ('M.Sem.Cur', f'Número de estudiantes matriculados en la carrera que iniciaron el primer nivel el semestre anterior ({ppasado.nombre}) y se mantienen matriculados en el semestre en curso ({pactual.nombre})'.capitalize(), matriculadossemestreencursoo),
                             ('Per.Carr', 'Permanencia de estudiantes en la carrera', porcentaje)])

        if len(columnas) == 2:
            aclabels = [f'Per.Carr. ({periodo_actual.inicio.year - 1})', f'Per.Carr. ({periodo_actual.inicio.year})']
            acvalues, color = [columnas[0][2][2], columnas[1][2][2]], ['gray', 'blue']

            acvalues[0] > acvalues[1] and color.sort(reverse=False)

            plt.figure(figsize=(6, 1.5))
            plt.barh(aclabels, acvalues, color=color, height=0.25)

            plt.title(f'Análisis comparativo de variables: año {periodo_actual.inicio.year} vs año {periodo_actual.inicio.year - 1}', fontsize=9)

            for i, value in enumerate(acvalues):
                plt.text(value + 1, i, f'{value}%', va='center', fontsize=7)

            plt.xlim(0, 100)
            plt.xticks(fontsize=7)
            plt.yticks(ticks=[0.02, 1 - 0.02], labels=aclabels, fontsize=7)

            for spine in plt.gca().spines.values():
                spine.set_linewidth(0.5)

            texto_descriptivo = "*Se muestra el analisis por año en funcion del periodo seleccionado"
            plt.figtext(0.5, -0.1, texto_descriptivo, wrap=True, horizontalalignment='center', fontsize=6)

            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=600, bbox_inches='tight', transparent=True)
            buffer.seek(0)
            img_analisiscomparativo = base64.b64encode(buffer.read()).decode('utf-8')
            plt.close()
            buffer.close()

        data['porcentaje'] = porcentaje
        data['resultados_ghe'] = resultados_ghe
        data['ejecucion'] = columnas[0] if columnas else []
        data['img_analisiscomparativo'] = img_analisiscomparativo
        data['matriculadossemestreanterior'] = matriculadossemestreanterior
        data['matriculadossemestreencursoo'] = matriculadossemestreencursoo

        return data
    except Exception as ex:
        print(str(ex))


def get_periodo_pasado(carreras, periodo_actual):
    try:
        periodo_pasado = 0
        filtroperiodopasado = Q(tipo=2, clasificacion=1, status=True)
        if periodo_actual.inicio.month > 7:
            periodo2s = True
            filtroperiodopasado &= Q(inicio__year=periodo_actual.inicio.year, inicio__month__lte=7)
        else:
            periodo1s = True
            filtroperiodopasado &= Q(inicio__year=periodo_actual.inicio.year - 1, inicio__month__gte=7)
        matriculadosperiodo = 0
        lista_periodos_pasados = Periodo.objects.filter(filtroperiodopasado).exclude(nombre__icontains='PLAN').exclude(nombre__icontains='REM').exclude(nombre__icontains='PRU').order_by('inicio')
        for periodo in lista_periodos_pasados:
            nuevobancomatriculados = MateriaAsignada.objects.filter(materia__nivel__periodo=periodo, matricula__inscripcion__carrera__in=carreras).values('matricula__inscripcion').distinct('matricula__inscripcion').count()
            if matriculadosperiodo < nuevobancomatriculados:
                matriculadosperiodo, periodo_pasado = nuevobancomatriculados, periodo
        return periodo_pasado
    except Exception as ex:
        pass


def get_formula_img(tiporeporte):
    try:
        from io import BytesIO
        _image, img64 = BytesIO(), 0
        if tiporeporte == 1:
            plt.figure(figsize=(3, 1))
            plt.text(0.5, 0.5, r"$\mathrm{Ef. Niv.} = \frac{NE. Ap. 1\ Mat + NE. Ap. 2\ Mat}{NE. Inc. Niv} \times 100 \times \rho \times \omega$", fontsize=12, ha='center', va='center')
            plt.axis('off')
            plt.savefig(_image, format='png', dpi=600, bbox_inches='tight', transparent=True)
            plt.close()
            _image.seek(0)
            img64 = base64.b64encode(_image.read()).decode('utf-8')
        elif tiporeporte == 2:
            plt.figure(figsize=(3, 1))
            plt.text(0.5, 0.5, r"$\mathrm{Per. Carr.} = \frac{NE. Ap. 1\ Mat + NE. Ap. 2\ Mat}{NE. Inc. Niv} \times 100 \times \rho \times \omega$", fontsize=12, ha='center', va='center')
            plt.axis('off')
            plt.savefig(_image, format='png', dpi=600, bbox_inches='tight', transparent=True)
            plt.close()
            _image.seek(0)
            img64 = base64.b64encode(_image.read()).decode('utf-8')
        elif tiporeporte == 3:
            plt.figure(figsize=(3, 1))
            plt.text(0.5, 0.5, r"$\mathrm{Per. Carr. (GHE)} = \frac{NE. Ap. 1\ Mat + NE. Ap. 2\ Mat}{NE. Inc. Niv} \times 100 \times \rho \times \omega$", fontsize=12, ha='center', va='center')
            plt.axis('off')
            plt.savefig(_image, format='png', dpi=600, bbox_inches='tight', transparent=True)
            plt.close()
            _image.seek(0)
            img64 = base64.b64encode(_image.read()).decode('utf-8')

        _image.close()
        return img64
    except Exception as ex:
        pass


def get_funcion_utilidad(x_vertical):
    try:
        x = np.linspace(0, 100, 400)
        y = np.piecewise(
            x,
            [x <= 29.61, (x > 29.61) & (x < 76.73), x >= 76.73],
            [0, lambda x: (x - 29.61) / (76.73 - 29.61), 1]
        )

        y_vertical = np.interp(x_vertical, x, y)
        plt.figure(figsize=(8, 6))
        plt.plot(x, y, label=f'y = {y_vertical:.2f}')
        plt.axvline(x=x_vertical, color='red', linestyle='--', label=f'x = {x_vertical}')
        plt.text(x_vertical, y_vertical, f'({x_vertical}, {y_vertical:.4f})', color='blue', fontsize=12, ha='right')

        plt.title('Gráfica de la función de utilidad')
        plt.legend()
        plt.grid(True)

        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=600, bbox_inches='tight', transparent=True)
        buf.seek(0)

        image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        buf.close()
        plt.close()
        return image_base64
    except Exception as ex:
        pass


def truncar_a_n_digitos(val, n):
    return math.trunc(val * (10**n)) / (10**n)


def get_periodos_validos(**kwargs):
    try:
        from sga.models import MESES_CHOICES
        tipoinforme, anio, periodo, persona = kwargs.pop('tipoinforme'), kwargs.pop('anio'), kwargs.pop('periodo'), kwargs.pop('persona')
        coordinaciones = [9] if tipoinforme == 1 else [1,2,3,4,5]
        filtrobasemateria = Q(materia__nivel__periodo__inicio__year=anio, materia__asignaturamalla__asignatura__modulo=False, status=True)
        if cc := periodo.coordinadorcarrera_set.filter(carrera__coordinacion__in=coordinaciones, persona=persona, tipo=3, status=True).first():
            filtrobasemateria &= Q(materia__asignaturamalla__malla__carrera=cc.carrera)
        periodosofertaacademica = MateriaAsignada.objects.filter(filtrobasemateria).values_list('materia__nivel__periodo', flat=True).distinct()
        filtromeses = Q(nombre__icontains=MESES_CHOICES[0][1].upper())
        for mes in MESES_CHOICES[1:]:
            filtromeses |= Q(nombre__icontains=mes[1].upper())
        return Periodo.objects.filter(Q(id__in=periodosofertaacademica) & filtromeses).exclude(id__in=[258]).exclude(nombre__icontains='REME').order_by('inicio')
    except Exception as ex:
        pass