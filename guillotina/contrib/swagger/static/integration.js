//   SwaggerUi,
var authToken = undefined;
window.onload = function(){
  var settings = JSON.parse(document.getElementById('swagger-configuration').innerHTML);
  url = settings.initial_swagger_url
  ui = SwaggerUIBundle({
    url: url,
    dom_id: '#swagger-ui-container',
    supportedSubmitMethods: ['get', 'post', 'put', 'delete', 'patch'],
    configs: {
      preFetch: function(req) {
        if(req.loadSpec){
          req.url.trim()
          req.url.replace(/\/$/, '');
          req.url = req.url + '/@swagger'
        }
        if (authToken) {
          req.headers["Authorization"] = authToken;
          window.ui=ui
        }
              return req;
      }
    },
    onFailure: function() {
      console.log("Unable to Load SwaggerUI");
    },
    deepLinking: true,
    presets: [
      SwaggerUIBundle.presets.apis,
      SwaggerUIStandalonePreset
    ],
    plugins: [
      SwaggerUIBundle.plugins.DownloadUrl
    ],
    layout: "StandaloneLayout",
  })

    var originalAuthorize = ui.authActions.authorize;
    var logout = ui.authActions.logout
    ui.authActions.authorize = function(authorization) {
      if(authorization.basicAuth){
      authToken = "Basic " + btoa(authorization.basicAuth.value.username+":"+authorization.basicAuth.value.password);
       originalAuthorize(authorization);
       
      }
      if(authorization.bearerAuth){
        authToken = "Bearer " + authorization.bearerAuth.value
        originalAuthorize(authorization);
      }
    };
    ui.authActions.logout = function(){
      authToken = undefined;
      return logout.apply(this, arguments)
    }   
  window.ui=ui
}