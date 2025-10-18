import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { FiArrowRight, FiStar, FiShoppingCart } from 'react-icons/fi';
import axios from 'axios';
import { useCart } from '../context/CartContext';
import { useAuth } from '../context/AuthContext';
import './Home.css';

const Home = ({ searchTerm, sortBy, filterBy }) => {
  const [allProducts, setAllProducts] = useState([]);
  const [filteredProducts, setFilteredProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const { addToCart } = useCart();
  const { isAuthenticated } = useAuth();

  useEffect(() => {
    const fetchProducts = async () => {
      try {
        const response = await axios.get('http://localhost:8000/products');
        const allData = response.data;
        setAllProducts(allData);
        setFilteredProducts(allData);
      } catch (error) {
        console.error('Error fetching products:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchProducts();
  }, []);

  useEffect(() => {
    let filtered = [...allProducts];

    // Apply search filter
    if (searchTerm) {
      filtered = filtered.filter(product =>
        product.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        product.description.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // Apply category filter
    if (filterBy && filterBy !== 'all') {
      filtered = filtered.filter(product => product.category === filterBy);
    }

    // Apply sorting
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'price-low':
          return a.price - b.price;
        case 'price-high':
          return b.price - a.price;
        case 'rating':
          return b.rating - a.rating;
        case 'name':
        default:
          return a.name.localeCompare(b.name);
      }
    });

    setFilteredProducts(filtered);
  }, [allProducts, searchTerm, sortBy, filterBy]);

  const handleAddToCart = (productId) => {
    if (!isAuthenticated) {
      // For non-authenticated users, show a message or redirect to login
      return;
    }
    addToCart(productId, 1);
  };

  if (loading) {
    return (
      <div className="home">
        <div className="container">
          <div className="loading-container">
            <div className="spinner"></div>
            <p>Loading products...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="home">
      {/* All Products Grid */}
      <section className="products-section">
        <div className="container">
          <div className="section-header">
            <h2 className="section-title">
              {searchTerm ? `Search Results for "${searchTerm}"` : 'All Products'}
            </h2>
            <p className="section-description">
              {filteredProducts.length} {filteredProducts.length === 1 ? 'product' : 'products'} found
            </p>
          </div>

          {filteredProducts.length === 0 ? (
            <div className="no-products">
              <p>No products found matching your criteria.</p>
            </div>
          ) : (
            <div className="products-grid">
              {filteredProducts.map((product) => (
                <div key={product.id} className="product-card">
                  <Link to={`/products/${product.id}`} className="product-link">
                    <div className="product-image">
                      <img src={product.image} alt={product.name} />
                      {product.featured && (
                        <span className="featured-badge">Featured</span>
                      )}
                      {product.stock === 0 && (
                        <span className="out-of-stock-badge">Out of Stock</span>
                      )}
                    </div>
                    <div className="product-info">
                      <h3 className="product-name">{product.name}</h3>
                      <p className="product-description">{product.description}</p>
                      <div className="product-rating">
                        <div className="stars">
                          {[...Array(5)].map((_, i) => (
                            <FiStar
                              key={i}
                              size={14}
                              className={i < Math.floor(product.rating) ? 'star-filled' : 'star-empty'}
                            />
                          ))}
                        </div>
                        <span className="rating-text">({product.rating})</span>
                      </div>
                      <div className="product-footer">
                        <div className="product-price">
                          ${product.price.toFixed(2)}
                        </div>
                        <div className="product-stock">
                          {product.stock > 0 ? (
                            <span className="in-stock">{product.stock} in stock</span>
                          ) : (
                            <span className="out-of-stock">Out of stock</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </Link>
                  {product.stock > 0 && (
                    <button
                      className="add-to-cart-btn"
                      onClick={(e) => {
                        e.preventDefault();
                        if (isAuthenticated) {
                          handleAddToCart(product.id);
                        } else {
                          // Show login prompt or redirect
                          window.location.href = '/login';
                        }
                      }}
                    >
                      <FiShoppingCart size={16} />
                      {isAuthenticated ? 'Add to Cart' : 'Login to Buy'}
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* CTA Section for non-authenticated users */}
      {!isAuthenticated && (
        <section className="cta-section">
          <div className="container">
            <div className="cta-content">
              <h2 className="cta-title">Ready to Start Shopping?</h2>
              <p className="cta-description">
                Create an account to add items to your cart and complete purchases
              </p>
              <div className="cta-actions">
                <Link to="/register" className="btn btn-primary btn-lg">
                  Get Started
                  <FiArrowRight />
                </Link>
                <Link to="/login" className="btn btn-outline btn-lg">
                  Sign In
                </Link>
              </div>
            </div>
          </div>
        </section>
      )}
    </div>
  );
};

export default Home;
