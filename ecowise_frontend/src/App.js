import React, { useContext } from 'react';
// We no longer need to import Router here
import { Routes, Route, Link, Navigate } from 'react-router-dom'; 
import './App.css';

import { AuthContext } from './context/AuthContext';

import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';

// A component to protect routes that require a user to be logged in
function ProtectedRoute({ children }) {
  const { user, loading } = useContext(AuthContext);

  if (loading) {
    return <div className="loading-message">Loading session...</div>; // Show a loading message while checking auth
  }

  if (!user) {
    // If not logged in, redirect to the login page
    return <Navigate to="/login" />;
  }

  // If logged in, show the child component (the dashboard)
  return children;
}

function App() {
  const { user, logout, loading } = useContext(AuthContext);

  // The <Router> wrapper has been removed from this file
  return (
    <div className="App">
      <nav className="navbar">
        <h1>💡 EcoWise Advisor</h1>
        <ul>
          {user ? (
            <>
              <li><span className="welcome-user">Welcome, {user.username}</span></li>
              <li><button onClick={logout} className="logout-button">Logout</button></li>
            </>
          ) : (
            !loading && ( // Hide login/register while checking session
              <>
                <li><Link to="/login">Login</Link></li>
                <li><Link to="/register">Register</Link></li>
              </>
            )
          )}
        </ul>
      </nav>

      <main className="App-header">
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route 
            path="/" 
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            } 
          />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;

