from .util import get_caller


# PEP 517: https://peps.python.org/pep-0517/
def get_requires_for_build_wheel(*args, **kwargs):
    return get_caller().get_requires_for_build_wheel(*args, **kwargs)


def prepare_metadata_for_build_wheel(*args, **kwargs):
    return get_caller().prepare_metadata_for_build_wheel(*args, **kwargs)


def build_wheel(*args, **kwargs):
    return get_caller().build_wheel(*args, **kwargs)


def get_requires_for_build_sdist(*args, **kwargs):
    return get_caller().get_requires_for_build_sdist(*args, **kwargs)


def build_sdist(*args, **kwargs):
    return get_caller().build_sdist(*args, **kwargs)


# PEP 660: https://peps.python.org/pep-0660/
def get_requires_for_build_editable(*args, **kwargs):
    return get_caller().get_requires_for_build_editable(*args, **kwargs)


def prepare_metadata_for_build_editable(*args, **kwargs):
    return get_caller().prepare_metadata_for_build_editable(*args, **kwargs)


def build_editable(*args, **kwargs):
    return get_caller().build_editable(*args, **kwargs)
