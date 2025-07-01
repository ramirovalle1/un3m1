importScripts('static/js/sw-utils.js');

const CACHE_NAME = 'UNEMI-v1.0';
const OFFLINE_VERSION = 1;
const CACHE_OFFLINE_URL = 'offline';
const CACHE_INMUTABLE_NAME = 'UNEMI-INMUTABLE-v1.0';
//const CACHE_STATIC_NAME = 'SGA-STATIC-v1.0';
//const CACHE_DYNAMIC_NAME = 'SGA-DYNAMIC-v1.0';

const APP_SHELL_OFFLINE = [
    // Al definir {cache: 'reload'} en la nueva consulta asegurara que la
    // respuesta no sea desde el caché de HTTP; i.e., esta será
    // de la red.
    new Request(CACHE_OFFLINE_URL, {cache: 'reload'}),
];

const LIST_CACHE = [
    CACHE_NAME,
    CACHE_INMUTABLE_NAME,
]

/*const APP_SHELL = [
    'static/images/aok/favicon32X32.ico',
    'static/css/stylesbs.css',
];

const APP_SHELL_INMUTABLE = [
    'static/sweet2/sweetalert2.css',
    'static/sweet2/sweetalert2.js',
    'static/js/jquery.min.js',
    'static/js/jquery.blockUI.js',
    'static/js/jquery.maskedinput.min.js',
    'static/js/sysend.js',
    'static/js/smoke.js',
    'static/js/bs/bootstrap.min.js',
    'static/js/bootstrap-timepicker.js',
    'static/js/bootstrap-modal.js',
    'static/js/bootstrap-modalmanager.js',
    'static/js/big.min.js',
    'static/js/jquery.flexbox.js',
    'static/js/dragdivscroll.js',
    'static/js/jquery.dataTables.min.js',
    'static/css/smoke.css',
    'static/css/bootstrap.min.css',
    'static/css/bootstrap-responsive.css',
    'static/css/font-awesome.css',
    'static/css/font-awesome.min.css',
    'static/css/datepicker.css',
    'static/css/bootstrap-timepicker.css',
    'static/css/bootstrap-modal.css',
    'static/css/jquery.flexbox.css',
    'static/css/jquery.dataTables.css',
    'static/js/select2.js',
    'static/css/select2.css',
    'static/js/snow.js',
    '/static/jgrowl/jgrowl.css',
    '/static/jgrowl/jgrowl.min.js',
];*/

self.addEventListener('install', e => {
    /*const cacheStatic = caches.open( CACHE_STATIC_NAME ).then(cache =>
        cache.addAll( APP_SHELL ));

    const cacheInmutable = caches.open( CACHE_INMUTABLE_NAME ).then(cache =>
        cache.addAll( APP_SHELL_INMUTABLE ));
    e.waitUntil( Promise.all([ cacheStatic, cacheInmutable ])  );*/
    e.waitUntil((async () => {
        const cacheInmutableOffLine = await caches.open(CACHE_INMUTABLE_NAME);

        await cacheInmutableOffLine.addAll( APP_SHELL_OFFLINE );
    })());
    // Obliga al service worker que espera a que se convierta en uno activo.
    self.skipWaiting();
});

addEventListener('activate', function (event) {
    var refresh = false;
    event.waitUntil(
        (async () => {
            // Permite la navegación precargada si tiene compatibilidad
            // Mira https://developers.google.com/web/updates/2017/02/navigation-preload
            if ("navigationPreload" in self.registration) {
                await self.registration.navigationPreload.enable();
            }
            caches.keys().then(function (keyList) {
                return Promise.all(keyList.map(function (key) {
                    //console.log(`key (${key}) inclye en LIST CACHE: `,LIST_CACHE.includes(key));
                    if (!LIST_CACHE.includes(key)) {
                        refresh = true;
                        caches.delete(key);
                    }
                })).then(async function () {
                    if (refresh) {
                        var clientes = await clients.matchAll({includeUncontrolled: true, type: 'window'});
                        for (const client of clientes) {
                            client.postMessage('refresh');
                        }
                    }
                });
            })
        })()
    );
    // Le dice al service worker activo que tome el control inmediato de la página.
    self.clients.claim();

});

addEventListener('push', async function (event) {
    const eventInfo = event.data.text();
    const data = JSON.parse(eventInfo);
    const head = data.head;
    const body = data.body;

    var clientes = await clients.matchAll({includeUncontrolled: true, type: 'window'});
    for (const client of clientes) {
        client.postMessage(data);
    }

    var DATANOT = {
        body: body,
        icon: "/static/pwalogo/512x512.png",
        badge: "/static/pwalogo/badge.png",
        vibrate: [500, 110, 500, 500, 110, 500],
        data: {url: data.url ? data.url : ''},
        actions: [{action: "open_url", title: "Ver ahora"}],
        requireInteraction: true
    };
    self.registration.showNotification(head, DATANOT);
});

self.onmessage = async function (event) {
    if (event.data && event.data.type === 'PORT_INITIALIZATION') {
        //port = event.ports[0];
    } else if (event.data && event.data.type) {
        var clientes = await clients.matchAll({includeUncontrolled: true, type: 'window'});
        for (const client of clientes) {
            client.postMessage(event.data.type);
        }
    }
}

addEventListener('notificationclick', function (event) {
    switch (event.action) {
        case 'open_url':
            if (event.notification.data.url) {
                clients.openWindow(event.notification.data.url); //which we got from above
            }
            break;
    }
}, false);

addEventListener( 'fetch', e => {
    // var origin = self.location.origin;
    // if (event.request.url.startsWith(origin + '/logout/')) {
    //     return;
    // }
    // event.respondWith(
    //     fetch(event.request)
    //         .then((result) => {
    //             return caches.open(CACHE_NAME)
    //                 .then(function (c) {
    //                     if (event.request.url.indexOf('http') === 0 && event.request.method === 'GET') {
    //                         if (event.request.url.startsWith(origin + '/static/') ||
    //                             event.request.url.startsWith(origin + '/media/') ||
    //                             event.request.url.indexOf('cdn.datatables') >= 0 ||
    //                             event.request.url.indexOf('maps.googleapis') >= 0 ||
    //                             event.request.url.indexOf('fonts.googleapis')) {
    //                             // c.put(event.request.url, result.clone());
    //                         }
    //                     }
    //                     return result;
    //                 })
    //         })
    //         .catch(function (e) {
    //             return caches.match(event.request).then(function (response) {
    //                 return response || caches.match("/offline-view/");
    //             });
    //         })
    // );
    const origin = self.location.origin;
    const static = `${origin}/static/`;
    const media = `${origin}/media/`;
    //console.log("origin:", origin);
    if (e.request.url.indexOf(static) != -1 || e.request.url.indexOf(media) != -1){
        //console.log("static:", static);
        //console.log("media:", media);
        const respuesta = caches.match( e.request ).then( res => {
            if ( res ) {
                return res;
            } else {

                return fetch( e.request ).then( newRes => {
                    //console.log(e);
                    return actualizaCacheDinamico( CACHE_NAME, e.request, newRes );

                });

            }

        });

    }
    else if (e.request.url.indexOf('offline') != -1){
        const respuesta = caches.match( e.request ).then( res => {
            if ( res ) {
                return res;
            } else {

                return fetch( e.request ).then( newRes => {
                    //console.log(e);
                    return actualizaCacheDinamico( CACHE_INMUTABLE_NAME, e.request, newRes );

                });

            }

        });
    }
    if (e.request.mode === "navigate") {
        e.respondWith(
            (async () => {
                try {
                    // Primero, utiliza una respuesta de precarga de navegación.
                    const preloadResponse = await e.preloadResponse;
                    console.log("preloadResponse: ", preloadResponse);
                    if (preloadResponse) {
                        return preloadResponse;
                    }

                    // Siempre usa la red primero.
                    const networkResponse = await fetch(e.request);
                    return networkResponse;
                } catch (error) {
                    // El catch solo se dispara cuando se obtiene una excepción
                    // gracias a un error en la red.
                    // Si fetch() regresa una respuesta HTTP valida con un codigo de respuesta en el
                    // rango de 4xx o 5xx, el catch() no se llamará
                    console.log("Fetch failed; returning offline page instead.", error);

                    const cache = await caches.open(CACHE_INMUTABLE_NAME);
                    const cachedResponse = await cache.match(CACHE_OFFLINE_URL);
                    return cachedResponse;
                }
            })()
        );
    }


});
