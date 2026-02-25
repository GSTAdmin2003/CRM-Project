def debug_mode(request):
    """
    Debug mode is active only when ?debug=1 is present in the current URL.
    No session storage — each page must carry the param explicitly.
    """
    return {'debug_mode': request.GET.get('debug') == '1'}
