# -*- coding: latin-1 -*-
import json
import os
import sys
from datetime import datetime
import code128
import pyqrcode
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.defaultfilters import floatformat
from mobi.decorators import detect_mobile

from bd.models import UserToken
from decorators import secure_module, last_access
from matricula.funciones import valid_intro_module_estudiante, get_nivel_matriculacion, \
    puede_matricularse_seguncronograma_coordinacion, puede_matricularse_seguncronograma_carrera, \
    get_horarios_clases_informacion, get_horarios_clases_data, get_practicas_data, to_unicode, \
    get_horarios_practicas_informacion, get_horarios_practicas_data, valida_conflicto_materias_estudiante, \
    valida_conflicto_materias_estudiante_enroll, TIPO_PROFESOR_PRACTICA, agregacion_aux_pregrado, \
    get_tipo_matricula, calcula_nivel, generateCodeRemoveMateria, reenvioCodeRemoveMateria, \
    generateCodeDeleteMatricula, reenvioCodeDeleteMatricula, get_client_ip, ubicar_nivel_matricula, \
    action_enroll_pregrado
from matricula.models import PeriodoMatricula
from sagest.models import Rubro
from settings import SITE_STORAGE, NIVEL_MALLA_CERO, NOTA_ESTADO_EN_CURSO, NOTIFICA_ELIMINACION_MATERIA, \
    FINANCIERO_GROUP_ID, SECRETARIA_GROUP_ID, HOMITIRCAPACIDADHORARIO, NIVEL_MALLA_UNO, RUBRO_ARANCEL, RUBRO_MATRICULA
from sga.commonviews import adduserdata, obtener_reporte
from sga.funciones import null_to_decimal, log, tituloinstitucion, lista_correo, variable_valor
from sga.models import Matricula, Inscripcion, Nivel, ConfirmarMatricula, Materia, AlumnosPracticaMateria, \
    ProfesorMateria, GruposProfesorMateria, MateriaAsignada, AgregacionEliminacionMaterias, AuditoriaMatricula, \
    CUENTAS_CORREOS, NivelMalla
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsavecertificados
from django.db import connections, transaction

from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt

unicode = str
EJE_FORMATIVO_PRACTICAS = 9
EJE_FORMATIVO_VINCULACION = 11
EXCLUDE_EJE_FORMATIVO = [EJE_FORMATIVO_PRACTICAS, EJE_FORMATIVO_VINCULACION]

@login_required(redirect_field_name='ret', login_url='/loginsga')
@last_access
@transaction.atomic()
@detect_mobile
def view_matriculacion_pregrado(request):
    if request.method == 'POST':
        action = request.POST['action']
        persona = request.session['persona']
        perfilprincipal = request.session['perfilprincipal']
        periodo = request.session['periodo']
        inscripcion = perfilprincipal.inscripcion
        hoy = datetime.now().date()

        if action == 'loadInitialData':
            try:
                nivel_id = int(request.POST['nivel_id']) if 'nivel_id' in request.POST and request.POST['nivel_id'] else None
                if not Nivel.objects.values('id').filter(pk=nivel_id).exists():
                    raise NameError(u"Nivel no existe")
                nivel = Nivel.objects.get(pk=nivel_id)
                periodomatricula = None
                if nivel.periodo.periodomatricula_set.values('id').filter(status=True).exists():
                    periodomatricula = nivel.periodo.periodomatricula_set.filter()[0]
                if not periodomatricula:
                    raise NameError(u"Periodo académico no existe")
                inscripcion_malla = inscripcion.malla_inscripcion()
                asignaturas_malla = inscripcion_malla.malla.asignaturamalla_set.select_related().all().exclude((Q(nivelmalla_id=NIVEL_MALLA_CERO) | Q(opcional=True) | Q(ejeformativo_id__in=EXCLUDE_EJE_FORMATIVO))).order_by('nivelmalla', 'ejeformativo')
                va_ultima_matricula = inscripcion.va_ultima_matricula(periodomatricula.num_matriculas)
                num_va_ultima_matricula = inscripcion.num_va_ultima_matricula(periodomatricula.num_matriculas)
                aData = []
                for am in asignaturas_malla:
                    puedetomar = inscripcion.puede_tomar_materia(am.asignatura)
                    estado = inscripcion.estado_asignatura(am.asignatura)
                    totalmatriculaasignatura = inscripcion.total_record_asignaturatodo(am.asignatura)
                    if not estado in [1, 2]:
                        if inscripcion.itinerario:
                            if am.itinerario:
                                if inscripcion.itinerario == am.itinerario:
                                    estado = 3
                                else:
                                    estado = 0
                            else:
                                estado = 3
                        else:
                            estado = 3

                    materias = []
                    puede_ver_horario = 0
                    """PERMITE QUE UNICAMENTE PUEDAN SELECCIONAR SOLO MATERIAS DE ULTIMA MATRICULA"""
                    if va_ultima_matricula and num_va_ultima_matricula >= periodomatricula.num_materias_maxima_ultima_matricula and puedetomar and estado in [2, 3] and totalmatriculaasignatura != (periodomatricula.num_matriculas - 1):
                        puedetomar = False

                    if puedetomar and estado in [2, 3] and totalmatriculaasignatura < periodomatricula.num_matriculas:
                        materiasabiertas = Materia.objects.filter(Q(asignatura=am.asignatura, inicio__gte=hoy, nivel__cerrado=False, nivel__periodo=nivel.periodo), status=True).order_by('id')
                        if periodomatricula and periodomatricula.valida_materia_carrera:
                            materiasabiertas = materiasabiertas.filter(asignaturamalla__malla=inscripcion.mi_malla()).distinct().order_by('id')
                        if periodomatricula and periodomatricula.valida_seccion and not va_ultima_matricula:
                            materiasabiertas = materiasabiertas.filter(nivel__sesion=inscripcion.sesion).distinct().order_by('id')
                        if materiasabiertas.count() > 0:
                            puede_ver_horario = 1
                        for m in materiasabiertas:
                            puede_agregar = False
                            if m.nivel.nivellibrecoordinacion_set.exists():
                                coordinacion = m.nivel.nivellibrecoordinacion_set.all()[0].coordinacion.nombre
                            else:
                                coordinacion = m.nivel.carrera.nombre
                            horarios_verbose = []
                            horarios = []
                            if periodomatricula.ver_horario_materia:
                                horarios_verbose = get_horarios_clases_informacion(m)
                            if periodomatricula.valida_conflicto_horario:
                                horarios = get_horarios_clases_data(m)
                            mispracticas = get_practicas_data(m)
                            if m.nivel.puede_agregar_materia_matricula():
                                puede_agregar = True
                            materias.append({"id": m.id,
                                             "asignatura": m.asignatura.nombre,
                                             "nivelmalla": to_unicode(m.asignaturamalla.nivelmalla.nombre) if m.asignaturamalla.nivelmalla else "",
                                             "nivelmalla_id": m.asignaturamalla.nivelmalla.id if m.asignaturamalla.nivelmalla else 0,
                                             'sede': to_unicode(m.nivel.sede.nombre) if m.nivel.sede else "",
                                             "carrera": to_unicode(m.asignaturamalla.malla.carrera.nombre_completo()) if m.asignaturamalla.malla.carrera.nombre else "",
                                             "coordinacion": coordinacion,
                                             "paralelo": m.paralelomateria.nombre,
                                             "paralelo_id": m.paralelomateria.id,
                                             "profesor": (m.profesor_principal().persona.nombre_completo()) if m.profesor_principal() else 'SIN DEFINIR',
                                             'inicio': m.inicio.strftime("%d-%m-%Y"),
                                             'fin': m.fin.strftime("%d-%m-%Y"),
                                             'session': to_unicode(m.nivel.sesion.nombre),
                                             'identificacion': m.identificacion,
                                             "tipomateria": m.tipomateria,
                                             "tipomateria_display": m.get_tipomateria_display(),
                                             "teoriapractica": 1 if m.asignaturamalla.practicas else 0,
                                             "cupos": m.cupo if periodomatricula and periodomatricula.valida_cupo_materia else 0,
                                             "disponibles": m.capacidad_disponible() if periodomatricula and periodomatricula.valida_cupo_materia else 0,
                                             "horarios_verbose": horarios_verbose,
                                             "horarios": horarios,
                                             "mispracticas": mispracticas,
                                             "puede_agregar": puede_agregar,
                                             })
                    if am.itinerario > 0:
                        itinerario_verbose = f"ITINERARIO {am.itinerario}"
                    else:
                        itinerario_verbose = ''
                    predecesoras_verbose = ' , '.join((p.predecesora.asignatura.nombre for p in am.lista_predecesoras()))
                    aData.append({"id": am.id,
                                  "asignatura": am.asignatura.nombre,
                                  "nivelmalla_id": am.nivelmalla.id,
                                  "nivelmalla": am.nivelmalla.nombre,
                                  "ejeformativo": am.ejeformativo.nombre,
                                  "estado": estado,
                                  "creditos": am.creditos,
                                  "itinerario": am.itinerario,
                                  "itinerario_verbose": itinerario_verbose,
                                  "horas": am.horas,
                                  "horas_semanal": am.horastotal(),
                                  "horas_contacto_docente": am.horasacdsemanal,
                                  "cantidad_predecesoras": am.cantidad_predecesoras(),
                                  "totalrecordasignatura": totalmatriculaasignatura,
                                  "va_num_matricula": totalmatriculaasignatura + 1,
                                  "predecesoras": predecesoras_verbose,
                                  "materias": materias,
                                  "puede_ver_horario": puede_ver_horario
                                  })
                return JsonResponse({"result": "ok", "aData": aData})
            except Exception as ex:
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error. %s" % ex})

        elif action == 'locateEnrollmentLevel':
            try:
                mismaterias = json.loads(request.POST['mismaterias'])
                res = ubicar_nivel_matricula(mismaterias)
                aData = {}
                if res:
                    if NivelMalla.objects.values('id').filter(pk=res).exists():
                        nivelmalla = NivelMalla.objects.get(pk=res)
                    else:
                        nivelmalla = NivelMalla.objects.get(pk=NIVEL_MALLA_UNO)
                    aData['id'] = nivelmalla.id
                    aData['nombre'] = nivelmalla.nombre
                return JsonResponse({"result": "ok", "aData": aData})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error. %s" % ex})

        elif action == 'loadCupoMateria':
            try:
                if not 'asignatura' in request.POST:
                    raise NameError(u"Parametro no valido")
                asignatura = json.loads(request.POST['asignatura'])
                if not asignatura:
                    raise NameError(u"Parametro no valido")
                materias = []
                for m in asignatura['materias']:
                    disponibles = 0
                    for key, value in m.items():
                        if 'id' == key:
                            materia = Materia.objects.get(pk=int(m['id']))
                            disponibles = materia.capacidad_disponible()
                    m['disponibles'] = disponibles
                    materias.append(m)
                asignatura['materias'] = materias
                return JsonResponse({"result": "ok", 'asignatura': asignatura})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error. %s" % ex})

        elif action == 'loadCupoPractica':
            try:
                if not 'materia' in request.POST:
                    raise NameError(u"Parametro no valido")
                materia = json.loads(request.POST['materia'])
                if not materia:
                    raise NameError(u"Parametro no valido")
                practicas = []
                for p in materia['mispracticas']:
                    disponibles = 0
                    for key, value in p.items():
                        if 'id' == key:
                            grupo = GruposProfesorMateria.objects.get(pk=int(p['id']))
                            disponibles = grupo.cuposdisponiblesgrupoprofesor()
                    p['disponibles'] = disponibles
                    practicas.append(p)

                materia['mispracticas'] = practicas

                return JsonResponse({"result": "ok", 'materia': materia})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error. %s" % ex})

        elif action == 'validConflictoHorario':
            try:
                if not 'materias' in request.POST:
                    raise NameError(u"Parametro de materias seleccionadas no valido")
                mis_materias = json.loads(request.POST['materias'])
                if not 'materia' in request.POST:
                    raise NameError(u"Parametro de materia seleccionada no valido")
                mi_materia = json.loads(request.POST['materia'])
                mis_clases = []
                mi_clase = []
                for materia in mis_materias:
                    if materia['practica'] and len(materia['practica']['horarios']) > 0:
                        mis_clases.append(materia['practica']['horarios'])
                    if materia['horarios'] and len(materia['horarios']) > 0:
                        mis_clases.append(materia['horarios'])
                if mi_materia['practica'] and len(mi_materia['practica']) > 0:
                    mi_clase.append(mi_materia['practica']['horarios'])
                if mi_materia['horarios'] and len(mi_materia['horarios']) > 0:
                    mi_clase.append(mi_materia['horarios'])
                tiene_conflicto, mensaje = valida_conflicto_materias_estudiante(mis_clases, mi_clase)
                return JsonResponse({"result": "ok", "conflicto": tiene_conflicto, "mensaje": mensaje})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error. %s" % ex})

        elif action == 'enroll':
            try:
                nivel_id = int(request.POST['nivel_id']) if 'nivel_id' in request.POST and request.POST[
                    'nivel_id'] else None
                if not Nivel.objects.values('id').filter(pk=nivel_id).exists():
                    raise NameError(u"Nivel no existe")
                nivel = Nivel.objects.get(pk=nivel_id)
                periodomatricula = None
                if nivel.periodo.periodomatricula_set.values('id').filter(status=True).exists():
                    periodomatricula = nivel.periodo.periodomatricula_set.filter()[0]
                if not periodomatricula:
                    raise NameError(u"Periodo académico no existe")
                if periodomatricula.valida_terminos:
                    if not 'acept_t' in request.POST or int(request.POST['acept_t']) != 1:
                        raise NameError(u"Para continuar, favor acepte los terminos y condiciones")
                if not 'materias' in request.POST:
                    raise NameError(u"Parametro de materias seleccionadas no valido")
                mis_clases = json.loads(request.POST['materias'])
                if not 'cobro' in request.POST:
                    raise NameError(u"Parametro de cobro no valido")
                cobro = int(request.POST['cobro'])
                valid, msg, aData = action_enroll_pregrado(request, inscripcion, periodomatricula, nivel, mis_clases, cobro)
                return JsonResponse({"result": "ok" if valid else "bad", "mensaje": u"Ocurrio un error en la matriculación. <br> %s" % msg, "aData": aData})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error en la matriculación. <br> %s" % ex})

        elif action == 'to_differ':
            try:
                idm = int(request.POST['idm'])

                matricula = Matricula.objects.get(pk=idm)
                periodomatricula = None
                if PeriodoMatricula.objects.values('id').filter(status=True, activo=True, periodo=matricula.nivel.periodo).exists():
                    periodomatricula = PeriodoMatricula.objects.get(status=True, activo=True, periodo=matricula.nivel.periodo)

                if not periodomatricula:
                    raise NameError(u"No se permite diferir arancel")
                if periodomatricula.valida_cuotas_rubro and periodomatricula.num_cuotas_rubro <= 0:
                    raise NameError(u"Periodo acádemico no permite diferir arancel")
                if not periodomatricula.tiene_fecha_cuotas_rubro():
                    raise NameError(u"Periodo acádemico no permite diferir arancel")

                if matricula.aranceldiferido == 1:
                    raise NameError(u"El rubro arancel ya ha sido diferido. Verifique módulo Mis Finanzas")

                if not Rubro.objects.values('id').filter(matricula=matricula, tipo_id=RUBRO_ARANCEL).exists():
                    raise NameError(u"No se puede procesar el registro.")

                arancel = Rubro.objects.get(matricula=matricula, tipo_id=RUBRO_ARANCEL)
                nombrearancel = arancel.nombre
                valorarancel = Decimal(arancel.valortotal).quantize(Decimal('.01'))
                num_cuotas = periodomatricula.num_cuotas_rubro
                try:
                    valor_cuota_mensual = (valorarancel / num_cuotas).quantize(Decimal('.01'))
                except ZeroDivisionError:
                    valor_cuota_mensual = 0
                if valor_cuota_mensual == 0:
                    raise NameError(u"No se puede procesar el registro.")

                # c1 = (valorarancel/3).quantize(Decimal('.01'))
                # c2 = c1
                # c3 = valorarancel - (c1 + c2)

                # rubromatricula = Rubro.objects.get(matricula=matricula, tipo_id=RUBRO_MATRICULA)
                rubromatricula = Rubro.objects.filter(matricula=matricula, tipo_id=RUBRO_MATRICULA).exclude(relacionados__isnull=True)[0]
                rubromatricula.relacionados = None
                rubromatricula.save(request)
                lista = []
                # fechas = periodomatricula.fecha_cuotas_rubro().values('fecha').distinct()
                # lista = [[1, c1, fechas[0]],
                #          [2, c2, fechas[1]],
                #          [3, c3, fechas[2]]]
                c = 0
                for r in periodomatricula.fecha_cuotas_rubro().values('fecha').distinct():
                    c += 1
                    lista.append([c, valor_cuota_mensual, r['fecha']])

                for item in lista:
                    rubro = Rubro(tipo_id=RUBRO_ARANCEL,
                                  persona=persona,
                                  relacionados=None,
                                  matricula=matricula,
                                  # contratorecaudacion = None,
                                  nombre=nombrearancel,
                                  cuota=item[0],
                                  fecha=datetime.now().date(),
                                  fechavence=item[2],
                                  valor=item[1],
                                  iva_id=1,
                                  valoriva=0,
                                  valortotal=item[1],
                                  saldo=item[1],
                                  cancelado=False)
                    rubro.save(request)

                    if item[0] == 1:
                        rubromatricula.relacionados = rubro
                        rubromatricula.save(request)
                arancel.delete()
                Matricula.objects.filter(pk=matricula.id).update(aranceldiferido=1)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error. %s" % ex})

        elif action == 'aceptarAutomatricula':
            try:
                id = int(request.POST['id']) if 'id' in request.POST and request.POST['id'] else 0
                if not Inscripcion.objects.filter(pk=id):
                    return JsonResponse({"result": "bad", "mensaje": u"No se reconocio al estudiante."})
                termino = int(request.POST['termino']) if 'termino' in request.POST and request.POST['termino'] else 0
                if not Inscripcion.objects.filter(pk=id):
                    return JsonResponse({"result": "bad", "mensaje": u"No se reconocio al estudiante."})
                if not termino:
                    return JsonResponse({"result": "bad", "mensaje": u"Debe aceptar los terminos."})
                inscripcion = Inscripcion.objects.get(pk=id)
                matricula = inscripcion.matricula_set.filter(automatriculapregrado=True, termino=False)[0]
                matricula.termino = True
                matricula.fechatermino = datetime.now()
                matricula.save(request)
                log(u'Acepto los terminos de la matricula: %s' % matricula, request, "edit")
                if not matricula.confirmarmatricula_set.filter(matricula=matricula):
                    confirmar = ConfirmarMatricula(matricula=matricula, estado=True)
                    confirmar.save(request)
                    log(u'Confirmo la matricula: %s' % confirmar, request, "add")
                return JsonResponse({'result': 'ok', 'mensaje': u"Se guardo correctamente la matrícula"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'rechazoAutomatricula':
            try:
                id = int(request.POST['id']) if 'id' in request.POST and request.POST['id'] else 0
                if not Inscripcion.objects.filter(pk=id):
                    return JsonResponse({"result": "bad", "mensaje": u"No se reconocio al estudiante."})
                inscripcion = Inscripcion.objects.get(pk=id)
                matricula = inscripcion.matricula_set.filter(automatriculapregrado=True, termino=False)[0]
                rubro = Rubro.objects.filter(matricula=matricula, status=True)
                if rubro:
                    if Rubro.objects.filter(matricula=matricula, status=True)[0].tiene_pagos():
                        return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar la matricula, porque existen rubros de la matricula ya cancelados."})
                delmatricula = matricula
                auditoria = AuditoriaMatricula(inscripcion=matricula.inscripcion,
                                               periodo=matricula.nivel.periodo,
                                               tipo=3)
                auditoria.save(request)
                matricula.delete()
                log(u'Elimino matricula: %s' % delmatricula, request, "del")
                return JsonResponse({"result": "ok", 'mensaje': u"Se elimino correctamente la matrícula"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al rechazar la matrícula"})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})


@login_required(redirect_field_name='ret', login_url='/loginsga')
@last_access
@transaction.atomic()
@detect_mobile
def view_addremove_matricula_pregrado(request):
    if request.method == 'POST':
        action = request.POST['action']
        persona = request.session['persona']
        perfilprincipal = request.session['perfilprincipal']
        periodo = request.session['periodo']
        inscripcion = perfilprincipal.inscripcion
        hoy = datetime.now().date()

        if action == 'loadInitialData':
            try:
                matricula_id = int(request.POST['matricula_id']) if 'matricula_id' in request.POST and request.POST['matricula_id'] else None
                if not Matricula.objects.values('id').filter(pk=matricula_id).exists():
                    raise NameError(u"Matricula no existe")
                matricula = Matricula.objects.get(pk=matricula_id)
                nivel = matricula.nivel
                periodomatricula = None
                if nivel.periodo.periodomatricula_set.values('id').filter(status=True).exists():
                    periodomatricula = nivel.periodo.periodomatricula_set.filter(status=True)[0]
                if not periodomatricula:
                    raise NameError(u"Periodo académico no existe")
                aInscripcion = {"id": inscripcion.id,
                                "itinerario": inscripcion.itinerario,
                                }
                tiene_rubro_pagado_matricula = False
                tiene_rubro_pagado_materias = False
                puede_quitar_matricula = False
                puede_agregar_matricula = False
                valor_pagados = 0.0
                valor_pendiente = 0.0
                if matricula.rubro_set.values("id").filter(status=True).exists():
                    # total = matricula.total_rubros()
                    tiene_rubro_pagado_materias = tiene_rubro_pagado_matricula = matricula.tiene_pagos_matricula()
                    valor_pagados = matricula.total_pagado_rubro()
                    valor_pendiente = matricula.total_saldo_rubro()
                if periodomatricula.puede_agregar_materia_rubro_pagados:
                    puede_agregar_matricula = periodomatricula.puede_agregar_materia and matricula.nivel.puede_agregar_materia_matricula()
                else:
                    puede_agregar_matricula = periodomatricula.puede_agregar_materia and not tiene_rubro_pagado_matricula and matricula.nivel.puede_agregar_materia_matricula()
                puede_quitar_matricula = periodomatricula.ver_eliminar_matricula and not tiene_rubro_pagado_matricula and matricula.nivel.puede_quitar_materia_matricula()

                aMatricula = {"id": matricula.id,
                              "totalcreditos": str(floatformat(matricula.totalcreditos, 2)),
                              "totalhoras": matricula.totalhoras,
                              "promedionotas": str(floatformat(matricula.promedionotas, 2)),
                              "promedioasistencias": matricula.promedioasistencias,
                              "retirado": matricula.retirado(),
                              "nivel": {"id": matricula.nivel.id,
                                        "cerrado": matricula.nivel.cerrado,
                                        },
                              "tiene_rubro_pagado": tiene_rubro_pagado_matricula,
                              "valor_pagados": valor_pagados,
                              "valor_pagados_str": str(floatformat(valor_pagados, 2)),
                              "valor_pendiente": valor_pendiente,
                              "valor_pendiente_str": str(floatformat(valor_pendiente, 2)),
                              "puede_quitar": puede_quitar_matricula,
                              "puede_agregar": puede_agregar_matricula,
                              "tiene_token": matricula.tiene_token_retiro(),
                              "puede_reenviar_token": matricula.puede_reenviar_email_token(),
                              "contador_reenviar_email_token": matricula.contador_reenviar_email_token(),
                              }

                materiasasignadas = matricula.materiaasignada_set.all().order_by('materia__asignaturamalla__nivelmalla__orden')
                aMaterias = []
                for ma in materiasasignadas:
                    totalrecordasignatura = inscripcion.total_record_asignaturatodo(ma.materia.asignatura)
                    nivelmateria = inscripcion.asignatura_en_asignaturamalla(ma.materia.asignatura)
                    practica = {}
                    alumnopracticamateria = ma.alumnopracticamateria()
                    if alumnopracticamateria:
                        if alumnopracticamateria.grupoprofesor:
                            practica['paralelo'] = alumnopracticamateria.grupoprofesor.get_paralelopractica_display()
                    puede_quitar_materia = False
                    if periodomatricula.puede_eliminar_materia_rubro_pagados:
                        puede_quitar_materia = ma.materia.nivel.puede_quitar_materia_matricula() and totalrecordasignatura <= 2 and not ma.homologada() and not ma.convalidada() and ma.valida_pararecord() and not ma.retirado() and not ma.materia.cerrado and ma.notafinal == 0
                    else:
                        puede_quitar_materia = not tiene_rubro_pagado_materias and ma.materia.nivel.puede_quitar_materia_matricula() and totalrecordasignatura <= 2 and not ma.homologada() and not ma.convalidada() and ma.valida_pararecord() and not ma.retirado() and not ma.materia.cerrado and ma.notafinal == 0

                    horarios = []
                    if periodomatricula.valida_conflicto_horario:
                        horarios = get_horarios_clases_data(ma.materia)
                    mipractica = None
                    if AlumnosPracticaMateria.objects.values("id").filter(materiaasignada__matricula__inscripcion=inscripcion, status=True).exists():
                        apm = AlumnosPracticaMateria.objects.filter(materiaasignada__matricula__inscripcion=inscripcion, status=True)[0]
                        mipractica = {"id": apm.grupoprofesor.id,
                                      "horarios_verbose": get_horarios_practicas_informacion(apm.grupoprofesor) if periodomatricula and periodomatricula.ver_horario_materia else '',
                                      "horarios": get_horarios_practicas_data(apm.grupoprofesor) if periodomatricula and periodomatricula.valida_conflicto_horario else [],
                                      "cupos": apm.grupoprofesor.cupo if periodomatricula and periodomatricula.valida_cupo_materia else 0,
                                      "disponibles": apm.grupoprofesor.cuposdisponiblesgrupoprofesor() if periodomatricula and periodomatricula.valida_cupo_materia else 0,
                                      "paralelo": apm.grupoprofesor.get_paralelopractica_display(),
                                      "profesor": apm.grupoprofesor.profesormateria.profesor.persona.nombre_completo_inverso().__str__(),
                                      }
                    aMaterias.append({"id": ma.id,
                                      "materia": {"id": ma.materia.id,
                                                  "nombre_completo": ma.materia.nombre_completo(),
                                                  "paralelo": ma.materia.paralelo,
                                                  "paralelo_verbose": ma.materia.paralelomateria.nombre,
                                                  "paralelo_id": ma.materia.paralelomateria.id,
                                                  "asignatura_id": ma.materia.asignaturamalla.asignatura.id,
                                                  "nivelmalla_id": ma.materia.asignaturamalla.nivelmalla.id,
                                                  "nivelmateria": nivelmateria.nivelmalla.__str__() if nivelmateria else None,
                                                  "nivel_id": ma.materia.nivel.id,
                                                  "cerrado": ma.materia.cerrado,
                                                  "inicio": ma.materia.inicio.__str__(),
                                                  "fin": ma.materia.fin.__str__(),
                                                  "creditos": str(floatformat(ma.materia.creditos, 2)),
                                                  "horas": ma.materia.horas,
                                                  "modulo": ma.materia.asignatura.modulo,
                                                  "horarios": horarios,
                                                  "practica": mipractica,
                                                  },
                                      "totalrecordasignatura": totalrecordasignatura,
                                      "itinerario": nivelmateria.itinerario if nivelmateria and nivelmateria.itinerario else 0,
                                      "convalidada": ma.convalidada(),
                                      "homologada": ma.homologada(),
                                      "retirado": ma.retirado(),
                                      "existe_en_malla": ma.existe_en_malla(),
                                      "valida_pararecord": ma.valida_pararecord(),
                                      "aprobada": ma.aprobada(),
                                      "estado_id": ma.estado.id,
                                      "estado_verbose": ma.estado.nombre,
                                      "evaluar": ma.evaluar,
                                      "pertenece_malla": ma.pertenece_malla(),
                                      "fechacierre": ma.fechacierre.__str__(),
                                      "practica": practica,
                                      "sinasistencia": ma.sinasistencia,
                                      "fechaasignacion": ma.fechaasignacion.__str__(),
                                      "notafinal": str(floatformat(ma.notafinal, 2)),
                                      "asistenciafinal": ma.asistenciafinal,
                                      "puede_quitar": puede_quitar_materia,
                                      "tiene_token": ma.tiene_token_retiro(),
                                      "puede_reenviar_token": ma.puede_reenviar_email_token(),
                                      "contador_reenviar_email_token": ma.contador_reenviar_email_token(),
                                      # "evaluada": ma.evaluada(),
                                      })

                inscripcion_malla = inscripcion.malla_inscripcion()
                inscripcion_nivel = inscripcion.mi_nivel()
                record = inscripcion.recordacademico().filter(status=True, aprobada=True, asignaturamalla__isnull=False)
                asignaturas_malla = inscripcion_malla.malla.asignaturamalla_set.filter(status=True).exclude(nivelmalla_id=NIVEL_MALLA_CERO)
                asignaturas_malla = asignaturas_malla.exclude(pk__in=materiasasignadas.values_list('materia__asignaturamalla_id', flat=True))
                asignaturas_malla = asignaturas_malla.exclude(pk__in=record.values_list('asignaturamalla_id', flat=True)).order_by('nivelmalla', 'ejeformativo')
                va_ultima_matricula = inscripcion.va_ultima_matricula(periodomatricula.num_matriculas)
                num_va_ultima_matricula = inscripcion.num_va_ultima_matricula(periodomatricula.num_matriculas)
                aAsignaturasMalla = []
                for am in asignaturas_malla:
                    puedetomar = inscripcion.puede_tomar_materia(am.asignatura)
                    estado = inscripcion.estado_asignatura(am.asignatura)
                    totalmatriculaasignatura = inscripcion.total_record_asignaturatodo(am.asignatura)
                    if not estado in [1, 2]:
                        if inscripcion.itinerario:
                            if am.itinerario:
                                if inscripcion.itinerario == am.itinerario:
                                    estado = 3
                                else:
                                    estado = 0
                            else:
                                estado = 3
                        else:
                            estado = 3

                    materias = []
                    puede_ver_horario = 0
                    """PERMITE QUE UNICAMENTE PUEDAN SELECCIONAR SOLO MATERIAS DE TERCERA MATRICULA"""
                    if va_ultima_matricula and num_va_ultima_matricula >= periodomatricula.num_materias_maxima_ultima_matricula and puedetomar and estado in [2, 3] and totalmatriculaasignatura != (periodomatricula.num_matriculas - 1) and am.nivelmalla.orden > inscripcion_nivel.nivel.orden:
                        puedetomar = False

                    if puedetomar and estado in [2, 3] and totalmatriculaasignatura < periodomatricula.num_matriculas:
                        materiasabiertas = Materia.objects.filter(Q(asignatura=am.asignatura, inicio__gte=hoy, nivel__cerrado=False, nivel__periodo=nivel.periodo), status=True).order_by('id')
                        if periodomatricula and periodomatricula.valida_materia_carrera:
                            materiasabiertas = materiasabiertas.filter(asignaturamalla__malla=inscripcion.mi_malla()).distinct().order_by('id')
                        if periodomatricula and periodomatricula.valida_seccion and not va_ultima_matricula:
                            materiasabiertas = materiasabiertas.filter(nivel__sesion=inscripcion.sesion).distinct().order_by('id')
                        if periodomatricula.puede_agregar_materia_rubro_pagados:
                            if materiasabiertas.count() > 0:
                                puede_ver_horario = 1
                        else:
                            if materiasabiertas.count() > 0 and not tiene_rubro_pagado_materias:
                                puede_ver_horario = 1

                        for m in materiasabiertas:
                            puede_agregar_materia = False
                            if m.nivel.nivellibrecoordinacion_set.exists():
                                coordinacion = m.nivel.nivellibrecoordinacion_set.all()[0].coordinacion.nombre
                            else:
                                coordinacion = m.nivel.carrera.nombre

                            horarios_verbose = []
                            horarios = []
                            if periodomatricula.ver_horario_materia:
                                horarios_verbose = get_horarios_clases_informacion(m)
                            if periodomatricula.valida_conflicto_horario:
                                horarios = get_horarios_clases_data(m)
                            mispracticas = get_practicas_data(m)
                            if m.nivel.puede_agregar_materia_matricula():
                                puede_agregar_materia = True
                            materias.append({"id": m.id,
                                             "asignatura": m.asignatura.nombre,
                                             "nivelmalla": to_unicode(m.asignaturamalla.nivelmalla.nombre) if m.asignaturamalla.nivelmalla else "",
                                             "nivelmalla_id": m.asignaturamalla.nivelmalla.id if m.asignaturamalla.nivelmalla else 0,
                                             'sede': to_unicode(m.nivel.sede.nombre) if m.nivel.sede else "",
                                             "carrera": to_unicode(m.asignaturamalla.malla.carrera.nombre_completo()) if m.asignaturamalla.malla.carrera.nombre else "",
                                             "coordinacion": coordinacion,
                                             "paralelo": m.paralelomateria.nombre,
                                             "paralelo_id": m.paralelomateria.id,
                                             "profesor": (m.profesor_principal().persona.nombre_completo()) if m.profesor_principal() else 'SIN DEFINIR',
                                             'inicio': m.inicio.strftime("%d-%m-%Y"),
                                             'fin': m.fin.strftime("%d-%m-%Y"),
                                             'session': to_unicode(m.nivel.sesion.nombre),
                                             'identificacion': m.identificacion,
                                             "tipomateria": m.tipomateria,
                                             "tipomateria_display": m.get_tipomateria_display(),
                                             "teoriapractica": 1 if m.asignaturamalla.practicas else 0,
                                             "cupos": m.cupo if periodomatricula and periodomatricula.valida_cupo_materia else 0,
                                             "disponibles": m.capacidad_disponible() if periodomatricula and periodomatricula.valida_cupo_materia else 0,
                                             "horarios_verbose": horarios_verbose,
                                             "horarios": horarios,
                                             "mispracticas": mispracticas,
                                             "puede_agregar": puede_agregar_materia,
                                             })
                    if am.itinerario > 0:
                        itinerario_verbose = f"ITINERARIO {am.itinerario}"
                    else:
                        itinerario_verbose = ''
                    predecesoras_verbose = ' , '.join(
                        (p.predecesora.asignatura.nombre for p in am.lista_predecesoras()))
                    aAsignaturasMalla.append({"id": am.id,
                                              "asignatura": am.asignatura.nombre,
                                              "nivelmalla_id": am.nivelmalla.id,
                                              "nivelmalla": am.nivelmalla.nombre,
                                              "ejeformativo": am.ejeformativo.nombre,
                                              "estado": estado,
                                              "creditos": am.creditos,
                                              "itinerario": am.itinerario,
                                              "itinerario_verbose": itinerario_verbose,
                                              "horas": am.horas,
                                              "cantidad_predecesoras": am.cantidad_predecesoras(),
                                              "totalrecordasignatura": totalmatriculaasignatura,
                                              "predecesoras": predecesoras_verbose,
                                              "materias": materias,
                                              "puede_ver_horario": puede_ver_horario
                                              })
                return JsonResponse({"result": "ok", "aInscripcion": aInscripcion, "aMatricula": aMatricula, "aMaterias": aMaterias, "aAsignaturasMalla": aAsignaturasMalla})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error. %s" % ex})

        elif action == 'loadCupoMateria':
            try:
                if not 'asignatura' in request.POST:
                    raise NameError(u"Parametro no valido")
                asignatura = json.loads(request.POST['asignatura'])
                if not asignatura:
                    raise NameError(u"Parametro no valido")
                materias = []
                for m in asignatura['materias']:
                    disponibles = 0
                    for key, value in m.items():
                        if 'id' == key:
                            materia = Materia.objects.get(pk=int(m['id']))
                            disponibles = materia.capacidad_disponible()
                    m['disponibles'] = disponibles
                    materias.append(m)
                asignatura['materias'] = materias
                return JsonResponse({"result": "ok", 'asignatura': asignatura})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error. %s" % ex})

        elif action == 'loadCupoPractica':
            try:
                if not 'materia' in request.POST:
                    raise NameError(u"Parametro no valido")
                materia = json.loads(request.POST['materia'])
                if not materia:
                    raise NameError(u"Parametro no valido")
                practicas = []
                for p in materia['mispracticas']:
                    disponibles = 0
                    for key, value in p.items():
                        if 'id' == key:
                            grupo = GruposProfesorMateria.objects.get(pk=int(p['id']))
                            disponibles = grupo.cuposdisponiblesgrupoprofesor()
                    p['disponibles'] = disponibles
                    practicas.append(p)

                materia['mispracticas'] = practicas

                return JsonResponse({"result": "ok", 'materia': materia})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error. %s" % ex})

        elif action == 'validConflictoHorario':
            try:
                if not 'materias' in request.POST:
                    raise NameError(u"Parametro de materias seleccionadas no valido")
                mis_materias = json.loads(request.POST['materias'])
                if not 'materia' in request.POST:
                    raise NameError(u"Parametro de materia seleccionada no valido")
                mi_materia = json.loads(request.POST['materia'])
                mis_clases = []
                mi_clase = []
                for materia in mis_materias:
                    if materia['practica'] and len(materia['practica']['horarios']) > 0:
                        mis_clases.append(materia['practica']['horarios'])
                    if materia['horarios'] and len(materia['horarios']) > 0:
                        mis_clases.append(materia['horarios'])
                if mi_materia['practica'] and len(mi_materia['practica']) > 0:
                    mi_clase.append(mi_materia['practica']['horarios'])
                if mi_materia['horarios'] and len(mi_materia['horarios']) > 0:
                    mi_clase.append(mi_materia['horarios'])
                tiene_conflicto, mensaje = valida_conflicto_materias_estudiante(mis_clases, mi_clase)
                return JsonResponse({"result": "ok", "conflicto": tiene_conflicto, "mensaje": mensaje})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error. %s" % ex})

        elif action == 'setMateria':
            try:
                if not 'idm' in request.POST:
                    raise NameError(u"Matricula no valida")
                if not Matricula.objects.values("id").filter(pk=int(request.POST['idm'])).exists():
                    raise NameError(u"Matricula no valida")
                matricula = Matricula.objects.get(pk=int(request.POST['idm']))
                inscripcion = matricula.inscripcion
                if not 'materias' in request.POST:
                    raise NameError(u"Parametro de materias no valida")
                mis_clases = json.loads(request.POST['materias'])
                if not 'materia' in request.POST:
                    raise NameError(u"Parametro de materia seleccionada no valida")
                mi_materia = json.loads(request.POST['materia'])
                if not Materia.objects.values("id").filter(pk=int(mi_materia['id'])).exists():
                    raise NameError(u"Materia seleccionada no valida")
                materia = Materia.objects.get(pk=int(mi_materia['id']))
                mi_practica = 0
                if mi_materia['practica']:
                    for k, v in mi_materia['practica'].items():
                        if k == 'id':
                            mi_practica = v

                mi_materia_singrupo = 0
                if materia.asignaturamalla.tipomateria_id == TIPO_PROFESOR_PRACTICA:
                    if mi_materia_singrupo != mi_practica:
                        mi_materia_singrupo = materia.id

                if not inscripcion.itinerario or inscripcion.itinerario < 1:
                    if materia.asignaturamalla.itinerario > 0:
                        inscripcion.itinerario = int(materia.asignaturamalla.itinerario)
                        inscripcion.save(request)

                if materia.asignaturamalla.practicas:
                    if mi_practica == 0:
                        raise NameError(u"Materia es TP, seleccione un horario de prácticas.")
                    # if not GruposProfesorMateria.objects.values("id").filter(pk=mi_practica).exists():
                    #     raise NameError(u"No existe grupo de prácticas.")
                    # grupoprofesormateria = GruposProfesorMateria.objects.get(pk=mi_practica)
                # MATERIAS PRACTICAS
                grupoprofesormaterias = GruposProfesorMateria.objects.filter(pk=mi_practica)
                profesoresmateriassingrupo = ProfesorMateria.objects.filter(materia_id=mi_materia_singrupo, tipoprofesor_id=TIPO_PROFESOR_PRACTICA)

                if matricula.inscripcion.existe_en_malla(materia.asignatura) and not matricula.inscripcion.puede_tomar_materia(materia.asignatura):
                    raise NameError(u"No puede tomar esta materia por tener precedencias")
                if matricula.inscripcion.existe_en_modulos(materia.asignatura) and not matricula.inscripcion.puede_tomar_materia_modulo(materia.asignatura):
                    raise NameError(u"No puede tomar esta materia por tener precedencias")
                periodomatricula = None
                if matricula.nivel.periodo.periodomatricula_set.values('id').filter(status=True).exists():
                    periodomatricula = matricula.nivel.periodo.periodomatricula_set.filter(status=True)[0]
                if not periodomatricula:
                    raise NameError(u"Periodo académico no existe")
                if not periodomatricula.puede_agregar_materia:
                    raise NameError(u"No se permite agregar materia a la matricula")

                if periodomatricula.valida_conflicto_horario and inscripcion.carrera.modalidad != 3:
                    conflicto, msg = valida_conflicto_materias_estudiante_enroll(mis_clases)
                    if conflicto:
                        raise NameError(msg)
                if periodomatricula.valida_cupo_materia:
                    if not materia.tiene_capacidad():
                        raise NameError(u"No existe cupo para esta materia.")
                        # VERIFICANDO CUPO MATERIAS PRACTICAS EN PROFESOR MATERIA CON PÁRALELO
                        for gpm in grupoprofesormaterias:
                            validar = True
                            if gpm.profesormateria.materia.tipomateria == TIPO_PROFESOR_PRACTICA:
                                validar = variable_valor('VALIDAR_HORARIO_CUPO_MATERIA_VIRTUAL')
                            if validar:
                                if not HOMITIRCAPACIDADHORARIO and gpm.cuposdisponiblesgrupoprofesor() <= 0:
                                    raise NameError(u"Capacidad limite de la materia en la práctica:  " + str(gpm.profesormateria.materia) + ", seleccione otro.")

                if matricula.materiaasignada_set.values('id').filter(materia=materia).exists():
                    raise NameError(u"Ya se encuentra matriculado en esta materia")

                materiaasignada = MateriaAsignada(matricula=matricula,
                                                  materia=materia,
                                                  notafinal=0,
                                                  asistenciafinal=0,
                                                  cerrado=False,
                                                  observaciones='',
                                                  estado_id=NOTA_ESTADO_EN_CURSO)
                materiaasignada.save(request)

                # MATRICULA EN LA PRACTICA QUE NO TENGAN GRUPO
                if profesoresmateriassingrupo.values('id').filter(materia=materia).exists():
                    profemate = profesoresmateriassingrupo.filter(materia=materia)[0]
                    alumnopractica = AlumnosPracticaMateria(materiaasignada=materiaasignada, profesormateria=profemate)
                    alumnopractica.save(request)
                    log(u'Materia (%s) con profesor practica (%s) seleccionada matricula: %s en tabla alumnopractica (%s)' % (materia, profemate, materiaasignada, alumnopractica.id), request, "add")
                # MATRICULA EN LA PRACTICA QUE SI TENGAN GRUPOS
                elif grupoprofesormaterias.values('id').filter(profesormateria__materia=materia).exists():
                    profemate_congrupo = grupoprofesormaterias.filter(profesormateria__materia=materia)[0]
                    if periodomatricula.valida_cupo_materia:
                        validar = True
                        if profemate_congrupo.profesormateria.materia.tipomateria == 2:
                            validar = variable_valor('VALIDAR_HORARIO_CUPO_MATERIA_VIRTUAL')
                        if validar:
                            if not HOMITIRCAPACIDADHORARIO and profemate_congrupo.cuposdisponiblesgrupoprofesor() <= 0:
                                raise NameError(u"Capacidad limite de la materia en la práctica:  " + str(profemate_congrupo.profesormateria.materia) + ", seleccione otro.")

                    alumnopractica = AlumnosPracticaMateria(materiaasignada=materiaasignada,
                                                            profesormateria=profemate_congrupo.profesormateria,
                                                            grupoprofesor=profemate_congrupo)
                    alumnopractica.save(request)
                    log(u'Materia (%s) con grupo profesor practica (%s) seleccionada matricula: %s en tabla alumnopractica (%s)' % (materia, profemate_congrupo, materiaasignada, alumnopractica.id), request, "add")
                materiaasignada.matriculas = materiaasignada.cantidad_matriculas()
                materiaasignada.asistencias()
                materiaasignada.evaluacion()
                materiaasignada.mis_planificaciones()
                materiaasignada.save(request)
                if matricula.nivel.nivelgrado:
                    log(u'Adiciono materia: %s' % materiaasignada, request, "add")
                else:
                    if datetime.now().date() < materia.nivel.fechainicioagregacion:
                        # AGREGACION DE MATERIAS EN MATRICULACION REGULAR SIN REALIZAR PAGOS
                        materiaasignada.save(request)
                        log(u'Adiciono materia: %s' % materiaasignada, request, "add")
                        # if CALCULO_POR_CREDITO:
                        agregacion_aux_pregrado(request, matricula)
                    elif matricula.nivel.puede_agregar_materia_matricula():
                        # AGREGACION DE MATERIAS EN FECHAS DE AGREGACIONES
                        registro = AgregacionEliminacionMaterias(matricula=matricula,
                                                                 agregacion=True,
                                                                 asignatura=materiaasignada.materia.asignatura,
                                                                 responsable=request.session['persona'],
                                                                 fecha=datetime.now().date(),
                                                                 creditos=materiaasignada.materia.creditos,
                                                                 nivelmalla=materiaasignada.materia.nivel.nivelmalla if materiaasignada.materia.nivel.nivelmalla else None,
                                                                 matriculas=materiaasignada.matriculas)
                        registro.save(request)
                        log(u'Adiciono materia: %s' % materiaasignada, request, "add")
                        # if CALCULO_POR_CREDITO:
                        agregacion_aux_pregrado(request, matricula)
                    else:
                        if not materia.asignatura.modulo:
                            raise NameError(u"Materia no permitida")
                        registro = AgregacionEliminacionMaterias(matricula=matricula,
                                                                 agregacion=True,
                                                                 asignatura=materiaasignada.materia.asignatura,
                                                                 responsable=request.session['persona'],
                                                                 fecha=datetime.now().date(),
                                                                 creditos=materiaasignada.materia.creditos,
                                                                 nivelmalla=materiaasignada.materia.nivel.nivelmalla if materiaasignada.materia.nivel.nivelmalla else None,
                                                                 matriculas=materiaasignada.matriculas)
                        registro.save(request)
                        log(u'Adiciono materia: %s' % materiaasignada, request, "add")
                        # if CALCULO_POR_CREDITO:
                        agregacion_aux_pregrado(request, matricula)
                matricula.actualizar_horas_creditos()
                matricula.actualiza_matricula()
                matricula.inscripcion.actualiza_estado_matricula()
                valid, msg, aData = get_tipo_matricula(request, matricula)
                if not valid:
                    raise NameError(msg)
                cantidad_nivel = aData['cantidad_nivel']
                porcentaje_perdidad_parcial_gratuidad = aData['porcentaje_perdidad_parcial_gratuidad']
                cantidad_seleccionadas = aData['cantidad_seleccionadas']
                porcentaje_seleccionadas = int(round(Decimal((float(cantidad_nivel) * float(porcentaje_perdidad_parcial_gratuidad)) / 100).quantize(Decimal('.00')), 0))
                if (cantidad_seleccionadas < porcentaje_seleccionadas):
                    matricula.grupo_socio_economico(2)
                else:
                    matricula.grupo_socio_economico(1)
                calcula_nivel(matricula)
                matricula.agregacion_aux(request)
                matricula.calcula_nivel()
                return JsonResponse({"result": "ok", "mensaje": u"Se adiciono correctamente la materia"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error al guardar. %s" % ex})

        elif action == "generateRetiroMateria":
            try:
                if not 'idma' in request.POST:
                    raise NameError(u"Materia no valida")
                if not MateriaAsignada.objects.values("id").filter(pk=int(request.POST['idma'])).exists():
                    raise NameError(u"Materia no encontrada")
                materiaasignada = MateriaAsignada.objects.get(pk=int(request.POST['idma']))
                return generateCodeRemoveMateria(request, materiaasignada)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error, %s" % ex.__str__()})

        elif action == "reenviarRetiroMateria":
            try:
                if not 'idma' in request.POST:
                    raise NameError(u"Materia no valida")
                if not MateriaAsignada.objects.values("id").filter(pk=int(request.POST['idma'])).exists():
                    raise NameError(u"Materia no encontrada")
                materiaasignada = MateriaAsignada.objects.get(pk=int(request.POST['idma']))

                if not materiaasignada.puede_reenviar_email_token():
                    raise NameError(
                        u"Ha agotado el número máximo de reenvio de correo electrónico por día de la materia")
                return reenvioCodeRemoveMateria(request, materiaasignada)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error, %s" % ex.__str__()})

        elif action == "cancelarRetiroMateria":
            try:
                if not 'idma' in request.POST:
                    raise NameError(u"Materia no valida")
                if not MateriaAsignada.objects.values("id").filter(pk=int(request.POST['idma'])).exists():
                    raise NameError(u"Materia no encontrada")
                materiaasignada = MateriaAsignada.objects.get(pk=int(request.POST['idma']))
                tokens = materiaasignada.materiaasignadatoken_set.filter(status=True, isActive=True)
                tokens.update(isActive=False)
                UserToken.objects.filter(pk__in=tokens.values("user_token__id")).update(isActive=False)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error, %s" % ex.__str__()})

        elif action == 'deleteMateria':
            try:
                if not 'idma' in request.POST:
                    raise NameError(u"Materia no valida")
                if not MateriaAsignada.objects.values("id").filter(pk=int(request.POST['idma'])).exists():
                    raise NameError(u"Materia no encontrada")
                materiaasignada = MateriaAsignada.objects.get(pk=int(request.POST['idma']))
                if not 'utilizaSeguridad' in request.POST:
                    raise NameError(u"Código no valido")
                utilizaSeguridad = request.POST['utilizaSeguridad'] == 'true'
                if utilizaSeguridad:
                    if not 'code' in request.POST:
                        raise NameError(u"Código no valido")
                    code = request.POST['code']
                    tokens = materiaasignada.materiaasignadatoken_set.filter(status=True, isActive=True,
                                                                             user_token__isActive=True,
                                                                             user_token__action_type=2,
                                                                             user_token__date_expires__gte=datetime.now())
                    if not tokens.filter(codigo=code).exists():
                        raise NameError(u"Código no valido")
                    tokens.update(isActive=False)
                    UserToken.objects.filter(pk__in=tokens.values("user_token__id")).update(isActive=False)

                matricula = materiaasignada.matricula
                periodomatricula = None
                if matricula.nivel.periodo.periodomatricula_set.values('id').filter(status=True).exists():
                    periodomatricula = matricula.nivel.periodo.periodomatricula_set.filter(status=True)[0]
                if not periodomatricula:
                    raise NameError(u"Periodo académico no existe")

                # if matricula.rubro_set.filter(status=True, cancelado=True).exists():
                #     raise NameError(u"No puede eliminar materia, porque existen rubros de la matricula cancelados")
                materia = materiaasignada.materia
                if matricula.nivel.nivelgrado:
                    if matricula.materiaasignada_set.values('id').filter(status=True).count() > 1:
                        bandera = 0
                        log(u'Elimino materia asignada: %s' % materiaasignada, request, "del")
                        materiaasignada.materia.descontar_cupo_adicional(request)
                        materiaasignada.delete()
                        matricula.actualizar_horas_creditos()
                    else:
                        bandera = 1
                        if matricula.rubro_set.values("id").filter(status=True).exists():
                            if matricula.tiene_pagos_matricula():
                                raise NameError(
                                    u"No puede eliminar ultima materia, porque matricula tiene rubros pagados")
                        log(u'Elimino matricula por ultima materia: %s' % materiaasignada, request, "del")
                        materiaasignada.materia.descontar_cupo_adicional(request)
                        materiaasignada.delete()
                        matricula.delete()
                else:
                    if matricula.nivel.fechafinquitar >= datetime.now().date():
                        if matricula.materiaasignada_set.values('id').filter(status=True).count() > 1:
                            bandera = 0
                            log(u'Elimino materia asignada: %s' % materiaasignada, request, "del")
                            materiaasignada.materia.descontar_cupo_adicional(request)
                            matricula.eliminar_materia(materiaasignada, request)
                            matricula.actualizar_horas_creditos()
                        else:
                            bandera = 1
                            if matricula.rubro_set.values("id").filter(status=True).exists():
                                if matricula.tiene_pagos_matricula():
                                    raise NameError(
                                        u"No puede eliminar ultima materia, porque matricula tiene rubros pagados")
                                log(u'Elimino matricula por ultima materia: %s' % materiaasignada, request, "del")
                                materiaasignada.materia.descontar_cupo_adicional(request)
                                matricula.eliminar_materia(materiaasignada, request)
                                matricula.delete()
                            else:
                                log(u'Elimino materia asignada: %s' % materiaasignada, request, "del")
                                materiaasignada.materia.descontar_cupo_adicional(request)
                                matricula.eliminar_materia(materiaasignada, request)
                                matricula.actualizar_horas_creditos()
                    else:
                        raise NameError(u"No se puede eliminar, por lo menos debe de existir una materia")
                # if CALCULO_POR_CREDITO:
                if bandera == 0:
                    matricula.agregacion_aux(request)
                    matricula.actualizar_horas_creditos()
                    matricula.actualiza_matricula()
                    matricula.inscripcion.actualiza_estado_matricula()
                    valid, msg, aData = get_tipo_matricula(request, matricula)
                    if not valid:
                        raise NameError(msg)
                    cantidad_nivel = aData['cantidad_nivel']
                    porcentaje_perdidad_parcial_gratuidad = aData['porcentaje_perdidad_parcial_gratuidad']
                    cantidad_seleccionadas = aData['cantidad_seleccionadas']
                    porcentaje_seleccionadas = int(round(
                        Decimal((float(cantidad_nivel) * float(porcentaje_perdidad_parcial_gratuidad)) / 100).quantize(
                            Decimal('.00')), 0))
                    if (cantidad_seleccionadas < porcentaje_seleccionadas):
                        matricula.grupo_socio_economico(2)
                    else:
                        matricula.grupo_socio_economico(1)

                    calcula_nivel(matricula)
                    if periodomatricula.valida_envio_mail:
                        if NOTIFICA_ELIMINACION_MATERIA:
                            send_html_mail("Materia eliminada",
                                           "emails/materiaeliminada.html",
                                           {
                                               'sistema': request.session['nombresistema'],
                                               'materia': materia,
                                               'matricula': matricula,
                                               't': tituloinstitucion()
                                           }, lista_correo([FINANCIERO_GROUP_ID, SECRETARIA_GROUP_ID]), [],
                                           cuenta=CUENTAS_CORREOS[0][1])
                        send_html_mail("Confirmación de retiro de materia",
                                       "emails/confirmacion_materia_eliminada.html",
                                       {
                                           'sistema': request.session['nombresistema'],
                                           'fecha': datetime.now().date,
                                           'fecha_g': datetime.now().date(),
                                           'hora_g': datetime.now().time(),
                                           'persona': persona,
                                           'materia': materia,
                                           'matricula': matricula,
                                           't': tituloinstitucion(),
                                           'ip': get_client_ip(request),
                                       },
                                       persona.lista_emails(), [],
                                       cuenta=CUENTAS_CORREOS[7][1])
                return JsonResponse({"result": "ok", "mensaje": u"Se quito correctamente la materia"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error al quitar materia. %s" % ex})

        elif action == "generateCodeEliminarMatricula":
            try:
                if not 'idm' in request.POST:
                    raise NameError(u"Matrícula no valida")
                if not Matricula.objects.values("id").filter(pk=int(request.POST['idm'])).exists():
                    raise NameError(u"Matrícula no encontrada")
                matricula = Matricula.objects.get(pk=int(request.POST['idm']))
                return generateCodeDeleteMatricula(request, matricula)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error, %s" % ex.__str__()})

        elif action == "cancelarEliminarMatricula":
            try:
                if not 'idm' in request.POST:
                    raise NameError(u"Matrícula no valida")
                if not Matricula.objects.values("id").filter(pk=int(request.POST['idm'])).exists():
                    raise NameError(u"Matrícula no encontrada")
                matricula = Matricula.objects.get(pk=int(request.POST['idm']))
                tokens = matricula.matriculatoken_set.filter(status=True, isActive=True)
                tokens.update(isActive=False)
                UserToken.objects.filter(pk__in=tokens.values("user_token__id")).update(isActive=False)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error, %s" % ex.__str__()})

        elif action == "reenviarEliminarMatricula":
            try:
                if not 'idm' in request.POST:
                    raise NameError(u"Matricula no valida")
                if not Matricula.objects.values("id").filter(pk=int(request.POST['idm'])).exists():
                    raise NameError(u"Matricula no encontrada")
                matricula = Matricula.objects.get(pk=int(request.POST['idm']))
                if not matricula.puede_reenviar_email_token():
                    raise NameError(
                        u"Ha agotado el número máximo de reenvio de correo electrónico por día de la matrícula")
                return reenvioCodeDeleteMatricula(request, matricula)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error, %s" % ex.__str__()})

        elif action == 'deleteMatricula':
            try:
                if not 'idm' in request.POST:
                    raise NameError(u"Matricula no valida")
                if not Matricula.objects.values("id").filter(pk=int(request.POST['idm'])).exists():
                    raise NameError(u"Matricula no encontrada")
                matricula = Matricula.objects.get(pk=int(request.POST['idm']))
                if matricula.rubro_set.values("id").filter(status=True).exists():
                    if matricula.tiene_pagos_matricula():
                        raise NameError(
                            u"No puede eliminar la matricula, porque existen rubros de la matricula ya cancelados.")

                if not 'utilizaSeguridad' in request.POST:
                    raise NameError(u"Código no valido")
                utilizaSeguridad = request.POST['utilizaSeguridad'] == 'true'
                if utilizaSeguridad:
                    if not 'code' in request.POST:
                        raise NameError(u"Código no valido")
                    code = request.POST['code']
                    tokens = matricula.matriculatoken_set.filter(status=True, isActive=True, user_token__isActive=True,
                                                                 user_token__action_type=3,
                                                                 user_token__date_expires__gte=datetime.now())
                    if not tokens.filter(codigo=code).exists():
                        raise NameError(u"Código no valido")
                    tokens.update(isActive=False)
                    UserToken.objects.filter(pk__in=tokens.values("user_token__id")).update(isActive=False)

                delpersona = matricula
                auditoria = AuditoriaMatricula(inscripcion=matricula.inscripcion,
                                               periodo=matricula.nivel.periodo,
                                               tipo=3)
                auditoria.save(request)
                matricula.delete()
                if NOTIFICA_ELIMINACION_MATERIA:
                    send_html_mail("Matricula eliminada",
                                   "emails/matriculaeliminada.html",
                                   {
                                       'sistema': request.session['nombresistema'],
                                       'matricula': delpersona,
                                       't': tituloinstitucion()
                                   }, lista_correo([FINANCIERO_GROUP_ID, SECRETARIA_GROUP_ID]), [],
                                   cuenta=CUENTAS_CORREOS[0][1])
                send_html_mail("Confirmación de retiro de materia",
                               "emails/confirmacion_matricula_eliminada.html",
                               {
                                   'sistema': request.session['nombresistema'],
                                   'fecha': datetime.now().date,
                                   'fecha_g': datetime.now().date(),
                                   'hora_g': datetime.now().time(),
                                   'persona': persona,
                                   'matricula': delpersona,
                                   't': tituloinstitucion(),
                                   'ip': get_client_ip(request),
                               },
                               persona.lista_emails(), [],
                               cuenta=CUENTAS_CORREOS[7][1])
                log(u'Elimino matricula: %s' % delpersona, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error, %s" % ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
