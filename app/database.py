import asyncpg

class Database:
    def __init__(self, db_url):
        self.db_url = db_url
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(self.db_url)

    async def create_table(self):
        async with self.pool.acquire() as connection:
            # Сначала проверяем существование таблицы
            table_exists = await connection.fetchval(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users')"
            )
            
            if table_exists:
                # Проверяем наличие столбцов
                for column in ['username', 'club_points', 'credit_rating']:
                    column_exists = await connection.fetchval(
                        f"SELECT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'users' AND column_name = '{column}')"
                    )
                    if not column_exists:
                        if column == 'username':
                            await connection.execute('ALTER TABLE users ADD COLUMN username VARCHAR(100)')
                        else:
                            await connection.execute(f'ALTER TABLE users ADD COLUMN {column} INTEGER DEFAULT 0')
            else:
                # Создаем таблицу с правильной структурой
                await connection.execute('''
                    CREATE TABLE users (
                        tg_id BIGINT PRIMARY KEY,
                        username VARCHAR(100),
                        club_points INTEGER DEFAULT 0,
                        credit_rating INTEGER DEFAULT 0
                    )
                ''')

    async def get_user(self, tg_id):
        async with self.pool.acquire() as connection:
            return await connection.fetchrow(
                'SELECT * FROM users WHERE tg_id = $1', tg_id
            )

    async def get_user_by_username(self, username):
        async with self.pool.acquire() as connection:
            return await connection.fetchrow(
                'SELECT * FROM users WHERE username = $1', username
            )

    async def create_user(self, tg_id, username):
        async with self.pool.acquire() as connection:
            # Проверяем, существует ли пользователь
            user_exists = await connection.fetchval(
                'SELECT EXISTS (SELECT 1 FROM users WHERE tg_id = $1)', tg_id
            )
            
            if user_exists:
                # Обновляем username если пользователь существует
                await connection.execute(
                    'UPDATE users SET username = $1 WHERE tg_id = $2',
                    username, tg_id
                )
            else:
                # Создаем нового пользователя со всеми полями
                await connection.execute(
                    'INSERT INTO users (tg_id, username, club_points, credit_rating) VALUES ($1, $2, 0, 0)',
                    tg_id, username
                )

    async def update_club_points(self, tg_id, points):
        async with self.pool.acquire() as connection:
            await connection.execute(
                'UPDATE users SET club_points = $1 WHERE tg_id = $2',
                points, tg_id
            )

    async def update_credit_rating(self, tg_id, rating):
        async with self.pool.acquire() as connection:
            await connection.execute(
                'UPDATE users SET credit_rating = $1 WHERE tg_id = $2',
                rating, tg_id
            )

    async def get_all_users(self):
        async with self.pool.acquire() as connection:
            return await connection.fetch('SELECT * FROM users ORDER BY club_points DESC')