//   SwaggerUi,
var authToken = undefined;
// console.log()
window.onload = function(){
  ui = SwaggerUIBundle({
    url: "http://localhost:8080/",
    dom_id: '#swagger-ui-container',
    supportedSubmitMethods: ['get', 'post', 'put', 'delete', 'patch'],
    configs: {
      preFetch: function(req) {
        req.url.trim()
        req.url.replace(/\/$/, '');
        req.url = req.url + '/@swagger'
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
    var logout = ui.authActions.logout
    ui.authActions.logout = function(){
      authToken = undefined;
      return logout.apply(this, arguments)
    }   
  window.ui=ui
}