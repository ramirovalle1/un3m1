# -*- coding: latin-1 -*-
import json
import sys
import urllib
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.template.loader import get_template

from decorators import secure_module, last_access
from posgrado.models import HistorialInteresadoProgramaMaestria
from voto.models import SedesElectoralesPeriodo, PersonasSede
from .adm_padronelectoral import generar_qr_padronelectoral
from .commonviews import adduserdata
from .funciones import log, notificacion, generar_nombre, remover_caracteres_especiales_unicode, variable_valor
from .funcionesxhtml2pdf import conviert_html_to_pdf, conviert_html_to_pdf_name_bitacora
from .models import CabPadronElectoral, DetPersonaPadronElectoral, MesasPadronElectoral, ESTADO_JUSTIFICACION, \
    JustificacionPersonaPadronElectoral, HistorialJustificacionPersonaPadronElectoral, SolicitudInformacionPadronElectoral
from sga.templatetags.sga_extras import encrypt
from .forms import JustificativoFaltaVotacionVirtual, JustificativoFaltaVotacionPresencial, DetalleJustificativoForm, SolicitudInformacionPadronElectoralForm, SedesElectoralesPersonaForm


@login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']
    perfilprincipal = request.session['perfilprincipal']
    # if not perfilprincipal.es_profesor():
    #     return HttpResponseRedirect("/?info=Solo los perfiles de profesores pueden ingresar al modulo.")
    data['profesor'] = profesor = perfilprincipal.profesor

    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'add':
                try:
                    with transaction.atomic():
                        newfile = None
                        id = int(request.POST['id'])
                        virtual = False
                        form = JustificativoFaltaVotacionPresencial(request.POST, request.FILES)
                        if form.is_valid():
                            filtro = DetPersonaPadronElectoral.objects.get(pk=id)
                            nombre_persona = remover_caracteres_especiales_unicode(filtro.persona.__str__().lower().replace(' ', '_')).lower().replace(' ', '_')
                            justificacion = JustificacionPersonaPadronElectoral(inscripcion=filtro, observacion=form.cleaned_data['observacion'].upper())
                            validador = False
                            cantdocumentos = 0
                            if 'certificado_medico' in request.FILES:
                                validador = True
                                cantdocumentos += 1
                                newfile = request.FILES['certificado_medico']
                                extension = newfile._name.split('.')
                                tam = len(extension)
                                exte = extension[tam - 1]
                                if newfile.size > 4194304:
                                    return JsonResponse({"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                                if exte in ['pdf', 'jpg', 'jpeg', 'png', 'jpeg', 'peg']:
                                    newfile._name = generar_nombre("certificado_medico_{}".format(nombre_persona), newfile._name)
                                else:
                                    transaction.set_rollback(True)
                                    return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})
                                justificacion.certificado_medico = newfile
                            if 'certificado_upc' in request.FILES:
                                validador = True
                                cantdocumentos += 1
                                newfile = request.FILES['certificado_upc']
                                extension = newfile._name.split('.')
                                tam = len(extension)
                                exte = extension[tam - 1]
                                if newfile.size > 4194304:
                                    return JsonResponse({"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                                if exte in ['pdf', 'jpg', 'jpeg', 'png', 'jpeg', 'peg']:
                                    newfile._name = generar_nombre("certificado_upc_{}".format(nombre_persona), newfile._name)
                                else:
                                    transaction.set_rollback(True)
                                    return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})
                                justificacion.certificado_upc = newfile
                            if 'certificado_defuncion' in request.FILES:
                                validador = True
                                cantdocumentos += 1
                                newfile = request.FILES['certificado_defuncion']
                                extension = newfile._name.split('.')
                                tam = len(extension)
                                exte = extension[tam - 1]
                                if newfile.size > 4194304:
                                    return JsonResponse({"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                                if exte in ['pdf', 'jpg', 'jpeg', 'png', 'jpeg', 'peg']:
                                    newfile._name = generar_nombre("certificado_defuncion_{}".format(nombre_persona), newfile._name)
                                else:
                                    transaction.set_rollback(True)
                                    return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})
                                justificacion.certificado_defuncion = newfile
                            if 'certificado_licencia' in request.FILES:
                                validador = True
                                cantdocumentos += 1
                                newfile = request.FILES['certificado_licencia']
                                extension = newfile._name.split('.')
                                tam = len(extension)
                                exte = extension[tam - 1]
                                if newfile.size > 4194304:
                                    return JsonResponse({"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                                if exte in ['pdf', 'jpg', 'jpeg', 'png', 'jpeg', 'peg']:
                                    newfile._name = generar_nombre("certificado_licencia_{}".format(nombre_persona), newfile._name)
                                else:
                                    transaction.set_rollback(True)
                                    return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})
                                justificacion.certificado_licencia = newfile
                            if 'certificado_alterno' in request.FILES:
                                validador = True
                                cantdocumentos += 1
                                newfile = request.FILES['certificado_alterno']
                                extension = newfile._name.split('.')
                                tam = len(extension)
                                exte = extension[tam - 1]
                                if newfile.size > 4194304:
                                    return JsonResponse({"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                                if exte in ['pdf', 'jpg', 'jpeg', 'png', 'jpeg', 'peg']:
                                    newfile._name = generar_nombre("certificado_alterno_{}".format(nombre_persona), newfile._name)
                                else:
                                    transaction.set_rollback(True)
                                    return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})
                                justificacion.certificado_alterno = newfile
                            if validador and cantdocumentos == 1:
                                filtro.puede_justificar = False
                                filtro.save(request)
                                justificacion.tipo = 2
                                justificacion.save(request)
                            else:
                                transaction.set_rollback(True)
                                return JsonResponse({"result": True, "mensaje": "Debe subir un solo documento de acuerdo a la categoría escogida."}, safe=False)

                            return JsonResponse({"result": False, 'to': "{}?action=justificacion&id={}".format(request.path, encrypt(filtro.pk))}, safe=False)
                        else:
                            transaction.set_rollback(True)
                            return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

            elif action == 'addsolicitud':
                try:
                    with transaction.atomic():
                        cab = CabPadronElectoral.objects.get(pk=int(request.POST['id']))
                        form = SolicitudInformacionPadronElectoralForm(request.POST, request.FILES)
                        if form.is_valid():
                            solicitud = SolicitudInformacionPadronElectoral(persona=persona,
                                                                            cab=cab,
                                                                            estados=0,
                                                                            tipo=form.cleaned_data['tipo'],
                                                                            observacion=form.cleaned_data['observacion'])
                            solicitud.save(request)
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            transaction.set_rollback(True)
                            return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

            elif action == 'cambiarsede':
                try:
                    with transaction.atomic():
                        filtro = PersonasSede.objects.get(pk=int(request.POST['id']))
                        form = SedesElectoralesPersonaForm(request.POST, request.FILES)
                        if form.is_valid():
                            filtro.sede = form.cleaned_data['sede']
                            filtro.canton = form.cleaned_data['sede'].canton
                            filtro.save(request)
                            log(u'Cambio de sede electoral: %s' % filtro, request, "change")
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            transaction.set_rollback(True)
                            return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'add':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['filtro'] = filtro = DetPersonaPadronElectoral.objects.get(pk=id)
                    form = JustificativoFaltaVotacionPresencial()
                    data['form2'] = form
                    template = get_template("alu_justificacionsufragio/formjustificacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'cambiarsede':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['filtro'] = filtro = PersonasSede.objects.get(pk=id)
                    form = SedesElectoralesPersonaForm({'sede': filtro.sede})
                    data['form2'] = form
                    template = get_template("alu_justificacionsufragio/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addsolicitud':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['filtro'] = filtro = CabPadronElectoral.objects.get(pk=id)
                    form = SolicitudInformacionPadronElectoralForm()
                    data['form2'] = form
                    template = get_template("alu_justificacionsufragio/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'verobservaciones':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = JustificacionPersonaPadronElectoral.objects.get(pk=request.GET['id'])
                    data['detalle'] = detalle = filtro.historialjustificacionpersonapadronelectoral_set.all().order_by('pk')
                    template = get_template("alu_justificacionsufragio/detalleobs.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'justificacion':
                data['title'] = u'Justificación de omisión al sufragío'
                data['id'] = id = int(encrypt(request.GET['id']))
                data['filtro'] = filtro = DetPersonaPadronElectoral.objects.get(pk=id)
                data['estados_justificacion'] = ESTADO_JUSTIFICACION
                data['listado'] = JustificacionPersonaPadronElectoral.objects.filter(status=True, inscripcion=filtro).order_by('-pk')
                return render(request, 'alu_justificacionsufragio/justificar.html', data)

            elif action == 'certificadojustificado':
                try:
                    data['hoy'] = datetime.now()
                    data['filtro'] = filtro = JustificacionPersonaPadronElectoral.objects.get(pk=encrypt(request.GET['pk']))
                    template_pdf = 'adm_padronelectoral/certificado_justificaciondoc.html'
                    return conviert_html_to_pdf(
                        template_pdf,
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'generarqr':
                try:
                    id = int(encrypt(request.GET['id'] ))
                    data['person'] = person = DetPersonaPadronElectoral.objects.get(id=id)
                    data['tittle'] = 'PDF QR Electoral'
                    data['foto'] = person.persona.get_foto()
                    result = generar_qr_padronelectoral(person)
                    if result.get('isSuccess', {}):
                        data['dataqr'] = dataqr = result.get('data', {})
                        data['pdfcodename']  = pdfCodeName = dataqr['pdfname']
                    if variable_valor('PDF_PYTHON_ELECCIONES'):
                        name_file = f'pdfelectoral_{person.persona.cedula}.pdf'
                        resp = conviert_html_to_pdf_name_bitacora('adm_padronelectoral/personaqr_pdf.html',{'data':data}, name_file)
                        if resp[0]:
                            resp[1].seek(0)
                            fil_content = resp[1].read()
                            resp = ContentFile(fil_content)
                        person.pdf.save(f'{name_file.replace(".pdf", "")}.pdf', resp)
                        person.save(request)
                        return conviert_html_to_pdf(
                            'adm_padronelectoral/personaqr_pdf.html',
                            {
                                'pagesize': 'A4',
                                'data': data,
                            }
                        )
                    else:
                        pass
                except Exception as ex:
                    messages.success(request, f"{ex} - {sys.exc_info()[-1].tb_lineno}")

        else:
            try:
                data['title'] = u'Proceso Electoral'
                data['procesoactivo'] = procesoactivo = CabPadronElectoral.objects.filter(status=True, activo=True).first()
                if procesoactivo:
                    data['soliprocesoactivos'] = SolicitudInformacionPadronElectoral.objects.filter(persona=persona, cab=procesoactivo).order_by('-pk')
                data['listvigente'] = DetPersonaPadronElectoral.objects.filter(status=True, persona=persona, cab__activo=True).order_by('-pk')
                data['listpasados'] = DetPersonaPadronElectoral.objects.filter(status=True, persona=persona, cab__activo=False).order_by('-pk')
                data['sedeelectoral'] = PersonasSede.objects.filter(status=True, persona=persona, sede__periodo__activo=True, sede__periodo__confirmacion_sede=True).order_by('-pk')
                return render(request, "alu_justificacionsufragio/view.html", data)
            except Exception as ex:
                pass
