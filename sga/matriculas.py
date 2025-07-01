# -*- coding: UTF-8 -*-
import json
from _decimal import Decimal
from datetime import datetime
from urllib.request import Request, urlopen

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction, connection
from django.db.models import Q, Sum, Count
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template

from api.serializers.alumno.matriculacion import MatriRequisitoIngresoUnidadIntegracionCurricularSerializer
from inno.models import PeriodoMalla, DetallePeriodoMalla, RequisitoMateriaUnidadIntegracionCurricular, \
    RequisitoIngresoUnidadIntegracionCurricular
from matricula.funciones import get_tipo_matricula, pre_inscripcion_practicas_pre_profesionales
from matricula.models import DetalleRubroMatricula, CostoOptimoMalla, PeriodoMatricula
from moodle import moodle
from decorators import secure_module, last_access
from sagest.models import Rubro, TipoOtroRubro, null_to_decimal
from settings import MAXIMO_MATERIA_ONLINE, RUBRO_ARANCEL, RUBRO_MATRICULA, TIPO_PERIODO_REGULAR
from settings import UTILIZA_NIVEL0_PROPEDEUTICO, MATRICULACION_LIBRE, HOMITIRCAPACIDADHORARIO, CALCULO_POR_CREDITO, \
    MATRICULACION_POR_NIVEL, UTILIZA_GRUPOS_ALUMNOS, UTILIZA_GRATUIDADES, PORCIENTO_PERDIDA_PARCIAL_GRATUIDAD, \
    PORCIENTO_PERDIDA_TOTAL_GRATUIDAD, NOTIFICA_ELIMINACION_MATERIA, NOTA_ESTADO_EN_CURSO, \
    FINANCIERO_GROUP_ID, SECRETARIA_GROUP_ID, MATRICULAR_CON_DEUDA, USA_EVALUACION_INTEGRAL, MATRICULAS_SOLO_TERCERAS, CANTIDAD_MATRICULAS_MAXIMAS, \
    USA_RETIRO_MATERIA, USA_RETIRO_MATRICULA
from sga.commonviews import adduserdata, obtener_reporte, actualizar_nota, materias_abiertas, matricular, \
    conflicto_materias_seleccionadas, contar_nivel, conflicto_materias_estudiante, actualizar_nota_planificacion, \
    get_user_info
from sga.forms import RetiradoMatriculaForm, MatriculaMultipleForm, MoverMatriculaNivelForm, \
    HomologacionInscripcionForm, ConvalidacionInscripcionForm, RetiradoMateriaForm, CambioFechaAsignacionMateriaForm
from sga.funciones import log, tituloinstitucion, MiPaginador, lista_correo, puede_realizar_accion, variable_valor, notificacion_masivo_grupo
from sga.models import Nivel, Carrera, Sede, Matricula, MateriaAsignada, DetalleModificacionNota, RecordAcademico, Materia, Asignatura, \
    Inscripcion, \
    RetiroMatricula, AgregacionEliminacionMaterias, MateriaAsignadaRetiro, HomologacionInscripcion, \
    ConvalidacionInscripcion, MateriaAsignadaConvalidacion, MateriaAsignadaHomologacion, Periodo, DetalleConvenioPago, \
    AsignaturaMalla, PeriodoGrupoSocioEconomico, CUENTAS_CORREOS, TipoProfesor, ProfesorMateria, AlumnosPracticaMateria, \
    GruposProfesorMateria, AsignaturaMallaHomologacion, Malla, Modalidad, Sesion, NivelMalla, Paralelo, \
    DetalleModeloEvaluativo, \
    AuditoriaNotas, PerdidaGratuidad
from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt

unicode = str

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    data['personasesion'] = persona = request.session['persona']
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'deudavencida':
                try:
                    inscripcion = Inscripcion.objects.get(pk=request.POST['iid'])
                    deuda = inscripcion.adeuda_a_la_fecha()
                    if deuda > 0:
                        result = {'result': 'bad', 'deuda': deuda}
                    else:
                        result = {'result': 'ok', 'deuda': deuda}
                    return JsonResponse(result)
                except Exception as ex:
                    pass
                    return JsonResponse({"result": "bad"})

            elif action == 'calcular':
                try:
                    matricula = Matricula.objects.get(pk=request.POST['id'])
                    if not matricula.inscripcion.mi_coordinacion().id in [7, 10]:
                        matricula.agregacion_aux(request)
                        matricula.inscripcion.actualiza_estado_matricula()
                        valid, msg, aData = get_tipo_matricula(None, matricula)
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
                        matricula.calcula_nivel()
                        matricula.aranceldiferido = 2
                        matricula.actacompromiso = None
                        matricula.save(request)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al calcular los rubros."})

            elif action == 'diferir':
                try:
                    eMatricula = Matricula.objects.get(pk=request.POST['id'])
                    ePeriodoMatricula = None
                    if PeriodoMatricula.objects.values('id').filter(status=True, activo=True, periodo=eMatricula.nivel.periodo).exists():
                        ePeriodoMatricula = PeriodoMatricula.objects.get(status=True, activo=True, periodo=eMatricula.nivel.periodo)
                    if not ePeriodoMatricula:
                        raise NameError(u"No se permite diferir arancel")
                    if ePeriodoMatricula.valida_cuotas_rubro and ePeriodoMatricula.num_cuotas_rubro <= 0:
                        raise NameError(u"Periodo acádemico no permite diferir arancel")
                    if not ePeriodoMatricula.tiene_fecha_cuotas_rubro():
                        raise NameError(u"Periodo acádemico no permite diferir arancel")
                    if ePeriodoMatricula.monto_rubro_cuotas == 0:
                        raise NameError(u"Periodo acádemico no permite diferir arancel")
                    if eMatricula.aranceldiferido == 1:
                        raise NameError(u"El rubro arancel ya ha sido diferido. Verifique módulo Mis Finanzas")
                    if not Rubro.objects.values('id').filter(matricula=eMatricula, tipo_id=RUBRO_ARANCEL, status=True).exists():
                        raise NameError(u"No se puede procesar el registro.")
                    arancel = Rubro.objects.filter(matricula=eMatricula, tipo_id=RUBRO_ARANCEL, status=True).first()
                    nombrearancel = arancel.nombre
                    valorarancel = Decimal(arancel.valortotal).quantize(Decimal('.01'))
                    if valorarancel < ePeriodoMatricula.monto_rubro_cuotas:
                        raise NameError(f"Periodo acádemico no permite diferir arancel manor a ${ePeriodoMatricula.monto_rubro_cuotas}")
                    num_cuotas = ePeriodoMatricula.num_cuotas_rubro
                    try:
                        valor_cuota_mensual = (valorarancel / num_cuotas).quantize(Decimal('.01'))
                    except ZeroDivisionError:
                        valor_cuota_mensual = 0
                    if valor_cuota_mensual == 0:
                        raise NameError(u"No se puede procesar el registro.")
                    eRubroMatricula = Rubro.objects.filter(matricula=eMatricula, tipo_id=RUBRO_MATRICULA)[0]
                    eRubroMatricula.relacionados = None
                    eRubroMatricula.save(request)
                    lista = []
                    c = 0
                    for r in ePeriodoMatricula.fecha_cuotas_rubro().values('fecha').distinct():
                        c += 1
                        lista.append([c, valor_cuota_mensual, r['fecha']])
                    for item in lista:
                        rubro = Rubro(tipo_id=RUBRO_ARANCEL,
                                      persona=eMatricula.inscripcion.persona,
                                      relacionados=eRubroMatricula,
                                      matricula=eMatricula,
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
                    arancel.delete()
                    # Matricula.objects.filter(pk=eMatricula.id).update(aranceldiferido=1)
                    url_acta_compromiso = ""
                    if ePeriodoMatricula.valida_rubro_acta_compromiso:
                        isResult, message = eMatricula.generar_actacompromiso_matricula_pregrado(request)
                        if not isResult:
                            raise NameError(message)
                        url_acta_compromiso = message
                        eMatricula.aranceldiferido = 1
                        eMatricula.actacompromiso = url_acta_compromiso
                        eMatricula.save(request)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al calcular los rubros."})

            elif action == 'promotemateria':
                try:
                    matricula = Matricula.objects.get(pk=int(request.POST['idma']))
                    if matricula.inscripcion.bloqueomatricula:
                        return JsonResponse({"result": "bad", "mensaje": u"Estimado estudiante, su matrícula se encuentra bloqueada, por favor contactarse a secretaria de facultad."})
                    materia = Materia.objects.get(pk=int(request.POST['seleccionado']))
                    profesormateria = None
                    grupoprofesormateria = None
                    # covid19
                    # if materia.asignaturamalla.practicas:
                    #     if materia.asignaturamalla.malla.carrera.id.__str__() in variable_valor('LISTA_CARRERA_PARA_MATRICULA_GRUPO_PRACTICA'):
                    #         if not int(request.POST['selecpract']) > 0:
                    #             return JsonResponse({"result": "bad", "mensaje": u"Seleccione un horario de prácticas."})
                    #         else:
                    #             profesormateria = ProfesorMateria.objects.get(pk=int(request.POST['selecpract']), materia=materia)
                    #             if not int(request.POST['selecgrup']) > 0 and profesormateria.grupoprofesormateria():
                    #                 return JsonResponse({"result": "bad", "mensaje": u"Seleccione un horario de prácticas."})
                    #             else:
                    #                 if profesormateria.grupoprofesormateria():
                    #                     grupoprofesormateria = GruposProfesorMateria.objects.get( pk=int(request.POST['selecgrup']), profesormateria__materia=materia,profesormateria=profesormateria)
                    #                     profesormateria = None
                    if matricula.inscripcion.existe_en_malla(materia.asignatura) and not matricula.inscripcion.puede_tomar_materia(materia.asignatura):
                        return JsonResponse({"result": "bad", "mensaje": u"No puede tomar esta materia por tener precedencias"})
                    if matricula.inscripcion.existe_en_modulos(materia.asignatura) and not matricula.inscripcion.puede_tomar_materia_modulo(materia.asignatura):
                        return JsonResponse({"result": "bad", "mensaje": u"No puede tomar esta materia por tener precedencias"})
                    if not materia.modeloevaluativo:
                        return JsonResponse({"result": "bad", "mensaje": u"No tiene modelo evaluativo en el distributivo de la asignatura"})
                    matriculacupoadicional = False
                    #covid19
                    # if MATRICULACION_LIBRE:
                    #     if not materia.tiene_capacidad():
                    #         if materia.cupoadicional > 0:
                    #             if not materia.existen_cupos_con_adicional() :
                    #                 return JsonResponse({"result": "bad", "mensaje": u"No existe cupo adicional para esta materia"})
                    #             else:
                    #                 matriculacupoadicional = True
                    #         else:
                    #             return JsonResponse({"result": "bad", "mensaje": u"No existe cupo para esta materia"})
                    #     if grupoprofesormateria:
                    #         if not grupoprofesormateria.cuposdisponiblesgrupoprofesor()>0:
                    #             return JsonResponse({"result": "bad", "mensaje": u"No existe cupo para en la practica"})
                    if matricula.materiaasignada_set.values('id').filter(materia=materia, status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya se encuentra matriculado en esta materia"})
                    elif matricula.materiaasignada_set.values('id').filter(materia=materia, status=False).exists():
                        materiaasig = MateriaAsignada.objects.get(matricula=matricula, materia=materia, status=False)
                        materiaasig.status = True
                        materiaasig.save(request)
                        log(u'Adiciono materia: %s' % materiaasig, request, "add")
                        return JsonResponse({"result": "ok"})
                    if materia.inglesepunemi:
                        materiaasignada = MateriaAsignada(matricula=matricula,
                                                          materia=materia,
                                                          notafinal=0,
                                                          asistenciafinal=100,
                                                          cerrado=False,
                                                          automatricula=True,
                                                          importa_nota=True,
                                                          observaciones='',
                                                          estado_id=NOTA_ESTADO_EN_CURSO)
                        materiaasignada.save(request)
                        matriculas = matricula.inscripcion.historicorecordacademico_set.filter(asignatura=materia.asignatura).count() + 1
                        if matriculas > 1 or matricula.inscripcion.persona.tiene_otro_titulo(matricula.inscripcion):
                            matricula.nuevo_calculo_matricula_ingles(materiaasignada)
                    else:
                        if matricula.inscripcion.carrera.modalidad == 3:
                            materiaasignada = MateriaAsignada(matricula=matricula,
                                                          materia=materia,
                                                          notafinal=0,
                                                          sinasistencia=True,
                                                          asistenciafinal=100,
                                                          cerrado=False,
                                                          observaciones='',
                                                          estado_id=NOTA_ESTADO_EN_CURSO)
                        else:
                            materiaasignada = MateriaAsignada(matricula=matricula,
                                                          materia=materia,
                                                          notafinal=0,
                                                          asistenciafinal=0,
                                                          cerrado=False,
                                                          observaciones='',
                                                          estado_id=NOTA_ESTADO_EN_CURSO)
                        materiaasignada.save(request)
                    if matriculacupoadicional:
                        materia.totalmatriculadocupoadicional += 1
                        materia.cupo += 1
                        materia.save(request)
                        log(u'Estudiante matriculado en cupo adicional materia: %s - estudiante: %s y se aumento un cupo en materia' % (materia, matricula), request, "add")
                    if profesormateria:
                        alumnopractica = AlumnosPracticaMateria(materiaasignada=materiaasignada, profesormateria=profesormateria)
                        alumnopractica.save(request)
                        log(u'Materia (%s) con profesor practica (%s) seleccionada matricula: %s en tabla alumnopractica (%s)' % (materia, profesormateria, materiaasignada, alumnopractica.id), request, "add")
                    elif grupoprofesormateria:
                        alumnopractica = AlumnosPracticaMateria(materiaasignada=materiaasignada, profesormateria=grupoprofesormateria.profesormateria, grupoprofesor=grupoprofesormateria)
                        alumnopractica.save(request)
                        log(u'Materia (%s) con grupo profesor practica (%s) seleccionada matricula: %s en tabla alumnopractica (%s) por modulo de inscripciones' % ( materia, grupoprofesormateria, materiaasignada, alumnopractica.id), request, "add")
                    matricula.actualizar_horas_creditos()
                    #covid19
                    # conflicto = matricula.verificar_conflicto_en_materias()
                    # if conflicto:
                    #     transaction.set_rollback(True)
                    #     return JsonResponse({"result": "bad", "mensaje": conflicto})
                    materiaasignada.matriculas = materiaasignada.cantidad_matriculas()
                    materiaasignada.asistencias()
                    materiaasignada.evaluacion()
                    materiaasignada.mis_planificaciones()
                    materiaasignada.save(request)
                    if matricula.nivel.nivelgrado:
                        log(u'Adiciono materia: %s' % materiaasignada, request, "add")
                    else:
                        if datetime.now().date() < matricula.nivel.periodo.inicio_agregacion:
                            # AGREGACION DE MATERIAS EN MATRICULACION REGULAR SIN REALIZAR PAGOS
                            materiaasignada.save(request)
                            log(u'Adiciono materia: %s' % materiaasignada, request, "add")
                            if CALCULO_POR_CREDITO and not materia.inglesepunemi  and not materia.coordinacion().id in [7,9]:
                                matricula.agregacion_aux(request)
                                matricula.inscripcion.actualiza_estado_matricula()
                                valid, msg, aData = get_tipo_matricula(None, matricula)
                                if not valid:
                                    raise NameError(msg)
                                cantidad_nivel = aData['cantidad_nivel']
                                porcentaje_perdidad_parcial_gratuidad = aData['porcentaje_perdidad_parcial_gratuidad']
                                cantidad_seleccionadas = aData['cantidad_seleccionadas']
                                porcentaje_seleccionadas = int(round(
                                    Decimal((float(cantidad_nivel) * float(
                                        porcentaje_perdidad_parcial_gratuidad)) / 100).quantize(
                                        Decimal('.00')), 0))
                                if (cantidad_seleccionadas < porcentaje_seleccionadas):
                                    matricula.grupo_socio_economico(2)
                                else:
                                    matricula.grupo_socio_economico(1)
                                # matricula.calcular_rubros_matricula(cobro)
                        elif matricula.nivel.periodo.fecha_agregaciones():
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
                            if CALCULO_POR_CREDITO and not materia.inglesepunemi and not materia.coordinacion().id in [7,9]:
                                matricula.agregacion_aux(request)
                                matricula.inscripcion.actualiza_estado_matricula()
                                valid, msg, aData = get_tipo_matricula(None, matricula)
                                if not valid:
                                    raise NameError(msg)
                                cantidad_nivel = aData['cantidad_nivel']
                                porcentaje_perdidad_parcial_gratuidad = aData['porcentaje_perdidad_parcial_gratuidad']
                                cantidad_seleccionadas = aData['cantidad_seleccionadas']
                                porcentaje_seleccionadas = int(round(
                                    Decimal((float(cantidad_nivel) * float(
                                        porcentaje_perdidad_parcial_gratuidad)) / 100).quantize(
                                        Decimal('.00')), 0))
                                if (cantidad_seleccionadas < porcentaje_seleccionadas):
                                    matricula.grupo_socio_economico(2)
                                else:
                                    matricula.grupo_socio_economico(1)
                        else:
                            # AGREGACION DE MATERIAS TERMINADA LAS AGREGACIONES
                            if materia.asignatura.modulo:
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
                                if CALCULO_POR_CREDITO and not materia.inglesepunemi  and not materia.coordinacion().id in [7,9]:
                                    matricula.agregacion_aux(request)
                                    matricula.inscripcion.actualiza_estado_matricula()
                                    valid, msg, aData = get_tipo_matricula(None, matricula)
                                    if not valid:
                                        raise NameError(msg)
                                    cantidad_nivel = aData['cantidad_nivel']
                                    porcentaje_perdidad_parcial_gratuidad = aData[
                                        'porcentaje_perdidad_parcial_gratuidad']
                                    cantidad_seleccionadas = aData['cantidad_seleccionadas']
                                    porcentaje_seleccionadas = int(round(
                                        Decimal((float(cantidad_nivel) * float(
                                            porcentaje_perdidad_parcial_gratuidad)) / 100).quantize(
                                            Decimal('.00')), 0))
                                    if (cantidad_seleccionadas < porcentaje_seleccionadas):
                                        matricula.grupo_socio_economico(2)
                                    else:
                                        matricula.grupo_socio_economico(1)
                            # else:
                            #      raise NameError('Error')
                    # del request.session['matricula']
                    # del request.session['periodos_estudiante']
                    # del request.session['periodo']
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al agregar la materia %s" %ex})

            elif action == 'conflictohorario':
                mismaterias = json.loads(request.POST['mismaterias'])
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                mispracticas = json.loads(request.POST['mispracticas'])
                excluidas = Asignatura.objects.filter(historicorecordacademico__inscripcion=inscripcion, historicorecordacademico__aprobada=False, historicorecordacademico__sinasistencia=True).distinct()
                materias = Materia.objects.filter(id__in=[int(x) for x in mismaterias]).exclude(asignatura__id__in=excluidas)
                # extraermos los datos de la lista profesormnaterias y paralelo
                listaprofemateriaid_singrupo = []
                listaprofemateriaid_congrupo = []
                for x in mispracticas:
                    if not int(x[1]) > 0:
                        listaprofemateriaid_singrupo.append(int(x[0]))
                    else:
                        listaprofemateriaid_congrupo.append([int(x[0]), int(x[1])])
                profemate = ProfesorMateria.objects.filter(id__in=listaprofemateriaid_singrupo, materia__in=materias)
                nivel = contar_nivel(mismaterias)
                conflicto = conflicto_materias_estudiante(materias, profemate, listaprofemateriaid_congrupo)
                if conflicto:
                    return JsonResponse({"result": "bad", "mensaje": conflicto})
                # EXTRAMOS LOS DATOS DE LA MATERIA SELECCIONADA
                datos = {}
                if 'idm' in request.POST:
                    datos = Materia.objects.get(pk=int(request.POST['idm'])).datos_practicas_materia(inscripcion)
                return JsonResponse({"result": "ok", "nivel": nivel, "datos": datos})

            elif action == 'conflictohorario_aux':
                nivel = 0
                mismaterias = json.loads(request.POST['mismaterias'])
                if len(mismaterias) > 0:
                    nivel = contar_nivel(mismaterias)
                return JsonResponse({"result": "ok", "nivel" : nivel})

            elif action == 'addmatriculamulti':
                try:
                    form = MatriculaMultipleForm(request.POST)
                    f = form
                    if f.is_valid():
                        nivel = Nivel.objects.get(pk=request.POST['nivelrpocedencia'])
                        fecha = datetime.now().date()
                        if fecha > nivel.fechatopematriculaes:
                            return JsonResponse({"result": "bad", "mensaje": u"Fuera de rago de fecha de matriculacion extraordinaria."})
                        if nivel.matricula_set.all().count() >= nivel.capacidadmatricula:
                            return JsonResponse({"result": "bad", "mensaje": u"Limite de matriculas para el paralelo."})
                        lista = request.POST.getlist('ins')
                        for inscripcion_id in lista:
                            inscripcion = Inscripcion.objects.get(pk=int(inscripcion_id))
                            if not inscripcion.matriculado():
                                if inscripcion.persona.tiene_deuda():
                                    transaction.set_rollback(True)
                                    return JsonResponse({"result": "bad", "mensaje": u"El estudiante: " + unicode(inscripcion.persona.nombre_completo()) + " Tiene rubros pendientes de pago."})
                                if inscripcion.tiene_perdida_carrera():
                                    transaction.set_rollback(True)
                                    return JsonResponse({"result": "bad", "mensaje": u"El estudiante: " + unicode(inscripcion.persona.nombre_completo()) + " tiene perdida de carrera."})
                                matricula = Matricula(inscripcion=inscripcion,
                                                      nivel=nivel,
                                                      pago=False,
                                                      iece=False,
                                                      becado=False,
                                                      porcientobeca=0,
                                                      fecha=datetime.now().date(),
                                                      hora=datetime.now().time())
                                matricula.save(request)
                                log(u'Adiciono matricula multiple: %s' % matricula, request, "add")
                                nivel = matricula.nivel
                                materias = nivel.materia_set.filter(Q(cerrado=False) | Q(cerrado=None))
                                inscripcion = matricula.inscripcion
                                tercera = inscripcion.tiene_tercera_matricula()
                                for materia in materias:
                                    if not inscripcion.ya_aprobada(materia.asignatura) and inscripcion.puede_tomar_materia(materia.asignatura):
                                        adicionar = True
                                        if tercera and MATRICULAS_SOLO_TERCERAS:
                                            if not inscripcion.cantidad_matriculas(materia.asignatura) == CANTIDAD_MATRICULAS_MAXIMAS:
                                                adicionar = False
                                        if adicionar:
                                            materiaasignada = MateriaAsignada(matricula=matricula,
                                                                              materia=materia,
                                                                              notafinal=0,
                                                                              cerrado=False,
                                                                              asistenciafinal=0,
                                                                              observaciones='',
                                                                              estado_id=NOTA_ESTADO_EN_CURSO)
                                            materiaasignada.save(request)
                                            log(u'Adiciono materia asignada: %s' % materiaasignada, request, "add")
                                            materiaasignada.matriculas = materiaasignada.cantidad_matriculas()
                                            materiaasignada.save(request)
                                            materiaasignada.evaluacion()
                                            materiaasignada.asistencias()
                                            materiaasignada.mis_planificaciones()
                                matricula.calcular_rubros_matricula()
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al matricular los estudiantes."})

            elif action == 'delmateria':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=request.POST['id'])
                    matricula = materiaasignada.matricula
                    # if Rubro.objects.filter(matricula=matricula, status=True, cancelado=True).exists():
                    #     return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar materias, porque existen rubros de la matricula cancelados"})
                    # else:
                    materia = materiaasignada.materia
                    if materia.asignaturamalla.asignaturapracticas:
                        pre_inscripcion_practicas_pre_profesionales(request, materiaasignada, matricula, None, 'deladm')
                    if matricula.nivel.nivelgrado:
                        if matricula.materiaasignada_set.values('id').filter(status=True).count() > 1:
                            bandera = 0
                            log(u'Elimino materia asignada: %s' % materiaasignada, request, "del")
                            materiaasignada.materia.descontar_cupo_adicional(request)
                            materiaasignada.delete()
                            matricula.actualizar_horas_creditos()
                        else:
                            bandera = 1
                            rubro = Rubro.objects.filter(matricula=matricula, status=True)
                            if not matricula.inscripcion.carrera.mi_coordinacion2() == 7:
                                if rubro:
                                    if rubro[0].tiene_pagos():
                                        transaction.set_rollback(True)
                                        return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar ultima materia, porque matricula tiene rubros pagados"})
                            log(u'Elimino matricula por ultima materia: %s' % materiaasignada, request, "del")
                            materiaasignada.materia.descontar_cupo_adicional(request)
                            materiaasignada.delete()
                            matricula.delete()
                    else:
                        if matricula.nivel.periodo.fecha_agregaciones():
                            if matricula.materiaasignada_set.values('id').filter(status=True).count() > 1:
                                bandera = 0
                                log(u'Elimino materia asignada: %s' % materiaasignada, request, "del")
                                if NOTIFICA_ELIMINACION_MATERIA:
                                    send_html_mail("Materia eliminada", "emails/materiaeliminada.html", {'sistema': request.session['nombresistema'], 'materia': materia, 'matricula': matricula, 't': tituloinstitucion()}, lista_correo([FINANCIERO_GROUP_ID, SECRETARIA_GROUP_ID]), [], cuenta=CUENTAS_CORREOS[5][1])
                                materiaasignada.materia.descontar_cupo_adicional(request)
                                matricula.eliminar_materia(materiaasignada, request)
                                matricula.actualizar_horas_creditos()
                                matricula.aranceldiferido=2
                                matricula.actacompromiso=None
                                matricula.save(request)
                            else:
                                bandera = 1
                                rubro = Rubro.objects.filter(matricula=matricula, status=True)
                                if rubro and matricula.inscripcion.carrera.mi_coordinacion2() != 7:
                                    if not matricula.inscripcion.carrera.mi_coordinacion2() == 7:
                                        if rubro[0].tiene_pagos():
                                            transaction.set_rollback(True)
                                            return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar ultima materia, porque matricula tiene rubros pagados"})
                                    log(u'Elimino matricula por ultima materia: %s' % materiaasignada, request, "del")
                                    materiaasignada.materia.descontar_cupo_adicional(request)
                                    matricula.eliminar_materia(materiaasignada, request)
                                    matricula.delete()
                                else:
                                    log(u'Elimino materia asignada: %s' % materiaasignada, request, "del")
                                    materiaasignada.materia.descontar_cupo_adicional(request)
                                    matricula.eliminar_materia(materiaasignada, request)
                                    matricula.actualizar_horas_creditos()
                                    matricula.aranceldiferido = 2
                                    matricula.actacompromiso = None
                                    matricula.save(request)
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar materias fuera de las fecha de agregaciones"})
                    if CALCULO_POR_CREDITO and not materia.coordinacion().id in [7,9]:
                        if bandera == 0:
                            matricula.agregacion_aux(request)
                            matricula.inscripcion.actualiza_estado_matricula()
                            valid, msg, aData = get_tipo_matricula(None, matricula)
                            if not valid:
                                raise NameError(msg)
                            cantidad_nivel = aData['cantidad_nivel']
                            porcentaje_perdidad_parcial_gratuidad = aData['porcentaje_perdidad_parcial_gratuidad']
                            cantidad_seleccionadas = aData['cantidad_seleccionadas']
                            porcentaje_seleccionadas = int(round(
                                Decimal((float(cantidad_nivel) * float(
                                    porcentaje_perdidad_parcial_gratuidad)) / 100).quantize(
                                    Decimal('.00')), 0))
                            if (cantidad_seleccionadas < porcentaje_seleccionadas):
                                matricula.grupo_socio_economico(2)
                            else:
                                matricula.grupo_socio_economico(1)
                            matricula.aranceldiferido = 2
                            matricula.actacompromiso = None
                            matricula.save(request)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar la materia. %s" % ex})

            elif action == 'sinasistencia':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=request.POST['id'])
                    materiaasignada.sinasistencia = True
                    materiaasignada.save(request)
                    materiaasignada.actualiza_estado()
                    log(u'Modifico estado asistencia: %s' % materiaasignada, request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'conasistencia':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=request.POST['id'])
                    materiaasignada.sinasistencia = False
                    materiaasignada.save(request)
                    materiaasignada.actualiza_estado()
                    log(u'Modifico estado asistencia: %s' % materiaasignada, request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'autorizarevaluacion':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=request.POST['id'])
                    materiaasignada.evaluar = True
                    materiaasignada.fechaevaluar = datetime.now()
                    materiaasignada.save(request)
                    log(u'Autorizo evaluacion: %s' % materiaasignada, request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'delmatricula':
                try:
                    matricula = Matricula.objects.get(pk=request.POST['id'])
                    rubro = Rubro.objects.filter(matricula=matricula, status=True).order_by('id')

                    if rubro and matricula.inscripcion.carrera.mi_coordinacion2() != 7:
                        for r in rubro:
                            if r.tiene_pagos():
                                return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar la matricula, porque existen rubros de la matricula ya cancelados."})
                    else:
                        if matricula.inscripcion.carrera.mi_coordinacion2() == 7:
                            for r in rubro:
                                r.matricula = None
                                r.save()
                        #if rubro[0].tiene_pagos():
                        #    return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar la matricula, porque existen rubros de la matricula ya cancelados."})
                    inscripcion = matricula.inscripcion
                    for materiaasignada in matricula.materiaasignada_set.all():
                        materiaasignada.delete()
                    log(u'Elimino matricula: %s' % matricula, request, "del")
                    # esta validacion esta para los de POSTGRADO, para que su convenio de pago sea desaprobado
                    if Periodo.objects.values('id').filter(pk=matricula.nivel.periodo.id, nombre__icontains='IPEC').exists():
                        if DetalleConvenioPago.objects.values('id').filter(inscripcion=inscripcion, status=True).exists():
                            detalleconveniopago = DetalleConvenioPago.objects.filter(inscripcion=inscripcion, status=True)[0]
                            detalleconveniopago.aprobado = False
                            detalleconveniopago.save(request)
                    matricula.delete()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'retirar':
                try:
                    matricula = Matricula.objects.get(pk=request.POST['id'])
                    f = RetiradoMatriculaForm(request.POST)
                    if f.is_valid():
                        if not matricula.retirado():
                            matricula.retiro_academico(f.cleaned_data['motivo'],request)
                            log(u'Retiro la matricula: %s' % matricula, request, "edit")
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Ya se encuentra retirado de la matricula."})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s"%ex})

            elif action == 'retirarmateria':
                try:
                    materia = MateriaAsignada.objects.get(pk=request.POST['id'])
                    f = RetiradoMateriaForm(request.POST)
                    if f.is_valid():
                        if not materia.retirado():
                            retiro = MateriaAsignadaRetiro(materiaasignada=materia,
                                                           motivo=f.cleaned_data['motivo'],
                                                           valida=False,
                                                           fecha=datetime.now().date())
                            retiro.save(request)
                            materia.retiramateria = True
                            materia.save(request)
                            log(u'Retiro de materia: %s' % retiro, request, "edit")
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Ya se encuentra retirado de la materia."})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'materiasabiertas':
                return materias_abiertas(request, True, True)

            elif action == 'moveranivel':
                try:
                    matricula = Matricula.objects.get(pk=request.POST['id'])
                    f = MoverMatriculaNivelForm(request.POST)
                    if f.is_valid():
                        nuevonivel = f.cleaned_data['nivel']
                        if matricula.nivel != nuevonivel:
                            for ma in matricula.materiaasignada_set.all():
                                if nuevonivel.materia_set.values('id').filter(asignatura=ma.materia.asignatura).exists():
                                    materiaexistente = nuevonivel.materia_set.filter(asignatura=ma.materia.asignatura)[0]
                                    materianueva = MateriaAsignada(matricula=matricula,
                                                                   materia=materiaexistente,
                                                                   notafinal=0,
                                                                   asistenciafinal=0,
                                                                   observaciones='',
                                                                   fechaasignacion=datetime.now().date(),
                                                                   estado_id=NOTA_ESTADO_EN_CURSO)
                                    materianueva.save(request)
                                    materianueva.matriculas = materianueva.cantidad_matriculas()
                                    materianueva.save(request)
                                    materianueva.asistencias()
                                    ma.delete()
                            matricula.nivel = nuevonivel
                            matricula.save(request)
                            conflicto = matricula.verificar_conflicto_en_materias()
                            if conflicto:
                                transaction.set_rollback(True)
                                return JsonResponse({"result": "bad", "mensaje": conflicto})
                        if UTILIZA_GRUPOS_ALUMNOS and not MATRICULACION_POR_NIVEL:
                            matricula.inscripcion.inscripcion_grupo(nuevonivel.grupo)
                        matricula.actualizar_horas_creditos()
                        log(u'Cambio de nivel: %s' % matricula, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'matricular':
                return matricular(request, True, False)

            if action == 'movermateriasession':
                try:
                    profesormateria = None
                    matriculacupoadicional = False
                    estudiantepractica = None
                    grupoprofesormateria=None
                    materia = Materia.objects.get(pk=request.POST['mid'])
                    materiaasignada = MateriaAsignada.objects.get(pk=request.POST['maid'])
                    if materia.asignaturamalla.practicas:
                        if materiaasignada.materia.asignaturamalla.malla.carrera.id.__str__() in variable_valor('LISTA_CARRERA_PARA_MATRICULA_GRUPO_PRACTICA'):
                            if not int(request.POST['idp']) > 0:
                                return JsonResponse({"result": "bad", "mensaje": u"Seleccione un horario de prácticas."})
                            else:
                                profesormateria = ProfesorMateria.objects.get(pk=int(request.POST['idp']), materia=materia)
                                if not int(request.POST['idg']) > 0 and profesormateria.grupoprofesormateria() :
                                    return JsonResponse({"result": "bad", "mensaje": u"Seleccione un horario de prácticas."})
                                else:
                                    if profesormateria.grupoprofesormateria():
                                        grupoprofesormateria = GruposProfesorMateria.objects.get(pk=int(request.POST['idg']), profesormateria__materia=materia, profesormateria = profesormateria)
                                        profesormateria = None
                    if MATRICULACION_LIBRE:
                        if not materia.tiene_capacidad():
                            if materia.cupoadicional > 0:
                                if not materia.existen_cupos_con_adicional() :
                                    return JsonResponse({"result": "bad", "mensaje": u"No existe cupo adicional para esta materia"})
                                else:
                                    matriculacupoadicional = True
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"No existe cupo para esta materia"})
                        if grupoprofesormateria:
                            if not grupoprofesormateria.cuposdisponiblesgrupoprofesor()>0:
                                return JsonResponse({"result": "bad", "mensaje": u"No existe cupo para en la práctica"})
                    if AlumnosPracticaMateria.objects.values('id').filter(materiaasignada=materiaasignada).exists():
                        estudiantepractica= AlumnosPracticaMateria.objects.get(materiaasignada=materiaasignada, status=True)
                    asistencias = materiaasignada.asistencialeccion_set.all()
                    asistencias.delete()
                    evaluaciones = materiaasignada.evaluacion()
                    evaluaciones.delete()
                    materiaasignada.materia.descontar_cupo_adicional(request)
                    materiaasignada.materia = materia
                    materiaasignada.save(request)
                    materiaasignada.notafinal = 0
                    materiaasignada.fechaasignacion = datetime.now().date()
                    materiaasignada.asistenciafinal = 100
                    materiaasignada.save(request)
                    if matriculacupoadicional:
                        materia.totalmatriculadocupoadicional += 1
                        materia.cupo += 1
                        materia.save(request)
                        log(u'Estudiante matriculado en cupo adicional materia: %s - estudiante: %s y se aumento un cupo en materia' % (materia, materiaasignada.matricula), request, "add")
                    if estudiantepractica:
                        if profesormateria:
                            actual = estudiantepractica.profesormateria
                            estudiantepractica.profesormateria = profesormateria
                            estudiantepractica.grupoprofesor = None
                            estudiantepractica.save(request)
                            log(u'Cambio de profesor de practica actual(%s) y nuevo(%s)' % (actual, profesormateria), request, "edit")
                        elif grupoprofesormateria:
                            actual = estudiantepractica.profesormateria
                            estudiantepractica.profesormateria = grupoprofesormateria.profesormateria
                            estudiantepractica.grupoprofesor = grupoprofesormateria
                            estudiantepractica.save(request)
                            log(u'Cambio de profesor de practica actual(%s) y nuevo(%s) y se adiciono grupoprofesor(%s)' % (actual, profesormateria, estudiantepractica.grupoprofesor),request, "edit")
                        else:
                            estudiantepractica.delete()
                            log(u'Se elimino porque ya no se va a utilizar: %s - materia asig %s - profesormat %s' % (estudiantepractica.id, estudiantepractica.materiaasignada, estudiantepractica.profesormateria), request, "edit")
                    else:
                        if profesormateria:
                            alumnopract = AlumnosPracticaMateria.objects.get(materiaasignada=materiaasignada, status=True)
                            alumnopract.save(request)
                            log(u'Adiciono alumno a practica %s - [%s-%s]' % (alumnopract.id, alumnopract.materiaasignada, alumnopract.profesormateria),request, "edit")
                        elif grupoprofesormateria:
                            alumnopractica = AlumnosPracticaMateria(materiaasignada=materiaasignada, profesormateria=grupoprofesormateria.profesormateria, grupoprofesor=grupoprofesormateria)
                            alumnopractica.save(request)
                            log(u'Materia (%s) con grupo profesor practica (%s) seleccionada matricula: %s en tabla alumnopractica (%s) cambio de paralelo a la materia' % (materia, grupoprofesormateria, materiaasignada, alumnopractica.id), request, "add")
                    if materia.asignaturamalla.malla.carrera.modalidad != 3:
                        conflicto = materiaasignada.matricula.verificar_conflicto_en_materias()
                        if conflicto:
                            transaction.set_rollback(True)
                            return JsonResponse({"result": "bad", "mensaje": conflicto})
                    materiaasignada.asistencias()
                    materiaasignada.evaluacion()
                    materiaasignada.mis_planificaciones()
                    ematricula = materiaasignada.matricula
                    ematricula.actualizar_horas_creditos()
                    # if materiaasignada.materia.inglesepunemi:
                    #     if materiaasignada.matriculas>1 or ematricula.inscripcion.persona.tiene_otro_titulo(ematricula.inscripcion):
                    #         ematricula.nuevo_calculo_matricula_ingles(materiaasignada)
                    # else:
                    #     ematricula.agregacion_aux(request)
                    ematricula.inscripcion.actualiza_estado_matricula()
                    if not ematricula.inscripcion.mi_coordinacion().id in [7, 10]:
                        valid, msg, aData = get_tipo_matricula(None, ematricula)
                        if not valid:
                            raise NameError(msg)
                        cantidad_nivel = aData['cantidad_nivel']
                        porcentaje_perdidad_parcial_gratuidad = aData['porcentaje_perdidad_parcial_gratuidad']
                        cantidad_seleccionadas = aData['cantidad_seleccionadas']
                        porcentaje_seleccionadas = int(round(
                            Decimal((float(cantidad_nivel) * float(porcentaje_perdidad_parcial_gratuidad)) / 100).quantize(
                                Decimal('.00')), 0))
                        if (cantidad_seleccionadas < porcentaje_seleccionadas):
                            materiaasignada.matricula.grupo_socio_economico(2)
                        else:
                            materiaasignada.matricula.grupo_socio_economico(1)
                    materiaasignada.matricula.calcula_nivel()
                    log(u'Cambio seccion materia: %s' % materiaasignada, request, "del")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'auditoria':
                try:
                    data['auditoriadetalle']=auditoria = DetalleModificacionNota.objects.filter(pk=request.POST['id'])

                except Exception as ex:
                    pass
            elif action == 'nota':
                try:
                    persona = request.session['persona']
                    materiaasignada = MateriaAsignada.objects.filter(pk=request.POST['maid']).first()
                    auditoria = DetalleModificacionNota(materiaasignada_id=request.POST['maid'], campo=request.POST['sel'], notaanterior=request.POST['unidad'],notaactual=request.POST['val'])
                    auditoria.save(request)
                    inscripcion = materiaasignada.matricula.inscripcion.persona
                    mensaje = f"Se modificó la nota correspondiente al {request.POST['sel'].upper()} {'de la' if inscripcion.es_mujer() else 'del'} alumn{'a' if inscripcion.es_mujer() else 'o'} {inscripcion} en la materia de {materiaasignada.materia} del periodo {materiaasignada.materia.nivel.periodo} por {'la' if persona.es_mujer() else 'el'} {request.session['perfilprincipal']}, {persona}"
                    log_message = (f"{mensaje} Nota anterior {request.POST['unidad']} - Nota Actual {request.POST['val']}")
                    log(log_message, request, 'edit')
                    notificacion_masivo_grupo(u"Modificación de notas", mensaje, 49,f'/matriculas?action=calificaciontardia&id={materiaasignada.id}',materiaasignada.pk, 1, 'sga', materiaasignada)
                    result = actualizar_nota(request)
                    correo_datos_adicionales = {
                        'sel': request.POST['sel'].upper(),
                        'genero': "de la" if inscripcion.es_mujer() else "del",
                        'estud': "a" if inscripcion.es_mujer() else "o",
                        'inscripcion': inscripcion,
                        'materia': materiaasignada.materia.asignatura.nombre,
                        'periodo': materiaasignada.materia.nivel.periodo.nombre,
                        'genero2': "la" if persona.es_mujer() else "el",
                        'perfil': request.session['perfilprincipal'],
                        'persona': persona,
                        'nota_anterior': request.POST['unidad'],
                        'nota_actual': request.POST['val']
                    }
                    send_html_mail(f"Actualizacion de Nota", "emails/cambio_notas.html",
                                   {'context': correo_datos_adicionales,
                                    'user_info': get_user_info(request)},
                                   persona.lista_emails_envio(),
                                   ['sga@unemi.edu.ec'], [],
                                   cuenta=CUENTAS_CORREOS[16][1])
                    return JsonResponse(result)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'homologar':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=request.POST['id'])
                    f = HomologacionInscripcionForm(request.POST)
                    if f.is_valid():
                        if materiaasignada.materiaasignadahomologacion_set.values('id').exists():
                            materiaasignadahomologacion = materiaasignada.materiaasignadahomologacion_set.all()[0]
                            homologacion = materiaasignadahomologacion.homologacion
                            homologacion.carrera = f.cleaned_data['carrera']
                            homologacion.asignatura = f.cleaned_data['asignatura']
                            homologacion.fecha = f.cleaned_data['fecha']
                            homologacion.nota_ant = f.cleaned_data['nota_ant']
                            homologacion.observaciones = f.cleaned_data['observaciones']
                            homologacion.creditos = f.cleaned_data['creditos']
                            homologacion.save(request)
                        else:
                            homologacion = HomologacionInscripcion(carrera=f.cleaned_data['carrera'],
                                                                   asignatura=f.cleaned_data['asignatura'],
                                                                   fecha=f.cleaned_data['fecha'],
                                                                   nota_ant=f.cleaned_data['nota_ant'],
                                                                   observaciones=f.cleaned_data['observaciones'],
                                                                   creditos=f.cleaned_data['creditos'])
                            homologacion.save(request)
                            materiaasignadahomologacion = MateriaAsignadaHomologacion(materiaasignada=materiaasignada,
                                                                                      homologacion=homologacion)
                            materiaasignadahomologacion.save(request)
                        log(u'Adicionada homologacion: %s' % homologacion, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'convalidar':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=request.POST['id'])
                    f = ConvalidacionInscripcionForm(request.POST)
                    if f.is_valid():
                        if materiaasignada.materiaasignadaconvalidacion_set.values('id').exists():
                            materiaasignadaconvalidacion = materiaasignada.materiaasignadaconvalidacion_set.all()[0]
                            convalidacion = materiaasignadaconvalidacion.convalidacion
                            convalidacion.centro = f.cleaned_data['centro']
                            convalidacion.carrera = f.cleaned_data['carrera']
                            convalidacion.asignatura = f.cleaned_data['asignatura']
                            convalidacion.anno = f.cleaned_data['anno']
                            convalidacion.nota_ant = f.cleaned_data['nota_ant']
                            convalidacion.nota_act = f.cleaned_data['nota_act']
                            convalidacion.observaciones = f.cleaned_data['observaciones']
                            convalidacion.creditos = f.cleaned_data['creditos']
                            convalidacion.save(request)
                        else:
                            convalidacion = ConvalidacionInscripcion(centro=f.cleaned_data['centro'],
                                                                     carrera=f.cleaned_data['carrera'],
                                                                     asignatura=f.cleaned_data['asignatura'],
                                                                     anno=f.cleaned_data['anno'],
                                                                     nota_ant=f.cleaned_data['nota_ant'],
                                                                     nota_act=f.cleaned_data['nota_act'],
                                                                     observaciones=f.cleaned_data['observaciones'],
                                                                     creditos=f.cleaned_data['creditos'])
                            convalidacion.save(request)
                            materiaasignadaconvalidacion = MateriaAsignadaConvalidacion(materiaasignada=materiaasignada,
                                                                                        convalidacion=convalidacion)
                            materiaasignadaconvalidacion.save(request)
                        log(u'Adicionada convalidacion: %s' % convalidacion, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'fechaasignacion':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=request.POST['id'])
                    f = CambioFechaAsignacionMateriaForm(request.POST)
                    if f.is_valid():
                        materiaasignada.fechaasignacion = f.cleaned_data['fecha']
                        materiaasignada.save(request, update_fields=['fechaasignacion'])
                        log(u'Modifico la fecha de asignacion de la materia: %s' % materiaasignada, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'detalle_matricula':
                try:
                    eMatricula = Matricula.objects.get(pk=int(request.POST['idmatricula']))
                    ePeriodoMatricula = None
                    if eMatricula.nivel.periodo.periodomatricula_set.values('id').filter(status=True).exists():
                        ePeriodoMatricula = eMatricula.nivel.periodo.periodomatricula_set.filter(status=True)[0]
                    if eMatricula.inscripcion.coordinacion_id in [1, 2, 3, 4, 5]:
                        porcentaje_perdidad_parcial_gratuidad = PORCIENTO_PERDIDA_PARCIAL_GRATUIDAD
                        if ePeriodoMatricula and ePeriodoMatricula.porcentaje_perdidad_parcial_gratuidad > 0:
                            porcentaje_perdidad_parcial_gratuidad = ePeriodoMatricula.porcentaje_perdidad_parcial_gratuidad
                        cursor = connection.cursor()
                        itinerario = 0
                        if not eMatricula.inscripcion.itinerario is None and eMatricula.inscripcion.itinerario > 0:
                            itinerario = eMatricula.inscripcion.itinerario
                        sql = f"select am.nivelmalla_id, count(am.nivelmalla_id) as cantidad_materias_seleccionadas from sga_materiaasignada ma, sga_materia m, sga_asignaturamalla am where ma.status=true and ma.matricula_id={str(eMatricula.id)} and m.status=true and m.id=ma.materia_id and am.status=true and am.id=m.asignaturamalla_id GROUP by am.nivelmalla_id, am.malla_id order by count(am.nivelmalla_id) desc, am.nivelmalla_id desc limit 1;"
                        if itinerario > 0:
                            sql = f"select am.nivelmalla_id, count(am.nivelmalla_id) as cantidad_materias_seleccionadas from sga_materiaasignada ma, sga_materia m, sga_asignaturamalla am where ma.status=true and ma.matricula_id={str(eMatricula.id)} and m.status=true and m.id=ma.materia_id and am.status=true and am.id=m.asignaturamalla_id and (am.itinerario=0 or am.itinerario=" + str(itinerario) + ") GROUP by am.nivelmalla_id, am.malla_id order by count(am.nivelmalla_id) desc, am.nivelmalla_id desc limit 1;"

                        cursor.execute(sql)
                        results = cursor.fetchall()
                        nivel = 0
                        for per in results:
                            nivel = per[0]
                            cantidad_seleccionadas = per[1]
                        cantidad_nivel = 0
                        materiasnivel = []
                        eAsignaturaMallas = AsignaturaMalla.objects.filter(nivelmalla__id=nivel, status=True, malla=eMatricula.inscripcion.mi_malla())
                        if itinerario > 0:
                            eAsignaturaMallas = eAsignaturaMallas.filter(Q(itinerario=0) | Q(itinerario=itinerario))
                        for eAsignaturaMalla in eAsignaturaMallas:
                            if Materia.objects.values('id').filter(nivel__periodo=eMatricula.nivel.periodo, asignaturamalla=eAsignaturaMalla).exists():
                                if eMatricula.inscripcion.estado_asignatura(eAsignaturaMalla.asignatura) != 1:
                                    cantidad_nivel += 1

                        porcentaje_seleccionadas = int(round(Decimal((float(cantidad_nivel) * float(porcentaje_perdidad_parcial_gratuidad)) / 100).quantize(Decimal('.00')), 0))
                        cobro = 0
                        if eMatricula.inscripcion.estado_gratuidad == 1 or eMatricula.inscripcion.estado_gratuidad == 2:
                            if (cantidad_seleccionadas < porcentaje_seleccionadas):
                                mensaje = f"Estudiante irregular, se ha matriculado en menos del {porcentaje_perdidad_parcial_gratuidad}%, debe cancelar por todas las asignaturas."
                                cobro = 1
                            else:
                                mensaje = u"Debe cancelar por las asignaturas que se matriculó por más de una vez."
                                cobro = 2
                        else:
                            if eMatricula.inscripcion.estado_gratuidad == 2:
                                mensaje = u"Su estado es de pérdida parcial de la gratuidad. Debe cancelar por las asignaturas que se matriculó por más de una vez."
                                cobro = 2
                            else:
                                mensaje = u"Alumno Regular"
                                cobro = 3
                        if eMatricula.inscripcion.persona.tiene_otro_titulo(inscripcion=eMatricula.inscripcion):
                            mensaje = u"El estudiante registra título en otra IES Pública o SENESCYT ha reportado. Su estado es de pérdida total de la gratuidad. Debe cancelar por todas las asignaturas."
                            cobro = 3
                        if cobro > 0:
                            for eMateriaAsignada in eMatricula.materiaasignada_set.filter(status=True, retiramateria=False):
                                if cobro == 1:
                                    materiasnivel.append(eMateriaAsignada.id)
                                else:
                                    if cobro == 2:
                                        if eMateriaAsignada.matriculas > 1:
                                            materiasnivel.append(eMateriaAsignada.id)
                                    else:
                                        materiasnivel.append(eMateriaAsignada.id)

                        matriculagruposocioeconomico = eMatricula.matriculagruposocioeconomico_set.filter(status=True)

                        if matriculagruposocioeconomico.values("id").exists():
                            eGrupoSocioEconomico = matriculagruposocioeconomico[0].gruposocioeconomico
                        else:
                            eGrupoSocioEconomico = eMatricula.inscripcion.persona.grupoeconomico()
                        eTipoOtroRubroArancel = TipoOtroRubro.objects.get(pk=RUBRO_ARANCEL)
                        eTipoOtroRubroMatricula = TipoOtroRubro.objects.get(pk=RUBRO_MATRICULA)
                        valorMatricula = 0
                        valorArancel = 0
                        aMateriaAsignadas = []
                        aMatricula = {}
                        if eMatricula.nivel.periodo.tipocalculo in (1, 2, 3, 4, 5):
                            valorGrupo = 0
                            if eMatricula.nivel.periodo.tipocalculo == 1:
                                ePeriodoGrupoSocioEconomico = PeriodoGrupoSocioEconomico.objects.filter(status=True, periodo=eMatricula.nivel.periodo, gruposocioeconomico=eGrupoSocioEconomico)[0]
                                valorGrupo = ePeriodoGrupoSocioEconomico.valor
                            elif eMatricula.nivel.periodo.tipocalculo in (2, 3, 4, 5):
                                malla = eMatricula.inscripcion.mi_malla()
                                if malla is None:
                                    raise NameError(u"Malla sin configurar")
                                periodomalla = PeriodoMalla.objects.filter(periodo=eMatricula.nivel.periodo, malla=malla, status=True)
                                if not periodomalla.values("id").exists():
                                    raise NameError(u"Malla no tiene configurado valores de cobro")
                                periodomalla = periodomalla[0]
                                detalleperiodomalla = DetallePeriodoMalla.objects.filter(periodomalla=periodomalla, gruposocioeconomico=eGrupoSocioEconomico, status=True)
                                if not detalleperiodomalla.values("id").exists():
                                    raise NameError(u"Malla en grupo socioeconomico no tiene configurado valores de cobro")
                                valorGrupo = detalleperiodomalla[0].valor
                            for eMateriaAsignada in MateriaAsignada.objects.filter(pk__in=materiasnivel):
                                creditos = 0
                                total = 0
                                if eMateriaAsignada.existe_modulo_en_malla():
                                    creditos = eMateriaAsignada.materia_modulo_malla().creditos
                                    total = null_to_decimal((Decimal(creditos).quantize(Decimal('.01')) * Decimal(valorGrupo).quantize(Decimal('.01'))).quantize(Decimal('.01')), 2)
                                elif eMateriaAsignada.materia.asignaturamalla.creditos > 0:
                                    creditos = eMateriaAsignada.materia.asignaturamalla.creditos
                                    total = null_to_decimal((Decimal(creditos).quantize(Decimal('.01')) * Decimal(valorGrupo).quantize(Decimal('.01'))).quantize(Decimal('.01')), 2)
                                else:
                                    creditos = eMateriaAsignada.materia.creditos
                                    total = null_to_decimal((Decimal(creditos).quantize(Decimal('.01')) * Decimal(valorGrupo).quantize(Decimal('.01'))).quantize(Decimal('.01')), 2)
                                aMateriaAsignadas.append({"id": encrypt(eMateriaAsignada.id),
                                                          "asignatura": eMateriaAsignada.materia.asignaturamalla.asignatura.nombre,
                                                          "creditos": creditos,
                                                          "valor": valorGrupo,
                                                          "total": total,
                                                          "fecha_asignacion": eMateriaAsignada.fecha_creacion.strftime("%d-%m-%Y %H:%M:%S"),
                                                          "fecha_eliminacion": None,
                                                          "activo": True,
                                                          "nivel": eMateriaAsignada.materia.asignaturamalla.nivelmalla.nombre})
                            aMatricula = {"id": encrypt(eMatricula.id),
                                          "estudiante": eMatricula.inscripcion.persona.nombre_completo(),
                                          "gruposocioeconomico": eGrupoSocioEconomico.nombre if eGrupoSocioEconomico else "",
                                          "style_color": eGrupoSocioEconomico.style_color() if eGrupoSocioEconomico else "",
                                          "mensaje": mensaje
                                          }
                            valorArancel = null_to_decimal(Rubro.objects.filter(matricula=eMatricula, status=True, tipo=eTipoOtroRubroArancel).aggregate(valor=Sum('valortotal'))['valor'])
                            valorMatricula = null_to_decimal(Rubro.objects.filter(matricula=eMatricula, status=True, tipo=eTipoOtroRubroMatricula).aggregate(valor=Sum('valortotal'))['valor'])
                        elif eMatricula.nivel.periodo.tipocalculo == 6:
                            aMatricula = {"id": encrypt(eMatricula.id),
                                          "estudiante": eMatricula.inscripcion.persona.nombre_completo(),
                                          "gruposocioeconomico": eGrupoSocioEconomico.nombre if eGrupoSocioEconomico else "",
                                          "style_color": eGrupoSocioEconomico.style_color() if eGrupoSocioEconomico else "",
                                          "mensaje": mensaje
                                          }
                            eDetalleRubroMatriculas = DetalleRubroMatricula.objects.filter(matricula=eMatricula)
                            eDetalleRubroMatriculas_m = eDetalleRubroMatriculas.filter(materia__isnull=True)
                            eDetalleRubroMatriculas_a = eDetalleRubroMatriculas.filter(materia__isnull=False)
                            if eDetalleRubroMatriculas_m.values("id").exists():
                                valorMatricula = null_to_decimal(Rubro.objects.filter(matricula=eMatricula, status=True, tipo=eTipoOtroRubroMatricula).aggregate(valor=Sum('valortotal'))['valor'])
                            if eDetalleRubroMatriculas_a.values("id").exists():
                                valorArancel = null_to_decimal(Rubro.objects.filter(matricula=eMatricula, status=True, tipo=eTipoOtroRubroArancel).aggregate(valor=Sum('valortotal'))['valor'])
                            for eDetalleRubroMatricula in eDetalleRubroMatriculas_a:
                                total = null_to_decimal((Decimal(eDetalleRubroMatricula.creditos).quantize(Decimal('.01')) * Decimal(eDetalleRubroMatricula.costo).quantize(Decimal('.01'))).quantize(Decimal('.01')), 2)
                                aMateriaAsignadas.append({"id": encrypt(eDetalleRubroMatricula.materia.id),
                                                          "asignatura": eDetalleRubroMatricula.materia.asignaturamalla.asignatura.nombre,
                                                          "creditos": eDetalleRubroMatricula.creditos,
                                                          "valor": eDetalleRubroMatricula.costo,
                                                          "total": total,
                                                          "fecha_asignacion": eMateriaAsignada.fecha_creacion.strftime("%d-%m-%Y %H:%M:%S"),
                                                          "fecha_eliminacion": eDetalleRubroMatricula.fecha.strftime("%d-%m-%Y %H:%M:%S") if eDetalleRubroMatricula.fecha else None,
                                                          "activo": eDetalleRubroMatricula.activo,
                                                          "nivel": eDetalleRubroMatricula.materia.asignaturamalla.nivelmalla.nombre})
                        else:
                            raise NameError(u"No se encontro configuración del proceso de cobro de matriculación")

                        data['eMatricula'] = aMatricula
                        data['eMateriaAsignadas'] = aMateriaAsignadas
                        data['valorArancel'] = valorArancel
                        data['valorMatricula'] = valorMatricula
                        data['valorPagar'] = valorArancel + valorMatricula
                        template = get_template("matriculas/detalle_matricula.html")
                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", 'html': json_content})
                    elif eMatricula.inscripcion.coordinacion_id in [9]:
                        # inscripcion.estado_gratuidad = 3
                        eMateriaAsignadas = MateriaAsignada.objects.filter(matricula=eMatricula,
                                                                           cobroperdidagratuidad=True)
                        aMateriaAsignadas = []
                        if eMatricula.inscripcion.sesion_id == 13:
                            eTipoOtroRubroMatricula = TipoOtroRubro.objects.get(pk=3019)
                        else:
                            eTipoOtroRubroMatricula = TipoOtroRubro.objects.get(pk=3011)
                        valorMatricula = null_to_decimal(Rubro.objects.filter(matricula=eMatricula, status=True, tipo=eTipoOtroRubroMatricula).aggregate(valor=Sum('valortotal'))['valor'])
                        valor_x_materia = null_to_decimal(Decimal(valorMatricula / len(eMateriaAsignadas)).quantize(Decimal('.01')).quantize(Decimal('.01')), 2)
                        for eMateriaAsignada in eMateriaAsignadas:
                            aMateriaAsignadas.append({"id": encrypt(eMateriaAsignada.id),
                                                      "asignatura": eMateriaAsignada.materia.asignaturamalla.asignatura.nombre,
                                                      "creditos": 0,
                                                      "valor": valor_x_materia,
                                                      "total": valor_x_materia,
                                                      "fecha_asignacion": eMateriaAsignada.fecha_creacion.strftime("%d-%m-%Y %H:%M:%S"),
                                                      "fecha_eliminacion": None,
                                                      "activo": True,
                                                      "nivel": eMateriaAsignada.materia.asignaturamalla.nivelmalla.nombre})
                        ePerdidaGratuidadas = PerdidaGratuidad.objects.values("id").filter(inscripcion=eMatricula.inscripcion, status=True)
                        mensaje = ''
                        if ePerdidaGratuidadas.values("id").exists():
                            mensaje = ePerdidaGratuidadas[0].observacion
                        else:
                            mensaje = 'Segunda matrícula'
                        aMatricula = {
                            "id": encrypt(eMatricula.id),
                            "estudiante": eMatricula.inscripcion.persona.nombre_completo(),
                            "gruposocioeconomico": "",
                            "mensaje": mensaje
                        }
                        data['eMatricula'] = aMatricula
                        data['eMateriaAsignadas'] = aMateriaAsignadas
                        data['valorArancel'] = null_to_decimal(Decimal(0).quantize(Decimal('.01')).quantize(Decimal('.01')), 2),
                        data['valorMatricula'] = valorMatricula
                        data['valorPagar'] = valorMatricula
                        template = get_template("matriculas/detalle_matricula_admision.html")
                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", 'html': json_content})
                    return JsonResponse({"result": "bad", "mensaje": "Ocurrio un error: Datos no encontrados"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'materiapractica':
                try:
                    materia = Materia.objects.get(id=int(request.POST['mat']))
                    matricula = Matricula.objects.get(pk=int(request.POST['idm']))
                    # EXTRAMOS LOS DATOS DE LA MATERIA SELECCIONADA
                    coordinacion=materia.coordinacion()
                    tipoprofesorpractica=None
                    # if coordinacion:
                    #     if coordinacion.id == 1:
                    #         tipoprofesorpractica = TipoProfesor.objects.get(pk=13)
                    #     else:
                    #         tipoprofesorpractica = TipoProfesor.objects.get(pk=2)
                    datos = materia.datos_practicas_materia(matricula.inscripcion)
                    return JsonResponse({"result": "ok", "datos": datos})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'actualizar_estudiantes_moodle':
                try:
                    materia = Materia.objects.get(pk=request.POST['id'], status=True)
                    if materia.coordinacion().id == 9:
                        tipourl = 2
                    else:
                        tipourl = 1
                    materia.crear_actualizar_estudiantes_curso(moodle, tipourl)
                    log(u'Utiliza el boton Actualizar todos los estudiantes moodle %s' % (materia), request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            elif action == 'actualizar_un_estudiante_moodle':
                try:
                    matricula = Matricula.objects.get(pk=request.POST['id'], status=True)
                    materia = Materia.objects.get(pk=request.POST['materia'], status=True)
                    if materia.coordinacion().id == 9:
                        tipourl = 2
                    else:
                        tipourl = 1
                    materia.crear_actualizar_un_estudiante_curso(moodle, tipourl,matricula)
                    log(u'Utiliza el boton Actualizar un estudiante moodle %s' % (materia), request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            elif action == 'loadModalitiesSesions_by_Period':
                try:
                    aDataModalities = []
                    aDataSesions = []
                    aDataModalities.append({"id": 0,
                                            "text": "---------",
                                            "selected": True})
                    aDataSesions.append({"id": 0,
                                         "text": "---------",
                                         "selected": True})
                    if not 'idp' in request.POST:
                        raise NameError(u"Periodo no identificado")
                    if not Periodo.objects.filter(pk=int(request.POST['idp'])).exists():
                        raise NameError(u"Periodo no identificado")
                    ePeriodo = Periodo.objects.get(pk=int(request.POST['idp']))
                    modalidades = Modalidad.objects.filter(pk__in=Nivel.objects.values_list('modalidad__id', flat=True).filter(periodo=ePeriodo).distinct())
                    sesions = Sesion.objects.filter(pk__in=Nivel.objects.values_list('sesion__id', flat=True).filter(periodo=ePeriodo).distinct())
                    for modalidad in modalidades:
                        aDataModalities.append({"id": modalidad.id,
                                                "text": modalidad.__str__()})

                    for sesion in sesions:
                        aDataSesions.append({"id": sesion.id,
                                             "text": sesion.__str__()})
                    return JsonResponse({"result": "ok", 'aDataModalities': aDataModalities, "aDataSesions": aDataSesions})
                except Exception as ex:
                    return JsonResponse({"result": "bad", 'aDataModalities': aDataModalities, "aDataSesions": aDataSesions})

            elif action == 'loadCurriculums':
                try:
                    aData = []
                    aData.append({"id": 0,
                                  "text": "---------",
                                  "selected": True})
                    if not 'idp' in request.POST:
                        raise NameError(u"Periodo no identificado")
                    if not Periodo.objects.filter(pk=int(request.POST['idp'])).exists():
                        raise NameError(u"Periodo no identificado")
                    if not 'idm' in request.POST:
                        raise NameError(u"Modalidad no identificada")
                    if not Modalidad.objects.filter(pk=int(request.POST['idm'])).exists():
                        raise NameError(u"Modalidad no identificada")
                    if not 'ids' in request.POST:
                        raise NameError(u"Sección no identificada")
                    if not Sesion.objects.filter(pk=int(request.POST['ids'])).exists():
                        raise NameError(u"Sección no identificada")
                    ePeriodo = Periodo.objects.get(pk=int(request.POST['idp']))
                    eModalidad = Modalidad.objects.get(pk=int(request.POST['idm']))
                    eSesion = Sesion.objects.get(pk=int(request.POST['ids']))
                    mallas = Malla.objects.filter(pk__in=Materia.objects.values_list('asignaturamalla__malla__id', flat=True).filter(nivel__periodo=ePeriodo, nivel__modalidad=eModalidad, nivel__sesion=eSesion).distinct())
                    for malla in mallas:
                        aData.append({"id": malla.id,
                                      "text": malla.__str__()})
                    return JsonResponse({"result": "ok", 'results': aData})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "results": aData})

            elif action == 'loadLevelsCurriculum':
                try:
                    aData = []
                    aData.append({"id": 0,
                                  "text": "---------",
                                  "selected": True})
                    if not 'idp' in request.POST:
                        raise NameError(u"Periodo no identificado")
                    if not Periodo.objects.filter(pk=int(request.POST['idp'])).exists():
                        raise NameError(u"Periodo no identificado")
                    if not 'idm' in request.POST:
                        raise NameError(u"Modalidad no identificada")
                    if not Modalidad.objects.filter(pk=int(request.POST['idm'])).exists():
                        raise NameError(u"Modalidad no identificada")
                    if not 'ids' in request.POST:
                        raise NameError(u"Sección no identificada")
                    if not Sesion.objects.filter(pk=int(request.POST['ids'])).exists():
                        raise NameError(u"Sección no identificada")
                    if not 'idma' in request.POST:
                        raise NameError(u"Malla no identificada")
                    if not Malla.objects.filter(pk=int(request.POST['idma'])).exists():
                        raise NameError(u"Malla no identificada")
                    ePeriodo = Periodo.objects.get(pk=int(request.POST['idp']))
                    eModalidad = Modalidad.objects.get(pk=int(request.POST['idm']))
                    eSesion = Sesion.objects.get(pk=int(request.POST['ids']))
                    eMalla = Malla.objects.get(pk=int(request.POST['idma']))
                    niveles = NivelMalla.objects.filter(pk__in=Materia.objects.values_list('asignaturamalla__nivelmalla__id', flat=True).filter(nivel__periodo=ePeriodo, nivel__modalidad=eModalidad, nivel__sesion=eSesion, asignaturamalla__malla=eMalla).distinct())
                    for nivel in niveles:
                        aData.append({"id": nivel.id,
                                      "text": nivel.__str__()})
                    return JsonResponse({"result": "ok", 'results': aData})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "results": aData})

            elif action == 'loadParallels':
                try:
                    aData = []
                    aData.append({"id": 0,
                                  "text": "---------",
                                  "selected": True})
                    if not 'idp' in request.POST:
                        raise NameError(u"Periodo no identificado")
                    if not Periodo.objects.filter(pk=int(request.POST['idp'])).exists():
                        raise NameError(u"Periodo no identificado")
                    if not 'idm' in request.POST:
                        raise NameError(u"Modalidad no identificada")
                    if not Modalidad.objects.filter(pk=int(request.POST['idm'])).exists():
                        raise NameError(u"Modalidad no identificada")
                    if not 'ids' in request.POST:
                        raise NameError(u"Sección no identificada")
                    if not Sesion.objects.filter(pk=int(request.POST['ids'])).exists():
                        raise NameError(u"Sección no identificada")
                    if not 'idma' in request.POST:
                        raise NameError(u"Malla no identificada")
                    if not Malla.objects.filter(pk=int(request.POST['idma'])).exists():
                        raise NameError(u"Malla no identificada")
                    if not 'idnm' in request.POST:
                        raise NameError(u"Nivel Malla no identificada")
                    if not NivelMalla.objects.filter(pk=int(request.POST['idnm'])).exists():
                        raise NameError(u"NivelMalla no identificada")
                    ePeriodo = Periodo.objects.get(pk=int(request.POST['idp']))
                    eModalidad = Modalidad.objects.get(pk=int(request.POST['idm']))
                    eSesion = Sesion.objects.get(pk=int(request.POST['ids']))
                    eMalla = Malla.objects.get(pk=int(request.POST['idma']))
                    eNivelMalla = NivelMalla.objects.get(pk=int(request.POST['idnm']))
                    paralelos = Paralelo.objects.filter(pk__in=Materia.objects.values_list('paralelomateria__id', flat=True).filter(nivel__periodo=ePeriodo, nivel__modalidad=eModalidad, nivel__sesion=eSesion, asignaturamalla__malla=eMalla, asignaturamalla__nivelmalla=eNivelMalla).distinct())
                    for paralelo in paralelos:
                        aData.append({"id": paralelo.id,
                                      "text": paralelo.__str__()})
                    return JsonResponse({"result": "ok", 'results': aData})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "results": aData})

            elif action == 'loadSubjects':
                try:
                    aData = []
                    if not 'idp' in request.POST:
                        raise NameError(u"Periodo no identificado")
                    if not Periodo.objects.filter(pk=int(request.POST['idp'])).exists():
                        raise NameError(u"Periodo no identificado")
                    if not 'idm' in request.POST:
                        raise NameError(u"Modalidad no identificada")
                    if not Modalidad.objects.filter(pk=int(request.POST['idm'])).exists():
                        raise NameError(u"Modalidad no identificada")
                    if not 'ids' in request.POST:
                        raise NameError(u"Sección no identificada")
                    if not Sesion.objects.filter(pk=int(request.POST['ids'])).exists():
                        raise NameError(u"Sección no identificada")
                    if not 'idma' in request.POST:
                        raise NameError(u"Malla no identificada")
                    if not Malla.objects.filter(pk=int(request.POST['idma'])).exists():
                        raise NameError(u"Malla no identificada")
                    if not 'idnm' in request.POST:
                        raise NameError(u"Nivel Malla no identificada")
                    if not NivelMalla.objects.filter(pk=int(request.POST['idnm'])).exists():
                        raise NameError(u"Nivel Malla no identificada")
                    if not 'idmatricula' in request.POST:
                        raise NameError(u"Matricula no identificada")
                    if not Matricula.objects.filter(pk=int(request.POST['idmatricula'])).exists():
                        raise NameError(u"Matricula no identificada")
                    eParalelo = None
                    if 'idpa' in request.POST:
                        if Paralelo.objects.filter(pk=int(request.POST['idpa'])).exists():
                            eParalelo = Paralelo.objects.get(pk=int(request.POST['idpa']))
                    ePeriodo = Periodo.objects.get(pk=int(request.POST['idp']))
                    eModalidad = Modalidad.objects.get(pk=int(request.POST['idm']))
                    eSesion = Sesion.objects.get(pk=int(request.POST['ids']))
                    eMalla = Malla.objects.get(pk=int(request.POST['idma']))
                    eNivelMalla = NivelMalla.objects.get(pk=int(request.POST['idnm']))
                    eMatricula = Matricula.objects.get(pk=int(request.POST['idmatricula']))
                    materiaasignadas = eMatricula.materiaasignada_set.filter(matricula__status=True)
                    materias = Materia.objects.filter(status=True, cerrado=False, nivel__cerrado=False, nivel__modalidad=eModalidad, nivel__sesion=eSesion, nivel__periodo=ePeriodo, asignaturamalla__malla=eMalla, asignaturamalla__nivelmalla=eNivelMalla).order_by('paralelomateria__nombre')
                    if eParalelo:
                        materias = materias.filter(paralelomateria=eParalelo)
                    # materias = materias.exclude(asignatura__id__in=materiaasignadas.values_list('materia__asignatura__id', flat=True).distinct())
                    for materia in materias:
                        aData.append({"id": materia.id,
                                      "nombre": materia.__str__(),
                                      "paralelo": materia.paralelomateria.nombre})
                    return JsonResponse({"result": "ok", 'results': aData})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "results": aData})

            elif action == 'loadSubjectSchedule':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    data['materia'] = materia = Materia.objects.get(pk=request.POST['idmateria'])
                    data['matricula'] = matricula = Matricula.objects.get(pk=request.POST['idmatricula'])
                    data['homitircapacidadhorario'] = HOMITIRCAPACIDADHORARIO
                    data['permiteagregaciones'] = matricula.nivel.periodo.limite_agregacion >= datetime.now().date()
                    template = get_template("matriculas/prometehorario.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            elif action == 'saveMateriaPosgrado':
                try:
                    matricula = Matricula.objects.get(pk=int(request.POST['idmatricula']))
                    if matricula.inscripcion.bloqueomatricula:
                        raise NameError(u"Estimado estudiante, su matrícula se encuentra bloqueada, por favor contactarse a secretaria de facultad.")
                    materia = Materia.objects.get(pk=int(request.POST['idmateria']))
                    profesormateria = None
                    grupoprofesormateria = None
                    matriculacupoadicional = False
                    if matricula.materiaasignada_set.values('id').filter(materia=materia).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya se encuentra matriculado en esta materia"})
                    materiaasignada = MateriaAsignada(matricula=matricula,
                                                      materia=materia,
                                                      notafinal=0,
                                                      asistenciafinal=0,
                                                      cerrado=False,
                                                      observaciones='',
                                                      estado_id=NOTA_ESTADO_EN_CURSO)
                    materiaasignada.save(request)
                    if matriculacupoadicional:
                        materia.totalmatriculadocupoadicional += 1
                        materia.cupo += 1
                        materia.save(request)
                        log(u'Estudiante matriculado en cupo adicional materia: %s - estudiante: %s y se aumento un cupo en materia' % (materia, matricula), request, "add")
                    if profesormateria:
                        alumnopractica = AlumnosPracticaMateria(materiaasignada=materiaasignada, profesormateria=profesormateria)
                        alumnopractica.save(request)
                        log(u'Materia (%s) con profesor practica (%s) seleccionada matricula: %s en tabla alumnopractica (%s)' % (materia, profesormateria, materiaasignada, alumnopractica.id), request, "add")
                    elif grupoprofesormateria:
                        alumnopractica = AlumnosPracticaMateria(materiaasignada=materiaasignada, profesormateria=grupoprofesormateria.profesormateria, grupoprofesor=grupoprofesormateria)
                        alumnopractica.save(request)
                        log(u'Materia (%s) con grupo profesor practica (%s) seleccionada matricula: %s en tabla alumnopractica (%s) por modulo de inscripciones' % ( materia, grupoprofesormateria, materiaasignada, alumnopractica.id), request, "add")
                    matricula.actualizar_horas_creditos()
                    materiaasignada.matriculas = materiaasignada.cantidad_matriculas()
                    materiaasignada.asistencias()
                    materiaasignada.evaluacion()
                    materiaasignada.mis_planificaciones()
                    materiaasignada.save(request)
                    if matricula.nivel.nivelgrado:
                        log(u'Adiciono materia: %s' % materiaasignada, request, "add")
                    else:
                        if datetime.now().date() < matricula.nivel.periodo.inicio_agregacion:
                            # AGREGACION DE MATERIAS EN MATRICULACION REGULAR SIN REALIZAR PAGOS
                            materiaasignada.save(request)
                            log(u'Adiciono materia: %s' % materiaasignada, request, "add")
                            if CALCULO_POR_CREDITO and not materia.coordinacion().id in [7,9]:
                                matricula.agregacion_aux(request)
                                matricula.inscripcion.actualiza_estado_matricula()
                                valid, msg, aData = get_tipo_matricula(None, matricula)
                                if not valid:
                                    raise NameError(msg)
                                cantidad_nivel = aData['cantidad_nivel']
                                porcentaje_perdidad_parcial_gratuidad = aData['porcentaje_perdidad_parcial_gratuidad']
                                cantidad_seleccionadas = aData['cantidad_seleccionadas']
                                porcentaje_seleccionadas = int(round(
                                    Decimal((float(cantidad_nivel) * float(
                                        porcentaje_perdidad_parcial_gratuidad)) / 100).quantize(
                                        Decimal('.00')), 0))
                                if (cantidad_seleccionadas < porcentaje_seleccionadas):
                                    matricula.grupo_socio_economico(2)
                                else:
                                    matricula.grupo_socio_economico(1)
                                # matricula.calcular_rubros_matricula(cobro)
                        elif matricula.nivel.periodo.fecha_agregaciones():
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
                            if CALCULO_POR_CREDITO  and not materia.coordinacion().id in [7,9]:
                                matricula.agregacion_aux(request)
                                matricula.inscripcion.actualiza_estado_matricula()
                                valid, msg, aData = get_tipo_matricula(None, matricula)
                                if not valid:
                                    raise NameError(msg)
                                cantidad_nivel = aData['cantidad_nivel']
                                porcentaje_perdidad_parcial_gratuidad = aData['porcentaje_perdidad_parcial_gratuidad']
                                cantidad_seleccionadas = aData['cantidad_seleccionadas']
                                porcentaje_seleccionadas = int(round(
                                    Decimal((float(cantidad_nivel) * float(
                                        porcentaje_perdidad_parcial_gratuidad)) / 100).quantize(
                                        Decimal('.00')), 0))
                                if (cantidad_seleccionadas < porcentaje_seleccionadas):
                                    matricula.grupo_socio_economico(2)
                                else:
                                    matricula.grupo_socio_economico(1)
                        else:
                            # AGREGACION DE MATERIAS TERMINADA LAS AGREGACIONES
                            if materia.asignatura.modulo:
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
                                if CALCULO_POR_CREDITO and not materia.coordinacion().id in [7,9]:
                                    matricula.agregacion_aux(request)
                                    matricula.inscripcion.actualiza_estado_matricula()
                                    valid, msg, aData = get_tipo_matricula(None, matricula)
                                    if not valid:
                                        raise NameError(msg)
                                    cantidad_nivel = aData['cantidad_nivel']
                                    porcentaje_perdidad_parcial_gratuidad = aData[
                                        'porcentaje_perdidad_parcial_gratuidad']
                                    cantidad_seleccionadas = aData['cantidad_seleccionadas']
                                    porcentaje_seleccionadas = int(round(
                                        Decimal((float(cantidad_nivel) * float(
                                            porcentaje_perdidad_parcial_gratuidad)) / 100).quantize(
                                            Decimal('.00')), 0))
                                    if (cantidad_seleccionadas < porcentaje_seleccionadas):
                                        matricula.grupo_socio_economico(2)
                                    else:
                                        matricula.grupo_socio_economico(1)
                            # else:
                            #      raise NameError('Error')
                            messages.success(request, 'Se agrego correctamente la materia')
                    return JsonResponse({"result": "ok", "mensaje": u"Se agrego correctamente la materia"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al agregar la materia"})

            elif action == 'viewauditoria':
                try:
                    data['planificacion'] = materiaasignada = MateriaAsignada.objects.get(pk=int(request.POST['id']))
                    template = get_template("matriculas/viewauditoria.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

            elif action == 'requisitostitulacion':
                try:
                    data['eMatricula'] = eMatricula = Matricula.objects.get(pk=int(request.POST['codmatricula']))
                    eInscripcionMalla = eMatricula.inscripcion.malla_inscripcion()
                    data['eAsignaturaMalla'] = eAsignaturaMalla = AsignaturaMalla.objects.get(pk=int(request.POST['idam']))
                    data['eMateria'] = eMateria = Materia.objects.get(pk=int(request.POST['idmat']))
                    # eRequisitos = RequisitoIngresoUnidadIntegracionCurricular.objects.filter(status=True, asignaturamalla=eAsignaturaMalla, activo=True, obligatorio=True)
                    eRequisitos_aux = RequisitoMateriaUnidadIntegracionCurricular.objects.filter(materia=eMateria, status=True, activo=True, obligatorio=True, inscripcion=True)
                    eRequisitos = RequisitoIngresoUnidadIntegracionCurricular.objects.filter(asignaturamalla=eAsignaturaMalla, requisito__id__in=eRequisitos_aux.values_list("requisito__id", flat=True)).distinct()
                    aRequisitos = []
                    total = len(eRequisitos.values("id"))
                    contador = 0
                    for eRequisito in eRequisitos:
                        eRequisito_data = MatriRequisitoIngresoUnidadIntegracionCurricularSerializer(eRequisito).data
                        if eRequisito.enlineamatriculacion:
                            eRequisito_data.__setitem__('cumple', True)
                            contador += 1
                        else:
                            cumple = eRequisito.run(eMatricula.inscripcion.pk)
                            if cumple:
                                contador += 1
                            eRequisito_data.__setitem__('cumple', cumple)
                        aRequisitos.append(eRequisito_data)
                    data['aRequisitos'] = aRequisitos
                    template = get_template("matriculas/requisitostitulacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'cumple': total == contador})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": f"Error al obtener los datos. {ex.__str__()}"})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Matriculas de alumnos'
        persona = request.session['persona']
        miscarreras = Carrera.objects.filter(grupocoordinadorcarrera__group__in=persona.grupos()).distinct()
        if 'action' in request.GET:
            action = request.GET['action']


            if action == 'matricula':
                try:
                    data['title'] = u'Matricula de nivel académico'
                    nivel = Nivel.objects.get(pk=request.GET['id'])
                    ret = None
                    if 'ret' in request.GET:
                        ret = request.GET['ret']
                    periodo = request.session['periodo']
                    search = ""
                    if 's' in request.GET:
                        search = request.GET['s']
                        ss = search.split(' ')
                        while '' in ss:
                            ss.remove('')
                        if len(ss) == 1:
                            matriculas = Matricula.objects.filter(Q(inscripcion__persona__nombres__icontains=search) |
                                                                  Q(inscripcion__persona__apellido1__icontains=search) |
                                                                  Q(inscripcion__persona__apellido2__icontains=search) |
                                                                  Q(inscripcion__persona__cedula__icontains=search) |
                                                                  Q(inscripcion__persona__pasaporte__icontains=search) |
                                                                  Q(inscripcion__identificador__icontains=search) |
                                                                  Q(inscripcion__inscripciongrupo__grupo__nombre__icontains=search) |
                                                                  Q(inscripcion__carrera__nombre__icontains=search) |
                                                                  Q(inscripcion__persona__usuario__username__icontains=search), nivel=nivel, status=True).order_by('inscripcion__persona').distinct()
                        else:
                            matriculas = Matricula.objects.filter(Q(inscripcion__persona__apellido1__icontains=ss[0]),
                                                                  Q(inscripcion__persona__apellido2__icontains=ss[1]), nivel=nivel, status=True).order_by('inscripcion__persona').distinct()
                    elif 'idm' in request.GET:
                        matriculas = Matricula.objects.filter(nivel=nivel, status=True, id=request.GET['idm']).order_by('inscripcion__persona').distinct()
                    else:
                        matriculas = Matricula.objects.filter(nivel=nivel, status=True).order_by('inscripcion__persona').distinct()
                    paging = MiPaginador(matriculas, 1000)
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
                    data['matriculas'] = page.object_list
                    data['search'] = search if search else ""
                    data['ret'] = ret if ret else ""
                    data['nivel'] = nivel
                    data['periodo'] = periodo
                    data['matriculados_total'] = Matricula.objects.filter(nivel=nivel, estado_matricula__in=[2,3]).count()
                    data['matriculalibre'] = MATRICULACION_LIBRE
                    data['calculocreditos'] = CALCULO_POR_CREDITO
                    data['reporte_0'] = obtener_reporte('lista_alumnos_matriculados')
                    data['reporte_1'] = obtener_reporte('certificado_matricula_alumno')
                    data['reporte_2'] = obtener_reporte('reporte_compromiso_pago')
                    data['matriculacion_libre'] = MATRICULACION_LIBRE
                    data['usa_retiro_matricula'] = USA_RETIRO_MATRICULA
                    data['permiteagregaciones'] = periodo.limite_agregacion >= datetime.now().date()
                    data['permiteretiro'] = periodo.limite_retiro >= datetime.now().date()
                    return render(request, "matriculas/matricula.html", data)
                except Exception as ex:
                    pass

            elif action == 'auditoria':
                try:
                    data['auditoriadetalle']=auditoria = DetalleModificacionNota.objects.filter(materiaasignada_id=request.GET['id'])
                    template = get_template("matriculas/auditorianota.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addmatriculalibre':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    data['title'] = u'Matricular estudiante'
                    data['periodo'] = periodo = request.session['periodo']
                    data['nivel'] = nivel = Nivel.objects.get(pk=request.GET['id'])
                    data['total_materias_nivel'] = 0
                    inscripcion = None
                    if 'iid' in request.GET:
                        inscripcion = Inscripcion.objects.get(pk=request.GET['iid'])
                        if not persona.usuario.is_superuser:
                            miscarreras = persona.mis_carreras_tercer_nivel()
                            es_director_carr = miscarreras.values("id").exists()
                            if not variable_valor('PUEDE_MATRICULAR_DIRECTOR') and es_director_carr:
                                return HttpResponseRedirect(u"/?info=Lo sentimos usted no puede acceder a la matriculación")
                        if not variable_valor('PUEDE_MATRICULARSE_OTRA_VEZ'):
                            asignaturaid = AsignaturaMalla.objects.values_list('asignatura__id', flat=True).filter(Q(malla__id=22) | Q(malla__carrera_id=37))
                            if inscripcion.recordacademico_set.filter(status=True, aprobada=False).exclude(asignatura__id__in=asignaturaid).count() > 0:
                                return HttpResponseRedirect(u"/?info=La matriculación se encuentra activa solo para estudiantes que han aprobado todas sus asignaturas")

                        # if inscripcion.persona.tiene_matricula_periodo(periodo):
                        #     return HttpResponseRedirect("/?info=Ya se encuentra matriculado en el periodo en otra Carrera")
                        # if inscripcion.persona.tiene_matricula_periodo(periodo):
                        #     return HttpResponseRedirect("/?info=Ya se encuentra matriculado en el periodo en otra Carrera")
                        if inscripcion.carrera not in nivel.coordinacion().carrera.all():
                            return HttpResponseRedirect("/matriculas?action=addmatriculalibre&err=1&iid=" + request.GET['iid'] + "&id=" + str(nivel.id))
                        if inscripcion.modalidad != nivel.modalidad:
                            return HttpResponseRedirect("/matriculas?action=addmatriculalibre&err=2&iid=" + request.GET['iid'] + "&id=" + str(nivel.id))
                        # if inscripcion.sesion != nivel.sesion:
                        #     return HttpResponseRedirect("/matriculas?action=addmatriculalibre&err=3&iid=" + request.GET['iid'] + "&id=" + str(nivel.id))
                        inscripcionmalla = inscripcion.malla_inscripcion()
                        if not inscripcionmalla:
                            return HttpResponseRedirect("/?info=Debe tener malla asociada para poder matricularse.")
                        if not MATRICULAR_CON_DEUDA:
                            if inscripcion.adeuda_a_la_fecha():
                                return HttpResponseRedirect("/matriculas?action=addmatriculalibre&err=5&iid=" + request.GET['iid'] + "&id=" + str(nivel.id))
                        if inscripcion.matriculado_periodo(periodo):
                            return HttpResponseRedirect("/matriculas?action=addmatriculalibre&err=6&iid=" + request.GET['iid'] + "&id=" + str(nivel.id))
                        # if 'ide' in request.GET:
                        #     inscripcion = Inscripcion.objects.get(pk=request.GET['ide'])
                        # if variable_valor('VALIDAR_QUE_SEA_PRIMERA_MATRICULA'):
                        #     if inscripcion.matricula_set.values('id').filter(status=True).exists():
                        #         return HttpResponseRedirect(u"/?info=No puede matricularse, solo apto para primera vez.")
                        data['inscripcion'] = inscripcion
                        data['malla'] = inscripcionmalla
                        data['iid'] = inscripcion.id
                        data['total_materias_nivel'] = inscripcion.total_materias_nivel()
                        data['materiasmalla'] = inscripcionmalla.malla.asignaturamalla_set.all().order_by('nivelmalla', 'ejeformativo')
                        data['materiasmodulos'] = inscripcionmalla.malla.modulomalla_set.all()
                        data['total_materias_pendientes_malla'] = inscripcion.total_materias_pendientes_malla()
                    else:
                        data['matriculado'] = False
                        data['materiasmalla'] = None
                        data['materiasmodulos'] = None
                        data['iid'] = None
                    data['materiasmaximas'] = MAXIMO_MATERIA_ONLINE
                    data['utiliza_gratuidades'] = UTILIZA_GRATUIDADES
                    data['err'] = int(request.GET['err']) if 'err' in request.GET else ''
                    data['nombreerroneo'] = Inscripcion.objects.get(pk=request.GET['ide']).persona.nombre_completo() if 'err' in request.GET else ''
                    data['porciento_perdida_parcial_gratuidad'] = PORCIENTO_PERDIDA_PARCIAL_GRATUIDAD
                    data['porciento_perdida_total_gratuidad'] = PORCIENTO_PERDIDA_TOTAL_GRATUIDAD
                    data['NOTIFICACIÓN_NO_MATRICULARSE_OTRA_VEZ'] = 'Aun no esta habilitada la matriculación por mas de una vez en las materia'
                    data['PUEDE_MATRICULARSE_OTRA_VEZ'] = variable_valor('PUEDE_MATRICULARSE_OTRA_VEZ')
                    data['fecha_actual'] = datetime.now().date()
                    # if RecordAcademico.objects.filter(aprobada=False, inscripcion=inscripcion).exists():
                    #     data['tiene_reprobada'] = True
                    # else:
                    #     data['tiene_reprobada'] = False
                    return render(request, "matriculas/addmatriculalibre.html", data)
                except Exception as ex:
                    pass

            elif action == 'addmatriculamulti':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    data['title'] = u'Matricular estudiantes'
                    data['nivel'] = nivel = Nivel.objects.get(pk=request.GET['id'])
                    form = MatriculaMultipleForm(initial={'nivel': nivel})
                    form.editar()
                    data['form'] = form
                    if MATRICULACION_POR_NIVEL:
                        if nivel.nivelgrado:
                            data['inscripciones'] = Inscripcion.objects.filter(inscripcionnivel__nivel=nivel.nivelmalla, sede=nivel.sede, carrera=nivel.carrera, retirocarrera__isnull=True, graduado__isnull=True).distinct()
                        else:
                            data['inscripciones'] = Inscripcion.objects.filter(inscripcionnivel__nivel=nivel.nivelmalla, modalidad=nivel.modalidad, sesion=nivel.sesion, sede=nivel.sede, carrera=nivel.carrera, retirocarrera__isnull=True, graduado__isnull=True).distinct()
                    else:
                        data['inscripciones'] = nivel.grupo.miembros()
                    return render(request, "matriculas/addmatriculamulti.html", data)
                except Exception as ex:
                    pass

            elif action == 'delmatricula':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    data['title'] = u'Borrar matricula de estudiante'
                    matricula = Matricula.objects.get(pk=request.GET['id'])
                    data['matricula'] = matricula
                    data['tiene_evaluacion'] = matricula.tiene_evaluacion()
                    return render(request, "matriculas/delmatricula.html", data)
                except Exception as ex:
                    pass

            elif action == 'continua':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    matricula = Matricula.objects.get(pk=request.GET['id'])
                    if not matricula.nivel.cerrado:
                        retiro = matricula.retiromatricula_set.all()
                        retiro.delete()
                        matricula.retiradomatricula = False
                        matricula.save(request)
                        retirnomaterias = MateriaAsignadaRetiro.objects.filter(materiaasignada__matricula=matricula)
                        for rm in retirnomaterias:
                            rm.materiaasignada.retiramateria = False
                            rm.materiaasignada.save(request)
                        log(u'Elimino retiro de matricula: %s' % retiro, request, "del")
                        retirnomaterias.delete()
                    return HttpResponseRedirect("/matriculas?action=matricula&id=" + str(matricula.nivel.id))
                except Exception as ex:
                    pass

            elif action == 'moveranivel':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    data['title'] = u'Mover matricula de estudiante a otro nivel'
                    periodo = request.session['periodo']
                    matricula = Matricula.objects.get(pk=request.GET['id'])
                    data['matricula'] = matricula
                    f = MoverMatriculaNivelForm()
                    if not MATRICULACION_LIBRE:
                        f.for_nivel(matricula)
                    else:
                        f.niveles_activos(periodo)
                    data['form'] = f
                    return render(request, "matriculas/moveranivel.html", data)
                except Exception as ex:
                    pass

            elif action == 'retirar':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    data['title'] = u'Retirar matricula de estudiante'
                    data['matricula'] = Matricula.objects.get(pk=request.GET['id'])
                    data['form'] = RetiradoMatriculaForm()
                    return render(request, "matriculas/retirar.html", data)
                except Exception as ex:
                    pass

            elif action == 'retirarmateria':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    data['title'] = u'Retirar de la materia al estudiante'
                    materiaasignada = MateriaAsignada.objects.get(pk=request.GET['id'])
                    data['materiaasignada'] = materiaasignada
                    data['form'] = RetiradoMateriaForm()
                    return render(request, "matriculas/retirarmateria.html", data)
                except Exception as ex:
                    pass

            elif action == 'continuarmateria':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    materiaasignada = MateriaAsignada.objects.get(pk=request.GET['id'])
                    retiro = materiaasignada.materiaasignadaretiro_set.all()
                    materiaasignada.retiramateria = False
                    materiaasignada.save(request)
                    log(u"Elimino retiro de materia:" + unicode(materiaasignada), request, "del")
                    retiro.delete()
                    return HttpResponseRedirect("/matriculas?action=materias&id=" + str(materiaasignada.matricula.id))
                except Exception as ex:
                    pass

            elif action == 'calificaciontardia':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_calificacion_tardia')
                    data['title'] = u'Calificación tardía'
                    data['materiaasignada'] = MateriaAsignada.objects.get(pk=request.GET['id'])
                    data['calificaciontardia'] = variable_valor('PUEDE_MODICAR_CALIFICACION')
                    data['validardeuda'] = False
                    data['incluyepago'] = False
                    data['incluyedatos'] = False
                    return render(request, "matriculas/calificaciontardia.html", data)
                except Exception as ex:
                    pass

            if action == 'segmento':
                try:
                    data['materiaasignada'] = MateriaAsignada.objects.filter(id=request.GET['idma'])
                    data['auditoriadetalle'] = DetalleModificacionNota.objects.filter(materiaasignada_id=request.GET['idma'])
                    data['materia'] = Materia.objects.get(pk=request.GET['id'])
                    data['validardeuda'] = False
                    data['incluyepago'] = False
                    data['incluyedatos'] = False
                    data['calificaciontardia'] = variable_valor('PUEDE_MODICAR_CALIFICACION')
                    if persona.usuario.is_superuser:
                        data['auditor'] = False
                    else:
                        data['auditor'] = puede_realizar_accion(request, 'sga.puede_modificar_calificacion_tardia')
                    data['cronograma'] = None
                    data['permitecambiarcodigo'] = False
                    return render(request, "matriculas/segmento.html", data)
                except Exception as ex:
                    pass

            if action == 'detallecostosmatricula':
                try:
                    if not 'idm' in request.GET or not request.GET['idm']:
                        return JsonResponse({"result": "bad", "mensaje": u"No se encontró la matrícula"})

                    matricula = Matricula.objects.get(pk=int(encrypt(request.GET['idm'])))
                    matriculagruposocioeconomico = matricula.matriculagruposocioeconomico_set.filter(status=True)
                    lista = []
                    if matriculagruposocioeconomico.values("id").exists():
                        gse = matriculagruposocioeconomico[0].gruposocioeconomico
                    elif matricula.inscripcion.persona.grupoeconomico():
                        gse = matricula.inscripcion.persona.grupoeconomico()
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"No se encontraron datos de la ficha socioeconómica."})

                    periodo = matricula.nivel.periodo
                    inscripcion = matricula.inscripcion
                    if inscripcion.es_pregrado() and periodo.tipocalculo == 6 and periodo and inscripcion.mi_malla():
                        ccm = CostoOptimoMalla.objects.filter(periodo=periodo, malla=inscripcion.mi_malla(), status=True).order_by('-id').first()
                        if not ccm:
                            return JsonResponse({"result": "bad", "mensaje": u"No se encontraron datos en el costo óptimo de la malla."})

                        for conm in ccm.costooptimonivelmalla_set.filter(status=True):
                            lista.append({
                                'nivel': u'%s' % conm.nivelmalla.nombre,
                                'horas': u'%s' % conm.horas,
                                'creditos': u'%s' % conm.creditos,
                                'vct': u'%s' % conm.vct,
                                'get_costoarancel': u'%s' % conm.costooptimogruposocioeconomico_set.filter(gruposocioeconomico=gse, status=True).first().costoarancel if conm.costooptimogruposocioeconomico_set.filter(gruposocioeconomico=gse, status=True).exists() else '',
                            })

                        data['eGrupoSocioEconomico'] = gse
                        data['ePeriodo'] = periodo
                        data['eMalla'] = inscripcion.mi_malla()
                        data['costoMatricula'] = ccm.costomatricula
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error de conexión"})

                    data['listaCostoOptimoMalla'] = lista
                    template = get_template("matriculas/detallecostosmatricula.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'materias':
                try:
                    data['title'] = u'Materias asignadas'
                    data['matricula'] = matricula = Matricula.objects.get(pk=request.GET['id'])
                    # data['poseerubrospagados'] = Rubro.objects.filter(status=True, matricula_id=matricula, cancelado=True).order_by('fecha_creacion').exists() if not persona.usuario.is_superuser() else False
                    data['poseerubrospagados'] = False #Se habilita el boton de eliminar y adicionar materias para todos por pedido de GTA, COLOCAR TRUE PARA QUITAR BOTON
                    data['materiasrepetidas']= MateriaAsignada.objects.values_list('materia__asignatura_id', flat=True).filter(status=True, matricula_id=matricula).annotate(num_registros=Count('materia__asignatura_id')).filter(num_registros__gt=1).exists()
                    ePeriodoMatricula = None
                    if PeriodoMatricula.objects.values('id').filter(status=True, activo=True, periodo=matricula.nivel.periodo).exists():
                        ePeriodoMatricula = PeriodoMatricula.objects.get(status=True, activo=True, periodo=matricula.nivel.periodo)
                    data['ePeriodoMatricula'] = ePeriodoMatricula
                    data['materias'] = materias = matricula.materiaasignada_set.filter(matricula__status=True, status=True)
                    data['carrera'] = matricula.inscripcion.carrera.nombre_completo()
                    materiasnodisponibles = Materia.objects.filter(cerrado=False, nivel__cerrado=False, nivel__periodo=matricula.nivel.periodo, status=True)
                    # if persona.usuario.is_superuser:
                    #     materiasnodisponibles = Materia.objects.filter(cerrado=False, nivel__cerrado=False, nivel__periodo=matricula.nivel.periodo, status=True)
                    # else:
                    #     materiasnodisponibles = Materia.objects.filter(cerrado=False, nivel__cerrado=False, nivel__periodo=matricula.nivel.periodo, status=True).exclude(asignaturamalla__validarequisitograduacion=True, asignaturamalla__nivelmalla_id=8)
                    disponibles = []
                    for materiad in materiasnodisponibles:
                        if materiad.asignatura.id not in disponibles:
                            disponibles.append(materiad.asignatura.id)
                    tomadas = []
                    for materiad in materias:
                        if materiad.materia.asignatura.id not in tomadas:
                            tomadas.append(materiad.materia.asignatura.id)
                    data['asignaturaslibres'] = Asignatura.objects.filter(id__in=disponibles).distinct().order_by('nombre')
                    malla = matricula.inscripcion.malla_inscripcion().malla
                    pendientes_modulos = []
                    for x in malla.modulomalla_set.all():
                        if not matricula.inscripcion.ya_aprobada(x.asignatura):
                            pendientes_modulos.append(x.asignatura)
                    pendientes = []
                    if malla.carrera.coordinacion_carrera().id == 7:
                        asignaturamalla = malla.asignaturamalla_set.filter(status=True).order_by('nivelmalla')
                    else:
                        asignaturamalla = malla.asignaturamalla_set.all().order_by('nivelmalla')
                    # if persona.usuario.is_superuser:
                    #     asignaturamalla = malla.asignaturamalla_set.all().order_by('nivelmalla')
                    # else:
                    #     asignaturamalla = malla.asignaturamalla_set.all().exclude(validarequisitograduacion=True, nivelmalla_id=8).order_by('nivelmalla')
                    for x in asignaturamalla:
                        if not matricula.inscripcion.ya_aprobada(x.asignatura) and not matricula.materiaasignada_set.values('id').filter(materia__asignatura=x.asignatura).exists():
                            if x.asignatura.modulo:
                                pendientes_modulos.append(x.asignatura)
                            else:
                                pendientes.append(x)
                    data['pendientes'] = pendientes
                    data['pendientes_modulos'] = pendientes_modulos
                    data['recordsp'] = RecordAcademico.objects.filter(inscripcion=matricula.inscripcion, aprobada=True).order_by('asignatura')
                    data['calculo_por_credito'] = CALCULO_POR_CREDITO
                    data['usa_evaluacion_integral'] = USA_EVALUACION_INTEGRAL
                    data['usa_retiro_materia'] = USA_RETIRO_MATERIA
                    # data['permiteagregaciones'] = matricula.nivel.periodo.limite_agregacion >= datetime.now().date()
                    data['permiteagregaciones'] = True if persona.usuario.is_superuser else matricula.nivel.periodo.puede_agregar_secretaria()
                    # data['permiteretiro'] = matricula.nivel.periodo.limite_retiro >= datetime.now().date()
                    data['permiteretiro'] = True if persona.usuario.is_superuser else matricula.nivel.periodo.puede_quitar_secretaria()
                    data['utiliza_gratuidades'] = UTILIZA_GRATUIDADES
                    data['valor_pendiente'] = matricula.total_saldo_rubro()
                    data['valor_pagados'] = matricula.total_pagado_rubro_sin_liquidados()
                    data['valor_liquidados'] = matricula.total_liquidado_rubro()
                    data['idasignaturasingles'] = AsignaturaMalla.objects.values_list('asignatura_id', flat=True).filter(status=True, malla__carrera__id=34).distinct()
                    periodoslibres = Periodo.objects.filter(pk__in=Materia.objects.values_list('nivel__periodo__id', flat=True).filter(asignaturamalla__malla__carrera__coordinacion__id=7, cerrado=False, nivel__cerrado=False).distinct())
                    data['periodoslibres'] = periodoslibres
                    data['NOTIFICACIÓN_NO_MATRICULARSE_OTRA_VEZ'] = 'Aun no esta habilitada la matriculación por mas de una vez en las materia'
                    data['NOTIFICACIÓN_NO_MATRICULARSE_EN_MAS_MATERIAS'] = 'No puede matricularse en mas materias por motivo que tiene materia 3ra de matricula.'
                    data['PUEDE_MATRICULARSE_OTRA_VEZ'] = variable_valor('PUEDE_MATRICULARSE_OTRA_VEZ')
                    data['puede_ver_mis_finanzas'] = matricula.inscripcion.es_pregrado() and matricula.nivel.periodo.tipocalculo == 6
                    return render(request, "matriculas/materias.html", data)
                except Exception as ex:
                    pass

            elif action == 'delmateria':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    data['title'] = u'Eliminar materia de asignadas'
                    data['materiaasignada'] = MateriaAsignada.objects.get(pk=request.GET['id'])
                    return render(request, "matriculas/delmateria.html", data)
                except Exception as ex:
                    pass

            elif action == 'sinasistencia':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    data['title'] = u'No tomar en cuenta asistencia'
                    data['materiaasignada'] = MateriaAsignada.objects.get(pk=request.GET['id'])
                    return render(request, "matriculas/sinasistencia.html", data)
                except Exception as ex:
                    pass

            elif action == 'conasistencia':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    data['title'] = u'Tomar en cuenta asistencia'
                    data['materiaasignada'] = MateriaAsignada.objects.get(pk=request.GET['id'])
                    return render(request, "matriculas/conasistencia.html", data)
                except Exception as ex:
                    pass

            elif action == 'importar_nota_proveedor':
                try:
                    with transaction.atomic():
                            periodo = request.session["periodo"].nombre
                            materiaasignada_id =  int(request.GET.get("materia_asignada_id",0))
                            if materiaasignada_id == 0:
                                return JsonResponse({'result': False, "sms":"Parametro no encontrado"})
                            materiaasignada = MateriaAsignada.objects.get(pk=materiaasignada_id)

                            idcursomoodle = materiaasignada.materia.idcursomoodle
                            url = 'https://upei.buckcenter.edu.ec/usernamecoursetograde.php?username=%s&curso=%s' % ( materiaasignada.matricula.inscripcion.persona.identificacion(), idcursomoodle)
                            req = Request(url)
                            response = urlopen(req)
                            result = json.loads(response.read().decode())
                            idcurso = int(result['idcurso'])
                            valores = 0
                            rubros = materiaasignada.rubro.filter(status=True, observacion=f'{periodo}')
                            for rubro in rubros:
                                valores = rubro.total_pagado()
                            #         tiene_pagos=False
                            # if tiene_pagos:
                            if idcurso == idcursomoodle:
                                try:
                                    nota = null_to_decimal(result['nota'], 0)
                                except:
                                    if result['nota'] == '-' or result['nota'] == None:
                                        nota = 0
                                if nota >= 70 and materiaasignada.cerrado == False:
                                    if nota != materiaasignada.notafinal and type(nota) in [int, float]:
                                            campo = materiaasignada.campo('EX')
                                            actualizar_nota_planificacion(materiaasignada.id, 'EX', nota)
                                            auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,calificacion=nota)
                                            auditorianotas.save(request)
                                            materiaasignada.importa_nota = True
                                            materiaasignada.cerrado = True
                                            materiaasignada.fechacierre = datetime.now().date()
                                            materiaasignada.save(request)
                                            d = locals()
                                            exec(materiaasignada.materia.modeloevaluativo.logicamodelo, globals(), d)
                                            d['calculo_modelo_evaluativo'](materiaasignada)
                                            materiaasignada.cierre_materia_asignada()
                                            print(u"IMPORTA Y CIERRA -- %s" % (materiaasignada))
                                elif materiaasignada.cerrado == True:
                                    if nota != materiaasignada.notafinal and type(nota) in [int, float]:
                                            campo = materiaasignada.campo('EX')
                                            actualizar_nota_planificacion(materiaasignada.id, 'EX', nota)
                                            auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
                                                                            calificacion=nota)
                                            auditorianotas.save(request)
                                            materiaasignada.importa_nota = True
                                            materiaasignada.cerrado = True
                                            materiaasignada.fechacierre = datetime.now().date()
                                            materiaasignada.save(request)
                                            d = locals()
                                            exec(materiaasignada.materia.modeloevaluativo.logicamodelo, globals(), d)
                                            d['calculo_modelo_evaluativo'](materiaasignada)
                                            materiaasignada.cierre_materia_asignada()
                                            print(u"IMPORTA Y CIERRA -- %s" % (materiaasignada))
                                else:
                                    return JsonResponse({'result': False, "sms": "Nota menor a 70 , materia asignada abierta, no se puede importar. Cierre primero."})

                            else:
                                return JsonResponse({'result': False, "sms":"Id curso moodle no coincide"})
                    return JsonResponse({'result': True, "sms":"Nota importada correctamente"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': False, "sms": f"{ex}"})
                    print('error: %s' % (ex))

            elif action == 'autorizarevaluacion':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_autorizacion_evaluacion')
                    data['title'] = u'Autorizado a evaluar'
                    data['materiaasignada'] = MateriaAsignada.objects.get(pk=request.GET['id'])
                    return render(request, "matriculas/autorizarevaluacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'promote':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    data['title'] = u'Seleccionar materia para alumno'
                    data['asignatura'] = asignatura = Asignatura.objects.get(pk=request.GET['id'])
                    data['matricula'] = matricula = Matricula.objects.get(pk=request.GET['matricula'])
                    solomimalla = False
                    if matricula.inscripcion.mi_malla():
                        if matricula.inscripcion.mi_malla().asignaturamalla_set.filter(validarequisitograduacion=True, asignatura=asignatura, status=True):
                            solomimalla = True

                    if solomimalla:
                        data['materias'] = Materia.objects.filter(asignaturamalla__malla=matricula.inscripcion.mi_malla(), asignatura=asignatura, nivel__periodo=matricula.nivel.periodo, cerrado=False, nivel__cerrado=False)
                    else:
                        data['materias'] = Materia.objects.filter(asignatura=asignatura, nivel__periodo=matricula.nivel.periodo, cerrado=False, nivel__cerrado=False)
                    data['homitircapacidadhorario'] = HOMITIRCAPACIDADHORARIO
                    data['permiteagregaciones'] = matricula.nivel.periodo.limite_agregacion >= datetime.now().date()
                    return render(request, "matriculas/promote.html", data)
                except Exception as ex:
                    pass

            elif action == 'promotecohorte':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    data['title'] = u'Seleccionar materia para alumno'
                    data['asignatura'] = asignatura = Asignatura.objects.get(pk=request.GET['id'])
                    data['matricula'] = matricula = Matricula.objects.get(pk=request.GET['matricula'])
                    if Materia.objects.filter(asignatura=asignatura, asignaturamalla__malla__carrera=matricula.inscripcion.carrera).exclude(nivel__periodo__lte=matricula.nivel.periodo):
                        data['materias'] = Materia.objects.filter(asignatura=asignatura, asignaturamalla__malla__carrera=matricula.inscripcion.carrera).exclude(nivel__periodo__lte=matricula.nivel.periodo).order_by('id')
                    else:
                        listadohomologacion = AsignaturaMallaHomologacion.objects.values_list('asignaturamalla__asignatura_id', flat=True).filter(homologacion__asignatura=asignatura,homologacion__malla__carrera=matricula.inscripcion.carrera, status=True)
                        data['materias'] = Materia.objects.filter(asignatura_id__in=listadohomologacion, asignaturamalla__malla__carrera=matricula.inscripcion.carrera).exclude(asignatura_id__in=matricula.materiaasignada_set.values_list('materia__asignatura_id', flat=True).filter(materia__asignatura_id__in=listadohomologacion,status=True)).order_by('id')
                    data['homitircapacidadhorario'] = HOMITIRCAPACIDADHORARIO
                    data['permiteagregaciones'] = matricula.nivel.periodo.limite_agregacion >= datetime.now().date()
                    return render(request, "matriculas/promotecohorte.html", data)
                except Exception as ex:
                    pass

            elif action == 'movermateriasession':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    data['title'] = u'Mover materia de session'
                    data['materiaasignada'] = materiaasignada = MateriaAsignada.objects.get(pk=request.GET['id'])
                    data['materias'] = Materia.objects.filter(asignatura=materiaasignada.materia.asignatura, nivel__periodo=materiaasignada.matricula.nivel.periodo, cerrado=False, nivel__cerrado=False).exclude(id=materiaasignada.materia.id)
                    data['matricula'] = materiaasignada.matricula
                    data['homitircapacidadhorario'] = HOMITIRCAPACIDADHORARIO
                    return render(request, "matriculas/movermateriasession.html", data)
                except Exception as ex:
                    pass

            elif action == 'validapararecord':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    materiaasignada = MateriaAsignada.objects.get(pk=request.GET['id'])
                    retiro = materiaasignada.retiro()
                    retiro.valida = True
                    retiro.save(request)
                    return HttpResponseRedirect("/matriculas?action=materias&id=" + str(materiaasignada.matricula.id))
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            elif action == 'calcular':
                try:
                    data['title'] = u'Recalcular valores de cobros en la matriculación'
                    data['matricula'] = Matricula.objects.get(pk=request.GET['id'])
                    return render(request, "matriculas/calcular.html", data)
                except Exception as ex:
                    pass

            elif action == 'quitardiferir':
                try:
                    data['title'] = u'Quitar diferido valores de cobros en la matriculación'
                    data['matricula'] = Matricula.objects.get(pk=request.GET['id'])
                    return render(request, "matriculas/quitardiferido.html", data)
                except Exception as ex:
                    pass

            elif action == 'diferir':
                try:
                    data['title'] = u'Diferir valores de cobros en la matriculación'
                    data['matricula'] = Matricula.objects.get(pk=request.GET['id'])
                    return render(request, "matriculas/diferir.html", data)
                except Exception as ex:
                    pass

            elif action == 'novalidapararecord':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    materiaasignada = MateriaAsignada.objects.get(pk=request.GET['id'])
                    retiro = materiaasignada.retiro()
                    retiro.valida = False
                    retiro.save(request)
                    return HttpResponseRedirect("/matriculas?action=materias&id=" + str(materiaasignada.matricula.id))
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            elif action == 'convalidar':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    data['title'] = u'Homologación de materia'
                    data['materiaasignada'] = materiaasignada = MateriaAsignada.objects.get(pk=request.GET['id'])
                    if materiaasignada.materiaasignadaconvalidacion_set.values('id').exists():
                        materiaasignadaconvalidacion = materiaasignada.materiaasignadaconvalidacion_set.all()[0]
                        data['form'] = ConvalidacionInscripcionForm(initial={'asignatura': materiaasignadaconvalidacion.convalidacion.asignatura,
                                                                             'centro': materiaasignadaconvalidacion.convalidacion.centro,
                                                                             'carrera': materiaasignadaconvalidacion.convalidacion.carrera,
                                                                             'creditos': materiaasignadaconvalidacion.convalidacion.creditos,
                                                                             'observaciones': materiaasignadaconvalidacion.convalidacion.observaciones,
                                                                             'nota_ant': materiaasignadaconvalidacion.convalidacion.nota_ant,
                                                                             'nota_act': materiaasignadaconvalidacion.convalidacion.nota_act,
                                                                             'anno': materiaasignadaconvalidacion.convalidacion.anno})
                    else:
                        data['form'] = ConvalidacionInscripcionForm(initial={'asignatura': materiaasignada.materia.asignatura.nombre,
                                                                             'creditos': materiaasignada.materia.creditos,
                                                                             'nota_ant': 0,
                                                                             'nota_act': 0,
                                                                             'anno': datetime.now().date().year})
                    return render(request, "matriculas/convalidar.html", data)
                except Exception as ex:
                    pass

            elif action == 'fechaasignacion':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    data['title'] = u'Cambiar fecha asignacion de la materia'
                    data['materiaasignada'] = materiaasignada = MateriaAsignada.objects.get(pk=request.GET['id'])
                    data['form'] = CambioFechaAsignacionMateriaForm(initial={'fecha': materiaasignada.matricula.fecha})
                    return render(request, "matriculas/fechaasignacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'delconvalidacion':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    materiaasignada = MateriaAsignada.objects.get(pk=request.GET['id'])
                    if materiaasignada.materiaasignadaconvalidacion_set.values('id').exists():
                        materiaasignadaconvalidacion = materiaasignada.materiaasignadaconvalidacion_set.all()[0]
                        log(u'Elimino convalidacion de materia: %s' % materiaasignadaconvalidacion, request, "del")
                        materiaasignadaconvalidacion.delete()
                    return HttpResponseRedirect("matriculas?action=materias&id=" + str(materiaasignada.matricula.id))
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            elif action == 'delhomologacion':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    materiaasignada = MateriaAsignada.objects.get(pk=request.GET['id'])
                    if materiaasignada.materiaasignadahomologacion_set.values('id').exists():
                        materiaasignadahomologacion = materiaasignada.materiaasignadahomologacion_set.all()[0]
                        log(u'Elimino homologacion de materia: %s' % materiaasignada, request, "del")
                        materiaasignadahomologacion.delete()
                    return HttpResponseRedirect("matriculas?action=materias&id=" + str(materiaasignada.matricula.id))
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            elif action == 'homologar':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    data['title'] = u'Homologacion de materia'
                    materiaasignada = MateriaAsignada.objects.get(pk=request.GET['id'])
                    if materiaasignada.materiaasignadahomologacion_set.values('id').exists():
                        materiaasignadahomologacion = materiaasignada.materiaasignadahomologacion_set.all()[0]
                        data['form'] = HomologacionInscripcionForm(initial={'carrera': materiaasignadahomologacion.homologacion.carrera,
                                                                            'asignatura': materiaasignadahomologacion.homologacion.asignatura,
                                                                            'fecha': materiaasignadahomologacion.homologacion.fecha,
                                                                            'nota_ant': materiaasignadahomologacion.homologacion.nota_ant,
                                                                            'creditos': materiaasignadahomologacion.homologacion.creditos,
                                                                            'observaciones': materiaasignadahomologacion.homologacion.observaciones})
                    else:
                        data['form'] = HomologacionInscripcionForm(initial={'fecha': datetime.now().date(),
                                                                            'nota_ant': 0,
                                                                            'creditos': materiaasignada.materia.creditos})
                    data['materiaasignada'] = materiaasignada
                    return render(request, "matriculas/homologar.html", data)
                except Exception as ex:
                    pass

            elif action == 'actualizarrecord':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    materiaasignada = MateriaAsignada.objects.get(pk=request.GET['id'])
                    materiaasignada.cierre_materia_asignada()
                    log(u'Actualizar record: %s' % materiaasignada, request, "edit")
                    return HttpResponseRedirect("matriculas?action=materias&id=" + str(materiaasignada.matricula.id))
                except Exception as ex:
                    pass

            elif action == 'confirmar_actualizacion_estudiantes':
                try:
                    data['title'] = u'Confirmar acualización de estudiantes'
                    data['matricula'] = Matricula.objects.get(pk=request.GET['idm'])
                    data['materia'] = Materia.objects.get(pk=int(request.GET['id']))
                    return render(request, "matriculas/confirmar_actualizacion_estudiantes.html", data)
                except Exception as ex:
                    pass

            elif action == 'confirmar_actualizacion_un_estudiante':
                try:
                    data['title'] = u'Confirmar acualización de estudiantes'
                    data['matricula'] = Matricula.objects.get(pk=request.GET['idm'])
                    data['materia'] = Materia.objects.get(pk=int(request.GET['id']))
                    return render(request, "matriculas/confirmar_actualizacion_un_estudiante.html", data)
                except Exception as ex:
                    pass

            elif action == 'ver_notas':
                try:
                    data['inscripcion'] = Inscripcion.objects.filter(id=request.GET['idinscripcion'])[0]
                    data['materiasasignadas'] = maateriaasignada = MateriaAsignada.objects.filter(id=request.GET['idcurso'])
                    data['matricula'] = maateriaasignada[0].matricula
                    return render(request, "matriculas/ver_notas.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Matriculas de alumnos'
            if MATRICULACION_LIBRE:
                return HttpResponseRedirect("/niveles")
            periodo = request.session['periodo']
            data['sedes'] = Sede.objects.all()
            data['carreras'] = Carrera.objects.all()
            data['niveles'] = Nivel.objects.filter(periodo=data['periodo'], carrera__in=data['carreras']).order_by('paralelo')
            data['niveles_abiertos'] = Nivel.objects.filter(cerrado=False, periodo=data['periodo'], carrera__in=data['carreras'])
            data['niveles_cerrados'] = Nivel.objects.filter(cerrado=True, periodo=data['periodo'], carrera__in=data['carreras'])
            data['usa_nivel0'] = UTILIZA_NIVEL0_PROPEDEUTICO
            data['total_matriculados'] = Matricula.objects.filter(nivel__periodo=periodo).count()
            data['total_retirados'] = RetiroMatricula.objects.filter(matricula__nivel__periodo=periodo).count()
            data['total_actual'] = data['total_matriculados'] - data['total_retirados']
            return render(request, "matriculas/view.html", data)
