// Cliente de la API del SITD. El token vive en memoria (no localStorage:
// para un perfil funcionario es preferible que la sesión no persista).
const BASE = '/api'

export async function login(correo, password) {
  const r = await fetch(`${BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ correo, password }),
  })
  if (!r.ok) {
    const e = await r.json().catch(() => ({}))
    throw new Error(e.detail || 'No se pudo iniciar sesión')
  }
  return r.json()
}

export async function agregar(token, poligonoWkt) {
  const r = await fetch(`${BASE}/agregacion`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ poligono_wkt: poligonoWkt }),
  })
  if (!r.ok) {
    const e = await r.json().catch(() => ({}))
    throw new Error(e.detail || 'La consulta no se pudo completar')
  }
  return r.json()
}

export async function comunas(token) {
  const r = await fetch(`${BASE}/comunas`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!r.ok) throw new Error('No se pudieron cargar las comunas')
  return r.json()
}

// Descarga el informe PDF del área. La respuesta es binaria, así que se
// maneja como blob y se dispara la descarga desde el navegador.
export async function descargarInforme(token, poligonoWkt) {
  const r = await fetch(`${BASE}/informe`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ poligono_wkt: poligonoWkt }),
  })
  if (!r.ok) {
    // El error viene en JSON aunque el endpoint devuelva PDF en el caso feliz.
    const e = await r.json().catch(() => ({}))
    throw new Error(e.detail || 'No se pudo generar el informe')
  }

  const blob = await r.blob()
  const nombre =
    r.headers.get('Content-Disposition')?.match(/filename="(.+?)"/)?.[1] ||
    'informe_sitd.pdf'

  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = nombre
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
