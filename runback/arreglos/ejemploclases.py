import openpyxl
# from django.template.loader import get_template
import json

from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa
import os
from urllib.request import urlopen, Request
# import requests

def taller_diez_mayo():
    miarchivo = openpyxl.load_workbook("ejemploclases.xlsx")
    lista = miarchivo.get_sheet_by_name('Hoja1')
    totallista = lista.rows
    total=18
    contador=0
    for filas in totallista:
        contador += 1
        if contador>2:
            cedula=str(filas[0].value)
            telefono=str(filas[3].value)
            print(cedula)
            filas[1].value = "REGISTRO MODIFICADO"
    miarchivo.save("ejemploclases.xlsx")

    # Imprimir una lista de números del 1 al 5:
    for i in range(1, 6):
        print(i)

    # Sumar los elementos de una lista:
    lista = [1, 2, 3, 4, 5]
    suma = 0
    for elemento in lista:
        suma += elemento
    print(suma)

    # Imprimir los caracteres de una cadena de texto:
    texto = "Hola mundo"
    for caracter in texto:
        print(caracter)

    # Recorrer un diccionario e imprimir sus claves y valores:
    diccionario = {'a': 1, 'b': 2, 'c': 3}
    for clave, valor in diccionario.items():
        print(clave, valor)

    # Iterar a través de una lista y realizar una acción para cada elemento que cumpla una condición:
    lista = [1, 2, 3, 4, 5]
    for elemento in lista:
        if elemento % 2 == 0:
            print(elemento, "es par")
            lista.remove(elemento)
        else:
            print(elemento, "es impar")
            lista.pop(elemento)
    print(lista)


    arra = [
    {'idr': 2932059, 'nota': 86, 'asistencia': 80, 'estado': 'APROBADO'},
    {'idr': 2919062, 'nota': 88, 'asistencia': 93, 'estado': 'APROBADO'},
    {'idr': 2939486, 'nota': 92, 'asistencia': 100, 'estado': 'APROBADO'},
    {'idr': 2940444, 'nota': 77, 'asistencia': 95, 'estado': 'APROBADO'},
    {'idr': 2941498, 'nota': 77, 'asistencia': 95, 'estado': 'APROBADO'},
    {'idr': 2938462, 'nota': 83, 'asistencia': 91, 'estado': 'APROBADO'},
    {'idr': 2930740, 'nota': 96, 'asistencia': 100, 'estado': 'APROBADO'},
    {'idr': 2935872, 'nota': 84, 'asistencia': 88, 'estado': 'APROBADO'},
    {'idr': 2921637, 'nota': 91, 'asistencia': 100, 'estado': 'APROBADO'},
    {'idr': 2940979, 'nota': 84, 'asistencia': 100, 'estado': 'APROBADO'}
    ]
    for x in arra:
        print(x.get("idr"))
        print(x.get("nota"))
        print(x.get("asistencia"))
        print(x.get("estado"))

def taller_17_mayo():
    estudiantes = [
        {'nombre': 'Kerly', 'carrera': 'Soft', 'sexo': 'M', 'estado': 'Medio', 'promedio': 80, 'asistencia': 100,
         'beca': False, 'deuda': 23.50, 'tipo': ''},
        {'nombre': 'Andres', 'carrera': 'Soft', 'sexo': 'H', 'estado': 'Medio alto', 'promedio': 92, 'asistencia': 95,
         'beca': False, 'deuda': 0, 'tipo': ''},
        {'nombre': 'Fernando', 'carrera': 'Soft', 'sexo': 'H', 'estado': 'Medio bajo', 'promedio': 98, 'asistencia': 80,
         'beca': False, 'deuda': 0, 'tipo': ''},
        {'nombre': 'Karla', 'carrera': 'Bio', 'sexo': 'M', 'estado': 'Bajo', 'promedio': 99, 'asistencia': 98,
         'beca': False, 'deuda': 0, 'tipo': ''},
        {'nombre': 'Manuel', 'carrera': 'Bio', 'sexo': 'H', 'estado': 'Alto', 'promedio': 90, 'asistencia': 99,
         'beca': False, 'deuda': 0, 'tipo': ''},
        {'nombre': 'Anna', 'carrera': 'Bio', 'sexo': 'M', 'estado': 'Bajo', 'promedio': 85, 'asistencia': 93,
         'beca': False, 'deuda': 0, 'tipo': ''},
        {'nombre': 'Brianna', 'carrera': 'Ali', 'sexo': 'M', 'estado': 'Bajo', 'promedio': 88, 'asistencia': 92,
         'beca': False, 'deuda': 0, 'tipo': ''},
        {'nombre': 'Ivan', 'carrera': 'Ali', 'sexo': 'H', 'estado': 'Medio bajo', 'promedio': 92, 'asistencia': 90,
         'beca': False, 'deuda': 0, 'tipo': ''},
        {'nombre': 'Tom', 'carrera': 'Ind', 'sexo': 'H', 'estado': 'Medio alto', 'promedio': 93, 'asistencia': 85,
         'beca': False, 'deuda': 0, 'tipo': ''},
        {'nombre': 'Omar', 'carrera': 'Ind', 'sexo': 'H', 'estado': 'Alto', 'promedio': 95, 'asistencia': 89,
         'beca': False, 'deuda': 0, 'tipo': ''},
    ]
    for x in estudiantes:
        if x.get("promedio") >=95 and x.get("asistencia")>=90 and x.get("deuda") == 0:
            x['beca'] = True
            x['tipo'] = 'A'
        elif x.get("promedio") >=80 and x.get("asistencia")>=90 and x.get("deuda") == 0 and x.get("estado") in  ['Bajo','Medio Bajo']:
            x['beca'] = True
            x['tipo'] = 'S'
    print(estudiantes)
# taller_17_mayo()

def taller_17_mayo_ejerciciojson():
    profesores=[]
    profesores_presentar=[]
    # archivo=open('publicacion.json',"r")
    # datos=json.load(archivo)
    #
    with open('publicacion.json') as f:
        data = json.load(f)
        for x in data:
            if not x.get("cedula") in profesores:
                profesores_presentar.append({"nombres": x.get("apellidos"),"cedula":x.get("cedula")})
                profesores.append(x.get("cedula"))
        print(len(profesores))
        cantidad_articulos=0
        for profesor in profesores_presentar:
            cantidad_articulos = 0
            for y in data:
                if y.get("cedula") == profesor.get("cedula"):
                    cantidad_articulos+=1
            print(profesor)
            print(cantidad_articulos)
    print(data)
# Función para convertir HTML a PDF
def convert_html_to_pdf(html_file, pdf_file, context):
    # Configurar el entorno de Jinja2
    env = Environment(loader=FileSystemLoader(os.path.dirname(html_file)))

    # Cargar el archivo HTML y renderizar con el contexto
    template = env.get_template(os.path.basename(html_file))
    rendered_html = template.render(context)

    # Convertir HTML a PDF
    with open(pdf_file, 'w+b') as file:
        pisa_status = pisa.CreatePDF(rendered_html, dest=file)

    if not pisa_status.err:
        print("PDF creado correctamente.")
    else:
        print(f"Error al crear el PDF: {pisa_status.err}")

def taller_23_pdf():
    # instalar jinja2 3.0.3
    usuario = {}
    usuario['Nombre'] = 'Jussibeth Tatiana'
    usuario['Apellido'] = 'Places Chungata'
    usuario['Cedula'] = '0928323765'
    usuario['Sexo'] = 'Femenino'
    usuario['FechaNacimiento'] = '05 de febrero 1993'
    usuario['Correo'] = 'jplacesc@unemi.edu.ec'
    usuario['Estado_civil'] = 'Casada'
    usuario['Domicilio'] = 'Milagro'
    usuario['Formacion'] = 'Estudiante'
    usuario['Curso'] = '2do Semestre'
    usuario['Firmas'] = 'Eduardo Quinteros'
    context = {'usuario': usuario}

    # Ruta del archivo HTML de origen
    html_file = 'archivo.html'

    # Ruta del archivo PDF de destino
    pdf_file = 'archivo.pdf'


    # Convertir HTML a PDF con el contexto
    convert_html_to_pdf(html_file, pdf_file, context)

def taller_31_mayo():
    url = 'https://sga.unemi.edu.ec/api?a=apirevistas'
    print(url)
    req = Request(url)
    response = urlopen(req)
    result = json.loads(response.read().decode())
    # print(result)
    context = {'data1': result}
    # Configurar el entorno de Jinja2
    env = Environment(loader=FileSystemLoader(os.path.dirname("vistadataapi.html")))
    # Cargar el archivo HTML y renderizar con el contexto
    template = env.get_template(os.path.basename("vistadataapi.html"))
    rendered_html = template.render(context)
    print(rendered_html)
    # Guardar el contenido HTML en un archivo (opcional)
    with open("presentaciondataapi.html", "w") as file:
        file.write(rendered_html)
def taller_31_mayov2():
    # Realizar una solicitud GET a la API
    response = requests.get("https://sga.unemi.edu.ec/api?a=apiareasconocimiento")

    # Verificar el código de respuesta
    if response.status_code == 200:
        # La solicitud fue exitosa
        data = response.json()  # Convertir la respuesta en formato JSON a un diccionario de Python
        # Trabajar con los datos obtenidos
        print(data)
    else:
        # La solicitud no fue exitosa
        print("Error al realizar la solicitud. Código de respuesta:", response.status_code)

taller_23_pdf()
# taller_31_mayo()
# taller_31_mayov2()