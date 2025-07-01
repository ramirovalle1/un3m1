# -*- coding: latin-1 -*-
import random
import sys

from django.db import transaction
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.db.models.query_utils import Q
from datetime import datetime

from django.template.loader import get_template

from balcon.forms import SolicitudBalconExternoForm
from balcon.models import Solicitud, Proceso, ProcesoServicio, Informacion, Agente, RequisitosSolicitud, HistorialSolicitud, RequisitosConfiguracion, Servicio
from decorators import last_access
from sga.funciones import remover_caracteres_especiales_unicode, generar_nombre, log, variable_valor

from sga.models import Persona, DetalleConfiguracionDescuentoPosgrado, AperturaPeriodoCambioCarrera, SolicitudCambioCarrera, CarrerasCambioCarrera, Periodo, DocumentosSolicitudCambioCarrera, InstitucionEducacionSuperior, ReponsableCambioCarrera, Pais, Discapacidad, PerfilUsuario, Externo
from sga.templatetags.sga_extras import encrypt


@last_access
@transaction.atomic()
def view(request):
    data = {}
    data['tipoentrada'] = 'SGA'
    # data['periodo']= periodo = request.session['periodo']
    data['url_'] = request.path
    data['currenttime'] = datetime.now()
    data['activo'] = activo = variable_valor('BALCON_EXTERNO_ACTIVO')
    if not eval(activo[0]):
        return render(request, "alu_solicitudbalcon/bloqueo_urlexterno.html", data)

    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'addsolicitud':
                try:
                    with transaction.atomic():
                        newfile = None
                        # tipo = int(request.POST['tipo'])
                        form = SolicitudBalconExternoForm(request.POST, request.FILES)
                        if form.is_valid():
                            procesoservicio = ProcesoServicio.objects.get(pk=int(request.POST['procesoservicio']))
                            subesolicitud = procesoservicio.proceso.subesolicitud
                            solicitante = Persona.objects.get(pk=int(request.POST['persona']))
                            perfil = None
                            if solicitante.perfilusuario_set.filter(visible=True).exists():
                                perfil = solicitante.perfilusuario_set.filter(visible=True).first()
                            else:
                                transaction.set_rollback(True)
                                return JsonResponse({"result": True, "mensaje": "Persona no cuenta con perfil usuario"}, safe=False)
                            ultimasoli = Solicitud.objects.filter(solicitante=solicitante).order_by('numero').last()
                            numsoli = ultimasoli.numero + 1 if ultimasoli else 1
                            soli = Solicitud(descripcion=form.cleaned_data['descripcion'].upper(),
                                             tipo=2,
                                             solicitante=solicitante,
                                             perfil=perfil,
                                             estado=1,
                                             numero=numsoli)
                            if subesolicitud:
                                if 'doc_solicitud' in request.FILES:
                                    newfile = request.FILES['doc_solicitud']
                                    extension = newfile._name.split('.')
                                    tam = len(extension)
                                    exte = extension[tam - 1]
                                    if newfile.size > 4194304:
                                        return JsonResponse(
                                            {"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                                    if exte in ['pdf', 'jpg', 'jpeg', 'png', 'jpeg', 'peg']:
                                        newfile._name = generar_nombre("solicitud_", newfile._name)
                                    else:
                                        return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})
                                    soli.archivo = newfile
                                else:
                                    transaction.set_rollback(True)
                                    return JsonResponse({"result": True, "mensaje": "FALTA SUBIR SOLICITUD"}, safe=False)
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
                            requisitos = procesoservicio.requisitosconfiguracion_set.filter(status=True)
                            for req in requisitos:
                                if not 'doc_{}'.format(req.requisito.pk) in request.FILES:
                                    if req.obligatorio:
                                        nombredocumento = req.requisito.descripcion
                                        transaction.set_rollback(True)
                                        return JsonResponse({"result": True, "mensaje": "FALTA SUBIR {}".format(nombredocumento)}, safe=False)
                                else:
                                    solicitante = Persona.objects.get(pk=request.POST['persona'])
                                    nombrepersona_str = solicitante.__str__().lower().replace(' ', '_')
                                    nombre = req.requisito.pk
                                    nombredoc = "doc_{}".format(req.requisito.pk)
                                    newfile = request.FILES[nombredoc]
                                    nombrefoto = '{}_{}'.format(nombrepersona_str, nombre)
                                    newfile._name = generar_nombre(nombrefoto.strip(), newfile._name)
                                    det = RequisitosSolicitud(solicitud=soli, requisito=req, archivo=newfile)
                                    det.save(request)
                            #log(u'Adiciono Solicitud para el balcon: %s' % soli, request, "add")
                            # proceso_id = int(request.POST['proceso']) if 'proceso' in request.POST and request.POST['proceso'] else 0
                            servicio_id = int(request.POST['procesoservicio']) if 'procesoservicio' in request.POST and request.POST['procesoservicio'] else 0
                            if Servicio.objects.filter(pk=servicio_id).exists():
                                historial = HistorialSolicitud(servicio_id=servicio_id,
                                                               solicitud=soli,
                                                               asignadorecibe=agentelibre.persona if agentelibre else None)
                                historial.save(request)
                                #log(u'Se asigna servicio: %s' % historial.servicio, request, "add")

                            return JsonResponse({"result": False, 'info':solicitante.cedula}, safe=False)
                        else:
                            transaction.set_rollback(True)
                            return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

            if action == 'editsolicitud':
                try:
                    with transaction.atomic():
                        filtro = Solicitud.objects.get(pk=int(encrypt(request.POST['id'])))
                        f = SolicitudBalconExternoForm(request.POST, request.FILES)
                        if f.is_valid():
                            procesoservicio = ProcesoServicio.objects.get(pk=int(request.POST['procesoservicio']))
                            subesolicitud = procesoservicio.proceso.subesolicitud

                            filtro.descripcion = f.cleaned_data['descripcion']
                            if subesolicitud:
                                if 'doc_solicitud' in request.FILES:
                                    newfile = request.FILES['doc_solicitud']
                                    extension = newfile._name.split('.')
                                    tam = len(extension)
                                    exte = extension[tam - 1]
                                    if newfile.size > 4194304:
                                        return JsonResponse(
                                            {"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                                    if exte in ['pdf', 'jpg', 'jpeg', 'png', 'jpeg', 'peg']:
                                        newfile._name = generar_nombre("solicitud_", newfile._name)
                                    else:
                                        return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})
                                    filtro.archivo = newfile
                                else:
                                    transaction.set_rollback(True)
                                    return JsonResponse({"result": True, "mensaje": "FALTA SUBIR SOLICITUD"}, safe=False)
                            filtro.save(request)
                            requisitos = procesoservicio.requisitosconfiguracion_set.filter(status=True)
                            antrequisito=RequisitosSolicitud.objects.filter(solicitud=filtro, requisito__servicio=procesoservicio)
                            if not antrequisito.exists():
                                RequisitosSolicitud.objects.filter(solicitud=filtro).delete()
                            for req in requisitos:
                                if 'doc_{}'.format(req.requisito.pk) in request.FILES:
                                    solicitante = Persona.objects.get(id=int(request.POST['persona']))
                                    nombrepersona_str = solicitante.__str__().lower().replace(' ', '_')
                                    nombre = req.requisito.pk
                                    nombredoc = "doc_{}".format(req.requisito.pk)
                                    newfile = request.FILES[nombredoc]
                                    nombrefoto = '{}_{}'.format(nombrepersona_str, nombre)
                                    newfile._name = generar_nombre(nombrefoto.strip(), newfile._name)

                                    if RequisitosSolicitud.objects.filter(solicitud=filtro, requisito=req).exists():
                                        det = RequisitosSolicitud.objects.get(solicitud=filtro, requisito=req)
                                        det.archivo=newfile
                                    else:
                                        newfile._name = generar_nombre(nombrefoto.strip(), newfile._name)
                                        det = RequisitosSolicitud(solicitud=filtro, requisito=req, archivo=newfile)
                                    det.save(request)
                            log(u'Edito Solicitud para el balcon: %s' % filtro, request, "editsolicitud")
                            servicio_id = int(request.POST['procesoservicio']) if 'procesoservicio' in request.POST and request.POST['procesoservicio'] else 0
                            historial = HistorialSolicitud.objects.get(solicitud=filtro)
                            historial.servicio_id=servicio_id
                            historial.save(request)

                            log(u'Modificó Solicitud Balcon: %s' % filtro, request, "edit")
                            return JsonResponse({"result": False,'info':filtro.solicitante.cedula}, safe=False)
                        else:
                            transaction.set_rollback(True)
                            return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

            if action == 'addregistro':
                try:
                    hoy, datospersona = datetime.now().date(), None
                    cedula = request.POST['cedula'].strip().upper()
                    tipoiden = request.POST['id_tipoiden']
                    nombres = request.POST['nombres']
                    apellido1 = request.POST['apellido1']
                    apellido2 = request.POST['apellido2']
                    email = request.POST['email']
                    telefono=request.POST['telefono']
                    nacionalidad=request.POST['nacionalidad']
                    paisnacimiento=request.POST['pais']
                    provincianacimiento=request.POST['provincia']
                    cantonnacimiento=request.POST['canton']
                    lgtbi=request.POST['lgtbi']
                    genero = request.POST['genero']
                    if not genero:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"Por favor seleccione su genero"})
                    if Persona.objects.filter(Q(pasaporte=cedula) |
                                              Q(cedula=cedula) |
                                              Q(cedula=cedula[2:]) |
                                              Q(pasaporte=('VS' + cedula)), status=True).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad",
                                             "mensaje": u"Usted ya se encuentra registrado, consulte su informacion"})
                    if tipoiden == '1':
                        if len(cedula) == 10:
                            datospersona = Persona(cedula=cedula, nombres=nombres, apellido1=apellido1,
                                                   apellido2=apellido2, email=email, nacimiento=datetime.now().date(),
                                                   telefono=telefono, nacionalidad=nacionalidad, paisnacimiento_id=paisnacimiento,
                                                   provincianacimiento_id=provincianacimiento, cantonnacimiento_id=cantonnacimiento,
                                                   sexo_id=genero, lgtbi=lgtbi)
                            datospersona.save(request)
                        else:
                            transaction.set_rollback(True)
                            return JsonResponse({'result': 'bad', "mensaje": u"Cédula solo debe tener 10 digitos"})
                    if tipoiden == '2':
                        if cedula[:2] == u'VS':
                            datospersona = Persona(pasaporte=cedula, nombres=nombres, apellido1=apellido1,
                                                   apellido2=apellido2, email=email, nacimiento=datetime.now().date(),
                                                   telefono=telefono, nacionalidad=nacionalidad, paisnacimiento_id=paisnacimiento,
                                                   provincianacimiento_id=provincianacimiento, cantonnacimiento_id=cantonnacimiento,
                                                   sexo_id=genero, lgtbi=lgtbi)
                            datospersona.save(request)
                        else:
                            transaction.set_rollback(True)
                            return JsonResponse({'result': 'bad', "mensaje": u"Pasaporte mal ingresado, no olvide colocar VS al inicio."})
                    if not Externo.objects.filter(persona=datospersona).exists():
                        externo=Externo(persona=datospersona, telefonocontacto=telefono)
                        externo.save(request)
                        perfil = PerfilUsuario(persona=datospersona, externo=externo)
                        perfil.save(request)

                    return JsonResponse({'result': 'ok', "mensaje": u"Se registro exitosamente"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})

            if action == 'consultacedula':
                try:
                    cedula = request.POST['cedula'].strip().upper()
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
                    if Persona.objects.filter(Q(pasaporte=cedula) | Q(cedula=cedula) | Q(pasaporte=('VS'+cedula)) | Q(cedula=cedula[2:])).exists():
                        datospersona = Persona.objects.get(Q(pasaporte=cedula) | Q(cedula=cedula) | Q(pasaporte=('VS'+cedula)) | Q(cedula=cedula[2:]))
                    if datospersona:
                        if datospersona.sexo:
                            idgenero = datospersona.sexo_id
                        return JsonResponse({"result": "ok", "apellido1": datospersona.apellido1, "apellido2": datospersona.apellido2,
                                             "nombres": datospersona.nombres, "email": datospersona.email, "telefono": datospersona.telefono, "idgenero": idgenero,
                                             'nacionalidad':datospersona.nacionalidad})
                    else:
                        return JsonResponse({"result": "no"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'listservicio':
                try:
                    lista = []
                    procesos = Proceso.objects.get(pk=request.POST['id'], status=True)
                    idslist = ProcesoServicio.objects.filter(proceso=procesos, status=True).values_list('id', flat=True)
                    informaciones = Informacion.objects.filter(mostrar=True, tipo=2, status=True, servicio_id__in=idslist).order_by('descripcion')
                    for informacion in informaciones:
                        lista.append([informacion.id, informacion.descripcion, informacion.servicio.id])
                    data = {"result": "ok", "lista": lista}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'serviciourl':
                try:
                    informacion = Informacion.objects.get(pk=int(request.POST['ids']))
                    servicio = ProcesoServicio.objects.get(pk=informacion.servicio_id, status=True)
                    if servicio.url:
                        return JsonResponse({'result': 'ok', "mensaje1": servicio.url})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})


            if action == 'delsolicitud':
                try:
                    with transaction.atomic():
                        solicitud = Solicitud.objects.get(id=int(encrypt(request.POST['id'])))
                        solicitud.status = False
                        solicitud.save(request)
                        log(u'Elimincion de solicitud: %s' % solicitud, request, "delsolicitud")
                        res_json = {"error": False}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
            if action=='addsolicitud':
                try:
                    data['id_persona'] = int(encrypt(request.GET['idpersona']))
                    data['procesos'] = procesos =  Proceso.objects.filter(status=True, activoadmin=True)
                    form=SolicitudBalconExternoForm()
                    form.fields['servicio'].queryset = Informacion.objects.none()
                    data['form'] = form
                    template = get_template("alu_solicitudbalcon/modal/formsolicitudexterna.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    mensaje = 'Intentelo mas tarde'
                    return JsonResponse({"result": False, "mensaje": mensaje})

            if action== 'editsolicitud':
                try:
                    data['id_persona'] = int(encrypt(request.GET['idpersona']))
                    data['id'] =id= request.GET['id']
                    data['filtro'] = filtro = Solicitud.objects.get(pk=int(encrypt(id)))
                    historial = HistorialSolicitud.objects.get(solicitud=filtro, status=True)
                    data['proceso']=historial.servicio.proceso.id
                    info=Informacion.objects.get(servicio=historial.servicio, status=True)
                    data['informacion']=info.id
                    form=SolicitudBalconExternoForm(initial=model_to_dict(filtro))
                    form.fields['servicio'].queryset = Informacion.objects.none()
                    data['form'] = form
                    template = get_template("alu_solicitudbalcon/modal/formsolicitudexterna.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'requisitos':
                try:
                    lista = []
                    servicio = request.GET['id']
                    servicio = ProcesoServicio.objects.get(pk=servicio)
                    requisitosconf = RequisitosConfiguracion.objects.filter(status=True, servicio=servicio)
                    subesolicitud=servicio.proceso.subesolicitud

                    for requisitoconf in requisitosconf:
                        lista.append([requisitoconf.id, requisitoconf.obligatorio, requisitoconf.requisito.id, requisitoconf.requisito.descripcion])

                    data = {'result':'ok', 'lista':lista, 'sol':subesolicitud}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action=='consultasolicitud':
                try:
                    cedula=request.GET['cedula'].upper()
                    email=request.GET['email'].lower()
                    tipo=int(request.GET['tipo'])
                    if tipo == 1:
                        if not Persona.objects.filter(cedula=cedula).exists():
                                return JsonResponse({"result": 'bad',"mensaje": "Estimado usuario, para ingresar una solicitud debe realizar el registro en el botón 'Registrarse'"})
                    elif tipo == 2:
                        if not cedula[:2] == 'VS':
                            return JsonResponse({"result": 'bad',"mensaje": "Para consultar por pasaporte no olvides colocar VS al principio"})
                        if not Persona.objects.filter(pasaporte=cedula).exists():
                            return JsonResponse({"result": 'bad',"mensaje": "No se encontro registro en la aplicacion con esta identificacion"})

                    data['persona'] = persona = Persona.objects.filter(Q(cedula=cedula) | Q(pasaporte=cedula),email=email, status=True).first()
                    if persona:
                        if persona.usuario and persona.usuario.is_superuser:
                            return JsonResponse({"result": 'bad', "mensaje": "No existen datos disponibles para mostrar"})
                        perfil = persona.perfilusuario_set.filter(Q(administrativo__isnull=False) | Q(profesor__isnull=False))
                        d = persona.inscripcion_set.filter(status=True)
                        if not perfil:
                            solicitudex = Solicitud.objects.filter(solicitante=persona,status=True).order_by('-id')
                            if solicitudex.filter(perfil__externo__isnull=False):
                                data['solicitudes'] = solicitudex
                            elif not d:
                                data['solicitudes'] = solicitudex
                            else:
                                return JsonResponse({"result": "bad", "mensaje": "Estimado estudiante, usted tiene una cuenta activa en el sga, por favor inicie sesión para ingresar o consultar solicitudes."})
                            template = get_template("alu_solicitudbalcon/infosolicitudexterno.html")
                            return JsonResponse({"result": 'ok', 'data': template.render(data)})
                    return JsonResponse({"result": 'bad',
                                         "mensaje": "No existen datos disponibles para mostrar"})
                except Exception as ex:
                    mensaje = 'Intentelo mas tarde'
                    return JsonResponse({"result": 'bad', "mensaje": mensaje})

            if action == 'verproceso':
                try:
                    data['title'] = u'Ver Historial'
                    data['id'] = id = request.GET['id']
                    data['filtro'] = filtro = Solicitud.objects.get(pk=int(id))
                    data['detalle'] = HistorialSolicitud.objects.filter(status=True, solicitud=filtro).order_by('pk')
                    template = get_template("adm_solicitudbalcon/verhistorial.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Solicitud de Balcon'
                data['institucion'] = u'UNIVERSIDAD ESTATAL DE MILAGRO'
                data['pais']=Pais.objects.filter(status=True)
                hoy = datetime.now().date()
                return render(request, "alu_solicitudbalcon/solicitudbalconexterno.html", data)
            except Exception as ex:
                pass