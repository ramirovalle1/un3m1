# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from datetime import datetime, date

from django.template import Context
from django.template.loader import get_template

from decorators import secure_module, last_access
from sga.commonviews import adduserdata, secuencia_contrato_beca
from sga.forms import SolicitudDevolucionForm
from sga.funciones import MiPaginador, log, variable_valor, generar_nombre
from sga.models import CuentaBancariaPersona, SolicitudDevolucionDinero, SolicitudDevolucionDineroRecorrido
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
    data['periodo'] =periodo= request.session['periodo']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    inscripcion = perfilprincipal.inscripcion

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addsolicitud':
            try:
                form = SolicitudDevolucionForm(request.POST, request.FILES)
                ingresarcuenta = request.POST['ingresarcuenta']

                if 'archivopago' in request.FILES:
                    arch = request.FILES['archivopago']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]

                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb. [Comprobante de Dep+osito]"})
                    if not exte.lower() == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf [Comprobante de Depósito]"})

                if 'archivocedula' in request.FILES:
                    arch = request.FILES['archivocedula']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]

                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb. [Cédula Solicitante]"})
                    if not exte.lower() == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf [Cédula Solicitante]"})

                if 'archivocertificado' in request.FILES:
                    arch = request.FILES['archivocertificado']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]

                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb. [Certificado de Cuenta Bancaria]"})
                    if not exte.lower() == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf [Certificado de Cuenta Bancaria]"})

                if form.is_valid():
                    if SolicitudDevolucionDinero.objects.values('id').filter(persona=persona, status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Usted ya cuenta con una solicitud registrada"})

                    if form.cleaned_data['monto'] < 1 or form.cleaned_data['monto'] > 500:
                        return JsonResponse({"result": "bad", "mensaje": u"El monto debe estar en el rango de 1 a 500"})

                    if ingresarcuenta == 'S':
                        if len(form.cleaned_data['numerocuenta'].strip()) < 5:
                            return JsonResponse({"result": "bad", "mensaje": u"El número de cuenta bancaria debe tener mínimo 5 dígitos."})

                        if CuentaBancariaPersona.objects.values('id').filter(numero=form.cleaned_data['numerocuenta'], status=True).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"El número de cuenta bancaria ya existe"})

                    archivodeposito = request.FILES['archivopago']
                    archivodeposito._name = generar_nombre("deposito", archivodeposito._name)

                    archivocedula = request.FILES['archivocedula']
                    archivocedula._name = generar_nombre("cedula", archivocedula._name)

                    if ingresarcuenta == 'S':
                        archivocertificado = request.FILES['archivocertificado']
                        archivocertificado._name = generar_nombre("certificadocuenta", archivocertificado._name)

                    solicitud = SolicitudDevolucionDinero(persona=persona,
                                                          motivo=form.cleaned_data['motivo'],
                                                          monto=form.cleaned_data['monto'],
                                                          archivodeposito=archivodeposito,
                                                          archivocedula=archivocedula,
                                                          estado=1
                                                          )
                    solicitud.save(request)

                    recorrido = SolicitudDevolucionDineroRecorrido(solicituddevolucion=solicitud,
                                                                   fecha=datetime.now().date(),
                                                                   observacion='SOLICITADO POR ESTUDIANTE',
                                                                   estado=1
                                                                   )
                    recorrido.save(request)

                    if ingresarcuenta == 'S':
                        cuentabancaria = CuentaBancariaPersona(persona=persona,
                                                               banco=form.cleaned_data['banco'],
                                                               tipocuentabanco=form.cleaned_data['tipocuenta'],
                                                               numero=form.cleaned_data['numerocuenta'].strip(),
                                                               estadorevision=1,
                                                               archivo=archivocertificado,
                                                               activapago=True)
                        cuentabancaria.save(request)


                    log(u'Adicionó solicitud de devolución: %s' % solicitud, request, "add")

                    # send_html_mail("Solicitud de Presentación de Ponencia",
                    #                "emails/confirmacion_solicitud_ponencias.html",
                    #                {'sistema': u'Sistema de Gestión Académica',
                    #                 'saludo': 'Estimado' if profesor.persona.sexo.id == 2 else 'Estimada',
                    #                 'docente': profesor.persona,
                    #                 'numero': planificarponencias.id,
                    #                 'fecha': datetime.now().date(),
                    #                 'hora': datetime.now().time(),
                    #                 't': miinstitucion()},
                    #                profesor.persona.lista_emails_envio(),
                    #                [],
                    #                cuenta=CUENTAS_CORREOS[0][1])

                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

        elif action == 'editsolicitud':
            try:
                form = SolicitudDevolucionForm(request.POST, request.FILES)
                ingresarcuenta = request.POST['ingresarcuenta']
                solicitud = SolicitudDevolucionDinero.objects.get(pk=int(encrypt(request.POST['id'])))
                cuentabancaria = CuentaBancariaPersona.objects.get(pk=int(encrypt(request.POST['idcuenta'])))

                if 'archivopago' in request.FILES:
                    arch = request.FILES['archivopago']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]

                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb. [Comprobante de Dep+osito]"})
                    if not exte.lower() == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf [Comprobante de Depósito]"})

                if 'archivocedula' in request.FILES:
                    arch = request.FILES['archivocedula']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]

                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb. [Cédula Solicitante]"})
                    if not exte.lower() == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf [Cédula Solicitante]"})

                if 'archivocertificado' in request.FILES:
                    arch = request.FILES['archivocertificado']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]

                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb. [Certificado de Cuenta Bancaria]"})
                    if not exte.lower() == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf [Certificado de Cuenta Bancaria]"})

                if form.is_valid():
                    if form.cleaned_data['monto'] < 1 or form.cleaned_data['monto'] > 500:
                        return JsonResponse({"result": "bad", "mensaje": u"El monto debe estar en el rango de 1 a 500"})
                    if ingresarcuenta == 'S':
                        if len(form.cleaned_data['numerocuenta'].strip()) < 5:
                            return JsonResponse({"result": "bad", "mensaje": u"El número de cuenta bancaria debe tener mínimo 5 dígitos."})

                        if CuentaBancariaPersona.objects.values('id').filter(numero=form.cleaned_data['numerocuenta'], status=True).exclude(pk=cuentabancaria.id).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"El número de cuenta bancaria ya existe"})

                    solicitud.motivo = form.cleaned_data['motivo']
                    solicitud.monto = form.cleaned_data['monto']
                    solicitud.estado = 1
                    solicitud.save(request)

                    if 'archivopago' in request.FILES:
                        archivodeposito = request.FILES['archivopago']
                        archivodeposito._name = generar_nombre("deposito", archivodeposito._name)
                        solicitud.archivodeposito = archivodeposito

                    if 'archivocedula' in request.FILES:
                        archivocedula = request.FILES['archivocedula']
                        archivocedula._name = generar_nombre("cedula", archivocedula._name)
                        solicitud.archivocedula = archivocedula

                    solicitud.save(request)

                    if ingresarcuenta == 'S':
                        cuentabancaria.banco = form.cleaned_data['banco']
                        cuentabancaria.tipocuentabanco = form.cleaned_data['tipocuenta']
                        cuentabancaria.numero = form.cleaned_data['numerocuenta'].strip()

                        if 'archivocertificado' in request.FILES:
                            archivocertificado = request.FILES['archivocertificado']
                            archivocertificado._name = generar_nombre("certificadocuenta", archivocertificado._name)
                            cuentabancaria.archivo = archivocertificado

                        cuentabancaria.save(request)

                    if solicitud.solicituddevoluciondinerorecorrido_set.filter(status=True).count() > 1:
                        # rinferior = solicitud.solicituddevoluciondinerorecorrido_set.filter(status=True).order_by('-id')[1:][0]
                        rinferior = solicitud.solicituddevoluciondinerorecorrido_set.filter(status=True).order_by('-id')[0]
                        if rinferior.estado != 1:
                            recorrido = SolicitudDevolucionDineroRecorrido(solicituddevolucion=solicitud,
                                                                           fecha=datetime.now().date(),
                                                                           observacion='SOLICITUD ACTUALIZADA POR ESTUDIANTE',
                                                                           estado=1
                                                                           )
                            recorrido.save(request)

                    log(u'Editó solicitud de devolución: %s' % solicitud, request, "edit")

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

            if action == 'addsolicitud':
                try:
                    data['title'] = u'Agregar Solicitud de Devolución'

                    cuentabancaria = persona.cuentabancaria()
                    data['ingresarcuenta'] = False if cuentabancaria else True

                    if cuentabancaria:
                        form = SolicitudDevolucionForm(initial={
                                                        'banco': cuentabancaria.banco,
                                                        'numerocuenta': cuentabancaria.numero,
                                                        'tipocuenta': cuentabancaria.tipocuentabanco
                        })
                    else:
                        form = SolicitudDevolucionForm()

                    data['form'] = form
                    return render(request, "alu_devoluciondinero/addsolicitud.html", data)
                except Exception as ex:
                    pass

            elif action == 'editsolicitud':
                try:
                    data['title'] = u'Editar Solicitud de Devolución'

                    solicitud = SolicitudDevolucionDinero.objects.get(pk=int(encrypt(request.GET['id'])))
                    cuentabancaria = solicitud.persona.cuentabancaria()

                    form = SolicitudDevolucionForm(initial={'motivo': solicitud.motivo,
                                                            'monto': solicitud.monto,
                                                            'banco': cuentabancaria.banco,
                                                            'numerocuenta': cuentabancaria.numero,
                                                            'tipocuenta': cuentabancaria.tipocuentabanco,
                    })

                    data['idsolicitud'] = solicitud.id
                    data['idcuenta'] = cuentabancaria.id
                    data['ingresarcuenta'] = False if cuentabancaria.estadorevision == 2 else True
                    data['form'] = form
                    return render(request, "alu_devoluciondinero/editsolicitud.html", data)
                except Exception as ex:
                    pass

            elif action == 'delsolicitud':
                try:
                    data['title'] = u'Eliminar Solicitud'
                    data['solicitud'] = solicitud = SolicitudDevolucionDinero.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "alu_devoluciondinero/deletesolicitud.html", data)
                except Exception as ex:
                    pass

            elif action == 'mostrarrecorrido':
                try:
                    data = {}
                    data['solicitud'] = solicitud = SolicitudDevolucionDinero.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['recorrido'] = solicitud.solicituddevoluciondinerorecorrido_set.filter(status=True).order_by('id')
                    template = get_template("alu_devoluciondinero/recorridosolicitud.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            return HttpResponseRedirect(request.path)
        else:
            try:
#                 lista = [75823,
# 72628,75723,73026,78940,77232,77735,74027,
# 75907,73983,74053,77066,74792,75439,55807,
# 82326,74226,81056,74233,74965,78625,79813,
# 79366,75699,78172,75686,74075,55567,73022,
# 75414,75320,73941,72256,78378,50518,75018,
# 76390,75406,77148,78967,74549,80192,75713,
# 74941,73956,76849,74326,81237,75430,78192,
# 79808,77903,74243,78255,74320,74720,74224,
# 75349,76973,75319,77648,78957,74722,74146,
# 77777,77289,73123,72964,78490,74445,71481,
# 76971,74093,77256,79680,74329,74094,77804,
# 74128,74487,78246,74856,42164,80836,75027,
# 75026,82040,74695,77287,72209,75200,74421,
# 80468,75420,78880,75017,74274,73313,74482,
# 74793,73991,74087,73349,79380,37072,81312,
# 73327,79047,74028,72432,75671,82760,74174,
# 75918,74434,74263,77123,73925,75865,77555,
# 73981,77207,74970,74717,72425,71579,74092,
# 81470,74163,74944,74956,82590,76852,81755,
# 74930,72974,
# 74747, 47647, 13559, 72222, 78191, 77611, 74157, 74853, 74691, 74962, 75826, 72332, 74236,
# 72620, 74227, 76765, 82487, 80984, 74672, 72585, 72627, 75510, 74039, 49755, 75133, 77349, 72459, 75003, 74753, 74808, 74523, 73966, 77070, 73924, 74070, 73937, 80494, 73340, 77601, 74982,
# 82586, 73306, 79036, 74666, 74019, 74926, 76534, 71725, 77399, 74920, 74519, 82406, 77251, 79253, 74316, 74296, 5386, 82316, 81057, 74276, 75014, 73326, 81751, 75164, 74066, 77640, 76931, 74089, 77575, 74209, 80269, 74502, 81425, 74551, 80645, 76449, 79555, 76696, 72983, 75499, 39640, 74464, 74052, 74071, 72951, 79978, 74473, 32755, 73935, 75161, 79308, 77925, 74215, 73168, 72294, 79029, 76989, 75348, 82086, 72659, 78487, 74149, 73426, 74513, 72594, 75020, 74724, 76204, 74077, 76052, 74698, 75557, 75986, 76124, 72526, 74008, 72421,
# 74935, 75063, 74214, 74011, 74643, 73173, 77339, 77936, 77455, 80296, 76208, 78227, 73118, 72975, 75558, 76287, 74200, 76175, 74381, 76184, 74267, 74492, 74283, 72735, 73960, 75606, 77269, 52862, 73986, 74069, 76223, 76993, 76026, 73395, 78426, 74687, 82826,
# 72527, 81982, 74415, 75416, 74903, 74202, 76086, 72588, 76255, 77253, 72546, 79931, 72778, 74509, 71409, 81365, 73078, 75982, 81934, 74607, 80781, 75475, 76049, 74198, 79095, 45211, 14800, 75904, 80071, 74196, 77941, 74103, 75099, 73369, 74686, 78139, 81424, 77124, 71575, 22516, 78711, 76307, 73623, 76099, 76125, 78338, 74827, 73872, 72497, 82545, 74229, 74874, 74210, 77483, 73621, 73631, 73661, 73897, 71240, 72614, 74249, 72905, 73362, 74503, 75795, 73865, 74024, 77285, 40733, 79106, 73838,
# 77581, 46164, 72681, 73104, 74948, 75559, 73907, 73942, 74033, 75601, 72490, 73288, 76118, 75304, 80585, 78853, 73827, 46323, 75249, 73634, 40998, 72936, 71716, 73371, 80637, 74177, 75168, 75854, 72307, 73940, 73632, 77029, 77567, 74403, 74096, 78020, 74222, 72280, 77812, 75466, 74444, 74472, 73688, 73849, 80670, 81848, 72841, 74466, 76227, 77281, 76513, 74606, 74921, 75540, 75206, 75580, 73414, 74949, 77843, 73606, 74459, 74789,
# 75075, 77374, 77800, 74040, 78294, 74268, 74575, 74241, 80047, 80999, 73625, 80548, 73964, 75794, 73729, 74743, 78024, 72183, 74942, 75932, 81046, 82232, 75123, 73400, 73830, 72534, 72413, 73751, 73644, 73854, 75311, 80563, 72436, 77720, 79769, 78381, 75207, 41001, 77305, 73857, 73639, 77625, 76074, 36313, 75141, 76037, 73364, 76595, 76134, 79544, 75494, 75197, 44637, 76143, 76720, 74328, 73650, 74591, 73963, 75818, 72752, 73895, 75910, 76053, 48357, 76230, 76213, 43581, 73256, 81988, 74021, 73701, 27243, 79894, 75853, 75266, 73269, 76269, 75966, 75958, 72536, 74823, 78567, 76136, 74203, 77874, 81030, 77426,
# 74298, 74734, 36950, 74216, 76303, 75539, 75448, 81329, 75901, 77763, 72206, 80998, 72397, 73189, 73515, 73253, 73510, 73262, 74649, 72657, 39412, 77296, 79501, 77343, 72598, 75299, 48768, 76714, 74314, 77133, 78513,
# 75599, 77524, 76129, 77617, 74330, 76356, 73636, 74173, 72959, 74469, 79506, 76930, 80685, 75419, 75952, 74850, 75594, 81484, 82119, 3920, 78627, 77186, 79056, 73695, 75620, 75954, 73598, 74752, 81202, 74899, 77303, 74486, 72877, 74095, 73268, 75013, 72389, 78594, 74981, 79351, 73702, 79461, 76076, 81854, 81257, 74153, 80918, 80816, 74614, 80498, 73074, 72383, 79905,
# 81914, 75843, 30794, 81200, 80758, 76127, 49467, 74805, 74804, 74872, 74042, 72927, 81215, 82417, 77246, 82671, 75886, 82352, 73708, 75139, 73903, 74700, 79498, 74350, 79547, 74727, 75830, 74121, 72892, 73870, 76274, 74002, 76286, 76288, 77561, 75827, 76094, 76732, 74012, 79048, 79684, 79698, 74362, 81040, 77234, 73643, 73993, 75998, 74373, 75006, 80653, 74064, 82635, 76382, 73544, 81461, 76870, 79312, 73824, 74180, 73853, 75418, 73408, 40717, 76162, 76171, 77206, 75692, 75323, 73839, 74029, 73299, 76821, 76856,
# 77685, 74388, 78590, 72757, 73731, 75912, 76041, 49056, 52025, 74928, 78789, 77273, 73193, 75967, 72607, 79860, 73665, 76627, 78767, 81937, 78014, 81043, 74225, 81584, 77403, 77049, 75091, 73105, 74797, 74626, 76948, 82667, 78623, 79145, 74407,
#                          73683
# ]
                # 41044
                solicitudes = SolicitudDevolucionDinero.objects.filter(persona=persona, status=True).order_by('-id')
                cuentabancaria = persona.cuentabancaria()

                # if persona.id in lista:
                    #if solicitudes or cuentabancaria:
                if solicitudes:
                    data['mostrarboton'] = False
                else:
                    # Fecha limite para mostrar boton Agregar
                    fechadisponible = datetime.strptime('2021-12-31', '%Y-%m-%d').date()
                    fechaactual = datetime.now().date()
                    data['mostrarboton'] = True if fechaactual.__le__(fechadisponible) else False
                # else:
                #     data['mostrarboton'] = False

                data['title'] = 'Listado de Solicitudes de Devolución de Dinero'
                data['solicitudes'] = solicitudes
                return render(request, "alu_devoluciondinero/view.html", data)
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})