# `py-generator-build-backend`

A Python build backend designed to wrap Python package generators (such as
[`openapi-python-client`]) into a PEP 517 compatible source tree.

## Demo

Create a new directory with a `pyproject.toml`:

```toml
[project]
name = "tictactoe-client"
dynamic = [
    "version",
    "dependencies",
]

[build-system]
requires = [
    "py-generator-build-backend",
]
build-backend = "py_generator_build_backend"

[tools.py-generator-build-backend]
generator = "openapi-python-client generate --url https://raw.githubusercontent.com/OAI/learn.openapis.org/refs/heads/main/examples/v3.1/tictactoe.json --output-path $GENERATOR_OUT_PATH"
```

The `tools.py-generator-build-backend.generator` is the key to making this work:
this command must produce a valid PEP 517 source tree in the (not-yet-existent)
directory specified by the `$GENERATOR_OUT_PATH` environment variable. You can
interpolate other environment variables in `generator` if you need to.

Note: you are responsible for making sure the command you want to run is
available on the `PATH`.

Now try to build the package: `python -m build .`. This should fail to build,
with instructions about the build requirements you need to add to your
`build-system.requires`. Add them and confirm that you are now able to build
the package.

Congratulations, you've got a Python package! See [Packaging Python Projects]
for possible next steps.

## Notes

For performance reasons, the output of the generator is cached in
`platformdirs.user_cache_dir`. We compute the cache entry by hashing together
the contents of the entire project directory, along with all environment
variables. This does a pretty good job of capturing all the "inputs" that go
into generating the package, but it's not perfect: the generator could be
non-deterministic, or packages could be updated in the `PATH`. If you care
about things like this, consider adopting a hermetic build tool like
[nix](https://nixos.org/).

(Ideally we'd have access to a scratch space that only lives as long as the
build frontend is invoking this build backend, but as far as I can tell,
there's no standardized mechanism for that.)

## Development

### Releasing

Edit `version` in `pyproject.toml`:

- `uv build`
- `uv publish`

[`openapi-python-client`]: https://github.com/openapi-generators/openapi-python-client
[Packaging Python Projects]: https://packaging.python.org/en/latest/tutorials/packaging-projects/
