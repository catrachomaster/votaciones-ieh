import os
from flask import Flask, render_template, request, redirect, url_for
from flask import flash
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename

from flask import abort

def admin_required():
    if 'admin_id' not in session:
        abort(403)  # acceso prohibido



from flask import Flask
from flask_mysqldb import MySQL

app = Flask(__name__)

# CONFIGURACIÓN DE CONEXIÓN A MARIADB
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Analucia17'
app.config['MYSQL_DB'] = 'votaciones'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

@app.route('/')
def index():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM candidatos")
    candidatos = cur.fetchall()
    cur.close()
    return str(candidatos)  # Solo para verificar conexión


# Configuración para subir archivos
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/agregar_candidato', methods=['GET', 'POST'])
def agregar_candidato():
    if request.method == 'POST':
        nombre = request.form['nombre']
        cargo = request.form['cargo']
        descripcion = request.form['descripcion']
        foto = request.files['foto']

        if foto and allowed_file(foto.filename):
            filename = secure_filename(foto.filename)
            foto.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO candidatos (nombre, cargo, descripcion, foto) VALUES (%s, %s, %s, %s)",
                        (nombre, cargo, descripcion, filename))
            mysql.connection.commit()
            cur.close()

            return redirect(url_for('agregar_candidato'))

    return render_template('agregar_candidato.html')

@app.route('/votar', methods=['GET', 'POST'])
def votar():
    if 'usuario_id' not in session:
        return redirect(url_for('votante'))

    usuario_id = session['usuario_id']

    if request.method == 'POST':
        candidato_id = request.form['candidato_id']

        cur = mysql.connection.cursor()

        # Verifica de nuevo si ya votó
        cur.execute("SELECT ya_voto FROM usuarios WHERE id = %s", [usuario_id])
        datos = cur.fetchone()
        if datos['ya_voto']:
            cur.close()
            return "Usted ya ha votado."

        # Suma el voto
        cur.execute("UPDATE candidatos SET votos = votos + 1 WHERE id = %s", [candidato_id])

        # Marca como que ya votó
        cur.execute("UPDATE usuarios SET ya_voto = TRUE WHERE id = %s", [usuario_id])

        mysql.connection.commit()
        cur.close()

        session.clear()
        return "Voto registrado exitosamente. Gracias por participar."

    # Mostrar candidatos
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM candidatos")
    candidatos = cur.fetchall()
    cur.close()

    return render_template('votar.html', candidatos=candidatos)


from flask import send_from_directory

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/resultados')
def resultados():
    cur = mysql.connection.cursor()
    cur.execute("SELECT nombre, cargo, votos FROM candidatos ORDER BY votos DESC")
    resultados = cur.fetchall()
    cur.close()
    return render_template('resultados.html', resultados=resultados)

from flask import session

app.secret_key = 'votaciones-secret-key'

@app.route('/votante', methods=['GET', 'POST'])
def votante():
    if request.method == 'POST':
        nombre = request.form['nombre']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM usuarios WHERE nombre = %s", [nombre])
        usuario = cur.fetchone()

        if usuario:
            if usuario['ya_voto']:
                return "Usted ya ha votado. Gracias."
            else:
                session['usuario_id'] = usuario['id']
                session['nombre'] = usuario['nombre']
                return redirect(url_for('votaciones_disponibles'))
        else:
            return "Usuario no encontrado"

    return render_template('votante.html')

@app.route('/registrar_usuario', methods=['GET', 'POST'])
def registrar_usuario():
    if request.method == 'POST':
        nombre = request.form['nombre']
        correo = request.form['correo']
        contrasena = request.form['contrasena']

        # Aquí podrías encriptar la contraseña si quisieras
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO usuarios (nombre, correo, contrasena) VALUES (%s, %s, %s)",
                    (nombre, correo, contrasena))
        mysql.connection.commit()
        cur.close()

        return "Usuario registrado correctamente"

    return render_template('registrar_usuario.html')

@app.route('/inicio', methods=['GET', 'POST'])
def inicio():
    if request.method == 'POST':
        nombre = request.form['nombre']
        contrasena = request.form['contrasena']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM usuarios WHERE nombre = %s AND contrasena = %s", (nombre, contrasena))
        usuario = cur.fetchone()
        cur.close()

        if usuario:
            if usuario['ya_voto']:
                return render_template('inicio.html', error='ya_voto')
            else:
                session['usuario_id'] = usuario['id']
                session['nombre'] = usuario['nombre']
                return redirect(url_for('votaciones_disponibles'))
        else:
            return render_template('inicio.html', error='usuario_no_encontrado')

    return render_template('inicio.html')


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        nombre = request.form['nombre']
        contrasena = request.form['contrasena']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM usuarios WHERE nombre = %s AND contrasena = %s", (nombre, contrasena))
        admin = cur.fetchone()
        cur.close()

        if admin and admin['es_admin']:
            session['admin_id'] = admin['id']
            session['admin_nombre'] = admin['nombre']
            return redirect(url_for('admin_configuracion'))
        else:
            return "Acceso denegado. Solo administradores pueden ingresar."

    return render_template('admin_login.html')

@app.route('/admin/configuracion', methods=['GET', 'POST'])
def admin_configuracion():
    if 'admin_id' not in session:
        return "Acceso denegado. No hay administrador autenticado.", 403

    cur = mysql.connection.cursor()

    if request.method == 'POST':
        print("✅ Se recibió un POST en /admin/configuracion")
        flash("POST recibido", "info")

        if 'crear' in request.form:
            flash("Se detectó acción: crear", "info")
            titulo = request.form['titulo']
            descripcion = request.form['descripcion']
            max_clerigos = request.form.get('max_clerigos', 1)
            max_laicos = request.form.get('max_laicos', 1)

            cur.execute("""
                INSERT INTO votaciones (titulo, descripcion, activa, max_clerigos, max_laicos)
                VALUES (%s, %s, TRUE, %s, %s)
            """, (titulo, descripcion, max_clerigos, max_laicos))
            mysql.connection.commit()
            flash("Votación creada exitosamente.", "success")

        elif 'accion' in request.form:
            votacion_id = int(request.form.get('votacion_id', 0))
            accion = request.form['accion']
            flash(f"Acción detectada: {accion}", "info")

            if accion == 'activar':
                cur.execute("UPDATE votaciones SET activa = TRUE WHERE id = %s", [votacion_id])
                mysql.connection.commit()
                flash("Votación activada exitosamente.", "success")

            elif accion == 'desactivar':
                cur.execute("UPDATE votaciones SET activa = FALSE WHERE id = %s", [votacion_id])
                mysql.connection.commit()
                flash("Votación desactivada exitosamente.", "success")

            elif accion == 'eliminar':
                cur.execute("""
                    DELETE v FROM votos v
                    JOIN candidatos c ON v.candidato_id = c.id
                    WHERE c.votacion_id = %s
                """, [votacion_id])
                cur.execute("DELETE FROM candidatos WHERE votacion_id = %s", [votacion_id])
                cur.execute("DELETE FROM votaciones WHERE id = %s", [votacion_id])
                mysql.connection.commit()
                flash("Votación eliminada correctamente.", "success")

            elif accion == 'editar_limites':
                try:
                    max_clerigos = int(request.form.get('max_clerigos', 0))
                    max_laicos = int(request.form.get('max_laicos', 0))

                    # Verificar cuántos candidatos hay
                    cur.execute("SELECT COUNT(*) as total FROM candidatos WHERE votacion_id = %s AND tipo = 'clerigo'", [votacion_id])
                    total_clerigos = cur.fetchone()['total']

                    cur.execute("SELECT COUNT(*) as total FROM candidatos WHERE votacion_id = %s AND tipo = 'laico'", [votacion_id])
                    total_laicos = cur.fetchone()['total']

                    # Validar que no se permita más votos que candidatos
                    if max_clerigos > total_clerigos or max_laicos > total_laicos:
                        flash("No puedes permitir más votos que candidatos disponibles en cada categoría.", "error")
                    else:
                        cur.execute("""
                            UPDATE votaciones
                            SET max_clerigos = %s, max_laicos = %s
                            WHERE id = %s
                        """, (max_clerigos, max_laicos, votacion_id))
                        mysql.connection.commit()
                        flash("Límites actualizados correctamente.", "success")

                except Exception as e:
                    flash("Ocurrió un error al actualizar los límites: " + str(e), "error")

        cur.close()
        return redirect(url_for('admin_configuracion'))

    # Mostrar todas las votaciones
    cur.execute("SELECT * FROM votaciones")
    votaciones = cur.fetchall()
    cur.close()

    return render_template('admin_configuracion.html', votaciones=votaciones)



@app.route('/votaciones_disponibles')
def votaciones_disponibles():
    if 'usuario_id' not in session:
        return redirect(url_for('votante'))

    usuario_id = session['usuario_id']
    cur = mysql.connection.cursor()

    # Buscar votaciones activas en las que aún NO ha votado
    cur.execute("""
        SELECT * FROM votaciones
        WHERE activa = TRUE AND id NOT IN (
            SELECT c.votacion_id
            FROM votos v
            JOIN candidatos c ON v.candidato_id = c.id
            WHERE v.usuario_id = %s
        )
    """, [usuario_id])
    votaciones = cur.fetchall()
    cur.close()

    if not votaciones:
        return redirect(url_for('fin_votacion'))

    return render_template('votaciones_disponibles.html', votaciones=votaciones, nombre=session.get('nombre'))


@app.route('/votar/<int:votacion_id>', methods=['GET', 'POST'])
def votar_por_tipo(votacion_id):
    if 'usuario_id' not in session:
        return redirect(url_for('votante'))

    usuario_id = session['usuario_id']
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        # Obtener listas separadas de IDs desde los campos ocultos
        ids_clerigos = request.form.get('seleccion_clerigos', '').split(',')
        ids_laicos = request.form.get('seleccion_laicos', '').split(',')

        todos_ids = [id for id in ids_clerigos + ids_laicos if id.strip()]

        if not todos_ids:
            cur.close()
            return "Debe seleccionar al menos un candidato."

        # Verificar si ya votó en esta votación
        cur.execute("""
            SELECT COUNT(*) AS total FROM votos
            WHERE usuario_id = %s AND candidato_id IN (
                SELECT id FROM candidatos WHERE votacion_id = %s
            )
        """, (usuario_id, votacion_id))
        ya_voto = cur.fetchone()['total'] > 0

        if ya_voto:
            cur.close()
            return "Ya has votado en esta votación."

        # Registrar votos
        for candidato_id in todos_ids:
            if candidato_id.isdigit():
                cur.execute("UPDATE candidatos SET votos = votos + 1 WHERE id = %s", [candidato_id])
                cur.execute("INSERT INTO votos (usuario_id, candidato_id) VALUES (%s, %s)", (usuario_id, candidato_id))

        mysql.connection.commit()
        cur.close()

        return render_template("voto_exitoso.html")

    # GET: mostrar la pantalla de votación
    cur.execute("SELECT * FROM candidatos WHERE votacion_id = %s AND tipo = 'clerigo'", [votacion_id])
    clerigos = cur.fetchall()

    cur.execute("SELECT * FROM candidatos WHERE votacion_id = %s AND tipo = 'laico'", [votacion_id])
    laicos = cur.fetchall()

    cur.execute("SELECT max_clerigos, max_laicos FROM votaciones WHERE id = %s", [votacion_id])
    votacion = cur.fetchone()

    cur.close()

    return render_template("votar.html",
                           clerigos=clerigos,
                           laicos=laicos,
                           max_clerigos=votacion['max_clerigos'],
                           max_laicos=votacion['max_laicos'])



@app.route('/admin/candidatos/<int:votacion_id>', methods=['GET', 'POST'])
def admin_candidatos(votacion_id):
    admin_required()
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        cargo = request.form['cargo']
        tipo = request.form.get('tipo', 'laico')  # por defecto 'laico'
        
        foto = request.files.get('foto')  # Esto evita el error

        if foto and allowed_file(foto.filename):
            filename = secure_filename(foto.filename)
            foto.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            cur.execute("""
                INSERT INTO candidatos (nombre, descripcion, cargo, foto, votacion_id, tipo)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (nombre, descripcion, cargo, filename, votacion_id, tipo))

            mysql.connection.commit()
        else:
            flash("Debe seleccionar una imagen válida", "error")

    # Cargar candidatos para la votación actual
    cur.execute("SELECT * FROM candidatos WHERE votacion_id = %s", [votacion_id])
    candidatos = cur.fetchall()
    cur.close()

    return render_template("admin_candidatos.html", candidatos=candidatos, votacion_id=votacion_id)


@app.route('/fin_votacion')
def fin_votacion():
    session.clear()  # Cierra sesión del votante
    return render_template('fin_votacion.html')

@app.route('/admin/reset_usuarios', methods=['POST'])
def reset_usuarios():
    admin_required()

    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM votos")  # Importante: borrar votos primero
    cur.execute("DELETE FROM usuarios WHERE es_admin = 0")  # Solo votantes
    cur.execute("ALTER TABLE usuarios AUTO_INCREMENT = 1")
    mysql.connection.commit()
    cur.close()

    return redirect(url_for('admin_configuracion'))


@app.route('/admin/reset_votos', methods=['POST'])
def reset_votos():
    admin_required()

    cur = mysql.connection.cursor()

    # Borra todos los votos
    cur.execute("DELETE FROM votos")

    # Reinicia el contador de ID
    cur.execute("ALTER TABLE votos AUTO_INCREMENT = 1")

    mysql.connection.commit()
    cur.close()

    return redirect(url_for('admin_configuracion'))




@app.route('/crear_admin')
def crear_admin():
    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO usuarios (nombre, correo, contrasena, ya_voto, es_admin)
        VALUES (%s, %s, %s, %s, %s)
    """, ('admin', 'admin@ieh.hn', 'admin123', 0, 1))
    mysql.connection.commit()
    cur.close()
    return "Administrador creado con usuario: admin y contraseña: admin123"

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('inicio'))



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')



