# -*- coding: UTF-8 -*-
from _decimal import Decimal

from babel.dates import format_date
from django import template
from django.core.files.storage import default_storage
from django.db.models import Q,  F, Value, Count, Case, When, ExpressionWrapper, FloatField
from django.db.models.functions import Concat, Coalesce
import settings
import json

from directivo.models import ConsultaFirmaPersonaSancion
from inno.models import MateriaGrupoTitulacion, TipoActaFirma
from sga.funciones import fechaletra_corta, fields_model, field_default_value_model, trimestre, null_to_decimal, \
    convertir_fecha, convertir_fecha_invertida, variable_valor, daterange
from sga.models import MESES_CHOICES, Persona, Sesion, Carrera, PracticasTutoria, PracticasPreprofesionalesInscripcion, \
    AgendaPracticasTutoria, ActividadConvenio, Modulo, DIAS_CHOICES, Clase, AsignaturaMallaPredecesora, MateriaAsignada, \
    MateriaTitulacion, SagResultadoEncuesta, SagMuestraEncuesta, DetalleDistributivo, ProfesorMateria, CompendioSilaboSemanal, \
    ClaseActividad, TipoProfesor, Silabo, VideoMagistralSilaboSemanal, GuiaEstudianteSilaboSemanal, \
    TareaSilaboSemanal, ForoSilaboSemanal, TareaPracticaSilaboSemanal, TestSilaboSemanal, TestSilaboSemanalAdmision, EvaluacionAprendizajeSilaboSemanal
from investigacion.models import ProyectoInvestigacionIntegrante, GrupoInvestigacionIntegrante
from datetime import datetime, timedelta, date

register = template.Library()
MODELO_EVALUATIVO_TRANSVERSAL = [27, 64]

def existe_validacion(pk, dia):
    from sagest.models import RecaudacionBanco
    incorrecto = False
    qs = RecaudacionBanco.objects.filter(cuentabanco_id=int(pk), fecha=convertir_fecha(dia))
    if qs.exists():
        incorrecto = qs[0].incorrecto
    return incorrecto


@register.simple_tag
def ver_valor_dict(diccionario, llave):
    return diccionario[llave]


@register.simple_tag
def ver_total_tutorias(mes, dia, anio, profesor):
    fecha = convertir_fecha(str(dia) + '-' + str(mes) + '-' + str(anio))
    return PracticasTutoria.objects.select_related('practica').filter(fechainicio=fecha, fechafin=fecha,
                                                                      practica__tutorunemi=profesor,
                                                                      status=True).count()


@register.simple_tag
def ver_total_tutorias_agendadas(mes, dia, anio, profesor):
    fecha = convertir_fecha(str(dia) + '-' + str(mes) + '-' + str(anio))
    return AgendaPracticasTutoria.objects.select_related('docente').filter(fecha=fecha, docente=profesor,
                                                                           status=True).count()


@register.simple_tag
def ver_total_actividad_convenio(mes, dia, anio, convenio):
    fecha = convertir_fecha(str(dia) + '-' + str(mes) + '-' + str(anio))
    return ActividadConvenio.objects.select_related('actividad').filter(fecha=fecha, status=True,
                                                                        convenioempresa=convenio).count()
@register.simple_tag
def fecha_vencida(obj, tipo):
    try:
        from posgrado.models import DetalleFechasEvalDirMateria
        estado = False
        if tipo == 1:
            if obj.fineval:
                if datetime.now().date() > obj.fineval:
                    estado = True
        elif tipo == 2:
            if obj.finevalauto:
                if datetime.now().date() > obj.finevalauto:
                    estado = True
        elif tipo == 3:
            eDetalle = DetalleFechasEvalDirMateria.objects.filter(status=True, materia=obj).first()
            if eDetalle and eDetalle.fin:
                if datetime.now().date() > eDetalle.fin:
                    estado = True
        return estado
    except Exception as ex:
        pass

@register.simple_tag
def fecha_vencida_new(obj):
    try:
        estado = False
        if obj.fin:
            if datetime.now().date() > obj.fin:
                estado = True
        return estado
    except Exception as ex:
        pass

@register.simple_tag
def fecha_hetero_posgrado(obj):
    try:
        estado = False
        hoy = datetime.now().date()
        if obj.materia.inicioeval and obj.materia.fineval:
            if obj.materia.inicioeval <= hoy <= obj.materia.fineval:
                estado = True
        return estado
    except Exception as ex:
        pass

@register.simple_tag
def fecha_satis(obj):
    try:
        estado = False
        hoy = datetime.now().date()
        if obj.inicio and obj.fin:
            if obj.inicio <= hoy <= obj.fin:
                estado = True
        return estado
    except Exception as ex:
        pass

@register.simple_tag
def fecha_dir_posgrado(obj):
    try:
        hoy=datetime.now().date()
        estado = False
        if obj.inicio <= hoy <= obj.fin:
            estado = True
        return estado
    except Exception as ex:
        pass

@register.simple_tag
def obj_eval_hetero(obj, mate, evaluador):
    from posgrado.models import RespuestaEvaluacionAcreditacionPosgrado
    objeto = None
    if RespuestaEvaluacionAcreditacionPosgrado.objects.filter(proceso=obj.materia.nivel.periodo.proceso_evaluativo(),
                                                              tipoinstrumento=1, profesor=obj.profesor,
                                                              evaluador=evaluador, materia=obj.materia,
                                                              materiaasignada=mate).exists():
        objeto = RespuestaEvaluacionAcreditacionPosgrado.objects.filter(proceso=obj.materia.nivel.periodo.proceso_evaluativo(),
                                                              tipoinstrumento=1, profesor=obj.profesor,
                                                              evaluador=evaluador, materia=obj.materia,
                                                              materiaasignada=mate).first()

    return objeto

@register.simple_tag
def estado_mate(obj):
    return datetime.now().date() > obj.fin

@register.simple_tag
def resumen_posgrado(eModulo):
    resumen = None
    eProfesor = eModulo.profesor
    distributivo = eProfesor.distributivohoraseval(eModulo.materia.nivel.periodo)
    if distributivo and distributivo.resumen_evaluacion_acreditacion():
        resumen = distributivo.resumen_evaluacion_acreditacion()
    return resumen

@register.simple_tag
def esta_evaluado_hetero(obj, persona, materia, periodo):
    if obj.respuestaevaluacionacreditacionposgrado_set.values('id').filter(proceso__periodo=periodo, tipoinstrumento=1,
                                                                        materia=materia, evaluador=persona).exists():
        estado = True
    elif obj.respuestaevaluacionacreditacion_set.values('id').filter(proceso__periodo=periodo, tipoinstrumento=1,
                                                                        materia=materia, evaluador=persona).exists():
        estado = True
    else:
        estado = False
    return estado

@register.simple_tag
def fecha_procesado_resultados(obj):
    from posgrado.models import DetalleResultadosEvaluacionPosgrado
    resultado = None

    if DetalleResultadosEvaluacionPosgrado.objects.filter(status=True, materia=obj.materia).exists():
        resultado = DetalleResultadosEvaluacionPosgrado.objects.filter(status=True, materia=obj.materia).order_by('-id').first()
    return resultado

@register.simple_tag
def prof_autor_2(obj):
    from sga.models import ProfesorMateria
    resultado = None
    if ProfesorMateria.objects.filter(status=True, materia=obj, tipoprofesor__id=11).exists():
        resultado = ProfesorMateria.objects.filter(status=True, materia=obj, tipoprofesor__id=11).order_by('-id').first()
    return resultado

@register.simple_tag
def obj_satis_est(obj, objen):
    from posgrado.models import InscripcionEncuestaSatisfaccionDocente
    if InscripcionEncuestaSatisfaccionDocente.objects.filter(status=True, materiaasignada__materia=obj, encuesta=objen).exists():
        return InscripcionEncuestaSatisfaccionDocente.objects.filter(status=True, materiaasignada__materia=obj, encuesta=objen).order_by('id').first()
    else:
        return None

@register.simple_tag
def encuestas_configuradas(obj):
    from posgrado.models import InscripcionEncuestaSatisfaccionDocente, EncuestaSatisfaccionDocente
    if InscripcionEncuestaSatisfaccionDocente.objects.filter(status=True, materiaasignada__materia=obj, encuesta__tipo=2).exists():
        ide = InscripcionEncuestaSatisfaccionDocente.objects.filter(status=True, materiaasignada__materia=obj, encuesta__tipo=2).values_list('encuesta__id', flat=True).distinct()
        return EncuestaSatisfaccionDocente.objects.filter(status=True, id__in=ide)
    else:
        return None

@register.simple_tag
def cantidad_satis(obj, num):
    from posgrado.models import InscripcionEncuestaSatisfaccionDocente, EncuestaSatisfaccionDocente
    try:
        if num == 0:
           return InscripcionEncuestaSatisfaccionDocente.objects.filter(status=True, materiaasignada__materia=obj.materiaasignada.materia,
                                                                        encuesta=obj.encuesta, respondio=False).count()
        else:
            return InscripcionEncuestaSatisfaccionDocente.objects.filter(status=True,
                                                                         materiaasignada__materia=obj.materiaasignada.materia,
                                                                         encuesta=obj.encuesta, respondio=True).count()
    except Exception as ex:
        pass

@register.simple_tag
def cantidad_matriculados(obj):
    from sga.models import MateriaAsignada
    cantidad = 0
    if MateriaAsignada.objects.filter(status=True, matricula__status=True, materia=obj,
                                      matricula__inscripcion__status=True, retiramateria=False).exists():
        cantidad = MateriaAsignada.objects.filter(status=True, matricula__status=True, materia=obj,
                                                  matricula__inscripcion__status=True, retiramateria=False).values_list('matricula__id').order_by('matricula__id').distinct().count()
    return cantidad

@register.simple_tag
def cortar_string(texto, longitud):
    if len(texto) > longitud:
        return f'{texto[:longitud]}...'
    return texto

@register.simple_tag
def cantidad_evaluacion_docente(obj):
    from posgrado.models import RespuestaEvaluacionAcreditacionPosgrado
    try:
        estado = True
        re = RespuestaEvaluacionAcreditacionPosgrado.objects.values('evaluador_id').filter(
            status=True,
            tipoinstrumento=1,
            proceso__periodo=obj.materia.nivel.periodo,
            materia=obj.materia,
            profesor=obj.profesor,
            respuestarubricaposgrado__rubrica__para_hetero=True).exclude(respuestarubricaposgrado__rubrica__rvigente=True)
        if re.exists():
            estado = False

        resultados = RespuestaEvaluacionAcreditacionPosgrado.objects.values('evaluador_id').filter(status=True,tipoinstrumento=1,profesor=obj.profesor,materia=obj.materia, respuestarubricaposgrado__rubrica__para_hetero=True, respuestarubricaposgrado__rubrica__rvigente=estado)
        if resultados.exists():
            return resultados.distinct().count()
        return 0
    except Exception as ex:
        pass

@register.simple_tag
def cantidad_evaluacion_auto(obj):
    from posgrado.models import RespuestaEvaluacionAcreditacionPosgrado
    try:
        resultados = RespuestaEvaluacionAcreditacionPosgrado.objects.values('profesor_id').filter(status=True,tipoinstrumento=2,profesor=obj.profesor,materia=obj.materia, respuestarubricaposgrado__rubrica__para_auto=True)
        if resultados.exists():
            return resultados.distinct().count()
        return 0
    except Exception as ex:
        pass

@register.simple_tag
def object_dir(obj):
    try:
        from posgrado.models import DetalleFechasEvalDirMateria
        eDetalle = None
        if DetalleFechasEvalDirMateria.objects.filter(status=True, materia=obj.materia).exists():
            eDetalle = DetalleFechasEvalDirMateria.objects.filter(status=True, materia=obj.materia).first()
        return eDetalle
    except Exception as ex:
        pass

@register.simple_tag
def evaluo_coordinador(obj):
    from posgrado.models import RespuestaEvaluacionAcreditacionPosgrado
    from posgrado.models import CohorteMaestria
    try:
        estado = False
        resultados=RespuestaEvaluacionAcreditacionPosgrado.objects.filter(status=True,tipoinstrumento=4,profesor=obj.profesor,materia=obj.materia, respuestarubricaposgrado__rubrica__para_directivo=True)
        if resultados.exists():
            for resultado in resultados:
                if CohorteMaestria.objects.filter(status=True, coordinador=resultado.evaluador,
                                                  maestriaadmision__carrera=resultado.materia.asignaturamalla.malla.carrera).exists():
                    estado = True
        return estado
    except Exception as ex:
        pass

@register.simple_tag
def evaluo_director(obj):
    from posgrado.models import RespuestaEvaluacionAcreditacionPosgrado
    from sagest.models import Departamento
    try:
        estado = False
        resultados=RespuestaEvaluacionAcreditacionPosgrado.objects.filter(status=True,tipoinstrumento=4,profesor=obj.profesor,materia=obj.materia, respuestarubricaposgrado__rubrica__para_directivo=True)
        if resultados.exists():
            for resultado in resultados:
                if Departamento.objects.filter(pk=216, responsable=resultado.evaluador).exists():
                    estado = True
                elif Departamento.objects.filter(pk=215, responsable=resultado.evaluador).exists():
                    estado = True
                elif Departamento.objects.filter(pk=163, responsable=resultado.evaluador).exists():
                    estado = True
        return estado
    except Exception as ex:
        pass

@register.simple_tag
def evaluo_director_2(obj):
    from posgrado.models import RespuestaEvaluacionAcreditacionPosgrado
    from sagest.models import Departamento
    try:
        estado = False
        resultados=RespuestaEvaluacionAcreditacionPosgrado.objects.filter(status=True,tipoinstrumento=4,profesor=obj.evaluado, materia=obj.materia, evaluador=obj.evaluador, respuestarubricaposgrado__rubrica__para_directivo=True)
        if resultados.exists():
            estado = True
            obj.evalua = True
            obj.save()
        return estado
    except Exception as ex:
        pass

@register.simple_tag
def evaluo_coordinador_2(self):
    from posgrado.models import RespuestaEvaluacionAcreditacionPosgrado
    from posgrado.models import CohorteMaestria
    try:
        estado = False
        resultados=RespuestaEvaluacionAcreditacionPosgrado.objects.filter(status=True,tipoinstrumento=4,profesor=self.evaluado,materia=self.materia, evaluador=self.evaluador, respuestarubricaposgrado__rubrica__para_directivo=True)
        if resultados.exists():
            estado = True
            self.evalua = True
            self.save()
        return estado
    except Exception as ex:
        pass

@register.simple_tag
def obj_instructor(eDetalle):
    from ejecuform.models import InstructorFormacionEjecutiva
    try:
        obj = None
        if InstructorFormacionEjecutiva.objects.filter(status=True, asignaturaform=eDetalle, activo=True).exists():
            obj = InstructorFormacionEjecutiva.objects.filter(status=True, asignaturaform=eDetalle, activo=True).first()
        return obj
    except Exception as ex:
        pass

@register.simple_tag
def calculo_carreras_posgrado(eCarrera, desde, hasta):
    try:
        filtro = Q(status=True, materia__nivel__periodo__tipo__id=3, tipoprofesor__id=11,
                   materia__asignaturamalla__malla__carrera=eCarrera,
                   materia__fin__lt=datetime.now().date())

        if desde and hasta:
            filtro = filtro & Q(materia__fin__range=(desde, hasta))

        elif desde:
            filtro = filtro & Q(materia__fin__gte=desde)

        elif hasta:
            filtro = filtro & Q(materia__fin__lte=hasta)

        if desde == '' and hasta == '':
            cvnt_beta_sal = cvnt_omega_sal = cvnt_alfa_sal = total_sal = suma_sal = 0
        else:
            eModulos = ProfesorMateria.objects.filter(filtro).order_by('-id')
            cvnt_beta_sal = cvnt_omega_sal = cvnt_alfa_sal = total_sal = suma_sal = 0
            for eModulo in eModulos:
                eProfesor = eModulo.profesor
                distributivo = eProfesor.distributivohoraseval(eModulo.materia.nivel.periodo)
                if distributivo and distributivo.resumen_evaluacion_acreditacion():
                    resumen = distributivo.resumen_evaluacion_acreditacion()
                    if resumen.resultado_docencia and resumen.resultado_docencia > 0:
                        if cincoacien(resumen.resultado_docencia) > 0 and cincoacien(resumen.resultado_docencia) <= 70:
                            cvnt_beta_sal += 1
                            suma_sal += cincoacien(resumen.resultado_docencia)
                        elif cincoacien(resumen.resultado_docencia) > 70 and cincoacien(resumen.resultado_docencia) <= 90:
                            cvnt_omega_sal += 1
                            suma_sal += cincoacien(resumen.resultado_docencia)
                        elif cincoacien(resumen.resultado_docencia) > 90:
                            cvnt_alfa_sal += 1
                            suma_sal += cincoacien(resumen.resultado_docencia)

        dicc4 = {'etiqueta': '0-70', 'cantidad': cvnt_beta_sal, 'orden': 1}
        dicc5 = {'etiqueta': '70-90', 'cantidad': cvnt_omega_sal, 'orden': 2}
        dicc6 = {'etiqueta': '90-100', 'cantidad': cvnt_alfa_sal, 'orden': 3}
        listado_salud = []
        listado_salud.append(dicc4)
        listado_salud.append(dicc5)
        listado_salud.append(dicc6)

        newlist_sal = sorted(listado_salud, key=lambda d: d['orden'], reverse=True)
        eti_sal = [d['etiqueta'] for d in newlist_sal]
        canti_sal = [d['cantidad'] for d in newlist_sal]
        total_sal = cvnt_beta_sal + cvnt_omega_sal + cvnt_alfa_sal
        if suma_sal > 0 and total_sal > 0:
            promedio_sal = suma_sal / total_sal
        else:
            promedio_sal = 0
        return [canti_sal, eti_sal, total_sal, promedio_sal]
    except Exception as ex:
        pass



def callmethod(obj, methodname):
    method = getattr(obj, methodname)
    if "__callArg" in obj.__dict__:
        ret = method(*obj.__callArg)
        del obj.__callArg
        return ret
    return method()


def args(obj, arg):
    if "__callArg" not in obj.__dict__:
        obj.__callArg = []
    obj.__callArg.append(arg)
    return obj


def suma(var, value=1):
    try:
        return var + value
    except Exception as ex:
        pass


def resta(var, value=1):
    return var - value


def restanumeros(var, value):
    return var - value

def cincoacien(valor):
    return round((valor * 100 / 5), 2)

def multiplicanumeros(var, value):
    return Decimal(Decimal(var).quantize(Decimal('.01')) * Decimal(value).quantize(Decimal('.01'))).quantize(
        Decimal('.01'))


def divide(value, arg):
    return int(value) / int(arg) if arg else 0


def porciento(value, arg):
    return round(value * 100 / float(arg), 2) if arg else 0


def calendarbox(var, dia):
    return var[dia]


def barraporciento(var, total):
    if int(total) == 0:
        return 0
    else:
        if settings.TIPO_RESPUESTA_EVALUACION == 3:
            return int((int(var) / 3) * total)
        elif settings.TIPO_RESPUESTA_EVALUACION == 1:
            return int((int(var) / 5) * total)
        elif settings.TIPO_RESPUESTA_EVALUACION == 2:
            return int((int(var) / 10) * total)


def calendarboxdetails(var, dia):
    lista = var[dia]
    result = []
    for x in lista:
        b = [x.split(',')[0], x.split(',')[1]]
        result.append(b)
    return result


@register.simple_tag
def traducir_mes(value):
    return ' '.join(str(value).lower().replace('january', 'Enero') \
                    .replace('february', 'Febrero') \
                    .replace('march', 'Marzo') \
                    .replace('april', 'Abril') \
                    .replace('may', 'Mayo') \
                    .replace('june', 'Junio') \
                    .replace('july', 'Julio') \
                    .replace('august', 'Agosto') \
                    .replace('september', 'Septiembre') \
                    .replace('october', 'Octubre') \
                    .replace('november', 'Noviembre') \
                    .replace('december', 'Diciembre').split(' ')[0:2])


@register.simple_tag
def traducir_dia(value):
    return ' '.join(str(value).lower().replace('monday', 'Lunes') \
                    .replace('tuesday', 'Martes') \
                    .replace('wednesday', 'Miercoles') \
                    .replace('thursday', 'Jueves') \
                    .replace('friday', 'Viernes') \
                    .replace('saturday', 'Sabado').split(' ')[0:2])

@register.simple_tag
def set_encuesta_muestra(self):
    return SagResultadoEncuesta.objects.filter(status=True,inscripcion=self,sagperiodo__primeravez=False,sagperiodo__tienemuestra=True).count()

@register.simple_tag
def set_encuesta_primeravez(self):
    return SagMuestraEncuesta.objects.filter(status=True,inscripcion=self,sagperiodo__primeravez=True,sagperiodo__tienemuestra=False).count()

@register.simple_tag
def gedc_texto_universidad(value):
    return str(value).replace('UNIVERSIDAD', 'UNI.').replace('INSTITUTO', 'INST.')


def calmodeloevaluaciondocente2015(periodo, docente):
    try:
        from django.db.models import Avg
        from sga.models import ResumenParcialEvaluacionIntegral, null_to_numeric
        notaporcentaje = ResumenParcialEvaluacionIntegral.objects.filter(profesor=docente, proceso=periodo).order_by(
            'materia__asignaturamalla__malla__carrera__id', 'materia__asignaturamalla__nivelmalla__id')
        return round(null_to_numeric(notaporcentaje.aggregate(prom=Avg('totalmateriadocencia'))['prom']), 2)
    except Exception as ex:
        return 0


def calmodeloevaluaciondocente(periodoid, docente):
    try:
        from sga.models import ResumenFinalEvaluacionAcreditacion
        porcentaje = ResumenFinalEvaluacionAcreditacion.objects.get(distributivo__profesor=docente,
                                                                    distributivo__periodo=periodoid)
        return round(((porcentaje.resultado_total * 100) / 5), 2)
    except Exception as ex:
        return 0


def calevaluaciondocente(periodoid, docente):
    try:
        from django.db.models import Avg
        from sga.models import MigracionEvaluacionDocente, null_to_numeric
        migra = MigracionEvaluacionDocente.objects.filter(idprofesor=docente, idperiodo=periodoid).order_by('tipoeval',
                                                                                                            'idperiodo',
                                                                                                            'carrera',
                                                                                                            'semestre',
                                                                                                            'materia')
        return round(null_to_numeric(migra.filter(modulo=0).aggregate(prom=Avg('promedioasignatura'))['prom']), 2)
    except Exception as ex:
        return 0


def gedc_calculos(row, filtro):
    from sga.models import GEDCRespuestas, GEDC_GRUPO, GENEROS_ENCUESTAS
    import statistics as stats
    grupoid = row['cab__cab__grupo'] if 'cab__cab__grupo' in row else None
    paisid = row['cab__pais__id'] if 'cab__pais__id' in row else None
    universidad_nombre = row['cab__universidad__nombre'] if 'cab__universidad__nombre' in row else ''
    generoid = row['cab__genero'] if 'cab__genero' in row else None
    preguntaid = row['indicador__id'] if 'indicador__id' in row else None
    frespuesta = Q(status=True) & Q(respcalificacion_inversa__isnull=False)
    if grupoid:
        frespuesta = frespuesta & Q(cab__cab__grupo=grupoid)
    if paisid:
        frespuesta = frespuesta & Q(cab__pais__id=paisid)
    if universidad_nombre:
        frespuesta = frespuesta & Q(cab__universidad__nombre=universidad_nombre)
    if generoid:
        frespuesta = frespuesta & Q(cab__genero=generoid)
    if preguntaid:
        frespuesta = frespuesta & Q(indicador__id=preguntaid)
    listaRespuestas = GEDCRespuestas.objects.filter(cab__cab__publicar=True, cab__pais__isnull=False,
                                                    cab__universidad__isnull=False).filter(
        frespuesta & filtro).values_list('respcalificacion_inversa', flat=True)
    totpreguntas = listaRespuestas.count()
    media = round(stats.mean(list(listaRespuestas)), 2)
    desvestandar = round(stats.pstdev(list(listaRespuestas)), 2)
    return [totpreguntas, media, desvestandar]


def gedc_calculos_grafica(row, filtro):
    try:
        from sga.models import GEDCRespuestas, GEDC_GRUPO, GENEROS_ENCUESTAS
        import statistics as stats
        grupoid = filtro['cab__grupo'] if 'cab__grupo' in filtro else None
        paisid = filtro['pais__id'] if 'pais__id' in filtro else None
        universidad_nombre = filtro['universidad__nombre'] if 'universidad__nombre' in filtro else ''
        generoid = filtro['genero'] if 'genero' in filtro else None
        frespuesta = Q(status=True) & Q(respcalificacion_inversa__isnull=False)
        if grupoid:
            frespuesta = frespuesta & Q(cab__cab__grupo=grupoid)
        if paisid:
            frespuesta = frespuesta & Q(cab__pais__id=paisid)
        if universidad_nombre:
            frespuesta = frespuesta & Q(cab__universidad__nombre=universidad_nombre)
        if generoid:
            frespuesta = frespuesta & Q(cab__genero=generoid)
        listaRespuestas = GEDCRespuestas.objects.filter(cab__cab__publicar=True, cab__pais__isnull=False,
                                                        cab__universidad__isnull=False,
                                                        indicador__factores_id=row.pk).filter(frespuesta).values_list(
            'respcalificacion_inversa', flat=True)
        totpreguntas = listaRespuestas.count()
        if totpreguntas > 0:
            media = round(stats.mean(list(listaRespuestas)), 2)
            desvestandar = round(stats.pstdev(list(listaRespuestas)), 2)
            return [totpreguntas, media, desvestandar]
        else:
            return [0, 0, 0]
    except Exception as ex:
        return [0, 0, 0]


def calendarboxdetailsmostrar(var, dia):
    return var[dia]


def calendarboxdetails2(var, dia):
    lista = var[dia]
    result = []
    b = []
    for x in lista:
        b.append(x[0])
        b.append(x[1])
        b.append(x[2])
        b.append(x[3])
        result.append(b)
    return result


def calendarboxdetailspracticas(var, dia):
    lista = var[dia]
    result = []
    b = []
    for x in lista:
        b.append(x[0])
        b.append(x[1])
        b.append(x[2])
        b.append(x[3])
        b.append(x[4])
        b.append(x[5])
        b.append(x[6])
        result.append(b)
    return result


def predecesoratitulacion(idasignaturamalla):
    listaprodecesoratitulacion = AsignaturaMallaPredecesora.objects.filter(asignaturamalla_id=idasignaturamalla,
                                                                           predecesora__validarequisitograduacion=True,
                                                                           status=True)
    return listaprodecesoratitulacion


def pertenecepredecesoratitulacion(idasignaturamalla):
    listaprodecesoratitulacion = AsignaturaMallaPredecesora.objects.filter(predecesora_id=idasignaturamalla,
                                                                           status=True)
    return listaprodecesoratitulacion


def actasgradopendiente(idpersona):
    faltantes = TipoActaFirma.objects.values('id').filter(persona_id=idpersona, tipoacta__tipo=5, turnofirmar=True,
                                                          firmado=False, status=True).count()
    return faltantes


def actasconsolidadaspendientes(idpersona):
    faltantes = TipoActaFirma.objects.values('id').filter(persona_id=idpersona, tipoacta__tipo=6, turnofirmar=True,
                                                          firmado=False, status=True).count()
    return faltantes


def firmaactagradosistema(idgraduado):
    return TipoActaFirma.objects.values('id').filter(tipoacta__graduado_id=idgraduado, tipoacta__tipo=5,
                                                     status=True).exists()


def notafinalmateriatitulacion(idmateriatitulacion, idmate):
    lista = []
    listanotas = []
    sumatoria = 0
    estadonota = 1
    matetitulacion = MateriaTitulacion.objects.get(pk=idmateriatitulacion)
    listadomateriagrupo = MateriaGrupoTitulacion.objects.filter(
        grupo__materia_id=matetitulacion.materiaasignada.materia.id, status=True).order_by('orden')
    for materiagrupo in listadomateriagrupo:
        listaprodecesoratitulacion = MateriaAsignada.objects.filter(
            matricula__inscripcion_id=matetitulacion.materiaasignada.matricula.inscripcion.id,
            materia__asignaturamalla_id=materiagrupo.asignaturamalla.id, status=True).order_by('-id')
        if not listaprodecesoratitulacion and matetitulacion.materiaasignada.materia.asignaturamalla.malla.modalidad.id == 3:
            listaprodecesoratitulacion = MateriaAsignada.objects.filter(
                matricula__inscripcion_id=matetitulacion.materiaasignada.matricula.inscripcion.id,
                materia__asignaturamalla__asignatura_id=materiagrupo.asignaturamalla.asignatura.id, status=True).order_by('-id')

            if MateriaAsignada.objects.filter(
                matricula__inscripcion_id=matetitulacion.materiaasignada.matricula.inscripcion.id,
                materia__asignaturamalla__asignatura_id=materiagrupo.asignaturamalla.asignatura.id, status=True):
                calculanota = round((listaprodecesoratitulacion[0].notafinal * materiagrupo.puntaje) / 100, 0)
                sumatoria = sumatoria + calculanota
                lista.append([calculanota, materiagrupo.nombre])
        else:
            if MateriaAsignada.objects.filter(
                    matricula__inscripcion_id=matetitulacion.materiaasignada.matricula.inscripcion.id,
                    materia__asignaturamalla_id=materiagrupo.asignaturamalla.id, status=True):
                calculanota = round((listaprodecesoratitulacion[0].notafinal * materiagrupo.puntaje) / 100, 0)
                sumatoria = sumatoria + calculanota
                lista.append([calculanota, materiagrupo.nombre])
    if sumatoria >= 70:
        estadonota = 2
    listanotas.append([lista, 'NOTA FINAL', sumatoria, estadonota])
    return listanotas


def listar_campos_tabla(modelo, dbname, schema='public'):
    from django.db import connections
    query = "SELECT column_name FROM information_schema.columns WHERE table_schema = '{}' AND table_name   = '{}';".format(
        schema, modelo)
    cursor = connections[dbname].cursor()
    cursor.execute(query)
    campos = list([c[0] for c in cursor.fetchall()])
    return campos


def tieneestudiantepracticas(detalle, dis_docente):
    resp = False
    if detalle.criteriodocenciaperiodo.criterio.pk == 6:
        dis_periodo = detalle.distributivo.periodo
        # practicas = PracticasPreprofesionalesInscripcion.objects.values_list('id').filter(Q(tutorunemi=dis_docente),
        #                                                                                 ((Q(fechadesde__gte=dis_periodo.inicio) & Q(fechadesde__lte=dis_periodo.fin)) |
        #                                                                                 (Q(fechahasta__gte=dis_periodo.inicio) & Q(fechahasta__lte=dis_periodo.fin))),
        #                                                                                 Q(estadosolicitud=2)).distinct()
        practicas = PracticasPreprofesionalesInscripcion.objects.values_list('id').filter(
            preinscripcion__preinscripcion__periodo__isnull=False, preinscripcion__preinscripcion__periodo=dis_periodo,
            tutorunemi=dis_docente, estadosolicitud=2).distinct()
        resp = practicas.exists()
    return resp


@register.filter
def contar_estado_solicitud(practica, estadosolicitud):
    return PracticasPreprofesionalesInscripcion.objects.filter(
        supervisor=practica.supervisor,
        preinscripcion__preinscripcion__periodo=practica.preinscripcion.preinscripcion.periodo,
        inscripcion__carrera=practica.inscripcion.carrera, estadosolicitud=estadosolicitud).count()


def times(number):
    return range(number)


def multipilca(number):
    return number * 5


def llevaraporcentaje(number):
    valor = (number * 100) / 5
    return null_to_decimal(valor, 2)


def nombremescorto(fecha):
    if type(fecha) is str:
        return "%s" % fecha[:3].capitalize()
    else:
        return "%s %s" % (fecha.day, MESES_CHOICES[fecha.month - 1][1][:3].capitalize())


def numerotemas(numero):
    num = ''
    num = numero * 2;
    if num == 1:
        num = 2;
    return str(num - 1) + '-' + str(num)


def numerotemasdiv(numero):
    num = ''
    num = numero * 2;
    return int(num)


def substraer(value, rmostrar):
    return "%s" % value[:rmostrar]


def substraerconpunto(value, rmostrar):
    if len(value) > int(rmostrar):
        return "%s..." % value[:rmostrar]
    else:
        return "%s" % value[:rmostrar]


def substraersinpuntohasta(value, rmostrar):
    if len(value) > int(rmostrar):
        return "%s" % value[:rmostrar]
    else:
        return "%s" % value[:rmostrar]


def substraersinpuntodesde(value, rmostrar):
    if len(value) > int(rmostrar):
        return "%s" % value[rmostrar:]
    else:
        return ""


def cambiarlinea(value, cant):
    cadena = ''
    c = 0
    for caracter in value:
        c = c + 1
        if c > cant:
            cadena = cadena + '<br />' + caracter
            c = 0
        else:
            cadena = cadena + "" + caracter
    return cadena


def contarcaracter(texto, cantidad):
    return len(texto) >= cantidad


def extraer(campo, cantidad):
    return campo[0:cantidad]


def nombremes(fecha):
    if type(fecha) is int:
        return "%s" % MESES_CHOICES[fecha - 1][1]
    elif type(fecha) is str:
        return ""
    else:
        return "%s" % MESES_CHOICES[fecha.month - 1][1]


def title2(texto=''):
    return " ".join([x.capitalize() if x.__len__() > 3 else x.lower() for x in f"{texto}".lower().split(' ')])


def numero_a_letras(numero):
    from sga.funciones import numero_a_letras
    return numero_a_letras(numero)

@register.simple_tag
def calcular_tiempo_cumplimiento (ini,fin):
    if ini and fin and ini != fin:
        mes = (fin.year - ini.year) * 12 + fin.month - ini.month
        if fin.day < ini.day:
            mes -= 1
            dias = ini.day - fin.day
        else:
            dias = fin.day - ini.day
        return f"{mes} Meses - {dias} Dias"
    return ""

def numeromes(fecha):
    return trimestre(int(fecha.strftime("%m")))


def fechapermiso(fecha):
    if datetime.now().date() >= fecha:
        return True
    else:
        return False


def entrefechas(finicio, ffin):
    if datetime.now().date() >= finicio and datetime.now().date() <= ffin:
        return True
    else:
        return False


def datename(fecha):
    return u"%s de %s de %s" % (str(fecha.day).rjust(2, "0"), nombremes(fecha=fecha).capitalize(), fecha.year)


def datetimename(dt):
    return u"%s de %s del %s %s:%s" % (
        str(dt.day).rjust(2, "0"), nombremes(fecha=dt).capitalize(), dt.year, str(dt.hour).rjust(2, "0"),
        str(dt.minute).rjust(2, "0"))


def sumarfecha(fecha):
    meses = int(round((((datetime.now().date() - fecha).days) / 30), 0))
    return meses


def sumarvalores(n1, n2):
    suma = int(n1) + int(n2)
    return suma


def nombrepersona(usuario):
    if Persona.objects.filter(usuario=usuario).exists():
        return Persona.objects.filter(usuario=usuario)[0]
    return None


def encrypt(value):
    if value == None:
        return value
    myencrip = ""
    if type(value) != str:
        value = str(value)
    i = 1
    for c in value.zfill(20):
        myencrip = myencrip + chr(int(44450 / 350) - ord(c) + int(i / int(9800 / 4900)))
        i = i + 1
    return myencrip


def encrypt_alu(value):
    if value == None:
        return value
    myencrip = ""
    if type(value) != str:
        value = str(value)
    i = 1
    for c in value.zfill(20):
        myencrip = myencrip + chr(int(44450 / 350) - ord(c) + int(i / int(14700 / 4900)))
        i = i + 1
    return myencrip


def solo_caracteres(texto):
    acentos = [u'á', u'é', u'í', u'ó', u'ú', u'Á', u'É', u'Í', u'Ó', u'Ú', u'ñ', u'Ñ']
    alfabeto = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u',
                'v', 'w', 'x', 'y', 'z', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F',
                'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '.',
                '/', '#', ',', ' ']
    resultado = ''
    for letra in texto:
        if letra in alfabeto:
            resultado += letra
        elif letra in acentos:
            if letra == u'á':
                resultado += 'a'
            elif letra == u'é':
                resultado += 'e'
            elif letra == u'í':
                resultado += 'i'
            elif letra == u'ó':
                resultado += 'o'
            elif letra == u'ú':
                resultado += 'u'
            elif letra == u'Á':
                resultado += 'A'
            elif letra == u'É':
                resultado += 'E'
            elif letra == u'Í':
                resultado += 'I'
            elif letra == u'Ó':
                resultado += 'O'
            elif letra == u'Ú':
                resultado += 'U'
            elif letra == u'Ñ':
                resultado += 'N'
            elif letra == u'ñ':
                resultado += 'n'
        else:
            resultado += '?'
    return resultado


def ceros(numero, cantidad):
    return str(numero).zfill(cantidad)


def fechamayor(fecha1, fecha2):
    if fecha1.date() > fecha2:
        return True
    else:
        return False


def fechamayor_aux(fecha1, fecha2):
    if convertir_fecha(fecha1) > fecha2:
        return True
    else:
        return False

def calculaedad(fecha1, fecha_actual):
    return fecha_actual.year - fecha1.year - ((fecha_actual.month, fecha_actual.day) < (fecha1.month, fecha1.day))


def transformar_n_l(n):
    arreglo = ['PRIMERO', 'SEGUNDO', 'TERCERO', 'CUARTO', 'QUINTO', 'SEXTO', 'SEPTIMO', 'OCTAVO', 'NOVENO', 'DECIMO']
    n2 = 10 if n >= 13 else n
    return arreglo[n2 - 1] if n else ""


def sumauno(numero):
    return numero + 1


def transformar_mes(n):
    arreglo = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre",
               "Noviembre", "Diciembre"]
    return arreglo[n - 1] if n else "SIN MES"


def diaenletra(dia):
    arreglo = ['LUNES', 'MARTES', 'MIERCOLES', 'JUEVES', 'VIERNES', 'SABADO', 'DOMINGO']
    return arreglo[int(dia) - 1]


def diaenletra_fecha(fecha):
    dia = fecha.isoweekday()
    return DIAS_CHOICES[dia - 1][1]


def diaisoweekday(fecha):
    return fecha.isoweekday()


def traernombre(idsesion):
    nombresesion = Sesion.objects.get(pk=idsesion)
    return nombresesion.nombre


def traernombrecarrera(idcarrera):
    nombre = Carrera.objects.get(pk=idcarrera)
    return nombre.nombre


# NO TUVE MAS REMEDIO QUE HACER FUNCIONES MUERTAS PARA UN SOLO REPORTE PIDO MIL DISCULPAS A MIS ADMIRADORES ATT. CLOCKEM
def sumar_fm(value, lista):
    su = 0
    for l in lista:
        if value == l[0]:
            su += l[3]
    return su


def sumar_fh(value, lista):
    su = 0
    for l in lista:
        if value == l[0]:
            su += l[4]
    return su


def sumar_cm(value, lista):
    su = 0
    for l in lista:
        if value[1] == l[1] and value[0] == l[0]:
            su += l[3]
    return su


def sumar_ch(value, lista):
    su = 0
    for l in lista:
        if value[1] == l[1] and value[0] == l[0]:
            su += l[4]
    return su


def sumar_th(value, lista):
    su = 0
    for l in lista:
        su += l[4]
    return su


def sumar_tm(value, lista):
    su = 0
    for l in lista:
        su += l[3]
    return su


def sumar_pagineo(totalpagina, contador):
    suma = totalpagina + contador
    return suma


def colores(colores, indice):
    color = colores[indice]
    return color

#permite un numero maximo de palabra de una descripcion

@register.filter
def max_length_chars(value, max_length):
    if len(value) > max_length:
        return value[:max_length] + '...'
    return value

# AQUI TERMINA LAS FUNCIONES NO REUTILIZABLES :(

def rangonumeros(_min, args=None):
    _max, _step = None, None
    if args:
        if not isinstance(args, int):
            _max, _step = map(int, args.split(','))
        else:
            _max = args
    args = filter(None, (_min, _max + 1, _step))
    return range(*args)


def splitcadena(string, sep):
    return string.split(sep)


def tranformarstring(valor):
    return str(valor)


def mod4(valor):
    return divmod(valor, 4)[1]


@register.filter
def convert_str_date(value):
    return str(value)[:10]


def num_notificaciones_modulo(idm, perfil):
    if not Modulo.objects.values("id").filter(pk=idm).exists():
        return 0
    eModulo = Modulo.objects.get(pk=idm)
    if not eModulo.tiene_notificaciones(perfil.persona.id, perfil.id):
        return 0
    return eModulo.num_notificaciones(perfil.persona.id, perfil.id)


def get_manual_usuario_modulo(idm, perfil):
    if not Modulo.objects.values("id").filter(pk=idm).exists():
        return None
    eModulo = Modulo.objects.get(pk=idm)
    return eModulo.get_manual_user(perfil)


@register.inclusion_tag('pwa.html', takes_context=True)
def progressive_web_app_meta_i(context):
    # Pass all PWA_* settings into the template
    return {
        setting_name: getattr(settings, setting_name)
        for setting_name in dir(settings)
        if setting_name.startswith('PWA_')
    }


@register.filter
def split(val, sep):
    return val.split(sep)


@register.simple_tag
def get_image_path(image_path):
    path = default_storage.path(image_path)
    return path


def obtener_tribunal(obj):
    return obj.tribunaltematitulacionposgradomatricula_set.filter(status=True).first()


@register.filter
def obtener_numero_de_revision_tribunal(obj):
    from posgrado.models import Revision
    mensaje = ""
    tribunal = obtener_tribunal(obj)
    revisiones = Revision.objects.filter(status=True, tribunal=tribunal)
    if revisiones.exists():
        cantidad_revision = revisiones.count()
    else:
        cantidad_revision = 0

    if cantidad_revision == 0:
        mensaje = "Informe de revisión no generado"

    if cantidad_revision == 1:
        mensaje = "Primera revisión del trabajo de titulación"

    if cantidad_revision == 2:
        mensaje = "Segunda revisión del trabajo de titulación"

    if cantidad_revision == 3:
        mensaje = "Tercera revisión del trabajo de titulación"

    return mensaje


def obtener_tribunal_pareja(obj):
    return obj.tribunaltematitulacionposgradomatricula_set.filter(status=True).first()


@register.filter
def obtener_numero_de_revision_tribunal_pareja(obj):
    from posgrado.models import Revision
    mensaje = ""
    tribunal = obtener_tribunal_pareja(obj)
    revisiones = Revision.objects.filter(status=True, tribunal=tribunal)
    if revisiones.exists():
        cantidad_revision = revisiones.count()
    else:
        cantidad_revision = 0

    if cantidad_revision == 0:
        mensaje = "Informe de revisión no generado"

    if cantidad_revision == 1:
        mensaje = "Primera revisión del trabajo de titulación"

    if cantidad_revision == 2:
        mensaje = "Segunda revisión del trabajo de titulación"

    if cantidad_revision == 3:
        mensaje = "Tercera revisión del trabajo de titulación"

    return mensaje


@register.filter
def convertir_tipo_oracion(texto):
    try:
        oraciones = texto.split('.')
        full = [oracion.strip() for oracion in oraciones if oracion.strip() != '']
        final = ''
        for oracion in full:
            final += "".join(oracion[0].upper() + oracion[1:].lower())
        return final
    except:
        return ''


@register.filter
def concat_str_int(value, args):
    try:
        return int(str(int(value)) + str(int(args)))
    except:
        return ''


@register.simple_tag
def contador_lista(page, forloop_counter):
    return ((page.number - 1) * page.paginator.per_page) + forloop_counter


def realizo_busqueda(url_vars='', numero=1):
    return len(url_vars.split('&')) - numero > 1


@register.simple_tag
def materias_imparte_periodo_seguimiento_silabo(obj, periodo, carreras, carrerasselected, asignaturaid, nivelid, paraleloid, super_directivos):
    from sga.models import Materia
    filtro = Q(status=True)
    if int(asignaturaid) > 0:
        filtro = filtro & Q(asignaturamalla__asignatura__id=asignaturaid)
    if int(nivelid) > 0:
        filtro = filtro & Q(asignaturamalla__nivelmalla__id=nivelid)
    if paraleloid != '0':
        filtro = filtro & Q(paralelo=paraleloid)
    if super_directivos == False:
        return Materia.objects.filter(filtro, profesormateria__activo=True, profesormateria__status=True,
                                      asignaturamalla__malla__carrera__id__in=carreras,
                                      nivel__periodo=periodo, profesormateria__tipoprofesor__in=[1, 14],
                                      profesormateria__profesor=obj, profesormateria__principal = True, profesormateria__hora__gt=0).exclude(asignaturamalla__tipomateria__id = 3).distinct().order_by('asignaturamalla__malla__carrera__nombre',
            'asignaturamalla__nivelmalla__nombre')
    else:
        if int(carrerasselected) > 0:
            filtro = filtro & Q(asignaturamalla__malla__carrera__id=carrerasselected)
        else:
            filtro = filtro & Q(asignaturamalla__malla__carrera__id__in=carreras)
        return Materia.objects.filter(filtro, profesormateria__activo=True, profesormateria__status=True,
                                      nivel__periodo=periodo, profesormateria__tipoprofesor__in=[1, 14],
                                      profesormateria__profesor=obj, profesormateria__principal = True, profesormateria__hora__gt=0).exclude(asignaturamalla__tipomateria__id = 3).distinct().order_by('asignaturamalla__malla__carrera__nombre',
            'asignaturamalla__nivelmalla__nombre')


@register.simple_tag
def carreras_imparte2(obj, materias):
    carreras = []
    try:
        # materias = obj.materias_imparte_periodo_seguimiento_silabo()
        for materia in materias:
            carreras.append(materia.asignaturamalla.malla.carrera)
        return set(carreras)
    except Exception as ex:
        return None


@register.simple_tag
def informe_actividades_mensual_docente_v4_extra(obj, periodo, fechaini, fechafin, tipo, tablepromedio=None):
    from sga.models import ProfesorDistributivoHoras, ProfesorMateria
    fini = convertir_fecha_invertida(fechaini)
    ffin = convertir_fecha_invertida(fechafin)
    distributivo = ProfesorDistributivoHoras.objects.filter(periodo=periodo, profesor=obj, status=True)
    if tipo == 'TODO' or tipo == 'FACULTAD':
        if not distributivo.exists():
            mensaje = "No registra actividades de docencia, verifique el periodo."
            raise NameError('Error')
    if distributivo:
        distributivo = distributivo[0]
    return {'distributivo': distributivo, 'fini': fini, 'ffin': ffin}


@register.simple_tag
def horarios_contenido_profesor_extra(obj, profesor, materia, fechaini, fechafin):
    try:
        from sga.models import DetalleDistributivo, GuiaEstudianteSilaboSemanal, TareaPracticaSilaboSemanal, \
            TipoProfesor, ProfesorMateria, ClaseActividad, Silabo, CompendioSilaboSemanal, VideoMagistralSilaboSemanal, \
            ForoSilaboSemanal, TareaSilaboSemanal, TestSilaboSemanalAdmision, TestSilaboSemanal, \
            DiapositivaSilaboSemanal, MaterialAdicionalSilaboSemanal, SilaboSemanal
        periodorelacionado = False
        listado = []
        periodo = obj.periodo
        fechaactual = datetime.now().date()
        periodos = [obj.periodo.pk]
        detalledistributivo = DetalleDistributivo.objects.get(criteriodocenciaperiodo=obj,
                                                              distributivo__profesor=profesor, status=True)
        fechasactividades = detalledistributivo.actividaddetalledistributivo_set.filter(status=True)[0]
        fechaini = periodo.inicio if fechaini < periodo.inicio else fechaini
        if obj.periodosrelacionados.exists():
            periodorelacionado = True
            periodos = []
            for per in obj.periodosrelacionados.values_list('id', flat=True):
                periodos.append(per)
        if periodos:
            periodorelacionado = ProfesorMateria.objects.values('id').filter(profesor=profesor, materia=materia,
                                                                             materia__nivel__periodo_id__in=periodos).distinct().exists()

        profesormateria = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__periodo_id__in=periodos,
                                                         materia=materia,
                                                         activo=True, materia__fin__gte=fechasactividades.desde,
                                                         materia__inicio__lte=fechasactividades.hasta).exclude(
            tipoprofesor_id=15).only('materia').distinct()
        for m in profesormateria:
            if not m.materia.tiene_cronograma():
                return 0
        claseactividad = ClaseActividad.objects.filter(detalledistributivo__criteriodocenciaperiodo=obj,
                                                       detalledistributivo__distributivo__profesor=profesor,
                                                       status=True).order_by('inicio', 'dia', 'turno__comienza')

        # para saber total de horas en el mes
        diasclas = claseactividad.values_list('dia', 'turno_id')
        dt = fechaini
        end = fechafin
        step = timedelta(days=1)
        listaretorno = []
        result = []
        while dt <= end:
            dias_nolaborables = obj.periodo.dias_nolaborables(dt)
            if not dias_nolaborables:
                for dclase in diasclas:
                    if dt.isocalendar()[2] == dclase[0]:
                        result.append(dt.strftime('%Y-%m-%d'))
            dt += step
        # if periodo.clasificacion == 1:
        listadotipoprofesor = TipoProfesor.objects.filter(
            pk__in=ProfesorMateria.objects.values_list('tipoprofesor_id').filter(profesor=profesor, materia=materia,
                                                                                 materia__nivel__periodo_id__in=periodos,
                                                                                 tipoprofesor_id__in=[1, 2, 5, 6, 10,
                                                                                                      11, 12, 14, 16],
                                                                                 activo=True,
                                                                                 materia__fin__gte=fechasactividades.desde,
                                                                                 materia__inicio__lte=fechasactividades.hasta).exclude(
                materia__modeloevaluativo_id__in=[26]).distinct())
        resultadominimoplanificar = 0
        resultadoplanificados = 0
        resultadoparciales = '-'
        resultadoporcentajes = 0
        resultadoporcentajessyl = 0
        sumatoriaindice = 0
        sumatoriaindicesyl = 0
        resultadototal = 0
        subtipo_docentes = 0
        listasilabofaltasilabo = []
        for ltipoprofesor in listadotipoprofesor:
            subtipo_docentes = 1
            nivelacion = False
            listadosilabos = Silabo.objects.filter(status=True, materia_id__in=ProfesorMateria.objects.values_list(
                'materia_id').filter(profesor=profesor, materia__nivel__periodo_id__in=periodos, materia=materia,
                                     tipoprofesor=ltipoprofesor, activo=True, materia__fin__gte=fechasactividades.desde,
                                     materia__inicio__lte=fechasactividades.hasta).distinct())
            if listadosilabos:
                if listadosilabos.filter(materia__asignaturamalla__malla__carrera__coordinacion__id=9).exists():
                    subtipo_docentes += 1
                    nivelacion = True
                    listadosilabos = Silabo.objects.filter(status=True,
                                                           materia_id__in=ProfesorMateria.objects.values_list(
                                                               'materia_id').filter(profesor=profesor, materia=materia,
                                                                                    materia__nivel__periodo_id__in=periodos,
                                                                                    tipoprofesor=ltipoprofesor,
                                                                                    activo=True,
                                                                                    materia__fin__gte=fechasactividades.desde,
                                                                                    materia__inicio__lte=fechasactividades.hasta).exclude(
                                                               materia__asignaturamalla__malla__carrera__coordinacion__id=9).distinct())
                while subtipo_docentes > 0:
                    if not listadosilabos and nivelacion:
                        subtipo_docentes -= 1
                    if subtipo_docentes == 1 and nivelacion:
                        listadosilabos = Silabo.objects.filter(status=True,
                                                               materia_id__in=ProfesorMateria.objects.values_list(
                                                                   'materia_id').filter(profesor=profesor,
                                                                                        materia=materia,
                                                                                        materia__nivel__periodo_id__in=periodos,
                                                                                        tipoprofesor=ltipoprofesor,
                                                                                        activo=True,
                                                                                        materia__fin__gte=fechasactividades.desde,
                                                                                        materia__inicio__lte=fechasactividades.hasta,
                                                                                        materia__asignaturamalla__malla__carrera__coordinacion__id=9).distinct())
                    listadosilabos = listadosilabos.exclude(materia__modeloevaluativo_id__in=[26, 27])
                    totalsilabos = listadosilabos.count()
                    totalsilabosplanificados = listadosilabos.filter(codigoqr=True).count()
                    porcentaje = 0
                    if periodorelacionado:
                        if totalsilabosplanificados >= 1:
                            porcentaje = 100
                    else:
                        try:
                            porcentaje = round(((100 * totalsilabosplanificados) / totalsilabos), 2)
                        except ZeroDivisionError:
                            porcentaje = 0
                    totalcompendioplanificada = 0
                    totalvideoplanificada = 0
                    totalguiaestplanificada = 0
                    totalmaterialplanificada = 0
                    totalcompendiosmoodle = 0
                    totalvideomoodle = 0
                    totalguiaestmoodle = 0
                    totaldiapositivasmoodle = 0
                    totalunidades = 0
                    totalacdplanificado = 0
                    totalacdplanificadosinmigrar = 0
                    totalaaplanificado = 0
                    totalaaplan = 0
                    totalaaplanificadosinmigrar = 0
                    totalapeplanificado = 0
                    totalapeplanificadosinmigrar = 0
                    minimoacd = 0
                    minimoaa = 0
                    minimoape = 0
                    tieneape = 0
                    totaldiapositivaplanificada = 0
                    totalmaterialplanificada = 0
                    totalmaterialmoodle = 0
                    totalunidades = 0
                    nombretipo = '{} - NIVELACIÓN'.format(
                        ltipoprofesor.nombre) if subtipo_docentes == 1 and nivelacion else ltipoprofesor.nombre
                    listadolineamiento = ltipoprofesor.lineamientorecursoperiodo_set.filter(periodo_id__in=periodos,
                                                                                            status=True,
                                                                                            nivelacion=True) if subtipo_docentes == 1 and nivelacion else ltipoprofesor.lineamientorecursoperiodo_set.filter(
                        periodo_id__in=periodos, status=True, nivelacion=False)
                    listado.append([claseactividad, nombretipo, 0, 0, 0, 0, 3])
                    bandera = 0
                    if nombretipo == 'PRÁCTICA':
                        bandera = 1
                    listamateriasfaltaguias = []
                    listamateriasfaltavideo = []
                    listamateriasfaltacompendio = []
                    listamateriasfaltadiapositiva = []
                    listamateriasfaltamaterial = []
                    listamateriasfaltaaa = []
                    listamateriasfaltaacd = []
                    listamateriasfaltaape = []
                    totalminimoacd = 0
                    totalminimoaa = 0
                    totalminimoape = 0
                    totalaamoodle = 0
                    totalacdmoodle = 0
                    totalapemoodle = 0
                    listamateriasfaltadiapositiva = []
                    listamateriasfaltamaterial = []
                    iddiapositiva = 2
                    idmateriales = 11
                    cantidadplanificadatest = 0
                    fechafinsemana = 0
                    i = 0
                    for lsilabo in listadosilabos:
                        # ini -- para saber cuantas unidades han cerrado
                        materiaplanificacion = lsilabo.materia.planificacionclasesilabo_materia_set.filter(
                            status=True).first()
                        listadoparciales = materiaplanificacion.tipoplanificacion.planificacionclasesilabo_set.values_list(
                            'parcial', 'fechafin').filter(status=True).distinct('parcial').order_by('parcial',
                                                                                                    '-fechafin').exclude(
                            parcial=None)
                        if nivelacion:
                            fechamaximalimite = fechasactividades.hasta
                        else:
                            fechamaximalimite = fechafin
                        parciales = listadoparciales.values_list('parcial', 'fechafin', 'fechainicio'). \
                            filter(Q(status=True),
                                   Q(fechafin__lte=fechamaximalimite) | Q(fechainicio__lte=fechamaximalimite)). \
                            distinct('parcial').order_by('parcial', '-fechafin')
                        listaparcialterminadas = []
                        estadoparcial = 'ABIERTO'
                        idparcial = 1
                        fechaparcial = ''
                        for sise in parciales:
                            if sise[1] <= fechafin or sise[2] <= fechafin:
                                listaparcialterminadas.append(sise[0])
                        if not lsilabo.codigoqr:
                            listasilabofaltasilabo.append([2, lsilabo.id, lsilabo.materia, 0, 1])
                        listaunidadterminadas = []
                        silabosemanaluni = lsilabo.silabosemanal_set.values_list(
                            'detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden',
                            'fechafinciosemana').filter(status=True).distinct(
                            'detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden').order_by(
                            'detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden',
                            '-fechafinciosemana')
                        for sise in silabosemanaluni:
                            # if sise[1] >= fechaini and sise[1] <= fechafin:
                            if sise[0]:
                                if sise[1] <= fechafin:
                                    if not sise[0] in listaunidadterminadas:
                                        listaunidadterminadas.append(sise[0])
                        if not listaunidadterminadas:
                            listaunidadterminadas.append(1)
                        # fin --

                        ############################################################################################

                        # silabosemanal = lsilabo.silabosemanal_set.filter(fechafinciosemana__range=(fechaini, fechafin),detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden__in=listaunidadterminadas,status=True)
                        silabosemanal = lsilabo.silabosemanal_set.filter(
                            detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden__in=listaunidadterminadas,
                            detallesilabosemanaltema__status=True, status=True).distinct()
                        totaltemas = 0
                        totalunidades = len(listaunidadterminadas)
                        runidad = []
                        unidades = silabosemanal.filter(status=True).values_list(
                            'detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico_id',
                            flat=True).distinct()
                        for silabosemana in silabosemanal:
                            for u in unidades:
                                if not u in runidad:
                                    runidad.append(u)
                                    totaltemas += len(silabosemana.temas_silabounidad_fecha(u, fechafin))
                                    #########################################

                        # para sacar diapositivas
                        iddiapositiva = 2
                        if iddiapositiva in listadolineamiento.values_list('tiporecurso', flat=True):
                            if lsilabo.materia.nivel.periodo.lineamientorecursoperiodo_set.exists():
                                totaldiapositivas = DiapositivaSilaboSemanal.objects.filter(
                                    silabosemanal_id__in=silabosemanal.values_list('id'),
                                    iddiapositivamoodle__gt=0,
                                    status=True).count()
                                multiplicador = len(listaparcialterminadas)
                                busc = lsilabo.materia.nivel.periodo.lineamientorecursoperiodo_set.filter(
                                    tipoprofesor_id__in=lsilabo.materia.profesormateria_set.values_list(
                                        'tipoprofesor').filter(status=True, profesor=profesor,
                                                               tipoprofesor=ltipoprofesor),
                                    tiporecurso=2, status=True)
                                if subtipo_docentes == 1 and nivelacion:
                                    totalminimoacd = 0
                                    busc = busc.filter(nivelacion=True)
                                    for lineaminetoacd in busc.filter(tiporecurso=iddiapositiva):
                                        if lineaminetoacd.aplicapara == 1:
                                            multiplicador = totalunidades
                                        elif lineaminetoacd.aplicapara == 2:
                                            multiplicador = totaltemas
                                totaldiapositivaplan = busc[0].cantidad * multiplicador
                                totaldiapositivaplanificada += totaldiapositivaplan

                                if totaldiapositivas > totaldiapositivaplan:
                                    totaldiapositivasmoodle += totaldiapositivaplan
                                else:
                                    totaldiapositivasmoodle += totaldiapositivas

                                listamateriasfaltadiapositiva.append(
                                    [1, lsilabo.id, lsilabo.materia, totaldiapositivas,
                                     totaldiapositivaplan])

                        # para sacar materialcomplementario
                        idmateriales = 11
                        if idmateriales in listadolineamiento.values_list('tiporecurso', flat=True):
                            if lsilabo.materia.nivel.periodo.lineamientorecursoperiodo_set.exists():
                                totalmateriales = MaterialAdicionalSilaboSemanal.objects.filter(
                                    silabosemanal_id__in=silabosemanal.values_list('id'),
                                    idmaterialesmoodle__gt=0,
                                    status=True).count()
                                multiplicador = len(listaparcialterminadas)
                                lsilabo.materia.nivel.periodo.lineamientorecursoperiodo_set.filter(
                                    tipoprofesor_id__in=lsilabo.materia.profesormateria_set.values_list(
                                        'tipoprofesor').filter(status=True, profesor=profesor,
                                                               tipoprofesor=ltipoprofesor), tiporecurso=11,
                                    status=True)

                                busc = lsilabo.materia.nivel.periodo.lineamientorecursoperiodo_set.filter(
                                    tipoprofesor_id__in=lsilabo.materia.profesormateria_set.values_list(
                                        'tipoprofesor').filter(status=True, profesor=profesor,
                                                               tipoprofesor=ltipoprofesor),
                                    tiporecurso=11, status=True)
                                if subtipo_docentes == 1 and nivelacion:
                                    totalminimoacd = 0
                                    busc = busc.filter(nivelacion=True)
                                    for lineaminetoacd in busc.filter(tiporecurso=iddiapositiva):
                                        if lineaminetoacd.aplicapara == 1:
                                            multiplicador = totalunidades
                                        elif lineaminetoacd.aplicapara == 2:
                                            multiplicador = totaltemas
                                else:
                                    busc = busc.exclude(nivelacion=True)
                                totalmaterialplan = busc[0].cantidad * multiplicador
                                totalmaterialplanificada += totalmaterialplan
                                if totalmateriales > totalmaterialplan:
                                    totalmaterialmoodle += totalmaterialplan
                                else:
                                    totalmaterialmoodle += totalmateriales

                                listamateriasfaltamaterial.append(
                                    [2, lsilabo.id, lsilabo.materia, totalmateriales, totalmaterialplan])

                        ########################################
                        # para sacar compendios
                        idcompendio = 1
                        if idcompendio in listadolineamiento.values_list('tiporecurso', flat=True):
                            totalcompendios = CompendioSilaboSemanal.objects.filter(
                                silabosemanal_id__in=silabosemanal.values_list('id'), idmcompendiomoodle__gt=0,
                                status=True).count()
                            totalcompendioplan = lsilabo.materia.nivel.periodo.lineamientorecursoperiodo_set.filter(
                                tipoprofesor_id__in=lsilabo.materia.profesormateria_set.values_list(
                                    'tipoprofesor').filter(status=True, materia=materia), tiporecurso=1, status=True)[
                                                     0].cantidad * len(
                                listaunidadterminadas)
                            totalcompendioplanificada += totalcompendioplan
                            if totalcompendios > totalcompendioplan:
                                totalcompendiosmoodle += totalcompendioplan
                            else:
                                totalcompendiosmoodle += totalcompendios
                            if totalcompendios < totalcompendioplan:
                                listamateriasfaltacompendio.append(
                                    [lsilabo.id, lsilabo.materia, totalcompendios, totalcompendioplan])

                        # para sacar videomagistral
                        idvideomagistral = 12
                        if idvideomagistral in listadolineamiento.values_list('tiporecurso', flat=True):
                            totalvideos = VideoMagistralSilaboSemanal.objects.filter(
                                silabosemanal_id__in=silabosemanal.values_list('id'), idvidmagistralmoodle__gt=0,
                                status=True).count()
                            totalvideoplan = lsilabo.materia.nivel.periodo.lineamientorecursoperiodo_set.filter(
                                tipoprofesor_id__in=lsilabo.materia.profesormateria_set.values_list(
                                    'tipoprofesor').filter(status=True, materia=materia), tiporecurso=12, status=True)[
                                                 0].cantidad * len(
                                listaunidadterminadas)
                            totalvideoplanificada += totalvideoplan
                            if totalvideos > totalvideoplan:
                                totalvideomoodle += totalvideoplan
                            else:
                                totalvideomoodle += totalvideos
                            if totalvideos < totalvideoplan:
                                listamateriasfaltavideo.append(
                                    [lsilabo.id, lsilabo.materia, totalvideos, totalvideoplan])

                        # para sacar guiaestudiante
                        idguiaestudiante = 4
                        if idguiaestudiante in listadolineamiento.values_list('tiporecurso', flat=True):
                            totalguiaestudiante = GuiaEstudianteSilaboSemanal.objects.filter(
                                silabosemanal_id__in=silabosemanal.values_list('id'), idguiaestudiantemoodle__gt=0,
                                status=True).count()
                            totalguiaestudianteplan = \
                                lsilabo.materia.nivel.periodo.lineamientorecursoperiodo_set.filter(
                                    tipoprofesor_id__in=lsilabo.materia.profesormateria_set.values_list(
                                        'tipoprofesor').filter(status=True, materia=materia), tiporecurso=4,
                                    status=True)[0].cantidad * len(
                                    listaunidadterminadas)
                            totalguiaestplanificada += totalguiaestudianteplan
                            if totalguiaestudiante > totalguiaestudianteplan:
                                totalguiaestmoodle += totalguiaestudianteplan
                            else:
                                totalguiaestmoodle += totalguiaestudiante
                            if totalguiaestudiante < totalguiaestudianteplan:
                                listamateriasfaltaguias.append(
                                    [lsilabo.id, lsilabo.materia, totalguiaestudiante, totalguiaestudianteplan])

                        # para sacar los compenentes acd ,aa ,ape
                        materiaplanificacion = lsilabo.materia.planificacionclasesilabo_materia_set.filter(status=True)[
                            0]
                        listadoparciales = materiaplanificacion.tipoplanificacion.planificacionclasesilabo_set.values_list(
                            'parcial', 'fechafin').filter(status=True).distinct('parcial').order_by('parcial',
                                                                                                    '-fechafin').exclude(
                            parcial=None)
                        if obj.periodosrelacionados.exists():
                            if nivelacion:
                                fecha_limite = fechasactividades.hasta + timedelta(days=30)
                            else:
                                fecha_limite = fechafin + timedelta(days=30)
                            parciales = listadoparciales.values_list('parcial', 'fechafin').filter(status=True,
                                                                                                   fechafin__lte=fecha_limite).distinct(
                                'parcial').order_by('parcial', '-fechafin')
                        else:
                            parciales = listadoparciales.values_list('parcial', 'fechafin', 'fechainicio').filter(
                                Q(status=True), Q(fechafin__lte=fechafin) | Q(fechainicio__lte=fechafin)).distinct(
                                'parcial').order_by('parcial', '-fechafin')
                        listaparcialterminadas = []
                        estadoparcial = 'ABIERTO'
                        idparcial = 1 if not obj.periodo.tipo.id in [3, 4] else 0
                        fechaparcial = ''
                        for sise in parciales:
                            if obj.periodosrelacionados.exists():
                                idparcial = sise[0]
                                listaparcialterminadas.append(sise[0])
                            else:
                                if sise[1] <= fechafin or sise[2] <= fechafin:
                                    idparcial = sise[0]
                                    listaparcialterminadas.append(sise[0])
                        for lpar in listadoparciales:
                            if listadoparciales.order_by('-parcial')[0][0] == lpar[0]:
                                if fechafin >= lpar[1]:
                                    estadoparcial = 'CERRADO'
                            if lpar[0] == idparcial:
                                fechaparcial = lpar[1]

                        if periodo.tipo.id not in [3, 4]:
                            listadocomponentes = lsilabo.materia.nivel.periodo.evaluacioncomponenteperiodo_set.select_related(
                                'componente').filter(nivelacion=True, parcial__in=listaparcialterminadas,
                                                     status=True) if subtipo_docentes == 1 and nivelacion else lsilabo.materia.nivel.periodo.evaluacioncomponenteperiodo_set.select_related(
                                'componente').filter(parcial__in=listaparcialterminadas, status=True)
                        else:
                            listadocomponentes = lsilabo.materia.nivel.periodo.evaluacioncomponenteperiodo_set.select_related(
                                'componente').filter(status=True)

                        # para sacar todos los silabos semanales segun fecha fin del parcial
                        silabosemanalparcial = lsilabo.silabosemanal_set.filter(fechafinciosemana__lte=fechaparcial,
                                                                                status=True)
                        # for silabosemana in silabosemanalparcial:
                        #     if lsilabo.silabosemanal_set.all()[i].listatest_semanales().count() > 0:
                        #         fechafinsemana = lsilabo.silabosemanal_set.values_list('fechafinciosemana',
                        #                                                                flat=True).filter(
                        #             status=True)[i]
                        #         if TestSilaboSemanal.objects.filter(silabosemanal=silabosemana,
                        #                                             silabosemanal_id__in=silabosemanalparcial.values_list(
                        #                                                 'id'), idtestmoodle__gt=0,
                        #                                             status=True).exists():
                        #             print('HA CUMPLIDO')
                        #         else:
                        #             if fechaactual <= fechafinsemana:
                        #                 print('PENDIENTE')
                        #             else:
                        #                 print('NO HA CUMPLIDO')
                        #     i += 1
                        if lsilabo.materia.modeloevaluativo.id != 25:
                            if listadocomponentes.filter(componente_id=1):
                                multiplicador = len(listaparcialterminadas)
                                if subtipo_docentes == 1 and nivelacion:
                                    totalminimoacd = 0
                                    for lineaminetoacd in listadolineamiento.filter(tiporecurso=7):
                                        if lineaminetoacd.aplicapara == 1:
                                            multiplicador = totalunidades
                                        elif lineaminetoacd.aplicapara == 2:
                                            multiplicador = totaltemas
                                        totalminimoacd += lineaminetoacd.cantidad * multiplicador
                                else:
                                    totalminimoacd = listadocomponentes.filter(componente_id=1,
                                                                               nivelacion=False).first().cantidad * multiplicador
                                minimoacd += totalminimoacd
                        totalacdplanificadotar = 0
                        totalacdplanificadosinmigrartar = 0
                        if (subtipo_docentes == 1 and not nivelacion) or (subtipo_docentes == 2 and nivelacion):
                            totalacdplanificadotar = TareaSilaboSemanal.objects.filter(
                                silabosemanal_id__in=silabosemanalparcial.values_list('id'), idtareamoodle__gt=0,
                                actividad_id__in=[2, 3], status=True).count()
                            totalacdplanificadosinmigrartar = TareaSilaboSemanal.objects.filter(
                                silabosemanal_id__in=silabosemanalparcial.values_list('id'),
                                actividad_id__in=[2, 3], status=True).count()

                        if subtipo_docentes == 1 and nivelacion:
                            totalacdplanificadotest = TestSilaboSemanalAdmision.objects.filter(
                                silabosemanal_id__in=silabosemanalparcial.values_list('id'), idtestmoodle__gt=0,
                                status=True).count()
                            totalacdplanificadosinmigrartest = TestSilaboSemanalAdmision.objects.filter(
                                silabosemanal_id__in=silabosemanalparcial.values_list('id'),
                                status=True).count()

                        else:
                            totalacdplanificadotest = TestSilaboSemanal.objects.filter(
                                silabosemanal_id__in=silabosemanalparcial.values_list('id'), idtestmoodle__gt=0,
                                tiporecurso_id__in=[11],
                                status=True).count()
                            totalacdplanificadosinmigrartest = TestSilaboSemanal.objects.filter(
                                silabosemanal_id__in=silabosemanalparcial.values_list('id'),tiporecurso_id__in=[11],
                                status=True).count()
                        totalacdplanificado += totalacdplanificadotar + totalacdplanificadotest
                        totalplanificadoacd = totalacdplanificadotar + totalacdplanificadotest

                        totalacdplanificadosinmigrar += totalacdplanificadosinmigrartar + totalacdplanificadosinmigrartest

                        if totalplanificadoacd > totalminimoacd:
                            totalacdmoodle += totalminimoacd
                        else:
                            totalacdmoodle += totalplanificadoacd
                        if estadoparcial == 'CERRADO':
                            if totalplanificadoacd < totalminimoacd:
                                listamateriasfaltaacd.append(
                                    [lsilabo.id, lsilabo.materia, totalplanificadoacd, totalminimoacd])

                        totalaaplanificadosinmigrartar = 0
                        if lsilabo.materia.modeloevaluativo.id != 25:
                            if listadocomponentes.filter(componente_id=3):
                                totalminimoaa = listadocomponentes.filter(componente_id=3)[0].cantidad * len(
                                    listaparcialterminadas)
                                minimoaa += totalminimoaa
                        totalplanificadoaatar = TareaSilaboSemanal.objects.filter(
                            silabosemanal_id__in=silabosemanalparcial.values_list('id'), idtareamoodle__gt=0,
                            actividad_id__in=[5, 7, 8], status=True).count()
                        totalplanificadoaasinmigrartar = TareaSilaboSemanal.objects.filter(
                            silabosemanal_id__in=silabosemanalparcial.values_list('id'),
                            actividad_id__in=[5, 7, 8], status=True).count()
                        totalplanificadoaafor = ForoSilaboSemanal.objects.filter(
                            silabosemanal_id__in=silabosemanalparcial.values_list('id'), idforomoodle__gt=0,
                            status=True).count()
                        totalplanificadoaasinmigrarfor = ForoSilaboSemanal.objects.filter(
                            silabosemanal_id__in=silabosemanalparcial.values_list('id'),
                            status=True).count()
                        totalaaplanificado += totalplanificadoaatar + totalplanificadoaafor
                        totalplanificadoaa = totalplanificadoaatar + totalplanificadoaafor
                        totalaaplanificadosinmigrar += totalplanificadoaasinmigrartar + totalplanificadoaasinmigrarfor

                        if totalplanificadoaa > totalminimoaa:
                            totalaamoodle += totalminimoaa
                        else:
                            totalaamoodle += totalplanificadoaa
                        if estadoparcial == 'CERRADO':
                            if totalplanificadoaa < totalminimoaa:
                                listamateriasfaltaaa.append(
                                    [lsilabo.id, lsilabo.materia, totalplanificadoaa, totalminimoaa])
                        totalapeplanificadosinmigrartar = 0
                        if lsilabo.materia.asignaturamalla.horasapeasistotal > 0:
                            if lsilabo.materia.modeloevaluativo.id != 25:
                                if listadocomponentes.filter(componente_id=2):
                                    totalminimoape = listadocomponentes.filter(componente_id=2)[0].cantidad * len(
                                        listaparcialterminadas)
                                    minimoape += totalminimoape
                                totalapeplanificadotar = TareaPracticaSilaboSemanal.objects.filter(
                                    silabosemanal_id__in=silabosemanalparcial.values_list('id'),
                                    idtareapracticamoodle__gt=0, status=True)
                                totalapeplanificadosinmigrartar = TareaPracticaSilaboSemanal.objects.filter(
                                    silabosemanal_id__in=silabosemanalparcial.values_list('id'), status=True).count()

                                totalapeplanificado += totalapeplanificadotar.count()
                                totalapeplanificadosinmigrar += totalapeplanificadosinmigrartar
                                # totalapeplanificadoape = totalapeplanificadotar.count()
                                totalapeplanificadoape = totalapeplanificadotar.values_list(
                                    'silabosemanal__parcial').distinct().count()
                                tieneape = 1
                                if totalapeplanificadoape > totalminimoape:
                                    totalapemoodle += totalminimoape
                                else:
                                    totalapemoodle += totalapeplanificadoape
                                if estadoparcial == 'CERRADO':
                                    if totalapeplanificadoape < totalminimoape:
                                        listamateriasfaltaape.append(
                                            [lsilabo.id, lsilabo.materia, totalapeplanificadoape, totalminimoape])
                    ##################################################

                    if iddiapositiva in listadolineamiento.values_list('tiporecurso', flat=True):
                        if periodorelacionado:
                            porcentajediapositivas = 0
                            if totaldiapositivasmoodle >= 1:
                                porcentajediapositivas = 100
                        else:
                            try:
                                porcentajediapositivas = round(
                                    ((100 * totaldiapositivasmoodle) / totaldiapositivaplanificada), 2)
                            except ZeroDivisionError:
                                porcentajediapositivas = 0
                    if idmateriales in listadolineamiento.values_list('tiporecurso', flat=True):
                        if periodorelacionado:
                            porcentajematerial = 0
                            if totalmaterialmoodle >= 1:
                                porcentajematerial = 100
                        else:
                            try:
                                porcentajematerial = round(((100 * totalmaterialmoodle) / totalmaterialplanificada), 2)
                            except ZeroDivisionError:
                                porcentajematerial = 0
                    listado.append([claseactividad, 'Sílabo', totalsilabos, totalsilabosplanificados, porcentaje, '',
                                    'ACTIVIDADES',
                                    listasilabofaltasilabo])
                    resultadominimoplanificar += totalsilabos
                    resultadoplanificados += totalsilabosplanificados
                    resultadoporcentajessyl += porcentaje
                    sumatoriaindicesyl += 1
                    ##################################################
                    if idcompendio in listadolineamiento.values_list('tiporecurso', flat=True):
                        if periodorelacionado:
                            porcentajecompendios = 0
                            if totalcompendiosmoodle >= 1:
                                porcentajecompendios = 100
                        else:
                            try:
                                porcentajecompendios = round(
                                    ((100 * totalcompendiosmoodle) / totalcompendioplanificada), 2)
                            except ZeroDivisionError:
                                porcentajecompendios = 0
                    if idvideomagistral in listadolineamiento.values_list('tiporecurso', flat=True):
                        if periodorelacionado:
                            porcentajevideo = 0
                            if totalvideomoodle >= 1:
                                porcentajevideo = 100
                        else:
                            try:
                                porcentajevideo = round(((100 * totalvideomoodle) / totalvideoplanificada), 2)
                            except ZeroDivisionError:
                                porcentajevideo = 0

                    if idguiaestudiante in listadolineamiento.values_list('tiporecurso', flat=True):
                        if periodorelacionado:
                            porcentajeguiaestudiante = 0
                            if totalguiaestmoodle >= 1:
                                porcentajeguiaestudiante = 100
                            else:
                                if totalguiaestplanificada == 0:
                                    porcentajeguiaestudiante = 100
                        else:
                            if totalguiaestplanificada == 0:
                                porcentajeguiaestudiante = 100
                            else:
                                try:
                                    porcentajeguiaestudiante = round(
                                        ((100 * totalguiaestmoodle) / totalguiaestplanificada), 2)
                                except ZeroDivisionError:
                                    porcentajeguiaestudiante = 0
                    try:
                        porcentajeacd = 0
                        if periodorelacionado:
                            if totalacdmoodle >= 1:
                                porcentajeacd = 100
                        else:
                            if totalacdmoodle > minimoacd:
                                porcentajeacd = 100
                            else:
                                porcentajeacd = round(((100 * totalacdmoodle) / minimoacd), 2)
                    except ZeroDivisionError:
                        porcentajeacd = 0
                    if porcentajeacd > 100:
                        porcentajeacd = 100
                    if estadoparcial == 'ABIERTO' and not nivelacion:
                        porcentajeacd = 100
                    try:
                        porcentajeaa = 0
                        if periodorelacionado:
                            if totalaamoodle >= 1:
                                porcentajeaa = 100
                        else:
                            if totalaamoodle > minimoaa:
                                porcentajeaa = 100
                            else:
                                porcentajeaa = round(((100 * totalaamoodle) / minimoaa), 2)
                    except ZeroDivisionError:
                        porcentajeaa = 0
                    if porcentajeaa > 100:
                        porcentajeaa = 100
                    if estadoparcial == 'ABIERTO':
                        porcentajeaa = 100

                    if tieneape == 1:
                        try:
                            porcentajeape = 0
                            if periodorelacionado:
                                if totalapemoodle >= 1:
                                    porcentajeape = 100
                            else:
                                if totalapemoodle > minimoape:
                                    porcentajeape = 100
                                else:
                                    porcentajeape = round(((100 * totalapemoodle) / minimoape), 2)
                        except ZeroDivisionError:
                            porcentajeape = 0
                        if porcentajeape > 100:
                            porcentajeape = 100
                        if estadoparcial == 'ABIERTO':
                            porcentajeape = 100

                    ###########################################

                    if iddiapositiva in listadolineamiento.values_list('tiporecurso', flat=True):
                        listado.append([claseactividad, 'Presentación (Diapositivas)', totaldiapositivaplanificada,
                                        totaldiapositivasmoodle, porcentajediapositivas, '', 'ACTIVIDADES',
                                        listamateriasfaltadiapositiva])
                        resultadominimoplanificar += totaldiapositivaplanificada
                        resultadoplanificados += totaldiapositivasmoodle
                        resultadoporcentajessyl += porcentajediapositivas
                        sumatoriaindicesyl += 1
                    if idmateriales in listadolineamiento.values_list('tiporecurso', flat=True):
                        listado.append(
                            [claseactividad, 'Material Complementario', totalmaterialplanificada, totalmaterialmoodle,
                             porcentajematerial, '', 'ACTIVIDADES', listamateriasfaltamaterial])
                        resultadominimoplanificar += totalmaterialplanificada
                        resultadoplanificados += totalmaterialmoodle
                        resultadoporcentajessyl += porcentajematerial
                        sumatoriaindicesyl += 1

                    ############################################
                    if idcompendio in listadolineamiento.values_list('tiporecurso', flat=True):
                        listado.append([claseactividad, 'COMPENDIO', totalcompendioplanificada, totalcompendiosmoodle,
                                        porcentajecompendios, 0, 'ACTIVIDADES', listamateriasfaltacompendio, porcentajecompendios,
                                        idcompendio, False])
                        resultadominimoplanificar += totalcompendioplanificada
                        resultadoplanificados += totalcompendiosmoodle
                        resultadoporcentajes += porcentajecompendios
                        sumatoriaindice += 1
                    if idvideomagistral in listadolineamiento.values_list('tiporecurso', flat=True):
                        listado.append([claseactividad, 'VIDEOS MAGISTRALES', totalvideoplanificada, totalvideomoodle,
                                        porcentajevideo, 0, 'ACTIVIDADES', listamateriasfaltavideo, porcentajevideo,
                                        idvideomagistral, False])
                        resultadominimoplanificar += totalvideoplanificada
                        resultadoplanificados += totalvideomoodle
                        resultadoporcentajes += porcentajevideo
                        sumatoriaindice += 1
                    if idguiaestudiante in listadolineamiento.values_list('tiporecurso', flat=True):
                        listado.append(
                            [claseactividad, 'GUÍA DEL ESTUDIANTE', totalguiaestplanificada, totalguiaestmoodle,
                             porcentajeguiaestudiante, 0, 'ACTIVIDADES', listamateriasfaltaguias, porcentajeguiaestudiante,
                             idguiaestudiante, False])
                        resultadominimoplanificar += totalguiaestplanificada
                        resultadoplanificados += totalguiaestmoodle
                        resultadoporcentajes += porcentajeguiaestudiante
                        sumatoriaindice += 1
                    if bandera != 1:
                        listado.append([claseactividad, 'ACD', minimoacd, totalacdplanificado,
                                        '-' if subtipo_docentes == 1 and nivelacion else estadoparcial, porcentajeacd,
                                        2,
                                        listamateriasfaltaacd, porcentajeacd, 8, subtipo_docentes == 1 and nivelacion,
                                        totalacdplanificadosinmigrar])
                    sumatoriaindice += 1
                    if (subtipo_docentes == 1 and not nivelacion) or (subtipo_docentes == 2 and nivelacion):
                        if bandera != 1:
                            listado.append(
                                [claseactividad, 'AA', minimoaa, totalaaplanificado, estadoparcial, porcentajeaa, 2,
                                 listamateriasfaltaaa, porcentajeaa, 9, False, totalaaplanificadosinmigrar])
                        sumatoriaindice += 1
                    if tieneape == 1:
                        if bandera == 1:
                            listado.append(
                                [claseactividad, 'APE', minimoape, totalapeplanificado, estadoparcial, porcentajeape, 2,
                                 listamateriasfaltaape, porcentajeape, 10, False, totalapeplanificadosinmigrar])
                        sumatoriaindice += 1
                    resultadominimoplanificar += minimoacd
                    resultadominimoplanificar += minimoaa
                    if tieneape == 1:
                        resultadominimoplanificar += minimoape
                    resultadoplanificados += totalacdplanificado
                    resultadoplanificados += totalaaplanificado
                    if tieneape == 1:
                        resultadoplanificados += totalapeplanificado
                    resultadoporcentajes += porcentajeacd
                    if (subtipo_docentes == 1 and not nivelacion) or (subtipo_docentes == 2 and nivelacion):
                        resultadoporcentajes += porcentajeaa
                    if tieneape == 1:
                        resultadoporcentajes += porcentajeape
                    subtipo_docentes -= 1
        try:
            resultadoporcentajes = round(((resultadoporcentajes) / sumatoriaindice), 2)
            resultadoporcentajessyl = round(((resultadoporcentajessyl) / sumatoriaindicesyl), 2)
            resultadototal = round(((resultadoporcentajes + resultadoporcentajessyl) / 2), 2)
            resultadosobre40 = round(((resultadototal * 40) / 100), 2)
        except ZeroDivisionError:
            resultadoporcentajes = 0
            resultadoporcentajessyl = 0
            resultadototal = 0
        listado.append(
            [claseactividad, resultadominimoplanificar, resultadoplanificados, resultadoporcentajes, len(result), 0, 4,
             [], resultadosobre40, resultadototal])
        return listado
    except Exception as e:
        import sys
        print(e)
        print('Error on line {} - {}'.format(sys.exc_info()[-1].tb_lineno, e))


@register.simple_tag
def actividadmacroactividades(self):
    try:
        from sga.pro_cronograma import CRITERIO_DIRECTOR_PROYECTO, CRITERIO_ASOCIADO_PROYECTO, CRITERIO_CODIRECTOR_PROYECTO_INV, CRITERIO_DIRECTOR_GRUPOINVESTIGACION, CRITERIO_INTEGRANTE_GRUPOINVESTIGACION
        from inno.models import ActividadDocentePeriodo, SubactividadDetalleDistributivo

        data = {}
        EXCLUIR_PROYECTOS_INVESTIGACION = variable_valor('EXCLUIR_PROYECTOS_INVESTIGACION')
        if actividad := self.actividaddetalledistributivo_set.filter(status=True, vigente=True).first():
            _exclude = Q()
            persona = actividad.criterio.distributivo.profesor.persona
            tipointegranteproyecto = persona.proyectoinvestigacionintegrante_set.values_list('funcion', flat=True).filter(tiporegistro__in=[1, 3, 4], proyecto__estado_id=37, status=True).exclude(proyecto__in=EXCLUIR_PROYECTOS_INVESTIGACION)
            if not 1 in tipointegranteproyecto:
                _exclude |= Q(subactividaddocenteperiodo__criterio=CRITERIO_DIRECTOR_PROYECTO)
            if not 2 in tipointegranteproyecto:
                _exclude |= Q(subactividaddocenteperiodo__criterio=CRITERIO_CODIRECTOR_PROYECTO_INV)
            if not 3 in tipointegranteproyecto:
                _exclude |= Q(subactividaddocenteperiodo__criterio=CRITERIO_ASOCIADO_PROYECTO)

            tipointegrantegrupo = persona.grupoinvestigacionintegrante_set.values_list('funcion', flat=True).filter(grupo__vigente=True, grupo__status=True, status=True)
            if not 1 in tipointegrantegrupo:
                _exclude |= Q(subactividaddocenteperiodo__criterio=CRITERIO_DIRECTOR_GRUPOINVESTIGACION)
            if not 2 in tipointegrantegrupo and not 3 in tipointegrantegrupo:
                _exclude |= Q(subactividaddocenteperiodo__criterio=CRITERIO_INTEGRANTE_GRUPOINVESTIGACION)

            data['subactividades'] = subactividades = SubactividadDetalleDistributivo.objects.filter(actividaddetalledistributivo=actividad, subactividaddocenteperiodo__criterio__status=True, status=True).exclude(_exclude).order_by('subactividaddocenteperiodo__criterio__nombre')
            data['actividades'] = ActividadDocentePeriodo.objects.filter(pk__in=subactividades.values_list('subactividaddocenteperiodo__actividad', flat=True), criterio__status=True).order_by('criterio__nombre')

        return data
    except Exception as ex:
        pass

@register.simple_tag
def get_actividades_actividad_macro(self, tipoevidencia=None):
    try:
        from inno.models import SubactividadDocentePeriodo

        filtro = Q(criterio__status=True, status=True)
        if tipoevidencia:
            queryset = SubactividadDocentePeriodo.objects.filter(tipoevidencia=tipoevidencia, criterio__status=True, status=True).values_list('actividad', flat=True).distinct()
            filtro &= Q(id__in=queryset)
        return self.actividaddocenteperiodo_set.filter(filtro).order_by('criterio__nombre')
    except Exception as ex:
        pass

@register.simple_tag
def listado_bitacora_docente(obj, criterio, fechafin, esautomatico=False):
    import calendar
    from dateutil.rrule import MONTHLY, rrule
    from django.db.models import Sum, F, ExpressionWrapper, TimeField
    from investigacion.models import BitacoraActividadDocente
    from sga.pro_cronograma import CRITERIO_ELABORA_ARTICULO_CIENTIFICO

    try:
        periodo = criterio.distributivo.periodo
        profesor = criterio.distributivo.profesor
        es_actividad_macro = criterio.es_actividadmacro()

        _get_horas_minutos = lambda th: (th.total_seconds() / 3600).__str__().split('.')

        data, listabitacoras, porcentajetotal = {}, [], 0
        claseactividad = criterio.claseactividad_set.filter(status=True).order_by('inicio', 'dia', 'turno__comienza')

        inicio, fin = periodo.inicio, periodo.fin
        if not es_actividad_macro:
            if actividad := criterio.actividaddetalledistributivo_set.filter(vigente=True, status=True).first():
                inicio, fin = actividad.desde, actividad.hasta
        else:
            inicio, fin = obj.fechainicio, obj.fechafin

        # Ajuste de fechas por si el inicio y fin de la actividad esta fuera del periodo académico
        if inicio < periodo.inicio:
            inicio = periodo.inicio

        if fin > periodo.fin:
            fin = periodo.fin
        # ----------------------------------------------------------------------------------------
        dt, end, step = date(fechafin.year, fechafin.month, 1), fechafin, timedelta(days=1)
        _result, total_ejecutada = [], 0
        while dt <= end:
            if inicio <= dt <= fin:
                exclude = 0
                if not criterio.distributivo.periodo.diasnolaborable_set.values('id').filter(status=True, fecha=dt, activo=True).exclude(motivo=exclude):
                    _result += [dt.strftime('%Y-%m-%d') for dclase in claseactividad.values_list('dia', 'turno_id') if dt.isocalendar()[2] == dclase[0]]

            dt += step

        filtro = Q(criterio=criterio) if not obj else Q(subactividad=obj)
        listabitacorasperiodo = BitacoraActividadDocente.objects.filter(Q(profesor=profesor, status=True) & filtro).filter(detallebitacoradocente__status=True).order_by('fechafin').distinct()

        for fecha in list(rrule(MONTHLY, dtstart=inicio, until=fin)):
            if fecha.date() > fechafin:
                break
            total_planificadas, total_registradas, total_aprobadas, porcentaje_cumplimiento = 0, 0, 0, 0
            if bitacora := listabitacorasperiodo.filter(fechaini__month=fecha.month, fechafin__year=fecha.year).first():
                fi, ff = date(bitacora.fechafin.year, bitacora.fechafin.month, 1), bitacora.fechafin
                detallebitacora = bitacora.detallebitacoradocente_set.filter(bitacoradocente=bitacora, fecha__lte=ff, fecha__gte=fi, status=True).annotate(diferencia=ExpressionWrapper(F('horafin') - F('horainicio'), output_field=TimeField())).order_by('fecha', 'horainicio', 'horafin')
                if th := detallebitacora.aggregate(total=Sum('diferencia'))['total']:
                    horas, minutos = _get_horas_minutos(th)
                    total_registradas = float("%s.%s" % (horas, round(float('0.' + minutos) * 60)))

                if th := detallebitacora.filter(estadoaprobacion=2).aggregate(total=Sum('diferencia'))['total']:
                    horas, minutos = _get_horas_minutos(th)
                    total_aprobadas = float("%s.%s" % (horas, round(float('0.' + minutos) * 60)))

                if not obj:
                    if total_planificadas := bitacora.get_horasplanificadas():
                        if bitacora.estadorevision == 3:
                            porcentaje_cumplimiento = 100 if (total_aprobadas > total_planificadas) else round((total_aprobadas / total_planificadas) * 100, 2)
                        else:
                            porcentaje_cumplimiento = 100 if (total_registradas > total_planificadas) else round((total_registradas / total_planificadas) * 100, 2)
                    else:
                        if total_registradas:
                            porcentaje_cumplimiento = 100
                else:
                    if total_registradas:
                        if bitacora.fechafin.month == fechafin.month and bitacora.fechafin.year == fechafin.year:
                            porcentaje_cumplimiento = 100
                        elif total_aprobadas:
                            porcentaje_cumplimiento = round((total_registradas / total_aprobadas) * 100, 2)

                if not bitacora.estadorevision == 3:
                    total_aprobadas = '-'
            else:
                lastday = calendar.monthrange(fecha.year, fecha.month)[1]
                bitacora = {
                    'fechaini': date(fecha.year, fecha.month, 1),
                    'fechafin': date(fecha.year, fecha.month, lastday),
                }

            if obj and obj.subactividaddocenteperiodo.criterio.pk == CRITERIO_ELABORA_ARTICULO_CIENTIFICO:
                porcentaje_cumplimiento = 100

            listabitacoras.append([bitacora, total_planificadas, total_registradas, total_aprobadas, porcentaje_cumplimiento])

        if listabitacoras:
            porcentajetotal = sum([l[4] for l in listabitacoras]) / len(listabitacoras)
            total_ejecutada = listabitacoras[-1][3]

        if obj and not obj.subactividaddocenteperiodo.validacion:
            porcentajetotal = 100

        listado = None
        if esautomatico:
            totalmensual = _result.__len__()
            promedio = porcentajetotal if porcentajetotal <= 100 else 100
            listado = [totalmensual, promedio]
        else:
            listado = {'listabitacoras': listabitacoras, 'claseactividad': claseactividad, 'porcentajetotal': porcentajetotal if porcentajetotal <= 100 else 100, 'planificadas_mes': _result.__len__(), 'total_ejecutada':total_ejecutada}
        return listado
    except Exception as ex:
        pass

@register.simple_tag
def actividad_produccion_cientifica(self, finicio, ffin, esautomatico=False):
    try:
        # self es un objeto DetalleDistributivo
        import calendar
        from dateutil.rrule import rrule, MONTHLY
        from sga.models import PlanificarPonencias
        from sga.funciones import mesesmenoresandias
        from inno.models import ActividadDocentePeriodo, SubactividadDocentePeriodo, Criterio
        from sga.pro_cronograma import CRITERIO_ELABORA_ARTICULO_CIENTIFICO, CRITERIO_DIRECTOR_PROYECTO, CRITERIO_CODIRECTOR_PROYECTO_INV, CRITERIO_ASOCIADO_PROYECTO, CRITERIO_DIRECTOR_GRUPOINVESTIGACION, CRITERIO_INTEGRANTE_GRUPOINVESTIGACION, CRITERIO_PONENCIAS

        data, data2 = {}, []
        mensajecargaobligatoria = False
        periodo = self.distributivo.periodo
        profesor = self.distributivo.profesor
        persona = self.distributivo.profesor.persona
        EXCLUIR_PROYECTOS_INVESTIGACION = variable_valor('EXCLUIR_PROYECTOS_INVESTIGACION')
        claseactividad = self.claseactividad_set.filter(actividaddetallehorario__vigente=True, status=True).order_by('inicio', 'dia', 'turno__comienza')
        dt, end, step = date(ffin.year, ffin.month, 1), ffin, timedelta(days=1)
        _result, total_ejecutada = [], 0
        while dt <= end:
            exclude = 0
            if not self.distributivo.periodo.diasnolaborable_set.values('id').filter(status=True, fecha=dt, activo=True).exclude(motivo=exclude):
                _result += [dt.strftime('%Y-%m-%d') for dclase in claseactividad.values_list('dia', 'turno_id') if dt.isocalendar()[2] == dclase[0]]
            dt += step

        lporcentajefinal, porcentajefinal = [], 0
        if actividades := self.actividaddetalledistributivo_set.filter(vigente=True, status=True):
            if actividades.__len__() == 1:
                actividad = actividades[0]
                # Mostrar las actividades obligatorias en el informe siempre y cuando formen parte de un proyecto o grupo
                _included = []
                if self.criterioinvestigacionperiodo:
                    tipointegranteproyecto = ProyectoInvestigacionIntegrante.objects.values_list('funcion', flat=True).filter(tiporegistro__in=[1, 3, 4], persona=persona, proyecto__estado_id=37, status=True).exclude(proyecto__in=EXCLUIR_PROYECTOS_INVESTIGACION)
                    if 1 in tipointegranteproyecto:
                        _included.append(CRITERIO_DIRECTOR_PROYECTO)
                    if 2 in tipointegranteproyecto:
                        _included.append(CRITERIO_CODIRECTOR_PROYECTO_INV)
                    if 3 in tipointegranteproyecto:
                        _included.append(CRITERIO_ASOCIADO_PROYECTO)

                    tipointegrantegrupo = GrupoInvestigacionIntegrante.objects.values_list('funcion', flat=True).filter(persona=persona, grupo__vigente=True, grupo__status=True, status=True)
                    if 1 in tipointegrantegrupo:
                        _included.append(CRITERIO_DIRECTOR_GRUPOINVESTIGACION)
                    if 2 in tipointegrantegrupo and 3 not in tipointegrantegrupo:
                        _included.append(CRITERIO_INTEGRANTE_GRUPOINVESTIGACION)

                    if _included.__len__():
                        mensajecargaobligatoria = True

                    #if profesor.dedicacion.pk == 1 and profesor.nivelcategoria.pk in (1, 2):
                    _included.append(CRITERIO_ELABORA_ARTICULO_CIENTIFICO)

                    # if PlanificarPonencias.objects.filter(profesor=persona.profesor(), estado=3, fecha_inicio__gte=periodo.inicio, fecha_fin__lte=ffin, status=True).values('id').exists():
                    #     _included.append(CRITERIO_PONENCIAS)

                # Incluir todas de vinculacion
                if self.criteriodocenciaperiodo and self.criteriodocenciaperiodo.criterio.tipo == 2:
                    _included += list(Criterio.objects.filter(tipo=2, tipocriterio=4).values_list('id', flat=True))
                # --------------------------------------------------------------------------------------------

                _included += list(self.bitacoraactividaddocente_set.filter(fechafin__lte=ffin, detallebitacoradocente__status=True, status=True).values_list('subactividad__subactividaddocenteperiodo__criterio', flat=True).distinct())
                _included += list(self.evidenciaactividaddetalledistributivo_set.filter(hasta__lte=ffin, status=True).values_list('subactividad__subactividaddocenteperiodo__criterio', flat=True).distinct())

                subactividaddistributivo = actividad.subactividaddetalledistributivo_set.filter(subactividaddocenteperiodo__criterio__in=_included,
                                                                                                subactividaddocenteperiodo__actividad__criterio__status=True,
                                                                                                subactividaddocenteperiodo__actividad__status=True,
                                                                                                subactividaddocenteperiodo__criterio__status=True,
                                                                                                subactividaddocenteperiodo__status=True,
                                                                                                fechainicio__lte=ffin,
                                                                                                status=True)

                actividadperiodo = ActividadDocentePeriodo.objects.filter(id__in=subactividaddistributivo.values_list('subactividaddocenteperiodo__actividad', flat=True), status=True)
                for actividad in actividadperiodo:
                    subactividad = subactividaddistributivo.filter(subactividaddocenteperiodo__actividad=actividad, status=True)
                    for sa in subactividad:
                        if sa.subactividaddocenteperiodo.tipoevidencia == 1:
                            if t := sa.horarios_informesinvestigacion_profesor(self, finicio, ffin, esautomatico=True):
                                lporcentajefinal.append(float(t[1]))
                        if sa.subactividaddocenteperiodo.tipoevidencia == 2:
                            if t := listado_bitacora_docente(sa, self, ffin, True):
                                if float(t[1]):
                                    lporcentajefinal.append(float(t[1]))

                    data2.append([actividad, subactividad])
            else:
                raise NameError('Error el su distributivo, usted cuenta con más de 1 actividad principal en vigencia.')

        try:
            porcentajefinal = (sum(lporcentajefinal) / len(lporcentajefinal))
        except Exception as ex:
            ...

        horasplanificadas = _result.__len__()
        porcentajefinal = "%.2f" % porcentajefinal if porcentajefinal <= 100 else "100.00"

        data['data2'] = data2
        data['claseactividad'] = claseactividad
        data['porcentajefinal'] = porcentajefinal
        data['horasplanificadas'] = horasplanificadas
        data['mensajecargaobligatoria'] = mensajecargaobligatoria

        if esautomatico:
            return [horasplanificadas, porcentajefinal]

        return True, data
    except Exception as ex:
        return False, ex.__str__()

@register.simple_tag
def listado_colectivos_academicos(obj, criterio, fechainicio, fechafin, esautomatico=False):
    try:
        from sga.models import ClaseActividad, CapCabeceraSolicitudDocente, CapEventoPeriodoDocente
        from dateutil.relativedelta import relativedelta
        periodo, profesor = criterio.distributivo.periodo, criterio.distributivo.profesor
        now = datetime.now().date()

        claseactividad = ClaseActividad.objects.filter(detalledistributivo=criterio, detalledistributivo__distributivo__profesor=profesor, status=True).order_by('inicio', 'dia', 'turno__comienza')
        inicio, fin = fechainicio, fechafin
        if actividad := criterio.actividaddetalledistributivo_set.filter(vigente=True, status=True).first():
            if actividad.hasta < fechafin:
                fin = actividad.hasta

        dt, end, step = date(fechafin.year, fechafin.month, 1), fechafin, timedelta(days=1)
        _result, total_ejecutada = [], 0
        while dt <= end:
            if inicio <= dt <= fin:
                exclude = 0
                if not periodo.diasnolaborable_set.values('id').filter(status=True, fecha=dt, activo=True).exclude(motivo=exclude):
                    _result += [dt.strftime('%Y-%m-%d') for dclase in claseactividad.values_list('dia', 'turno_id') if dt.isocalendar()[2] == dclase[0]]

            dt += step

        __totalplanificadas, __porcentajegeneral, __miseventos = _result.__len__(), 0, []

        filtroa = Q(capeventoperiodo__status=True, capeventoperiodo__capevento__status=True, status=True, participante=profesor.persona)
        filtrob = Q(capeventoperiodo__fechafin__gte=fechainicio - relativedelta(months=1)) | Q(capeventoperiodo__fechafin__gte=fechainicio - relativedelta(months=1), capeventoperiodo__fechafin__lte=fechafin)

        existe_capacitacion = CapEventoPeriodoDocente.objects.filter(status=True, visualizar=True, fechainicio__gte=fechainicio - relativedelta(months=1), fechafin__lte=fechafin).values('id').exists()
        eventos = CapCabeceraSolicitudDocente.objects.select_related('capeventoperiodo').filter(filtroa & filtrob).order_by('-capeventoperiodo__fechafin').exclude(estadosolicitud=4)
        for e in eventos:
            __miseventos.append({'evento': e, 'porcentaje': 100, 'estado': 'EJECUTADO' if e.capeventoperiodo.fechafin <= fechafin else 'EN CURSO'})

        if count := __miseventos.__len__():
            __porcentajegeneral = sum([x['porcentaje'] for x in __miseventos]) / count

        __porcentajegeneral = __porcentajegeneral if __porcentajegeneral <= 100 else 100

        if esautomatico:
            totalmensual = __totalplanificadas
            promedio = __porcentajegeneral
            listado = [totalmensual, promedio] if existe_capacitacion else []
            return listado
        else:
            return {'planificadas': __totalplanificadas, 'data': __miseventos, 'porcentajegeneral': __porcentajegeneral, "claseactividad": claseactividad, 'existe_capacitacion': existe_capacitacion}
    except Exception as ex:
        pass

@register.simple_tag
def recursos_docente(obj, profesor, materia, fechaini, fechafin):
    try:
        from sga.models import DetalleDistributivo, GuiaEstudianteSilaboSemanal, TareaPracticaSilaboSemanal, \
            TipoProfesor, ProfesorMateria, ClaseActividad, Silabo, CompendioSilaboSemanal, VideoMagistralSilaboSemanal, \
            ForoSilaboSemanal, TareaSilaboSemanal, TestSilaboSemanalAdmision, TestSilaboSemanal, \
            DiapositivaSilaboSemanal, MaterialAdicionalSilaboSemanal, SilaboSemanal, EvaluacionAprendizajeSilaboSemanal
        from django.db.models import Exists, OuterRef
        ## RECURSOS ##
        cantidad_diapositivas = 0
        cantidad_diapositivas_moodle = 0
        total_diapositiva = 0
        porcentaje_diapositiva = 0

        cantidad_compendio = 0
        cantidad_compendio_moodle = 0
        total_compendio = 0
        porcentaje_compendio = 0

        cantidad_guia_estudiante = 0
        cantidad_guia_estudiante_moodle = 0
        total_guia_estudiante = 0
        porcentaje_guia_estudiante = 0

        cantidad_material = 0
        cantidad_material_moodle = 0
        total_material = 0
        porcentaje_material = 0

        total_ACD = 0
        ## ACD ##
        cantidad_test = 0
        cantidad_test_moodle = 0
        porcentaje_test = 0

        cantidad_taller = 0
        cantidad_taller_moodle = 0
        porcentaje_taller = 0

        cantidad_expo = 0
        cantidad_expo_moodle = 0
        porcentaje_expo = 0
        ## AA ##
        cantidad_foro = 0
        cantidad_foro_moodle = 0
        porcentaje_foro = 0

        cantidad_tarea = 0
        cantidad_tarea_moodle = 0
        porcentaje_tarea = 0

        cantidad_caso = 0
        cantidad_caso_moodle = 0
        porcentaje_caso = 0

        cantidad_inves = 0
        cantidad_inves_moodle = 0
        porcentaje_inves = 0
        ## APE ##
        cantidad_practicas = 0
        cantidad_practicas_moodle = 0
        porcentaje_practicas = 0

        listado = []
        if silabocab := Silabo.objects.select_related('materia').filter(status=True, materia_id=materia.pk).first():
            fechaactual = datetime.now().date()
            diferencia = fechaactual - fechaini
            num_semanas = (diferencia.days // 7) + 1
            silabosemanal = silabocab.silabosemanal_set.filter(status=True). \
                annotate(tieneactividadplanificada=Exists(
                EvaluacionAprendizajeSilaboSemanal.objects.filter(silabosemanal__silabo_id=silabocab.id,
                                                                  tipoactividadsemanal=1, silabosemanal_id=OuterRef('id'),
                                                                  status=True, silabosemanal__status=True)))
            try:
                semanas = silabosemanal[:num_semanas-1]
            except Exception as ex:
                if silabosemanal.count() > 0:
                    semanas = silabosemanal[:0]

            tiene_horas_ape = False
            if silabocab.materia.asignaturamalla.horasapesemanal > 0:
                tiene_horas_ape = True


            for semana in semanas:
                ## RECURSOS ##
                cantidad_diapositivas += semana.diapositivasilabosemanal_set.filter(status=True).count()
                cantidad_diapositivas_moodle += semana.diapositivasilabosemanal_set.filter(Q(status=True) & (Q(estado=4) | Q(migrado=True))).count()
                cantidad_compendio += semana.compendiosilabosemanal_set.filter(status=True).count()
                cantidad_compendio_moodle += semana.compendiosilabosemanal_set.filter(Q(status=True) & (Q(estado=4) | Q(migrado=True))).count()
                if semana.guiaestudiantesilabosemanal_set.filter(status=True):
                    cantidad_guia_estudiante += semana.guiaestudiantesilabosemanal_set.filter(status=True).count()
                    cantidad_guia_estudiante_moodle += semana.guiaestudiantesilabosemanal_set.filter(Q(status=True) & (Q(estado=4) | Q(migrado=True))).count()
                cantidad_material += semana.materialadicionalsilabosemanal_set.filter(status=True).count()
                cantidad_material_moodle += semana.materialadicionalsilabosemanal_set.filter(Q(status=True) & (Q(estado=4) | Q(migrado=True))).count()
                ## ACD ##
                cantidad_test += semana.testsilabosemanal_set.filter(status=True).count()
                cantidad_test_moodle += semana.testsilabosemanal_set.filter(Q(status=True) & (Q(estado=4) | Q(migrado=True))).count()
                if semana.tareasilabosemanal_set.filter(actividad_id=3, status=True):
                    cantidad_taller += semana.tareasilabosemanal_set.filter(actividad_id=3, status=True).count()
                    cantidad_taller_moodle += semana.tareasilabosemanal_set.filter((Q(actividad_id=3) & Q(status=True)) & (Q(estado=4) | Q(migrado=True))).count()
                if semana.tareasilabosemanal_set.filter(actividad_id=2, status=True):
                    cantidad_expo += semana.tareasilabosemanal_set.filter(actividad_id=2, status=True).count()
                    cantidad_expo_moodle += semana.tareasilabosemanal_set.filter((Q(actividad_id=2) & Q(status=True)) & (Q(estado=4) | Q(migrado=True))).count()
                ## AA ##
                if semana.forosilabosemanal_set.filter(status=True):
                    cantidad_foro += semana.forosilabosemanal_set.filter(status=True).count()
                    cantidad_foro_moodle += semana.forosilabosemanal_set.filter(Q(status=True) & (Q(estado=4) | Q(migrado=True))).count()
                if semana.tareasilabosemanal_set.filter(actividad_id=5, status=True):
                    cantidad_tarea += semana.tareasilabosemanal_set.filter(actividad_id=5, status=True).count()
                    cantidad_tarea_moodle += semana.tareasilabosemanal_set.filter((Q(actividad_id=5) & Q(status=True)) & (Q(estado=4) | Q(migrado=True))).count()
                if semana.tareasilabosemanal_set.filter(actividad_id=8, status=True):
                    cantidad_caso += semana.tareasilabosemanal_set.filter(actividad_id=8, status=True).count()
                    cantidad_caso_moodle += semana.tareasilabosemanal_set.filter((Q(actividad_id=8) & Q(status=True)) & (Q(estado=4) | Q(migrado=True))).count()
                if semana.tareasilabosemanal_set.filter(actividad_id=7, status=True):
                    cantidad_inves += semana.tareasilabosemanal_set.filter(actividad_id=7, status=True).count()
                    cantidad_inves_moodle += semana.tareasilabosemanal_set.filter((Q(actividad_id=7) & Q(status=True)) & (Q(estado=4) | Q(migrado=True))).count()
                ## APE ##
                if tiene_horas_ape:
                    if semana.tareapracticasilabosemanal_set.filter(status=True):
                        cantidad_practicas += semana.tareapracticasilabosemanal_set.filter(status=True).count()
                        cantidad_practicas_moodle += semana.tareapracticasilabosemanal_set.filter(Q(status=True) & (Q(estado=4) | Q(idtareapracticamoodle__gt=0)) ).count()

            cont = 0
            cont_recursos = 0
            cont_ACD = 0
            cont_AA = 0
            cont_APE = 0
            tiene_recursos = False
            tiene_ACD = False
            tiene_AA = False
            tiene_APE = False
            porcentaje_total_recursos = 0
            porcentaje_total_ACD = 0
            porcentaje_total_AA = 0
            porcentaje_total_APE = 0
            ## RECURSOS
            if cantidad_diapositivas > 0:
                tiene_recursos = True
                porcentaje_diapositiva = round((cantidad_diapositivas_moodle/cantidad_diapositivas)*100,2)
                cont_recursos += 1
                listado.append(['DIAPOSITIVAS', cantidad_diapositivas, cantidad_diapositivas_moodle, porcentaje_diapositiva, 1])
            if cantidad_compendio > 0:
                tiene_recursos = True
                porcentaje_compendio = round((cantidad_compendio_moodle / cantidad_compendio) * 100, 2)
                cont_recursos += 1
                listado.append(['COMPENDIO', cantidad_compendio, cantidad_compendio_moodle, porcentaje_compendio, 1])
            if cantidad_guia_estudiante > 0:
                tiene_recursos = True
                porcentaje_guia_estudiante = round((cantidad_guia_estudiante_moodle / cantidad_guia_estudiante) * 100, 2)
                cont_recursos += 1
                listado.append(['GUIA DEL ESTUDIANTE', cantidad_guia_estudiante, cantidad_guia_estudiante_moodle, porcentaje_guia_estudiante, 1])
            if cantidad_material > 0:
                tiene_recursos = True
                porcentaje_material = round((cantidad_material_moodle / cantidad_material) * 100, 2)
                cont_recursos += 1
                listado.append(['MATERIAL COMPLEMENTARIO', cantidad_material, cantidad_material_moodle, porcentaje_material, 1])
            if tiene_recursos:
                # listado = [['RECURSOS', '', '', '', 'TITULO']] + listado
                # listado.append(['RECURSOS', '', '', '', 'TITULO'])
                listado.insert(0, ['RECURSOS', '', '', '', 'TITULO'])
                cont += 1
                porcentaje_total_recursos = (porcentaje_diapositiva + porcentaje_compendio + porcentaje_guia_estudiante + porcentaje_material)/cont_recursos

            ## ACD
            if cantidad_test > 0:
                tiene_ACD = True
                porcentaje_test = round((cantidad_test_moodle / cantidad_test) * 100, 2)
                cont_ACD += 1
                listado.append(['TEST', cantidad_test, cantidad_test_moodle, porcentaje_test, 2])
            if cantidad_taller > 0:
                tiene_ACD = True
                porcentaje_taller = round((cantidad_taller_moodle / cantidad_taller) * 100, 2)
                cont_ACD += 1
                listado.append(['TALLER', cantidad_taller, cantidad_taller_moodle, porcentaje_taller, 2])
            if cantidad_expo > 0:
                tiene_ACD = True
                porcentaje_expo = round((cantidad_expo_moodle / cantidad_expo) * 100, 2)
                cont_ACD += 1
                listado.append(['EXPOSICION', cantidad_expo, cantidad_expo_moodle, porcentaje_expo, 2])
            if tiene_ACD:
                # listado.append(['ACD', '', '', '', 'TITULO'])
                # listado = [['ACD', '', '', '', 'TITULO']] + listado
                listado.insert(len(listado)-cont_ACD, ['ACD', '', '', '', 'TITULO'])
                cont += 1
                porcentaje_total_ACD = (porcentaje_test + porcentaje_taller + porcentaje_expo) / cont_ACD

            ## AA
            if cantidad_foro > 0:
                tiene_AA = True
                porcentaje_foro = round((cantidad_foro_moodle / cantidad_foro) * 100, 2)
                cont_AA += 1
                listado.append(['FORO', cantidad_foro, cantidad_foro_moodle, porcentaje_foro, 3])
            if cantidad_tarea > 0:
                tiene_AA = True
                porcentaje_tarea = round((cantidad_tarea_moodle / cantidad_tarea) * 100, 2)
                cont_AA += 1
                listado.append(['TAREA', cantidad_tarea, cantidad_tarea_moodle, porcentaje_tarea, 3])
            if cantidad_caso > 0:
                tiene_AA = True
                porcentaje_caso = round((cantidad_caso_moodle / cantidad_caso) * 100, 2)
                cont_AA += 1
                listado.append(['ANALISIS DE CASO', cantidad_caso, cantidad_caso_moodle, porcentaje_caso, 3])
            if cantidad_inves > 0:
                tiene_AA = True
                porcentaje_inves = round((cantidad_inves_moodle / cantidad_inves) * 100, 2)
                cont_AA += 1
                listado.append(['TRABAJO DE INVESTIGACION', cantidad_inves, cantidad_inves_moodle, porcentaje_inves, 3])
            if tiene_AA:
                # listado.append(['AA', '', '', '', 'TITULO'])
                # listado = [['AA', '', '', '', 'TITULO']] + listado
                listado.insert(len(listado)-cont_AA, ['AA', '', '', '', 'TITULO'])
                cont += 1
                porcentaje_total_AA = (porcentaje_foro + porcentaje_tarea + porcentaje_caso + porcentaje_inves)/cont_AA

            ## APE
            if cantidad_practicas > 0:
                tiene_APE = True
                porcentaje_practicas = round((cantidad_practicas_moodle / cantidad_practicas) * 100, 2)
                cont_APE += 1
                listado.append(['PRACTICAS', cantidad_practicas, cantidad_practicas_moodle, porcentaje_practicas, 4])
            if tiene_APE:
                # listado.append(['APE', '', '', '', 'TITULO'])
                # listado = [['APE', '', '', '', 'TITULO']] + listado
                listado.insert(len(listado)-cont_APE, ['APE', '', '', '', 'TITULO'])
                cont += 1
                porcentaje_total_APE = porcentaje_practicas / cont_APE

            try:
                if materia.modeloevaluativo.id != 66:
                    resultadoporcentajes = round(((porcentaje_total_recursos+porcentaje_total_ACD+porcentaje_total_AA+ porcentaje_total_APE) / cont), 2)
                else:
                    resultadoporcentajes = 100
                resultadoporcentajes_sobre_40 = round(((resultadoporcentajes*40) / 100), 2)
            except ZeroDivisionError:
                resultadoporcentajes = 0
                resultadoporcentajes_sobre_40 = 0

            listado.append([resultadoporcentajes, resultadoporcentajes_sobre_40, '', '', 'TOTAL'])

        return listado
    except Exception as e:
        import sys
        print(e)
        print('Error on line {} - {}'.format(sys.exc_info()[-1].tb_lineno, e))

@register.simple_tag
def temasimpartidos(obj, idmateria, periodo):
    from sga.models import Silabo, TemaAsistencia, SubTemaAsistencia, SubTemaAdicionalAsistencia, DiasNoLaborable, DetalleSilaboSemanalSubtema,SolicitudAperturaClase
    from django.db import connections
    from django.core.cache import cache
    try:
        # cache_key = f'silabo_data_temasimpartidos_{idmateria}'
        # cached_data = cache.get(cache_key)
        #
        # if cached_data:
        #     return cached_data
        listado = []
        cont = 0
        porcentajecumplimiento = 0
        porcentajetotal = 0
        fechaactual = datetime.now().date()
        no_empieza = False
        if silabos := Silabo.objects.filter(status=True, materia_id=idmateria).first():
            numeros_semana = [fecha.isocalendar()[1] for fecha in periodo.diasnolaborable_set.filter(status=True).values_list('fecha', flat=True)]
            num_sem_dia_no_laborable = list(dict.fromkeys(numeros_semana))
            silabosemanal = silabos.silabosemanal_set.filter(status=True).order_by('numsemana')
            if silabosemanal:
                cursor = connections['sga_select'].cursor()
                for silsem in silabosemanal:
                    # unidadsilsem = silsem.temas_seleccionados_planclase()
                    sql_tema = f"""SELECT "sga_detallesilabosemanaltema"."id", "sga_temaunidadresultadoprogramaanalitico"."descripcion", "sga_detallesilabosemanaltema"."temaunidadresultadoprogramaanalitico_id" FROM "sga_detallesilabosemanaltema" INNER JOIN "sga_temaunidadresultadoprogramaanalitico" ON ("sga_detallesilabosemanaltema"."temaunidadresultadoprogramaanalitico_id" = "sga_temaunidadresultadoprogramaanalitico"."id") WHERE ("sga_detallesilabosemanaltema"."silabosemanal_id" = {silsem.pk} AND "sga_temaunidadresultadoprogramaanalitico"."status" AND "sga_detallesilabosemanaltema"."status") ORDER BY "sga_temaunidadresultadoprogramaanalitico"."orden" ASC"""
                    cursor.execute(sql_tema)
                    unidadsilsem = cursor.fetchall()
                    # unidadsilsem = list(silsem.detallesilabosemanaltema_set.select_related('temaunidadresultadoprogramaanalitico').values_list('id','temaunidadresultadoprogramaanalitico__descripcion','temaunidadresultadoprogramaanalitico').filter(temaunidadresultadoprogramaanalitico__status=True).order_by('temaunidadresultadoprogramaanalitico__orden'))
                    fechainicio = silsem.fechainiciosemana
                    fechafin = silsem.fechafinciosemana
                    if fechainicio > fechaactual:
                        no_empieza = True
                        break
                    listado.append([silsem.numsemana, silsem.fechainiciosemana, silsem.fechafinciosemana, '', 'fechas'])
                    num_semana_fechainiciosilabo = fechainicio.isocalendar()[1]
                    if (num_semana_fechainiciosilabo in num_sem_dia_no_laborable):
                        fechafin += timedelta(weeks=2)
                    else:
                        fechafin += timedelta(weeks=1)
                    if unidadsilsem:
                        for tema in unidadsilsem:
                            if (fechafin <= fechaactual) or (TemaAsistencia.objects.values('id').filter(fecha__lte=fechafin, tema=tema[0]).exists()):
                                cont += 1
                                # if TemaAsistencia.objects.values('id').filter(fecha__lte=fechafin, tema=tema[0]).exists() or (num_semana_fechainiciosilabo in num_sem_dia_no_laborable):
                                if (TemaAsistencia.objects.values('id').filter(fecha__lte=fechafin, tema=tema[0]).exists()) or (TemaAsistencia.objects.values('id').filter(leccion__solicitada = True, tema=tema[0]).exists()):
                                    porcentajecumplimiento += 1
                                    listado.append(
                                        ['', '', '', tema[1], 'temas', 1])
                                else:
                                    listado.append(
                                        ['', '', '', tema[1], 'temas', 0])
                            else:
                                listado.append(
                                    ['', '', '', tema[1], 'temas', '-'])
                            subtemas = DetalleSilaboSemanalSubtema.objects.select_related('subtemaunidadresultadoprogramaanalitico').values_list('id','subtemaunidadresultadoprogramaanalitico__descripcion').filter(status=True,subtemaunidadresultadoprogramaanalitico__temaunidadresultadoprogramaanalitico=tema[2], subtemaunidadresultadoprogramaanalitico__status=True, subtemaunidadresultadoprogramaanalitico__temaunidadresultadoprogramaanalitico__isnull=False,subtemaunidadresultadoprogramaanalitico__temaunidadresultadoprogramaanalitico__status=True,silabosemanal=silsem).order_by('subtemaunidadresultadoprogramaanalitico__orden')
                            sql_subtemas = f"""SELECT "sga_detallesilabosemanalsubtema"."id", "sga_subtemaunidadresultadoprogramaanalitico"."descripcion" FROM "sga_detallesilabosemanalsubtema" INNER JOIN "sga_subtemaunidadresultadoprogramaanalitico" ON ("sga_detallesilabosemanalsubtema"."subtemaunidadresultadoprogramaanalitico_id" = "sga_subtemaunidadresultadoprogramaanalitico"."id") INNER JOIN "sga_temaunidadresultadoprogramaanalitico" ON ("sga_subtemaunidadresultadoprogramaanalitico"."temaunidadresultadoprogramaanalitico_id" = "sga_temaunidadresultadoprogramaanalitico"."id") WHERE ("sga_detallesilabosemanalsubtema"."silabosemanal_id" = {silsem.pk} AND "sga_detallesilabosemanalsubtema"."status" AND "sga_subtemaunidadresultadoprogramaanalitico"."status" AND "sga_subtemaunidadresultadoprogramaanalitico"."temaunidadresultadoprogramaanalitico_id" = {tema[2]} AND "sga_subtemaunidadresultadoprogramaanalitico"."temaunidadresultadoprogramaanalitico_id" IS NOT NULL AND "sga_temaunidadresultadoprogramaanalitico"."status") ORDER BY "sga_subtemaunidadresultadoprogramaanalitico"."orden" ASC"""
                            cursor.execute(sql_subtemas)
                            subtemas = cursor.fetchall()
                            # subtemas = silsem.subtemas_silabosemanal(tema.temaunidadresultadoprogramaanalitico)
                            for subtema in subtemas:
                                if (fechafin <= fechaactual) or (SubTemaAsistencia.objects.values('id').filter(subtema__silabosemanal=silsem, fecha__lte=fechafin, subtema=subtema[0]).exists()):
                                    cont += 1
                                    # if SubTemaAsistencia.objects.values('id').filter(subtema__silabosemanal=silsem, fecha__lte=fechafin, subtema=subtema[0]).exists() or (num_semana_fechainiciosilabo in num_sem_dia_no_laborable):
                                    if (SubTemaAsistencia.objects.values('id').filter(subtema__silabosemanal=silsem, fecha__lte=fechafin, subtema=subtema[0]).exists()) or (SubTemaAsistencia.objects.values('id').filter(subtema__silabosemanal=silsem,tema__leccion__solicitada = True, subtema=subtema[0]).exists()):
                                        porcentajecumplimiento += 1
                                        listado.append(['', '', '', subtema[1], 'subtemas', 1])
                                    else:
                                        listado.append(['', '', '', subtema[1], 'subtemas', 0])
                                else:
                                    listado.append(['', '', '', subtema[1], 'subtemas', '-'])

                            # subtemaadicional = silsem.subtemas_adicionales(tema.id)
                            subtemaadicional = silsem.subtemaadicionalessilabo_set.values_list('id','subtema').filter(status=True, tema_id=tema[0]).order_by('id')
                            for subtemasad in subtemaadicional:
                                if (fechafin <= fechaactual) or (SubTemaAdicionalAsistencia.objects.values('id').filter(fecha__lte=fechafin, subtema=subtemasad[0]).exists()):
                                    cont += 1
                                    # if SubTemaAdicionalAsistencia.objects.values('id').filter(fecha__lte=fechafin, subtema=subtemasad[0]).exists() or (num_semana_fechainiciosilabo in num_sem_dia_no_laborable):
                                    if (SubTemaAdicionalAsistencia.objects.values('id').filter(fecha__lte=fechafin, subtema=subtemasad[0]).exists()) or (SubTemaAdicionalAsistencia.objects.values('id').filter(tema__leccion__solicitada = True, subtema=subtemasad[0]).exists()):
                                        porcentajecumplimiento += 1
                                        listado.append(['', '', '', subtemasad[1], 'subtemas', 1])
                                    else:
                                        listado.append(['', '', '', subtemasad[1], 'subtemas', 0])
                                else:
                                    listado.append(['', '', '', subtemasad[1], 'subtemas', '-'])

        try:
            percent = (porcentajecumplimiento / cont)
            percent = round((percent * 100), 2)
            calculosobre30 = round(((percent * 30) / 100), 2)
            # resultadoporcentajes = percent if 0 < percent <= 100 else 100
        except ZeroDivisionError:
            if no_empieza:
                percent = 100
                calculosobre30 = 30
            percent = 0
            calculosobre30 = 0

        listado.append([percent, calculosobre30, 'ponderacion'])
        # now = datetime.now()
        # end_of_day = datetime.combine(now.date(), datetime.max.time())
        # seconds_until_end_of_day = (end_of_day - now).total_seconds()
        # cache.set(cache_key, listado, seconds_until_end_of_day )
        return listado
    except Exception as e:
        import sys
        print(e)
        print('Error on line {} - {}'.format(sys.exc_info()[-1].tb_lineno, e))


@register.simple_tag
def contenido_profesor_total_V2(obj, profesor, materia, fechaini, fechafin):
    try:
        from sga.models import (DetalleDistributivo, GuiaEstudianteSilaboSemanal, TareaPracticaSilaboSemanal, \
            TipoProfesor, ProfesorMateria, ClaseActividad, Silabo, CompendioSilaboSemanal, VideoMagistralSilaboSemanal, \
            ForoSilaboSemanal, TareaSilaboSemanal, TestSilaboSemanalAdmision, TestSilaboSemanal, \
            DiapositivaSilaboSemanal, MaterialAdicionalSilaboSemanal, SilaboSemanal, EvaluacionAprendizajeSilaboSemanal, TemaAsistencia, SubTemaAsistencia, SubTemaAdicionalAsistencia, DiasNoLaborable, DetalleSilaboSemanalSubtema,SolicitudAperturaClase)
        from django.db.models import Exists, OuterRef
        from inno.models import RespuestaPreguntaEncuestaSilaboGrupoEstudiantes
        from django.db import connections
        from django.core.cache import cache
        # cache_key = f'silabo_data_calculo_total_{materia.pk}'
        # cached_data = cache.get(cache_key)
        #
        # if cached_data:
        #     return cached_data
        listado = []
        periodo = obj.periodo
        fechaactual = datetime.now().date()
        periodos = [obj.periodo.pk]

        ####################################################################################################
        # -------------------------------PLANIFICACION DE RECURSOS------------------------------------#
        ## RECURSOS ##
        cantidad_diapositivas = 0
        cantidad_diapositivas_moodle = 0
        total_diapositiva = 0
        porcentaje_diapositiva = 0

        cantidad_compendio = 0
        cantidad_compendio_moodle = 0
        total_compendio = 0
        porcentaje_compendio = 0

        cantidad_guia_estudiante = 0
        cantidad_guia_estudiante_moodle = 0
        total_guia_estudiante = 0
        porcentaje_guia_estudiante = 0

        cantidad_material = 0
        cantidad_material_moodle = 0
        total_material = 0
        porcentaje_material = 0

        total_ACD = 0
        ## ACD ##
        cantidad_test = 0
        cantidad_test_moodle = 0
        porcentaje_test = 0

        cantidad_taller = 0
        cantidad_taller_moodle = 0
        porcentaje_taller = 0

        cantidad_expo = 0
        cantidad_expo_moodle = 0
        porcentaje_expo = 0
        ## AA ##
        cantidad_foro = 0
        cantidad_foro_moodle = 0
        porcentaje_foro = 0

        cantidad_tarea = 0
        cantidad_tarea_moodle = 0
        porcentaje_tarea = 0

        cantidad_caso = 0
        cantidad_caso_moodle = 0
        porcentaje_caso = 0

        cantidad_inves = 0
        cantidad_inves_moodle = 0
        porcentaje_inves = 0
        ## APE ##
        cantidad_practicas = 0
        cantidad_practicas_moodle = 0
        porcentaje_practicas = 0

        resultadoporcentajes = 0
        resultadoporcentajes_sobre_40 = 0

        if silabocab := Silabo.objects.select_related('materia').filter(status=True, materia_id=materia.pk).first():
            fechaactual = datetime.now().date()
            diferencia = fechaactual - fechaini
            num_semanas = (diferencia.days // 7) + 1
            silabosemanal = silabocab.silabosemanal_set.filter(status=True). \
                annotate(tieneactividadplanificada=Exists(
                EvaluacionAprendizajeSilaboSemanal.objects.filter(silabosemanal__silabo_id=silabocab.id,
                                                                  tipoactividadsemanal=1, silabosemanal_id=OuterRef('id'),
                                                                  status=True, silabosemanal__status=True)))
            try:
                semanas = silabosemanal[:num_semanas-1]
            except Exception as ex:
                if silabosemanal.count() > 0:
                    semanas = silabosemanal[:0]

            tiene_horas_ape = False
            if silabocab.materia.asignaturamalla.horasapesemanal > 0:
                tiene_horas_ape = True

            for semana in semanas:
                ## RECURSOS ##
                cantidad_diapositivas += semana.diapositivasilabosemanal_set.filter(status=True).count()
                cantidad_diapositivas_moodle += semana.diapositivasilabosemanal_set.filter(Q(status=True) & (Q(estado=4) | Q(migrado=True))).count()
                cantidad_compendio += semana.compendiosilabosemanal_set.filter(status=True).count()
                cantidad_compendio_moodle += semana.compendiosilabosemanal_set.filter(Q(status=True) & (Q(estado=4) | Q(migrado=True))).count()
                if semana.guiaestudiantesilabosemanal_set.filter(status=True):
                    cantidad_guia_estudiante += semana.guiaestudiantesilabosemanal_set.filter(status=True).count()
                    cantidad_guia_estudiante_moodle += semana.guiaestudiantesilabosemanal_set.filter(Q(status=True) & (Q(estado=4) | Q(migrado=True))).count()
                cantidad_material += semana.materialadicionalsilabosemanal_set.filter(status=True).count()
                cantidad_material_moodle += semana.materialadicionalsilabosemanal_set.filter(Q(status=True) & (Q(estado=4) | Q(migrado=True))).count()
                ## ACD ##
                cantidad_test += semana.testsilabosemanal_set.filter(status=True).count()
                cantidad_test_moodle += semana.testsilabosemanal_set.filter(Q(status=True) & (Q(estado=4) | Q(migrado=True))).count()
                if semana.tareasilabosemanal_set.filter(actividad_id=3, status=True):
                    cantidad_taller += semana.tareasilabosemanal_set.filter(actividad_id=3, status=True).count()
                    cantidad_taller_moodle += semana.tareasilabosemanal_set.filter((Q(actividad_id=3) & Q(status=True)) & (Q(estado=4) | Q(migrado=True))).count()
                if semana.tareasilabosemanal_set.filter(actividad_id=2, status=True):
                    cantidad_expo += semana.tareasilabosemanal_set.filter(actividad_id=2, status=True).count()
                    cantidad_expo_moodle += semana.tareasilabosemanal_set.filter((Q(actividad_id=2) & Q(status=True)) & (Q(estado=4) | Q(migrado=True))).count()
                ## AA ##
                if semana.forosilabosemanal_set.filter(status=True):
                    cantidad_foro += semana.forosilabosemanal_set.filter(status=True).count()
                    cantidad_foro_moodle += semana.forosilabosemanal_set.filter(Q(status=True) & (Q(estado=4) | Q(migrado=True))).count()
                if semana.tareasilabosemanal_set.filter(actividad_id=5, status=True):
                    cantidad_tarea += semana.tareasilabosemanal_set.filter(actividad_id=5, status=True).count()
                    cantidad_tarea_moodle += semana.tareasilabosemanal_set.filter((Q(actividad_id=5) & Q(status=True)) & (Q(estado=4) | Q(migrado=True))).count()
                if semana.tareasilabosemanal_set.filter(actividad_id=8, status=True):
                    cantidad_caso += semana.tareasilabosemanal_set.filter(actividad_id=8, status=True).count()
                    cantidad_caso_moodle += semana.tareasilabosemanal_set.filter((Q(actividad_id=8) & Q(status=True)) & (Q(estado=4) | Q(migrado=True))).count()
                if semana.tareasilabosemanal_set.filter(actividad_id=7, status=True):
                    cantidad_inves += semana.tareasilabosemanal_set.filter(actividad_id=7, status=True).count()
                    cantidad_inves_moodle += semana.tareasilabosemanal_set.filter((Q(actividad_id=7) & Q(status=True)) & (Q(estado=4) | Q(migrado=True))).count()
                ## APE ##
                if tiene_horas_ape:
                    if semana.tareapracticasilabosemanal_set.filter(status=True):
                        cantidad_practicas += semana.tareapracticasilabosemanal_set.filter(status=True).count()
                        cantidad_practicas_moodle += semana.tareapracticasilabosemanal_set.filter(Q(status=True) & (Q(estado=4) | Q(idtareapracticamoodle__gt=0))).count()

            cont = 0
            cont_recursos = 0
            cont_ACD = 0
            cont_AA = 0
            cont_APE = 0
            tiene_recursos = False
            tiene_ACD = False
            tiene_AA = False
            tiene_APE = False
            porcentaje_total_recursos = 0
            porcentaje_total_ACD = 0
            porcentaje_total_AA = 0
            porcentaje_total_APE = 0
            ## RECURSOS
            if cantidad_diapositivas > 0:
                tiene_recursos = True
                porcentaje_diapositiva = round((cantidad_diapositivas_moodle/cantidad_diapositivas)*100,2)
                cont_recursos += 1
            if cantidad_compendio > 0:
                tiene_recursos = True
                porcentaje_compendio = round((cantidad_compendio_moodle / cantidad_compendio) * 100, 2)
                cont_recursos += 1
            if cantidad_guia_estudiante > 0:
                tiene_recursos = True
                porcentaje_guia_estudiante = round((cantidad_guia_estudiante_moodle / cantidad_guia_estudiante) * 100, 2)
                cont_recursos += 1
            if cantidad_material > 0:
                tiene_recursos = True
                porcentaje_material = round((cantidad_material_moodle / cantidad_material) * 100, 2)
                cont_recursos += 1
            if tiene_recursos:
                cont += 1
                porcentaje_total_recursos = (porcentaje_diapositiva + porcentaje_compendio + porcentaje_guia_estudiante + porcentaje_material)/cont_recursos

            ## ACD
            if cantidad_test > 0:
                tiene_ACD = True
                porcentaje_test = round((cantidad_test_moodle / cantidad_test) * 100, 2)
                cont_ACD += 1
            if cantidad_taller > 0:
                tiene_ACD = True
                porcentaje_taller = round((cantidad_taller_moodle / cantidad_taller) * 100, 2)
                cont_ACD += 1
            if cantidad_expo > 0:
                tiene_ACD = True
                porcentaje_expo = round((cantidad_expo_moodle / cantidad_expo) * 100, 2)
                cont_ACD += 1
            if tiene_ACD:
                cont += 1
                porcentaje_total_ACD = (porcentaje_test + porcentaje_taller + porcentaje_expo) / cont_ACD

            ## AA
            if cantidad_foro > 0:
                tiene_AA = True
                porcentaje_foro = round((cantidad_foro_moodle / cantidad_foro) * 100, 2)
                cont_AA += 1
            if cantidad_tarea > 0:
                tiene_AA = True
                porcentaje_tarea = round((cantidad_tarea_moodle / cantidad_tarea) * 100, 2)
                cont_AA += 1
            if cantidad_caso > 0:
                tiene_AA = True
                porcentaje_caso = round((cantidad_caso_moodle / cantidad_caso) * 100, 2)
                cont_AA += 1
            if cantidad_inves > 0:
                tiene_AA = True
                porcentaje_inves = round((cantidad_inves_moodle / cantidad_inves) * 100, 2)
                cont_AA += 1
            if tiene_AA:
                cont += 1
                porcentaje_total_AA = (porcentaje_foro + porcentaje_tarea + porcentaje_caso + porcentaje_inves)/cont_AA

            ## APE
            if cantidad_practicas > 0:
                tiene_APE = True
                porcentaje_practicas = round((cantidad_practicas_moodle / cantidad_practicas) * 100, 2)
                cont_APE += 1
            if tiene_APE:
                cont += 1
                porcentaje_total_APE = porcentaje_practicas / cont_APE

            try:
                if materia.modeloevaluativo.id != 66:
                    resultadoporcentajes = round(((porcentaje_total_recursos+porcentaje_total_ACD+porcentaje_total_AA+ porcentaje_total_APE) / cont), 2)
                else:
                    resultadoporcentajes = 100
                resultadoporcentajes_sobre_40 = round(((resultadoporcentajes*40) / 100), 2)
            except ZeroDivisionError:
                resultadoporcentajes = 0
                resultadoporcentajes_sobre_40 = 0
        else:
            if materia.modeloevaluativo.id == 66:
                resultadoporcentajes_sobre_40 = 40
            else:
                resultadoporcentajes_sobre_40 = 0

        ####################################################################################################
        # -------------------------------CONFIRMACION DE TEMAS------------------------------------#
        if silabos_tema := Silabo.objects.filter(status=True, materia_id=materia.pk).first():
            porcentajecumplimiento = 0
            calculosobre30 = 0
            cont = 0
            no_empieza = False
            numeros_semana = [fecha.isocalendar()[1] for fecha in
                              periodo.diasnolaborable_set.filter(status=True).values_list('fecha', flat=True)]
            num_sem_dia_no_laborable = list(dict.fromkeys(numeros_semana))
            silabosemanal_tema = silabos_tema.silabosemanal_set.filter(status=True).order_by('numsemana')
            if silabosemanal_tema:
                cursor = connections['sga_select'].cursor()
                for silsem in silabosemanal_tema:
                    # unidadsilsem = silsem.temas_seleccionados_planclase()
                    sql_tema = f"""SELECT "sga_detallesilabosemanaltema"."id", "sga_temaunidadresultadoprogramaanalitico"."descripcion", "sga_detallesilabosemanaltema"."temaunidadresultadoprogramaanalitico_id" FROM "sga_detallesilabosemanaltema" INNER JOIN "sga_temaunidadresultadoprogramaanalitico" ON ("sga_detallesilabosemanaltema"."temaunidadresultadoprogramaanalitico_id" = "sga_temaunidadresultadoprogramaanalitico"."id") WHERE ("sga_detallesilabosemanaltema"."silabosemanal_id" = {silsem.pk} AND "sga_temaunidadresultadoprogramaanalitico"."status" AND "sga_detallesilabosemanaltema"."status") ORDER BY "sga_temaunidadresultadoprogramaanalitico"."orden" ASC"""
                    cursor.execute(sql_tema)
                    unidadsilsem = cursor.fetchall()
                    # unidadsilsem = list(silsem.detallesilabosemanaltema_set.select_related('temaunidadresultadoprogramaanalitico').values_list('id','temaunidadresultadoprogramaanalitico__descripcion','temaunidadresultadoprogramaanalitico').filter(temaunidadresultadoprogramaanalitico__status=True).order_by('temaunidadresultadoprogramaanalitico__orden'))
                    fechainicio = silsem.fechainiciosemana
                    fechafin = silsem.fechafinciosemana
                    if fechainicio > fechaactual:
                        no_empieza = True
                        break
                    num_semana_fechainiciosilabo = fechainicio.isocalendar()[1]
                    if (num_semana_fechainiciosilabo in num_sem_dia_no_laborable):
                        fechafin += timedelta(weeks=2)
                    else:
                        fechafin += timedelta(weeks=1)
                    if unidadsilsem:
                        for tema in unidadsilsem:
                            if (fechafin <= fechaactual) or (
                            TemaAsistencia.objects.values('id').filter(fecha__lte=fechafin, tema=tema[0]).exists()):
                                cont += 1
                                if (TemaAsistencia.objects.values('id').filter(fecha__lte=fechafin,
                                                                               tema=tema[0]).exists()) or (
                                TemaAsistencia.objects.values('id').filter(leccion__solicitada=True,
                                                                           tema=tema[0]).exists()):
                                    porcentajecumplimiento += 1
                            subtemas = DetalleSilaboSemanalSubtema.objects.select_related(
                                'subtemaunidadresultadoprogramaanalitico').values_list('id',
                                                                                       'subtemaunidadresultadoprogramaanalitico__descripcion').filter(
                                status=True,
                                subtemaunidadresultadoprogramaanalitico__temaunidadresultadoprogramaanalitico=tema[2],
                                subtemaunidadresultadoprogramaanalitico__status=True,
                                subtemaunidadresultadoprogramaanalitico__temaunidadresultadoprogramaanalitico__isnull=False,
                                subtemaunidadresultadoprogramaanalitico__temaunidadresultadoprogramaanalitico__status=True,
                                silabosemanal=silsem).order_by('subtemaunidadresultadoprogramaanalitico__orden')
                            sql_subtemas = f"""SELECT "sga_detallesilabosemanalsubtema"."id", "sga_subtemaunidadresultadoprogramaanalitico"."descripcion" FROM "sga_detallesilabosemanalsubtema" INNER JOIN "sga_subtemaunidadresultadoprogramaanalitico" ON ("sga_detallesilabosemanalsubtema"."subtemaunidadresultadoprogramaanalitico_id" = "sga_subtemaunidadresultadoprogramaanalitico"."id") INNER JOIN "sga_temaunidadresultadoprogramaanalitico" ON ("sga_subtemaunidadresultadoprogramaanalitico"."temaunidadresultadoprogramaanalitico_id" = "sga_temaunidadresultadoprogramaanalitico"."id") WHERE ("sga_detallesilabosemanalsubtema"."silabosemanal_id" = {silsem.pk} AND "sga_detallesilabosemanalsubtema"."status" AND "sga_subtemaunidadresultadoprogramaanalitico"."status" AND "sga_subtemaunidadresultadoprogramaanalitico"."temaunidadresultadoprogramaanalitico_id" = {tema[2]} AND "sga_subtemaunidadresultadoprogramaanalitico"."temaunidadresultadoprogramaanalitico_id" IS NOT NULL AND "sga_temaunidadresultadoprogramaanalitico"."status") ORDER BY "sga_subtemaunidadresultadoprogramaanalitico"."orden" ASC"""
                            cursor.execute(sql_subtemas)
                            subtemas = cursor.fetchall()
                            # subtemas = silsem.subtemas_silabosemanal(tema.temaunidadresultadoprogramaanalitico)
                            for subtema in subtemas:
                                if (fechafin <= fechaactual) or (
                                SubTemaAsistencia.objects.values('id').filter(subtema__silabosemanal=silsem,
                                                                              fecha__lte=fechafin,
                                                                              subtema=subtema[0]).exists()):
                                    cont += 1
                                    if (SubTemaAsistencia.objects.values('id').filter(subtema__silabosemanal=silsem,
                                                                                      fecha__lte=fechafin,
                                                                                      subtema=subtema[0]).exists()) or (
                                    SubTemaAsistencia.objects.values('id').filter(subtema__silabosemanal=silsem,
                                                                                  tema__leccion__solicitada=True,
                                                                                  subtema=subtema[0]).exists()):
                                        porcentajecumplimiento += 1
                            # subtemaadicional = silsem.subtemas_adicionales(tema.id)
                            subtemaadicional = silsem.subtemaadicionalessilabo_set.values_list('id', 'subtema').filter(
                                status=True, tema_id=tema[0]).order_by('id')
                            for subtemasad in subtemaadicional:
                                if (fechafin <= fechaactual) or (
                                SubTemaAdicionalAsistencia.objects.values('id').filter(fecha__lte=fechafin,
                                                                                       subtema=subtemasad[0]).exists()):
                                    cont += 1
                                    # if SubTemaAdicionalAsistencia.objects.values('id').filter(fecha__lte=fechafin, subtema=subtemasad[0]).exists() or (num_semana_fechainiciosilabo in num_sem_dia_no_laborable):
                                    if (SubTemaAdicionalAsistencia.objects.values('id').filter(fecha__lte=fechafin,
                                                                                               subtema=subtemasad[
                                                                                                   0]).exists()) or (
                                    SubTemaAdicionalAsistencia.objects.values('id').filter(
                                            tema__leccion__solicitada=True, subtema=subtemasad[0]).exists()):
                                        porcentajecumplimiento += 1

            try:
                if materia.modeloevaluativo.id != 66:
                    percent = porcentajecumplimiento / cont
                    percent = percent * 100
                else:
                    percent = 100
                calculosobre30 = round(((percent * 30) / 100), 2)
                # resultadoporcentajes = percent if 0 < percent <= 100 else 100
            except ZeroDivisionError:
                if no_empieza:
                    percent = 100
                    calculosobre30 = 30
                percent = 0
                calculosobre30 = 0
        else:
            if materia.modeloevaluativo.id == 66:
                calculosobre30 = 30
            else:
                calculosobre30 = 0

        ####################################################################################################


        ####################################################################################################
        # -------------------------------PORCENTAJE DE ENCUESTAS------------------------------------#
        preguntas_con_respuestas = RespuestaPreguntaEncuestaSilaboGrupoEstudiantes.objects.values(
            'pregunta__id', 'pregunta__descripcion'
        ).annotate(
            cantidad_si = Coalesce(Count(Case(When(respuesta='SI', then=1))), Value(0)),
            cantidad_no = Coalesce(Count(Case(When(respuesta='NO', then=1))), Value(0)),
            cantidad_total = F('cantidad_si') + F('cantidad_no'),
            porcentaje = F('cantidad_si') * 100 / F('cantidad_total')
        ).filter(~Q(respuesta__isnull=True), status=True, inscripcionencuestasilabo__encuesta__encuestagrupoestudianteseguimientosilabo__periodo = periodo,inscripcionencuestasilabo__materia__id=materia.id).distinct()
        suma_total_encuesta = 0
        porcentaje_total_encuesta = 0
        porcentaje_encuesta_sobre30 = 0
        cont_encuesta = 0
        if preguntas_con_respuestas.exists():
            for pregunta in preguntas_con_respuestas:
                suma_total_encuesta += pregunta['porcentaje']
                cont_encuesta += 1
        if cont_encuesta > 0:
            porcentaje_total_encuesta = round((suma_total_encuesta / cont_encuesta), 2)
            porcentaje_encuesta_sobre30 = round(((porcentaje_total_encuesta * 30) / 100), 2)
        else:
            porcentaje_total_encuesta = 100.0
            porcentaje_encuesta_sobre30 = 30.0
        ####################################################################################################
        ###### NO APLICA PARA INFORME PRELIMINAR
        if not variable_valor('MOSTRAR_RESULTADOS_SILABO'):
            porcentaje_encuesta_sobre30 = 0
            #####TOTAL SIN CONTAR ENCUESTA
            porcentajetotalsilabo = round((((resultadoporcentajes_sobre_40 + calculosobre30 + porcentaje_encuesta_sobre30) *100) / 70), 2)
        else:
            ######SUMATORIA PUNTAJE SILABO
            porcentajetotalsilabo = round((resultadoporcentajes_sobre_40 + calculosobre30 + porcentaje_encuesta_sobre30), 2)


        listado.append([resultadoporcentajes_sobre_40,calculosobre30,porcentaje_encuesta_sobre30,porcentajetotalsilabo])
        # now = datetime.now()
        # end_of_day = datetime.combine(now.date(), datetime.max.time())
        # seconds_until_end_of_day = (end_of_day - now).total_seconds()
        # cache.set(cache_key, listado, seconds_until_end_of_day)
        return listado
    except Exception as e:
        import sys
        print(e)
        print('Error on line {} - {}'.format(sys.exc_info()[-1].tb_lineno, e))

@register.simple_tag
def temasimpartidos_V2(obj, idmateria, periodo):
    from inno.models import TemaImpartidoDocente, SubtemaImpartidoDocente
    from django.db import connections
    from itertools import groupby
    from operator import itemgetter
    try:
        temas_impartidos = TemaImpartidoDocente.objects.filter(
            status=True,
            periodo_id=periodo.pk,
            materia_id=idmateria
        ).order_by('fecha_inicio_semana')

        if temas_impartidos:
            grouped_temas = {}
            for key, group in groupby(temas_impartidos, key=lambda x: x.fecha_inicio_semana):
                first_item = next(group)
                group_list = [first_item] + list(group)
                custom_key = f"Semana: {first_item.semana} (Fecha inicio: {first_item.fecha_inicio_semana.strftime('%d/%m/%Y')} - Fecha fin: {first_item.fecha_fin_semana.strftime('%d/%m/%Y')})"
                grouped_temas[custom_key] = group_list

            return grouped_temas
        else:
            return None
    except Exception as e:
        import sys
        print(e)
        print('Error on line {} - {}'.format(sys.exc_info()[-1].tb_lineno, e))

@register.simple_tag
def subtemasimpartidos_V2(tema):
    from inno.models import  SubtemaImpartidoDocente
    from django.db import connections
    try:
        subtemas_impartidos = SubtemaImpartidoDocente.objects.filter(status=True, tema=tema)
        if subtemas_impartidos:
            return subtemas_impartidos
        else:
            return None
    except Exception as e:
        import sys
        print(e)
        print('Error on line {} - {}'.format(sys.exc_info()[-1].tb_lineno, e))

@register.simple_tag
def contenido_profesor_total_V3(obj, profesor, materia, fechaini, fechafin):
    try:
        from sga.models import (DetalleDistributivo, GuiaEstudianteSilaboSemanal, TareaPracticaSilaboSemanal, \
            TipoProfesor, ProfesorMateria, ClaseActividad, Silabo, CompendioSilaboSemanal, VideoMagistralSilaboSemanal, \
            ForoSilaboSemanal, TareaSilaboSemanal, TestSilaboSemanalAdmision, TestSilaboSemanal, \
            DiapositivaSilaboSemanal, MaterialAdicionalSilaboSemanal, SilaboSemanal, EvaluacionAprendizajeSilaboSemanal, TemaAsistencia, SubTemaAsistencia, SubTemaAdicionalAsistencia, DiasNoLaborable, DetalleSilaboSemanalSubtema,SolicitudAperturaClase)
        from django.db.models import Exists, OuterRef
        from inno.models import RespuestaPreguntaEncuestaSilaboGrupoEstudiantes, TemaImpartidoDocente
        from django.db import connections
        listado = []
        periodo = obj.periodo
        fechaactual = datetime.now().date()
        periodos = [obj.periodo.pk]

        ####################################################################################################
        # -------------------------------PLANIFICACION DE RECURSOS------------------------------------#
        ## RECURSOS ##
        cantidad_diapositivas = 0
        cantidad_diapositivas_moodle = 0
        total_diapositiva = 0
        porcentaje_diapositiva = 0

        cantidad_compendio = 0
        cantidad_compendio_moodle = 0
        total_compendio = 0
        porcentaje_compendio = 0

        cantidad_guia_estudiante = 0
        cantidad_guia_estudiante_moodle = 0
        total_guia_estudiante = 0
        porcentaje_guia_estudiante = 0

        cantidad_material = 0
        cantidad_material_moodle = 0
        total_material = 0
        porcentaje_material = 0

        total_ACD = 0
        ## ACD ##
        cantidad_test = 0
        cantidad_test_moodle = 0
        porcentaje_test = 0

        cantidad_taller = 0
        cantidad_taller_moodle = 0
        porcentaje_taller = 0

        cantidad_expo = 0
        cantidad_expo_moodle = 0
        porcentaje_expo = 0
        ## AA ##
        cantidad_foro = 0
        cantidad_foro_moodle = 0
        porcentaje_foro = 0

        cantidad_tarea = 0
        cantidad_tarea_moodle = 0
        porcentaje_tarea = 0

        cantidad_caso = 0
        cantidad_caso_moodle = 0
        porcentaje_caso = 0

        cantidad_inves = 0
        cantidad_inves_moodle = 0
        porcentaje_inves = 0
        ## APE ##
        cantidad_practicas = 0
        cantidad_practicas_moodle = 0
        porcentaje_practicas = 0

        resultadoporcentajes = 0
        resultadoporcentajes_sobre_40 = 0

        if silabocab := Silabo.objects.select_related('materia').filter(status=True, materia_id=materia.pk).first():
            fechaactual = datetime.now().date()
            diferencia = fechaactual - fechaini
            num_semanas = (diferencia.days // 7) + 1
            silabosemanal = silabocab.silabosemanal_set.filter(status=True). \
                annotate(tieneactividadplanificada=Exists(
                EvaluacionAprendizajeSilaboSemanal.objects.filter(silabosemanal__silabo_id=silabocab.id,
                                                                  tipoactividadsemanal=1, silabosemanal_id=OuterRef('id'),
                                                                  status=True, silabosemanal__status=True)))
            try:
                semanas = silabosemanal[:num_semanas-1]
            except Exception as ex:
                if silabosemanal.count() > 0:
                    semanas = silabosemanal[:0]

            tiene_horas_ape = False
            if silabocab.materia.asignaturamalla.horasapesemanal > 0:
                tiene_horas_ape = True

            for semana in semanas:
                ## RECURSOS ##
                cantidad_diapositivas += semana.diapositivasilabosemanal_set.filter(status=True).count()
                cantidad_diapositivas_moodle += semana.diapositivasilabosemanal_set.filter(Q(status=True) & (Q(estado=4) | Q(migrado=True))).count()
                cantidad_compendio += semana.compendiosilabosemanal_set.filter(status=True).count()
                cantidad_compendio_moodle += semana.compendiosilabosemanal_set.filter(Q(status=True) & (Q(estado=4) | Q(migrado=True))).count()
                if semana.guiaestudiantesilabosemanal_set.filter(status=True):
                    cantidad_guia_estudiante += semana.guiaestudiantesilabosemanal_set.filter(status=True).count()
                    cantidad_guia_estudiante_moodle += semana.guiaestudiantesilabosemanal_set.filter(Q(status=True) & (Q(estado=4) | Q(migrado=True))).count()
                cantidad_material += semana.materialadicionalsilabosemanal_set.filter(status=True).count()
                cantidad_material_moodle += semana.materialadicionalsilabosemanal_set.filter(Q(status=True) & (Q(estado=4) | Q(migrado=True))).count()
                ## ACD ##
                cantidad_test += semana.testsilabosemanal_set.filter(status=True).count()
                cantidad_test_moodle += semana.testsilabosemanal_set.filter(Q(status=True) & (Q(estado=4) | Q(migrado=True))).count()
                if semana.tareasilabosemanal_set.filter(actividad_id=3, status=True):
                    cantidad_taller += semana.tareasilabosemanal_set.filter(actividad_id=3, status=True).count()
                    cantidad_taller_moodle += semana.tareasilabosemanal_set.filter((Q(actividad_id=3) & Q(status=True)) & (Q(estado=4) | Q(migrado=True))).count()
                if semana.tareasilabosemanal_set.filter(actividad_id=2, status=True):
                    cantidad_expo += semana.tareasilabosemanal_set.filter(actividad_id=2, status=True).count()
                    cantidad_expo_moodle += semana.tareasilabosemanal_set.filter((Q(actividad_id=2) & Q(status=True)) & (Q(estado=4) | Q(migrado=True))).count()
                ## AA ##
                if semana.forosilabosemanal_set.filter(status=True):
                    cantidad_foro += semana.forosilabosemanal_set.filter(status=True).count()
                    cantidad_foro_moodle += semana.forosilabosemanal_set.filter(Q(status=True) & (Q(estado=4) | Q(migrado=True))).count()
                if semana.tareasilabosemanal_set.filter(actividad_id=5, status=True):
                    cantidad_tarea += semana.tareasilabosemanal_set.filter(actividad_id=5, status=True).count()
                    cantidad_tarea_moodle += semana.tareasilabosemanal_set.filter((Q(actividad_id=5) & Q(status=True)) & (Q(estado=4) | Q(migrado=True))).count()
                if semana.tareasilabosemanal_set.filter(actividad_id=8, status=True):
                    cantidad_caso += semana.tareasilabosemanal_set.filter(actividad_id=8, status=True).count()
                    cantidad_caso_moodle += semana.tareasilabosemanal_set.filter((Q(actividad_id=8) & Q(status=True)) & (Q(estado=4) | Q(migrado=True))).count()
                if semana.tareasilabosemanal_set.filter(actividad_id=7, status=True):
                    cantidad_inves += semana.tareasilabosemanal_set.filter(actividad_id=7, status=True).count()
                    cantidad_inves_moodle += semana.tareasilabosemanal_set.filter((Q(actividad_id=7) & Q(status=True)) & (Q(estado=4) | Q(migrado=True))).count()
                ## APE ##
                if tiene_horas_ape:
                    if semana.tareapracticasilabosemanal_set.filter(status=True):
                        cantidad_practicas += semana.tareapracticasilabosemanal_set.filter(status=True).count()
                        cantidad_practicas_moodle += semana.tareapracticasilabosemanal_set.filter(Q(status=True) & (Q(estado=4) | Q(idtareapracticamoodle__gt=0))).count()

            cont = 0
            cont_recursos = 0
            cont_ACD = 0
            cont_AA = 0
            cont_APE = 0
            tiene_recursos = False
            tiene_ACD = False
            tiene_AA = False
            tiene_APE = False
            porcentaje_total_recursos = 0
            porcentaje_total_ACD = 0
            porcentaje_total_AA = 0
            porcentaje_total_APE = 0
            ## RECURSOS
            if cantidad_diapositivas > 0:
                tiene_recursos = True
                porcentaje_diapositiva = round((cantidad_diapositivas_moodle/cantidad_diapositivas)*100,2)
                cont_recursos += 1
            if cantidad_compendio > 0:
                tiene_recursos = True
                porcentaje_compendio = round((cantidad_compendio_moodle / cantidad_compendio) * 100, 2)
                cont_recursos += 1
            if cantidad_guia_estudiante > 0:
                tiene_recursos = True
                porcentaje_guia_estudiante = round((cantidad_guia_estudiante_moodle / cantidad_guia_estudiante) * 100, 2)
                cont_recursos += 1
            if cantidad_material > 0:
                tiene_recursos = True
                porcentaje_material = round((cantidad_material_moodle / cantidad_material) * 100, 2)
                cont_recursos += 1
            if tiene_recursos:
                cont += 1
                porcentaje_total_recursos = (porcentaje_diapositiva + porcentaje_compendio + porcentaje_guia_estudiante + porcentaje_material)/cont_recursos

            ## ACD
            if cantidad_test > 0:
                tiene_ACD = True
                porcentaje_test = round((cantidad_test_moodle / cantidad_test) * 100, 2)
                cont_ACD += 1
            if cantidad_taller > 0:
                tiene_ACD = True
                porcentaje_taller = round((cantidad_taller_moodle / cantidad_taller) * 100, 2)
                cont_ACD += 1
            if cantidad_expo > 0:
                tiene_ACD = True
                porcentaje_expo = round((cantidad_expo_moodle / cantidad_expo) * 100, 2)
                cont_ACD += 1
            if tiene_ACD:
                cont += 1
                porcentaje_total_ACD = (porcentaje_test + porcentaje_taller + porcentaje_expo) / cont_ACD

            ## AA
            if cantidad_foro > 0:
                tiene_AA = True
                porcentaje_foro = round((cantidad_foro_moodle / cantidad_foro) * 100, 2)
                cont_AA += 1
            if cantidad_tarea > 0:
                tiene_AA = True
                porcentaje_tarea = round((cantidad_tarea_moodle / cantidad_tarea) * 100, 2)
                cont_AA += 1
            if cantidad_caso > 0:
                tiene_AA = True
                porcentaje_caso = round((cantidad_caso_moodle / cantidad_caso) * 100, 2)
                cont_AA += 1
            if cantidad_inves > 0:
                tiene_AA = True
                porcentaje_inves = round((cantidad_inves_moodle / cantidad_inves) * 100, 2)
                cont_AA += 1
            if tiene_AA:
                cont += 1
                porcentaje_total_AA = (porcentaje_foro + porcentaje_tarea + porcentaje_caso + porcentaje_inves)/cont_AA

            ## APE
            if cantidad_practicas > 0:
                tiene_APE = True
                porcentaje_practicas = round((cantidad_practicas_moodle / cantidad_practicas) * 100, 2)
                cont_APE += 1
            if tiene_APE:
                cont += 1
                porcentaje_total_APE = porcentaje_practicas / cont_APE

            try:
                resultadoporcentajes = round(((porcentaje_total_recursos+porcentaje_total_ACD+porcentaje_total_AA+ porcentaje_total_APE) / cont), 2)
                resultadoporcentajes_sobre_40 = round(((resultadoporcentajes*40) / 100), 2)
            except ZeroDivisionError:
                resultadoporcentajes = 0
                resultadoporcentajes_sobre_40 = 0
        else:
            resultadoporcentajes_sobre_40 = 0

        ####################################################################################################
        # -------------------------------CONFIRMACION DE TEMAS------------------------------------#

        silabos_tema = TemaImpartidoDocente.calculo_total(materia.pk, periodo)


        ####################################################################################################


        ####################################################################################################
        # -------------------------------PORCENTAJE DE ENCUESTAS------------------------------------#
        preguntas_con_respuestas = RespuestaPreguntaEncuestaSilaboGrupoEstudiantes.objects.values(
            'pregunta__id', 'pregunta__descripcion'
        ).annotate(
            cantidad_si = Coalesce(Count(Case(When(respuesta='SI', then=1))), Value(0)),
            cantidad_no = Coalesce(Count(Case(When(respuesta='NO', then=1))), Value(0)),
            cantidad_total = F('cantidad_si') + F('cantidad_no'),
            porcentaje = F('cantidad_si') * 100 / F('cantidad_total')
        ).filter(~Q(respuesta__isnull=True), status=True, inscripcionencuestasilabo__encuesta__encuestagrupoestudianteseguimientosilabo__periodo = periodo,inscripcionencuestasilabo__materia__id=materia.id).distinct()
        suma_total_encuesta = 0
        porcentaje_total_encuesta = 0
        porcentaje_encuesta_sobre30 = 0
        cont_encuesta = 0
        if preguntas_con_respuestas.exists():
            for pregunta in preguntas_con_respuestas:
                suma_total_encuesta += pregunta['porcentaje']
                cont_encuesta += 1
        if cont_encuesta > 0:
            porcentaje_total_encuesta = round((suma_total_encuesta / cont_encuesta), 2)
            porcentaje_encuesta_sobre30 = round(((porcentaje_total_encuesta * 30) / 100), 2)
        else:
            porcentaje_total_encuesta = 100.0
            porcentaje_encuesta_sobre30 = 30.0
        ####################################################################################################
        ###### NO APLICA PARA INFORME PRELIMINAR
        # porcentaje_encuesta_sobre30 = 0
        ######SUMATORIA PUNTAJE SILABO
        porcentajetotalsilabo = round((resultadoporcentajes_sobre_40 + silabos_tema[1] + porcentaje_encuesta_sobre30), 2)
        #####TOTAL SIN CONTAR ENCUESTA
        # porcentajetotalsilabo = round(((porcentajetotalsilabo *100) / 70), 2)

        listado.append([resultadoporcentajes_sobre_40,silabos_tema[1],porcentaje_encuesta_sobre30,porcentajetotalsilabo])
        return listado
    except Exception as e:
        import sys
        print(e)
        print('Error on line {} - {}'.format(sys.exc_info()[-1].tb_lineno, e))

@register.simple_tag
def horario_seguimiento_tecnico_transaversal_fecha(obj, profesor, fechaini, fechafin, esautomatico=False):
    try:
        from sga.models import ClaseActividad, CapCabeceraSolicitudDocente, CapEventoPeriodoDocente, Silabo, ProfesorMateria, DetalleDistributivo, TipoProfesor, VideoMagistralSilaboSemanal, ClaseAsincronica, ClaseSincronica, Modalidad
        listado = []
        actividades_marcadas_criterio = []
        actividades = 0
        clase = Clase.objects.filter(
            Q(status=True, activo=True, profesor=profesor, materia__nivel__periodo=obj.periodo,
              materia__nivel__periodo__visible=True, materia__nivel__periodo__visiblehorario=True),
            Q(Q(fin__gte=fechafin))).filter(tipoprofesor_id=22).distinct().order_by('turno__inicio')

        if clase.exists():
            actividades += int(len(clase.values('dia', 'turno')))
            for cl in clase.values('dia', 'turno').exclude().distinct():
                actividades_marcadas_criterio.append(int('{}{}'.format(cl['dia'], cl['turno'])))


        claseactividad = ClaseActividad.objects.filter(detalledistributivo__criteriodocenciaperiodo=obj, detalledistributivo__distributivo__profesor=profesor, status=True).order_by('inicio', 'dia', 'turno__comienza')
        listadosilabos = Silabo.objects.filter(materia_id__in=ProfesorMateria.objects.values_list('materia_id').filter(profesor=profesor, materia__nivel__periodo=obj.periodo,
                                                                                                                       tipoprofesor_id__in=[22],
                                                                                                                       activo=True,status=True).exclude(materia__asignaturamalla__malla__carrera__coordinacion__id=9).distinct())
        # para sacar total de horas planificadas
        # diasclas = claseactividad.values_list('dia', 'turno_id')
        diasclas = clase.values_list('dia', 'turno_id').exclude().distinct()
        dt = fechaini
        end = fechafin
        step = timedelta(days=1)

        listaretorno = []
        result = []
        while dt <= end:
            dias_nolaborables = obj.periodo.dias_nolaborables(dt)
            if not dias_nolaborables:
                for dclase in diasclas:
                    if dt.isocalendar()[2] == dclase[0]:
                        result.append(dt.strftime('%Y-%m-%d'))
            dt += step

        # INICIO SEGUIMIENTO TECNICO TRANSVERSAL
        totalporcentaje = 0
        for lsilabo in listadosilabos:
            listadoseguimiento = lsilabo.materia.seguimientotutor_set.filter(Q(fechainicio__range=(fechaini, fechafin)) | Q(fechafin__range=(fechaini, fechafin))).order_by('fechainicio')
            for seguimiento in listadoseguimiento:
                porcentaje = 0
                if seguimiento.verde() >= 0:
                    if seguimiento.amarillo() == 0 and seguimiento.rojo() == 0:
                        porcentaje = 100
                    else:
                        if seguimiento.amarillo() == 0 and seguimiento.rojo() == 0 and  seguimiento.total_acciones_correo() == 0 and seguimiento.total_acciones_llamadas() == 0:
                            porcentaje = 100
                        if seguimiento.amarillo() > 0 or seguimiento.rojo() > 0:
                            if seguimiento.total_acciones_correo() == 0 and seguimiento.total_acciones_llamadas() == 0:
                                porcentaje = 50
                            else:
                                porcentaje = 100
                totalporcentaje += porcentaje
                listado.append([lsilabo.materia, seguimiento.fechainicio, seguimiento.fechafin, seguimiento.verde(),
                                seguimiento.amarillo(), seguimiento.rojo(), seguimiento.total_acciones_correo(), seguimiento.total_acciones_llamadas(),
                                seguimiento.total_acciones_respuestas(), porcentaje, clase, seguimiento.id])

        porcentajecompendios = 0
        if listado:
            porcentajecompendios = round((totalporcentaje / len(listado)), 2)
        listado.append([0, 0, 0, 0, 0, 0, 0, 0, 0, porcentajecompendios, clase, len(result)])
        # FIN SEGUIMIENTO TECNICO TRANSVERSAL

        # INICIO VIDEOS TECNICO TRANSVERSAL
        listadovideos = []
        fechaactual = datetime.now().date()
        periodos = [obj.periodo.pk]
        detalledistributivo = DetalleDistributivo.objects.get(criteriodocenciaperiodo=obj, distributivo__profesor=profesor, status=True)
        fechasactividades = detalledistributivo.actividaddetalledistributivo_set.filter(status=True)[0]
        profesormateria = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__periodo_id__in=periodos, activo=True, materia__fin__gte=fechasactividades.desde, materia__inicio__lte=fechasactividades.hasta).exclude(tipoprofesor_id=15).only('materia').distinct()
        for m in profesormateria:
            if not m.materia.tiene_cronograma():
                return 0
        eTipoprofesor = TipoProfesor.objects.filter(pk__in=ProfesorMateria.objects.values_list('tipoprofesor_id').filter(profesor=profesor, materia__nivel__periodo_id__in=periodos, tipoprofesor_id__in=[22], activo=True, materia__fin__gte=fechasactividades.desde, materia__inicio__lte=fechasactividades.hasta).exclude(materia__modeloevaluativo_id__in=[25, 26, 57, 59, 63, 66, 67]).distinct()).first()
        resultadominimoplanificar = 0
        resultadoplanificados = 0
        resultadoparciales = '-'
        resultadoporcentajes = 0
        sumatoriaindice = 0
        subtipo_docentes = 0
        listamateriasvideo = []
        if eTipoprofesor:
            subtipo_docentes = 1
            nivelacion = False
            listadosilabos = Silabo.objects.filter(status=True, materia_id__in=ProfesorMateria.objects.values_list('materia_id').filter(profesor=profesor, materia__nivel__periodo_id__in=periodos, tipoprofesor=eTipoprofesor, activo=True, materia__fin__gte=fechasactividades.desde, materia__inicio__lte=fechasactividades.hasta).distinct())
            if listadosilabos:
                if listadosilabos.filter(materia__asignaturamalla__malla__carrera__coordinacion__id=9).exists():
                    subtipo_docentes += 1
                    nivelacion = True
                    listadosilabos = Silabo.objects.filter(status=True, materia_id__in=ProfesorMateria.objects.values_list(
                        'materia_id').filter(profesor=profesor, materia__nivel__periodo_id__in=periodos, tipoprofesor=eTipoprofesor, activo=True, materia__fin__gte=fechasactividades.desde,
                                             materia__inicio__lte=fechasactividades.hasta).exclude(materia__asignaturamalla__malla__carrera__coordinacion__id=9).distinct())
                while subtipo_docentes > 0:
                    if not listadosilabos and nivelacion:
                        subtipo_docentes -= 1
                    if subtipo_docentes == 1 and nivelacion:
                        listadosilabos = Silabo.objects.filter(status=True, materia_id__in=ProfesorMateria.objects.values_list(
                                                                   'materia_id').filter(profesor=profesor, materia__nivel__periodo_id__in=periodos, tipoprofesor=eTipoprofesor,
                                                                                        activo=True, materia__fin__gte=fechasactividades.desde, materia__inicio__lte=fechasactividades.hasta,
                                                                                        materia__asignaturamalla__malla__carrera__coordinacion__id=9).distinct())
                    listadosilabos = listadosilabos.exclude(materia__modeloevaluativo_id__in = [25, 26, 57, 59, 67, 66, 63])
                    totalvideoplanificada = 0
                    totalvideomoodle = 0
                    totalacdplanificado = 0
                    totalaaplanificado = 0
                    listadolineamiento = eTipoprofesor.lineamientorecursoperiodo_set.filter(periodo_id__in=periodos, status=True, nivelacion=True) if subtipo_docentes == 1 and nivelacion else eTipoprofesor.lineamientorecursoperiodo_set.filter(periodo_id__in=periodos, status=True, nivelacion=False)
                    listamateriasvideo = []
                    idvideomagistral = 12
                    for lsilabo in listadosilabos:
                        # ini -- para saber cuantas unidades han cerrado
                        listaunidadterminadas = []
                        silabosemanaluni = lsilabo.silabosemanal_set.values_list('detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden', 'fechafinciosemana').filter(status=True).distinct('detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden').order_by('detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden', '-fechafinciosemana')
                        for sise in silabosemanaluni:
                            if sise[0]:
                                # if sise[1] <= fechaactual:
                                if sise[1] <= fechafin:
                                    listaunidadterminadas.append(sise[0])
                        if not listaunidadterminadas:
                            listaunidadterminadas.append(1)
                        silabosemanal = lsilabo.silabosemanal_set.filter(detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden__in=listaunidadterminadas, detallesilabosemanaltema__status=True, status=True).distinct()
                        # para sacar videomagistral
                        # if idvideomagistral in listadolineamiento.values_list('tiporecurso', flat=True):
                        totalvideos = 0
                        if idvideomagistral:
                            # totalvideos = VideoMagistralSilaboSemanal.objects.filter(silabosemanal_id__in=silabosemanal.values_list('id'), idvidmagistralmoodle__gt=0, status=True).count()

                            _malla = lsilabo.materia.asignaturamalla.malla
                            coordinacion = _malla.carrera.coordinacion_carrera()
                            if lsilabo.materia.modeloevaluativo_id in [27, 64] and lsilabo.materia.asignaturamalla.transversal:
                                modalidad = Modalidad.objects.get(id=3)
                            else: modalidad = _malla.modalidad
                            eClase = clase.filter(materia=lsilabo.materia)

                            for c in eClase:
                                if coordinacion.id in [1, 2, 3, 4, 5, 12]:
                                    if c.tipohorario in [2, 7, 8, 9]:
                                        if modalidad:
                                            if modalidad.id in [1, 2]:
                                                if c.tipohorario in [2, 8]:
                                                    totalvideos += ClaseAsincronica.objects.filter(clase=c, status=True).count()
                                            elif modalidad.id in [3]:
                                                if c.tipohorario in [2, 8]:
                                                    totalvideos += ClaseSincronica.objects.filter(clase=c, status=True).count()
                                                elif c.tipohorario in [7, 9]:
                                                    totalvideos += ClaseAsincronica.objects.filter(clase=c, status=True).count()

                                elif coordinacion.id in [9]:
                                    if c.tipohorario == 1:
                                        raise NameError(u"Clase de tipo presencial no se sube video")
                                    elif c.tipohorario in [2, 7, 8, 9]:
                                        if c.tipohorario in [2, 8]:
                                            totalvideos += ClaseSincronica.objects.filter(clase=c, status=True).count()
                                        elif c.tipohorario in [7, 9]:
                                            totalvideos += ClaseAsincronica.objects.filter(clase=c, status=True).count()
                                elif coordinacion.id in [7, 10]:
                                    totalvideos += ClaseAsincronica.objects.filter(clase=c, status=True).count()


                            # totalvideos = ClaseAsincronica.objects.filter(clase_id__in=clase.filter(materia=lsilabo.materia), status=True)

                            # totalvideoplan = lsilabo.materia.nivel.periodo.lineamientorecursoperiodo_set.filter(tipoprofesor_id__in=lsilabo.materia.profesormateria_set.values_list('tipoprofesor').filter(status=True, tipoprofesor_id=22), tiporecurso=12, status=True)[0].cantidad * len(listaunidadterminadas)
                            totalvideoplan = eClase.count()
                            totalvideoplanificada += totalvideoplan
                            if totalvideos > totalvideoplan:
                                totalvideomoodle += totalvideoplan
                            else:
                                totalvideomoodle += totalvideos
                            try:
                                if totalvideos > totalvideoplan:
                                    porcentajevideoaux = 100
                                else:
                                    porcentajevideoaux = round(((100 * totalvideos) / totalvideoplan), 2)
                            except ZeroDivisionError:
                                porcentajevideoaux = 0

                            listamateriasvideo.append([lsilabo.id, lsilabo.materia, totalvideos, totalvideoplan, porcentajevideoaux])
                    # if idvideomagistral in listadolineamiento.values_list('tiporecurso', flat=True):
                    if idvideomagistral:
                        try:
                            porcentajevideo = round(((100 * totalvideomoodle) / totalvideoplanificada), 2)
                        except ZeroDivisionError:
                            porcentajevideo = 0

                        # listadovideos.append([clase, 'VIDEOS MAGISTRALES', totalvideoplanificada, totalvideomoodle, 0, 1, listamateriasvideo, porcentajevideo, idvideomagistral, False])
                        resultadominimoplanificar += totalvideoplanificada
                        resultadoplanificados += totalvideomoodle
                        resultadoporcentajes += porcentajevideo
                        sumatoriaindice += 1

                    subtipo_docentes -= 1
        try:
            resultadoporcentajes = round(((resultadoporcentajes) / sumatoriaindice), 2)

        except ZeroDivisionError:
            resultadoporcentajes = 0
        listadovideos.append([clase, listamateriasvideo, resultadominimoplanificar, resultadoplanificados, resultadoporcentajes, len(result), 0, 4, []])

        # FIN VIDEOS TECNICO TRANSVERSAL
        porcentajetotal = 0
        try:
            porcentajetotal = round(((porcentajecompendios + resultadoporcentajes)/2), 2)
        except ZeroDivisionError:
            porcentajetotal = 0

        if esautomatico:
            cuenta = False
            if not listadosilabos:
                totalmensual = '-'
                promedio = '-'
            else:
                cuenta = True
                totalmensual = len(result)
                promedio = porcentajetotal
            listado = [totalmensual, promedio, cuenta]
        return {'listaseguimiento': listado, 'listavideo': listadovideos, 'claseactividad': clase, 'porcentajetotal': porcentajetotal if porcentajetotal <= 100 else 100, 'planificadas_mes': len(result)}
    except Exception as ex:
        pass

@register.simple_tag
def horarios_contenido_profesor_v2(detalledistributivo, profesor, fechaini, fechafin, esautomatico=False, **kwargs):
    try:
        listado = []
        periodorelacionado = False
        fechaactual = datetime.now().date()
        obj = detalledistributivo.criteriodocenciaperiodo
        periodo = detalledistributivo.distributivo.periodo
        profesor = detalledistributivo.distributivo.profesor
        periodoposgrado = periodo.tipo.id in [3, 4]

        __silabo, __tipoprofesor = (kwargs.get('silabo'), kwargs.get('tipoprofesor')) if kwargs else (0, 0)

        periodos = [periodo.pk]
        fechasactividades = detalledistributivo.actividaddetalledistributivo_set.filter(hasta__gte=fechaini, status=True).first()
        if obj.periodosrelacionados.exists():
            periodos = []
            periodorelacionado = True
            for per in obj.periodosrelacionados.values_list('id', flat=True):
                periodos.append(per)

        if periodos:
            periodorelacionado = ProfesorMateria.objects.values('id').filter(profesor=profesor, materia__nivel__periodo_id__in=periodos).distinct().exists()

        profesormateria = ProfesorMateria.objects.filter(materia__asignaturamalla__asignatura__modulo=False, profesor=profesor, materia__nivel__periodo_id__in=periodos, activo=True, materia__fin__gte=fechasactividades.desde, materia__inicio__lte=fechasactividades.hasta).exclude(tipoprofesor_id=15).only('materia').distinct().exclude(materia__inicio__gt=datetime.now().date())
        for m in profesormateria:
            if not m.materia.tiene_cronograma():
                return 0

        claseactividad = detalledistributivo.claseactividad_set.filter(detalledistributivo__distributivo__profesor=profesor, status=True).order_by('inicio', 'dia', 'turno__comienza')

        # para saber total de horas en el mes
        diasclas = claseactividad.values_list('dia', 'turno_id')
        dt = fechaini
        end = fechafin
        step = timedelta(days=1)

        # listaretorno = []
        result = []
        while dt <= end:
            if not periodo.dias_nolaborables(dt):
                result += [dt.strftime('%Y-%m-%d') for dclase in claseactividad.values_list('dia', 'turno_id') if dt.isocalendar()[2] == dclase[0]]
            dt += step

        listado_actividades_adicional_cumplen = []
        resultadoporcentajes, sumatoriaindice, subtipo_docentes, resultadominimoplanificar, resultadoplanificados = 0, 0, 0, 0, 0
        filtrotipoprofesor = Q(pk__in=ProfesorMateria.objects.values_list('tipoprofesor_id', flat=True).filter(profesor=profesor, materia__nivel__periodo_id__in=periodos, tipoprofesor_id__in=[1, 2, 5, 6, 10, 11, 12, 14, 16],activo=True,  materia__fin__gte=fechasactividades.desde, materia__inicio__lte=fechasactividades.hasta).exclude(materia__modeloevaluativo_id__in=[25, 26, 57, 59, 63, 66, 67, 71, 68]).distinct().exclude(materia__inicio__gt=datetime.now().date()))

        if __tipoprofesor:
            filtrotipoprofesor &= Q(id=__tipoprofesor)

        listadotipoprofesor = TipoProfesor.objects.filter(filtrotipoprofesor)
        for ltipoprofesor in listadotipoprofesor:
            subtipo_docentes=1
            nivelacion = False
            excluded = profesor.profesormateria_set.filter(materia__nivel__periodo=periodo,materia__asignaturamalla__malla__carrera__coordinacion=9, materia__inicio__gt=datetime.now().date()).values_list('id', flat=True)
            filtro_silabo_materia = Q(materia_id__in=ProfesorMateria.objects.values_list('materia_id').filter(profesor=profesor, materia__nivel__periodo_id__in=periodos, tipoprofesor=ltipoprofesor, activo=True,  materia__fin__gte=fechasactividades.desde, materia__inicio__lte=fechasactividades.hasta).exclude(id__in=excluded).distinct(), status=True)
            if __silabo:
                filtro_silabo_materia &= Q(id__in=__silabo)
            if listadosilabos := Silabo.objects.filter(filtro_silabo_materia).exclude(materia__inicio__gt=datetime.now().date()):
                if listadosilabos.filter(materia__asignaturamalla__malla__carrera__coordinacion__id=9).exists():
                    subtipo_docentes += 1
                    nivelacion = True
                    listadosilabos = Silabo.objects.filter(status=True, materia_id__in=ProfesorMateria.objects.values_list(
                                                               'materia_id').filter(profesor=profesor,
                                                                                    materia__nivel__periodo_id__in=periodos,
                                                                                    tipoprofesor=ltipoprofesor,
                                                                                    activo=True,
                                                                                    materia__fin__gte=fechasactividades.desde,
                                                                                    materia__inicio__lte=fechasactividades.hasta).exclude(materia__asignaturamalla__malla__carrera__coordinacion__id=9).distinct())

                while subtipo_docentes > 0:
                    if not listadosilabos and nivelacion:
                        subtipo_docentes -= 1
                    if subtipo_docentes == 1 and nivelacion:
                        listadosilabos = Silabo.objects.filter(status=True,
                                                               materia_id__in=ProfesorMateria.objects.values_list(
                                                                   'materia_id').filter(profesor=profesor,
                                                                                        materia__nivel__periodo_id__in=periodos,
                                                                                        tipoprofesor=ltipoprofesor,
                                                                                        activo=True,
                                                                                        materia__fin__gte=fechasactividades.desde,
                                                                                        materia__inicio__lte=fechasactividades.hasta,
                                                                                        materia__asignaturamalla__malla__carrera__coordinacion__id=9).distinct())
                    listadosilabos = listadosilabos.exclude(materia__modeloevaluativo_id__in = [25, 26, 57, 59, 67, 66, 63, 71,68]).exclude(materia__inicio__gt=datetime.now().date())

                    # totalsilabos = listadosilabos.count()
                    # totalsilabosplanificados = listadosilabos.filter(codigoqr=True).count()
                    # try:
                    #     porcentaje = round(((100 * totalsilabosplanificados) / totalsilabos), 2)
                    # except ZeroDivisionError:
                    #     porcentaje = 0


                    totalcompendioplanificado = 0
                    totalvideoplanificado = 0
                    totalguiaplanificado = 0
                    totaldiapositivaplanificado = 0
                    totalmaterialplanificado = 0
                    totalcompendiosmoodle = 0
                    totalvideomoodle = 0
                    totalguiamoodle = 0
                    totaldiapositivasmoodle = 0
                    totalmaterialmoodle = 0
                    totalunidades = 0
                    minimocompendio, minimovideo, minimoguia = 0, 0, 0
                    totalacdplanificado = 0
                    totalaaplanificado = 0
                    # totalaaplan = 0
                    totalapeplanificado = 0
                    minimoacd = 0
                    minimoaa = 0
                    minimoape = 0
                    tieneape = 0
                    nombretipo = '{} - NIVELACIÓN'.format(ltipoprofesor.nombre) if subtipo_docentes == 1 and nivelacion else ltipoprofesor.nombre
                    listadolineamiento =  ltipoprofesor.lineamientorecursoperiodo_set.filter(periodo_id__in=periodos, status=True, nivelacion=True) if subtipo_docentes == 1 and nivelacion else ltipoprofesor.lineamientorecursoperiodo_set.filter(periodo_id__in=periodos, status=True, nivelacion=False)
                    listado.append([claseactividad,nombretipo,0,0,0,0,3])
                    listamateriasfaltaguias = []
                    listamateriasfaltavideo = []
                    listamateriasfaltacompendio = []
                    listamateriasfaltadiapositiva =[]
                    listamateriasfaltamaterial = []
                    listamateriasfaltaaa = []
                    listamateriasfaltaacd = []
                    listamateriasfaltaape = []
                    totalminimoacd = 0
                    totalminimoaa = 0
                    totalminimoape = 0
                    totalaamoodle = 0
                    totalacdmoodle = 0
                    totalapemoodle = 0
                    listado_APE_no_cumple = []
                    listado_ACD_no_cumple = []
                    listado_AA_no_cumple = []
                    listado_COMPENDIO_no_cumple = []
                    listado_VIDEOMAGISTRAL_no_cumple = []
                    listado_GUIAESTUDIANTE_no_cumple = []
                    idcompendio, idvideomagistral, idguiaestudiante = 1, 12, 4
                    for lsilabo in listadosilabos:
                        # ini -- para saber cuantas unidades han cerrado
                        listaunidadterminadas = []
                        silabosemanaluni = lsilabo.silabosemanal_set.values_list('detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden', 'fechafinciosemana').filter(status=True).filter(fechainiciosemana__gte=fechasactividades.desde).distinct('detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden').order_by('detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden', '-fechafinciosemana')
                        for sise in silabosemanaluni:
                            if sise[0]:
                                if sise[1] <= fechafin:
                                    listaunidadterminadas.append(sise[0])
                        if not listaunidadterminadas:
                            listaunidadterminadas.append(1)
                        # fin --

                        silabosemanal = lsilabo.silabosemanal_set.filter(detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden__in=listaunidadterminadas,detallesilabosemanaltema__status=True,status=True).filter(fechainiciosemana__gte=fechasactividades.desde).distinct()
                        totaltemas = 0
                        # totalunidades = len(listaunidadterminadas)
                        runidad = []
                        unidades = silabosemanal.filter(status=True).values_list('detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico_id', flat=True).distinct()
                        for silabosemana in silabosemanal:
                            for u in unidades:
                                if not u in runidad:
                                    runidad.append(u)
                                    totaltemas += len(silabosemana.temas_silabounidad_fecha(u, fechafin))

                        # para sacar todos los silabos semanales segun fecha fin del parcial
                        # _silabosemanal = silabosemanal.filter(fechainiciosemana__lte=fechafin, status=True)
                        _silabosemanal = silabosemanal.filter(Q(fechainiciosemana__lte=fechafin, fechafinciosemana__gte=fechaini), status=True)
                        idsemanas = _silabosemanal.values_list('id', flat=True)
                        query_cumplen = Q()

                        for s in _silabosemanal:
                            fecha_fin_ajustada = s.fechafinciosemana + timedelta(days=1)
                            query_cumplen |= Q(silabosemanal_id=s.id) & (Q(fecha_creacion__range=[s.fechainiciosemana, fecha_fin_ajustada]) | Q(fecha_creacion__lt=fecha_fin_ajustada))

                        registros_evaluacion_aprendizaje = EvaluacionAprendizajeSilaboSemanal.objects.filter(silabosemanal_id__in=idsemanas, tipoactividadsemanal=1, status=True)

                        # para sacar compendios
                        query_cumplen_extra = Q()
                        if ltipoprofesor.id == 16:
                            _silabosemanal_extra = lsilabo.silabosemanal_set.filter(status=True).filter(fechainiciosemana__gte=fechaini, fechainiciosemana__lte=fechafin).distinct()
                        else:
                            _silabosemanal_extra = silabosemanal.filter(fechainiciosemana__lte=fechafin, status=True)
                        if lsilabo.materia.asignaturamalla.transversal:
                            query_cumplen_extra = Q(silabosemanal_id__in=_silabosemanal_extra.values_list('id', flat=True))
                        else:
                            for s in _silabosemanal_extra:
                                fecha_fin_ajustada = s.fechafinciosemana + timedelta(days=1)
                                query_cumplen_extra |= Q(silabosemanal_id=s.id) & (Q(fecha_creacion__range=[s.fechainiciosemana, fecha_fin_ajustada]) | Q(fecha_creacion__lt=fecha_fin_ajustada))
                        idcompendio = 1
                        if idcompendio in listadolineamiento.values_list('tiporecurso', flat=True):
                            compendio_planificar = lsilabo.materia.nivel.periodo.lineamientorecursoperiodo_set.filter(tipoprofesor_id__in=lsilabo.materia.profesormateria_set.values_list('tipoprofesor').filter(status=True), tiporecurso=1, status=True)[0].cantidad * len(listaunidadterminadas)
                            compendio_cumple = CompendioSilaboSemanal.objects.filter(query_cumplen_extra, idmcompendiomoodle__gt=0, status=True)
                            compendio_no_cumple = CompendioSilaboSemanal.objects.filter(silabosemanal_id__in=idsemanas, idmcompendiomoodle__gt=0, status=True).exclude(pk__in=compendio_cumple.values_list('id', flat=True))
                            for x in compendio_cumple[:compendio_planificar]:
                                cumple = 1
                                listado_COMPENDIO_no_cumple.append(['COMPENDIO', x.id, x.descripcion, x.silabosemanal.silabo.materia.asignatura.nombre, x.silabosemanal.silabo.materia.paralelo, x.silabosemanal.numsemana, x.silabosemanal.fechainiciosemana.strftime("%d-%m-%Y"), x.silabosemanal.fechafinciosemana.strftime("%d-%m-%Y"), x.descripcion, x.fecha_creacion.strftime("%d-%m-%Y"), cumple])
                            for x in compendio_no_cumple:
                                cumple = 0
                                listado_COMPENDIO_no_cumple.append(['COMPENDIO', x.id, x.descripcion, x.silabosemanal.silabo.materia.asignatura.nombre, x.silabosemanal.silabo.materia.paralelo, x.silabosemanal.numsemana, x.silabosemanal.fechainiciosemana.strftime("%d-%m-%Y"), x.silabosemanal.fechafinciosemana.strftime("%d-%m-%Y"), x.descripcion, x.fecha_creacion.strftime("%d-%m-%Y"), cumple])
                            lista_compendio_adicional_cumple = [['COMPENDIO', nombretipo, x, x.descripcion] for x in compendio_cumple[compendio_planificar:]]
                            compendio_planificado_cumple = len(compendio_cumple)

                            totalminimocompendio = compendio_planificar
                            listado_actividades_adicional_cumplen += lista_compendio_adicional_cumple
                            minimocompendio += totalminimocompendio

                            totalcompendioplanificado += compendio_planificado_cumple
                            totalplanificadocompendio = compendio_planificado_cumple

                            if totalplanificadocompendio > totalminimocompendio:
                                totalcompendiosmoodle += totalminimocompendio
                            else:
                                totalcompendiosmoodle += totalplanificadocompendio
                            if totalplanificadocompendio < totalminimocompendio:
                                listamateriasfaltacompendio.append([lsilabo.id, lsilabo.materia, totalplanificadocompendio, totalminimocompendio])

                        # para sacar videomagistral
                        if idvideomagistral in listadolineamiento.values_list('tiporecurso', flat=True):
                            video_planificar = lsilabo.materia.nivel.periodo.lineamientorecursoperiodo_set.filter(tipoprofesor_id__in=lsilabo.materia.profesormateria_set.values_list('tipoprofesor').filter(status=True), tiporecurso=12, status=True)[0].cantidad * len(listaunidadterminadas)
                            video_cumple = VideoMagistralSilaboSemanal.objects.filter(query_cumplen_extra, idvidmagistralmoodle__gt=0, status=True)
                            video_no_cumple = VideoMagistralSilaboSemanal.objects.filter(silabosemanal_id__in=idsemanas, idvidmagistralmoodle__gt=0, status=True).exclude(pk__in=video_cumple.values_list('id', flat=True))
                            for x in video_cumple[:video_planificar]:
                                cumple = 1
                                listado_VIDEOMAGISTRAL_no_cumple.append(['VIDEO MAGISTRAL', x.id, x.descripcion, x.silabosemanal.silabo.materia.asignatura.nombre, x.silabosemanal.silabo.materia.paralelo, x.silabosemanal.numsemana, x.silabosemanal.fechainiciosemana.strftime("%d-%m-%Y"), x.silabosemanal.fechafinciosemana.strftime("%d-%m-%Y"), x.descripcion, x.fecha_creacion.strftime("%d-%m-%Y"), cumple])
                            for x in video_no_cumple:
                                cumple = 0
                                listado_VIDEOMAGISTRAL_no_cumple.append(['VIDEO MAGISTRAL', x.id, x.descripcion, x.silabosemanal.silabo.materia.asignatura.nombre, x.silabosemanal.silabo.materia.paralelo, x.silabosemanal.numsemana, x.silabosemanal.fechainiciosemana.strftime("%d-%m-%Y"), x.silabosemanal.fechafinciosemana.strftime("%d-%m-%Y"), x.descripcion, x.fecha_creacion.strftime("%d-%m-%Y"), cumple])
                            lista_video_magistral_adicional_cumple = [['VIDEO MAGISTRAL', nombretipo, x, x.nombre] for x in video_cumple[video_planificar:]]

                            video_planificado_cumple = len(video_cumple)

                            totalminimovideo = video_planificar
                            listado_actividades_adicional_cumplen += lista_video_magistral_adicional_cumple
                            minimovideo += totalminimovideo

                            totalvideoplanificado += video_planificado_cumple
                            totalplanificadovideo = video_planificado_cumple

                            if totalplanificadovideo > totalminimovideo:
                                totalvideomoodle += totalminimovideo
                            else:
                                totalvideomoodle += totalplanificadovideo
                            if totalplanificadovideo < totalminimovideo:
                                listamateriasfaltavideo.append([lsilabo.id, lsilabo.materia, totalplanificadovideo, totalminimovideo])

                        # para sacar guiaestudiante
                        if idguiaestudiante in listadolineamiento.values_list('tiporecurso', flat=True):
                            guia_planificar = lsilabo.materia.nivel.periodo.lineamientorecursoperiodo_set.filter(tipoprofesor_id__in=lsilabo.materia.profesormateria_set.values_list('tipoprofesor').filter(status=True), tiporecurso=4, status=True)[0].cantidad * len(listaunidadterminadas)
                            guia_cumple = GuiaEstudianteSilaboSemanal.objects.filter(query_cumplen_extra, idguiaestudiantemoodle__gt=0, status=True)
                            guia_no_cumple = GuiaEstudianteSilaboSemanal.objects.filter(silabosemanal_id__in=idsemanas, idguiaestudiantemoodle__gt=0, status=True).exclude(pk__in=guia_cumple.values_list('id', flat=True))
                            for x in guia_cumple[:guia_planificar]:
                                cumple = 1
                                listado_GUIAESTUDIANTE_no_cumple.append(['GUÍA ESTUDIANTE', x.id, x.descripcion, x.silabosemanal.silabo.materia.asignatura.nombre, x.silabosemanal.silabo.materia.paralelo, x.silabosemanal.numsemana, x.silabosemanal.fechainiciosemana.strftime("%d-%m-%Y"), x.silabosemanal.fechafinciosemana.strftime("%d-%m-%Y"), x.descripcion, x.fecha_creacion.strftime("%d-%m-%Y"), cumple])
                            for x in guia_no_cumple:
                                cumple = 0
                                listado_GUIAESTUDIANTE_no_cumple.append(['GUÍA ESTUDIANTE', x.id, x.descripcion, x.silabosemanal.silabo.materia.asignatura.nombre, x.silabosemanal.silabo.materia.paralelo, x.silabosemanal.numsemana, x.silabosemanal.fechainiciosemana.strftime("%d-%m-%Y"), x.silabosemanal.fechafinciosemana.strftime("%d-%m-%Y"), x.descripcion, x.fecha_creacion.strftime("%d-%m-%Y"), cumple])
                            lista_guia_estudiante_adicional_cumple = [['GUÍA ESTUDIANTE', nombretipo, x, x.observacion] for x in guia_cumple[guia_planificar:]]
                            guia_planificado_cumple = len(guia_cumple)

                            totalminimoguia = guia_planificar
                            listado_actividades_adicional_cumplen += lista_guia_estudiante_adicional_cumple
                            minimoguia += totalminimoguia

                            totalguiaplanificado += guia_planificado_cumple
                            totalplanificadoguia = guia_planificado_cumple

                            if totalplanificadoguia > totalminimoguia:
                                totalguiamoodle += totalminimoguia
                            else:
                                totalguiamoodle += totalplanificadoguia
                            if totalplanificadoguia < totalminimoguia:
                                listamateriasfaltaguias.append([lsilabo.id, lsilabo.materia, totalplanificadoguia, totalminimoguia])

                        # para sacar los compenentes acd ,aa ,ape
                        materiaplanificacion = lsilabo.materia.planificacionclasesilabo_materia_set.filter(status=True)[0]
                        listadoparciales = materiaplanificacion.tipoplanificacion.planificacionclasesilabo_set.values_list('parcial','fechafin').filter(status=True).distinct('parcial').order_by('parcial','-fechafin').exclude(parcial=None)
                        if obj.periodosrelacionados.exists():
                            if nivelacion:
                                fecha_limite = fechasactividades.hasta + timedelta(days=30)
                            else:
                                fecha_limite = fechafin + timedelta(days=30)
                            parciales = listadoparciales.values_list('parcial','fechafin').filter(status=True, fechafin__lte=fecha_limite).distinct('parcial').order_by('parcial','-fechafin')
                        else:
                            parciales = listadoparciales.values_list('parcial','fechafin', 'fechainicio').filter(Q(status=True), Q(fechafin__lte=fechafin) | Q(fechainicio__lte=fechafin)).distinct('parcial').order_by('parcial','-fechafin')
                        listaparcialterminadas = []
                        estadoparcial = 'ABIERTO'
                        idparcial = 1 if not periodo.tipo.id in [3, 4] else 0
                        # fechaparcial = ''
                        for sise in parciales:
                            if obj.periodosrelacionados.exists():
                                idparcial = sise[0]
                                listaparcialterminadas.append(sise[0])
                            else:
                                if sise[1] <= fechafin or sise[2] <= fechafin:
                                    idparcial = sise[0]
                                    listaparcialterminadas.append(sise[0])
                        for lpar in listadoparciales:
                            if listadoparciales.order_by('-parcial')[0][0] == lpar[0]:
                                    if fechafin >= lpar[1]:
                                        estadoparcial = 'CERRADO'

                        if periodo.tipo.id not in [3,4]:
                            listadocomponentes = lsilabo.materia.nivel.periodo.evaluacioncomponenteperiodo_set.select_related('componente').filter(nivelacion=True, parcial__in=listaparcialterminadas, status=True) if subtipo_docentes == 1 and nivelacion else lsilabo.materia.nivel.periodo.evaluacioncomponenteperiodo_set.select_related('componente').filter(parcial__in=listaparcialterminadas, status=True)
                        else:
                            listadocomponentes = lsilabo.materia.nivel.periodo.evaluacioncomponenteperiodo_set.select_related('componente').filter(status=True)

                        acd_planificado_cumple, cantidad_taller_exposicion, taller_exposicion_cumple, taller_exposicion_no_cumple, lista_taller_exposicion_no_cumple = 0, 0, 0, [], []
                        aa_planificado_cumple = 0

                        if ltipoprofesor.id != 2:
                            if lsilabo.materia.modeloevaluativo.id != 25:
                                if listadocomponentes.filter(componente_id=1):
                                    lista_test = registros_evaluacion_aprendizaje.filter(evaluacionaprendizaje_id=1)
                                    if subtipo_docentes == 1 and nivelacion:
                                        test_cumple = TestSilaboSemanalAdmision.objects.filter(query_cumplen)
                                        test_planificado_cumple = test_cumple.filter(silabosemanal__numsemana__in=lista_test.values_list('silabosemanal__numsemana', flat=True))
                                        test_adicional_cumple = test_cumple.exclude(pk__in=test_planificado_cumple.values_list('id', flat=True))
                                        test_no_cumple = TestSilaboSemanalAdmision.objects.filter(silabosemanal_id__in=idsemanas).exclude(pk__in=test_cumple.values_list('id', flat=True))
                                    else:
                                        test_cumple = TestSilaboSemanal.objects.filter(query_cumplen)
                                        test_planificado_cumple = test_cumple.filter(silabosemanal__numsemana__in=lista_test.values_list('silabosemanal__numsemana', flat=True))
                                        test_adicional_cumple = test_cumple.exclude(pk__in=test_planificado_cumple.values_list('id', flat=True))
                                        test_no_cumple = TestSilaboSemanal.objects.filter(silabosemanal_id__in=idsemanas).exclude(pk__in=test_cumple.values_list('id', flat=True))

                                    for x in lista_test:
                                        _recurso = test_planificado_cumple.filter(silabosemanal__numsemana=x.silabosemanal.numsemana, status=True).first() #Creados
                                        if not _recurso : _recurso = test_planificado_cumple.filter(silabosemanal__numsemana=x.silabosemanal.numsemana, status=False).first() #Eliminados
                                        cumple = 1
                                        if not _recurso:
                                            cumple = 0
                                            _recurso = test_no_cumple.filter(silabosemanal__numsemana=x.silabosemanal.numsemana).first()
                                        _nombretest = ''
                                        if _recurso:
                                            _nombretest = _recurso.descripcion if subtipo_docentes == 1 and nivelacion else _recurso.nombretest
                                        listado_ACD_no_cumple.append(['ACD', x.id, x.evaluacionaprendizaje.descripcion, x.silabosemanal.silabo.materia.asignatura.nombre, x.silabosemanal.silabo.materia.paralelo, x.silabosemanal.numsemana, x.silabosemanal.fechainiciosemana.strftime("%d-%m-%Y"), x.silabosemanal.fechafinciosemana.strftime("%d-%m-%Y"), _nombretest, _recurso.fecha_creacion.strftime("%d-%m-%Y") if _recurso else '', cumple, encrypt(x.silabosemanal.silabo.id), _recurso.status if _recurso else ''])
                                    lista_test_adicional_cumple = [['ACD', nombretipo, x, x.titulo if subtipo_docentes == 1 and nivelacion else x.nombretest] for x in test_adicional_cumple]

                                    lista_taller_adicional_cumple, lista_exposicion_adicional_cumple, taller_cumple, exposicion_cumple, lista_taller, lista_exposicion = [], [], [], [], [], []
                                    if (subtipo_docentes == 1 and not nivelacion) or (subtipo_docentes == 2 and nivelacion):
                                        lista_taller = registros_evaluacion_aprendizaje.filter(evaluacionaprendizaje_id=3)

                                        taller_cumple = TareaSilaboSemanal.objects.filter(query_cumplen, actividad_id=3)
                                        taller_planificado_cumple = taller_cumple.filter(silabosemanal__numsemana__in=lista_taller.values_list('silabosemanal__numsemana', flat=True))
                                        taller_adicional_cumple = taller_cumple.exclude(pk__in=taller_planificado_cumple.values_list('id', flat=True))
                                        taller_no_cumple = TareaSilaboSemanal.objects.filter(silabosemanal_id__in=idsemanas, actividad_id=3).exclude(pk__in=taller_cumple.values_list('id', flat=True))

                                        for x in lista_taller:
                                            _recurso = taller_planificado_cumple.filter(silabosemanal__numsemana=x.silabosemanal.numsemana, status=True).first()  # Creados
                                            if not _recurso: _recurso = taller_planificado_cumple.filter(silabosemanal__numsemana=x.silabosemanal.numsemana, status=False).first()  # Eliminados
                                            cumple = 1
                                            if not _recurso:
                                                cumple = 0
                                                _recurso = taller_no_cumple.filter(silabosemanal__numsemana=x.silabosemanal.numsemana).first()
                                            listado_ACD_no_cumple.append(['ACD', x.id, x.evaluacionaprendizaje.descripcion, x.silabosemanal.silabo.materia.asignatura.nombre, x.silabosemanal.silabo.materia.paralelo, x.silabosemanal.numsemana, x.silabosemanal.fechainiciosemana.strftime("%d-%m-%Y"), x.silabosemanal.fechafinciosemana.strftime("%d-%m-%Y"), _recurso.nombre if _recurso else '', _recurso.fecha_creacion.strftime("%d-%m-%Y") if _recurso else '', cumple, encrypt(x.silabosemanal.silabo.id), _recurso.status if _recurso else ''])
                                        lista_taller_adicional_cumple = [['ACD', nombretipo, x, x.nombre] for x in taller_adicional_cumple]

                                        lista_exposicion = registros_evaluacion_aprendizaje.filter(evaluacionaprendizaje_id=2)
                                        exposicion_cumple = TareaSilaboSemanal.objects.filter(query_cumplen, actividad_id=2)
                                        exposicion_planificado_cumple = exposicion_cumple.filter(silabosemanal__numsemana__in=lista_exposicion.values_list('silabosemanal__numsemana', flat=True))
                                        exposicion_adicional_cumple = exposicion_cumple.exclude(pk__in=exposicion_planificado_cumple.values_list('id', flat=True))
                                        exposicion_no_cumple = TareaSilaboSemanal.objects.filter(silabosemanal_id__in=idsemanas, actividad_id=2).exclude(pk__in=exposicion_cumple.values_list('id', flat=True))

                                        for x in lista_exposicion:
                                            _recurso = exposicion_planificado_cumple.filter(silabosemanal__numsemana=x.silabosemanal.numsemana, status=True).first()  # Creados
                                            if not _recurso: _recurso = exposicion_planificado_cumple.filter(silabosemanal__numsemana=x.silabosemanal.numsemana, status=False).first()  # Eliminados
                                            cumple = 1
                                            if not _recurso:
                                                cumple = 0
                                                _recurso = exposicion_no_cumple.filter(silabosemanal__numsemana=x.silabosemanal.numsemana).first()
                                            listado_ACD_no_cumple.append(['ACD', x.id, x.evaluacionaprendizaje.descripcion, x.silabosemanal.silabo.materia.asignatura.nombre, x.silabosemanal.silabo.materia.paralelo, x.silabosemanal.numsemana, x.silabosemanal.fechainiciosemana.strftime("%d-%m-%Y"), x.silabosemanal.fechafinciosemana.strftime("%d-%m-%Y"), _recurso.nombre if _recurso else '', _recurso.fecha_creacion.strftime("%d-%m-%Y") if _recurso else '', cumple, encrypt(x.silabosemanal.silabo.id), _recurso.status if _recurso else ''])
                                        lista_exposicion_adicional_cumple = [['ACD', nombretipo, x, x.nombre] for x in exposicion_adicional_cumple]

                                    acd_planificar = len(lista_test) + len(lista_taller) + len(lista_exposicion)
                                    acd_planificado_cumple = len(test_cumple) + len(taller_cumple) + len(exposicion_cumple)
                                    listado_acd_adicional_cumple = lista_test_adicional_cumple + lista_taller_adicional_cumple + lista_exposicion_adicional_cumple

                                    totalminimoacd = acd_planificar
                                    listado_actividades_adicional_cumplen += listado_acd_adicional_cumple
                                    minimoacd += totalminimoacd

                            totalacdplanificado += acd_planificado_cumple
                            totalplanificadoacd = acd_planificado_cumple

                            if totalplanificadoacd > totalminimoacd:
                                totalacdmoodle += totalminimoacd
                            else:
                                totalacdmoodle += totalplanificadoacd
                            if estadoparcial == 'CERRADO':
                                if totalplanificadoacd < totalminimoacd:
                                    listamateriasfaltaacd.append([lsilabo.id, lsilabo.materia, totalplanificadoacd, totalminimoacd])

                            if not lsilabo.materia.modeloevaluativo.id in (25, *MODELO_EVALUATIVO_TRANSVERSAL):
                                if listadocomponentes.filter(componente_id=3):

                                    lista_tarea = registros_evaluacion_aprendizaje.filter(evaluacionaprendizaje_id=5)
                                    tarea_cumple = TareaSilaboSemanal.objects.filter(query_cumplen, actividad_id=5)
                                    tarea_planificado_cumple = tarea_cumple.filter(silabosemanal__numsemana__in=lista_tarea.values_list('silabosemanal__numsemana', flat=True))
                                    tarea_adicional_cumple = tarea_cumple.exclude(pk__in=tarea_planificado_cumple.values_list('id', flat=True))
                                    tarea_no_cumple = TareaSilaboSemanal.objects.filter(silabosemanal_id__in=idsemanas, actividad_id=5).exclude(pk__in=tarea_cumple.values_list('id', flat=True))
                                    for x in lista_tarea:
                                        _recurso = tarea_planificado_cumple.filter(silabosemanal__numsemana=x.silabosemanal.numsemana, status=True).first()  # Creados
                                        if not _recurso: _recurso = tarea_planificado_cumple.filter(silabosemanal__numsemana=x.silabosemanal.numsemana, status=False).first()  # Eliminados
                                        cumple = 1
                                        if not _recurso:
                                            cumple = 0
                                            _recurso = tarea_no_cumple.filter(silabosemanal__numsemana=x.silabosemanal.numsemana).first()
                                        listado_AA_no_cumple.append(['AA', x.id, x.evaluacionaprendizaje.descripcion, x.silabosemanal.silabo.materia.asignatura.nombre, x.silabosemanal.silabo.materia.paralelo, x.silabosemanal.numsemana, x.silabosemanal.fechainiciosemana.strftime("%d-%m-%Y"), x.silabosemanal.fechafinciosemana.strftime("%d-%m-%Y"), _recurso.nombre if _recurso else '', _recurso.fecha_creacion.strftime("%d-%m-%Y") if _recurso else '', cumple, encrypt(x.silabosemanal.silabo.id), _recurso.status if _recurso else ''])
                                    lista_tarea_adicional_cumple = [['AA', nombretipo, x, x.nombre] for x in tarea_adicional_cumple]

                                    lista_foro = registros_evaluacion_aprendizaje.filter(evaluacionaprendizaje_id=6)
                                    foro_cumple = ForoSilaboSemanal.objects.filter(query_cumplen)
                                    foro_planificado_cumple = foro_cumple.filter(silabosemanal__numsemana__in=lista_foro.values_list('silabosemanal__numsemana', flat=True))
                                    foro_adicional_cumple = foro_cumple.exclude(pk__in=foro_planificado_cumple.values_list('id', flat=True))
                                    foro_no_cumple = ForoSilaboSemanal.objects.filter(silabosemanal_id__in=idsemanas).exclude(pk__in=foro_cumple.values_list('id', flat=True))
                                    for x in lista_foro:
                                        _recurso = foro_planificado_cumple.filter(silabosemanal__numsemana=x.silabosemanal.numsemana, status=True).first()  # Creados
                                        if not _recurso: _recurso = foro_planificado_cumple.filter(silabosemanal__numsemana=x.silabosemanal.numsemana, status=False).first()  # Eliminados
                                        cumple = 1
                                        if not _recurso:
                                            cumple = 0
                                            _recurso = foro_no_cumple.filter(silabosemanal__numsemana=x.silabosemanal.numsemana).first()
                                        listado_AA_no_cumple.append(['AA', x.id, x.evaluacionaprendizaje.descripcion, x.silabosemanal.silabo.materia.asignatura.nombre, x.silabosemanal.silabo.materia.paralelo, x.silabosemanal.numsemana, x.silabosemanal.fechainiciosemana.strftime("%d-%m-%Y"), x.silabosemanal.fechafinciosemana.strftime("%d-%m-%Y"), _recurso.nombre if _recurso else '', _recurso.fecha_creacion.strftime("%d-%m-%Y") if _recurso else '', cumple, encrypt(x.silabosemanal.silabo.id), _recurso.status if _recurso else ''])
                                    lista_foro_adicional_cumple = [['AA', nombretipo, x, x.nombre] for x in foro_adicional_cumple]

                                    lista_investigacion = registros_evaluacion_aprendizaje.filter(evaluacionaprendizaje_id=7)
                                    investigacion_cumple = TareaSilaboSemanal.objects.filter(query_cumplen, actividad_id=7)
                                    investigacion_planificado_cumple = investigacion_cumple.filter(silabosemanal__numsemana__in=lista_investigacion.values_list('silabosemanal__numsemana', flat=True))
                                    investigacion_adicional_cumple = investigacion_cumple.exclude(pk__in=investigacion_planificado_cumple.values_list('id', flat=True))
                                    investigacion_no_cumple = TareaSilaboSemanal.objects.filter(silabosemanal_id__in=idsemanas, actividad_id=7).exclude(pk__in=investigacion_cumple.values_list('id', flat=True))
                                    for x in lista_investigacion:
                                        _recurso = investigacion_planificado_cumple.filter(silabosemanal__numsemana=x.silabosemanal.numsemana, status=True).first()  # Creados
                                        if not _recurso: _recurso = investigacion_planificado_cumple.filter(silabosemanal__numsemana=x.silabosemanal.numsemana, status=False).first()  # Eliminados
                                        cumple = 1
                                        if not _recurso:
                                            cumple = 0
                                            _recurso = investigacion_no_cumple.filter(silabosemanal__numsemana=x.silabosemanal.numsemana).first()
                                        listado_AA_no_cumple.append(['AA', x.id, x.evaluacionaprendizaje.descripcion, x.silabosemanal.silabo.materia.asignatura.nombre, x.silabosemanal.silabo.materia.paralelo, x.silabosemanal.numsemana, x.silabosemanal.fechainiciosemana.strftime("%d-%m-%Y"), x.silabosemanal.fechafinciosemana.strftime("%d-%m-%Y"), _recurso.nombre if _recurso else '', _recurso.fecha_creacion.strftime("%d-%m-%Y") if _recurso else '', cumple, encrypt(x.silabosemanal.silabo.id), _recurso.status if _recurso else ''])
                                    lista_investigacion_adicional_cumple = [['AA', nombretipo, x, x.nombre] for x in investigacion_adicional_cumple]

                                    lista_caso = registros_evaluacion_aprendizaje.filter(evaluacionaprendizaje_id=8)
                                    caso_cumple = TareaSilaboSemanal.objects.filter(query_cumplen, actividad_id=8)
                                    caso_planificado_cumple = caso_cumple.filter(silabosemanal__numsemana__in=lista_caso.values_list('silabosemanal__numsemana', flat=True))
                                    caso_adicional_cumple = caso_cumple.exclude(pk__in=caso_planificado_cumple.values_list('id', flat=True))
                                    caso_no_cumple = TareaSilaboSemanal.objects.filter(silabosemanal_id__in=idsemanas, actividad_id=8).exclude(pk__in=caso_cumple.values_list('id', flat=True))
                                    for x in lista_caso:
                                        _recurso = caso_planificado_cumple.filter(silabosemanal__numsemana=x.silabosemanal.numsemana, status=True).first()  # Creados
                                        if not _recurso: _recurso = caso_planificado_cumple.filter(silabosemanal__numsemana=x.silabosemanal.numsemana, status=False).first()  # Eliminados
                                        cumple = 1
                                        if not _recurso:
                                            cumple = 0
                                            _recurso = caso_no_cumple.filter(silabosemanal__numsemana=x.silabosemanal.numsemana).first()
                                        listado_AA_no_cumple.append(['AA', x.id, x.evaluacionaprendizaje.descripcion, x.silabosemanal.silabo.materia.asignatura.nombre, x.silabosemanal.silabo.materia.paralelo, x.silabosemanal.numsemana, x.silabosemanal.fechainiciosemana.strftime("%d-%m-%Y"), x.silabosemanal.fechafinciosemana.strftime("%d-%m-%Y"), _recurso.nombre if _recurso else '', _recurso.fecha_creacion.strftime("%d-%m-%Y") if _recurso else '', cumple, encrypt(x.silabosemanal.silabo.id), _recurso.status if _recurso else ''])
                                    lista_caso_adicional_cumple = [['AA', nombretipo, x, x.nombre] for x in caso_adicional_cumple]

                                    aa_planificar = len(lista_tarea) + len(lista_foro) + len(lista_investigacion) + len(lista_caso)
                                    aa_planificado_cumple = len(tarea_cumple) + len(foro_cumple) + len(investigacion_cumple) + len(caso_cumple)
                                    listado_aa_adicional_cumple = lista_tarea_adicional_cumple + lista_foro_adicional_cumple + lista_investigacion_adicional_cumple + lista_caso_adicional_cumple

                                    totalminimoaa = aa_planificar
                                    listado_actividades_adicional_cumplen += listado_aa_adicional_cumple
                                    minimoaa += totalminimoaa

                            totalaaplanificado += aa_planificado_cumple
                            totalplanificadoaa = aa_planificado_cumple

                            if totalplanificadoaa > totalminimoaa:
                                totalaamoodle += totalminimoaa
                            else:
                                totalaamoodle += totalplanificadoaa
                            if estadoparcial == 'CERRADO':
                                if totalplanificadoaa < totalminimoaa:
                                    listamateriasfaltaaa.append([lsilabo.id, lsilabo.materia, totalplanificadoaa, totalminimoaa])

                        if lsilabo.materia.asignaturamalla.horasapeasistotal > 0 and (ltipoprofesor.id == 2 or (ltipoprofesor.id == 1 and 2 not in listadotipoprofesor.values_list('id', flat=True))):
                            if not lsilabo.materia.modeloevaluativo.id in (25, *MODELO_EVALUATIVO_TRANSVERSAL):
                                if listadocomponentes.filter(componente_id=2):
                                    listado_ape = registros_evaluacion_aprendizaje.filter(evaluacionaprendizaje_id__in=[4])
                                    cantidad_ape = listado_ape.count()

                                    practica_cumple = TareaPracticaSilaboSemanal.objects.filter(query_cumplen)
                                    practica_planificada_cumple = practica_cumple.filter(silabosemanal__numsemana__in=listado_ape.values_list('silabosemanal__numsemana', flat=True))
                                    practica_adicional_cumple = practica_cumple.exclude(pk__in=practica_planificada_cumple.values_list('id', flat=True))
                                    practica_no_cumple = TareaPracticaSilaboSemanal.objects.filter(silabosemanal_id__in=idsemanas).exclude(pk__in=practica_cumple.values_list('id', flat=True))

                                    for x in listado_ape:
                                        _recurso = practica_planificada_cumple.filter(silabosemanal__numsemana=x.silabosemanal.numsemana, status=True).first()  # Creados
                                        if not _recurso: _recurso = practica_planificada_cumple.filter(silabosemanal__numsemana=x.silabosemanal.numsemana, status=False).first()  # Eliminados
                                        cumple = 1
                                        if not _recurso:
                                            cumple = 0
                                            _recurso = practica_no_cumple.filter(silabosemanal__numsemana=x.silabosemanal.numsemana).first()
                                        listado_APE_no_cumple.append(['APE', x.id, x.evaluacionaprendizaje.descripcion, x.silabosemanal.silabo.materia.asignatura.nombre, x.silabosemanal.silabo.materia.paralelo, x.silabosemanal.numsemana, x.silabosemanal.fechainiciosemana.strftime("%d-%m-%Y"), x.silabosemanal.fechafinciosemana.strftime("%d-%m-%Y"), _recurso.nombre if _recurso else '', _recurso.fecha_creacion.strftime("%d-%m-%Y") if _recurso else '', cumple, encrypt(x.silabosemanal.silabo.id), _recurso.status if _recurso else ''])
                                    lista_practica_adicional_cumple = [['APE', nombretipo, x, x.nombre] for x in practica_adicional_cumple]

                                    ape_planificar = cantidad_ape
                                    ape_planificado_cumple = len(practica_cumple)
                                    listado_ape_adicional_cumple = lista_practica_adicional_cumple

                                    totalminimoape = ape_planificar
                                    listado_actividades_adicional_cumplen += listado_ape_adicional_cumple
                                    minimoape += totalminimoape

                                    totalapeplanificado += ape_planificado_cumple
                                    totalapeplanificadoape = ape_planificado_cumple

                                tieneape = 1
                                if totalapeplanificadoape > totalminimoape:
                                    totalapemoodle += totalminimoape
                                else:
                                    totalapemoodle += totalapeplanificadoape
                                if estadoparcial == 'CERRADO':
                                    if totalapeplanificadoape < totalminimoape:
                                        listamateriasfaltaape.append([lsilabo.id, lsilabo.materia, totalapeplanificadoape, totalminimoape])

                    if idcompendio in listadolineamiento.values_list('tiporecurso', flat=True):
                        try:
                            porcentajecompendios = 0
                            if totalcompendiosmoodle >= minimocompendio > 0:
                                porcentajecompendios = 100
                            else:
                                porcentajecompendios = round(((100 * totalcompendiosmoodle) / minimocompendio), 2)
                        except ZeroDivisionError:
                            porcentajecompendios = 0
                        if porcentajecompendios > 100:
                            porcentajecompendios = 100

                    if idvideomagistral in listadolineamiento.values_list('tiporecurso', flat=True):
                        try:
                            porcentajevideo = 0
                            if totalvideomoodle >= minimovideo > 0:
                                porcentajevideo = 100
                            else:
                                porcentajevideo = round(((100 * totalvideomoodle) / minimovideo), 2)
                        except ZeroDivisionError:
                            porcentajevideo = 0
                        if porcentajevideo > 100:
                            porcentajevideo = 100

                    if idguiaestudiante in listadolineamiento.values_list('tiporecurso', flat=True):
                        try:
                            porcentajeguiaestudiante = 0
                            if totalguiamoodle >= minimoguia > 0:
                                porcentajevideo = 100
                            else:
                                porcentajeguiaestudiante = round(((100 * totalguiamoodle) / minimoguia), 2)
                        except ZeroDivisionError:
                            porcentajeguiaestudiante = 0
                        if porcentajeguiaestudiante > 100:
                            porcentajeguiaestudiante = 100

                    try:
                        porcentajeacd = 0
                        if totalacdmoodle >= minimoacd > 0:
                            porcentajeacd = 100
                        else:
                            porcentajeacd = round(((100 * totalacdmoodle) / minimoacd), 2)
                    except ZeroDivisionError:
                        porcentajeacd = 0
                    if porcentajeacd > 100:
                        porcentajeacd = 100

                    try:
                        porcentajeaa = 0
                        if totalaamoodle >= minimoaa > 0:
                            porcentajeaa = 100
                        else:
                            porcentajeaa = round(((100 * totalaamoodle) / minimoaa), 2)
                    except ZeroDivisionError:
                        porcentajeaa = 0
                    if porcentajeaa > 100:
                        porcentajeaa = 100

                    if tieneape == 1:
                        try:
                            porcentajeape = 0
                            if totalapemoodle > minimoape > 0:
                                porcentajeape = 100
                            else:
                                porcentajeape = round(((100 * totalapemoodle) / minimoape), 2)
                        except ZeroDivisionError:
                            porcentajeape = 0
                        if porcentajeape > 100:
                            porcentajeape = 100

                    if idcompendio in listadolineamiento.values_list('tiporecurso', flat=True):
                        listado.append([claseactividad, 'COMPENDIO', minimocompendio, totalcompendiosmoodle, porcentajecompendios, 0, 1, listamateriasfaltacompendio, porcentajecompendios, idcompendio, False, json.dumps(listado_COMPENDIO_no_cumple)])
                        resultadominimoplanificar += totalcompendioplanificado
                        resultadoplanificados += totalcompendiosmoodle
                        resultadoporcentajes += porcentajecompendios
                        sumatoriaindice += 1
                    if idvideomagistral in listadolineamiento.values_list('tiporecurso', flat=True):
                        listado.append([claseactividad, 'VIDEOS MAGISTRALES', minimovideo, totalvideomoodle, porcentajevideo, 0, 1, listamateriasfaltavideo, porcentajevideo, idvideomagistral, False, json.dumps(listado_VIDEOMAGISTRAL_no_cumple)])
                        resultadominimoplanificar += totalvideoplanificado
                        resultadoplanificados += totalvideomoodle
                        resultadoporcentajes += porcentajevideo
                        sumatoriaindice += 1
                    if idguiaestudiante in listadolineamiento.values_list('tiporecurso', flat=True):
                        listado.append([claseactividad, 'GUÍA DEL ESTUDIANTE', minimoguia, totalguiamoodle, porcentajeguiaestudiante, 0, 1, listamateriasfaltaguias, porcentajeguiaestudiante, idguiaestudiante, False, json.dumps(listado_GUIAESTUDIANTE_no_cumple)])
                        resultadominimoplanificar += totalguiaplanificado
                        resultadoplanificados += totalguiamoodle
                        resultadoporcentajes += porcentajeguiaestudiante
                        sumatoriaindice += 1

                    if ltipoprofesor.id != 2:
                        listado.append([claseactividad,'ACD',minimoacd,totalacdplanificado,'-' if subtipo_docentes == 1 and nivelacion else estadoparcial,porcentajeacd,2,listamateriasfaltaacd,porcentajeacd, 8, subtipo_docentes == 1 and nivelacion, json.dumps(listado_ACD_no_cumple)])
                        if minimoacd > 0:
                            sumatoriaindice += 1
                        if (subtipo_docentes == 1 and not nivelacion) or (subtipo_docentes == 2 and nivelacion):
                            if not lsilabo.materia.modeloevaluativo.id in MODELO_EVALUATIVO_TRANSVERSAL:
                                listado.append([claseactividad,'AA',minimoaa,totalaaplanificado,estadoparcial,porcentajeaa,2,listamateriasfaltaaa,porcentajeaa, 9, False, json.dumps(listado_AA_no_cumple)])
                                if minimoaa > 0:
                                    sumatoriaindice += 1
                    if tieneape == 1 :
                        listado.append([claseactividad,'APE',minimoape,totalapeplanificado,estadoparcial,porcentajeape,2,listamateriasfaltaape,porcentajeape, 10, False, json.dumps(listado_APE_no_cumple)])
                        if minimoape > 0:
                            sumatoriaindice += 1
                    resultadominimoplanificar += minimoacd
                    resultadominimoplanificar += minimoaa
                    if tieneape == 1:
                        resultadominimoplanificar += minimoape
                    resultadoplanificados += totalacdplanificado
                    resultadoplanificados += totalaaplanificado
                    if tieneape == 1:
                        resultadoplanificados += totalapeplanificado
                    resultadoporcentajes += porcentajeacd
                    if (subtipo_docentes == 1 and not nivelacion) or (subtipo_docentes == 2 and nivelacion):
                        if not lsilabo.materia.modeloevaluativo.id in MODELO_EVALUATIVO_TRANSVERSAL:
                            resultadoporcentajes += porcentajeaa
                    if tieneape == 1:
                        resultadoporcentajes += porcentajeape
                    subtipo_docentes -= 1
        try:
            resultadoporcentajes = round(((resultadoporcentajes) / sumatoriaindice), 2)
        except ZeroDivisionError:
            resultadoporcentajes = 0
        _promedia = False

        if sumatoriaindice > 0:
            _promedia = True

        listado.append([claseactividad,resultadominimoplanificar,resultadoplanificados,resultadoporcentajes,len(result),0,4,[]])
        if esautomatico:
            totalmensual = len(result)
            promedio = resultadoporcentajes
            listado = [totalmensual, promedio]
        # return listado
        return {'listaseguimiento': listado, 'claseactividad': claseactividad, 'planificadas_mes': len(result), 'listado_actividades_adicional_cumplen': listado_actividades_adicional_cumplen, 'periodoposgrado': periodoposgrado, 'promedia': _promedia}
    except Exception as e:
        import sys
        print(e)
        print('Error on line {} - {}'.format(sys.exc_info()[-1].tb_lineno, e))

@register.simple_tag
def contenido_profesor_total(obj, profesor, materia, fechaini, fechafin):
    try:
        from sga.models import DetalleDistributivo, GuiaEstudianteSilaboSemanal, TareaPracticaSilaboSemanal, \
            TipoProfesor, ProfesorMateria, ClaseActividad, Silabo, CompendioSilaboSemanal, VideoMagistralSilaboSemanal, \
            ForoSilaboSemanal, TareaSilaboSemanal, TestSilaboSemanalAdmision, TestSilaboSemanal, \
            DiapositivaSilaboSemanal, MaterialAdicionalSilaboSemanal, TemaAsistencia, SubTemaAsistencia, SubTemaAdicionalAsistencia, DiasNoLaborable, DetalleSilaboSemanalSubtema
        from inno.models import RespuestaPreguntaEncuestaSilaboGrupoEstudiantes
        from django.db import connections
        periodorelacionado = False
        listado = []
        periodo = obj.periodo
        fechaactual = datetime.now().date()
        periodos = [obj.periodo.pk]
        detalledistributivo = DetalleDistributivo.objects.get(criteriodocenciaperiodo=obj,
                                                              distributivo__profesor=profesor, status=True)
        fechasactividades = detalledistributivo.actividaddetalledistributivo_set.filter(status=True)[0]
        fechaini = periodo.inicio if fechaini < periodo.inicio else fechaini
        if obj.periodosrelacionados.exists():
            periodorelacionado = True
            periodos = []
            for per in obj.periodosrelacionados.values_list('id', flat=True):
                periodos.append(per)
        if periodos:
            periodorelacionado = ProfesorMateria.objects.values('id').filter(profesor=profesor, materia=materia,
                                                                             materia__nivel__periodo_id__in=periodos).distinct().exists()

        profesormateria = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__periodo_id__in=periodos,
                                                         materia=materia,
                                                         activo=True, materia__fin__gte=fechasactividades.desde,
                                                         materia__inicio__lte=fechasactividades.hasta).exclude(
            tipoprofesor_id=15).only('materia').distinct()
        for m in profesormateria:
            if not m.materia.tiene_cronograma():
                return 0
        claseactividad = ClaseActividad.objects.filter(detalledistributivo__criteriodocenciaperiodo=obj,
                                                       detalledistributivo__distributivo__profesor=profesor,
                                                       status=True).order_by('inicio', 'dia', 'turno__comienza')

        # para saber total de horas en el mes
        diasclas = claseactividad.values_list('dia', 'turno_id')
        dt = fechaini
        end = fechafin
        step = timedelta(days=1)
        listaretorno = []
        result = []
        while dt <= end:
            dias_nolaborables = obj.periodo.dias_nolaborables(dt)
            if not dias_nolaborables:
                for dclase in diasclas:
                    if dt.isocalendar()[2] == dclase[0]:
                        result.append(dt.strftime('%Y-%m-%d'))
            dt += step
        # if periodo.clasificacion == 1:
        listadotipoprofesor = TipoProfesor.objects.filter(
            pk__in=ProfesorMateria.objects.values_list('tipoprofesor_id').filter(profesor=profesor, materia=materia,
                                                                                 materia__nivel__periodo_id__in=periodos,
                                                                                 tipoprofesor_id__in=[1, 2, 5, 6, 10,
                                                                                                      11, 12, 14, 16],
                                                                                 activo=True,
                                                                                 materia__fin__gte=fechasactividades.desde,
                                                                                 materia__inicio__lte=fechasactividades.hasta).exclude(
                materia__modeloevaluativo_id__in=[26]).distinct())
        resultadominimoplanificar = 0
        resultadoplanificados = 0
        resultadoparciales = '-'
        resultadoporcentajes = 0
        resultadoporcentajessyl = 0
        sumatoriaindice = 0
        sumatoriaindicesyl = 0
        resultadototal = 0
        subtipo_docentes = 0
        listasilabofaltasilabo = []

        porcentajetotalsilabo = 0
        resultadosobre40 = 0
        calculosobre30 = 0

        #---------------------CONFIRMACION DE TEMAS-----------------------#
        # cont = 0
        # porcentajecumplimiento = 0
        # porcentajetotal = 0
        # silabos = Silabo.objects.filter(status=True, materia_id=materia.pk)
        # if silabos:
        #     dias_no_laborales = DiasNoLaborable.objects.values_list('fecha', flat=True).filter(status=True,
        #                                                                                        periodo=periodo)
        #     numeros_semana = []
        #     for fecha in dias_no_laborales:
        #         numero_semana = fecha.isocalendar()[1]
        #         numeros_semana.append(numero_semana)
        #     num_sem_dia_no_laborable = list(dict.fromkeys(numeros_semana))
        #     silabosemanal = silabos.first().silabosemanal_set.filter(status=True)
        #     if silabosemanal:
        #         for silsem in silabosemanal:
        #             unidadsilsem = silsem.temas_seleccionados_planclase()
        #             fechainiciosilabo = silsem.fechainiciosemana
        #             fechafinsilabo = silsem.fechafinciosemana
        #             num_semana_fechainiciosilabo = fechainiciosilabo.isocalendar()[1]
        #             if unidadsilsem:
        #                 for tema in unidadsilsem:
        #                     if fechafinsilabo <= fechaactual:
        #                         cont += 1
        #                         if TemaAsistencia.objects.filter(fecha__lte=fechafinsilabo, tema=tema).exists()  or (num_semana_fechainiciosilabo in num_sem_dia_no_laborable):
        #                             porcentajecumplimiento += 1
        #                     subtemas = silsem.subtemas_silabosemanal(tema.temaunidadresultadoprogramaanalitico)
        #                     if subtemas:
        #                         for subtema in subtemas:
        #                             if fechafinsilabo <= fechaactual:
        #                                 cont += 1
        #                                 if SubTemaAsistencia.objects.filter(fecha__lte=fechafinsilabo, subtema=subtema).exists()  or (num_semana_fechainiciosilabo in num_sem_dia_no_laborable):
        #                                     porcentajecumplimiento += 1
        #                     subtemaadicional = silsem.subtemas_adicionales(tema.id)
        #                     if subtemaadicional:
        #                         for subtemasad in subtemaadicional:
        #                             if fechafinsilabo <= fechaactual:
        #                                 cont += 1
        #                                 if SubTemaAdicionalAsistencia.objects.filter(fecha__lte=fechafinsilabo, subtema=subtemasad).exists()  or (num_semana_fechainiciosilabo in num_sem_dia_no_laborable):
        #                                     porcentajecumplimiento += 1

        cont = 0
        porcentajecumplimiento = 0
        porcentajetotal = 0
        if silabos := Silabo.objects.filter(status=True, materia_id=materia.pk):
            numeros_semana = [fecha.isocalendar()[1] for fecha in periodo.diasnolaborable_set.filter(status=True).values_list('fecha', flat=True)]
            num_sem_dia_no_laborable = list(dict.fromkeys(numeros_semana))
            silabosemanal = silabos.first().silabosemanal_set.filter(status=True)
            if silabosemanal:
                cursor = connections['sga_select'].cursor()
                for silsem in silabosemanal:
                    # unidadsilsem = silsem.temas_seleccionados_planclase()
                    sql_tema = f"""SELECT "sga_detallesilabosemanaltema"."id", "sga_temaunidadresultadoprogramaanalitico"."descripcion", "sga_detallesilabosemanaltema"."temaunidadresultadoprogramaanalitico_id" FROM "sga_detallesilabosemanaltema" INNER JOIN "sga_temaunidadresultadoprogramaanalitico" ON ("sga_detallesilabosemanaltema"."temaunidadresultadoprogramaanalitico_id" = "sga_temaunidadresultadoprogramaanalitico"."id") WHERE ("sga_detallesilabosemanaltema"."silabosemanal_id" = {silsem.pk} AND "sga_temaunidadresultadoprogramaanalitico"."status") ORDER BY "sga_temaunidadresultadoprogramaanalitico"."orden" ASC"""
                    cursor.execute(sql_tema)
                    unidadsilsem = cursor.fetchall()
                    # unidadsilsem = list(silsem.detallesilabosemanaltema_set.select_related('temaunidadresultadoprogramaanalitico').values_list('id','temaunidadresultadoprogramaanalitico__descripcion','temaunidadresultadoprogramaanalitico').filter(temaunidadresultadoprogramaanalitico__status=True).order_by('temaunidadresultadoprogramaanalitico__orden'))
                    fechainiciosilabo = silsem.fechainiciosemana
                    fechafinsilabo = silsem.fechafinciosemana
                    num_semana_fechainiciosilabo = fechainiciosilabo.isocalendar()[1]
                    if unidadsilsem:
                        for tema in unidadsilsem:
                            if fechafinsilabo <= fechaactual:
                                cont += 1
                                if TemaAsistencia.objects.values('id').filter(fecha__lte=fechafinsilabo,tema=tema[0]).exists() or (num_semana_fechainiciosilabo in num_sem_dia_no_laborable):
                                    porcentajecumplimiento += 1
                            subtemas = DetalleSilaboSemanalSubtema.objects.select_related('subtemaunidadresultadoprogramaanalitico').values_list('id', 'subtemaunidadresultadoprogramaanalitico__descripcion').filter(status=True, subtemaunidadresultadoprogramaanalitico__temaunidadresultadoprogramaanalitico=tema[2],subtemaunidadresultadoprogramaanalitico__status=True,subtemaunidadresultadoprogramaanalitico__temaunidadresultadoprogramaanalitico__isnull=False,subtemaunidadresultadoprogramaanalitico__temaunidadresultadoprogramaanalitico__status=True,silabosemanal=silsem).order_by('subtemaunidadresultadoprogramaanalitico__orden')
                            sql_subtemas = f"""SELECT "sga_detallesilabosemanalsubtema"."id", "sga_subtemaunidadresultadoprogramaanalitico"."descripcion" FROM "sga_detallesilabosemanalsubtema" INNER JOIN "sga_subtemaunidadresultadoprogramaanalitico" ON ("sga_detallesilabosemanalsubtema"."subtemaunidadresultadoprogramaanalitico_id" = "sga_subtemaunidadresultadoprogramaanalitico"."id") INNER JOIN "sga_temaunidadresultadoprogramaanalitico" ON ("sga_subtemaunidadresultadoprogramaanalitico"."temaunidadresultadoprogramaanalitico_id" = "sga_temaunidadresultadoprogramaanalitico"."id") WHERE ("sga_detallesilabosemanalsubtema"."silabosemanal_id" = {silsem.pk} AND "sga_detallesilabosemanalsubtema"."status" AND "sga_subtemaunidadresultadoprogramaanalitico"."status" AND "sga_subtemaunidadresultadoprogramaanalitico"."temaunidadresultadoprogramaanalitico_id" = {tema[2]} AND "sga_subtemaunidadresultadoprogramaanalitico"."temaunidadresultadoprogramaanalitico_id" IS NOT NULL AND "sga_temaunidadresultadoprogramaanalitico"."status") ORDER BY "sga_subtemaunidadresultadoprogramaanalitico"."orden" ASC"""
                            cursor.execute(sql_subtemas)
                            subtemas = cursor.fetchall()
                            # subtemas = silsem.subtemas_silabosemanal(tema.temaunidadresultadoprogramaanalitico)
                            for subtema in subtemas:
                                if fechafinsilabo <= fechaactual:
                                    cont += 1
                                    if SubTemaAsistencia.objects.values('id').filter(subtema__silabosemanal=silsem,fecha__lte=fechafinsilabo,subtema=subtema[0]).exists() or ( num_semana_fechainiciosilabo in num_sem_dia_no_laborable):
                                        porcentajecumplimiento += 1
                            # subtemaadicional = silsem.subtemas_adicionales(tema.id)
                            subtemaadicional = silsem.subtemaadicionalessilabo_set.values_list('id', 'subtema').filter(status=True, tema_id=tema[0]).order_by('id')
                            for subtemasad in subtemaadicional:
                                if fechafinsilabo <= fechaactual:
                                    cont += 1
                                    if SubTemaAdicionalAsistencia.objects.values('id').filter(fecha__lte=fechafinsilabo, subtema=subtemasad[0]).exists() or (num_semana_fechainiciosilabo in num_sem_dia_no_laborable):
                                        porcentajecumplimiento += 1

        ####################################################################################################
        # -------------------------------PORCENTAJE DE ENCUESTAS------------------------------------#
        preguntas_con_respuestas = RespuestaPreguntaEncuestaSilaboGrupoEstudiantes.objects.values(
            'pregunta__id', 'pregunta__descripcion'
        ).annotate(
            cantidad_si = Coalesce(Count(Case(When(respuesta='SI', then=1))), Value(0)),
            cantidad_no = Coalesce(Count(Case(When(respuesta='NO', then=1))), Value(0)),
            cantidad_total = F('cantidad_si') + F('cantidad_no'),
            porcentaje = F('cantidad_si') * 100 / F('cantidad_total')
        ).filter(
            ~Q(respuesta__isnull=True), status=True, inscripcionencuestasilabo__materia__id=materia.id)
        suma_total_encuesta = 0
        porcentaje_total_encuesta = 0
        porcentaje_encuesta_sobre30 = 0
        cont_encuesta = 0
        if preguntas_con_respuestas.exists():
            for pregunta in preguntas_con_respuestas:
                suma_total_encuesta += pregunta['porcentaje']
                cont_encuesta += 1
        if cont_encuesta > 0:
            porcentaje_total_encuesta = round((suma_total_encuesta / cont_encuesta), 2)
            porcentaje_encuesta_sobre30 = round(((porcentaje_total_encuesta * 30) / 100), 2)
        else:
            porcentaje_total_encuesta = 0
            porcentaje_encuesta_sobre30 = 0
        ####################################################################################################
        for ltipoprofesor in listadotipoprofesor:
            subtipo_docentes = 1
            nivelacion = False
            listadosilabos = Silabo.objects.filter(status=True, materia_id__in=ProfesorMateria.objects.values_list(
                'materia_id').filter(profesor=profesor, materia__nivel__periodo_id__in=periodos, materia=materia,
                                     tipoprofesor=ltipoprofesor, activo=True, materia__fin__gte=fechasactividades.desde,
                                     materia__inicio__lte=fechasactividades.hasta).distinct())
            if listadosilabos:
                if listadosilabos.filter(materia__asignaturamalla__malla__carrera__coordinacion__id=9).exists():
                    subtipo_docentes += 1
                    nivelacion = True
                    listadosilabos = Silabo.objects.filter(status=True,
                                                           materia_id__in=ProfesorMateria.objects.values_list(
                                                               'materia_id').filter(profesor=profesor, materia=materia,
                                                                                    materia__nivel__periodo_id__in=periodos,
                                                                                    tipoprofesor=ltipoprofesor,
                                                                                    activo=True,
                                                                                    materia__fin__gte=fechasactividades.desde,
                                                                                    materia__inicio__lte=fechasactividades.hasta).exclude(
                                                               materia__asignaturamalla__malla__carrera__coordinacion__id=9).distinct())
                while subtipo_docentes > 0:
                    if not listadosilabos and nivelacion:
                        subtipo_docentes -= 1
                    if subtipo_docentes == 1 and nivelacion:
                        listadosilabos = Silabo.objects.filter(status=True,
                                                               materia_id__in=ProfesorMateria.objects.values_list(
                                                                   'materia_id').filter(profesor=profesor,
                                                                                        materia=materia,
                                                                                        materia__nivel__periodo_id__in=periodos,
                                                                                        tipoprofesor=ltipoprofesor,
                                                                                        activo=True,
                                                                                        materia__fin__gte=fechasactividades.desde,
                                                                                        materia__inicio__lte=fechasactividades.hasta,
                                                                                        materia__asignaturamalla__malla__carrera__coordinacion__id=9).distinct())
                    listadosilabos = listadosilabos.exclude(materia__modeloevaluativo_id__in=[26, 27])
                    totalsilabos = listadosilabos.count()
                    totalsilabosplanificados = listadosilabos.filter(codigoqr=True).count()
                    porcentaje = 0
                    if periodorelacionado:
                        if totalsilabosplanificados >= 1:
                            porcentaje = 100
                    else:
                        try:
                            porcentaje = round(((100 * totalsilabosplanificados) / totalsilabos), 2)
                        except ZeroDivisionError:
                            porcentaje = 0
                    totalcompendioplanificada = 0
                    totalvideoplanificada = 0
                    totalguiaestplanificada = 0
                    totalmaterialplanificada = 0
                    totalcompendiosmoodle = 0
                    totalvideomoodle = 0
                    totalguiaestmoodle = 0
                    totaldiapositivasmoodle = 0
                    totalunidades = 0
                    totalacdplanificado = 0
                    totalacdplanificadosinmigrar = 0
                    totalaaplanificado = 0
                    totalaaplan = 0
                    totalapeplanificado = 0
                    minimoacd = 0
                    minimoaa = 0
                    minimoape = 0
                    tieneape = 0
                    totaldiapositivaplanificada = 0
                    totalmaterialplanificada = 0
                    totalmaterialmoodle = 0
                    totalunidades = 0
                    nombretipo = '{} - NIVELACIÓN'.format(
                        ltipoprofesor.nombre) if subtipo_docentes == 1 and nivelacion else ltipoprofesor.nombre
                    listadolineamiento = ltipoprofesor.lineamientorecursoperiodo_set.filter(periodo_id__in=periodos,
                                                                                            status=True,
                                                                                            nivelacion=True) if subtipo_docentes == 1 and nivelacion else ltipoprofesor.lineamientorecursoperiodo_set.filter(
                        periodo_id__in=periodos, status=True, nivelacion=False)
                    bandera = 0
                    if nombretipo == 'PRÁCTICA':
                        bandera = 1
                    listamateriasfaltaguias = []
                    listamateriasfaltavideo = []
                    listamateriasfaltacompendio = []
                    listamateriasfaltadiapositiva = []
                    listamateriasfaltamaterial = []
                    listamateriasfaltaaa = []
                    listamateriasfaltaacd = []
                    listamateriasfaltaape = []
                    totalminimoacd = 0
                    totalminimoaa = 0
                    totalminimoape = 0
                    totalaamoodle = 0
                    totalacdmoodle = 0
                    totalapemoodle = 0
                    listamateriasfaltadiapositiva = []
                    listamateriasfaltamaterial = []
                    iddiapositiva = 2
                    idmateriales = 11
                    for lsilabo in listadosilabos:
                        # ini -- para saber cuantas unidades han cerrado
                        materiaplanificacion = lsilabo.materia.planificacionclasesilabo_materia_set.filter(
                            status=True).first()
                        listadoparciales = materiaplanificacion.tipoplanificacion.planificacionclasesilabo_set.values_list(
                            'parcial', 'fechafin').filter(status=True).distinct('parcial').order_by('parcial',
                                                                                                    '-fechafin').exclude(
                            parcial=None)
                        if nivelacion:
                            fechamaximalimite = fechasactividades.hasta
                        else:
                            fechamaximalimite = fechafin
                        parciales = listadoparciales.values_list('parcial', 'fechafin', 'fechainicio'). \
                            filter(Q(status=True),
                                   Q(fechafin__lte=fechamaximalimite) | Q(fechainicio__lte=fechamaximalimite)). \
                            distinct('parcial').order_by('parcial', '-fechafin')
                        listaparcialterminadas = []
                        estadoparcial = 'ABIERTO'
                        idparcial = 1
                        fechaparcial = ''
                        for sise in parciales:
                            if sise[1] <= fechafin or sise[2] <= fechafin:
                                listaparcialterminadas.append(sise[0])
                        if not lsilabo.codigoqr:
                            listasilabofaltasilabo.append([2, lsilabo.id, lsilabo.materia, 0, 1])
                        listaunidadterminadas = []
                        silabosemanaluni = lsilabo.silabosemanal_set.values_list(
                            'detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden',
                            'fechafinciosemana').filter(status=True).distinct(
                            'detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden').order_by(
                            'detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden',
                            '-fechafinciosemana')
                        for sise in silabosemanaluni:
                            # if sise[1] >= fechaini and sise[1] <= fechafin:
                            if sise[0]:
                                if sise[1] <= fechafin:
                                    if not sise[0] in listaunidadterminadas:
                                        listaunidadterminadas.append(sise[0])
                        if not listaunidadterminadas:
                            listaunidadterminadas.append(1)
                        # fin --

                        ############################################################################################

                        # silabosemanal = lsilabo.silabosemanal_set.filter(fechafinciosemana__range=(fechaini, fechafin),detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden__in=listaunidadterminadas,status=True)
                        silabosemanal = lsilabo.silabosemanal_set.filter(
                            detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden__in=listaunidadterminadas,
                            detallesilabosemanaltema__status=True, status=True).distinct()
                        totaltemas = 0
                        totalunidades = len(listaunidadterminadas)
                        runidad = []
                        unidades = silabosemanal.filter(status=True).values_list(
                            'detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico_id',
                            flat=True).distinct()
                        for silabosemana in silabosemanal:
                            for u in unidades:
                                if not u in runidad:
                                    runidad.append(u)
                                    totaltemas += len(silabosemana.temas_silabounidad_fecha(u, fechafin))
                                    #########################################

                        # para sacar diapositivas
                        iddiapositiva = 2
                        if iddiapositiva in listadolineamiento.values_list('tiporecurso', flat=True):
                            if lsilabo.materia.nivel.periodo.lineamientorecursoperiodo_set.exists():
                                totaldiapositivas = DiapositivaSilaboSemanal.objects.filter(
                                    silabosemanal_id__in=silabosemanal.values_list('id'),
                                    iddiapositivamoodle__gt=0,
                                    status=True).count()
                                multiplicador = len(listaparcialterminadas)
                                busc = lsilabo.materia.nivel.periodo.lineamientorecursoperiodo_set.filter(
                                    tipoprofesor_id__in=lsilabo.materia.profesormateria_set.values_list(
                                        'tipoprofesor').filter(status=True, profesor=profesor,
                                                               tipoprofesor=ltipoprofesor),
                                    tiporecurso=2, status=True)
                                if subtipo_docentes == 1 and nivelacion:
                                    totalminimoacd = 0
                                    busc = busc.filter(nivelacion=True)
                                    for lineaminetoacd in busc.filter(tiporecurso=iddiapositiva):
                                        if lineaminetoacd.aplicapara == 1:
                                            multiplicador = totalunidades
                                        elif lineaminetoacd.aplicapara == 2:
                                            multiplicador = totaltemas
                                totaldiapositivaplan = busc[0].cantidad * multiplicador
                                totaldiapositivaplanificada += totaldiapositivaplan

                                if totaldiapositivas > totaldiapositivaplan:
                                    totaldiapositivasmoodle += totaldiapositivaplan
                                else:
                                    totaldiapositivasmoodle += totaldiapositivas

                                listamateriasfaltadiapositiva.append(
                                    [1, lsilabo.id, lsilabo.materia, totaldiapositivas,
                                     totaldiapositivaplan])

                        # para sacar materialcomplementario
                        idmateriales = 11
                        if idmateriales in listadolineamiento.values_list('tiporecurso', flat=True):
                            if lsilabo.materia.nivel.periodo.lineamientorecursoperiodo_set.exists():
                                totalmateriales = MaterialAdicionalSilaboSemanal.objects.filter(
                                    silabosemanal_id__in=silabosemanal.values_list('id'),
                                    idmaterialesmoodle__gt=0,
                                    status=True).count()
                                multiplicador = len(listaparcialterminadas)
                                lsilabo.materia.nivel.periodo.lineamientorecursoperiodo_set.filter(
                                    tipoprofesor_id__in=lsilabo.materia.profesormateria_set.values_list(
                                        'tipoprofesor').filter(status=True, profesor=profesor,
                                                               tipoprofesor=ltipoprofesor), tiporecurso=11,
                                    status=True)

                                busc = lsilabo.materia.nivel.periodo.lineamientorecursoperiodo_set.filter(
                                    tipoprofesor_id__in=lsilabo.materia.profesormateria_set.values_list(
                                        'tipoprofesor').filter(status=True, profesor=profesor,
                                                               tipoprofesor=ltipoprofesor),
                                    tiporecurso=11, status=True)
                                if subtipo_docentes == 1 and nivelacion:
                                    totalminimoacd = 0
                                    busc = busc.filter(nivelacion=True)
                                    for lineaminetoacd in busc.filter(tiporecurso=iddiapositiva):
                                        if lineaminetoacd.aplicapara == 1:
                                            multiplicador = totalunidades
                                        elif lineaminetoacd.aplicapara == 2:
                                            multiplicador = totaltemas
                                else:
                                    busc = busc.exclude(nivelacion=True)
                                totalmaterialplan = busc[0].cantidad * multiplicador
                                totalmaterialplanificada += totalmaterialplan
                                if totalmateriales > totalmaterialplan:
                                    totalmaterialmoodle += totalmaterialplan
                                else:
                                    totalmaterialmoodle += totalmateriales

                                listamateriasfaltamaterial.append(
                                    [2, lsilabo.id, lsilabo.materia, totalmateriales, totalmaterialplan])

                        ########################################
                        # para sacar compendios
                        idcompendio = 1
                        if idcompendio in listadolineamiento.values_list('tiporecurso', flat=True):
                            totalcompendios = CompendioSilaboSemanal.objects.filter(
                                silabosemanal_id__in=silabosemanal.values_list('id'), idmcompendiomoodle__gt=0,
                                status=True).count()
                            totalcompendioplan = lsilabo.materia.nivel.periodo.lineamientorecursoperiodo_set.filter(
                                tipoprofesor_id__in=lsilabo.materia.profesormateria_set.values_list(
                                    'tipoprofesor').filter(status=True, materia=materia), tiporecurso=1, status=True)[
                                                     0].cantidad * len(
                                listaunidadterminadas)
                            totalcompendioplanificada += totalcompendioplan
                            if totalcompendios > totalcompendioplan:
                                totalcompendiosmoodle += totalcompendioplan
                            else:
                                totalcompendiosmoodle += totalcompendios
                            if totalcompendios < totalcompendioplan:
                                listamateriasfaltacompendio.append(
                                    [lsilabo.id, lsilabo.materia, totalcompendios, totalcompendioplan])

                        # para sacar videomagistral
                        idvideomagistral = 12
                        if idvideomagistral in listadolineamiento.values_list('tiporecurso', flat=True):
                            totalvideos = VideoMagistralSilaboSemanal.objects.filter(
                                silabosemanal_id__in=silabosemanal.values_list('id'), idvidmagistralmoodle__gt=0,
                                status=True).count()
                            totalvideoplan = lsilabo.materia.nivel.periodo.lineamientorecursoperiodo_set.filter(
                                tipoprofesor_id__in=lsilabo.materia.profesormateria_set.values_list(
                                    'tipoprofesor').filter(status=True, materia=materia), tiporecurso=12, status=True)[
                                                 0].cantidad * len(
                                listaunidadterminadas)
                            totalvideoplanificada += totalvideoplan
                            if totalvideos > totalvideoplan:
                                totalvideomoodle += totalvideoplan
                            else:
                                totalvideomoodle += totalvideos
                            if totalvideos < totalvideoplan:
                                listamateriasfaltavideo.append(
                                    [lsilabo.id, lsilabo.materia, totalvideos, totalvideoplan])

                        # para sacar guiaestudiante
                        idguiaestudiante = 4
                        if idguiaestudiante in listadolineamiento.values_list('tiporecurso', flat=True):
                            totalguiaestudiante = GuiaEstudianteSilaboSemanal.objects.filter(
                                silabosemanal_id__in=silabosemanal.values_list('id'), idguiaestudiantemoodle__gt=0,
                                status=True).count()
                            totalguiaestudianteplan = \
                                lsilabo.materia.nivel.periodo.lineamientorecursoperiodo_set.filter(
                                    tipoprofesor_id__in=lsilabo.materia.profesormateria_set.values_list(
                                        'tipoprofesor').filter(status=True, materia=materia), tiporecurso=4,
                                    status=True)[0].cantidad * len(
                                    listaunidadterminadas)
                            totalguiaestplanificada += totalguiaestudianteplan
                            if totalguiaestudiante > totalguiaestudianteplan:
                                totalguiaestmoodle += totalguiaestudianteplan
                            else:
                                totalguiaestmoodle += totalguiaestudiante
                            if totalguiaestudiante < totalguiaestudianteplan:
                                listamateriasfaltaguias.append(
                                    [lsilabo.id, lsilabo.materia, totalguiaestudiante, totalguiaestudianteplan])

                        # para sacar los compenentes acd ,aa ,ape
                        materiaplanificacion = lsilabo.materia.planificacionclasesilabo_materia_set.filter(status=True)[
                            0]
                        listadoparciales = materiaplanificacion.tipoplanificacion.planificacionclasesilabo_set.values_list(
                            'parcial', 'fechafin').filter(status=True).distinct('parcial').order_by('parcial',
                                                                                                    '-fechafin').exclude(
                            parcial=None)
                        if obj.periodosrelacionados.exists():
                            if nivelacion:
                                fecha_limite = fechasactividades.hasta + timedelta(days=30)
                            else:
                                fecha_limite = fechafin + timedelta(days=30)
                            parciales = listadoparciales.values_list('parcial', 'fechafin').filter(status=True,
                                                                                                   fechafin__lte=fecha_limite).distinct(
                                'parcial').order_by('parcial', '-fechafin')
                        else:
                            parciales = listadoparciales.values_list('parcial', 'fechafin', 'fechainicio').filter(
                                Q(status=True), Q(fechafin__lte=fechafin) | Q(fechainicio__lte=fechafin)).distinct(
                                'parcial').order_by('parcial', '-fechafin')
                        listaparcialterminadas = []
                        estadoparcial = 'ABIERTO'
                        idparcial = 1 if not obj.periodo.tipo.id in [3, 4] else 0
                        fechaparcial = ''
                        for sise in parciales:
                            if obj.periodosrelacionados.exists():
                                idparcial = sise[0]
                                listaparcialterminadas.append(sise[0])
                            else:
                                if sise[1] <= fechafin or sise[2] <= fechafin:
                                    idparcial = sise[0]
                                    listaparcialterminadas.append(sise[0])
                        for lpar in listadoparciales:
                            if listadoparciales.order_by('-parcial')[0][0] == lpar[0]:
                                if fechafin >= lpar[1]:
                                    estadoparcial = 'CERRADO'
                            if lpar[0] == idparcial:
                                fechaparcial = lpar[1]

                        if periodo.tipo.id not in [3, 4]:
                            listadocomponentes = lsilabo.materia.nivel.periodo.evaluacioncomponenteperiodo_set.select_related(
                                'componente').filter(nivelacion=True, parcial__in=listaparcialterminadas,
                                                     status=True) if subtipo_docentes == 1 and nivelacion else lsilabo.materia.nivel.periodo.evaluacioncomponenteperiodo_set.select_related(
                                'componente').filter(parcial__in=listaparcialterminadas, status=True)
                        else:
                            listadocomponentes = lsilabo.materia.nivel.periodo.evaluacioncomponenteperiodo_set.select_related(
                                'componente').filter(status=True)

                        # para sacar todos los silabos semanales segun fecha fin del parcial
                        silabosemanalparcial = lsilabo.silabosemanal_set.filter(fechafinciosemana__lte=fechaparcial,
                                                                                status=True)
                        if lsilabo.materia.modeloevaluativo.id != 25:
                            if listadocomponentes.filter(componente_id=1):
                                multiplicador = len(listaparcialterminadas)
                                if subtipo_docentes == 1 and nivelacion:
                                    totalminimoacd = 0
                                    for lineaminetoacd in listadolineamiento.filter(tiporecurso=7):
                                        if lineaminetoacd.aplicapara == 1:
                                            multiplicador = totalunidades
                                        elif lineaminetoacd.aplicapara == 2:
                                            multiplicador = totaltemas
                                        totalminimoacd += lineaminetoacd.cantidad * multiplicador
                                else:
                                    totalminimoacd = listadocomponentes.filter(componente_id=1,
                                                                               nivelacion=False).first().cantidad * multiplicador
                                minimoacd += totalminimoacd
                        totalacdplanificadotar = 0
                        totalacdplanificadosinmigrartar = 0
                        if (subtipo_docentes == 1 and not nivelacion) or (subtipo_docentes == 2 and nivelacion):
                            totalacdplanificadotar = TareaSilaboSemanal.objects.filter(
                                silabosemanal_id__in=silabosemanalparcial.values_list('id'), idtareamoodle__gt=0,
                                actividad_id__in=[2, 3], status=True).count()
                            totalacdplanificadosinmigrartar = TareaSilaboSemanal.objects.filter(
                                silabosemanal_id__in=silabosemanalparcial.values_list('id'),
                                actividad_id__in=[2, 3], status=True).count()

                        if subtipo_docentes == 1 and nivelacion:
                            totalacdplanificadotest = TestSilaboSemanalAdmision.objects.filter(
                                silabosemanal_id__in=silabosemanalparcial.values_list('id'), idtestmoodle__gt=0,
                                status=True).count()
                            totalacdplanificadosinmigrartest = TestSilaboSemanalAdmision.objects.filter(
                                silabosemanal_id__in=silabosemanalparcial.values_list('id'),
                                status=True).count()

                        else:
                            totalacdplanificadotest = TestSilaboSemanal.objects.filter(
                                silabosemanal_id__in=silabosemanalparcial.values_list('id'), idtestmoodle__gt=0,
                                status=True).count()
                            totalacdplanificadosinmigrartest = TestSilaboSemanal.objects.filter(
                                silabosemanal_id__in=silabosemanalparcial.values_list('id'),
                                status=True).count()
                        totalacdplanificado += totalacdplanificadotar + totalacdplanificadotest
                        totalplanificadoacd = totalacdplanificadotar + totalacdplanificadotest

                        totalacdplanificadosinmigrar += totalacdplanificadosinmigrartar + totalacdplanificadosinmigrartest

                        if totalplanificadoacd > totalminimoacd:
                            totalacdmoodle += totalminimoacd
                        else:
                            totalacdmoodle += totalplanificadoacd
                        if estadoparcial == 'CERRADO':
                            if totalplanificadoacd < totalminimoacd:
                                listamateriasfaltaacd.append(
                                    [lsilabo.id, lsilabo.materia, totalplanificadoacd, totalminimoacd])

                        totalaaplanificadosinmigrartar = 0
                        if lsilabo.materia.modeloevaluativo.id != 25:
                            if listadocomponentes.filter(componente_id=3):
                                totalminimoaa = listadocomponentes.filter(componente_id=3)[0].cantidad * len(
                                    listaparcialterminadas)
                                minimoaa += totalminimoaa
                        totalplanificadoaatar = TareaSilaboSemanal.objects.filter(
                            silabosemanal_id__in=silabosemanalparcial.values_list('id'), idtareamoodle__gt=0,
                            actividad_id__in=[5, 7, 8], status=True).count()
                        totalplanificadoaasinmigrartar = TareaSilaboSemanal.objects.filter(
                            silabosemanal_id__in=silabosemanalparcial.values_list('id'),
                            actividad_id__in=[5, 7, 8], status=True).count()
                        totalplanificadoaafor = ForoSilaboSemanal.objects.filter(
                            silabosemanal_id__in=silabosemanalparcial.values_list('id'), idforomoodle__gt=0,
                            status=True).count()
                        totalplanificadoaasinmigrarfor = ForoSilaboSemanal.objects.filter(
                            silabosemanal_id__in=silabosemanalparcial.values_list('id'),
                            status=True).count()
                        totalaaplanificado += totalplanificadoaatar + totalplanificadoaafor
                        totalplanificadoaa = totalplanificadoaatar + totalplanificadoaafor
                        totalaaplanificadosinmigrartar += totalplanificadoaasinmigrartar + totalplanificadoaasinmigrarfor

                        if totalplanificadoaa > totalminimoaa:
                            totalaamoodle += totalminimoaa
                        else:
                            totalaamoodle += totalplanificadoaa
                        if estadoparcial == 'CERRADO':
                            if totalplanificadoaa < totalminimoaa:
                                listamateriasfaltaaa.append(
                                    [lsilabo.id, lsilabo.materia, totalplanificadoaa, totalminimoaa])
                        totalapeplanificadosinmigrartar = 0
                        if lsilabo.materia.asignaturamalla.horasapeasistotal > 0:
                            if lsilabo.materia.modeloevaluativo.id != 25:
                                if listadocomponentes.filter(componente_id=2):
                                    totalminimoape = listadocomponentes.filter(componente_id=2)[0].cantidad * len(
                                        listaparcialterminadas)
                                    minimoape += totalminimoape
                                totalapeplanificadotar = TareaPracticaSilaboSemanal.objects.filter(
                                    silabosemanal_id__in=silabosemanalparcial.values_list('id'),
                                    idtareapracticamoodle__gt=0, status=True)
                                totalapeplanificadosinmigrartar = TareaPracticaSilaboSemanal.objects.filter(
                                    silabosemanal_id__in=silabosemanalparcial.values_list('id'), status=True).count()

                                totalapeplanificado += totalapeplanificadotar.count()
                                totalaaplanificadosinmigrartar += totalapeplanificadosinmigrartar
                                # totalapeplanificadoape = totalapeplanificadotar.count()
                                totalapeplanificadoape = totalapeplanificadotar.values_list(
                                    'silabosemanal__parcial').distinct().count()
                                tieneape = 1
                                if totalapeplanificadoape > totalminimoape:
                                    totalapemoodle += totalminimoape
                                else:
                                    totalapemoodle += totalapeplanificadoape
                                if estadoparcial == 'CERRADO':
                                    if totalapeplanificadoape < totalminimoape:
                                        listamateriasfaltaape.append(
                                            [lsilabo.id, lsilabo.materia, totalapeplanificadoape, totalminimoape])
                    ##################################################

                    if iddiapositiva in listadolineamiento.values_list('tiporecurso', flat=True):
                        if periodorelacionado:
                            porcentajediapositivas = 0
                            if totaldiapositivasmoodle >= 1:
                                porcentajediapositivas = 100
                        else:
                            try:
                                porcentajediapositivas = round(
                                    ((100 * totaldiapositivasmoodle) / totaldiapositivaplanificada), 2)
                            except ZeroDivisionError:
                                porcentajediapositivas = 0
                    if idmateriales in listadolineamiento.values_list('tiporecurso', flat=True):
                        if periodorelacionado:
                            porcentajematerial = 0
                            if totalmaterialmoodle >= 1:
                                porcentajematerial = 100
                        else:
                            try:
                                porcentajematerial = round(((100 * totalmaterialmoodle) / totalmaterialplanificada), 2)
                            except ZeroDivisionError:
                                porcentajematerial = 0
                    resultadominimoplanificar += totalsilabos
                    resultadoplanificados += totalsilabosplanificados
                    resultadoporcentajessyl += porcentaje
                    sumatoriaindicesyl += 1
                    ##################################################
                    if idcompendio in listadolineamiento.values_list('tiporecurso', flat=True):
                        if periodorelacionado:
                            porcentajecompendios = 0
                            if totalcompendiosmoodle >= 1:
                                porcentajecompendios = 100
                        else:
                            try:
                                porcentajecompendios = round(
                                    ((100 * totalcompendiosmoodle) / totalcompendioplanificada), 2)
                            except ZeroDivisionError:
                                porcentajecompendios = 0
                    if idvideomagistral in listadolineamiento.values_list('tiporecurso', flat=True):
                        if periodorelacionado:
                            porcentajevideo = 0
                            if totalvideomoodle >= 1:
                                porcentajevideo = 100
                        else:
                            try:
                                porcentajevideo = round(((100 * totalvideomoodle) / totalvideoplanificada), 2)
                            except ZeroDivisionError:
                                porcentajevideo = 0

                    if idguiaestudiante in listadolineamiento.values_list('tiporecurso', flat=True):
                        if periodorelacionado:
                            porcentajeguiaestudiante = 0
                            if totalguiaestmoodle >= 1:
                                porcentajeguiaestudiante = 100
                            else:
                                if totalguiaestplanificada == 0:
                                    porcentajeguiaestudiante = 100
                        else:
                            if totalguiaestplanificada == 0:
                                porcentajeguiaestudiante = 100
                            else:
                                try:
                                    porcentajeguiaestudiante = round(
                                        ((100 * totalguiaestmoodle) / totalguiaestplanificada), 2)
                                except ZeroDivisionError:
                                    porcentajeguiaestudiante = 0
                    try:
                        porcentajeacd = 0
                        if periodorelacionado:
                            if totalacdmoodle >= 1:
                                porcentajeacd = 100
                        else:
                            if totalacdmoodle > minimoacd:
                                porcentajeacd = 100
                            else:
                                porcentajeacd = round(((100 * totalacdmoodle) / minimoacd), 2)
                    except ZeroDivisionError:
                        porcentajeacd = 0
                    if porcentajeacd > 100:
                        porcentajeacd = 100
                    if estadoparcial == 'ABIERTO' and not nivelacion:
                        porcentajeacd = 100
                    try:
                        porcentajeaa = 0
                        if periodorelacionado:
                            if totalaamoodle >= 1:
                                porcentajeaa = 100
                        else:
                            if totalaamoodle > minimoaa:
                                porcentajeaa = 100
                            else:
                                porcentajeaa = round(((100 * totalaamoodle) / minimoaa), 2)
                    except ZeroDivisionError:
                        porcentajeaa = 0
                    if porcentajeaa > 100:
                        porcentajeaa = 100
                    if estadoparcial == 'ABIERTO':
                        porcentajeaa = 100

                    if tieneape == 1:
                        try:
                            porcentajeape = 0
                            if periodorelacionado:
                                if totalapemoodle >= 1:
                                    porcentajeape = 100
                            else:
                                if totalapemoodle > minimoape:
                                    porcentajeape = 100
                                else:
                                    porcentajeape = round(((100 * totalapemoodle) / minimoape), 2)
                        except ZeroDivisionError:
                            porcentajeape = 0
                        if porcentajeape > 100:
                            porcentajeape = 100
                        if estadoparcial == 'ABIERTO':
                            porcentajeape = 100

                    ###########################################

                    if iddiapositiva in listadolineamiento.values_list('tiporecurso', flat=True):
                        resultadominimoplanificar += totaldiapositivaplanificada
                        resultadoplanificados += totaldiapositivasmoodle
                        resultadoporcentajessyl += porcentajediapositivas
                        sumatoriaindicesyl += 1
                    if idmateriales in listadolineamiento.values_list('tiporecurso', flat=True):
                        resultadominimoplanificar += totalmaterialplanificada
                        resultadoplanificados += totalmaterialmoodle
                        resultadoporcentajessyl += porcentajematerial
                        sumatoriaindicesyl += 1

                    ############################################
                    if idcompendio in listadolineamiento.values_list('tiporecurso', flat=True):
                        resultadominimoplanificar += totalcompendioplanificada
                        resultadoplanificados += totalcompendiosmoodle
                        resultadoporcentajes += porcentajecompendios
                        sumatoriaindice += 1
                    if idvideomagistral in listadolineamiento.values_list('tiporecurso', flat=True):
                        resultadominimoplanificar += totalvideoplanificada
                        resultadoplanificados += totalvideomoodle
                        resultadoporcentajes += porcentajevideo
                        sumatoriaindice += 1
                    if idguiaestudiante in listadolineamiento.values_list('tiporecurso', flat=True):
                        resultadominimoplanificar += totalguiaestplanificada
                        resultadoplanificados += totalguiaestmoodle
                        resultadoporcentajes += porcentajeguiaestudiante
                        sumatoriaindice += 1
                    sumatoriaindice += 1
                    if (subtipo_docentes == 1 and not nivelacion) or (subtipo_docentes == 2 and nivelacion):
                        sumatoriaindice += 1
                    if tieneape == 1:
                        sumatoriaindice += 1
                    resultadominimoplanificar += minimoacd
                    resultadominimoplanificar += minimoaa
                    if tieneape == 1:
                        resultadominimoplanificar += minimoape
                    resultadoplanificados += totalacdplanificado
                    resultadoplanificados += totalaaplanificado
                    if tieneape == 1:
                        resultadoplanificados += totalapeplanificado
                    resultadoporcentajes += porcentajeacd
                    if (subtipo_docentes == 1 and not nivelacion) or (subtipo_docentes == 2 and nivelacion):
                        resultadoporcentajes += porcentajeaa
                    if tieneape == 1:
                        resultadoporcentajes += porcentajeape
                    subtipo_docentes -= 1
        try:
            resultadoporcentajes = round(((resultadoporcentajes) / sumatoriaindice), 2)
        except ZeroDivisionError:
            resultadoporcentajes = 0

        try:
            resultadoporcentajessyl = round(((resultadoporcentajessyl) / sumatoriaindicesyl), 2)
        except ZeroDivisionError:
            resultadoporcentajessyl = 0
        try:
            resultadototal = round(((resultadoporcentajes + resultadoporcentajessyl) / 2), 2)
        except ZeroDivisionError:
            resultadototal = 0

        try:
            resultadosobre40 = round(((resultadototal * 40) / 100), 2)
        except ZeroDivisionError:
            resultadosobre40 = 0

        try:
            ######CONFIRMACION TEMAS
            percent = round((porcentajecumplimiento / cont), 2)
            percent = round((percent * 100), 2)
            calculosobre30 = round(((percent * 30) / 100), 2)
        except ZeroDivisionError:
            percent = 0
            calculosobre30 = 0
        ######SUMATORIA PUNTAJE SILABO
        porcentajetotalsilabo = round((resultadosobre40 + calculosobre30 + porcentaje_encuesta_sobre30), 2)
        #####TOTAL SIN CONTAR ENCUESTA
        # porcentajetotalsilabo = round(((porcentajetotalsilabo *100) / 70), 2)

        listado.append(
            [claseactividad, resultadominimoplanificar, resultadoplanificados, resultadoporcentajes, len(result), 0, 4,
             [], resultadosobre40, resultadototal, calculosobre30, porcentaje_encuesta_sobre30, porcentajetotalsilabo])
        return listado
    except Exception as e:
        import sys
        print(e)
        print('Error on line {} - {}'.format(sys.exc_info()[-1].tb_lineno, e))

@register.simple_tag
def cronograma_silabo_v2(self, fecha):
    from sga.funciones import daterange
    from sga.models import PlanificacionClaseSilabo
    try:
        if self.tiene_silabo():
            __pk__ = []
            if self.tiene_cronograma() and self.silabo_actual().esta_aprobado():
                for index, value in enumerate(PlanificacionClaseSilabo.objects.filter(Q(tipoplanificacion__planificacionclasesilabo_materia__materia=self, status=True, fechainicio__lte=fecha)).order_by('-fechainicio')):
                    if index == 2:
                        for d in daterange(value.fechainicio, value.fechafin + timedelta(1)):
                            if self.nivel.periodo.dias_nolaborables(d):
                                __pk__.append(value.pk)  # Si en la tercera semana hay feriado lo incluye
                                break
                        break
                    else:
                        __pk__.append(value.pk)
                return PlanificacionClaseSilabo.objects.filter(pk__in=__pk__).order_by('-fechainicio')
        return []
    except Exception as ex:
        return PlanificacionClaseSilabo.objects.filter(Q(tipoplanificacion__planificacionclasesilabo_materia__materia=self, status=True, fechainicio__lte=fecha, fechainicio__gte=fecha - timedelta(weeks=2))).order_by('-fechainicio')


def tipo_archivo(namefile=''):
    ext = namefile[namefile.rfind("."):].lower()
    if ext in ['.pdf']:
        return 'pdf'
    elif ext in ['.png', '.jpg', '.jpeg', '.svg']:
        return 'img'
    elif ext in ['.xls', '.xlsx', '.xlsx', '.xlsb']:
        return 'excel'
    elif ext in ['.docx', '.doc']:
        return 'word'
    else:
        return 'otro'

def clean_text(html_content=''):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    solo_texto = soup.get_text().replace('\n', '<br>')
    return solo_texto

def es_numero_par(numero):
    return numero % 2 == 0

def clean_text_parsereportlab(html_content=''):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    solo_texto = soup.get_text().replace('\n', '<br/>')
    return solo_texto

def clean_text_coma(html_content=''):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    solo_texto = soup.get_text().strip()
    # Elimina solo el primer carácter de nueva línea
    if solo_texto.startswith('\n'):
        solo_texto = solo_texto[1:]
    solo_texto = solo_texto.replace('\n', ', ').replace(', , ', ', ')
    return solo_texto.capitalize()

def tiene_solicitud_de_ingreso_titulacion_posgrado(pk):
    from sga.models import TemaTitulacionPosgradoMatricula
    from posgrado.models import SolicitudIngresoTitulacionPosgrado
    eTemaTitulacionPosgradoMatricula = TemaTitulacionPosgradoMatricula.objects.get(pk=pk)
    eSolicitudIngresoTitulacionPosgrado = SolicitudIngresoTitulacionPosgrado.objects.filter(status=True,matricula = eTemaTitulacionPosgradoMatricula.matricula,firmado=True)
    return eSolicitudIngresoTitulacionPosgrado if eSolicitudIngresoTitulacionPosgrado.exists() else None

def calculaporcentaje(var, value):
    return round((value / var) * 100, 2)

def asignacion_url(url_entrada='', url_offline=''):
    return url_offline if url_offline else url_entrada

def es_palabra_femenina(palabra=''):
    #Aumentar sufijos según se requiera para mejorar la detección
    sufijos_femeninos = ['a', 'ión', 'ad', 'umbre', 'ie', 'z']
    palabra = str(palabra).lower()
    return any(palabra.endswith(sufijo) for sufijo in sufijos_femeninos)
def articulo_palabra(palabra='', femenino='la', masculino='el'):
    #Aumentar sufijos según se requiera para mejorar la detección
    if es_palabra_femenina(str(palabra)):
        return femenino
    return masculino

def fecha_natural(fecha=datetime.now().date()):
    # Para mostrar todo el formato usar:format='log'
    format_custom = "d 'de' MMMM 'del' y"
    return format_date(fecha, format=format_custom, locale='es')

def mes_fecha_natural(fecha=datetime.now().date()):
    format_custom = "MMMM"
    return format_date(fecha, format=format_custom, locale='es')

@register.simple_tag
def persona_genero(persona, masculino='el', femenino='la'):
    sexo = persona.sexo
    palabra = masculino if not sexo or sexo.id == 2 else femenino
    return palabra

@register.simple_tag
def docentes_practicas_estudiantes(ins, periodo, itinerario):
    from sga.models import MateriaAsignada, Matricula
    from django.db import connections
    nivmal = ''
    nomasignatura = ''
    profesor = ''
    id_asigmal = 0

    if itinerario:
        iti = str(itinerario.id)
        if iti.isdigit():
            ## DERECHO
            if ins.carrera.id == 126:
                if int(iti) == 294:
                    id_asigmal = 10623
                elif int(iti) == 295:
                    id_asigmal = 10627
            ## COMUNICACION
            elif ins.carrera.id == 131:
                if int(iti) == 300:
                    id_asigmal = 10850
                elif int(iti) == 301:
                    id_asigmal = 10854
                elif int(iti) == 302:
                    id_asigmal = 10853

        matricula = Matricula.objects.filter(status=True, nivel__periodo=periodo, inscripcion=ins)
        if matricula.exists():
            nivmal = itinerario.nivel
        else:
            nivmal = ins.mi_nivel().nivel
        if id_asigmal>0:
            materiaasignada = MateriaAsignada.objects.filter(status=True, matricula__inscripcion=ins,
                                                             materia__profesormateria__tipoprofesor=14,
                                                             materia__asignaturamalla__nivelmalla=nivmal,
                                                             materia__asignaturamalla__asignaturapracticas=True, materia__asignaturamalla_id = id_asigmal)
        else:
            materiaasignada = MateriaAsignada.objects.filter(status=True, matricula__inscripcion=ins,
                                                             materia__profesormateria__tipoprofesor=14,
                                                             materia__asignaturamalla__nivelmalla=nivmal,
                                                             materia__asignaturamalla__asignaturapracticas=True)

        if materiaasignada:
            profesor = materiaasignada.first().materia.profesor_principal()
            if profesor:
                return profesor
            else:
                return None
    else:
        return None

def limit_objects(objetos, numero=4):
    cantidad = len(objetos)
    if cantidad > numero:
        objetos = objetos[:numero]
    return objetos

def numero_restante(objetos, numero=4):
    cantidad = len(objetos)
    restante = 0
    if cantidad > numero:
        restante = cantidad - numero
    return restante


def get_fotocedula(cedula):
    url = f"https://sga.unemi.edu.ec/static/images/iconos/hombre.png"
    if persona := Persona.objects.filter(cedula=cedula, status=True, real=True).first():
        url = persona.get_foto()
    return url

@register.simple_tag
def get_consulta_firma_persona_sancion(persona_sancion_id, tipo_doc):
    return ConsultaFirmaPersonaSancion.objects.filter(persona_sancion_id=persona_sancion_id, status=True, tipo_doc=tipo_doc).first()



register.filter('mod4', mod4)
register.filter('diaenletra', diaenletra)
register.filter('filedsmodel', fields_model)
register.filter('fielddefaultvaluemodel', field_default_value_model)
register.filter('ceros', ceros)
register.filter('fechamayor', fechamayor)
register.filter('fechaletra_corta', fechaletra_corta)
register.filter('times', times)
register.filter('multipilca', multipilca)
register.filter("call", callmethod)
register.filter("args", args)
register.filter("transformar_n_l", transformar_n_l)
register.filter("transformar_mes", transformar_mes)
register.filter("traernombre", traernombre)
register.filter("traernombrecarrera", traernombrecarrera)
register.filter("suma", suma)
register.filter("sumar_fm", sumar_fm)
register.filter("sumar_fh", sumar_fh)
register.filter("sumar_cm", sumar_cm)
register.filter("sumar_ch", sumar_ch)
register.filter("sumar_th", sumar_th)
register.filter("sumar_pagineo", sumar_pagineo)
register.filter("colores", colores)
register.filter("sumar_tm", sumar_tm)
register.filter("resta", resta)
register.filter("restanumeros", restanumeros)
register.filter("cincoacien", cincoacien)
register.filter("multiplicanumeros", multiplicanumeros)
register.filter("entrefechas", entrefechas)
register.filter("porciento", porciento)
register.filter("nombremescorto", nombremescorto)
register.filter("numerotemas", numerotemas)
register.filter("numerotemasdiv", numerotemasdiv)
register.filter("llevaraporcentaje", llevaraporcentaje)
register.filter("substraer", substraer)
register.filter("nombremes", nombremes)
register.filter("numeromes", numeromes)
register.filter("fechapermiso", fechapermiso)
register.filter("nombrepersona", nombrepersona)
register.filter("datename", datename)
register.filter("sumarfecha", sumarfecha)
register.filter("sumarvalores", sumarvalores)
register.filter("divide", divide)
register.filter("calendarbox", calendarbox)
register.filter("calendarboxdetails", calendarboxdetails)
register.filter("calendarboxdetails2", calendarboxdetails2)
register.filter("calendarboxdetailspracticas", calendarboxdetailspracticas)
register.filter("listar_campos_tabla", listar_campos_tabla)
register.filter("tieneestudiantepracticas", tieneestudiantepracticas)
register.filter("calevaluaciondocente", calevaluaciondocente)
register.filter("calmodeloevaluaciondocente", calmodeloevaluaciondocente)
register.filter("calmodeloevaluaciondocente2015", calmodeloevaluaciondocente2015)
register.filter("gedc_calculos", gedc_calculos)
register.filter("gedc_calculos_grafica", gedc_calculos_grafica)
register.filter("existe_validacion", existe_validacion)
register.filter("calendarboxdetailsmostrar", calendarboxdetailsmostrar)
register.filter("barraporciento", barraporciento)
register.filter("solo_caracteres", solo_caracteres)
register.filter("rangonumeros", rangonumeros)
register.filter("splitcadena", splitcadena)
register.filter("encrypt", encrypt)
register.filter("encrypt_alu", encrypt_alu)
register.filter("substraerconpunto", substraerconpunto)
register.filter("substraersinpuntohasta", substraersinpuntohasta)
register.filter("substraersinpuntodesde", substraersinpuntodesde)
register.filter("contarcaracter", contarcaracter)
register.filter("cambiarlinea", cambiarlinea)
register.filter("extraer", extraer)
register.filter("tranformarstring", tranformarstring)
register.filter("fechamayor_aux", fechamayor_aux)
register.filter("sumauno", sumauno)
register.filter("datetimename", datetimename)
register.filter("num_notificaciones_modulo", num_notificaciones_modulo)
register.filter("get_manual_usuario_modulo", get_manual_usuario_modulo)
register.filter("diaenletra_fecha", diaenletra_fecha)
register.filter("diaisoweekday", diaisoweekday)
register.filter("numero_a_letras", numero_a_letras)
register.filter("title2", title2)
register.filter("predecesoratitulacion", predecesoratitulacion)
register.filter("pertenecepredecesoratitulacion", pertenecepredecesoratitulacion)
register.filter("notafinalmateriatitulacion", notafinalmateriatitulacion)
register.filter("actasgradopendiente", actasgradopendiente)
register.filter("actasconsolidadaspendientes", actasconsolidadaspendientes)
register.filter("firmaactagradosistema", firmaactagradosistema)
register.filter("realizo_busqueda", realizo_busqueda)
register.filter("tipo_archivo", tipo_archivo)
register.filter("clean_text", clean_text)
register.filter("es_numero_par", es_numero_par)
register.filter("clean_text_coma", clean_text_coma)
register.filter("tiene_solicitud_de_ingreso_titulacion_posgrado", tiene_solicitud_de_ingreso_titulacion_posgrado)
register.filter("calculaedad", calculaedad)
register.filter("calculaporcentaje", calculaporcentaje)
register.filter("asignacion_url", asignacion_url)
register.filter("es_palabra_femenina", es_palabra_femenina)
register.filter("articulo_palabra", articulo_palabra)
register.filter("limit_objects", limit_objects)
register.filter("numero_restante", numero_restante)
register.filter("fecha_natural", fecha_natural)
register.filter("get_fotocedula", get_fotocedula)
register.filter("mes_fecha_natural", mes_fecha_natural)
