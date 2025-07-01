# -*- coding: latin-1 -*-
import json
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum, Q, F
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from sga.funcionesxhtml2pdf import conviert_html_to_pdf, conviert_html_to_pdfsaveinformeayudante
from django.template.loader import get_template
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import ActividadInscripcionCatedraRegistrarForm, ActividadInscripcionCatedraRechazarForm, \
    ActividadInscripcionCatedraAprobarForm, InscripcionCatedraAprobarForm, InformeAyudanteCatedraForm, SolicitudProfesorCatedraForm
from sga.funciones import log, generar_nombre, variable_valor
from sga.models import InscripcionCatedra, ActividadInscripcionCatedra, PeriodoCatedra, Inscripcion, NivelMalla, \
    EjeFormativo, AsignaturaMalla, Silabo, BibliografiaProgramaAnaliticoAsignatura, ContenidoResultadoProgramaAnalitico, \
    SilaboActividadInscripcionCatedra, SubtemaUnidadResultadoProgramaAnalitico, TemaUnidadResultadoProgramaAnalitico, \
    null_to_numeric, miinstitucion, CUENTAS_CORREOS, PracticasPreprofesionalesInscripcion, \
    EvidenciaPracticasProfesionales, DetalleEvidenciasPracticasPro, InformeAyudanteCatedra, \
    ConclusionInformeAyudanteCatedra, ProfesorDistributivoHoras, AprobacionInformeAyudanteCatedra, SolicitudProfesorCatedra, Materia,\
    DIAS_CHOICES, DetalleSolicitudProfesorCatedra, DetalleHorarioSolicitudProfesorCatedra
from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt


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
    periodocatedra = periodo.periodocatedra_set.filter(status=True).first()
    if periodocatedra is None:
        return HttpResponseRedirect(f"/?info=No existe periodo catedra configurado")
    perfilprincipal = request.session['perfilprincipal']
    profesor = perfilprincipal.profesor
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'aprobarregistrar':
            try:
                inscripcioncatedra = InscripcionCatedra.objects.get(pk=request.POST['idinscripcion'])
                form = InscripcionCatedraAprobarForm(request.POST, request.FILES)
                if 'archivofinal' in request.FILES:
                    d = request.FILES['archivofinal']
                    if d.size > 6291456:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                    else:
                        newfiles = request.FILES['archivofinal']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if ext == '.pdf' or  ext == '.doc' or ext == '.docx' :
                            a = 1
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf,.doc,docx."})
                else:
                        return JsonResponse({"result": "bad", "mensaje": u"No existe archivo"})

                if form.is_valid():
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
                    inscripcioncatedra.observacionfinal=form.cleaned_data['observacion']
                    inscripcioncatedra.practica=practicaspreprofesionalesinscripcion
                    if 'archivofinal' in request.FILES:
                        newfile = request.FILES['archivofinal']
                        newfile._name = generar_nombre("informe_final_", newfile._name)
                        inscripcioncatedra.archivofinal = newfile
                    inscripcioncatedra.save(request)

                    # subir evidencias
                    evidencia = DetalleEvidenciasPracticasPro(evidencia = inscripcioncatedra.periodocatedra.periodoevidencia.evidencias_practica()[0],
                                                              inscripcionpracticas = practicaspreprofesionalesinscripcion,
                                                              puntaje = form.cleaned_data['puntaje'],
                                                              descripcion = 'INFORME FINAL',
                                                              estadorevision = 1,
                                                              archivo = inscripcioncatedra.archivofinal,
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

        if action == 'add':
            try:
                inscripcioncatedra = InscripcionCatedra.objects.get(pk=request.POST['idinscripcion'])
                if not inscripcioncatedra.puederegistraractividad():  # SOLO PUEDE REGISTRAR ACTIVIDADES CUANDO ESTÉ DENTRO DEL PERIODO
                    raise ('Error')
                temas = json.loads(request.POST['lista_items2'])
                subtemas = json.loads(request.POST['lista_items1'])
                form = ActividadInscripcionCatedraRegistrarForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    if d.size > 6291456:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if ext == '.pdf' or  ext == '.doc' or ext == '.docx' :
                            a = 1
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf,.doc,docx."})
                else:
                        return JsonResponse({"result": "bad", "mensaje": u"No existe archivo"})
                if form.is_valid():
                    actividadinscripcioncatedra = ActividadInscripcionCatedra(inscripcioncatedra=inscripcioncatedra,
                                                                              fecha=form.cleaned_data['fecha'],
                                                                              horadesde=form.cleaned_data['horadesde'],
                                                                              horahasta=form.cleaned_data['horahasta'],
                                                                              actividadModel=form.cleaned_data['actividadModel'])
                    actividadinscripcioncatedra.save(request)
                    horas_actividades = null_to_numeric(ActividadInscripcionCatedra.objects.filter(inscripcioncatedra=inscripcioncatedra, status=True).exclude(estado=3).aggregate(minutos=Sum('minutos'))['minutos'])
                    horasmaximas = int(periodocatedra.horasmaxima)*60
                    if horas_actividades > horasmaximas:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"El limite de horas de ayudantia de catedra son %s" % (horasmaximas/60)})


                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("tutoria_", newfile._name)
                        actividadinscripcioncatedra.archivo = newfile
                        actividadinscripcioncatedra.save()
                    for subtema in subtemas:
                        subtemaunidadresultadoprogramaanalitico = SubtemaUnidadResultadoProgramaAnalitico.objects.filter(pk=int(subtema))[0]
                        temaunidadresultadoprogramaanalitico = subtemaunidadresultadoprogramaanalitico.temaunidadresultadoprogramaanalitico
                        silaboactividadinscripcioncatedra = SilaboActividadInscripcionCatedra(actividadinscripcioncatedra=actividadinscripcioncatedra,
                                                                                              temaunidadresultadoprogramaanalitico=temaunidadresultadoprogramaanalitico,
                                                                                              subtemaunidadresultadoprogramaanalitico=subtemaunidadresultadoprogramaanalitico )
                        silaboactividadinscripcioncatedra.save(request)
                    for tema in temas:
                        temaunidadresultadoprogramaanalitico = TemaUnidadResultadoProgramaAnalitico.objects.filter(pk=int(tema))[0]
                        if not SilaboActividadInscripcionCatedra.objects.filter(temaunidadresultadoprogramaanalitico=temaunidadresultadoprogramaanalitico).exists():
                            silaboactividadinscripcioncatedra = SilaboActividadInscripcionCatedra(actividadinscripcioncatedra=actividadinscripcioncatedra,
                                                                                                  temaunidadresultadoprogramaanalitico=temaunidadresultadoprogramaanalitico)
                            silaboactividadinscripcioncatedra.save(request)
                    lista = inscripcioncatedra.inscripcion.persona.lista_emails()
                    send_html_mail("Nueva Actividad de Ayudantía de Cátedra %s" % inscripcioncatedra.materia.asignatura.nombre,
                                   "emails/solicitud_ayudantia_catedra_nueva_actividad.html",
                                   {'sistema': request.session['nombresistema'],
                                    'paralelo': inscripcioncatedra.materia.paralelomateria,
                                    'materia': inscripcioncatedra.materia.asignatura,
                                    'docente': inscripcioncatedra.docente.persona.nombre_completo_inverso(),
                                    't': miinstitucion()}, lista, [], cuenta=CUENTAS_CORREOS[5][1])
                    log(u'Adiciono Actividad Inscripcion Ayudantia Catedra: %s' % actividadinscripcioncatedra, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editar':
            try:

                actividadinscripcioncatedra = ActividadInscripcionCatedra.objects.get(pk=request.POST['idactividadinscripcion'])
                inscripcioncatedra = actividadinscripcioncatedra.inscripcioncatedra
                temas = json.loads(request.POST['lista_items2'])
                subtemas = json.loads(request.POST['lista_items1'])
                form = ActividadInscripcionCatedraRegistrarForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    if d.size > 6291456:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if ext == '.pdf' or  ext == '.doc' or ext == '.docx' :
                            a = 1
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf,.doc,docx."})
                if form.is_valid():
                    actividadinscripcioncatedra.fecha=form.cleaned_data['fecha']
                    actividadinscripcioncatedra.horadesde=form.cleaned_data['horadesde']
                    actividadinscripcioncatedra.horahasta=form.cleaned_data['horahasta']
                    actividadinscripcioncatedra.actividadModel=form.cleaned_data['actividadModel']
                    actividadinscripcioncatedra.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("tutoria_", newfile._name)
                        actividadinscripcioncatedra.archivo = newfile
                        actividadinscripcioncatedra.save()
                    SilaboActividadInscripcionCatedra.objects.filter(actividadinscripcioncatedra=actividadinscripcioncatedra).delete()
                    for subtema in subtemas:
                        if subtema:
                            subtemaunidadresultadoprogramaanalitico = SubtemaUnidadResultadoProgramaAnalitico.objects.filter(pk=int(subtema))[0]
                            temaunidadresultadoprogramaanalitico = subtemaunidadresultadoprogramaanalitico.temaunidadresultadoprogramaanalitico
                            silaboactividadinscripcioncatedra = SilaboActividadInscripcionCatedra(actividadinscripcioncatedra=actividadinscripcioncatedra,
                                                                                                  temaunidadresultadoprogramaanalitico=temaunidadresultadoprogramaanalitico,
                                                                                                  subtemaunidadresultadoprogramaanalitico=subtemaunidadresultadoprogramaanalitico )
                            silaboactividadinscripcioncatedra.save(request)
                    for tema in temas:
                        temaunidadresultadoprogramaanalitico = TemaUnidadResultadoProgramaAnalitico.objects.filter(pk=int(tema))[0]
                        if not SilaboActividadInscripcionCatedra.objects.filter(temaunidadresultadoprogramaanalitico=temaunidadresultadoprogramaanalitico).exists():
                            silaboactividadinscripcioncatedra = SilaboActividadInscripcionCatedra(actividadinscripcioncatedra=actividadinscripcioncatedra,
                                                                                                  temaunidadresultadoprogramaanalitico=temaunidadresultadoprogramaanalitico)
                            silaboactividadinscripcioncatedra.save(request)
                    lista = inscripcioncatedra.inscripcion.persona.lista_emails()
                    send_html_mail("Modifico Actividad de Ayudantía de Cátedra %s" % inscripcioncatedra.materia.asignatura.nombre,
                                   "emails/solicitud_ayudantia_catedra_edito_actividad.html",
                                   {'sistema': request.session['nombresistema'],
                                    'paralelo': inscripcioncatedra.materia.paralelomateria,
                                    'materia': inscripcioncatedra.materia.asignatura,
                                    'docente': inscripcioncatedra.docente.persona.nombre_completo_inverso(),
                                    't': miinstitucion()}, lista, [], cuenta=CUENTAS_CORREOS[5][1])
                    log(u'Adiciono Actividad Inscripcion Ayudantia Catedra: %s' % actividadinscripcioncatedra, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'aprobar_solicitud':
            try:
                inscripcioncatedra = InscripcionCatedra.objects.get(pk=request.POST['id'])
                materia = inscripcioncatedra.materia
                idinscripcioncatedra = inscripcioncatedra.id
                if not InscripcionCatedra.objects.filter(materia=materia, status=True, estado=4).exists():#estado 4=APROBADO
                    #inscripcioncatedra.estado = 2
                    inscripcioncatedra.estado = 4 #SE APRUEBA LA SOLICITUD DE LA FORMA QUE LO HACÍA VINCULAACIÓN
                    inscripcioncatedra.fechadesdeaprobado = datetime.now()
                    inscripcioncatedra.save(request)
                    lista = inscripcioncatedra.inscripcion.persona.lista_emails()
                    send_html_mail("Aprobación Solicitud de Ayudantía de Cátedra %s" % inscripcioncatedra.materia.asignatura.nombre,
                                   "emails/solicitud_ayudantia_catedra_aprobacion.html",
                                   {'sistema': request.session['nombresistema'],
                                    'paralelo': inscripcioncatedra.materia.paralelomateria,
                                    'materia': inscripcioncatedra.materia.asignatura,
                                    'docente': inscripcioncatedra.docente.persona.nombre_completo_inverso(),
                                    't': miinstitucion()}, lista, [], cuenta=CUENTAS_CORREOS[5][1])
                    # rechazar las demas solicitudes segun materia y docente
                    for i in InscripcionCatedra.objects.filter(materia=materia,docente=profesor, status=True).exclude(pk=idinscripcioncatedra):
                        i.estado = 3
                        i.fechadesdeaprobado = datetime.now()
                        i.save(request)
                        lista = inscripcioncatedra.inscripcion.persona.lista_emails()
                        send_html_mail("Rechazo Solicitud de Ayudantía de Cátedra %s" % inscripcioncatedra.materia.asignatura.nombre,
                                       "emails/solicitud_ayudantia_catedra_rechazo.html",
                                       {'sistema': request.session['nombresistema'],
                                        'paralelo': inscripcioncatedra.materia.paralelomateria,
                                        'materia': inscripcioncatedra.materia.asignatura,
                                        'docente': inscripcioncatedra.docente.persona.nombre_completo_inverso(),
                                        't': miinstitucion()}, lista, [], cuenta=CUENTAS_CORREOS[5][1])

                    log(u'Aprobacion ayudante catedra: %s' % inscripcioncatedra, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Ya tiene aprobado un ayudante para esta materia."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u'Error al guardar los datos'})

        if action == 'rechazar_solicitud':
            try:
                inscripcioncatedra = InscripcionCatedra.objects.get(pk=request.POST['id'])
                inscripcioncatedra.estado = 3
                inscripcioncatedra.estadoinscripcion = 3
                inscripcioncatedra.fechadesdeaprobado = datetime.now()
                inscripcioncatedra.save(request)
                lista = inscripcioncatedra.inscripcion.persona.lista_emails()
                send_html_mail("Rechazo Solicitud de Ayudantía de Cátedra %s" % inscripcioncatedra.materia.asignatura.nombre,
                               "emails/solicitud_ayudantia_catedra_rechazo.html",
                               {'sistema': request.session['nombresistema'],
                                'paralelo': inscripcioncatedra.materia.paralelomateria,
                                'materia': inscripcioncatedra.materia.asignatura,
                                'docente': inscripcioncatedra.docente.persona.nombre_completo_inverso(),
                                't': miinstitucion()}, lista, [], cuenta=CUENTAS_CORREOS[5][1])
                log(u'Aprobacion actividad ayudante catedra: %s' % inscripcioncatedra, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u'Error al guardar los datos'})

        if action == 'aprobar_actividad':
            try:
                actividadinscripcioncatedra = ActividadInscripcionCatedra.objects.get(pk=request.POST['id'])
                inscripcioncatedra = actividadinscripcioncatedra.inscripcioncatedra
                horasmaxima = inscripcioncatedra.periodocatedra.horasmaxima
                canthorasaprobadas = inscripcioncatedra.cant_horasaprobadas()#canthorasaprobadas[0]-> HORAS canthorasaprobadas[1]-> MINUTOS
                horasrestantes = horasmaxima-canthorasaprobadas[0]
                if horasrestantes<=0:
                    return JsonResponse({"result": "bad", "mensaje": u'El alumno ya completó las horas máximas'})
                form = ActividadInscripcionCatedraAprobarForm(request.POST)
                if form.is_valid():
                    actividadinscripcioncatedra.estado = 2
                    actividadinscripcioncatedra.docenteestado = profesor
                    actividadinscripcioncatedra.horadesde = form.cleaned_data['horadesde']
                    actividadinscripcioncatedra.horahasta = form.cleaned_data['horahasta']
                    horas = actividadinscripcioncatedra.horahasta.hour - actividadinscripcioncatedra.horadesde.hour
                    minutos = actividadinscripcioncatedra.horahasta.minute - actividadinscripcioncatedra.horadesde.minute
                    if horas>horasrestantes or (horas==horasrestantes and minutos>0):
                        return JsonResponse({"result": "bad", "mensaje": u'Las horas asignadas sobrepasan el máximo'})
                    actividadinscripcioncatedra.observacionestado = form.cleaned_data['observacionestado']
                    actividadinscripcioncatedra.save(request)
                    lista = actividadinscripcioncatedra.inscripcioncatedra.inscripcion.persona.lista_emails()
                    send_html_mail("Aprobación Actividad de Ayudantía de Cátedra %s" % actividadinscripcioncatedra.inscripcioncatedra.materia.asignatura.nombre,
                                   "emails/solicitud_ayudantia_catedra_aprobacion_actividad.html",
                                   {'sistema': request.session['nombresistema'],
                                    'paralelo': actividadinscripcioncatedra.inscripcioncatedra.materia.paralelomateria,
                                    'materia': actividadinscripcioncatedra.inscripcioncatedra.materia.asignatura,
                                    'docente': actividadinscripcioncatedra.inscripcioncatedra.docente.persona.nombre_completo_inverso(),
                                    't': miinstitucion()}, lista, [], cuenta=CUENTAS_CORREOS[5][1])
                    log(u'Aprobacion actividad ayudante catedra: %s' % actividadinscripcioncatedra, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u'Error al guardar los datos'})

        if action == 'rechazar_actividad':
            try:
                actividadinscripcioncatedra = ActividadInscripcionCatedra.objects.get(pk=request.POST['id'])

                form = ActividadInscripcionCatedraRechazarForm(request.POST)
                if form.is_valid():
                    actividadinscripcioncatedra.estado = 3
                    actividadinscripcioncatedra.docenteestado = profesor
                    actividadinscripcioncatedra.observacionestado = form.cleaned_data['observacionestado']
                    actividadinscripcioncatedra.save(request)
                    lista = actividadinscripcioncatedra.inscripcioncatedra.inscripcion.persona.lista_emails()
                    send_html_mail("Rechazo Actividad de Ayudantía de Cátedra %s" % actividadinscripcioncatedra.inscripcioncatedra.materia.asignatura.nombre,
                                   "emails/solicitud_ayudantia_catedra_rechazo_actividad.html",
                                   {'sistema': request.session['nombresistema'],
                                    'paralelo': actividadinscripcioncatedra.inscripcioncatedra.materia.paralelomateria,
                                    'materia': actividadinscripcioncatedra.inscripcioncatedra.materia.asignatura,
                                    'docente': actividadinscripcioncatedra.inscripcioncatedra.docente.persona.nombre_completo_inverso(),
                                    't': miinstitucion()}, lista, [], cuenta=CUENTAS_CORREOS[5][1])
                    log(u'Aprobacion actividad ayudante catedra: %s' % actividadinscripcioncatedra, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u'Error al guardar los datos'})

        if action == 'actividades_pdf':
            try:
                data['inscripcioncatedra'] = inscripcioncatedra = InscripcionCatedra.objects.get(pk=request.POST['idinscripcion'])
                data['actividadinscripcioncatedras'] = inscripcioncatedra.actividadinscripcioncatedra_set.filter(status=True).order_by('-id')
                data['fechahoy'] = datetime.now().date()
                return conviert_html_to_pdf(
                    'pro_ayudantiacatedra/actividades_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as ex:
                pass

        if action == 'addinformeayudante':
            try:
                if not json.loads(request.POST['lista_items1']):
                    return JsonResponse({"result": "bad", "mensaje": u"Debe tener al menos una conclusión"})
                else:
                    conclusiones = json.loads(request.POST['lista_items1'])
                inscripcioncatedra = InscripcionCatedra.objects.get(pk=int(encrypt(request.POST['idinscripcion'])))
                if inscripcioncatedra.informeayudantecatedra_set.exists():
                    return JsonResponse({"result": "bad", "mensaje": u"El informe ya se generó, solo tiene permiso a editarlo."})
                form = InformeAyudanteCatedraForm(request.POST)
                if form.is_valid():
                    inscripcionayudante = inscripcioncatedra.inscripcion
                    malla = inscripcionayudante.malla_inscripcion().malla
                    decano = malla.carrera.coordinaciones()[0].responsable_periododos(periodo, 1) if malla.carrera.coordinaciones()[0].responsable_periododos(periodo, 1) else None
                    directorcarrera = inscripcionayudante.carrera.coordinador(periodo, inscripcionayudante.coordinacion.sede) if inscripcionayudante.carrera else None
                    informeayudante = InformeAyudanteCatedra(
                        inscripcioncatedra=inscripcioncatedra,
                        objetivo=form.cleaned_data['objetivo'],
                        decano=decano.persona,
                        profesor=profesor,
                        directorcarrera=directorcarrera.persona,
                        fechaelaboracion=form.cleaned_data['fechaelaboracion']
                    )
                    informeayudante.save(request)
                    aprobacion = AprobacionInformeAyudanteCatedra(
                        informe=informeayudante,
                        observacion='SE CREÓ EL INFORME',
                        aprueba=persona,
                        estado=InformeAyudanteCatedra.INGRESADO,
                        fechaaprobacion=datetime.now()
                    )
                    aprobacion.save(request)
                    for conclusion in conclusiones:
                        model = ConclusionInformeAyudanteCatedra(
                            informe=informeayudante,
                            descripcion=conclusion['descripcion']
                        )
                        model.save(request)
                    data['actividades'] = actividades = inscripcioncatedra.actividadinscripcioncatedra_set.filter(status=True, estado=2).order_by('fecha')
                    data['conclusiones'] = conclusiones = informeayudante.conclusioninformeayudantecatedra_set.filter(status=True)
                    if len(actividades) == 0:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"Debe tener al menos una actividad."})
                    if len(conclusiones) == 0:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"Debe tener al menos una conclusión."})
                    data['title'] = u'Informe de actividades'
                    data['asunto'] = u'INFORME DE ACTIVIDADES DE AYUDANTÍA DE CÁTEDRA/INVESTIGACIÓN'
                    data['fechaimpresion'] = datetime.now().date()
                    data['informeayudante'] = informeayudante
                    nombrearchivo = generar_nombre("inscripcioncatedra", "inscripcioncatedra.pdf")
                    import os
                    from settings import SITE_STORAGE
                    folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'informeayudantecatedra'))
                    rutapdf = folder + '/' + nombrearchivo
                    if os.path.isfile(rutapdf):
                        os.remove(rutapdf)
                    valida = conviert_html_to_pdfsaveinformeayudante(
                        'pro_ayudantiacatedra/informe_ayudante_catedra.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }, nombrearchivo)
                    if valida:
                        informeayudante.archivo = 'informeayudantecatedra/' + nombrearchivo
                        informeayudante.save(request)
                        log(u'Adiciono informe de ayudante: %s [%s] - archivo:(%s)' % (
                            informeayudante, informeayudante.id, informeayudante.archivo), request, "add")
                        return JsonResponse({"result": "ok"})
                        # return JsonResponse({"result": "bad", "mensaje": u"Pruebas."})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Problemas al ejecutar el reporte."})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'editinformeayudante':
            try:
                if not json.loads(request.POST['lista_items1']):
                    return JsonResponse({"result": "bad", "mensaje": u"Debe tener al menos una conclusión"})
                else:
                    conclusiones = json.loads(request.POST['lista_items1'])
                form = InformeAyudanteCatedraForm(request.POST)
                if form.is_valid():
                    informeayudante = InformeAyudanteCatedra.objects.get(pk=int(encrypt(request.POST['id'])))
                    if informeayudante.aprobado():
                        raise NameError('Error')
                    informeayudante.objetivo = form.cleaned_data['objetivo']
                    informeayudante.estado = InformeAyudanteCatedra.INGRESADO
                    informeayudante.aprobadodecano = False
                    informeayudante.fechaelaboracion = form.cleaned_data['fechaelaboracion']
                    informeayudante.save(request)
                    aprobacion = AprobacionInformeAyudanteCatedra(
                        informe=informeayudante,
                        observacion='SE EDITÓ EL INFORME',
                        aprueba=persona,
                        estado=InformeAyudanteCatedra.INGRESADO,
                        fechaaprobacion=datetime.now()
                    )
                    aprobacion.save(request)
                    informeayudante.conclusioninformeayudantecatedra_set.all().delete()
                    #informeayudante.conclusioninformeayudantecatedra_set.update(status=False)
                    for conclusion in conclusiones:
                        model = ConclusionInformeAyudanteCatedra(
                            informe=informeayudante,
                            descripcion=conclusion['descripcion']
                        )
                        model.save(request)
                    data['actividades'] = actividades = informeayudante.inscripcioncatedra.actividadinscripcioncatedra_set.filter(status=True, estado=2).order_by('fecha')
                    data['conclusiones'] = conclusiones = informeayudante.conclusioninformeayudantecatedra_set.filter(status=True)
                    if len(actividades) == 0:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"Debe tener al menos una actividad."})
                    if len(conclusiones) == 0:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"Debe tener al menos una conclusión."})
                    data['title'] = u'Informe de actividades'
                    data['asunto'] = u'INFORME DE ACTIVIDADES DE AYUDANTÍA DE CÁTEDRA/INVESTIGACIÓN'
                    data['fechaimpresion'] = datetime.now().date()
                    data['informeayudante'] = informeayudante
                    nombrearchivo = generar_nombre("inscripcioncatedra", "inscripcioncatedra.pdf")
                    import os
                    from settings import SITE_STORAGE
                    folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'informeayudantecatedra'))
                    rutapdf = folder + '/' + nombrearchivo
                    if os.path.isfile(rutapdf):
                        os.remove(rutapdf)
                    valida = conviert_html_to_pdfsaveinformeayudante(
                        'pro_ayudantiacatedra/informe_ayudante_catedra.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }, nombrearchivo)
                    if valida:
                        informeayudante.archivo = 'informeayudantecatedra/' + nombrearchivo
                        informeayudante.save(request)
                        log(u'Adiciono informe de ayudante: %s [%s] - archivo:(%s)' % (
                            informeayudante, informeayudante.id, informeayudante.archivo), request, "add")
                        return JsonResponse({"result": "ok"})
                        # return JsonResponse({"result": "bad", "mensaje": u"Pruebas."})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Problemas al ejecutar el reporte."})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'editresponsables':
            try:
                informeayudante = InformeAyudanteCatedra.objects.get(pk=int(encrypt(request.POST['id'])))
                actividades = informeayudante.inscripcioncatedra.actividadinscripcioncatedra_set.filter(status=True, estado=2).order_by('fecha')  # ESTADO 2=APROBADO
                conclusiones = informeayudante.conclusioninformeayudantecatedra_set.filter(status=True)
                if len(actividades)==0:
                    return JsonResponse({"result": "bad", "mensaje": u"Debe tener al menos una actividad."})
                if len(conclusiones)==0:
                    return JsonResponse({"result": "bad", "mensaje": u"Debe tener al menos una conclusión."})
                aprobacion = AprobacionInformeAyudanteCatedra(
                    informe=informeayudante,
                    observacion='SE ACTUALIZÓ LOS RESPONSABLES',
                    aprueba=persona,
                    estado=InformeAyudanteCatedra.INGRESADO,
                    fechaaprobacion=datetime.now()
                )
                aprobacion.save(request)
                if informeayudante.aprobado():
                    raise NameError('Error')
                inscripcionayudante = informeayudante.inscripcioncatedra.inscripcion
                malla = inscripcionayudante.malla_inscripcion().malla
                decano = malla.carrera.coordinaciones()[0].responsable_periododos(periodo, 1) if \
                malla.carrera.coordinaciones()[0].responsable_periododos(periodo, 1) else None
                directorcarrera = inscripcionayudante.carrera.coordinador(periodo, inscripcionayudante.coordinacion.sede) if inscripcionayudante.carrera else None
                informeayudante.decano = decano.persona
                informeayudante.profesor = profesor
                informeayudante.fechaelaboracion = datetime.now().date()
                informeayudante.directorcarrera = directorcarrera.persona
                informeayudante.aprobadodecano = False
                informeayudante.estado = InformeAyudanteCatedra.INGRESADO
                informeayudante.save(request)
                data['actividades'] = actividades
                data['conclusiones'] = conclusiones
                data['title'] = u'Informe de actividades'
                data['asunto'] = u'INFORME DE ACTIVIDADES DE AYUDANTÍA DE CÁTEDRA/INVESTIGACIÓN'
                data['fechaimpresion'] = datetime.now().date()
                data['informeayudante'] = informeayudante
                nombrearchivo = generar_nombre("inscripcioncatedra", "inscripcioncatedra.pdf")
                import os
                from settings import SITE_STORAGE
                folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'informeayudantecatedra'))
                rutapdf = folder + '/' + nombrearchivo
                if os.path.isfile(rutapdf):
                    os.remove(rutapdf)
                valida = conviert_html_to_pdfsaveinformeayudante(
                    'pro_ayudantiacatedra/informe_ayudante_catedra.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }, nombrearchivo)
                if valida:
                    informeayudante.archivo = 'informeayudantecatedra/' + nombrearchivo
                    informeayudante.save(request)
                    log(u'Adiciono informe de ayudante: %s [%s] - archivo:(%s)' % (
                        informeayudante, informeayudante.id, informeayudante.archivo), request, "add")
                    return JsonResponse({"result": "ok"})
                    # return JsonResponse({"result": "bad", "mensaje": u"Pruebas."})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Problemas al ejecutar el reporte."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'loadDataTableSolicitudesProfesorCatedra':
            try:
                txt_filter = request.POST['sSearch'] if request.POST['sSearch'] else ''
                limit = int(request.POST['iDisplayLength']) if request.POST['iDisplayLength'] else 25
                offset = int(request.POST['iDisplayStart']) if request.POST['iDisplayStart'] else 0
                tCount = 0
                solicitudes = SolicitudProfesorCatedra.objects.filter(status=True, profesor=profesor)
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
                                    "estado": row.estado,
                                    }
                                   ])
                return JsonResponse({"result": "ok", "data": aaData, "iTotalRecords": tCount, "iTotalDisplayRecords": tCount})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos. %s" % ex.__str__(), "data": [], "iTotalRecords": 0, "iTotalDisplayRecords": 0})

        elif action == 'saveSolicitudProfesorCatedra':
            try:
                print(request.POST)
                id = int(encrypt(request.POST['id'])) if 'id' in request.POST and request.POST['id'] and int(encrypt(request.POST['id'])) != 0 else None
                typeForm = 'edit' if id else 'new'
                form = SolicitudProfesorCatedraForm(request.POST, request.FILES)
                if not form.is_valid():
                    errores = []
                    for k, v in form.errors.items():
                        errores.append(f'el campo {k} {v[0]}')
                    raise NameError(u"Debe ingresar la información en todos los campos  \n %s" % '\n'.join(errores))
                if typeForm == 'new':
                    eSolicitudProfesorCatedraLast = SolicitudProfesorCatedra.objects.filter(status=True).order_by('-id').first()
                    numero_solicitud = eSolicitudProfesorCatedraLast.numero if eSolicitudProfesorCatedraLast is not None else 0
                    numero_solicitud += 1
                    file = None
                    valid_ext = [".pdf"]
                    if 'archivo' in request.FILES:
                        file = request.FILES['archivo']
                        if file:
                            if file.size > 20480000:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo es mayor a 20 Mb."})
                            else:
                                newfilesd = file._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if not ext in valid_ext:
                                    return JsonResponse({"result": "bad", "mensaje": f"Error, Solo archivos con extensión .jrxml"})

                    eSolicitudProfesorCatedra = SolicitudProfesorCatedra(
                        periodocatedra=periodocatedra,
                        profesor=profesor,
                        carrera=form.cleaned_data['carrera'],
                        descripcion=form.cleaned_data['descripcion'],
                        numero=numero_solicitud,
                        archivo=file
                    )
                    eSolicitudProfesorCatedra.save(request)
                    materias = json.loads(request.POST.get('materias'))
                    for materia in materias:
                        eDetalleSolicitudProfesorCatedra = DetalleSolicitudProfesorCatedra(
                            solicitud=eSolicitudProfesorCatedra,
                            materia_id=int(materia['id']),
                            numero_estudiantes=int(materia['numero_estudiantes'])
                        )
                        eDetalleSolicitudProfesorCatedra.save(request)
                        horarios = materia.get('horarios', [])
                        for horario in horarios:
                            eDetalleHorarioSolicitudProfesorCatedra = DetalleHorarioSolicitudProfesorCatedra(
                                detallesolicitud=eDetalleSolicitudProfesorCatedra,
                                dia=int(horario['dia']),
                                horainicio=horario['horainicio'],
                                horafin=horario['horafin'],
                            )
                            eDetalleHorarioSolicitudProfesorCatedra.save(request)
                    log(u'Adiciono solicitud de ayudantes de catedras: %s' % (eSolicitudProfesorCatedra), request, "add")
                else:
                    if not id:
                        NameError(u"No se encontro el parametro id")
                    eSolicitudProfesorCatedra = SolicitudProfesorCatedra.objects.get(id=id)
                    file = None
                    valid_ext = [".pdf"]
                    if 'archivo' in request.FILES:
                        file = request.FILES['archivo']
                        if file:
                            if file.size > 20480000:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo es mayor a 20 Mb."})
                            else:
                                newfilesd = file._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if not ext in valid_ext:
                                    return JsonResponse({"result": "bad", "mensaje": f"Error, Solo archivos con extensión .jrxml"})
                            eSolicitudProfesorCatedra.archivo = file
                    eSolicitudProfesorCatedra.carrera = form.cleaned_data.get('carrera')
                    eSolicitudProfesorCatedra.observacion = form.cleaned_data.get('observacion')
                    eSolicitudProfesorCatedra.estado = 1
                    eSolicitudProfesorCatedra.save(request)
                    materias = json.loads(request.POST.get('materias'))
                    idsdet = []
                    for materia in materias:
                        detalle_id = int(materia['detalle_id']) if 'detalle_id' in materia.keys() else 0
                        eDetalleSolicitudProfesorCatedra = eSolicitudProfesorCatedra.detallesolicitudprofesorcatedra_set.filter(id=detalle_id, status=True).first()
                        es_nuevo = False
                        if eDetalleSolicitudProfesorCatedra is None:
                            es_nuevo = True
                            eDetalleSolicitudProfesorCatedra = eSolicitudProfesorCatedra.detallesolicitudprofesorcatedra_set.model()
                            eDetalleSolicitudProfesorCatedra.solicitud = eSolicitudProfesorCatedra
                            eDetalleSolicitudProfesorCatedra.materia_id = int(materia['id'])
                        eDetalleSolicitudProfesorCatedra.numero_estudiantes = int(materia['numero_estudiantes'])
                        eDetalleSolicitudProfesorCatedra.save(request)
                        idsdet.append(eDetalleSolicitudProfesorCatedra.id)
                        horarios = materia.get('horarios', [])
                        idhorsdet = []
                        for horario in horarios:
                            horario_id = int(horario['idh']) if 'idh' in horario.keys() else 0
                            eDetalleHorarioSolicitudProfesorCatedra = eDetalleSolicitudProfesorCatedra.detallehorariosolicitudprofesorcatedra_set.filter(id=horario_id, status=True).first()
                            es_nuevodet = False
                            if eDetalleHorarioSolicitudProfesorCatedra is None:
                                es_nuevodet = True
                                eDetalleHorarioSolicitudProfesorCatedra = eDetalleSolicitudProfesorCatedra.detallehorariosolicitudprofesorcatedra_set.model()
                                eDetalleHorarioSolicitudProfesorCatedra.detallesolicitud = eDetalleSolicitudProfesorCatedra
                            eDetalleHorarioSolicitudProfesorCatedra.dia = int(horario['dia'])
                            eDetalleHorarioSolicitudProfesorCatedra.horainicio = horario['horainicio']
                            eDetalleHorarioSolicitudProfesorCatedra.horafin = horario['horafin']
                            eDetalleHorarioSolicitudProfesorCatedra.save(request)
                            idhorsdet.append(eDetalleHorarioSolicitudProfesorCatedra.id)
                        # Eliminación de forma logica horario  de detalle solicitud
                        eDetalleSolicitudProfesorCatedra.detallehorariosolicitudprofesorcatedra_set.exclude(id__in=idhorsdet).update(status=False)
                    #Eliminación de forma logica detalle de materias
                    eSolicitudProfesorCatedra.detallesolicitudprofesorcatedra_set.exclude(id__in=idsdet).update(status=False)
                    log(u'Editó solicitud de ayudantes de catedras: %s' % (eSolicitudProfesorCatedra), request, "edit")
                return JsonResponse({"result": "ok", "mensaje": "Se guardo correctamente la solicitud"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "%s" % ex.__str__()})

        elif action == 'deleteSolicitudProfesorCatedra':
            try:
                id = int(encrypt(request.POST['id'])) if 'id' in request.POST and request.POST['id'] and int(encrypt(request.POST['id'])) != 0 else None
                eSolicitudProfesorCatedra = SolicitudProfesorCatedra.objects.get(id=id)
                if eSolicitudProfesorCatedra.estado in [2, 3]:
                    raise NameError('Su solicitud no se puede eliminara tiene estado Aceptado o Rechazado')
                for eDetalleMateria in eSolicitudProfesorCatedra.detalle_materias():
                    #Eliminar detalle de materia  de la solicitud
                    eDetalleMateria.detalle_horario().update(status=False)
                    eDetalleMateria.status = False
                    eDetalleMateria.save(request)
                eSolicitudProfesorCatedra.status = False
                eSolicitudProfesorCatedra.save(request)
                log(u'Elimino solicitud de ayudantes de catedra: %s' % (eSolicitudProfesorCatedra), request, "del")
                return JsonResponse({"result": "ok", "mensaje": "Eliminó correctamenta la solicitud"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "%s" % ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        data['title'] = u'Ayudantía catedra'
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['inscripcioncatedra'] = inscripcioncatedra = InscripcionCatedra.objects.get(pk=request.GET['idinscripcion'])
                    if not inscripcioncatedra.puederegistraractividad():  # SOLO PUEDE REGISTRAR ACTIVIDADES CUANDO ESTÉ DENTRO DEL PERIODO
                        raise ('Error')
                    data['title'] = u'Adicionar actividad'
                    materia = inscripcioncatedra.materia
                    data['silabo'] = None
                    data['bibliografia'] = None
                    data['contenido'] = None
                    if materia.tiene_silabo_digital() and materia.tiene_silabo_semanal():
                        data['silabo'] = silabo = Silabo.objects.get(pk=materia.silabo_set.get(status=True).id)
                        data['bibliografia'] = BibliografiaProgramaAnaliticoAsignatura.objects.filter(programaanaliticoasignatura=silabo.programaanaliticoasignatura)
                        data['contenido'] = ContenidoResultadoProgramaAnalitico.objects.filter(programaanaliticoasignatura=silabo.programaanaliticoasignatura).order_by('orden')

                    form = ActividadInscripcionCatedraRegistrarForm()
                    form.eliminar_actividad()
                    form.cargaractividadperiodo(inscripcioncatedra.periodocatedra)
                    data['form'] = form
                    return render(request, "pro_ayudantiacatedra/add.html", data)
                except Exception as ex:
                    pass

            if action == 'editar':
                try:
                    data['actividadinscripcioncatedra'] = actividadinscripcioncatedra = ActividadInscripcionCatedra.objects.get(pk=request.GET['id'])
                    data['inscripcioncatedra'] = inscripcioncatedra = actividadinscripcioncatedra.inscripcioncatedra
                    data['title'] = u'Editar actividad  - ' + inscripcioncatedra.inscripcion.persona.nombre_completo_inverso()
                    materia = inscripcioncatedra.materia
                    data['silabo'] = None
                    data['bibliografia'] = None
                    data['contenido'] = None
                    if materia.tiene_silabo_digital() and materia.tiene_silabo_semanal():
                        data['silabo'] = silabo = Silabo.objects.get(pk=materia.silabo_set.get(status=True).id)
                        data['bibliografia'] = BibliografiaProgramaAnaliticoAsignatura.objects.filter(programaanaliticoasignatura=silabo.programaanaliticoasignatura)
                        data['contenido'] = ContenidoResultadoProgramaAnalitico.objects.filter(programaanaliticoasignatura=silabo.programaanaliticoasignatura)

                    form = ActividadInscripcionCatedraRegistrarForm(initial={'fecha': actividadinscripcioncatedra.fecha,
                                                                             'horadesde': str(actividadinscripcioncatedra.horadesde)[0:5],
                                                                             'horahasta': str(actividadinscripcioncatedra.horahasta)[0:5],
                                                                             'actividadModel': actividadinscripcioncatedra.actividadModel,
                                                                             'actividad': actividadinscripcioncatedra.actividad})
                    form.eliminar_actividad()
                    form.cargaractividadperiodo(inscripcioncatedra.periodocatedra)
                    data['silabosactividadtema'] = TemaUnidadResultadoProgramaAnalitico.objects.filter(silaboactividadinscripcioncatedra__actividadinscripcioncatedra=actividadinscripcioncatedra, status=True).distinct()
                    data['silabosactividadsubtema'] = SubtemaUnidadResultadoProgramaAnalitico.objects.filter(silaboactividadinscripcioncatedra__actividadinscripcioncatedra=actividadinscripcioncatedra, status=True).distinct()
                    data['form'] = form
                    return render(request, "pro_ayudantiacatedra/editar.html", data)
                except Exception as ex:
                    pass

            if action == 'registraractividades':
                try:
                    data['inscripcioncatedra'] = inscripcioncatedra = InscripcionCatedra.objects.get(pk=request.GET['idinscripcion'])
                    if not inscripcioncatedra.puederegistraractividad():#SOLO PUEDE REGISTRAR ACTIVIDADES CUANDO ESTÉ DENTRO DEL PERIODO
                        raise('Error')
                    data['actividadinscripcioncatedras'] = inscripcioncatedra.actividadinscripcioncatedra_set.filter(status=True).order_by('-id')
                    data['title'] = u'AYUDANTÍA DE CATEDRA  - ' + inscripcioncatedra.materia.asignatura.nombre + ' - ' + inscripcioncatedra.inscripcion.persona.nombre_completo_inverso()

                    return render(request, "pro_ayudantiacatedra/registraractividades.html", data)
                except Exception as ex:
                    pass

            if action == 'aprobar_solicitud':
                try:
                    data['inscripcioncatedra'] = inscripcioncatedra = InscripcionCatedra.objects.get(pk=request.GET['id'])
                    data['title'] = u'Aprobar solicitud'
                    return render(request, 'pro_ayudantiacatedra/aprobar_solicitud.html', data)
                except Exception as ex:
                    pass

            if action == 'rechazar_solicitud':
                try:
                    data['inscripcioncatedra'] = inscripcioncatedra = InscripcionCatedra.objects.get(pk=request.GET['id'])
                    data['title'] = u'Rechazar solicitud'
                    return render(request, 'pro_ayudantiacatedra/rechazar_solicitud.html', data)
                except Exception as ex:
                    pass

            if action == 'aprobar_actividad':
                try:
                    data['actividadinscripcioncatedra'] = actividadinscripcioncatedra = ActividadInscripcionCatedra.objects.get(pk=request.GET['id'])
                    data['title'] = u'Aprobar solicidud'
                    data['form'] = ActividadInscripcionCatedraAprobarForm(initial={'horadesde': str(actividadinscripcioncatedra.horadesde)[0:5],
                                                                                   'horahasta': str(actividadinscripcioncatedra.horahasta)[0:5]})
                    return render(request, 'pro_ayudantiacatedra/aprobar.html', data)
                except Exception as ex:
                    pass

            if action == 'rechazar_actividad':
                try:
                    data['actividadinscripcioncatedra'] = actividadinscripcioncatedra = ActividadInscripcionCatedra.objects.get(pk=request.GET['id'])
                    data['title'] = u'Rechazar solicitud'
                    data['form'] = ActividadInscripcionCatedraRechazarForm()
                    return render(request, 'pro_ayudantiacatedra/rechazar.html', data)
                except Exception as ex:
                    pass

            if action == 'alumalla':
                try:
                    data['title'] = u'Malla'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    data['inscripcion_malla'] = inscripcionmalla = inscripcion.malla_inscripcion()
                    data['malla'] = malla = inscripcionmalla.malla
                    data['nivelesdemallas'] = NivelMalla.objects.all().order_by('id')
                    data['ejesformativos'] = EjeFormativo.objects.all().order_by('nombre')
                    data['asignaturasmallas'] = [(x, inscripcion.aprobadaasignatura(x)) for x in AsignaturaMalla.objects.filter(malla=malla)]
                    resumenniveles = [{'id': x.id, 'horas': x.total_horas(malla), 'creditos': x.total_creditos(malla)} for x in NivelMalla.objects.all().order_by('id')]
                    data['resumenes'] = resumenniveles
                    template = get_template("pro_ayudantiacatedra/alumalla.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            if action == 'verasistencia':
                try:
                    data['actividadinscripcioncatedra'] = actividadinscripcioncatedra = ActividadInscripcionCatedra.objects.get(pk=request.GET['idactividad'])
                    data['asistenciaactividadinscripcioncatedras'] = actividadinscripcioncatedra.asistenciaactividadinscripcioncatedra_set.filter(status=True).order_by('inscripcionalumno__persona__apellido1', 'inscripcionalumno__persona__apellido2')

                    template = get_template("pro_ayudantiacatedra/verasistencia.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            if action == 'addinformeayudante':
                try:
                    data['title'] = u'Adicionar informe ayudante'
                    data['inscripcioncatedra'] = inscripcioncatedra = InscripcionCatedra.objects.get(pk=int(encrypt(request.GET['idinscripcion'])))
                    if inscripcioncatedra.informeayudantecatedra_set.exists():
                        raise NameError('Error')
                    form = InformeAyudanteCatedraForm()
                    data['form'] = form
                    return render(request, "pro_ayudantiacatedra/addinformeayudante.html", data)
                except Exception as ex:
                    pass

            elif action == 'editinformeayudante':
                try:
                    data['title'] = u'Editar informe ayudante'
                    data['informeayudante'] = informeayudante = InformeAyudanteCatedra.objects.get(inscripcioncatedra_id=int(encrypt(request.GET['idinscripcion'])))
                    data['conclusiones'] = informeayudante.conclusioninformeayudantecatedra_set.filter(status=True)
                    form = InformeAyudanteCatedraForm(initial={'objetivo': informeayudante.objetivo, 'fechaelaboracion': informeayudante.fechaelaboracion})
                    data['form'] = form
                    return render(request, "pro_ayudantiacatedra/editinformeayudante.html", data)
                except Exception as ex:
                    pass

            elif action == 'veraprobacioninforme':
                try:
                    data['informe'] = informe = InformeAyudanteCatedra.objects.get(pk=int(encrypt(request.GET['idinforme'])))
                    data['aprobacion'] = informe.aprobacioninformeayudantecatedra_set.all().order_by('-id')
                    return render(request, "ayudantiacatedra/modalveraprobacioninforme.html", data)
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
                    idscarrdocente = profesor.mis_materias(periodo).values_list('materia__asignaturamalla__malla__carrera_id', flat=True).distinct()
                    form.fields['carrera'].queryset = form.fields['carrera'].queryset.filter(pk__in=idscarrdocente)
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
                    template = get_template("pro_ayudantiacatedra/frmSolicitudProfesorCatedra.html")
                    json_content = template.render(data, request=request)
                    return JsonResponse({"result": "ok", 'html': json_content, 'eMaterias': eMaterias})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"%s" % ex.__str__()})

            if action == 'loadMateriasImparte':
                try:
                    data['title'] = u'Adicionar informe ayudante'
                    carrera_id = request.GET.get('carrera')
                    exclude_materias = json.loads(request.GET.get('exclude'))
                    #MATERIAS QUE ESTEN SOLICITUDES COMO APROBADAS O PENDIENTES
                    idsmaterias_en_solicitudes = profesor.solicitudprofesorcatedra_set.filter(status=True, estado__in=[1,3]).values_list('detallesolicitudprofesorcatedra__materia_id', flat=True).distinct()
                    exclude_materias.extend(list(idsmaterias_en_solicitudes))
                    exclude_materias = set(exclude_materias)
                    idsmaterias = profesor.mis_materias(periodo).filter(materia__asignaturamalla__malla__carrera_id=carrera_id,
                                                                        materia__status=True,
                                                                        status=True).values_list('materia_id', flat=True).exclude(materia_id__in=exclude_materias)
                    eMaterias = Materia.objects.filter(pk__in=idsmaterias, status=True)
                    data_select = [{'id': eMateria.id,
                                   'name': eMateria.__str__(),
                                   'text': u'%s - %s -%s' % (eMateria.asignaturamalla.asignatura.nombre, eMateria.paralelomateria.__str__(), eMateria.nivel.paralelo),
                                   'paralelo': eMateria.paralelomateria.__str__(),
                                   'horarios': [],
                                   'numero_estudiantes': 0,
                                    } for eMateria in eMaterias]
                    return JsonResponse({"result": "ok", 'results': data_select})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"%s" % ex.__str__()})

            elif action == 'view_old':
                try:
                    data['inscripcioncatedras'] = InscripcionCatedra.objects.filter(docente=profesor,
                                                                                    periodocatedra=periodocatedra,
                                                                                    periodocatedra__status=True,
                                                                                    status=True, estado=1,
                                                                                    estadoinscripcion=1).order_by('materia').distinct()
                    data['inscripcioncatedras_aprobadas'] = InscripcionCatedra.objects.filter(estado__in=[2, 4],
                                                                                              docente=profesor,
                                                                                              periodocatedra=periodocatedra,
                                                                                              periodocatedra__status=True,
                                                                                              status=True).order_by('materia').distinct()
                    data['title'] = u'Solicitudes de Ayudentes de catedra'
                    data['dias'] = DIAS_CHOICES
                    return render(request, "pro_ayudantiacatedra/view_old.html", data)
                except Exception as ex:
                    pass

            elif action == 'viewsolicitudmateriasprofesorcatedra':
                try:
                    data['title'] = u'Solicitudes de Ayudentes de catedra'
                    id = encrypt(request.GET.get('id'))
                    data['eSolicitudCatedra'] = eSolicitudCatedra = SolicitudProfesorCatedra.objects.get(id=id)
                    return render(request, "pro_ayudantiacatedra/viewsolicitudmateriasprofesorcatedra.html", data)
                except Exception as ex:
                    pass

            elif action == 'viewsolicitudesestudiantescatedra':
                try:
                    data['title'] = u'Solicitudes de Ayudentes de catedra'
                    id = int(encrypt(request.GET.get('id')))
                    data['eDetalleSolicituProfesorCatedra'] = eDetalleSolicituProfesorCatedra = DetalleSolicitudProfesorCatedra.objects.get(id=id)
                    data['inscripcioncatedras'] = InscripcionCatedra.objects.filter(docente=profesor,
                                                                                    detallesolicitudprofesorcatedra=eDetalleSolicituProfesorCatedra,
                                                                                    periodocatedra=periodocatedra,
                                                                                    periodocatedra__status=True,
                                                                                    status=True, estado=1,
                                                                                    estadoinscripcion=1).order_by('materia').distinct()
                    data['inscripcioncatedras_aprobadas'] = InscripcionCatedra.objects.filter(estado__in=[2, 4],
                                                                                              docente=profesor,
                                                                                              detallesolicitudprofesorcatedra_id=id,
                                                                                              periodocatedra=periodocatedra,
                                                                                              periodocatedra__status=True,
                                                                                              status=True).order_by('materia').distinct()
                    return render(request, "pro_ayudantiacatedra/viewsolicitudesestudiantescatedra.html", data)
                except Exception as ex:
                    pass
            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Solicitudes de Ayudentes de catedra'
                data['dias'] = DIAS_CHOICES
                data['ePeriodosCatedra'] = ePeriodosCatedra = PeriodoCatedra.objects.filter(status=True)
                data['ePeriodoCatedra'] = periodocatedra
                return render(request, "pro_ayudantiacatedra/view.html", data)
            except Exception as ex:
                pass