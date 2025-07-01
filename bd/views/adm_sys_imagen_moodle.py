from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module
from bd.forms import ImagenMoodleForm
from sga.commonviews import adduserdata
from django.db import connection, transaction
from sga.funciones import generar_nombre, log, MiPaginador
from django.db.models.query_utils import Q
from sga.models import ImagenMoodle
from settings import DEBUG


@login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        action = data['action'] = request.POST['action']
        if action == 'add':
            try:
                form = ImagenMoodleForm(request.POST, request.FILES)
                file = None
                valid_ext = [".jpg", ".JPG", ".jpeg", ".JPEG", ".png", ".PNG"]
                if 'imagen' in request.FILES:
                    file = request.FILES['imagen']
                    if file:
                        if file.size > 4194304:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo es mayor a 4 Mb."})
                        else:
                            newfilesd = file._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext in valid_ext:
                                file._name = generar_nombre("imgmoodle", file._name)
                            else:
                                return JsonResponse({"result": "bad", "mensaje": f"Error, Solo archivos con extención .jpg .jpeg, .png"})
                if form.is_valid():
                    im = ImagenMoodle(descripcion=form.cleaned_data['descripcion'])
                    im.imagen = file if file else None
                    im.save(request)
                    log(u'Adiciono nueva imagen: %s' % im, request, "add")
                else:
                    print([{k: v[0]} for k, v in form.errors.items()])
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})

                return JsonResponse({"result": 'ok'}, safe=False)
            except Exception as ex:
                transaction.rollback()
                pass
        if action == 'delete':
            try:
                with transaction.atomic():
                    instancia = ImagenMoodle.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Eliminó imagen: %s' % instancia, request, "del")
                    res_json = {"error": False}
            except Exception as ex:
                transaction.rollback()
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)
        HttpResponseRedirect("/adm_sistemas?info=Solicitud incorrecta.")
    else:
        if 'action' in request.GET:
            action = data['action'] = request.GET['action']
            if action == 'add':
                try:
                    form = ImagenMoodleForm()
                    data['title'] = u"Adicionar imagen"
                    data['form'] = form
                    return render(request, "adm_sistemas/permissions/crud/add.html", data)
                except Exception as ex:
                    HttpResponseRedirect(f"/adm_sistemas?info={ex.__str__()}")

            HttpResponseRedirect("/adm_sistemas?info=Solicitud incorrecta.")
        else:
            try:
                data['title'] = 'Imágenes de moodle'
                filtros, s, url_vars = Q(status=True), request.GET.get('s', ''), ''

                if s:
                    filtros = filtros & (Q(permiso__name__icontains=s) | Q(permiso__codename__icontains=s) | Q(descripcion__icontains=s))
                    data['s'] = f"{s}"
                    url_vars += f"&s={s}"

                paging = MiPaginador(ImagenMoodle.objects.filter(filtros).order_by('-id'), 10)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session:
                        paginasesion = int(request.session['paginador'])
                    if 'page' in request.GET:
                        p = int(request.GET['page'])
                    else:
                        p = paginasesion
                    try:
                        page = paging.page(p)
                    except:
                        p = 1
                    page = paging.page(p)
                except:
                    page = paging.page(p)
                request.session['paginador'] = p
                data['paging'] = paging
                data['page'] = page
                data['rangospaging'] = paging.rangos_paginado(p)
                data['imagenes'] = page.object_list
                data['url_vars'] = url_vars
                url_path = 'http://127.0.0.1:8000'
                if not DEBUG:
                    url_path = 'https://sga.unemi.edu.ec'
                data['url_path'] = url_path
                return render(request, "adm_sistemas/imagenmoodle/view.html", data)

            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})