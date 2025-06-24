from django import template
from urllib.parse import urlencode

register = template.Library()

@register.simple_tag
def querystring(current_querydict, **new_params):
    query = current_querydict.copy()
    for k, v in new_params.items():
        if v is None:
            query.pop(k, None)
        else:
            query[k] = v
    return urlencode(query)


