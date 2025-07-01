#!/usr/bin/env python
# -*- coding: utf-8 -*

import os
import sys
from django.core.wsgi import get_wsgi_application
from django.shortcuts import render

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from datetime import datetime, timedelta
from sga.graduados import convertir_certificadopdf_a_jpg, CUENTAS_CORREOS
import pyqrcode
import time
SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)
from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from sga.models import Graduado, FirmaPersona, Persona, Notificacion
from sagest.models import DistributivoPersona, PersonaDepartamentoFirmas
from settings import SITE_STORAGE, PUESTO_ACTIVO_ID, SITE_POPPLER
import uuid
from django.db import transaction
from sga.tasks import send_html_mail
from django.db.models import Q
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsaveqrtitulo
from sga.graduados import convertir_certificadopdf_a_jpg
from sga.funciones import variable_valor


data = {}

data['IS_DEBUG'] = IS_DEBUG = variable_valor('IS_DEBUG')

dominio_sistema = 'https://sga.unemi.edu.ec'
graduados = Graduado.objects.filter(Q(status=True, inscripcion__carrera__coordinacion__id=7),
                                    fecharefrendacion__isnull=False, fecharefrendacion__year__gte=2022).order_by('-id')[:10]
limitecorreo = 5
if IS_DEBUG:
    dominio_sistema = 'http://127.0.0.1:8000'
    graduados = Graduado.objects.filter(Q(status=True, inscripcion__carrera__coordinacion__id=7),
                                        fecharefrendacion__isnull=False, fecharefrendacion__year__gte=2022).order_by('-id')[:2]
    limitecorreo = 1


data["DOMINIO_DEL_SISTEMA"] = dominio_sistema
lista_correctos = []
lista_errores = []
cont = 0
correoins=[]
correoins.append('marianamadeleineas@gmail.com')
for graduado in graduados:
    try:
        cont += 1
        persona_cargo_tercernivel = None
        cargo = None
        tamano = 0
        firmauno = None
        if DistributivoPersona.objects.filter(denominacionpuesto=113, estadopuesto__id=1, status=True).exists():
            firmauno = DistributivoPersona.objects.filter(denominacionpuesto=113, estadopuesto__id=1, status=True)[
                0]
        data['firmauno'] = firmauno
        firmatres = None
        if DistributivoPersona.objects.filter(denominacionpuesto=502, estadopuesto__id=1, status=True).exists():
            firmatres = DistributivoPersona.objects.filter(denominacionpuesto=502, estadopuesto__id=1, status=True)[
                0]
        data['firmatres'] = firmatres
        firma_departamento = PersonaDepartamentoFirmas.objects.get(tipopersonadepartamento_id=1,
                                                                   departamentofirma_id=1, status=True,
                                                                   actualidad=True)
        listafirmaspersonadepartamento = PersonaDepartamentoFirmas.objects.filter(tipopersonadepartamento_id=1,
                                                                                  departamentofirma_id=1,
                                                                                  status=True)
        for firma in listafirmaspersonadepartamento:
            if firma.fechafin is not None and firma.fechainicio is not None:
                if graduado.fecharefrendacion <= firma.fechafin and graduado.fecharefrendacion >= firma.fechainicio:
                    firma_departamento = firma
        data['firmadirector'] = firma_departamento
        data['imgfirmadirector'] = firma_departamento.personadepartamento.firmapersona_set.filter(
            status=True).order_by('-tipofirma').first()
        if PersonaDepartamentoFirmas.objects.filter(actualidad=True, status=True).exists():
            firmaizquierda = PersonaDepartamentoFirmas.objects.get(actualidad=True, status=True,
                                                                   tipopersonadepartamento_id=2,
                                                                   departamentofirma_id=1)
        data['firmaizquierda'] = firmaizquierda
        data['firmaimgizq'] = FirmaPersona.objects.filter(status=True,
                                                          persona=firmaizquierda.personadepartamento).last()
        data['persona_cargo'] = cargo
        data['persona_cargo_tercernivel'] = persona_cargo_tercernivel
        data['graduado'] = graduado
        # data['title'] = ''
        data['fecha'] = None
        fechagraduado = graduado.fecharefrendacion if graduado.fecharefrendacion else None
        if fechagraduado:
            mes = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
                   "octubre", "noviembre", "diciembre"]
            if fechagraduado.day > 1:
                cadena = u"a los %s días" % (fechagraduado.day)
            else:
                cadena = u"al primer día"
            data['fecha'] = u"San Francisco de Milagro, " + cadena + " del mes de %s de %s." % (
                str(mes[fechagraduado.month - 1]), fechagraduado.year)
        data['fecha_graduado_insignia'] = fechagraduado
        data['controlar_bajada_logo'] = tamano
        qrname = 'qr_titulo_' + str(graduado.id)
        # folder = SITE_STORAGE + 'media/qrcode/evaluaciondocente/'
        folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'titulos', 'qr'))
        directory = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'titulos'))
        # folder = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'evaluaciondocente')
        rutapdf = folder + qrname + '.pdf'
        rutaimg = folder + qrname + '.png'
        try:
            os.stat(directory)
        except:
            os.mkdir(directory)
        if os.path.isfile(rutapdf):
            os.remove(rutaimg)
            os.remove(rutapdf)
        # generar nombre html y url html
        if not graduado.namehtmltitulo:
            htmlname = "%s%s" % (uuid.uuid4().hex, '.html')
        else:
            htmlname = graduado.namehtmltitulo
        urlname = "/media/qrcode/titulos/%s" % htmlname
        rutahtml = SITE_STORAGE + urlname
        if os.path.isfile(rutahtml):
            os.remove(rutahtml)
        # generar nombre html y url html
        data['version'] = version = datetime.now().strftime('%Y%m%d_%H%M%S%f')
        url = pyqrcode.create(f'{dominio_sistema}/media/qrcode/titulos/{htmlname}?v={version}')
        # url = pyqrcode.create('https://sga.unemi.edu.ec/media/qrcode/titulos/' + htmlname)
        imageqr = url.png(folder + qrname + '.png', 16, '#000000')
        data['qrname'] = 'qr' + qrname
        data['urlhtmlinsignia'] = urlhtmlinsignia = dominio_sistema + urlname
        data['posgrado'] = u'DIRECCIÓN DE POSGRADO'
        valida = conviert_html_to_pdfsaveqrtitulo(
            'graduados/titulo_formatonuevo_pdf.html',
            {'pagesize': 'A4', 'data': data},
            qrname + '.pdf'
        )
        if valida:
            # elimino codigo qr despues de pegarlo en el titulo titulo_formatonuevo_pdf.html
            if os.path.isfile(rutaimg):
                os.remove(rutaimg)
            # generar portada del certificado
            portada = convertir_certificadopdf_a_jpg(qrname, SITE_STORAGE, dominio_sistema, data)
            graduado.rutapdftitulo = 'qrcode/titulos/' + qrname + '.pdf'
            data['rutapdf'] = '/media/{}'.format(graduado.rutapdftitulo)  # ojo
            data['idinsignia'] = htmlname[0:len(htmlname) - 5]
            data['inscripcion'] = inscripcion = graduado.inscripcion
            data['records'] = inscripcion.recordacademico_set.filter(status=True).order_by(
                'asignaturamalla__nivelmalla', 'asignatura', 'fecha')
            data['total_creditos'] = inscripcion.total_creditos()
            data['total_creditos_malla'] = inscripcion.total_creditos_malla()
            data['total_creditos_modulos'] = inscripcion.total_creditos_modulos()
            data['total_creditos_otros'] = inscripcion.total_creditos_otros()
            data['total_horas'] = inscripcion.total_horas()
            data['promedio'] = inscripcion.promedio_record()
            # crear html de titulo valido en la media  y guardar url en base
            a = render(None, "graduados/titulovalido.html",
                       {"data": data})
            with open(SITE_STORAGE + urlname, "wb") as f:
                f.write(a.content)
            f.close()
            # elimino portada de titulo despues de añadirla en el insignia titulovalido.html
            graduado.namehtmltitulo = htmlname
            graduado.urlhtmltitulo = urlname
            graduado.estadonotificacion = 2
            # fin crear html en la media y guardar url en base
            graduado.save()
            # envio por correo
            firmacertificado = None
            if PersonaDepartamentoFirmas.objects.filter(status=True, departamento=158).exists():
                firmacertificado = PersonaDepartamentoFirmas.objects.filter(status=True, departamento=158).order_by(
                    '-id').first()
            asunto = u"INSIGNIA - " + str(graduado.inscripcion.carrera)
            if cont<=limitecorreo:
                send_html_mail(asunto, "emails/notificar_tituloinsignia_posgrado.html",
                               {'sistema': 'Sistema de Gestión Académica', 'graduado': graduado,
                                'director': firmacertificado, 'urlhtmlinsignia': f'{urlhtmlinsignia}?v={version}'},
                               correoins,
                               [], None,
                               cuenta=CUENTAS_CORREOS[0][1])
            if not IS_DEBUG:
                time.sleep(90)
            lista_correctos.append(f'{graduado.id}')
    except Exception as ex:
        lista_errores.append(f'Cédula: {graduado.inscripcion.persona.cedula} - Id graduado: {graduado.id} - Error: {ex}\n')
        print(f'Cédula: {graduado.inscripcion.persona.cedula} - Id: {graduado.id} - Error: {ex}\n')
# Para masivo enviar notificacion al sga del administrativo
if len(lista_errores) == 0:
    titulonotificacion = f"Proceso exitoso de generación de títulos masivo"
    cuerponotificacion = u"Se generó correctamente el proceso. \nTotal correctos: %s, \nTotal graduados: %s. Generados correctamente (idgraduado): %s" % (
        str(len(lista_correctos)), str(len(graduados)), str(lista_correctos))
else:
    titulonotificacion = f"Error en el proceso de generación de títulos de graduados de posgrado"
    cuerponotificacion = u"No se generaron %s título(s): \n%s, \nTotal correctos: %s, \nTotal graduados: %s. Generados correctamente (idgraduado): %s" % (
        str(len(lista_errores)), str(lista_errores), str(len(lista_correctos)), str(len(graduados)),
        str(lista_correctos))
# Notifica el resultado del proceso como notificacion en el sga
notificacion = Notificacion(
    titulo=titulonotificacion,
    cuerpo=cuerponotificacion,
    destinatario=Persona.objects.get(pk=21966),
    url=f"/graduados",
    content_type=None,
    object_id=None,
    prioridad=1,
    app_label='SGA',
    fecha_hora_visible=datetime.now() + timedelta(days=3))
notificacion.save()
print('Fin proceso')