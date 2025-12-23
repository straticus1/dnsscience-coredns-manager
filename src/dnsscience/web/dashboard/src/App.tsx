import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Service from './pages/Service'
import Cache from './pages/Cache'
import Query from './pages/Query'
import Config from './pages/Config'
import Compare from './pages/Compare'
import Migrate from './pages/Migrate'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/service" element={<Service />} />
        <Route path="/cache" element={<Cache />} />
        <Route path="/query" element={<Query />} />
        <Route path="/config" element={<Config />} />
        <Route path="/compare" element={<Compare />} />
        <Route path="/migrate" element={<Migrate />} />
      </Routes>
    </Layout>
  )
}

export default App
