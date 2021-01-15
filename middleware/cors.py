"""
Small middleware to allow cross-origin resource sharing. Should only be enabled
in a local development environment.
"""

class CorsMiddleware(object):
    def process_response(self, req, resp):
        resp["Access-Control-Allow-Origin"] = "*"
        resp["Access-Control-Allow-Headers"] = "*"
        return resp
