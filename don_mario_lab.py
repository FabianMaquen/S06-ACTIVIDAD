"""
don_mario_lab.py — Laboratorio de la Semana 06 · Agentes Inteligentes
SQL, pandas y el agente de la Pizzería Don Mario.
Dr. José Alfredo Herrera Quispe

Uso rápido (Colab, Jupyter o consola):
    from don_mario_lab import *
    mini = crear_mini_base()                 # base de calentamiento (20 ventas)
    conn = crear_base(CODIGO)                # tu base personal (semilla = tu código)
    print(experimento_escala(CODIGO))        # Parte 5
    print(torneo(CODIGO))                    # Parte 6
Solo requiere Python 3.9+ y pandas. SQLite viene con Python.
"""
import sqlite3, random, time, datetime as dt
import pandas as pd

CODIGO = 2311685          # Código de alumno y semilla de la base personal.

# ---------------------------------------------------------------- 1. BASES
ESQUEMA = """
DROP TABLE IF EXISTS ventas; DROP TABLE IF EXISTS clientes; DROP TABLE IF EXISTS productos;
CREATE TABLE clientes  (id INTEGER PRIMARY KEY, nombre TEXT, ciudad TEXT);
CREATE TABLE productos (id INTEGER PRIMARY KEY, nombre TEXT, categoria TEXT, precio REAL);
CREATE TABLE ventas    (id INTEGER PRIMARY KEY, cliente_id INTEGER, producto_id INTEGER,
                        fecha TEXT, cantidad INTEGER,
                        FOREIGN KEY (cliente_id)  REFERENCES clientes(id),
                        FOREIGN KEY (producto_id) REFERENCES productos(id));
"""

def crear_mini_base():
    """Base de calentamiento: 5 clientes, 6 productos, 20 ventas. Igual para todos."""
    conn = sqlite3.connect(":memory:")
    conn.executescript(ESQUEMA + """
    INSERT INTO clientes VALUES (1,'Ana López','Lima'),(2,'Luis Pérez','Arequipa'),
      (3,'María García','Lima'),(4,'Pedro Soto','Cusco'),(5,'Sofía Ramos','Lima');
    INSERT INTO productos VALUES (1,'Pizza Margarita','Pizza',28.0),(2,'Pizza Pepperoni','Pizza',32.0),
      (3,'Pizza Hawaiana','Pizza',30.0),(4,'Coca-Cola 500ml','Bebida',6.0),
      (5,'Inca Kola 500ml','Bebida',6.0),(6,'Tiramisú','Postre',15.0);
    INSERT INTO ventas (cliente_id, producto_id, fecha, cantidad) VALUES
      (1,1,'2025-04-01',2),(1,4,'2025-04-01',2),(2,2,'2025-04-02',1),(2,5,'2025-04-02',1),
      (3,3,'2025-04-03',1),(3,6,'2025-04-03',2),(1,2,'2025-04-05',1),(4,1,'2025-04-05',3),
      (5,3,'2025-04-06',2),(5,4,'2025-04-06',2),(3,2,'2025-04-08',2),(2,1,'2025-04-09',1),
      (1,3,'2025-04-10',1),(4,5,'2025-04-10',1),(5,2,'2025-04-12',1),(3,1,'2025-04-13',2),
      (2,6,'2025-04-14',1),(1,5,'2025-04-15',3),(4,2,'2025-04-16',2),(5,1,'2025-04-17',1);
    """)
    conn.commit()
    return conn

CLIENTES = [("Ana López","Lima"),("Luis Pérez","Arequipa"),("María García","Lima"),("Pedro Soto","Cusco"),
            ("Sofía Ramos","Lima"),("Jorge Huamán","Trujillo"),("Carla Quispe","Arequipa"),("Diego Flores","Lima"),
            ("Rosa Mamani","Cusco"),("Iván Torres","Piura"),("Lucía Vargas","Trujillo"),("Óscar Medina","Lima")]
PRODUCTOS = [("Pizza Margarita","Pizza",28.0,5),("Pizza Pepperoni","Pizza",32.0,6),("Pizza Hawaiana","Pizza",30.0,4),
             ("Pizza Americana","Pizza",29.0,4),("Coca-Cola 500ml","Bebida",6.0,4),("Inca Kola 500ml","Bebida",6.0,5),
             ("Tiramisú","Postre",15.0,2),("Pan al ajo","Entrada",9.0,3)]
PESO_DIA = [0.7, 0.7, 0.8, 0.9, 1.5, 2.0, 1.7]      # lunes … domingo: el fin de semana vende más
INICIO, DIAS_HISTORIA = dt.date(2026, 3, 2), 56     # 8 semanas exactas, empieza en lunes

def crear_base(codigo, n_ventas=600, ruta=":memory:"):
    """Tu base personal: mismas tablas, datos generados con tu código como semilla."""
    rng = random.Random(codigo)
    conn = sqlite3.connect(ruta)
    conn.executescript(ESQUEMA)
    conn.executemany("INSERT INTO clientes (nombre, ciudad) VALUES (?,?)", CLIENTES)
    conn.executemany("INSERT INTO productos (nombre, categoria, precio) VALUES (?,?,?)", [p[:3] for p in PRODUCTOS])
    fechas = [INICIO + dt.timedelta(days=i) for i in range(DIAS_HISTORIA)]
    f = rng.choices([d.isoformat() for d in fechas], weights=[PESO_DIA[d.weekday()] for d in fechas], k=n_ventas)
    c = rng.choices(range(1, len(CLIENTES)+1), weights=[rng.uniform(0.5, 2.0) for _ in CLIENTES], k=n_ventas)
    p = rng.choices(range(1, len(PRODUCTOS)+1), weights=[x[3] for x in PRODUCTOS], k=n_ventas)
    q = rng.choices([1, 2, 3, 4], weights=[55, 30, 10, 5], k=n_ventas)
    conn.executemany("INSERT INTO ventas (cliente_id, producto_id, fecha, cantidad) VALUES (?,?,?,?)", zip(c, p, f, q))
    conn.commit()
    return conn

# ---------------------------------------------------------------- 2. PARTE 5: SQL frente a pandas, con evidencia
Q_TOP = """SELECT c.nombre, c.ciudad, SUM(p.precio * v.cantidad) AS total
FROM ventas v JOIN clientes c ON v.cliente_id = c.id JOIN productos p ON v.producto_id = p.id
GROUP BY c.id, c.nombre, c.ciudad ORDER BY total DESC LIMIT 1"""

def experimento_escala(codigo, tamanos=(1_000, 100_000, 1_000_000)):
    filas = []
    for n in tamanos:
        conn = crear_base(codigo, n_ventas=n)
        t0 = time.perf_counter(); a = pd.read_sql(Q_TOP, conn); t_sql = time.perf_counter() - t0
        t0 = time.perf_counter()
        v = pd.read_sql("SELECT * FROM ventas", conn); c = pd.read_sql("SELECT * FROM clientes", conn)
        p = pd.read_sql("SELECT * FROM productos", conn)
        df = v.merge(c, left_on="cliente_id", right_on="id", suffixes=("", "_c")) \
              .merge(p, left_on="producto_id", right_on="id", suffixes=("", "_p"))
        df["total"] = df["precio"] * df["cantidad"]
        b = df.groupby(["nombre", "ciudad"])["total"].sum().nlargest(1)
        t_pd = time.perf_counter() - t0
        assert a.loc[0, "nombre"] == b.index[0][0], "Las dos versiones deben coincidir"
        mb = sum(x.memory_usage(deep=True).sum() for x in (v, c, p)) / 1e6
        filas.append({"ventas": n, "filas_A": len(a), "filas_B": len(v)+len(c)+len(p),
                      "seg_SQL": round(t_sql, 3), "seg_pandas": round(t_pd, 3), "MB_en_RAM_B": round(mb, 1)})
        conn.close()
    return pd.DataFrame(filas)

# ---------------------------------------------------------------- 3. PARTE 6: el agente Don Mario
FACTOR_PROMO = 1.25     # un día con promoción vende 25 % más…
COSTO_PROMO  = 100.0    # …pero cuesta S/ 100 entre publicidad y descuentos
DIAS_SIMULADOS = 28

def preparar_agente(conn):
    """La memoria del agente: caja diaria (historia) y decisiones (lo que él hace)."""
    conn.executescript("""
    DROP TABLE IF EXISTS caja_diaria; DROP TABLE IF EXISTS decisiones;
    CREATE TABLE caja_diaria (dia TEXT PRIMARY KEY, ingreso REAL);
    CREATE TABLE decisiones  (dia TEXT, agente TEXT, accion TEXT, ingreso_neto REAL);
    INSERT INTO caja_diaria
      SELECT v.fecha, SUM(p.precio * v.cantidad) FROM ventas v
      JOIN productos p ON v.producto_id = p.id GROUP BY v.fecha;
    """)

def percibir(conn, dia):
    """SENSOR: todo lo que el agente sabe del mundo lo obtiene con SELECT (ASK)."""
    uno = lambda q, *a: (conn.execute(q, a).fetchone() or [None])[0] or 0.0
    return {
        "dia": dia,
        "dia_semana": dt.date.fromisoformat(dia).weekday(),          # 0 = lunes
        "ingreso_ayer": uno("SELECT ingreso FROM caja_diaria WHERE dia = date(?, '-1 day')", dia),
        "promedio_7d": uno("SELECT AVG(ingreso) FROM caja_diaria WHERE dia >= date(?, '-7 day') AND dia < ?", dia, dia),
        "promedio_dia_semana": uno("SELECT AVG(ingreso) FROM caja_diaria "
                                   "WHERE strftime('%w', dia) = strftime('%w', ?) AND dia < ?", dia, dia),
    }

def decidir_nunca(p):                     # línea base: no hace nada
    return "NADA"

def decidir_reflejo(p):                   # agente reflejo simple: condición → acción
    return "PROMO" if p["ingreso_ayer"] < 0.8 * p["promedio_7d"] else "NADA"

def decidir_utilidad(p):                  # agente basado en utilidad: saca cuentas
    esperado = p["promedio_dia_semana"]
    u_nada, u_promo = esperado, esperado * FACTOR_PROMO - COSTO_PROMO
    return "PROMO" if u_promo > u_nada else "NADA"

def decidir_modelo(p):                    # RETO 1: usa la memoria (p. ej. compara con el mismo día de la semana)
    return "NADA"

def decidir_objetivo(p):                  # RETO 2: define una meta semanal y decide según lo que falta
    return "NADA"

def actuar(conn, dia, agente, accion, neto):
    """ACTUADOR: la decisión queda registrada con INSERT (TELL)."""
    conn.execute("INSERT INTO decisiones VALUES (?,?,?,?)", (dia, agente, accion, neto))

def entorno(demanda_real, dia, accion, codigo):
    """El mundo responde. El agente NO ve esta función: solo ve la caja al día siguiente."""
    ruido = random.Random(f"{codigo}-{dia}").uniform(0.85, 1.15)      # mismo ruido para todos los agentes
    base = demanda_real[dt.date.fromisoformat(dia).weekday()] * ruido
    bruto = base * FACTOR_PROMO if accion == "PROMO" else base
    return bruto, bruto - (COSTO_PROMO if accion == "PROMO" else 0.0)

def simular(codigo, decidir, nombre, n_ventas=600):
    conn = crear_base(codigo, n_ventas); preparar_agente(conn)
    demanda_real = {int(w): m for w, m in conn.execute(
        "SELECT (CAST(strftime('%w', dia) AS INTEGER) + 6) % 7, AVG(ingreso) FROM caja_diaria GROUP BY 1")}
    hoy = INICIO + dt.timedelta(days=DIAS_HISTORIA)
    for _ in range(DIAS_SIMULADOS):
        dia = hoy.isoformat()
        percepcion = percibir(conn, dia)                     # 1. percibir
        accion = decidir(percepcion)                         # 2. decidir
        bruto, neto = entorno(demanda_real, dia, accion, codigo)
        actuar(conn, dia, nombre, accion, neto)              # 3. actuar
        conn.execute("INSERT INTO caja_diaria VALUES (?,?)", (dia, bruto))
        hoy += dt.timedelta(days=1)
    return pd.read_sql("SELECT * FROM decisiones", conn)

AGENTES = {"nunca": decidir_nunca, "reflejo": decidir_reflejo, "utilidad": decidir_utilidad,
           "modelo": decidir_modelo, "objetivo": decidir_objetivo}

def torneo(codigo, agentes=None):
    filas = []
    for nombre, f in (agentes or AGENTES).items():
        d = simular(codigo, f, nombre)
        filas.append({"agente": nombre, "promos": int((d.accion == "PROMO").sum()),
                      "ingreso_neto": round(d.ingreso_neto.sum(), 1)})
    return pd.DataFrame(filas).sort_values("ingreso_neto", ascending=False, ignore_index=True)

# ---------------------------------------------------------------- 4. BONO: guardas para un agente LLM de texto a SQL
def ejecutar_seguro(ruta_db, sql, limite=200):
    """Ejecuta SOLO una sentencia SELECT, en modo solo lectura y con LIMIT."""
    s = sql.strip().rstrip(";").strip()
    if ";" in s or not s.lower().startswith(("select", "with")):
        raise ValueError("Guarda: solo se permite una sentencia SELECT.")
    ro = sqlite3.connect(f"file:{ruta_db}?mode=ro", uri=True)
    try:
        return pd.read_sql(f"SELECT * FROM ({s}) LIMIT {int(limite)}", ro)
    finally:
        ro.close()

if __name__ == "__main__":
    print(experimento_escala(CODIGO, (1_000, 100_000)))
    print(torneo(CODIGO))
