# -*- coding: latin-1 -*-
import sys

from django.template import Context
from django.template.loader import get_template
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from posgrado.forms import AdmiPeriodoForm
from settings import MATRICULACION_LIBRE, VERIFICAR_CONFLICTO_DOCENTE
from sga.commonviews import adduserdata, obtener_reporte
from sga.forms import ClaseForm, AulaForm, ClaseTodosturnosForm, ClaseHorarioForm
from sga.funciones import log, variable_valor
from sga.models import Sede, Carrera, Nivel, Turno, Clase, Materia, NivelMalla, Malla, Aula, Profesor, ProfesorMateria, \
    ClaseAsincronica, DIAS_CHOICES, Bloque, Sesion
from sga.templatetags.sga_extras import encrypt
from inno.models import HorarioTutoriaAcademica
from django.db.models import Sum

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    periodo = request.session['periodo']
    persona = request.session['persona']
    hoy=datetime.now().date()
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addclase':
            try:
                tipoformulario = request.POST['id']
                if tipoformulario == '1':
                    f = ClaseTodosturnosForm(request.POST)
                else:
                    f = ClaseForm(request.POST)
                if f.is_valid():
                    turno = f.cleaned_data['turno']
                    dia = f.cleaned_data['dia']
                    materia = Materia.objects.get(pk=f.cleaned_data['materia'].id)
                    inicio = f.cleaned_data['inicio']
                    fin = f.cleaned_data['fin']
                    tipoprofesor = f.cleaned_data['tipoprofesor']
                    aula = f.cleaned_data['aula'] if 'aula' in request.POST else None
                    claseconflicto = Clase.objects.filter(Q(inicio__lte=inicio, fin__gte=inicio) | Q(inicio__lte=fin, fin__gte=fin) | Q(inicio__gte=inicio, fin__lte=fin), Q(turno=turno, dia=dia, activo=True, materia__cerrado=False, profesor=f.cleaned_data['profesor']))
                    if claseconflicto:
                        return JsonResponse({"result": "bad", "mensaje": u"El profesor ya tiene asignada una materia en ese turno y día."})
                    if aula is not None and aula.id == 218:
                        # CONFLICTO OTRAS CLASES
                        if not ProfesorMateria.objects.filter(profesor=f.cleaned_data['profesor'], novalidahorario=True, activo=True, tipoprofesor = f.cleaned_data['tipoprofesor'], materia=f.cleaned_data['materia']).exists():
                        # claseconflicto = Clase.objects.filter(Q(inicio__lte=inicio, fin__gte=inicio) | Q(inicio__lte=fin, fin__gte=fin) | Q(inicio__gte=inicio, fin__lte=fin), materia=materia, turno=turno, dia=dia, activo=True)
                        # claseconflicto = Clase.objects.filter(materia__nivel__periodo=periodo, turno=turno, dia=dia, materia__asignatura_id=materia.asignatura.id,  activo=True)
                            if claseconflicto.values('id').filter(tipoprofesor = f.cleaned_data['tipoprofesor'], profesor = f.cleaned_data['profesor'], materia__asignatura_id=materia.asignatura.id ).exists():
                                return JsonResponse({"result": "bad", "mensaje": u"La materia ya existe en este turno, dia y profesor en ese rango de fechas."})
                            # elif claseconflicto.values('id').filter(materia__asignatura_id=materia.asignatura.id).exists() and not f.cleaned_data['tipoprofesor'].id == 2:
                            #     return JsonResponse({"result": "bad", "mensaje": u"La materia ya existe en este turno y dia en ese rango de fechas."})
                            elif claseconflicto.values('id').filter(tipoprofesor = f.cleaned_data['tipoprofesor'], profesor = f.cleaned_data['profesor']).exists():
                                return JsonResponse({"result": "bad", "mensaje": u"El profesor ya tiene asignada una materia en ese turno y día."})
                    else:
                        # claseconflicto = Clase.objects.filter(materia__nivel__periodo=periodo, turno=turno, dia=dia,activo=True, materia__cerrado=False)
                        # claseconflicto = Clase.objects.filter(Q(inicio__lte=inicio, fin__gte=inicio) | Q(inicio__lte=fin, fin__gte=fin) | Q(inicio__gte=inicio, fin__lte=fin), materia=materia, turno=turno, dia=dia, activo=True)
                        claseconflicto = Clase.objects.filter(Q(inicio__lte=inicio, fin__gte=inicio) | Q(inicio__lte=fin, fin__gte=fin) | Q(inicio__gte=inicio, fin__lte=fin), materia__nivel__periodo=periodo, turno=turno, dia=dia, activo=True, materia__cerrado=False)
                        if claseconflicto.values('id').filter(tipoprofesor=f.cleaned_data['tipoprofesor'], profesor=f.cleaned_data['profesor'],materia__asignatura_id=materia.asignatura.id).exists():
                            return JsonResponse({"result": "bad","mensaje": u"La materia ya existe en este turno, dia, aula y profesor en ese rango de fechas."})

                        # elif claseconflicto.values('id').filter(aula=aula).exists(): # se quitó validacion para que se guarde cualquier aula
                        #     return JsonResponse({"result": "bad", "mensaje": u"Ya existe un turno asignado en el aula"})

                        elif claseconflicto.values('id').filter(tipoprofesor=f.cleaned_data['tipoprofesor'],profesor=f.cleaned_data['profesor']).exists():
                            return JsonResponse({"result": "bad",  "mensaje": u"El profesor ya tiene asignada una materia en ese turno, día y aula."})

                    # else:
                    #     if claseconflicto.values('id').exists() and not f.cleaned_data['tipoprofesor'].id == 2:
                    #         return JsonResponse({"result": "bad", "mensaje": u"La materia ya existe en este turno y dia en ese rango de fechas."})
                    if f.cleaned_data['inicio'] < materia.inicio:
                        return JsonResponse({"result": "bad", "mensaje": u"Fecha de inicio incorrecta."})
                    # comentado por kerly 12/04/2018
                    # if f.cleaned_data['fin'] > materia.fin:
                    #     return JsonResponse({"result": "bad", "mensaje": u"Fecha fin incorrecta."})
                    # CONFLICTO DOCENTE
                    profesor = f.cleaned_data['profesor']
                    materia.actualizarhtml = True
                    materia.save()
                    if materia.tipomateria == 1:
                        verificar_conflito_docente = profesor.existe_conflicto_docente(periodo, materia, tipoprofesor, inicio, fin, dia, turno)
                        if verificar_conflito_docente[0]:
                            return JsonResponse({"result": "bad","mensaje": verificar_conflito_docente[1]})
                    elif materia.coordinacion().id!=9:
                        verificar_conflito_docente = profesor.existe_conflicto_docente(periodo, materia, tipoprofesor,
                                                                                       inicio, fin, dia, turno)
                        if verificar_conflito_docente[0]:
                            return JsonResponse({"result": "bad", "mensaje": verificar_conflito_docente[1]})
                    clases = Clase.objects.filter(Q(tipoprofesor=f.cleaned_data['tipoprofesor']), Q(materia=f.cleaned_data['materia']), Q(turno=f.cleaned_data['turno']), Q(dia=f.cleaned_data['dia']),
                                                  ((Q(inicio__gte= f.cleaned_data['inicio']) & Q(fin__lte=f.cleaned_data['fin'])) | (Q(inicio__lte= f.cleaned_data['inicio']) & Q(fin__gte=f.cleaned_data['fin'])) |
                                                   (Q(inicio__lte=f.cleaned_data['fin']) & Q(inicio__gte=f.cleaned_data['fin'])) | (Q(fin__gte= f.cleaned_data['inicio']) & Q(fin__lte=f.cleaned_data['fin']))), activo=True)
                    if clases.values('id').filter(Q(profesor__isnull=True) | Q(profesor = f.cleaned_data['profesor'])).exists():
                        clase = clases.filter(Q(profesor__isnull=True) | Q(profesor = f.cleaned_data['profesor']))[0]
                        clase.aula = f.cleaned_data['aula']
                        clase.tipohorario = f.cleaned_data['tipohorario']
                        clase.inicio = f.cleaned_data['inicio']
                        clase.fin = f.cleaned_data['fin']
                        clase.activo = True
                        clase.save(request)
                        log(u'Edito y se activo clase: %s' % clase, request, "edit")
                    else:
                        clase = Clase(materia=f.cleaned_data['materia'],
                                      turno=f.cleaned_data['turno'],
                                      aula=f.cleaned_data['aula'],
                                      tipoprofesor=f.cleaned_data['tipoprofesor'],
                                      tipohorario=f.cleaned_data['tipohorario'],
                                      dia=f.cleaned_data['dia'],
                                      inicio=f.cleaned_data['inicio'],
                                      fin=f.cleaned_data['fin'],
                                      activo=True)
                        clase.profesor = f.cleaned_data['profesor']
                        if f.cleaned_data['tipoprofesor'].id in [2, 13]:
                            if f.cleaned_data['grupoprofesor']:
                                clase.grupoprofesor = f.cleaned_data['grupoprofesor']
                        clase.save(request)
                        log(u'Adicionado horario: %s' % clase, request, "add")
                    # Para actualizar la opcion de subir enlace de la asignatura
                    materia.reajuste_horario_clase_seguida_subir_enlace()
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as e:
                error = "%s - %s" % (sys.exc_info()[-1].tb_lineno, e)
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % error})



        if action == 'addclasehorario':
            try:
                f = ClaseHorarioForm(request.POST)
                if f.is_valid():
                    turno = f.cleaned_data['turno']
                    dia = f.cleaned_data['dia']
                    if 'materia_sel' in request.POST:
                        materia = Materia.objects.get(pk=request.POST['materia_sel'])
                    inicio = f.cleaned_data['inicio']
                    fin = f.cleaned_data['fin']
                    tipoprofesor = f.cleaned_data['tipoprofesor']
                    aula = request.POST['id']
                    claseconflicto = Clase.objects.filter(Q(inicio__lte=inicio, fin__gte=inicio) | Q(inicio__lte=fin, fin__gte=fin) | Q(inicio__gte=inicio, fin__lte=fin),Q(turno=turno, dia=dia, activo=True, materia__cerrado=False,profesor=f.cleaned_data['profesor']))
                    if claseconflicto:
                        return JsonResponse({"result": "bad", "mensaje": u"El profesor ya tiene asignada una materia en ese turno y día."})

                    if aula == 218:

                        # CONFLICTO OTRAS CLASES
                        # if not ProfesorMateria.objects.filter(profesor=f.cleaned_data['profesor'], novalidahorario=True, activo=True, tipoprofesor = f.cleaned_data['tipoprofesor'], materia=f.cleaned_data['materia']).exists():
                        # claseconflicto = Clase.objects.filter(Q(inicio__lte=inicio, fin__gte=inicio) | Q(inicio__lte=fin, fin__gte=fin) | Q(inicio__gte=inicio, fin__lte=fin), materia=materia, turno=turno, dia=dia, activo=True)
                        # claseconflicto = Clase.objects.filter(materia__nivel__periodo=periodo, turno=turno, dia=dia, materia__asignatura_id=materia.asignatura.id,  activo=True)
                        claseconflicto = Clase.objects.filter(materia__nivel__periodo=periodo, turno=turno, dia=dia,activo=True)
                        if claseconflicto.values('id').filter(tipoprofesor=f.cleaned_data['tipoprofesor'], profesor=f.cleaned_data['profesor'],materia__asignatura_id=materia.asignatura.id).exists():
                            return JsonResponse({"result": "bad","mensaje": u"La materia ya existe en este turno, dia y profesor en ese rango de fechas."})

                        # elif claseconflicto.values('id').filter(materia__asignatura_id=materia.asignatura.id).exists() and not f.cleaned_data['tipoprofesor'].id == 2:
                        #     return JsonResponse({"result": "bad", "mensaje": u"La materia ya existe en este turno y dia en ese rango de fechas."})

                        elif claseconflicto.values('id').filter(tipoprofesor=f.cleaned_data['tipoprofesor'],profesor=f.cleaned_data['profesor']).exists():
                            return JsonResponse({"result": "bad","mensaje": u"El profesor ya tiene asignada una materia en ese turno y día."})
                    else:
                        claseconflicto = Clase.objects.filter(materia__nivel__periodo=periodo, turno=turno, dia=dia,activo=True)
                        if claseconflicto.values('id').filter(tipoprofesor=f.cleaned_data['tipoprofesor'],profesor=f.cleaned_data['profesor'],materia__asignatura_id=materia.asignatura.id).exists():
                            return JsonResponse({"result": "bad","mensaje": u"La materia ya existe en este turno, dia, aula y profesor en ese rango de fechas."})

                        # elif claseconflicto.values('id').filter(aula=aula).exists() :
                        #     return JsonResponse({"result": "bad", "mensaje": u"Ya existe un turno asignado en el aula"})

                        elif claseconflicto.values('id').filter(tipoprofesor=f.cleaned_data['tipoprofesor'],profesor=f.cleaned_data['profesor']).exists():
                            return JsonResponse({"result": "bad","mensaje": u"El profesor ya tiene asignada una materia en ese turno, día y aula."})
                    if f.cleaned_data['inicio'] < materia.inicio:
                        return JsonResponse({"result": True, "mensaje": u"Fecha de inicio incorrecta."})
                    # comentado por kerly 12/04/2018
                    # if f.cleaned_data['fin'] > materia.fin:
                    #     return JsonResponse({"result": "bad", "mensaje": u"Fecha fin incorrecta."})
                    # CONFLICTO DOCENTE
                    profesor = f.cleaned_data['profesor']
                    materia.actualizarhtml = True
                    materia.save()
                    if materia.tipomateria == 1:
                        verificar_conflito_docente = profesor.existe_conflicto_docente(periodo, materia, tipoprofesor, inicio, fin, dia, turno)
                        if verificar_conflito_docente[0]:
                            return JsonResponse({"result": "bad","mensaje": verificar_conflito_docente[1]})
                    elif materia.coordinacion().id!=9:
                        verificar_conflito_docente = profesor.existe_conflicto_docente(periodo, materia, tipoprofesor,
                                                                                       inicio, fin, dia, turno)
                        if verificar_conflito_docente[0]:
                            return JsonResponse({"result": "bad", "mensaje": verificar_conflito_docente[1]})
                    clases = Clase.objects.filter(Q(tipoprofesor=f.cleaned_data['tipoprofesor']), Q(materia=f.cleaned_data['materia']), Q(turno=f.cleaned_data['turno']), Q(dia=f.cleaned_data['dia']),
                                                  ((Q(inicio__gte= f.cleaned_data['inicio']) & Q(fin__lte=f.cleaned_data['fin'])) | (Q(inicio__lte= f.cleaned_data['inicio']) & Q(fin__gte=f.cleaned_data['fin'])) |
                                                   (Q(inicio__lte=f.cleaned_data['fin']) & Q(inicio__gte=f.cleaned_data['fin'])) | (Q(fin__gte= f.cleaned_data['inicio']) & Q(fin__lte=f.cleaned_data['fin']))), activo=True)
                    if clases.values('id').filter(Q(profesor__isnull=True) | Q(profesor = f.cleaned_data['profesor'])).exists():
                        clase = clases.filter(Q(profesor__isnull=True) | Q(profesor = f.cleaned_data['profesor']))[0]
                        clase.aula = request.POST['id']
                        clase.tipohorario = f.cleaned_data['tipohorario']
                        clase.inicio = f.cleaned_data['inicio']
                        clase.fin = f.cleaned_data['fin']
                        clase.activo = True
                        clase.save(request)
                        log(u'Edito y se activo clase: %s' % clase, request, "edit")
                    else:
                        clase = Clase(materia=materia,
                                      turno=f.cleaned_data['turno'],
                                      aula_id=request.POST['id'],
                                      tipoprofesor=f.cleaned_data['tipoprofesor'],
                                      tipohorario=f.cleaned_data['tipohorario'],
                                      dia=f.cleaned_data['dia'],
                                      inicio=f.cleaned_data['inicio'],
                                      fin=f.cleaned_data['fin'],
                                      activo=True)
                        clase.profesor = f.cleaned_data['profesor']
                        if f.cleaned_data['tipoprofesor'].id == 2:
                            if f.cleaned_data['grupoprofesor']:
                                clase.grupoprofesor = f.cleaned_data['grupoprofesor']
                        clase.save(request)
                        log(u'Adicionado horario: %s' % clase, request, "add")
                    # Para actualizar la opcion de subir enlace de la asignatura
                    materia.reajuste_horario_clase_seguida_subir_enlace()
                    return JsonResponse({"result": False, 'modalname': 'itemspanelmatricula', 'cerrar': True, 'mensaje': 'Registro guardado con exito'}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})

        elif action == 'editclase':
            try:
                f = ClaseForm(request.POST)
                if f.is_valid():
                    clase = Clase.objects.get(pk=request.POST['id'])
                    inicio = f.cleaned_data['inicio']
                    tipoprofesor = f.cleaned_data['tipoprofesor']
                    fin = f.cleaned_data['fin']
                    materia = clase.materia
                    turno = f.cleaned_data['turno']
                    dia = f.cleaned_data['dia']
                    # CONFLICTO OTRAS CLASES
                    if f.cleaned_data['inicio'] < materia.inicio:
                        return JsonResponse({"result": "bad", "mensaje": u"Fecha de inicio incorrecta."})
                    # comentado por kerly 12/04/2019
                    # if f.cleaned_data['fin'] > materia.fin:
                    #     return JsonResponse({"result": "bad", "mensaje": u"Fecha fin incorrecta."})
                    if f.cleaned_data['inicio'] < materia.inicio:
                        return JsonResponse({"result": "bad", "mensaje": u"Fecha de inicio incorrecta."})
                    # comentado por kerly 12/04/2019
                    # if f.cleaned_data['fin'] > materia.fin:
                    #     return JsonResponse({"result": "bad", "mensaje": u"Fecha fin incorrecta."})
                    # CONFLICTO DOCENTE
                    profesor = f.cleaned_data['profesor']
                    if materia.tipomateria == 1:
                        verificar_conflito_docente = profesor.existe_conflicto_docente(periodo, materia, tipoprofesor, inicio, fin, dia, turno, False, clase)
                        if verificar_conflito_docente[0]:
                            return JsonResponse({"result": "bad", "mensaje": verificar_conflito_docente[1]})
                    elif materia.coordinacion().id != 9:
                        verificar_conflito_docente = profesor.existe_conflicto_docente(periodo, materia, tipoprofesor, inicio, fin, dia, turno, False, clase)
                        if verificar_conflito_docente[0]:
                            return JsonResponse({"result": "bad", "mensaje": verificar_conflito_docente[1]})
                    clase.aula = f.cleaned_data['aula']
                    clase.inicio = f.cleaned_data['inicio']
                    clase.fin = f.cleaned_data['fin']
                    clase.turno = f.cleaned_data['turno']
                    clase.dia= f.cleaned_data['dia']
                    clase.tipoprofesor = f.cleaned_data['tipoprofesor']
                    clase.tipohorario = f.cleaned_data['tipohorario']
                    clase.profesor = f.cleaned_data['profesor']
                    if f.cleaned_data['tipoprofesor'].id in [2, 13]:
                        if f.cleaned_data['grupoprofesor']:
                            clase.grupoprofesor = f.cleaned_data['grupoprofesor']
                        else:
                            clase.grupoprofesor = None
                    else:
                        clase.grupoprofesor = None
                    clase.save(request)
                    materia.actualizarhtml = True
                    materia.save()
                    # Para actualizar la opcion de subir enlace de la asignatura
                    materia.reajuste_horario_clase_seguida_subir_enlace()
                    lecciones_falso = clase.lista_leccion_falso()
                    if lecciones_falso:
                        for lecc in lecciones_falso:
                            lecc.delete()
                    log(u'Modifico horario: %s' % clase, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editclaseturnosinactivos':
            try:
                f = ClaseTodosturnosForm(request.POST)
                if f.is_valid():
                    clase = Clase.objects.get(pk=request.POST['id'])
                    inicio = f.cleaned_data['inicio']
                    tipoprofesor = f.cleaned_data['tipoprofesor']
                    fin = f.cleaned_data['fin']
                    materia = clase.materia
                    turno = f.cleaned_data['turno']
                    dia = f.cleaned_data['dia']
                    # CONFLICTO OTRAS CLASES
                    if f.cleaned_data['inicio'] < materia.inicio:
                        return JsonResponse({"result": "bad", "mensaje": u"Fecha de inicio incorrecta."})
                    # comentado por kerly 12/04/2019
                    # if f.cleaned_data['fin'] > materia.fin:
                    #     return JsonResponse({"result": "bad", "mensaje": u"Fecha fin incorrecta."})
                    if f.cleaned_data['inicio'] < materia.inicio:
                        return JsonResponse({"result": "bad", "mensaje": u"Fecha de inicio incorrecta."})
                    # comentado por kerly 12/04/2019
                    # if f.cleaned_data['fin'] > materia.fin:
                    #     return JsonResponse({"result": "bad", "mensaje": u"Fecha fin incorrecta."})
                    # CONFLICTO DOCENTE
                    profesor = f.cleaned_data['profesor']
                    verificar_conflito_docente = profesor.existe_conflicto_docente(periodo, materia, tipoprofesor, inicio, fin, dia, turno, False, clase)
                    if verificar_conflito_docente[0]:
                        return JsonResponse({"result": "bad", "mensaje": verificar_conflito_docente[1]})
                    clase.aula = f.cleaned_data['aula']
                    clase.inicio = f.cleaned_data['inicio']
                    clase.fin = f.cleaned_data['fin']
                    clase.turno = f.cleaned_data['turno']
                    clase.dia= f.cleaned_data['dia']
                    clase.tipoprofesor = f.cleaned_data['tipoprofesor']
                    clase.tipohorario = f.cleaned_data['tipohorario']
                    clase.profesor = f.cleaned_data['profesor']
                    if f.cleaned_data['tipoprofesor'].id in [2, 13]:
                        if f.cleaned_data['grupoprofesor']:
                            clase.grupoprofesor = f.cleaned_data['grupoprofesor']
                        else:
                            clase.grupoprofesor = None
                    else:
                        clase.grupoprofesor = None
                    materia.actualizarhtml = True
                    materia.save()
                    clase.save(request)
                    # Para actualizar la opcion de subir enlace de la asignatura
                    materia.reajuste_horario_clase_seguida_subir_enlace()
                    log(u'Modifico horario: %s' % clase, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'duplicarhorario':
            try:
                miclase = Clase.objects.get(pk=int(encrypt(request.POST['id'])))
                sesion = miclase.materia.nivel.sesion
                listamensajeconflicto = []
                conflictohorario = False
                data = {}
                contar_conflictos = 0
                contar_sin_conflictos = 0
                json_content = None
                if periodo.tipo.id==3:
                    rangodias = 8
                else:
                    rangodias = 6
                for i in range(miclase.dia + 1, rangodias):
                    if sesion.dia_habilitado(i):
                        if not Clase.objects.values('id').filter(materia=miclase.materia, turno=miclase.turno, dia=i, inicio=miclase.inicio, fin=miclase.fin, activo=True).exists():
                            # CONFLICTO DOCENTE
                            verificar_conflito_docente = miclase.profesor.existe_conflicto_docente(periodo, miclase.materia, miclase.tipoprofesor,  miclase.inicio, miclase.fin,i, miclase.turno)
                            if not verificar_conflito_docente[0]:
                                clases = Clase.objects.filter(Q(tipoprofesor=miclase.tipoprofesor), Q(materia=miclase.materia), Q(turno=miclase.turno), Q(dia=i),
                                                              ((Q(inicio__gte=miclase.inicio) & Q(fin__lte=miclase.fin)) | (Q(inicio__lte=miclase.inicio) & Q(fin__gte=miclase.fin)) |
                                                               (Q(inicio__lte=miclase.fin) & Q(inicio__gte=miclase.inicio)) | (Q(fin__gte=miclase.inicio) & Q(fin__lte=miclase.fin))), activo=True)
                                if clases.values('id').filter(Q(profesor__isnull=True) | Q(profesor=miclase.profesor)).exists():
                                    clase_clon = clases.filter(Q(profesor__isnull=True) | Q(profesor=miclase.profesor))[0]
                                    clase_clon.aula = miclase.aula
                                    clase_clon.tipohorario = miclase.tipohorario
                                    clase_clon.inicio = miclase.inicio
                                    clase_clon.fin = miclase.fin
                                    clase_clon.activo = True
                                    log(u'Edito y se activo clase: %s' % clase_clon, request, "edit")
                                    materia = clase_clon.materia
                                    materia.actualizarhtml = True
                                    materia.save()
                                else:
                                    clase_clon = Clase(materia=miclase.materia,
                                                       turno=miclase.turno,
                                                       inicio=miclase.inicio,
                                                       fin=miclase.fin,
                                                       aula=miclase.aula,
                                                       profesor=miclase.profesor,
                                                       grupoprofesor=miclase.grupoprofesor,
                                                       tipohorario=miclase.tipohorario,
                                                       dia=i,
                                                       activo=True,
                                                       tipoprofesor=miclase.tipoprofesor)
                                    clase_clon.save(request)
                                    materia = clase_clon.materia
                                    materia.actualizarhtml = True
                                    materia.save()
                                    log(u'Adiciono clase: %s' % clase_clon, request, "add")
                                contar_sin_conflictos += 1
                            else:
                                listamensajeconflicto.append(verificar_conflito_docente)
                                conflictohorario = True
                                contar_conflictos+=1
                if conflictohorario:
                    data['mensajes'] = listamensajeconflicto
                    data['contarclasesconflicto'] = contar_conflictos.__str__()
                    data['clasesafectadas'] = contar_sin_conflictos.__str__()
                    template = get_template("niveles/mensajeconflicto.html")
                    json_content = template.render(data)
                return JsonResponse({"result": "ok", 'existeconflicto':conflictohorario, 'segmento':json_content, 'clasesafectadas':contar_sin_conflictos.__str__()})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad"})

        elif action == 'infomateria':
            try:
                materia = Materia.objects.get(pk=request.POST['id'])
                aulas = Aula.objects.filter(aulacoordinacion__coordinacion=materia.nivel.coordinacion())
                return JsonResponse({"result": "ok", "inicio": materia.inicio.strftime('%d-%m-%Y'), "fin": materia.fin.strftime('%d-%m-%Y'), "aulas":[(aula.id, aula.__str__()) for aula in aulas]})
            except Exception as ex:
                return JsonResponse({"result": "bad"})

        elif action == 'clear':
            try:
                nivel = Nivel.objects.get(pk=request.POST['id'])
                if 'materiaid' in request.POST:
                    materia = Materia.objects.get(pk=request.POST['materiaid'])
                    clases = Clase.objects.filter(materia__nivel=nivel, materia=materia, activo=True)
                else:
                    clases = Clase.objects.filter(materia__nivel=nivel, activo=True)
                for clase in clases:
                    materia = clase.materia
                    materia.actualizarhtml = True
                    materia.save()
                    if not clase.tiene_lecciones():
                        clase.delete()
                    else:
                        clase.activo = False
                        clase.save(request)
                log(u"Elimino todos los horarios del nivel: %s" % nivel.paralelo, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'limpiarhorarioparalelo':
            try:
                nivel = Nivel.objects.get(pk=int(request.POST['id']))
                paraleloid = request.POST['paraleloid']
                materias = nivel.materia_set.filter(asignaturamalla__malla__id=int(request.POST['mallaid']))
                if 'nivelmallaid' in request.POST:
                    if int(request.POST['nivelmallaid']) > 0:
                        materias = materias.filter(asignaturamalla__nivelmalla__id=int(request.POST['nivelmallaid']))
                if not paraleloid == '0':
                    materias = materias.filter(paralelo=paraleloid)
                for clase in Clase.objects.filter(materia__id__in=materias.values_list('id', flat=True), activo=True):
                    materia = clase.materia
                    materia.actualizarhtml = True
                    materia.save()
                    log(u"Elimino clase desde horario paralelo desde el boton Limpiar, clase: %s" % clase, request, "del")
                    if not clase.tiene_lecciones():
                        clase.delete()
                    else:
                        clase.activo = False
                        clase.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addaulas':
            try:
                idaula=int(request.POST['idaula'])
                materias = Materia.objects.filter(status=True, nivel_id= request.POST['nivel'], paralelo=request.POST['paraleloid'],
                                                  asignaturamalla__nivelmalla__id=request.POST['nivelmallaid'],
                                                  asignaturamalla__malla__id=request.POST['mallaid']).distinct()
                for x in materias:
                    clases = x.clase_set.filter(activo=True).exclude(tipohorario=2)
                    for c in clases:
                        c.aula_id = idaula
                        c.save(request)
                        log(u"Se adiciono aula (%s) en la clase(%s) en la materia (%s)" % (c.aula, c, x), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'profesoresmateria':
            try:
                id_tipo_profesor = int(request.POST['idt'])
                materia = Materia.objects.get(pk=int(request.POST['idm']), status=True)
                profesoresmateria = materia.profesores_materia_segun_tipoprofesor_pm(id_tipo_profesor)
                listaprofesores = []
                for profesormateria in profesoresmateria:
                    listaprofesores.append([profesormateria.profesor.id, u'%s [Max hrs: %s - Profesor en materia: %s/total: %s]'% (profesormateria.profesor.persona.nombre_completo_inverso(), profesormateria.contar_horario_en_dia(int(request.POST['dia'])), profesormateria.contar_horario_materia_tipoprofesor(), profesormateria.hora)])
                return JsonResponse({'result': 'ok', 'lista': listaprofesores})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

        elif action == 'fechasmaterias':
            try:
                materia = Materia.objects.get(pk=int(request.POST['idm']), status=True)
                inicio = materia.inicio
                fin = materia.fin
                return JsonResponse({'result': 'ok', "inicio": inicio, "fin": fin})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

        elif action == 'turnosesion':
            try:
                sesion = Sesion.objects.get(pk=int(request.POST['ids']), status=True)
                turnos = Turno.objects.filter(status=True, sesion_id=sesion, mostrar=True).distinct()
                listaturnos = []
                for turno in turnos:
                    # listaturnos.append([turno.id, u'%s Turno:' %turno.turno, ])
                    listaturnos.append([turno.id, u'Turno %s [%s a %s]' % (str(turno.turno), turno.comienza.strftime("%H:%M %p"), turno.termina.strftime("%H:%M %p"))])
                    # listaturnos.append(turno.id, turno.turno)
                return JsonResponse({'result': 'ok', 'lista': listaturnos })
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

        elif action == 'grupoprofesor':
            try:
                materia = Materia.objects.get(pk=int(request.POST['idm']), status=True)
                profesor = Profesor.objects.get(pk=int(request.POST['idp']), status=True)
                select = request.POST.get('select', 0)
                tipo = 0
                if 'tipo' in request.POST:
                    tipo = int(request.POST['tipo'])
                profesormateria = None
                if tipo in [0, 2]:
                    # POR DEFECTO SE BUSCA PRACTICA
                    profesormateria = materia.profesormateriapractica(profesor)
                elif tipo in [13]:
                    # SE BUSCA PRACTICA SALUD
                    profesormateria = materia.profesormateriapracticasalud(profesor)
                listaprofesores = []
                if profesormateria:
                    for grupo in profesormateria.gruposprofesormateria_set.filter(status=True):
                        listaprofesores.append([grupo.id, grupo.__str__(), 'select' if grupo.id == select else ''])
                return JsonResponse({'result': 'ok', 'lista': listaprofesores})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

        elif action == 'addclasepegar':
            try:
                json_content = None
                contar_conflictos = 0
                conflictohorario = False
                notificacion_excedio_hora = ''
                idclase = None
                materia = None
                contar_sin_conflictos = 0
                listamensajeconflicto = []
                miclase = Clase.objects.get(pk=int(encrypt(request.POST['idc'])))
                turno = Turno.objects.get(pk=int(encrypt(request.POST['idt'])))
                dia = int(encrypt(request.POST['idd']))
                verificar_conflito_docente = miclase.profesor.existe_conflicto_docente(periodo, miclase.materia, miclase.tipoprofesor, miclase.inicio, miclase.fin, dia, turno, verificar_x_adicionar_o_editar=False)
                if not verificar_conflito_docente[0]:
                    clases = Clase.objects.filter(Q(tipoprofesor=miclase.tipoprofesor), Q(materia=miclase.materia), Q(turno=turno), Q(dia=dia),
                                                  ((Q(inicio__gte=miclase.inicio) & Q(fin__lte=miclase.fin)) | ( Q(inicio__lte=miclase.inicio) & Q(fin__gte=miclase.fin)) |
                                                   (Q(inicio__lte=miclase.fin) & Q(inicio__gte=miclase.inicio)) | (Q(fin__gte=miclase.inicio) & Q(fin__lte=miclase.fin))), activo=True)
                    if clases.values('id').filter(Q(profesor__isnull=True) | Q(profesor=miclase.profesor)).exists():
                        clase = clases.filter(Q(profesor__isnull=True) | Q(profesor=miclase.profesor))[0]
                        clase.aula = miclase.aula
                        clase.tipohorario = miclase.tipohorario
                        clase.inicio = miclase.inicio
                        clase.fin = miclase.fin
                        clase.activo = True
                        clase.save(request)
                        log(u'Edito y se activo clase: %s' % clase, request, "edit")
                    else:
                        clase = Clase(materia=miclase.materia,
                                      turno=turno,
                                      inicio=miclase.inicio,
                                      fin=miclase.fin,
                                      aula=miclase.aula,
                                      profesor=miclase.profesor,
                                      grupoprofesor=miclase.grupoprofesor,
                                      tipohorario=miclase.tipohorario,
                                      dia=dia,
                                      activo=True,
                                      tipoprofesor=miclase.tipoprofesor)
                        clase.save(request)
                    materia = clase.materia
                    materia.actualizarhtml = True
                    materia.save()
                    contar_sin_conflictos += 1
                    log(u'Adiciono clase por pegado: %s' % clase, request, "add")
                    idclase = encrypt(clase.id)
                    profesormateria = miclase.materia.profesormateria_segun_profe_tipoprofe(miclase.profesor, miclase.tipoprofesor.id)
                    if profesormateria.excedio_total_horario_en_dia(miclase.dia):
                        notificacion_excedio_hora = u'<b>EXCEDIÓ</b> el número de horas en el día el profesor <b>%s</b> teniendo un total de horas <b>%s/8</b> el día <b>%s</b>.' % (clase.profesor.persona.nombre_completo_inverso(), profesormateria.contar_horario_en_dia(miclase.dia), clase.get_dia_display())
                    if profesormateria.excedio_total_horario_materia_tipoprofesor():
                        notificacion_excedio_hora += u'%s el número de horas semanales el profesor <b>%s</b> teniendo un total de horas semanal <b>%s/%s</b> en la materia <b>%s</b>.' % ('<br/><b>Y excedió</b> ' if notificacion_excedio_hora else '<b>EXCEDIÓ</b> ', clase.profesor.persona.nombre_completo_inverso(), profesormateria.contar_horario_materia_tipoprofesor(), profesormateria.hora, clase.materia.nombre_mostrar_solo())
                else:
                    listamensajeconflicto.append(verificar_conflito_docente)
                    conflictohorario = True
                    contar_conflictos+=1
                if conflictohorario:
                    data = {}
                    data['mensajes'] = listamensajeconflicto
                    data['contarclasesconflicto'] = contar_conflictos.__str__()
                    data['clasesafectadas'] = contar_sin_conflictos.__str__()
                    template = get_template("niveles/mensajeconflicto.html")
                    json_content = template.render(data)
                # Para actualizar la opcion de subir enlace de la asignatura
                if materia:
                    materia.reajuste_horario_clase_seguida_subir_enlace()
                return JsonResponse({"result": "ok", 'existeconflicto':'ok' if conflictohorario else 'no', 'segmento':json_content, 'iddc': idclase, 'adicionado': 'ok' if idclase else 'no','notificar_excedio': True if notificacion_excedio_hora else False, 'notificacion_excedio_hora': notificacion_excedio_hora})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delclasepegar':
            try:
                clase = Clase.objects.get(pk=int(encrypt(request.POST['iddc'])))
                materia = clase.materia
                materia.actualizarhtml = True
                materia.save()
                log(u'Elimino horario despues del pegado: %s' % clase, request, "del")
                if not clase.tiene_lecciones():
                    clase.delete()
                else:
                    clase.activo = False
                    clase.save(request)
                # Para actualizar la opcion de subir enlace de la asignatura
                materia.reajuste_horario_clase_seguida_subir_enlace()
                return JsonResponse({"result": "ok", 'existeconflicto': 'no', 'adicionado': 'no'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'detallehorario':
            try:
                data['clases'] = clase = Clase.objects.filter(aula_id=request.POST['idaula'], materia__nivel__periodo=periodo).order_by('turno_id')
                data['semana'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sabado'], [7, 'Domingo']]
                template = get_template("adm_horarios/clases/detallehorario.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                pass


        elif action == 'delclase':
            try:
                clase = Clase.objects.get(pk=request.POST['id'])
                materia = clase.materia
                materia.actualizarhtml = True
                materia.save()
                log(u'Elimino horario: %s' % clase, request, "del")
                if not clase.tiene_lecciones():
                    clase.delete()
                else:
                    clase.activo = False
                    clase.save(request)
                log(u'deshabilito clase: %s' % clase, request, "del")
                # Para actualizar la opcion de subir enlace de la asignatura
                materia.reajuste_horario_clase_seguida_subir_enlace()
                return JsonResponse({"resp": True}, safe=False)
            except Exception as ex:
                return JsonResponse({"resp": False, "message": "Error: {}".format(ex)}, safe=False)

        elif action == 'hideclase':
            try:
                clase = Clase.objects.get(pk=request.POST['id'])
                materia = clase.materia
                materia.actualizarhtml = True
                materia.save()
                clase.activo = False
                clase.save(request)
                log(u'oculto clase: %s' % clase, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'listarprofesorayudante':
            try:
                clase = Clase.objects.get(pk=int(encrypt(request.POST['idc'])))
                profesoresmateria = clase.materia.profesores_materia_segun_excluir(clase.profesor.persona)
                listaprofesores = []
                for pm in profesoresmateria:
                    listaprofesores.append([pm.id, u'%s - %s - %s hrs.' % (pm.profesor.persona.nombre_completo_inverso().__str__(), pm.tipoprofesor.__str__(), pm.hora.__str__())])
                return JsonResponse({'result': 'ok', 'lista': listaprofesores})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

        elif action == 'listarleccionesfalso':
            try:
                clase = Clase.objects.get(pk=int(request.POST['idc']))
                lista_lecciones = []
                lecciones = clase.lista_leccion_falso()
                for l in lecciones:
                    lista_lecciones.append([f"{l.fecha.__str__()} - {l.clase.materia.asignatura.nombre} {l.clase.turno.__str__()} {l.clase.aula.__str__()}"])

                return JsonResponse({'result': 'ok', 'lecciones': lista_lecciones})
            except Exception as ex:
                pass



        elif action == 'addprofesorayudante':
            try:
                json_content = None
                contar_conflictos = 0
                conflictohorario = False
                contar_sin_conflictos = 0
                listamensajeconflicto = []
                idp = int(request.POST['idp'])
                clase = Clase.objects.get(pk=int(encrypt(request.POST['idc'])))
                if idp > 0:
                    pm = ProfesorMateria.objects.get(pk=idp)
                    verificar_conflito_docente = pm.profesor.existe_conflicto_docente(periodo, clase.materia, pm.tipoprofesor, clase.inicio, clase.fin, clase.dia, clase.turno, False, clase)
                    if not verificar_conflito_docente[0]:
                        clase.profesorayudante = pm.profesor
                        log(u'Edito profesor ayudante: %s - en la clase: %s - en el dia: %s [%s]' % (pm.profesor, clase, clase.get_dia_display(), clase.id), request, "edit")
                    else:
                        listamensajeconflicto.append(verificar_conflito_docente)
                        conflictohorario = True
                        contar_conflictos += 1
                else:
                    log(u'Elimino profesor ayudante: %s - en la clase: %s - en el dia: %s [%s]' % (clase.profesorayudante, clase, clase.get_dia_display(), clase.id), request, "del")
                    clase.profesorayudante = None
                clase.save(request)
                if conflictohorario:
                    data = {}
                    data['mensajes'] = listamensajeconflicto
                    data['contarclasesconflicto'] = contar_conflictos.__str__()
                    data['clasesafectadas'] = contar_sin_conflictos.__str__()
                    template = get_template("niveles/mensajeconflicto.html")
                    json_content = template.render(data)
                return JsonResponse({"result": "ok", 'existeconflicto':'ok' if conflictohorario else 'no', 'segmento':json_content, 'iddc': encrypt(clase.id)})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:

        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'mostrar':
                try:
                    turno = Turno.objects.get(pk=request.GET['idturno'])
                    if turno.mostrar :
                        turno.mostrar=False
                    else:
                        turno.mostrar = True
                    turno.save()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'horario':
                try:
                    data['title'] = u'Horarios de clases del periodo'
                    data['materiaid'] = None
                    data['materia'] = None
                    tienelink = False
                    data['semana'] = ['Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado', 'Domingo']
                    if MATRICULACION_LIBRE:
                        materia = Materia.objects.get(pk=request.GET['materiaid'])
                        if ClaseAsincronica.objects.filter(clase__materia=materia, status=True).exists():
                            tienelink = True
                        data['nivel'] = nivel = materia.nivel
                        data['activo'] = datetime.now().date() <= nivel.fin
                        if materia.asignaturamalla.malla.carrera.mi_coordinacion2() == 7:
                            data['turnos'] = turnos = nivel.sesion.turno_set.filter(status=True)
                        else:
                        #     data['turnos'] = turnos = nivel.sesion.turno_set.filter(mostrar=True, status=True)
                            data['turnos'] = turnos = Turno.objects.filter(mostrar=True, status=True)
                        data['turnos_fuera'] = Turno.objects.filter(pk__in=Clase.objects.values_list("turno_id", flat=True).filter(materia=materia,status=True).exclude(turno_id__in=turnos.values_list("id", flat=True).distinct()))
                        data['materia'] = materia = Materia.objects.get(pk=request.GET['materiaid'])
                        data['materiasfaltantes'] = None
                        data['materiaid'] = materia.id
                        data['carreraid'] = materia.asignaturamalla.malla.carrera_id

                        if materia.asignaturamalla.malla.carrera.mi_coordinacion2() == 7:
                            data['semanatutoria'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sábado']]
                            turnosparatutoria = None
                            profesormateria = ProfesorMateria.objects.get(status=True, materia=materia, materia__nivel__periodo=periodo,profesor=materia.profesor_principal())
                            # profesormateria = ProfesorMateria.objects.get(status=True, materia=materia, materia__periodo=periodo, profesor=materia.profesor_principal())
                            data['turnos'] = turnos = nivel.sesion.turno_set.filter(status=True)
                            if HorarioTutoriaAcademica.objects.filter(status=True, profesor=profesormateria.profesor, periodo=periodo, profesormateria=profesormateria).exists():
                                horarios = HorarioTutoriaAcademica.objects.filter(status=True, profesor=profesormateria.profesor, periodo=periodo)
                                data['suma'] = int(horarios.aggregate(total=Sum('turno__horas'))['total'])
                                idturnostutoria = horarios.values_list('turno_id').distinct()
                                turnosparatutoria = Turno.objects.filter(status=True, sesion_id__in=[19, 15], id__in=idturnostutoria).distinct().order_by('comienza')
                            data['turnostutoria'] = turnosparatutoria
                    else:
                        data['nivel'] = nivel = Nivel.objects.get(pk=request.GET['id'])
                        # data['turnos'] = nivel.sesion.turno_set.objects.filter(mostrar=True,status=True)
                        data['turnos'] = turnos = Turno.objects.filter(mostrar=True, status=True)
                        data['materiasfaltantes'] = nivel.materia_set.all()
                    data['horario_resumido'] = variable_valor('HORARIO_RESUMIDO')
                    data['verificar_conflicto_docente'] = variable_valor('VERIFICAR_CONFLICTO_DOCENTE')
                    data['matriculacion_libre'] = MATRICULACION_LIBRE
                    data['reporte_0'] = obtener_reporte('horario')
                    data['reporte_1'] = obtener_reporte('horario_carrera')
                    data['reporte_2'] = obtener_reporte('horario_carrera_nivel')
                    data['reporte_3'] = obtener_reporte('horario_materia')
                    data['bloqueado'] = nivel.bloqueado() and not persona.usuario.groups.filter(id__in=[143])
                    if materia.asignaturamalla.transversal:
                        tienelink=False
                    data['tienelink'] = tienelink
                    if 'nivelmallaid' in request.GET:
                        data['nivelmallaid'] = request.GET['nivelmallaid']
                    else:
                        data['nivelmallaid'] = 0
                    if 'paraleloid' in request.GET:
                        data['paraleloid'] = request.GET['paraleloid']
                    return render(request, "adm_horarios/clases/horario.html", data)
                except Exception as ex:
                    pass

            elif action == 'horariototal':
                try:
                    data['title'] = u'Horarios de clases del periodo'
                    data['mallaid'] = request.GET['mallaid']
                    data['mallanombre'] = malla = Malla.objects.get(pk=int(request.GET['mallaid']))
                    data['materiaid'] = None
                    data['materia'] = None
                    nivel = Nivel.objects.get(pk=request.GET['nivel'])
                    data['paraleloid'] = request.GET['paraleloid']
                    data['semana'] = ['Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado', 'Domingo']
                    if MATRICULACION_LIBRE:
                        # materia = Materia.objects.get(pk=request.GET['materiaid'])
                        data['nivel'] = nivel
                        data['activo'] = datetime.now().date() <= nivel.fin
                        # if malla.carrera.mi_coordinacion2() == 1:
                        #     data['turnos'] = nivel.sesion.turno_set.filter(status=True, mostrar=True)
                        # else:
                        #     data['turnos'] = nivel.sesion.turno_set.filter(status=True, mostrar=True)
                        data['turnos'] = turnos = Turno.objects.filter(mostrar=True, status=True)
                        # data['materia'] = materia = Materia.objects.get(pk=request.GET['materiaid'])
                        data['materiasfaltantes'] = None
                        # data['materiaid'] = materia.id
                        # data['carreraid'] = materia.asignaturamalla.malla.carrera_id
                    else:
                        data['nivel'] = nivel = Nivel.objects.get(pk=request.GET['id'])
                        # data['turnos'] = nivel.sesion.turno_set.filter(status=True, mostrar=True)
                        data['turnos'] = turnos = Turno.objects.filter(mostrar=True, status=True)
                        # data['materiasfaltantes'] = nivel.materia_set.all()
                    data['horario_resumido'] = variable_valor('HORARIO_RESUMIDO')
                    data['verificar_conflicto_docente'] = variable_valor('VERIFICAR_CONFLICTO_DOCENTE')
                    data['matriculacion_libre'] = MATRICULACION_LIBRE
                    data['reporte_0'] = obtener_reporte('horario')
                    data['reporte_1'] = obtener_reporte('horario_carrera')
                    data['reporte_2'] = obtener_reporte('horario_carrera_nivel')
                    data['reporte_3'] = obtener_reporte('horario_materia')
                    data['bloqueado'] = nivel.bloqueado() and not persona.usuario.groups.filter(id__in=[143])
                    data['form2'] = AulaForm()
                    if 'nivelmallaid' in request.GET:
                        data['nivelmallaid'] = request.GET['nivelmallaid']
                        data['nivelmalla'] = NivelMalla.objects.get(pk=int(request.GET['nivelmallaid']))
                    else:
                        data['nivelmallaid'] = 0
                    return render(request, "adm_horarios/clases/horariototal.html", data)
                except Exception as ex:
                    pass

            elif action == 'addclasetotal':
                try:
                    data['title'] = u'Adicionar materia a horario'
                    nivel = Nivel.objects.get(pk=request.GET['idn'])
                    data['mallaid'] = request.GET['idm']
                    data['paraleloid'] = request.GET['p']
                    data['nivelmallaid'] = request.GET['idnm']
                    data['nivel'] = nivel
                    form = ClaseForm(initial={'turno':Turno.objects.get(pk=int(request.GET['tid']), status=True), 'dia':int(request.GET['dia'])})
                    form.visible_profesor_adicionar(periodo)
                    form.adicionar_grupoprofesor(periodo)
                    form.fields['materia'].queryset= Materia.objects.filter(status=True, nivel_id=nivel.id, paralelo=request.GET['p'],asignaturamalla__nivelmalla__id=request.GET['idnm'],asignaturamalla__malla__id=request.GET['idm']).distinct()
                    form.fields['turno'].queryset = nivel.sesion.turnosactivos()
                    # form.adicionartotal()
                    if nivel.coordinacion().id == 1:
                        data['turnosactivos'] = 1
                    else:
                        data['turnosactivos'] = 2
                    data['form'] = form
                    return render(request, "adm_horarios/clases/addclasetotal.html", data)
                except Exception as ex:
                    pass

            elif action == 'addclase':
                try:
                    data['title'] = u'Adicionar materia a horario'
                    nivel = Nivel.objects.get(pk=request.GET['nivel'])
                    data['nivel'] = nivel
                    if 'materia' in request.GET:
                        materia = Materia.objects.get(pk=request.GET['materia'])
                        form = ClaseForm(initial={'materia': materia,
                                                  'inicio': materia.inicio,
                                                  'fin': materia.fin})
                    else:
                        materia = Materia.objects.get(pk=request.GET['materiaid'])
                        form = ClaseForm(initial={'turno': Turno.objects.get(pk=request.GET['turno']),
                                                  'dia': request.GET['dia'],
                                                  'inicio': materia.inicio,
                                                  'materia': materia,
                                                  'fin': materia.fin})
                    carrera = None
                    materia = None
                    if 'materiaid' in request.GET:
                        data['materiaid'] = request.GET['materiaid']
                        materia = Materia.objects.get(pk=int(request.GET['materiaid']))
                    if 'carreraid' in request.GET:
                        data['carreraid'] = request.GET['carreraid']
                        carrera = Carrera.objects.get(pk=int(request.GET['carreraid']))
                    if 'nivelmid' in request.GET:
                        data['nivelmid'] = request.GET['nivelmid']
                    if 'paraleloid' in request.GET:
                        data['paraleloid'] = request.GET['paraleloid']
                    form.adicionar(nivel, nivel.coordinacion(), carrera, materia)
                    form.visible_profesor_adicionar(periodo)
                    form.adicionar_grupoprofesor(periodo)
                    data['form'] = form
                    if nivel.coordinacion().id == 1:
                        data['turnosactivos'] = 1
                    else:
                        data['turnosactivos'] = 2
                    return render(request, "adm_horarios/clases/addclase.html", data)
                except Exception as ex:
                    pass

            elif action == 'editclase':
                try:
                    data['title'] = u'Editar clase de horario'
                    clase = Clase.objects.get(pk=request.GET['id'])
                    data['clase'] = clase
                    form = ClaseForm(initial={'materia': clase.materia,
                                              'turno': clase.turno,
                                              'aula': clase.aula,
                                              'inicio': clase.inicio,
                                              'tipoprofesor': clase.tipoprofesor,
                                              'profesor': clase.profesor,
                                              'grupoprofesor': clase.grupoprofesor,
                                              'tipohorario': clase.tipohorario,
                                              'fin': clase.fin,
                                              'dia': clase.dia})
                    form.cargar_profesores(clase, periodo)
                    profesormateria = None
                    if clase.profesor:
                        try:
                            profesormateria = clase.materia.profesormateria_segun_profe_tipoprofe(clase.profesor, clase.tipoprofesor.id)
                        except Exception as ex:
                            profesormateria = None
                    form.cargar_grupoprofesor(profesormateria, clase.tipoprofesor, periodo)
                    carrera = None
                    if 'materiaid' in request.GET:
                        data['materiaid'] = request.GET['materiaid']
                    if 'carreraid' in request.GET:
                        data['carreraid'] = request.GET['carreraid']
                        carrera = Carrera.objects.get(pk=int(request.GET['carreraid']))
                    if 'nivelmid' in request.GET:
                        data['nivelmid'] = request.GET['nivelmid']
                    if 'paraleloid' in request.GET:
                        data['paraleloid'] = request.GET['paraleloid']
                    form.editar(clase.materia.nivel, clase.materia.nivel.coordinacion(), clase.materia, carrera)
                    data['form'] = form
                    data['nivel'] = clase.materia.nivel
                    if clase.materia.nivel.coordinacion().id == 1:
                        return render(request, "adm_horarios/clases/editclaseturnosinactivos.html", data)
                    else:
                        return render(request, "adm_horarios/clases/editclase.html", data)
                except Exception as ex:
                    pass

            elif action == 'editclasetotal':
                try:
                    data['title'] = u'Editar clase de horario'
                    clase = Clase.objects.get(pk=request.GET['id'])
                    data['clase'] = clase
                    form = ClaseForm(initial={'materia': clase.materia,
                                              'turno': clase.turno,
                                              'aula': clase.aula,
                                              'inicio': clase.inicio,
                                              'tipoprofesor': clase.tipoprofesor,
                                              'profesor': clase.profesor,
                                              'grupoprofesor': clase.grupoprofesor,
                                              'tipohorario': clase.tipohorario,
                                              'fin': clase.fin,
                                              'dia': clase.dia})
                    carrera = None
                    if 'materiaid' in request.GET:
                        data['materiaid'] = request.GET['materiaid']
                    if 'carreraid' in request.GET:
                        data['carreraid'] = request.GET['carreraid']
                        carrera = Carrera.objects.get(pk=int(request.GET['carreraid']))
                    if 'nivelmid' in request.GET:
                        data['nivelmid'] = request.GET['nivelmid']
                    if 'paraleloid' in request.GET:
                        data['paraleloid'] = request.GET['paraleloid']
                    form.editar(clase.materia.nivel, clase.materia.nivel.coordinacion(), clase.materia, carrera)
                    form.cargar_profesores(clase, periodo)
                    form.cargar_grupoprofesor(clase.materia.profesormateria_segun_profe_tipoprofe(clase.profesor, clase.tipoprofesor.id) if clase.profesor else None, clase.tipoprofesor, periodo)
                    data['form'] = form
                    if clase.grupoprofesor:
                        data['grupoprofesorselect'] = clase.grupoprofesor.pk
                    data['nivel'] = clase.materia.nivel
                    return render(request, "adm_horarios/clases/editclasetotal.html", data)
                except Exception as ex:
                    pass

            elif action == 'clear':
                try:
                    nivel = Nivel.objects.get(pk=request.GET['id'])
                    data['nivel'] = nivel
                    data['materiaid'] = request.GET['materiaid']
                    data['mallaid'] = request.GET['mallaid']
                    data['nivelmallaid'] = request.GET['nivelmallaid']
                    if 'carreraid' in request.GET:
                        data['carreraid'] = request.GET['carreraid']
                    else:
                        data['carreraid'] = None
                    return render(request, "adm_horarios/clases/clear.html", data)
                except Exception as ex:
                    pass

            elif action == 'addclasehorario':
                try:
                    data['id_aula']=int(request.GET['id'])
                    form = ClaseHorarioForm()
                    # maestria = MaestriasAdmision.objects.values_list('carrera_id', flat=True)
                    # form.fields['carrera'].queryset = Carrera.objects.filter(status=True, coordinacion__id__in=[7, 13]).exclude(id__in=maestria)
                    data['form'] = form
                    # periodo = 76
                    # form.visible_profesor_adicionar(periodo)
                    # form.adicionar_grupoprofesor(periodo)
                    template = get_template("adm_horarios/clases/modal_addclasehorario.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'buscarmaterias':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    query = Materia.objects.filter(status=True, nivel__periodo=periodo).filter((Q(asignatura__nombre__icontains=q) | Q(identificacion__icontains=q) | Q(paralelo__icontains=q))).distinct()[:15]
                    data = {"result": "ok", "results": [{"id": x.id, "name": "{}".format(x.__str__())} for x in query]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass


            elif action == 'limpiarhorarioparalelo':
                try:
                    data['title'] = u'Eliminar clases'
                    data['nivel'] = Nivel.objects.get(pk=int(encrypt(request.GET['id'])))
                    mallaid = None
                    nivelmallaid = None
                    paraleloid = None
                    if 'mallaid' in request.GET:
                        mallaid = request.GET['mallaid']
                    data['mallaid'] = mallaid
                    if 'paraleloid' in request.GET:
                        paraleloid = request.GET['paraleloid']
                    data['paraleloid'] = paraleloid
                    if 'nivelmallaid' in request.GET:
                        nivelmallaid = request.GET['nivelmallaid']
                    data['nivelmallaid'] = nivelmallaid
                    return render(request, "adm_horarios/clases/limpiarhorarioparalelo.html", data)
                except Exception as ex:
                    pass

            if action == 'delclase':
                try:
                    data['title'] = u'Eliminar clase'
                    data['clase'] = Clase.objects.get(pk=request.GET['id'])
                    return render(request, 'adm_horarios/clases/delclase.html', data)
                except Exception as ex:
                    pass

            if action == 'hideclase':
                try:
                    data['title'] = u'Eliminar clase'
                    data['clase'] = Clase.objects.get(pk=request.GET['id'])
                    return render(request, 'adm_horarios/clases/hideclase.html', data)
                except Exception as ex:
                    pass

            if action == 'turnosaulas':
                try:
                    data['title'] = u'Turnos Disponibles'
                    data['aulaid']=int(request.GET['id'])
                    # data['clases'] = clase = Clase.objects.filter(aula_id=request.POST['idaula'],materia__nivel__periodo=periodo).order_by('turno_id')
                    # data['turno'] = Clase.objects.get(pk=request.GET['id'])
                    data['semana'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'],[6, 'Sabado'], [7, 'Domingo']]
                    data['sesionesturnos'] = sesion = Sesion.objects.filter(pk__in=[1, 4, 5, 7], status=True).distinct()
                    # data['turnos'] = Turno.objects.filter(status=True, sesion_id__in=[1, 4, 5, 7]).distinct()
                    data['turnos'] = Turno.objects.filter(status=True, sesion_id__in=[20]).distinct()
                    if 'sesion' in request.GET:
                        data['sesiones'] = sesion = Sesion.objects.get(pk=request.GET['sesion'])
                        # if Clase.objects.filter(aula=aula, turno__sesion__id=18, turno__mostrar=True).exists():
                        # data['turnos'] = sesion.turno_set.filter(mostrar=True, status=True)
                        data['turnos'] = turnos = Turno.objects.filter(mostrar=True, status=True)

                    return render(request, 'adm_horarios/clases/turnosaulas.html', data)
                except Exception as ex:
                    pass


            if action == 'aulasdisponibles':
                try:
                    data['title'] = u'Aulas Disponibles'
                    # data['aulaid']=int(request.GET['id'])
                    # data['clases'] = clase = Clase.objects.filter(aula_id=request.POST['idaula'],materia__nivel__periodo=periodo).order_by('turno_id')
                    # data['turno'] = Clase.objects.get(pk=request.GET['id'])
                    data['semana'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'],[6, 'Sabado'], [7, 'Domingo']]
                    data['sesionesturnos'] = sesion = Sesion.objects.filter(pk__in=[1, 4, 5, 7], status=True).distinct()
                    # data['turnos'] = Turno.objects.filter(status=True, sesion_id__in=[1, 4, 5, 7]).distinct()
                    if 'sesion' in request.GET:
                        data['sesiones'] = sesion = Sesion.objects.get(pk=request.GET['sesion'])
                        # if Clase.objects.filter(aula=aula, turno__sesion__id=18, turno__mostrar=True).exists():
                        # data['turnos'] = sesion.turno_set.filter(mostrar=True, status=True)

                    return render(request, 'adm_horarios/clases/aulasdisponibles.html', data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:

            try:
                data['title'] = u'Administración de horarios de clases del periodo'
                data['bloques'] = bloques = Bloque.objects.filter(status=True, tipo=1).order_by('pk')
                return render(request, "adm_horarios/clases/view.html", data)

            except Exception as ex:
                data['msg_error'] = ex.__str__()
                return render(request, "adm_horarios/error.html", data)
