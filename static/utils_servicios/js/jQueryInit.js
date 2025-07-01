jQuery.browser = {};

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