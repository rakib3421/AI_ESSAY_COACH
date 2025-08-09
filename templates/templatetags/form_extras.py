from django import template

register = template.Library()

@register.filter
def add_class(field, css):
    """Add a CSS class to a form field widget in templates."""
    existing = field.field.widget.attrs.get('class', '')
    classes = f"{existing} {css}".strip()
    field.field.widget.attrs['class'] = classes
    return field
