# Brother Printer Monitor for Zabbix

Este script en Python permite extraer información de mantenimiento de impresoras Brother (niveles de tóner, tambor, fusor, correa y contador de páginas) y enviarla automáticamente a un servidor Zabbix mediante `zabbix_sender`.

## 📋 Funcionalidades

*   Conexión y autenticación automática en la interfaz web de la impresora Brother.
*   Extracción (Scraping) de datos de mantenimiento:
    *   Niveles de Tóner (Cian, Magenta, Amarillo, Negro).
    *   Vida útil de la Unidad de Tambor (Drum Unit).
    *   Vida útil y páginas de la Unidad de Correa (Belt Unit).
    *   Vida útil y páginas de la Unidad de Fusor (Fuser Unit).
    *   Contadores de páginas impresas (Total, Color, Blanco y Negro).
*   Envío de métricas a Zabbix Server/Proxy.
*   Soporte para interfaces en Inglés y Español.

## 🛠️ Requisitos Previos

### Sistema Operativo
*   Tener instalado `zabbix_sender`.
    ```bash
    # En Debian/Ubuntu
    sudo apt-get install zabbix-sender
    ```

### Python
*   Python 3.x
*   Librerías necesarias:
    ```bash
    pip install requests beautifulsoup4
    ```

## 🚀 Uso

El script se ejecuta desde la línea de comandos pasando los parámetros necesarios:

```bash
python3 brother.py \
  --url "http://192.168.1.50" \
  --password "TuPasswordDeImpresora" \
  --zabbix-server "192.168.1.10" \
  --zabbix-hostname "Impresora_RRHH"
```

### Argumentos

| Argumento | Obligatorio | Descripción | Ejemplo |
|-----------|-------------|-------------|---------|
| `--url` | Sí | URL base de la impresora Brother. | `http://192.168.1.50` |
| `--password` | Sí | Contraseña de acceso web a la impresora. | `initpass` |
| `--zabbix-server` | Sí | IP o Hostname del servidor Zabbix (o Proxy). | `192.168.1.10` |
| `--zabbix-hostname` | Sí | Nombre del Host configurado en Zabbix. | `Impresora_RRHH` |
| `--zabbix-port` | No | Puerto del servidor Zabbix (Default: 10051). | `10051` |
| `--output` | No | Archivo temporal para el HTML descargado. | `/tmp/debug.html` |

## ⚙️ Configuración en Zabbix

Para que Zabbix reciba los datos correctamente, debes crear un **Host** con el nombre que pases en el argumento `--zabbix-hostname` y configurar **Items** de tipo "Zabbix trapper" con las siguientes "Keys":

### Niveles de Tóner
*   `cyan.toner.level`
*   `magenta.toner.level`
*   `yellow.toner.level`
*   `black.toner.level`

### Unidad de Tambor (Drum)
*   `cyan.drum.level`
*   `magenta.drum.level`
*   `yellow.drum.level`
*   `black.drum.level`

### Otros Consumibles
*   `brother.belt.pages` (Páginas unidad de correa)
*   `brother.belt.percent` (Porcentaje vida unidad de correa)
*   `brother.fuser.pages` (Páginas unidad de fusor)
*   `brother.fuser.percent` (Porcentaje vida unidad de fusor)

### Contadores de Páginas
*   `brother.pages.total`
*   `brother.pages.colour`
*   `brother.pages.bw`

## 📄 Licencia
Este proyecto es de uso libre.
