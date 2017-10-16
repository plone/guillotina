
var BASE_URL = 'http://localhost:8080/db/container'
var JWT_KEY = 'gchat_token'
var CURRENT_CONVERSATION = null;
var SOCKET = null;

var http = function(options){
  var url = options.url;
  var method = options.method || 'GET';
  var callback = options.callback || null;
  var data = options.data || null;
  var auth = options.auth || false;

  var xhr = new XMLHttpRequest();

  xhr.onreadystatechange = function () {
    if (xhr.readyState === 4) {
      if ([201, 200, 204].indexOf(xhr.status) !== -1 && callback) {
        callback(xhr);
      }
    }
  };
  xhr.open(method, url, true);
  if(auth){
    xhr.setRequestHeader("Authorization", "Bearer " + localStorage.getItem(JWT_KEY));
  }

  if(data){
    xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
  }else{
     data = '';
  }
  xhr.send(data);
};


var showSection = function(name){
  document.querySelectorAll('.container .section').forEach(function(el){
    if(name !== el.id){
      el.style.display = 'none';
    }else{
      el.style.display = 'block';
    }
  });
}


var login = function(username, password){
  http({
    url: BASE_URL + '/@login',
    method: 'POST',
    callback: function(response){
      var data = JSON.parse(response.responseText);
      localStorage.setItem(JWT_KEY, data['token']);
      showSection('conversations');
      getConversations();
      startSocket();
    },
    data: JSON.stringify({
      username: username,
      password: password
    })
  });
}

var getConversations = function(){
  http({
    url: BASE_URL + '/@get-conversations',
    auth: true,
    callback: function(response){
      var data = JSON.parse(response.responseText);
      var container = document.querySelector('#conversations ul');
      container.innerHTML = '';
      data.forEach(function(conversation){
        var convObj = new Conversation(conversation);
        container.appendChild(convObj.render());
      });
    }
  });
}

var Conversation = function(data){
  var self = this;
  self.data = data;
  self.messages = [];

  self.render = function(){
    var li = document.createElement('li');
    var a = document.createElement('a');
    a.href = '#';
    li.appendChild(a);
    var title;
    if(self.data.title){
      title = self.data.title;
    }else{
      title = 'Conversation with';
    }
    title += '(' + self.data.users.join(', ') + ')'
    a.innerHTML = title;
    a.addEventListener('click', self.onClick);
    return li;
  };

  self.addMessage = function(message){
    self.messages.push(message);
    self.renderMessages();
  };

  self.loadMessages = function(callbackFunc){
    http({
      url: self.data['@id'] + '/@get-messages',
      auth: true,
      callback: function(response){
        var data = JSON.parse(response.responseText);
        self.messages = data;
        self.renderMessages(callbackFunc)
      }
    });
  }

  self.renderMessages = function(callbackFunc){
    var container = document.querySelector('#conversation ul');
    container.innerHTML = '';
    self.messages.forEach(function(message){
      var messObj = new Message(message);
      container.appendChild(messObj.render());
    });
    if(callbackFunc){
      callbackFunc();
    }
  }

  self.onClick = function(e){
    if(e){
      e.preventDefault();
    }
    self.loadMessages(function(){
      showSection('conversation');

      CURRENT_CONVERSATION = self;
      var newMessage = document.getElementById('new-message-btn');
      newMessage.removeEventListener('click', self.newMessage);
      newMessage.addEventListener('click', self.newMessage);
      var newMessageForm = document.getElementById('new-message-form');
      newMessageForm.removeEventListener('submit', self.newMessage);
      newMessageForm.addEventListener('submit', self.newMessage);
    });
  }

  self.newMessage = function(e){
    e.preventDefault();
    http({
      url: self.data['@id'],
      method: 'POST',
      auth: true,
      data: JSON.stringify({
        '@type': 'Message',
        'text': document.getElementById('new-message').value
      }),
      callback: function(){
        document.getElementById('new-message').value = '';
      }
    });
  };

  return self;
}

var Message = function(data){
  var self = this;
  self.data = data;

  self.render = function(){
    var li = document.createElement('li');
    var date = new Date(self.data.creation_date);
    var message = (self.data.text || '') + ' &mdash; ' + self.data.author + '(' +
      date.toString() + ')';
    li.innerHTML = message;
    return li;
  };

  return self;
}


var loginAction = function(e){
  e.preventDefault();
  var username = document.getElementById('login-username').value;
  var password = document.getElementById('login-password').value;
  login(username, password);
};

var newConversation = function(e){
  e.preventDefault();
  http({
    url: BASE_URL + '/conversations',
    method: 'POST',
    auth: true,
    data: JSON.stringify({
      '@type': 'Conversation',
      'users': [document.getElementById('new-conversation').value]
    }),
    callback: function(){
      document.getElementById('new-conversation').value = '';
      getConversations();
    }
  })
};

var startSocket = function(){
  if(SOCKET !== null){
    SOCKET.close();
  }
  http({
    url: BASE_URL + '/@wstoken',
    auth: true,
    callback: function(response){
      var data = JSON.parse(response.responseText);
      var url = BASE_URL + '/@conversate?ws_token=' + data['token'];
      SOCKET = new WebSocket(url.replace('http://', 'ws://'));

      SOCKET.onopen = function(e){
      };
      SOCKET.onmessage = function(msg){
        var data = JSON.parse(msg.data);
        if(CURRENT_CONVERSATION.data.id == data.conversation_id){
          CURRENT_CONVERSATION.addMessage(data);
        }
      };
      SOCKET.onclose = function(e){
      };

      SOCKET.onerror = function(e){
      };
    }
  });
}

document.querySelector('#login .button').addEventListener('click', loginAction);
document.querySelector('#login form').addEventListener('submit', loginAction);

document.querySelectorAll('.menu .item').forEach(function(el){
  el.addEventListener('click', function(e){
    e.preventDefault();
    showSection(e.target.attributes.section.value);
  });
});

document.getElementById('new-conversation-btn').addEventListener('click', newConversation);
document.getElementById('new-conversation-form').addEventListener('submit', newConversation);


if(localStorage.getItem(JWT_KEY)){
  showSection('conversations');
  getConversations();
  startSocket();
}
