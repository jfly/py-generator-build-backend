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
          python = pkgs.python3;
        }).overrideScope
          (
            lib.composeManyExtensions [
              inputs.pyproject-build-systems.overlays.default
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
