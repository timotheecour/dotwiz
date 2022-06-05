"""Main module."""
import keyword
import re

from .common import __convert_to_dict__, __resolve_value__


# Credits: https://stackoverflow.com/a/46493824/10237506
#
# Known bug: it doesn't handle cases like `H@llo` or `WhaTSuP!` very well;
# though the lower cased versions are OK.
__SPECIAL_CASE_RE = re.compile(
    r'\d[A-Z]+|[A-Z]?[a-z\d]+|[A-Z]{2,}(?=[A-Z][a-z]|\d|\W|$)|\d+|[A-Z]{2,}|[A-Z]'
)

# A running cache of special cases that we've transformed based on above.
__SPECIAL_KEYS = {}

__DIGIT_MAP = {'0': 'o', '1': 'i', '2': 'z', '3': 'e', '4': 'o', '5': 's',
               '6': 's', '7': 'z', '8': 'b', '9': 'n'}


def to_snake_case(string, *, __get=__DIGIT_MAP.get, __default='x'):
    """
    Make an underscored, lowercase form from the expression in the string.
    Example::
        >>> to_snake_case("DeviceType")
        'device_type'
    """
    words = __SPECIAL_CASE_RE.findall(string)

    # note: this definitely does slow down performance, but here we need to
    # check for words with a leading digit such as `123test` - since these
    # are not valid identifiers in python, unfortunately.
    words = [w if not w[0].isdigit() else f'{__get(w[0], __default)}{w[1:]}'
             for w in words]

    return '_'.join(words).lower()


def make_dot_wiz_plus(*args, **kwargs):
    """
    Helper function to create and return a :class:`DotWizPlus` (dot-access dict)
    from an optional *iterable* object and *keyword* arguments.

    Example::

        >>> from dotwiz import make_dot_wiz_plus
        >>> make_dot_wiz_plus([('k1', 11), ('k2', [{'a': 'b'}]), ('k3', 'v3')], y=True)
        DotWizPlus(y=True, k1=11, k2=[DotWizPlus(a='b')], k3='v3')

    """
    kwargs.update(*args)

    return DotWizPlus(kwargs)


# noinspection PyDefaultArgument
def __upsert_into_dot_wiz_plus__(self, input_dict={},
                                 *, __set=dict.__setitem__,
                                 __is_keyword=keyword.iskeyword,
                                 **kwargs):
    """
    Helper method to generate / update a :class:`DotWizPlus` (dot-access dict)
    from a Python ``dict`` object, and optional *keyword arguments*.

    """
    __dict = self.__dict__

    if kwargs:
        # avoids the potential pitfall of a "mutable default argument" -
        # only update or modify `input_dict` if the param is passed in.
        if input_dict:
            input_dict.update(kwargs)
        else:
            input_dict = kwargs

    for key in input_dict:
        # note: this logic is the same as `__resolve_value__()`
        #
        # *however*, I decided to inline it because it's actually faster
        # to eliminate a function call here.
        value = input_dict[key]
        t = type(value)

        if t is dict:
            value = DotWizPlus(value)
        elif t is list:
            value = [__resolve_value__(e, DotWizPlus) for e in value]

        lower_key = key.lower()

        if __is_keyword(lower_key):
            __set(self, key, value)
            __dict[f'{lower_key}_'] = value
        else:
            # handle special cases such as `hey, world!` or `ThisIsATest`
            if not key == lower_key or not key.isidentifier():
                if key in __SPECIAL_KEYS:
                    key = __SPECIAL_KEYS[key]
                else:  # transform key to `snake case` and cache the result.
                    __SPECIAL_KEYS[key] = key = to_snake_case(key)

            # note: this logic is the same as `DotWizPlus.__setitem__()`
            __set(self, key, value)
            __dict[key] = value


def __setitem_impl__(self, key, value,
                     *, __set=dict.__setitem__,
                     __is_keyword=keyword.iskeyword):
    """Implementation of `DotWizPlus.__setitem__` to preserve dot access"""
    lower_key = key.lower()
    value = __resolve_value__(value, DotWizPlus)

    if __is_keyword(lower_key):
        __set(self, key, value)
        self.__dict__[f'{lower_key}_'] = value
    else:
        # handle special cases such as `hey, world!` or `ThisIsATest`
        if not key == lower_key or not key.isidentifier():
            if key in __SPECIAL_KEYS:
                key = __SPECIAL_KEYS[key]
            else:  # transform key to `snake case` and cache the result.
                __SPECIAL_KEYS[key] = key = to_snake_case(key)

        __set(self, key, value)
        self.__dict__[key] = value


class DotWizPlus(dict):
    """
    :class:`DotWizPlus` - a blazing *fast* ``dict`` subclass that also supports
    *dot access* notation.

    Usage::

    >>> from dotwiz import DotWizPlus
    >>> dw = DotWizPlus({'key_1': [{'k': 'v'}], 'keyTwo': '5', 'key-3': 3.21})
    >>> assert dw.key_1[0].k == 'v'
    >>> assert dw.key_two == '5'
    >>> assert dw.key_3 == 3.21

    """
    __slots__ = ('__dict__', )

    __init__ = update = __upsert_into_dot_wiz_plus__

    __delattr__ = __delitem__ = dict.__delitem__
    __setattr__ = __setitem__ = __setitem_impl__

    def __getitem__(self, key):
        return self.__dict__[key]

    def __repr__(self):
        # note: iterate over `self.__dict__` instead of `self`, in case
        # of keywords like `for`, which we store differently - like `for_`.
        fields = [f'{k}={v!r}' for k, v in self.__dict__.items()]
        # we could use `self.__class__.__name__`, but here we already know
        # the name of the class.
        return f'DotWizPlus({", ".join(fields)})'

    to_dict = __convert_to_dict__
    to_dict.__doc__ = 'Recursively convert the :class:`DotWizPlus` instance ' \
                      'back to a ``dict``.'
