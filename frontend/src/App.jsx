import { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Search from './Search';
import UploadSettings from './UploadSettings';
import Files from './Files';
import Login from './Login';

function App() {
  const [loggedIn, setLoggedIn] = useState(false);
  const [mode, setMode] = useState('default');

  if (!loggedIn) {
    return <Login setLoggedIn={setLoggedIn} />;
  }

  return (
    <BrowserRouter>
      <Layout onLogout={() => setLoggedIn(false)}>
        <Routes>
          <Route path="/" element={<Navigate to="/search" replace />} />
          <Route path="/search" element={<Search mode={mode} />} />
          <Route path="/settings" element={<UploadSettings mode={mode} setMode={setMode} />} />
          <Route path="/stats" element={<Files />} />
          <Route path="*" element={<Navigate to="/search" replace />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;