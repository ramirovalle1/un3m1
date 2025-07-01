# -*- coding: latin-1 -*-
from datetime import datetime, timedelta
import xlrd as xlrd
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse
from django.db import transaction
from django.shortcuts import render
from decorators import secure_module, last_access
from settings import NOTA_ESTADO_EN_CURSO, TIPO_CUOTA_RUBRO, ARCHIVO_TIPO_GENERAL
from sga.commonviews import adduserdata, obtener_reporte
from django.template.loader import get_template
from django.template.context import Context
from django.contrib import messages
from sga.forms import CursoEscuelaForm, MateriasCursoEscuelaForm, PagoCursoEscuelaForm, ImportarArchivoXLSForm, MatricularCursoEscuelaComplementariaForm
from sga.funciones import MiPaginador, log, puede_realizar_accion, generar_nombre, validar_archivo
from sga.models import CursoEscuelaComplementaria, MatriculaCursoEscuelaComplementaria, Inscripcion, MateriaCursoEscuelaComplementaria, \
    PagosCursoEscuelaComplementaria, MateriaAsignadaCurso, Archivo, Persona


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'editar':
                try:
                    f = CursoEscuelaForm(request.POST, request.FILES)

                    if 'archivo' in request.FILES:
                        archivo = request.FILES['archivo']
                        descripcionarchivo = 'Archivo Soporte'

                        # Validar el archivo
                        resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                    if f.is_valid():
                        actividad = CursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                        actividad.nombre = f.cleaned_data['nombre']
                        actividad.tema = f.cleaned_data['tema']
                        if actividad.materiacursoescuelacomplementaria_set.exists():
                            inicio = actividad.materiacursoescuelacomplementaria_set.order_by('fecha_inicio')[0].fecha_inicio
                            fin = actividad.materiacursoescuelacomplementaria_set.order_by('-fecha_fin')[0].fecha_fin
                            if f.cleaned_data['fechainicio'] > inicio:
                                return JsonResponse({"result": "bad", "mensaje": u"La fecha de inicio debe coincidir con el rago de inicio de las materias."})
                            if f.cleaned_data['fechafin'] < fin:
                                return JsonResponse({"result": "bad", "mensaje": u"La fecha de fin debe coincidir con el rago de finalización de las materias."})
                        actividad.fecha_inicio = f.cleaned_data['fechainicio']
                        actividad.fecha_fin = f.cleaned_data['fechafin']
                        actividad.sesion = f.cleaned_data['sesion']
                        actividad.paralelo = f.cleaned_data['paralelo']
                        if f.cleaned_data['cupo'] < actividad.registrados():
                            actividad.cupo = actividad.registrados()
                        else:
                            actividad.cupo = f.cleaned_data['cupo']

                        if 'archivo' in request.FILES:
                            archivo = request.FILES['archivo']
                            archivo._name = generar_nombre("soporteremedial", archivo._name)
                            actividad.archivo = archivo

                        actividad.save(request)
                        log(u"Modifico curso: %s" % actividad, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    msg = ex.__str__()
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

            if action == 'add':
                try:
                    f = CursoEscuelaForm(request.POST, request.FILES)
                    if 'archivo' in request.FILES:
                        archivo = request.FILES['archivo']
                        descripcionarchivo = 'Archivo Soporte'

                        # Validar el archivo
                        resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                    if f.is_valid():
                        if f.cleaned_data['fechafin'] < f.cleaned_data['fechainicio']:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "Fechas incorrectas.", "showSwal": "True", "swalType": "warning"})

                        archivo = None
                        if 'archivo' in request.FILES:
                            archivo = request.FILES['archivo']
                            archivo._name = generar_nombre("soporteremedial", archivo._name)

                        actividad = CursoEscuelaComplementaria(nombre=f.cleaned_data['nombre'],
                                                               tema=f.cleaned_data['tema'],
                                                               fecha_inicio=f.cleaned_data['fechainicio'],
                                                               fecha_fin=f.cleaned_data['fechafin'],
                                                               sesion=f.cleaned_data['sesion'],
                                                               paralelo=f.cleaned_data['paralelo'],
                                                               cupo=f.cleaned_data['cupo'],
                                                               archivo=archivo)
                        actividad.save(request)
                        log(u"Adiciono curso: %s" % actividad, request, "add")
                        return JsonResponse({"result": "ok", "id": actividad.id})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    msg = ex.__str__()
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

            if action == 'addmateria':
                try:
                    curso = CursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                    form = MateriasCursoEscuelaForm(request.POST)
                    if form.is_valid():
                        materias = MateriaCursoEscuelaComplementaria(asignatura=form.cleaned_data['asignatura'],
                                                                     profesor=form.cleaned_data['profesor'],
                                                                     fecha_inicio=form.cleaned_data['fechainicio'],
                                                                     fecha_fin=form.cleaned_data['fechafin'],
                                                                     calificar=form.cleaned_data['calificar'],
                                                                     horas=form.cleaned_data['horas'],
                                                                     creditos=form.cleaned_data['creditos'],
                                                                     validacreditos=form.cleaned_data['validacreditos'],
                                                                     validapromedio=form.cleaned_data['validapromedio'],
                                                                     calfmaxima=form.cleaned_data['califmaxima'] if form.cleaned_data['calificar'] else 0,
                                                                     calfminima=form.cleaned_data['califminima'] if form.cleaned_data['calificar'] else 0,
                                                                     asistminima=form.cleaned_data['asistminima'],
                                                                     curso=curso)
                        materias.save(request)
                        for participante in curso.matriculacursoescuelacomplementaria_set.all():
                            materiaasignada = MateriaAsignadaCurso(inscripcion=participante,
                                                                   materia=materias,
                                                                   estado_id=NOTA_ESTADO_EN_CURSO)
                            materiaasignada.save(request)
                        log(u'Adiciono materia de curso: %s' % materias, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'eliminar':
                try:
                    actividad = CursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                    if actividad.registrados():
                        return JsonResponse({"result": "bad", "mensaje": u"Existen estudiantes registrados."})
                    log(u'Elimino curso: %s' % actividad, request, "del")
                    actividad.delete()
                    return JsonResponse({"result": "ok", "id": actividad.id})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            if action == 'addregistrocurso':
                try:
                    f = MatricularCursoEscuelaComplementariaForm(request.POST)
                    if f.is_valid():
                        curso = CursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                        idpersona = f.cleaned_data['registro']
                        registro = Persona.objects.get(pk=idpersona)
                        inscripcion = registro.inscripcion_principal()
                        if not MatriculaCursoEscuelaComplementaria.objects.filter(curso=curso, inscripcion=inscripcion).exists():
                            if curso.cupo:
                                registro = MatriculaCursoEscuelaComplementaria(curso=curso,
                                                                               inscripcion=inscripcion)
                                registro.save(request)
                                for materia in curso.materiacursoescuelacomplementaria_set.all():
                                    asignatura = MateriaAsignadaCurso(inscripcion=registro,
                                                                      materia=materia,
                                                                      calificacion=0,
                                                                      asistencia=0,
                                                                      estado_id=NOTA_ESTADO_EN_CURSO)
                                    asignatura.save(request)
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Se acabo el cupo del curso."})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Ya se encuentra Registrado."})
                        log(u"Adiciono curso: %s" % curso, request, "add")
                        messages.success(request, 'Se agregó registro exitosamente.')
                        return JsonResponse({"result": "ok", "id": curso.id})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'inscripcionmasiva':
                try:
                    form = ImportarArchivoXLSForm(request.POST, request.FILES)
                    if not 'archivo' in request.FILES or not request.FILES['archivo']:
                        raise NameError(u"Favor subir un archivo")
                    if form.is_valid():
                        hoy = datetime.now().date()
                        nfile = request.FILES['archivo']
                        nfile._name = generar_nombre("importacion_", nfile._name)
                        archivo = Archivo(nombre='IMPORTACION INSCRIPCIONES MASIVA CURSO',
                                          fecha=datetime.now().date(),
                                          archivo=nfile,
                                          tipo_id=ARCHIVO_TIPO_GENERAL)
                        archivo.save(request)
                        workbook = xlrd.open_workbook(archivo.archivo.file.name)
                        sheet = workbook.sheet_by_index(0)
                        curso = CursoEscuelaComplementaria.objects.get(pk=request.POST['idcurso'])
                        if not curso.registrados():
                            linea = 1
                            for rowx in range(sheet.nrows):
                                if linea > 1:
                                    cols = sheet.row_values(rowx)
                                    inscripcion = Inscripcion.objects.get(pk=int(cols[11]))
                                    if not MatriculaCursoEscuelaComplementaria.objects.filter(curso=curso,inscripcion=inscripcion).exists():
                                        if curso.cupo:
                                            registro = MatriculaCursoEscuelaComplementaria(curso=curso,
                                                                                           inscripcion=inscripcion)
                                            registro.save(request)
                                            for materia in curso.materiacursoescuelacomplementaria_set.all():
                                                asignatura = MateriaAsignadaCurso(inscripcion=registro,
                                                                                  materia=materia,
                                                                                  calificacion=0,
                                                                                  asistencia=0,
                                                                                  estado_id=NOTA_ESTADO_EN_CURSO)
                                                asignatura.save(request)
                                        else:
                                            return JsonResponse({"result": "bad", "mensaje": u"Se acabo el cupo del curso."})
                                linea += 1
                        else:
                            linea = 1
                            listainscripcionnew = []
                            for rowx in range(sheet.nrows):
                                if linea > 1:
                                    cols = sheet.row_values(rowx)
                                    inscripcion = Inscripcion.objects.get(pk=int(cols[11]))
                                    listainscripcionnew.append(inscripcion)
                                    if not MatriculaCursoEscuelaComplementaria.objects.filter(curso=curso, inscripcion=inscripcion).exists(): #si existe no lo agrega
                                        if curso.cupo:
                                            registro = MatriculaCursoEscuelaComplementaria(curso=curso,
                                                                                           inscripcion=inscripcion)
                                            registro.save(request)
                                            for materia in curso.materiacursoescuelacomplementaria_set.all():
                                                asignatura = MateriaAsignadaCurso(inscripcion=registro,
                                                                                  materia=materia,
                                                                                  calificacion=0,
                                                                                  asistencia=0,
                                                                                  estado_id=NOTA_ESTADO_EN_CURSO)
                                                asignatura.save(request)
                                        else:
                                            return JsonResponse({"result": "bad", "mensaje": u"Se acabo el cupo del curso."})
                                linea += 1
                            #elimiar registros que no estan en el nuevo masivo
                            registroborrar = MatriculaCursoEscuelaComplementaria.objects.filter(curso=curso).exclude(inscripcion__in=listainscripcionnew)
                            for reg in registroborrar:
                                for materia in curso.materiacursoescuelacomplementaria_set.all():
                                    asignatura = MateriaAsignadaCurso.objects.get(inscripcion=reg, materia=materia)
                                    asignatura.delete()
                                reg.delete()
                        log(u"Adiciono registro de curso de forma masiva: %s" % curso, request, "add")
                        messages.success(request, 'Se realizó masivo exitosamente.')
                        return JsonResponse({"result": "ok"})

                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos, archivo incorrecto. %s" % ex})

            if action == 'addcurso':
                try:
                    inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                    curso = CursoEscuelaComplementaria.objects.get(pk=request.POST['idc'])
                    if curso.cupo:
                        registro = MatriculaCursoEscuelaComplementaria(curso=curso,
                                                                       inscripcion=inscripcion)
                        registro.save(request)
                        for materia in curso.materiacursoescuelacomplementaria_set.all():
                            asignatura = MateriaAsignadaCurso(inscripcion=registro,
                                                              materia=materia,
                                                              estado_id=NOTA_ESTADO_EN_CURSO,
                                                              calificacion=0)
                            asignatura.save(request)
                        log(u"Adiciono registro de curso: %s" % registro, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'editmateria':
                try:
                    f = MateriasCursoEscuelaForm(request.POST)
                    if f.is_valid():
                        materia = MateriaCursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                        materia.asignatura = f.cleaned_data['asignatura']
                        materia.profesor = f.cleaned_data['profesor']
                        materia.fecha_inicio = f.cleaned_data['fechainicio']
                        materia.fecha_fin = f.cleaned_data['fechafin']
                        materia.calificar = f.cleaned_data['calificar']
                        materia.asistminima = f.cleaned_data['asistminima']
                        materia.horas = f.cleaned_data['horas']
                        materia.creditos = f.cleaned_data['creditos']
                        materia.validacreditos = f.cleaned_data['validacreditos']
                        materia.validapromedio = f.cleaned_data['validapromedio']
                        if f.cleaned_data['calificar']:
                            materia.calfmaxima = f.cleaned_data['califmaxima']
                            materia.calfminima = f.cleaned_data['califminima']
                        else:
                            materia.calfmaxima = 0
                            materia.calfminima = 0
                        materia.save(request)
                        for participante in materia.materiaasignadacurso_set.all():
                            participante.actualiza_estado()
                            participante.save(request)
                        log(u'Modifico materia de curso: %s' % materia, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'delmateria':
                try:
                    materia = MateriaCursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                    log(u'Elimino materia de curso: %s' % materia, request, "del")
                    materia.delete()
                    return JsonResponse({"result": "ok", "id": materia.id})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            if action == 'addpagos':
                try:
                    curso = CursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                    f = PagoCursoEscuelaForm(request.POST)
                    if f.is_valid():
                        if PagosCursoEscuelaComplementaria.objects.filter(curso=curso, tipo=f.cleaned_data['tipo'], cuota=f.cleaned_data['cuota']).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Ya existe ese tipo de pago registrado."})
                        pagocurso = PagosCursoEscuelaComplementaria(curso=curso,
                                                                    tipo=f.cleaned_data['tipo'],
                                                                    cuota=f.cleaned_data['cuota'],
                                                                    fecha=f.cleaned_data['fecha'],
                                                                    valor=f.cleaned_data['valor'])
                        pagocurso.save(request)
                        log(u"Adiciono pago de curso: %s" % pagocurso, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'editpagos':
                try:
                    pagocurso = PagosCursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                    f = PagoCursoEscuelaForm(request.POST)
                    if f.is_valid():
                        pagocurso.fecha = f.cleaned_data['fecha']
                        pagocurso.valor = f.cleaned_data['valor']
                        pagocurso.save(request)
                        log(u"Modifico pago de curso: %s" % pagocurso, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data = {}
        adduserdata(request, data)
        data['title'] = u'Cursos y escuelas complementarias'
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'eliminar':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_cursos')
                    data['title'] = u'Eliminar curso o escuela'
                    data['actividad'] = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cursoscomplementarios/eliminar.html", data)
                except Exception as ex:
                    pass

            if action == 'cerrar':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_cursos')
                    actividad = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    if actividad.permite_cerrar():
                        actividad.cerrado = True
                        actividad.save(request)
                    return HttpResponseRedirect('/adm_cursoscomplementarios')
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'abrir':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_cursos')
                    actividad = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    actividad.cerrado = False
                    actividad.save(request)
                    return HttpResponseRedirect('/adm_cursoscomplementarios')
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'cerrarmateria':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_cursos')
                    materia = MateriaCursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    materia.cerrada = True
                    materia.save(request)
                    for materiaasignada in materia.materiaasignadacurso_set.all():
                        materiaasignada.cierre_materia_asignada()
                    log(u"Cerro materia de curso: %s" % materia, request, "add")
                    return HttpResponseRedirect('/adm_cursoscomplementarios?action=materias&id=' + str(materia.curso.id))
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'abrirmateria':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_cursos')
                    materia = MateriaCursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    materia.cerrada = False
                    materia.save(request)
                    for materiaasignada in materia.materiaasignadacurso_set.all():
                        materiaasignada.actualiza_estado()
                    log(u"Abrio materia de curso: %s" % materia, request, "add")
                    return HttpResponseRedirect('/adm_cursoscomplementarios?action=materias&id=' + str(materia.curso.id))
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            elif action == 'editar':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_cursos')
                    data['title'] = u'Editar curso o escuela'
                    actividad = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    form = CursoEscuelaForm(initial={'nombre': actividad.nombre,
                                                     'tema': actividad.tema,
                                                     'fechainicio': actividad.fecha_inicio,
                                                     'fechafin': actividad.fecha_fin,
                                                     'sesion': actividad.sesion,
                                                     'paralelo': actividad.paralelo,
                                                     'cupo': actividad.cupo})
                    data['form'] = form
                    data['actividad'] = actividad
                    return render(request, "adm_cursoscomplementarios/editar.html", data)
                except Exception as ex:
                    pass

            elif action == 'add':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_cursos')
                    data['title'] = u'Adicionar curso o escuela'
                    data['form'] = CursoEscuelaForm(initial={'fechainicio': datetime.now().date(),
                                                             'fechafin': (datetime.now() + timedelta(days=30)).date(),
                                                             'cupo': 30})
                    return render(request, "adm_cursoscomplementarios/add.html", data)
                except Exception as ex:
                    pass

            elif action == 'registrados':
                try:
                    data['title'] = u'Registrados en curso o escuela'
                    data['actividad'] = actividad = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    data['registrados'] = actividad.matriculacursoescuelacomplementaria_set.all().order_by('inscripcion__persona')
                    data['reporte_0'] = obtener_reporte('certificado_extracurricular')
                    return render(request, "adm_cursoscomplementarios/registrados.html", data)
                except Exception as ex:
                    pass

            elif action == 'addregistrocurso':
                try:
                    data['title'] = u'Registrar en curso o escuela'
                    data['actividad'] = actividad = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    data['form'] = MatricularCursoEscuelaComplementariaForm()
                    return render(request, "adm_cursoscomplementarios/addregistrocurso.html", data)
                except Exception as ex:
                    pass

            elif action == 'registradosmaterias':
                try:
                    data['title'] = u'Materias en curso o escuela'
                    registrado = MatriculaCursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    materias = registrado.materiaasignadacurso_set.all()
                    data['registrado'] = registrado
                    data['materias'] = materias
                    return render(request, "adm_cursoscomplementarios/registradosmaterias.html", data)
                except Exception as ex:
                    pass

            elif action == 'cursos':
                try:
                    data['title'] = u'Registrar en cursos o escuela'
                    inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    cursos = CursoEscuelaComplementaria.objects.filter(fecha_fin__gte=datetime.now().date())
                    data['cursos'] = cursos
                    data['inscripcion'] = inscripcion
                    return render(request, "adm_cursoscomplementarios/cursos.html", data)
                except Exception as ex:
                    pass

            elif action == 'addcurso':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_cursos')
                    data['title'] = u'Registrar en curso o escuela'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    curso = CursoEscuelaComplementaria.objects.get(pk=request.GET['idc'])
                    data['curso'] = curso
                    return render(request, "adm_cursoscomplementarios/addcurso.html", data)
                except Exception as ex:
                    pass

            elif action == 'inscripcionmasiva':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_cursos')
                    data['title'] = u'Importar inscripciones cursos masivo'
                    data['form'] = ImportarArchivoXLSForm()
                    data['curso'] = CursoEscuelaComplementaria.objects.filter(pk=request.GET['idc'])[0]
                    data['mensaje'] = 'IMPORTANTE: Al realizar la inscripción masiva, se guardarán todos los registros del documento excel y se eliminarán aquellos que no se encuentren.'
                    return render(request, "adm_cursoscomplementarios/inscripcionmasiva.html", data)
                except Exception as ex:
                    pass

            elif action == 'retirar':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_cursos')
                    matricula = MatriculaCursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    curso = matricula.curso
                    log(u'Elimino registro de curso: %s' % matricula, request, "del")
                    matricula.delete()
                    return HttpResponseRedirect("/adm_cursoscomplementarios?action=registrados&id=" + str(curso.id))
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            elif action == 'materias':
                try:
                    data['title'] = u'Materias del curso o escuela'
                    data['curso'] = curso = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    data['materias'] = materias = curso.materiacursoescuelacomplementaria_set.all()
                    data['reporte_0'] = obtener_reporte('acta_calificacion_curso')
                    return render(request, "adm_cursoscomplementarios/materias.html", data)
                except Exception as ex:
                    pass

            elif action == 'addmateria':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_cursos')
                    data['title'] = u' Adicionar materias'
                    curso = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    form = MateriasCursoEscuelaForm(initial={'fechainicio': curso.fecha_inicio,
                                                             'fechafin': curso.fecha_fin})
                    data['form'] = form
                    data['curso'] = curso
                    return render(request, "adm_cursoscomplementarios/addmateria.html", data)
                except Exception as ex:
                    pass

            elif action == 'editmateria':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_cursos')
                    data['title'] = u'Editar materia'
                    materia = MateriaCursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    form = MateriasCursoEscuelaForm(initial={'asignatura': materia.asignatura,
                                                             'profesor': materia.profesor,
                                                             'fechainicio': materia.fecha_inicio,
                                                             'calificar': materia.calificar,
                                                             'califmaxima': materia.calfmaxima,
                                                             'califminima': materia.calfminima,
                                                             'asistminima': materia.asistminima,
                                                             'horas': materia.horas,
                                                             'creditos': materia.creditos,
                                                             'validacreditos': materia.validacreditos,
                                                             'validapromedio': materia.validapromedio,
                                                             'fechafin': materia.fecha_fin})
                    data['form'] = form
                    data['materia'] = materia
                    return render(request, "adm_cursoscomplementarios/editmateria.html", data)
                except Exception as ex:
                    pass

            if action == 'delmateria':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_cursos')
                    data['title'] = u'Eliminar materia'
                    data['materia'] = MateriaCursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cursoscomplementarios/delmateria.html", data)
                except Exception as ex:
                    pass

            if action == 'pagos':
                try:
                    data['title'] = u'Cronograma de pagos'
                    data['curso'] = curso = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    data['pagos'] = curso.pagoscursoescuelacomplementaria_set.all()
                    return render(request, "adm_cursoscomplementarios/pagos.html", data)
                except Exception as ex:
                    pass

            elif action == 'addpagos':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_pagos_curso')
                    data['title'] = u'Adicionar pago'
                    data['curso'] = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    data['form'] = PagoCursoEscuelaForm()
                    data['tipo_cuota_rubro'] = TIPO_CUOTA_RUBRO
                    return render(request, "adm_cursoscomplementarios/addpagos.html", data)
                except Exception as ex:
                    pass

            elif action == 'editpagos':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_pagos_curso')
                    data['title'] = u'Editar pago'
                    data['pagocurso'] = pagocurso = PagosCursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    form = PagoCursoEscuelaForm(initial={'tipo': pagocurso.tipo,
                                                         'cuota': pagocurso.cuota,
                                                         'fecha': pagocurso.fecha,
                                                         'valor': pagocurso.valor})
                    form.editar()
                    data['form'] = form
                    return render(request, "adm_cursoscomplementarios/editpagos.html", data)
                except Exception as ex:
                    pass

            elif action == 'delpagos':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_pagos_curso')
                    pagocurso = PagosCursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    curso = pagocurso.curso
                    log(u'Elimino pago de curso: %s' % pagocurso, request, "del")
                    pagocurso.delete()
                    return HttpResponseRedirect("/adm_cursoscomplementarios?action=pagos&id=" + str(curso.id))
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            return HttpResponseRedirect(request.path)
        else:
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
                actividades = CursoEscuelaComplementaria.objects.filter(nombre__icontains=search).distinct().order_by('-fecha_inicio')
            elif 'id' in request.GET:
                ids = request.GET['id']
                actividades = CursoEscuelaComplementaria.objects.filter(id=ids)
            else:
                actividades = CursoEscuelaComplementaria.objects.all().order_by('-id')
            paging = MiPaginador(actividades, 25)
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
            data['rangospaging'] = paging.rangos_paginado(p)
            data['page'] = page
            data['search'] = search if search else ""
            data['ids'] = ids if ids else ""
            data['actividades'] = page.object_list
            data['reporte_0'] = obtener_reporte("listado_estudiantes_curso")
            data['reporte_1'] = obtener_reporte("listado_estudiantes_curso_notas")
            return render(request, "adm_cursoscomplementarios/view.html", data)
