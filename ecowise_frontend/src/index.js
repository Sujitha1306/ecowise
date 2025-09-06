import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter as Router } from 'react-router-dom'; // Import Router here
import './index.css';
import App from './App';
import { AuthProvider } from './context/AuthContext'; // Import the provider

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    {/* Router now wraps everything, making navigation available everywhere */}
    <Router>
      {/* AuthProvider is inside Router, so it can use navigation hooks */}
      <AuthProvider>
        <App />
      </AuthProvider>
    </Router>
  </React.StrictMode>
);
