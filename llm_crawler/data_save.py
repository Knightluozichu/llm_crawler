import sqlite3

class JobDatabase:
    def __init__(self, db_name='job_database.db'):
        self.db_name = db_name
        # self.table_name = table_name
        
    def connect(self):
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
        
    def close(self):
        self.cursor.close()
        self.conn.close()
        
    def create_table(self, table_name):
        self.connect()
        self.cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position_name TEXT,
                company_name TEXT,
                salary TEXT,
                work_city TEXT,
                work_exp TEXT,
                education TEXT,
                company_size TEXT,
                company_type TEXT,
                industry TEXT,
                position_url TEXT,
                job_summary TEXT,
                welfare TEXT,
                salary_count INTEGER
            )
        ''')
        self.conn.commit()
        self.close()
        
    def insert_job(self, table_name, position_name, company_name, salary, work_city, work_exp, 
                  education, company_size, company_type, industry, position_url, 
                  job_summary, welfare, salary_count):
        self.connect()
        self.cursor.execute(f'''
            INSERT INTO {table_name} (position_name, company_name, salary, work_city, work_exp,
                            education, company_size, company_type, industry, position_url,
                            job_summary, welfare, salary_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (position_name, company_name, salary, work_city, work_exp,
              education, company_size, company_type, industry, position_url,
              job_summary, welfare, salary_count))
        self.conn.commit()
        self.close()
        
    def get_table_names(self):
        """获取数据库中所有表名"""
        try:
            self.connect()
            # 排除 sqlite 系统表
            self.cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' 
                AND name NOT LIKE 'sqlite_%'
            """)
            tables = [table[0] for table in self.cursor.fetchall()]
            self.close()
            return tables
        except Exception as e:
            print(f"获取表名失败: {str(e)}")
            return []

    def get_table_data(self, table_name):
        """获取指定表的所有数据"""
        try:
            self.connect()
            # 使用参数化查询避免 SQL 注入
            self.cursor.execute("SELECT * FROM `{}`".format(table_name))
            data = self.cursor.fetchall()
            self.close()
            return data
        except Exception as e:
            print(f"获取表数据失败: {str(e)}")
            return []
        
    def update_job(self, job_id, position_name, company_name, salary, work_city, 
                   work_exp, education, company_size, company_type, industry, 
                   position_url, job_summary, welfare, salary_count):
        self.connect()
        self.cursor.execute(f'''
            UPDATE {self.table_name}
            SET position_name=?, company_name=?, salary=?, work_city=?, work_exp=?,
                education=?, company_size=?, company_type=?, industry=?, position_url=?,
                job_summary=?, welfare=?, salary_count=?
            WHERE id=?
        ''', (position_name, company_name, salary, work_city, work_exp,
              education, company_size, company_type, industry, position_url,
              job_summary, welfare, salary_count, job_id))
        self.conn.commit()
        self.close()
        
    def delete_job(self, job_id):
        self.connect()
        self.cursor.execute(f'DELETE FROM {self.table_name} WHERE id=?', (job_id,))
        self.conn.commit()
        self.close()
    
    def get_random_job(self):
        self.connect()
        self.cursor.execute(f'SELECT * FROM {self.table_name} ORDER BY RANDOM() LIMIT 1')
        job = self.cursor.fetchone()
        self.close()
        return job