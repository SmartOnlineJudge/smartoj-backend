import json

from fastapi.responses import HTMLResponse
from fastapi.openapi.docs import swagger_ui_default_parameters
from fastapi.encoders import jsonable_encoder

import settings


def custom_swagger_ui_html(
    *,
    openapi_url: str,
    title: str,
    swagger_js_url: str = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
    swagger_css_url: str = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    swagger_favicon_url: str = None,
    oauth2_redirect_url: str = None,
    init_oauth=None,
    swagger_ui_parameters=None,
) -> HTMLResponse:
    if swagger_favicon_url is None:
        swagger_favicon_url = settings.API_DOCS_LOGO or "https://fastapi.tiangolo.com/img/favicon.png"

    current_swagger_ui_parameters = swagger_ui_default_parameters.copy()
    if swagger_ui_parameters:
        current_swagger_ui_parameters.update(swagger_ui_parameters)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <link type="text/css" rel="stylesheet" href="{swagger_css_url}">
    <link rel="shortcut icon" href="{swagger_favicon_url}">
    <title>{title}</title>
    </head>
    <body>
    <div id="swagger-ui">
    </div>
    <script src="{swagger_js_url}"></script>
    <!-- `SwaggerUIBundle` is now available on the page -->
    <script>
    const ui = SwaggerUIBundle({{
        url: '{openapi_url}',
        // 请求拦截器，在 Cookie 中设置 session_id。
        requestInterceptor: request => {{ 
            if (!document.cookie.includes('session_id')) {{
                const authorization = JSON.parse(localStorage.getItem('authorized'));
                if (authorization && authorization.APIKeyCookie && authorization.APIKeyCookie.value) {{
                    document.cookie += 'session_id=' + authorization.APIKeyCookie.value + ';';
                }}
            }}
            return request; 
        }},
    """

    for key, value in current_swagger_ui_parameters.items():
        html += f"{json.dumps(key)}: {json.dumps(jsonable_encoder(value))},\n"

    if oauth2_redirect_url:
        html += f"oauth2RedirectUrl: window.location.origin + '{oauth2_redirect_url}',"

    html += """
    presets: [
        SwaggerUIBundle.presets.apis,
        SwaggerUIBundle.SwaggerUIStandalonePreset
        ],
    })"""

    if init_oauth:
        html += f"""
        ui.initOAuth({json.dumps(jsonable_encoder(init_oauth))})
        """

    html += """
    </script>
    </body>
    </html>
    """
    return HTMLResponse(html)
