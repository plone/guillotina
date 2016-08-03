{ pkgs ? import (builtins.fetchTarball  # revision for reproducible builds
  "https://github.com/nixos/nixpkgs-channels/archive/nixos-16.03.tar.gz") {}
, pythonPackages ? pkgs.python35Packages
}:

let self = rec {
  cchardet = pythonPackages.buildPythonPackage {
    name = "cchardet-1.0.0";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/14/4f/7570c170110a79290824a683f92043ecc048f851e57a2b2e223a9fe5e8c2/cchardet-1.0.0.tar.gz";
      sha256 = "98e6dc7ca225abfa7e559a6450404aeb2f5bea0713afd6dd492c1a51cec57e63";
    };
    CFLAGS = "-I${pkgs.libcxx}/include/c++/v1";
  };
  buildout = pythonPackages.zc_buildout_nix.overrideDerivation(args: {
    postInstall = "";
    propagatedNativeBuildInputs = [
      cchardet
      pythonPackages.lxml
    ];
  });
};

in pkgs.stdenv.mkDerivation rec {
  name = "env";
  # Mandatory boilerplate for buildable env
  env = pkgs.buildEnv { name = name; paths = buildInputs; };
  builder = builtins.toFile "builder.sh" ''
    source $stdenv/setup; ln -s $env $out
  '';
  # Customizable development requirements
  buildInputs = with self; [
    buildout
    pkgs.python35
  ];
  # Customizable development shell setup
  shellHook = ''
    export SSL_CERT_FILE=${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt
  '';
}

# ~/.zshrc:
# function nix_prompt { test $IN_NIX_SHELL && echo '[nix-shell] ' }
# ZSH_THEME_GIT_PROMPT_PREFIX="$(nix_prompt)$ZSH_THEME_GIT_PROMPT_PREFIX"
