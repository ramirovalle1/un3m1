from rest_framework.response import Response


class Helper_Response(Response):
    def __init__(self,
                 token=False,
                 redirect=None,
                 module_access=True,
                 data=None,
                 status=None,
                 isSuccess=False,
                 message=None,
                 template_name=None,
                 headers=None,
                 exception=False,
                 content_type=None):
        if not isSuccess and not message:
            message = "Ocurrio un error!"
        aData = {
            'data': data,
            'module_access': module_access,
            'message': message,
            'isSuccess': isSuccess,
            'redirect': redirect,
            'token': token,
            'info': {
                'api': "API UNEMI",
                'version': "2.0",
            }
        }
        super(Helper_Response, self).__init__(data=aData,
                                              status=status,
                                              template_name=template_name,
                                              headers=headers,
                                              exception=exception,
                                              content_type=content_type)
