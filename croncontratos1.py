#!/usr/bin/env python
import csv
import os
import sys

import xlrd
from docx import Document
from settings import USA_TIPOS_INSCRIPCIONES, TIPO_INSCRIPCION_INICIAL, DIAS_MATRICULA_EXPIRA

# import urllib2
# Full path and name to your csv file
# from django.db.backends.oracle.base import to_unicode
# from apt.package import Record
# from __builtin__ import file
# from IPython.lib.editorhooks import mate
# from numpy.core.records import record
# from numpy.matrixlib.defmatrix import matrix
SITE_ROOT = os.path.dirname(os.path.realpath(__file__))

your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from sga.models import *
from sagest.models import *


def fecha_letra(valor):
    mes = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    d = int(valor[0:2])
    m = int(valor[3:5])
    a = int(valor[6:10])
    if d == 1:
        return u"al %s día del mes de %s del %s" % (numero_a_letras(d), str(mes[m - 1]), numero_a_letras(a))
    else:
        return u"a los %s días del mes de %s del %s" % (numero_a_letras(d), str(mes[m - 1]), numero_a_letras(a))

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
    if numero_entero <= 99:
        resultado = leer_decenas(numero_entero)
    elif numero_entero <= 999:
        resultado = leer_centenas(numero_entero)
    elif numero_entero <= 999999:
        resultado = leer_miles(numero_entero)
    elif numero_entero <= 999999999:
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
        posicion = numero.split('.')
        numero_entero = int(posicion[0])
        parte_decimal = 0
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
    if millar == 1:
        resultado = ''
    if 2 <= millar <= 9:
        resultado = UNIDADES[millar]
    elif 10 <= millar <= 99:
        resultado = leer_decenas(millar)
    elif 100 <= millar <= 999:
        resultado = leer_centenas(millar)
    resultado = '%s mil' % resultado
    if centena > 0:
        resultado = '%s %s' % (resultado, leer_centenas(centena))
    return resultado


def leer_millones(numero):
    millon, millar = divmod(numero, 1000000)
    resultado = ''
    if millon == 1:
        resultado = ' un millon '
    if 2 <= millon <= 9:
        resultado = UNIDADES[millon]
    elif 10 <= millon <= 99:
        resultado = leer_decenas(millon)
    elif 100 <= millon <= 999:
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






#contrato talento humano
# arreglo_campo_contrato_indefinido = [1,44,8,38,40,93,94,95,96,4,97,98,35,3,50,9,2,100,5,99]
# contrato_id=65
# arreglo_campo_contrato_relacion_dependencia = [1,44,8,38,40,93,66,94,95,96,4,97,98,102,103,104,105,106,107,108,79,109,3,50,110,9,111,2,37,100,5,113,112,99,36,114]
# contrato_id=66
arreglo_campo_contrato_honorarios = [1,44,8,117,118,4,97,5,94,93,95,66,109,53,6,119,120,50,9,103,104,105,106,107,108,121,122,123,124,2,57,3,125,38,40,126,127,128,129,130,131,132,133,134,135,136,137,138,139,140]
contrato_id=67
workbook = xlrd.open_workbook("HONORARIOS PROFESIONALES.xlsx")
# workbook = xlrd.open_workbook("CT_IND_2020 - subir.xlsx")
sheet = workbook.sheet_by_index(0)
n1 = 1
for rowx in range(sheet.nrows):
    row = sheet.row_values(rowx)
    if n1>1:
        cedula=row[0].strip()
        fecha = str(row[2]).strip()
        anio = fecha.split('-')[2]
        mes = fecha.split('-')[1]
        # cantidad=20
        persona = Persona.objects.get(cedula=cedula)
        if ContratoPersona.objects.filter(persona=persona, contrato_id=contrato_id).exists():
            contratopersona = ContratoPersona.objects.filter(persona=persona, contrato_id=contrato_id)[0]
        else:
            contratopersona = ContratoPersona(persona=persona,
                                              contrato_id=contrato_id)
            contratopersona.save()


        nombre_plantilla = contratopersona.contrato.archivo.file.name
        nombre_contrato = str(contratopersona.id) + ".docx"
        direccion_contrato = os.path.join(SITE_STORAGE, 'media', 'contratos', 'contrato')
        filename_contrato = os.path.join(direccion_contrato, nombre_contrato)
        # guarda la direccion
        cantidad_parrafo = 0
        document = Document(nombre_plantilla)
        i = 0
        for elemento in arreglo_campo_contrato_honorarios:
            codigo = u"%s-%s-%s" % (anio, mes, persona.id)
            i+=1
            if ContratoPersonaDetalle.objects.filter(contratopersona=contratopersona,campos_id=int(elemento)).exists():
                if int(elemento) != 1:
                    contratopersonadetalle = ContratoPersonaDetalle.objects.filter(contratopersona=contratopersona,campos_id=int(elemento))[0]
                    contratopersonadetalle.valor = str(row[i]).strip()
                    contratopersonadetalle.save()
            else:
                if int(elemento) == 1:
                    contratopersonadetalle = ContratoPersonaDetalle(contratopersona=contratopersona,
                                                                    campos_id=int(elemento),
                                                                    valor=codigo)
                else:
                    contratopersonadetalle = ContratoPersonaDetalle(contratopersona=contratopersona,
                                                                    campos_id=int(elemento),
                                                                    valor=str(row[i]).strip())
                contratopersonadetalle.save()

            parrafo = document.paragraphs
            cantidad_parrafo = parrafo.__len__()
            n = 0
            campo = CamposContratos.objects.filter(pk=int(elemento))[0]
            if campo.script[:11] == 'JAVASCRIPT:':
                campo1 = str(row[i]).strip()
                valor = ''
                try:
                    funcion = campo.script[11:].split('(')[0]
                    if funcion == 'fecha_letra':
                        valor = fecha_letra(campo1)
                    if funcion == 'numero_a_moneda':
                        valor = numero_a_moneda(campo1)

                except:
                    pass
                campo_buscar = '${campo' + str(campo.id) + '}'
                for n in range(cantidad_parrafo):
                    parrafo[n].text = parrafo[n].text.replace(campo_buscar, valor)
                    n += 1
            else:
                if int(elemento) == 1:
                    reemplazar = codigo
                else:
                    reemplazar = str(row[i]).strip()
                campo_buscar = '${campo' + str(campo.id) + '}'
                for n in range(cantidad_parrafo):
                    parrafo[n].text = parrafo[n].text.replace(campo_buscar, reemplazar)
                    n += 1











            campo_buscar = '${campo' + str(campo.id) + '}'
            for n in range(cantidad_parrafo):
                if int(elemento) == 1:
                    reemplazar = codigo
                else:
                    reemplazar = str(row[i]).strip()
                parrafo[n].text = parrafo[n].text.replace(campo_buscar, reemplazar)
                n += 1
            n = 0
            persona_nombre = contratopersona.persona.nombre_titulo()
            persona_cedula = contratopersona.persona.cedula
            persona_ruc = u'%s001' % contratopersona.persona.cedula
            cadena1 = '${empleado}'
            cadena2 = '${cedula}'
            cadena3 = '${ruc}'
            for n in range(cantidad_parrafo):
                parrafo[n].text = parrafo[n].text.replace(cadena1, persona_nombre)
                parrafo[n].text = parrafo[n].text.replace(cadena2, persona_cedula)
                parrafo[n].text = parrafo[n].text.replace(cadena3, persona_ruc)
                n += 1
            document.save(filename_contrato)
        contratopersona.archivo.name = "contratos/contrato/%s" % nombre_contrato
        contratopersona.save()
    n1+=1
    print(n1)




