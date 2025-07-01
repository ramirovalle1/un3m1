# -*- coding: UTF-8 -*-
import json
import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction, connection
from django.db.models import Max
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.context import Context
from django.template.loader import get_template
from decorators import secure_module, last_access
from sagest.models import ExperienciaLaboral
from sga.commonviews import adduserdata
from sga.forms import SilaboForm, BibliografiaProgramaAnaliticoAsignaturaForm, GPPracticaFrom
from sga.funciones import log, generar_nombre
from sga.lecciones_dia import daterange
from sga.models import Materia, ContenidoResultadoProgramaAnalitico, SilaboSemanal, Titulacion, \
    DetalleSilaboSemanalTema, DetalleSilaboSemanalSubtema, BibliografiaProgramaAnaliticoAsignatura, \
    DetalleSilaboSemanalBibliografia, SubtemaUnidadResultadoProgramaAnalitico, ProgramaAnaliticoAsignatura, \
    DetalleSilaboSemanalBibliografiaDocente, Silabo, UnidadResultadoProgramaAnalitico, GPGuiaPracticaSemanal, \
    LaboratorioAcademia, InventarioLaboratorioAcademia, GPInstruccion, GPLugarPracticaDetalle
from sga.funcionesxhtml2pdf import conviert_html_to_pdf


def daterange(start_date, end_date):
    for ordinal in range(start_date.toordinal(), end_date.toordinal()):
        yield datetime.date.fromordinal(ordinal)

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_profesor():
        return HttpResponseRedirect("/?info=Solo los perfiles de profesores pueden ingresar al modulo.")
    data['profesor'] = profesor = perfilprincipal.profesor
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']
            if action == 'addpsemanasilabo':
                try:
                    subtema = ''
                    tema = ''
                    form = SilaboForm(request.POST)
                    if form.is_valid():
                        cadena = request.POST['id'].split("_")
                        materia = Materia.objects.get(pk=cadena[0])
                        silabosemana = SilaboSemanal(materia=materia,
                                                     numsemana=cadena[4],
                                                     semana=cadena[1],
                                                     fechainiciosemana=cadena[2],
                                                     fechafinciosemana=cadena[3],
                                                     objetivoaprendizaje=form.cleaned_data['objetivoaprendizaje'],
                                                     enfoque=form.cleaned_data['enfoque'],
                                                     recursos=form.cleaned_data['recursos'],
                                                     evaluacion=form.cleaned_data['evaluacion'])
                        silabosemana.save(request)
                        log(u'Adiciono una semana del Plan de Estudio: %s - %s' % (silabosemana, materia), request, "add")
                        return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'eliminarbibliografia':
                try:
                    lib = DetalleSilaboSemanalBibliografiaDocente.objects.get(pk=request.POST['codigobiblio'])
                    lib.delete()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            if action == 'listadelbibliografia':
                try:
                    lib = DetalleSilaboSemanalBibliografiaDocente.objects.get(pk=request.POST['id'])
                    nombrelibro = lib.librokohaprogramaanaliticoasignatura.nombre
                    codigolibro = lib.id
                    return JsonResponse({"result": "ok", 'descripcion': nombrelibro, 'codigolibro': codigolibro})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'adicionarbibliografia':
                try:
                    f = BibliografiaProgramaAnaliticoAsignaturaForm(request.POST)
                    if f.is_valid():
                        if DetalleSilaboSemanalBibliografiaDocente.objects.filter(librokohaprogramaanaliticoasignatura_id=int(f.cleaned_data['bibliografia']), silabosemanal_id=request.POST['id']).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Ya se encuentra registrada."})
                        bibliografia = DetalleSilaboSemanalBibliografiaDocente(librokohaprogramaanaliticoasignatura_id=int(f.cleaned_data['bibliografia']),
                                                                               silabosemanal_id=request.POST['id'])
                        bibliografia.save(request)
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'addpsemanasilaboresultado':
                try:
                    subtema = ''
                    tema = ''
                    bibliografia = ''
                    listaometodologia = json.loads(request.POST['lista_items2'])
                    if 'lista_items1' in request.POST:
                        subtema = json.loads(request.POST['lista_items1'])
                    if 'lista_items2' in request.POST:
                        tema = json.loads(request.POST['lista_items2'])
                    cadena = request.POST['id'].split("_")
                    silabo = Silabo.objects.get(pk=cadena[0])
                    silabosemana = SilaboSemanal(silabo=silabo,
                                                 numsemana=cadena[4],
                                                 semana=cadena[1],
                                                 fechainiciosemana=cadena[2],
                                                 fechafinciosemana=cadena[3],
                                                 objetivoaprendizaje='',
                                                 enfoque='',
                                                 recursos='',
                                                 evaluacion='',
                                                 horaspresencial=0,
                                                 horaautonoma=0)
                    silabosemana.save(request)
                    if subtema:
                        for subt in subtema:
                            ingresosubt = DetalleSilaboSemanalSubtema(silabosemanal_id=silabosemana.id,
                                                                      subtemaunidadresultadoprogramaanalitico_id=subt)
                            ingresosubt.save(request)
                    if tema:
                        for tem in tema:
                            ingresostemas = DetalleSilaboSemanalTema(silabosemanal_id=silabosemana.id,
                                                                     temaunidadresultadoprogramaanalitico_id=tem)
                            ingresostemas.save(request)
                    return JsonResponse({"result": "ok"}, )
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'deletetemasilabo':
                try:
                    valor = False
                    if DetalleSilaboSemanalTema.objects.filter(temaunidadresultadoprogramaanalitico_id=request.POST['idtema'], silabosemanal_id=request.POST['idsilabosemanal']).exists():
                        temasilabo = DetalleSilaboSemanalTema.objects.get(temaunidadresultadoprogramaanalitico_id=request.POST['idtema'], silabosemanal_id=request.POST['idsilabosemanal'])
                        subtemasilabo = DetalleSilaboSemanalSubtema.objects.filter(subtemaunidadresultadoprogramaanalitico__temaunidadresultadoprogramaanalitico_id=temasilabo.temaunidadresultadoprogramaanalitico_id, silabosemanal_id=request.POST['idsilabosemanal'])
                        subtemasilabo.delete()
                        temasilabo.delete()
                        valor = False
                    else:
                        ingresostemas = DetalleSilaboSemanalTema(silabosemanal_id=request.POST['idsilabosemanal'],
                                                                 temaunidadresultadoprogramaanalitico_id=request.POST['idtema'])
                        ingresostemas.save(request)
                        registrosubtemas = SubtemaUnidadResultadoProgramaAnalitico.objects.filter(temaunidadresultadoprogramaanalitico_id=request.POST['idtema'])
                        for sub in registrosubtemas:
                            ingresossubtemas = DetalleSilaboSemanalSubtema(silabosemanal_id=request.POST['idsilabosemanal'],
                                                                           subtemaunidadresultadoprogramaanalitico_id=sub.id)
                            ingresossubtemas.save(request)
                        valor = True
                    return JsonResponse({"result": "ok", 'valor': valor})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            if action == 'deleteteemasilabo':
                try:
                    valor = False
                    if DetalleSilaboSemanalSubtema.objects.filter(subtemaunidadresultadoprogramaanalitico_id=request.POST['idsubtema'], silabosemanal_id=request.POST['idsilabosemanal']).exists():
                        subtemasilabo = DetalleSilaboSemanalSubtema.objects.get(subtemaunidadresultadoprogramaanalitico_id=request.POST['idsubtema'], silabosemanal_id=request.POST['idsilabosemanal'])
                        subtemasilabo.delete()
                        valor = False
                    else:
                        ingresostemas = DetalleSilaboSemanalSubtema(silabosemanal_id=request.POST['idsilabosemanal'],
                                                                    subtemaunidadresultadoprogramaanalitico_id=request.POST['idsubtema'])
                        ingresostemas.save(request)
                        if DetalleSilaboSemanalTema.objects.filter(silabosemanal_id=request.POST['idsilabosemanal'], temaunidadresultadoprogramaanalitico_id=ingresostemas.subtemaunidadresultadoprogramaanalitico.temaunidadresultadoprogramaanalitico_id).exists():
                            a = 0
                        else:
                            ingresostemas = DetalleSilaboSemanalTema(silabosemanal_id=request.POST['idsilabosemanal'],
                                                                     temaunidadresultadoprogramaanalitico_id=ingresostemas.subtemaunidadresultadoprogramaanalitico.temaunidadresultadoprogramaanalitico_id)
                            ingresostemas.save(request)
                        valor = True
                    return JsonResponse({"result": "ok", 'valor': valor})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            if action == 'editsemanasilabo':
                try:
                    form = SilaboForm(request.POST)
                    if form.is_valid():
                        bibliografia = ''
                        if 'lista_items3' in request.POST:
                            bibliografia = json.loads(request.POST['lista_items3'])
                        silabosemana = SilaboSemanal.objects.get(pk=request.POST['id'])
                        silabosemana.objetivoaprendizaje = form.cleaned_data['objetivoaprendizaje']
                        silabosemana.enfoque = form.cleaned_data['enfoque']
                        silabosemana.recursos = form.cleaned_data['recursos']
                        silabosemana.evaluacion = form.cleaned_data['evaluacion']
                        silabosemana.horaspresencial = form.cleaned_data['horaspresencial']
                        silabosemana.horaautonoma = form.cleaned_data['horaautonoma']
                        silabosemana.save(request)
                        deletebibliografia = DetalleSilaboSemanalBibliografia.objects.filter(silabosemanal_id=silabosemana.id)
                        deletebibliografia.delete()
                        if bibliografia:
                            for bib in bibliografia:
                                ingresosbibliografia = DetalleSilaboSemanalBibliografia(silabosemanal_id=silabosemana.id,
                                                                                        bibliografiaprogramaanaliticoasignatura_id=bib)
                                ingresosbibliografia.save(request)
                        # log(u'Adiciono Plan de Estudio Malla: %s - %s' % (malla, programaanaliticomalla.fecha), request, "add")
                        return JsonResponse({"result": "ok"}, )
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'silabopdf':
                try:
                    lista = []
                    listaid = []
                    listaidsolo = []
                    data['silabo'] = silabo = Silabo.objects.get(pk=request.POST['id'])
                    data['materia'] = materia = Materia.objects.get(pk=silabo.materia.id)
                    # data['hoy'] = datetime.now()
                    cursor = connection.cursor()
                    cursor.execute("select distinct con.id,con.descripcion,con.orden,si.id,si.numsemana,si.fechainiciosemana,si.fechafinciosemana from sga_detallesilabosemanaltema t, sga_temaunidadresultadoprogramaanalitico tu,sga_unidadresultadoprogramaanalitico uni,sga_contenidoresultadoprogramaanalitico con,sga_silabosemanal si where si.id=t.silabosemanal_id and temaunidadresultadoprogramaanalitico_id=tu.id and tu.unidadresultadoprogramaanalitico_id=uni.id and uni.contenidoresultadoprogramaanalitico_id=con.id and si.silabo_id='" + str(silabo.id) + "' order by con.orden")
                    results = cursor.fetchall()
                    for r in results:
                        sila = SilaboSemanal.objects.get(pk=r[3])
                        lista.append([r[0], sila])
                        if r[0] not in listaidsolo:
                            listaidsolo.append(r[0])
                    data['lista'] = lista
                    data['listaid'] = listaidsolo
                    data['aprendizajes'] = UnidadResultadoProgramaAnalitico.objects.filter(contenidoresultadoprogramaanalitico__in=listaidsolo)
                    data['proanalitico'] = ProgramaAnaliticoAsignatura.objects.get(pk=silabo.programaanaliticoasignatura.id)
                    data['bibliografia'] = BibliografiaProgramaAnaliticoAsignatura.objects.filter(programaanaliticoasignatura=silabo.programaanaliticoasignatura)
                    data['titulos'] = Titulacion.objects.filter(persona=persona, titulo__nivel_id__in=[3, 4], status=True)
                    data['persona'] = persona
                    data['fechaactual'] = datetime.date.today()
                    data['experiencialaboral'] = ExperienciaLaboral.objects.filter(persona=persona, status=True)
                    return conviert_html_to_pdf(
                        'pro_silabos/silabo_pdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    pass

            # if action == 'addpractica':
            #     try:
            #         form = GPPracticaFrom(request.POST, request.FILES)
            #         if 'lista_items1' in request.POST and not json.loads(request.POST['lista_items1']):
            #             return JsonResponse({"result": "bad", "mensaje": u"No a elegido un equipo/intrumento"})
            #         if not request.POST['lista_items2']:
            #             return JsonResponse({"result": "bad", "mensaje": u"No a elegido un material/insumo"})
            #         listadoequipos = InventarioLaboratorioAcademia.objects.filter(id__in=[int(datos['idequipo']) for datos in json.loads(request.POST['lista_items1'])]) if request.POST['lista_items1'] else []
            #         listaproductos=[]
            #         for datos in json.loads(request.POST['lista_items2']):
            #             listaproductos.append((int(datos['idproducto']), int(datos['cantidad'])))
            #         if form.is_valid():
            #             practica = GPGuiaPracticaSemanal(silabosemanal_id = request.POST['id'],
            #                                              temapractica_id = request.POST['temapractica'],
            #                                              numeropractica = int(request.POST['npractica']),
            #                                              tiempoactividad = request.POST['tiempoactividad'],
            #                                              fechaelaboracion = form.cleaned_data['fechaelaboracion'],
            #                                              individual = form.cleaned_data['individual'] if 'individual' in request.POST else False,
            #                                              grupo = form.cleaned_data['grupo'] if 'grupo' in request.POST else False,
            #                                              cantidadalumnogrupo = form.cleaned_data['cantidadalumnogrupo'] if 'cantidadalumnogrupo' in request.POST else 0,
            #                                              objetvopactica = form.cleaned_data['objetvopactica'],
            #                                              actividaddesarrollar = form.cleaned_data['actividaddesarrollar'],
            #                                              rubica = form.cleaned_data['rubica'])
            #             practica.save(request)
            #             log(u'Adiciono una practica a la semana: %s - %s' % (practica, practica.silabosemanal.silabo.materia), request, "add")
            #             newfile=None
            #             if 'instruccionarchivo' in request.FILES:
            #                 newfile = request.FILES['instruccionarchivo']
            #                 newfile._name = generar_nombre("instruccion_", newfile._name)
            #                 instruccion = GPInstruccion(guiasemanal=practica,observacion=form.cleaned_data['instruccionobservacion'],archivo=newfile)
            #                 instruccion.save(request)
            #             lugarlaboratorio = GPLugarPractica(guiasemanal_id=practica.id,laboratorio_id=int(request.POST['laboratorio']))
            #             lugarlaboratorio.save(request)
            #             for equipo in listadoequipos:
            #                 detallelaboratorio = GPLugarPracticaDetalle(lugarparctica=lugarlaboratorio, detalle_id=equipo.id)
            #                 detallelaboratorio.save(request)
            #             for producto in listaproductos:
            #                 detallelaboratorio = GPLugarPracticaDetalle(lugarparctica=lugarlaboratorio, detalle_id=int(producto[0]), cantidad=int(producto[1]))
            #                 detallelaboratorio.save(request)
            #             return JsonResponse({"result": "ok"}, )
            #         else:
            #              raise NameError('Error')
            #     except Exception as ex:
            #         transaction.set_rollback(True)
            #         return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            #
            # if action == 'delpractica':
            #     try:
            #         if 'id' in request.POST:
            #             equipo = GPGuiaPracticaSemanal.objects.get(pk=request.POST['id'])
            #             equipo.gplugarpractica_set.all()[0].gplugarpracticadetalle_set.all().delete()
            #             equipo.gplugarpractica_set.all().delete()
            #             equipo.gpinstruccion_set.all().delete()
            #             log(u'Elimino la Práctica : %s' % (equipo.silabosemanal.silabo.materia.asignatura), request, "del")
            #             equipo.delete()
            #             return JsonResponse({"result": "ok"}, )
            #         else:
            #              raise NameError('Error')
            #     except Exception as ex:
            #         transaction.set_rollback(True)
            #         return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            #
            # if action == 'editpractica':
            #     try:
            #         form = GPPracticaFrom(request.POST, request.FILES)
            #         if request.POST['lista_items1'] and not json.loads(request.POST['lista_items1']):
            #             return JsonResponse({"result": "bad", "mensaje": u"No a elegido un equipo/intrumento"})
            #         if not request.POST['lista_items2']:
            #             return JsonResponse({"result": "bad", "mensaje": u"No a elegido un material/insumo"})
            #         listadoequipos = InventarioLaboratorioAcademia.objects.filter(id__in=[int(datos['idequipo']) for datos in json.loads(request.POST['lista_items1'])]) if request.POST['lista_items1'] else []
            #         listaproductos=[]
            #         for datos in json.loads(request.POST['lista_items2']):
            #             listaproductos.append((int(datos['idproducto']), int(datos['cantidad'])))
            #         if form.is_valid():
            #             practica = GPGuiaPracticaSemanal.objects.get(pk=int(request.POST['id']))
            #             practica.temapractica_id=request.POST['temapractica']
            #             practica.tiempoactividad=request.POST['tiempoactividad']
            #             practica.fechaelaboracion=form.cleaned_data['fechaelaboracion']
            #             practica.individual=form.cleaned_data['individual'] if 'individual' in request.POST else False
            #             practica.grupo=form.cleaned_data['grupo'] if 'grupo' in request.POST else False
            #             practica.cantidadalumnogrupo=form.cleaned_data['cantidadalumnogrupo'] if 'cantidadalumnogrupo' in request.POST else 0
            #             practica.objetvopactica=form.cleaned_data['objetvopactica']
            #             practica.actividaddesarrollar=form.cleaned_data['actividaddesarrollar']
            #             practica.rubica=form.cleaned_data['rubica']
            #             practica.save(request)
            #             log(u'Adiciono una practica a la semana: %s - %s' % (practica, practica.silabosemanal.silabo.materia), request, "edit")
            #             instruccion = GPInstruccion.objects.get(pk=practica.gpinstruccion_set.filter(status=True)[0].id,status=True)
            #             if 'instruccionarchivo' in request.FILES:
            #                 newfile = request.FILES['instruccionarchivo']
            #                 newfile._name = generar_nombre("instruccion_", newfile._name)
            #                 instruccion.observacion=form.cleaned_data['instruccionobservacion']
            #                 instruccion.archivo=newfile
            #             else:
            #                 instruccion.observacion = form.cleaned_data['instruccionobservacion']
            #             instruccion.save(request)
            #             lugarlaboratorio = GPLugarPractica.objects.get(pk=practica.mi_laboratorio().id, status = True)
            #             lugarlaboratorio.laboratorio_id=int(request.POST['laboratorio'])
            #             lugarlaboratorio.save(request)
            #             for deta in practica.mi_laboratorio().gplugarpracticadetalle_set.filter(status=True, detalle__activo__isnull=False):
            #                 deta.status=False
            #                 deta.save(request)
            #             for equipo in listadoequipos:
            #                 if practica.mi_laboratorio().gplugarpracticadetalle_set.filter(detalle_id = equipo.id).exists():
            #                     detallelaboratorio = practica.mi_laboratorio().gplugarpracticadetalle_set.get(detalle_id = equipo.id)
            #                     detallelaboratorio.status=True
            #                     detallelaboratorio.save(request)
            #                 else:
            #                     detallelaboratorio = GPLugarPracticaDetalle(lugarparctica_id=practica.mi_laboratorio().id, detalle_id=equipo.id)
            #                     detallelaboratorio.save(request)
            #             for deta in practica.mi_laboratorio().gplugarpracticadetalle_set.filter(status=True, detalle__producto__isnull=False):
            #                 deta.status=False
            #                 deta.save(request)
            #             for producto in listaproductos:
            #                 if practica.mi_laboratorio().gplugarpracticadetalle_set.filter(detalle_id=producto[0]).exists():
            #                     detallelaboratorio = practica.mi_laboratorio().gplugarpracticadetalle_set.get(detalle_id=producto[0])
            #                     detallelaboratorio.status=True
            #                     detallelaboratorio.cantidad=producto[1]
            #                     detallelaboratorio.save(request)
            #                 else:
            #                     detallelaboratorio = GPLugarPracticaDetalle(lugarparctica_id=practica.mi_laboratorio().id, detalle_id=int(producto[0]), cantidad=int(producto[1]))
            #                     detallelaboratorio.save(request)
            #             return JsonResponse({"result": "ok"}, )
            #         else:
            #              raise NameError('Error')
            #     except Exception as ex:
            #         transaction.set_rollback(True)
            #         return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})


            return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrectadd."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'silabo':
                try:
                    data['title'] = u'Silabo'
                    if not Silabo.objects.filter(materia_id=request.GET['materia'],profesor=profesor,status=True).exists():
                        materia = Materia.objects.get(pk=request.GET['materia'])
                        programaanalitico = ProgramaAnaliticoAsignatura.objects.get(asignaturamalla=materia.asignaturamalla,activo=True,status=True)
                        crearsilabo = Silabo(materia=materia,
                                             profesor=profesor,
                                             programaanaliticoasignatura=programaanalitico)
                        crearsilabo.save(request)
                    data['silabos'] = Silabo.objects.filter(materia_id=request.GET['materia'],status=True)
                    return render(request, "pro_silabos/silabodocente.html", data)
                except Exception as ex:
                    pass

            if action == 'planclase':
                try:
                    data['title'] = u'PLANIFICACIÓN SEMANAL DE SÍLABO'
                    lista_nueva = []
                    lista_semanas = []
                    panalitico = 0
                    data['silabocab'] = silabocab = Silabo.objects.get(pk=request.GET['silaboid'],status=True)
                    # materia = Materia.objects.get(pk=request.GET['materia'])
                    silabo = SilaboSemanal.objects.filter(silabo=silabocab)
                    if DetalleSilaboSemanalTema.objects.filter(silabosemanal_id__in=silabo).exists():
                        panalitico = 1
                    for dia in daterange(silabocab.materia.inicio, silabocab.materia.fin):
                        if (dia.isocalendar()[1]) not in lista_nueva:
                            lista_nueva.append(dia.isocalendar()[1])
                            obj = ''
                            enf = ''
                            rec = ''
                            eva = ''
                            idcodigo = 0
                            horap = 0
                            modelosilabo = 0
                            horaa = 0
                            for sila in silabo:
                                if sila.semana == dia.isocalendar()[1]:
                                    obj = sila.objetivoaprendizaje
                                    enf = sila.enfoque
                                    rec = sila.recursos
                                    eva = sila.evaluacion
                                    horap = sila.silabo.materia.asignaturamalla.horaspresenciales
                                    horaa = sila.silabo.materia.asignaturamalla.horasautonomas
                                    idcodigo = sila.id
                                    modelosilabo = sila
                            lista_semanas.append([dia.isocalendar()[1], dia, (dia + datetime.timedelta(days=6)), obj, enf, rec, eva, horap, horaa, idcodigo, modelosilabo])
                    data['panalitico'] = panalitico
                    data['fechas'] = lista_semanas
                    data['tiene_practica']= silabocab.materia.practicas
                    return render(request, "pro_silabos/listado_plancase.html", data)
                except Exception as ex:
                    pass

            if action == 'recursopractica':
                try:
                    if 'id' in request.GET:
                        listaactivo = []
                        listaproducto = []
                        activos= InventarioLaboratorioAcademia.objects.filter(laboratorio_id=int(request.GET['id']),status=True, activo__isnull=False)
                        for equipo in activos:
                            listaactivo.append([equipo.id, str(equipo.activo)])
                        productos = InventarioLaboratorioAcademia.objects.filter(laboratorio_id=int(request.GET['id']),status=True, producto__isnull=False)
                        for pro in productos:
                            listaproducto.append([pro.id, str(pro.producto)])
                        if 'idp' in request.GET:
                            practica = GPGuiaPracticaSemanal.objects.get(pk=int(request.GET['idp']))
                            activos =[]
                            for eq in practica.mi_laboratorio().gplugarpracticadetalle_set.filter(status=True,detalle__activo__isnull=False):
                                activos.append([eq.detalle.id, str(eq.detalle.activo)])
                            productos=[]
                            for pro in practica.mi_laboratorio().gplugarpracticadetalle_set.filter(status=True,detalle__producto__isnull=False):
                                productos.append([pro.detalle.id,pro.cantidad,str(pro.detalle.producto.unidadmedida.nombre), str(pro.detalle.producto)])
                            data = {"results": "ok", 'listaactivo': listaactivo, 'listaproducto':listaproducto, 'activos':activos,'productos':productos}
                        else:
                            data = {"results": "ok", 'listaactivo': listaactivo, 'listaproducto': listaproducto}
                        return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'cantidadrecurso':
                try:
                    if 'id' in request.GET:
                        lista = []
                        recurso= InventarioLaboratorioAcademia.objects.get(pk=int(request.GET['id']))
                        for can in range(recurso.cantidad):
                            lista.append([can+1])
                        data = {"results": "ok", 'lista': lista}
                        return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'consultaractivo':
                try:
                    if 'id' in request.GET:
                        recurso= InventarioLaboratorioAcademia.objects.get(pk=int(request.GET['id']))
                        data = {"results": "ok", "recurso": str(recurso.activo)}
                        return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'consultarproducto':
                try:
                    if 'id' in request.GET:
                        recurso= InventarioLaboratorioAcademia.objects.get(pk=int(request.GET['id']))
                        data = {"results": "ok", "producto": str(recurso.producto),"unidad":str(recurso.producto.unidadmedida)}
                        return JsonResponse(data)
                except Exception as ex:
                    pass


            if action == 'practicas':
                try:
                    data['title'] = u'Guia de Prácticas'
                    data['silabosemana'] =  silabosemana = SilaboSemanal.objects.get(pk=int(request.GET['ids']))
                    data['silabo'] = silabosemana.silabo
                    data['practicas']= practica = GPGuiaPracticaSemanal.objects.filter(status=True, silabosemanal_id=silabosemana.id)
                    return render(request, "pro_silabos/viewguiapratica.html", data)
                except Exception as ex:
                    pass

            if action == 'addpractica':
                try:
                    data['title'] = u'Guia de Prácticas'
                    data['silabosemana'] =  silabosemana = SilaboSemanal.objects.get(pk=int(request.GET['ids']))
                    data['silabo'] = silabosemana
                    npractica = \
                    GPGuiaPracticaSemanal.objects.filter(silabosemanal__silabo_id=silabosemana.silabo.id).aggregate(npractica=Max('numeropractica'))['npractica'] if GPGuiaPracticaSemanal.objects.filter(silabosemanal__silabo_id=silabosemana.silabo.id).exists() else 0
                    data['npractica'] = npractica + 1
                    form = GPPracticaFrom(initial={'numeropractica':npractica })#initial={'laboratorio':silabosemana.silabo.materia.laboratorio if silabosemana.silabo.materia.laboratorio else None })
                    form.fields['temapractica'].queryset = silabosemana.detallesilabosemanaltema_set.all()
                    # laboratorio= LaboratorioAcademia.objects.filter(pk=silabosemana.silabo.materia.laboratorio)
                    form.fields['laboratorio'].queryset=LaboratorioAcademia.objects.filter(pk=silabosemana.silabo.materia.laboratorio.id)if silabosemana.silabo.materia.laboratorio else None
                    data['form']=form
                    # data['laboratorios']= LaboratorioAcademia.objects.filter(status=True)
                    return render(request, "pro_silabos/addpractica.html", data)
                except Exception as ex:
                    pass

            if action == 'delpractica':
                try:
                    data['title'] = u'Eliminar la Práctica'
                    data['practica'] =  practica = GPGuiaPracticaSemanal.objects.get(pk=int(request.GET['id']))
                    data['silabo'] = practica.silabosemanal
                    return render(request, "pro_silabos/delpractica.html", data)
                except Exception as ex:
                    pass

            if action == 'editpractica':
                try:
                    data['title'] = u'Editar Guia de Prácticas'
                    data['practicasemana'] = practica = GPGuiaPracticaSemanal.objects.get(pk=int(request.GET['id']))
                    data['silabo'] = practica.silabosemanal
                    form = GPPracticaFrom(initial={'temapractica': practica.temapractica,
                                                   'numeropractica':practica.numeropractica,
                                                   'tiempoactividad':practica.tiempoactividad.strftime("%H:%M"),
                                                   'fechaelaboracion':practica.fechaelaboracion.strftime("%d-%m-%Y"),
                                                   'individual':practica.individual,
                                                   'grupo':practica.grupo,
                                                   'cantidadalumnogrupo':practica.cantidadalumnogrupo if practica.cantidadalumnogrupo else None,
                                                   'objetvopactica':practica.objetvopactica,
                                                   'instruccionobservacion':practica.gpinstruccion_set.filter(status=True)[0].observacion,
                                                   'actividaddesarrollar':practica.actividaddesarrollar,
                                                   'rubica':practica.rubica,
                                                   'laboratorio':practica.mi_laboratorio().laboratorio})#initial={'laboratorio':silabosemana.silabo.materia.laboratorio if silabosemana.silabo.materia.laboratorio else None })
                    form.fields['temapractica'].queryset = practica.silabosemanal.detallesilabosemanaltema_set.filter(status=True)
                    form.fields['temapractica'].queryset = practica.silabosemanal.detallesilabosemanaltema_set.filter(status=True)
                    form.fields['laboratorio'].queryset = LaboratorioAcademia.objects.filter(pk=practica.mi_laboratorio().laboratorio.id)
                    data['form']=form
                    # data['laboratorios']= LaboratorioAcademia.objects.filter(status=True)
                    return render(request, "pro_silabos/editpractica.html", data)
                except Exception as ex:
                    pass

            # if action == 'detalleequipo':
            #     try:
            #         if 'id' in request.GET:
            #             laboratorio = GPLugarPractica.objects.get(pk=int(request.GET['id']), status=True)
            #             data['equipos'] = laboratorio.gplugarpracticadetalle_set.filter(status=True,detalle__activo__isnull=False)
            #             template = get_template("pro_silabos/detalleequipos.html")
            #             json_content = template.render(data)
            #             return JsonResponse({"result": "ok", 'data': json_content})
            #     except Exception as ex:
            #         return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'detallepractica':
                try:
                    if 'id' in request.GET:
                        data['practica'] = practica = GPGuiaPracticaSemanal.objects.get(pk=int(request.GET['id']), status=True)
                        template = get_template("pro_silabos/detallepractica.html")
                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'deldetallelaboratorio':
                try:
                    data['title'] = u'Eliminar la Equipo'
                    data['practica'] =  practica = GPGuiaPracticaSemanal.objects.get(pk=int(request.GET['id']))
                    data['detalle'] = GPLugarPracticaDetalle.objects.get(id=int(request.GET['idd']), practica_id=int(request.GET['id']))
                    data['silabo'] = practica.silabosemanal
                    return render(request, "pro_silabos/delpractica.html", data)
                except Exception as ex:
                    pass


            if action == 'addsemana':
                try:
                    data['title'] = u'Adicionar Plan de Clase'
                    materia = Materia.objects.get(pk=request.GET['id'])
                    data['bibliografia'] = BibliografiaProgramaAnaliticoAsignatura.objects.filter(programaanaliticoasignatura__asignaturamalla=materia.asignaturamalla, programaanaliticoasignatura__activo=True)
                    data['contenido'] = ContenidoResultadoProgramaAnalitico.objects.filter(programaanaliticoasignatura__asignaturamalla=materia.asignaturamalla, programaanaliticoasignatura__activo=True)
                    data['numsemana'] = request.GET['numsemana']
                    data['semana'] = request.GET['semana']
                    data['fini'] = request.GET['fini']
                    data['ffin'] = request.GET['ffin']
                    data['form'] = SilaboForm()
                    data['materia'] = materia
                    return render(request, "pro_silabos/addsemanasilabo.html", data)
                except Exception as ex:
                    pass

            if action == 'addsemanasilabotemas':
                try:
                    data['title'] = u'Adicionar Resultado de Aprendizaje'
                    data['silabo'] = silabo = Silabo.objects.get(pk=request.GET['idsilabo'])
                    data['bibliografia'] = BibliografiaProgramaAnaliticoAsignatura.objects.filter(programaanaliticoasignatura=silabo.programaanaliticoasignatura)
                    data['contenido'] = ContenidoResultadoProgramaAnalitico.objects.filter(programaanaliticoasignatura=silabo.programaanaliticoasignatura)
                    data['numsemana'] = request.GET['numsemana']
                    data['semana'] = request.GET['semana']
                    data['fini'] = request.GET['fini']
                    data['ffin'] = request.GET['ffin']
                    return render(request, "pro_silabos/addsemanasilaboresultado.html", data)
                except Exception as ex:
                    pass

            if action == 'addbibliografiadocente':
                try:
                    data['title'] = u'Adicionar Bibliografía'
                    data['silabo'] = silabo = SilaboSemanal.objects.get(pk=request.GET['codsilabosemana'])
                    data['bibliografia'] = DetalleSilaboSemanalBibliografiaDocente.objects.filter(silabosemanal=silabo)
                    return render(request, "pro_silabos/listadobibliografiadocente.html", data)
                except Exception as ex:
                    pass

            if action == 'editsemanasilabo':
                try:
                    data['title'] = u'Editar Semana Silabo'

                    data['silabo'] = silabo = SilaboSemanal.objects.get(pk=request.GET['codigosilabo'])
                    data['subtemasilabos'] = DetalleSilaboSemanalSubtema.objects.filter(silabosemanal_id=silabo.id)
                    data['temasilabos'] = temasilabos = DetalleSilaboSemanalTema.objects.filter(silabosemanal_id=silabo.id)
                    tem = temasilabos[0]
                    data['bibliografiasilabos'] = DetalleSilaboSemanalBibliografia.objects.filter(silabosemanal_id=silabo.id)
                    data['librosilabos'] = BibliografiaProgramaAnaliticoAsignatura.objects.filter(programaanaliticoasignatura_id=tem.temaunidadresultadoprogramaanalitico.unidadresultadoprogramaanalitico.contenidoresultadoprogramaanalitico.programaanaliticoasignatura_id)
                    data['contenido'] = ContenidoResultadoProgramaAnalitico.objects.filter(programaanaliticoasignatura_id=tem.temaunidadresultadoprogramaanalitico.unidadresultadoprogramaanalitico.contenidoresultadoprogramaanalitico.programaanaliticoasignatura_id)
                    form = SilaboForm(initial={'objetivoaprendizaje': silabo.objetivoaprendizaje,
                                               'enfoque': silabo.enfoque,
                                               'recursos': silabo.recursos,
                                               'evaluacion': silabo.evaluacion,
                                               'horaspresencial': silabo.horaspresencial,
                                               'horaautonoma': silabo.horaautonoma})
                    data['form'] = form
                    return render(request, "pro_silabos/editsemanasilabo.html", data)
                except Exception as ex:
                    pass

            if action == 'adicionarbibliografia':
                try:
                    data['title'] = u'Adicionar Bibliografía'
                    data['silabo'] = SilaboSemanal.objects.get(pk=int(request.GET['id']))
                    form = BibliografiaProgramaAnaliticoAsignaturaForm()
                    data['form'] = form
                    return render(request, "pro_silabos/addbibliografia.html", data)
                except Exception as ex:
                    pass

            if action == 'editsemanasilabotemas':
                try:
                    data['title'] = u'Editar Resultado de Aprendizaje'
                    data['silabo'] = silabo = SilaboSemanal.objects.get(pk=request.GET['codigosilabo'])
                    data['subtemasilabos'] = DetalleSilaboSemanalSubtema.objects.filter(silabosemanal_id=silabo.id)
                    data['temasilabos'] = temasilabos = DetalleSilaboSemanalTema.objects.filter(silabosemanal_id=silabo.id)
                    tem = temasilabos[0]
                    data['bibliografiasilabos'] = DetalleSilaboSemanalBibliografia.objects.filter(silabosemanal_id=silabo.id)
                    data['librosilabos'] = BibliografiaProgramaAnaliticoAsignatura.objects.filter(programaanaliticoasignatura_id=tem.temaunidadresultadoprogramaanalitico.unidadresultadoprogramaanalitico.contenidoresultadoprogramaanalitico.programaanaliticoasignatura_id)
                    data['contenido'] = ContenidoResultadoProgramaAnalitico.objects.filter(programaanaliticoasignatura_id=tem.temaunidadresultadoprogramaanalitico.unidadresultadoprogramaanalitico.contenidoresultadoprogramaanalitico.programaanaliticoasignatura_id)
                    data['permite_modificar'] = False
                    # form = SilaboForm(initial={'objetivoaprendizaje': silabo.objetivoaprendizaje,
                    #                            'enfoque': silabo.enfoque,
                    #                            'recursos': silabo.recursos,
                    #                            'evaluacion': silabo.evaluacion})
                    # data['form'] = form
                    return render(request, "pro_silabos/editsemanasilabotemas.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Silabos de Materias del Profesor'
            periodo = request.session['periodo']
            data['materias'] = Materia.objects.filter(status=True, profesormateria__profesor=profesor, profesormateria__principal=True, nivel__periodo=periodo).distinct().order_by('inicio')
            return render(request, "pro_silabos/view.html", data)