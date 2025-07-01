# -*- coding: UTF-8 -*-
from django.urls import re_path
from sagest import commonviews, adm_productos, adm_proveedores, adm_compras, adm_salidas, adm_anulaciones, \
    adm_inventarios, \
    adm_departamentos, adm_cuentas, adm_suministro, adm_suministro_salida, adm_ubicacion, adm_solicitudvehiculo, \
    adm_solicitudvehiculodetalle, adm_solicitudvehiculoaprobacion, th_personal, th_plantilla, th_accionpersonal, \
    th_hojaruta, \
    th_hojavida, th_permiso_institucional, th_aprobar_permiso, th_aprobar_permiso_th, th_consulta_permiso, th_nomina, \
    th_titulos, th_telefonia, th_contrato, th_marcadas, th_marcadas_consulta, th_tipopermiso, th_horas, th_horastthh, \
    th_horasingresar, \
    af_ubicacion, af_catalogo, af_taller_mantenimiento, af_activofijo, poa_programas, poa_objestrategicos, \
    poa_objestrategicosgeneral, poa_objtacticos, poa_objoperativos, poa_indicadores, poa_periodos, \
    poa_usuarioevidencia, poa_subirevidencia, poa_revisaevidencia, poa_aprobarevidencia, poa_subirevidatrasada, \
    poa_consultarevidencias, poa_usuarioconevidencia, pac_periodo, pac_pacdepartamento, pac_pacgeneral, pac_pacrevision, \
    pac_pacejecucion, pac_pacpresupuesto, totalpac, vertotalpac, pod_periodo, pod_departamento_ingreso, \
    er_riesgotrabajo, er_agenteriesgo, er_planificacion, pre_saldo_partida, pre_rubros, rec_contratos, rec_caja, \
    rec_recibocaja, rec_finanzas, rec_facturas, rec_consultaalumnos, rec_notacredito, rec_cheques, rec_bancopacifico, \
    rec_clienteexterno, rec_comprobantes, rec_conciliacion, rec_documentoscomprobantes, rec_garantias, sign, show, \
    ob_anexosrecursos, ob_planillapresupuesto, ob_recursosactividad, ob_presupuestos, fin_tramitepago, \
    fin_gastospersonales, fin_comprobantes, fin_resumencomprobantes, fin_centrocosto, fin_documentostramite, \
    fin_archivoproceso, adm_hdincidente, adm_hdusuario, adm_hdagente, adm_capacitacioneventoperiodo, \
    adm_capacitacionaprobacion_dr, adm_capacitacionaprobacion_th, adm_capacitacioneventoperiodoipec, \
    adm_capacitacioneventoperiodoipec_inst, publimes, adm_periodos_rubros, adm_archivo_retenciones, cajachica, \
    custodio_cajachica, \
    aprobar_cajachica, pro_becarios, adm_rubrosbeca, \
    adm_becasdocentes, adm_aprobacionbecasdocentes, adm_vermarcadas, ins_cursosipec, ins_horariocapacitacionipec, \
    adm_requerimiento, experto_requerimiento, ins_clases, adm_resoluciones, entradasalidaobras, adm_capdocenteperiodo, \
    adm_ingresoactividadescrai, poa_menutree, th_personaltrabajador, adm_congresos, adm_capacitacion, \
    adm_capacitacionaprobacion, rec_cuentabeneficiario, rec_devoluciondinero, adm_ordenpedido, \
    adm_formulario107, rec_recibocajapago, adm_archivodescarga, adm_solicitudproductos, adm_consultaeducacioncontinua, \
    adm_seguimientomaestrias, th_dir_planificacion, th_escalasalarial, th_perfilpuesto, adm_repositorio, \
    inventario_activofijo, ver_resoluciones, adm_rolespagoexterno \
    , sharedlinkedin, adm_solicitudpagobeca, at_activostecnologicos, adm_liquidacion_compras, activodetalleqr, \
    adm_novedadesaso, adm_activostecnologicos, adm_mantenimientogarantia, th_pazsalvo, adm_equiposcomputo, adm_justificacioneleccion
from sga import adm_aulas
from sagest import chatbotv1
urlpatterns = [re_path(r'^loginsagest$', commonviews.login_user, name='login'),
               re_path(r'^adm_productos$', adm_productos.view, name='sagest_adm_productos_view'),
               re_path(r'^adm_proveedores$', adm_proveedores.view, name=u"sagest_adm_proveedores_view"),
               re_path(r'^adm_compras$', adm_compras.view, name=u"sagest_adm_compras_view"),
               re_path(r'^adm_salidas$', adm_salidas.view, name=u"sagest_adm_salidas_view"),
               re_path(r'^adm_solicitudproductos$', adm_solicitudproductos.view, name=u"sagest_adm_solicitudproductos_view"),
               re_path(r'^adm_seguimientomaestrias$', adm_seguimientomaestrias.view, name=u"sagest_adm_seguimientomaestrias_view"),
               re_path(r'^adm_anulaciones$', adm_anulaciones.view, name=u"sagest_adm_anulaciones_view"),
               re_path(r'^adm_inventarios$', adm_inventarios.view, name=u"sagest_adm_inventarios_view"),
               re_path(r'^adm_departamentos$', adm_departamentos.view, name=u"sagest_adm_departamentos_view"),
               re_path(r'^adm_cuentas$', adm_cuentas.view, name=u"sagest_adm_cuentas_view"),
               re_path(r'^adm_aulas$', adm_aulas.view, name=u"sga_adm_aulas_view"),
               re_path(r'^adm_suministro$', adm_suministro.view, name=u"sagest_adm_suministro_view"),
               re_path(r'^adm_suministro_salida$', adm_suministro_salida.view, name=u"sagest_adm_suministro_salida_view"),
               re_path(r'^adm_ubicacion$', adm_ubicacion.view, name=u"sagest_adm_ubicacion_view"),
               re_path(r'^adm_solicitudvehiculo$', adm_solicitudvehiculo.view, name=u"sagest_adm_solicitudvehiculo_view"),
               re_path(r'^adm_solicitudvehiculodetalle$', adm_solicitudvehiculodetalle.view, name=u"sagest_adm_solicitudvehiculodetalle_view"),
               re_path(r'^adm_solicitudvehiculoaprobacion$', adm_solicitudvehiculoaprobacion.view, name=u"sagest_adm_solicitudvehiculoaprobacion_view"),
               re_path(r'^adm_vermarcadas$', adm_vermarcadas.view, name=u"sagest_adm_vermarcadas_view"),
               re_path(r'^adm_ordenpedido$', adm_ordenpedido.view, name=u"sagest_adm_ordenpedido_view"),
               # Talento Humano
               re_path(r'^th_personal$', th_personal.view, name=u"sagest_th_personal_view"),
               re_path(r'^th_personaltrabajador$', th_personaltrabajador.view, name=u"sagest_th_personaltrabajador_view"),
               re_path(r'^th_plantilla$', th_plantilla.view, name=u"sagest_th_plantilla_view"),
               re_path(r'^th_accionpersonal$', th_accionpersonal.view, name=u"sagest_th_accionpersonal_view"),
               re_path(r'^th_hojaruta$', th_hojaruta.view, name=u"sagest_th_hojaruta_view"),
               re_path(r'^th_hojavida$', th_hojavida.view, name=u"sagest_th_hojavida_view"),
               re_path(r'^th_permiso$', th_permiso_institucional.view, name=u"sagest_th_permiso_institucional_view"),
               re_path(r'^th_aprobarpermiso$', th_aprobar_permiso.view, name=u"sagest_th_aprobar_permiso_view"),
               re_path(r'^th_aprobarpermiso_th$', th_aprobar_permiso_th.view, name=u"sagest_th_aprobar_permiso_th_view"),
               re_path(r'^th_consultapermiso$', th_consulta_permiso.view, name=u"sagest_th_consulta_permiso_view"),
               re_path(r'^th_nomina$', th_nomina.view, name=u"sagest_th_nomina_view"),
               re_path(r'^th_titulos$', th_titulos.view, name=u"sagest_th_titulos_view"),
               re_path(r'^th_telefonia$', th_telefonia.view, name=u"sagest_th_telefonia_view"),
               re_path(r'^th_contrato$', th_contrato.view, name=u"sagest_th_contrato_view"),
               re_path(r'^th_marcadas$', th_marcadas.view, name=u"sagest_th_marcadas_view"),
               re_path(r'^th_marcadas_consulta$', th_marcadas_consulta.view, name=u"sagest_th_marcadas_consulta_view"),
               re_path(r'^th_tipopermiso$', th_tipopermiso.view, name=u"sagest_th_tipopermiso_view"),
               re_path(r'^th_horas$', th_horas.view, name=u"sagest_th_horas_view"),
               re_path(r'^th_horastthh$', th_horastthh.view, name=u"sagest_th_horastthh_view"),
               re_path(r'^th_horasingresar$', th_horasingresar.view, name=u"sagest_th_horasingresar_view"),
               re_path(r'^th_escalasalarial$', th_escalasalarial.view, name=u"sagest_th_escalasalarial_view"),
               re_path(r'^th_perfilpuesto$', th_perfilpuesto.view, name=u"sagest_th_perfilpuesto_view"),
               re_path(r'^th_pazsalvo$', th_pazsalvo.view, name=u"sagest_th_pazsalvo_view"),
               # PLANTILLA TH
               re_path(r'^th_dir_planificacion$', th_dir_planificacion.view, name='sga_th_dir_planificacionth_view'),

               # Activos Fijos
               re_path(r'^af_ubicacion$', af_ubicacion.view, name=u"sagest_af_ubicacion_view"),
               re_path(r'^af_catalogo$', af_catalogo.view, name=u"sagest_af_catalogo_view"),
               re_path(r'^af_taller_mantenimiento$', af_taller_mantenimiento.view, name=u"sagest_af_taller_mantenimiento_view"),
               re_path(r'^af_activofijo$', af_activofijo.view, name=u"sagest_af_activofijo_view"),

               # Planificacion Operativa (POA)
               re_path(r'^poa_programas$', poa_programas.view, name=u"sagest_poa_programas_view"),
               re_path(r'^poa_objestrategicos$', poa_objestrategicos.view, name=u"sagest_poa_objestrategicos_view"),
               re_path(r'^poa_objestrategicosgeneral$', poa_objestrategicosgeneral.view, name=u"sagest_poa_objestrategicosgeneral_view"),
               re_path(r'^poa_menutree$', poa_menutree.view, name=u"sagest_poa_menutree_view"),
               re_path(r'^poa_objtacticos$', poa_objtacticos.view, name=u"sagest_poa_objtacticos_view"),
               re_path(r'^poa_objoperativos$', poa_objoperativos.view, name=u"sagest_poa_objoperativos_view"),
               re_path(r'^poa_indicadores$', poa_indicadores.view, name=u"sagest_poa_indicadores_view"),
               re_path(r'^poa_periodos$', poa_periodos.view, name=u"sagest_poa_periodos_view"),
               re_path(r'^poa_usuarioevidencia$', poa_usuarioevidencia.view, name=u"sagest_poa_usuarioevidencia_view"),
               re_path(r'^poa_subirevidencia$', poa_subirevidencia.view, name=u"sagest_poa_subirevidencia_view"),
               re_path(r'^poa_revisaevidencia$', poa_revisaevidencia.view, name=u"sagest_poa_revisaevidencia_view"),
               re_path(r'^poa_aprobarevidencia$', poa_aprobarevidencia.view, name=u"sagest_poa_aprobarevidencia_view"),
               re_path(r'^poa_subirevidatrasada$', poa_subirevidatrasada.view, name=u"sagest_poa_subirevidatrasada_view"),
               re_path(r'^poa_consultarevidencias$', poa_consultarevidencias.view, name=u"sagest_poa_consultarevidencias_view"),
               re_path(r'^poa_usuarioconevidencia$', poa_usuarioconevidencia.view, name=u"sagest_poa_usuarioconevidencia_view"),

               # (PAC)
               re_path(r'^pac_periodo$', pac_periodo.view, name=u"sagest_pac_periodo_view"),
               re_path(r'^pac_pacdepartamento$', pac_pacdepartamento.view, name=u"sagest_pac_pacdepartamento_view"),
               re_path(r'^pac_pacgeneral$', pac_pacgeneral.view, name=u"sagest_pac_pacgeneral_view"),
               re_path(r'^pac_pacrevision$', pac_pacrevision.view, name=u"sagest_pac_pacrevision_view"),
               re_path(r'^pac_pacejecucion$', pac_pacejecucion.view, name=u"sagest_pac_pacejecucion_view"),
               re_path(r'^pac_pacpresupuesto$', pac_pacpresupuesto.view, name=u"sagest_pac_pacpresupuesto_view"),
               re_path(r'^totalpac$', totalpac.view, name=u"sagest_totalpac_view"),
               re_path(r'^vertotalpac$', vertotalpac.view, name=u"sagest_vertotalpac_view"),

               # Perfil Optimo de desempeño (POD)
               re_path(r'^pod_periodo$', pod_periodo.view, name=u"sagest_pod_periodo_view"),
               re_path(r'^pod_departamento_ingreso$', pod_departamento_ingreso.view, name=u"sagest_pod_departamento_ingreso_view"),

               # Evaluación de Riesgos y Planificacion de Acción Preventiva
               re_path(r'^er_riesgotrabajo$', er_riesgotrabajo.view, name=u"sagest_er_riesgotrabajo.view"),
               re_path(r'^er_agenteriesgo$', er_agenteriesgo.view, name=u"sagest_er_agenteriesgo_view"),
               re_path(r'^er_planificacion$', er_planificacion.view, name=u"sagest_er_planificacion_view"),

               # Presupuesto
               re_path(r'^pre_saldos$', pre_saldo_partida.view, name=u"sagest_pre_saldo_partida_view"),
               re_path(r'^pre_rubros$', pre_rubros.view, name=u"sagest_pre_rubros_view"),

               # Recaudación
               re_path(r'^rec_contratos$', rec_contratos.view, name=u"sagest_rec_contratos_view"),
               re_path(r'^rec_caja$', rec_caja.view, name=u"sagest_rec_caja_view"),
               re_path(r'^rec_recibocaja$', rec_recibocaja.view,name=u"sagest_rec_recibocaja_view"),
               re_path(r'^rec_finanzas$', rec_finanzas.view, name=u"sagest_rec_finanzas_view"),
               re_path(r'^rec_facturas$', rec_facturas.view, name=u"sagest_rec_facturas_view"),
               re_path(r'^rec_consultaalumnos$', rec_consultaalumnos.view, name=u"sagest_rec_consultaalumnos_view"),
               re_path(r'^rec_notacredito$', rec_notacredito.view, name=u"sagest_rec_notacredito_view"),
               re_path(r'^rec_cheques$', rec_cheques.view, name=u'sagest_rec_cheques_view'),
               re_path(r'^rec_bancopacifico$', rec_bancopacifico.view, name=u'sagest_rec_bancopacifico_view'),
               re_path(r'^rec_clienteexterno$', rec_clienteexterno.view, name='sagest_rec_clienteexterno_view'),
               re_path(r'^rec_comprobantes$', rec_comprobantes.view, name=u'sagest_rec_comprobantes_view'),
               re_path(r'^rec_conciliacion$', rec_conciliacion.view, name=u'sagest_rec_conciliacion_view'),
               re_path(r'^rec_documentoscomprobantes$', rec_documentoscomprobantes.view, name='sagest_rec_documentoscomprobantes_view'),
               re_path(r'^rec_garantias$', rec_garantias.view, name=u'sagest_rec_garantias_view'),
               re_path(r'^sign_factura/(?P<weburl>.+)$', sign.factura, name=u'sagest_sign_factura'),
               re_path(r'^show_factura/(?P<id>.+)$', show.factura, name=u'sagest_show_factura'),
               re_path(r'^sign_notacredito/(?P<weburl>.+)$', sign.notacredito, name=u'sagest_sign_notacredito'),
               re_path(r'^sign_liquidacion/(?P<weburl>.+)$', sign.liquidacion, name=u'sagest_sign_liquidacion'),
               re_path(r'^show_notacredito/(?P<id>.+)$', show.notacredito, name='sagest_show_notacredito'),
               re_path(r'^rec_cuentabeneficiario$', rec_cuentabeneficiario.view, name='sagest_rec_cuentabeneficiario_view'),
               re_path(r'^rec_devoluciondinero$', rec_devoluciondinero.view, name='sagest_rec_devoluciondinero_view'),
               re_path(r'^rec_recibocajapago$', rec_recibocajapago.view, name='sagest_rec_recibocajapago_view'),

               # Obras
               re_path(r'^ob_anexosrecursos$', ob_anexosrecursos.view, name=u"sagest_ob_anexosrecursos_view"),
               re_path(r'^ob_planillapresupuesto$', ob_planillapresupuesto.view, name=u"sagest_ob_planillapresupuesto_view"),
               re_path(r'^ob_recursosactividad$', ob_recursosactividad.view, name=u"sagest_ob_recursosactividad_view"),
               re_path(r'^ob_presupuestos$', ob_presupuestos.view, name=u"sagest_ob_presupuestos_view"),

               # Financiero
               re_path(r'^fin_tramitepago$', fin_tramitepago.view, name=u"sagest_fin_tramitepago_view"),
               re_path(r'^fin_gastospersonales$', fin_gastospersonales.view, name=u"sagest_fin_gastospersonales_view"),
               re_path(r'^fin_comprobantes$', fin_comprobantes.view, name=u"sagest_fin_comprobantes_view"),
               re_path(r'^fin_resumencomprobantes$', fin_resumencomprobantes.view, name=u"sagest_fin_resumencomprobantes_view"),
               re_path(r'^fin_centrocosto$', fin_centrocosto.view, name=u"sagest_fin_centrocosto_view"),
               re_path(r'^fin_documentostramite$', fin_documentostramite.view, name=u"sagest_fin_documentostramite_view"),
               re_path(r'^fin_archivoproceso$', fin_archivoproceso.view, name=u"sagest_fin_archivoproceso_view"),
               re_path(r'^adm_periodos_rubros$', adm_periodos_rubros.view, name=u"sagest_adm_periodos_rubros_view"),
               re_path(r'^adm_archivo_retenciones$', adm_archivo_retenciones.view, name=u"sagest_archivo_retenciones_view"),
               re_path(r'^adm_formulario107$', adm_formulario107.view, name=u"sagest_adm_formulario107_view"),

               #Help Desk
               re_path(r'^adm_hdincidente$', adm_hdincidente.view, name=u'sagest_adm_hdincidente_view'),
               re_path(r'^adm_hdusuario$', adm_hdusuario.view, name=u'sagest_adm_hdusuario_view'),
               re_path(r'^adm_hdagente$', adm_hdagente.view, name=u'sagest_adm_hdagente_view'),
               # Capacitacion Talento Humano
               re_path(r'^adm_capdocenteperiodo$', adm_capdocenteperiodo.view, name=u'sagest_adm_capdocenteperiodo_view'),
               re_path(r'^adm_capeventoperiodo$', adm_capacitacioneventoperiodo.view, name=u'sagest_adm_capacitacioneventoperiodo_view'),
               re_path(r'^adm_capaprobar$', adm_capacitacionaprobacion_dr.view, name=u'sagest_adm_capacitacionaprobacion_dr_view'),
               re_path(r'^adm_capaprobar_th$', adm_capacitacionaprobacion_th.view, name=u'sagest_adm_capacitacionaprobacion_th_view'),
               re_path(r'^adm_capacitacion$', adm_capacitacion.view, name=u'sagest_adm_capacitacion_view'),
               re_path(r'^adm_capacitacionaprobacion$', adm_capacitacionaprobacion.view, name=u'sagest_adm_capacitacionaprobacion_view'),
               # Capacitacion IPEC
               # pruebam
               #  re_path(r'^certificadovalidado$', prueba.validarcertificado, name='sagest_certificadovalidadoprueba'),
               #  re_path(r'^shared', sharedlinkedin.view, name='sagest_certificadovalidado'),

               re_path(r'^adm_capeventoperiodoipec$', adm_capacitacioneventoperiodoipec.view, name=u'sagest_adm_capacitacioneventoperiodoipec_view'),
               re_path(r'^adm_capeventoperiodoipec_inst$', adm_capacitacioneventoperiodoipec_inst.view, name='sagest_adm_capacitacioneventoperiodoipec_inst_view'),
               re_path(r'^adm_consultaeducacioncontinua$', adm_consultaeducacioncontinua.view, name='adm_consultaeducacioncontinua_view'),
               # PUBLIMES
               re_path(r'^publimes$', publimes.view, name=u'sagest_publimes_view'),
               # # Becados Docentes
               # re_path(r'^pro_becarios$', pro_becarios.view, name=u'sagest_pro_becarios_view'),
               # re_path(r'^adm_rubrosbeca$', adm_rubrosbeca.view, name=u'sagest_adm_rubrosbeca_view'),
               # re_path(r'^adm_becasdocentes$', adm_becasdocentes.view, name=u'sagest_adm_becasdocentes_view'),
               # re_path(r'^adm_aprobacionbecasdocentes$', adm_aprobacionbecasdocentes.view, name=u'sagest_adm_aprobacionbecasdocentes_view'),
               # CAJA CHICA
               re_path(r'^cajachica', cajachica.view, name=u'sagest_cajachica_view'),
               re_path(r'^custodio_cajachica', custodio_cajachica.view, name=u'sagest_custodio_cajachica_view'),
               re_path(r'^aprobar_cajachica', aprobar_cajachica.view, name=u'sagest_aprobar_cajachica_view'),
               re_path(r'^pro_becarios$', pro_becarios.view, name=u'sagest_pro_becarios_view'),
               re_path(r'^adm_rubrosbeca$', adm_rubrosbeca.view, name=u'sagest_adm_rubrosbeca_view'),
               re_path(r'^adm_becasdocentes$', adm_becasdocentes.view, name=u'sagest_adm_becasdocentes_view'),
               re_path(r'^adm_aprobacionbecasdocentes$', adm_aprobacionbecasdocentes.view, name=u'sagest_adm_aprobacionbecasdocentes_view'),
               # MODULOS DE IPEC PROFESOR
               re_path(r'^ins_cursosipec$', ins_cursosipec.view, name=u'sagest_ins_cursosipec_view'),
               re_path(r'^ins_horariocapacitacionipec$', ins_horariocapacitacionipec.view, name=u'sagest_ins_horariocapacitacionipec_view'),
               re_path(r'^ins_clases$', ins_clases.view, name=u'sagest_ins_clases_view'),

               # SISTEMA REQUERIMIENTO
               re_path(r'^adm_requerimiento', adm_requerimiento.view, name=u'sagest_adm_requerimiento'),
               re_path(r'^experto_requerimiento', experto_requerimiento.view, name=u'sagest_exterto_requerimiento'),

               #RESOLUCIONES
               re_path(r'^adm_resoluciones', adm_resoluciones.view, name=u'sagest_adm_resoluciones_view'),
               re_path(r'^ver_resoluciones', ver_resoluciones.view, name=u'sagest_ver_resoluciones_view'),

               #MODULO DE INVENTARIO DE SUBMINISTROS DE OBRAS UNIVERSITARIAS
               re_path(r'^entradasalidaobras', entradasalidaobras.view, name=u'sagest_entradasalidaobras_view'),
               #CRAI
               re_path(r'^adm_ingresoactividadescrai$', adm_ingresoactividadescrai.view, name=u'sagest_adm_ingresoactividadescrai_view'),
                # CONGRESOS
               re_path(r'^adm_congresos$', adm_congresos.view, name=u'sagest_adm_congresos_view'),
               #REPOSITORIO DE PROGRAMAS
               re_path(r'^adm_archivodescarga', adm_archivodescarga.view, name=u'sagest_adm_archivodescarga_view'),
               re_path(r'^adm_repositorio', adm_repositorio.view, name=u'sagest_adm_repositorio_view'),

               #INVENTARIO TECNOLÓGICO TICS
               re_path(r'^inventario_activofijo', inventario_activofijo.view, name=u'sagest_inventario_activofijo_view'),

               #ROLES DE PAGO EXTERNO
               re_path(r'^adm_rolespagoexterno', adm_rolespagoexterno.view, name=u'sagest_adm_rolespagoexterno_view'),


               re_path(r'^adm_solicitudpagobeca', adm_solicitudpagobeca.view, name=u'sagest_adm_solicitudpagobeca_view'),

               #MODULO ACTIVOS TECNOLOGICOS
               re_path(r'^at_activostecnologicos', at_activostecnologicos.view, name=u'sagest_at_activostecnologicos'),
               re_path(r'^adm_activostecnologicos', adm_activostecnologicos.view, name=u'sagest_adm_activostecnologicos'),
               re_path(r'^adm_mantenimientogarantia', adm_mantenimientogarantia.view, name=u'sagest_adm_mantenimientogarantia'),
               re_path(r'^activodetalleqr', activodetalleqr.view, name=u'activodetalleqr'),

               re_path(r'^ingresoalcampus', chatbotv1.view, name=u'encuestamovilidad'),

               #PRESTAMO DE EQUIPOS DE COMPUTO
               re_path(r'^adm_equiposcomputo$', adm_equiposcomputo.view, name=u'adm_equiposcomputo'),

               # subnovedades en rol
               re_path(r'^adm_novedadesaso', adm_novedadesaso.view, name=u'adm_novedadesaso'),
               # LIQUIDACIONES EN COMPRA
               re_path(r'^adm_liquidacion_compras$', adm_liquidacion_compras.view, name='sagest_liquidacion_compras'),

               # JUSTIFICACIÓN DE SOLICITUD DE PROCESO DE ELECCION
               re_path(r'^adm_justificacioneleccion$', adm_justificacioneleccion.view, name='adm_justificacioneleccion'),

               ]

