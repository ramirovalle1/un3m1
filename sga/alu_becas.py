# -*- coding: UTF-8 -*-
import json
import os
import sys

import pyqrcode
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction, connections
from django.db.models import F
from django.db.models.query_utils import Q
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
import xlwt
from xlwt import *
import random
from datetime import datetime, date
from django.template.loader import get_template
from django.template import Context
from decorators import secure_module, last_access
from sagest.forms import DiscapacidadForm
from sagest.models import Banco, TipoCuentaBanco
from settings import DEBUG, SITE_STORAGE
from sga.commonviews import adduserdata, secuencia_contrato_beca_aux, matricular
from sga.forms import BecaTipoForm, BecaUtilizacionForm, BecaRequisitosForm, BecaDetalleSolicitudArchivoForm, \
    BecaDetalleUtilizacionForm, BecaSolicitudSubirCedulaForm, RepresentanteSolidarioForm, BecaAceptarRechazarForm, \
    BecaSolicitudAnularForm, CuentaBancariaBecadoForm, BecaSubirContratoForm, BecaComprobanteVentaForm, \
    BecaComprobanteVentaEditForm
from sga.funciones import MiPaginador, log, variable_valor, generar_nombre, validarcedula, fechaletra_corta, \
    lista_mejores_promedio_beca_v2, lista_discapacitado_beca_v2, lista_deportista_beca_v2, lista_migrante_beca_v2, \
    lista_exterior_beca_v2, lista_etnia_beca_v2, lista_gruposocioeconomico_beca_v2, \
    leer_fecha_hora_letra_formato_fecha_hora, elimina_tildes
from sga.funcionesxhtml2pdf import conviert_html_to_pdf, conviert_html_to_pdfsaveqr_generico
from sga.models import Inscripcion, BecaTipo, BecaDetalleUtilizacion, \
    BecaAsignacion, BecaUtilizacion, BecaRequisitos, MatriculaGrupoSocioEconomico, Matricula, Periodo, MateriaAsignada, \
    BecaSolicitud, BecaDetalleSolicitud, PerfilInscripcion, BecaPeriodo, DetalleTitulacionBachiller, \
    PersonaDocumentoPersonal, BecaSolicitudRecorrido, miinstitucion, BecaSolicitudNecesidad, CuentaBancariaPersona, \
    BecaComprobanteVenta, Persona, MESES_CHOICES, BecaComprobanteRevision, PreInscripcionBeca, BecaTipoConfiguracion, \
    BecaSolicitudHistorialDocumentoPersonal
from sga.tasks import send_html_mail, conectar_cuenta
from socioecon.models import FichaSocioeconomicaINEC, GrupoSocioEconomico


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if not request.session['periodo']:
        return HttpResponseRedirect("/?info=No tiene periodo asignado.")
    data['periodo'] = periodo = request.session['periodo']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    inscripcion = perfilprincipal.inscripcion
    periodos_estudiante = Periodo.objects.filter(nivel__matricula__inscripcion=inscripcion, status=True,
                                                 nivel__status=True, nivel__matricula__status=True,
                                                 nivel__matricula__inscripcion__status=True).order_by('-inicio')

    y = periodos_estudiante.filter(status=True, id__lte=periodo.id, tipo=2).exclude(id=periodo.id).order_by("-id")
    data['anterior'] =anterior=None
    if y:
        data['anterior'] = anterior = y[0]
    if not Matricula.objects.filter(inscripcion__persona=persona, nivel__periodo=periodo).exists():
        return HttpResponseRedirect("/?info=Debe Estar Matriculado en el Periodo Actual Para Ingresar al Modulo.")
    hoy = datetime.now().date()
    if not BecaPeriodo.objects.filter(status=True,periodo=periodo,fechainiciosolicitud__lte=hoy, fechafinsolicitud__gte=hoy).exists():
        if BecaAsignacion.objects.filter(solicitud__inscripcion=inscripcion, solicitud__periodo=periodo).exists():
            esbecado = True
            data['esbecado'] = esbecado
        # else:
        #     return HttpResponseRedirect("/?info=El periodo de postulación ha terminado.")
    data['debeactualizar'] = False
    if Matricula.objects.filter(inscripcion__persona=persona, nivel__periodo=periodo,nivelmalla__id=1).exists():
        data['esprimernivel']=True
        if DetalleTitulacionBachiller.objects.filter(titulacion__persona=persona).exists():
            data['bachiller']=bachiller=DetalleTitulacionBachiller.objects.filter(titulacion__persona=persona)[0]
            becaperiodo=BecaPeriodo.objects.filter(status=True, periodo=periodo)[0]
            if bachiller.calificacion>=8.5 and bachiller.actagrado !="" and bachiller.anioinicioperiodograduacion==becaperiodo.fechainiciocolegio and bachiller.aniofinperiodograduacion==becaperiodo.fechafincolegio:
                data['cumplecalificacion']=True
            else:
                data['cumplecalificacion'] = False
        else:
            data['debeactualizar'] = True
    else:
        data['esprimernivel'] = False
    if request.method == 'POST':
        action = request.POST['action']
        # if action == 'asignar':
        #     try:
        #         id = int(request.POST['id'])
        #         tipo = int(request.POST['tipo'])
        #         if not BecaAsignacion.objects.filter(inscripcion_id=id).exists() :
        #             becaasignacion = BecaAsignacion(inscripcion_id=id,
        #                                             becatipo_id=tipo)
        #             becaasignacion.save(request)
        #             log(u'Asigno un estudiante a beca: %s' % becaasignacion, request, "add")
        #             return JsonResponse({"result": "ok"})
        #         else:
        #             return JsonResponse({"result": "bad", "mensaje": u"Inscripcion ya asignada."})
        #     except Exception as ex:
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": "bad", "mensaje": u"Error al Asignar, Intentelo mas tarde."})
        #
        # elif action == 'notificar':
        #     asunto = u"NOTIFICACION DE BECA"
        #     id = int(request.POST['id'])
        #     becado = BecaAsignacion.objects.get(inscripcion__id=id, status=True)
        #     send_html_mail(asunto, "emails/notificarbecado.html",
        #                    {'sistema': request.session['nombresistema'],
        #                     'alumno': becado.inscripcion.persona.nombre_completo_inverso()},
        #                    becado.inscripcion.persona.lista_emails_envio(), [],
        #                    cuenta=variable_valor('CUENTAS_CORREOS')[0])

        if action == 'subirdocumentoetnia':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"No se encontro solicitud"})
                solicitud = BecaSolicitud.objects.get(pk=int(request.POST['id']))
                if solicitud.becatipo.id != 21:
                    return JsonResponse({"result": "bad", "mensaje": u"No se puede subir el documento porque no pertenece a pueblos y nacionalidades"})
                if persona.validado_estado_documento_raza():
                    return JsonResponse({"result": "bad", "mensaje": u"Los documentos no se pueden volver a cargar porque ya fueron verificados por Bienestar."})
                if not 'raza' in request.FILES:
                    return JsonResponse({"result": "bad", "mensaje": u"Registre documento de declaración juramentada."})
                newfile = None
                if 'raza' in request.FILES:
                    arch = request.FILES['raza']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if not exte.lower() == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})
                    newfile = request.FILES['raza']
                    newfile._name = generar_nombre("etnia", newfile._name)
                perfilinscripcion = persona.perfilinscripcion_set.filter(status=True).first()
                perfilinscripcion.archivoraza = newfile
                perfilinscripcion.estadoarchivoraza = 1
                perfilinscripcion.save(request)
                beca = solicitud.becaasignacion_set.all()[0]
                beca.personarevisadocumento = None
                beca.save(request)
                recorrido = BecaSolicitudRecorrido(solicitud=solicitud,
                                                   observacion="DECLARACIÓN JURAMENTADA CARGADA",
                                                   estado=9,
                                                   fecha=datetime.now().date())
                recorrido.save(request)
                log(u'Agregó documentos de declaración juramentada: %s' % persona, request, "add")
                messages.add_message(request, messages.SUCCESS, f'Se subio correctamente el documento')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. Detalle: %s" % msg})

        elif action == 'solicitarbeca':
            try:
                periodovalida = int(request.POST['periodovalida'])
                tipobeca = int(request.POST['tipobeca'])
                #necesidad = int(request.POST['necesidad'])
                if not BecaSolicitud.objects.filter(inscripcion=inscripcion, periodo=periodo, periodocalifica=periodovalida).exclude(estado=5).exists():
                    requisitos = json.loads(request.POST['lista_items1'])
                    beca = BecaSolicitud(inscripcion=inscripcion,
                                         becatipo_id=tipobeca,
                                         periodo=periodo,
                                         periodocalifica_id=periodovalida,
                                         estado=1,
                                         observacion='SEMESTRE MAYO - SETIEMBRE 2020 V2  - MODALIDAD VIRTUAL'
                                         )

                    beca.save(request)

                    for r in requisitos:
                        detalle = BecaDetalleSolicitud(solicitud=beca,
                                                       requisito_id=int(r['id']),
                                                       cumple=True if r['cumple'] == 'SI' else False,
                                                       archivo=None,
                                                       estado=1 if int(r['id']) in [15, 16] else 2,
                                                       observacion='' if int(r['id']) in [15, 16] else 'APROBACIÓN AUTOMÁTICA',
                                                       personaaprueba=None,
                                                       fechaaprueba=None)
                        detalle.save(request)


                    #necesidadsolicitud = BecaSolicitudNecesidad(solicitud=beca, necesidad=necesidad)
                    #necesidadsolicitud.save(request)


                    recorrido = BecaSolicitudRecorrido(solicitud=beca,
                                                       observacion="SOLICITADO POR ESTUDIANTE",
                                                       estado=1,
                                                       fecha=datetime.now().date()
                                                       )
                    recorrido.save(request)

                    tituloemail = "Registro de Solicitud de Beca - Semestre MAYO - SEPTIEMBRE 2020 V2"
                    tipobeca = beca.becatipo.nombre.upper()

                    send_html_mail(tituloemail,
                                   "emails/solicitudbecaestudiante.html",
                                   {'sistema': u'SGA - UNEMI',
                                    'tipo': 'SOL',
                                    'tipobeca': tipobeca,
                                    'fecha': datetime.now().date(),
                                    'hora': datetime.now().time(),
                                    'estudiante': persona,
                                    'autoridad2': '',
                                    't': miinstitucion()
                                    },
                                   persona.lista_emails_envio(),
                                   [],
                                   cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                   )

                    log(u'Agregó solicitud de beca: %s' % persona, request, "add")

                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"La solicitud de la beca ya ha sido creada."})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'subirdocumentocedula':
            try:
                # if persona.cedula_solicitante_representante_validadas() and persona.certificado_bancario_validado():
                solicitud = BecaSolicitud.objects.get(pk=int(request.POST['id']))

                if solicitud.verificar_documentos_validados():
                    return JsonResponse({"result": "bad", "mensaje": u"Los documentos no se pueden volver a cargar porque ya fueron verificados por Bienestar."})

                documentos = persona.documentos_personales()
                # cuentabancaria = persona.cuentabancaria()

                f = BecaSolicitudSubirCedulaForm(request.POST, request.FILES)

                if 'archivo1' in request.FILES:
                    arch = request.FILES['archivo1']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb. (Cédula Solicitante)"})
                    if not exte.lower() == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf (Cédula Solicitante)"})

                if 'archivo2' in request.FILES:
                    arch = request.FILES['archivo2']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb. (Certificado Solicitante)"})
                    if not exte.lower() == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf (Certificado Solicitante)"})

                if 'archivo3' in request.FILES:
                    arch = request.FILES['archivo3']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb. (Cédula Representante solidario)"})
                    if not exte.lower() == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf (Cédula Representante solidario)"})

                if 'archivo4' in request.FILES:
                    arch = request.FILES['archivo4']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb. (Certificado Representante solidario)"})
                    if not exte.lower() == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf (Certificado Representante solidario)"})

                if 'archivo5' in request.FILES:
                    arch = request.FILES['archivo5']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb. (Acta de grado)"})
                    if not exte.lower() == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf (Acta de grado)"})

                if 'archivo6' in request.FILES:
                    arch = request.FILES['archivo6']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb. (Servicio Básica)"})
                    if not exte.lower() == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf (Servicio Básica)"})

                if 'archivo7' in request.FILES:
                    arch = request.FILES['archivo7']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb. (Declaración juramentada)"})
                    if not exte.lower() == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf (Declaración juramentada)"})

                if f.is_valid():
                    if 'archivo1' in request.FILES:
                        newfile = request.FILES['archivo1']
                        newfile._name = generar_nombre("cedula", newfile._name)

                    if 'archivo2' in request.FILES:
                        newfile2 = request.FILES['archivo2']
                        newfile2._name = generar_nombre("certvotacion", newfile2._name)

                    if 'archivo3' in request.FILES:
                        newfile3 = request.FILES['archivo3']
                        newfile3._name = generar_nombre("cedularepsol", newfile3._name)

                    if 'archivo4' in request.FILES:
                        newfile4 = request.FILES['archivo4']
                        newfile4._name = generar_nombre("certvotacionrepsol", newfile4._name)

                    newfile5 = None
                    estadoacta = None
                    if 'archivo5' in request.FILES:
                        newfile5 = request.FILES['archivo5']
                        newfile5._name = generar_nombre("actagrado_", newfile5._name)
                        estadoacta = 1

                    newfile6 = None
                    serviciobasico = None
                    if 'archivo6' in request.FILES:
                        newfile6 = request.FILES['archivo6']
                        newfile6._name = generar_nombre("serviciobasico_", newfile6._name)
                        serviciobasico = 1

                    newfile7 = None
                    raza = None
                    if 'archivo7' in request.FILES:
                        newfile7 = request.FILES['archivo7']
                        newfile7._name = generar_nombre("raza_", newfile7._name)
                        raza = 1

                    if documentos is None:
                        documentos = PersonaDocumentoPersonal(persona=persona,
                                                              cedula=newfile,
                                                              estadocedula=1,
                                                              papeleta=newfile2,
                                                              estadopapeleta=1,
                                                              actagrado=newfile5,
                                                              estadoactagrado=estadoacta,
                                                              cedularepresentantesol=newfile3,
                                                              estadocedularepresentantesol=1,
                                                              papeletarepresentantesol=newfile4,
                                                              estadopapeletarepresentantesol=1,
                                                              serviciosbasico=newfile6,
                                                              estadoserviciosbasico=serviciobasico,
                                                              observacion=""
                                                             )
                    else:
                        if 'archivo1' in request.FILES:
                            documentos.cedula = newfile
                            documentos.estadocedula = 1

                        if 'archivo2' in request.FILES:
                            documentos.papeleta = newfile2
                            documentos.estadopapeleta = 1

                        if 'archivo3' in request.FILES:
                            documentos.cedularepresentantesol = newfile3
                            documentos.estadocedularepresentantesol = 1

                        if 'archivo4' in request.FILES:
                            documentos.papeletarepresentantesol = newfile4
                            documentos.estadopapeletarepresentantesol = 1

                        if 'archivo5' in request.FILES:
                            documentos.actagrado = newfile5
                            documentos.estadoactagrado = 1

                        if 'archivo6' in request.FILES:
                            documentos.serviciosbasico = newfile6
                            documentos.estadoserviciosbasico = 1

                        if 'archivo7' in request.FILES:
                            ds_raza = persona.perfilinscripcion_set.first()
                            ds_raza.archivoraza = newfile7
                            ds_raza.estadoarchivoraza = raza
                            ds_raza.verificaraza = False
                            ds_raza.observacionarchraza = None
                            ds_raza.save(request)

                        documentos.observacion = ""

                    documentos.save(request)


                    beca = solicitud.becaasignacion_set.all()[0]
                    beca.personarevisadocumento = None
                    beca.save(request)

                    if 'archivo1' in request.FILES or 'archivo2' in request.FILES or 'archivo3' in request.FILES or 'archivo4' in request.FILES or 'archivo5' in request.FILES or 'archivo6' in request.FILES or 'archivo7' in request.FILES:
                        recorrido = BecaSolicitudRecorrido(solicitud=solicitud,
                                                           observacion="DOCUMENTOS PERSONALES CARGADOS",
                                                           estado=9,
                                                           fecha=datetime.now().date())
                        recorrido.save(request)

                    log(u'Agregó documentos cédula solicitante y garante solidario: %s' % (persona), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

        elif action == 'subircontratobeca':
            try:
                solicitud = BecaSolicitud.objects.get(pk=int(request.POST['id']))
                beca = BecaAsignacion.objects.get(solicitud=solicitud)
                if beca.estadorevisioncontrato == 2:
                    return JsonResponse({"result": "bad", "mensaje": u"El documento no se puede subir debido a que ya fue verificado por Bienestar."})

                f = BecaSubirContratoForm(request.POST, request.FILES)

                if 'contrato' in request.FILES:
                    arch = request.FILES['contrato']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if not exte.lower() == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                if f.is_valid():
                    newfile = request.FILES['contrato']
                    newfile._name = generar_nombre("contratobeca", newfile._name)

                    beca.archivocontrato = newfile
                    beca.estadorevisioncontrato = 1
                    beca.personarevisacontrato = None
                    beca.observacion = ""
                    beca.save(request)

                    recorrido = BecaSolicitudRecorrido(solicitud=solicitud,
                                                       observacion="CONTRATO DE BECA CARGADO",
                                                       estado=17,
                                                       fecha=datetime.now().date())
                    recorrido.save(request)

                    log(u'Agregó contrato de beca: %s' % (persona), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

        elif action == 'representantesolidario':
            try:
                persona = request.session['persona']
                solicitud = BecaSolicitud.objects.get(pk=request.POST['id'])
                f = RepresentanteSolidarioForm(request.POST, request.FILES)
                if not f.is_valid():
                    raise NameError('Error')

                if not f.cleaned_data['cedula'].isdigit():
                    return JsonResponse({"result": "bad", "mensaje": "El número de cédula debe ser numérico"})

                resp = validarcedula(f.cleaned_data['cedula'])
                if resp != 'Ok':
                    return JsonResponse({"result": "bad", "mensaje": resp})

                if f.cleaned_data['cedula'] == persona.cedula:
                    return JsonResponse({"result": "bad", "mensaje": "El número de cédula del representante solidario debe ser distinto al del estudiante"})

                if 'archivocedula' in request.FILES:
                    arch = request.FILES['archivocedula']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if not exte.lower() in ['pdf']:
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                if 'archivovotacion' in request.FILES:
                    arch = request.FILES['archivovotacion']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if not exte.lower() in ['pdf']:
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                newfile1 = request.FILES['archivocedula']
                newfile1._name = generar_nombre("cedularepsol", newfile1._name)

                newfile2 = request.FILES['archivovotacion']
                newfile2._name = generar_nombre("certvotacionrepsol", newfile2._name)

                representante = persona.personaextension_set.all()[0]
                representante.cedularepsolidario = f.cleaned_data['cedula']
                representante.nombresrepsolidario = f.cleaned_data['nombre']
                representante.apellido1repsolidario = f.cleaned_data['apellido1']
                representante.apellido2repsolidario = f.cleaned_data['apellido2']
                representante.save(request)

                documentos = persona.documentos_personales()

                documentos.cedularepresentantesol = newfile1
                documentos.estadocedularepresentantesol = 1
                documentos.papeletarepresentantesol = newfile2
                documentos.estadopapeletarepresentantesol = 1

                documentos.save(request)

                recorrido = BecaSolicitudRecorrido(solicitud=solicitud,
                                                   observacion="DATOS DEL REPRESENTANTE SOLIDARIO CARGADO",
                                                   estado=9,
                                                   fecha=datetime.now().date())
                recorrido.save(request)

                log(u'Actualizó datos de representante solidario: %s' % persona, request, "edit")
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'actualizarcuentabancaria':
            try:
                persona = request.session['persona']
                solicitud = BecaSolicitud.objects.get(pk=int(request.POST['id']))
                f = CuentaBancariaBecadoForm(request.POST, request.FILES)

                if 'archivo' in request.FILES:
                    arch = request.FILES['archivo']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if not exte.lower() == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                if f.is_valid():
                    if len(f.cleaned_data['numero'].strip()) < 5:
                        return JsonResponse({"result": "bad", "mensaje": u"El número de cuenta bancaria debe tener mínimo 5 dígitos."})

                    cuentasexiste = persona.cuentabancariapersona_set.filter(status=True, numero=request.POST.get('numero', '').strip())
                    if cuentasexiste.values_list('id', flat=True).exists():
                        cuentabanca = cuentasexiste.first()
                        cuentabanca.activapago = True
                        cuentabanca.save(request)

                    cuentabancaria = persona.cuentabancaria()
                    if cuentabancaria.estadorevision != 2:
                        cuentabancaria.numero = f.cleaned_data['numero'].strip()
                        cuentabancaria.banco = f.cleaned_data['banco']
                        cuentabancaria.tipocuentabanco = f.cleaned_data['tipocuentabanco']
                        cuentabancaria.personarevisa = None
                        cuentabancaria.estadorevision = 1
                        cuentabancaria.observacion = ""

                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("cuentabancaria_", newfile._name)
                            cuentabancaria.archivo = newfile

                        cuentabancaria.save(request)

                    recorrido = BecaSolicitudRecorrido(solicitud=solicitud,
                                                       observacion="CERTIFICADO BANCARIO CARGADO",
                                                       estado=13,
                                                       fecha=datetime.now().date())
                    recorrido.save(request)
                    cuentabancariahistorialbeca = BecaSolicitudHistorialDocumentoPersonal(
                        becasolicitud=solicitud,
                        observacion=u'ACTUALIZÓ CUENTA BANCARIA',
                        archivo=cuentabancaria.archivo.url,
                        banco=cuentabancaria.banco,
                        tipocuentabanco=cuentabancaria.tipocuentabanco,
                        numero_cuentabancaria=cuentabancaria.numero,
                        tipo=3
                    )
                    cuentabancariahistorialbeca.save(request)
                    log(u'Actualizó datos de la cuenta bancaria: %s' % persona, request, "edit")
                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addcuentabancaria':
            try:
                persona = request.session['persona']
                solicitud = BecaSolicitud.objects.get(pk=int(request.POST['id']))
                f = CuentaBancariaBecadoForm(request.POST, request.FILES)

                if 'archivo' in request.FILES:
                    arch = request.FILES['archivo']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if not exte.lower() == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                if f.is_valid():
                    if len(f.cleaned_data['numero'].strip()) < 5:
                        return JsonResponse({"result": "bad", "mensaje": u"El número de cuenta bancaria debe tener mínimo 5 dígitos."})

                    cuentasexiste = persona.cuentabancariapersona_set.filter(status=True, numero=request.POST.get('numero', '').strip())
                    if cuentasexiste.values_list('id', flat=True).exists():
                        cuentabanca = cuentasexiste.first()
                        cuentabanca.activapago = True
                        cuentabanca.save(request)

                    newfile = request.FILES['archivo']
                    newfile._name = generar_nombre("cuentabancaria_", newfile._name)

                    cuentavigente = persona.cuentabancaria()
                    if cuentavigente:
                        cuentavigente.activapago = False
                        cuentavigente.save(request)
                    if cuentavigente is None:
                        cuentabancaria = CuentaBancariaPersona(persona=persona)
                    else:
                        cuentabancaria = cuentavigente
                    if cuentabancaria.estadorevision != 2:
                        cuentabancaria.persona.banco = f.cleaned_data['banco']
                        cuentabancaria.persona.numero = f.cleaned_data['numero'].strip()
                        cuentabancaria.tipocuentabanco = f.cleaned_data['tipocuentabanco']
                        cuentabancaria.estadorevision = 1
                        cuentabancaria.archivo = newfile
                        cuentabancaria.activapago = True
                        cuentabancaria.save(request)
                    recorrido = BecaSolicitudRecorrido(solicitud=solicitud,
                                                       observacion="CERTIFICADO BANCARIO CARGADO",
                                                       estado=13,
                                                       fecha=datetime.now().date())
                    recorrido.save(request)

                    log(u'Actualizó datos de la cuenta bancaria: %s' % persona, request, "edit")
                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editcomprobanteventa':
            try:
                persona = request.session['persona']
                comprobante = BecaComprobanteVenta.objects.get(pk=int(request.POST['idcomprobante']))

                revisioncomprobante = BecaComprobanteRevision.objects.get(pk=comprobante.revision.id)

                f = BecaComprobanteVentaEditForm(request.POST, request.FILES)
                solicitud = revisioncomprobante.asignacion.solicitud

                if 'archivo2' in request.FILES:
                    arch = request.FILES['archivo2']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if not exte.lower() == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                if f.is_valid():
                    if len(f.cleaned_data['rucproveedor2'].strip()) != 13:
                        return JsonResponse({"result": "bad", "mensaje": u"El número de Ruc del proveedor debe tener 13 dígitos."})

                    # resp = validarcedula(f.cleaned_data['rucproveedor'].strip()[:10])
                    # if resp != 'Ok':
                    #     return JsonResponse({"result": "bad", "mensaje": "El número de Ruc no es válido"})
                    # else:
                    #     if f.cleaned_data['rucproveedor'].strip()[-3:] != '001':
                    #         return JsonResponse({"result": "bad", "mensaje": "El número de Ruc no es válido"})

                    if f.cleaned_data['rucproveedor2'].strip()[-3:] != '001':
                        return JsonResponse({"result": "bad", "mensaje": "El número de Ruc no es válido"})

                    if f.cleaned_data['total2']:
                        if f.cleaned_data['total2'] < 1:
                            return JsonResponse({"result": "bad", "mensaje": "El total del comprobante debe ser mayor a 0"})

                    comprobante.rucproveedor = f.cleaned_data['rucproveedor2'].strip()
                    if f.cleaned_data['total2']:
                        comprobante.total = f.cleaned_data['total2']

                    guardarecorrido = False

                    comprobantes = revisioncomprobante.becacomprobanteventa_set.filter(status=True)

                    if comprobante.estadorevisionfin == 3:
                        comprobante.observacionfin = ''
                        comprobante.estadorevisionfin = 1
                        comprobante.estado = 1
                        comprobante.save(request)

                        totalrechazado = comprobantes.filter(estadorevisionfin=3).count()
                        totalrechazadoio = comprobantes.filter(estadorevisionfin=6).count()
                        if totalrechazado == 0 and totalrechazadoio == 0:
                            revisioncomprobante.observacionfin = ''
                            revisioncomprobante.estadorevisionfin = 1
                            revisioncomprobante.personarevisafin = None
                            revisioncomprobante.estado = 1

                        guardarecorrido = True
                    elif comprobante.estadorevisiondbu == 3:
                        comprobante.observaciondbu = ''
                        comprobante.estadorevisiondbu = 1
                        comprobante.estado = 1
                        comprobante.save(request)

                        totalrechazado = comprobantes.filter(estadorevisiondbu=3).count()
                        totalrechazadoio = comprobantes.filter(estadorevisiondbu=6).count()
                        if totalrechazado == 0 and totalrechazadoio == 0:
                            revisioncomprobante.observaciondbu = ''
                            revisioncomprobante.estadorevisiondbu = 1
                            revisioncomprobante.personarevisadbu = None
                            revisioncomprobante.estado = 1

                        guardarecorrido = True

                    revisioncomprobante.save(request)

                    if 'archivo2' in request.FILES:
                        newfile = request.FILES['archivo2']
                        newfile._name = generar_nombre("compvta_", newfile._name)
                        comprobante.archivo = newfile

                    comprobante.save(request)

                    if guardarecorrido:
                        recorrido = BecaSolicitudRecorrido(solicitud=solicitud,
                                                           observacion="COMPROBANTE DE VENTA CARGADO",
                                                           estado=21,
                                                           fecha=datetime.now().date())
                        recorrido.save(request)

                    log(u'Actualizó comprobante de venta: %s' % persona, request, "edit")
                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')

            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos.<br> %s" % msg})

        elif action == 'agregarcomprobanteventa':
            try:
                persona = request.session['persona']
                solicitud = BecaSolicitud.objects.get(pk=int(request.POST['idbeca']))
                beca = BecaAsignacion.objects.get(solicitud=solicitud)
                f = BecaComprobanteVentaForm(request.POST, request.FILES)

                if 'archivo' in request.FILES:
                    arch = request.FILES['archivo']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if not exte.lower() == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                if f.is_valid():
                    if len(f.cleaned_data['rucproveedor'].strip()) != 13:
                        return JsonResponse({"result": "bad", "mensaje": u"El número de Ruc del proveedor debe tener 13 dígitos."})

                    # resp = validarcedula(f.cleaned_data['rucproveedor'].strip()[:10])
                    # if resp != 'Ok':
                    #     return JsonResponse({"result": "bad", "mensaje": "El número de Ruc no es válido"})
                    # else:
                    #     if f.cleaned_data['rucproveedor'].strip()[-3:] != '001':
                    #         return JsonResponse({"result": "bad", "mensaje": "El número de Ruc no es válido"})

                    if f.cleaned_data['rucproveedor'].strip()[-3:] != '001':
                        return JsonResponse({"result": "bad", "mensaje": "El número de Ruc no es válido"})

                    if f.cleaned_data['total'] < 1:
                        return JsonResponse({"result": "bad", "mensaje": "El total del comprobante debe ser mayor a 0"})

                    if not BecaComprobanteRevision.objects.filter(asignacion=beca, status=True).exists():
                        revisioncomprobante = BecaComprobanteRevision(asignacion=beca,
                                                                      estado=1,
                                                                      estadorevisiondbu=1,
                                                                      estadorevisionfin=1
                                                                      )
                        revisioncomprobante.save(request)
                        existerevision = False
                    else:
                        revisioncomprobante = BecaComprobanteRevision.objects.get(asignacion=beca)
                        existerevision = True


                    if BecaComprobanteVenta.objects.filter(status=True, revision=revisioncomprobante, rucproveedor=f.cleaned_data['rucproveedor'].strip(), total=f.cleaned_data['total']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El comprobante de venta ya existe."})

                    comprobante = BecaComprobanteVenta(revision=revisioncomprobante,
                                                       rucproveedor=f.cleaned_data['rucproveedor'].strip(),
                                                       total=f.cleaned_data['total'],
                                                       estado=1,
                                                       estadorevisiondbu=1,
                                                       estadorevisionfin=1)
                    comprobante.save(request)

                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("compvta_", newfile._name)
                        comprobante.archivo = newfile

                    comprobante.save(request)

                    if existerevision is False:
                        recorrido = BecaSolicitudRecorrido(solicitud=solicitud,
                                                           observacion="COMPROBANTE DE VENTA CARGADO",
                                                           estado=21,
                                                           fecha=datetime.now().date())
                        recorrido.save(request)

                    comprechazados = revisioncomprobante.becacomprobanteventa_set.filter(status=True, estadorevisiondbu=3)
                    if comprechazados:
                        comprechazados.update(observaciondbu='', estadorevisiondbu=1, estado=1)

                        revisioncomprobante.observaciondbu = ''
                        revisioncomprobante.estadorevisiondbu = 1
                        revisioncomprobante.personarevisadbu = None
                        revisioncomprobante.estado = 1
                        revisioncomprobante.save(request)

                        recorrido = BecaSolicitudRecorrido(solicitud=solicitud,
                                                           observacion="COMPROBANTE DE VENTA CARGADO",
                                                           estado=21,
                                                           fecha=datetime.now().date())
                        recorrido.save(request)

                    # Desbloquear el acceso al Moodle Pregrado
                    cnmoodle = connections['moodle_db'].cursor()
                    idum = persona.idusermoodle
                    # Consulta en mooc_user
                    sql = """Select id From mooc_user Where id=%s and deleted = 1 """ % (idum)
                    cnmoodle.execute(sql)
                    row = cnmoodle.fetchone()
                    if row is not None:
                        # Asignar estado deleted = 0 para que pueda acceder
                        sql = """Update mooc_user Set deleted=0 Where id=%s""" % (idum)
                        cnmoodle.execute(sql)

                    cnmoodle.close()
                    # Desbloquear el acceso al Moodle Pregrado


                    log(u'Agregó comprobante de venta: %s' % persona, request, "edit")
                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos.<br> %s" % msg})

        elif action == 'aceptar_rechazar_beca':
            try:
                persona = request.session['persona']
                idsolicitud = int(request.POST['id'])
                tipo = request.POST['tipo']

                solicitud = BecaSolicitud.objects.get(pk=idsolicitud)

                if tipo == 'A':
                    if BecaAsignacion.objects.filter(solicitud=solicitud, status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El Registro de beca ya fue guardado."})

                if solicitud.becatipo_id == 23:
                    beneficios = solicitud.becasolicitudnecesidad_set.all()[0]
                    beneficio = beneficios.necesidad

                if 'archivo' in request.FILES:
                    arch = request.FILES['archivo']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if not exte.lower() in ['pdf']:
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                if tipo == 'A':
                    if not BecaTipoConfiguracion.objects.filter(becaperiodo__periodo=solicitud.periodo, becatipo=solicitud.becatipo).exists():
                        raise NameError(u"No se encontro configuración para el tipo de beca")
                    becatipoconfig = BecaTipoConfiguracion.objects.get(becaperiodo__periodo=solicitud.periodo, becatipo=solicitud.becatipo)

                    solicitud.becaaceptada = 2
                    solicitud.becaasignada = 2
                    solicitud.save(request)

                    # AYUDAS ECONOMICAS COVID
                    if solicitud.becatipo.id == 23:
                        modalidad = solicitud.inscripcion.carrera.modalidad
                        montobeca = 270.36 if modalidad != 3 else 44.80

                        beca = BecaAsignacion(solicitud=solicitud,
                                              montomensual=montobeca,
                                              cantidadmeses=1,
                                              montobeneficio=montobeca,
                                              fecha=datetime.now().date(),
                                              activo=True,
                                              grupopago=None,
                                              tipo=1,
                                              notificar=True,
                                              estadobeca=None,
                                              infoactualizada=False,
                                              cargadocumento=True)
                        beca.save(request)

                        detalleuso = BecaDetalleUtilizacion(asignacion=beca,
                                                            utilizacion_id=8 if beneficio == 1 else 9,
                                                            personaaprueba=persona,
                                                            archivo=None,
                                                            fechaaprueba=datetime.now(),
                                                            fechaarchivo=None,
                                                            estado=2,
                                                            observacion='GENERADO AUTOMÁTICAMENTE')
                        detalleuso.save(request)

                        # VERIFICAR SI TIENE DOCUMENTACION APROBADA DE UN PROCESO ANTERIOR
                        persona = solicitud.inscripcion.persona
                        if persona.documentos_personales():
                            # SI TIENEN DOCUMENTACION VALIDADA
                            if persona.cedula_solicitante_representante_validadas():
                                beca.infoactualizada = True
                                beca.cargadocumento = False
                                beca.save(request)
                    else:
                        # OTROS TIPOS DE BECA
                        # if solicitud.becatipo_id == 16 or solicitud.becatipo_id == 17:
                        #     montobeca = 110.04
                        # else:
                        #     montobeca = 184.08

                        montobeca = becatipoconfig.becamonto
                        meses = becatipoconfig.becameses
                        montomensual = becatipoconfig.monto_x_mes()

                        beca = BecaAsignacion(solicitud=solicitud,
                                              montomensual=montomensual,
                                              cantidadmeses=meses,
                                              montobeneficio=montobeca,
                                              fecha=datetime.now().date(),
                                              activo=True,
                                              grupopago=None,
                                              tipo=solicitud.tiposolicitud,
                                              notificar=True,
                                              estadobeca=None,
                                              infoactualizada=False,
                                              cargadocumento=True)
                        beca.save(request)

                        # VERIFICAR SI TIENE DOCUMENTACION APROBADA DE UN PROCESO ANTERIOR
                        persona = solicitud.inscripcion.persona
                        if persona.documentos_personales():
                            # SI TIENEN DOCUMENTACION VALIDADA
                            if persona.cedula_solicitante_representante_validadas():
                                beca.infoactualizada = True
                                beca.cargadocumento = False
                                beca.save(request)

                    log(u'Aceptó la beca estudiantil: %s' % persona, request, "edit")
                else:
                    f = BecaAceptarRechazarForm(request.POST, request.FILES)
                    if not f.is_valid():
                        raise NameError('Complete todos los campos requerido!')
                    solicitud.becaaceptada = 3
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("rechazobeca", newfile._name)
                        solicitud.archivorechazo = newfile
                    solicitud.observacion = f.cleaned_data['observacion'].strip().upper()
                    solicitud.save(request)
                    log(u'Rechazó la beca estudiantil: %s' % persona, request, "edit")

                recorrido = BecaSolicitudRecorrido(solicitud=solicitud,
                                                   estado=6 if tipo == 'A' else 7,
                                                   observacion='BECA ACEPTADA POR ESTUDIANTE' if tipo == 'A' else 'BECA RECHAZADA POR ESTUDIANTE',
                                                   fecha=datetime.now().date())
                recorrido.save(request)

                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos.<br> %s" % msg})

        elif action == 'anular_solicitud':
            try:
                persona = request.session['persona']
                idsolicitud = int(request.POST['id'])
                solicitud = BecaSolicitud.objects.get(pk=idsolicitud)

                if solicitud.estado == 8:
                    return JsonResponse({"result": "bad", "mensaje": u"La solicitud ya ha sido desistida por otro usuario."})

                f = BecaSolicitudAnularForm(request.POST)
                if f.is_valid():
                    solicitud.estado = 8
                    solicitud.observacion = f.cleaned_data['observacion'].strip().upper()
                    solicitud.save(request)

                    recorrido = BecaSolicitudRecorrido(
                        solicitud=solicitud,
                        observacion=f.cleaned_data['observacion'].strip().upper(),
                        estado=8,
                        fecha=datetime.now().date()
                    )
                    recorrido.save(request)

                    log(u'Desistió de la solicitud de beca: %s  - %s' % (persona, solicitud), request, "edit")

                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'actualizardatos':
            try:
                validapais = True
                solicitud = None
                if BecaSolicitud.objects.filter(inscripcion=inscripcion, periodo=periodo).exists():
                    solicitud = BecaSolicitud.objects.get(inscripcion=inscripcion, periodo=periodo)
                if solicitud and solicitud.becatipo.id == 22 and persona.ecuatoriano_vive_exterior():
                    validapais = False
                # if validapais and int(request.POST['pais']) != 1:
                #     return JsonResponse({"result": "bad", "mensaje": u"Seleccione ECUADOR como país de residencia."})

                if 'cedulaestudiante' in request.FILES:
                    arch = request.FILES['cedulaestudiante']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if not exte.lower() in ['pdf']:
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                if 'certificadoestudiante' in request.FILES:
                    arch = request.FILES['certificadoestudiante']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if not exte.lower() in ['pdf']:
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                if 'actagradoestudiante' in request.FILES:
                    arch = request.FILES['actagradoestudiante']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if not exte.lower() in ['pdf']:
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                if 'certificadobancario' in request.FILES:
                    arch = request.FILES['certificadobancario']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if not exte.lower() in ['pdf']:
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})
                deportista = persona.deportistapersona_set.filter(status=True).first()
                # if 'cedularepresentante' in request.FILES:
                #     arch = request.FILES['cedularepresentante']
                #     extension = arch._name.split('.')
                #     tam = len(extension)
                #     exte = extension[tam - 1]
                #     if arch.size > 4194304:
                #         return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                #     if not exte.lower() in ['pdf']:
                #         return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})
                #
                # if 'certificadorepresentante' in request.FILES:
                #     arch = request.FILES['certificadorepresentante']
                #     extension = arch._name.split('.')
                #     tam = len(extension)
                #     exte = extension[tam - 1]
                #     if arch.size > 4194304:
                #         return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                #     if not exte.lower() in ['pdf']:
                #         return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                if 'serviciobasico' in request.FILES:
                    arch = request.FILES['serviciobasico']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if not exte.lower() in ['pdf']:
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                if 'raza' in request.FILES:
                    arch = request.FILES['raza']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if not exte.lower() in ['pdf']:
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                if 'archivodiscapacidad' in request.FILES:
                    arch = request.FILES['archivodiscapacidad']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if not exte.lower() in ['pdf']:
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                if 'archivodeporteevento' in request.FILES:
                    arch = request.FILES['archivodeporteevento']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if not exte.lower() in ['pdf']:
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                if 'archivodeporteentrena' in request.FILES:
                    arch = request.FILES['archivodeporteentrena']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if not exte.lower() in ['pdf']:
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                # resp = validarcedula(request.POST['numerocedularepresentante'].strip())
                # if resp != 'Ok':
                #     return JsonResponse({"result": "bad", "mensaje": resp})

                persona = request.session['persona']

                # if request.POST['numerocedularepresentante'].strip() == persona.cedula:
                #     return JsonResponse({"result": "bad", "mensaje": u"El número de cédula del representante solidario debe ser diferente al del alumno"})
                personadocumentopersonal = persona.personadocumentopersonal_set.filter(status=True).first()
                newfile = None
                if 'cedulaestudiante' in request.FILES:
                    newfile = request.FILES['cedulaestudiante']
                    newfile._name = generar_nombre("cedula", newfile._name)

                newfile2 = None
                if 'certificadoestudiante' in request.FILES:
                    newfile2 = request.FILES['certificadoestudiante']
                    newfile2._name = generar_nombre("certvotacion", newfile2._name)

                # newfile3 = request.FILES['cedularepresentante']
                # newfile3._name = generar_nombre("cedularepsol", newfile3._name)
                #
                # newfile4 = request.FILES['certificadorepresentante']
                # newfile4._name = generar_nombre("certvotacionrepsol", newfile4._name)
                newfile5 = None
                if 'certificadobancario' in request.FILES:
                    newfile5 = request.FILES['certificadobancario']
                    newfile5._name = generar_nombre("cuentabancaria_", newfile5._name)

                newfile6 = None
                estadoactagrado = None
                if 'actagradoestudiante' in request.FILES:
                    newfile6 = request.FILES['actagradoestudiante']
                    newfile6._name = generar_nombre("actagrado_", newfile6._name)
                    estadoactagrado = 1

                newfile7 = None
                if 'serviciobasico' in request.FILES:
                    newfile7 = request.FILES['serviciobasico']
                    newfile7._name = generar_nombre("serviciobasico_", newfile7._name)

                newfile8 = None
                if 'raza' in request.FILES:
                    newfile8 = request.FILES['raza']
                    newfile8._name = generar_nombre("raza", newfile8._name)


                newfile9 = None
                if 'archivodiscapacidad' in request.FILES:
                    newfile9 = request.FILES['archivodiscapacidad']
                    newfile9._name = generar_nombre("archivodiscapacidad", newfile9._name)

                newfile10 = None
                if 'archivodeporteevento' in request.FILES:
                    newfile10 = request.FILES['archivodeporteevento']
                    newfile10._name = generar_nombre("archivodeporteevento_", newfile10._name)

                newfile11 = None
                if 'archivodeporteentrena' in request.FILES:
                    newfile11 = request.FILES['archivodeporteentrena']
                    newfile11._name = generar_nombre("archivodeporteentrena_", newfile10._name)

                persona.pais_id = int(request.POST['pais'])
                persona.provincia_id = int(request.POST['provincia'])
                if validapais and int(request.POST['pais']) == 1:
                    if not 'canton' in request.POST:
                        raise NameError('Debe ingresar el cantón')
                    persona.canton_id = int(request.POST['canton'])
                    if not 'parroquia' in request.POST:
                        raise NameError('Debe ingresar la parroquia')
                    persona.parroquia_id = int(request.POST['parroquia'])
                persona.sector = request.POST['sector'].strip().upper()
                persona.num_direccion = request.POST['numerocasa'].strip().upper()
                persona.direccion = request.POST['direccion1'].strip().upper()
                persona.direccion2 = request.POST['direccion2'].strip().upper()
                persona.referencia = request.POST['referencia'].strip().upper()
                persona.telefono_conv = request.POST['telefono'].strip().upper()
                persona.telefono = request.POST['celular'].strip().upper()
                persona.tipocelular = int(request.POST['operadora'])
                persona.save(request)

                # representante = persona.personaextension_set.all()[0]
                # representante.cedularepsolidario = request.POST['numerocedularepresentante'].strip().upper()
                # representante.nombresrepsolidario = request.POST['nombrerepresentante'].strip().upper()
                # representante.apellido1repsolidario = request.POST['apellido1representante'].strip().upper()
                # representante.apellido2repsolidario = request.POST['apellido2representante'].strip().upper()
                # representante.save(request)

                documentos = persona.documentos_personales()
                observacion_historial = 'ACTUALIZÓ'
                if documentos is None:
                    documentos = PersonaDocumentoPersonal(persona=persona,
                                                          cedula=newfile,
                                                          estadocedula=1,
                                                          papeleta=newfile2,
                                                          estadopapeleta=1,
                                                          actagrado=newfile6,
                                                          estadoactagrado=estadoactagrado,
                                                          # cedularepresentantesol=newfile3,
                                                          # estadocedularepresentantesol=1,
                                                          # papeletarepresentantesol=newfile4,
                                                          # estadopapeletarepresentantesol=1,
                                                          observacion=""
                                                          )
                    if solicitud and solicitud.becatipo.id == 22 and persona.ecuatoriano_vive_exterior():
                        documentos.serviciosbasico = newfile7 if newfile7 is not None else documentos.serviciosbasico
                        documentos.estadoserviciosbasico = 1
                    observacion_historial = 'ADICIONÓ'
                else:
                    documentos.cedula = newfile if newfile is not None else documentos.cedula
                    documentos.estadocedula = 1 if newfile is not None else documentos.estadocedula
                    documentos.papeleta = newfile2 if newfile2 is not None else documentos.papeleta
                    documentos.estadopapeleta = 1  if newfile2 is not None else documentos.estadopapeleta
                    # documentos.cedularepresentantesol = newfile3
                    # documentos.estadocedularepresentantesol = 1
                    # documentos.papeletarepresentantesol = newfile4
                    # documentos.estadopapeletarepresentantesol = 1
                    documentos.actagrado = newfile6 if newfile6 is not None else documentos.actagrado
                    documentos.estadoactagrado = estadoactagrado if newfile6 is not None else documentos.estadoactagrado
                    documentos.observacion = ""
                    if solicitud and solicitud.becatipo.id == 22 and persona.ecuatoriano_vive_exterior():
                        documentos.serviciosbasico = newfile7 if newfile7 is not None else documentos.serviciosbasico
                        documentos.estadoserviciosbasico = 1 if newfile7 is not None else documentos.estadoserviciosbasico

                documentos.save(request)
                cedulahistorialbeca = BecaSolicitudHistorialDocumentoPersonal(
                    becasolicitud=solicitud,
                    observacion=u'%s %s' % (observacion_historial, 'CÉDULA DE CIUDADANÍA'),
                    archivo=documentos.cedula.url,
                    tipo=1
                )
                cedulahistorialbeca.save(request)
                # papelehistorialbeca = BecaSolicitudHistorialDocumentoPersonal(
                #     becasolicitud=solicitud,
                #     observacion=u'%s %s' % (observacion_historial, 'CERTIFICADO DE VOTACiÓN'),
                #     archivo=documentos.papeleta.url,
                #     tipo=2
                # )
                # papelehistorialbeca.save(request)
                cuentasexiste = persona.cuentabancariapersona_set.filter(status=True, numero=request.POST.get('cuentabancaria', '').strip())
                if cuentasexiste.values_list('id', flat=True).exists():
                    cuentabanca = cuentasexiste.first()
                    cuentabanca.activapago=True
                    cuentabanca.save()
                cuentabancaria = persona.cuentabancaria()
                observacion_historial = 'ACTUALIZÓ'
                if cuentabancaria is None:
                    cuentabancaria = CuentaBancariaPersona(persona=persona,
                                                           numero=request.POST['cuentabancaria'].strip(),
                                                           banco_id=int(request.POST['banco']),
                                                           tipocuentabanco_id=int(request.POST['tipocuenta']),
                                                           archivo=newfile5,
                                                           estadorevision=1,
                                                           activapago=True)
                    observacion_historial = 'ADICIONÓ'
                elif cuentabancaria.estadorevision !=2:
                    cuentabancaria.numero = request.POST['cuentabancaria'].strip()
                    cuentabancaria.banco_id = int(request.POST['banco'])
                    cuentabancaria.tipocuentabanco_id = int(request.POST['tipocuenta'])
                    cuentabancaria.archivo = newfile5 if newfile5 is not None else cuentabancaria.archivo
                    cuentabancaria.estadorevision = 1 if newfile5 is not None else cuentabancaria.estadorevision
                    cuentabancaria.activapago = True

                cuentabancaria.save(request)
                cuentabancariahistorialbeca = BecaSolicitudHistorialDocumentoPersonal(
                    becasolicitud=solicitud,
                    observacion=u'%s CUENTA BANCARIA' % (observacion_historial),
                    archivo=cuentabancaria.archivo.url,
                    banco=cuentabancaria.banco,
                    tipocuentabanco=cuentabancaria.tipocuentabanco,
                    numero_cuentabancaria=cuentabancaria.numero,
                    tipo=3
                )
                cuentabancariahistorialbeca.save(request)

                # mi_perfil = persona.mi_perfil()
                ds_raza = persona.perfilinscripcion_set.first()
                ds_raza.archivoraza = newfile8 if  newfile8 else ds_raza.archivoraza
                ds_raza.estadoarchivoraza = 1 if  newfile8 else  ds_raza.estadoarchivoraza
                ds_raza.verificaraza = False if  newfile8 else  ds_raza.verificaraza
                ds_raza.observacionarchraza = None if  newfile8 else  ds_raza.observacionarchraza
                ds_raza.save(request)

                if solicitud.becatipo_id == 21:
                    etniahistorialbeca = BecaSolicitudHistorialDocumentoPersonal(
                        becasolicitud=solicitud,
                        observacion=u'ACTUALIZÓ  CERTIFICADO DE PUEBLOS Y NACIONALIDADES DEL ECUADOR',
                        archivo=ds_raza.archivoraza.url,
                        tipo=6
                    )
                    etniahistorialbeca.save(request)

                if solicitud.becatipo_id == 19:
                    perfilinscripcion = persona.perfilinscripcion_set.first()
                    perfilinscripcion.archivo = newfile9 if  newfile9 else  perfilinscripcion.archivo
                    perfilinscripcion.save(request)
                    papelehistorialbeca = BecaSolicitudHistorialDocumentoPersonal(
                        becasolicitud=solicitud,
                        observacion=u'ACTUALIZÓ %s' % ('CERTIFICADO DE DISCAPACIDAD'),
                        archivo=perfilinscripcion.archivo.url,
                        tipo=4
                    )

                # if not BecaSolicitud.objects.filter(periodo=periodo, inscripcion=inscripcion).exists():
                #     beca = BecaAsignacion.objects.get(solicitud__periodo=90, solicitud__inscripcion__persona=inscripcion.persona)
                # else:
                #     beca = BecaAsignacion.objects.get(solicitud__inscripcion=inscripcion, solicitud__periodo=110)

                if not BecaSolicitud.objects.filter(periodo=periodo, inscripcion=inscripcion).exists():
                    raise NameError('No se encontro solicitud')
                if not BecaAsignacion.objects.filter(solicitud__inscripcion=inscripcion, solicitud__periodo=periodo).exists():
                    raise NameError('No se encontro beca asignada')
                beca = BecaAsignacion.objects.get(solicitud__inscripcion=inscripcion, solicitud__periodo=periodo)

                beca.infoactualizada = True
                beca.save(request)

                recorrido = BecaSolicitudRecorrido(solicitud=beca.solicitud,
                                                   observacion="DOCUMENTOS PERSONALES CARGADOS",
                                                   estado=9,
                                                   fecha=datetime.now().date()
                                                   )
                recorrido.save(request)

                recorrido = BecaSolicitudRecorrido(solicitud=beca.solicitud,
                                                   observacion="CERTIFICADO BANCARIO CARGADO",
                                                   estado=13,
                                                   fecha=datetime.now().date()
                                                   )
                recorrido.save(request)

                # SI TIENE BECA ACEPTADA DE AYUDA ECONOMICA
                if BecaAsignacion.objects.filter(solicitud__inscripcion=inscripcion, solicitud__periodo=periodo).exists():
                    beca = BecaAsignacion.objects.get(solicitud__inscripcion=inscripcion, solicitud__periodo=periodo)
                    if beca.infoactualizada is False:
                        beca.infoactualizada = True
                        beca.save(request)

                if solicitud.becatipo_id == 20:
                    if deportista:
                        deportista.archivoevento = newfile10 if newfile10 else deportista.archivoevento
                        deportista.estadoarchivoevento = 1 if newfile10 else deportista.estadoarchivoevento
                        deportista.archivoentrena = newfile11 if newfile11 else deportista.archivoentrena
                        deportista.estadoarchivoentrena = 1 if newfile11 else deportista.estadoarchivoentrena
                        deportista.save(request)
                        ruta = ''
                        if deportista.archivoevento and deportista.archivoentrena:
                            ruta = f'{deportista.archivoevento.url},{deportista.archivoentrena.url}'
                        elif deportista.archivoevento:
                            ruta = f'{deportista.archivoevento.url}'
                        elif deportista.archivoentrena:
                            ruta = f'{deportista.archivoentrena.url}'

                        cluddeportebeca = BecaSolicitudHistorialDocumentoPersonal(
                            becasolicitud=solicitud,
                            observacion=u'ACTUALIZÓ CERTIFICADOS DE CLUB DEPORTE',
                            archivo=ruta,
                            tipo=5
                        )
                        cluddeportebeca.save(request)

                if solicitud.becatipo_id == 22:
                    if persona.ecuatoriano_vive_exterior():
                        servicioshistorialbeca = BecaSolicitudHistorialDocumentoPersonal(
                            becasolicitud=beca.solicitud,
                            observacion=u'ACTUALIZÓ CERTIFICADO DE SERVICIOS  BASÍCOS',
                            archivo=documentos.serviciosbasico.url,
                            tipo=7
                        )
                        servicioshistorialbeca.save(request)

                if solicitud.cumple_todos_documentos_requeridos():
                    beca.infoactualizada = True
                    beca.cargadocumento = False
                    beca.save(request)
                fechaactual = datetime.now()
                solicitudesdoc = solicitud.inscripcion.becasolicitud_set.filter(periodo__becaperiodo__periodo_id=F('periodo_id'),
                                                      periodo__becaperiodo__vigente=True,
                                                      periodo__becaperiodo__fechainiciosolicitud__lte=fechaactual,
                                                      periodo__becaperiodo__fechafinsolicitud__gte=fechaactual,
                                                      becaaceptada=2,
                                                      status=True,
                                                      estado=2).order_by('periodo__inicio').distinct()
                primerasol = solicitudesdoc.first()
                if primerasol is not None:
                    if not primerasol.tiene_pendiente_documentos_por_cargar():
                        for eBecasol in solicitudesdoc:
                            eBecasol.delete_documentacion_cache()
                #tiene_pendiente_documentos_por_cargar
                log(u'Actualizó datos de localización, cuenta bancaria, etc.: %s' % persona, request, "edit")
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                textoerror = '{} Linea:{}'.format(str(ex), sys.exc_info()[-1].tb_lineno)
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. Detalle: %s" % (textoerror)})

        if action == 'generanumerocontrato':
            try:
                beca = BecaAsignacion.objects.get(solicitud_id=int(request.POST['id']))
                if not BecaPeriodo.objects.filter(periodo=periodo, vigente=True).exists():
                    raise NameError(u"No tiene configurado el contrato")
                becaperiodo = BecaPeriodo.objects.get(periodo=periodo, vigente=True)
                fechainicio = becaperiodo.fechainicioimprimircontrato
                fechafin = becaperiodo.fechafinimprimircontrato
                fechaactual = datetime.now()
                if not inscripcion.tienesolicitudbeca():
                    raise NameError(u"No tiene beca asignada")
                if fechaactual >= fechainicio and fechaactual <= fechafin:
                    if not beca.numerocontrato:
                        secuencia = secuencia_contrato_beca_aux(beca.solicitud.periodo)
                        # if beca.solicitud.becatipo.id == 23:
                        #     if BecaAsignacion.objects.filter(solicitud__becatipo_id=23, numerocontrato=secuencia, status=True).exists():
                        #         return JsonResponse({"result": "bad", "mensaje": u"Error al generar el contrato, intente nuevamente"})
                        # else:
                        #     if BecaAsignacion.objects.filter(~Q(solicitud__becatipo_id=23), numerocontrato=secuencia, status=True).exists():
                        #         return JsonResponse({"result": "bad", "mensaje": u"Error al generar el contrato, intente nuevamente"})

                        beca.fechacontrato = datetime.now().date()
                        beca.numerocontrato = secuencia
                        beca.save(request)
                        log(u'Editó registro de beca: %s' % beca, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al generar el contrato no se encuentra activo."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar la secuencia del contrato. %s" % ex.__str__()})

        elif action == 'contratobecapdf':
            try:
                data = {}

                beca = BecaAsignacion.objects.get(solicitud_id=int(request.POST['id']))

                # data['fechainiciocap'] = str(capacitacion.fechainicio.day) + " de " + \
                #                          MESES_CHOICES[capacitacion.fechainicio.month - 1][
                #                              1].capitalize() + " del " + str(capacitacion.fechainicio.year)
                # data['fechafincap'] = str(capacitacion.fechafin.day) + " de " + \
                #                       MESES_CHOICES[capacitacion.fechafin.month - 1][1].capitalize() + " del " + str(
                #     capacitacion.fechafin.year)

                if beca.solicitud.becatipo.id == 23:
                    data['numerocontrato'] = "CONTRATO Nº 1S-2021-" + str(beca.numerocontrato).zfill(4)
                else:
                    data['numerocontrato'] = "CONTRATO Nº " + str(beca.numerocontrato).zfill(4) + "-2021-1S"

                if beca.solicitud.becatipo.id == 16:
                    matricula = beca.solicitud.inscripcion.matricula_periodo_actual(beca.solicitud.periodo)[0]
                    carrera = matricula.inscripcion.carrera
                else:
                    carrera = beca.solicitud.inscripcion.carrera

                becaperiodo = BecaPeriodo.objects.get(periodo=beca.solicitud.periodo)
                becaconftipo = BecaTipoConfiguracion.objects.get(becaperiodo=becaperiodo, becatipo=beca.solicitud.becatipo)

                data['mimalla'] = mimalla = beca.solicitud.inscripcion.mi_malla()
                data['beca'] = beca
                data['inscripcion'] = beca.solicitud.inscripcion
                data['carrera'] = carrera
                data['becaconftipo'] = becaconftipo
                data['fechacontrato'] = fechaletra_corta(beca.fechacontrato)
                data['fechacontrato2'] = str(beca.fechacontrato.day) + " de " + MESES_CHOICES[beca.fechacontrato.month - 1][1].capitalize() + " del " + str(beca.fechacontrato.year)


                return conviert_html_to_pdf(
                    'adm_becas/contratoayudaeconomicapdf.html' if beca.solicitud.becatipo.id == 23 else 'adm_becas/contratobecapdfv2.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as ex:
                return HttpResponseRedirect("/alu_becas?info=%s" % "Error al generar el reporte del contrato de la beca")

        elif action == 'actualizardiscapacidad':
            try:
                if 'archivo' in request.FILES:
                    arch = request.FILES['archivo']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if not exte.lower() in ['pdf']:
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                persona = request.session['persona']
                f = DiscapacidadForm(request.POST, request.FILES)
                if f.is_valid():
                    perfil = persona.mi_perfil()
                    perfil.porcientodiscapacidad = f.cleaned_data['porcientodiscapacidad'] if f.cleaned_data['porcientodiscapacidad'] else 0
                    perfil.carnetdiscapacidad = f.cleaned_data['carnetdiscapacidad']
                    perfil.institucionvalida = f.cleaned_data['institucionvalida']
                    perfil.verificadiscapacidad = False

                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("archivosdiscapacidad_", newfile._name)
                        perfil.archivo = newfile
                        perfil.estadoarchivodiscapacidad = 1

                    perfil.save(request)
                    log(u'Modifico tipo de discapacidad: %s' % persona, request, "edit")
                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'subirarchivos':
            try:
                data['title'] = 'Subir Archivos Envidencia de Solicitud'
                id = int(request.POST['id'])
                idtipo = int(request.POST['idtipo'])
                if not BecaSolicitud.objects.filter(inscripcion_id=id, periodo=periodo).exists():
                    cabecera = BecaSolicitud(inscripcion_id=id,
                                             becatipo_id=idtipo,
                                             periodo=periodo, estado=4)
                    cabecera.save(request)
                    for x in BecaRequisitos.objects.filter(status=True):
                        if x.id == 1 or x.id == 3 or x.id == 5:
                            cumple = True
                        else:
                            cumple = False
                        becasolicituddetalle = BecaDetalleSolicitud(solicitud=cabecera,
                                                                    requisito=x,
                                                                    cumple=cumple,
                                                                    estado=4)
                        becasolicituddetalle.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'addevidencia':
            try:
                no=False
                f = BecaDetalleSolicitudArchivoForm(request.POST, request.FILES)
                # 2.5MB - 2621440
                # 5MB - 5242880
                # 10MB - 10485760
                # 20MB - 20971520
                # 50MB - 5242880
                # 100MB 104857600
                # 250MB - 214958080
                # 500MB - 429916160
                d = request.FILES['archivo']
                if d.size > 6291456:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                if f.is_valid():
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("evidenciabeca_", newfile._name)
                    if BecaDetalleSolicitud.objects.filter(id=request.POST['idevidencia'],solicitud_id=request.POST['idsolicitud']).exists():
                        detalle = BecaDetalleSolicitud.objects.get(id=request.POST['idevidencia'],solicitud_id=request.POST['idsolicitud'])
                        if detalle.estado == 4:
                            detalle.archivo = newfile
                            detalle.save(request)
                        elif detalle.estado == 1 or detalle.estado == 3:
                            becasolicituddetalle = BecaDetalleSolicitud(solicitud=detalle.solicitud,
                                                                        requisito=detalle.requisito,
                                                                        cumple=detalle.cumple,
                                                                        estado=1,
                                                                        archivo=newfile)
                            becasolicituddetalle.save(request)
                        log(u'Adiciono evidencia de beca: %s [%s]' % (detalle.solicitud , detalle.id), request, "add")
                    vacios=BecaDetalleSolicitud.objects.filter(solicitud_id=request.POST['idsolicitud'],estado=4).exclude(archivo="")
                    if vacios.count() > 5:
                        becasolicitud = BecaSolicitud.objects.get(pk=request.POST['idsolicitud'])
                        becasolicitud.estado = 1
                        becasolicitud.save(request)
                        for x in becasolicitud.becadetallesolicitud_set.all():
                            x.estado = 1
                            x.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos.%s " % ex})

        elif action == 'subirarchivoutilizacion':
            try:
                f = BecaDetalleUtilizacionForm(request.POST, request.FILES)
                # 2.5MB - 2621440
                # 5MB - 5242880
                # 10MB - 10485760
                # 20MB - 20971520
                # 50MB - 5242880
                # 100MB 104857600
                # 250MB - 214958080
                # 500MB - 429916160
                d = request.FILES['archivo']
                if d.size > 6291456:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                f.desbloquear()
                if f.is_valid():
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("evidenciausobeca_", newfile._name)
                        idasignacion=request.POST['idasignacion']
                        idutilizacion=request.POST['idutilizacion']
                        if not BecaDetalleUtilizacion.objects.filter(status=True,asignacion_id=idasignacion,utilizacion_id=idutilizacion,estado=2).exists():
                            detalle = BecaDetalleUtilizacion(asignacion_id=idasignacion,
                                                             utilizacion_id=idutilizacion,
                                                             archivo=newfile,
                                                             fechaarchivo=datetime.now(),
                                                             estado=1)
                            detalle.save(request)
                            log(u'Subio Archivo utilizacion beca: %s - %s' % (detalle.asignacion.solicitud.inscripcion.persona,detalle.utilizacion), request, "add")
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Ya subio Archivo "})
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos.%s " % ex})

        elif action == 'generar_acta_compromiso':
            try:
                aData = {}
                url_path = 'http://127.0.0.1:8000'
                if not DEBUG:
                    url_path = 'https://sga.unemi.edu.ec'
                id = int(request.POST['id'])
                acepto = request.POST.get('acepto')
                output_folder = ''
                aData['becasolicitud'] = becasolicitud = BecaSolicitud.objects.get(id=id)
                # if not becasolicitud.cumple_todos_documentos_requeridos():
                #     raise NameError(f'Estimad {"a" if persona.sexo_id == 1 else "o" if persona.sexo_id == 2 else "o/a" } estudiante revisar su documentación desde el botón revisión de documentos')
                aData['configuracionbecatipoperiodo'] = becatipoconfiguracion =  becasolicitud.obtener_configuracionbecatipoperiodo()
                aData['matricula'] = matricula =  becasolicitud.obtener_matricula()
                eInscripcion = becasolicitud.inscripcion
                ePeriodo = becasolicitud.periodo
                eUsuario = request.user
                username = elimina_tildes(eUsuario.username)
                filename = f'acta_compromiso_{eInscripcion.id}_{ePeriodo.id}_{becasolicitud.id}'
                folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'becas', 'temp', 'actas_compromisos', username, ''))
                folder2 = os.path.join(os.path.join(SITE_STORAGE, 'media', 'becas', 'temp', 'actas_compromisos', username, 'qrcode', ''))
                aData['url_qr'] = rutaimg = folder2 + filename + '.png'
                aData['rutapdf'] = rutapdf = folder2 + filename + '.pdf'
                if os.path.isfile(rutapdf):
                    os.remove(rutapdf)
                elif os.path.isfile(rutaimg):
                    os.remove(rutaimg)
                os.makedirs(folder, exist_ok=True)
                os.makedirs(folder2, exist_ok=True)
                aData['version'] = datetime.now().strftime('%Y%m%d_%H%M%S')
                aData['image_qrcode'] = f'{url_path}/media/becas/temp/actas_compromisos/{username}/qrcode/{filename}.png'
                aData['fechaactual'] = datetime.now()
                url_acta = f'{url_path}/media/becas/temp/actas_compromisos/{username}/{filename}.pdf'
                rutapdf = folder + filename + '.pdf'

                valida, pdf, result = conviert_html_to_pdfsaveqr_generico(request, 'alu_becas/actacompromiso.html', {
                                                'pagesize': 'A4',
                                                'data': aData,

                                            }, folder, filename+ '.pdf')
                if not valida:
                    raise NameError('Error al generar el pdf de acta de compromiso')
                return JsonResponse({"result": "ok", "mensaje": u"Error al obtener los datos.", "url_acta":url_acta})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'generar_acta_compromiso_firma':
            try:
                aData = {}
                url_path = 'http://127.0.0.1:8000'
                if not DEBUG:
                    url_path = 'https://sga.unemi.edu.ec'
                id = int(request.POST['id'])
                acepto = request.POST.get('acepto')

                output_folder = ''
                aData['becasolicitud'] = becasolicitud = BecaSolicitud.objects.get(id=id)
                data['documentopersonal'] = documentopersonal = persona.personadocumentopersonal_set.filter(status=True).first()
                data['cuentabancaria'] = cuentabancaria = cuentabancaria = persona.cuentabancaria_becas()
                data['perfil'] = perfil =persona.mi_perfil()
                data['deportista'] = deportista =persona.deportistapersona_set.filter(status=True).first()
                data['isPersonaExterior'] = isPersonaExterior = persona.ecuatoriano_vive_exterior()
                # if not becasolicitud.cumple_todos_documentos_requeridos():
                #     raise NameError(f'Estimad {"a" if persona.sexo_id == 1 else "o" if persona.sexo_id == 2 else "o/a" } estudiante revisar su documentación desde el botón revisión de documentos')
                aData['configuracionbecatipoperiodo'] = becatipoconfiguracion =  becasolicitud.obtener_configuracionbecatipoperiodo()
                aData['matricula'] = matricula =  becasolicitud.obtener_matricula()
                eInscripcion = becasolicitud.inscripcion
                ePeriodo = becasolicitud.periodo
                eUsuario = request.user
                username = elimina_tildes(eUsuario.username)
                filename = f'acta_compromiso_{eInscripcion.id}_{ePeriodo.id}_{becasolicitud.id}'
                filenametemp = os.path.join(os.path.join(SITE_STORAGE, 'media', 'becas', 'temp', 'actas_compromisos', username, filename + '.pdf'))
                filenameqrtemp = os.path.join(os.path.join(SITE_STORAGE, 'media', 'becas', 'temp', 'actas_compromisos', username, 'qrcode', filename + '.png'))
                url_actafirmada=None
                mensaje = u"Usted rechazo la  beca"
                if acepto == '1':
                    becaasignacion = BecaAsignacion.objects.filter(solicitud=becasolicitud, status=True).first()
                    if becaasignacion is not  None:
                        raise NameError(u"El Registro de beca ya fue guardado.")
                    if becasolicitud.becatipo_id == 23:
                        beneficios = becasolicitud.becasolicitudnecesidad_set.all().first()
                        beneficio = beneficios.necesidad
                    if becatipoconfiguracion is None:
                        raise NameError(u"No se encontro configuración para el tipo de beca")
                    folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'becas', 'actas_compromisos', username, ''))
                    folder2 = os.path.join(os.path.join(SITE_STORAGE, 'media', 'becas', 'actas_compromisos', username, 'qrcode', ''))
                    aData['aceptobeca'] = True
                    aData['url_qr'] = rutaimg = folder2 + filename + '.png'
                    aData['rutapdf'] = rutapdf = folder + filename + '.pdf'
                    aData['url_pdf'] = url_pdf = f'{url_path}/media/becas/actas_compromisos/{username}/{filename}.pdf'
                    if os.path.isfile(rutapdf):
                        os.remove(rutapdf)
                    elif os.path.isfile(rutaimg):
                        os.remove(rutaimg)
                    os.makedirs(folder, exist_ok=True)
                    os.makedirs(folder2, exist_ok=True)
                    firma = f'ACEPTADO POR: {eInscripcion.persona.__str__()}\nUSUARIO:{username}\nFECHA: {datetime.utcnow()}\nACEPTO EN: sga.unemi.edu.ec\nDOCUMENTO:{url_pdf}'
                    url = pyqrcode.create(firma)
                    imageqr = url.png(rutaimg, 16, '#000000')
                    aData['version'] = datetime.now().strftime('%Y%m%d_%H%M%S')
                    aData['image_qrcode'] = f'{url_path}/media/becas/actas_compromisos/{username}/qrcode/{filename}.png'
                    aData['fechaactual'] = datetime.now()
                    url_acta = f'becas/actas_compromisos/{username}/{filename}.pdf'
                    rutapdf = folder + filename + '.pdf'

                    valida, pdf, result = conviert_html_to_pdfsaveqr_generico(request, 'alu_becas/actacompromiso.html', {
                                                    'pagesize': 'A4',
                                                    'data': aData,

                                                }, folder, filename + '.pdf')
                    if not valida:
                        raise NameError('Error al generar el pdf de acta de compromiso')
                    becasolicitud.archivoactacompromiso = url_acta
                    becasolicitud.becaaceptada = 2
                    becasolicitud.becaasignada = 2
                    becasolicitud.save(request)
                    # AYUDAS ECONOMICAS COVID
                    if becasolicitud.becatipo.id == 23:
                        modalidad = becasolicitud.inscripcion.carrera.modalidad
                        montobeca = 270.36 if modalidad != 3 else 44.80
                        beca = BecaAsignacion(solicitud=becasolicitud,
                                              montomensual=montobeca,
                                              cantidadmeses=1,
                                              montobeneficio=montobeca,
                                              fecha=datetime.now().date(),
                                              activo=True,
                                              grupopago=None,
                                              tipo=1,
                                              notificar=True,
                                              estadobeca=None,
                                              infoactualizada=False,
                                              cargadocumento=True)
                        beca.save(request)
                        detalleuso = BecaDetalleUtilizacion(asignacion=beca,
                                                            utilizacion_id=8 if beneficio == 1 else 9,
                                                            personaaprueba=persona,
                                                            archivo=None,
                                                            fechaaprueba=datetime.now(),
                                                            fechaarchivo=None,
                                                            estado=2,
                                                            observacion='GENERADO AUTOMÁTICAMENTE')
                        detalleuso.save(request)
                        persona = becasolicitud.inscripcion.persona
                        if persona.documentos_personales():
                            # SI TIENEN DOCUMENTACION VALIDADA
                            if persona.cedula_solicitante_representante_validadas():
                                beca.infoactualizada = True
                                beca.cargadocumento = False
                                beca.save(request)
                    else:
                        # OTROS TIPOS DE BECA
                        # if solicitud.becatipo_id == 16 or solicitud.becatipo_id == 17:
                        #     montobeca = 110.04
                        # else:
                        #     montobeca = 184.08
                        montobeca = becatipoconfiguracion.becamonto
                        meses = becatipoconfiguracion.becameses
                        montomensual = becatipoconfiguracion.monto_x_mes()
                        beca = BecaAsignacion(solicitud=becasolicitud,
                                              montomensual=montomensual,
                                              cantidadmeses=meses,
                                              montobeneficio=montobeca,
                                              fecha=datetime.now().date(),
                                              activo=True,
                                              grupopago=None,
                                              tipo=becasolicitud.tiposolicitud,
                                              notificar=True,
                                              estadobeca=None,
                                              infoactualizada=False,
                                              cargadocumento=True)
                        beca.save(request)
                        # VERIFICAR SI TIENE DOCUMENTACION APROBADA DE UN PROCESO ANTERIOR
                        # persona = becasolicitud.inscripcion.persona
                        # if persona.documentos_personales():
                        #     # SI TIENEN DOCUMENTACION VALIDADA
                        #     if persona.cedula_solicitante_representante_validadas():
                        #         beca.infoactualizada = True
                        #         beca.cargadocumento = False
                        #         beca.save(request)

                        if becasolicitud.cumple_todos_documentos_requeridos():
                            beca.infoactualizada = True
                            beca.cargadocumento = False
                            beca.save(request)
                    url_actafirmada = becasolicitud.archivoactacompromiso.url
                    log(u'Aceptó la beca estudiantil: %s' % (persona), request, "edit")
                    mensaje = u"Acepto correctamente la beca"
                if acepto == '0':
                    becasolicitud.becaaceptada = 3
                    becasolicitud.observacion = 'El estudiante rechazó la beca estudiantil'
                    becasolicitud.save(request)
                    log(u'Rechazó la beca estudiantil: %s' % persona, request, "edit")
                if os.path.isfile(filenameqrtemp):
                    os.remove(filenameqrtemp)
                elif os.path.isfile(filenametemp):
                    os.remove(filenametemp)
                return JsonResponse({"result": "ok", "mensaje":mensaje, "url_acta":url_actafirmada})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"%s"%ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'actualizardatos':
                try:
                    data['title'] = "Actualización de Datos de Domicilio del Estudiante"
                    data['inscripcion'] = Inscripcion.objects.get(pk=inscripcion.id)
                    data['bancos'] = Banco.objects.filter(status=True).order_by('nombre')
                    data['perfil'] = persona.mi_perfil()
                    data['documentopersonal'] = persona.personadocumentopersonal_set.filter(status=True).first()
                    data['cuentabancaria'] = cuentabancaria = persona.cuentabancaria()
                    data['tiposcuentas'] = tiposcuentas = TipoCuentaBanco.objects.filter(status=True)
                    data['deportista'] = deportista = persona.deportistapersona_set.filter(status=True).first()
                    if not BecaSolicitud.objects.filter(periodo=periodo, inscripcion=inscripcion).exists() and not DEBUG:
                        return HttpResponseRedirect("/alu_becas?info=No tiene solicitudes registradas en el período académico %s"%(periodo))
                    solicitud = BecaSolicitud.objects.get(periodo=periodo, inscripcion=inscripcion)
                    data['tipobeca'] = solicitud.becatipo.id
                    if not BecaPeriodo.objects.filter(periodo=periodo, vigente=True).exists() and not DEBUG:
                        return HttpResponseRedirect("/alu_becas?info=%s" % f"Estimad{ 'o' if solicitud.inscripcion.persona.sexo_id == 2 else 'a'} estudiante estamos en proceso de configuración de las becas")
                    becaperiodo = BecaPeriodo.objects.filter(periodo=periodo, vigente=True).first()
                    fechainicioimprimircontrato = becaperiodo.fechainicioimprimircontrato
                    # msg = f"Estimad{ 'o' if solicitud.inscripcion.persona.sexo_id == 2 else 'a'} estudiante, se le comunica que usted cuenta con información VALIDADA por lo que el siguiente paso es Imprimir el Contrato de Beca que estará disponible desde el {leer_fecha_hora_letra_formato_fecha_hora(str(fechainicioimprimircontrato.date()), str(fechainicioimprimircontrato.time()), True)}"
                    # if solicitud.tiposolicitud == 2:
                    #     return HttpResponseRedirect("/alu_becas")
                    # else:
                    #     if inscripcion.persona.documentos_personales() and not DEBUG:
                    #         if inscripcion.persona.cedula_solicitante_representante_validadas():
                    #             return HttpResponseRedirect("/alu_becas?info=%s" % msg)

                    isPersonaExterior = persona.ecuatoriano_vive_exterior()
                    data["isPersonaExterior"] = isPersonaExterior
                    data["estado_no_cargardocumentos"] = [5, 2] # 2 validadado y 5 en revision

                    return render(request, "alu_becas/actualizardatos.html", data)
                except Exception as ex:
                    pass

            elif action == 'solicitarbeca':
                try:
                    # if inscripcion.modalidad_id == 3:
                    #     return HttpResponseRedirect("/?info=Sólo aplican estudiantes de la modalidad Presencial y Semipresencial.")

                    # if inscripcion.tienesolicitudbecacovid():
                    #     return HttpResponseRedirect("/alu_becas?info=Usted ya posee una solicitud de beca para el periodo actual.")

                    if inscripcion.tienesolicitudbeca():
                        return HttpResponseRedirect("/alu_becas?info=Usted ya posee una solicitud de beca para el periodo actual.")

                    if periodo.id != 113:
                        return HttpResponseRedirect("/?info=Para solicitar una beca debe seleccionar el periodo actual.")

                    if not Matricula.objects.filter(inscripcion__persona=persona, nivel__periodo_id=113, status=True).exists():
                        return HttpResponseRedirect("/?info=Para poder solicitar la beca debe estar matriculado en el periodo actual.")

                    matricula = Matricula.objects.get(inscripcion__persona=persona, nivel__periodo_id=113, status=True)
                    if matricula.nivelmalla_id == 1:
                        return HttpResponseRedirect(u"/?info=Únicamente aplican estudiantes matriculados desde segundo nivel.")

                    verifica = matricula.cumple_requisitos_generales_beca()
                    # if not verifica['cumplerequisitos']:
                    #     return HttpResponseRedirect("/?info=Usted no cumple con los requisitos para solicitar beca en este periodo.")

                    data['title'] = u'Agregar Solicitud de Beca'
                    data['datoscompletosdiscapacidad'] = ""
                    tipo = 0
                    matriculanterior = verifica['matriculaanterior']
                    tipo_beca_id = request.GET['tb'] if 'tb' in request.GET and request.GET['tb'] else 0
                    tipos = BecaTipo.objects.filter(status=True, vigente=True, pk__in=[17, 18, 19, 20, 21, 22])
                    if tipos.filter(pk=tipo_beca_id).exists():
                        tipos = tipos.filter(pk=tipo_beca_id)
                        tipo = tipos.first().id

                    if tipo_beca_id == 19:
                        tipo = 19
                        p = persona.mi_perfil()
                        if p.porcientodiscapacidad > 0 and p.porcientodiscapacidad is not None and \
                                p.carnetdiscapacidad != '' and p.carnetdiscapacidad is not None and p.archivo and p.institucionvalida:
                            data['datoscompletosdiscapacidad'] = "SI"
                        else:
                            data['datoscompletosdiscapacidad'] = "NO"

                    # if matriculanterior.cumple_requisitos_beca_situacioneconomica():
                    #     tipos = [18]
                    #     tipo = 18
                    # if matriculanterior.cumple_requisitos_beca_discapacidad():
                    #     tipos = [19]
                    #     tipo = 19
                    #     p = persona.mi_perfil()
                    #     if p.porcientodiscapacidad > 0 and p.porcientodiscapacidad is not None and \
                    #             p.carnetdiscapacidad != '' and p.carnetdiscapacidad is not None and p.archivo and p.institucionvalida:
                    #         data['datoscompletosdiscapacidad'] = "SI"
                    #     else:
                    #         data['datoscompletosdiscapacidad'] = "NO"
                    # else:
                    #     tipos = [18, 19]
                    #     tipo = 0

                    data['tipobeca'] = tipos
                    data['tipobecapermitido'] = tipo
                    data['modalidad'] = inscripcion.modalidad_id

                    return render(request, "alu_becas/solicitarbeca.html", data)
                except Exception as ex:
                    pass

            elif action == 'mostrarrequisitos':
                try:
                    data = {}
                    tipobeca = int(request.GET['tipobeca'])
                    procesar = True

                    if periodo.id != 113:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar el periodo lectivo actual."})

                    matriculaactual = Matricula.objects.get(inscripcion=inscripcion, nivel__periodo=periodo, status=True)

                    if matriculaactual.nivelmalla_id == 1:
                        return JsonResponse({"result": "bad", "mensaje": u"Únicamente aplican estudiantes matriculados desde segundo nivel."})

                    totalmatriculas = Matricula.objects.values('nivel__periodo_id').filter(inscripcion__persona=persona, status=True, estado_matricula__in=[2,3], nivel__periodo__activo=True).count()
                    if Matricula.objects.values('nivel__periodo_id').filter(inscripcion__persona=persona, status=True, estado_matricula__in=[2,3], nivel__periodo__activo=True).count() > 1:
                        periodomatriculaanterior = Matricula.objects.values('nivel__periodo_id').filter(inscripcion__persona=persona, status=True, estado_matricula__in=[2,3], nivel__periodo__activo=True).order_by('-nivel__periodo__fin')[1]
                        matriculaanterior = Matricula.objects.get(inscripcion__persona=persona, nivel__periodo_id=periodomatriculaanterior['nivel__periodo_id'], status=True)

                        if matriculaanterior.mis_materias_sin_retiro().count() == 0:
                            if totalmatriculas >= 3:
                                periodomatriculaanterior = Matricula.objects.values('nivel__periodo_id').filter(inscripcion__persona=persona, status=True, estado_matricula__in=[2,3], nivel__periodo__activo=True).order_by('-nivel__periodo__fin')[2]
                                matriculaanterior = Matricula.objects.get(inscripcion__persona=persona, nivel__periodo_id=periodomatriculaanterior['nivel__periodo_id'], status=True)
                            else:
                                procesar = False
                    else:
                        procesar = False

                    if not procesar:
                        return JsonResponse({"result": "bad", "mensaje": u"No cumple con todos los requisitos."})


                    requisitos = BecaRequisitos.objects.filter(Q(becatipo__isnull=True) | Q(becatipo_id=tipobeca), periodo_id=90, status=True, vigente=True).exclude(numero=7).order_by('numero')

                    lista_requisitos = []
                    cumple_todos = True
                    evaluado = False
                    contador = 1
                    lista_nocumplen = ""
                    cnc = 0

                    for req in requisitos:
                        idrequisito = req.id
                        numero = req.numero
                        nombre = req.nombre
                        tipo = req.becatipo.nombre if req.becatipo else ''
                        valor = req.valoresrequisito
                        camposeleccion = 'N'

                        cumple = True

                        if numero == 1 or numero == 2:
                            if evaluado is False:
                                if persona.paisnacimiento_id == 1:
                                    cumple = True
                                else:
                                    if persona.paisnacimiento_id is not None:
                                        if persona.pais_id == 1:
                                            cumple = True
                                        else:
                                            cumple = False
                                            cumple_todos = False
                                    else:
                                        cumple = False
                                        cumple_todos = False

                        elif numero == 3:
                            inscripcion.matricula()
                            if not inscripcion.matriculado_periodo(periodo):
                                cumple = False
                                cumple_todos = False
                        elif numero == 4:
                            if matriculaactual.tipomatriculalumno() != 'REGULAR':
                                cumple = False
                                cumple_todos = False
                        elif numero == 5:
                            if inscripcion.tiene_sancion():
                                cumple = False
                                cumple_todos = False
                        elif numero == 6:
                            if not matriculaanterior.materias_aprobadas_todas():
                                cumple = False
                                cumple_todos = False
                        elif numero == 8:
                            if persona.tiene_becas_externas_activas():
                                cumple = False
                                cumple_todos = False
                        elif numero == 9:
                            # Campo no existe
                            camposeleccion = 'S'
                            cumple = True
                        elif numero == 10:
                            # Campo no existe
                            camposeleccion = 'S'
                            cumple = True
                        elif numero == 22 or numero == 25:
                            if matriculaanterior.promedio_nota_dbu() < Decimal(valor):
                                cumple = False
                                cumple_todos = False
                        elif numero == 23 or numero == 26:
                            if matriculaanterior.promedio_asistencias_dbu() < Decimal(valor):
                                cumple = False
                                cumple_todos = False
                        elif numero == 24:
                            grupossoc = valor.split(",")
                            if persona.mi_ficha().grupoeconomico:
                                if not persona.mi_ficha().grupoeconomico.codigo in grupossoc:
                                    cumple = False
                                    cumple_todos = False
                            else:
                                cumple = False
                                cumple_todos = False
                        elif numero == 27:
                            p = persona.mi_perfil()
                            if not p.tienediscapacidad:
                                cumple = False
                                cumple_todos = False

                        if numero == 1 or numero == 2:
                            if evaluado is False:
                                if cumple:
                                    lista_requisitos.append([idrequisito, tipo, nombre, 'SI', numero, camposeleccion])
                                else:
                                    lista_requisitos.append([idrequisito, tipo, nombre, 'NO', numero, camposeleccion])
                                    lista_nocumplen = "No. " + str(
                                        numero) + ", " + nombre if lista_nocumplen == '' else lista_nocumplen + ", " + "No. " + str(
                                        numero) + ", " + nombre
                                    cnc += 1
                                contador += 1
                                evaluado = True
                        else:
                            if cumple:
                                lista_requisitos.append([idrequisito, tipo, nombre, 'SI', numero, camposeleccion])
                            else:
                                lista_requisitos.append([idrequisito, tipo, nombre, 'NO', numero, camposeleccion])
                                lista_nocumplen = "No. " + str(
                                    contador) + ", " + nombre if lista_nocumplen == '' else lista_nocumplen + ", " + "No. " + str(
                                    contador) + ", " + nombre
                                cnc += 1
                            contador += 1

                    data['requisitos'] = lista_requisitos
                    data['lista_nocumplen'] = lista_nocumplen
                    data['cumple_todos'] = "SI" if cumple_todos else "NO"
                    data['periodovalida'] = periodomatriculaanterior['nivel__periodo_id']
                    template = get_template("alu_becas/requisitosbeca.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'subirdocumentocedula':
                try:
                    cedula1oblig = cert1oblig = cedula2oblig = cert2oblig = actaoblig = servibasoblig = razaoblig =  False
                    documentos = persona.documentos_personales()
                    form = BecaSolicitudSubirCedulaForm()
                    solicitud = BecaSolicitud.objects.get(pk=int(request.GET['id']))
                    mostrarcampoacta = True if solicitud.becatipo.id == 16 else False
                    mostrarcamposervicio = True if solicitud.becatipo.id == 22 and solicitud.inscripcion.persona.ecuatoriano_vive_exterior() else False
                    mostrarcamporaza = True if solicitud.becatipo.id == 21 else False

                    if documentos:
                        if documentos.estadocedula == 3:
                            cedula1oblig = True
                        elif documentos.estadocedula == 2:
                            form.borrar_campos(1)

                        if documentos.estadopapeleta == 3:
                            cert1oblig = True
                        elif documentos.estadopapeleta == 2:
                            form.borrar_campos(2)

                        if documentos.estadocedularepresentantesol == 3:
                            cedula2oblig = True
                        elif documentos.estadocedularepresentantesol == 2:
                            form.borrar_campos(3)

                        if documentos.estadopapeletarepresentantesol == 3:
                            cert2oblig = True
                        elif documentos.estadopapeletarepresentantesol == 2:
                            form.borrar_campos(4)

                        if solicitud.becatipo.id == 16:
                            if documentos.estadoactagrado == 3:
                                actaoblig = True
                            elif documentos.estadoactagrado == 2:
                                form.borrar_campos(5)
                        else:
                            form.borrar_campos(5)

                        if solicitud.becatipo.id == 22 and solicitud.inscripcion.persona.ecuatoriano_vive_exterior():
                            if documentos.estadoserviciosbasico == 3:
                                servibasoblig = True
                            elif documentos.estadoserviciosbasico == 2:
                                form.borrar_campos(6)
                        else:
                            form.borrar_campos(6)
                    else:
                        cedula1oblig = cert1oblig = cedula2oblig = cert2oblig = True
                        if mostrarcampoacta:
                            actaoblig = True
                        if mostrarcamposervicio:
                            servibasoblig = True

                    if mostrarcamporaza:
                        if PerfilInscripcion.objects.filter(persona=solicitud.inscripcion.persona).exists():
                            perfil = PerfilInscripcion.objects.filter(persona=solicitud.inscripcion.persona).first()
                            if perfil.estadoarchivoraza == 3 or perfil.estadoarchivoraza is None:
                                razaoblig = True
                            elif perfil.estadoarchivoraza == 2:
                                form.borrar_campos(7)
                        else:
                            razaoblig = True
                    else:
                        form.borrar_campos(7)


                    # if not mostrarcampoacta:
                    #     form.borrar_campos(5)
                    # if not mostrarcamposervicio:
                    #     form.borrar_campos(6)

                    data['title'] = u'Actualizar PDF Documentos'
                    data['id'] = int(request.GET['id'])
                    data['form'] = form
                    data['cedula1oblig'] = cedula1oblig
                    data['cert1oblig'] = cert1oblig
                    data['cedula2oblig'] = cedula2oblig
                    data['cert2oblig'] = cert2oblig
                    data['actaoblig'] = actaoblig
                    data['servibasoblig'] = servibasoblig
                    data['razaoblig'] = razaoblig
                    data['mostrarcampoacta'] = mostrarcampoacta
                    data['mostrarcamposervicio'] = mostrarcamposervicio
                    data['mostrarcamporaza'] = mostrarcamporaza

                    template = get_template("alu_becas/subirdocumentocedula.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'subircontratobeca':
                try:
                    form = BecaSubirContratoForm()

                    data['title'] = u'Subir Contrato de Beca Firmado'
                    data['id'] = int(request.GET['id'])
                    data['form'] = form

                    template = get_template("alu_becas/subircontratobeca.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'representantesolidario':
                try:
                    data['title'] = u'Actualizar Representante Solidario'
                    data['id'] = int(request.GET['id'])
                    representante = persona.personaextension_set.all()[0]

                    data['form'] = RepresentanteSolidarioForm(initial={'cedula': representante.cedularepsolidario,
                                                                       'nombre': representante.nombresrepsolidario,
                                                                       'apellido1': representante.apellido1repsolidario,
                                                                       'apellido2': representante.apellido2repsolidario
                                                                       })

                    template = get_template("alu_becas/representantesolidario.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'cuentabancaria':
                try:
                    data['title'] = u'Actualizar Cuenta Bancaria'
                    data['id'] = int(request.GET['id'])
                    cuentabancaria = persona.cuentabancaria()
                    data['form'] = CuentaBancariaBecadoForm(initial={'banco': cuentabancaria.banco,
                                                            'numero': cuentabancaria.numero,
                                                            'tipocuentabanco': cuentabancaria.tipocuentabanco})

                    certcuentaoblig = False
                    if cuentabancaria.estadorevision == 3:
                        certcuentaoblig = True

                    data['certcuentaoblig'] = certcuentaoblig
                    template = get_template("alu_becas/cuentabancaria.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'addcuentabancaria':
                try:
                    data['title'] = u'Agregar Cuenta Bancaria'
                    data['id'] = int(request.GET['id'])
                    cuentabancaria = persona.cuentabancaria()
                    data['form'] = CuentaBancariaBecadoForm()
                    data['cuentabancaria'] = cuentabancaria

                    template = get_template("alu_becas/addcuentabancaria.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'comprobanteventa':
                try:
                    data['title'] = u'Comprobante de Venta'
                    data['id'] = int(request.GET['id'])

                    beca = BecaAsignacion.objects.get(solicitud_id=int(request.GET['id']))
                    comprobante = beca.becacomprobanteventa_set.filter(status=True)[0] if beca.becacomprobanteventa_set.filter(status=True).exists() else None

                    comprobanteoblig = False
                    totaloblig = True
                    if not comprobante:
                        form = BecaComprobanteVentaForm()
                        comprobanteoblig = True
                    else:
                        form = BecaComprobanteVentaForm(initial={'rucproveedor': comprobante.rucproveedor,
                                                                 'total': comprobante.total})
                        if comprobante.estadorevisiondbu == 2:
                            form.borrar_campos()
                            totaloblig = False

                        if comprobante.estadorevisiondbu == 3 or comprobante.estadorevisionfin == 3:
                            comprobanteoblig = True

                    data['form'] = form
                    data['comprobanteoblig'] = comprobanteoblig
                    data['totaloblig'] = totaloblig
                    template = get_template("alu_becas/comprobanteventa.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'agregarcomprobanteventa':
                try:
                    data['title'] = u'Agregar Comprobante de Venta'
                    data['id'] = int(request.GET['id'])

                    beca = BecaAsignacion.objects.get(solicitud_id=int(request.GET['id']))

                    comprobanteoblig = True
                    totaloblig = True

                    form = BecaComprobanteVentaForm()

                    data['form'] = form
                    data['comprobanteoblig'] = comprobanteoblig
                    data['totaloblig'] = totaloblig

                    # template = get_template("alu_becas/comprobanteventa.html")
                    template = get_template("alu_becas/addcomprobante.html")

                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'editarcomprobanteventa':
                try:
                    data['title'] = u'Editar Comprobante de Venta'
                    data['idc'] = int(request.GET['idc'])

                    comprobante = BecaComprobanteVenta.objects.get(pk=request.GET['idc'])

                    form = BecaComprobanteVentaEditForm(initial={'rucproveedor2': comprobante.rucproveedor,
                                                             'total2': comprobante.total})
                    totaloblig = True
                    comprobanteoblig = False
                    if comprobante.estadorevisiondbu == 2:
                        form.borrar_campos()
                        totaloblig = False

                    if comprobante.estadorevisiondbu == 3 or comprobante.estadorevisionfin == 3:
                        comprobanteoblig = True

                    data['form'] = form
                    data['comprobanteoblig'] = comprobanteoblig
                    data['totaloblig'] = totaloblig

                    # template = get_template("alu_becas/editcomprobanteventa.html")
                    template = get_template("alu_becas/editcomprobante2.html")

                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'aceptar_rechazar_beca':
                try:
                    tipo = request.GET['tipo']
                    data['title'] = title = u'Términos y condiciones Aceptar Beca' if tipo == 'A' else u'Rechazar Beca'
                    data['id'] = int(request.GET['id'])
                    becasolicitud = BecaSolicitud.objects.get(pk=int(request.GET['id']))
                    data['tipobeca'] = becasolicitud.becatipo.id
                    data['fichasocio'] = fichasocio = FichaSocioeconomicaINEC.objects.filter(persona=persona, status=True).first()
                    grupoeconomico = fichasocio.grupoeconomico
                    form = BecaAceptarRechazarForm()
                    if tipo == 'A':
                        form.borrar_campos()
                        template = get_template("alu_becas/aceptarbeca.html")
                    else:
                        template = get_template("alu_becas/rechazarbeca.html")
                    data['form'] = form
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': title})
                except Exception as ex:
                    pass

            elif action == 'anular_solicitud':
                try:
                    data['title'] = u'Desistir Solicitud de Beca'
                    data['id'] = int(request.GET['id'])

                    form = BecaSolicitudAnularForm()

                    template = get_template("alu_becas/anularsolicitudbeca.html")
                    data['form'] = form
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'datosdiscapacidad':
                try:
                    data['title'] = u'Actualizar Datos Discapacidad'
                    # data['id'] = int(request.GET['id'])
                    # data['form'] = BecaSolicitudSubirCedulaForm

                    perfil = persona.mi_perfil()
                    form = DiscapacidadForm(initial={
                                                     'tipodiscapacidad': perfil.tipodiscapacidad,
                                                     'porcientodiscapacidad': perfil.porcientodiscapacidad,
                                                     'carnetdiscapacidad': perfil.carnetdiscapacidad,
                                                     'institucionvalida': perfil.institucionvalida})
                    form.ocultarcampos()
                    form.bloquearcampos()
                    tienearchivo = True if perfil.archivo else False
                    data['form'] = form
                    data['tienearchivo'] = tienearchivo

                    template = get_template("alu_becas/datosdiscapacidad.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'mostrarrecorrido':
                try:
                    data = {}
                    data['solicitud'] = solicitud = BecaSolicitud.objects.get(pk=int(request.GET['id']))
                    data['recorrido'] = solicitud.becasolicitudrecorrido_set.filter(status=True).order_by('id')
                    template = get_template("adm_becas/recorridosolicitud.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'mostrardocumentos':
                try:
                    data = {}
                    data['documentos'] = persona.documentos_personales()
                    data['cuentabancaria'] = persona.cuentabancaria()
                    data['beca'] = beca = BecaAsignacion.objects.get(solicitud_id=int(request.GET['id']))
                    idperiodobeca = beca.solicitud.periodo.id
                    data['inscripcion'] =  beca.solicitud.inscripcion
                    data['documentopersonal'] = persona.personadocumentopersonal_set.filter(status=True).first()
                    data['cuentabancaria'] = cuentabancaria = persona.cuentabancaria()
                    data['perfil'] = persona.mi_perfil()
                    data['deportista'] = persona.deportistapersona_set.filter(status=True).first()
                    isPersonaExterior = persona.ecuatoriano_vive_exterior()
                    data["isPersonaExterior"] = isPersonaExterior
                    perilinscripcion = None
                    if beca.solicitud.inscripcion.persona.perfilinscripcion_set.filter(status=True).exists():
                        perilinscripcion = beca.solicitud.inscripcion.persona.perfilinscripcion_set.filter(status=True).first()
                    data['perilinscripcion'] = perilinscripcion
                    becaperiodo = None
                    if BecaPeriodo.objects.filter(periodo_id=idperiodobeca).exists():
                        becaperiodo = BecaPeriodo.objects.get(periodo_id=idperiodobeca)

                    data['becaperiodo'] = becaperiodo
                    data['docvalidado'] = persona.cedula_solicitante_representante_validadas() if beca.solicitud.becatipo.id != 16 else persona.cedula_solicitante_representante_validadasbpn()

                    comprobantes = beca.becacomprobanterevision_set.filter(status=True)
                    data['comprobante'] = comprobantes[0] if comprobantes else None

                    template = get_template("alu_becas/mostrardocumentos.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'mostrarcomprobantes':
                try:
                    data = {}
                    fechaactual = datetime.now().date()
                    data['beca'] = beca = BecaAsignacion.objects.get(solicitud_id=int(request.GET['id']))
                    enovedad = "S" if beca.solicitud.existen_novedades_documentos() else "N"

                    revisioncomprobante = beca.becacomprobanterevision_set.filter(status=True)[0] if beca.becacomprobanterevision_set.filter(status=True).exists() else None
                    data['comprobantes'] = comprobantes = revisioncomprobante.becacomprobanteventa_set.filter(status=True).order_by('id') if revisioncomprobante else None

                    detallepago = beca.solicitudpagobecadetalle_set.all()[0]
                    fechaacredita = datetime.strptime(str(detallepago.fechaacredita)[:10], "%Y-%m-%d").date()
                    diastranscurridos = abs((fechaactual - fechaacredita).days)

                    PLAZO = 350# 150 dias :D

                    if not comprobantes:
                        data['permitiragregar'] = True if diastranscurridos <= PLAZO else False
                    else:
                        cargado = comprobantes.filter(estadorevisiondbu=1).count()
                        rechazado = comprobantes.filter(estadorevisiondbu__in=[3, 6]).count()
                        data['permitiragregar'] = True if rechazado > 0 or cargado > 0 else False

                    data['mostrarmensajeplazo'] = True if not comprobantes and diastranscurridos > PLAZO else False
                    data['fechaacredita'] = fechaacredita
                    data['fechaactual'] = fechaactual
                    data['dias'] = diastranscurridos + 1

                    data['modolectura'] = True if request.GET['modo'] == 'L' else False

                    template = get_template("alu_becas/mostrarcomprobantes.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'enovedad': enovedad})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addevidencia':
                try:
                    data['title'] = u'Subir Evidencia'
                    data['form'] = BecaDetalleSolicitudArchivoForm
                    data['idinscripcion'] = request.GET['idinscripcion']
                    data['idtipo'] = request.GET['idtipo']
                    data['idevidencia'] = request.GET['idevidencia']
                    data['idsolicitud'] = request.GET['idsolicitud']
                    template = get_template("alu_becas/add_evidencia.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'subirarchivoutilizacion':
                try:
                    data['title'] = u'Subir Evidencia Utilización'
                    data['idasignacion'] = idasignacion= request.GET['idasignacion']
                    data['idutilizacion'] =idutilizacion= request.GET['idutilizacion']
                    data['idinscripcion'] = request.GET['idinscripcion']
                    # utilizacion=BecaUtilizacion.objects.get(id=idutilizacion)
                    asignacion=BecaAsignacion.objects.get(id=int(idasignacion))
                    form = BecaDetalleUtilizacionForm(initial={'utilizacion': idutilizacion})
                    form.bloquear(asignacion)
                    data['form'] = form
                    template = get_template("alu_becas/add_evidencia_utilizacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'becautilizacion':
                try:
                    data['title'] = u'JUSTIFICATIVOS PARA LOS DESEMBOLSOS DE LA BECA'
                    data['id'] = id=int(request.GET['id'])
                    data['asignacion']=asignacion=BecaAsignacion.objects.filter(status=True,solicitud__inscripcion_id=id,solicitud__periodo=periodo)[0]
                    data['utilizacion']=utilizacion = BecaUtilizacion.objects.filter(status=True,vigente=True)
                    if BecaDetalleUtilizacion.objects.filter(status=True,asignacion=asignacion).exists():
                        data['detalle'] = BecaDetalleUtilizacion.objects.filter(status=True,asignacion=asignacion)
                    return render(request, "alu_becas/becautilizacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'iniciosolicitud':
                try:
                    data['title'] = u'Beca estudiantil'
                    data['idtipo'] = idtipo = int(request.GET['idtipo'])
                    mat = Matricula.objects.filter(inscripcion__persona=persona, nivel__periodo=periodo)[0]
                    if BecaAsignacion.objects.filter(solicitud__inscripcion=mat.inscripcion,solicitud__periodo=periodo).exists():
                        esbecado = True
                        data['esbecado'] = esbecado
                        data['becaperiodo']=becaperiodo=BecaAsignacion.objects.filter(solicitud__inscripcion=mat.inscripcion)[0].solicitud.periodo.nombre
                    else:
                        esbecado = False
                        data['esbecado'] = esbecado
                    data['matricula'] = mat
                    data['requisito'] = BecaRequisitos.objects.filter(status=True, vigente=True).order_by('id')
                    data['tipobeca'] = BecaTipo.objects.get(id=idtipo, status=True, vigente=True)
                    if BecaSolicitud.objects.filter(inscripcion__persona=persona, periodo=periodo).exists():
                        solicito=True
                        data['solicito']=solicito
                    else:
                        solicito = False
                        data['solicito'] = solicito
                    return render(request, "alu_becas/iniciar.html", data)
                except Exception as ex:
                    pass

            elif action == 'detalletipobeca':
                try:
                    data = {}
                    mat = Matricula.objects.filter(inscripcion__persona=persona, nivel__periodo=periodo)[0]
                    # ins= Inscripcion.objects.filter(persona__id=18803)
                    # ins= 23366
                    data['matricula'] = mat
                    data['perfil']=PerfilInscripcion.objects.filter(persona=mat.inscripcion.persona)
                    data['notas']=mat.promedio_asistencia_alumno_sin(anterior.id)
                    data['quintil']=MatriculaGrupoSocioEconomico.objects.filter(matricula=mat)[0]
                    tipo = BecaTipo.objects.get(pk=int(request.GET['id']))
                    data['tipo'] = tipo
                    template = get_template("alu_becas/detalletipobeca.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'subirarchivos':
                try:
                    data['title'] = 'Subir Archivos Envidencia de Solicitud'

                    id = int(request.GET['id'])
                    data['idtipo'] = idtipo = int(request.GET['idtipo'])
                    data['idinscripcion'] = id
                    fecha = datetime.now()
                    lista=[]
                    if BecaSolicitud.objects.filter(inscripcion_id=id, periodo=periodo).exists():
                        requisito=BecaRequisitos.objects.filter(status=True)
                        cabecera = BecaSolicitud.objects.get(inscripcion_id=id, periodo=periodo)
                        data['cabecerasolicitud'] = cabecera
                        for x in requisito:
                            lista.append( cabecera.becadetallesolicitud_set.filter(requisito=x).order_by('requisito__id','-fechaaprueba')[0])
                        data['detallesolicitud']=lista
                        return render(request, "alu_becas/subirarchivos.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'detallerquisito':
                try:
                    data = {}
                    idrequisito = int(request.GET['idr'])
                    data['requisito']=BecaRequisitos.objects.get(id=idrequisito)
                    data['idsolicitud'] = idsolicitud = int(request.GET['ids'])
                    data['detalle']=BecaDetalleSolicitud.objects.filter(status=True,solicitud_id=idsolicitud,requisito_id=idrequisito)
                    template = get_template("alu_becas/detallerequisito.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'revision_verificacion_documentos':
                try:
                    data = {}
                    idrequisito = int(request.GET['id'])
                    data['solicitud'] = solicitud = BecaSolicitud.objects.get(id=idrequisito)
                    data['inscripcion'] = solicitud.inscripcion
                    data['documentopersonal'] = persona.personadocumentopersonal_set.filter(status=True).first()
                    data['cuentabancaria'] = cuentabancaria = persona.cuentabancaria_becas()
                    data['perfil'] = persona.mi_perfil()
                    data['deportista'] = persona.deportistapersona_set.filter(status=True).first()
                    template = get_template("alu_becas/tabla_revisiondocumentos.html")
                    isPersonaExterior = persona.ecuatoriano_vive_exterior()
                    data["isPersonaExterior"] = isPersonaExterior
                    url_path = 'http://127.0.0.1:8000'
                    if not DEBUG:
                        url_path = 'https://sga.unemi.edu.ec'
                    data['url_path'] = url_path
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})


            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Beca estudiantil'
                # solicitudes = BecaSolicitud.objects.filter(inscripcion__persona=persona, status=True).order_by('-id')
                solicitudes = BecaSolicitud.objects.filter(inscripcion=inscripcion, status=True).order_by('-id')
                # mimalla = inscripcion.mi_malla()
                aplica_beca = False
                tipo_beca = 0
                can_actualizar_data = False
                periodovigente_id = None

                if solicitudes.filter(status=True, periodo=periodo).exclude(estado__in=[5, 3]).exists():
                    data['solicitudbeca'] = solicitudbeca = solicitudes.filter(status=True, periodo=periodo).exclude(estado__in=[5, 3]).first()
                    if solicitudbeca.puede_actualizar_documentos():
                        if solicitudbeca.becatipo.id == 21 and not solicitudbeca.inscripcion.persona.tiene_documento_raza():
                            messages.add_message(request, messages.WARNING, f'Favor subir documento de declaración juramentada en la solicitud de beca')

                if solicitudes.filter(periodo=periodo, periodocalifica=anterior).exclude(estado=5).exists():
                    aplica_beca = False
                    tipo_beca = solicitudes.filter(periodo=periodo, periodocalifica=anterior).exclude(estado=5).order_by('-id').first().becatipo.id
                    if BecaPeriodo.objects.filter(periodo=periodo, vigente=True).exists():
                        becaperiodo = BecaPeriodo.objects.get(periodo=periodo, vigente=True)
                        fechainicio = becaperiodo.fechainiciosolicitud.date()
                        fechafin = becaperiodo.fechafinsolicitud.date()
                        fechaactual = datetime.now().date()
                        if inscripcion.tienesolicitudbeca():
                            if fechaactual >= fechainicio and fechaactual <= fechafin:
                                can_actualizar_data = True
                                periodovigente_id = becaperiodo.periodo_id
                                if inscripcion.solicitudaprobadaperiodo(periodo) and inscripcion.becapendienteaceptarperiodo(periodo):
                                    MAXIMO_DIAS_ACEPTAR = (fechafin - fechainicio).days
                                    solicitud = solicitudes.filter(status=True, periodo=periodo)[0]
                                    # solicitud = BecaSolicitud.objects.filter(inscripcion__persona=inscripcion.persona, status=True, periodo=periodo)[0]
                                    fechaaprobacion = datetime.strptime(str(solicitud.fecha_modificacion)[:10], "%Y-%m-%d").date()
                                    plazo = MAXIMO_DIAS_ACEPTAR - abs((fechaactual - fechaaprobacion).days)

                                    if plazo > 0:
                                        # data['tipomensaje'] = 'MENSAJEBECA'
                                        data['aplica_beca'] = aplica_beca = True
                                        textomensajebeca = f"""<span style="font-size: 30px; font-family: 'Montserrat', sans-serif;"><strong>Estimad{'a' if inscripcion.persona.sexo_id == 1 else 'o'} estudiante</strong></span><br><br><span style="font-size:17px; font-family: 'Montserrat', sans-serif;">Informamos que su solicitud de Beca de tipo <strong>{solicitud.becatipo.nombre.upper()}</strong> para el Periodo Académico {str(solicitud.periodo)}, fue <strong>APROBADA</strong> el {str(solicitud.fecha_modificacion)[:10]}. Por lo tanto, <strong>dispone de {str(plazo)}</strong> días para ingresar al módulo <a href="/alu_becas" style="text-decoration:none; color:#ffffff"><strong>BECA ESTUDIANTIL</strong></a> y ACEPTAR o RECHAZAR este beneficio.</span> <br><br><span style="font-size: 17px; font-family: 'Montserrat', sans-serif;"><strong>IMPORTANTE:</strong> Pasado el plazo establecido y en caso de no haber ACEPTADO la BECA; la misma será RECHAZADA automáticamente.</span>"""
                                        data['textomensajebeca'] = textomensajebeca
                            else:
                                if fechaactual < fechainicio:
                                    solicitudes = solicitudes.exclude(periodo=periodo)

                data['aplica_beca'] = aplica_beca
                data['tipo_beca'] = tipo_beca
                data['mostrarboton'] = False
                data['solicitudes'] = solicitudes
                data['mensajecomprobante'] = persona.obligado_a_cargar_comprobante_venta_beca()
                data['can_actualizar_data'] = can_actualizar_data
                data['periodovigente_id'] = periodovigente_id
                return render(request, "alu_becas/view.html", data)

            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
