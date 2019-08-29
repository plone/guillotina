# Mailer

`guillotina` provides out of the box mailer utilities


## Configuration

```yaml
applications:
- guillotina.contrib.mailer
mailer:
  default_sender: foo@bar.com
  endpoints:
    default:
      type: smtp
      host: localhost
      port: 25
  utility: guillotina.contrib.mailer.utility.PrintingMailerUtility
```

Available utilities:
- `guillotina.contrib.mailer.utility.MailerUtility`
- `guillotina.contrib.mailer.utility.PrintingMailerUtility`
- `guillotina.contrib.mailer.utility.TestMailerUtility`


## Usage

```python
from guillotina.component import query_utility
from guillotina_mailer.interfaces import IMailer
mailer = query_utility(IMailer)
await mailer.send(recipient='john@doe.com', subject='This is my subject', text='Body of email')
```