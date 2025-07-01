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
from posgrado.models import PreInscripcion, FormatoCarreraIpec, EvidenciasMaestrias, InteresadoMaestria
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
                    nombres = request.POST['nombres']
                    email = request.POST['email']
                    telefono = request.POST['telefono']
                    profesion = request.POST['profesion']
                    idcarrera = request.POST['id_carrera']
                    formato = FormatoCarreraIpec.objects.filter(id=idcarrera, status=True)[0]
                    interasado = InteresadoMaestria(nombre=nombres.upper(),
                                                    fecha_hora=hoy,
                                                    carrera_id=formato.carrera_id,
                                                    email=email,
                                                    profesion= profesion,
                                                    telefono= telefono)

                    interasado.save(request)
                    lista = []
                    lista.append(interasado.email)
                    lista.append(conectar_cuenta(CUENTAS_CORREOS[18][1]))
                    if formato.correomaestria:
                        lista.append(formato.correomaestria)
                    asunto = u"Petición de información de maestría"
                    send_html_mail(asunto, "emails/notificacion_interesado_ipec.html",
                                        {'sistema': 'Posgrado UNEMI', 'interasado': interasado,'formato': formato.banner},
                                        lista, [], [formato.archivo, ],
                                        cuenta=CUENTAS_CORREOS[18][1])
                    return JsonResponse({'result': 'ok', "mensaje": u"Sus datos se enviaron correctamente, por favor revisar la notificación enviada a su correo electrónico."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})

            # elif action == 'consultacedula':
            #     try:
            #         cedula = request.POST['cedula'].strip()
            #         datospersona = None
            #         provinciaid = 0
            #         cantonid = 0
            #         cantonnom = ''
            #         lugarestudio = ''
            #         carrera = ''
            #         profesion = ''
            #         institucionlabora = ''
            #         cargo = ''
            #         teleoficina = ''
            #         idgenero = 0
            #         habilitaemail = 0
            #         if Persona.objects.filter(cedula=cedula).exists():
            #             datospersona = Persona.objects.get(cedula=cedula)
            #         elif Persona.objects.filter(pasaporte=cedula).exists():
            #             datospersona = Persona.objects.get(pasaporte=cedula)
            #         if datospersona:
            #             return JsonResponse({"result": "ok", "apellido1": datospersona.apellido1, "apellido2": datospersona.apellido2,
            #                                  "nombres": datospersona.nombres, "email": datospersona.email})
            #         else:
            #             return JsonResponse({"result": "no"})
            #     except Exception as ex:
            #         transaction.set_rollback(True)
            #         return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            #
            # elif action == 'subirdocumentos':
            #     try:
            #         if 'hojavida' in request.FILES is not '' and 'copiavotacion' in request.FILES is not '' and 'copiacedula' in request.FILES is not '' and 'senescyt' in request.FILES is not '':
            #             inscripcion = PreInscripcion.objects.get(id=encrypt(request.POST['id']))
            #             inscripcion.evidencias = True
            #             inscripcion.save()
            #             evidencia = EvidenciasMaestrias(preinscripcion=inscripcion)
            #             evidencia.save()
            #         newfile = None
            #         if 'hojavida' in request.FILES is not '':
            #             newfilehojavida = request.FILES['hojavida']
            #             if newfilehojavida:
            #                 newfilesd = newfilehojavida._name
            #                 ext = newfilesd[newfilesd.rfind("."):]
            #                 if not ext in ['.doc', '.pdf', '.docx']:
            #                     return JsonResponse(
            #                         {"result": "bad", "mensaje": u"Solo se permiten archivos .doc y .pdf"})
            #                 if newfilehojavida.size > 10485760:
            #                     return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
            #                 if newfilehojavida:
            #                     newfilehojavida._name = generar_nombre("requisitoipecpreinscrito", newfilehojavida._name)
            #                 evidencia.hojavida=newfilehojavida
            #                 evidencia.save()
            #             else:
            #                 return JsonResponse({"result": "bad", "mensaje": u"Falta hoja de vida."})
            #
            #         if 'copiavotacion' in request.FILES is not '':
            #             newfilecopiavotacion = request.FILES['copiavotacion']
            #             if newfilecopiavotacion:
            #                 newfilesd = newfilecopiavotacion._name
            #                 ext = newfilesd[newfilesd.rfind("."):]
            #                 if not ext in ['.doc', '.pdf', '.docx']:
            #                     return JsonResponse(
            #                         {"result": "bad", "mensaje": u"Solo se permiten archivos .doc y .pdf"})
            #                 if newfilecopiavotacion.size > 10485760:
            #                     return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
            #                 if newfilecopiavotacion:
            #                     newfilecopiavotacion._name = generar_nombre("requisitoipecpreinscrito", newfilecopiavotacion._name)
            #                 evidencia.copiavotacion = newfilecopiavotacion
            #                 evidencia.save()
            #         else:
            #             return JsonResponse({"result": "bad", "mensaje": u"Falta copia de votación."})
            #
            #         if 'copiacedula' in request.FILES is not '':
            #             newfilecopiacedula = request.FILES['copiacedula']
            #             if newfilecopiacedula:
            #                 newfilesd = newfilecopiacedula._name
            #                 ext = newfilesd[newfilesd.rfind("."):]
            #                 if not ext in ['.doc', '.pdf', '.docx']:
            #                     return JsonResponse(
            #                         {"result": "bad", "mensaje": u"Solo se permiten archivos .doc y .pdf"})
            #                 if newfilecopiacedula.size > 10485760:
            #                     return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
            #                 if newfilecopiacedula:
            #                     newfilecopiacedula._name = generar_nombre("requisitoipecpreinscrito", newfilecopiacedula._name)
            #                 evidencia.copiacedula = newfilecopiacedula
            #                 evidencia.save()
            #         else:
            #             return JsonResponse({"result": "bad", "mensaje": u"Falta copia de cédula."})
            #
            #         if 'senescyt' in request.FILES is not '':
            #             newfilesenescyt= request.FILES['senescyt']
            #             if newfilesenescyt:
            #                 newfilesd = newfilesenescyt._name
            #                 ext = newfilesd[newfilesd.rfind("."):]
            #                 if not ext in ['.doc', '.pdf', '.docx']:
            #                     return JsonResponse(
            #                         {"result": "bad", "mensaje": u"Solo se permiten archivos .doc y .pdf"})
            #                 if newfilesenescyt.size > 10485760:
            #                     return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
            #                 if newfilesenescyt:
            #                     newfilesenescyt._name = generar_nombre("requisitoipecpreinscrito", newfilesenescyt._name)
            #                 evidencia.senescyt = newfilesenescyt
            #                 evidencia.save()
            #         else:
            #             return JsonResponse({"result": "bad", "mensaje": u"Falta certificado de senescyt."})
            #
            #         if 'lenguaextranjera' in request.FILES:
            #             newfilelenguaextranjera= request.FILES['lenguaextranjera']
            #             if newfilelenguaextranjera:
            #                 newfilesd = newfilelenguaextranjera._name
            #                 ext = newfilesd[newfilesd.rfind("."):]
            #                 if not ext in ['.doc', '.pdf', '.docx']:
            #                     return JsonResponse(
            #                         {"result": "bad", "mensaje": u"Solo se permiten archivos .doc y .pdf"})
            #                 if newfilelenguaextranjera.size > 10485760:
            #                     return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
            #                 if newfilelenguaextranjera:
            #                     newfilelenguaextranjera._name = generar_nombre("requisitoipecpreinscrito", newfilelenguaextranjera._name)
            #                 evidencia.lenguaextranjera = newfilelenguaextranjera
            #                 evidencia.save()
            #         return JsonResponse({"result": "ok"})
            #     except Exception as ex:
            #         transaction.set_rollback(True)
            #         return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos, falta uno o varios documentos."})
            #
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        if 'action' in request.GET:
            action = request.GET['action']
            # if action == 'inscripcion':
            #     try:
            #         data['title'] = u'Registro Admisión-MAESTRÍAS'
            #         return render(request, "interesadosmaestria/interesadosmaestria.html", data)
            #     except Exception as ex:
            #         pass
            # elif action == 'subirdocumentos':
            #     try:
            #         data['title'] = u'Subir documentos'
            #         data['inscripcion'] =inscripcion= PreInscripcion.objects.get(pk=int(encrypt(request.GET['id'])), enviocorreo = True)
            #         data['detalle'] = detalle=inscripcion.evidenciasmaestrias_set.filter(status=True)[0] if inscripcion.evidenciasmaestrias_set.filter(status=True).exists() else None
            #         if detalle:
            #             initial=model_to_dict(detalle)
            #             form = RegistroRequisitosMaestriaForm1(initial=initial)
            #         else:
            #             form = RegistroRequisitosMaestriaForm()
            #         data['form'] = form
            #         return render(request, "interesadosmaestria/requisitosmaestria.html", data)
            #         # return render(request, "interesadosmaestria/subirdocumentos.html", data)
            #         # return render(request, "interesadosmaestria/interesadosmaestria.html", data)
            #     except Exception as ex:
            #         pass
            return HttpResponseRedirect(request.path)
        else:
            try:
                #data['carreras'] = Carrera.objects.filter(status=True,coordinacion__id=7)
                data['idcarrera'] = request.GET['ic']
                data['carreras'] = FormatoCarreraIpec.objects.filter(status=True).order_by('-id')
                return render(request, "interesados/interesados.html", data)
            except Exception as ex:
                pass


# def interesados(request):
#     form = RegistroRequisitosMaestriaForm()
#     if request.method == 'POST':
#         form = RegistroRequisitosMaestriaForm(request.POST, request.FILES)
#         if form.is_valid():
#             form.save()
#     return render(request, "alu_requisitosmaestria/requisitosmaestria.html", locals())
#
