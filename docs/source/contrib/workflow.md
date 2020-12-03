# Workflows

`guillotina` provides out of the box workflows for security management on content.

## Configuration

There are two main global configuration sections:

```yaml
workflows:
    myworkflow:
        # Initial state of the workflow
        initial_state: private
        states:
            # Private state
            private:
                # Possible actions from private state
                actions:
                    presentar:
                        title: Publicar
                        # Destination state
                        to: publicat
                        # Guard to execute state change
                        check_permission: guillotina.ModifyContent
                # When the content is at this state this permissions
                # should be applied
                set_permission:
                    # Role permission relation
                    roleperm:
                    - setting: Unset
                        role: guillotina.Member
                        permission: guillotina.ViewContent
                    - setting: Unset
                        role: guillotina.Member
                        permission: guillotina.AccessContent
                    - setting: Unset
                        role: guillotina.Member
                        permission: guillotina.AddContent
            publicat:
                actions:
                    presentar:
                        title: Privat
                        to: private
                        check_permissione: guillotina.ModifyContent
                set_permission:
                    roleperm:
                    - setting: AllowSingle
                      role: guillotina.Member
                      permission: guillotina.ViewContent
                    - setting: AllowSingle
                      role: guillotina.Member
                      permission: guillotina.AccessContent
                    - setting: AllowSingle
                      role: guillotina.Member
                      permission: guillotina.AddContent
workflows_content:
    mypackage.interfaces.IMyContentInterface: myworkflow
    mypackage.interfaces.IMyOtherContentInterface: guillotina_basic
```

## Defined workflows

- guillotina_basic: public and private states
- guillotina_private: only private
- guillotina_simple: basic review process
