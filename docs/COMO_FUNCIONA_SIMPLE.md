# SITD — Cómo funciona, explicado simple

Guía para explicar el sistema a alguien no técnico, o para preparar la defensa.

---

## La idea en una frase

**Un funcionario dibuja un área cualquiera en un mapa y el sistema le dice, al
instante, cuánta gente vive ahí, en qué condiciones y qué tipo de suelo hay** —
sin importar que esa área cruce los límites de varias comunas.

---

## El problema que resuelve

Chile está dividido en comunas y toda la información oficial viene organizada
según esos límites. Pero los problemas reales no respetan esas fronteras: un
incendio no se detiene en el borde comunal, un barrio periférico queda partido
entre dos comunas, una cuenca atraviesa cinco municipios.

Cuando un Gobernador necesita saber "¿cuánta gente vive en esta zona de
riesgo?", hoy debe pedir a un equipo técnico que cruce planillas y mapas a
mano. Eso toma días. Mientras tanto, la decisión se toma sin datos.

---

## Cómo funciona, paso a paso

### Etapa 1 — Preparar los ingredientes (ETL)

Llegan dos archivos oficiales:

- **Del INE:** un mapa donde cada manzana urbana y cada sector rural es un
  polígono con datos de población, viviendas, edades, empleo y servicios.
  Son 18.653 unidades.
- **De CONAF:** otro mapa con lo que hay en cada terreno: bosque nativo,
  plantación, cultivo, ciudad, río. Son 119.017 polígonos.

El sistema los limpia, los pone en el mismo sistema de coordenadas y los carga
en una base de datos especializada en mapas.

**El paso clave:** cruza ambos mapas *una sola vez* y guarda el resultado. Por
ejemplo, anota que la unidad 7103011001 tiene 4,9 hectáreas de bosque nativo,
3,1 de matorral y 2,0 de cultivo. Ese cálculo es pesado, así que se hace una vez
y queda listo.

> **Analogía:** es como picar todas las verduras el domingo. Durante la semana
> ya está todo listo y solo tomas lo que necesitas.

*(ETL significa Extract, Transform, Load: extraer, transformar y cargar.)*

### Etapa 2 — El motor (agregación elástica)

Cuando el usuario dibuja un polígono, el motor:

1. Busca qué unidades censales caen dentro.
2. Suma sus datos: población, hogares, viviendas.
3. Calcula indicadores: no solo "hay 340 niños", sino "el índice de dependencia
   es 52%", "el 18% de las viviendas está hacinada", "el 63% usa leña".

Todo en **milisegundos**, porque el trabajo pesado ya se hizo en la Etapa 1.

### Etapa 3 — La pantalla (dashboard)

El funcionario entra con su correo institucional, dibuja el área que le interesa
y al costado aparecen los indicadores. Además:

- Ve **resaltadas en verde las unidades que realmente se incluyeron**, no solo
  su trazo — así entiende exactamente qué se está sumando.
- Puede desplegar una **tabla con los identificadores** de cada unidad y hacer
  clic para ubicarla en el mapa.
- Puede **descargar un informe PDF** con el mapa, los indicadores y el listado
  completo de unidades.

Según su perfil ve distinto: un gobernador accede a toda la región; un técnico
de SECPLAN, solo a su comuna.

---

## Las dos decisiones que hay que saber explicar

### 1. Por qué las unidades no se cortan

Si dibujas un área y una manzana queda a medias, ¿qué haces con su gente?

La respuesta ingenua sería: "si la mitad está dentro, cuento la mitad".
**Eso está mal.** Las personas no están repartidas uniformemente dentro de una
manzana; pueden estar todas en un edificio de una esquina. Cortar así
inventaría habitantes.

**La solución:** cada unidad se incluye **entera o nada**, según dónde caiga su
punto central. Si ese punto está dentro del dibujo, entra completa.

**Por qué importa:** garantiza que la suma coincida exactamente con las cifras
oficiales del INE. Verificado: Curepto 9.464, Talca 230.638, Linares 95.855 —
idénticas a las oficiales.

### 2. Por qué el suelo SÍ se corta

Con el uso de suelo pasa lo contrario. Si una unidad tiene bosque en una mitad
y cultivo en la otra, eso es un hecho físico medible. Ahí sí tiene sentido
decir "3 hectáreas de bosque, 2 de cultivo".

| | ¿Se puede partir? | ¿Por qué? |
|---|---|---|
| Personas | No | Están concentradas, no repartidas parejo |
| Superficie | Sí | El terreno es continuo y medible |

Dos lógicas opuestas en el mismo sistema, cada una correcta para su tipo de
dato. Es probablemente la decisión de diseño más interesante del proyecto.

---

## Qué lo diferencia de un programa de mapas normal

Un visor SIG (como QGIS) muestra capas y permite consultar cosas que **ya
existen**: clic en una comuna, ves sus datos.

El SITD **calcula sobre áreas que no existen en ningún dato**. Dibujas una
forma inventada y obtiene sus cifras al instante.

Pero conviene ser honesto en la defensa: **un experto en QGIS podría hacer este
mismo cruce manualmente.** La diferencia no está en la operación geométrica,
sino en tres cosas juntas:

1. **Automatización:** lo que tomaba días de trabajo técnico, ahora son segundos.
2. **Accesibilidad:** lo puede hacer un alcalde, no solo un especialista en SIG.
3. **Exactitud garantizada:** el diseño asegura que nunca se pierda ni duplique
   población, cosa que un cruce manual mal hecho sí haría.

El aporte es de **ingeniería de sistemas aplicada a la gestión pública**, no la
invención de un algoritmo geoespacial nuevo. Y eso es exactamente lo que
corresponde a un proyecto de título de Ingeniería en Computación.

---

## Sobre el informe PDF

El sistema genera un informe descargable con el mapa del área, los totales, los
once indicadores, la composición de uso de suelo y un anexo con el listado
completo de identificadores de las unidades incluidas.

**Un detalle que vale contar:** el mapa del informe se dibuja con los **datos
propios del sistema** (los límites comunales derivados de la capa censal), no
con cartografía descargada de internet. Esto surgió de un problema real: al
intentar usar las teselas de OpenStreetMap, sus servidores bloquearon las
peticiones, porque su política de uso no permite la descarga automatizada.

La solución resultó mejor que el plan original: el informe ya no depende de
servicios externos, se genera de forma inmediata (menos de 2 segundos) y no
tiene restricciones de licencia. Un buen ejemplo de cómo una limitación
encontrada durante el desarrollo puede llevar a un diseño más sólido.

---

## Sobre la base de datos en la nube

La base se migró a Supabase (PostgreSQL con PostGIS, servidor en São Paulo).

**Lo interesante: no se sube todo.**

| Qué | Peso | ¿Se sube? |
|---|---|---|
| Datos del censo | ~40 MB | Sí |
| Resultado del cruce con CONAF | ~3 MB | Sí |
| **Mapas originales de CONAF** | **607 MB** | **No** |

Los mapas de CONAF pesan más de lo que permite cualquier plan gratuito (límite
500 MB). Pero **no hacen falta**: el cruce ya se calculó en la Etapa 1, y el
sistema en operación solo consulta el resultado.

**La base en la nube pesa ~60 MB en vez de 650.**

> Para la defensa: la decisión de precalcular el cruce se tomó por
> **rendimiento** (para cumplir el criterio de tiempo del OE2), pero además
> redujo el tamaño de la base en un 90%, lo que hizo posible desplegarla sin
> costo. Un mismo diseño resolvió dos problemas, uno sin haberlo previsto.

El traspaso no consistió en copiar la base: se volvieron a ejecutar los mismos
programas de carga apuntando a Supabase. Eso demuestra que **el proceso completo
es reproducible** desde los archivos originales.

---

## Preguntas que te pueden hacer

**"¿Esto no lo hace ya QGIS?"**
La operación geométrica sí. Lo que QGIS no hace es automatizarla, ponerla al
alcance de un no especialista y garantizar la exactitud demográfica. El aporte
es de sistema, no de algoritmo.

**"¿Por qué no cortan las unidades por el borde?"**
Porque la población no se distribuye uniformemente dentro de una unidad.
Prorratear por área inventaría habitantes. Incluir la unidad completa garantiza
coincidencia exacta con las cifras del INE.

**"¿Y si el polígono corta una entidad rural gigante?"**
Es una limitación real y declarada. La entidad rural mayor mide 1.783 km²; si el
dibujo cubre solo parte de ella, igual se suma toda su población. Se acepta
porque prorratear sería peor: la población rural se concentra en caseríos. Está
documentado como limitación metodológica.

**"¿Cumple con la ley de datos personales?"**
Sí. Solo se procesan datos agregados por unidad censal, nunca individuales.
Además el sistema **respeta el secreto estadístico del INE**: cuando el INE
ocultó un dato por baja frecuencia, el sistema lo mantiene oculto en vez de
rellenarlo con cero.

**"¿Qué tan rápido es?"**
El criterio exigía menos de 10 minutos. Las mediciones dan entre 6 y 27
milisegundos: unas 20.000 veces más rápido que el requisito.

**"¿Cómo sé que las cifras son correctas?"**
Hay pruebas automatizadas que comparan la suma del motor contra los totales
oficiales del INE en varias comunas. Todas coinciden exactamente. Además el
informe PDF incluye el listado completo de identificadores usados, de modo que
cualquiera puede auditar la agregación.
