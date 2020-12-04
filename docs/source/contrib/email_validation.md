# Email validation

`guillotina` provides out of the box an email validation system to validate actions with a mail with a link that frontend needs to negotatiate with the API.

Its scalable on defining different actions that need email validation. By default Guillotina provides Register user and Reset password actions email validation.

This addon requires Installing the `email_validation` addon to register the persistent settings on the container.

## Configuration

### Add a new action

You need to define on the config.yaml or package configuration::

```yaml
auth_validation_tasks:
    reset_password:
        schema:
            title: Reset password validation information
            required:
            - password
            type: object
            properties:
                password:
                    type: string
                    widget: password
                    minLength: 6
        executor: guillotina.contrib.email_validation.reset_password
```

This configuration defines the action `reset_password`, which is the schema that will need to be validated on 2nd fase flow and who is the executor of the action after validation.
The executor should be a module with an async `run` function.

### Container configuration

You can configure at interface `guillotina.contrib.email_validation.interfaces.IValidationSettings`:

- validation_template: By default uses `validate.html`
- site_url: Base URL of the frontend
- validation_url: Path URL of the frontend for the validation. `?token=` will be appended to define the validation token.
- site_mails_from: Sender of validation emails

## Flow

In the service you want to start the validation you should then call:

```python
from guillotina.interfaces import IAuthValidationUtility
from guillotina.component import get_utility
from guillotina.api.service import Service
from guillotina import configure

@configure.service(...)
class MyService(Service):
    async def __call__(self):
        ...
        validation_utility = get_utility(IAuthValidationUtility)
        await validation_utility.start(
            as_user=user_id,  # Payload received on the final action runner
            from_user=actual_user.id,  # Payload received on the final action runner
            email=email,  # Who should receive the validation email
            task_description="Reset password",  # This is the email summary
            task_id="reset_password",  # This is the action id
            context_description=self.context.title,  # Context for the mail
            redirect_url=redirect_url,  # After validation redirect url
            data={}  # Base data for the 1rst step validation
        )
        ...
```

Once the mail is sent and the user clicks on the link the frontend can:

- ask for the needed schema at `CONTAINER/@validate_schema/TOKEN`
- render the JSON Schema to ask required extra information to the user
- finally call `CONTAINER/@validate/TOKEN` with the JSON data to finish the validation process which will run the action runner

Action runner should be an async function with:

```python
async def run(token_data, payload):
    # Payload is the data sent by the browser on the @validate endpoint (2nd step validation).
    # Token data is the original data sent on the 1rst step validation.
    #  v_user : as_user from start function
    #  v_task : task_id from start function
    #  v_querier : from_user from start function
    #  v_redirect_url : redirect_url from start function
    #  ... : data from start function

    return {}

```
