import React, { createContext, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

export const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    // --- THIS IS THE FIX: Using 'localhost' instead of '127.0.0.1' ---
    fetch('http://localhost:5000/@me', {
      credentials: 'include',
    })
    .then(res => res.ok ? res.json() : null)
    .then(userData => setUser(userData))
    .catch(() => setUser(null))
    .finally(() => setLoading(false));
  }, []);

  const login = (userData) => {
    setUser({id: userData.user_id, username: userData.username});
    navigate('/');
  };

  const logout = () => {
    // --- THIS IS THE FIX: Using 'localhost' ---
    fetch('http://localhost:5000/logout', {
      method: 'POST',
      credentials: 'include',
    })
    .then(() => {
      setUser(null);
      navigate('/login');
    })
    .catch(error => console.error("Logout failed:", error));
  };

  const value = { user, loading, login, logout };

  if (loading) {
    return null;
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

