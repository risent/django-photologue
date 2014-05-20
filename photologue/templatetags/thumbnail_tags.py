#-*-coding:utf-8 -*-
#from photologue.models import 
from django import template
from django.utils.encoding import smart_str, force_unicode
from django.utils.html import escape
from django.utils.safestring import mark_safe

from .compat import parse_bits

register = template.Library()


ASSIGNMENT_DELIMETER = 'as'
HTML_ATTRS_DELIMITER = '--'


@register.simple_tag
def thumbnail_url(img, width, height, crop, **kwargs):
    return img._get_custom_url(**{'width':width, 'height':height, 'crop':crop})


@register.simple_tag
def simple_thumbnail(img, width, height, crop, alt=''):
    if crop not in ['center', 'top', 'bottom', 'left', 'right', 'fill', 'null']:
        return None

    url = img._get_custom_url(int(width), int(height), crop)
    result =  '''<img src="%s"  width="%s" height="%s" alt="%s" ''' % (url, width, height, smart_str(alt))

    # for k,v in kwargs.iteritems():
    #     result += ' %s="%s"' % (k, v)

    result += '/>'

    return result



def parse_thumb_tag_bits(parser, bits):
    """
    Parses the tag name, html attributes and variable name (for assignment tags)
    from the provided bits. The preceding bits may vary and are left to be
    parsed by specific tags.

    """
    varname = None
    html_attrs = {}
    tag_name = bits.pop(0)

    if len(bits) >= 2 and bits[-2] == ASSIGNMENT_DELIMETER:
        varname = bits[-1]
        bits = bits[:-2]

    if HTML_ATTRS_DELIMITER in bits:

        if varname:
            raise template.TemplateSyntaxError('Do not specify html attributes'
                    ' (using "%s") when using the "%s" tag as an assignment'
                    ' tag.' % (HTML_ATTRS_DELIMITER, tag_name))

        index = bits.index(HTML_ATTRS_DELIMITER)
        html_bits = bits[index + 1:]
        bits = bits[:index]

        if not html_bits:
            raise template.TemplateSyntaxError('Don\'t use "%s" unless you\'re'
                ' setting html attributes.' % HTML_ATTRS_DELIMITER)

        args, html_attrs = parse_bits(parser, html_bits, [], 'args',
                'kwargs', None, False, tag_name)
        if len(args):
            raise template.TemplateSyntaxError('All "%s" tag arguments after'
                    ' the "%s" token must be named.' % (tag_name,
                    HTML_ATTRS_DELIMITER))

    return (tag_name, bits, html_attrs, varname)



class ThumbnailImageTagNode(template.Node):

    def __init__(self, img, dimensions, generator_kwargs, html_attrs):
        self._dimensions = dimensions
        self._img = img
        self._generator_kwargs = generator_kwargs
        self._html_attrs = html_attrs

    def render(self, context):
        img_obj = self._img.resolve(context)
        if img_obj is None:
            return ""

        width, height = [d.strip() or None for d in self._dimensions.resolve(context).split('x')]
        # dimensions = parse_dimensions(self._dimensions.resolve(context))
        kwargs = dict((k, v.resolve(context)) for k, v in
                self._generator_kwargs.items())

        kwargs['width'] = int(width)
        kwargs['height'] = int(height)
        # generator = generator_registry.get(generator_id, **kwargs)

        # file = ImageCacheFile(generator)

        attrs = dict((k, v.resolve(context)) for k, v in
                self._html_attrs.items())
        attrs['src'] = img_obj._get_custom_url(**kwargs)

        # Rewrite the height and width from the html_attr
        if not 'width' in attrs and not 'height' in attrs:
            attrs.update(width=width, height=height)
        attr_str = ' '.join('%s="%s"' % (escape(k), escape(v)) for k, v in
                attrs.items())
        return mark_safe(u'<img %s />' % attr_str)


def thumbnail(parser, token):
    """
    {% thumbnail img '100x100'  crop='center' -- alt='Hello Crop Thumbnail' %}
    """
    bits = token.split_contents()
    tag_name, bits, html_attrs, varname = parse_thumb_tag_bits(parser, bits)

    args, kwargs = parse_bits(parser, bits, [], 'args', 'kwargs', None, False, tag_name)

    if len(args) < 2:
        raise template.TemplateSyntaxError('The "%s" tag requires at least two'
                ' unnamed arguments: the dimensions and the source image.'
                % tag_name)
    elif len(args) > 3:
        raise template.TemplateSyntaxError('The "%s" tag accepts at most three'
                ' unnamed arguments: a generator id, the dimensions, and the'
                ' source image.' % tag_name)
    img, dimensions = args[-2:]

    if varname:
        return None
    else:
        return ThumbnailImageTagNode(img, dimensions, kwargs, html_attrs)
        
thumbnail = register.tag(thumbnail)
