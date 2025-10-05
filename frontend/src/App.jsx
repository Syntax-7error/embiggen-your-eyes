
import React from 'react'
import { Routes, Route } from 'react-router-dom';
import Home from './Home';
import PhotoDetail from './PhotoDetail';
import './App.css';

  function App() {
    return (
      <Routes>

      <Route path="/" element={<Home />} />
      <Route path="/photo/:id" element={<PhotoDetail />} />
      </Routes>
    );
  }

export default App;
