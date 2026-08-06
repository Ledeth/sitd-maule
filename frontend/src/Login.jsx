import { useState } from 'react'
import { login } from './api.js'

export default function Login({ onEntrar }) {
  const [correo, setCorreo] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [cargando, setCargando] = useState(false)

  async function entrar(e) {
    e.preventDefault()
    setError('')
    setCargando(true)
    try {
      const datos = await login(correo, password)
      onEntrar(datos.access_token, datos.rol)
    } catch (err) {
      setError(err.message)
    } finally {
      setCargando(false)
    }
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center bg-slate-50"
      style={{
        backgroundImage:
          'linear-gradient(#e2e8f0 1px, transparent 1px), linear-gradient(90deg, #e2e8f0 1px, transparent 1px)',
        backgroundSize: '40px 40px',
      }}
    >
      <form
        onSubmit={entrar}
        className="w-full max-w-sm bg-white border border-slate-200 rounded-lg shadow-sm p-8"
      >
        <div className="text-center mb-6">
          <div className="text-3xl mb-2" aria-hidden="true">⊕</div>
          <h1 className="text-xl font-bold tracking-widest text-slate-900">SITD</h1>
          <p className="text-[10px] uppercase tracking-wider text-slate-500 mt-1">
            Sistema de Inteligencia Territorial Dinámica
          </p>
        </div>

        <label className="block text-xs font-medium text-slate-700 mb-1">
          Correo institucional
        </label>
        <input
          type="email"
          required
          value={correo}
          onChange={(e) => setCorreo(e.target.value)}
          placeholder="nombre@gobierno.cl"
          className="w-full mb-4 px-3 py-2 border border-slate-300 rounded text-sm
                     focus:outline-none focus:ring-2 focus:ring-slate-900"
        />

        <label className="block text-xs font-medium text-slate-700 mb-1">
          Contraseña
        </label>
        <input
          type="password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full mb-5 px-3 py-2 border border-slate-300 rounded text-sm
                     focus:outline-none focus:ring-2 focus:ring-slate-900"
        />

        {error && (
          <p className="mb-4 text-xs text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={cargando}
          className="w-full bg-slate-900 hover:bg-slate-800 disabled:opacity-60
                     text-white text-xs font-semibold tracking-widest uppercase
                     py-3 rounded transition"
        >
          {cargando ? 'Verificando…' : 'Iniciar sesión'}
        </button>

        <p className="mt-6 text-center text-[10px] uppercase tracking-wider text-slate-400">
          Acceso restringido · Perfil funcionario
        </p>
      </form>
    </div>
  )
}
