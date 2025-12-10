import { useState } from 'react';
import api from './api';

function Login({ setLoggedIn }) {
  const handleLogin = async () => {
    try {
      await api.post('/login', {}, {
        auth: { username: 'demo', password: 'demo' }
      });
      setLoggedIn(true);
    } catch (e) {
      alert('Erreur login – mais normalement ça passe');
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-black">
      <button 
        onClick={handleLogin}
        className="px-10 py-5 bg-green-600 text-white text-2xl rounded hover:bg-green-700"
      >
        CONNEXION DEMO (clic ici)
      </button>
    </div>
  );
}

export default Login;