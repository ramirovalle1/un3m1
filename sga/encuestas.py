# -*- coding: latin-1 -*-
import json
import csv
import random
from django.contrib import messages
from django.contrib.auth.models import Group
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.template.loader import get_template
from reportlab.lib.enums import TA_LEFT
from decorators import secure_module, last_access
from settings import ARCHIVO_TIPO_GENERAL
from sga.commonviews import adduserdata, obtener_reporte
from sga.forms import EncuestaForm, ImportarEncuestaForm, EncuestaIndicadoresModalForm, EncuestaAmbitoModalForm
from sga.funciones import log, generar_nombre, null_to_decimal
from sga.funcionesxhtml2pdf import add_titulo_reportlab, add_tabla_reportlab, add_graficos_circular_reporlab, \
    add_graficos_barras_reportlab, generar_pdf_reportlab
from sga.models import Encuesta, InstrumentoEvaluacion, AmbitoEvaluacion, IndicadorEvaluacion, \
    AmbitoInstrumentoEvaluacion, IndicadorAmbitoInstrumentoEvaluacion, \
    Archivo, MuestraEncuesta, Persona, RespuestaEncuesta, Carrera, DatoRespuestaEncuesta, MuestraGrupoEncuesta, \
    TipoRespuesta
from sga.templatetags.sga_extras import encrypt
from xlwt import *


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = EncuestaForm(request.POST)
                if f.is_valid():
                    if Encuesta.objects.filter(nombre=f.cleaned_data['nombre'].upper()).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe una encuesta con ese nombre"})

                    if f.cleaned_data['porfacultades']:
                        if 'facultades' in request.POST:
                            if len(request.POST['facultades']) == 0:
                                return JsonResponse({"result": "bad", "mensaje": u"Debe adicionar al menos una coordinación"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Debe adicionar al menos una coordinación"})

                    if f.cleaned_data['pordepartamentos']:
                        if 'departamentos' in request.POST:
                            if len(request.POST['departamentos']) == 0:
                                return JsonResponse({"result": "bad", "mensaje": u"Debe adicionar al menos un departamento"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Debe adicionar al menos un departamento"})

                    if f.cleaned_data['porregimenlaboral']:
                        if 'regimenlaboral' in request.POST:
                            if len(request.POST['regimenlaboral']) == 0:
                                return JsonResponse({"result": "bad", "mensaje": u"Debe adicionar al menos un régimen laboral"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Debe adicionar al menos un régimen laboral"})

                    if not f.cleaned_data['pindependientes']:
                        if f.cleaned_data['tiporespuesta']:
                            pass
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Debe adicionar tipo de respuesta."})

                    encuesta = Encuesta(nombre=f.cleaned_data['nombre'],
                                        leyenda=f.cleaned_data['leyenda'],
                                        fechainicio=f.cleaned_data['fechainicio'],
                                        fechafin=f.cleaned_data['fechafin'],
                                        activa=False,
                                        matriculados=f.cleaned_data['matriculados'],
                                        obligatoria=f.cleaned_data['obligatoria'],
                                        pindependientes=f.cleaned_data['pindependientes'],
                                        conmuestra=f.cleaned_data['conmuestra'],
                                        observaciondetallada=f.cleaned_data['observaciondetallada'],
                                        observaciongeneral=f.cleaned_data['observaciongeneral'],
                                        labelobservacion=f.cleaned_data['labelobservacion'],
                                        tiporespuesta=f.cleaned_data['tiporespuesta'],
                                        muestra=f.cleaned_data['muestra'],
                                        sexo=f.cleaned_data['sexo'],
                                        porfacultades=f.cleaned_data['porfacultades'],
                                        pordepartamentos=f.cleaned_data['pordepartamentos'],
                                        porregimenlaboral=f.cleaned_data['porregimenlaboral'],
                                        instrumento=None)
                    encuesta.save(request)

                    for g in f.cleaned_data['grupos']:
                        encuesta.grupos.add(g)

                    for g in f.cleaned_data['exclude_grupos']:
                        encuesta.exclude_grupos.add(g)

                    if f.cleaned_data['porfacultades']:
                        for g in f.cleaned_data['facultades']:
                            encuesta.facultades.add(g)

                    if f.cleaned_data['pordepartamentos']:
                        for g in f.cleaned_data['departamentos']:
                            encuesta.departamentos.add(g)

                    if f.cleaned_data['porregimenlaboral']:
                        for g in f.cleaned_data['regimenlaboral']:
                            encuesta.regimenlaboral.add(g)

                    if f.cleaned_data['muestra']:
                        for muestragrupo in json.loads(request.POST['lista_items1']):
                            muestragrupoencuesta = MuestraGrupoEncuesta(encuesta = encuesta,
                                                                        grupo_id=encrypt(muestragrupo['idg']),
                                                                        muestra=muestragrupo['valor'])
                            muestragrupoencuesta.save(request)
                            log(u'Adiciono muestra de grupo a encuesta: encuesta(%s)[%s] - grupo(%s) - muestra(%s)' % (encuesta, encuesta.id, muestragrupoencuesta.grupo, muestragrupoencuesta.muestra), request, "add")
                    log(u'Adiciono encuesta: %s' % encuesta, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'edit':
            try:
                encuesta = Encuesta.objects.get(pk=request.POST['id'])
                f = EncuestaForm(request.POST)
                if f.is_valid():
                    encuesta.nombre = f.cleaned_data['nombre']
                    encuesta.leyenda = f.cleaned_data['leyenda']
                    encuesta.fechainicio = f.cleaned_data['fechainicio']
                    encuesta.fechafin = f.cleaned_data['fechafin']
                    encuesta.activa = False
                    encuesta.matriculados = f.cleaned_data['matriculados']
                    encuesta.obligatoria = f.cleaned_data['obligatoria']
                    encuesta.conmuestra = f.cleaned_data['conmuestra']
                    encuesta.observaciondetallada = f.cleaned_data['observaciondetallada']
                    encuesta.observaciongeneral = f.cleaned_data['observaciongeneral']
                    encuesta.labelobservacion = f.cleaned_data['labelobservacion']
                    encuesta.tiporespuesta = f.cleaned_data['tiporespuesta']
                    encuesta.tiporespuesta = f.cleaned_data['tiporespuesta']
                    encuesta.muestra = f.cleaned_data['muestra']
                    encuesta.sexo = f.cleaned_data['sexo']
                    encuesta.pindependientes = f.cleaned_data['pindependientes']
                    encuesta.porfacultades=f.cleaned_data['porfacultades']
                    encuesta.pordepartamentos=f.cleaned_data['pordepartamentos']
                    encuesta.porregimenlaboral=f.cleaned_data['porregimenlaboral']
                    encuesta.save(request)

                    for g in encuesta.grupos.all():
                        encuesta.grupos.remove(g)
                    for g in encuesta.exclude_grupos.all():
                        encuesta.exclude_grupos.remove(g)
                    for g in encuesta.departamentos.all():
                        encuesta.departamentos.remove(g)
                    for g in encuesta.facultades.all():
                        encuesta.facultades.remove(g)

                    for g in f.cleaned_data['grupos']:
                        encuesta.grupos.add(g)

                    for g in f.cleaned_data['exclude_grupos']:
                        encuesta.exclude_grupos.add(g)

                    if f.cleaned_data['porfacultades']:
                        for g in f.cleaned_data['facultades']:
                            encuesta.facultades.add(g)

                    if f.cleaned_data['porregimenlaboral']:
                        for g in f.cleaned_data['regimenlaboral']:
                            encuesta.regimenlaboral.add(g)

                    if f.cleaned_data['pordepartamentos']:
                        for g in f.cleaned_data['departamentos']:
                            encuesta.departamentos.add(g)

                    if f.cleaned_data['muestra']:
                        listamuestragrupo = json.loads(request.POST['lista_items1'])
                        for muestragrupo in listamuestragrupo:
                            idgrupo = int(encrypt(muestragrupo['idg']))
                            muestra = int(muestragrupo['valor'])
                            registrogrupo = encuesta.muestragrupoencuesta_set.filter(grupo_id=idgrupo)
                            if not registrogrupo.values('id').exists():
                                muestragrupoencuesta = MuestraGrupoEncuesta(encuesta=encuesta, grupo_id=idgrupo, muestra=muestra)
                                muestragrupoencuesta.save(request)
                                log(u'Adiciono muestra de grupo a encuesta: encuesta(%s)[%s] - grupo(%s) - muestra(%s)' % (encuesta, encuesta.id, muestragrupoencuesta.grupo, muestragrupoencuesta.muestra), request, "add")
                            elif registrogrupo.values('id').exists():
                                if not muestra == registrogrupo[0].muestra:
                                    muestgrup = registrogrupo[0]
                                    muestgrup.muestra = muestra
                                    muestgrup.save(request)
                                    log(u'Edito muestra de grupo a encuesta: encuesta(%s)[%s] - grupo(%s) - muestra(%s)' % (encuesta, encuesta.id, muestgrup.grupo, muestgrup.muestra), request, "edit")
                        for eliminargrupo in encuesta.muestragrupoencuesta_set.filter(status=True).exclude(grupo_id__in=[int(encrypt(muestragrupo['idg'])) for muestragrupo in listamuestragrupo]):
                            log(u'Elimino muestra de grupo a encuesta: encuesta(%s)[%s] - grupo(%s) - muestra(%s)' % (encuesta, encuesta.id, eliminargrupo.grupo, eliminargrupo.muestra), request,"del")
                            eliminargrupo.delete()
                    else:
                        encuesta.muestragrupoencuesta_set.filter(status=True).delete()
                        log(u'Elimino toda las muestra de encuesta: %s[%s]' % (encuesta, encuesta.id), request, "del")
                    log(u'Modifico encuesta: %s' % encuesta, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})

        if action == 'delencuestados':
            try:
                encuestado = RespuestaEncuesta.objects.get(pk=request.POST['id'])
                log(u'Elimino encuesta de: %s' % encuestado, request, "del")
                encuestado.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'importar':
            try:
                form = ImportarEncuestaForm(request.POST, request.FILES)
                if form.is_valid():
                    arch = request.FILES['archivo']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]

                    if not exte.lower() == 'csv':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .csv"})

                    if arch.size > 4194304:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})

                    nfile = request.FILES['archivo']
                    nfile._name = generar_nombre("importacion_", nfile._name)
                    archivo = Archivo(nombre='IMPORTACION MUESTRAS',
                                      fecha=datetime.now().date(),
                                      archivo=nfile,
                                      tipo_id=ARCHIVO_TIPO_GENERAL)
                    archivo.save(request)
                    datareader = csv.reader(open(archivo.archivo.file.name, "rU"), delimiter=',')
                    linea = 1
                    encuesta = Encuesta.objects.get(pk=request.POST['id'])
                    for row in datareader:
                        if linea > 1:
                            if MuestraEncuesta.objects.filter(persona__cedula=row[0], encuesta=encuesta).exists():
                                return JsonResponse({"result": "bad", "mensaje": u"Existe una muestra en la encuesta con esta identificacion: " + row[0]})
                            persona = Persona.objects.get(cedula=row[0])
                            muestraenc = MuestraEncuesta(encuesta=encuesta, persona=persona)
                            muestraenc.save(request)
                            log(u'Importo muestra-encuesta: %s' % encuesta, request, "add")
                        linea += 1
                        print(linea)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

        if action == 'resultadoencuesta':
            try:
                encuesta = Encuesta.objects.get(pk=int(encrypt(request.POST['id'])))
                idcarrera = None
                if 'idc' in request.POST:
                    idcarrera = int(request.POST['idc']) if int(request.POST['idc'])>0 else None
                literales_generales_pregunta = encuesta.literales_de_respuesta()
                ambitos_encuesta = encuesta.ambitos()
                add_titulo_reportlab(descripcion=" DIRECCIÓN DE EVALUACIÓN Y ASEGURAMIENTO DE LA CALIDAD", tamano=12, espacios=19)
                add_titulo_reportlab(descripcion=" RESULTADOS ENCUESTA DE SATISFACCIÓN DE ESTUDIANTES", tamano=12, espacios=19)
                add_titulo_reportlab(descripcion=" Información general de la encuesta:", tamano=12, espacios=19, alineacion=TA_LEFT, tipoletra='Helvetica')
                for grupo in encuesta.grupos_encuentas():
                    nombre = u'%s %s %s' % (grupo.name.capitalize(),('matriculados ' if encuesta.matriculados else '') + 'a encuestar:', encuesta.total_encuestar_por_grupo(grupo.id))
                    add_titulo_reportlab(descripcion=nombre, tamano=12, espacios=19, alineacion=TA_LEFT, tipoletra='Helvetica')
                add_titulo_reportlab(descripcion='Cantidad de preguntas: ' + encuesta.cantidad_indicadores().__str__(), tamano=12, espacios=19, alineacion=TA_LEFT, tipoletra='Helvetica')
                for grupo in encuesta.grupos_encuentas():
                    if grupo.id == 2 or grupo.id==1:

                        # RESULTADOS GENERALES
                        total = encuesta.total_encuestar_por_grupo(grupo.id)
                        total_porcentaje = null_to_decimal((total*100/total), 2)
                        total_encuestado = encuesta.total_encuestado_por_grupo(grupo.id)
                        total_encuestado_porcentaje = null_to_decimal((total_encuestado*100/total), 2)
                        total_no_encuestado = encuesta.total_encuestar_por_grupo(grupo.id) - encuesta.total_encuestado_por_grupo(grupo.id)
                        total_no_encuestado_porcentaje = null_to_decimal((total_no_encuestado*100/total), 2)
                        detalle = [('Encuestados', total_encuestado, total_encuestado_porcentaje.__str__() + '%'), ('No encuestados', total_no_encuestado, total_no_encuestado_porcentaje.__str__() + '%'), ('Total', total , total_porcentaje.__str__() + '%')]
                        add_titulo_reportlab(descripcion="RESULTADOS GENERALES", tamano=12, espacios=19)
                        add_tabla_reportlab(encabezado=[(grupo.name.capitalize().__str__(), 'Total', 'Porcentaje de población y muestra')],
                                            detalles=detalle, anchocol=[150, 50, 150], cabecera_left_center=[False, True, True], detalle_left_center=[False, True, True])
                        add_graficos_circular_reporlab(datavalor=[total_encuestado_porcentaje, total_no_encuestado_porcentaje], datanombres=[detalle[0][0].__str__(), detalle[1][0].__str__()],
                                                       anchografico=125, altografico=125, posiciongrafico_x=180, posiciongrafico_y=30,
                                                       titulo='Porcentaje de población y muestra', tamanotitulo=10, ubicaciontitulo_x=60, ubicaciontitulo_y=12, mostrarsignoporcentaje=True)
                        # cabecera
                        listacabecera = []
                        listaanchocolumna = [24, 150]
                        cabecera_left_center = [True, False]
                        listaliteralcabecera = ['Nº', 'Ámbitos']
                        for literal in literales_generales_pregunta:
                            listaliteralcabecera.append(literal.nombre.capitalize().__str__())
                            listaanchocolumna.append(40 if literal.nombre.__len__()<4 else 75)
                            cabecera_left_center.append(True)
                        listacabecera.append(listaliteralcabecera)
                        # detalles
                        listadetalles = []
                        listaambitos_barras=[]
                        listaliterales_barras=[]
                        listaliterales_barras_porcentaje=[]
                        contador = 1
                        for ambito in ambitos_encuesta:
                            aux = [contador, ambito.nombre]
                            aux1 = []
                            aux2 = []
                            listaambitos_barras.append(ambito.nombre)
                            total_encuestado_por_ambito = encuesta.total_encuestado_por_ambito_todo_literal(grupo.id, ambito.id)
                            for literal in literales_generales_pregunta:
                                total = encuesta.total_encuestado_por_ambito_segun_literal(grupo.id, ambito.id, literal.id)
                                aux.append(total)
                                aux1.append(total)
                                aux2.append(null_to_decimal((total * 100 / total_encuestado_por_ambito), 2))
                            listadetalles.append(aux)
                            listaliterales_barras.append(aux1)
                            listaliterales_barras_porcentaje.append(aux2)
                            contador += 1
                        # acomodando lista para presentar en barras
                        lista_acomodada_literales = []
                        lista_acomodada_literales_porcentaje = []
                        contador = 0
                        while contador < listaliteralcabecera.__len__() - 2:
                            aux = []
                            aux1 = []
                            for listaliteral in listaliterales_barras:
                                if contador <= listaliterales_barras.__len__()-1:
                                    aux.append(listaliteral[contador])
                            for listaliteral in listaliterales_barras_porcentaje:
                                if contador <= listaliterales_barras_porcentaje.__len__()-1:
                                    aux1.append(listaliteral[contador])
                            contador +=1
                            lista_acomodada_literales.append(aux)
                            lista_acomodada_literales_porcentaje.append(aux1)
                        add_titulo_reportlab(descripcion=grupo.name.upper().__str__()+" QUE CONSTESTARON LA ENCUESTA", tamano=12, espacios=19)
                        add_tabla_reportlab(encabezado=listacabecera, detalles=listadetalles,
                                            anchocol=listaanchocolumna, cabecera_left_center=cabecera_left_center, detalle_left_center=cabecera_left_center)
                        add_graficos_barras_reportlab(datavalor=lista_acomodada_literales, datanombres=listaambitos_barras,
                                                      anchografico=500, altografico=125, tamanoletra=6, posiciongrafico_x=25, posiciongrafico_y=30,
                                                      titulo='Respuestas por ámbitos en números', tamanotitulo=10, ubicaciontitulo_x=225, ubicaciontitulo_y=17,
                                                      posicionleyenda_x=430, mostrarleyenda=False, barra_vertical_horizontal=True, presentar_nombre_o_numero=False)
                        add_graficos_barras_reportlab(datavalor=lista_acomodada_literales_porcentaje, datanombres=listaambitos_barras,
                                                      anchografico=500, altografico=125, tamanoletra=6, posiciongrafico_x=25, posiciongrafico_y=30,
                                                      titulo='Respuestas por ámbitos en porcentajes', tamanotitulo=10, ubicaciontitulo_x=225, ubicaciontitulo_y=17, minimo=0 , maximo=100, step=20,
                                                      posicionleyenda_x=430, mostrarleyenda=False, barra_vertical_horizontal=True, presentar_nombre_o_numero=False, decimal=True)
                        # RESULTADOS POR INDICADORES
                        # cabecera
                        listacabecera = []
                        listaanchocolumna = [24, 200]
                        listaliteralcabecera = ['Nº', '']
                        cabecera_left_center = [True, False]
                        for literal in literales_generales_pregunta:
                            listaliteralcabecera.append(literal.nombre.capitalize().__str__())
                            listaanchocolumna.append(40 if literal.nombre.__len__() < 4 else 75)
                            cabecera_left_center.append(True)
                        listacabecera.append(listaliteralcabecera)
                        # presentando por carrera
                        for carrera in encuesta.extraer_carreras_estudiante(grupo.id, idcarrera):
                            add_titulo_reportlab(descripcion=carrera.__str__(), tamano=13, espacios=19)
                            add_titulo_reportlab(descripcion="RESULTADOS POR INDICADORES", tamano=12, espacios=19)
                            for ambito in ambitos_encuesta:
                                listacabecera[0][1] = ambito.nombre.capitalize()
                                # armando detalle
                                lista_detalle = []
                                lista_detalle_total_barra = []
                                lista_detalle_total_barra_porcentaje = []
                                lista_detalle_pregunta_barra = []
                                numero = 1
                                for pregunta_indicador in encuesta.preguntas_por_ambitos(ambito.id):
                                    aux = [numero, pregunta_indicador.indicador.nombre.capitalize().__str__()]
                                    aux1 = []
                                    aux2 = []
                                    lista_detalle_pregunta_barra.append(pregunta_indicador.indicador.nombre.capitalize().__str__())
                                    total_resp_pregunta_por_carrera = encuesta.total_encuestado_por_ambito_segun_indicador_carrera(grupo.id, ambito.id, pregunta_indicador.indicador.id, carrera.id)
                                    for literal in literales_generales_pregunta:
                                        total_repuesta = encuesta.total_encuestado_por_ambito_segun_literal_y_indicador(grupo.id, ambito.id, literal.id, pregunta_indicador.indicador.id, carrera.id)
                                        aux.append(total_repuesta)
                                        aux1.append(total_repuesta)
                                        aux2.append(null_to_decimal((total_repuesta * 100 / total_resp_pregunta_por_carrera), 2))
                                    lista_detalle.append(aux)
                                    lista_detalle_total_barra.append(aux1)
                                    lista_detalle_total_barra_porcentaje.append(aux2)
                                    numero += 1
                                # acomodando detalle para grafica
                                contador = 0
                                lista_acomodada_literales = []
                                lista_acomodada_literales_porcentaje = []
                                while contador < listaliteralcabecera.__len__() - 2:
                                    aux = []
                                    aux1 = []
                                    for listaliteral in lista_detalle_total_barra:
                                        aux.append(listaliteral[contador])
                                    for listaliteral in lista_detalle_total_barra_porcentaje:
                                        aux1.append(listaliteral[contador])
                                    contador += 1
                                    lista_acomodada_literales.append(aux)
                                    lista_acomodada_literales_porcentaje.append(aux1)
                                # ----------------
                                add_tabla_reportlab(encabezado=listacabecera, detalles=lista_detalle,
                                                    anchocol=listaanchocolumna, cabecera_left_center=cabecera_left_center, detalle_left_center=cabecera_left_center)
                                add_graficos_barras_reportlab(datavalor=lista_acomodada_literales, datanombres=lista_detalle_pregunta_barra,
                                                              anchografico=500, altografico=125, tamanoletra=6, posiciongrafico_x=25, posiciongrafico_y=30,
                                                              titulo='Respuestas por indicador en números', tamanotitulo=10, ubicaciontitulo_x=225, ubicaciontitulo_y=17,
                                                              posicionleyenda_x=430, mostrarleyenda=False, barra_vertical_horizontal=True, presentar_nombre_o_numero=False)
                                add_graficos_barras_reportlab(datavalor=lista_acomodada_literales_porcentaje, datanombres=lista_detalle_pregunta_barra,
                                                              anchografico=500, altografico=125, tamanoletra=6, posiciongrafico_x=25, posiciongrafico_y=30,
                                                              titulo='Respuestas por indicador en porcentajes', tamanotitulo=10, ubicaciontitulo_x=225, minimo=0 , maximo=100, step=20,
                                                              ubicaciontitulo_y=17, posicionleyenda_x=430, mostrarleyenda=False, barra_vertical_horizontal=True, presentar_nombre_o_numero=False, decimal=True)
                return generar_pdf_reportlab(topmargin=62)
            except Exception as ex:
                messages.error(request, 'Error al generar informe de resultado de encuesta:  ' + str(ex))
                #messages.error(request, ex)
                return HttpResponseRedirect("/encuestas")

        if action == 'resultadoencuesta_excel':
            try:
                encuenta = Encuesta.objects.get(pk=int(encrypt(request.POST['id'])))
                __author__ = 'Unemi'
                title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False
                wb = Workbook(encoding='utf-8')
                ws = wb.add_sheet('exp_xls_post_part')
                response = HttpResponse(content_type="application/ms-excel")
                response['Content-Disposition'] = 'attachment; filename=Encuestados ' + random.randint(1, 10000).__str__() + '.xls'
                columns = [
                    (u"Apellidos y nombres", 6000),
                    (u"Cédula", 3000),
                    (u"Edad", 1500),
                    (u"Género", 3000),
                    (u"Carrera", 10000),
                    (u"Email institucional", 6000),
                    (u"Email personal", 6000),
                    (u"Teléfono", 3000),
                    (u"Ciudad residencia", 6000),
                    (u"Labora", 6000),
                ]
                row_num = 0
                for col_num in range(len(columns)):
                    ws.write(row_num, col_num, columns[col_num][0], font_style)
                    ws.col(col_num).width = columns[col_num][1]
                row_num = 0
                col_num = len(columns)
                if encuenta.respuestaencuesta_set.filter(status=True).exists():
                    for p in encuenta.respuestaencuesta_set.filter(status=True)[1].lista_preguntas():
                        ws.write(row_num, col_num, '%s' % p[1], font_style2)
                        col_num = col_num +1
                row_num = 1
                for e in encuenta.respuestaencuesta_set.filter(status=True):
                    cedula = ''
                    if e.matricula:
                        cedula = e.matricula.inscripcion.persona.cedula if e.matricula.inscripcion.persona.cedula else e.matricula.inscripcion.persona.pasaporte
                    ws.write(row_num, 0, '%s %s %s' %(e.matricula.inscripcion.persona.apellido1, e.matricula.inscripcion.persona.apellido2, e.matricula.inscripcion.persona.nombres) if e.matricula else '', font_style2)
                    ws.write(row_num, 1, cedula, font_style2)
                    ws.write(row_num, 2, e.matricula.inscripcion.persona.edad() if e.matricula else '', font_style2)
                    genero = ''
                    ciudadresidencia = ''
                    if e.matricula:
                        if e.matricula.inscripcion.persona.sexo:
                            genero = e.matricula.inscripcion.persona.sexo.nombre

                        if e.matricula.inscripcion.persona.canton:
                            ciudadresidencia = e.matricula.inscripcion.persona.canton.nombre

                    ws.write(row_num, 3, genero, font_style2)
                    ws.write(row_num, 4, e.matricula.inscripcion.carrera.nombre if e.matricula else '', font_style2)
                    ws.write(row_num, 5, e.matricula.inscripcion.persona.emailinst if e.matricula else '', font_style2)
                    ws.write(row_num, 6, e.matricula.inscripcion.persona.email if e.matricula else '', font_style2)
                    ws.write(row_num, 7, e.matricula.inscripcion.persona.telefono if e.matricula else '', font_style2)

                    ws.write(row_num, 8, ciudadresidencia, font_style2)
                    ws.write(row_num, 9, e.matricula.inscripcion.persona.get_labora_display() if e.matricula else '', font_style2)
                    col_num = 9+1
                    for p in e.lista_preguntas():
                        r = DatoRespuestaEncuesta.objects.values_list('respuestapregunta__nombre', flat=True).get(pk=p[0])
                        ws.write(row_num, col_num, '%s' % r, font_style2)
                        col_num = col_num +1
                    row_num += 1
                wb.save(response)
                return response
            except Exception as ex:
                messages.error(request, ex)
                return HttpResponseRedirect("/encuestas")

        if action == 'resultadoencuesta_grupo_excel':
            try:
                encuenta = Encuesta.objects.get(pk=int(encrypt(request.POST['id'])))
                __author__ = 'Unemi'
                title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False
                wb = Workbook(encoding='utf-8')
                ws = wb.add_sheet('exp_xls_post_part')
                response = HttpResponse(content_type="application/ms-excel")
                response['Content-Disposition'] = 'attachment; filename=Encuestados-'+ encuenta.nombre + random.randint(1, 10000).__str__() + '.xls'
                columns = [
                    (u"Ámbito", 10000),
                    (u"Indicador", 16000),
                ]
                row_num = 0
                for col_num in range(len(columns)):
                    ws.write(row_num, col_num, columns[col_num][0], font_style)
                    ws.col(col_num).width = columns[col_num][1]
                row_num = 0
                col_num = len(columns)
                col_num2 = len(columns)
                if encuenta.respuestaencuesta_set.filter(status=True).exists():
                    for escala in encuenta.tiporespuesta.respuesta_set.all().order_by('valor'):
                        ws.write(row_num, col_num, '%s' % escala.nombre, font_style2)
                        col_num = col_num +1
                row_num = 1
                listaanvito = encuenta.ambitos().values_list('id', flat=False)
                indicadores = IndicadorAmbitoInstrumentoEvaluacion.objects.filter(ambitoinstrumento__instrumento__id=encuenta.instrumento.id, ambitoinstrumento__ambito__id__in=listaanvito).order_by('ambitoinstrumento__ambito')
                for i in indicadores:
                    ws.write(row_num, 0, i.ambitoinstrumento.ambito.nombre, font_style2)
                    ws.write(row_num, 1, i.indicador.nombre, font_style2)
                    col_num = col_num2
                    for escala in encuenta.tiporespuesta.respuesta_set.all().order_by('valor'):
                        valor = i.datorespuestaencuesta_set.values('id').filter(respuestapregunta=escala, indicador=i).count()
                        ws.write(row_num, col_num, '%s' % valor, font_style2)
                        col_num = col_num +1
                    row_num += 1
                wb.save(response)
                return response
            except Exception as ex:
                messages.error(request, ex)
                return HttpResponseRedirect("/encuestas")

        if action == 'resultadoencuesta_grupo_excel_independientes':
            try:
                encuenta = Encuesta.objects.get(pk=int(encrypt(request.POST['id'])))
                __author__ = 'Unemi'
                title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False
                wb = Workbook(encoding='utf-8')
                ws = wb.add_sheet('exp_xls_post_part')
                response = HttpResponse(content_type="application/ms-excel")
                response['Content-Disposition'] = 'attachment; filename=Encuestados-'+ encuenta.nombre + random.randint(1, 10000).__str__() + '.xls'
                columns = [
                    (u"Ámbito", 10000),
                    (u"Indicador", 16000),
                    (u"Tipo Respuesta", 16000),
                ]
                row_num = 0
                for col_num in range(len(columns)):
                    ws.write(row_num, col_num, columns[col_num][0], font_style)
                    ws.col(col_num).width = columns[col_num][1]
                row_num = 0
                col_num = len(columns)
                col_num2 = len(columns)
                # if encuenta.respuestaencuesta_set.filter(status=True).exists():
                #     for escala in encuenta.tiporespuesta.respuesta_set.all().order_by('valor'):
                #         ws.write(row_num, col_num, '%s' % escala.nombre, font_style2)
                #         col_num = col_num +1
                row_num = 1
                listaanvito = encuenta.ambitos().values_list('id', flat=False)
                indicadores = IndicadorAmbitoInstrumentoEvaluacion.objects.filter(ambitoinstrumento__instrumento__id=encuenta.instrumento.id, ambitoinstrumento__ambito__id__in=listaanvito).order_by('ambitoinstrumento__ambito')
                for i in indicadores:
                    ws.write(row_num, 0, i.ambitoinstrumento.ambito.nombre, font_style2)
                    ws.write(row_num, 1, i.indicador.nombre, font_style2)
                    ws.write(row_num, 2, i.tiporespuesta.nombre, font_style2)
                    col_num = col_num2
                    if i.tiporespuesta.id == 9:
                        respuestas = i.datorespuestaencuesta_set.filter(respuestapregunta__isnull=True, indicador=i)
                        for resp in respuestas:
                            ws.write(row_num, col_num, '%s' % resp.respuestapreguntaabierta, font_style2)
                            row_num = row_num + 1
                    for escala in i.tiporespuesta.respuesta_set.all().order_by('valor'):
                        valor = i.datorespuestaencuesta_set.values('id').filter(respuestapregunta=escala, indicador=i).count()
                        ws.write(row_num, col_num, '%s' % valor, font_style2)
                        col_num = col_num +1
                    row_num += 1
                wb.save(response)
                return response
            except Exception as ex:
                messages.error(request, ex)
                return HttpResponseRedirect("/encuestas")

        if action == 'addindicadorpregunta':
            try:
                with transaction.atomic():
                    ambito = AmbitoInstrumentoEvaluacion.objects.get(pk=request.POST['ambito'])
                    indicador = IndicadorEvaluacion.objects.get(pk=request.POST['indicadores'])
                    tiporespuesta = TipoRespuesta.objects.get(pk=request.POST['respuesta'])
                    if IndicadorAmbitoInstrumentoEvaluacion.objects.filter(ambitoinstrumento=ambito, indicador=indicador).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Indicador ya existe."}, safe=False)
                    else:
                        preguntas = IndicadorAmbitoInstrumentoEvaluacion(ambitoinstrumento=ambito, indicador=indicador, tiporespuesta=tiporespuesta)
                        preguntas.save(request)
                        log(u'Adiciono indicador de instrumento de encuesta: %s' % indicador, request, "add")
                        return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'addindicadormodal':
            try:
                with transaction.atomic():
                    form = EncuestaIndicadoresModalForm(request.POST)
                    if form.is_valid():
                        filtro = IndicadorEvaluacion(nombre=form.cleaned_data['nombre'].upper(),
                                              encuesta=form.cleaned_data['encuesta'])
                        filtro.save(request)
                        log(u'Adiciono indicador Encuesta: %s' % filtro, request, "add")
                        # return JsonResponse({"result": False,'to':'/nuevaurl'}, safe=False) SI DESEAS REDIRECCIONAR ADICIONARLE TO A LA RESPUESTA
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'editindicadormodal':
            try:
                with transaction.atomic():
                    filtro = IndicadorEvaluacion.objects.get(pk=request.POST['id'])
                    f = EncuestaIndicadoresModalForm(request.POST)
                    if f.is_valid():
                        filtro.nombre = f.cleaned_data['nombre'].upper()
                        filtro.encuesta = f.cleaned_data['encuesta']
                        filtro.save(request)
                        log(u'Modificó indicador en Encuestas: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'delindicadormodal':
            try:
                filtro = IndicadorEvaluacion.objects.get(pk=request.POST['id'])
                filtro.status = False
                filtro.save(request)
                log(u'Elimino Indicador Encuestas: %s' % filtro, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'addambitomodal':
            try:
                with transaction.atomic():
                    form = EncuestaAmbitoModalForm(request.POST)
                    if form.is_valid():
                        filtro = AmbitoEvaluacion(nombre=form.cleaned_data['nombre'].upper(),
                                              encuesta=form.cleaned_data['encuesta'])
                        filtro.save(request)
                        log(u'Adiciono Ambito Encuesta: %s' % filtro, request, "add")
                        # return JsonResponse({"result": False,'to':'/nuevaurl'}, safe=False) SI DESEAS REDIRECCIONAR ADICIONARLE TO A LA RESPUESTA
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'editambitomodal':
            try:
                with transaction.atomic():
                    filtro = AmbitoEvaluacion.objects.get(pk=request.POST['id'])
                    f = EncuestaAmbitoModalForm(request.POST)
                    if f.is_valid():
                        filtro.nombre = f.cleaned_data['nombre'].upper()
                        filtro.encuesta = f.cleaned_data['encuesta']
                        filtro.save(request)
                        log(u'Modificó Ambito en Encuestas: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'delambitomodal':
            try:
                filtro = AmbitoEvaluacion.objects.get(pk=request.POST['id'])
                filtro.status = False
                filtro.save(request)
                log(u'Elimino Ambito Encuestas: %s' % filtro, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data = {}
        adduserdata(request, data)
        data['title'] = u'Gestión de encuestas'
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Crear nueva Encuesta'
                    data['form'] = EncuestaForm(initial={'fechainicio': datetime.now().date(),
                                                         'fechafin': (datetime.now() + timedelta(days=15)).date()})
                    data['grupos'] = Group.objects.all()
                    return render(request, "encuestas/add.html", data)
                except Exception as ex:
                    pass

            elif action == 'edit':
                try:
                    data['title'] = u'Editar encuesta'
                    encuesta = Encuesta.objects.get(pk=request.GET['id'])
                    data['encuesta'] = encuesta
                    data['form'] = EncuestaForm(initial=model_to_dict(encuesta))
                    data['grupos'] = Group.objects.all()
                    data['muestragrupoencuestas'] = encuesta.muestra_grupo_encuesta()
                    return render(request, "encuestas/edit.html", data)
                except Exception as ex:
                    pass

            elif action == 'activar':
                try:
                    encuesta = Encuesta.objects.get(pk=request.GET['id'])
                    encuesta.activa = True
                    encuesta.save(request)
                    return HttpResponseRedirect(request.path)
                except Exception as ex:
                    pass

            elif action == 'desactivar':
                try:
                    encuesta = Encuesta.objects.get(pk=request.GET['id'])
                    encuesta.activa = False
                    encuesta.save(request)
                    return HttpResponseRedirect(request.path)
                except Exception as ex:
                    pass
            elif action == 'importar':
                try:
                    data['title'] = u'Importar Muestra'
                    encuesta = Encuesta.objects.get(pk=request.GET['id'])
                    data['encuesta'] = encuesta
                    data['form'] = ImportarEncuestaForm()
                    return render(request, "encuestas/importar.html", data)
                except Exception as ex:
                    pass

            elif action == 'editinst':
                try:
                    if 'id' in request.GET:
                        request.session['idencuestavista'] = en = Encuesta.objects.get(pk=request.GET['id'])
                        data['encu'] = en = Encuesta.objects.get(pk=request.GET['id'])
                        data['ide'] = en.pk
                        if not en.instrumento:
                            ins = InstrumentoEvaluacion(nombre=en.nombre)
                            ins.save(request)
                            en.instrumento = ins
                            en.save(request)
                        data['instrumento'] = en.instrumento
                    elif 'in' in request.GET:
                        data['ide'] = ide = request.GET['ide'] if 'ide' in request.GET else ''
                        if ide:
                            data['encu'] = en = Encuesta.objects.get(pk=ide)
                        ins = InstrumentoEvaluacion.objects.get(pk=request.GET['in'])
                        data['instrumento'] = ins
                    data['tipo'] = "Encuesta %s" % data['instrumento'].nombre
                    data['ambitoslibres'] = AmbitoEvaluacion.objects.filter(encuesta=True).exclude(id__in=[x.ambito.id for x in data['instrumento'].ambitoinstrumentoevaluacion_set.all()])
                    data['indicadores'] = IndicadorEvaluacion.objects.filter(encuesta=True)
                    data['instrumentonumero'] = "1"
                    return render(request, "encuestas/editinst.html", data)
                except Exception as ex:
                    pass

            elif action == 'responder':
                try:
                    # IMSM
                    data['encuesta'] = encuesta = Encuesta.objects.get(pk=request.GET['id'])
                    instrumento = encuesta.instrumento
                    data['ambitos'] = instrumento.ambitoinstrumentoevaluacion_set.all()
                    data['fecha'] = datetime.now()
                    data['respuesta'] = None
                    if encuesta.tiporespuesta:
                        data['tiporespuesta'] = encuesta.tiporespuesta.respuesta_set.all()
                    return render(request, "encuestas/vistaprevia.html", data)
                except Exception as ex:
                    pass

            elif action == 'addambito':
                try:
                    ide = request.GET['ide']
                    inst = InstrumentoEvaluacion.objects.get(pk=request.GET['inst'])
                    na = AmbitoInstrumentoEvaluacion(instrumento=inst, ambito=AmbitoEvaluacion.objects.get(pk=request.GET['amb']))
                    na.save(request)
                    log(u'Adiciono ambito de instrumento de encuesta: %s' % na, request, "add")
                    return HttpResponseRedirect('/encuestas?action=editinst&ide={}&in={}'.format(ide, inst.id))
                except Exception as ex:
                    pass

            elif action == 'addambitonuevo':
                try:
                    inst = InstrumentoEvaluacion.objects.get(pk=request.GET['inst'])
                    ambito = AmbitoEvaluacion(nombre=request.GET['nombre'], encuesta=True)
                    ambito.save(request)
                    na = AmbitoInstrumentoEvaluacion(instrumento=inst, ambito=ambito)
                    na.save(request)
                    log(u'Adiciono ambito de encuesta: %s' % ambito, request, "add")
                    ide = request.GET['ide'] if 'ide' in request.GET else ''
                    return HttpResponseRedirect('/encuestas?action=editinst&in={}&ide={}'.format(inst.id,ide))
                except Exception as ex:
                    pass

            elif action == 'delambito':
                try:
                    ambito = AmbitoInstrumentoEvaluacion.objects.get(pk=request.GET['id'])
                    log(u'Elimino ambito de encuesta: %s' % ambito, request, "del")
                    ambito.delete()
                    inst = InstrumentoEvaluacion.objects.get(pk=request.GET['inst'])
                    ide = request.GET['ide'] if 'ide' in request.GET else ''
                    return HttpResponseRedirect('/encuestas?action=editinst&in={}&ide={}'.format(inst.id,ide))
                except Exception as ex:
                    pass

            elif action == 'addindicador':
                try:
                    ambito = AmbitoInstrumentoEvaluacion.objects.get(pk=request.GET['ambito'])
                    indicador = IndicadorAmbitoInstrumentoEvaluacion(ambitoinstrumento=ambito, indicador=IndicadorEvaluacion.objects.get(pk=request.GET['indicador']))
                    indicador.save(request)
                    log(u'Adiciono indicador de instrumento de encuesta: %s' % indicador, request, "add")
                    inst = InstrumentoEvaluacion.objects.get(pk=request.GET['inst'])
                    ide = request.GET['ide'] if 'ide' in request.GET else ''
                    return HttpResponseRedirect('/encuestas?action=editinst&in={}&ide={}'.format(inst.id,ide))
                except Exception as ex:
                    pass

            elif action == 'addindicadornuevo':
                try:
                    ambito = AmbitoInstrumentoEvaluacion.objects.get(pk=request.GET['ambito'])
                    indicadornuevo = IndicadorEvaluacion(nombre=request.GET['nombre'], encuesta=True)
                    indicadornuevo.save(request)
                    indicador = IndicadorAmbitoInstrumentoEvaluacion(ambitoinstrumento=ambito, indicador=indicadornuevo)
                    indicador.save(request)
                    log(u'Adicionado indicador de ambito de instrumento de encuesta: %s' % indicador, request, "add")
                    inst = InstrumentoEvaluacion.objects.get(pk=request.GET['inst'])
                    ide = request.GET['ide'] if 'ide' in request.GET else ''
                    return HttpResponseRedirect('/encuestas?action=editinst&in={}&ide={}'.format(inst.id,ide))
                except Exception as ex:
                    pass

            elif action == 'delindicador':
                try:
                    indicador = IndicadorAmbitoInstrumentoEvaluacion.objects.get(pk=request.GET['id'])
                    log(u'Elimino indicador: %s' % indicador, request, "del")
                    indicador.delete()
                    inst = InstrumentoEvaluacion.objects.get(pk=request.GET['inst'])
                    ide = request.GET['ide'] if 'ide' in request.GET else ''
                    return HttpResponseRedirect('/encuestas?action=editinst&in={}&ide={}'.format(inst.id,ide))
                except Exception as ex:
                    pass

            elif action == 'piechartgeneral':
                try:
                    data['title'] = u'Graficas generales sobre encuesta'
                    encuesta = Encuesta.objects.get(pk=request.GET['id'])
                    ambitos_encuesta = encuesta.ambitos()
                    data['total_excelente'] = sum([x.encuestaron_excelente() for x in ambitos_encuesta])
                    data['total_muybien'] = sum([x.encuestaron_muybien() for x in ambitos_encuesta])
                    data['total_bien'] = sum([x.encuestaron_bien() for x in ambitos_encuesta])
                    data['total_regular'] = sum([x.encuestaron_regular() for x in ambitos_encuesta])
                    data['total_mal'] = sum([x.encuestaron_mal() for x in ambitos_encuesta])
                    data['total_no'] = sum([x.encuestaron_no() for x in ambitos_encuesta])
                    data['hoy'] = datetime.now().date()
                    data['encuesta'] = encuesta
                    data['ambitos'] = ambitos_encuesta
                    return render(request, "encuestas/piechartgeneral.html", data)
                except Exception as ex:
                    pass

            elif action == 'encuestaavance':
                try:
                    data['title'] = u'Avance de encuesta'
                    data['encuesta'] = encuesta = Encuesta.objects.get(pk=request.GET['id'])
                    data['muestras'] = encuesta.muestraencuesta_set.filter(status=True).order_by('persona')
                    data['hoy'] = datetime.now().date()
                    return render(request, "encuestas/avance.html", data)
                except Exception as ex:
                    pass

            elif action == 'piechartindicadores':
                try:
                    data['title'] = u'Graficas sobre indicadores'
                    encuesta = Encuesta.objects.get(pk=request.GET['id'])
                    data['indicadores'] = encuesta.indicadores()
                    data['hoy'] = datetime.now().date()
                    data['encuesta'] = encuesta
                    return render(request, "encuestas/piechartindicadores.html", data)
                except Exception as ex:
                    pass

            if action == 'encuestados':
                data['title'] = u'Gestión de encuestados'
                search = None
                if 's' in request.GET:
                    search = request.GET['s']
                respuesta = RespuestaEncuesta.objects.filter(encuesta=request.GET['id']).order_by('persona')
                paging = Paginator(respuesta, 50)
                p = 1
                try:
                    if 'page' in request.GET:
                        p = int(request.GET['page'])
                    page = paging.page(p)
                except Exception as ex:
                    page = paging.page(1)
                data['paging'] = paging
                data['page'] = page
                data['idencu'] = request.GET['id']
                data['search'] = search if search else ""
                data['encuestas'] = page.object_list
                data['cant_encuestados'] = respuesta.values('id').count()
                return render(request, "encuestas/evaluaron.html", data)

            if action == 'delencuestados':
                try:
                    data['title'] = u'Eliminar encuestados'
                    data['idencu'] = request.GET['idencu']
                    data['criterio'] = RespuestaEncuesta.objects.get(pk=request.GET['id'])
                    return render(request, "encuestas/delencuestados.html", data)
                except Exception as ex:
                    pass

            if action == 'buscarcarreras':
                try:
                    q = request.GET['q'].upper().strip()
                    qset = Carrera.objects.filter(status=True).filter(Q(nombre__icontains=q)).order_by('nombre').distinct()[:15]
                    results = [{'id': 0, 'name': 'TODAS LAS CARRERAS'}]
                    [results.append({"id": x.id, "name": "{}".format(x.nombre)}) for x in qset]
                    data = {"result": "ok", "results":results}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'configuraciones':
                try:
                    data['title'] = u'Configuraciones'
                    data['ambitoslibres'] = AmbitoEvaluacion.objects.filter(encuesta=True)
                    data['indicadores'] = IndicadorEvaluacion.objects.filter(encuesta=True)
                    return render(request, "encuestas/configuraciones.html", data)
                except Exception as ex:
                    pass

            if action == 'addindicadorpregunta':
                try:
                    # data['indicador'] = indicador = IndicadorEvaluacion.objects.get(pk=request.GET['id'])
                    data['ambito'] = ambito = AmbitoInstrumentoEvaluacion.objects.get(pk=request.GET['ambito'])
                    preguntas = IndicadorAmbitoInstrumentoEvaluacion.objects.filter(ambitoinstrumento=ambito).values_list('indicador_id', flat=True)
                    data['indicadores'] = IndicadorEvaluacion.objects.filter(encuesta=True).exclude(pk__in=preguntas)
                    data['tiporespuesta'] = TipoRespuesta.objects.all()
                    template = get_template("encuestas/modal/formindicadorpregunta.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'addindicadormodal':
                try:
                    data['form2'] = EncuestaIndicadoresModalForm()
                    template = get_template("encuestas/modal/formindicador.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editindicadormodal':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = IndicadorEvaluacion.objects.get(pk=request.GET['id'])
                    data['form2'] = EncuestaIndicadoresModalForm(initial=model_to_dict(filtro))
                    template = get_template("encuestas/modal/formindicador.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'delindicadormodal':
                try:
                    data['title'] = u'ELIMINAR INDICADOR'
                    data['filtro'] = IndicadorEvaluacion.objects.get(pk=request.GET['id'])
                    return render(request, 'encuestas/delindicadormodal.html', data)
                except Exception as ex:
                    pass

            if action == 'addambitomodal':
                try:
                    data['form2'] = EncuestaAmbitoModalForm()
                    template = get_template("encuestas/modal/formambito.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editambitomodal':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = AmbitoEvaluacion.objects.get(pk=request.GET['id'])
                    data['form2'] = EncuestaAmbitoModalForm(initial=model_to_dict(filtro))
                    template = get_template("encuestas/modal/formambito.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'delambitomodal':
                try:
                    data['title'] = u'ELIMINAR AMBITO'
                    data['filtro'] = AmbitoEvaluacion.objects.get(pk=request.GET['id'])
                    return render(request, 'encuestas/delambitomodal.html', data)
                except Exception as ex:
                    pass

            if action == 'vercoordinaciones':
                try:
                    data['encuesta'] = Encuesta.objects.get(pk=request.GET['id'])
                    template = get_template("encuestas/modal/vercoordinaciones.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'verdepartamentos':
                try:
                    data['encuesta'] = Encuesta.objects.get(pk=request.GET['id'])
                    template = get_template("encuestas/modal/verdepartamentos.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'addhijos':
                try:
                    pk = request.GET['pk']
                    data['indicador'] = indicador = IndicadorEvaluacion.objects.get(pk=request.GET['pk'])
                    data['respuesta'] = respuesta = TipoRespuesta.objects.get(pk=request.GET['pkr'])
                    data['indicadores'] = IndicadorEvaluacion.objects.filter(encuesta=True).exclude(pk=indicador.pk)
                    data['tiporespuesta'] = TipoRespuesta.objects.all()
                    template = get_template('encuestas/modal/addhijos.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': 'Intentelo más tarde'})

            return HttpResponseRedirect(request.path)
        else:
            search = None
            if 's' in request.GET:
                search = request.GET['s']
                busqueda = request.GET.get("searchinput")
            if search:
                encuestas = Encuesta.objects.filter(Q(nombre__icontains=search))
            else:
                encuestas = Encuesta.objects.filter(status=True).order_by('-id')
                #encuestas = Encuesta.objects.filter(status=True).order_by('-id')
            paging = Paginator(encuestas, 10)
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
            data['page'] = page
            data['search'] = search if search else ""
            data['encuestas'] = page.object_list
            data['reporte_0'] = obtener_reporte('evaluacion_encuestas')
            # data['carreras'] = Carrera.objects.filter(status=True)
            if 'idencuestavista' in request.session:
                del request.session['idencuestavista']
            return render(request, "encuestas/view.html", data)
