{ pkgs ? import (builtins.fetchTarball
  "https://github.com/nixos/nixpkgs-channels/archive/nixos-16.09.tar.gz") {}
, pythonPackages ? pkgs.python35Packages
}:

let self = rec {

  version = builtins.replaceStrings ["\n"] [""] (builtins.readFile ./VERSION);

  chardet = pythonPackages.buildPythonPackage {
    name = "chardet-2.3.0";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/7d/87/4e3a3f38b2f5c578ce44f8dc2aa053217de9f0b6d737739b0ddac38ed237/chardet-2.3.0.tar.gz";
      sha256 = "1ak87ikcw34fivcgiz2xvi938dmclh078az65l9x3rmgljrkhgp5";
    };
    doCheck = false;
  };

  cchardet = pythonPackages.buildPythonPackage {
    name = "cchardet-1.1.1";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/c7/4c/d6094866f19a5636f68b3e6d0028fa32fae46a69d998a30e18fe43b6e81b/cchardet-1.1.1.tar.gz";
      sha256 = "16dwplfnmwlpkj003kn3rl0yv54sl0f598k5wsr4avradq92iygj";
    };
    CFLAGS = "-I${pkgs.libcxx}/include/c++/v1";
    doCheck = false;
  };

  multidict = pythonPackages.buildPythonPackage {
    name = "multidict-2.1.2";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/8b/99/a32210e82198db00d071aa207432b898ddd8061000d00d3841a63a734d31/multidict-2.1.2.tar.gz";
      sha256 = "0xl530478kamn3l473x82g91hr02cy8056cd9cyrbpjm5m3nf0yr";
    };
    buildInputs = [
      pythonPackages.cython
      pytest
    ];
    doCheck = false;
  };

  async_timeout = pythonPackages.buildPythonPackage {
    name = "async-timeout-1.1.0";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/29/f6/eeac39dfadd3a7610bb33842cf611a1f09fcd2e445ab76e4c951efde0c2b/async-timeout-1.1.0.tar.gz";
      sha256 = "109h2hc3czvacjjzpsb8csjy4698nf0pmwkv7k10x00v03zd32xq";
    };
    buildInputs = [
      pytest
      pytestrunner
    ];
    doCheck = false;
  };

  aiohttp = pythonPackages.buildPythonPackage {
    name = "aiohttp-1.0.5";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/09/5a/7b81ea8729d41f44c6fe6a116e466c8fb884950a0061aa3768dbd6bee2f8/aiohttp-1.0.5.tar.gz";
      sha256 = "1243mbwv3q8jj9c5q7405gridqnzvfr5idp8czh40zgr4rvqkqf3";
    };
    buildInputs = [
      pythonPackages.cython
    ];
    propagatedBuildInputs = [
      chardet
      cchardet
      multidict
      async_timeout
    ];
    doCheck = false;
  };

  zope_interface = pythonPackages.buildPythonPackage {
    name = "zope.interface-4.3.2";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/38/1b/d55c39f2cf442bd9fb2c59760ed058c84b57d25c680819c25f3aff741e1f/zope.interface-4.3.2.tar.gz";
      sha256 = "1vjwjj9fn0nblk1gq5vja1x3yla78yi004vv79xy4g1f0m5243ka";
    };
    doCheck = false;
  };

  persistent = pythonPackages.buildPythonPackage {
    name = "persistent-4.2.1";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/85/cc/ef995d2c270fd4174c391d304b0dbc2ea1a18f499091f37ced78041df0e0/persistent-4.2.1.tar.gz";
      sha256 = "1fdxxffyl8947ph4x4gkfd8y6475fjr5ysszxz58pv3y0qa63xwh";
    };
    propagatedBuildInputs = [
      zope_interface
    ];
    doCheck = false;
  };

  BTrees = pythonPackages.buildPythonPackage {
    name = "BTrees-4.3.1";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/24/76/cd6f225f2180c22af5cdb6656f51aec5fca45e45bdc4fa75c0a32f161a61/BTrees-4.3.1.tar.gz";
      sha256 = "15as34f9sa4nnd62nnjkik2jd4rg1byp0i4kwaqwdpv0ab9vfr95";
    };
    propagatedBuildInputs = [
      persistent
    ];
    doCheck = false;
  };

  zope_i18nmessageid = pythonPackages.buildPythonPackage {
    name = "zope.i18nmessageid-4.4.2";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/97/16/e76c4d7833d8e4246e0ebec826b68facbf21c97a1a62a9292f0b2779e3a1/zope.i18nmessageid-4.4.2.tar.gz";
      sha256 = "1rslyph0klk58dmjjy4j0jxy21k03azksixc3x2xhqbkv97cmzml";
    };
    doCheck = false;
  };

  zope_i18n = pythonPackages.buildPythonPackage {
    name = "zope.i18n-4.1.0";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/52/16/846c445fe3009b9180618145b86aeebc1c851a3da1cb9893a51c8b45d567/zope.i18n-4.1.0.tar.gz";
      sha256 = "0mp1ay5hc02ahgs7xp0wdl777j8p74zcj86pib4ywi67sh1byhkb";
    };
    propagatedBuildInputs = [
      pythonPackages.pytz
      zope_component
      zope_i18nmessageid
      zope_schema
    ];
    doCheck = false;
  };

  zope_event = pythonPackages.buildPythonPackage {
    name = "zope.event-4.2.0";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/cd/a5/4927363244aaa7fd8a696d32005ea8214c4811550d35edea27797ebbd4fd/zope.event-4.2.0.tar.gz";
      sha256 = "0n4725cr51l5pswv7g9j703vknmx60bs6rqsx8klhfl62x1004ff";
    };
    doCheck = false;
  };

  zope_schema = pythonPackages.buildPythonPackage {
    name = "zope.schema-4.4.2";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/0d/b2/41fdc6c42c4320f326c65810eff785247e65e4ea856cff15120e47b93509/zope.schema-4.4.2.tar.gz";
      sha256 = "1p943jdxb587dh7php4vx04qvn7b2877hr4qs5zyckvp5afhhank";
    };
    propagatedBuildInputs = [
      zope_event
      zope_interface
    ];
    doCheck = false;
  };

  zope_configuration = pythonPackages.buildPythonPackage {
    name = "zope.configuration-4.0.3";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/37/d7/653c2a05d876e787a1532b51ef7f89917ff17885daaac41af9da5e2f140b/zope.configuration-4.0.3.tar.gz";
      sha256 = "1x9dfqypgympnlm25p9m43xh4qv3p7d75vksv9pzqibrb4cggw5n";
    };
    propagatedBuildInputs = [
      zope_schema
      zope_i18nmessageid
    ];
    doCheck = false;
  };

  zope_security = pythonPackages.buildPythonPackage {
    name = "zope.security-4.0.3";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/fa/48/d4d207f993359fdc8bbeda17f71f882de9d0a1974dfff423c0bda7f615f1/zope.security-4.0.3.tar.gz";
      sha256 = "14zmf684amc0x32kq05yxnhfqd1cmyhafkw05gn81rn90zjv6ssy";
    };
    propagatedBuildInputs = [
      zope_component
      zope_i18nmessageid
      zope_location
      zope_proxy
      zope_schema
    ];
    doCheck = false;
  };

  zope_proxy = pythonPackages.buildPythonPackage {
    name = "zope.proxy-4.2.0";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/d3/3f/6137793109bdc27cfa2d1331c2c57f2a1081dd7e2ff872b3967c1a937d9c/zope.proxy-4.2.0.tar.gz";
      sha256 = "16n03ai07kmxj4z5sm0p5msvlmhp6sdqhg6w2ihaqm5mm1knrmn7";
    };
    propagatedBuildInputs = [
      zope_interface
    ];
    doCheck = false;  # cyclic dependency on zope.security
  };

  zope_location = pythonPackages.buildPythonPackage {
    name = "zope.location-4.0.3";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/38/8a/863ded50bb2c795299dd9168b924b03e38a90731dfbe5264e0418c257ae4/zope.location-4.0.3.tar.gz";
      sha256 = "1nj9da4ksiyv3h8n2vpzwd0pb03mdsh7zy87hfpx72b6p2zcwg74";
    };
    propagatedBuildInputs = [
      zope_interface
      zope_proxy
      zope_schema
    ];
    doCheck = false;
  };

  zope_exceptions = pythonPackages.buildPythonPackage {
    name = "zope.exceptions-4.0.8";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/8f/b7/eba9eca6841fa47d9a30f71a602be7615bff4f8e11f85c2840b88a77c68a/zope.exceptions-4.0.8.tar.gz";
      sha256 = "0zwxaaa66sqxg5k7zcrvs0fbg9ym1njnxnr28dfmchzhwjvwnfzl";
    };
    propagatedBuildInputs = [
      zope_interface
    ];
    doCheck = false;
  };

  zope_component = pythonPackages.buildPythonPackage {
    name = "zope.component-4.3.0";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/c9/56/501d51f0277af1899d1381e4b9928b5e14675187752622ddc344a756439d/zope.component-4.3.0.tar.gz";
      sha256 = "1hlvzwj1kcfz1qms1dzhwsshpsf38z9clmyksb1gh41n8k3kchdv";
    };
    propagatedBuildInputs = [
      zope_event
      zope_interface
    ];
    doCheck = false;
  };

  zope_annotation = pythonPackages.buildPythonPackage {
    name = "zope.annotation-4.4.1";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/f6/90/d4eb80fd19bad86d006bad0b9ee6dbc598c1924db49b22b96422977e8fb1/zope.annotation-4.4.1.tar.gz";
      sha256 = "011lnibldv8rsdrqxpwnpaajjqkdzyylhz0h97fk2251k028h9p5";
    };
    propagatedBuildInputs = [
      zope_component
      zope_interface
      zope_location
    ];
    doCheck = false;
  };

  plone_behavior = pythonPackages.buildPythonPackage {
    name = "plone.behavior-1.1.3";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/fd/e9/0741b349ba31a3af3125f4d28b9089641f714cb97534026ed6ed7a0317b5/plone.behavior-1.1.3.tar.gz";
      sha256 = "0wc4f1gpjpdqrw7rsmwik0z6kka7pqzzidrrm5zqqpqwj7q17q76";
    };
    propagatedBuildInputs = [
      zope_configuration
      zope_annotation
    ];
    doCheck = false;
  };

  plone_jsonserializer = pythonPackages.buildPythonPackage {
    name = "plone.jsonserializer-0.9.1";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/94/1d/64a338c9a68c660ce0f87631b574d6018621c5c999fba329691bb0fb46f5/plone.jsonserializer-0.9.1.tar.gz";
      sha256 = "1rm3y6damy014psxm36qbb7k6zxr1gbb06nwxxxhx7c7q4qgcf4i";
    };
    doCheck = false;
  };

  transaction = pythonPackages.buildPythonPackage {
    name = "transaction-1.7.0";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/be/13/adbd15c6c92ae60079aac322db2d4e6424ec98b68a00b442419bfe6a1ab9/transaction-1.7.0.tar.gz";
      sha256 = "157ijwjrga99g41nibinsifqw683711sq6x38xwjryn0sh1d0075";
    };
    propagatedBuildInputs = [
      zope_interface
    ];
    doCheck = false;
  };

  ujson = pythonPackages.buildPythonPackage {
    name = "ujson-1.35";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/16/c4/79f3409bc710559015464e5f49b9879430d8f87498ecdc335899732e5377/ujson-1.35.tar.gz";
      sha256 = "11jz5wi7mbgqcsz52iqhpyykiaasila4lq8cmc2d54bfa3jp6q7n";
    };
    doCheck = false;
  };

  ZConfig = pythonPackages.buildPythonPackage {
    name = "ZConfig-3.1.0";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/52/b3/a96d62711a26d8cfbe546519975dc9ed54d2eb50b3238d2e6de045764796/ZConfig-3.1.0.tar.gz";
      sha256 = "0bl4186bfxiiv8y1pspz5jlr8a9r2xkx8dl016l2asd5ffha67y2";
    };
    doCheck = false;
  };

  zdaemon = pythonPackages.buildPythonPackage {
    name = "zdaemon-4.1.0";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/cd/db/20dd050d4486cbaeced4f51a381b7f057632c52c3e160be29d9139f6b7cb/zdaemon-4.1.0.zip";
      sha256 = "1ydi1bhqq874zqyyfp0098r7b7isgk6wawkmvfy8p4lzni53fnqq";
    };
    propagatedBuildInputs = [
      ZConfig
    ];
    doCheck = false;
  };

  ZEO = pythonPackages.buildPythonPackage {
    name = "ZEO-5.0.2";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/8d/19/5eba4c05acc5f55a28b782e6342cdf4e182e8fce011c9cb00d3851d067f1/ZEO-5.0.2.tar.gz";
      sha256 = "1phz4f6bq9jsm2l09y1s4ixzzam7gyjgb0xx7l767h0xb0m9mv38";
    };
    propagatedBuildInputs = [
      pythonPackages.six
      zdaemon
      ZODB
    ];
    doCheck = false;
  };

  zc.lockfile = pythonPackages.buildPythonPackage {
    name = "zc.lockfile=1.2.1";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/bd/84/0299bbabbc9d3f84f718ba1039cc068030d3ad723c08f82a64337edf901e/zc.lockfile-1.2.1.tar.gz";
      sha256 = "0gh41p02x0h0bcqvnsznapk4yb01mvgbzm38wamfhbzjlynr3nqi";
    };
    doCheck = false;
  };

  zodbpickle = pythonPackages.buildPythonPackage {
    name = "zodbpickle-0.6.0";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/7a/fc/f6f437a5222b330735eaf8f1e67a6845bd1b600e9a9455e552d3c13c4902/zodbpickle-0.6.0.tar.gz";
      sha256 = "0rb634fp91l68csrilz7a9fj7fcjm5gf7c1x3rwyfnb1jsz4hcpa";
    };
    doCheck = false;
  };

  ZODB = pythonPackages.buildPythonPackage {
    name = "ZODB-5.0.0";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/a5/b3/0577df5cc2be1a4efceb4d5f1375968595072e9e4889d71605d36e410a14/ZODB-5.0.0.tar.gz";
      sha256 = "01spa2ijmjzcxbafyqj8vx72wm18476wsl0dnc0yh8a007zlz111";
    };
    propagatedBuildInputs = [
      BTrees
      persistent
      pythonPackages.six
      transaction
      zc.lockfile
      ZConfig
      zodbpickle
    ];
    doCheck = false;
  };

  zope_browser = pythonPackages.buildPythonPackage {
    name = "zope.browser-2.1.0";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/d0/f3/6638d8c238a8923f5c65dfa91e4078826b5a24619a5ff8bfbe69d1d4e49e/zope.browser-2.1.0.tar.gz";
      sha256 = "18jx1arcjsx9ipc0f3dsr0mw744hq50v6ciacj2xj05l0563hl3g";
    };
    propagatedBuildInputs = [
      zope_interface
    ];
    doCheck = false;
  };

  zope_authentication = pythonPackages.buildPythonPackage {
    name = "zope.authentication-4.2.1";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/c0/f0/88ace1a23decf050835ec4bacc53cf01135b83f81ade4b0ae772894fb10d/zope.authentication-4.2.1.tar.gz";
      sha256 = "000pn7q4j3mkmd48gciq0n68k63llnzggknr5kf1pfv6bx1vjvpm";
    };
    propagatedBuildInputs = [
      zope_security
      zope_browser
    ];
    doCheck = false;
  };

  zope_dottedname = pythonPackages.buildPythonPackage {
    name = "zope.dottedname-4.1.0";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/61/61/d910357dfdfb10f7defde018e81506feea01141711a88cfb088f6ff9f45f/zope.dottedname-4.1.0.tar.gz";
      sha256 = "0z0agz2zax8pcasa630l2jr4wb94wgf9dw58d56cc2s7lrjzvvjl";
    };
    doCheck = false;
  };

  zope_datetime = pythonPackages.buildPythonPackage {
    name = "zope.datetime-4.1.0";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/f9/42/53ef2c03d85225068fd189fc264bbc6d6a5560b4cbb879ad66be9bba4854/zope.datetime-4.1.0.tar.gz";
      sha256 = "1yvg836y17zd8g6cmys4iq2cwxvj4yzjs3ysyx2bys43xa29nagb";
    };
    doCheck = false;
  };

  zope_dublincore = pythonPackages.buildPythonPackage {
    name = "zope.dottedname-4.1.1";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/59/3a/8d15ae261a8fac53d3091d45fff8c0982f83d9e0f617d5cc1d1433d17257/zope.dublincore-4.1.1.tar.gz";
      sha256 = "1yjrphs0gjm3wyy4jdrryxk35my43n7dpjzpd4m3lxpy18lzg4jz";
    };
    propagatedBuildInputs = [
      pythonPackages.pytz
      pythonPackages.six
      persistent
      zope_annotation
      zope_component
      zope_configuration
      zope_datetime
      zope_interface
      zope_lifecycleevent
      zope_location
      zope_schema
      zope_security
    ];
    doCheck = false;
  };

  zope_lifecycleevent = pythonPackages.buildPythonPackage {
    name = "zope.lifecycleevent-4.1.0";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/27/fd/346b2f83049e451ee3c609d15ee183330e0adf48bb207a081c52263843f6/zope.lifecycleevent-4.1.0.tar.gz";
      sha256 = "1imhslxf4hf8gspgm56d97gq9qqp5zhxlmqzmicmgba27qg7m3p2";
    };
    propagatedBuildInputs = [
      zope_event
      zope_interface
    ];
    doCheck = false;
  };

  zope_securitypolicy = pythonPackages.buildPythonPackage {
    name = "zope.securitypolicy-4.1.0";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/90/e9/8d950f1b265835104e925671f4b57a236218f7e7fc507049043edb875449/zope.securitypolicy-4.1.0.tar.gz";
      sha256 = "1jpg2kx7jkasw5g4shmj8s9khwn3jchw8m2wnn7a61k0bf620277";
    };
    propagatedBuildInputs = [
      persistent
      zope_annotation
      zope_authentication
      zope_configuration
      zope_i18nmessageid
    ];
    doCheck = false;
  };

  zope_testing = pythonPackages.buildPythonPackage {
    name = "zope.testing-4.6.0";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/fd/99/adba8abc72a3598befd25789822de82699bd5aecf268846b40a147a225e2/zope.testing-4.6.0.tar.gz";
      sha256 = "0349dyfa11c1q4rs3640wymj09r0a4lrgsx5wp0pqqzs5xkxld09";
    };
    propagatedBuildInputs = [
      zope_interface
      zope_exceptions
    ];
    doCheck = false;
  };

  gocept_pytestlayer = pythonPackages.buildPythonPackage {
    name = "gocept.pytestlayer-5.0";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/5d/09/b72b87846c97afc06ee116b4a68c6d65192d8d0bdae85a56dbc02c8dbf9f/gocept.pytestlayer-5.0.tar.gz";
      sha256 = "0l9w5lc4svs3lhmr0dx3bsypfn9wnpib0y1w40vgckp3yg9fbsw0";
    };
    propagatedBuildInputs = [
      zope_dottedname
      pytest
      pythonPackages.six
    ];
    doCheck = false;
  };

  pytest = pythonPackages.pytest.overrideDerivation(old: {
    name = "pytest-3.0.4";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/2f/03/0c636d7191255e1737012e5f9c42368f11b55463aeea46fb1955892cab0d/pytest-3.0.4.tar.gz";
      sha256 = "03d49xc0l4sdncq47rn1p42ywjnxqrvpc160y8dwvanv3wnfx7w7";
    };
    propagatedNativeBuildInputs = old.propagatedNativeBuildInputs ++ [
      pythonPackages.hypothesis
    ];
  });

  pytestrunner = pythonPackages.buildPythonPackage {
    name = "pytest-runner-2.9";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/11/d4/c335ddf94463e451109e3494e909765c3e5205787b772e3b25ee8601b86a/pytest-runner-2.9.tar.gz";
      sha256 = "0cfiw5m3ds68spxnpz48dpqcd78vwzgh8fbdg5j1zx82kgjqsdsh";
    };
    propagatedBuildInputs = [
      pytest
    ];
    doCheck = false;
  };

};

in pythonPackages.buildPythonPackage rec {
  name = "plone.server-${self.version}";
  src = builtins.filterSource
    (path: type: baseNameOf path != ".git"
              && baseNameOf path != "result")
    ./.;
  buildInputs = with self; [
    (pythonPackages.zc_buildout_nix.overrideDerivation(args: {
      postInstall = "";
      inherit propagatedBuildInputs;
    }))
    pytest
    pytestrunner
    pythonPackages.requests2
    zope_testing
    gocept_pytestlayer
  ];
  propagatedBuildInputs = with self; [
    aiohttp
    BTrees
    persistent
    plone_behavior
    plone_jsonserializer
    pythonPackages.dateutil
    pythonPackages.pycrypto
    pythonPackages.setuptools
    pythonPackages.six
    transaction
    ujson
    ZEO
    ZODB
    zope_authentication
    zope_component
    zope_configuration
    zope_dottedname
    zope_dublincore
    zope_event
    zope_i18n
    zope_i18nmessageid
    zope_interface
    zope_lifecycleevent
    zope_location
    zope_proxy
    zope_schema
    zope_security
    zope_securitypolicy
  ];
}
