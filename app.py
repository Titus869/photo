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
        # 用户表
        c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
        ''')
        # 分类表 (已更新，包含 user_id)
        c.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            UNIQUE(name, user_id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        ''')
        # 图片表
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

# 确保上传文件夹存在
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/')
def index():
    return "Hello, Flask!"

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'success': False, 'message': '用户名或密码不能为空'})

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ?', (username,))
        if c.fetchone():
            return jsonify({'success': False, 'message': '用户已存在'})

        c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
        conn.commit()
    return jsonify({'success': True, 'message': '注册成功'})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'success': False, 'message': '用户名或密码不能为空'})

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('SELECT id, username FROM users WHERE username = ? AND password = ?', (username, password))
        user = c.fetchone()
        if user:
            session['user_id'] = user[0] # 存储用户ID到session
            session['username'] = user[1] # 存储用户名到session
            return jsonify({'success': True, 'message': '登录成功', 'username': user[1]})
        else:
            return jsonify({'success': False, 'message': '用户名或密码错误'})

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return jsonify({'success': True, 'message': '已登出'})

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/add_category', methods=['POST'])
def add_category():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '未登录'})

    user_id = session['user_id'] # Get user_id from session
    data = request.get_json()
    new_category = data.get('category')

    if not new_category:
        return jsonify({'success': False, 'message': '分类名称不能为空'})

    try:
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            # 检查是否已存在该用户下的同名分类
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

    user_id = session['user_id'] # Get user_id from session
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        # Filter categories by user_id
        c.execute('SELECT name FROM categories WHERE user_id=?', (user_id,))
        rows = c.fetchall()
        category_list = [row[0] for row in rows]

    return jsonify({'success': True, 'categories': category_list})

@app.route('/delete_category', methods=['POST'])
def delete_category():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '未登录'})

    user_id = session['user_id'] # Get user_id from session
    username = session['username'] # Get username from session for image deletion
    data = request.get_json()
    category = data.get('category')
    if not category:
        return jsonify({'success': False, 'message': '未指定分类'})

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        # Delete category only if it belongs to the current user
        c.execute('DELETE FROM categories WHERE name=? AND user_id=?', (category, user_id))
        # Delete images associated with this category AND user
        c.execute('DELETE FROM images WHERE category=? AND user=?', (category, username))
        conn.commit()

    return jsonify({'success': True, 'message': '分类已删除'})

@app.route('/upload_image', methods=['POST'])
def upload_image():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '未登录'})

    if 'image' not in request.files:
        return jsonify({'success': False, 'message': '没有图片文件'})

    file = request.files['image']
    category = request.form.get('category')
    username = session.get('username')

    if file.filename == '':
        return jsonify({'success': False, 'message': '文件名为空'})
    if not category:
        return jsonify({'success': False, 'message': '分类未指定'})
    if not username:
        return jsonify({'success': False, 'message': '用户信息缺失'})

    original_filename = secure_filename(file.filename)
    name_without_ext, file_extension = os.path.splitext(original_filename)

    # 检查并生成唯一文件名
    counter = 0
    new_filename = original_filename
    while True:
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            # 检查数据库中是否存在同名文件（对于当前用户和分类）
            c.execute('SELECT COUNT(*) FROM images WHERE user=? AND category=? AND filename=?',
                      (username, category, new_filename))
            count = c.fetchone()[0]

            if count == 0:
                # 如果文件名不存在，则找到一个唯一的文件名
                break
            else:
                # 如果文件名已存在，尝试下一个带序号的名称
                counter += 1
                new_filename = f"{name_without_ext}({counter}){file_extension}"

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
    file.save(filepath)

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('INSERT INTO images (user, category, filename, filepath) VALUES (?, ?, ?, ?)',
                  (username, category, new_filename, new_filename)) # 注意这里 filepath 存储的是仅文件名
        conn.commit()

    return jsonify({'success': True, 'message': '图片上传成功'})


@app.route('/get_images')
def get_images():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '未登录'})

    user = session.get('username') # Get username from session
    category = request.args.get('category')
    if not category:
        return jsonify({'success': False, 'message': '未指定分类'})

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        # Query images for the specific category AND user
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
    filepath = data.get('filepath') # 这里 filepath 实际上是存储在数据库中的文件名
    filename = data.get('filename')
    comment = data.get('comment')

    if not filepath or not filename:
        return jsonify({'success': False, 'message': '参数缺失'})

    # 检查该文件是否属于当前用户
    username = session.get('username')
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM images WHERE filepath=? AND user=?', (filepath, username))
        if c.fetchone()[0] == 0:
            return jsonify({'success': False, 'message': '无权修改此图片'})

        # 在更新文件名之前，需要考虑新文件名是否与用户在该分类下的其他图片冲突
        # 简化处理：这里假设只更新 comment，不更新 filename。
        # 如果要允许更新 filename，需要在这里加入与上传图片类似的重命名逻辑，
        # 并且还要处理旧文件和新文件的物理存储。
        # 对于当前需求，我们只允许更新 comment。
        c.execute('UPDATE images SET filename=?, comment=? WHERE filepath=? AND user=?', (filename, comment, filepath, username))
        conn.commit()

    return jsonify({'success': True, 'message': '更新成功'})

@app.route('/delete_image', methods=['POST'])
def delete_image():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '未登录'})

    data = request.json
    filepath = data.get('filepath') # 这里 filepath 实际上是存储在数据库中的文件名
    if not filepath:
        return jsonify({'success': False, 'message': '参数缺失'})

    username = session.get('username')
    # 删除数据库记录
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        # 确保只删除属于当前用户的图片
        c.execute('SELECT filepath FROM images WHERE filepath=? AND user=?', (filepath, username))
        image_record = c.fetchone()

        if not image_record:
            return jsonify({'success': False, 'message': '无权删除此图片或图片不存在'})

        c.execute('DELETE FROM images WHERE filepath=? AND user=?', (filepath, username))
        conn.commit()

        # 删除物理文件
        file_path_on_disk = os.path.join(app.config['UPLOAD_FOLDER'], filepath)
        if os.path.exists(file_path_on_disk):
            os.remove(file_path_on_disk)

    return jsonify({'success': True, 'message': '图片已删除'})

if __name__ == '__main__':
    init_db()
    app.run(debug=True)