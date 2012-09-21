from django import template
import re


def form_error(value):
    """
    Formats form error
    """
    error_text = ""
    if value:
        #value = re.sub(r'[\[\]\'\.]', '', value)
        for error_string in value:
            error_text = '<div class="form-error">%s</div>' % error_string
    return error_text

register = template.Library()
register.filter('form_error', form_error)
