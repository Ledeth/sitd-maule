import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet-draw'
import proj4 from 'proj4'
import { agregar, descargarInforme } from './api.js'

// El mapa trabaja en WGS84 (lat/lon) pero el motor espera EPSG:32719 (UTM 19S).
// La conversión se hace aquí, al construir el WKT que se envía a la API.
const UTM19S = '+proj=utm +zone=19 +south +datum=WGS84 +units=m +no_defs'

function poligonoAWkt(latlngs) {
  const puntos = latlngs.map(({ lat, lng }) => {
    const [x, y] = proj4('EPSG:4326', UTM19S, [lng, lat])
    return `${x.toFixed(2)} ${y.toFixed(2)}`
  })
  puntos.push(puntos[0]) // WKT exige cerrar el anillo
  return `POLYGON((${puntos.join(', ')}))`
}

// Estilos de las capas del mapa.
// Leaflet.draw viene en inglés. Se traduce su diccionario antes de instanciar
// el control; debe hacerse una sola vez, a nivel de módulo.
L.drawLocal.draw.toolbar.actions.title = 'Cancelar dibujo'
L.drawLocal.draw.toolbar.actions.text = 'Cancelar'
L.drawLocal.draw.toolbar.finish.title = 'Terminar el trazado'
L.drawLocal.draw.toolbar.finish.text = 'Terminar'
L.drawLocal.draw.toolbar.undo.title = 'Eliminar el último punto'
L.drawLocal.draw.toolbar.undo.text = 'Deshacer punto'
L.drawLocal.draw.toolbar.buttons.polygon = 'Dibujar un área'
L.drawLocal.draw.handlers.polygon.tooltip.start = 'Haz clic para empezar a dibujar el área'
L.drawLocal.draw.handlers.polygon.tooltip.cont = 'Haz clic para seguir dibujando'
L.drawLocal.draw.handlers.polygon.tooltip.end = 'Haz clic en el primer punto para cerrar el área'
L.drawLocal.edit.toolbar.actions.save.title = 'Guardar los cambios'
L.drawLocal.edit.toolbar.actions.save.text = 'Guardar'
L.drawLocal.edit.toolbar.actions.cancel.title = 'Descartar los cambios'
L.drawLocal.edit.toolbar.actions.cancel.text = 'Cancelar'
L.drawLocal.edit.toolbar.actions.clearAll.title = 'Borrar el área'
L.drawLocal.edit.toolbar.actions.clearAll.text = 'Borrar todo'
L.drawLocal.edit.toolbar.buttons.edit = 'Modificar el área'
L.drawLocal.edit.toolbar.buttons.editDisabled = 'No hay áreas que modificar'
L.drawLocal.edit.toolbar.buttons.remove = 'Borrar el área'
L.drawLocal.edit.toolbar.buttons.removeDisabled = 'No hay áreas que borrar'
L.drawLocal.edit.handlers.edit.tooltip.text = 'Arrastra los vértices para ajustar el área'
L.drawLocal.edit.handlers.edit.tooltip.subtext = 'Pulsa Cancelar para descartar los cambios'
L.drawLocal.edit.handlers.remove.tooltip.text = 'Haz clic en el área para borrarla'

// Límites de la Región del Maule, calculados sobre la propia capa censal
// (18.653 unidades) y ampliados ~15 km para dejar aire en los bordes. Acotar
// la vista evita que el usuario navegue fuera del territorio con datos, donde
// el sistema no tendría nada que responder.
const LIMITES_MAULE = L.latLngBounds(
  L.latLng(-36.694, -72.936),   // suroeste
  L.latLng(-34.535, -70.162),   // noreste
)
const ZOOM_MINIMO = 8            // por debajo se saldría de la región

const ESTILO_DIBUJO = {          // el polígono que trazó el usuario
  color: '#0ea5e9', weight: 2, dashArray: '6 4', fill: false,
}
const ESTILO_UNIDAD = {          // unidades censales efectivamente incluidas
  color: '#0f766e', weight: 1, fillColor: '#14b8a6', fillOpacity: 0.35,
}
const ESTILO_UNIDAD_ACTIVA = {   // unidad sobre la que está el cursor / clic
  color: '#7c2d12', weight: 2, fillColor: '#f59e0b', fillOpacity: 0.6,
}

export default function Dashboard({ token, rol, onSalir }) {
  const contenedor = useRef(null)
  const mapaRef = useRef(null)
  const capaDibujoRef = useRef(null)
  const capaUnidadesRef = useRef(null)

  const [informe, setInforme] = useState(null)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')
  const [verTabla, setVerTabla] = useState(false)
  const [unidadActiva, setUnidadActiva] = useState(null)
  const [wktActual, setWktActual] = useState(null)
  const [generando, setGenerando] = useState(false)

  useEffect(() => {
    if (mapaRef.current) return

    const mapa = L.map(contenedor.current, {
      maxBounds: LIMITES_MAULE,      // no se puede arrastrar fuera de la región
      maxBoundsViscosity: 0.9,       // el borde "resiste" al arrastrar
      minZoom: ZOOM_MINIMO,
      maxZoom: 18,
    })
    mapa.fitBounds(LIMITES_MAULE)    // abre encuadrado en la región completa

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap', maxZoom: 18,
      bounds: LIMITES_MAULE,         // no pide teselas fuera del área de interés
    }).addTo(mapa)

    // Dos capas separadas: el trazo del usuario y las unidades resultantes.
    const dibujados = new L.FeatureGroup().addTo(mapa)
    const unidades = new L.FeatureGroup().addTo(mapa)
    capaDibujoRef.current = dibujados
    capaUnidadesRef.current = unidades

    const control = new L.Control.Draw({
      edit: { featureGroup: dibujados, remove: true },
      draw: {
        polygon: {
          shapeOptions: ESTILO_DIBUJO,
          allowIntersection: false,
          showArea: false,
        },
        // Solo polígono libre: el rectángulo se retiró por no aportar sobre el
        // trazado libre, que es el gesto natural para delimitar un territorio.
        rectangle: false, polyline: false, circle: false,
        marker: false, circlemarker: false,
      },
    })
    mapa.addControl(control)

    mapa.on(L.Draw.Event.CREATED, async (e) => {
      dibujados.clearLayers()
      unidades.clearLayers()
      dibujados.addLayer(e.layer)
      await consultar(poligonoAWkt(e.layer.getLatLngs()[0]))
    })

    // Al ajustar los vértices de un área ya trazada, se recalcula el informe:
    // sin esto la edición no tendría efecto y el panel quedaría desactualizado.
    mapa.on(L.Draw.Event.EDITED, async (e) => {
      let capa = null
      e.layers.eachLayer((l) => { capa = l })
      if (!capa) return
      unidades.clearLayers()
      await consultar(poligonoAWkt(capa.getLatLngs()[0]))
    })

    mapa.on(L.Draw.Event.DELETED, () => {
      unidades.clearLayers()
      setInforme(null)
      setWktActual(null)
    })

    mapaRef.current = mapa

    // Leaflet mide el contenedor al inicializarse, cuando el layout flex aún
    // no terminó de aplicarse, y queda dibujado en un área menor a la real.
    // invalidateSize() lo recalcula ya con el layout definitivo.
    const recalcular = () => mapa.invalidateSize()
    requestAnimationFrame(recalcular)
    setTimeout(recalcular, 200)
    const observador = new ResizeObserver(recalcular)
    observador.observe(contenedor.current)
    window.addEventListener('resize', recalcular)

    return () => {
      observador.disconnect()
      window.removeEventListener('resize', recalcular)
    }
  }, [])

  // Pinta en el mapa las unidades que el motor incluyó en la agregación.
  function dibujarUnidades(geojson) {
    const capa = capaUnidadesRef.current
    if (!capa) return
    capa.clearLayers()
    if (!geojson) return

    const gj = L.geoJSON(geojson, {
      style: ESTILO_UNIDAD,
      onEachFeature: (feature, layer) => {
        const p = feature.properties
        layer.bindTooltip(
          `<strong>${p.id_unidad}</strong><br/>${p.comuna} · ${p.tipo}<br/>` +
          `${p.poblacion.toLocaleString('es-CL')} hab · ${p.hogares.toLocaleString('es-CL')} hogares`,
          { sticky: true }
        )
        layer.on('mouseover', () => layer.setStyle(ESTILO_UNIDAD_ACTIVA))
        layer.on('mouseout', () => layer.setStyle(ESTILO_UNIDAD))
        layer.on('click', () => setUnidadActiva(p.id_unidad))
      },
    })
    gj.addTo(capa)
  }

  // Centra el mapa en una unidad al hacer clic en la tabla.
  function enfocarUnidad(id) {
    setUnidadActiva(id)
    const capa = capaUnidadesRef.current
    if (!capa) return
    capa.eachLayer((grupo) => {
      grupo.eachLayer?.((l) => {
        if (l.feature?.properties?.id_unidad === id) {
          mapaRef.current.fitBounds(l.getBounds(), { maxZoom: 16 })
          l.setStyle(ESTILO_UNIDAD_ACTIVA)
          setTimeout(() => l.setStyle(ESTILO_UNIDAD), 2000)
        }
      })
    })
  }

  async function consultar(wkt) {
    setCargando(true)
    setError('')
    setUnidadActiva(null)
    setWktActual(wkt)
    try {
      const datos = await agregar(token, wkt)
      setInforme(datos)
      dibujarUnidades(datos.geojson)
    } catch (err) {
      setError(err.message)
      setInforme(null)
    } finally {
      setCargando(false)
    }
  }

  async function pedirInforme() {
    if (!wktActual) return
    setGenerando(true)
    setError('')
    try {
      await descargarInforme(token, wktActual)
    } catch (err) {
      setError(err.message)
    } finally {
      setGenerando(false)
    }
  }

  return (
    <div className="h-screen flex flex-col bg-slate-100">
      <header className="bg-white border-b border-slate-200 px-5 py-3 flex items-center justify-between">
        <div className="flex items-baseline gap-3">
          <span className="font-bold tracking-widest text-slate-900">SITD</span>
          <span className="text-xs text-slate-500">Visor territorial · Región del Maule</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-xs text-slate-600">
            Perfil: <strong className="text-slate-900">{rol}</strong>
          </span>
          <button onClick={onSalir} className="text-xs text-slate-500 hover:text-slate-900 underline">
            Cerrar sesión
          </button>
        </div>
      </header>

      <div className="flex-1 flex min-h-0">
        {/* Mapa */}
        <div className="flex-1 relative" style={{ minHeight: 0 }}>
          <div
            ref={contenedor}
            style={{ position: 'absolute', inset: 0, height: '100%', width: '100%' }}
          />
          <button
            onClick={() => mapaRef.current?.fitBounds(LIMITES_MAULE)}
            className="absolute top-4 right-4 z-[1000] bg-white/95 hover:bg-white
                       border border-slate-300 rounded px-3 py-1.5 text-xs
                       text-slate-700 shadow transition"
            title="Volver a la vista de toda la región"
          >
            Ver toda la región
          </button>

          <div className="absolute bottom-4 left-4 z-[1000] bg-white/95 border border-slate-200
                          rounded px-3 py-2 text-xs text-slate-700 shadow max-w-xs">
            {!informe && 'Dibuja un polígono o rectángulo con las herramientas de la izquierda.'}
            {informe && !informe.geometrias_omitidas &&
              `${informe.n_unidades.toLocaleString('es-CL')} unidades censales incluidas (en verde). Pasa el cursor para ver su detalle.`}
            {informe && informe.geometrias_omitidas && (
              <span className="text-amber-800">
                {informe.n_unidades.toLocaleString('es-CL')} unidades incluidas. El área
                supera el límite de resaltado en el mapa; los datos del panel sí las
                consideran todas.
              </span>
            )}
          </div>
        </div>

        {/* Panel de análisis */}
        <aside className="w-96 bg-white border-l border-slate-200 overflow-y-auto">
          <div className="px-5 py-4 border-b border-slate-200">
            <h2 className="font-semibold text-slate-900">Análisis de subterritorio</h2>
            <p className="text-xs text-slate-500">Censo 2024 (INE) · Catastro CONAF</p>
          </div>

          {cargando && <p className="px-5 py-6 text-sm text-slate-500">Calculando…</p>}

          {error && (
            <p className="mx-5 my-4 text-xs text-red-700 bg-red-50 border border-red-200
                          rounded px-3 py-2">{error}</p>
          )}

          {!cargando && !informe && !error && (
            <p className="px-5 py-6 text-sm text-slate-500">
              Aún no hay un área seleccionada. Dibuja una en el mapa para ver su
              población, indicadores y uso de suelo.
            </p>
          )}

          {informe && !cargando && (
            <div className="px-5 py-4 space-y-5">
              <div className="grid grid-cols-2 gap-3">
                <Metrica etiqueta="Población" valor={informe.poblacion_total?.toLocaleString('es-CL')} />
                <Metrica etiqueta="Hogares" valor={informe.hogares_total?.toLocaleString('es-CL')} />
                <Metrica etiqueta="Viviendas" valor={informe.viviendas_total?.toLocaleString('es-CL')} />
                <Metrica etiqueta="Unidades censales" valor={informe.n_unidades?.toLocaleString('es-CL')} />
              </div>

              {/* Tabla de atributos de las unidades incluidas */}
              <section>
                <button
                  onClick={() => setVerTabla(!verTabla)}
                  className="w-full flex items-center justify-between text-xs font-semibold
                             uppercase tracking-wider text-slate-500 hover:text-slate-900 mb-2"
                >
                  <span>Unidades incluidas ({informe.n_unidades})</span>
                  <span className="text-slate-400">{verTabla ? '▾' : '▸'}</span>
                </button>

                {verTabla && (
                  <div className="border border-slate-200 rounded overflow-hidden">
                    {informe.geometrias_omitidas && (
                      <p className="text-[10px] text-amber-800 bg-amber-50 px-2 py-1.5">
                        Área muy extensa: se listan los atributos, pero las geometrías
                        no se resaltan en el mapa por rendimiento.
                      </p>
                    )}
                    <div className="max-h-64 overflow-y-auto">
                      <table className="w-full text-[11px]">
                        <thead className="bg-slate-50 sticky top-0">
                          <tr className="text-slate-600">
                            <th className="text-left font-medium px-2 py-1.5">Unidad</th>
                            <th className="text-left font-medium px-2 py-1.5">Comuna</th>
                            <th className="text-right font-medium px-2 py-1.5">Hab.</th>
                            <th className="text-right font-medium px-2 py-1.5">Hog.</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(informe.unidades || []).map((u) => (
                            <tr
                              key={u.id_unidad}
                              onClick={() => enfocarUnidad(u.id_unidad)}
                              className={`border-t border-slate-100 cursor-pointer
                                          hover:bg-teal-50 ${
                                            unidadActiva === u.id_unidad ? 'bg-amber-50' : ''
                                          }`}
                              title="Clic para ubicarla en el mapa"
                            >
                              <td className="px-2 py-1 font-mono text-[10px] text-slate-700">
                                {u.id_unidad}
                                <span className={`ml-1 text-[9px] ${
                                  u.tipo === 'RURAL' ? 'text-emerald-700' : 'text-sky-700'
                                }`}>
                                  {u.tipo === 'RURAL' ? 'R' : 'U'}
                                </span>
                              </td>
                              <td className="px-2 py-1 text-slate-600 truncate max-w-[90px]">
                                {u.comuna}
                              </td>
                              <td className="px-2 py-1 text-right tabular-nums text-slate-900">
                                {u.poblacion?.toLocaleString('es-CL')}
                              </td>
                              <td className="px-2 py-1 text-right tabular-nums text-slate-600">
                                {u.hogares?.toLocaleString('es-CL')}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <p className="text-[10px] text-slate-400 px-2 py-1 border-t border-slate-100">
                      U = manzana urbana · R = entidad rural · clic para ubicar en el mapa
                    </p>
                  </div>
                )}
              </section>

              {/* Indicadores */}
              <section>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">
                  Indicadores
                </h3>
                <ul className="space-y-1.5">
                  {Object.entries(informe.indicadores || {}).map(([clave, ind]) => (
                    <li key={clave} className="flex items-start justify-between gap-3 text-sm">
                      <span className="text-slate-700 leading-snug">{ind.etiqueta}</span>
                      <span className="font-semibold text-slate-900 tabular-nums shrink-0">
                        {ind.valor ?? '—'}
                      </span>
                    </li>
                  ))}
                </ul>
              </section>

              {/* Uso de suelo */}
              <section>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">
                  Uso de suelo · {informe.superficie_total_ha?.toLocaleString('es-CL')} ha
                </h3>
                <ul className="space-y-2">
                  {(informe.uso_suelo || []).map((u) => (
                    <li key={u.subuso}>
                      <div className="flex justify-between text-xs mb-0.5">
                        <span className="text-slate-700">
                          {u.subuso}
                          {u.es_bosque_nativo && (
                            <span className="ml-1 text-[10px] text-emerald-700">· nativo</span>
                          )}
                        </span>
                        <span className="text-slate-500 tabular-nums">{u.porcentaje}%</span>
                      </div>
                      <div className="h-1.5 bg-slate-100 rounded">
                        <div
                          className={u.es_bosque_nativo ? 'h-1.5 rounded bg-emerald-600' : 'h-1.5 rounded bg-slate-400'}
                          style={{ width: `${u.porcentaje}%` }}
                        />
                      </div>
                    </li>
                  ))}
                </ul>
              </section>

              <button
                onClick={pedirInforme}
                disabled={generando}
                className="w-full bg-slate-900 hover:bg-slate-800 disabled:opacity-60
                           text-white text-xs font-semibold tracking-wide
                           py-3 rounded transition flex items-center justify-center gap-2"
              >
                {generando ? 'Generando informe…' : '⤓  Descargar informe técnico (PDF)'}
              </button>

              <p className="text-[10px] text-slate-400 border-t border-slate-100 pt-3">
                Consulta resuelta en {informe.duracion_ms} ms · perfil {informe.rol_solicitante}
              </p>
            </div>
          )}
        </aside>
      </div>
    </div>
  )
}

function Metrica({ etiqueta, valor }) {
  return (
    <div className="border border-slate-200 rounded p-3">
      <p className="text-[10px] uppercase tracking-wider text-slate-500">{etiqueta}</p>
      <p className="text-lg font-semibold text-slate-900 tabular-nums">{valor ?? '—'}</p>
    </div>
  )
}
