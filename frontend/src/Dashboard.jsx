import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet-draw'
import proj4 from 'proj4'
import { agregar } from './api.js'

// El mapa trabaja en WGS84 (lat/lon) pero el motor espera EPSG:32719 (UTM 19S).
// La conversión se hace aquí, al construir el WKT que se envía a la API.
const UTM19S =
  '+proj=utm +zone=19 +south +datum=WGS84 +units=m +no_defs'

function poligonoAWkt(latlngs) {
  const puntos = latlngs.map(({ lat, lng }) => {
    const [x, y] = proj4('EPSG:4326', UTM19S, [lng, lat])
    return `${x.toFixed(2)} ${y.toFixed(2)}`
  })
  puntos.push(puntos[0]) // WKT exige cerrar el anillo
  return `POLYGON((${puntos.join(', ')}))`
}

const COLOR_DIMENSION = {
  demografia: 'bg-sky-100 text-sky-800',
  vulnerabilidad: 'bg-amber-100 text-amber-800',
  habitacional: 'bg-violet-100 text-violet-800',
  servicios: 'bg-teal-100 text-teal-800',
  ambiental: 'bg-emerald-100 text-emerald-800',
}

export default function Dashboard({ token, rol, onSalir }) {
  const contenedor = useRef(null)
  const mapaRef = useRef(null)
  const [informe, setInforme] = useState(null)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (mapaRef.current) return

    const mapa = L.map(contenedor.current).setView([-35.43, -71.65], 9)
    L.tileLayer(
      'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
      { attribution: '© OpenStreetMap', maxZoom: 18 }
    ).addTo(mapa)

    const dibujados = new L.FeatureGroup().addTo(mapa)
    const control = new L.Control.Draw({
      edit: { featureGroup: dibujados, remove: true },
      draw: {
        polygon: { shapeOptions: { color: '#14b8a6', weight: 2, fillOpacity: 0.25 } },
        rectangle: { shapeOptions: { color: '#14b8a6', weight: 2, fillOpacity: 0.25 } },
        polyline: false, circle: false, marker: false, circlemarker: false,
      },
    })
    mapa.addControl(control)

    mapa.on(L.Draw.Event.CREATED, async (e) => {
      dibujados.clearLayers()
      dibujados.addLayer(e.layer)
      const anillo = e.layer.getLatLngs()[0]
      await consultar(poligonoAWkt(anillo))
    })

    mapaRef.current = mapa

    // Leaflet mide el contenedor al inicializarse, pero en ese instante el
    // layout flex aún no ha terminado de aplicarse y el mapa queda dibujado
    // en un área más pequeña que la real. invalidateSize() lo recalcula una
    // vez que el navegador ya pintó el layout definitivo.
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

  async function consultar(wkt) {
    setCargando(true)
    setError('')
    try {
      const datos = await agregar(token, wkt)
      setInforme(datos)
    } catch (err) {
      setError(err.message)
      setInforme(null)
    } finally {
      setCargando(false)
    }
  }

  return (
    <div className="h-screen flex flex-col bg-slate-100">
      {/* Barra superior */}
      <header className="bg-white border-b border-slate-200 px-5 py-3 flex items-center justify-between">
        <div className="flex items-baseline gap-3">
          <span className="font-bold tracking-widest text-slate-900">SITD</span>
          <span className="text-xs text-slate-500">Visor territorial · Región del Maule</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-xs text-slate-600">
            Perfil: <strong className="text-slate-900">{rol}</strong>
          </span>
          <button
            onClick={onSalir}
            className="text-xs text-slate-500 hover:text-slate-900 underline"
          >
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
          <div className="absolute bottom-4 left-4 z-[1000] bg-white/95 border border-slate-200
                          rounded px-3 py-2 text-xs text-slate-700 shadow max-w-xs">
            Dibuja un polígono o rectángulo con las herramientas de la izquierda
            para analizar ese subterritorio.
          </div>
        </div>

        {/* Panel de análisis */}
        <aside className="w-96 bg-white border-l border-slate-200 overflow-y-auto">
          <div className="px-5 py-4 border-b border-slate-200">
            <h2 className="font-semibold text-slate-900">Análisis de subterritorio</h2>
            <p className="text-xs text-slate-500">Censo 2024 (INE) · Catastro CONAF</p>
          </div>

          {cargando && (
            <p className="px-5 py-6 text-sm text-slate-500">Calculando…</p>
          )}

          {error && (
            <p className="mx-5 my-4 text-xs text-red-700 bg-red-50 border border-red-200
                          rounded px-3 py-2">{error}</p>
          )}

          {!cargando && !informe && !error && (
            <p className="px-5 py-6 text-sm text-slate-500">
              Aún no hay un área seleccionada. Dibuja una en el mapa para ver
              su población, indicadores y uso de suelo.
            </p>
          )}

          {informe && !cargando && (
            <div className="px-5 py-4 space-y-5">
              {/* Totales */}
              <div className="grid grid-cols-2 gap-3">
                <Metrica etiqueta="Población" valor={informe.poblacion_total?.toLocaleString('es-CL')} />
                <Metrica etiqueta="Hogares" valor={informe.hogares_total?.toLocaleString('es-CL')} />
                <Metrica etiqueta="Viviendas" valor={informe.viviendas_total?.toLocaleString('es-CL')} />
                <Metrica etiqueta="Unidades censales" valor={informe.n_unidades?.toLocaleString('es-CL')} />
              </div>

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
