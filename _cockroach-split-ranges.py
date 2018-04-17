import argparse
import asyncio
import asyncpg


parser = argparse.ArgumentParser()
parser.add_argument(
    '--connection', default='postgresql://root@localhost:26257/guillotina?sslmode=disable')
parser.add_argument('--segments', type=int, default=50)

async def run():
    args = parser.parse_args()
    conn = await asyncpg.connect(args.connection)

    count = (await conn.fetch('select count(*) from objects;'))[0][0]
    print(f'{count} total objects')
    keys = []
    ids = []
    for idx in range(args.segments - 1):
        offset = round((count / args.segments) * (idx + 1))
        print(f'getting offset {offset}')
        keys.append((await conn.fetch(
            f'select zoid from objects order by zoid limit 1 offset {offset};'))[0][0])
        ids.append((await conn.fetch(
            f'select id from objects order by id limit 1 offset {offset};'))[0][0])

    print(f'splitting on keys: {keys}')
    sql = 'ALTER TABLE objects SPLIT AT VALUES {};'.format(
        ', '.join([f"('{k}')" for k in keys])
    )
    print(f'Running SQL: {sql}')
    await conn.execute(sql)

    sql = 'ALTER INDEX objects@object_of SPLIT AT VALUES {};'.format(
        ', '.join([f"('{k}')" for k in keys])
    )
    print(f'Running SQL: {sql}')
    await conn.execute(sql)

    sql = 'ALTER INDEX objects@object_parent SPLIT AT VALUES {};'.format(
        ', '.join([f"('{k}')" for k in keys])
    )
    print(f'Running SQL: {sql}')
    await conn.execute(sql)

    sql = 'ALTER INDEX objects@object_id SPLIT AT VALUES {};'.format(
        ', '.join([f"('{k}')" for k in ids])
    )
    print(f'Running SQL: {sql}')
    await conn.execute(sql)

if __name__ == '__main__':
    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(run())
