from datetime import datetime
from dateutil import tz

import time


ITERATIONS = 1000000


# ----------------------------------------------------
# Measure performance of timezone usage
#
# Results:
#  Test local timezone usage
#  Done with 1000000 in 46.29461884498596 seconds
#  Test utz timezone usage
#  Done with 1000000 in 0.9611668586730957 seconds
#  Test no timezone
#  Done with 1000000 in 0.5719988346099854 seconds
#  Test no timezone utcnow()
#  Done with 1000000 in 0.29074907302856445 seconds
#
# Lessons:
#   - tzlocal is insanely slow
#   - the more utz you go, the faster
#   - fastest would be utcnow() naive objects
# ----------------------------------------------------


async def run1():
    print('Test local timezone usage')
    start = time.time()
    for _ in range(ITERATIONS):
        datetime.now(tz=tz.tzlocal())
    end = time.time()
    print(f'Done with {ITERATIONS} in {end - start} seconds')


async def run2():
    print('Test utz timezone usage')
    start = time.time()
    for _ in range(ITERATIONS):
        datetime.now(tz=tz.tzutc())
    end = time.time()
    print(f'Done with {ITERATIONS} in {end - start} seconds')


async def run3():
    print('Test no timezone now()')
    start = time.time()
    for _ in range(ITERATIONS):
        datetime.now()
    end = time.time()
    print(f'Done with {ITERATIONS} in {end - start} seconds')


async def run4():
    print('Test no timezone utcnow()')
    start = time.time()
    for _ in range(ITERATIONS):
        datetime.utcnow()
    end = time.time()
    print(f'Done with {ITERATIONS} in {end - start} seconds')


async def run():
    await run1()
    await run2()
    await run3()
    await run4()
