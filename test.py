#!/usr/bin/env python3
import httpx
import requests
from urllib.parse import urlparse
import traceback

# URL de prueba
URL = "https://im.vsco.co/aws-us-west-2/0baa3b/57604661/67dc16ee388c7b71342fed40/vsco_032025.jpg"

print("="*60)
print("PRUEBA DE REDIRECCIÓN VSCO")
print("="*60)

# ============= PRUEBA 1: httpx sin seguir redirecciones =============
print("\n[1] HTTPX - Sin seguir redirecciones:")
print("-"*40)
try:
    with httpx.Client(follow_redirects=False) as client:
        response = client.get(URL)
        print(f"Status Code: {response.status_code}")
        print(f"URL Final: {response.url}")
        
        # Verificar si hay header Location (redirección)
        if 'Location' in response.headers:
            print(f"Redirección detectada -> {response.headers['Location']}")
        else:
            print("No hay header 'Location'")
            
        # Mostrar todos los headers de respuesta
        print("\nHeaders de respuesta:")
        for key, value in response.headers.items():
            print(f"  {key}: {value}")
            
except Exception as e:
    print(f"ERROR: {e}")
    traceback.print_exc()

# ============= PRUEBA 2: httpx siguiendo redirecciones =============
print("\n[2] HTTPX - Siguiendo redirecciones:")
print("-"*40)
try:
    with httpx.Client(follow_redirects=True, max_redirects=10) as client:
        response = client.get(URL)
        print(f"Status Code: {response.status_code}")
        print(f"URL Final: {response.url}")
        print(f"Número de redirecciones: {len(response.history)}")
        
        # Mostrar historial de redirecciones
        if response.history:
            print("\nHistorial de redirecciones:")
            for i, r in enumerate(response.history):
                print(f"  {i+1}. {r.url} -> {r.status_code}")
                if 'Location' in r.headers:
                    print(f"      Redirige a: {r.headers['Location']}")
        else:
            print("No hubo redirecciones")
            
except Exception as e:
    print(f"ERROR: {e}")
    traceback.print_exc()

# ============= PRUEBA 3: requests con diferentes headers =============
print("\n[3] REQUESTS - Con headers de navegador:")
print("-"*40)
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache',
    'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Windows"',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
}

try:
    # Sin seguir redirecciones
    response = requests.get(URL, headers=headers, allow_redirects=False)
    print(f"Status Code (sin redir): {response.status_code}")
    
    if response.status_code in [301, 302, 303, 307, 308]:
        print(f"Redirección detectada -> {response.headers.get('Location', 'NO LOCATION HEADER')}")
    
    # Siguiendo redirecciones
    response = requests.get(URL, headers=headers, allow_redirects=True)
    print(f"Status Code (con redir): {response.status_code}")
    print(f"URL Final: {response.url}")
    print(f"Historial: {[r.url for r in response.history]}")
    
    if response.status_code == 200:
        print(f"Tamaño de imagen: {len(response.content)} bytes")
    
except Exception as e:
    print(f"ERROR: {e}")
    traceback.print_exc()

# ============= PRUEBA 4: Probar URL transformada manualmente =============
print("\n[4] PRUEBA URL TRANSFORMADA:")
print("-"*40)
# Transformar im.vsco.co/aws-us-west-2/ -> img.vsco.co/
transformed_url = URL.replace('im.vsco.co/aws-us-west-2/', 'img.vsco.co/')
print(f"URL Original: {URL}")
print(f"URL Transformada: {transformed_url}")

try:
    response = requests.get(transformed_url, headers=headers)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print(f"✅ ÉXITO! Tamaño: {len(response.content)} bytes")
        # Guardar imagen para verificar
        with open("test_vsco.jpg", "wb") as f:
            f.write(response.content)
        print("Imagen guardada como 'test_vsco.jpg'")
except Exception as e:
    print(f"ERROR: {e}")

# ============= PRUEBA 5: curl command para comparar =============
print("\n[5] COMANDO CURL EQUIVALENTE:")
print("-"*40)
print(f"curl -I -L '{URL}'")
print("\nPrueba también:")
print(f"curl -I '{URL}' --header 'User-Agent: Mozilla/5.0'")