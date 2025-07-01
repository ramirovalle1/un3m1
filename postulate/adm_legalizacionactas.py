import json
import os
import random
import sys

# decoradores
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.template.loader import get_template
from unidecode import unidecode

from core.firmar_documentos import obtener_posicion_x_y_saltolinea
from core.firmar_documentos_ec import JavaFirmaEc
from decorators import last_access, secure_module

from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.db.models.query_utils import Q
from datetime import datetime,date
from django.core.files import File as DjangoFile
from postulate.models import Partida, PartidaTribunal, PersonaAplicarPartida, ActaPartida, HistorialActaFirma
from sagest.funciones import encrypt_id
from settings import MEDIA_ROOT
from sga.commonviews import adduserdata
from sga.funciones import log, MiPaginador, numero_a_letras,generar_nombre, notificacion
from sga.funcionesxhtml2pdf import  conviert_html_to_pdf_save_file_model
import io

@login_required(redirect_field_name='ret', login_url='/loginpostulate')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    perfilprincipal = request.session['perfilprincipal']
    persona = request.session['persona']
    periodo = request.session['periodo']
    data['currenttime'] =currentime= datetime.now()
    data['hoy'] = hoy = currentime.date()
    data['perfil'] = persona.mi_perfil()
    data['periodo'] = periodo

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'firmaracta':
            try:
                certificado = request.FILES["firma"]
                contrasenaCertificado = request.POST['palabraclave']
                razon = request.POST['razon'] if 'razon' in request.POST else ''
                extension_certificado = os.path.splitext(certificado.name)[1][1:]
                bytes_certificado = certificado.read()
                acta = ActaPartida.objects.get(id=encrypt_id(request.POST['id']))
                firmas = []
                personatribunal = acta.persona_tribunal(persona)
                if not personatribunal:
                    raise NameError('Usted no es parte del tribunal que requiere firmar el acta')
                archivo_ = archivo_original = acta.get_documento()
                cargo = personatribunal.get_cargos_display()
                palabras = f'{persona} {cargo}'
                x, y, numPage = obtener_posicion_x_y_saltolinea(archivo_.url, palabras, False, True, acta.tipo != 1)
                if not x or not y:
                    raise NameError('No se encontro ubicación de la firma')
                firmas.append({'x': x, 'y': y, 'numPage': numPage})
                for membrete in firmas:
                    datau = JavaFirmaEc(
                        archivo_a_firmar=archivo_, archivo_certificado=bytes_certificado, extension_certificado=extension_certificado,
                        password_certificado=contrasenaCertificado,
                        page=int(membrete["numPage"]), reason=razon, lx=membrete["x"], ly=membrete["y"]
                    ).sign_and_get_content_bytes()
                    archivo_ = io.BytesIO()
                    archivo_.write(datau)
                    archivo_.seek(0)

                tipo = unidecode(acta.get_tipo_display().lower().replace(' ', '_'))
                _name = generar_nombre(f'{acta.id}_{tipo}_', '')
                file_obj = DjangoFile(archivo_, name=f"{_name}.pdf")


                historial = HistorialActaFirma(acta=acta,
                                                archivo_original=archivo_original,
                                                archivo_firmado=file_obj,
                                                personatribunal=personatribunal,
                                                cantidadfirmas=len(firmas),
                                                estado=3)
                historial.save(request)

                acta.archivo = file_obj
                acta.estado = 3 if acta.firmado_all() else 2
                acta.save(request)
                log(u'Edito Acta: {}'.format(acta), request, "edit")

                # titulo = 'Certificado de paz y salvo firmado por responsables exitosamente.'
                # observacion = f'Estimado/a {acta.persona.nombre_completo_minus()} su certificado de paz y salvo fue firmado por todos los responsables a cargo,' \
                #               f'por favor revise su certificado y proceda a firmarlo.'
                # notificacion(titulo, observacion, acta.persona, None, '/th_hojavida?action=acta', acta.pk, 2, 'sagest', acta, request)

                return JsonResponse({"result": False, "mensaje": "Guardado con exito", }, safe=False)
            except Exception as ex:
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                textoerror = '{} Linea:{}'.format(ex, sys.exc_info()[-1].tb_lineno)
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error: %s" % ex})

        if action == 'firmaractamasiva':
            try:
                certificado = request.FILES["firma"]
                contrasenaCertificado = request.POST['palabraclave']
                razon = request.POST['razon'] if 'razon' in request.POST else ''
                extension_certificado = os.path.splitext(certificado.name)[1][1:]
                bytes_certificado = certificado.read()
                actas = ActaPartida.objects.filter(status=True, partida__partidatribunal__persona=persona).exclude(estado=3).order_by('id').distinct()
                for acta in actas:
                    firmas = []
                    personatribunal = acta.persona_tribunal(persona)
                    if personatribunal and acta.puede_firmar(persona):
                        archivo_ = archivo_original = acta.get_documento()
                        cargo = personatribunal.get_cargos_display()
                        palabras = f'{persona} {cargo}'
                        x, y, numPage = obtener_posicion_x_y_saltolinea(archivo_.url, palabras, False, True, acta.tipo != 1)
                        if x and y:
                            firmas.append({'x': x, 'y': y, 'numPage': numPage})
                        if firmas:
                            try:
                                for membrete in firmas:
                                    datau = JavaFirmaEc(
                                        archivo_a_firmar=archivo_, archivo_certificado=bytes_certificado, extension_certificado=extension_certificado,
                                        password_certificado=contrasenaCertificado,
                                        page=int(membrete["numPage"]), reason=razon, lx=membrete["x"], ly=membrete["y"]
                                    ).sign_and_get_content_bytes()
                                    archivo_ = io.BytesIO()
                                    archivo_.write(datau)
                                    archivo_.seek(0)

                                tipo = unidecode(acta.get_tipo_display().lower().replace(' ', '_'))
                                _name = generar_nombre(f'{acta.id}_{tipo}_', '')
                                file_obj = DjangoFile(archivo_, name=f"{_name}.pdf")


                                historial = HistorialActaFirma(acta=acta,
                                                                archivo_original=archivo_original,
                                                                archivo_firmado=file_obj,
                                                                personatribunal=personatribunal,
                                                                cantidadfirmas=len(firmas),
                                                                estado=3)
                                historial.save(request)

                                acta.archivo = file_obj
                                acta.estado = 3 if acta.firmado_all() else 2
                                acta.save(request)
                                log(u'Edito Acta: {}'.format(acta), request, "edit")
                            except Exception as ex:
                                if f'{ex}' == 'Certificado no es válido':
                                    raise NameError(f'{ex}')
                return JsonResponse({"result": False, "mensaje": "Guardado con exito", }, safe=False)
            except Exception as ex:
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                textoerror = '{} Linea:{}'.format(ex, sys.exc_info()[-1].tb_lineno)
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error: %s" % ex})

        if action == 'delacta':
            try:
                acta = ActaPartida.objects.get(id=encrypt_id(request.POST['id']))
                acta.status = False
                acta.save(request)
                log(f'Elimino acta de constatación {acta}', request, 'del')
                return JsonResponse({"error": False, "mensaje": "Guardado con éxito", }, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                textoerror = '{} Linea:{}'.format(ex, sys.exc_info()[-1].tb_lineno)
                return JsonResponse({"error": True, "mensaje": u"Error: %s" % textoerror})

        if action == 'recalcularestado':
            try:
                actas = ActaPartida.objects.filter(status=True, estado=2)
                for acta in actas:
                    acta.estado = 3 if acta.firmado_all() else 2
                    acta.save(request)
                    log(u'Cambio estado de acta: %s' % acta, request, "edit")
                return JsonResponse({"error": False, "mensaje": "Guardado con éxito", }, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                textoerror = '{} Linea:{}'.format(ex, sys.exc_info()[-1].tb_lineno)
                return JsonResponse({"error": True, "mensaje": u"Error: %s" % textoerror})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        # fin get
        adduserdata(request, data)
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
            if action == 'firmaracta':
                try:
                    data['id'] = encrypt_id(request.GET['id'])
                    data['b4'] = True
                    # data['info_mensaje'] = f'Nota: Una vez seleccionado en firmar se firmara el certificado en la parte inferior del documneto.'
                    template = get_template("formfirmaelectronicamasiva.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': f'{ex}'})

            elif action == 'firmaractamasiva':
                try:
                    data['b4'] = True
                    actas = ActaPartida.objects.filter(status=True, estado__in=[1,2,4])
                    cont=0
                    for a in actas:
                        cont+= 1 if a.puede_firmar(persona) else 0
                    if cont == 0:
                        raise NameError('No dispone de actas por firmar')
                    data['info_mensaje'] = f'Nota: Esta por firmar {cont} actas que se encuentran pendientes de firmar a su nombre'
                    template = get_template("formfirmaelectronicamasiva.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': f'{ex}'})

            elif action == 'historialfirmas':
                try:
                    data['acta'] = acta = ActaPartida.objects.get(id=encrypt_id(request.GET['id']))
                    data['historial'] = acta.historial_firmas_all().order_by('-fecha_creacion')
                    template = get_template('postulate/adm_legalizacionactas/historialfirmas.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': f'{ex}'})

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Legalización de actas'
                search, filtro, url_vars = request.GET.get('s', ''), (Q(status=True)), ''

                if not request.user.has_perm('postulate.puede_revisar_todas_las_actas'):
                    filtro = filtro & (Q(partida__partidatribunal__persona=persona))
                if search:
                    data['search'] = search
                    url_vars += "&s={}".format(search)
                    filtro = filtro & (Q(descripcion__icontains=search))

                listado = ActaPartida.objects.filter(filtro).order_by('id').distinct()
                paging = MiPaginador(listado.order_by('-fecha_creacion'), 20)
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
                data['list_count'] = len(listado)
                return render(request, "postulate/adm_legalizacionactas/view.html", data)
            except Exception as ex:
                pass


def fecha_letra(valor):
    mes = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    a = int(valor[0:4])
    m = int(valor[5:7])
    d = int(valor[8:10])
    if d == 1:
        return u"al %s día del mes de %s del año %s" % (numero_a_letras(d), str(mes[m - 1]),numero_a_letras(a))
    else:
        return u"a los %s días del mes de %s del año %s" % (numero_a_letras(d), str(mes[m - 1]),numero_a_letras(a))


def generar_actas(request, partida=None):
    data = {}
    hoy = datetime.now().date()
    if not partida:
        idpartida = encrypt_id(request.POST['id'])
        partida = Partida.objects.get(id=idpartida)
    tipo = int(request.POST['tipo'])

    # Crear directorios recursivamente
    directory_p = os.path.join(MEDIA_ROOT, 'postulate')
    directory = os.path.join(directory_p, 'actaspartida')
    directory_o = os.path.join(directory, 'original')
    directory_f = os.path.join(directory, 'firmadas')
    os.makedirs(directory, exist_ok=True)
    os.makedirs(directory_o, exist_ok=True)
    os.makedirs(directory_f, exist_ok=True)

    data['firmas'] = firmas = PartidaTribunal.objects.filter(partida=partida, status=True, tipo=tipo).order_by('id')
    data['partida'] = partida
    if 'actaconformacion' in request.POST:
        acta = ActaPartida.objects.filter(partida=partida, tipo=1, status=True).first()
        if not acta or acta.estado == 1:
            nombre_archivo = generar_nombre(f'actaconformacion_{partida.id}_', 'generado') + '.pdf'
            fecha = request.POST.get('fecha', '')
            fecha = hoy if not fecha else fecha
            data['fecha_letra'] = fecha_letra(fecha.__str__())
            data['firmas'] = firmas.filter(firma=True).order_by('id')
            pdf, response = conviert_html_to_pdf_save_file_model(
                'postulate/actas/actaconformacion.html',
                {'pagesize': 'a4 landscape',
                 'data': data, }, nombre_archivo)
            if not acta:
                acta = ActaPartida(partida=partida, archivo=pdf, estado=1, tipo=1, tipotribunal=1)
                acta.save(request)
            else:
                acta.archivo = pdf
                acta.save(request)
            historial = HistorialActaFirma(acta=acta, archivo_original=pdf, estado=1)
            historial.save(request)

    if 'actacalificacionmerito' in request.POST:
        acta = ActaPartida.objects.filter(partida=partida, tipo=2, status=True).first()
        if not acta or acta.estado == 1:
            nombre_archivo = generar_nombre(f'actacalificacionmerito_{partida.id}_', 'generado') + '.pdf'
            data['participantes'] = participantes = PersonaAplicarPartida.objects.filter(partida=partida, status=True).order_by('persona__apellido1', 'persona__nombres')
            data['total'] = len(participantes)
            html='postulate/actas/actacalificacionmerito.html'
            if partida.convocatoria.modeloevaluativoconvocatoria:
                html='postulate/actas/actacalificacionmeritov2.html'

            pdf, response = conviert_html_to_pdf_save_file_model(html, {'data': data}, nombre_archivo)
            if not acta:
                acta = ActaPartida(partida=partida, archivo=pdf, estado=1, tipo=2, tipotribunal=1)
                acta.save(request)
            else:
                acta.archivo = pdf
                acta.save(request)
            historial = HistorialActaFirma(acta=acta, archivo_original=pdf, estado=1)
            historial.save(request)

    if 'actacalificacionmerito2' in request.POST:
        acta = ActaPartida.objects.filter(partida=partida, tipo=3, status=True).first()
        if not acta or acta.estado == 1:
            nombre_archivo = generar_nombre(f'actacalificacionmerito2_{partida.id}_', 'generado') + '.pdf'
            data['participantes'] = participantes = PersonaAplicarPartida.objects.filter(partida=partida, status=True).order_by('persona__apellido1', 'persona__nombres')
            data['total'] = len(participantes)
            data['firmas'] = PartidaTribunal.objects.filter(partida=partida, status=True, tipo=1).order_by('id')
            html='postulate/actas/actacalificacionmeritodesempate.html'
            if partida.convocatoria.modeloevaluativoconvocatoria:
                html='postulate/actas/actacalificacionmeritodesempatev2.html'
            pdf, response = conviert_html_to_pdf_save_file_model(html, {'data': data}, nombre_archivo)
            if not acta:
                acta = ActaPartida(partida=partida, archivo=pdf, estado=1, tipo=3, tipotribunal=1)
                acta.save(request)
            else:
                acta.archivo = pdf
                acta.save(request)
            historial = HistorialActaFirma(acta=acta, archivo_original=pdf, estado=1)
            historial.save(request)

    if 'actaentrevistatrib2' in request.POST:
        acta = ActaPartida.objects.filter(partida=partida, tipo=4, status=True).first()
        if not acta or acta.estado == 1:
            nombre_archivo = generar_nombre(f'actaentrevistatrib2_{partida.id}_', 'generado') + '.pdf'
            data['participantes'] = participantes = partida.personaaplicarpartida_set.filter(status=True, estado__in=[1, 4], esmejorpuntuado=True).order_by('-nota_final_entrevista')
            data['total'] = len(participantes)
            html = 'postulate/actas/actaentrevista.html'
            if partida.convocatoria.modeloevaluativoconvocatoria:
                html='postulate/actas/actaentrevistav2.html'
            pdf, response = conviert_html_to_pdf_save_file_model(html, {'data': data}, nombre_archivo)
            if not acta:
                acta = ActaPartida(partida=partida, archivo=pdf, estado=1, tipo=4, tipotribunal=2)
                acta.save(request)
            else:
                acta.archivo = pdf
                acta.save(request)
            historial = HistorialActaFirma(acta=acta, archivo_original=pdf, estado=1)
            historial.save(request)

    if 'actapuntajefinaltrib2' in request.POST:
        acta = ActaPartida.objects.filter(partida=partida, tipo=5, status=True).first()
        if not acta or acta.estado == 1:
            nombre_archivo = generar_nombre(f'actapuntajefinaltrib2_{partida.id}_', 'generado') + '.pdf'
            data['firmas'] = firmas.filter(firma=True).order_by('id')
            data['participantes'] = participantes = partida.personaaplicarpartida_set.filter(status=True, esmejorpuntuado=True).order_by('-nota_final_entrevista')
            data['total'] = len(participantes)
            html = 'postulate/actas/actanotafinal.html'
            if partida.convocatoria.modeloevaluativoconvocatoria:
                data['campos'] = partida.convocatoria.modeloevaluativoconvocatoria.campos()
                html='postulate/actas/actanotafinalv2.html'
            pdf, response = conviert_html_to_pdf_save_file_model(html, {'data': data}, nombre_archivo)
            if not acta:
                acta = ActaPartida(partida=partida, archivo=pdf, estado=1, tipo=5, tipotribunal=2)
                acta.save(request)
            else:
                acta.archivo = pdf
                acta.save(request)
            historial = HistorialActaFirma(acta=acta, archivo_original=pdf, estado=1)
            historial.save(request)