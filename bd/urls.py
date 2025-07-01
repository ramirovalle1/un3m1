from django.urls import re_path
from bd.views import adm_sistemas, adm_sys_academic_period, adm_sys_carnet_config, adm_sys_groups_modules, \
    adm_sys_modules_visit, adm_sys_modules, adm_sys_global_variables, adm_sys_persons, adm_sys_enroll_statistics, \
    adm_sys_permissions, adm_sys_non_working_days, adm_sys_groups, gestion, adm_sys_users, adm_sys_web_services_wsdl, \
    adm_sys_user_access_profile, estadares_desarrollo, adm_sys_remove_enroll_process, adm_sys_linea_grafica, \
    adm_sys_special_enroll_process, adm_sys_web_services, estandaresview, adm_sys_special_enroll_reason, \
    adm_sys_report_list, adm_sys_setting_template, adm_sys_remove_enroll_reason, adm_sys_remove_enroll_state, \
    adm_sys_special_enroll_state, recoverypassword, data, adm_sys_secretary, adm_sys_imagen_moodle, \
    my_profile_security, security_device, scrum_actividades, adm_actividades_scrum, adm_sys_options, \
    adm_sys_modules_categorias, adm_sys_modules_categoriassagest, execute_process

urlpatterns = [
    re_path(r'^data$', data.view, name='data_view'),
    re_path(r'^recoverypassword$', recoverypassword.view, name='data_view'),
    re_path(r'^gestion$', gestion.view, name='gestion_view'),
    # re_path(r'^estandaresmenu$', estandaresview.view, name='estandaresview'),
    # re_path(r'^adm_sistemas/estandares', estadares_desarrollo.view, name='estadares_desarrollo_view'),
    re_path(r'^adm_sistemas$', adm_sistemas.view, name='adm_sistemas_view'),
    re_path(r'^adm_sistemas/arbolcategoriassagest$', adm_sys_modules_categoriassagest.view, name='adm_sys_modules_visit'),
    re_path(r'^adm_sistemas/arbolcategoriassga$', adm_sys_modules_categorias.view, name='adm_sys_modules_visit'),
    re_path(r'^adm_sistemas/visita_modulos$', adm_sys_modules_visit.view, name='adm_sys_modules_visit'),
    re_path(r'^adm_sistemas/users$', adm_sys_users.view, name='adm_sys_users_view'),
    re_path(r'^adm_sistemas/groups$', adm_sys_groups.view, name='adm_sys_groups_view'),
    re_path(r'^adm_sistemas/modules$', adm_sys_modules.view, name='adm_sys_modules_view'),
    re_path(r'^adm_sistemas/groups_modules$', adm_sys_groups_modules.view, name='adm_sys_groups_modules_view'),
    re_path(r'^adm_sistemas/persons$', adm_sys_persons.view, name='adm_sys_persons_view'),
    re_path(r'^adm_sistemas/user_access_profile$', adm_sys_user_access_profile.view, name='adm_sys_user_access_profile_view'),
    re_path(r'^adm_sistemas/academic_period$', adm_sys_academic_period.view, name='adm_sys_academic_period_view'),
    re_path(r'^adm_sistemas/academic_period/statistics$', adm_sys_enroll_statistics.view, name='adm_sys_enroll_statistics_view'),
    re_path(r'^adm_sistemas/global_variables$', adm_sys_global_variables.view, name='adm_sys_global_variables_view'),
    re_path(r'^adm_sistemas/special_enrollment_process$', adm_sys_special_enroll_process.view, name='adm_sys_special_enroll_process_view'),
    re_path(r'^adm_sistemas/special_enrollment_process/motivo$', adm_sys_special_enroll_reason.view, name='adm_sys_special_enroll_reason_view'),
    re_path(r'^adm_sistemas/special_enrollment_process/estado$', adm_sys_special_enroll_state.view, name='adm_sys_special_enroll_state_view'),
    re_path(r'^adm_sistemas/remove_enrollment_process$', adm_sys_remove_enroll_process.view, name='adm_sys_remove_enroll_process_view'),
    re_path(r'^adm_sistemas/remove_enrollment_process/motivo$', adm_sys_remove_enroll_reason.view, name='adm_sys_remove_enroll_reason_view'),
    re_path(r'^adm_sistemas/remove_enrollment_process/estado$', adm_sys_remove_enroll_state.view, name='adm_sys_remove_enroll_state_view'),
    re_path(r'^adm_sistemas/config_carnet$', adm_sys_carnet_config.view, name='adm_sys_carnet_config_view'),
    re_path(r'^adm_sistemas/web_services$', adm_sys_web_services.view, name='adm_sys_web_services_view'),
    re_path(r'^adm_sistemas/web_services/wsdl$', adm_sys_web_services_wsdl.view, name='adm_sys_web_services_wsdl_view'),
    re_path(r'^adm_sistemas/setting_template$', adm_sys_setting_template.view, name='adm_sys_setting_template_view'),
    re_path(r'^adm_sistemas/non_working_days$', adm_sys_non_working_days.view, name='adm_sys_non_working_days_view'),
    re_path(r'^adm_sistemas/permissions$', adm_sys_permissions.view, name='adm_sys_permissions'),
    re_path(r'^adm_sistemas/report_list$', adm_sys_report_list.view, name='adm_sys_report_list'),
    re_path(r'^adm_sistemas/secretary/services$', adm_sys_secretary.services, name='adm_sys_secretary_services'),
    re_path(r'^adm_sistemas/secretary/categories$', adm_sys_secretary.categories, name='adm_sys_secretary_categories'),
    re_path(r'^adm_sistemas/options$', adm_sys_options.view, name='adm_sys_options'),
    re_path(r'^adm_sistemas/imagen_moodle$', adm_sys_imagen_moodle.view, name='adm_sys_imagen_moodle_view'),
    re_path(r'^adm_sistemas/linea_grafica$', adm_sys_linea_grafica.view, name='adm_sys_linea_grafica_view'),
    re_path(r'^my_profile/security$', my_profile_security.view, name='my_profile_security_view'),
    re_path(r'^security/device$', security_device.view, name='security_device_view'),
    re_path(r'^misactividades$', adm_actividades_scrum.view, name='adm_actividades_scrum_view'),
    re_path(r'^adm_scrum_actividades$', scrum_actividades.view, name='adm_scrum'),
    re_path(r'^adm_execute_process$', execute_process.view, name='adm_execute_process'),
]
