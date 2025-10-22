from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
import uuid
from datetime import datetime

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

DATA_DIR = 'data'

# Файлы данных
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
LEVELS_FILE = os.path.join(DATA_DIR, 'levels.json')
LESSONS_FILE = os.path.join(DATA_DIR, 'lessons.json')
PURCHASES_FILE = os.path.join(DATA_DIR, 'purchases.json')

# Создаем папку data если ее нет
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Инициализация файлов данных
def init_data_files():
    default_data = {
        USERS_FILE: [],
        LEVELS_FILE: [],
        LESSONS_FILE: [],
        PURCHASES_FILE: []
    }
    
    for file_path, default_value in default_data.items():
        if not os.path.exists(file_path):
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(default_value, f, ensure_ascii=False, indent=2)

init_data_files()

# Вспомогательные функции для работы с данными
def read_json(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def write_json(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# API Routes
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/teacher')
def serve_teacher():
    return send_from_directory('.', 'teacher.html')

@app.route('/student')
def serve_student():
    return send_from_directory('.', 'student.html')

# Пользователи
@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.json
    users = read_json(USERS_FILE)
    
    user = {
        'id': str(uuid.uuid4()),
        'name': data['name'],
        'type': data['type'],  # 'teacher' or 'student'
        'email': data.get('email', ''),
        'created_at': datetime.now().isoformat()
    }
    
    users.append(user)
    write_json(USERS_FILE, users)
    
    return jsonify(user)

# Уровни
@app.route('/api/levels', methods=['GET'])
def get_levels():
    levels = read_json(LEVELS_FILE)
    return jsonify(levels)

@app.route('/api/levels', methods=['POST'])
def create_level():
    data = request.json
    levels = read_json(LEVELS_FILE)
    
    level = {
        'id': str(uuid.uuid4()),
        'title': data['title'],
        'description': data['description'],
        'author': data['author'],
        'robot': data['robot'],
        'coins': data['coins'],
        'enemies': data.get('enemies', []),
        'obstacles': data.get('obstacles', []),
        'is_public': data.get('is_public', False),
        'created_at': datetime.now().isoformat()
    }
    
    levels.append(level)
    write_json(LEVELS_FILE, levels)
    
    return jsonify(level)

# Уроки
@app.route('/api/lessons', methods=['GET'])
def get_lessons():
    teacher_id = request.args.get('teacher_id')
    lessons = read_json(LESSONS_FILE)
    
    if teacher_id:
        lessons = [lesson for lesson in lessons if lesson['teacher_id'] == teacher_id]
    
    return jsonify(lessons)

@app.route('/api/lessons', methods=['POST'])
def create_lesson():
    data = request.json
    lessons = read_json(LESSONS_FILE)
    
    lesson = {
        'id': str(uuid.uuid4()),
        'code': str(uuid.uuid4())[:8].upper(),
        'title': data['title'],
        'description': data['description'],
        'teacher_id': data['teacher_id'],
        'levels': data['levels'],
        'grades_shop': data.get('grades_shop', []),
        'students': [],
        'created_at': datetime.now().isoformat()
    }
    
    lessons.append(lesson)
    write_json(LESSONS_FILE, lessons)
    
    return jsonify(lesson)

@app.route('/api/lessons/<lesson_code>/join', methods=['POST'])
def join_lesson(lesson_code):
    data = request.json
    lessons = read_json(LESSONS_FILE)
    
    for lesson in lessons:
        if lesson['code'] == lesson_code:
            student_data = {
                'student_id': data['student_id'],
                'student_name': data['student_name'],
                'coins': 0,
                'completed_levels': [],
                'joined_at': datetime.now().isoformat()
            }
            
            if student_data not in lesson['students']:
                lesson['students'].append(student_data)
                write_json(LESSONS_FILE, lessons)
                return jsonify({'success': True, 'lesson': lesson})
    
    return jsonify({'success': False, 'error': 'Lesson not found'}), 404

# Прогресс ученика
@app.route('/api/progress', methods=['POST'])
def update_progress():
    data = request.json
    lessons = read_json(LESSONS_FILE)
    
    for lesson in lessons:
        if lesson['id'] == data['lesson_id']:
            for student in lesson['students']:
                if student['student_id'] == data['student_id']:
                    # Обновляем монеты
                    student['coins'] = data['coins']
                    
                    # Добавляем пройденный уровень если его еще нет
                    if data['level_id'] not in student['completed_levels']:
                        student['completed_levels'].append(data['level_id'])
                    
                    write_json(LESSONS_FILE, lessons)
                    return jsonify({'success': True})
    
    return jsonify({'success': False}), 404

# Покупки оценок
@app.route('/api/purchase', methods=['POST'])
def make_purchase():
    data = request.json
    lessons = read_json(LESSONS_FILE)
    purchases = read_json(PURCHASES_FILE)
    
    for lesson in lessons:
        if lesson['id'] == data['lesson_id']:
            # Находим ученика
            student = None
            for s in lesson['students']:
                if s['student_id'] == data['student_id']:
                    student = s
                    break
            
            if not student:
                return jsonify({'success': False, 'error': 'Student not found'}), 404
            
            # Находим оценку в магазине
            grade_item = None
            for item in lesson['grades_shop']:
                if item['id'] == data['grade_id']:
                    grade_item = item
                    break
            
            if not grade_item:
                return jsonify({'success': False, 'error': 'Grade not found'}), 404
            
            # Проверяем достаточно ли монет
            if student['coins'] < grade_item['price']:
                return jsonify({'success': False, 'error': 'Not enough coins'}), 400
            
            # Совершаем покупку
            student['coins'] -= grade_item['price']
            
            purchase = {
                'id': str(uuid.uuid4()),
                'lesson_id': data['lesson_id'],
                'student_id': data['student_id'],
                'student_name': student['student_name'],
                'grade': grade_item['grade'],
                'price': grade_item['price'],
                'purchased_at': datetime.now().isoformat(),
                'teacher_notified': False
            }
            
            purchases.append(purchase)
            write_json(PURCHASES_FILE, purchases)
            write_json(LESSONS_FILE, lessons)
            
            return jsonify({'success': True, 'purchase': purchase})
    
    return jsonify({'success': False}), 404

# Уведомления для учителя
@app.route('/api/notifications/<teacher_id>', methods=['GET'])
def get_notifications(teacher_id):
    purchases = read_json(PURCHASES_FILE)
    lessons = read_json(LESSONS_FILE)
    
    # Находим все уроки учителя
    teacher_lessons = [lesson['id'] for lesson in lessons if lesson['teacher_id'] == teacher_id]
    
    # Находим покупки в этих уроках
    teacher_purchases = [p for p in purchases if p['lesson_id'] in teacher_lessons and not p['teacher_notified']]
    
    # Помечаем как уведомленные
    for purchase in teacher_purchases:
        purchase['teacher_notified'] = True
    
    write_json(PURCHASES_FILE, purchases)
    
    return jsonify(teacher_purchases)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
