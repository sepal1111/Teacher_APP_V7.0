import sys
import os
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, session
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
    students = db.get_students_by_class(class_name)
    return render_template('class_dashboard.html', students=students, class_name=class_name)

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

@app.route('/api/update_seat_order', methods=['POST'])
def api_update_seat_order():
    """ API: 更新座位順序 """
    data = request.get_json()
    student_order = data.get('order')
    if student_order:
        for index, student_db_id in enumerate(student_order):
            db.update_seat_order(student_db_id, index)
        return {'status': 'success'}, 200
    return {'status': 'error', 'message': 'Missing order data'}, 400


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

