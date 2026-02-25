# Security Model

## What it is
Guillotina applies hierarchical, role/permission-based security over the object
model.

## Why it matters
Security decisions determine who can read, modify, and manage content at each
context path.

## How it works
- Users and groups hold roles.
- Roles map to permissions.
- Permission resolution is contextual and can inherit through the object tree.

## Minimal example
```shell
curl -u root:root http://localhost:8080/db/container/@users
```

## Common failures
- Assigning roles at the wrong level causes overexposure or accidental denial.
- Assuming global roles override contextual permission checks.

## Related pages
- {doc}`object-model`
- {doc}`traversal`
- {doc}`../developer/security`
