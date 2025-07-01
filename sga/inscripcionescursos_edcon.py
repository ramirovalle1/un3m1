# -*- coding: latin-1 -*-
import json
from itertools import count
import random
from PIL.ImageOps import _lut
from django.contrib.auth.decorators import login_required
from django.db import transaction
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
from sga.funciones import MiPaginador, log, variable_valor
from sga.models import Persona, Provincia, Externo, Matricula, RecordAcademico



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
                    browser = request.POST['navegador']
                    ops = request.POST['os']
                    cookies = request.POST['cookies']
                    screensize = request.POST['screensize']
                    hoy = datetime.now().date()
                    cedula = request.POST['cedula'].strip()
                    direccion1 = request.POST['direccion1']
                    direccion2 = request.POST['direccion2']
                    tipoiden = request.POST['id_tipoiden']
                    telefono = request.POST['telefono']
                    nombres = request.POST['nombres']
                    apellido1 = request.POST['apellido1']
                    apellido2 = request.POST['apellido2']
                    email = request.POST['email']
                    sexo = request.POST['genero']
                    nacimiento = request.POST['nacimiento']
                    lugarestudio = request.POST['lugarestudio']
                    carrera = request.POST['carrera']
                    profesion = request.POST['profesion']
                    institucionlabora = request.POST['dondelabora']
                    cargo = request.POST['cargo']
                    teleoficina = request.POST['teleoficina']
                    provinciaid = request.POST['provinciaid']
                    cantonid = request.POST['cantonid']
                    cursoid = CapEventoPeriodoIpec.objects.get(pk=request.POST['cursoid'])
                    if cursoid.cupo > cursoid.capinscritoipec_set.filter(status=True).count():
                        if not cursoid.tiporubro and cursoid.generarrubro:
                            return JsonResponse({'result': 'bad', "mensaje": u"No existe Rubro en curso."})
                        tiporubroarancel = cursoid.tiporubro
                        if tipoiden == '1':
                            if Persona.objects.filter(cedula=cedula).exists():
                                datospersona = Persona.objects.get(cedula=cedula)
                                datospersona.direccion = direccion1
                                datospersona.direccion2 = direccion2
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
                                                       direccion2=direccion2,
                                                       provincia_id=provinciaid,
                                                       canton_id=cantonid,
                                                       telefono=telefono
                                                       )
                                datospersona.save(request)
                        if tipoiden == '2':
                            if Persona.objects.filter(pasaporte=cedula).exists():
                                datospersona = Persona.objects.get(pasaporte=cedula)
                                datospersona.direccion = direccion1
                                datospersona.direccion2 = direccion2
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
                                                       direccion2=direccion2,
                                                       provincia_id=provinciaid,
                                                       canton_id=cantonid,
                                                       telefono=telefono
                                                       )
                                datospersona.save(request)
                        if not datospersona.externo_set.filter(status=True).exists():
                            datospersonaexterna = Externo(persona=datospersona,
                                                          nombrecomercial='',
                                                          nombrecontacto='',
                                                          telefonocontacto='',
                                                          lugarestudio=lugarestudio,
                                                          carrera=carrera,
                                                          profesion=profesion,
                                                          institucionlabora=institucionlabora,
                                                          cargodesempena=cargo,
                                                          telefonooficina=teleoficina
                                                          )
                            datospersonaexterna.save(request)
                        else:
                            datospersonaexterna = Externo.objects.get(persona=datospersona)
                            datospersonaexterna.lugarestudio = lugarestudio
                            datospersonaexterna.carrera = carrera
                            datospersonaexterna.profesion = profesion
                            datospersonaexterna.institucionlabora = institucionlabora
                            datospersonaexterna.cargodesempena = cargo
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
                            if cursoid.generarrubro:
                                rubro = Rubro(tipo=tiporubroarancel,
                                              persona=datospersona,
                                              capeventoperiodoipec=cursoid,
                                              # inscripcioncursoposgrado=inscripcioncurso,
                                              relacionados=None,
                                              nombre=tiporubroarancel.nombre + ' - ' + cursoid.capevento.nombre,
                                              cuota=1,
                                              fecha=datetime.now().date(),
                                              fechavence=cursoid.fechamaxpago + timedelta(days=1),
                                              valor=costo_curso_total,
                                              iva_id=1,
                                              valoriva=0,
                                              valortotal=costo_curso_total,
                                              saldo=costo_curso_total,
                                              epunemi=True,
                                              cancelado=False)
                                rubro.save(request)
                            if cursoid.generarrubro:
                                return JsonResponse({'result': 'ok', "mensaje": u"Estimado participante, Usted se encuentra pre inscrito. Por favor, acérquese a realizar el pago en ventanillas de Recaudación de la ECUNEMI(junto a la UNEMI) de manera inmediata, o efectuar el pago mediante transferencia bancaria a las cuentas respectivas.<br> Fecha máxima de pago: " + str(cursoid.fechamaxpago)})
                            else:
                                return JsonResponse({'result': 'ok', "mensaje": u"Estimado participante, se inscribió correctamente." })
                        else:
                            return JsonResponse({'result': 'si', "mensaje": u"Usted ya se encuentra matriculado en el curso."})
                    else:
                        return JsonResponse({'result': 'bad', "mensaje": u"Lo sentimos el cupo está completo."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

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
                            return JsonResponse({"result": "si", "mensaje": u"Usted ya se encuentra inscrito en el curso: </br>" + codigocurso.capevento.nombre + ' - ' + miinscripcion.capeventoperiodo.observacion })

                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'inscripcion':
                try:
                    data['title'] = u'Registrar certificado'
                    data['cursos'] = CapEventoPeriodoIpec.objects.filter(id=160, status=True)
                    data['listaprovinvias'] = Provincia.objects.filter(pais_id=1, status=True).order_by('nombre')
                    data['currenttime'] = datetime.now()
                    return render(request, "inscripcionescursos_edcon/inscripcionescursos.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Registrar certificado'
                return render(request, "inscripcionescursos_edcon/inscripcionescursos.html", data)
            except Exception as ex:
                pass
