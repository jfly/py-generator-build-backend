{ inputs, lib, ... }:
{
  imports = [
    inputs.devshell.flakeModule
  ];

  perSystem =
    { pkgs, ... }:
    let
      workspace = inputs.uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./..; };

      overlay = workspace.mkPyprojectOverlay {
        sourcePreference = "wheel";
      };
      pythonSet =
        (pkgs.callPackage inputs.pyproject-nix.build.packages {
          # 2025-05-12: this is the oldest supported version of Python. See
          # https://devguide.python.org/versions/
          python = pkgs.python39;
        }).overrideScope
          (
            lib.composeManyExtensions [
              inputs.pyproject-build-systems.overlays.default
              # <<< (final: prev: {
              # <<<   hatchling = prev.hatchling.overrideAttrs (oldAttrs: {
              # <<<     nativeBuildInputs = oldAttrs.nativeBuildInputs ++ [
              # <<<       (lib.traceVal (final.resolveBuildSystem { editables = [ ]; }))
              # <<<     ];
              # <<<   });
              # <<< })
              overlay
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
