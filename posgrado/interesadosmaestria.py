# -*- coding: latin-1 -*-
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.db.models.query_utils import Q
from datetime import datetime
from decorators import last_access
from posgrado.forms import RegistroRequisitosMaestriaForm, RegistroRequisitosMaestriaForm1

from sga.funciones import generar_nombre
from sga.models import Persona,  Carrera, CUENTAS_CORREOS
from posgrado.models import PreInscripcion, FormatoCarreraIpec, EvidenciasMaestrias, CohorteMaestria
from django.forms import model_to_dict
from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt


@last_access
@transaction.atomic()
def view(request):
    data = {}
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']
            if action == 'addregistro':
                try:
                    hoy = datetime.now().date()
                    cedula = request.POST['cedula'].strip()
                    tipoiden = request.POST['id_tipoiden']
                    nombres = request.POST['nombres']
                    apellido1 = request.POST['apellido1']
                    apellido2 = request.POST['apellido2']
                    carrera = request.POST['carrera']
                    email = request.POST['email']
                    telefono = request.POST['telefono']
                    datospersona=None
                    formato = FormatoCarreraIpec.objects.filter(carrera=carrera, status=True)[0]
                    if tipoiden == '1':
                        if Persona.objects.filter(Q(cedula__icontains=cedula) |Q(pasaporte__icontains=cedula)).exists():
                            datospersona = Persona.objects.get(Q(cedula__icontains=cedula) |Q(pasaporte__icontains=cedula))
                            datospersona.email = email
                            datospersona.telefono = telefono
                            datospersona.save(request)
                        else:
                            datospersona = Persona(cedula=cedula,
                                                   nombres=nombres,
                                                   apellido1=apellido1,
                                                   apellido2=apellido2,
                                                   email=email,
                                                   telefono=telefono,
                                                   nacimiento=datetime.now().date()
                                                   )
                            datospersona.save(request)

                    if tipoiden == '2':
                        if Persona.objects.filter(Q(cedula__icontains=cedula) | Q(pasaporte__icontains=cedula)).exists():
                            datospersona = Persona.objects.get(Q(cedula__icontains=cedula) |Q(pasaporte__icontains=cedula))
                            datospersona.email = email
                            datospersona.telefono = telefono
                            datospersona.save(request)
                        else:
                            datospersona = Persona(pasaporte=cedula,
                                                   nombres=nombres,
                                                   apellido1=apellido1,
                                                   apellido2=apellido2,
                                                   email=email,
                                                   telefono=telefono,
                                                   nacimiento=datetime.now().date()
                                                   )
                            datospersona.save(request)

                    if datospersona:
                        if datospersona.preinscripcion_set.filter(carrera_id=carrera, status=True).exists():
                            return JsonResponse({'result': 'bad', "mensaje": u"Usted ya se encuentra inscrito."})
                        else:
                            preinscrito = PreInscripcion(persona=datospersona,
                                                         fecha_hora=hoy,
                                                         carrera_id=carrera,
                                                         formato= formato
                                                         )

                            preinscrito.save(request)

                        lista = []
                        if preinscrito.persona.emailinst:
                            lista.append(preinscrito.persona.emailinst)
                        if preinscrito.persona.email:
                            lista.append(preinscrito.persona.email)
                        if formato.correomaestria:
                            lista.append(formato.correomaestria)
                        lista.append(conectar_cuenta(CUENTAS_CORREOS[18][1]))
                        asunto = u"Confirmación de pre-inscripción de maestría"
                        send_html_mail(asunto, "emails/notificacion_preinscripcion_ipec.html",
                                            {'sistema': 'Posgrado UNEMI', 'preinscrito': preinscrito,'formato': formato.banner},
                                            lista, [], [],
                                            cuenta=CUENTAS_CORREOS[18][1])

                    # if carrera == '60':
                    #     lista = []
                    #     lista.append('maestria.economia-desarrolloproductivo@unemi.edu.ec')
                    #     asunto = u"Nueva inscripción a la carrera"
                    #     send_html_mail(asunto, "emails/notificacion_nueva_preinscripcion_ipec.html",
                    #                    {'sistema': 'Posgrado', 'preinscrito': preinscrito},
                    #                    lista, [], [],
                    #                    cuenta=CUENTAS_CORREOS[18][1])

                    #else:

                        return JsonResponse({'result': 'ok', "mensaje": u"Sus datos se enviaron correctamente, por favor revisar la notificación enviada a su correo."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})

            elif action == 'consultacedula':
                try:
                    cedula = request.POST['cedula'].strip()
                    datospersona = None
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
                    elif Persona.objects.filter(pasaporte=cedula).exists():
                        datospersona = Persona.objects.get(pasaporte=cedula)
                    if datospersona:
                        if datospersona.sexo:
                            idgenero = datospersona.sexo_id
                        return JsonResponse({"result": "ok", "apellido1": datospersona.apellido1, "apellido2": datospersona.apellido2,
                                             "nombres": datospersona.nombres, "email": datospersona.email, "telefono": datospersona.telefono, "idgenero": idgenero})
                    else:
                        return JsonResponse({"result": "no"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'subirdocumentos':
                try:
                    if 'hojavida' in request.FILES != '' and 'copiavotacion' in request.FILES != '' and 'copiacedula' in request.FILES != '' and 'senescyt' in request.FILES != '':
                        inscripcion = PreInscripcion.objects.get(id=encrypt(request.POST['id']))
                        inscripcion.evidencias = True
                        inscripcion.save()
                        evidencia = EvidenciasMaestrias(preinscripcion=inscripcion)
                        evidencia.save()
                    newfile = None
                    if 'hojavida' in request.FILES != '':
                        newfilehojavida = request.FILES['hojavida']
                        if newfilehojavida:
                            newfilesd = newfilehojavida._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if not ext in ['.doc', '.pdf', '.docx']:
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"Solo se permiten archivos .doc y .pdf"})
                            if newfilehojavida.size > 10485760:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                            if newfilehojavida:
                                newfilehojavida._name = generar_nombre("requisitoipecpreinscrito", newfilehojavida._name)
                            evidencia.hojavida=newfilehojavida
                            evidencia.save()
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Falta hoja de vida."})

                    if 'copiavotacion' in request.FILES != '':
                        newfilecopiavotacion = request.FILES['copiavotacion']
                        if newfilecopiavotacion:
                            newfilesd = newfilecopiavotacion._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if not ext in ['.doc', '.pdf', '.docx']:
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"Solo se permiten archivos .doc y .pdf"})
                            if newfilecopiavotacion.size > 10485760:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                            if newfilecopiavotacion:
                                newfilecopiavotacion._name = generar_nombre("requisitoipecpreinscrito", newfilecopiavotacion._name)
                            evidencia.copiavotacion = newfilecopiavotacion
                            evidencia.save()
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Falta copia de votación."})

                    if 'copiacedula' in request.FILES != '':
                        newfilecopiacedula = request.FILES['copiacedula']
                        if newfilecopiacedula:
                            newfilesd = newfilecopiacedula._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if not ext in ['.doc', '.pdf', '.docx']:
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"Solo se permiten archivos .doc y .pdf"})
                            if newfilecopiacedula.size > 10485760:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                            if newfilecopiacedula:
                                newfilecopiacedula._name = generar_nombre("requisitoipecpreinscrito", newfilecopiacedula._name)
                            evidencia.copiacedula = newfilecopiacedula
                            evidencia.save()
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Falta copia de cédula."})

                    if 'senescyt' in request.FILES != '':
                        newfilesenescyt= request.FILES['senescyt']
                        if newfilesenescyt:
                            newfilesd = newfilesenescyt._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if not ext in ['.doc', '.pdf', '.docx']:
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"Solo se permiten archivos .doc y .pdf"})
                            if newfilesenescyt.size > 10485760:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                            if newfilesenescyt:
                                newfilesenescyt._name = generar_nombre("requisitoipecpreinscrito", newfilesenescyt._name)
                            evidencia.senescyt = newfilesenescyt
                            evidencia.save()
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Falta certificado de senescyt."})

                    if 'lenguaextranjera' in request.FILES:
                        newfilelenguaextranjera= request.FILES['lenguaextranjera']
                        if newfilelenguaextranjera:
                            newfilesd = newfilelenguaextranjera._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if not ext in ['.doc', '.pdf', '.docx']:
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"Solo se permiten archivos .doc y .pdf"})
                            if newfilelenguaextranjera.size > 10485760:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                            if newfilelenguaextranjera:
                                newfilelenguaextranjera._name = generar_nombre("requisitoipecpreinscrito", newfilelenguaextranjera._name)
                            evidencia.lenguaextranjera = newfilelenguaextranjera
                            evidencia.save()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos, falta uno o varios documentos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'inscripcion':
                try:
                    data['title'] = u'Registro Admisión-MAESTRÍAS'
                    return render(request, "interesadosmaestria/interesadosmaestria.html", data)
                except Exception as ex:
                    pass
            elif action == 'subirdocumentos':
                try:
                    data['title'] = u'Requisitos básicos para admisión'
                    data['inscripcion'] =inscripcion= PreInscripcion.objects.get(pk=int(encrypt(request.GET['id'])), enviocorreo = True)
                    data['detalle'] = detalle=inscripcion.evidenciasmaestrias_set.filter(status=True)[0] if inscripcion.evidenciasmaestrias_set.filter(status=True).exists() else None
                    if detalle:
                        initial=model_to_dict(detalle)
                        form = RegistroRequisitosMaestriaForm1(initial=initial)
                    else:
                        form = RegistroRequisitosMaestriaForm()
                    data['form'] = form
                    return render(request, "interesadosmaestria/requisitosmaestria.html", data)
                    # return render(request, "interesadosmaestria/subirdocumentos.html", data)
                    # return render(request, "interesadosmaestria/interesadosmaestria.html", data)
                except Exception as ex:
                    pass
            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Registrar certificado'
                hoy = datetime.now().date()
                data['listadomaestriascohorte'] = CohorteMaestria.objects.filter(activo=True, fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, status=True).order_by('id')
                data['carreras'] = FormatoCarreraIpec.objects.filter(carrera__id__in=[154,155], status=True).order_by('-id')
                return render(request, "interesadosmaestria/interesadosmaestria.html", data)
            except Exception as ex:
                pass


def requisitos_maestria_archivos(request):
    form = RegistroRequisitosMaestriaForm()
    if request.method == 'POST':
        form = RegistroRequisitosMaestriaForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
    return render(request, "alu_requisitosmaestria/requisitosmaestria.html", locals())

