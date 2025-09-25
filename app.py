import sys
import os
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename
from waitress import serve
import database as db

# --- 應用程式設定 ---
# 判斷資源路徑 (適用於打包成 .exe)
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.abspath(".")

# 設定 Flask 的 template 和 static 資料夾路徑
template_folder = os.path.join(base_path, 'templates')
static_folder = os.path.join(base_path, 'static')
app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
app.secret_key = 'your_very_secret_key_for_session' # 用於 session 加密

# 設定上傳資料夾
UPLOAD_FOLDER = os.path.join(base_path, 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# --- 路由 (Routes) ---

@app.before_request
def require_login():
    """ 檢查使用者是否已登入 """
    allowed_routes = ['login', 'static']
    if 'logged_in' not in session and request.endpoint not in allowed_routes:
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """ 登入頁面 """
    if request.method == 'POST':
        password = request.form['password']
        if db.verify_password(password):
            session['logged_in'] = True
            flash('登入成功！', 'success')
            return redirect(url_for('index'))
        else:
            flash('密碼錯誤！', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    """ 登出 """
    session.pop('logged_in', None)
    flash('您已成功登出。', 'info')
    return redirect(url_for('login'))

@app.route('/')
def index():
    """ 主頁面，顯示所有班級 """
    classes = db.get_all_classes()
    return render_template('index.html', classes=classes)

@app.route('/class/<class_name>')
def class_dashboard(class_name):
    """ 班級主控台 """
    settings = db.get_class_settings(class_name)
    layout = settings['seating_layout']
    rows, cols = map(int, layout.split('x'))

    students = db.get_all_students_for_class(class_name)
    
    # 如果學生還沒有被排過座位，就進行初始排列
    if students and students[0]['seat_row'] is None:
        all_seats = []
        for r in range(rows):
            for c in range(cols):
                all_seats.append((r, c))
        
        assignments = []
        num_students_to_seat = min(len(students), len(all_seats))
        for i in range(num_students_to_seat):
            student = students[i]
            seat = all_seats[i]
            assignments.append((seat[0], seat[1], student['id']))
        
        if assignments:
            db.batch_update_seat_positions(assignments)
        
        # 重新獲取學生資料以包含座位資訊
        students = db.get_all_students_for_class(class_name)

    # 建立一個二維陣列來代表座位表
    seating_grid = [[None for _ in range(cols)] for _ in range(rows)]
    for student in students:
        if student['seat_row'] is not None and student['seat_col'] is not None:
             # 防止資料庫中的位置超出當前佈局範圍
            if 0 <= student['seat_row'] < rows and 0 <= student['seat_col'] < cols:
                seating_grid[student['seat_row']][student['seat_col']] = dict(student)

    grade_items = db.get_grade_items()
    
    return render_template(
        'class_dashboard.html', 
        class_name=class_name, 
        grade_items=grade_items,
        seating_grid=seating_grid,
        layout=layout,
        students=students
    )

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """ 設定頁面：匯入學生資料、變更密碼 """
    if request.method == 'POST':
        # 處理變更密碼
        if 'new_password' in request.form:
            new_password = request.form['new_password']
            confirm_password = request.form['confirm_password']
            if new_password == confirm_password:
                db.update_password(new_password)
                flash('密碼更新成功！', 'success')
            else:
                flash('兩次輸入的密碼不一致！', 'danger')
        
        # 處理檔案上傳
        if 'student_file' in request.files:
            file = request.files['student_file']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                # 處理匯入邏輯
                try:
                    df = pd.read_excel(filepath)
                    # 假設 Excel 有 '學號', '姓名', '班級', '帳號' 四個欄位
                    required_columns = ['學號', '姓名', '班級', '帳號']
                    if all(col in df.columns for col in required_columns):
                        db.clear_students_data() # 清空舊資料
                        for index, row in df.iterrows():
                            db.add_student(str(row['學號']), row['姓名'], row['班級'], str(row.get('帳號', '')))
                        flash('學生資料匯入成功！', 'success')
                    else:
                        flash(f'Excel 檔案缺少必要的欄位 ({", ".join(required_columns)})！', 'danger')
                except Exception as e:
                    flash(f'處理檔案時發生錯誤: {e}', 'danger')
        
        return redirect(url_for('settings'))

    return render_template('settings.html')


# --- API 路由 (用於 JavaScript 互動) ---

@app.route('/api/save_seating_chart', methods=['POST'])
def api_save_seating_chart():
    """ API: 儲存整個座位表 """
    data = request.get_json()
    assignments_data = data.get('assignments')

    if not assignments_data:
        return jsonify({'status': 'error', 'message': '缺少座位資料'}), 400

    assignments_tuples = []
    for assign in assignments_data:
        # 確保所有需要的鍵都存在
        if 'student_id' in assign and 'row' in assign and 'col' in assign:
            assignments_tuples.append((assign['row'], assign['col'], assign['student_id']))
    
    if assignments_tuples:
        db.batch_update_seat_positions(assignments_tuples)

    return jsonify({'status': 'success'})

@app.route('/api/update_layout', methods=['POST'])
def api_update_layout():
    """ API: 更新座位表佈局 """
    data = request.get_json()
    class_name = data.get('class_name')
    layout = data.get('layout')
    if class_name and layout in ['6x6', '8x5']:
        db.update_class_layout(class_name, layout)
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'Invalid data'}), 400

@app.route('/api/grade_items', methods=['GET', 'POST'])
def api_manage_grade_items():
    """ API: 管理成績項目 """
    if request.method == 'POST':
        data = request.get_json()
        name = data.get('name')
        item_type = data.get('type')
        if name and item_type:
            db.add_grade_item(name, item_type)
            return jsonify({'status': 'success', 'message': f'項目 "{name}" 已新增。'})
        return jsonify({'status': 'error', 'message': '缺少名稱或類型。'}), 400
    
    items = db.get_grade_items()
    return jsonify([dict(row) for row in items])

@app.route('/api/grades/<int:item_id>', methods=['GET'])
def api_get_grades(item_id):
    """ API: 根據班級和項目取得成績 """
    class_name = request.args.get('class_name')
    if not class_name:
        return jsonify({'status': 'error', 'message': '未提供班級名稱'}), 400
        
    students = db.get_all_students_for_class(class_name)
    student_ids = [s['id'] for s in students]
    
    grades = db.get_student_grades_by_item(student_ids, item_id)
    
    return jsonify(grades)

@app.route('/api/grades/update', methods=['POST'])
def api_update_grade():
    """ API: 更新單一筆成績 """
    data = request.get_json()
    student_db_id = data.get('student_db_id')
    item_id = data.get('item_id')
    score = data.get('score')
    
    if student_db_id is None or item_id is None:
        return jsonify({'status': 'error', 'message': '缺少學生ID或項目ID'}), 400
        
    try:
        if score is not None and score != '':
            float(score)
        db.update_or_insert_grade(student_db_id, item_id, score)
        return jsonify({'status': 'success'})
    except ValueError:
        return jsonify({'status': 'error', 'message': '分數格式不正確'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# --- 主程式進入點 ---

if __name__ == '__main__':
    # 檢查資料庫是否存在，若否，提示使用者執行 init_db.py
    if not os.path.exists('teacher_app.db'):
        print("="*50)
        print("錯誤：找不到資料庫檔案 'teacher_app.db'。")
        print("請先執行 'python init_db.py' 來初始化資料庫。")
        print("="*50)
    else:
        print("伺服器啟動於 http://127.0.0.1:8080")
        print("請用瀏覽器開啟此網址。")
        serve(app, host='0.0.0.0', port=8080)

