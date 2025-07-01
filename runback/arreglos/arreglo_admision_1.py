#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import openpyxl
# import urllib2
import pyqrcode
# Full path and name to your csv file
import unicodedata
# from django.db.backends.oracle.base import to_unicode
# from apt.package import Record

import xlrd
# from __builtin__ import file
# from IPython.lib.editorhooks import mate
from django.http import HttpResponse
# from numpy.core.records import record
# from numpy.matrixlib.defmatrix import matrix
from setuptools.windows_support import hide_file
from urllib3 import request
from docx import Document
from xlwt import easyxf
from settings import EMAIL_INSTITUCIONAL_AUTOMATICO, EMAIL_DOMAIN, PROFESORES_GROUP_ID, \
    RESPONSABLE_BIENES_ID, ALUMNOS_GROUP_ID, USA_TIPOS_INSCRIPCIONES, TIPO_INSCRIPCION_INICIAL, DIAS_MATRICULA_EXPIRA, \
    CLAVE_USUARIO_CEDULA, CHEQUEAR_CONFLICTO_HORARIO

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))


# csv_filepathname = "cbaja.xlsx"
# csv_filepathname2 = "parroquia.txt"
# csv_filepathname2 = "notas2015salida.csv"
# csv_filepathname = "notas_ingles_150515.csv"
# csv_filepathname = "tesis.csv"
# csv_filepathname = "registro_libros.csv"
# csv_filepathname = "cuentas.csv"
# csv_filepathname = "deudas.csv"
# csv_filepathname = "records.csv"
# csv_filepathname2 = "deudas.csv"G
#csv_filepathname2 = "notas.csv"
# csv_filepathname= "MATERIAS.txt"
# csv_filepathname2 = "historico.csv"
# csv_filepathname2 = "fallos_notas_ingles.csv"
csv_filepathname2 = "egresadofalta.csv"

# your_djangoproject_home=os.path.split(SITE_ROOT)[0]
#
# sys.path.append(your_djangoproject_home)
# os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'



# SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
YOUR_PATH = os.path.dirname(os.path.realpath(__file__))
# print(f"YOUR_PATH: {YOUR_PATH}")
SITE_ROOT = os.path.dirname(os.path.dirname(YOUR_PATH))
SITE_ROOT = os.path.join(SITE_ROOT, '')
# print(f"SITE_ROOT: {SITE_ROOT}")
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
# print(f"your_djangoproject_home: {your_djangoproject_home}")
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsaveqrcertificado



# def download(url, NOMBRE):
#     try:
#         furl = urllib2.urlopen(url)
#         f = file("%s.png"%NOMBRE,'wb')
#         f.write(furl.read())
#         f.close()
#     except:
#         print('Unable to download file')



def to_unicode(s):
    if isinstance(s, unicode):
        return s

    from locale import getpreferredencoding
    for cp in (getpreferredencoding(), "cp1255", "cp1250"):
        try:
            return unicode(s, cp)
        except UnicodeDecodeError:
            pass
    raise Exception("Conversion to unicode failed")

def fechatope(fecha):
    contador = 0
    nuevafecha = fecha
    while contador < DIAS_MATRICULA_EXPIRA:
        nuevafecha = nuevafecha + timedelta(1)
        if nuevafecha.weekday() != 5 and nuevafecha.weekday() != 6:
            contador += 1
    return nuevafecha

def calculate_username(persona, variant=1):
    alfabeto = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
    s = persona.nombres.lower().split(' ')
    while '' in s:
        s.remove('')
    if persona.apellido2:
        usernamevariant = s[0][0] + persona.apellido1.lower() + persona.apellido2.lower()[0]
    else:
        usernamevariant = s[0][0] + persona.apellido1.lower()
    usernamevariant = usernamevariant.replace(' ', '').replace(u'ñ', 'n').replace(u'á', 'a').replace(u'é', 'e').replace(u'í', 'i').replace(u'ó', 'o').replace(u'ú', 'u')
    usernamevariantfinal = ''
    for letra in usernamevariant:
        if letra in alfabeto:
            usernamevariantfinal += letra
    if variant > 1:
        usernamevariantfinal += str(variant)
    if not User.objects.filter(username=usernamevariantfinal).exclude(persona=persona).exists():
        return usernamevariantfinal
    else:
        return calculate_username(persona, variant + 1)

def generar_usuario(persona, usuario, group_id):
    password = DEFAULT_PASSWORD
    if CLAVE_USUARIO_CEDULA:
        password = persona.cedula
    user = User.objects.create_user(usuario, '', password)
    user.save()
    persona.usuario = user
    persona.save()
    persona.cambiar_clave()
    g = Group.objects.get(pk=group_id)
    g.user_set.add(user)
    g.save()

from sga.models import *
from sagest.models import *

# from bib.models import *
# from med.models import *

# from sga.docentes import calculate_username
import csv

dataWriter = csv.writer(open(csv_filepathname2,'ab'), delimiter=';')
# dataReader = csv.reader(open(csv_filepathname,"rU"), delimiter=';')
# dataReader2 = csv.reader(open(csv_filepathname2,"rU"), delimiter=';')


# import xlrd

# workbook = xlrd.open_workbook("productos_unemi.xlsx")
# sheet = workbook.sheet_by_index(0)

# workbook = xlrd.open_workbook("producto.xlsx")
# sheet = workbook.sheet_by_index(0)

def convertirfecha(fecha):
    try:
        return date(int(fecha[6:10]),int(fecha[3:5]),int(fecha[0:2]))
    except Exception as ex:
        return datetime.now().date()

def convertirfechahora(fecha):
    try:
        return datetime(int(fecha[0:4]), int(fecha[5:7]), int(fecha[8:10]),int(fecha[11:13]),int(fecha[14:16]),int(fecha[17:19]))
    except Exception as ex:
        return datetime.now()


def convertirfecha2(fecha):
    try:
        return date(int(fecha[0:4]),int(fecha[5:7]),int(fecha[8:10]))
    except Exception as ex:
        return datetime.now().date()

def remover_caracteres_especiales(cadena):
    s = ''.join((c for c in unicodedata.normalize('NFD',unicode(cadena)) if unicodedata.category(c) != 'Mn'))
    return s.decode()

def fecha_letra(valor):
    Mes = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    d = int(valor[0:2])
    m = int(valor[3:5])
    a = int(valor[6:10])
    if d == 1:
        return  u"al %s día del mes de %s del %s" % (numero_a_letras(d),str(Mes[m - 1]),numero_a_letras(a))
    else:
        return u"a los %s días del mes de %s del %s" % (numero_a_letras(d),str(Mes[m - 1]),numero_a_letras(a))

def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)

MONEDA_SINGULAR = 'dolar'
MONEDA_PLURAL = 'dolares'

CENTIMOS_SINGULAR = 'centavo'
CENTIMOS_PLURAL = 'centavos'

MAX_NUMERO = 999999999999

UNIDADES = (
    'cero',
    'uno',
    'dos',
    'tres',
    'cuatro',
    'cinco',
    'seis',
    'siete',
    'ocho',
    'nueve'
)

DECENAS = (
    'diez',
    'once',
    'doce',
    'trece',
    'catorce',
    'quince',
    'dieciseis',
    'diecisiete',
    'dieciocho',
    'diecinueve'
)

DIEZ_DIEZ = (
    'cero',
    'diez',
    'veinte',
    'treinta',
    'cuarenta',
    'cincuenta',
    'sesenta',
    'setenta',
    'ochenta',
    'noventa'
)

CIENTOS = (
    '_',
    'ciento',
    'doscientos',
    'trescientos',
    'cuatroscientos',
    'quinientos',
    'seiscientos',
    'setecientos',
    'ochocientos',
    'novecientos'
)

def numero_a_letras(numero):
    numero_entero = int(numero)
    if numero_entero > MAX_NUMERO:
        raise OverflowError('Número demasiado alto')
    if numero_entero < 0:
        return 'menos %s' % numero_a_letras(abs(numero))
    letras_decimal = ''
    parte_decimal = int(round((abs(numero) - abs(numero_entero)) * 100))
    if parte_decimal > 9:
        letras_decimal = 'punto %s' % numero_a_letras(parte_decimal)
    elif parte_decimal > 0:
        letras_decimal = 'punto cero %s' % numero_a_letras(parte_decimal)
    if (numero_entero <= 99):
        resultado = leer_decenas(numero_entero)
    elif (numero_entero <= 999):
        resultado = leer_centenas(numero_entero)
    elif (numero_entero <= 999999):
        resultado = leer_miles(numero_entero)
    elif (numero_entero <= 999999999):
        resultado = leer_millones(numero_entero)
    else:
        resultado = leer_millardos(numero_entero)
    resultado = resultado.replace('uno mil', 'un mil')
    resultado = resultado.strip()
    resultado = resultado.replace(' _ ', ' ')
    resultado = resultado.replace('  ', ' ')
    if parte_decimal > 0:
        resultado = '%s %s' % (resultado, letras_decimal)
    return resultado

def numero_a_moneda(numero):
    if '.' in numero:
        posicion=numero.split('.')
        numero_entero = int(posicion[0])
        parte_decimal=0
        if posicion[1] != '':
            parte_decimal = int(posicion[1])
    else:
        numero_entero = int(numero)
        parte_decimal = 0
    centimos = ''
    if parte_decimal == 1:
        centimos = CENTIMOS_SINGULAR
    else:
        centimos = CENTIMOS_PLURAL
    moneda = ''
    if numero_entero == 1:
        moneda = MONEDA_SINGULAR
    else:
        moneda = MONEDA_PLURAL
    letras = numero_a_letras(numero_entero)
    letras = letras.replace('uno', 'un')
    letras_decimal = u'%s/100 DOLARES DE LOS ESTADOS UNIDOS DE NORTE AMÉRICA' % (str(parte_decimal))
    letras = u'%s %s' % (letras, letras_decimal)
    return letras

def leer_decenas(numero):
    if numero < 10:
        return UNIDADES[numero]
    decena, unidad = divmod(numero, 10)
    if unidad == 0:
        resultado = DIEZ_DIEZ[decena]
    else:
        if numero <= 19:
            resultado = DECENAS[unidad]
        elif numero <= 29:
            resultado = 'veinti%s' % UNIDADES[unidad]
        else:
            resultado = DIEZ_DIEZ[decena]
            if unidad > 0:
                resultado = '%s y %s' % (resultado, UNIDADES[unidad])
    return resultado

def leer_centenas(numero):
    centena, decena = divmod(numero, 100)
    if numero == 0:
        resultado = 'cien'
    else:
        resultado = CIENTOS[centena]
        if decena > 0:
            resultado = '%s %s' % (resultado, leer_decenas(decena))
    return resultado

def leer_miles(numero):
    millar, centena = divmod(numero, 1000)
    resultado = ''
    if (millar == 1):
        resultado = ''
    if (millar >= 2) and (millar <= 9):
        resultado = UNIDADES[millar]
    elif (millar >= 10) and (millar <= 99):
        resultado = leer_decenas(millar)
    elif (millar >= 100) and (millar <= 999):
        resultado = leer_centenas(millar)
    resultado = '%s mil' % resultado
    if centena > 0:
        resultado = '%s %s' % (resultado, leer_centenas(centena))
    return resultado

def leer_millones(numero):
    millon, millar = divmod(numero, 1000000)
    resultado = ''
    if (millon == 1):
        resultado = ' un millon '
    if (millon >= 2) and (millon <= 9):
        resultado = UNIDADES[millon]
    elif (millon >= 10) and (millon <= 99):
        resultado = leer_decenas(millon)
    elif (millon >= 100) and (millon <= 999):
        resultado = leer_centenas(millon)
    if millon > 1:
        resultado = '%s millones' % resultado
    if (millar > 0) and (millar <= 999):
        resultado = '%s %s' % (resultado, leer_centenas(millar))
    elif (millar >= 1000) and (millar <= 999999):
        resultado = '%s %s' % (resultado, leer_miles(millar))
    return resultado

def leer_millardos(numero):
    millardo, millon = divmod(numero, 1000000)
    return '%s millones %s' % (leer_miles(millardo), leer_millones(millon))

# import openpyxl
# a = 0
# miarchivo = openpyxl.load_workbook('CASOS_HCUENTA_UNEMI_1S2020.xlsx')
# lista = miarchivo.get_sheet_by_name('presencial')
# periodo=Periodo.objects.get(id=90)
# totallista = lista.rows
# for filas in totallista[:]:
#     a += 1
#     if a > 1:
#         try:
#             cedula = filas[8].value.strip()
#             observacion =""
#             if Persona.objects.filter(Q(cedula=cedula) | Q(pasaporte=cedula), status=True).exists():
#                 persona = Persona.objects.filter(Q(cedula=cedula) | Q(pasaporte=cedula), status=True)[0]
#                 observacion =" Persona %s " % (persona)
#                 if Inscripcion.objects.values('id').filter(status=True, persona=persona).exists():
#                     for inscripcion in Inscripcion.objects.filter(status=True, persona=persona):
#                         observacion = observacion + " se encuentra inscrito en %s \n " % (inscripcion.carrera)
#                         if inscripcion.matriculado_periodo(periodo):
#                             observacion=observacion+"se encuentra matriculado en %s  \n " %(periodo)
#                         if inscripcion.graduado():
#                             observacion = observacion + "se encuentra graduado %s  \n "%(inscripcion.carrera)
#                         if inscripcion.retiro_carrera():
#                             observacion = observacion + " se encuentra retirado de la carrera %s  \n "%(inscripcion.carrera)
#                         for record in inscripcion.recordacademico_set.filter(status=True, aprobada=False).distinct('materiaregular__nivel__periodo__nombre'):
#                             if record.materiaregular:
#                                 observacion=observacion+"reprobo asignaturas en el periodo %s \n " %(record.materiaregular.nivel.periodo.nombre)
#                 else:
#                     observacion=observacion+"Persona no se encuentra inscrito en ninguna carrera %s \n "%(persona)
#             else:
#                 observacion = observacion + "Persona no se encuentra en el sistema \n "
#             filas[22].value = observacion
#             print("%s - %s"%(a,observacion))
#         except Exception as ex:
#             print('error: %s' % ex)
# miarchivo.save("CASOS_HCUENTA_UNEMI_1S2020.xlsx")

# inscritos = CapInscritoIpec.objects.filter(status=True,rutapdf__isnull=False,persona_emailnotifica__isnull=False)
# for inscrito in inscritos:
#     if inscrito.cancelo_rubro() or (inscrito.capeventoperiodo.costo == 0 and inscrito.capeventoperiodo.costoexterno == 0):
#         data = {}
#         tamano=0
#         data['evento'] = evento = inscrito.capeventoperiodo
#         data['logoaval'] = inscrito.capeventoperiodo.archivo
#         persona=inscrito.persona_emailnotifica
#         cargo=None
#         persona_cargo_tercernivel=None
#         if DistributivoPersona.objects.filter(persona_id=persona, estadopuesto__id=PUESTO_ACTIVO_ID, status=True).exists():
#             cargo =  DistributivoPersona.objects.filter(persona_id=persona, estadopuesto__id=PUESTO_ACTIVO_ID, status=True)[0]
#         data['persona_cargo'] = cargo
#         data['persona_cargo_titulo'] = titulo = persona.titulacion_principal_senescyt_registro()
#         if not titulo == '':
#             persona_cargo_tercernivel = persona.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion')[0] if titulo.titulo.nivel_id == 4 else None
#         data['persona_cargo_tercernivel'] = persona_cargo_tercernivel
#         data['elabora_persona'] = persona
#         firmacertificado = 'robles'
#         fechacambio = (datetime(2019, 11, 1, 0, 0, 0)).date()
#         if evento.fechafin >= fechacambio:
#             firmacertificado = 'firmaguillermo'
#         data['firmacertificado'] = firmacertificado
#         if evento.envionotaemail:
#             data['nota'] = evento.instructor_principal().extaer_notatotal(inscrito.id)
#         data['inscrito'] = inscrito
#         mes = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
#                "noviembre", "diciembre"]
#         data['listado_contenido'] = listado = evento.contenido.split("\n") if evento.contenido else []
#         if evento.objetivo.__len__() < 290:
#             if listado.__len__() < 21:
#                 tamano = 120
#             elif listado.__len__() < 35:
#                 tamano = 100
#             elif listado.__len__() < 41:
#                 tamano = 70
#             else:
#                 tamano = 70
#         data['controlar_bajada_logo'] = tamano
#         qrname = 'qr_certificado_' + str(inscrito.id)
#         # folder = SITE_STORAGE + 'media/qrcode/evaluaciondocente/'
#         folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificados', 'qr'))
#         # folder = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'evaluaciondocente')
#         rutapdf = folder + qrname + '.pdf'
#         rutaimg = folder + qrname + '.png'
#         if os.path.isfile(rutapdf):
#             os.remove(rutaimg)
#             os.remove(rutapdf)
#
#         url = pyqrcode.create('http://sga.unemi.edu.ec//media/qrcode/certificados/' + qrname + '.pdf')
#
#         imageqr = url.png(folder + qrname + '.png', 16, '#000000')
#         data['qrname'] = 'qr' + qrname
#         valida = conviert_html_to_pdfsaveqrcertificado(
#             'adm_capacitacioneventoperiodoipec/certificado_pdf.html',
#             {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
#         )
#         if valida:
#             os.remove(rutaimg)
#             inscrito.rutapdf = 'qrcode/certificados/' + qrname + '.pdf'
#             inscrito.save()

# i=1
# inscritoscongreso = InscritoCongreso.objects.filter(status=True,rutapdf__isnull=True,persona_emailnotifica__isnull=True, congreso__rubro__status=False).distinct()
# for inscritoc in inscritoscongreso:
#     if not  inscritoc.cancelo_rubro():
#         congreso = inscritoc.congreso
        # data = {}
        # data['congreso'] = congreso = inscritoc.congreso
        # persona=inscritoc.persona_emailnotifica
        # data['elabora_persona'] = persona
        # data['inscrito'] = inscritoc
        # mes = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre","octubre", "noviembre", "diciembre"]
        # qrname = 'qr_certificado_' + str(inscritoc.id)+str(inscritoc.congreso_id)
        # folder = os.path.join(os.path.join(SITE_STORAGE, 'media','certificadoscongresoinscrito',''))
        # rutapdf = folder + qrname + '.pdf'
        # if os.path.isfile(rutapdf):
        #     os.remove(rutapdf)
        #
        # url = pyqrcode.create('http://sga.unemi.edu.ec//media/certificadoscongresoinscrito/' + qrname + '.pdf')
        # valida = conviert_html_to_pdfsaveqrcertificado(
        #     'congreso/certificado_pdf.html',
        #     {'pagesize': 'A4', 'data': data},qrname + '.pdf'
        # )
        # if valida:
        #     inscritoc.rutapdf = '/certificadoscongresoinscrito/' + qrname + '.pdf'
        #     inscritoc.save()
        # inscritoc.status=False
        # inscritoc.save()
        # print("%s - %s - %s"%(i,inscritoc, congreso))
        # i+=1


from sga.models import *
i=1
periodo1=Periodo.objects.get(id=96)
periodo2=Periodo.objects.get(id=97)
materiasid = Materia.objects.values_list('id').filter(status=True, nivel__periodo=periodo1, esintroductoria=False, asignaturamalla__malla__carrera__in=[126,127,128,129,130,131,132,135]).distinct()
clases =Clase.objects.filter(status=True,materia__id__in=materiasid )
for clase in clases:
    if Materia.objects.filter(asignatura=clase.materia.asignatura,status=True, nivel__periodo=periodo2, esintroductoria=False, asignaturamalla__malla__carrera=clase.materia.carrera(),paralelomateria=clase.materia.paralelomateria,asignaturamalla=clase.materia.asignaturamalla,asignaturamalla__nivelmalla_id__lte=3).exists():
        materiafutura=Materia.objects.filter(asignatura=clase.materia.asignatura,status=True, nivel__periodo=periodo2, esintroductoria=False, asignaturamalla__malla__carrera=clase.materia.carrera(),paralelomateria=clase.materia.paralelomateria,asignaturamalla=clase.materia.asignaturamalla,asignaturamalla__nivelmalla_id__lte=3)[0]
        clase_clon = Clase(materia=materiafutura,
                           turno=clase.turno,
                           inicio=materiafutura.inicio,
                           fin=materiafutura.fin,
                           aula=clase.aula,
                           tipohorario=2,
                           dia=clase.dia,
                           activo=True)
        clase_clon.save()
        print("%s - %s "%(i,clase_clon))
        i+=1
