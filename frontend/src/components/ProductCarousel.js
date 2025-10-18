import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { FiChevronLeft, FiChevronRight, FiStar, FiShoppingCart } from 'react-icons/fi';
import { useCart } from '../context/CartContext';
import { useAuth } from '../context/AuthContext';
import './ProductCarousel.css';

const ProductCarousel = ({ products, maxItemsPerView = 4 }) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [itemsPerView, setItemsPerView] = useState(() => Math.min(maxItemsPerView, 4));
  const { addToCart } = useCart();
  const { isAuthenticated } = useAuth();

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 640) {
        setItemsPerView(1);
      } else if (window.innerWidth < 768) {
        setItemsPerView(Math.min(2, maxItemsPerView));
      } else if (window.innerWidth < 1024) {
        setItemsPerView(Math.min(3, maxItemsPerView));
      } else {
        setItemsPerView(Math.min(4, maxItemsPerView));
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [maxItemsPerView]);

  const maxIndex = Math.max(0, products.length - itemsPerView);

  const nextSlide = () => {
    setCurrentIndex(prev => (prev >= maxIndex ? 0 : prev + 1));
  };

  const prevSlide = () => {
    setCurrentIndex(prev => (prev <= 0 ? maxIndex : prev - 1));
  };

  const handleAddToCart = (e, productId) => {
    e.preventDefault();
    e.stopPropagation();
    addToCart(productId, 1);
  };

  if (!products || products.length === 0) {
    return (
      <div className="carousel-empty">
        <p>No featured products available</p>
      </div>
    );
  }

  return (
    <div className="product-carousel">
      <div className="carousel-container">
        <button 
          className="carousel-btn carousel-btn-prev"
          onClick={prevSlide}
          disabled={products.length <= itemsPerView}
        >
          <FiChevronLeft size={20} />
        </button>

        <div className="carousel-wrapper">
          <div 
            className="carousel-track"
            style={{
              transform: `translateX(-${currentIndex * (100 / itemsPerView)}%)`,
              width: `${(products.length / itemsPerView) * 100}%`
            }}
          >
            {products.map((product) => (
              <div 
                key={product.id}
                className="carousel-item"
                style={{
                  flex: `0 0 ${100 / itemsPerView}%`,
                  maxWidth: `${100 / itemsPerView}%`
                }}
              >
                <Link to={`/products/${product.id}`} className="product-card">
                  <div className="product-image">
                    <img src={product.image} alt={product.name} />
                    <div className="product-overlay">
                      {isAuthenticated && (
                        <button
                          className="add-to-cart-btn"
                          onClick={(e) => handleAddToCart(e, product.id)}
                        >
                          <FiShoppingCart size={16} />
                          Add to Cart
                        </button>
                      )}
                    </div>
                  </div>
                  <div className="product-info">
                    <h3 className="product-name">{product.name}</h3>
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
                    <div className="product-price">
                      ${product.price.toFixed(2)}
                    </div>
                  </div>
                </Link>
              </div>
            ))}
          </div>
        </div>

        <button 
          className="carousel-btn carousel-btn-next"
          onClick={nextSlide}
          disabled={products.length <= itemsPerView}
        >
          <FiChevronRight size={20} />
        </button>
      </div>

      {/* Dots Indicator */}
      {products.length > itemsPerView && (
        <div className="carousel-dots">
          {[...Array(maxIndex + 1)].map((_, index) => (
            <button
              key={index}
              className={`carousel-dot ${index === currentIndex ? 'active' : ''}`}
              onClick={() => setCurrentIndex(index)}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default ProductCarousel;
