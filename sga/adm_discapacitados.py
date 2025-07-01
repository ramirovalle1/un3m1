# -*- coding: latin-1 -*-
import random
from xlwt import *
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sagest.forms import DiscapacidadForm2, ArtistaValidacionForm, BecaValidacionForm, DeportistaValidacionForm, \
    DiscapacidadValidacionForm, EtniaValidacionForm, MigranteValidacionForm
from sga.commonviews import adduserdata, obtener_reporte
from sga.funciones import generar_nombre, fechaformatostr
from sga.models import Inscripcion, ArtistaPersona, BecaPersona, DeportistaPersona, PerfilInscripcion, MigrantePersona
from sga.funciones import log

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    data['periodo'] = periodo = request.session['periodo']
    if 'action' in request.GET:
        action = request.GET['action']
        if action == 'discapacidad':
            try:
                data['title'] = u'Discapacidad'
                inscripcion = Inscripcion.objects.get(pk=int(request.GET['id']))
                perfil = inscripcion.persona.mi_perfil()
                form = DiscapacidadForm2(initial={'tienediscapacidad': perfil.tienediscapacidad,
                                                  'tipodiscapacidad': perfil.tipodiscapacidad,
                                                  'porcientodiscapacidad': perfil.porcientodiscapacidad,
                                                  'carnetdiscapacidad': perfil.carnetdiscapacidad,
                                                  'verificadiscapacidad': perfil.verificadiscapacidad})
                data['form'] = form
                data['inscripcion'] = inscripcion
                return render(request, "adm_discapacitados/discapacidad.html", data)
            except:
                pass
        if action == 'descargar':
            try:
                __author__ = 'UNEMI'
                style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                title = easyxf(
                    'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                style1 = easyxf(num_format_str='D-MMM-YY')
                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False
                wb = Workbook(encoding='utf-8')
                ws = wb.add_sheet('exp_xls_post_part')
                response = HttpResponse(content_type="application/ms-excel")
                response[
                    'Content-Disposition'] = 'attachment; filename=estudiantes_discapacidad_' + random.randint(1, 10000).__str__() + '.xls'
                columns = [
                    (u"CEDULA", 3000),
                    (u"ESTUDIANTE", 12000),
                    (u"CORREO PERSONAL", 8000),
                    (u"CORREO INSTITUCIONAL", 8000),
                    (u"TELEFONOS", 6000),
                    (u"CARRERA", 12000),
                    (u"FACULTAD", 12000),
                    (u"SECCION", 6000),
                    (u"NIVEL", 6000),
                    (u"DISCAPACIDAD", 6000),
                    (u"PORCENTAJE", 6000),
                    (u"CARNET", 6000),
                    (u"BECA", 6000),
                    (u"VERIFICADO POR LA UBE", 6000),
                    (u"SEXO", 6000)
                ]
                row_num = 0
                for col_num in range(len(columns)):
                    ws.write(row_num, col_num, columns[col_num][0], font_style)
                    ws.col(col_num).width = columns[col_num][1]
                inscripcion = Inscripcion.objects.filter(matricula__status=True, matricula__nivel__periodo=periodo,persona__perfilinscripcion__tienediscapacidad=True).order_by("persona")
                row_num = 1
                for r in inscripcion:
                    i = 0
                    campo1 = r.persona.cedula
                    campo2 = r.persona.__str__()
                    campo3 = r.persona.email
                    campo4 = r.persona.emailinst
                    campo5 = "%s - %s" % (r.persona.telefono, r.persona.telefono_conv)
                    campo15 = r.coordinacion.__str__()
                    campo6 = r.carrera.__str__()
                    campo7 = r.sesion.nombre
                    campo8 = r.matricula_set.filter(nivel__periodo=periodo)[0].nivelmalla.nombre
                    campo9=""
                    if r.persona.mi_perfil():
                        if r.persona.mi_perfil().tipodiscapacidad:
                            campo9 = r.persona.mi_perfil().tipodiscapacidad.nombre
                    campo10 = ("%s" % r.persona.mi_perfil().porcientodiscapacidad) + "%"
                    campo11 = r.persona.mi_perfil().carnetdiscapacidad
                    campo12 = "BECADO" if r.tiene_registro_becario() else "NO BECADO"
                    campo13 = "SI" if r.persona.mi_perfil().verificadiscapacidad else "NO"
                    campo14 = r.persona.sexo.nombre if r.persona.sexo else ''
                    ws.write(row_num, 0, campo1, font_style2)
                    ws.write(row_num, 1, campo2, font_style2)
                    ws.write(row_num, 2, campo3, font_style2)
                    ws.write(row_num, 3, campo4, font_style2)
                    ws.write(row_num, 4, campo5, font_style2)
                    ws.write(row_num, 5, campo6, font_style2)
                    ws.write(row_num, 6, campo15, font_style2)
                    ws.write(row_num, 7, campo7, font_style2)
                    ws.write(row_num, 8, campo8, font_style2)
                    ws.write(row_num, 9, campo9, font_style2)
                    ws.write(row_num, 10, campo10, font_style2)
                    ws.write(row_num, 11, campo11, font_style2)
                    ws.write(row_num, 12, campo12, font_style2)
                    ws.write(row_num, 13, campo13, font_style2)
                    ws.write(row_num, 14, campo14, font_style2)
                    row_num += 1
                wb.save(response)
                return response
            except Exception as ex:
                pass

    if 'action' in request.POST:
        action = request.POST['action']
        if action == 'discapacidad':
            try:
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile.size > 2194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 2Mb"})
                f = DiscapacidadForm2(request.POST)
                if f.is_valid():
                    newfile = None
                    perfil = Inscripcion.objects.get(pk=int(request.POST['id'])).persona.mi_perfil()
                    perfil.tienediscapacidad = f.cleaned_data['tienediscapacidad']
                    perfil.tipodiscapacidad = f.cleaned_data['tipodiscapacidad']
                    perfil.porcientodiscapacidad = f.cleaned_data['porcientodiscapacidad'] if f.cleaned_data[
                        'porcientodiscapacidad'] else 0
                    perfil.carnetdiscapacidad = f.cleaned_data['carnetdiscapacidad']
                    perfil.verificadiscapacidad = f.cleaned_data['verificadiscapacidad']
                    if not f.cleaned_data['tienediscapacidad']:
                        perfil.archivo = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("archivosdiscapacidad_", newfile._name)
                        perfil.archivo = newfile
                    perfil.save(request)
                    log(u'Modifico tipo de discapacidad: %s' % perfil, request, "edit")
                    return JsonResponse({'result': 'ok'})
                else:
                     raise NameError('Error')
            except Exception as ex:
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        elif action == 'datosartista':
            try:
                artista = ArtistaPersona.objects.get(pk=int(request.POST['id']))
                estudiante = str(artista.persona)
                grupopertenece = artista.grupopertenece
                inicioensayo = fechaformatostr(str(artista.fechainicioensayo),'DMA')
                finensayo = fechaformatostr(str(artista.fechafinensayo),'DMA')
                archivo = artista.archivo.url
                verificado = artista.verificado
                estadoarchivo = artista.estadoarchivo
                observacion = artista.observacion

                lista = []
                campos = artista.campoartistico.all()

                for c in campos:
                    lista.append([c.id, c.descripcion])

                artista = {'estudiante': estudiante,
                         'grupopertenece': grupopertenece,
                         'inicioensayo': inicioensayo,
                         'finensayo': finensayo,
                         'archivo': archivo,
                         'verificado': 'SI' if verificado else 'NO',
                         'estadoarchivo': estadoarchivo,
                         'observacion': observacion,
                         'campoartistico': lista}

                return JsonResponse({'result': 'ok', 'artista': artista})
            except Exception as ex:
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al obtener los datos'})

        elif action == 'datosbecado':
            try:
                becado = BecaPersona.objects.get(pk=int(request.POST['id']))
                estudiante = str(becado.persona)
                institucion = str(becado.institucion)
                tipoinstitucion = becado.get_tipoinstitucion_display()
                archivo = becado.archivo.url
                verificado = becado.verificado
                estadoarchivo = becado.estadoarchivo
                observacion = becado.observacion

                beca = {'estudiante': estudiante,
                         'institucion': institucion,
                         'tipoinstitucion': tipoinstitucion,
                         'archivo': archivo,
                         'verificado': 'SI' if verificado else 'NO',
                         'estadoarchivo': estadoarchivo,
                         'observacion': observacion
                        }

                return JsonResponse({'result': 'ok', 'becado': beca})
            except Exception as ex:
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al obtener los datos'})

        elif action == 'datosdeportista':
            try:
                deportista = DeportistaPersona.objects.get(pk=int(request.POST['id']))
                estudiante = str(deportista.persona)
                representapais = deportista.representapais
                evento = deportista.evento
                paisparticipa = str(deportista.paisevento)
                equiporepresenta = deportista.equiporepresenta
                eventodesde = fechaformatostr(str(deportista.fechainicioevento), 'DMA')
                eventohasta = fechaformatostr(str(deportista.fechafinevento), 'DMA')
                archivoparticipacion = deportista.archivoevento.url
                entrenamientodesde = fechaformatostr(str(deportista.fechainicioentrena), 'DMA')
                entrenamientohasta = fechaformatostr(str(deportista.fechafinentrena), 'DMA')
                archivoentrenamiento = deportista.archivoentrena.url
                verificado = deportista.verificado
                estadoarchivoeve = deportista.estadoarchivoevento
                observacioneve = deportista.observacionarchevento
                estadoarchivoent = deportista.estadoarchivoentrena
                observacionent = deportista.observacionarchentrena

                lista = []
                disciplinas = deportista.disciplina.all()

                for c in disciplinas:
                    lista.append([c.id, c.descripcion])

                deportista = {'estudiante': estudiante,
                         'representapais': 'SI' if representapais else 'NO',
                         'evento': evento,
                         'paisparticipa': paisparticipa,
                         'equiporepresenta': equiporepresenta,
                         'eventodesde': eventodesde,
                         'eventohasta': eventohasta,
                         'archivoparticipacion': archivoparticipacion,
                         'entrenamientodesde': entrenamientodesde,
                         'entrenamientohasta': entrenamientohasta,
                         'archivoentrenamiento': archivoentrenamiento,
                         'verificado': 'SI' if verificado else 'NO',
                         'estadoarchivoeve': estadoarchivoeve,
                         'observacioneve': observacioneve,
                         'estadoarchivoent': estadoarchivoent,
                         'observacionent': observacionent,
                         'disciplinas': lista}

                return JsonResponse({'result': 'ok', 'deportista': deportista})
            except Exception as ex:
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al obtener los datos'})

        elif action == 'datosdiscapacidad':
            try:
                discapacidad = PerfilInscripcion.objects.get(pk=int(request.POST['id']))
                estudiante = str(discapacidad.persona)
                tipo = str(discapacidad.tipodiscapacidad)
                porcentaje = discapacidad.porcientodiscapacidad
                carnet = discapacidad.carnetdiscapacidad
                archivo = discapacidad.archivo.url if discapacidad.archivo else ''
                verificado = discapacidad.verificadiscapacidad
                estadoarchivo = discapacidad.estadoarchivodiscapacidad
                observacion = discapacidad.observacionarchdiscapacidad
                institucion = str(discapacidad.institucionvalida) if discapacidad.institucionvalida else ''

                discapacidad = {'estudiante': estudiante,
                         'tipodiscapacidad': tipo,
                         'porcentajediscapacidad': porcentaje,
                         'carnet': carnet,
                         'archivo': archivo,
                         'verificado': 'SI' if verificado else 'NO',
                         'estadoarchivo': estadoarchivo,
                         'observacion': observacion,
                         'institucion': institucion
                        }

                return JsonResponse({'result': 'ok', 'discapacidad': discapacidad})
            except Exception as ex:
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al obtener los datos'})

        elif action == 'datosetnia':
            try:
                etnia = PerfilInscripcion.objects.get(pk=int(request.POST['id']))
                estudiante = str(etnia.persona)
                etnianombre = str(etnia.raza)
                nacionalidadetnia = str(etnia.nacionalidadindigena) if etnia.nacionalidadindigena else ''
                archivo = etnia.archivoraza.url if etnia.archivoraza else ''
                verificado = etnia.verificaraza
                estadoarchivo = etnia.estadoarchivoraza
                observacion = etnia.observacionarchraza

                etnia = {'estudiante': estudiante,
                         'etnianombre': etnianombre,
                         'nacionalidadetnia': nacionalidadetnia,
                         'archivo': archivo,
                         'verificado': 'SI' if verificado else 'NO',
                         'estadoarchivo': estadoarchivo,
                         'observacion': observacion
                        }

                return JsonResponse({'result': 'ok', 'etnia': etnia})
            except Exception as ex:
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al obtener los datos'})

        elif action == 'datosmigrante':
            try:
                migrante = MigrantePersona.objects.get(pk=int(request.POST['id']))
                estudiante = str(migrante.persona)
                anios = migrante.anioresidencia
                meses = migrante.mesresidencia
                fecharetorno = fechaformatostr(str(migrante.fecharetorno), 'DMA')
                archivo = migrante.archivo.url
                verificado = migrante.verificado
                estadoarchivo = migrante.estadoarchivo
                observacion = migrante.observacion

                migrante = {'estudiante': estudiante,
                         'anios': anios,
                         'meses': meses,
                         'fecharetorno': fecharetorno,
                         'archivo': archivo,
                         'verificado': 'SI' if verificado else 'NO',
                         'estadoarchivo': estadoarchivo,
                         'observacion': observacion
                        }

                return JsonResponse({'result': 'ok', 'migrante': migrante})
            except Exception as ex:
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al obtener los datos'})


        elif action == 'validarartista':
            try:
                form = ArtistaValidacionForm(request.POST)
                if form.is_valid():
                    artista = ArtistaPersona.objects.get(pk=int(request.POST['ida']))
                    artista.estadoarchivo = form.cleaned_data['estadoartista']
                    artista.observacion = form.cleaned_data['observacionartista'].strip().upper()
                    artista.verificado = True if int(form.cleaned_data['estadoartista']) == 2 else False
                    artista.save(request)
                    log(u'Actualizó registro de artista: %s' % artista, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'validarbecado':
            try:
                form = BecaValidacionForm(request.POST)
                if form.is_valid():
                    becado = BecaPersona.objects.get(pk=int(request.POST['idb']))
                    becado.estadoarchivo = form.cleaned_data['estadobecado']
                    becado.observacion = form.cleaned_data['observacionbecado'].strip().upper()
                    becado.verificado = True if int(form.cleaned_data['estadobecado']) == 2 else False
                    becado.save(request)
                    log(u'Actualizó registro de becado: %s' % becado, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'validardeportista':
            try:
                form = DeportistaValidacionForm(request.POST)
                if form.is_valid():
                    deportista = DeportistaPersona.objects.get(pk=int(request.POST['idd']))
                    deportista.estadoarchivoevento = form.cleaned_data['estadoarchivoevento']
                    deportista.observacionarchevento = form.cleaned_data['observacionarchevento'].strip().upper()
                    deportista.estadoarchivoentrena = form.cleaned_data['estadoarchivoentrena']
                    deportista.observacionarchentrena = form.cleaned_data['observacionarchentrena'].strip().upper()
                    deportista.verificado = True if int(form.cleaned_data['estadoarchivoevento']) == 2 and int(form.cleaned_data['estadoarchivoentrena']) == 2 else False
                    deportista.save(request)
                    log(u'Actualizó registro de deportista: %s' % deportista, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'validardiscapacidad':
            try:
                form = DiscapacidadValidacionForm(request.POST)
                if form.is_valid():
                    discapacidad = PerfilInscripcion.objects.get(pk=int(request.POST['iddis']))
                    discapacidad.estadoarchivodiscapacidad = form.cleaned_data['estadodiscapacidad']
                    discapacidad.observacionarchdiscapacidad = form.cleaned_data['observaciondiscapacidad'].strip().upper()
                    discapacidad.verificadiscapacidad = True if int(form.cleaned_data['estadodiscapacidad']) == 2 else False
                    discapacidad.save(request)
                    log(u'Actualizó registro de discapacidad: %s' % discapacidad, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'validaretnia':
            try:
                form = EtniaValidacionForm(request.POST)
                if form.is_valid():
                    etnia = PerfilInscripcion.objects.get(pk=int(request.POST['ide']))
                    etnia.estadoarchivoraza = form.cleaned_data['estadoetnia']
                    etnia.observacionarchraza = form.cleaned_data['observacionetnia'].strip().upper()
                    etnia.verificaraza = True if int(form.cleaned_data['estadoetnia']) == 2 else False
                    etnia.save(request)
                    log(u'Actualizó registro de etnia: %s' % etnia, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'validarmigrante':
            try:
                form = MigranteValidacionForm(request.POST)
                if form.is_valid():
                    migrante = MigrantePersona.objects.get(pk=int(request.POST['idm']))
                    migrante.estadoarchivo = form.cleaned_data['estadomigrante']
                    migrante.observacion = form.cleaned_data['observacionmigrante'].strip().upper()
                    migrante.verificado = True if int(form.cleaned_data['estadomigrante']) == 2 else False
                    migrante.save(request)
                    log(u'Actualizó registro de migrante: %s' % migrante, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})


    data['title'] = u'Verificación de Documentos'
    data['inscripciones'] = Inscripcion.objects.filter(matricula__status=True, matricula__nivel__periodo=periodo,persona__perfilinscripcion__tienediscapacidad=True).order_by("persona")
    data['artista'] = Inscripcion.objects.filter(matricula__status=True, matricula__nivel__periodo=periodo, persona__artistapersona__isnull=False, persona__artistapersona__status=True, persona__artistapersona__vigente=1).order_by("persona")
    data['becado'] = Inscripcion.objects.filter(matricula__status=True, matricula__nivel__periodo=periodo, persona__becapersona__isnull=False, persona__becapersona__status=True, persona__becapersona__fechafin__isnull=True).order_by("persona")
    data['deportista'] = Inscripcion.objects.filter(matricula__status=True, matricula__nivel__periodo=periodo, persona__deportistapersona__isnull=False, persona__deportistapersona__status=True, persona__deportistapersona__vigente=1).order_by("persona")
    data['etnia'] = etnias = Inscripcion.objects.filter(matricula__status=True, matricula__nivel__periodo=periodo, persona__perfilinscripcion__raza__id__in=[1, 2, 4, 5]).order_by("persona")
    # data['etnia'] = None
    data['migrante'] = Inscripcion.objects.filter(matricula__status=True, matricula__nivel__periodo=periodo, persona__migrantepersona__isnull=False, persona__migrantepersona__status=True).order_by("persona")

    data['form'] = ArtistaValidacionForm()
    data['form2'] = BecaValidacionForm()
    data['form3'] = DeportistaValidacionForm()
    data['form4'] = DiscapacidadValidacionForm()
    data['form5'] = EtniaValidacionForm()
    data['form6'] = MigranteValidacionForm()


    data['reporte_1'] = obtener_reporte('hoja_vida_sagest')
    data['reporte_2'] = obtener_reporte('discapacitados')
    return render(request, "adm_discapacitados/view.html", data)