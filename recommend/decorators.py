from django.http import HttpResponseRedirect

def secure_required(view_func):
    def _wrapped_view_func(request, *args, **kwargs):
        if request:
            if not request.is_secure():
                request_url = request.build_absolute_uri(request.get_full_path())
                secure_url = request_url.replace('http://', 'https://')
                return HttpResponseRedirect(secure_url)
            return view_func(request, *args, **kwargs)
        else:
            return view_func(request, *args, **kwargs)
    return _wrapped_view_func
