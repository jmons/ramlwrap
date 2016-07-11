
from rest_framework.response import Response

def version(request):
    """
    a version api
    """

    # take client_key_ref for return in dict
    # ifthere was data, it would be in this now: (its json loaded)
    # x  = request.validated_data['something']

    reply = {
        "version": "jt-testone"
    }

    return Response(reply)