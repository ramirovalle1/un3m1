# -*- coding: latin-1 -*-
import json
import os
from datetime import datetime
import code128
import pyqrcode
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.defaultfilters import floatformat
from django.views.decorators.csrf import csrf_exempt

from bd.models import UserToken, WebSocket
from decorators import secure_module, last_access
from matricula.funciones import valid_intro_module_estudiante, get_nivel_matriculacion, \
    puede_matricularse_seguncronograma_coordinacion, puede_matricularse_seguncronograma_carrera, \
    get_horarios_clases_informacion, get_horarios_clases_data, get_practicas_data, to_unicode, \
    get_horarios_practicas_informacion, get_horarios_practicas_data, valida_conflicto_materias_estudiante, \
    valida_conflicto_materias_estudiante_enroll, TIPO_PROFESOR_PRACTICA, agregacion_aux_pregrado, \
    get_tipo_matricula, calcula_nivel, generateCodeRemoveMateria, reenvioCodeRemoveMateria, \
    generateCodeDeleteMatricula, reenvioCodeDeleteMatricula
from matricula.models import PeriodoMatricula
from settings import SITE_STORAGE, NIVEL_MALLA_CERO, NOTA_ESTADO_EN_CURSO, NOTIFICA_ELIMINACION_MATERIA, \
    FINANCIERO_GROUP_ID, SECRETARIA_GROUP_ID, HOMITIRCAPACIDADHORARIO
from sga.commonviews import adduserdata, obtener_reporte
from sga.funciones import null_to_decimal, log, tituloinstitucion, lista_correo, variable_valor
from sga.models import Matricula, Inscripcion, Nivel, ConfirmarMatricula, Materia, AlumnosPracticaMateria, \
    ProfesorMateria, GruposProfesorMateria, MateriaAsignada, AgregacionEliminacionMaterias, AuditoriaMatricula, \
    CUENTAS_CORREOS, Persona, Periodo
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsavecertificados
from django.db import connections, transaction

from sga.tasks import send_html_mail
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
                    tiene_rubro_pagado = False
                    valor_pagados = 0.0
                    valor_pendiente = 0.0
                    if matricula.rubro_set.values("id").filter(status=True).exists():
                        # total = matricula.total_rubros()
                        tiene_rubro_pagado = matricula.tiene_pagos_matricula()
                        valor_pagados = matricula.total_pagado_rubro()
                        valor_pendiente = matricula.total_saldo_rubro()
                    aMatricula = {"id": matricula.id,
                                  "totalcreditos": str(floatformat(matricula.totalcreditos, 2)),
                                  "totalhoras": matricula.totalhoras,
                                  "promedionotas": str(floatformat(matricula.promedionotas, 2)),
                                  "promedioasistencias": matricula.promedioasistencias,
                                  "retirado": matricula.retirado(),
                                  "nivel": {"id": matricula.nivel.id,
                                            "cerrado": matricula.nivel.cerrado,
                                            },
                                  "tiene_rubro_pagado": tiene_rubro_pagado,
                                  "valor_pagados": valor_pagados,
                                  "valor_pagados_str": str(floatformat(valor_pagados, 2)),
                                  "valor_pendiente": valor_pendiente,
                                  "valor_pendiente_str": str(floatformat(valor_pendiente, 2)),
                                  "puede_quitar": periodomatricula.ver_eliminar_matricula and not tiene_rubro_pagado and matricula.nivel.puede_quitar_materia_matricula(),
                                  "puede_agregar": periodomatricula.puede_agregar_materia and not tiene_rubro_pagado and matricula.nivel.puede_agregar_materia_matricula(),
                                  "tiene_token": matricula.tiene_token_retiro(),
                                  "puede_reenviar_token": matricula.puede_reenviar_email_token(),
                                  "contador_reenviar_email_token": matricula.contador_reenviar_email_token(),
                                  }

                    materiasasignadas = matricula.materiaasignada_set.all().order_by('materia__asignaturamalla__nivelmalla__orden')
                    aMaterias = []
                    for ma in materiasasignadas:
                        totalrecordasignatura = inscripcion.total_record_asignatura(ma.materia.asignatura)
                        nivelmateria = inscripcion.asignatura_en_asignaturamalla(ma.materia.asignatura)
                        practica = {}
                        alumnopracticamateria = ma.alumnopracticamateria()
                        if alumnopracticamateria:
                            if alumnopracticamateria.grupoprofesor:
                                practica['paralelo'] = alumnopracticamateria.grupoprofesor.get_paralelopractica_display()
                        puede_quitar = False
                        if not tiene_rubro_pagado and ma.materia.nivel.puede_quitar_materia_matricula() and totalrecordasignatura <= 2 and not ma.homologada() and not ma.convalidada() and ma.valida_pararecord() and not ma.retirado() and not ma.materia.cerrado and ma.notafinal == 0:
                            puede_quitar = True
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
                                                      "nivelmateria": nivelmateria.nivelmalla.__str__(),
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
                                          "puede_quitar": puede_quitar,
                                          "tiene_token": ma.tiene_token_retiro(),
                                          "puede_reenviar_token": ma.puede_reenviar_email_token(),
                                          "contador_reenviar_email_token": ma.contador_reenviar_email_token(),
                                          # "evaluada": ma.evaluada(),
                                          })

                    inscripcion_malla = inscripcion.malla_inscripcion()
                    record = inscripcion.recordacademico().filter(status=True, aprobada=True, asignaturamalla__isnull=False)
                    asignaturas_malla = inscripcion_malla.malla.asignaturamalla_set.filter(status=True).exclude(nivelmalla_id=NIVEL_MALLA_CERO)
                    asignaturas_malla = asignaturas_malla.exclude(pk__in=materiasasignadas.values_list('materia__asignaturamalla_id', flat=True))
                    asignaturas_malla = asignaturas_malla.exclude(pk__in=record.values_list('asignaturamalla_id', flat=True)).order_by('nivelmalla', 'ejeformativo')
                    va_ultima_matricula = inscripcion.va_ultima_matricula(periodomatricula.num_matriculas)
                    aAsignaturasMalla = []
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
                            if materiasabiertas.count() > 0 and not tiene_rubro_pagado:
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
                        alumnopractica = AlumnosPracticaMateria(materiaasignada=materiaasignada,
                                                                profesormateria=profemate)
                        alumnopractica.save(request)
                        log(u'Materia (%s) con profesor practica (%s) seleccionada matricula: %s en tabla alumnopractica (%s)' % (materia, profemate, materiaasignada, alumnopractica.id), request, "add", persona.usuario)
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
                        log(u'Materia (%s) con grupo profesor practica (%s) seleccionada matricula: %s en tabla alumnopractica (%s)' % (materia, profemate_congrupo, materiaasignada, alumnopractica.id), request, "add", persona.usuario)
                    materiaasignada.matriculas = materiaasignada.cantidad_matriculas()
                    materiaasignada.asistencias()
                    materiaasignada.evaluacion()
                    materiaasignada.mis_planificaciones()
                    materiaasignada.save(request)
                    if matricula.nivel.nivelgrado:
                        log(u'Adiciono materia: %s' % materiaasignada, request, "add", persona.usuario)
                    else:
                        if datetime.now().date() < materia.nivel.fechainicioagregacion:
                            # AGREGACION DE MATERIAS EN MATRICULACION REGULAR SIN REALIZAR PAGOS
                            materiaasignada.save(request)
                            log(u'Adiciono materia: %s' % materiaasignada, request, "add", persona.usuario)
                            # if CALCULO_POR_CREDITO:
                            agregacion_aux_pregrado(request, matricula)
                        elif matricula.nivel.puede_agregar_materia_matricula():
                            # AGREGACION DE MATERIAS EN FECHAS DE AGREGACIONES
                            registro = AgregacionEliminacionMaterias(matricula=matricula,
                                                                     agregacion=True,
                                                                     asignatura=materiaasignada.materia.asignatura,
                                                                     responsable=persona,
                                                                     fecha=datetime.now().date(),
                                                                     creditos=materiaasignada.materia.creditos,
                                                                     nivelmalla=materiaasignada.materia.nivel.nivelmalla if materiaasignada.materia.nivel.nivelmalla else None,
                                                                     matriculas=materiaasignada.matriculas)
                            registro.save(request)
                            log(u'Adiciono materia: %s' % materiaasignada, request, "add", persona.usuario)
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
                            log(u'Adiciono materia: %s' % materiaasignada, request, "add", persona.usuario)
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
                    return JsonResponse({"result": "bad", "mensaje": u"Error, %s" % ex.__str__()})

            elif action == "reenviarRetiroMateria":
                try:
                    if not 'idma' in request.POST:
                        raise NameError(u"Materia no valida")
                    if not MateriaAsignada.objects.values("id").filter(pk=int(request.POST['idma'])).exists():
                        raise NameError(u"Materia no encontrada")
                    materiaasignada = MateriaAsignada.objects.get(pk=int(request.POST['idma']))

                    if not materiaasignada.puede_reenviar_email_token():
                        raise NameError(u"Ha agotado el número máximo de reenvio de correo electrónico por día de la materia")
                    return reenvioCodeRemoveMateria(request, materiaasignada)
                except Exception as ex:
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
                        tokens = materiaasignada.materiaasignadatoken_set.filter(status=True, isActive=True, user_token__isActive=True, user_token__action_type=2, user_token__date_expires__gte=datetime.now())
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
                            log(u'Elimino materia asignada: %s' % materiaasignada, request, "del", persona.usuario)
                            materiaasignada.materia.descontar_cupo_adicional(request)
                            materiaasignada.delete()
                            matricula.actualizar_horas_creditos()
                        else:
                            bandera = 1
                            if matricula.rubro_set.values("id").filter(status=True).exists():
                                if matricula.tiene_pagos_matricula():
                                    raise NameError(u"No puede eliminar ultima materia, porque matricula tiene rubros pagados")
                            log(u'Elimino matricula por ultima materia: %s' % materiaasignada, request, "del", persona.usuario)
                            materiaasignada.delete()
                            matricula.delete()
                    else:
                        if matricula.nivel.fechafinagregacion >= datetime.now().date():
                            if matricula.materiaasignada_set.values('id').filter(status=True).count() > 1:
                                bandera = 0
                                log(u'Elimino materia asignada: %s' % materiaasignada, request, "del", persona.usuario)
                                if NOTIFICA_ELIMINACION_MATERIA:
                                    send_html_mail("Materia eliminada", "emails/materiaeliminada.html", {'sistema': request.session['nombresistema'], 'materia': materia, 'matricula': matricula, 't': tituloinstitucion()}, lista_correo([FINANCIERO_GROUP_ID, SECRETARIA_GROUP_ID]), [], cuenta=CUENTAS_CORREOS[0][1])
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
                        porcentaje_seleccionadas = int(round(Decimal((float(cantidad_nivel) * float(porcentaje_perdidad_parcial_gratuidad)) / 100).quantize(Decimal('.00')), 0))
                        if (cantidad_seleccionadas < porcentaje_seleccionadas):
                            matricula.grupo_socio_economico(2)
                        else:
                            matricula.grupo_socio_economico(1)

                        calcula_nivel(matricula)
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
                        raise NameError(u"Ha agotado el número máximo de reenvio de correo electrónico por día de la matrícula")
                    return reenvioCodeDeleteMatricula(request, matricula)
                except Exception as ex:
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
                            raise NameError(u"No puede eliminar la matricula, porque existen rubros de la matricula ya cancelados.")

                    if not 'utilizaSeguridad' in request.POST:
                        raise NameError(u"Código no valido")
                    utilizaSeguridad = request.POST['utilizaSeguridad'] == 'true'
                    if utilizaSeguridad:
                        if not 'code' in request.POST:
                            raise NameError(u"Código no valido")
                        code = request.POST['code']
                        tokens = matricula.matriculatoken_set.filter(status=True, isActive=True, user_token__isActive=True, user_token__action_type=3, user_token__date_expires__gte=datetime.now())
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
                    log(u'Elimino matricula: %s' % delpersona, request, "del", persona.usuario)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error, %s" % ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
        else:
            try:
                data['title'] = u'Matriculación Online'
                periodomatricula = None
                matricula = None
                if inscripcion.tiene_perdida_carrera():
                    raise NameError(u"ATENCIÓN: Su limite de matricula por perdida de una o mas asignaturas correspondientes a su plan de estudios, ha excedido. Por favor, acercarse a Secretaria para mas informacion.")
                if inscripcion.tiene_cuarta_matricula():
                    raise NameError(u"ATENCIÓN: Su limite de matricula por perdida de una o mas asignaturas correspondientes a su plan de estudios, ha excedido. Por favor, acercarse a Secretaria para mas informacion.")
                if not PeriodoMatricula.objects.values_list('id').filter(status=True, periodo=periodo).exists():
                    raise NameError(u"Estimado/a estudiante, el periodo de matriculación se encuentra inactivo")
                periodomatricula = PeriodoMatricula.objects.filter(status=True, periodo=periodo)
                if periodomatricula.count() > 1:
                    raise NameError(u"Estimado/a estudiante, proceso de matriculación no se encuentra activo")
                periodomatricula = periodomatricula[0]
                if not periodomatricula.esta_periodoactivomatricula():
                    raise NameError(u"Estimado/a estudiante, el periodo de matriculación se encuentra inactivo")
                if periodomatricula.periodo and inscripcion.tiene_automatriculapregrado_por_confirmar(periodomatricula.periodo):
                    return HttpResponseRedirect("/alu_matricula")
                nivelid = get_nivel_matriculacion(inscripcion, periodomatricula.periodo)
                if nivelid < 0:
                    if nivelid == -1:
                        raise NameError(u"Estimado/a estudiante, su carrera no tiene coordinacion o no se encuentra abierto un nivel para su carrera.")
                    if nivelid == -2:
                        raise NameError(u"Estimado/a estudiante, no existen niveles con cupo para matricularse")
                    if nivelid == -3:
                        raise NameError(u"Estimado/a estudiante, no existen paralelos disponibles")
                    if nivelid == -4:
                        raise NameError(u"Estimado/a estudiante, no existen paralelos para su nivel")
                if not Matricula.objects.values('id').filter(inscripcion=inscripcion, nivel__periodo=periodomatricula.periodo).exists():
                    raise NameError(u"ATENCIÓN: Para usar este módulo, debe estar matriculado en el periodo actual: [%s]" % periodomatricula.periodo)

                matricula = Matricula.objects.filter(inscripcion=inscripcion, nivel__periodo=periodomatricula.periodo)[0]
                if not ConfirmarMatricula.objects.filter(matricula=matricula, status=True).exists():
                    raise NameError(u"Estimado estudiante, aún no se encuentra confirmado su matricula")
                nivel = matricula.nivel
                # if hoy > nivel.fechatopematriculaes:
                #     raise NameError(u"Estimado/a estudiante, ya terminó la fecha de matriculación...")
                # if periodomatricula.valida_cronograma:
                #     if not puede_matricularse_seguncronograma_coordinacion(inscripcion, nivel.periodo):
                #         raise NameError(u"Estimado/a estudiante, aún no está habilitado el cronograma de matriculación de su carrera.")
                # else:
                #     if periodomatricula.tiene_cronograma_carreras():
                #         a = puede_matricularse_seguncronograma_carrera(inscripcion, nivel.periodo)
                #         if a[0] == 2:
                #             raise NameError(u"Estimado/a estudiante, aún no está habilitado el cronograma de matriculación de su carrera.")
                #         if a[0] == 3:
                #             raise NameError(u"Estimado/a estudiante, usted no realizó su Pre-Matrícula (matricularse después de dos días de haber iniciado matrícula ordinaria).")
                #         if a[0] == 4:
                #             raise NameError(u"Estimado/a estudiante, el periodo de matriculación no se encuentra activo")
                inscripcion_malla = inscripcion.malla_inscripcion()
                data['matricula'] = matricula
                data['nivel'] = nivel
                data['inscripcion'] = matricula.inscripcion
                data['nivelesmalla'] = inscripcion_malla.malla.niveles_malla()
                data['inscripcionmalla'] = inscripcion.malla_inscripcion()
                data['tiene_itinerarios'] = inscripcion_malla.malla.tiene_itinerarios()
                data['lista_itinerarios'] = inscripcion_malla.malla.lista_itinerarios()
                data['minivel'] = inscripcion.mi_nivel().nivel
                # data['materias'] = materias = matricula.materiaasignada_set.all().order_by('materia__asignaturamalla__nivelmalla__orden')
                data['periodomatricula'] = periodomatricula
                data['fecha_hoy'] = hoy
                data['carrera'] = matricula.inscripcion.carrera.nombre
                data['fichasocioeconomicainec'] = persona.fichasocioeconomicainec()
                data['va_ultima_matricula'] = inscripcion.va_ultima_matricula(periodomatricula.num_matriculas)

                return render(request, "matricula_addremove/pregrado_demo/view.html", data)
            except Exception as ex:
                data['msg_matricula'] = ex.__str__()
                return render(request, "matricula_addremove/view.html", data)
