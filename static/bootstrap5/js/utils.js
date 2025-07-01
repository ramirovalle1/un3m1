
let request_path = localStorage.getItem("request_path");
// console.log(request_path)

// Buscar persona por tipo, entre los siguientes disponibles:
// administrativos, distributivos, estudiantes, docentes o sin enviar nada busca todo
// pueden enviar varios tipos separados por comas ejemplo: 'distributivos, estudiantes'
// de igual maneras ids para excluir en la busqueda: '1,2,3,4'
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

function buscarPersona(objeto, tipo, action='buscarpersonas',args='', modemovil=false) {
    let url=request_path;
    let name_action = 'action';
    let api = objeto.attr('api');
    if (api){
        url='/api';
        name_action= 'a';
    }
    objeto.select2({
        width: '100%',
        placeholder: "Consultar Personas",
        allowClear: true,
        ajax: {
            url: function (params) {
                return `${url}?${name_action}=${action}&q=${params.term}&tipo=${tipo}&idsagregados=${args}`;
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
        templateResult: function(repo) { return formatRepo(repo, modemovil); }, // omitted for brevity, see the source of this page
        templateSelection: ItemsDisplayPersonas // omitted for brevity, see the source of this page
    });
}

// Permite cargar un segundo select secundario,
// Solo se tiene que enviar el action, el objeto principal y el secundario a cargar data.
function cargarSelectSecundario(action, objeto_p, objeto_s, id='', args='') {
    objeto_p.on("select2:select", function (evt) {
        // Realizar la consulta AJAX utilizando el valor seleccionado
        cargarLista(action, objeto_p, objeto_s,id, args)
    });
}

// Permite cargar un select con los parametros de busqueda enviado
function cargarSelect(objeto, action, title = 'Buscar contenido...', url=request_path) {
    objeto.select2({
        width: '100%',
        placeholder: title,
        allowClear: true,
        ajax: {
            url: function (params) {
                return `${url}?action=${action}&q=${params.term}`;
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
    bloqueointerface()
    let url=request_path;
    let value = objeto_p.val();
    let name_action = 'action';
    let api = objeto_p.attr('api');
    if (api){
        url='/api';
        name_action= 'a';
    }
    $.ajax({
            url: url,
            type: 'GET',
            data: {'id': value, [name_action]:action, 'args':args},
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
                console.log(error)
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

function soloNumerosClass(selectorClase) {
    const elementos = document.querySelectorAll(selectorClase);
    elementos.forEach((objeto) => {
        objeto.addEventListener('input', function (event) {
            soloNumerosKeydown(objeto)
        })
    });
}

// Permite validar que se ingresen solo números con 2 decimales a lado del punto o de la coma
// Se tiene que usar en un input tipo text
function soloMoneyKeydown(objeto) {
    objeto.addEventListener('input', function (event) {
           let valor = objeto.value;

        // Remover caracteres no numéricos excepto punto
        let valorLimpio = valor.replace(/[^0-9.,]/g, '');
        valorLimpio = valorLimpio.replace(',', '.');
        // Asegurar que solo haya un punto decimal y no puntos consecutivos
        if (valorLimpio.indexOf('.') !== -1) {

            let partes = valorLimpio.split('.');
            valorLimpio = partes.shift() + '.' + partes.join('');
        }

        // Evitar puntos consecutivos
        valorLimpio = valorLimpio.replace(/\.{2,}/g, '.');

        // Asignar el valor limpio al campo de entrada
        objeto.value = valorLimpio;
        });
}

function soloMoneyClassKeydown(selectorClase) {
   const elementos = document.querySelectorAll(selectorClase);
    elementos.forEach((objeto) => {
        soloMoneyKeydown(objeto)
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
function consultaAjax(value, action, url = request_path, args='', type='GET', name_action='action') {
    bloqueointerface()
    $.ajax({
        url: url,
        type: type,
        data: {'value': value,'args':args, [name_action]: action},
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

// Permite realizar una consulta ajax al metodo GET segun se requiera ****
function sendPostAjax(value, args='', action, url = request_path) {
    bloqueointerface()
    $.ajax({
        url: url,
        type: 'POST',
        data: {'value': value,'args':args, 'action': action},
        success: function (response) {
            $.unblockUI();
            if (response.result === true){
                alertaSuccess(response.mensaje)
            }else{
                mensajeDanger(response.mensaje)
            }
        },
        error: function (xhr, status, error) {
            $.unblockUI();
            alertaDanger('Error de conexión')
            // Manejar el error de la consulta AJAX si es necesario
        }
    });
}

// Permite ver contraseña de campo password ****
function verContraseña(name) {
   let input = $(`#id_${name}`)
   let icon = $(`#icon_${name}`)
   if (input.attr('type')=='password'){
       input.attr('type','text')
       icon.removeClass('fa-eye').addClass('fa-eye-slash')
   }else{
        input.attr('type','password')
       icon.removeClass('fa-eye-slash').addClass('fa-eye')
   }
}

//Actualizar estados de checks
//Recuerden usar en cada checkbox data-class y data-id para recoger en este metodo
//data-class = Clase que tienen todos los checkbox con quien se va hacer la iteracción si no tiene data-class se pondra activo por defecto
//data-id = id de objeto que se enviara por ajax para cambiar su estado.
//unico = esta variable hace noción que si el checkbox que se va a activar tiene que existir solo uno activo si es asi enviar en true
//args = argumentos extras que requieran enviar no es obligatorio
function updateCheckMain(obj, action, args = '', unico = false, confirm=false, texthtml='') {
    // bloqueointerface();
    let id = obj.attr('data-id')
    let data_class =  obj.attr('data-class')? obj.attr('data-class') : 'activo';
    let data_confirm =  obj.attr('data-confirm')? obj.attr('data-confirm') : 'solo_confirmar';
    let check = obj.is(':checked');
    if (confirm){
        if (data_confirm == 'solo_confirmar'){
            showMessageConfirmCheckMain(obj, action, args, unico, id, data_class, check, texthtml)
        }else if (data_confirm == 'inputText'){
            showMessageInputCheckMain(obj, action, args, unico, id, data_class, check, texthtml)
        }
    }else {
        sendAjaxCheckMain(action, args, unico, id, data_class, check)
    }
}

function showMessageConfirmCheckMain(obj, action, args, unico, id, data_class, check, texthtml) {
    let mensaje = texthtml ? texthtml : '¿Está seguro de cambiar el estado?'
    Swal.fire({
        title: 'Advertencia',
        html: mensaje,
        type: 'warning',
        showCancelButton: true,
        allowOutsideClick: false,
        confirmButtonColor: '#3085d6',
        cancelButtonColor: '#d33',
        confirmButtonText: 'Si, deseo hacerlo',
        cancelButtonText: 'Cancelar'
    }).then((result) => {
        if (result.value) {
            sendAjaxCheckMain(obj, action, args, unico, id, data_class, check)
        } else {
            $.unblockUI();
            obj.prop('checked', !check);
        }
    })
}

function showMessageInputCheckMain(obj, action, args, unico, id, data_class, check, texthtml) {
    let mensaje = texthtml ? texthtml : '¿Está seguro de cambiar el estado?'
    const swalOptions = {
        allowOutsideClick: false,
        allowEscapeKey: false,
        allowEnterKey: false,
        type: 'warning',
        title: 'Cambio de estado',
        html: mensaje,
        confirmButtonText: 'Aceptar',
        showCancelButton: true,
        cancelButtonText: 'Cancelar',
        input: 'textarea',
        inputPlaceholder: 'Motivo por el cambio de estado...',
        preConfirm: () => {
            const inputValue = document.querySelector('.swal2-textarea').value;
            if (!inputValue) {
                Swal.showValidationMessage('Este campo es requerido');
                return false;
            }
            return inputValue;
        }
    };
    Swal.fire(swalOptions).then((result) => {
        if (result.dismiss !== Swal.DismissReason.cancel) {
            const inputValue = result.value !== undefined ? result.value : '';
            args = {'val': args, 'text':inputValue}
            sendAjaxCheckMain(obj, action, args, unico, id, data_class, check)
        } else {
            $.unblockUI();
            obj.prop('checked', !check);
        }
    })
}

function sendAjaxCheckMain(obj, action, args, unico, id, data_class, check) {
    $.ajax({
        type: "POST",
        url: request_path,
        data: {'action': action, 'id': id, 'val': check, 'args':args},
        success: function (data) {
            if (data.result === true) {
                $.unblockUI();
                alertaSuccess(data.mensaje)
                if (unico && check) {
                    $(`.${data_class}`).prop('checked', false)
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




// Permite inicializar la libreria switchery dinamicamente partiendo del argumento 'data-switchery': True en el formulario
function cargarSwitchs() {
    var elems = Array.prototype.slice.call(document.querySelectorAll('.js-switch'));
    if (elems.length > 0) {
        // Cargar el archivo CSS de Switchery
        let link = document.createElement('link');
        link.rel = 'stylesheet';
        link.type = 'text/css';
        link.href = '/static/switchery/switchery.min.css';
        document.head.appendChild(link);

        let script = document.createElement('script');
        script.src = '/static/switchery/switchery.min.js';
        script.onload = function () {

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
}

// Permite inicializar la libreria ckeditor dinamicamente partiendo de la clase ckeditors proporcionada en el formulario
function cargarCkeditor() {
    let ckeditorElements = document.querySelectorAll('.ckeditors');
    if (ckeditorElements.length > 0) {
        // Cargar js de ckeditors libreria
        // let script_init = document.createElement('script');
        // script_init.src = '/static/ckeditor/ckeditor-init.js?v=1.0.1';
        // document.head.appendChild(script_init);

        let script = document.createElement('script');
        script.src = '/static/ckeditor/ckeditor/ckeditor.js?v=1.0.1';
        script.onload = function () {
            ckeditorElements.forEach(function (element) {
                 // Destruir CKEditor existente si ya está inicializado
                if (CKEDITOR.instances[element.id]) {
                    CKEDITOR.instances[element.id].destroy(true);
                }
                let editor_sm=element.getAttribute('editor-sm')
                let ckeditorTxt = element.getAttribute('ckeditor-text')
                if (editor_sm){
                    var editor = CKEDITOR.replace(element, {toolbar: [
                                            {name: 'document', items: ['Source']}, // Oculta el botón de código fuente
                                            {name: 'clipboard', items: ['Undo', 'Redo']}, // Muestra solo los botones de deshacer y rehacer
                                            {
                                                name: 'basicstyles',
                                                items: ['Bold', 'Italic', 'Underline', 'Strike', 'JustifyLeft', 'JustifyCenter', 'JustifyRight', 'JustifyBlock']
                                            },
                                            { name: 'paragraph', items: ['NumberedList', 'BulletedList']}, // Agrega botones para listas numeradas y con viñetas
                                        ]});
                }else{
                    var editor = CKEDITOR.replace(element);
                }
                if (ckeditorTxt && !element.value) {
                    editor.setData(ckeditorTxt);
                }
                $("#submit").on('click', function () {
                    // Actualizar el valor del campo de entrada correspondiente
                    $('#' + element.id).val(editor.getData());
                });
                editor.on('blur', function () {
//                    console.log('blur')
                    // Actualizar el valor del campo de entrada correspondiente
                    $('#' + element.id).val(editor.getData());
                    let sendAjax = element.getAttribute('sendAjax')
                    if(sendAjax){
                        accionEjecutar($('#' + element.id))
                    }
                });
            });
        };
        document.head.appendChild(script);
    }
}
// Permite inicializar la libreria ckeditor dinamicamente partiendo de la clase ckeditors proporcionada en el formulario pero con uso de tablas
// Permite inicializar la libreria ckeditor dinamicamente partiendo de la clase ckeditors proporcionada en el formulario pero con uso de tablas
function cargarCkeditortable() {
    let ckeditorElements = document.querySelectorAll('.ckeditorstable');
    if (ckeditorElements.length > 0) {
        let script = document.createElement('script');
        script.src = '/static/ckeditor/ckeditor/ckeditor.js?v=1.0.1';
        script.onload = function () {
            ckeditorElements.forEach(function (element) {
                let config = {
                    extraPlugins: 'font,colorbutton,justify,image,clipboard,list,link,table,save,print,pastefromword,preview,find,maximize,forms', // Ensure these plugins are loaded
                    toolbar: [

                        {name: 'forms', items: []}, // Form elements
                        {name: 'basicstyles', items: ['Bold', 'Italic', 'Underline', 'Strike', 'Subscript']}, // Basic text styling
                        {name: 'paragraph', items: ['NumberedList', 'BulletedList', 'JustifyLeft', 'JustifyCenter', 'JustifyRight', 'JustifyBlock']}, // Paragraph formatting
                        {name: 'insert', items: ['Table']}, // Insert commands
                        {name: 'styles', items: ['Styles', 'Format', 'Font', 'FontSize']}, // Styles and formatting
                        {name: 'colors', items: ['TextColor', 'BGColor']}, // Color commands
                        {name: 'tools', items: ['Maximize']}, // Tools
                        {name: 'others', items: []} // Miscellaneous
                    ]
                };

                // Initialize CKEditor with the specified configuration
                var editor = CKEDITOR.replace(element, config);

                // Handle form submission
                $("#submit").on('click', function () {
                    $('#' + element.id).val(editor.getData());
                });

                // Handle blur event
                editor.on('blur', function () {
                    $('#' + element.id).val(editor.getData());
                });
            });
        };
        document.head.appendChild(script);
    }
}
// Permite mostrar un mensaje de confirmación con o sin cuadro de texto antes de realizar una acción. el campo de texto se retorna como "message"
function confirmsweetalertmessage(title, messageHtml, action, id, idx='',  urlDestiny = request_path,
                                  input = false, isObligatory = false, inputplaceholder = 'Escribe algo..', coloricon = 'warning') {
    const swalOptions = {
        allowOutsideClick: false,
        allowEscapeKey: false,
        allowEnterKey: false,
        type: coloricon,
        title: title,
        html: messageHtml,
        confirmButtonText: 'Aceptar',
        showCancelButton: true,
        cancelButtonText: 'Cancelar',
        preConfirm: () => {
            if (input) {
                const inputValue = document.querySelector('.swal2-textarea').value;
                if (isObligatory && !inputValue) {
                    Swal.showValidationMessage('Este campo es requerido');
                    return false;
                }
                return inputValue;
            }
        }
    };

    if (input) {
        swalOptions.input = 'textarea';
        swalOptions.inputPlaceholder = inputplaceholder;
    }

    Swal.fire(swalOptions).then((result) => {
        if (result.dismiss !== Swal.DismissReason.cancel) {
            const inputValue = result.value !== undefined ? result.value : '';
            bloqueointerface();
            $.ajax({
                type: "POST",
                url: urlDestiny,
                data: {
                    action: action,
                    id: id,
                    idx: idx,
                    message: inputValue,
                },
                success: function (data) {
                    $.unblockUI();
                    if (data.result === 'ok') {
                        if (data.mensaje) {
                            mensajeSuccessSwal(data.titulo, data.mensaje, urlDestiny);
                        } else {
                            location.href = urlDestiny;
                        }
                    } else {
                        if (data.swalType === 'warning') {
                            mensajeWarningSwal(data.titulo, data.mensaje);
                        } else {
                            mensajeErrorSwal(data.titulo, data.mensaje);
                        }
                    }
                },
                error: function () {
                    $.unblockUI();
                    mensajeErrorSwal("No se puede procesar", "Error al enviar los datos");
                },
                dataType: "json"
            });
        } else {
            console.log('Operación cancelada por el usuario');
        }
    });
}
