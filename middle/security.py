

class IPFilterMiddleware(object):

    def process_request(self, request):
        remoteaddr = request.META['REMOTE_ADDR']
        return remoteaddr