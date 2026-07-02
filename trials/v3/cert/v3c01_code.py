"""layered_config — merge configuration from defaults, a file layer, and env.

Precedence, lowest to highest: schema defaults < file layer < env overrides.
File-layer values must already carry the declared type (ints are accepted
for float fields; bools are never accepted as ints); env values arrive as
strings and are coerced. Float fields must be finite. Both layers are plain
mappings supplied by the caller — this module performs no I/O of its own.
"""
import math


class ConfigError(ValueError):
    """Unknown key, wrong type, failed coercion, or failed validation."""


_TRUE_WORDS = frozenset({"1", "true", "yes", "on"})
_FALSE_WORDS = frozenset({"0", "false", "no", "off"})


def _check_typed_value(label, type_, value):
    """Verify `value` carries `type_`; return it (ints normalized to float)."""
    if type_ is bool:
        if isinstance(value, bool):
            return value
    elif type_ is float:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            value = float(value)
            if not math.isfinite(value):
                raise ConfigError(f"{label}: float must be finite, got {value!r}")
            return value
    elif isinstance(value, type_) and not isinstance(value, bool):
        return value
    raise ConfigError(f"{label}: expected {type_.__name__}, got {type(value).__name__}")


def _coerce_env(env_key, type_, raw):
    """Coerce the env string `raw` to `type_`; raise ConfigError on failure."""
    if type_ is bool:
        word = raw.strip().lower()
        if word in _TRUE_WORDS:
            return True
        if word in _FALSE_WORDS:
            return False
        raise ConfigError(f"{env_key}: cannot parse {raw!r} as bool")
    if type_ is str:
        return raw
    try:
        return type_(raw)
    except ValueError as exc:
        raise ConfigError(f"{env_key}: cannot parse {raw!r} as {type_.__name__}") from exc


class Field:
    """Schema entry: a type (str/int/float/bool), a type-checked default, and
    optional constraints — `choices` (allowed values) and inclusive
    `minimum`/`maximum` bounds, enforced on the final effective value."""

    def __init__(self, type_, default, choices=None, minimum=None, maximum=None):
        if type_ not in (str, int, float, bool):
            raise ConfigError(f"unsupported field type: {type_!r}")
        self.type = type_
        self.default = _check_typed_value("default value", type_, default)
        self.choices = None if choices is None else tuple(choices)
        self.minimum = minimum
        self.maximum = maximum


def _validate(name, field, value):
    """Check `value` against the field's constraints; return it unchanged."""
    if field.choices is not None and value not in field.choices:
        raise ConfigError(f"{name}: {value!r} not in choices {field.choices!r}")
    if field.minimum is not None and value < field.minimum:
        raise ConfigError(f"{name}: {value!r} is below minimum {field.minimum!r}")
    if field.maximum is not None and value > field.maximum:
        raise ConfigError(f"{name}: {value!r} is above maximum {field.maximum!r}")
    return value


def merge_config(schema, file_layer=None, env=None, env_prefix="APP_"):
    """Merge the layers and return a plain dict of validated values.

    `schema` maps field names to Field specs; `file_layer` is an already
    parsed mapping (unknown keys raise); field `name` is overridden by env
    key `env_prefix + name.upper()`. Prefixed env keys matching no field
    raise; unprefixed keys are ignored. Final values are validated.
    """
    if not env_prefix:
        raise ConfigError("env_prefix must be non-empty")
    file_layer = {} if file_layer is None else file_layer
    env = {} if env is None else env

    env_keys = {env_prefix + name.upper(): name for name in schema}
    if len(env_keys) != len(schema):
        raise ConfigError(f"two schema fields share one {env_prefix}* env key")
    unknown_file = sorted(set(file_layer) - set(schema))
    if unknown_file:
        raise ConfigError(f"unknown file-layer keys: {unknown_file}")
    stray = sorted(k for k in env if k.startswith(env_prefix) and k not in env_keys)
    if stray:
        raise ConfigError(f"unknown env overrides: {stray}")

    result = {}
    for name, field in schema.items():
        value = field.default
        if name in file_layer:
            value = _check_typed_value(name, field.type, file_layer[name])
        key = env_prefix + name.upper()
        if key in env:
            coerced = _coerce_env(key, field.type, env[key])
            value = _check_typed_value(name, field.type, coerced)
        result[name] = _validate(name, field, value)
    return result


if __name__ == "__main__":
    schema = {
        "host": Field(str, "localhost"),
        "port": Field(int, 8080, minimum=1, maximum=65535),
        "debug": Field(bool, False),
        "timeout": Field(float, 2.5, minimum=0.0),
        "mode": Field(str, "fast", choices=("fast", "safe")),
    }

    # Defaults only.
    assert merge_config(schema) == {"host": "localhost", "port": 8080,
                                    "debug": False, "timeout": 2.5, "mode": "fast"}
    # File layer overrides defaults; an int is accepted for a float field.
    cfg = merge_config(schema, file_layer={"port": 9000, "timeout": 3})
    assert cfg["port"] == 9000 and cfg["timeout"] == 3.0 and type(cfg["timeout"]) is float
    # Env overrides beat the file layer; strings are coerced.
    cfg = merge_config(schema, file_layer={"port": 9000}, env={
        "APP_PORT": "9100", "APP_DEBUG": "yes", "APP_MODE": "safe"})
    assert cfg["port"] == 9100 and cfg["debug"] is True and cfg["mode"] == "safe"
    # Env keys without the prefix are ignored; empty schema is fine.
    cfg = merge_config(schema, env={"PATH": "/usr/bin", "APP_HOST": "example.org"})
    assert cfg["host"] == "example.org"
    assert merge_config({}) == {}
    assert Field(float, 3).default == 3.0  # int default normalized to float

    def expect_raise(fn):
        try:
            fn()
        except ConfigError:
            return
        raise AssertionError(f"expected ConfigError from {fn}")

    expect_raise(lambda: merge_config(schema, file_layer={"protx": 1}))
    expect_raise(lambda: merge_config(schema, file_layer={"port": "9000"}))
    expect_raise(lambda: merge_config(schema, file_layer={"port": True}))
    expect_raise(lambda: merge_config(schema, file_layer={"mode": "turbo"}))
    expect_raise(lambda: merge_config(schema, env={"APP_PORT": "70000"}))
    expect_raise(lambda: merge_config(schema, env={"APP_PORT": "9k"}))
    expect_raise(lambda: merge_config(schema, env={"APP_DEBUG": "maybe"}))
    expect_raise(lambda: merge_config(schema, env={"APP_TIMEOUT": "nan"}))
    expect_raise(lambda: merge_config(schema, env={"APP_RETRIES": "3"}))
    expect_raise(lambda: merge_config(schema, env_prefix=""))
    expect_raise(lambda: Field(int, "8080"))  # mistyped default
    expect_raise(lambda: merge_config({"a_b": Field(int, 1), "A_B": Field(int, 2)}))

    print("OK")
