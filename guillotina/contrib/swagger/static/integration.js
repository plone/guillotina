/* global
  SwaggerUi,
  localStorage,
  XMLHttpRequest,
  btoa,
  hljs,
  SwaggerClient
*/
/*
No way, pure js(minus swagger ui), how is this possible?

Well, let's give the old fashioned way a try I guess since building swagger ui
separately was painful...

Things we're trying to do...

- authenticate
- load swagger json
- load swagger ui with authenticated requests...

*/


var _E = function(el){
  var that = this;
  that.hide = function(){
    el.style.display = 'none';
  };
  that.show = function(){
    el.style.display = 'block';
  };
  that.addClass = function(klassName){
    if (el.classList){
      el.classList.add(klassName);
    }else{
      el.className += ' ' + klassName;
    }
  };
  that.removeClass = function(klassName){
    if (el.classList){
      el.classList.remove(klassName);
    }else{
      el.className = el.className.replace(new RegExp('(^|\\b)' + klassName.split(' ').join('|') + '(\\b|$)', 'gi'), ' ');
    }
  };
};
var Q = function(qs){
  return document.querySelector(qs);
};
var E = function(el){
  /* element utilities... like jq */
  if(typeof(el) === 'string'){
    // query selector for it...
    el = Q(el);
  }
  return new _E(el);
};

var urlJoin = function(){
  var parts = [];
  Array.prototype.slice.call(arguments).forEach(function(part, idx){
    if(idx !== 0){
      if(part.substring(0, 1) === '/'){
        part = part.substring(1);
      }
    }
    if(part.substring(part.length - 1, part.length) === '/'){
      part = part.substring(0, part.length - 1);
    }
    parts.push(part);
  });
  return parts.join('/');
};


var Authenticator = function(options){
  var _ls_username_key = '_swagger_username';
  var _ls_password_key = '_swagger_password';
  var _ls_base_url = '_swagger_base_url';
  var _ls_authorization_key = '_swagger_authorization'

  var that = this;
  that.elements = {
    username: Q('#username'),
    password: Q('#password'),
    authorization: Q('#authorization'),
    baseUrl: Q('#baseUrl'),
    modal: Q('#login-modal'),
    authBtn: Q('#authenticate'),
    cancelAuthBtn: Q('#cancel'),
    reauthWrapper: Q('#auth_container'),
    reauthBtn: Q('#auth_container a'),
  };

  that.init = function(){
    that.authorization = null;
    (options.application.settings.auth_storage_search_keys || []).forEach(function(key){
      if(that.authorization){
        return;
      }
      var val = localStorage.getItem(key);
      if(val){
        try{
          val = JSON.parse(val);
          if(val.user_jwt){
            that.authorization = 'Bearer ' + val.user_jwt;
          }
        }catch(e){
          //
        }
      }
    });
    if(that.authorization){
      that.username = that.password = '';
    }else{
      that.username = localStorage.getItem(_ls_username_key) || '';
      that.password = localStorage.getItem(_ls_password_key) || '';
    }
    that.baseUrl = localStorage.getItem(_ls_base_url) || options.application.settings.initial_swagger_url;
    that.options = options;

    if(!this.elements.authBtn){
      return;
    }
    that.elements.authBtn.addEventListener('click', that.authenticateClicked);
    if(that.elements.reauthBtn){
      that.elements.reauthBtn.addEventListener('click', function(e){
        e.preventDefault();
        that.showModal();
      });
    }
    that.elements.cancelAuthBtn.addEventListener('click', function(e){
      e.preventDefault();
      that.hideModal();
    });
  };

  that.isLoggedIn = function(){
    return that.authorization || (that.username && that.password);
  };

  that.showModal = function(){
    that.elements.username.value = that.username;
    that.elements.password.value = that.password;
    that.elements.authorization.value = that.authorization;
    that.elements.baseUrl.value = that.baseUrl;
    E(that.elements.modal).show();
  };
  that.hideModal = function(){
    E(that.elements.modal).hide();
  };

  that.authenticateClicked = function(e){
    e.preventDefault();
    that.authorization = that.elements.authorization.value;
    that.username = that.elements.username.value;
    that.password = that.elements.password.value;
    that.baseUrl = that.elements.baseUrl.value;
    localStorage.setItem(_ls_username_key, that.username);
    localStorage.setItem(_ls_password_key, that.password);
    localStorage.setItem(_ls_base_url, that.baseUrl);
    localStorage.setItem(_ls_authorization_key, that.authorization);
    if(that.options.onLogin){
      that.options.onLogin();
    }
    that.hideModal();
  };

  that.getAuthToken = function(){
    if(that.authorization){
      return that.authorization;
    }
    return 'Basic ' + btoa(that.username + ':' + that.password);
  };

  that.init();
};

var Application = function(settings){
  var that = this;
  that.settings = settings;
  that.authenticator = null;

  that.init = function(){
    that.ui = null;
    that.authenticator = new Authenticator({
      application: that,
      onLogin: function(){
        window.location.hash = '';
        that.render();
      }
    });
    that.render();

    hljs.configure({
      highlightSizeThreshold: 5000
    });
    if(window.SwaggerTranslator) {
      window.SwaggerTranslator.translate();
    }
  };

  that.render = function(){
    that.getSwagger(function(definition){
      that.ui = new SwaggerUi({
        spec: definition,
        dom_id: "swagger-ui-container",
        supportedSubmitMethods: ['get', 'post', 'put', 'delete', 'patch'],
        validatorUrl: null,
        docExpansion: 'list',
        onComplete: function(){
        },
        onFailure: function() {
          console.log("Unable to Load SwaggerUI");
        },
        jsonEditor: false,
        defaultModelRendering: 'schema',
        showRequestHeaders: false,
        showOperationIds: false,
        apisSorter: 'alpha',
        operationsSorter: function(one, two){
          if(one.method === 'get'){
            return -1;
          }else if(two.method === 'get'){
            return 1;
          }
          return one.method > two.method;
        }
      });

      that.ui.load();
      if(that.authenticator.isLoggedIn()){
        var auth =
        that.ui.api.clientAuthorizations.add(
          "auth_name", new SwaggerClient.ApiKeyAuthorization(
            "AUTHORIZATION", that.authenticator.getAuthToken(), "header"));
        }
    });
  };

  that.getSwagger = function(onLoad){
    var request = new XMLHttpRequest();
    request.open('GET', urlJoin(this.authenticator.baseUrl, '@swagger'), true);
    if(that.authenticator.isLoggedIn()){
      request.setRequestHeader("AUTHORIZATION", that.authenticator.getAuthToken());
    }

    request.onload = function() {
      if (request.status >= 200 && request.status < 400) {
        // Success!
        var resp = request.responseText;
        onLoad(JSON.parse(resp));
      } else {
        // We reached our target server, but it returned an error
        alert('Error getting swagger definition. Try using different url or auth details');
        that.authenticator.showModal();
      }
    };

    request.onerror = function() {
      // There was a connection error of some sort
      alert('Error getting swagger definition. Try using different url or auth details');
      that.authenticator.showModal();
    };

    request.send();

  };

  that.init();
};


window.onload = function() {
  var settings = JSON.parse(document.getElementById('swagger-configuration').innerHTML);
  new Application(settings);
};
