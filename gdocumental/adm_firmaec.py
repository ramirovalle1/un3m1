import base64
import json
import io
import os
from datetime import datetime

from dateutil.relativedelta import relativedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from decorators import secure_module
# from gdocumental.forms import DocumentoFirmadoForm, EnviarArchivoForm
from core.firmar_documentos_ec_descentralizada import qrImgFirma, getFirmaEcLink, get_archivo_firmado_base64
# from gdocumental.models import DocumentoFirmado, UsuarioFirma, ArchivoFirmaEc
# from notificaciones.notificacion_config import enviar_not_push
from sga.commonviews import adduserdata
from django.core.files.base import ContentFile

from sga.models import Persona
from sga.tasks import send_mail


@login_required
# @secure_module
def view(request):
    data = {'title': f"Firmar Documentos Electrónicos"}
    adduserdata(request, data)
    persona = data['persona']
    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'generar_link_firma':
                archivo = request.FILES.get("archivo") or request.POST['archivo']
                firma_json = json.loads(request.POST["firma_json"])
                razon = request.POST.get("razon") or ""
                codigoDocumentoFirmado = request.POST.get('codigoDocumentoFirmado')
                fecha_expira = str(datetime.utcnow() + relativedelta(minutes=4))
                firma_ec_link, nombre_documento = getFirmaEcLink(
                    persona.cedula, archivo if type(archivo).__name__.lower() == "str" else base64.b64encode(archivo.read()).decode(), int(firma_json["numPage"]) + 1,
                    int(firma_json["x"]), int(firma_json["y"]), razon=razon
                )
                archivoBase64, arch_codi = get_archivo_firmado_base64(codigoDocumentoFirmado)
                return JsonResponse(
                    {
                        "firma_ec_link": firma_ec_link,
                        "codigoDocumentoFirmado": nombre_documento,
                        "archivoBase64": archivoBase64,
                        "fecha_expira": fecha_expira
                    }
                )
            if action == 'get_archivo_base64':
                codigoDocumentoFirmado = request.POST['codigoDocumentoFirmado']
                archivoBase64, arch_codi = get_archivo_firmado_base64(codigoDocumentoFirmado)
                return JsonResponse(
                    {
                        "archivoBase64": archivoBase64
                    }
                )
            if action == 'guardar_archivo_firmado':
                documento_id = request.POST.get('documento_id') or 0
                documentoExistente = DocumentoFirmado.objects.filter(id=documento_id).first()
                usuarioFirma = UsuarioFirma.objects.filter(user_firma_id=request.user.id, documento_id=documento_id).first()
                obj = documentoExistente or DocumentoFirmado()
                codigoDocumentoFirmado = request.POST["codigoDocumentoFirmado"]
                cantidad_veces_firmado = int(request.POST["cantidad_veces_firmado"])

                archivoBase64, arch_codi = ArchivoFirmaEc.get_archivo_firmado_base64(codigoDocumentoFirmado)

                filename = request.POST["filename"]
                razon = request.POST["razon"]
                archivo_firmado = base64.b64decode((archivoBase64))
                old_archivo_firmado_path = obj and obj.archivo and str(obj.archivo.path)
                obj.archivo = ContentFile(archivo_firmado, name="{}-signed.pdf".format(filename.replace(".pdf", "")))
                obj.save(request)
                usuarioFirma = usuarioFirma or UsuarioFirma(
                    documento_id=obj.id,
                    user_firma_id=request.user.id,
                    veces_firmado=0
                )
                usuarioFirma.fecha_firma = datetime.now()
                usuarioFirma.arch_nombre = codigoDocumentoFirmado
                usuarioFirma.arch_codi = arch_codi
                usuarioFirma.firmado = True
                usuarioFirma.razon = razon
                usuarioFirma.veces_firmado = usuarioFirma.veces_firmado + cantidad_veces_firmado
                usuarioFirma.save(request)
                messages.success(request, "Archivo firmado correctamente")
                if old_archivo_firmado_path:
                    os.remove(old_archivo_firmado_path)
                return ok_json({"id": obj.id, "area_modulo": obj.area_modulo})
            if action == 'enviar_a_firmar':
                form = EnviarArchivoForm(request.POST, request.FILES)
                documento_id = request.POST.get("documento_id")
                if documento_id:
                    del form.fields["archivo"]
                if form.is_valid():
                    if documento_id:
                        obj = DocumentoFirmado.objects.get(id=documento_id)
                    else:
                        obj = DocumentoFirmado()
                        obj.archivo = form.files["archivo"]
                        obj.save(request)
                    enviado_a_firmar = enviar_a_firmar(form.cleaned_data["user_firma"].id, form.cleaned_data["mensaje"], obj, request)
                    if enviado_a_firmar:
                        messages.success(request, "Archivo enviado correctamente")
                        return ok_json()
                    else:
                        return bad_json(error=1)
                else:
                    return bad_json(error=1)
        except ValueError as ex:
            v = str(ex)
            if "invalid" in v.lower():
                v = "La contraseña o certificado no son válidos"
            return bad_json(mensaje=v)
        except Exception as ex:
            return bad_json(error=3)
    elif request.method == 'GET':
        data["action"] = action = request.GET.get('action')
        if action == 'firmararchivo':
            data['form'] = DocumentoFirmadoForm()
            qr = qrImgFirma(request, persona, "png", paraMostrar=True)
            data["qrBase64"] = qr[0]
            return render(request, 'firmaelectronica/form.html', data)
        if action == 'firmar_documento_enviado':
            data["title"] = "Firmar documento enviado"
            data["firmauser_id"] = firmauser_id = request.GET["firmauser_id"]
            data["documento_id"] = documento_id = request.GET["documento_id"]
            obj = UsuarioFirma.objects.get(
                id=firmauser_id,
                documento_id=documento_id,
                user_firma=request.user.id
            )
            documento = obj.documento
            data["archivo_url"] = documento.archivo.url
            data["archivo_base64"] = documento.archivo_base64
            data["archivo_base64_filename"] = os.path.basename(documento.archivo.path)
            data["mensaje_firma"] = obj.mensaje
            form = DocumentoFirmadoForm(
                instance=documento, initial={'razon': obj.razon}
            )
            del form.fields["archivo"]
            data['form'] = form
            qr = qrImgFirma(request, persona, "png", paraMostrar=True)
            data["qrBase64"] = qr[0]
            return render(request, 'firmaelectronica/form.html', data)
        if action == 'enviar_a_firmar':
            data["documento_id"] = documento_id = request.GET.get("documento_id")
            form = EnviarArchivoForm()
            if documento_id:
                data['documentoObj'] = documentoObj = DocumentoFirmado.objects.get(id=documento_id)
                del form.fields["archivo"]
            data['form'] = form
            data['title'] = "Enviar a firmar un documento"
            return render(request, 'firmaelectronica/enviar_a_firmar.html', data)
        if action == 'ver_firmas':
            documento_id = request.GET["documento_id"]
            data['documentoObj'] = documentoObj = DocumentoFirmado.objects.get(id=documento_id)
            data["firmas"] = documentoObj.usuariofirma_set.all().order_by("pk")
            data['title'] = "Firmas"
            return render(request, 'firmaelectronica/ver_firmas.html', data)

        qr = qrImgFirma(request, persona, "png", paraMostrar=True)
        data["qrBase64"] = qr[0]
        return render(request, 'firmaelectronica/form.html', data)