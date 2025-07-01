# -*- coding: latin-1 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from googletrans import Translator
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from bib.forms import DocumentoForm, PrestamoDocumentoForm, AdicionarDocumentoForm, PrestamoDocumentoReservaForm
from bib.models import Documento, TipoDocumento, PrestamoDocumento, DocumentoColeccion, ReservaDocumento
from decorators import secure_module, last_access
from settings import DOCUMENTOS_COLECCION, DOCUMENTOS_AUTONUMERACION, DOCUMENTOS_COLECCION_AUTONUMERACION
from sga.commonviews import adduserdata, obtener_reporte
from sga.funciones import generar_nombre, log, puede_realizar_accion, MiPaginador
from sga.models import Persona
from datetime import datetime, timedelta


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = DocumentoForm(request.POST, request.FILES)
                if f.is_valid():
                    if not DOCUMENTOS_AUTONUMERACION:
                        if Documento.objects.filter(codigo=f.cleaned_data['codigo']).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Ya existe un documento con ese codigo."})
                    documento = Documento(codigo='',
                                          codigoisbnissn=f.cleaned_data['codigoisbnissn'],
                                          nombre=f.cleaned_data['nombre'],
                                          ubicacionfisica=f.cleaned_data['ubicacionfisica'],
                                          estado=f.cleaned_data['estado'],
                                          areaconocimiento=f.cleaned_data['areaconocimiento'],
                                          fecha=f.cleaned_data['fecha'],
                                          numerofactura=f.cleaned_data['numerofactura'],
                                          autorcorporativo=f.cleaned_data['autorcorporativo'],
                                          lugarpublicacion=f.cleaned_data['lugarpublicacion'],
                                          edicion=f.cleaned_data['edicion'],
                                          autor=f.cleaned_data['autor'],
                                          tipo=f.cleaned_data['tipo'],
                                          nivel=f.cleaned_data['nivel'],
                                          tipoingreso=f.cleaned_data['tipoingreso'],
                                          donadopor=f.cleaned_data['donadopor'],
                                          anno=f.cleaned_data['anno'],
                                          emision=f.cleaned_data['emision'],
                                          volumen=f.cleaned_data['volumen'],
                                          tomo=f.cleaned_data['tomo'],
                                          palabrasclaves=f.cleaned_data['palabrasclaves'],
                                          fisico=True,
                                          copias=f.cleaned_data['copias'],
                                          paginas=f.cleaned_data['paginas'],
                                          editora=f.cleaned_data['editora'],
                                          referencia=f.cleaned_data['referencia'],
                                          sede=f.cleaned_data['sede'],
                                          codigodewey=f.cleaned_data['codigodewey'],
                                          idioma=f.cleaned_data['idioma'],
                                          tutor=f.cleaned_data['tutor'],
                                          resumen=f.cleaned_data['resumen'],
                                          codigocutter=f.cleaned_data['codigocutter'],
                                          preciocosto=f.cleaned_data['preciocosto'],
                                          establecimientoresponsable=f.cleaned_data['establecimientoresponsable'])
                    if 'digital' in request.FILES:
                        documento.descripcionfisica = ''
                        documento.fisico = False
                        documento.prestamosala = False
                        fichero1 = request.FILES['digital']
                        fichero1._name = generar_nombre("documento_", fichero1._name)
                        documento.digital = fichero1
                    else:
                        documento.digital = ''
                        documento.descripcionfisica = f.cleaned_data['descripcionfisica']
                        documento.fisico = True
                        documento.prestamosala = f.cleaned_data['prestamosala']
                    if DOCUMENTOS_COLECCION:
                        documento.copias = 0
                    else:
                        documento.copias = f.cleaned_data['copias']
                    if 'portada' in request.FILES:
                        fichero2 = request.FILES['portada']
                        fichero2._name = generar_nombre("portada_", fichero2._name)
                        documento.portada = fichero2
                    if 'indice' in request.FILES:
                        fichero3 = request.FILES['indice']
                        fichero3._name = generar_nombre("indice", fichero3._name)
                        documento.indice = fichero3
                    documento.save(request)
                    if DOCUMENTOS_AUTONUMERACION:
                        documento.codigo = documento.id.__str__().zfill(10)
                    else:
                        documento.codigo = f.cleaned_data['codigo']
                    documento.save(request)
                    documentocarrera = documento.documento_carrera()
                    if not documento.referencia:
                        documentocarrera.carrera = f.cleaned_data['carrera']
                        documentocarrera.save(request)
                    log(u'Adiciono documento en biblioteca: %s' % documento, request, "add")
                    return JsonResponse({"result": "ok", "id": documento.id})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "mensaje":translator.translate(ex.__str__(),'es').text})

        elif action == 'addejemplar':
            try:
                f = AdicionarDocumentoForm(request.POST)
                if f.is_valid():
                    documento = Documento.objects.get(pk=request.POST['id'])
                    if DocumentoColeccion.objects.filter(codigo=f.cleaned_data['codigo']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El codigo ingresado ya existe."})
                    documentocoleccion = DocumentoColeccion(documento=documento,
                                                            codigo=f.cleaned_data['codigo'],
                                                            estado=f.cleaned_data['estado'],
                                                            habilitado=True)
                    documentocoleccion.save(request)
                    log(u'Adiciono ejemplar en biblioteca: %s' % documentocoleccion, request, "add")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editejemplar':
            try:
                f = AdicionarDocumentoForm(request.POST)
                documento = DocumentoColeccion.objects.get(pk=request.POST['id'])
                if f.is_valid():
                    documento.estado = f.cleaned_data['estado']
                    documento.save(request)
                    log(u'Modifico ejemplar en biblioteca: %s' % documento, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'edit':
            try:
                documento = Documento.objects.get(pk=request.POST['id'])
                f = DocumentoForm(request.POST, request.FILES)
                if f.is_valid():
                    documento.codigoisbnissn = f.cleaned_data['codigoisbnissn']
                    documento.codigodewey = f.cleaned_data['codigodewey']
                    documento.codigocutter = f.cleaned_data['codigocutter']
                    documento.ubicacionfisica = f.cleaned_data['ubicacionfisica']
                    documento.percha = f.cleaned_data['percha']
                    documento.hilera = f.cleaned_data['hilera']
                    documento.estado = f.cleaned_data['estado']
                    documento.areaconocimiento = f.cleaned_data['areaconocimiento']
                    documento.fecha = f.cleaned_data['fecha']
                    documento.numerofactura = f.cleaned_data['numerofactura']
                    documento.nivel = f.cleaned_data['nivel']
                    documento.tipoingreso = f.cleaned_data['tipoingreso']
                    documento.donadopor = f.cleaned_data['donadopor']
                    documento.nombre = f.cleaned_data['nombre']
                    documento.nombre2 = f.cleaned_data['nombre2']
                    documento.autor = f.cleaned_data['autor']
                    documento.tipo = f.cleaned_data['tipo']
                    documento.anno = f.cleaned_data['anno']
                    documento.emision = f.cleaned_data['emision']
                    documento.volumen = f.cleaned_data['volumen']
                    documento.tomo = f.cleaned_data['tomo']
                    documento.palabrasclaves = f.cleaned_data['palabrasclaves']
                    documento.editora = f.cleaned_data['editora']
                    documento.sede = f.cleaned_data['sede']
                    documento.idioma = f.cleaned_data['idioma']
                    documento.paginas = f.cleaned_data['paginas']
                    documento.tutor = f.cleaned_data['tutor']
                    documento.referencia = f.cleaned_data['referencia']
                    documento.resumen = f.cleaned_data['resumen']
                    documento.autorcorporativo = f.cleaned_data['autorcorporativo']
                    documento.lugarpublicacion = f.cleaned_data['lugarpublicacion']
                    documento.edicion = f.cleaned_data['edicion']
                    documento.preciocosto = f.cleaned_data['preciocosto']
                    documento.establecimientoresponsable = f.cleaned_data['establecimientoresponsable']
                    documentocarrera = documento.documento_carrera()
                    if documento.referencia:
                        carreras = documento.documento_carrera()
                        carreras.carrera.clear()
                    else:
                        documentocarrera.carrera = f.cleaned_data['carrera']
                        documentocarrera.save(request)
                    if documento.digital:
                        documento.fisico = False
                        documento.copias = 0
                        documento.prestamosala = False
                        documento.descripcionfisica = ''
                    else:
                        documento.ubicacionfisica = f.cleaned_data['ubicacionfisica']
                        documento.fisico = True
                        if DOCUMENTOS_COLECCION:
                            documento.copias = 0
                        else:
                            documento.copias = f.cleaned_data['copias']
                        documento.prestamosala = f.cleaned_data['prestamosala']
                        documento.descripcionfisica = f.cleaned_data['descripcionfisica']
                    if 'portada' in request.FILES:
                        fichero2 = request.FILES['portada']
                        fichero2._name = generar_nombre("portada_", fichero2._name)
                        documento.portada = fichero2
                    if 'indice' in request.FILES:
                        fichero3 = request.FILES['indice']
                        fichero3._name = generar_nombre("indice", fichero3._name)
                        documento.indice = fichero3
                    documento.save(request)
                    log(u'Modifico documento de biblioteca: %s' % documento, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delete':
            try:
                documento = Documento.objects.get(pk=request.POST['id'])
                if documento.prestamodocumento_set.exists():
                    return JsonResponse({"result": "bad", "mensaje": u"El documento tiene prestamos."})
                log(u'Elimino documento de biblioteca: %s' % documento, request, "del")
                documento.delete()
                return JsonResponse({"result": "ok", "id": documento.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar datos."})

        elif action == 'delejemplar':
            try:
                documentocoleccion = DocumentoColeccion.objects.get(pk=request.POST['id'])
                if documentocoleccion.prestamodocumento_set.exists():
                    return JsonResponse({"result": "bad", "mensaje": u"El documento tiene prestamos."})
                log(u'Elimino ejemplar de biblioteca: %s' % documentocoleccion, request, "del")
                documentocoleccion.delete()
                return JsonResponse({"result": "ok", "id": documentocoleccion.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar datos."})

        elif action == 'addprestamo':
            try:
                documento = Documento.objects.get(pk=request.POST['id'])
                responsableentrega = request.session['persona']
                f = PrestamoDocumentoForm(request.POST)
                if f.is_valid():
                    persona = Persona.objects.get(pk=request.POST['idpersona'])
                    prestamo = PrestamoDocumento(documento=documento,
                                                 persona=persona,
                                                 responsableentrega=responsableentrega,
                                                 tiempo=f.cleaned_data['tiempo'],
                                                 fechaentrega=datetime.now().date() if not f.cleaned_data['retroactivo'] else (datetime.now() - timedelta(hours=int(f.cleaned_data['tiempo']))).date(),
                                                 horaentrega=datetime.now().time() if not f.cleaned_data['retroactivo'] else (datetime.now() - timedelta(hours=int(f.cleaned_data['tiempo']))).time(),
                                                 entregado=True,
                                                 recibido=False if not f.cleaned_data['retroactivo'] else True,
                                                 prestamosala=f.cleaned_data['prestamosala'])
                    prestamo.save(request)
                    if f.cleaned_data['retroactivo']:
                        prestamo.fecharecibido = datetime.now().date()
                        prestamo.horarecibido = datetime.now().time()
                        prestamo.responsablerecibido = responsableentrega
                        prestamo.save(request)
                    if DOCUMENTOS_COLECCION:
                        prestamo.documentocoleccion = f.cleaned_data['ejemplar']
                        prestamo.save(request)
                    log(u'Prestamo de documento en biblioteca: %s' % prestamo, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addprestamoreserva':
            try:
                reserva = ReservaDocumento.objects.get(pk=request.POST['id'])
                responsableentrega = request.session['persona']
                f = PrestamoDocumentoReservaForm(request.POST)
                if f.is_valid():
                    prestamo = PrestamoDocumento(documento=reserva.documento,
                                                 persona=reserva.persona,
                                                 responsableentrega=responsableentrega,
                                                 tiempo=f.cleaned_data['tiempo'],
                                                 fechaentrega=datetime.now().date() if not f.cleaned_data['retroactivo'] else (datetime.now() - timedelta(hours=int(f.cleaned_data['tiempo']))).date(),
                                                 horaentrega=datetime.now().time() if not f.cleaned_data['retroactivo'] else (datetime.now() - timedelta(hours=int(f.cleaned_data['tiempo']))).time(),
                                                 entregado=True,
                                                 recibido=False if not f.cleaned_data['retroactivo'] else True,
                                                 prestamosala=f.cleaned_data['prestamosala'])
                    prestamo.save(request)
                    reserva.entregado = True
                    reserva.fechaentrega = prestamo.fechaentrega
                    reserva.save(request)
                    if f.cleaned_data['retroactivo']:
                        prestamo.fecharecibido = datetime.now().date()
                        prestamo.horarecibido = datetime.now().time()
                        prestamo.responsablerecibido = responsableentrega
                        prestamo.save(request)
                    if DOCUMENTOS_COLECCION:
                        prestamo.documentocoleccion = f.cleaned_data['ejemplar']
                        prestamo.save(request)
                    log(u'Prestamo de documento desde reserva en biblioteca: %s' % prestamo, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_documentos_biblioteca')
                    data['title'] = u'Adicionar documento a la biblioteca'
                    form = DocumentoForm(initial={'fecha': datetime.now()})
                    if DOCUMENTOS_COLECCION:
                        form.es_coleccion()
                    if DOCUMENTOS_AUTONUMERACION:
                        form.es_autonumerico()
                    data['form'] = form
                    return render(request, "biblioteca/add.html", data)
                except Exception as ex:
                    pass

            elif action == 'edit':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_documentos_biblioteca')
                    data['title'] = u'Editar documento de la biblioteca'
                    documento = Documento.objects.get(pk=request.GET['id'])
                    carreras = documento.documento_carrera()
                    form = DocumentoForm(initial={'codigoisbnissn': documento.codigoisbnissn,
                                                  'codigodewey': documento.codigodewey,
                                                  'codigocutter': documento.codigocutter,
                                                  'percha': documento.percha,
                                                  'hilera': documento.hilera,
                                                  'estado': documento.estado,
                                                  'areaconocimiento': documento.areaconocimiento,
                                                  'fecha': documento.fecha,
                                                  'numerofactura': documento.numerofactura,
                                                  'tipo': documento.tipo,
                                                  'tutor': documento.tutor,
                                                  'nombre': documento.nombre,
                                                  'nombre2': documento.nombre2,
                                                  'ubicacionfisica': documento.ubicacionfisica,
                                                  'autor': documento.autor,
                                                  'nivel': documento.nivel,
                                                  'tipoingreso': documento.tipoingreso,
                                                  'donadopor': documento.donadopor,
                                                  'autorcorporativo': documento.autorcorporativo,
                                                  'anno': documento.anno,
                                                  'emision': documento.emision,
                                                  'volumen': documento.volumen,
                                                  'tomo': documento.tomo,
                                                  'edicion': documento.edicion,
                                                  'editora': documento.editora,
                                                  'lugarpublicacion': documento.lugarpublicacion,
                                                  'sede': documento.sede,
                                                  'idioma': documento.idioma,
                                                  'establecimientoresponsable': documento.establecimientoresponsable,
                                                  'descripcionfisica': documento.descripcionfisica,
                                                  'paginas': documento.paginas,
                                                  'copias': documento.copias,
                                                  'referencia': documento.referencia,
                                                  'resumen': documento.resumen,
                                                  'prestamosala': documento.prestamosala,
                                                  'preciocosto': documento.preciocosto,
                                                  'digital': documento.digital,
                                                  'carrera': carreras.carrera.all(),
                                                  'portada': documento.portada,
                                                  'palabrasclaves': documento.palabrasclaves})
                    form.es_autonumerico()
                    if documento.fisico:
                        form.editar_fisico()
                    else:
                        form.editar_digital()
                    data['form'] = form
                    data['documento'] = documento
                    return render(request, "biblioteca/edit.html", data)
                except Exception as ex:
                    pass

            elif action == 'delete':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_documentos_biblioteca')
                    data['title'] = u'Eliminar documento de la biblioteca'
                    data['documento'] = Documento.objects.get(pk=request.GET['id'])
                    return render(request, "biblioteca/delete.html", data)
                except Exception as ex:
                    pass

            elif action == 'ejemplares':
                try:
                    data['title'] = u'Ejemplares de libros'
                    documento = Documento.objects.get(pk=request.GET['id'])
                    data['documento'] = documento
                    data['ejemplares'] = documento.documentocoleccion_set.all()
                    return render(request, "biblioteca/ejemplares.html", data)
                except Exception as ex:
                    pass

            elif action == 'addejemplar':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_documentos_biblioteca')
                    documento = Documento.objects.get(pk=request.GET['id'])
                    if DOCUMENTOS_COLECCION_AUTONUMERACION:
                        ejemplar = DocumentoColeccion(documento=documento,
                                                      codigo='',
                                                      habilitado=True)
                        ejemplar.save(request)
                        ejemplar.codigo = ejemplar.id.__str__().zfill(10)
                        ejemplar.save(request)
                        log(u'Adiciono ejemplar en biblioteca: %s' % ejemplar, request, "edit")
                        return HttpResponseRedirect("/documentos?action=ejemplares&id=" + request.GET['id'])
                    else:
                        form = AdicionarDocumentoForm()
                        data['form'] = form
                        data['documento'] = documento
                        return render(request, "biblioteca/addejemplar.html", data)
                except Exception as ex:
                    pass

            elif action == 'editejemplar':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_documentos_biblioteca')
                    data['title'] = u'Editar Ejemplar'
                    documento = DocumentoColeccion.objects.get(pk=request.GET['id'])
                    form = AdicionarDocumentoForm(initial={'estado': documento.estado})
                    form.editar()
                    data['form'] = form
                    data['documento'] = documento
                    return render(request, "biblioteca/editejemplar.html", data)
                except Exception as ex:
                    pass

            elif action == 'habilitarejemplar':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_documentos_biblioteca')
                    documento = DocumentoColeccion.objects.get(pk=request.GET['id'])
                    if not documento.prestamodocumento_set.filter(recibido=False).exists():
                        documento.habilitado = True
                        documento.save(request)
                        log(u'Habilito documento en biblioteca: %s' % documento, request, "edit")
                    return HttpResponseRedirect("/documentos?action=ejemplares&id=" + str(documento.documento.id))
                except Exception as ex:
                    pass

            elif action == 'deshabilitarjemplar':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_documentos_biblioteca')
                    documento = DocumentoColeccion.objects.get(pk=request.GET['id'])
                    if not documento.prestamodocumento_set.filter(recibido=False).exists():
                        documento.habilitado = False
                        documento.save(request)
                        log(u'Deshabilito documento en biblioteca: %s' % documento, request, "edit")
                    return HttpResponseRedirect("/documentos?action=ejemplares&id=" + str(documento.documento.id))
                except Exception as ex:
                    pass

            elif action == 'delejemplar':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_documentos_biblioteca')
                    data['title'] = u'Eliminar ejemplares'
                    data['documentocoleccion'] = DocumentoColeccion.objects.get(pk=request.GET['id'])
                    return render(request, "biblioteca/delejemplares.html", data)
                except Exception as ex:
                    pass

            elif action == 'addprestamo':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_prestamos_biblioteca')
                    data['title'] = u'Generar prestamo de documento en la biblioteca'
                    documento = Documento.objects.get(pk=request.GET['id'])
                    form = PrestamoDocumentoForm(initial={'prestamosala': documento.prestamosala})
                    form.en_coleccion(documento)
                    data['form'] = form
                    data['documento'] = documento
                    return render(request, "biblioteca/addprestamo.html", data)
                except Exception as ex:
                    pass

            elif action == 'addprestamoreserva':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_prestamos_biblioteca')
                    data['title'] = u'Generar prestamo de documento desde reserva en la biblioteca'
                    reserva = ReservaDocumento.objects.get(pk=request.GET['id'])
                    form = PrestamoDocumentoReservaForm(initial={'prestamosala': reserva.documento.prestamosala,
                                                                 'persona': reserva.persona})
                    form.en_coleccion(reserva.documento)
                    form.solicita(reserva.persona)
                    data['form'] = form
                    data['reserva'] = reserva
                    return render(request, "biblioteca/addprestamoreserva.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Documentos en biblioteca'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
                documentos = Documento.objects.filter(Q(codigo__icontains=search) |
                                                      Q(nombre__icontains=search) |
                                                      Q(documentocoleccion__codigo__icontains=search) |
                                                      Q(autor__icontains=search) |
                                                      Q(anno__icontains=search)).distinct()
            elif 'id' in request.GET:
                ids = request.GET['id']
                documentos = Documento.objects.filter(id=ids)
            else:
                documentos = Documento.objects.all()
            paging = MiPaginador(documentos, 25)
            p = 1
            try:
                if 'page' in request.GET:
                    p = int(request.GET['page'])
                page = paging.page(p)
            except Exception as ex:
                page = paging.page(p)
            data['paging'] = paging
            data['rangospaging'] = paging.rangos_paginado(p)
            data['page'] = page
            data['search'] = search if search else ""
            data['ids'] = ids if ids else ""
            data['documentos'] = page.object_list
            data['tipos'] = TipoDocumento.objects.all()
            data['coleccion'] = DOCUMENTOS_COLECCION
            data['reporte_0'] = obtener_reporte('cartillas_biblioteca_individual')
            return render(request, "biblioteca/documentos.html", data)
