// detection.js
function calculateEAR(eye) {
    const A = Math.hypot(eye[1].x - eye[5].x, eye[1].y - eye[5].y);
    const B = Math.hypot(eye[2].x - eye[4].x, eye[2].y - eye[4].y);
    const C = Math.hypot(eye[0].x - eye[3].x, eye[0].y - eye[3].y);
    return (A + B) / (2.0 * C);
}


function detectLeftMovement(noseX) {
    const leftThreshold = 0.60; // Incrementar el umbral para evitar falsos positivos
    return noseX > leftThreshold;
}

function detectRightMovement(noseX) {
    // Ajustado para detectar la derecha del usuario (que es la izquierda en la cámara)
    return noseX < 0.45; // Ajusta el umbral si es necesario
}

function detectSmile(mouthLeftX, mouthRightX) {
    const mouthWidth = Math.abs(mouthRightX - mouthLeftX);
    return mouthWidth > 0.10;  // 0.12 umbral de sonrisa bien grande | 0.10 umbral de sonrisa leve
}

function detectBlink(leftEAR, rightEAR) {
    leftEAR = calculateEAR(leftEAR);
    rightEAR = calculateEAR(rightEAR);
    return (leftEAR < 0.2 || rightEAR < 0.2);  // Detecta si a parpadeado
}

function detectSerious(mouthLeftX, mouthRightX) {
    const mouthWidth = Math.abs(mouthRightX - mouthLeftX);
    return mouthWidth < 0.9; // Umbral ajustado para detectar una cara seria
}


function detectHeadUp(noseY, chinY) {
    // Si el mentón está significativamente más abajo que la nariz, se considera que la cabeza está inclinada hacia arriba.
    return chinY > noseY + 0.2;  // Ajusta este umbral según los valores reales obtenidos
}

function detectHeadDown(noseY, chinY) {
    const threshold = 0.18; // Umbral ajustado basado en los datos observados
    return (chinY - noseY) > threshold; // Detecta si el mentón está significativamente más abajo que la nariz
}

function detectMouthOpen(mouthTopY, mouthBottomY) {
    return Math.abs(mouthBottomY - mouthTopY) > 0.03; // Detecta si la boca está abierta
}

function detectTiltLeft(noseX, chinX) {
    const tiltThreshold = 0.05; // Ajusta este umbral según sea necesario
    return (noseX - chinX) > tiltThreshold;
}

function detectTiltRight(noseX, chinX) {
     const tiltThreshold = 0.05; // Ajusta este umbral según sea necesario
    return (chinX - noseX) > tiltThreshold;
}


function captureInitialBrowDistance(landmarks) {
    const browLeftX = landmarks[70].x;
    const browRightX = landmarks[107].x;
    return Math.abs(browRightX - browLeftX);
}



//Secuencia para movimientos de la cabeza y expresiones faciales
let sequence = [];
let currentStep = 0;

function generateSequence() {
    const movements = [
//        'left',
//        'right',
        'smile',
        'blink',
//        'serious',
//        'headUp',
        'tiltLeft',
        'tiltRight',
//        'mouthOpen',
    ];

    sequence = [];
    for (let i = 0; i < 1; i++) {  // Puedes ajustar este número para generar más o menos pasos
        const randomIndex = Math.floor(Math.random() * movements.length);
        sequence.push(movements[randomIndex]);
    }
    console.log("Secuencia generada:", sequence);
    updateInstructions();
}

function updateInstructions() {
    const instructions = {
//    'left': 'Mueve la cabeza a la izquierda',
//    'right': 'Mueve la cabeza a la derecha',
    'smile': 'Sonríe',
    'blink': 'Parpadea',
//    'serious': 'Pon una cara seria',
//    'headUp': 'Mueve la cabeza hacia arriba',
    'tiltLeft': 'Inclina la cabeza hacia la izquierda',
    'tiltRight': 'Inclina la cabeza hacia la derecha',
//    'mouthOpen': 'Abre la boca',
    };

    if (currentStep < sequence.length) {
    document.getElementById('instructions').innerText = `${instructions[sequence[currentStep]]}`;
    } else {
    document.getElementById('result').innerText = 'Prueba de vida completada con éxito';
    }
}

function resetSequence() {
    currentStep = 0;
    generateSequence();
    updateInstructions();
}