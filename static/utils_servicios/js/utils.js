<!----------------- JQUERY FUNCIONAL-------------------->

jQuery.browser = {};
request_path = localStorage.getItem("request_path");

(function () {
    jQuery.browser.msie = false;
    jQuery.browser.version = 0;
    if (navigator.userAgent.match(/MSIE ([0-9]+)\./)) {
        jQuery.browser.msie = true;
        jQuery.browser.version = RegExp.$1;
    }
})();

<!----------------- CARGA DE CRFTOKEN PARA CONSULTAS AJAX-------------------->
function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

var csrftoken = getCookie('csrftoken');

function csrfSafeMethod(method) {
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

$.ajaxSetup({
    beforeSend: function (xhr, settings) {
        if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
    }
});
<!----------------- CARGAS AL DOOM -------------------->
$(function () {

<!----------------- RECUPERACIÓN DE VARIABLES Y TRATADO SEGÚN EXISTENCIA-------------------->
    let persona = localStorage.getItem("tiene_persona");
    let check_session = localStorage.getItem("tiene_check_session");
    if (persona && check_session) {
        chequearsesion = function () {
            $.ajax({
                type: "POST",
                url: "/api",
                data: {'a': 'checksession'},
                success: function (data) {
                    if (data.result == 'ok') {
                        if (data.nuevasesion) {
                            bloqueointerface();
                            location.href = '/signout';
                        }
                    }
                },
                dataType: "json"
            });
        };
        setInterval(chequearsesion, 60000);
    }
    if (persona) {
        logout = function() {
            bloqueointerface();
            localStorage.clear();
            $.ajax({
                type: "POST",
                url: "/api",
                data: {'a': 'logout'},
                headers: {
                    "X-CSRFToken": csrftoken // Incluir el token CSRF en los encabezados de la solicitud
                },
                success: function (data) {
                    if (data.result == 'ok') {
                        location.href = data.url;
                    } else {
                        logout();
                    }
                },
                error: function () {
                    logout();
                },
                dataType: "json"
            });
        };
        $('.logoutuser').click(function () {
            logout();
        });
    }

    const tabla = $('.tabla_responsive').DataTable({
        responsive: true,
        ordering: false,
        paging: false,
        searching: false,
        bInfo: false,
        dom: 'Bfrtip',
        language: {
            "url": '/static/js/i18n/Spanish.json'
        },
        buttons: []
    });

    tabla.buttons().container().appendTo('.tabla_responsive .col-md-6:eq(0)');

    $('.tabla_responsive tbody').on('click', 'tr', function () {
        var data = tabla.row(this).data();
    });
<!----------------- EJECUCIÓN DE FUNCIONES SEGÚN CLASES O IDS -------------------->
    $('.bloqueo_pantalla').click(function () {
        bloqueointerface();
    })
});

<!----------------- FUNCIONES REUTILIZABLES -------------------->
function bloqueointerface() {
    if (!$(".blockUI").length) {
        $.blockUI({
            message: $('#throbber'),
            css: {
                backgroundColor: 'transparent',
                border: '0',
                zIndex: 9999999
            },
            overlayCSS: {
                backgroundColor: '#fff',
                opacity: 0.8,
                zIndex: 9999990
            }
        });
    }
}

function CargarSwitchery() {
        // Cargar el archivo CSS de Switchery
        let link = document.createElement('link');
        link.rel = 'stylesheet';
        link.type = 'text/css';
        link.href = '/static/switchery/switchery.min.css';
        document.head.appendChild(link);

        let script = document.createElement('script');
        script.src = '/static/switchery/switchery.min.js';
        script.onload = function() {
            var elems = Array.prototype.slice.call(document.querySelectorAll('.js-switch'));
            elems.forEach(function (switchEl) {
                switchery = new Switchery(switchEl, {
                    size: 'small',
                    color: 'rgba(17,218,35,0.56)',
                    secondaryColor: 'rgba(218,0,7,0.74)'
                });
                // // Agregar un listener de evento change para cada Switchery
                // switchEl.addEventListener('change', function(event) {
                //     if (event.target.checked) {
                //         console.log('Switch marcado:', event.target.id);
                //         // Aquí puedes hacer algo cuando se marca el switch
                //     } else {
                //         console.log('Switch desmarcado:', event.target.id);
                //         // Aquí puedes hacer algo cuando se desmarca el switch
                //     }
                // });
            });
        };
        document.head.appendChild(script);
    }

function formatRepo(repo) {
if (repo.loading) {
    return 'Buscando..'
}
var option = '';
if (/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)) {
    option = $(`<b>${repo.text}</b>`);
} else {
    option = $(`<div class="wrapper container"><div class="row"><div class="col-lg-2 text-center"><img src="${repo.foto}" width="50px" height="50px" class="w-25px rounded-circle me-2"></div><div class="col-lg-10 text-left"><b>Documento:</b> ${repo.documento}<br><b>Nombres:</b> ${repo.text}<br>${repo.departamento ? `<b>Departamento: </b><span>${repo.departamento}</span>` : ''} </div></div></div>`);
}
return option;
}

ItemsDisplayPersonas = function (item) {
if (item.text && item.documento) {
    return $(`<img src="${item.foto}" width="25px" height="25px" class="w-25px rounded-circle me-2"><span>${item.text}</span>`);
} else if (item) {
    return item.text;
} else {
    return ' Consultar Personas';
}
};

// Buscar persona por tipo, entre los siguientes disponibles:
// administrativos, distributivos, estudiantes, docentes o sin enviar nada busca todo
// pueden enviar varios tipos separados por comas ejemplo: 'distributivos, estudiantes'
// de igual maneras ids para excluir en la busqueda: '1,2,3,4'
function buscarPersona(objeto, tipo, action='buscarpersonas',args='') {
objeto.select2({
    width: '100%',
    placeholder: "Consultar Personas",
    allowClear: true,
    ajax: {
        url: function (params) {
            return `{{ reques.path }}?action=${action}&q=${params.term}&tipo=${tipo}&idsagregados=${args}`;
        },
        dataType: 'json',
        delay: 250,
        data: function (params) {
            return {
                q: params.term,
                page: params.page
            };
        },
        processResults: function (data, params) {
            params.page = params.page || 1;
            return {
                results: data.results,
                pagination: {
                    more: (params.page * 30) < data.total_count
                }
            };
        },
        cache: true
    },
    escapeMarkup: function (markup) {
        return markup;
    }, // let our custom formatter work
    minimumInputLength: 1,
    templateResult: formatRepo, // omitted for brevity, see the source of this page
    templateSelection: ItemsDisplayPersonas // omitted for brevity, see the source of this page
});
}

// Permite cargar un segundo select secundario,
// Solo se tiene que enviar el action, el objeto principal y el secundario a cargar data.
function cargarSelectSecundario(action, objeto_p, objeto_s) {
objeto_p.on("select2:select", function (evt) {
    // Realizar la consulta AJAX utilizando el valor seleccionado
    cargarLista(action, objeto_p, objeto_s)
});
}

// Permite cargar un select con los parametros de busqueda enviado
function cargarSelect(objeto, action, title = 'Buscar contenido...') {
objeto.select2({
    width: '100%',
    placeholder: title,
    allowClear: true,
    ajax: {
        url: function (params) {
            return `{{ reques.path }}?action=${action}&q=${params.term}`;
        },
        dataType: 'json',
        delay: 250,
        data: function (params) {
            return {
                q: params.term,
            };
        },
        processResults: function (data, params) {
            return {
                results: data,
            };
        },
        cache: true
    },
    minimumInputLength: 1,
});
}

// Codependiente para cargar select secundario
function cargarLista(action, objeto_p, objeto_s, id='', args='') {
 console.log(args)
bloqueointerface()
let value = objeto_p.val();
$.ajax({
        url: request_path,
        type: 'GET',
        data: {'id': value, 'action': action, 'args':args},
        success: function (response) {
            $.unblockUI();
            // Limpiar el select secundario
            objeto_s.empty();

            // Llenar el select secundario con las opciones de la respuesta de la consulta AJAX
            $.each(response.data, function (index, option) {
                objeto_s.append($('<option>').text(option.text).val(option.value));
            });

            // Actualizar el select secundario con las nuevas opciones
            objeto_s.val(id).trigger('change');
        },
        error: function (xhr, status, error) {
            $.unblockUI();
            // Manejar el error de la consulta AJAX si es necesario
        }
    });
}

// Permite validar que se ingresen solo números al momento de presionar una tecla
function soloNumerosKeydown(objeto) {
objeto.addEventListener('input', function (event) {
    const valor = objeto.value;

    // Remover caracteres no numéricos excepto punto y coma
    const valorLimpio = valor.replace(/[^0-9]/g, '');

    // Asignar el valor limpio al campo de entrada
    objeto.value = valorLimpio;
});
}

// Permite realizar funcionalidad a input tipo text con diseño para ingreso de datos solo numéricos ****
function sumaNumeroResta(objeto){
//Control de suma y resta mas validador//
objeto.keypress(function (e) {
    return solodigitos(e)
})

$(".sumar").click(function () {
    let cant = 0
    var name = $(this).attr('data-id')
    if ($("#id_" + name).val()) {
        cant = parseInt($("#id_" + name).val())
    }
    $("#id_" + name).val(cant + 1)
})

$(".restar").click(function () {
    let cant = 0
    var name = $(this).attr('data-id')
    if ($("#id_" + name).val()) {
        cant = parseInt($("#id_" + name).val())
    }
    if (cant > 1) {
        $("#id_" + name).val(cant - 1)
    }
})

solodigitos = function (e) {
    if (e.which != 8 && e.which != 0 && (e.which < 48 || e.which > 57)) {
        return false;
    }
};
}

// Permite seleccionar todos y desmarcar todos segun se requiera ****
// Estructura de input en html para su funcionamiento
// Seleccionar todo: <input type="checkbox" name="checkall" id="check_all" class="checkall">
// Items seleccionados: <span class="items-seleccionados">0</span>
// Todos los checkbox tiene que tener la clase seleccion
function comprobarSeleccion() {
var checkboxes = document.querySelectorAll('.seleccion');
var algunoSeleccionado = false;
var sinSeleccionar = false;
var cont = 0
for (var i = 0; i < checkboxes.length; i++) {
    if (checkboxes[i].checked) {
        algunoSeleccionado = true;
        cont += 1
    } else {
        sinSeleccionar = true;
    }
}
if (sinSeleccionar) {
    $(".checkall").prop('checked', false);
} else {
    $(".checkall").prop('checked', true);
}
$(".items-seleccionados").text(cont)
}

// Permite realizar una consulta ajax al metodo GET segun se requiera ****
function consultaAjax(value, action, url = request_path, args='', type='GET') {
bloqueointerface()
$.ajax({
    url: url,
    type: type,
    data: {'value': value,'args':args, 'action': action},
    success: function (response) {
        $.unblockUI();
        if (response.results === false){
            mensajeDanger(response.mensaje)
        }else{
            consultaAjaxResponse(response)
        }
    },
    error: function (xhr, status, error) {
        $.unblockUI();
        alertaDanger('Error de conexión')
        // Manejar el error de la consulta AJAX si es necesario
    }
});
}

function updateCheckMain(obj, action, args = '', unico = false) {
    bloqueointerface();
    let id = obj.attr('data-id')
    let clase = "."+obj.attr('data-class')
    let check = obj.is(':checked');
    $.ajax({
        type: "POST",
        url: request_path,
        data: {'action': action, 'id': id, 'val': check, 'args':args},
        success: function (data) {
            if (data.result === true) {
                $.unblockUI();
                alertaSuccess(data.mensaje)
                if (unico && check) {
                    $(`${clase}`).prop('checked', false)
                    obj.prop('checked', check);
                }
            } else {
                $.unblockUI();
                obj.prop('checked', !check);
                alertaDanger(data.mensaje);
            }
        },
        error: function () {
            $.unblockUI();
            obj.prop('checked', !check);
            alertaInfo("Error al enviar los datos.");
        },
        dataType: "json"
    });
}

<!----------------- MENSAJES FLOTANTES SWEETALERT 2 -------------------->
function mensajeSuccess(titulo, mensaje) {
    Swal.fire(titulo, mensaje, 'success')
}

function mensajeWarning(titulo, mensaje) {
    Swal.fire(titulo, mensaje, 'warning')
}

function mensajeDanger(titulo, mensaje) {
    Swal.fire(titulo, mensaje, 'error')
}

function alertaSuccess(mensaje, time = 5000) {
    Swal.fire({
        toast: true,
        position: 'top-end',
        type: 'success',
        title: mensaje,
        showConfirmButton: false,
        timer: time
    })
}

function alertaWarning(mensaje, time = 5000) {
    Swal.fire({
        toast: true,
        position: 'top-end',
        type: 'warning',
        title: mensaje,
        showConfirmButton: false,
        timer: time
    })
}

function alertaDanger(mensaje, time = 5000) {
    Swal.fire({
        toast: true,
        position: 'top-end',
        type: 'error',
        title: mensaje,
        showConfirmButton: false,
        timer: time
    })
}

function alertaInfo(mensaje, time = 5000) {
    Swal.fire({
        toast: true,
        position: 'top-end',
        type: 'info',
        title: mensaje,
        showConfirmButton: false,
        timer: time
    })
}
