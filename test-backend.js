const axios = require('axios');

async function testBackend() {
  const API_BASE_URL = 'http://localhost:8000';
  
  try {
    console.log('🔍 Testing backend connection...');
    
    // Test health endpoint
    const healthResponse = await axios.get(`${API_BASE_URL}/health`, { timeout: 5000 });
    console.log('✅ Backend health check:', healthResponse.data);
    
    // Test card validation endpoint
    const testCardData = {
      card_number: '4242424242424242',
      expiry_month: '12',
      expiry_year: '2025',
      cvv: '123'
    };
    
    const validationResponse = await axios.post(`${API_BASE_URL}/validate-card`, testCardData, {
      timeout: 5000,
      headers: { 'Content-Type': 'application/json' }
    });
    
    console.log('✅ Card validation test:', validationResponse.data);
    
    console.log('🎉 Backend is working correctly!');
    
  } catch (error) {
    console.error('❌ Backend test failed:', error.message);
    
    if (error.code === 'ECONNREFUSED') {
      console.log('💡 Make sure the backend is running with:');
      console.log('   cd backend && python -m uvicorn app.main:app --reload');
    }
  }
}

testBackend(); 