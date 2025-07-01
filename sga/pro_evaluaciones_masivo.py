# -*- coding: UTF-8 -*-
import csv
import json
import os
from datetime import datetime
from googletrans import Translator
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from settings import DATOS_ESTRICTO, PAGO_ESTRICTO, USA_EVALUACION_INTEGRAL, ARCHIVO_TIPO_NOTAS, SITE_ROOT
from sga.commonviews import adduserdata, actualizar_nota, obtener_reporte
from sga.forms import ImportarArchivoCSVForm
from sga.funciones import log, generar_nombre, variable_valor
from sga.models import Materia, MateriaAsignada, miinstitucion, LeccionGrupo, Archivo, PlanificacionMateria, \
    ProfesorReemplazo, PermisoPeriodo, CUENTAS_CORREOS
from sga.reportes import elimina_tildes
from sga.tasks import send_html_mail, conectar_cuenta


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
    profesor = perfilprincipal.profesor
    periodo = request.session['periodo']
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'cerrarmateriaasignada':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=request.POST['maid'])
                    materiaasignada.cerrado = (request.POST['cerrado'] == 'false')
                    materiaasignada.fechacierre = datetime.now().date()
                    materiaasignada.save(actualiza=True)
                    materiaasignada.actualiza_estado()
                    materiasabiertas = MateriaAsignada.objects.filter(materia=materiaasignada.materia, cerrado=False).count()
                    return JsonResponse({"result": "ok", 'cerrado': materiaasignada.cerrado, 'importadeuda': PAGO_ESTRICTO, 'tienedeuda': materiaasignada.matricula.inscripcion.persona.tiene_deuda(), 'materiasabiertas': materiasabiertas, "estadoid": materiaasignada.estado.id, "estado": materiaasignada.estado.nombre, "valida": materiaasignada.valida_pararecord()})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad"})

            elif action == 'cerrarmateria':
                try:
                    materia = Materia.objects.get(pk=request.POST['mid'])
                    materia.cerrado = True
                    materia.fechacierre = datetime.now().date()
                    materia.save(request)
                    for asig in materia.asignados_a_esta_materia():
                        asig.cierre_materia_asignada()
                    for lg in LeccionGrupo.objects.filter(lecciones__clase__materia=materia, abierta=True):
                        lg.abierta = False
                        lg.horasalida = lg.turno.termina
                        lg.save(request)
                    log(u'Cerro la materia: %s' % materia, request, "add")
                    send_html_mail("Cierre de materia", "emails/cierremateria.html", {'profesor': profesor, 'materia': materia, 't': miinstitucion()}, profesor.persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[4][1])
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad"})

            elif action == 'abrirmateria':
                try:
                    materia = Materia.objects.get(pk=request.POST['mid'])
                    materia.cerrado = False
                    materia.save(request)
                    send_html_mail("Apertura de materia", "emails/aperturamateria.html", {'sistema': request.session['nombresistema'], 'profesor': profesor, 'materia': materia, 'apertura': datetime.now(), 't': miinstitucion()}, profesor.persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[4][1])
                    log(u'Abrio la materia: %s' % materia, request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad"})

            elif action == 'nota':
                try:
                    datos = json.loads(request.POST['datos'])
                    result = {}
                    for d in datos:
                        materiaasignada = MateriaAsignada.objects.get(pk=d['maid'])
                        modeloevaluativo = materiaasignada.materia.modeloevaluativo
                        campomodelo = modeloevaluativo.campo(d['sel'])
                        valor = round(float(d['valor']), campomodelo.decimales)
                        result = actualizar_nota(request, materiaasignada=materiaasignada, sel=d['sel'], valor=valor)
                    return JsonResponse(result)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'envioclave':
                try:
                    clave = profesor.generar_clave_notas()
                    datos = profesor.datos_habilitacion()
                    datos.habilitado = False
                    datos.clavegenerada = clave
                    datos.fecha = datetime.now().date()
                    datos.save(request)
                    send_html_mail("Nueva clave para ingreso de calificaciones", "emails/nuevaclavecalificaciones.html", {'sistema': request.session['nombresistema'], 'profesor': profesor, 'clave': datos.clavegenerada, 'fecha': datos.fecha, 't': miinstitucion()}, profesor.persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[0][1])
                    return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'verificacionclave':
                try:
                    clave = request.POST['clave']
                    datos = profesor.datos_habilitacion()
                    if datos.clavegenerada == clave and datos.fecha == datetime.now().date():
                        datos.habilitado = True
                        datos.save(request)
                        log(u'Editó datos del profesor: %s' % datos, request, "edit")
                        return JsonResponse({'result': 'ok'})
                    else:
                        return JsonResponse({'result': 'bad', 'mensaje': u'Clave incorrecta'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'actualizarestado':
                try:
                    materia = Materia.objects.get(pk=request.POST['mid'])
                    for materiaasignada in materia.asignados_a_esta_materia():
                        materiaasignada.actualiza_estado()
                    return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'exportar':
                try:
                    materia = Materia.objects.get(pk=request.POST['id'])
                    output_folder = os.path.join(os.path.join(SITE_ROOT, 'media', 'notas'))
                    try:
                        os.makedirs(output_folder)
                    except Exception as ex:
                        pass
                    nombre = 'NOTAS_' + elimina_tildes(materia.identificacion).replace(' ', '') + "_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".csv"
                    filename = os.path.join(output_folder, nombre)
                    with open(filename, 'wb') as fichero:
                        cabecera = elimina_tildes(materia.nombre_completo()) + '\r\n\r\n'
                        fichero.write(cabecera)
                        cabecera = "COD;CEDULA;ESTUDIANTE;"
                        for campo in materia.modeloevaluativo.detallemodeloevaluativo_set.filter(dependiente=False).order_by('orden'):
                            cabecera += campo.nombre + ";"
                        cabecera += '\r\n'
                        fichero.write(cabecera)
                        for materiaasignada in materia.asignados_a_esta_materia():
                            persona = materiaasignada.matricula.inscripcion.persona
                            filanotas = str(materiaasignada.id) + ";" + persona.cedula + ";" + persona.nombre_completo_inverso().encode("ascii", "ignore") + ';'
                            for campo in materiaasignada.evaluacion().filter(detallemodeloevaluativo__dependiente=False).order_by('detallemodeloevaluativo__orden'):
                                filanotas += str(campo.valor) + ";"
                            filanotas += '\r\n'
                            fichero.write(filanotas)
                    fichero.close()
                    return JsonResponse({'result': 'ok', 'archivo': nombre})
                except Exception as ex:
                    translator = Translator()
                    return JsonResponse({"result": "bad", "mensaje": translator.translate(ex.__str__(),'es').text})

            elif action == 'importar':
                try:
                    form = ImportarArchivoCSVForm(request.POST, request.FILES)
                    materia = Materia.objects.get(pk=request.POST['id'])
                    if form.is_valid():
                        nfile = request.FILES['archivo']
                        nfile._name = generar_nombre("importacionnotas_", nfile._name)
                        archivo = Archivo(nombre='IMPORTACION_NOTAS',
                                          fecha=datetime.now().date(),
                                          archivo=nfile,
                                          tipo_id=ARCHIVO_TIPO_NOTAS)
                        archivo.save(request)
                        datareader = csv.reader(open(archivo.archivo.file.name, "rU"), delimiter=';')
                        linea = 1
                        hoy = datetime.now().date()
                        for row in datareader:
                            if linea > 3:
                                if not materia.materiaasignada_set.filter(id=int(row[0])).exists():
                                    transaction.set_rollback(True)
                                    return JsonResponse({"result": "bad", "mensaje": u"El codigo %s no existe como estudiante de esta materia." % row[0]})
                                materiaasignada = materia.materiaasignada_set.filter(id=int(row[0]))[0]
                                numero_campo = 3
                                for campo in materiaasignada.evaluacion().filter(detallemodeloevaluativo__dependiente=False):
                                    try:
                                        valor = float(row[numero_campo])
                                    except:
                                        valor = 0
                                    cronograma = materiaasignada.materia.cronogramacalificaciones()
                                    if cronograma:
                                        permite = campo.detallemodeloevaluativo.permite_ingreso_nota(materiaasignada, cronograma)
                                        if permite:
                                            result = actualizar_nota(request, materiaasignada=materiaasignada, sel=campo.detallemodeloevaluativo.nombre, valor=valor)
                                    numero_campo += 1
                            linea += 1
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'observaciones':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=request.POST['id'])
                    materiaasignada.observaciones = request.POST['observacion']
                    materiaasignada.save(request)
                    return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'segmento':
                try:
                    data['materia'] = materia = Materia.objects.get(pk=request.GET['id'])
                    data['cronograma'] = materia.cronogramacalificaciones()
                    data['usacronograma'] = materia.usaperiodocalificaciones
                    data['usa_evaluacion_integral'] = USA_EVALUACION_INTEGRAL
                    data['validardeuda'] = PAGO_ESTRICTO
                    data['incluyedatos'] = DATOS_ESTRICTO
                    data['dentro_fechas'] = materia.fin >= datetime.now().date()
                    data['auditor'] = False
                    data['reporte_0'] = obtener_reporte('acta_notas')
                    data['reporte_1'] = obtener_reporte('lista_control_calificaciones')
                    data['reporte_2'] = obtener_reporte('acta_notas_parcial')
                    bandera = False
                    if PlanificacionMateria.objects.filter(materia=materia, paraevaluacion=True).exists():
                        bandera = True
                    data['bandera'] = bandera
                    return render(request, "pro_evaluaciones_masivo/segmento.html", data)
                except Exception as ex:
                    pass

            if action == 'importar':
                try:
                    data['title'] = u'Importar notas'
                    data['form'] = ImportarArchivoCSVForm()
                    data['materia'] = Materia.objects.get(pk=request.GET['id'])
                    return render(request, "pro_evaluaciones_masivo/importar.html", data)
                except Exception as ex:
                    pass

            if action == 'cierretodasma':
                try:
                    data['materia'] = materia = Materia.objects.get(pk=request.GET['materiaid'])
                    for materiaasignada in materia.materiaasignada_set.all():
                        materiaasignada.cerrado = True
                        materiaasignada.fechacierre = datetime.now().date()
                        materiaasignada.save(actualiza=True)
                        materiaasignada.actualiza_estado()
                    return HttpResponseRedirect("/pro_evaluaciones_masivo?materiaid=" + request.GET['materiaid'])
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Evaluaciones de alumnos'
            hoy = datetime.now().date()
            if PermisoPeriodo.objects.filter(periodo=periodo).exists():
                data['permiso'] = True
            else:
                return HttpResponseRedirect("/?info=No tiene materias en el periodo seleccionado.")
            materias = Materia.objects.filter(status=True, profesormateria__profesor=profesor, profesormateria__principal=True, profesormateria__activo=True, nivel__periodo=periodo)
            otrasmaterias = []
            if profesor.reemplaza_set.filter(desde__lte=hoy, hasta__gte=hoy).exists():
                # solicita = profesor.reemplaza_set.filter(desde__lte=hoy, hasta__gte=hoy)[0].solicita
                solicita = ProfesorReemplazo.objects.values('solicita_id').filter(desde__lte=hoy, hasta__gte=hoy, reemplaza=profesor)
                otrasmaterias = Materia.objects.filter(status=True, profesormateria__profesor__in=solicita, profesormateria__principal=True, profesormateria__activo=True, nivel__periodo=periodo)
            if otrasmaterias:
                if materias:
                    data['materias'] = materias | otrasmaterias
                else:
                    data['materias'] = materias = otrasmaterias
            else:
                data['materias'] = materias
                if not materias:
                    return HttpResponseRedirect("/?info=No tiene materias en el periodo seleccionado.")
            if 'materiaid' not in request.GET:
                data['materiaid'] = materias[0].id
            else:
                data['materiaid'] = int(request.GET['materiaid'])
            data['materia'] = materia = Materia.objects.get(pk=data['materiaid'])
            data['utiliza_validacion_calificaciones'] = variable_valor('UTILIZA_VALIDACION_CALIFICACIONES')
            data['habilitado_ingreso_calificaciones'] = profesor.habilitado_ingreso_calificaciones()
            data['profesor'] = profesor
            return render(request, "pro_evaluaciones_masivo/view.html", data)