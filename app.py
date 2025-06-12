from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # 必须设置，用于 session 加密
CORS(app, supports_credentials=True)  # 支持跨域携带 cookie

DB_NAME = 'mydata.db'

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        # 用户表 (无变化)
        c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
        ''')
        # 分类表 - 添加 user_id 列
        c.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            user_id INTEGER NOT NULL, -- 添加 user_id 列
            UNIQUE(name, user_id), -- 确保每个用户下的分类名称是唯一的
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        ''')
        # 图片表 (无变化，因为已经有 'user' 列)
        c.execute('''
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT NOT NULL,
            category TEXT NOT NULL,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            comment TEXT
        )
        ''')
        conn.commit()

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 允许的图片扩展名
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'success': False, 'message': '用户名或密码不能为空'})

    try:
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
        return jsonify({'success': True, 'message': '注册成功'})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': '用户名已存在'})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'success': False, 'message': '用户名或密码不能为空'})

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username=? AND password=?', (username, password))
        user = c.fetchone()

    if user:
        # 登录成功，写入 session
        session['user_id'] = user[0]
        session['username'] = user[1]
        return jsonify({'success': True, 'message': '登录成功'})
    else:
        return jsonify({'success': False, 'message': '用户名或密码错误'})

@app.route('/current_user')
def current_user():
    if 'user_id' in session:
        return jsonify({'logged_in': True, 'user_id': session['user_id'], 'username': session['username']})
    else:
        return jsonify({'logged_in': False})

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True, 'message': '已退出登录'})

@app.route('/add_category', methods=['POST'])
def add_category():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '未登录'})

    user_id = session['user_id'] # 从会话中获取 user_id
    data = request.get_json()
    new_category = data.get('category')

    if not new_category:
        return jsonify({'success': False, 'message': '分类名称不能为空'})

    try:
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            # 检查该用户下是否已存在同名分类
            c.execute('SELECT * FROM categories WHERE name=? AND user_id=?', (new_category, user_id))
            if c.fetchone():
                return jsonify({'success': False, 'message': '分类已存在'})

            c.execute('INSERT INTO categories (name, user_id) VALUES (?, ?)', (new_category, user_id))
            conn.commit()
        return jsonify({'success': True, 'message': '分类添加成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': '数据库错误: ' + str(e)})

@app.route('/categories')
def get_categories():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '未登录'})

    user_id = session['user_id'] # 从会话中获取 user_id
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        # 按 user_id 过滤分类
        c.execute('SELECT name FROM categories WHERE user_id=?', (user_id,))
        rows = c.fetchall()
        category_list = [row[0] for row in rows]

    return jsonify({'success': True, 'categories': category_list})

@app.route('/delete_category', methods=['POST'])
def delete_category():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '未登录'})

    user_id = session['user_id'] # 从会话中获取 user_id
    username = session['username'] # 从会话中获取 username 以便删除图片
    data = request.get_json()
    category = data.get('category')
    if not category:
        return jsonify({'success': False, 'message': '未指定分类'})

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        # 仅当分类属于当前用户时才删除
        c.execute('DELETE FROM categories WHERE name=? AND user_id=?', (category, user_id))
        # 删除与此分类和用户关联的图片
        c.execute('DELETE FROM images WHERE category=? AND user=?', (category, username))
        conn.commit()

    return jsonify({'success': True, 'message': '分类已删除'})


@app.route('/upload_image', methods=['POST'])
def upload_image():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '未登录'})

    user = session.get('username')
    category = request.form.get('category')
    if not category:
        return jsonify({'success': False, 'message': '未指定分类'})

    if 'image' not in request.files:
        return jsonify({'success': False, 'message': '未找到图片文件'})

    file = request.files['image']
    if file.filename == '':
        return jsonify({'success': False, 'message': '未选择文件'})

    if not allowed_file(file.filename):
        return jsonify({'success': False, 'message': '不支持的文件格式'})

    filename = secure_filename(file.filename)

    # 构造用户目录和分类目录
    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], user)
    category_folder = os.path.join(user_folder, category)
    os.makedirs(category_folder, exist_ok=True)

    file_path = os.path.join(category_folder, filename)
    file.save(file_path)

    # 数据库存储路径用相对路径方便前端访问
    relative_path = f"{user}/{category}/{filename}"

    # 插入数据库（假设已有images表，字段至少有：id, category, filename, filepath, comment, user）
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        # 这里暂时空注释
        c.execute('''
          INSERT INTO images (user, category, filename, filepath, comment) 
          VALUES (?, ?, ?, ?, ?)
        ''', (user, category, filename, relative_path, ''))
        conn.commit()

    return jsonify({'success': True, 'message': '上传成功'})

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/get_images')
def get_images():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '未登录'})

    user = session.get('username') # 从会话中获取 username
    category = request.args.get('category')
    if not category:
        return jsonify({'success': False, 'message': '未指定分类'})

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        # 查询特定分类和用户下的图片
        c.execute('SELECT filepath, filename, comment FROM images WHERE category=? AND user=?', (category, user))
        rows = c.fetchall()

    images = []
    for row in rows:
        images.append({
            'url': f'/uploads/{row[0]}',  # 拼接成访问路径
            'filename': row[1],
            'comment': row[2]
        })

    return jsonify({'success': True, 'images': images})

@app.route('/update_image', methods=['POST'])
def update_image():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '未登录'})

    data = request.json
    filepath = data.get('filepath')
    filename = data.get('filename')
    comment = data.get('comment')

    if not filepath or not filename:
        return jsonify({'success': False, 'message': '参数缺失'})

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('UPDATE images SET filename=?, comment=? WHERE filepath=?', (filename, comment, filepath))
        conn.commit()

    return jsonify({'success': True, 'message': '更新成功'})

@app.route('/delete_image', methods=['POST'])
def delete_image():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '未登录'})

    data = request.json
    filepath = data.get('filepath')
    if not filepath:
        return jsonify({'success': False, 'message': '参数缺失'})

    # 删除数据库记录
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('DELETE FROM images WHERE filepath=?', (filepath,))
        conn.commit()

    # 删除实际图片文件
    try:
        os.remove(os.path.join(UPLOAD_FOLDER, filepath))
    except Exception as e:
        print('删除文件失败：', e)

    return jsonify({'success': True, 'message': '图片已删除'})


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
