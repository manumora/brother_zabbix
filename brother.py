import requests
import os
import subprocess
import re
import argparse
from bs4 import BeautifulSoup

def extract_printer_data(html_content):
    """
    Extracts all maintenance data from the HTML page.
    
    Args:
        html_content: HTML content of the page
        
    Returns:
        dict: Dictionary with all extracted data
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    data = {
        'toner': {},
        'drum': {},
        'belt_unit': {},
        'fuser_unit': {},
        'pages_printed': {}
    }
    
    # Search for all dt elements
    for dt in soup.find_all('dt'):
        text = dt.get_text().strip()
        dd = dt.find_next_sibling('dd')
        if not dd:
            continue
            
        value_text = dd.get_text().strip()
        
        # Extract Toner levels
        if 'Toner' in text and '**' in text:
            color = None
            if 'Cyan' in text:
                color = 'cyan'
            elif 'Magenta' in text:
                color = 'magenta'
            elif 'Yellow' in text:
                color = 'yellow'
            elif 'Black' in text:
                color = 'black'
            
            if color:
                match = re.search(r'(\d+)%', value_text)
                if match:
                    data['toner'][color] = int(match.group(1))
        
        # Extract Drum Unit levels
        elif 'Drum Unit' in text and '*' in text:
            color = None
            if 'Cyan' in text:
                color = 'cyan'
            elif 'Magenta' in text:
                color = 'magenta'
            elif 'Yellow' in text:
                color = 'yellow'
            elif 'Black' in text:
                color = 'black'
            
            if color:
                match = re.search(r'(\d+)%', value_text)
                if match:
                    data['drum'][color] = int(match.group(1))
        
        # Extract Belt Unit (only the first time we find it)
        elif 'Belt Unit' == text and not data['belt_unit']:
            match = re.search(r'(\d+)', value_text)
            if match:
                data['belt_unit']['pages'] = int(match.group(1))
            # Search for the percentage in the next element
            next_dt = dt.find_next_sibling('dt')
            if next_dt and 'Life Remaining' in next_dt.get_text():
                next_dd = next_dt.find_next_sibling('dd')
                if next_dd:
                    match_pct = re.search(r'(\d+)%', next_dd.get_text())
                    if match_pct:
                        data['belt_unit']['percent'] = int(match_pct.group(1))
        
        # Extract Fuser Unit (only the first time we find it)
        elif 'Fuser Unit' == text and not data['fuser_unit']:
            match = re.search(r'(\d+)', value_text)
            if match:
                data['fuser_unit']['pages'] = int(match.group(1))
            # Search for the percentage in the next element
            next_dt = dt.find_next_sibling('dt')
            if next_dt and 'Life Remaining' in next_dt.get_text():
                next_dd = next_dt.find_next_sibling('dd')
                if next_dd:
                    match_pct = re.search(r'(\d+)%', next_dd.get_text())
                    if match_pct:
                        data['fuser_unit']['percent'] = int(match_pct.group(1))
    
    # Extract Total Pages Printed
    # Search for the "Total Pages Printed" section that has the overall total
    for h3 in soup.find_all('h3'):
        if 'Total Pages Printed' in h3.get_text():
            # Search for the next dl with items_info_1line class
            dl = h3.find_next('dl', class_='items_info_1line')
            if dl:
                found_total = False
                # Search for the dt with "Total"
                for dt in dl.find_all('dt'):
                    text_dt = dt.get_text().strip()
                    
                    if text_dt == 'Total':
                        dd = dt.find_next_sibling('dd')
                        if dd:
                            match = re.search(r'(\d+)', dd.get_text())
                            if match:
                                data['pages_printed']['total'] = int(match.group(1))
                                found_total = True
                    
                    # Only extract Colour and B&W if we already found Total
                    # and they are the first subheads after Total
                    elif found_total and dt.get('class') and 'subhead' in dt.get('class'):
                        span = dt.find('span')
                        if span:
                            span_text = span.get_text().strip()
                            if span_text == 'Colour' and 'colour' not in data['pages_printed']:
                                dd = dt.find_next_sibling('dd')
                                if dd:
                                    match = re.search(r'(\d+)', dd.get_text())
                                    if match:
                                        data['pages_printed']['colour'] = int(match.group(1))
                            elif span_text == 'B&W' and 'bw' not in data['pages_printed']:
                                dd = dt.find_next_sibling('dd')
                                if dd:
                                    match = re.search(r'(\d+)', dd.get_text())
                                    if match:
                                        data['pages_printed']['bw'] = int(match.group(1))
                        
                        # If we already have the three values, exit
                        if len(data['pages_printed']) == 3:
                            break
                # We only need the first "Total Pages Printed" with the overall total
                break
    
    return data

def send_to_zabbix(hostname, data, zabbix_server="127.0.0.1", zabbix_port=10051):
    """
    Sends all printer data to Zabbix using zabbix_sender.
    
    Args:
        hostname: Host name in Zabbix
        data: Dictionary with all extracted data (toner, drum, belt, fuser)
        zabbix_server: Zabbix server address
        zabbix_port: Zabbix server port
        
    Returns:
        bool: True if sending was successful, False otherwise
    """
    try:
        sent = 0
        errors = 0
        
        # Mapping for Toner levels
        if 'toner' in data:
            print("\n📊 Sending Toner levels...")
            for color, level in data['toner'].items():
                item_key = f'brother.toner.{color}'
                cmd = [
                    'zabbix_sender',
                    '-z', zabbix_server,
                    '-p', str(zabbix_port),
                    '-s', hostname,
                    '-k', item_key,
                    '-o', str(level)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    print(f"  ✓ Toner {color.capitalize()}: {level}%")
                    sent += 1
                else:
                    print(f"  ✗ Error sending Toner {color}: {result.stderr}")
                    errors += 1
        
        # Mapping for Drum Units
        if 'drum' in data:
            print("\n🥁 Sending Drum Unit levels...")
            for color, level in data['drum'].items():
                item_key = f'brother.drum.{color}'
                cmd = [
                    'zabbix_sender',
                    '-z', zabbix_server,
                    '-p', str(zabbix_port),
                    '-s', hostname,
                    '-k', item_key,
                    '-o', str(level)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    print(f"  ✓ Drum {color.capitalize()}: {level}%")
                    sent += 1
                else:
                    print(f"  ✗ Error sending Drum {color}: {result.stderr}")
                    errors += 1
        
        # Belt Unit
        if 'belt_unit' in data and data['belt_unit']:
            print("\n🔧 Sending Belt Unit data...")
            
            if 'pages' in data['belt_unit']:
                cmd = [
                    'zabbix_sender',
                    '-z', zabbix_server,
                    '-p', str(zabbix_port),
                    '-s', hostname,
                    '-k', 'brother.belt.pages',
                    '-o', str(data['belt_unit']['pages'])
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"  ✓ Belt Unit pages: {data['belt_unit']['pages']}")
                    sent += 1
                else:
                    print(f"  ✗ Error sending Belt Unit pages: {result.stderr}")
                    errors += 1
            
            if 'percent' in data['belt_unit']:
                cmd = [
                    'zabbix_sender',
                    '-z', zabbix_server,
                    '-p', str(zabbix_port),
                    '-s', hostname,
                    '-k', 'brother.belt.percent',
                    '-o', str(data['belt_unit']['percent'])
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"  ✓ Belt Unit remaining life: {data['belt_unit']['percent']}%")
                    sent += 1
                else:
                    print(f"  ✗ Error sending Belt Unit percentage: {result.stderr}")
                    errors += 1
        
        # Fuser Unit
        if 'fuser_unit' in data and data['fuser_unit']:
            print("\n🔥 Sending Fuser Unit data...")
            
            if 'pages' in data['fuser_unit']:
                cmd = [
                    'zabbix_sender',
                    '-z', zabbix_server,
                    '-p', str(zabbix_port),
                    '-s', hostname,
                    '-k', 'brother.fuser.pages',
                    '-o', str(data['fuser_unit']['pages'])
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"  ✓ Fuser Unit pages: {data['fuser_unit']['pages']}")
                    sent += 1
                else:
                    print(f"  ✗ Error sending Fuser Unit pages: {result.stderr}")
                    errors += 1
            
            if 'percent' in data['fuser_unit']:
                cmd = [
                    'zabbix_sender',
                    '-z', zabbix_server,
                    '-p', str(zabbix_port),
                    '-s', hostname,
                    '-k', 'brother.fuser.percent',
                    '-o', str(data['fuser_unit']['percent'])
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"  ✓ Fuser Unit remaining life: {data['fuser_unit']['percent']}%")
                    sent += 1
                else:
                    print(f"  ✗ Error sending Fuser Unit percentage: {result.stderr}")
                    errors += 1
        
        # Pages printed
        if 'pages_printed' in data and data['pages_printed']:
            print("\n📄 Sending printed pages data...")
            
            if 'total' in data['pages_printed']:
                cmd = [
                    'zabbix_sender',
                    '-z', zabbix_server,
                    '-p', str(zabbix_port),
                    '-s', hostname,
                    '-k', 'brother.pages.total',
                    '-o', str(data['pages_printed']['total'])
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"  ✓ Total pages: {data['pages_printed']['total']}")
                    sent += 1
                else:
                    print(f"  ✗ Error sending total pages: {result.stderr}")
                    errors += 1
            
            if 'colour' in data['pages_printed']:
                cmd = [
                    'zabbix_sender',
                    '-z', zabbix_server,
                    '-p', str(zabbix_port),
                    '-s', hostname,
                    '-k', 'brother.pages.colour',
                    '-o', str(data['pages_printed']['colour'])
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"  ✓ Colour pages: {data['pages_printed']['colour']}")
                    sent += 1
                else:
                    print(f"  ✗ Error sending colour pages: {result.stderr}")
                    errors += 1
            
            if 'bw' in data['pages_printed']:
                cmd = [
                    'zabbix_sender',
                    '-z', zabbix_server,
                    '-p', str(zabbix_port),
                    '-s', hostname,
                    '-k', 'brother.pages.bw',
                    '-o', str(data['pages_printed']['bw'])
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"  ✓ B&W pages: {data['pages_printed']['bw']}")
                    sent += 1
                else:
                    print(f"  ✗ Error sending B&W pages: {result.stderr}")
                    errors += 1
        
        print(f"\n{'='*60}")
        print(f"Summary: {sent} values sent successfully, {errors} errors")
        print(f"{'='*60}")
        
        return errors == 0
        
    except FileNotFoundError:
        print("Error: zabbix_sender is not installed or not in PATH")
        print("Install it with: sudo apt-get install zabbix-sender")
        return False
    except Exception as e:
        print(f"Error sending data to Zabbix: {e}")
        return False

def login_y_descargar_html(url_base, contrasena, ruta_destino="pagina_descargada.html"):
    """
    Logs into a website and downloads the HTML from a page.
    
    Args:
        url_base: Base URL of the website
        contrasena: Password to login
        ruta_destino: Path where the downloaded HTML will be saved
        
    Returns:
        str: Downloaded HTML content or None if there's an error
    """
    # Create a session to maintain cookies
    session = requests.Session()
    
    # Form data for login
    login_data = {
        "B1889": contrasena,
        "loginurl": "/general/information.html?kind=item"
    }
    
    # URL for login
    login_url = f"{url_base}/home/status.html"
    
    try:
        # Perform the login request
        print("Attempting to login...")
        response_login = session.post(login_url, data=login_data)
        response_login.raise_for_status()  # Check if there are errors in the response
        
        # Verify if login was successful (this depends on the site's behavior)
        if "Iniciar sesión" in response_login.text:
            print("Error: Could not login. Check the password.")
            return None
        
        print("Login successful")
        
        # URL to download after login
        # Here I'm using the URL provided in loginurl, but you can change it
        target_url = f"{url_base}/general/information.html?kind=item"
        
        # Download the page after login
        print(f"Downloading content from {target_url}...")
        response_download = session.get(target_url)
        response_download.raise_for_status()
        
        # Save the downloaded HTML to a file
        with open(ruta_destino, "w", encoding="utf-8") as file:
            file.write(response_download.text)
        
        print(f"HTML downloaded and saved to '{ruta_destino}'")
        return response_download.text
    
    except requests.exceptions.RequestException as e:
        print(f"Error during HTTP request: {e}")
        return None

if __name__ == "__main__":
    # Configure argument parser
    parser = argparse.ArgumentParser(description='Script to extract Brother printer data and send it to Zabbix')
    parser.add_argument('--url', required=True, help='Brother printer URL (e.g.: http://172.23.36.16)')
    parser.add_argument('--password', required=True, help='Printer password')
    parser.add_argument('--zabbix-server', required=True, help='Zabbix server IP (e.g.: 172.23.36.6)')
    parser.add_argument('--zabbix-port', type=int, default=10051, help='Zabbix server port (default: 10051)')
    parser.add_argument('--zabbix-hostname', required=True, help='Hostname of the host in Zabbix (e.g.: imp-secretaria)')
    parser.add_argument('--output', default='pagina_descargada.html', help='File where to save the downloaded HTML (default: pagina_descargada.html)')
    
    args = parser.parse_args()
    
    # Configuration from parameters
    URL_BASE = args.url
    PASSWORD = args.password
    RUTA_DESTINO = args.output
    
    # Zabbix configuration from parameters
    ZABBIX_SERVER = args.zabbix_server
    ZABBIX_PORT = args.zabbix_port
    ZABBIX_HOSTNAME = args.zabbix_hostname
    
    # Download the HTML
    print("\n" + "="*60)
    print("STEP 1: Downloading printer information")
    print("="*60)
    html_content = login_y_descargar_html(URL_BASE, PASSWORD, RUTA_DESTINO)
    
    if html_content:
        # Extract all maintenance data
        print("\n" + "="*60)
        print("STEP 2: Extracting maintenance data")
        print("="*60)
        datos = extract_printer_data(html_content)
        
        # Delete the temporary HTML file
        try:
            if os.path.exists(RUTA_DESTINO):
                os.remove(RUTA_DESTINO)
                print(f"✓ Temporary file '{RUTA_DESTINO}' deleted")
        except Exception as e:
            print(f"⚠ Warning: Could not delete temporary file: {e}")
        
        if datos:
            # Show extracted data
            print("\n📊 EXTRACTED DATA:")
            print("="*60)
            
            if datos['toner']:
                print("\n🖨️  Toner Levels:")
                for color, nivel in datos['toner'].items():
                    print(f"  - {color.capitalize()}: {nivel}%")
            
            if datos['drum']:
                print("\n🥁 Drum Units:")
                for color, nivel in datos['drum'].items():
                    print(f"  - {color.capitalize()}: {nivel}%")
            
            if datos['belt_unit']:
                print("\n🔧 Belt Unit:")
                if 'pages' in datos['belt_unit']:
                    print(f"  - Remaining pages: {datos['belt_unit']['pages']}")
                if 'percent' in datos['belt_unit']:
                    print(f"  - Remaining life: {datos['belt_unit']['percent']}%")
            
            if datos['fuser_unit']:
                print("\n🔥 Fuser Unit:")
                if 'pages' in datos['fuser_unit']:
                    print(f"  - Remaining pages: {datos['fuser_unit']['pages']}")
                if 'percent' in datos['fuser_unit']:
                    print(f"  - Remaining life: {datos['fuser_unit']['percent']}%")
            
            if datos['pages_printed']:
                print("\n📄 Printed Pages:")
                if 'total' in datos['pages_printed']:
                    print(f"  - Total: {datos['pages_printed']['total']} pages")
                if 'colour' in datos['pages_printed']:
                    print(f"  - Colour: {datos['pages_printed']['colour']} pages")
                if 'bw' in datos['pages_printed']:
                    print(f"  - B&W: {datos['pages_printed']['bw']} pages")
            
            # Send to Zabbix
            print("\n" + "="*60)
            print("STEP 3: Sending data to Zabbix")
            print("="*60)
            send_to_zabbix(ZABBIX_HOSTNAME, datos, ZABBIX_SERVER, ZABBIX_PORT)
        else:
            print("Could not extract data from HTML")
    else:
        print("Could not download printer content")
