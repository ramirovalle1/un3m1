# -*- coding: latin-1 -*-
import json
import os
from datetime import datetime, timedelta, date
from decimal import Decimal

import code128
import pyqrcode
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from django.views.decorators.csrf import csrf_exempt

from bd.models import WebSocket
from decorators import secure_module, last_access
from matricula.funciones import get_nivel_matriculacion, puede_matricularse_seguncronograma_carrera, \
    puede_matricularse_seguncronograma_coordinacion, ubicar_nivel_matricula, get_practicas_data, \
    get_horarios_clases_informacion, get_deuda_persona, get_horarios_clases_data, valida_conflicto_materias_estudiante, \
    action_enroll_pregrado, valid_intro_module_estudiante, to_unicode
from matricula.models import PeriodoMatricula
from sagest.models import Rubro, Pago
from settings import SITE_STORAGE, NIVEL_MALLA_CERO, MATRICULACION_LIBRE, MAXIMO_MATERIA_ONLINE, UTILIZA_GRATUIDADES, \
    PORCIENTO_PERDIDA_PARCIAL_GRATUIDAD, PORCIENTO_PERDIDA_TOTAL_GRATUIDAD, NIVEL_MALLA_UNO, RUBRO_ARANCEL, \
    RUBRO_MATRICULA
from sga.commonviews import adduserdata, obtener_reporte, nivel_matriculacion
from sga.funciones import log, variable_valor, null_to_numeric
from sga.models import Matricula, Inscripcion, Periodo, ConfirmarMatricula, Nivel, InscripcionMalla, Malla, \
    AsignaturaMalla, RecordAcademico, Materia, NivelMalla, TipoProfesor, GruposProfesorMateria, MESES_CHOICES, \
    AuditoriaMatricula, Persona
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsavecertificados
from django.db import connections, transaction

from sga.templatetags.sga_extras import encrypt


# @login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
# @last_access
@csrf_exempt
@transaction.atomic()
def view(request):
    data = {}
    # adduserdata(request, data)
    # valid, msg_error = valid_intro_module_estudiante(request, 'pregrado')
    # if not valid:
    #     return HttpResponseRedirect(f"/?info={msg_error}")

    data['persona'] = persona = Persona.objects.get(pk=75935)
    # perfilprincipal = request.session['perfilprincipal']
    data['periodo'] = periodo = Periodo.objects.get(pk=119)
    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=104493)
    hoy = datetime.now().date()
    data['currenttime'] = datetime.now()
    data['check_session'] = False
    data['websocket'] = None
    if WebSocket.objects.values('id').filter(habilitado=True, sga=True).exists():
        data['websocket'] = WebSocket.objects.filter(habilitado=True, sga=True).first()

    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

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
                    asignaturas_malla = inscripcion_malla.malla.asignaturamalla_set.select_related().all().exclude(nivelmalla_id=NIVEL_MALLA_CERO).order_by('nivelmalla', 'ejeformativo')
                    va_ultima_matricula = inscripcion.va_ultima_matricula(periodomatricula.num_matriculas)
                    aData = []
                    for am in asignaturas_malla:
                        puedetomar = inscripcion.puede_tomar_materia(am.asignatura)
                        estado = inscripcion.estado_asignatura(am.asignatura)
                        totalmatriculaasignatura = inscripcion.total_record_asignatura(am.asignatura)
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
                        if va_ultima_matricula and puedetomar and estado in [2, 3] and totalmatriculaasignatura != 2:
                            puedetomar = False

                        if puedetomar and estado in [2, 3] and totalmatriculaasignatura < 3:
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
                                      "cantidad_predecesoras": am.cantidad_predecesoras(),
                                      "totalrecordasignatura": totalmatriculaasignatura,
                                      "predecesoras": predecesoras_verbose,
                                      "materias": materias,
                                      "puede_ver_horario": puede_ver_horario
                                      })
                    return JsonResponse({"result": "ok", "aData": aData})
                except Exception as ex:
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

            elif action == 'viewPendingValues':
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
                    rubros = Rubro.objects.filter(persona=persona, cancelado=False, status=True).distinct()
                    if periodomatricula.tiene_tiposrubros():
                        rubros = rubros.filter(tipo__in=periodomatricula.tiposrubros())
                    if rubros.exists():
                        rubros_vencidos = rubros.filter(fechavence__lt=datetime.now().date()).distinct()
                        if rubros_vencidos.exists():
                            data['rubros'] = rubros_vencidos
                            data['vencidos'] = True
                            valor_rubros = null_to_numeric(rubros_vencidos.aggregate(valor=Sum('valortotal'))['valor'])
                            valor_pagos = null_to_numeric(Pago.objects.filter(rubro__in=rubros_vencidos, status=True).distinct().aggregate(valor=Sum('valortotal'))['valor'])
                            valores_vencidos = valor_rubros - valor_pagos
                            data['valor_rubros'] = valor_rubros
                            data['valor_pagos'] = valor_pagos
                            data['valor_pendiente'] = valores_vencidos
                        else:
                            data['rubros'] = rubros
                            data['vencidos'] = False
                            valor_rubros = null_to_numeric(rubros.aggregate(valor=Sum('valortotal'))['valor'])
                            valor_pagos = null_to_numeric(Pago.objects.filter(rubro__in=rubros, status=True).distinct().aggregate(valor=Sum('valortotal'))['valor'])
                            valores_pendientes = valor_rubros - valor_pagos
                            data['valor_rubros'] = valor_rubros
                            data['valor_pagos'] = valor_pagos
                            data['valor_pendiente'] = valores_pendientes
                    template = get_template("matricula/pregrado_demo/view_valores_pendientes.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
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
                    nivel_id = int(request.POST['nivel_id']) if 'nivel_id' in request.POST and request.POST['nivel_id'] else None
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
                        valor_cuota_mensual = (valorarancel/num_cuotas).quantize(Decimal('.01'))
                    except ZeroDivisionError:
                        valor_cuota_mensual = 0
                    if valor_cuota_mensual == 0:
                        raise NameError(u"No se puede procesar el registro.")

                    # c1 = (valorarancel/3).quantize(Decimal('.01'))
                    # c2 = c1
                    # c3 = valorarancel - (c1 + c2)

                    rubromatricula = Rubro.objects.get(matricula=matricula, tipo_id=RUBRO_MATRICULA)
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

            elif action == 'loadCalendar':
                try:
                    if not 'idn' in request.POST:
                        raise NameError(u"Datos no enocntrados")
                    if not Nivel.objects.values('id').filter(pk=int(request.POST['idn'])).exists():
                        raise NameError(u"Datos del nivel no encontrado")
                    nivel = Nivel.objects.get(pk=int(request.POST['idn']))
                    if 'mover' in request.POST:
                        mover = request.POST['mover']
                        if mover == 'before':
                            mes = int(request.POST['mes'])
                            anio = int(request.POST['anio'])
                            pmes = mes - 1
                            if pmes == 0:
                                pmes = 12
                                panio = anio - 1
                            else:
                                panio = anio

                        elif mover == 'after':
                            mes = int(request.POST['mes'])
                            anio = int(request.POST['anio'])
                            pmes = mes + 1
                            if pmes == 13:
                                pmes = 1
                                panio = anio + 1
                            else:
                                panio = anio
                        else:
                            pmes = hoy.month
                            panio = hoy.year
                    else:
                        pmes = hoy.month
                        panio = hoy.year
                    pdia = 1
                    lista = {}
                    for i in range(1, 43, 1):
                        dia = {i: 'no'}
                        lista.update(dia)
                        ff = {i: None}
                    comienzo = False
                    fin = False
                    for i in lista.items():
                        try:
                            fecha = date(panio, pmes, pdia)
                            if fecha.isoweekday() == i[0] and fin is False and comienzo is False:
                                comienzo = True
                        except Exception as ex:
                            pass
                        if comienzo:
                            try:
                                fecha = date(panio, pmes, pdia)
                            except Exception as ex:
                                fin = True
                        if comienzo and fin is False:
                            dia = {i[0]: pdia}
                            pdia += 1
                            lista.update(dia)
                    data['pdia'] = pdia
                    data['pmes'] = pmes
                    data['panio'] = panio
                    data['mes'] = MESES_CHOICES[pmes - 1]
                    data['ws'] = [0, 7, 14, 21, 28, 35]
                    data['dwnm'] = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
                    data['dwn'] = [1, 2, 3, 4, 5, 6, 7]
                    data['lista'] = lista
                    data['nivel'] = nivel
                    template = get_template("matricula/pregrado_demo/view_calendario_matricula.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", "json_content": json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error. <br> %s" % ex})

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
                    log(u'Acepto los terminos de la matricula: %s' % matricula, request, "edit", persona.usuario)
                    if not matricula.confirmarmatricula_set.filter(matricula=matricula):
                        confirmar = ConfirmarMatricula(matricula=matricula, estado=True)
                        confirmar.save(request)
                        log(u'Confirmo la matricula: %s' % confirmar, request, "add", persona.usuario)
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
                    log(u'Elimino matricula: %s' % delmatricula, request, "del", persona.usuario)
                    return JsonResponse({"result": "ok", 'mensaje': u"Se elimino correctamente la matrícula"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al rechazar la matrícula"})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
        else:
            try:
                periodomatricula = None
                matricula = None
                if not PeriodoMatricula.objects.values('id').filter(status=True, tipo=2, periodo_id=119).exists():
                    raise NameError(u"Estimado/a estudiante, el periodo de matriculación se encuentra inactivo")
                periodomatricula = PeriodoMatricula.objects.filter(status=True, tipo=2, periodo_id=119)
                if periodomatricula.count() > 1:
                    raise NameError(u"Estimado/a estudiante, proceso de matriculación no se encuentra activo")
                periodomatricula = periodomatricula[0]
                # if not periodomatricula.esta_periodoactivomatricula():
                #     raise NameError(u"Estimado/a estudiante, el periodo de matriculación se encuentra inactivo")
                # periodomatricula = Periodo.objects.filter(status=True, matriculacionactiva=True, activo=True, inicio_agregacion__lte=hoy, limite_agregacion__gte=hoy, tipo_id=2)[0]
                if periodo and periodomatricula and periodomatricula.periodo.id == periodo.id and inscripcion.persona.tiene_matricula_periodo(periodo):
                    matricula = inscripcion.matricula_periodo2(periodo)
                    if ConfirmarMatricula.objects.values('id').filter(matricula=matricula).exists():
                        raise NameError(f"Estimado/a estudiante, le informamos que ya se encuentra matriculado en el Periodo {periodo.__str__()}. <br>Verificar en el módulo <a href='/alu_materias' class='bloqueo_pantalla'>Mis Materias</a>")
                if periodomatricula.valida_coordinacion:
                    if not inscripcion.coordinacion in periodomatricula.coordinaciones():
                        raise NameError(u"Estimado/a estudiante, su coordinación/facultad no esta permitida para la matriculación")
                if periodomatricula.periodo and inscripcion.tiene_automatriculapregrado_por_confirmar(periodomatricula.periodo):
                    data['inscripcion'] = inscripcion
                    data['fichasocioeconomicainec'] = persona.fichasocioeconomicainec()
                    data['periodomatricula'] = periodomatricula
                    data['inscripcionmalla'] = inscripcion.malla_inscripcion()
                    data['minivel'] = inscripcion.mi_nivel().nivel
                    data['title'] = "Confirmación de matrícula"
                    data['materiassignadas'] = inscripcion.materias_automatriculapregrado_por_confirmar(periodomatricula.periodo)
                    return render(request, "matricula/pregrado_demo/confirmar_automatricula.html", data)
                nivel = None
                nivelid = get_nivel_matriculacion(inscripcion, periodomatricula.periodo)

                if nivelid < 0:
                    if nivelid == -1:
                        log(u"Estimado/a estudiante, el periodo de matriculación no se encuentra activo.... %s" % (inscripcion.info()), request, "add", persona.usuario)
                        raise NameError(u"Estimado/a estudiante, el periodo de matriculación no se encuentra activo")
                    if nivelid == -2:
                        raise NameError(u"Estimado/a estudiante, no existen niveles con cupo para matricularse")
                    if nivelid == -3:
                        raise NameError(u"Estimado/a estudiante, no existen paralelos disponibles")
                    if nivelid == -4:
                        raise NameError(u"Estimado/a estudiante, no existen paralelos para su nivel")
                nivel = Nivel.objects.get(pk=nivelid)

                if not nivel.fechainicioagregacion or not nivel.fechatopematricula or not nivel.fechatopematriculaex or not nivel.fechatopematriculaes:
                    raise NameError(u"Estimado/a estudiante, el proceso de matrícula se encuentra inactivo...")

                if hoy < nivel.fechainicioagregacion:
                    raise NameError(u"Estimado/a estudiante, el proceso de matrícula empieza el %s" % nivel.fechainicioagregacion.__str__())

                if hoy <= nivel.fechatopematriculaes:
                    if hoy > nivel.fechatopematriculaex:
                        raise NameError(u"Estimado/a estudiante, el proceso de matrícula especial termina el %s, favor contactarse a secretaria de su facultad" % nivel.fechatopematriculaes.__str__())
                else:
                    if hoy > nivel.fechatopematriculaes:
                        raise NameError(u"Estimado/a estudiante, el proceso de matrícula especial terminó el %s" % nivel.fechatopematriculaes.__str__())

                if periodomatricula.valida_cronograma:
                    if not puede_matricularse_seguncronograma_coordinacion(inscripcion, nivel.periodo):
                        raise NameError(u"Estimado/a estudiante, aún no está habilitado el cronograma de matriculación de su carrera.")
                else:
                    if periodomatricula.tiene_cronograma_carreras():
                        a = puede_matricularse_seguncronograma_carrera(inscripcion, nivel.periodo)
                        if a[0] == 2:
                            raise NameError(u"Estimado/a estudiante, aún no está habilitado el cronograma de matriculación de su carrera.")
                        if a[0] == 3:
                            raise NameError(u"Estimado/a estudiante, usted no realizó su Pre-Matrícula (matricularse después de dos días de haber iniciado matrícula ordinaria).")
                        if a[0] == 4:
                            log(u"Estimado/a estudiante, el periodo de matriculación no se encuentra activo.... %s" % (inscripcion.info()), request, "add", persona.usuario)
                            raise NameError(u"Estimado/a estudiante, el periodo de matriculación no se encuentra activo")

                # if not nivel.periodo.matriculacionactiva:
                #     raise NameError(u"No esta habilitada la matricula")
                # if not nivel.periodo.matriculacionactiva:
                #    raise NameError(u"El periodo de matriculación no se encuentra activo......")

                malla = None
                inscripcion_malla = inscripcion.malla_inscripcion()
                if not inscripcion.tiene_malla():
                    raise NameError(u"Estimado/a estudiante, debe tener malla asociada para poder matricularse.")
                malla = inscripcion_malla.malla

                if inscripcion.tiene_ultima_matriculas(periodomatricula.num_matriculas):
                    raise NameError(u"Atencion: Estimado/a estudiante, su limite de matricula por perdida de una o mas asignaturas correspondientes a su plan de estudios, ha excedido. Por favor, acercarse a Secretaria de la facultad para mas informacion.")

                if variable_valor('VALIDAR_QUE_SEA_PRIMERA_MATRICULA'):
                    if inscripcion.matricula_set.values('id').filter(status=True).exists():
                        raise NameError(u"Estimado/a estudiante, no puede matricularse; solo apto para primer nivel (nuevos).")

                minivel = inscripcion.mi_nivel().nivel

                asignaturasmalla = AsignaturaMalla.objects.values_list('asignatura_id', flat=True).filter(status=True, malla_id=inscripcion.mi_malla().id)
                fechaultimamateriaprobada = None
                ultimamateriaaprobada = RecordAcademico.objects.filter(inscripcion_id=inscripcion.id, status=True, asignatura_id__in=asignaturasmalla).exclude(noaplica=True).order_by('-fecha')
                if ultimamateriaaprobada:
                    fechaultimamateriaprobada = ultimamateriaaprobada[0].fecha + timedelta(days=1810)
                if fechaultimamateriaprobada:
                    if fechaultimamateriaprobada < nivel.periodo.inicio:
                        raise NameError(u"Reglamento del Régimen Académico - DISPOSICIONES GENERALES: QUINTA.- Si un estudiante no finaliza su carrera o programa y se retira, podrá reingresar a la misma carrera o programa en el tiempo máximo de 5 años contados a partir de la fecha de su retiro. Si no estuviere aplicándose el mismo plan de estudios deberá completar todos los requisitos establecidos en el plan de estudios vigente a la fecha de su reingreso. Cumplido este plazo máximo para el referido reingreso, deberá reiniciar sus estudios en una carrera o programa vigente. En este caso el estudiante podrá homologar a través del mecanismo de validación de conocimientos, las asignaturas, cursos o sus equivalentes, en una carrera o programa vigente, de conformidad con lo establecido en el presente Reglamento.")
                # if inscripcion.matricula_periodo(periodomatricula.periodo):
                #     minivel = inscripcion.matricula_periodo(periodomatricula.periodo).nivelmalla
                if periodomatricula.valida_deuda:
                    tiene_valores_pendientes, msg = get_deuda_persona(persona, periodomatricula)
                    data['tiene_valores_pendientes'] = tiene_valores_pendientes
                    data['msg_valores_pendientes'] = msg

                data['title'] = u"Matriculación Online"
                data['inscripcion'] = inscripcion
                # data['semestre'] = semestre = inscripcion.avance_semestre(minivel)
                data['minivel'] = minivel
                # data['materiasmalla'] = inscripcion_malla.malla.asignaturamalla_set.select_related().all().exclude(nivelmalla_id=NIVEL_MALLA_CERO).order_by('nivelmalla', 'ejeformativo')
                data['nivelesmalla'] = inscripcion_malla.malla.niveles_malla()
                data['tiene_itinerarios'] = inscripcion_malla.malla.tiene_itinerarios()
                data['lista_itinerarios'] = inscripcion_malla.malla.lista_itinerarios()
                data['inscripcionmalla'] = inscripcion.malla_inscripcion()
                data['periodomatricula'] = periodomatricula
                data['matriculacion_libre'] = MATRICULACION_LIBRE
                # data['materiasmaximas'] = MAXIMO_MATERIA_ONLINE
                data['nivel'] = nivel
                data['malla'] = inscripcion_malla.malla
                data['va_ultima_matricula'] = inscripcion.va_ultima_matricula(periodomatricula.num_matriculas)
                data['total_materias_nivel'] = inscripcion.total_materias_nivel()
                data['total_materias_pendientes_malla'] = inscripcion.total_materias_pendientes_malla()
                # data['materiasmodulos'] = inscripcion_malla.malla.modulomalla_set.all()
                # data['utiliza_gratuidades'] = UTILIZA_GRATUIDADES
                # data['porciento_perdida_parcial_gratuidad'] = PORCIENTO_PERDIDA_PARCIAL_GRATUIDAD
                # data['porciento_perdida_total_gratuidad'] = PORCIENTO_PERDIDA_TOTAL_GRATUIDAD
                data['PUEDE_MATRICULARSE_OTRA_VEZ'] = variable_valor('PUEDE_MATRICULARSE_OTRA_VEZ')
                data['fichasocioeconomicainec'] = persona.fichasocioeconomicainec()
                return render(request, "matricula/pregrado_demo/view.html", data)
            except Exception as ex:
                data['msg_error'] = ex.__str__()
                return render(request, "matricula/view.html", data)
