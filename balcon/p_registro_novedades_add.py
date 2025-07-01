# coding=latin-1
import random
import sys
import json
from cgitb import html
from datetime import datetime, timedelta
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from django.db import connection
from django.db import transaction
from django.db.models import Count, PROTECT, Sum, Avg, Min, Max
from django.db.models.query_utils import Q
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from balcon.models import ProcesoServicio, Solicitud, Agente, Servicio, HistorialSolicitud, \
    RegistroNovedadesExternoAdmision, ConfigInformacionExterno, TipoProcesoServicio
from settings import DEBUG
from sga.funciones import variable_valor, generar_nombre, log, notificacion
from sga.models import LogReporteDescarga, Matricula, MateriaAsignada, Persona, PerfilUsuario, TestSilaboSemanal, \
    TestSilaboSemanalAdmision, LinkMateriaExamen
from moodle import moodle


@transaction.atomic()
def view(request):
    data = {}
    validar_con_captcha = variable_valor('VALIDAR_CON_CAPTCHA_REGISTRO_NOVEDADES')
    if DEBUG:
        validar_con_captcha = False
    data['validar_con_captcha'] = validar_con_captcha
    data['public_key'] = public_key = variable_valor('API_GOOGLE_RECAPTCHA_PUBLIC_KEY')
    data['private_key'] = private_key = variable_valor('API_GOOGLE_RECAPTCHA_PRIVATE_KEY')
    procesoservicio = None
    agentesregistros = None
    agente_ok = False
    periodo_id = 158
    config = None
    if ConfigInformacionExterno.objects.values("id").filter(activo=True).exists():
        config = ConfigInformacionExterno.objects.filter(activo=True)[0]
        if config.fechaapertura <= datetime.now() and config.fechacierre >= datetime.now():
            procesoservicio = config.informacion.servicio
            agente_ok = config.agente_ok
            agentesregistros = config.agentesregistros()
            periodo_id = config.periodo.id if config.periodo else 158
    client_address = get_client_ip(request)
    tipo_id = 2
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'searchDocumentNew':
            try:
                capippriva = request.POST['capippriva'] if 'capippriva' in request.POST else ''
                browser = request.POST['navegador']
                ops = request.POST['os']
                cookies = request.POST['cookies']
                screensize = request.POST['screensize']
                if validar_con_captcha:
                    if not 'g-recaptcha-response' in request.POST:
                        raise NameError(u"Complete el captcha de seguridad.")
                    recaptcha_response = request.POST.get('g-recaptcha-response')
                    url = 'https://www.google.com/recaptcha/api/siteverify'
                    values = {'secret': private_key,
                              'response': recaptcha_response}
                    aData = urlencode(values)
                    aData = aData.encode('utf-8')
                    req = Request(url, aData)
                    response = urlopen(req)
                    result = json.loads(response.read().decode())
                    if not result['success']:
                        raise NameError(u"ReCaptcha no válido. Vuelve a intentarlo..")

                if not 'documento' in request.POST or not request.POST['documento']:
                    raise NameError(u"Número de cédula o pásaporte incorrecto")
                documento = (request.POST['documento']).strip()
                if documento == '':
                    raise NameError(u"Número de cédula o pásaporte incorrecto")
                if not Matricula.objects.values("id").filter(Q(inscripcion__persona__cedula=documento) | Q(inscripcion__persona__pasaporte=documento), nivel__periodo_id=periodo_id, status=True).exists():
                    raise NameError(u"No registra matricula en el curso de nivelación de carrera 2S-2021")

                matricula = Matricula.objects.filter(Q(inscripcion__persona__cedula=documento) | Q(inscripcion__persona__pasaporte=documento), nivel__periodo_id=periodo_id, status=True).first()
                # materiaasignadas = MateriaAsignada.objects.filter(matricula=matricula, retiramateria=False).exclude(materia__asignaturamalla__asignatura_id=4837)
                materiaasignadas = MateriaAsignada.objects.filter(matricula=matricula, retiramateria=False, status=True)
                data['matricula'] = matricula
                data['materiaasignadas'] = materiaasignadas
                data['agente_ok'] = agente_ok
                data['agentes'] = agentesregistros
                data['config'] = config
                template = get_template("p_registro_novedades/registro.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", 'mensaje': u'Ocurrio un error al consultar los datos. %s' % ex})

        if action == 'loadActividad':
            try:
                ma_id = request.POST['id']
                if not MateriaAsignada.objects.filter(pk=ma_id).exists():
                    raise NameError(u"Materia no encontrada")
                materiasignada = MateriaAsignada.objects.get(pk=ma_id)
                actividades = []
                semana = config.fechaactividad.isocalendar()[1] if config.fechaactividad else None
                tests = TestSilaboSemanalAdmision.objects.filter(status=True, silabosemanal__silabo__materia=materiasignada.materia).exclude(titulo__icontains='DIAGNÓSTICO')
                examenes = LinkMateriaExamen.objects.filter(status=True, materia=materiasignada.materia)
                tests1 = tests2 = None
                if semana:
                    tests1 = tests.filter(silabosemanal__semana=semana)
                if config.actividad:
                    tests2 = tests.filter(titulo__icontains=config.actividad)
                if tests1 or tests2:
                    if tests1 and tests2:
                        tests = tests1 | tests2
                    if tests1:
                        tests = tests1
                    if tests2:
                        tests = tests2
                if config.tipo_actividad == 1 or config.tipo_actividad == 3:
                    for test in tests:
                        actividades.append({"id": test.id,
                                            "nombre": test.titulo,
                                            "tipo": "test"})
                if config.tipo_actividad == 2 or config.tipo_actividad == 3:
                    for exmanen in examenes:
                        actividades.append({"id": exmanen.id,
                                            "nombre": exmanen.nombre,
                                            "tipo": "examen"})

                data['actividades'] = actividades
                template = get_template("p_registro_novedades/actividadestest.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", 'mensaje': u'Ocurrio un error al consultar los datos. %s' % ex})

        if action == 'saveSolicitud':
            try:
                agenteregistro = None
                if agente_ok:
                    if not 'agente' in request.POST or not request.POST['agente']:
                        raise NameError(u"Seleccione un agente de registro")
                    if not agentesregistros:
                        raise NameError(u"No existe agente de registro configurados")
                    if not agentesregistros.filter(pk=request.POST['agente']).exists():
                        raise NameError(u"No existe agente de registro configurados")
                    agenteregistro = agentesregistros.filter(pk=request.POST['agente']).first()

                if not 'asignatura' in request.POST or not request.POST['asignatura']:
                    raise NameError(u"Seleccione una asignatura")

                if int(request.POST['asignatura']) == 0:
                    raise NameError(u"Seleccione una asignatura")

                if int(request.POST['actividad']) == 0:
                    raise NameError(u"Seleccione una actividad")

                if not 'tipo' in request.POST or not request.POST['tipo']:
                    raise NameError(u"Actividad no identificada")

                _type = request.POST['tipo']
                if not _type in ['test', 'examen']:
                    raise NameError(u"Actividad no identificada")

                if not 'causal' in request.POST or not request.POST['causal']:
                    raise NameError(u"Seleccione una causal")

                if int(request.POST['causal']) == 0:
                    raise NameError(u"Seleccione una causal")

                if not 'motivo' in request.POST or not request.POST['motivo']:
                    raise NameError(u"Ingrese un motivo")

                if request.POST['motivo'] == '':
                    raise NameError(u"Ingrese un motivo")

                if not 'persona_id' in request.POST or not request.POST['persona_id']:
                    raise NameError(u"Persona no encontrada")

                if not 'matricula_id' in request.POST or not request.POST['matricula_id']:
                    raise NameError(u"Matricula no encontrada")

                if not procesoservicio:
                    raise NameError(u"No existe el servicio configurado")
                arch = None
                if 'archivo' in request.FILES:
                    arch = request.FILES['archivo']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 8388608:
                        raise NameError(u"El tamaño del archivo es mayor a 8 MB")
                    if not exte.lower() in ("pdf"):
                        raise NameError(u"Solo se permite archivos pdf")
                    arch._name = generar_nombre("solicitud_", arch._name)
                if not Persona.objects.filter(pk=request.POST['persona_id']).exists():
                    raise NameError(u"Persona no encontrada")
                persona = Persona.objects.get(pk=request.POST['persona_id'])
                if not Matricula.objects.filter(pk=request.POST['matricula_id']).exists():
                    raise NameError(u"Matricula no encontrada")
                matricula = Matricula.objects.get(pk=request.POST['matricula_id'])
                if not MateriaAsignada.objects.filter(pk=int(request.POST['asignatura'])).exists():
                    raise NameError(u"Seleccione una asignatura")
                if not TipoProcesoServicio.objects.filter(pk=int(request.POST['causal'])).exists():
                    raise NameError(u"Seleccione una causa")
                causal = TipoProcesoServicio.objects.get(pk=int(request.POST['causal']))
                materiaasignada = MateriaAsignada.objects.get(pk=int(request.POST['asignatura']))
                actividad = None

                if _type == 'test':
                    if not TestSilaboSemanalAdmision.objects.filter(pk=int(request.POST['actividad'])).exists():
                        raise NameError(u"Seleccione una actividad")
                    actividad = TestSilaboSemanalAdmision.objects.get(pk=int(request.POST['actividad']))
                    actividad_titulo = actividad.titulo
                    if RegistroNovedadesExternoAdmision.objects.filter(matricula=matricula, materiaasignada=materiaasignada, test=actividad).exists():
                        raise NameError(u"Solicitud ya fue registrada previamente")
                elif _type == 'examen':
                    if not LinkMateriaExamen.objects.filter(pk=int(request.POST['actividad'])).exists():
                        raise NameError(u"Seleccione una actividad")
                    actividad = LinkMateriaExamen.objects.get(pk=int(request.POST['actividad']))
                    actividad_titulo = actividad.nombre
                    if RegistroNovedadesExternoAdmision.objects.filter(matricula=matricula, materiaasignada=materiaasignada, examen=actividad).exists():
                        raise NameError(u"Solicitud ya fue registrada previamente")

                if not actividad:
                    raise NameError(u"Actividad no identificada")
                ultimasoli = Solicitud.objects.filter(solicitante=persona).order_by('numero').last()
                numsoli = ultimasoli.numero + 1 if ultimasoli else 1
                perfil = PerfilUsuario.objects.filter(inscripcion=matricula.inscripcion).first()
                # causal_nombre = u"PROBLEMAS EN PLATAFORMA" if int(request.POST['causal']) == 1 else u"ENFERMEDAD"
                descripcion = f"Asignatura: {materiaasignada.materia.asignaturamalla.asignatura.nombre}, de la actividad: {actividad_titulo}, por la causal: {causal.nombre}, con la observación: {request.POST['motivo']}"
                if agenteregistro:
                    descripcion = f"{descripcion} registrado por el agente: {agenteregistro.nombre_completo_inverso()} - {agenteregistro.cedula}"

                # if Solicitud.objects.filter(Q(descripcion__icontains=f"Asignatura: {materiaasignada.materia.asignaturamalla.asignatura.nombre}"), solicitante=persona, tipo=tipo_id, perfil=perfil).exists():
                #     raise NameError(u"Solicitud ya fue registrada previamente")
                soli = Solicitud(descripcion=descripcion,
                                 tipo=tipo_id,
                                 solicitante=persona,
                                 perfil=perfil,
                                 estado=1,
                                 numero=numsoli,
                                 archivo=arch)
                soli.save()
                registro = None
                if _type == 'test':
                    registro = RegistroNovedadesExternoAdmision(persona=matricula.inscripcion.persona,
                                                                matricula=matricula,
                                                                materiaasignada=materiaasignada,
                                                                tipoprocesoservicio=causal,
                                                                solicitud=soli,
                                                                test=actividad,
                                                                )
                    registro.save()
                elif _type == 'examen':
                    registro = RegistroNovedadesExternoAdmision(persona=matricula.inscripcion.persona,
                                                                matricula=matricula,
                                                                materiaasignada=materiaasignada,
                                                                tipoprocesoservicio=causal,
                                                                solicitud=soli,
                                                                examen=actividad,
                                                                )
                    registro.save()
                if registro and agenteregistro:
                    registro.agente = agenteregistro
                    registro.save()
                agentelibre = None
                if Agente.objects.filter(status=True, estado=True).exists():
                    agente = Agente.objects.filter(status=True, estado=True)
                    agenteslista = {}
                    for a in agente:
                        agenteslista[a.pk] = a.total_solicitud()
                    ordenados = sorted(agenteslista.items(), key=lambda x: x[1])
                    agentelibre = Agente.objects.get(pk=ordenados[0][0])
                    soli.agente = agentelibre
                soli.save(request)
                if procesoservicio:
                    historial = HistorialSolicitud(servicio=procesoservicio,
                                                   solicitud=soli,
                                                   asignadorecibe=agentelibre.persona if agentelibre else None,
                                                   tiposervicio=causal)
                    historial.save(request)
                    cuerpo = ('Ha recibido una solicitud de %s' % soli)
                    notificacion("Solicitud de %s en balcón de servicios" % soli.solicitante, cuerpo, soli.agente.persona, None, 'adm_solicitudbalcon', soli.id, 1, 'sga', Solicitud, request)
                    if not DEBUG:
                        tipourl = 2
                        persona = matricula.inscripcion.persona
                        periodo = matricula.nivel.periodo
                        username = persona.usuario.username
                        bestudiante = moodle.BuscarUsuario(periodo, tipourl, 'username', username)
                        estudianteid = 0
                        if not bestudiante:
                            bestudiante = moodle.BuscarUsuario(periodo, tipourl, 'username', username)
                        if bestudiante['users']:
                            if 'id' in bestudiante['users'][0]:
                                estudianteid = bestudiante['users'][0]['id']
                        else:
                            raise NameError(u"Usuario de aula virtual no encontrado, favor contactarse con el Departamento de Servicios Informáticos")
                        if estudianteid:
                            quizid = actividad.get_test_id()
                            if quizid:
                                response = moodle.ObtenerIntentosTest(periodo, tipourl, quizid, estudianteid)
                                intentos = response['attempts'] if response and 'attempts' in response else None
                                if intentos:
                                    obsIntentos = []
                                    contI = 1
                                    for intento in intentos:
                                        timestart = datetime.fromtimestamp(intento['timestart'])
                                        timefinish = datetime.fromtimestamp(intento['timefinish'])
                                        obsIntentos.append(u"Intento %s desde %s hasta %s" % (contI, timestart.__str__(), timefinish.__str__()))
                                        contI += 1
                                    soli.estado = 2
                                    soli.save()
                                    historialbase = HistorialSolicitud.objects.filter(solicitud=soli).last()
                                    nota = HistorialSolicitud(solicitud=soli,
                                                              asignaenvia=Persona.objects.get(pk=1),
                                                              observacion=u"Su solicitud ha sido rechazada. Se registra intentos: %s " % (", ".join([str(x) for x in obsIntentos])),
                                                              servicio=historialbase.servicio,
                                                              asignadorecibe=historialbase.asignadorecibe,
                                                              departamentoenvia=historialbase.departamentoenvia,
                                                              departamento=historialbase.departamento,
                                                              estado=4)
                                    nota.save(request)
                                    log(u'Rechazo Solicitud en balcon: %s por motivo de intentos' % soli, request, "add")

                                    cuerpo = ('Su solicitud ha sido rechazada. \n Motivo: %s' % nota.observacion)
                                    notificacion('Estimado(a) %s se ha rechazado su solicitud' % persona, cuerpo, soli.solicitante, None, 'alu_solicitudbalcon?action=misolicitudes', soli.id, 1, 'sga', Solicitud, request)

                return JsonResponse({"result": "ok", "mensaje": u"Solicitud se guardo correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos: %s" % ex})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            return HttpResponseRedirect('/p_registro_novedades')
        else:
            try:
                data['title'] = u"Adicionar un registro de novedades"
                data['config'] = config
                data['procesoservicio'] = procesoservicio
                if not procesoservicio:
                    raise NameError(u"Proceso no activo")
                return render(request, "p_registro_novedades/add.html", data)

            except Exception as ex:
                return HttpResponseRedirect('/p_registro_novedades?info=%s' % ex)


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
