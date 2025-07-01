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
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, HttpResponseNotFound
from django.template.loader import get_template
from django.shortcuts import render, redirect
from pdf2image import convert_from_bytes

from core.firmar_documentos_superuser import firmarfecha, generarfirmaimagenfecha
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
    # if not request.user.is_staff:
    #     return redirect('/')
    global folder_pdf, qrname
    data = {}
    hoy = datetime.now()
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'firmardocumento':
            try:
                pdf = request.FILES["pdf"]
                firma = request.FILES["firma"]
                passfirma = request.POST['palabraclave']
                fecha, hora = request.POST['fecha'], request.POST['hora']
                fecha_firmar = datetime.strptime(f'{fecha} {hora}:{datetime.now().time().second}', '%Y-%m-%d %H:%M:%S')
                txtFirmas = json.loads(request.POST['txtFirmas'])
                if not txtFirmas:
                    messages.error(request, "Error: Debe seleccionar ubicación de la firma")
                    return redirect(request.path)
                generar_archivo_firmado = io.BytesIO()
                x = txtFirmas[-1]
                datau, datas = firmarfecha(request, fecha_firmar, passfirma, firma, pdf, x["numPage"], x["x"], x["y"], x["width"], x["height"])
                if not datau:
                    messages.error(request, f"Error: {datas}")
                    return redirect(request.path)
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
                log(u'Firmo Documento: {}'.format(nombrefile_), request, "add")
                return response
            except Exception as ex:
                messages.error(request, "Error: {}".format(ex))
                return redirect(request.path)
                # return JsonResponse({'result': True, "mensaje": "Error: {}".format(ex)}, safe=False)

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
                    return conviert_html_to_pdf('adm_archivosdepartamentales/firma/vistapreviafirma.html',  {'data': data})
                    # if valida:
                    #     images = convert_from_bytes(valida.content,
                    #                                 output_folder=folder_images,
                    #                                 poppler_path=SITE_POPPLER,
                    #                                 output_file=f'{qrname}_firma',
                    #                                 fmt="png")#dpi=95, size=(150, 45)
                    #     return JsonResponse({"result": "ok", "image": images[0].filename, "mensaje": u"Se genero correctamente la firma electronica.", 'url': f'{url_path}/'+'/'.join(['media', 'adm_archivosdepartamentales', 'ejemplo', 'participantes', 'participacion', f'{qrname}.png' ])})
                except Exception as ex:
                    msg = '{} Linea:{}'.format(ex, sys.exc_info()[-1].tb_lineno)
                    return JsonResponse({"result": "bad", "mensaje": f"Error: {msg} f'{folder_pdf}{qrname}.pdf'"})
        data['title'] = f'Firmar documentos'
        return render(request, 'adm_firmardocumentos/firmardocumento_superuser.html', data)
