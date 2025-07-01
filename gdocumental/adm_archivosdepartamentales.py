# -*- coding: UTF-8 -*-
import io
import json
import os
import sys
from datetime import datetime

import pyqrcode
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, FileResponse
from django.template.loader import get_template
from django.shortcuts import render, redirect
from pdf2image import convert_from_bytes

from core.firmar_documentos import firmar
from sagest.models import Departamento
from sga.formmodel import CustomDateInput
from sga.funcionesxhtml2pdf import conviert_html_to_pdf, conviert_html_to_pdfsaveqrcertificado_generico
from .form import SolicitudFirmaDocumentoForm, FirmarDocumentoForm, CarpetaPrincipalForm, CarpetaForm, \
    CompartirCarpetaForm, AperturaProcesoForm, DepartamentoValidarDirectorForm, DepartamentoValidarArchivoForm
from settings import EMAIL_DOMAIN, SITE_STORAGE, SITE_POPPLER, DEBUG
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, generar_nombre, remover_caracteres_especiales_unicode, \
    remover_caracteres_tildes_unicode, puede_realizar_accion, convertir_fecha, logiteraccion, notificacion
from gdocumental.models import Persona, \
    DepartamentoArchivos, DepartamentoArchivosGestiones, DepartamentoArchivoCarpeta, DepartamentoArchivoDocumentos, \
    PersonasCompartidasCarpetas, ROLES_USUARIOS_DOCUMENTAL, SolicitudProcesoDocumental, ESTADO_SOLICITUD_DOCUMENTAL, \
    TIPO_CARPETA_PROCESO, LogIteraccion, Papelera
from django.db.models import Q
from sga.templatetags.sga_extras import encrypt
from django.core.files import File
from io import BytesIO
from django.utils.text import slugify
from django.core.files import File as DjangoFile
from django.core.files.base import ContentFile


def permisosarchivos(request, data):
    return True


def changeparentfolder(request, lista, nivel):
    try:
        for l in lista:
            l.parent = nivel
            l.save(request)
            if l.traerhijas():
                changeparentfolder(request, l.traerhijas(), nivel + 1)
    except Exception as ex:
        pass


@login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
# @last_access
@transaction.atomic()
def view(request):
    data = {}
    hoy = datetime.now()
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addsoliproceso':
            try:
                id = int(encrypt(request.POST['id']))
                form = AperturaProcesoForm(request.POST, request.FILES)
                if id == 0 and not request.POST['gestion']:
                    return JsonResponse({'result': True,'mensaje': f'Seleccione una gestión para continuar con la solicitud.'})
                elif request.POST['gestion']:
                    id = int(request.POST['gestion'])
                else:
                    form.desactivar()

                gestion_ = DepartamentoArchivosGestiones.objects.get(id=id)
                if form.is_valid():
                    if form.cleaned_data['finicio'] < datetime.now().date():
                        return JsonResponse({'result': True, 'mensaje': f'La fecha de inicio del proceso debe ser mayor o igual a la fecha actual.'})
                    numsolicitud = SolicitudProcesoDocumental.objects.values('id').filter(tipo=form.cleaned_data['tipo'], gestion=gestion_, status=True).count() + 1
                    filtro = SolicitudProcesoDocumental(numsolicitud=numsolicitud, persona=persona, gestion=gestion_,
                                                        nombre=f'SOLICITUD #{numsolicitud}',
                                                        tipo=form.cleaned_data['tipo'],
                                                        finicio=form.cleaned_data['finicio'],
                                                        descripcion=form.cleaned_data['descripcion'])
                    filtro.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre(f'{request.user.username}', newfile._name)
                        filtro.archivo = newfile
                    filtro.save(request)

                    logiteraccion(u'Adiciono solicitud de apertura de proceso: %s' % filtro.nombre, request, filtro, 0, persona.id,filtro.nombre, None, [persona.id])
                    log(u'Adiciono Solicitud de Apertura Proceso: %s' % filtro, request, 'add')
                    return JsonResponse({'result': False, 'mensaje': u'Guardado con exito'})
                else:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        if action == 'addfolderfirst':
            try:
                idgestion = int(encrypt(request.POST['id']))
                form = CarpetaPrincipalForm(request.POST)
                if form.is_valid():
                    gestion_ = DepartamentoArchivosGestiones.objects.get(pk=idgestion)
                    if DepartamentoArchivoCarpeta.objects.filter(status=True, nombre=form.cleaned_data['nombre'], gestion=gestion_, parent=0):
                        return JsonResponse({'result': True, 'mensaje': f"Ya existe una carpeta con este nombre {form.cleaned_data['nombre']}"})
                    filtro = DepartamentoArchivoCarpeta(propietario=persona, nombre=form.cleaned_data['nombre'], gestion=gestion_, parent=0)
                    filtro.save(request)
                    compartido_ = PersonasCompartidasCarpetas(carpeta=filtro, rol=1, persona=persona)
                    compartido_.save(request)
                    lista = filtro.personascompartidasruta()
                    logiteraccion(u'Adiciono carpeta en gestión: %s' % filtro, request, filtro, 0, persona.id, filtro.nombre, None, lista)
                    log(u'Adiciono Carpeta en Gestión: %s' % filtro, request, "add")
                    return JsonResponse({'result': False, 'mensaje': u'Guardado con exito'})
                else:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': u'Error al guardar los datos'})

        if action == 'addfolder':
            try:
                idfolder = int(encrypt(request.POST['id']))
                form = CarpetaForm(request.POST)
                if form.is_valid():
                    folderfirst = DepartamentoArchivoCarpeta.objects.get(pk=idfolder)
                    if DepartamentoArchivoCarpeta.objects.filter(status=True, nombre=form.cleaned_data['nombre'], gestion=folderfirst.gestion, carpetaref=folderfirst, parent=folderfirst.next()):
                        return JsonResponse({'result': True, 'mensaje': f"Ya existe una carpeta con este nombre {form.cleaned_data['nombre']}"})
                    filtro = DepartamentoArchivoCarpeta(propietario=persona, nombre=form.cleaned_data['nombre'], gestion=folderfirst.gestion, carpetaref=folderfirst, parent=folderfirst.next())
                    filtro.save(request)
                    compartido_ = PersonasCompartidasCarpetas(carpeta=filtro, rol=1, persona=persona)
                    compartido_.save(request)
                    lista = filtro.personascompartidasruta()
                    logiteraccion(u'Adiciono carpeta en gestión: %s' % filtro, request, filtro, 0, persona.id, filtro.nombre,None,lista)
                    log(u'Adiciono Carpeta en Gestión: %s' % filtro, request, "add")
                    return JsonResponse({'result': False, 'mensaje': u'Guardado con exito'})
                else:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': u'Error al guardar los datos'})

        if action == 'editfolder':
            try:
                idfolder = int(encrypt(request.POST['id']))
                form = CarpetaForm(request.POST)
                if form.is_valid():
                    folderfirst = DepartamentoArchivoCarpeta.objects.get(pk=idfolder)
                    nombre=folderfirst.nombre
                    if DepartamentoArchivoCarpeta.objects.filter(status=True, nombre=form.cleaned_data['nombre'], gestion=folderfirst.gestion, carpetaref=folderfirst, parent=folderfirst.next()):
                        return JsonResponse({'result': True, 'mensaje': f"Ya existe una carpeta con este nombre {form.cleaned_data['nombre']}"})
                    folderfirst.nombre = form.cleaned_data['nombre']
                    folderfirst.save(request)
                    messages.success(request, 'Carpeta editada')
                    lista = folderfirst.personascompartidasruta()
                    logiteraccion(f'Edito carpeta: {nombre} | {folderfirst.nombre}', request, folderfirst, 1, persona.id, folderfirst.nombre,None, lista)
                    log(u'Edito Carpeta en Gestión: %s' % folderfirst, request, "edit")
                    return JsonResponse({'result': False})
                else:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': u'Error al guardar los datos'})

        if action == 'uploadfile':
            try:
                id_ = int(encrypt(request.POST['folder']))
                qsbase = DepartamentoArchivoCarpeta.objects.filter(status=True, id=id_)
                if qsbase.exists():
                    filtro_ = qsbase.first()
                    gestion_ = filtro_.gestion
                    path_ = request.POST['path']
                    carpeta_, num = filtro_, 1
                    if not path_ == 'undefined':
                        listpath_ = path_.split('/')[:-1]
                        for l_ in listpath_:
                            if num == 1:
                                if DepartamentoArchivoCarpeta.objects.filter(gestion=gestion_, status=True, carpetaref=filtro_, nombre=l_, parent=num).exists():
                                    carpeta_ = DepartamentoArchivoCarpeta.objects.filter(gestion=gestion_, status=True, carpetaref=filtro_, nombre=l_, parent=num).first()
                                else:
                                    carpeta_ = DepartamentoArchivoCarpeta(propietario=persona, gestion=gestion_, status=True, carpetaref=filtro_, nombre=l_, parent=num)
                                    carpeta_.save(request)
                                    compartido_ = PersonasCompartidasCarpetas(carpeta=carpeta_, rol=1, persona=persona)
                                    compartido_.save(request)
                            else:
                                if DepartamentoArchivoCarpeta.objects.filter(gestion=gestion_, status=True, carpetaref=carpeta_, nombre=l_, parent=num).exists():
                                    carpeta_ = DepartamentoArchivoCarpeta.objects.filter(gestion=gestion_, status=True, carpetaref=carpeta_, nombre=l_, parent=num).first()
                                else:
                                    carpeta_ = DepartamentoArchivoCarpeta(propietario=persona, gestion=gestion_, status=True, carpetaref=carpeta_, nombre=l_, parent=num)
                                    carpeta_.save(request)
                                    compartido_ = PersonasCompartidasCarpetas(carpeta=carpeta_, rol=1, persona=persona)
                                    compartido_.save(request)
                            num += 1
                    print(path_)
                    # if request.user.id == filtro_.usuario_creacion.id:
                    for l in range(0, len(request.FILES)):
                        file_ = request.FILES[f'file[{l}]']
                        ext = file_.name[file_.name.rfind("."):]
                        # file_ = request.FILES['file']
                        nombrefile_ = remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(str(file_.name).lower())).replace('-', '_')
                        file_._name = nombrefile_
                        filesize = file_.size / 1024.0 ** 2
                        if DepartamentoArchivoDocumentos.objects.filter(carpeta=carpeta_, nombre=nombrefile_, propietario=persona, status=True).exists():
                            archivo_ = DepartamentoArchivoDocumentos.objects.filter(carpeta=carpeta_, nombre=nombrefile_, propietario=persona, status=True).first()
                        else:
                            archivo_ = DepartamentoArchivoDocumentos(carpeta=carpeta_, nombre=nombrefile_, propietario=persona)
                        archivo_.filesize = filesize
                        archivo_.ext = ext
                        archivo_.archivo = file_
                        archivo_.estado = 2
                        # archivo_.ruta = carpeta_.ruta_carpeta_str()
                        archivo_.save(request)
                        log(f'Cargo archivo {archivo_.__str__()}', request, "add")

                    lista=filtro_.personascompartidasruta()
                    # logiteraccion(u'Carga de {} archivos masivos: {}'.format(str(len(request.FILES)), str(filtro_)), request, filtro_, 0, persona.id,filtro_.nombre,None,lista)
                    return JsonResponse({'message': 'Archivo subido con exito'}, status=200)
                    # else:
                    #     return JsonResponse({'message': 'No puede subir archivos, no es el propietario de esta carpeta'}, status=500)
                else:
                    return JsonResponse({'message': 'Carpeta no existe'}, status=500)
            except Exception as ex:
                print(sys.exc_info()[-1].tb_lineno)
                return JsonResponse({'message': 'Intentelo más tarde. {} {}'.format(str(ex), str(sys.exc_info()[-1].tb_lineno))}, status=500)

        if action == 'changefilefolder':
            try:
                with transaction.atomic():
                    idfolder_ = int(encrypt(request.POST['idfolder']))
                    idfile = int(encrypt(request.POST['idfile']))
                    folder_ = DepartamentoArchivoCarpeta.objects.get(pk=idfolder_)
                    file_ = DepartamentoArchivoDocumentos.objects.get(pk=idfile)
                    file_.carpeta = folder_
                    file_.save(request)
                    messages.success(request, 'Archivo movido con exito.')
                    lista = file_.carpeta.personascompartidasruta()
                    logiteraccion(f'Cambio ubicación de archivo: {file_} | Carpeta: {file_.carpeta.nombre}', request, file_, 1, persona.id, file_.nombre, None, lista)
                    log(u'Cambio Ubicación de Archivo: %s' % file_, request, "change")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'changefolderfolder':
            try:
                with transaction.atomic():
                    idfolderdestino_ = int(encrypt(request.POST['idfolder']))
                    idfolder_ = int(encrypt(request.POST['idfile']))
                    foldernext_ = DepartamentoArchivoCarpeta.objects.get(pk=idfolderdestino_)
                    folder_ = DepartamentoArchivoCarpeta.objects.get(pk=idfolder_)
                    folder_.carpetaref = foldernext_
                    folder_.parent = foldernext_.parent + 1
                    folder_.save(request)
                    if folder_.traerhijas():
                        changeparentfolder(request, folder_.traerhijas(), foldernext_.parent + 2)

                    lista = folder_.personascompartidasruta()
                    messages.success(request, 'Carpeta movida con exito.')
                    logiteraccion(f'Cambio de  ubicación de carpeta: ({folder_.nombre}) | Carpeta: ({foldernext_.nombre})', request, folder_, 1, persona.id, folder_.nombre, None,lista)
                    log(u'Cambio Ubicación de Carpeta: %s' % folder_, request, "change")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'sharefolder':
            try:
                idfolder = int(encrypt(request.POST['id']))
                form = CompartirCarpetaForm(request.POST)
                if form.is_valid():
                    folder_ = DepartamentoArchivoCarpeta.objects.get(pk=idfolder)
                    if form.cleaned_data['rol'] == '1':
                        if PersonasCompartidasCarpetas.objects.filter(carpeta=folder_, rol=form.cleaned_data['rol']).exists():
                            transaction.set_rollback(True)
                            return JsonResponse({'result': True, 'mensaje': u'Ya existe una persona con el rol de propietario.'})
                    usuarios_ = form.cleaned_data['personas']
                    for ul in usuarios_:
                        compartido_ = PersonasCompartidasCarpetas(carpeta=folder_, rol=form.cleaned_data['rol'], persona=ul)
                        compartido_.save(request)
                        notificacion('Se le compartió una carpeta {} - {}'.format(folder_.nombre,compartido_.get_rol_display()),
                                     'Se le compartió la carpeta {} para su revisión'.format(folder_.nombre),
                                     ul, None, '/adm_archivosdepartamentales?action=compartidas',
                                     compartido_.pk, 1, 'sga', PersonasCompartidasCarpetas, request)

                        lista = folder_.personascompartidasruta()
                        logiteraccion(u'Comparto carpeta con: %s' % compartido_,
                                      request, compartido_, 3, persona.id, folder_.nombre,None,lista)
                        log(u'Compartió Carpeta con: %s' % compartido_, request, "add")
                    messages.success(request, f'Accesos compartidos')
                    return JsonResponse({'result': False, 'mensaje': u'Guardado con exito'})
                else:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': u'Error al guardar los datos'})

        if action == 'changerolcompartido':
            try:
                value, id = int(request.POST['value']), int(request.POST['id'])
                filtro_ = PersonasCompartidasCarpetas.objects.get(pk=id)
                if value == 1:
                    if PersonasCompartidasCarpetas.objects.filter(carpeta=filtro_.carpeta, rol=1).exists():
                        return JsonResponse({'result': 'bad', 'mensaje': u'Ya existe una persona con el rol de propietario.'})
                filtro_.rol = value
                filtro_.save(request)
                notificacion('Reasignación de rol: {} en carpeta {}'.format(filtro_.get_rol_display(), filtro_.carpeta.nombre),
                             'Su rol en la carpeta {} fue modificado a {}'.format(filtro_.carpeta.nombre, filtro_.get_rol_display()),
                             filtro_.persona, None, '/adm_archivosdepartamentales?action=compartidas',
                             filtro_.pk, 1, 'sga', PersonasCompartidasCarpetas, request)
                lista = filtro_.carpeta.personascompartidasruta()
                logiteraccion(u'Cambio de rol a usuario: %s' % filtro_, request, filtro_, 1, persona.id,filtro_.carpeta.nombre,None,lista)
                log(u'Cambio el rol de: %s' % filtro_, request, "edit")
                return JsonResponse({"result": "ok", })
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al actualizar rol."})

        if action == 'deletefile':
            try:
                with transaction.atomic():
                    id = int(encrypt(request.POST['id']))
                    instancia = DepartamentoArchivoDocumentos.objects.get(pk=id)
                    instancia.status = False
                    instancia.save(request)

                    papelera = Papelera(persona=persona, documento=instancia)
                    papelera.save(request)
                    papelera.personas_compartidas.clear()
                    lista=instancia.carpeta.personascompartidasruta()
                    for p_com in lista:
                        papelera.personas_compartidas.add(p_com[0])
                    papelera.save(request)
                    logiteraccion(u'Elimino archivo: %s' % instancia.nombre, request, instancia, 2, persona.id, instancia.nombre,None,lista)
                    log(u'Elimino archivo: %s' % instancia, request, "delete")
                    return JsonResponse({"error": False}, safe=False)
            except Exception as ex:
                return JsonResponse({'error': True, "message": "Error: {}".format(ex)}, safe=False)

        if action == 'deletefolder':
            try:
                with transaction.atomic():
                    id = int(encrypt(request.POST['id']))
                    instancia = DepartamentoArchivoCarpeta.objects.get(pk=id)
                    # if instancia.enuso():
                    #     return JsonResponse({'error': True, "message": "No se puede eliminar una carpeta en uso."}, safe=False)
                    instancia.status = False
                    instancia.save(request)

                    papelera=Papelera(persona=persona, carpeta=instancia)
                    papelera.save(request)
                    papelera.personas_compartidas.clear()
                    lista=instancia.personascompartidasruta()
                    for p_com in lista:
                        papelera.personas_compartidas.add(p_com[0])
                    papelera.save(request)
                    logiteraccion(u'Elimino carpeta: %s' % instancia.nombre, request, instancia, 2, persona.id, instancia.nombre,None, lista)
                    log(u'Elimino carpeta: %s' % instancia, request, "delete")
                    return JsonResponse({"error": False}, safe=False)
            except Exception as ex:
                return JsonResponse({'error': True, "message": "Error: {}".format(ex)}, safe=False)

        if action == 'validardirector':
            try:
                id = int(encrypt(request.POST['id']))
                departamento = DepartamentoArchivoDocumentos.objects.get(id=id)
                departamento.propietario_id = int(request.POST['propietario'])
                departamento.fvalidacion_director = hoy
                departamento.validacion_director = int(request.POST['validar_director'])
                departamento.save(request)
                log(u'Validación de director : %s' % departamento, request, "validardirector")
                return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                return JsonResponse({'result': True, "message": "Error: {}".format(ex)}, safe=False)

        if action == 'subirdocumento':
            try:
                id = int(encrypt(request.POST['id']))
                filtro = DepartamentoArchivoDocumentos.objects.get(id=id)
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    extension = newfile._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if newfile.size > 4194304:
                        raise NameError('El tamaño del archivo es mayor a 4 Mb.')
                    if not exte.lower() in ['pdf']:
                        raise NameError('Solo archivos .pdf')
                    nombrefile_ = remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(newfile._name)).replace('-', '_')
                    newfile._name = generar_nombre(f'{request.user.username}', nombrefile_)
                    filtro.archivo = newfile
                    filtro.filesize = newfile.size / 1024.0 ** 2
                filtro.fcarga_documento = hoy
                filtro.estado = 2
                filtro.ruta = filtro.carpeta.ruta_carpeta_str()
                filtro.save(request)
                log(u'Subir Documento de Asignación: %s' % filtro, request, "subirdocumento")
                return JsonResponse({"result": False, "mensaje": "Guardado con exito"}, safe=False)
            except Exception as ex:
                return JsonResponse({'result': True, "mensaje": "Error: {}".format(ex)}, safe=False)

        if action == 'firmardocumento':
            try:
                id = int(encrypt(request.POST['id']))
                filtro = DepartamentoArchivoDocumentos.objects.get(id=id)
                pdf = request.FILES["pdf"]
                firma = request.FILES["firma"]
                passfirma = request.POST['palabraclave']
                txtFirmas = json.loads(request.POST['txtFirmas'])
                if not txtFirmas:
                    return JsonResponse({'result': True, "mensaje": "Error: Debe seleccionar ubicación de la firma"}, safe=False)
                generar_archivo_firmado = io.BytesIO()
                x = txtFirmas[-1]
                datau, datas = firmar(request, passfirma, firma, pdf, x["numPage"], x["x"], x["y"], x["width"], x["height"])
                if not datau:
                    return JsonResponse({'result': True, "mensaje": datas}, safe=False)
                generar_archivo_firmado.write(datau)
                generar_archivo_firmado.write(datas)
                generar_archivo_firmado.seek(0)
                extension = pdf._name.split('.')
                tam = len(extension)
                exte = extension[tam - 1]
                nombrefile_ = remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(pdf._name)).replace('-', '_')
                _name = generar_nombre(f'{request.user.username}', nombrefile_)
                file_obj = DjangoFile(generar_archivo_firmado, name=f"{_name}_firmado.pdf")
                filtro.archivo = file_obj
                filtro.filesize = pdf.size / 1024.0 ** 2
                filtro.ext = exte
                filtro.fcarga_documento = hoy
                filtro.estado = 2
                filtro.ruta = filtro.carpeta.ruta_carpeta_str()
                filtro.save(request)
                messages.success(request, f'Documento firmado con exito')
                log(u'Firmo Documento: %s' % filtro.__str__(), request, "add")
                return JsonResponse({"result": False, "mensaje": "Guardado con exito", "to": f'{request.path}?action=buzondocumental&id={encrypt(filtro.id)}'}, safe=False)
            except Exception as ex:
                return JsonResponse({'result': True, "mensaje": "Error: {}".format(ex)}, safe=False)

        if action == 'delsoliproceso':
            try:
                with transaction.atomic():
                    id = int(encrypt(request.POST['id']))
                    instancia = SolicitudProcesoDocumental.objects.get(pk=id)
                    instancia.status = False
                    instancia.save(request)
                    logiteraccion(u'Elimino solicitud: %s' % instancia.nombre, request, instancia, 2, persona.id, instancia.nombre,None,[persona.id])
                    log(u'Elimino solicitud: %s' % instancia, request, "delete")
                    return JsonResponse({"error": False}, safe=False)
            except Exception as ex:
                return JsonResponse({'error': True, "message": "Error: {}".format(ex)}, safe=False)

        if action == 'restaurar':
            try:
                with transaction.atomic():
                    id = int(encrypt(request.POST['id']))
                    papelera=Papelera.objects.get(id=id)
                    papelera.status=False
                    papelera.save(request)
                    if papelera.carpeta:
                        instancia = papelera.carpeta
                        lista = instancia.personascompartidasruta()
                    else:
                        instancia = papelera.documento
                        lista = instancia.carpeta.personascompartidasruta()
                    instancia.status = True
                    instancia.save(request)
                    logiteraccion(u'Restauro: %s' % instancia.get_nombre(), request, instancia, 5, persona.id, instancia.nombre,None,lista)
                    log(u'Restauro carpeta o archivo: %s' % instancia, request, "restaurar")
                    return JsonResponse({"error": False}, safe=False)
            except Exception as ex:
                return JsonResponse({'error': True, "message": "Error: {}".format(ex)}, safe=False)

        if action == 'deleteregistro':
            try:
                with transaction.atomic():
                    id = int(encrypt(request.POST['id']))
                    papelera = Papelera.objects.get(id=id)
                    papelera.status = False
                    papelera.save(request)
                    if papelera.carpeta:
                        instancia = papelera.carpeta
                        lista = instancia.personascompartidasruta()
                    else:
                        instancia = papelera.documento
                        lista = instancia.carpeta.personascompartidasruta()
                    instancia.delete()
                    logiteraccion(u'Elimino definitivamente: %s' % instancia.get_nombre(), request, instancia, 4, persona.id, instancia.nombre, id,lista)
                    log(u'Elimino : %s' % instancia, request, "del")
                    return JsonResponse({"error": False}, safe=False)
            except Exception as ex:
                return JsonResponse({'error': True, "message": "Error: {}".format(ex)}, safe=False)


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        idgestionesges, iddepartamentoges, idgestionesdir, iddepartamentodir = [], [], [], []
        qsgestiones = DepartamentoArchivosGestiones.objects.filter(status=True, responsable=persona)
        idgestionesges = qsgestiones.values_list('id', flat=True)
        iddepartamentoges = qsgestiones.values_list('departamento__id', flat=True)
        departamentosarchivos = DepartamentoArchivos.objects.filter(status=True, responsable=persona)
        if departamentosarchivos.exists():
            qsgestiones = DepartamentoArchivosGestiones.objects.filter(status=True, departamento__responsable=persona)
            idgestionesdir = qsgestiones.values_list('id', flat=True)
            iddepartamentodir = qsgestiones.values_list('departamento__id', flat=True)
        idgestiones = list(list(idgestionesdir) + list(idgestionesges))
        iddepartamento = list(list(iddepartamentodir) + list(iddepartamentoges))
        data['listdepartamentos'] = listdepartamentos = DepartamentoArchivos.objects.filter(status=True, id__in=iddepartamento).order_by('departamento__nombre')
        departamentodocumentos = DepartamentoArchivoDocumentos.objects.filter(status=True, carpeta__gestion__in=idgestiones, requisito__isnull=False)
        data['valpendiente'] = departamentodocumentos.values('id').filter(departamentoreponsable_id__in=listdepartamentos.values_list('departamento_id'), validacion_director=1).count()
        data['buzonpendiente'] = DepartamentoArchivoDocumentos.objects.values('id').filter(propietario=persona, status=True, archivo='', validacion_director=2).count()

        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'soliprocesos':
                try:
                    data['title'] = u'Solicitudes de procesos'
                    search, filtro, url_vars,tipo = request.GET.get('s', ''), Q(status=True), f'&action={action}', request.GET.get('tipo','')

                    if tipo:
                        data['tipo']=idtipo=int(tipo)
                        filtro = filtro & (Q(tipo=idtipo))
                        url_vars += '&tipo=' + tipo
                    if search:
                        data['s'] = search
                        filtro = filtro & (Q(descripcion__unaccent__icontains=search) | Q(nombre__icontains=search) )
                        url_vars += '&s=' + search
                    listado = SolicitudProcesoDocumental.objects.filter(persona=persona).filter(filtro).order_by('-id')
                    paging = MiPaginador(listado, 25)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['listado'] = page.object_list
                    data['url_vars'] = url_vars
                    request.session['viewactivo'] = 2
                    return render(request, "adm_archivosdepartamentales/viewsoliprocesos.html", data)
                except Exception as ex:
                    print('Error on line {} - {}'.format(sys.exc_info()[-1].tb_lineno, ex))

            if action == 'addsoliproceso':
                try:
                    data['title'] = u'Adicionar Solicitud de Proceso'
                    midepartamento_ = persona.mi_departamento()
                    migestion_ = persona.mi_gestion()
                    if not midepartamento_:
                        return JsonResponse({"result": False, 'message': f'Usted no forma parte de un departamento.'})
                    # if not migestion_:
                    #     return JsonResponse({"result": False, 'message': f'Usted no es responsable de ninguna gestión.'})
                    qsdepartamento = DepartamentoArchivos.objects.filter(status=True, departamento=midepartamento_)
                    if not qsdepartamento:
                        return JsonResponse({"result": False, 'message': f'Su departamento no cuenta con espacio asignado a Gestión Documental, contactar con el encargado del Área de Gestión Documental.'})
                    qsgestion = DepartamentoArchivosGestiones.objects.filter(status=True, gestion=migestion_)
                    # if not qsgestion:
                    #     return JsonResponse({"result": False, 'message': f'Su Gestión no cuenta con espacio asignado a Gestión Documental, contactar con el encargado del Área de Gestión Documental.'})
                    data['gestion'] = qsgestion.first()
                    form = AperturaProcesoForm()
                    # if qsgestion:
                    #     form.desactivar()
                    form.fields['gestion'].queryset=DepartamentoArchivosGestiones.objects.filter(status=True, departamento=qsdepartamento.first())
                    data['form'] = form
                    template = get_template("adm_archivosdepartamentales/modal/formsolicitud.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            if action == 'treeview':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['listado'] = listado = DepartamentoArchivosGestiones.objects.filter(pk=id)
                    filtro = listado.first()
                    data['filtro'] = filtro
                    data['title'] = u'ARBOL DE {}'.format(filtro.gestion.descripcion)
                    return render(request, 'adm_archivosdepartamentales/arbol/viewarbol.html', data)
                except Exception as ex:
                    messages.error(request, str(ex))
                    return redirect(request.path)

            if action == 'folders':
                try:
                    data['title'] = f'Mi Unidad'
                    data['idp'] = idp = int(encrypt(request.GET['idp']))  # numparent
                    data['idf'] = idf = int(encrypt(request.GET['idf']))  # idfolder
                    data['filtro'] = ffolder_ = DepartamentoArchivoCarpeta.objects.get(pk=idf)
                    data['filesize'] = ffolder_.gestion.departamento.filesize
                    idsubcarpetas = []
                    principal=ffolder_.carpeta_principal_obj()
                    if not principal.propietario == persona:
                        compartida=PersonasCompartidasCarpetas.objects.filter(status=True, rol__in=[2, 3], carpeta_id=ffolder_.carpeta_principal(),persona=persona)
                        if compartida.exists():
                            url_ = '{}?action=folderscompartidas&idp={}&idf={}&idc={}'.format(request.path, encrypt(idp), encrypt(idf), encrypt(compartida.first().id))
                            return redirect(url_)
                        else:
                            messages.error(request, 'Usted no tiene acceso a este repositorio')
                            return redirect(request.path)
                    # if ffolder_.gestion.responsable.id == persona.id or ffolder_.gestion.departamento.responsable.id == persona.id:
                    idsubcarpetas += list(DepartamentoArchivoCarpeta.objects.filter(status=True, carpetaref=ffolder_).values_list('id', flat=True))
                    search, url_vars, filtros = request.GET.get('search', ''), '', Q(status=True)
                    if search:
                        data['search'] = search
                        filtros = filtros & (Q(nombre__icontains=search))
                        url_vars += '&search={}'.format(search)
                    data['listado_folders'] = listado_folders = DepartamentoArchivoCarpeta.objects.filter(filtros).filter(id__in=idsubcarpetas).order_by('id')
                    data['listado_files'] = listado_files = DepartamentoArchivoDocumentos.objects.filter(status=True, carpeta=ffolder_).order_by('id')
                    data['cantfolders'] = len(listado_folders)
                    data['cantfiles'] = len(listado_files)
                    # can_add_files = False
                    # if ffolder_.usuario_creacion.id == request.user.id:
                    can_add_files = True
                    data['can_add_files'] = can_add_files
                    data["url_vars"] = url_vars
                    request.session['viewactivo'] = 1
                    return render(request, 'adm_archivosdepartamentales/viewfolder.html', data)
                except Exception as ex:
                    messages.error(request, str(ex))
                    return redirect(request.path)

            if action == 'addfolder':
                try:
                    data['title'] = u'Adicionar Carpeta'
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['filtro'] = DepartamentoArchivoCarpeta.objects.get(id=id)
                    data['form'] = CarpetaForm()
                    template = get_template("adm_archivosdepartamentales/modal/formfolder.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editfolder':
                try:
                    data['title'] = u'Editar Carpeta'
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['filtro'] = filtro = DepartamentoArchivoCarpeta.objects.get(id=id)
                    data['form'] = CarpetaForm(initial=model_to_dict(filtro))
                    template = get_template("adm_archivosdepartamentales/modal/formfolder.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'sharefolder':
                try:
                    data['title'] = u'Compartir Carpeta'
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['filtro'] = filtro = DepartamentoArchivoCarpeta.objects.get(id=id)
                    data['listcompartidos'] = listcompartidos = filtro.personascompartidascarpetas_set.select_related().filter(status=True).order_by('id')
                    form = CompartirCarpetaForm()
                    form.fields['personas'].queryset = Persona.objects.none()
                    data['form'] = form
                    data['listroles'] = ROLES_USUARIOS_DOCUMENTAL[1:]
                    template = get_template("adm_archivosdepartamentales/modal/formsharefolder.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'infofolder':
                try:
                    data['title'] = u'Información de Carpeta'
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['filtro'] = filtro = DepartamentoArchivoCarpeta.objects.get(id=id)
                    data['listcompartidos'] = listcompartidos = filtro.personascompartidascarpetas_set.select_related().filter(status=True).order_by('id')
                    template = get_template("adm_archivosdepartamentales/modal/infofolder.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'buscarpersonas':
                try:
                    idsexcluidas = []
                    idscompartidos, idsexcluir = request.GET['idscompartidos'], request.GET['idsexcluir']
                    if idsexcluir and idsexcluir != 'null':
                        idsexcluir = idsexcluir.split(',')
                        idsexcluidas = [idl for idl in idsexcluir]
                    if idscompartidos:
                        idscompartidos = idscompartidos.split(',')
                        idsexcluidas += [idl for idl in idscompartidos]
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    qspersona = Persona.objects.filter(status=True, administrativo__isnull=False).exclude(id__in=idsexcluidas).order_by('apellido1')
                    if len(s) == 1:
                        qspersona = qspersona.filter((Q(nombres__icontains=q) | Q(apellido1__icontains=q) | Q(cedula__icontains=q) | Q(apellido2__icontains=q) | Q(cedula__contains=q)), Q(status=True)).distinct()[:15]
                    elif len(s) == 2:
                        qspersona = qspersona.filter((Q(apellido1__contains=s[0]) & Q(apellido2__contains=s[1])) |
                                                     (Q(nombres__icontains=s[0]) & Q(nombres__icontains=s[1])) |
                                                     (Q(nombres__icontains=s[0]) & Q(apellido1__contains=s[1]))).filter(status=True).distinct()[:15]
                    else:
                        qspersona = qspersona.filter((Q(nombres__contains=s[0]) & Q(apellido1__contains=s[1]) & Q(apellido2__contains=s[2])) |
                                                     (Q(nombres__contains=s[0]) & Q(nombres__contains=s[1]) & Q(apellido1__contains=s[2]))).filter(status=True).distinct()[:15]
                    resp = [{'id': qs.pk, 'text': f"{qs.nombre_completo_inverso()}", "departamento": qs.departamentopersona(), 'documento': qs.documento(), 'foto': qs.get_foto()} for qs in qspersona]
                    return HttpResponse(json.dumps({'status': True, 'results': resp}))
                except Exception as ex:
                    pass

            if action == 'foldersest':
                try:
                    data['title'] = f'Mi Unidad'
                    data['idp'] = idp = int(encrypt(request.GET['idp']))  # numparent
                    data['idf'] = idf = int(encrypt(request.GET['idf']))  # idfolder
                    data['filtro'] = ffolder_ = DepartamentoArchivoCarpeta.objects.get(pk=idf)
                    if not ffolder_.personascompartidascarpetas_set.filter(rol=1, persona=persona).exists():
                        messages.warning(request, 'Usted no tiene acceso a estos recursos.')
                        return redirect(request.path)
                    data['filesize'] = ffolder_.gestion.departamento.filesize
                    data['listado_files'] = listado_files = DepartamentoArchivoDocumentos.objects.filter(status=True, carpeta=ffolder_).order_by('id')
                    totalvalidados = listado_files.filter(validacion_director=True).count()
                    data['cantfiles'] = cantfiles = len(listado_files)
                    data['isvalid'] = (totalvalidados == cantfiles)
                    request.session['viewactivo'] = 1
                    return render(request, 'adm_archivosdepartamentales/viewfolderest.html', data)
                except Exception as ex:
                    messages.error(request, str(ex))
                    return redirect(request.path)

            # if action == 'papelera':
            #     try:
            #         data['title'] = u'Papelera'
            #         listado=[]
            #         search, url_vars, filtros = request.GET.get('search', ''), f'&action={action}', Q(status=False, propietario=persona)
            #         if search:
            #             data['search'] = search
            #             filtros = filtros & (Q(nombre__icontains=search))
            #             url_vars += '&search={}'.format(search)
            #         data['listado_folders']= listado_folders= DepartamentoArchivoCarpeta.objects.filter(filtros).order_by('-fecha_modificacion').values_list('id','nombre', 'fecha_modificacion')
            #         data['listado_files']= listado_files = DepartamentoArchivoDocumentos.objects.filter(filtros).order_by('-fecha_modificacion').values_list('id','nombre', 'fecha_modificacion', 'filesize', 'carpeta__nombre', 'archivo', 'ext')
            #         listado=list(listado_folders)+list(listado_files)
            #         listado=sorted(listado, key=lambda fecha: fecha[2], reverse=True)
            #         paging = MiPaginador(listado, 20)
            #         p = 1
            #         try:
            #             paginasesion = 1
            #             if 'paginador' in request.session:
            #                 paginasesion = int(request.session['paginador'])
            #             if 'page' in request.GET:
            #                 p = int(request.GET['page'])
            #             else:
            #                 p = paginasesion
            #             try:
            #                 page = paging.page(p)
            #             except:
            #                 p = 1
            #             page = paging.page(p)
            #         except:
            #             page = paging.page(p)
            #         request.session['paginador'] = p
            #         data['paging'] = paging
            #         data['rangospaging'] = paging.rangos_paginado(p)
            #         data['page'] = page
            #         data["url_vars"] = url_vars
            #         data['listado'] = page.object_list
            #         data['cantfolders'] = len(listado_folders)
            #         data['cantfiles'] = len(listado_files)
            #         request.session['viewactivo'] = 5
            #         return render(request, 'adm_archivosdepartamentales/viewpapelera.html', data)
            #     except Exception as ex:
            #         messages.error(request, str(ex))
            #         return redirect(request.path)

            if action == 'papelera':
                try:
                    data['title'] = u'Papelera'
                    search, url_vars, filtros = request.GET.get('search', ''), f'&action={action}', Q(status=True, personas_compartidas=persona)
                    if search:
                        data['search'] = search
                        filtros = filtros & (Q(nombre__icontains=search))
                        url_vars += '&search={}'.format(search)
                    listado=Papelera.objects.filter(filtros).order_by('-pk')
                    paging = MiPaginador(listado, 20)
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
                    data['listado'] = page.object_list
                    request.session['viewactivo'] = 5
                    return render(request, 'adm_archivosdepartamentales/viewpapelera_v2.html', data)
                except Exception as ex:
                    messages.error(request, str(ex))
                    return redirect(request.path)

            if action == 'validarasignacion':
                try:
                    data['title'] = f'Validar Asignación'
                    cantfiles = 0
                    if departamentosarchivos.exists():
                        departamentos = departamentosarchivos.values_list('departamento_id')
                        estado, search, filtro, url_vars = request.GET.get('est', ''), request.GET.get('s', ''), Q(status=True, requisito__isnull=False, departamentoreponsable_id__in=departamentos), f'&action={action}'

                        if estado:
                            data['est'] = est = int(estado)
                            filtro = filtro & (Q(validacion_director=est))
                            url_vars += '&est=' + estado

                        if search:
                            data['s'] = search
                            s = search.split(' ')
                            if len(s) == 1:
                                filtro = filtro & (Q(nombre__icontains=search) |
                                                   Q(propietario__cedula__icontains=search) |
                                                   Q(propietario__nombres__icontains=search) |
                                                   Q(carpeta__nombre__icontains=search))
                            if len(s) >= 2:
                                filtro = filtro & (Q(propietario__apellido1__icontains=s[0]) &
                                                   Q(propietario__apellido2__icontains=s[1]) |
                                                   Q(carpeta__nombre__icontains=search))
                            url_vars += '&s=' + search

                        listado = DepartamentoArchivoDocumentos.objects.filter(filtro).order_by('-id')
                        paging = MiPaginador(listado, 5)
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
                        cantfiles = len(page.object_list)
                        request.session['paginador'] = p
                        data['paging'] = paging
                        data['page'] = page
                        data['url_vars'] = url_vars
                        data['rangospaging'] = paging.rangos_paginado(p)
                        data['listado_files'] = page.object_list
                    data['cantfiles'] = cantfiles
                    data['estados'] = ESTADO_SOLICITUD_DOCUMENTAL
                    data['migestion'] = persona.mi_gestion()
                    request.session['viewactivo'] = 7
                    return render(request, 'adm_archivosdepartamentales/viewvalidacion.html', data)
                except Exception as ex:
                    messages.error(request, str(ex))
                    return redirect(request.path)

            if action == 'validardirector':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    departamentoarchivo = DepartamentoArchivoDocumentos.objects.get(id=id)
                    lista = departamentoarchivo.departamentoreponsable.integrantes.all().values_list('id')
                    form = DepartamentoValidarDirectorForm(initial={'propietario': departamentoarchivo.propietario, 'validar': departamentoarchivo.validacion_director})
                    form.fields['propietario'].queryset = Persona.objects.filter(status=True, id__in=lista).exclude(id=departamentoarchivo.carpeta.propietario.id)
                    form.fields['validar_director'].choices=ESTADO_SOLICITUD_DOCUMENTAL[1:]
                    data['form'] = form
                    template = get_template("adm_archivosdepartamentales/modal/formvalidardirector.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'buzondocumental':
                try:
                    data['title'] = f'Buzón de documentos'
                    id, estado, search, filtro, url_vars = request.GET.get('id', ''), request.GET.get('est', 0), request.GET.get('s', ''), Q(status=True, requisito__isnull=False, propietario=persona), f'&action={action}'
                    data['est'] = est = int(estado)
                    if est == 1:
                        filtro = filtro & (Q(archivo__exact=''))
                        url_vars += '&est=' + estado
                    elif est == 2:
                        filtro = filtro & (Q(fcarga_documento__isnull=False))
                        url_vars += '&est=' + estado
                    if search:
                        data['s'] = search
                        filtro = filtro & (Q(nombre__icontains=search) | Q(carpeta__nombre__icontains=search))
                        url_vars += '&s=' + search
                    if id:
                        data['id'] = id
                        filtro = filtro & Q(id=int(encrypt(id)))
                        url_vars += '&id=' + id

                    listado = DepartamentoArchivoDocumentos.objects.filter(filtro).order_by('-id')
                    paging = MiPaginador(listado, 5)
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
                    cantfiles = len(page.object_list)
                    request.session['paginador'] = p
                    data['paging'] = paging
                    data['page'] = page
                    data['url_vars'] = url_vars
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['listado_files'] = page.object_list
                    data['cantfiles'] = cantfiles
                    request.session['viewactivo'] = 4
                    return render(request, 'adm_archivosdepartamentales/viewbuzon.html', data)
                except Exception as ex:
                    messages.error(request, str(ex))
                    return redirect(request.path)

            if action == 'subirdocumento':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    form = DepartamentoValidarArchivoForm()
                    data['form'] = form
                    template = get_template("adm_archivosdepartamentales/modal/formuploaddoc.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'firmardocumento':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['title'] = f'Firmar documento'
                    data['filtro'] = filtro = DepartamentoArchivoDocumentos.objects.get(id=id)
                    return render(request, 'adm_archivosdepartamentales/firmardocumento.html', data)
                except Exception as ex:
                    pass

            if action == 'firmavistaprevia':
                try:
                    data["DOMINIO_DEL_SISTEMA"] = dominio_sistema = request.build_absolute_uri('/')[:-1].strip("/")
                    folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'firmaelectronica', ''))
                    os.makedirs(folder, exist_ok=True)
                    qrname = 'qr_firma_{}'.format(persona.id)
                    rutapdf = '{}{}.pdf'.format(folder, qrname)
                    rutaimg = '{}{}.png'.format(folder, qrname)
                    url = pyqrcode.create(f'FIRMADO POR: {persona.__str__()}\nFECHA: {datetime.now()}\nVALIDAR CON: www.firmadigital.gob.ec\nFIRMADO EN: sga.unemi.edu.ec')
                    url.png('{}{}.png'.format(folder, qrname), 16, '#1C3247')  # '#1C3247'
                    # url.svg('{}/{}.svg'.format(directory_qr, qrname), 16, '#1C3247')
                    url_path = dominio_sistema
                    data['url_path'] = url_path
                    data['qrname'] = '{}'.format(qrname)
                    data['persona'] = persona
                    valida, pdfge, result = conviert_html_to_pdfsaveqrcertificado_generico(request, 'adm_archivosdepartamentales/firma/vistapreviafirma.html', {'data': data}, folder, f'{qrname}.pdf')
                    if valida:
                        with open(f'{folder}{qrname}.pdf', mode='rb') as pdf:
                            images = convert_from_bytes(pdf.read(), output_folder=folder, poppler_path=SITE_POPPLER, fmt="png", single_file=True, output_file=f'{qrname}_firma')  # dpi=95, size=(150, 45)
                    return conviert_html_to_pdf('adm_archivosdepartamentales/firma/vistapreviafirma.html', {'data': data})
                except Exception as ex:
                    pass

            if action == 'seguimientoproceso':
                try:
                    data['title'] = 'Seguimiento de carga de archivos'
                    data['idf'] = idf = int(encrypt(request.GET['id']))  # idfolder
                    data['filtro'] = ffolder_ = DepartamentoArchivoCarpeta.objects.get(pk=idf)
                    data['listado_files'] = listado_files = DepartamentoArchivoDocumentos.objects.filter(status=True, carpeta=ffolder_).order_by('id')
                    data['cantfiles'] = len(listado_files)
                    template = get_template("adm_archivosdepartamentales/modal/infoseguimiento.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'compartidas':
                try:
                    data['title'] = f'Compartido conmigo'
                    id, search, filtro, url_vars = request.GET.get('id', ''), request.GET.get('s', ''), Q(status=True, persona=persona, rol__in=[2,3]), f'&action={action}'
                    if search:
                        filtro = filtro & (Q(carpeta__nombre__unaccent__icontains=search))
                        url_vars += '&s=' + search
                        data['s'] = search
                    data['url_vars']=url_vars
                    data['listado'] = listado = PersonasCompartidasCarpetas.objects.filter(filtro).order_by('id')
                    request.session['viewactivo'] = 3
                    return render(request, 'adm_archivosdepartamentales/viewcompartidas.html', data)
                except Exception as ex:
                    messages.error(request, str(ex))
                    return redirect(request.path)

            if action == 'folderscompartidas':
                try:
                    data['title'] = f'Compartido conmigo'
                    data['idp'] = idp = int(encrypt(request.GET['idp']))  # numparent
                    data['idf'] = idf = int(encrypt(request.GET['idf']))  # idfolder
                    data['idc']= idc =int(encrypt(request.GET['idc'])) #idcompartido
                    data['filtro'] = ffolder_ = DepartamentoArchivoCarpeta.objects.get(pk=idf)
                    data['compartido'] =compartida = PersonasCompartidasCarpetas.objects.get(pk=idc)
                    data['filesize'] = ffolder_.gestion.departamento.filesize
                    idsubcarpetas = []
                    if compartida.rol == 4:
                        messages.error(request, 'Usted no tiene acceso a este repositorio')
                        url_ = '{}?action=compartidas'.format(request.path)
                        return redirect(url_)
                    # if ffolder_.gestion.responsable.id == persona.id or ffolder_.gestion.departamento.responsable.id == persona.id:
                    idsubcarpetas += list(
                        DepartamentoArchivoCarpeta.objects.filter(status=True, carpetaref=ffolder_).values_list('id',
                                                                                                                flat=True))
                    search, url_vars, filtros = request.GET.get('search', ''), '', Q(status=True)
                    if search:
                        data['search'] = search
                        filtros = filtros & (Q(nombre__icontains=search))
                        url_vars += '&search={}'.format(search)
                    data['listado_folders'] = listado_folders = DepartamentoArchivoCarpeta.objects.filter(
                        filtros).filter(id__in=idsubcarpetas).order_by('id')
                    data['listado_files'] = listado_files = DepartamentoArchivoDocumentos.objects.filter(status=True,
                                                                                                         carpeta=ffolder_).order_by(
                        'id')
                    data['cantfolders'] = len(listado_folders)
                    data['cantfiles'] = len(listado_files)
                    # can_add_files = False
                    # if ffolder_.usuario_creacion.id == request.user.id:
                    can_add_files = True
                    data['can_add_files'] = can_add_files
                    data["url_vars"] = url_vars
                    request.session['viewactivo'] = 3
                    return render(request, 'adm_archivosdepartamentales/viewcompartidasfolders.html', data)
                except Exception as ex:
                    messages.error(request, str(ex))
                    return redirect(request.path)

            if action == 'log':
                try:
                    data['title'] = f'Mi actividad'
                    accion, search, filtro, url_vars = request.GET.get('accion', ''), \
                                                       request.GET.get('s', ''), \
                                                       Q(status=True, personas_compartidas=persona), f'&action={action}'

                    if accion:
                        data['accion'] = accion
                        filtro = filtro & Q(accion=int(accion))
                        url_vars += '&acc=' + accion

                    if search:
                        filtro = filtro & (
                                    Q(categoria__descripcion__unaccent__icontains=search) | Q(nombre__icontains=search))
                        url_vars += '&s=' + search
                        data['s'] = search
                    data["url_vars"] = url_vars
                    listado = LogIteraccion.objects.filter(filtro).order_by('-id')
                    paging = MiPaginador(listado, 25)
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
                    data["url_vars"] = url_vars
                    data['listado'] = page.object_list
                    data['listcount'] = len(listado)
                    request.session['viewactivo'] = 6
                    return render(request, 'adm_archivosdepartamentales/viewlog.html', data)
                except Exception as ex:
                    messages.error(request, str(ex))
                    return redirect(request.path)

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Repositorio Departamental'
            search, filtro, url_vars = request.GET.get('s', ''), Q(status=True, persona=persona, estado__in=[1,2]), ''
            if search:
                filtro = filtro & (Q(categoria__descripcion__unaccent__icontains=search) | Q(nombre__icontains=search))
                url_vars += '&s=' + search
                data['s'] = search
            data["url_vars"] = url_vars
            listado = SolicitudProcesoDocumental.objects.filter(filtro).order_by('-id')
            paging = MiPaginador(listado, 25)
            p = 1
            try:
                paginasesion = 1
                if 'paginador' in request.session:
                    paginasesion = int(request.session['paginador'])
                if 'page' in request.GET:
                    p = int(request.GET['page'])
                    # p = int(request.GET['page'])
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
            data["url_vars"] = url_vars
            data['listado'] = page.object_list
            data['listcount'] = len(listado)
            request.session['viewactivo'] = 1
            return render(request, 'adm_archivosdepartamentales/view.html', data)
