# -*- coding: latin-1 -*-
import random

import xlwt
from django.contrib.auth.context_processors import PermWrapper
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Sum
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from xlwt import *
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from datetime import datetime, timedelta
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import PeriodoCatedraForm, InscripcionCatedraEstadoForm, InscripcionCatedraArchivoForm, \
    SupervisorAyudantiaCatedraForm, ActividadInscripcionCatedraForm, ActividadAyudantiaCatedraForm, \
    InformeAyudanteCatedraEstadoForm, InscripcionCatedraAprobarForm, ArchivoGeneralCatedraForm, \
    SolicitudProfesorCatedraForm
from sga.funciones import MiPaginador, log, generar_nombre, puede_realizar_accion, puede_realizar_accion_afirmativo, \
    puede_realizar_acciones_afirmativo, null_to_numeric
from sga.models import PeriodoCatedra, Carrera, InscripcionCatedra, ActividadInscripcionCatedra, miinstitucion, \
    CUENTAS_CORREOS, ActividadAyudantiaCatedra, InformeAyudanteCatedra, AprobacionInformeAyudanteCatedra, \
    PracticasPreprofesionalesInscripcion, DetalleEvidenciasPracticasPro, ArchivoGeneralCatedra, \
    SolicitudProfesorCatedra, DIAS_CHOICES
from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt

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
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = PeriodoCatedraForm(request.POST)
                if not f.is_valid():
                    errores = []
                    for k, v in f.errors.items():
                        errores.append(f'el campo {k} {v[0]}')
                    raise NameError('\n'.join(errores))
                if not PeriodoCatedra.objects.filter(periodolectivo=f.cleaned_data['periodolectivo']).exists():
                    periodocatedra = PeriodoCatedra(periodolectivo=f.cleaned_data['periodolectivo'],
                                                    nombre=f.cleaned_data['nombre'],
                                                    fechadesde=f.cleaned_data['fechadesde'],
                                                    fechahasta=f.cleaned_data['fechahasta'],
                                                    fechahastaaprobar=f.cleaned_data['fechahastaaprobar'],
                                                    fecharegistroactividad=f.cleaned_data['fecharegistroactividad'],
                                                    horasmaxima=f.cleaned_data['horasmaxima'],
                                                    nivelmalla=f.cleaned_data['nivelmalla'],
                                                    periodoevidencia=f.cleaned_data['periodoevidencia'],
                                                    fechainicio_solicitud_docente=f.cleaned_data['fechainicio_solicitud_docente'],
                                                    fechafin_solicitud_docente=f.cleaned_data['fechafin_solicitud_docente'],
                                                    fechainicio_solicitud_director=f.cleaned_data['fechainicio_solicitud_director'],
                                                    fechafin_solicitud_director=f.cleaned_data['fechafin_solicitud_director'],
                                                    )
                    periodocatedra.save(request)
                    actividades = f.cleaned_data.get('actividades')
                    for actividad in actividades:
                        periodocatedra.actividades.add(actividad)
                    periodocatedra.save(request)
                    log(u'Adiciono Periodo Ayudantia Catedra: %s' % periodocatedra, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Periodo lectivo ya tiene configurado Ayudantia catedra"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"%s" % ex.__str__()})

        if action == 'edit_estado':
            try:
                f = InscripcionCatedraEstadoForm(request.POST)
                if f.is_valid():
                    inscripcioncatedra = InscripcionCatedra.objects.get(pk=int(request.POST['idinscripcion']))
                    inscripcioncatedra.estado = f.cleaned_data['estadoinscripcion']
                    inscripcioncatedra.motivoestado = f.cleaned_data['motivoestado']
                    if int(f.cleaned_data['estadoinscripcion']) == 3:
                        inscripcioncatedra.estadoinscripcion = f.cleaned_data['estadoinscripcion']
                    inscripcioncatedra.save(request)
                    lista = inscripcioncatedra.inscripcion.persona.lista_emails()
                    send_html_mail("Actividad de Ayudantía de Cátedra %s" % inscripcioncatedra.materia.asignatura.nombre,
                                   "emails/solicitud_ayudantia_catedra_aprobacion_vice.html",
                                   {'sistema': request.session['nombresistema'],
                                    'paralelo': inscripcioncatedra.materia.paralelomateria,
                                    'materia': inscripcioncatedra.materia.asignatura,
                                    'docente': inscripcioncatedra.docente.persona.nombre_completo_inverso(),
                                    'motivoestado': inscripcioncatedra.motivoestado,
                                    'estado': inscripcioncatedra.get_estadoinscripcion_display(),
                                    't': miinstitucion()}, lista, [], cuenta=CUENTAS_CORREOS[4][1])
                    log(u'Modifico estado inscripcion de la Inscripcion: %s' % inscripcioncatedra, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'edit_estadoinforme':
            try:
                f = InformeAyudanteCatedraEstadoForm(request.POST)
                if f.is_valid():
                    informe = InformeAyudanteCatedra.objects.get(pk=int(encrypt(request.POST['idinforme'])))
                    informe.estado = int(f.cleaned_data['estado'])
                    if informe.aprobado():
                        if puede_realizar_accion_afirmativo(request, 'sga.puede_gestionar_ayudante_catedra_decano'):
                            informe.aprobadodecano = True
                    elif informe.rechazado():
                        if puede_realizar_accion_afirmativo(request, 'sga.puede_gestionar_ayudante_catedra_decano'):
                            informe.aprobadodecano = False
                    informe.save(request)
                    informe.aprobacioninformeayudantecatedra_set.update(status=False)
                    aprobacion = AprobacionInformeAyudanteCatedra(
                        informe=informe,
                        observacion=f.cleaned_data['observacion'],
                        aprueba=persona,
                        estado=informe.estado,
                        fechaaprobacion=datetime.now()
                    )
                    aprobacion.save(request)
                    log(u'Modifico estado informe del Ayudante: %s' % informe, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'supervisor':
            try:
                f = SupervisorAyudantiaCatedraForm(request.POST)
                if f.is_valid():
                    inscripcioncatedra = InscripcionCatedra.objects.get(pk=int(request.POST['idinscripcion']))
                    inscripcioncatedra.supervisor = f.cleaned_data['supervisor']
                    inscripcioncatedra.save(request)
                    lista = inscripcioncatedra.inscripcion.persona.lista_emails()
                    send_html_mail("Supervisor de Ayudantía de Cátedra %s" % inscripcioncatedra.materia.asignatura.nombre,
                                   "emails/solicitud_ayudantia_catedra_supervisor.html",
                                   {'sistema': request.session['nombresistema'],
                                    'materia': inscripcioncatedra.materia.asignatura,
                                    'paralelo': inscripcioncatedra.materia.paralelomateria,
                                    'docente': inscripcioncatedra.docente.persona.nombre_completo_inverso(),
                                    'estudiante': inscripcioncatedra.inscripcion.persona.nombre_completo_simple(),
                                    't': miinstitucion()}, lista, [], cuenta=CUENTAS_CORREOS[4][1])
                    listaprofesor = inscripcioncatedra.supervisor.persona.emails()
                    send_html_mail("Supervisor de Ayudantía de Cátedra %s" % inscripcioncatedra.materia.asignatura.nombre,
                                   "emails/solicitud_ayudantia_catedra_supervisor.html",
                                   {'sistema': request.session['nombresistema'],
                                    'materia': inscripcioncatedra.materia.asignatura,
                                    'paralelo': inscripcioncatedra.materia.paralelomateria,
                                    'docente': inscripcioncatedra.docente.persona.nombre_completo_inverso(),
                                    'estudiante': inscripcioncatedra.inscripcion.persona.nombre_completo_simple(),
                                    't': miinstitucion()}, listaprofesor, [], cuenta=CUENTAS_CORREOS[4][1])
                    log(u'Modifico estado inscripcion de la Inscripcion: %s' % inscripcioncatedra, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'edit':
            try:
                periodocatedra = PeriodoCatedra.objects.get(pk=request.POST['id'])
                f = PeriodoCatedraForm(request.POST)
                if not f.is_valid():
                    errores = []
                    for k, v in f.errors.items():
                        errores.append(f'el campo {k} {v[0]}')
                    raise NameError('\n'.join(errores))

                periodocatedra.nombre = f.cleaned_data['nombre']
                periodocatedra.fechadesde = f.cleaned_data['fechadesde']
                periodocatedra.fechahasta = f.cleaned_data['fechahasta']
                periodocatedra.horasmaxima = f.cleaned_data['horasmaxima']
                periodocatedra.nivelmalla = f.cleaned_data['nivelmalla']
                periodocatedra.fechahastaaprobar = f.cleaned_data['fechahastaaprobar']
                periodocatedra.fecharegistroactividad = f.cleaned_data['fecharegistroactividad']
                periodocatedra.periodoevidencia = f.cleaned_data['periodoevidencia']
                periodocatedra.fechainicio_solicitud_docente = f.cleaned_data['fechainicio_solicitud_docente']
                periodocatedra.fechafin_solicitud_docente = f.cleaned_data['fechafin_solicitud_docente']
                periodocatedra.fechainicio_solicitud_director = f.cleaned_data['fechainicio_solicitud_docente']
                periodocatedra.fechafin_solicitud_director = f.cleaned_data['fechafin_solicitud_director']
                periodocatedra.save(request)
                actividades = f.cleaned_data.get('actividades')
                for actividad in actividades:
                    periodocatedra.actividades.add(actividad)
                periodocatedra.save(request)
                log(u'Modifico Periodo Ayudantia Catedra: %s' % periodocatedra, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"%s" % ex.__str__()})

        if action == 'delete':
            try:
                periodocatedra = PeriodoCatedra.objects.get(pk=request.POST['id'])
                if periodocatedra.en_uso():
                    return JsonResponse({"result": "bad", "mensaje": u"El registro esta en uso."})
                periodocatedra.status=False
                periodocatedra.save(request)
                log(u'Elimino Periodo Ayudantia Catedra: %s' % periodocatedra, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'segmento':
            try:
                data['carrera'] = carrera = Carrera.objects.get(pk=int(request.POST['carrera']), status=True)
                data['periodocatedra'] = periodocatedra = PeriodoCatedra.objects.filter(pk=request.POST['idperiodo'], status=True)[0]
                data['inscripcioncatedras'] = inscripcioncatedras = InscripcionCatedra.objects.filter(periodocatedra=periodocatedra, inscripcion__carrera=carrera, status=True).order_by('materia__asignaturamalla__nivelmalla', 'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2')
                data['total_inscritos'] = inscripcioncatedras.count()
                data['perms'] = PermWrapper(request.user)
                template = get_template("ayudantiacatedra/segmento.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        elif action == 'subircarta':
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
                        if ext == '.pdf':
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

        if action == 'actividades_pdf':
            try:
                data['inscripcioncatedra'] = inscripcioncatedra = InscripcionCatedra.objects.get(pk=request.POST['idinscripcion'])
                data['actividadinscripcioncatedras'] = inscripcioncatedra.actividadinscripcioncatedra_set.filter(status=True).order_by('-id')
                data['fechahoy'] = datetime.now().date()
                return conviert_html_to_pdf(
                    'ayudantiacatedra/actividades_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as ex:
                pass

        elif action == 'addactividadayudante':
            try:
                form = ActividadAyudantiaCatedraForm(request.POST)
                if form.is_valid():
                    actividad = ActividadAyudantiaCatedra(
                        descripcion=form.cleaned_data['descripcion'].upper()
                    )
                    actividad.save(request)
                    log(u'Adicionó actividad de ayudantía : %s' % (actividad), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "Formulario no válido."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'editactividadayudante':
            try:
                form = ActividadAyudantiaCatedraForm(request.POST)
                if form.is_valid():
                    actividad = ActividadAyudantiaCatedra.objects.get(pk=int(encrypt(request.POST['id'])))
                    actividad.descripcion = form.cleaned_data['descripcion'].upper()
                    actividad.save(request)
                    log(u'Adicionó actividad de ayudantía : %s' % (actividad), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "Formulario no válido."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'delactividadayudante':
            try:
                actividad = ActividadAyudantiaCatedra.objects.get(pk=int(encrypt(request.POST['id'])))
                actividad.status = False
                actividad.save()
                log(u'Cambió estado [status=False] de actividad de ayudante : %s' % actividad, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'aprobarregistrar':
            try:
                inscripcioncatedra = InscripcionCatedra.objects.get(pk=request.POST['idinscripcion'])
                f = InscripcionCatedraAprobarForm(request.POST)
                if f.is_valid():
                    #     guardar en tablas de practicas
                    tutoruniversidad = inscripcioncatedra.docente
                    fechatutor = inscripcioncatedra.fechadesdeaprobado
                    supervisor = None
                    fechasupervisor = None
                    empresaem = 3
                    rotacion = None

                    horas = null_to_numeric(inscripcioncatedra.actividadinscripcioncatedra_set.filter(status=True, estado=2).aggregate(valor=Sum('minutos'))['valor'])
                    hora = 0
                    if horas > 0:
                        hora = int(horas / 60)


                    practicaspreprofesionalesinscripcion = PracticasPreprofesionalesInscripcion(inscripcion=inscripcioncatedra.inscripcion,
                                                                                                tipo=5,
                                                                                                fechadesde=inscripcioncatedra.materia.inicio,
                                                                                                tiposolicitud=2,
                                                                                                empresaempleadora_id=empresaem,
                                                                                                rotacionmalla=rotacion,
                                                                                                culminada=False,
                                                                                                fechahasta=inscripcioncatedra.materia.fin,
                                                                                                tutorunemi=tutoruniversidad,
                                                                                                supervisor=supervisor,
                                                                                                tutorempresa=tutoruniversidad.persona.nombre_completo_simple(),
                                                                                                numerohora=hora,
                                                                                                horahomologacion=0,
                                                                                                otraempresaempleadora='',
                                                                                                # institucion=f.cleaned_data['institucion'],
                                                                                                tipoinstitucion=1,
                                                                                                sectoreconomico=5,
                                                                                                observacion='',
                                                                                                fechaasigtutor=fechatutor,
                                                                                                fechaasigsupervisor=fechasupervisor,
                                                                                                archivo=inscripcioncatedra.archivo,
                                                                                                periodoevidencia=inscripcioncatedra.periodocatedra.periodoevidencia,
                                                                                                estadosolicitud=2)

                    practicaspreprofesionalesinscripcion.save(request)
                    inscripcioncatedra.estadoinscripcion = 2
                    inscripcioncatedra.motivoestado = f.cleaned_data['observacion']
                    inscripcioncatedra.observacionfinal=f.cleaned_data['observacion']
                    inscripcioncatedra.practica=practicaspreprofesionalesinscripcion
                    inscripcioncatedra.save(request)
                    # subir evidencias
                    evidencia = DetalleEvidenciasPracticasPro(evidencia = inscripcioncatedra.periodocatedra.periodoevidencia.evidencias_practica()[0],
                                                              inscripcionpracticas = practicaspreprofesionalesinscripcion,
                                                              # puntaje = f.cleaned_data['puntaje'],
                                                              descripcion = 'INFORME FINAL',
                                                              estadorevision = 1,
                                                              archivo = inscripcioncatedra.informeayudantecatedra_set.all()[0].archivo,
                                                              fechaarchivo = datetime.now(),
                                                              fechainicio = inscripcioncatedra.materia.inicio,
                                                              fechafin = inscripcioncatedra.materia.fin,
                                                              estadotutor = 2,
                                                              obstutor = inscripcioncatedra.observacionfinal)
                    evidencia.save(request)

                    log(u'Adicionado practica preprofesionales inscripcion, por modulo de ayudantía de catedra: %s' % practicaspreprofesionalesinscripcion, request, "add")


                    lista = inscripcioncatedra.inscripcion.persona.lista_emails()
                    send_html_mail("Aprobación Final Ayudantía de Cátedra %s" % inscripcioncatedra.materia.asignatura.nombre,
                                   "emails/solicitud_ayudantia_catedra_aprobacion_final.html",
                                   {'sistema': request.session['nombresistema'],
                                    'paralelo': inscripcioncatedra.materia.paralelomateria,
                                    'materia': inscripcioncatedra.materia.asignatura,
                                    'docente': inscripcioncatedra.docente.persona.nombre_completo_inverso(),
                                    't': miinstitucion()}, lista, [], cuenta=CUENTAS_CORREOS[5][1])
                    log(u'Adiciono Actividad Inscripcion Ayudantia Catedra: %s' % inscripcioncatedra, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addarchivogeneral':
            try:
                form = ArchivoGeneralCatedraForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    newfile = d._name
                    ext = newfile[newfile.rfind("."):]
                    if ext == '.pdf' or ext == '.PDF' or ext == '.doc' or ext == '.docx':
                        a = 1
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf, .doc, .docx."})
                    if d.size > 15728640:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 15 Mb."})
                if form.is_valid():
                    archivogeneral = ArchivoGeneralCatedra(nombre=form.cleaned_data['nombre'],
                                                                            visible=form.cleaned_data['visible'])
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("archivogeneralcatedra", newfile._name)
                        archivogeneral.archivo = newfile
                    archivogeneral.save(request)
                    log(u'Adiciono archivo general de cátedra: %s [%s] - archivo:(%s)' % (
                    archivogeneral, archivogeneral.id, archivogeneral.archivo), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'editarchivogeneral':
            try:
                form = ArchivoGeneralCatedraForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    newfile = d._name
                    ext = newfile[newfile.rfind("."):]
                    if ext == '.pdf' or ext == '.PDF' or ext == '.doc' or ext == '.docx':
                        a = 1
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf, .doc, .docx."})
                    if d.size > 10485760:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                if form.is_valid():
                    archivogeneral = ArchivoGeneralCatedra.objects.get(
                        pk=int(encrypt(request.POST['id'])))
                    archivogeneral.nombre = form.cleaned_data['nombre']
                    archivogeneral.visible = form.cleaned_data['visible']
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("archivogeneralcatedra", newfile._name)
                        archivogeneral.archivo = newfile
                    archivogeneral.save(request)
                    log(u'Edito archivo general de cátedra: %s [%s] - archivo:(%s)' % (
                    archivogeneral, archivogeneral.id, archivogeneral.archivo), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'delarchivogeneral':
            try:
                archivogeneral = ArchivoGeneralCatedra.objects.get(pk=int(encrypt(request.POST['id'])))
                log(u'Elimino archivo general de cátedra: %s [%s] - archivo:(%s)' % (
                archivogeneral, archivogeneral.id, archivogeneral.archivo), request, "del")
                archivogeneral.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        if action == 'loadDataTableSolicitudesProfesorCatedra':
            try:
                txt_filter = request.POST['sSearch'] if request.POST['sSearch'] else ''
                limit = int(request.POST['iDisplayLength']) if request.POST['iDisplayLength'] else 25
                offset = int(request.POST['iDisplayStart']) if request.POST['iDisplayStart'] else 0
                tCount = 0
                periodocatedra_id = int(encrypt(request.POST['periodocatedra_id'])) if 'periodocatedra_id' in request.POST and request.POST['periodocatedra_id'] and int(encrypt(request.POST['periodocatedra_id'])) != 0 else None
                solicitudes = SolicitudProfesorCatedra.objects.filter(status=True, periodocatedra_id=periodocatedra_id)
                if txt_filter:
                    search = txt_filter.strip()
                    solicitudes = solicitudes.filter(Q(descripcion__icontains=search))
                tCount = solicitudes.count()
                if offset == 0:
                    rows = solicitudes[offset:limit]
                else:
                    rows = solicitudes[offset:offset + limit]
                aaData = []
                for row in rows:
                    materias = [{
                        'id': detallesoli.materia.id,
                        'name': u'%s - %s - %s' % (detallesoli.materia.asignaturamalla.asignatura.nombre, detallesoli.materia.paralelomateria.__str__(), detallesoli.materia.nivel.paralelo),
                        'number_students': detallesoli.numero_estudiantes,
                        'horarios': [{
                            'id': horario.id,
                            'dia': horario.get_dia_display(),
                            'horainicio': horario.horainicio.strftime("%H:%M %p"),
                            'horafin': horario.horafin.strftime("%H:%M %p"),
                        }for horario in detallesoli.detallehorariosolicitudprofesorcatedra_set.filter(status=True)]
                    }for detallesoli in row.detallesolicitudprofesorcatedra_set.filter(status=True)]
                    aaData.append([row.numero,
                                   {"id": row.id,
                                    "name": row.__str__(),
                                    "docente": {
                                        'name': row.profesor.__str__(),
                                        'foto': row.profesor.persona.get_foto(),
                                    },
                                    "carrera": row.carrera.__str__(),
                                    },
                                    materias,
                                   {
                                       'estado': row.estado,
                                       'estado_display': row.get_estado_display()
                                   },
                                   {"id": row.id,
                                    "id_encr": encrypt(row.id),
                                    "name": row.__str__(),
                                    "numero": row.numero,
                                    'estado': row.estado,
                                    }
                                   ])
                return JsonResponse({"result": "ok", "data": aaData, "iTotalRecords": tCount, "iTotalDisplayRecords": tCount})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos. %s" % ex.__str__(), "data": [], "iTotalRecords": 0, "iTotalDisplayRecords": 0})

        if action == 'CambiarEstadoSolicitudProfesorCatedra':
            try:
                id = int(encrypt(request.POST['id'])) if 'id' in request.POST and request.POST['id'] and int(encrypt(request.POST['id'])) != 0 else None
                estado = request.POST['estado']
                observacion = request.POST['observacion']
                eSolicitudProfesorCatedra = SolicitudProfesorCatedra.objects.filter(pk=id, status=True).first()
                if eSolicitudProfesorCatedra is None:
                    raise NameError('No se encontro solicitud')
                eSolicitudProfesorCatedra.estado = estado
                eSolicitudProfesorCatedra.observacion = observacion
                eSolicitudProfesorCatedra.save(request)
                log(u'Actualizó estado de ayudante de catedara: %s al siguiente estado %s --> %s' % (eSolicitudProfesorCatedra, eSolicitudProfesorCatedra.get_estado_display(), eSolicitudProfesorCatedra.observacion), request, "edit")
                # eSolicitudFeriaHistorial = SolicitudFeriaHistorial(solicitud=eSolicitudFeria,
                #                                                    observacion=observacion,
                #                                                    estado=eSolicitudFeria.estado)
                # eSolicitudFeriaHistorial.save(request)
                return JsonResponse({"result": "ok", "mensaje": u"Se cambio correctamente el estado de la solicitud"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'PERIODO AYUDANTÍA CATEDRA'
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    # puede_realizar_accion(request, 'sga.puede_modificar_periodo_ayudantia_catedra')
                    data['title'] = u'NUEVO PERIODO AYUDANTÍA CATEDRA'
                    form = PeriodoCatedraForm()
                    form.fields['periodolectivo'].queryset = form.fields['periodolectivo'].queryset.filter(periodocatedra__isnull=True)
                    data['form'] = form
                    return render(request, "ayudantiacatedra/add.html", data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    # puede_realizar_accion(request, 'sga.puede_modificar_periodo_ayudantia_catedra')
                    data['title'] = u'EDITAR PERIODO AYUDANTÍA CATEDRA'
                    data['periodocatedra'] = periodocatedra = PeriodoCatedra.objects.get(pk=request.GET['id'])
                    dict_periodocatedra = model_to_dict(periodocatedra)
                    form = PeriodoCatedraForm(initial=dict_periodocatedra)
                    # form = PeriodoCatedraForm(initial={'periodolectivo': periodocatedra.periodolectivo,
                    #                             'nombre': periodocatedra.nombre,
                    #                             'fechadesde': periodocatedra.fechadesde,
                    #                             'fechahasta': periodocatedra.fechahasta,
                    #                             'fechahastaaprobar': periodocatedra.fechahastaaprobar,
                    #                             'fecharegistroactividad': periodocatedra.fecharegistroactividad,
                    #                             'horasmaxima': periodocatedra.horasmaxima,
                    #                             'nivelmalla': periodocatedra.nivelmalla,
                    #                             'periodoevidencia': periodocatedra.periodoevidencia,
                    #                             'actividades': periodocatedra.actividades.all(),
                    #                             'fechainicio_solicitud_docente': periodocatedra.fechainicio_solicitud_docente,
                    #                             'fechafin_solicitud_docente': periodocatedra.fechafin_solicitud_docente,})
                    form.editar()
                    data['form'] = form
                    return render(request, "ayudantiacatedra/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'delete':
                try:
                    data['title'] = u'ELIMINAR PERIODO AYUDANTÍA CATEDRA'
                    data['periodocatedra'] = PeriodoCatedra.objects.get(pk=request.GET['id'])
                    return render(request, 'ayudantiacatedra/delete.html', data)
                except Exception as ex:
                    pass

            if action == 'seguimiento':
                try:
                    data['periodocatedra'] = periodocatedra = PeriodoCatedra.objects.filter(pk=request.GET['id'], status=True)[0]
                    data['title'] = u'SEGUIMIENTO  - ' + periodocatedra.nombre

                    idcarrera = 0
                    # carrera
                    data['carreras'] = carreras1 = Carrera.objects.filter(inscripcion__inscripcioncatedra__periodocatedra=periodocatedra, inscripcion__inscripcioncatedra__isnull=False, inscripcion__inscripcioncatedra__status=True).distinct()
                    if 'idcarrera' in request.GET:
                        idcarrera = request.GET['idcarrera']
                    else:
                        if carreras1:
                            idcarrera = carreras1[0].id

                    data['idcarrera'] = idcarrera
                    return render(request, "ayudantiacatedra/seguimiento.html", data)
                except Exception as ex:
                    pass

            if action == 'actividades':
                try:
                    data['inscripcioncatedra'] = inscripcioncatedra = InscripcionCatedra.objects.get(pk=request.GET['idinscripcion'])
                    data['actividadinscripcioncatedras'] = inscripcioncatedra.actividadinscripcioncatedra_set.filter(status=True).order_by('-id')
                    data['title'] = u'AYUDANTIA DE CATEDRA  - ' + inscripcioncatedra.materia.asignatura.nombre + ' - ' + inscripcioncatedra.inscripcion.persona.nombre_completo_inverso()

                    template = get_template("ayudantiacatedra/actividades.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            if action == 'verasistencia':
                try:
                    data['actividadinscripcioncatedra'] = actividadinscripcioncatedra = ActividadInscripcionCatedra.objects.get(pk=request.GET['idactividad'])
                    data['asistenciaactividadinscripcioncatedras'] = actividadinscripcioncatedra.asistenciaactividadinscripcioncatedra_set.filter(status=True).order_by('inscripcionalumno__persona__apellido1', 'inscripcionalumno__persona__apellido2')

                    template = get_template("ayudantiacatedra/verasistencia.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            if action == 'descargar':
                try:
                    idperiodo = request.GET['idperiodo']
                    periodocatedra = PeriodoCatedra.objects.get(pk=idperiodo)
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 8, periodocatedra.nombre, title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=ayudantiacatedra_' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"PERIODO LECTIVO", 6000),
                        (u"FACULTAD", 6000),
                        (u"CARRERA", 6000),
                        (u"MATERIA", 6000),
                        (u"DOCENTE", 6000),
                        (u"ALUMNO", 6000),
                        (u"GENERO", 6000),
                        (u"NIVEL ESTUDIANTE", 6000),
                        (u"JORNADA", 6000),
                        (u"CEDULA", 6000),
                        (u"CORREO", 6000),
                        (u"NIVEL QUE POSTULO", 6000),
                        (u"PARALELO QUE POSTULO", 6000),
                        (u"ESTADO DOCENTE", 6000),
                        (u"ESTADO AYUDANTE", 6000),
                        (u"CARTA COMPROMISO", 6000),
                        (u"INFORME FINAL", 6000),
                        (u"ESTADO", 6000),
                        (u"HORAS SOLICITADAS", 6000),
                        (u"HORAS APROBADAS", 6000),
                        (u"HORAS RECHAZADAS", 6000),
                        (u"TIENE SILABO", 6000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]

                    row_num = 4
                    for inscripcioncatedra in InscripcionCatedra.objects.filter(status=True, periodocatedra=periodocatedra):
                        i = 0
                        campo1 = inscripcioncatedra.periodocatedra.periodolectivo.nombre
                        campo2 = inscripcioncatedra.inscripcion.carrera.coordinacion_set.all()[0].nombre
                        campo3 = inscripcioncatedra.inscripcion.carrera.nombre
                        campo4 = inscripcioncatedra.materia.asignatura.nombre
                        campo5 = inscripcioncatedra.docente.persona.nombre_completo_inverso()
                        campo6 = inscripcioncatedra.inscripcion.persona.nombre_completo_inverso()
                        campo7 = inscripcioncatedra.get_estado_display()
                        campo8 = inscripcioncatedra.horas_solicitadas()
                        campo9 = inscripcioncatedra.horas_aprobadas()
                        campo10 = inscripcioncatedra.horas_rechazadas()

                        campo11 = inscripcioncatedra.inscripcion.persona.sexo.nombre
                        campo12 = ''
                        if inscripcioncatedra.matricula:
                            campo12 = inscripcioncatedra.matricula.nivelmalla.nombre
                        campo13 = inscripcioncatedra.inscripcion.sesion.nombre
                        campo14 = inscripcioncatedra.inscripcion.persona.cedula
                        campo15 = inscripcioncatedra.inscripcion.persona.emails()
                        campo16 = inscripcioncatedra.materia.asignaturamalla.nivelmalla.nombre
                        campo17 = inscripcioncatedra.materia.paralelo
                        campo18 = inscripcioncatedra.get_estado_display()
                        campo19 = inscripcioncatedra.get_estadoinscripcion_display()
                        campo20 = inscripcioncatedra.cartacompromiso()
                        campo21 = inscripcioncatedra.informefinal()
                        campo22 = 'NO'
                        if inscripcioncatedra.materia.tiene_silabo_digital():
                            campo22 = 'SI'


                        ws.write(row_num, 0, campo1, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                        ws.write(row_num, 3, campo4, font_style2)
                        ws.write(row_num, 4, campo5, font_style2)
                        ws.write(row_num, 5, campo6, font_style2)
                        ws.write(row_num, 6, campo11, font_style2)
                        ws.write(row_num, 7, campo12, font_style2)
                        ws.write(row_num, 8, campo13, font_style2)
                        ws.write(row_num, 9, campo14, font_style2)
                        ws.write(row_num, 10, campo15, font_style2)
                        ws.write(row_num, 11, campo16, font_style2)
                        ws.write(row_num, 12, campo17, font_style2)
                        ws.write(row_num, 13, campo18, font_style2)
                        ws.write(row_num, 14, campo19, font_style2)
                        ws.write(row_num, 15, campo20, font_style2)
                        ws.write(row_num, 16, campo21, font_style2)
                        ws.write(row_num, 17, campo7, font_style2)
                        ws.write(row_num, 18, campo8, font_style2)
                        ws.write(row_num, 19, campo9, font_style2)
                        ws.write(row_num, 20, campo10, font_style2)
                        ws.write(row_num, 21, campo22, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            if action == 'edit_estado':
                try:
                    data['title'] = u'APROBAR O NEGAR AYUDANTIA CATEDRA'
                    data['inscripcioncatedra'] = inscripcioncatedra = InscripcionCatedra.objects.get(pk=int(request.GET['idinscripcion']))
                    data['periodocatedra'] = PeriodoCatedra.objects.get(pk=int(request.GET['idperiodo']))
                    data['idcarrera'] = request.GET['idcarrera']
                    form = InscripcionCatedraEstadoForm(initial={'estadoinscripcion': inscripcioncatedra.estadoinscripcion})
                    data['form'] = form
                    return render(request, "ayudantiacatedra/edit_estado.html", data)
                except Exception as ex:
                    pass

            if action == 'edit_estadoinforme':
                try:
                    if not(puede_realizar_accion_afirmativo(request, 'sga.puede_gestionar_ayudante_catedra_decano') or puede_realizar_accion_afirmativo(request, 'sga.puede_gestionar_ayudante_catedra_vinculacion')):
                        raise Exception('Permiso denegado.')
                    data['title'] = u'APROBAR O NEGAR INFORME AYUDANTIA CATEDRA'
                    data['informe'] = informe = InformeAyudanteCatedra.objects.get(pk=int(encrypt(request.GET['idinforme'])))
                    data['periodocatedra'] = PeriodoCatedra.objects.get(pk=int(request.GET['idperiodo']))
                    data['idcarrera'] = request.GET['idcarrera']
                    form = InformeAyudanteCatedraEstadoForm(initial={'estado': informe.estado})
                    data['form'] = form
                    return render(request, "ayudantiacatedra/edit_estadoinforme.html", data)
                except Exception as ex:
                    pass

            elif action == 'veraprobacioninforme':
                try:
                    data['informe'] = informe = InformeAyudanteCatedra.objects.get(pk=int(encrypt(request.GET['idinforme'])))
                    data['aprobacion'] = informe.aprobacioninformeayudantecatedra_set.all().order_by('-id')
                    return render(request, "ayudantiacatedra/modalveraprobacioninforme.html", data)
                except Exception as ex:
                    pass

            if action == 'supervisor':
                try:
                    data['title'] = u'SUPERVISOR AYUDANTIA CATEDRA'
                    data['inscripcioncatedra'] = inscripcioncatedra = InscripcionCatedra.objects.get(pk=int(request.GET['idinscripcion']))
                    data['periodocatedra'] = periodocatedra = PeriodoCatedra.objects.get(pk=int(request.GET['idperiodo']))
                    data['idcarrera'] = request.GET['idcarrera']
                    form = SupervisorAyudantiaCatedraForm()
                    form.ingresar(periodocatedra.periodolectivo)
                    data['form'] = form
                    return render(request, "ayudantiacatedra/supervisor.html", data)
                except Exception as ex:
                    pass

            elif action == 'subircarta':
                try:
                    data['title'] = u'Subir carta compromiso de ayudantía de cátedra'
                    data['idperiodo']=request.GET['idperiodo']
                    data['idcarrera']=request.GET['idcarrera']
                    data['inscripcioncatedra'] = inscripcioncatedra = InscripcionCatedra.objects.get(pk=request.GET['idinscripcion'])
                    data['form'] = InscripcionCatedraArchivoForm()
                    return render(request, "ayudantiacatedra/subircarta.html", data)
                except Exception as ex:
                    pass

            elif action == 'actividadayudante':
                try:
                    data['title'] = u'Actividad de ayudante'
                    search = None
                    actividad = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        if search.isdigit():
                            actividad = ActividadAyudantiaCatedra.objects.filter(pk=search, status=True)
                        else:
                            if search:
                                actividad = ActividadAyudantiaCatedra.objects.filter(Q(actividad__icontains=search), Q(status=True))
                            else:
                                actividad = ActividadAyudantiaCatedra.objects.filter(status=True)
                    else:
                        actividad = ActividadAyudantiaCatedra.objects.filter(status=True)
                    paging = MiPaginador(actividad, 25)
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
                    data['actividades'] = page.object_list
                    data['search'] = search if search else ""
                    return render(request, "ayudantiacatedra/viewactividadayudante.html", data)
                except Exception as ex:
                    pass

            elif action == 'addactividadayudante':
                try:
                    data['title'] = u'Adicionar actividad de ayudante'
                    data['form'] = ActividadAyudantiaCatedraForm()
                    return render(request, "ayudantiacatedra/addactividadayudante.html", data)
                except Exception as ex:
                    pass

            elif action == 'editactividadayudante':
                try:
                    data['title'] = u'Editar actividad de ayudante'
                    data['actividad'] = actividad = ActividadAyudantiaCatedra.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['form'] = ActividadAyudantiaCatedraForm(initial={'descripcion': actividad.descripcion})
                    return render(request, "ayudantiacatedra/editactividadayudante.html", data)
                except Exception as ex:
                    pass

            elif action == 'delactividadayudante':
                try:
                    data['title'] = u'Eliminar actividad de ayudante'
                    data['actividad'] = ActividadAyudantiaCatedra.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "ayudantiacatedra/delactividadayudante.html", data)
                except Exception as ex:
                    pass

            elif action == 'excelayudantecarrera':
                try:
                    __author__ = 'Unemi'
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('practicas')
                    ws.write_merge(0, 0, 0, 9, 'REPORTE DE AYUDANTÍA DE CÁTEDRA', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=Listas_ayudante_carrera' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"N°", 1000),
                        (u"ESTUDIANTE", 10000),
                        (u"NIVEL", 3000),
                        (u"ACTIVIDADES DESARROLLADAS", 15000),
                        (u"HORAS ACREDITADAS", 5000),
                        (u"PROFESOR(A)", 10000),
                        (u"ESTADO", 6000),
                        (u"HORAS SOLICITADAS", 6000),
                        (u"HORAS APROBADAS", 6000),
                        (u"HORAS RECHAZADAS", 6000)
                    ]
                    row_num = 2
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    idcarrera = int(request.GET['idcarrera'])
                    idperiodo = int(request.GET['idperiodo'])
                    carrera = Carrera.objects.get(id=idcarrera)
                    ws.write_merge(1, 1, 0, 1, "CARRERA:", font_style)
                    ws.write_merge(1, 1, 2, 5, carrera.nombre_completo())
                    periodocatedra = PeriodoCatedra.objects.get(id=idperiodo)
                    listainscripcion = InscripcionCatedra.objects.filter(periodocatedra=periodocatedra, inscripcion__carrera=carrera)#ESTADO APROBADO|2
                    row_num = 3
                    for index,inscripcioncatedra in enumerate(listainscripcion):
                        campo1 = index+1
                        campo2 = inscripcioncatedra.inscripcion.persona.nombre_completo()
                        campo3 = inscripcioncatedra.matricula.nivelmalla.__str__()
                        actividadinscripcioncatedra = inscripcioncatedra.actividadinscripcioncatedra_set.all()
                        actividades = []
                        for aic in actividadinscripcioncatedra:
                            if aic.actividadModel:
                                actividades.append(aic.actividadModel.descripcion)
                            else:
                                actividades.append(aic.actividad)
                        campo4 = '\n'.join(actividades)
                        campo5 = inscripcioncatedra.horas_aprobadas()
                        campo6 = inscripcioncatedra.docente.persona.nombre_completo()
                        campo7 = inscripcioncatedra.get_estado_display()
                        campo8 = inscripcioncatedra.horas_solicitadas()
                        campo9 = inscripcioncatedra.horas_aprobadas()
                        campo10 = inscripcioncatedra.horas_rechazadas()
                        ws.write(row_num, 0, campo1, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                        ws.write(row_num, 3, campo4, font_style2)
                        ws.write(row_num, 4, campo5, font_style2)
                        ws.write(row_num, 5, campo6, font_style2)
                        ws.write(row_num, 6, campo7, font_style2)
                        ws.write(row_num, 7, campo8, font_style2)
                        ws.write(row_num, 8, campo9, font_style2)
                        ws.write(row_num, 9, campo10, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'excelayudantefacultad':
                try:
                    __author__ = 'Unemi'
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('practicas')
                    ws.write_merge(0, 0, 0, 10, 'REPORTE DE AYUDANTÍA DE CÁTEDRA', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=Listas_ayudante_facultad' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"N°", 1000),
                        (u"ESTUDIANTE", 10000),
                        (u"CARRERA", 10000),
                        (u"NIVEL", 3000),
                        (u"ACTIVIDADES DESARROLLADAS", 15000),
                        (u"HORAS ACREDITADAS", 5000),
                        (u"PROFESOR(A)", 10000),
                        (u"ESTADO", 6000),
                        (u"HORAS SOLICITADAS", 6000),
                        (u"HORAS APROBADAS", 6000),
                        (u"HORAS RECHAZADAS", 6000)
                    ]
                    row_num = 2
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    idcarrera = int(request.GET['idcarrera'])
                    idperiodo = int(request.GET['idperiodo'])
                    carrera = Carrera.objects.get(id=idcarrera)
                    coordinacion = carrera.coordinacion_carrera()
                    ws.write_merge(1, 1, 0, 1, "FACULTAD:", font_style)
                    ws.write_merge(1, 1, 2, 10, coordinacion.nombre)
                    periodocatedra = PeriodoCatedra.objects.get(id=idperiodo)
                    listainscripcion = InscripcionCatedra.objects.filter(periodocatedra=periodocatedra, inscripcion__coordinacion=coordinacion)#ESTADO APROBADO|2
                    row_num = 3
                    for index,inscripcioncatedra in enumerate(listainscripcion):
                        campo1 = index+1
                        campo2 = inscripcioncatedra.inscripcion.persona.nombre_completo()
                        campo3 = inscripcioncatedra.matricula.nivelmalla.__str__()
                        actividadinscripcioncatedra = inscripcioncatedra.actividadinscripcioncatedra_set.all()
                        actividades = []
                        for aic in actividadinscripcioncatedra:
                            if aic.actividadModel:
                                actividades.append(aic.actividadModel.descripcion)
                            else:
                                actividades.append(aic.actividad)
                        campo4 = '\n'.join(actividades)
                        campo5 = inscripcioncatedra.horas_aprobadas()
                        campo6 = inscripcioncatedra.docente.persona.nombre_completo()
                        campo7 = inscripcioncatedra.inscripcion.carrera.nombre_completo()
                        campo8 = inscripcioncatedra.get_estado_display()
                        campo9 = inscripcioncatedra.horas_solicitadas()
                        campo10 = inscripcioncatedra.horas_aprobadas()
                        campo11 = inscripcioncatedra.horas_rechazadas()
                        ws.write(row_num, 0, campo1, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 3, campo3, font_style2)
                        ws.write(row_num, 4, campo4, font_style2)
                        ws.write(row_num, 5, campo5, font_style2)
                        ws.write(row_num, 6, campo6, font_style2)
                        ws.write(row_num, 2, campo7, font_style2)
                        ws.write(row_num, 7, campo7, font_style2)
                        ws.write(row_num, 8, campo8, font_style2)
                        ws.write(row_num, 9, campo9, font_style2)
                        ws.write(row_num, 10, campo10, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'excelayudantetodo':
                try:
                    __author__ = 'Unemi'
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('practicas')
                    ws.write_merge(0, 0, 0, 11, 'REPORTE DE AYUDANTÍA DE CÁTEDRA', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=Listas_ayudante_todo' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"N°", 1000),
                        (u"ESTUDIANTE", 10000),
                        (u"FACULTAD", 10000),
                        (u"CARRERA", 10000),
                        (u"NIVEL", 3000),
                        (u"ACTIVIDADES DESARROLLADAS", 15000),
                        (u"HORAS ACREDITADAS", 5000),
                        (u"PROFESOR(A)", 10000),
                        (u"ESTADO", 6000),
                        (u"HORAS SOLICITADAS", 6000),
                        (u"HORAS APROBADAS", 6000),
                        (u"HORAS RECHAZADAS", 6000)
                    ]
                    row_num = 1
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    idperiodo = int(request.GET['idperiodo'])
                    periodocatedra = PeriodoCatedra.objects.get(id=idperiodo)
                    listainscripcion = InscripcionCatedra.objects.filter(periodocatedra=periodocatedra)#ESTADO APROBADO|2
                    row_num = 2
                    for index,inscripcioncatedra in enumerate(listainscripcion):
                        campo1 = index+1
                        campo2 = inscripcioncatedra.inscripcion.persona.nombre_completo()
                        campo3 = inscripcioncatedra.matricula.nivelmalla.__str__()
                        actividadinscripcioncatedra = inscripcioncatedra.actividadinscripcioncatedra_set.all()
                        actividades = []
                        for aic in actividadinscripcioncatedra:
                            if aic.actividadModel:
                                actividades.append(aic.actividadModel.descripcion)
                            else:
                                actividades.append(aic.actividad)
                        campo4 = '\n'.join(actividades)
                        campo5 = inscripcioncatedra.horas_aprobadas()
                        campo6 = inscripcioncatedra.docente.persona.nombre_completo()
                        campo7 = inscripcioncatedra.inscripcion.carrera.nombre_completo()
                        campo8 = inscripcioncatedra.inscripcion.carrera.coordinacion_carrera().nombre
                        campo9 = inscripcioncatedra.get_estado_display()
                        campo10 = inscripcioncatedra.horas_solicitadas()
                        campo11 = inscripcioncatedra.horas_aprobadas()
                        campo12 = inscripcioncatedra.horas_rechazadas()
                        ws.write(row_num, 0, campo1, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 4, campo3, font_style2)
                        ws.write(row_num, 5, campo4, font_style2)
                        ws.write(row_num, 6, campo5, font_style2)
                        ws.write(row_num, 7, campo6, font_style2)
                        ws.write(row_num, 3, campo7, font_style2)
                        ws.write(row_num, 2, campo8, font_style2)
                        ws.write(row_num, 8, campo9, font_style2)
                        ws.write(row_num, 9, campo10, font_style2)
                        ws.write(row_num, 10, campo11, font_style2)
                        ws.write(row_num, 11, campo12, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'aprobarregistrar':
                try:
                    data['inscripcioncatedra'] = inscripcioncatedra = InscripcionCatedra.objects.get(pk=request.GET['idinscripcion'])
                    data['carrera'] = inscripcioncatedra.inscripcion.carrera
                    data['periodo'] = inscripcioncatedra.periodocatedra
                    data['title'] = u'Aprobar ayudantia'
                    materia = inscripcioncatedra.materia
                    form = InscripcionCatedraAprobarForm()
                    data['form'] = form
                    return render(request, "ayudantiacatedra/aprobarregistrar.html", data)
                except Exception as ex:
                    pass

            elif action == 'archivogeneral':
                try:
                    data['title'] = u'Archivos generales'
                    search = None
                    archivogeneral = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        if search.isdigit():
                            archivogeneral = ArchivoGeneralCatedra.objects.filter(pk=search,
                                                                                                   status=True)
                        else:
                            if ' ' in search:
                                s = search.split(" ")
                                if len(s) == 1:
                                    archivogeneral = ArchivoGeneralCatedra.objects.filter(
                                        Q(nombre__icontains=s[0]), Q(status=True))
                                elif len(s) == 2:
                                    archivogeneral = ArchivoGeneralCatedra.objects.filter(
                                        Q(nombre__icontains=s[0]) & Q(nombre__icontains=s[1]) & Q(status=True))
                                elif len(s) == 3:
                                    archivogeneral = ArchivoGeneralCatedra.objects.filter(
                                        Q(nombre__icontains=s[0]) & Q(nombre__icontains=s[1]) & Q(
                                            nombre__icontains=s[2]), Q(status=True))
                            else:
                                archivogeneral = ArchivoGeneralCatedra.objects.filter(status=True)
                    else:
                        archivogeneral = ArchivoGeneralCatedra.objects.filter(status=True)
                    paging = MiPaginador(archivogeneral, 25)
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
                    data['archivogenerales'] = page.object_list
                    data['search'] = search if search else ""
                    return render(request, "ayudantiacatedra/viewarchivogeneral.html", data)
                except Exception as ex:
                    pass

            elif action == 'addarchivogeneral':
                try:
                    data['title'] = u'Adicionar archivos generales'
                    data['form'] = ArchivoGeneralCatedraForm()
                    return render(request, "ayudantiacatedra/addarchivogeneral.html", data)
                except Exception as ex:
                    pass

            elif action == 'editarchivogeneral':
                try:
                    data['title'] = u'Editar archivos generales'
                    data['archivogeneral'] = archivogeneral = ArchivoGeneralCatedra.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    data['form'] = ArchivoGeneralCatedraForm(
                        initial={'nombre': archivogeneral.nombre, 'visible': archivogeneral.visible})
                    return render(request, "ayudantiacatedra/editarchivogeneral.html", data)
                except Exception as ex:
                    pass

            elif action == 'delarchivogeneral':
                try:
                    data['title'] = u'Eliminar archivos generales'
                    data['archivogeneral'] = ArchivoGeneralCatedra.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    return render(request, "ayudantiacatedra/delarchivogeneral.html", data)
                except Exception as ex:
                    pass

            elif action == 'viewsolictudesprofesorcatedra':
                try:
                    data['title'] = u'Solicitudes de Ayudentes de catedra'
                    data['dias'] = DIAS_CHOICES
                    ePeridoCatedra = PeriodoCatedra.objects.get(id=int(encrypt(request.GET['id'])))
                    data['ePeriodoCatedra'] = ePeridoCatedra
                    return render(request, "ayudantiacatedra/viewsolictudesprofesorcatedra.html", data)
                except Exception as ex:
                    pass

            if action == 'loadFormSolicitudProfesorCatedra':
                try:
                    data['title'] = u'Adicionar informe ayudante'
                    typeForm = request.GET['typeForm'] if 'typeForm' in request.GET and request.GET['typeForm'] and str(request.GET['typeForm']) in ['new', 'edit', 'view'] else None
                    if typeForm is None:
                        raise NameError(u"No se encontro el tipo de formulario")
                    form = SolicitudProfesorCatedraForm()
                    eSolicitudPofesorCatedra = None
                    id=0
                    #idscarrdocente = profesor.mis_materias(periodo).values_list('materia__asignaturamalla__malla__carrera_id', flat=True).distinct()
                    #form.fields['carrera'].queryset = form.fields['carrera'].queryset.filter(pk__in=idscarrdocente)
                    eMaterias = []
                    if typeForm in ['edit', 'view']:
                        id = int(encrypt(request.GET['id'])) if 'id' in request.GET and encrypt(request.GET['id']) and int(encrypt(request.GET['id'])) != 0 else None
                        eSolicitudPofesorCatedra = SolicitudProfesorCatedra.objects.filter(pk=id, status=True).first()
                        if eSolicitudPofesorCatedra is None:
                            raise NameError(u"No solicitud con el parametro id")
                        form.initial = model_to_dict(eSolicitudPofesorCatedra)
                        if typeForm == 'edit':
                            form.editar()
                        if typeForm == 'view':
                            form.view()
                        for eMateria in eSolicitudPofesorCatedra.detalle_materias():
                            eMateriaHorariodict = [
                                {
                                    'idh': horario.id,
                                    'dia': horario.dia,
                                    'horainicio': horario.horainicio.strftime("%H:%M"),
                                    'horafin': horario.horafin.strftime("%H:%M"),
                                }for horario in eMateria.detalle_horario()
                            ]
                            eMateriadict = {
                                'id': eMateria.materia_id,
                                'name': eMateria.__str__(),
                                'text': u'%s - %s' % (eMateria.materia.asignaturamalla.asignatura.nombre, eMateria.materia.paralelomateria.__str__()),
                                'paralelo': eMateria.materia.paralelomateria.__str__(),
                                'horarios': eMateriaHorariodict,
                                'detalle_id': eMateria.id,
                                'numero_estudiantes': eMateria.numero_estudiantes,
                            }
                            eMaterias.append(eMateriadict)
                    else:
                        pass
                    data['form'] = form
                    data['frmName'] = "frmSolicitudProfesorCatedra"
                    data['typeForm'] = typeForm
                    data['id'] = encrypt(id)
                    data['eSolicitudPofesorCatedra'] = eSolicitudPofesorCatedra
                    template = get_template("ayudantiacatedra/frmSolicitudProfesorCatedra.html")
                    json_content = template.render(data, request=request)
                    return JsonResponse({"result": "ok", 'html': json_content, 'eMaterias': eMaterias})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"%s" % ex.__str__()})
            return HttpResponseRedirect(request.path)
        else:
            search = None
            ids = None
            if 'id' in request.GET:
                ids = request.GET['id']
                periodocatedras = PeriodoCatedra.objects.filter(id=ids, status=True).order_by('-id').distinct()
            elif 's' in request.GET:
                search = request.GET['s']
                periodocatedras = PeriodoCatedra.objects.filter(nombre__icontains=search, status=True).order_by('-id').distinct()
            else:
                periodocatedras = PeriodoCatedra.objects.filter(status=True).order_by('-id').distinct()
            paging = MiPaginador(periodocatedras, 25)
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
            data['periodocatedras'] = page.object_list
            return render(request, "ayudantiacatedra/view.html", data)