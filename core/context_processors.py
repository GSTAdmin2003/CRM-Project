def debug_mode(request):
    """
    Persist debug mode via session.
    Activate with ?debug=1, deactivate with ?debug=0.
    """
    if 'debug' in request.GET:
        if request.GET['debug'] == '1':
            request.session['debug_mode'] = True
        else:
            request.session.pop('debug_mode', None)

    return {'debug_mode': request.session.get('debug_mode', False)}
