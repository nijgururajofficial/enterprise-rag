import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { FiShoppingCart, FiUser, FiMenu, FiX, FiLogOut, FiSearch, FiFilter } from 'react-icons/fi';
import { useAuth } from '../context/AuthContext';
import { useCart } from '../context/CartContext';
import './Navbar.css';

const Navbar = ({ onSearch, onSort, onFilter, searchTerm, sortBy, filterBy }) => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const { user, logout, isAuthenticated } = useAuth();
  const { getCartItemCount } = useCart();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/');
    setIsUserMenuOpen(false);
  };

  const cartItemCount = getCartItemCount();
  const isHomePage = location.pathname === '/';

  return (
    <nav className="navbar">
      <div className="container">
        <div className="navbar-content">
          {/* Logo */}
          <Link to="/" className="navbar-logo">
            <span className="logo-text">ElectroStore</span>
          </Link>

          {/* Desktop Navigation */}
          <div className="navbar-links">
            <Link to="/" className="nav-link">Home</Link>
            <Link to="/products" className="nav-link">Products</Link>
          </div>

          {/* Search and Filter Section (only on home page) */}
          {isHomePage && onSearch && (
            <div className="navbar-search-section">
              <div className="search-container">
                <FiSearch className="search-icon" />
                <input
                  type="text"
                  placeholder="Search products..."
                  value={searchTerm || ''}
                  onChange={(e) => onSearch(e.target.value)}
                  className="search-input"
                />
              </div>
              <button
                className="filter-toggle"
                onClick={() => setShowFilters(!showFilters)}
              >
                <FiFilter size={16} />
                Filters
              </button>
            </div>
          )}

          {/* Right Side Icons */}
          <div className="navbar-actions">
            {/* Cart Icon */}
            {isAuthenticated && (
              <Link to="/cart" className="cart-icon">
                <FiShoppingCart size={20} />
                {cartItemCount > 0 && (
                  <span className="cart-badge">{cartItemCount}</span>
                )}
              </Link>
            )}

            {/* User Menu */}
            {isAuthenticated ? (
              <div className="user-menu">
                <button
                  className="user-menu-trigger"
                  onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                >
                  <FiUser size={20} />
                  <span className="user-name">{user?.name}</span>
                </button>
                {isUserMenuOpen && (
                  <div className="user-menu-dropdown">
                    <button onClick={handleLogout} className="user-menu-item">
                      <FiLogOut size={16} />
                      Logout
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className="auth-links">
                <Link to="/login" className="btn btn-outline">Login</Link>
                <Link to="/register" className="btn btn-primary">Register</Link>
              </div>
            )}

            {/* Mobile Menu Toggle */}
            <button
              className="mobile-menu-toggle"
              onClick={() => setIsMenuOpen(!isMenuOpen)}
            >
              {isMenuOpen ? <FiX size={24} /> : <FiMenu size={24} />}
            </button>
          </div>
        </div>

        {/* Filters Panel (only on home page) */}
        {isHomePage && showFilters && onSort && onFilter && (
          <div className="navbar-filters-panel">
            <div className="filter-group">
              <label className="filter-label">Sort By:</label>
              <select
                value={sortBy || 'name'}
                onChange={(e) => onSort(e.target.value)}
                className="filter-select"
              >
                <option value="name">Name (A-Z)</option>
                <option value="price-low">Price (Low to High)</option>
                <option value="price-high">Price (High to Low)</option>
                <option value="rating">Rating (High to Low)</option>
              </select>
            </div>

            <div className="filter-group">
              <label className="filter-label">Filter By:</label>
              <select
                value={filterBy || 'all'}
                onChange={(e) => onFilter(e.target.value)}
                className="filter-select"
              >
                <option value="all">All Products</option>
                <option value="featured">Featured Only</option>
                <option value="in-stock">In Stock Only</option>
              </select>
            </div>
          </div>
        )}

        {/* Mobile Menu */}
        {isMenuOpen && (
          <div className="mobile-menu">
            <Link to="/" className="mobile-nav-link" onClick={() => setIsMenuOpen(false)}>
              Home
            </Link>
            <Link to="/products" className="mobile-nav-link" onClick={() => setIsMenuOpen(false)}>
              Products
            </Link>
            {isAuthenticated ? (
              <>
                <Link to="/cart" className="mobile-nav-link" onClick={() => setIsMenuOpen(false)}>
                  Cart ({cartItemCount})
                </Link>
                <button onClick={handleLogout} className="mobile-nav-link logout-btn">
                  Logout
                </button>
              </>
            ) : (
              <>
                <Link to="/login" className="mobile-nav-link" onClick={() => setIsMenuOpen(false)}>
                  Login
                </Link>
                <Link to="/register" className="mobile-nav-link" onClick={() => setIsMenuOpen(false)}>
                  Register
                </Link>
              </>
            )}
          </div>
        )}
      </div>
    </nav>
  );
};

export default Navbar;
