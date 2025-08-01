from flask import Blueprint, render_template, request, redirect, url_for
from models import db, Wedding, Task

tasks_bp = Blueprint('tasks_bp', __name__, url_prefix='/tasks')

@tasks_bp.route('/<int:wedding_id>')
def task_list(wedding_id):
    wedding = Wedding.query.get_or_404(wedding_id)
    return render_template('tasks.html', wedding=wedding)

@tasks_bp.route('/<int:wedding_id>/add', methods=['POST'])
def add_task(wedding_id):
    description = request.form['description']
    if description.strip():
        db.session.add(Task(description=description, wedding_id=wedding_id))
        db.session.commit()
    return redirect(url_for('tasks_bp.task_list', wedding_id=wedding_id))

@tasks_bp.route('/<int:wedding_id>/done/<int:task_id>', methods=['POST'])
def toggle_done(wedding_id, task_id):
    task = Task.query.get_or_404(task_id)
    task.is_done = not task.is_done
    db.session.commit()
    return redirect(url_for('tasks_bp.task_list', wedding_id=wedding_id))

@tasks_bp.route('/<int:wedding_id>/delete/<int:task_id>', methods=['POST'])
def delete_task(wedding_id, task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for('tasks_bp.task_list', wedding_id=wedding_id))
