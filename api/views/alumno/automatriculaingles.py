# coding=utf-8
import json
from datetime import datetime, timedelta

from django.db import transaction
from django.db.models import Q, Sum
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.automatriculaingles import AsignaturaSerializer, InscripcionSerializer, MallaSerializer, \
    NivelSerializer
from sagest.models import Rubro
from settings import MATRICULACION_LIBRE, MAXIMO_MATERIA_ONLINE, PORCIENTO_PERDIDA_PARCIAL_GRATUIDAD, \
    PORCIENTO_PERDIDA_TOTAL_GRATUIDAD, NIVEL_MALLA_CERO, NOTA_ESTADO_EN_CURSO, HOMITIRCAPACIDADHORARIO
from sga.commonviews import nivel_matriculacion, \
    conflicto_materias_estudiante, matricular
from sga.funciones import variable_valor, log, null_to_decimal, fechatope, to_unicode
from sga.models import PerfilUsuario, Nivel, AsignaturaMalla, Periodo, Asignatura, Materia, AlumnosPracticaMateria, \
    MateriaAsignada, Matricula, NivelLibreCoordinacion, ConfirmarMatricula
from sga.templatetags.sga_extras import encrypt


def matricular_modulo_informatica(request, matricula, materias, persona, periodo):
    with transaction.atomic():
        for materia in materias:
            if not materia.capacidad_disponible() > 0:
                raise NameError(f"Capacidad limite de la materia: {materia.asignatura}, seleccione otro.")
        for materia in materias:
            matriculas = matricula.inscripcion.historicorecordacademico_set.filter(asignatura=materia.asignatura, status=True).count() + 1
            if matricula.materiaasignada_set.filter(materia=materia).exists():
                raise NameError("Ya se encuentra matriculado en esta materia: " + materia.nombre_completo())

            materiaasignada = MateriaAsignada(matricula=matricula,
                                              materia=materia,
                                              notafinal=0,
                                              asistenciafinal=100,
                                              cerrado=False,
                                              matriculas=matriculas,
                                              observaciones='',
                                              estado_id=NOTA_ESTADO_EN_CURSO
                                              )
            materiaasignada.save(request)
            materiaasignada.asistencias()
            materiaasignada.evaluacion()
            materiaasignada.mis_planificaciones()
        log(u'Automatricula modulos informática: %s' % matricula, request, "add")
        if not matricula.confirmarmatricula_set.filter(matricula=matricula):
            confirmar = ConfirmarMatricula(matricula=matricula, estado=True)
            confirmar.save(request)
            log(u'Confirmo la matricula de informatica: %s' % confirmar, request, "add")
        mensaje = "Se ha matriculado correctamente"
        return mensaje

def matricular_modulo_ingles_con_matricula(request, matricula, materias, persona, periodo):
    with transaction.atomic():
        for materia in materias:
            if not materia.capacidad_disponible() > 0:
                raise NameError(f"Capacidad limite de la materia: {materia.asignatura}, seleccione otro.")
        for materia in materias:
            matriculas = matricula.inscripcion.historicorecordacademico_set.filter(asignatura=materia.asignatura, status=True).count() + 1
            if matricula.materiaasignada_set.filter(materia=materia).exists():
                raise NameError("Ya se encuentra matriculado en esta materia: " + materia.nombre_completo())

            materiaasignada = MateriaAsignada(matricula=matricula,
                                              materia=materia,
                                              notafinal=0,
                                              asistenciafinal=100,
                                              cerrado=False,
                                              matriculas=matriculas,
                                              observaciones='',
                                              estado_id=NOTA_ESTADO_EN_CURSO
                                              )
            materiaasignada.save(request)
            materiaasignada.asistencias()
            materiaasignada.evaluacion()
            materiaasignada.mis_planificaciones()
            if matriculas > 1 or matricula.inscripcion.persona.tiene_otro_titulo(matricula.inscripcion):
                matricula.nuevo_calculo_matricula_ingles(materiaasignada)
        log(u'Automatricula modulos ingles: %s' % matricula, request, "add")
        if not matricula.confirmarmatricula_set.filter(matricula=matricula):
            confirmar = ConfirmarMatricula(matricula=matricula, estado=True)
            confirmar.save(request)
            log(u'Confirmo la matricula ingles no egresado: %s' % confirmar, request, "add")
        valorpagar = int(null_to_decimal(Rubro.objects.filter(status=True, persona=persona, cancelado=False, observacion="INGLÉS %s" % periodo.nombre).aggregate(valor=Sum('valortotal'))['valor']))
        mensaje = "Se ha matriculado correctamente" if valorpagar == 0 else f"Se ha matriculado correctamente, valor a pagar : {valorpagar}"
        return mensaje


def matricular_modulos_ingles_egresado(request, inscripcion, nivel_matricular, periodo_matricular, materias, persona, tipo_matricula):
    with transaction.atomic():
        for materia in materias:
            if materia.capacidad_disponible() <= 0:
                raise NameError(f"Capacidad limite de la materia: {materia.asignatura}, seleccione otro.")

        if not inscripcion.matriculado_periodo(periodo_matricular):
            matricula = Matricula(inscripcion=inscripcion,
                                  nivel=nivel_matricular,
                                  pago=False,
                                  iece=False,
                                  becado=False,
                                  porcientobeca=0,
                                  fecha=datetime.now().date(),
                                  hora=datetime.now().time(),
                                  fechatope=fechatope(datetime.now().date()))
            matricula.save(request)
            matricula.tipomatricula.id = tipo_matricula
            matricula.save(request)
            matricula.actualiza_matricula()
            matricula.inscripcion.actualiza_estado_matricula()
            matricula.grupo_socio_economico(tipo_matricula)
            matricula.calcula_nivel()
            for materia in materias:
                matriculas = matricula.inscripcion.historicorecordacademico_set.filter(asignatura=materia.asignatura, fecha__lt=materia.nivel.fin, status=True).count() + 1
                materiaasignada = MateriaAsignada(matricula=matricula,
                                                  materia=materia,
                                                  notafinal=0,
                                                  asistenciafinal=100,
                                                  cerrado=False,
                                                  matriculas=matriculas,
                                                  observaciones='',
                                                  estado_id=NOTA_ESTADO_EN_CURSO
                                                  )
                materiaasignada.save(request)
                materiaasignada.asistencias()
                materiaasignada.evaluacion()
                materiaasignada.mis_planificaciones()
                materiaasignada.save(request)
                if matriculas > 1 or matricula.inscripcion.persona.tiene_otro_titulo(matricula.inscripcion):
                    matricula.nuevo_calculo_matricula_ingles(materiaasignada)
                log(u'Materia seleccionada matricula: %s' % materiaasignada, request, "add")

            if not matricula.confirmarmatricula_set.filter(matricula=matricula):
                confirmar = ConfirmarMatricula(matricula=matricula, estado=True)
                confirmar.save(request)
                log(u'Confirmo la matricula ingles egresado: %s' % confirmar, request, "add")

        valorpagar = int(null_to_decimal(Rubro.objects.filter(status=True, persona=persona, cancelado=False, observacion="INGLÉS %s" % periodo_matricular.nombre).aggregate(valor=Sum('valortotal'))['valor']))
        mensaje = "Se ha matriculado correctamente" if valorpagar == 0 else f"Se ha matriculado correctamente, valor a pagar : {valorpagar}"
        return mensaje


def materias_abiertas(asignatura, materiasabiertas):
    materias = []
    for materia in materiasabiertas:
        mat = []
        origen = materia.nivel.nivellibrecoordinacion_set.all()[0].coordinacion.alias if materia.nivel.nivellibrecoordinacion_set.exists() else materia.nivel.carrera.nombre
        paralelo = materia.paralelo
        if materia.capacidad_disponible() > 0:
            mat = {'nivel': to_unicode(materia.nivel.nivelmalla.nombre) if materia.nivel.nivelmalla else "",
                   'id': materia.pk,
                   'sede': to_unicode(materia.nivel.sede.nombre) if materia.nivel.sede else "",
                   'tipomateria': materia.tipomateria,
                   'inicio': materia.inicio.strftime("%d-%m-%Y"),
                   'session': to_unicode(materia.nivel.sesion.nombre),
                   'fin': materia.fin.strftime("%d-%m-%Y"), 'identificacion': materia.identificacion,
                   'coordcarrera': origen,
                   'paralelo': paralelo,
                   'cupo': materia.cupo,
                   'matriculados': materia.cantidad_matriculas_materia_sin_retirados(),
                   'carrera': to_unicode(materia.asignaturamalla.malla.carrera.nombre) if materia.asignaturamalla.malla.carrera.nombre else "",
                   }

            materias.append(mat)

    respuesta = {
        "pk": asignatura.id,
        "asignatura": str(asignatura.nombre),
        "abiertas": len(materiasabiertas),
        "disponibles": len(materias),
        "materias": materias
    }
    lista_respuesta = [respuesta]

    return lista_respuesta


def tiene_rubros_sin_cancelar(periodo=None, matricula=None, persona=None, tiene_matricula=True):
    from django.db.models import Q
    # ID_MODULOS_DE_INGLES = 6
    # valores = 0
    # ids_niveles = NivelLibreCoordinacion.objects.values_list('nivel_id',flat=True).filter(status=True, coordinacion_id=ID_MODULOS_DE_INGLES, nivel__periodo=periodo)
    # if tiene_matricula:
    #     materiasasignadas = MateriaAsignada.objects.filter(status=True,
    #                                                        materia__inglesepunemi=True,
    #                                                        matricula = matricula,
    #                                                        retiramateria=False,
    #                                                        materia__nivel__in=ids_niveles,
    #                                                        materia__status=True
    #                                                        )
    #
    #     for materia in materiasasignadas:
    #         rubros = materia.rubro.filter(observacion='INGLÉS ABRIL - AGOSTO 2023',status=True)
    #         for rubro in rubros:
    #             valores = rubro.total_pagado()
    #             if valores == 0: return True
    # else:
    tiene_deuda = False
    eRubros = Rubro.objects.filter(status=True, persona=persona, observacion__icontains='INGLÉS', fechavence__lt=datetime.now().date()).exclude(cancelado=True)
    for rubro in eRubros:
        valores = rubro.total_pagado()
        if valores == 0: tiene_deuda = True

    return tiene_deuda


def es_bloqueado_por_no_realizar_el_curso_en_buckingham(matricula):
    return True if matricula.observaciones == "admin_sga bloqueado_buckingham" else False

def matricular_en_periodo(request, inscripcion, nivel_matricular, tipomatricula):
    matricula = None
    try:
        matricula = Matricula(inscripcion=inscripcion,
                              nivel=nivel_matricular,
                              pago=False,
                              iece=False,
                              becado=False,
                              porcientobeca=0,
                              fecha=datetime.now().date(),
                              hora=datetime.now().time(),
                              fechatope=fechatope(datetime.now().date()))
        matricula.save(request)
        matricula.tipomatricula.id = tipomatricula
        matricula.save(request)
        matricula.actualiza_matricula()
        matricula.inscripcion.actualiza_estado_matricula()
        matricula.grupo_socio_economico(tipomatricula)
        matricula.calcula_nivel()
        return Matricula.object.filter(id=matricula.id)
    except Exception as ex:
        return matricula


class AutomatriculaInglesAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = 'ALUMNO_MATRI_MODULO_INGLES_KEY'

    @api_security
    def post(self, request):
        hoy = datetime.now().date()
        payload = request.auth.payload
        ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(payload['perfilprincipal']['id']))
        inscripcion = ePerfilUsuario.inscripcion
        persona = ePerfilUsuario.persona
        periodo = Periodo.objects.get(pk=int(encrypt(payload['periodo']['id'])))

        if not ePerfilUsuario.es_estudiante():
            raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')

        if 'multipart/form-data' in request.content_type:
            eRequest = request._request.POST
        else:
            eRequest = request.data
        try:
            if not 'action' in eRequest:
                raise NameError(u'Parametro de acciòn no encontrado')

            action = eRequest['action']

            if action == 'seeleccionarMateria':
                try:
                    id = int(eRequest['id'])
                    materia = Materia.objects.get(pk=id)
                    if inscripcion.matriculado():
                        matricula = inscripcion.matricula()
                        materiaasignada = matricula.materiaasignada_set.filter(status=True, materia=materia)
                        if materiaasignada.exists():
                            raise NameError(f"Ya se encuentra matriculado en el módulo : {materiaasignada.first()}")

                    if not materia.capacidad_disponible() > 0:
                        raise NameError("Lo sentimos, se termino el cupo, seleccione otro.")

                    aData = {}
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            if action == 'matricular':
                try:
                    if not variable_valor('ACTIVA_MATRICULA_MODULOS_INGLES'):
                        raise NameError('Lo sentimos, la matriculación no se encuentra activa en este momento')
                    mismaterias = eRequest['idsMaterias']
                    nivel_matricular = Nivel.objects.get(pk=variable_valor('NIVEL_ACTUAL_MATRICULA_INGLES_ID'))
                    periodo_matricular = nivel_matricular.periodo
                    TIPOS_MATRICULA = {
                        "ORDINARIA": 1,
                    }
                    materias = Materia.objects.filter(status=True, id__in=[int(x) for x in mismaterias])
                    matricula = inscripcion.matricula_periodo(periodo_matricular) #Se obtiene la matricula del periodo actual de los módulos
                    if not matricula: # Se verifica si no esta matriculado en el periodo actual de los módulos, de no existir se lo matricula
                        matricula = matricular_en_periodo(request, inscripcion, nivel_matricular, TIPOS_MATRICULA["ORDINARIA"])
                    if not matricula: # Se verifica nuevamente si se lo matriuclo con el proceso pasado, si hubo error no se permite continuar
                        raise NameError('Lo sentimos, no pudimos matricularte en este módulo')
                    # if matricula:  # es egresado
                        # matricula = inscripcion.matricula()
                    mensaje = matricular_modulo_ingles_con_matricula(request, matricula, materias, persona, periodo)
                    # else:
                    #     mensaje = matricular_modulos_ingles_egresado(request, inscripcion, nivel_matricular, periodo_matricular, materias, persona, TIPOS_MATRICULA["ORDINARIA"])
                    aData = {
                        "mensaje": mensaje
                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)
            if action == 'matricularInformatica':
                try:
                    if not variable_valor('ACTIVA_MATRICULA_MODULOS_INFORMATICA'):
                        raise NameError('Lo sentimos, la matriculación no se encuentra activa en este momento')
                    mismaterias = eRequest['idsMaterias']
                    nivel_matricular = Nivel.objects.get(pk=variable_valor('NIVEL_ACTUAL_MATRICULA_INFORMATICA_ID'))
                    periodo_matricular = nivel_matricular.periodo
                    TIPOS_MATRICULA = {
                        "ORDINARIA": 1,
                    }
                    materias = Materia.objects.filter(status=True, id__in=[int(x) for x in mismaterias])
                    matricula = inscripcion.matricula_periodo(periodo_matricular)
                    if not matricula:
                        matricula = matricular_en_periodo(request, inscripcion, nivel_matricular, TIPOS_MATRICULA["ORDINARIA"])
                    if not matricula:
                        raise NameError('Lo sentimos, no pudimos matricularte en este módulo')
                    mensaje = matricular_modulo_informatica(request, matricula, materias, persona, periodo)
                    aData = {"mensaje": mensaje}
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'desmatricular':
                try:
                    if not eRequest['idMateria']:
                        raise NameError("Lo sentimos, no encontramos la materia.")
                    nivel_matricular = Nivel.objects.get(pk=variable_valor('NIVEL_ACTUAL_MATRICULA_INGLES_ID'))
                    materia_id = int(encrypt(eRequest['idMateria']))
                    materia_alumno = MateriaAsignada.objects.filter(materia__asignatura_id=materia_id, materia__nivel_id=nivel_matricular, matricula__inscripcion=inscripcion).first()
                    if not materia_alumno:
                        raise NameError(f"Usted ya se encuentra desmatriculado de este módulo")
                    materia = materia_alumno.materia
                    materiaasigadamodulo = MateriaAsignada.objects.filter(status=True, materia=materia, matricula__inscripcion=inscripcion).first()
                    # if rubro := Rubro.objects.filter(persona=persona, cancelado=False, observacion="INGLÉS %s" % materia.nivel.periodo.nombre).exists():
                    if rubro := materiaasigadamodulo.rubro.filter(persona=persona, cancelado=False, observacion="INGLÉS %s" % materia.nivel.periodo.nombre).first():
                        if rubro.tiene_pagos():
                            raise NameError(f"Lo sentimos, no puede desmatricularse de este módulo porque tiene pagos realizados")
                        log(u'Eliminó rubro de inglés por desmatriculacion de módulo: %s' % materiaasigadamodulo.matricula, request, "del")
                        rubro.delete()
                        from matricula.models import DetalleRubroMatricula
                        if detallerubros := DetalleRubroMatricula.objects.filter(status=True, matricula=materiaasigadamodulo.matricula, materia=materia).first():
                            detallerubros.delete()
                    log(u'Eliminó modulos de inglés: %s' % materiaasigadamodulo.matricula, request, "del")
                    materiaasigadamodulo.delete()
                    if matriculaactual := Matricula.objects.filter(nivel__periodo_id=materia.nivel.periodo_id, inscripcion=inscripcion).exclude(retiradomatricula=True).first():
                        if not matriculaactual.materiaasignada_set.filter(status=True):
                            matriculaactual.delete()
                            log(u'Eliminó matricula por ultima asignatura: %s' % matriculaactual, request, "del")
                    return Helper_Response(isSuccess=True, data={}, message=f'Se ha desmatriculado correctamente!', status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)
            if action == 'desmatricularInformatica':
                try:
                    if not eRequest['idMateria']:
                        raise NameError("Lo sentimos, no encontramos la materia.")
                    nivel_matricular = Nivel.objects.get(pk=variable_valor('NIVEL_ACTUAL_MATRICULA_INFORMATICA_ID'))
                    materia_id = int(encrypt(eRequest['idMateria']))
                    materia_alumno = MateriaAsignada.objects.filter(materia__asignatura_id=materia_id, materia__nivel_id=nivel_matricular, matricula__inscripcion=inscripcion).first()
                    if not materia_alumno:
                        raise NameError(f"Usted ya se encuentra desmatriculado de este módulo")
                    materia = materia_alumno.materia
                    materiaasigadamodulo = MateriaAsignada.objects.filter(status=True, materia=materia, matricula__inscripcion=inscripcion).first()
                    log(u'Eliminó modulos de informática: %s' % materiaasigadamodulo.matricula, request, "del")
                    materiaasigadamodulo.delete()
                    if matriculaactual := Matricula.objects.filter(nivel__periodo_id=materia.nivel.periodo_id, inscripcion=inscripcion).exclude(retiradomatricula=True).first():
                        if not matriculaactual.materiaasignada_set.filter(status=True):
                            matriculaactual.delete()
                            log(u'Eliminó matricula por ultima asignatura: %s' % matriculaactual, request, "del")
                    return Helper_Response(isSuccess=True, data={}, message=f'Se ha desmatriculado correctamente!', status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)
            return Helper_Response(isSuccess=False, data={}, message=f'Acciòn no encontrada', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

    @api_security
    def get(self, request):
        try:
            hoy = datetime.now().date()
            payload = request.auth.payload
            ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(payload['perfilprincipal']['id']))
            inscripcion = ePerfilUsuario.inscripcion
            persona = ePerfilUsuario.persona
            malla = inscripcion.malla_inscripcion().malla
            cordinacionid = inscripcion.carrera.coordinacion_carrera().id
            if not payload['periodo']['id']:
                raise NameError("No tiene periodo configurado.")
            periodo = Periodo.objects.get(pk=int(encrypt(payload['periodo']['id'])))
            matricula = None if not inscripcion.matricula() else inscripcion.matricula()
            nivel = None if matricula == None else matricula.nivel
            tiene_matricula = False
            if 'action' in request.query_params:
                action = request.query_params['action']

                if action == 'loadCursos':
                    try:
                        id = int(encrypt(request.query_params['id']))
                        eAsignatura = Asignatura.objects.get(pk=id)
                        # -----------------------------------------------------------
                        malla_materias_actuales_creadas = 353  # MODULOS DE INGLES (ABRIL 2019) PRESENCIAL 2019.0000 - SNIESE
                        nivel_materias_ofertadas_actual_creadas = Nivel.objects.get(pk=variable_valor('NIVEL_ACTUAL_MATRICULA_INGLES_ID'))
                        id_materias_ofertadas_actual_creadas = nivel_materias_ofertadas_actual_creadas.materia_set.values_list('id', flat=True).filter(status=True, asignaturamalla__malla_id=malla_materias_actuales_creadas)
                        materiasabiertas = Materia.objects.filter(Q(asignatura=eAsignatura, nivel_id=nivel_materias_ofertadas_actual_creadas.pk, nivel__cerrado=False), status=True, id__in=id_materias_ofertadas_actual_creadas).exclude(asignaturamalla__malla__carrera__id__in=(variable_valor('CARRERA_NO_MATRICULAR_INGLES_ID'))).order_by('id')
                        # -----------------------------------------------------------
                        cursos = materias_abiertas(eAsignatura, materiasabiertas)
                        aData = {
                            'cursos': cursos if cursos else [],
                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                               status=status.HTTP_200_OK)
                elif action == 'loadCursosInformatica':
                    try:
                        id = int(encrypt(request.query_params['id']))
                        eAsignatura = Asignatura.objects.get(pk=id)
                        # -----------------------------------------------------------
                        malla_materias_actuales_creadas = 32  # MODULOS DE INFORMATICA
                        nivel_materias_ofertadas_actual_creadas = Nivel.objects.get(pk=variable_valor('NIVEL_ACTUAL_MATRICULA_INFORMATICA_ID'))
                        id_materias_ofertadas_actual_creadas = nivel_materias_ofertadas_actual_creadas.materia_set.values_list('id', flat=True).filter(status=True, asignaturamalla__malla_id=malla_materias_actuales_creadas)
                        materiasabiertas = Materia.objects.filter(Q(asignatura=eAsignatura, nivel_id=nivel_materias_ofertadas_actual_creadas.pk, nivel__cerrado=False), status=True, id__in=id_materias_ofertadas_actual_creadas).filter(carrerascomunes=inscripcion.carrera).order_by('id')
                        # -----------------------------------------------------------
                        cursos = materias_abiertas(eAsignatura, materiasabiertas)
                        aData = {'cursos': cursos if cursos else []}
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)
            else:
                try:
                    asignatura_data_informatica = []
                    puede_ingles = [True, '']
                    puede_informartica = [True, '']
                    ACTIVA_MATRICULA_MODULOS_INFORMATICA = variable_valor('ACTIVA_MATRICULA_MODULOS_INFORMATICA')
                    ACTIVA_MATRICULA_MODULOS_INGLES = variable_valor('ACTIVA_MATRICULA_MODULOS_INGLES')
                    if not ACTIVA_MATRICULA_MODULOS_INFORMATICA and not ACTIVA_MATRICULA_MODULOS_INGLES:
                        raise NameError(f"Estimad{'a' if persona.es_mujer() else 'o'} estudiante, actualmente no tenemos módulos disponibles.")
                    if not malla:
                        raise NameError(f"Estimad{'a' if persona.es_mujer() else 'o'} estudiante, Debe tener malla asociada para poder matricularse.")
                    if cordinacionid in [9, 7]:
                        raise NameError(f"Estimad{'a' if persona.es_mujer() else 'o'} estudiante, este módulo es solo para pregrado")
                    # MATRICULA PARA MÓDULOS DE INGLÉS
                    if inscripcion.carrera.id.__str__() in (variable_valor('CARRERA_NO_MATRICULAR_INGLES_ID')) and puede_ingles[0]:
                        # raise NameError(f" La carrera {inscripcion.carrera} no está habilitada para matriculación de módulos de inglés")
                        puede_ingles = [False, 'f" La carrera {inscripcion.carrera} no está habilitada para matriculación de módulos de inglés"']

                    if not inscripcion.recordacademico_set.filter(status=True, fecha__gte=hoy - timedelta(days=1825)).exclude(noaplica=True).exists() and inscripcion.recordacademico_set.filter(status=True).exists() and puede_ingles[0]:
                        # raise NameError(f"Estimad{'a' if persona.es_mujer() else 'o'} estudiante, debe de acercarse a secretaria para matricularse, por no haber tomado materias hace mas de 5 años.")
                        puede_ingles = [False, f"Estimad{'a' if persona.es_mujer() else 'o'} estudiante, debe de acercarse a secretaria para matricularse, por no haber tomado materias hace mas de 5 años."]
                    if MateriaAsignada.objects.values('id').filter(status=True, estado_id=1, matricula=matricula, cerrado=True, materia__nivel__id__in=variable_valor('NIVELES_VALIDA_APROBADOS')).count() >= 2 and puede_ingles[0]:
                        # raise NameError(f"Estimad{'a' if persona.es_mujer() else 'o'} estudiante, usted ya registra la aprobación de dos módulos de inglés por periodo académico. Debe esperar el siguiente periodo académico para continuar con sus módulos.")
                        puede_ingles = [False, f"Estimad{'a' if persona.es_mujer() else 'o'} estudiante, usted ya registra la aprobación de dos módulos de inglés por periodo académico. Debe esperar el siguiente periodo académico para continuar con sus módulos."]
                    if matricula:
                        tiene_matricula = True

                        if es_bloqueado_por_no_realizar_el_curso_en_buckingham(matricula) and puede_ingles[0]:
                            # raise NameError(f"Estimad{'a' if persona.es_mujer() else 'o'} estudiante, Usted se encuentra bloqueado para la matriculación del presente Módulo, debido a que en la fase 1 NO registra uso de su cupo de matrícula en la plataforma de la academia Buckingham.")
                            puede_ingles = [False, f"Estimad{'a' if persona.es_mujer() else 'o'} estudiante, Usted se encuentra bloqueado para la matriculación del presente Módulo, debido a que en la fase 1 NO registra uso de su cupo de matrícula en la plataforma de la academia Buckingham."]

                        # if matricula.materiaasignada_set.filter(status=True, materia__nivel_id= variable_valor('NIVEL_ACTUAL_MATRICULA_INGLES_ID'), materia__cerrado=False,cerrado=False).exists():
                        #     raise NameError(f"Estimad{'a' if persona.es_mujer() else 'o'} estudiante, usted está cursando el módulo: {matricula.materiaasignada_set.filter(status=True, materia__nivel_id=variable_valor('NIVEL_ACTUAL_MATRICULA_INGLES_ID'), materia__cerrado=False).first().materia.__str__()}.")

                        if tiene_rubros_sin_cancelar(periodo, matricula, persona, True) and puede_ingles[0]:
                            puede_ingles = [False, f"Estimad{'a' if persona.es_mujer() else 'o'} estudiante, tiene deudas vencidas por módulos de inglés, consulte en el módulo mis finanzas."]

                        nivel_matricula = matricula.nivelmalla.orden
                        nivel_minimo = int(variable_valor('NIVEL_MINIMO_MATRICULAR_INGLES')) if variable_valor('NIVEL_MINIMO_MATRICULAR_INGLES') else None
                        if nivel_minimo and not nivel_matricula >= nivel_minimo and puede_ingles[0]:
                            # raise NameError(f"Estimad{'a' if persona.es_mujer() else 'o'} estudiante, solo se encuentra habilitado la matriculación para estudiantes cursando desde el {nivel_minimo}° hasta el 10° semestre.")
                            puede_ingles = [False, f"Estimad{'a' if persona.es_mujer() else 'o'} estudiante, solo se encuentra habilitado la matriculación para estudiantes cursando desde el {nivel_minimo}° hasta el 10° semestre."]

                        eAsignatura = Asignatura.objects.filter(Q(id__in=[x.asignatura.id for x in malla.modulomalla_set.filter(status=True).exclude(orden=0)]), modulo=True).distinct()

                        modulo_minimo_aprobado = int(variable_valor('ID_MODULO_MINIMO_APROBADO')) if variable_valor('ID_MODULO_MINIMO_APROBADO') else None
                        if modulo_minimo_aprobado and puede_ingles[0]:
                            if eModulo := eAsignatura.filter(pk=modulo_minimo_aprobado).first():
                                estado = inscripcion.estado_asignatura(eModulo)
                                if not estado == 1:
                                    # raise NameError(f"Estimad{'a' if persona.es_mujer() else 'o'} estudiante, solo se encuentra habilitado la matriculación para aquellos que hayan aprobado el módulo {eModulo.nombre}.")
                                    puede_ingles = [False, f"Estimad{'a' if persona.es_mujer() else 'o'} estudiante, solo se encuentra habilitado la matriculación para aquellos que hayan aprobado el módulo {eModulo.nombre}."]

                        if materias_matriculadas := matricula.materiaasignada_set.filter(status=True, materia__nivel_id=variable_valor('NIVEL_ACTUAL_MATRICULA_INGLES_ID'), materia__cerrado=False, cerrado=False).values('materia__asignatura_id').distinct():
                            eAsignatura = eAsignatura.filter(id__in=materias_matriculadas)
                        asignatura_data = []
                        for asignatura in eAsignatura:
                            puede_tomar_materia = inscripcion.puede_tomar_materia_modulo(asignatura)
                            estado_asignatura = inscripcion.estado_asignatura(asignatura)
                            if variable_valor('VALIDA_NIVELES_ANTERIORES_MATRICULA_INGLES_ID'):
                                matricula_anterior = matricula.materiaasignada_set.filter(status=True, materia__nivel_id__in=variable_valor('NIVELES_ANTERIORES_MATRICULA_INGLES_ID'), materia__asignatura=asignatura, materia__cerrado=False, cerrado=False).exists()
                                if matricula_anterior:
                                    puede_tomar_materia = False
                            eAsignaturaSerializer = AsignaturaSerializer(asignatura)
                            lista_asignatura = {
                                'asignatura': eAsignaturaSerializer.data,
                                'puede_tomar_materia': puede_tomar_materia,
                                'estado_asignatura': estado_asignatura,
                                'esta_matriculado': matricula.materiaasignada_set.filter(status=True, materia__nivel_id=variable_valor('NIVEL_ACTUAL_MATRICULA_INGLES_ID'), materia__asignatura=asignatura, materia__cerrado=False, cerrado=False).exists(),
                            }

                            asignatura_data.append(lista_asignatura)

                        # MATRICULA PARA MÓDULOS DE INFORMÁTICA
                        eAsignaturaInformatica = Asignatura.objects.filter(Q(id__in=[1053, 1054]), modulo=True).distinct().order_by('id')
                        for asignatura in eAsignaturaInformatica:
                            puede_tomar_materia = inscripcion.puede_tomar_materia_modulo_informatica(asignatura)
                            estado_asignatura = inscripcion.estado_asignatura(asignatura)
                            if variable_valor('VALIDA_NIVELES_ANTERIORES_MATRICULA_INFORMATICA_ID'):
                                matricula_anterior = matricula.materiaasignada_set.filter(status=True, materia__nivel_id__in=variable_valor('NIVELES_ANTERIORES_MATRICULA_INFORMATICA_ID'), materia__asignatura=asignatura, materia__cerrado=False, cerrado=False).exists()
                                if matricula_anterior:
                                    puede_tomar_materia = False
                            eAsignaturaSerializer = AsignaturaSerializer(asignatura)
                            lista_asignatura = {
                                'asignatura': eAsignaturaSerializer.data,
                                'puede_tomar_materia': puede_tomar_materia,
                                'estado_asignatura': estado_asignatura,
                                'esta_matriculado': matricula.materiaasignada_set.filter(status=True, materia__nivel_id=variable_valor('NIVEL_ACTUAL_MATRICULA_INFORMATICA_ID'), materia__asignatura=asignatura, materia__cerrado=False, cerrado=False).exists(),
                            }

                            asignatura_data_informatica.append(lista_asignatura)

                    else:
                        nivelid = nivel_matriculacion(inscripcion)
                        if nivelid < 0:
                            if nivelid == -1:
                                raise NameError(f"Estimad{'a' if persona.es_mujer() else 'o'} estudiante, el periodo de matriculación no se encuentra activo.")
                            if nivelid == -2:
                                raise NameError(f"Estimad{'a' if persona.es_mujer() else 'o'} estudiante, no existen niveles con cupo para matricularse.")
                            if nivelid == -3:
                                raise NameError(f"Estimad{'a' if persona.es_mujer() else 'o'} estudiante, no existen paralelos disponibles.")
                            if nivelid == -4:
                                raise NameError(f"Estimad{'a' if persona.es_mujer() else 'o'} estudiante, no existen paralelos para su nivel.")
                        else:
                            nivel = Nivel.objects.get(pk=nivelid)

                        eInscripcionmalla = inscripcion.malla_inscripcion()
                        if not eInscripcionmalla:
                            raise NameError(f"Estimad{'a' if persona.es_mujer() else 'o'} estudiante, Debe tener malla asociada para poder matricularse.")

                        if tiene_rubros_sin_cancelar(None, None, persona, False):
                            raise NameError(f"Estimad{'a' if persona.es_mujer() else 'o'} estudiante, Tiene deudas vencidas por módulos de inglés, consulte en el módulo mis finanzas.")

                        nivel_malla = inscripcion.mi_nivel().nivel.orden
                        nivel_minimo = int(variable_valor('NIVEL_MINIMO_MATRICULAR_INGLES')) if variable_valor('NIVEL_MINIMO_MATRICULAR_INGLES') else None
                        if nivel_minimo and not nivel_malla >= nivel_minimo:
                            raise NameError(f"Estimad{'a' if persona.es_mujer() else 'o'} estudiante, solo se encuentra habilitado la matriculación para estudiantes cursando desde el {nivel_minimo}° hasta el 10° semestre.")

                        listamodulos = eInscripcionmalla.malla.modulomalla_set.values_list('asignatura_id').filter(status=True).exclude(orden=0)
                        eAsignatura = Asignatura.objects.filter(pk__in=listamodulos).distinct()

                        modulo_minimo_aprobado = int(variable_valor('ID_MODULO_MINIMO_APROBADO')) if variable_valor('ID_MODULO_MINIMO_APROBADO') else None
                        if modulo_minimo_aprobado:
                            if eModulo := eAsignatura.filter(pk=modulo_minimo_aprobado).first():
                                estado = inscripcion.estado_asignatura(eModulo)
                                if not estado == 1:
                                    raise NameError(f"Estimad{'a' if persona.es_mujer() else 'o'} estudiante, solo se encuentra habilitado la matriculación para aquellos que hayan aprobado el módulo {eModulo.nombre}.")
                        # if materias_matriculadas := matricula.materiaasignada_set.filter(status=True, materia__nivel_id=variable_valor('NIVEL_ACTUAL_MATRICULA_INGLES_ID'), materia__cerrado=False, cerrado=False).values('materia__asignatura_id').distinct():
                        #     eAsignatura = eAsignatura.filter(id__in=materias_matriculadas)

                        asignatura_data = []
                        for asignatura in eAsignatura:
                            puede_tomar_materia = inscripcion.puede_tomar_materia_modulo(asignatura)
                            estado_asignatura = inscripcion.estado_asignatura(asignatura)
                            eAsignaturaSerializer = AsignaturaSerializer(asignatura)
                            lista_asignatura = {
                                'asignatura': eAsignaturaSerializer.data,
                                'puede_tomar_materia': puede_tomar_materia,
                                'estado_asignatura': estado_asignatura,
                                'esta_matriculado': False
                            }

                            asignatura_data.append(lista_asignatura)

                        malla = eInscripcionmalla.malla

                        eAsignaturaInformatica = Asignatura.objects.filter(Q(id__in=[1053, 1054]), modulo=True).distinct().order_by('id')
                        for asignatura in eAsignaturaInformatica:
                            puede_tomar_materia = inscripcion.puede_tomar_materia_modulo_informatica(asignatura)
                            estado_asignatura = inscripcion.estado_asignatura(asignatura)
                            if variable_valor('VALIDA_NIVELES_ANTERIORES_MATRICULA_INFORMATICA_ID'):
                                matricula_anterior = matricula.materiaasignada_set.filter(status=True, materia__nivel_id__in=variable_valor('NIVELES_ANTERIORES_MATRICULA_INFORMATICA_ID'), materia__asignatura=asignatura, materia__cerrado=False, cerrado=False).exists()
                                if matricula_anterior:
                                    puede_tomar_materia = False
                            eAsignaturaSerializer = AsignaturaSerializer(asignatura)
                            lista_asignatura = {
                                'asignatura': eAsignaturaSerializer.data,
                                'puede_tomar_materia': puede_tomar_materia,
                                'estado_asignatura': estado_asignatura,
                                'esta_matriculado': False,
                            }

                            asignatura_data_informatica.append(lista_asignatura)

                    fichasocioeconomicainec = persona.fichasocioeconomicainec()
                    eInscripcionSerializer = InscripcionSerializer(inscripcion)
                    eMallaSerializer = MallaSerializer(malla)
                    eNivelSerializer = NivelSerializer(nivel)
                    data = {
                        'eAsignatura': asignatura_data if eAsignatura else [],
                        'inscripcion': eInscripcionSerializer.data if inscripcion else [],
                        'malla': eMallaSerializer.data if malla else [],
                        'nivel': eNivelSerializer.data if nivel else [],
                        'tiene_matricula': tiene_matricula,
                        'fichasocioeconomicainec': fichasocioeconomicainec if fichasocioeconomicainec else [],
                        'eAsignaturainformatica': asignatura_data_informatica if asignatura_data_informatica else [],
                        'puede_ingles': puede_ingles,
                        'puede_informatica': puede_informartica,
                        'ACTIVA_MATRICULA_MODULOS_INFORMATICA': ACTIVA_MATRICULA_MODULOS_INFORMATICA,
                        'ACTIVA_MATRICULA_MODULOS_INGLES': ACTIVA_MATRICULA_MODULOS_INGLES
                    }

                    return Helper_Response(isSuccess=True, data=data, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'{ex.__str__()}', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                   status=status.HTTP_200_OK)
