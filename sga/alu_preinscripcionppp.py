# -*- coding: latin-1 -*-
import json
import os
from datetime import datetime
import random

from inno.funciones import haber_aprobado_modulos_ingles, haber_aprobado_modulos_computacion
from settings import SITE_STORAGE
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from decorators import secure_module, last_access
from sagest.models import Departamento
from sga.commonviews import adduserdata
from sga.forms import RechazarAsignacionPracticaFrom, DocumentoPracticasPPPForm, SolicitudEmpresaPreinscripcionForm, AsignacionTutorForm
from sga.funcionesxhtml2pdf import conviert_html_to_pdf, conviert_html_to_pdf_name_save, conviert_html_to_pdf_name
from sga.funciones_templatepdf import generar_acta_compromiso_v2
from inno.models import ExtraDetallePreInscripcionPracticasPP
from sga.models import PreInscripcionPracticasPP, Inscripcion, DetalleRespuestaPreInscripcionPPP, \
    RespuestaPreInscripcionPracticasPP, DetallePreInscripcionPracticasPP, PracticasPreprofesionalesInscripcion, \
    DetalleRecoridoPreInscripcionPracticasPP, CUENTAS_CORREOS, DatosEmpresaPreInscripcionPracticasPP, MESES_CHOICES, \
    FirmaPersona, AcuerdoCompromiso, Pais, Provincia, Canton, ActividadDetalleDistributivoCarrera, ConvenioEmpresa, \
    SolicitudVinculacionPreInscripcionPracticasPP, EmpresaEmpleadora
from django.template import Context
from django.template.loader import get_template
from sga.funciones import log, notificacion, generar_codigo, remover_caracteres_especiales_unicode, \
    remover_caracteres_tildes_unicode, generar_nombre, get_director_vinculacion
from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt
from django.db.models import Q

@login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    PREFIX = 'UNEMI'
    SUFFIX = 'VICEVIN-PPP'
    adduserdata(request, data)
    persona = request.session['persona']
    data['coordinacion'] = coordinacion = request.session['coordinacion']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    departamentogestion = Departamento.objects.filter(pk=111)
    responsablevinculacion = departamentogestion.first().responsable if departamentogestion.exists() else None
    inscripcion = perfilprincipal.inscripcion
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'addpreinscripcion':
                try:
                    preinscripcion = []
                    itinerarios = []
                    falta_horas = False
                    cant_preguntas = 0
                    respondio = False
                    conf = []
                    data['cumple'] = cumple = int(request.POST.get('cumple', 0))

                    carreraconfigurada = True

                    if not inscripcion.cumple_total_parcticapp():
                        # if coordinacion == 1:
                        #     conf = PreInscripcionPracticasPP.objects.filter(fechainicio__lte=datetime.now().date(),fechafin__gte=datetime.now().date(), coordinacion__in=[1])
                        #     data['inglesaproado'] = aproboingles = inglesaprobado(inscripcion) if conf[0].inglesaprobado else True
                        #     if not aproboingles:
                        #         texto = 'LO SENTIMOS, NO TE PUEDES PRE INSCRIBIR SIN HABER APROBADO TODOS TUS MÓDULOS DE INGLÉS'
                        #         return JsonResponse({"result": "bad", "mensaje": texto})
                        # else:
                        conf = PreInscripcionPracticasPP.objects.filter(fechainicio__lte=datetime.now().date(),fechafin__gte=datetime.now().date())
                        if conf:
                            x = conf[0].carreras()
                            if x:
                                if PreInscripcionPracticasPP.objects.filter(fechainicio__lte=datetime.now().date(), fechafin__gte=datetime.now().date(), carrera=inscripcion.carrera).exists():
                                    preinscripcion = PreInscripcionPracticasPP.objects.filter(fechainicio__lte=datetime.now().date(), fechafin__gte=datetime.now().date(), carrera=inscripcion.carrera)[0]
                                    carreraconfigurada = True
                                else:
                                    carreraconfigurada = False
                            else:
                                preinscripcion = PreInscripcionPracticasPP.objects.filter(fechainicio__lte=datetime.now().date(), fechafin__gte=datetime.now().date(), coordinacion=inscripcion.carrera.coordinacion_set.filter(status=True)[0])[0]

                                if preinscripcion:
                                    carreraconfigurada = True
                                else:
                                    carreraconfigurada = False
                            estudiante_salud = False
                            lista_estado = [1]
                            if inscripcion.carrera.coordinacion_carrera().id == 1:
                                estudiante_salud = True
                                lista_estado = [1, 2]
                            # periodospreins = PreInscripcionPracticasPP.objects.values_list('id', flat=False).filter(fechainicio__lte=datetime.now().date(), fechafin__gte=datetime.now().date())
                            periodospreins = conf
                            listapre = inscripcion.detallepreinscripcionpracticaspp_set.values_list('itinerariomalla_id', flat=False).filter(status=True, estado__in=lista_estado, preinscripcion__in=periodospreins)
                            if inscripcion.inscripcionmalla_set.values('id').exists():
                                if inscripcion.inscripcionmalla_set.filter(status=True)[0].malla.itinerariosmalla_set.filter(status=True).exists():
                                    matricula = inscripcion.matricula_set.filter(status=True)[0]
                                    listaitinerariorealizado = inscripcion.cumple_total_horas_itinerario()
                                    itinerariosvalidosid = []
                                    for it in inscripcion.inscripcionmalla_set.filter(status=True)[0].malla.itinerariosmalla_set.filter(status=True):
                                        nivelhasta = it.nivel.orden
                                        if inscripcion.todas_materias_aprobadas_rango_nivel2(1, nivelhasta):
                                            itinerariosvalidosid.append(it.pk)
                                    practicaculminada = inscripcion.practicaspreprofesionalesinscripcion_set.values_list('preinscripcion__itinerariomalla_id').filter(status=True,culminada=True,estadosolicitud=2,preinscripcion__itinerariomalla__isnull=False,preinscripcion__itinerariomalla_id__in=itinerariosvalidosid)
                                    practicaculminada2 = inscripcion.practicaspreprofesionalesinscripcion_set.values_list('actividad__itinerariomalla_id').filter(status=True,culminada=True,estadosolicitud=2,actividad__itinerariomalla__isnull=False,actividad__itinerariomalla_id__in=itinerariosvalidosid)
                                    if estudiante_salud:
                                        itinerarios = inscripcion.inscripcionmalla_set.filter(status=True)[0].malla.itinerariosmalla_set.values_list('id', 'nombre', 'nivel__nombre').filter(status=True).exclude(id__in=listaitinerariorealizado).exclude(id__in=listapre).exclude(id__in=practicaculminada).exclude(id__in=practicaculminada2)
                                    else:
                                        itinerarios = inscripcion.inscripcionmalla_set.filter(status=True)[0].malla.itinerariosmalla_set.values_list('id', 'nombre', 'nivel__nombre').filter(status=True, nivel__orden__lte=matricula.nivelmalla.orden).filter(pk__in=itinerariosvalidosid).exclude(id__in=listaitinerariorealizado).exclude(id__in=listapre).exclude(id__in=practicaculminada).exclude(id__in=practicaculminada2)
                                    # itinerarios = inscripcion.inscripcionmalla_set.filter(status=True)[0].malla.itinerariosmalla_set.values_list('id', 'nombre', 'nivel__nombre').filter(status=True).filter(pk__in=itinerariosvalidosid).exclude(id__in=listaitinerariorealizado).exclude(id__in=listapre)

                            else:
                                if inscripcion.mi_nivel().nivel.orden + 1 > 5:
                                    if not inscripcion.detallepreinscripcionpracticaspp_set.filter(status=True, itinerariomalla__isnull=True).exists():
                                        falta_horas = inscripcion.cumple_total_parcticapp()
                                    else:
                                        preinscripcion = []
                            respondio = conf[0].detallerespuestapreinscripcionppp_set.filter(inscripcion=inscripcion).exists()
                            if not respondio:
                                cant_preguntas = conf[0].preguntas().count()
                        else:
                            preinscripcion = []

                            carreraconfigurada = False

                    data['preinscripcion'] = preinscripcion
                    if preinscripcion:
                        data['inglesaprobado'] = inglesaprobado = haber_aprobado_modulos_ingles(inscripcion.id)
                        data['computacionaprobado'] = computacionaprobado = haber_aprobado_modulos_computacion(inscripcion.id)
                        validar_preinscripcion_ = True
                        if not preinscripcion.inglesaprobado and not preinscripcion.computacionaprobado:
                            validar_preinscripcion_ = True
                        if preinscripcion.inglesaprobado and not preinscripcion.computacionaprobado:
                            validar_preinscripcion_ = inglesaprobado
                        if not preinscripcion.inglesaprobado and preinscripcion.computacionaprobado:
                            validar_preinscripcion_ = computacionaprobado
                        if preinscripcion.inglesaprobado and preinscripcion.computacionaprobado:
                            validar_preinscripcion_ = (computacionaprobado and inglesaprobado)
                        data['validar_preinscripcion_'] = validar_preinscripcion_
                    data['itinerarios'] = itinerarios
                    data['falta_horas'] = falta_horas
                    data['cant_preg'] = cant_preguntas
                    data['respondio'] = respondio
                    data['idinscripcion'] = inscripcion.id
                    data['inscripcion'] = inscripcion
                    data['nivel'] = minivel = inscripcion.mi_nivel().nivel.orden + 1
                    data['mostrarmensajenotiene'] = False if not itinerarios and minivel > 5 else True
                    data['carreraconfigurada'] = carreraconfigurada

                    if carreraconfigurada:
                        template = get_template("alu_preinscripcionppp/addpreinscripcion.html")
                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", "data": json_content, "title":preinscripcion.motivo if preinscripcion else ''})
                    else:
                        return JsonResponse({"result": "bad", "mensaje":"Su carrera no esta configurada para pre-inscripciones de prácticas"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", 'mensaje': u'Error al obtener los datos.'})

            elif action == 'preinscripcionppp':
                try:
                    if 'idp' in request.POST and 'id' in request.POST:
                        inscripcion = Inscripcion.objects.get(id=int(request.POST['id']))

                        nivelalumno = inscripcion.mi_nivel().nivel if inscripcion.coordinacion.id != 1 else None

                        # VALIDAR QUE NO SE GRABE 2 VECES
                        if DetallePreInscripcionPracticasPP.objects.filter(preinscripcion_id=int(request.POST['idp']), inscripcion=inscripcion).exists():
                            li = json.loads(request.POST['listapreinscripcion'])
                            if len(li) > 0:
                                for i in li:
                                    if DetallePreInscripcionPracticasPP.objects.filter(status=True, preinscripcion_id=int(request.POST['idp']), inscripcion=inscripcion,itinerariomalla_id=i).exclude(estado=3).exists():
                                        return JsonResponse({"result": "bad", 'mensaje': u'La pre-inscripción ya ha sido grabada.'})

                        for i in json.loads(request.POST['listapreinscripcion']):
                            detalle = DetallePreInscripcionPracticasPP(preinscripcion_id= int(request.POST['idp']),
                                                                       inscripcion=inscripcion,
                                                                       nivelmalla=nivelalumno,
                                                                       itinerariomalla_id=None if int(i) == 0 else int(i),
                                                                       estado=1,
                                                                       fecha=datetime.now())
                            detalle.save(request)
                            pdf, response = generar_acta_compromiso_v2(detalle)
                            if pdf:
                                extradetalle = ExtraDetallePreInscripcionPracticasPP(detallepreins=detalle, actacompromisopracticas=pdf)
                                extradetalle.save(request)
                            log(u'Adicionó una Pre-Inscripción de practicas preprofecionales: %s el estudiante: %s' % (detalle, inscripcion), request, "add")
                        lr = json.loads(request.POST['listarespuesta'])
                        if len(lr)>0:
                            if not DetalleRespuestaPreInscripcionPPP.objects.filter(status=True, preinscripcion_id=int(request.POST['idp']), inscripcion=inscripcion).exists():
                                lista = []
                                for r in json.loads(request.POST['listarespuesta']):
                                    lista.append(int(r[1]))
                                resp = RespuestaPreInscripcionPracticasPP.objects.filter(status=True, id__in=lista)
                                res = DetalleRespuestaPreInscripcionPPP(preinscripcion_id=int(request.POST['idp']), inscripcion=inscripcion)
                                res.save(request)
                                # res.respuesta=resp
                                for r in resp:
                                    res.respuesta.add(r)
                                res.save(request)
                        return JsonResponse({'result': 'ok'})
                    else:
                        return JsonResponse({"result": "bad", 'mensaje': u'Error al guardar los datos.'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, Error en el sistema.'})

            elif action == 'delpreinscripcion':
                try:
                    detalle = DetallePreInscripcionPracticasPP.objects.get(pk=int(request.POST['id']))
                    if detalle.estado == 1:
                        if detalle.solicitudvinculacionpreinscripcionpracticaspp_set.filter(status=True).exists():
                            return JsonResponse({"result": "bad", "mensaje": "Acción no permitida, usted cuenta con una solicitud de asignación de tutor activa."})
                        if detalle.puede_eliminar_todo(inscripcion):
                            respuestas = DetalleRespuestaPreInscripcionPPP.objects.filter(inscripcion=detalle.inscripcion, preinscripcion=detalle.preinscripcion)
                            if respuestas:
                                for r in respuestas:
                                    r.delete()
                            detalle.delete()
                        else:
                            detalle.delete()
                        log(u'Eliminó la pre-inscripción de practicas preprofecionales: %s' % detalle, request, "del")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

            elif action == 'delarchivo':
                try:
                    detalle = DetallePreInscripcionPracticasPP.objects.get(pk=int(request.POST['id']))
                    if detalle.puede_eliminar():
                        detalle.archivo.delete()
                        detalle.save()
                        log(u'Eliminó solicitud de empresa pre-inscripción de practicas preprofesionales: %s' % detalle, request, "del")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "Acción no permitida fuera de fecha."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

            elif action == 'actualizarrespuesta':
                try:
                    if 'idpre' in request.POST and 'idp' in request.POST and 'idr' in request.POST:
                        if DetalleRespuestaPreInscripcionPPP.objects.filter(status=True, preinscripcion_id=int(request.POST['idpre']), inscripcion_id=inscripcion.id).exists():
                            detalle = DetalleRespuestaPreInscripcionPPP.objects.filter(status=True, preinscripcion_id=int(request.POST['idpre']), inscripcion_id=inscripcion.id)[0]
                            if detalle.respuesta:
                                resp = RespuestaPreInscripcionPracticasPP.objects.filter(pk=int(request.POST['idr']))
                                # detalle.respuesta= resp
                                for r in resp:
                                    detalle.respuesta.add(r)
                                detalle.save()
                                log(u'Eliminó la pre-inscripción de practicas preprofecionales: %s' % detalle, request, "del")
                        else:
                            detalle = DetalleRespuestaPreInscripcionPPP(preinscripcion_id=int(request.POST['idpre']), inscripcion_id=inscripcion.id)
                            detalle.save()
                            # detalle.respuesta=RespuestaPreInscripcionPracticasPP.objects.filter(pk=int(request.POST['idr']))
                            resp = RespuestaPreInscripcionPracticasPP.objects.filter(pk=int(request.POST['idr']))
                            for r in resp:
                                detalle.respuesta.add(r)
                            detalle.save(request)
                            log(u'Eliminó la pre-inscripción de practicas preprofecionales: %s' % detalle, request, "del")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

            elif action == 'aceptar_practica':
                try:
                    if 'id' in request.POST:
                        preins = DetallePreInscripcionPracticasPP.objects.get(pk=int(request.POST['id']))
                        pract = PracticasPreprofesionalesInscripcion(preinscripcion=preins,
                                                                      inscripcion=preins.inscripcion,
                                                                      itinerariomalla=preins.itinerariomalla if preins.itinerariomalla else None,
                                                                      tipo=preins.tipo,
                                                                      fechadesde=preins.fechadesde,
                                                                      fechahasta=preins.fechahasta,
                                                                      tutorunemi=preins.tutorunemi if preins.tutorunemi else None,
                                                                      supervisor=preins.supervisor if preins.supervisor else None,
                                                                      numerohora=preins.numerohora,
                                                                      tiposolicitud=1,
                                                                      empresaempleadora=preins.empresaempleadora if preins.empresaempleadora else None,
                                                                      otraempresaempleadora=preins.otraempresaempleadora,
                                                                      tipoinstitucion=preins.tipoinstitucion if preins.tipoinstitucion else None,
                                                                      sectoreconomico=preins.sectoreconomico if preins.sectoreconomico else None,
                                                                      departamento=preins.departamento if preins.departamento else None,
                                                                      periodoevidencia=preins.periodoevidencia if preins.periodoevidencia else None,
                                                                      fechaasigtutor=datetime.now().date(),
                                                                      fechaasigsupervisor=datetime.now().date())
                        pract.save(request)
                        log(u'El estudiante %s acepto la asignacion de práctica preprofecionales a la empresa: %s' % (preins.inscripcion, preins.empresaempleadora if preins.empresaempleadora else preins.otraempresaempleadora), request, "del")
                        if preins.estado==2:
                            if not preins.detallerecoridopreinscripcionpracticaspp_set.filter(status=True).exists():
                                recorrido = DetalleRecoridoPreInscripcionPracticasPP(preinscripcion=preins,
                                                                                     fecha=preins.fecha,
                                                                                     observacion=u'Asignado',
                                                                                     estado=2)
                                recorrido.save(request)
                        recorrido = DetalleRecoridoPreInscripcionPracticasPP(preinscripcion=preins,
                                                                             fecha=datetime.now().date(),
                                                                             observacion=u'Acepto la asignacion de práctica Preprofesionales',
                                                                             estado=5,
                                                                             esestudiante=True)
                        recorrido.save(request)
                        preins.estado=5
                        preins.save(request)
                        emailestudiante = preins.inscripcion.persona.lista_emails_envio()
                        estudiante = preins.inscripcion.persona.nombre_completo_inverso()
                        asunto = u"Asignación de cupo para Prácticas Preprofesionales"
                        send_html_mail(asunto, "emails/tutor_practicas_alumno.html",
                                       {'sistema': request.session['nombresistema'],
                                        'estudiante': estudiante}, emailestudiante, [],
                                       cuenta=CUENTAS_CORREOS[4][1])
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

            elif action == 'rechazar_practica':
                try:
                    if 'id' in request.POST:
                        form = RechazarAsignacionPracticaFrom(request.POST)
                        if form.is_valid():
                            preins = DetallePreInscripcionPracticasPP.objects.get(pk=int(request.POST['id']))
                            recorrido = DetalleRecoridoPreInscripcionPracticasPP(preinscripcion=preins,
                                                                                 fecha=datetime.now().date(),
                                                                                 observacion=form.cleaned_data['observacion'],
                                                                                 estado=3,
                                                                                 esestudiante=True)
                            recorrido.save(request)
                            log(u'El estudiante %s rechazo la asignacion de práctica-inscripción de practicas preprofecionales: %s' % (preins.inscripcion, preins.empresaempleadora if preins.empresaempleadora else preins.otraempresaempleadora), request, "del")
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

            elif action == 'subirdocumento':
                try:
                    preins = DetallePreInscripcionPracticasPP.objects.get(pk=int(request.POST['id']))
                    if 'archivo' in request.FILES:
                        nombrepersona = remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode((preins.inscripcion.persona.nombres).replace(' ', '_')))
                        nombredocumento = '{}_{}'.format(nombrepersona, random.randint(1, 100000).__str__())
                        arch = request.FILES['archivo']
                        arch._name = generar_nombre(nombredocumento, arch._name)
                        extension = arch._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]

                        if arch.size > 4194304:
                            return JsonResponse({"result": "bad",
                                                 "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                        if not exte.lower() == 'pdf':
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})
                    f = DocumentoPracticasPPPForm(request.POST, request.FILES)
                    if f.is_valid():
                        if preins.archivo:
                            preins.archivo.delete()
                            preins.save(request)
                        preins.archivo = arch
                        preins.convenioempresa=f.cleaned_data['empresa']
                        preins.otraempresaempleadora=f.cleaned_data['empresaotra']
                        preins.pais = f.cleaned_data['pais']
                        preins.provincia = f.cleaned_data['provincia']
                        preins.canton = f.cleaned_data['canton']
                        preins.telefonoempresa = f.cleaned_data['telefonoempresa']
                        preins.email = f.cleaned_data['emailempresa']
                        preins.direccion = f.cleaned_data['direccion']
                        preins.tipoinstitucion = f.cleaned_data['tipoinstitucion']
                        preins.fechaarchivo = datetime.now().date()
                        preins.horaarchivo = datetime.now().time()
                        preins.save(request)
                        recorrido = DetalleRecoridoPreInscripcionPracticasPP(preinscripcion=preins,
                                                                             fecha=datetime.now().date(),
                                                                             observacion='ARCHIVO CORREGIDO',
                                                                             estado=1,
                                                                             esestudiante=True)
                        recorrido.save(request)
                        messages.success(request,'Estimado(a) estudiante una vez validada su solicitud el departamento le asignará un tutor, la notificación le llegará automáticamente a su correo institucional.')
                        log(u'Cargó carta para practicas %s - %s' % (persona, preins), request,"add")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Datos incorrectos')
                except Exception as ex:
                    msg = ex.__str__()
                    transaction.set_rollback(True)
                    return JsonResponse(
                        {"result": "bad", "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

            elif action == 'solicitarempresa':
                try:
                    postar = DetallePreInscripcionPracticasPP.objects.get(id=int(request.POST['id']))
                    form = SolicitudEmpresaPreinscripcionForm(request.POST)
                    if form.is_valid():
                        year = datetime.now().strftime('%Y')
                        numsolicitudporanio = DatosEmpresaPreInscripcionPracticasPP.objects.filter(fecha_creacion__year=year).count() + 1
                        codsolicitud = generar_codigo(numsolicitudporanio, PREFIX, SUFFIX)

                        # if DatosEmpresaPreInscripcionPracticasPP.objects.filter(status=True, preinscripcion=postar).exists():
                        #     datosempresa = DatosEmpresaPreInscripcionPracticasPP.objects.filter(status=True, preinscripcion=postar)
                        #     for d in datosempresa:
                        #         d.est_empresas=3
                        #         d.save(request)
                        datosempresa = DatosEmpresaPreInscripcionPracticasPP(preinscripcion=postar, dirigidoa=form.cleaned_data['dirigidoa'], empresa=form.cleaned_data['empresa'],
                                                                             cargo=form.cleaned_data['cargo'], correo=form.cleaned_data['correo'], telefono=form.cleaned_data['telefono'],
                                                                             direccion=form.cleaned_data['direccion'], numerodocumento=numsolicitudporanio, codigodocumento=codsolicitud)
                        datosempresa.save(request)
                        log(u'Solicito Empresa Preinscripción Practicas : %s %s' % (postar, postar.inscripcion), request, "add")
                        return JsonResponse({"result": False, 'mensaje': 'Solicitud Generada, debe ser aprobado por vinculación para descargar el formato.', 'modalsuccess': True}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "mensaje": "Error en el formulario" })
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": u"Error al obtener los datos. {}".format(ex)})

            elif action == 'detalleobservacion':
                try:
                    data['pre'] = pre = DetallePreInscripcionPracticasPP.objects.get(pk=int(request.POST['id']))
                    data['detalles'] = pre.detallerecoridopreinscripcionpracticaspp_set.filter(status=True).order_by(
                        '-fecha')
                    template = get_template("alu_practicaspreprofesionalesinscripcion/detalleobservacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

            elif action == 'addtutor':
                try:
                    id, newfile = request.POST['id'], None
                    preinscripcion = DetallePreInscripcionPracticasPP.objects.get(pk=id)
                    if 'documentoaceptacion' in request.FILES:
                        newfile = request.FILES['documentoaceptacion']
                        if newfile.size > 8194304:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 8 Mb."})
                        else:
                            newfilename = newfile._name
                            ext = newfilename[newfilename.rfind("."):]
                            if not ext == '.pdf':
                                return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                    f = AsignacionTutorForm(request.POST)
                    if f.is_valid():
                        isnew = True
                        if SolicitudVinculacionPreInscripcionPracticasPP.objects.filter(status=True, preinscripcion=preinscripcion).exists():
                            isnew = False
                            asignacion = SolicitudVinculacionPreInscripcionPracticasPP.objects.filter(status=True, preinscripcion=preinscripcion).first()
                        else:
                            if not 'documentoaceptacion' in request.FILES:
                                return JsonResponse({"result": "bad", "mensaje": u"Debe subir documento de aceptación."})
                            asignacion = SolicitudVinculacionPreInscripcionPracticasPP(preinscripcion=preinscripcion)
                        asignacion.tipovinculacion=f.cleaned_data['tipovinculacion']
                        asignacion.tipopracticas=f.cleaned_data['tipopracticas']
                        asignacion.acuerdo=f.cleaned_data['acuerdo']
                        asignacion.convenio=f.cleaned_data['convenio']
                        asignacion.direccion=f.cleaned_data['direccion']
                        asignacion.empresanombre=f.cleaned_data['empresanombre']
                        asignacion.empresaruc=f.cleaned_data['empresaruc']
                        asignacion.tipoinstitucion=f.cleaned_data['tipoinstitucion']
                        asignacion.sectoreconomico=f.cleaned_data['sectoreconomico']
                        asignacion.empresatelefonos=f.cleaned_data['empresatelefonos']
                        asignacion.empresaemail=f.cleaned_data['empresaemail']
                        asignacion.empresacanton=f.cleaned_data['empresacanton']
                        asignacion.empresadireccion=f.cleaned_data['empresadireccion']
                        asignacion.dirigidoa=f.cleaned_data['dirigidoa']
                        asignacion.cargo=f.cleaned_data['cargo']
                        asignacion.telefonos=f.cleaned_data['telefonos']
                        asignacion.email=f.cleaned_data['email']
                        asignacion.ccemail=f.cleaned_data['ccemail']
                        asignacion.estado=1
                        asignacion.save(request)
                        if newfile:
                            nombrepersona = remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode((preinscripcion.inscripcion.persona.__str__()).replace(' ', '_')))
                            nombredocumento = '{}_{}'.format(nombrepersona, random.randint(1, 100000).__str__())
                            newfile._name = generar_nombre(nombredocumento, newfile._name)
                            asignacion.archivo = newfile
                            asignacion.fechaarchivo = datetime.now().date()
                            asignacion.horaarchivo = datetime.now().time()
                            asignacion.save(request)
                            preinscripcion.archivo = newfile
                            preinscripcion.fechaarchivo = datetime.now().date()
                            preinscripcion.horaarchivo = datetime.now().time()
                            preinscripcion.save(request)
                            log(u'Cargó carta para practicas %s - %s' % (persona, preinscripcion), request,"add")
                        messages.success(request,'Estimado(a) estudiante una vez validada su solicitud el departamento le asignará un tutor, la notificación le llegará automáticamente a su correo institucional.')
                        if isnew:
                            log(u'Solicito asignación docente practicas profesionales: %s' % asignacion, request, "add")
                        else:
                            log(u'Edito Solicitud de asignación docente practicas profesionales: %s' % asignacion, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'addtutor':
                try:
                    data['title'] = u'Solicitud de vinculación a practicas preprofesionales'
                    data['filtro'] = filtro = DetallePreInscripcionPracticasPP.objects.get(pk=int(request.GET['id']))
                    if  not filtro.estado in [1, 5]:
                        messages.warning(request, 'Preinscripción ya no esta habilitada.')
                        return redirect('{}'.format(request.path))
                    fechaactual, filtroacuerdoconvenio = datetime.now().date(), Q(para_practicas=True)
                    acuerdoqs = AcuerdoCompromiso.objects.filter(status=True, fechafinalizacion__gte=fechaactual, carrera=inscripcion.carrera).order_by('empresa__nombre')
                    convenioqs = ConvenioEmpresa.objects.filter(status=True, fechafinalizacion__gte=fechaactual,  conveniocarrera__carrera=inscripcion.carrera).order_by('empresaempleadora__nombre')
                    solicitudqs = SolicitudVinculacionPreInscripcionPracticasPP.objects.filter(status=True, preinscripcion=filtro)
                    if solicitudqs.exists():
                        data['solprevia'] = solprevia = solicitudqs.first()
                        form = AsignacionTutorForm(initial=model_to_dict(solprevia))
                        if solprevia.tipovinculacion == 2:
                            filtroacuerdoconvenio = Q(para_pasantias=True)
                    else:
                        form = AsignacionTutorForm()
                    form.fields['acuerdo'].queryset = acuerdoqs.filter(filtroacuerdoconvenio)
                    form.fields['convenio'].queryset = convenioqs.filter(filtroacuerdoconvenio)
                    form.fields['empresapais'].queryset = Pais.objects.none()
                    form.fields['empresaprovincia'].queryset = Provincia.objects.none()
                    form.fields['empresacanton'].queryset = Canton.objects.none()
                    data['form'] = form
                    # id de criterios de practicas 154 es nuevo y 6 anterior, para filtrar todos
                    qsdocentes = ActividadDetalleDistributivoCarrera.objects.filter(actividaddetalle__criterio__criteriodocenciaperiodo__criterio__id__in=[6, 154], actividaddetalle__criterio__distributivo__periodo=filtro.preinscripcion.periodo, actividaddetalle__criterio__distributivo__status=True, status=True, carrera=filtro.inscripcion.carrera, itinerariosactividaddetalledistributivocarrera__itinerario=filtro.itinerariomalla)
                    if qsdocentes.exists():
                        cupodisponible = 0
                        for doc in qsdocentes:
                            cupodisponible += doc.get_disponbile()
                        data['docentescarrera'] = qsdocentes
                        data['cupodisponible'] = int(cupodisponible)
                        if cupodisponible > 0:
                            return render(request, "alu_preinscripcionppp/formasignacion.html", data)
                        else:
                            messages.warning(request, 'No existen docentes disponibles para vincular')
                            return redirect('{}'.format(request.path))
                    else:
                        messages.warning(request, 'No existen docentes disponibles para vincular')
                        return redirect('{}'.format(request.path))
                except Exception as ex:
                    pass

            if action == 'buscarnombreempresas':
                try:
                    q = request.GET['q'].upper().strip()
                    emmpresas = EmpresaEmpleadora.objects.filter(status=True).filter(nombre__icontains=q).distinct('nombre')[:15]
                    data = {"result": "ok", "results": [{"id": x.id, "nombre": str(x.nombre)} for x in emmpresas]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'traerconvenios':
                try:
                    lista = []
                    filtro, id, tipo = Q(status=True), request.GET['id'], int(request.GET['tipo'])
                    if tipo:
                        if tipo == 1:
                            filtro = filtro & Q(para_practicas=True)
                        if tipo == 2:
                            filtro = filtro & Q(para_pasantias=True)
                    fechaactual = datetime.now().date()
                    inscrip = DetallePreInscripcionPracticasPP.objects.get(pk=int(id))
                    listado = ConvenioEmpresa.objects.filter(filtro).filter(fechafinalizacion__gte=fechaactual, conveniocarrera__carrera=inscripcion.carrera)
                    for p in listado.distinct():
                        lista.append([p.id, p.__str__()])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'traeracuerdos':
                try:
                    lista = []
                    filtro, id, tipo = Q(status=True), request.GET['id'], int(request.GET['tipo'])
                    if tipo:
                        if tipo == 1:
                            filtro = filtro & Q(para_practicas=True)
                        if tipo == 2:
                            filtro = filtro & Q(para_pasantias=True)
                    inscrip = DetallePreInscripcionPracticasPP.objects.get(pk=int(id))
                    fechaactual = datetime.now().date()
                    listado = AcuerdoCompromiso.objects.filter(filtro).filter(carrera=inscrip.inscripcion.carrera, fechafinalizacion__gte=fechaactual)
                    for p in listado.distinct():
                        lista.append([p.id, p.__str__()])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'missolicitudesempresa':
                try:
                    data['filtro'] = filtro = DetallePreInscripcionPracticasPP.objects.get(pk=int(request.GET['id']))
                    form = SolicitudEmpresaPreinscripcionForm()
                    data['form2'] = form
                    template = get_template("alu_preinscripcionppp/modal/missolicitudesempresas.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'delpreinscripcion':
                try:
                    data['title'] = u'Eliminar pre-inscripción de Práctica Pre-Profesional'
                    data['pre'] = DetallePreInscripcionPracticasPP.objects.get(pk=int(request.GET['id']))
                    return render(request, "alu_preinscripcionppp/delpreinscripcion.html", data)
                except Exception as ex:
                    pass

            if action == 'delarchivo':
                try:
                    data['title'] = u'Eliminar archivo de pre-inscripción'
                    data['pre'] = DetallePreInscripcionPracticasPP.objects.get(pk=int(request.GET['id']))
                    return render(request, "alu_preinscripcionppp/delarchivo.html", data)
                except Exception as ex:
                    pass

            elif action == 'aceptar_practica':
                try:
                    data['title'] = u'Aceptar asignación de práctica pre profesional'
                    data['pre'] = DetallePreInscripcionPracticasPP.objects.get(pk=request.GET['id'])
                    return render(request, "alu_preinscripcionppp/aceptar_practica.html", data)
                except Exception as ex:
                    pass

            elif action == 'rechazar_practica':
                try:
                    data['title'] = u'Rechazar asignación de práctica pre profesional'
                    data['form'] = RechazarAsignacionPracticaFrom()
                    data['pre'] = DetallePreInscripcionPracticasPP.objects.get(pk=request.GET['id'])
                    template = get_template("alu_preinscripcionppp/rechazar_practica.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'subirdocumento':
                try:
                    data['title'] = u'<i class="fa fa-upload"></i> Subir Acta de Aceptación' if not coordinacion == 1 else u'<i class="fa fa-upload"></i> Subir documento de prioridad'
                    data['idm'] = request.GET['id']
                    data['filtro'] = filtro = DetallePreInscripcionPracticasPP.objects.get(id=request.GET['id'],status=True)
                    data['form'] = DocumentoPracticasPPPForm(initial={
                        'empresa':filtro.convenioempresa,
                        'empresaotra':filtro.otraempresaempleadora,
                        'tipoinstitucion':filtro.tipoinstitucion,
                        'emailempresa':filtro.email,
                        'telefonoempresa':filtro.telefonoempresa,
                        'pais':filtro.pais,
                        'provincia':filtro.provincia,
                        'canton':filtro.canton,
                        'direccion':filtro.direccion,
                        'archivo':filtro.archivo,
                    })

                    template = get_template("alu_preinscripcionppp/subirdocumento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'solicitudpdf':
                try:
                    filtro = DatosEmpresaPreInscripcionPracticasPP.objects.get(pk=encrypt(request.GET['pk']))
                    directory = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'solicitudempresas')
                    try:
                        os.stat(directory)
                    except:
                        os.mkdir(directory)
                    return JsonResponse({"result": 'ok', 'url': f"{filtro.archivodescargar.url}" if filtro.archivodescargar else ''})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        else:
            try:
                data['title'] = u'Pre-Inscripcion de prácticas preprofesionales'
                data['idalu'] = inscripcion.id
                data['inscripcion'] = inscripcion

                fechainicioprimernivel = inscripcion.fechainicioprimernivel if inscripcion.fechainicioprimernivel else datetime.now().date()
                excluiralumnos = datetime(2009, 1, 21, 23, 59, 59).date()
                data['esexonerado'] = fechainicioprimernivel <= excluiralumnos
                data['cumple'] = cumple = int(request.GET.get('cumple', 0))

                if coordinacion == 1:
                    conf = PreInscripcionPracticasPP.objects.filter(fechainicio__lte=datetime.now().date(), fechafin__gte=datetime.now().date(), coordinacion__in=[1])
                    data['inglesaprobado'] = haber_aprobado_modulos_ingles(inscripcion.id)
                    data['computacionaprobado'] = haber_aprobado_modulos_computacion(inscripcion.id)
                else:
                    conf = PreInscripcionPracticasPP.objects.filter(fechainicio__lte=datetime.now().date(), fechafin__gte=datetime.now().date(), coordinacion=coordinacion)
                lista = DetallePreInscripcionPracticasPP.objects.values_list('preinscripcion__id', flat=False).filter(status=True, inscripcion=inscripcion).distinct('preinscripcion')
                data['confpre'] = confpre = PreInscripcionPracticasPP.objects.filter(id__in=lista)
                data['conf'] = conf[0] if conf else []
                mensajeestudiante = False
                if 'mensaje' in request.GET:
                    mensajeestudiante = True
                data['mensajeestudiante'] = mensajeestudiante
                # data['preinscripciones'] = inscripcion.detallepreinscripcionpracticaspp_set.filter(status=True)
                # data['conf'] = PreInscripcionPracticasPP(id__in=inscripcion.detallepreinscripcionpracticaspp_set.values_list('preinscripcion_id', flat=True).filter(status=True))
                if not inscripcion.inscripcionmalla_set.values('id').exists():
                    return HttpResponseRedirect("/?info=Debe tener malla asociada para poder inscribirse.")
                data['puede_preinscribirseppp'] = x = inscripcion.puede_preinscribirseppp()
                return render(request, "alu_preinscripcionppp/view.html", data)
            except Exception as ex:
                return redirect('/?info={}'.format(ex))


# def inglesaprobado(inscripcion):
#     if inscripcion:
#         inscripcionmalla = inscripcion.malla_inscripcion()
#         modulomalla = inscripcionmalla.malla.modulomalla_set.filter(status=True).values_list('asignatura_id', flat=True)
#         aprobadas = inscripcion.recordacademico_set.filter(aprobada=True, status=True, asignatura_id__in=modulomalla).values_list('asignatura_id', flat=True)
#         return len(modulomalla) == len(aprobadas)
#     return False
