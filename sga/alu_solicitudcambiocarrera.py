# -*- coding: latin-1 -*-
import random
import sys
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Count
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.template.loader import get_template

from decorators import last_access
from sga.commonviews import adduserdata
from sga.forms import ReemplazarDocumentoCambioCarreraForm
from sga.funciones import generar_nombre, log, notificacion, remover_caracteres_especiales_unicode
from sga.models import SolicitudCambioCarrera, AperturaPeriodoCambioCarrera, \
    DocumentosSolicitudCambioCarrera, CarrerasCambioCarrera, ConvalidaCambioCarrera, SolicitudConvalidaCambioCarrera, \
    AsignaturaMalla, NivelMalla, EjeFormativo, RespuestasSolicitudConvalidaCambioCarrera, HomologacionAsignatura, Malla, \
    ReponsableCambioCarrera, RequisitosCambioCarrera, HistorialDocumentosSolicitudCC
from sga.templatetags.sga_extras import encrypt


# @csrf_exempt
@login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    hoy=datetime.now().date()
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    data['periodo']=periodo = request.session['periodo']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    data['inscripcionpersona'] = inscripcion = perfilprincipal.inscripcion
    if not inscripcion.puede_solicitar_cambio_carrera():
        return HttpResponseRedirect("/?info=Solo los estudiantes que hayan aprobado mas del 50% de las materias de primer nivel pueden ingresar al modulo.")
    data['inscripcionmalla'] = inscripcionmalla = inscripcion.malla_inscripcion()
    if not inscripcionmalla:
        return HttpResponseRedirect("/?info=Este estudiante no tiene ninguna malla asociada")
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                with transaction.atomic():
                    id = request.POST['id']
                    periodocambiocarrera = AperturaPeriodoCambioCarrera.objects.get(pk=id)
                    if not 'carreras' in request.POST:
                        return JsonResponse({"result": True, "mensaje": "Debe seleccionar una carrera para continuar."}, safe=False)

                    carreradestino_id = int(request.POST['carreras'])
                    puntaje = float(request.POST['puntajeobtenido'])

                    if hoy > periodocambiocarrera.fechacierrerecepciondocumentos:
                        return JsonResponse({"result": True, "mensaje": "La fecha de recepción de solicitudes culminó, usted ya no puede realizar una solicitud."}, safe=False)
                    if not puntaje:
                        puntaje=inscripcion.puntajesenescyt
                    if SolicitudCambioCarrera.objects.filter(periodocambiocarrera=periodocambiocarrera, status=True,
                                                             inscripcion=inscripcion, estados__in=[0, 1]).values('id').exists():
                        return JsonResponse({"result": True, "mensaje": "Ya existe una solicitud de cambio de carrera en este periodo abierto."}, safe=False)
                    if puntaje <= 0.00:
                        return JsonResponse({"result": True, "mensaje": "Debe ingresar su puntaje para continuar."}, safe=False)
                    totalsubidos = 0
                    totalsubidosmultiple = 0
                    documentos_requeridos_multiple = periodocambiocarrera.requisitos.filter(status=True, multiple=True, externo=False, documentorequerido=True)
                    documentos_requeridos = periodocambiocarrera.requisitos.filter(status=True,externo=False, multiple=False, documentorequerido=True)
                    if not documentos_requeridos:
                        return JsonResponse({"result": True, "mensaje": "Debe subir todos los requisitos para continuar."}, safe=False)

                    # if not documentos_requeridos_multiple:
                    #     transaction.set_rollback(True)
                    #     return JsonResponse(
                    #         {"result": True, "mensaje": "Debe subir todos los requisitos para continuar."},
                    #         safe=False)

                    carreradestino = CarrerasCambioCarrera.objects.get(id=carreradestino_id)
                    if carreradestino.cupo_disponible() <= 0:
                        raise NameError("Los cupos disponibles para esta carrera están agotados.")

                    if puntaje < carreradestino.puntajerequerido:
                        return JsonResponse({"result": True, "mensaje": "El puntaje ingresado no es el correcto para la carrera seleccionada."}, safe=False)

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
                        return JsonResponse({"result": True, "mensaje": "Debe subir todos los requisitos."}, safe=False)

                    #Permite asignar casos equitativamente a 4 administrativos con id de persona quemados
                    verificador = SolicitudCambioCarrera.objects.filter(status=True, periodocambiocarrera=periodocambiocarrera).values('id')
                    cb = 0
                    cr = 0
                    cont = 0
                    persona_admision_id = 0
                    responsables = ReponsableCambioCarrera.objects.filter(status=True, rol=0, estado=True).values_list('persona_id', flat=True)
                    resinactivos = ReponsableCambioCarrera.objects.filter(status=True, rol=0, estado=False).values_list('persona_id', flat=True)
                    lista = []
                    for p in responsables:
                        cont += 1
                        if not verificador.filter(persona_admision=p).exists():
                            persona_admision_id = p
                            break
                    if persona_admision_id == 0 and verificador.exists():
                        persona_admision_id = SolicitudCambioCarrera.objects.filter(status=True, periodocambiocarrera=periodocambiocarrera).exclude(persona_admision_id__in=resinactivos).values('persona_admision_id').annotate(total=Count('id')).order_by('total')[0]['persona_admision_id']

                        # elif len(verificador) >= len(responsables):
                        #     ct = len(verificador.filter(persona_admision=p))
                        #     if ct > cr:
                        #         th = ct
                        #     elif ct < cr or cb == 0:
                        #         cb = ct
                        #         per = p
                        #     elif cr == ct:
                        #         if len(lista) != 0:
                        #             lista = lista+[p]
                        #         else:
                        #             lista = lista+[p2, p]
                        #     cr = ct
                        #     # if len(lista) == 4:
                        #     if len(lista) == len(responsables)-1:
                        #         rango=len(responsables)-1
                        #         numaleatorio=random.randint(0, rango)
                        #         persona_admision_id = responsables[numaleatorio]
                        #         break
                        #     elif cb < th and cont == len(responsables):
                        #         persona_admision_id = per
                        #         break
                        #     p2 = p
                    solicitud = SolicitudCambioCarrera(periodocambiocarrera=periodocambiocarrera,
                                                       inscripcion=inscripcion,
                                                       carreradestino=carreradestino.carrera, puntajealumno=puntaje,
                                                       puntajeacogido=carreradestino.puntajerequerido,
                                                       persona_admision_id=persona_admision_id,)
                    solicitud.save(request)
                    # carreradestino.cupo -= 1
                    carreradestino.save()

                    for dr in documentos_requeridos:
                        if 'doc_{}'.format(dr.nombre_input()) in request.FILES:
                            newfile = request.FILES['doc_{}'.format(dr.nombre_input())]
                            extension = newfile._name.split('.')
                            tam = len(extension)
                            exte = extension[tam - 1]
                            if newfile.size > 2194304:
                                # return JsonResponse({"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 2 Mb."})
                                raise NameError('Error, el tamaño del archivo es mayor a 2 Mb.')
                            if not exte.lower() in ['pdf']:
                                # return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf"})
                                raise NameError('Error, solo archivos .pdf')
                            docrequerido = DocumentosSolicitudCambioCarrera(solicitud=solicitud, documento=dr)
                            nombre_persona = remover_caracteres_especiales_unicode(persona.apellido1).lower().replace(' ', '_')
                            newfile._name = generar_nombre("{}__{}".format(nombre_persona, dr.nombre_input()[:5]), newfile._name)
                            docrequerido.archivo = newfile
                            docrequerido.save(request)

                    # Guarda Archivos de seleccion multiple
                    for dm in documentos_requeridos_multiple:
                        if 'doc_{}[]'.format(dm.nombre_input()) in request.FILES:
                            docmultiple = request.FILES.getlist('doc_{}[]'.format(dm.nombre_input()))
                            descripciones = request.POST.getlist('desc_{}[]'.format(dm.nombre_input()))
                            niveles = request.POST.getlist('nivel_{}[]'.format(dm.nombre_input()))
                            mensaje='Por favor complete todos los campos.'
                            if dm.essilabo and len(docmultiple) != len(niveles) or len(docmultiple) != len(descripciones):
                                raise NameError(mensaje)
                            elif not dm.essilabo and len(docmultiple) != len(descripciones):
                                raise NameError(mensaje)
                            cont = 0
                            for drmultiple in docmultiple:
                                print(docmultiple)
                                print(niveles)
                                print(descripciones)
                                nivel = None
                                if not dm.essilabo :
                                    if descripciones[cont] == '':
                                        raise NameError(mensaje)
                                    cuerpo = dm.nombre_input()
                                elif dm.essilabo:
                                    if descripciones[cont] == '' or niveles[cont] == '':
                                        raise NameError(mensaje)
                                    nivel=niveles[cont]
                                    cuerpo = 'silabo_'+remover_caracteres_especiales_unicode(descripciones[cont]).lower().replace(' ', '_')
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
                                    print(exte)
                                    transaction.set_rollback(True)
                                    return JsonResponse(
                                        {"result": True, "mensaje": u"Error, solo archivos .pdf"})
                                docrequerido = DocumentosSolicitudCambioCarrera(solicitud=solicitud,
                                                                                nivel_id=nivel,
                                                                                descripcion=descripciones[cont],
                                                                                documento=dm)
                                nombre_persona = remover_caracteres_especiales_unicode(solicitud.inscripcion.persona.apellido1).lower().replace(' ', '_')
                                newfile._name = generar_nombre(
                                    "{}__{}__{}".format(nombre_persona, cuerpo, cont),
                                    newfile._name)
                                docrequerido.archivo = newfile
                                docrequerido.save(request)
                                cont += 1


                    notificacion(('Nueva solicitud de cambio de carrera').upper(), 'Se le asigno una solicitud de cambio de carrera', solicitud.persona_admision,
                                 None, '/alu_cambiocarrera?action=solicitantes&id={}&search={}'.format(solicitud.periodocambiocarrera.pk, solicitud.inscripcion.persona.cedula), solicitud.pk,
                                 1, 'sga', SolicitudCambioCarrera, request)

                    log(u'Adiciono Solicitud de Cambio de Carrera: %s' % solicitud, request, "add")
                    return JsonResponse({"result": False, 'mensaje': 'Solicitud registrada con éxito, sus datos serán validados ', 'modalsuccess': True,
                                         'to': '{}?action=verproceso&id={}'.format(request.path, encrypt(solicitud.pk))}, safe=False)

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": str(ex)}, safe=False)

        if action == 'reemplazardocumento':
            try:
                postar = DocumentosSolicitudCambioCarrera.objects.get(id=int(request.POST['id']))
                f = ReemplazarDocumentoCambioCarreraForm(request.POST)
                if f.is_valid():
                    postar.doccorregido = True
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

                    historial=postar.historialdocumentossolicitudcc_set.filter(documento=postar, status=True)
                    if historial.exists():
                        historial=historial.last()
                        historial.estados=5
                        historial.fecha_correccion=datetime.now()
                        historial.save(request)
                    log(u'Documento Cambio Carrera %s estudiante: %s' % (postar, postar.solicitud.inscripcion),
                        request, "add")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al obtener los datos. {}".format(ex)})

        if action == 'notificardocumentoscorregidos':
            solicitud = SolicitudCambioCarrera.objects.get(id=int(request.POST['id']))
            titulo='Documentos de cambio de carrera corregidos'
            mensaje='corrigio todos los documentos de cambio de carrera'
            if 'estado' in request.POST:
                solicitud.estadomensaje=False
                solicitud.save(request)
                titulo = 'Documentos faltantes fueron compltados'
                mensaje = 'subio todos los documentos faltantes para revision'
            notificacion(titulo.upper(),
                         '{} {}'.format(
                             solicitud.inscripcion.persona, mensaje).upper(), solicitud.persona_admision,
                         None,
                         '/alu_cambiocarrera?action=solicitantes&id={}&search={}'.format(
                             solicitud.periodocambiocarrera.pk, solicitud.inscripcion.persona.cedula), solicitud.pk,
                         1,
                         'sga', SolicitudCambioCarrera, request)
            return JsonResponse({"result": True, 'mensaje': 'Notificacion enviada correctamente!'}, safe=False)

        if action == 'buscarcarrera':
            try:
                item = []
                param = request.POST['term']
                puntaje = float(request.POST['puntaje'])
                if not puntaje:
                    puntaje = inscripcion.puntajesenescyt
                data['periodocabiocarrera'] = apertura = AperturaPeriodoCambioCarrera.objects.filter(pk=int(request.POST['periodo'])).first()
                if 0 < puntaje <= 1000:
                    carreras=apertura.carrerascambiocarrera_set.filter(status=True,carrera__nombre__icontains=param, puntajerequerido__lte=puntaje).exclude(
                        Q(carrera=perfilprincipal.inscripcion.carrera)).exclude(
                        Q(puntajerequerido__lte=0)).order_by('carrera__nombre')
                    if SolicitudCambioCarrera.objects.filter(inscripcion=inscripcion,periodocambiocarrera=apertura, status=True, estados__in=[5,6,8]).exists():
                        solicitud = SolicitudCambioCarrera.objects.get(inscripcion=inscripcion, status=True, estados__in=[5, 6, 8])
                        carreras = carreras.exclude(Q(carrera=solicitud.carreradestino))
                    data['carreras'] = carreras
                    for c in carreras:
                        if c.cupo_disponible() > 0:
                            text = c.carrera.nombre_completo_inscripcion() + " - CUPO DISPONIBLE: " + str(c.cupo_disponible()) + " - PUNTAJE REQUERIDO: " + str(c.puntajerequerido)
                            item.append({'id': c.id, 'text': text})

                return JsonResponse(item, safe=False)
            except Exception as e:
                pass

        if action == 'corregirpuntajealumno':
            try:
                id = request.POST['id']
                puntaje = request.POST['puntaje']
                solicitud = SolicitudCambioCarrera.objects.get(id=id)
                solicitud.puntajealumno = float(puntaje)
                solicitud.puntajeincorrecto = False
                solicitud.save(request)
                log(u'Cambio el puntaje ingresado en solicitud de cambio de carrera: %s' % solicitud, request, "edit")
                return JsonResponse({"result": 'ok'}, safe=False)
            except Exception as e:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'delsolicitud':
            try:
                with transaction.atomic():
                    solicitud=SolicitudCambioCarrera.objects.get(id=int(request.POST['id']))
                    solicitud.status=False
                    solicitud.save(request)
                    log(u'Eliminación de solicitud de cambio de carrera: %s' % solicitud, request, "delsolicitud", )
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'addsolicitudsimulador':
            try:
                    id = request.POST['id']
                    respuestas=eval(request.POST['requisito[]'])
                    convalida = ConvalidaCambioCarrera.objects.get(pk=id)
                    puntaje = float(request.POST['puntajeobtenido'])

                    if SolicitudConvalidaCambioCarrera.objects.filter(convalida=convalida, status=True,
                                                             inscripcion=inscripcion).exists():
                        return JsonResponse({"result": True,
                                             "mensaje": "Ya se a enviado un formulario para esta carrera"},
                                            safe=False)
                    if puntaje <= 0.00:
                        return JsonResponse({"result": True, "mensaje": "Debe ingresar su puntaje para continuar."},
                                            safe=False)
                    if puntaje < convalida.carrera.id:
                        return JsonResponse({"result": True,
                                             "mensaje": "El puntaje ingresado no es el correcto para la carrera seleccionada."},
                                            safe=False)
                    requisitos=convalida.todos_requisitos()
                    solicitud = SolicitudConvalidaCambioCarrera(convalida=convalida,
                                                       inscripcion=inscripcion,
                                                       carreradestino=convalida.carrera)
                    solicitud.save(request)
                    for requisito in requisitos:
                        respuestasolicitud = RespuestasSolicitudConvalidaCambioCarrera(solicitud=solicitud, requisitos=requisito, estado=False)
                        for respuesta in respuestas:
                            if requisito.id == int(respuesta):
                                respuestasolicitud  = RespuestasSolicitudConvalidaCambioCarrera(solicitud=solicitud, requisitos=requisito, estado=True)
                        respuestasolicitud .save(request)
                    log(u'Adiciono Solicitud de Convalidacion de Simulacro %s' % solicitud, request, "add")
                    return JsonResponse(
                        {"result": 'ok', 'mensaje': 'Solicitud registrada con éxito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'buscarcarrerasimulador':
            try:
                item = []
                param = request.POST['term']
                # puntaje = float(request.POST['puntaje'])
                convalida= ConvalidaCambioCarrera.objects.filter(carrera=inscripcion.carrera,status=True, publico=True)
                # if 0 < puntaje <= 1000:
                if request.POST['modalidad']=='3':
                    data['carreras'] =carreras= convalida.filter(malla__nombre__icontains=param, carrera__modalidad=3).exclude(
                        Q(carrera=perfilprincipal.inscripcion.carrera)).order_by('carrera__nombre')
                else:
                    data['carreras'] = carreras=convalida.filter(carrera__nombre__icontains=param).exclude(
                        Q(carrera=perfilprincipal.inscripcion.carrera)).order_by('carrera__nombre')
                for c in carreras:
                    text = c.carrera.nombre + " - PUNTAJE REQUERIDO: " + str(c.puntajerequerido)
                    item.append({'id': c.id, 'text': text})
                return JsonResponse(item, safe=False)
            except Exception as ex:
                pass

        if action == 'subirdocfaltante':
            try:
                solicitud=SolicitudCambioCarrera.objects.get(pk=request.POST['idsolicitud'])

                requisito=RequisitosCambioCarrera.objects.get(pk=request.POST['idrequisito'])
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
                        nombre_persona = remover_caracteres_especiales_unicode(persona.apellido1).lower().replace(' ',
                                                                                                                  '_')
                        newfile._name = generar_nombre("{}__{}".format(nombre_persona, requisito.nombre_input()[:5]),
                                                       newfile._name)
                        docrequerido.archivo = newfile
                        docrequerido.save(request)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Seleccione un archivo."}, safe=False)
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
                                print(exte)
                                transaction.set_rollback(True)
                                return JsonResponse(
                                    {"result": True, "mensaje": u"Error, solo archivos .pdf"})
                            docrequerido = DocumentosSolicitudCambioCarrera(solicitud=solicitud,
                                                                            documento=requisito)
                            nombre_persona = remover_caracteres_especiales_unicode(
                                solicitud.inscripcion.persona.apellido1).lower().replace(' ', '_')
                            newfile._name = generar_nombre(
                                "{}__{}__{}".format(nombre_persona, requisito.nombre_input(), cont),
                                newfile._name)
                            docrequerido.archivo = newfile
                            docrequerido.save(request)
                            cont += 1
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Seleccione almenos un archivo."}, safe=False)
                log(u'Documento Cambio Carrera %s estudiante: %s' % (solicitud, solicitud.inscripcion),
                    request, "add")
                return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                pass

        elif action == 'deldocumento':
            try:
                with transaction.atomic():
                    documento = DocumentosSolicitudCambioCarrera.objects.get(pk=int(encrypt(request.POST['id'])))
                    documento.motivo=request.POST['observacion']
                    documento.status = False
                    documento.save(request)
                    log(u'Elimino documento de estudiante de cambio de carrera: %s - %s - %s', request, "deldocumento")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
            if action == 'add':
                try:
                    if AperturaPeriodoCambioCarrera.objects.filter(status=True, publico=True).exists():
                        if not inscripcion.solicitudcambiocarrera_set.filter(status=True, inscripcion=inscripcion, estados__in=[0,7,4], periodocambiocarrera__publico=True, periodocambiocarrera__status=True ).exists():
                            data['title'] = u'Registro de Solicitud para cambio de carrera'
                            data['apertura'] = apertura = AperturaPeriodoCambioCarrera.objects.filter(status=True, publico=True).first()
                            data['homologaciones']= HomologacionAsignatura.objects.filter(status=True, origen__malla_id=inscripcionmalla.malla.id)
                            data['nivelesdemallas'] = NivelMalla.objects.all().order_by('id')
                            if hoy > apertura.fechacierrerecepciondocumentos:
                                messages.warning(request,'La fecha de recepción de solicitudes culminó por lo tanto usted no podra realizar una solicitud en este período')
                                return redirect('/alu_solicitudcambiocarrera')
                            # asignaturasmalla = AsignaturaMalla.objects.filter(malla=inscripcionmalla.malla, status=True, vigente=True).exclude(tipomateria_id=3)
                            # data['tercera']=False
                            # for asignaturamalla in asignaturasmalla:
                            #     matricula=inscripcion.historicorecordacademico_set.values("id").filter(asignatura=asignaturamalla.asignatura,noaplica=False).count()
                            #     print(matricula)
                            #     if matricula == 3:
                            #         data['tercera'] = True
                            #         messages.warning(request,'Usted no puede realizar el cambio de carrera por que tiene una o varias asignaturas en tercera matricula')
                            #         return redirect('/alu_solicitudcambiocarrera')
                            return render(request, "alu_solicitudcambiocarrera/formsolicitud.html", data)
                        else:
                            messages.warning(request,'Usted ya tiene una solicitud de cambio de carrera pendiente en este periodo')
                            return redirect('/alu_solicitudcambiocarrera')
                    else:
                        messages.warning(request, 'No existen periodos de cambio de carrera disponibles')
                        return redirect('/alu_solicitudcambiocarrera')
                except Exception as ex:
                    pass

            if action == 'verproceso':
                try:
                    data['hoy']=hoy
                    data['title'] = u'Proceso de Solicitud Cambio de Carrera'
                    data['solicitud'] = solicitud = SolicitudCambioCarrera.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    data['carreradestino'] = CarrerasCambioCarrera.objects.get(status=True,
                        periodocambiocarrera=solicitud.periodocambiocarrera, carrera=solicitud.carreradestino)
                    data['documentos'] = documentos = DocumentosSolicitudCambioCarrera.objects.filter(status=True,
                        solicitud=solicitud).order_by('documento__nombre')
                    data['filtro'] = filtro = solicitud.periodocambiocarrera
                    pasoactual = 1
                    porcentaje = [0,0]
                    data['paso2'] = paso2 = False if not solicitud.revision_admision == 1 else True
                    data['paso3'] = paso3 = False if not solicitud.revision_bienestar == 1 else True
                    data['paso4'] = paso4 = False if not solicitud.aprobacion_admision == 1 else True
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
                    data['porcentaje']=porcentaje
                    data['pasoactual'] = pasoactual
                    data['ultimopaso'] = 5
                    return render(request, "alu_solicitudcambiocarrera/wizard_solicitud.html", data)
                except Exception as ex:
                    pass

            elif action == 'reemplazardocumento':
                try:
                    data['filtro'] = solicitud = DocumentosSolicitudCambioCarrera.objects.get(
                        pk=int(request.GET['id']))
                    form = ReemplazarDocumentoCambioCarreraForm(initial=model_to_dict(solicitud))
                    data['form2'] = form
                    template = get_template("alu_practicaspro/modal/reemplazardocumento.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'tablahomologacion':
                try:
                    cambiocarrera=CarrerasCambioCarrera.objects.get(id=request.GET['id'])
                    malladestino=cambiocarrera.carrera.malla()
                    existe=True
                    homologaciones=HomologacionAsignatura.objects.filter(status=True, origen__malla=inscripcionmalla.malla, malladestino=malladestino)
                    if homologaciones:
                        data['asignaturashomologadas']=homologaciones
                        data['puntajeobtenido'] = request.GET['puntajeobtenido']
                        data['nivelesdemallas'] = NivelMalla.objects.all().order_by('orden')
                        data['malladestino']=malladestino

                        #Malla Destino
                        ejesenuso = AsignaturaMalla.objects.values_list('ejeformativo_id', flat=True).filter(malla=malladestino).distinct()
                        data['asignaturasmallasdestino'] = AsignaturaMalla.objects.filter(malla=malladestino)
                        data['ejesformativosdestino'] = EjeFormativo.objects.filter(id__in=ejesenuso).order_by('nombre')

                        # Malla Alumno
                        asignaturamalla = AsignaturaMalla.objects.filter(malla=inscripcionmalla.malla, status=True, vigente=True).exclude(tipomateria_id=3)
                        xyz = [1, 2, 3]
                        if inscripcion.itinerario and inscripcion.itinerario > 0:
                            xyz.remove(inscripcion.itinerario)
                            asignaturamalla = asignaturamalla.exclude(itinerario__in=xyz)
                        data['ejesformativos'] = EjeFormativo.objects.filter(status=True, id__in=AsignaturaMalla.objects.values_list('ejeformativo_id', flat=True).filter(malla=inscripcionmalla.malla, status=True, vigente=True).distinct()).order_by('nombre')
                        data['asignaturasmallasestudiante'] = [(x, inscripcion.aprobadaasignatura(x)) for x in asignaturamalla]
                        data['resumenes'] = [{'id': x.id, 'horas': x.total_horas(inscripcionmalla.malla), 'creditos': x.total_creditos(inscripcionmalla.malla)} for x in NivelMalla.objects.all().order_by('nombre')]
                    else:
                        existe=False
                    template = get_template("alu_solicitudcambiocarrera/tablacomparacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data), "existe":existe})
                except Exception as ex:
                    mensaje = 'Intentelo mas tarde'
                    return JsonResponse({"result": False, "mensaje": mensaje})

            if action == 'verasignaturashomologadas':
                try:
                    idm = request.GET['idmalladestino']
                    ida = request.GET['idasignaturaorigen']
                    if HomologacionAsignatura.objects.filter(origen_id=ida, malladestino_id=idm, status=True).exists():
                        homologacion = HomologacionAsignatura.objects.get(origen_id=ida, malladestino_id=idm)
                        data['homologaciones'] = homologacion.todas_asignaturasdestino()
                        data['malladestino'] = Malla.objects.get(id=idm)
                    template = get_template("alu_solicitudcambiocarrera/modal/verasignaturashomologadas.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    mensaje = 'Intentelo mas tarde'
                    return JsonResponse({"result": False, "mensaje": mensaje})

            if action == 'tablamalladestino':
                try:
                    idm = request.GET['idmalladestino']
                    data['nivelesdemallas'] = NivelMalla.objects.all().order_by('orden')
                    data['malladestino'] = Malla.objects.get(id=idm)
                    # Malla Destino
                    ejesenuso = AsignaturaMalla.objects.values_list('ejeformativo_id', flat=True).filter(malla=idm).distinct()
                    data['asignaturasmallasdestino'] = AsignaturaMalla.objects.filter(malla=idm)
                    data['ejesformativosdestino'] = EjeFormativo.objects.filter(id__in=ejesenuso).order_by('nombre')

                    template = get_template("alu_solicitudcambiocarrera/modal/tablamalladestino.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    mensaje = 'Intentelo mas tarde'
                    return JsonResponse({"result": False, "mensaje": mensaje})

            if action == 'subirdocfaltante':
                try:
                    data['filtro'] = solicitud = SolicitudCambioCarrera.objects.get(pk=int(request.GET['id']))
                    data['requisito'] = RequisitosCambioCarrera.objects.get(pk=int(request.GET['idrequisito']))
                    template = get_template("alu_solicitudcambiocarrera/modal/docfaltantes.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass
        else:
            data['title'] = u'Solicitudes de Cambio de Carrera'
            data['listado'] = listado = SolicitudCambioCarrera.objects.filter(status=True,
                                                                              inscripcion=inscripcion).order_by(
                '-pk')
            data['periodocambiocarrera'] = periodocambiocarrera = AperturaPeriodoCambioCarrera.objects.filter(
                status=True, publico=True).exists()
            return render(request, "alu_solicitudcambiocarrera/view.html", data)
