from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ExifTags, TiffImagePlugin
import io
import os
import sys
import httpx
from pydantic import BaseModel
import traceback 
from pprint import pprint 

app = FastAPI()

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Lista los dominios si es necesario
    allow_credentials=True,
    allow_methods=["POST"],  # Métodos HTTP permitidos
    allow_headers=["*"],
)

class ImageUrl(BaseModel):
    url: str

def cast(value):
    """Convierte valores no serializables a formatos compatibles con JSON."""
    if isinstance(value, TiffImagePlugin.IFDRational):
        return float(value)
    elif isinstance(value, tuple):
        return tuple(cast(t) for t in value)
    elif isinstance(value, bytes):
        return value.decode(errors="replace")
    elif isinstance(value, dict):
        return {kk: cast(vv) for kk, vv in value.items()}
    else:
        return value

@app.post("/getExifFromUrl/")
async def get_exif_from_url(image_url: ImageUrl):
    try:
        async with httpx.AsyncClient(follow_redirects=False) as client:

            print(f"INPUT URL: {image_url.url}")

            response = await client.get(image_url.url)

            urls_visited = [str(response.url)]  # Convertir la URL a str para evitar problemas de serialización
            while response.is_redirect:
                response = await client.get(response.headers["Location"])
                urls_visited.append(str(response.url))  # Convertir cada URL redirigida a str

            final_url = urls_visited[-1]
            print(f"URL: {final_url}")

            # Descargar la imagen desde la URL final
            response = await client.get(final_url)
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Error descargando la imagen desde la URL final.")

            # Procesar la imagen para obtener los metadatos EXIF
            image = Image.open(io.BytesIO(response.content))
            exif_data = image._getexif() or {}
            exif = {ExifTags.TAGS.get(k, k): cast(v) for k, v in exif_data.items()}

            pprint(exif)

            return JSONResponse(content={"url": final_url, "EXIF": exif})
    except Exception as e:
        traceback.print_exc()
        
        print('### Error getExifFromUrl: ' + str(e))
        
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)

        return JSONResponse(content={"error": str(e)}, status_code=500)