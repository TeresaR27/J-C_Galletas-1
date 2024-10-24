from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import hashlib

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta'  # Cambia esto a una clave secreta más segura

# Conectar con la base de datos SQLite
def get_db_connection():
    conn = sqlite3.connect('inventario.db')
    conn.row_factory = sqlite3.Row
    return conn

# Inicializar la base de datos
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Crear tablas de base de datos si no existen
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Crear tabla de Productos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT,
            nombre TEXT,
            categoria TEXT,
            sabores TEXT,
            formato TEXT
        );
    ''')

    # Crear tabla de Inventario
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Inventario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER,
            cantidad_producida INTEGER,
            cantidad_vendida INTEGER,
            cantidad_devueltas INTEGER,
            cantidad_defectuosa INTEGER,
            fecha TEXT,
            FOREIGN KEY (producto_id) REFERENCES Productos(id)
        );
    ''')

    # Crear tabla de Usuarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        );
    ''')

    # Insertar un usuario por defecto (solo para propósitos de desarrollo)
    cursor.execute("INSERT OR IGNORE INTO Usuarios (username, password) VALUES (?, ?)", ('admin', hash_password('password123')))  # Cambia 'password123' a una contraseña segura.

    conn.commit()
    conn.close()

# Inicializar la base de datos
init_db()

# Ruta principal para mostrar los productos y realizar la búsqueda
@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    productos = []  # Inicialmente vacío

    if request.method == 'POST':  # Si se hace una búsqueda
        search_query = request.form['search_query']
        cursor.execute("SELECT * FROM Productos WHERE codigo LIKE ? OR nombre LIKE ?", ('%' + search_query + '%', '%' + search_query + '%'))
        productos = cursor.fetchall()
    else:  # Si es GET, simplemente no se muestra nada
        productos = []

    conn.close()
    return render_template('index.html', productos=productos)

# Ruta para agregar un nuevo producto
@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        codigo = request.form['codigo']
        nombre = request.form['nombre']
        categoria = request.form['categoria']
        sabores = request.form['sabores']
        formato = request.form['formato']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(''' 
            INSERT INTO Productos (codigo, nombre, categoria, sabores, formato)
            VALUES (?, ?, ?, ?, ?)
        ''', (codigo, nombre, categoria, sabores, formato))
        conn.commit()
        conn.close()

        return redirect(url_for('index'))

    return render_template('add_product.html')

# Ruta para mostrar y manejar inventario de un producto
@app.route('/inventory/<int:id>', methods=['GET', 'POST'])
def inventory(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        cantidad_producida = request.form['cantidad_producida']
        cantidad_vendida = request.form['cantidad_vendida']
        cantidad_devueltas = request.form['cantidad_devueltas']
        cantidad_defectuosa = request.form['cantidad_defectuosa']
        fecha = request.form['fecha']

        cursor.execute(''' 
            INSERT INTO Inventario (producto_id, cantidad_producida, cantidad_vendida, cantidad_devueltas, cantidad_defectuosa, fecha)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (id, cantidad_producida, cantidad_vendida, cantidad_devueltas, cantidad_defectuosa, fecha))
        conn.commit()

    # Obtener datos del producto
    cursor.execute('SELECT * FROM Productos WHERE id = ?', (id,))
    producto = cursor.fetchone()

    # Obtener historial de inventario
    cursor.execute('SELECT * FROM Inventario WHERE producto_id = ?', (id,))
    inventarios = cursor.fetchall()

    conn.close()
    return render_template('inventory.html', producto=producto, inventarios=inventarios)

# Ruta para eliminar un registro de inventario
@app.route('/delete_inventory/<int:id>', methods=['GET', 'POST'])
def delete_inventory(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Obtener el inventario correspondiente
    cursor.execute('SELECT * FROM Inventario WHERE id = ?', (id,))
    inventario = cursor.fetchone()

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Validar el usuario y la contraseña
        cursor.execute('SELECT * FROM Usuarios WHERE username = ? AND password = ?', (username, hash_password(password)))
        user = cursor.fetchone()

        if user:
            # Lógica para eliminar el registro de inventario
            cursor.execute('DELETE FROM Inventario WHERE id = ?', (id,))
            conn.commit()
            flash('Registro de inventario eliminado con éxito.', 'success')  # Mensaje de éxito
            return redirect(url_for('inventory', id=inventario['producto_id']))  # Regresar a la vista de inventario

        flash('Nombre de usuario o contraseña incorrectos', 'danger')

    conn.close()
    return render_template('confirm_delete_inventory.html', inventario=inventario)  # Nueva plantilla para confirmar eliminación

# Ruta para eliminar un producto
@app.route('/delete_product/<int:id>', methods=['POST'])
def delete_product(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM Productos WHERE id = ?', (id,))
    cursor.execute('DELETE FROM Inventario WHERE producto_id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# Ruta para editar un producto
@app.route('/edit_product/<int:id>', methods=['GET', 'POST'])
def edit_product(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        codigo = request.form['codigo']
        nombre = request.form['nombre']
        categoria = request.form['categoria']
        sabores = request.form['sabores']
        formato = request.form['formato']

        cursor.execute(''' 
            UPDATE Productos SET codigo = ?, nombre = ?, categoria = ?, sabores = ?, formato = ? WHERE id = ?
        ''', (codigo, nombre, categoria, sabores, formato, id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    # Obtener datos del producto a editar
    cursor.execute('SELECT * FROM Productos WHERE id = ?', (id,))
    producto = cursor.fetchone()
    conn.close()
    return render_template('edit_product.html', producto=producto)

# Ruta para iniciar sesión
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM Usuarios WHERE username = ? AND password = ?', (username, hash_password(password)))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user_id'] = user['id']
            flash('Inicio de sesión exitoso', 'success')
            return redirect(url_for('index'))
        else:
            flash('Nombre de usuario o contraseña incorrectos', 'danger')

    return render_template('login.html')

# Ruta para cerrar sesión
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Has cerrado sesión', 'info')
    return redirect(url_for('login'))

# Ruta para registrarse
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('INSERT INTO Usuarios (username, password) VALUES (?, ?)', (username, hash_password(password)))
            conn.commit()
            flash('Registro exitoso, puedes iniciar sesión', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('El nombre de usuario ya está en uso', 'danger')
        
        conn.close()

    return render_template('register.html')

if __name__ == "__main__":
    app.run(debug=True)
