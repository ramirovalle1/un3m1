# -*- coding: latin-1 -*-
import json
import random
from datetime import datetime
from decimal import Decimal

from django.db.models import Sum, F
from django.db.models.query_utils import Q
import xlwt
from django.utils.formats import number_format
from xlwt import *
from xlwt import easyxf
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.context import Context
from django.template.loader import get_template

from decorators import secure_module, last_access
from posgrado.models import CohorteMaestria
from sga.admin import ModuloGrupoAdmin
from sga.commonviews import adduserdata
from sga.forms import ConfiguracionDescuentoPosgradoForm, DescuentoPosgradoForm, \
    ConfiguracionDescuentoPosgradoDetalleForm, ConfiguracionPeriodoPosgradoDetalleForm, \
    ConfiguracionRequisitoPosgradoDetalleForm, EvidenciaLeyHumanitariaForm
from sga.funciones import log, MiPaginador, variable_valor, generar_nombre, cuenta_email_disponible_para_envio, \
    validar_archivo, remover_caracteres_especiales_unicode
from sga.models import TemaTitulacionPosgradoMatricula, \
    ConfiguracionDescuentoPosgrado, DescuentoPosgrado, DetalleConfiguracionDescuentoPosgrado, Periodo, \
    PeriodoDetalleConfiguracionDescuentoPosgrado, RequisitosDetalleConfiguracionDescuentoPosgrado, \
    DescuentoPosgradoMatricula, EvidenciasDescuentoPosgradoMatricula, miinstitucion, \
    DetalleEvidenciaDescuentoPosgradoMatricula, Matricula, ESTADO, Inscripcion, DescuentoPosgradoMatriculaRecorrido, \
    CUENTAS_CORREOS, ESTADO_BECA_POSGRADO
from sga.tasks import send_html_mail, conectar_cuenta
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
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

    grupobecaposgradoube = persona.grupo_becas_posgrado_bienestar()

    # periodo = request.session['periodo']
    carreras = persona.mis_carreras()
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = ConfiguracionDescuentoPosgradoForm(request.POST, request.FILES)
                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        if newfile.size > 4194304:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 4 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == ".doc" or ext == ".docx" or ext == ".pdf":
                                newfile._name = generar_nombre("formato_", newfile._name)
                            else:
                                return JsonResponse({"result": "bad","mensaje": u"Error, archivo de Formato solo en .pdf, .doc, docx."})

                if f.is_valid():
                    configuracion = ConfiguracionDescuentoPosgrado(descripcion=f.cleaned_data['descripcion'],
                                                                   fechainicio=f.cleaned_data['fechainicio'],
                                                                   fechafin=f.cleaned_data['fechafin'],
                                                                   porcentaje=f.cleaned_data['porcentaje'],
                                                                   fecharige=f.cleaned_data['fecharige'],
                                                                   fechafinrequisito=f.cleaned_data['fechafinrequisito'],
                                                                   activo=f.cleaned_data['activo'])
                    configuracion.save(request)
                    if newfile:
                        configuracion.archivo = newfile
                        configuracion.save(request)

                    log(u'Adiciono configuracion Descuento posgrado: %s' % configuracion, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'adddescuento':
            try:
                if 'archivo' in request.FILES:
                    da = request.FILES['archivo']
                    if da.size > 20971520:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 20 Mb."})
                    else:
                        newfileotro = request.FILES['archivo']
                        newfilesotrod = newfileotro._name
                        ext = newfilesotrod[newfilesotrod.rfind("."):]
                        if ext.lower() == '.pdf':
                            newfileotro._name = generar_nombre("archivodescuento_", newfileotro._name)
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo solo en .pdf."})
                f = DescuentoPosgradoForm(request.POST, request.FILES)
                if f.is_valid():
                    rubrica = DescuentoPosgrado(nombre=f.cleaned_data['nombre'],
                                                activo=f.cleaned_data['activo'])
                    rubrica.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("archivodescuento_", newfile._name)
                        rubrica.archivo = newfile
                        rubrica.save(request)
                    log(u'Adiciono descuento posgrado: %s' % rubrica, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'edit':
            try:
                configuracion = ConfiguracionDescuentoPosgrado.objects.get(pk=request.POST['id'])
                f = ConfiguracionDescuentoPosgradoForm(request.POST, request.FILES)
                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        if newfile.size > 4194304:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 4 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == ".doc" or ext == ".docx" or ext == ".pdf":
                                newfile._name = generar_nombre("formato_", newfile._name)
                            else:
                                return JsonResponse({"result": "bad",
                                                     "mensaje": u"Error, archivo de Formato solo en .pdf, .doc, docx."})

                if f.is_valid():
                    configuracion.descripcion = f.cleaned_data['descripcion']
                    configuracion.fechainicio = f.cleaned_data['fechainicio']
                    configuracion.fechafin = f.cleaned_data['fechafin']
                    configuracion.porcentaje = f.cleaned_data['porcentaje']
                    configuracion.fecharige = f.cleaned_data['fecharige']
                    configuracion.fechafinrequisito = f.cleaned_data['fechafinrequisito']
                    configuracion.activo = f.cleaned_data['activo']
                    if newfile:
                        configuracion.archivo = newfile
                    configuracion.save(request)
                    log(u'Modifico configuracion Descuento posgrado: %s' % configuracion, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editrequisito':
            try:
                configuracion = RequisitosDetalleConfiguracionDescuentoPosgrado.objects.get(pk=request.POST['id'])
                f = ConfiguracionRequisitoPosgradoDetalleForm(request.POST)
                if f.is_valid():
                    configuracion.descripcion = f.cleaned_data['descripcion']
                    configuracion.requisito = f.cleaned_data['requisito']
                    configuracion.save(request)
                    log(u'Modifico requisito descuento posgrado: %s' % configuracion, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editdescuento':
            try:
                if 'archivo' in request.FILES:
                    da = request.FILES['archivo']
                    if da.size > 20971520:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 20 Mb."})
                    else:
                        newfileotro = request.FILES['archivo']
                        newfilesotrod = newfileotro._name
                        ext = newfilesotrod[newfilesotrod.rfind("."):]
                        if ext.lower() == '.pdf':
                            newfileotro._name = generar_nombre("archivodescuento_", newfileotro._name)
                        else:
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"Error, archivo solo en .pdf."})
                rubrica = DescuentoPosgrado.objects.get(pk=request.POST['id'])
                f = DescuentoPosgradoForm(request.POST, request.FILES)
                if f.is_valid():
                    rubrica.nombre = f.cleaned_data['nombre']
                    rubrica.activo = f.cleaned_data['activo']
                    rubrica.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("archivodescuento_", newfile._name)
                        rubrica.archivo = newfile
                        rubrica.save(request)
                    log(u'Modifico descuento posgrado: %s' % rubrica, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'adddescuentos':
            try:
                configuracion = ConfiguracionDescuentoPosgrado.objects.get(pk=request.POST['id'])
                configuracion.detalleconfiguraciondescuentoposgrado_set.all().delete()
                datos = json.loads(request.POST['lista_items1'])
                for elemento in datos:
                    detalleconfiguraciondescuentoposgrado = DetalleConfiguracionDescuentoPosgrado(configuraciondescuentoposgrado=configuracion,
                                                                                                  descuentoposgrado_id=int(elemento['id']))
                    detalleconfiguraciondescuentoposgrado.save(request)

                log(u'Modifico descuento configuracion posgrado: %s' % configuracion, request, "edit")
                return JsonResponse({"result": "ok"})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addperiodos':
            try:
                configuracion = DetalleConfiguracionDescuentoPosgrado.objects.get(pk=request.POST['id'])
                configuracion.periododetalleconfiguraciondescuentoposgrado_set.all().delete()
                datos = json.loads(request.POST['lista_items1'])
                for elemento in datos:
                    periododetalleconfiguraciondescuentoposgrado = PeriodoDetalleConfiguracionDescuentoPosgrado(detalleconfiguraciondescuentoposgrado=configuracion,
                                                                                                                periodo_id=int(elemento['id']))
                    periododetalleconfiguraciondescuentoposgrado.save(request)

                log(u'Modifico periodo configuracion posgrado: %s' % configuracion, request, "edit")
                return JsonResponse({"result": "ok"})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addrequisito':
            try:
                configuracion = DetalleConfiguracionDescuentoPosgrado.objects.get(pk=request.POST['id'])
                f = ConfiguracionRequisitoPosgradoDetalleForm(request.POST)
                if f.is_valid():
                    requisitosdetalleconfiguraciondescuentoposgrado = RequisitosDetalleConfiguracionDescuentoPosgrado(detalleconfiguraciondescuentoposgrado=configuracion,
                                                                                                                      requisito=f.cleaned_data['requisito'],
                                                                                                                      descripcion=f.cleaned_data['descripcion'])
                    requisitosdetalleconfiguraciondescuentoposgrado.save(request)
                    log(u'Ingreso requisito descuento posgrado: %s' % configuracion, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delete':
            try:
                configuracion = ConfiguracionDescuentoPosgrado.objects.get(pk=int(request.POST['id']), status=True)
                if not configuracion.en_uso():
                    log(u'Eliminó la configuración descuento: %s' % configuracion, request, "del")
                    configuracion.delete()
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"No se puede eliminar ya se encuentra en uso."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleterequisito':
            try:
                configuracion = RequisitosDetalleConfiguracionDescuentoPosgrado.objects.get(pk=int(request.POST['id']), status=True)
                if not configuracion.en_uso():
                    log(u'Eliminó requisito configuración descuento: %s' % configuracion, request, "del")
                    configuracion.delete()
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"No se puede eliminar ya se encuentra en uso."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'detalleaprobacion':
            try:
                data['tema'] = tema = TemaTitulacionPosgradoMatricula.objects.get(pk=int(request.POST['id']))
                data['historialaprobacion'] = tema.tematitulacionposgradomatriculahistorial_set.filter(
                    status=True).order_by('-id')
                data['aprobar'] = variable_valor('APROBAR_SILABO')
                data['rechazar'] = variable_valor('RECHAZAR_SILABO')
                data['pendiente'] = variable_valor('PENDIENTE_SILABO')
                template = get_template("adm_configuracionpropuesta/detalleaprobacion.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                pass

        elif action == 'aprobarrequisitos':
            try:
                inscripcioncohorte = DescuentoPosgradoMatricula.objects.get(pk=int(request.POST['id']),status=True)
                inscripcioncohorte.estado=2
                inscripcioncohorte.fecha_aprobador = datetime.now()
                inscripcioncohorte.persona_aprobador = persona
                inscripcioncohorte.save(request)
                if inscripcioncohorte.matricula:
                    correropersona = inscripcioncohorte.matricula.inscripcion.persona.emailpersonal()
                else:
                    correropersona = inscripcioncohorte.inscripcioncohorte.inscripcionaspirante.persona.emailpersonal()
                log(u'Aprobo solicitud descuento matricula: %s' % (inscripcioncohorte), request, "add")
                send_html_mail("Aprobado Descuento-UNEMI.", "emails/registroaprobaciondescuento.html",{'sistema': u'Admision - UNEMI', 'fecha': datetime.now().date(),'hora': datetime.now().time(), 't': miinstitucion()}, correropersona, [],cuenta=variable_valor('CUENTAS_CORREOS')[16])
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u'Error al guardar los datos'})

        elif action == 'rechazarrequisitos':
            try:
                inscripcioncohorte = DescuentoPosgradoMatricula.objects.get(pk=int(request.POST['id']),status=True)
                inscripcioncohorte.estado=3
                inscripcioncohorte.save(request)
                if inscripcioncohorte.matricula:
                    correropersona = inscripcioncohorte.matricula.inscripcion.persona.emailpersonal()
                else:
                    correropersona = inscripcioncohorte.inscripcioncohorte.inscripcionaspirante.persona.emailpersonal()
                log(u'Rechazo solicitud descuento matricula: %s' % (inscripcioncohorte), request, "add")
                send_html_mail("Rechazo Descuento-UNEMI.", "emails/registrorechazodescuento.html",{'sistema': u'Admision - UNEMI', 'fecha': datetime.now().date(),'hora': datetime.now().time(), 't': miinstitucion()}, correropersona, [],cuenta=variable_valor('CUENTAS_CORREOS')[16])
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u'Error al guardar los datos'})

        elif action == 'aprobarrequisitoevidencia':
            try:
                detalleevidencia = DetalleEvidenciaDescuentoPosgradoMatricula.objects.get(pk=request.POST['idevidencia'])
                detalleevidencia.observacion_aprobacion = request.POST['id_observacion']
                detalleevidencia.persona = persona
                detalleevidencia.estado_aprobacion = request.POST['id_estado']
                detalleevidencia.fecha_aprobacion = datetime.now()
                detalleevidencia.save(request)
                log(u'Actualizó observacion evidencia descuento matricula: %s' % (detalleevidencia), request, "add")
                #enviar mail cuando le rechazan
                if detalleevidencia.estado_aprobacion == 3:
                    send_html_mail("Rechazado Evidencia-UNEMI.", "emails/registrorechazadoevidenciadescuento.html",{'sistema': u'Admision - UNEMI', 'fecha': datetime.now().date(),'hora': datetime.now().time(), 't': miinstitucion(), 'observacion': detalleevidencia.observacion_aprobacion},detalleevidencia.persona.emailpersonal(), [],cuenta=variable_valor('CUENTAS_CORREOS')[16])
                # cohorte = detalleevidencia.evidencia.requisitosdetalleconfiguraciondescuentoposgrado.detalleconfiguraciondescuentoposgrado
                # inscripcioncohorte = detalleevidencia.evidencia.descuentoposgradomatricula
                # # verificar si ya esta todo aprobado para enviar correo de aprobacion
                # bandera = 0
                # for re in cohorte.requisitosdetalleconfiguraciondescuentoposgrado_set.filter(status=True):
                #     ingresoevidencias = re.detalle_requisitosmaestriacohorte(inscripcioncohorte)
                #     if ingresoevidencias:
                #         if not ingresoevidencias.ultima_evidencia().estado_aprobacion == 2:
                #             bandera = 1
                #     else:
                #         bandera = 1
                # if bandera == 0:
                #     # inscripcioncoohorte = InscripcionCohorte.objects.get(pk=request.POST['idinscripcioncohorte'])
                #     inscripcioncohorte.fecha_aprobador = datetime.now()
                #     inscripcioncohorte.estado = 2
                #     inscripcioncohorte.persona_aprobador = persona
                #     inscripcioncohorte.save(request)
                #     log(u'Envio email aprobacion, masivo: %s' % (inscripcioncohorte), request, "add")
                #     send_html_mail("Aprobado Admision-UNEMI.", "emails/registroaprobadomasivo.html",{'sistema': u'Admision - UNEMI', 'fecha': datetime.now().date(),'hora': datetime.now().time(), 't': miinstitucion()},inscripcioncohorte.inscripcionaspirante.persona.emailpersonal(), [],cuenta=variable_valor('CUENTAS_CORREOS')[16])
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar."})

        elif action == 'informefinal':
            try:
                data = {}
                data['tema'] = tema = DescuentoPosgradoMatricula.objects.get(status=True, id=int(request.POST['idtema']))

                if tema.fecha_aprobador.date() <= datetime.strptime('2020-11-30', '%Y-%m-%d').date():
                    nombredirector = "Del Campo Saltos Guillermo Segundo"
                    cargo = "Director de Investigación y Posgrado"
                elif tema.fecha_aprobador.date() <= datetime.strptime('2021-09-30', '%Y-%m-%d').date():
                    nombredirector = "Chacón Luna Ana Eva"
                    cargo = "Directora de Investigación y Posgrado"
                else:
                    nombredirector = "Sylva Lazo Maritza Yesenia"
                    cargo = "Directora de Investigación y Posgrado"

                data['nombredirector'] = nombredirector
                data['cargo'] = cargo

                if tema.numerosolicitud == 0:
                    numerommayor = DescuentoPosgradoMatricula.objects.filter(status=True).order_by('-numerosolicitud')[0]
                    tema.numerosolicitud = numerommayor.numerosolicitud + 1
                    tema.save(request)
                # data['detalleevidencia'] = DetalleEvidenciaDescuentoPosgradoMatricula.objects.filter(evidencia__descuentoposgradomatricula=tema, status=True, estadorevision=1).order_by('evidencia__requisitosdetalleconfiguraciondescuentoposgrado__descripcion')
                data['requisitos'] = tema.evidenciasdescuentoposgradomatricula_set.filter(status=True).order_by('id')
                numero = len(str(tema.numerosolicitud))
                data['numero'] = numero
                return conviert_html_to_pdf(
                    'adm_configuraciondescuento/informefinal_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as ex:
                pass

        elif action == 'validarsolicitudbeca':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                # Consulto la solicitud de beca
                solicitudbeca = DescuentoPosgradoMatricula.objects.get(pk=int(encrypt(request.POST['id'])))
                tipobeca = solicitudbeca.detalleconfiguraciondescuentoposgrado.descuentoposgrado.id
                solicitante = solicitudbeca.inscripcioncohorte.inscripcion.persona

                # Obtengo los valores de los campos del formulario
                estadosolicitud = int(request.POST['estadosolicitud'])
                observacion = request.POST['observacion'].strip().upper()
                porcentajedescuento = request.POST['porcentajedescuento']
                valorbeca = request.POST['valorbeca']

                # Validar saldo de presupuesto para becas disponible
                saldo = solicitudbeca.inscripcioncohorte.cohortes.saldo_disponible_presupuestobecas()
                if Decimal(valorbeca).quantize(Decimal('.01')) > saldo:
                    msgsaldo = "<strong>Saldo presupuesto para becas: $ " + number_format(str(saldo), force_grouping=True) + " (" + solicitudbeca.inscripcioncohorte.inscripcion.carrera.nombre + " - " + solicitudbeca.inscripcioncohorte.cohortes.descripcion + ")</strong>"
                    return JsonResponse({"result": "bad", "mensaje": u"El saldo disponible del presupuesto para becas es insuficiente", "msgsaldo": msgsaldo})

                promedio = puntajeficha = porcentajediscapacidad = 0

                if tipobeca == 5:
                    promedio = request.POST['promedio']
                elif tipobeca == 6:
                    puntajeficha = request.POST['puntajeficha']
                else:
                    porcentajediscapacidad= request.POST['porcentajediscapacidad']

                # Obtengo los valores de los campos tipo arreglo del formulario
                idevidencias = request.POST.getlist('idevidencia[]')
                estados = request.POST.getlist('estadorequisito[]')
                observaciones = request.POST.getlist('observacionreg[]')

                # Actualiza la solicitud
                solicitudbeca.estado = estadosolicitud

                # Si es validada
                if estadosolicitud == 4:
                    observacion = 'VALIDADA POR POSGRADO'
                    solicitudbeca.puntajeficha = puntajeficha
                    solicitudbeca.promedio = promedio
                    solicitudbeca.gradodiscapacidad = porcentajediscapacidad
                    solicitudbeca.porcentajedescuento = porcentajedescuento
                    solicitudbeca.valordescuento = valorbeca
                    if tipobeca == 5 or tipobeca == 7:
                        solicitudbeca.aplicabeca = 1
                    else:
                        solicitudbeca.aplicabeca = 3
                        solicitudbeca.remitidodbu = True

                solicitudbeca.save(request)

                # Guardo el recorrido
                recorridosolicitud = DescuentoPosgradoMatriculaRecorrido(
                    descuentoposgradomatricula=solicitudbeca,
                    fecha=datetime.now().date(),
                    persona=persona,
                    observacion=observacion,
                    estado=estadosolicitud
                )
                recorridosolicitud.save(request)

                # Si es Validada y tipo de beca es por Alto Rendimiento o Discapacidad propia entonces poner estado APTO PARA BECA
                if estadosolicitud == 4 and tipobeca in [5, 7]:
                    solicitudbeca.estado = 8
                    solicitudbeca.save(request)

                    # Guardo el recorrido
                    recorridosolicitud = DescuentoPosgradoMatriculaRecorrido(
                        descuentoposgradomatricula=solicitudbeca,
                        fecha=datetime.now().date(),
                        persona=persona,
                        observacion='APTO PARA APLICAR A BECA',
                        estado=8
                    )
                    recorridosolicitud.save(request)

                # Actualizo los detalle de los requisitos
                for idevidencia, estado, observacion in zip(idevidencias, estados, observaciones):
                    # Consulto la evidencia
                    evidencia = EvidenciasDescuentoPosgradoMatricula.objects.get(pk=idevidencia)

                    # Consulto el ultimo detalle de la evidencia
                    detalleevidencia = evidencia.ultima_evidencia()

                    # Actualizo detalle de evidencia
                    detalleevidencia.persona = persona
                    detalleevidencia.fecha_aprobacion = datetime.now()
                    detalleevidencia.observacion_aprobacion = observacion
                    detalleevidencia.estado_aprobacion = estado
                    detalleevidencia.save(request)


                # Envio de e-mail de notificacion al solicitante
                # listacuentascorreo = [23, 24, 25, 26, 27]
                # posgrado1_unemi@unemi.edu.ec
                # posgrado2_unemi@unemi.edu.ec
                # posgrado3_unemi@unemi.edu.ec
                # posgrado4_unemi@unemi.edu.ec
                # posgrado5_unemi@unemi.edu.ec
                #
                listacuentascorreo = [18]  # posgrado@unemi.edu.ec

                lista_email_envio = solicitante.lista_emails_envio()

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                if estadosolicitud == 4:
                    msg = "Validó"
                    tituloemail = "Solicitud de Beca de Posgrado - Validada"
                    tiponotificacion = "VALIDADA"
                elif estadosolicitud == 3:
                    msg = "Rechazó"
                    tituloemail = "Solicitud de Beca de Posgrado - Rechazada"
                    tiponotificacion = "RECHAZADA"
                else:
                    msg = "Registró novedad a la"
                    tituloemail = "Solicitud de Beca de Posgrado con Novedades"
                    tiponotificacion = "NOVEDAD"


                send_html_mail(tituloemail,
                               "emails/notificacion_solicitud_becaposgrado.html",
                               {'sistema': u'Posgrado UNEMI',
                                'fecha': fechaenvio,
                                'hora': horaenvio,
                                'saludo': 'Estimada' if solicitante.sexo_id == 1 else 'Estimado',
                                'solicitante': solicitante.nombre_completo_inverso(),
                                'tiponotificacion': tiponotificacion,
                                'observaciones': observacion,
                                't': miinstitucion()
                                },
                               lista_email_envio,
                               [],
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                log(u'%s solicitud de beca de posgrado: %s' % (msg, solicitudbeca), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'verificarsolicitudbeca':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                # Consulto la solicitud de beca
                solicitudbeca = DescuentoPosgradoMatricula.objects.get(pk=int(encrypt(request.POST['id'])))

                # tipobeca = solicitudbeca.detalleconfiguraciondescuentoposgrado.descuentoposgrado.id

                solicitante = solicitudbeca.inscripcioncohorte.inscripcion.persona

                # Obtengo los valores de los campos del formulario
                visitarealizada = 'visitarealizada' in request.POST
                estadosolicitud = int(request.POST['estadosolicitud'])
                observacion = request.POST['observacion'].strip().upper()
                archivo = request.FILES['archivoinforme']
                descripcionarchivo = 'Archivo del informe'

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                archivo._name = generar_nombre("informebienestar", archivo._name)

                # Actualiza la solicitud
                solicitudbeca.estado = estadosolicitud
                solicitudbeca.visitadbu = visitarealizada
                solicitudbeca.archivoinformedbu = archivo

                # Si es validada
                if estadosolicitud == 8:
                    observacion = 'APTO PARA APLICAR A BECA'
                    solicitudbeca.aplicabeca = 1
                else:
                    solicitudbeca.aplicabeca = 2

                solicitudbeca.save(request)

                # Guardo el recorrido
                recorridosolicitud = DescuentoPosgradoMatriculaRecorrido(
                    descuentoposgradomatricula=solicitudbeca,
                    fecha=datetime.now().date(),
                    persona=persona,
                    observacion=observacion,
                    estado=estadosolicitud
                )
                recorridosolicitud.save(request)

                # Envio de e-mail de notificacion al solicitante
                # listacuentascorreo = [23, 24, 25, 26, 27]
                # posgrado1_unemi@unemi.edu.ec
                # posgrado2_unemi@unemi.edu.ec
                # posgrado3_unemi@unemi.edu.ec
                # posgrado4_unemi@unemi.edu.ec
                # posgrado5_unemi@unemi.edu.ec
                #
                listacuentascorreo = [18]  # posgrado@unemi.edu.ec

                lista_email_envio = solicitante.lista_emails_envio()

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                if estadosolicitud == 8:
                    msg = "Verificó"
                    tituloemail = "Solicitud de Beca de Posgrado - Verificada"
                    tiponotificacion = "VERIFICADA"
                else:
                    msg = "Rechazó"
                    tituloemail = "Solicitud de Beca de Posgrado - Rechazada"
                    tiponotificacion = "RECHAZADA"

                send_html_mail(tituloemail,
                               "emails/notificacion_solicitud_becaposgrado.html",
                               {'sistema': u'Posgrado UNEMI',
                                'fecha': fechaenvio,
                                'hora': horaenvio,
                                'saludo': 'Estimada' if solicitante.sexo_id == 1 else 'Estimado',
                                'solicitante': solicitante.nombre_completo_inverso(),
                                'tiponotificacion': tiponotificacion,
                                'observaciones': observacion,
                                't': miinstitucion()
                                },
                               lista_email_envio,
                               [],
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                log(u'%s solicitud de beca de posgrado: %s' % (msg, solicitudbeca), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'verificaraplicanbeca':
            try:
                if DescuentoPosgradoMatricula.objects.values("id").filter(status=True, aplicabeca=1, detalleconfiguraciondescuentoposgrado__configuraciondescuentoposgrado__id=int(encrypt(request.POST['idp']))).exists():
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "No existen maestrantes que apliquen a becas para generar el reporte"})

            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar la consulta."})

        elif action == 'verificarsolicitudes':
            try:
                if DescuentoPosgradoMatricula.objects.values('id').filter(
                    detalleconfiguraciondescuentoposgrado__configuraciondescuentoposgrado_id=int(encrypt(request.POST['idp'])),
                    status=True,
                    detalleconfiguraciondescuentoposgrado__status=True,
                    inscripcioncohorte__integrantegrupoentrevitamsc__estado=2,
                    inscripcioncohorte__tipobeca__isnull=False,
                    inscripcioncohorte__inscripcion__isnull=False,
                    evidenciasdescuentoposgradomatricula__isnull=False,
                    inscripcioncohorte__rubro__status=True,
                    inscripcioncohorte__rubro__admisionposgradotipo__in=[2, 3],
                    inscripcioncohorte__rubro__cancelado=True
                ).distinct().exists():
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "No existen registros de solicitudes de becas"})

            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar la consulta."})

        elif action == 'listadoaplicanbeca':
            try:
                __author__ = 'Unemi'

                fuentenormal = easyxtitulo = easyxf(
                    'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                titulo = easyxf(
                    'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                titulo2 = easyxf(
                    'font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
                fuentecabecera = easyxf(
                    'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                fuentenormal = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                fuentenormalwrap = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                fuentenormalwrap.alignment.wrap = True
                fuentenormalcent = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
                fuentemoneda = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                    num_format_str=' "$" #,##0.00')
                fuentefecha = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
                    num_format_str='yyyy-mm-dd')
                fuentenumerodecimal = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                    num_format_str='#,##0.00')
                fuentenumeroentero = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')

                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False
                wb = Workbook(encoding='utf-8')
                ws = wb.add_sheet('SolicitudesBeca')
                response = HttpResponse(content_type="application/ms-excel")
                response['Content-Disposition'] = 'attachment; filename=solicitudes_aplican_becaposgrado_' + random.randint(1, 10000).__str__() + '.xls'

                ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                ws.write_merge(1, 1, 0, 10, 'DIRECCIÓN DE INVESTIGACIÓN Y POSGRADO', titulo2)
                ws.write_merge(2, 2, 0, 10, 'LISTADO DE MAESTRANTES APTOS PARA APLICAR A BECAS DE POSGRADO', titulo2)

                row_num = 4
                columns = [
                    (u"#", 800),
                    (u"FECHA SOLICITUD", 3500),
                    (u"PROGRAMA", 10000),
                    (u"COHORTE", 10000),
                    (u"IDENTIFICACIÓN", 5000),
                    (u"NOMBRES COMPLETOS", 10000),
                    (u"CORREO PERSONAL", 8000),
                    (u"CORREO UNEMI", 8000),
                    (u"TELÉFONO", 5000),
                    (u"CELULAR", 5000),
                    (u"NOTA EXAMEN ADMISIÓN", 5000),
                    (u"TIPO DE BECA", 10000),

                    (u"PUNTAJE ACADÉMICO", 5000),
                    (u"GRADO DISCAPACIDAD", 5000),
                    (u"GRUPO SOCIOECONÓMICO", 5000),

                    (u"COSTO PROGRAMA", 5000),
                    (u"VALOR BECA", 5000),
                    (u"TOTAL GENERADO", 5000)
                ]
                for col_num in range(len(columns)):
                    ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                    ws.col(col_num).width = columns[col_num][1]

                solicitudes = DescuentoPosgradoMatricula.objects.filter(status=True, aplicabeca=1, detalleconfiguraciondescuentoposgrado__configuraciondescuentoposgrado__id=int(encrypt(request.POST['idp']))).order_by('-fecha_creacion')
                c = 0
                for solicitud in solicitudes:
                    row_num += 1
                    c += 1
                    alumno = solicitud.inscripcioncohorte.inscripcionaspirante.persona
                    tipobeca = solicitud.detalleconfiguraciondescuentoposgrado.descuentoposgrado.id
                    valor_programa = Decimal(solicitud.inscripcioncohorte.valor_maestria()).quantize(Decimal('.01'))
                    valor_beca = solicitud.valordescuento

                    # ws.write(row_num, 0, str(solicitud.id).zfill(5), fuentenormalcent)
                    ws.write(row_num, 0, c, fuentenumeroentero)
                    ws.write(row_num, 1, solicitud.fecha_creacion, fuentefecha)
                    ws.write(row_num, 2, solicitud.inscripcioncohorte.cohortes.maestriaadmision.carrera.nombre, fuentenormal)
                    ws.write(row_num, 3, solicitud.inscripcioncohorte.cohortes.descripcion, fuentenormal)
                    ws.write(row_num, 4, alumno.identificacion(), fuentenormal)
                    ws.write(row_num, 5, alumno.nombre_completo_inverso(), fuentenormal)
                    ws.write(row_num, 6, alumno.email, fuentenormal)
                    ws.write(row_num, 7, alumno.emailinst, fuentenormal)
                    ws.write(row_num, 8, alumno.telefono_conv, fuentenormal)
                    ws.write(row_num, 9, alumno.telefono, fuentenormal)
                    ws.write(row_num, 10, solicitud.inscripcioncohorte.integrantegrupoexamenmsc_set.filter(status=True)[0].notaexa , fuentenormal)
                    ws.write(row_num, 11, solicitud.detalleconfiguraciondescuentoposgrado.descuentoposgrado.nombre, fuentenormal)
                    ws.write(row_num, 12, solicitud.promedio if tipobeca == 5 else '', fuentenormal)
                    ws.write(row_num, 13, solicitud.gradodiscapacidad if tipobeca in [7, 8] else '', fuentenormal)
                    ws.write(row_num, 14, solicitud.inscripcioncohorte.inscripcion.persona.mi_ficha().grupoeconomico.nombre_corto() if tipobeca == 6 else '', fuentenormal)
                    ws.write(row_num, 15, valor_programa, fuentemoneda)
                    ws.write(row_num, 16, valor_beca, fuentemoneda)
                    ws.write(row_num, 17, valor_programa - valor_beca, fuentemoneda)

                wb.save(response)
                return response
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar la consulta."})

        elif action == 'listadogeneral':
            try:
                __author__ = 'Unemi'

                fuentenormal = easyxtitulo = easyxf(
                    'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                titulo = easyxf(
                    'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                titulo2 = easyxf(
                    'font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
                fuentecabecera = easyxf(
                    'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                fuentenormal = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                fuentenormalwrap = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                fuentenormalwrap.alignment.wrap = True
                fuentenormalcent = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
                fuentemoneda = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                    num_format_str=' "$" #,##0.00')
                fuentefecha = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
                    num_format_str='yyyy-mm-dd')
                fuentenumerodecimal = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                    num_format_str='#,##0.00')
                fuentenumeroentero = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')

                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False
                wb = Workbook(encoding='utf-8')
                ws = wb.add_sheet('SolicitudesBecaGeneral')
                response = HttpResponse(content_type="application/ms-excel")
                response['Content-Disposition'] = 'attachment; filename=solicitudes_general_' + random.randint(1, 10000).__str__() + '.xls'

                ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                ws.write_merge(1, 1, 0, 10, 'DIRECCIÓN DE INVESTIGACIÓN Y POSGRADO', titulo2)
                ws.write_merge(2, 2, 0, 10, 'LISTADO DE SOLICITUDES DE BECAS DE POSGRADO', titulo2)

                row_num = 4
                columns = [
                    (u"#", 800),
                    (u"FECHA SOLICITUD", 3500),
                    (u"PROGRAMA", 10000),
                    (u"COHORTE", 10000),
                    (u"IDENTIFICACIÓN", 5000),
                    (u"NOMBRES COMPLETOS", 10000),
                    (u"CORREO PERSONAL", 8000),
                    (u"CORREO UNEMI", 8000),
                    (u"TELÉFONO", 5000),
                    (u"CELULAR", 5000),
                    (u"NOTA EXAMEN ADMISIÓN", 5000),
                    (u"TIPO DE BECA", 10000),
                    (u"ESTADO", 5000),
                    (u"OBSERVACION", 5000)
                ]
                for col_num in range(len(columns)):
                    ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                    ws.col(col_num).width = columns[col_num][1]

                solicitudes = DescuentoPosgradoMatricula.objects.filter(
                    detalleconfiguraciondescuentoposgrado__configuraciondescuentoposgrado_id=int(encrypt(request.POST['idp'])),
                    status=True,
                    detalleconfiguraciondescuentoposgrado__status=True,
                    inscripcioncohorte__integrantegrupoentrevitamsc__estado=2,
                    inscripcioncohorte__tipobeca__isnull=False,
                    inscripcioncohorte__inscripcion__isnull=False,
                    evidenciasdescuentoposgradomatricula__isnull=False,
                    inscripcioncohorte__rubro__status=True,
                    inscripcioncohorte__rubro__admisionposgradotipo__in=[2, 3],
                    inscripcioncohorte__rubro__cancelado=True
                ).distinct().order_by('-fecha_creacion')


                c = 0
                for solicitud in solicitudes:
                    row_num += 1
                    c += 1
                    alumno = solicitud.inscripcioncohorte.inscripcionaspirante.persona
                    tipobeca = solicitud.detalleconfiguraciondescuentoposgrado.descuentoposgrado.id
                    # valor_programa = Decimal(solicitud.inscripcioncohorte.valor_maestria()).quantize(Decimal('.01'))
                    # valor_beca = solicitud.valordescuento

                    # ws.write(row_num, 0, str(solicitud.id).zfill(5), fuentenormalcent)
                    ws.write(row_num, 0, c, fuentenumeroentero)
                    ws.write(row_num, 1, solicitud.fecha_creacion, fuentefecha)
                    ws.write(row_num, 2, solicitud.inscripcioncohorte.cohortes.maestriaadmision.carrera.nombre, fuentenormal)
                    ws.write(row_num, 3, solicitud.inscripcioncohorte.cohortes.descripcion, fuentenormal)
                    ws.write(row_num, 4, alumno.identificacion(), fuentenormal)
                    ws.write(row_num, 5, alumno.nombre_completo_inverso(), fuentenormal)
                    ws.write(row_num, 6, alumno.email, fuentenormal)
                    ws.write(row_num, 7, alumno.emailinst, fuentenormal)
                    ws.write(row_num, 8, alumno.telefono_conv, fuentenormal)
                    ws.write(row_num, 9, alumno.telefono, fuentenormal)
                    ws.write(row_num, 10, solicitud.inscripcioncohorte.integrantegrupoexamenmsc_set.filter(status=True)[0].notaexa , fuentenormal)
                    ws.write(row_num, 11, solicitud.detalleconfiguraciondescuentoposgrado.descuentoposgrado.nombre, fuentenormal)
                    ws.write(row_num, 12, solicitud.get_estado_display(), fuentenormal)
                    ws.write(row_num, 13, solicitud.ultimo_registro_recorrido().observacion, fuentenormal)

                wb.save(response)
                return response
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar la consulta."})

        elif action == 'subirevidencialey':
            id = request.POST['id']
            form = EvidenciaLeyHumanitariaForm(request.POST, request.FILES)
            if form.is_valid():
                nfile = request.FILES['archivo']
                nfile._name = remover_caracteres_especiales_unicode(nfile._name).lower().replace(' ', '_')
                solictud = DescuentoPosgradoMatricula.objects.get(id=id)
                solictud.usuariosubidaleyhumanitaria = request.session['persona']
                solictud.fechasubidaleyhumanitaria = datetime.now().date()
                solictud.evidencialeyhumanitaria = nfile
                solictud.save()
                return JsonResponse({"result": False}, safe=False)
            else:
                return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "mensaje": "Error en el formulario"})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Configuración de Descuento de Posgrado'
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Nueva configuración de Descuento Posgrado'
                    form = ConfiguracionDescuentoPosgradoForm()
                    data['form'] = form
                    return render(request, "adm_configuraciondescuento/add.html", data)
                except Exception as ex:
                    pass

            elif action == 'adddescuento':
                try:
                    data['title'] = u'Nueva Descuento Posgrado'
                    form = DescuentoPosgradoForm()
                    data['form'] = form
                    return render(request, "adm_configuraciondescuento/adddescuento.html", data)
                except Exception as ex:
                    pass

            elif action == 'adddescuentos':
                try:
                    data['title'] = u'Descuentos configuración Posgrado'
                    configuracion = ConfiguracionDescuentoPosgrado.objects.get(pk=int(request.GET['id']))
                    form = ConfiguracionDescuentoPosgradoDetalleForm(initial={'descripcion': configuracion.descripcion})
                    form.editar()
                    data['configuracion'] = configuracion
                    data['sublineas'] = DescuentoPosgrado.objects.filter(status=True, activo=True)
                    data['form'] = form
                    return render(request, "adm_configuraciondescuento/adddescuentos.html", data)
                except Exception as ex:
                    pass

            elif action == 'addperiodos':
                try:
                    data['title'] = u'Periodos configuración Posgrado'
                    configuracion = DetalleConfiguracionDescuentoPosgrado.objects.get(pk=int(request.GET['id']))
                    form = ConfiguracionPeriodoPosgradoDetalleForm(initial={'descripcion': configuracion.descuentoposgrado.nombre})
                    form.editar()
                    data['configuracion'] = configuracion
                    hoy = datetime.now().date()
                    data['periodos'] = Periodo.objects.filter(status=True, activo=True, tipo__id__in=[3,4] ,inicio__lte=hoy, fin__gte=hoy).distinct()
                    data['form'] = form
                    return render(request, "adm_configuraciondescuento/addperiodos.html", data)
                except Exception as ex:
                    pass

            elif action == 'addrequisito':
                try:
                    data['title'] = u'Requisitos configuración Posgrado'
                    configuracion = DetalleConfiguracionDescuentoPosgrado.objects.get(pk=int(request.GET['id']))
                    form = ConfiguracionRequisitoPosgradoDetalleForm()
                    data['configuracion'] = configuracion
                    data['form'] = form
                    return render(request, "adm_configuraciondescuento/addrequisito.html", data)
                except Exception as ex:
                    pass

            elif action == 'edit':
                try:
                    data['title'] = u'Editar configuración descuento posgrado'
                    configuracion = ConfiguracionDescuentoPosgrado.objects.get(pk=int(request.GET['id']))
                    form = ConfiguracionDescuentoPosgradoForm(initial={'descripcion': configuracion.descripcion,
                                                                       'fechainicio': configuracion.fechainicio,
                                                                       'fechafin': configuracion.fechafin,
                                                                       'porcentaje': configuracion.porcentaje,
                                                                       'fecharige': configuracion.fecharige,
                                                                       'fechafinrequisito': configuracion.fechafinrequisito,
                                                                       'activo' : configuracion.activo})
                    data['configuracion'] = configuracion
                    # form.editar()
                    data['form'] = form
                    return render(request, "adm_configuraciondescuento/edit.html", data)
                except Exception as ex:
                    pass

            elif action == 'editrequisito':
                try:
                    data['title'] = u'Editar Requisito descuento posgrado'
                    configuracion = RequisitosDetalleConfiguracionDescuentoPosgrado.objects.get(pk=int(request.GET['id']))
                    form = ConfiguracionRequisitoPosgradoDetalleForm(initial={'descripcion': configuracion.descripcion,
                                                                              'requisito' : configuracion.requisito})
                    data['configuracion'] = configuracion
                    # form.editar()
                    data['form'] = form
                    return render(request, "adm_configuraciondescuento/editrequisito.html", data)
                except Exception as ex:
                    pass

            elif action == 'editdescuento':
                try:
                    data['title'] = u'Editar descuento posgrado'
                    rubrica = DescuentoPosgrado.objects.get(pk=int(request.GET['id']))
                    form = DescuentoPosgradoForm(initial={'nombre': rubrica.nombre,
                                                          'activo': rubrica.activo})
                    data['rubrica'] = rubrica
                    data['form'] = form
                    return render(request, "adm_configuraciondescuento/editdescuento.html", data)
                except Exception as ex:
                    pass

            elif action == 'descuento':
                try:
                    search = None
                    data['title'] = u'Descuentos'
                    rubricas = DescuentoPosgrado.objects.filter(status=True).order_by('-id')
                    if 'id' in request.GET:
                        ids = int(request.GET['id'])
                        rubricas = rubricas.filter(status=True,id=int(request.GET['id']))

                    if 's' in request.GET:
                        search = request.GET['s']
                        # s = search.split(" ")
                        rubricas = rubricas.filter(status=True,nombre__icontains=search)

                    paging = MiPaginador(rubricas, 25)
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
                    data['temas'] = page.object_list
                    data['search'] = search if search else ""
                    data['rubricas'] = rubricas
                    return render(request, "adm_configuraciondescuento/descuento.html", data)
                except Exception as ex:
                    pass

            elif action == 'descuentos':
                try:
                    rubrica = ConfiguracionDescuentoPosgrado.objects.get(pk=request.GET['id'], status=True)
                    data['title'] = u'Descuentos - ' + rubrica.descripcion
                    detalles = rubrica.detalleconfiguraciondescuentoposgrado_set.filter(status=True).order_by('-id')
                    data['detalles'] = detalles
                    data['rubrica'] = rubrica
                    return render(request, "adm_configuraciondescuento/descuentos.html", data)
                except Exception as ex:
                    pass

            elif action == 'periodos':
                try:
                    rubrica = DetalleConfiguracionDescuentoPosgrado.objects.get(pk=request.GET['id'], status=True)
                    data['title'] = u'Periodo - ' + rubrica.__str__()
                    detalles = rubrica.periododetalleconfiguraciondescuentoposgrado_set.filter(status=True).order_by('-id')
                    data['detalles'] = detalles
                    data['rubrica'] = rubrica
                    return render(request, "adm_configuraciondescuento/periodos.html", data)
                except Exception as ex:
                    pass

            elif action == 'requisitos':
                try:
                    rubrica = DetalleConfiguracionDescuentoPosgrado.objects.get(pk=request.GET['id'], status=True)
                    data['title'] = u'Requisitos - ' + rubrica.__str__()
                    detalles = rubrica.requisitosdetalleconfiguraciondescuentoposgrado_set.filter(status=True).order_by('-id')
                    data['detalles'] = detalles
                    data['rubrica'] = rubrica
                    return render(request, "adm_configuraciondescuento/requisitos.html", data)
                except Exception as ex:
                    pass

            elif action == 'delete':
                try:
                    data['title'] = u'ELIMINAR CONFIGURACIÓN DESCUENTO POSGRADO'
                    data['configuracion'] = ConfiguracionDescuentoPosgrado.objects.get(pk=request.GET['id'])
                    return render(request, 'adm_configuraciondescuento/delete.html', data)
                except Exception as ex:
                    pass

            elif action == 'deleterequisito':
                try:
                    data['title'] = u'ELIMINAR REQUISITO DESCUENTO POSGRADO'
                    data['configuracion'] = RequisitosDetalleConfiguracionDescuentoPosgrado.objects.get(pk=request.GET['id'])
                    return render(request, 'adm_configuraciondescuento/deleterequisito.html', data)
                except Exception as ex:
                    pass

            elif action == 'propuestastemas':
                try:
                    data['title'] = u'Gestión de Solicitudes de Descuento'
                    data['aprobar'] = variable_valor('APROBAR_SILABO')
                    data['rechazar'] = variable_valor('RECHAZAR_SILABO')
                    data['pendiente'] = variable_valor('PENDIENTE_SILABO')
                    data['estados'] = ESTADO_BECA_POSGRADO

                    data['estadosevidencia'] = ((0, u'TODAS'),
                                                (1, u'CARGADAS'),
                                                (2, u'NO CARGADAS'))

                    configuracion = ConfiguracionDescuentoPosgrado.objects.get(pk=int(request.GET['idconfiguracion']))

                    tipoconfiguracion = configuracion.tipo


                    search = None
                    ids = None
                    if 'tipoestado' in request.GET:
                        data['tipoestado'] = int(request.GET['tipoestado'])
                        if int(request.GET['tipoestado']) > 0:
                            solicitudes = DescuentoPosgradoMatricula.objects.filter(estado=int(request.GET['tipoestado']),
                                                                                    detalleconfiguraciondescuentoposgrado__configuraciondescuentoposgrado=configuracion,
                                                                                    status=True, detalleconfiguraciondescuentoposgrado__status=True
                                                                                    ).order_by('-id').distinct()
                        else:
                            solicitudes = DescuentoPosgradoMatricula.objects.filter(
                                                                                    detalleconfiguraciondescuentoposgrado__configuraciondescuentoposgrado=configuracion,
                                                                                    status=True, detalleconfiguraciondescuentoposgrado__status=True
                                                                                    ).order_by('-id').distinct()

                        if grupobecaposgradoube:
                            solicitudes = solicitudes.filter(remitidodbu=True)

                        # Si es becas de postulantes
                        if tipoconfiguracion == 2:
                            solicitudes = solicitudes.filter(inscripcioncohorte__integrantegrupoentrevitamsc__estado=2,
                                                             inscripcioncohorte__tipobeca__isnull=False,
                                                             inscripcioncohorte__inscripcion__isnull=False,
                                                             evidenciasdescuentoposgradomatricula__isnull=False,
                                                             inscripcioncohorte__rubro__status=True,
                                                             inscripcioncohorte__rubro__admisionposgradotipo__in=[2, 3],
                                                             inscripcioncohorte__rubro__cancelado=True).order_by('-id').distinct()

                    else:
                        if not grupobecaposgradoube:
                            estadocons = 1
                        else:
                            estadocons = 4

                        data['tipoestado'] = estadocons
                        solicitudes = DescuentoPosgradoMatricula.objects.filter(
                                                                                detalleconfiguraciondescuentoposgrado__configuraciondescuentoposgrado=configuracion,
                                                                                status=True,
                                                                                estado=estadocons,
                                                                                detalleconfiguraciondescuentoposgrado__status=True
                                                                                ).order_by('-id').distinct()

                        if grupobecaposgradoube:
                            solicitudes = solicitudes.filter(remitidodbu=True)

                        # Si es becas de postulantes
                        if tipoconfiguracion == 2:
                            solicitudes = solicitudes.filter(inscripcioncohorte__integrantegrupoentrevitamsc__estado=2,
                                                             inscripcioncohorte__tipobeca__isnull=False,
                                                             inscripcioncohorte__inscripcion__isnull=False,
                                                             evidenciasdescuentoposgradomatricula__isnull=False,
                                                             inscripcioncohorte__rubro__status=True,
                                                             inscripcioncohorte__rubro__admisionposgradotipo__in=[2, 3],
                                                             inscripcioncohorte__rubro__cancelado=True
                                                             ).order_by('-id').distinct()



                    estadoevidencia = 0

                    # if 'estadoevidencia' in request.GET:
                    #     estadoevidencia = int(request.GET['estadoevidencia'])
                    #
                    # if estadoevidencia > 0 and tipoconfiguracion == 2:
                    #     if estadoevidencia == 1:
                    #         solicitudes = solicitudes.filter(evidenciasdescuentoposgradomatricula__isnull=False).distinct()
                    #     else:
                    #         solicitudes = solicitudes.filter(evidenciasdescuentoposgradomatricula__isnull=True).distinct()


                    if 'id' in request.GET:
                        ids = int(request.GET['id'])
                        solicitudes = solicitudes.filter(status=True, id=int(request.GET['id']))

                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            if int(request.GET['idconfiguracion']) == 3:
                                solicitudes = solicitudes.filter(Q(inscripcioncohorte__inscripcionaspirante__persona__nombres__icontains=search) |
                                                     Q(inscripcioncohorte__inscripcionaspirante__persona__apellido1__icontains=search) |
                                                     Q(inscripcioncohorte__inscripcionaspirante__persona__apellido2__icontains=search) |
                                                     Q(inscripcioncohorte__inscripcionaspirante__persona__cedula__icontains=search) |
                                                     Q(inscripcioncohorte__inscripcionaspirante__persona__pasaporte__icontains=search) |
                                                     Q(inscripcioncohorte__inscripcionaspirante__persona__usuario__username__icontains=search),detalleconfiguraciondescuentoposgrado__configuraciondescuentoposgrado=configuracion, status=True)
                            else:
                                solicitudes = solicitudes.filter(detalleconfiguraciondescuentoposgrado__configuraciondescuentoposgrado=configuracion, status=True,detalleconfiguraciondescuentoposgrado__configuraciondescuentoposgrado__descripcion__icontains=search)
                        else:
                            if int(request.GET['idconfiguracion']) == 3:
                                solicitudes = solicitudes.filter(Q(inscripcioncohorte__inscripcionaspirante__persona__apellido1__icontains=ss[0]) &
                                                     Q(inscripcioncohorte__inscripcionaspirante__persona__apellido2__icontains=ss[1]),detalleconfiguraciondescuentoposgrado__configuraciondescuentoposgrado=configuracion, status=True)
                            else:
                                solicitudes = solicitudes.filter(detalleconfiguraciondescuentoposgrado__configuraciondescuentoposgrado=configuracion, status=True,detalleconfiguraciondescuentoposgrado__configuraciondescuentoposgrado__descripcion__icontains=search)


                    paging = MiPaginador(solicitudes, 25)
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
                    data['temas'] = page.object_list
                    data['search'] = search if search else ""
                    data['configuracion'] = configuracion
                    data['estadoevidencia'] = estadoevidencia
                    data['grupobecaposgradoube'] = grupobecaposgradoube
                    return render(request, "adm_configuraciondescuento/propuestastemas.html", data)
                except Exception as ex:
                    pass

            elif action == 'evidenciasinscritos':
                try:
                    data['title'] = u'Revisión de Solicitudes'
                    data['inscripcion'] = inscripcion = DescuentoPosgradoMatricula.objects.get(pk=request.GET['id'])
                    data['configuracion'] = cohorte = inscripcion.detalleconfiguraciondescuentoposgrado.configuraciondescuentoposgrado
                    data['requisitos'] = inscripcion.evidenciasdescuentoposgradomatricula_set.filter(status=True).order_by('id')
                    # verificar si ya esta todo aprobado para enviar correo de aprobacion
                    bandera = 0
                    requi = inscripcion.detalleconfiguraciondescuentoposgrado.requisitosdetalleconfiguraciondescuentoposgrado_set.filter(status=True)
                    cantidad = requi.count()
                    cantidad_aux = 0
                    for re in requi:
                        ingresoevidencias = re.detalle_requisitosmaestriacohorte(inscripcion)
                        if ingresoevidencias:
                            if ingresoevidencias.ultima_evidencia().estado_aprobacion == 2:
                                cantidad_aux += 1
                    if cantidad == cantidad_aux:
                        bandera = 1
                    data['bandera'] = bandera
                    return render(request, "adm_configuraciondescuento/evidenciasinscritos.html", data)
                except Exception as ex:
                    pass

            elif action == 'validarsolicitudbeca':
                try:
                    data['title'] = u'Revisión y Validación de Solicitud de Beca'
                    data['solicitud'] = solicitud = DescuentoPosgradoMatricula.objects.get(pk=request.GET['id'])

                    solicitante = solicitud.inscripcioncohorte.inscripcionaspirante.persona

                    data['datosprincipales'] = {"identificacion": solicitante.identificacion(),
                                                "nombres": solicitante.nombre_completo_inverso(),
                                                "programa": solicitud.inscripcioncohorte.inscripcion.carrera.nombre,
                                                "cohorte": solicitud.inscripcioncohorte.cohortes.descripcion,
                                                "costoprograma": solicitud.inscripcioncohorte.valor_maestria(),
                                                "tipobeca": solicitud.detalleconfiguraciondescuentoposgrado.descuentoposgrado.nombre,
                                                "idtipobeca": solicitud.detalleconfiguraciondescuentoposgrado.descuentoposgrado.id}

                    data['saldopresupuestobecas'] = x = solicitud.inscripcioncohorte.cohortes.saldo_disponible_presupuestobecas()
                    detalledescuento = solicitud.detalleconfiguraciondescuentoposgrado

                    requisitos = detalledescuento.requisitos()

                    lista_requisitos = []
                    for requisito in requisitos:
                        if solicitud.evidenciasdescuentoposgradomatricula_set.values('id').filter(status=True, requisitosdetalleconfiguraciondescuentoposgrado__id=requisito.id).exists():
                            evidenciasolicitud = EvidenciasDescuentoPosgradoMatricula.objects.get(descuentoposgradomatricula=solicitud, requisitosdetalleconfiguraciondescuentoposgrado=requisito)
                            idevidencia = evidenciasolicitud.id
                            archivoevidencia = evidenciasolicitud.archivo.url
                            ultimaevidencia = evidenciasolicitud.ultima_evidencia()
                            estado = ultimaevidencia.get_estado_aprobacion_display()
                            valorestado = ultimaevidencia.estado_aprobacion
                            color_estado = ultimaevidencia.color_estado()
                            observacion = ultimaevidencia.observacion_aprobacion
                        else:
                            idevidencia = 0
                            archivoevidencia = ''
                            estado = ''
                            valorestado = 0
                            color_estado = ''
                            observacion = ''


                        lista_requisitos.append([requisito.id, idevidencia, requisito.requisito, archivoevidencia, estado, color_estado, observacion, valorestado])


                    data['requisitos'] = lista_requisitos
                    if solicitud.evidenciasdescuentoposgradomatricula_set.filter(status=True).exists():
                        data['primerdocumento'] = p = solicitud.evidenciasdescuentoposgradomatricula_set.filter(status=True).order_by('id')[0]
                        data['estadossolicitud'] = (
                            (4, u'VALIDADA'),
                            (6, u'NOVEDAD REQUISITO'),
                            (3, u'RECHAZADA')
                        )

                        data['estadosrequisitos'] = (
                            (2, u"VALIDADO"),
                            (4, u"NOVEDAD"),
                            (3, u"RECHAZADO")
                        )
                    else:
                        data['primerdocumento'] = None
                        data['estadossolicitud'] = (
                            (3, u'RECHAZADA'),
                        )

                    data['porcentajesdescuento'] = solicitud.detalleconfiguraciondescuentoposgrado.porcentajedescuentobecaposgrado_set.filter(status=True).order_by('id')

                    idtipobeca = solicitud.detalleconfiguraciondescuentoposgrado.descuentoposgrado.id
                    if idtipobeca != 6:
                        tablaporc = {"titulo": "Puntaje" if idtipobeca == 5 else "Grado de Discapacidad",
                                     "titulo2": "",
                                     "ancho1": "0",
                                     "ancho2": "40",
                                     "ancho3": "40",
                                     "ancho4": "15",
                                     "ancho5": "5",
                                     }
                    else:
                        tablaporc = {"titulo": "Umbrales",
                                     "titulo2": "Grupo Socioeconómico",
                                     "ancho1": "30",
                                     "ancho2": "25",
                                     "ancho3": "25",
                                     "ancho4": "15",
                                     "ancho5": "15",
                                     }

                    data['tablaporc'] = tablaporc
                    data['configuracion'] = cohorte = solicitud.detalleconfiguraciondescuentoposgrado.configuraciondescuentoposgrado
                    data['puntajeficha'] = 0

                    # Si es beca por situación económica
                    if idtipobeca == 6:
                        # Consulto el total en la ficha socioeconómica
                        fichasocioecon = solicitud.inscripcioncohorte.inscripcionaspirante.persona.mi_ficha()
                        data['puntajeficha'] = fichasocioecon.puntajetotal
                        data['gruposocioeconomico'] = fichasocioecon.grupoeconomico.nombre_corto()


                    return render(request, "adm_configuraciondescuento/validarsolicitudbeca.html", data)
                except Exception as ex:
                    pass

            elif action == 'verificarsolicitudbeca':
                try:
                    data['title'] = u'Verificación de Solicitud de Beca - Dirección de Bienestar Universitario'
                    data['solicitud'] = solicitud = DescuentoPosgradoMatricula.objects.get(pk=request.GET['id'])
                    idtipobeca = solicitud.detalleconfiguraciondescuentoposgrado.descuentoposgrado.id
                    solicitante = solicitud.inscripcioncohorte.inscripcionaspirante.persona

                    if idtipobeca == 5:
                        parametrocalculo = solicitud.promedio
                    elif idtipobeca == 6:
                        parametrocalculo = solicitud.puntajeficha
                    else:
                        parametrocalculo = solicitud.gradodiscapacidad

                    data['parametrocalculo'] = parametrocalculo

                    data['datosprincipales'] = {"identificacion": solicitante.identificacion(),
                                                "nombres": solicitante.nombre_completo_inverso(),
                                                "programa": solicitud.inscripcioncohorte.inscripcion.carrera.nombre,
                                                "cohorte": solicitud.inscripcioncohorte.cohortes.descripcion,
                                                "costoprograma": solicitud.inscripcioncohorte.valor_maestria(),
                                                "tipobeca": solicitud.detalleconfiguraciondescuentoposgrado.descuentoposgrado.nombre,
                                                "idtipobeca": solicitud.detalleconfiguraciondescuentoposgrado.descuentoposgrado.id}

                    lista_requisitos = []
                    evidencias = solicitud.evidenciasdescuentoposgradomatricula_set.filter(status=True).order_by('id')
                    for evidencia in evidencias:
                        descripcion = evidencia.requisitosdetalleconfiguraciondescuentoposgrado.requisito
                        archivoevidencia = evidencia.archivo.url
                        ultimaevidencia = evidencia.ultima_evidencia()
                        estado = ultimaevidencia.get_estado_aprobacion_display()
                        color_estado = ultimaevidencia.color_estado()

                        lista_requisitos.append([descripcion, archivoevidencia, estado, color_estado])


                    data['requisitos'] = lista_requisitos

                    data['primerdocumento'] = p = solicitud.evidenciasdescuentoposgradomatricula_set.filter(status=True).order_by('id')[0]
                    data['estadossolicitud'] = (
                        (8, u'APTO BECA'),
                        (9, u'RECHAZADA B')
                    )

                    data['porcentajesdescuento'] = solicitud.detalleconfiguraciondescuentoposgrado.porcentajedescuentobecaposgrado_set.filter(status=True).order_by('id')

                    if idtipobeca != 6:
                        tablaporc = {"titulo": "Puntaje" if idtipobeca == 5 else "Grado de Discapacidad",
                                     "titulo2": "",
                                     "ancho1": "0",
                                     "ancho2": "40",
                                     "ancho3": "40",
                                     "ancho4": "15",
                                     "ancho5": "5",
                                     }
                    else:
                        tablaporc = {"titulo": "Umbrales",
                                     "titulo2": "Grupo Socioeconómico",
                                     "ancho1": "30",
                                     "ancho2": "25",
                                     "ancho3": "25",
                                     "ancho4": "15",
                                     "ancho5": "15",
                                     }

                    data['tablaporc'] = tablaporc
                    data['configuracion'] = solicitud.detalleconfiguraciondescuentoposgrado.configuraciondescuentoposgrado
                    data['puntajeficha'] = 0

                    return render(request, "adm_configuraciondescuento/verificarsolicitudbeca.html", data)
                except Exception as ex:
                    pass

            elif action == 'saldospresupuestobecas':
                try:
                    programasmaestria = CohorteMaestria.objects.filter(status=True, presupuestobeca__gt=0, inscripcioncohorte__descuentoposgradomatricula__estado__in=[2, 4, 8, 10])\
                                    .annotate(programa=F('maestriaadmision__carrera__nombre'),
                                              cohorte=F('descripcion'),
                                              utilizado=Sum('inscripcioncohorte__descuentoposgradomatricula__valordescuento'))\
                                    .values('programa', 'cohorte', 'presupuestobeca', 'utilizado')\
                                    .order_by('programa', 'cohorte')

                    # print(programasmaestria.query)

                    saldospresupuesto = []

                    for detalle in programasmaestria:
                        saldospresupuesto.append({
                            'programa': detalle['programa'],
                            'cohorte': detalle['cohorte'],
                            'presupuestobeca': detalle['presupuestobeca'],
                            'utilizado': detalle['utilizado'],
                            'saldo': Decimal(detalle['presupuestobeca']).quantize(Decimal('.01'))-detalle['utilizado']
                        })

                    data['saldospresupuesto'] = saldospresupuesto
                    template = get_template("adm_configuraciondescuento/saldospresupuestobecas.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'informeevidencias1':
                try:
                    data['title'] = u'Revisión de Solicitudes'
                    requisito = EvidenciasDescuentoPosgradoMatricula.objects.get(pk=request.GET['idrequisito'])
                    data['requisitoinscrito'] = requisito
                    template = get_template("adm_configuraciondescuento/informe_evidencia.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'aprobarrequisitos':
                try:
                    data['title'] = u'Aprobar Solicitud'
                    data['inscripcioncohorte'] = DescuentoPosgradoMatricula.objects.get(pk=request.GET['id'],status=True)
                    return render(request, "adm_configuraciondescuento/aprobarrequisito.html", data)
                except Exception as ex:
                    pass

            elif action == 'rechazarrequisitos':
                try:
                    data['title'] = u'Rechazar Solicitud'
                    data['inscripcioncohorte'] = DescuentoPosgradoMatricula.objects.get(pk=request.GET['id'],status=True)
                    return render(request, "adm_configuraciondescuento/rechazarrequisito.html", data)
                except Exception as ex:
                    pass

            elif action == 'excelprograma':
                try:
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
                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=Descuento' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"NUM", 2000),
                        (u"PERIODO", 10000),
                        (u"CARRERA", 10000),
                        (u"MAESTRANTE", 3000),
                        (u"DESCUENTO", 3000),
                        (u"CORREO", 3000),
                        (u"TELEFONO", 3000),
                        (u"ESTADO", 3000),
                        (u"COSTO DEL PROGRAMA", 3000),
                        (u"VALOR DESCONTADO", 3000),
                        (u"COSTO FINAL DEL PROGRAMA", 3000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]

                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    listaprogramas = DescuentoPosgradoMatricula.objects.filter(status=True,detalleconfiguraciondescuentoposgrado__configuraciondescuentoposgrado__id=request.GET['id']).order_by('matricula__nivel__periodo','matricula__inscripcion__carrera')
                    row_num = 4
                    i = 0
                    for programa in listaprogramas:
                        i += 1
                        campo1 = i
                        if programa.matricula:
                            campo2 = programa.matricula.nivel.periodo.nombre
                            campo3 = programa.matricula.inscripcion.carrera.nombre
                            campo4 = programa.matricula.inscripcion.persona.nombre_completo_inverso()
                            campo5 = programa.matricula.inscripcion.persona.email
                            campo6 = programa.matricula.inscripcion.persona.telefonos()
                            campo9 = programa.matricula.costo_programa()
                            campo10 = programa.valordescuento
                            campo11 = campo9 - campo10
                        else:
                            campo2 = ''
                            campo3 = programa.inscripcioncohorte.cohortes.maestriaadmision.carrera.nombre
                            campo4 = programa.inscripcioncohorte.inscripcionaspirante.persona.nombre_completo_inverso()
                            campo5 = programa.inscripcioncohorte.inscripcionaspirante.persona.email
                            campo6 = programa.inscripcioncohorte.inscripcionaspirante.persona.telefonos()
                            campo9 = '-'
                            campo10 = '-'
                            campo11 = '-'
                        campo7 = programa.get_estado_display()
                        campo8 = programa.detalleconfiguraciondescuentoposgrado.descuentoposgrado.nombre

                        ws.write(row_num, 0, campo1, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                        ws.write(row_num, 3, campo4, font_style2)
                        ws.write(row_num, 4, campo8, font_style2)
                        ws.write(row_num, 5, campo5, font_style2)
                        ws.write(row_num, 6, campo6, font_style2)
                        ws.write(row_num, 7, campo7, font_style2)
                        ws.write(row_num, 8, campo9, font_style2)
                        ws.write(row_num, 9, campo10, font_style2)
                        ws.write(row_num, 10, campo11, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'subirevidencialey':
                data['id'] = request.GET['id']
                data['form'] = EvidenciaLeyHumanitariaForm()
                template = get_template("adm_configuraciondescuento/evidencia_ley.html")
                return JsonResponse({"result": True, 'data': template.render(data)})

            return HttpResponseRedirect(request.path)
        else:
            try:
                search = None
                ids = None
                if 'id' in request.GET:
                    ids = request.GET['id']
                    configuraciones = ConfiguracionDescuentoPosgrado.objects.filter(id=int(ids)).order_by('-id')
                elif 's' in request.GET:
                    search = request.GET['s']
                    configuraciones = ConfiguracionDescuentoPosgrado.objects.filter(descripcion__icontains=search).distinct().order_by('-id')
                else:
                    configuraciones = ConfiguracionDescuentoPosgrado.objects.filter(status=True).order_by('-id')

                # Si es usuario de bienestar, solo puede ver las configuraciones tipo 2
                if grupobecaposgradoube:
                    configuraciones = configuraciones.filter(tipo=2)

                paging = MiPaginador(configuraciones, 25)
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
                data['configuraciones'] = page.object_list
                data['grupobecaposgradoube'] = grupobecaposgradoube
                return render(request, "adm_configuraciondescuento/view.html", data)
            except Exception as ex:
                pass