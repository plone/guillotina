CHANGELOG
=========

5.0.0 (unreleased)
------------------

- Rename `IWriter.parent_id` to `IWriter.parent_uid`

- Rename `guillotina.db.oid` to `guillotina.db.uid`

- Rename `oid_generate` setting to `uid_generator`

- Rename `BaseObject._p_register` -> `BaseObject.register`

- Rename `BaseObject._p_serial` -> `BaseObject.__serial__`

- Rename `BaseObject._p_oid` -> `BaseObject.__uuid__`

- Rename `BaseObject._p_jar` -> `BaseObject.__txn__`

- separate transaction from request object

- rename `guillotina.transactions.managed_transaction` to `guillotina.transactions.transaction`
