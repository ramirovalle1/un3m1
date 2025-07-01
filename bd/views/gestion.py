# -*- coding: UTF-8 -*-
import json
import random
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from django.http import HttpResponse
from bd.models import LogQuery, LogQueryFavoritos, UserQuery
from decorators import secure_module, last_access
from bd.forms import *
from settings import MEDIA_ROOT, MEDIA_URL
from sga.commonviews import adduserdata
from django.db import connection, transaction
from django.template import Context
import sys
from django.template.loader import get_template
from sga.templatetags.sga_extras import encrypt
from sga.funciones import log, puede_realizar_accion, puede_realizar_accion_is_superuser, logquery
import xlwt
from xlwt import *
import io
import xlsxwriter

@login_required(redirect_field_name='ret', login_url='/loginsagest')
# @secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}

    adduserdata(request, data)
    persona = request.session['persona']

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'probarconexion':
            try:
                gestion = request.POST['conexion']
                cursor2 = None
                sql = 'SELECT table_name FROM information_schema.tables'
                if gestion == '1':
                    cursor2 = connections['default'].cursor()
                    data['bdname'] = 'default'
                elif gestion == '2':
                    cursor2 = connections['epunemi'].cursor()
                    data['bdname'] = 'epunemi'
                elif gestion == '3':
                    cursor2 = connections['aulagradoa'].cursor()
                    data['bdname'] = 'aulagradoa'
                elif gestion == '4':
                    cursor2 = connections['db_moodle_virtual'].cursor()
                    data['bdname'] = 'db_moodle_virtual'
                elif gestion == '5':
                    cursor2 = connections['moodle_pos'].cursor()
                    data['bdname'] = 'moodle_pos'
                elif gestion == '6':
                    cursor2 = connections['postulate'].cursor()
                    data['bdname'] = 'postulate'
                elif gestion == '7':
                    cursor2 = connections['deva'].cursor()
                    data['bdname'] = 'deva'
                elif gestion == '8':
                    cursor2 = connections['admision'].cursor()
                    data['bdname'] = 'sag_unemi_edu_ec'
                elif gestion == '9':
                    cursor2 = connections['moodleadmisionvirtual'].cursor()
                    data['bdname'] = 'moodleadmisionvirtual'
                elif gestion == '10':
                    cursor2 = connections['uxplora'].cursor()
                    data['bdname'] = 'uxplora'
                elif gestion == '11':
                    cursor2 = connections['aulagradob'].cursor()
                    data['bdname'] = 'aulagradob'
                cursor2.execute(sql)
                data['baseafectada'] = dict(BASE_CONEXION)[int(gestion)]
                data['tablas'] = tablas = list([c[0] for c in cursor2.fetchall()])
                template = get_template("gestion/tablas.html")
                return JsonResponse({"result": True, 'data': template.render(data)})
            except Exception as ex:
                return JsonResponse({"result": False, 'mensaje': '{}'.format(ex)})

        elif action == 'mislogs':
            try:
                data['listado'] = LogQuery.objects.filter(usuario_creacion=request.user).order_by('-pk')
                data['basechoices'] = BASE_CONEXION
                template = get_template("gestion/mislogs.html")
                return JsonResponse({"result": True, 'data': template.render(data)})
            except Exception as ex:
                return JsonResponse({"result": False, 'mensaje': '{}'.format(ex)})

        elif action == 'addfavoritos':
            try:
                lq = LogQuery.objects.filter(id=int(request.POST['id'])).first()
                if not request.POST['descripcion']:
                    return JsonResponse({"result": False, 'mensaje': u'Ingrese la descripción.'})

                if not LogQueryFavoritos.objects.values('id').filter(logquery__id=lq.pk, status=True).exists():
                    favoritos = LogQueryFavoritos(logquery=lq, descripcion=request.POST['descripcion'])
                    favoritos.save(request)
                    log("Agrego el query %s a favoritos" % lq.pk, request, "add")
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, 'mensaje': u'{}'.format(ex)})

        elif action == 'delfavoritos':
            try:
                favoritos = LogQueryFavoritos.objects.filter(logquery_id=int(request.POST['id']), status=True)
                # for x in favoritos:
                #     x.delete()
                favoritos.update(status=False)
                log("Eliminó el query %s de favoritos" % favoritos.first(), request, "del")
                return JsonResponse({"result": True})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, 'mensaje': u'{}'.format(ex)})

        elif action == 'delfavoritos_admin':
            try:
                fav = LogQueryFavoritos.objects.filter(pk=int(request.POST['id']), status=True).first()
                fav.status = False
                fav.save()
                log("Eliminó el query %s de favoritos" % fav, request, "del")
                return JsonResponse({"result": True})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, 'mensaje': u'{}'.format(ex)})

        elif action == 'traercampos':
            try:
                dbname = request.POST['dbname']
                schema = 'public'
                modelo = request.POST['modelo']
                query = "SELECT column_name FROM information_schema.columns WHERE table_schema = '{}' AND table_name   = '{}';".format(schema, modelo)
                cursor = connections[dbname].cursor()
                cursor.execute(query)
                campos = list([c[0] for c in cursor.fetchall()])
                return JsonResponse({"result": True, 'campos': campos})
            except Exception as ex:
                return JsonResponse({"result": False, 'mensaje': '{}'.format(ex)})

        elif action == 'traertablas':
            try:
                gestion = request.POST['conexion']
                cursor2 = None
                nombretabla = request.POST['nombretabla']
                if nombretabla != '':
                    sql = "SELECT table_name FROM information_schema.tables WHERE TABLE_NAME ILIKE '%{}%' LIMIT 15".format(nombretabla)
                    if gestion == '1':
                        cursor2 = connections['default'].cursor()
                        data['bdname'] = 'default'
                    elif gestion == '2':
                        cursor2 = connections['epunemi'].cursor()
                        data['bdname'] = 'epunemi'
                    elif gestion == '3':
                        cursor2 = connections['aulagradoa'].cursor()
                        data['bdname'] = 'aulagradoa'
                    elif gestion == '4':
                        cursor2 = connections['db_moodle_virtual'].cursor()
                        data['bdname'] = 'db_moodle_virtual'
                    elif gestion == '5':
                        cursor2 = connections['moodle_pos'].cursor()
                        data['bdname'] = 'moodle_pos'
                    elif gestion == '6':
                        cursor2 = connections['postulate'].cursor()
                        data['bdname'] = 'postulate'
                    elif gestion == '7':
                        cursor2 = connections['deva'].cursor()
                        data['bdname'] = 'deva'
                    elif gestion == '8':
                        cursor2 = connections['admision'].cursor()
                        data['bdname'] = 'sag_unemi_edu_ec'
                    elif gestion == '9':
                        cursor2 = connections['moodleadmisionvirtual'].cursor()
                        data['bdname'] = 'moodleadmisionvirtual'
                    elif gestion == '10':
                        cursor2 = connections['uxplora'].cursor()
                        data['bdname'] = 'uxplora'
                    elif gestion == '11':
                        cursor2 = connections['aulagradob'].cursor()
                        data['bdname'] = 'aulagradob'
                    cursor2.execute(sql)
                    data['baseafectada'] = dict(BASE_CONEXION)[int(gestion)]
                    data['tablas'] = tablas = list([c[0] for c in cursor2.fetchall()])
                    template = get_template("gestion/tablasresultado.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                else:
                    return JsonResponse({"result": False})
            except Exception as ex:
                return JsonResponse({"result": False, 'mensaje': '{}'.format(ex)})

        elif action == 'ejecutar':
            try:
                import unicodedata
                if persona.usuario.is_superuser or 49 in persona.usuario.groups.values_list('id',flat=True):
                    sql = u"%s"%(request.POST['query'])
                    filename = "resultados"
                    sqllower=sql.lower()
                    idsequipos = UserQuery.objects.values_list('user_id',flat=True).filter(status=True)
                    # if not puede_realizar_accion_is_superuser(request, 'sga.puede_ejecutar_update_bd'):
                    if 'update' in sql and not 'where' in sql and not 'WHERE' in sql:
                        return JsonResponse({"result": "bad", "mensaje": u"No puede ejecutar un UPDATE in WHERE."})
                    if 'UPDATE' in sql and not 'where' in sql and not 'WHERE' in sql:
                        return JsonResponse({"result": "bad", "mensaje": u"No puede ejecutar un UPDATE in WHERE."})
                    # if not puede_realizar_accion_is_superuser(request, 'sga.puede_ejecutar_delete_bd'):
                    if 'DELETE' in sql and not 'where' in sql and 'WHERE' not in sql:
                        return JsonResponse({"result": "bad", "mensaje": u"No puede ejecutar un DELETE in WHERE."})
                    if 'delete' in sql and not 'where' in sql and not 'WHERE' in sql:
                        return JsonResponse({"result": "bad", "mensaje": u"No puede ejecutar un DELETE in WHERE."})
                    # if not puede_realizar_accion_is_superuser(request, 'sga.puede_ejecutar_crud_bd'):
                    if 'DROP' in sqllower or 'drop' in sqllower:
                        return JsonResponse({"result": "bad", "mensaje": u"No puede ejecutar esta sentencia."})
                    if 'mooc_question_answers' in sqllower or 'MOOC_QUESTION_ANSWERS' in sqllower:
                        return JsonResponse({"result": "bad", "mensaje": u"No puede ejecutar esta sentencia."})
                    if not persona.usuario_id in idsequipos:
                        if 'DELETE' in sqllower or 'UPDATE' in sqllower or 'delete' in sqllower or 'update' in sqllower:
                            return JsonResponse({"result": "bad", "mensaje": u"No puede ejecutar esta sentencia."})

                    gestion = request.POST['base']
                    baseafectada = dict(BASE_CONEXION)[int(gestion)]
                    cursor2 = None
                    if gestion == '1':
                        cursor2 = connections['default'].cursor()
                    elif gestion == '2':
                        cursor2 = connections['epunemi'].cursor()
                    elif gestion == '3':
                        cursor2 = connections['aulagradoa'].cursor()
                    elif gestion == '4':
                        cursor2 = connections['db_moodle_virtual'].cursor()
                    elif gestion == '5':
                        cursor2 = connections['moodle_pos'].cursor()
                    elif gestion == '6':
                        cursor2 = connections['postulate'].cursor()
                    elif gestion == '7':
                        cursor2 = connections['deva'].cursor()
                    elif gestion == '8':
                        cursor2 = connections['admision'].cursor()
                    elif gestion == '9':
                        cursor2 = connections['moodleadmisionvirtual'].cursor()
                    elif gestion == '10':
                        cursor2 = connections['uxplora'].cursor()
                        data['bdname'] = 'uxplora'
                    elif gestion == '11':
                        cursor2 = connections['aulagradob'].cursor()
                    cursor2.execute(sql)
                    rows_effected = cursor2.rowcount

                    try:
                        name = f"{persona}".lower()
                        filename = unicodedata.normalize('NFD', f"resultados {name}").encode('ascii', 'ignore').decode("utf-8").replace(' ', '_')
                    except Exception as ex:
                        pass
                    try:
                        data1 = {}
                        data1['resultados'] = listado = cursor2.fetchall()
                        data1['resultados_count'] = len(listado)
                        data1['tablacampos'] = [desc[0] for desc in cursor2.description]
                        data1['filename'] = filename
                        template = get_template("gestion/resultados.html")
                        json_content = template.render(data1)
                        # log(u'Ejecutó un query: %s ' % (sql), request, "add")
                        logquery(baseafectada, sql, rows_effected, request)
                        return JsonResponse(
                            {"result": "ok", 'mensaje': u"Cantidad de filas afectadas %s" % rows_effected,
                             'resultados': json_content})
                    except Exception as ex:
                        pass
                    log(u'Ejecutó un query: %s ' % (sql), request, "edit")
                    logquery(baseafectada, sql, rows_effected, request)
                    return JsonResponse({"result": "ok",'mensaje':u"Cantidad de filas afectadas %s"%rows_effected})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al ejecutar las sentencias. {}".format(ex)})

        elif action == 'export_to_excel':
            try:
                from bd.funciones import export_query_to_excel
                if persona.usuario.is_superuser or persona.usuario.is_staff:
                    sql = u"%s"%(request.POST['value'])
                    gestion = request.POST['base']
                    baseafectada = dict(BASE_CONEXION)[int(gestion)]
                    sqllower = sql.lower()
                    if not puede_realizar_accion_is_superuser(request, 'sga.puede_ejecutar_update_bd'):
                        if 'update' in sql and not 'where' in sql and not 'WHERE' in sql:
                            return JsonResponse({'error': True, "mensaje": u"No puede ejecutar un UPDATE in WHERE."})
                        if 'UPDATE' in sql and not 'where' in sql and not 'WHERE' in sql:
                            return JsonResponse({'error': True, "mensaje": u"No puede ejecutar un UPDATE in WHERE."})
                    if not puede_realizar_accion_is_superuser(request, 'sga.puede_ejecutar_delete_bd'):
                        if 'DELETE' in sql and not 'where' in sql and 'WHERE' not in sql:
                            return JsonResponse({'error': True, "mensaje": u"No puede ejecutar un DELETE in WHERE."})
                        if 'delete' in sql and not 'where' in sql and not 'WHERE' in sql:
                            return JsonResponse({'error': True, "mensaje": u"No puede ejecutar un DELETE in WHERE."})
                    if not puede_realizar_accion_is_superuser(request, 'sga.puede_ejecutar_crud_bd'):
                        if 'DROP' in sqllower or 'drop' in sqllower or 'database' in sqllower or 'DATABASE' in sqllower or 'table' in sqllower or 'TABLE' in sqllower or 'alter' in sqllower or 'ALTER' in sqllower or 'CREATE' in sqllower or 'create' in sqllower or 'using' in sqllower or 'USING' in sqllower:
                            return JsonResponse({'error': True, "mensaje": u"No puede ejecutar esta sentencia."})
                    if not 'select' in sqllower:
                        return JsonResponse({'error': True, "mensaje": u"No puede ejecutar esta sentencia, solo se puede ejecutar sentencias Select."})
                    if 'mooc_question_answers' in sqllower or 'MOOC_QUESTION_ANSWERS' in sqllower:
                        return JsonResponse({"result": "bad", "mensaje": u"No puede ejecutar esta sentencia."})
                    cursor = None
                    if gestion == '1':
                        cursor = connections['default'].cursor()
                    if gestion == '2':
                        cursor = connections['epunemi'].cursor()
                    if gestion == '3':
                        cursor = connections['aulagradoa'].cursor()
                    if gestion == '4':
                        cursor = connections['db_moodle_virtual'].cursor()
                    if gestion == '5':
                        cursor = connections['moodle_pos'].cursor()
                    if gestion == '6':
                        cursor = connections['postulate'].cursor()
                    if gestion == '7':
                        cursor = connections['deva'].cursor()
                    if gestion == '8':
                        cursor = connections['admision'].cursor()
                    if gestion == '9':
                        cursor = connections['moodleadmisionvirtual'].cursor()
                    if gestion == '10':
                        cursor = connections['uxplora'].cursor()
                    if gestion == '11':
                        cursor = connections['aulagradob'].cursor()
                    # cursor.execute(sql)
                    # rows_effected = cursor.rowcount
                    # listado = cursor.fetchall()
                    # campos = [desc[0] for desc in cursor.description]
                    directory = os.path.join(MEDIA_ROOT, 'reportes', 'gestion')
                    try:
                        os.stat(directory)
                    except:
                        os.mkdir(directory)
                    name_document = 'reporte_{}_{}'.format(request.user.username, str(date.today()))
                    nombre_archivo = name_document + "_{}.xlsx".format(random.randint(1, 10000).__str__())
                    directory = os.path.join(MEDIA_ROOT, 'reportes', 'gestion', nombre_archivo)
                    export = export_query_to_excel(request, sql, cursor, nombre_archivo, [], directory, baseafectada, sheet_name='Reporte')
                    # __author__ = 'Unemi'
                    # workbook = xlsxwriter.Workbook(directory, {'constant_memory': True})
                    # ws = workbook.add_worksheet('resultados')
                    # fuentecabecera = workbook.add_format({
                    #     'align': 'center',
                    #     'bg_color': 'silver',
                    #     'border': 1,
                    #     'bold': 1
                    # })
                    #
                    # formatoceldacenter = workbook.add_format({
                    #     'border': 1,
                    #     'valign': 'vcenter',
                    #     'align': 'center'})
                    #
                    # row_num, numcolum = 0, 0
                    #
                    # for col_num in campos:
                    #     ws.write(row_num, numcolum, col_num,fuentecabecera)
                    #     ws.set_column(row_num,numcolum, 40)
                    #     numcolum += 1
                    # row_num += 1
                    # for lis in listado:
                    #     colum_num = 0
                    #     for l in lis:
                    #         ws.write(row_num, colum_num, l,formatoceldacenter)
                    #         ws.set_column(row_num, numcolum, 40)
                    #         colum_num += 1
                    #     row_num += 1
                    #
                    # workbook.close()
                    # response = HttpResponse(directory, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    # response['Content-Disposition'] = 'attachment; filename=%s' % name_document
                    # #
                    # url_file = "{}reportes/gestion/{}".format(MEDIA_URL, nombre_archivo)
                    # logquery(baseafectada, sql, rows_effected, request, url=url_file)
                    if not export['error']:
                        response = HttpResponse(directory, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                        response['Content-Disposition'] = 'attachment; filename=%s' % name_document
                        #
                        url_file = "{}reportes/gestion/{}".format(MEDIA_URL, nombre_archivo)
                        return JsonResponse({'error': False, 'url': url_file})
                    raise NameError(export['message'])
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'error': True, "mensaje": u"Error al ejecutar las sentencias. {}".format(ex)})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'loadfavorites':
                try:
                    data['title'] = u"Mis Favoritos"
                    data['logqueryfavoritos'] = LogQueryFavoritos.objects.filter(status=True)
                    template = get_template("gestion/loadfavorites.html")
                    return JsonResponse({"result": True, 'html': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

            elif action == 'loadmislogstable':
                try:
                    data_table = {}
                    filtro = (Q(status=True) & Q(usuario_creacion=request.user))
                    search = request.GET.get('search', '')
                    if search:
                        filtro &= (Q(query__icontains=search) | Q(baseafectada__icontains=search))

                    init, ends = int(request.GET['inicio']), int(request.GET['limite'])
                    datalogquery = LogQuery.objects.values('id', 'fecha_creacion', 'baseafectada', 'query', 'filasafectadas', 'url_archivo', 'logqueryfavoritos__status').filter(filtro).order_by('-pk').distinct('pk')
                    array_data = [v for k, v in enumerate(datalogquery[init:init + ends], init)]
                    data_table['length'] = datalogquery.count()
                    data_table['data'] = array_data
                    return JsonResponse(json.dumps(data_table, default=str), safe=False)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta. %s" % ex})

            return HttpResponseRedirect(request.path)
        else:
            try:
                if persona.usuario.is_superuser or 49 in persona.usuario.groups.values_list('id',flat=True):
                    data['title'] = u'EJECUTAR SENTENCIAS'
                    data['form'] = QueryForm()
                    query = 'SELECT table_name FROM information_schema.tables'
                    cursor = connection.cursor()
                    cursor.execute(query)
                    data['tablas'] = tablas = list([c[0] for c in cursor.fetchall()])
                    dominiosistema = request.build_absolute_uri('/')[:-1].strip("/")
                    if '127.0.0.1' in dominiosistema:
                        enproduccion = False
                    else:
                        enproduccion = True
                    data['enproduccion'] = enproduccion
                    return render(request, "gestion/add.html", data)
                else:
                    return redirect('/')
            except Exception as ex:
                pass
