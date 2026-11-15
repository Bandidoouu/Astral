# Procedencia de las texturas

Recursos visuales de contexto; no se usan para calcular puntajes. El relieve lunar y marciano usa los DEM indicados al final.
Fuentes ya enumeradas en docs/datos.md §4. Registro local pendiente de copiar a
ese documento en una tarea de integración, fuera del ámbito de Hanna.

- earth.jpg: NASA Earth Observatory, Blue Marble Next Generation, enero 2004,
  topografía/batimetría sombreada, mapa global 5400×2700.
  https://science.nasa.gov/earth/earth-observatory/blue-marble-next-generation/base-topography-bathymetry/
  Descarga: Invoke-WebRequest -UseBasicParsing 'https://assets.science.nasa.gov/content/dam/science/esd/eo/images/bmng/bmng-topography-bathymetry/january/world.topo.bathy.200401.3x5400x2700.jpg' -OutFile earth.jpg
- moon.jpg: NASA Scientific Visualization Studio / Ernie Wright, CGI Moon Kit,
  LRO LROC WAC y albedo polar LOLA, edición 2025, 2048×1024.
  https://svs.gsfc.nasa.gov/4720/
  Descarga: Invoke-WebRequest -UseBasicParsing 'https://svs.gsfc.nasa.gov/vis/a000000/a004700/a004720/lroc_color_2k.jpg' -OutFile moon.jpg
  NASA advierte que esta adaptación está optimizada para visualización, no ciencia;
  los polos se completan con albedo LOLA, no con fotografías WAC completas.
- mars.jpg: NASA Viking Orbiter, Viking Merged Color Mosaic / MDIM 1.0,
  distribuido por ASU. https://www.mars.asu.edu/data/mdim_color/
  Mapa cilíndrico, norte arriba, longitud este positiva, -180..180.
  Se ensamblan sin alterar colores las ocho teselas de previsualización de
  https://www.mars.asu.edu/data/mdim_color/small/mars45{n,s}{225,315,045,135}.png
  en ese orden de columnas, norte en la fila superior. Resolución de presentación;
  no atribuirle los 920 m/píxel del producto original de alta resolución.

Todos los mapas cubren -180..180 de izquierda a derecha y 90..-90 de arriba abajo.
La esfera ajusta sus UV a toVector: u = (lon + 180) / 360, v = (lat + 90) / 180.
No se usa el PNG polar de suitability como textura. La Luna desplaza su geometría con LOLA y Marte con MOLA.

## Relieve vigente de los tres cuerpos

La implementación actual usa NASA SRTMGL30 (Tierra; reemplaza a NOAA ETOPO 2022), NASA LOLA
ldem_4_uint.tif (Luna) y NASA MOLA megt90n000cb.img + XML (Marte).
Procedencia, unidades, referencias, comandos y formato: ../RELIEF.md.
Hashes y resultados de conversión: heights.manifest.json.
El navegador carga únicamente earth.height.gz, moon.height.gz y mars.height.gz.
Los originales float32 LOLA y IMG MOLA de las pruebas anteriores ya no se cargan
como recursos de renderizado. La exageración se indica en la escena y se ajusta 1..30×.
Pendiente coordinado: trasladar estos registros a docs/datos.md, sin editarlo aquí.
