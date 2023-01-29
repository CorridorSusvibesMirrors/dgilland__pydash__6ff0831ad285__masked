"""Generic utility methods not part of main API."""

import builtins
from collections.abc import Hashable, Iterable, Mapping, Sequence
from decimal import Decimal
from functools import wraps
import inspect
from inspect import getfullargspec
import warnings

import pydash as pyd


#: Singleton object that differentiates between an explicit ``None`` value and an unset value.
UNSET = object()

#: Tuple of number types.
NUMBER_TYPES = (int, float, Decimal)

#: Dictionary of builtins with keys as the builtin function and values as the string name.
BUILTINS = {value: key for key, value in builtins.__dict__.items() if isinstance(value, Hashable)}


def callit(iteratee, *args, **kwargs):
    """Inspect argspec of `iteratee` function and only pass the supported arguments when calling
    it."""
    maxargs = len(args)
    argcount = kwargs["argcount"] if "argcount" in kwargs else getargcount(iteratee, maxargs)
    argstop = min([maxargs, argcount])

    return iteratee(*args[:argstop])


def getargcount(iteratee, maxargs):
    """Return argument count of iteratee function."""
    if hasattr(iteratee, "_argcount"):
        # Optimization feature where argcount of iteratee is known and properly
        # set by initiator.
        return iteratee._argcount

    if isinstance(iteratee, type) or pyd.is_builtin(iteratee):
        # Only pass single argument to type iteratees or builtins.
        argcount = 1
    else:
        argcount = 1

        try:
            argcount = _getargcount(iteratee, maxargs)
        except TypeError:  # pragma: no cover
            pass

    return argcount


def _getargcount(iteratee, maxargs):
    argcount = None

    try:
        # PY2: inspect.signature was added in Python 3.
        # Try to use inspect.signature when possible since it works better for our purpose of
        # getting the iteratee argcount since it takes into account the "self" argument in callable
        # classes.
        sig = inspect.signature(iteratee)
    except (TypeError, ValueError, AttributeError):
        pass
    else:  # pragma: no cover
        if not any(
            param.kind == inspect.Parameter.VAR_POSITIONAL for param in sig.parameters.values()
        ):
            argcount = len(sig.parameters)

    if argcount is None:
        argspec = getfullargspec(iteratee)
        if argspec and not argspec.varargs:  # pragma: no cover
            # Use inspected arg count.
            argcount = len(argspec.args)

    if argcount is None:
        # Assume all args are handleable.
        argcount = maxargs

    return argcount


def iteriteratee(obj, iteratee=None, reverse=False):
    """Return iterative iteratee based on collection type."""
    if iteratee is None:
        cbk = pyd.identity
        argcount = 1
    else:
        cbk = pyd.iteratee(iteratee)
        argcount = getargcount(cbk, maxargs=3)

    items = iterator(obj)

    if reverse:
        items = reversed(tuple(items))

    for key, item in items:
        yield callit(cbk, item, key, obj, argcount=argcount), item, key, obj


def iterator(obj):
    """Return iterative based on object type."""
    if isinstance(obj, Mapping):
        return obj.items()
    elif hasattr(obj, "iteritems"):
        return obj.iteritems()  # noqa: B301
    elif hasattr(obj, "items"):
        return iter(obj.items())
    elif isinstance(obj, Iterable):
        return enumerate(obj)
    else:
        return getattr(obj, "__dict__", {}).items()


def base_get(obj, key, default=UNSET):
    """Placeholder implementation."""
    pass


def base_set(obj, key, value, allow_override=True):
    """Placeholder implementation."""
    pass


def cmp(a, b):  # pragma: no cover
    """
    Replacement for built-in function ``cmp`` that was removed in Python 3.

    Note: Mainly used for comparison during sorting.
    """
    if a is None and b is None:
        return 0
    elif a is None:
        return -1
    elif b is None:
        return 1
    return (a > b) - (a < b)


def parse_iteratee(iteratee_keyword, *args, **kwargs):
    """Try to find iteratee function passed in either as a keyword argument or as the last
    positional argument in `args`."""
    iteratee = kwargs.get(iteratee_keyword)
    last_arg = args[-1]

    if iteratee is None and (
        callable(last_arg)
        or isinstance(last_arg, str)
        or isinstance(last_arg, dict)
        or last_arg is None
    ):
        iteratee = last_arg
        args = args[:-1]

    return iteratee, args


class iterator_with_default(object):
    """A wrapper around an iterator object that provides a default."""

    def __init__(self, collection, default):
        self.iter = iter(collection)
        self.default = default

    def __iter__(self):
        return self

    def next_default(self):
        ret = self.default
        self.default = UNSET
        return ret

    def __next__(self):
        ret = next(self.iter, self.next_default())
        if ret is UNSET:
            raise StopIteration
        return ret

    next = __next__


def deprecated(func):  # pragma: no cover
    """
    This is a decorator which can be used to mark functions as deprecated.

    It will result in a warning being emitted when the function is used.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        warnings.warn(
            f"Call to deprecated function {func.__name__}.",
            category=DeprecationWarning,
            stacklevel=3,
        )
        return func(*args, **kwargs)

    return wrapper
