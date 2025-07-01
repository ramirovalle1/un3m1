#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from django.core.wsgi import get_wsgi_application
from django.shortcuts import render

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()

from sga.graduados import convertir_certificadopdf_a_jpg, CUENTAS_CORREOS
import pyqrcode

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)
from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from sga.models import Graduado, FirmaPersona
from sagest.models import DistributivoPersona, PersonaDepartamentoFirmas
from settings import SITE_STORAGE, PUESTO_ACTIVO_ID, SITE_POPPLER, DEBUG
import uuid
from django.db import transaction
from sga.tasks import send_html_mail

from sga.funcionesxhtml2pdf import conviert_html_to_pdfsaveqrtitulo
try:
    data = {}
    dominio_sistema = 'https://sga.unemi.edu.ec'
    # if DEBUG:
    #     dominio_sistema = 'http://127.0.0.1:8000'
    # graduados = Graduado.objects.filter(status=True, inscripcion__carrera__coordinacion__id=7)
    # modo prueba
    graduados = Graduado.objects.filter(status=True, inscripcion__carrera__coordinacion__id=7)[:7]
    data["DOMINIO_DEL_SISTEMA"] = dominio_sistema
    listagenerados = []
    for graduado in graduados:
        persona_cargo_tercernivel = None
        cargo = None
        tamano = 0
        firmauno = None
        if DistributivoPersona.objects.filter(denominacionpuesto=113, estadopuesto__id=1, status=True).exists():
            firmauno = DistributivoPersona.objects.filter(denominacionpuesto=113, estadopuesto__id=1, status=True)[0]
        data['firmauno'] = firmauno
        firmatres = None
        if DistributivoPersona.objects.filter(denominacionpuesto=502, estadopuesto__id=1, status=True).exists():
            firmatres = DistributivoPersona.objects.filter(denominacionpuesto=502, estadopuesto__id=1, status=True)[0]
        data['firmatres'] = firmatres
        firmacertificado = None

        if PersonaDepartamentoFirmas.objects.filter(status=True, departamento=158).exists():
            firmacertificado = PersonaDepartamentoFirmas.objects.filter(status=True, departamento=158).order_by(
                '-id').first()

        if PersonaDepartamentoFirmas.objects.filter(actualidad=True, status=True).exists():
            firmaizquierda = PersonaDepartamentoFirmas.objects.get(actualidad=True, status=True,
                                                                   tipopersonadepartamento_id=2,
                                                                   departamentofirma_id=1)
        data['firmacertificado'] = firmacertificado
        data['firmaimg'] = FirmaPersona.objects.filter(status=True,
                                                       persona=firmacertificado.personadepartamento).last()
        data['firmaizquierda'] = firmaizquierda
        data['firmaimgizq'] = FirmaPersona.objects.filter(status=True,
                                                          persona=firmaizquierda.personadepartamento).last()
        data['persona_cargo'] = cargo
        data['persona_cargo_tercernivel'] = persona_cargo_tercernivel
        data['graduado'] = graduado
        fechagraduado = graduado.fechagraduado if graduado.fechagraduado else graduado.fecha_creacion
        mes = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
               "octubre", "noviembre", "diciembre"]
        if fechagraduado.day > 1:
            cadena = u"a los %s días" % (fechagraduado.day)
        else:
            cadena = u"al primer día"
        data['fecha_graduado_insignia'] = fechagraduado
        data['fecha'] = u"San Francisco de Milagro, " + cadena + " del mes de %s de %s." % (
            str(mes[fechagraduado.month - 1]), fechagraduado.year)
        data['controlar_bajada_logo'] = tamano
        qrname = 'qr_titulo_' + str(graduado.id)
        folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'titulos', 'qr'))
        directory = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'titulos'))
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
        url = pyqrcode.create('https://sga.unemi.edu.ec/media/qrcode/titulos/' + htmlname)
        imageqr = url.png(folder + qrname + '.png', 16, '#000000')
        data['qrname'] = 'qr' + qrname
        data['urlhtmlinsignia'] = urlhtmlinsignia = dominio_sistema + urlname
        vistaprevia = False
        valida = conviert_html_to_pdfsaveqrtitulo(
            'graduados/titulo_formatonuevo_pdf.html',
            {'pagesize': 'A4', 'data': data},
            qrname + '.pdf',
            vistaprevia
        )
        if valida:
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
            a = render(None, "graduados/titulovalido.html", {"data": data})
            with open(SITE_STORAGE + urlname, "wb") as f:
                f.write(a.content)
            f.close()
            graduado.namehtmltitulo = htmlname
            graduado.urlhtmltitulo = urlname
            # fin crear html en la media y guardar url en base
            graduado.save()
            # envio por correo
            asunto = u"INSIGNIA Y TÍTULO - " + str(graduado.inscripcion.carrera)

            # correoins = graduado.inscripcion.persona.emailpersonal()
            correoins = ['marianamadeleineas@gmail.com']
            send_html_mail(asunto, "emails/notificar_tituloinsignia_posgrado.html",
                           {'sistema': 'Sistema de Gestión Académica', 'graduado': graduado,
                            'director': firmacertificado, 'urlhtmlinsignia': urlhtmlinsignia},
                           correoins,
                           [], [graduado.rutapdftitulo],
                           cuenta=CUENTAS_CORREOS[0][1])
            listagenerados.append(graduado.inscripcion.persona.cedula)
        else:
            print("Problemas al ejecutar el reporte.")
    print('titulos generados masivo exitoso', listagenerados)
except Exception as ex:
    transaction.set_rollback(True)
    print('error al ejecutar el reporte', str(ex))