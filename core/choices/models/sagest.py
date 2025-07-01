from django.db import models

MY_ESTADO_ACTIVO = (
    (1, u'ACTIVO'),
    (2, u'DADO DE BAJA'),
)

MY_ESTADO_PARTES = (
    (1, u'ACTIVO'),
    (2, u'INACTIVO'),
)

MY_TIPO_ZONA = (
    (1, u'URBANA'),
    (2, u'RURAL'),
)


MY_TIPO_MOVIMIENTO_ACTIVO = (
    (1, u'ASIGNACIÓN'),
    (2, u'TRASPASO'),
)

MY_ESTADOS_COMPROBANTES = (
    (1, u'PENDIENTE'),
    (2, u'VALIDADO'),
    (3, u'RECHAZADO'),
    (4, u'RECAUDADO'),
)

MY_TIPO_REGISTRO_COMPROBANTE = (
    (1, u'COMPROBANTE PAGO'),
    (2, u'COMPROBANTE PAGO ANTICIPO'),
)

MY_TIPO_COMPROBANTE = (
    (1, u'DEPOSITO POR PAPELETA'),
    (2, u'TRANSFERENCIA'),
)

MY_ESTADO_ACTA = (
    (1, u'PENDIENTE'),
    (2, u'FINALIZADA'),
)

MY_TIPO_FIRMA = (
    (1, u'PRIMERO'),
    (2, u'SEGUNDO'),
)

MY_TIPO_INDICADOR = (
    (1, u'NUMÉRICO'),
    (2, u'PORCENTAJE'),
)

MY_TIPO_META = (
    (1, u'1ER SEMESTRE'),
    (2, u'2DO SEMESTRE'),
)

MY_TIPO_MANTENIMIENTO = (
    (1, u'INTERNO Y EXTERNO'),
    (2, u'INTERNO '),
    (3, u'EXTERNO'),
)

MY_SEMAFORO_VIDAUTIL = (
    (1, u'VERDE'),
    (2, u'NARANJA'),
    (3, u'ROJO')
)

MY_ORIGEN_REGISTRO = (
    (1, u'INDIVIDUAL'),
    (2, u'LOTE'),
)

MY_SINO = (
    ("S", u"SI"),
    ("N", u"NO"),
)

MY_AFECTATOTAL = (
    ("1", u"SI"),
    ("2", u"NO"),
)

MY_ESTRUCTURA_ACTIVO = (
    (1, u'INDIVIDUAL'),
    (2, u'COMPONENTES'),
)


MY_CLASE_BIEN = (
    (1, u'LARGA DURACIÓN'),
    (2, u'CONTROL ADMINISTRATIVO'),
)

MY_ESTADO_CONSTATACION = (
    (1, u'EN PROCESO'),
    (2, u'FINALIZADA'),
)

MY_ESTADO_PROCESO = (
    (1, u'EN PROCESO'),
    (2, u'FINALIZADA'),
    (3, u'ANULADO'),
)

MY_VIDA_UTIL = (
    (1, u'0'),
    (2, u'5'),
    (3, u'10'),
    (4, u'20'),
    (5, u'25'),
    (6, u'35'),
    (7, u'40'),
    (8, u'50'),
)

MY_TIPO_SOLICITUD_TRASPASO_BAJA = (
    (1, u'OFICIO'),
    (2, u'EMAIL'),
    (3, u'MEMORANDO'),
    (4, u'RESOLUCION'),
    (5, u'POR SISTEMA'),
)

MY_TIPO_RUBRO = (
    (1, u'MAESTRIAS POSGRADO - EPUNEMI'),
    (2, u'EDUCACION CONTINUA - EPUNEMI'),
    (3, u'OTRO'),
    (4, u'CONGRESO'),
    (5, u'MAESTRIAS POSGRADO - UNEMI'),
    (6, u'EDUCACION CONTINUA - UNEMI'),
    (7, u'VINCULACION - EPUNEMI'),
    (8, u'FORMACIÓN EJECUTIVA - UNEMI'),
)

MY_SUB_TIPO_RUBRO = (
    (1, u'REGULAR'),
    (2, u'INSCRIPCIONES A MÓDULOS REPROBADOS'),
    (3, u'PRÓRROGA TITULACIÓN POSGRADO'),
    (4, u'VALIDACIÓN DE CONOCIMIENTO'),
    (5, u'REPROBACIÓN UNIDAD DE TITULACIÓN'),
    (6, u'COSTO POR TITULACIÓN EXTRAORDINARIA'),
    (7, u'ACTUALIZACIÓN DE CONOCIMIENTO '),
    (8, u'RETIRO VOLUNTARIO DEL MÓDULO'),
    (9, u'COSTOS POR SOLICITUDES DE DEVOLUCIÓN'),
    (10, u'COSTOS POR ABANDONO O RETIRO VOLUNTARIO DEL PROGRAMA'),
    (11, u'COSTOS POR SOLICITUDES DE DEVOLUCIÓN PAGOS EN EXCESO'),
    (12, u'COSTOS POR DEVOLUCIÓN DE VALORES POR PREINSCRIPCIÓN'),
    (13, u'RECONOCIMIENTO U HOMOLOGACIÓN DE ESTUDIOS DE POSGRADO'),
    (14, u'COSTO POR CERTIFICACIONES ACADÉMICAS DE POSGRADO'),
    (15, u'COSTO POR CERTIFICACIONES ACADÉMICAS DE GRADO'),
    (16, u'COSTO POR CERTIFICACIONES ACADÉMICAS DE NIVELACIÓN')
)

MY_TIPO_TRASPASO = (
    (0, u'NO ES TRASPASO'),
    (1, u'TRASPASO USUARIO'),
    (2, u'TRASPASO CUSTODIO'),
)

MY_TIPO_REGISTRO_TRASLADO = (
    (1, u'BORRADOR'),
    (2, u'DEFINITIVO'),
)

MY_ESTADO_ROL = (
    (1, u'ELABORADO'),
    (2, u'NOVEDADES'),
    (3, u'VERIFICAR NOVEDADES'),
    (4, u'PROCESADO'),
    (5, u'CERRADO')
)

MY_TIPO_RUBRO_ROL = (
    (1, u'INGRESO'),
    (2, u'EGRESO'),
    (3, u'INFORMATIVO')
)

MY_TIPO_CAMPO = (
    (1, u'TEXTO'),
    (2, u'NUMERO'),
    (3, u'FECHA'),
    (4, u'HORA'),
    (5, u'COMBO'),
    (6, u'FUNCION')
)

MY_ESTADO_IMPORTACION = (
    (1, u'EN PROCESO'),
    (2, u'FINALIZADO')
)

MY_EXCEPCIONES_GASTOS_PERSONALES = (
    (1, u'NINGUNO'),
    (2, u'MAYOR EDAD'),
    (3, u'DISCAPACITADO'),
    (4, u'TERCERA EDAD Y DISCAPACITADO')
)

MY_ESTADO_COMPROBANTE = (
    (1, u'PENDIENTE'),
    (2, u'FINALIZADA'),
    (3, u'ANULADA'),
)

MY_TIPO_ACTIVIDAD_PRESUPUESTO = (
    (1, u'OTROS'),
    (2, u'EQUIPOS'),
    (3, u'MANO DE OBRA'),
    (4, u'MATERIAL'),
    (5, u'TRANSPORTE')
)

MY_TIPO_ANEXOS_RECURSOS = (
    (1, u'OTROS'),
    (2, u'MAQUINARIA'),
    (3, u'SALARIOS'),
    (4, u'MATERIALES')
)

MY_TIPO_PANILLA = (
    (1, u'AVANCE'),
    (2, u'COMPLEMENTARIA'),
    (3, u'EXTRA')
)

MY_ESTADO_TRAMITE_PAGO = (
    (1, u'POR PROCESAR'),
    (2, u'RECHAZADO'),
    (3, u'FINALIZADO')
)

MY_TIPO_MARCADAS_JORNADA = (
    (1, u'TRABAJADAS'),
    (2, u'PERMISOS'),
    (3, u'EXTRAS'),
    (4, u'ATRASOS')
)

MY_ESTADO_COMPROMISO = (
    (1, u"APROBADO"),
    (2, u"ERRADO"),
    (3, u"LIQUIDADO"),
    (4, u"FINLIZADO")
)

MY_ESTADO_CERTIFICACION = (
    (1, u"PENDIENTE"),
    (2, u"FINALIZADO")
)

MY_ESTADO_ITEM = (
    (1, u"PAC"),
    (2, u"PRESUPUESTO")
)

MY_TIPO_CATALOGO = (
    (1, u"BIEN"),
    (2, u"SERVICIO"),
    (3, u"OBRAS"),
    (4, u"CONSULTA"),
)

MY_ESTADO_REFORMA = (
    (1, u"APROBADO"),
    (2, u"NO PLANTEADA"),
    (3, u"RECHAZADO POR MF")
)

MY_TIPO_PAC = (
    (1, u"PROFORMA"),
    (2, u"REFORMA")
)

MY_ESTADO_PAC = (
    (1, u"ACTIVO"),
    (2, u"RECUPERADO"),
    (3, u"HISTORIAL")
)

MY_TIPO_REFORMA = (
    (1, u"AUMENTO"),
    (2, u"DISMINUCION")
)

MY_TIPO_SISTEMA = (
    (0, u"-----------"),
    (1, u"SAGEST"),
    (2, u"SGA"),
    (3, u"MOODLE"),
    (4, u"POSGRADO"),
    (5, u"ADMISIÓN"),
    (6, u"CORREO"),
    (7, u"MEET/ZOOM"),
    (8, u"QUIPUX"),
    (9, u"POSTULATE"),
    (10, u"SGA-SAGEST"),
    (11, u"SELECCIÓN DOCENTE POSGRADO"),
)

MY_TIPO_ACTIVIDAD_BITACORA = (
    (1, 'PLANIFICADA'),
    (2, 'NO PLANIFICADA'),
)

MY_TIPO_CAPACITACION = (
    (1, u"PRESENTACIÓN"),
    (2, u"CAPACITACIÓN"),
    (3, u"OTRO")
)

MY_ESTADO_CAPACITACION = (
    (1, u'PENDIENTE'),
    (2, u'FINALIZADO'),
)

MY_TIPO_GRADO = (
    (1, u"0"),
    (2, u"1"),
    (3, u"2"),
    (4, u"3"),
    (5, u"4"),
    (6, u"5"),
    (7, u"6"),
    (8, u"7"),
    (9, u"8"),
    (10, u"9"),
    (11, u"10"),
    (12, u"11"),
    (13, u"12")
)

MY_TIPO_PARTIDA = (
    (1, u'EGRESO'),
    (2, u'INGRESO')
)

MY_TIPO_SOLICITUD_PUBLICACION = (
    (1, u'ARTICULO'),
    (2, u'PONENCIA'),
    (3, u'LIBRO'),
    (4, u'CAPITULO LIBRO'),
    (5, u'PROCEEDING (ARTÍCULO DE CONGRESO)')
)

MY_TIPO_REGISTRO_PERSONA = (
    (1, u'PROFESOR'),
    (2, u'ADMINISTRATIVO'),
    (3, u'ESTUDIANTE'),
    (4, u'EXTERNO')
)

MY_TIPO_SOLICITUD_PUBLICACION_TH = (
    (1, u'ARTICULO'),
    (2, u'PONENCIA'),
    (3, u'LIBRO'),
    (5, u'PROCEEDING (ARTÍCULO DE CONGRESO)')
)

MY_TIPO_PROYECTO_ARTICULO = (
    ('', u'---------'),
    (1, u'VINCULACIÓN'),
    (2, u'INVESTIGACIÓN INTERNO'),
    (3, u'INVESTIGACIÓN EXTERNO')
)

MY_TIPO_COMPROMISO_PAGO = (
    (1, u'NUEVO'),
    (2, u'REFINANCIAMIENTO')
)

MY_TIPO_GARANTE = (
    (1, u'CONYUGE ESTUDIANTE'),
    (2, u'GARANTE'),
    (3, u'CONYUGE GARANTE')
)

MY_GARANTE_RELACION_DEPENDENCIA = (
    ('', u'--------'),
    (1, u'SI'),
    (2, u'NO')
)

MY_GARANTE_PERSONA_JURIDICA = (
    ('', u'--------'),
    (1, u'SI'),
    (2, u'NO')
)

MY_TIPO_PRODUCTO_PAC = (
    (1, u'BIENES'),
    (2, u'SERVICIOS'),
    (3, u'INSUMOS'),
)

MY_TIPO_PRODUCTO_PAC_INGRESO = (
    (2, u'SERVICIOS'),
    (3, u'INSUMOS'),
)

MY_TIPO_ANEXO_INFORME = (
    (1, u'ACTA DE ACEPTACIÓN'),
    (2, u'ACTA DE REUNIONES'),
    (3, u'ESPECIFICACIÓN DE REQUERIMIENTOS'),
    (4, u'ACTA DE CAPACITACIÓN')
)

MY_TIPO_ARCHIVO = (
    (1, u'.DOC'),
    (2, u'.XLS'),
    (3, u'.PPT'),
    (4, u'.PDF'),
    (5, u'.ZIP')

)

MY_TIPO_MARCADA = (
    (1, u'INSTITUCIONAL'),
    (2, u'ACTVIDAD VIRTUAL'),
)

TIPO_MARCAJE = (
    (1, u'Entrada al trabajo'),
    (2, u'Salida del trabajo'),
    (3, u'Salida al almuerzo'),
    (4, u'Regreso del almuerzo'),
)

MY_ESTADO_TRASPASO = (
    (1, u'PENDIENTE'),
    (2, u'APROBADO FUTURO RESPONSABLE'),
    (3, u'RECHAZADO FUTURO RESPONSABLE'),
    (4, u'APROBADO RESPONSABLE'),
    (5, u'RECHAZADO RESPONSABLE'),
    (6, u'ELIMINA SOLICITANTE'),
    (7, u'FINALIZADO'),
)

MY_ESTADO_CIERRE = (
    (1, u'PLANIFICACIÓN'),
    (2, u'PERIODO ABIERTO'),
    (3, u'PERIODO CERRADO'),
)

MY_ESTADO_INVENTARIO = (
    (1, u'CIERRE'),
)
MY_ESTADO_CONSTATACION_AT = (
    (1, U'Planificado'),
    (2, U'En proceso'),
    (3, U'Finalizado'),
    (4, U'Cerrado'),
)
MY_ESTADO_MOVIMIENTO = (
    (1, u'ENCONTRADO'),
    (2, u'INFORME DE BAJA'),
    (3, u'PEDIR TRASPASO'),
)

MY_ESTADO_UBICACION = (
    (1, u'ENCONTRADO'),
    (2, u'NO ENCONTRADO')
)

MY_ESTADO_FUNCIONAMIENTO = (
    (1, u'FUNCIONANDO'),
    (2, u'NO FUNCIONANDO'),
    (3, u'NO DETALLADO')
)

MY_ESTADO_USO_AT = (
    (1, u'EN USO'),
    (2, u'NO USADO')
)

MY_ACCION_MODULO = (
    (1, 'Inventario tecnológico'),
    (2, 'Matenimiento de activos')
)

MY_APLICA_GRATUIDAD_INSCRITO = (
    (1, u'APLICA'),
    (2, u'NO APLICA')
)

MY_PRESTAMO_ACTIVOS_OPERACIONES = (
    (1, u'PRÉSTAMO'),
    (2, u'DEVUELVE USUARIO'),
    (3, u'TIEMPO EXCEDIDO'),
    (4, u'SOLICITA DEVOLUCIÓN'),
    (5, u'DEVUELTO'),
)

MY_AUDITORIA_PRESTAMO_ACTIVOS_OPERACIONES = (
    (1, u'REALIZA PRÉSTAMO'),
    (2, u'REALIZA DEVOLUCIÓN'),
    (3, u'ACTUALIZA DATOS'),
    (4, u'NOTIFICA TRASPASO'),
    (5, u'ELIMINA PRÉSTAMO'),
    (6, u'DEVUELTO'),
    (7, u'DEVUELVE USUARIO'),
    (8, u'SOLICITA DEVOLUCIÓN'),
    (9, u'RECHAZA DEVOLUCIÓN'),
    (10, u'PRÉSTAMO'),
)

MY_ESTADO_SOLICITUD_TRASPASO = (
    (1, u'PENDIENTE'),
    (2, u'ACEPTA USUARIO ENTREGA'),
    (3, u'RECHAZA USUARIO ENTREGA'),
    (4, u'ACEPTA USUARIO RECIBE'),
    (5, u'RECHAZA USUARIO RECIBE'),
    (6, u'FINALIZADO'),
    (7, u'CANCELADO'),
    (8, u'TRASPASO PENDIENTE'),
    (9, u'TRASPASO REALIZADO'),
    (10, u'TRASPASO NO REALIZADO'),
    (11, u'PENDIENTE FIRMAR'),
    (12, u'FIRMA USUARIO ENTREGA'),
    (13, u'FIRMA USUARIO RECIBE'),
    (14, u'FIRMA ACTIVO FIJO'),
    (15, u'FIRMA CUSTODIO ENTREGA'),
    (16, u'FIRMA CUSTODIO RECIBE'),
    (17, u'ACEPTA CUSTODIO RECIBE'),
    (18, u'RECHAZA CUSTODIO RECIBE'),
    (19, u'GENERACIÓN ACTA DE TRASPASO'),
    (20, u'EN CORRECCIÓN'),
    (21, u'CORREGIDO'),
)

MY_QUIEN_SOLICITA_TRASPASO = (
    (1, u'RESPONSABLE'),
    (2, u'OPERACIONES'),
)

MY_TIPO_REGISTRO_ACTIVOSTECNOLOGICOS = (
    (1, u'CREADO'),
    (2, u'MIGRADO')
)

MY_TIPO_RELACION_LABORAL = (
    (1, u"Nombramiento"),
    (2, u"Contrato"),
    (3, u"Código de Trabajo"),
)

MY_ESTADO_PAZ_SALVO = (
    (1, u"Pendiente"),
    (2, u"Generado"),
    (3, u"Firmado"),
    (4, u"Finalizado"),
)

MY_ESTADO_TRAMITE_PAGO_PAZ_SALVO = (
    (1, u"Pendiente de remisión"),
    (2, u"Remitido para pago"),
)

MY_MOTIVO_SALIDA = (
    (1, u"Renuncia Voluntaria"),
    (2, u"Terminación de Contrato"),
)

MY_ESTADO_HISTORIAL_PS = (
    (1, u"Generado"),
    (2, u"Firmado"),
    (3, u"Revertido"),
)

MY_TIPO_PERMISO = (
    (1, 'Registrar evidencia'),
    (2, 'Seguimiento de evidencia'),
    (3, 'Consulta evidencia'),
    (4, 'Valida la evidencia')
)
MY_ESTADO_SOLICITUD_EQUIPO_COMPUTO = (
    (1, u"Pendiente"),
    (2, u"Aprobada"),
    (3, u"Equipo Entregado"),
    (4, u"Finalizada"),
    (5, u"Rechazada"),
)

MY_TIPO_REGISTRO_ACTIVO_FIJO = (
    (1, u"Informe baja"),
    (2, u"Verificación técnica"),
    (3, u"Gestión de baja"),
    (4, u"Actualización masiva"),
    (5, u"Constatación de activos"),
)

MY_TIPO_DOCUMENTO_EQUIPO_COMPUTO = (
    (1, 'Cédula'),
    (2, 'Pasaporte'),
    (3, 'Licencia de Conducir'),
    (4, 'Carnet Estudiantil'),
    (5, 'Otro'),
)

MY_ESTADO_EQUIPO_COMPUTO = (
    (1, u"Disponible"),
    (2, u"Ocupado"),
)


ESTADO_REVISION_EVIDENCIA = (
    (1, 'Registrado'),
    (2, 'Revisado'),
    (3, 'Requiere ajustes'),
    # (4, 'No aplica'),
    (5, 'Actualizado'),
    (6, 'Validado'),
    (7, 'Pendiente'),
    (8, 'Devuelto'),
    (9, 'En proceso de revisión'),
    (10, 'Remitido a validación'),
)
ESTADO_LEGALIZACION_POA = (
    (1, 'Generado'),
    (2, 'En proceso'),
    (3, 'Legalizado')
)
ACCION_HISTORIAL_EVIDENCIA = (
    (1, 'Registro de evidencia'),
    (2, 'Validación de evidencia'),
    (3, 'Validación, notificación y actualización de estado principal'),
    (4, 'Remitido para aprobación')
)
ESTADO_SEGUIMIENTO_POA = (
    (1, 'Pendiente'),
    (2, 'Agendado'),
    (3, 'Finalizado'),
    (4, 'Cancelado'),
    (5, 'Reagendado')
)

MY_ESTADO_FIRMA_INFORME_BAJA = (
    (1, 'Generado'),
    (2, 'En proceso'),
    (3, 'Legalizado'),
)

MY_ESTADO_FIRMA_INFORME_BAJA_HISTORIAL = (
    (1, 'Generado'),
    (2, 'Firmado'),
    (3, 'Subió archivo firmado'),
    (4, 'Generado por sistema'),
)

ESTADO_JUSTIFICACION_PROCESO = (
    (1, 'Pendiente'),
    (2, 'Aprobado'),
    (3, 'Rechazado'),
)

TIPO_FALTA = (
    (1, 'Leves'),
    (2, 'Graves'),
)

PUNTO_CONTROL = (
    (0, 'Sin punto de control'),
    (1, 'Hoja de ruta'),
    (2, 'Marcadas'),
    (3, 'Constancia de puestos'),
    (4, 'Manual de puestos'),
    (5, 'Manual de funciones'),
    (6, 'PQRS'),
)

TIPO_REQUISITO = (
    (1, 'Video'),
    (2, 'Foto'),
    (3, 'Documento'),
    (4, 'Url'),
)

MY_ESTADO_BODEGA_VIRTUAL = (
    (1, 'Disponible'),
    (2, 'Solicitado'),
    (3, 'En proceso'),
    (4, 'Finalizado'),
)

ETAPA_INCIDENCIA = (
    (1, 'Revisión y validación de caso'), # Generación y reporte de la incidencia.
    (2, 'Análisis y ejecución de acciones'), # Revisión del informe del caso presentado.
    (3, 'Gestión de audiencia'), # Análisis del caso presentado.
    (4, 'Finalización de caso'), # El caso se archiva porque no se considera procedente.

)

ESTADO_INCIDENCIA = (
    (0, 'Borrador'), # Identificación de una posible falta disciplinaria.
    (1, 'Caso reportado'), # Generación y reporte de la incidencia.
    (2, 'Remitido a RRHH'), # Revisión del informe del caso presentado.
    (3, 'En ejecución'), # Análisis del caso presentado.
    (4, 'Archivado (No procedente)'), # El caso se archiva porque no se considera procedente.
    (5, 'Respuesta de descargo'),     # Respuesta de descargo
    (6, 'Planificación de audiencia'),     # En planificación de audiencia
    (7, 'En Audiencia'),     # En audiencia
    (8, 'Emisión de documentos'),  # Documentos en emisión.
    (9, 'Documentación emitida'),
    (10, 'Finalizado'),
    (11, 'Caso absuelto'),
)
ESTADO_SANCION_PERSONA = (
    (0, 'Por validar'), # Generación y reporte de la incidencia.
    (1, 'Procede en el caso'), # Generación y reporte de la incidencia.
    (2, 'No procedente'), # El caso se archiva porque no se considera procedente.
    (3, 'Procede la sanción'),
    (4, 'Caso absuelto'),
)

ESTADO_NOTIFICACION_SANCION = (
    (0, 'Pendiente'),
    (1, 'Notificado'),
    (2, 'Visto'),
)

ESTADO_FIRMA_ACCION_PERSONAL_SANCION = (
    (0, 'Solicitado'),
    (1, 'Si'),
    (2, 'No'),
)

ACCION_REALIZADA = (
    (1, 'Validación de incidencia'), # Proceso de confirmación y documentación de la incidencia.
    (2, 'Generación de documento'), # Creación de un informe detallado basado en la revisión de la incidencia.
    (3, 'Legalización de documento'), # Proceso de autenticación y formalización del informe y documentos relacionados.
    (4, 'Planificación de audiencia'), # Proceso de autenticación y formalización del informe y documentos relacionados.
)

ESTADO_LEGALIZACION_DOCUMENTO = (
    (1, 'Generado'), # Generación y reporte de la incidencia.
    (2, 'En proceso'), # Revisión del informe del caso presentado.
    (3, 'Legalizado'), # Análisis del caso presentado.
)

ROL_FIRMA_DOCUMENTO = (
    (0, 'Sin rol en el documento'),
    (1, 'Elaborado por'), #en accion de personal es RESPONSABLE DE ELABORACIÓN
    # ROLES PARA INFORME DE FUNDAMENTOS DE HECHO
    (2, 'Verificado por'), # en accion de personal es RESPONSABLE DE REVISIÓN
    (3, 'Aprobado por'),
    (11, 'Verificado y Aprobado por'),
    # ROLES PARA ACTA DE AUDIENCIA
    (4, 'Sustanciador'),
    (5, 'Secretario Ad- hoc'),
    (6, 'Director Jurídico'),
    (12, 'Testigo'), # (Abogado institucional)
    (7, 'Servidor Público'),
    (13, 'Abogado defensor'),
    # ROLES PARA ACCION DE PERSONAL
    (8, 'Responsable del Registro y control'),
    (9, 'Autoridad Nominadora o su delegado'),
    (10, 'Funcionario o Funcionaria'),
    (14, 'Director de talento humano'),
    (15, 'Responsable que notifica'),
)

TIPO_DOCUMENTOS = (
    (1, 'Informe de fundamentos de hecho'),
    (2, 'Acta de audiencia'),
    (3, 'Acción de personal'),
    (4, 'Informe técnico de sustanciación'),
    (5, 'Acta de reunión'),
)

NIVEL_GESTION = (
    (1, 'ADMINISTRATIVO'),
    (2, 'ACADÉMICO'),
)

ESTADO_APROBACION_ASISTENCIA = (
    (0, 'Por validar'),
    (1, 'Aprobado'),
    (2, 'Rechazado'),
)

ESTADO_PRUEBA_DESCARGO = (
    (0, 'Por validar'),
    (1, 'Procedente'),
    (2, 'No procede'),
)
ESTADO_AUDIENCIA = (
    (0, 'Borrador'),
    (1, 'Notificada'),
    (2, 'Programada'),
    (3, 'Cancelada'),
    (4, 'En ejecución'),
    (5, 'Finalizada'),
)
ESTADO_DESICION_AUDIENCIA = (
    (0, 'En espera de resolución de audiencia'),
    (1, 'Caso absuelto'),
    (2, 'Procede la sanción'),
)

MY_ESTADO_EVALUACION_REQUERIMIENTO = (
    (1, u'Pendiente'),
    (2, u'Aceptado'),
    (3, u'Rechazado'),
)

NOMBRE_FALTA_DISCIPLINARIA = (
    (0, 'LEVE'),
    (1, 'GRAVE'),
)

class ProfileChoice(models.IntegerChoices):
    administrativo = 1, 'Administrativo'
    docente = 2, 'Docente'
class AccionesMrcadaChoice(models.IntegerChoices):
    ACTIVO = 1, 'Marcada habilitado/deshabilitado'
    EXTERNO = 2, 'Marcaje externo'
    SOLO_PC = 3, 'Marcaje solo en ordenador '
class PisosBloqueChoice(models.IntegerChoices):
    PLANTABAJA = 0, 'Planta baja'
    PISO1 = 1, 'Primer piso'
    PISO2 = 2, 'Segundo piso'
    PISO3 = 3, 'Tercer piso'
    PISO4 = 4, 'Cuarto piso'
    PISO5 = 5, 'Quinto piso'
    PISO6 = 6, 'Sexto piso'
    PISO7 = 7, 'Séptimo piso'
    PISO8 = 8, 'Octávo piso'