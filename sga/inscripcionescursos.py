# -*- coding: latin-1 -*-
import json
import sys
from itertools import count
import random
from PIL.ImageOps import _lut
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction

from ejecuform.models import CapacitaEventoFormacionEjecutiva, PeriodoFormaEjecutiva, CapaEventoInscritoFormaEjecutiva
from moodle.models import UserAuth
from sga.templatetags.sga_extras import encrypt
from django.db.models import Sum
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.template.loader import get_template
from django.template.context import Context
from django.db.models.query_utils import Q
from datetime import datetime, timedelta
from xlwt import *
from xlwt import easyxf
import xlwt

from decorators import secure_module, last_access
from posgrado.forms import AdmiPeriodoForm
from sagest.models import TipoOtroRubro, Rubro, CapPeriodoIpec, CapEventoPeriodoIpec, CapInscritoIpec
from sga.commonviews import obtener_reporte
from sga.forms import ActextracurricularForm, RegistrarCertificadoForm, InscripcionCursoProsgradoForm
from sga.funciones import MiPaginador, log, variable_valor, calculate_username, generar_usuario_sin_perfil
from sga.models import Persona, Provincia, Externo, Matricula, RecordAcademico, miinstitucion, CUENTAS_CORREOS

from sga.tasks import send_html_mail, conectar_cuenta

# @login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'addregistro':
                try:
                    dominioemailunemi = '@unemi.edu.ec'
                    if dominioemailunemi in request.POST['email']:
                        return JsonResponse({"result": "bad", "mensaje": f"El correo ingresado {request.POST['email']} es el institucional UNEMI. Por favor, debe ingresar un correo personal (al que actualmente tenga acceso)."})
                    if not request.POST['aceptoterminos']:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe aceptar los términos y condiciones para continuar."})
                    browser = request.POST['navegador']
                    ops = request.POST['os']
                    cookies = request.POST['cookies']
                    screensize = request.POST['screensize']
                    hoy = datetime.now().date()
                    cedula = request.POST['cedula'].strip()
                    direccion1 = request.POST['direccion1']
                    # direccion2 = request.POST['direccion2']
                    tipoiden = request.POST['id_tipoiden']
                    telefono = request.POST['telefono']
                    nombres = request.POST['nombres']
                    apellido1 = request.POST['apellido1']
                    apellido2 = request.POST['apellido2']
                    email = request.POST['email']
                    sexo = request.POST['genero']
                    nacimiento = request.POST['nacimiento']
                    # lugarestudio = request.POST['lugarestudio']
                    # carrera = request.POST['carrera']
                    # profesion = request.POST['profesion']
                    # institucionlabora = request.POST['dondelabora']
                    # cargo = request.POST['cargo']
                    teleoficina = request.POST['teleoficina']
                    # provinciaid = request.POST['provinciaid']
                    # cantonid = request.POST['cantonid']
                    datospersona=None
                    cursoid = CapEventoPeriodoIpec.objects.get(pk=request.POST['cursoid'])
                    if cursoid.seguimientograduado:
                        return JsonResponse({'result': 'bad', "mensaje": u"No se puede inscribir a este curso"})
                    notifica = cursoid.notificarubro
                    if cursoid.cupo > cursoid.capinscritoipec_set.filter(status=True).count():
                        if not cursoid.tiporubro and cursoid.generarrubro:
                            return JsonResponse({'result': 'bad', "mensaje": u"No existe Rubro en curso."})
                        tiporubroarancel = cursoid.tiporubro
                        if tipoiden == '1':
                            if Persona.objects.filter(Q(cedula=cedula) |Q(pasaporte=cedula),status=True).exists():
                                datospersona = Persona.objects.filter(Q(cedula=cedula) |Q(pasaporte=cedula),status=True)
                                if datospersona.count()>1:
                                    raise NameError(u"La cedula ingresada se encuentra asociado a más de una persona, por favor comunicarse con desarrollo.sistemas@unemi.edu.ec ")
                                datospersona = datospersona[0]
                                datospersona.direccion = direccion1
                                # datospersona.direccion2 = direccion2
                                datospersona.telefono = telefono
                                datospersona.email = email
                                datospersona.save(request)
                            else:
                                datospersona = Persona(cedula=cedula,
                                                       nombres=nombres,
                                                       apellido1=apellido1,
                                                       apellido2=apellido2,
                                                       email=email,
                                                       sexo_id=sexo,
                                                       nacimiento=nacimiento,
                                                       direccion=direccion1,
                                                       # direccion2=direccion2,
                                                       # provincia_id=provinciaid,
                                                       # canton_id=cantonid,
                                                       telefono=telefono
                                                       )
                                datospersona.save(request)
                        if tipoiden == '2':
                            if Persona.objects.filter(Q(cedula=cedula) |Q(pasaporte=cedula),status=True).exists():
                                datospersona = Persona.objects.filter(Q(cedula=cedula) |Q(pasaporte=cedula),status=True)
                                if datospersona.count()>1:
                                    raise NameError(u"El pasaporte ingresado se encuentra asociado a más de una persona, por favor comunicarse con desarrollo.sistemas@unemi.edu.ec ")
                                datospersona=datospersona[0]
                                datospersona.direccion = direccion1
                                # datospersona.direccion2 = direccion2
                                datospersona.email = email
                                datospersona.save(request)
                            else:
                                datospersona = Persona(pasaporte=cedula,
                                                       nombres=nombres,
                                                       apellido1=apellido1,
                                                       apellido2=apellido2,
                                                       email=email,
                                                       sexo_id=sexo,
                                                       nacimiento=nacimiento,
                                                       direccion=direccion1,
                                                       # direccion2=direccion2,
                                                       # provincia_id=provinciaid,
                                                       # canton_id=cantonid,
                                                       telefono=telefono
                                                       )
                                datospersona.save(request)
                        if not datospersona.externo_set.filter(status=True).exists():
                            datospersonaexterna = Externo(persona=datospersona,
                                                          nombrecomercial='',
                                                          nombrecontacto='',
                                                          telefonocontacto='',
                                                          # lugarestudio=lugarestudio,
                                                          # carrera=carrera,
                                                          # profesion=profesion,
                                                          # institucionlabora=institucionlabora,
                                                          # cargodesempena=cargo,
                                                          telefonooficina=teleoficina
                                                          )
                            datospersonaexterna.save(request)
                        else:
                            datospersonaexterna = Externo.objects.get(persona=datospersona)
                            # datospersonaexterna.lugarestudio = lugarestudio
                            # datospersonaexterna.carrera = carrera
                            # datospersonaexterna.profesion = profesion
                            # datospersonaexterna.institucionlabora = institucionlabora
                            # datospersonaexterna.cargodesempena = cargo
                            datospersonaexterna.telefonooficina = teleoficina
                            datospersonaexterna.save(request)
                        if not CapInscritoIpec.objects.filter(participante=datospersona, capeventoperiodo=cursoid, status=True).exists():
                            personalunemi = False
                            if datospersona.distributivopersona_set.filter(estadopuesto_id=1, status=True).exists():
                                costo_curso_total = cursoid.costo
                                personalunemi = True
                            else:
                                if datospersona.inscripcion_set.filter(status=True).exclude(coordinacion_id=9):
                                    verificainsripcion = datospersona.inscripcion_set.values_list('id').filter(status=True).exclude(coordinacion_id=9)
                                    if Matricula.objects.filter(inscripcion__id__in=verificainsripcion, status=True):
                                        # if datospersona.inscripcion_set.filter(status=True).exclude(coordinacion_id=9)[0].matricula_set.filter(status=True):
                                        costo_curso_total = cursoid.costo
                                        personalunemi = True
                                    else:
                                        if RecordAcademico.objects.filter(inscripcion__id__in=verificainsripcion, status=True):
                                            costo_curso_total = cursoid.costo
                                            personalunemi = True
                                        else:
                                            costo_curso_total = cursoid.costoexterno
                                else:
                                    costo_curso_total = cursoid.costoexterno
                            inscripcioncurso = CapInscritoIpec(participante=datospersona,
                                                               capeventoperiodo=cursoid,
                                                               personalunemi=personalunemi
                                                               )
                            inscripcioncurso.save(request)

                            # epunemi = False
                            # fepunemi = '2019-09-01'
                            # fechaepunemi = datetime.strptime(fepunemi, "%Y-%m-%d").date()
                            # if datetime.now().date()>=fechaepunemi:
                            #     epunemi = True
                            # if cursoid.generarrubro:
                            #     rubro = Rubro(tipo=tiporubroarancel,
                            #                   persona=datospersona,
                            #                   capeventoperiodoipec=cursoid,
                            #                   # inscripcioncursoposgrado=inscripcioncurso,
                            #                   relacionados=None,
                            #                   nombre=tiporubroarancel.nombre + ' - ' + cursoid.capevento.nombre,
                            #                   cuota=1,
                            #                   fecha=datetime.now().date(),
                            #                   fechavence=cursoid.fechamaxpago + timedelta(days=1),
                            #                   valor=costo_curso_total,
                            #                   iva_id=1,
                            #                   valoriva=0,
                            #                   valortotal=costo_curso_total,
                            #                   saldo=costo_curso_total,
                            #                   epunemi=True,
                            #                   cancelado=False)
                            #     rubro.save(request)
                            send_html_mail("Registro exitoso Inscripcion-CURSOS.", "emails/registro_edcon.html",
                                           {'sistema': u'CURSOS - UNEMI', 'fecha': datetime.now().date(),
                                            'hora': datetime.now().time(),'inscrito': inscripcioncurso,'notifica':notifica, 'bs': browser, 'os': ops, 'cookies': cookies,
                                            'screensize': screensize},datospersona.emailpersonal(),[],cuenta=variable_valor('CUENTAS_CORREOS')[4])
                            # if cursoid.generarrubro:
                            #     return JsonResponse({'result': 'ok', "mensaje": u"Estimado participante, Usted se encuentra pre inscrito. Por favor, acérquese a realizar el pago en ventanillas de Recaudación de la ECUNEMI(junto a la UNEMI) de manera inmediata, o efectuar el pago mediante transferencia bancaria a las cuentas respectivas.<br> Fecha máxima de pago: " + str(cursoid.fechamaxpago)})
                            # else:
                            return JsonResponse({'result': 'ok', "mensaje": u"Estimado participante, se inscribió correctamente." })
                        else:
                            return JsonResponse({'result': 'si', "mensaje": u"Usted ya se encuentra matriculado en el curso."})
                    else:
                        return JsonResponse({'result': 'bad', "mensaje": u"Lo sentimos el cupo está completo."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos, %s"%ex})

            if action == 'addregistroformejecut':
                try:
                    dominioemailunemi = '@unemi.edu.ec'
                    if dominioemailunemi in request.POST['email']:
                        return JsonResponse({"result": "bad", "mensaje": f"El correo ingresado {request.POST['email']} es el institucional UNEMI. Por favor, debe ingresar un correo personal (al que actualmente tenga acceso)."})
                    if not request.POST['aceptoterminos']:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe aceptar los términos y condiciones para continuar."})
                    browser = request.POST['navegador']
                    ops = request.POST['os']
                    cookies = request.POST['cookies']
                    screensize = request.POST['screensize']
                    hoy = datetime.now().date()
                    cedula = request.POST['cedula'].strip()
                    direccion1 = request.POST['direccion1']
                    # direccion2 = request.POST['direccion2']
                    tipoiden = request.POST['id_tipoiden']
                    telefono = request.POST['telefono']
                    nombres = request.POST['nombres']
                    apellido1 = request.POST['apellido1']
                    apellido2 = request.POST['apellido2']
                    email = request.POST['email']
                    sexo = request.POST['genero']
                    nacimiento = request.POST['nacimiento']
                    teleoficina = request.POST['teleoficina']
                    datospersona=None
                    if request.POST['cursoid'] == '':
                        raise NameError("No existen cupos disponibles")
                    if not CapacitaEventoFormacionEjecutiva.objects.values('id').filter(pk=request.POST['cursoid'],status=True).exists():
                        return JsonResponse({'result': 'bad', "mensaje": u"No existe el evento, intentelo mas tarde."})
                    cursoid = CapacitaEventoFormacionEjecutiva.objects.get(pk=request.POST['cursoid'])
                    if cursoid.cupo > cursoid.capaeventoinscritoformaejecutiva_set.filter(status=True).count():
                        if not cursoid.tiporubro and cursoid.generarrubro:
                            return JsonResponse({'result': 'bad', "mensaje": u"No existe Rubro en curso."})
                        tiporubroarancel = cursoid.tiporubro
                        if tipoiden == '1':
                            if Persona.objects.filter(Q(cedula=cedula) |Q(pasaporte=cedula),status=True).exists():
                                datospersona = Persona.objects.filter(Q(cedula=cedula) |Q(pasaporte=cedula),status=True)
                                if datospersona.count()>1:
                                    raise NameError(u"La cedula ingresada se encuentra asociado a más de una persona, por favor comunicarse con desarrollo.sistemas@unemi.edu.ec ")
                                datospersona = datospersona[0]
                                datospersona.direccion = direccion1
                                datospersona.telefono = telefono
                                datospersona.email = email
                                datospersona.save(request)
                            else:
                                datospersona = Persona(cedula=cedula,
                                                       nombres=nombres,
                                                       apellido1=apellido1,
                                                       apellido2=apellido2,
                                                       email=email,
                                                       sexo_id=sexo,
                                                       nacimiento=nacimiento,
                                                       direccion=direccion1,
                                                       telefono=telefono
                                                       )
                                datospersona.save(request)
                        if tipoiden == '2':
                            if Persona.objects.filter(Q(cedula=cedula) |Q(pasaporte=cedula),status=True).exists():
                                datospersona = Persona.objects.filter(Q(cedula=cedula) |Q(pasaporte=cedula),status=True)
                                if datospersona.count()>1:
                                    raise NameError(u"El pasaporte ingresado se encuentra asociado a más de una persona, por favor comunicarse con desarrollo.sistemas@unemi.edu.ec ")
                                datospersona=datospersona[0]
                                datospersona.direccion = direccion1
                                datospersona.email = email
                                datospersona.save(request)
                            else:
                                datospersona = Persona(pasaporte=cedula,
                                                       nombres=nombres,
                                                       apellido1=apellido1,
                                                       apellido2=apellido2,
                                                       email=email,
                                                       sexo_id=sexo,
                                                       nacimiento=nacimiento,
                                                       direccion=direccion1,
                                                       telefono=telefono
                                                       )
                                datospersona.save(request)
                        if not datospersona.externo_set.filter(status=True).exists():
                            datospersonaexterna = Externo(persona=datospersona,
                                                          nombrecomercial='',
                                                          nombrecontacto='',
                                                          telefonocontacto='',
                                                          telefonooficina=teleoficina
                                                          )
                            datospersonaexterna.save(request)
                        else:
                            datospersonaexterna = Externo.objects.get(persona=datospersona)
                            datospersonaexterna.telefonooficina = teleoficina
                            datospersonaexterna.save(request)
                        if not CapaEventoInscritoFormaEjecutiva.objects.filter(participante=datospersona, capeventoperiodo=cursoid, status=True).exists():
                            personalunemi = False
                            if datospersona.distributivopersona_set.filter(estadopuesto_id=1, status=True).exists():
                                costo_curso_total = cursoid.costo
                                personalunemi = True
                            else:
                                if datospersona.inscripcion_set.filter(status=True).exclude(coordinacion_id=9):
                                    verificainsripcion = datospersona.inscripcion_set.values_list('id').filter(status=True).exclude(coordinacion_id=9)
                                    if Matricula.objects.filter(inscripcion__id__in=verificainsripcion, status=True):
                                        # if datospersona.inscripcion_set.filter(status=True).exclude(coordinacion_id=9)[0].matricula_set.filter(status=True):
                                        costo_curso_total = cursoid.costo
                                        personalunemi = True
                                    else:
                                        if RecordAcademico.objects.filter(inscripcion__id__in=verificainsripcion, status=True):
                                            costo_curso_total = cursoid.costo
                                            personalunemi = True
                                        else:
                                            costo_curso_total = cursoid.costoexterno
                                else:
                                    costo_curso_total = cursoid.costoexterno
                            inscripcioncurso = CapaEventoInscritoFormaEjecutiva(participante=datospersona,
                                                               capeventoperiodo=cursoid,
                                                               personalunemi=personalunemi
                                                               )
                            inscripcioncurso.save(request)
                            usuarionuevo = False
                            if not datospersona.usuario:
                                usuarionuevo = True
                                username = calculate_username(datospersona)
                                generar_usuario_sin_perfil_formacioneje(datospersona, username)
                                resetear = request.POST.get('resetear', '') == 'on'
                                enviar_correo_credenciales(request, datospersona, usuarionuevo, resetear,
                                                           'CLIENTE EXTERNO', CUENTAS_CORREOS[4][1])

                            send_html_mail("Registro exitoso Inscripcion-CURSOS.", "emails/registro_formejecutiva.html",
                                           {'sistema': u'CURSOS - UNEMI', 'fecha': datetime.now().date(),
                                            'hora': datetime.now().time(),'inscrito': inscripcioncurso , 'bs': browser, 'os': ops, 'cookies': cookies,
                                            'screensize': screensize}, datospersona.emailpersonal(), [],
                                           cuenta=variable_valor('CUENTAS_CORREOS')[4])
                            return JsonResponse({'result': 'ok', "mensaje": u"Estimado participante, se inscribió correctamente." })
                        else:
                            return JsonResponse({'result': 'si', "mensaje": u"Usted ya se encuentra matriculado en el curso."})
                    else:
                        return JsonResponse({'result': 'bad', "mensaje": u"Lo sentimos el cupo está completo."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos, %s"%ex})

            if action == 'consultacedula':
                try:
                    codigocurso = CapEventoPeriodoIpec.objects.get(pk=request.POST['codigocurso'])
                    cedula = request.POST['cedula'].strip()
                    datospersona = None
                    costocurso = 0
                    provinciaid = 0
                    cantonid = 0
                    cantonnom = ''
                    lugarestudio = ''
                    carrera = ''
                    profesion = ''
                    institucionlabora = ''
                    cargo = ''
                    teleoficina = ''
                    idgenero = 0
                    habilitaemail = 0
                    if Persona.objects.filter(cedula=cedula).exists():
                        datospersona = Persona.objects.get(cedula=cedula)
                    if Persona.objects.filter(pasaporte=cedula).exists():
                        datospersona = Persona.objects.get(pasaporte=cedula)
                    if not datospersona:
                        return JsonResponse({"result": "bad", "costocurso": codigocurso.costoexterno})
                    else:
                        if datospersona.distributivopersona_set.filter(estadopuesto_id=1, status=True).exists():
                            costocurso = codigocurso.costo
                            if not datospersona.email:
                                habilitaemail = 1
                        else:
                            habilitaemail = 1
                            if datospersona.inscripcion_set.filter(status=True).exclude(coordinacion_id=9):
                                verificainsripcion = datospersona.inscripcion_set.values_list('id').filter(status=True).exclude(coordinacion_id=9)
                                if Matricula.objects.filter(inscripcion__id__in=verificainsripcion, status=True):
                                    # if datospersona.inscripcion_set.filter(status=True).exclude(coordinacion_id=9)[0].matricula_set.filter(status=True):
                                    costocurso = codigocurso.costo
                                else:
                                    if RecordAcademico.objects.filter(inscripcion__id__in=verificainsripcion, status=True):
                                        costocurso = codigocurso.costo
                                    else:
                                        costocurso = codigocurso.costoexterno
                            else:
                                costocurso = codigocurso.costoexterno
                        if datospersona.sexo:
                            idgenero = datospersona.sexo.id
                        if datospersona.provincia:
                            provinciaid = datospersona.provincia.id
                        if datospersona.canton:
                            cantonid = datospersona.canton.id
                            cantonnom = datospersona.canton.nombre
                        if datospersona.externo_set.filter(status=True).exists():
                            datospersonaexterna = datospersona.externo_set.filter(status=True)[0]
                            lugarestudio = datospersonaexterna.lugarestudio
                            carrera = datospersonaexterna.carrera
                            profesion = datospersonaexterna.profesion
                            institucionlabora = datospersonaexterna.institucionlabora
                            cargo = datospersonaexterna.cargodesempena
                            teleoficina = datospersonaexterna.telefonooficina
                        # if not CapInscritoIpec.objects.filter(participante=datospersona, capeventoperiodo__capevento=codigocurso.capevento, status=True).exists():
                        if not CapInscritoIpec.objects.filter(participante=datospersona, capeventoperiodo=codigocurso, status=True).exists():
                            return JsonResponse({"result": "ok", "apellido1": datospersona.apellido1, "apellido2": datospersona.apellido2,
                                                 "nombres": datospersona.nombres, "email": datospersona.email, "telefono": datospersona.telefono,
                                                 "direccion1": datospersona.direccion, "direccion2": datospersona.direccion2,
                                                 "nacimiento": datospersona.nacimiento, "costocurso": costocurso,
                                                 "provinciaid": provinciaid, "cantonid": cantonid, "cantonnom": cantonnom,
                                                 "lugarestudio": lugarestudio,"carrera": carrera,"profesion": profesion,
                                                 "institucionlabora": institucionlabora,"cargo": cargo,"teleoficina": teleoficina,"idgenero": idgenero,"habilitaemail": habilitaemail })
                        else:
                            # miinscripcion = CapInscritoIpec.objects.get(participante=datospersona, capeventoperiodo__capevento=codigocurso.capevento, status=True)
                            miinscripcion = CapInscritoIpec.objects.get(participante=datospersona, capeventoperiodo=codigocurso, status=True)
                            return JsonResponse({"result": "si", "mensaje": u"Usted ya se encuentra inscrito en el curso: " + codigocurso.capevento.nombre + ' - ' + miinscripcion.capeventoperiodo.observacion })

                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'consultacedulaejecu':
                try:
                    if request.POST['codigocurso'] == "":
                        raise NameError("Curso no disponible")
                    codigocurso = CapacitaEventoFormacionEjecutiva.objects.get(pk=request.POST['codigocurso'])
                    cedula = request.POST['cedula'].strip()
                    datospersona = None
                    costocurso = 0
                    provinciaid = 0
                    cantonid = 0
                    cantonnom = ''
                    lugarestudio = ''
                    carrera = ''
                    profesion = ''
                    institucionlabora = ''
                    cargo = ''
                    teleoficina = ''
                    idgenero = 0
                    habilitaemail = 0
                    if Persona.objects.filter(cedula=cedula).exists():
                        datospersona = Persona.objects.get(cedula=cedula)
                    if Persona.objects.filter(pasaporte=cedula).exists():
                        datospersona = Persona.objects.get(pasaporte=cedula)
                    if not datospersona:
                        return JsonResponse({"result": "bad", "costocurso": codigocurso.costoexterno})
                    else:
                        if datospersona.distributivopersona_set.filter(estadopuesto_id=1, status=True).exists():
                            costocurso = codigocurso.costo
                            if not datospersona.email:
                                habilitaemail = 1
                        else:
                            habilitaemail = 1
                            if datospersona.inscripcion_set.filter(status=True).exclude(coordinacion_id=9):
                                verificainsripcion = datospersona.inscripcion_set.values_list('id').filter(
                                    status=True).exclude(coordinacion_id=9)
                                if Matricula.objects.filter(inscripcion__id__in=verificainsripcion, status=True):
                                    # if datospersona.inscripcion_set.filter(status=True).exclude(coordinacion_id=9)[0].matricula_set.filter(status=True):
                                    costocurso = codigocurso.costo
                                else:
                                    if RecordAcademico.objects.filter(inscripcion__id__in=verificainsripcion,
                                                                      status=True):
                                        costocurso = codigocurso.costo
                                    else:
                                        costocurso = codigocurso.costoexterno
                            else:
                                costocurso = codigocurso.costoexterno
                        if datospersona.sexo:
                            idgenero = datospersona.sexo.id
                        if datospersona.provincia:
                            provinciaid = datospersona.provincia.id
                        if datospersona.canton:
                            cantonid = datospersona.canton.id
                            cantonnom = datospersona.canton.nombre
                        if datospersona.externo_set.filter(status=True).exists():
                            datospersonaexterna = datospersona.externo_set.filter(status=True)[0]
                            lugarestudio = datospersonaexterna.lugarestudio
                            carrera = datospersonaexterna.carrera
                            profesion = datospersonaexterna.profesion
                            institucionlabora = datospersonaexterna.institucionlabora
                            cargo = datospersonaexterna.cargodesempena
                            teleoficina = datospersonaexterna.telefonooficina
                        if not CapaEventoInscritoFormaEjecutiva.objects.filter(participante=datospersona, capeventoperiodo=codigocurso,
                                                              status=True).exists():
                            return JsonResponse({"result": "ok", "apellido1": datospersona.apellido1,
                                                 "apellido2": datospersona.apellido2,
                                                 "nombres": datospersona.nombres, "email": datospersona.email,
                                                 "telefono": datospersona.telefono,
                                                 "direccion1": datospersona.direccion,
                                                 "direccion2": datospersona.direccion2,
                                                 "nacimiento": datospersona.nacimiento, "costocurso": costocurso,
                                                 "provinciaid": provinciaid, "cantonid": cantonid,
                                                 "cantonnom": cantonnom,
                                                 "lugarestudio": lugarestudio, "carrera": carrera,
                                                 "profesion": profesion,
                                                 "institucionlabora": institucionlabora, "cargo": cargo,
                                                 "teleoficina": teleoficina, "idgenero": idgenero,
                                                 "habilitaemail": habilitaemail})
                        else:
                            miinscripcion = CapaEventoInscritoFormaEjecutiva.objects.get(participante=datospersona,
                                                                        capeventoperiodo=codigocurso, status=True)
                            return JsonResponse({"result": "si",
                                                 "mensaje": u"Usted ya se encuentra inscrito en el curso: " + codigocurso.capevento.nombre + ' - ' + miinscripcion.capeventoperiodo.observacion})
                except Exception as ex:
                    err_ = f'{ex}({sys.exc_info()[-1].tb_lineno})'
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": err_})


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'insripcioncursoposgrado':
                try:
                    data['title'] = u'Registrar certificado'
                    hoy = datetime.now().date()
                    cursos = None
                    listacur = []
                    if CapEventoPeriodoIpec.objects.filter(fechainicioinscripcion__lte=hoy, fechafininscripcion__gte=hoy , publicarinscripcion=True, status=True).exists():
                        cursos = CapEventoPeriodoIpec.objects.filter(fechainicioinscripcion__lte=hoy, fechafininscripcion__gte=hoy, publicarinscripcion=True, status=True).exclude(seguimientograduado=True)
                        for cur in cursos:
                            if cur.cupo > cur.capinscritoipec_set.filter(status=True).count():
                                listacur.append(cur.id)
                        if listacur:
                            cursos = CapEventoPeriodoIpec.objects.filter(pk__in=listacur)
                        else:
                            cursos = None
                        if not TipoOtroRubro.objects.filter(pk__in=cursos.values_list('tiporubro_id').filter(status=True)).exists():
                            cursos = None
                    data['cursos'] = cursos
                    data['listaprovinvias'] = Provincia.objects.filter(pais_id=1, status=True).order_by('nombre')
                    data['currenttime']= datetime.now()
                    data['id_eventoperiodo'] = id_eventoperiodo = int(encrypt(request.GET['id']))
                    data['evento'] = CapEventoPeriodoIpec.objects.filter(id=id_eventoperiodo).first()
                    return render(request, "inscripcionescursos/inscripcionescursosedcon.html", data)
                except Exception as ex:
                    pass
            elif action == 'cursosdisponibles':
                try:
                    search = None
                    ids = None
                    hoy = datetime.now().date()
                    data['url_vars'] = '&action=cursosdisponibles'
                    data['periodo_ipec'] = periodo = CapPeriodoIpec.objects.get(pk=10)
                    evento = CapEventoPeriodoIpec.objects.filter(fechainicioinscripcion__lte=hoy, fechafininscripcion__gte=hoy , publicarinscripcion=True, status=True).order_by('fechainicio').exclude(seguimientograduado=True)
                    paging = MiPaginador(evento, 8)
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
                    data['evento'] = page.object_list
                    return render(request, "inscripcionescursos/cursosdisponibles.html", data)
                except Exception as ex:
                    pass
                
            elif action == 'cursodisponible':
                try:
                    hoy = datetime.now().date()
                    data['evento'] = evento = CapEventoPeriodoIpec.objects.get(pk=int(encrypt(request.GET['id'])),fechainicioinscripcion__lte=hoy, fechafininscripcion__gte=hoy , publicarinscripcion=True,status=True)
                    data['title'] = evento.capevento.nombre
                    cursosrecomendados = CapEventoPeriodoIpec.objects.filter(status=True,fechainicioinscripcion__lte=hoy, fechafininscripcion__gte=hoy , publicarinscripcion=True,enfoque=evento.enfoque).exclude(Q(id=evento.id) | Q(seguimientograduado=True))
                    if cursosrecomendados.count() < 4:
                        cursosrecomendados = CapEventoPeriodoIpec.objects.filter(status=True,fechainicioinscripcion__lte=hoy, fechafininscripcion__gte=hoy , publicarinscripcion=True).exclude(Q(id=evento.id) | Q(seguimientograduado=True))[:4]
                    else:
                        cursosrecomendados = cursosrecomendados[:4]
                    data['cursosrecomendados'] = cursosrecomendados
                    # data['periodo'] = periodo = CapPeriodoIpec.objects.get(pk=int(request.GET['periodo_ipec']))
                    # data['eventosedcon'] = evento = CapEventoPeriodoIpec.objects.filter(periodo=periodo, status=True).order_by('fechainicio')
                    return render(request, "inscripcionescursos/cursodisponible.html", data)
                except Exception as ex:
                    pass

            elif action == 'cursoformacionejecutiva':
                try:
                    search = None
                    ids = None
                    hoy = datetime.now().date()
                    data['url_vars'] = '&action=cursoformacionejecutiva'
                    # data['periodo_formejecu'] = periodo = PeriodoFormaEjecutiva.objects.get(pk=10)
                    evento = CapacitaEventoFormacionEjecutiva.objects.filter(fechainicioinscripcion__lte=hoy,fechafininscripcion__gte=hoy, publicarinscripcion=True,
                                                                 status=True).order_by('fechainicio')
                    paging = MiPaginador(evento, 8)
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
                    data['evento'] = page.object_list
                    return render(request, "inscripcionescursos/cursosformejecutiva.html", data)
                except Exception as ex:
                    pass

            elif action == 'courseformejex':
                try:
                    hoy = datetime.now().date()
                    data['evento'] = evento = CapacitaEventoFormacionEjecutiva.objects.get(pk=int(encrypt(request.GET['id'])),
                                                                               fechainicioinscripcion__lte=hoy,
                                                                               fechafininscripcion__gte=hoy,
                                                                               publicarinscripcion=True, status=True)
                    data['title'] = evento.capevento.nombre
                    cursosrecomendados = CapacitaEventoFormacionEjecutiva.objects.filter(status=True,
                                                                             fechainicioinscripcion__lte=hoy,
                                                                             fechafininscripcion__gte=hoy,
                                                                             publicarinscripcion=True,
                                                                             enfoque=evento.enfoque).exclude(
                        id=evento.id)
                    if cursosrecomendados.count() < 4:
                        cursosrecomendados = CapacitaEventoFormacionEjecutiva.objects.filter(status=True,
                                                                                 fechainicioinscripcion__lte=hoy,
                                                                                 fechafininscripcion__gte=hoy,
                                                                                 publicarinscripcion=True).exclude(
                            id=evento.id)[:4]
                    else:
                        cursosrecomendados = cursosrecomendados[:4]
                    data['cursosrecomendados'] = cursosrecomendados
                    # data['periodo'] = periodo = CapPeriodoIpec.objects.get(pk=int(request.GET['periodo_ipec']))
                    # data['eventosedcon'] = evento = CapEventoPeriodoIpec.objects.filter(periodo=periodo, status=True).order_by('fechainicio')
                    return render(request, "inscripcionescursos/cursoformejecutiva.html", data)
                except Exception as ex:
                    pass

            elif action == 'enrollcourseposgrado':
                try:
                    data['title'] = u'Registrar certificado'
                    hoy = datetime.now().date()
                    cursos = None
                    listacur = []
                    if CapacitaEventoFormacionEjecutiva.objects.filter(fechainicioinscripcion__lte=hoy, fechafininscripcion__gte=hoy , publicarinscripcion=True, status=True).exists():
                        cursos = CapacitaEventoFormacionEjecutiva.objects.filter(fechainicioinscripcion__lte=hoy, fechafininscripcion__gte=hoy, publicarinscripcion=True, status=True)
                        for cur in cursos:
                            if cur.cupo > cur.capaeventoinscritoformaejecutiva_set.filter(status=True).count():
                                listacur.append(cur.id)
                        if listacur:
                            cursos = CapacitaEventoFormacionEjecutiva.objects.filter(pk__in=listacur)
                        else:
                            cursos = None
                        if not TipoOtroRubro.objects.filter(pk__in=cursos.values_list('tiporubro_id').filter(status=True)).exists():
                            cursos = None
                    data['cursos'] = cursos
                    data['listaprovinvias'] = Provincia.objects.filter(pais_id=1, status=True).order_by('nombre')
                    data['currenttime']= datetime.now()
                    data['id_eventoperiodo'] = int(encrypt(request.GET['id']))
                    return render(request, "inscripcionescursos/inscripcionesformejecut.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Registrar certificado'
                hoy = datetime.now().date()
                cursos = None
                return render(request, "inscripcionescursos/inscripcionescursos.html", data)
            except Exception as ex:
                pass
def enviar_correo_credenciales(request, persona, usuarionuevo, resetear, tipousuario, cuentascorreos):
    correo = persona.lista_emails()
    anio = "*" + str(persona.nacimiento)[0:4] if persona.nacimiento else ''
    if persona.cedula:
        password = persona.cedula.strip() + anio
    elif persona.pasaporte:
        password = persona.pasaporte.strip() + anio
    else:
        password = persona.ruc.strip() + anio
    send_html_mail("Creación de cuenta institucional", "emails/nuevacuentacorreo_v2.html",
                   {'sistema': 'Sistema de Gestión Administrativa', 'persona': persona, 'nuevo': usuarionuevo,
                    'resetear': resetear, 'pass': password,
                    't': miinstitucion(), 'tipo_usuario': tipousuario,
                    'usuario': persona.usuario.username, 'tiposistema_': 2}, correo, [],
                   cuenta=cuentascorreos)


def generar_usuario_sin_perfil_formacioneje(persona, usuario):
    from sga.models import Externo
    from moodle.models import UserAuth
    anio = ''
    if persona.nacimiento:
        anio = "*" + str(persona.nacimiento)[0:4]
    password = persona.identificacion() + anio
    emailinst_ = '{}@unemi.edu.ec'.format(usuario)
    user = User.objects.create_user(usuario, emailinst_, password)
    user.save()
    persona.usuario = user
    persona.save()
    if not Externo.objects.filter(status=True, persona=persona).exists():
        externo = Externo(persona=persona,
                          nombrecomercial='',
                          nombrecontacto='',
                          telefonocontacto='')
        externo.save()
    else:
        externo = Externo.objects.get(status=True, persona=persona)
    persona.crear_perfil(externo=externo)
    persona.clave_cambiada()
    persona.mi_perfil()
    if not UserAuth.objects.filter(usuario=user).exists():
        usermoodle = UserAuth(usuario=user)
        usermoodle.set_data()
        usermoodle.set_password(password)
        usermoodle.save()
    else:
        usermoodle = UserAuth.objects.filter(usuario=user).first()
        usermoodle.set_data()
        usermoodle.save()
