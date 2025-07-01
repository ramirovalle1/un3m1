# -*- coding: latin-1 -*-
import random

from django.contrib import messages
from django.db import transaction
from django.db.models import Count
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.db.models.query_utils import Q
from datetime import datetime

from django.template.loader import get_template

from decorators import last_access
from sga.forms import ReemplazarDocumentoCambioCarreraForm
from sga.funciones import remover_caracteres_especiales_unicode, generar_nombre, log, notificacion

from sga.models import Persona, DetalleConfiguracionDescuentoPosgrado, AperturaPeriodoCambioCarrera, \
    SolicitudCambioCarrera, CarrerasCambioCarrera, Periodo, DocumentosSolicitudCambioCarrera, \
    InstitucionEducacionSuperior, ReponsableCambioCarrera, Externo, PerfilUsuario, RequisitosCambioCarrera, Inscripcion, \
    NivelMalla
from sga.templatetags.sga_extras import encrypt


@last_access
@transaction.atomic()
def view(request):
    data = {}
    data['tipoentrada'] = 'SGA'
    data['url_'] = request.path
    data['currenttime'] = datetime.now()
    hoy = datetime.now().date()
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']
            if action == 'addregistro':
                try:
                    with transaction.atomic():
                        id = request.POST['id']
                        cedula=request.POST['cedula'].strip()
                        periodocambiocarrera = AperturaPeriodoCambioCarrera.objects.get(pk=id)
                        if hoy > periodocambiocarrera.fechacierrerecepciondocumentos:
                            return JsonResponse({'result': False, "mensaje": u"La fecha de recepción de solicitudes culminó por lo tanto usted no podra realizar una solicitud en este período"})
                        carreradestino_id = int(request.POST['carreras'])
                        puntaje = float(request.POST['puntajeobtenido'])
                        iduniversidad = request.POST['universidad']
                        universidadtext = request.POST['universidadtext']
                        email_universidad = request.POST['emailuniversidad']
                        telefono_contacto=request.POST['telefonocontacto']
                        nombre_contacto=request.POST['nombrecontacto']

                        if not SolicitudCambioCarrera.objects.filter(status=True, persona__cedula=cedula,estados__in=[0,1,3,7,4,2], periodocambiocarrera__publico=True).exists():
                            if Persona.objects.filter(Q(cedula=cedula) | Q(pasaporte=cedula), usuario__isnull=False).exists():
                                persona = Persona.objects.get(cedula=cedula, status=True)
                                for perfil in persona.perfilusuario_set.filter(status=True):
                                    if perfil.es_estudiante() and Inscripcion.objects.filter(persona=persona, carrera__coordinacion__id__in=[1, 3, 2, 5, 4, 13], activo=True).exists():
                                        return JsonResponse({'result': False,
                                                             "mensaje": u"Usted es un estudiante UNEMI por favor gestione el proceso, por la plataforma SGA UNEMI"})
                            # Datos Persona
                            hoy = datetime.now().date()
                            tipoiden = request.POST['iden']
                            nombres = request.POST['nombres']
                            apellido1 = request.POST['apellido1']
                            apellido2 = request.POST['apellido2']
                            email = request.POST['email']
                            telefono = request.POST['celular']

                            if not Persona.objects.filter(Q(pasaporte=cedula) |
                                                          Q(cedula=cedula) |
                                                          Q(cedula=cedula[2:]) |
                                                          Q(pasaporte=('VS' + cedula)), status=True).exists():

                                if tipoiden == '1':
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
                                    datospersona = Persona(pasaporte=cedula,
                                                           nombres=nombres,
                                                           apellido1=apellido1,
                                                           apellido2=apellido2,
                                                           email=email,
                                                           telefono=telefono,
                                                           nacimiento=datetime.now().date()
                                                           )
                                    datospersona.save(request)

                                externo = Externo(persona=datospersona, telefonocontacto=telefono)
                                externo.save(request)
                                perfil = PerfilUsuario(persona=datospersona, externo=externo)
                                perfil.save(request)
                            else:
                                datospersona = Persona.objects.get(Q(pasaporte=cedula) |
                                                                  Q(cedula=cedula) |
                                                                  Q(cedula=cedula[2:]) |
                                                                  Q(pasaporte=('VS' + cedula)))
                                datospersona.nombres=nombres
                                datospersona.apellido1=apellido1
                                datospersona.apellido2=apellido2
                                datospersona.email=email
                                datospersona.telefono=telefono
                                datospersona.save(request)

                            if puntaje <= 0.00:
                                transaction.set_rollback(True)
                                return JsonResponse({"result": True, "mensaje": "Debe ingresar su puntaje para continuar."},
                                                    safe=False)
                            totalsubidos = 0
                            totalsubidosmultiple = 0
                            documentos_requeridos = periodocambiocarrera.requisitos.filter(status=True,multiple=False, documentorequerido=True)
                            documentos_requeridos_multiple = periodocambiocarrera.requisitos.filter(status=True, multiple=True, documentorequerido=True)
                            if not documentos_requeridos:
                                transaction.set_rollback(True)
                                return JsonResponse({"result": True, "mensaje": "Debe subir todos los requisitos para continuar."},
                                                    safe=False)
                            # if not documentos_requeridos_multiple:
                            #     transaction.set_rollback(True)
                            #     return JsonResponse(
                            #         {"result": True, "mensaje": "Debe subir todos los requisitos para continuar."},
                            #         safe=False)

                            if not carreradestino_id or carreradestino_id <= 0:
                                transaction.set_rollback(True)
                                return JsonResponse(
                                    {"result": True, "mensaje": "Debe seleccionar una carrera para continuar."}, safe=False)

                            carreradestino = CarrerasCambioCarrera.objects.get(id=carreradestino_id)
                            if carreradestino.cupo_disponible() <= 0:
                                raise NameError("Los cupos disponibles para esta carrera están agotados.")
                            if puntaje < carreradestino.puntajerequerido:
                                transaction.set_rollback(True)
                                return JsonResponse({"result": True,
                                                     "mensaje": "El puntaje ingresado no es el correcto para la carrera seleccionada."},
                                                    safe=False)

                            for dr in documentos_requeridos:
                                if 'doc_{}'.format(dr.nombre_input()) in request.FILES:
                                    totalsubidos += 1
                                elif dr.opcional:
                                    totalsubidos += 1

                            for dm in documentos_requeridos_multiple:
                                if 'doc_{}[]'.format(dm.nombre_input()) in request.FILES:
                                    totalsubidosmultiple += 1
                                elif dm.opcional:
                                    totalsubidosmultiple += 1

                            if not totalsubidos == len(documentos_requeridos) or not totalsubidosmultiple == len(documentos_requeridos_multiple):
                                transaction.set_rollback(True)
                                return JsonResponse({"result": True, "mensaje": "Debe subir todos los requisitos."},safe=False)

                            # Permite asignar casos equitativamente a 4 administrativos con id de persona quemados
                            verificador = SolicitudCambioCarrera.objects.filter(status=True, periodocambiocarrera=periodocambiocarrera).values('id')
                            # comprobador = 0
                            # valoranterior = 0
                            # cont = 0
                            persona_admision_id = 0
                            if persona_admision_id == 0 and verificador.exists():
                                persona_admision_id = SolicitudCambioCarrera.objects.filter(status=True,periodocambiocarrera=periodocambiocarrera).values(
                                    'persona_admision_id').annotate(total=Count('id')).order_by('total')[0][
                                    'persona_admision_id']

                            # for p in responsables:
                            #     cont += 1
                            #     if not verificador.filter(persona_admision=p).exists():
                            #         persona_admision_id = p
                            #         break
                            #     elif len(verificador) >= len(responsables):
                            #         numsolicitudes = len(verificador.filter(persona_admision=p))
                            #         print(numsolicitudes)
                            #         if numsolicitudes < valoranterior or valoranterior == 0:
                            #             valormenor = numsolicitudes
                            #             per = p
                            #         elif valoranterior == numsolicitudes:
                            #             comprobador += 1
                            #
                            #         valoranterior = numsolicitudes
                            #
                            #         if comprobador == len(responsables) - 1:
                            #             rango = len(responsables) - 1
                            #             numaleatorio = random.randint(0, rango)
                            #             persona_admision_id = responsables[numaleatorio]
                            #             break
                            #         elif valormenor <= numsolicitudes and cont == len(responsables):
                            #             persona_admision_id = per
                            #             break
                            solicitud=SolicitudCambioCarrera(periodocambiocarrera=periodocambiocarrera,
                                                             carreradestino=carreradestino.carrera,
                                                             puntajeacogido=carreradestino.puntajerequerido,
                                                             puntajealumno=puntaje,
                                                             persona_admision_id=persona_admision_id,
                                                             persona_id=datospersona.id,
                                                             universidad_id=iduniversidad,
                                                             email_universidad=email_universidad,
                                                             telefono_uniersidad=telefono_contacto,
                                                             nombre_contacto=nombre_contacto,
                                                             universidadtext=universidadtext)
                            solicitud.save(request)
                            # carreradestino.cupo -= 1
                            carreradestino.save()
                            #Guarda Arvhivos individuales
                            for dr in documentos_requeridos:
                                if 'doc_{}'.format(dr.nombre_input()) in request.FILES:
                                    newfile = request.FILES['doc_{}'.format(dr.nombre_input())]
                                    extension = newfile._name.split('.')
                                    tam = len(extension)
                                    exte = extension[tam - 1]
                                    if newfile.size > 2194304:
                                        transaction.set_rollback(True)
                                        return JsonResponse(
                                            {"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 2 Mb."})
                                    if not exte.lower() in ['pdf']:
                                        transaction.set_rollback(True)
                                        return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf"})
                                    docrequerido = DocumentosSolicitudCambioCarrera(solicitud=solicitud, documento=dr)
                                    nombre_persona = remover_caracteres_especiales_unicode(
                                        datospersona.apellido1).lower().replace(' ', '_')
                                    newfile._name = generar_nombre("{}__{}".format(nombre_persona, dr.nombre_input()),
                                                                   newfile._name)
                                    docrequerido.archivo = newfile
                                    docrequerido.save(request)
                            #Guarda Archivos de Multiples
                            for dm in documentos_requeridos_multiple:
                                if 'doc_{}[]'.format(dm.nombre_input()) in request.FILES:
                                    docmultiple= request.FILES.getlist('doc_{}[]'.format(dm.nombre_input()))
                                    descripciones = request.POST.getlist('desc_{}[]'.format(dm.nombre_input()))
                                    niveles = request.POST.getlist('nivel_{}[]'.format(dm.nombre_input()))
                                    mensaje = 'Por favor complete todos los campos.'
                                    if dm.essilabo and len(docmultiple) != len(niveles) or len(docmultiple) != len(descripciones):
                                        raise NameError(mensaje)
                                    elif not dm.essilabo and len(docmultiple) != len(descripciones):
                                        raise NameError(mensaje)
                                    contador=0
                                    for drmultiple in docmultiple:
                                        nivel = None
                                        if not dm.essilabo:
                                            if descripciones[contador] == '':
                                                raise NameError(mensaje)
                                            cuerpo = dm.nombre_input()
                                        elif dm.essilabo:
                                            if descripciones[contador] == '' or niveles[contador] == '':
                                                raise NameError(mensaje)
                                            nivel = niveles[contador]
                                            cuerpo = 'silabo_' + remover_caracteres_especiales_unicode(
                                                descripciones[contador]).lower().replace(' ', '_')
                                        newfile = drmultiple
                                        extension = newfile._name.split('.')
                                        tam = len(extension)
                                        exte = extension[tam - 1]
                                        if newfile.size > 2194304:
                                            transaction.set_rollback(True)
                                            return JsonResponse(
                                                {"result": True,
                                                 "mensaje": u"Error, el tamaño del archivo {} {} es mayor a 2 Mb.".format(descripciones[contador], dm)})
                                        if not exte.lower() in ['pdf']:
                                            transaction.set_rollback(True)
                                            return JsonResponse(
                                                {"result": True, "mensaje": u"Error, solo archivos .pdf"})
                                        docrequerido = DocumentosSolicitudCambioCarrera(solicitud=solicitud,
                                                                                        nivel_id=nivel,
                                                                                        descripcion=descripciones[contador],
                                                                                        documento=dm)
                                        nombre_persona = remover_caracteres_especiales_unicode(
                                            datospersona.apellido1).lower().replace(' ', '_')
                                        newfile._name = generar_nombre(
                                            "{}__{}__{}".format(nombre_persona, cuerpo, contador),
                                            newfile._name)
                                        docrequerido.archivo = newfile
                                        docrequerido.save(request)
                                        contador+=1

                            notificacion(('SOLICITUD DE  CAMBIO DE CARRERA/IES-MODALIDAD PENDIENTE DE REVISIÓN').upper(),
                                         'Se le ha asignado una solicitud de cambio de carrera para revisión.', solicitud.persona_admision,
                                         None, '/alu_cambiocarrera?action=solicitantes&id={}&search={}'.format(
                                    solicitud.periodocambiocarrera.pk, solicitud.persona.cedula),
                                         solicitud.pk,
                                         1, 'sga', SolicitudCambioCarrera, request)
                        else:
                            return JsonResponse({'result': 'bad', "mensaje": u"Ya existe una solicitud activa con sus datos"})
                        return JsonResponse({'result':'ok',"mensaje": u"Solicitud registrada con éxito, sus datos serán validados y notificados por correo electronico.",'solicitud':solicitud.id,})
                except Exception as ex:
                    print(ex)
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": str(ex)}, safe=False)

            if action == 'buscarcarrera':
                try:
                    item = []
                    param = request.POST['term']
                    puntaje = float(request.POST['puntaje'])
                    data['periodocabiocarrera'] = apertura = AperturaPeriodoCambioCarrera.objects.filter(
                        pk=int(request.POST['periodo'])).first()
                    if 0 < puntaje <= 1000:
                        data['carreras'] = carreras = apertura.carrerascambiocarrera_set.filter(status=True,
                                                                                                carrera__nombre__icontains=param,
                                                                                                puntajerequerido__lte=puntaje).exclude(
                            Q(puntajerequerido__lte=0) | Q(cupo__lte=0)).order_by('carrera__nombre')
                        for c in carreras:
                            if c.cupo_disponible() > 0:
                                text = c.carrera.nombre_completo_inscripcion() + " - CUPO DISPONIBLE: " + str(
                                c.cupo_disponible()) + " - PUNTAJE REQUERIDO: " + str(c.puntajerequerido)
                                item.append({'id': c.id, 'text': text})
                    return JsonResponse(item, safe=False)
                except Exception as e:
                    pass

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
                    if Persona.objects.filter(Q(pasaporte=cedula) | Q(cedula=cedula) | Q(pasaporte=('VS' + cedula)) | Q(cedula=cedula[2:])).exists():
                        datospersona = Persona.objects.get(Q(pasaporte=cedula) | Q(cedula=cedula) | Q(pasaporte=('VS' + cedula)) | Q(
                                cedula=cedula[2:]))
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

            if action == 'reemplazardocumento':
                try:
                    postar = DocumentosSolicitudCambioCarrera.objects.get(id=int(request.POST['id']))
                    f = ReemplazarDocumentoCambioCarreraForm(request.POST)
                    if not 'archivo' in request.FILES:
                        transaction.set_rollback(True)
                        return JsonResponse(
                            {"result": True, "mensaje": u"Por favor seleccione un archivo."})
                    if f.is_valid():
                        postar.doccorregido = True
                        id = request.POST['solicitud']
                        soli=SolicitudCambioCarrera.objects.get(pk=id)
                        persona=Persona.objects.get(pk=soli.persona.id)
                        newfile = request.FILES['archivo']
                        extension = newfile._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if newfile.size > 2194304:
                            transaction.set_rollback(True)
                            return JsonResponse(
                                {"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 2 Mb."})
                        if not exte in ['pdf']:
                            transaction.set_rollback(True)
                            return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})
                        nombre_persona = remover_caracteres_especiales_unicode(persona.apellido1).lower().replace(' ',
                                                                                                                  '_')
                        newfile._name = generar_nombre("{}__{}".format(nombre_persona, postar.documento.nombre_input()),
                                                       newfile._name)
                        postar.archivo = newfile
                        postar.save(request)

                        # log(u'Documento Cambio Carrera %s estudiante: %s' % (postar, postar.solicitud.inscripcion),
                        #     request, "add")
                        return JsonResponse({"result": 'ok','mensaje':'Documento actualizado'}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": 'bad', "mensaje": "Complete los datos requeridos."}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": u"Error al obtener los datos. {}".format(ex)})

            if action == 'corregirpuntajealumno':
                try:
                    id = request.POST['id']
                    puntaje = request.POST['puntaje']
                    solicitud = SolicitudCambioCarrera.objects.get(id=id)
                    solicitud.puntajealumno = float(puntaje)
                    solicitud.puntajeincorrecto = False
                    solicitud.save(request)
                    # log(u'Cambio el puntaje ingresado en solicitud de cambio de carrera: %s' % solicitud, request,
                    #     "edit")
                    return JsonResponse({"result": 'ok'}, safe=False)
                except Exception as e:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": "Intentelo más tarde."}, safe=False)

            if action == 'notificardocumentoscorregidos':
                solicitud = SolicitudCambioCarrera.objects.get(id=int(request.POST['id']))
                titulo = 'Documentos de cambio de carrera corregidos'
                mensaje = 'corrigio todos los documentos de cambio de carrera'
                if 'estado' in request.POST:
                    solicitud.estadomensaje = False
                    solicitud.save(request)
                    titulo = 'Documentos faltantes fueron compltados'
                    mensaje = 'subio todos los documentos faltantes para revision'
                notificacion(titulo.upper(),
                             '{} {}'.format(
                                 solicitud.persona, mensaje).upper(), solicitud.persona_admision,
                             None,
                             '/alu_cambiocarrera?action=solicitantes&id={}&search={}'.format(
                                 solicitud.periodocambiocarrera.pk, solicitud.persona.cedula), solicitud.pk,
                             1,
                             'sga', SolicitudCambioCarrera, request)
                return JsonResponse({"result": True, 'mensaje': 'Notificacion enviada correctamente!'}, safe=False)

            if action == 'subirdocfaltante':
                try:
                    solicitud = SolicitudCambioCarrera.objects.get(pk=request.POST['idsolicitud'])

                    requisito = RequisitosCambioCarrera.objects.get(pk=request.POST['idrequisito'])
                    if not requisito.multiple:
                        if 'doc_{}'.format(requisito.nombre_input()) in request.FILES:
                            newfile = request.FILES['doc_{}'.format(requisito.nombre_input())]
                            extension = newfile._name.split('.')
                            tam = len(extension)
                            exte = extension[tam - 1]
                            if newfile.size > 2194304:
                                # return JsonResponse({"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 2 Mb."})
                                raise NameError('Error, el tamaño del archivo es mayor a 2 Mb.')
                            if not exte.lower() in ['pdf']:
                                # return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf"})
                                raise NameError('Error, solo archivos .pdf')
                            docrequerido = DocumentosSolicitudCambioCarrera(solicitud=solicitud, documento=requisito)
                            nombre_persona = remover_caracteres_especiales_unicode(solicitud.persona.apellido1).lower().replace(
                                ' ',
                                '_')
                            newfile._name = generar_nombre(
                                "{}__{}".format(nombre_persona, requisito.nombre_input()[:5]),
                                newfile._name)
                            docrequerido.archivo = newfile
                            docrequerido.save(request)
                        else:
                            transaction.set_rollback(True)
                            return JsonResponse({"result": False, "mensaje": "Seleccione un archivo."}, safe=False)
                    else:
                        # Guarda Archivos de seleccion multiple
                        if 'doc_{}[]'.format(requisito.nombre_input()) in request.FILES:
                            docmultiple = 'doc_{}[]'.format(requisito.nombre_input())
                            cont = 0
                            for drmultiple in request.FILES.getlist(docmultiple):
                                print(cont)
                                newfile = drmultiple
                                extension = newfile._name.split('.')
                                tam = len(extension)
                                exte = extension[tam - 1]
                                if newfile.size > 2194304:
                                    transaction.set_rollback(True)
                                    return JsonResponse(
                                        {"result": True,
                                         "mensaje": u"Error, el tamaño del archivo es mayor a 2 Mb."})
                                if not exte.lower() in ['pdf']:
                                    transaction.set_rollback(True)
                                    return JsonResponse(
                                        {"result": True, "mensaje": u"Error, solo archivos .pdf"})
                                docrequerido = DocumentosSolicitudCambioCarrera(solicitud=solicitud,
                                                                                documento=requisito)
                                nombre_persona = remover_caracteres_especiales_unicode(
                                    solicitud.persona.apellido1).lower().replace(' ', '_')
                                newfile._name = generar_nombre(
                                    "{}__{}__{}".format(nombre_persona, requisito.nombre_input(), cont),
                                    newfile._name)
                                docrequerido.archivo = newfile
                                docrequerido.save(request)
                                cont += 1
                        else:
                            transaction.set_rollback(True)
                            return JsonResponse({"result": False, "mensaje": "Seleccione almenos un archivo."},
                                                safe=False)
                    # log(u'Documento Cambio Carrera %s estudiante: %s' % (solicitud, solicitud.inscripcion),
                    #     request, "add")
                    return JsonResponse({"result": True}, safe=False)
                except Exception as ex:
                    pass

            elif action == 'deldocumento':
                try:
                    with transaction.atomic():
                        documento = DocumentosSolicitudCambioCarrera.objects.get(pk=int(encrypt(request.POST['id'])))
                        documento.motivo = request.POST['observacion']
                        documento.status = False
                        documento.save(request)
                        log(u'Elimino documento de estudiante de cambio de carrera: %s - %s - %s', request,
                            "deldocumento")
                        res_json = {"error": False}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
            if action == 'reemplazardocumento':
                try:
                    data['filtro'] = solicitud = DocumentosSolicitudCambioCarrera.objects.get(
                        pk=int(request.GET['id']))
                    form = ReemplazarDocumentoCambioCarreraForm(initial=model_to_dict(solicitud))
                    soli=SolicitudCambioCarrera.objects.get(pk=int(request.GET['solicitud']))
                    data['solicitud']=soli.id
                    data['form2'] = form
                    template = get_template("alu_solicitudcambioies/modal/remplazardocumento.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'buscaruniversidad':
                try:
                    item = []
                    param = request.GET['term']
                    data['universidades'] = universidades = InstitucionEducacionSuperior.objects.filter(status=True, nombre__icontains=param).order_by('nombre').exclude(id=9139)
                    otra=InstitucionEducacionSuperior.objects.get(id=9139)
                    item.append({'id': otra.id, 'text': otra.nombre})
                    for universidad in universidades:
                        text = universidad.nombre
                        item.append({'id': universidad.id, 'text': text})
                    return JsonResponse(item, safe=False)
                except Exception as ex:
                    pass

            if action == 'listsolicitudes':
                try:
                    cedula = request.GET['cedula']
                    if Persona.objects.filter(status=True, cedula=cedula, usuario__isnull=False).exists():
                        persona=Persona.objects.get(cedula=cedula,status=True)
                        for perfil in persona.perfilusuario_set.filter(status=True):
                            if perfil.es_estudiante() and Inscripcion.objects.filter(persona=persona, carrera__coordinacion__id__in=[1, 3, 2, 5, 4, 13], activo=True).exists():
                                return JsonResponse({'result': False,
                                                     "mensaje": u"Usted es un estudiante UNEMI por favor gestione el proceso, por la plataforma SGA UNEMI"})
                    if not SolicitudCambioCarrera.objects.filter(status=True, persona__cedula=cedula).exists():
                        return JsonResponse({'result': False,"mensaje": u"No existen solicitudes registradas con este número de cedula"})

                    data['solicitudes'] = solicitud = SolicitudCambioCarrera.objects.filter(status=True, persona__cedula=cedula)
                    template = get_template("alu_solicitudcambioies/listsolicitudes.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'seguimiento':
                try:
                    data['title'] = u'Proceso de Solicitud Cambio de Carrera'
                    id=request.GET['id']
                    data['solicitud'] = solicitud = SolicitudCambioCarrera.objects.get(pk=id)
                    data['carreradestino'] = CarrerasCambioCarrera.objects.get(status=True,
                        periodocambiocarrera=solicitud.periodocambiocarrera, carrera=solicitud.carreradestino)
                    data['documentos'] = documentos = DocumentosSolicitudCambioCarrera.objects.filter(status=True, solicitud=solicitud).order_by('documento__nombre')
                    data['filtro'] = filtro = solicitud.periodocambiocarrera
                    pasoactual = 1
                    porcentaje = [0,0]
                    data['paso2'] = paso2 = False if not solicitud.revision_admision == 1 else True
                    data['paso3'] = paso3 = False if not solicitud.revision_bienestar == 1 else True
                    data['paso4'] = paso4 = False if not solicitud.aprobacion_admision == 1  else True
                    data['paso5'] = paso5 = False if not solicitud.revision_decano == 1 else True
                    data['paso6'] = paso6 = False if not solicitud.revision_director == 1 else True
                    if paso2:
                        pasoactual = 2
                        porcentaje = [1,20]
                    if paso3:
                        pasoactual = 3
                        porcentaje = [2,40]
                    if paso4:
                        pasoactual = 4
                        porcentaje = [3,60]
                    if paso5:
                        pasoactual = 5
                        porcentaje = [4,80]
                    if paso6:
                        pasoactual = 6
                        porcentaje = [5,100]

                    data['pasoactual'] = pasoactual
                    data['porcentaje'] = porcentaje
                    data['ultimopaso'] = 5
                    data['hoy']=hoy
                    template = get_template("alu_solicitudcambioies/seguimiento.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'cargarfile':
                try:
                    data['action']=action
                    data['requisito'] = requisito = RequisitosCambioCarrera.objects.get(pk=int(request.GET['id']))
                    template = get_template("alu_solicitudcambioies/modal/cargarfile.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'subirdocfaltante':
                try:
                    data['filtro'] = solicitud = SolicitudCambioCarrera.objects.get(pk=int(request.GET['id']))
                    data['requisito'] = RequisitosCambioCarrera.objects.get(pk=int(request.GET['idrequisito']))
                    template = get_template("alu_solicitudcambioies/modal/docfaltantes.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Cambio Carrera'
                data['institucion'] = u'UNIVERSIDAD ESTATAL DE MILAGRO'
                data['action'] = u'addregistro'
                puedeinscribirse = False
                mensaje="NO SE ENCUENTRAN PERIODOS DE CAMBIO DE CARRERA APERTURADOS"
                if AperturaPeriodoCambioCarrera.objects.filter(status=True, publico=True).exists():
                    apertura = AperturaPeriodoCambioCarrera.objects.filter(status=True, publico=True).order_by('fechaapertura').last()
                    if apertura.fechaapertura <= hoy and apertura.fechacierre >=hoy:
                        if hoy <= apertura.fechacierrerecepciondocumentos:
                            data['apertura'] = apertura
                            data['nivelesdemallas'] = NivelMalla.objects.all().order_by('id')
                            puedeinscribirse = True
                        else:
                            mensaje="La fecha de recepción de solicitudes culminó por lo tanto usted no podra realizar una solicitud en este período."
                if not puedeinscribirse:
                    data['mensaje']=mensaje
                data['puedeinscribirse'] = puedeinscribirse
                return render(request, "alu_solicitudcambioies/solicitudies.html", data)
            except Exception as ex:
                pass