import os
import uuid
import sqlite3
from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # 必须设置，用于 session 加密
CORS(app, supports_credentials=True)  # 支持跨域携带 cookie

DB_NAME = 'mydata.db'

UPLOAD_FOLDER = 'uploads' # 基础上传目录
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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

    user_id = session['user_id']
    username = session['username'] # 获取当前登录的用户名
    category = request.form.get('category')
    image_file = request.files.get('image')

    if not category or not image_file:
        return jsonify({'success': False, 'message': '参数缺失'})

    if image_file:
        # 原始文件名
        original_filename = secure_filename(image_file.filename)
        # 获取文件扩展名
        file_ext = os.path.splitext(original_filename)[1]
        # 使用 UUID 生成唯一文件名，防止重复
        unique_filename = str(uuid.uuid4()) + file_ext

        # 1. 构建用户和分类的子目录路径
        # secure_filename 同样应用于 category，以防目录名包含非法字符
        user_dir = secure_filename(username)
        category_dir = secure_filename(category)
        
        # 完整的上传目录路径：uploads/username/categoryname/
        target_upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], user_dir, category_dir)

        # 2. 检查并创建目录
        if not os.path.exists(target_upload_dir):
            try:
                os.makedirs(target_upload_dir) # 递归创建目录
            except OSError as e:
                return jsonify({'success': False, 'message': f'创建目录失败: {e}'})

        # 3. 构造完整的文件保存路径
        full_filepath_on_disk = os.path.join(target_upload_dir, unique_filename)
        
        # 4. 保存文件
        image_file.save(full_filepath_on_disk)

        # 5. 修改数据库中 filepath 的存储方式
        # 存储相对路径，方便后续构建 URL： username/categoryname/unique_filename.ext
        # 这个 'filepath_for_db' 将被用于 `get_images` 函数中构建完整的 URL
        filepath_for_db = os.path.join(user_dir, category_dir, unique_filename)

        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            # 注意：这里的 filepath 存储的是相对路径 (username/categoryname/unique_filename.ext)
            c.execute('INSERT INTO images (user, category, filename, filepath, comment) VALUES (?, ?, ?, ?, ?)',
                      (username, category, original_filename, filepath_for_db, ''))
            conn.commit()
        return jsonify({'success': True, 'message': '图片上传成功'})
    return jsonify({'success': False, 'message': '文件类型不允许'})


@app.route('/get_images')
def get_images():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '未登录'})

    user_id = session['user_id']
    username = session['username']
    category = request.args.get('category')

    if not category:
        return jsonify({'success': False, 'message': '未指定分类'})

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        # 确保只获取当前用户和指定分类的图片
        c.execute('SELECT filepath, filename, comment FROM images WHERE category=? AND user=?', (category, username))
        rows = c.fetchall()

    images = []
    for row in rows:
        # row[0] 现在是 'username/categoryname/unique_filename.ext'
        # 所以我们需要将其与基础的 UPLOAD_FOLDER 组合，才能形成正确的 URL
        image_relative_path = row[0] # 这是数据库中存储的 filepath
        
        images.append({
            'url': f'/{UPLOAD_FOLDER}/{image_relative_path}', # <-- 修改这里！
            'filename': row[1],
            'comment': row[2],
            'filepath': image_relative_path # 确保前端仍然有这个纯文件名作为唯一标识
        })
    return jsonify({'success': True, 'images': images})

@app.route('/update_image', methods=['POST'])
def update_image():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '未登录'})

    username = session.get('username')
    data = request.json
    filepath_from_frontend = data.get('filepath') # 这是前端传来的，现在是相对路径

    # 在 update_image 中，filepath_from_frontend 应该就是数据库中存储的 filepath
    # 我们不更改文件名本身在磁盘上的位置，只更新数据库记录的 filename 和 comment
    filename = data.get('filename')
    comment = data.get('comment')

    if not filepath_from_frontend or not filename:
        return jsonify({'success': False, 'message': '参数缺失'})

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        # 确保只更新属于当前用户的图片
        c.execute('UPDATE images SET filename=?, comment=? WHERE filepath=? AND user=?', 
                  (filename, comment, filepath_from_frontend, username))
        conn.commit()

    return jsonify({'success': True, 'message': '更新成功'})


@app.route('/delete_image', methods=['POST'])
def delete_image():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '未登录'})

    data = request.json
    filepath_to_delete_from_db = data.get('filepath') # 这是前端传来的，现在是相对路径
    if not filepath_to_delete_from_db:
        return jsonify({'success': False, 'message': '参数缺失'})

    username = session.get('username')
    
    # 1. 从数据库中获取完整的物理路径
    physical_file_path = None
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        # 确保只删除属于当前用户的图片，并获取其完整的物理路径
        c.execute('SELECT filepath FROM images WHERE filepath=? AND user=?', (filepath_to_delete_from_db, username))
        image_record = c.fetchone()

        if not image_record:
            return jsonify({'success': False, 'message': '无权删除此图片或图片不存在'})

        # 构建完整的物理路径： uploads/filepath_to_delete_from_db
        physical_file_path = os.path.join(app.config['UPLOAD_FOLDER'], image_record[0])
        
        # 2. 删除数据库记录
        c.execute('DELETE FROM images WHERE filepath=? AND user=?', (filepath_to_delete_from_db, username))
        conn.commit()

    # 3. 删除物理文件 (在数据库删除后，以防万一数据库删除失败)
    if physical_file_path and os.path.exists(physical_file_path):
        try:
            os.remove(physical_file_path)
            # 尝试删除空的用户/分类目录 (可选，但推荐)
            # 获取图片所在的目录
            image_dir = os.path.dirname(physical_file_path)
            # 检查目录是否为空，如果为空则删除
            if not os.listdir(image_dir):
                os.rmdir(image_dir)
                # 检查用户目录是否为空，如果为空则删除
                user_dir = os.path.dirname(image_dir)
                if user_dir != app.config['UPLOAD_FOLDER'] and not os.listdir(user_dir): # 避免删除基础上传目录
                    os.rmdir(user_dir)

        except OSError as e:
            # 即使文件删除失败，数据库记录也已删除，可以返回成功
            return jsonify({'success': True, 'message': f'图片已从数据库删除，但物理文件删除失败: {e}'})

    return jsonify({'success': True, 'message': '图片删除成功'})

if __name__ == '__main__':
    init_db()
    app.run(debug=True)