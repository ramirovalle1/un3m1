# -*- coding: UTF-8 -*-

import json
import html
import os
import random
import sys
import zipfile
# from datetime import datetime, timedelta, time
import time as ET
import requests

from django.core.files.base import ContentFile
from django.db.models.functions import ExtractYear
from django.template.loader import get_template
import xlwt
from webpush import send_user_notification
from xlwt import *
from django.contrib.auth.decorators import login_required
from django.db import transaction, connections
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from django.template import Context

from decorators import secure_module, last_access
from investigacion.funciones import coordinador_investigacion, analista_investigacion, notificar_revision_solicitud_produccion_cientifica
from sagest.commonviews import obtener_estados_solicitud, obtener_estado_solicitud
from sagest.models import SolicitudPublicacion, ParticipanteSolicitudPublicacion
from settings import SITE_STORAGE
from sga.commonviews import adduserdata, traerNotificaciones
from sga.forms import EvidenciaForm, ArticulosInvestigacionForm, \
    ParticipanteProfesorArticuloForm, ParticipanteAdministrativoArticuloForm, BaseIndexadaInvestigacionForm, \
    RevistaInvestigacionForm, BaseIndexadaInvestigacionListaForm, ParticipanteInscripcionArticuloForm, \
    ArticulosInvestigacionAuxForm, DocumentoIndexacionForm, ArticulosInvestigacion3Form, RevistaInvestigacionAdminForm, \
    RevistaInvestigacionEditAdminForm, SolicitudPublicacionForm, ArticuloProceedingForm
from sga.funciones import MiPaginador, log, generar_nombre, convertir_fecha_invertida, cuenta_email_disponible, \
    remover_caracteres_tildes_unicode, remover_caracteres_especiales_unicode, elimina_tildes, remover_caracteres, cuenta_email_disponible_para_envio, validar_archivo
from sga.models import Evidencia, DetalleEvidencias, ProyectosInvestigacion, \
    ArticuloInvestigacion, ParticipantesArticulos, ArticulosBaseIndexada, RevistaInvestigacion, \
    BaseIndexadaInvestigacion, TIPO_PARTICIPANTE_INSTITUCION, Persona, CUENTAS_CORREOS, RevistaInvestigacionBase, \
    miinstitucion, TIPO_PARTICIPANTE, RedPersona, Notificacion
from sga.funcionesxhtml2pdf import conviert_html_to_pdf, convert_html_to_pdf
from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt



@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    miscarreras = persona.mis_carreras()

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'actualizardocumentoindexacion':
            try:
                revistabase = RevistaInvestigacionBase.objects.get(pk=int(request.POST['id']))
                f = DocumentoIndexacionForm(request.POST, request.FILES)

                if 'documento' in request.FILES:
                    arch = request.FILES['documento']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if not exte.lower() == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                if f.is_valid():
                    newfile = request.FILES['documento']
                    newfile._name = generar_nombre("docindexacion_", newfile._name)
                    revistabase.documentoindexacion = newfile
                    revistabase.save(request)

                    log(u'Aactualizó documento de indexación de revista: %s' % revistabase.revista, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

        elif action == 'add':
            try:
                f = ArticulosInvestigacionForm(request.POST)
                if f.is_valid():
                    if not ArticuloInvestigacion.objects.filter(nombre=f.cleaned_data['nombre']).exists():
                        programas = ArticuloInvestigacion(nombre=f.cleaned_data['nombre'],
                                                          doy=f.cleaned_data['doy'],
                                                          indexada=f.cleaned_data['indexada'],
                                                          fecharecepcion=f.cleaned_data['fecharecepcion'],
                                                          fechaaprobacion=f.cleaned_data['fechaaprobacion'],
                                                          fechapublicacion=f.cleaned_data['fechapublicacion'],
                                                          volumen=f.cleaned_data['volumen'],
                                                          numero=f.cleaned_data['numero'],
                                                          paginas=f.cleaned_data['paginas'],
                                                          enlace=f.cleaned_data['enlace'],
                                                          estado=f.cleaned_data['estado'],
                                                          revista=f.cleaned_data['revista'],
                                                          areaconocimiento=f.cleaned_data['areaconocimiento'],
                                                          subareaconocimiento=f.cleaned_data['subareaconocimiento'],
                                                          subareaespecificaconocimiento=f.cleaned_data['subareaespecificaconocimiento'],
                                                          accesoabierto=f.cleaned_data['accesoabierto'],
                                                          cuartil=f.cleaned_data['cuartil'],
                                                          jcr=f.cleaned_data['jcr'],
                                                          sjr=f.cleaned_data['sjr']
                                                          )
                        programas.save(request)
                        log(u'Adiciono articulo de investigacion: %s [%s]' % (programas,programas.id), request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Ya el articulo esta ingresado."})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addarticulo':
            try:
                f = ArticuloProceedingForm(request.POST, request.FILES)

                archivo = request.FILES['archivoportada']
                descripcionarchivo = 'Portada e Índice'
                resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                archivo = request.FILES['archivoarticulo']
                descripcionarchivo = 'Artículo'
                resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '10MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivocarta' in request.FILES:
                    archivo = request.FILES['archivocarta']
                    descripcionarchivo = 'Carta de aceptación'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if f.is_valid():
                    revista = f.cleaned_data['revista2']
                    if not revista.basesindexadas():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La revista %s no tiene bases indexadas" % (revista.nombre) , "showSwal": "True", "swalType": "warning"})

                    if not ArticuloInvestigacion.objects.filter(nombre=f.cleaned_data['nombre'], status=True).exists():
                        # Artículo
                        articulo = ArticuloInvestigacion(nombre=f.cleaned_data['nombre'].strip().upper(),
                                                         resumen=f.cleaned_data['resumen'].strip(),
                                                          doy=f.cleaned_data['doi'],
                                                          indexada=f.cleaned_data['revistaindexada'],
                                                          fecharecepcion=f.cleaned_data['fecharecepcion'],
                                                          fechaaprobacion=f.cleaned_data['fechaaprobacion'],
                                                          fechapublicacion=f.cleaned_data['fechapublicacion'],
                                                          volumen=f.cleaned_data['volumen'],
                                                          numero=f.cleaned_data['numero'],
                                                          paginas=f.cleaned_data['paginas'],
                                                          enlace=f.cleaned_data['enlace'],
                                                          estado=1,
                                                          revista=f.cleaned_data['revista2'],
                                                          areaconocimiento=f.cleaned_data['areaconocimiento'],
                                                          subareaconocimiento=f.cleaned_data['subareaconocimiento'],
                                                          subareaespecificaconocimiento=f.cleaned_data['subareaespecificaconocimiento'],
                                                          accesoabierto=f.cleaned_data['accesoabierto'],
                                                          cuartil=f.cleaned_data['cuartilarticulo'] if f.cleaned_data['cuartilarticulo'].isdigit() else None,
                                                          jcr=f.cleaned_data['jcrarticulo'],
                                                          sjr=f.cleaned_data['sjrarticulo'],
                                                          provieneproyecto=f.cleaned_data['provieneproyecto'],
                                                          tipoproyecto=f.cleaned_data['tipoproyecto'] if f.cleaned_data['provieneproyecto'] else None,
                                                          lineainvestigacion=f.cleaned_data['lineainvestigacion'],
                                                          sublineainvestigacion=f.cleaned_data['sublineainvestigacion'],
                                                          pertenecegrupoinv=f.cleaned_data['pertenecegrupoinv'],
                                                          grupoinvestigacion=f.cleaned_data['grupoinvestigacion'],
                                                          solicitudpublicacion=None,
                                                          tipoarticulo=1 if int(f.cleaned_data['tiposolicitud']) == 1 else 2,
                                                          categoria=int(request.POST['categoriaarticuloid']),
                                                          observacion=f.cleaned_data['observacion'].upper().strip()
                                                          )
                        articulo.save(request)

                        if f.cleaned_data['provieneproyecto']:
                            if int(f.cleaned_data['tipoproyecto']) != 3:
                                articulo.proyectointerno = f.cleaned_data['proyectointerno']
                            else:
                                articulo.proyectoexterno = f.cleaned_data['proyectoexterno']
                        articulo.save(request)

                        # Bases indexadas del artículo
                        revistabases = revista.basesindexadas()
                        for revistabase in revistabases:
                            articulobase = ArticulosBaseIndexada(articulo=articulo,
                                                                 baseindexada=revistabase.baseindexada)
                            articulobase.save(request)

                        # ARTÍCULO
                        evidencia1 = Evidencia.objects.get(pk=1)
                        newfile = request.FILES['archivoarticulo']
                        newfile._name = generar_nombre("articulo", newfile._name)

                        detalleevidencia = DetalleEvidencias(evidencia=evidencia1,
                                                             articulo=articulo,
                                                             descripcion='ARTÍCULO PUBLICADO',
                                                             archivo=newfile)
                        detalleevidencia.save(request)

                        # CERTIFICADO ACEPTACION
                        if 'archivocarta' in request.FILES:
                            evidencia2 = Evidencia.objects.get(pk=3)
                            newfile = request.FILES['archivocarta']
                            newfile._name = generar_nombre("cartaaceptacion", newfile._name)

                            detalleevidencia = DetalleEvidencias(evidencia=evidencia2,
                                                                 articulo=articulo,
                                                                 descripcion='CARTA DE ACEPTACION DE ARTÍCULO',
                                                                 archivo=newfile)
                            detalleevidencia.save(request)

                        # PORTADA E ÍNDICE
                        evidencia3 = Evidencia.objects.get(pk=26)
                        newfile = request.FILES['archivoportada']
                        newfile._name = generar_nombre("portada", newfile._name)

                        detalleevidencia = DetalleEvidencias(evidencia=evidencia3,
                                                             articulo=articulo,
                                                             descripcion='PORTADA E ÍNDICE',
                                                             archivo=newfile)
                        detalleevidencia.save(request)

                        log(u'%s adicionó artículo de investigacion: %s [%s]' % (persona, articulo, articulo.id), request, "add")
                        return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
                    else:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El título para el tipo de publicación ya ha sido ingresado anteriormente", "showSwal": "True", "swalType": "warning"})
                else:
                    msg = ",".join([k + ': ' + v[0] for k, v in f.errors.items()])
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'ingresarsolicitudarticulo':
            try:
                solicitud = SolicitudPublicacion.objects.get(pk=int(encrypt(request.POST['ids'])))

                if solicitud.registrado:
                    return JsonResponse({"result": "bad", "mensaje": u"La solicitud ya ha sido registrada como Artículo."})

                f = ArticulosInvestigacion3Form(request.POST)
                if f.is_valid():
                    estadosolicitud = int(request.POST['estadosolicitud'])

                    # Si el estado es VERIFICADO
                    if estadosolicitud == 57:
                        revista = f.cleaned_data['revista2']
                        if not revista.basesindexadas():
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La revista %s no tiene bases indexadas" % (revista.nombre), "showSwal": "True", "swalType": "warning"})

                        if not ArticuloInvestigacion.objects.filter(nombre=f.cleaned_data['nombre'], status=True).exists():
                            if solicitud.tiposolicitud == 1:
                                categoriaconfirmada = int(f.cleaned_data['categoriaconfirmada']) == 1
                            else:
                                categoriaconfirmada = True

                            articulo = ArticuloInvestigacion(nombre=f.cleaned_data['nombre'],
                                                              resumen=f.cleaned_data['resumen'],
                                                              doy=f.cleaned_data['doi'],
                                                              indexada=f.cleaned_data['revistaindexada'],
                                                              fecharecepcion=f.cleaned_data['fecharecepcion'],
                                                              fechaaprobacion=f.cleaned_data['fechaaprobacion'],
                                                              fechapublicacion=f.cleaned_data['fechapublicacion'],
                                                              volumen=f.cleaned_data['volumen'],
                                                              numero=f.cleaned_data['numero'],
                                                              paginas=f.cleaned_data['paginas'],
                                                              enlace=f.cleaned_data['enlace'],
                                                              estado=f.cleaned_data['estadopublicacion'],
                                                              revista=f.cleaned_data['revista2'],
                                                              areaconocimiento=f.cleaned_data['areaconocimiento'],
                                                              subareaconocimiento=f.cleaned_data['subareaconocimiento'],
                                                              subareaespecificaconocimiento=f.cleaned_data['subareaespecificaconocimiento'],
                                                              accesoabierto=f.cleaned_data['accesoabierto'],
                                                              cuartil=f.cleaned_data['cuartilarticulo'] if f.cleaned_data['cuartilarticulo'].isdigit() else None,
                                                              jcr=f.cleaned_data['jcrarticulo'],
                                                              sjr=f.cleaned_data['sjrarticulo'],
                                                              provieneproyecto=f.cleaned_data['provieneproyecto'],
                                                              tipoproyecto=f.cleaned_data['tipoproyecto'] if f.cleaned_data['provieneproyecto'] else None,
                                                              lineainvestigacion=f.cleaned_data['lineainvestigacion'],
                                                              sublineainvestigacion=f.cleaned_data['sublineainvestigacion'],
                                                              solicitudpublicacion=solicitud,
                                                              tipoarticulo=1 if solicitud.tiposolicitud == 1 else 2,
                                                              categoriaconfirmada=categoriaconfirmada,
                                                              categoria=int(request.POST['categoriaarticuloid']) if request.POST['categoriaarticuloid'] != '' else None,
                                                              observacion=f.cleaned_data['observacion'].upper().strip(),
                                                              pertenecegrupoinv=f.cleaned_data['pertenecegrupoinv'],
                                                              grupoinvestigacion=f.cleaned_data['grupoinvestigacion']
                                                              )
                            articulo.save(request)

                            if f.cleaned_data['provieneproyecto']:
                                if int(f.cleaned_data['tipoproyecto']) != 3:
                                    articulo.proyectointerno = f.cleaned_data['proyectointerno']
                                else:
                                    articulo.proyectoexterno = f.cleaned_data['proyectoexterno']
                            articulo.save(request)

                            solicitud.registrado = True
                            solicitud.estado_id = estadosolicitud
                            solicitud.save(request)

                            revistabases = revista.basesindexadas()
                            for revistabase in revistabases:
                                articulobase = ArticulosBaseIndexada(articulo=articulo,
                                                                     baseindexada=revistabase.baseindexada)
                                articulobase.save(request)

                            if solicitud.estadopublicacion == 1:
                                # ARTICULO ACADEMICO
                                evidencia1 = Evidencia.objects.get(pk=1)
                                new_file = ContentFile(solicitud.archivo.file.read())
                                new_file.name = generar_nombre("articulo", solicitud.nombre_archivo_publicacion())

                                detalleevidencia = DetalleEvidencias(evidencia=evidencia1,
                                                                     articulo=articulo,
                                                                     descripcion='ARTÍCULO PUBLICADO',
                                                                     archivo=new_file)
                                detalleevidencia.save(request)

                            # CERTIFICADO ACEPTACION
                            if solicitud.archivocertificado:
                                evidencia2 = Evidencia.objects.get(pk=3)
                                new_file = ContentFile(solicitud.archivocertificado.file.read())
                                new_file.name = generar_nombre("cartaaceptacion", solicitud.nombre_archivo_carta_aceptacion())

                                detalleevidencia = DetalleEvidencias(evidencia=evidencia2,
                                                                     articulo=articulo,
                                                                     descripcion='CARTA DE ACEPTACION DE ARTÍCULO',
                                                                     archivo=new_file)
                                detalleevidencia.save(request)

                            # PORTADA E ÍNDICE
                            if solicitud.archivocomite:
                                evidencia3 = Evidencia.objects.get(pk=26)
                                new_file = ContentFile(solicitud.archivocomite.file.read())
                                new_file.name = generar_nombre("portada", solicitud.nombre_archivo_portada_indice())

                                detalleevidencia = DetalleEvidencias(evidencia=evidencia3,
                                                                     articulo=articulo,
                                                                     descripcion='PORTADA E ÍNDICE',
                                                                     archivo=new_file)
                                detalleevidencia.save(request)

                            # Participantes: Autores/Coautores
                            participantes = ParticipanteSolicitudPublicacion.objects.filter(solicitud=solicitud, status=True).order_by('id')
                            for p in participantes:
                                participantearticulo = ParticipantesArticulos(matrizevidencia_id=3,
                                                                              articulo=articulo,
                                                                              profesor=p.profesor,
                                                                              tipo=p.tipo,
                                                                              administrativo=p.administrativo,
                                                                              tipoparticipanteins=p.tipoparticipanteins,
                                                                              inscripcion=p.inscripcion)
                                participantearticulo.save(request)

                            notificar_revision_solicitud_produccion_cientifica(solicitud)

                            log(u'Adicionó artÍculo de investigación: %s [%s]' % (articulo, articulo.id), request, "add")
                            return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
                        else:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El artículo con ese título ya está ingresado", "showSwal": "True", "swalType": "warning"})
                    else:
                        observacion = request.POST['observacionsolicitud'].strip().upper()

                        # Actualiza solicitud
                        solicitud.estado_id = estadosolicitud
                        solicitud.observacion = observacion
                        solicitud.save(request)

                        notificar_revision_solicitud_produccion_cientifica(solicitud)

                        if solicitud.estado.valor == 3:
                            log(u'Registró novedad en solicitud: %s' % solicitud.persona, request, "edit")
                        else:
                            log(u'Rechazó solicitud de artículo: %s' % solicitud.persona, request, "edit")

                        return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
                else:
                    errorformulario = f._errors
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addrevista':
            try:
                f = RevistaInvestigacionAdminForm(request.POST, request.FILES)

                tiporegistro = int(request.POST['tiporegistro'])

                if f.is_valid():
                    idsbase = json.loads(request.POST['lista_items1'])
                    archivosbase = request.FILES.getlist('documento[]')

                    for base, file in zip(idsbase, archivosbase):
                        arch = file

                        extension = arch._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if arch.size > 4194304:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb para [%s]." % (base['nombrebase'])})
                        if not exte.lower() == 'pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf para [%s]" % (base['nombrebase'])})

                    if not RevistaInvestigacion.objects.filter(nombre=f.cleaned_data['nombrerevista'], codigoissn=f.cleaned_data['codigoissn'], tiporegistro=tiporegistro, borrador=False).exists():
                        revista = RevistaInvestigacion(nombre=f.cleaned_data['nombrerevista'],
                                                       codigoissn=f.cleaned_data['codigoissn'],
                                                       institucion=f.cleaned_data['institucion'],
                                                       tipo=f.cleaned_data['tipo'],
                                                       cuartil=f.cleaned_data['cuartil'] if f.cleaned_data['cuartil'].isdigit() else None,
                                                       sjr=f.cleaned_data['sjr'],
                                                       jcr=f.cleaned_data['jcr'],
                                                       enlace=f.cleaned_data['enlacerevista'],
                                                       tiporegistro=tiporegistro)
                        revista.save(request)

                        bases = f.cleaned_data['baseindexada']
                        for base in bases:
                            revistabase = RevistaInvestigacionBase(revista=revista,
                                                                   baseindexada_id=base.id,
                                                                   documentoindexacion=None
                                                                   )
                            revistabase.save(request)

                        for base, file in zip(idsbase, archivosbase):
                            idbase = base['idbase']
                            arch = file
                            arch._name = generar_nombre("docindexacion_", arch._name)

                            revistabase = RevistaInvestigacionBase.objects.get(revista=revista, baseindexada_id=idbase)
                            revistabase.documentoindexacion = arch
                            revistabase.save(request)

                        if 'revistaborradorid' in request.POST:
                            if request.POST['revistaborradorid'] != '':
                                if request.POST['revistaborradorid'] != 'None':
                                    RevistaInvestigacion.objects.filter(pk=int(request.POST['revistaborradorid'])).update(status=False)

                        log(u'Adiciono revista de investigacion: %s [%s]' % (revista, revista.id), request, "add")

                        if 'registromodal' not in request.POST:
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "ok", "id": revista.id})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"La Revista ya ha sido ingresada anteriormente."})
                else:
                    errorformulario = f._errors
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

        elif action == 'updatetipoparticipante':
            try:
                participantes = ParticipantesArticulos.objects.get(pk=request.POST['iditem'])
                idtipo = request.POST['idtipo']
                participantes.tipoparticipanteins = idtipo
                participantes.save(request)
                log(u'Actualizo tipo de participante en articulo: %s [%s]' % (participantes, participantes.id), request, "edit")
                return JsonResponse({'result': 'ok', 'idarticulo': encrypt(participantes.articulo.id)})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad'})

        elif action == 'updatetipoautor':
            try:
                participantes = ParticipantesArticulos.objects.get(pk=request.POST['iditem'])
                idtipo = request.POST['idtipo']
                participantes.tipo = idtipo
                participantes.save(request)
                log(u'Actualizo tipo de participante autor en articulo: %s [%s]' % (participantes, participantes.id), request, "edit")
                return JsonResponse({'result': 'ok', 'idarticulo': encrypt(participantes.articulo.id)})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad'})

        elif action == 'addbase':
            try:
                f = BaseIndexadaInvestigacionForm(request.POST)
                if f.is_valid():
                    if not BaseIndexadaInvestigacion.objects.filter(nombre=f.cleaned_data['nombre'].upper()).exists():
                        base = BaseIndexadaInvestigacion(nombre=f.cleaned_data['nombre'],
                                                         categoria=f.cleaned_data['categoria']
                                                         )
                        base.save(request)
                        log(u'Adiciono base en indexada de investigacion: %s [%s]' % (base, base.id),request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"La base ya está ingresada."})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'pdffichacatalograficas':
            try:
                data = {}
                data['participante'] = articulo = ParticipantesArticulos.objects.get(pk=request.POST['id'],status=True)
                data['basesindexadas'] = ArticulosBaseIndexada.objects.filter(articulo_id=articulo.articulo_id,status=True)
                return conviert_html_to_pdf(
                    'inv_articulos/fichacatalografica_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as ex:
                pass

        elif action == 'pdffichacatalograficas_articulo':
            try:
                data = {}
                data['participantess'] = articulo = ParticipantesArticulos.objects.filter(articulo__id=int(encrypt(request.POST['id'])), status=True)
                data['cantidad'] = articulo.count()
                data['basesindexadas'] = ArticulosBaseIndexada.objects.filter(articulo_id=int(encrypt(request.POST['id'])), status=True)
                return conviert_html_to_pdf(
                    'inv_articulos/fichacatalografica_articulo_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as ex:
                pass

        elif action == 'editarticulo':
            try:
                f = ArticulosInvestigacion3Form(request.POST)

                articulo = ArticuloInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))
                if f.is_valid():
                    if not ArticuloInvestigacion.objects.filter(nombre=f.cleaned_data['nombre'], status=True).exclude(pk=int(encrypt(request.POST['id']))).exists():

                        if articulo.tipoarticulo == 1:
                            categoriaconfirmada = int(f.cleaned_data['categoriaconfirmada']) == 1
                        else:
                            categoriaconfirmada = True

                        if request.POST['categoriaarticuloid'] == '':
                            observacion = ''
                        else:
                            observacion = f.cleaned_data['observacion'] if int(request.POST['categoriaarticuloid']) != int(request.POST['categoriabaseid']) else ''

                        articulo.nombre = f.cleaned_data['nombre']
                        articulo.resumen = f.cleaned_data['resumen']
                        articulo.doy = f.cleaned_data['doi']
                        articulo.indexada = f.cleaned_data['revistaindexada']
                        articulo.fecharecepcion = f.cleaned_data['fecharecepcion']
                        articulo.fechaaprobacion = f.cleaned_data['fechaaprobacion']
                        articulo.fechapublicacion = f.cleaned_data['fechapublicacion']
                        articulo.volumen = f.cleaned_data['volumen']
                        articulo.numero = f.cleaned_data['numero']
                        articulo.paginas = f.cleaned_data['paginas']
                        articulo.enlace = f.cleaned_data['enlace']
                        articulo.estado = f.cleaned_data['estadopublicacion']
                        articulo.revista = f.cleaned_data['revista2']
                        articulo.areaconocimiento = f.cleaned_data['areaconocimiento']
                        articulo.subareaconocimiento = f.cleaned_data['subareaconocimiento']
                        articulo.subareaespecificaconocimiento = f.cleaned_data['subareaespecificaconocimiento']
                        articulo.accesoabierto = f.cleaned_data['accesoabierto']
                        articulo.cuartil = f.cleaned_data['cuartilarticulo'] if f.cleaned_data['cuartilarticulo'].isdigit() else None
                        articulo.jcr = f.cleaned_data['jcrarticulo']
                        articulo.sjr = f.cleaned_data['sjrarticulo']
                        articulo.provieneproyecto = f.cleaned_data['provieneproyecto']
                        articulo.tipoproyecto = f.cleaned_data['tipoproyecto'] if f.cleaned_data['provieneproyecto'] else None
                        articulo.lineainvestigacion = f.cleaned_data['lineainvestigacion']
                        articulo.sublineainvestigacion = f.cleaned_data['sublineainvestigacion']
                        articulo.pertenecegrupoinv = f.cleaned_data['pertenecegrupoinv']
                        articulo.grupoinvestigacion = f.cleaned_data['grupoinvestigacion']
                        articulo.categoriaconfirmada = categoriaconfirmada
                        articulo.categoria = int(request.POST['categoriaarticuloid']) if request.POST['categoriaarticuloid'] != '' else None
                        articulo.observacion = observacion
                        articulo.save(request)

                        if f.cleaned_data['provieneproyecto']:
                            if int(f.cleaned_data['tipoproyecto']) != 3:
                                articulo.proyectointerno = f.cleaned_data['proyectointerno']
                                articulo.proyectoexterno = None
                            else:
                                articulo.proyectoexterno = f.cleaned_data['proyectoexterno']
                                articulo.proyectointerno = None
                        else:
                            articulo.tipoproyecto = None
                            articulo.proyectointerno = None
                            articulo.proyectoexterno = None

                        articulo.save(request)

                        revistabases = articulo.revista.basesindexadas()
                        lista1 = [rb.baseindexada.id for rb in revistabases]
                        lista2 = [ab.baseindexada.id for ab in articulo.articulosbaseindexada_set.filter(status=True)]
                        if not lista1 == lista2:
                            articulo.articulosbaseindexada_set.update(status=False)
                            for revistabase in revistabases:
                                articulobase = ArticulosBaseIndexada(articulo=articulo,
                                                                     baseindexada=revistabase.baseindexada)
                                articulobase.save(request)

                        log(u'Editó artículo de investigación: %s [%s]' % (articulo, articulo.id), request, "edit")
                        return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
                    else:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El artículo con ese título ya está ingresado", "showSwal": "True", "swalType": "warning"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editrevista':
            try:
                f = RevistaInvestigacionAdminForm(request.POST, request.FILES)

                revista = RevistaInvestigacion.objects.get(pk=request.POST['id'])
                if f.is_valid():
                    idsbase = json.loads(request.POST['lista_items1'])
                    archivosbase = request.FILES.getlist('documento[]')

                    for base, file in zip(idsbase, archivosbase):
                        arch = file

                        extension = arch._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if arch.size > 4194304:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb para [%s]." % (base['nombrebase'])})
                        if not exte.lower() == 'pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf para [%s]" % (base['nombrebase'])})

                    if not RevistaInvestigacion.objects.filter(nombre=f.cleaned_data['nombrerevista'], codigoissn=f.cleaned_data['codigoissn'], borrador=False).exclude(pk=request.POST['id']).exists():
                        revista.nombre = f.cleaned_data['nombrerevista']
                        revista.codigoissn = f.cleaned_data['codigoissn']
                        revista.institucion = f.cleaned_data['institucion']
                        revista.enlace = f.cleaned_data['enlacerevista']
                        revista.tipo = f.cleaned_data['tipo']
                        revista.cuartil = f.cleaned_data['cuartil'] if f.cleaned_data['cuartil'].isdigit() else None
                        revista.sjr = f.cleaned_data['sjr']
                        revista.jcr = f.cleaned_data['jcr']
                        revista.save(request)

                        bases = f.cleaned_data['baseindexada']
                        basesnoseleccionadas = BaseIndexadaInvestigacion.objects.filter(revistainvestigacionbase__revista=revista, revistainvestigacionbase__status=True).exclude(pk__in=bases).order_by('nombre')

                        for base in bases:
                            if not RevistaInvestigacionBase.objects.filter(baseindexada=base, revista=revista).exists():
                                revistabase = RevistaInvestigacionBase(revista=revista,
                                                                       baseindexada_id=base.id,
                                                                       documentoindexacion=None
                                                                       )
                                revistabase.save(request)
                            elif RevistaInvestigacionBase.objects.filter(baseindexada=base, revista=revista, status=False).exists():
                                RevistaInvestigacionBase.objects.filter(revista=revista, baseindexada=base).update(status=True)

                        RevistaInvestigacionBase.objects.filter(revista=revista, baseindexada__in=basesnoseleccionadas).update(status=False)

                        for base, file in zip(idsbase, archivosbase):
                            idbase = base['idbase']
                            arch = file
                            arch._name = generar_nombre("docindexacion_", arch._name)

                            revistabase = RevistaInvestigacionBase.objects.get(revista=revista, baseindexada_id=idbase)
                            revistabase.documentoindexacion = arch
                            revistabase.save(request)

                        log(u'Edito revista de investigacion: %s [%s]' % (revista, revista.id), request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"La Revista ya ha sido ingresada anteriormente."})
                else:
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

        elif action == 'editrevistaarticulo':
            try:
                f = RevistaInvestigacionEditAdminForm(request.POST, request.FILES)

                revista = RevistaInvestigacion.objects.get(pk=request.POST['idrev'])
                if f.is_valid():

                    idsbase = json.loads(request.POST['lista_items1'])
                    archivosbase = request.FILES.getlist('documento[]')

                    for base, file in zip(idsbase, archivosbase):
                        arch = file

                        extension = arch._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if arch.size > 4194304:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb para [%s]." % (base['nombrebase'])})
                        if not exte.lower() == 'pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf para [%s]" % (base['nombrebase'])})

                    if not RevistaInvestigacion.objects.filter(nombre=f.cleaned_data['nombrerevista2'], codigoissn=f.cleaned_data['codigoissn2'], borrador=False).exclude(pk=request.POST['idrev']).exists():
                        revista.nombre = f.cleaned_data['nombrerevista2']
                        revista.codigoissn = f.cleaned_data['codigoissn2']
                        revista.institucion = f.cleaned_data['institucion2']
                        revista.enlace = f.cleaned_data['enlacerevista2']
                        revista.tipo = f.cleaned_data['tipo2']
                        revista.cuartil = f.cleaned_data['cuartil2'] if f.cleaned_data['cuartil2'].isdigit() else None
                        revista.sjr = f.cleaned_data['sjr2']
                        revista.jcr = f.cleaned_data['jcr2']
                        revista.save(request)

                        bases = f.cleaned_data['baseindexada2']
                        basesnoseleccionadas = BaseIndexadaInvestigacion.objects.filter(revistainvestigacionbase__revista=revista, revistainvestigacionbase__status=True).exclude(pk__in=bases).order_by('nombre')

                        for base in bases:
                            if not RevistaInvestigacionBase.objects.filter(baseindexada=base, revista=revista).exists():
                                revistabase = RevistaInvestigacionBase(revista=revista,
                                                                       baseindexada_id=base.id,
                                                                       documentoindexacion=None
                                                                       )
                                revistabase.save(request)
                            elif RevistaInvestigacionBase.objects.filter(baseindexada=base, revista=revista, status=False).exists():
                                RevistaInvestigacionBase.objects.filter(revista=revista, baseindexada=base).update(status=True)


                        RevistaInvestigacionBase.objects.filter(revista=revista, baseindexada__in=basesnoseleccionadas).update(status=False)

                        for base, file in zip(idsbase, archivosbase):
                            idbase = base['idbase']
                            arch = file
                            arch._name = generar_nombre("docindexacion_", arch._name)

                            revistabase = RevistaInvestigacionBase.objects.get(revista=revista, baseindexada_id=idbase)
                            revistabase.documentoindexacion = arch
                            revistabase.save(request)

                        log(u'Edito revista de investigacion: %s [%s]' % (revista, revista.id), request, "edit")
                        return JsonResponse({"result": "ok", "idrevista": revista.id})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"La Revista ya ha sido ingresada anteriormente."})
                else:
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

        elif action == 'editbase':
            try:
                f = BaseIndexadaInvestigacionForm(request.POST)
                base = BaseIndexadaInvestigacion.objects.get(pk=request.POST['id'])
                if f.is_valid():
                    if not BaseIndexadaInvestigacion.objects.filter(nombre=f.cleaned_data['nombre']).exclude(pk=request.POST['id']).exists():
                        base.nombre = f.cleaned_data['nombre']
                        base.categoria = f.cleaned_data['categoria']
                        base.save(request)
                        log(u'Edito base de indexada de investigacion: %s [%s]' % (base, base.id), request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"La base ya está ingresada."})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteparticipantearticulo':
            try:
                participante = ParticipantesArticulos.objects.get(pk=request.POST['id'])
                participante.status = False
                participante.save(request)
                log(u'Elimino participante de articulos de investigacion: %s [%s]' % (participante, participante.id), request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'deletearticulo':
            try:
                articulos = ArticuloInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))
                participantes = ParticipantesArticulos.objects.filter(articulo=articulos, matrizevidencia_id=3)
                bases = ArticulosBaseIndexada.objects.filter(articulo=articulos)
                evidencias = DetalleEvidencias.objects.filter(articulo=articulos)
                for participante in participantes:
                    participante.status = False
                    participante.save(request)
                for base in bases:
                    base.status = False
                    base.save(request)
                for evidencia in evidencias:
                    evidencia.status = False
                    evidencia.save(request)
                articulos.status = False
                articulos.save(request)
                log(u'Eliminó artículo de investigación: %s [%s]' % (articulos, articulos.id), request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'deletebasesarticulos':
            try:
                baseindex = ArticulosBaseIndexada.objects.get(pk=request.POST['id'])
                baseindex.status = False
                baseindex.save(request)
                log(u'Elimino base de articulos base indexada: %s [%s]' % (baseindex, baseindex.id), request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addbaseindexarticulo':
            try:
                baseindex = ArticulosBaseIndexada(articulo_id=request.POST['articulo'],
                                                  baseindexada_id=request.POST['idbaseindex'])
                baseindex.save(request)
                log(u'Adiciono base indexada de activulos: %s [%s]' % (baseindex, baseindex.id), request, "add")
                return JsonResponse({'result': 'ok', 'valor': request.POST['articulo']})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteproyecto':
            try:
                proyecto = ProyectosInvestigacion.objects.get(pk=request.POST['id'])
                proyecto.status = False
                proyecto.save(request)
                log(u'Eliminar proyecto de investigacion: %s [%s]' % (proyecto, proyecto.id), request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addparticipantesdocentes':
            try:
                f = ParticipanteProfesorArticuloForm(request.POST)
                if f.is_valid():
                    if ParticipantesArticulos.objects.filter(status=True, matrizevidencia_id=3, articulo_id=int(encrypt(request.POST['id'])), profesor_id=f.cleaned_data['profesor']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El participante ya fue agregado anteriormente."})
                    else:
                        programas = ParticipantesArticulos(matrizevidencia_id=3,
                                                           articulo_id=int(encrypt(request.POST['id'])),
                                                           profesor_id=f.cleaned_data['profesor'],
                                                           tipo=f.cleaned_data['tipo'],
                                                           tipoparticipanteins=f.cleaned_data['tipoparticipanteins']
                                                           )
                        programas.save(request)
                        log(u'Adicionó participantes docentes en artículos: %s [%s]' % (programas, programas.id), request, "add")
                        return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addparticipantesadministrativos':
            try:
                f = ParticipanteAdministrativoArticuloForm(request.POST)
                if f.is_valid():
                    if ParticipantesArticulos.objects.filter(status=True, matrizevidencia_id=3, articulo_id=int(encrypt(request.POST['id'])), administrativo_id=f.cleaned_data['administrativo']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El participante ya fue agregado anteriormente."})
                    else:
                        programas = ParticipantesArticulos(matrizevidencia_id=3,
                                                           articulo_id=int(encrypt(request.POST['id'])),
                                                           administrativo_id=f.cleaned_data['administrativo'],
                                                           tipo=f.cleaned_data['tipo'],
                                                           tipoparticipanteins=f.cleaned_data['tipoparticipanteins']
                                                           )
                        programas.save(request)
                        log(u'Adicionó participantes administrativo en artículos: %s [%s]' % (programas, programas.id), request, "add")
                        return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addparticipantesinscripcion':
            try:
                f = ParticipanteInscripcionArticuloForm(request.POST)
                if f.is_valid():
                    if ParticipantesArticulos.objects.filter(status=True, matrizevidencia_id=3, articulo_id=int(encrypt(request.POST['id'])), inscripcion_id=f.cleaned_data['inscripcion']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El participante ya fue agregado anteriormente."})
                    else:
                        programas = ParticipantesArticulos(matrizevidencia_id=3,
                                                           articulo_id=int(encrypt(request.POST['id'])),
                                                           inscripcion_id=f.cleaned_data['inscripcion'],
                                                           tipo=f.cleaned_data['tipo'],
                                                           tipoparticipanteins=f.cleaned_data['tipoparticipanteins']
                                                           )
                        programas.save(request)
                        log(u'Adiciono participantes estudiante en articulos: %s [%s]' % (programas, programas.id), request, "add")
                        return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addevidenciasarticulos':
            try:
                f = EvidenciaForm(request.POST, request.FILES)
                # 2.5MB - 2621440
                # 5MB - 5242880
                # 10MB - 10485760
                # 20MB - 20971520
                # 50MB - 5242880
                # 100MB 104857600
                # 250MB - 214958080
                # 500MB - 429916160
                d = request.FILES['archivo']
                if d.size > 10485760:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                if f.is_valid():
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("articulo_", newfile._name)
                    if DetalleEvidencias.objects.filter(evidencia_id=int(encrypt(request.POST['idevidencia'])), articulo_id=int(encrypt(request.POST['id']))).exists():
                        detalle = DetalleEvidencias.objects.get(evidencia_id=int(encrypt(request.POST['idevidencia'])), articulo_id=int(encrypt(request.POST['id'])))
                        detalle.descripcion = f.cleaned_data['descripcion']
                        detalle.archivo = newfile
                        detalle.save(request)
                        log(u'Adicionó evidencia de artículos en artículo de investigación: %s [%s]' % (detalle, detalle.id), request, "add")
                    else:
                        evidencia = DetalleEvidencias(evidencia_id=int(encrypt(request.POST['idevidencia'])),
                                                      articulo_id=int(encrypt(request.POST['id'])),
                                                      descripcion=f.cleaned_data['descripcion'],
                                                      archivo=newfile)
                        evidencia.save(request)
                        log(u'Adicionó evidencia de artículos en artículo de investigación: %s [%s]' % (evidencia, evidencia.id), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'solicitudes':
            try:
                data['solicitudes'] = SolicitudPublicacion.objects.filter(tiposolicitud__in=[1, 5], status=True, estado__valor=1).order_by('fecha_creacion')
                template = get_template("inv_articulos/solicitudes.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'verarticulos':
            try:
                data['personaarticulos'] = personaarticulos = Persona.objects.get(pk=int(request.POST['idp']))
                template = get_template("inv_articulos/verarticulos.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'aprobar':
            try:
                solicitudes = SolicitudPublicacion.objects.get(pk=request.POST['id'])
                solicitudes.aprobado = True
                solicitudes.save(request)
                log(u'Aprobo solicitud: %s' % solicitudes.persona, request, "edit")

                # FALTA ENVIO DE CORREO

                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al aprobar los datos."})

        elif action == 'preaprobararticulo':
            try:
                # Consulto el artículo
                articulo = ArticuloInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))

                # Obtengo estado PRE-APROBADO
                estado = obtener_estado_solicitud(8, 6)

                # if articulo.solicitudpublicacion:
                solicitud = SolicitudPublicacion.objects.get(pk=articulo.solicitudpublicacion.id)
                solicitud.estado = estado
                solicitud.save(request)

                articulo.preaprobado = True
                articulo.save(request)

                notificar_revision_solicitud_produccion_cientifica(solicitud)

                log(u'%s Pre-aprobó artículo: %s' % (persona, articulo.nombre), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'aprobararticulo':
            try:
                articulo = ArticuloInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))

                # Si existe solicitud
                if articulo.solicitudpublicacion:
                    estadosolicitud = obtener_estado_solicitud(8, 5)  # APROBADO

                    solicitud = SolicitudPublicacion.objects.get(pk=articulo.solicitudpublicacion.id)
                    solicitud.aprobado = True
                    solicitud.estado = estadosolicitud
                    solicitud.save(request)

                articulo.aprobado = True
                articulo.save(request)

                integrantes = articulo.participantes()
                articulo.tipoaporte = 1 if integrantes.filter(tipoparticipanteins=1).count() >= 1 else 2
                articulo.save(request)

                # Si existe solicitud se debe notificar
                if articulo.solicitudpublicacion:
                    notificar_revision_solicitud_produccion_cientifica(solicitud)

                log(u'%s Aprobó artículo: %s' % (persona, articulo.nombre), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'rechazar':
            try:
                solicitud = SolicitudPublicacion.objects.get(pk=request.POST['id'])
                observacion = request.POST['observacion'].strip().upper()
                if observacion:
                    solicitud.aprobado = False
                    solicitud.observacion = observacion
                    solicitud.save(request)
                    log(u'Rechazo solicitud: %s' % solicitud.persona, request, "edit")
                    asunto = u"Solicitud de Registro de Artículo Rechazada"

                    cuenta = cuenta_email_disponible()

                    send_html_mail(asunto,
                                   "emails/estadosolicitudarticulo.html",
                                   {'sistema': 'SGA - UNEMI',
                                    'saludo': 'Estimado' if solicitud.persona.sexo.id == 2 else 'Estimada',
                                    'titulo': solicitud.nombre,
                                    'motivorechazo': observacion,
                                    'solicitante': solicitud.persona.nombre_completo_inverso()},
                                   solicitud.persona.lista_emails_envio(),
                                   [],
                                   cuenta=CUENTAS_CORREOS[cuenta][1])
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Debe ingresar una observación."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'evidenciasarticulo':
            try:
                import time as ET
                # Aquí se almacenan las fichas catalográficas
                directorio = SITE_STORAGE + '/media/articulos'
                try:
                    os.stat(directorio)
                except:
                    os.mkdir(directorio)

                caracteres_a_quitar = "!\"\#$%&()=?¡'¿{}[],.-+*/|°^~:;"
                anio = request.POST['anio']
                output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'zipav'))

                response = HttpResponse(content_type='application/zip')
                response['Content-Disposition'] = 'attachment; filename=articulosevidencias_' + random.randint(1, 10000).__str__() + '.zip'

                nombre_archivo = "evidenciasarticulos" + anio + ".zip"
                filename = os.path.join(output_folder, nombre_archivo)
                fantasy_zip = zipfile.ZipFile(filename, 'w')

                articulos_publicados = ArticuloInvestigacion.objects.filter(status=True, fechapublicacion__year=anio).order_by('id')
                total1 = articulos_publicados.count()

                articulos_no_publicados = ArticuloInvestigacion.objects.filter(status=True, fechapublicacion__isnull=True, fechaaprobacion__year=anio).order_by('id')
                total2 = articulos_no_publicados.count()

                total = total1 + total2
                rp = 0
                # articulos_publicados = ArticuloInvestigacion.objects.filter(status=True, fechapublicacion__year=anio).order_by('id')[:10]

                for articulo in articulos_publicados:
                    rp += 1
                    print("Procesando", rp, " de ", total)
                    titulo = articulo.nombre

                    palabras = titulo.split(" ")
                    titulo = "_".join(palabras[0:5])
                    titulo = remover_caracteres(titulo, caracteres_a_quitar)

                    titulo = elimina_tildes(remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(titulo)))
                    carpetaarticulo = "PUBLICADOS/ART_" + articulo.revista.codigoissn.strip().replace('-', '_') + "_" + str(articulo.id)+ "_" + titulo

                    articulo_id = articulo.id
                    nombre = "ARTICULO_" + str(articulo_id).zfill(4)

                    # Agrego las evidencias a la carpeta del artículo
                    for evidencia in articulo.detalleevidencias_set.filter(status=True):
                        ext = evidencia.archivo.__str__()[evidencia.archivo.__str__().rfind("."):]

                        if evidencia.descripcion:
                            nombreevidencia = evidencia.descripcion.upper()
                            nombreevidencia = remover_caracteres(nombreevidencia, caracteres_a_quitar)
                            nombreevidencia = elimina_tildes(remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(nombreevidencia))).replace(" ", "_")
                        else:
                            nombreevidencia = "EVIDENCIA" + random.randint(1, 10000).__str__()

                        if evidencia.evidencia.id == 1:
                            if os.path.exists(SITE_STORAGE + evidencia.archivo.url):
                                fantasy_zip.write(SITE_STORAGE + evidencia.archivo.url, carpetaarticulo + "/" + nombreevidencia + ext.lower())
                        elif evidencia.evidencia.id == 3:
                            if os.path.exists(SITE_STORAGE + evidencia.archivo.url):
                                fantasy_zip.write(SITE_STORAGE + evidencia.archivo.url, carpetaarticulo + "/" + nombreevidencia + ext.lower())

                    # Generar la ficha catalográfica del artículo
                    data['participantess'] = participantes = ParticipantesArticulos.objects.filter(articulo=articulo, status=True)
                    data['cantidad'] = participantes.count()
                    data['basesindexadas'] = ArticulosBaseIndexada.objects.filter(articulo=articulo, status=True)

                    nombrearchivoficha = 'fichacatalograficaart_' + str(articulo_id) + '_' + str(random.randint(1, 10000)) + '.pdf'
                    valida = convert_html_to_pdf(
                        'inv_articulos/fichacatalografica_articulo_pdf.html',
                        {'pagesize': 'A4', 'data': data},
                        nombrearchivoficha,
                        directorio
                    )

                    archivoficha = directorio + "/" + nombrearchivoficha
                    # Agrego el archivo de la ficha a la carpeta del artículo
                    fantasy_zip.write(archivoficha, carpetaarticulo + "/FICHA_CATALOGRAFICA.pdf")
                    # Borro el archivo de la ficha creado
                    ET.sleep(1)
                    os.remove(archivoficha)


                articulos_no_publicados = ArticuloInvestigacion.objects.filter(status=True, fechapublicacion__isnull=True, fechaaprobacion__year=anio).order_by('id')
                # articulos_no_publicados = ArticuloInvestigacion.objects.filter(status=True, fechapublicacion__isnull=True, fechaaprobacion__year=anio).order_by('id')[:10]
                for articulo in articulos_no_publicados:
                    rp += 1
                    print("Procesando", rp, " de ", total)

                    titulo = articulo.nombre

                    palabras = titulo.split(" ")
                    titulo = "_".join(palabras[0:5])
                    titulo = remover_caracteres(titulo, caracteres_a_quitar)

                    titulo = elimina_tildes(remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(titulo)))
                    carpetaarticulo = "ACEPTADOPUBLICACION/ART_" + articulo.revista.codigoissn.strip().replace('-', '_') + "_" + str(articulo.id)+ "_" + titulo

                    articulo_id = articulo.id
                    nombre = "ARTICULO_" + str(articulo_id).zfill(4)

                    # Agrego las evidencias a la carpeta del artículo
                    for evidencia in articulo.detalleevidencias_set.filter(status=True):
                        ext = evidencia.archivo.__str__()[evidencia.archivo.__str__().rfind("."):]

                        if evidencia.descripcion:
                            nombreevidencia = evidencia.descripcion.upper()
                            nombreevidencia = remover_caracteres(nombreevidencia, caracteres_a_quitar)
                            nombreevidencia = elimina_tildes(remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(nombreevidencia))).replace(" ", "_")
                        else:
                            nombreevidencia = "EVIDENCIA" + random.randint(1, 10000).__str__()

                        if evidencia.evidencia.id == 1:
                            if os.path.exists(SITE_STORAGE + evidencia.archivo.url):
                                fantasy_zip.write(SITE_STORAGE + evidencia.archivo.url, carpetaarticulo + "/" + nombreevidencia + ext.lower())
                        elif evidencia.evidencia.id == 3:
                            if os.path.exists(SITE_STORAGE + evidencia.archivo.url):
                                fantasy_zip.write(SITE_STORAGE + evidencia.archivo.url, carpetaarticulo + "/" + nombreevidencia + ext.lower())

                    # Generar la ficha catalográfica del artículo
                    data['participantess'] = participantes = ParticipantesArticulos.objects.filter(articulo=articulo, status=True)
                    data['cantidad'] = participantes.count()
                    data['basesindexadas'] = ArticulosBaseIndexada.objects.filter(articulo=articulo, status=True)

                    nombrearchivoficha = 'fichacatalograficaart_' + str(articulo_id) + '_' + str(random.randint(1, 10000)) + '.pdf'
                    valida = convert_html_to_pdf(
                        'inv_articulos/fichacatalografica_articulo_pdf.html',
                        {'pagesize': 'A4', 'data': data},
                        nombrearchivoficha,
                        directorio
                    )

                    archivoficha = directorio + "/" + nombrearchivoficha
                    # Agrego el archivo de la ficha a la carpeta del artículo
                    fantasy_zip.write(archivoficha, carpetaarticulo + "/FICHA_CATALOGRAFICA.pdf")
                    # Borro el archivo de la ficha creado
                    ET.sleep(1)
                    os.remove(archivoficha)


                fantasy_zip.close()

                ruta = "media/zipav/" + nombre_archivo

                return JsonResponse({'result': 'ok', 'archivo': ruta})
            except Exception as ex:
                msg = ex.__str__()
                return JsonResponse({"result": "bad", "mensaje": u"Error al descargar evidencias. Detalle: %s" % (msg)})

        elif action == 'addorcidpersona':
            try:
                if 'persona_select2' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                idpersona = int(request.POST['persona_select2'])
                urlorcid = request.POST['urlorcid'].strip()
                idorcid = request.POST['idorcid'].strip()
                submissiondate = request.POST['submissiondate'].strip()
                givenname = request.POST['givenname'].strip()
                familyname = request.POST['familyname'].strip()

                if givenname and familyname:
                    completename = givenname + " " + familyname
                else:
                    completename = givenname if givenname else familyname

                # Verifico que el Orcid ID no haya sido asignado a otra persona
                if RedPersona.objects.filter(status=True, tipo__id=1, identificador=idorcid, verificada=True).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El identificador %s ya ha sido asignado a otra persona" % (idorcid), "showSwal": "True", "swalType": "warning"})

                personaorcid = Persona.objects.get(pk=int(idpersona))

                # Creo el registro de la red ORCID
                registroorcid = RedPersona(
                    tipo_id=1,
                    fecha=submissiondate,
                    identificador=idorcid,
                    nombre=completename,
                    persona=personaorcid,
                    enlace=urlorcid,
                    verificada=True
                )
                registroorcid.save(request)

                log(u'%s agregó identificador ORCID para la persona: %s' % (persona, personaorcid), request, "add")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editorcidpersona':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                idpersona = int(request.POST['editpersona_select2'])
                personaorcid = Persona.objects.get(pk=int(idpersona))

                # Verifico que la persona no tenga asignado un Orcid ID
                if RedPersona.objects.filter(status=True, tipo__id=1, persona=personaorcid, verificada=True).exclude(pk=int(encrypt(request.POST['id']))).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La persona ya tiene asignado identificador ORCID", "showSwal": "True", "swalType": "warning"})

                # Consulto el registro ORCID
                registroorcid = RedPersona.objects.get(pk=int(encrypt(request.POST['id'])))

                # Actualizo el registro ORCID
                registroorcid.persona = personaorcid
                registroorcid.save(request)

                log(u'%s editó persona del identificador ORCID: %s' % (persona, registroorcid.str_red_persona()), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addscopuspersona':
            try:
                if 'persona_select2' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                idpersona = int(request.POST['persona_select2'])
                urlscopus = request.POST['urlscopus'].strip()
                idscopus = request.POST['idscopus'].strip()
                submissiondate = None
                profilename = request.POST['profilename'].strip()

                personascopus = Persona.objects.get(pk=int(idpersona))

                # Verifico que la persona no tenga asignado perfil SCOPUS
                if RedPersona.objects.filter(status=True, tipo__id=4, persona=personascopus, verificada=True).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La persona ya tiene asignado un perfil de SCOPUS", "showSwal": "True", "swalType": "warning"})

                # Verifico que el SCOPUS ID no haya sido asignado a otra persona
                if RedPersona.objects.filter(status=True, tipo__id=4, identificador=idscopus, verificada=True).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El identificador %s ya ha sido asignado a otra persona" % (idscopus), "showSwal": "True", "swalType": "warning"})

                # Creo el registro del perfil SCOPUS
                registroscopus = RedPersona(
                    tipo_id=4,
                    fecha=submissiondate,
                    identificador=idscopus,
                    nombre=profilename,
                    persona=personascopus,
                    enlace=urlscopus,
                    ndocumento=0,
                    ncita=0,
                    indiceh=0,
                    verificada=True
                )
                registroscopus.save(request)

                log(u'%s agregó perfil SCOPUS para la persona: %s' % (persona, personascopus), request, "add")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editscopuspersona':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                idpersona = int(request.POST['editpersona_select2'])
                personascopus = Persona.objects.get(pk=int(idpersona))

                urlscopus = request.POST['urlscopus'].strip()
                idscopus = request.POST['idscopus'].strip()
                submissiondate = None
                profilename = request.POST['profilename'].strip()

                # Verifico que la persona no tenga asignado un perfil SCOPUS
                if RedPersona.objects.filter(status=True, tipo__id=4, persona=personascopus, verificada=True).exclude(pk=int(encrypt(request.POST['id']))).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La persona ya tiene asignado un perfil SCOPUS", "showSwal": "True", "swalType": "warning"})

                # Verifico que el SCOPUS ID no haya sido asignado a otra persona
                if RedPersona.objects.filter(status=True, tipo__id=4, identificador=idscopus, verificada=True).exclude(pk=int(encrypt(request.POST['id']))).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El identificador %s ya ha sido asignado a otra persona" % (idscopus), "showSwal": "True", "swalType": "warning"})

                # Consulto el registro SCOPUS
                registroscopus = RedPersona.objects.get(pk=int(encrypt(request.POST['id'])))

                # Actualizo el registro SCOPUS
                registroscopus.persona = personascopus
                registroscopus.fecha = submissiondate
                registroscopus.identificador = idscopus
                registroscopus.nombre = profilename
                registroscopus.enlace = urlscopus
                registroscopus.save(request)

                log(u'%s editó perfil de SCOPUS: %s' % (persona, registroscopus.str_red_persona()), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})



        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'actualizardocumentoindexacion':
                try:
                    revistabase = RevistaInvestigacionBase.objects.get(pk=int(request.GET['idrb']))

                    form = DocumentoIndexacionForm(initial={'revista': revistabase.revista.nombre,
                                                            'baseindexada': revistabase.baseindexada.nombre})

                    data['title'] = u'Actualizar Documento Indexación'
                    data['id'] = int(request.GET['idrb'])
                    if len(request.GET['ts']) > 0:
                        data['search'] = request.GET['ts']

                    if int(request.GET['idr']) > 0:
                        data['idr'] = request.GET['idr']

                    data['form'] = form

                    template = get_template("inv_articulos/actualizadocumentoindexacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'aprobar':
                try:
                    data['title'] = u'Aprobar Solicitud Articulos'
                    data['solicitudes'] = SolicitudPublicacion.objects.get(pk=request.GET['id'])
                    return render(request, "inv_articulos/aprobar.html", data)
                except Exception as ex:
                    pass

            elif action == 'aprobararticulo':
                try:
                    data['title'] = u'Aprobar Artículo'
                    articulo = ArticuloInvestigacion.objects.get(pk=request.GET['idarticulo'])
                    # if articulo.solicitudpublicacion:
                    #     data['solicitud'] = SolicitudPublicacion.objects.get(pk=articulo.solicitudpublicacion.id)
                    data['articulo'] = articulo
                    return render(request, "inv_articulos/aprobararticulo.html", data)
                except Exception as ex:
                    pass

            elif action == 'rechazar':
                try:
                    data['title'] = u'Rechazar Solicitud'
                    data['solicitud'] = SolicitudPublicacion.objects.get(pk=request.GET['id'])
                    return render(request, "inv_articulos/rechazar.html", data)
                except Exception as ex:
                    pass

            elif action == 'add':
                try:
                    data['title'] = u'Adicionar Articulo'
                    form = ArticulosInvestigacionForm()
                    data['form'] = form
                    return render(request, "inv_articulos/add.html", data)
                except Exception as ex:
                    pass

            elif action == 'addarticulo':
                try:
                    data['title'] = u'Adicionar Artículo/Proceeding'
                    form = ArticuloProceedingForm()
                    form2 = RevistaInvestigacionAdminForm()
                    form2.quitar_campo_tipo()

                    data['form'] = form
                    data['form2'] = form2

                    return render(request, "inv_articulos/addarticulo.html", data)
                except Exception as ex:
                    import datetime
                    print(ex)
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    textoerror = '{} Linea:{}'.format(ex, sys.exc_info()[-1].tb_lineno)

                    from datetime import timedelta
                    notificacion = Notificacion(
                        cuerpo="Error formulario agregar artículos",
                        titulo=textoerror,
                        destinatario=persona,
                        prioridad=1,
                        app_label='SGA',
                        fecha_hora_visible=None,
                        tipo=2,
                        en_proceso=False,
                        error=True)
                    notificacion.save(request)

                    # send_user_notification(user=persona.usuario, payload={
                    #     "head": "Error formulario agregar artículos",
                    #     "body": "Error formulario agregar artículos",
                    #     "action": "notificacion",
                    #     "timestamp": time.mktime(datetime.now().timetuple()),
                    #     "btn_notificaciones": traerNotificaciones(request, data, persona),
                    #     "mensaje": "Error al generar <b>{}</b>. Error: {}".format("Error formulario agregar artículos", textoerror),
                    #     "error": True
                    # }, ttl=500)

                    pass

            elif action == 'ingresarsolicitudarticulo':
                try:
                    data['title'] = u'Adicionar Articulo'
                    solicitud = SolicitudPublicacion.objects.get(pk=encrypt(request.GET['id']))

                    revistaborrador = None
                    if solicitud.revista:
                        revistaborrador = solicitud.revista
                    elif solicitud.revistainvestigacion.borrador:
                        revistaborrador = solicitud.revistainvestigacion

                    form = ArticulosInvestigacion3Form(initial={'nombre': solicitud.nombre,
                                                             'resumen': solicitud.motivo,
                                                             'fecharecepcion': solicitud.fecharecepcion,
                                                             'fechaaprobacion': solicitud.fechaaprobacion,
                                                             'fechapublicacion': solicitud.fechapublicacion,
                                                             'volumen': solicitud.volumen,
                                                             'numero': solicitud.numero,
                                                             'paginas': solicitud.paginas,
                                                             'areaconocimiento': solicitud.areaconocimiento,
                                                             'subareaconocimiento': solicitud.subareaconocimiento,
                                                             'subareaespecificaconocimiento': solicitud.subareaespecificaconocimiento,
                                                             'evento': solicitud.evento,
                                                             'enlace': solicitud.enlace,
                                                             'revista': revistaborrador,
                                                             # 'revista2': solicitud.revistainvestigacion if not solicitud.revistainvestigacion.borrador else None,
                                                             'revista2': solicitud.revistainvestigacion if not revistaborrador else None,
                                                             'provieneproyecto': solicitud.provieneproyecto,
                                                             'lineainvestigacion': solicitud.lineainvestigacion,
                                                             'sublineainvestigacion': solicitud.sublineainvestigacion,
                                                             'base': solicitud.base,
                                                             'estadopublicacion': solicitud.estadopublicacion,
                                                             'tipoproyecto': solicitud.tipoproyecto,
                                                             'proyectointerno': solicitud.proyectointerno,
                                                             'proyectoexterno': solicitud.proyectoexterno,
                                                             'pertenecegrupoinv': solicitud.pertenecegrupoinv,
                                                             'grupoinvestigacion': solicitud.grupoinvestigacion
                                                             })
                    form.editar(solicitud)

                    revistaborradorid = None
                    if not revistaborrador:
                        form2 = RevistaInvestigacionAdminForm()
                    else:
                        basesindexadas = None
                        if not solicitud.revista:
                            basesindexadas = BaseIndexadaInvestigacion.objects.filter(revistainvestigacionbase__revista=revistaborrador, revistainvestigacionbase__status=True).order_by('nombre')
                            revistaborradorid = revistaborrador.id

                        form2 = RevistaInvestigacionAdminForm(initial={
                                                                'codigoissn': revistaborrador.codigoissn if not solicitud.revista else '',
                                                                'nombrerevista': revistaborrador.nombre if not solicitud.revista else revistaborrador,
                                                                'institucion': revistaborrador.institucion if not solicitud.revista else '',
                                                                'enlacerevista': revistaborrador.enlace if not solicitud.revista else '',
                                                                'baseindexada': basesindexadas,
                                                                'cuartil': revistaborrador.cuartil if not solicitud.revista else '',
                                                                'sjr': revistaborrador.sjr if not solicitud.revista else '',
                                                                'jcr': revistaborrador.jcr if not solicitud.revista else '',
                                                                'tipo': revistaborrador.tipo if not solicitud.revista else ''
                        })

                    form2.quitar_campo_tipo()

                    data['idsolicitud'] = solicitud.id
                    data['tiposolicitud'] = solicitud.tiposolicitud
                    data['congresoid'] = solicitud.revistainvestigacion.id if solicitud.revistainvestigacion else 0
                    data['revistaborradorid'] = revistaborradorid
                    data['form'] = form
                    data['form2'] = form2
                    data['evidencias'] = solicitud.evidencias()
                    data['participantes'] = solicitud.participantes()
                    data['estadossolicitud'] = obtener_estados_solicitud(8, [2, 3, 4])
                    return render(request, "inv_articulos/ingresarsolicitudarticulo.html", data)
                except Exception as ex:
                    pass

            elif action == 'addrevista':
                try:
                    data['title'] = u'Adicionar Revista'
                    form = RevistaInvestigacionAdminForm()
                    data['form'] = form
                    return render(request, "inv_articulos/addrevista.html", data)
                except Exception as ex:
                    pass

            elif action == 'addbase':
                try:
                    data['title'] = u'Adicionar Bases Indexadas'
                    form = BaseIndexadaInvestigacionForm()
                    data['form'] = form
                    return render(request, "inv_articulos/addbase.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadorevistas':
                try:
                    data['title'] = u'Listado de Revistas'
                    search = None
                    ids = None

                    basesindexadas = BaseIndexadaInvestigacion.objects.filter(revistainvestigacionbase__status=True).distinct().order_by('nombre')

                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        revistas = RevistaInvestigacion.objects.select_related().filter(Q(nombre__icontains=search)|Q(institucion__icontains=search), status=True, borrador=False).order_by('nombre')
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        revistas = RevistaInvestigacion.objects.select_related().filter(id=ids, status=True, borrador=False).order_by('nombre')
                    else:
                        revistas = RevistaInvestigacion.objects.select_related().filter(status=True, borrador=False).order_by('nombre')

                    idbaseindexada = tiporegistro = 0

                    if 'tiporegistro' in request.GET:
                        tiporegistro = int(request.GET['tiporegistro'])
                        if tiporegistro > 0:
                            revistas = revistas.filter(tiporegistro=tiporegistro)

                    if 'idbaseindexada' in request.GET:
                        idbaseindexada = int(request.GET['idbaseindexada'])
                        if idbaseindexada > 0:
                            revistas = revistas.filter(revistainvestigacionbase__status=True, revistainvestigacionbase__baseindexada__id=idbaseindexada)

                    paging = MiPaginador(revistas, 25)
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
                    data['revistas'] = page.object_list
                    data['basesindexadas'] = basesindexadas
                    data['idbaseindexada'] = idbaseindexada
                    data['tiporegistro'] = tiporegistro
                    return render(request, "inv_articulos/listarevistas.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadobases':
                try:
                    data['title'] = u'Listado de Bases Indexadas'
                    search = None
                    ids = None
                    inscripcionid = None
                    data['bases'] = BaseIndexadaInvestigacion.objects.select_related().filter(status=True).order_by('nombre')
                    return render(request, "inv_articulos/listabases.html", data)
                except Exception as ex:
                    pass

            elif action == 'editarticulo':
                try:
                    data['title'] = u'Editar Artículo'
                    data['articulo'] = articulo = ArticuloInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))

                    form = ArticulosInvestigacion3Form(initial={'nombre': articulo.nombre,
                                                                'resumen': articulo.resumen,
                                                                'revista2': articulo.revista,
                                                                'estadopublicacion': articulo.estado,
                                                                'fecharecepcion': articulo.fecharecepcion,
                                                                'fechaaprobacion': articulo.fechaaprobacion,
                                                                'fechapublicacion': articulo.fechapublicacion,
                                                                'enlace': articulo.enlace,
                                                                'numero': articulo.numero,
                                                                'volumen': articulo.volumen,
                                                                'paginas': articulo.paginas,
                                                                'areaconocimiento': articulo.areaconocimiento,
                                                                'subareaconocimiento': articulo.subareaconocimiento,
                                                                'subareaespecificaconocimiento': articulo.subareaespecificaconocimiento,
                                                                'lineainvestigacion': articulo.lineainvestigacion,
                                                                'sublineainvestigacion': articulo.sublineainvestigacion,
                                                                'provieneproyecto': articulo.provieneproyecto,
                                                                'tipoproyecto': articulo.tipoproyecto,
                                                                'proyectointerno': articulo.proyectointerno,
                                                                'proyectoexterno': articulo.proyectoexterno,
                                                                'pertenecegrupoinv': articulo.pertenecegrupoinv,
                                                                'grupoinvestigacion': articulo.grupoinvestigacion,
                                                                'doi': articulo.doy,
                                                                'revistaindexada': articulo.indexada,
                                                                'accesoabierto': articulo.accesoabierto,
                                                                'cuartilarticulo': articulo.cuartil,
                                                                'sjrarticulo': articulo.sjr,
                                                                'jcrarticulo': articulo.jcr,
                                                                'categoriaconfirmada': 1 if articulo.categoriaconfirmada else 2,
                                                                'categoriaarticulo': articulo.get_categoria_display(),
                                                                'observacion': articulo.observacion
                    })

                    form.editar(articulo)

                    form2 = RevistaInvestigacionAdminForm()
                    form2.quitar_campo_tipo()

                    # data['idsolicitud'] = solicitud.id
                    data['tiposolicitud'] = articulo.tipoarticulo
                    data['congresoid'] = articulo.revista.id if articulo.revista else 0
                    data['form'] = form
                    data['form2'] = form2
                    # data['mostrarguardar'] = False if articulo.aprobado else True
                    data['mostrarguardar'] = True

                    return render(request, "inv_articulos/editarticulo.html", data)
                except Exception as ex:
                    pass

            elif action == 'editrevista':
                try:
                    data['title'] = u'Editar Revista'
                    data['revista'] = revista = RevistaInvestigacion.objects.get(pk=request.GET['id'])
                    basesindexadas = BaseIndexadaInvestigacion.objects.filter(revistainvestigacionbase__revista=revista, revistainvestigacionbase__status=True).order_by('nombre')
                    form = RevistaInvestigacionAdminForm(initial={'nombrerevista': revista.nombre,
                                                             'codigoissn': revista.codigoissn,
                                                             'institucion': revista.institucion,
                                                             'tipo': revista.tipo,
                                                             'enlacerevista': revista.enlace,
                                                             'cuartil': revista.cuartil,
                                                             'sjr': revista.sjr,
                                                             'jcr': revista.jcr,
                                                             'baseindexada': basesindexadas})
                    data['form'] = form
                    return render(request, "inv_articulos/editrevista.html", data)
                except Exception as ex:
                    pass

            elif action == 'editrevistaarticulo':
                try:
                    data['title'] = u'Editar Revista' if int(request.GET['tiporegistro']) == 1 else 'Editar Congreso'
                    data['revista'] = revista = RevistaInvestigacion.objects.get(pk=request.GET['id'])
                    basesindexadas = BaseIndexadaInvestigacion.objects.filter(revistainvestigacionbase__revista=revista, revistainvestigacionbase__status=True).order_by('nombre')

                    if basesindexadas:
                        if len(basesindexadas) > 3: basesindexadas = basesindexadas[:3]

                    form = RevistaInvestigacionEditAdminForm(initial={'nombrerevista2': revista.nombre,
                                                             'codigoissn2': revista.codigoissn,
                                                             'institucion2': revista.institucion,
                                                             'tipo2': revista.tipo,
                                                             'enlacerevista2': revista.enlace,
                                                             'cuartil2': revista.cuartil,
                                                             'sjr2': revista.sjr,
                                                             'jcr2': revista.jcr,
                                                             'baseindexada2': basesindexadas})
                    data['form'] = form

                    template = get_template("inv_articulos/editrevistaarticulo.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'editbase':
                try:
                    data['title'] = u'Editar Base Indexadas'
                    data['base'] = baseindex = BaseIndexadaInvestigacion.objects.get(pk=request.GET['id'])
                    form = BaseIndexadaInvestigacionForm(initial={'nombre': baseindex.nombre,
                                                                  'categoria': baseindex.categoria})
                    data['form'] = form
                    return render(request, "inv_articulos/editbase.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleteparticipantearticulo':
                try:
                    data['title'] = u'Eliminar Participante'
                    tipo = request.GET['tipo']
                    data['participante'] = participante = ParticipantesArticulos.objects.get(pk=request.GET['id'])
                    if tipo == '1':
                        data['nombres'] = participante.profesor.persona.nombre_completo()
                    if tipo == '3':
                        data['nombres'] = participante.administrativo.persona.nombre_completo()
                    if tipo == '4':
                        data['nombres'] = participante.inscripcion.persona.nombre_completo()
                    return render(request, "inv_articulos/deleteparticipantearticulo.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletearticulo':
                try:
                    data['title'] = u'Eliminar Articulo'
                    data['articulo'] = ArticuloInvestigacion.objects.get(pk=int(encrypt(request.GET['idarticulo'])))
                    return render(request, "inv_articulos/deletearticulo.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletebasesarticulos':
                try:
                    data['title'] = u'Eliminar Base indexada de artículo'
                    data['baseindex'] = ArticulosBaseIndexada.objects.get(pk=request.GET['id'])
                    return render(request, "inv_articulos/deletebaseindexarticulo.html", data)
                except Exception as ex:
                    pass

            elif action == 'addparticipantesdocentes':
                try:
                    data['title'] = u'Participante Docente'
                    data['form'] = ParticipanteProfesorArticuloForm
                    data['id'] = request.GET['idarticulo']
                    return render(request, "inv_articulos/addparticipantedocente.html", data)
                except Exception as ex:
                    pass

            elif action == 'addparticipantesadministrativos':
                try:
                    data['title'] = u'Participante Administrativo'
                    data['form'] = ParticipanteAdministrativoArticuloForm
                    data['id'] = request.GET['idarticulo']
                    return render(request, "inv_articulos/addparticipanteadministrativo.html", data)
                except Exception as ex:
                    pass

            elif action == 'addparticipantesinscripcion':
                try:
                    data['title'] = u'Participante Estudiante'
                    data['form'] = ParticipanteInscripcionArticuloForm
                    data['id'] = request.GET['idarticulo']
                    return render(request, "inv_articulos/addparticipanteinscripcion.html", data)
                except Exception as ex:
                    pass

            elif action == 'participantesarticulos':
                try:
                    data['title'] = u'Participantes de Articulos'
                    data['articulo'] = articulo = ArticuloInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['tipoparinstitucion'] = TIPO_PARTICIPANTE_INSTITUCION
                    data['tipoautor'] = TIPO_PARTICIPANTE
                    data['participantes'] = ParticipantesArticulos.objects.filter(status=True, matrizevidencia_id=3, articulo=articulo)
                    return render(request, "inv_articulos/participantesarticulos.html", data)
                except Exception as ex:
                    pass

            elif action == 'basesindexadas':
                try:
                    data['title'] = u'Bases Indexadas de Articulos'
                    data['articulo'] = articulo = ArticuloInvestigacion.objects.get(pk=request.GET['id'])
                    data['form_baseindexada'] = BaseIndexadaInvestigacionListaForm()
                    data['basesindexadas'] = ArticulosBaseIndexada.objects.filter(status=True, articulo=articulo)
                    return render(request, "inv_articulos/basesindexadasarticulos.html", data)
                except Exception as ex:
                    pass

            elif action == 'evidenciasarticulos':
                try:
                    data['title'] = u'Evidencia Articulos'
                    data['articulo'] = articulo = ArticuloInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['evidencias'] = Evidencia.objects.filter(status=True, matrizevidencia_id=3, pk__in=[1, 3, 26, 30])
                    data['formevidencias'] = EvidenciaForm()
                    return render(request, "inv_articulos/evidenciasarticulos.html", data)
                except Exception as ex:
                    pass

            elif action == 'addevidenciasarticulos':
                try:
                    evidencia = Evidencia.objects.get(pk=int(encrypt(request.GET['idevidencia'])))
                    if DetalleEvidencias.objects.filter(evidencia_id=int(encrypt(request.GET['idevidencia'])), articulo_id=int(encrypt(request.GET['id']))).exists():
                        detalleevidencia = DetalleEvidencias.objects.get(evidencia_id=int(encrypt(request.GET['idevidencia'])), articulo_id=int(encrypt(request.GET['id'])))
                        form = EvidenciaForm(initial={'descripcion': detalleevidencia.descripcion})
                    else:
                        form = EvidenciaForm(initial={'descripcion': evidencia.nombre.upper()})

                    data['title'] = u'Editar Evidencia'
                    data['evidencia'] = evidencia.nombre.upper()
                    data['form'] = form
                    data['id'] = request.GET['id']
                    data['idevidencia'] = request.GET['idevidencia']
                    template = get_template("inv_articulos/add_evidenciasarticulos.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'reporte_articulos_excel':
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
                    ws = wb.add_sheet('Listado')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=lista_articulos_' + random.randint(1, 10000).__str__() + '.xls'

                    ws.write_merge(0, 0, 0, 35, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                    ws.write_merge(1, 1, 0, 35, 'VICERRECTORADO DE INVESTIGACIÓN Y POSGRADO', titulo2)
                    ws.write_merge(2, 2, 0, 35, 'COORDINACIÓN DE INVESTIGACIÓN', titulo2)
                    ws.write_merge(3, 3, 0, 35, 'LISTADO DE ARTÍCULOS', titulo2)

                    row_num = 5
                    columns = [
                        (u"TIPO DE ARTÍCULOS", 2500),
                        (u"CÓDIGO", 4500),
                        (u"ARTÍCULO", 10000),
                        (u"VOL.", 2000),
                        (u"NUM.", 2000),
                        (u"PAG.", 2000),
                        (u"CÓDIGO ISSN", 2000),
                        (u"BASE INDEXADA", 2000),
                        (u"NOMBRE BASE INDEXADA", 10000),
                        (u"REVISTA", 10000),
                        (u"TIPO", 10000),
                        (u"SJR", 2000),
                        (u"FECHA PUBLICACIÓN", 3000),
                        (u"ÁREA DE CONOCIMIENTO", 10000),
                        (u"SUB-ÁREA DE CONOCIMIENTO", 10000),
                        (u"SUB-ÁREA ESPECÍFICA", 10000),
                        (u"LÍNEA INVESTIGACIÓN", 10000),
                        (u"SUB-LÍNEA INVESTIGACIÓN", 10000),
                        (u"PROVIENE DE PROYECTO", 3000),
                        (u"TIPO PROYECTO", 3000),
                        (u"TÍTULO DEL PROYECTO", 10000),
                        (u"PERTENECE GRUPO INVESTIGACIÓN", 3000),
                        (u"GRUPO DE INVESTIGACIÓN", 10000),
                        (u"ESTADO", 3000),
                        (u"CÉDULA", 3000),
                        (u"TIPO PARTICIPANTE", 3000),
                        (u"PARTICIPANTE", 15000),
                        (u"TIPO PARTICIPACION", 4000),
                        (u"TIPO UNEMI", 4000),
                        (u"DOI", 6000),
                        (u"CUARTIL", 3000),
                        (u"JCR", 3000),
                        (u"SJR", 3000),
                        (u"CATEGORÍA", 6000),
                        (u"ENLACE ARTÍCULO", 15000),
                        (u"ENLACE REVISTA", 15000)
                    ]

                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]

                    listaarticulos = ParticipantesArticulos.objects.filter(status=True).order_by('articulo__nombre')

                    for articulos in listaarticulos:
                        row_num += 1

                        listabasesindexadas = ','.join([x.baseindexada.nombre for x in ArticulosBaseIndexada.objects.filter(articulo=articulos.articulo.id, status=True)])

                        if articulos.profesor:
                            nombres = articulos.profesor.persona.nombre_completo_inverso()
                            tipoparticipante = articulos.get_tipoparticipanteins_display()
                            cedula = articulos.profesor.persona.cedula
                        elif articulos.administrativo:
                            nombres = articulos.administrativo.persona.nombre_completo_inverso()
                            tipoparticipante = articulos.get_tipoparticipanteins_display()
                            cedula = articulos.administrativo.persona.cedula
                        elif articulos.inscripcion:
                            nombres = articulos.inscripcion.persona.nombre_completo_inverso()
                            tipoparticipante = articulos.get_tipoparticipanteins_display()
                            cedula = articulos.inscripcion.persona.cedula

                        ws.write(row_num, 0, "REVISTA", fuentenormal)
                        ws.write(row_num, 1, articulos.articulo.revista.codigoissn + ' ' + str(articulos.articulo.id) + '-ART', fuentenormal)
                        ws.write(row_num, 2, articulos.articulo.nombre.strip() , fuentenormal)
                        ws.write(row_num, 3, articulos.articulo.volumen, fuentenormal)
                        ws.write(row_num, 4, articulos.articulo.numero, fuentenormal)
                        ws.write(row_num, 5, articulos.articulo.paginas, fuentenormal)
                        ws.write(row_num, 6, articulos.articulo.revista.codigoissn, fuentenormal)
                        ws.write(row_num, 7, "SI" if articulos.articulo.indexada else "NO", fuentenormal)
                        ws.write(row_num, 8, listabasesindexadas, fuentenormal)
                        ws.write(row_num, 9, articulos.articulo.revista.nombre.strip(), fuentenormal)
                        ws.write(row_num, 10, articulos.articulo.revista.get_tipo_display(), fuentenormal)
                        ws.write(row_num, 11, articulos.articulo.revista.sjr, fuentenormal)
                        ws.write(row_num, 12, articulos.articulo.fechapublicacion, fuentefecha)
                        ws.write(row_num, 13, articulos.articulo.areaconocimiento.nombre, fuentenormal)
                        ws.write(row_num, 14, articulos.articulo.subareaconocimiento.nombre, fuentenormal)
                        ws.write(row_num, 15, articulos.articulo.subareaespecificaconocimiento.nombre, fuentenormal)
                        ws.write(row_num, 16, articulos.articulo.lineainvestigacion.nombre if articulos.articulo.lineainvestigacion else '', fuentenormal)
                        ws.write(row_num, 17, articulos.articulo.sublineainvestigacion.nombre if articulos.articulo.sublineainvestigacion else '', fuentenormal)
                        ws.write(row_num, 18, 'SI' if articulos.articulo.tipoproyecto else 'NO', fuentenormal)
                        ws.write(row_num, 19, articulos.articulo.get_tipoproyecto_display() if articulos.articulo.tipoproyecto else '', fuentenormal)
                        if articulos.articulo.tipoproyecto:
                            ws.write(row_num, 20, articulos.articulo.proyectointerno.nombre if articulos.articulo.proyectointerno else articulos.articulo.proyectoexterno.nombre, fuentenormal)
                        else:
                            ws.write(row_num, 20, '', fuentenormal)

                        ws.write(row_num, 21, 'SI' if articulos.articulo.pertenecegrupoinv else 'NO', fuentenormal)
                        ws.write(row_num, 22, articulos.articulo.grupoinvestigacion.nombre if articulos.articulo.pertenecegrupoinv else '', fuentenormal)
                        ws.write(row_num, 23, articulos.articulo.get_estado_display(), fuentenormal)
                        ws.write(row_num, 24, cedula, fuentenormal)
                        ws.write(row_num, 25, articulos.get_tipo_display(), fuentenormal)
                        ws.write(row_num, 26, nombres, fuentenormal)
                        ws.write(row_num, 27, tipoparticipante, fuentenormal)
                        ws.write(row_num, 28, articulos.tipo_unemi(), fuentenormal)
                        ws.write(row_num, 29, articulos.articulo.doy, fuentenormal)
                        ws.write(row_num, 30, articulos.articulo.get_cuartil_display(), fuentenormal)
                        ws.write(row_num, 31, articulos.articulo.jcr, fuentenormal)
                        ws.write(row_num, 32, articulos.articulo.sjr, fuentenormal)
                        ws.write(row_num, 33, articulos.articulo.get_categoria_display(), fuentenormal)
                        ws.write(row_num, 34, articulos.articulo.enlace, fuentenormal)
                        ws.write(row_num, 35, articulos.articulo.revista.enlace, fuentenormal)

                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'reporte_articulos_excel_participante':
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
                    ws = wb.add_sheet('Listado')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=lista_articulos_participante_' + random.randint(1, 10000).__str__() + '.xls'

                    ws.write_merge(0, 0, 0, 35, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                    ws.write_merge(1, 1, 0, 35, 'DIRECCIÓN DE INVESTIGACIÓN Y POSGRADO', titulo2)
                    ws.write_merge(2, 2, 0, 35, 'COORDINACIÓN DE INVESTIGACIÓN', titulo2)
                    ws.write_merge(3, 3, 0, 35, 'LISTADO DE ARTÍCULOS POR PARTICIPANTE', titulo2)

                    row_num = 5

                    columns = [
                        (u"TIPO DE ARTÍCULOS", 2500),
                        (u"CÓDIGO", 4500),
                        (u"ARTÍCULO", 10000),
                        (u"VOL.", 2000),
                        (u"NUM.", 2000),
                        (u"PAG.", 2000),
                        (u"CÓDIGO ISSN", 2000),
                        (u"BASE INDEXADA", 2000),
                        (u"NOMBRE BASE INDEXADA", 10000),
                        (u"REVISTA", 10000),
                        (u"TIPO", 10000),
                        (u"SJR", 2000),
                        (u"FECHA PUBLICACIÓN", 3000),
                        (u"ÁREA DE CONOCIMIENTO", 10000),
                        (u"SUB-ÁREA DE CONOCIMIENTO", 10000),
                        (u"SUB-ÁREA ESPECÍFICA", 10000),
                        (u"LÍNEA INVESTIGACIÓN", 10000),
                        (u"SUB-LÍNEA INVESTIGACIÓN", 10000),
                        (u"PROVIENE DE PROYECTO", 3000),
                        (u"TIPO PROYECTO", 3000),
                        (u"TÍTULO DEL PROYECTO", 10000),
                        (u"PERTENECE GRUPO INVESTIGACIÓN", 3000),
                        (u"GRUPO DE INVESTIGACIÓN", 10000),
                        (u"ESTADO", 3000),
                        (u"CÉDULA", 3000),
                        (u"TIPO PARTICIPANTE", 3000),
                        (u"PARTICIPANTE", 15000),
                        (u"TIPO PARTICIPACION", 4000),
                        (u"TIPO UNEMI", 4000),
                        (u"DOI", 6000),
                        (u"CUARTIL", 3000),
                        (u"JCR", 3000),
                        (u"SJR", 3000),
                        (u"CATEGORÍA", 6000),
                        (u"ENLACE ARTÍCULO", 15000),
                        (u"ENLACE REVISTA", 15000)
                    ]

                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]

                    lista_ids_personas = request.GET['idsp'].split(",")

                    listaarticulos = ParticipantesArticulos.objects.filter( Q(profesor__persona__id__in=lista_ids_personas)|
                                                                            Q(administrativo__persona__id__in=lista_ids_personas)|
                                                                            Q(inscripcion__persona__id__in=lista_ids_personas), status=True).order_by('articulo__nombre')

                    for articulos in listaarticulos:
                        row_num += 1

                        listabasesindexadas = ','.join([x.baseindexada.nombre for x in ArticulosBaseIndexada.objects.filter(articulo=articulos.articulo.id, status=True)])


                        if articulos.profesor:
                            nombres = articulos.profesor.persona.nombre_completo_inverso()
                            tipoparticipante = articulos.get_tipoparticipanteins_display()
                            cedula = articulos.profesor.persona.cedula
                        elif articulos.administrativo:
                            nombres = articulos.administrativo.persona.nombre_completo_inverso()
                            tipoparticipante = articulos.get_tipoparticipanteins_display()
                            cedula = articulos.administrativo.persona.cedula
                        elif articulos.inscripcion:
                            nombres = articulos.inscripcion.persona.nombre_completo_inverso()
                            tipoparticipante = articulos.get_tipoparticipanteins_display()
                            cedula = articulos.inscripcion.persona.cedula

                        ws.write(row_num, 0, "REVISTA", fuentenormal)
                        ws.write(row_num, 1, articulos.articulo.revista.codigoissn + ' ' + str(articulos.articulo.id) + '-ART', fuentenormal)
                        ws.write(row_num, 2, articulos.articulo.nombre.strip(), fuentenormal)
                        ws.write(row_num, 3, articulos.articulo.volumen, fuentenormal)
                        ws.write(row_num, 4, articulos.articulo.numero, fuentenormal)
                        ws.write(row_num, 5, articulos.articulo.paginas, fuentenormal)
                        ws.write(row_num, 6, articulos.articulo.revista.codigoissn, fuentenormal)
                        ws.write(row_num, 7, "SI" if articulos.articulo.indexada else "NO", fuentenormal)
                        ws.write(row_num, 8, listabasesindexadas, fuentenormal)
                        ws.write(row_num, 9, articulos.articulo.revista.nombre.strip(), fuentenormal)
                        ws.write(row_num, 10, articulos.articulo.revista.get_tipo_display(), fuentenormal)
                        ws.write(row_num, 11, articulos.articulo.revista.sjr, fuentenormal)
                        ws.write(row_num, 12, articulos.articulo.fechapublicacion, fuentefecha)
                        ws.write(row_num, 13, articulos.articulo.areaconocimiento.nombre, fuentenormal)
                        ws.write(row_num, 14, articulos.articulo.subareaconocimiento.nombre, fuentenormal)
                        ws.write(row_num, 15, articulos.articulo.subareaespecificaconocimiento.nombre, fuentenormal)
                        ws.write(row_num, 16, articulos.articulo.lineainvestigacion.nombre if articulos.articulo.lineainvestigacion else '', fuentenormal)
                        ws.write(row_num, 17, articulos.articulo.sublineainvestigacion.nombre if articulos.articulo.sublineainvestigacion else '', fuentenormal)
                        ws.write(row_num, 18, 'SI' if articulos.articulo.tipoproyecto else 'NO', fuentenormal)
                        ws.write(row_num, 19, articulos.articulo.get_tipoproyecto_display() if articulos.articulo.tipoproyecto else '', fuentenormal)
                        if articulos.articulo.tipoproyecto:
                            ws.write(row_num, 20, articulos.articulo.proyectointerno.nombre if articulos.articulo.proyectointerno else articulos.articulo.proyectoexterno.nombre, fuentenormal)
                        else:
                            ws.write(row_num, 20, '', fuentenormal)

                        ws.write(row_num, 21, 'SI' if articulos.articulo.pertenecegrupoinv else 'NO', fuentenormal)
                        ws.write(row_num, 22, articulos.articulo.grupoinvestigacion.nombre if articulos.articulo.pertenecegrupoinv else '', fuentenormal)
                        ws.write(row_num, 23, articulos.articulo.get_estado_display(), fuentenormal)
                        ws.write(row_num, 24, cedula, fuentenormal)
                        ws.write(row_num, 25, articulos.get_tipo_display(), fuentenormal)
                        ws.write(row_num, 26, nombres, fuentenormal)
                        ws.write(row_num, 27, tipoparticipante, fuentenormal)
                        ws.write(row_num, 28, articulos.tipo_unemi(), fuentenormal)
                        ws.write(row_num, 29, articulos.articulo.doy, fuentenormal)
                        ws.write(row_num, 30, articulos.articulo.get_cuartil_display(), fuentenormal)
                        ws.write(row_num, 31, articulos.articulo.jcr, fuentenormal)
                        ws.write(row_num, 32, articulos.articulo.sjr, fuentenormal)
                        ws.write(row_num, 33, articulos.articulo.get_categoria_display(), fuentenormal)
                        ws.write(row_num, 34, articulos.articulo.enlace, fuentenormal)
                        ws.write(row_num, 35, articulos.articulo.revista.enlace, fuentenormal)

                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'excelarticulos':
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
                    response[
                        'Content-Disposition'] = 'attachment; filename=Listas_Articulos' + random.randint(
                        1, 10000).__str__() + '.xls'

                    columns = [
                        (u"TIPO DE ARTICULOS", 2500),
                        (u"CODIGO", 4500),
                        (u"ARTICULO", 10000),
                        (u"VOL.", 2000),
                        (u"NUM.", 2000),
                        (u"PAG.", 2000),
                        (u"CODIGO ISSN", 2000),
                        (u"BASE INDEXADA", 2000),
                        (u"NOMBRE BASE INDEXADA", 10000),
                        (u"REVISTA", 10000),
                        (u"TIPO", 10000),
                        (u"SJR", 2000),
                        (u"FECHA PUBLICACION", 3000),
                        (u"AREA DE CONOCIMIENTO", 10000),
                        (u"SUBAREA DE CONOCIMIENTO", 10000),
                        (u"SUBAREA ESPECIFICA", 10000),
                        (u"ESTADO", 3000),
                        (u"CEDULA", 3000),
                        (u"TIPO PARTICIPANTE", 3000),
                        (u"PARTICIPANTE", 15000),
                        (u"TIPO PARTICIPACION", 4000),
                        (u"TIPO UNEMI", 4000),
                        (u"CUARTIL", 3000),
                        (u"JCR", 3000),
                        (u"SJR", 3000),
                        (u"CATEGORÍA", 6000),
                        (u"ENLACE ARTÍCULO", 15000),
                        (u"ENLACE REVISTA", 15000)
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    listaarticulos = ParticipantesArticulos.objects.filter(status=True).order_by('articulo__nombre')
                    row_num = 4
                    for articulos in listaarticulos:
                        listabesesindex = ""
                        if ArticulosBaseIndexada.objects.filter(articulo=articulos.articulo.id, status=True).exists():
                            listabases = ArticulosBaseIndexada.objects.filter(articulo=articulos.articulo.id, status=True)
                            for bases in listabases:
                                listabesesindex=listabesesindex+bases.baseindexada.nombre+','
                        i = 0
                        campo8 = None
                        campo1 = articulos.articulo.id
                        campo2 = articulos.articulo.nombre
                        campo4 = articulos.articulo.revista.nombre
                        campo5 = articulos.articulo.areaconocimiento.nombre
                        campo6 = articulos.articulo.subareaconocimiento.nombre
                        campo7 = articulos.articulo.subareaespecificaconocimiento.nombre
                        if articulos.profesor:
                            campo8 = articulos.profesor.persona.nombre_completo_inverso()
                            campo9 = articulos.get_tipoparticipanteins_display()
                            campo10 = articulos.profesor.persona.cedula
                        if articulos.administrativo:
                            campo8 = articulos.administrativo.persona.nombre_completo_inverso()
                            campo9 = articulos.get_tipoparticipanteins_display()
                            campo10 = articulos.administrativo.persona.cedula
                        if articulos.inscripcion:
                            campo8 = articulos.inscripcion.persona.nombre_completo_inverso()
                            campo9 = articulos.get_tipoparticipanteins_display()
                            campo10 = articulos.inscripcion.persona.cedula

                        if articulos.articulo.indexada:
                            campo3 = 'SI'
                        else:
                            campo3 = 'NO'
                        campo11 = articulos.articulo.jcr
                        campo12 = articulos.articulo.sjr

                        ws.write(row_num, 0, 'REVISTA', font_style2)
                        ws.write(row_num, 1, articulos.articulo.revista.codigoissn + ' ' + str(articulos.articulo.id) + '-ART', font_style2)
                        ws.write(row_num, 2, campo2, font_style2)
                        ws.write(row_num, 3, articulos.articulo.volumen, font_style2)
                        ws.write(row_num, 4, articulos.articulo.numero, font_style2)
                        ws.write(row_num, 5, articulos.articulo.paginas, font_style2)
                        ws.write(row_num, 6, articulos.articulo.revista.codigoissn, font_style2)
                        ws.write(row_num, 7, campo3, font_style2)
                        ws.write(row_num, 8, listabesesindex, font_style2)
                        ws.write(row_num, 9, campo4, font_style2)
                        ws.write(row_num, 10, articulos.articulo.revista.get_tipo_display(), font_style2)
                        ws.write(row_num, 11, articulos.articulo.revista.sjr, font_style2)
                        ws.write(row_num, 12, articulos.articulo.fechapublicacion, date_format)
                        ws.write(row_num, 13, campo5, font_style2)
                        ws.write(row_num, 14, campo6, font_style2)
                        ws.write(row_num, 15, campo7, font_style2)
                        ws.write(row_num, 16, articulos.articulo.get_estado_display(), font_style2)
                        ws.write(row_num, 17, campo10, font_style2)
                        ws.write(row_num, 18, articulos.get_tipo_display(), font_style2)
                        ws.write(row_num, 19, campo8, font_style2)
                        ws.write(row_num, 20, campo9, font_style2)
                        ws.write(row_num, 21, articulos.tipo_unemi(), font_style2)


                        ws.write(row_num, 22, articulos.articulo.get_cuartil_display() , font_style2)
                        ws.write(row_num, 23, campo11, font_style2)
                        ws.write(row_num, 24, campo12, font_style2)
                        ws.write(row_num, 25, articulos.articulo.get_categoria_display(), font_style2)
                        ws.write(row_num, 26, articulos.articulo.enlace, font_style2)
                        ws.write(row_num, 27, articulos.articulo.revista.enlace, font_style2)

                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'excelrevistas':
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
                    ws.write_merge(0, 0, 0, 7, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=Listas_Revistas' + random.randint(1, 10000).__str__() + '.xls'

                    columns = [
                        (u"TIPO", 2500),
                        (u"ISSN", 5000),
                        (u"NOMBRE", 10000),
                        (u"INSTITUCIÓN", 10000),
                        (u"LINK", 6000),
                        (u"BASE INDEXADA", 8000),
                        (u"CATEGORÍA", 10000),# ES LA CATEGORIA DE LA BASE
                        (u"CUARTIL", 3000)
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'

                    revistas = RevistaInvestigacion.objects.filter(status=True, borrador=False).order_by('nombre')

                    row_num = 4
                    for revista in revistas:
                        listabases = ", ".join([base.baseindexada.nombre for base in revista.basesindexadas()])
                        listacategorias = ", ".join([categoria.nombre for categoria in revista.categoriasbasesindexadas()])

                        ws.write(row_num, 0, revista.get_tiporegistro_display(), font_style2)
                        ws.write(row_num, 1, revista.codigoissn, font_style2)
                        ws.write(row_num, 2, revista.nombre, font_style2)
                        ws.write(row_num, 3, revista.institucion, font_style2)
                        ws.write(row_num, 4, revista.enlace, font_style2)
                        ws.write(row_num, 5, listabases, font_style2)
                        ws.write(row_num, 6, listacategorias, font_style2)
                        ws.write(row_num, 7, revista.get_cuartil_display(), font_style2)

                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'perfilesorcid':
                try:
                    search, url_vars = request.GET.get('s', ''), '&action=' + action
                    filtro = Q(status=True, tipo__id=1, verificada=True)

                    if search:
                        data['s'] = search
                        s = search.split(" ")
                        if len(s) == 1:
                            filtro = filtro & (Q(persona__apellido1__icontains=search) | Q(persona__apellido2__icontains=search) | Q(persona__nombres__icontains=search))
                        else:
                            filtro = filtro & (Q(persona__apellido1__icontains=s[0]) & Q(persona__apellido2__icontains=s[1]))

                        url_vars += '&s=' + search

                    personas = RedPersona.objects.filter(filtro).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')

                    paging = MiPaginador(personas, 25)
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
                    data['url_vars'] = url_vars
                    data['personas'] = page.object_list
                    data['title'] = u'Perfiles Académicos ORCID'
                    data['enlaceatras'] = "/articulosinvestigacion"

                    return render(request, "inv_articulos/listadoorcid.html", data)
                except Exception as ex:
                    pass

            elif action == 'addorcidpersona':
                try:
                    data['title'] = u'Agregar Perfil ORCID a Persona'
                    template = get_template("inv_articulos/addorcidpersona.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'editorcidpersona':
                try:
                    data['title'] = u'Editar Perfil ORCID Persona'
                    data['registroorcid'] = RedPersona.objects.get(pk=int(encrypt(request.GET['id'])))
                    template = get_template("inv_articulos/editorcidpersona.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'verificarorcid':
                try:
                    import datetime
                    identificador = request.GET['identificador'].strip()

                    registroorcid = requests.get(f'https://pub.orcid.org/v3.0/{identificador}', headers={'accept': 'application/json'})
                    objeto = registroorcid.json()

                    if not "response-code" in objeto:
                        fechasub = datetime.datetime.fromtimestamp(int(objeto["history"]["submission-date"]["value"]) / 1000)

                        registro = {
                            "url": objeto["orcid-identifier"]["uri"],
                            "identifier": objeto["orcid-identifier"]["path"],
                            "submissiondate": fechasub.strftime("%Y-%m-%d"),
                            "givenname": objeto["person"]["name"]["given-names"]["value"],
                            "familyname": objeto["person"]["name"]["family-name"]["value"] if objeto["person"]["name"]["family-name"] else ""
                        }

                        return JsonResponse({"result": "ok", "registro": registro})
                    else:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "No se encontraron registros asociados al identificador %s en el sitio web de ORCID" % (identificador), "showSwal": "True", "swalType": "warning"})
                except Exception as ex:
                    msg = ex.__str__()
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % (msg)})

            elif action == 'mostrarpublicaciones':
                try:
                    title = u'Publicaciones en ORCID'
                    redpersona = RedPersona.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['redpersona'] = redpersona
                    data['publicaciones'] = redpersona.publicaciones_orcid()
                    template = get_template("inv_articulos/publicacionesorcid.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': title})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'perfilesscopus':
                try:
                    search, url_vars = request.GET.get('s', ''), '&action=' + action
                    filtro = Q(status=True, tipo__id=4, verificada=True)

                    if search:
                        data['s'] = search
                        s = search.split(" ")
                        if len(s) == 1:
                            filtro = filtro & (Q(persona__apellido1__icontains=search) | Q(persona__apellido2__icontains=search) | Q(persona__nombres__icontains=search))
                        else:
                            filtro = filtro & (Q(persona__apellido1__icontains=s[0]) & Q(persona__apellido2__icontains=s[1]))

                        url_vars += '&s=' + search

                    personas = RedPersona.objects.filter(filtro).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')

                    paging = MiPaginador(personas, 25)
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
                    data['url_vars'] = url_vars
                    data['personas'] = page.object_list
                    data['title'] = u'Perfiles Académicos SCOPUS'
                    data['enlaceatras'] = "/articulosinvestigacion"

                    return render(request, "inv_articulos/listadoscopus.html", data)
                except Exception as ex:
                    pass

            elif action == 'addscopuspersona':
                try:
                    data['title'] = u'Agregar Perfil SCOPUS a Persona'
                    template = get_template("inv_articulos/addscopuspersona.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'editscopuspersona':
                try:
                    data['title'] = u'Editar Perfil SCOPUS Persona'
                    data['registroscopus'] = RedPersona.objects.get(pk=int(encrypt(request.GET['id'])))
                    template = get_template("inv_articulos/editscopuspersona.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'verificarscopus':
                try:
                    identificador = request.GET['identificador'].strip()

                    # Consulto por medio de la Api pública las publicaciones
                    registro = requests.get(f'https://api.elsevier.com/content/search/scopus?query=AU-ID("{identificador}")&apiKey=cfa6f5b37a0e8a3f6a30c190da693411', headers={'accept': 'application/json'})
                    objeto = registro.json()

                    totalregistros = int(objeto["search-results"]["opensearch:totalResults"])

                    # Si existen publicaciones es porque el ID es válido
                    if totalregistros > 0:
                        perfilscopus = requests.get(f'https://api.elsevier.com/content/author/author_id/{identificador}?apiKey=cfa6f5b37a0e8a3f6a30c190da693411', headers={'accept': 'application/json'})
                        objeto = perfilscopus.json()
                        apellidos = objeto["author-retrieval-response"][0]["author-profile"]["preferred-name"]["surname"]
                        nombres = objeto["author-retrieval-response"][0]["author-profile"]["preferred-name"]["given-name"]
                        nombrescompletos = apellidos + ", " + nombres

                        registro = {
                            "url": f'https://www.scopus.com/authid/detail.uri?authorId={identificador}',
                            "identifier": identificador,
                            "profilename": nombrescompletos
                        }

                        return JsonResponse({"result": "ok", "registro": registro})
                    else:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "No se encontraron registros asociados al identificador %s en el sitio web de SCOPUS" % (identificador), "showSwal": "True", "swalType": "warning"})
                except Exception as ex:
                    msg = ex.__str__()
                    return JsonResponse({"result": "bad", "titulo": "No se pudo consultar!!!", "mensaje": u"Error al obtener los datos. %s" % (msg)})

            elif action == 'mostrarpublicacionesscopus':
                try:
                    title = u'Publicaciones en SCOPUS'
                    perfilacademico = RedPersona.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['perfilacademico'] = perfilacademico
                    data['publicaciones'] = perfilacademico.publicaciones_scopus()
                    template = get_template("inv_articulos/publicacionesscopus.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': title})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            # elif action == 'evidenciasarticulo':
            #     try:
            #         url = '/media/zipav/articulosevidencias.zip'
            #         fantasy_zip = zipfile.ZipFile(SITE_STORAGE + url, 'w')
            #
            #         # articulos = ArticuloInvestigacion.objects.filter(status=True, fechapublicacion__isnull=False, fechapublicacion__year=2019).order_by('id')
            #         articulos = ArticuloInvestigacion.objects.filter(status=True, fechapublicacion__isnull=False).order_by('id')
            #         for articulo in articulos:
            #             articulo_id = articulo.id
            #             nombre = "ARTICULO_" + str(articulo_id).zfill(4)
            #
            #             for evidencia in articulo.detalleevidencias_set.filter(status=True):
            #                 ext = evidencia.archivo.__str__()[evidencia.archivo.__str__().rfind("."):]
            #                 if evidencia.evidencia.id == 1:
            #                     if os.path.exists(SITE_STORAGE + evidencia.archivo.url):
            #                         fantasy_zip.write(SITE_STORAGE + evidencia.archivo.url, nombre + '_PUBLICACION_' + str(articulo.fechapublicacion.year) + ext.lower())
            #                 elif evidencia.evidencia.id == 3:
            #                     if os.path.exists(SITE_STORAGE + evidencia.archivo.url):
            #                         fantasy_zip.write(SITE_STORAGE + evidencia.archivo.url, nombre + '_CARTAACEPTACION_' + str(articulo.fechapublicacion.year) + ext.lower())
            #
            #         fantasy_zip.close()
            #
            #         response = HttpResponse(open(SITE_STORAGE + url, 'rb'), content_type='application/zip')
            #         response['Content-Disposition'] = 'attachment; filename=articulosevidencias_' + random.randint(1, 10000).__str__() + '.zip'
            #         return response
            #     except Exception as ex:
            #         pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Listado de Articulos'
            search = None
            ids = None
            tipobus = None
            inscripcionid = None
            if 'id' in request.GET:
                data['tipobus'] = 2
                ids = request.GET['id']
                programasinvestigacion = ArticuloInvestigacion.objects.select_related().filter(pk=int(encrypt(ids)), status=True).order_by('nombre')
            elif 's' in request.GET:
                search = request.GET['s']
                # if search.isdigit():
                #     data['tipobus'] = 2
                #     programasinvestigacion = ArticuloInvestigacion.objects.select_related().filter(pk=search, status=True).order_by('-fechapublicacion', 'revista__nombre', 'numero', 'nombre')
                # else:
                tipobus = int(request.GET['tipobus'])
                data['tipobus'] = tipobus
                if tipobus == 1:
                    programasinvestigacion = ArticuloInvestigacion.objects.select_related().filter(revista__nombre__icontains=search, revista__status=True, status=True).order_by('revista__nombre', '-fechapublicacion', 'numero', 'nombre')
                if tipobus == 2:
                    programasinvestigacion = ArticuloInvestigacion.objects.select_related().filter(nombre__icontains=search, status=True).order_by('revista__nombre', '-fechapublicacion', 'numero', 'nombre')
                if tipobus == 3:
                    if ' ' in search:
                        s = search.split(" ")
                        participantesarticulos = ParticipantesArticulos.objects.values_list('articulo_id').filter(status=True).filter(Q(profesor__persona__apellido1__contains=s[0]) & Q(profesor__persona__apellido2__contains=s[1])).distinct()
                        programasinvestigacion = ArticuloInvestigacion.objects.select_related().filter(pk__in=participantesarticulos, status=True).order_by('revista__nombre','-fechapublicacion',  'numero', 'nombre')
                    else:
                        participantesarticulos = ParticipantesArticulos.objects.values_list('articulo_id').filter(status=True).filter(
                            Q(profesor__persona__nombres__icontains=search) |
                            Q(profesor__persona__apellido1__icontains=search) |
                            Q(profesor__persona__apellido2__icontains=search) |
                            Q(administrativo__persona__nombres__icontains=search) |
                            Q(administrativo__persona__apellido1__icontains=search) |
                            Q(administrativo__persona__apellido2__icontains=search) |
                            Q(inscripcion__persona__nombres__icontains=search) |
                            Q(inscripcion__persona__apellido1__icontains=search) |
                            Q(inscripcion__persona__apellido2__icontains=search) ).distinct()
                        programasinvestigacion = ArticuloInvestigacion.objects.select_related().filter(pk__in=participantesarticulos, status=True).order_by('revista__nombre','-fechapublicacion',  'numero', 'nombre')
                if tipobus == 4:
                    programasinvestigacion = ArticuloInvestigacion.objects.select_related().filter(articulosbaseindexada__baseindexada__nombre__icontains=search, status=True).order_by('-fechapublicacion', 'revista__nombre', 'numero', 'nombre')
                if tipobus == 5:
                    # fecha = convertir_fecha_invertida(search)
                    anio = int(search)
                    programasinvestigacion = ArticuloInvestigacion.objects.select_related().filter(fechapublicacion__year=anio, status=True).order_by('revista__nombre','-fechapublicacion',  'numero', 'nombre')
            elif 'idsp' in request.GET:
                data['tipobus'] = 3
                lista_ids_personas = request.GET['idsp'].split(",")
                participantesarticulos = ParticipantesArticulos.objects.values_list('articulo_id').filter(status=True).filter(Q(profesor__persona__id__in=lista_ids_personas) |
                                                                                                                              Q(administrativo__persona__id__in=lista_ids_personas)|
                                                                                                                              Q(inscripcion__persona__id__in=lista_ids_personas)).distinct()
                programasinvestigacion = ArticuloInvestigacion.objects.select_related().filter(pk__in=participantesarticulos, status=True).order_by('revista__nombre','-fechapublicacion',  'numero', 'nombre')
            else:
                data['tipobus'] = 2
                programasinvestigacion = ArticuloInvestigacion.objects.select_related().filter(status=True).order_by('revista__nombre','-fechapublicacion',  'numero', 'nombre')

            # estadoparticipante  = 0
            # if 'estadoparticipante' in request.GET:
            #     estadoparticipante = int(request.GET['estadoparticipante'])
            #     if estadoparticipante > 0:
            #         if estadoparticipante == 1:
            #             participantesarticulos = ParticipantesArticulos.objects.values_list('articulo_id').distinct('articulo_id')#.filter(status=True)#
            #             programasinvestigacion = programasinvestigacion.filter(pk__in=participantesarticulos)
            #         else:
            #             programasinvestigacion = programasinvestigacion.filter(participantesarticulos__isnull=True)

            estadoparticipante = 0
            if 'estadoparticipante' in request.GET:
                estadoparticipante = int(request.GET['estadoparticipante'])
                if estadoparticipante > 0:
                    if estadoparticipante == 1:
                        programasinvestigacion = programasinvestigacion.filter(aprobado=True)
                    else:
                        programasinvestigacion = programasinvestigacion.filter(aprobado=False)


            totalarticulos = programasinvestigacion.count()
            totalsinparticipantes = programasinvestigacion.filter(participantesarticulos__isnull=True).count()
            totalconparticipantes = totalarticulos - totalsinparticipantes

            totalaprobados = programasinvestigacion.filter(aprobado=True).count()
            totalporaprobar = totalarticulos - totalaprobados

            paging = MiPaginador(programasinvestigacion, 25)
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
            data['articulos'] = page.object_list
            data['search'] = search if search else ""
            data['ids'] = ids if ids else ""
            data['totalarticulos'] = totalarticulos
            data['totalconparticipantes'] = totalconparticipantes
            data['totalsinparticipantes'] = totalsinparticipantes
            data['estadoparticipante'] = estadoparticipante
            data['totalaprobados'] = totalaprobados
            data['totalporaprobar'] = totalporaprobar
            data['aniosevidencias'] = ArticuloInvestigacion.objects.filter(Q(status=True) | Q(status=False, eliminadoxdoc=True), fechapublicacion__isnull=False).annotate(anio=ExtractYear('fechapublicacion')).values_list('anio', flat=True).order_by('-anio').distinct()
            data['participantes'] = Persona.objects.values('id', 'cedula', 'nombres', 'apellido1', 'apellido2').filter(Q(profesor__participantesarticulos__isnull=False, profesor__participantesarticulos__status=True)
                                                           |Q(administrativo__participantesarticulos__isnull=False, administrativo__participantesarticulos__status=True)
                                                           |Q(inscripcion__participantesarticulos__isnull=False, inscripcion__participantesarticulos__status=True)).distinct().order_by('apellido1', 'apellido2', 'nombres')

            return render(request, "inv_articulos/view.html", data)

