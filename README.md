# Payment Gateway Project

A complete payment gateway solution with FastAPI backend and React frontend.

## 🚀 Features

- **FastAPI Backend**: Modern Python web framework with auto-generated API docs
- **MySQL Database**: Persistent storage with SQLAlchemy ORM
- **React Frontend**: Beautiful, responsive payment form with Bootstrap
- **Auto Table Creation**: Database tables created automatically on startup
- **CORS Enabled**: Frontend can communicate with backend seamlessly
- **Transaction Tracking**: Unique reference numbers for each transaction

## 📁 Project Structure

```
Payment-Gateway/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI application
│   │   ├── database.py      # Database configuration
│   │   ├── model.py         # SQLAlchemy models
│   │   └── schemas.py       # Pydantic schemas
│   ├── requirements.txt     # Python dependencies
│   └── env.example          # Environment variables template
├── frontend/
│   ├── public/
│   │   └── index.html       # Main HTML file
│   ├── src/
│   │   ├── App.js           # Main React component
│   │   ├── App.css          # Component styles
│   │   ├── index.js         # React entry point
│   │   └── index.css        # Global styles
│   └── package.json         # Node.js dependencies
└── README.md               # This file
```

## 🛠️ Setup Instructions

### Prerequisites

- Python 3.8+
- Node.js 16+
- MySQL Server
- SQLyog (for database management)

### 1. Database Setup

1. Create a MySQL database named `payment_gateway`
2. Copy `backend/env.example` to `backend/.env`
3. Update the database credentials in `backend/.env`:

```env
DB_USER=your_username
DB_PASSWORD=your_password
DB_HOST=localhost
DB_NAME=payment_gateway
```

### 2. Backend Setup

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend will run on: `http://localhost:8000`
API Documentation: `http://localhost:8000/docs`

### 3. Frontend Setup

```bash
cd frontend
npm install
npm start
```

Frontend will run on: `http://localhost:3000`

## 🗄️ Database Schema

### Transactions Table

| Column     | Type      | Description                    |
|------------|-----------|--------------------------------|
| id         | INT       | Primary key                    |
| full_name  | VARCHAR   | Customer's full name           |
| email      | VARCHAR   | Customer's email address       |
| phone      | VARCHAR   | Customer's phone number        |
| amount     | FLOAT     | Payment amount                 |
| reference  | VARCHAR   | Unique transaction reference   |
| status     | VARCHAR   | Transaction status (pending)   |
| created_at | TIMESTAMP | Transaction creation time      |

## 🔌 API Endpoints

### POST /transactions/create
Create a new payment transaction.

**Request Body:**
```json
{
  "full_name": "John Doe",
  "email": "john@example.com",
  "phone": "+1234567890",
  "amount": 99.99
}
```

**Response:**
```json
{
  "id": 1,
  "full_name": "John Doe",
  "email": "john@example.com",
  "phone": "+1234567890",
  "amount": 99.99,
  "reference": "uuid-reference-here",
  "status": "pending",
  "created_at": "2024-01-01T12:00:00"
}
```

### GET /transactions
Get all transactions (for admin purposes).

### GET /
Health check endpoint.

## 🎨 Frontend Features

- **Responsive Design**: Works on desktop, tablet, and mobile
- **Modern UI**: Clean, professional payment form
- **Real-time Validation**: Form validation and error handling
- **Loading States**: Visual feedback during payment processing
- **Success/Error Messages**: Clear feedback to users
- **Bootstrap Styling**: Professional appearance with custom CSS

## 🔒 Security Features

- **Input Validation**: Server-side validation with Pydantic
- **SQL Injection Protection**: SQLAlchemy ORM prevents SQL injection
- **CORS Configuration**: Proper CORS setup for frontend-backend communication
- **Error Handling**: Graceful error handling and user feedback

## 🚀 Quick Start

1. **Start Backend:**
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

2. **Start Frontend:**
   ```bash
   cd frontend
   npm install
   npm start
   ```

3. **Open Browser:**
   - Frontend: `http://localhost:3000`
   - Backend API Docs: `http://localhost:8000/docs`

4. **Test Payment:**
   - Fill out the payment form
   - Click "Pay Now"
   - See the transaction reference in the success message

## 🛠️ Development

### Backend Development
- FastAPI with automatic API documentation
- SQLAlchemy for database operations
- Pydantic for data validation
- CORS middleware for frontend integration

### Frontend Development
- React with functional components and hooks
- Bootstrap for responsive design
- Axios for API communication
- Custom CSS for enhanced styling

## 📝 Environment Variables

### Backend (.env)
```env
DB_USER=root
DB_PASSWORD=your_password
DB_HOST=localhost
DB_NAME=payment_gateway
```

## 🔧 Troubleshooting

### Common Issues

1. **Database Connection Error:**
   - Check MySQL server is running
   - Verify database credentials in `.env`
   - Ensure database `payment_gateway` exists

2. **CORS Error:**
   - Backend CORS is configured for `http://localhost:3000`
   - Ensure frontend is running on port 3000

3. **Port Already in Use:**
   - Backend: Change port in uvicorn command
   - Frontend: React will automatically suggest alternative port

## 📈 Production Deployment

For production deployment:

1. **Backend:**
   - Use production WSGI server (Gunicorn)
   - Set up proper environment variables
   - Configure HTTPS
   - Add logging and monitoring

2. **Frontend:**
   - Build production version: `npm run build`
   - Serve static files with Nginx
   - Configure proper CORS origins

3. **Database:**
   - Use production MySQL configuration
   - Set up proper backups
   - Configure connection pooling

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is open source and available under the MIT License. 
