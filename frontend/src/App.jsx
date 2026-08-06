import { useState } from 'react'
import Login from './Login.jsx'
import Dashboard from './Dashboard.jsx'

export default function App() {
  // El token vive en memoria: al recargar hay que volver a autenticarse.
  const [sesion, setSesion] = useState(null)

  if (!sesion) {
    return <Login onEntrar={(token, rol) => setSesion({ token, rol })} />
  }
  return (
    <Dashboard
      token={sesion.token}
      rol={sesion.rol}
      onSalir={() => setSesion(null)}
    />
  )
}
