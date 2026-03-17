import { Outlet } from 'react-router-dom';
import { Providers } from './providers';

function App() {
  return (
    <Providers>
      <Outlet />
    </Providers>
  );
}

export default App;