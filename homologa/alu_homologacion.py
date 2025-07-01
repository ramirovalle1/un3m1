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

from decorators import last_access, secure_module
from homologa.forms import SubirDocumentoForm
from homologa.models import SolicitudEstudianteHomologacion, PeriodoHomologacion, ResponsableHomologacion, \
    DocumentosSolicitudHomologacion, RequisitoPeriodoHomologacion, SeguimientoRevision
from sga.commonviews import adduserdata
from sga.funciones import generar_nombre, log, notificacion, remover_caracteres_especiales_unicode, MiPaginador
from sga.models import NivelMalla, Malla, Inscripcion
from sga.templatetags.sga_extras import encrypt


# @csrf_exempt
@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    hoy=datetime.now().date()
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    data['periodo']= periodo = request.session['periodo']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    data['inscripcion_p'] = inscripcion = perfilprincipal.inscripcion
    # if not inscripcion.puede_solicitar_cambio_carrera():
    #     return HttpResponseRedirect("/?info=Solo los estudiantes que hayan aprobado mas del 50% de las materias de primer nivel pueden ingresar al modulo.")
    data['inscripcionmalla'] = inscripcionmalla = inscripcion.malla_inscripcion()
    if not inscripcionmalla:
        return HttpResponseRedirect("/?info=Este estudiante no tiene ninguna malla asociada")
    periodo_h=PeriodoHomologacion.objects.filter(status=True, publico=True, fechainiciorecepciondocumentos__lte=hoy,fechacierrerecepciondocumentos__gte=hoy).first()
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addsolicitud':
            with transaction.atomic():
                try:
                    carrera = int(request.POST.get('carrera', 0))
                    carrera_text = request.POST.get('carrera_text', '')
                    if SolicitudEstudianteHomologacion.objects.filter(periodo_h=periodo_h, status=True, inscripcion=inscripcion, estado__in=[0, 1, 3, 4]).values('id').exists():
                        raise NameError("Ya existe una solicitud de homologación de asignaturas en este periodo abierto.")
                    if carrera == 0 and not carrera_text:
                        raise NameError("Debe seleccionar o digitar una carrera a homologar.")
                    totalsubidos = 0
                    totalsubidosmultiple = 0
                    documentos_requeridos_multiple = periodo_h.requisitos_visibles().filter(status=True, multiple=True)
                    documentos_requeridos = periodo_h.requisitos_visibles().filter(status=True, multiple=False)

                    for dr in documentos_requeridos:
                        if 'doc_{}'.format(dr.id) in request.FILES:
                            totalsubidos += 1
                        elif dr.opcional:
                            totalsubidos += 1
                    for dm in documentos_requeridos_multiple:
                        if 'doc_{}[]'.format(dm.id) in request.FILES:
                            totalsubidosmultiple += 1
                        elif dm.opcional:
                            totalsubidosmultiple += 1

                    if not totalsubidos == len(documentos_requeridos) or not totalsubidosmultiple == len(documentos_requeridos_multiple):
                        raise NameError("Debe subir todos los requisitos.")

                    #Permite asignar casos equitativamente a 4 administrativos con id de persona quemados
                    verificador = SolicitudEstudianteHomologacion.objects.filter(status=True, periodo_h=periodo_h).values('id')
                    responsables = ResponsableHomologacion.objects.filter(status=True, rol=0, estado=True).values_list('id', flat=True)
                    lista = []
                    for p in responsables:
                        total=len(verificador.filter(persona_gacademica=p))
                        lista.append((p,total))
                    id_ga, min_value = min(lista, key=lambda item: item[1])
                    malla=None
                    if carrera != 0:
                        malla = Malla.objects.filter(status=True, carrera_id=carrera).first()
                    solicitud = SolicitudEstudianteHomologacion(periodo_h=periodo_h,
                                                               inscripcion=inscripcion,
                                                               malla_anterior=malla,
                                                               carrera_anterior=carrera_text,
                                                               persona_gacademica_id=id_ga,)
                    solicitud.save(request)

                    for dr in documentos_requeridos:
                        obligatorio=True
                        if dr.opcional:
                            obligatorio=False
                        docrequerido = DocumentosSolicitudHomologacion(solicitud=solicitud, obligatorio=obligatorio, requisito=dr)
                        docrequerido.save(request)
                        if f'doc_{dr.id}' in request.FILES:
                            newfile = request.FILES[f'doc_{dr.id}']
                            extension = newfile._name.split('.')
                            tam = len(extension)
                            exte = extension[tam - 1]
                            if newfile.size > 4194304:
                                raise NameError('Error, el tamaño del archivo es mayor a 4 Mb.')
                            if not exte.lower() in ['pdf']:
                                raise NameError('Error, solo archivos .pdf')
                            newfile._name = generar_nombre(f"p_{persona.id}__rp{dr.id}_", newfile._name)
                            docrequerido.archivo = newfile
                            docrequerido.save(request)

                    # Guarda Archivos de seleccion multiple
                    for dm in documentos_requeridos_multiple:
                        obligatorio = True
                        if dm.opcional:
                            obligatorio = False
                        if f'doc_{dm.id}[]' in request.FILES:
                            docmultiple = request.FILES.getlist(f'doc_{dm.id}[]')
                            descripciones = request.POST.getlist(f'desc_{dm.id}[]')
                            niveles = request.POST.getlist(f'nivel_{dm.id}[]')
                            mensaje='Por favor complete todos los campos.'
                            if dm.essilabo and len(docmultiple) != len(niveles) or len(docmultiple) != len(descripciones):
                                raise NameError(mensaje)
                            elif not dm.essilabo and len(docmultiple) != len(descripciones):
                                raise NameError(mensaje)
                            cont = 0
                            for drmultiple in docmultiple:
                                nivel = None
                                if not dm.essilabo :
                                    if descripciones[cont] == '':
                                        raise NameError(mensaje)
                                    cuerpo = f'rp_{dr.id}'
                                else:
                                    if descripciones[cont] == '' or niveles[cont] == '':
                                        raise NameError(mensaje)
                                    nivel=niveles[cont]
                                    cuerpo = f'silabo_{dr.id}'
                                newfile = drmultiple
                                extension = newfile._name.split('.')
                                tam = len(extension)
                                exte = extension[tam - 1]
                                if newfile.size > 4194304:
                                    raise NameError("El tamaño del archivo es mayor a 4 Mb.")
                                if not exte.lower() in ['pdf']:
                                    raise NameError("Error, solo archivos .pdf")
                                newfile._name = generar_nombre(f"p_{persona.id}__{cuerpo}__{cont}",newfile._name)
                                docrequerido = DocumentosSolicitudHomologacion(solicitud=solicitud,
                                                                               obligatorio=obligatorio,
                                                                               requisito=dm,
                                                                               nivel_id=nivel,
                                                                               descripcion=descripciones[cont])
                                docrequerido.save(request)
                                docrequerido.archivo = newfile
                                docrequerido.save(request)
                                cont += 1
                        else:
                            docrequerido = DocumentosSolicitudHomologacion(solicitud=solicitud,
                                                                           obligatorio=obligatorio,
                                                                           requisito=dm)
                            docrequerido.save(request)

                    notificacion('Nueva solicitud de homologacion de asignaturas', 'Se le asigno una solicitud de homologación de asignaturas', solicitud.persona_gacademica.persona,
                                 None, f'/adm_homologacion?action=solicitudes&id={encrypt(solicitud.periodo_h.pk)}&s={solicitud.inscripcion.persona.cedula}', solicitud.pk,
                                 1, 'sga', SolicitudEstudianteHomologacion, request)

                    log(u'Adiciono Solicitud de homologación de asignaturas: %s' % solicitud, request, "add")
                    messages.success(request, 'Solicitud registrada con éxito, sus datos serán validados')
                    return JsonResponse({"result": False, 'to': '{}?action=verproceso&id={}'.format(request.path, encrypt(solicitud.pk))}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": str(ex)}, safe=False)

        if action == 'subirdocumento':
            with transaction.atomic():
                try:
                    form = SubirDocumentoForm(request.POST, request.FILES)
                    idp = int(encrypt(request.POST['idp']))
                    ids = int(encrypt(request.POST['ids']))
                    id=int(encrypt(request.POST['id']))
                    solicitud=SolicitudEstudianteHomologacion.objects.get(id=ids)
                    if solicitud.revision_gacademica == 1 or solicitud.revision_gacademica == 2:
                        raise NameError('No puede subir mas documentación debido a que su solicitud ya fue validada en el primer paso.')
                    requisito=RequisitoPeriodoHomologacion.objects.get(pk=idp)
                    obligatorio=True if not requisito.opcional else False
                    if requisito.multiple and not requisito.essilabo:
                        form.solo_multiple()
                    elif not requisito.multiple and not requisito.essilabo:
                        form.individual()
                    if form.is_valid():
                        if id != 0:
                            documento=DocumentosSolicitudHomologacion.objects.get(id=id)
                            documento.nivel=form.cleaned_data['nivel']
                            documento.descripcion=form.cleaned_data['descripcion']
                            if documento.estado == 3:
                                documento.f_correccion=datetime.now()
                                documento.estado = 4
                                titulo = u"Documento de homologación de asignaturas ({})".format(documento.get_estado_display())
                                mensaje = f"Documento ({documento}) fue corregido"
                                notificacion(titulo, mensaje, documento.solicitud.persona_gacademica.persona, None,
                                             f'/adm_homologacion?action=solicitudes&id={encrypt(documento.solicitud.periodo_h.pk)}&s={documento.solicitud.inscripcion.persona.cedula}',
                                             documento.pk, 1, 'sga', DocumentosSolicitudHomologacion, request)
                            lista=['Edito documento de solicitud','edit']
                        else:
                            documento = DocumentosSolicitudHomologacion(solicitud_id=ids,
                                                                        requisito_id=idp,
                                                                        obligatorio=obligatorio,
                                                                        nivel=form.cleaned_data['nivel'],
                                                                        descripcion=form.cleaned_data['descripcion'])
                            lista = ['Adiciono documento de solicitud', 'add']

                        documento.save(request)
                        newfile = request.FILES[f'archivo']
                        extension = newfile._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if newfile.size > 4194304:
                            raise NameError('Error, el tamaño del archivo es mayor a 4 Mb.')
                        if not exte.lower() in ['pdf']:
                            raise NameError('Error, solo archivos .pdf')
                        newfile._name = generar_nombre(f"p_{persona.id}__rp{requisito.id}_", newfile._name)
                        documento.archivo = newfile
                        documento.save(request)
                        if documento.estado == 4:
                            seguimiento = SeguimientoRevision(documento=documento,estado_doc=4,
                                                              solictud=solicitud,estado=solicitud.estado,
                                                              rutaarchivo=documento.archivo.url,
                                                              observacion='Corrección de documento enviado a corregir.'
                                                              )
                            seguimiento.save(request)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                             "mensaje": "Error en el formulario"})
                    log(f'{lista[0]}: {documento}', request, lista[1])
                    return JsonResponse({"result": False}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        if action == 'deldocumento':
            with transaction.atomic():
                try:
                    if not request.POST['observacion']:
                        raise NameError('Por favor escriba el motivo de eliminación del documento')
                    instancia = DocumentosSolicitudHomologacion.objects.get(pk=int(encrypt(request.POST['id'])))
                    if not instancia.estado == 0:
                        raise NameError('Documento que intenta eliminar ya fue validado por favor actualizar la pagina')
                    instancia.observacion = request.POST['observacion']
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino documento de solicitud: %s' % instancia, request, "del")
                    messages.success(request, 'Documento eliminado correctamente')
                    return JsonResponse({'result': True}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": "{}".format(str(ex))},safe=False)
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
            if action == 'addsolicitud':
                try:
                    data['periodo_h'] = periodo_h
                    data['nivelesdemallas'] = NivelMalla.objects.filter(status=True).order_by('orden')
                    data['inscripciones']=Inscripcion.objects.filter(status=True, persona=persona, coordinacion_id__in=[1,2,3,4,5]).exclude(id=inscripcion.id)
                    template = get_template("alu_homologacion/modal/formsolicitud.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'verproceso':
                try:
                    data['title']='Proceso de solicitud'
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['filtro'] = filtro = SolicitudEstudianteHomologacion.objects.get(pk=id)
                    data['paso'] = 0
                    return render(request, 'alu_homologacion/viewproceso.html', data)
                except Exception as ex:
                    pass

            if action == 'subirdocumento':
                try:
                    id=int(request.GET.get('id',0))
                    idp=int(request.GET.get('idp',0))
                    data['ids']=request.GET['idex']
                    data['rq']=requisito=RequisitoPeriodoHomologacion.objects.get(pk=idp)
                    if id !=0:
                        data['filtro'] = documento = DocumentosSolicitudHomologacion.objects.get(pk=id)
                        form = SubirDocumentoForm(model_to_dict(documento))
                    else:
                        form = SubirDocumentoForm()
                    if requisito.multiple and not requisito.essilabo:
                        form.solo_multiple()
                    elif not requisito.multiple and not requisito.essilabo:
                        form.individual()

                    data['form'] = form
                    template = get_template("alu_homologacion/modal/formsubirarchivo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass
        else:
            try:
                data['title'] = u'Homologación de asignaturas'
                search, filtro, url_vars = request.GET.get('s', ''), Q(status=True, inscripcion=inscripcion), ''

                if search:
                    filtro = filtro & (Q(periodo_h__periodo__nombre__unaccent__icontains=search))
                    url_vars += '&s=' + search
                    data['s'] = search

                listado = SolicitudEstudianteHomologacion.objects.filter(filtro)
                paging = MiPaginador(listado, 10)
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
                data["url_vars"] = url_vars
                data['periodo_h']=periodo_h
                data['listado'] = page.object_list
                return render(request, 'alu_homologacion/viewsolicitudeshomologacion.html', data)
            except Exception as ex:
                return render({'result': False, 'mensaje': f'{ex}'})