# Devociones Automáticas

Sistema de extracción y publicación automatizada de devociones desde [devocionmatutina.com](https://devocionmatutina.com) en Facebook, con revisión humana previa vía Telegram.

---

## Descripción del flujo

```
[6:00 AM] GitHub Actions ejecuta "Revisar Devociones"
      ↓
  Scraper extrae las 6 devociones del día
      ↓
  Envía resúmenes a Telegram para revisión
      ↓
  [Usuario revisa y aprueba]
      ↓
  Usuario ejecuta "Publicar Devociones" desde GitHub Actions
      ↓
  Se publican en la página de Facebook
      ↓
  Se registran en SQLite para evitar duplicados
```

---

## Estructura del proyecto

```
Devociones-automaticas/
├── main.py              # Punto de entrada (modos: revisar / publicar)
├── scraper.py           # Extracción desde devocionmatutina.com
├── telegram_bot.py      # Notificaciones a Telegram
├── facebook.py          # Publicación en Facebook Graph API
├── database.py          # Persistencia SQLite
├── requirements.txt     # Dependencias Python
├── README.md
├── .gitignore
├── data/
│   └── publicados.db    # Base de datos (generada automáticamente, ignorada por git)
└── .github/
    └── workflows/
        ├── revisar.yml   # Workflow automático (6 AM diario)
        └── publicar.yml  # Workflow manual (ejecuta el usuario)
```

---

## Instalación local

### 1. Clonar el repositorio

```bash
git clone https://github.com/liriocortez-dotcom/Devociones-automaticas.git
cd Devociones-automaticas
```

### 2. Crear entorno virtual

```bash
python3.12 -m venv .venv
source .venv/bin/activate        # Linux/macOS
.venv\Scripts\activate           # Windows
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

---

## Configuración de variables de entorno (local)

Crea un archivo `.env` en la raíz del proyecto (no se sube a Git):

```env
TELEGRAM_BOT_TOKEN=tu_token_aqui
TELEGRAM_CHAT_ID=tu_chat_id_aqui
FACEBOOK_PAGE_ACCESS_TOKEN=tu_page_access_token_aqui
FACEBOOK_PAGE_ID=114590400325920
```

Carga las variables antes de ejecutar:

```bash
export $(cat .env | xargs)   # Linux/macOS
```

O usa [`python-dotenv`](https://pypi.org/project/python-dotenv/) si lo prefieres.

---

## Ejecución local

```bash
# Modo revisión: extrae devociones y las envía a Telegram
python main.py revisar

# Modo publicación: publica en Facebook y registra en SQLite
python main.py publicar
```

---

## Configuración de GitHub Secrets

Ve a tu repositorio en GitHub → **Settings → Secrets and variables → Actions → New repository secret**.

Crea los siguientes secrets:

| Secret | Descripción |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token de tu bot de Telegram (obtenido desde [@BotFather](https://t.me/BotFather)) |
| `TELEGRAM_CHAT_ID` | ID del chat/grupo donde recibirás los resúmenes |
| `FACEBOOK_PAGE_ACCESS_TOKEN` | Page Access Token de Facebook (ver sección siguiente) |
| `FACEBOOK_PAGE_ID` | ID de tu página: `114590400325920` |

---

## Cómo obtener las credenciales

### Telegram Bot Token

1. Abre Telegram y busca `@BotFather`.
2. Envía `/newbot` y sigue las instrucciones.
3. Copia el token que te entrega.

### Telegram Chat ID

1. Añade tu bot a un chat o grupo.
2. Envía cualquier mensaje al bot.
3. Visita: `https://api.telegram.org/bot<TU_TOKEN>/getUpdates`
4. Busca el campo `chat.id` en la respuesta JSON.

### Facebook Page Access Token

1. Ve a [Meta for Developers](https://developers.facebook.com/).
2. Crea una app de tipo **Business**.
3. Agrega el producto **Facebook Login**.
4. En **Graph API Explorer**, selecciona tu app y tu página.
5. Solicita los permisos: `pages_manage_posts`, `pages_read_engagement`.
6. Genera un **Page Access Token de larga duración** (Long-Lived Token).

> ⚠️ Los tokens de corta duración expiran en 1 hora. Para producción debes convertirlo a largo plazo usando el endpoint de intercambio de tokens.

---

## Despliegue en GitHub Actions

Los workflows se configuran automáticamente al subir el código al repositorio.

### Workflow `Revisar Devociones`

Se ejecuta **automáticamente** todos los días a las **6:00 AM hora de México** (12:00 UTC).

También puedes ejecutarlo manualmente desde:
**GitHub → Actions → Revisar Devociones → Run workflow**

### Workflow `Publicar Devociones`

Solo se ejecuta **manualmente**:

1. Ve a **GitHub → Actions**.
2. Selecciona **Publicar Devociones**.
3. Haz clic en **Run workflow**.

---

## Solución de problemas

### No llegan mensajes a Telegram

- Verifica que `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` estén correctamente definidos en los Secrets.
- Asegúrate de haber enviado al menos un mensaje al bot antes de que pueda escribirte.
- Para grupos, asegúrate de haber añadido el bot como miembro.

### Error al publicar en Facebook

- Verifica que el `FACEBOOK_PAGE_ACCESS_TOKEN` no haya expirado.
- Asegúrate de que la app de Facebook tenga los permisos `pages_manage_posts`.
- Revisa el log del workflow en GitHub Actions para el código de error exacto.

### El scraper no encuentra devociones

- El sitio puede haber cambiado su HTML. Revisa el log y abre un issue.
- Puedes ejecutar `python main.py revisar` localmente con logs para diagnosticar.

### Duplicados en publicaciones

- La base de datos `data/publicados.db` se crea localmente pero **no persiste entre ejecuciones de GitHub Actions** (el filesystem se reinicia en cada ejecución).
- Si necesitas persistencia real, considera hacer commit de la DB o usar un servicio externo gratuito (p.ej. GitHub Releases como storage de archivos binarios).

---

## Pruebas locales rápidas

```bash
# Solo probar el scraper
python -c "from scraper import obtener_devociones; d = obtener_devociones(); print(f'{len(d)} devociones encontradas'); [print(x[\"categoria\"], x[\"titulo\"]) for x in d]"

# Solo probar Telegram
python -c "from telegram_bot import enviar_resumen; enviar_resumen([{'categoria':'Test','fecha':'2024-01-01','titulo':'Prueba','texto':'Texto de prueba de 500 caracteres o menos.','url':'https://ejemplo.com'}])"

# Solo inicializar la DB
python -c "import database; database.init_db(); print('DB OK')"
```

---

## Tecnologías utilizadas

- **Python 3.12**
- **SQLite** — persistencia de publicaciones
- **Requests** — peticiones HTTP
- **BeautifulSoup4** — parsing HTML
- **Telegram Bot API** — notificaciones
- **Facebook Graph API v19.0** — publicación
- **GitHub Actions** — automatización CI/CD

**Costo mensual: $0 USD** — todo el stack es gratuito.

---

## Licencia

El código fuente de este proyecto es libre de uso. El contenido de las devociones pertenece a sus autores y se republica con autorización expresa.
