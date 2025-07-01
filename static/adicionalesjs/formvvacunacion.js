const _urlvac = window.location.toString().split(window.location.host.toString())[1];
const _cargando = '<i class="fa fa-cog fa-spin" role="status" aria-hidden="true"></i>';
const __method_req___ = "POST";
const _enc = $('*[data-datoseguro=true]').toArray();
const headerId = '#header';
var __enc = [];
for (var i = 0; i < _enc.length; i++) {
    __enc.push($(_enc[i]).attr('name'));
}
const __inputsEncrypted__ = __enc.join('|');
$(function () {
    $('.formModalclass').submit(function (e) {
        e.preventDefault();
        const formulario = $(this);
        const btnSubmit = $('#submit,#submit2,#submit3');
        const error_btn = btnSubmit.html();
        $('input').removeClass('is-invalid');
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
        const listInputsEnc = __inputsEncrypted__.split('|');
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
            type: __method_req___,
            url: _urlvac,
            data: _form,
            dataType: "json",
            enctype: formulario.attr('enctype'),
            cache: false,
            contentType: false,
            processData: false,
            beforeSend: function () {
                btnSubmit.html(_cargando);
                btnSubmit.attr("disabled", true);
                bloqueointerface();
            }
        }).done(function (data) {
            if (!data.result) {
                if (data.to) {
                    location = data.to;
                } else {
                    location.reload();
                }
            } else {
                smoke.alert(data.mensaje);
                btnSubmit.html(error_btn);
                btnSubmit.attr("disabled", false);
                $.unblockUI();
            }
        }).fail(function (jqXHR, textStatus, errorThrown) {
            smoke.alert('Intentelo más tarde');
            btnSubmit.html(error_btn);
            btnSubmit.attr("disabled", false);
            $.unblockUI();
        }).always(function () {

        });
    });
});

