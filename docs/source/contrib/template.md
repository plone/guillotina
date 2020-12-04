# Template

`guillotina` provides out of the box template rendering with Jinja. Its mostly used for emails composition.

## Configuration

```yaml
templates:
- guillotina.contrib.email_validation:templates
```

You can define the relative folder to a python path where templates are allocated.

There is an alpha feature that you can enable content type templates also by defining:

```yaml
template_content_type: True
```

## Usage

```python
from guillotina.contrib.templates.interfaces import IJinjaUtility
from guillotina.component import get_utility
...
render_util = get_utility(IJinjaUtility)
template = await render_util.render(
    template_name,
    **kwargs
)
...
```

It will render the Jinja template found first on the folders defined at the templates global list with the id name template_name and format with the kwargs parameters.
