import sqlite3
import bcrypt

DATABASE_FILE = 'teacher_app.db'

def get_db_connection():
    """ 建立並返回一個帶有 row_factory 的資料庫連線，以便將結果作為字典返回 """
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# --- 使用者與密碼相關 ---

def verify_password(password):
    """ 驗證密碼是否正確 """
    conn = get_db_connection()
    setting = conn.execute('SELECT hashed_password FROM settings WHERE id = 1').fetchone()
    conn.close()
    if setting:
        return bcrypt.checkpw(password.encode('utf-8'), setting['hashed_password'])
    return False

def update_password(new_password):
    """ 更新使用者密碼 """
    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
    conn = get_db_connection()
    conn.execute('UPDATE settings SET hashed_password = ? WHERE id = 1', (hashed_password,))
    conn.commit()
    conn.close()

# --- 學生資料相關 ---

def clear_students_data():
    """ 清空所有學生資料，用於重新匯入 """
    conn = get_db_connection()
    # 由於有外鍵關聯，需要先刪除關聯的資料
    conn.execute('DELETE FROM grades')
    conn.execute('DELETE FROM attendance')
    conn.execute('DELETE FROM students')
    conn.commit()
    conn.close()

def add_student(student_id, name, class_name, account):
    """ 新增單一學生資料 """
    conn = get_db_connection()
    conn.execute('INSERT INTO students (student_id, name, class_name, account) VALUES (?, ?, ?, ?)',
                 (student_id, name, class_name, account))
    conn.commit()
    conn.close()
    
def get_all_classes():
    """ 取得所有不重複的班級名稱 """
    conn = get_db_connection()
    classes = conn.execute('SELECT DISTINCT class_name FROM students ORDER BY class_name').fetchall()
    conn.close()
    return [c['class_name'] for c in classes]

def get_students_by_class(class_name):
    """ 根據班級名稱取得所有學生，並按座位順序排列 """
    conn = get_db_connection()
    students = conn.execute('SELECT * FROM students WHERE class_name = ? ORDER BY seat_order, student_id', 
                            (class_name,)).fetchall()
    conn.close()
    return students

def update_seat_order(student_db_id, new_order):
    """ 更新學生的座位順序 """
    conn = get_db_connection()
    conn.execute('UPDATE students SET seat_order = ? WHERE id = ?', (new_order, student_db_id))
    conn.commit()
    conn.close()


# --- 成績相關 (此處僅為範例，需擴充) ---

def add_grade_item(name, type, parent_id=None, percentage=None):
    """ 新增成績項目 """
    conn = get_db_connection()
    conn.execute('INSERT INTO grade_items (name, type, parent_id, percentage) VALUES (?, ?, ?, ?)',
                 (name, type, parent_id, percentage))
    conn.commit()
    conn.close()

def get_grade_items():
    """ 取得所有成績項目 """
    conn = get_db_connection()
    items = conn.execute('SELECT * FROM grade_items ORDER BY type, name').fetchall()
    conn.close()
    return items
    
# --- 點名與日常表現相關 (此處僅為範例，需擴充) ---

def record_attendance(student_db_id, date, status, notes=""):
    """ 紀錄單一學生的出缺席狀況 """
    conn = get_db_connection()
    # 檢查當天是否已有紀錄，若有則更新，否則新增
    existing = conn.execute('SELECT id FROM attendance WHERE student_db_id = ? AND date = ?', (student_db_id, date)).fetchone()
    if existing:
        conn.execute('UPDATE attendance SET status = ?, daily_performance_notes = ? WHERE id = ?', (status, notes, existing['id']))
    else:
        conn.execute('INSERT INTO attendance (student_db_id, date, status, daily_performance_notes) VALUES (?, ?, ?, ?)',
                     (student_db_id, date, status, notes))
    conn.commit()
    conn.close()

# 你可以在此繼續添加更多與資料庫互動的函式...

