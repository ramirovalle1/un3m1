# coding=utf-8
import calendar
from _decimal import Decimal
from datetime import datetime
from django.db.models import Q, Sum
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.general import MateriaSerializer, MatriculaSerializer, RubroSerializer, \
    TestSilaboSemanalSerializer, TareaSilaboSemanalSerializer, ForoSilaboSemanalSerializer, \
    TareaPracticaSilaboSemanalSerializer
from api.serializers.alumno.notificacion import NotificacionSerializer
from core.cache import get_cache_ePerfilUsuario
from inno.models import PeriodoMalla, DetallePeriodoMalla, CalendarioRecursoActividadAlumno, CHOICES_TIPO_ACTIVIDADES, \
    CHOICES_TIPO_ACTIVIDADES_COLOURS
from settings import PORCIENTO_PERDIDA_PARCIAL_GRATUIDAD, RUBRO_ARANCEL, RUBRO_MATRICULA
from sga.funciones import null_to_decimal, log
from sga.models import Noticia, Inscripcion, PerfilUsuario, Matricula, AsignaturaMalla, Materia, \
    PeriodoGrupoSocioEconomico, MateriaAsignada, Nivel, PerdidaGratuidad, MESES_CHOICES, Notificacion, \
    PersonaEstadoCivil, Sexo, ParentescoPersona, Persona
from sagest.models import TipoOtroRubro, Rubro, Pago
from matricula.models import DetalleRubroMatricula
from sga.templatetags.sga_extras import encrypt
from django.db import transaction, connection
from django.core.cache import cache


class GeneralAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = None

    @api_security
    def post(self, request):
        try:
            hoy = datetime.now()
            payload = request.auth.payload
            ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(payload['perfilprincipal']['id']))
            if not ePerfilUsuario.es_estudiante():
                raise NameError(u'Solo los perfiles de estudiantes pueden ingresar a la información.')
            eIncripcion = ePerfilUsuario.inscripcion
            ePersona = eIncripcion.persona
            if not 'action' in request.data:
                raise NameError(u"Parametro de acción no encontrado")

            action = request.data['action']

            if action == 'detail_enroll_items_invoice':
                try:
                    if not 'id' in request.data:
                        raise NameError(u"Parametro de matrícula no encontrado")
                    if not Matricula.objects.values("id").filter(pk=encrypt(request.data['id'])).exists():
                        raise NameError(u"Matrícula no encontrada")
                    eMatricula = Matricula.objects.get(pk=encrypt(request.data['id']))
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

                        aData = {
                            "eMateriaAsignadas": aMateriaAsignadas,
                            "eMatricula": aMatricula,
                            "valorArancel": valorArancel,
                            "valorMatricula": valorMatricula,
                            "valorPagar": valorArancel + valorMatricula
                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    elif eMatricula.inscripcion.coordinacion_id in [9]:
                        # inscripcion.estado_gratuidad = 3
                        eMateriaAsignadas = MateriaAsignada.objects.filter(matricula=eMatricula, cobroperdidagratuidad=True)
                        aMateriaAsignadas = []
                        if eMatricula.inscripcion.sesion_id == 13:
                            eTipoOtroRubroMatricula = TipoOtroRubro.objects.get(pk=3019)
                        else:
                            eTipoOtroRubroMatricula = TipoOtroRubro.objects.get(pk=3011)
                        valorMatricula = null_to_decimal(Rubro.objects.filter(matricula=eMatricula, status=True, tipo=eTipoOtroRubroMatricula).aggregate(valor=Sum('valortotal'))['valor'])
                        valor_x_materia = null_to_decimal(Decimal(valorMatricula/len(eMateriaAsignadas)).quantize(Decimal('.01')).quantize(Decimal('.01')), 2)
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
                        ePerdidaGratuidadas = PerdidaGratuidad.objects.filter(inscripcion=eMatricula.inscripcion, status=True)
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
                        aData = {
                            "eMateriaAsignadas": aMateriaAsignadas,
                            "eMatricula": aMatricula,
                            "valorArancel": null_to_decimal(Decimal(0).quantize(Decimal('.01')).quantize(Decimal('.01')), 2),
                            "valorMatricula": valorMatricula,
                            "valorPagar": valorMatricula
                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    return Helper_Response(isSuccess=False, message=f'Ocurrio un error: Datos no encontrados', status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'detail_pending_values':
                try:
                    id = encrypt(request.data['id']) if 'id' in request.data and encrypt(request.data['id']) else None
                    if not Nivel.objects.values('id').filter(pk=id).exists():
                        raise NameError(u"Nivel no existe")
                    eNivel = Nivel.objects.get(pk=id)
                    ePeriodoMatricula = None
                    if eNivel.periodo.periodomatricula_set.values('id').filter(status=True).exists():
                        ePeriodoMatricula = eNivel.periodo.periodomatricula_set.filter()[0]
                    if not ePeriodoMatricula:
                        raise NameError(u"Periodo académico no existe")
                    eRubros = Rubro.objects.filter(persona=ePersona, cancelado=False, status=True).distinct()
                    if ePeriodoMatricula.tiene_tiposrubros():
                        eRubros = eRubros.filter(tipo__in=ePeriodoMatricula.tiposrubros())
                    aData = {}
                    if eRubros.values("id").exists():
                        eRubros_vencidos = eRubros.filter(fechavence__lt=datetime.now().date()).distinct()
                        if eRubros_vencidos.values("id").exists():
                            valor_total = null_to_decimal(eRubros_vencidos.aggregate(valor=Sum('valortotal'))['valor'])
                            valor_abonos = null_to_decimal(Pago.objects.filter(rubro__in=eRubros_vencidos, status=True).distinct().aggregate(valor=Sum('valortotal'))['valor'])
                            valores_pendiente = valor_total - valor_abonos
                            eRubro_Serializer = RubroSerializer(eRubros_vencidos, many=True)

                            aData = {
                                'eRubros': eRubro_Serializer.data,
                                'tieneVencidos': True,
                                'valorPendiente': valores_pendiente,
                                'valorAbono': valor_abonos,
                                'valorTotal': valor_total,
                            }
                        else:
                            valor_total = null_to_decimal(eRubros.aggregate(valor=Sum('valortotal'))['valor'])
                            valor_abonos = null_to_decimal(Pago.objects.filter(rubro__in=eRubros, status=True).distinct().aggregate(valor=Sum('valortotal'))['valor'])
                            valores_pendiente = valor_total - valor_abonos
                            eRubro_Serializer = RubroSerializer(eRubros, many=True)
                            aData = {
                                'eRubros': eRubro_Serializer.data,
                                'tieneVencidos': False,
                                'valorPendiente': valores_pendiente,
                                'valorAbono': valor_abonos,
                                'valorTotal': valor_total,
                            }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'detail_calenar_student':
                try:
                    aData = {}
                    if not 'id' in request.data:
                        raise NameError(u"Parametro de matrícula no encontrado")
                    if not Matricula.objects.values("id").filter(pk=encrypt(request.data['id'])).exists():
                        raise NameError(u"Matrícula no encontrada")
                    fecha = datetime.now().date()
                    month = fecha.month
                    year = fecha.year
                    if 'mover' in request.data:
                        mover = request.data['mover']
                        if mover == 'before':
                            mes = int(request.data['mes'])
                            anio = int(request.data['anio'])
                            month = mes - 1
                            if month == 0:
                                month = 12
                                year = anio - 1
                            else:
                                year = anio

                        elif mover == 'after':
                            mes = int(request.data['mes'])
                            anio = int(request.data['anio'])
                            month = mes + 1
                            if month == 13:
                                month = 1
                                year = anio + 1
                            else:
                                year = anio
                        else:
                            month = fecha.month
                            year = fecha.year
                    eMatricula = Matricula.objects.get(pk=encrypt(request.data['id']))
                    eMateriaAsignadas = eMatricula.materiaasignada_set.filter(status=True, retiramateria=False)
                    calendario = calendar.Calendar()
                    aCalendario = []
                    aTipoActividades = []
                    for semanas in calendario.monthdatescalendar(year, month):
                        dia = 0
                        aSemana = []
                        fechaInicio = semanas[0]
                        fechaFin = semanas[6]
                        for f in semanas:
                            dia += 1
                            eRecurso = []
                            # eCalendarioRecursoActividadAlumnos = CalendarioRecursoActividadAlumno.objects.filter(materiaasignada__in=eMateriaAsignadas, recurso__fechahoradesde__gte=fechaInicio, recurso__fechahorahasta__lte=fechaFin)
                            eCalendarioRecursoActividadAlumnos = CalendarioRecursoActividadAlumno.objects.filter(materiaasignada__in=eMateriaAsignadas, recurso__fechahorahasta__date=f)
                            for eCalendarioRecursoActividadAlumno in eCalendarioRecursoActividadAlumnos:
                                eMateria = MateriaSerializer(eCalendarioRecursoActividadAlumno.recurso.materia).data
                                eActividad = {}
                                if eCalendarioRecursoActividadAlumno.recurso.tipo == 1:
                                    eActividad = TestSilaboSemanalSerializer(eCalendarioRecursoActividadAlumno.recurso.content_object).data
                                elif eCalendarioRecursoActividadAlumno.recurso.tipo in [2, 3, 4, 5, 6]:
                                    eActividad = TareaSilaboSemanalSerializer(eCalendarioRecursoActividadAlumno.recurso.content_object).data
                                elif eCalendarioRecursoActividadAlumno.recurso.tipo == 7:
                                    eActividad = ForoSilaboSemanalSerializer(eCalendarioRecursoActividadAlumno.recurso.content_object).data
                                elif eCalendarioRecursoActividadAlumno.recurso.tipo == 8:
                                    eActividad = TareaPracticaSilaboSemanalSerializer(eCalendarioRecursoActividadAlumno.recurso.content_object).data
                                tipo_background = ''
                                tipo_color = ''
                                for num in CHOICES_TIPO_ACTIVIDADES_COLOURS:
                                    if num[0] == eCalendarioRecursoActividadAlumno.recurso.tipo:
                                        tipo_background = num[2]
                                        tipo_color = num[3]
                                eRecurso.append({"id": eCalendarioRecursoActividadAlumno.recurso.id,
                                                 "eMateria": eMateria,
                                                 "eActividad": eActividad,
                                                 "tipo": eCalendarioRecursoActividadAlumno.recurso.tipo,
                                                 "tipo_display": eCalendarioRecursoActividadAlumno.recurso.get_tipo_display(),
                                                 "background": tipo_background,
                                                 "color": tipo_color,
                                                 "url": eCalendarioRecursoActividadAlumno.recurso.url,
                                                 "fechahoradesde": eCalendarioRecursoActividadAlumno.recurso.fechahoradesde,
                                                 "fechahorahasta": eCalendarioRecursoActividadAlumno.recurso.fechahorahasta,
                                                 "cambio": eCalendarioRecursoActividadAlumno.recurso.cambio
                                                 })
                                if not eCalendarioRecursoActividadAlumno.recurso.tipo in [x[0] for x in aTipoActividades]:
                                    for num in CHOICES_TIPO_ACTIVIDADES_COLOURS:
                                        if num[0] == eCalendarioRecursoActividadAlumno.recurso.tipo:
                                            aTipoActividades.append(num)
                            aSemana.append({"dia": dia, "day": f.day, "fecha": f, "monthActive": f.month == month, "actividades": eRecurso})
                        aCalendario.append(aSemana)
                    aData['aCalendario'] = aCalendario
                    aData['year'] = year
                    aData['month'] = month
                    aData['month_display'] = MESES_CHOICES[month - 1][1]
                    aData['eMatricula'] = MatriculaSerializer(eMatricula).data
                    aData['TiposActividad'] = CHOICES_TIPO_ACTIVIDADES
                    aData['aTipoActividades'] = aTipoActividades
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',status=status.HTTP_200_OK)

            elif action == 'detail_notifcations_student':
                try:
                    aData = {}
                    eNotificaciones = Notificacion.objects.filter(Q(app_label='SIE'), destinatario=ePersona, perfil=ePerfilUsuario, leido=False, visible=True, fecha_hora_visible__gte=hoy)[0:5]
                    aData['eNotificaciones'] = NotificacionSerializer(eNotificaciones, many=True).data if eNotificaciones.values("id").exists() else []
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',status=status.HTTP_200_OK)

            elif action == 'save_view_notifcation_student':
                with transaction.atomic():
                    try:
                        if not 'id' in request.data:
                            raise NameError(u"Parametro de notificación no encontrado")
                        if not Notificacion.objects.values("id").filter(pk=encrypt(request.data['id'])).exists():
                            raise NameError(u"Notificación no encontrada")
                        aData = {}
                        eNotificacion = Notificacion.objects.get(pk=encrypt(request.data['id']))
                        eNotificacion.leido = True
                        eNotificacion.fecha_hora_leido = hoy
                        eNotificacion.visible = False
                        eNotificacion.save(request)
                        log(u'Leo el mensaje: %s' % eNotificacion, request, "edit")
                        payload = request.auth.payload
                        ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(payload['perfilprincipal']['id']))
                        eNotificacionEnCache = cache.get(f"notificaciones_perfilusuario_id_{encrypt(ePerfilUsuario.id)}")
                        if eNotificacionEnCache:
                            cache.delete(f"notificaciones_perfilusuario_id_{encrypt(ePerfilUsuario.id)}")
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'get_titulos_educacion_superior':
                with transaction.atomic():
                    try:
                        from soap.consumer.senescyt import Titulos
                        payload = request.auth.payload
                        ePerfilUsuario = get_cache_ePerfilUsuario(int(encrypt(payload['perfilprincipal']['id'])))
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        identificacion = ePersona.identificacion()
                        eTitulos = Titulos(identificacion)
                        mistitulos = eTitulos.consultar()
                        return Helper_Response(isSuccess=True, data={'cantidad': len(mistitulos)}, message=f'Se obtuvo la información correctamente', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al obtener los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'get_titulos_educacion_bachiller':
                with transaction.atomic():
                    try:
                        from soap.consumer.mineduc import Titulos
                        payload = request.auth.payload
                        ePerfilUsuario = get_cache_ePerfilUsuario(int(encrypt(payload['perfilprincipal']['id'])))
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        identificacion = ePersona.identificacion()
                        eTitulos = Titulos(identificacion)
                        mistitulos = eTitulos.consultar()
                        return Helper_Response(isSuccess=True, data={'cantidad': len(mistitulos)}, message=f'Se obtuvo la información correctamente', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al obtener los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            return Helper_Response(isSuccess=False, data={}, message=f'Acción no encontrada', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

