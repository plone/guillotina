{ pkgs ? import (builtins.fetchTarball  # revision for reproducible builds
  "https://github.com/nixos/nixpkgs-channels/archive/nixos-16.03.tar.gz") {}
, pythonPackages ? pkgs.python35Packages
}:

let self = {
  buildout = pythonPackages.zc_buildout_nix.overrideDerivation(args: {
    postInstall = "";
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
