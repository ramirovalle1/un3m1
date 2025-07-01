# -*- coding: UTF-8 -*-
import json
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from django.template.loader import get_template
from django.template import Context
from django.views.decorators.csrf import csrf_exempt

from balcon.models import Informacion, Proceso, Solicitud, Agente, Servicio, HistorialSolicitud, ProcesoServicio, \
    RequisitosConfiguracion, RequisitosSolicitud, Categoria, RespuestaEncuestaSatisfaccion
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from .forms import SolicitudBalconForm, SolicitudBalconEditForm
from sga.funciones import log, generar_nombre, notificacion, remover_caracteres_especiales_unicode
from sga.templatetags.sga_extras import encrypt
from django.db import connections

import random

@csrf_exempt
@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'delsolicitud':
            try:
                solicitud = Solicitud.objects.get(pk=request.POST['id'])
                log(u'Eliminó solicitud problemas: %s' % (solicitud), request, "del")
                solicitud.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos. Detalle: %s" % (msg)})

        elif action == 'addsolicitudmodal':
            try:
                with transaction.atomic():
                    newfile = None
                    tipo = int(request.POST['tipo'])
                    form = SolicitudBalconForm(request.POST, request.FILES)
                    if form.is_valid():
                        servicio = ProcesoServicio.objects.get(pk=int(request.POST['servicio']))
                        servicio_id = int(request.POST['servicio']) if 'servicio' in request.POST and request.POST[ 'servicio'] else 0
                        if HistorialSolicitud.objects.filter((Q(solicitud__estado=1) | Q(solicitud__estado=3)),solicitud__solicitante_id=persona,solicitud__status=True,servicio_id=servicio_id).exists():
                            return JsonResponse({"result": True, "mensaje": u"TIENE SOLICITUDES PENDIENTES EN EL PROCESO %s  " % (servicio.servicio)})

                        subesolicitud = servicio.proceso.subesolicitud
                        ultimasoli = Solicitud.objects.filter(solicitante=persona).order_by('numero').last()
                        numsoli = ultimasoli.numero + 1 if ultimasoli else 1
                        tipo = int(request.POST['tipo'])
                        soli = Solicitud(descripcion=form.cleaned_data['descripcion'].upper(),
                                         tipo=tipo,
                                         solicitante=persona,
                                         perfil=perfilprincipal,
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
                        requisitos = servicio.requisitosconfiguracion_set.filter(status=True)
                        for req in requisitos:
                            if not'doc_{}'.format(req.requisito.pk) in request.FILES:
                                if req.obligatorio:
                                    nombredocumento = remover_caracteres_especiales_unicode(req.requisito.descripcion)
                                    transaction.set_rollback(True)
                                    return JsonResponse({"result": True, "mensaje": "FALTA SUBIR {}".format(nombredocumento)},safe=False)
                            else:
                                nombrepersona_str = remover_caracteres_especiales_unicode(persona.__str__()).lower().replace(' ', '_')
                                nombre = req.requisito.nombre_input()
                                nombredoc = "doc_{}".format(req.requisito.pk)
                                newfile = request.FILES[nombredoc]
                                nombrefoto = '{}_{}'.format(nombrepersona_str, nombre)
                                newfile._name = generar_nombre(nombrefoto.strip(), newfile._name)
                                det = RequisitosSolicitud(solicitud=soli, requisito=req, archivo=newfile)
                                det.save(request)
                        log(u'Adiciono Solicitud para el balcon: %s' % soli, request, "add")
                        #proceso_id = int(request.POST['proceso']) if 'proceso' in request.POST and request.POST['proceso'] else 0
                        servicio_id = int(request.POST['servicio']) if 'servicio' in request.POST and request.POST['servicio'] else 0
                        if Servicio.objects.filter(pk=servicio_id).exists():
                            historial = HistorialSolicitud(servicio_id=servicio_id,
                                                           solicitud=soli,
                                                           asignadorecibe=agentelibre.persona if agentelibre else None)
                            historial.save(request)
                            log(u'Se asigna servicio: %s' % historial.servicio, request, "add")
                            cuerpo = ('Ha recibido una solicitud de %s'% soli)
                            notificacion("Solicitud de %s en balcón de servicios" % soli.solicitante,
                                         cuerpo,soli.agente.persona,None,'adm_solicitudbalcon',soli.id,
                                         1,'sga', Solicitud,request)

                        return JsonResponse({"result": False, 'to': "{}?solicitudsuccess=1".format(request.path)}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'editsolicitudmodal':
            try:
                with transaction.atomic():
                    filtro = Solicitud.objects.get(pk=request.POST['id'])
                    f = SolicitudBalconEditForm(request.POST)
                    if f.is_valid():
                        filtro.descripcion = f.cleaned_data['descripcion']
                        filtro.save(request)
                        log(u'Modificó Solicitud Balcon: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'saveSolicitudCalificarServicio':
            try:
                id = int(encrypt(request.POST['id'])) if 'id' in request.POST and request.POST['id'] and int(encrypt(request.POST['id'])) != 0 else None
                typeForm = request.POST.get('typeForm')
                if typeForm == 'qualify':
                    eSolicitudBalcon = Solicitud.objects.get(id=id)
                    preguntasresueltas = json.loads(request.POST.get('preguntas'))
                    for pregunta in preguntasresueltas:
                        ePreguntaResuelta = RespuestaEncuestaSatisfaccion(
                            pregunta_id=int(encrypt(pregunta['pregunta_id'])),
                            solicitud=eSolicitudBalcon,
                            valoracion=int(pregunta['valoracion']),
                            observacion=pregunta['observacion'],
                        )
                        ePreguntaResuelta.save(request)
                        log(u'Calificó Pregunta de Solicitud Balcon: %s %s' % (eSolicitudBalcon, ePreguntaResuelta), request, "edit")
                    log(u'Calificó Solicitud Balcon: %s' % eSolicitudBalcon, request, "edit")
                return JsonResponse({"result": "ok", "mensaje": "Se guardo correctamente la encuesta de satisfacción"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "%s" % ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'addsolicitudmodal':
                try:
                    data['tipo'] = id = request.GET['id']
                    #data['proceso'] = request.GET['proceso']
                    data['servicio'] = servicio = request.GET['servicio']
                    data['proceso'] = servicio = ProcesoServicio.objects.get(pk=servicio)
                    data['requisitos'] = requisitos = RequisitosConfiguracion.objects.filter(status=True, servicio=servicio)
                    data['subesolicitud'] = servicio.proceso.subesolicitud
                    # proceso = Proceso.objects.get(pk= int(request.GET['proceso']))
                    #if proceso.subesolicitud()
                    data['form2'] = SolicitudBalconForm()
                    template = get_template("adm_balconservicios/modal/formsolicitudalu.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editsolicitudmodal':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = Solicitud.objects.get(pk=request.GET['id'])
                    data['form2'] = SolicitudBalconEditForm(initial=model_to_dict(filtro))
                    template = get_template("adm_balconservicios/modal/formsolicitudalu.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'delsolicitud':
                try:
                    data['title'] = u'Eliminar Solicitud'
                    data['solicitud'] = solicitud = Solicitud.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "alu_solicitudbalcon/deletesolicitud.html", data)
                except Exception as ex:
                    pass

            if action == 'informacion':
                try:
                    data['title'] = u'Información'
                    data['informaciones'] = Informacion.objects.filter(status=True,mostrar=True,tipo=2)
                    data['procesos'] = Proceso.objects.filter(status=True,activo=True)
                    return render(request, "alu_solicitudbalcon/informacionview.html", data)
                except Exception as ex:
                    pass

            if action == 'selcab':
                template = get_template('alu_solicitudbalcon/modalcabtipo.html')
                json_content = template.render(data)
                return JsonResponse({"result": True, 'data': json_content, 'titulo': 'Seleccione tipo de queja'})

            if action == 'selsub':
                nombretipo = 'Tipo'
                template = get_template('alu_solicitudbalcon/modalsubtipo.html')
                json_content = template.render(data)
                return JsonResponse({"result": True, 'data': json_content, 'titulo': 'Seleccione sub tipo de {}'.format(nombretipo)})

            if action == 'seldet':
                nombretipo = 'SubTipo'
                template = get_template('alu_solicitudbalcon/modaldetsubtipo.html')
                json_content = template.render(data)
                return JsonResponse({"result": True, 'data': json_content, 'titulo': '{}'.format(nombretipo)})


            # if action == 'servicios':
            #     try:
            #         data['title'] = u'Información'
            #         data['informaciones'] = Informacion.objects.filter(status=True, mostrar=True, tipo=2)
            #         data['procesos'] = Proceso.objects.filter(status=True, activo=True)
            #         return render(request, "alu_solicitudbalcon/informacionview.html", data)
            #     except Exception as ex:
            #         pass

            if action == 'traerinfo':
                try:
                    data['proceso'] = proceso = Proceso.objects.get(pk=int(request.GET['id']))
                    idslist = ProcesoServicio.objects.filter(proceso=proceso,status=True).values_list('id', flat=True)
                    data['informacion'] = informacion = Informacion.objects.filter(mostrar=True, tipo=2, status=True, servicio_id__in=idslist)
                    nrandom = random.randint(1, 3)
                    data['imgdefault'] = '/static/images/undraw/qs_{}.png?0.1'.format(nrandom)
                    template = get_template("alu_solicitudbalcon/detalleinfo.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

            if action == 'traercampos':
                try:
                    categoria = Categoria.objects.get(pk=int(request.GET['id']))
                    proceso = Proceso.objects.filter(status=True, activo=True, categoria=categoria).order_by('descripcion')
                    campos = [{'id': cr.pk, 'text': cr.descripcion} for cr in proceso]
                    return JsonResponse({"result": True, 'campos': campos})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': '{}'.format(ex)})

            if action == 'traercategorias':
                try:
                    procesos = Proceso.objects.filter(status=True, activo=True).distinct('categoria').values_list('categoria_id',flat=True)
                    mi_coordinacion = perfilprincipal.inscripcion.mi_coordinacion()
                    categorias = Categoria.objects.filter(status=True, estado=True,coordinaciones=mi_coordinacion)
                    if 'campo' in request.GET:
                        categorias = categorias.filter(descripcion__icontains=request.GET['campo'])
                    data['categorias'] = categorias.order_by('descripcion')
                    template = get_template("alu_solicitudbalcon/traercategorias.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': '{}'.format(ex)})

            if action == 'misolicitudes':
                try:
                    solicitudes = Solicitud.objects.filter(solicitante=persona, status=True).order_by('-id')
                    data['title'] = 'Mis Solicitudes'
                    data['solicitudes'] = solicitudes
                    return render(request, "alu_solicitudbalcon/view.html", data)
                except Exception as ex:
                    pass

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
            #loadFormEncuestaCalificar
            if action == 'loadFormSolicitudCalificarServicio':
                try:
                    data['title'] = u'Adicionar informe ayudante'
                    typeForm = request.GET['typeForm'] if 'typeForm' in request.GET and request.GET['typeForm'] and str(request.GET['typeForm']) in ['new', 'qualify', 'view'] else None
                    if typeForm is None:
                        raise NameError(u"No se encontro el tipo de formulario")
                    eEncuentasProcesoVigentes = []
                    eSolicitudBalcon = None
                    id = 0
                    if typeForm in ['qualify', 'view']:
                        id = int(encrypt(request.GET['id'])) if 'id' in request.GET and encrypt(request.GET['id']) and int(encrypt(request.GET['id'])) != 0 else None
                        eSolicitudBalcon = Solicitud.objects.get(id=id)
                        eEncuentasProcesoVigentes = eSolicitudBalcon.encuesta_proceso_preguntas_vigentes()
                        data['eEncuentasProcesoVigentes'] = eEncuentasProcesoVigentes
                    else:
                        pass
                    data['frmName'] = "frmSolicitudCalificarServicio"
                    data['typeForm'] = typeForm
                    data['id'] = encrypt(id)
                    data['eSolicitudBalcon'] = eSolicitudBalcon
                    template = get_template("alu_solicitudbalcon/modal/frmSolicitudCalificarServicio.html")
                    json_content = template.render(data, request=request)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"%s" % ex.__str__()})

            return HttpResponseRedirect(request.path)

        else:
            try:
                # solicitudes = Solicitud.objects.filter(solicitante=persona, status=True, perfil=perfilprincipal).order_by('-id')
                # data['title'] = 'Listado de Solicitudes'
                # data['solicitudes'] = solicitudes
                # return render(request, "alu_solicitudbalcon/view.html", data)

                data['title'] = u'Le damos la bienvenida a balcón de servicios'
                #data['informaciones'] = Informacion.objects.filter(status=True, mostrar=True, tipo=2)

                data['procesos'] = Proceso.objects.filter(status=True, activo=True)

                solicitudsuccess = False
                if 'solicitudsuccess' in request.GET:
                    solicitudsuccess = True
                data['solicitudsuccess'] = solicitudsuccess
                return render(request, "alu_solicitudbalcon/informacionview.html", data)
            except Exception as ex:
                return redirect('/')