from django import template

register = template.Library()


@register.filter
def mmss(seconds):
    """132.4 -> '2:12'"""
    total = int(seconds or 0)
    return f"{total // 60}:{total % 60:02d}"
