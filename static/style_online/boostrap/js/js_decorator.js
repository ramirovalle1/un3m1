function activasubtema(codigosubtema){
	$('.active').removeClass('active');
	$('#lisub'+codigosubtema).addClass('active');
	$(".ocultadiv").hide();
	$("#sub"+codigosubtema).show();
}
function activalectura(codigolectura){
	$('.active').removeClass('active');
	$('#lilec'+codigolectura).addClass('active');
	$(".ocultadiv").hide();
	$("#lec"+codigolectura).show();
}
function activaexperiencia(codigoexperiencia){
	$('.active').removeClass('active');
	$('#liexp'+codigoexperiencia).addClass('active');
	$(".ocultadiv").hide();
	$("#exp"+codigoexperiencia).show();
}
function activamasrecursos(codigorecurso){
	$('.active').removeClass('active');
	$('#lirec'+codigorecurso).addClass('active');
	$(".ocultadiv").hide();
	$("#rec"+codigorecurso).show();
}
function activatema(){
	$(".ocultadiv").hide();
	$("#tem").show();
}