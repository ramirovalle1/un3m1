from django.urls import re_path, include

from api.views.alumno.actividadescomplementarias import ActividadesComplementariasAPIView
from api.views.alumno.alu_justificacion_nosufragio import AluJustificacioNoSufragioAPIView
from api.views.alumno.alu_vinculacion_posgrado import AluVinculacionPosgradoAPIView
from api.views.alumno.archivo_descarga import ArchivoDescargaAPIView
from api.views.alumno.asistencia import AsistenciasAPIView, AsistenciaDetalleAPIView
from api.views.alumno.balconservicio import BalconServicioAPIView
from api.views.alumno.carnet import CarnetAPIView
from api.views.alumno.certificado import CertificadosAPIView
from api.views.alumno.congreso import CongresoAPIView
from api.views.alumno.evento import EventoAPIView
from api.views.alumno.feria import FeriasAPIView
from api.views.alumno.horario.horario import HorarioAPIView
from api.views.alumno.idiomas import IdiomaAPIView
from api.views.alumno.malla import MallaAPIView
from api.views.alumno.manual_usuario import ManualUsuarioAPIView
from api.views.alumno.materia import MateriasAPIView, EncuestaEstudianteSilaboAPIView, SaveEncuestaSilaboAPIView
from api.views.alumno.aula_virtual.index import AulaVirtualAPIView
from api.views.alumno.aula_virtual.examen import ExamenAPIView
from api.views.alumno.finanza import RubrosAPIView
from api.views.alumno.general import GeneralAPIView
from api.views.alumno.matricula.admision import MatriculaAdmisionAPIView
from api.views.alumno.matricula.pregrado import MatriculaPregradoAPIView
from api.views.alumno.matricula.posgrado import MatriculaPosgradoAPIView
from api.views.alumno.actualizadatos import ActualizaDatosAPIView
from api.views.alumno.addremove_matricula.pregrado import AddRemoveMatriculaPregradoAPIView
from api.views.alumno.automatriculaingles import AutomatriculaInglesAPIView
from api.views.alumno.notificacion import NotificacionesAPIView
from api.views.alumno.ofertalaboral import OfertaLaboralAPIView
from api.views.alumno.panel.actualizaDatos import ActualizaDatoAPIView, SaveActualizaDatosAPIView
from api.views.alumno.panel.encuestaegresado import EncuestaEgresadoAPIView
from api.views.alumno.panel.insignias import InsigniasView
from api.views.alumno.panel.becas import BecaSolicitudView
from api.views.alumno.panel.footer import FooterInfoAPIView
from api.views.alumno.panel.encuesta import EncuestaAPIView, SaveEncuestaAPIView, DeleteEncuestaAPIView
from api.views.alumno.panel.sedeelectoral import SedeElectoralAPIView, SaveSedeElectoralAPIView
from api.views.alumno.procesoelectoral import ProcesoElectoralAPIView, ProcesoElectoralJustificacionAPIView
from api.views.alumno.record_academico.notas import NotasAPIView, NotaHistoricaAPIView
from api.views.alumno.miscitas import MisCitasAPIView
from api.views.alumno.secretary.category import CategoryAPIView
from api.views.alumno.secretary.service import ServiceAPIView
from api.views.alumno.secretary.product import ProductAPIView
from api.views.alumno.secretary.solicitud import SolicitudAPIView
from api.views.alumno.titulacionposgrado import TemaTitulacionPosgradoAPIView
from api.views.alumno.panel.evento import PanelEventoAPIView
from api.views.alumno.ver_resoluciones import VerResolucionesAPIView
from api.views.alumno.convenioempresa import ConvenioEmpresaAPIView
from api.views.alumno.hoja_vida import HojaVidaAPIView
from api.views.alumno.panel.index import PanelAPIView
from api.views.alumno.socioeconomico import SocioEconAPIView
from api.views.alumno.balcon_posgrado import BalconPosgradoAPIView
from api.views.alumno.alu_eleccionsede_examen import SeleccionMatriculaSedeExamenAPIView

urlpatterns = [
    re_path(r'^general/data$', GeneralAPIView.as_view(), name="api_view_get_general"),
    re_path(r'^panel/get/quizzesegre$', EncuestaEgresadoAPIView.as_view(), name="api_view_panel_get_encuestasegre"),
    re_path(r'^panel/get/quizzes$', EncuestaAPIView.as_view(), name="api_view_panel_get_encuestas"), #DESPUES ELEIMINAR
    re_path(r'^panel/save/quizzes$', SaveEncuestaAPIView.as_view(), name="api_view_panel_save_encuestas"), #DESPUES ELEIMINAR
    re_path(r'^panel/delete/quizzes$', DeleteEncuestaAPIView.as_view(), name="api_view_panel_save_encuestas"), #DESPUES ELEIMINAR
    re_path(r'^panel/get/evento$', PanelEventoAPIView.as_view(), name="api_view_panel_evento"), #DESPUES ELEIMINAR
    re_path(r'^footer$', FooterInfoAPIView.as_view(), name="api_view_footer"),
    re_path(r'^panel$', PanelAPIView.as_view(), name="api_view_panel_index"),
    re_path(r'^certificado/all$', CertificadosAPIView.as_view(), name="api_view_certificates_all"),
    re_path(r'^finanzas$', RubrosAPIView.as_view(), name="api_view_finances_all"),
    re_path(r'^matricula/pregrado$', MatriculaPregradoAPIView.as_view(), name="api_view_matricula_pregrado"),
    re_path(r'^matricula/admision$', MatriculaAdmisionAPIView.as_view(), name="api_view_matricula_admision"),
    re_path(r'^matricula/posgrado$', MatriculaPosgradoAPIView.as_view(), name="api_view_matricula_posgrado"),
    re_path(r'^actualizadatos$', ActualizaDatosAPIView.as_view(), name="api_view_actualiza_datos"),
    re_path(r'^matricula/add_remove/pregrado$', AddRemoveMatriculaPregradoAPIView.as_view(), name="api_view_add_remove_matricula_pregrado"),
    re_path(r'^materias$', MateriasAPIView.as_view(), name="api_view_materias"),
    re_path(r'^materias/get/quizzes$', EncuestaEstudianteSilaboAPIView.as_view(), name="api_view_materias_get_encuesta"),
    re_path(r'^materias/save/quizzes$', SaveEncuestaSilaboAPIView.as_view(), name="api_view_materias_save_encuesta"),
    re_path(r'^malla$', MallaAPIView.as_view(), name="api_view_malla"),
    re_path(r'^notas/(?P<inscripcion_id>[\w-]+)/$', NotasAPIView.as_view(), name="api_view_notas"),
    re_path(r'^record_academico-historico$', NotaHistoricaAPIView.as_view(), name="api_view_notas_historica"),
    re_path(r'^aulavirtual$', AulaVirtualAPIView.as_view(), name="api_view_aulavirtual"),
    re_path(r'^aulavirtual/examenes$', ExamenAPIView.as_view(), name="api_view_aulavirtual_examenes"),
    re_path(r'^miscitas$', MisCitasAPIView.as_view(), name="api_view_miscitas"),
    re_path(r'^horario$', HorarioAPIView.as_view(), name="api_view_horario"),
    re_path(r'^manual_usuario$', ManualUsuarioAPIView.as_view(), name="api_view_manual_usuario"),
    re_path(r'^congreso$', CongresoAPIView.as_view(), name="api_view_congreso"),
    re_path(r'^archivo_descarga$', ArchivoDescargaAPIView.as_view(), name="api_view_archivo_descarga"),
    re_path(r'^oferta_laboral$', OfertaLaboralAPIView.as_view(), name="api_view_oferta_laboral"),
    re_path(r'^notificacion$', NotificacionesAPIView.as_view(), name="api_view_notificacion"),
    re_path(r'^asistencia/(?P<matricula_id>[\w-]+)/$', AsistenciasAPIView.as_view(), name="api_view_asistencia"),
    re_path(r'^asistencia-detalle$', AsistenciaDetalleAPIView.as_view(), name="api_view_asistencia_detalle"),
    re_path(r'^complementarias$', ActividadesComplementariasAPIView.as_view(), name="api_view_actividades_complementarias"),
    re_path(r'^carnet$', CarnetAPIView.as_view(), name="api_view_carnet"),
    re_path(r'^ferias$', FeriasAPIView.as_view(), name="api_view_ferias_all"),
    re_path(r'^balcon_servicios$', BalconServicioAPIView.as_view(), name="api_view_balcon_servicios_all"),
    re_path(r'^insignias$', InsigniasView.as_view(), name="api_view_insignias_all"),
    re_path(r'^becas$', BecaSolicitudView.as_view(), name="api_view_becasolicitud_all"),
    re_path(r'^secretary/category', CategoryAPIView.as_view(), name="api_view_secretary_category"),
    re_path(r'^secretary/service$', ServiceAPIView.as_view(), name="api_view_secretary_service"),
    re_path(r'^secretary/product$', ProductAPIView.as_view(), name="api_view_secretary_product"),
    re_path(r'^secretary/solicitud$', SolicitudAPIView.as_view(), name="api_view_solicitud_product"),
    re_path(r'^tematitulacion_posgrado$', TemaTitulacionPosgradoAPIView.as_view(), name="api_view_tema_titulacion_posgradol"),
    re_path(r'^evento$', EventoAPIView.as_view(), name="api_view_evento_all"),
    re_path(r'^resoluciones$', VerResolucionesAPIView.as_view(), name ="api_ver_resoluciones_alumno"),
    re_path(r'^convenios$', ConvenioEmpresaAPIView.as_view(), name ="api_convenio_empresa"),
    re_path(r'^hoja_vida$', HojaVidaAPIView.as_view(), name="api_hoja_vida"),
    re_path(r'^idiomas$', IdiomaAPIView.as_view(), name="api_view_idioma"),
    re_path(r'^alu_automatriculamodulos$', AutomatriculaInglesAPIView.as_view(), name="api_view_automatriculaingles"),
    re_path(r'^socioeconomica$', SocioEconAPIView.as_view(), name="api_view_socioeconomico"),
    re_path(r'^actualizadatosdomicilio$', ActualizaDatoAPIView.as_view(), name="api_view_panel_actualizadatos"),
    re_path(r'^actualizadatosdomicilio/save$', SaveActualizaDatosAPIView.as_view(), name="api_view_panel_actualizadatos_save"),
    re_path(r'^procesoelectoral$', ProcesoElectoralAPIView.as_view(), name="api_view_proceso_electoral"),
    re_path(r'^procesoelectoral/justificativo$', ProcesoElectoralJustificacionAPIView.as_view(), name="api_view_proceso_electoral_justificacion"),
    re_path(r'^sedeelectoral$', SedeElectoralAPIView.as_view(), name="api_view_panel_registra_sede"),
    re_path(r'^panel/sedeexamen$', SeleccionMatriculaSedeExamenAPIView.as_view(), name="api_view_panel_selecciona_sede_examen"),
    re_path(r'^sedeelectoral/save$', SaveSedeElectoralAPIView.as_view(), name="api_view_panel_proceso_electoral_save"),
    re_path(r'^alu_vinculacion_posgrado$', AluVinculacionPosgradoAPIView.as_view(), name="api_view_panel_vinculacion_posgrado"),
    re_path(r'^alu_justificacion_nosufragio$', AluJustificacioNoSufragioAPIView.as_view(), name="api_view_panel_justificacion_nosufragio"),
    re_path(r'^balcon_posgrado$', BalconPosgradoAPIView.as_view(), name="api_view_panel_balcon_posgrado"),
    re_path(r'^', include('api.views.alumno.solicitud_tutor.urls')),
    re_path(r'^', include('api.views.alumno.tutoria_academica.urls')),
]
