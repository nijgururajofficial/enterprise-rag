# Mock products database with enhanced electronics focus
products = {
    "p1": {
        "id": "p1", 
        "name": "Wireless Noise-Canceling Headphones", 
        "price": 299.99, 
        "category": "electronics",
        "description": "Premium wireless headphones with active noise cancellation and 30-hour battery life.",
        "image": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500",
        "stock": 25,
        "featured": True,
        "rating": 4.8
    },
    "p2": {
        "id": "p2", 
        "name": "Smart Fitness Watch", 
        "price": 249.99, 
        "category": "electronics",
        "description": "Advanced smartwatch with health monitoring, GPS, and 7-day battery life.",
        "image": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=500",
        "stock": 15,
        "featured": True,
        "rating": 4.6
    },
    "p3": {
        "id": "p3", 
        "name": "4K Gaming Monitor", 
        "price": 599.99, 
        "category": "electronics",
        "description": "27-inch 4K gaming monitor with 144Hz refresh rate and HDR support.",
        "image": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=500",
        "stock": 8,
        "featured": True,
        "rating": 4.9
    },
    "p4": {
        "id": "p4", 
        "name": "Wireless Mechanical Keyboard", 
        "price": 179.99, 
        "category": "electronics",
        "description": "Premium wireless mechanical keyboard with RGB backlighting and hot-swappable switches.",
        "image": "https://images.unsplash.com/photo-1541140532154-b024d705b90a?w=500",
        "stock": 12,
        "featured": False,
        "rating": 4.7
    },
    "p5": {
        "id": "p5", 
        "name": "Smartphone 128GB", 
        "price": 799.99, 
        "category": "electronics",
        "description": "Latest smartphone with triple camera system, 5G connectivity, and all-day battery.",
        "image": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=500",
        "stock": 20,
        "featured": True,
        "rating": 4.5
    },
    "p6": {
        "id": "p6", 
        "name": "Bluetooth Speaker", 
        "price": 89.99, 
        "category": "electronics",
        "description": "Portable waterproof Bluetooth speaker with 360-degree sound and 12-hour battery.",
        "image": "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=500",
        "stock": 30,
        "featured": False,
        "rating": 4.4
    },
    "p7": {
        "id": "p7", 
        "name": "Laptop 16GB RAM", 
        "price": 1299.99, 
        "category": "electronics",
        "description": "High-performance laptop with Intel i7 processor, 16GB RAM, and 512GB SSD.",
        "image": "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=500",
        "stock": 5,
        "featured": True,
        "rating": 4.8
    },
    "p8": {
        "id": "p8", 
        "name": "Wireless Earbuds", 
        "price": 149.99, 
        "category": "electronics",
        "description": "True wireless earbuds with active noise cancellation and wireless charging case.",
        "image": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=500",
        "stock": 40,
        "featured": False,
        "rating": 4.3
    }
}

# Mock orders database
orders = {}

# Mock users database
users = {
    "user1": {
        "id": "user1",
        "email": "john@example.com",
        "password": "hashed_password_123",  # In real app, this would be properly hashed
        "name": "John Doe",
        "address": "123 Main St, City, State 12345"
    }
}

# Mock shopping carts database
carts = {}

# Mock conversation sessions database
# Structure: {session_id: {context: dict, messages: list, user_id: str}}
sessions = {}