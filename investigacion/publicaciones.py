# -*- coding: UTF-8 -*-
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.db import connection, transaction, connections



@transaction.atomic()
def view(request):
    data = {}
    if request.method == 'POST':
        action = request.POST['action']
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            return HttpResponseRedirect(request.path)
        else:
            try:
                cnunemi = connections['sga_select'].cursor()
                sql = """ 
                    SELECT acon.nombre AS areaconocimiento ,
                    ar.nombre as articulos,
                    extract(year from  ar.fechapublicacion) as fecha ,
                    rev.nombre as revista,
                    (select string_agg(base.nombre,',' ) 
                    from sga_baseindexadainvestigacion base
                    INNER JOIN sga_articulosbaseindexada bindex ON  base.id=bindex.baseindexada_id
                    where bindex.articulo_id=ar.id 
                    and base.status=True 
                    and bindex.status=True
                    ) as bases,
                    (
                    SELECT array_to_string(array_agg('<li>'||per.apellido1||' '||per.apellido2||' '||per.nombres),'</li>') AS autor
                    from sga_participantesarticulos par 
                    INNER JOIN sga_profesor pro ON par.profesor_id=pro.id 
                    INNER JOIN sga_persona per ON pro.persona_id=per.id 
                    WHERE ar.id=par.articulo_id  AND par.status=TRUE
                    ) AS participantes
                    from sga_articuloinvestigacion ar 
                    INNER JOIN sga_revistainvestigacion rev ON ar.revista_id=rev.id 
                    INNER JOIN sga_areaconocimientotitulacion acon ON ar.areaconocimiento_id=acon.id
                    where ar.status   

                  """
                if 'ida' in request.GET:
                    data['ida'] = ida = int(request.GET['ida'])
                    if ida > 0:
                        sql = sql + " and acon.id=" + str(ida)
                sql = sql + " ORDER BY ar.fechapublicacion DESC, ar.nombre"
                cnunemi.execute(sql)
                results = cnunemi.fetchall()
                data['articulos'] = results
                data['areasconocimiento'] = areasconocimiento()

                return render(request, "../templates/publicaciones/view.html", data)
            except Exception as ex:
                print(ex)
                HttpResponseRedirect(f"/publicaciones?info={ex.__str__()}")


def areasconocimiento():
    cnunemi1 = connections['sga_select'].cursor()
    sql_areas = """  SELECT distinct areas.id, areas.nombre
         from sga_articuloinvestigacion art
         INNER JOIN sga_areaconocimientotitulacion areas ON areas.id=art.areaconocimiento_id
         WHERE areas.status=True ORDER BY nombre """
    cnunemi1.execute(sql_areas)
    return cnunemi1.fetchall()