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
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, HttpResponseNotFound, FileResponse
from django.template.loader import get_template
from django.shortcuts import render, redirect
from pdf2image import convert_from_bytes
from unidecode import unidecode

from core.firmar_documentos import firmar, generarfirmaimagen, verificarFirmasPDF
from core.firmar_documentos_ec import JavaFirmaEc
from core.firmar_documentos_ec_descentralizada import qrImgFirma
from decorators import secure_module
from settings import EMAIL_DOMAIN, SITE_STORAGE, SITE_POPPLER, DEBUG
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, generar_nombre, remover_caracteres_especiales_unicode, \
    remover_caracteres_tildes_unicode, puede_realizar_accion
from django.db.models import Q

from sga.funcionesxhtml2pdf import conviert_html_to_pdfsaveqrcertificado_generico, conviert_html_to_pdf
from sga.templatetags.sga_extras import encrypt
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.files import File as DjangoFile

@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
# @last_access
# @transaction.atomic()
def view(request):
    global folder_pdf, qrname
    data = {}
    hoy = datetime.now()
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'firmardocumento':
            try:
                documento_a_firmar = request.FILES["archivo"]
                certificado = request.FILES["firma"]
                contrasenaCertificado = request.POST['palabraclave']
                razon = request.POST['razon'] if 'razon' in request.POST else ''
                jsonFirmas = json.loads(request.POST['txtFirmas'])
                name_documento_a_firmar, extension_documento_a_firmar = os.path.splitext(documento_a_firmar.name)
                extension_certificado = os.path.splitext(certificado.name)[1][1:]
                bytes_certificado = certificado.read()
                if not jsonFirmas:
                    messages.error(request, "Error: Debe seleccionar ubicación de la firma")
                    return redirect(request.path)
                for membrete in jsonFirmas:
                    datau = JavaFirmaEc(
                        archivo_a_firmar=documento_a_firmar, archivo_certificado=bytes_certificado, extension_certificado=extension_certificado,
                        password_certificado=contrasenaCertificado,
                        page=int(membrete["numPage"]), reason=razon, lx=membrete["x"], ly=membrete["y"]
                    ).sign_and_get_content_bytes()
                    documento_a_firmar = io.BytesIO()
                    documento_a_firmar.write(datau)
                    documento_a_firmar.seek(0)
                nombrefile_ = unidecode(name_documento_a_firmar).replace('-', '_').replace('.pdf', '').replace('.', '_')
                _name = generar_nombre(f'{request.user.username}', nombrefile_)
                response = HttpResponse(documento_a_firmar, content_type="application/pdf")
                response['Content-Disposition'] = f'attachment; filename="{nombrefile_}_firmado.pdf"'
                log(u'Firmo Documento: {}'.format(name_documento_a_firmar), request, "add")
                return response
            except Exception as ex:
                messages.error(request, "Error: {}".format(ex))
                return redirect(request.path)

        if action == 'firmardocumentoold':
            try:
                pdf = request.FILES["pdf"]
                firma = request.FILES["firma"]
                passfirma = request.POST['palabraclave']
                txtFirmas = json.loads(request.POST['txtFirmas'])
                if not txtFirmas:
                    messages.error(request, "Error: Debe seleccionar ubicación de la firma")
                    return redirect(request.path)
                    # return JsonResponse({'result': True, "mensaje": "Error: Debe seleccionar ubicación de la firma"}, safe=False)
                generar_archivo_firmado = io.BytesIO()
                x = txtFirmas[-1]
                datau, datas = firmar(request, passfirma, firma, pdf, x["numPage"], x["x"], x["y"], x["width"], x["height"])
                if not datau:
                    messages.error(request, f"Error: {datas}")
                    return redirect(request.path)
                    # return JsonResponse({'result': True, "mensaje": datas}, safe=False)
                generar_archivo_firmado.write(datau)
                generar_archivo_firmado.write(datas)
                generar_archivo_firmado.seek(0)
                extension = pdf._name.split('.')
                tam = len(extension)
                exte = extension[tam - 1]
                nombrefile_ = remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(pdf._name)).replace('-', '_').replace('.pdf', '')
                _name = generar_nombre(f'{request.user.username}', nombrefile_)
                response = HttpResponse(generar_archivo_firmado, content_type="application/pdf")
                response['Content-Disposition'] = f'attachment; filename="{nombrefile_}_firmado.pdf"'
                # messages.success(request, f'Documento firmado con exito')
                log(u'Firmo Documento: {}'.format(nombrefile_), request, "add")
                return response
                # return JsonResponse({"result": False, "mensaje": "Guardado con exito", "response": response}, safe=False)
            except Exception as ex:
                messages.error(request, "Error: {}".format(ex))
                return redirect(request.path)
                # return JsonResponse({'result': True, "mensaje": "Error: {}".format(ex)}, safe=False)

        elif action == 'verificarfirmas':
            try:
                archivo = request.FILES['archivo_verificar']
                valido, msg, diccionario = verificarFirmasPDF(archivo)
                return JsonResponse({'result': True, 'context': diccionario})
            except Exception as ex:
                return JsonResponse({'result': False, "mensaje": 'Error: {}'.format(ex)}, safe=False)
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
            if action == 'firmavistaprevia':
                try:
                    folder_pdf = os.path.join(os.path.join(SITE_STORAGE, 'media', 'firmaelectronicapdf', ''))
                    folder_images = os.path.join(os.path.join(SITE_STORAGE, 'media', 'firmaelectronicaimages', ''))
                    os.makedirs(folder_pdf, exist_ok=True)
                    os.makedirs(folder_images, exist_ok=True)
                    qrname = 'qr_firma_{}'.format(persona.id)
                    rutapdf = '{}{}.pdf'.format(folder_pdf, qrname)
                    rutaimg = '{}{}.png'.format(folder_images, qrname)
                    url = pyqrcode.create(f'FIRMADO POR: {persona.__str__()}\nFECHA: {datetime.now()}\nVALIDAR CON: www.firmadigital.gob.ec\nFIRMADO EN: sga.unemi.edu.ec')
                    url.png('{}/{}.png'.format(folder_pdf, qrname), 16, '#000000')#'#1C3247'
                    url_path = request.build_absolute_uri('/')[:-1].strip("/")
                    data['url_path'] = url_path
                    data['qrname'] = '{}'.format(qrname)
                    data['persona'] = persona
                    valida = conviert_html_to_pdf('adm_archivosdepartamentales/firma/vistapreviafirma.html',  {'data': data})
                    if valida:
                        images = convert_from_bytes(valida.content,
                                                    output_folder=folder_images,
                                                    poppler_path=SITE_POPPLER,
                                                    output_file=f'{qrname}_firma',
                                                    fmt="png")#dpi=95, size=(150, 45)
                        return JsonResponse({"result": "ok", "image": images[0].filename, "mensaje": u"Se genero correctamente la firma electronica.", 'url': f'{url_path}/'+'/'.join(['media', 'adm_archivosdepartamentales', 'ejemplo', 'participantes', 'participacion', f'{qrname}.png' ])})
                except Exception as ex:
                    msg = '{} Linea:{}'.format(ex, sys.exc_info()[-1].tb_lineno)
                    return JsonResponse({"result": "bad", "mensaje": f"Error: {msg} f'{folder_pdf}{qrname}.pdf'"})
        try:
            data['title'] = f'Firmar documentos'
            qr = qrImgFirma(request, persona, "png", paraMostrar=True)
            data["qrBase64"] = qr[0]
            return render(request, 'adm_firmardocumentos/firmardocumento.html', data)
        except Exception as ex:
            return JsonResponse({'result': False, 'ex': f"{ex} - {sys.exc_info()[-1].tb_lineno}"})
