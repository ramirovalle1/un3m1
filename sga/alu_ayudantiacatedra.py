# -*- coding: latin-1 -*-
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from django.template import Context
from django.template.loader import get_template
from decorators import secure_module, last_access
from sga.commonviews import adduserdata, obtener_reporte
from sga.forms import ActividadInscripcionCatedraForm, InscripcionCatedraArchivoForm
from sga.funciones import log, generar_nombre, variable_valor
from sga.models import PeriodoCatedra, InscripcionCatedra, AsignaturaMalla, ProfesorMateria, \
    ActividadInscripcionCatedra, MateriaAsignada, AsistenciaActividadInscripcionCatedra, Inscripcion, miinstitucion, \
    CUENTAS_CORREOS, RecordAcademico, ArchivoGeneralCatedra, DetalleSolicitudProfesorCatedra
from django.db.models import Q
from sga.tasks import send_html_mail, conectar_cuenta


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
    perfilprincipal = request.session['perfilprincipal']
    inscripcion = perfilprincipal.inscripcion
    eInscripcion = perfilprincipal.inscripcion
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")

    ePeriodoCatedra = periodo.periodocatedra_set.filter(status=True).first()
    if ePeriodoCatedra is None:
        return HttpResponseRedirect(f"/?info=No existe periodo catedra configurado")

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'registrar_old':
            try:
                periodocatedra = PeriodoCatedra.objects.filter(pk=request.POST['idperiodocatedra'])[0]
                notamaximaperiodo = periodocatedra.notamaxima
                periodolectivo = periodocatedra.periodolectivo
                matricula = inscripcion.matricula_periodo(periodolectivo)
                profesormateria = ProfesorMateria.objects.get(pk=int(request.POST['id']))
                #notarecordmateria = RecordAcademico.objects.filter(inscripcion=inscripcion, status=True, asignaturamalla=profesormateria.materia.asignaturamalla)[0].nota
                cantidad_materias_periodocatedra = periodocatedra.numeromateria
                # cantidad_registros = InscripcionCatedra.objects.filter(periodocatedra=periodocatedra, inscripcion=inscripcion, status=True).count()
                cantidad_registros_solicitados = InscripcionCatedra.objects.filter(estado=1,estadoinscripcion=1,periodocatedra=periodocatedra, inscripcion=inscripcion, status=True).count()
                cantidad_registros_aprobobados = InscripcionCatedra.objects.filter(estado=2,estadoinscripcion=2,periodocatedra=periodocatedra, inscripcion=inscripcion, status=True).count()
                cantidad_registros_aprob_soli = InscripcionCatedra.objects.filter(estado=2,estadoinscripcion=1,periodocatedra=periodocatedra, inscripcion=inscripcion, status=True).count()
                if ( cantidad_registros_solicitados < cantidad_materias_periodocatedra) and (cantidad_registros_aprobobados<cantidad_materias_periodocatedra) and (cantidad_registros_aprob_soli<cantidad_materias_periodocatedra):
                    # if notarecordmateria >= float(notamaximaperiodo):
                        profesormateria = ProfesorMateria.objects.get(pk=int(request.POST['id']))
                        profesor = profesormateria.profesor
                        materia = profesormateria.materia
                        inscripcioncatedra = InscripcionCatedra(periodocatedra=periodocatedra,
                                                                inscripcion=inscripcion,
                                                                matricula=matricula,
                                                                materia=materia,
                                                                docente=profesor)
                        inscripcioncatedra.save(request)
                        lista = inscripcioncatedra.docente.persona.emails()
                        send_html_mail(
                            "Solicitud de Ayudantia de Catedra %s" % inscripcioncatedra.materia.asignatura.nombre,
                            "emails/solicitud_ayudantia_catedra_registrar.html",
                            {'sistema': request.session['nombresistema'],
                             'materia': inscripcioncatedra.materia.asignatura,
                             'solicita': inscripcioncatedra.inscripcion.persona.nombre_completo_inverso(),
                             't': miinstitucion()}, lista, [], cuenta=CUENTAS_CORREOS[5][1])
                        log(u'Adiciono Ayudantia Catedra: %s' % inscripcioncatedra, request, "add")
                        return JsonResponse({"result": "ok", "mensaje": u"Materia Solicitada con éxito"})
                    #else:
                #    return JsonResponse({"result": "bad","mensaje": u"Su nota en esta asignatura debe ser mayor o igual a %s." % notamaximaperiodo})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Llego al limite de materias que puede solicitar."})
                # (Q(estado=1) &
                #  Q(estadoinscripcion=1)) |
                # (Q(estado=2) &
                #  Q(estadoinscripcion=2))

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'registrar':
            try:
                notamaximaperiodo = ePeriodoCatedra.notamaxima
                periodolectivo = ePeriodoCatedra.periodolectivo
                eMatricula = inscripcion.matricula_periodo(periodolectivo)
                eDetalleSolicitudProfesorCatedra = DetalleSolicitudProfesorCatedra.objects.get(id=int(request.POST['id']))
                eInscripcionesCatedras = eInscripcion.inscripcioncatedra_set.filter(status=True, periodocatedra=ePeriodoCatedra)
                cantidad_registros_solicitados = eInscripcionesCatedras.filter(estado=1, estadoinscripcion=1).count()
                cantidad_registros_aprobobados = eInscripcionesCatedras.filter(estado=2, estadoinscripcion=2).count()
                cantidad_registros_aprob_soli = eInscripcionesCatedras.filter(estado=2, estadoinscripcion=1).count()
                if (cantidad_registros_solicitados < ePeriodoCatedra.numeromateria) and (cantidad_registros_aprobobados < ePeriodoCatedra.numeromateria) and (cantidad_registros_aprob_soli < ePeriodoCatedra.numeromateria):
                    eInscripcionCatedra = InscripcionCatedra(detallesolicitudprofesorcatedra=eDetalleSolicitudProfesorCatedra,
                                                             periodocatedra=ePeriodoCatedra,
                                                             inscripcion=eInscripcion,
                                                             matricula=eMatricula,
                                                             materia=eDetalleSolicitudProfesorCatedra.materia,
                                                             docente=eDetalleSolicitudProfesorCatedra.solicitud.profesor)
                    eInscripcionCatedra.save(request)
                    lista = eInscripcionCatedra.docente.persona.lista_emails()
                    send_html_mail(
                        "Solicitud de Ayudantía de Cátedra %s" % eInscripcionCatedra.materia.asignatura.nombre,
                        "emails/solicitud_ayudantia_catedra_registrar.html",
                        {'sistema': request.session['nombresistema'],
                         'materia': eInscripcionCatedra.materia.asignatura,
                         'paralelo': eInscripcionCatedra.materia.paralelomateria,
                         'solicita': eInscripcionCatedra.inscripcion.persona.nombre_completo_inverso(),
                         't': miinstitucion()}, lista, [], cuenta=CUENTAS_CORREOS[5][1])
                    log(u'Adiciono Ayudantia Catedra: %s' % eInscripcionCatedra, request, "add")
                    return JsonResponse({"result": "ok", "mensaje": u"Materia Solicitada con éxito"})
                else:
                    raise NameError(u"Llego al limite de materias que puede solicitar.")
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"%s" % ex.__str__()})

        if action == 'delete':
            try:
                inscripcioncatedra = InscripcionCatedra.objects.get(pk=request.POST['id'])
                inscripcioncatedra.status=False
                inscripcioncatedra.save(request)
                lista = inscripcioncatedra.docente.persona.lista_emails()
                send_html_mail("Solicitud de Ayudantía de Cátedra %s" % inscripcioncatedra.materia.asignatura.nombre,
                               "emails/solicitud_ayudantia_catedra_eliminar.html",
                               {'sistema': request.session['nombresistema'],
                                'paralelo': inscripcioncatedra.materia.paralelomateria,
                                'materia': inscripcioncatedra.materia.asignatura,
                                'solicita': inscripcioncatedra.inscripcion.persona.nombre_completo_inverso(),
                                't': miinstitucion()}, lista, [], cuenta=CUENTAS_CORREOS[5][1])
                log(u'Elimino Ayudantia Catedra: %s' % inscripcioncatedra, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'subirarchivos':
            try:
                actividadinscripcioncatedra = ActividadInscripcionCatedra.objects.get(pk=request.POST['id'])
                if not actividadinscripcioncatedra.inscripcioncatedra.puederegistraractividad():  # SOLO PUEDE REGISTRAR ACTIVIDADES CUANDO ESTÉ DENTRO DEL PERIODO
                    raise ('Error')
                f = ActividadInscripcionCatedraForm(request.POST, request.FILES)
                if 'archivoevidencia' in request.FILES:
                    d = request.FILES['archivoevidencia']
                    if d.size > 6291456:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                    else:
                        newfiles = request.FILES['archivoevidencia']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        extensiones = []
                        if ext == '.pdf' or  ext == '.doc' or ext == '.docx' :
                            a = 1
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf,.doc,docx."})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"No existe archivo"})
                if f.is_valid():
                    newfile = None
                    if 'archivoevidencia' in request.FILES:
                        newfile = request.FILES['archivoevidencia']
                        newfile._name = generar_nombre("archivoevidencia_", newfile._name)
                        actividadinscripcioncatedra.archivoevidencia = newfile
                    actividadinscripcioncatedra.actividadevidencia = f.cleaned_data['actividadevidencia']
                    actividadinscripcioncatedra.fechaevidencia = datetime.now()
                    actividadinscripcioncatedra.save(request)
                    lista = actividadinscripcioncatedra.inscripcioncatedra.docente.persona.lista_emails()
                    send_html_mail("Subir Evidencia de Ayudantia de Catedra %s" % actividadinscripcioncatedra.inscripcioncatedra.materia.asignatura.nombre,
                                   "emails/solicitud_ayudantia_catedra_evidencia.html",
                                   {'sistema': request.session['nombresistema'],
                                    'paralelo': actividadinscripcioncatedra.inscripcioncatedra.materia.paralelomateria,
                                    'materia': actividadinscripcioncatedra.inscripcioncatedra.materia,
                                    'solicita': actividadinscripcioncatedra.inscripcioncatedra.inscripcion.persona.nombre_completo_inverso(),
                                    't': miinstitucion()}, lista, [], cuenta=CUENTAS_CORREOS[5][1])
                    log(u'Subio Evidencia Ayudantia Catedra: %s' % actividadinscripcioncatedra, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al subir la Evidencia."})

        if action == 'subircarta':
            try:
                inscripcioncatedra = InscripcionCatedra.objects.get(pk=request.POST['idinscripcion'])
                f = InscripcionCatedraArchivoForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    if d.size > 6291456:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        extensiones = []
                        if ext == '.pdf' or  ext == '.doc' or ext == '.docx' :
                            a = 1
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf,.doc,docx."})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"No existe archivo"})
                if f.is_valid():
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("archivoevidencia_", newfile._name)
                        inscripcioncatedra.archivo = newfile
                        inscripcioncatedra.save(request)
                        log(u'Subio Carta Compromiso Ayudantia Catedra: %s' % inscripcioncatedra, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al subir la Carta Compromiso."})

        if action == 'validacion':
            try:
                if not inscripcion.graduado():
                    # valideacion de periodo y fecha
                    periodocatedra = PeriodoCatedra.objects.filter(pk=ePeriodoCatedra.id)
                    if periodocatedra:
                        periodolectivo = periodocatedra[0].periodolectivo
                        hoy = datetime.now().date()
                        fechadesde = periodocatedra[0].fechadesde
                        fechahasta = periodocatedra[0].fechahasta
                        if hoy < fechadesde:
                            return JsonResponse({"result": "bad", "mensaje": u"El periodo de inscripción ha terminado."})
                        if hoy > fechahasta:
                            return JsonResponse({"result": "bad", "mensaje": u"El periodo de inscripción ha terminado."})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"No existe configuración de Ayudantía de cátedra para el periodo académico."})
                    # validacion de nivel maximo de configuracion
                    nivelmallaperiodo = periodocatedra[0].nivelmalla
                    notamaximaperiodo = periodocatedra[0].notamaxima
                    matricula = inscripcion.matricula_periodo(periodolectivo)
                    if not matricula:
                        # nivelmallamatricula = 10
                        return JsonResponse({"result": "bad","mensaje": u"Solo los alumnos matriculados en el periodo puede solicitar ayudantía de cátedra."})
                    else:
                        nivelmallamatricula = matricula.nivelmalla.id

                    if nivelmallamatricula < nivelmallaperiodo.id:
                        return JsonResponse({"result": "bad", "mensaje": u"Solo los alumnos matriculados a partir de %s puede solicitar ayudantía de cátedra." % nivelmallaperiodo})
                    mallainscripcion = inscripcion.malla_inscripcion().malla
                    asignaturas = AsignaturaMalla.objects.values_list('asignatura__id', flat=True).filter(malla=mallainscripcion, nivelmalla__id__lt=nivelmallaperiodo.id, status=True, opcional=False)
                    cantidadvalidacionreprobada = RecordAcademico.objects.filter(inscripcion=inscripcion, asignaturamalla__nivelmalla__id__lt=nivelmallaperiodo.id,asignatura__id__in=asignaturas, aprobada=False, status=True).count()
                    if cantidadvalidacionreprobada > 0:
                        return JsonResponse({"result": "bad", "mensaje": u"Solo los alumnos que tiene aprobadas todas las materias de los niveles que ha cursado hasta ahora y con notas mayor igual a %s puede solicitar ayudantía de catédra." % notamaximaperiodo})

                    # cantidadvalidacion = RecordAcademico.objects.filter(inscripcion=inscripcion, nota__lt=notamaximaperiodo, asignaturamalla__nivelmalla__id__lt=nivelmallamatricula, asignatura__id__in=asignaturas, aprobada=True, status=True).count()
                    # if cantidadvalidacion > 0:
                    #     return JsonResponse({"result": "bad", "mensaje": u"Solo los alumnos que tiene aprobadas todas las materias de su nivel para atras con notas mayor igual a %s puede solicitar Ayudantia de catedra." % notamaximaperiodo})

                    cantidadasignaturasmallas = asignaturas.count()
                    # cantidadvalidacionaprobadas = RecordAcademico.objects.filter(inscripcion=inscripcion, nota__gte=notamaximaperiodo, asignaturamalla__nivelmalla__id__lt=nivelmallamatricula, asignatura__id__in=asignaturas, aprobada=True, status=True).count()
                    cantidadvalidacionaprobadas = RecordAcademico.objects.filter(inscripcion=inscripcion, asignaturamalla__nivelmalla__id__lt=nivelmallaperiodo.id, aprobada=True, status=True).count()
                    if cantidadasignaturasmallas > cantidadvalidacionaprobadas:
                        return JsonResponse({"result": "bad", "mensaje": u"Solo los alumnos que tiene aprobadas todas las materias de los niveles que ha cursado hasta ahora y con notas mayor igual a %s puede solicitar ayudantía de cátedra." % notamaximaperiodo})
                    #Validación de estudiantes solo pueden ser ayudantes de cátedra 3 veces
                    cantidad_ayudantias = eInscripcion.inscripcioncatedra_set.filter(status=True,
                                                                                     estado__in=[2, 4],
                                                                                     estadoinscripcion__in=[1, 2]).values_list('id', flat=True).count()
                    if cantidad_ayudantias >= 3:
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se le permite a los estudiantes ser 3 veces ayudantes de cátedra"})

                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Los alumnos graduados no pueden solicitar ayudantía de cátedra."})

            except Exception as ex:
                pass

        if action == 'validacion_subir':
            try:
                actividadinscripcioncatedra = ActividadInscripcionCatedra.objects.filter(pk=request.POST['idactividad'])[0]
                dias = actividadinscripcioncatedra.inscripcioncatedra.periodocatedra.diasevidencia
                hoy = datetime.now().date()
                fecha = actividadinscripcioncatedra.fecha
                fechahasta = actividadinscripcioncatedra.fecha + + timedelta(days=dias)
                if hoy < fecha:
                    return JsonResponse({"result": "bad", "mensaje": u"Subir evidencia a partir del %s." % fecha})
                if hoy > fechahasta:
                    return JsonResponse({"result": "bad", "mensaje": u"Puede subir evidencia hasta el %s." % fechahasta})
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                pass

        if action == 'validacioncarta':
            try:
                inscripcioncatedra = InscripcionCatedra.objects.filter(pk=request.POST['idinscripcion'])[0]
                if not inscripcioncatedra.archivo:
                    return JsonResponse({"result": "bad", "mensaje": u"Para registrar sus actividades de ayudantia, debe subir su Carta de Compromiso firmada por su docente"})
                return JsonResponse({"result": "ok"})

            except Exception as ex:
                pass

        if action == 'asistencia':
            try:
                inscripcion = Inscripcion.objects.filter(pk=request.POST['idasis'])[0]
                valor = request.POST['valor']
                actividadinscripcioncatedra = ActividadInscripcionCatedra.objects.get(pk=request.POST['idactividad'])
                AsistenciaActividadInscripcionCatedra.objects.filter(actividadinscripcioncatedra=actividadinscripcioncatedra, status=True, inscripcionalumno=inscripcion).delete()
                if valor=='true':
                    asistenciaactividadinscripcioncatedra = AsistenciaActividadInscripcionCatedra(actividadinscripcioncatedra=actividadinscripcioncatedra,
                                                                                                  inscripcionalumno=inscripcion)
                    asistenciaactividadinscripcioncatedra.save(request)
                else:
                    asistenciaactividadinscripcioncatedra = AsistenciaActividadInscripcionCatedra.objects.filter(actividadinscripcioncatedra=actividadinscripcioncatedra,inscripcionalumno=inscripcion)
                log(u'Ingreso Asistencia Ayudantia Catedra, con estado %s : %s' % (valor, asistenciaactividadinscripcioncatedra), request, "add")
                return JsonResponse({"result": "ok"})

            except Exception as ex:
                pass

        if action == 'actividades_pdf':
            try:
                data['inscripcioncatedra'] = inscripcioncatedra = InscripcionCatedra.objects.get(pk=request.POST['idinscripcion'])
                data['actividadinscripcioncatedras'] = inscripcioncatedra.actividadinscripcioncatedra_set.filter(status=True).order_by('-id')
                data['fechahoy'] = datetime.now().date()
                return conviert_html_to_pdf(
                    'alu_ayudantiacatedra/actividades_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as ex:
                pass

        return JsonResponse({"result": "bad", "mensaje": u"Error de datos."})
    else:
        data['title'] = u'Ayudantía  de Cátedra'
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add_old':
                try:
                    data['title'] = u'Solicitud de ayudantía de Cátedra'
                    periodocatedra = PeriodoCatedra.objects.filter(pk=request.GET['idperiodocatedra'])[0]
                    periodolectivo = periodocatedra.periodolectivo
                    matricula = inscripcion.matricula_periodo(periodolectivo)
                    if not matricula:
                        nivelmallamatricula = 10
                    else:
                        nivelmallamatricula = matricula.nivelmalla.id
                    mallainscripcion = inscripcion.malla_inscripcion().malla
                    asignaturas = AsignaturaMalla.objects.values_list('asignatura__id', flat=True).filter(malla__carrera__coordinacion=matricula.inscripcion.coordinacion, nivelmalla__id__lt=nivelmallamatricula, status=True)

                    materia_inscritas = InscripcionCatedra.objects.values_list('materia__asignatura__id', flat=True).filter(status=True, periodocatedra=periodocatedra, inscripcion=inscripcion).exclude(estado=3)
                    # profesormaterias_seleccionas = ProfesorMateria.objects.filter(tipoprofesor__id__in=[1, 2],status=True, materia__status=True,materia__nivel__periodo=periodolectivo,materia__asignaturamalla__malla=mallainscripcion,materia__asignatura__status=True,materia__asignatura__id__in=asignaturas).exclude(materia__asignatura__id__in=materia_inscritas).order_by('materia__asignaturamalla__nivelmalla','materia__asignatura').distinct()
                    profesormaterias_seleccionas = ProfesorMateria.objects.filter(tipoprofesor__id__in=[1, 2],status=True, materia__status=True,materia__nivel__periodo=periodolectivo,materia__asignaturamalla__malla__carrera__coordinacion=matricula.inscripcion.coordinacion,materia__asignatura__status=True,materia__asignatura__id__in=asignaturas).exclude(materia__asignatura__id__in=materia_inscritas).order_by('materia__asignaturamalla__nivelmalla','materia__asignatura').distinct()
                    data['periodocatedra'] = periodocatedra
                    data['profesormaterias_seleccionas'] = profesormaterias_seleccionas
                    return render(request, "alu_ayudantiacatedra/add_old.html", data)
                except Exception as ex:
                    pass

            if action == 'add':
                try:
                    data['title'] = u'Solicitud de ayudantía de Cátedra'
                    eMatricula = inscripcion.matricula_periodo(periodo)
                    #ASIGNATURAS IDS APROBADAS EN EL RECORDS ACADEMICO
                    eHistoricosRecordAcademico = eInscripcion.historicorecordacademico_set.filter(status=True, aprobada=True)
                    idsAsignaturasAprobadas = list(eHistoricosRecordAcademico.values_list('asignatura_id', flat=True).exclude(asignatura_id__isnull=True))
                    idsAsignaturasAprobadasMalla = list(eHistoricosRecordAcademico.values_list('asignaturamalla__asignatura_id', flat=True).exclude(asignaturamalla__asignatura_id__isnull=True))
                    idsAsignaturasAprobadas.extend(idsAsignaturasAprobadasMalla)
                    idsAsignaturasAprobadas = set(idsAsignaturasAprobadas)
                    #ASIGNATURAS FALTANTANTES DE MALLA CURRICULAR
                    eMalla = eInscripcion.mi_malla()
                    idsexcluirasignaturas = eMalla.asignaturamalla_set.exclude(status=True, asignatura_id__in=idsAsignaturasAprobadas).values_list('asignatura_id', flat=True)
                    #SOLICITUDES APROBADAS DE DOCENTES QUE NECESITAN AYUDANTES DE CATEDRAS DE LAS MATERIAS QUE IMPARTEN EN LA COORDINACIÓN DE LA INSCRIPCIÓN
                    eSolicitudesProfesoresCatedras = ePeriodoCatedra.solicitudprofesorcatedra_set.filter(status=True,
                                                                                                         carrera__coordinacion=eInscripcion.coordinacion,
                                                                                                         estado=3).values_list('id', flat=True)
                    #EXCLUIR SOLICTUDES INSCRITAS
                    idsmateriassolicitdas = eInscripcion.inscripcioncatedra_set.filter(status=True).values_list('detallesolicitudprofesorcatedra_id', flat=True)

                    #MATERIAS APROBADAS DE DOCENTES CON AYUDANTES DE CATEDRAS
                    eMateriasSolicitadasProfesorCatedras = DetalleSolicitudProfesorCatedra.objects.filter(status=True,
                                                                                                          materia__asignaturamalla__asignatura_id__in=idsAsignaturasAprobadas,
                                                                                                          solicitud_id__in=eSolicitudesProfesoresCatedras)
                    # EXCLUIR SOLICTUDES INSCRITAS
                    eMateriasSolicitadasProfesorCatedras = eMateriasSolicitadasProfesorCatedras.exclude(id__in=idsmateriassolicitdas)

                    #EXCLUIR ASIGNATURAS EN CURSO Y ASIGNATURAS QUE NO HA VISTO EL ESTUDIANTE
                    eMateriasSolicitadasProfesorCatedras = eMateriasSolicitadasProfesorCatedras.exclude( materia__asignaturamalla__asignatura_id__in=idsexcluirasignaturas)

                    data['eMateriasSolicitadasProfesorCatedras'] = eMateriasSolicitadasProfesorCatedras

                    data['periodocatedra'] = ePeriodoCatedra
                    #data['profesormaterias_seleccionas'] = profesormaterias_seleccionas
                    return render(request, "alu_ayudantiacatedra/add.html", data)
                except Exception as e:
                    pass

            if action == 'registrar':
                try:
                    data['title'] = u'Confirmar Ayudantía de Cátedra'
                    data['eDetalleSolicitudProfesorCatedra'] = DetalleSolicitudProfesorCatedra.objects.get(pk=int(request.GET['idmaterias']))
                    data['periodocatedra'] = ePeriodoCatedra #PeriodoCatedra.objects.filter(pk=request.GET['idperiodocatedra'])[0]
                    return render(request, "alu_ayudantiacatedra/registrar.html", data)
                except:
                    pass

            if action == 'delete':
                try:
                    data['title'] = u'Eliminar Ayudantía de Cátedra'
                    data['inscripcioncatedra'] = InscripcionCatedra.objects.get(pk=request.GET['id'])
                    return render(request, 'alu_ayudantiacatedra/delete.html', data)
                except Exception as ex:
                    pass

            if action == 'actividades':
                try:
                    data['inscripcioncatedra'] = inscripcioncatedra = InscripcionCatedra.objects.get(pk=request.GET['idinscripcion'])
                    data['actividadinscripcioncatedras'] = inscripcioncatedra.actividadinscripcioncatedra_set.filter(status=True).order_by('-id')

                    data['title'] = u'ACTIVIDADES AYUDANTÍA DE CÁTEDRA  - ' + inscripcioncatedra.materia.asignatura.nombre + ' - DOCENTE: ' + inscripcioncatedra.docente.persona.nombre_completo_inverso()

                    return render(request, "alu_ayudantiacatedra/actividades.html", data)
                except Exception as ex:
                    pass

            if action == 'asistencia':
                try:
                    data['actividadinscripcioncatedra'] = actividadinscripcioncatedra = ActividadInscripcionCatedra.objects.get(pk=request.GET['id'])
                    if not actividadinscripcioncatedra.archivoevidencia:
                        return JsonResponse({"result": "bad", "mensaje": u"Puede tomar asistencia despues de subir la evidencia"})
                    data['title'] = u'Asistencia de Ayudantía de Cátedra'
                    data['materiaasignadas'] = MateriaAsignada.objects.filter(status=True, matricula__estado_matricula__in=[2,3], materia=actividadinscripcioncatedra.inscripcioncatedra.materia)
                    data['asistenciaactividadinscripcioncatedra'] = AsistenciaActividadInscripcionCatedra.objects.values_list('inscripcionalumno__id', flat=True).filter(status=True, actividadinscripcioncatedra=actividadinscripcioncatedra)
                    template = get_template("alu_ayudantiacatedra/asistencia.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            if action == 'subirarchivos':
                try:
                    data['title'] = u'Subir evidencia de ayudantía de cátedra'
                    data['actividadinscripcioncatedra'] = actividadinscripcioncatedra = ActividadInscripcionCatedra.objects.get(pk=request.GET['id'])
                    if not actividadinscripcioncatedra.inscripcioncatedra.puederegistraractividad():#SOLO PUEDE REGISTRAR ACTIVIDADES CUANDO ESTÉ DENTRO DEL PERIODO
                        raise('Error')
                    data['form'] = ActividadInscripcionCatedraForm(initial={'actividadevidencia': actividadinscripcioncatedra.actividadevidencia})
                    return render(request, "alu_ayudantiacatedra/subirarchivos.html", data)
                except Exception as ex:
                    pass

            if action == 'subircarta':
                try:
                    data['title'] = u'Subir carta compromiso de ayudantía de cátedra'
                    data['inscripcioncatedra'] = inscripcioncatedra = InscripcionCatedra.objects.get(pk=request.GET['idinscripcion'])
                    data['form'] = InscripcionCatedraArchivoForm()
                    return render(request, "alu_ayudantiacatedra/subircarta.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                eInscripcionesCatedras = eInscripcion.inscripcioncatedra_set.filter(status=True,
                                                                                    periodocatedra=ePeriodoCatedra).order_by('id').distinct()
                data['eInscripcionesCatedra'] = eInscripcionesCatedras

                #data['periodocatedras'] = periodocatedras = PeriodoCatedra.objects.filter(status = True).order_by('-id')
                # idperiodocatedra = 0
                # periodocatedra = None
                # if 'idperiodocatedra' in request.GET:
                #     idperiodocatedra = int(request.GET['idperiodocatedra'])
                #     periodocatedra = PeriodoCatedra.objects.filter(pk=int(idperiodocatedra), status=True)[0]
                # else:
                #     if periodocatedras:
                #         idperiodocatedra = periodocatedras[0].id
                #         periodocatedra = PeriodoCatedra.objects.filter(pk=int(idperiodocatedra), status=True)[0]



                # data['inscripcioncatedras'] = inscripcioncatedras = InscripcionCatedra.objects.filter(status=True,
                #                                                                                       periodocatedra_id=periodocatedra.id,
                #                                                                                       inscripcion=inscripcion).order_by('id').distinct()
                # data['banderacertificado'] = inscripcioncatedras.filter(estadoinscripcion=2).exists()
                #data['periodocatedra'] = periodocatedra
                data['archivos'] = ArchivoGeneralCatedra.objects.filter(status=True, visible=True)
                data['reporte_1'] = obtener_reporte('certificado_ayudantia')
                return render(request, "alu_ayudantiacatedra/view.html", data)
            except Exception as ex:
                pass
