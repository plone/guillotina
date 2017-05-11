from guillotina.db.interfaces import ILockingStrategy


async def lock_object(obj):
    trns = obj._p_jar
    if (trns is not None and not obj.__locked__ and
            ILockingStrategy.providedBy(trns._strategy)):
        await trns._strategy.lock(obj)


async def unlock_object(obj):
    trns = obj._p_jar
    if (trns is not None and obj.__locked__ and
            ILockingStrategy.providedBy(trns._strategy)):
        await trns._strategy.unlock(obj)
