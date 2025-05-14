{ inputs, lib, ... }:
{
  imports = [
    inputs.devshell.flakeModule
  ];

  perSystem =
    { pkgs, system, ... }:
    let
      workspace = inputs.uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./..; };

      overlay = workspace.mkPyprojectOverlay {
        sourcePreference = "wheel";
      };
      pythonSet =
        (pkgs.callPackage inputs.pyproject-nix.build.packages {
          # 2025-07-07: Ideally we'd test with Python 3.9, as that's is the
          # oldest supported version of Python
          # <https://devguide.python.org/versions/>. However, that version of
          # Python is no longer packaged in nixos-unstable. I don't think it's
          # worth pulling a different version of nixpkgs just to do that. I
          # also doubt we'll actually have anything Python 3.9 users for this
          # package anyways.
          python = pkgs.python310;
        }).overrideScope
          (
            lib.composeManyExtensions [
              inputs.pyproject-build-systems.overlays.default
              overlay
              (final: prev: {
                py-generator-build-backend = prev.py-generator-build-backend.overrideAttrs (oldAttrs: {
                  nativeBuildInputs = oldAttrs.nativeBuildInputs ++ (final.resolveBuildSystem { editables = [ ]; });
                });
              })
            ]
          );
      editableOverlay = workspace.mkEditablePyprojectOverlay {
        root = "$PRJ_ROOT"; # Set by devshell.
      };
      editablePythonSet = pythonSet.overrideScope editableOverlay;
      virtualenv = editablePythonSet.mkVirtualEnv "dev-env" workspace.deps.all;
    in
    {
      devshells.default = {
        packages = [
          virtualenv
          pkgs.uv
        ];
      };

      packages.default = pythonSet.py-generator-build-backend;
    };
}
