import React, { useState, createContext, useContext } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

import { AuthProvider } from './context/AuthContext';
import { CartProvider } from './context/CartContext';

import Navbar from './components/Navbar';
import Chatbot from './components/Chatbot';
import Home from './pages/Home';
import Products from './pages/Products';
import ProductDetail from './pages/ProductDetail';
import Cart from './pages/Cart';
import Checkout from './pages/Checkout';
import Orders from './pages/Orders';
import Complaints from './pages/Complaints';
import Login from './pages/Login';
import Register from './pages/Register';
import ProtectedRoute from './components/ProtectedRoute';

// Create context for sidebar state
const SidebarContext = createContext();

export const useSidebar = () => {
  const context = useContext(SidebarContext);
  if (!context) {
    throw new Error('useSidebar must be used within a SidebarProvider');
  }
  return context;
};

function App() {
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState('name');
  const [filterBy, setFilterBy] = useState('all');
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [recommendedProducts, setRecommendedProducts] = useState([]);

  const handleSearch = (term) => {
    setSearchTerm(term);
  };

  const handleSort = (sort) => {
    setSortBy(sort);
  };

  const handleFilter = (filter) => {
    setFilterBy(filter);
  };

  const handleRecommendations = (products) => {
    setRecommendedProducts(products || []);
  };

  return (
    <AuthProvider>
      <CartProvider>
        <SidebarContext.Provider value={{ isSidebarOpen, setIsSidebarOpen }}>
          <Router>
            <div className="App">
              <Navbar 
                onSearch={handleSearch}
                onSort={handleSort}
                onFilter={handleFilter}
                searchTerm={searchTerm}
                sortBy={sortBy}
                filterBy={filterBy}
              />
              <main className={`main-content ${isSidebarOpen ? 'sidebar-open' : 'sidebar-closed'}`}>
                <Routes>
                  <Route 
                    path="/" 
                    element={
                      <Home 
                        searchTerm={searchTerm}
                        sortBy={sortBy}
                        filterBy={filterBy}
                        recommendedProducts={recommendedProducts}
                      />
                    } 
                  />
                  <Route path="/products" element={<Products />} />
                  <Route path="/products/:id" element={<ProductDetail />} />
                  <Route path="/login" element={<Login />} />
                  <Route path="/register" element={<Register />} />
                  <Route 
                    path="/cart" 
                    element={
                      <ProtectedRoute>
                        <Cart />
                      </ProtectedRoute>
                    } 
                  />
                  <Route 
                    path="/checkout" 
                    element={
                      <ProtectedRoute>
                        <Checkout />
                      </ProtectedRoute>
                    } 
                  />
                  <Route 
                    path="/orders" 
                    element={
                      <ProtectedRoute>
                        <Orders />
                      </ProtectedRoute>
                    } 
                  />
                  <Route 
                    path="/complaints" 
                    element={
                      <ProtectedRoute>
                        <Complaints />
                      </ProtectedRoute>
                    } 
                  />
                </Routes>
              </main>
              <ToastContainer
                position="top-right"
                autoClose={3000}
                hideProgressBar={false}
                newestOnTop={false}
                closeOnClick
                rtl={false}
                pauseOnFocusLoss
                draggable
                pauseOnHover
              />
              <Chatbot onRecommendations={handleRecommendations} />
            </div>
          </Router>
        </SidebarContext.Provider>
      </CartProvider>
    </AuthProvider>
  );
}

export default App;
