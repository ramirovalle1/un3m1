# -*- coding: latin-1 -*-
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse
from django.db import transaction
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.models import TemaUnidadResultadoProgramaAnalitico, DetalleSilaboSemanalTema, Materia

# @login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'editar':
                try:
                    d = 'hola'
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'menu':
                try:
                    data['title'] = u'Registrados en esta actividad'
                    idrecurso=0
                    idexperiencia = 0
                    idsubtema = 0
                    idlectura = 0
                    nom = request.GET['nom']
                    idmoculto = request.GET['idmoculto']
                    if 'idrecurso' in request.GET:
                        idrecurso = request.GET['idrecurso']
                    if 'idsubtema' in request.GET:
                        idsubtema = request.GET['idsubtema']
                    if 'idexperiencia' in request.GET:
                        idexperiencia = request.GET['idexperiencia']
                    if 'idlectura' in request.GET:
                        idlectura = request.GET['idlectura']
                    tema = TemaUnidadResultadoProgramaAnalitico.objects.get(pk=request.GET['idtema'])
                    # data['listasubtemas'] = tema.subtemaunidadresultadoprogramaanalitico_set.db_manager('sga_select').filter(detallesilabosemanalsubtema__silabosemanal__silabo__materia__id=idmoculto, status=True).distinct().order_by('orden')
                    data['listasubtemas'] = tema.subtemaunidadresultadoprogramaanalitico_set.filter(detallesilabosemanalsubtema__silabosemanal__silabo__materia__id=idmoculto, status=True).distinct().order_by('orden')
                    data['listastemas'] = TemaUnidadResultadoProgramaAnalitico.objects.filter(detallesilabosemanaltema__silabosemanal__silabo__materia__id=idmoculto,detallesilabosemanaltema__silabosemanal__silabo__status=True,detallesilabosemanaltema__silabosemanal__status=True,detallesilabosemanaltema__status=True, status=True).distinct().order_by('orden')
                    data['listaactividades'] = tema.virtualactividadessilabo_set.filter(silabosemanal__silabo__materia__id=idmoculto, status=True).distinct().distinct().order_by('id')
                    data['listarecursos'] = tema.virtualmasrecursosilabo_set.filter(silabosemanal__silabo__materia__id=idmoculto, status=True).distinct().distinct().order_by('tiporecurso','id')
                    data['listacasospracticos'] = tema.virtualcasospracticossilabo_set.filter(silabosemanal__silabo__materia__id=idmoculto, status=True).distinct().distinct().order_by('id')
                    data['listatestsilabos'] = tema.virtualtestsilabo_set.filter(silabosemanal__silabo__materia__id=idmoculto, status=True).distinct().distinct().order_by('id')
                    data['listalecturasilabos'] = tema.virtuallecturassilabo_set.filter(silabosemanal__silabo__materia__id=idmoculto, status=True).distinct().distinct().order_by('id')
                    num_tema = request.GET['num_tema']
                    data['nom'] = nom
                    data['num_tema'] = num_tema
                    data['idsubtema'] = int(idsubtema)
                    data['idexperiencia'] = int(idexperiencia)
                    data['idtema'] = tema
                    data['idmoculto'] = int(idmoculto)
                    data['idrecurso'] = int(idrecurso)
                    data['idlectura'] = int(idlectura)
                    return render(request, "contenidosonline/menu.html", data)
                except Exception as ex:
                    pass

            if action == 'rutas':
                try:
                    data['nom'] = 26456
                    return render(request, "contenidosonline/rutas.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Listado de actividades extracurriculares'
            data['nommateria'] = materia = Materia.objects.get(pk=request.GET['codimat'])
            # data['nommateria'] = materia = Materia.objects.get(pk=18814)
            # data['nommateria'] = materia = Materia.objects.get(pk=15120)
            totalcon = int(DetalleSilaboSemanalTema.objects.values('temaunidadresultadoprogramaanalitico_id').filter(temaunidadresultadoprogramaanalitico__status=True, silabosemanal__status=True, silabosemanal__silabo__status=True, silabosemanal__silabo__materia=materia).distinct().count() / 2)
            data['numtemas'] = list(range(1,totalcon + 1))
            return render(request, "contenidosonline/view.html", data)