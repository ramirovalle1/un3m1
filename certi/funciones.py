# coding=utf-8
from __future__ import division

import subprocess
from datetime import datetime, timedelta, date, time
from dateutil.relativedelta import relativedelta
from pdf2image import convert_from_bytes
import os
import sys
import shutil
import uuid
from PyPDF2 import PdfFileMerger

from django.db import transaction
from django.template.loader import get_template
from html2image import Html2Image

from certi.models import Carnet
from settings import SITE_STORAGE, MEDIA_URL, SITE_POPPLER, JR_JAVA_COMMAND, DATABASES, JR_RUN, MEDIA_ROOT, DEBUG, JR_USEROUTPUT_FOLDER
from sga.funciones import log, elimina_tildes
from sga.models import unicode
from sga.reportes import transform_jasperstarter, transform_jasperstarter_kwargs


def valida_tiempo_certificado(vigencia, tipo_vigencia, fechahoraregistro):
    ahora = datetime.now()
    if tipo_vigencia == 1:
        return fechahoraregistro <= ahora + timedelta(hours=vigencia)
    elif tipo_vigencia == 2:
        return fechahoraregistro <= ahora + timedelta(days=vigencia)
    elif tipo_vigencia == 3:
        return fechahoraregistro <= ahora + relativedelta(months=vigencia)
    elif tipo_vigencia == 4:
        return fechahoraregistro <= ahora + relativedelta(years=vigencia)
    else:
        return True


def crear_carnet_estudiantil(matricula, config, request, **kwargs):
    try:
        # base_url = request.META['HTTP_HOST']
        output_folder_pdf = os.path.join(SITE_STORAGE, 'media', 'carnet', 'estudiantil', elimina_tildes(request.user.username), f'{matricula.id}', 'pdf')
        output_folder_images = os.path.join(SITE_STORAGE, 'media', 'carnet', 'estudiantil', elimina_tildes(request.user.username), f'{matricula.id}', 'images')
        try:
            shutil.rmtree(output_folder_pdf)
        except Exception as ex:
            pass
        try:
            shutil.rmtree(output_folder_images)
        except Exception as ex:
            pass
        try:
            os.makedirs(output_folder_pdf)
        except Exception as ex:
            pass

        try:
            os.makedirs(output_folder_images)
        except Exception as ex:
            pass
        d = datetime.now()
        reporte = config.reporte
        # pdfname = reporte.nombre + d.strftime('%Y%m%d_%H%M%S')
        pdfname = str(uuid.uuid4())
        folder_pdf = os.path.join(os.path.join(SITE_STORAGE, 'media', 'carnet', 'estudiantil', elimina_tildes(request.user.username), f'{matricula.id}', 'pdf', ''))
        folder_images = os.path.join(os.path.join(SITE_STORAGE, 'media', 'carnet', 'estudiantil', elimina_tildes(request.user.username), f'{matricula.id}', 'images', ''))
        rutapdf = folder_pdf + pdfname + '.pdf'
        if os.path.isfile(rutapdf):
            os.remove(rutapdf)
        url_pdf = "/".join([MEDIA_URL, 'carnet', 'estudiantil', elimina_tildes(request.user.username), f'{matricula.id}', 'pdf', pdfname + ".pdf"])
        runjrcommand = [JR_JAVA_COMMAND, '-jar',
                        os.path.join(JR_RUN, 'jasperstarter.jar'),
                        'pr', reporte.archivo.file.name,
                        '--jdbc-dir', JR_RUN,
                        '-f', 'pdf',
                        '-t', 'postgres',
                        '-H', DATABASES['sga_select']['HOST'],
                        '-n', DATABASES['sga_select']['NAME'],
                        '-u', DATABASES['sga_select']['USER'],
                        '-p', f"'{DATABASES['sga_select']['PASSWORD']}'",
                        '--db-port', DATABASES['sga_select']['PORT'],
                        '-o', output_folder_pdf + os.sep + pdfname]
        parametros = reporte.parametros()
        if kwargs:
            paramlist = [transform_jasperstarter_kwargs(p, **kwargs) for p in parametros]
        else:
            paramlist = [transform_jasperstarter(p, request, 'POST') for p in parametros]

        if paramlist:
            runjrcommand.append('-P')
            for parm in paramlist:
                runjrcommand.append(parm)
        else:
            runjrcommand.append('-P')
        runjrcommand.append(u'MEDIA_DIR=' + unicode("/".join([MEDIA_ROOT, ''])))
        mens = ''
        mensaje = ''
        for m in runjrcommand:
            mens += ' ' + m
        if DEBUG:
            runjr = subprocess.run(mens, shell=True, check=True)
            # print('runjr:', runjr.returncode)
        else:
            runjr = subprocess.call(mens.encode("latin1"), shell=True)

        sp = os.path.split(reporte.archivo.file.name)
        with open(rutapdf, mode='rb') as pdf:
            images = convert_from_bytes(pdf.read(), output_folder=folder_images, poppler_path=SITE_POPPLER, fmt="png")
        with os.scandir(folder_images) as ficheros:
            ficheros = [fichero.name for fichero in ficheros if fichero.is_file() and fichero.name.endswith('.png')]
        linea = 0
        url_png_anverso = None
        url_png_reverso = None
        for fichero in ficheros:
            linea += 1
            if linea == 1:
                url_png_anverso = "/".join([MEDIA_URL, 'carnet', 'estudiantil', elimina_tildes(request.user.username), f'{matricula.id}', 'images', fichero])
                # os.rename(os.path.join(folder_images, fichero), os.path.join(folder_images, 'anverso.png'))
            else:
                url_png_reverso = "/".join([MEDIA_URL, 'carnet', 'estudiantil', elimina_tildes(request.user.username), f'{matricula.id}', 'images', fichero])
                # os.rename(os.path.join(folder_images, fichero), os.path.join(folder_images, 'reverso.png'))
        carnet = Carnet(config=config,
                        persona=matricula.inscripcion.persona,
                        matricula=matricula,
                        pdf=url_pdf,
                        png_anverso=url_png_anverso,
                        png_reverso=url_png_reverso,
                        fecha_emision=datetime.now(),
                        fecha_caducidad=datetime.combine(matricula.nivel.periodo.fin, time(23, 59, 59)),
                        activo=True,
                        )
        carnet.save(request)
        return True, ''
    except Exception as ex:
        mensaje_ex = f'Error on line {sys.exc_info()[-1].tb_lineno} {ex.__str__()}'
        print(mensaje_ex)
        return False, mensaje_ex


def crear_carnet_estudiantil_old(matricula, config, request=None):
    with transaction.atomic():
        try:
            carnet = Carnet(config=config,
                            persona=matricula.inscripcion.persona,
                            matricula=matricula,
                            fecha_emision=datetime.now(),
                            fecha_caducidad=datetime.combine(matricula.nivel.periodo.fin, time(23, 59, 59))
                            )
            carnet.save(request)
            data = {}
            data['persona'] = persona = matricula.inscripcion.persona
            data['carnet'] = carnet
            base_url = request.META['HTTP_HOST']
            data['url_path'] = request.scheme + "://" + unicode(base_url)
            if config.es_anverso():
                anverso = get_template("alu_carnet/create/anverso.html")
                json_anverso = anverso.render(data)
            elif config.es_reverso():
                reverso = get_template("alu_carnet/create/reverso.html")
                json_reverso = reverso.render(data)
            elif config.es_anverso_y_reverso():
                anverso = get_template("alu_carnet/create/anverso.html")
                json_anverso = anverso.render(data)
                reverso = get_template("alu_carnet/create/reverso.html")
                json_reverso = reverso.render(data)
            else:
                raise NameError(u"Tipo de carné estudiantil no encontrado")
            output_folder = os.path.join(SITE_STORAGE, 'media', 'carnet', elimina_tildes(request.user.username), f'{matricula.id}')
            try:
                os.makedirs(output_folder)
            except Exception as ex:
                pass
            hti = Html2Image(output_path=output_folder)
            if config.es_anverso():
                name_anverso = f'anverso_{carnet.fecha_emision.strftime("%Y%m%d_%H%M%S")}.png'
                hti.screenshot(html_str=json_anverso, save_as=name_anverso, size=(350, 250))
                carnet.anverso = "/".join([MEDIA_URL, 'media', 'carnet', elimina_tildes(request.user.username), name_anverso])
                # carnet.anverso = output_folder + name_anverso
            elif config.es_reverso():
                name_reverso = f'reverso_{carnet.fecha_emision.strftime("%Y%m%d_%H%M%S")}.png'
                hti.screenshot(html_str=json_reverso, save_as=name_reverso, size=(350, 250))
                carnet.reverso = "/".join([MEDIA_URL, 'media', 'carnet', elimina_tildes(request.user.username), name_reverso])
            elif config.es_anverso_y_reverso():
                name_anverso = f'anverso_{carnet.fecha_emision.strftime("%Y%m%d_%H%M%S")}.png'
                hti.screenshot(html_str=json_anverso, save_as=name_anverso, size=(350, 250))
                name_reverso = f'reverso_{carnet.fecha_emision.strftime("%Y%m%d_%H%M%S")}.png'
                hti.screenshot(html_str=json_reverso, save_as=name_reverso, size=(350, 250))
                carnet.anverso = "/".join([MEDIA_URL, 'media', 'carnet', elimina_tildes(request.user.username), name_anverso])
                carnet.reverso = "/".join([MEDIA_URL, 'media', 'carnet', elimina_tildes(request.user.username), name_reverso])
            else:
                raise NameError(u"Tipo de carné estudiantil no encontrado")
            carnet.save(request)
            log(u'Adiciono carné estudiantil: %s' % carnet, request, "add")
            return True, None
        except Exception as ex:
            transaction.set_rollback(True)
            return False, f"{ex.__str__()}"


def crear_carnet(config, request, matricula=None, distributivo=None, **kwargs):
    try:
        # base_url = request.META['HTTP_HOST']
        texto_perfil = None
        objeto = None
        if config.tipo_perfil == 1:
            texto_perfil = 'estudiantil'
            objeto = matricula
        elif config.tipo_perfil == 2:
            texto_perfil = 'administrativo'
            objeto = distributivo
        elif config.tipo_perfil == 3:
            texto_perfil = 'docentes'
            objeto = distributivo

        output_folder_pdf = os.path.join(SITE_STORAGE, 'media', 'carnet', texto_perfil, elimina_tildes(request.user.username), f'{objeto.id}', 'pdf')
        output_folder_images = os.path.join(SITE_STORAGE, 'media', 'carnet', texto_perfil, elimina_tildes(request.user.username), f'{objeto.id}', 'images')
        try:
            shutil.rmtree(output_folder_pdf)
        except Exception as ex:
            pass
        try:
            shutil.rmtree(output_folder_images)
        except Exception as ex:
            pass
        try:
            os.makedirs(output_folder_pdf)
        except Exception as ex:
            pass

        try:
            os.makedirs(output_folder_images)
        except Exception as ex:
            pass
        d = datetime.now()
        reporte = config.reporte
        # pdfname = reporte.nombre + d.strftime('%Y%m%d_%H%M%S')
        pdfname = str(uuid.uuid4())
        folder_pdf = os.path.join(os.path.join(SITE_STORAGE, 'media', 'carnet', texto_perfil, elimina_tildes(request.user.username), f'{objeto.id}', 'pdf', ''))
        folder_images = os.path.join(os.path.join(SITE_STORAGE, 'media', 'carnet', texto_perfil, elimina_tildes(request.user.username), f'{objeto.id}', 'images', ''))
        rutapdf = folder_pdf + pdfname + '.pdf'
        if os.path.isfile(rutapdf):
            os.remove(rutapdf)
        url_pdf = "/".join([MEDIA_URL, 'carnet', texto_perfil, elimina_tildes(request.user.username), f'{objeto.id}', 'pdf', pdfname + ".pdf"])
        runjrcommand = [JR_JAVA_COMMAND, '-jar',
                        os.path.join(JR_RUN, 'jasperstarter.jar'),
                        'pr', reporte.archivo.file.name,
                        '--jdbc-dir', JR_RUN,
                        '-f', 'pdf',
                        '-t', 'postgres',
                        '-H', DATABASES['sga_select']['HOST'],
                        '-n', DATABASES['sga_select']['NAME'],
                        '-u', DATABASES['sga_select']['USER'],
                        '-p', f"'{DATABASES['sga_select']['PASSWORD']}'",
                        '--db-port', DATABASES['sga_select']['PORT'],
                        '-o', output_folder_pdf + os.sep + pdfname]
        parametros = reporte.parametros()
        if kwargs:
            paramlist = [transform_jasperstarter_kwargs(p, **kwargs) for p in parametros]
        else:
            paramlist = [transform_jasperstarter(p, request, 'POST') for p in parametros]
        if paramlist:
            runjrcommand.append('-P')
            for parm in paramlist:
                runjrcommand.append(parm)
        else:
            runjrcommand.append('-P')
        runjrcommand.append(u'MEDIA_DIR=' + unicode("/".join([MEDIA_ROOT, ''])))
        mens = ''
        mensaje = ''
        for m in runjrcommand:
            mens += ' ' + m
        if DEBUG:
            runjr = subprocess.run(mens, shell=True, check=True)
            # print('runjr:', runjr.returncode)
        else:
            runjr = subprocess.call(mens.encode("latin1"), shell=True)

        sp = os.path.split(reporte.archivo.file.name)
        with open(rutapdf, mode='rb') as pdf:
            images = convert_from_bytes(pdf.read(), output_folder=folder_images, poppler_path=SITE_POPPLER, fmt="png")
        with os.scandir(folder_images) as ficheros:
            ficheros = [fichero.name for fichero in ficheros if fichero.is_file() and fichero.name.endswith('.png')]
        linea = 0
        url_png_anverso = None
        url_png_reverso = None
        for fichero in ficheros:
            linea += 1
            if linea == 1:
                url_png_anverso = "/".join([MEDIA_URL, 'carnet', texto_perfil, elimina_tildes(request.user.username), f'{objeto.id}', 'images', fichero])
                # os.rename(os.path.join(folder_images, fichero), os.path.join(folder_images, 'anverso.png'))
            else:
                url_png_reverso = "/".join([MEDIA_URL, 'carnet', texto_perfil, elimina_tildes(request.user.username), f'{objeto.id}', 'images', fichero])
                # os.rename(os.path.join(folder_images, fichero), os.path.join(folder_images, 'reverso.png'))
        fecha_actual = datetime.now()
        aniosuma = 0
        if distributivo is not None:
            if distributivo.unidadorganica_id == 212:
                aniosuma = 1
        fecha_final = date(fecha_actual.year + aniosuma, 12, 31)

        carnet = Carnet(config=config,
                        persona=matricula.inscripcion.persona if matricula else distributivo.persona,
                        matricula=matricula,
                        distributivo=distributivo,
                        pdf=url_pdf,
                        png_anverso=url_png_anverso,
                        png_reverso=url_png_reverso,
                        fecha_emision=datetime.now(),
                        fecha_caducidad=datetime.combine(matricula.nivel.periodo.fin, time(23, 59, 59))if matricula else fecha_final,
                        activo=True,
                        )
        carnet.save(request)
        return True, "Carnet guardado exitosamente", carnet
    except Exception as ex:
        return False, ex.__str__(), None


def unir_pdf(archivo, logreporte):
    try:
        if archivo:
            archivoresultado = os.path.join(JR_USEROUTPUT_FOLDER, elimina_tildes(logreporte.usuario_creacion.username), '')
            listadopdfs = [
                "".join([SITE_STORAGE, logreporte.url]).replace('//', '/'),
                archivo
                #"".join([SITE_STORAGE, archivo.url]).replace('//', '/'),
                #'D://git/academico/media//documentos//userreports//atorrese////mallacurricular27801.pdf'
            ]
            merger = PdfFileMerger()
            merger.setPageMode('/FullScreen')
            [merger.append(pdf) for pdf in listadopdfs]
            pdfname = logreporte.reporte.nombre + datetime.now().strftime('%Y%m%d_%H%M%S')+".pdf"
            reportfile = archivoresultado+pdfname
            with open(reportfile, "wb") as new_file:
                merger.write(new_file)
            return True, u'Combinacion Completa', pdfname
        else:
            raise NameError('Certificado Sin Malla Adjunta')
    except Exception as ex:
        return False, u'Fallo operación %s' % str(ex), None


def crear_html_a_pdf_malla(malla):
    pass