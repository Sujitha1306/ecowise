import React, { useState, useEffect, useContext, useMemo } from 'react';
import { AuthContext } from '../context/AuthContext';
import './DashboardStyles.css';

function DashboardPage() {
  const { user } = useContext(AuthContext);

  const [myAppliances, setMyAppliances] = useState([]);
  const [allAppliances, setAllAppliances] = useState([]);
  const [selectedType, setSelectedType] = useState('');
  const [selectedBrand, setSelectedBrand] = useState('');
  const [selectedApplianceId, setSelectedApplianceId] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [suggestion, setSuggestion] = useState(null);
  const [isLoadingSuggestion, setIsLoadingSuggestion] = useState(false);

  useEffect(() => {
    if (user) {
      Promise.all([
        fetch(`http://localhost:5000/user/${user.id}`, { credentials: 'include' }),
        fetch('http://localhost:5000/appliances', { credentials: 'include' })
      ])
      .then(async ([myAppliancesRes, allAppliancesRes]) => {
        if (!myAppliancesRes.ok) {
            if(myAppliancesRes.status === 403) throw new Error("You are not authorized to view this user's data.");
            throw new Error('Could not fetch your appliance data.');
        }
        if (!allAppliancesRes.ok) throw new Error('Could not fetch the master appliance list.');
        
        const myAppliancesData = await myAppliancesRes.json();
        const allAppliancesData = await allAppliancesRes.json();
        
        setMyAppliances(myAppliancesData.appliances || []);
        setAllAppliances(allAppliancesData || []);
      })
      .catch(err => {
        setError(err.message);
      })
      .finally(() => setIsLoading(false));
    } else {
        setIsLoading(false);
    }
  }, [user]);

  const applianceTypes = useMemo(() => [...new Set(allAppliances.map(app => app.type))], [allAppliances]);
  const availableBrands = useMemo(() => {
    if (!selectedType) return [];
    return [...new Set(allAppliances.filter(app => app.type === selectedType).map(app => app.brand))];
  }, [allAppliances, selectedType]);
  const availableModels = useMemo(() => {
    if (!selectedBrand) return [];
    return allAppliances.filter(app => app.type === selectedType && app.brand === selectedBrand);
  }, [allAppliances, selectedType, selectedBrand]);

  const handleAddAppliance = (e) => {
    e.preventDefault();
    if (!selectedApplianceId) return;

    fetch(`http://localhost:5000/user/${user.id}/appliance`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ appliance_id: selectedApplianceId }),
    })
    .then(res => {
        if (!res.ok) throw new Error("Failed to add appliance.");
        return res.json();
    })
    .then(() => {
      const newAppliance = allAppliances.find(app => app.id === parseInt(selectedApplianceId));
      if (newAppliance && !myAppliances.some(app => app.id === newAppliance.id)) {
        setMyAppliances([...myAppliances, newAppliance]);
      }
    })
    .catch(err => setError(err.message));
  };

  const handleRemoveAppliance = (applianceId) => {
    fetch(`http://localhost:5000/user/${user.id}/appliance/${applianceId}`, {
      method: 'DELETE',
      credentials: 'include',
    })
    .then(response => {
      if (!response.ok) throw new Error('Failed to remove appliance');
      return response.json();
    })
    .then(() => {
      setMyAppliances(myAppliances.filter(app => app.id !== applianceId));
    })
    .catch(error => setError(error.message));
  };
  
  const getSuggestion = (applianceId) => {
    setIsLoadingSuggestion(true);
    setSuggestion(null);
    fetch(`http://localhost:5000/user/${user.id}/appliance/${applianceId}/suggestion`, {
        credentials: 'include'
    })
      .then(res => res.json())
      .then(data => {
          if (data.error) throw new Error(data.error);
          setSuggestion(data)
      })
      .catch(err => setError(err.message))
      .finally(() => setIsLoadingSuggestion(false));
  };

  if (isLoading) return <div className="dashboard-container"><p>Loading dashboard...</p></div>;
  if (!user) return <div className="dashboard-container"><p className="error-message">Please log in to continue.</p></div>;

  return (
    <div className="dashboard-container">
      <h2>Welcome, {user.username}!</h2>
      <p className="subtitle">Manage your appliances and get smart advice to save energy and water.</p>
      
      {error && <p className="error-message">{error}</p>}
      
      <div className="add-appliance-section">
          <h3>Add a New Appliance</h3>
          <form onSubmit={handleAddAppliance} className="add-appliance-form">
              <select value={selectedType} onChange={e => { setSelectedType(e.target.value); setSelectedBrand(''); setSelectedApplianceId(''); }}>
                  <option value="">1. Select Type</option>
                  {applianceTypes.map(type => <option key={type} value={type}>{type}</option>)}
              </select>
              <select value={selectedBrand} onChange={e => { setSelectedBrand(e.target.value); setSelectedApplianceId(''); }} disabled={!selectedType}>
                  <option value="">2. Select Brand</option>
                  {availableBrands.map(brand => <option key={brand} value={brand}>{brand}</option>)}
              </select>
              <select value={selectedApplianceId} onChange={e => setSelectedApplianceId(e.target.value)} disabled={!selectedBrand}>
                  <option value="">3. Select Model</option>
                  {availableModels.map(app => <option key={app.id} value={app.id}>{app.model}</option>)}
              </select>
              <button type="submit" disabled={!selectedApplianceId}>Add</button>
          </form>
      </div>

      <div className="appliances-list">
        <h3>My Appliances</h3>
        {myAppliances.length > 0 ? (
          myAppliances.map(appliance => (
            <div key={appliance.id} className="appliance-item">
              <span>{appliance.brand} {appliance.model}</span>
              <div className="button-group">
                <button className="advice-button" onClick={() => getSuggestion(appliance.id)}>Get Advice</button>
                <button className="remove-button" onClick={() => handleRemoveAppliance(appliance.id)}>Remove</button>
              </div>
            </div>
          ))
        ) : (
          <p>You haven't added any appliances yet. Use the form above to add one.</p>
        )}
      </div>

      {isLoadingSuggestion && <p>Getting your smart suggestion...</p>}

      {suggestion && (
        <div className="suggestion-card-dashboard">
          <h3>Smart Suggestion For:</h3>
          <p><strong>{suggestion.appliance}</strong></p>
          <p className="suggestion-text">{suggestion.suggestion}</p>
        </div>
      )}
    </div>
  );
}

export default DashboardPage;

