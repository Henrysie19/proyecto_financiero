# Pipeline ETL y análisis cuantitativo de activos

Proyecto independiente del motor de alertas de e-commerce. Construye un pipeline Python para descargar precios históricos ajustados, calcular señales estadísticas reproducibles y guardar los resultados en PostgreSQL local.

> Este proyecto es educativo y analítico; un Z-Score no es una recomendación de inversión ni predice el rendimiento futuro.

## Estado

**Fase 2 — Dashboard con análisis interpretativo; falta revisión visual en navegador**

- [x] Crear estructura de extracción, transformación, carga y orquestación.
- [x] Usar la API `yfinance` con opciones explícitas y validar los datos descargados.
- [x] Calcular estadísticas sobre las `N` sesiones previas, evitando incluir el precio actual en su propia referencia.
- [x] Crear tablas PostgreSQL con claves únicas y cargas idempotentes.
- [x] Añadir pruebas unitarias con datos/respuestas simulados.
- [x] Instalar dependencias y ejecutar las pruebas.
- [x] Iniciar PostgreSQL con Docker Compose y validar conexión real.
- [x] Ejecutar una descarga de prueba de 5 días para `SPY` con conexión a Internet.
- [x] Ejecutar el pipeline ETL completo y verificar las filas persistidas en PostgreSQL.
- [x] Repetir el pipeline y confirmar que la carga idempotente no duplica registros.
- [x] Instalar Streamlit y probar el dashboard contra la base real con `AppTest`.
- [x] Añadir análisis interpretativo debajo de los gráficos para sobreventa, sobrecompra, neutral e histórico insuficiente.
- [ ] Abrir el dashboard en navegador y revisar la experiencia visual.

## Diseño y señales

- `close` corresponde al precio ajustado por dividendos/splits porque la extracción usa `auto_adjust=True`.
- La media y desviación móvil usan las **20 observaciones previas** por defecto; la desviación estándar es muestral (`ddof=1`).
- `Z = (close_actual - media_previa) / desviación_previa`.
- `Z <= -2` se etiqueta `oversold`; `Z >= 2` se etiqueta `overbought`.
- Antes de disponer de ventana completa, o si la desviación es cero, la etiqueta es `insufficient_history`.
- La carga hace `UPSERT` por ticker/fecha y guarda precios y señales en la misma transacción.
- PostgreSQL solo escucha en `127.0.0.1`; no se publica el puerto en todas las interfaces.

## Estructura

```text
proyecto_financiero/
├── .env.example
├── docker-compose.yml
├── requirements.txt
├── README.md
├── app.py
├── src/
│   ├── analysis.py
│   ├── extract.py
│   ├── transform.py
│   ├── load.py
│   ├── main.py
│   └── dashboard_data.py
└── tests/
    ├── test_extract.py
    ├── test_transform.py
    ├── test_load.py
    ├── test_dashboard.py
    └── test_analysis.py
```

## Ejecutar el proyecto paso a paso (PowerShell)

Abre una terminal de VS Code en la carpeta `proyecto_financiero` o entra a ella desde la raíz del workspace:

```powershell
Set-Location .\proyecto_financiero
```

1. Instala las dependencias:

```powershell
py -m pip install -r requirements.txt
```

2. Asegúrate de que exista `.env`. Ya fue creado localmente para este proyecto. Si falta, créalo desde la plantilla:

```powershell
Copy-Item .env.example .env
```

Si lo creas de nuevo, asigna localmente un valor para `POSTGRES_PASSWORD` y utiliza el mismo en DBeaver. No uses credenciales reales reutilizadas ni compartas el archivo; `.env` está excluido por Git.

3. Inicia Docker Desktop y PostgreSQL:

```powershell
docker compose up -d
docker compose ps
```

Espera a que `postgres` aparezca como `healthy`.

4. Para descargar y guardar datos (repítelo cuando quieras actualizar el histórico):

```powershell
py -m src.main --tickers SPY --period 6mo --window 20 --threshold 2
```

5. Inicia el dashboard:

```powershell
py -m streamlit run app.py
```

Abre `http://localhost:8501`. El dashboard solo lee la base; no descarga ni modifica datos.

6. Para detener PostgreSQL sin borrar los datos:

```powershell
docker compose down
```

No agregues `-v`; borraría el volumen persistente.

Conexión desde DBeaver:

- Host: `localhost`
- Puerto: `5432`
- Base de datos: `financial_market`
- Usuario: `market_user`
- Contraseña: el valor local de `POSTGRES_PASSWORD` en `.env` (no compartirlo)

La aplicación y Compose leen el `.env` de esta carpeta, no el del proyecto de e-commerce ni variables heredadas del shell. Para configurar DBeaver, copia la contraseña localmente desde este archivo; no la pegues en el chat.

Ejecutar pruebas offline (no consulta Yahoo Finance ni PostgreSQL):

```powershell
py -m unittest discover -s tests -v
```

Ejecutar el pipeline:

```powershell
py -m src.main --tickers SPY AAPL --period 6mo --window 20 --threshold 2
```

Iniciar el dashboard (primero confirma que PostgreSQL esté arriba con `docker compose ps`):

```powershell
py -m streamlit run app.py
```

Streamlit abrirá el dashboard en el navegador, normalmente en `http://localhost:8501`. El selector muestra tickers guardados; el umbral modifica la clasificación visual de la señal y las líneas de referencia del Z-Score.

### Si DBeaver no muestra la base

La base fue verificada desde Python: PostgreSQL responde en `localhost:5432`, la base es `financial_market`, el usuario `market_user`, y las tablas `historical_prices` y `market_signals` contienen registros de `SPY`. En DBeaver crea o edita una conexión **PostgreSQL** con esos valores (no uses `warehouse/admin`, que pertenecían a la configuración heredada anterior). Copia localmente la contraseña desde `POSTGRES_PASSWORD` en `.env` de esta carpeta; no la publiques. Pulsa **Test Connection**, guarda, desconecta y reconecta, y actualiza el navegador del árbol de bases. Si DBeaver tiene configurado “Show all databases”, se puede dejar apagado: lo importante es que el campo **Database** sea `financial_market`.

Puedes comprobar las tablas con este SQL en DBeaver:

```sql
SELECT ticker, price_date, close
FROM historical_prices
ORDER BY price_date DESC
LIMIT 10;

SELECT ticker, signal_date, z_score, signal
FROM market_signals
ORDER BY signal_date DESC
LIMIT 10;
```

Los símbolos, datos de Yahoo Finance, límites de consulta y disponibilidad de sus datos dependen del proveedor. La extracción usa su biblioteca cliente y puede fallar por conectividad o disponibilidad; los errores se reportan, no se convierten en datos vacíos exitosos.

## Bitácora / cómo retomar

**Última actualización:** 2026-10-24.

**Decisión de continuidad:** el proyecto financiero vive en esta subcarpeta para conservar intactos los archivos y la bitácora de e-commerce.

**Entorno observado:** Python 3.14.6, dependencias y Docker Desktop instalados. La primera carga detectó variables heredadas de otro proyecto (`warehouse/admin`), así que aislamos la configuración: Compose usa el `.env` de este directorio y un volumen dedicado `financial_market_pgdata_v2`; la aplicación obtiene conexión solo de este `.env`. El contenedor quedó saludable y conectó a `financial_market` como `market_user`. El volumen anterior `proyecto_financiero_postgres_data` se conserva sin montar en el servicio actual; contenía las 5 filas de la primera carga. No se borró ningún volumen.

**Validación end-to-end:** `py -m unittest discover -s tests -v` pasó las 9 pruebas. `docker compose config --quiet` validó la configuración. `py -m src.main --tickers SPY --period 5d --window 2 --threshold 2` descargó y guardó 5 precios y 5 señales (fechas 2026-10-19 a 2026-10-23); se verificó que `market_signals` contiene 2 señales extremas en esa ventana. Una segunda ejecución volvió a informar 5 precios y 5 señales, y el conteo quedó en 5/5, confirmando idempotencia.

**Validación de PostgreSQL/DBeaver:** la base `financial_market` y el usuario `market_user` se verificaron por conexión directa; ambas tablas tienen 5 filas de SPY. Si no se ven en DBeaver, revisar que la conexión use los parámetros indicados y actualizar/reconectar el navegador.

**Dashboard:** se creó `app.py` con selector dinámico de tickers, umbral configurable, KPIs, clasificación por Z-Score y dos gráficos Plotly. Las consultas de solo lectura se separaron en `src/dashboard_data.py`. El dashboard carga `SPY` y cinco observaciones desde la base activa; `AppTest` se ejecutó sin excepciones y verificó los dos KPIs y dos gráficos. Los valores observados fueron cierre `759.97` y Z-Score `-1.33`.

**Análisis interpretativo:** se añadió `src/analysis.py` y una sección después de ambos gráficos. Interpreta Z-Score extremo, neutral o sin histórico suficiente, usando el umbral del sidebar y mostrando cierre/media. El texto evita afirmar que habrá rebotes/caídas o dar recomendación personalizada; incluye contexto educativo sobre límites del indicador.

**Validación de análisis:** `py -m unittest discover -s tests -v` pasó 17 pruebas. `AppTest` cargó los datos reales actuales de `SPY` y comprobó 2 métricas, 2 gráficos y la sección interpretativa sin excepciones. La señal puede variar al actualizarse el histórico; el dashboard toma la última fila disponible.

**Siguiente paso:** desde esta carpeta abrir `py -m streamlit run app.py` para revisar la experiencia visual en `http://localhost:8501`. Si DBeaver apunta a otra base, conectarlo a `financial_market` en `localhost:5432` con `market_user`; copiar la contraseña localmente desde `.env`, sin compartirla.
