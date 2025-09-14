import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, g, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'mymoneypal-secret-key-12345-mazboot-password'

# Database setup
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            os.path.join(app.instance_path, 'mymoneypal.db'),
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# Initialize database
def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql') as f:
            db.executescript(f.read().decode('utf8'))
        print("Database initialized successfully!")

# CLI command to initialize database
@app.cli.command('init-db')
def init_db_command():
    """Clear existing data and create new tables."""
    init_db()
    print('Initialized the database.')

# User authentication helpers
def get_user_id(username):
    db = get_db()
    user = db.execute(
        'SELECT id FROM users WHERE username = ?', (username,)
    ).fetchone()
    return user['id'] if user else None

def login_required(view):
    from functools import wraps
    @wraps(view)
    def wrapped_view(**kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.')
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view

# Routes
@app.route('/')
def index():
    if 'user_id' not in session:
        return render_template('index.html', balance=0, transactions=[])
    
    db = get_db()
    
    # Calculate balance from all transactions
    balance_result = db.execute(
        'SELECT SUM(CASE WHEN type = "income" THEN amount ELSE -amount END) as balance FROM transactions WHERE user_id = ?',
        (session['user_id'],)
    ).fetchone()
    balance = balance_result['balance'] if balance_result['balance'] is not None else 0
    
    # Get recent transactions
    transactions = db.execute(
        'SELECT * FROM transactions WHERE user_id = ? ORDER BY date DESC LIMIT 5',
        (session['user_id'],)
    ).fetchall()
    
    return render_template('index.html', balance=balance, transactions=transactions)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_transaction():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form.get('description', '')
        amount = float(request.form['amount'])
        type_ = request.form['type']
        date = request.form['date']
        
        db = get_db()
        db.execute(
            'INSERT INTO transactions (user_id, title, description, amount, type, date) VALUES (?, ?, ?, ?, ?, ?)',
            (session['user_id'], title, description, amount, type_, date)
        )
        db.commit()
        
        flash('Transaction added successfully!')
        return redirect(url_for('index'))
    
    return render_template('add.html')

@app.route('/expenses')
@login_required
def expenses():
    db = get_db()
    transactions = db.execute(
        'SELECT * FROM transactions WHERE user_id = ? ORDER BY date DESC',
        (session['user_id'],)
    ).fetchall()
    return render_template('expenses.html', transactions=transactions)

# API Routes
@app.route('/api/transactions', methods=['GET', 'POST'])
@login_required
def api_transactions():
    db = get_db()
    
    if request.method == 'GET':
        transactions = db.execute(
            'SELECT * FROM transactions WHERE user_id = ? ORDER BY date DESC',
            (session['user_id'],)
        ).fetchall()
        
        # Convert rows to dictionaries
        transactions_list = []
        for transaction in transactions:
            transactions_list.append(dict(transaction))
        
        return jsonify(transactions_list)
    
    elif request.method == 'POST':
        data = request.get_json()
        
        db.execute(
            'INSERT INTO transactions (user_id, title, description, amount, type, date) VALUES (?, ?, ?, ?, ?, ?)',
            (session['user_id'], data['title'], data.get('description', ''), 
             float(data['amount']), data['type'], data['date'])
        )
        db.commit()
        
        return jsonify({'success': True})

@app.route('/api/transactions/<int:id>', methods=['PUT', 'DELETE'])
@login_required
def api_transaction(id):
    db = get_db()
    
    # Verify the transaction belongs to the current user
    transaction = db.execute(
        'SELECT * FROM transactions WHERE id = ? AND user_id = ?',
        (id, session['user_id'])
    ).fetchone()
    
    if not transaction:
        return jsonify({'error': 'Transaction not found'}), 404
    
    if request.method == 'PUT':
        data = request.get_json()
        
        db.execute(
            'UPDATE transactions SET title = ?, description = ?, amount = ?, type = ?, date = ? WHERE id = ?',
            (data['title'], data.get('description', ''), float(data['amount']), 
             data['type'], data['date'], id)
        )
        db.commit()
        
        return jsonify({'success': True})
    
    elif request.method == 'DELETE':
        db.execute('DELETE FROM transactions WHERE id = ?', (id,))
        db.commit()
        
        return jsonify({'success': True})

# Authentication routes
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db = get_db()
        error = None
        
        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'
        elif db.execute(
            'SELECT id FROM users WHERE username = ?', (username,)
        ).fetchone() is not None:
            error = f'User {username} is already registered.'
        
        if error is None:
            db.execute(
                'INSERT INTO users (username, password) VALUES (?, ?)',
                (username, generate_password_hash(password))
            )
            db.commit()
            
            # Log the user in automatically after signup
            user_id = get_user_id(username)
            session.clear()
            session['user_id'] = user_id
            session['username'] = username
            
            flash('Account created successfully!')
            return redirect(url_for('index'))
        
        flash(error)
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db = get_db()
        error = None
        user = db.execute(
            'SELECT * FROM users WHERE username = ?', (username,)
        ).fetchone()
        
        if user is None:
            error = 'Incorrect username.'
        elif not check_password_hash(user['password'], password):
            error = 'Incorrect password.'
        
        if error is None:
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            
            flash('Logged in successfully!')
            return redirect(url_for('index'))
        
        flash(error)
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('index'))

# Register teardown function
app.teardown_appcontext(close_db)

if __name__ == '__main__':
    # Create instance folder if it doesn't exist
    if not os.path.exists(app.instance_path):
        os.makedirs(app.instance_path)
    
    app.run(debug=True)