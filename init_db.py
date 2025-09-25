import sqlite3
import os
import bcrypt

# --- 設定 ---
DATABASE_FILE = 'teacher_app.db'
DEFAULT_PASSWORD = 'password' # 預設密碼

def create_connection():
    """ 建立並返回一個資料庫連線 """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        print(f"成功連線到 SQLite 資料庫: {DATABASE_FILE}")
    except sqlite3.Error as e:
        print(e)
    return conn

def create_table(conn, create_table_sql):
    """ 在資料庫中建立一個資料表 """
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except sqlite3.Error as e:
        print(e)

def setup_database():
    """ 主要的資料庫設定函式 """
    
    # 如果資料庫檔案已存在，先刪除，確保是一個全新的開始
    if os.path.exists(DATABASE_FILE):
        os.remove(DATABASE_FILE)
        print(f"已刪除舊的資料庫檔案: {DATABASE_FILE}")

    conn = create_connection()

    if conn is not None:
        # --- 建立資料表 ---
        
        # 使用者設定表 (只會有單一一筆紀錄)
        sql_create_settings_table = """
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY,
            hashed_password TEXT NOT NULL
        );
        """
        
        # 學生資料表
        sql_create_students_table = """
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            class_name TEXT NOT NULL,
            account TEXT, -- 新增帳號欄位
            seat_order INTEGER DEFAULT 0
        );
        """
        
        # 成績項目表
        sql_create_grade_items_table = """
        CREATE TABLE IF NOT EXISTS grade_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL, -- '平時評量' 或 '定期評量'
            parent_id INTEGER, -- 用於平時評量下的子項目
            percentage REAL, -- 佔比
            FOREIGN KEY (parent_id) REFERENCES grade_items (id)
        );
        """
        
        # 成績紀錄表
        sql_create_grades_table = """
        CREATE TABLE IF NOT EXISTS grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_db_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            score REAL,
            is_retest BOOLEAN DEFAULT 0, -- 是否為補考成績
            FOREIGN KEY (student_db_id) REFERENCES students (id),
            FOREIGN KEY (item_id) REFERENCES grade_items (id)
        );
        """
        
        # 出缺席與日常表現紀錄表
        sql_create_attendance_table = """
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_db_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            status TEXT NOT NULL, -- '出席', '遲到', '事假', '病假', '曠課'
            daily_performance_notes TEXT, -- 日常行為表現文字紀錄
            FOREIGN KEY (student_db_id) REFERENCES students (id)
        );
        """
        
        create_table(conn, sql_create_settings_table)
        create_table(conn, sql_create_students_table)
        create_table(conn, sql_create_grade_items_table)
        create_table(conn, sql_create_grades_table)
        create_table(conn, sql_create_attendance_table)
        
        # --- 插入初始資料 ---
        
        # 插入預設密碼
        hashed_password = bcrypt.hashpw(DEFAULT_PASSWORD.encode('utf-8'), bcrypt.gensalt())
        cursor = conn.cursor()
        cursor.execute("INSERT INTO settings (id, hashed_password) VALUES (?, ?)", (1, hashed_password))
        conn.commit()
        
        print("資料庫初始化完成，並已設定預設密碼。")

        conn.close()
    else:
        print("錯誤！無法建立資料庫連線。")

if __name__ == '__main__':
    setup_database()

