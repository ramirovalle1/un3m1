# -*- coding: latin-1 -*-
from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.utils.translation import gettext_lazy as _
from django import forms
from django.contrib.auth.models import Permission

from sga.djangoselect2 import MySelect2Widget

from sga.models import *
from sga.My_Model.SubirMatrizSENESCYT import *
from inno.models import *

MANAGERS = (
    ('isaltosm', 'isaltosm@unemi.edu.ec'),
    ('kpalaciosz', 'kpalaciosz@unemi.edu.ec'),
    ('michaeloc_20', 'clockem@unemi.edu.ec'),
    ('ryseven', 'ryepezb1@unemi.edu.ec'),
    ('crodriguezn', 'crodriguezn@unemi.edu.ec'),
    ('ame_dam', 'jplacesc@unemi.edu.ec'),
    ('rviterib1', 'rviterib1@unemi.edu.ec'),
    ('isabel.gomez', 'igomezg@unemi.edu.ec '),
    ('cgomezm3', 'cgomezm3@unemi.edu.ec '),
    ('wgavilanesr', 'wgavilanesr@unemi.edu.ec '),
    ('nfuentesp', 'nfuentesp@unemi.edu.ec '),
    ('jguachuns', 'jguachuns@unemi.edu.ec '),
    ('mleong2', 'mleong2@unemi.edu.ec '),
)


class ModeloBaseTabularAdmin(admin.TabularInline):
    exclude = ("usuario_creacion", "fecha_creacion", "usuario_modificacion", "fecha_modificacion")


class ModeloBaseAdmin(admin.ModelAdmin):

    def get_actions(self, request):
        actions = super(ModeloBaseAdmin, self).get_actions(request)
        if request.user.username not in [x[0] for x in MANAGERS]:
            del actions['delete_selected']
        return actions

    def has_add_permission(self, request):
        return request.user.username in [x[0] for x in MANAGERS]

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return request.user.username in [x[0] for x in MANAGERS]

    def get_form(self, request, obj=None, **kwargs):
        self.exclude = ("usuario_creacion", "fecha_creacion", "usuario_modificacion", "fecha_modificacion")
        form = super(ModeloBaseAdmin, self).get_form(request, obj, **kwargs)
        return form

    def save_model(self, request, obj, form, change):
        if request.user.username not in [x[0] for x in MANAGERS]:
             raise Exception('Sin permiso a modificacion')
        else:
            obj.save(request)


class ProfesorTipoAdmin(ModeloBaseAdmin):
    list_display = ('nombre', )
    ordering = ('nombre',)
    search_fields = ('nombre',)


class DetalleModeloEvaluativoAdmin(ModeloBaseAdmin):
    list_display = ('modelo', 'nombre', 'notaminima', 'notamaxima', 'decimales')
    ordering = ('modelo', 'orden',)
    list_filter = ('modelo',)


class AgregacioneliminacionmateriasAdmin(ModeloBaseAdmin):
    list_display = ('agregacion', 'asignatura', 'fecha', 'matricula')
    ordering = ('-fecha',)
    search_fields = ('matricula',)


class EspecialidadAdmin(ModeloBaseAdmin):
    list_display = ('nombre', )
    ordering = ('nombre',)
    search_fields = ('nombre',)


class ItemExamenComplexivoAdmin(ModeloBaseAdmin):
    list_display = ('detalle',)
    ordering = ('detalle',)
    search_fields = ('detalle',)


class CategorizacionDocenteAdmin(ModeloBaseAdmin):
    list_display = ('nombre', )
    ordering = ('nombre',)
    search_fields = ('nombre',)


class CoordinacionAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'alias', 'sede')
    ordering = ('nombre', 'sede')
    search_fields = ('nombre', 'sede', 'alias')


class InscripcionFlagsAdmin(ModeloBaseAdmin):
    list_display = ('inscripcion', 'tienechequeprotestado', 'tienedeudaexterna', 'motivo')
    ordering = ('inscripcion',)
    search_fields = ('inscripcion__persona__cedula', 'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')
    list_filter = ('tienechequeprotestado', 'tienedeudaexterna')


class NotaCreditoAdmin(ModeloBaseAdmin):
    list_display = ('inscripcion', 'motivo', 'fecha', 'valorinicial', 'saldo')
    ordering = ('inscripcion',)
    search_fields = ('inscripcion__persona__cedula', 'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')


class DatosNotaCreditoAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'numero', 'fecha', 'total', 'iva', 'subtotal')
    ordering = ('numero', 'nombre')
    search_fields = ('numero',)


class CargoInstitucionAdmin(ModeloBaseAdmin):
    list_display = ('persona', 'cargo')
    ordering = ('persona', 'cargo')
    search_fields = ('persona', 'cargo')


class EstadoCarreraAdmin(ModeloBaseAdmin):
    list_display = ('nombre', )
    ordering = ('nombre', )
    search_fields = ('nombre', )


class CarreraAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'modalidad' ,  'mencion', 'alias', 'codigo', 'niveltitulacion', 'estadocarrera')
    ordering = ('nombre', 'mencion', )
    search_fields = ('alias', 'nombre', 'mencion', 'modalidad' )


class ImpresionAdmin(ModeloBaseAdmin):
    list_display = ('usuario', 'impresa')
    ordering = ('usuario',)
    search_fields = ('usuario',)


class TituloInstitucionAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'direccion', 'telefono', 'correo', 'web', 'municipio', 'codigo')
    ordering = ('nombre',)
    search_fields = ('nombre', 'correo')


class ConvalidacionInscripcionAdmin(ModeloBaseAdmin):
    list_display = ('record', 'centro', 'carrera', 'asignatura', 'anno', 'nota_ant', 'nota_act', 'observaciones')
    ordering = ('asignatura',)
    search_fields = ('asignatura',)


class GrupoAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'tiene_cupo', 'carrera', 'sesion', 'modalidad', 'sede', 'capacidad', 'inicio', 'fin', 'observaciones', 'abierto')
    ordering = ('inicio',)
    search_fields = ('nombre', 'observaciones', 'capacidad', 'abierto')
    list_filter = ('carrera', 'sesion', 'modalidad', 'sede')


class SesionCajaAdmin(ModeloBaseAdmin):
    list_display = ('caja', 'fecha', 'hora', 'fondo', 'facturaempieza', 'facturatermina', 'fondo', 'abierta')
    ordering = ('fecha', 'hora')
    search_fields = ('caja', 'facturaempieza', 'facturatermina')
    list_filter = ('abierta',)


class GrupoCoordinadorCarreraAdmin(ModeloBaseAdmin):
    list_display = ('group', 'carrera')
    ordering = ('group', 'carrera')
    search_fields = ('group__name', 'carrera__nombre')
    list_filter = ('group', 'carrera')


class GrupoCoordinadorCoordinacionAdmin(ModeloBaseAdmin):
    list_display = ('group', 'coordinacion')
    ordering = ('coordinacion__nombre',)
    search_fields = ('group__name', 'coordinacion__nombre')
    list_filter = ('group', 'coordinacion')


class ParametroReporteAdmin(ModeloBaseTabularAdmin):
    model = ParametroReporte


class SubReporteAdmin(ModeloBaseTabularAdmin):
    model = SubReporte


class ReporteAdmin(ModeloBaseAdmin):
    inlines = [ParametroReporteAdmin, SubReporteAdmin]
    list_display = ('nombre', 'descripcion', 'archivo', 'categoria', 'interface', 'sga', 'sagest')
    ordering = ('nombre',)
    search_fields = ('nombre',)
    list_filter = ('categoria', 'grupos')


class TipoIncidenciaAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'correo', 'responsable')
    ordering = ('nombre',)
    search_fields = ('nombre', 'correo', 'responsable')


class IncidenciaAdmin(ModeloBaseAdmin):
    list_display = ('lecciongrupo', 'tipo', 'contenido', 'cerrada')
    ordering = ('lecciongrupo', 'cerrada')
    list_filter = ('tipo', 'cerrada')


class PerfilInscripcionAdmin(ModeloBaseAdmin):
    list_display = ('inscripcion', 'raza', 'estrato', 'tienediscapacidad', 'tipodiscapacidad')
    ordering = ('inscripcion__persona__apellido1',)
    search_fields = ('inscripcion',)


class PersonaAdmin(ModeloBaseAdmin):
    list_display = ('nombre_completo', 'cedula','pasaporte', 'sexo', 'email', 'telefono', 'provincia', 'usuario')
    ordering = ('nombres',)
    search_fields = ('nombres', 'apellido1', 'apellido2', 'cedula')
    list_filter = ('provincia', 'sexo')
    raw_id_fields = ('usuario',)


class AlumnoAdmin(ModeloBaseAdmin):
    list_display = ('nombre_completo', 'colegio', 'especialidad')
    ordering = ('persona',)
    search_fields = ('nombre_completo',)
    list_filter = ('colegio', 'especialidad')


class AsignaturaAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'cantidad_dependencias', 'codigo', 'creditos', 'horas')
    ordering = ('nombre',)
    search_fields = ('nombre', 'codigo')


class CodigoEvaluacionAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'alias')
    ordering = ('id', 'nombre')
    search_fields = ('nombre', 'alias')


class PeriodoAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'inicio', 'fin', 'activo', 'tipo', 'valida_asistencia', 'valida_deuda', 'preferencia_inicio', 'preferencia_final', 'usa_moodle', 'anio', 'cohorte')
    ordering = ('activo', 'fin')
    search_fields = ('nombre',)
    list_filter = ('activo','tipo')
    date_hierarchy = 'inicio'


class NivelAdmin(ModeloBaseAdmin):
    list_display = ('paralelo', 'inicio', 'fin', 'nivelgrado')
    ordering = ('fin', )
    search_fields = ('paralelo',)
    date_hierarchy = 'inicio'


class AsignaturaMallaAdmin(ModeloBaseAdmin):
    list_display = ('malla', 'asignatura', 'nivelmalla', 'ejeformativo', 'horas', 'creditos')
    ordering = ('malla',)
    search_fields = ('malla', 'asignatura',)
    list_filter = ('nivelmalla', 'ejeformativo', 'malla', 'asignatura')


class SesionAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'comienza', 'termina', 'cantidad_turnos', 'repr_dias', 'codigo')
    ordering = ('nombre',)
    search_fields = ('nombre',)


class MateriaAdmin(ModeloBaseAdmin):
    list_display = ('id','asignatura', 'nivel', 'horas', 'creditos', 'inicio', 'fin', 'cerrado')
    ordering = ('-fin', 'nivel', 'asignatura')
    search_fields = ('id','asignatura__nombre', 'nivel__paralelo', 'horas', 'creditos')
    fields = ['horas', 'horassemanales', 'inicio', 'fin', 'rectora', 'cerrado', 'practicas', 'grado', 'cupo', 'modelotarjeta', 'namehtml', 'urlhtml', 'actualizarhtml', 'status', 'idcursomoodle']


class MallaAdmin(ModeloBaseAdmin):
    list_display = ('carrera', 'inicio', 'vigente')
    ordering = ('inicio',)
    search_fields = ('carrera',)
    list_filter = ('vigente',)
    date_hierarchy = 'inicio'


class InscripcionMallaAdmin(ModeloBaseAdmin):
    list_display = ('inscripcion', 'malla', )
    ordering = ('inscripcion',)


class AulaAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'capacidad', 'tipo', 'sede')
    ordering = ('nombre', 'tipo')
    search_fields = ('nombre',)
    list_filter = ('tipo', 'sede',)


class TurnoAdmin(ModeloBaseAdmin):
    list_display = ('sesion', 'turno', 'comienza', 'termina', 'horas', 'status')
    ordering = ('sesion', 'turno')
    search_fields = ('sesion', 'turno')
    list_filter = ('sesion', 'turno')


class ModuloAdmin(ModeloBaseAdmin):
    list_display = ('url', 'nombre', 'icono', 'descripcion', 'activo')
    ordering = ('url',)
    search_fields = ('url', 'nombre', 'descripcion', 'categorias')
    list_filter = ('activo',)


class ModuloGrupoAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'prioridad', 'descripcion')
    ordering = ('prioridad', 'nombre')
    search_fields = ('nombre', 'descripcion')


class ClaseAdmin(ModeloBaseAdmin):
    list_display = ('materia', 'turno', 'aula', 'dia')
    ordering = ('materia', 'dia', 'aula')
    search_fields = ('materia', 'aula')
    list_filter = ('aula', 'dia', 'turno')


class ProfesorAdmin(ModeloBaseAdmin):
    list_display = ('persona', 'activo', 'fechaingreso')
    ordering = ('persona',)
    search_fields = ('persona__nombres', 'persona__apellido1', 'persona__apellido2')
    list_filter = ('activo',)
    date_hierarchy = 'fechaingreso'


class PreInscritoAdmin(ModeloBaseAdmin):
    list_display = ('nombres', 'apellido1', 'apellido2', 'email')
    ordering = ('nombres', 'apellido1', 'apellido2',)
    search_fields = ('nombres', 'apellido1', 'apellido2',)


class InscripcionAdmin(ModeloBaseAdmin):
    list_display = ('persona', 'fecha', 'carrera', 'modalidad', 'sesion', 'colegio', 'especialidad')
    ordering = ('persona',)
    search_fields = ('persona__nombres', 'persona__apellido1', 'persona__apellido2', 'carrera__nombre')
    list_filter = ('modalidad', 'carrera', 'especialidad')
    date_hierarchy = 'fecha'


class RecordAcademicoAdmin(ModeloBaseAdmin):
    list_display = ('inscripcion', 'asignatura', 'nota', 'asistencia', 'fecha', 'convalidacion', 'aprobada')
    ordering = ('inscripcion__persona__nombres',)
    search_fields = ('inscripcion__persona__nombres', 'asignatura__nombre',)
    list_filter = ('asignatura', 'convalidacion')
    date_hierarchy = 'fecha'


class HistoricoRecordAcademicoAdmin(ModeloBaseAdmin):
    list_display = ('inscripcion', 'asignatura', 'nota', 'asistencia', 'fecha', 'convalidacion', 'aprobada')
    ordering = ('inscripcion__persona__nombres',)
    search_fields = ('inscripcion__persona__nombres', 'asignatura__nombre',)
    list_filter = ('asignatura', 'convalidacion')
    date_hierarchy = 'fecha'

# class MatriculaFormAdmin(forms.ModelForm):
#
#     class Meta:
#         model = Matricula
#         fields = '__all__'
#
#     def __init__(self, *args, **kwargs):
#         super(MatriculaFormAdmin, self).__init__(*args, **kwargs)
#         self.fields['inscripcion'].widget = MySelect2Widget(searchs=["persona__apellido1__icontains"], queryset=Inscripcion.objects.all(), attrs={"style":"width:480px;"})
#         if 'instance' in kwargs:
#             if kwargs['instance'].inscripcion:
#                 # self.fields['inscripcion'].queryset = Inscripcion.objects.filter(pk=kwargs['instance'].inscripcion.pk)
#                 self.fields['inscripcion'].initial = kwargs['instance'].inscripcion


class MatriculaAdmin(ModeloBaseAdmin):
    # form = MatriculaFormAdmin
    list_per_page = 15
    list_display = ('id','inscripcion', 'periodo_name', 'pago', 'becado', 'porcientobeca', 'tipobeca')
    ordering = ('inscripcion',)
    search_fields = ('id', 'inscripcion__persona__nombres', 'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2')
    fields = ['id', 'inscripcion',
              'pago', 'iece', 'becado', 'becaexterna','beneficiomonetario','tipomatricula','tipobeca',
              'porcientobeca','montomensual','cantidadmeses','montobeneficio','formalizada','promedionotas','aprobadofinanzas','cerrada',
              'tipobecarecibe','nivelmalla','estado_matricula','status']
    readonly_fields = ['id',]

    # class Media:
    #     js = (
    #         'http://ajax.googleapis.com/ajax/libs/jquery/1.9.1/jquery.min.js',
    #     )

    def idinscripcion(self,obj):
        return '%s' % (obj.inscripcion_id)


class MateriaAsignadaAdmin(ModeloBaseAdmin):
    fields = ['materia', 'status' ]
    ordering = ('matricula', 'materia', 'notafinal')
    search_fields = ('matricula__inscripcion__persona__nombres', 'matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2',)
    raw_id_fields = ('materia',)

class LeccionAdmin(ModeloBaseAdmin):
    list_display = ('clase', 'fecha', 'horaentrada', 'horasalida', 'abierta')
    ordering = ('-fecha',)
    search_fields = ('clase__materia__asignatura__nombre', 'clase__aula__nombre', 'contenido', 'observaciones')
    list_filter = ('abierta',)
    date_hierarchy = 'fecha'


class LeccionGrupoAdmin(ModeloBaseAdmin):
    list_display = ('profesor', 'fecha', 'horaentrada', 'horasalida', 'abierta')
    ordering = ('-fecha',)
    search_fields = ('profesor', 'contenido', 'observaciones')
    list_filter = ('abierta', 'profesor')
    date_hierarchy = 'fecha'


class SolicitudSecretariaDocenteAdmin(ModeloBaseAdmin):
    list_display = ('persona', 'fecha', 'hora', 'tipo', 'cerrada', 'fechacierre')
    ordering = ('-fecha',)
    search_fields = ('persona', 'descripcion')
    list_filter = ('cerrada', 'tipo')
    date_hierarchy = 'fecha'


class DocumentosDeInscripcionAdmin(ModeloBaseAdmin):
    list_display = ('inscripcion', 'titulo', 'acta', 'cedula', 'fotos', 'partida_nac', 'actaconv', 'votacion')
    ordering = ('inscripcion__persona__apellido1',)
    search_fields = ('inscripcion',)
    list_filter = ('titulo', 'acta', 'cedula', 'fotos')


class GraduadoAdmin(ModeloBaseAdmin):
    list_display = ('inscripcion', 'notafinal', 'fechagraduado', 'tematesis', 'registro')
    # ordering = ('inscripcion__persona__apellido1')
    search_fields = ('inscripcion',)


class EgresadoAdmin(ModeloBaseAdmin):
    list_display = ('inscripcion', 'fechaegreso', 'notaegreso')
    ordering = ('inscripcion__persona__apellido1', 'fechaegreso', 'notaegreso')
    search_fields = ('inscripcion',)


class RetiradoMatriculaAdmin(ModeloBaseAdmin):
    list_display = ('matricula', 'fecha', 'motivo')
    ordering = ('matricula', 'fecha')
    search_fields = ('matricula__inscripcion__persona__nombres', 'matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2')
    date_hierarchy = 'fecha'


class LicenciaAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'ruc', 'email', 'telefono', 'direccion', 'expira', 'idautorizacion')
    ordering = ('expira',)
    search_fields = ('nombre', 'ruc', 'email')
    date_hierarchy = 'expira'


class ArchivoAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'materia', 'lecciongrupo', 'fecha', 'archivo', 'tipo')
    ordering = ('nombre',)
    search_fields = ('nombre', 'materia__asignatura__nombre')
    list_filter = ('tipo',)
    date_hierarchy = 'fecha'


class BancoAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'tasaprotesto')
    ordering = ('nombre',)
    search_fields = ('nombre', 'tasaprotesto')


class CuentaBancoAdmin(ModeloBaseAdmin):
    list_display = ('banco', 'numero', 'tipocuenta', 'representante')
    ordering = ('banco',)
    search_fields = ('banco', 'numero', 'tipocuenta')
    list_filter = ('numero',)


class RubroAdmin(ModeloBaseAdmin):
    list_display = ('fecha', 'valor', 'inscripcion', 'cancelado', 'fechavence')
    ordering = ('fecha', 'valor')
    search_fields = ('fecha', 'inscripcion__persona__cedula', 'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')


class RubroNotaDebitoAdmin(ModeloBaseAdmin):
    list_display = ('rubro', 'motivo')
    ordering = ('rubro', 'motivo')
    search_fields = ('rubro__inscripcion__persona__cedula', 'rubro__inscripcion__persona__apellido1', 'rubro__inscripcion__persona__apellido2', 'rubro__inscripcion__persona__nombres', 'motivo')


class ActividadExtraCurricularAdmin(ModeloBaseAdmin):
    list_display = ('periodo', 'nombre', 'tipo', 'fechainicio', 'fechafin', 'responsable', 'cupo')
    ordering = ('periodo', 'tipo', 'fechainicio')
    search_fields = ('nombre', 'tipo')
    list_filter = ('fechainicio',)


class ParticipanteActividadExtraCurricularAdmin(ModeloBaseAdmin):
    list_display = ('actividad', 'inscripcion', 'nota', 'asistencia')
    ordering = ('actividad', 'nota')
    search_fields = ('actividad', 'inscripcion')


class TipoOtroRubroAdmin(ModeloBaseAdmin):
    list_display = ('nombre',)
    ordering = ('nombre',)
    search_fields = ('nombre',)


class RubroOtroAdmin(ModeloBaseAdmin):
    list_display = ('rubro', 'tipo', 'descripcion')
    ordering = ('rubro', 'tipo')
    search_fields = ('rubro', 'tipo')


class LugarRecaudacionAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'persona', 'puntoventa')
    ordering = ('nombre', 'persona')
    search_fields = ('nombre', 'persona')


class PagoChequeAdmin(ModeloBaseAdmin):
    list_display = ('numero', 'banco', 'fecha', 'fechacobro', 'emite', 'valor', 'protestado')
    ordering = ('numero', 'fecha')
    search_fields = ('banco',)


class PagoTarjetaAdmin(ModeloBaseAdmin):
    list_display = ('banco', 'poseedor', 'valor', 'procesadorpago', 'referencia', 'fecha')
    ordering = ('banco', 'valor', 'fecha')
    search_fields = ('banco', 'poseedor')


class ChequeProtestadoAdmin(ModeloBaseAdmin):
    list_display = ('cheque', 'motivo', 'fecha')
    ordering = ('cheque',)
    search_fields = ('cheque', 'fecha')


class CoordinadorCarreraAdmin(ModeloBaseAdmin):
    list_display = ('persona', 'carrera', 'periodo')
    ordering = ('persona', 'carrera')
    search_fields = ('persona__nombres', 'persona__apellido1', 'persona__apellido2', 'carrera__nombre')
    list_filter = ('periodo', 'carrera')


class AmbitoInstrumentoEvaluacionAdmin(ModeloBaseAdmin):
    list_display = ('instrumento', 'ambito')
    ordering = ('instrumento',)
    search_fields = ('instrumento', 'ambito')


class MatrizInscripcionAdmin(ModeloBaseAdmin):
    list_display = ('periodo', 'fecha_inicio', 'fecha_fin', 'anio', 'inscripcion', 'institucion', 'fecha_primernivel', 'creditos_aprobados')
    ordering = ('periodo',)
    search_fields = ('periodo', 'inscripcion__persona__cedula', 'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')


class IndicadorAmbitoInstrumentoEvaluacionAdmin(ModeloBaseAdmin):
    list_display = ('ambitoinstrumento', 'indicador')
    ordering = ('ambitoinstrumento',)
    search_fields = ('ambitoinstrumento', 'indicador')


class ProcesoEvaluativoAdmin(ModeloBaseAdmin):
    list_display = ('periodo', 'instrumentoalumno', 'instrumentoprofesor', 'instrumentocoordinador', 'desde', 'hasta')
    ordering = ('periodo', 'desde')
    search_fields = ('periodo',)


class EvaluacionProfesorAdmin(ModeloBaseAdmin):
    list_display = ('proceso', 'profesor', 'fecha')
    ordering = ('proceso', 'fecha')
    search_fields = ('profesor__persona__nombres', 'profesor__persona__apellido1', 'profesor__persona__apellido2')


class DatoInstrumentoEvaluacionAdmin(ModeloBaseAdmin):
    list_display = ('evaluacion', 'indicador', 'valor', 'observaciones')
    ordering = ('evaluacion',)
    search_fields = ('valor', 'evaluacion')


class CierreSesionCajaAdmin(ModeloBaseAdmin):
    list_display = ('sesion', 'bill100', 'bill50', 'bill20', 'bill10', 'bill5', 'bill2', 'bill1', 'enmonedas', 'deposito', 'total', 'fecha', 'hora')
    ordering = ('sesion__fecha',)


class PagoCalendarioAdmin(ModeloBaseAdmin):
    list_display = ('periodo', 'tipo', 'fecha', 'valor')
    ordering = ('periodo', 'tipo')
    list_filter = ('periodo',)


class AplicanteOfertaAdmin(ModeloBaseAdmin):
    list_display = ('oferta', 'inscripcion', 'entrevistado', 'aprobada')
    ordering = ('fechaentrevista',)
    list_filter = ('oferta',)


class ColegioAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'codigo')
    ordering = ('nombre',)


class CostoPeriodoTipoInscripcionAdmin(ModeloBaseAdmin):
    list_display = ('periodo', 'tipoinscripcion', 'tipomateria', 'valor')
    ordering = ('periodo', 'tipoinscripcion')
    list_filter = ('periodo',)


class LogEntryAdmin(ModeloBaseAdmin):
    date_hierarchy = 'action_time'
    list_filter = ['action_flag']
    search_fields = ['change_message', 'object_repr', 'user__username']
    list_display = ['action_time', 'user', 'action_flag', 'change_message']

    def get_actions(self, request):
        actions = super(LogEntryAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        self.readonly_fields = [x.name for x in self.model._meta.local_fields]
        return True

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
         raise Exception('Sin permiso a modificacion')


class LogEntryBackupAdmin(ModeloBaseAdmin):
    date_hierarchy = 'action_time'
    list_filter = ['action_flag']
    search_fields = ['change_message', 'object_repr', 'user__username']
    list_display = ['action_time', 'user', 'action_flag', 'change_message']

    def get_actions(self, request):
        actions = super(LogEntryBackupAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


class LogEntryBackupdosAdmin(ModeloBaseAdmin):
    date_hierarchy = 'action_time'
    list_filter = ['action_flag']
    search_fields = ['change_message', 'object_repr', 'user__username']
    list_display = ['action_time', 'user', 'action_flag', 'change_message']

    def get_actions(self, request):
        actions = super(LogEntryBackupdosAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


class RelacionAdmin(ModeloBaseAdmin):
    list_display = ('tipo', 'nombre')
    ordering = ('tipo',)
    list_filter = ('tipo',)


class InscripcionNivelAdmin(ModeloBaseAdmin):
    list_display = ('inscripcion', 'nivel', )
    ordering = ('inscripcion',)
    search_fields = ('inscripcion__persona__nombres', 'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2',)


class TipoInscripcionAdmin(ModeloBaseAdmin):
    list_display = ('nombre', )
    search_fields = ('nombre', )
    ordering = ('nombre',)


class TipoEvaluacionEvaluacionAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'campo', 'valormaximo')
    search_fields = ('nombre', )
    ordering = ('nombre',)


class AulaCoordinacionAdmin(ModeloBaseAdmin):
    list_display = ('aula', 'coordinacion')
    search_fields = ('aula__nombre', 'coordinacion__nombre')
    ordering = ('aula', )
    list_filter = ('coordinacion', )


class ResponsableCoordinacionAdmin(ModeloBaseAdmin):
    list_display = ('coordinacion', 'persona')
    ordering = ('coordinacion', )



# class PerfilAccesoUsuarioFormAdmin(forms.ModelForm):
#     class Meta:
#         model = PerfilAccesoUsuario
#         fields = '__all__'
#         # widgets = {
#         #     'grupo': MySelect2Widget(searchs=["name__icontains"], queryset=Group.objects.all(), attrs={"style": "width:280px;"}),
#         #     'coordinacion': MySelect2Widget(searchs=["nombre__icontains"], queryset=Coordinacion.objects.all(), attrs={"style":"width:480px;"}),
#         #     'carrera': MySelect2Widget(searchs=["nombre__icontains"], queryset=Carrera.objects.all(), dependent_fields={'coordinacion': 'coordinacion'}, attrs={"style":"width:480px;"})
#         # }
#
#     def __init__(self, *args, **kwargs):
#         super(PerfilAccesoUsuarioFormAdmin, self).__init__(*args, **kwargs)
#         self.fields['grupo'].widget = MySelect2Widget(searchs=["name__icontains"], queryset=Group.objects.all(), attrs={"style":"width:480px;"})
#         self.fields['coordinacion'].widget = MySelect2Widget(searchs=["nombre__icontains"], queryset=Coordinacion.objects.all(), attrs={"style":"width:480px;"})
#         self.fields['carrera'].widget = MySelect2Widget(searchs=["nombre__icontains"], queryset=Carrera.objects.all(), dependent_fields={'coordinacion': 'coordinacion'}, attrs={"style":"width:480px;"})
#         if 'instance' in kwargs:
#             if kwargs['instance']:
#                 if kwargs['instance'].grupo:
#                     self.fields['grupo'].queryset = Group.objects.all()
#                     self.fields['grupo'].initial = kwargs['instance'].grupo
#                 if kwargs['instance'].coordinacion:
#                     self.fields['coordinacion'].queryset = Coordinacion.objects.all()
#                     self.fields['coordinacion'].initial = kwargs['instance'].coordinacion.pk
#                 if kwargs['instance'].carrera:
#                     self.fields['carrera'].queryset = Carrera.objects.all()
#                     self.fields['carrera'].initial = kwargs['instance'].carrera.pk

class PerfilAccesoUsuarioAdmin(ModeloBaseAdmin):
    # form = PerfilAccesoUsuarioFormAdmin
    list_display = ('grupo', 'coordinacion', 'carrera')
    ordering = ('grupo', )
    list_filter = ('grupo', 'coordinacion', )
    search_fields = ('grupo__name',)

    # class Media:
    #     js = (
    #         'http://ajax.googleapis.com/ajax/libs/jquery/1.9.1/jquery.min.js',
    #     )

class ParroquiaAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'canton')
    ordering = ('nombre', )
    list_filter = ('canton',)


class CantonAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'provincia')
    ordering = ('nombre', )
    list_filter = ('provincia',)


class AreaTituloAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'codigo',)
    ordering = ('nombre', )


class InstitucionEducacionSuperiorAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'codigo',)
    ordering = ('nombre', )


class TituloAdmin(ModeloBaseAdmin):
    search_fields = ('nombre',)
    list_display = ('nombre', 'abreviatura', 'nivel')
    ordering = ('nombre', )
    list_filter = ('nivel',)


class TipoBecaAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'beneficiomonetario', 'becaexterna', 'valormensual')


class ParametrosAutoInscripcionAdmin(ModeloBaseAdmin):
    list_display = ('sede', 'carrera', 'modalidad', 'sesion')

class ActividadAcademicaAdmin(ModeloBaseAdmin):
    search_fields = ('descripcion',)
    list_display = ('descripcion', 'fechainicio', 'fechafin',)
    ordering = ('descripcion', 'fechainicio', 'fechafin',)
    list_filter = ('descripcion', 'fechainicio', 'fechafin',)


class MyGroupAdminForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = '__all__'

    permissions = forms.ModelMultipleChoiceField(Permission.objects.exclude(name__startswith='Can'), widget=admin.widgets.FilteredSelectMultiple(_('permissions'), False), required=False)


class MyGroupAdmin(admin.ModelAdmin):
    form = MyGroupAdminForm
    search_fields = ('name',)
    ordering = ('name',)

    def get_actions(self, request):
        actions = super(MyGroupAdmin, self).get_actions(request)
        if request.user.username not in [x[0] for x in MANAGERS]:
            del actions['delete_selected']
        return actions

    def has_add_permission(self, request):
        return request.user.username in [x[0] for x in MANAGERS]

    def has_change_permission(self, request, obj=None):
        if request.user.username in [x[0] for x in MANAGERS]:
            pass
        else:
            self.readonly_fields = [x.name for x in self.model._meta.local_fields]
        return True

    def has_delete_permission(self, request, obj=None):
        return request.user.username in [x[0] for x in MANAGERS]

    def save_model(self, request, obj, form, change):
        if request.user.username not in [x[0] for x in MANAGERS]:
             raise Exception('Sin permiso a modificacion')
        else:
            return super(MyGroupAdmin, self).save_model(request, obj, form, change)


class MyUserAdminForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = '__all__'

    permissions = forms.ModelMultipleChoiceField(
        Permission.objects.exclude(name__startswith='Can'), widget=admin.widgets.FilteredSelectMultiple(_('permissions'), False), required=False)


class MyUserAdmin(admin.ModelAdmin):
    form = MyUserAdminForm
    filter_horizontal = ('user_permissions', )
    search_fields = ('username',)
    ordering = ('username',)

    def get_actions(self, request):
        actions = super(MyUserAdmin, self).get_actions(request)
        if request.user.username not in [x[0] for x in MANAGERS]:
            del actions['delete_selected']
        return actions

    def has_add_permission(self, request):
        return request.user.username in [x[0] for x in MANAGERS]

    def has_change_permission(self, request, obj=None):
        if request.user.username in [x[0] for x in MANAGERS]:
            pass
        else:
            self.readonly_fields = [x.name for x in self.model._meta.local_fields]
        return True

    def has_delete_permission(self, request, obj=None):
        return request.user.username in [x[0] for x in MANAGERS]

    def save_model(self, request, obj, form, change):
        if request.user.username not in [x[0] for x in MANAGERS]:
             raise Exception('Sin permiso a modificacion')
        else:
            return super(MyUserAdmin, self).save_model(request, obj, form, change)


# class DiasNoLaborableAdmin(ModeloBaseAdmin):
#     list_display = ('periodo', 'motivo', 'fecha', 'desde', 'hasta', 'observaciones', 'coordinacion', 'carrera', 'nivelmalla')
#     ordering = ('fecha',)
#     search_fields = ('periodo',)
#     list_filter = ('motivo', 'periodo', 'coordinacion', 'carrera', 'nivelmalla')


class RubricaAdmin(admin.ModelAdmin):
    list_display = ('proceso', 'nombre', 'descripcion', 'para_hetero', 'para_auto', 'para_par', 'para_directivo', 'para_materiapractica', 'para_nivelacion', 'informativa', 'texto_nosatisfactorio', 'texto_basico', 'texto_competente', 'texto_muycompetente', 'texto_destacado', 'tipo_criterio')
    ordering = ('tipo_criterio', 'nombre')
    search_fields = ('id','nombre')
    list_filter = ('proceso', 'nombre', 'descripcion', 'para_hetero', 'para_auto', 'para_par', 'para_directivo', 'para_materiapractica', 'para_nivelacion', 'informativa', 'texto_nosatisfactorio', 'texto_basico', 'texto_competente', 'texto_muycompetente', 'texto_destacado', 'tipo_criterio')


class InscripcionVinculacionAdmin(admin.ModelAdmin):
    list_display = ('inscripcion', 'cedula', 'nombres')
    ordering = ('nombres',)
    search_fields = ('nombres',)
    list_filter = ('inscripcion', 'cedula')


class ProgramasInvestigacionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'lineainvestigacion', 'fechainicio', 'fechaplaneado', 'fechareal', 'alcanceterritorial', 'areaconocimiento', 'subareaconocimiento', 'subareaespecificaconocimiento')
    ordering = ('nombre',)
    search_fields = ('id', 'nombre',)
    list_filter = ('nombre', 'lineainvestigacion', 'fechainicio', 'fechaplaneado', 'fechareal', 'alcanceterritorial', 'areaconocimiento', 'subareaconocimiento', 'subareaespecificaconocimiento')


class MatrizEvidenciaAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    ordering = ('nombre',)
    search_fields = ('nombre',)
    list_filter = ('nombre',)


class EvidenciaAdmin(admin.ModelAdmin):
    list_display = ('matrizevidencia', 'nombre',)
    ordering = ('nombre',)
    search_fields = ('nombre',)
    list_filter = ('matrizevidencia', 'nombre',)


class SagPreguntaTipoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tienealternativa','min', 'max', 'escala', 'numeromatriz', 'estilo',)
    ordering = ('nombre',)
    search_fields = ('nombre',)
    list_filter = ('nombre', 'tienealternativa',)


class PermisoPeriodoAdmin(admin.ModelAdmin):
    list_display = ('periodo', 'activo',)
    ordering = ('periodo',)
    search_fields = ('periodo',)
    list_filter = ('periodo', 'activo',)


class SagPreguntaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion',)
    ordering = ('nombre',)
    search_fields = ('nombre',)
    list_filter = ('nombre', 'descripcion',)


class PersonaTituloUniversidadAdmin(admin.ModelAdmin):
    list_display = ('persona', 'universidad',)
    ordering = ('persona', 'universidad')
    search_fields = ('persona', 'universidad')
    list_filter = ('persona', 'universidad')


class SagGrupoPreguntaAdmin(admin.ModelAdmin):
    list_display = ('descripcion', 'orden','grupo','observacion','estado','agrupado',)
    ordering = ('orden', 'descripcion')
    search_fields = ('descripcion', 'orden')
    list_filter = ('descripcion', 'orden')


class TipoSolicitudAdmin(admin.ModelAdmin):
    list_display = ('descripcion',)
    ordering = ('descripcion',)
    search_fields = ('descripcion',)
    list_filter = ('descripcion',)


class ActaFacultadAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    ordering = ('nombre',)
    search_fields = ('nombre',)
    list_filter = ('nombre',)


class EvidenciaPracticasProfesionalesAdmin(admin.ModelAdmin):
    list_display = ('nombre','nombrearchivo','orden','puntaje','fechainicio','fechafin')
    ordering = ('nombre',)
    search_fields = ('nombre','nombrearchivo','puntaje','fechainicio','fechafin')
    list_filter = ('nombre',)


class TipoFormacionCarreraAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    ordering = ('nombre',)
    search_fields = ('nombre',)
    list_filter = ('nombre',)


class CredoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activo')
    ordering = ('nombre',)
    search_fields = ('nombre',)
    list_filter = ('nombre',)


class PreferenciaPoliticaAdmin(admin.ModelAdmin):
     list_display = ('nombre','activo' )
     ordering = ('nombre',)
     search_fields = ('nombre',)
     list_filter = ('nombre',)


class PublicarEnlaceAdmin(admin.ModelAdmin):
    list_display = ('nombre','inscripcion', 'docente', 'administrador', 'discapacidad', 'grupo', 'fechainicio', 'fechafin', 'link', 'texto')
    ordering = ('nombre',)
    search_fields = ('nombre',)
    list_filter = ('nombre',)

class ConfiguracionTerceraMatriculaAdmin(admin.ModelAdmin):
    ordering = ('nombre',)
    search_fields = ('nombre',)
    list_filter = ('nombre',)

class RepresentantesFacultadAdmin(admin.ModelAdmin):
    list_display = ('facultad', 'representanteestudiantil', 'representantedocente', 'representantesuplentedocente', 'representanteservidores')
    ordering = ('facultad',)
    search_fields = ('facultad',)
    list_filter = ('facultad',)

class MecanismoTitulacionAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    ordering = ('nombre',)
    search_fields = ('nombre',)
    list_filter = ('nombre',)

class GraduadoMecanismoTitulacionAdmin(admin.ModelAdmin):
    list_display = ('nombre','mecanismotitulacion', 'codigosniese')
    ordering = ('nombre',)
    search_fields = ('nombre',)
    list_filter = ('nombre',)


class TipoNoticiasAdmin(ModeloBaseAdmin):
    list_display = ('nombre', )
    ordering = ('id',)
    search_fields = ('nombre',)


class SugerenciaCongresoAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'fechainicio', 'fechafin', 'pais', 'institucion', 'link', 'observacion')
    ordering = ('id',)
    search_fields = ('nombre',)


class TipoServicioCraiAdmin(ModeloBaseAdmin):
    list_display = ('descripcion',)
    ordering = ('id',)
    search_fields = ('descripcion',)


class TablaReconocimientoCreditosAdmin(ModeloBaseAdmin):
    list_display = ('id',)
    ordering = ('id',)
    search_fields = ('id',)


class ActividadesCraiAdmin(ModeloBaseAdmin):
    list_display = ('descripcion',)
    ordering = ('id',)
    search_fields = ('descripcion',)


class TipoBuzonAdmin(ModeloBaseAdmin):
    list_display = ('descripcion',)
    ordering = ('id',)
    search_fields = ('descripcion',)


class PeriodoCarreraCostoAdmin(ModeloBaseAdmin):
    list_display = ('periodo', 'carrera', 'costo')
    ordering = ('periodo', 'carrera')
    search_fields = ('periodo', 'carrera')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "periodo":
            kwargs["queryset"] = Periodo.objects.filter(tipo_id__in=[3, 4])
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

class ProyectosInvestigacionAdmin(ModeloBaseAdmin):
    list_display = ('programa', 'nombre', 'tipo',)
    ordering = ('programa', 'nombre',)
    search_fields = ('programa', 'nombre',)


class ManualUsuarioAdmin(ModeloBaseAdmin):
    search_fields = ('nombre',)
    list_display = ('nombre', 'version', 'fecha', 'archivo', 'archivofuente', 'observacion', 'visible', )
    ordering = ('nombre', )
    # list_filter = ('nombre',)

class LineaTiempoAdmin(ModeloBaseAdmin):
    search_fields = ('anio','mes','fechainicio','fechafin',)
    list_display = ('anio','mes','fechainicio','fechafin', )
    ordering = ('fechainicio','fechafin',)
    list_filter = ('anio','mes','fechainicio','fechafin',)

admin.site.register(MotivoRetiroMatricula)
admin.site.register(SolicitudRetiroMatricula)
admin.site.register(SolicitudMateriaRetirada)
class PreguntaEncuestaTecnologicaAdmin(ModeloBaseAdmin):
    search_fields = ('descripcion',)
    list_display = ('descripcion', )
    ordering = ('descripcion',)

class EncuestaTecnologicaAdmin(ModeloBaseAdmin):
    search_fields = ('matricula','pregunta',)
    list_display = ('matricula','pregunta',)
    ordering = ('matricula','pregunta',)


class TipoProfesorCriterioPeriodoAdmin(ModeloBaseAdmin):
    search_fields = ('periodo','tipoprofesor','criterio',)
    list_display = ('periodo','tipoprofesor','criterio',)
    ordering = ('periodo','tipoprofesor','criterio',)


class ActividadesMoodleAdmin(ModeloBaseAdmin):
    search_fields = ('descripcion',)
    list_display = ('descripcion',)
    ordering = ('descripcion',)


class CoordinacionReporteAdmin(ModeloBaseAdmin):
    list_display = ('periodo', 'coordinacion')
    ordering = ('periodo', 'coordinacion')
    search_fields = ('periodo', 'coordinacion')


class EncuestaFormsGoogleAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'coordinacion', 'fechainicio', 'fechafin', 'activa', 'obligatoria', 'url')
    ordering = ('fechainicio', 'nombre', 'coordinacion')
    search_fields = ('nombre', 'coordinacion')


class CriterioSubirMatrizInscripcionAdmin(ModeloBaseAdmin):
    list_display = ('orden', 'nombre', 'alias_sistema', 'alias_archivo', 'observacion', 'is_obligatorio', 'is_editable', 'is_valida', 'status')
    ordering = ('orden', 'nombre',)
    search_fields = ('nombre', 'alias_sistema', 'alias_archivo')


class ProcesoSubirMatrizInscripcionAdmin(ModeloBaseTabularAdmin):
    model = My_ProcesoSubirMatrizInscripcion


class TituloProcesoSubirMatrizInscripcionAdmin(ModeloBaseAdmin):
    inlines = [ProcesoSubirMatrizInscripcionAdmin]
    list_display = ('nombre', 'descripcion')
    ordering = ('nombre',)
    search_fields = ('nombre', 'descripcion')


class RespuestaAdmin(ModeloBaseTabularAdmin):
    model = Respuesta


class TipoRespuestaAdmin(ModeloBaseAdmin):
    inlines = [RespuestaAdmin]
    list_display = ('nombre', 'elemento',)
    ordering = ('nombre', 'elemento',)
    search_fields = ('nombre', 'elemento',)


class SilaboAdmin(ModeloBaseAdmin):
    list_display = ('id', 'idmateria', 'versionsilabo', 'versionrecurso', 'codigoqr', 'status')
    ordering = ('id',)
    search_fields = ('id' , 'materia__id')
    fields = ['id','idmateria','versionsilabo', 'versionrecurso', 'codigoqr', 'status']
    readonly_fields = ['id', 'idmateria']

    def idmateria(self,obj):
        return '%s' % (obj.materia_id)


class SilaboSemanalAdmin(ModeloBaseAdmin):
    list_display = ('id', 'idsilabo', 'idmateria', 'numsemana', 'semana', 'fechainiciosemana', 'fechafinciosemana', 'status')
    ordering = ('id', 'numsemana', 'semana')
    search_fields = ('id', 'silabo__id', 'silabo__materia__id')
    fields = ['id','idsilabo', 'idmateria','numsemana', 'semana', 'fechainiciosemana', 'fechafinciosemana', 'status']
    readonly_fields = ['id','idsilabo', 'idmateria']

    def idsilabo(self,obj):
        return '%s' % (obj.silabo_id)

    def idmateria(self,obj):
        return '%s' % (obj.silabo.materia_id)


class TareaSilaboSemanalAdmin(ModeloBaseAdmin):
    list_display = ('id', 'nombre','actividad' ,'idmateria','idsilabo','idsilabosemanal','idtareamoodle', 'estado', 'status')
    ordering = ('silabosemanal__id',)
    search_fields = ('id', 'nombre' , 'idtareamoodle','silabosemanal__id','silabosemanal__silabo__id','silabosemanal__silabo__materia__id')
    fields = ['idsilabo', 'idsilabosemanal','idtareamoodle','estado', 'nombre', 'fechadesde', 'fechahasta', 'status']
    readonly_fields = ['idsilabo', 'idsilabosemanal']

    def idsilabo(self, obj):
        return '%s' % (obj.silabosemanal.silabo_id)

    def idsilabosemanal(self, obj):
        return '%s' % (obj.silabosemanal_id)

    def idmateria(self, obj):
        return '%s' % (obj.silabosemanal.silabo.materia_id)


class TareaPracticaSilaboSemanalAdmin(ModeloBaseAdmin):
    list_display = ('id', 'nombre','idmateria','idsilabo','idsilabosemanal','idtareapracticamoodle', 'estado', 'status')
    ordering = ('silabosemanal__id',)
    search_fields = ('id', 'nombre' , 'idtareapracticamoodle','silabosemanal__id','silabosemanal__silabo__id','silabosemanal__silabo__materia__id')
    fields = ['idsilabo', 'idsilabosemanal','idtareapracticamoodle','estado', 'nombre', 'fechadesde', 'fechahasta', 'status']
    readonly_fields = ['idsilabo', 'idsilabosemanal']

    def idsilabo(self, obj):
        return '%s' % (obj.silabosemanal.silabo_id)

    def idsilabosemanal(self, obj):
        return '%s' % (obj.silabosemanal_id)

    def idmateria(self, obj):
        return '%s' % (obj.silabosemanal.silabo.materia_id)


class TestSilaboSemanalAdmin(ModeloBaseAdmin):
    list_display = ('id', 'nombretest' ,'idmateria','idsilabo','idsilabosemanal', 'idtestmoodle' , 'estado', 'status')
    ordering = ('silabosemanal__id',)
    search_fields = ('id', 'nombretest', 'idtestmoodle','silabosemanal__id','silabosemanal__silabo__id','silabosemanal__silabo__materia__id')
    fields = ['idsilabo', 'idsilabosemanal', 'idtestmoodle','status','estado', 'nombretest', 'fechadesde', 'fechahasta']
    readonly_fields = ['idsilabo', 'idsilabosemanal']

    def idsilabo(self,obj):
        return '%s' % (obj.silabosemanal.silabo_id)

    def idsilabosemanal(self,obj):
        return '%s' % (obj.silabosemanal_id)

    def idmateria(self,obj):
        return '%s' % (obj.silabosemanal.silabo.materia_id)

class ForoSilaboSemanalAdmin(ModeloBaseAdmin):
    list_display = ('id' ,'nombre' ,'objetivo' ,'idmateria','idsilabo','idsilabosemanal','idforomoodle' , 'estado', 'status')
    ordering = ('silabosemanal__id',)
    search_fields = ('id', 'idforomoodle' , 'nombre', 'objetivo','silabosemanal__id','silabosemanal__silabo__id','silabosemanal__silabo__materia__id')
    fields = ['idsilabo', 'idsilabosemanal', 'idforomoodle','status','estado', 'nombre', 'objetivo', 'fechadesde', 'fechahasta']
    readonly_fields = ['idsilabo', 'idsilabosemanal']

    def idsilabo(self, obj):
        return '%s' % (obj.silabosemanal.silabo_id)

    def idsilabosemanal(self, obj):
        return '%s' % (obj.silabosemanal_id)

    def idmateria(self, obj):
        return '%s' % (obj.silabosemanal.silabo.materia_id)


class ClaseAsincronicaAdmin(ModeloBaseAdmin):
    list_display = ('id' ,'numerosemana' ,'idforomoodle' ,'fechaforo','fecha_creacion', 'enlaceuno', 'status')
    ordering = ('id', 'idforomoodle' , 'fechaforo')
    search_fields = ('id', 'idforomoodle' , 'fechaforo')
    fields = ['numerosemana' ,'idforomoodle' ,'fechaforo', 'enlaceuno','enlacedos','enlacetres','diferido', 'status']


class EvaluacionAprendizajeComponenteAdmin(ModeloBaseAdmin):
    list_display = ('id' ,'tipoevaluacion' ,'descripcion' ,'alias', 'color', 'categoriamoodle', 'status')
    ordering = ('descripcion','tipoevaluacion')
    search_fields = ('id', 'descripcion')
    fields = ['tipoevaluacion' ,'descripcion' , 'alias', 'color', 'categoriamoodle', 'status']


class DiapositivaSilaboSemanalAdmin(ModeloBaseAdmin):
    list_display = ('id' ,'idsilabo','idsilabosemanal','descripcion' ,'nombre' , 'iddiapositivamoodle','estado', 'status')
    ordering = ('fecha_creacion',)
    search_fields = ('id','descripcion' ,'silabosemanal__silabo__id','silabosemanal__id',)
    fields = ['idsilabo','idsilabosemanal','estado', 'iddiapositivamoodle', 'status', 'descripcion', 'nombre', 'tipomaterial']
    readonly_fields = ['idsilabo','idsilabosemanal']

    def idsilabo(self,obj):
        return '%s' % (obj.silabosemanal.silabo_id)

    def idsilabosemanal(self,obj):
        return '%s' % (obj.silabosemanal_id)

class CompendioSilaboSemanalAdmin(ModeloBaseAdmin):
    list_display = ('id' ,'idsilabo','idsilabosemanal','idmateria','descripcion' ,'estado', 'idmcompendiomoodle', 'status')
    ordering = ('fecha_creacion',)
    search_fields = ('id','descripcion','idmcompendiomoodle','silabosemanal__silabo__id','silabosemanal__id','silabosemanal__silabo__materia__id')
    fields = ['idsilabo', 'idsilabosemanal','estado' , 'idmcompendiomoodle', 'status','descripcion' ]
    readonly_fields = ['idsilabo', 'idsilabosemanal']

    def idsilabo(self,obj):
        return '%s' % (obj.silabosemanal.silabo_id)

    def idsilabosemanal(self,obj):
        return '%s' % (obj.silabosemanal_id)

    def idmateria(self,obj):
        return '%s' % (obj.silabosemanal.silabo.materia_id)


class GuiaEstudianteSilaboSemanalAdmin(ModeloBaseAdmin):
    list_display = ('id' ,'idsilabo','idsilabosemanal','idmateria','observacion', 'idguiaestudiantemoodle','estado', 'status')
    ordering = ('fecha_creacion',)
    search_fields = ('id','observacion','idguiaestudiantemoodle','silabosemanal__silabo__id','silabosemanal__id','silabosemanal__silabo__materia__id')
    fields = ['idsilabo', 'idsilabosemanal', 'idguiaestudiantemoodle','estado', 'status', 'observacion']
    readonly_fields = ['idsilabo', 'idsilabosemanal']

    def idsilabo(self,obj):
        return '%s' % (obj.silabosemanal.silabo_id)

    def idsilabosemanal(self,obj):
        return '%s' % (obj.silabosemanal_id)

    def idmateria(self,obj):
        return '%s' % (obj.silabosemanal.silabo.materia_id)

class MaterialAdicionalSilaboSemanalAdmin(ModeloBaseAdmin):
    list_display = ('id' ,'idsilabo','idsilabosemanal','idmateria','nombre', 'descripcion', 'idmaterialesmoodle','estado', 'status')
    ordering = ('fecha_creacion',)
    search_fields = ('id','nombre','descripcion','idmaterialesmoodle','silabosemanal__silabo__id','silabosemanal__id','silabosemanal__silabo__materia__id')
    fields = ['idsilabo', 'idsilabosemanal', 'idmaterialesmoodle','estado', 'status','nombre','descripcion','tiporecurso']
    readonly_fields = ['idsilabo', 'idsilabosemanal']

    def idsilabo(self,obj):
        return '%s' % (obj.silabosemanal.silabo_id)

    def idsilabosemanal(self,obj):
        return '%s' % (obj.silabosemanal_id)

    def idmateria(self,obj):
        return '%s' % (obj.silabosemanal.silabo.materia_id)


class UsuarioLdapAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'status')
    ordering = ('id', 'usuario')
    search_fields = ('id', 'usuario')
    fields = ['usuario','status']


class PlanificarCapacitacionesAdmin(admin.ModelAdmin):
    list_display = ('id', 'tema', 'fechainicio', 'fechafin', 'estado')
    ordering = ('id', 'tema')
    search_fields = ('id', 'tema', 'profesor__persona__apellido1', 'profesor__persona__apellido2')
    fields = ['tema', 'fechainicio', 'fechafin', 'estado', 'usuario_modificacion']


class PlanificarCapacitacionesRecorridoAdmin(admin.ModelAdmin):
    list_display = ('id', 'planificarcapacitaciones', 'idcapacitacion', 'observacion', 'estado', 'fecha')
    ordering = ('id', 'planificarcapacitaciones', 'estado')
    search_fields = ('id', 'planificarcapacitaciones__tema', 'planificarcapacitaciones__profesor__persona__apellido1', 'planificarcapacitaciones__profesor__persona__apellido2')
    fields = ['planificarcapacitaciones', 'observacion', 'estado', 'fecha', 'persona']

    def idcapacitacion(self, obj):
        return '%s' % (obj.planificarcapacitaciones_id)


class ActividadConvalidacionPPVAdmin(admin.ModelAdmin):
    list_display = ('id', 'titulo', 'profesor', 'estado')
    ordering = ('id', 'titulo')
    search_fields = ('titulo', 'profesor__persona__apellido1', 'profesor__persona__apellido2')
    fields = ('titulo', 'estado')


class SolicitudRefinanciamientoPosgradoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombreprofesor', 'motivo', 'estado')
    ordering = ('id', )
    search_fields = ('id', 'persona__apellido1', 'persona__apellido2')
    fields = ('persona', 'motivo', 'estado')

    def nombreprofesor(self, obj):
        return '%s' % (obj.persona.nombre_completo())


class SolicitudRefinanciamientoPosgradoRecorridoAdmin(admin.ModelAdmin):
    list_display = ('id', 'solicitud', 'fecha', 'observacion', 'estado')
    ordering = ('id',)
    search_fields = ('id', 'solicitud__persona__apellido1', 'solicitud__persona__apellido2')
    fields = ('solicitud', 'observacion', 'estado')


class RubricaMoodleAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipotarea', 'estado','profesor',)
    ordering = ('nombre', 'tipotarea', 'estado','profesor',)
    search_fields = ('nombre', 'profesor__persona__apellido1','profesor__persona__apellido2',)
    fields = ('nombre', 'tipotarea', 'estado','profesor',)


class PonderacionSeguimientoAdmin(admin.ModelAdmin):
    list_display = ('periodo', 'tiposeguimiento', 'porcentaje',)
    ordering = ('periodo', 'tiposeguimiento', 'porcentaje',)
    search_fields = ('periodo__nombre',)
    fields = ('periodo', 'tiposeguimiento', 'porcentaje',)


class RespuestaEvaluacionAcreditacionAdmin(ModeloBaseAdmin):
    list_display = ('id', 'tipoinstrumento','profesor', 'evaluador', 'proceso', 'status')
    ordering = ('id', 'profesor')
    search_fields = ('id', 'profesor__persona__apellido1', 'profesor__persona__apellido2')
    fields = ['tipoinstrumento',  'idprofesor', 'status']
    readonly_fields = ['idprofesor']

    def idprofesor(self, obj):
        return '%s' % (obj.profesor_id)


class DetalleInstrumentoEvaluacionDirectivoAcreditacionAdmin(ModeloBaseAdmin):
    list_display = ('id', 'evaluado', 'evaluador', 'proceso', 'coordinacion', 'status')
    ordering = ('id', 'evaluado')
    search_fields = ('id', 'evaluador__apellido1', 'evaluador__apellido2')
    fields = ['idevaluado', 'status']
    readonly_fields = ['idevaluado']

    def idevaluado(self, obj):
        return '%s' % (obj.evaluado_id)


class NotificacionDeudaPeriodoAdmin(ModeloBaseAdmin):
    list_display = ('periodo', 'fechainicionotificacion', 'fechafinnotificacion', 'vigente')
    ordering = ('-periodo__inicio', '-fechainicionotificacion')
    search_fields = ('periodo__nombre',)
    raw_id_fields = ('periodo',)
    filter_horizontal = ('coordinaciones', 'tiposrubros')
    fieldsets = [
        (None, {'fields': ['periodo', 'vigente']}),
        ('Fechas de Notificación', {'fields': ['fechainicionotificacion', 'fechafinnotificacion']}),
        (None, {'fields': ['archivo', 'coordinaciones', 'tiposrubros']}),
        (None, {'fields': ['logicanotificacion']}),
    ]


class NivelTitulacionAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'rango','codigo_tthh','tipo','status', )
    ordering = ('nombre', 'tipo', )
    search_fields = ('nombre', 'tipo', )
    fields = ['nombre', 'rango','codigo_tthh','nivel', 'tipo','status', ]

# class TipoRecursoAdmin(admin.ModelAdmin):
#     list_display = ('descripcion',)
#     ordering = ('descripcion',)
#     search_fields = ('descripcion',)
#     fields = ('status','descripcion',)
#
# class ConfiguracionRecursoAdmin(admin.ModelAdmin):
#     list_display = ('tiporecurso','carrera','periodo','tipoarchivo',)
#     ordering = ('tiporecurso',)
#     search_fields = ('carrera__nombre','periodo__nombre')
#     fields = ('status','tiporecurso','carrera','periodo','tipoarchivo',)
#     raw_id_fields = ('tiporecurso','carrera','periodo',)

class DetPersonaPadronElectoralAdmin(admin.ModelAdmin):
    list_display = ('persona','tipo','lugarmesa','enmesa',)
    ordering = ('persona','tipo',)
    search_fields = ('persona__apellido1','persona__apellido2','persona__nombres',)
    raw_id_fields = ('persona',)
    fields = ('status','cab', 'persona','tipo','bloque','mesa','horario','lugar','enmesa','lugarmesa','puede_justificar',)


class PorcentajeDescuentoBecaPosgradoAdmin(ModeloBaseAdmin):
    list_display = ('id', 'detalleconfiguraciondescuentoposgrado', 'descripcion', 'gruposocioecon', 'rangodesde', 'rangohasta', 'porcentaje')
    ordering = ('id', 'rangodesde', 'rangohasta')
    # search_fields = ('descripcion', )


class CriterioLinkAdmin(ModeloBaseAdmin):
    list_display = ('link', 'tipolink', 'tipocriterio', 'archivo')
    ordering = ('tipocriterio',)

class AsesoramientoSEETipoTrabajoAdmin(ModeloBaseAdmin):
    list_display = ('nombre',)
    ordering = ('nombre',)

class AsesoramientoSEEAdmin(ModeloBaseAdmin):
    list_display = ('persona','titulo','descripcion','estado')
    ordering = ('persona',)


class HorarioExamenAdmin(ModeloBaseTabularAdmin):
    model = HorarioExamenDetalle



class DetalleHorarioExamenAdmin(ModeloBaseAdmin):
    inlines = [HorarioExamenAdmin]
    ordering = ('materia_id',)
    search_fields = ('materia_id',)


class CursoEscuelaComplementariaAdmin(ModeloBaseAdmin):
    list_display = ('nombre',)
    ordering = ('nombre',)
    search_fields = ('nombre',)

class RequisitoBecaAdmin(ModeloBaseAdmin):
    list_display = ('nombre',)
    ordering = ('nombre',)
    search_fields = ('nombre',)

class InstitucionCertificadoraAdmin(ModeloBaseAdmin):
    list_display = ('nombre',)
    ordering = ('nombre',)
    search_fields = ('nombre',)

class ModuloCategoriasAdmin(ModeloBaseAdmin):
    list_display = ('nombre',)
    ordering = ('nombre',)
    search_fields = ('nombre',)

class NivelSuficenciaAdmin(ModeloBaseAdmin):
    list_display = ('descripcion',)
    ordering = ('descripcion',)
    search_fields = ('descripcion',)

class SesionZoomAdmin(ModeloBaseAdmin):
    list_display = ('materiaasignada','modulo','fecha','hora','horaultima','activo',)
    ordering = ('materiaasignada',)
    search_fields = ('materiaasignada__matricula__inscripcion__persona__nombres', 'materiaasignada__matricula__inscripcion__persona__apellido1', 'materiaasignada__matricula__inscripcion__persona__apellido2',)

class TipoGastoAdmin(ModeloBaseAdmin):
    list_display = ('nombre',)
    ordering = ('nombre',)
    search_fields = ('nombre',)

class TipoTransporteAdmin(ModeloBaseAdmin):
    list_display = ('nombre',)
    ordering = ('nombre',)
    search_fields = ('nombre',)

class LugarAlimentacionAdmin(ModeloBaseAdmin):
    list_display = ('nombre',)
    ordering = ('nombre',)
    search_fields = ('nombre',)

class LugarCompraAlimentosAdmin(ModeloBaseAdmin):
    list_display = ('nombre',)
    ordering = ('nombre',)
    search_fields = ('nombre',)

class OperadoraMovilAdmin(ModeloBaseAdmin):
    list_display = ('nombre',)
    ordering = ('nombre',)
    search_fields = ('nombre',)


class ConvocatoriaPonenciaAdmin(ModeloBaseAdmin):
    list_display = ('id', 'descripcion', 'iniciopos', 'finpos', 'publicada')
    ordering = ('id', 'descripcion', 'iniciopos', 'finpos')
    search_fields = ('descripcion',)


class CriterioPonenciaAdmin(ModeloBaseAdmin):
    list_display = ('id', 'descripcion', 'tipoponencia', 'orden', 'obligatorio')
    ordering = ('id', 'descripcion', 'tipoponencia', 'orden')
    search_fields = ('descripcion',)


class SedeVirtualPeriodoAcademicoAdmin(ModeloBaseAdmin):
    list_display = ('id', 'sedevirtual', 'periodo')
    ordering = ('id', 'periodo', 'sedevirtual')
    # search_fields = ('sedevirtual__nombre',)


class PersonaDetalleMaternidadExtensionSaludAdmin(ModeloBaseAdmin):
    list_display = ('id', 'personamaternidad', 'fecha', 'estadoaprobacion')
    ordering = ('id', 'personamaternidad', 'fecha')
    # search_fields = ('sedevirtual__nombre',)


class TipoSolicitudInformacionPadronElectoralAdmin(ModeloBaseAdmin):
    list_display = ('id', 'descripcion')

class PlanificarCapacitacionesCriteriosAdmin(ModeloBaseAdmin):
    list_display = ('id', 'status', 'tipo', 'criterio', 'obligatoriosolicitante')


admin.site.register(TipoSolicitudInformacionPadronElectoral, TipoSolicitudInformacionPadronElectoralAdmin)
admin.site.register(CursoEscuelaComplementaria, CursoEscuelaComplementariaAdmin)
admin.site.register(VideoUnidadResultadoProgramaAnaliticoEliminado)
admin.site.register(VideoTemaProgramaAnaliticoEliminado)
admin.site.register(VideoSubTemaProgramaAnaliticoEliminado)
admin.site.register(RecursoUnidadProgramaAnaliticoEliminado)
admin.site.register(RecursoTemaProgramaAnaliticoEliminado)
admin.site.register(RecursoSubTemaProgramaAnaliticoEliminado)
admin.site.register(PeriodoCarreraCosto, PeriodoCarreraCostoAdmin)
admin.site.register(TablaReconocimientoCreditos, TablaReconocimientoCreditosAdmin)
admin.site.register(Zona, ModeloBaseAdmin)
admin.site.register(PersonaTituloUniversidad, PersonaTituloUniversidadAdmin)
admin.site.register(MatrizEvidencia, MatrizEvidenciaAdmin)
admin.site.register(Evidencia, EvidenciaAdmin)
admin.site.register(ProgramasInvestigacion, ProgramasInvestigacionAdmin)
admin.site.register(InscripcionVinculacion, InscripcionVinculacionAdmin)
admin.site.register(PreInscrito, PreInscritoAdmin)
admin.site.register(AulaCoordinacion, AulaCoordinacionAdmin)
admin.site.register(TipoInscripcion, ModeloBaseAdmin)
admin.site.register(TipoInstitucion, ModeloBaseAdmin)
admin.site.register(ObservacionSeguimiento, ModeloBaseAdmin)
admin.site.register(SeguimientoPreInscrito, ModeloBaseAdmin)
admin.site.register(TipoRelacion, ModeloBaseAdmin)
admin.site.register(Relacion, RelacionAdmin)
admin.site.register(CategoriaHerramienta, ModeloBaseAdmin)
admin.site.register(ConocimientoHerramienta, ModeloBaseAdmin)
admin.site.register(ConocimientoInformatico, ModeloBaseAdmin)
admin.site.register(ConocimientoAdiconal, ModeloBaseAdmin)
admin.site.register(TipoProyecto, ModeloBaseAdmin)
admin.site.register(Programa, ModeloBaseAdmin)
admin.site.register(ProyectosVinculacion, ModeloBaseAdmin)
admin.site.register(CoordinadorCarrera, CoordinadorCarreraAdmin)
admin.site.register(AmbitoInstrumentoEvaluacion, AmbitoInstrumentoEvaluacionAdmin)
admin.site.register(IndicadorAmbitoInstrumentoEvaluacion, IndicadorAmbitoInstrumentoEvaluacionAdmin)
admin.site.register(ProcesoEvaluativo, ProcesoEvaluativoAdmin)
admin.site.register(EvaluacionProfesor, EvaluacionProfesorAdmin)
admin.site.register(DatoInstrumentoEvaluacion, DatoInstrumentoEvaluacionAdmin)
admin.site.register(AmbitoEvaluacion, ModeloBaseAdmin)
admin.site.register(IndicadorEvaluacion, ModeloBaseAdmin)
admin.site.register(InstrumentoEvaluacion, ModeloBaseAdmin)
admin.site.register(TipoActividadExtraCurricular, ModeloBaseAdmin)
admin.site.register(ActividadExtraCurricular, ActividadExtraCurricularAdmin)
admin.site.register(ParticipanteActividadExtraCurricular, ParticipanteActividadExtraCurricularAdmin)
admin.site.register(TipoMatricula, ModeloBaseAdmin)
admin.site.register(ComoSeInformo, ModeloBaseAdmin)
admin.site.register(RazonesMotivaron, ModeloBaseAdmin)
admin.site.register(PagoCalendario, PagoCalendarioAdmin)
admin.site.register(ProfesorTipo, ProfesorTipoAdmin)
admin.site.register(LogEntry, LogEntryAdmin)
admin.site.register(CodigoEvaluacion, CodigoEvaluacionAdmin)
admin.site.register(Sesion, SesionAdmin)
admin.site.register(TipoArchivo, ModeloBaseAdmin)
admin.site.register(Archivo, ArchivoAdmin)
admin.site.register(Graduado, GraduadoAdmin)
admin.site.register(Egresado, EgresadoAdmin)
admin.site.register(TipoEstado, ModeloBaseAdmin)
admin.site.register(RetiroMatricula, RetiradoMatriculaAdmin)
admin.site.register(DocumentosDeInscripcion, DocumentosDeInscripcionAdmin)
admin.site.register(SolicitudSecretariaDocente, SolicitudSecretariaDocenteAdmin)
admin.site.register(TipoSolicitudSecretariaDocente, ModeloBaseAdmin)
admin.site.register(Leccion, LeccionAdmin)
admin.site.register(LeccionGrupo, LeccionGrupoAdmin)
admin.site.register(MateriaAsignada, MateriaAsignadaAdmin)
admin.site.register(Matricula, MatriculaAdmin)
admin.site.register(Inscripcion, InscripcionAdmin)
admin.site.register(Persona, PersonaAdmin)
admin.site.register(Asignatura, AsignaturaAdmin)
admin.site.register(Periodo, PeriodoAdmin)
admin.site.register(AsignaturaMalla, AsignaturaMallaAdmin)
admin.site.register(Nivel, NivelAdmin)
admin.site.register(Materia, MateriaAdmin)
admin.site.register(Malla, MallaAdmin)
admin.site.register(Aula, AulaAdmin)
admin.site.register(Turno, TurnoAdmin)
admin.site.register(Modulo, ModuloAdmin)
admin.site.register(ModuloGrupo, ModuloGrupoAdmin)
admin.site.register(Clase, ClaseAdmin)
admin.site.register(Profesor, ProfesorAdmin)
admin.site.register(InscripcionMalla, InscripcionMallaAdmin)
admin.site.register(EstadoCarrera, EstadoCarreraAdmin)
admin.site.register(Carrera, CarreraAdmin)
admin.site.register(Impresion, ImpresionAdmin)
admin.site.register(CargoInstitucion, CargoInstitucionAdmin)
admin.site.register(InscripcionFlags, InscripcionFlagsAdmin)
admin.site.register(TituloInstitucion, TituloInstitucionAdmin)
admin.site.register(ConvalidacionInscripcion, ConvalidacionInscripcionAdmin)
admin.site.register(TipoCertificacion, ModeloBaseAdmin)
admin.site.register(Provincia, ModeloBaseAdmin)
admin.site.register(PlanificacionMateria, ModeloBaseAdmin)
admin.site.register(MateriaAsignadaPlanificacion, ModeloBaseAdmin)
admin.site.register(Canton, CantonAdmin)
admin.site.register(Parroquia, ParroquiaAdmin)
admin.site.register(Sexo, ModeloBaseAdmin)
admin.site.register(Colegio, ColegioAdmin)
admin.site.register(Sede, ModeloBaseAdmin)
admin.site.register(SedeVirtual, ModeloBaseAdmin)
admin.site.register(SedeProvincia, ModeloBaseAdmin)
admin.site.register(Industria, ModeloBaseAdmin)
admin.site.register(NivelCargo, ModeloBaseAdmin)
admin.site.register(RangoSalario, ModeloBaseAdmin)
admin.site.register(TipoActividad, ModeloBaseAdmin)
admin.site.register(Actividad, ModeloBaseAdmin)
admin.site.register(NivelMalla, ModeloBaseAdmin)
admin.site.register(EjeFormativo, ModeloBaseAdmin)
admin.site.register(TipoAula, ModeloBaseAdmin)
admin.site.register(ModeloImpresion, ModeloBaseAdmin)
admin.site.register(TiempoDedicacionDocente, ModeloBaseAdmin)
admin.site.register(NivelTitulacion, NivelTitulacionAdmin)
admin.site.register(Especialidad, EspecialidadAdmin)
admin.site.register(ItemExamenComplexivo, ItemExamenComplexivoAdmin)
admin.site.register(Coordinacion, CoordinacionAdmin)
admin.site.register(CategorizacionDocente, CategorizacionDocenteAdmin)
admin.site.register(CargoDocente, ModeloBaseAdmin)
admin.site.register(NivelEscalafonDocente, ModeloBaseAdmin)
admin.site.register(TipoPeriodo, ModeloBaseAdmin)
admin.site.register(Modalidad, ModeloBaseAdmin)
admin.site.register(TipoSangre, ModeloBaseAdmin)
admin.site.register(CategoriaReporte, ModeloBaseAdmin)
admin.site.register(FotoPersona, ModeloBaseAdmin)
admin.site.register(Raza, ModeloBaseAdmin)
admin.site.register(EstratoSociocultural, ModeloBaseAdmin)
admin.site.register(Discapacidad, ModeloBaseAdmin)
admin.site.register(TipoBeca, TipoBecaAdmin)
admin.site.register(Grupo, GrupoAdmin)
admin.site.register(GrupoCoordinadorCarrera, GrupoCoordinadorCarreraAdmin)
admin.site.register(GrupoCoordinadorCoordinacion, GrupoCoordinadorCoordinacionAdmin)
admin.site.register(Reporte, ReporteAdmin)
admin.site.register(TipoIncidencia, TipoIncidenciaAdmin)
admin.site.register(Incidencia, IncidenciaAdmin)
admin.site.register(Mensaje, ModeloBaseAdmin)
admin.site.register(Pasantia, ModeloBaseAdmin)
admin.site.register(Idioma, ModeloBaseAdmin)
admin.site.register(CentroInformacion, ModeloBaseAdmin)
admin.site.register(Empleador, ModeloBaseAdmin)
admin.site.register(EmpresaEmpleadora, ModeloBaseAdmin)
admin.site.register(AplicanteOferta, AplicanteOfertaAdmin)
admin.site.register(OfertaLaboral, ModeloBaseAdmin)
admin.site.register(IdiomaDomina, ModeloBaseAdmin)
admin.site.register(TipoCurso, ModeloBaseAdmin)
admin.site.register(MensajeDestinatario, ModeloBaseAdmin)
admin.site.register(AgregacionEliminacionMaterias, AgregacioneliminacionmateriasAdmin)
admin.site.register(Pais, ModeloBaseAdmin)
admin.site.register(Nacionalidades, ModeloBaseAdmin)
admin.site.register(TipoMateria, ModeloBaseAdmin)
admin.site.register(TipoPlanificacion, ModeloBaseAdmin)
admin.site.register(PalabrasProhibidasEvaluacionIntegral, ModeloBaseAdmin)
admin.site.register(TipoEvaluacionGeneralEvaluacionIntegral, ModeloBaseAdmin)
admin.site.register(TipoRespuestaEvaluacionIntegral, ModeloBaseAdmin)
admin.site.register(Encuesta, ModeloBaseAdmin)
admin.site.register(ProcesoEvaluativoIntegral, ModeloBaseAdmin)
admin.site.register(SubTipoComponenteEvaluacionIntegral, ModeloBaseAdmin)
admin.site.register(TipoComponenteEvaluacionIntegral, ModeloBaseAdmin)
admin.site.register(ModeloEvaluativo, ModeloBaseAdmin)
admin.site.register(DetalleModeloEvaluativo, DetalleModeloEvaluativoAdmin)
admin.site.register(AreaConocimiento, ModeloBaseAdmin)
admin.site.register(SubAreaConocimiento, ModeloBaseAdmin)
admin.site.register(Titulo, TituloAdmin)
admin.site.register(AreaTitulo, AreaTituloAdmin)
admin.site.register(InstitucionEducacionSuperior, InstitucionEducacionSuperiorAdmin)
admin.site.register(FuenteFinanciamiento, ModeloBaseAdmin)
admin.site.register(TipoGrado, ModeloBaseAdmin)
admin.site.register(TipoTrabajoTitulacion, ModeloBaseAdmin)
admin.site.register(LineaInvestigacion, ModeloBaseAdmin)
#admin.site.register(Respuesta, ModeloBaseAdmin)
admin.site.register(TipoRespuesta, TipoRespuestaAdmin)
admin.site.register(SubLineaInvestigacion, ModeloBaseAdmin)
admin.site.register(ResponsableCoordinacion, ResponsableCoordinacionAdmin)
admin.site.register(TipoEvaluacionEvaluacion, TipoEvaluacionEvaluacionAdmin)
admin.site.register(InscripcionNivel, InscripcionNivelAdmin)
admin.site.register(CostoPeriodoTipoInscripcion, CostoPeriodoTipoInscripcionAdmin)
admin.site.register(ParametrosAutoInscripcion, ParametrosAutoInscripcionAdmin)
admin.site.register(CriterioDocencia, ModeloBaseAdmin)
admin.site.register(CriterioGestion, ModeloBaseAdmin)
admin.site.register(TipoCapacitacion, ModeloBaseAdmin)
admin.site.register(TipoParticipacion, ModeloBaseAdmin)
admin.site.register(CriterioInvestigacion, ModeloBaseAdmin)
admin.site.register(CriterioDocenciaPeriodo, ModeloBaseAdmin)
admin.site.register(CriterioGestionPeriodo, ModeloBaseAdmin)
admin.site.register(CriterioInvestigacionPeriodo, ModeloBaseAdmin)
admin.site.register(FinanciamientoBeca, ModeloBaseAdmin)
admin.site.register(GradoTitulacion, ModeloBaseAdmin)
admin.site.register(TipoProfesor, ModeloBaseAdmin)
admin.site.register(PerfilAccesoUsuario, PerfilAccesoUsuarioAdmin)
admin.site.unregister(Group)
admin.site.register(Group, MyGroupAdmin)
admin.site.unregister(User)
admin.site.register(User, MyUserAdmin)
# admin.site.register(DiasNoLaborable, DiasNoLaborableAdmin)
admin.site.register(MatrizInscripcion, MatrizInscripcionAdmin)
admin.site.register(ContextoCapacitacion, ModeloBaseAdmin)
admin.site.register(DetalleContextoCapacitacion, ModeloBaseAdmin)
admin.site.register(Rubrica, ModeloBaseAdmin)
admin.site.register(SagPreguntaTipo, SagPreguntaTipoAdmin)
admin.site.register(PermisoPeriodo, PermisoPeriodoAdmin)
admin.site.register(SagPregunta, SagPreguntaAdmin)
admin.site.register(TipoSolicitud, TipoSolicitudAdmin)
admin.site.register(SagGrupoPregunta, SagGrupoPreguntaAdmin)
admin.site.register(ActaFacultad, ActaFacultadAdmin)
admin.site.register(EvidenciaPracticasProfesionales, EvidenciaPracticasProfesionalesAdmin)
admin.site.register(TipoFormacionCarrera, TipoFormacionCarreraAdmin)
admin.site.register(Credo, CredoAdmin)
admin.site.register(PreferenciaPolitica, PreferenciaPoliticaAdmin)
admin.site.register(PublicarEnlace, PublicarEnlaceAdmin)
admin.site.register(ConfiguracionTerceraMatricula, ConfiguracionTerceraMatriculaAdmin)
admin.site.register(RepresentantesFacultad, RepresentantesFacultadAdmin)
admin.site.register(MecanismoTitulacion, MecanismoTitulacionAdmin)
admin.site.register(GraduadoMecanismoTitulacion, GraduadoMecanismoTitulacionAdmin)
admin.site.register(TipoNoticias, TipoNoticiasAdmin)
admin.site.register(SugerenciaCongreso, SugerenciaCongresoAdmin)
admin.site.register(TipoServicioCrai, TipoServicioCraiAdmin)
admin.site.register(ActividadesCrai, ActividadesCraiAdmin)
admin.site.register(TipoBuzon, TipoBuzonAdmin)
admin.site.register(ProyectosInvestigacion, ProyectosInvestigacionAdmin)
admin.site.register(ManualUsuario, ManualUsuarioAdmin)
admin.site.register(ActividadAcademica, ActividadAcademicaAdmin)
admin.site.register(LineaTiempo, LineaTiempoAdmin)
admin.site.register(EncuestaTecnologica, EncuestaTecnologicaAdmin)
admin.site.register(PreguntaEncuestaTecnologica, PreguntaEncuestaTecnologicaAdmin)
admin.site.register(TipoProfesorCriterioPeriodo, TipoProfesorCriterioPeriodoAdmin)
admin.site.register(ActividadesMoodle, ActividadesMoodleAdmin)
admin.site.register(CoordinacionReporte, CoordinacionReporteAdmin)
admin.site.register(EncuestaFormsGoogle, EncuestaFormsGoogleAdmin)
admin.site.register(My_CriterioSubirMatrizInscripcion, CriterioSubirMatrizInscripcionAdmin)
admin.site.register(My_TituloProcesoSubirMatrizInscripcion, TituloProcesoSubirMatrizInscripcionAdmin)
admin.site.register(Silabo, SilaboAdmin)
admin.site.register(SilaboSemanal, SilaboSemanalAdmin)
admin.site.register(TareaSilaboSemanal, TareaSilaboSemanalAdmin)
admin.site.register(TareaPracticaSilaboSemanal, TareaPracticaSilaboSemanalAdmin)
admin.site.register(TestSilaboSemanal, TestSilaboSemanalAdmin)
admin.site.register(ForoSilaboSemanal, ForoSilaboSemanalAdmin)
admin.site.register(ClaseAsincronica, ClaseAsincronicaAdmin)
admin.site.register(EvaluacionAprendizajeComponente, EvaluacionAprendizajeComponenteAdmin)
admin.site.register(CompendioSilaboSemanal, CompendioSilaboSemanalAdmin)
admin.site.register(UsuarioLdap, UsuarioLdapAdmin)
admin.site.register(DiapositivaSilaboSemanal, DiapositivaSilaboSemanalAdmin)
admin.site.register(GuiaEstudianteSilaboSemanal, GuiaEstudianteSilaboSemanalAdmin)
admin.site.register(MaterialAdicionalSilaboSemanal, MaterialAdicionalSilaboSemanalAdmin)
admin.site.register(PlanificarCapacitaciones, PlanificarCapacitacionesAdmin)
admin.site.register(PlanificarCapacitacionesRecorrido, PlanificarCapacitacionesRecorridoAdmin)
admin.site.register(ActividadConvalidacionPPV, ActividadConvalidacionPPVAdmin)
admin.site.register(SolicitudRefinanciamientoPosgrado, SolicitudRefinanciamientoPosgradoAdmin)
admin.site.register(SolicitudRefinanciamientoPosgradoRecorrido, SolicitudRefinanciamientoPosgradoRecorridoAdmin)
admin.site.register(LogEntryBackup, LogEntryBackupAdmin)
admin.site.register(LogEntryBackupdos, LogEntryBackupdosAdmin)
admin.site.register(RubricaMoodle, RubricaMoodleAdmin)
admin.site.register(PonderacionSeguimiento, PonderacionSeguimientoAdmin)
admin.site.register(RespuestaEvaluacionAcreditacion, RespuestaEvaluacionAcreditacionAdmin)
admin.site.register(DetalleInstrumentoEvaluacionDirectivoAcreditacion, DetalleInstrumentoEvaluacionDirectivoAcreditacionAdmin)
admin.site.register(NotificacionDeudaPeriodo, NotificacionDeudaPeriodoAdmin)
# admin.site.register(TipoRecurso, TipoRecursoAdmin)
# admin.site.register(ConfiguracionRecurso, ConfiguracionRecursoAdmin)
admin.site.register(DetPersonaPadronElectoral, DetPersonaPadronElectoralAdmin)
admin.site.register(PorcentajeDescuentoBecaPosgrado, PorcentajeDescuentoBecaPosgradoAdmin)
admin.site.register(CriterioLink, CriterioLinkAdmin)
admin.site.register(AsesoramientoSEETipoTrabajo, AsesoramientoSEETipoTrabajoAdmin)
admin.site.register(AsesoramientoSEE, AsesoramientoSEEAdmin)
admin.site.register(HorarioExamen, DetalleHorarioExamenAdmin)
admin.site.register(RequisitoBeca, RequisitoBecaAdmin)
admin.site.register(InstitucionCertificadora, InstitucionCertificadoraAdmin)
admin.site.register(NivelSuficencia, NivelSuficenciaAdmin)
admin.site.register(SesionZoom, SesionZoomAdmin)
admin.site.register(TipoGasto, TipoGastoAdmin)
admin.site.register(TipoTransporte, TipoTransporteAdmin)
admin.site.register(LugarAlimentacion, LugarAlimentacionAdmin)
admin.site.register(LugarCompraAlimentos, LugarCompraAlimentosAdmin)
admin.site.register(OperadoraMovil, OperadoraMovilAdmin)
admin.site.register(ConvocatoriaPonencia, ConvocatoriaPonenciaAdmin)
admin.site.register(CriterioPonencia, CriterioPonenciaAdmin)
admin.site.register(CarreraGruposCarrera, ModeloBaseAdmin)
admin.site.register(Insignia, ModeloBaseAdmin)
admin.site.register(CategoriaInsignia, ModeloBaseAdmin)
admin.site.register(SagResultadoEncuesta, ModeloBaseAdmin)
admin.site.register(ModuloCategorias, ModeloBaseAdmin)
admin.site.register(EvaluacionComponentePeriodo)
admin.site.register(GrupoAsignatura)
admin.site.register(ResponsableGrupoAsignatura)
admin.site.register(DetalleGrupoAsignatura)
admin.site.register(PracticasPreprofesionalesInscripcion)
admin.site.register(DetalleEvidenciasPracticasPro)
admin.site.register(SedeVirtualPeriodoAcademico, SedeVirtualPeriodoAcademicoAdmin)
admin.site.register(PersonaDetalleMaternidadExtensionSalud, PersonaDetalleMaternidadExtensionSaludAdmin)
admin.site.register(PlanificarCapacitacionesCriterios, PlanificarCapacitacionesCriteriosAdmin)
