"""
Contains MEMENTO's configuration generator and ``Configuration``, ``Config`` types.
"""

import itertools


def generate_configurations(matrix: dict) -> "Configurations":
    """
    Generate a list of configurations from a configuration matrix. You usually shouldn't need to
    call this directly, as it's called as part of ``Memento.run``. Of course, if you don't want
    to use MEMENTO's runner framework this method can be used completely standalone.
    """

    if not isinstance(matrix, dict):
        raise TypeError(f"matrix must be a dict, got {type(matrix)}")

    if "parameters" not in matrix:
        raise ValueError("matrix must contain a 'parameters' key")

    if "settings" in matrix["parameters"]:
        raise ValueError("settings is a reserved parameter name")

    parameters = matrix["parameters"]
    settings = matrix.get("settings", {})
    exclude = matrix.get("exclude", [])

    # Generate the cartesian product of all parameters
    elements = itertools.product(*parameters.values())
    configs = [Config(**dict(zip(parameters.keys(), element))) for element in elements]

    idx_exclude = set()
    for ex in exclude:
        for i, config in enumerate(configs):
            if all(getattr(config, k, _Never) == v for (k, v) in ex.items()):
                idx_exclude.add(i)
    configs = [j for i, j in enumerate(configs) if i not in idx_exclude]

    return Configurations(configs, settings)


class Configurations:
    """
    Holds all generated experiment configurations.

    Global settings can be accessed via `configurations.settings`.
    """

    def __init__(self, configs, settings):
        self.configurations = configs
        self.settings = settings

        # Create back-references
        for config in self.configurations:
            config.settings = settings

    def __len__(self):
        return self.configurations.__len__()

    def __iter__(self):
        return self.configurations.__iter__()

    def __getitem__(self, index):
        return self.configurations.__getitem__(index)


class Config:
    """
    A single experiment configuration. Parameters are set as attributes.

    Global settings can also be accessed via `config.settings`.
    """

    def __new__(cls, *args, **kwargs):  # pylint: disable=W0613
        self = super(Config, cls).__new__(cls)
        # This is required to establish the invariant that `_dict` is always defined.
        # During deserialization __getattr__ may be called before __init__. If _dict
        # is not defined this creates an infinite loop.
        self._dict = {}
        return self

    def __init__(self, **kwargs):
        self._dict = kwargs

    def __getattr__(self, name):
        try:
            return self._dict[name]
        except KeyError:
            raise AttributeError(name) from None

    def __str__(self):
        pretty_dict = {}
        for key, value in self._dict.items():
            try:
                value = value.__name__
            except AttributeError:
                value = value.__class__.__name__
            pretty_dict[key] = value
        return str(pretty_dict)

    def __repr__(self):
        return self._dict.__repr__()

    def __eq__(self, obj: object) -> bool:
        if not isinstance(obj, type(self)):
            return False
        return self._dict == obj._dict and self.settings == obj.settings

    def asdict(self):
        """
        Return the internal `dict` of parameters.
        """

        return self._dict


class _Never:  # pylint: disable=R0903
    """
    Type used for hackish equality test (it should always fail, as this should never be
    constructed).
    """

    def __init__(self) -> None:
        raise Exception("_Never cannot be constructed")
