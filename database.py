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

def get_all_students_for_class(class_name):
    """ 根據班級名稱取得所有學生，按學號排序 """
    conn = get_db_connection()
    students = conn.execute(
        'SELECT * FROM students WHERE class_name = ? ORDER BY student_id',
        (class_name,)
    ).fetchall()
    conn.close()
    return students

def batch_update_seat_positions(assignments):
    """
    批次更新學生座位.
    assignments 是一個元組列表: (seat_row, seat_col, student_db_id)
    """
    conn = get_db_connection()
    conn.executemany('UPDATE students SET seat_row = ?, seat_col = ? WHERE id = ?', assignments)
    conn.commit()
    conn.close()

# --- 班級設定相關 ---

def get_class_settings(class_name):
    """ 取得班級設定 """
    conn = get_db_connection()
    settings = conn.execute('SELECT * FROM class_settings WHERE class_name = ?', (class_name,)).fetchone()
    if not settings:
        # 如果沒有設定，就建立一個預設的
        conn.execute('INSERT INTO class_settings (class_name, seating_layout) VALUES (?, ?)', (class_name, '6x6'))
        conn.commit()
        settings = conn.execute('SELECT * FROM class_settings WHERE class_name = ?', (class_name,)).fetchone()
    conn.close()
    return settings

def update_class_layout(class_name, layout):
    """ 更新班級的座位表佈局 """
    conn = get_db_connection()
    # 切換佈局時，同時清除所有座位安排，因為位置無法轉移
    conn.execute('UPDATE students SET seat_row = NULL, seat_col = NULL WHERE class_name = ?', (class_name,))
    conn.execute('UPDATE class_settings SET seating_layout = ? WHERE class_name = ?', (layout, class_name))
    conn.commit()
    conn.close()


# --- 成績相關 ---

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

def get_student_grades_by_item(student_db_ids, item_id):
    """ 根據學生ID列表和成績項目ID取得成績 """
    conn = get_db_connection()
    # 建立一個 {student_id: score} 的字典
    grades = {}
    if not student_db_ids:
        return grades
        
    placeholders = ','.join('?' for _ in student_db_ids)
    query = f'SELECT student_db_id, score FROM grades WHERE item_id = ? AND student_db_id IN ({placeholders})'
    
    params = [item_id] + student_db_ids
    results = conn.execute(query, params).fetchall()
    
    for row in results:
        grades[row['student_db_id']] = row['score']
        
    conn.close()
    return grades

def update_or_insert_grade(student_db_id, item_id, score):
    """ 新增或更新一個學生的成績 """
    conn = get_db_connection()
    # 檢查成績是否已存在
    existing = conn.execute('SELECT id FROM grades WHERE student_db_id = ? AND item_id = ?', 
                            (student_db_id, item_id)).fetchone()
    
    if score == '' or score is None:
        # 如果分數是空的，則刪除紀錄
        if existing:
            conn.execute('DELETE FROM grades WHERE id = ?', (existing['id'],))
    else:
        if existing:
            conn.execute('UPDATE grades SET score = ? WHERE id = ?', (score, existing['id']))
        else:
            conn.execute('INSERT INTO grades (student_db_id, item_id, score) VALUES (?, ?, ?)',
                         (student_db_id, item_id, score))
    conn.commit()
    conn.close()
    
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

