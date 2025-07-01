# -*- coding: UTF-8 -*-
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, F
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, variable_valor, remover_caracteres_tildes_unicode, remover_caracteres_especiales_unicode
from settings import SITE_STORAGE
import sys
import os
import json
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsave_anteproyecto
from sga.templatetags.sga_extras import encrypt
# Proceso Solicitud
from edcon.forms import SolicitudAnteproyectoForm
from edcon.models import SolicitudAnteproyecto, ComponenteAprendizaje, HistorialSolicitudAnteproyecto, ConfigTipoAnteproyectoRequisito, ConfigTipoAnteComponenteApre, TipoAnteproyecto
import fitz
from django.core.files import File as DjangoFile
import io
from core.firmar_documentos import firmar


@login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    usuario = request.user

    data['IS_DEBUG'] = IS_DEBUG = variable_valor('IS_DEBUG')

    dominio_sistema = 'http://127.0.0.1:8000'
    if not IS_DEBUG:
        dominio_sistema = 'https://sga.unemi.edu.ec'

    if request.method == 'POST':
        data['action'] = action = request.POST['action']

        if action == 'addsolicitud':
            with transaction.atomic():
                try:
                    form = SolicitudAnteproyectoForm(request.POST)
                    # analizar getlist
                    lista = request.POST.getlist('puntaje_item[]')
                    if form.is_valid() and form.validador():

                        # lista = json.loads(request.POST['lista_items1'])

                        # predeterminar el departamento
                        data['departamento'] = departamento = u'Educación Continua'
                        # Validaciones
                        configrequisitos = ConfigTipoAnteproyectoRequisito.objects.filter(status=True, tipoanteproyecto=form.cleaned_data['tipoanteproyecto'], vigente=True)
                        if not configrequisitos:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!",
                                                 "mensaje": u"Acción no permitida. No existe una configuración de requisitos vigente, por favor comunicar al departamento de " + str(departamento),
                                                 "showSwal": "True", "swalType": "warning"})
                        if len(configrequisitos) > 1:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!",
                                                 "mensaje": u"Acción no permitida. Existe más de una configuración de requisitos vigente, sólo se permite una, por favor comunicar al departamento de " + str(departamento),
                                                 "showSwal": "True", "swalType": "warning"})
                        # Obtener la configuracion de requisitos vigente conforme el tipo de anteproyecto
                        configrequisitos = ConfigTipoAnteproyectoRequisito.objects.get(status=True, tipoanteproyecto=form.cleaned_data['tipoanteproyecto'], vigente=True)

                        solicitudanteproyecto = SolicitudAnteproyecto(
                            fecha=datetime.now().date(),
                            tema=form.cleaned_data['tema'],
                            persona=persona,
                            estado = 1,
                            tipoanteproyecto = form.cleaned_data['tipoanteproyecto'],
                            introduccion = form.cleaned_data['introduccion'],
                            metodologia = form.cleaned_data['metodologia'],
                            estudiopertinencia = form.cleaned_data['estudiopertinencia'],
                            problemasoluciona = form.cleaned_data['problemasoluciona'],
                            objetivogeneral = form.cleaned_data['objetivogeneral'],
                            objetivoespecifico = form.cleaned_data['objetivoespecifico'],
                            dirigidoa = form.cleaned_data['dirigidoa'],
                            configtipoanteproyectorequisito = configrequisitos,
                            contenido=form.cleaned_data['contenido'],
                            # fechainicio=form.cleaned_data['fechainicio'],
                            # fechafin=form.cleaned_data['fechafin'],
                            duracion=form.cleaned_data['duracion'],
                            horario=form.cleaned_data['horario'],
                            considerarhorasautonomas=form.cleaned_data['considerarhorasautonomas'],
                            modalidad=form.cleaned_data['modalidad'],
                            tipocertificado=form.cleaned_data['tipocertificado'],
                            conclusion=form.cleaned_data['conclusion'],
                            recomendacion=form.cleaned_data['recomendacion'],
                            # observacion=form.cleaned_data['observacion']
                        )
                        solicitudanteproyecto.save(request)

                        # Guardo la cantidad de horas de la lista de componentes de aprendizajes
                        # if 'lista_items1' in request.POST:
                        #     lista = json.loads(request.POST['lista_items1'])
                        #     for l in lista:
                        #         detallecomponentes = DetalleComponenteAprendizaje(
                        #             solicitudanteproyecto=solicitudanteproyecto,
                        #             componenteaprendizaje_id=l['id'],
                        #             hora=l['valor']
                        #         )
                        #         detallecomponentes.save()

                        # Generar anteproyecto pdf desactualizada revisar
                        # data['solicitud'] = solicitudanteproyecto
                        # dominio_sistema = 'http://127.0.0.1:8000'
                        # if not IS_DEBUG:
                        #     dominio_sistema = 'https://sga.unemi.edu.ec'
                        # data["DOMINIO_DEL_SISTEMA"] = dominio_sistema
                        # data['version'] = version = datetime.now().strftime('%Y%m%d_%H%M%S%f')
                        # name = f'anteproyecto_{str(solicitudanteproyecto.id)}_{str(solicitudanteproyecto.estado)}_{str(version)}'
                        # folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'anteproyectos'))
                        # directory = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'anteproyectos'))
                        # rutapdf = folder + name + '.pdf'
                        # try:
                        #     os.stat(directory)
                        # except:
                        #     os.mkdir(directory)
                        # if os.path.isfile(rutapdf):
                        #     os.remove(rutapdf)
                        # valida = conviert_html_to_pdfsave_anteproyecto(
                        #     'pro_solicitudanteproyecto/anteproyecto_pdf.html',
                        #     {'pagesize': 'A4', 'data': data},
                        #     name + '.pdf',
                        #     'anteproyectos'
                        # )
                        # solicitudanteproyecto.archivo = 'qrcode/anteproyectos/' + name + '.pdf'
                        # solicitudanteproyecto.save(request)
                        # Generar anteproyecto pdf

                        # LLama a la función que generar el pdf de la solicitud
                        generarpdf_solicitud(request, solicitudanteproyecto, data, dominio_sistema)

                        # Guardo el historial de las solicitudes de anteproyecto realizadas
                        historial = HistorialSolicitudAnteproyecto(fecha=datetime.now().date(),
                                                                 persona=persona,
                                                                 solicitudanteproyecto=solicitudanteproyecto,
                                                                 estado=1,
                                                                 archivo=solicitudanteproyecto.archivo,
                                                                 observacion='Solicitud ingresada, falta firma electrónica.')
                        historial.save(request)
                        log(u'%s adicionó solicitud de anteproyecto en : %s' % (persona, solicitudanteproyecto),
                            request, "add")
                        return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito",
                                            "showSwal": True})
                    else:
                        transaction.set_rollback(True)
                        x = form.errors
                        raise NameError('Error en el formulario')
                except Exception as ex:
                    msg = ex.__str__()
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg,
                                        "showSwal": "True", "swalType": "error"})

        elif action == 'editsolicitud':
            with transaction.atomic():
                try:
                    pass
                    # Valido si puede editar
                    # if not solicitud.puede_editar():
                    #     return JsonResponse(
                    #         {"result": "bad", "titulo": "Atención!!!", "mensaje": f"Acción no permitida debido al estado de la solicitud.",
                    #          "showSwal": "True", "swalType": "warning"})
                except Exception as ex:
                    msg = ex.__str__()
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'delsolicitud':
            with transaction.atomic():
                try:
                    solicitud = SolicitudAnteproyecto.objects.get(pk=int(encrypt(request.POST['id'])))
                    # Valido si puede eliminar
                    if not solicitud.puede_eliminar():
                        return JsonResponse(
                            {"result": "bad", "titulo": "Atención!!!", "mensaje": f"Acción no permitida, debido al estado de la solicitud.",
                             "showSwal": "True", "swalType": "danger"})
                    solicitud.status = False
                    # Elimino el historial de la solicitud
                    for historialsolicitud in solicitud.historialsolicitudanteproyecto_set.filter(status=True):
                        historialsolicitud.status = False
                        historialsolicitud.save(request)
                    solicitud.save(request)
                    log(u'%s eliminó solicitud de anteproyecto: %s' % (persona, solicitud), request, "del")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    msg = ex.__str__()
                    transaction.set_rollback(True)
                    return JsonResponse(
                        {"result": "bad", "titulo": "Error", "mensaje": u"Error al eliminar el registro. [%s]" % msg,
                         "showSwal": "True", "swalType": "error"})

        if action == 'firmarsolicitud':
            try:
                solicitud = SolicitudAnteproyecto.objects.get(pk=encrypt(request.POST['id']))
                pdf = solicitud.archivo
                #obtener la posicion xy de la firma del doctor en el pdf
                pdfname = SITE_STORAGE + solicitud.archivo.url
                palabras = solicitud.persona.nombre_completo()
                documento = fitz.open(pdfname)
                numpaginafirma = int(documento.page_count)-1
                with fitz.open(pdfname) as document:
                    words_dict = {}
                    for page_number, page in enumerate(document):
                        if page_number == numpaginafirma:
                            words = page.get_text("blocks")
                            words_dict[0] = words
                valor = None
                for cadena in words_dict[0]:
                    if palabras in cadena[4]:
                        valor = cadena
                if valor:
                    # Ubicación vertical de la firma
                    y = 5000 - int(valor[3]) - 4140
                else:
                    solicitud.estado = 4
                    solicitud.save(request)
                    # Guardar historial
                    historial = HistorialSolicitudAnteproyecto(solicitudanteproyecto_id=solicitud.id)
                    historial.save(request)
                    historial.estado = 4
                    historial.archivo = solicitud.archivo
                    historial.observacion = 'El nombre del solicitante en la firma del anteproyecto es incorrecto.'
                    historial.persona = persona
                    historial.fecha = datetime.now()
                    historial.save(request)
                    messages.warning(request, f"Alerta: { historial.observacion } Se ha rechazado.")
                    return JsonResponse({"result": "errornombre"})
                #fin obtener posicion
                firma = request.FILES["firma"]
                passfirma = request.POST['palabraclave']
                txtFirmas = json.loads(request.POST['txtFirmas'])
                if not txtFirmas:
                    return JsonResponse({"result": "bad", "mensaje": u"No se ha podido seleccionar la ubicación de la firma"})
                generar_archivo_firmado = io.BytesIO()
                x = txtFirmas[-1]
                datau, datas = firmar(request, passfirma, firma, pdf, numpaginafirma, x["x"], y, x["width"], x["height"])
                if not datau:
                    return JsonResponse({"result": "bad", "mensaje": f"{datas}"})
                generar_archivo_firmado.write(datau)
                generar_archivo_firmado.write(datas)
                generar_archivo_firmado.seek(0)
                extension = pdf.name.split('.')
                tam = len(extension)
                exte = extension[tam - 1]
                nombrefile_ = remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(pdf.name)).replace('-', '_').replace('.pdf', '')
                _name = f'anteproyecto_{str(solicitud.id)}_{datetime.now().strftime("%Y%m%d_%H%M%S%f")}'
                file_obj = DjangoFile(generar_archivo_firmado, name=f"{_name}_firmado.pdf")
                solicitud.archivo = file_obj
                solicitud.estado = 2
                solicitud.save(request)
                # Guardar historial
                historial = HistorialSolicitudAnteproyecto(solicitudanteproyecto_id=solicitud.id)
                historial.fecha = datetime.now()
                historial.estado = 2
                historial.archivo = solicitud.archivo
                historial.observacion = 'Solicitud firmada mediante SGA.'
                historial.persona = persona
                historial.save(request)
                messages.success(request, f'Solicitud firmada con éxito')
                log(u'Firmó la solicitud: {} - {}'.format(nombrefile_, solicitud.persona), request, "firmarsolicitud")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error: %s"%ex})

        elif action == 'consultarcomponentes':
            try:
                # Falta validaciones
                lista = []
                config = ConfigTipoAnteComponenteApre.objects.filter(tipoanteproyecto_id=request.POST['id'], vigente=True, status=True).order_by('-id').distinct().first().componentesaprendizajes.all()
                for dato in config:
                    lista.append([dato.id, dato.descripcion])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        if 'action' in request.GET:

            data['action'] = action = request.GET['action']

            if action == 'addsolicitud':
                try:
                    # Valido que haya una configuración vigente de requisitos y componentes de aprendizaje para el tipo de anteproyecto seleccionado
                    data['title'] = u'Agregar solicitud de anteproyecto'
                    form = SolicitudAnteproyectoForm()
                    # Cargar sólo los tipos de anteproyectos configurados o vigentes
                    form.cargartipoanteproyecto_vig()
                    data['componentes'] = ComponenteAprendizaje.objects.filter(status=True).order_by('id')
                    # data['criteriosnac'] = CriterioPonencia.objects.filter(status=True, tipoponencia=1, vigente=True).order_by('orden')
                    # data['criteriosint'] = CriterioPonencia.objects.filter(status=True, tipoponencia=2, vigente=True).order_by('orden')
                    # data['convocatoria'] = ConvocatoriaPonencia.objects.get(pk=int(encrypt(request.GET['idc'])))
                    # data['idc'] = request.GET['idc']
                    data['form'] = form
                    return render(request, "pro_solicitudanteproyecto/addsolicitudanteproyecto.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})


            elif action == 'editsolicitud':
                try:
                    pass
                    # Valido si puede editar
                    # if not solicitud.puede_editar():
                    #     return JsonResponse(
                    #         {"result": "bad", "titulo": "Atención!!!", "mensaje": f"Acción no permitida, debido al estado de la solicitud.",
                    #          "showSwal": "True", "swalType": "warning"})
                except Exception as ex:
                    pass

            elif action == 'firmarsolicitud':
                try:
                    data = {}
                    data['solicitud'] = solicitud = SolicitudAnteproyecto.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['titulo'] = solicitud.tema
                    template = get_template("pro_solicitudanteproyecto/modal/firmarsolicitud.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'historial':
                try:
                    title = u'Historial de solicitud de anteproyecto'
                    solicitud = SolicitudAnteproyecto.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['solicitud'] = solicitud
                    data['historial'] = solicitud.historialsolicitudanteproyecto_set.filter(status=True).order_by('id')
                    template = get_template("pro_solicitudanteproyecto/modal/historialsolicitud.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': title})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'generarpdf':
                try:
                    solicitudanteproyecto = SolicitudAnteproyecto.objects.get(status=True, pk=int(encrypt(request.GET['id'])))
                    generarpdf_solicitud(request, solicitudanteproyecto, data, dominio_sistema)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)

        else:
            try:
                data['title'] = u'Solicitud de anteproyectos'
                search, filtro, url_vars, fechasrango, hora = request.GET.get('s', '').strip() , Q(status=True, persona=persona), '', request.GET.get('fechas', '').strip(), request.GET.get('hora', '').strip()
                if search:
                    filtro = filtro & (Q(detallejornadaimpresora__impresora__impresora__codigotic__icontains=search) |
                                       Q(detallejornadaimpresora__impresora__impresora__codigointerno__icontains=search) |
                                       Q(detallejornadaimpresora__impresora__impresora__codigogobierno__icontains=search)
                                       )
                    url_vars += '&s=' + search
                    data['s'] = search

                if fechasrango:
                    try:
                        fechasrango = fechasrango.split(' - ')
                        desde = datetime.strptime(fechasrango.__getitem__(0), '%d-%m-%Y').date()
                        hasta = datetime.strptime(fechasrango.__getitem__(1), '%d-%m-%Y').date()
                        filtro = filtro & (Q(fechaagendada__range=[desde, hasta]))
                        data['fechasrango'] = fechasrango = f"{desde.strftime('%d-%m-%Y')} - {hasta.strftime('%d-%m-%Y')}"
                        url_vars += '&fechas=' + fechasrango
                    except Exception as ex:
                        messages.error(request, u"Formato de fecha inválida. No se consideró en la búsqueda.")

                if hora:
                    hora= datetime.strptime(hora, '%H:%M').time()
                    filtro = filtro & (Q(horainicio__lte=hora, horafin__gte=hora))
                    data['hora'] = hora = hora.strftime('%H:%M')
                    url_vars += '&hora=' + hora

                # listado = SolicitudAnteproyecto.objects.filter(filtro).order_by('estado', '-id')
                listado = SolicitudAnteproyecto.objects.filter(filtro).order_by('-fecha', 'estado')
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
                data['listado'] = page.object_list
                data['listcount'] = len(listado)
                data['tipoanteproyecto_vig'] = tipoanteproyecto_vig()
                request.session['viewactivo'] = 1
                return render(request, 'pro_solicitudanteproyecto/viewsolicitudanteproyecto.html', data)
            except Exception as ex:
                return render({'result': False, 'mensaje': '{}'.format(ex)})


# Función que genera el pdf de la solicitud de anteproyecto
def generarpdf_solicitud(request, solicitudanteproyecto, data, dominio_sistema):
    try:
        # solicitudanteproyecto = SolicitudAnteproyecto.objects.get(status=True, pk=int(encrypt(request.GET['id'])))
        # Generar anteproyecto pdf
        data['solicitud'] = solicitudanteproyecto

        data["DOMINIO_DEL_SISTEMA"] = dominio_sistema
        fechaactual = datetime.now()
        data['version'] = version = fechaactual.strftime('%Y%m%d_%H%M%S%f')
        name = f'anteproyecto_{str(solicitudanteproyecto.id)}_{fechaactual.strftime("%Y%m%d_%H%M%S%f")}_{str(solicitudanteproyecto.get_estado_display().lower())}'
        directory = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'anteproyectos'))
        # rutapdf = directory + '/' + name + '.pdf'
        rutapdf = f"{directory}/{name}.pdf"
        try:
            os.stat(directory)
        except:
            os.mkdir(directory)
        # if os.path.isfile(rutapdf):
        #     os.remove(rutapdf)
        valida = conviert_html_to_pdfsave_anteproyecto(
            'pro_solicitudanteproyecto/anteproyecto_pdf.html',
            {'pagesize': 'A4', 'data': data},
            name + '.pdf',
            'anteproyectos'
        )
        solicitudanteproyecto.archivo = 'qrcode/anteproyectos/' + name + '.pdf'
        solicitudanteproyecto.estado = 1
        solicitudanteproyecto.save(request)
        # Generar anteproyecto pdf
    except Exception as ex:
        messages.error(request, str(ex))

def tipoanteproyecto_vig():
    tiposanteproyecto_vig = []
    for tipoanteproyecto in TipoAnteproyecto.objects.filter(status=True):
        if tipoanteproyecto.configtipoanteproyectorequisito_set.filter(status=True, vigente=True) and tipoanteproyecto.configtipoantecomponenteapre_set.filter(status=True, vigente=True):
            tiposanteproyecto_vig.append(tipoanteproyecto.id)
    return tiposanteproyecto_vig