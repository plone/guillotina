import asyncpg
import asyncio


async def run():
    # Establish a connection to an existing database named "test"
    # as a "postgres" user.
    conn = await asyncpg.connect('postgresql://root@localhost:26257?sslmode=disable')
    # Execute a statement to create a new table.
    await conn.execute('''CREATE DATABASE guillotina''')


if __name__ == '__main__':
    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(run())
