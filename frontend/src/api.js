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
