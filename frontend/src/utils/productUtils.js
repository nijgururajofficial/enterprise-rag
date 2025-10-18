/**
 * Product utility functions for filtering, sorting, and searching products
 */

/**
 * Filter products by category
 * @param {Array} products - Array of product objects
 * @param {string} category - Category to filter by (e.g., 'phones', 'laptops', 'monitors', 'accessories')
 * @returns {Array} Filtered array of products
 */
export const filterProductsByCategory = (products, category) => {
  if (!products || !Array.isArray(products)) {
    return [];
  }

  // Return all products if category is 'all' or not specified
  if (!category || category === 'all') {
    return products;
  }

  return products.filter(product => 
    product.category && product.category.toLowerCase() === category.toLowerCase()
  );
};

/**
 * Filter products by search term (searches in name and description)
 * @param {Array} products - Array of product objects
 * @param {string} searchTerm - Search term to filter by
 * @returns {Array} Filtered array of products
 */
export const filterProductsBySearch = (products, searchTerm) => {
  if (!products || !Array.isArray(products)) {
    return [];
  }

  if (!searchTerm || searchTerm.trim() === '') {
    return products;
  }

  const lowerSearchTerm = searchTerm.toLowerCase();
  
  return products.filter(product => 
    (product.name && product.name.toLowerCase().includes(lowerSearchTerm)) ||
    (product.description && product.description.toLowerCase().includes(lowerSearchTerm))
  );
};

/**
 * Filter products by multiple categories
 * @param {Array} products - Array of product objects
 * @param {Array} categories - Array of categories to filter by
 * @returns {Array} Filtered array of products
 */
export const filterProductsByMultipleCategories = (products, categories) => {
  if (!products || !Array.isArray(products)) {
    return [];
  }

  if (!categories || !Array.isArray(categories) || categories.length === 0) {
    return products;
  }

  const lowerCategories = categories.map(cat => cat.toLowerCase());
  
  return products.filter(product => 
    product.category && lowerCategories.includes(product.category.toLowerCase())
  );
};

/**
 * Filter products by price range
 * @param {Array} products - Array of product objects
 * @param {number} minPrice - Minimum price (inclusive)
 * @param {number} maxPrice - Maximum price (inclusive)
 * @returns {Array} Filtered array of products
 */
export const filterProductsByPriceRange = (products, minPrice, maxPrice) => {
  if (!products || !Array.isArray(products)) {
    return [];
  }

  return products.filter(product => {
    const price = parseFloat(product.price);
    const min = minPrice !== undefined ? parseFloat(minPrice) : 0;
    const max = maxPrice !== undefined ? parseFloat(maxPrice) : Infinity;
    
    return price >= min && price <= max;
  });
};

/**
 * Filter products by rating
 * @param {Array} products - Array of product objects
 * @param {number} minRating - Minimum rating (inclusive)
 * @returns {Array} Filtered array of products
 */
export const filterProductsByRating = (products, minRating) => {
  if (!products || !Array.isArray(products)) {
    return [];
  }

  if (minRating === undefined || minRating === null) {
    return products;
  }

  return products.filter(product => 
    product.rating && parseFloat(product.rating) >= parseFloat(minRating)
  );
};

/**
 * Filter products by stock availability
 * @param {Array} products - Array of product objects
 * @param {boolean} inStockOnly - If true, only return products with stock > 0
 * @returns {Array} Filtered array of products
 */
export const filterProductsByStock = (products, inStockOnly = false) => {
  if (!products || !Array.isArray(products)) {
    return [];
  }

  if (!inStockOnly) {
    return products;
  }

  return products.filter(product => 
    product.stock && parseInt(product.stock) > 0
  );
};

/**
 * Sort products by various criteria
 * @param {Array} products - Array of product objects
 * @param {string} sortBy - Sort criteria ('name', 'price-low', 'price-high', 'rating')
 * @returns {Array} Sorted array of products
 */
export const sortProducts = (products, sortBy) => {
  if (!products || !Array.isArray(products)) {
    return [];
  }

  const sortedProducts = [...products];

  switch (sortBy) {
    case 'price-low':
      return sortedProducts.sort((a, b) => parseFloat(a.price) - parseFloat(b.price));
    
    case 'price-high':
      return sortedProducts.sort((a, b) => parseFloat(b.price) - parseFloat(a.price));
    
    case 'rating':
      return sortedProducts.sort((a, b) => parseFloat(b.rating || 0) - parseFloat(a.rating || 0));
    
    case 'name':
    default:
      return sortedProducts.sort((a, b) => 
        (a.name || '').localeCompare(b.name || '')
      );
  }
};

/**
 * Apply all filters and sorting to products
 * @param {Array} products - Array of product objects
 * @param {Object} options - Filter and sort options
 * @param {string} options.category - Category to filter by
 * @param {string} options.searchTerm - Search term to filter by
 * @param {string} options.sortBy - Sort criteria
 * @param {number} options.minPrice - Minimum price
 * @param {number} options.maxPrice - Maximum price
 * @param {number} options.minRating - Minimum rating
 * @param {boolean} options.inStockOnly - Only show in-stock products
 * @returns {Array} Filtered and sorted array of products
 */
export const applyProductFilters = (products, options = {}) => {
  if (!products || !Array.isArray(products)) {
    return [];
  }

  let filtered = [...products];

  // Apply category filter
  if (options.category) {
    filtered = filterProductsByCategory(filtered, options.category);
  }

  // Apply search filter
  if (options.searchTerm) {
    filtered = filterProductsBySearch(filtered, options.searchTerm);
  }

  // Apply price range filter
  if (options.minPrice !== undefined || options.maxPrice !== undefined) {
    filtered = filterProductsByPriceRange(filtered, options.minPrice, options.maxPrice);
  }

  // Apply rating filter
  if (options.minRating) {
    filtered = filterProductsByRating(filtered, options.minRating);
  }

  // Apply stock filter
  if (options.inStockOnly) {
    filtered = filterProductsByStock(filtered, true);
  }

  // Apply sorting
  if (options.sortBy) {
    filtered = sortProducts(filtered, options.sortBy);
  }

  return filtered;
};

/**
 * Get unique categories from products array
 * @param {Array} products - Array of product objects
 * @returns {Array} Array of unique categories
 */
export const getUniqueCategories = (products) => {
  if (!products || !Array.isArray(products)) {
    return [];
  }

  const categories = products
    .map(product => product.category)
    .filter(category => category !== undefined && category !== null && category !== '');

  return [...new Set(categories)];
};

