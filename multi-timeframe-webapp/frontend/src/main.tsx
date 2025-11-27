import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

// 注意：暂时移除了React.StrictMode
// 因为echarts-for-react在StrictMode下有ResizeObserver dispose错误
// 这是该库的已知问题，不影响生产环境
ReactDOM.createRoot(document.getElementById('root')!).render(
  <App />,
)
