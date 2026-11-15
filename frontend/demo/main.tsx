import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '../src/index.css'
import PagesDemo from '../src/PagesDemo'

createRoot(document.getElementById('root')!).render(<StrictMode><PagesDemo /></StrictMode>)
