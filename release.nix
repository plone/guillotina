{ image_name ? "guillotina",
  image_tag ? "master", image_entrypoint ? "/bin/server"
, supportedSystems ? [ "x86_64-linux" ]
, pkgs ? import (builtins.fetchTarball
  "https://github.com/nixos/nixpkgs-channels/archive/nixos-16.09.tar.gz") {}
}:

let

  pkgFor = system: import ./default.nix {
    pkgs = import pkgs.path { inherit system; };
  };

in rec {

  build = pkgs.lib.genAttrs supportedSystems (system: pkgs.lib.hydraJob (
    pkgFor system
  ));

  python = pkgs.lib.genAttrs supportedSystems (system: pkgs.lib.hydraJob (
    let package = pkgFor system;
        syspkgs = import pkgs.path { inherit system; };
    in syspkgs.python35Packages.python.buildEnv.override {
      extraLibs = package.nativeBuildInputs
                  ++ package.propagatedNativeBuildInputs;
      ignoreCollisions = true;
    }
  ));

  tarball = pkgs.lib.hydraJob((pkgFor "x86_64-linux")
                    .overrideDerivation(args: {
    phases = [ "unpackPhase" "buildPhase" ];
    buildPhase = ''
      ${python."x86_64-linux"}/bin/python3 setup.py sdist --formats=gztar
      mkdir -p $out/tarballs $out/nix-support
      mv dist/${args.name}.tar.gz $out/tarballs
      echo "file source-dist $out/tarballs/${args.name}.tar.gz" > \
           $out/nix-support/hydra-build-products
      echo ${args.name} > $out/nix-support/hydra-release-name
    '';
  }));

  image = pkgs.lib.hydraJob (
    let package = pkgFor "x86_64-linux";
        syspkgs = import pkgs.path { system = "x86_64-linux"; };
        python = syspkgs.python35.buildEnv.override {
          extraLibs = [ package ];
          ignoreCollisions = true;
        };
    in pkgs.dockerTools.buildImage {
      name = image_name;
      tag = image_tag;
      contents = [ syspkgs.busybox python ];
      runAsRoot = ''
        #!${pkgs.stdenv.shell}
        ${pkgs.dockerTools.shadowSetup}
        groupadd --system --gid 65534 nobody
        useradd --system --uid 65534 --gid 65534 -d / -s /sbin/nologin nobody
        echo "hosts: files dns" > /etc/nsswitch.conf
        mkdir -p /usr/bin && ln -s /bin/env /usr/bin
      '';
      config = {
        EntryPoint = [ "${image_entrypoint}" ];
        User = "nobody";
      };
    }
  );
}
