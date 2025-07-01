const _url2 = window.location.toString().split(window.location.host.toString())[1];
const cargando2 = '<i class="fa fa-cog fa-spin" role="status" aria-hidden="true"></i>';
const error_btn3 = '<i class="fa fa-check-circle" role="status" aria-hidden="true"></i> Guardar';
const method_req2 = "POST";
const _enc2 = $('*[data-datoseguro=true]').toArray();
const _headerId2 = '#header';
var __enc2 = [];
for (var i = 0; i < _enc2.length; i++) {
    __enc2.push($(_enc2[i]).attr('name'));
}
const _inputsEncrypted2 = __enc2.join('|');
$(function () {
    $('.modaldatospanel').submit(function (e) {
        e.preventDefault();
        const formulario = $(this);
        const btnSubmit = $('#submit,#submit2,#submit3');
        const error_btn = btnSubmit.html();
        $('input, textarea, select').removeClass('is-invalid');
        const pk = formulario.find('input[name=pk]').length ? parseInt(formulario.find('input[name=pk]').val()) : 0;
        const action = formulario.find('input[name=action]').length ? formulario.find('input[name=action]').val() : false;
        var _form = new FormData(formulario[0]);
        if (pk !== 0) {
            if (_form.has('pk')) {
                _form.set('pk', pk.toString());
            } else {
                _form.append('pk', pk.toString());
            }

        }
        if (action !== false) {
            if (_form.has('action')) {
                _form.set('action', action);
            } else {
                _form.append('action', action);
            }
        }
        const listInputsEnc = _inputsEncrypted2.split('|');
        for (var i = 0; i < listInputsEnc.length; i++) {
            if (_form.has(listInputsEnc[i])) {
                _form.set(listInputsEnc[i], doRSA(_form.get(listInputsEnc[i])));
            }
        }
        try {
            _form.append("lista_items1", JSON.stringify(lista_items1));
        } catch (err) {
            console.log(err.message);
        }

        $.ajax({
            type: method_req2,
            url: _url2,
            data: _form,
            dataType: "json",
            enctype: formulario.attr('enctype'),
            cache: false,
            contentType: false,
            processData: false,
            beforeSend: function () {
                btnSubmit.html(cargando2);
                btnSubmit.attr("disabled", true);
                bloqueointerface();
            }
        }).done(function (data) {
            if (!data.result) {
                $('.modal').modal('hide');
                if (data.to) {
                    if (data.modalsuccess) {
                        $.unblockUI();
                        Swal.fire({
                            title: data.mensaje,
                            text: '',
                            type: 'success',
                            showCancelButton: false,
                            allowOutsideClick: false,
                            confirmButtonColor: '#3085d6',
                            confirmButtonText: 'Ok'
                        }).then((result) => {
                            if (result.value) {
                                location = data.to;
                            }
                        })
                    } else {
                        location = data.to;
                    }
                } else {
                    if (data.modalsuccess) {
                        $.unblockUI();
                        Swal.fire({
                            title: data.mensaje,
                            text: '',
                            type: 'success',
                            showCancelButton: false,
                            allowOutsideClick: false,
                            confirmButtonColor: '#3085d6',
                            confirmButtonText: 'Ok'
                        }).then((result) => {
                            if (result.value) {
                                location.reload();
                            }
                        })
                    } else {
                        location.reload();
                    }

                }
            } else {

                if (data.form) {
                    data.form.forEach(function (val, indx) {
                        var keys = Object.keys(val);
                        keys.forEach(function (val1, indx1) {
                            $("#id_" + val1).addClass("is-invalid");
                            $("#errorMessage" + val1).html(val[val1]);
                        });
                    });
                }

                smoke.alert(data.mensaje);
                btnSubmit.html(error_btn3);
                btnSubmit.attr("disabled", false);
                $.unblockUI();
            }
        }).fail(function (jqXHR, textStatus, errorThrown) {
            btnSubmit.html(error_btn3);
            btnSubmit.attr("disabled", false);
            $.unblockUI();
        }).always(function () {

        });
    });
});

