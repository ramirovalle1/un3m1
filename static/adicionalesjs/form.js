const _url = window.location.toString().split(window.location.host.toString())[1];
const cargando = '<i class="fa fa-cog fa-spin" role="status" aria-hidden="true"></i>';
const method_req = "POST";
const _enc = $('*[data-datoseguro=true]').toArray();
const headerId = '#header';
var __enc = [];
for (var i = 0; i < _enc.length; i++) {
    __enc.push($(_enc[i]).attr('name'));
}
const inputsEncrypted = __enc.join('|');
$(function () {
    $('form:not(#frmBuscarGET, #frmEliminar, #frmEliminar1,  #frmEliminar2, #frmVisita, #frmVisible, #frmEliPrg, #frmRespuesta, #frmGestion, #frmReactivar, #frmEliminarConComentario, #frmQuitarBestseller, #frmHacerBestseller, #frmActivarProducto, [method=GET], [method=get])').submit(function (e) {
        e.preventDefault();
        const formulario = $(this)
        const btnSubmit = $('#submit,#submit2,#submit3');
        const error_btn = btnSubmit.html();
        $('input').removeClass('is-invalid');
        const pk = $(this).find('input[name=pk]').length ? parseInt($(this).find('input[name=pk]').val()) : 0;
        const action = $(this).find('input[name=action]').length ? $(this).find('input[name=action]').val() : false;
        var _form = new FormData($(this)[0]);
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
        $.ajax({
            type: method_req,
            url: _url,
            data: _form,
            dataType: "json",
            enctype: $(this).attr('enctype'),
            cache: false,
            contentType: false,
            processData: false,
            beforeSend: function () {
                btnSubmit.html(cargando);
                btnSubmit.attr("disabled", true);
                bloqueointerface();
            }
        }).done(function (data) {
            if (!data.result) {
                if (data.to) {
                    location = data.to;
                } else {
                    $('.modal').modal('hide')
                    smoke.alert(data.mensaje)
                }
            } else {
                smoke.alert(data.mensaje);
            }
            btnSubmit.html(error_btn);
            btnSubmit.attr("disabled", false);
            $.unblockUI();
        }).fail(function (jqXHR, textStatus, errorThrown) {
            smoke.alert('Error en el servidor');
            btnSubmit.html(error_btn);
            btnSubmit.attr("disabled", false);
            $.unblockUI();
        }).always(function () {

        });
    });
});