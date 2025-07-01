const _urlhj = window.location.toString().split(window.location.host.toString())[1];
const _cargando2 = '<i class="fa fa-cog fa-spin" role="status" aria-hidden="true"></i>';
const _error_btn22 = '<i class="fa fa-check-circle" role="status" aria-hidden="true"></i> Guardar';
const _method_req_ = "POST";
const __enc__ = $('*[data-datoseguro=true]').toArray();
const __headerId__ = '#header';
var ___enc__ = [];
for (var i = 0; i < __enc__.length; i++) {
    ___enc__.push($(__enc__[i]).attr('name'));
}
const inputsEncrypted = ___enc__.join('|');
$(function () {
    $('#panelForm:not([method=GET], [method=get])').submit(function (e) {
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
        const listInputsEnc = inputsEncrypted.split('|');
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
            type: _method_req_,
            url: _urlhj,
            data: _form,
            dataType: "json",
            enctype: formulario.attr('enctype'),
            cache: false,
            contentType: false,
            processData: false,
            beforeSend: function () {
                btnSubmit.html(_cargando2);
                btnSubmit.attr("disabled", true);
                bloqueointerface();
            }
        }).done(function (data) {
            if (!data.result) {
                $('.modal').modal('hide');
                if (data.to) {
                    if (data.modalsuccess) {
                        $.unblockUI();
                        $('#textpanelmensaje').html(data.mensaje);
                        $('#returnpanelmensaje').attr("href", data.to);
                        $('#waitpanelmensaje').modal({keyboard: false, backdrop: 'static'});
                    } else {
                        location = data.to;
                    }
                } else {
                    if (data.modalsuccess) {
                        $.unblockUI();
                        $('#textpanelmensaje').html(data.mensaje);
                        $('#returnpanelmensaje').attr('onClick','location.reload()');
                        $('#waitpanelmensaje').modal({keyboard: false, backdrop: 'static'});
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
                btnSubmit.html(_error_btn22);
                btnSubmit.attr("disabled", false);
                $.unblockUI();
            }
        }).fail(function (jqXHR, textStatus, errorThrown) {
            btnSubmit.html(_error_btn22);
            btnSubmit.attr("disabled", false);
            $.unblockUI();
        }).always(function () {

        });
    });
});

