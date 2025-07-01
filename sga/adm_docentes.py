# -*- coding: latin-1 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction, connections
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from settings import FICHA_MEDICA_ESTRICTA, MATRICULACION_LIBRE, USA_PLANIFICACION, ABRIR_CLASES_ATRASADAS, \
    CANTIDAD_HORAS_JUSTIFICACION_ASISTENCIAS, LIMITE_HORAS_JUSTIFICAR
from sga.commonviews import adduserdata, obtener_reporte, \
    justificar_asistencia, actualizar_asistencia
from sga.forms import CambiarProfesorForm
from sga.funciones import MiPaginador, log, convertir_fecha, puede_modificar_profesor, variable_valor, puede_realizar_accion
from django.template import Context
from django.template.loader import get_template
from sga.models import Profesor, LeccionGrupo, AsistenciaLeccion, Turno, Aula, Clase, Leccion, Sesion, Materia, \
    MateriaAsignada, \
    TipoIncidencia, Incidencia, Archivo, ProfesorMateria, Coordinacion, EvidenciaActividadDetalleDistributivo, \
    ProfesorDistributivoHoras, ComplexivoClase, TipoProfesor, TemaAsistencia, SubTemaAdicionalAsistencia, \
    SubTemaAsistencia, ClaseAsincronica, ClaseSincronica
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.templatetags.sga_extras import encrypt
import json

unicode =str
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
    miscarreras = persona.mis_carreras()
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'asistencia':
            try:
                asistencialeccion = AsistenciaLeccion.objects.get(pk=request.POST['id'])
                if not request.user.is_superuser:
                    if LIMITE_HORAS_JUSTIFICAR:
                        horas_extras = CANTIDAD_HORAS_JUSTIFICACION_ASISTENCIAS
                        if asistencialeccion.leccion.leccion_grupo().dia in [5, 6, 7] and CANTIDAD_HORAS_JUSTIFICACION_ASISTENCIAS < 72:
                            horas_extras += 48
                        # if asistencialeccion.leccion.fecha < datetime.now().date() - timedelta(hours=horas_extras):
                        #     return JsonResponse({"result": "bad", "mensaje": u"Las faltas menores a " + str(horas_extras) + " horas no pueden ser justificadas."})
                result = justificar_asistencia(request)
                result['materiaasignada'] = None
                return JsonResponse(result)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'pdfacta':
            try:
                data = {}
                data['materia'] = Materia.objects.get(pk=request.POST['idmateria'])
                data['profesor'] = Profesor.objects.get(pk=request.POST['iddocente'])
                return conviert_html_to_pdf(
                    'adm_docentes/pdf_acta.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as ex:
                pass

        if action == 'asistenciaclase':
            try:
                result = actualizar_asistencia(request)
                result['materiaasignada'] = None
                return JsonResponse(result)
            except Exception as ex:
                return JsonResponse({"result": "bad"})

        elif action == 'deleteclase':
            try:
                lecciongrupo = LeccionGrupo.objects.get(pk=request.POST['id'])
                materiasasignadas = MateriaAsignada.objects.filter(id__in=[x.materiaasignada.id for x in AsistenciaLeccion.objects.filter(leccion__lecciongrupo=lecciongrupo).distinct()])
                log(u'Elimino leccion: %s' % lecciongrupo, request, "del")
                todaslecciones = lecciongrupo.lecciones.all()
                for lecciones in todaslecciones:
                    materia = lecciones.clase.materia
                    lecciones.delete()
                    for materiaasignada in materia.materiaasignada_set.all():
                        materiaasignada.actualiza_notafinal()
                lecciongrupo.delete()
                for maa in materiasasignadas:
                    maa.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'asistenciageneral':
            try:
                leccion = Leccion.objects.get(pk=int(request.POST['id']))
                # for leccion in lecciongrupo.lecciones.all():
                for asistencia in leccion.asistencialeccion_set.all():
                    if asistencia.puede_tomar_asistencia():
                        asistencia.asistio = True
                    else:
                        asistencia.asistio = False
                    asistencia.save(request)
                    asistencia.materiaasignada.save(actualiza=True)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad"})

        if action == 'cambiardocente':
            mensaje = u"No se pudo ejecutar el proceso de cambio de docentes."
            try:
                nombrematerias = ""
                distributivo = ProfesorDistributivoHoras.objects.get(id=int(encrypt(request.POST['id'])), periodo = periodo)
                profesor = Profesor.objects.get(id=int(request.POST['idp']))
                # CAMBIO DE PROFESOR EN LAS MATERIAS DADAS PROFESORMATERIA
                for profesormateria in ProfesorMateria.objects.filter(profesor = distributivo.profesor, materia__nivel__periodo=periodo):
                    profemate = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__periodo=periodo, materia = profesormateria.materia, tipoprofesor = profesormateria.tipoprofesor)
                    if profemate.exists():
                        mensaje = u"Ya se encuentra el profesor "+profesor.persona.nombre_completo_inverso() + " en la materia " + profemate[0].materia.__str__() + " con tipo profesor " + profemate[0].tipoprofesor.__str__()
                        raise NameError('Error')
                    # elif profemate.filter(activo=False).exists():
                    #     profemate = profemate[0]
                    #     profemate.activo = True
                    else:
                        profesormateria.profesor = profesor
                        profesormateria.save(request)
                        nombrematerias += u'(%s - %s - %s - %s a %s - %s), '%(profesormateria.materia.nombre_mostrar_solo(), profesormateria.hora, profesormateria.materia.nombre_mostrar_solo(), profesormateria.desde.strftime('%d-%m-%Y'), profesormateria.hasta.strftime('%d-%m-%Y'), profesormateria.materia.nivel.periodo)
                profesoractual = distributivo.profesor
                if not ProfesorDistributivoHoras.objects.values('id').filter(profesor=profesor, periodo = periodo).exists():
                    distributivo.profesor = profesor
                    distributivo.save(request)
                listamensaje = []
                existeconflicto = False
                json_content = None
                contarclasesconflicto = 0
                contarclasessinconflicto = 0
                for clase in Clase.objects.filter(profesor = profesoractual, materia__nivel__periodo=periodo):
                    verificar_conflito_docente = profesor.existe_conflicto_docente(periodo, clase.materia, clase.tipoprofesor, clase.inicio, clase.fin, clase.dia, clase.turno)
                    if verificar_conflito_docente[0]:
                        listamensaje.append(verificar_conflito_docente)
                        existeconflicto = True
                        contarclasesconflicto += 1
                        clase.profesor = None
                        clase.save(request)
                    else:
                        contarclasessinconflicto += 1
                        clase.profesor = profesor
                        clase.save(request)
                        log(u'Cambio de docente en la clase: %s[%s] - profesor que se va asignar:%s[%s] - profesor anterior:%s[%s]' % (clase, clase.id, profesor, profesor.id, profesoractual, profesoractual.id), request, "edit")
                if existeconflicto:
                    data['mensajes'] = listamensaje
                    data['contarclasesconflicto'] = contarclasesconflicto.__str__()
                    data['clasesafectadas'] = contarclasessinconflicto.__str__()
                    template = get_template("niveles/mensajeconflicto.html")
                    json_content = template.render(data)
                for tipoprofesor in TipoProfesor.objects.filter(status=True):
                    profesoractual.actualizar_distributivo_horas(request, periodo, tipoprofesor.id)
                    profesor.actualizar_distributivo_horas(request, periodo, tipoprofesor.id)
                if periodo.fechadesdenotificacion:
                    if periodo.fechadesdenotificacion <= datetime.now().date():
                        descripcion = u'Se cambio de profesor: %s en las materias: [%s] al profesor: %s en el periodo de %s' % (profesoractual.persona.nombre_completo_inverso(), nombrematerias, distributivo.profesor.persona.nombre_completo_inverso(), distributivo.periodo)
                        profesor.mail_notificar_procesoevaluacion(request.session['nombresistema'], descripcion, persona, periodo)
                log(u"Ejecuto proceso cambio de profesor en el modulo clases y evaluaciones: idDocenteDistributivoHoras (%s) - profesor actual (%s) - profesor q reemplaza (%s) - periodo (%s) fue afectado en profesormateria, en clase y en profesordistributivohoras" % (distributivo.id, profesoractual, profesor, periodo), request, "add")
                return JsonResponse({"result": "ok", "existeconflicto": existeconflicto, 'segmento': json_content, "clasesafectadas": contarclasessinconflicto.__str__()})
            except Exception as ex:
                import sys
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": mensaje})

        if action == 'nuevaleccion':
            try:
                clases = Clase.objects.filter(id__in=[int(x) for x in request.POST['clases'].split(',')])
                profesor = Profesor.objects.get(pk=request.POST['pid'])
                turno = Turno.objects.get(pk=clases[0].turno.id)
                aula = Aula.objects.get(pk=clases[0].aula.id)
                motivoapertura = request.POST['motivo']
                fecha = convertir_fecha(request.POST['fecha'])
                for clase in clases:
                    if fecha > clase.fin or fecha < clase.inicio:
                        return JsonResponse({"result": "bad", "mensaje": u"No puede abrir una clase con fecha diferente al horario."})
                dia = clases[0].dia
                ids = []
                if ABRIR_CLASES_ATRASADAS:
                    enhora = False
                    if (fecha < datetime.now().date()) or (fecha == datetime.now().date() and turno.comienza < datetime.now().time() < turno.termina) or (fecha == datetime.now().date() and turno.termina < datetime.now().time()):
                        enhora = fecha == datetime.now().date() and turno.comienza < datetime.now().time() < turno.termina
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"No puede abrir clases de fechas y horas futuras."})
                    if enhora:
                        if LeccionGrupo.objects.filter(profesor=profesor, abierta=True).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Ya existe una clase abierta para ese profesor."})
                else:
                    if (fecha < datetime.now().date()) or (fecha == datetime.now().date() and turno.termina < datetime.now().time()):
                        pass
                    # else:
                    #     return JsonResponse({"result": "bad", "mensaje": u"No puede abrir clases de fechas y horas futuras o en curso."})
                grupoleccion = LeccionGrupo.objects.filter(profesor=profesor, turno=turno, fecha=fecha)
                lecciongrupo = None
                if grupoleccion.exists():
                    if grupoleccion[0].mis_leciones().filter(clase__id__in=clases.values_list('id')).values('id').exists():
                        return JsonResponse({"result": "bad","mensaje": u"Ya existe una clase registrada para esa fecha en ese turno."})
                    if grupoleccion[0].verificar_profemate_novalidahor(clases):
                        lecciongrupo = grupoleccion[0]
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe una clase registrada para esa fecha en ese turno."})
                if lecciongrupo:
                    lecciongrupo.motivoapertura=motivoapertura
                    lecciongrupo.origen_coordinador=True
                    lecciongrupo.automatica=False
                    lecciongrupo.solicitada=False
                    lecciongrupo.abierta=True if turno.comienza <= datetime.now().time() <= turno.termina and ABRIR_CLASES_ATRASADAS else False
                else:
                    lecciongrupo = LeccionGrupo(profesor=profesor,
                                                turno=turno,
                                                aula=aula,
                                                dia=dia,
                                                fecha=fecha,
                                                horaentrada=turno.comienza,
                                                horasalida=turno.termina,
                                                abierta=True if turno.comienza <= datetime.now().time() <= turno.termina and ABRIR_CLASES_ATRASADAS else False,
                                                contenido='SIN CONTENIDO',
                                                estrategiasmetodologicas='SIN CONTENIDO',
                                                observaciones='SIN OBSERVACIONES',
                                                origen_coordinador=True,
                                                motivoapertura=motivoapertura)
                lecciongrupo.save(request)
                for clase in clases:
                    leccion = Leccion(clase=clase,
                                      fecha=lecciongrupo.fecha,
                                      horaentrada=lecciongrupo.horaentrada,
                                      horasalida=lecciongrupo.horasalida,
                                      abierta=True if turno.comienza <= datetime.now().time() <= turno.termina and ABRIR_CLASES_ATRASADAS else False,
                                      contenido=lecciongrupo.contenido,
                                      estrategiasmetodologicas=lecciongrupo.estrategiasmetodologicas,
                                      observaciones=lecciongrupo.observaciones,
                                      origen_coordinador=True,
                                      motivoapertura=motivoapertura)
                    leccion.save(request)
                    lecciongrupo.lecciones.add(leccion)
                    materia = clase.materia
                    asignadas = materia.materiaasignada_set.filter(matricula__estado_matricula__in=[2,3])
                    for asignada in asignadas:
                        asistencialeccion = AsistenciaLeccion(leccion=leccion,
                                                              materiaasignada=asignada,
                                                              asistio=False)
                        asistencialeccion.save(request)
                        materiaasignada = asistencialeccion.materiaasignada
                        materiaasignada.save(actualiza=True)
                        materiaasignada.actualiza_estado()
                    ids.append(encrypt(leccion.id))
                lecciongrupo.save(request)
                log(u"Adiciono clase: %s" % lecciongrupo, request, "add")
                return JsonResponse({"result": "ok", "lg": lecciongrupo.id, "listal":ids})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad"})

        if action == 'listar_clases':
            try:
                if 'fecha' in request.POST:
                    fecha= convertir_fecha(request.POST['fecha'])
                    clases = Clase.objects.filter(activo=True, inicio__lte=fecha, fin__gte=fecha, dia=(fecha.weekday() + 1), status=True, materia__nivel__periodo_id=periodo.id)
                    lista = []
                    for cl in clases:
                        clase= {'materia': unicode(str(cl.materia.asignaturamalla.asignatura.nombre)+' '+str(cl.turno)),'id': cl.id}
                        lista.append(clase)
                    return JsonResponse({"result": "ok", "lista": lista})
            except Exception as ex:
                return JsonResponse({"result": "bad"})

        if action == 'recalcular_asistencia':
            try:
                if 'fecha' in request.POST:
                    fecha= convertir_fecha(request.POST['fecha'])
                    # for cl in Clase.objects.filter(activo=True, inicio__lte=fecha, fin__gte=fecha, dia=(fecha.weekday() + 1), status=True, materia__nivel__periodo_id=14):
                    cl = Clase.objects.filter(activo=True, id=int(request.POST['id']), status=True,materia__nivel__periodo_id=periodo.id)[0]
                    if cl.materia.profesor_principal():
                        if LeccionGrupo.objects.filter(profesor=cl.materia.profesor_principal(), turno=cl.turno, fecha=fecha).exists():
                            lecciongrupo = LeccionGrupo.objects.get(profesor=cl.materia.profesor_principal(), turno=cl.turno, fecha=fecha)
                        else:
                            lecciongrupo = LeccionGrupo(profesor=cl.materia.profesor_principal(),
                                                        turno=cl.turno,
                                                        aula=cl.aula,
                                                        dia=cl.dia,
                                                        fecha=fecha,
                                                        horaentrada=cl.turno.comienza,
                                                        horasalida=cl.turno.termina,
                                                        abierta=False,
                                                        automatica=True,
                                                        contenido='REGISTRO MASIVO 2018',
                                                        observaciones='REGISTRO MASIVO 2018')
                            lecciongrupo.save()
                        if Leccion.objects.filter(clase=cl, fecha=fecha).exists():
                            leccion = Leccion.objects.get(clase=cl, fecha=fecha)
                        else:
                            leccion = Leccion(clase=cl,
                                              fecha=fecha,
                                              horaentrada=cl.turno.comienza,
                                              horasalida=cl.turno.termina,
                                              abierta=True,
                                              automatica=True,
                                              aperturaleccion=True,
                                              contenido=lecciongrupo.contenido,
                                              observaciones=lecciongrupo.observaciones)
                            leccion.save()
                        if not lecciongrupo.lecciones.filter(pk=leccion.id).exists():
                            lecciongrupo.lecciones.add(leccion)
                        if AsistenciaLeccion.objects.filter(leccion=leccion).exists():
                            for asis in AsistenciaLeccion.objects.filter(leccion=leccion):
                                if not asis.asistio:
                                    asis.asistio = True
                                    asis.save()
                                    mateasig = asis.materiaasignada
                                    mateasig.save(actualiza=True)
                                    mateasig.actualiza_estado()
                        else:
                            for materiaasignada in cl.materia.asignados_a_esta_materia():
                                if not AsistenciaLeccion.objects.filter(leccion=leccion,  materiaasignada=materiaasignada).exists():
                                    asistencialeccion = AsistenciaLeccion(leccion=leccion,
                                                                          materiaasignada=materiaasignada,
                                                                          asistio=True)
                                    asistencialeccion.save()
                                    materiaasignada.save(actualiza=True)
                                    materiaasignada.actualiza_estado()
                                    # guardar temas de silabo

                        lecciongrupo.save()
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "ok"})
                        # print(cl)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad"})

        elif action == 'selecttema':
            try:
                lista = []
                leccion = Leccion.objects.get(pk=int(request.POST['idl']))
                materia = leccion.clase.materia
                leccion_id = leccion.id
                if not TemaAsistencia.objects.filter(leccion_id=leccion_id, tema_id=request.POST['idt']).exists():
                    tema = TemaAsistencia(leccion_id=leccion_id, tema_id=request.POST['idt'],
                                          fecha=datetime.now().date())
                    tema.save(request)
                    log(u'Seleccionó tema de la planificacion: %s' % tema, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    tema = TemaAsistencia.objects.get(leccion_id=leccion_id, tema_id=int(request.POST['idt']))
                    if tema.subtemaasistencia_set.filter(status=True).exists():
                        for s in tema.subtemaasistencia_set.all():
                            lista.append([s.subtema.id])
                        subtema = tema.subtemaasistencia_set.all()
                        subtema.delete()
                    log(u'Eliminar tema  de la planificación: %s' % tema, request, "del")
                    tema.delete()
                    return JsonResponse({"result": "ok", 'lista': lista})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error los temas. %s" % ex})

        elif action == 'selectsubtema':
            try:
                stema = 0
                leccion = Leccion.objects.get(pk=int(request.POST['idl']))
                materia = leccion.clase.materia
                leccion_id = leccion.id
                if not TemaAsistencia.objects.filter(leccion_id=leccion_id, tema_id=request.POST['idt']).exists():
                    tema = TemaAsistencia(leccion_id=leccion_id, tema_id=request.POST['idt'],
                                          fecha=datetime.now().date())
                    tema.save(request)
                    log(u'Seleccionó tema de la planificacion: %s' % tema, request, "add")
                    stema = tema.tema.id
                    sub = SubTemaAsistencia(tema_id=tema.id, subtema_id=request.POST['ids'],
                                            fecha=datetime.now().date())
                    sub.save(request)
                    log(u'Seleccionó subtema de la planificacion: %s' % sub, request, "add")
                else:
                    tema = TemaAsistencia.objects.get(leccion_id=leccion_id, tema_id=int(request.POST['idt']))
                    if not tema.subtemaasistencia_set.filter(subtema_id=int(request.POST['ids'])).exists():
                        sub = SubTemaAsistencia(tema_id=tema.id, subtema_id=request.POST['ids'],
                                                fecha=datetime.now().date())
                        sub.save(request)
                        log(u'Seleccionó subtema de la planificacion: %s' % sub, request, "add")
                    else:
                        sub = SubTemaAsistencia.objects.get(tema_id=tema.id, subtema_id=request.POST['ids'])
                        log(u'Eliminó subtema de la planificacion: %s' % sub, request, "add")
                        sub.delete()
                return JsonResponse({"result": "ok", 'tem': stema})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los temas."})

        elif action == 'selectsubtemaadicional':
            try:
                stema = 0
                leccion = Leccion.objects.get(pk=int(request.POST['idl']))
                materia = leccion.clase.materia
                leccion_id = leccion.id
                if not TemaAsistencia.objects.filter(leccion_id=leccion_id, tema_id=request.POST['idt']).exists():
                    tema = TemaAsistencia(leccion_id=leccion_id, tema_id=request.POST['idt'],
                                          fecha=datetime.now().date())
                    tema.save(request)
                    log(u'Seleccionó tema de la planificacion: %s' % tema, request, "add")
                    # stema= tema.tema.id
                    suba = SubTemaAdicionalAsistencia(tema=tema, subtema_id=int(request.POST['ids']),
                                                      fecha=datetime.now().date())
                    suba.save(request)
                    log(u'Seleccionó subtema de la planificacion: %s' % suba, request, "add")
                else:
                    tema = TemaAsistencia.objects.get(leccion_id=leccion_id, tema_id=int(request.POST['idt']))
                    if not tema.subtemaadicionalasistencia_set.filter(subtema_id=int(request.POST['ids'])).exists():
                        suba = SubTemaAdicionalAsistencia(tema_id=tema.id, subtema_id=request.POST['ids'],
                                                          fecha=datetime.now().date())
                        suba.save(request)
                        log(u'Seleccionó subtema de la planificacion: %s' % suba, request, "add")
                    else:
                        sub = SubTemaAdicionalAsistencia.objects.get(tema_id=tema.id, subtema_id=request.POST['ids'])
                        log(u'Eliminó subtema de la planificacion: %s' % sub, request, "del")
                        sub.delete()
                return JsonResponse({"result": "ok", 'tem': tema.tema.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los temas."})

        elif action == 'DeleteclassAsynchronous':
            with transaction.atomic():
                try:
                    puede_realizar_accion(request, 'sga.puede_eliminar_link_clase_sincronica_asincronica_administrativo')
                    if not 'id' in request.POST:
                        raise NameError(u"Parametro de asincrónica no encontrado")
                    clase = ClaseAsincronica.objects.get(pk=int(encrypt(request.POST['id'])))
                    clase.status = False
                    clase.save(request)
                    log(u'Elimino clase asincrónica: %s' % clase, request, "del")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar el dato. %s" % ex.__str__()})

        elif action == 'DeleteclassSynchronous':
            with transaction.atomic():
                try:
                    puede_realizar_accion(request, 'sga.puede_eliminar_link_clase_sincronica_asincronica_administrativo')
                    if not 'id' in request.POST:
                        raise NameError(u"Parametro de clase sincrónica no encontrado")
                    clase = ClaseSincronica.objects.get(pk=int(encrypt(request.POST['id'])))
                    clase.status = False
                    clase.save(request)
                    log(u'Elimino clase sincrónica: %s' % clase, request, "del")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar el dato. %s" % ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Administrar clases y evaluaciones de profesores'
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'clases':
                try:
                    data['title'] = u'Listado de clases impartidas'
                    profesor = Profesor.objects.filter(Q(profesormateria__materia__nivel__carrera__in=miscarreras) | Q(profesormateria__materia__nivel__nivellibrecoordinacion__coordinacion__carrera__in=miscarreras)).distinct().get(pk=request.GET['id'])
                    data['materias'] =mismaterias= profesor.materias_imparte_periodo(periodo)
                    # puedeabrirclases = False
                    # for materia in mismaterias:
                    #     if not materia.cerrado:
                    #         puedeabrirclases = True
                    if 'mid' in request.GET:
                        materia = Materia.objects.get(pk=int(request.GET['mid']))
                        data['mid'] = materia.id
                        lecciones = Leccion.objects.filter(status=True, clase__materia=materia).order_by('-fecha', '-horaentrada').distinct()
                    else:
                        lecciones = Leccion.objects.filter(status=True, clase__materia__in=[materia.id for materia in mismaterias]).order_by('-fecha', '-horaentrada').distinct()
                    paging = MiPaginador(lecciones, 25)
                    p = 1
                    try:
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        page = paging.page(p)
                    except Exception as ex:
                        page = paging.page(1)
                    data['paging'] = paging
                    data['page'] = page
                    data['lecciones'] = page.object_list
                    data['profesor'] = profesor
                    # data['puedeabrirclases'] = puedeabrirclases
                    solo_adicionar_clase = False
                    if variable_valor('SOLO_ADICIONAR_CLASE_IPEC'):
                        if periodo.tipo_id==3:
                            solo_adicionar_clase = True
                    else:
                        solo_adicionar_clase = True
                    data['solo_adicionar_clase'] = solo_adicionar_clase
                    return render(request, "adm_academica/clases.html", data)
                except Exception as ex:
                    pass

            elif action == 'nuevaclase':
                try:
                    data['title'] = u'Horario de profesor'
                    data['profesor'] = profesor = Profesor.objects.filter(Q(profesormateria__materia__nivel__carrera__in=miscarreras) | Q(profesormateria__materia__nivel__nivellibrecoordinacion__coordinacion__carrera__in=miscarreras)).distinct().get(pk=request.GET['id'])
                    # puede_modificar_profesor(request, profesor)
                    # profesoringresado = Profesor.objects.get(persona=persona)
                    # puede_modificar_profesor(request, profesoringresado)
                    data['semana'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sabado'], [7, 'Domingo']]
                    turnos_clases = profesor.extrae_turnos_y_clases_docente(periodo, True, True)
                    data['misclases'] = turnos_clases[0]
                    data['materiasnoprogramadas'] = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__periodo=periodo, activo=True, materia__in=[x.materia for x in turnos_clases[0]])
                    data['profesor'] = profesor
                    data['sesiones'] = Sesion.objects.filter(turno__in=turnos_clases[1]).distinct()
                    data['fecha'] = datetime.now().date()
                    return render(request, "adm_academica/nuevaclase.html", data)
                except Exception as ex:
                    pass

            elif action == 'editclase':
                try:
                    data['title'] = u'Editar clase'
                    data['lecciongrupo'] = lecciongrupo = LeccionGrupo.objects.filter(Q(profesor__profesormateria__materia__nivel__carrera__in=miscarreras) | Q(profesor__profesormateria__materia__nivel__nivellibrecoordinacion__coordinacion__carrera__in=miscarreras)).distinct().get(pk=int(request.GET['id']))
                    data['profesor'] = profesor = lecciongrupo.profesor
                    puede_modificar_profesor(request, profesor)
                    if 'listal' in request.GET:
                        data['lecciones'] = lecciones = lecciongrupo.lecciones.filter(id__in=[encrypt(idleccion)for idleccion in json.loads(request.GET['listal'])])
                    else:
                        data['lecciones'] = lecciones = lecciongrupo.lecciones.filter(id=int(encrypt(request.GET['idl'])))
                    idmateria = lecciones[0].clase.materia.id
                    data['incluyepago'] = False
                    data['incluyedatos'] = False
                    data['matriculacion_libre'] = MATRICULACION_LIBRE
                    data['usa_planificacion'] = USA_PLANIFICACION
                    # data['temas'] = TemaAsistencia.objects.filter(leccion__clase__materia__id=lecciones[0].clase.materia.id, status=True).distinct().order_by('tema__temaunidadresultadoprogramaanalitico__orden')
                    # data['subtemas'] = SubTemaAsistencia.objects.filter(tema__leccion__clase__materia__id=lecciones[0].clase.materia.id, tema__status=True).distinct().order_by('subtema__subtemaunidadresultadoprogramaanalitico__orden')
                    # data['subtemasad'] = SubTemaAdicionalAsistencia.objects.filter(tema__leccion__clase__materia__id=lecciones[0].clase.materia.id, status=True).distinct()
                    return render(request, "adm_academica/editclase.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleteclase':
                try:
                    data['title'] = u'Borrar lección del docente'
                    data['lecciongrupo'] = lecciongrupo = LeccionGrupo.objects.filter(Q(profesor__profesormateria__materia__nivel__carrera__in=miscarreras) | Q(profesor__profesormateria__materia__nivel__nivellibrecoordinacion__coordinacion__carrera__in=miscarreras)).distinct().get(pk=request.GET['id'])
                    puede_modificar_profesor(request, lecciongrupo.profesor)
                    return render(request, "adm_academica/deleteclase.html", data)
                except Exception as ex:
                    pass

            elif action == 'cronograma':
                try:
                    data['title'] = u'Cronograma de materias del profesor'
                    data['periodo'] = periodo
                    data['profesor'] = profesor = Profesor.objects.filter(Q(profesormateria__materia__nivel__carrera__in=miscarreras) | Q(profesormateria__materia__nivel__nivellibrecoordinacion__coordinacion__carrera__in=miscarreras)).distinct().get(pk=request.GET['id'])
                    # data['materias'] = profesor.materias_imparte_periodo(periodo)
                    data['materias'] = Materia.objects.filter(status=True, profesormateria__activo=True, profesormateria__status=True,
                                      nivel__periodo=periodo,
                                      profesormateria__profesor=profesor).distinct()
                    data['matriculacion_libre'] = MATRICULACION_LIBRE
                    data['reporte_0'] = obtener_reporte('mate_cronogramaprofesor')
                    data['reporte_1'] = obtener_reporte("control_academico")
                    return render(request, "adm_academica/cronograma.html", data)
                except Exception as ex:
                    pass

            elif action == 'horario':
                try:
                    data['title'] = u'Horario de profesor'
                    # data['profesor'] = profesor = Profesor.objects.filter(Q(profesormateria__materia__nivel__carrera__in=miscarreras) | Q(profesormateria__materia__nivel__nivellibrecoordinacion__coordinacion__carrera__in=miscarreras)).distinct().get(pk=request.GET['id'])
                    data['profesor'] = profesor = Profesor.objects.get(pk=request.GET['id'])
                    data['semana'] = ['Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado', 'Domingo']
                    data['turnos'] = profesor.extrae_turnos_y_clases_docente(periodo)[1]
                    data['reporte_0'] = obtener_reporte('horario_profesor')
                    data['puede_ver_horario'] = periodo.visible==True and periodo.visiblehorario==True
                    return render(request, "adm_academica/horario.html", data)
                except Exception as ex:
                    pass

            elif action == 'horarioprofesor':
                data = {}
                data['periodo'] = periodo = request.session['periodo']
                # if not PermisoPeriodo.objects.filter(periodo=periodo).exists():
                if not request.session['periodo'].visible:
                    return HttpResponseRedirect("/?info=No tiene permiso para imprimir en el periodo seleccionado.")
                data['profesor'] = profesor = Profesor.objects.filter().distinct().get(pk=request.GET['profesor'])
                # data['semana'] = ['Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado', 'Domingo']
                data['semana'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'],[6, 'Sabado'], [7, 'Domingo']]
                # data['turnos'] = Turno.objects.filter(clase__activo=True, clase__materia__nivel__periodo=periodo, clase__materia__profesormateria__profesor=profesor, clase__materia__profesormateria__principal=True).distinct().order_by('comienza')
                turnoclases = profesor.extrae_turnos_y_clases_docente(periodo)[1]
                complexivo = ComplexivoClase.objects.values_list('turno__id').filter(activo=True, materia__profesor__profesorTitulacion=profesor, materia__status=True)
                # turnoclases = Turno.objects.filter(Q(id__in=turnoclases) | Q(id__in=complexivo)).distinct().order_by('comienza')
                turnoclases = Turno.objects.filter(Q(status=True, mostrar=True), Q(id__in=turnoclases) | Q(id__in=complexivo)).distinct('comienza').order_by('comienza')
                # turnoactividades = Turno.objects.filter(claseactividad__detalledistributivo__distributivo__periodo=periodo, claseactividad__detalledistributivo__distributivo__profesor=profesor).distinct().order_by('comienza')
                turnoactividades = Turno.objects.filter(status=True, mostrar=True, claseactividad__detalledistributivo__distributivo__periodo=periodo, claseactividad__detalledistributivo__distributivo__profesor=profesor).distinct('comienza').order_by('comienza')
                data['turnos'] = turnoclases | turnoactividades
                return conviert_html_to_pdf(
                    'adm_academica/horario_pfd.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )

            elif action == 'segmento':
                try:
                    data['materia'] = Materia.objects.get(pk=request.GET['id'])
                    data['profesor'] = Profesor.objects.get(pk=request.GET['profesor'])
                    data['reporte_0'] = obtener_reporte('acta_notas')
                    return render(request, "adm_academica/segmento.html", data)
                except Exception as ex:
                    pass

            elif action == 'calificaciones':
                try:
                    data['title'] = u'Evaluaciones de alumnos'
                    data['profesor'] = profesor = Profesor.objects.filter(Q(profesormateria__materia__nivel__carrera__in=miscarreras) | Q(profesormateria__materia__nivel__nivellibrecoordinacion__coordinacion__carrera__in=miscarreras)).distinct().get(pk=request.GET['id'])
                    data['materias'] = profesor.materias_imparte_periodo(periodo)
                    return render(request, "adm_academica/calificaciones.html", data)
                except Exception as ex:
                    pass

            elif action == 'segmentoasist':
                try:
                    return render(request, "adm_academica/segmentoasist.html", {'materia': Materia.objects.get(pk=request.GET['id'])})
                except Exception as ex:
                    pass

            elif action == 'asistencias':
                try:
                    data['title'] = u'Consulta de asistencias de alumnos'
                    data['profesor'] = profesor = Profesor.objects.filter(Q(profesormateria__materia__nivel__carrera__in=miscarreras) | Q(profesormateria__materia__nivel__nivellibrecoordinacion__coordinacion__carrera__in=miscarreras)).distinct().get(pk=request.GET['id'])
                    data['materias'] = profesor.materias_imparte_periodo(periodo)
                    return render(request, "adm_academica/asistencias.html", data)
                except Exception as ex:
                    pass

            elif action == 'planificaciones':
                try:
                    data['title'] = u'Consulta de planificación del docente'
                    data['profesor'] = profesor = Profesor.objects.filter(Q(profesormateria__materia__nivel__carrera__in=miscarreras) | Q(profesormateria__materia__nivel__nivellibrecoordinacion__coordinacion__carrera__in=miscarreras)).distinct().get(pk=request.GET['id'])
                    data['materias'] = profesor.materias_imparte_periodo(periodo)
                    return render(request, "adm_academica/planificaciones.html", data)
                except Exception as ex:
                    pass

            elif action == 'planificacionmateria':
                try:
                    data['title'] = u'Planificación de materia'
                    data['profesor'] = Profesor.objects.filter(Q(profesormateria__materia__nivel__carrera__in=miscarreras) | Q(profesormateria__materia__nivel__nivellibrecoordinacion__coordinacion__carrera__in=miscarreras)).distinct().get(pk=request.GET['idp'])
                    data['materia'] = materia = Materia.objects.get(pk=request.GET['id'])
                    data['planificaciones'] = materia.planificacionmateria_set.all().order_by('tipoevaluacion')
                    return render(request, "adm_academica/planificacionmateria.html", data)
                except Exception as ex:
                    pass

            elif action == 'view':
                try:
                    data['title'] = u'Lección'
                    if 'ret' in request.GET:
                        data['ret'] = request.GET['ret']
                    if 'reg' in request.GET:
                        data['reg'] = request.GET['reg']
                    data['lecciongrupo'] = lecciongrupo = LeccionGrupo.objects.get(pk=request.GET['id'])
                    data['lecciones'] = lecciones = lecciongrupo.lecciones.all()
                    data['tiposincidencias'] = TipoIncidencia.objects.all()
                    data['incidencias'] = []
                    if Incidencia.objects.filter(lecciongrupo=lecciongrupo).exists():
                        data['incidencias'] = Incidencia.objects.filter(lecciongrupo=lecciongrupo)
                    data['deber'] = None
                    if Archivo.objects.filter(lecciongrupo=lecciongrupo).exists():
                        data['deber'] = Archivo.objects.filter(lecciongrupo=lecciongrupo)[0]
                    data['incluyepago'] = False
                    data['incluyedatos'] = False
                    data['incluyedatosmedicos'] = FICHA_MEDICA_ESTRICTA
                    return render(request, "pro_clases/leccion.html", data)
                except Exception as ex:
                    pass

            elif action == 'verevidencia':
                try:
                    data['title'] = u'Evidencias Actividad'
                    # puede_realizar_accion(request, 'sga.puede_modificar_criteriosdocentes')
                    # data['coordinacion'] = coordinaciones = persona.mis_coordinaciones()
                    data['profesor'] = profesor = Profesor.objects.filter(pk=request.GET['id'])
                    data['coordinacion'] = coordinaciones = Coordinacion.objects.all()
                    data['periodo'] = periodo
                    data['permite_modificar'] = False
                    data['evidenciaactividaddetalledistributivodocencia'] = EvidenciaActividadDetalleDistributivo.objects.filter(criterio__distributivo__profesor__coordinacion__in=coordinaciones, criterio__distributivo__periodo=periodo, criterio__criteriodocenciaperiodo__isnull=False, criterio__distributivo__profesor=profesor).distinct().order_by('criterio__distributivo__profesor','desde')
                    data['evidenciaactividaddetalledistributivoinvestigacion'] = EvidenciaActividadDetalleDistributivo.objects.filter(criterio__distributivo__profesor__coordinacion__in=coordinaciones, criterio__distributivo__periodo=periodo, criterio__criterioinvestigacionperiodo__isnull=False, criterio__distributivo__profesor=profesor).distinct().order_by('criterio__distributivo__profesor','desde')
                    data['evidenciaactividaddetalledistributivogestion'] = EvidenciaActividadDetalleDistributivo.objects.filter(criterio__distributivo__profesor__coordinacion__in=coordinaciones, criterio__distributivo__periodo=periodo, criterio__criteriogestionperiodo__isnull=False, criterio__distributivo__profesor=profesor).distinct().order_by('criterio__distributivo__profesor','desde')
                    return render(request, "adm_docentes/verevidencia.html", data)
                except Exception as ex:
                    pass

            elif action == 'detalle_clasesvideo':
                try:
                    profesor = Profesor.objects.get(pk=request.GET['id'])
                    data['title'] = u'Detalle clases sincrónicas y asincrónicas'
                    data['hoy'] = hoy = datetime.now().date()
                    listaasistencias = []
                    cursor = connections['default'].cursor()
                    sql = f"""
                            SELECT DISTINCT 
                                ten.codigoclase, ten.dia, ten.turno_id,
                                ten.inicio, ten.fin, ten.materia_id,
                                ten.tipohorario, ten.horario, ten.rangofecha,
                                ten.rangodia, sincronica.fecha AS sincronica, asincronica.fechaforo AS asincronica, 
                                asignatura, paralelo,
                                CASE 
                                    WHEN asincronica.idforomoodle IS NOT  NULL THEN asincronica.idforomoodle 
                                    ELSE sincronica.idforomoodle 
                                END  idforomoodle, ten.comienza, ten.termina,
                                nolaborables.fecha, nolaborables.observaciones, ten.nivelmalla,
                                ten.idnivelmalla, ten.idcarrera, ten.idcoordinacion,
                                ten.tipoprofesor_id,EXTRACT(week FROM ten.rangofecha::date) AS numerosemana,ten.tipoprofesor
                            FROM ( SELECT DISTINCT  
                                        cla.tipoprofesor_id,cla.id AS	codigoclase,
                                        cla.dia,cla.turno_id,cla.inicio,cla.fin,cla.materia_id, cla.tipohorario, 
                                        CASE WHEN cla.tipohorario IN(2,8)  THEN 2 WHEN cla.tipohorario in(7,9)  THEN 7 END AS horario,
                                        CURRENT_DATE + GENERATE_SERIES(cla.inicio- CURRENT_DATE, cla.fin - CURRENT_DATE ) AS rangofecha,
                                        EXTRACT (isodow  FROM  CURRENT_DATE + GENERATE_SERIES(cla.inicio- CURRENT_DATE, 
                                        cla.fin - CURRENT_DATE )) AS rangodia,asig.nombre AS asignatura, mate.paralelo AS paralelo,
                                        tur.comienza,tur.termina,nimalla.nombre AS nivelmalla,nimalla.id AS idnivelmalla,
                                        malla.carrera_id AS idcarrera,coorcar.coordinacion_id AS idcoordinacion,
                                        tipro.nombre AS tipoprofesor 
                                    FROM sga_clase cla , sga_materia mate,
                                     sga_asignaturamalla asimalla,sga_asignatura asig,
                                     sga_turno tur,sga_nivel niv,sga_nivelmalla nimalla,
                                     sga_malla malla,sga_carrera carre, 
                                     sga_coordinacion_carrera coorcar, 
                                     sga_tipoprofesor tipro 
                                    WHERE	
                                        cla.profesor_id={profesor.id} AND	
                                        cla.materia_id = mate.id AND mate.asignaturamalla_id = asimalla.id AND 
                                        asimalla.malla_id=malla.id AND asimalla.asignatura_id = asig.id AND	 
                                        cla.turno_id=tur.id AND asimalla.nivelmalla_id=nimalla.id AND	 
                                        malla.carrera_id=carre.id AND	 coorcar.carrera_id=carre.id AND 
                                        cla.tipohorario IN (8, 9, 2, 7) AND mate.nivel_id=niv.id AND	 
                                        cla.activo=True AND cla.tipoprofesor_id=tipro.id AND niv.periodo_id={periodo.id}) AS ten
                                LEFT JOIN(  SELECT 
                                                clas.id  clase_id, clas.materia_id,asi.fecha_creacion::timestamp::date AS fecha, clas.tipoprofesor_id,
                                                asi.fecha_creacion AS fecharegistro, asi.fechaforo AS fechaforo, asi.idforomoodle idforomoodle 
                                            FROM sga_clasesincronica asi, sga_clase clas 
                                            WHERE asi.clase_id=clas.id AND asi.status=true AND clas.profesor_id={profesor.id}) AS sincronica 
                                    ON (ten.rangofecha=fechaforo AND ten.horario=2 AND sincronica.materia_id=ten.materia_id  AND sincronica.tipoprofesor_id=ten.tipoprofesor_id)OR 
                                       (sincronica.materia_id=ten.materia_id AND sincronica.fechaforo=ten.rangofecha AND EXTRACT(dow from  sincronica.fechaforo)=ten.rangodia AND sincronica.tipoprofesor_id=ten.tipoprofesor_id)
                                LEFT JOIN(  SELECT   
                                                clas.id  clase_id,  clas.materia_id,asi.fechaforo,asi.idforomoodle, clas.tipoprofesor_id 
                                            FROM sga_claseasincronica asi, sga_clase clas 
                                            WHERE asi.clase_id=clas.id AND asi.status=true) AS asincronica 
                                    ON (asincronica.materia_id=ten.materia_id AND ten.rangofecha=asincronica.fechaforo AND	ten.horario=2  AND asincronica.tipoprofesor_id=ten.tipoprofesor_id)OR 
                                        (asincronica.materia_id=ten.materia_id  AND	 asincronica.fechaforo=ten.rangofecha AND  EXTRACT(dow from  asincronica.fechaforo)=ten.rangodia AND asincronica.tipoprofesor_id=ten.tipoprofesor_id)        
                                LEFT JOIN (SELECT 
                                            nolab.observaciones, nolab.fecha 
                                            FROM sga_diasnolaborable nolab 
                                            WHERE nolab.periodo_id={periodo.id}) AS nolaborables ON nolaborables.fecha = ten.rangofecha   
                            WHERE 
                                ten.dia=ten.rangodia AND 
                                ten.rangofecha <'{hoy}'
                            ORDER BY ten.rangofecha,materia_id,ten.turno_id,tipohorario                
                    """
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    totalsincronica = 0
                    totalasincronica = 0
                    totalplansincronica = 0
                    totalplanasincronica = 0
                    for cuentamarcadas in results:
                        materia = None
                        moodle_url = None
                        if Materia.objects.values("id").filter(pk=cuentamarcadas[5],status=True).exists():
                            materia = Materia.objects.get(pk=cuentamarcadas[5])
                            mi_coordinacion = materia.coordinacion()
                            if mi_coordinacion:
                                if mi_coordinacion.id == 9:
                                    moodle_url = f'https://aulanivelacion.unemi.edu.ec/mod/url/view.php?id={cuentamarcadas[14]}'
                                elif mi_coordinacion.id in [1, 2, 3, 4, 5, 12]:
                                    if materia.asignaturamalla.malla.modalidad_id in [1, 2]:
                                        moodle_url = f'https://aulagradoa.unemi.edu.ec/mod/url/view.php?id={cuentamarcadas[14]}'
                                    elif materia.asignaturamalla.malla.modalidad_id == 3:
                                        moodle_url = f'https://aulagradob.unemi.edu.ec/mod/url/view.php?id={cuentamarcadas[14]}'
                                    else:
                                        moodle_url = f'https://aulagrado.unemi.edu.ec/mod/url/view.php?id={cuentamarcadas[14]}'

                        sinasistencia = periodo.tiene_dias_nolaborables(fecha=cuentamarcadas[8], materia=materia)
                        dianolaborable = periodo.dias_nolaborables(fecha=cuentamarcadas[8], materia=materia)
                        hoy = datetime.now().date()
                        codigoclase = cuentamarcadas[0]
                        clase = Clase.objects.get(pk=codigoclase)
                        clases = Clase.objects.filter(materia=clase.materia, dia=clase.dia, tipoprofesor=clase.tipoprofesor, tipohorario=clase.tipohorario)
                        if clases.exists():
                            clases = clases.order_by('-id')
                            clasetrue = clases.filter(inicio__lte=hoy, fin__gte=hoy)
                            if clasetrue.exists():
                                clasetrue = clasetrue.order_by('-turno__comienza')[0]
                            else:
                                clasetrue = clases.order_by('-turno__comienza')[0]
                            codigoclase = clasetrue.id

                        # sinasistencia = False
                        # if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22],carrera_id=cuentamarcadas[21],nivelmalla_id=cuentamarcadas[20], status=True).exists():
                        #     if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22],carrera_id=cuentamarcadas[21],nivelmalla_id=cuentamarcadas[20], fecha=cuentamarcadas[8], status=True).exists():
                        #         sinasistencia = True
                        # else:
                        #     if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id=cuentamarcadas[21], nivelmalla_id__isnull=True, status=True).exists():
                        #         if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id=cuentamarcadas[21], nivelmalla_id__isnull=True, fecha=cuentamarcadas[8], status=True).exists():
                        #             sinasistencia = True
                        #     else:
                        #         if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id__isnull=True, nivelmalla_id__isnull=True, status=True).exists():
                        #             if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id__isnull=True, nivelmalla_id__isnull=True, fecha=cuentamarcadas[8], status=True).exists():
                        #                 sinasistencia = True
                        #         else:
                        #             if periodo.diasnolaborable_set.filter(coordinacion_id__isnull=True, carrera_id__isnull=True, nivelmalla_id__isnull=True, status=True).exists():
                        #                 if periodo.diasnolaborable_set.filter(coordinacion_id__isnull=True, carrera_id__isnull=True, nivelmalla_id__isnull=True, fecha=cuentamarcadas[8], status=True).exists():
                        #                     sinasistencia = True
                        listaasistencias.append(
                            [codigoclase, cuentamarcadas[1], cuentamarcadas[2], cuentamarcadas[3],
                             cuentamarcadas[4], cuentamarcadas[5], cuentamarcadas[6], cuentamarcadas[7],
                             cuentamarcadas[8], cuentamarcadas[9], cuentamarcadas[10], cuentamarcadas[11],
                             cuentamarcadas[12], cuentamarcadas[13], cuentamarcadas[14], cuentamarcadas[15],
                             cuentamarcadas[16], cuentamarcadas[17], cuentamarcadas[18], cuentamarcadas[19],
                             sinasistencia, cuentamarcadas[24], cuentamarcadas[25], dianolaborable, moodle_url, clase])

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
                    # data['procentajesincronica'] = (totalplansincronica * 100) / totalsincronica
                    # data['procentajeasincronica'] = (totalplanasincronica * 100) / totalasincronica
                    data['profesor'] = profesor
                    # profesoresingresar = [1459,1450]

                    # puedeingresar = False
                    # if profesor.id in profesoresingresar:
                    #     puedeingresar = True
                    #     fechainiplan = '2020-11-28'
                    #     fechafinplan = '2021-03-05'
                    # else:
                    #     fechainiplan = '2021-01-14'
                    #     fechafinplan = '2021-01-14'
                    # data['puedeingresar'] = puedeingresar
                    # data['fechainicio'] = date(int(fechainiplan[0:4]), int(fechainiplan[5:7]), int(fechainiplan[8:10]))
                    # data['fechafinal'] = date(int(fechafinplan[0:4]), int(fechafinplan[5:7]), int(fechafinplan[8:10]))
                    return render(request, "adm_academica/detalle_clasesvideo.html", data)
                except Exception as ex:
                    pass

            elif action == 'loadDetailClassSynchronousAsynchronous':
                try:
                    if not 'id' in request.GET:
                        raise NameError(u"No se encontro parametro de lección")
                    if not 'num_semana' in request.GET:
                        raise NameError(u"Parametro de numero de la semana de la clase no encontrado")
                    clase = Clase.objects.filter(pk=int(encrypt(request.GET['id']))).first()
                    numero_semana = request.GET['num_semana']
                    if clase is None:
                        raise NameError(u"Lección/Clase no encontrada")

                    clases_sincronicas = clase.clasesincronica_set.filter(numerosemana=numero_semana, status=True)
                    clases_asincronicas = clase.claseasincronica_set.filter(numerosemana=numero_semana, status=True)

                    data['clase'] = clase
                    data['num_semana'] = numero_semana
                    data['title'] = u'Clase %s'%(clase)
                    data['clases_sincronicas'] = clases_sincronicas
                    data['clases_asincronicas'] = clases_asincronicas
                    template = get_template(f"adm_academica/listadoclase_sincronicas_asincronicas.html")
                    json_content = template.render(data, request=request)
                    return JsonResponse({"result": "ok", 'html': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            return HttpResponseRedirect(request.path)
        else:
            search = None
            ids = None
            periodo = request.session['periodo']
            if persona.usuario.is_superuser:
                distributivohora = ProfesorDistributivoHoras.objects.filter(periodo=periodo).distinct().order_by('profesor__persona')
            elif persona.es_responsablecoordinacion(periodo):
                responsablecoordinacion = persona.responsablecoordinacion(periodo)
                if responsablecoordinacion.coordinacion_id == 25:
                    distributivohora = ProfesorDistributivoHoras.objects.filter(periodo=periodo).distinct().order_by(
                        'profesor__persona')
                else:
                    distributivohora = ProfesorDistributivoHoras.objects.filter(periodo=periodo, coordinacion=responsablecoordinacion.coordinacion).distinct().order_by('profesor__persona')
            elif persona.es_coordinadorcarrera(periodo):
                responsablecarrera = persona.coordinadorcarreras(periodo)
                coordinaciones = Coordinacion.objects.filter(carrera__id__in=responsablecarrera.values_list('carrera__id'))
                listaprofesorprofesor = ProfesorMateria.objects.values_list('profesor__id').filter(materia__nivel__periodo=periodo, materia__asignaturamalla__malla__carrera__coordinacion__in=coordinaciones).distinct('profesor__id').order_by('profesor__id')
                distributivohora = ProfesorDistributivoHoras.objects.filter(periodo=periodo, profesor__id__in=listaprofesorprofesor).distinct().order_by('profesor__persona')
            else:
                distributivohora = ProfesorDistributivoHoras.objects.filter(periodo=periodo).distinct().order_by('profesor__persona')
            # if not request.session['periodo'].visible:
            #     return HttpResponseRedirect("/?info=Periodo Inactivo.")
            if 's' in request.GET:
                search = request.GET['s']
                ss = search.split(' ')
                if len(ss) == 1:
                    distributivohora = distributivohora.filter(Q(profesor__persona__nombres__icontains=search) |
                                                               Q(profesor__persona__apellido1__icontains=search) |
                                                               Q(profesor__persona__apellido2__icontains=search) |
                                                               Q(profesor__persona__cedula__icontains=search)).distinct().order_by('profesor__persona')
                else:
                    distributivohora = distributivohora.filter(Q(profesor__persona__apellido1__icontains=ss[0]) &
                                                               Q(profesor__persona__apellido2__icontains=ss[1])).distinct().order_by('profesor__persona')
            elif 'id' in request.GET:
                ids = request.GET['id']
                distributivohora = distributivohora.filter(profesor__id=ids).distinct()
            paging = MiPaginador(distributivohora, 30)
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
            data['search'] = search if search else ""
            data['ids'] = ids if ids else ""
            data['distributivohora'] = page.object_list
            data['usa_planificacion'] = USA_PLANIFICACION
            data['form2'] = CambiarProfesorForm()
            return render(request, "adm_academica/view.html", data)
