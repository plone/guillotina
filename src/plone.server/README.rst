Asyncio and ZODB
================

The official instruction is to just keep using worker threads for all ZODB accessing application code as usual.

This sandbox, however, experiments using single ZODB connection asynchronously so that each
request still has its own transaction manager independently form each other.

Compromises
----------- 

* Frame inspection magic to resolve the current request when object registered for
  transaction. Persistent object API is so implicit that request cannot be
  passed explicitly.

* No MVCC. ZODB relies on single active transaction per each ZODB connection and cache for MVCC.
  Once multiple concurrent transactions see the same connection cache, no MVCC can be guaranteed.
  
* Manual locking for modified objects required. Because multiple concurrent transaction see the
  same object instances in memory, each modified object is only registered for the first
  modifying transaction. To prevent modifying object already registered for another transaction,
  manual locking in code is required.
  
* ... (probably weird conflicts may happend) 
