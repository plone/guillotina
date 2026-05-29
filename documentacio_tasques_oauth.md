Tasques revisades:

Implementacio well known:

Documentacio: https://www.rfc-editor.org/info/rfc9728/

Explicacio principal:

- Quan fem la peticio a la peticio de @mcp/protocol, si l'usuari no esta autenticat tornem unes capçaleres perque el client pugui autenticarse amb oauth. 

La reposta es :
```json
{
    "resource": "http://localhost:8080/db/container/@mcp/protocol",
    "authorization_servers": [
        "http://localhost:8080/db/container"
    ],
    "scopes_supported": [
        "guillotina:access"
    ]
}
```



Preguntes:

Quin RFC ens diu que el validador del JWT normal, s'ha de bloquejar si el token es d'oauth?

A parlar amb el ramon, estem fent un lock per la bd al crear les taules en la utility, realment pg no te problemes en diferens instancies intantant crear estructura, com a molt retornaria un error, es una mica de sobreenyinyeria o codi inecessari aquest lock? Realment amb les utilities no hauriem de tenir mai una mateixa instància dos processos a la vegada. 
