# -*- coding: UTF-8 -*-
from dateutil.relativedelta import relativedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction, connections
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from datetime import datetime, date, timedelta
import time as pausaparaemail

from django.template import Context
from django.template.loader import get_template

from decorators import secure_module, last_access
from sagest.commonviews import obtener_estado_solicitud
from sagest.models import Rubro, CompromisoPagoPosgrado, CompromisoPagoPosgradoRecorrido, RubroRefinanciamiento, \
    CuentaContable
from sga.commonviews import adduserdata, secuencia_contrato_beca
from sga.forms import SolicitudDevolucionForm, SolicitudRefinanciamientoPosgradoForm, BecaSubirContratoForm, \
    RefinanciamientoPosgradoSubirJustificativoForm, RefinanciamientoPosgradoSubirComprobantePagoForm
from sga.funciones import MiPaginador, log, variable_valor, generar_nombre, cuenta_email_disponible, \
    cuenta_email_disponible_para_envio, null_to_decimal, validar_archivo
from sga.models import CuentaBancariaPersona, SolicitudDevolucionDinero, SolicitudDevolucionDineroRecorrido, \
    SolicitudRefinanciamientoPosgrado, SolicitudRefinanciamientoPosgradoRecorrido, \
    SolicitudRefinanciamientoPosgradoDetalle, miinstitucion, CUENTAS_CORREOS
from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt


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
    matricula = inscripcion.matricula_periodo(periodo)

    if inscripcion.mi_coordinacion().id != 7:
        return HttpResponseRedirect("/?info=El Módulo está disponible solo para estudiantes de posgrado.")

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addsolicitud':
            conexion = connections['epunemi']
            cnepunemi = conexion.cursor()
            try:
                form = SolicitudRefinanciamientoPosgradoForm(request.POST, request.FILES)

                if 'archivocertmedico' in request.FILES:
                    descripcionarchivo = 'Certificado Médico'
                    resp = validar_archivo(descripcionarchivo, request.FILES['archivocertmedico'], ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                if 'archivoculmilaboral' in request.FILES:
                    descripcionarchivo = 'Certificado Culminación Relación Laboral'
                    resp = validar_archivo(descripcionarchivo, request.FILES['archivoculmilaboral'], ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                if 'archivoafiliaseguro' in request.FILES:
                    descripcionarchivo = 'Certificado Afiliación Seguro'
                    resp = validar_archivo(descripcionarchivo, request.FILES['archivoafiliaseguro'], ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                if 'archivoactadefun' in request.FILES:
                    descripcionarchivo = 'Acta de Defunción'
                    resp = validar_archivo(descripcionarchivo, request.FILES['archivoactadefun'], ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                if 'archivocertmedicofam' in request.FILES:
                    descripcionarchivo = 'Certificado Médico'
                    resp = validar_archivo(descripcionarchivo, request.FILES['archivocertmedicofam'], ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                if 'archivootro' in request.FILES:
                    descripcionarchivo = 'Justificativo'
                    resp = validar_archivo(descripcionarchivo, request.FILES['archivootro'], ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                if 'archivosueldo' in request.FILES:
                    descripcionarchivo = 'Certificado / Rol de Pago'
                    resp = validar_archivo(descripcionarchivo, request.FILES['archivosueldo'], ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                if form.is_valid():
                    if SolicitudRefinanciamientoPosgrado.objects.values('id').filter(persona=persona, status=True).exclude(estado__valor__in=[17, 24]).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Usted ya cuenta con una solicitud registrada"})
                    motivo = int(form.cleaned_data['motivo'])
                    archivo1 = archivo2 = None
                    if motivo == 1:
                        archivo1 = request.FILES['archivocertmedico']
                        archivo1._name = generar_nombre("certmedicoalumno", archivo1._name)
                    elif motivo == 2:
                        archivo1 = request.FILES['archivoculmilaboral']
                        archivo1._name = generar_nombre("certculmlaboralalumno", archivo1._name)
                        archivo2 = request.FILES['archivoafiliaseguro']
                        archivo2._name = generar_nombre("certafiliaseguroalumno", archivo2._name)
                    elif motivo == 3:
                        archivo1 = request.FILES['archivoactadefun']
                        archivo1._name = generar_nombre("actadefunfamiliaralumno", archivo1._name)
                    elif motivo == 4:
                        archivo1 = request.FILES['archivocertmedicofam']
                        archivo1._name = generar_nombre("certmedicofamiliaralumno", archivo1._name)
                    elif motivo == 6:
                        archivo1 = request.FILES['archivosueldo']
                        archivo1._name = generar_nombre("certsueldorolpago", archivo1._name)
                    else:
                        archivo1 = request.FILES['archivootro']
                        archivo1._name = generar_nombre("justificativoalumno", archivo1._name)

                    valorpagado = matricula.total_pagado_alumno()
                    cuotasvencidas = matricula.numero_cuotas_vencidas()

                    descuento = matricula.tiene_descuento_posgrado()
                    if descuento:
                        valordescuento = descuento.valordescuento
                    else:
                        valordescuento = 0

                    costoprograma = matricula.costo_programa()


                    if not matricula.retiradomatricula:
                        valorgenerado = matricula.total_generado_alumno()
                        valorvencido = matricula.vencido_a_la_fechamatricula()
                        valorpendiente = matricula.total_saldo_rubrosinanular()
                    else:
                        valorgenerado = matricula.total_generado_alumno_retirado()
                        valorvencido = matricula.total_saldo_alumno_retirado()
                        valorpendiente = valorvencido

                    # Consulto el estado que voy a asignar
                    estado = obtener_estado_solicitud(1, 1)

                    # Creo la solicitud
                    solicitud = SolicitudRefinanciamientoPosgrado(persona=persona,
                                                                  matricula=matricula,
                                                                  costoprograma=costoprograma,
                                                                  descuento=valordescuento,
                                                                  totalprograma=valorgenerado,
                                                                  pagado=valorpagado,
                                                                  pendiente=valorpendiente,
                                                                  vencido=valorvencido,
                                                                  cantidadcuota=cuotasvencidas,
                                                                  motivo=motivo,
                                                                  otromotivo=form.cleaned_data['otromotivo'] if motivo == 5 else None,
                                                                  evidencia1=archivo1,
                                                                  evidencia2=archivo2,
                                                                  estado=estado)
                    solicitud.save(request)

                    # Creo el recorrido de la solicitud
                    recorrido = SolicitudRefinanciamientoPosgradoRecorrido(solicitud=solicitud,
                                                                   fecha=datetime.now().date(),
                                                                   observacion='SOLICITADO POR ALUMNO',
                                                                   estado=estado
                                                                   )
                    recorrido.save(request)

                    # Consulto los rubros de maestría ligados a la matrícula del maestrante
                    rubros = Rubro.objects.filter(status=True, matricula=matricula).order_by('fechavence')
                    for rubro in rubros:
                        fechapago = None
                        vencido = False

                        pagosrubro = rubro.pago_set.filter(status=True).order_by('-fecha')

                        if pagosrubro:
                            fechapago = pagosrubro[0].fecha

                        if not rubro.cancelado:
                            vencido = datetime.now().date() > rubro.fechavence

                        # Creo el detalle de rubro para la solicitud
                        detallesolicitud = SolicitudRefinanciamientoPosgradoDetalle(solicitud=solicitud,
                                                                                    rubro=rubro,
                                                                                    valor=rubro.valor,
                                                                                    fechaemite=rubro.fecha,
                                                                                    fechavence=rubro.fechavence,
                                                                                    fechapago=fechapago,
                                                                                    pagado=rubro.cancelado,
                                                                                    totalpagado=rubro.valor - rubro.saldo,
                                                                                    saldo=rubro.saldo,
                                                                                    vencido=vencido)
                        detallesolicitud.save(request)

                        # Bloqueo el rubro para que no se pueda editar ni eliminar en Módulo Finanzas
                        rubro.bloqueado = True
                        rubro.save(request)

                        # Bloquear rubros en epunemi
                        sql = """UPDATE sagest_rubro SET bloqueado=TRUE WHERE idrubrounemi=%s AND status=true""" % (rubro.id)
                        cnepunemi.execute(sql)

                    conexion.commit()
                    cnepunemi.close()
                    # Envio de e-mail de notificacion al solicitante
                    # listacuentascorreo = [23, 24, 25, 26, 27]
                    #posgrado1_unemi@unemi.edu.ec
                    #posgrado2_unemi@unemi.edu.ec
                    #posgrado3_unemi@unemi.edu.ec
                    #posgrado4_unemi@unemi.edu.ec
                    #posgrado5_unemi@unemi.edu.ec

                    listacuentascorreo = [18] # posgrado@unemi.edu.ec

                    fechaenvio = datetime.now().date()
                    horaenvio = datetime.now().time()
                    cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)
                    tituloemail = "Registro de Solicitud de Refinanciamiento de Deuda de Programas de Posgrado"
                    send_html_mail(tituloemail,
                                   "emails/notificacion_solicitud_refinanciamiento_posgrado.html",
                                   {'sistema': u'Posgrado UNEMI',
                                    'fecha': fechaenvio,
                                    'hora': horaenvio,
                                    'saludo': 'Estimada' if persona.sexo_id == 1 else 'Estimado',
                                    'estudiante': persona.nombre_completo_inverso(),
                                    'numero': solicitud.id,
                                    'destino': 'ESTUDIANTE',
                                    't': miinstitucion()
                                    },
                                   persona.lista_emails_envio(),
                                   # ['isaltosm@unemi.edu.ec'],
                                   [],
                                   cuenta=CUENTAS_CORREOS[cuenta][1]
                                   )

                    # Temporizador para evitar que se bloquee el servicio de gmail
                    pausaparaemail.sleep(2)

                    # Envío de e-mail de notificación a Posgrado
                    lista_email_posgrado = []

                    lista_email_posgrado.append('dmaciasv@unemi.edu.ec')
                    lista_email_posgrado.append('smendietac@unemi.edu.ec')

                    # lista_email_posgrado.append('ivan_saltos_medina@hotmail.com')
                    # lista_email_posgrado.append('ivan.saltos.medina@gmail.com')

                    cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)
                    tituloemail = "Registro de Solicitud de Refinanciamiento de Deuda de Programas de Posgrado"

                    send_html_mail(tituloemail,
                                   "emails/notificacion_solicitud_refinanciamiento_posgrado.html",
                                   {'sistema': u'Posgrado UNEMI',
                                    'fecha': fechaenvio,
                                    'hora': horaenvio,
                                    'saludo': 'Estimados',
                                    'estudiante': persona.nombre_completo_inverso(),
                                    'numero': solicitud.id,
                                    'destino': 'POSGRADO',
                                    't': miinstitucion()
                                    },
                                   lista_email_posgrado,
                                   [],
                                   cuenta=CUENTAS_CORREOS[cuenta][1]
                                   )
                    # Temporizador para evitar que se bloquee el servicio de gmail
                    pausaparaemail.sleep(2)

                    log(u'Adicionó solicitud de refinanciamiento de deuda de posgrado: %s' % solicitud, request, "add")

                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                conexion.rollback()
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

        elif action == 'aceptarrechazar':
            conexion = connections['epunemi']
            cnepunemi = conexion.cursor()
            try:
                if not 'idsolicitud' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                tipoaccion = request.POST['tipoaccion']

                # Consulto la solicitud
                solicitud = SolicitudRefinanciamientoPosgrado.objects.get(pk=int(encrypt(request.POST['idsolicitud'])))

                # Consulto el estado PROPUESTA ACEPTADA o RECHAZADA
                estado = obtener_estado_solicitud(1, 8) if tipoaccion == 'A' else obtener_estado_solicitud(1, 9)

                # Actualizo la solicitud
                if tipoaccion == 'A':
                    fechaactual = datetime.now().date()
                    fechapago = fechaactual + timedelta(days=5)  # 5 días de plazo
                    solicitud.fechavencepago = fechapago
                    solicitud.propuestaaceptada = True

                    # Consulto los rubros con estado pendiente de pago
                    rubrospendientes = solicitud.solicitudrefinanciamientoposgradodetalle_set.filter(status=True, pagado=False).order_by('rubro_id')

                    # Desbloquear los rubros en epunemi según el monto requerido para refinanciar. Esto es para que puedan cobrar en epunemi
                    sumasaldo = 0
                    for rubropendiente in rubrospendientes:
                        if sumasaldo < solicitud.pagorequerido:
                            sumasaldo += rubropendiente.saldo
                            sql = """UPDATE sagest_rubro SET bloqueado=FALSE WHERE idrubrounemi=%s AND status=true""" % (rubropendiente.rubro.id)
                            cnepunemi.execute(sql)
                        else:
                            break
                else:
                    # Desbloquear los rubros en epunemi para que puedan cobrar
                    for detalle in solicitud.solicitudrefinanciamientoposgradodetalle_set.filter(status=True):
                        sql = """UPDATE sagest_rubro SET bloqueado=FALSE WHERE idrubrounemi=%s AND status=true""" % (detalle.rubro.id)
                        cnepunemi.execute(sql)

                solicitud.estado = estado
                solicitud.save(request)

                # Agrego recorrido de la solicitud
                recorrido = SolicitudRefinanciamientoPosgradoRecorrido(solicitud=solicitud,
                                                                       fecha=datetime.now().date(),
                                                                       observacion='PROPUESTA ACEPTADA POR ALUMNO' if tipoaccion == 'A' else 'PROPUESTA RECHAZADA POR ALUMNO',
                                                                       estado=estado
                                                                       )
                recorrido.save(request)

                conexion.commit()
                cnepunemi.close()

                # Envio de email de notificación al solicitante
                # listacuentascorreo = [23, 24, 25, 26, 27]
                # posgrado1_unemi@unemi.edu.ec
                # posgrado2_unemi@unemi.edu.ec
                # posgrado3_unemi@unemi.edu.ec
                # posgrado4_unemi@unemi.edu.ec
                # posgrado5_unemi@unemi.edu.ec

                listacuentascorreo = [18]  # posgrado@unemi.edu.ec

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                if tipoaccion == 'A':
                    tituloemail = "Propuesta de Refinanciamiento de Deuda de Programas de Posgrado - ACEPTADA"
                else:
                    tituloemail = "Propuesta de Refinanciamiento de Deuda de Programas de Posgrado - RECHAZADA"

                send_html_mail(tituloemail,
                               "emails/notificacion_estado_refinanciamiento_posgrado.html",
                               {'sistema': u'Posgrado UNEMI',
                                'fecha': fechaenvio,
                                'hora': horaenvio,
                                'saludo': 'Estimada' if persona.sexo_id == 1 else 'Estimado',
                                'estudiante': persona.nombre_completo_inverso(),
                                'numero': solicitud.id,
                                'estado': estado.valor,
                                'pagorequerido': solicitud.pagorequerido,
                                'observaciones': '',
                                't': miinstitucion()
                                },
                               persona.lista_emails_envio(),
                               # ['isaltosm@unemi.edu.ec'],
                               [],
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                # Temporizador para evitar que se bloquee el servicio de gmail
                pausaparaemail.sleep(2)

                # Envío de e-mail de notificación a Posgrado
                lista_email_posgrado = []

                lista_email_posgrado.append('dmaciasv@unemi.edu.ec')
                lista_email_posgrado.append('smendietac@unemi.edu.ec')

                # lista_email_posgrado.append('ivan_saltos_medina@hotmail.com')
                # lista_email_posgrado.append('ivan.saltos.medina@gmail.com')

                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                send_html_mail(tituloemail,
                               "emails/notificacion_solicitud_refinanciamiento_posgrado.html",
                               {'sistema': u'Posgrado UNEMI',
                                'fecha': fechaenvio,
                                'hora': horaenvio,
                                'saludo': 'Estimados',
                                'estudiante': persona.nombre_completo_inverso(),
                                'numero': solicitud.id,
                                'destino': 'PROPUESTA',
                                'tipoaccion': 'ACEPTÓ' if tipoaccion == 'A' else 'RECHAZÓ',
                                't': miinstitucion()
                                },
                               lista_email_posgrado,
                               [],
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )
                # Temporizador para evitar que se bloquee el servicio de gmail
                pausaparaemail.sleep(2)

                if tipoaccion == 'A':
                    log(u'Aceptó propuesta de refinanciamiento de deuda de posgrado: %s  - %s - %s' % (persona, solicitud, estado.descripcion), request, "edit")
                else:
                    log(u'Rechazó propuesta de refinanciamiento de deuda de posgrado: %s  - %s - %s' % (persona, solicitud, estado.descripcion), request, "edit")

                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                conexion.rollback()
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'subirjustificativo':
            try:
                # Consulto la solicitud
                solicitud = SolicitudRefinanciamientoPosgrado.objects.get(pk=int(encrypt(request.POST['id'])))

                mensaje = u"Debe seleccionar el archivo" if solicitud.motivo != 2 else u"Debe seleccionar al menos un archivo"

                if 'archivocertmedico' not in request.FILES and 'archivoculmilaboral' not in request.FILES and 'archivoafiliaseguro' not in request.FILES and 'archivoactadefun' not in request.FILES and 'archivocertmedicofam' not in request.FILES and 'archivootro' not in request.FILES:
                    return JsonResponse({"result": "bad", "mensaje": mensaje})


                if 'archivocertmedico' in request.FILES:
                    descripcionarchivo = 'Certificado Médico'
                    resp = validar_archivo(descripcionarchivo, request.FILES['archivocertmedico'], ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                if 'archivoculmilaboral' in request.FILES:
                    descripcionarchivo = 'Certificado Culminación Relación Laboral'
                    resp = validar_archivo(descripcionarchivo, request.FILES['archivoculmilaboral'], ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                if 'archivoafiliaseguro' in request.FILES:
                    descripcionarchivo = 'Certificado Afiliación Seguro'
                    resp = validar_archivo(descripcionarchivo, request.FILES['archivoafiliaseguro'], ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                if 'archivoactadefun' in request.FILES:
                    descripcionarchivo = 'Acta de Defunción'
                    resp = validar_archivo(descripcionarchivo, request.FILES['archivoactadefun'], ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                if 'archivocertmedicofam' in request.FILES:
                    descripcionarchivo = 'Certificado Médico'
                    resp = validar_archivo(descripcionarchivo, request.FILES['archivocertmedicofam'], ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                if 'archivootro' in request.FILES:
                    descripcionarchivo = 'Justificativo'
                    resp = validar_archivo(descripcionarchivo, request.FILES['archivootro'], ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                f = RefinanciamientoPosgradoSubirJustificativoForm(request.POST, request.FILES)

                if f.is_valid():
                    archivo1 = archivo2 = None

                    # Consulto el estado JUSTIFICATIVOS CARGADOS
                    estado = obtener_estado_solicitud(1, 6)

                    if solicitud.motivo == 1:
                        archivo1 = request.FILES['archivocertmedico']
                        archivo1._name = generar_nombre("certmedicoalumno", archivo1._name)
                    elif solicitud.motivo == 2:
                        if 'archivoculmilaboral' in request.FILES:
                            archivo1 = request.FILES['archivoculmilaboral']
                            archivo1._name = generar_nombre("certculmlaboralalumno", archivo1._name)

                        if 'archivoafiliaseguro' in request.FILES:
                            archivo2 = request.FILES['archivoafiliaseguro']
                            archivo2._name = generar_nombre("certafiliaseguroalumno", archivo2._name)

                    elif solicitud.motivo == 3:
                        archivo1 = request.FILES['archivoactadefun']
                        archivo1._name = generar_nombre("actadefunfamiliaralumno", archivo1._name)
                    elif solicitud.motivo == 4:
                        archivo1 = request.FILES['archivocertmedicofam']
                        archivo1._name = generar_nombre("certmedicofamiliaralumno", archivo1._name)
                    else:
                        archivo1 = request.FILES['archivootro']
                        archivo1._name = generar_nombre("justificativoalumno", archivo1._name)

                    if archivo1:
                        solicitud.evidencia1 = archivo1
                    if archivo2:
                        solicitud.evidencia2 = archivo2

                    solicitud.observacion = ""
                    solicitud.personarevisa = None
                    solicitud.estado = estado
                    solicitud.save(request)

                    # Creo el recorrido de la solicitud
                    recorrido = SolicitudRefinanciamientoPosgradoRecorrido(solicitud=solicitud,
                                                                           fecha=datetime.now().date(),
                                                                           observacion='JUSTIFICATIVOS CARGADOS',
                                                                           estado=estado
                                                                           )
                    recorrido.save(request)

                    # Envio de e-mail de notificacion al solicitante
                    # listacuentascorreo = [23, 24, 25, 26, 27]
                    # posgrado1_unemi@unemi.edu.ec
                    # posgrado2_unemi@unemi.edu.ec
                    # posgrado3_unemi@unemi.edu.ec
                    # posgrado4_unemi@unemi.edu.ec
                    # posgrado5_unemi@unemi.edu.ec

                    listacuentascorreo = [18]  # posgrado@unemi.edu.ec

                    fechaenvio = datetime.now().date()
                    horaenvio = datetime.now().time()
                    cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)
                    tituloemail = "Carga de Justificativos - Registro de Solicitud de Refinanciamiento de Deuda de Programas de Posgrado"

                    send_html_mail(tituloemail,
                                   "emails/notificacion_estado_refinanciamiento_posgrado.html",
                                   {'sistema': u'Posgrado UNEMI',
                                    'fecha': fechaenvio,
                                    'hora': horaenvio,
                                    'saludo': 'Estimada' if persona.sexo_id == 1 else 'Estimado',
                                    'estudiante': persona.nombre_completo_inverso(),
                                    'numero': solicitud.id,
                                    'estado': estado.valor,
                                    'observaciones': '',
                                    't': miinstitucion()
                                    },
                                   persona.lista_emails_envio(),
                                   # ['isaltosm@unemi.edu.ec'],
                                   [],
                                   cuenta=CUENTAS_CORREOS[cuenta][1]
                                   )

                    # Temporizador para evitar que se bloquee el servicio de gmail
                    pausaparaemail.sleep(2)

                    # Envío de e-mail de notificación a Posgrado
                    lista_email_posgrado = []

                    lista_email_posgrado.append('dmaciasv@unemi.edu.ec')
                    lista_email_posgrado.append('smendietac@unemi.edu.ec')

                    # lista_email_posgrado.append('ivan_saltos_medina@hotmail.com')
                    # lista_email_posgrado.append('ivan.saltos.medina@gmail.com')

                    cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                    send_html_mail(tituloemail,
                                   "emails/notificacion_solicitud_refinanciamiento_posgrado.html",
                                   {'sistema': u'Posgrado UNEMI',
                                    'fecha': fechaenvio,
                                    'hora': horaenvio,
                                    'saludo': 'Estimados',
                                    'estudiante': persona.nombre_completo_inverso(),
                                    'numero': solicitud.id,
                                    'destino': 'JUSTIFICATIVOS',
                                    't': miinstitucion()
                                    },
                                   lista_email_posgrado,
                                   [],
                                   cuenta=CUENTAS_CORREOS[cuenta][1]
                                   )
                    # Temporizador para evitar que se bloquee el servicio de gmail
                    pausaparaemail.sleep(2)

                    log(u'Actualizó justificativos de la solicitud de refinanciamiento %s - %s' % (persona, solicitud), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

        elif action == 'subircomprobantepago':
            # conexión a base de datos EPUNEMI
            # conexion = connections['epunemi']
            # cnepunemi = conexion.cursor()
            try:
                # Consulto la solicitud
                solicitud = SolicitudRefinanciamientoPosgrado.objects.get(pk=int(encrypt(request.POST['id'])))

                if solicitud.estado.valor == 11:
                    return JsonResponse({"result": "bad", "mensaje": u"No se puede cargar el comprobante debido a que ya se asignó estado PAGO VALIDADO."})

                if 'comprobantepago' in request.FILES:
                    descripcionarchivo = 'Comprobante de Pago'
                    resp = validar_archivo(descripcionarchivo, request.FILES['comprobantepago'], ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                f = RefinanciamientoPosgradoSubirComprobantePagoForm(request.POST, request.FILES)

                if f.is_valid():
                    # # Consulto el estado REFINANCIADO
                    # estado = obtener_estado_solicitud(1, 15)

                    archivo = request.FILES['comprobantepago']
                    archivo._name = generar_nombre("comprobantepago", archivo._name)

                    solicitud.comprobantepago = archivo
                    solicitud.observacion = ""
                    # solicitud.estado = estado
                    solicitud.save(request)

                    # # Creo el recorrido de la solicitud
                    # recorrido = SolicitudRefinanciamientoPosgradoRecorrido(solicitud=solicitud,
                    #                                                        fecha=datetime.now().date(),
                    #                                                        observacion='REFINANCIAMIENTO GENERADO AUTOMÁTICAMENTE',
                    #                                                        estado=estado
                    #                                                        )
                    # recorrido.save()

                    # Generar la tabla de amortización por refinanciamiento en caso de no haber sido generados por primera vez

                    # if not solicitud.rubrosgenerados:
                    # Si no existe el compromiso de pago lo debo crear
                    if not CompromisoPagoPosgrado.objects.filter(matricula=solicitud.matricula, status=True, vigente=True, tipo=2).exists():
                        # Consulto el estado Compromiso Generado
                        estado = obtener_estado_solicitud(2, 1)
                        compromisopago = CompromisoPagoPosgrado(matricula=solicitud.matricula,
                                                                fecha=datetime.now().date(),
                                                                tipo=2,
                                                                vigente=True,
                                                                archivocomprobante=archivo,
                                                                estadocomprobante=1,
                                                                solicitudrefinanciamiento=solicitud,
                                                                estado=estado)
                        compromisopago.save(request)

                        # Creo el recorrido del compromiso de pago
                        recorrido = CompromisoPagoPosgradoRecorrido(compromisopago=compromisopago,
                                                                    fecha=datetime.now().date(),
                                                                    observacion='COMPROMISO DE PAGO GENERADO',
                                                                    estado=estado
                                                                    )
                        recorrido.save(request)

                            # rubromaestria = Rubro.objects.filter(status=True, matricula=solicitud.matricula).order_by('-fechavence')[0].tipo
                            #
                            # # Consulto los rubros de la tabla amortizacion original para guardarlos en el compromiso por refinanciamiento
                            # rubros = Rubro.objects.filter(status=True, matricula=solicitud.matricula).order_by('fechavence')
                            # for rubro in rubros:
                            #     fechapago = None
                            #     vencido = False
                            #
                            #     pagosrubro = rubro.pago_set.filter(status=True).order_by('-fecha')
                            #
                            #     if pagosrubro:
                            #         fechapago = pagosrubro[0].fecha
                            #
                            #     if not rubro.cancelado:
                            #         vencido = datetime.now().date() > rubro.fechavence
                            #
                            #     rubrocompromiso = RubroRefinanciamiento(compromisopago=compromisopago,
                            #                                             rubro=rubro,
                            #                                             valor=rubro.valor,
                            #                                             fechaemite=rubro.fecha,
                            #                                             fechavence=rubro.fechavence,
                            #                                             saldo=rubro.saldo,
                            #                                             vencido=vencido,
                            #                                             cancelado=rubro.cancelado)
                            #     rubrocompromiso.save(request)
                            #
                            # # Los rubros no cancelados y que no tengan pagos se inactivan y se coloca estado refinanciado True
                            # for rubro in rubros.filter(cancelado=False):
                            #     pagosrubro = rubro.pago_set.filter(status=True).order_by('-fecha')
                            #     if not pagosrubro:
                            #         rubro.refinanciado = True
                            #         rubro.status = False
                            #         rubro.observacion = "REFINANCIADO POSGRADO"
                            #         rubro.save(request)
                            #
                            #         # Actualizar en base de epunemi
                            #         sql = """UPDATE sagest_rubro SET status=FALSE, refinanciado=TRUE, observacion = 'REFINANCIADO POSGRADO' WHERE idrubrounemi=%s AND status=true""" % (rubro.id)
                            #         cnepunemi.execute(sql)
                            #
                            # # Consulto los rubros con saldo
                            # rubrosconsaldo = Rubro.objects.filter(status=True, matricula=solicitud.matricula, saldo__gt=0).order_by('fechavence')
                            # for rubrosaldo in rubrosconsaldo:
                            #     pagosrubro = rubrosaldo.pago_set.filter(status=True).order_by('-fecha')
                            #     # si tiene pagos actualizo el valor del rubro que seria valor original - saldo
                            #     if pagosrubro:
                            #         rubrosaldo.valor = rubrosaldo.valor - rubrosaldo.saldo
                            #         rubrosaldo.cancelado = True
                            #         rubrosaldo.refinanciado = True
                            #         rubrosaldo.observacion = ""
                            #         rubrosaldo.save(request)
                            #
                            #         # Hacer la misma actalizacion en EPUNEMI
                            #         sql = """UPDATE sagest_rubro SET valor=valor-saldo, cancelado=TRUE, refinanciado=TRUE, observacion = '' WHERE idrubrounemi=%s AND status=true""" % (rubro.id)
                            #         cnepunemi.execute(sql)
                            #
                            # # Consulto la persona por cedula en base de epunemi
                            # cedula = solicitud.matricula.inscripcion.persona.cedula
                            #
                            # sql = """SELECT pe.id FROM sga_persona AS pe WHERE pe.cedula='%s' AND pe.status=TRUE;  """ % (cedula)
                            # cnepunemi.execute(sql)
                            # registro = cnepunemi.fetchone()
                            # codigoalumno = registro[0]
                            #
                            # #  Se crean los nuevos rubros según la propuesta aceptada
                            # propuesta = solicitud.solicitudrefinanciamientoposgradopropuesta_set.filter(status=True).order_by('id')
                            # for cuota in propuesta:
                            #     nuevorubro = Rubro(fecha=datetime.now().date(),
                            #                        valor=cuota.valorcuota,
                            #                        valortotal=cuota.valorcuota,
                            #                        saldo=cuota.valorcuota,
                            #                        persona=solicitud.matricula.inscripcion.persona,
                            #                        matricula=solicitud.matricula,
                            #                        nombre=rubromaestria.nombre,
                            #                        tipo=rubromaestria,
                            #                        cancelado=False,
                            #                        observacion='',
                            #                        iva_id=1,
                            #                        epunemi=True,
                            #                        fechavence=cuota.fechacuota,
                            #                        compromisopago=compromisopago,
                            #                        bloqueado=True
                            #                        )
                            #     nuevorubro.save(request)
                            #
                            #     # Consulto el tipo otro rubro en epunemi
                            #     sql = """SELECT id FROM sagest_tipootrorubro WHERE idtipootrorubrounemi=%s; """ % (rubromaestria.id)
                            #     cnepunemi.execute(sql)
                            #     registro = cnepunemi.fetchone()
                            #
                            #     # Si existe
                            #     if registro is not None:
                            #         tipootrorubro = registro[0]
                            #     else:
                            #         # Debo crear ese tipo de rubro
                            #         # Consulto centro de costo
                            #         sql = """SELECT id FROM sagest_centrocosto WHERE status=True AND unemi=True AND tipo=%s;""" % (rubromaestria.tiporubro)
                            #         cnepunemi.execute(sql)
                            #         centrocosto = cnepunemi.fetchone()
                            #         idcentrocosto = centrocosto[0]
                            #
                            #         # Consulto la cuenta contable
                            #         cuentacontable = CuentaContable.objects.get(partida=rubromaestria.partida, status=True)
                            #
                            #         # Creo el tipo de rubro en epunemi
                            #         sql = """ Insert Into sagest_tipootrorubro (status, nombre, partida_id, valor, interface, activo, ivaaplicado_id, nofactura, exportabanco, cuentacontable_id, centrocosto_id, tiporubro, idtipootrorubrounemi, unemi)
                            # VALUES(TRUE, '%s', %s, %s, FALSE, TRUE, %s, FALSE, TRUE, %s, %s, 1, %s, TRUE); """ % (
                            #         rubromaestria.nombre, cuentacontable.partida.id, rubromaestria.valor,
                            #         rubromaestria.ivaaplicado.id, cuentacontable.id, idcentrocosto, rubromaestria.id)
                            #         cnepunemi.execute(sql)
                            #
                            #     # Insertar en base de datos epunemi
                            #     sql = """ INSERT INTO sagest_rubro (status, usuario_creacion_id, fecha_creacion, cuota, tipocuota, valoriva, tienenotacredito, valornotacredito, valordescuento, anulado, fecha, valor ,valortotal, saldo, persona_id, nombre, tipo_id, cancelado, observacion, iva_id, idrubrounemi, totalunemi, fechavence, compromisopago, bloqueado, refinanciado)
                            #                                       VALUES (TRUE, 1, NOW(), 0, 3, 0, FALSE, 0, 0, FALSE, NOW(),                   %s, %s,    %s, %s,     '%s', %s,   FALSE,    '',              1,   %s,        %s,     '/%s/',   %s, FALSE, FALSE); """ \
                            #           % (cuota.valorcuota, cuota.valorcuota, cuota.valorcuota, codigoalumno,
                            #              rubromaestria.nombre, tipootrorubro, nuevorubro.id, cuota.valorcuota,
                            #              cuota.fechacuota, compromisopago.id)
                            #     cnepunemi.execute(sql)
                            #
                            # solicitud.rubrosgenerados = True
                            # solicitud.save(request)
                            #

                    # conexion.commit()
                    # cnepunemi.close()
                    # Envio de e-mail de notificacion al solicitante
                    # listacuentascorreo = [23, 24, 25, 26, 27]
                    # posgrado1_unemi@unemi.edu.ec
                    # posgrado2_unemi@unemi.edu.ec
                    # posgrado3_unemi@unemi.edu.ec
                    # posgrado4_unemi@unemi.edu.ec
                    # posgrado5_unemi@unemi.edu.ec

                    listacuentascorreo = [18]  # posgrado@unemi.edu.ec

                    fechaenvio = datetime.now().date()
                    horaenvio = datetime.now().time()
                    cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)
                    tituloemail = "Carga de Comprobante de Pago - Refinanciamiento de Deuda de Programas de Posgrado"

                    send_html_mail(tituloemail,
                                   "emails/notificacion_estado_refinanciamiento_posgrado.html",
                                   {'sistema': u'Posgrado UNEMI',
                                    'fecha': fechaenvio,
                                    'hora': horaenvio,
                                    'saludo': 'Estimada' if persona.sexo_id == 1 else 'Estimado',
                                    'estudiante': persona.nombre_completo_inverso(),
                                    'numero': solicitud.id,
                                    'estado': estado.valor,
                                    'observaciones': '',
                                    't': miinstitucion()
                                    },
                                   persona.lista_emails_envio(),
                                   # ['isaltosm@unemi.edu.ec'],
                                   [],
                                   cuenta=CUENTAS_CORREOS[cuenta][1]
                                   )

                    # Temporizador para evitar que se bloquee el servicio de gmail
                    pausaparaemail.sleep(2)

                    # # Envío de e-mail de notificación a Posgrado
                    # lista_email_posgrado = []
                    #
                    # lista_email_posgrado.append('dmaciasv@unemi.edu.ec')
                    # lista_email_posgrado.append('smendietac@unemi.edu.ec')
                    #
                    # # lista_email_posgrado.append('ivan_saltos_medina@hotmail.com')
                    # # lista_email_posgrado.append('ivan.saltos.medina@gmail.com')
                    #
                    # cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)
                    #
                    # send_html_mail(tituloemail,
                    #                "emails/notificacion_solicitud_refinanciamiento_posgrado.html",
                    #                {'sistema': u'Posgrado UNEMI',
                    #                 'fecha': fechaenvio,
                    #                 'hora': horaenvio,
                    #                 'saludo': 'Estimados',
                    #                 'estudiante': persona.nombre_completo_inverso(),
                    #                 'numero': solicitud.id,
                    #                 'destino': 'COMPROBANTEPAGO',
                    #                 't': miinstitucion()
                    #                 },
                    #                lista_email_posgrado,
                    #                [],
                    #                cuenta=CUENTAS_CORREOS[cuenta][1]
                    #                )
                    # # Temporizador para evitar que se bloquee el servicio de gmail
                    # pausaparaemail.sleep(2)

                    log(u'Cargó comprobante de pago de la solicitud de refinanciamiento %s - %s' % (persona, solicitud), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                # conexion.rollback()
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

        elif action == 'editsolicitud':
            try:
                form = SolicitudRefinanciamientoPosgradoForm(request.POST, request.FILES)
                solicitud = SolicitudRefinanciamientoPosgrado.objects.get(pk=int(encrypt(request.POST['id'])))

                if solicitud.estado.valor == 2:
                    return JsonResponse({"result": "bad", "mensaje": "No se puede editar la solicitud debido a que tiene estado REVISADA."})

                if 'archivocertmedico' in request.FILES:
                    descripcionarchivo = 'Certificado Médico'
                    resp = validar_archivo(descripcionarchivo, request.FILES['archivocertmedico'], ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                if 'archivoculmilaboral' in request.FILES:
                    descripcionarchivo = 'Certificado Culminación Relación Laboral'
                    resp = validar_archivo(descripcionarchivo, request.FILES['archivoculmilaboral'], ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                if 'archivoafiliaseguro' in request.FILES:
                    descripcionarchivo = 'Certificado Afiliación Seguro'
                    resp = validar_archivo(descripcionarchivo, request.FILES['archivoafiliaseguro'], ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                if 'archivoactadefun' in request.FILES:
                    descripcionarchivo = 'Acta de Defunción'
                    resp = validar_archivo(descripcionarchivo, request.FILES['archivoactadefun'], ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                if 'archivocertmedicofam' in request.FILES:
                    descripcionarchivo = 'Certificado Médico'
                    resp = validar_archivo(descripcionarchivo, request.FILES['archivocertmedicofam'], ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                if 'archivootro' in request.FILES:
                    descripcionarchivo = 'Justificativo'
                    resp = validar_archivo(descripcionarchivo, request.FILES['archivootro'], ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                if 'archivosueldo' in request.FILES:
                    descripcionarchivo = 'Certificado / Rol de Pago'
                    resp = validar_archivo(descripcionarchivo, request.FILES['archivosueldo'], ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                if form.is_valid():
                    # Consulto el estado SOLICITUD ACTUALIZADA JUSTIFICATIVOS CARGADOS
                    estado = obtener_estado_solicitud(1, 6)

                    motivo = int(form.cleaned_data['motivo'])
                    archivo1 = archivo2 = None
                    if motivo == 1:
                        archivo1 = request.FILES['archivocertmedico']
                        archivo1._name = generar_nombre("certmedicoalumno", archivo1._name)
                    elif motivo == 2:
                        archivo1 = request.FILES['archivoculmilaboral']
                        archivo1._name = generar_nombre("certculmlaboralalumno", archivo1._name)
                        archivo2 = request.FILES['archivoafiliaseguro']
                        archivo2._name = generar_nombre("certafiliaseguroalumno", archivo2._name)
                    elif motivo == 3:
                        archivo1 = request.FILES['archivoactadefun']
                        archivo1._name = generar_nombre("actadefunfamiliaralumno", archivo1._name)
                    elif motivo == 4:
                        archivo1 = request.FILES['archivocertmedicofam']
                        archivo1._name = generar_nombre("certmedicofamiliaralumno", archivo1._name)
                    elif motivo == 6:
                        archivo1 = request.FILES['archivosueldo']
                        archivo1._name = generar_nombre("certsueldorolpago", archivo1._name)
                    else:
                        archivo1 = request.FILES['archivootro']
                        archivo1._name = generar_nombre("justificativoalumno", archivo1._name)

                    solicitud.motivo = motivo
                    solicitud.otromotivo = form.cleaned_data['otromotivo'] if motivo == 5 else None

                    if archivo1:
                        solicitud.evidencia1 = archivo1
                    if archivo2:
                        solicitud.evidencia2 = archivo2

                    solicitud.observacion = ''
                    solicitud.estado = estado
                    solicitud.save(request)

                    # Creo el recorrido de la solicitud
                    recorrido = SolicitudRefinanciamientoPosgradoRecorrido(solicitud=solicitud,
                                                                           fecha=datetime.now().date(),
                                                                           observacion='SOLICITUD ACTUALIZADA/JUSTIFICATIVOS CARGADOS',
                                                                           estado=estado
                                                                           )
                    recorrido.save(request)

                    # Envio de e-mail de notificacion al solicitante
                    # listacuentascorreo = [23, 24, 25, 26, 27]
                    # posgrado1_unemi@unemi.edu.ec
                    # posgrado2_unemi@unemi.edu.ec
                    # posgrado3_unemi@unemi.edu.ec
                    # posgrado4_unemi@unemi.edu.ec
                    # posgrado5_unemi@unemi.edu.ec

                    listacuentascorreo = [18]  # posgrado@unemi.edu.ec

                    fechaenvio = datetime.now().date()
                    horaenvio = datetime.now().time()
                    cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)
                    tituloemail = "Actualización de Solicitud de Refinanciamiento de Deuda de Programas de Posgrado"

                    send_html_mail(tituloemail,
                                   "emails/notificacion_estado_refinanciamiento_posgrado.html",
                                   {'sistema': u'Posgrado UNEMI',
                                    'fecha': fechaenvio,
                                    'hora': horaenvio,
                                    'saludo': 'Estimada' if persona.sexo_id == 1 else 'Estimado',
                                    'estudiante': persona.nombre_completo_inverso(),
                                    'numero': solicitud.id,
                                    'estado': estado.valor,
                                    'observaciones': '',
                                    't': miinstitucion()
                                    },
                                   persona.lista_emails_envio(),
                                   # ['isaltosm@unemi.edu.ec'],
                                   [],
                                   cuenta=CUENTAS_CORREOS[cuenta][1]
                                   )

                    # Temporizador para evitar que se bloquee el servicio de gmail
                    pausaparaemail.sleep(2)

                    # Envío de e-mail de notificación a Posgrado
                    lista_email_posgrado = []

                    lista_email_posgrado.append('dmaciasv@unemi.edu.ec')
                    lista_email_posgrado.append('smendietac@unemi.edu.ec')

                    # lista_email_posgrado.append('ivan_saltos_medina@hotmail.com')
                    # lista_email_posgrado.append('ivan.saltos.medina@gmail.com')

                    cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                    send_html_mail(tituloemail,
                                   "emails/notificacion_solicitud_refinanciamiento_posgrado.html",
                                   {'sistema': u'Posgrado UNEMI',
                                    'fecha': fechaenvio,
                                    'hora': horaenvio,
                                    'saludo': 'Estimados',
                                    'estudiante': persona.nombre_completo_inverso(),
                                    'numero': solicitud.id,
                                    'destino': 'JUSTIFICATIVOS',
                                    't': miinstitucion()
                                    },
                                   lista_email_posgrado,
                                   [],
                                   cuenta=CUENTAS_CORREOS[cuenta][1]
                                   )
                    # Temporizador para evitar que se bloquee el servicio de gmail
                    pausaparaemail.sleep(2)

                    log(u'Editó solicitud de refinanciamiento de deudas de posgrado: %s' % solicitud, request, "edit")

                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

        elif action == 'delsolicitud':
            try:
                solicitud = SolicitudDevolucionDinero.objects.get(pk=request.POST['id'])
                solicitud.status = False
                solicitud.save(request)

                cuentabancaria = solicitud.persona.cuentabancaria()
                if cuentabancaria.estadorevision != 2:
                    cuentabancaria.status = False
                    cuentabancaria.save(request)

                log(u'Eliminó solicitud de devolución: %s [%s]' % (solicitud, solicitud.id), request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos. Detalle: %s" % (msg)})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'mostrarpropuesta':
                try:
                    data['title'] = u'Aceptar/Rechazar Propuesta de Refinanciamiento de Deudas de Posgrado'
                    data['id'] = idsol = int(encrypt(request.GET['id']))
                    data['solicitud'] = solicitud = SolicitudRefinanciamientoPosgrado.objects.get(pk=idsol)
                    data['detallecuotas'] = detalle = solicitud.solicitudrefinanciamientoposgradopropuesta_set.filter(status=True).order_by('numerocuota')
                    data['totalcuotas'] = detalle.count()

                    template = get_template("alu_refinanciamientoposgrado/mostrarpropuesta.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'mostrartablarefinanciamiento':
                try:
                    data = {}
                    data['solicitud'] = solicitud = SolicitudRefinanciamientoPosgrado.objects.get(pk=int(encrypt(request.GET['id'])))
                    compromisopago = CompromisoPagoPosgrado.objects.get(solicitudrefinanciamiento=solicitud)
                    data['rubros'] = Rubro.objects.filter(status=True, compromisopago=compromisopago).order_by('fechavence')

                    template = get_template("alu_refinanciamientoposgrado/tablarefinanciamiento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'mostrardocumentos':
                try:
                    data = {}
                    solicitud = SolicitudRefinanciamientoPosgrado.objects.get(pk=int(encrypt(request.GET['id'])))
                    documentos = []

                    if solicitud.motivo == 1:
                        documentos.append(['Certificado Médico', solicitud.evidencia1.url])
                    elif solicitud.motivo == 2:
                        documentos.append(['Certificado Culminación Relación Laboral', solicitud.evidencia1.url])
                        documentos.append(['Certificado Afiliación Seguro', solicitud.evidencia2.url])
                    elif solicitud.motivo == 3:
                        documentos.append(['Acta de Defunción del Familiar', solicitud.evidencia1.url])
                    elif solicitud.motivo == 4:
                        documentos.append(['Certificado Médico del Familiar', solicitud.evidencia1.url])
                    elif solicitud.motivo == 6:
                        documentos.append(['Certificado / Rol de Pago', solicitud.evidencia1.url])
                    else:
                        documentos.append(['Justificativo', solicitud.evidencia1.url])

                    if solicitud.comprobantepago:
                        documentos.append(['Comprobante de Pago', solicitud.comprobantepago.url])

                    data['documentos'] = documentos
                    data['solicitud'] = solicitud

                    template = get_template("alu_refinanciamientoposgrado/mostrardocumentos.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'subirjustificativo':
                try:
                    form = RefinanciamientoPosgradoSubirJustificativoForm()
                    data['title'] = u'Subir Justificativos de la Solicitud'

                    motivo = SolicitudRefinanciamientoPosgrado.objects.get(pk=int(encrypt(request.GET['id']))).motivo

                    data['id'] = request.GET['id']
                    data['form'] = form
                    data['motivo'] = motivo

                    template = get_template("alu_refinanciamientoposgrado/subirjustificativo.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'subircomprobantepago':
                try:
                    form = RefinanciamientoPosgradoSubirComprobantePagoForm()
                    data['title'] = u'Subir Comprobante de Pago'

                    pagorequerido = SolicitudRefinanciamientoPosgrado.objects.get(pk=int(encrypt(request.GET['id']))).pagorequerido

                    data['id'] = request.GET['id']
                    data['form'] = form
                    data['pagorequerido'] = pagorequerido
                    data['saludo'] = 'Estimada' if persona.sexo_id == 1 else 'Estimado'

                    template = get_template("alu_refinanciamientoposgrado/subircomprobantepago.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass



            if action == 'addsolicitud':
                try:
                    data['title'] = u'Agregar Solicitud de Refinanciamiento de Deudas Posgrado'

                    # Consulto los total del alumno
                    valorpagado = matricula.total_pagado_alumno()
                    cuotasvencidas = matricula.numero_cuotas_vencidas()
                    descuento = matricula.tiene_descuento_posgrado()
                    if descuento:
                        valordescuento = descuento.valordescuento
                    else:
                        valordescuento = 0

                    if not matricula.retiradomatricula:
                        valorgenerado = matricula.total_generado_alumno()
                        valorvencido = matricula.vencido_a_la_fechamatricula()
                        valorpendiente = matricula.total_saldo_rubrosinanular()
                    else:
                        valorgenerado = matricula.total_generado_alumno_retirado()
                        valorvencido = matricula.total_saldo_alumno_retirado()
                        valorpendiente = valorvencido

                    form = SolicitudRefinanciamientoPosgradoForm(initial={
                        'alumno': matricula.inscripcion.persona.nombre_completo_inverso(),
                        'cohorte': matricula.nivel.periodo.nombre,
                        'programa': matricula.inscripcion.carrera.nombre,
                        'costoprograma': matricula.costo_programa(),
                        'descuento': valordescuento,
                        'totalprograma': valorgenerado,
                        'totalpagado': valorpagado,
                        'totalpendiente': valorpendiente,
                        'totalvencido': valorvencido,
                        'cantidadcuota': cuotasvencidas,
                        'totalrefinancia': valorpendiente
                    })


                    data['form'] = form
                    # data['detallepropuesta'] = detallepropuesta
                    return render(request, "alu_refinanciamientoposgrado/addsolicitud.html", data)
                except Exception as ex:
                    pass

            elif action == 'mostrarrecorrido':
                try:
                    data = {}
                    data['solicitud'] = solicitud = SolicitudRefinanciamientoPosgrado.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['recorrido'] = solicitud.solicitudrefinanciamientoposgradorecorrido_set.filter(status=True).order_by('id')
                    template = get_template("alu_refinanciamientoposgrado/recorridosolicitud.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'editsolicitud':
                try:
                    data['title'] = u'Editar Solicitud de Refinanciamiento de Deudas Posgrado'

                    solicitud = SolicitudRefinanciamientoPosgrado.objects.get(pk=int(encrypt(request.GET['id'])))

                    form = SolicitudRefinanciamientoPosgradoForm(initial={
                        'alumno': solicitud.matricula.inscripcion.persona.nombre_completo_inverso(),
                        'cohorte': solicitud.matricula.nivel.periodo.nombre,
                        'programa': solicitud.matricula.inscripcion.carrera.nombre,
                        'costoprograma': solicitud.costoprograma,
                        'descuento': solicitud.descuento,
                        'totalprograma': solicitud.totalprograma,
                        'totalpagado': solicitud.pagado,
                        'totalpendiente': solicitud.pendiente,
                        'totalvencido': solicitud.vencido,
                        'cantidadcuota': solicitud.cantidadcuota,
                        'totalrefinancia': solicitud.pendiente,
                        'motivo': solicitud.motivo
                    })

                    data['idsolicitud'] = request.GET['id']

                    data['form'] = form
                    return render(request, "alu_refinanciamientoposgrado/editsolicitud.html", data)
                except Exception as ex:
                    pass

            elif action == 'delsolicitud':
                try:
                    data['title'] = u'Eliminar Solicitud'
                    data['solicitud'] = solicitud = SolicitudDevolucionDinero.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "alu_devoluciondinero/deletesolicitud.html", data)
                except Exception as ex:
                    pass


            return HttpResponseRedirect(request.path)
        else:
            conexion = connections['epunemi']
            cnepunemi = conexion.cursor()
            try:
                solicitudes = SolicitudRefinanciamientoPosgrado.objects.filter(persona=persona, status=True).order_by('-id')

                if solicitudes:

                    if solicitudes.filter(estado__valor__in=[17, 24]).exists() and not solicitudes.exclude(estado__valor__in=[17, 24]).exists():
                        data['mostrarboton'] = True
                    else:
                        data['mostrarboton'] = False

                    # Verificar si el pago requerido de la solicitud esta vencido
                    for solicitud in solicitudes.exclude(estado__valor__in=[17, 24]):
                        if solicitud.fechavencepago:
                            # Si el pago minimo esta vencido y sino realizó el pago se debe RECHAZAR LA SOLICITUD Y desbloquear los rubros
                            if not solicitud.montopagado and solicitud.pagovencido() and not solicitud.pagorequeridorealizado():
                                # Rechazar la solicitud
                                # Consulto el estado que voy a asignar
                                estado = obtener_estado_solicitud(1, 13)
                                solicitud.estado = estado
                                solicitud.save(request)

                                # Creo el recorrido de la solicitud
                                recorrido = SolicitudRefinanciamientoPosgradoRecorrido(solicitud=solicitud,
                                                                                       fecha=datetime.now().date(),
                                                                                       observacion='RECHAZO AUTOMÁTICO',
                                                                                       estado=estado
                                                                                       )
                                recorrido.save(request)

                                # Desbloquear los rubros en epunemi para que puedan cobrar
                                for detalle in solicitud.solicitudrefinanciamientoposgradodetalle_set.filter(status=True):
                                    sql = """UPDATE sagest_rubro SET bloqueado=FALSE WHERE idrubrounemi=%s AND status=true""" % (detalle.rubro.id)
                                    cnepunemi.execute(sql)
                            elif solicitud.pagorequeridorealizado() and solicitud.montopagado is False:
                                # Consulto el estado que voy a asignar
                                estado = obtener_estado_solicitud(1, 14)
                                solicitud.montopagado = True
                                solicitud.estado = estado
                                solicitud.save(request)

                                # Creo el recorrido de la solicitud
                                recorrido = SolicitudRefinanciamientoPosgradoRecorrido(solicitud=solicitud,
                                                                                       fecha=datetime.now().date(),
                                                                                       observacion='PAGO REGISTRADO',
                                                                                       estado=estado
                                                                                       )
                                recorrido.save(request)

                    conexion.commit()
                    cnepunemi.close()


                    if matricula.retiradomatricula:
                        if matricula.numero_cuotas_vencidas() == 0:
                            data['mostrarboton'] = False
                    else:
                        if matricula.numero_cuotas_vencidas() < 3:
                            if matricula.ultimo_rubro_posgrado() > datetime.now().date():
                                data['mostrarboton'] = False

                else:
                    if matricula.retiradomatricula:
                        if matricula.numero_cuotas_vencidas() == 0:
                            data['mostrarboton'] = False
                        else:
                            data['mostrarboton'] = mostrarboton = periodo_solicitud_vigente()
                            data['mensaje'] = "El cronograma de registro de solicitudes de refinanciamiento no está vigente" if not mostrarboton else ""
                            if mostrarboton:
                                data['msgvalidacion'] = "Estimado alumno se le comunica que la opción Agregar Solicitud de Refinanciamiento no está disponible por el momento" if not validacion_rubros_unemi_epunemi(matricula) else ""
                    else:
                        if matricula.numero_cuotas_vencidas() < 3:
                            if matricula.ultimo_rubro_posgrado() > datetime.now().date():
                                data['mostrarboton'] = False
                            else:
                                if matricula.numero_cuotas_vencidas() > 0:
                                    data['mostrarboton'] = mostrarboton = periodo_solicitud_vigente()
                                    data['mensaje'] = "El cronograma de registro de solicitudes de refinanciamiento no está vigente" if not mostrarboton else ""
                                    if mostrarboton:
                                        data['msgvalidacion'] = "Estimado alumno se le comunica que la opción Agregar Solicitud de Refinanciamiento no está disponible por el momento" if not validacion_rubros_unemi_epunemi(matricula) else ""

                                else:
                                    data['mostrarboton'] = False
                        else:
                            data['mostrarboton'] = mostrarboton = periodo_solicitud_vigente()
                            data['mensaje'] = "El cronograma de registro de solicitudes de refinanciamiento no está vigente" if not mostrarboton else ""
                            if mostrarboton:
                                data['msgvalidacion'] = "Estimado alumno se le comunica que la opción Agregar Solicitud de Refinanciamiento no está disponible por el momento" if not validacion_rubros_unemi_epunemi(matricula) else ""

                data['title'] = 'Solicitudes de Refinanciamiento de Deudas Programas de Posgrado'
                data['solicitudes'] = solicitudes

                return render(request, "alu_refinanciamientoposgrado/view.html", data)
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                conexion.rollback()
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})


def periodo_solicitud_vigente():
    fechadisponible = datetime.strptime('2021-09-15', '%Y-%m-%d').date()
    fechaactual = datetime.now().date()
    return fechaactual.__le__(fechadisponible)


def validacion_rubros_unemi_epunemi(matricula):
    if not matricula.retiradomatricula:
        valorpendiente = matricula.total_saldo_rubrosinanular()
    else:
        valorvencido = matricula.total_saldo_alumno_retirado()
        valorpendiente = valorvencido

    sumasaldoepunemi = 0
    cnepunemi = connections['epunemi'].cursor()
    rubros = Rubro.objects.filter(status=True, matricula=matricula, cancelado=False).order_by('fechavence')
    for rubro in rubros:
        idrubro = rubro.id
        sql = """SELECT ru.id,ru.saldo, ru.valor FROM sagest_rubro AS ru WHERE ru.idrubrounemi=%s AND status=true;""" % (idrubro)
        cnepunemi.execute(sql)
        registro = cnepunemi.fetchone()
        if registro is not None:
            pendienteepunemi = registro[1]
            sumasaldoepunemi += pendienteepunemi
        else:
            pendienteepunemi = 0
            sumasaldoepunemi += pendienteepunemi

    cnepunemi.close()

    valorpendiente = null_to_decimal(valorpendiente, 2)
    sumasaldoepunemi = null_to_decimal(sumasaldoepunemi, 2)

    if valorpendiente == sumasaldoepunemi:
        return True
    else:
        # Envio de e-mail de notificacion a desarrollo
        listacuentascorreo = [18]  # posgrado@unemi.edu.ec

        fechaenvio = datetime.now().date()
        horaenvio = datetime.now().time()
        cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)
        tituloemail = "Novedades Saldos de Rubros UNEMI / EPUNEMI - Programas de Posgrado"
        send_html_mail(tituloemail,
                       "emails/notificacion_saldos_unemi_epunemi.html",
                       {'sistema': u'Posgrado UNEMI',
                        'fecha': fechaenvio,
                        'hora': horaenvio,
                        'genero': 'la' if matricula.inscripcion.persona.sexo_id == 1 else 'él',
                        'estudiante': matricula.inscripcion.persona.nombre_completo_inverso(),
                        'cedula': matricula.inscripcion.persona.identificacion(),
                        'saldounemi': valorpendiente,
                        'saldoepunemi': sumasaldoepunemi,
                        't': miinstitucion()
                        },
                       ['isaltosm@unemi.edu.ec'],
                       [],
                       cuenta=CUENTAS_CORREOS[cuenta][1]
                       )

        # Temporizador para evitar que se bloquee el servicio de gmail
        pausaparaemail.sleep(2)

        return False
